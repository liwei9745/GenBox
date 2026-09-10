"""Fail-closed local U2Net human-segmentation adapter.

This module has no network path.  The model remains an ignored runtime artifact
and is accepted only when its embedded manifest matches exactly.  The bounded
installer lives in ``cutout_model_manager`` and coordinates file mutations with
this adapter's single-flight model-operation lock.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
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
import warnings
from pathlib import Path
from typing import Any, Mapping, Optional


CUTOUT_CONTRACT = "genbox-cutout-v1"
ADAPTER_ID = "u2net-human-seg-onnx"
MODEL_RELATIVE_PATH = Path("storage/models/cutout/u2net_human_seg.onnx")
MODEL_FILENAME = MODEL_RELATIVE_PATH.name
MODEL_SIZE_BYTES = 175_997_641
MODEL_SHA256 = "01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c"
MODEL_MD5 = "c09ddc2e0104f800e3e1bb4652583d1f"

# Descriptive aliases make the manifest easy to inspect in tests and tooling.
EXPECTED_MODEL_SIZE = MODEL_SIZE_BYTES
EXPECTED_MODEL_SHA256 = MODEL_SHA256
EXPECTED_MODEL_MD5 = MODEL_MD5
MODEL_MANIFEST = {
    "filename": MODEL_FILENAME,
    "relative_path": str(MODEL_RELATIVE_PATH).replace("\\", "/"),
    "size_bytes": MODEL_SIZE_BYTES,
    "sha256": MODEL_SHA256,
    "md5": MODEL_MD5,
}

DEFAULT_TIMEOUT_SECONDS = 45.0
MIN_TIMEOUT_SECONDS = 0.25
MAX_TIMEOUT_SECONDS = 180.0
MAX_INPUT_BYTES = int(os.getenv("GENBOX_CUTOUT_MAX_IMAGE_BYTES", str(25 * 1024 * 1024)))
MAX_INPUT_PIXELS = int(os.getenv("GENBOX_CUTOUT_MAX_IMAGE_PIXELS", "25000000"))
MAX_OUTPUT_BYTES = int(os.getenv("GENBOX_CUTOUT_MAX_OUTPUT_BYTES", str(25 * 1024 * 1024)))
_DATA_URL_RE = re.compile(
    r"^data:([A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+);base64$", re.IGNORECASE
)
_ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
_FORMAT_MIME_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def _runtime_base_path() -> Path:
    """Return the writable application directory, never PyInstaller's temp dir."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _bounded_timeout(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS
    if not math.isfinite(parsed):
        return DEFAULT_TIMEOUT_SECONDS
    return max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, parsed))


