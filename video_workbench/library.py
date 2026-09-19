"""Minimal, metadata-free discovery of unregistered local library candidates."""

import base64
import binascii
import heapq
import json
import os
from pathlib import Path
import re
import stat
import time

from .media.ingest import _fail


_SCAN_ENTRIES = 100_000
_SCAN_SECONDS = 2.0


def validate_identity(kind, item_id):
    if not isinstance(kind, str) or kind not in {"image", "video"} or (
        not isinstance(item_id, str) or not 0 < len(item_id) <= 255
        or item_id in {".", ".."} or any(char in item_id for char in "/\\:\x00")
        or any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in item_id)
    ):
        raise _fail("invalid_request", "admission", field="library_item_id")


def _cursor(kind, query, position):
    raw = json.dumps([1, kind, query, *position], ensure_ascii=False, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _position(cursor, kind, query):
    if not isinstance(cursor, str) or len(cursor) > 3072:
        raise _fail("invalid_request", "admission", field="cursor")
    if not cursor:
        return ("", "")
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", cursor):
            raise ValueError
        data = json.loads(base64.b64decode(
            cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True,
        ).decode("utf-8"))
        if not isinstance(data, list) or len(data) != 5 or type(data[0]) is not int or data[:3] != [1, kind, query]:
            raise ValueError
        validate_identity(data[3], data[4])
        if kind is not None and data[3] != kind:
            raise ValueError
        if _cursor(kind, query, data[3:]) != cursor:
            raise ValueError
        return tuple(data[3:])
    except (ValueError, TypeError, UnicodeError, binascii.Error, RecursionError):
        raise _fail("invalid_request", "admission", field="cursor") from None


def list_candidates(service, owner, *, cursor="", kind=None, query="", limit=20):
    service._owner(owner)
    if (kind is not None and (not isinstance(kind, str) or kind not in {"image", "video"})) or (
        type(limit) is not int or not 1 <= limit <= 50
        or not isinstance(query, str) or len(query) > 128
        or any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in query)
    ):
        raise _fail("invalid_request", "admission")
    position = _position(cursor, kind, query)
    started = time.monotonic()
    count = 0
    folded = query.casefold()

    def candidates():
        nonlocal count
        for media_kind, root, suffix in (
            ("image", service.gallery, ".png"), ("video", service.videos, ".mp4"),
        ):
            if kind is not None and kind != media_kind:
                continue
            service.media._assert_confined(root, root)
            if not root.exists():
                continue
            if not root.is_dir():
                raise _fail("internal", "lookup")
            before = root.stat()
            stamp = (before.st_dev, before.st_ino, before.st_mtime_ns)
            with os.scandir(root) as entries:
                for entry in entries:
                    count += 1
                    if count > _SCAN_ENTRIES or time.monotonic() - started > _SCAN_SECONDS:
                        raise _fail("conflict", "lookup")
                    name = Path(entry.name)
                    key = (media_kind, name.stem)
                    if name.suffix != suffix or key <= position or folded not in name.stem.casefold():
                        continue
                    # Exclude names the exact resolver cannot select.
                    if not 0 < len(name.stem) <= 255 or name.stem in {".", ".."} or (
                        any(char in name.stem for char in "/\\:\x00")
                        or any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in name.stem)
                    ):
                        continue
                    path = root / entry.name
                    service.media._assert_confined(path, root)
                    info = entry.stat(follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode):
                        continue
                    yield (*key, info.st_size)
            service.media._assert_confined(root, root)
            after = root.stat()
            if stamp != (after.st_dev, after.st_ino, after.st_mtime_ns):
                raise _fail("conflict", "lookup")
        if time.monotonic() - started > _SCAN_SECONDS:
            raise _fail("conflict", "lookup")

    try:
        selected = heapq.nsmallest(limit + 1, candidates())
    except FileNotFoundError:
        raise _fail("conflict", "lookup") from None
    return {
        "items": [
            {"library_kind": row[0], "library_item_id": row[1], "byte_length": row[2]}
            for row in selected[:limit]
        ],
        "next_cursor": _cursor(kind, query, selected[limit - 1][:2]) if len(selected) > limit else None,
    }
