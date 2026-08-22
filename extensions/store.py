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
    EnvironmentFacts,
    EnvironmentProjection,
    ExtensionInstance,
    ExtensionTarget,
    is_canonical_host_key_trust,
)
from extensions.capabilities import project_store_actions


EXTENSIONS_FILE = STORAGE_DIR / "extensions.json"


PAIRING_PROTOCOL_VERSION = "GENBOX-PAIR/1"
PAIRING_TTL_SECONDS = 300
ENVIRONMENT_FACTS_TTL_SECONDS = 3600
ENVIRONMENT_FACT_PROBES = (
    "os", "arch", "cpu", "memory_mb", "disk_mb", "docker", "compose", "python", "uv",
)
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


@dataclass(frozen=True)
class _VerifiedEnvironmentProjection:
    """Store write token issued only after server-side discovery validation."""

    projection: EnvironmentProjection


@dataclass(frozen=True)
class _VerifiedEnvironmentFacts:
    """Store write token issued only after server-side discovery validation."""

    facts: EnvironmentFacts


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
    environment_facts = []
    raw_environment_facts = raw.get("environment_facts", [])
    if not isinstance(raw_environment_facts, list):
        raw_environment_facts = []
    for item in raw_environment_facts:
        try:
            environment_facts.append(EnvironmentFacts(**item))
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
        environment_facts=environment_facts,
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


def verified_environment_projection(
    target: ExtensionTarget,
    discovery: dict,
    public: dict,
) -> _VerifiedEnvironmentProjection | None:
    """Create a Store write token from complete, successful server evidence."""
    if discovery.get("ok") is not True:
        return None
    evidence_manifest = public.get("evidence_manifest")
    if not isinstance(evidence_manifest, dict) or evidence_manifest.get("complete") is not True:
        return None
    capabilities = public.get("capabilities")
    if not isinstance(capabilities, dict):
        return None
    docker_available = capabilities.get("docker_available")
    compose_available = capabilities.get("compose_available")
    if not isinstance(docker_available, bool) or not isinstance(compose_available, bool):
        return None
    projection = EnvironmentProjection(
        target_id=target.id,
        target_identity_digest=target_identity_digest(target),
        observed_at=datetime.now(timezone.utc).isoformat(),
        docker_available=docker_available,
        compose_available=compose_available,
        evidence_complete=True,
        confidence=("high" if docker_available and compose_available else "unknown"),
    )
    return _VerifiedEnvironmentProjection(projection)


def save_environment_projection(verified: _VerifiedEnvironmentProjection) -> EnvironmentProjection:
    """Persist only a Store projection issued by verified server evidence."""
    if not isinstance(verified, _VerifiedEnvironmentProjection):
        raise TypeError("verified_environment_projection_required")
    projection = verified.projection
    with _config_lock():
        config = load_config()
        config.environment_projections = [
            item for item in config.environment_projections
            if item.target_id != projection.target_id
        ] + [projection]
        save_config(config)
    return projection


def _normalized_fact_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    if value.casefold() in {"unknown", "unavailable", "none", "null"}:
        return None
    return value if len(value) <= 256 else None


def _normalized_version_value(value: object) -> str | None:
    value = _normalized_fact_value(value)
    return value if value and re.search(r"\d", value) else None


def _normalized_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.fullmatch(r"[1-9]\d*", value):
        return None
    return int(value)


