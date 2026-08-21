import json
import hashlib
import hmac
import os
import re
import secrets
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from config import STORAGE_DIR
from extensions.models import (
    ExtensionConfig,
    EnvironmentProjection,
    ExtensionInstance,
    ExtensionTarget,
    is_canonical_host_key_trust,
)
from extensions.capabilities import project_store_actions


EXTENSIONS_FILE = STORAGE_DIR / "extensions.json"


PAIRING_PROTOCOL_VERSION = "GENBOX-PAIR/1"
PAIRING_TTL_SECONDS = 300
_PAIRING_ID_BYTES = 18
_PAIRING_CHALLENGE_BYTES = 24


@contextmanager
def _config_lock():
    """Serialize config read/compare/write sections across threads and workers."""
    lock_path = EXTENSIONS_FILE.with_name(f".{EXTENSIONS_FILE.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
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


def target_identity_digest(target: ExtensionTarget) -> str:
    """Return a digest that changes when a target identity generation changes."""
    value = "\x1f".join((
        target.id,
        target.host,
        str(target.port),
        target.username,
        str(target.identity_version),
        target.host_key_algorithm,
        target.host_key,
        target.primary_network,
        target.network_url,
    ))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HostKeyPairing:
    pairing_id: str
    challenge: str
    target_id: str
    target_identity: str
    algorithm: str
    fingerprint: str
    expires_at: float


class HostKeyPairingManager:
    """Short-lived, single-use pairing state; deliberately never persisted."""

    def __init__(self, ttl_seconds: int = PAIRING_TTL_SECONDS):
        self.ttl_seconds = int(ttl_seconds)
        self._lock = threading.Lock()
        self._records: dict[str, HostKeyPairing] = {}

    def _prune(self, now: float) -> None:
        self._records = {
            key: record for key, record in self._records.items()
            if record.expires_at > now
        }

    def create(self, target: ExtensionTarget, algorithm: str, fingerprint: str) -> HostKeyPairing:
        if not is_canonical_host_key_trust(algorithm, fingerprint):
            raise ValueError("unsupported_host_key")
        now = time.time()
        record = HostKeyPairing(
            pairing_id=secrets.token_urlsafe(_PAIRING_ID_BYTES),
            challenge=secrets.token_urlsafe(_PAIRING_CHALLENGE_BYTES),
            target_id=target.id,
            target_identity=target_identity_digest(target),
            algorithm=algorithm,
            fingerprint=fingerprint,
            expires_at=now + self.ttl_seconds,
        )
        with self._lock:
            self._prune(now)
            self._records[record.pairing_id] = record
        return record

    def consume(self, pairing_id: str) -> HostKeyPairing | None:
        """Atomically consume a record, including on validation failure."""
        now = time.time()
        with self._lock:
            self._prune(now)
            return self._records.pop(pairing_id, None)

    def discard(self, pairing_id: str) -> None:
        with self._lock:
            self._records.pop(pairing_id, None)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


host_key_pairings = HostKeyPairingManager()

_PAIRING_KEY_PATHS = {
    "ssh-ed25519": "/etc/ssh/ssh_host_ed25519_key.pub",
    "ecdsa-sha2-nistp256": "/etc/ssh/ssh_host_ecdsa_key.pub",
    "ssh-rsa": "/etc/ssh/ssh_host_rsa_key.pub",
}
_PAIRING_RESPONSE_RE = re.compile(
    r"^GENBOX-PAIR/1 code=([A-Za-z0-9_-]{20,128}) proof=([a-f0-9]{64})$"
)


def build_host_key_pairing_helper(record: HostKeyPairing) -> str:
    """Build a fixed command; only generated opaque values are interpolated."""
    path = _PAIRING_KEY_PATHS.get(record.algorithm)
    if not path:
        raise ValueError("unsupported_host_key")
    # Keep this one line and shell-portable across the supported OpenSSH VPS images.
    return (
        "f='" + path + "'; [ -r \"$f\" ] || exit 1; "
        "k=$(ssh-keygen -lf \"$f\" -E sha256 2>/dev/null | awk 'NR==1 {print $2}'); "
        "a=$(awk 'NR==1 {print $1}' \"$f\"); "
        "case \"$a\" in ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa) ;; *) exit 1 ;; esac; "
        "p=$(printf '%s' \"$a:$k:" + record.challenge + "\" | sha256sum 2>/dev/null | awk 'NR==1 {print $1}'); "
        "case \"$p\" in *[!a-f0-9]*|'') exit 1 ;; esac; "
        "[ ${#p} -eq 64 ] || exit 1; "
        "printf 'GENBOX-PAIR/1 code=%s proof=%s\\n' '" + record.challenge + "' \"$p\""
    )


def parse_host_key_pairing_response(value: str) -> dict[str, str] | None:
    """Parse exactly one generated response line, never arbitrary shell/text."""
    if not isinstance(value, str) or len(value) > 512:
        return None
    # A pasted terminal line may carry its final newline; other whitespace is invalid.
    match = _PAIRING_RESPONSE_RE.fullmatch(value.rstrip("\r\n"))
    if not match:
        return None
    code, proof = match.groups()
    return {
        "code": code,
        "proof": proof,
    }


def load_config() -> ExtensionConfig:
    if not EXTENSIONS_FILE.exists():
        return ExtensionConfig()
    try:
        raw = json.loads(EXTENSIONS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[Extensions] 配置读取失败: {exc}")
        return ExtensionConfig()
    if not isinstance(raw, dict):
        return ExtensionConfig()
    targets = []
    invalid_targets = 0
    raw_targets = raw.get("targets", [])
    if not isinstance(raw_targets, list):
        raw_targets = []
        invalid_targets += 1
    for item in raw_targets:
        try:
            # A pre-role record must not silently become deployable.
            item = {**item}
            item.setdefault("target_role", "production-read-only")
            targets.append(ExtensionTarget(**item))
        except Exception:
            invalid_targets += 1
    instances = []
    invalid_instances = 0
    raw_instances = raw.get("instances", [])
    if not isinstance(raw_instances, list):
        raw_instances = []
        invalid_instances += 1
    for item in raw_instances:
        try:
            instances.append(ExtensionInstance(**item))
        except Exception:
            invalid_instances += 1
    if invalid_targets or invalid_instances:
        print(
            "[Extensions] 已隔离无效配置记录: "
            f"targets={invalid_targets}, instances={invalid_instances}"
        )
    projections = []
    raw_projections = raw.get("environment_projections", [])
    if not isinstance(raw_projections, list):
        raw_projections = []
    for item in raw_projections:
        try:
            projections.append(EnvironmentProjection(**item))
        except Exception:
            continue
    batch_target_ids = raw.get("batch_target_ids", [])
    if not isinstance(batch_target_ids, list):
        batch_target_ids = []
    raw_generations = raw.get("target_generations", {})
    if not isinstance(raw_generations, dict):
        raw_generations = {}
    target_generations = {
        str(key): int(value) for key, value in raw_generations.items()
        if str(value).isdigit() and int(value) >= 0
    }
    for target in targets:
        target_generations[target.id] = max(target_generations.get(target.id, 0), target.identity_version)
    return ExtensionConfig(
        targets=targets,
        instances=instances,
        environment_projections=projections,
        batch_target_ids=[str(item) for item in batch_target_ids],
        target_generations=target_generations,
    )


def save_config(config: ExtensionConfig) -> None:
    EXTENSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = EXTENSIONS_FILE.with_name(f".{EXTENSIONS_FILE.name}.{os.getpid()}.tmp")
    temporary.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary, EXTENSIONS_FILE)


def upsert_target(data: dict) -> ExtensionTarget:
    with _config_lock():
        config = load_config()
        target_id = str(data.get("id") or uuid.uuid4().hex[:8])
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        existing = next((item for item in config.targets if item.id == target_id), None)
        submitted_identity = (
            str(data.get("host", existing.host if existing else "")),
            int(data.get("port", existing.port if existing else 22)),
            str(data.get("username", existing.username if existing else "")),
        )
        same_identity = bool(existing) and submitted_identity == (existing.host, existing.port, existing.username)
        generation = max(
            int(config.target_generations.get(target_id, 0)),
            int(existing.identity_version) if existing else 0,
        )
        if not existing or not same_identity:
            generation += 1
        generation = max(1, generation)
        target = ExtensionTarget(
            **{
                **(existing.model_dump() if existing else {}),
                **data,
                "id": target_id,
                "identity_version": generation,
                "created_at": existing.created_at if existing else now,
                "updated_at": now,
            }
        )
        config.targets = [item for item in config.targets if item.id != target_id] + [target]
        config.target_generations[target_id] = generation
        save_config(config)
        return target


def _target_endpoint_identity(host: object, port: object, username: object) -> tuple[str, int, str]:
    """Normalize only fields that identify a saved SSH endpoint."""
    return (
        str(host or "").strip().lower().rstrip("."),
        int(port or 22),
        str(username or "").strip(),
    )


def save_target_metadata(data: dict) -> ExtensionTarget:
    """Save browser-editable target metadata without accepting trust material."""
    with _config_lock():
        config = load_config()
        target_id = str(data.get("id") or uuid.uuid4().hex[:8])
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        existing = next((item for item in config.targets if item.id == target_id), None)
        browser_fields = {"name", "host", "port", "username", "target_role", "chatgpt2api_port"}
        submitted = {key: value for key, value in data.items() if key in browser_fields}
        if "target_role" not in submitted and not existing:
            submitted["target_role"] = "production-read-only"
        if not existing and not data.get("id"):
            submitted_identity = _target_endpoint_identity(
                submitted.get("host"), submitted.get("port", 22), submitted.get("username")
            )
            matching_targets = [
                item for item in config.targets
                if _target_endpoint_identity(item.host, item.port, item.username) == submitted_identity
            ]
            if matching_targets:
                # Metadata saves never receive trust material, so reuse rather than duplicate.
                existing = max(matching_targets, key=lambda item: (item.updated_at, item.id))
                target_id = existing.id
        same_identity = bool(existing) and _target_endpoint_identity(
            submitted.get("host", existing.host),
            submitted.get("port", existing.port),
            submitted.get("username", existing.username),
        ) == _target_endpoint_identity(existing.host, existing.port, existing.username)
        generation = max(
            int(config.target_generations.get(target_id, 0)),
            int(existing.identity_version) if existing else 0,
        )
        if not existing or not same_identity:
            generation += 1
        generation = max(1, generation)
        trust_state = {
            "host_key_algorithm": existing.host_key_algorithm if same_identity else "",
            "host_key": existing.host_key if same_identity else "",
            "available_networks": existing.available_networks if same_identity else [],
            "network_url": existing.network_url if same_identity else "",
            "network_verified_at": existing.network_verified_at if same_identity else "",
        }
        target = ExtensionTarget(
            **{
                **(existing.model_dump() if existing else {}),
                **submitted,
                "id": target_id,
                **trust_state,
                "identity_version": generation,
                "created_at": existing.created_at if existing else now,
                "updated_at": now,
            }
        )
        config.targets = [item for item in config.targets if item.id != target_id] + [target]
        config.target_generations[target_id] = generation
        save_config(config)
        return target


def save_environment_projection(
    target: ExtensionTarget,
    *,
    docker_available: bool,
    compose_available: bool,
    evidence_complete: bool,
    observed_at: str | None = None,
) -> EnvironmentProjection:
    """Persist only sanitized, target-bound discovery facts from the server."""
    projection = EnvironmentProjection(
        target_id=target.id,
        target_identity_digest=target_identity_digest(target),
        observed_at=observed_at or datetime.now(timezone.utc).isoformat(),
        docker_available=bool(docker_available),
        compose_available=bool(compose_available),
        evidence_complete=bool(evidence_complete),
        confidence=("high" if docker_available and compose_available and evidence_complete else "unknown"),
    )
    with _config_lock():
        config = load_config()
        config.environment_projections = [
            item for item in config.environment_projections
            if item.target_id != target.id
        ] + [projection]
        save_config(config)
    return projection


def invalidate_environment_projection(target_id: str) -> None:
    with _config_lock():
        config = load_config()
        config.environment_projections = [
            item for item in config.environment_projections if item.target_id != target_id
        ]
        save_config(config)


def get_environment_projection(target: ExtensionTarget) -> EnvironmentProjection | None:
    projection = next(
        (item for item in load_config().environment_projections if item.target_id == target.id),
        None,
    )
    if not projection or not hmac.compare_digest(
        projection.target_identity_digest, target_identity_digest(target)
    ):
        return None
    try:
        observed_at = datetime.fromisoformat(projection.observed_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    if (datetime.now(timezone.utc) - observed_at).total_seconds() > 3600:
        return None
    return projection


def confirm_target_host_key(
    expected: ExtensionTarget,
    algorithm: str,
    fingerprint: str,
) -> ExtensionTarget:
    """Persist a probed identity pair only if target and trust state are unchanged."""
    with _config_lock():
        config = load_config()
        current = next((item for item in config.targets if item.id == expected.id), None)
        if not current:
            raise ValueError("target_missing")
        comparisons = (
            hmac.compare_digest(current.host, expected.host),
            hmac.compare_digest(str(current.port), str(expected.port)),
            hmac.compare_digest(current.username, expected.username),
            hmac.compare_digest(str(current.identity_version), str(expected.identity_version)),
            hmac.compare_digest(current.host_key_algorithm, expected.host_key_algorithm),
            hmac.compare_digest(current.host_key, expected.host_key),
        )
        if not all(comparisons):
            raise ValueError("target_changed")
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        confirmed = current.model_copy(update={
            "host_key_algorithm": algorithm,
            "host_key": fingerprint,
            "updated_at": now,
        })
        config.targets = [item for item in config.targets if item.id != current.id] + [confirmed]
        save_config(config)
        return confirmed


def reset_target_host_key(target_id: str) -> ExtensionTarget | None:
    """Atomically discard saved host trust and invalidate outstanding pairings."""
    with _config_lock():
        config = load_config()
        current = next((item for item in config.targets if item.id == target_id), None)
        if not current:
            return None
        if not current.host_key_algorithm and not current.host_key:
            return current
        generation = max(
            int(config.target_generations.get(target_id, 0)),
            int(current.identity_version),
        ) + 1
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        reset = current.model_copy(update={
            "host_key_algorithm": "",
            "host_key": "",
            "identity_version": generation,
            "available_networks": [],
            "network_url": "",
            "network_verified_at": "",
            "updated_at": now,
        })
        config.targets = [item for item in config.targets if item.id != target_id] + [reset]
        config.target_generations[target_id] = generation
        save_config(config)
        return reset


def list_targets() -> list[ExtensionTarget]:
    return load_config().targets


def get_target(target_id: str) -> ExtensionTarget | None:
    return next((item for item in load_config().targets if item.id == target_id), None)


def get_batch_target_ids() -> list[str]:
    config = load_config()
    valid_ids = {target.id for target in config.targets}
    return [target_id for target_id in config.batch_target_ids if target_id in valid_ids]


def save_batch_target_ids(target_ids: list[str]) -> list[str]:
    config = load_config()
    valid_ids = {target.id for target in config.targets}
    selected = list(dict.fromkeys(target_id for target_id in target_ids if target_id in valid_ids))
    config.batch_target_ids = selected
    save_config(config)
    return selected


def delete_target(target_id: str) -> bool:
    with _config_lock():
        config = load_config()
        remaining = [item for item in config.targets if item.id != target_id]
        if len(remaining) == len(config.targets):
            return False
        config.targets = remaining
        save_config(config)
        return True


def upsert_instance(data: dict) -> ExtensionInstance:
    config = load_config()
    instance_id = str(data.get("id") or "").strip()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    existing = next((item for item in config.instances if item.id == instance_id), None)
    target_id = str(data.get("target_id") or "").strip()
    if existing and existing.target_id != target_id:
        raise ValueError("instance_id_conflicts_with_another_target")
    merged = dict(data)
    if existing:
        for field in (
            "status", "data_dir", "ownership", "container_id", "container_name",
            "install_dir", "compose_project", "image", "console_url", "api_url",
        ):
            unknown_values = {None, "", "unknown"} if field == "status" else {None, ""}
            if merged.get(field) in unknown_values:
                merged.pop(field, None)
        if existing.managed:
            merged["managed"] = True
            merged["ownership"] = existing.ownership or "managed"
            merged["service_port"] = existing.service_port
    instance = ExtensionInstance(**{
        **(existing.model_dump() if existing else {}),
        **merged,
        "id": instance_id,
        "created_at": existing.created_at if existing else now,
        "updated_at": now,
    })
    config.instances = [item for item in config.instances if item.id != instance_id] + [instance]
    save_config(config)
    return instance


def list_instances(target_id: str = "") -> list[ExtensionInstance]:
    items = load_config().instances
    return [item for item in items if not target_id or item.target_id == target_id]


def get_instance(instance_id: str) -> ExtensionInstance | None:
    return next((item for item in load_config().instances if item.id == instance_id), None)


def _store_item(item: dict) -> dict:
    """Return the public Store item with registry-derived actions."""
    return {
        **item,
        "actions": project_store_actions(item),
    }


def store_projection(
    catalog: list[dict], instances: list[ExtensionInstance], *,
    environment_projection: EnvironmentProjection | None = None,
) -> dict:
    """Build the read-only Installed/Recommended/All Store projection."""
    catalog_by_id = {str(item.get("id")): item for item in catalog}
    all_items = [_store_item(item) for item in catalog]
    installed = []
    for instance in instances:
        item = catalog_by_id.get(instance.project)
        if not item:
            continue
        installed.append({
            **_store_item(item),
            "instance_id": instance.id,
            "instance_status": instance.status,
            "ownership": "managed" if instance.managed is True else "external",
            "actions": project_store_actions(item) if instance.managed is True else [],
        })
    environment_verified = bool(
        environment_projection
        and environment_projection.confidence == "high"
        and environment_projection.evidence_complete
        and environment_projection.docker_available
        and environment_projection.compose_available
    )
    recommended = []
    if environment_verified:
        for item in all_items:
            if item["id"] == "chatgpt2api":
                recommended.append({
                    **item,
                    "confidence": environment_projection.confidence,
                    "reasons": ["已验证 Docker 与 Docker Compose 环境，且 discovery 证据完整"],
                })
    return {
        "installed": installed,
        "recommended": recommended,
        "all": all_items,
    }


def public_store_projection() -> dict:
    """Build Store views without exposing instance credentials or identities."""
    from extensions.catalog import CATALOG

    target = next((item for item in list_targets() if item.target_role == "isolated-development"), None)
    projection = get_environment_projection(target) if target else None
    return store_projection(CATALOG, list_instances(), environment_projection=projection)
