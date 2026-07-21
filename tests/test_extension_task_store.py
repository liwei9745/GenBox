import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from extensions.models import ExtensionDeployRequest, ExtensionPlanRequest, ExtensionTarget, SSHCredential
from extensions.deployment_failures import FAILURES, VALID_FAILURE_COMBINATIONS
from extensions.orchestrator import (
    DeploymentPlanManager,
    DeploymentResourceConflictError,
    DeploymentResourceReservations,
    ExtensionTaskManager,
)
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


def prepare_deployment_plan(monkeypatch, request: ExtensionDeployRequest):
    from extensions import orchestrator

    target = request.target.model_copy(update={"host_key": "SHA256:public-test"})
    request = request.model_copy(update={"target": target, "trust_host_key": False})
    auth_kind = "private_key" if request.credential.private_key else "password"
    privileges = {
        "auth_kind": auth_kind,
        "elevation_contract": request.credential.elevation,
        "is_root": False,
        "docker_access": True,
        "elevated_docker_access": False,
        "passwordless_sudo": False,
        "password_sudo": False,
        "can_admin": False,
        "can_deploy": True,
        "diagnostic_code": "legacy_discovery",
    }
    discovery = {
        "host_key": target.host_key,
        "environment": {
            "docker_version": "27.0", "compose_version": "2.30",
            "home_dir": f"/home/{target.username}", "listening_ports": [], "disk_free_mb": 5000,
        },
        "privileges": privileges,
        "instances": [],
        "path_conditions": {"install_dir_absent": True},
    }
    plan_manager = DeploymentPlanManager()
    plan = plan_manager.create(ExtensionPlanRequest(
        project_id=request.project_id,
        target=target,
        credential=request.credential,
        instance_id=request.instance_id,
        strategy=request.strategy,
        deployment_mode=request.deployment_mode,
        service_port=target.chatgpt2api_port,
        image=request.image,
        clone_source_id=request.clone_source_id,
        clone_scope=request.clone_scope,
    ), discovery)
    request = request.model_copy(update={"confirmed_plan_id": plan["id"]})
    monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)

    async def fake_discover(_request, *, path_checks=None):
        return copy.deepcopy(discovery)

    monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
    return request, plan_manager, plan


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
        assert task_id not in rebuilt.task_reservations
    assert rebuilt.list_summary()["active_task_id"] is None
    assert rebuilt.resource_reservations.active_count == 0


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
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        runner = manager.runners[task_id]
        await runner
        await asyncio.sleep(0)
        assert task_id not in manager.runners
        assert manager.resource_reservations.active_count == 0

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
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        await entered_verify.wait()
        assert manager.cancel(task_id) is True
        blocked.set()
        await manager.runners[task_id]
        assert manager.get(task_id)["status"] == "cancelled"
        assert manager.get(task_id)["result"] is None
        assert manager.resource_reservations.active_count == 0
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
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        state = manager.get(task_id)
        assert state["failed_phase"] is None
        assert state["error_code"] is None
        assert state["recovery_action"] is None
        release.set()
        await manager.runners[task_id]

    asyncio.run(run())


def test_deploy_route_store_failure_restores_plan_without_task_runner_or_remote_write(tmp_path, monkeypatch):
    target = ExtensionTarget(
        id="t", name="VPS", host="host.example", username="deploy-user",
        host_key="SHA256:public-test", chatgpt2api_port=33010,
    )
    request = ExtensionDeployRequest(
        target=target,
        credential=SSHCredential(password="transaction-test-only"),
        instance_id="transaction-app",
    )
    request, plan_manager, plan = prepare_deployment_plan(monkeypatch, request)
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    runner_started = []

    async def forbidden_run(*_args, **_kwargs):
        runner_started.append(True)

    def fail_save(_tasks):
        raise OSError("injected task store failure")

    monkeypatch.setattr(manager, "_run", forbidden_run)
    monkeypatch.setattr(manager.store, "save", fail_save)
    monkeypatch.setattr(main, "extension_tasks", manager)
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/deploy",
        json=request.model_dump(),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["diagnostic"] == {
        "code": "extension_deploy_preflight_failed",
        "stage": "deployment_preflight",
        "retry_safe": False,
    }
    assert plan["id"] in plan_manager.plans
    assert "_lease_token" not in plan_manager.plans[plan["id"]]
    assert manager.tasks == {}
    assert manager.runners == {}
    assert manager.deliveries == {}
    assert manager.resource_reservations.active_count == 0
    assert runner_started == []
    assert not (tmp_path / "extension_tasks.json").exists()


def test_concurrent_plans_for_same_resource_allow_one_task_and_retain_loser_plan(tmp_path, monkeypatch):
    from extensions import orchestrator

    class Result:
        def __init__(self, exit_status=0, stdout=""):
            self.exit_status = exit_status
            self.stdout = stdout

    class Instance:
        def model_dump(self):
            return {"id": "shared-app", "managed": True}

    first_write_started = asyncio.Event()
    release_first_write = asyncio.Event()
    remote_commands = []
    connection_count = 0

    class Connection:
        async def run(self, command, check=False, **kwargs):
            remote_commands.append(command)
            if command == 'printf %s "$HOME"':
                return Result(stdout="/home/deploy-user")
            if "&& mkdir /home/deploy-user/genbox-apps/chatgpt2api/shared-app" in command:
                first_write_started.set()
                await release_first_write.wait()
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        nonlocal connection_count
        connection_count += 1
        return Connection(), "SHA256:public-test"

    privileges = {
        "auth_kind": "password", "elevation_contract": "none", "is_root": False,
        "docker_access": True, "elevated_docker_access": False,
        "passwordless_sudo": False, "password_sudo": False,
        "can_admin": False, "can_deploy": True, "diagnostic_code": "legacy_discovery",
    }
    discovery = {
        "host_key": "SHA256:public-test",
        "environment": {
            "docker_version": "27.0", "compose_version": "2.30",
            "home_dir": "/home/deploy-user", "listening_ports": [], "disk_free_mb": 5000,
        },
        "privileges": privileges,
        "instances": [],
        "path_conditions": {"install_dir_absent": True},
    }
    target = ExtensionTarget(
        id="shared-target", name="VPS", host="host.example", username="deploy-user",
        host_key="SHA256:public-test", chatgpt2api_port=33010,
    )
    credential = SSHCredential(password="concurrency-test-only")
    plan_manager = DeploymentPlanManager()
    plan_request = ExtensionPlanRequest(
        target=target, credential=credential, instance_id="shared-app", service_port=33010,
    )
    first_plan = plan_manager.create(plan_request, discovery)
    second_plan = plan_manager.create(plan_request, discovery)
    first_request = ExtensionDeployRequest(
        target=target, credential=credential, instance_id="shared-app",
        confirmed_plan_id=first_plan["id"],
    )
    second_request = first_request.model_copy(update={"confirmed_plan_id": second_plan["id"]})
    discovery_gate = asyncio.Event()
    discovery_count = 0

    async def fake_discover(_request, *, path_checks=None):
        nonlocal discovery_count
        discovery_count += 1
        if discovery_count == 2:
            discovery_gate.set()
        await discovery_gate.wait()
        return copy.deepcopy(discovery)

    async def fake_privileges(_connection, _credential):
        return copy.deepcopy(privileges)

    async def run():
        monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        monkeypatch.setattr(orchestrator, "_connect", fake_connect)
        monkeypatch.setattr(orchestrator, "_diagnose_privileges", fake_privileges)
        monkeypatch.setattr(orchestrator.extensions_store, "upsert_instance", lambda _record: Instance())
        manager = ExtensionTaskManager(store_path=tmp_path / "concurrent.json")

        results = await asyncio.gather(
            manager.create(first_request), manager.create(second_request), return_exceptions=True,
        )
        task_ids = [result for result in results if isinstance(result, str)]
        conflicts = [result for result in results if isinstance(result, DeploymentResourceConflictError)]
        assert len(task_ids) == 1
        assert len(conflicts) == 1
        assert str(conflicts[0]) == "deployment_resource_conflict"
        assert all(secret not in str(conflicts[0]) for secret in (
            "host.example", "deploy-user", "/home/deploy-user", "concurrency-test-only",
        ))

        await asyncio.wait_for(first_write_started.wait(), timeout=1)
        assert connection_count == 1
        assert len(manager.tasks) == 1
        assert len(manager.runners) == 1
        assert manager.resource_reservations.active_count == 1
        assert len([command for command in remote_commands if "&& mkdir " in command]) == 1
        persisted = TaskStore(tmp_path / "concurrent.json").load()
        assert len(persisted) == 1

        loser_plan = first_plan if isinstance(results[0], DeploymentResourceConflictError) else second_plan
        assert loser_plan["id"] in plan_manager.plans
        assert "_lease_token" not in plan_manager.plans[loser_plan["id"]]

        runner = manager.runners[task_ids[0]]
        release_first_write.set()
        await runner
        assert manager.resource_reservations.active_count == 0

    asyncio.run(run())


