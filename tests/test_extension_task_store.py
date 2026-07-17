import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from extensions.models import ExtensionDeployRequest, ExtensionTarget, SSHCredential
from extensions.deployment_failures import FAILURES, VALID_FAILURE_COMBINATIONS
from extensions.orchestrator import ExtensionTaskManager, deployment_plans
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
        store.save([task("replacement")])
        assert json.loads(path.read_text(encoding="utf-8"))["tasks"][0]["id"] == "replacement"
        assert quarantined[0].read_text(encoding="utf-8") == content


def test_known_schema_field_corruption_quarantines_entire_task_store(tmp_path):
    invalid_values = {
        "id": [], "status": [], "steps": {}, "logs": {}, "result": [],
        "error": {}, "recovery_action": [], "phase": None, "progress": "10",
    }
    for field, value in invalid_values.items():
        path = tmp_path / f"invalid-{field}.json"
        record = task("invalid")
        record[field] = value
        original = json.dumps({"schema_version": TASK_STORE_SCHEMA_VERSION, "tasks": [record]})
        path.write_text(original, encoding="utf-8")

        manager = ExtensionTaskManager(store_path=path)

        assert manager.tasks == {}
        assert manager.runners == {}
        assert manager.store.warning
        quarantined = list(tmp_path.glob(f"invalid-{field}.json.invalid.*.json"))
        assert len(quarantined) == 1
        assert quarantined[0].read_text(encoding="utf-8") == original
        assert not path.exists()

    path = tmp_path / "invalid-status-value.json"
    record = task("invalid", status="not-a-task-status")
    original = json.dumps({"schema_version": TASK_STORE_SCHEMA_VERSION, "tasks": [record]})
    path.write_text(original, encoding="utf-8")
    manager = ExtensionTaskManager(store_path=path)
    assert manager.tasks == {}
    assert list(tmp_path.glob("invalid-status-value.json.invalid.*.json"))[0].read_text(encoding="utf-8") == original


def test_structured_failure_store_accepts_legacy_and_quarantines_invalid_enums(tmp_path):
    path = tmp_path / "extension_tasks.json"
    legacy = task("legacy", "failed", error="old safe fallback")
    TaskStore(path).save([legacy])
    assert TaskStore(path).load()[0]["id"] == "legacy"

    valid = task(
        "valid", "failed", error="fixed public message", failed_phase="pull",
        error_code="image_prepare_failed", recovery_action="check_image_access_and_regenerate_plan",
    )
    TaskStore(path).save([valid])
    assert TaskStore(path).load()[0]["error_code"] == "image_prepare_failed"

    for index, mutation in enumerate((
        {"failed_phase": "unknown"}, {"error_code": "raw_remote_exception"},
        {"recovery_action": "retry_arbitrary_command"},
    )):
        invalid_path = tmp_path / f"invalid-structured-{index}.json"
        invalid = dict(valid)
        invalid.update(mutation)
        invalid_path.write_text(json.dumps({"schema_version": 1, "tasks": [invalid]}), encoding="utf-8")
        store = TaskStore(invalid_path)
        assert store.load() == []
        assert store.warning
        assert len(list(tmp_path.glob(f"invalid-structured-{index}.json.invalid.*.json"))) == 1


def test_recovery_action_contract_rejects_legacy_failed_and_nonfailed_unknown_actions(tmp_path):
    invalid_records = [
        task("legacy-failed-action", "failed", recovery_action="arbitrary_legacy_retry"),
        *(task(f"unknown-{status}", status, recovery_action="arbitrary_action") for status in (
            "queued", "running", "completed", "cancelled", "interrupted",
        )),
    ]
    for index, record in enumerate(invalid_records):
        path = tmp_path / f"invalid-recovery-{index}.json"
        original = json.dumps({"schema_version": TASK_STORE_SCHEMA_VERSION, "tasks": [record]})
        path.write_text(original, encoding="utf-8")
        store = TaskStore(path)

        assert store.load() == []
        assert store.warning
        quarantined = list(tmp_path.glob(f"invalid-recovery-{index}.json.invalid.*.json"))
        assert len(quarantined) == 1
        assert quarantined[0].read_text(encoding="utf-8") == original


def test_task_store_save_rejects_invalid_recovery_without_overwriting_existing_file(tmp_path):
    path = tmp_path / "extension_tasks.json"
    store = TaskStore(path)
    store.save([task("original")])
    original = path.read_bytes()

    with pytest.raises(ValueError, match="invalid task store record"):
        store.save([task("invalid", "running", recovery_action="unknown_action")])

    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))