def verified_environment_facts(
    target: ExtensionTarget,
    discovery: dict,
    public: dict,
) -> _VerifiedEnvironmentFacts | None:
    """Create a facts write token from complete, successful server evidence."""
    if not isinstance(discovery, dict) or discovery.get("ok") is not True:
        return None
    evidence_manifest = public.get("evidence_manifest") if isinstance(public, dict) else None
    if not isinstance(evidence_manifest, dict) or evidence_manifest.get("complete") is not True:
        return None
    if evidence_manifest.get("fact_probe_complete") is not True:
        return None
    statuses = evidence_manifest.get("fact_probe_statuses")
    if not isinstance(statuses, dict) or any(
        not isinstance(statuses.get(probe), int)
        or isinstance(statuses.get(probe), bool)
        or statuses.get(probe) != 0
        for probe in ENVIRONMENT_FACT_PROBES
    ):
        return None
    output_validity = evidence_manifest.get("fact_probe_output_validity")
    if not isinstance(output_validity, dict) or any(
        output_validity.get(probe) is not True for probe in ENVIRONMENT_FACT_PROBES
    ):
        return None
    environment = discovery.get("environment")
    if not isinstance(environment, dict):
        return None
    normalized_values = {
        "os": _normalized_fact_value(environment.get("os")),
        "arch": _normalized_fact_value(environment.get("arch")),
        "cpu": _normalized_positive_int(environment.get("cpu")),
        "memory_mb": _normalized_positive_int(environment.get("memory_mb")),
        "disk_mb": _normalized_positive_int(environment.get("disk_free_mb")),
        "docker": _normalized_version_value(environment.get("docker_version")),
        "compose": _normalized_version_value(environment.get("compose_version")),
        "python": _normalized_version_value(environment.get("python_version")),
        "uv": _normalized_version_value(environment.get("uv_version")),
    }
    if any(value is None for value in normalized_values.values()):
        return None
    current = get_target(target.id)
    if current is None or not hmac.compare_digest(
        target_identity_digest(current), target_identity_digest(target)
    ):
        return None
    facts = EnvironmentFacts(
        target_id=target.id,
        target_identity_digest=target_identity_digest(target),
        observed_at=datetime.now(timezone.utc).isoformat(),
        os=normalized_values["os"],
        arch=normalized_values["arch"],
        cpu_cores=normalized_values["cpu"],
        memory_mb=normalized_values["memory_mb"],
        disk_mb=normalized_values["disk_mb"],
        docker_version=normalized_values["docker"],
        compose_version=normalized_values["compose"],
        python_version=normalized_values["python"],
        uv_version=normalized_values["uv"],
    )
    return _VerifiedEnvironmentFacts(facts)


def save_environment_facts(verified: _VerifiedEnvironmentFacts) -> EnvironmentFacts:
    """Persist only facts issued by verified server evidence."""
    if not isinstance(verified, _VerifiedEnvironmentFacts):
        raise TypeError("verified_environment_facts_required")
    facts = verified.facts
    with _config_lock():
        config = load_config()
        current = next((item for item in config.targets if item.id == facts.target_id), None)
        if current is None or not hmac.compare_digest(
            facts.target_identity_digest, target_identity_digest(current)
        ):
            raise ValueError("saved_target_identity_required")
        config.environment_facts = [
            item for item in config.environment_facts if item.target_id != facts.target_id
        ] + [facts]
        save_config(config)
    return facts


def save_environment_observation(
    projection_token: _VerifiedEnvironmentProjection,
    facts_token: _VerifiedEnvironmentFacts,
) -> tuple[EnvironmentProjection, EnvironmentFacts]:
    """Persist one complete projection/facts observation in one config transaction."""
    if not isinstance(projection_token, _VerifiedEnvironmentProjection):
        raise TypeError("verified_environment_projection_required")
    if not isinstance(facts_token, _VerifiedEnvironmentFacts):
        raise TypeError("verified_environment_facts_required")
    projection = projection_token.projection
    facts = facts_token.facts
    if projection.target_id != facts.target_id or not hmac.compare_digest(
        projection.target_identity_digest, facts.target_identity_digest
    ):
        raise ValueError("environment_observation_identity_mismatch")
    with _config_lock():
        config = load_config()
        current = next((item for item in config.targets if item.id == facts.target_id), None)
        if current is None or not hmac.compare_digest(
            facts.target_identity_digest, target_identity_digest(current)
        ):
            raise ValueError("saved_target_identity_required")
        config.environment_projections = [
            item for item in config.environment_projections if item.target_id != projection.target_id
        ] + [projection]
        config.environment_facts = [
            item for item in config.environment_facts if item.target_id != facts.target_id
        ] + [facts]
        save_config(config)
    return projection, facts


