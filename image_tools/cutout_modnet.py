"""Opt-in MODNet ONNX cutout adapter.

This adapter is intentionally not registered by the default GenBox registry.
It is for a user-provided MODNet checkpoint only.  A caller must provide a
complete file manifest and explicitly confirm responsibility for the
checkpoint's license before the adapter reports an executable capability.
The implementation keeps the same bounded image, CPU-only, timeout and
atomic-save boundaries as the verified U2-Net adapter without changing that
adapter or the shared registry contract.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import io
import math
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Optional

from image_tools.cutout_onnx import (
    CUTOUT_CONTRACT,
    CutoutAdapterError,
    CutoutBusyError,
    CutoutOutputError,
    CutoutPersistenceError,
    CutoutTimeoutError,
    CutoutUnavailableError,
    validate_input_image,
    validate_output_png,
)
from image_tools.cutout_modnet_import import (
    DEFAULT_MODEL_FILENAME,
    MODNET_IMPORT_DIR,
)


MODNET_ADAPTER_ID = "modnet-portrait-onnx"
MODNET_ALGORITHM = "MODNet photographic portrait matting ONNX"
# Keep runtime discovery aligned with the canonical import manager location.
MODNET_MODEL_RELATIVE_PATH = MODNET_IMPORT_DIR / DEFAULT_MODEL_FILENAME
DEFAULT_TIMEOUT_SECONDS = 45.0
MIN_TIMEOUT_SECONDS = 0.25
MAX_TIMEOUT_SECONDS = 180.0


def _bounded_timeout(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS
    if not math.isfinite(parsed):
        return DEFAULT_TIMEOUT_SECONDS
    return max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, parsed))


def _runtime_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _hash_file(path: Path) -> tuple[int, str, str]:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            sha256.update(chunk)
            md5.update(chunk)
    return size, sha256.hexdigest().lower(), md5.hexdigest().lower()


def _unavailable(code: str, message: str, *, state: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contract": CUTOUT_CONTRACT,
        "available": False,
        "executable": False,
        "adapters": [],
        "adapter": MODNET_ADAPTER_ID,
        "algorithm": MODNET_ALGORITHM,
        "state": state,
        "reason": code,
        "code": code,
        "message": message,
        "cancel_supported": False,
    }
    payload.update(extra)
    return payload


class ModNetONNXAdapter:
    """Explicitly opt-in, single-flight CPU-only MODNet adapter."""

    adapter_id = MODNET_ADAPTER_ID
    algorithm = MODNET_ALGORITHM
    contract = CUTOUT_CONTRACT

    def __init__(
        self,
        model_path: Optional[os.PathLike[str] | str] = None,
        *,
        base_path: Optional[os.PathLike[str] | str] = None,
        model_manifest: Optional[Mapping[str, Any]] = None,
        license_confirmed: bool = False,
        license_source: Optional[str] = None,
        timeout_seconds: object = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        root = Path(base_path) if base_path is not None else _runtime_base_path()
        self.base_path = root.resolve()
        self.model_path = (
            Path(model_path)
            if model_path is not None
            else self.base_path / MODNET_MODEL_RELATIVE_PATH
        ).resolve()
        self.expected_manifest = dict(model_manifest or {})
        self.license_confirmed = bool(license_confirmed)
        self.license_source = str(license_source or "").strip()
        self.timeout_seconds = _bounded_timeout(timeout_seconds)
        self._session: Any = None
        self._session_fingerprint: Optional[tuple[int, str, str]] = None
        self._session_input_name: Optional[str] = None
        self._session_input_size: tuple[int, int] = (512, 288)
        self._ort: Any = None
        self._numpy: Any = None
        self._session_lock = threading.Lock()
        self._flight_lock = threading.Lock()

    @property
    def busy(self) -> bool:
        return self._flight_lock.locked()

    def acquire_model_operation(self) -> bool:
        return self._flight_lock.acquire(blocking=False)

    def release_model_operation(self) -> None:
        try:
            self._flight_lock.release()
        except RuntimeError:
            pass

    def invalidate_session(self) -> None:
        with self._session_lock:
            self._session = None
            self._session_fingerprint = None
            self._session_input_name = None
            self._session_input_size = (512, 288)

    def _manifest_expected(self) -> tuple[int, str, str]:
        try:
            size = int(self.expected_manifest["size_bytes"])
            sha256 = str(self.expected_manifest["sha256"]).lower()
            md5 = str(self.expected_manifest["md5"]).lower()
            filename = str(self.expected_manifest["filename"]).strip()
        except (KeyError, TypeError, ValueError):
            raise CutoutUnavailableError(
                "modnet_model_manifest_invalid",
                "MODNet 权重清单不完整，无法安全启用",
                state="needs_model",
                needs_model=True,
            ) from None
        if (
            size <= 0
            or not filename
            or Path(filename).name != filename
            or not re.fullmatch(r"[0-9a-f]{64}", sha256)
            or not re.fullmatch(r"[0-9a-f]{32}", md5)
        ):
            raise CutoutUnavailableError(
                "modnet_model_manifest_invalid",
                "MODNet 权重清单不完整，无法安全启用",
                state="needs_model",
                needs_model=True,
            )
        return size, sha256, md5

    def validate_model_artifact(self) -> dict[str, Any]:
        expected_size, expected_sha, expected_md5 = self._manifest_expected()
        if not self.license_confirmed:
            raise CutoutUnavailableError(
                "modnet_license_unconfirmed",
                "请先确认你自行取得的 MODNet 权重许可，再启用该算法",
                state="needs_license_confirmation",
                needs_model=True,
            )
        try:
            if self.model_path.is_symlink() or not self.model_path.is_file():
                raise CutoutUnavailableError(
                    "modnet_model_missing",
                    "尚未找到用户提供的 MODNet 权重",
                    state="needs_model",
                    needs_model=True,
                )
            actual_size, actual_sha, actual_md5 = _hash_file(self.model_path)
        except CutoutAdapterError:
            raise
        except (OSError, ValueError):
            raise CutoutUnavailableError(
                "modnet_model_unreadable",
                "MODNet 权重不可读取",
                state="needs_model",
                needs_model=True,
            ) from None
        if actual_size != expected_size:
            raise CutoutUnavailableError(
                "modnet_model_size_mismatch",
                "MODNet 权重大小校验失败",
                state="needs_model",
                needs_model=True,
            )
        if actual_sha != expected_sha or actual_md5 != expected_md5:
            raise CutoutUnavailableError(
                "modnet_model_hash_mismatch",
                "MODNet 权重完整性校验失败",
                state="needs_model",
                needs_model=True,
            )
        return {
            "size_bytes": actual_size,
            "sha256": actual_sha,
            "md5": actual_md5,
            "fingerprint": (actual_size, actual_sha, actual_md5),
        }

    def _load_dependencies(self) -> tuple[Any, Any]:
        if self._ort is not None and self._numpy is not None:
            return self._ort, self._numpy
        try:
            ort = importlib.import_module("onnxruntime")
            numpy = importlib.import_module("numpy")
        except Exception:
            raise CutoutUnavailableError(
                "cutout_dependency_missing",
                "本地 MODNet 运行依赖不可用，请安装 onnxruntime 与 numpy",
                state="needs_dependency",
                needs_dependency=True,
            ) from None
        self._ort = ort
        self._numpy = numpy
        return ort, numpy

    @staticmethod
    def _known_dimension(value: object, fallback: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        return parsed if parsed > 0 else fallback

    def _load_session(self, manifest: Mapping[str, Any]) -> dict[str, Any]:
        fingerprint = tuple(manifest["fingerprint"])
        with self._session_lock:
            if self._session is not None and self._session_fingerprint == fingerprint:
                return {
                    "session": self._session,
                    "numpy": self._numpy,
                    "input_name": self._session_input_name,
                    "input_size": self._session_input_size,
                }
            ort, numpy = self._load_dependencies()
            try:
                session = ort.InferenceSession(
                    str(self.model_path), providers=["CPUExecutionProvider"]
                )
                if list(session.get_providers()) != ["CPUExecutionProvider"]:
                    raise CutoutUnavailableError(
                        "cutout_cpu_provider_required",
                        "本地 MODNet 仅允许 CPUExecutionProvider",
                        state="unavailable",
                    )
                inputs = list(session.get_inputs())
                outputs = list(session.get_outputs())
                if len(inputs) != 1 or not outputs:
                    raise CutoutUnavailableError(
                        "modnet_session_invalid",
                        "MODNet 模型会话结构无效",
                        state="unavailable",
                    )
                info = inputs[0]
                shape = list(getattr(info, "shape", []) or [])
                if len(shape) != 4 or self._known_dimension(shape[1], 3) != 3:
                    raise CutoutUnavailableError(
                        "modnet_session_invalid",
                        "MODNet 模型输入结构无效",
                        state="unavailable",
                    )
                height = self._known_dimension(shape[2], 288)
                width = self._known_dimension(shape[3], 512)
                name = str(getattr(info, "name", "") or "")
                if not name:
                    raise CutoutUnavailableError(
                        "modnet_session_invalid",
                        "MODNet 模型输入名称无效",
                        state="unavailable",
                    )
            except CutoutAdapterError:
                self._session = None
                self._session_fingerprint = None
                raise
            except Exception:
                self._session = None
                self._session_fingerprint = None
                raise CutoutUnavailableError(
                    "modnet_session_unavailable",
                    "MODNet 模型会话无法启动",
                    state="unavailable",
                ) from None
            self._session = session
            self._session_fingerprint = fingerprint
            self._session_input_name = name
            self._session_input_size = (width, height)
            return {
                "session": session,
                "numpy": numpy,
                "input_name": name,
                "input_size": (width, height),
            }

    def capabilities(self) -> dict[str, Any]:
        if not self.acquire_model_operation():
            return _unavailable("cutout_busy", "本地 MODNet 正在使用中", state="busy", busy=True)
        try:
            try:
                manifest = self.validate_model_artifact()
                info = self._load_session(manifest)
            except CutoutAdapterError as exc:
                return _unavailable(
                    exc.code,
                    exc.message,
                    state=str(exc.details.get("state") or "unavailable"),
                    needs_model=bool(exc.details.get("needs_model", False)),
                    needs_dependency=bool(exc.details.get("needs_dependency", False)),
                    license_confirmed=self.license_confirmed,
                )
            return {
                "contract": CUTOUT_CONTRACT,
                "available": True,
                "executable": True,
                "adapters": [MODNET_ADAPTER_ID],
                "adapter": MODNET_ADAPTER_ID,
                "algorithm": MODNET_ALGORITHM,
                "state": "ready",
                "reason": None,
                "needs_model": False,
                "needs_dependency": False,
                "license_confirmed": True,
                "license_source": self.license_source or None,
                "cpu_execution_provider": True,
                "cancel_supported": False,
                "timeout_seconds": self.timeout_seconds,
                "input_size": list(info["input_size"]),
                "model": {
                    "filename": self.expected_manifest["filename"],
                    "size_bytes": int(manifest["size_bytes"]),
                    "sha256": str(manifest["sha256"]),
                    "md5": str(manifest["md5"]),
                },
            }
        finally:
            self.release_model_operation()

    capability = capabilities
    get_capabilities = capabilities
    probe = capabilities

    def _run_inference(self, decoded: Mapping[str, Any], session_info: Mapping[str, Any]) -> dict[str, Any]:
        from PIL import Image

        numpy = session_info["numpy"]
        session = session_info["session"]
        input_name = str(session_info["input_name"])
        input_width, input_height = tuple(session_info["input_size"])
        width, height = int(decoded["width"]), int(decoded["height"])
        try:
            with Image.open(io.BytesIO(bytes(decoded["bytes"]))) as source:
                rgb = source.convert("RGB")
            resized = rgb.resize((input_width, input_height), Image.Resampling.LANCZOS)
            array = numpy.asarray(resized, dtype=numpy.float32) / 255.0
            array = (array - 0.5) / 0.5
            tensor = numpy.transpose(array, (2, 0, 1))[None, ...]
            outputs = session.run(None, {input_name: tensor})
            if not outputs:
                raise CutoutOutputError("cutout_output_invalid", "MODNet 模型返回空结果")
            mask = numpy.squeeze(numpy.asarray(outputs[0], dtype=numpy.float32))
            if mask.ndim != 2 or mask.size == 0 or not bool(numpy.isfinite(mask).all()):
                raise CutoutOutputError("cutout_output_invalid", "MODNet 返回了无法识别的掩码")
            low, high = float(mask.min()), float(mask.max())
            if not math.isfinite(low) or not math.isfinite(high) or high <= low:
                raise CutoutOutputError("cutout_output_alpha_invalid", "MODNet 没有产生有效透明区域")
            if low < 0.0 or high > 1.0:
                mask = 1.0 / (1.0 + numpy.exp(-numpy.clip(mask, -40.0, 40.0)))
                low, high = float(mask.min()), float(mask.max())
            normalized = numpy.clip((mask - low) / max(high - low, 1e-6), 0.0, 1.0)
            # Preserve the model's soft matte while making the PNG contract
            # deterministic: quantization must retain explicit transparent
            # and opaque endpoints for downstream validation/compositing.
            quantized = numpy.rint(normalized * 255.0).astype(numpy.uint8)
            if low <= 0.05:
                quantized[normalized <= 0.05] = 0
            if high >= 0.95:
                quantized[normalized >= 0.95] = 255
            alpha = numpy.asarray(
                Image.fromarray(quantized, mode="L")
                .resize((width, height), Image.Resampling.BILINEAR),
                dtype=numpy.uint8,
            )
            if alpha.size < 2:
                raise CutoutOutputError("cutout_output_alpha_invalid", "抠图输出像素不足")
            rgba = rgb.convert("RGBA")
            rgba.putalpha(Image.fromarray(alpha, mode="L"))
            output = io.BytesIO()
            rgba.save(output, format="PNG", optimize=False)
            png_bytes = output.getvalue()
        except CutoutAdapterError:
            raise
        except Exception:
            raise CutoutOutputError("cutout_output_invalid", "MODNet 输出处理失败") from None
        validate_output_png(png_bytes, (width, height))
        return {
            "image_bytes": png_bytes,
            "width": width,
            "height": height,
            "adapter": MODNET_ADAPTER_ID,
        }

    def _process_claimed(self, decoded: Mapping[str, Any], session_info: Mapping[str, Any]) -> dict[str, Any]:
        try:
            started = time.monotonic()
            result = self._run_inference(decoded, session_info)
            result["elapsed_seconds"] = round(max(0.0, time.monotonic() - started), 3)
            return result
        finally:
            self.release_model_operation()

    def process(self, image_data: object) -> dict[str, Any]:
        if not self.acquire_model_operation():
            raise CutoutBusyError()
        try:
            manifest = self.validate_model_artifact()
            session_info = self._load_session(manifest)
            decoded = validate_input_image(image_data)
        except BaseException:
            self.release_model_operation()
            raise
        return self._process_claimed(decoded, session_info)

    async def process_async(self, image_data: object, *, timeout_seconds: object = None) -> dict[str, Any]:
        if not self.acquire_model_operation():
            raise CutoutBusyError()
        try:
            manifest = await asyncio.to_thread(self.validate_model_artifact)
            session_info = await asyncio.to_thread(self._load_session, manifest)
            decoded = validate_input_image(image_data)
            future = asyncio.create_task(asyncio.to_thread(self._process_claimed, decoded, session_info))
        except BaseException:
            self.release_model_operation()
            raise
        timeout = self.timeout_seconds if timeout_seconds is None else _bounded_timeout(timeout_seconds)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
        except asyncio.TimeoutError:
            future.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)
            raise CutoutTimeoutError(timeout) from None

    async def run(self, image_data: object, *, timeout_seconds: object = None) -> dict[str, Any]:
        return await self.process_async(image_data, timeout_seconds=timeout_seconds)

    execute = run

    def save_atomic(self, png_bytes: object, gallery_dir: os.PathLike[str] | str, *, expected_size: Optional[tuple[int, int]] = None) -> Path:
        checked = validate_output_png(png_bytes, expected_size)
        directory = Path(gallery_dir)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir():
                raise OSError("gallery is not a directory")
            filename = f"cutout_modnet_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:12]}.png"
            target = directory / filename
            temporary = directory / f".{filename}.{uuid.uuid4().hex}.tmp"
            with temporary.open("xb") as handle:
                handle.write(checked["bytes"])
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(str(temporary), str(target))
            return target
        except CutoutAdapterError:
            raise
        except Exception:
            try:
                if "temporary" in locals() and temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
            raise CutoutPersistenceError() from None


__all__ = [
    "MODNET_ADAPTER_ID",
    "MODNET_ALGORITHM",
    "MODNET_MODEL_RELATIVE_PATH",
    "ModNetONNXAdapter",
]
