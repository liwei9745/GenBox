import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

import main
from extensions.orchestrator import ExtensionTaskManager
from extensions.task_store import TASK_STORE_SCHEMA_VERSION, TaskStore


def task(task_id, status="completed", updated_at="2026-07-17T00:00:00.000Z", **extra):
    return {
        "id": task_id,
        "status": status,
        "phase": "verify",
        "progress": 100 if status == "completed" else 20,
        "steps": [{"id": "connect", "label": "Connect", "status": "success"}],
        "logs": [{"time": "00:00:00", "message": "Public progress"}],
        "error": None,
        "host_key": "SHA256:public",
        "result": None,
        "created_at": "2026-07-16T00:00:00.000Z",
        "updated_at": updated_at,
        "recovery_action": None,
        **extra,
    }


def test_task_store_roundtrip_uses_versioned_atomic_json(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    store = TaskStore(path)
    calls = []
    real_replace = os.replace

    def record_replace(source, target):
        calls.append((Path(source), Path(target), Path(source).exists()))
        return real_replace(source, target)

    monkeypatch.setattr("extensions.task_store.os.replace", record_replace)
    store.save([task("finished")])

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == TASK_STORE_SCHEMA_VERSION
    assert payload["tasks"][0]["id"] == "finished"
    assert store.load()[0]["status"] == "completed"
    assert calls[-1][1] == path
    assert calls[-1][2] is True
    assert not list(tmp_path.glob("*.tmp"))


def test_completed_failed_and_cancelled_tasks_survive_manager_rebuild(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks = {
        "completed": task("completed", "completed", "2026-07-17T00:00:03.000Z"),
        "failed": task("failed", "failed", "2026-07-17T00:00:02.000Z", error="safe failure"),
        "cancelled": task("cancelled", "cancelled", "2026-07-17T00:00:01.000Z", error="cancelled"),
    }
    manager._persist()

    rebuilt = ExtensionTaskManager(store_path=path)
    assert {name: rebuilt.get(name)["status"] for name in manager.tasks} == {
        "completed": "completed", "failed": "failed", "cancelled": "cancelled",
    }


def test_running_or_queued_task_recovers_as_interrupted_without_runner(tmp_path):
    path = tmp_path / "extension_tasks.json"
    TaskStore(path).save([task("running", "running"), task("queued", "queued")])

    rebuilt = ExtensionTaskManager(store_path=path)
    for task_id in ("running", "queued"):
        state = rebuilt.get(task_id)
        assert state["status"] == "interrupted"
        assert state["recovery_action"] == "regenerate_plan_and_reprovide_credentials"
        assert task_id not in rebuilt.runners
    assert rebuilt.list_summary()["active_task_id"] is None


def test_corrupt_or_unknown_schema_is_quarantined_without_overwriting_original(tmp_path):
    for name, content in (("corrupt", "{not json"), ("unknown", '{"schema_version": 99, "tasks": []}')):
        path = tmp_path / f"{name}.json"
        path.write_text(content, encoding="utf-8")
        store = TaskStore(path)

        assert store.load() == []
        assert store.warning
        quarantined = list(tmp_path.glob(f"{name}.json.invalid.*.json"))
        assert len(quarantined) == 1
        assert quarantined[0].read_text(encoding="utf-8") == content
        assert not path.exists()


def test_task_store_excludes_all_deployment_secret_sentinels(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["public"] = task("public", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "admin_key": "admin-secret",
        "instance": {"id": "instance-a", "managed": True, "password": "ssh-secret"},
    })
    manager._persist()

    text = path.read_text(encoding="utf-8")
    for sentinel in ("admin-secret", "ssh-secret", "private-key-secret", "passphrase-secret", "sudo-secret", "enrollment-secret"):
        assert sentinel not in text
    assert '"admin_key_available": true' in text


def test_delivery_is_once_only_and_restart_requires_credential_recovery(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["delivery"] = task("delivery", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["delivery"] = "gbx-secret-delivery"
    manager._persist()
    assert "gbx-secret-delivery" not in path.read_text(encoding="utf-8")
    assert manager.take_delivery("delivery") == "gbx-secret-delivery"
    assert manager.take_delivery("delivery") is None
    assert manager.get("delivery")["result"]["admin_key_available"] is False

    manager.tasks["restart"] = task("restart", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-b", "managed": True},
    })
    manager._persist()
    rebuilt = ExtensionTaskManager(store_path=path)
    recovered = rebuilt.get("restart")
    assert recovered["result"]["admin_key_available"] is False
    assert recovered["result"]["credential_recovery_required"] is True
    assert recovered["recovery_action"] == "reverify_ownership_and_rotate_admin_key"
    assert rebuilt.take_delivery("restart") is None


def test_task_list_route_is_sorted_and_reports_active_latest_and_404(tmp_path, monkeypatch):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks = {
        "older": task("older", "failed", "2026-07-17T00:00:01.000Z"),
        "active": task("active", "running", "2026-07-17T00:00:02.000Z"),
        "latest": task("latest", "completed", "2026-07-17T00:00:03.000Z"),
    }
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    response = client.get("/api/extensions/tasks")
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data["tasks"]] == ["latest", "active", "older"]
    assert data["active_task_id"] == "active"
    assert data["latest_task_id"] == "latest"
    assert client.get("/api/extensions/tasks/missing").status_code == 404


def test_task_manager_keeps_fifty_terminal_tasks_without_pruning_active_tasks(tmp_path):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks = {
        f"done-{index}": task(f"done-{index}", "completed", f"2026-07-17T00:00:00.{index:03d}Z")
        for index in range(52)
    }
    manager.tasks["active-running"] = task("active-running", "running")
    manager.tasks["active-queued"] = task("active-queued", "queued")
    manager._persist()

    assert len([item for item in manager.tasks.values() if item["status"] == "completed"]) == 50
    assert {"active-running", "active-queued"}.issubset(manager.tasks)


def test_extensions_ui_restores_server_task_state_without_browser_task_storage():
    script = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    assert "'/api/extensions/tasks'" in script
    assert "summary.active_task_id||summary.latest_task_id" in script
    assert "startTaskPolling(taskId)" in script
    assert "task.status==='interrupted'" in script
    assert "clearInterval(taskPoll)" in script
    assert "extensionRecoveryText(task.recovery_action)" in script
    assert "localStorage" not in script