class CutoutAdapterError(RuntimeError):
    """A safe, structured local cutout failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 503,
        **details: Any,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.status_code = int(status_code)
        self.details = dict(details)

    def to_detail(self, *, adapter_id: str = ADAPTER_ID) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "contract": CUTOUT_CONTRACT,
            "available": False,
            "executable": False,
            "adapters": [],
            "adapter": adapter_id,
            "cancel_supported": False,
        }
        detail.update(self.details)
        return detail


class CutoutUnavailableError(CutoutAdapterError):
    pass


class CutoutBusyError(CutoutAdapterError):
    def __init__(self, message: str = "本地抠图正在处理另一个请求，请稍后重试") -> None:
        super().__init__("cutout_busy", message, status_code=409, busy=True)


class CutoutTimeoutError(CutoutAdapterError):
    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(
            "cutout_timeout",
            "本地抠图超过软超时时间；底层推理无法取消，仍会在后台收尾",
            status_code=504,
            timeout_seconds=round(float(timeout_seconds), 3),
            soft_timeout=True,
            cancel_supported=False,
            background_continues=True,
        )


class CutoutInputError(CutoutAdapterError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(code, message, status_code=422, **details)


class CutoutOutputError(CutoutAdapterError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(code, message, status_code=500, **details)


class CutoutPersistenceError(CutoutAdapterError):
    def __init__(self, message: str = "抠图结果保存失败") -> None:
        super().__init__("cutout_persistence_failed", message, status_code=500)


def _unavailable(
    code: str,
    message: str,
    *,
    state: str,
    needs_model: bool = False,
    needs_dependency: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contract": CUTOUT_CONTRACT,
        "available": False,
        "executable": False,
        "adapters": [],
        "adapter": ADAPTER_ID,
        "state": state,
        "reason": code,
        "needs_model": bool(needs_model),
        "needs_dependency": bool(needs_dependency),
        "cancel_supported": False,
        "message": message,
        "code": code,
    }
    payload.update(extra)
    return payload


def _decode_payload(value: object) -> tuple[bytes, str]:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return raw, ""
    if not isinstance(value, str) or not value.strip():
        raise CutoutInputError("image_data_required", "image_data must contain a base64 image payload")

    original = value.strip()
    encoded = original
    declared_mime = ""
    if original.lower().startswith("data:"):
        header, separator, encoded = original.partition(",")
        if not separator:
            raise CutoutInputError("invalid_image_data_url", "image_data must be a base64 data URL")
        match = _DATA_URL_RE.fullmatch(header)
        if not match:
            raise CutoutInputError("invalid_image_data_url", "image_data must be a base64 data URL")
        declared_mime = match.group(1).lower()
        if declared_mime == "image/jpg":
            declared_mime = "image/jpeg"
        if declared_mime not in _ALLOWED_MIME_TYPES:
            raise CutoutInputError("unsupported_image_mime", "image_data uses an unsupported image MIME type")

    max_encoded_length = ((MAX_INPUT_BYTES + 2) // 3) * 4
    if len(encoded) > max_encoded_length:
        raise CutoutInputError("image_too_large", "image_data exceeds the configured byte limit", max_bytes=MAX_INPUT_BYTES)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise CutoutInputError("invalid_image_base64", "image_data is not valid base64") from None
    if not raw:
        raise CutoutInputError("invalid_image_base64", "image_data decoded to an empty image")
    return raw, declared_mime


def validate_input_image(value: object) -> dict[str, Any]:
    """Decode and validate one bounded browser image payload.

    The function accepts a data URL or raw base64 for compatibility, but never
    treats the value as a filesystem path or URL to fetch.
    """

    raw, declared_mime = _decode_payload(value)
    if len(raw) > MAX_INPUT_BYTES:
        raise CutoutInputError("image_too_large", "image_data exceeds the configured byte limit", max_bytes=MAX_INPUT_BYTES)

    try:
        from PIL import Image

        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                width, height = image.size
                image_format = str(image.format or "").upper()
                if width <= 0 or height <= 0 or width * height > MAX_INPUT_PIXELS:
                    raise CutoutInputError(
                        "image_pixels_exceeded",
                        "image_data exceeds the configured pixel limit",
                        max_pixels=MAX_INPUT_PIXELS,
                    )
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
    except CutoutInputError:
        raise
    except Exception:
        raise CutoutInputError("invalid_image_payload", "image_data is not a readable image") from None

    actual_mime = _FORMAT_MIME_TYPES.get(image_format, "")
    if actual_mime not in _ALLOWED_MIME_TYPES:
        raise CutoutInputError("unsupported_image_mime", "image_data uses an unsupported image format")
    if declared_mime and declared_mime != actual_mime:
        raise CutoutInputError("image_mime_mismatch", "image_data MIME type does not match its payload")
    return {
        "bytes": raw,
        "width": int(width),
        "height": int(height),
        "mime_type": actual_mime,
    }


def validate_output_png(value: object, expected_size: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Require a non-empty, readable RGBA PNG with meaningful alpha."""

    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise CutoutOutputError("cutout_output_invalid", "抠图输出不是有效的 PNG 字节")
    raw = bytes(value)
    if not raw or len(raw) > MAX_OUTPUT_BYTES:
        raise CutoutOutputError("cutout_output_invalid", "抠图输出为空或超过大小限制")

    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as image:
            image_format = str(image.format or "").upper()
            size = tuple(int(part) for part in image.size)
            mode = str(image.mode or "")
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            if image_format != "PNG" or mode != "RGBA":
                raise CutoutOutputError("cutout_output_invalid", "抠图输出必须是 RGBA PNG")
            if expected_size is not None and size != tuple(expected_size):
                raise CutoutOutputError("cutout_output_size_mismatch", "抠图输出尺寸必须与输入一致")
            alpha = image.getchannel("A")
            extrema = alpha.getextrema()
            if not extrema or extrema[0] != 0 or extrema[1] != 255:
                raise CutoutOutputError(
                    "cutout_output_alpha_invalid",
                    "抠图输出必须同时包含完全透明和完全不透明像素",
                )
            if image.width * image.height < 2:
                raise CutoutOutputError("cutout_output_alpha_invalid", "抠图输出像素不足以表达透明区域")
    except CutoutOutputError:
        raise
    except Exception:
        raise CutoutOutputError("cutout_output_invalid", "抠图输出不是可读的 PNG") from None

    return {"bytes": raw, "width": size[0], "height": size[1], "mode": "RGBA", "format": "PNG"}


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


