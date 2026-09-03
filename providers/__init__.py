"""
动态多模型图像生成服务
- 从 ConfigManager 读取运行时配置
- 自动为每个 image 类型 Provider 创建调用实例
- 支持 OpenAI 兼容 / Gemini / Qwen2API 三种协议
"""
import asyncio
import base64
import binascii
import ipaddress
import json
import math
import os
import re
import socket
import tempfile
import threading
import unicodedata
import uuid
import time
import warnings
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image
from io import BytesIO

from config import (
    cfg_mgr,
    GALLERY_DIR,
    PrecisionEditProfile,
    ProviderConfig,
    VideoModelSpec,
    VIDEO_MODEL_SPECS,
    normalize_precision_capability_size,
    precision_capability_size_declaration,
    resolve_precision_model_capability,
    verify_ssl_enabled,
)


# 国内模型厂商（始终直连，不走代理）
CHINESE_PROVIDERS = {
    "qwen",        # 阿里通义千问
    "zhipu",       # 智谱 GLM
    "deepseek",    # DeepSeek
    "volcengine",  # 火山引擎
    "siliconflow", # SiliconFlow
}

INPAINT_MASK_CONTRACT = "genbox-edit-white-v1"
INPAINT_CAPABILITY = "inpaint_mask"
PRECISION_ANNOTATION_CONTRACT_V1 = "genbox-annotation-v1"
PRECISION_ANNOTATION_CONTRACT_V2 = "genbox-annotation-v2"
PRECISION_ANNOTATION_CONTRACT_V3 = "genbox-annotation-v3"
PRECISION_ANNOTATION_CONTRACT = PRECISION_ANNOTATION_CONTRACT_V1
PRECISION_ANNOTATION_CONTRACTS = frozenset({
    PRECISION_ANNOTATION_CONTRACT_V1,
    PRECISION_ANNOTATION_CONTRACT_V2,
    PRECISION_ANNOTATION_CONTRACT_V3,
})
PRECISION_EDIT_CAPABILITY = "precision_edit"
LEGACY_PRECISION_EDIT_PROFILE = (
    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE
)
GENERATED_IMAGE_MAX_BYTES = 20 * 1024 * 1024
GENERATED_IMAGE_MAX_PIXELS = int(
    os.getenv("GENBOX_GENERATE_MAX_IMAGE_PIXELS", "25000000")
)
GENERATED_IMAGE_MAX_DIMENSION = 8192
GENERATED_IMAGE_MAX_REDIRECTS = 3
PROVIDER_JSON_OVERHEAD_BYTES = 1024 * 1024
PROVIDER_ERROR_RESPONSE_MAX_BYTES = 64 * 1024
PROVIDER_LLM_RESPONSE_MAX_BYTES = 1024 * 1024
PROVIDER_MODEL_LIST_RESPONSE_MAX_BYTES = 2 * 1024 * 1024
GENERATED_IMAGE_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
GENERATED_IMAGE_FORMAT_MIME_TYPES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}
GENERATED_IMAGE_BLOCKED_PORTS = frozenset({21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 445, 2375, 2376, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 9200, 11211})
GENERATED_IMAGE_METADATA_HOSTS = frozenset({
    "instance-data",
    "instance-data.ec2.internal",
    "metadata",
    "metadata.google.internal",
    "metadata.goog",
})
_WINDOWS_RESERVED_FILENAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
})
_IMAGE_SAVE_LOCK = threading.Lock()
_IMAGE_HEADER_VALIDATION_LOCK = threading.RLock()
GENERATED_IMAGE_METADATA_ADDRESSES = frozenset({
    ipaddress.ip_address("100.100.100.200"),  # Alibaba Cloud ECS
    ipaddress.ip_address("168.63.129.16"),   # Azure platform virtual IP
    ipaddress.ip_address("169.254.169.254"), # AWS/GCP/Azure/OCI IMDS
    ipaddress.ip_address("fd00:ec2::254"),   # AWS IMDS IPv6
})
PRECISION_MAX_OUTPUT_PIXELS = 64 * 1024 * 1024
PRECISION_OUTPUT_SIZE_POLICIES = ("strict", "fit_crop")
PRECISION_FIT_CROP_MAX_ASPECT_RATIO_DELTA = 0.05
PRECISION_FIT_CROP_MAX_UPSCALE = 1.5
PROVIDER_ERROR_MAX_LENGTH = 2400


@dataclass(frozen=True)
class GeneratedImageInspection:
    width: int
    height: int
    image_format: str
    mime_type: str
    has_alpha: bool


class GeneratedImageValidationError(ValueError):
    """Structured rejection for untrusted provider image output."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ProviderResponseValidationError(ValueError):
    """Structured rejection for a malformed or oversized Provider response."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _provider_json_response_max_bytes(image_count: int = 1) -> int:
    count = max(1, int(image_count))
    encoded_image_max = 4 * ((GENERATED_IMAGE_MAX_BYTES + 2) // 3)
    return encoded_image_max * count + PROVIDER_JSON_OVERHEAD_BYTES


async def _read_bounded_provider_response(response, max_bytes: int) -> bytes:
    """Read a streamed response while enforcing declared and actual byte caps."""
    content_length = (getattr(response, "headers", {}) or {}).get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except (TypeError, ValueError):
            raise ProviderResponseValidationError(
                "provider_response_content_length_invalid",
                "provider response has an invalid Content-Length",
            ) from None
        if declared_length < 0:
            raise ProviderResponseValidationError(
                "provider_response_content_length_invalid",
                "provider response has an invalid Content-Length",
            )
        if declared_length > max_bytes:
            raise ProviderResponseValidationError(
                "provider_response_bytes_exceeded",
                "provider response exceeds the configured byte limit",
                details={"max_bytes": max_bytes},
            )

    content = bytearray()
    async for chunk in response.aiter_bytes():
        if len(content) + len(chunk) > max_bytes:
            raise ProviderResponseValidationError(
                "provider_response_bytes_exceeded",
                "provider response exceeds the configured byte limit",
                details={"max_bytes": max_bytes},
            )
        content.extend(chunk)
    return bytes(content)


async def _stream_bounded_provider_response(
    client,
    method: str,
    url: str,
    *,
    response_image_count: int = 1,
    success_max_bytes: Optional[int] = None,
    **request_kwargs,
):
    """Stream one Provider response before exposing its content to parsers."""
    stream = getattr(client, "stream", None)
    if not callable(stream):
        # Existing unit-test doubles predate streaming. Real httpx clients
        # always take the bounded stream branch above.
        request = getattr(client, method.lower())
        return await request(url, **request_kwargs)

    async with stream(method, url, **request_kwargs) as response:
        max_bytes = (
            PROVIDER_ERROR_RESPONSE_MAX_BYTES
            if int(response.status_code) >= 400
            else (
                int(success_max_bytes)
                if success_max_bytes is not None
                else _provider_json_response_max_bytes(response_image_count)
            )
        )
        content = await _read_bounded_provider_response(response, max_bytes)
        request = getattr(response, "request", None) or httpx.Request(method, url)
        return httpx.Response(
            int(response.status_code),
            headers=dict(getattr(response, "headers", {}) or {}),
            content=content,
            request=request,
        )


def _parse_provider_json_response(response) -> Any:
    try:
        return response.json()
    except Exception:
        raise ProviderResponseValidationError(
            "provider_response_json_invalid",
            "provider response is not valid JSON",
        ) from None


def _normalize_generated_image_mime(value: object) -> str:
    mime_type = str(value or "").split(";", 1)[0].strip().lower()
    return "image/jpeg" if mime_type == "image/jpg" else mime_type


def _validate_generated_image_header(
    image: Image.Image,
    *,
    declared_mime: object = None,
    max_pixels: int = GENERATED_IMAGE_MAX_PIXELS,
    max_dimension: int = GENERATED_IMAGE_MAX_DIMENSION,
) -> GeneratedImageInspection:
    image_format = str(image.format or "").upper()
    actual_mime = GENERATED_IMAGE_FORMAT_MIME_TYPES.get(image_format, "")
    if actual_mime not in GENERATED_IMAGE_CONTENT_TYPES:
        raise GeneratedImageValidationError(
            "generated_image_format_unsupported",
            "generated image uses an unsupported image format",
        )

    normalized_declared_mime = _normalize_generated_image_mime(declared_mime)
    if normalized_declared_mime:
        if normalized_declared_mime not in GENERATED_IMAGE_CONTENT_TYPES:
            raise GeneratedImageValidationError(
                "generated_image_mime_unsupported",
                "generated image declares an unsupported MIME type",
                details={"declared_mime": normalized_declared_mime},
            )
        if normalized_declared_mime != actual_mime:
            raise GeneratedImageValidationError(
                "generated_image_mime_mismatch",
                "generated image MIME type does not match its decoded format",
                details={
                    "declared_mime": normalized_declared_mime,
                    "actual_mime": actual_mime,
                },
            )

    width, height = image.size
    if (
        width <= 0
        or height <= 0
        or width > max_dimension
        or height > max_dimension
        or width * height > max_pixels
    ):
        raise GeneratedImageValidationError(
            "generated_image_pixels_exceeded",
            "generated image dimensions exceed the configured safety limit",
            details={
                "width": width,
                "height": height,
                "max_dimension": max_dimension,
                "max_pixels": max_pixels,
            },
        )

    return GeneratedImageInspection(
        width=width,
        height=height,
        image_format=image_format,
        mime_type=actual_mime,
        has_alpha="A" in image.getbands() or "transparency" in image.info,
    )


def _open_validated_generated_image(
    image_data: bytes,
    *,
    declared_mime: object = None,
    max_pixels: int = GENERATED_IMAGE_MAX_PIXELS,
    max_dimension: int = GENERATED_IMAGE_MAX_DIMENSION,
    load_pixels: bool,
) -> tuple[Image.Image, GeneratedImageInspection]:
    if not isinstance(image_data, (bytes, bytearray, memoryview)) or not image_data:
        raise GeneratedImageValidationError(
            "generated_image_empty",
            "generated image payload is empty",
        )
    if len(image_data) > GENERATED_IMAGE_MAX_BYTES:
        raise GeneratedImageValidationError(
            "generated_image_bytes_exceeded",
            "generated image exceeds the configured compressed-byte limit",
            details={"max_bytes": GENERATED_IMAGE_MAX_BYTES},
        )

    image = None
    try:
        # Pillow warning filters are process-global. Serialize this short,
        # header-only section so concurrent generations cannot bypass the
        # promoted DecompressionBombWarning before project limits are checked.
        with _IMAGE_HEADER_VALIDATION_LOCK:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(BytesIO(bytes(image_data)))
                inspection = _validate_generated_image_header(
                    image,
                    declared_mime=declared_mime,
                    max_pixels=max_pixels,
                    max_dimension=max_dimension,
                )
        if load_pixels:
            image.load()
        return image, inspection
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        if image is not None:
            image.close()
        raise GeneratedImageValidationError(
            "generated_image_decompression_bomb",
            "generated image was rejected by the decompression-bomb guard",
        ) from exc
    except GeneratedImageValidationError:
        if image is not None:
            image.close()
        raise
    except Exception as exc:
        if image is not None:
            image.close()
        raise GeneratedImageValidationError(
            "generated_image_unreadable",
            "generated image payload is not a readable image",
        ) from exc


def _inspect_generated_image(
    image_data: bytes,
    *,
    declared_mime: object = None,
    max_pixels: int = GENERATED_IMAGE_MAX_PIXELS,
    max_dimension: int = GENERATED_IMAGE_MAX_DIMENSION,
) -> GeneratedImageInspection:
    image, inspection = _open_validated_generated_image(
        image_data,
        declared_mime=declared_mime,
        max_pixels=max_pixels,
        max_dimension=max_dimension,
        load_pixels=False,
    )
    image.close()
    return inspection


def _decode_generated_image_base64(value: object) -> bytes:
    if not isinstance(value, str) or not value:
        raise GeneratedImageValidationError(
            "generated_image_base64_invalid",
            "generated image base64 payload is invalid",
        )

    encoded = value
    declared_mime = ""
    if encoded.lower().startswith("data:"):
        header, separator, encoded = encoded.partition(",")
        header_parts = header[5:].split(";")
        if (
            not separator
            or len(header_parts) < 2
            or header_parts[-1].strip().lower() != "base64"
        ):
            raise GeneratedImageValidationError(
                "generated_image_base64_invalid",
                "generated image data URL is invalid",
            )
        declared_mime = _normalize_generated_image_mime(header_parts[0])
        if not declared_mime:
            raise GeneratedImageValidationError(
                "generated_image_base64_invalid",
                "generated image data URL is invalid",
            )
    max_encoded_length = 4 * ((GENERATED_IMAGE_MAX_BYTES + 2) // 3)
    if len(encoded) > max_encoded_length:
        raise GeneratedImageValidationError(
            "generated_image_bytes_exceeded",
            "generated image exceeds the configured compressed-byte limit",
            details={"max_bytes": GENERATED_IMAGE_MAX_BYTES},
        )
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise GeneratedImageValidationError(
            "generated_image_base64_invalid",
            "generated image base64 payload is invalid",
        ) from exc
    if not decoded:
        raise GeneratedImageValidationError(
            "generated_image_empty",
            "generated image payload is empty",
        )
    if len(decoded) > GENERATED_IMAGE_MAX_BYTES:
        raise GeneratedImageValidationError(
            "generated_image_bytes_exceeded",
            "generated image exceeds the configured compressed-byte limit",
            details={"max_bytes": GENERATED_IMAGE_MAX_BYTES},
        )
    if declared_mime:
        _inspect_generated_image(decoded, declared_mime=declared_mime)
    return decoded


@dataclass(frozen=True)
class PrecisionEditTransportProfile:
    path: str
    image_field: str
    image_payload: str = "source_and_annotation"
    preserve_size: str = "auto"


@dataclass
class PrecisionEditPostBudget:
    """One bounded POST allowance shared by all endpoints for one edit operation."""

    remaining: int = 3

    def consume(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True

    @property
    def exhausted(self) -> bool:
        return self.remaining <= 0


PRECISION_EDIT_TRANSPORT_PROFILES = {
    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE.value: (
        PrecisionEditTransportProfile(path="/images/edits", image_field="image")
    ),
    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_IMAGE_ARRAY.value: (
        PrecisionEditTransportProfile(path="/images/edits", image_field="image[]")
    ),
    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE.value: (
        PrecisionEditTransportProfile(
            path="/images/edits",
            image_field="image",
            image_payload="source_only",
            preserve_size="source_dimensions",
        )
    ),
}

_SENSITIVE_FIELD_RE = re.compile(
    r"(?i)((?<![\w-])[\"']?(?:x[_-]?api[_-]?key|api[_-]?key|access[_-]?token|"
    r"refresh[_-]?token|token|auth(?:orization)?|client[_-]?secret|password|secret|"
    r"signature|credential)\b[\"']?\s*[:=]\s*)"
    r"((?:Bearer|Basic)\s+[^\s,;\"'}]+|"
    r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|\[[^\]]*\]|[^\s,;&}\]]+)"
)
_SENSITIVE_QUERY_RE = re.compile(
    r"(?i)(^|[?&;\s])((?:key|api[_-]?key|access[_-]?token|refresh[_-]?token|token|auth(?:orization)?|"
    r"client[_-]?secret|password|secret|signature|sig|credential)=)"
    r"(\[REDACTED\]|[^&#\s\"',;]*)"
)
_AUTH_SCHEME_RE = re.compile(
    r"(?i)\b(Bearer|Basic)\s+([^\s,;\"'}]+)"
)
_URL_USERINFO_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9+.-])([A-Za-z][A-Za-z0-9+.-]*://)([^/?#\s]+)@(?=[^/?#\s])"
)
_PREFIXED_SECRET_RE = re.compile(r"(?i)\b(?:sk|rk|pk)-[A-Za-z0-9_-]{8,}\b")
_QUERY_TRAILING_PUNCTUATION = ".,:!?)]}"
_SENSITIVE_JSON_KEYS = frozenset({
    "key",
    "xapikey",
    "apikey",
    "accesstoken",
    "refreshtoken",
    "token",
    "auth",
    "authorization",
    "clientsecret",
    "password",
    "secret",
    "signature",
    "credential",
})


