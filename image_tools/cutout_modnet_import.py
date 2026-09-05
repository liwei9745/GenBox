"""Fail-closed import manager for an optional, user-provided MODNet ONNX model.

This is the single authoritative MODNet import implementation. It accepts file
content only, never a server path or remote URL, stores the checkpoint in an
isolated directory, verifies the caller's manifest, and atomically publishes the
model plus a non-secret manifest. Importing does not register MODNet in the
default U2-Net registry; runtime probing remains an explicit later step.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import tempfile
import threading
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Mapping, Optional

MODNET_IMPORT_CONTRACT = "genbox-cutout-modnet-import-v1"
MODNET_IMPORT_DIR = Path("storage/models/cutout/modnet")
DEFAULT_MAX_BYTES = 512 * 1024 * 1024
MAX_MODNET_MODEL_BYTES = DEFAULT_MAX_BYTES
DEFAULT_MODEL_FILENAME = "modnet.onnx"
MODNET_MODEL_FILENAME = DEFAULT_MODEL_FILENAME
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.onnx$", re.IGNORECASE)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_MD5_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


class ModNetImportError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.status_code = int(status_code)

    def to_detail(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "contract": MODNET_IMPORT_CONTRACT}


@dataclass(frozen=True)
class ModNetImportResult:
    model_path: Path
    manifest_path: Path
    filename: str
    size_bytes: int
    sha256: str
    md5: str
    license_confirmed: bool
    license_source: str

    def as_dict(self) -> dict[str, Any]:
        # Deliberately omit model_path/manifest_path from public payloads.
        return {
            "ok": True,
            "contract": MODNET_IMPORT_CONTRACT,
            "adapter": "modnet-portrait-onnx",
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "md5": self.md5,
            "license_confirmed": self.license_confirmed,
            "license_source": self.license_source or None,
            "state": "imported",
            "executable": False,
            "runtime_probe_required": True,
        }


def _reject_source(value: object) -> None:
    if isinstance(value, (str, os.PathLike)):
        raise ModNetImportError("modnet_upload_content_required", "只允许上传模型文件内容，不接受服务器路径或 URL")


def _safe_filename(filename: object) -> str:
    raw = str(filename or "").strip()
    name = Path(raw).name
    if not raw or name != raw or "\\" in raw or not _SAFE_NAME.fullmatch(name):
        raise ModNetImportError("modnet_filename_invalid", "模型文件名必须是安全的 .onnx 文件名")
    return name


def _license(license_confirmed: object, license_source: object) -> tuple[bool, str]:
    if license_confirmed is not True:
        raise ModNetImportError("modnet_license_unconfirmed", "请明确确认你拥有该 MODNet 权重的使用许可")
    source = str(license_source or "").strip()
    if len(source) > 512:
        raise ModNetImportError("modnet_license_source_invalid", "许可来源说明过长")
    return True, source


def _expected_manifest(expected: Optional[Mapping[str, Any]], *, actual_size: int, sha256: str, md5: str) -> None:
    if expected is None:
        return
    try:
        expected_size = int(expected["size_bytes"])
        expected_sha = str(expected["sha256"]).strip().lower()
        expected_md5 = str(expected["md5"]).strip().lower()
    except (KeyError, TypeError, ValueError):
        raise ModNetImportError("modnet_manifest_invalid", "模型清单必须包含文件大小、SHA-256 和 MD5") from None
    if expected_size != actual_size or expected_sha != sha256.lower() or expected_md5 != md5.lower():
        raise ModNetImportError("modnet_manifest_mismatch", "模型清单与上传内容不匹配")


class ModNetModelImportManager:
    def __init__(self, *, base_path: os.PathLike[str] | str, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        try:
            limit = int(max_bytes)
        except (TypeError, ValueError):
            raise ModNetImportError("modnet_import_limit_invalid", "模型大小限制无效") from None
        if limit <= 0 or limit > DEFAULT_MAX_BYTES:
            raise ModNetImportError("modnet_import_limit_invalid", "模型大小限制必须在 1 至 512 MB 之间")
        self.base_path = Path(base_path).resolve()
        # Keep the managed directory lexical so a pre-existing symlink remains
        # observable and can be rejected before any upload touches it.
        self.model_dir = self.base_path / MODNET_IMPORT_DIR
        self.model_path = self.model_dir / DEFAULT_MODEL_FILENAME
        self.manifest_path = self.model_dir / (DEFAULT_MODEL_FILENAME + ".manifest.json")
        self.max_bytes = limit
        self._lock = threading.RLock()

    def _prepare_dirs(self) -> None:
        if self.model_dir.is_symlink() or (self.model_dir.exists() and not self.model_dir.is_dir()):
            raise ModNetImportError("modnet_import_directory_invalid", "MODNet 模型目录不可用", status_code=500)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        if self.model_dir.is_symlink() or not self.model_dir.is_dir():
            raise ModNetImportError("modnet_import_directory_invalid", "MODNet 模型目录不可用", status_code=500)

    @staticmethod
    def _hash_file(path: Path) -> tuple[int, str, str]:
        sha, md5 = hashlib.sha256(), hashlib.md5()
        total = 0
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                sha.update(chunk)
                md5.update(chunk)
        return total, sha.hexdigest(), md5.hexdigest()

    def _public_status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "ok": True, "contract": MODNET_IMPORT_CONTRACT, "adapter": "modnet-portrait-onnx",
            "installed": False, "valid": False, "executable": False, "state": "missing",
            "reason": "modnet_model_missing", "filename": DEFAULT_MODEL_FILENAME, "size_bytes": 0,
            "sha256": None, "md5": None, "license_confirmed": False, "license_source": None,
            "runtime_probe_required": True,
        }
        if self.model_path.is_symlink() or self.manifest_path.is_symlink():
            status.update(state="invalid", reason="modnet_target_symlink")
            return status
        if not self.model_path.is_file() or not self.manifest_path.is_file():
            return status
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError
            filename = _safe_filename(manifest.get("filename"))
            size = int(manifest["size_bytes"])
            sha = str(manifest["sha256"]).lower()
            md5 = str(manifest["md5"]).lower()
            confirmed, source = _license(manifest.get("license_confirmed"), manifest.get("license_source"))
            if size <= 0 or size > self.max_bytes or not _SHA256_RE.fullmatch(sha) or not _MD5_RE.fullmatch(md5):
                raise ValueError
            actual_size, actual_sha, actual_md5 = self._hash_file(self.model_path)
            valid = actual_size == size and actual_sha == sha and actual_md5 == md5
            status.update(installed=True, valid=valid, state="imported" if valid else "invalid",
                          reason=None if valid else "modnet_manifest_mismatch", filename=filename,
                          size_bytes=size, sha256=sha, md5=md5, license_confirmed=confirmed,
                          license_source=source or None)
        except Exception:
            status.update(installed=True, state="invalid", reason="modnet_manifest_invalid")
        return status

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._public_status()

    def manifest(self) -> Optional[dict[str, Any]]:
        with self._lock:
            status = self._public_status()
            if not status["installed"] or not status["valid"]:
                return None
            return {key: status[key] for key in ("filename", "size_bytes", "sha256", "md5")}

    def _write_and_hash(self, source: BinaryIO) -> tuple[Path, int, str, str]:
        self._prepare_dirs()
        temp_name: Optional[str] = None
        sha, md5 = hashlib.sha256(), hashlib.md5()
        total = 0
        try:
            fd, temp_name = tempfile.mkstemp(prefix=".modnet-upload-", suffix=".tmp", dir=self.model_dir)
            temp_path = Path(temp_name)
            if temp_path.is_symlink() or not temp_path.is_file():
                raise ModNetImportError("modnet_temp_invalid", "拒绝使用异常临时文件")
            with os.fdopen(fd, "wb") as handle:
                while True:
                    chunk = source.read(1024 * 1024)
                    if inspect.isawaitable(chunk):
                        raise ModNetImportError("modnet_upload_async_required", "异步上传必须使用异步导入接口")
                    if chunk in (b"", None):
                        break
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        raise ModNetImportError("modnet_upload_invalid", "上传内容必须是二进制文件")
                    data = bytes(chunk)
                    total += len(data)
                    if total > self.max_bytes:
                        raise ModNetImportError("modnet_model_too_large", "MODNet 模型超过允许大小", status_code=413)
                    handle.write(data)
                    sha.update(data)
                    md5.update(data)
                handle.flush()
                os.fsync(handle.fileno())
            if total <= 0:
                raise ModNetImportError("modnet_model_empty", "MODNet 模型文件不能为空")
            return temp_path, total, sha.hexdigest(), md5.hexdigest()
        except ModNetImportError:
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)
            raise
        except (OSError, ValueError):
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)
            raise ModNetImportError("modnet_upload_failed", "MODNet 模型上传失败", status_code=500) from None

    def _publish_pair(self, model_tmp: Path, manifest_tmp: Path) -> None:
        targets = (self.model_path, self.manifest_path)
        backups: dict[Path, Path] = {}
        published: set[Path] = set()
        try:
            for target in targets:
                if not target.exists():
                    continue
                if target.is_symlink() or not target.is_file():
                    raise ModNetImportError("modnet_target_invalid", "拒绝覆盖异常模型目标", status_code=409)
                backup = self.model_dir / f".{target.name}.{uuid.uuid4().hex}.bak"
                os.replace(str(target), str(backup))
                backups[target] = backup

            os.replace(str(model_tmp), str(self.model_path))
            published.add(self.model_path)
            os.replace(str(manifest_tmp), str(self.manifest_path))
            published.add(self.manifest_path)
        except ModNetImportError:
            if not self._rollback_pair(targets, backups, published):
                raise ModNetImportError(
                    "modnet_import_rollback_failed",
                    "MODNet 模型导入失败，旧模型备份已保留以便恢复",
                    status_code=500,
                ) from None
            raise
        except (OSError, ValueError):
            rollback_ok = self._rollback_pair(targets, backups, published)
            if not rollback_ok:
                raise ModNetImportError(
                    "modnet_import_rollback_failed",
                    "MODNet 模型导入失败，旧模型备份已保留以便恢复",
                    status_code=500,
                ) from None
            raise ModNetImportError("modnet_import_failed", "MODNet 模型导入失败", status_code=500) from None
        else:
            for backup in backups.values():
                try:
                    backup.unlink(missing_ok=True)
                except OSError:
                    # The new pair is already committed; a stale hidden backup
                    # must not turn a successful import into a false failure.
                    pass

    @staticmethod
    def _rollback_pair(
        targets: tuple[Path, Path],
        backups: Mapping[Path, Path],
        published: set[Path],
    ) -> bool:
        rollback_ok = True
        for target in reversed(targets):
            if target not in published:
                continue
            try:
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    raise OSError
                target.unlink(missing_ok=True)
            except OSError:
                rollback_ok = False
        for target in targets:
            backup = backups.get(target)
            if backup is None:
                continue
            try:
                os.replace(str(backup), str(target))
            except OSError:
                rollback_ok = False
        return rollback_ok

    def import_content(self, content: object, *, filename: str = DEFAULT_MODEL_FILENAME,
                       license_confirmed: object = False, license_source: object = "",
                       expected: Optional[Mapping[str, Any]] = None) -> ModNetImportResult:
        _reject_source(content)
        safe_name = _safe_filename(filename)
        confirmed, source = _license(license_confirmed, license_source)
        if not hasattr(content, "read"):
            raise ModNetImportError("modnet_upload_content_required", "请上传模型文件内容")
        with self._lock:
            temp_path, size, sha256, md5 = self._write_and_hash(content)  # type: ignore[arg-type]
            manifest_tmp: Optional[Path] = None
            try:
                _expected_manifest(expected, actual_size=size, sha256=sha256, md5=md5)
                if self.model_path.is_symlink() or self.manifest_path.is_symlink():
                    raise ModNetImportError("modnet_target_symlink", "拒绝覆盖符号链接目标", status_code=409)
                manifest = {"contract": MODNET_IMPORT_CONTRACT, "filename": safe_name, "size_bytes": size,
                            "sha256": sha256, "md5": md5, "license_confirmed": confirmed,
                            "license_source": source}
                manifest_tmp = self.model_dir / f".{self.manifest_path.name}.{uuid.uuid4().hex}.tmp"
                # The manifest is JSON text; use exclusive text mode so the
                # encoding argument is valid while preserving no-clobber
                # creation before the atomic replace below.
                with manifest_tmp.open("x", encoding="utf-8", newline="") as handle:
                    json.dump(manifest, handle, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
                    handle.flush()
                    os.fsync(handle.fileno())
                self._publish_pair(temp_path, manifest_tmp)
                return ModNetImportResult(self.model_path, self.manifest_path, safe_name, size, sha256, md5, confirmed, source)
            except ModNetImportError:
                raise
            except (OSError, ValueError):
                raise ModNetImportError("modnet_import_failed", "MODNet 模型导入失败", status_code=500) from None
            finally:
                temp_path.unlink(missing_ok=True)
                if manifest_tmp is not None:
                    manifest_tmp.unlink(missing_ok=True)

    def import_bytes(self, content: bytes, **kwargs: Any) -> ModNetImportResult:
        return self.import_content(BytesIO(content), **kwargs)

    async def import_upload(self, upload: object, **kwargs: Any) -> ModNetImportResult:
        if upload is None or not hasattr(upload, "read"):
            raise ModNetImportError("modnet_upload_content_required", "请上传模型文件内容")
        filename = kwargs.pop("filename", None) or getattr(upload, "filename", None) or DEFAULT_MODEL_FILENAME
        manifest_fields = {key: kwargs.pop(key) for key in ("size_bytes", "sha256", "md5") if key in kwargs}
        if manifest_fields:
            kwargs["expected"] = manifest_fields
        spool = tempfile.SpooledTemporaryFile(max_size=min(self.max_bytes, 8 * 1024 * 1024), mode="w+b")
        total = 0
        try:
            while True:
                chunk = upload.read(1024 * 1024)  # type: ignore[attr-defined]
                if inspect.isawaitable(chunk):
                    chunk = await chunk
                if chunk in (b"", None):
                    break
                if not isinstance(chunk, (bytes, bytearray, memoryview)):
                    raise ModNetImportError("modnet_upload_invalid", "上传内容必须是二进制文件")
                total += len(chunk)
                if total > self.max_bytes:
                    raise ModNetImportError("modnet_model_too_large", "MODNet 模型超过允许大小", status_code=413)
                spool.write(bytes(chunk))
            if total <= 0:
                raise ModNetImportError("modnet_model_empty", "MODNet 模型文件不能为空")
            spool.seek(0)
            return self.import_content(spool, filename=filename, **kwargs)
        finally:
            spool.close()

    def delete(self) -> dict[str, Any]:
        with self._lock:
            for path in (self.model_path, self.manifest_path):
                if path.is_symlink():
                    raise ModNetImportError("modnet_target_symlink", "拒绝删除符号链接目标", status_code=409)
            try:
                for path in (self.model_path, self.manifest_path):
                    if path.exists():
                        if not path.is_file():
                            raise OSError
                        path.unlink()
            except OSError:
                raise ModNetImportError("modnet_delete_failed", "MODNet 模型删除失败", status_code=500) from None
            return self._public_status()


ModNetModelManager = ModNetModelImportManager
ModNetModelManagerError = ModNetImportError

__all__ = [
    "DEFAULT_MAX_BYTES", "DEFAULT_MODEL_FILENAME", "MAX_MODNET_MODEL_BYTES",
    "MODNET_IMPORT_CONTRACT", "MODNET_IMPORT_DIR", "MODNET_MODEL_FILENAME",
    "ModNetImportError", "ModNetImportResult", "ModNetModelImportManager",
    "ModNetModelManager", "ModNetModelManagerError",
]
