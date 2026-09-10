"""Validate bounded, secret-free plans for VPS read-only discovery.

This module deliberately handles only the authorization, host-trust, and
operation boundary.  It neither connects to a target nor accepts a shell
command from a browser or a plan file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import ipaddress
import posixpath
import re
from typing import Any

from extensions.models import HOST_KEY_ALGORITHMS, is_canonical_host_key_trust


READ_ONLY_SCOPE = "read-only-discovery"
TARGET_ROLES = frozenset({"isolated-development", "production-read-only"})
_HOST_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}")
_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_RECORD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}")
_CONTAINER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_PATH_PATTERN = re.compile(r"/[A-Za-z0-9._/-]*")
_LABELS = frozenset({
    "com.genbox.managed",
    "com.genbox.instance",
    "com.docker.compose.project",
    "com.docker.compose.project.working_dir",
    "com.docker.compose.service",
})
_NO_ARGUMENT_OPERATIONS = frozenset({
    "identity",
    "os_release",
    "cpu_architecture",
    "cpu_count",
    "memory_summary",
    "home_directory",
    "python_version",
    "uv_version",
    "docker_version",
    "compose_version",
    "docker_ps",
    "compose_ls",
    "listening_ports",
})
_CONTAINER_OPERATIONS = frozenset({"container_summary", "container_mounts"})
_PATH_OPERATIONS = frozenset({"filesystem_summary", "capacity", "directory_size"})
ALLOWED_OPERATIONS = frozenset(
    _NO_ARGUMENT_OPERATIONS | _CONTAINER_OPERATIONS | _PATH_OPERATIONS | {"container_label"}
)


class DiscoveryPlanValidationError(ValueError):
    """A fail-closed error which names a field, never its supplied value."""

    def __init__(self, field: str):
        self.field = field
        super().__init__(f"invalid read-only discovery plan field: {field}")


@dataclass(frozen=True)
class ValidatedDiscoveryPlan:
    """A normalized, non-secret plan ready for a fixed-command executor."""

    authorization: dict[str, Any]
    trust: dict[str, Any]
    operations: tuple[dict[str, str], ...]


def _require_mapping(value: Any, field: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise DiscoveryPlanValidationError(field)
    return value


def _normalize_host(value: Any, field: str) -> str:
    host = str(value or "").strip()
    if not host or any(character.isspace() for character in host):
        raise DiscoveryPlanValidationError(field)
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        if not _HOST_PATTERN.fullmatch(host):
            raise DiscoveryPlanValidationError(field)
        return host.rstrip(".").lower()


def _normalize_port(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise DiscoveryPlanValidationError(field)
    return value


def _normalize_username(value: Any, field: str) -> str:
    username = str(value or "").strip()
    if not _USERNAME_PATTERN.fullmatch(username):
        raise DiscoveryPlanValidationError(field)
    return username


def _normalize_record(value: Any, field: str) -> str:
    record = str(value or "").strip()
    if not _RECORD_PATTERN.fullmatch(record):
        raise DiscoveryPlanValidationError(field)
    return record


def _normalize_timestamp(value: Any, field: str) -> str:
    timestamp = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DiscoveryPlanValidationError(field) from exc
    if parsed.tzinfo is None:
        raise DiscoveryPlanValidationError(field)
    return timestamp


def _normalize_path(value: Any, field: str) -> str:
    path = str(value or "").strip()
    if not _PATH_PATTERN.fullmatch(path) or "\x00" in path:
        raise DiscoveryPlanValidationError(field)
    normalized = posixpath.normpath(path)
    if normalized != path or "/../" in f"/{path.lstrip('/')}":
        raise DiscoveryPlanValidationError(field)
    return normalized


def _normalize_operation(raw: Any, index: int) -> dict[str, str]:
    prefix = f"operations[{index}]"
    if not isinstance(raw, dict):
        raise DiscoveryPlanValidationError(prefix)
    operation = raw.get("id")
    if operation not in ALLOWED_OPERATIONS:
        raise DiscoveryPlanValidationError(f"{prefix}.id")
    if operation in _NO_ARGUMENT_OPERATIONS:
        _require_mapping(raw, prefix, {"id"})
        return {"id": operation}
    if operation in _CONTAINER_OPERATIONS:
        _require_mapping(raw, prefix, {"id", "container"})
        container = str(raw.get("container") or "").strip()
        if not _CONTAINER_PATTERN.fullmatch(container):
            raise DiscoveryPlanValidationError(f"{prefix}.container")
        return {"id": operation, "container": container}
    if operation == "container_label":
        _require_mapping(raw, prefix, {"id", "container", "label"})
        container = str(raw.get("container") or "").strip()
        if not _CONTAINER_PATTERN.fullmatch(container):
            raise DiscoveryPlanValidationError(f"{prefix}.container")
        label = str(raw.get("label") or "").strip()
        if label not in _LABELS:
            raise DiscoveryPlanValidationError(f"{prefix}.label")
        return {"id": operation, "container": container, "label": label}
    _require_mapping(raw, prefix, {"id", "path"})
    return {"id": operation, "path": _normalize_path(raw.get("path"), f"{prefix}.path")}


def validate_read_only_discovery_plan(raw: Any) -> ValidatedDiscoveryPlan:
    """Validate a plan without resolving DNS, opening SSH, or writing state."""
    plan = _require_mapping(raw, "plan", {"authorization", "trust", "operations"})
    authorization = _require_mapping(
        plan["authorization"],
        "authorization",
        {"scope", "target_role", "host", "port", "username", "approval_record_id", "approved_at"},
    )
    if authorization["scope"] != READ_ONLY_SCOPE:
        raise DiscoveryPlanValidationError("authorization.scope")
    if authorization["target_role"] not in TARGET_ROLES:
        raise DiscoveryPlanValidationError("authorization.target_role")
    normalized_authorization = {
        "scope": READ_ONLY_SCOPE,
        "target_role": authorization["target_role"],
        "host": _normalize_host(authorization["host"], "authorization.host"),
        "port": _normalize_port(authorization["port"], "authorization.port"),
        "username": _normalize_username(authorization["username"], "authorization.username"),
        "approval_record_id": _normalize_record(
            authorization["approval_record_id"], "authorization.approval_record_id"
        ),
        "approved_at": _normalize_timestamp(authorization["approved_at"], "authorization.approved_at"),
    }
    trust = _require_mapping(
        plan["trust"],
        "trust",
        {
            "expected_host",
            "expected_port",
            "expected_algorithm",
            "expected_fingerprint",
            "observed_host",
            "observed_port",
            "observed_algorithm",
            "observed_fingerprint",
        },
    )
    normalized_trust = {
        "expected_host": _normalize_host(trust["expected_host"], "trust.expected_host"),
        "expected_port": _normalize_port(trust["expected_port"], "trust.expected_port"),
        "expected_algorithm": str(trust["expected_algorithm"] or "").strip(),
        "expected_fingerprint": str(trust["expected_fingerprint"] or "").strip(),
        "observed_host": _normalize_host(trust["observed_host"], "trust.observed_host"),
        "observed_port": _normalize_port(trust["observed_port"], "trust.observed_port"),
        "observed_algorithm": str(trust["observed_algorithm"] or "").strip(),
        "observed_fingerprint": str(trust["observed_fingerprint"] or "").strip(),
    }
    if normalized_trust["expected_algorithm"] not in HOST_KEY_ALGORITHMS:
        raise DiscoveryPlanValidationError("trust.expected_algorithm")
    if not is_canonical_host_key_trust(
        normalized_trust["expected_algorithm"], normalized_trust["expected_fingerprint"]
    ):
        raise DiscoveryPlanValidationError("trust.expected_fingerprint")
    for field in ("host", "port"):
        if normalized_authorization[field] != normalized_trust[f"expected_{field}"]:
            raise DiscoveryPlanValidationError(f"trust.expected_{field}")
        if normalized_authorization[field] != normalized_trust[f"observed_{field}"]:
            raise DiscoveryPlanValidationError(f"trust.observed_{field}")
    if normalized_trust["expected_algorithm"] != normalized_trust["observed_algorithm"]:
        raise DiscoveryPlanValidationError("trust.observed_algorithm")
    if normalized_trust["expected_fingerprint"] != normalized_trust["observed_fingerprint"]:
        raise DiscoveryPlanValidationError("trust.observed_fingerprint")
    operations = plan["operations"]
    # A bootstrap `docker_ps` operation may safely derive a bounded set of
    # per-container summary, mount, label, and directory-size operations.  The
    # executor re-validates that derived plan before each new operation is used.
    if not isinstance(operations, list) or not operations or len(operations) > 256:
        raise DiscoveryPlanValidationError("operations")
    normalized_operations = tuple(_normalize_operation(item, index) for index, item in enumerate(operations))
    if len({tuple(sorted(item.items())) for item in normalized_operations}) != len(normalized_operations):
        raise DiscoveryPlanValidationError("operations")
    return ValidatedDiscoveryPlan(normalized_authorization, normalized_trust, normalized_operations)


def extend_read_only_discovery_plan(
    plan: ValidatedDiscoveryPlan,
    operations: list[dict[str, str]],
) -> ValidatedDiscoveryPlan:
    """Return a re-validated plan with executor-derived, bounded operations.

    Callers may only pass handles and paths already returned by an approved
    discovery operation.  This function still validates their shape and never
    accepts a shell command or browser-provided operation.
    """
    return validate_read_only_discovery_plan({
        "authorization": plan.authorization,
        "trust": plan.trust,
        "operations": [*plan.operations, *operations],
    })