def _json_string_end(text: str, start: int) -> int | None:
    """Return the closing quote for one JSON string, honoring escaped quotes."""
    escaped = False
    for index in range(start + 1, len(text)):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return index
    return None


def _redact_sensitive_json_fields(text: str) -> str:
    """Redact valid JSON string values without losing text after escaped quotes."""
    chunks = []
    cursor = 0
    index = 0
    while index < len(text):
        if text[index] != '"':
            index += 1
            continue
        key_end = _json_string_end(text, index)
        if key_end is None:
            break
        try:
            key = json.loads(text[index:key_end + 1])
        except (TypeError, ValueError, json.JSONDecodeError):
            index = key_end + 1
            continue
        separator = key_end + 1
        while separator < len(text) and text[separator].isspace():
            separator += 1
        if separator >= len(text) or text[separator] != ":":
            index = key_end + 1
            continue
        normalized_key = re.sub(r"[-_\s]", "", key.lower()) if isinstance(key, str) else ""
        if normalized_key not in _SENSITIVE_JSON_KEYS:
            index = key_end + 1
            continue
        value_start = separator + 1
        while value_start < len(text) and text[value_start].isspace():
            value_start += 1
        if value_start >= len(text) or text[value_start] != '"':
            index = key_end + 1
            continue
        value_end = _json_string_end(text, value_start)
        if value_end is None:
            break
        chunks.extend((text[cursor:value_start], '"[REDACTED]"'))
        cursor = value_end + 1
        index = cursor
    if not chunks:
        return text
    chunks.append(text[cursor:])
    return "".join(chunks)


def _redact_sensitive_text(text: str) -> str:
    """Remove credentials from upstream diagnostics while retaining useful context."""
    def redact_field(match: re.Match) -> str:
        value = match.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
            replacement = f"{value[0]}[REDACTED]{value[0]}"
        else:
            replacement = "[REDACTED]"
        return f"{match.group(1)}{replacement}"

    def redact_auth_scheme(match: re.Match) -> str:
        return f"{match.group(1)} [REDACTED]"

    def redact_query(match: re.Match) -> str:
        value = match.group(3)
        if value == "[REDACTED]":
            return f"{match.group(1)}{match.group(2)}{value}"
        suffix = ""
        while value and value[-1] in _QUERY_TRAILING_PUNCTUATION:
            suffix = value[-1] + suffix
            value = value[:-1]
        return f"{match.group(1)}{match.group(2)}[REDACTED]{suffix}"

    redacted = _redact_sensitive_json_fields(text)
    redacted = _URL_USERINFO_RE.sub(r"\1[REDACTED]@", redacted)
    redacted = _SENSITIVE_QUERY_RE.sub(redact_query, redacted)
    redacted = _SENSITIVE_FIELD_RE.sub(redact_field, redacted)
    redacted = _AUTH_SCHEME_RE.sub(redact_auth_scheme, redacted)
    return _PREFIXED_SECRET_RE.sub("[REDACTED]", redacted)