@pytest.mark.parametrize("first,second", [
    (
        {"target_id": "one", "host": "HOST.EXAMPLE.", "host_fingerprint": "SHA256:first", "ssh_port": 22,
         "instance_id": "app-one", "install_dir": "/srv/one", "compose_project": "compose-one", "service_port": 33010},
        {"target_id": "two", "host": "host.example", "host_fingerprint": "SHA256:second", "ssh_port": 22,
         "instance_id": "app-two", "install_dir": "/srv/two", "compose_project": "compose-two", "service_port": 33010},
    ),
    (
        {"target_id": "one", "host": "2001:0db8:0:0:0:0:0:1", "host_fingerprint": "SHA256:first", "ssh_port": 22,
         "instance_id": "app-one", "install_dir": "/srv/one", "compose_project": "compose-one", "service_port": 33010},
        {"target_id": "two", "host": "[2001:db8::1]", "host_fingerprint": "SHA256:second", "ssh_port": 22,
         "instance_id": "app-two", "install_dir": "/srv/two", "compose_project": "compose-two", "service_port": 33010},
    ),
    (
        {"target_id": "one", "host": "host.example", "host_fingerprint": "SHA256:first", "ssh_port": 22,
         "instance_id": "app-one", "install_dir": "/srv/apps/shared", "compose_project": "compose-one", "service_port": 33010},
        {"target_id": "two", "host": "host.example", "host_fingerprint": "SHA256:second", "ssh_port": 22,
         "instance_id": "app-two", "install_dir": "//srv/apps/./shared/", "compose_project": "compose-two", "service_port": 33011},
    ),
    (
        {"target_id": "one", "host": "host.example", "host_fingerprint": "SHA256:first", "ssh_port": 22,
         "instance_id": "app-one", "install_dir": "/srv/one", "compose_project": "Shared-Compose", "service_port": 33010},
        {"target_id": "two", "host": "host.example", "host_fingerprint": "SHA256:second", "ssh_port": 22,
         "instance_id": "app-two", "install_dir": "/srv/two", "compose_project": "shared-compose", "service_port": 33011},
    ),
])
def test_resource_reservation_normalizes_target_path_and_compose_aliases(first, second):
    reservations = DeploymentResourceReservations()
    first_token = reservations.acquire(first)
    with pytest.raises(DeploymentResourceConflictError, match="^deployment_resource_conflict$"):
        reservations.acquire(second)
    reservations.release(first_token)
    second_token = reservations.acquire(second)
    assert reservations.active_count == 1
    reservations.release(second_token)
    assert reservations.active_count == 0


def test_atomic_install_dir_claim_failure_stops_before_config_copy_or_compose(tmp_path, monkeypatch):
    class Result:
        def __init__(self, exit_status=0, stdout=""):
            self.exit_status = exit_status
            self.stdout = stdout

    commands = []

    class Connection:
        async def run(self, command, check=False, **kwargs):
            commands.append(command)
            if command == 'printf %s "$HOME"':
                return Result(stdout="/home/deploy-user")
            if "&& mkdir /home/deploy-user/genbox-apps/chatgpt2api/atomic-app" in command:
                return Result(exit_status=1)
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:public-test"

    async def fake_privileges(_connection, _credential):
        return {
            "auth_kind": "password", "elevation_contract": "none", "is_root": False,
            "docker_access": True, "elevated_docker_access": False,
            "passwordless_sudo": False, "password_sudo": False,
            "can_admin": False, "can_deploy": True, "diagnostic_code": "legacy_discovery",
        }

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        monkeypatch.setattr("extensions.orchestrator._diagnose_privileges", fake_privileges)
        manager = ExtensionTaskManager(store_path=tmp_path / "atomic-claim.json")
        request = ExtensionDeployRequest(
            target=ExtensionTarget(
                id="atomic-target", name="VPS", host="host.example",
                username="deploy-user", chatgpt2api_port=33010,
            ),
            credential=SSHCredential(password="atomic-test-only"),
            instance_id="atomic-app", confirmed_plan_id="atomic-plan",
        )
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        await manager.runners[task_id]

        state = manager.get(task_id)
        assert state["status"] == "failed"
        assert state["error_code"] == "preparation_failed"
        claim_commands = [command for command in commands if "&& mkdir " in command]
        assert claim_commands == [
            "umask 077; mkdir -p /home/deploy-user/genbox-apps/chatgpt2api "
            "&& mkdir /home/deploy-user/genbox-apps/chatgpt2api/atomic-app "
            "&& mkdir /home/deploy-user/genbox-apps/chatgpt2api/atomic-app/data"
        ]
        assert not any(fragment in command for command in commands for fragment in (
            "base64 -d >", "docker pull ", "docker tag ", "cp -a ", "rm -f ",
            "compose.yml up -d", "compose.yml down", ".genbox-instance", "curl -fsS",
        ))
        assert manager.resource_reservations.active_count == 0

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
                return Result(stdout="/home/ubuntu")
            if scenario == "docker" and command == "docker version >/dev/null 2>&1":
                raise RuntimeError("password=never-persist host=203.0.113.10 /private/path")
            if scenario == "prepare" and "&& mkdir " in command:
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
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
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
                return type("R", (), {"stdout": "/home/ubuntu", "exit_status": 0})()
            if "&& mkdir " in command:
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
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "failed"
        assert state["error_code"] == "preparation_failed"

    asyncio.run(run())