class CutoutONNXAdapter:
    """Single-flight CPU-only ONNX Runtime adapter for U2Net human cutout."""

    adapter_id = ADAPTER_ID
    contract = CUTOUT_CONTRACT
    model_manifest = MODEL_MANIFEST

    def __init__(
        self,
        model_path: Optional[os.PathLike[str] | str] = None,
        *,
        base_path: Optional[os.PathLike[str] | str] = None,
        timeout_seconds: object = DEFAULT_TIMEOUT_SECONDS,
        model_manifest: Optional[Mapping[str, Any]] = None,
    ) -> None:
        root = Path(base_path) if base_path is not None else _runtime_base_path()
        self.base_path = root.resolve()
        self.model_path = (
            Path(model_path) if model_path is not None else self.base_path / MODEL_RELATIVE_PATH
        ).resolve()
        self.expected_manifest = dict(model_manifest or MODEL_MANIFEST)
        self.timeout_seconds = _bounded_timeout(timeout_seconds)
        self._session: Any = None
        self._session_fingerprint: Optional[tuple[int, str, str]] = None
        self._session_input_name: Optional[str] = None
        self._session_input_size: tuple[int, int] = (320, 320)
        self._ort: Any = None
        self._numpy: Any = None
        self._session_lock = threading.Lock()
        self._flight_lock = threading.Lock()

    @property
    def busy(self) -> bool:
        return self._flight_lock.locked()

    def acquire_model_operation(self) -> bool:
        """Claim exclusive access to the model file without blocking."""

        return self._flight_lock.acquire(blocking=False)

    def release_model_operation(self) -> None:
        try:
            self._flight_lock.release()
        except RuntimeError:
            pass

    def invalidate_session(self) -> None:
        """Drop the cached ONNX session after an installed model changes."""

        with self._session_lock:
            self._session = None
            self._session_fingerprint = None
            self._session_input_name = None
            self._session_input_size = (320, 320)

    def _manifest_expected(self) -> tuple[int, str, str]:
        try:
            size = int(self.expected_manifest["size_bytes"])
            sha = str(self.expected_manifest["sha256"]).lower()
            md5 = str(self.expected_manifest["md5"]).lower()
        except (KeyError, TypeError, ValueError):
            raise CutoutUnavailableError(
                "cutout_model_manifest_invalid",
                "本地抠图模型清单无效",
                state="needs_model",
                needs_model=True,
            ) from None
        if size <= 0 or not re.fullmatch(r"[0-9a-f]{64}", sha) or not re.fullmatch(r"[0-9a-f]{32}", md5):
            raise CutoutUnavailableError(
                "cutout_model_manifest_invalid",
                "本地抠图模型清单无效",
                state="needs_model",
                needs_model=True,
            )
        return size, sha, md5

    def validate_model_artifact(self) -> dict[str, Any]:
        """Validate the fixed local artifact and return a non-sensitive fingerprint."""

        expected_size, expected_sha, expected_md5 = self._manifest_expected()
        path = self.model_path
        try:
            if path.is_symlink() or not path.is_file():
                raise CutoutUnavailableError(
                    "cutout_model_missing",
                    "尚未安装本地抠图模型",
                    state="needs_model",
                    needs_model=True,
                )
            actual_size, actual_sha, actual_md5 = _hash_file(path)
        except CutoutAdapterError:
            raise
        except (OSError, ValueError):
            raise CutoutUnavailableError(
                "cutout_model_unreadable",
                "本地抠图模型不可读取",
                state="needs_model",
                needs_model=True,
            ) from None

        if actual_size != expected_size:
            raise CutoutUnavailableError(
                "cutout_model_size_mismatch",
                "本地抠图模型大小校验失败",
                state="needs_model",
                needs_model=True,
            )
        if actual_sha != expected_sha or actual_md5 != expected_md5:
            raise CutoutUnavailableError(
                "cutout_model_hash_mismatch",
                "本地抠图模型完整性校验失败",
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
                "本地抠图运行依赖不可用，请重新安装 GenBox 或 requirements-cutout.txt",
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

    @staticmethod
    def _letterbox_source(
        source,
        target_size: tuple[int, int],
    ) -> tuple[Any, tuple[int, int, int, int]]:
        from PIL import Image

        target_width, target_height = (int(target_size[0]), int(target_size[1]))
        source_width, source_height = (int(source.width), int(source.height))
        if source_width <= 0 or source_height <= 0:
            raise CutoutOutputError("cutout_output_invalid", "抠图输入尺寸无效")

        scale = min(target_width / source_width, target_height / source_height)
        resized_width = max(1, min(target_width, int(round(source_width * scale))))
        resized_height = max(1, min(target_height, int(round(source_height * scale))))
        resized = source.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_width, target_height), (0, 0, 0))
        offset_x = (target_width - resized_width) // 2
        offset_y = (target_height - resized_height) // 2
        canvas.paste(resized, (offset_x, offset_y))
        return canvas, (offset_x, offset_y, offset_x + resized_width, offset_y + resized_height)

    @staticmethod
    def _crop_mask_to_source(
        mask,
        output_size: tuple[int, int],
        content_box: tuple[int, int, int, int],
        target_size: tuple[int, int],
    ):
        import numpy

        output_width, output_height = (int(output_size[0]), int(output_size[1]))
        if output_width <= 0 or output_height <= 0:
            raise CutoutOutputError("cutout_output_invalid", "抠图模型返回了无效结果")
        target_width, target_height = (int(target_size[0]), int(target_size[1]))
        if target_width <= 0 or target_height <= 0:
            raise CutoutOutputError("cutout_output_invalid", "抠图输入尺寸无效")
        x0, y0, x1, y1 = (int(content_box[0]), int(content_box[1]), int(content_box[2]), int(content_box[3]))
        crop_x0 = max(0, min(output_width, int(round(x0 * output_width / target_width))))
        crop_x1 = max(crop_x0 + 1, min(output_width, int(round(x1 * output_width / target_width))))
        crop_y0 = max(0, min(output_height, int(round(y0 * output_height / target_height))))
        crop_y1 = max(crop_y0 + 1, min(output_height, int(round(y1 * output_height / target_height))))
        return numpy.asarray(mask, dtype=numpy.float32)[crop_y0:crop_y1, crop_x0:crop_x1]

    @staticmethod
    def _calibrate_mask(mask, numpy):
        finite = mask[numpy.isfinite(mask)]
        if finite.size == 0:
            raise CutoutOutputError("cutout_output_invalid", "抠图模型返回了无效数值")

        try:
            minimum = float(finite.min())
            maximum = float(finite.max())
        except (TypeError, ValueError):
            minimum = float("nan")
            maximum = float("nan")

        low = float(numpy.quantile(finite, 0.02))
        high = float(numpy.quantile(finite, 0.98))
        if not math.isfinite(low) or not math.isfinite(high) or high <= low + 1e-6:
            if math.isfinite(minimum) and math.isfinite(maximum) and minimum >= -0.25 and maximum <= 1.25:
                low, high = 0.0, 1.0
            else:
                low, high = minimum, maximum

        if not math.isfinite(low) or not math.isfinite(high) or high <= low:
            raise CutoutOutputError("cutout_output_alpha_invalid", "抠图模型没有产生有效透明区域")

        calibrated = (mask - low) / (high - low)
        return numpy.clip(calibrated, 0.0, 1.0)

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
                # Explicitly pass the CPU provider and reject every other
                # provider reported by the resulting session.
                session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
                providers = list(session.get_providers())
                if providers != ["CPUExecutionProvider"]:
                    raise CutoutUnavailableError(
                        "cutout_cpu_provider_required",
                        "本地抠图仅允许 CPUExecutionProvider",
                        state="unavailable",
                    )
                inputs = list(session.get_inputs())
                outputs = list(session.get_outputs())
                if len(inputs) != 1 or not outputs:
                    raise CutoutUnavailableError(
                        "cutout_session_invalid",
                        "本地抠图模型会话结构无效",
                        state="unavailable",
                    )
                input_info = inputs[0]
                shape = list(getattr(input_info, "shape", []) or [])
                if len(shape) != 4 or self._known_dimension(shape[1], 3) != 3:
                    raise CutoutUnavailableError(
                        "cutout_session_invalid",
                        "本地抠图模型输入结构无效",
                        state="unavailable",
                    )
                input_height = self._known_dimension(shape[2], 320)
                input_width = self._known_dimension(shape[3], 320)
                input_name = str(getattr(input_info, "name", "") or "")
                if not input_name:
                    raise CutoutUnavailableError(
                        "cutout_session_invalid",
                        "本地抠图模型输入名称无效",
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
                    "cutout_session_unavailable",
                    "本地抠图模型会话无法启动",
                    state="unavailable",
                ) from None

            self._session = session
            self._session_fingerprint = fingerprint
            self._session_input_name = input_name
            self._session_input_size = (input_width, input_height)
            return {
                "session": session,
                "numpy": numpy,
                "input_name": input_name,
                "input_size": (input_width, input_height),
            }

    def capabilities(self) -> dict[str, Any]:
        """Return an honest capability snapshot without raising on setup gaps."""

        if not self.acquire_model_operation():
            return _unavailable(
                "cutout_busy",
                "本地抠图模型正在使用中",
                state="busy",
                busy=True,
            )
        try:
            try:
                manifest = self.validate_model_artifact()
            except CutoutAdapterError as exc:
                return _unavailable(
                    exc.code,
                    exc.message,
                    state=str(exc.details.get("state") or "needs_model"),
                    needs_model=bool(exc.details.get("needs_model", True)),
                    needs_dependency=bool(exc.details.get("needs_dependency", False)),
                )

            try:
                self._load_session(manifest)
            except CutoutAdapterError as exc:
                return _unavailable(
                    exc.code,
                    exc.message,
                    state=str(exc.details.get("state") or "unavailable"),
                    needs_model=bool(exc.details.get("needs_model", False)),
                    needs_dependency=bool(exc.details.get("needs_dependency", False)),
                )

            return {
                "contract": CUTOUT_CONTRACT,
                "available": True,
                "executable": True,
                "adapters": [ADAPTER_ID],
                "adapter": ADAPTER_ID,
                "state": "ready",
                "reason": None,
                "needs_model": False,
                "needs_dependency": False,
                "cpu_execution_provider": True,
                "cancel_supported": False,
                "timeout_seconds": self.timeout_seconds,
                "model": {
                    "filename": MODEL_FILENAME,
                    "size_bytes": int(self.expected_manifest["size_bytes"]),
                    "sha256": str(self.expected_manifest["sha256"]),
                    "md5": str(self.expected_manifest["md5"]),
                },
            }
        finally:
            self.release_model_operation()

    # Compatibility aliases used by route-level tests and future tools.
    capability = capabilities
    get_capabilities = capabilities
    probe = capabilities

    def _run_inference(self, decoded: Mapping[str, Any], session_info: Mapping[str, Any]) -> dict[str, Any]:
        from PIL import Image

        numpy = session_info["numpy"]
        session = session_info["session"]
        input_name = str(session_info["input_name"])
        input_width, input_height = tuple(session_info["input_size"])
        source_bytes = bytes(decoded["bytes"])
        width, height = int(decoded["width"]), int(decoded["height"])

        try:
            with Image.open(io.BytesIO(source_bytes)) as source:
                rgb = source.convert("RGB")
            letterboxed, content_box = self._letterbox_source(rgb, (input_width, input_height))
            array = numpy.asarray(letterboxed, dtype=numpy.float32) / 255.0
            mean = numpy.asarray([0.485, 0.456, 0.406], dtype=numpy.float32)
            std = numpy.asarray([0.229, 0.224, 0.225], dtype=numpy.float32)
            tensor = (array - mean) / std
            tensor = numpy.transpose(tensor, (2, 0, 1))[None, ...]
            outputs = session.run(None, {input_name: tensor})
            if not outputs:
                raise CutoutOutputError("cutout_output_invalid", "抠图模型返回空结果")
            mask = numpy.asarray(outputs[0], dtype=numpy.float32)
            mask = numpy.squeeze(mask)
            if mask.ndim != 2 or mask.size == 0:
                raise CutoutOutputError("cutout_output_invalid", "抠图模型返回了无法识别的掩码")
            if not bool(numpy.isfinite(mask).all()):
                raise CutoutOutputError("cutout_output_invalid", "抠图模型返回了无效数值")
            cropped_mask = self._crop_mask_to_source(
                mask,
                (mask.shape[1], mask.shape[0]),
                content_box,
                (input_width, input_height),
            )
            calibrated = self._calibrate_mask(cropped_mask, numpy)
            calibrated_image = Image.fromarray(
                numpy.asarray((calibrated * 255.0).round(), dtype=numpy.uint8),
                mode="L",
            )
            mask_image = calibrated_image.resize((width, height), Image.Resampling.BILINEAR)
            alpha = numpy.asarray(mask_image, dtype=numpy.uint8).copy()
            if alpha.size < 2:
                raise CutoutOutputError("cutout_output_alpha_invalid", "抠图输出像素不足以表达透明区域")
            rgba = rgb.convert("RGBA")
            rgba.putalpha(Image.fromarray(alpha, mode="L"))
            output = io.BytesIO()
            rgba.save(output, format="PNG", optimize=False)
            png_bytes = output.getvalue()
        except CutoutAdapterError:
            raise
        except Exception:
            raise CutoutOutputError("cutout_output_invalid", "抠图模型输出处理失败") from None

        validate_output_png(png_bytes, (width, height))
        return {
            "image_bytes": png_bytes,
            "width": width,
            "height": height,
            "adapter": ADAPTER_ID,
        }

    # Alternate spelling is useful for narrow unit-test fakes.
    _infer = _run_inference

    def _process_claimed(self, decoded: Mapping[str, Any], session_info: Mapping[str, Any]) -> dict[str, Any]:
        try:
            started = time.monotonic()
            result = self._run_inference(decoded, session_info)
            result["elapsed_seconds"] = round(max(0.0, time.monotonic() - started), 3)
            return result
        finally:
            # Ownership is transferred to the worker thread for async calls;
            # threading.Lock intentionally permits release from that worker.
            try:
                self._flight_lock.release()
            except RuntimeError:
                pass

    def process(self, image_data: object) -> dict[str, Any]:
        """Synchronous execution for local callers and deterministic tests."""

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
        """Execute in a worker with a truthful soft timeout.

        ``asyncio`` cannot cancel an already-running native/runtime call.  On a
        timeout the worker continues and owns the single-flight lock until it
        exits, preventing overlapping model executions.
        """

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
            # Drain a late exception/result so the event loop does not emit an
            # unhandled-future warning after the soft timeout response.
            def _drain(completed: asyncio.Future[Any]) -> None:
                try:
                    completed.exception()
                except BaseException:
                    pass

            future.add_done_callback(_drain)
            raise CutoutTimeoutError(timeout) from None

    async def run(self, image_data: object, *, timeout_seconds: object = None) -> dict[str, Any]:
        return await self.process_async(image_data, timeout_seconds=timeout_seconds)

    execute = run

    def save_atomic(
        self,
        png_bytes: object,
        gallery_dir: os.PathLike[str] | str,
        *,
        expected_size: Optional[tuple[int, int]] = None,
    ) -> Path:
        """Atomically persist a validated result in the target gallery dir."""

        checked = validate_output_png(png_bytes, expected_size)
        data = checked["bytes"]
        directory = Path(gallery_dir)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir():
                raise OSError("gallery is not a directory")
            filename = f"cutout_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:12]}.png"
            target = directory / filename
            temporary = directory / f".{filename}.{uuid.uuid4().hex}.tmp"
            with temporary.open("xb") as handle:
                handle.write(data)
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