def _coerce_text(value: Any) -> str:
    """Normalize an upstream/error value before any redaction or truncation.

    Some third-party endpoints echo non-ASCII characters in bodies or headers.
    Modern httpx/JSON paths are UTF-8 safe, but str()-conversions in older
    packaged environments can raise ``UnicodeEncodeError: 'ascii'`` when the
    value flows through a repr/log. This keeps any error/report text printable
    and never drops the original information.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    try:
        text = str(value).encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    except Exception:
        text = repr(value).encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return text


def _safe_text(value: Any) -> str:
    """Return printable text with generic credential patterns removed."""
    return _redact_sensitive_text(_coerce_text(value))


def _provider_error_text(value: Any, cfg: ProviderConfig) -> str:
    """Sanitize generic secrets and exact credentials configured for this provider."""
    text = _coerce_text(value)
    secrets = [getattr(cfg, "api_key", ""), *(getattr(cfg, "api_keys", None) or [])]
    secrets.extend(getattr(endpoint, "key", "") for endpoint in (getattr(cfg, "endpoints", None) or []))
    for secret in sorted({str(item) for item in secrets if item}, key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    return _redact_sensitive_text(text)


def _provider_error_excerpt(value: Any, cfg: ProviderConfig, limit: int) -> str:
    """Apply all provider-aware redaction before imposing an error-text limit."""
    return _provider_error_text(value, cfg).strip()[:limit]


def _exception_text(exc: BaseException) -> str:
    """Return useful evidence even for exceptions whose ``str()`` is empty."""
    detail = _safe_text(exc).strip()
    return detail or type(exc).__name__


def _provider_exception_text(exc: BaseException, cfg: ProviderConfig) -> str:
    """Return provider-aware exception evidence without pre-redacting exact keys."""
    detail = _provider_error_text(exc, cfg).strip()
    return detail or type(exc).__name__


def _endpoint_failure_summary(cfg: ProviderConfig, failures: list[tuple[int, object, str]]) -> str:
    """Keep every configured endpoint name/status while bounding log-safe detail."""
    entries = []
    for index, endpoint, error in failures:
        configured_name = _provider_error_text(getattr(endpoint, "name", ""), cfg).strip()
        label = configured_name[:80] if configured_name else f"端点 {index}"
        detail = _provider_error_text(error or "未知错误", cfg).strip()
        statuses = list(dict.fromkeys(re.findall(r"(?i)\bHTTP\s+\d{3}\b", detail)))
        status_text = "/".join(status.upper() for status in statuses) or "FAILED"
        entries.append((label, status_text, detail))

    if not entries:
        return "无可用端点"

    label_cost = sum(len(label) + len(status) + 8 for label, status, _ in entries)
    detail_budget = max(24, min(240, (2100 - label_cost) // len(entries)))
    summary = " | ".join(
        f"{label} [{status}]: {detail[:detail_budget]}"
        for label, status, detail in entries
    )
    if len(summary) <= 2200:
        return summary

    compact = " | ".join(f"{label} [{status}]" for label, status, _ in entries)
    return compact[:2200]


def _validate_generated_size(image_data: bytes, requested_size: str, cfg: ProviderConfig) -> str | None:
    """Return a user-facing error when an endpoint silently ignores ``size``.

    OpenAI-compatible gateways often accept arbitrary JSON but still return
    their default square canvas. Treat that as a failed generation instead of
    presenting a misleading successful result.
    """
    if not requested_size or "x" not in str(requested_size).lower():
        return None
    try:
        expected_w, expected_h = (int(part) for part in str(requested_size).lower().split("x", 1))
        inspection = _inspect_generated_image(image_data)
        actual_w, actual_h = inspection.width, inspection.height
    except (GeneratedImageValidationError, TypeError, ValueError):
        return None
    if expected_w <= 0 or expected_h <= 0:
        return None
    expected_ratio = expected_w / expected_h
    actual_ratio = actual_w / actual_h if actual_h else 0
    if abs(expected_ratio - actual_ratio) > 0.02:
        return (
            f"[{cfg.name}] 图片比例未按请求生效：请求 {expected_w}×{expected_h}，"
            f"接口返回 {actual_w}×{actual_h}。该端点可能不支持此比例，请换用支持 {expected_w}×{expected_h} 的模型，"
            "或改用该模型支持的尺寸后重试。"
        )
    return None


def _crop_generated_size(image_data: bytes, requested_size: str) -> bytes | None:
    """Center-crop a sufficiently large, similarly shaped canvas."""
    if not requested_size or "x" not in str(requested_size).lower():
        return None
    source = None
    image = None
    try:
        expected_w, expected_h = (int(part) for part in str(requested_size).lower().split("x", 1))
        source, _inspection = _open_validated_generated_image(
            image_data,
            load_pixels=True,
        )
        image = source.convert("RGBA")
        actual_w, actual_h = image.size
    except (GeneratedImageValidationError, TypeError, ValueError):
        if image is not None:
            image.close()
        if source is not None:
            source.close()
        return None
    try:
        if expected_w <= 0 or expected_h <= 0:
            return None
        if actual_w < expected_w or actual_h < expected_h:
            return None
        expected_ratio = expected_w / expected_h
        actual_ratio = actual_w / actual_h if actual_h else 0
        if abs(expected_ratio - actual_ratio) > 0.15:
            return None
        left = (actual_w - expected_w) // 2
        top = (actual_h - expected_h) // 2
        cropped = image.crop((left, top, left + expected_w, top + expected_h))
        try:
            output = BytesIO()
            cropped.save(output, format="PNG")
            return output.getvalue()
        finally:
            cropped.close()
    finally:
        image.close()
        source.close()


def _friendly_generation_error(error: str) -> str:
    """Explain common upstream failures without hiding technical evidence."""
    text = _safe_text(error)
    if "503 Service Unavailable" in text or "provider_unavailable" in text:
        return (
            "上游生图服务暂时不可用（503）。这通常是模型服务繁忙或临时故障，"
            "不是提示词或本机尺寸设置错误。请稍后重试，或切换到其他可用端点/模型。"
            f" 技术详情：{text}"
        )
    lower = text.lower()
    if "unsupported image model" in lower:
        return (
            "当前模型名称不被这个端点的图片编辑接口支持。请在“编辑模型”中改选端点明确支持的模型名称。"
            f" 技术详情：{text}"
        )
    if "no available channel" in lower or "model_not_found" in lower:
        return (
            "这个端点当前没有可用的图片编辑通道。模型本身可能支持改图，但该中转服务暂时无法调用它。"
            "请稍后重试、切换端点，或联系端点服务商开通对应模型通道。"
            f" 技术详情：{text}"
        )
    return text


def _get_proxy_url(cfg: ProviderConfig = None) -> str | None:
    """获取代理 URL（支持 Provider 级别跳过代理）
    
    逻辑：
    1. 国内厂商（CHINESE_PROVIDERS）→ 始终直连
    2. 全局代理未启用 → 返回 None（直连）
    3. Provider 设置 skip_proxy=True → 返回 None（直连）
    4. 其他情况 → 返回代理 URL
    """
    # 国内厂商始终直连
    if cfg and cfg.id in CHINESE_PROVIDERS:
        return None
    
    proxy = cfg_mgr.config.proxy
    if not proxy.enabled or not proxy.host:
        return None
    # Provider 级别跳过代理
    if cfg and cfg.skip_proxy:
        return None
    return f"{proxy.type}://{proxy.host}:{proxy.port}"


def get_video_model_spec(model_name: str):
    """根据模型名称获取视频模型参数约束
    
    匹配规则：按优先级匹配模型名称中的关键词
    返回: VideoModelSpec 或默认规格
    """
    model_lower = model_name.lower() if model_name else ""
    
    # 按优先级匹配模型关键词
    spec_keywords = [
        ("veo_3", "veo-3"),
        ("veo_2", "veo-2"),
        ("veo-", "veo-3"),      # veo-3-1, veo-3-0 等
        ("sora", "sora"),
        ("kling", "kling-v2"),
        ("hailuo", "hailuo"),
        ("minimax", "hailuo"),
        ("wanx2", "wanx2.1"),
        ("wan2", "wan2"),
        ("wan_", "wan2"),
        ("hunyuan", "hunyuan"),
        ("doubao", "seedance"),   # doubao-seedance 系列
        ("seedance", "seedance"),
        ("agnes", "agnes"),
    ]
    
    for keyword, spec_key in spec_keywords:
        if keyword in model_lower:
            return VIDEO_MODEL_SPECS.get(spec_key)
    
    # 默认返回 Agnes 规格（最灵活）
    return VIDEO_MODEL_SPECS.get("agnes")


def get_video_model_spec_dict(model_name: str) -> dict:
    """获取视频模型参数约束的字典格式（用于API返回）"""
    spec = get_video_model_spec(model_name)
    if spec:
        return spec.model_dump()
    return VideoModelSpec().model_dump()


@dataclass
class ImageResult:
    """统一返回格式"""
    success: bool
    image_data: Optional[bytes] = None
    image_url: Optional[str] = None
    local_path: Optional[str] = None
    model: str = ""
    error: str = ""
    generation_id: str = ""
    error_code: str = ""
    error_details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    warnings: Optional[List[Dict[str, str]]] = None


def _sanitize_failed_image_result(result: ImageResult, cfg: ProviderConfig) -> ImageResult:
    """Apply provider-aware masking before a failed result crosses a boundary."""
    if isinstance(result, ImageResult) and not result.success:
        result.error = _provider_error_excerpt(result.error, cfg, PROVIDER_ERROR_MAX_LENGTH)
    return result


def _safe_gallery_slug(value: object, fallback: str, max_length: int = 64) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_value)
    slug = re.sub(r"_+", "_", slug).strip("_-")
    safe_fallback = re.sub(r"[^A-Za-z0-9_-]+", "_", str(fallback or "image"))
    safe_fallback = re.sub(r"_+", "_", safe_fallback).strip("_-") or "image"
    if not slug:
        slug = safe_fallback
    if slug.upper() in _WINDOWS_RESERVED_FILENAMES:
        slug = f"{safe_fallback}_{slug}"
    slug = slug[:max_length].rstrip("_-")
    return slug or safe_fallback[:max_length]


def _save_image(
    data: bytes,
    model_id: str,
    prompt_short: str,
    full_prompt: str = "",
    *,
    generation_metadata: Optional[Dict[str, Any]] = None,
    declared_mime: object = None,
    max_pixels: int = GENERATED_IMAGE_MAX_PIXELS,
    max_dimension: int = GENERATED_IMAGE_MAX_DIMENSION,
) -> str:
    """保存图片到本地图库，将 prompt 写入 PNG 元数据"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_model = _safe_gallery_slug(model_id, "model")
    safe_short = _safe_gallery_slug(prompt_short, "image", 30)

    source, _inspection = _open_validated_generated_image(
        data,
        declared_mime=declared_mime,
        max_pixels=max_pixels,
        max_dimension=max_dimension,
        load_pixels=True,
    )

    normalized = source
    try:
        if source.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"}:
            normalized = source.convert("RGBA" if "A" in source.getbands() else "RGB")
        save_options = {}
        if full_prompt or generation_metadata:
            from PIL import PngImagePlugin

            metadata = PngImagePlugin.PngInfo()
            if full_prompt:
                metadata.add_text("Prompt", full_prompt)
            metadata.add_text("Model", model_id)
            metadata.add_text("CreatedAt", ts)
            if generation_metadata:
                metadata.add_text(
                    "GenBoxGenerationMetadata",
                    json.dumps(
                        generation_metadata,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                )
            save_options["pnginfo"] = metadata
        output = BytesIO()
        normalized.save(output, format="PNG", **save_options)
        png_data = output.getvalue()
    except Exception as exc:
        raise ValueError("generated image payload could not be encoded as PNG") from exc
    finally:
        if normalized is not source:
            normalized.close()
        source.close()

    gallery_root = GALLERY_DIR.resolve()
    temporary_path = None
    with _IMAGE_SAVE_LOCK:
        for _ in range(16):
            filename = f"{safe_model}_{ts}_{safe_short}_{uuid.uuid4().hex[:6]}.png"
            out_path = (gallery_root / filename).resolve()
            if out_path.parent != gallery_root:
                raise ValueError("generated image destination is outside the gallery")
            if not out_path.exists():
                break
        else:
            raise FileExistsError("unable to allocate a unique gallery image filename")

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{out_path.stem}.",
                suffix=".tmp",
                dir=gallery_root,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name).resolve()
                if temporary_path.parent != gallery_root:
                    raise ValueError("generated image temporary file is outside the gallery")
                temporary.write(png_data)
                temporary.flush()
                os.fsync(temporary.fileno())
            if out_path.exists():
                raise FileExistsError("gallery image destination already exists")
            os.replace(temporary_path, out_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
    return str(out_path)


# ──────────────────────────────────────────────────────────────
# 协议路由：根据 base_url 或 provider id 判断 API 协议
# ──────────────────────────────────────────────────────────────
def _detect_protocol(cfg: ProviderConfig) -> str:
    """
    检测 API 协议类型:
    - "openai": OpenAI 兼容 (包括 GPT Image, Flux, SD 等)
    - "gemini": Google Gemini 原生 API
    - "qwen": Qwen2API (兼容 OpenAI 但路径不同)
    - "agnes": Agnes AI (兼容 OpenAI 但 image/response_format 放在 extra_body)
    
    优先级: URL > Provider ID > Model 名称
    （URL 最可靠：第三方代理 + /v1 → 必定 OpenAI 兼容）
    """
    url_lower = cfg.base_url.lower()

    # ── 1. URL 最优先 ──
    # Google 原生 API → Gemini 协议
    is_google_native = ("googleapis" in url_lower or "gemini.google.com" in url_lower)
    if is_google_native:
        return "gemini"
    # 特定关键字优先于通用 /v1 检测
    if "agnes" in url_lower:
        return "agnes"
    if "qwen" in url_lower or "wanx" in url_lower:
        return "qwen"
    # URL 包含 /v1 且不是 googleapis → 第三方 OpenAI 兼容代理
    if url_lower.rstrip('/').endswith('/v1'):
        return "openai"

    # ── 2. Provider ID 次之 ──
    pid = cfg.id.lower()
    if "agnes" in pid:
        return "agnes"
    if "qwen" in pid or "wanx" in pid:
        return "qwen"
    # id == "gemini" 但 URL 不是 googleapis → 不走原生协议，走默认 OpenAI

    # ── 3. Model 名称最后（仅限明确的非通用场景）──
    model_lower = cfg.model.lower()
    if "agnes" in model_lower:
        return "agnes"
    if "wanx" in model_lower or "qwen" in model_lower:
        return "qwen"

    # 默认走 OpenAI 兼容协议（覆盖绝大多数第三方服务）
    return "openai"


# ──────────────────────────────────────────────────────────────
# 通用生成器（一个函数处理所有 Provider）
# ──────────────────────────────────────────────────────────────
async def generate_for_provider(
    cfg: ProviderConfig,
    prompt: str,
    **kwargs
) -> ImageResult:
    """
    根据 Provider 配置自动选择协议并生图
    这是核心入口，所有 Provider 都走这里
    支持 t2i (文生图) 和 i2i (图生图) 两种模式
    支持多端点轮询（endpoints 字段）+ 多账号轮询（api_keys 字段）
    """
    from .key_pool import key_pool_manager

    requested_protocol = kwargs.get("protocol")
    protocol = str(requested_protocol).strip().lower() if requested_protocol else _detect_protocol(cfg)
    dispatch_kwargs = dict(kwargs)
    dispatch_kwargs.pop("protocol", None)
    precision_post_budget = None
    if str(dispatch_kwargs.get("mode") or "").strip().lower() == "precision_edit":
        precision_post_budget = PrecisionEditPostBudget()
        dispatch_kwargs["_precision_post_budget"] = precision_post_budget

    # 获取端点列表（endpoints 优先，fallback 到 base_url+api_key）
    endpoints = cfg.get_active_endpoints()

    if endpoints:
        # 多端点模式：逐个尝试
        endpoint_errors = []
        last_structured_failure = None
        for endpoint_index, ep in enumerate(endpoints, start=1):
            if not ep.url or not ep.key:
                continue
            result = await _try_generate_with_endpoint(
                cfg, prompt, ep.url, ep.key, protocol, **dispatch_kwargs
            )
            result = _sanitize_failed_image_result(result, cfg)
            if result.success:
                return result
            if result.error_code:
                last_structured_failure = result
            endpoint_errors.append((endpoint_index, ep, result.error))
            if precision_post_budget is not None and precision_post_budget.exhausted:
                break
        failure_detail = _endpoint_failure_summary(cfg, endpoint_errors)
        error = f"[{cfg.name}] 所有端点均失败: {_friendly_generation_error(failure_detail)}"
        return ImageResult(
            success=False,
            error=_provider_error_text(error, cfg)[:PROVIDER_ERROR_MAX_LENGTH],
            model=cfg.id,
            error_code=(
                last_structured_failure.error_code
                if last_structured_failure is not None
                else None
            ),
            error_details=(
                last_structured_failure.error_details
                if last_structured_failure is not None
                else None
            ),
        )
    else:
        # 旧模式：单 URL + 多 Key 轮询
        effective_keys = cfg.get_effective_keys()
        if not effective_keys:
            return ImageResult(success=False, error=f"[{cfg.name}] API Key 未配置", model=cfg.id)

        pool = key_pool_manager.get_or_create(cfg.id, effective_keys)
        api_key = await pool.get_key()
        if not api_key:
            return ImageResult(success=False, error=f"[{cfg.name}] 所有 API Key 均在冷却中，请稍后重试", model=cfg.id)

        original_key = cfg.api_key
        cfg.api_key = api_key
        try:
            result = await _dispatch_generate(cfg, prompt, protocol, **dispatch_kwargs)
        except ProviderResponseValidationError as exc:
            result = _provider_response_failure(cfg, exc)
        except Exception as e:
            result = ImageResult(
                success=False,
                error=f"[{cfg.name}] {_provider_exception_text(e, cfg)}",
                model=cfg.id,
            )
        result = _sanitize_failed_image_result(result, cfg)

        if result.success:
            pool.mark_success(api_key)
        else:
            error_msg = (result.error or "").lower()
            if "429" in error_msg or "too many requests" in error_msg or "insufficient_quota" in error_msg or "quota" in error_msg:
                retry_after = 0.0
                if "retry" in error_msg:
                    import re
                    m = re.search(r'retry[_-]?after[:\s]*(\d+)', error_msg)
                    if m:
                        retry_after = float(m.group(1))
                pool.mark_error(api_key, retry_after)
            elif "401" in error_msg or "unauthorized" in error_msg or "invalid" in error_msg:
                pool.mark_error(api_key, retry_after=600.0)

        cfg.api_key = original_key
        return result


async def _try_generate_with_endpoint(cfg, prompt, url, key, protocol, **kwargs) -> ImageResult:
    """使用指定端点尝试生成（临时注入 url 和 key）"""
    original_url = cfg.base_url
    original_key = cfg.api_key
    cfg.base_url = url
    cfg.api_key = key
    try:
        result = await _dispatch_generate(cfg, prompt, protocol, **kwargs)
    except ProviderResponseValidationError as exc:
        result = _provider_response_failure(cfg, exc)
    except Exception as e:
        result = ImageResult(
            success=False,
            error=f"[{cfg.name}] {_provider_exception_text(e, cfg)}",
            model=cfg.id,
        )
    finally:
        cfg.base_url = original_url
        cfg.api_key = original_key
    return _sanitize_failed_image_result(result, cfg)


async def _dispatch_generate(cfg, prompt, protocol, **kwargs):
    """内部调度：根据协议选择生成函数"""
    mode = str(kwargs.get("mode") or "").strip().lower()
    has_precision_fields = any(
        kwargs.get(key) not in (None, "", False, [])
        for key in (
            "annotation_image_data",
            "annotation_contract",
            "annotations",
            "precision_canvas_only",
            "precision_size_mode",
            "precision_target_size",
            "precision_resize_prompt",
            "precision_output_size_policy",
            "precision_edit_authorized",
        )
    )
    if mode == "precision_edit" or has_precision_fields:
        if mode != "precision_edit":
            return _precision_edit_failure(
                cfg,
                "precision_edit_mode_required",
                "annotation fields are accepted only when mode=precision_edit",
            )
        return await _dispatch_precision_edit(cfg, prompt, protocol, **kwargs)

    has_inpaint_fields = any(
        kwargs.get(key) not in (None, "", False)
        for key in ("mask_data", "mask_contract", "inpaint_authorized")
    )
    if mode == "inpaint" or has_inpaint_fields:
        if mode != "inpaint":
            return _inpaint_failure(
                cfg,
                "inpaint_mode_required",
                "mask fields are accepted only when mode=inpaint",
            )
        return await _dispatch_inpaint(cfg, prompt, protocol, **kwargs)

    image_data = kwargs.get("image_data")
    image_data_list = [item for item in (kwargs.get("image_data_list") or []) if item]
    if not image_data and image_data_list:
        image_data = image_data_list[0]
    strength = kwargs.get("strength", 0.55)

    # 图生图
    if image_data and protocol == "openai":
        kwargs_copy = {k: v for k, v in kwargs.items() if k not in ("image_data", "image_data_list", "strength")}
        return await _gen_openai_edit(cfg, prompt, image_data, strength, image_data_list=image_data_list, **kwargs_copy)
    elif image_data and protocol == "gemini":
        kwargs_copy = {k: v for k, v in kwargs.items() if k not in ("image_data", "image_data_list", "strength")}
        return await _gen_gemini_edit(cfg, prompt, image_data, strength, image_data_list=image_data_list, **kwargs_copy)
    elif image_data and protocol == "agnes":
        kwargs_copy = {k: v for k, v in kwargs.items()}
        return await _gen_agnes(cfg, prompt, **kwargs_copy)
    elif image_data:
        return ImageResult(success=False, error=f"[{cfg.name}] 图生图 (I2I) 暂不支持 {protocol} 协议", model=cfg.id)

    # 文生图
    if protocol == "gemini":
        return await _gen_gemini(cfg, prompt, **kwargs)
    elif protocol == "qwen":
        return await _gen_qwen(cfg, prompt, **kwargs)
    elif protocol == "agnes":
        return await _gen_agnes(cfg, prompt, **kwargs)
    else:
        return await _gen_openai(cfg, prompt, **kwargs)


def _generated_image_failure(
    cfg: ProviderConfig,
    code: str,
    detail: str,
    *,
    details: Optional[Dict[str, Any]] = None,
) -> ImageResult:
    return ImageResult(
        success=False,
        error=_provider_error_text(f"[{cfg.name}] {code}: {detail}", cfg)[:PROVIDER_ERROR_MAX_LENGTH],
        model=cfg.id,
        error_code=code,
        error_details=details,
    )


def _generated_image_validation_failure(
    cfg: ProviderConfig,
    exc: GeneratedImageValidationError,
    *,
    code: str | None = None,
) -> ImageResult:
    details = {"validation_code": exc.code, **exc.details}
    return _generated_image_failure(
        cfg,
        code or exc.code,
        str(exc),
        details=details,
    )


def _provider_response_failure(
    cfg: ProviderConfig,
    exc: ProviderResponseValidationError,
    *,
    code: str | None = None,
) -> ImageResult:
    return _generated_image_failure(
        cfg,
        code or exc.code,
        str(exc),
        details={"validation_code": exc.code, **exc.details},
    )


def _generated_image_download_error_details(error: object) -> Optional[Dict[str, Any]]:
    validation_code = str(error or "").partition(":")[0].strip()
    if validation_code.startswith("generated_image_"):
        return {"validation_code": validation_code}
    return None


def _inpaint_failure(
    cfg: ProviderConfig,
    code: str,
    detail: str,
    *,
    details: Optional[Dict[str, Any]] = None,
) -> ImageResult:
    return _generated_image_failure(cfg, code, detail, details=details)


def _precision_edit_failure(
    cfg: ProviderConfig,
    code: str,
    detail: str,
    *,
    details: Optional[Dict[str, Any]] = None,
) -> ImageResult:
    return ImageResult(
        success=False,
        error=_provider_error_text(f"[{cfg.name}] {code}: {detail}", cfg)[:PROVIDER_ERROR_MAX_LENGTH],
        model=cfg.id,
        error_code=code,
        error_details=details,
    )


def _precision_annotation_text_is_safe(value: str) -> bool:
    if not value.isprintable():
        return False
    if re.search(r"(?i)(?:https?|ftp|file|data|javascript):|www\.", value):
        return False
    if "<" in value or ">" in value:
        return False
    return not re.search(
        r"(?:^|\s)(?:[A-Za-z]:[\\/]|\\\\|\.\.[\\/]|/(?:[\w.-]+/)+[\w.-]+)",
        value,
    )


def _normalized_precision_annotations(
    value: object,
    contract: str = PRECISION_ANNOTATION_CONTRACT_V1,
) -> list[dict]:
    """Defense-in-depth validation for direct provider callers."""
    if not isinstance(value, list) or not value or len(value) > 100:
        raise ValueError("annotations must contain between 1 and 100 items")
    is_v2 = contract == PRECISION_ANNOTATION_CONTRACT_V2
    is_v3 = contract == PRECISION_ANNOTATION_CONTRACT_V3
    is_structured = is_v2 or is_v3
    if contract == PRECISION_ANNOTATION_CONTRACT_V1:
        field_sets = {
            "arrow": {"type", "x1", "y1", "x2", "y2"},
            "rectangle": {"type", "x", "y", "width", "height"},
            "text": {"type", "x", "y", "text"},
        }
    elif is_v2:
        field_sets = {
            "arrow": {"type", "label", "instruction", "x1", "y1", "x2", "y2"},
            "rectangle": {"type", "label", "instruction", "x", "y", "width", "height"},
            "text": {"type", "label", "text", "instruction", "x", "y"},
        }
    elif is_v3:
        field_sets = {
            "arrow": {"type", "label", "instruction", "x1", "y1", "x2", "y2"},
            "rectangle": {"type", "label", "instruction", "x", "y", "width", "height"},
            "ellipse": {"type", "label", "instruction", "x", "y", "width", "height"},
            "brush": {"type", "label", "instruction", "points"},
            "text": {"type", "label", "text", "instruction", "x", "y"},
        }
    else:
        raise ValueError("annotation contract is unsupported")
    coordinate_sets = {
        "arrow": ("x1", "y1", "x2", "y2"),
        "rectangle": ("x", "y", "width", "height"),
        "ellipse": ("x", "y", "width", "height"),
        "brush": (),
        "text": ("x", "y"),
    }
    output = []
    total_text = 0
    seen_labels = set()
    total_brush_points = 0
    for index, raw in enumerate(value):
        if not isinstance(raw, dict) or raw.get("type") not in field_sets:
            raise ValueError(f"annotations[{index}] has an unsupported type")
        annotation_type = raw["type"]
        actual_fields = set(raw)
        required_fields = field_sets[annotation_type]
        if is_structured and annotation_type == "text":
            required_fields = required_fields - {"instruction"}
        if actual_fields - field_sets[annotation_type] or required_fields - actual_fields:
            raise ValueError(f"annotations[{index}] has missing or unsupported fields")
        normalized = {"type": annotation_type}
        if is_structured:
            label = raw.get("label")
            if isinstance(label, bool) or not isinstance(label, int) or label <= 0:
                raise ValueError(f"annotations[{index}].label must be a positive integer")
            if label in seen_labels:
                raise ValueError(f"annotations[{index}].label must be unique")
            seen_labels.add(label)
            normalized["label"] = label
        for field_name in coordinate_sets[annotation_type]:
            coordinate = raw[field_name]
            if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
                raise ValueError(f"annotations[{index}].{field_name} must be numeric")
            coordinate = float(coordinate)
            if not math.isfinite(coordinate) or coordinate < 0.0 or coordinate > 1.0:
                raise ValueError(f"annotations[{index}].{field_name} must be between 0 and 1")
            normalized[field_name] = coordinate
        if annotation_type == "arrow":
            if normalized["x1"] == normalized["x2"] and normalized["y1"] == normalized["y2"]:
                raise ValueError(f"annotations[{index}] arrow has identical endpoints")
        elif annotation_type in {"rectangle", "ellipse"}:
            if normalized["width"] <= 0.0 or normalized["height"] <= 0.0:
                raise ValueError(f"annotations[{index}] {annotation_type} has an empty area")
            if normalized["x"] + normalized["width"] > 1.0 or normalized["y"] + normalized["height"] > 1.0:
                raise ValueError(f"annotations[{index}] {annotation_type} exceeds the canvas")
        elif annotation_type == "brush":
            points = raw.get("points")
            if not isinstance(points, list) or len(points) < 2 or len(points) > 1024:
                raise ValueError(f"annotations[{index}].points must contain 2 to 1024 points")
            normalized_points = []
            for point_index, point in enumerate(points):
                if not isinstance(point, dict) or set(point) != {"x", "y"}:
                    raise ValueError(f"annotations[{index}].points[{point_index}] must contain only x and y")
                normalized_point = {}
                for field_name in ("x", "y"):
                    coordinate = point[field_name]
                    if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
                        raise ValueError(f"annotations[{index}].points[{point_index}].{field_name} must be numeric")
                    coordinate = float(coordinate)
                    if not math.isfinite(coordinate) or coordinate < 0.0 or coordinate > 1.0:
                        raise ValueError(f"annotations[{index}].points[{point_index}].{field_name} must be between 0 and 1")
                    normalized_point[field_name] = coordinate
                normalized_points.append(normalized_point)
            if all(point == normalized_points[0] for point in normalized_points[1:]):
                raise ValueError(f"annotations[{index}].points must describe a non-empty path")
            total_brush_points += len(normalized_points)
            if total_brush_points > 4096:
                raise ValueError("brush paths exceed the total point limit")
            normalized["points"] = normalized_points
        if annotation_type == "text":
            text_value = raw["text"]
            if not isinstance(text_value, str) or not text_value.strip() or len(text_value.strip()) > 500:
                raise ValueError(f"annotations[{index}].text is empty or too long")
            text_value = text_value.strip()
            if not _precision_annotation_text_is_safe(text_value):
                raise ValueError(f"annotations[{index}].text contains a forbidden resource reference")
            total_text += len(text_value)
            if total_text > 4000:
                raise ValueError("annotation text exceeds the total length limit")
            normalized["text"] = text_value
        if is_structured:
            instruction = raw.get("instruction")
            if annotation_type in {"arrow", "rectangle", "ellipse", "brush"} and (
                not isinstance(instruction, str) or not instruction.strip()
            ):
                raise ValueError(f"annotations[{index}].instruction is required")
            if instruction is not None:
                if not isinstance(instruction, str) or not instruction.strip():
                    raise ValueError(f"annotations[{index}].instruction must be omitted or non-empty")
                instruction = instruction.strip()
                if len(instruction) > 500:
                    raise ValueError(f"annotations[{index}].instruction is too long")
                if not _precision_annotation_text_is_safe(instruction):
                    raise ValueError(f"annotations[{index}].instruction contains a forbidden resource reference")
                total_text += len(instruction)
                if total_text > 4000:
                    raise ValueError("annotation text exceeds the total length limit")
                normalized["instruction"] = instruction
        output.append(normalized)
    if is_structured:
        output.sort(key=lambda item: item["label"])
    return output


def _precision_model_is_authorized(cfg: ProviderConfig, model_id: str) -> bool:
    capabilities = getattr(cfg, "capabilities", None)
    if not isinstance(capabilities, dict) or capabilities.get(PRECISION_EDIT_CAPABILITY) is not True:
        return False
    resolution = _precision_model_capability_resolution(cfg, model_id)
    return resolution.structure_valid and resolution.precision_edit_confirmed


def _precision_model_capability_resolution(cfg: ProviderConfig, model_id: str):
    extra = getattr(cfg, "extra", None)
    model_capabilities = extra.get("model_capabilities") if isinstance(extra, dict) else None
    return resolve_precision_model_capability(
        model_capabilities,
        model_id,
        max_output_pixels=PRECISION_MAX_OUTPUT_PIXELS,
    )


def _precision_edit_transport_profile(
    cfg: ProviderConfig,
) -> PrecisionEditTransportProfile | None:
    """Resolve an allowlisted profile, preserving the historical request shape."""
    configured = getattr(cfg, "precision_edit_profile", None)
    if configured is None:
        configured = LEGACY_PRECISION_EDIT_PROFILE
    if isinstance(configured, PrecisionEditProfile):
        configured = configured.value
    return PRECISION_EDIT_TRANSPORT_PROFILES.get(str(configured or "").strip())


def _precision_declared_sizes(model_capabilities: object) -> set[str]:
    """Return only valid, explicitly declared WIDTHxHEIGHT dimensions."""
    _present, valid, sizes, _reason = precision_capability_size_declaration(
        model_capabilities,
        max_output_pixels=PRECISION_MAX_OUTPUT_PIXELS,
    )
    return set(sizes) if valid else set()


def _normalize_precision_size(value: object) -> str | None:
    return normalize_precision_capability_size(
        value,
        max_output_pixels=PRECISION_MAX_OUTPUT_PIXELS,
    )


def _precision_size_tuple(value: str) -> tuple[int, int]:
    width, height = (int(part) for part in value.split("x", 1))
    return width, height


def _precision_ratio_label(size: str) -> str:
    width, height = _precision_size_tuple(size)
    divisor = math.gcd(width, height)
    reduced = (width // divisor, height // divisor)
    if reduced == (7, 3):
        return "21:9"
    return f"{reduced[0]}:{reduced[1]}"


def _precision_aspect_ratio_delta(
    requested_size: tuple[int, int],
    actual_size: tuple[int, int],
) -> float:
    requested_ratio = requested_size[0] / requested_size[1]
    actual_ratio = actual_size[0] / actual_size[1]
    return abs(actual_ratio - requested_ratio) / requested_ratio


def _inspect_precision_output(image_data: bytes) -> tuple[tuple[int, int], str, bool]:
    try:
        inspection = _inspect_generated_image(
            image_data,
            max_pixels=PRECISION_MAX_OUTPUT_PIXELS,
            max_dimension=GENERATED_IMAGE_MAX_DIMENSION,
        )
    except GeneratedImageValidationError as exc:
        raise exc
    return (
        (inspection.width, inspection.height),
        inspection.image_format,
        inspection.has_alpha,
    )


def _fit_crop_precision_output(
    image_data: bytes,
    requested_size: tuple[int, int],
) -> tuple[bytes, Dict[str, Any]] | None:
    source, inspection = _open_validated_generated_image(
        image_data,
        max_pixels=PRECISION_MAX_OUTPUT_PIXELS,
        max_dimension=GENERATED_IMAGE_MAX_DIMENSION,
        load_pixels=True,
    )
    try:
        actual_size = (inspection.width, inspection.height)
        source_format = inspection.image_format
        source_has_alpha = inspection.has_alpha
        aspect_ratio_delta = _precision_aspect_ratio_delta(requested_size, actual_size)
        scale_factor = max(
            requested_size[0] / actual_size[0],
            requested_size[1] / actual_size[1],
        )
        if (
            aspect_ratio_delta > PRECISION_FIT_CROP_MAX_ASPECT_RATIO_DELTA
            or scale_factor > PRECISION_FIT_CROP_MAX_UPSCALE
        ):
            return None

        normalized = source.convert("RGBA" if source_has_alpha else "RGB")
    finally:
        source.close()
    try:
        scaled_size = (
            max(requested_size[0], math.ceil(actual_size[0] * scale_factor)),
            max(requested_size[1], math.ceil(actual_size[1] * scale_factor)),
        )
        resized = normalized.resize(scaled_size, Image.Resampling.LANCZOS)
        try:
            left = (scaled_size[0] - requested_size[0]) // 2
            top = (scaled_size[1] - requested_size[1]) // 2
            crop_box = (
                left,
                top,
                left + requested_size[0],
                top + requested_size[1],
            )
            final_image = resized.crop(crop_box)
            try:
                output = BytesIO()
                final_image.save(output, format="PNG")
            finally:
                final_image.close()
        finally:
            resized.close()
    finally:
        normalized.close()

    transform = {
        "operation": "center_cover_crop",
        "scale_factor": round(scale_factor, 8),
        "scaled_size": f"{scaled_size[0]}x{scaled_size[1]}",
        "crop_box": list(crop_box),
        "resample": "LANCZOS",
        "source_format": source_format,
        "output_format": "PNG",
        "alpha_preserved": source_has_alpha,
    }
    return output.getvalue(), transform


def _precision_model_declared_sizes(cfg: ProviderConfig, model_id: str) -> set[str]:
    resolution = _precision_model_capability_resolution(cfg, model_id)
    if not resolution.structure_valid or not resolution.size_declaration_valid:
        return set()
    return set(resolution.supported_sizes)


def _precision_model_has_size_declaration(cfg: ProviderConfig, model_id: str) -> bool:
    resolution = _precision_model_capability_resolution(cfg, model_id)
    return resolution.structure_valid and resolution.size_declaration_present


def _precision_preserve_source_size_error(
    cfg: ProviderConfig,
    model_id: str,
    image_size: tuple[int, int],
) -> tuple[str, str] | None:
    width, height = image_size
    if (
        width < 64
        or width > 8192
        or height < 64
        or height > 8192
        or width * height > PRECISION_MAX_OUTPUT_PIXELS
    ):
        return (
            "precision_edit_source_size_invalid",
            "single-image precision edit requires source dimensions between 64 and 8192 pixels "
            "per side and within the configured pixel limit",
        )
    source_size = f"{width}x{height}"
    resolution = _precision_model_capability_resolution(cfg, model_id)
    selected_record = None
    extra = getattr(cfg, "extra", None)
    model_capabilities = extra.get("model_capabilities") if isinstance(extra, dict) else None
    if isinstance(model_capabilities, dict):
        selected_record = model_capabilities.get(model_id)
    selected_declares_alias = isinstance(selected_record, dict) and any(
        field in selected_record for field in ("alias_of", "canonical_model")
    )
    if not resolution.structure_valid or not resolution.precision_edit_confirmed:
        if selected_declares_alias:
            return (
                "precision_edit_source_size_not_declared",
                f"the selected model does not declare the source size {source_size}",
            )
        return (
            "precision_edit_size_capability_unknown",
            "the selected model has no explicit supported size list",
        )
    if not resolution.size_declaration_present:
        if selected_declares_alias:
            return (
                "precision_edit_source_size_not_declared",
                f"the selected model does not declare the source size {source_size}",
            )
        return (
            "precision_edit_size_capability_unknown",
            "the selected model has no explicit supported size list",
        )
    if not resolution.size_declaration_valid:
        return (
            "precision_edit_size_capability_unknown",
            "the selected model declares image sizes but none are valid for precision editing",
        )
    declared = set(resolution.supported_sizes)
    if source_size not in declared:
        return (
            "precision_edit_source_size_not_declared",
            f"the selected model does not declare the source size {source_size}",
        )
    return None


def _precision_size_error(
    cfg: ProviderConfig,
    model_id: str,
    mode: str,
    target: str,
    generic_size: str = "",
) -> tuple[str, str] | None:
    if mode == "preserve":
        if target or generic_size not in {"", "auto"}:
            return "precision_preserve_size_conflict", "preserve mode accepts only size=auto and no target size"
        return None
    if mode != "resize":
        return "precision_size_mode_invalid", "unsupported precision size mode"
    if _normalize_precision_size(target) is None:
        return "precision_target_size_invalid", "resize mode requires a valid WIDTHxHEIGHT target"
    declared = _precision_model_declared_sizes(cfg, model_id)
    if not declared:
        return "precision_edit_size_capability_unknown", "the selected model has no explicit supported size list"
    if target not in declared:
        return "precision_edit_target_size_not_declared", "the selected model has not declared this target size"
    return None


def _generated_image_address_is_safe(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return ip not in GENERATED_IMAGE_METADATA_ADDRESSES and ip.is_global


def _resolve_generated_image_url(url: str) -> tuple[object | None, tuple[str, ...], str | None]:
    try:
        parsed = urlsplit(str(url or ""))
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return None, (), "image URL must use HTTPS"
        if parsed.username is not None or parsed.password is not None:
            return None, (), "image URL must not contain credentials"
        port = parsed.port or 443
        if port != 443 or port in GENERATED_IMAGE_BLOCKED_PORTS:
            return None, (), "image URL uses a disallowed port"
        host = parsed.hostname.rstrip(".").lower()
        if (
            host == "localhost"
            or host in GENERATED_IMAGE_METADATA_HOSTS
            or host.endswith(".localhost")
            or host.endswith(".internal")
        ):
            return None, (), "image URL targets a local or metadata host"
        try:
            addresses = [str(ipaddress.ip_address(host))]
        except ValueError:
            resolved = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            if not resolved:
                return None, (), "image URL host did not resolve"
            addresses = []
            for item in resolved:
                address = str(item[4][0])
                if address not in addresses:
                    addresses.append(address)
        for address in addresses:
            if not _generated_image_address_is_safe(address):
                return None, (), (
                    "image URL targets a private, shared, link-local, reserved, "
                    "unallocated, or metadata address"
                )
        return parsed, tuple(addresses), None
    except (ValueError, OSError, socket.gaierror):
        return None, (), "image URL is invalid or unsafe"


def _generated_image_url_is_safe(url: str) -> tuple[bool, str]:
    _parsed, _addresses, error = _resolve_generated_image_url(url)
    return error is None, error or ""


def _bound_generated_image_request(parsed, address: str) -> tuple[str, dict, dict]:
    host = parsed.hostname.rstrip(".").encode("idna").decode("ascii")
    ip = ipaddress.ip_address(address)
    netloc = f"[{ip.compressed}]" if ip.version == 6 else ip.compressed
    bound_url = parsed._replace(netloc=netloc).geturl()
    return bound_url, {"Host": host}, {"sni_hostname": host}


def _generated_image_http_client():
    # Generated media is untrusted input. Never let HTTP(S)_PROXY or provider
    # proxy configuration resolve its hostname or choose its connection target.
    return httpx.AsyncClient(
        timeout=180.0,
        proxy=None,
        trust_env=False,
        verify=True,
    )


async def _download_generated_image(
    client,
    image_url: str,
    *,
    max_pixels: int | None = None,
    max_dimension: int = GENERATED_IMAGE_MAX_DIMENSION,
) -> tuple[bytes | None, str | None]:
    """Download an upstream image through a bounded, IP-pinned SSRF gate."""
    current = str(image_url or "")
    for redirect_count in range(GENERATED_IMAGE_MAX_REDIRECTS + 1):
        parsed, addresses, error = _resolve_generated_image_url(current)
        if error:
            return None, error
        bound_url, headers, extensions = _bound_generated_image_request(parsed, addresses[0])
        async with _generated_image_http_client() as download_client:
            async with download_client.stream(
                "GET",
                bound_url,
                headers=headers,
                extensions=extensions,
                follow_redirects=False,
            ) as response:
                if 300 <= response.status_code < 400:
                    location = response.headers.get("location")
                    if not location or redirect_count >= GENERATED_IMAGE_MAX_REDIRECTS:
                        return None, "image URL redirect limit exceeded"
                    current = urljoin(current, location)
                    continue
                if response.status_code >= 400:
                    return None, f"HTTP {response.status_code}"
                content_type = str(response.headers.get("content-type", "")).split(";", 1)[0].strip().lower()
                if content_type not in GENERATED_IMAGE_CONTENT_TYPES:
                    return None, "image URL response is not an allowed image Content-Type"
                content_length = response.headers.get("content-length")
                try:
                    if content_length is not None and int(content_length) > GENERATED_IMAGE_MAX_BYTES:
                        return None, "image URL response is too large"
                except (TypeError, ValueError):
                    return None, "image URL response has an invalid Content-Length"
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > GENERATED_IMAGE_MAX_BYTES:
                        return None, "image URL response is too large"
                image_data = bytes(content)
                if max_pixels is not None:
                    try:
                        _inspect_generated_image(
                            image_data,
                            declared_mime=content_type,
                            max_pixels=max_pixels,
                            max_dimension=max_dimension,
                        )
                    except GeneratedImageValidationError as exc:
                        return None, f"{exc.code}: {exc}"
                return image_data, None
    return None, "image URL redirect limit exceeded"


async def _dispatch_precision_edit(
    cfg: ProviderConfig,
    prompt: str,
    protocol: str,
    **kwargs,
) -> ImageResult:
    """Fail closed unless annotation editing has a verified OpenAI transport."""
    endpoint_type = str(getattr(cfg, "endpoint_type", "auto") or "auto").strip().lower()
    effective_protocol = str(protocol or "auto").strip().lower()
    model_id = str(kwargs.get("model") or cfg.model or "").strip()
    if endpoint_type != "openai" or effective_protocol != "openai":
        return _precision_edit_failure(
            cfg,
            "precision_edit_protocol_unverified",
            "precision_edit requires an explicit OpenAI-compatible endpoint type",
        )
    if kwargs.get("precision_edit_authorized") is not True or not _precision_model_is_authorized(cfg, model_id):
        return _precision_edit_failure(
            cfg,
            "precision_edit_capability_not_authorized",
            f"model={model_id or 'unknown'} requires explicit capability={PRECISION_EDIT_CAPABILITY}",
        )
    transport_profile = _precision_edit_transport_profile(cfg)
    if transport_profile is None:
        return _precision_edit_failure(
            cfg,
            "precision_edit_profile_unsupported",
            "precision_edit requires an allowlisted transport profile",
        )
    size_mode = str(kwargs.get("precision_size_mode") or "preserve").strip().lower()
    target_size = str(kwargs.get("precision_target_size") or "")
    generic_size = str(kwargs.get("size") or "").strip().lower()
    output_size_policy = str(kwargs.get("precision_output_size_policy") or "strict")
    if output_size_policy not in PRECISION_OUTPUT_SIZE_POLICIES:
        return _precision_edit_failure(
            cfg,
            "precision_output_size_policy_invalid",
            "precision_output_size_policy must be strict or fit_crop",
            details={"allowed_policies": list(PRECISION_OUTPUT_SIZE_POLICIES)},
        )
    if size_mode != "resize" and "precision_output_size_policy" in kwargs:
        return _precision_edit_failure(
            cfg,
            "precision_output_size_policy_not_allowed",
            "precision_output_size_policy is accepted only for precision_edit resize",
        )
    precision_canvas_only = kwargs.get("precision_canvas_only") is True
    annotation_field_names = {
        "annotation_image_data",
        "annotation_contract",
        "annotations",
    }
    if precision_canvas_only and any(key in kwargs for key in annotation_field_names):
        return _precision_edit_failure(
            cfg,
            "precision_resize_annotation_fields_conflict",
            "source-only precision resize does not accept annotation fields",
        )
    if precision_canvas_only and size_mode != "resize":
        return _precision_edit_failure(
            cfg,
            "precision_canvas_only_resize_required",
            "precision_edit without annotations requires precision_size_mode=resize",
        )
    size_error = _precision_size_error(cfg, model_id, size_mode, target_size, generic_size)
    if size_error:
        return _precision_edit_failure(cfg, size_error[0], size_error[1])
    resize_prompt = str(kwargs.get("precision_resize_prompt") or "").strip()
    if size_mode == "resize":
        if not resize_prompt:
            return _precision_edit_failure(
                cfg,
                "precision_resize_prompt_required",
                "resize mode requires composition guidance",
            )
        if len(resize_prompt) > 500 or not _precision_annotation_text_is_safe(resize_prompt):
            return _precision_edit_failure(
                cfg,
                "precision_resize_prompt_invalid",
                "resize guidance is too long or contains a forbidden resource reference",
            )
    annotation_contract = str(kwargs.get("annotation_contract") or "").strip()
    if not precision_canvas_only and annotation_contract not in PRECISION_ANNOTATION_CONTRACTS:
        return _precision_edit_failure(
            cfg,
            "precision_annotation_contract_unsupported",
            "annotation_contract is unsupported",
        )
    if "image_data_list" in kwargs:
        return _precision_edit_failure(
            cfg,
            "precision_edit_single_image_required",
            "precision_edit accepts exactly one source image",
        )
    image_data = kwargs.get("image_data")
    annotation_image_data = kwargs.get("annotation_image_data")
    if not isinstance(image_data, str) or not image_data.strip():
        return _precision_edit_failure(cfg, "precision_edit_image_required", "image_data is required")
    if not precision_canvas_only and (
        not isinstance(annotation_image_data, str) or not annotation_image_data.strip()
    ):
        return _precision_edit_failure(
            cfg,
            "precision_annotation_image_required",
            "annotation_image_data is required",
        )
    prompt_text = str(prompt or "").strip()
    if len(prompt_text) > 2000 or (prompt_text and not _precision_annotation_text_is_safe(prompt_text)):
        return _precision_edit_failure(
            cfg,
            "precision_edit_prompt_invalid",
            "prompt is too long or contains a forbidden resource reference",
        )
    annotations = None
    if not precision_canvas_only:
        try:
            annotations = _normalized_precision_annotations(
                kwargs.get("annotations"),
                annotation_contract,
            )
        except ValueError as exc:
            return _precision_edit_failure(
                cfg,
                "precision_annotations_invalid",
                _provider_exception_text(exc, cfg),
            )

    clean_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key not in {
            "mode",
            "image_data",
            "image_data_list",
            "annotation_image_data",
            "annotation_contract",
            "annotations",
            "precision_canvas_only",
            "precision_edit_authorized",
            "precision_edit_transport_profile",
        }
    }
    return await _gen_openai_precision_edit(
        cfg,
        prompt_text,
        image_data,
        annotation_image_data,
        annotations,
        annotation_contract=annotation_contract,
        precision_canvas_only=precision_canvas_only,
        transport_profile=transport_profile,
        **clean_kwargs,
    )


async def _dispatch_inpaint(
    cfg: ProviderConfig,
    prompt: str,
    protocol: str,
    **kwargs,
) -> ImageResult:
    """Fail-closed dispatch for an explicitly authorized mask edit."""
    endpoint_type = str(getattr(cfg, "endpoint_type", "auto") or "auto").strip().lower()
    effective_protocol = str(protocol or "auto").strip().lower()

    if endpoint_type == "auto" or effective_protocol == "auto":
        return _inpaint_failure(
            cfg,
            "mask_protocol_unverified",
            "inpaint requires an explicit OpenAI-compatible endpoint type",
        )
    if endpoint_type != "openai" or effective_protocol != "openai":
        return _inpaint_failure(
            cfg,
            "mask_protocol_unverified",
            f"inpaint mask transport is unavailable for protocol={effective_protocol}",
        )
    if kwargs.get("inpaint_authorized") is not True:
        return _inpaint_failure(
            cfg,
            "inpaint_capability_not_authorized",
            f"upper layer must authorize capability={INPAINT_CAPABILITY}",
        )
    if kwargs.get("mask_contract") != INPAINT_MASK_CONTRACT:
        return _inpaint_failure(
            cfg,
            "mask_contract_unsupported",
            f"required mask_contract={INPAINT_MASK_CONTRACT}",
        )

    raw_images = kwargs.get("image_data_list") or []
    if not isinstance(raw_images, (list, tuple)):
        return _inpaint_failure(
            cfg,
            "inpaint_single_image_required",
            "image_data_list must contain exactly one base image",
        )
    images = [item for item in raw_images if item]
    legacy_image = kwargs.get("image_data")
    if not images and legacy_image:
        images = [legacy_image]
    elif legacy_image and images and legacy_image != images[0]:
        return _inpaint_failure(
            cfg,
            "inpaint_base_image_conflict",
            "image_data must match the first image_data_list item",
        )
    if len(images) != 1:
        return _inpaint_failure(
            cfg,
            "inpaint_single_image_required",
            "inpaint accepts exactly one base image",
        )

    mask_data = kwargs.get("mask_data")
    if not isinstance(mask_data, str) or not mask_data.strip():
        return _inpaint_failure(
            cfg,
            "inpaint_mask_required",
            "mask_data must contain one PNG mask",
        )

    clean_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key not in {
            "mode",
            "image_data",
            "image_data_list",
            "mask_data",
            "mask_contract",
            "inpaint_authorized",
        }
    }
    return await _gen_openai_inpaint(
        cfg,
        prompt,
        images[0],
        mask_data,
        **clean_kwargs,
    )


async def _http_post_with_retry(
    url,
    headers,
    payload=None,
    *,
    files=None,
    data=None,
    timeout=120.0,
    max_retries=3,
    retry_delay=2.0,
    retry_transport_errors=True,
    post_budget: PrecisionEditPostBudget = None,
    proxy: str = None,
    cfg: ProviderConfig = None,
    response_image_count: int = 1,
):
    """带重试的 HTTP POST，返回 (resp, client) 或抛异常（附带响应体）。
    注意：返回的 client 可能已关闭，调用方需自行管理后续请求。"""
    def response_excerpt(value: Any) -> str:
        if cfg is not None:
            return _provider_error_excerpt(value, cfg, 300)
        return _safe_text(value).strip()[:300]

    async def close_client(client) -> None:
        close = getattr(client, "aclose", None)
        if close is not None:
            await close()

    if files is not None and payload is not None:
        raise ValueError("multipart and JSON payloads are mutually exclusive")
    if files is None and payload is None:
        raise ValueError("a JSON payload or multipart files are required")

    last_exc = None
    for attempt in range(max_retries):
        if post_budget is not None and not post_budget.consume():
            raise last_exc or RuntimeError("HTTP POST budget exhausted")
        client = httpx.AsyncClient(
            timeout=timeout,
            proxy=proxy,
            verify=verify_ssl_enabled(),
        )
        try:
            request_kwargs = {"headers": headers}
            if files is not None:
                request_kwargs.update({"files": files, "data": data or {}})
            else:
                request_kwargs["json"] = payload
            resp = await _stream_bounded_provider_response(
                client,
                "POST",
                url,
                response_image_count=response_image_count,
                **request_kwargs,
            )
            # 429 Too Many Requests 或 5xx 服务器错误 → 重试
            if resp.status_code >= 400:
                body_text = response_excerpt(resp.text) if resp.text else ""
                reason_phrase = str(getattr(resp, "reason_phrase", "")).strip()
                request = getattr(resp, "request", None) or httpx.Request("POST", url)
                retryable = resp.status_code == 429 or resp.status_code >= 500
                await close_client(client)
                if (
                    retryable
                    and attempt < max_retries - 1
                    and (post_budget is None or not post_budget.exhausted)
                ):
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                raise httpx.HTTPStatusError(
                    (
                        f"HTTP {resp.status_code} {reason_phrase} | Response: "
                        f"{translate_upstream_error(body_text)}"
                    ).strip(),
                    request=request,
                    response=resp,
                )
            return resp, client
        except asyncio.CancelledError:
            try:
                await close_client(client)
            except BaseException:
                # Preserve the original cancellation even if transport cleanup fails.
                pass
            raise
        except httpx.HTTPStatusError as e:
            try:
                await close_client(client)
            except Exception:
                pass
            raise
        except ProviderResponseValidationError:
            try:
                await close_client(client)
            except Exception:
                pass
            raise
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            try:
                await close_client(client)
            except Exception:
                pass
            last_exc = e
            if (
                retry_transport_errors
                and attempt < max_retries - 1
                and (post_budget is None or not post_budget.exhausted)
            ):
                await asyncio.sleep(retry_delay * (2 ** attempt))
                continue
            raise
    raise last_exc or Exception("Max retries exceeded")


def _ensure_v1(base_url: str) -> str:
    """Ensure base_url ends with /v1 for OpenAI-compatible APIs."""
    b = base_url.rstrip("/")
    # Already has /v1 or /v1beta or other subpath — leave as-is
    if b.endswith("/v1") or b.endswith("/v1beta"):
        return b
    # Already contains /v1/ as a subpath (e.g. /openai/v1) — leave as-is
    if "/v1/" in b or "/v1beta/" in b:
        return b
    # Bare host — append /v1
    return b + "/v1"


async def _gen_openai(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """OpenAI 兼容协议: POST /images/generations"""
    size = kwargs.get("size") or cfg.size or "1024x1024"
    quality = kwargs.get("quality") or cfg.quality or "standard"
    model_id = kwargs.get("model") or cfg.model

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }
    if quality and quality != "default":
        payload["quality"] = quality

    base = _ensure_v1(cfg.base_url)
    resp, client = await _http_post_with_retry(
        f"{base}/images/generations",
        headers=headers, payload=payload,
        proxy=_get_proxy_url(cfg),
        cfg=cfg,
    )
    data = _parse_provider_json_response(resp)

    img_info = data.get("data", [{}])[0]
    b64 = img_info.get("b64_json")
    img_url = img_info.get("url")

    if b64:
        try:
            img_data = _decode_generated_image_base64(b64)
        except GeneratedImageValidationError as exc:
            return _generated_image_validation_failure(cfg, exc)
    elif img_url:
        img_data, download_error = await _download_generated_image(
            client, img_url, max_pixels=GENERATED_IMAGE_MAX_PIXELS
        )
        if download_error:
            return _generated_image_failure(
                cfg,
                "image_result_download_rejected",
                download_error,
                details=_generated_image_download_error_details(download_error),
            )
    else:
        return ImageResult(success=False, error=f"[{cfg.name}] API 返回无图片数据", model=cfg.id)

    size_error = _validate_generated_size(img_data, size, cfg)
    if size_error and kwargs.get("exact_ratio_crop") is True:
        cropped = _crop_generated_size(img_data, size)
        if cropped is not None:
            img_data = cropped
            size_error = _validate_generated_size(img_data, size, cfg)
    if size_error:
        return ImageResult(success=False, error=size_error, model=cfg.id)

    try:
        local_path = _save_image(img_data, cfg.id, prompt, prompt)
    except GeneratedImageValidationError as exc:
        return _generated_image_validation_failure(cfg, exc)
    return ImageResult(
        success=True, image_data=img_data, local_path=local_path,
        model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
    )


async def _gen_gemini(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """Google Gemini 原生协议"""
    model_id = kwargs.get("model") or cfg.model

    async with httpx.AsyncClient(
        timeout=120.0,
        proxy=_get_proxy_url(cfg),
        verify=verify_ssl_enabled(),
    ) as client:
        # 处理 base_url：移除末尾的 /v1 或 /v1beta（如果存在）
        base = cfg.base_url.rstrip('/')
        if base.endswith('/v1') or base.endswith('/v1beta'):
            base = base.rsplit('/', 1)[0]
        
        url = f"{base}/v1beta/models/{model_id}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["image", "text"]},
        }

        resp = await _stream_bounded_provider_response(
            client,
            "POST",
            url,
            headers={"x-goog-api-key": cfg.api_key},
            json=payload,
            timeout=120.0,
        )
        resp.raise_for_status()
        data = _parse_provider_json_response(resp)

        candidates = data.get("candidates", [])
        if not candidates:
            return ImageResult(success=False, error=f"[{cfg.name}] 返回无内容", model=cfg.id)

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                inline_data = part["inlineData"]
                try:
                    img_data = _decode_generated_image_base64(inline_data.get("data"))
                    local_path = _save_image(
                        img_data,
                        cfg.id,
                        prompt,
                        prompt,
                        declared_mime=inline_data.get("mimeType"),
                    )
                except GeneratedImageValidationError as exc:
                    return _generated_image_validation_failure(cfg, exc)
                return ImageResult(
                    success=True, image_data=img_data, local_path=local_path,
                    model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
                )

        return ImageResult(success=False, error=f"[{cfg.name}] 未返回图片数据", model=cfg.id)


async def _gen_qwen(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """Qwen2API 协议 (OpenAI 兼容但字段名不同)"""
    size = kwargs.get("size") or cfg.size or "1024*1024"
    model_id = kwargs.get("model") or cfg.model

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "prompt": prompt,
        "size": size,
    }

    resp, client = await _http_post_with_retry(
        f"{_ensure_v1(cfg.base_url)}/images/generations",
        headers=headers, payload=payload,
        proxy=_get_proxy_url(cfg),
        cfg=cfg,
    )
    data = _parse_provider_json_response(resp)

    img_info = data.get("data", [{}])[0]
    b64 = img_info.get("b64_json")
    img_url = img_info.get("url")

    if b64:
        try:
            img_data = _decode_generated_image_base64(b64)
        except GeneratedImageValidationError as exc:
            return _generated_image_validation_failure(cfg, exc)
    elif img_url:
        img_data, download_error = await _download_generated_image(
            client, img_url, max_pixels=GENERATED_IMAGE_MAX_PIXELS
        )
        if download_error:
            return _generated_image_failure(
                cfg,
                "image_result_download_rejected",
                download_error,
                details=_generated_image_download_error_details(download_error),
            )
    else:
        return ImageResult(success=False, error=f"[{cfg.name}] 无图片返回", model=cfg.id)

    try:
        local_path = _save_image(img_data, cfg.id, prompt, prompt)
    except GeneratedImageValidationError as exc:
        return _generated_image_validation_failure(cfg, exc)
    return ImageResult(
        success=True, image_data=img_data, local_path=local_path,
        model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
    )


async def _gen_agnes(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """Agnes AI 协议 (兼容 OpenAI /images/generations 但参数格式特殊)"""
    size = kwargs.get("size") or cfg.size or "1024x1024"
    model_id = kwargs.get("model") or cfg.model

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    # Agnes 特殊格式：基础字段 + extra_body
    payload = {
        "model": model_id,
        "prompt": prompt,
        "size": size,
    }

    # 图生图模式：image 和 response_format 必须在 extra_body 里
    image_data = kwargs.get("image_data")
    if image_data:
        if "," in image_data:
            image_b64 = image_data.split(",")[1]
        else:
            image_b64 = image_data
        # 检测 MIME
        mime = "image/png"
        if image_data.startswith("data:image/jpeg"):
            mime = "image/jpeg"
        elif image_data.startswith("image/webp"):
            mime = "image/webp"
        data_uri = f"data:{mime};base64,{image_b64}"
        payload["extra_body"] = {
            "image": [data_uri],
            "response_format": "b64_json",
        }
    else:
        # 文生图：用 return_base64=true 或 extra_body.response_format
        payload["return_base64"] = True

    resp, client = await _http_post_with_retry(
        f"{_ensure_v1(cfg.base_url)}/images/generations",
        headers=headers, payload=payload,
        proxy=_get_proxy_url(cfg),
        cfg=cfg,
    )
    data = _parse_provider_json_response(resp)

    img_info = data.get("data", [{}])[0]
    b64 = img_info.get("b64_json")
    img_url = img_info.get("url")

    if b64:
        try:
            img_data = _decode_generated_image_base64(b64)
        except GeneratedImageValidationError as exc:
            return _generated_image_validation_failure(cfg, exc)
    elif img_url:
        img_data, download_error = await _download_generated_image(
            client, img_url, max_pixels=GENERATED_IMAGE_MAX_PIXELS
        )
        if download_error:
            return _generated_image_failure(
                cfg,
                "image_result_download_rejected",
                download_error,
                details=_generated_image_download_error_details(download_error),
            )
    else:
        return ImageResult(success=False, error=f"[{cfg.name}] API 返回无图片数据", model=cfg.id)

    size_error = _validate_generated_size(img_data, size, cfg)
    if size_error:
        return ImageResult(success=False, error=size_error, model=cfg.id)

    try:
        local_path = _save_image(img_data, cfg.id, prompt, prompt)
    except GeneratedImageValidationError as exc:
        return _generated_image_validation_failure(cfg, exc)
    return ImageResult(
        success=True, image_data=img_data, local_path=local_path,
        model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
    )


# ──────────────────────────────────────────────────────────────
# 图生图 (I2I) 生成器
# ──────────────────────────────────────────────────────────────
def _decode_inpaint_image_data(value: str, default_mime: str) -> tuple[bytes, str]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("image payload is empty")

    encoded = value.strip()
    mime_type = default_mime
    mime_was_declared = False
    if encoded.startswith("data:"):
        header, separator, encoded = encoded.partition(",")
        if not separator or ";base64" not in header.lower():
            raise ValueError("image payload must be a base64 data URL")
        mime_type = header[5:].split(";", 1)[0].strip().lower()
        mime_was_declared = True

    if mime_type == "image/jpg":
        mime_type = "image/jpeg"
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError(f"unsupported image MIME type: {mime_type or 'unknown'}")

    try:
        decoded = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("image payload is not valid base64") from exc
    if not decoded:
        raise ValueError("image payload decoded to empty bytes")
    try:
        with Image.open(BytesIO(decoded)) as image:
            image.load()
            actual_mime = {
                "PNG": "image/png",
                "JPEG": "image/jpeg",
                "WEBP": "image/webp",
            }.get(str(image.format or "").upper())
    except Exception as exc:
        raise ValueError("image payload is not a readable image") from exc
    if actual_mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("image payload uses an unsupported image format")
    if mime_was_declared and mime_type != actual_mime:
        raise ValueError("image MIME type does not match its image payload")
    return decoded, actual_mime


def _prepare_openai_inpaint_mask(mask_bytes: bytes) -> tuple[bytes, tuple[int, int]]:
    """Convert white=edit/black=preserve into an alpha-based OpenAI mask."""
    try:
        with Image.open(BytesIO(mask_bytes)) as source:
            if source.format != "PNG":
                raise ValueError("mask_data must decode to a PNG image")
            source.load()
            rgba = source.convert("RGBA")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("mask_data is not a readable PNG image") from exc

    opaque_black = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
    edit_map = Image.alpha_composite(opaque_black, rgba).convert("L")
    if edit_map.getbbox() is None:
        raise ValueError("mask_data contains no editable white region")

    provider_mask = Image.new("RGBA", edit_map.size, (0, 0, 0, 255))
    provider_mask.putalpha(edit_map.point(lambda value: 255 - value))
    output = BytesIO()
    provider_mask.save(output, format="PNG")
    return output.getvalue(), edit_map.size


def _image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            return image.size
    except Exception as exc:
        raise ValueError("image_data is not a readable image") from exc


async def _gen_openai_inpaint(
    cfg: ProviderConfig,
    prompt: str,
    image_data: str,
    mask_data: str,
    **kwargs,
) -> ImageResult:
    """Strict OpenAI-compatible mask edit with no protocol or mode fallback."""
    try:
        image_bytes, image_mime = _decode_inpaint_image_data(image_data, "image/png")
        mask_bytes, mask_mime = _decode_inpaint_image_data(mask_data, "image/png")
        if mask_mime != "image/png":
            raise ValueError("mask_data must use image/png")
        image_size = _image_dimensions(image_bytes)
        provider_mask, mask_size = _prepare_openai_inpaint_mask(mask_bytes)
        if image_size != mask_size:
            raise ValueError(
                f"image and mask dimensions must match ({image_size[0]}x{image_size[1]} != "
                f"{mask_size[0]}x{mask_size[1]})"
            )
    except ValueError as exc:
        return _inpaint_failure(cfg, "inpaint_payload_invalid", _provider_exception_text(exc, cfg))

    extension = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }[image_mime]
    files = [
        ("image", (f"image.{extension}", image_bytes, image_mime)),
        ("mask", ("mask.png", provider_mask, "image/png")),
    ]

    model_id = kwargs.get("model") or cfg.model
    size = kwargs.get("size") or cfg.size or "1024x1024"
    quality = kwargs.get("quality") or cfg.quality
    data_dict = {
        "model": model_id,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    if quality and quality != "default":
        data_dict["quality"] = quality

    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    base = _ensure_v1(cfg.base_url)
    url = f"{base}/images/edits"

    async with httpx.AsyncClient(
        timeout=180.0,
        proxy=_get_proxy_url(cfg),
        verify=verify_ssl_enabled(),
    ) as client:
        try:
            resp = await _stream_bounded_provider_response(
                client,
                "POST",
                url,
                headers=headers,
                files=files,
                data=data_dict,
            )
        except ProviderResponseValidationError as exc:
            return _inpaint_failure(
                cfg,
                "inpaint_invalid_response",
                str(exc),
                details={"validation_code": exc.code, **exc.details},
            )
        if resp.status_code >= 400:
            detail = _provider_error_excerpt(getattr(resp, "text", ""), cfg, 200)
            suffix = f": {detail}" if detail else ""
            return _inpaint_failure(
                cfg,
                "inpaint_upstream_error",
                f"HTTP {resp.status_code}{suffix}",
            )

        try:
            result = _parse_provider_json_response(resp)
        except ProviderResponseValidationError as exc:
            return _inpaint_failure(
                cfg,
                "inpaint_invalid_response",
                str(exc),
                details={"validation_code": exc.code, **exc.details},
            )

        if not isinstance(result, dict):
            return _inpaint_failure(
                cfg,
                "inpaint_invalid_response",
                "upstream response must be a JSON object",
            )
        result_data = result.get("data")
        if not isinstance(result_data, list) or not result_data or not isinstance(result_data[0], dict):
            return _inpaint_failure(
                cfg,
                "inpaint_invalid_response",
                "upstream response data must contain an image object",
            )
        img_info = result_data[0]
        image_b64 = img_info.get("b64_json")
        image_url = img_info.get("url")
        if image_b64:
            try:
                output_data = _decode_generated_image_base64(image_b64)
            except GeneratedImageValidationError as exc:
                return _inpaint_failure(
                    cfg,
                    "inpaint_invalid_response",
                    str(exc),
                    details={"validation_code": exc.code, **exc.details},
                )
        elif image_url:
            output_data, download_error = await _download_generated_image(
                client,
                image_url,
                max_pixels=GENERATED_IMAGE_MAX_PIXELS,
            )
            if download_error:
                return _inpaint_failure(
                    cfg,
                    "inpaint_result_download_rejected",
                    download_error,
                    details=_generated_image_download_error_details(download_error),
                )
        else:
            return _inpaint_failure(
                cfg,
                "inpaint_no_image_data",
                "upstream response contained no image",
            )

    try:
        local_path = _save_image(output_data, cfg.id, f"inpaint_{prompt[:30]}", prompt)
    except GeneratedImageValidationError as exc:
        return _inpaint_failure(
            cfg,
            "inpaint_invalid_response",
            str(exc),
            details={"validation_code": exc.code, **exc.details},
        )
    return ImageResult(
        success=True,
        image_data=output_data,
        local_path=local_path,
        model=cfg.id,
        generation_id=f"{cfg.id}_inpaint_{uuid.uuid4().hex[:8]}",
    )


def _precision_v2_provider_prompt(prompt: str, annotations: list[dict]) -> str:
    item_lines = []
    geometry = []
    for annotation in sorted(annotations, key=lambda item: item["label"]):
        annotation_type = annotation["type"]
        label = annotation["label"]
        if annotation_type == "text":
            item_detail = f'output text={json.dumps(annotation["text"], ensure_ascii=False)}'
            if annotation.get("instruction"):
                item_detail += (
                    "; additional edit instruction="
                    + json.dumps(annotation["instruction"], ensure_ascii=False)
                )
        else:
            item_detail = "edit instruction=" + json.dumps(
                annotation["instruction"],
                ensure_ascii=False,
            )
        item_lines.append(f"- Label {label} ({annotation_type}): {item_detail}")
        geometry.append({
            key: value
            for key, value in annotation.items()
            if key not in {"instruction", "text"}
        })

    sections = ["Precision image edit using the numbered annotation overlay."]
    if prompt:
        sections.append("Overall requirements:\n" + prompt)
    sections.append("Item instructions:\n" + "\n".join(item_lines))
    sections.append(
        "Normalized geometry JSON:\n"
        + json.dumps(geometry, ensure_ascii=False, separators=(",", ":"))
    )
    sections.append(
        "Preserve every unmarked area. Remove all annotation arrows, rectangles, ellipses, "
        "freehand strokes, labels, and overlay text from the final image. Text listed as output text is "
        "requested image content, not an edit instruction."
    )
    return "\n\n".join(sections)


async def _gen_openai_precision_edit(
    cfg: ProviderConfig,
    prompt: str,
    image_data: str,
    annotation_image_data: str | None,
    annotations: list[dict] | None,
    annotation_contract: str = "",
    precision_canvas_only: bool = False,
    transport_profile: PrecisionEditTransportProfile | None = None,
    _precision_post_budget: PrecisionEditPostBudget | None = None,
    **kwargs,
) -> ImageResult:
    """Strict annotated or source-only resize transport with no T2I fallback."""
    try:
        image_bytes, image_mime = _decode_inpaint_image_data(image_data, "image/png")
        image_size = _image_dimensions(image_bytes)
        annotation_bytes = b""
        safe_annotations: list[dict] = []
        if precision_canvas_only:
            if annotation_image_data is not None or annotations is not None or annotation_contract:
                raise ValueError("source-only precision resize does not accept annotation fields")
        else:
            annotation_bytes, annotation_mime = _decode_inpaint_image_data(
                annotation_image_data,
                "image/png",
            )
            if annotation_mime != "image/png":
                raise ValueError("annotation_image_data must use image/png")
            annotation_size = _image_dimensions(annotation_bytes)
            if image_size != annotation_size:
                raise ValueError(
                    f"source and annotation dimensions must match ({image_size[0]}x{image_size[1]} != "
                    f"{annotation_size[0]}x{annotation_size[1]})"
                )
            safe_annotations = _normalized_precision_annotations(
                annotations,
                annotation_contract,
            )
    except ValueError as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_payload_invalid",
            _provider_exception_text(exc, cfg),
        )

    extension = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }[image_mime]
    if transport_profile is None:
        transport_profile = _precision_edit_transport_profile(cfg)
    if transport_profile is None:
        return _precision_edit_failure(
            cfg,
            "precision_edit_profile_unsupported",
            "precision_edit requires an allowlisted transport profile",
        )
    size_mode = str(kwargs.get("precision_size_mode") or "preserve").strip().lower()
    resize_prompt = str(kwargs.get("precision_resize_prompt") or "").strip()
    model_id = str(kwargs.get("model") or cfg.model or "").strip()
    target_size = str(kwargs.get("precision_target_size") or "")
    generic_size = str(kwargs.get("size") or "").strip().lower()
    output_size_policy = str(kwargs.get("precision_output_size_policy") or "strict")
    if output_size_policy not in PRECISION_OUTPUT_SIZE_POLICIES:
        return _precision_edit_failure(
            cfg,
            "precision_output_size_policy_invalid",
            "precision_output_size_policy must be strict or fit_crop",
            details={"allowed_policies": list(PRECISION_OUTPUT_SIZE_POLICIES)},
        )
    if size_mode != "resize" and "precision_output_size_policy" in kwargs:
        return _precision_edit_failure(
            cfg,
            "precision_output_size_policy_not_allowed",
            "precision_output_size_policy is accepted only for precision_edit resize",
        )
    if transport_profile.image_payload == "source_only" and not precision_canvas_only:
        if size_mode == "preserve":
            source_size_error = _precision_preserve_source_size_error(cfg, model_id, image_size)
            if source_size_error:
                return _precision_edit_failure(cfg, source_size_error[0], source_size_error[1])
    if precision_canvas_only or transport_profile.image_payload == "source_only":
        files = [
            (transport_profile.image_field, (f"source.{extension}", image_bytes, image_mime)),
        ]
    else:
        files = [
            (transport_profile.image_field, (f"source.{extension}", image_bytes, image_mime)),
            (transport_profile.image_field, ("annotations.png", annotation_bytes, "image/png")),
        ]
    if precision_canvas_only:
        edit_prompt = (
            "Source-only canvas expansion. Preserve the existing subject, foreground content, "
            "visual identity, and style."
        )
        if prompt:
            edit_prompt += f"\n\nOverall requirements:\n{prompt}"
    elif annotation_contract in {PRECISION_ANNOTATION_CONTRACT_V2, PRECISION_ANNOTATION_CONTRACT_V3}:
        edit_prompt = _precision_v2_provider_prompt(prompt, safe_annotations)
    else:
        structured_annotations = json.dumps(
            safe_annotations,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        edit_prompt = (
            "Precision image edit. The first image is the source. The second image is an annotation "
            "overlay. Apply requested changes only at annotated positions. Remove all arrows, "
            "rectangles, and annotation text from the result. Preserve unmarked areas. "
            f"User instruction: {prompt}\n"
            f"Normalized annotations: {structured_annotations}"
        )
    size_error = _precision_size_error(cfg, model_id, size_mode, target_size, generic_size)
    if size_error:
        return _precision_edit_failure(cfg, size_error[0], size_error[1])
    if size_mode == "preserve":
        edit_prompt += (
            f"\n\nCanvas policy: preserve the source canvas ({image_size[0]}x{image_size[1]}) and its aspect ratio. "
            "Do not crop, stretch, or reframe the image."
        )
        request_size = (
            f"{image_size[0]}x{image_size[1]}"
            if transport_profile.preserve_size == "source_dimensions"
            else "auto"
        )
    elif size_mode == "resize":
        request_size = target_size
        if not resize_prompt:
            return _precision_edit_failure(cfg, "precision_resize_prompt_required", "resize mode requires composition guidance")
        ratio_label = _precision_ratio_label(request_size)
        edit_prompt += (
            f"\n\nTarget canvas constraint: output exactly {request_size} ({ratio_label}). "
            "Expand/outpaint the canvas and reframe only as needed; preserve the existing subject, "
            "visual identity, and style. Do not crop or stretch the source merely to fill the target."
        )
        edit_prompt += f"\nUser resize guidance: {resize_prompt}"
    else:
        return _precision_edit_failure(cfg, "precision_size_mode_invalid", "unsupported precision size mode")
    quality = kwargs.get("quality") or cfg.quality
    data_dict = {"model": model_id, "prompt": edit_prompt, "n": 1, "size": request_size}
    if quality and quality != "default":
        data_dict["quality"] = quality

    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    url = f"{_ensure_v1(cfg.base_url)}{transport_profile.path}"
    client = None
    try:
        resp, client = await _http_post_with_retry(
            url,
            headers,
            files=files,
            data=data_dict,
            timeout=180.0,
            max_retries=3,
            retry_delay=0.25,
            retry_transport_errors=False,
            post_budget=_precision_post_budget or PrecisionEditPostBudget(),
            proxy=_get_proxy_url(cfg),
            cfg=cfg,
        )
    except httpx.TimeoutException as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_timeout",
            f"图片编辑端点响应超时（{_provider_exception_text(exc, cfg)}）。请稍后重试或切换端点",
        )
    except httpx.HTTPStatusError as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_upstream_error",
            _friendly_generation_error(_provider_exception_text(exc, cfg)),
        )
    except httpx.HTTPError as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_connection_error",
            f"无法完成图片编辑请求（{_provider_exception_text(exc, cfg)}）。请检查端点连通性后重试",
        )
    except ProviderResponseValidationError as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_invalid_response",
            str(exc),
            details={"validation_code": exc.code, **exc.details},
        )
    try:
        try:
            result = _parse_provider_json_response(resp)
        except ProviderResponseValidationError as exc:
            return _precision_edit_failure(
                cfg,
                "precision_edit_invalid_response",
                str(exc),
                details={"validation_code": exc.code, **exc.details},
            )

        if not isinstance(result, dict):
            return _precision_edit_failure(
                cfg,
                "precision_edit_invalid_response",
                "upstream response must be a JSON object",
            )
        result_data = result.get("data")
        if not isinstance(result_data, list) or not result_data or not isinstance(result_data[0], dict):
            return _precision_edit_failure(
                cfg,
                "precision_edit_invalid_response",
                "upstream response data must contain an image object",
            )
        image_info = result_data[0]
        image_b64 = image_info.get("b64_json")
        image_url = image_info.get("url")
        if image_b64:
            try:
                output_data = _decode_generated_image_base64(image_b64)
            except GeneratedImageValidationError as exc:
                return _precision_edit_failure(
                    cfg,
                    "precision_edit_invalid_response",
                    str(exc),
                    details={"validation_code": exc.code, **exc.details},
                )
        elif image_url:
            output_data, download_error = await _download_generated_image(
                client,
                image_url,
                max_pixels=PRECISION_MAX_OUTPUT_PIXELS,
            )
            if download_error:
                return _precision_edit_failure(
                    cfg,
                    "precision_edit_result_download_rejected",
                    download_error,
                    details=_generated_image_download_error_details(download_error),
                )
        else:
            return _precision_edit_failure(
                cfg,
                "precision_edit_no_image_data",
                "upstream response contained no image",
            )
    finally:
        if client is not None:
            close = getattr(client, "aclose", None)
            if close is not None:
                await close()

    try:
        output_size, output_format, output_has_alpha = _inspect_precision_output(output_data)
    except GeneratedImageValidationError as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_invalid_response",
            str(exc),
            details={"validation_code": exc.code, **exc.details},
        )
    except ValueError as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_invalid_response",
            _provider_exception_text(exc, cfg),
        )
    expected_size = image_size if size_mode == "preserve" else _precision_size_tuple(request_size)
    aspect_ratio_delta = _precision_aspect_ratio_delta(expected_size, output_size)
    generation_metadata = None
    warnings = None
    if output_size != expected_size:
        mismatch_details = {
            "requested_size": f"{expected_size[0]}x{expected_size[1]}",
            "actual_size": f"{output_size[0]}x{output_size[1]}",
            "aspect_ratio_delta": round(aspect_ratio_delta, 8),
            "allowed_policies": (
                list(PRECISION_OUTPUT_SIZE_POLICIES)
                if size_mode == "resize"
                else ["strict"]
            ),
        }
        fitted = None
        if size_mode == "resize" and output_size_policy == "fit_crop":
            fitted = _fit_crop_precision_output(output_data, expected_size)
        if fitted is None:
            return _precision_edit_failure(
                cfg,
                "precision_edit_output_size_mismatch",
                (
                    f"图片编辑模型返回了 {output_size[0]}x{output_size[1]}，"
                    f"但当前尺寸策略要求 {expected_size[0]}x{expected_size[1]}。"
                    "结果未接管主画布；请切换支持该尺寸的模型，或主动使用改变尺寸。"
                ),
                details=mismatch_details,
            )
        output_data, transform = fitted
        final_size = _image_dimensions(output_data)
        generation_metadata = {
            "requested_size": mismatch_details["requested_size"],
            "provider_actual_size": mismatch_details["actual_size"],
            "final_size": f"{final_size[0]}x{final_size[1]}",
            "policy": "fit_crop",
            "aspect_ratio_delta": mismatch_details["aspect_ratio_delta"],
            "transform": transform,
        }
        warnings = [{
            "code": "precision_edit_output_fit_crop_applied",
            "message": (
                f"Provider output {output_size[0]}x{output_size[1]} was locally fit-cropped "
                f"to requested size {expected_size[0]}x{expected_size[1]}."
            ),
        }]
    elif size_mode == "resize" and output_size_policy == "fit_crop":
        requested_size = f"{expected_size[0]}x{expected_size[1]}"
        generation_metadata = {
            "requested_size": requested_size,
            "provider_actual_size": requested_size,
            "final_size": requested_size,
            "policy": "fit_crop",
            "aspect_ratio_delta": 0.0,
            "transform": {
                "operation": "none",
                "scale_factor": 1.0,
                "scaled_size": requested_size,
                "crop_box": [0, 0, expected_size[0], expected_size[1]],
                "resample": None,
                "source_format": output_format,
                "output_format": output_format,
                "alpha_preserved": output_has_alpha,
            },
        }

    try:
        local_path = _save_image(
            output_data,
            cfg.id,
            f"precision_{prompt[:30]}",
            prompt,
            generation_metadata=generation_metadata,
            max_pixels=PRECISION_MAX_OUTPUT_PIXELS,
        )
    except GeneratedImageValidationError as exc:
        return _precision_edit_failure(
            cfg,
            "precision_edit_invalid_response",
            str(exc),
            details={"validation_code": exc.code, **exc.details},
        )
    return ImageResult(
        success=True,
        image_data=output_data,
        local_path=local_path,
        model=cfg.id,
        generation_id=f"{cfg.id}_precision_{uuid.uuid4().hex[:8]}",
        metadata=generation_metadata,
        warnings=warnings,
    )