def test_task_store_accepts_only_legal_interrupted_and_completed_recovery_actions(tmp_path):
    path = tmp_path / "extension_tasks.json"
    records = [
        task("interrupted", "interrupted", recovery_action="regenerate_plan_and_reprovide_credentials"),
        task("completed-none", "completed", recovery_action=None),
        task("completed-rotate", "completed", recovery_action="reverify_ownership_and_rotate_admin_key"),
    ]
    store = TaskStore(path)
    store.save(records)

    loaded = {record["id"]: record for record in store.load()}
    assert loaded["interrupted"]["recovery_action"] == "regenerate_plan_and_reprovide_credentials"
    assert loaded["completed-none"]["recovery_action"] is None
    assert loaded["completed-rotate"]["recovery_action"] == "reverify_ownership_and_rotate_admin_key"


def test_deployment_failure_registry_contains_only_exact_public_contract():
    assert VALID_FAILURE_COMBINATIONS == {
        ("connect", "host_key_confirmation_required", "confirm_host_key"),
        ("connect", "connection_failed", "check_ssh_connection_and_credentials"),
        ("docker", "docker_unavailable", "fix_docker_access_and_regenerate_plan"),
        ("prepare", "preparation_failed", "inspect_owned_partial_deployment_and_regenerate_plan"),
        ("pull", "image_prepare_failed", "check_image_access_and_regenerate_plan"),
        ("start", "service_start_failed", "inspect_owned_instance_and_regenerate_plan"),
        ("verify", "service_verification_failed", "inspect_owned_instance_and_regenerate_plan"),
        ("verify", "service_verification_failed", "verify_owned_instance_stopped_before_retry"),
        ("verify", "instance_registration_failed", "reconcile_owned_instance_registration"),
    }
    assert all("secret" not in failure.public_message.lower() for failure in FAILURES.values())


def test_task_store_defensively_redacts_all_deployment_secret_sentinels(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    sentinels = (
        "password-sentinel", "private key-sentinel", "passphrase-sentinel", "sudo-sentinel",
        "admin key-sentinel", "Bearer sentinel", "-----BEGIN PRIVATE KEY-----", "key block-sentinel",
    )
    manager.tasks["public"] = task("public", error=" / ".join(sentinels), logs=[{
        "time": "00:00:00", "message": " / ".join(sentinels),
    }], result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "admin_key": "admin-secret",
        "instance": {"id": "instance-a", "managed": True, "password": "ssh-secret"},
    })
    manager._persist()

    text = path.read_text(encoding="utf-8")
    for sentinel in (*sentinels, "admin-secret", "ssh-secret", "private-key-secret", "passphrase-secret", "sudo-secret", "enrollment-secret"):
        assert sentinel not in text
    assert '"admin_key_available": true' in text
    assert "Sensitive task detail redacted." in text


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
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["tasks"][0]["result"]["admin_key_available"] is False

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