def invalidate_environment_facts(target_id: str) -> None:
    with _config_lock():
        config = load_config()
        config.environment_facts = [
            item for item in config.environment_facts if item.target_id != target_id
        ]
        save_config(config)


def get_environment_facts(target: ExtensionTarget) -> EnvironmentFacts | None:
    facts = next(
        (item for item in load_config().environment_facts if item.target_id == target.id),
        None,
    )
    if not facts or not hmac.compare_digest(
        facts.target_identity_digest, target_identity_digest(target)
    ):
        return None
    try:
        observed_at = datetime.fromisoformat(facts.observed_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if observed_at.tzinfo is None or observed_at.utcoffset() != timezone.utc.utcoffset(observed_at):
        return None
    age_seconds = (datetime.now(timezone.utc) - observed_at).total_seconds()
    if age_seconds < 0 or age_seconds > ENVIRONMENT_FACTS_TTL_SECONDS:
        return None
    return facts


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
    age_seconds = (datetime.now(timezone.utc) - observed_at).total_seconds()
    if age_seconds < 0 or age_seconds > 3600:
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


_PUBLIC_STORE_FIELDS = (
    "id",
    "name",
    "repository",
    "category",
    "status",
    "integrates_proxy",
    "provides_proxy",
    "manifest_version",
    "license",
    "provenance",
    "permissions",
    "network_exposure",
    "data_sensitivity",
    "operational_risk",
    "adapter_ref",
)

_PUBLIC_STORE_DEFAULTS = {
    "id": "",
    "name": "",
    "repository": "",
    "category": "",
    "status": "unknown",
    "integrates_proxy": False,
    "provides_proxy": False,
    "manifest_version": "unknown",
    "license": "unknown",
    "provenance": "unavailable",
    "permissions": [],
    "network_exposure": "unknown",
    "data_sensitivity": "unknown",
    "operational_risk": "unknown",
    "adapter_ref": "",
}

_RECOMMENDATION_FACT_FIELDS = (
    ("os", "os"),
    ("arch", "arch"),
    ("cpu_cores", "cpu_cores"),
    ("memory_mb", "memory_mb"),
    ("disk_mb", "disk_mb"),
    ("docker_version", "docker_version"),
    ("compose_version", "compose_version"),
    ("python_version", "python_version"),
    ("uv_version", "uv_version"),
)


def _store_item(item: dict) -> dict:
    """Project a Store item through an explicit public-field whitelist.

    Unknown or future catalog fields never reach the browser; actions come only
    from the executable capability registry.
    """
    if not isinstance(item, dict):
        return {**_PUBLIC_STORE_DEFAULTS, "permissions": [], "actions": []}
    public = {}
    for field in _PUBLIC_STORE_FIELDS:
        value = item.get(field, _PUBLIC_STORE_DEFAULTS[field])
        if field == "permissions":
            value = value if isinstance(value, list) and all(isinstance(item, str) for item in value) else []
            value = list(value)
        elif field in {"integrates_proxy", "provides_proxy"}:
            value = value if isinstance(value, bool) else _PUBLIC_STORE_DEFAULTS[field]
        elif not isinstance(value, str):
            value = _PUBLIC_STORE_DEFAULTS[field]
        public[field] = value
    public["id"] = str(public["id"] or "")
    public["actions"] = project_store_actions(item)
    return public


def _fresh_environment_facts(
    facts: EnvironmentFacts | None,
    *,
    target_id: str = "",
    target_identity_digest: str = "",
) -> EnvironmentFacts | None:
    """Return only a current facts record bound to the projection identity."""
    if not isinstance(facts, EnvironmentFacts):
        return None
    if target_id and facts.target_id != target_id:
        return None
    if target_identity_digest and not hmac.compare_digest(
        facts.target_identity_digest, target_identity_digest
    ):
        return None
    try:
        observed_at = datetime.fromisoformat(facts.observed_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if observed_at.tzinfo is None or observed_at.utcoffset() != timezone.utc.utcoffset(observed_at):
        return None
    age_seconds = (datetime.now(timezone.utc) - observed_at).total_seconds()
    if age_seconds < 0 or age_seconds > ENVIRONMENT_FACTS_TTL_SECONDS:
        return None
    return facts


def _environment_fact_reasons(facts: EnvironmentFacts | None) -> tuple[list[str], list[str]]:
    """Explain only observed facts; an absent field is never given a default value."""
    reasons = []
    unknown_facts = []
    for field, label in _RECOMMENDATION_FACT_FIELDS:
        value = getattr(facts, field, None) if facts is not None else None
        if value is None:
            reasons.append(f"{label}=未观测")
            unknown_facts.append(label)
        else:
            reasons.append(f"{label}={value}")
    return reasons, unknown_facts


def _environment_facts_complete(facts: EnvironmentFacts | None) -> bool:
    return facts is not None and all(
        getattr(facts, field, None) is not None
        for field, _label in _RECOMMENDATION_FACT_FIELDS
    )


def _current_store_target() -> ExtensionTarget | None:
    return next(
        (item for item in list_targets() if item.target_role == "isolated-development"),
        None,
    )


def _same_environment_projection(
    left: EnvironmentProjection | None,
    right: EnvironmentProjection | None,
) -> bool:
    return (
        isinstance(left, EnvironmentProjection)
        and isinstance(right, EnvironmentProjection)
        and left.target_id == right.target_id
        and hmac.compare_digest(left.target_identity_digest, right.target_identity_digest)
        and left.model_dump() == right.model_dump()
    )


def store_projection(
    catalog: list[dict], instances: list[ExtensionInstance], *,
    environment_projection: EnvironmentProjection | None = None,
    environment_facts: EnvironmentFacts | None = None,
) -> dict:
    """Build the read-only Installed/Recommended/All Store projection.

    Fail-closed: missing or mistyped inputs never raise and never leak, and the
    recommended view is high only when the environment projection is complete,
    correctly typed, and bound to a non-empty target identity digest.
    """
    if not isinstance(catalog, list):
        catalog = []
    if not isinstance(instances, list):
        instances = []
    instances = [item for item in instances if isinstance(item, ExtensionInstance)]
    current_target = _current_store_target()
    authoritative_projection = (
        get_environment_projection(current_target) if current_target else None
    )
    if environment_projection is not None:
        if not _same_environment_projection(environment_projection, authoritative_projection):
            environment_projection = None
        else:
            environment_projection = authoritative_projection
    else:
        environment_projection = authoritative_projection
    if environment_facts is None and current_target is not None:
        environment_facts = get_environment_facts(current_target)
    catalog_by_id = {}
    for item in catalog:
        if not isinstance(item, dict):
            continue
        catalog_by_id[str(item.get("id") or "")] = item
    all_items = [_store_item(item) for item in catalog if isinstance(item, dict)]
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
        environment_projection is not None
        and environment_projection.confidence == "high"
        and environment_projection.evidence_complete is True
        and isinstance(environment_projection.docker_available, bool)
        and isinstance(environment_projection.compose_available, bool)
        and environment_projection.docker_available is True
        and environment_projection.compose_available is True
        and bool(environment_projection.target_identity_digest)
    )
    environment_facts = _fresh_environment_facts(
        environment_facts,
        target_id=(current_target.id if current_target else ""),
        target_identity_digest=(
            target_identity_digest(current_target) if current_target else ""
        ),
    )
    facts_reasons, unknown_facts = _environment_fact_reasons(environment_facts)
    facts_complete = _environment_facts_complete(environment_facts)
    recommended = []
    if environment_verified and facts_complete:
        for item in all_items:
            if item["id"] == "chatgpt2api":
                recommended.append({
                    **item,
                    "confidence": environment_projection.confidence,
                    "reasons": facts_reasons,
                    "unknown_facts": unknown_facts,
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