def test_deployed_service_vault_controls_mount_and_bind_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
(async () => {
const created = [];
const calls = [];
let opened = '';
function basicNode(tag='div') {
  return {tagName:tag.toUpperCase(),className:'',textContent:'',innerHTML:'',disabled:false,
    classList:{toggle(){},add(){},remove(){}},appendChild(){},insertBefore(){},insertAdjacentHTML(){},
    querySelector(){return basicNode();},querySelectorAll(){return []},setAttribute(){},getAttribute(){return null}};
}
const name = basicNode(); name.textContent = 'managed-one';
const top = basicNode(); top.appended = []; top.appendChild = item => top.appended.push(item);
const reset = basicNode('button');
const actions = basicNode(); actions.inserted = []; actions.querySelector = selector => selector === '.ext-reset-btn' ? reset : null; actions.insertBefore = item => actions.inserted.push(item);
const card = basicNode(); card.querySelector = selector => ({'.ext-service-name':name,'.ext-service-card-top':top,'.ext-service-actions':actions}[selector] || null);
const groupBody = basicNode();
const groupCount = basicNode();
const drawer = basicNode();
drawer.querySelectorAll = selector => selector === '.ext-service-card' ? [card] : [];
drawer.querySelector = selector => selector.includes('.ext-bento-group-count') ? groupCount : (selector.includes('.ext-bento-group-body') ? groupBody : null);
const elements = new Map([['extDrawerList',drawer]]);
function element(id){if(!elements.has(id))elements.set(id,basicNode());return elements.get(id)}
global.window = global;
global.document = {
  getElementById: element,
  querySelector(){return basicNode()}, querySelectorAll(){return []}, addEventListener(){}, removeEventListener(){},
  createElement(tag){const item=basicNode(tag);created.push(item);return item;},
};
global.i18nText = key => key;
global.getUiLanguage = () => 'en';
global.escHtml = value => String(value || '');
global._authFetch = async url => {
  calls.push(url);
  let body = {};
  if(url === '/api/extensions/vault/status') body = {configured:true,unlocked:true,entry_count:1};
  else if(url === '/api/extensions/vault/credentials') body = {credentials:[{instance_id:'managed-one'}]};
  else if(url === '/api/extensions/instances') body = {instances:[{id:'managed-one',project:'chatgpt2api',managed:true,status:'running',service_port:33010,console_url:'http://console.example',api_url:'http://console.example/v1',admin_key:'raw-admin-secret',raw_secret:'raw-secret'}]};
  return {ok:true,text:async()=>JSON.stringify(body)};
};
eval(source);
window.extensionOpenCredential = id => {opened=id};
await window.extensionLoadServices();
const state = created.find(item => item.tagName === 'SPAN');
const button = created.find(item => item.tagName === 'BUTTON');
if(!state || state.textContent !== 'vault.saved' || !top.appended.includes(state)) throw new Error('vault state was not mounted');
if(!button || button.textContent !== 'vault.view' || !actions.inserted.includes(button)) throw new Error('credential button was not mounted');
if(typeof button.onclick !== 'function') throw new Error('credential button was not bound');
button.onclick();
if(opened !== 'managed-one') throw new Error('credential button binding was not callable');
if(drawer.innerHTML.includes('raw-admin-secret') || drawer.innerHTML.includes('raw-secret')) throw new Error('raw secret was rendered in service drawer');
if(source.includes('localStorage')) throw new Error('service drawer uses localStorage');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_completed_delivery_renders_once_and_does_not_refetch_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
(async () => {
const elements = new Map();
function element(id){
  if(!elements.has(id)){
    const classes=new Set(id==='extHandoff'?['hidden']:[]);
    const item={style:{},value:'',textContent:'',innerHTML:'',href:'',readOnly:false,placeholder:'',dataset:{},
      classList:{toggle(name,on){if(on)classes.add(name);else classes.delete(name)},add(name){classes.add(name)},remove(name){classes.delete(name)},contains(name){return classes.has(name)}},
      querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}};
    elements.set(id,item);
  }
  return elements.get(id);
}
let nextStep = 0;
let deliveryCalls = 0;
let sshCalls = 0;
const completed={id:'delivery-task',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',label:'Verify',status:'success'}],logs:[],error:null,host_key:'SHA256:public',created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:null,failed_phase:null,error_code:null,result:{instance:{id:'managed-one',target_id:'saved',managed:true},url:'http://console.example',api_url:'http://console.example/v1',admin_key_available:true}};
const summary={active_task_id:null,latest_task_id:'delivery-task',tasks:[completed]};
global.window=global;
global.document={getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=key=>key;
global.getUiLanguage=()=> 'en';
global.escHtml=value=>String(value||'');
global.extensionNext=step=>{nextStep=step};
global.clearInterval=()=>{};
global.setInterval=()=>({});
global._authFetch=async url=>{
  let body={};
  if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key:'SHA256:test',chatgpt2api_port:33010}]};
  else if(url==='/api/extensions/catalog')body={categories:[],items:[]};
  else if(url==='/api/extensions/targets/batch')body={target_ids:[]};
  else if(url==='/api/extensions/tasks')body=summary;
  else if(url==='/api/extensions/tasks/delivery-task/delivery'){
    deliveryCalls+=1;
    completed.result.admin_key_available=false;
    body={admin_key:'one-time-key',shown_once:true};
  }
  else if(url==='/api/extensions/ssh/test')sshCalls+=1;
  return {ok:true,text:async()=>JSON.stringify(body)};
};
eval(source);
window.extensionLoadServices=async()=>{};
const originalNext=window.extensionNext;
window.extensionNext=step=>{nextStep=step;return originalNext(step)};
await window.loadExtensions();
if(deliveryCalls!==1)throw new Error('delivery endpoint was not requested exactly once');
if(element('extConsoleUrl').value!=='http://console.example' || element('extApiUrl').value!=='http://console.example/v1')throw new Error('delivery URLs were not filled');
if(element('extAdminKey').value!=='one-time-key')throw new Error('one-time key was not filled');
if(element('extOpenConsole').href!=='http://console.example')throw new Error('console link was not filled');
if(element('extHandoff').classList.contains('hidden') || nextStep!==5)throw new Error('unclaimed delivery was not displayed hidden='+element('extHandoff').classList.contains('hidden')+' step='+nextStep);
if(element('extGuidePrimaryBtn').textContent!=='extensions.prepare_local_network')throw new Error('delivery interstitial falsely claimed the private link was complete');
window.extensionPrimaryAction();
if(nextStep!==3)throw new Error('delivery interstitial did not continue to local networking');
await window.loadExtensions();
if(deliveryCalls!==1)throw new Error('delivery endpoint was requested more than once');
if(nextStep!==3)throw new Error('claimed historical deployment did not resume at network selection step='+nextStep);
window.extensionLoadTarget('saved');
element('extPassword').value='test-only-secret';
window.extensionCredentialChanged();
if(element('extSshNextBtn').disabled||element('extSshNextLabel').textContent!=='extensions.return_network_check')throw new Error('network resume action was not enabled after re-entering credentials');
window.extensionSshNext();
if(nextStep!==4||sshCalls!==0)throw new Error('network resume required an unnecessary SSH test or went to the wrong step');
if(source.includes('localStorage'))throw new Error('delivery flow uses localStorage');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


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


def test_ssh_ui_blocks_empty_credentials_and_deduplicates_requests_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
(async () => {
const elements = new Map();
function element(id){
  if(!elements.has(id)){
    const classes=new Set(['extHostKeyConfirm'].includes(id)?['hidden']:[]);
    elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},
      classList:{toggle(name,on){if(on)classes.add(name);else classes.delete(name)},add(name){classes.add(name)},remove(name){classes.delete(name)},contains(name){return classes.has(name)}},
      querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}});
  }
  return elements.get(id);
}
const networkRadio={value:'tailscale',checked:true};
global.window=global;
global.document={
  getElementById:element,
  querySelector(selector){if(selector.includes('extNetwork'))return networkRadio;return element('query')},
  querySelectorAll(){return []},addEventListener(){},removeEventListener(){}
};
global.i18nText=key=>key;
global.getUiLanguage=()=> 'en';
global.escHtml=value=>String(value||'');
global.clearInterval=()=>{};
global.setInterval=()=>({});
let sshCalls=0;
let releaseSsh;
global._authFetch=async (url,options={})=>{
  let body={};
  if(url==='/api/extensions/targets'&&options.method==='POST')body={target:{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key:'SHA256:test',chatgpt2api_port:33010}};
  else if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key:'SHA256:test',chatgpt2api_port:33010}]};
  else if(url==='/api/extensions/catalog')body={categories:[],items:[]};
  else if(url==='/api/extensions/targets/batch')body={target_ids:[]};
  else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:null,tasks:[]};
  else if(url==='/api/extensions/ssh/test'){
    sshCalls+=1;
    return await new Promise(resolve=>{releaseSsh=()=>resolve({ok:true,text:async()=>JSON.stringify({ok:true,host_key:'SHA256:test',privileges:{is_root:true,can_deploy:true}})})});
  }
  return {ok:true,text:async()=>JSON.stringify(body)};
};
eval(source);
window.extensionLoadServices=async()=>{};
await window.loadExtensions();
window.extensionLoadTarget('saved');
if(!element('extTestSshBtn').disabled)throw new Error('SSH test enabled without credentials');
await window.extensionTestSSH(false);
if(sshCalls!==0)throw new Error('empty credentials sent an SSH request');
element('extPassword').value='test-only-secret';
window.extensionCredentialChanged();
if(element('extTestSshBtn').disabled)throw new Error('SSH test stayed disabled after credentials were entered');
const first=window.extensionTestSSH(false);
const second=window.extensionTestSSH(false);
await Promise.resolve();
if(sshCalls!==1)throw new Error('duplicate SSH requests were created');
if(!element('extTestSshBtn').disabled)throw new Error('SSH test button was not locked in flight');
releaseSsh();
await Promise.all([first,second]);
if(sshCalls!==1)throw new Error('duplicate SSH request completed');
if(element('extSshNextBtn').disabled)throw new Error('successful SSH test did not unlock the next step');
if(element('extTestSshBtn').disabled)throw new Error('SSH test button did not unlock after completion');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_fresh_completed_poll_displays_and_claims_delivery_once_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(id==='extHandoff'?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
global.window=global;global.document={getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};
const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};let nextStep=0,deliveryCalls=0;
const running={id:'task-one',status:'running',progress:10,steps:[{id:'connect',status:'running'}],logs:[],result:null};const completed={id:'task-one',status:'completed',progress:100,steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',managed:true},url:'http://console.example',api_url:'http://console.example/v1',admin_key_available:true}};let task=running;
global._authFetch=async url=>{let body={};if(url==='/api/extensions/targets')body={targets:[]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:'task-one',latest_task_id:'task-one',tasks:[running]};else if(url==='/api/extensions/tasks/task-one')body=task;else if(url==='/api/extensions/tasks/task-one/delivery'){deliveryCalls+=1;body={admin_key:'one-time-key'}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};window.extensionNext=step=>{nextStep=step};await window.loadExtensions();if(timers.length!==1)throw new Error('active poller missing');task=completed;await Promise.all([timers[0](),timers[0]()]);if(deliveryCalls!==1)throw new Error('delivery was not claimed exactly once');if(nextStep!==5)throw new Error('fresh delivery was not shown');if(element('extAdminKey').value!=='one-time-key'||element('extHandoff').classList.contains('hidden'))throw new Error('fresh delivery content was not visible');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_delivery_failure_is_not_overwritten_by_deploy_success_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(id==='extHandoff'?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
global.window=global;global.document={getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const completed={id:'task-one',status:'completed',progress:100,steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',managed:true},url:'http://console.example',api_url:'http://console.example/v1',admin_key_available:true}};
global._authFetch=async url=>{let body={};if(url==='/api/extensions/targets')body={targets:[]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:'task-one',tasks:[completed]};else if(url==='/api/extensions/tasks/task-one/delivery')return {ok:false,text:async()=>JSON.stringify({detail:'delivery unavailable'})};return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();const output=element('extensionMessage').textContent;if(!output.includes('extensions.delivery_failed_prefix'))throw new Error('delivery failure was not shown');if(output.includes('extensions.deploy_complete'))throw new Error('deploy success overwrote delivery failure');if(element('extAdminKey').value)throw new Error('failed delivery populated a key');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_inflight_ssh_result_cannot_verify_changed_credentials_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
(async () => {
const elements=new Map();
function element(id){if(!elements.has(id)){const classes=new Set();elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true};
global.window=global;
global.document={getElementById:element,querySelector(selector){if(selector.includes('extNetwork'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=key=>key;global.getUiLanguage=()=> 'en';global.escHtml=value=>String(value||'');global.clearInterval=()=>{};global.setInterval=()=>({});
let releaseSsh,targetSaves=0;
global._authFetch=async (url,options={})=>{
  let body={};
  if(url==='/api/extensions/targets'&&options.method==='POST'){targetSaves+=1;body={target:{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key:'SHA256:old',chatgpt2api_port:33010}}}
  else if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key:'SHA256:old',chatgpt2api_port:33010}]};
  else if(url==='/api/extensions/catalog')body={categories:[],items:[]};
  else if(url==='/api/extensions/targets/batch')body={target_ids:[]};
  else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:null,tasks:[]};
  else if(url==='/api/extensions/ssh/test')return await new Promise(resolve=>{releaseSsh=()=>resolve({ok:true,text:async()=>JSON.stringify({ok:true,host_key:'SHA256:new',privileges:{is_root:true,can_deploy:true}})})});
  return {ok:true,text:async()=>JSON.stringify(body)};
};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');
element('extPassword').value='first-secret';window.extensionCredentialChanged();
const pending=window.extensionTestSSH(false);await Promise.resolve();
element('extPassword').value='changed-secret';window.extensionCredentialChanged();
releaseSsh();await pending;
if(!element('extSshNextBtn').disabled)throw new Error('stale SSH response unlocked the next step');
if(targetSaves!==0)throw new Error('stale SSH response persisted a new host key');
if(element('extTestSshBtn').disabled)throw new Error('SSH test button stayed locked after stale request completed');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_deployed_target_confirms_host_key_without_ssh_auth_loop_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey','extHandoff'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true,disabled:false,classList:{toggle(){}},focus(){}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const fingerprint='SHA256:AAAAAAAAAAAAAAAAAAAA';let target={id:'saved',name:'Saved',host:'safe.example',port:22,username:'ubuntu',host_key:'',chatgpt2api_port:33010};let probeCalls=0,confirmCalls=0,sshCalls=0;
const completed={id:'done',status:'completed',progress:100,host_key:'',steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',target_id:'saved',managed:true},url:'http://service.example',api_url:'http://service.example/v1',admin_key_available:false}};
global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:'done',tasks:[completed]};else if(url==='/api/extensions/network/local/tailscale/status')body={installed:true,online:true,serve:true,serve_port:8893,app_port:8892};else if(url==='/api/extensions/ssh/host-key/probe'){probeCalls+=1;const sent=JSON.parse(options.body);if(Object.keys(sent).join(',')!=='target_id')throw new Error('probe sent credential data');body={target_id:'saved',fingerprint};}else if(url==='/api/extensions/ssh/host-key/confirm'){confirmCalls+=1;const sent=JSON.parse(options.body);if(sent.target_id!=='saved'||sent.fingerprint!==fingerprint||Object.keys(sent).length!==2)throw new Error('confirm payload was not minimal');target={...target,host_key:fingerprint};body={target};}else if(url==='/api/extensions/ssh/test'){sshCalls+=1;return {ok:false,text:async()=>JSON.stringify({detail:'Permission denied for user ubuntu on host safe.example 192.0.2.77'})};}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();const visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();window.extensionSshNext();if(visited.at(-1)!==4)throw new Error('deployed target did not return to step 4');if(element('extNetworkHostKey').classList.contains('hidden'))throw new Error('missing host key did not stay in network step');if(!element('extNetworkConnectBtn').disabled)throw new Error('network connected before host key confirmation');await window.extensionProbeHostKey();if(visited.at(-1)!==4)throw new Error('probe left step 4');if(element('extNetworkHostKeyValue').textContent!==fingerprint)throw new Error('fingerprint was not shown for review');await window.extensionConfirmHostKey();if(visited.at(-1)!==4)throw new Error('confirm left step 4 for a deployed target');if(probeCalls!==1||confirmCalls!==1)throw new Error('host key flow did not run exactly once');if(element('extNetworkConnectBtn').disabled)throw new Error('confirmed host key did not unlock network check');await window.extensionTestSSH(false);if(sshCalls!==1)throw new Error('optional SSH diagnostic was not called');const output=element('extensionMessage').textContent;if(output.includes('Permission denied')||output.includes('ubuntu')||output.includes('safe.example')||output.includes('192.0.2.77'))throw new Error('raw SSH error reached the UI');if(element('extNetworkConnectBtn').disabled)throw new Error('SSH diagnostic failure erased confirmed host key');await window.loadExtensions();window.extensionLoadTarget('saved');if(!element('extNetworkHostKey').classList.contains('hidden')||element('extNetworkConnectBtn').disabled)throw new Error('reload did not restore persisted host key');if(probeCalls!==1)throw new Error('reload unnecessarily reprobed the host key');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_stale_host_key_probe_cannot_pollute_a_new_target_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true,classList:{toggle(){}},focus(){}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});let releaseProbe;
const targets=[{id:'one',name:'One',host:'one.example',port:22,username:'ubuntu',host_key:'',chatgpt2api_port:3000},{id:'two',name:'Two',host:'two.example',port:22,username:'ubuntu',host_key:'',chatgpt2api_port:3000}];let probeCalls=0;global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/probe'){probeCalls+=1;if(probeCalls===1)return await new Promise(resolve=>{releaseProbe=()=>resolve({ok:true,text:async()=>JSON.stringify({target_id:'one',fingerprint:'SHA256:AAAAAAAAAAAAAAAAAAAA'})})});body={target_id:'two',fingerprint:'SHA256:BBBBBBBBBBBBBBBBBBBB'};}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('one');const pending=window.extensionProbeHostKey();await Promise.resolve();window.extensionLoadTarget('two');if(element('extNetworkHostKeyProbeBtn').disabled)throw new Error('new target probe stayed locked after target switch');const second=window.extensionProbeHostKey();releaseProbe();await Promise.all([pending,second]);if(element('extNetworkHostKeyValue').textContent!=='SHA256:BBBBBBBBBBBBBBBBBBBB')throw new Error('new target fingerprint was not retained');if(element('extNetworkHostKeyConfirmBtn').classList.contains('hidden'))throw new Error('new target fingerprint was not confirmable');if(probeCalls!==2)throw new Error('new target could not start its own probe');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_new_target_host_key_setup_rejects_malformed_responses_and_returns_to_step_one_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true,classList:{toggle(){}},focus(){}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
let target={id:'saved',name:'Saved',host:'safe.example',port:22,username:'ubuntu',host_key:'',chatgpt2api_port:3000};const responses=['','SHA256:short','SHA256:bad value','SHA256:AAAAAAAAAAAAAAAAAAAA'];let probeCalls=0,confirmCalls=0;global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/probe')body={target_id:'saved',fingerprint:responses[probeCalls++]};else if(url==='/api/extensions/ssh/host-key/confirm'){confirmCalls+=1;target={...target,host_key:'SHA256:AAAAAAAAAAAAAAAAAAAA'};body={target};}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');if(element('extStepHostKeyBtn').disabled)throw new Error('new target host-key setup was not available');if(element('extTestSshLabel').textContent!=='extensions.ssh_deploy_diagnostic')throw new Error('new deployment SSH action had optional wording');const visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};for(let i=0;i<3;i++){await window.extensionStartHostKeySetup();if(!element('extNetworkHostKeyConfirmBtn').classList.contains('hidden'))throw new Error('malformed fingerprint became confirmable');if(!element('extNetworkConnectBtn').disabled)throw new Error('malformed fingerprint unlocked connection');if(!element('extensionMessage').textContent.includes('extensions.host_key_invalid_response'))throw new Error('malformed fingerprint did not show safe validation error');}await window.extensionStartHostKeySetup();if(element('extNetworkHostKeyValue').textContent!=='SHA256:AAAAAAAAAAAAAAAAAAAA')throw new Error('valid fingerprint was not displayed');await window.extensionConfirmHostKey();if(confirmCalls!==1)throw new Error('valid fingerprint was not confirmed exactly once');if(visited.at(-1)!==1)throw new Error('new deployment did not return to step 1 after host-key confirmation');if(element('extTestSshBtn').disabled===false)throw new Error('SSH test unlocked without session credentials');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_restored_deployment_is_bound_to_its_original_target_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey','extHandoff'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true,classList:{toggle(){}},focus(){}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';const targets=[{id:'one',name:'One',host:'one.example',port:22,username:'ubuntu',host_key:key,chatgpt2api_port:3000},{id:'two',name:'Two',host:'two.example',port:22,username:'ubuntu',host_key:key,chatgpt2api_port:3000}];const completed={id:'done',status:'completed',progress:100,host_key:key,steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',target_id:'one',managed:true},url:'http://service.example',api_url:'http://service.example/v1',admin_key_available:false}};let remoteCalls=0;global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={latest_task_id:'done',tasks:[completed]};else if(url.includes('/api/extensions/ssh/')||url==='/api/extensions/network/connect'){remoteCalls+=1;body={};}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();if(element('extTargetSelect').value!=='one')throw new Error('restore did not select the deployed VPS');window.extensionLoadTarget('two');element('extPassword').value='session-only';window.extensionCredentialChanged();const visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};window.extensionSshNext();await window.extensionProbeHostKey();await window.extensionConnectNetwork();if(visited.includes(4))throw new Error('wrong target entered network step');if(remoteCalls!==0)throw new Error('wrong target triggered a remote operation');if(!element('extensionMessage').textContent.includes('extensions.deployment_target_mismatch'))throw new Error('wrong target did not show recovery guidance');if(!element('extNetworkConnectBtn').disabled)throw new Error('wrong target left network action enabled');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_network_connect_is_single_flight_until_terminal_task_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkRecovery'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};
const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};let connectCalls=0,releaseConnect;
global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:'SHA256:test',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/connect'){connectCalls+=1;return await new Promise(resolve=>{releaseConnect=()=>resolve({ok:true,text:async()=>JSON.stringify({task_id:'network-one'})})})}else if(url==='/api/extensions/network/tasks/network-one')body={status:'failed',progress:20,failed_phase:'remote_network_detect',recovery_action:'confirm VPS Tailscale is online',steps:[{id:'remote_network_detect',status:'failed'}],logs:[],error:'safe failure',diagnostics:{exit_status:0,stdout_present:true,json_parsed:true,json_type:'object',backend_state:'needs_login',cgnat_candidate_count:0}};return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extRemoteNetworkMode').value='existing';window.extensionNetworkModeChanged('existing');element('extPassword').value='test-only-secret';window.extensionCredentialChanged();
const first=window.extensionConnectNetwork();const second=window.extensionConnectNetwork();await Promise.resolve();if(connectCalls!==1)throw new Error('duplicate network connect requests were created');if(!element('extNetworkConnectBtn').disabled)throw new Error('network button was not locked');releaseConnect();await Promise.all([first,second]);if(!element('extNetworkConnectBtn').disabled)throw new Error('network button unlocked before terminal task');if(timers.length!==1)throw new Error('network poller was not created exactly once');await timers[0]();if(element('extNetworkConnectBtn').disabled)throw new Error('network button did not unlock after failure');if(element('extPassword').value!=='test-only-secret')throw new Error('session credential was discarded before recovery');if(!element('extNetworkDiagnosticDetail').textContent.includes('extensions.network_diag_needs_login'))throw new Error('safe diagnostic was not translated into one concrete recovery fact');if(element('extensionMessage').textContent.includes('safe failure'))throw new Error('raw task error reached the novice status message');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_auto_network_auth_key_is_required_retained_on_post_failure_and_cleared_after_task_creation_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkRecovery','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){this.focused=true},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};
let postCalls=0,lastBody=null;global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:'SHA256:test',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/connect'){postCalls+=1;lastBody=JSON.parse(options.body);if(postCalls===2)return {ok:false,status:503,text:async()=>JSON.stringify({detail:'temporary'})};body={task_id:postCalls===1?'network-inspect':'network-auto'}}else if(url==='/api/extensions/network/tasks/network-inspect')body={status:'needs_action',phase:'remote_enroll',progress:44,recovery_code:'TAILSCALE_AUTH_KEY_REQUIRED',recovery_action:'need key',next_action:{type:'provide_secret',label_key:'extensions.enter_auth_key',handler:'network_retry'},steps:[{id:'remote_enroll',status:'needs_action'}],logs:[],diagnostics:{}};return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extRemoteNetworkMode').value='auto';window.extensionNetworkModeChanged('auto');element('extPassword').value='ssh-session';window.extensionCredentialChanged();window.extensionNext(4);
await window.extensionConnectNetwork();if(postCalls!==1)throw new Error('empty Auth Key did not start read-only detection');if(lastBody.enrollment_token!=='')throw new Error('read-only detection submitted a secret');if(timers.length!==1)throw new Error('inspection task did not start polling');await timers[0]();if(element('extGuidePrimaryBtn').textContent!=='extensions.enter_auth_key')throw new Error('needs_action did not produce one Auth Key CTA');window.extensionPrimaryAction();if(!element('extNetworkToken').focused)throw new Error('Auth Key CTA did not focus the secret input');
element('extNetworkToken').value='one-time-auth-key';await window.extensionConnectNetwork();if(postCalls!==2)throw new Error('first Auth Key POST did not run');if(element('extNetworkToken').value!=='one-time-auth-key')throw new Error('POST failure discarded Auth Key');
await window.extensionConnectNetwork();if(postCalls!==3)throw new Error('second Auth Key POST did not run');if(element('extNetworkToken').value!=='')throw new Error('created task did not clear Auth Key');if(lastBody.operation_mode!=='auto'||lastBody.enrollment_token!=='one-time-auth-key')throw new Error('auto request did not carry the one-time key exactly once');if(element('extPassword').value!=='ssh-session')throw new Error('task creation cleared SSH credentials before terminal completion');if(timers.length!==2)throw new Error('created task did not start one new poller');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_stale_network_post_and_poll_cannot_clear_new_credentials_or_show_success_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkRecovery','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};
let connectCalls=0,releasePost,releasePoll;global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:'SHA256:test',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/connect'){connectCalls+=1;if(connectCalls===1)return await new Promise(resolve=>{releasePost=()=>resolve({ok:true,text:async()=>JSON.stringify({task_id:'stale-post'})})});body={task_id:'stale-poll'}}else if(url==='/api/extensions/network/tasks/stale-poll')return await new Promise(resolve=>{releasePoll=()=>resolve({ok:true,text:async()=>JSON.stringify({status:'completed',progress:100,steps:[{id:'http_probe',status:'success'}],logs:[],result:{local_address:'100.64.0.1',remote_address:'100.64.0.2',peer_reachable:true,genbox_reachable:true,genbox_url:'http://100.64.0.1:8893'}})})});return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extRemoteNetworkMode').value='existing';window.extensionNetworkModeChanged('existing');element('extPassword').value='old-post';window.extensionCredentialChanged();window.extensionNext(4);
const pendingPost=window.extensionConnectNetwork();await Promise.resolve();element('extPassword').value='new-post';releasePost();await pendingPost;if(timers.length!==0)throw new Error('stale POST created a poller');if(element('extPassword').value!=='new-post')throw new Error('stale POST cleared new credentials');
element('extPassword').value='old-poll';await window.extensionConnectNetwork();if(timers.length!==1)throw new Error('second task did not start polling');const pendingPoll=timers[0]();await Promise.resolve();element('extPassword').value='new-poll';releasePoll();await pendingPoll;if(element('extPassword').value!=='new-poll')throw new Error('stale poll cleared new credentials');if(!element('extSuccessBanner').classList.contains('hidden'))throw new Error('stale poll displayed success');if(!element('extensionMessage').textContent.includes('extensions.network_context_changed'))throw new Error('stale response did not explain why it was ignored');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_structured_ssh_diagnostic_is_rendered_without_sensitive_fields_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set();elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:'SHA256:test',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')return {ok:false,text:async()=>JSON.stringify({detail:{error:'安全认证提示',diagnostic:{code:'ssh_auth_rejected',stage:'password_requested',password_requested:true,retry_safe:false},host:'must-not-render',user:'must-not-render',raw:'must-not-render'}})};return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='test-only-secret';window.extensionCredentialChanged();await window.extensionTestSSH(false);const output=element('extensionMessage').textContent;if(!output.includes('安全认证提示')||!output.includes('extensions.ssh_diag_password_requested'))throw new Error('structured diagnostic stage was not rendered');if(output.includes('must-not-render')||output.includes('test-only-secret')||output.includes('vps.example')||output.includes('root'))throw new Error('sensitive diagnostic fields were rendered');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_novice_step_two_executes_discovery_plan_deploy_and_routes_to_network_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();
function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview','extHandoff','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){this.focused=true},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const radios={
  network:{value:'tailscale',checked:true,classList:{toggle(){}}},intent:{value:'development',checked:true},strategy:{value:'isolated',checked:true},mode:{value:'compose',checked:true},scope:{value:'empty',checked:true},delivery:{value:'once',checked:true}
};
global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return radios.network;if(s.includes('extIntent')&&s.includes(':checked'))return radios.intent;if(s.includes('extStrategy')&&s.includes('[value="isolated"]'))return radios.strategy;if(s.includes('extStrategy')&&s.includes(':checked'))return radios.strategy;if(s.includes('extDeployMode'))return radios.mode;if(s.includes('extCloneScope'))return radios.scope;if(s.includes('extCredentialDelivery'))return radios.delivery;if(s.includes('.extension-pane'))return element('heading');return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};
const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';
const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:key,chatgpt2api_port:33010};
const discovery={environment:{os:'Ubuntu',cpu:2,memory_mb:2048,disk_free_mb:4096,listening_ports:[],docker_version:'Docker',compose_version:'Compose',python_version:'3.12'},instances:[],deployment_modes:[{id:'compose',name:'Compose',summary:'Recommended',recommended:true,available:true}]};
const plan={id:'plan-one',instance_id:'chatgpt2api-dev',service_port:33010,image:'image:test',strategy:'isolated',deployment_mode:'compose',clone_source_id:'',clone_scope:'empty',operations:['prepare'],safety:['isolated'],source_baseline:{}};
let deployCalls=0,releaseDeploy;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/discover')body=discovery;else if(url==='/api/extensions/deploy/plan')body={plan,discovery};else if(url==='/api/extensions/deploy'){deployCalls+=1;return await new Promise(resolve=>{releaseDeploy=()=>resolve({ok:true,text:async()=>JSON.stringify({task_id:'deploy-one'})})})}else if(url==='/api/extensions/tasks/deploy-one')body={status:'completed',progress:100,host_key:key,steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',target_id:'saved',managed:true},url:'http://service.example',api_url:'http://service.example/v1',admin_key_available:false}};return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);window.extensionNext(2);
if(element('extGuidePrimaryBtn').textContent!=='extensions.discover')throw new Error('step 2 did not begin with discovery');
await window.extensionPrimaryAction();if(element('extGuidePrimaryBtn').textContent!=='extensions.create_plan')throw new Error('discovery did not advance to plan creation');
await window.extensionPrimaryAction();if(element('extGuidePrimaryBtn').textContent!=='extensions.confirm_deploy')throw new Error('plan did not advance to explicit deployment confirmation');
const first=window.extensionPrimaryAction();const second=window.extensionPrimaryAction();for(let i=0;i<8&&!releaseDeploy;i+=1)await Promise.resolve();if(deployCalls!==1)throw new Error('double click created duplicate deployment requests');if(!element('extGuidePrimaryBtn').disabled||element('extGuidePrimaryBtn').textContent!=='status.processing')throw new Error('deployment in flight was not locked');releaseDeploy();await Promise.all([first,second]);if(timers.length!==1)throw new Error('deployment poller was not created once');
let visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};await timers[0]();if(visited.includes(5)||visited.at(-1)!==3)throw new Error('deployment without one-time delivery falsely skipped to completion');if(!element('extSuccessBanner').classList.contains('hidden'))throw new Error('success banner appeared before private-network verification');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_lost_deploy_response_reconciles_one_accepted_task_without_retry_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();
function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview','extHandoff','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const radios={network:{value:'tailscale',checked:true,classList:{toggle(){}}},intent:{value:'development',checked:true},strategy:{value:'isolated',checked:true},mode:{value:'compose',checked:true},scope:{value:'empty',checked:true},delivery:{value:'once',checked:true}};
global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return radios.network;if(s.includes('extIntent')&&s.includes(':checked'))return radios.intent;if(s.includes('extStrategy')&&s.includes('[value="isolated"]'))return radios.strategy;if(s.includes('extStrategy')&&s.includes(':checked'))return radios.strategy;if(s.includes('extDeployMode'))return radios.mode;if(s.includes('extCloneScope'))return radios.scope;if(s.includes('extCredentialDelivery'))return radios.delivery;if(s.includes('.extension-pane'))return element('heading');return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};global.clearInterval=()=>{};
const key='SHA256:AAAAAAAAAAAAAAAAAAAA',target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:key,chatgpt2api_port:33010};
const discovery={environment:{os:'Ubuntu',cpu:2,memory_mb:2048,disk_free_mb:4096,listening_ports:[],docker_version:'Docker',compose_version:'Compose',python_version:'3.12'},instances:[],deployment_modes:[{id:'compose',name:'Compose',summary:'Recommended',recommended:true,available:true}]};
const plan={id:'plan-one',instance_id:'chatgpt2api-dev',service_port:33010,image:'image:test',strategy:'isolated',deployment_mode:'compose',clone_source_id:'',clone_scope:'empty',operations:['prepare'],safety:['isolated'],source_baseline:{}};
const accepted={id:'accepted-one',status:'running',phase:'connect',progress:5,steps:[{id:'connect',status:'running'}],logs:[],result:null};let serverTasks=[],taskVisible=false,deployCalls=0,taskListReads=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks'){taskListReads+=1;const visible=taskVisible?serverTasks:[];body={active_task_id:visible.length?visible[0].id:null,latest_task_id:visible.length?visible[0].id:null,tasks:visible}}else if(url==='/api/extensions/ssh/test')body={ok:true,host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/discover')body=discovery;else if(url==='/api/extensions/deploy/plan')body={plan,discovery};else if(url==='/api/extensions/deploy'){deployCalls+=1;serverTasks=[accepted];throw new TypeError('response stream lost')}else if(url==='/api/extensions/tasks/accepted-one')body=accepted;return {ok:true,status:200,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);window.extensionNext(2);await window.extensionDiscover();await window.extensionCreatePlan();
await window.extensionStartDeploy();await window.extensionStartDeploy();
if(deployCalls!==1||serverTasks.length!==1)throw new Error('lost response created a duplicate deployment task');
if(taskListReads<3)throw new Error('lost response did not reconcile the task list');
if(timers.length!==1)throw new Error('lost response did not keep reconciling while task visibility was unknown');
if(element('extGuideFound').textContent==='extensions.guide_step2_confirmation_failed')throw new Error('ambiguous response falsely claimed plan confirmation blocked the task');
if(element('extensionMessage').textContent.includes('extensions.deploy_confirmation_safe_notice'))throw new Error('ambiguous response falsely claimed no task or VPS change');
taskVisible=true;await timers[0]();
if(timers.length!==2)throw new Error('newly visible accepted task did not transition from reconciliation to task polling');
await timers[1]();
})().catch(error=>{console.error(error.stack||error);process.exit(1)});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_identity_plan_confirmation_returns_to_authoritative_target_and_credentials_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();
function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview','extHandoff','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const radios={network:{value:'tailscale',checked:true,classList:{toggle(){}}},intent:{value:'development',checked:true},strategy:{value:'isolated',checked:true},mode:{value:'compose',checked:true},scope:{value:'empty',checked:true},delivery:{value:'once',checked:true}};
global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return radios.network;if(s.includes('extIntent')&&s.includes(':checked'))return radios.intent;if(s.includes('extStrategy')&&s.includes('[value="isolated"]'))return radios.strategy;if(s.includes('extStrategy')&&s.includes(':checked'))return radios.strategy;if(s.includes('extDeployMode'))return radios.mode;if(s.includes('extCloneScope'))return radios.scope;if(s.includes('extCredentialDelivery'))return radios.delivery;if(s.includes('.extension-pane'))return element('heading');return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.setInterval=()=>({});global.clearInterval=()=>{};
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';let target={id:'saved',name:'Saved',host:'authoritative.example',port:2222,username:'deploy',host_key:key,chatgpt2api_port:33010};
const discovery={environment:{os:'Ubuntu',cpu:2,memory_mb:2048,disk_free_mb:4096,listening_ports:[],docker_version:'Docker',compose_version:'Compose',python_version:'3.12'},instances:[],deployment_modes:[{id:'compose',name:'Compose',summary:'Recommended',recommended:true,available:true}]};
const plan={id:'plan-one',instance_id:'chatgpt2api-dev',service_port:33010,image:'image:test',strategy:'isolated',deployment_mode:'compose',clone_source_id:'',clone_scope:'empty',operations:['prepare'],safety:['isolated'],source_baseline:{}};let targetReads=0,deployCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets'){targetReads+=1;body={targets:[target]}}else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:null,tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/discover')body=discovery;else if(url==='/api/extensions/deploy/plan')body={plan,discovery};else if(url==='/api/extensions/deploy'){deployCalls+=1;target={...target,host:'reloaded-authoritative.example',port:2200,username:'reloaded-user'};return {ok:false,status:409,text:async()=>JSON.stringify({detail:{error:'identity changed',diagnostic:{code:'deployment_plan_identity_mismatch',stage:'plan_confirmation',retry_safe:false}}})}}return {ok:true,status:200,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};let visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);window.extensionNext(2);await window.extensionDiscover();await window.extensionCreatePlan();await window.extensionStartDeploy();
if(deployCalls!==1)throw new Error('identity mismatch did not stop after one deploy request');
if(targetReads<2)throw new Error('identity mismatch did not reload the authoritative saved target');
if(element('extHost').value!=='reloaded-authoritative.example'||element('extPort').value!==2200||element('extUsername').value!=='reloaded-user')throw new Error('identity mismatch retained stale target fields');
if(visited.at(-1)!==1)throw new Error('identity mismatch did not return to VPS identity step');
if(element('extPassword').value||!element('extSshNextBtn').disabled)throw new Error('identity mismatch retained credentials or SSH verification');
if(element('extGuidePrimaryBtn').textContent==='extensions.regenerate_safe_plan')throw new Error('identity mismatch exposed the step-2 regenerate loop');
if(!element('extensionMessage').textContent.includes('extensions.deploy_identity_reconfirm_notice'))throw new Error('identity mismatch did not explain target and credential reconfirmation');
})().catch(error=>{console.error(error.stack||error);process.exit(1)});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_plan_creation_preserves_bound_clone_scope_for_regeneration_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();
function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const groups={};
function radio(name,value,checked=false){const input={name,value,_checked:false,dataset:{},classList:{toggle(){}}};Object.defineProperty(input,'checked',{get(){return this._checked},set(on){this._checked=!!on;if(on)(groups[name]||[]).forEach(other=>{if(other!==this)other._checked=false})}});(groups[name]||(groups[name]=[])).push(input);input.checked=checked;return input}
const intent=radio('extIntent','development',true),strategy=radio('extStrategy','isolated',true),mode=radio('extDeployMode','compose',true),empty=radio('extCloneScope','empty',true),working=radio('extCloneScope','working-copy'),delivery=radio('extCredentialDelivery','once',true),network=radio('extNetwork','tailscale',true);
global.window=global;global.document={getElementById:element,querySelector(s){const match=s.match(/input\[name="([^"]+)"\](?:\[value="([^"]+)"\])?/);if(match){const choices=groups[match[1]]||[];if(match[2]!==undefined)return choices.find(input=>input.value===match[2])||null;if(s.includes(':checked'))return choices.find(input=>input.checked)||null;return choices[0]||null}if(s.includes('.extension-pane'))return element('heading');return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:key,chatgpt2api_port:33010};
const discovery={environment:{os:'Ubuntu',cpu:2,memory_mb:2048,disk_free_mb:4096,listening_ports:[],docker_version:'Docker',compose_version:'Compose',python_version:'3.12'},instances:[],deployment_modes:[{id:'compose',name:'Compose',summary:'Recommended',recommended:true,available:true}]};
const planBodies=[];
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/deploy/plan'){const request=JSON.parse(options.body);planBodies.push(request);body={discovery,plan:{id:'plan-'+planBodies.length,instance_id:request.instance_id,service_port:request.service_port,image:request.image,strategy:request.strategy,deployment_mode:request.deployment_mode,clone_source_id:request.clone_source_id,clone_scope:request.clone_scope,operations:['prepare'],safety:['isolated'],source_baseline:{}}}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);element('extInstanceId').value='chatgpt2api-dev';element('extServicePort').value='33010';element('extImage').value='image:test';element('extCloneSource').value='';
window.extensionSelectIntent(intent);empty.checked=true;await window.extensionCreatePlan();if(planBodies[0].clone_scope!=='empty')throw new Error('first plan did not submit the explicit empty scope');if(!empty.checked||working.checked)throw new Error('successful empty plan was rendered as working-copy');if(!strategy.checked||element('extCloneSource').value!==''||element('extImage').value!=='image:test')throw new Error('plan rendering changed strategy, source, or image semantics');
await window.extensionCreatePlan();if(planBodies[1].clone_scope!=='empty')throw new Error('regenerated plan did not preserve empty scope');if(!empty.checked||working.checked)throw new Error('regenerated empty plan changed the visible scope');
window.extensionSelectIntent(intent);if(!working.checked||empty.checked)throw new Error('explicit development intent no longer defaults to working-copy');await window.extensionCreatePlan();if(planBodies[2].clone_scope!=='working-copy'||!working.checked||empty.checked)throw new Error('working-copy plan behavior changed');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_stale_plan_responses_cannot_restore_a_plan_or_enable_deploy_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview'].includes(id)?['hidden']:[]);elements.set(id,{id,style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const groups={};function radio(name,value,checked=false){const input={name,value,_checked:false,dataset:{}};Object.defineProperty(input,'checked',{get(){return this._checked},set(on){this._checked=!!on;if(on)(groups[name]||[]).forEach(other=>{if(other!==this)other._checked=false})}});(groups[name]||(groups[name]=[])).push(input);input.checked=checked;return input}
radio('extIntent','development',true);radio('extStrategy','isolated',true);radio('extDeployMode','compose',true);radio('extCloneScope','empty',true);radio('extCloneScope','working-copy');radio('extCredentialDelivery','once',true);radio('extNetwork','tailscale',true);
const listeners={};global.window=global;global.document={getElementById:element,querySelector(s){const match=s.match(/input\[name="([^"]+)"\](?:\[value="([^"]+)"\])?/);if(match){const choices=groups[match[1]]||[];if(match[2]!==undefined)return choices.find(input=>input.value===match[2])||null;if(s.includes(':checked'))return choices.find(input=>input.checked)||null;return choices[0]||null}if(s.includes('.extension-pane'))return element('heading');return element('query')},querySelectorAll(){return []},addEventListener(type,fn){(listeners[type]||(listeners[type]=[])).push(fn)},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const key='SHA256:AAAAAAAAAAAAAAAAAAAA',target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:key,chatgpt2api_port:33010},discovery={environment:{},instances:[],deployment_modes:[{id:'compose',name:'Compose',summary:'Recommended',recommended:true,available:true}]};const releases=[];let deployCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/deploy/plan'){const request=JSON.parse(options.body);return await new Promise(resolve=>releases.push(()=>resolve({ok:true,text:async()=>JSON.stringify({discovery,plan:{id:'plan',instance_id:request.instance_id,service_port:request.service_port,image:request.image,strategy:request.strategy,deployment_mode:request.deployment_mode,clone_source_id:request.clone_source_id,clone_scope:request.clone_scope,operations:['prepare'],safety:['isolated'],source_baseline:{}}})})))}else if(url==='/api/extensions/deploy'){deployCalls+=1;body={task_id:'must-not-start'}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);element('extInstanceId').value='chatgpt2api-dev';element('extServicePort').value='33010';element('extImage').value='image:test';element('extCloneSource').value='';element('extDeployBtn').disabled=true;
const first=window.extensionCreatePlan();await Promise.resolve();element('extImage').value='image:changed';(listeners.input||[]).forEach(fn=>fn({target:element('extImage')}));element('extImage').value='image:test';releases.shift()();await first;if(!element('extDeployBtn').disabled)throw new Error('sequence-stale plan enabled deploy');await window.extensionStartDeploy();if(deployCalls!==0)throw new Error('sequence-stale response restored currentPlan');
const second=window.extensionCreatePlan();await Promise.resolve();element('extServicePort').value='33011';releases.shift()();await second;if(!element('extDeployBtn').disabled)throw new Error('context-stale plan enabled deploy');await window.extensionStartDeploy();if(deployCalls!==0)throw new Error('context-stale response restored currentPlan');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_adversarial_plan_clone_scope_fails_closed_before_selector_use_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const groups={};function radio(name,value,checked=false){const input={name,value,checked,dataset:{}};(groups[name]||(groups[name]=[])).push(input);return input}radio('extIntent','development',true);radio('extStrategy','isolated',true);radio('extDeployMode','compose',true);radio('extCloneScope','empty',true);radio('extCloneScope','working-copy');radio('extCredentialDelivery','once',true);radio('extNetwork','tailscale',true);
const malicious='empty"][value="working-copy';let maliciousSelector=false;global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes(malicious))maliciousSelector=true;const match=s.match(/input\[name="([^"]+)"\](?:\[value="([^"]+)"\])?/);if(match){const choices=groups[match[1]]||[];if(match[2]!==undefined)return choices.find(input=>input.value===match[2])||null;if(s.includes(':checked'))return choices.find(input=>input.checked)||null;return choices[0]||null}return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});const key='SHA256:AAAAAAAAAAAAAAAAAAAA',target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:key,chatgpt2api_port:33010};let deployCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/deploy/plan'){const request=JSON.parse(options.body);body={discovery:{environment:{},instances:[],deployment_modes:[]},plan:{id:'bad-plan',instance_id:request.instance_id,service_port:request.service_port,image:request.image,strategy:request.strategy,deployment_mode:request.deployment_mode,clone_source_id:'',clone_scope:malicious,operations:[],safety:[],source_baseline:{}}}}else if(url==='/api/extensions/deploy'){deployCalls+=1;body={task_id:'must-not-start'}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);element('extInstanceId').value='chatgpt2api-dev';element('extServicePort').value='33010';element('extImage').value='image:test';element('extCloneSource').value='';element('extDeployBtn').disabled=true;await window.extensionCreatePlan();if(maliciousSelector)throw new Error('untrusted clone_scope reached a selector');if(!element('extDeployBtn').disabled)throw new Error('malformed clone_scope enabled deploy');await window.extensionStartDeploy();if(deployCalls!==0)throw new Error('malformed clone_scope restored currentPlan');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_novice_step_one_executes_save_host_key_credential_and_ssh_states_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey','extHostKeyConfirm'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){this.focused=true},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const network={value:'tailscale',checked:true,classList:{toggle(){}}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return network;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';let saved={id:'saved',name:'My VPS',host:'vps.example',port:22,username:'root',host_key:'',chatgpt2api_port:33010};let saveCalls=0,probeCalls=0,confirmCalls=0,sshCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets'&&options.method==='POST'){saveCalls+=1;body={target:saved}}else if(url==='/api/extensions/targets')body={targets:[]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/probe'){probeCalls+=1;body={target_id:'saved',fingerprint:key}}else if(url==='/api/extensions/ssh/host-key/confirm'){confirmCalls+=1;saved={...saved,host_key:key};body={target:saved}}else if(url==='/api/extensions/ssh/test'){sshCalls+=1;body={ok:true,host_key:key,privileges:{is_root:true,can_deploy:true}}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();element('extName').value='My VPS';element('extHost').value='vps.example';element('extPort').value='22';element('extUsername').value='root';element('extServicePort').value='33010';
if(element('extGuidePrimaryBtn').textContent!=='common.save')throw new Error('unsaved target did not offer save');await window.extensionPrimaryAction();if(saveCalls!==1||element('extGuidePrimaryBtn').textContent!=='extensions.read_confirm_host_key')throw new Error('save did not advance to host-key setup');
await window.extensionPrimaryAction();if(probeCalls!==1||element('extGuidePrimaryBtn').textContent!=='extensions.confirm_host_key')throw new Error('host-key probe did not advance to explicit confirmation');await window.extensionPrimaryAction();if(confirmCalls!==1||element('extGuidePrimaryBtn').textContent!=='extensions.enter_password_button')throw new Error('confirmed host key did not request a session credential');
window.extensionPrimaryAction();if(!element('extPassword').focused)throw new Error('credential guide action did not focus the password field');element('extPassword').value='session-only';window.extensionCredentialChanged();if(element('extGuidePrimaryBtn').textContent!=='extensions.ssh_deploy_diagnostic')throw new Error('credential state did not offer SSH deployment diagnostics');
await window.extensionPrimaryAction();if(sshCalls!==1||element('extGuidePrimaryBtn').textContent!=='common.next')throw new Error('verified SSH did not unlock the next step: '+element('extGuidePrimaryBtn').textContent+' / '+element('extensionMessage').textContent);let visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};window.extensionPrimaryAction();if(visited.at(-1)!==2)throw new Error('verified SSH did not advance to service preparation');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_ssh_diagnostic_without_deploy_capability_does_not_unlock_next_steps_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set();elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const network={value:'tailscale',checked:true,classList:{toggle(){}}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return network;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'deploy-user',host_key:key,chatgpt2api_port:33010};let discoveryCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key:key,privileges:{is_root:false,docker_access:false,passwordless_sudo:false,password_sudo:false,can_deploy:false,diagnostic_code:'no_sudo_or_docker'}};else if(url==='/api/extensions/discover'){discoveryCalls+=1;body={}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);
if(!element('extSshNextBtn').disabled)throw new Error('can_deploy=false unlocked SSH next');if(element('extGuidePrimaryBtn').textContent==='common.next')throw new Error('can_deploy=false unlocked novice next');await window.extensionDiscover();if(discoveryCalls!==0)throw new Error('can_deploy=false unlocked discovery');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_managed_key_reset_submits_passwordless_and_explicit_reuse_contracts_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set();elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,checked:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const network={value:'tailscale',checked:true,classList:{toggle(){}}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return network;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});global.localStorage=new Proxy({}, {get(){throw new Error('reset touched browser storage')},set(){throw new Error('reset touched browser storage')}});
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'deploy-user',host_key:key,chatgpt2api_port:33010};const bodies=[];
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/local/tailscale/status')body={installed:false,online:false,serve:false};else if(url==='/api/extensions/instances/reset-admin-key'){bodies.push(JSON.parse(options.body));body={admin_key:'gbx-test-only'}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');window.extensionOpenResetModal('managed-app');
element('extResetPassword').value='login-session';element('extResetElevation').value='passwordless_sudo';element('extResetSudo').value='must-clear';element('extResetReuseSshPassword').checked=true;window.extensionResetCredentialChanged();await window.extensionConfirmResetKey();
if(bodies.length!==1)throw new Error('passwordless reset was not submitted');let c=bodies[0].credential;if(c.elevation!=='passwordless_sudo'||c.sudo_password||c.reuse_ssh_password)throw new Error('passwordless reset contract was inferred incorrectly');
window.extensionOpenResetModal('managed-app');element('extResetPassword').value='same-session';element('extResetElevation').value='password_sudo';element('extResetSudo').value='must-not-send';element('extResetReuseSshPassword').checked=true;window.extensionResetCredentialChanged();await window.extensionConfirmResetKey();
if(bodies.length!==2)throw new Error('reuse reset was not submitted');c=bodies[1].credential;if(c.elevation!=='password_sudo'||c.reuse_ssh_password!==true||c.password!=='same-session'||c.sudo_password)throw new Error('explicit reuse reset contract was not preserved');if(JSON.stringify(bodies).includes('must-not-send'))throw new Error('unused sudo secret was submitted');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_novice_local_tailscale_states_expose_one_next_action_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set();elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const network={value:'tailscale',checked:true,classList:{toggle(){}}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return network;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
let state={installed:false,online:false,serve:false,app_port:8892,serve_port:8893},installCalls=0,loginCalls=0,serveCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/local/tailscale/status')body=state;else if(url==='/api/extensions/network/local/tailscale/install'){installCalls+=1;body={task_id:'install-one'}}else if(url==='/api/extensions/network/local/tailscale/login'){loginCalls+=1;body={online:false}}else if(url==='/api/extensions/network/local/tailscale/serve'){serveCalls+=1;body={url:'https://genbox.tailnet'}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionNext(3);await window.extensionCheckLocalTailscale();if(element('extGuidePrimaryBtn').textContent!=='common.install')throw new Error('missing Tailscale did not offer install');await window.extensionPrimaryAction();if(installCalls!==1)throw new Error('install guide action was not executable');
state={...state,installed:true};await window.extensionCheckLocalTailscale();if(element('extGuidePrimaryBtn').textContent!=='auth.login')throw new Error('installed offline state did not offer login');await window.extensionPrimaryAction();if(loginCalls!==1)throw new Error('login guide action was not executable');
state={...state,online:true};await window.extensionCheckLocalTailscale();if(element('extGuidePrimaryBtn').textContent!=='extensions.enable_private_entry')throw new Error('online state did not offer Serve');await window.extensionPrimaryAction();if(serveCalls!==1)throw new Error('Serve guide action was not executable');
state={...state,serve:true};await window.extensionCheckLocalTailscale();if(element('extGuidePrimaryBtn').textContent!=='extensions.connect_and_test')throw new Error('ready local state did not offer the remote test');let visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};window.extensionPrimaryAction();if(visited.at(-1)!==4)throw new Error('ready local state did not advance to remote verification');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_network_credentials_survive_transport_failures_and_clear_only_on_completion_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkRecovery','extHandoff','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const network={value:'tailscale',checked:true,classList:{toggle(){}}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return network;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};
const key='SHA256:AAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key:key,chatgpt2api_port:33010};const deployment={id:'done',status:'completed',progress:100,host_key:key,steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',target_id:'saved',managed:true},url:'http://service.example',api_url:'http://service.example/v1',admin_key_available:false}};
let attempt=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={latest_task_id:'done',tasks:[deployment]};else if(url==='/api/extensions/network/connect'){attempt+=1;if(attempt===1)return {ok:false,status:503,text:async()=>JSON.stringify({detail:'temporary'})};body={task_id:'network-'+attempt}}else if(url==='/api/extensions/network/tasks/network-2')return {ok:false,status:502,text:async()=>JSON.stringify({detail:'poll temporary'})};else if(url==='/api/extensions/network/tasks/network-3')body={status:'completed',progress:100,steps:[{id:'http_probe',status:'success'}],logs:[],result:{local_address:'100.64.0.1',remote_address:'100.64.0.2',peer_reachable:true,genbox_reachable:true,genbox_url:'https://genbox.tailnet'}};return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extRemoteNetworkMode').value='existing';window.extensionNetworkModeChanged('existing');element('extPassword').value='password-session';element('extPrivateKey').value='';element('extElevation').value='password_sudo';element('extSudoPassword').value='sudo-session';window.extensionCredentialChanged();window.extensionNext(4);
await window.extensionConnectNetwork();if(element('extPassword').value!=='password-session'||element('extSudoPassword').value!=='sudo-session')throw new Error('network POST failure cleared credentials');
await window.extensionConnectNetwork();if(timers.length!==1)throw new Error('polling attempt was not created');await timers[0]();if(element('extPassword').value!=='password-session'||element('extSudoPassword').value!=='sudo-session')throw new Error('poll HTTP failure cleared credentials');
await window.extensionConnectNetwork();if(timers.length!==2)throw new Error('completion attempt was not created');await timers[1]();if(element('extPassword').value||element('extPrivateKey').value||element('extSudoPassword').value)throw new Error('completed network task did not clear session credentials');if(element('extSuccessBanner').classList.contains('hidden'))throw new Error('verified application probe did not show completion');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
