"""Default-off bounded installer framework for the local cutout checkpoint.

The browser selects only the versioned contract and fixed source identity.  It
cannot supply a URL, filesystem path, size, or digest. Production download is
disabled while source and authorization remain unverified. Explicitly enabled
test fixtures stream to a same-directory exclusive temporary file and publish
only after the embedded size and digest contract has been verified.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import os
import re
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional
from urllib.parse import urljoin, urlsplit

import httpx

from image_tools.cutout_onnx import CutoutAdapterError, CutoutONNXAdapter


MODEL_INSTALL_CONTRACT = "genbox-cutout-model-install-v1"
MODEL_SOURCE_ID = "rembg-u2net-human-seg-v0.0.0"
MODEL_SOURCE_PAGE = "https://github.com/danielgatis/rembg/releases/tag/v0.0.0"
MODEL_DOWNLOAD_URL = (
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
    "u2net_human_seg.onnx"
)
MODEL_DOWNLOAD_HOSTS = frozenset({"github.com", "release-assets.githubusercontent.com"})
MODEL_DOWNLOAD_TIMEOUT_SECONDS = 180.0
MODEL_INSTALL_LOCK_TIMEOUT_SECONDS = 5.0
MODEL_DOWNLOAD_MAX_REDIRECTS = 5
MODEL_DOWNLOAD_CHUNK_BYTES = 1024 * 1024
_PART_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
_TERMINAL_TASK_STATES = frozenset({"completed", "failed", "cancelled"})


class CutoutModelManagerError(RuntimeError):
    """A structured failure whose public form contains no URL or local path."""

    def __init__(self, code: str, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.status_code = int(status_code)

    def to_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "contract": MODEL_INSTALL_CONTRACT,
            "source_id": MODEL_SOURCE_ID,
        }


class _DownloadCancelled(RuntimeError):
    pass


def _default_resolver(host: str, port: int) -> list[str]:
    addresses: list[str] = []
    for result in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        address = str(result[4][0])
        if address not in addresses:
            addresses.append(address)
    return addresses


class CutoutModelManager:
    """Process-local single-flight task manager for one immutable checkpoint."""

    def __init__(
        self,
        adapter: CutoutONNXAdapter,
        *,
        download_url: str = MODEL_DOWNLOAD_URL,
        source_id: str = MODEL_SOURCE_ID,
        source_page: str = MODEL_SOURCE_PAGE,
        allowed_hosts: Iterable[str] = MODEL_DOWNLOAD_HOSTS,
        resolver: Optional[Callable[[str, int], Iterable[str]]] = None,
        client_factory: Optional[Callable[[], Any]] = None,
        timeout_seconds: float = MODEL_DOWNLOAD_TIMEOUT_SECONDS,
        install_lock_timeout_seconds: float = MODEL_INSTALL_LOCK_TIMEOUT_SECONDS,
        max_redirects: int = MODEL_DOWNLOAD_MAX_REDIRECTS,
        download_supported: bool = False,
    ) -> None:
        self.adapter = adapter
        self.model_path = Path(adapter.model_path).resolve()
        self.expected_manifest = dict(adapter.expected_manifest)
        self.download_url = str(download_url)
        self.source_id = str(source_id)
        self.source_page = str(source_page)
        self.allowed_hosts = frozenset(str(host).lower() for host in allowed_hosts)
        self.resolver = resolver or _default_resolver
        self.client_factory = client_factory
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 600.0))
        self.install_lock_timeout_seconds = max(
            0.01, min(float(install_lock_timeout_seconds), 30.0)
        )
        self.max_redirects = max(0, min(int(max_redirects), 10))
        self.download_supported = download_supported is True
        self._state_lock = threading.RLock()
        self._mutation_lock = threading.Lock()
        self._tasks: dict[str, dict[str, Any]] = {}
        self._runners: dict[str, asyncio.Task[Any]] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._active_task_id: Optional[str] = None
        self._validate_fixed_contract()
        self.cleanup_stale_parts()

    def _expected(self) -> tuple[int, str, str, str]:
        try:
            filename = str(self.expected_manifest["filename"])
            size = int(self.expected_manifest["size_bytes"])
            sha256 = str(self.expected_manifest["sha256"]).lower()
            md5 = str(self.expected_manifest["md5"]).lower()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid cutout model manifest") from exc
        if (
            filename != self.model_path.name
            or size <= 0
            or not re.fullmatch(r"[0-9a-f]{64}", sha256)
            or not re.fullmatch(r"[0-9a-f]{32}", md5)
        ):
            raise ValueError("invalid cutout model manifest")
        return size, sha256, md5, filename

    def _validate_fixed_contract(self) -> None:
        _size, _sha256, _md5, filename = self._expected()
        if (
            self.source_id != MODEL_SOURCE_ID
            or self.source_page != MODEL_SOURCE_PAGE
            or self.download_url != MODEL_DOWNLOAD_URL
            or self.allowed_hosts != MODEL_DOWNLOAD_HOSTS
        ):
            raise ValueError("fixed cutout model source contract cannot be overridden")
        parsed = self._validated_url(self.download_url, initial=True)
        if parsed.hostname != "github.com" or not parsed.path.endswith("/" + filename):
            raise ValueError("invalid fixed cutout model source")
        source_page = urlsplit(self.source_page)
        if (
            source_page.scheme.lower() != "https"
            or source_page.hostname != "github.com"
            or source_page.username is not None
            or source_page.password is not None
            or source_page.port not in (None, 443)
            or source_page.query
            or source_page.fragment
        ):
            raise ValueError("invalid fixed cutout model source page")

    def _validated_url(self, value: str, *, initial: bool) -> Any:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except (TypeError, ValueError) as exc:
            raise CutoutModelManagerError(
                "cutout_model_source_rejected",
                "抠图模型下载来源不受信任",
            ) from exc
        hostname = parsed.hostname
        if (
            parsed.scheme.lower() != "https"
            or not hostname
            or hostname != hostname.lower()
            or hostname not in self.allowed_hosts
            or parsed.username is not None
            or parsed.password is not None
            or port not in (None, 443)
            or parsed.fragment
            or (initial and parsed.query)
        ):
            raise CutoutModelManagerError(
                "cutout_model_source_rejected",
                "抠图模型下载来源不受信任",
            )
        return parsed

    def _verify_public_dns(self, hostname: str) -> None:
        try:
            addresses = list(self.resolver(hostname, 443))
        except Exception as exc:
            raise CutoutModelManagerError(
                "cutout_model_source_unresolved",
                "抠图模型下载来源无法解析",
            ) from exc
        if not addresses:
            raise CutoutModelManagerError(
                "cutout_model_source_unresolved",
                "抠图模型下载来源无法解析",
            )
        try:
            parsed_addresses = [ipaddress.ip_address(str(value).split("%", 1)[0]) for value in addresses]
        except ValueError as exc:
            raise CutoutModelManagerError(
                "cutout_model_source_rejected",
                "抠图模型下载来源不受信任",
            ) from exc
        if any(not address.is_global for address in parsed_addresses):
            raise CutoutModelManagerError(
                "cutout_model_source_rejected",
                "抠图模型下载来源不受信任",
            )

    def _make_client(self):
        if self.client_factory is not None:
            return self.client_factory()
        return httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(self.timeout_seconds),
            trust_env=False,
            headers={
                "Accept-Encoding": "identity",
                "User-Agent": "GenBox cutout model installer",
            },
        )

    def _open_part(self) -> tuple[Path, Any]:
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        for _attempt in range(16):
            candidate = self.model_path.with_name(
                f"{self.model_path.name}.{uuid.uuid4().hex}.part"
            )
            try:
                handle = candidate.open("xb")
            except FileExistsError:
                continue
            return candidate, handle
        raise CutoutModelManagerError(
            "cutout_model_temp_unavailable",
            "无法创建抠图模型临时文件",
        )

    def _is_owned_part(self, candidate: Path) -> bool:
        prefix = self.model_path.name + "."
        name = candidate.name
        if candidate.parent.resolve() != self.model_path.parent.resolve():
            return False
        if not name.startswith(prefix) or not name.endswith(".part"):
            return False
        token = name[len(prefix) : -len(".part")]
        return bool(_PART_TOKEN_RE.fullmatch(token))

    def cleanup_stale_parts(self) -> int:
        """Remove only temp files created for this exact model filename."""

        parent = self.model_path.parent
        if not parent.is_dir():
            return 0
        removed = 0
        try:
            candidates = list(parent.glob(f"{self.model_path.name}.*.part"))
        except OSError:
            return 0
        for candidate in candidates:
            if not self._is_owned_part(candidate):
                continue
            try:
                candidate.unlink(missing_ok=True)
                removed += 1
            except OSError:
                continue
        return removed

    @staticmethod
    def _safe_task(state: Mapping[str, Any]) -> dict[str, Any]:
        keys = (
            "id",
            "contract",
            "source_id",
            "status",
            "phase",
            "progress",
            "downloaded_bytes",
            "total_bytes",
            "error_code",
            "message",
        )
        return {key: state.get(key) for key in keys}

    def _update_task(self, task_id: str, **updates: Any) -> None:
        with self._state_lock:
            state = self._tasks.get(task_id)
            if state is not None:
                state.update(updates)

    def _finish_task(self, task_id: str, **updates: Any) -> None:
        with self._state_lock:
            state = self._tasks.get(task_id)
            if state is not None:
                state.update(updates)
            if self._active_task_id == task_id:
                self._active_task_id = None
            self._runners.pop(task_id, None)
            self._cancel_events.pop(task_id, None)

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._state_lock:
            state = self._tasks.get(str(task_id))
            return self._safe_task(state) if state is not None else None

    def _active_task(self) -> Optional[dict[str, Any]]:
        with self._state_lock:
            if self._active_task_id is None:
                return None
            state = self._tasks.get(self._active_task_id)
            return self._safe_task(state) if state is not None else None

    def model_status(self) -> dict[str, Any]:
        expected_size, expected_sha, expected_md5, filename = self._expected()
        installed = self.model_path.exists() or self.model_path.is_symlink()
        valid = False
        reason: Optional[str] = None
        try:
            self.adapter.validate_model_artifact()
            installed = True
            valid = True
        except CutoutAdapterError as exc:
            reason = exc.code
        except Exception:
            reason = "cutout_model_unreadable"
        state = "ready" if valid else ("invalid" if installed else "missing")
        return {
            "contract": MODEL_INSTALL_CONTRACT,
            "source_id": self.source_id,
            "source_page": self.source_page,
            "filename": filename,
            "installed": installed,
            "valid": valid,
            "state": state,
            "reason": reason,
            "size_bytes": expected_size,
            "sha256": expected_sha,
            "md5": expected_md5,
            "download_supported": self.download_supported,
            "install_supported": self.download_supported,
            "confirmation_required": True,
            "license": {
                "checkpoint_provenance_status": "UNVERIFIED",
                "commercial_use_status": "UNVERIFIED",
            },
            "active_task": self._active_task(),
        }

    def model_projection_from_capability(self, capability: Mapping[str, Any]) -> dict[str, Any]:
        # Keep the model projection about the artifact itself.  Dependency or
        # ONNX-session failures belong to the legacy capability fields and must
        # not make an installed, hash-valid checkpoint appear absent.
        status = self.model_status()
        status["active_task"] = self._active_task()
        return status

    def start_download(self) -> dict[str, Any]:
        if not self.download_supported:
            raise CutoutModelManagerError(
                "cutout_model_download_unavailable",
                "抠图模型来源和使用授权尚未验证，当前版本不支持联网下载",
                status_code=409,
            )
        with self._state_lock:
            if self._active_task_id is not None:
                active = self._tasks.get(self._active_task_id)
                if active is not None and active.get("status") not in _TERMINAL_TASK_STATES:
                    raise CutoutModelManagerError(
                        "cutout_model_download_busy",
                        "已有抠图模型下载任务正在运行",
                        status_code=409,
                    )
            task_id = "cutout-model-" + uuid.uuid4().hex[:16]
            expected_size, _sha, _md5, _filename = self._expected()
            state = {
                "id": task_id,
                "contract": MODEL_INSTALL_CONTRACT,
                "source_id": self.source_id,
                "status": "queued",
                "phase": "queued",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": expected_size,
                "error_code": None,
                "message": "下载任务已创建",
            }
            cancel_event = threading.Event()
            self._tasks[task_id] = state
            self._cancel_events[task_id] = cancel_event
            self._active_task_id = task_id
            try:
                runner = asyncio.create_task(self._run_download(task_id, cancel_event))
            except Exception:
                self._tasks.pop(task_id, None)
                self._cancel_events.pop(task_id, None)
                self._active_task_id = None
                raise
            self._runners[task_id] = runner
            terminal_ids = [
                key for key, value in self._tasks.items()
                if key != task_id and value.get("status") in _TERMINAL_TASK_STATES
            ]
            for old_id in terminal_ids[:-8]:
                self._tasks.pop(old_id, None)
            return self._safe_task(state)

    async def cancel_download(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._state_lock:
            state = self._tasks.get(str(task_id))
            if state is None:
                return None
            if state.get("status") in _TERMINAL_TASK_STATES:
                return self._safe_task(state)
            cancel_event = self._cancel_events.get(str(task_id))
            runner = self._runners.get(str(task_id))
            if cancel_event is not None:
                cancel_event.set()
            if runner is not None:
                runner.cancel()
        if runner is not None:
            try:
                await runner
            except asyncio.CancelledError:
                pass
        current = self.get_task(str(task_id))
        if current is not None and current.get("status") not in _TERMINAL_TASK_STATES:
            self._finish_task(
                str(task_id),
                status="cancelled",
                phase="cancelled",
                error_code=None,
                message="抠图模型下载已取消",
            )
        return self.get_task(str(task_id))

    async def _run_download(self, task_id: str, cancel_event: threading.Event) -> None:
        part_path: Optional[Path] = None
        mutation_claimed = self._mutation_lock.acquire(blocking=False)
        if not mutation_claimed:
            self._finish_task(
                task_id,
                status="failed",
                phase="failed",
                error_code="cutout_model_mutation_busy",
                message="抠图模型文件正在被其他操作使用",
            )
            return
        try:
            self._update_task(
                task_id,
                status="downloading",
                phase="downloading",
                progress=1,
                message="正在下载抠图模型",
            )
            part_path = await asyncio.wait_for(
                self._download_to_part(task_id, cancel_event),
                timeout=self.timeout_seconds,
            )
            if cancel_event.is_set():
                raise _DownloadCancelled()
            self._update_task(
                task_id,
                status="installing",
                phase="installing",
                progress=96,
                message="正在安装抠图模型",
            )
            await self._acquire_model_operation_for_install(cancel_event)
            try:
                if cancel_event.is_set():
                    raise _DownloadCancelled()
                os.replace(part_path, self.model_path)
                part_path = None
                self.adapter.invalidate_session()
            finally:
                self.adapter.release_model_operation()
            self._finish_task(
                task_id,
                status="completed",
                phase="completed",
                progress=100,
                error_code=None,
                message="抠图模型安装完成",
            )
        except (asyncio.CancelledError, _DownloadCancelled):
            self._finish_task(
                task_id,
                status="cancelled",
                phase="cancelled",
                error_code=None,
                message="抠图模型下载已取消",
            )
        except asyncio.TimeoutError:
            self._finish_task(
                task_id,
                status="failed",
                phase="failed",
                error_code="cutout_model_download_timeout",
                message="抠图模型下载超时",
            )
        except CutoutModelManagerError as exc:
            self._finish_task(
                task_id,
                status="failed",
                phase="failed",
                error_code=exc.code,
                message=exc.message,
            )
        except Exception:
            self._finish_task(
                task_id,
                status="failed",
                phase="failed",
                error_code="cutout_model_install_failed",
                message="抠图模型安装失败",
            )
        finally:
            if part_path is not None:
                try:
                    part_path.unlink(missing_ok=True)
                except OSError:
                    pass
            self._mutation_lock.release()

    async def _acquire_model_operation_for_install(
        self, cancel_event: threading.Event
    ) -> None:
        deadline = time.monotonic() + self.install_lock_timeout_seconds
        while not self.adapter.acquire_model_operation():
            if cancel_event.is_set():
                raise _DownloadCancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CutoutModelManagerError(
                    "cutout_model_inference_busy",
                    "本地抠图推理持续占用模型，安装已安全终止",
                    status_code=409,
                )
            await asyncio.sleep(min(0.05, remaining))

    async def _download_to_part(self, task_id: str, cancel_event: threading.Event) -> Path:
        expected_size, expected_sha, expected_md5, _filename = self._expected()
        current_url = self.download_url
        part_path: Optional[Path] = None
        try:
            async with self._make_client() as client:
                for redirect_count in range(self.max_redirects + 1):
                    parsed = self._validated_url(current_url, initial=redirect_count == 0)
                    await asyncio.to_thread(self._verify_public_dns, str(parsed.hostname))
                    if cancel_event.is_set():
                        raise _DownloadCancelled()
                    try:
                        async with client.stream("GET", current_url) as response:
                            if response.status_code in {301, 302, 303, 307, 308}:
                                if redirect_count >= self.max_redirects:
                                    raise CutoutModelManagerError(
                                        "cutout_model_redirect_limit",
                                        "抠图模型下载重定向次数过多",
                                    )
                                location = response.headers.get("location")
                                if not location:
                                    raise CutoutModelManagerError(
                                        "cutout_model_redirect_rejected",
                                        "抠图模型下载重定向无效",
                                    )
                                next_url = urljoin(current_url, location)
                                self._validated_url(next_url, initial=False)
                                current_url = next_url
                                continue
                            if response.status_code != 200:
                                raise CutoutModelManagerError(
                                    "cutout_model_download_failed",
                                    "抠图模型下载失败",
                                )
                            content_encoding = response.headers.get("content-encoding", "").strip().lower()
                            if content_encoding not in {"", "identity"}:
                                raise CutoutModelManagerError(
                                    "cutout_model_content_encoding_rejected",
                                    "抠图模型下载响应编码不受支持",
                                )
                            raw_length = response.headers.get("content-length")
                            if raw_length is not None:
                                raw_length = raw_length.strip()
                                if not raw_length or not raw_length.isdigit():
                                    raise CutoutModelManagerError(
                                        "cutout_model_content_length_invalid",
                                        "抠图模型下载大小声明无效",
                                    )
                                declared_length = int(raw_length)
                                if declared_length != expected_size:
                                    raise CutoutModelManagerError(
                                        "cutout_model_size_mismatch",
                                        "抠图模型下载大小校验失败",
                                    )
                            part_path, part_handle = self._open_part()
                            sha256 = hashlib.sha256()
                            md5 = hashlib.md5()
                            downloaded = 0
                            with part_handle as handle:
                                async for chunk in response.aiter_raw(MODEL_DOWNLOAD_CHUNK_BYTES):
                                    if cancel_event.is_set():
                                        raise _DownloadCancelled()
                                    if not chunk:
                                        continue
                                    downloaded += len(chunk)
                                    if downloaded > expected_size:
                                        raise CutoutModelManagerError(
                                            "cutout_model_size_exceeded",
                                            "抠图模型下载超过固定大小上限",
                                        )
                                    handle.write(chunk)
                                    sha256.update(chunk)
                                    md5.update(chunk)
                                    progress = min(90, max(1, int(downloaded * 90 / expected_size)))
                                    self._update_task(
                                        task_id,
                                        downloaded_bytes=downloaded,
                                        progress=progress,
                                    )
                                handle.flush()
                                os.fsync(handle.fileno())
                            self._update_task(
                                task_id,
                                status="verifying",
                                phase="verifying",
                                progress=93,
                                downloaded_bytes=downloaded,
                                message="正在校验抠图模型",
                            )
                            if downloaded != expected_size:
                                raise CutoutModelManagerError(
                                    "cutout_model_size_mismatch",
                                    "抠图模型下载大小校验失败",
                                )
                            if (
                                sha256.hexdigest().lower() != expected_sha
                                or md5.hexdigest().lower() != expected_md5
                            ):
                                raise CutoutModelManagerError(
                                    "cutout_model_hash_mismatch",
                                    "抠图模型下载完整性校验失败",
                                )
                            return part_path
                    except httpx.TimeoutException as exc:
                        raise CutoutModelManagerError(
                            "cutout_model_download_timeout",
                            "抠图模型下载超时",
                        ) from exc
                    except httpx.HTTPError as exc:
                        raise CutoutModelManagerError(
                            "cutout_model_download_failed",
                            "抠图模型下载失败",
                        ) from exc
            raise CutoutModelManagerError(
                "cutout_model_redirect_limit",
                "抠图模型下载重定向次数过多",
            )
        except BaseException:
            if part_path is not None:
                try:
                    part_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def delete_model(self) -> dict[str, Any]:
        if not self._mutation_lock.acquire(blocking=False):
            raise CutoutModelManagerError(
                "cutout_model_mutation_busy",
                "抠图模型下载或删除正在进行",
                status_code=409,
            )
        try:
            if not self.adapter.acquire_model_operation():
                raise CutoutModelManagerError(
                    "cutout_model_inference_busy",
                    "本地抠图正在处理请求，请稍后删除模型",
                    status_code=409,
                )
            try:
                existed = self.model_path.exists() or self.model_path.is_symlink()
                if existed:
                    try:
                        self.model_path.unlink()
                    except OSError as exc:
                        raise CutoutModelManagerError(
                            "cutout_model_delete_failed",
                            "抠图模型删除失败",
                        ) from exc
                    self.adapter.invalidate_session()
                return {"deleted": bool(existed), "model": self.model_status()}
            finally:
                self.adapter.release_model_operation()
        finally:
            self._mutation_lock.release()


__all__ = [
    "CutoutModelManager",
    "CutoutModelManagerError",
    "MODEL_DOWNLOAD_HOSTS",
    "MODEL_DOWNLOAD_URL",
    "MODEL_INSTALL_LOCK_TIMEOUT_SECONDS",
    "MODEL_INSTALL_CONTRACT",
    "MODEL_SOURCE_ID",
    "MODEL_SOURCE_PAGE",
]