def atomic_save_png(png_bytes: object, gallery_dir: os.PathLike[str] | str, *, expected_size: Optional[tuple[int, int]] = None) -> Path:
    """Standalone persistence helper used by tests and future adapters."""

    return CutoutONNXAdapter(model_manifest=MODEL_MANIFEST).save_atomic(
        png_bytes,
        gallery_dir,
        expected_size=expected_size,
    )


__all__ = [
    "ADAPTER_ID",
    "CUTOUT_CONTRACT",
    "DEFAULT_TIMEOUT_SECONDS",
    "EXPECTED_MODEL_MD5",
    "EXPECTED_MODEL_SHA256",
    "EXPECTED_MODEL_SIZE",
    "MAX_INPUT_BYTES",
    "MAX_INPUT_PIXELS",
    "MODEL_FILENAME",
    "MODEL_MANIFEST",
    "MODEL_MD5",
    "MODEL_RELATIVE_PATH",
    "MODEL_SHA256",
    "MODEL_SIZE_BYTES",
    "CutoutAdapterError",
    "CutoutBusyError",
    "CutoutInputError",
    "CutoutONNXAdapter",
    "CutoutOutputError",
    "CutoutPersistenceError",
    "CutoutTimeoutError",
    "atomic_save_png",
    "validate_input_image",
    "validate_output_png",
]
