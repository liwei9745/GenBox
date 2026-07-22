"""Versioned, explicit public-only persistence for extension deployment tasks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from config import STORAGE_DIR
from extensions.deployment_failures import VALID_FAILURE_COMBINATIONS


TASK_STORE_SCHEMA_VERSION = 2
LEGACY_TASK_STORE_SCHEMA_VERSION = 1
EXTENSION_TASKS_FILE = Path(os.environ.get("GENBOX_EXTENSION_TASKS_FILE", STORAGE_DIR / "extension_tasks.json"))
TASK_STATUSES = {"queued", "running", "completed", "failed", "cancelled", "interrupted"}

PUBLIC_TASK_FIELDS = {
    "id", "status", "phase", "progress", "steps", "created_at", "updated_at",
    "recovery_action", "failed_phase", "error_code", "evidence_manifest",
}
PUBLIC_STEP_LABELS = {
    "connect": "Connect",
    "docker": "Check Docker",
    "prepare": "Prepare deployment",
    "pull": "Prepare image",
    "start": "Start service",
    "verify": "Verify service",
}
PUBLIC_STEP_STATUSES = {"pending", "running", "success", "failed"}
_LOGICAL_FIELD_ID = re.compile(r"[a-z][a-z0-9_.-]{0,79}")


class TaskStore:
    """Persist and return only the allowlisted public deployment task schema."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path or EXTENSION_TASKS_FILE)
        self.lock = threading.RLock()
        self.warning: str | None = None
        self._writes_blocked = False

    def load(self) -> list[dict[str, Any]]:
        with self.lock:
            if not self.path.exists():
                return []
            recognized_legacy = False
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("invalid task store payload")
                tasks = payload.get("tasks")
                if not isinstance(tasks, list) or not all(isinstance(task, dict) for task in tasks):
                    raise ValueError("invalid task store payload")
                schema_version = payload.get("schema_version")
                if schema_version == TASK_STORE_SCHEMA_VERSION:
                    if not all(self._valid_task(task) for task in tasks) or not self._unique_task_ids(tasks):
                        raise ValueError("invalid task store record")
                    return [self.public_task(task) for task in tasks]
                if schema_version == LEGACY_TASK_STORE_SCHEMA_VERSION:
                    migrated = [self._migrate_legacy_task(task) for task in tasks]
                    if not all(self._valid_task(task) for task in migrated) or not self._unique_task_ids(migrated):
                        raise ValueError("invalid legacy task store record")
                    recognized_legacy = True
                    self._write_tasks(migrated)
                    self.warning = "Previous deployment tasks were recovered with public-only state."
                    return migrated
                raise ValueError("unsupported task store schema")
            except Exception:
                if recognized_legacy:
                    self._writes_blocked = True
                    self.warning = "Previous deployment task state requires safe migration before it can be shown."
                    return []
                quarantined = self._quarantine_invalid_file()
                self._writes_blocked = not quarantined
                self.warning = (
                    "Previous deployment task state could not be read; the original remains in place and writes are blocked."
                    if self._writes_blocked
                    else "Previous deployment task state could not be read and was preserved safely."
                )
                return []

    def save(self, tasks: list[dict[str, Any]]) -> None:
        with self.lock:
            if self._writes_blocked:
                raise RuntimeError("deployment task store writes are blocked until preserved state is resolved")
            public_tasks = [self.public_task(task) for task in tasks]
            if not all(self._valid_task(task) for task in public_tasks) or not self._unique_task_ids(public_tasks):
                raise ValueError("invalid task store record")
            self._write_tasks(public_tasks)

    def _write_tasks(self, tasks: list[dict[str, Any]]) -> None:
        payload = {
            "schema_version": TASK_STORE_SCHEMA_VERSION,
            "tasks": tasks,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _quarantine_invalid_file(self) -> bool:
        if not self.path.exists():
            return True
        quarantine = self.path.with_name(f"{self.path.name}.invalid.{uuid.uuid4().hex}.json")
        try:
            os.replace(self.path, quarantine)
        except OSError:
            return False
        return True

    @staticmethod
    def _unique_task_ids(tasks: list[dict[str, Any]]) -> bool:
        task_ids = [task.get("id") for task in tasks]
        return len(task_ids) == len(set(task_ids))

    @staticmethod
    def interrupted_recovery_action(phase: Any) -> str:
        if phase in {"connect", "docker"}:
            return "regenerate_plan_and_reprovide_credentials"
        if phase == "prepare":
            return "inspect_owned_partial_deployment_and_regenerate_plan"
        return "inspect_owned_instance_and_regenerate_plan"

    @classmethod
    def public_task(cls, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("id")
        manifest = task.get("evidence_manifest")
        public_manifest = None
        if isinstance(manifest, dict):
            public_manifest = {
                "contract_version": manifest.get("contract_version"),
                "snapshot_digest": manifest.get("snapshot_digest"),
                "complete": manifest.get("complete"),
                "changed_fields": list(manifest.get("changed_fields", []))
                if isinstance(manifest.get("changed_fields"), list) else manifest.get("changed_fields"),
            }
        steps = []
        if isinstance(task.get("steps"), list):
            for step in task["steps"]:
                if not isinstance(step, dict):
                    steps.append({})
                    continue
                step_id = step.get("id")
                steps.append({
                    "id": step_id,
                    "label": PUBLIC_STEP_LABELS.get(step_id),
                    "status": step.get("status"),
                })
        return {
            "id": task_id,
            "status": task.get("status"),
            "phase": task.get("phase"),
            "progress": task.get("progress"),
            "steps": steps,
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
            "recovery_action": task.get("recovery_action"),
            "failed_phase": task.get("failed_phase"),
            "error_code": task.get("error_code"),
            "evidence_manifest": public_manifest,
        }

    @classmethod
    def _migrate_legacy_task(cls, task: dict[str, Any]) -> dict[str, Any]:
        required = {"id", "status", "phase", "progress", "steps", "created_at", "updated_at"}
        if not required.issubset(task):
            raise ValueError("unrecognized legacy task")
        status = task.get("status")
        failed_phase = task.get("failed_phase")
        error_code = task.get("error_code")
        recovery_action = task.get("recovery_action")
        if status in {"queued", "running", "interrupted"}:
            status = "interrupted"
            failed_phase = None
            error_code = None
            recovery_action = cls.interrupted_recovery_action(task.get("phase"))
        elif status == "completed":
            failed_phase = None
            error_code = None
            recovery_action = "reverify_ownership_and_rotate_admin_key"
        elif status == "failed":
            if (failed_phase, error_code, recovery_action) not in VALID_FAILURE_COMBINATIONS:
                status = "interrupted"
                failed_phase = None
                error_code = None
                recovery_action = "regenerate_plan_and_reprovide_credentials"
        elif status == "cancelled":
            failed_phase = None
            error_code = None
            recovery_action = None
        else:
            raise ValueError("unrecognized legacy task status")
        return cls.public_task({
            "id": task.get("id"),
            "status": status,
            "phase": task.get("phase"),
            "progress": task.get("progress"),
            "steps": task.get("steps"),
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
            "recovery_action": recovery_action,
            "failed_phase": failed_phase,
            "error_code": error_code,
            "evidence_manifest": task.get("evidence_manifest") or cls._recovery_manifest(str(task.get("id") or "")),
        })

    @staticmethod
    def _recovery_manifest(task_id: str) -> dict[str, Any]:
        digest = hashlib.sha256(f"legacy-public-task:{task_id}".encode("utf-8")).hexdigest()
        return {
            "contract_version": "phase4-v3",
            "snapshot_digest": digest,
            "complete": False,
            "changed_fields": ["legacy.task_state"],
        }

    @staticmethod
    def _valid_task(task: dict[str, Any]) -> bool:
        if set(task) != PUBLIC_TASK_FIELDS:
            return False
        if not isinstance(task.get("id"), str) or not task["id"].strip():
            return False
        if task.get("status") not in TASK_STATUSES:
            return False
        if task.get("phase") not in PUBLIC_STEP_LABELS:
            return False
        if isinstance(task.get("progress"), bool) or not isinstance(task.get("progress"), int):
            return False
        if not 0 <= task["progress"] <= 100:
            return False
        if not isinstance(task.get("steps"), list):
            return False
        seen_steps = set()
        for step in task["steps"]:
            if not isinstance(step, dict) or set(step) != {"id", "label", "status"}:
                return False
            step_id = step.get("id")
            if step_id not in PUBLIC_STEP_LABELS or step_id in seen_steps:
                return False
            seen_steps.add(step_id)
            if step.get("label") != PUBLIC_STEP_LABELS[step_id] or step.get("status") not in PUBLIC_STEP_STATUSES:
                return False
        if not task["steps"]:
            return False
        for field in ("created_at", "updated_at"):
            if not isinstance(task.get(field), str) or not task[field]:
                return False
        manifest = task.get("evidence_manifest")
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"contract_version", "snapshot_digest", "complete", "changed_fields"}
            or manifest.get("contract_version") != "phase4-v3"
            or not isinstance(manifest.get("snapshot_digest"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", manifest["snapshot_digest"])
            or not isinstance(manifest.get("complete"), bool)
            or not isinstance(manifest.get("changed_fields"), list)
            or any(not isinstance(field, str) or not _LOGICAL_FIELD_ID.fullmatch(field) for field in manifest["changed_fields"])
        ):
            return False
        failed_phase = task.get("failed_phase")
        error_code = task.get("error_code")
        recovery_action = task.get("recovery_action")
        if any(value is not None and not isinstance(value, str) for value in (failed_phase, error_code, recovery_action)):
            return False
        if task["status"] == "failed":
            if (failed_phase, error_code, recovery_action) not in VALID_FAILURE_COMBINATIONS:
                return False
        else:
            if failed_phase is not None or error_code is not None:
                return False
            allowed_actions = {
                "interrupted": {
                    "regenerate_plan_and_reprovide_credentials",
                    "inspect_owned_partial_deployment_and_regenerate_plan",
                    "inspect_owned_instance_and_regenerate_plan",
                },
                "completed": {None, "reverify_ownership_and_rotate_admin_key"},
                "queued": {None},
                "running": {None},
                "cancelled": {None},
            }
            if recovery_action not in allowed_actions[task["status"]]:
                return False
        return True
