"""Authenticated image ingest helpers for remote push integrations."""
import hashlib
import hmac
import io
import json
import os
import re
from pathlib import PurePosixPath
from typing import Dict, Optional

from PIL import Image


MAX_PUSH_IMAGE_BYTES = int(os.getenv("GENBOX_PUSH_MAX_BYTES", str(25 * 1024 * 1024)))
PUSH_CONTRACT_VERSION = "v1"
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def push_max_image_bytes() -> int:
    """Return the byte limit used by this running receiver process."""
    return MAX_PUSH_IMAGE_BYTES


def validate_source_sha256(value: str) -> str:
    """Validate an optional sender-provided digest without trusting it."""
    normalized = str(value or "")
    if not normalized:
        return ""
    if not SHA256_PATTERN.fullmatch(normalized):
        raise ValueError("source_sha256 must be a canonical SHA-256 digest")
    return normalized.lower()


def load_push_keys(raw: Optional[str] = None) -> Dict[str, str]:
    """Load a source-id to API-key map from GENBOX_PUSH_KEYS JSON."""
    value = os.getenv("GENBOX_PUSH_KEYS", "") if raw is None else raw
    if not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("GENBOX_PUSH_KEYS must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError("GENBOX_PUSH_KEYS must be a JSON object")
    return {
        str(source_id): str(key)
        for source_id, key in parsed.items()
        if str(source_id).strip() and str(key)
    }


def authenticate_push_source(source_id: str, api_key: str, raw_keys: Optional[str] = None) -> bool:
    if not SOURCE_ID_PATTERN.fullmatch(source_id or ""):
        return False
    configured_keys = load_push_keys(raw_keys)
    if raw_keys is not None:
        expected = configured_keys.get(source_id)
        return bool(expected) and hmac.compare_digest(expected, api_key or "")
    from sync.push_sources import authenticate_source

    managed = authenticate_source(source_id, api_key or "")
    if managed is not None:
        return managed
    expected = configured_keys.get(source_id)
    return bool(expected) and hmac.compare_digest(expected, api_key or "")


def validate_remote_path(remote_path: str) -> str:
    """Require an unambiguous source-relative POSIX path without changing it."""
    value = str(remote_path or "")
    if not value or value != value.strip() or len(value) > 1024:
        raise ValueError("remote_path must be a stable relative path")
    if (
        "\\" in value
        or "//" in value
        or value.startswith("/")
        or value.endswith("/")
        or WINDOWS_DRIVE_PATTERN.match(value)
    ):
        raise ValueError("remote_path must be a stable relative path")
    if "://" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("remote_path must be a stable relative path")
    parts = PurePosixPath(value).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("remote_path must be a stable relative path")
    return value


def validate_image_payload(payload: bytes, content_type: str = "") -> dict:
    if not payload:
        raise ValueError("empty image payload")
    max_bytes = push_max_image_bytes()
    if len(payload) > max_bytes:
        raise ValueError(f"image exceeds {max_bytes} byte limit")
    if content_type and not content_type.lower().startswith("image/"):
        raise ValueError("content type must be image/*")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
            image_format = str(image.format or "").lower()
    except Exception as exc:
        raise ValueError("invalid image payload") from exc
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
        "width": width,
        "height": height,
        "format": image_format,
    }
