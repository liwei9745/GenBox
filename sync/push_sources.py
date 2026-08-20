"""Durable, hashed credentials for GenBox-managed Push sources."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from config import STORAGE_DIR


PUSH_SOURCES_FILE = STORAGE_DIR / "push_sources.json"
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
KEY_PREFIX = "gpk-"
KEY_ITERATIONS = 310_000
SALT_BYTES = 16
KEY_BYTES = 32
_LOCK = threading.RLock()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _key_digest(value: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", value.encode("utf-8"), salt, KEY_ITERATIONS, dklen=KEY_BYTES
    ).hex()


def _empty_config() -> dict[str, Any]:
    return {"version": 1, "sources": []}


@contextmanager
def _config_lock():
    """Serialize registry updates across threads and GenBox processes."""
    lock_path = PUSH_SOURCES_FILE.with_name(f".{PUSH_SOURCES_FILE.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _load_config() -> dict[str, Any]:
    if not PUSH_SOURCES_FILE.exists():
        return _empty_config()
    try:
        data = json.loads(PUSH_SOURCES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("managed Push source configuration is unreadable") from exc
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("sources"), list):
        raise ValueError("managed Push source configuration is invalid")
    for item in data["sources"]:
        if not isinstance(item, dict):
            raise ValueError("managed Push source configuration is invalid")
        source_id = str(item.get("source_id") or "")
        target_id = str(item.get("target_id") or "")
        instance_id = str(item.get("instance_id") or "")
        salt = str(item.get("salt") or "")
        key_hash = str(item.get("key_hash") or "")
        created_at = item.get("created_at")
        updated_at = item.get("updated_at")
        if (
            SOURCE_ID_PATTERN.fullmatch(source_id) is None
            or not target_id
            or not instance_id
            or not isinstance(item.get("active"), bool)
            or len(salt) != SALT_BYTES * 2
            or len(key_hash) != KEY_BYTES * 2
            or not isinstance(created_at, str)
            or not isinstance(updated_at, str)
            or not created_at
            or not updated_at
            or (item.get("grant_delete") is not None and not isinstance(item.get("grant_delete"), bool))
        ):
            raise ValueError("managed Push source configuration is invalid")
        try:
            bytes.fromhex(salt)
            bytes.fromhex(key_hash)
        except ValueError as exc:
            raise ValueError("managed Push source configuration is invalid") from exc
    return data


def _save_config(config: dict[str, Any]) -> None:
    PUSH_SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = PUSH_SOURCES_FILE.with_name(f".{PUSH_SOURCES_FILE.name}.{secrets.token_hex(8)}.tmp")
    try:
        temporary.write_text(
            json.dumps(config, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, PUSH_SOURCES_FILE)
        if os.name != "nt":
            os.chmod(PUSH_SOURCES_FILE, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def _public(record: dict[str, Any]) -> dict[str, str | bool]:
    return {
        "source_id": str(record["source_id"]),
        "created_at": str(record["created_at"]),
        "updated_at": str(record["updated_at"]),
        "grant_delete": bool(record.get("grant_delete") is True),
    }


def _new_source_id(records: list[dict[str, Any]]) -> str:
    existing = {str(item.get("source_id") or "") for item in records}
    for _ in range(32):
        source_id = f"gbxps-{secrets.token_hex(12)}"
        if source_id not in existing:
            return source_id
    raise RuntimeError("could not allocate managed Push source identity")


def _new_key_record(
    source_id: str, target_id: str, instance_id: str, now: str
) -> tuple[dict[str, Any], str]:
    raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
    salt = secrets.token_bytes(SALT_BYTES)
    return {
        "source_id": source_id,
        "target_id": target_id,
        "instance_id": instance_id,
        "active": True,
        "salt": salt.hex(),
        "key_hash": _key_digest(raw_key, salt),
        "grant_delete": False,
        "created_at": now,
        "updated_at": now,
    }, raw_key


def create_source(target_id: str, instance_id: str) -> tuple[dict[str, str], str]:
    """Create a source and return its public metadata plus one-time raw key."""
    if not target_id or not instance_id:
        raise ValueError("managed instance is required")
    with _LOCK, _config_lock():
        config = _load_config()
        if any(
            item["target_id"] == target_id
            and item["instance_id"] == instance_id
            and item["active"]
            for item in config["sources"]
        ):
            raise ValueError("managed Push source already exists")
        now = _now()
        record, raw_key = _new_key_record(
            _new_source_id(config["sources"]), target_id, instance_id, now
        )
        config["sources"].append(record)
        _save_config(config)
    return _public(record), raw_key


def list_sources(target_id: str, instance_id: str) -> list[dict[str, str]]:
    with _LOCK, _config_lock():
        config = _load_config()
        return [
            _public(record)
            for record in config["sources"]
            if record["target_id"] == target_id and record["instance_id"] == instance_id and record["active"]
        ]


def rotate_source(source_id: str, target_id: str, instance_id: str) -> tuple[dict[str, str], str] | None:
    if SOURCE_ID_PATTERN.fullmatch(source_id or "") is None:
        return None
    with _LOCK, _config_lock():
        config = _load_config()
        record = next(
            (
                item
                for item in config["sources"]
                if item["source_id"] == source_id
                and item["target_id"] == target_id
                and item["instance_id"] == instance_id
                and item["active"]
            ),
            None,
        )
        if record is None:
            return None
        now = _now()
        replacement, raw_key = _new_key_record(source_id, target_id, instance_id, now)
        replacement["created_at"] = record["created_at"]
        replacement["grant_delete"] = bool(record.get("grant_delete") is True)
        config["sources"] = [replacement if item is record else item for item in config["sources"]]
        _save_config(config)
    return _public(replacement), raw_key


def revoke_source(source_id: str, target_id: str, instance_id: str) -> bool:
    if SOURCE_ID_PATTERN.fullmatch(source_id or "") is None:
        return False
    with _LOCK, _config_lock():
        config = _load_config()
        record = next(
            (
                item
                for item in config["sources"]
                if item["source_id"] == source_id
                and item["target_id"] == target_id
                and item["instance_id"] == instance_id
                and item["active"]
            ),
            None,
        )
        if record is None:
            return False
        record["active"] = False
        record["updated_at"] = _now()
        _save_config(config)
        return True


def revoke_target_sources(target_id: str) -> int:
    """Deactivate every managed source owned by a removed target."""
    if not target_id:
        return 0
    with _LOCK, _config_lock():
        config = _load_config()
        changed = 0
        now = _now()
        for record in config["sources"]:
            if record["target_id"] == target_id and record["active"]:
                record["active"] = False
                record["updated_at"] = now
                changed += 1
        if changed:
            _save_config(config)
        return changed


def set_source_grant_delete(source_id: str, target_id: str, instance_id: str, enabled: bool) -> bool:
    """Enable or disable deletion grant for one managed Push source.

    This is the receiver-side authority the sender's per-action user selection
    depends on: a receipt only contains ``safe_to_delete_source=true`` after the
    source owner explicitly granted deletion for this managed source. It is
    disabled by default and never inferred.
    """
    if SOURCE_ID_PATTERN.fullmatch(source_id or "") is None:
        return False
    with _LOCK, _config_lock():
        config = _load_config()
        record = next(
            (
                item
                for item in config["sources"]
                if item["source_id"] == source_id
                and item["target_id"] == target_id
                and item["instance_id"] == instance_id
                and item["active"]
            ),
            None,
        )
        if record is None:
            return False
        record["grant_delete"] = bool(enabled)
        record["updated_at"] = _now()
        _save_config(config)
        return True


def deletion_granted(source_id: str) -> bool:
    """Read-only: does this managed Push source have explicit deletion grant?"""
    if SOURCE_ID_PATTERN.fullmatch(source_id or "") is None:
        return False
    try:
        with _LOCK, _config_lock():
            config = _load_config()
            record = next((item for item in config["sources"] if item["source_id"] == source_id), None)
    except ValueError:
        # A damaged registry is never permission to grant deletion.
        return False
    if record is None or not record["active"]:
        return False
    return bool(record.get("grant_delete") is True)


def authenticate_source(source_id: str, key: str) -> bool | None:
    """Check one managed source without ever loading a raw key from disk."""
    if SOURCE_ID_PATTERN.fullmatch(source_id or "") is None:
        return False
    try:
        with _LOCK, _config_lock():
            config = _load_config()
            record = next((item for item in config["sources"] if item["source_id"] == source_id), None)
    except ValueError:
        # A damaged managed registry is never permission to fall back to a
        # similarly named legacy environment credential.
        return False
    if record is None:
        return None
    if not record["active"]:
        return False
    digest = _key_digest(key or "", bytes.fromhex(record["salt"]))
    return hmac.compare_digest(digest, record["key_hash"])
    if not record["active"]:
        return False
    digest = _key_digest(key or "", bytes.fromhex(record["salt"]))
    return hmac.compare_digest(digest, record["key_hash"])


def source_key_belongs_to_instance(
    source_id: str, target_id: str, instance_id: str, key: str,
) -> bool:
    """Verify a displayed one-time key still belongs to this managed instance."""
    if (
        SOURCE_ID_PATTERN.fullmatch(source_id or "") is None
        or not target_id
        or not instance_id
        or not key
    ):
        return False
    try:
        with _LOCK, _config_lock():
            config = _load_config()
            record = next(
                (
                    item
                    for item in config["sources"]
                    if item["source_id"] == source_id
                    and item["target_id"] == target_id
                    and item["instance_id"] == instance_id
                    and item["active"]
                ),
                None,
            )
    except ValueError:
        return False
    if record is None:
        return False
    digest = _key_digest(key, bytes.fromhex(record["salt"]))
    return hmac.compare_digest(digest, record["key_hash"])