async def _gen_openai_edit(cfg: ProviderConfig, prompt: str, image_data: str, strength: float, image_data_list=None, **kwargs) -> ImageResult:
    """OpenAI 兼容协议图生图: POST /images/edits"""
    # 从 base64 data URL 提取纯 base64 数据
    if "," in image_data:
        image_b64 = image_data.split(",")[1]
    else:
        image_b64 = image_data

    images = image_data_list or [image_data]
    image_bytes_list = []
    for item in images:
        raw = item.split(",", 1)[1] if "," in item else item
        image_bytes_list.append(base64.b64decode(raw))
    model_id = kwargs.get("model") or cfg.model
    size = kwargs.get("size") or cfg.size or "1024x1024"
    n_val = int(round((1 - strength) * 10))  # strength 转为 n 参数近似

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
    }

    # 使用 multipart/form-data
    files = [("image", (f"image-{idx}.png", data, "image/png")) for idx, data in enumerate(image_bytes_list)]
    files.append(("prompt", (None, prompt)))
    data_dict = {
        "model": model_id,
        "n": 1,
        "size": size,
    }

    async with httpx.AsyncClient(
        timeout=180.0,
        proxy=_get_proxy_url(cfg),
        verify=verify_ssl_enabled(),
    ) as client:
        # 尝试标准 /images/edits 端点
        base = _ensure_v1(cfg.base_url)
        url = f"{base}/images/edits"
        resp = await _stream_bounded_provider_response(
            client,
            "POST",
            url,
            headers=headers,
            files=files,
            data=data_dict,
        )
        
        if resp.status_code == 404:
            # edits 端点不存在，尝试 /images/edit（无 s）
            url_alt = f"{base}/images/edit"
            resp = await _stream_bounded_provider_response(
                client,
                "POST",
                url_alt,
                headers=headers,
                files=files,
                data=data_dict,
            )
            if resp.status_code == 404:
                # 两个端点都不支持，fallback 到文生图
                return await _gen_openai_i2i_fallback(cfg, prompt, image_bytes_list[0], **kwargs)
        
        if resp.status_code >= 400:
            # 400/422 等错误，尝试移除不支持的参数后重试
            data_dict_clean = {"model": model_id, "prompt": prompt}
            resp_retry = await _stream_bounded_provider_response(
                client,
                "POST",
                url,
                headers=headers,
                files=files,
                data=data_dict_clean,
            )
            if resp_retry.status_code >= 400:
                # 仍然失败，记录详细错误并 fallback
                err_detail = _provider_error_excerpt(resp_retry.text, cfg, 200)
                fallback_result = await _gen_openai_i2i_fallback(cfg, prompt, image_bytes_list[0], **kwargs)
                fallback_result.error = f"[I2I {resp_retry.status_code}] {err_detail} | 已降级为参考生图"
                return fallback_result
            resp = resp_retry
        
        result = _parse_provider_json_response(resp)

        img_info = result.get("data", [{}])[0]
        b64 = img_info.get("b64_json")
        img_url = img_info.get("url")

        if b64:
            try:
                out_data = _decode_generated_image_base64(b64)
            except GeneratedImageValidationError as exc:
                return _generated_image_validation_failure(cfg, exc)
        elif img_url:
            out_data, download_error = await _download_generated_image(
                client,
                img_url,
                max_pixels=GENERATED_IMAGE_MAX_PIXELS,
            )
            if download_error:
                return _generated_image_failure(
                    cfg,
                    "image_result_download_rejected",
                    download_error,
                    details=_generated_image_download_error_details(download_error),
                )
        else:
            return ImageResult(success=False, error=f"[{cfg.name}] I2I API 返回无图片数据", model=cfg.id)

        try:
            local_path = _save_image(out_data, cfg.id, f"i2i_{prompt[:30]}", prompt)
        except GeneratedImageValidationError as exc:
            return _generated_image_validation_failure(cfg, exc)
        return ImageResult(
            success=True, image_data=out_data, local_path=local_path,
            model=cfg.id, generation_id=f"{cfg.id}_i2i_{uuid.uuid4().hex[:8]}",
        )