def test_delivery_route_is_once_only_and_persists_consumption(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["delivery"] = task("delivery", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["delivery"] = "route-delivery-key"
    manager._persist()
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    first = client.post("/api/extensions/tasks/delivery/delivery")
    assert first.status_code == 200
    assert first.json() == {"admin_key": "route-delivery-key", "shown_once": True}
    assert client.post("/api/extensions/tasks/delivery/delivery").status_code == 404
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["tasks"][0]["result"]["admin_key_available"] is False


def test_cancel_route_persists_state_and_rejects_second_cancel(tmp_path, monkeypatch):
    class Runner:
        def __init__(self):
            self.cancelled = False

        def done(self):
            return self.cancelled

        def cancel(self):
            self.cancelled = True

    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["cancel"] = task("cancel", "running")
    manager.runners["cancel"] = Runner()
    manager._persist()
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    assert client.post("/api/extensions/tasks/cancel/cancel").json() == {"cancelled": True}
    assert manager.get("cancel")["status"] == "cancelled"
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["tasks"][0]["status"] == "cancelled"
    assert client.post("/api/extensions/tasks/cancel/cancel").status_code == 409


def test_concurrent_delivery_consumption_has_one_winner(tmp_path):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks["delivery"] = task("delivery", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["delivery"] = "thread-safe-delivery"
    manager._persist()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: manager.take_delivery("delivery"), range(8)))

    assert results.count("thread-safe-delivery") == 1
    assert results.count(None) == 7
    assert manager.get("delivery")["result"]["admin_key_available"] is False


def test_retention_prunes_delivery_and_runner_orphans(tmp_path):
    class Runner:
        def done(self):
            return False

    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks = {
        f"done-{index:02d}": task(
            f"done-{index:02d}", "completed", f"2026-07-17T00:00:00.{index:03d}Z",
            result={"admin_key_available": True, "instance": {"id": f"instance-{index}", "managed": True}},
        )
        for index in range(51)
    }
    manager.deliveries["done-00"] = "pruned-delivery"
    manager.runners["done-00"] = Runner()
    manager._persist()

    assert "done-00" not in manager.tasks
    assert "done-00" not in manager.deliveries
    assert "done-00" not in manager.runners
    assert manager.take_delivery("done-00") is None


def test_done_runner_reference_is_removed_after_task_finishes(tmp_path, monkeypatch):
    async def fake_run(_task_id, _request, _plan):
        return None

    async def run():
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        monkeypatch.setattr(manager, "_run", fake_run)
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="test-only"), confirmed_plan_id="runner-cleanup",
        )
        deployment_plans.plans["runner-cleanup"] = {
            "id": "runner-cleanup", "project_id": "chatgpt2api", "target_id": "t", "instance_id": request.instance_id,
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "runner-cleanup", "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        runner = manager.runners[task_id]
        await runner
        await asyncio.sleep(0)
        assert task_id not in manager.runners

    asyncio.run(run())


def test_completed_task_cannot_cancel_but_can_take_its_available_delivery(tmp_path, monkeypatch):
    class WaitingRunner:
        def done(self):
            return False

        def cancel(self):
            raise AssertionError("completed task must not cancel its runner")

    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["completed"] = task("completed", "completed", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.runners["completed"] = WaitingRunner()
    manager.deliveries["completed"] = "completed-delivery"
    manager._persist()
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    assert client.post("/api/extensions/tasks/completed/cancel").status_code == 409
    assert manager.get("completed")["status"] == "completed"
    delivery = client.post("/api/extensions/tasks/completed/delivery")
    assert delivery.status_code == 200
    assert delivery.json()["admin_key"] == "completed-delivery"


def test_cancelled_task_never_delivers_even_if_key_was_injected(tmp_path):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks["cancelled"] = task("cancelled", "cancelled", result={
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["cancelled"] = "injected-delivery"
    manager._persist()

    assert manager.take_delivery("cancelled") is None
    assert "cancelled" not in manager.deliveries


def test_main_import_uses_preconfigured_task_store_without_touching_developer_sentinel(tmp_path):
    developer_file = tmp_path / "developer-storage" / "extension_tasks.json"
    developer_file.parent.mkdir()
    developer_file.write_text("developer sentinel", encoding="utf-8")
    isolated_file = tmp_path / "isolated" / "extension_tasks.json"
    env = os.environ.copy()
    env["APP_MODE"] = "dev"
    env["GENBOX_EXTENSION_TASKS_FILE"] = str(isolated_file)
    root = Path(__file__).parents[1]

    result = subprocess.run(
        ["python", "-c", "import main; from extensions.orchestrator import extension_tasks; print(extension_tasks.store.path)"],
        cwd=root, env=env, text=True, capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert str(isolated_file) in result.stdout
    assert developer_file.read_text(encoding="utf-8") == "developer sentinel"
    assert not isolated_file.exists()


def test_task_list_route_is_sorted_and_reports_active_latest_and_404(tmp_path, monkeypatch):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks = {
        "older": task("older", "failed", "2026-07-17T00:00:01.000Z"),
        "active-a": task("active-a", "running", "2026-07-17T00:00:02.000Z"),
        "active-z": task("active-z", "queued", "2026-07-17T00:00:02.000Z"),
        "latest": task("latest", "completed", "2026-07-17T00:00:03.000Z"),
    }
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    response = client.get("/api/extensions/tasks")
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data["tasks"]] == ["latest", "active-z", "active-a", "older"]
    assert data["active_task_id"] == "active-z"
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


def test_cancelled_runner_cannot_overwrite_persisted_cancelled_state(tmp_path, monkeypatch):
    class Result:
        stdout = ""
        exit_status = 0

    blocked = asyncio.Event()
    entered_verify = asyncio.Event()

    class Connection:
        async def run(self, command, check=False, **kwargs):
            result = Result()
            if command == "id -u":
                result.stdout = "0"
            elif command == 'printf %s "$HOME"':
                result.stdout = "/home/ubuntu"
            elif "curl -fsS" in command:
                entered_verify.set()
                await blocked.wait()
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="test-only"), trust_host_key=True,
            instance_id="chatgpt2api-dev", confirmed_plan_id="cancel-race",
        )
        deployment_plans.plans["cancel-race"] = {
            "id": "cancel-race", "project_id": "chatgpt2api", "target_id": "t", "instance_id": "chatgpt2api-dev",
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "genbox-chatgpt2api-chatgpt2api-dev", "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        await entered_verify.wait()
        assert manager.cancel(task_id) is True
        blocked.set()
        await manager.runners[task_id]
        assert manager.get(task_id)["status"] == "cancelled"
        assert manager.get(task_id)["result"] is None
        persisted = json.loads((tmp_path / "extension_tasks.json").read_text(encoding="utf-8"))
        assert persisted["tasks"][0]["status"] == "cancelled"

    asyncio.run(run())


def test_new_deployment_task_initializes_structured_failure_fields(tmp_path, monkeypatch):
    release = asyncio.Event()

    async def fake_run(_task_id, _request, _plan):
        await release.wait()

    async def run():
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        monkeypatch.setattr(manager, "_run", fake_run)
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="test-only"), confirmed_plan_id="structured-init",
        )
        deployment_plans.plans["structured-init"] = {
            "id": "structured-init", "project_id": "chatgpt2api", "target_id": "t", "instance_id": request.instance_id,
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "structured-init", "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        state = manager.get(task_id)
        assert state["failed_phase"] is None
        assert state["error_code"] is None
        assert state["recovery_action"] is None
        release.set()
        await manager.runners[task_id]

    asyncio.run(run())


@pytest.mark.parametrize(("scenario", "expected"), [
    ("host-key", ("connect", "host_key_confirmation_required", "confirm_host_key")),
    ("connect", ("connect", "connection_failed", "check_ssh_connection_and_credentials")),
    ("docker", ("docker", "docker_unavailable", "fix_docker_access_and_regenerate_plan")),
    ("prepare", ("prepare", "preparation_failed", "inspect_owned_partial_deployment_and_regenerate_plan")),
    ("pull", ("pull", "image_prepare_failed", "check_image_access_and_regenerate_plan")),
    ("start", ("start", "service_start_failed", "inspect_owned_instance_and_regenerate_plan")),
    ("verify", ("verify", "service_verification_failed", "inspect_owned_instance_and_regenerate_plan")),
    ("verify-stop", ("verify", "service_verification_failed", "verify_owned_instance_stopped_before_retry")),
    ("registration", ("verify", "instance_registration_failed", "reconcile_owned_instance_registration")),
])
def test_runtime_failures_are_structured_sanitized_and_stage_accurate(tmp_path, monkeypatch, scenario, expected):
    class Result:
        def __init__(self, exit_status=0, stdout=""):
            self.exit_status = exit_status
            self.stdout = stdout

    class Instance:
        def model_dump(self):
            return {"id": "loop3b-instance", "managed": True}

    class Connection:
        def close(self):
            pass

        async def wait_closed(self):
            pass

        async def run(self, command, check=False, **kwargs):
            if command == "id -u":
                return Result(stdout="0")
            if command == 'printf %s "$HOME"':
                return Result(stdout="/home/test")
            if scenario == "docker" and command == "docker version >/dev/null 2>&1":
                raise RuntimeError("password=never-persist host=203.0.113.10 /private/path")
            if scenario == "prepare" and "test ! -e" in command:
                return Result(1)
            if scenario == "pull" and command.startswith("docker pull "):
                return Result(1)
            if scenario == "start" and "compose.yml up -d" in command:
                return Result(1)
            if scenario in {"verify", "verify-stop"} and "curl -fsS" in command:
                return Result(1)
            if scenario == "verify-stop" and "compose.yml down" in command:
                raise RuntimeError("stderr includes credential and host")
            return Result()

    async def fake_connect(_request):
        if scenario == "connect":
            raise RuntimeError("ssh://user:password@203.0.113.10/private/path")
        if scenario == "host-key":
            return None, "SHA256:public-test"
        return Connection(), "SHA256:public-test"

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        if scenario == "registration":
            monkeypatch.setattr("extensions.orchestrator.extensions_store.upsert_instance", lambda _record: (_ for _ in ()).throw(OSError("C:/secret/path")))
        else:
            monkeypatch.setattr("extensions.orchestrator.extensions_store.upsert_instance", lambda _record: Instance())
        manager = ExtensionTaskManager(store_path=tmp_path / f"{scenario}.json")
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="test-only"), trust_host_key=True,
            instance_id="loop3b-instance", confirmed_plan_id=f"loop3b-{scenario}",
        )
        deployment_plans.plans[request.confirmed_plan_id] = {
            "id": request.confirmed_plan_id, "project_id": "chatgpt2api", "target_id": "t",
            "instance_id": request.instance_id, "strategy": "isolated", "deployment_mode": "compose",
            "service_port": 33010, "image": request.image, "compose_project": "genbox-loop3b",
            "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        runner = manager.runners[task_id]
        await runner
        state = manager.get(task_id)
        assert (state["failed_phase"], state["error_code"], state["recovery_action"]) == expected
        assert state["status"] == "failed"
        assert state["phase"] == expected[0]
        assert next(step for step in state["steps"] if step["id"] == expected[0])["status"] == "failed"
        assert state["result"] is None
        assert task_id not in manager.deliveries
        persisted = (tmp_path / f"{scenario}.json").read_text(encoding="utf-8")
        for forbidden in ("never-persist", "203.0.113.10", "/private/path", "C:/secret/path", "stderr includes"):
            assert forbidden not in persisted

    asyncio.run(run())


def test_connection_close_errors_do_not_overwrite_failed_terminal_state(tmp_path, monkeypatch):
    class Connection:
        def close(self):
            raise RuntimeError("close failure with host detail")

        async def wait_closed(self):
            raise RuntimeError("wait failure with path detail")

        async def run(self, command, check=False, **kwargs):
            if command == "id -u":
                return type("R", (), {"stdout": "0", "exit_status": 0})()
            if command == 'printf %s "$HOME"':
                return type("R", (), {"stdout": "/home/test", "exit_status": 0})()
            if "test ! -e" in command:
                return type("R", (), {"stdout": "", "exit_status": 1})()
            return type("R", (), {"stdout": "", "exit_status": 0})()

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", lambda _request: None)
        async def fake_connect(_request):
            return Connection(), "SHA256:public-test"
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        manager = ExtensionTaskManager(store_path=tmp_path / "close-errors.json")
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="test-only"), trust_host_key=True,
            instance_id="loop3b-close", confirmed_plan_id="loop3b-close",
        )
        deployment_plans.plans["loop3b-close"] = {
            "id": "loop3b-close", "project_id": "chatgpt2api", "target_id": "t", "instance_id": "loop3b-close",
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "genbox-loop3b-close", "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "failed"
        assert state["error_code"] == "preparation_failed"

    asyncio.run(run())


def test_extensions_ui_recovery_contract_executes_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
(async () => {
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    style: {}, value: '', textContent: '', innerHTML: '', href: '', readOnly: false, dataset: {},
    classList: { toggle(){}, add(){}, remove(){} },
    querySelector(){ return element('nested'); }, querySelectorAll(){ return []; }, focus(){}, setAttribute(){}, removeAttribute(){},
  });
  return elements.get(id);
}
const timers = [];
const cleared = [];
const calls = [];
let summary = {};
global.window = global;
global.document = { getElementById: element, querySelector(){ return element('query'); }, querySelectorAll(){ return []; }, addEventListener(){}, removeEventListener(){} };
global.i18nText = key => key;
global.getUiLanguage = () => 'en';
global.escHtml = value => String(value || '');
global.extensionNext = () => {};
global.setCheck = () => {};
global.setInterval = (fn, ms) => { const timer = {fn, ms}; timers.push(timer); return timer; };
global.clearInterval = timer => { if (timer) cleared.push(timer); };
const details = {};
global._authFetch = async url => {
  calls.push(url);
  let body = {};
  if (url === '/api/extensions/targets') body = {targets:[]};
  else if (url === '/api/extensions/catalog') body = {categories:[],items:[]};
  else if (url === '/api/extensions/targets/batch') body = {target_ids:[]};
  else if (url === '/api/extensions/tasks') body = summary;
  else if (details[url]) body = details[url];
  return { ok: true, text: async () => JSON.stringify(body) };
};
eval(source);
window.extensionLoadServices = async () => {};
const fullTask = (id, status, result, recovery_action='regenerate_plan_and_reprovide_credentials', failed_phase=null, error_code=null) => ({id,status,phase:failed_phase||'verify',progress:10,steps:[{id:'connect',label:'Connect',status:'success'}],logs:[{time:'00:00:00',message:'Public'}],error:'raw backend detail must not render',host_key:'SHA256:public',result,created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action,failed_phase,error_code});
const active = fullTask('active', 'running', null);
const latest = fullTask('latest', 'completed', {instance:{id:'latest',managed:true},url:'http://latest',api_url:'http://latest/v1',admin_key_available:false});
summary = { active_task_id: 'active', latest_task_id: 'latest', tasks: [latest, active] };
details['/api/extensions/tasks/active'] = active;
await window.loadExtensions();
if (timers.length !== 1 || timers[0].ms !== 800) throw new Error('active polling was not started');
await timers[0].fn();
if (!calls.includes('/api/extensions/tasks/active')) throw new Error('active task was not polled');
if (cleared.includes(timers[0])) throw new Error('active polling callback failed');
details['/api/extensions/tasks/active'] = fullTask('active', 'failed', null, 'check_image_access_and_regenerate_plan', 'pull', 'image_prepare_failed');
await timers[0].fn();
if (!cleared.includes(timers[0])) throw new Error('live failed task did not stop polling');
if (!element('extensionMessage').textContent.includes('extensions.deploy_error_image_prepare_failed') || !element('extensionMessage').textContent.includes('extensions.deploy_recovery_check_image_access_and_regenerate_plan')) throw new Error('live structured failure was not localized');
if (element('extensionMessage').textContent.includes('raw backend detail')) throw new Error('raw failed-task error was rendered');
const timerCount = timers.length;
const interrupted = fullTask('interrupted', 'interrupted', null);
summary = { active_task_id: null, latest_task_id: 'interrupted', tasks: [interrupted] };
await window.loadExtensions();
if (timers.length !== timerCount || !cleared.includes(timers[0]) || !element('extensionMessage').textContent.includes('extensions.recovery_regenerate_plan')) throw new Error('interrupted recovery was not rendered');
const restoredFailed = fullTask('restored-failed', 'failed', null, 'verify_owned_instance_stopped_before_retry', 'verify', 'service_verification_failed');
summary = { active_task_id: null, latest_task_id: 'restored-failed', tasks: [restoredFailed] };
await window.loadExtensions();
if (!element('extensionMessage').textContent.includes('extensions.deploy_recovery_verify_owned_instance_stopped_before_retry')) throw new Error('restored structured failure was not rendered');
const legacyFailed = { ...fullTask('legacy-failed', 'failed', null), failed_phase: undefined, error_code: undefined, recovery_action: undefined };
summary = { active_task_id: null, latest_task_id: 'legacy-failed', tasks: [legacyFailed] };
await window.loadExtensions();
if (!element('extensionMessage').textContent.includes('extensions.deploy_failure_unknown_reason') || !element('extensionMessage').textContent.includes('extensions.deploy_failure_unknown_recovery')) throw new Error('legacy failed task did not use safe fallback');
const unknownFailed = fullTask('unknown-failed', 'failed', null, 'raw_unknown_action', 'raw_unknown_phase', 'raw_unknown_code');
summary = { active_task_id: null, latest_task_id: 'unknown-failed', tasks: [unknownFailed] };
await window.loadExtensions();
if (element('extensionMessage').textContent.includes('raw_unknown')) throw new Error('unknown failure enums were rendered');
calls.length = 0;
const completed = fullTask('completed', 'completed', {instance:{id:'completed',managed:true},url:'http://done',api_url:'http://done/v1',admin_key_available:false,credential_recovery_required:true}, 'reverify_ownership_and_rotate_admin_key');
summary = { active_task_id: null, latest_task_id: 'completed', tasks: [completed] };
await window.loadExtensions();
if (calls.some(url => url.includes('/delivery'))) throw new Error('unavailable delivery was requested');
if (!element('extensionMessage').textContent.includes('extensions.recovery_rotate_admin_key')) throw new Error('credential recovery was not rendered');
if (source.includes('localStorage')) throw new Error('extension task recovery uses localStorage');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
