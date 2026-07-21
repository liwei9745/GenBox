"""Versioned, public-only persistence for extension deployment task snapshots."""

from __future__ import annotations

import copy
import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from config import STORAGE_DIR
from extensions.deployment_failures import VALID_FAILURE_COMBINATIONS


TASK_STORE_SCHEMA_VERSION = 1
EXTENSION_TASKS_FILE = Path(os.environ.get("GENBOX_EXTENSION_TASKS_FILE", STORAGE_DIR / "extension_tasks.json"))
TASK_STATUSES = {"queued", "running", "completed", "failed", "cancelled", "interrupted"}

_TASK_FIELDS = {
    "id", "status", "phase", "progress", "steps", "logs", "error", "host_key",
    "result", "created_at", "updated_at", "recovery_action", "failed_phase", "error_code",
    "deployment_attempt_id", "deployment_context_fingerprint",
}
_INSTANCE_FIELDS = {
    "id", "target_id", "project", "strategy", "deployment_mode", "compose_project",
    "service_port", "install_dir", "data_dir", "image", "version", "status",
    "console_url", "api_url", "managed", "clone_source_id", "clone_scope",
    "created_at", "updated_at",
}
_SENSITIVE_TEXT = re.compile(
    r"(?:password|private[ _-]?key|passphrase|sudo|admin[ _-]?key|bearer|"
    r"-----begin(?: [a-z0-9]+)? private key-----|key[ _-]?block)",
    re.IGNORECASE,
)
_REDACTED_DETAIL = "Sensitive task detail redacted."


class TaskStore:
    """Persist task state without retaining deployment requests or credentials."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path or EXTENSION_TASKS_FILE)
        self.lock = threading.RLock()
        self.warning: str | None = None

    def load(self) -> list[dict[str, Any]]:
        with self.lock:
            if not self.path.exists():
                return []
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or payload.get("schema_version") != TASK_STORE_SCHEMA_VERSION:
                    raise ValueError("unsupported task store schema")
                tasks = payload.get("tasks")
                if not isinstance(tasks, list) or not all(isinstance(task, dict) for task in tasks):
                    raise ValueError("invalid task store payload")
                if not all(self._valid_task(task) for task in tasks):
                    raise ValueError("invalid task store record")
                return [self._public_task(task) for task in tasks]
            except Exception:
                self._quarantine_invalid_file()
                self.warning = "Previous deployment task state could not be read and was preserved safely."
                return []

    def save(self, tasks: list[dict[str, Any]]) -> None:
        with self.lock:
            public_tasks = [self._public_task(task) for task in tasks]
            if not all(self._valid_task(task) for task in public_tasks):
                raise ValueError("invalid task store record")
            payload = {
                "schema_version": TASK_STORE_SCHEMA_VERSION,
                "tasks": public_tasks,
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
            try:
                temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                os.replace(temporary, self.path)
            finally:
                if temporary.exists():
                    temporary.unlink()

    def _quarantine_invalid_file(self) -> None:
        if not self.path.exists():
            return
        quarantine = self.path.with_name(f"{self.path.name}.invalid.{uuid.uuid4().hex}.json")
        try:
            os.replace(self.path, quarantine)
        except OSError:
            # The source remains untouched if it cannot be isolated.
            pass

    @staticmethod
    def _public_task(task: dict[str, Any]) -> dict[str, Any]:
        public = {key: copy.deepcopy(task[key]) for key in _TASK_FIELDS if key in task}
        if "error" in public:
            public["error"] = TaskStore._safe_text(public["error"])
        if isinstance(public.get("steps"), list):
            public["steps"] = [
                {key: copy.deepcopy(step[key]) for key in ("id", "label", "status") if key in step}
                for step in public["steps"] if isinstance(step, dict)
            ]
        if isinstance(public.get("logs"), list):
            public["logs"] = [
                {
                    key: (TaskStore._safe_text(log[key]) if key == "message" else copy.deepcopy(log[key]))
                    for key in ("time", "message") if key in log
                }
                for log in public["logs"] if isinstance(log, dict)
            ]
        result = public.get("result")
        if isinstance(result, dict):
            public["result"] = {
                key: copy.deepcopy(result[key])
                for key in ("url", "api_url", "admin_key_available", "credential_recovery_required")
                if key in result
            }
            instance = result.get("instance")
            if isinstance(instance, dict):
                public["result"]["instance"] = {
                    key: copy.deepcopy(instance[key]) for key in _INSTANCE_FIELDS if key in instance
                }
        return public

    @staticmethod
    def _valid_task(task: dict[str, Any]) -> bool:
        if not isinstance(task.get("id"), str) or not task["id"].strip():
            return False
        attempt_id = task.get("deployment_attempt_id")
        context_fingerprint = task.get("deployment_context_fingerprint")
        if (attempt_id is None) != (context_fingerprint is None):
            return False
        if attempt_id is not None:
            if not isinstance(attempt_id, str) or not re.fullmatch(r"[a-f0-9]{32}", attempt_id):
                return False
            if not isinstance(context_fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", context_fingerprint):
                return False
        if task.get("status") not in TASK_STATUSES:
            return False
        if not isinstance(task.get("phase"), str):
            return False
        if isinstance(task.get("progress"), bool) or not isinstance(task.get("progress"), int):
            return False
        if not 0 <= task["progress"] <= 100:
            return False
        if not isinstance(task.get("steps"), list) or not isinstance(task.get("logs"), list):
            return False
        if task.get("result") is not None and not isinstance(task["result"], dict):
            return False
        for field in ("error", "recovery_action", "failed_phase", "error_code"):
            if task.get(field) is not None and not isinstance(task[field], str):
                return False
        failed_phase = task.get("failed_phase")
        error_code = task.get("error_code")
        recovery_action = task.get("recovery_action")
        if task["status"] == "failed":
            # Schema v1 records written before structured failures had neither
            # field. Keep those readable so the UI can render a safe fallback.
            legacy_failure = "failed_phase" not in task and "error_code" not in task
            if legacy_failure and recovery_action is not None:
                return False
            if not legacy_failure and (failed_phase, error_code, recovery_action) not in VALID_FAILURE_COMBINATIONS:
                return False
        else:
            if failed_phase is not None or error_code is not None:
                return False
            allowed_actions = {
                "interrupted": {"regenerate_plan_and_reprovide_credentials"},
                "completed": {None, "reverify_ownership_and_rotate_admin_key"},
                "queued": {None},
                "running": {None},
                "cancelled": {None},
            }
            if recovery_action not in allowed_actions[task["status"]]:
                return False
        for field in ("host_key", "created_at", "updated_at"):
            if not isinstance(task.get(field), str):
                return False
        for step in task["steps"]:
            if not isinstance(step, dict) or not all(isinstance(step.get(field), str) for field in ("id", "label", "status")):
                return False
        for log in task["logs"]:
            if not isinstance(log, dict) or not all(isinstance(log.get(field), str) for field in ("time", "message")):
                return False
        result = task.get("result")
        if isinstance(result, dict):
            if any(key in result and not isinstance(result[key], str) for key in ("url", "api_url")):
                return False
            if any(key in result and not isinstance(result[key], bool) for key in ("admin_key_available", "credential_recovery_required")):
                return False
            if "instance" in result and not isinstance(result["instance"], dict):
                return False
        return True

    @staticmethod
    def _safe_text(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return _REDACTED_DETAIL if _SENSITIVE_TEXT.search(value) else value