async def _gen_openai_i2i_fallback(cfg: ProviderConfig, prompt: str, image_bytes: bytes, **kwargs) -> ImageResult:
    """
    Fallback: 当 /images/edits 不支持时，将图片信息编码到 prompt 中
    部分模型（如 GPT-Image）支持在 prompt 中引用图片描述
    """
    # 尝试将图片作为 base64 内嵌到请求中（部分 API 支持）
    import io
    from PIL import Image as PILImage

    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        w, h = img.size
        enhanced_prompt = f"[INPUT IMAGE: {w}x{h} pixels] Transform this image according to: {prompt}"
    except Exception:
        enhanced_prompt = f"Transform the input image: {prompt}"

    # 回退到普通文生图，但使用增强的 prompt
    return await _gen_openai(cfg, enhanced_prompt, **kwargs)


async def _gen_gemini_edit(cfg: ProviderConfig, prompt: str, image_data: str, strength: float, image_data_list=None, **kwargs) -> ImageResult:
    """Gemini 原生协议图生图: 在 generateContent 中内联图片"""
    images = image_data_list or [image_data]

    # 检测 MIME 类型
    mime_type = "image/png"
    parts = [{"text": prompt}]
    for item in images:
        item_b64 = item.split(",", 1)[1] if "," in item else item
        item_mime = "image/jpeg" if item.startswith("data:image/jpeg") else "image/webp" if item.startswith("data:image/webp") else mime_type
        parts.append({"inlineData": {"mimeType": item_mime, "data": item_b64}})

    model_id = kwargs.get("model") or cfg.model

    async with httpx.AsyncClient(
        timeout=180.0,
        proxy=_get_proxy_url(cfg),
        verify=verify_ssl_enabled(),
    ) as client:
        # 处理 base_url：移除末尾的 /v1 或 /v1beta
        base = cfg.base_url.rstrip('/')
        if base.endswith('/v1') or base.endswith('/v1beta'):
            base = base.rsplit('/', 1)[0]
        
        url = f"{base}/v1beta/models/{model_id}:generateContent"
        payload = {
            "contents": [{
                "parts": parts
            }],
            "generationConfig": {
                "responseModalities": ["image", "text"],
            },
        }

        resp = await _stream_bounded_provider_response(
            client,
            "POST",
            url,
            headers={"x-goog-api-key": cfg.api_key},
            json=payload,
            timeout=180.0,
        )
        resp.raise_for_status()
        data = _parse_provider_json_response(resp)

        candidates = data.get("candidates", [])
        if not candidates:
            return ImageResult(success=False, error=f"[{cfg.name}] 返回无内容", model=cfg.id)

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                inline_data = part["inlineData"]
                try:
                    out_data = _decode_generated_image_base64(inline_data.get("data"))
                    local_path = _save_image(
                        out_data,
                        cfg.id,
                        f"i2i_{prompt[:30]}",
                        prompt,
                        declared_mime=inline_data.get("mimeType"),
                    )
                except GeneratedImageValidationError as exc:
                    return _generated_image_validation_failure(cfg, exc)
                return ImageResult(
                    success=True, image_data=out_data, local_path=local_path,
                    model=cfg.id, generation_id=f"{cfg.id}_i2i_{uuid.uuid4().hex[:8]}",
                )

        return ImageResult(success=False, error=f"[{cfg.name}] 未返回图片数据", model=cfg.id)


