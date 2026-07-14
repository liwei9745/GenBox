"""Authenticated image ingest helpers for remote push integrations."""
import hashlib
import hmac
import io
import json
import os
import re
from typing import Dict, Optional

from PIL import Image


MAX_PUSH_IMAGE_BYTES = int(os.getenv("GENBOX_PUSH_MAX_BYTES", str(25 * 1024 * 1024)))
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


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
    expected = load_push_keys(raw_keys).get(source_id)
    return bool(expected) and hmac.compare_digest(expected, api_key or "")


def validate_image_payload(payload: bytes, content_type: str = "") -> dict:
    if not payload:
        raise ValueError("empty image payload")
    if len(payload) > MAX_PUSH_IMAGE_BYTES:
        raise ValueError(f"image exceeds {MAX_PUSH_IMAGE_BYTES} byte limit")
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