# ──────────────────────────────────────────────────────────────
# 并发生图入口
# ──────────────────────────────────────────────────────────────
async def generate_multi(
    prompts: List[str],
    provider_ids: List[str],
    **kwargs
) -> dict:
    """
    并发生图：同 prompt + 多 Provider 同时生成
    返回 {provider_id: ImageResult}
    """
    results = {}
    tasks = []
    pid_list = []

    # 构建查找表
    all_providers = {p.id: p for p in cfg_mgr.config.providers}

    for pid in provider_ids:
        if pid in all_providers:
            p_cfg = all_providers[pid]
            for prompt in prompts:
                tasks.append(generate_for_provider(p_cfg, prompt, **kwargs))
                pid_list.append(pid)

    if not tasks:
        return {}

    import asyncio
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    for pid, outcome in zip(pid_list, outcomes):
        cfg = all_providers.get(pid)
        if isinstance(outcome, Exception):
            results[pid] = ImageResult(
                success=False,
                error=_provider_exception_text(outcome, cfg) if cfg else _exception_text(outcome),
                model=pid,
            )
        else:
            results[pid] = _sanitize_failed_image_result(outcome, cfg) if cfg else outcome

    return results


# ──────────────────────────────────────────────────────────────
# LLM 提示词优化
# ──────────────────────────────────────────────────────────────
async def enhance_prompt_with_llm(prompt: str, llm_provider_id: str = None) -> str:
    """使用配置的 LLM Provider 优化提示词"""
    # 如果指定了特定 LLM Provider，使用它
    if llm_provider_id:
        all_providers = {p.id: p for p in cfg_mgr.config.providers}
        llm_cfg = all_providers.get(llm_provider_id)
    else:
        # 否则使用第一个启用的 LLM Provider
        llm_cfg = cfg_mgr.get_llm_provider()
    
    if not llm_cfg:
        return prompt

    headers = {
        "Authorization": f"Bearer {llm_cfg.api_key}",
        "Content-Type": "application/json",
    }

    sys_prompt = (
        "你是一个专业的AI图像生成提示词优化助手。"
        "将用户的简短描述扩展为详细、专业的生图提示词，"
        "包含艺术风格、光照、构图、相机参数等细节。"
        "直接返回优化后的提示词，不要解释。"
    )

    payload = {
        "model": llm_cfg.model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(
            timeout=60.0,
            proxy=_get_proxy_url(llm_cfg),
            verify=verify_ssl_enabled(),
        ) as client:
            resp = await _stream_bounded_provider_response(
                client,
                "POST",
                f"{_ensure_v1(llm_cfg.base_url)}/chat/completions",
                success_max_bytes=PROVIDER_LLM_RESPONSE_MAX_BYTES,
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = _parse_provider_json_response(resp)
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        error_text = _provider_exception_text(e, llm_cfg)[:PROVIDER_ERROR_MAX_LENGTH]
        print(f"[LLM] 优化失败: {error_text}")
        return prompt


async def enhance_prompt_with_llm_detailed(prompt: str, llm_provider_id: str = None) -> dict:
    """LLM 提示词优化（返回详细结果，含错误信息）"""
    if llm_provider_id:
        all_providers = {p.id: p for p in cfg_mgr.config.providers}
        llm_cfg = all_providers.get(llm_provider_id)
    else:
        llm_cfg = cfg_mgr.get_llm_provider()

    if not llm_cfg:
        return {"text": prompt, "optimized": False, "error": "未配置 LLM Provider", "provider": None}

    headers = {
        "Authorization": f"Bearer {llm_cfg.api_key}",
        "Content-Type": "application/json",
    }

    sys_prompt = (
        "你是一个专业的AI图像生成提示词优化助手。"
        "将用户的简短描述扩展为详细、专业的生图提示词，"
        "包含艺术风格、光照、构图、相机参数等细节。"
        "直接返回优化后的提示词，不要解释。"
    )

    payload = {
        "model": llm_cfg.model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(
            timeout=60.0,
            proxy=_get_proxy_url(llm_cfg),
            verify=verify_ssl_enabled(),
        ) as client:
            resp = await _stream_bounded_provider_response(
                client,
                "POST",
                f"{_ensure_v1(llm_cfg.base_url)}/chat/completions",
                success_max_bytes=PROVIDER_LLM_RESPONSE_MAX_BYTES,
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = _parse_provider_json_response(resp)
            result_text = data["choices"][0]["message"]["content"].strip()
            return {"text": result_text, "optimized": True, "error": None, "provider": llm_cfg.id}
    except Exception as e:
        error_text = _provider_exception_text(e, llm_cfg)[:PROVIDER_ERROR_MAX_LENGTH]
        print(f"[LLM] 优化失败: {error_text}")
        return {
            "text": prompt,
            "optimized": False,
            "error": error_text,
            "provider": llm_cfg.id,
        }


# ──────────────────────────────────────────────────────────────
# 从上游 API 拉取可用模型列表
# ──────────────────────────────────────────────────────────────
async def fetch_models_from_upstream(cfg: ProviderConfig) -> List[str]:
    """
    根据 Provider 配置从上游获取可用模型列表。

    优先使用用户显式设置的 endpoint_type；为 auto 时按 URL 自动识别。
    任何网络/协议失败都会如实抛出错误，**绝不返回伪造的模型列表**。
    （火山方舟 Agent Plan 没有公开的模型列表 API，返回官方文档候选名，
     这些候选名仅表示「可能可用」，真实可用性需在生成时验证。）
    """
    if not cfg.get_effective_keys() and not cfg.get_active_endpoints():
        raise ValueError("API Key 未配置")
    if not cfg.base_url and not cfg.get_active_endpoints():
        raise ValueError("Base URL 未配置")

    # 1) 确定端点类型（显式优先）
    et = (cfg.endpoint_type or "auto").strip().lower()
    if et in ("auto", ""):
        et = _detect_protocol(cfg)

    # 2) 火山方舟 Agent Plan：无模型列表 API，返回官方候选名
    if et == "volc_ark_plan":
        return _volcengine_plan_candidate_models(cfg)

    # 3) 标准 Ark / OpenAI 兼容 / Gemini / Qwen / Agnes：真实拉取，失败即报错
    if et == "gemini":
        return await _fetch_gemini_models(cfg)
    if et == "qwen":
        return await _fetch_qwen_models(cfg)
    # volc_ark / openai / agnes 统一走 OpenAI 兼容 GET /v1/models
    return await _fetch_openai_models(cfg)


def _volcengine_plan_candidate_models(cfg: ProviderConfig) -> List[str]:
    """火山方舟 Agent Plan 无模型列表 API，返回官方文档中的候选模型名。

    仅为「可能可用」的候选，真实可用性需在生成时验证
    （Small 套餐不支持视频生成，需 Medium 及以上套餐）。
    """
    if cfg.type == "video":
        return [
            "doubao-seedance-2.0",
            "doubao-seedance-2.0-fast",
            "doubao-seedance-2.0-mini",
            "doubao-seedance-1.5-pro",
        ]
    if cfg.type == "image":
        return ["doubao-seedream-5.0-lite"]
    return []


async def _fetch_openai_models(cfg: ProviderConfig) -> List[str]:
    """OpenAI 兼容: GET /v1/models，根据 provider 类型推荐合适模型"""
    explicit_endpoints = [endpoint for endpoint in (cfg.endpoints or []) if endpoint.enabled and endpoint.url and endpoint.key]
    candidates = [(endpoint.url, endpoint.key) for endpoint in explicit_endpoints]
    if not explicit_endpoints:
        candidates = [(cfg.base_url, key) for key in cfg.get_effective_keys()]
    last_response = None

    async with httpx.AsyncClient(
        timeout=30.0,
        proxy=_get_proxy_url(cfg),
        verify=verify_ssl_enabled(),
    ) as client:
        for base_url, api_key in candidates:
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = await _stream_bounded_provider_response(
                client,
                "GET",
                f"{base_url.rstrip('/')}/models",
                success_max_bytes=PROVIDER_MODEL_LIST_RESPONSE_MAX_BYTES,
                headers=headers,
            )
            if resp.status_code == 200:
                last_response = resp
                break
            last_response = resp
        if last_response is None:
            raise ValueError("API Key 未配置")
        last_response.raise_for_status()
        data = _parse_provider_json_response(last_response)

    raw_models = data.get("data", [])
    model_ids = [m.get("id", "") for m in raw_models if m.get("id")]

    if cfg.type == "llm":
        # LLM 类型：优先推荐对话/语言模型，排除图像生成模型
        image_keywords = ["image", "dall", "gpt-image", "flux", "sd", "stable", "midjourney", "wanx", "paint", "imagen"]
        llm_models = [m for m in model_ids if not any(k in m.lower() for k in image_keywords)]
        image_models = [m for m in model_ids if any(k in m.lower() for k in image_keywords)]
        return llm_models + image_models
    else:
        # 图像/视频类型：优先推荐图像生成相关模型
        image_keywords = ["image", "dall", "gpt-image", "flux", "sd", "stable", "midjourney", "wanx", "paint"]
        recommended = [m for m in model_ids if any(k in m.lower() for k in image_keywords)]
        others = [m for m in model_ids if m not in recommended]
        return recommended + others


async def _fetch_gemini_models(cfg: ProviderConfig) -> List[str]:
    """
    Gemini: 尝试原生 API，失败则 fallback 到 OpenAI 兼容格式
    支持两种部署方式：
    1. Google 官方 API: /v1beta/models，使用 x-goog-api-key 请求头
    2. OpenAI 兼容代理: /v1/models
    """
    # 处理 base_url：移除末尾的 /v1 或 /v1beta
    base = cfg.base_url.rstrip('/')
    if base.endswith('/v1') or base.endswith('/v1beta'):
        base = base.rsplit('/', 1)[0]
    
    # 先尝试原生 Gemini API
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            proxy=_get_proxy_url(cfg),
            verify=verify_ssl_enabled(),
        ) as client:
            url = f"{base}/v1beta/models"
            resp = await _stream_bounded_provider_response(
                client,
                "GET",
                url,
                success_max_bytes=PROVIDER_MODEL_LIST_RESPONSE_MAX_BYTES,
                headers={"x-goog-api-key": cfg.api_key},
            )
            if resp.status_code == 200:
                data = _parse_provider_json_response(resp)
                models = data.get("models", [])
                image_models = []
                other_models = []
                for m in models:
                    mid = m.get("name", "").replace("models/", "")
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods or "imageGeneration" in methods:
                        image_models.append(mid)
                    else:
                        other_models.append(mid)
                return image_models + other_models
    except Exception:
        pass  # fallback 到 OpenAI 兼容格式

    # Fallback: 尝试 OpenAI 兼容格式
    return await _fetch_openai_models(cfg)


async def _fetch_qwen_models(cfg: ProviderConfig) -> List[str]:
    """Qwen2API: 尝试多种路径拉取模型列表"""
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    base = cfg.base_url.rstrip('/')

    async with httpx.AsyncClient(
        timeout=30.0,
        proxy=_get_proxy_url(cfg),
        verify=verify_ssl_enabled(),
    ) as client:
        # 尝试多种可能的端点
        endpoints_to_try = [
            f"{base}/v1/models",
            f"{base}/models",
            f"{base}/v1/image/models",
        ]

        for endpoint in endpoints_to_try:
            try:
                resp = await _stream_bounded_provider_response(
                    client,
                    "GET",
                    endpoint,
                    success_max_bytes=PROVIDER_MODEL_LIST_RESPONSE_MAX_BYTES,
                    headers=headers,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = _parse_provider_json_response(resp)
                    raw = data.get("data", [])
                    if raw:
                        model_ids = [m.get("id", "") for m in raw if m.get("id")]
                        if model_ids:
                            print(f"[fetch-qwen] 从 {endpoint} 获取到 {len(model_ids)} 个模型")
                            return model_ids
            except Exception as e:
                print(f"[fetch-qwen] {endpoint} 失败: {_provider_exception_text(e, cfg)}")
                continue

        # 所有端点都失败，返回完整的已知 qwen 图像模型列表（基于截图中的实际模型）
        print(f"[fetch-qwen] 所有端点失败，使用完整 fallback 列表")
        return [
            # Qwen3 系列
            "qwen3-235B-A22B",
            "qwen3-Coder",
            "qwen3-Max",
            "qwen3-Omni-Flash",
            "qwen3-VL-235B-A22B",
            # Qwen3.5 系列
            "qwen3.5-122B-A10B",
            "qwen3.5-27B",
            "qwen3.5-35B-A3B",
            "qwen3.5-397B-A17B",
            "qwen3.5-Flash",
            "qwen3.5-Omni-Flash",
            "qwen3.5-Omni-Plus",
            "qwen3.5-Plus",
            # Qwen3.6 系列
            "qwen3.6-27B",
            "qwen3.6-35B-A3B",
            "qwen3.6-Plus",
            # Wanx 图像系列
            "qwen3-235B-A22B (qwen-plus-2025-07-28-image)",
            "qwen3-Coder (qwen3-coder-plus-image)",
            "qwen3-Max (qwen3-max-2026-01-23-image)",
            "qwen3-Omni-Flash (qwen3-omni-flash-2025-12-01-image)",
            "qwen3-VL-235B-A22B (qwen3-vl-plus-a10b-image)",
            "qwen3.5-122B-A10B (qwen3.5-122b-a10b-image)",
            "qwen3.5-27B (qwen3.5-27b-image)",
            "qwen3.5-35B-A3B (qwen3.5-35b-a3b-image)",
            "qwen3.5-397B-A17B (qwen3.5-397b-a17b-image)",
            "qwen3.5-Flash (qwen3.5-flash-image)",
            "qwen3.5-Omni-Flash (qwen3.5-omni-flash-image)",
            "qwen3.5-Omni-Plus (qwen3.5-omni-plus-image)",
            "qwen3.5-Plus (qwen3.5-plus-image)",
            "qwen3.6-27B (qwen3.6-27b-image)",
            "qwen3.6-35B-A3B (qwen3.6-35b-a3b-image)",
            "qwen3.6-Plus (qwen3.6-plus-image)",
        ]


def translate_upstream_error(raw: str) -> str:
    """将上游模型 API 常见的英文错误翻译成易懂的中文提示。

    无法识别时原样返回，绝不吞掉原始信息（符合「错误要诚实、可懂」原则）。
    """
    if not raw:
        return raw
    s = raw.strip()
    low = s.lower()

    rules = [
        ("does not support image input",
         "当前模型不支持图片输入。请改用支持图生视频(I2V)/图生图的模型，或去掉图片只用文字生成。"),
        ("image input",
         "当前模型不支持图片输入。请改用支持图片的模型，或去掉参考图。"),
        ("modelnotopen",
         "该模型尚未在火山方舟控制台开通。请到方舟控制台「模型管理」中开通该模型服务后再试。"),
        ("unsupportedmodel",
         "该模型不被当前套餐/端点支持。请确认模型名称正确，且已在对应套餐或控制台开通。"),
        ("invalidendpointormodel",
         "模型或端点不存在/无访问权限。请确认模型名称正确，且账户已开通该模型。"),
        ("authenticationerror",
         "API Key 无效或无权限。请检查 Key 是否正确、是否复制完整。"),
        ("invalidapikey",
         "API Key 无效。请检查 Key 是否正确。"),
        ("insufficient",
         "账户余额不足或配额不足。请充值或提升套餐后重试。"),
        ("quota",
         "配额不足或已超限。请稍后重试或提升套餐。"),
        ("rate limit",
         "请求过于频繁，触发限流。请稍等片刻再试。"),
        ("ratelimit",
         "请求过于频繁，触发限流。请稍等片刻再试。"),
        ("not found",
         "请求的资源/模型不存在。请检查模型名称或端点。"),
        ("timeout",
         "上游响应超时。请稍后重试。"),
    ]
    for key, zh in rules:
        if key in low:
            return f"{zh}（原始信息：{s[:200]}）"
    return s


def _get_fallback_models(cfg: ProviderConfig, protocol: str) -> List[str]:
    """
    当上游 API 拉取失败时，返回该协议的常用模型列表
    这样用户至少能看到一些选项
    """
    if cfg.type == "video":
        return [
            "doubao-seedance-2.0",
            "doubao-seedance-2.0-fast",
            "doubao-seedance-1.5-pro",
            "veo-3-1-generate-preview",
            "veo-3-1-fast-generate-preview",
            "veo-3-0-generate-001",
            "veo-2-0-generate-001",
            "wanx2.1-t2v-turbo",
            "wanx2.1-t2v-plus",
            "hailuoai-video",
            "kling-v2",
            "kling-v1",
            "gen-3a-turbo",
            "gen-3a-turbo-video",
            "sora",
        ]
    if protocol == "gemini":
        return [
            "gemini-2.0-flash-exp-image-generation",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
        ]
    elif protocol == "qwen":
        return [
            "qwen3.6-Plus (qwen3.6-plus-image)",
            "qwen3.5-Plus (qwen3.5-plus-image)",
            "qwen3.5-Flash (qwen3.5-flash-image)",
            "qwen3-Max (qwen3-max-2026-01-23-image)",
            "qwen3.6-27B (qwen3.6-27b-image)",
            "qwen3.6-35B-A3B (qwen3.6-35b-a3b-image)",
            "qwen3.5-27B (qwen3.5-27b-image)",
            "qwen3.5-397B-A17B (qwen3.5-397b-a17b-image)",
            "qwen3.5-Omni-Flash (qwen3.5-omni-flash-image)",
            "qwen3.5-Omni-Plus (qwen3.5-omni-plus-image)",
            "qwen3.5-122B-A10B (qwen3.5-122b-a10b-image)",
            "qwen3-Coder (qwen3-coder-plus-image)",
            "qwen3-Omni-Flash (qwen3-omni-flash-2025-12-01-image)",
            "qwen3-VL-235B-A22B (qwen3-vl-plus-a10b-image)",
            "qwen3-235B-A22B (qwen-plus-2025-07-28-image)",
        ]
    else:  # openai or agnes
        if cfg.type == "llm":
            return [
                "gpt-4o-mini", "gpt-4o", "gpt-4-turbo",
                "deepseek-chat", "deepseek-reasoner",
                "qwen-turbo", "qwen-plus", "qwen-max",
                "claude-3-haiku", "claude-3-sonnet",
            ]
        fallback = [
            "gpt-image-2",
            "gpt-image-1",
            "dall-e-3",
            "dall-e-2",
            "flux-dev",
            "flux-schnell",
            "sd-xl",
            "sd-3",
        ]
        if protocol == "agnes":
            return ["agnes-image-2.0-flash"]
        return fallback


# 兼容旧代码导出
PROVIDERS = {}  # 不再使用，保留防报错
