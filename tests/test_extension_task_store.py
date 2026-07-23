import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
from extensions.models import ExtensionDeployRequest, ExtensionPlanRequest, ExtensionTarget, SSHCredential
from extensions.deployment_failures import FAILURES, VALID_FAILURE_COMBINATIONS
from extensions.orchestrator import (
    DeploymentPlanUnavailableError,
    DeploymentPlanManager,
    DeploymentResourceConflictError,
    DeploymentResourceReservations,
    ExtensionTaskManager,
    _resume_target_handle,
    public_instance_handle,
)
from extensions.task_store import (
    PREVIOUS_TASK_STORE_SCHEMA_VERSION,
    TASK_STORE_SCHEMA_VERSION,
    TaskStore,
)


DEPLOYMENT_ATTEMPT_ID = "0123456789abcdef0123456789abcdef"
TEST_HOST_KEY_ALGORITHM = "ssh-ed25519"
TEST_HOST_KEY = "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


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
        "evidence_manifest": {
            "contract_version": "phase4-v3",
            "snapshot_digest": "a" * 64,
            "complete": True,
            "changed_fields": [],
        },
        **extra,
    }


@pytest.mark.parametrize("attempt_id", [
    "",
    "a" * 31,
    "a" * 33,
    "A" * 32,
    "g" * 32,
    "0123456789abcdef0123456789abcde-",
])
def test_deployment_attempt_id_requires_exact_lowercase_hex(attempt_id):
    target = ExtensionTarget(
        id="attempt-target", name="VPS", host="host.example", username="deploy-user",
    )
    with pytest.raises(ValueError):
        ExtensionDeployRequest(
            deployment_attempt_id=attempt_id,
            target=target,
            credential=SSHCredential(password="validation-only"),
        )

    valid = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=target,
        credential=SSHCredential(password="validation-only"),
    )
    assert valid.deployment_attempt_id == DEPLOYMENT_ATTEMPT_ID


def prepare_deployment_plan(monkeypatch, request: ExtensionDeployRequest):
    from extensions import orchestrator

    target = request.target.model_copy(update={
        "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY,
    })
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
        "host_key_algorithm": target.host_key_algorithm,
        "host_key": target.host_key,
        "environment": {
            "docker_version": "27.0", "compose_version": "2.30",
            "home_dir": f"/home/{target.username}", "listening_ports": [],
            "tcp_listeners": [],
            "listening_ports_probe": {
                "status": 0, "complete": True, "payload_present": True,
            },
            "disk_free_mb": 5000,
        },
        "privileges": privileges,
        "instances": [],
        "path_conditions_version": "phase4-v3",
        "path_conditions": {
            "target_install_dir_absent": True,
            "target_install_parent_claimable": True,
            "target_data_dir_nonoverlap": True,
            "target_compose_project_nonoverlap": True,
            "target_port_unoccupied": True,
        },
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


def test_duplicate_deployment_attempt_is_idempotent_and_conflicting_reuse_fails_closed(tmp_path, monkeypatch):
    from extensions import orchestrator

    request = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=ExtensionTarget(
            id="attempt-target", name="VPS", host="host.example", username="deploy-user",
            chatgpt2api_port=33010,
        ),
        credential=SSHCredential(password="attempt-password-sentinel"),
        instance_id="attempt-app",
        image="example.invalid/app@sha256:" + "a" * 64,
    )
    request, plan_manager, plan = prepare_deployment_plan(monkeypatch, request)
    fresh_discovery = copy.deepcopy(plan_manager.plans[plan["id"]]["execution_snapshot"])
    fresh_discovery["environment"]["disk_free_mb"] = 5000
    fresh_discovery["path_conditions_version"] = "phase4-v3"
    fresh_discovery["path_conditions"] = {
        "target_install_dir_absent": True,
        "target_install_parent_claimable": True,
        "target_data_dir_nonoverlap": True,
        "target_compose_project_nonoverlap": True,
        "target_port_unoccupied": True,
    }
    discovery_calls = 0
    runner_calls = 0
    release_runner = asyncio.Event()

    async def counted_discovery(_request, *, path_checks=None):
        nonlocal discovery_calls
        discovery_calls += 1
        return copy.deepcopy(fresh_discovery)

    async def blocked_runner(_task_id, _request, _plan):
        nonlocal runner_calls
        runner_calls += 1
        await release_runner.wait()

    async def run():
        monkeypatch.setattr("extensions.discovery.discover_environment", counted_discovery)
        manager = ExtensionTaskManager(store_path=tmp_path / "attempts.json")
        monkeypatch.setattr(manager, "_run", blocked_runner)

        first_id, duplicate_id = await asyncio.gather(manager.create(request), manager.create(request))
        assert first_id == duplicate_id
        assert discovery_calls == 1
        assert len(manager.tasks) == 1
        assert len(manager.runners) == 1
        assert manager.resource_reservations.active_count == 1

        conflicting = request.model_copy(update={
            "image": "example.invalid/other@sha256:" + "b" * 64,
            "service_port": 33011,
        })
        with pytest.raises(Exception) as exc_info:
            await manager.create(conflicting)
        assert exc_info.value.__class__.__name__ == "DeploymentAttemptConflictError"
        assert getattr(exc_info.value, "diagnostic", {}) == {
            "code": "deployment_attempt_conflict",
            "stage": "deployment_attempt",
            "retry_safe": False,
        }
        assert all(value not in str(exc_info.value) for value in (
            "host.example", "deploy-user", "attempt-password-sentinel", "33011", "example.invalid/other",
        ))
        assert discovery_calls == 1
        assert len(manager.tasks) == 1
        assert len(manager.runners) == 1

        release_runner.set()
        await manager.runners[first_id]
        assert runner_calls == 1

    asyncio.run(run())


def test_deployment_attempt_correlation_is_memory_only_and_restart_uses_opaque_task_state(tmp_path, monkeypatch, caplog):
    request = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=ExtensionTarget(
            id="restart-target", name="VPS", host="restart.example", username="deploy-user",
            chatgpt2api_port=33010,
        ),
        credential=SSHCredential(password="restart-password-sentinel"),
        instance_id="restart-app",
        image="example.invalid/app@sha256:" + "c" * 64,
    )
    request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
    path = tmp_path / "restart-attempts.json"

    async def blocked_runner(_task_id, _request, _plan):
        await asyncio.Event().wait()

    async def run():
        manager = ExtensionTaskManager(store_path=path)
        monkeypatch.setattr(manager, "_run", blocked_runner)
        task_id = await manager.create(request)
        binding = manager.resume_bindings[task_id]
        assert set(binding) == {"target_handle", "instance_handle", "managed_required"}
        assert binding["target_handle"].startswith("t-")
        assert binding["instance_handle"].startswith("i-")
        assert binding["managed_required"] is True
        assert request.target.id not in json.dumps(binding)
        assert request.instance_id not in json.dumps(binding)
        manager.runners[task_id].cancel()
        with pytest.raises(asyncio.CancelledError):
            await manager.runners[task_id]

        recovered = ExtensionTaskManager(store_path=path)
        assert recovered.get(task_id)["status"] == "interrupted"
        assert "deployment_attempt_id" not in recovered.get(task_id)
        assert "deployment_attempt_id" not in recovered.list_summary()["tasks"][0]
        assert recovered.runners == {}
        assert recovered.resume_bindings == {}

        persisted = path.read_text(encoding="utf-8")
        assert DEPLOYMENT_ATTEMPT_ID not in persisted
        assert "deployment_context_fingerprint" not in persisted
        assert all(secret not in persisted for secret in (
            "restart-password-sentinel", "restart.example", "deploy-user",
        ))
        assert all(secret not in caplog.text for secret in (
            "restart-password-sentinel", "restart.example", "deploy-user",
        ))

    asyncio.run(run())


def test_cancelled_deployment_owner_releases_lease_attempt_and_waiter(tmp_path, monkeypatch):
    request = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=ExtensionTarget(
            id="cancel-owner-target", name="VPS", host="host.example", username="deploy-user",
            chatgpt2api_port=33010,
        ),
        credential=SSHCredential(password="cancel-owner-sentinel"),
        instance_id="cancel-owner-app",
        image="example.invalid/app@sha256:" + "d" * 64,
    )
    request, plan_manager, plan = prepare_deployment_plan(monkeypatch, request)
    discovery_started = asyncio.Event()

    async def suspended_discovery(_request, *, path_checks=None):
        discovery_started.set()
        await asyncio.Event().wait()

    async def run():
        monkeypatch.setattr("extensions.discovery.discover_environment", suspended_discovery)
        manager = ExtensionTaskManager(store_path=tmp_path / "cancel-owner.json")
        owner = asyncio.create_task(manager.create(request))
        await discovery_started.wait()
        waiter = asyncio.create_task(manager.create(request))
        await asyncio.sleep(0)

        owner.cancel()
        results = await asyncio.wait_for(
            asyncio.gather(owner, waiter, return_exceptions=True),
            timeout=1,
        )

        assert all(isinstance(result, asyncio.CancelledError) for result in results)
        assert request.deployment_attempt_id not in manager.deployment_attempts
        assert plan["id"] in plan_manager.plans
        assert "_lease_token" not in plan_manager.plans[plan["id"]]
        assert manager.resource_reservations.active_count == 0
        assert manager.tasks == {}
        assert manager.runners == {}
        assert manager.task_reservations == {}
        assert not (tmp_path / "cancel-owner.json").exists()

    asyncio.run(run())


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


def test_task_store_and_task_routes_expose_only_the_explicit_public_projection(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manifest = {
        "contract_version": "phase4-v3",
        "snapshot_digest": "a" * 64,
        "complete": True,
        "changed_fields": [],
    }
    sentinels = (
        "sentinel-host.example", "SHA256:SENTINELFINGERPRINT", "/srv/sentinel/path",
        "https://sentinel.example/console", "registry.invalid/sentinel-image", "34567",
        "sentinel-compose", "sentinel-container", "sentinel-lease", "sentinel-command-output",
        "sentinel-session-secret", "sentinel-host-key-algorithm",
    )
    manager.tasks["opaque-task"] = task(
        "opaque-task",
        host_key_algorithm=sentinels[11],
        host_key=sentinels[1],
        logs=[{
            "time": "00:00:00",
            "message": f"{sentinels[11]} {sentinels[1]} {sentinels[9]}",
        }],
        result={
            "url": sentinels[3],
            "api_url": sentinels[3] + "/v1",
            "admin_key_available": True,
            "instance": {
                "id": "sentinel-instance", "target_id": "sentinel-target",
                "install_dir": sentinels[2], "data_dir": sentinels[2] + "/data",
                "image": sentinels[4], "service_port": 34567,
                "compose_project": sentinels[6], "container_id": sentinels[7],
                "managed": True,
            },
        },
        deployment_attempt_id="b" * 32,
        deployment_context_fingerprint="c" * 64,
        evidence_manifest=manifest,
        request={"host": sentinels[0], "secret": sentinels[10]},
        execution_snapshot={"path": sentinels[2], "binding": sentinels[5]},
        reservation_token=sentinels[8],
    )
    manager.deliveries["opaque-task"] = sentinels[10]
    manager._persist()

    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")
    single = client.get("/api/extensions/tasks/opaque-task")
    summary = client.get("/api/extensions/tasks")
    assert single.status_code == 200
    assert summary.status_code == 200

    expected_keys = {
        "id", "status", "phase", "steps", "progress", "created_at", "updated_at",
        "failed_phase", "error_code", "recovery_action", "evidence_manifest",
    }
    single_task = single.json()
    listed_task = summary.json()["tasks"][0]
    assert set(single_task) == expected_keys
    assert listed_task == single_task
    assert set(single_task["steps"][0]) == {"id", "label", "status"}

    persisted = path.read_text(encoding="utf-8")
    responses = json.dumps({"single": single_task, "summary": summary.json()}, ensure_ascii=False)
    for sentinel in sentinels:
        assert sentinel not in persisted
        assert sentinel not in responses


def test_legacy_v1_tasks_are_sanitized_and_atomically_rewritten_to_v3(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    replace_calls = []
    real_replace = os.replace
    sentinels = {
        "host_key": "SHA256:LEGACYFINGERPRINT",
        "url": "https://legacy.example/console",
        "path": "/srv/legacy/private",
        "image": "registry.invalid/legacy-image",
        "secret": "legacy-session-secret",
    }
    legacy_tasks = [
        task(
            "legacy-running", "running",
            phase="connect",
            host_key=sentinels["host_key"],
            logs=[{"time": "00:00:00", "message": sentinels["path"]}],
            deployment_attempt_id="d" * 32,
            deployment_context_fingerprint="e" * 64,
        ),
        task(
            "legacy-completed", "completed",
            host_key=sentinels["host_key"],
            result={
                "url": sentinels["url"], "api_url": sentinels["url"] + "/v1",
                "admin_key_available": True,
                "instance": {
                    "id": "legacy-instance", "target_id": "legacy-target",
                    "install_dir": sentinels["path"], "data_dir": sentinels["path"] + "/data",
                    "image": sentinels["image"], "service_port": 34567,
                    "compose_project": "legacy-compose", "container_id": "legacy-container",
                    "managed": True,
                },
                "delivery": sentinels["secret"],
            },
        ),
    ]
    path.write_text(json.dumps({"schema_version": 1, "tasks": legacy_tasks}), encoding="utf-8")

    def record_replace(source, target):
        replace_calls.append((Path(source), Path(target), Path(source).exists()))
        return real_replace(source, target)

    monkeypatch.setattr("extensions.task_store.os.replace", record_replace)
    loaded = TaskStore(path).load()

    assert TASK_STORE_SCHEMA_VERSION == 3
    assert {item["id"]: item["status"] for item in loaded} == {
        "legacy-running": "interrupted",
        "legacy-completed": "completed",
    }
    assert next(item for item in loaded if item["id"] == "legacy-running")["recovery_action"] == (
        "regenerate_plan_and_reprovide_credentials"
    )
    assert next(item for item in loaded if item["id"] == "legacy-completed")["recovery_action"] == (
        "reverify_ownership_and_rotate_admin_key"
    )
    rewritten = path.read_text(encoding="utf-8")
    assert json.loads(rewritten)["schema_version"] == 3
    assert replace_calls[-1][1] == path and replace_calls[-1][2] is True
    assert not list(tmp_path.glob("extension_tasks.json.invalid.*.json"))
    for sentinel in sentinels.values():
        assert sentinel not in rewritten


def test_v2_phase_recovery_is_atomically_normalized_to_v3(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    records = [
        TaskStore.public_task(task("cancel-prepare", "cancelled", phase="prepare")),
        TaskStore.public_task(task("cancel-verify", "cancelled", phase="verify")),
        TaskStore.public_task(task(
            "cancel-connect", "cancelled", phase="connect",
            recovery_action="inspect_owned_instance_and_regenerate_plan",
        )),
        TaskStore.public_task(task(
            "interrupted-verify", "interrupted", phase="verify",
            recovery_action="regenerate_plan_and_reprovide_credentials",
        )),
    ]
    path.write_text(json.dumps({
        "schema_version": PREVIOUS_TASK_STORE_SCHEMA_VERSION,
        "tasks": records,
    }), encoding="utf-8")
    replace_calls = []
    real_replace = os.replace

    def record_replace(source, target):
        replace_calls.append((Path(source), Path(target), Path(source).exists()))
        return real_replace(source, target)

    monkeypatch.setattr("extensions.task_store.os.replace", record_replace)
    store = TaskStore(path)
    loaded = {record["id"]: record for record in store.load()}

    assert PREVIOUS_TASK_STORE_SCHEMA_VERSION == 2
    assert loaded["cancel-prepare"]["recovery_action"] == (
        "inspect_owned_partial_deployment_and_regenerate_plan"
    )
    assert loaded["cancel-verify"]["recovery_action"] == (
        "inspect_owned_instance_and_regenerate_plan"
    )
    assert loaded["cancel-connect"]["recovery_action"] is None
    assert loaded["interrupted-verify"]["recovery_action"] == (
        "inspect_owned_instance_and_regenerate_plan"
    )
    rewritten = json.loads(path.read_text(encoding="utf-8"))
    assert rewritten["schema_version"] == TASK_STORE_SCHEMA_VERSION
    assert replace_calls[-1][1] == path and replace_calls[-1][2] is True
    assert not list(tmp_path.glob("*.tmp"))
    assert "phase-aware recovery" in (store.warning or "")


def test_invalid_v2_public_record_is_quarantined_without_migration(tmp_path):
    path = tmp_path / "invalid-v2.json"
    record = TaskStore.public_task(task("invalid-v2"))
    record["raw_target_id"] = "must-not-be-normalized"
    original = json.dumps({
        "schema_version": PREVIOUS_TASK_STORE_SCHEMA_VERSION,
        "tasks": [record],
    })
    path.write_text(original, encoding="utf-8")

    assert TaskStore(path).load() == []
    quarantined = list(tmp_path.glob("invalid-v2.json.invalid.*.json"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding="utf-8") == original
    assert not path.exists()


def test_v2_atomic_rewrite_failure_preserves_original_and_blocks_writes(tmp_path, monkeypatch):
    path = tmp_path / "v2-write-failure.json"
    original = json.dumps({
        "schema_version": PREVIOUS_TASK_STORE_SCHEMA_VERSION,
        "tasks": [TaskStore.public_task(task("cancel-v2", "cancelled", phase="verify"))],
    })
    path.write_text(original, encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("injected v2 atomic rewrite failure")

    monkeypatch.setattr("extensions.task_store.os.replace", fail_replace)
    store = TaskStore(path)
    assert store.load() == []
    assert store.warning == "Previous deployment task state requires safe migration before it can be shown."
    assert path.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob("v2-write-failure.json.invalid.*.json"))
    with pytest.raises(RuntimeError, match="writes are blocked"):
        store.save([task("must-not-overwrite")])


@pytest.mark.parametrize(("phase", "expected"), [
    ("prepare", "inspect_owned_partial_deployment_and_regenerate_plan"),
    ("verify", "inspect_owned_instance_and_regenerate_plan"),
])
def test_legacy_invalid_failed_task_migrates_to_phase_aware_interrupted_recovery(tmp_path, phase, expected):
    path = tmp_path / f"legacy-invalid-{phase}.json"
    legacy = task(
        f"legacy-invalid-{phase}", "failed", phase=phase,
        failed_phase="unknown", error_code="unknown", recovery_action="unknown",
    )
    path.write_text(json.dumps({"schema_version": 1, "tasks": [legacy]}), encoding="utf-8")

    loaded = TaskStore(path).load()

    assert loaded[0]["status"] == "interrupted"
    assert loaded[0]["recovery_action"] == expected


def test_recognized_legacy_rewrite_failure_keeps_original_without_public_reexport(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    original = json.dumps({"schema_version": 1, "tasks": [task("legacy-running", "running")]})
    path.write_text(original, encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("injected atomic rewrite failure")

    monkeypatch.setattr("extensions.task_store.os.replace", fail_replace)
    store = TaskStore(path)
    assert store.load() == []
    assert store.warning == "Previous deployment task state requires safe migration before it can be shown."
    assert path.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob("extension_tasks.json.invalid.*.json"))


def test_completed_failed_and_cancelled_tasks_survive_manager_rebuild(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks = {
        "completed": task("completed", "completed", "2026-07-17T00:00:03.000Z"),
        "failed": task(
            "failed", "failed", "2026-07-17T00:00:02.000Z",
            failed_phase="pull", error_code="image_prepare_failed",
            recovery_action="check_image_access_and_regenerate_plan",
        ),
        "cancelled": task(
            "cancelled", "cancelled", "2026-07-17T00:00:01.000Z", error="cancelled",
            recovery_action="inspect_owned_instance_and_regenerate_plan",
        ),
    }
    manager._persist()

    rebuilt = ExtensionTaskManager(store_path=path)
    assert {name: rebuilt.get(name)["status"] for name in manager.tasks} == {
        "completed": "completed", "failed": "failed", "cancelled": "cancelled",
    }


def test_running_or_queued_task_recovers_as_interrupted_without_runner(tmp_path):
    path = tmp_path / "extension_tasks.json"
    TaskStore(path).save([
        task("running", "running", phase="connect"),
        task("queued", "queued", phase="docker"),
    ])

    rebuilt = ExtensionTaskManager(store_path=path)
    for task_id in ("running", "queued"):
        state = rebuilt.get(task_id)
        assert state["status"] == "interrupted"
        assert state["recovery_action"] == "regenerate_plan_and_reprovide_credentials"
        assert task_id not in rebuilt.runners
        assert task_id not in rebuilt.task_reservations
    assert rebuilt.list_summary()["active_task_id"] is None
    assert rebuilt.resource_reservations.active_count == 0


def test_post_write_restart_requires_owned_resource_inspection(tmp_path):
    path = tmp_path / "extension_tasks.json"
    TaskStore(path).save([
        task("prepare", "running", phase="prepare"),
        task("pull", "running", phase="pull"),
        task("start", "queued", phase="start"),
        task("verify", "running", phase="verify"),
    ])

    rebuilt = ExtensionTaskManager(store_path=path)
    assert rebuilt.get("prepare")["recovery_action"] == (
        "inspect_owned_partial_deployment_and_regenerate_plan"
    )
    for task_id in ("pull", "start", "verify"):
        assert rebuilt.get(task_id)["recovery_action"] == (
            "inspect_owned_instance_and_regenerate_plan"
        )


@pytest.mark.parametrize("schema_version", [
    1, PREVIOUS_TASK_STORE_SCHEMA_VERSION, TASK_STORE_SCHEMA_VERSION,
])
def test_duplicate_task_ids_fail_closed_and_quarantine_on_load(tmp_path, schema_version):
    path = tmp_path / f"duplicates-v{schema_version}.json"
    original = json.dumps({
        "schema_version": schema_version,
        "tasks": [task("duplicate"), task("duplicate")],
    })
    path.write_text(original, encoding="utf-8")

    assert TaskStore(path).load() == []
    quarantined = list(tmp_path.glob(f"duplicates-v{schema_version}.json.invalid.*.json"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding="utf-8") == original


def test_duplicate_task_ids_are_rejected_before_save(tmp_path):
    path = tmp_path / "duplicates-save.json"
    with pytest.raises(ValueError, match="invalid task store record"):
        TaskStore(path).save([task("duplicate"), task("duplicate")])
    assert not path.exists()


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


def test_failed_quarantine_blocks_later_writes_and_preserves_truthful_warning(tmp_path, monkeypatch):
    path = tmp_path / "corrupt-live.json"
    original = "{corrupt live task state"
    path.write_text(original, encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("injected quarantine failure")

    monkeypatch.setattr("extensions.task_store.os.replace", fail_replace)
    store = TaskStore(path)
    assert store.load() == []
    assert "remains in place" in (store.warning or "")
    assert "writes are blocked" in (store.warning or "")
    with pytest.raises(RuntimeError, match="writes are blocked"):
        store.save([task("must-not-overwrite")])
    assert path.read_text(encoding="utf-8") == original


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
    valid = task(
        "valid", "failed", failed_phase="pull",
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
        invalid_path.write_text(json.dumps({"schema_version": TASK_STORE_SCHEMA_VERSION, "tasks": [invalid]}), encoding="utf-8")
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
        task(
            "interrupted", "interrupted", phase="connect",
            recovery_action="regenerate_plan_and_reprovide_credentials",
        ),
        task("completed-none", "completed", recovery_action=None),
        task("completed-rotate", "completed", recovery_action="reverify_ownership_and_rotate_admin_key"),
    ]
    store = TaskStore(path)
    store.save(records)

    loaded = {record["id"]: record for record in store.load()}
    assert loaded["interrupted"]["recovery_action"] == "regenerate_plan_and_reprovide_credentials"
    assert loaded["completed-none"]["recovery_action"] is None
    assert loaded["completed-rotate"]["recovery_action"] == "reverify_ownership_and_rotate_admin_key"


@pytest.mark.parametrize(("status", "phase", "recovery_action"), [
    ("cancelled", "connect", "inspect_owned_instance_and_regenerate_plan"),
    ("cancelled", "prepare", None),
    ("cancelled", "verify", "inspect_owned_partial_deployment_and_regenerate_plan"),
    ("interrupted", "connect", "inspect_owned_instance_and_regenerate_plan"),
    ("interrupted", "prepare", "regenerate_plan_and_reprovide_credentials"),
    ("interrupted", "verify", "inspect_owned_partial_deployment_and_regenerate_plan"),
])
def test_current_schema_requires_exact_phase_aware_recovery_pairing(
    tmp_path, status, phase, recovery_action,
):
    path = tmp_path / f"strict-{status}-{phase}.json"
    with pytest.raises(ValueError, match="invalid task store record"):
        TaskStore(path).save([task(
            f"strict-{status}-{phase}", status, phase=phase,
            recovery_action=recovery_action,
        )])
    assert not path.exists()


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
    assert "admin_key_available" not in text
    assert "result" not in text
    assert "logs" not in text


def test_delivery_is_once_only_and_restart_requires_credential_recovery(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["delivery"] = task("delivery", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["delivery"] = {
        "deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID,
        "admin_key": "gbx-secret-delivery",
        "instance": {
            "handle": "i-" + "a" * 32, "project": "chatgpt2api", "managed": True,
            "running": True, "console_url": "http://service.example",
            "api_url": "http://service.example/v1",
        },
    }
    manager.resume_bindings["delivery"] = {
        "target_handle": "t-" + "a" * 32,
        "instance_handle": "i-" + "a" * 32,
        "managed_required": True,
    }
    manager._persist()
    assert "gbx-secret-delivery" not in path.read_text(encoding="utf-8")
    assert manager.take_delivery("delivery", DEPLOYMENT_ATTEMPT_ID)["admin_key"] == "gbx-secret-delivery"
    assert "delivery" in manager.resume_bindings
    assert manager.take_delivery("delivery", DEPLOYMENT_ATTEMPT_ID) is None
    assert "result" not in manager.get("delivery")
    assert manager.get("delivery")["recovery_action"] == "reverify_ownership_and_rotate_admin_key"
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert "result" not in persisted["tasks"][0]

    manager.tasks["restart"] = task("restart", recovery_action="reverify_ownership_and_rotate_admin_key", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-b", "managed": True},
    })
    manager._persist()
    rebuilt = ExtensionTaskManager(store_path=path)
    recovered = rebuilt.get("restart")
    assert "result" not in recovered
    assert recovered["recovery_action"] == "reverify_ownership_and_rotate_admin_key"
    assert rebuilt.take_delivery("restart", DEPLOYMENT_ATTEMPT_ID) is None


def test_delivery_route_is_once_only_and_persists_consumption(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["delivery"] = task("delivery", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["delivery"] = {
        "deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID,
        "admin_key": "route-delivery-key",
        "instance": {
            "handle": "i-" + "b" * 32, "project": "chatgpt2api", "managed": True,
            "running": True, "console_url": "http://service.example",
            "api_url": "http://service.example/v1",
        },
    }
    manager._persist()
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    assert client.post("/api/extensions/tasks/delivery/delivery").status_code == 422
    assert client.post(
        "/api/extensions/tasks/delivery/delivery",
        json={"deployment_attempt_id": "f" * 32},
    ).status_code == 404
    assert "delivery" in manager.deliveries
    first = client.post(
        "/api/extensions/tasks/delivery/delivery",
        json={"deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID},
    )
    assert first.status_code == 200
    assert first.json() == {
        "admin_key": "route-delivery-key",
        "instance": {
            "handle": "i-" + "b" * 32, "project": "chatgpt2api", "managed": True,
            "running": True, "console_url": "http://service.example",
            "api_url": "http://service.example/v1",
        },
        "shown_once": True,
    }
    assert client.post(
        "/api/extensions/tasks/delivery/delivery",
        json={"deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID},
    ).status_code == 404
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert "result" not in persisted["tasks"][0]


def test_two_tabs_cannot_cross_claim_delivery_and_each_initiator_consumes_once(tmp_path, monkeypatch):
    manager = ExtensionTaskManager(store_path=tmp_path / "multiple-deliveries.json")
    for task_id, suffix, host in (
        ("task-a", "a", "first.example"),
        ("task-b", "b", "second.example"),
    ):
        manager.tasks[task_id] = task(task_id)
        manager.deliveries[task_id] = {
            "deployment_attempt_id": suffix * 32,
            "admin_key": f"key-{suffix}",
            "instance": {
                "handle": "i-" + suffix * 32, "project": "chatgpt2api",
                "managed": True, "running": True,
                "console_url": f"https://{host}", "api_url": f"https://{host}/v1",
            },
        }
    manager._persist()
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    assert client.post(
        "/api/extensions/tasks/task-b/delivery", json={"deployment_attempt_id": "a" * 32},
    ).status_code == 404
    assert "task-b" in manager.deliveries
    second = client.post(
        "/api/extensions/tasks/task-b/delivery", json={"deployment_attempt_id": "b" * 32},
    ).json()
    first = client.post(
        "/api/extensions/tasks/task-a/delivery", json={"deployment_attempt_id": "a" * 32},
    ).json()
    assert second["admin_key"] == "key-b"
    assert second["instance"]["handle"] == "i-" + "b" * 32
    assert second["instance"]["console_url"] == "https://second.example"
    assert first["admin_key"] == "key-a"
    assert first["instance"]["handle"] == "i-" + "a" * 32
    assert first["instance"]["console_url"] == "https://first.example"
    assert client.post(
        "/api/extensions/tasks/task-b/delivery", json={"deployment_attempt_id": "b" * 32},
    ).status_code == 404


def test_resume_route_requires_exact_ephemeral_binding_and_returns_only_safe_access(tmp_path, monkeypatch):
    path = tmp_path / "resume-binding.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["historical"] = task("historical", recovery_action="reverify_ownership_and_rotate_admin_key")
    manager.resume_bindings["historical"] = {
        "target_handle": _resume_target_handle("target-a"),
        "instance_handle": public_instance_handle("target-a", "instance-a"),
        "managed_required": True,
    }
    manager.deliveries["historical"] = {
        "deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID,
        "admin_key": "must-remain-unclaimed",
        "instance": {"handle": "i-opaque"},
    }
    matching = SimpleNamespace(
        id="instance-a", target_id="target-a", project="chatgpt2api",
        status="running", managed=True, ownership="managed",
        console_url="https://console.example", api_url="https://console.example/v1",
    )
    unrelated_instance = SimpleNamespace(
        id="instance-b", target_id="target-b", project="chatgpt2api",
        status="running", managed=True, ownership="managed",
        console_url="https://unrelated.example", api_url="https://unrelated.example/v1",
    )
    monkeypatch.setattr(
        "extensions.orchestrator.extensions_store.list_instances",
        lambda target_id="": [matching] if target_id == "target-a" else [unrelated_instance],
    )
    manager._persist()
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    assert client.post("/api/extensions/tasks/historical/resume").status_code == 422
    assert client.post(
        "/api/extensions/tasks/historical/resume", json={"target_id": "../invalid"},
    ).status_code == 422
    unrelated = client.post(
        "/api/extensions/tasks/historical/resume", json={"target_id": "target-b"},
    )
    assert unrelated.status_code == 200
    assert unrelated.json() == {"resumable": False}
    resumed = client.post(
        "/api/extensions/tasks/historical/resume", json={"target_id": "target-a"},
    )
    assert resumed.status_code == 200
    assert resumed.json() == {
        "resumable": True,
        "instance": {
            "handle": public_instance_handle("target-a", "instance-a"),
            "project": "chatgpt2api", "managed": True, "running": True,
            "console_url": "https://console.example",
            "api_url": "https://console.example/v1",
        },
    }
    assert manager.deliveries["historical"]["admin_key"] == "must-remain-unclaimed"
    persisted = path.read_text(encoding="utf-8")
    assert "target-a" not in persisted
    assert "instance-a" not in persisted
    assert "target_handle" not in persisted
    assert "instance_handle" not in persisted

    rebuilt = ExtensionTaskManager(store_path=path)
    monkeypatch.setattr(main, "extension_tasks", rebuilt)
    assert rebuilt.resume_bindings == {}
    assert client.post(
        "/api/extensions/tasks/historical/resume", json={"target_id": "target-a"},
    ).json() == {"resumable": False}


def test_resume_binding_fails_closed_for_stale_ineligible_and_ambiguous_instances(tmp_path, monkeypatch):
    manager = ExtensionTaskManager(store_path=tmp_path / "resume-fail-closed.json")
    manager.tasks["historical"] = task("historical")
    manager.resume_bindings["historical"] = {
        "target_handle": _resume_target_handle("target-a"),
        "instance_handle": public_instance_handle("target-a", "instance-a"),
        "managed_required": True,
    }

    def instance(*, instance_id="instance-a", status="running", managed=True, ownership="managed"):
        return SimpleNamespace(
            id=instance_id, target_id="target-a", project="chatgpt2api",
            status=status, managed=managed, ownership=ownership,
            console_url="https://console.example", api_url="https://console.example/v1",
        )

    monkeypatch.setattr(
        "extensions.orchestrator.extensions_store.list_instances", lambda _target_id="": [],
    )
    assert manager.resume_access("historical", "target-a") is None

    for candidate in (
        instance(instance_id="replacement-instance"),
        instance(managed=False, ownership=""),
        instance(status="stopped"),
        instance(ownership="unverified"),
    ):
        monkeypatch.setattr(
            "extensions.orchestrator.extensions_store.list_instances",
            lambda _target_id="", candidate=candidate: [candidate],
        )
        assert manager.resume_access("historical", "target-a") is None

    duplicate = instance()
    monkeypatch.setattr(
        "extensions.orchestrator.extensions_store.list_instances",
        lambda _target_id="": [instance(), duplicate],
    )
    assert manager.resume_access("historical", "target-a") is None
    assert manager.resume_access("historical", "target-b") is None


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


def test_cancel_save_failure_still_stops_runner_before_remote_side_effects_continue(tmp_path, monkeypatch):
    class Runner:
        cancelled = False

        def done(self):
            return False

        def cancel(self):
            self.cancelled = True

    manager = ExtensionTaskManager(store_path=tmp_path / "cancel-save-failure.json")
    runner = Runner()
    manager.tasks["cancel"] = task("cancel", "running", phase="prepare")
    manager.runners["cancel"] = runner

    def fail_save(_tasks):
        raise OSError("injected task-store save failure")

    monkeypatch.setattr(manager.store, "save", fail_save)
    with pytest.raises(OSError, match="injected task-store save failure"):
        manager.cancel("cancel")
    assert runner.cancelled is True
    assert manager.get("cancel")["status"] == "cancelled"
    assert manager.get("cancel")["recovery_action"] == (
        "inspect_owned_partial_deployment_and_regenerate_plan"
    )


@pytest.mark.parametrize(("phase", "expected"), [
    ("connect", None),
    ("docker", None),
    ("prepare", "inspect_owned_partial_deployment_and_regenerate_plan"),
    ("pull", "inspect_owned_instance_and_regenerate_plan"),
    ("start", "inspect_owned_instance_and_regenerate_plan"),
    ("verify", "inspect_owned_instance_and_regenerate_plan"),
])
def test_cancel_persists_phase_aware_owned_resource_guidance(tmp_path, phase, expected):
    class Runner:
        def done(self):
            return False

        def cancel(self):
            pass

    path = tmp_path / f"cancel-{phase}.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks[phase] = task(phase, "running", phase=phase)
    manager.runners[phase] = Runner()

    assert manager.cancel(phase) is True
    assert manager.get(phase)["recovery_action"] == expected
    assert json.loads(path.read_text(encoding="utf-8"))["tasks"][0]["recovery_action"] == expected


def test_concurrent_delivery_consumption_has_one_winner(tmp_path):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks["delivery"] = task("delivery", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["delivery"] = {
        "deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID,
        "admin_key": "thread-safe-delivery",
        "instance": {
            "handle": "i-" + "c" * 32, "project": "chatgpt2api", "managed": True,
            "running": True, "console_url": "http://service.example",
            "api_url": "http://service.example/v1",
        },
    }
    manager._persist()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(
            lambda _: manager.take_delivery("delivery", DEPLOYMENT_ATTEMPT_ID), range(8),
        ))

    assert sum(result is not None and result["admin_key"] == "thread-safe-delivery" for result in results) == 1
    assert results.count(None) == 7
    assert "result" not in manager.get("delivery")
    assert manager.get("delivery")["recovery_action"] == "reverify_ownership_and_rotate_admin_key"


def test_delivery_save_failure_restores_one_time_value_and_public_state(tmp_path, monkeypatch):
    manager = ExtensionTaskManager(store_path=tmp_path / "delivery-save-failure.json")
    manager.tasks["delivery"] = task("delivery", recovery_action=None)
    delivery = {
        "deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID,
        "admin_key": "retryable-one-time-key",
        "instance": {
            "handle": "i-" + "e" * 32, "project": "chatgpt2api", "managed": True,
            "running": True, "console_url": "https://console.example",
            "api_url": "https://console.example/v1",
        },
    }
    manager.deliveries["delivery"] = copy.deepcopy(delivery)
    before = manager.get("delivery")
    real_save = manager.store.save

    def fail_save(_tasks):
        raise OSError("injected delivery save failure")

    monkeypatch.setattr(manager.store, "save", fail_save)
    with pytest.raises(OSError, match="injected delivery save failure"):
        manager.take_delivery("delivery", DEPLOYMENT_ATTEMPT_ID)
    assert manager.deliveries["delivery"] == delivery
    assert manager.get("delivery") == before

    monkeypatch.setattr(manager.store, "save", real_save)
    expected = copy.deepcopy(delivery)
    expected.pop("deployment_attempt_id")
    assert manager.take_delivery("delivery", DEPLOYMENT_ATTEMPT_ID) == expected


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
    manager.resume_bindings["done-00"] = {"opaque": "pruned-binding"}
    manager.runners["done-00"] = Runner()
    manager._persist()

    assert "done-00" not in manager.tasks
    assert "done-00" not in manager.deliveries
    assert "done-00" not in manager.resume_bindings
    assert "done-00" not in manager.runners
    assert manager.take_delivery("done-00", DEPLOYMENT_ATTEMPT_ID) is None


def test_done_runner_reference_is_removed_after_task_finishes(tmp_path, monkeypatch):
    async def fake_run(_task_id, _request, _plan):
        return None

    async def run():
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        monkeypatch.setattr(manager, "_run", fake_run)
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
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
    manager.deliveries["completed"] = {
        "deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID,
        "admin_key": "completed-delivery",
        "instance": {
            "handle": "i-" + "d" * 32, "project": "chatgpt2api", "managed": True,
            "running": True, "console_url": "http://service.example",
            "api_url": "http://service.example/v1",
        },
    }
    manager._persist()
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    assert client.post("/api/extensions/tasks/completed/cancel").status_code == 409
    assert manager.get("completed")["status"] == "completed"
    delivery = client.post(
        "/api/extensions/tasks/completed/delivery",
        json={"deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID},
    )
    assert delivery.status_code == 200
    assert delivery.json()["admin_key"] == "completed-delivery"


def test_cancelled_task_never_delivers_even_if_key_was_injected(tmp_path):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks["cancelled"] = task("cancelled", "cancelled", result={
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    }, recovery_action="inspect_owned_instance_and_regenerate_plan")
    manager.deliveries["cancelled"] = "injected-delivery"
    manager._persist()

    assert manager.take_delivery("cancelled", DEPLOYMENT_ATTEMPT_ID) is None
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
        return Connection(), TEST_HOST_KEY

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
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
        assert "result" not in manager.get(task_id)
        assert manager.get(task_id)["recovery_action"] == "inspect_owned_instance_and_regenerate_plan"
        assert manager.resource_reservations.active_count == 0
        persisted = json.loads((tmp_path / "extension_tasks.json").read_text(encoding="utf-8"))
        assert persisted["tasks"][0]["status"] == "cancelled"
        assert persisted["tasks"][0]["recovery_action"] == "inspect_owned_instance_and_regenerate_plan"

    asyncio.run(run())


def test_new_deployment_task_initializes_structured_failure_fields(tmp_path, monkeypatch):
    release = asyncio.Event()

    async def fake_run(_task_id, _request, _plan):
        await release.wait()

    async def run():
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        monkeypatch.setattr(manager, "_run", fake_run)
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="test-only"), confirmed_plan_id="structured-init",
        )
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        state = manager.get(task_id)
        assert state["failed_phase"] is None
        assert state["error_code"] is None
        assert state["recovery_action"] is None
        assert state["evidence_manifest"]["contract_version"] == "phase4-v3"
        assert state["evidence_manifest"]["complete"] is True
        persisted = (tmp_path / "extension_tasks.json").read_text(encoding="utf-8")
        for forbidden in (
            "/home/ubuntu/genbox-apps", "ghcr.io/yukkcat/chatgpt2api:latest",
            "host.example", "port_bindings", "execution_snapshot", "path_requirements",
        ):
            assert forbidden not in persisted
        release.set()
        await manager.runners[task_id]

    asyncio.run(run())


def test_post_cas_store_failure_consumes_plan_without_task_runner_or_remote_write(tmp_path, monkeypatch):
    target = ExtensionTarget(
        id="t", name="VPS", host="host.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
        chatgpt2api_port=33010,
    )
    request = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
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
    assert plan["id"] not in plan_manager.plans
    with pytest.raises(DeploymentPlanUnavailableError):
        plan_manager.lease(plan["id"], request)
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
        return Connection(), TEST_HOST_KEY

    privileges = {
        "auth_kind": "password", "elevation_contract": "none", "is_root": False,
        "docker_access": True, "elevated_docker_access": False,
        "passwordless_sudo": False, "password_sudo": False,
        "can_admin": False, "can_deploy": True, "diagnostic_code": "legacy_discovery",
    }
    discovery = {
        "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY,
        "environment": {
            "docker_version": "27.0", "compose_version": "2.30",
            "home_dir": "/home/deploy-user", "listening_ports": [],
            "tcp_listeners": [],
            "listening_ports_probe": {
                "status": 0, "complete": True, "payload_present": True,
            },
            "disk_free_mb": 5000,
        },
        "privileges": privileges,
        "instances": [],
        "path_conditions_version": "phase4-v3",
        "path_conditions": {
            "target_install_dir_absent": True,
            "target_install_parent_claimable": True,
            "target_data_dir_nonoverlap": True,
            "target_compose_project_nonoverlap": True,
            "target_port_unoccupied": True,
        },
    }
    target = ExtensionTarget(
        id="shared-target", name="VPS", host="host.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
        chatgpt2api_port=33010,
    )
    credential = SSHCredential(password="concurrency-test-only")
    plan_manager = DeploymentPlanManager()
    plan_request = ExtensionPlanRequest(
        target=target, credential=credential, instance_id="shared-app", service_port=33010,
    )
    first_plan = plan_manager.create(plan_request, discovery)
    second_plan = plan_manager.create(plan_request, discovery)
    first_request = ExtensionDeployRequest(
        deployment_attempt_id="11111111111111111111111111111111",
        target=target, credential=credential, instance_id="shared-app",
        confirmed_plan_id=first_plan["id"],
    )
    second_request = first_request.model_copy(update={
        "deployment_attempt_id": "22222222222222222222222222222222",
        "confirmed_plan_id": second_plan["id"],
    })
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
        return Connection(), TEST_HOST_KEY

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
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
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
            "&& mkdir /home/deploy-user/genbox-apps/chatgpt2api/atomic-app"
        ]
        assert not any(fragment in command for command in commands for fragment in (
            "base64 -d >", "docker pull ", "docker tag ", "cp -a ", "rm -f ",
            "compose.yml up -d", "compose.yml down", ".genbox-instance", "curl -fsS",
        ))
        assert manager.resource_reservations.active_count == 0

    asyncio.run(run())


def test_ownership_marker_is_verified_before_data_config_image_or_compose_mutation(tmp_path, monkeypatch):
    class Result:
        def __init__(self, exit_status=0, stdout=""):
            self.exit_status = exit_status
            self.stdout = stdout

    class Instance:
        def model_dump(self):
            return {"id": "marker-app", "target_id": "marker-target", "managed": True}

    commands = []

    class Connection:
        async def run(self, command, check=False, **kwargs):
            commands.append(command)
            if command == 'printf %s "$HOME"':
                return Result(stdout="/home/deploy-user")
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), TEST_HOST_KEY

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
        monkeypatch.setattr("extensions.orchestrator.extensions_store.upsert_instance", lambda _record: Instance())
        manager = ExtensionTaskManager(store_path=tmp_path / "marker-order.json")
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=ExtensionTarget(
                id="marker-target", name="VPS", host="host.example",
                username="deploy-user", chatgpt2api_port=33010,
            ),
            credential=SSHCredential(password="marker-test-only"),
            instance_id="marker-app", confirmed_plan_id="marker-plan",
        )
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        await manager.runners[task_id]
        assert manager.get(task_id)["status"] == "completed"

        claim_index = next(i for i, command in enumerate(commands) if "&& mkdir /home/deploy-user/genbox-apps/chatgpt2api/marker-app" in command)
        marker_write_index = next(i for i, command in enumerate(commands) if "base64 -d > /home/deploy-user/genbox-apps/chatgpt2api/marker-app/.genbox-instance" in command)
        marker_read_index = next(
            i for i, command in enumerate(commands)
            if command.startswith("python3 -c ") and "/marker-app/.genbox-instance" in command
        )
        data_index = next(i for i, command in enumerate(commands) if command == "umask 077; mkdir /home/deploy-user/genbox-apps/chatgpt2api/marker-app/data")
        config_index = next(i for i, command in enumerate(commands) if "base64 -d > /home/deploy-user/genbox-apps/chatgpt2api/marker-app/compose.yml" in command)
        assert claim_index < marker_write_index < marker_read_index < data_index < config_index
        assert "/marker-app/data" not in commands[claim_index]

    asyncio.run(run())


def test_tampered_marker_stops_before_owned_mutation(tmp_path, monkeypatch):
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
            if command.startswith("python3 -c ") and "/marker-app/.genbox-instance" in command:
                return Result(exit_status=1)
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), TEST_HOST_KEY

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
        manager = ExtensionTaskManager(store_path=tmp_path / "marker-tamper.json")
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=ExtensionTarget(
                id="marker-target", name="VPS", host="host.example",
                username="deploy-user", chatgpt2api_port=33010,
            ),
            credential=SSHCredential(password="marker-test-only"),
            instance_id="marker-app", confirmed_plan_id="marker-plan",
        )
        request, _plan_manager, _plan = prepare_deployment_plan(monkeypatch, request)
        task_id = await manager.create(request)
        await manager.runners[task_id]

        state = manager.get(task_id)
        assert state["status"] == "failed"
        assert state["error_code"] == "preparation_failed"
        assert any(".genbox-instance" in command for command in commands)
        assert not any(fragment in command for command in commands for fragment in (
            "/marker-app/data", "/marker-app/compose.yml", "/marker-app/.env",
            "/marker-app/config.json", "docker pull ", "docker compose ", "cp -a ",
        ))

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
            return None, TEST_HOST_KEY
        return Connection(), TEST_HOST_KEY

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        if scenario == "registration":
            monkeypatch.setattr("extensions.orchestrator.extensions_store.upsert_instance", lambda _record: (_ for _ in ()).throw(OSError("C:/secret/path")))
        else:
            monkeypatch.setattr("extensions.orchestrator.extensions_store.upsert_instance", lambda _record: Instance())
        manager = ExtensionTaskManager(store_path=tmp_path / f"{scenario}.json")
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
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
        assert "result" not in state
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
            return Connection(), TEST_HOST_KEY
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        manager = ExtensionTaskManager(store_path=tmp_path / "close-errors.json")
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
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
  if (url.includes('/delivery')) return {ok:false,status:404,text:async()=>JSON.stringify({detail:'not available'})};
  let body = {};
  if(url === '/api/extensions/vault/status') body = {configured:true,unlocked:true,entry_count:1};
  else if(url === '/api/extensions/vault/credentials') body = {credentials:[{instance_handle:'managed-one'}]};
  else if(url === '/api/extensions/instances') body = {instances:[{handle:'managed-one',project:'chatgpt2api',managed:true,running:true}]};
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


def test_first_and_post_consumption_refresh_never_claim_and_target_scoped_network_resume_works_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
let source = fs.readFileSync(process.argv[1], 'utf8');
const marker=source.lastIndexOf('})();');
source=source.slice(0,marker)+`window.__resumeState=function(){return currentDeployment};`+source.slice(marker);
(async () => {
const elements = new Map();
function element(id){
  if(!elements.has(id)){
    const classes=new Set(id==='extHandoff'?['hidden']:[]);
    const item={style:{},value:'',textContent:'',innerHTML:'',href:'',readOnly:false,placeholder:'',dataset:{},
      classList:{toggle(name,on){if(on)classes.add(name);else classes.delete(name)},add(name){classes.add(name)},remove(name){classes.delete(name)},contains(name){return classes.has(name)}},
      querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(name,value){this[name]=value},removeAttribute(name){this[name]=''}};
    elements.set(id,item);
  }
  return elements.get(id);
}
    let nextStep = 0;
    let deliveryCalls = 0;
    let resumeChecks = 0;
    let resumeAllowed = true;
let sshCalls = 0;
const completed={id:'delivery-task',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',label:'Verify service',status:'success'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:'reverify_ownership_and_rotate_admin_key',failed_phase:null,error_code:null,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]}};
const summary={active_task_id:null,latest_task_id:'delivery-task',tasks:[completed]};
global.window=global;
global.document={getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=key=>key;
global.getUiLanguage=()=> 'en';
global.escHtml=value=>String(value||'');
global.extensionNext=step=>{nextStep=step};
global.clearInterval=()=>{};
global.setInterval=()=>({});
global._authFetch=async (url,options={})=>{
  let body={};
  if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}]};
  else if(url==='/api/extensions/catalog')body={categories:[],items:[]};
  else if(url==='/api/extensions/targets/batch')body={target_ids:[]};
      else if(url==='/api/extensions/tasks')body=summary;
      else if(url==='/api/extensions/tasks/delivery-task/resume'){
        resumeChecks+=1;
        if(options.method!=='POST'||options.headers['Content-Type']!=='application/json')throw new Error('resume was not a JSON POST');
        const request=JSON.parse(options.body);
        if(Object.keys(request).length!==1||request.target_id!=='saved')throw new Error('resume target body mismatch');
        body=resumeAllowed?{resumable:true,instance:{handle:'i-'+"a".repeat(32),project:'chatgpt2api',managed:true,running:true,console_url:'https://first.example',api_url:'https://first.example/v1'}}:{resumable:false};
      }
      else if(url==='/api/extensions/tasks/delivery-task/delivery'){
        deliveryCalls+=1;
        body={admin_key:'one-time-key',shown_once:true,instance:{handle:'i-'+"a".repeat(32),project:'chatgpt2api',managed:true,running:true,console_url:'https://console.example',api_url:'https://console.example/v1'}};
  }
  else if(url==='/api/extensions/ssh/test')sshCalls+=1;
  return {ok:true,text:async()=>JSON.stringify(body)};
};
eval(source);
window.extensionLoadServices=async()=>{};
const originalNext=window.extensionNext;
    window.extensionNext=step=>{nextStep=step;return originalNext(step)};
    await window.loadExtensions();
    if(deliveryCalls!==0)throw new Error('refresh auto-claimed a one-time delivery');
    if(element('extAdminKey').value||!element('extHandoff').classList.contains('hidden'))throw new Error('refresh exposed delivery content');
    if(!element('extensionMessage').textContent.includes('extensions.recovery_rotate_admin_key'))throw new Error('refresh did not show safe key recovery');
    await window.extensionLoadTarget('saved');
    if(resumeChecks!==1||nextStep!==3)throw new Error('selected target did not enable exact network resume');
    if(!window.__resumeState()||window.__resumeState().instance_handle!=='i-'+"a".repeat(32))throw new Error('validated opaque instance was not bound');
    resumeAllowed=false;
    await window.loadExtensions();
    if(deliveryCalls!==0)throw new Error('later refresh auto-claimed a one-time delivery');
    if(resumeChecks!==2||window.__resumeState()!==null)throw new Error('failed exact validation retained or fabricated a deployment');
    if(nextStep!==3||sshCalls!==0)throw new Error('exact completion resume changed steps or triggered SSH');
if(source.includes('/api/extensions/instances?target_id='))throw new Error('resume still infers ownership from target instance listing');
if(source.includes('localStorage'))throw new Error('delivery flow uses localStorage');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_initiating_tab_claims_show_once_key_with_exact_attempt_only_once_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');let source=fs.readFileSync(process.argv[1],'utf8');const marker=source.lastIndexOf('})();');
source=source.slice(0,marker)+`window.__test={renderTask,setTarget(){currentTargetId='saved';targetDirty=false}};`+source.slice(marker);
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(id==='extHandoff'?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(n,v){this[n]=v},removeAttribute(n){this[n]=''}})}return elements.get(id)}
let calls=0,nextStep=0;const attempt='a'.repeat(32),completed={id:'owned-task',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',label:'Verify service',status:'success'}],recovery_action:'reverify_ownership_and_rotate_admin_key'};
global.window=global;global.document={getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
global._authFetch=async(url,options={})=>{if(url!=='/api/extensions/tasks/owned-task/delivery')throw new Error('unexpected request '+url);calls+=1;const claim=JSON.parse(options.body);if(claim.deployment_attempt_id!==attempt||Object.keys(claim).length!==1)throw new Error('claim proof mismatch');return {ok:true,status:200,text:async()=>JSON.stringify({admin_key:'one-time-key',shown_once:true,instance:{handle:'i-'+"a".repeat(32),project:'chatgpt2api',managed:true,running:true,console_url:'https://console.example',api_url:'https://console.example/v1'}})}};
eval(source);window.extensionNext=step=>{nextStep=step};window.__test.setTarget();
(async()=>{await Promise.all([window.__test.renderTask(completed,'owned-task',false,attempt),window.__test.renderTask(completed,'owned-task',false,attempt)]);if(calls!==1)throw new Error('initiator claimed delivery more than once');if(element('extAdminKey').value!=='one-time-key'||element('extHandoff').classList.contains('hidden')||nextStep!==5)throw new Error('initiator did not receive show-once key')})().catch(error=>{console.error(error.stack||error);process.exit(1)});
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
  if (url.includes('/delivery')) return {ok:false,status:404,text:async()=>JSON.stringify({detail:'not available'})};
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
const fullTask = (id, status, recovery_action='regenerate_plan_and_reprovide_credentials', failed_phase=null, error_code=null) => ({id,status,phase:failed_phase||'verify',progress:10,steps:[{id:'connect',label:'Connect',status:'success'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action,failed_phase,error_code,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]}});
const active = fullTask('active', 'running');
const latest = fullTask('latest', 'completed', 'reverify_ownership_and_rotate_admin_key');
summary = { active_task_id: 'active', latest_task_id: 'latest', tasks: [latest, active] };
details['/api/extensions/tasks/active'] = active;
await window.loadExtensions();
if (timers.length !== 1 || timers[0].ms !== 800) throw new Error('active polling was not started');
await timers[0].fn();
if (!calls.includes('/api/extensions/tasks/active')) throw new Error('active task was not polled');
if (cleared.includes(timers[0])) throw new Error('active polling callback failed');
details['/api/extensions/tasks/active'] = fullTask('active', 'failed', 'check_image_access_and_regenerate_plan', 'pull', 'image_prepare_failed');
await timers[0].fn();
if (!cleared.includes(timers[0])) throw new Error('live failed task did not stop polling');
if (!element('extensionMessage').textContent.includes('extensions.deploy_error_image_prepare_failed') || !element('extensionMessage').textContent.includes('extensions.deploy_recovery_check_image_access_and_regenerate_plan')) throw new Error('live structured failure was not localized');
if (element('extensionMessage').textContent.includes('raw backend detail')) throw new Error('raw failed-task error was rendered');
const timerCount = timers.length;
const interrupted = fullTask('interrupted', 'interrupted');
    summary = { active_task_id: null, latest_task_id: 'interrupted', tasks: [interrupted] };
    await window.loadExtensions();
    if (timers.length !== timerCount || !cleared.includes(timers[0]) || !element('extensionMessage').textContent.includes('extensions.recovery_regenerate_plan')) throw new Error('interrupted recovery was not rendered');
    const cancelled = fullTask('cancelled', 'cancelled', 'inspect_owned_instance_and_regenerate_plan');
    summary = { active_task_id: null, latest_task_id: 'cancelled', tasks: [cancelled] };
    await window.loadExtensions();
    if (!element('extensionMessage').textContent.includes('extensions.deploy_recovery_inspect_owned_instance_and_regenerate_plan')) throw new Error('post-write cancellation recovery was not rendered');
    const restoredFailed = fullTask('restored-failed', 'failed', 'verify_owned_instance_stopped_before_retry', 'verify', 'service_verification_failed');
summary = { active_task_id: null, latest_task_id: 'restored-failed', tasks: [restoredFailed] };
await window.loadExtensions();
if (!element('extensionMessage').textContent.includes('extensions.deploy_recovery_verify_owned_instance_stopped_before_retry')) throw new Error('restored structured failure was not rendered');
const legacyFailed = { ...fullTask('legacy-failed', 'failed'), failed_phase: undefined, error_code: undefined, recovery_action: undefined };
summary = { active_task_id: null, latest_task_id: 'legacy-failed', tasks: [legacyFailed] };
await window.loadExtensions();
if (!element('extensionMessage').textContent.includes('extensions.deploy_failure_unknown_reason') || !element('extensionMessage').textContent.includes('extensions.deploy_failure_unknown_recovery')) throw new Error('legacy failed task did not use safe fallback');
const unknownFailed = fullTask('unknown-failed', 'failed', 'raw_unknown_action', 'raw_unknown_phase', 'raw_unknown_code');
summary = { active_task_id: null, latest_task_id: 'unknown-failed', tasks: [unknownFailed] };
await window.loadExtensions();
if (element('extensionMessage').textContent.includes('raw_unknown')) throw new Error('unknown failure enums were rendered');
calls.length = 0;
    const completed = fullTask('completed', 'completed', 'reverify_ownership_and_rotate_admin_key');
    summary = { active_task_id: null, latest_task_id: 'completed', tasks: [completed] };
    await window.loadExtensions();
    if (calls.some(url => url.includes('/delivery'))) throw new Error('restored completed task auto-claimed one-time delivery');
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
  if(url==='/api/extensions/targets'&&options.method==='POST')body={target:{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}};
  else if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}]};
  else if(url==='/api/extensions/catalog')body={categories:[],items:[]};
  else if(url==='/api/extensions/targets/batch')body={target_ids:[]};
  else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:null,tasks:[]};
  else if(url==='/api/extensions/ssh/test'){
    sshCalls+=1;
    return await new Promise(resolve=>{releaseSsh=()=>resolve({ok:true,text:async()=>JSON.stringify({ok:true,host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',privileges:{is_root:true,can_deploy:true}})})});
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


def test_restored_active_task_that_completes_does_not_claim_delivery_without_attempt_proof_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(id==='extHandoff'?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(name,value){this[name]=value},removeAttribute(name){this[name]=''}})}return elements.get(id)}
global.window=global;global.document={getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};
const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};let nextStep=0,deliveryCalls=0;
const running={id:'task-one',status:'running',progress:10,steps:[{id:'connect',status:'running'}],logs:[],result:null};const completed={id:'task-one',status:'completed',progress:100,steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',managed:true},url:'http://console.example',api_url:'http://console.example/v1',admin_key_available:true}};let task=running;
global._authFetch=async url=>{let body={};if(url==='/api/extensions/targets')body={targets:[]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:'task-one',latest_task_id:'task-one',tasks:[running]};else if(url==='/api/extensions/tasks/task-one')body=task;else if(url==='/api/extensions/tasks/task-one/delivery'){deliveryCalls+=1;body={admin_key:'one-time-key',instance:{handle:'i-'+"b".repeat(32),project:'chatgpt2api',managed:true,running:true,console_url:'https://console.example',api_url:'https://console.example/v1'}}}return {ok:true,text:async()=>JSON.stringify(body)}};
    eval(source);window.extensionLoadServices=async()=>{};window.extensionNext=step=>{nextStep=step};await window.loadExtensions();if(timers.length!==1)throw new Error('active poller missing');task=completed;await Promise.all([timers[0](),timers[0]()]);if(deliveryCalls!==0)throw new Error('restored active task claimed delivery without attempt proof');if(nextStep===5)throw new Error('restored task exposed delivery completion');if(element('extAdminKey').value||!element('extHandoff').classList.contains('hidden'))throw new Error('restored task exposed delivery content');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_restored_completion_uses_rotation_guidance_without_delivery_request_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(id==='extHandoff'?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
global.window=global;global.document={getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
    const completed={id:'task-one',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',status:'success'}],recovery_action:'reverify_ownership_and_rotate_admin_key',logs:[],result:{instance:{id:'managed',managed:true},url:'http://console.example',api_url:'http://console.example/v1',admin_key_available:true}};
global._authFetch=async url=>{let body={};if(url==='/api/extensions/targets')body={targets:[]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:'task-one',tasks:[completed]};else if(url==='/api/extensions/tasks/task-one/delivery')return {ok:false,text:async()=>JSON.stringify({detail:'delivery unavailable'})};return {ok:true,text:async()=>JSON.stringify(body)}};
    eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();const output=element('extensionMessage').textContent;if(!output.includes('extensions.recovery_rotate_admin_key'))throw new Error('safe rotation guidance was not shown');if(output.includes('extensions.delivery_failed_prefix'))throw new Error('restore attempted delivery without proof');if(element('extAdminKey').value)throw new Error('restore populated a key');
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
  if(url==='/api/extensions/targets'&&options.method==='POST'){targetSaves+=1;body={target:{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}}}
  else if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved VPS',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}]};
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


def test_completed_public_task_does_not_infer_target_or_host_key_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey','extHandoff'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true,disabled:false,classList:{toggle(){}},focus(){}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const algorithm='ssh-ed25519',fingerprint='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';let target={id:'saved',name:'Saved',host:'safe.example',port:22,username:'ubuntu',host_key_algorithm:'',host_key:'',chatgpt2api_port:33010};let probeCalls=0,confirmCalls=0,sshCalls=0;
const completed={id:'done',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',label:'Verify service',status:'success'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:'reverify_ownership_and_rotate_admin_key',failed_phase:null,error_code:null,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]}};
global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:'done',tasks:[completed]};else if(url==='/api/extensions/network/local/tailscale/status')body={installed:true,online:true,serve:true,serve_port:8893,app_port:8892};else if(url==='/api/extensions/ssh/host-key/probe'){probeCalls+=1;const sent=JSON.parse(options.body);if(Object.keys(sent).join(',')!=='target_id')throw new Error('probe sent credential data');body={target_id:'saved',algorithm,fingerprint};}else if(url==='/api/extensions/ssh/host-key/confirm'){confirmCalls+=1;const sent=JSON.parse(options.body);if(sent.target_id!=='saved'||sent.algorithm!==algorithm||sent.fingerprint!==fingerprint||Object.keys(sent).length!==3)throw new Error('confirm payload was not minimal');target={...target,host_key_algorithm:algorithm,host_key:fingerprint};body={target};}else if(url==='/api/extensions/ssh/test'){sshCalls+=1;return {ok:false,text:async()=>JSON.stringify({detail:'Permission denied for user ubuntu on host safe.example 192.0.2.77'})};}return {ok:true,text:async()=>JSON.stringify(body)}};
const marker=source.lastIndexOf('})();'),instrumented=source.slice(0,marker)+`window.__deploymentState=()=>currentDeployment;`+source.slice(marker);eval(instrumented);window.extensionLoadServices=async()=>{};await window.loadExtensions();if(window.__deploymentState()!==null)throw new Error('opaque completed task inferred deployment target state');const visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();window.extensionSshNext();if(visited.includes(4))throw new Error('opaque completed task bypassed fresh SSH verification');if(probeCalls!==0||confirmCalls!==0||sshCalls!==0)throw new Error('completed task restore triggered a remote identity operation');
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
const algorithm='ssh-ed25519',firstKey='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',secondKey='SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB';const targets=[{id:'one',name:'One',host:'one.example',port:22,username:'ubuntu',host_key_algorithm:'',host_key:'',chatgpt2api_port:3000},{id:'two',name:'Two',host:'two.example',port:22,username:'ubuntu',host_key_algorithm:'',host_key:'',chatgpt2api_port:3000}];let probeCalls=0;global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/probe'){probeCalls+=1;if(probeCalls===1)return await new Promise(resolve=>{releaseProbe=()=>resolve({ok:true,text:async()=>JSON.stringify({target_id:'one',algorithm,fingerprint:firstKey})})});body={target_id:'two',algorithm,fingerprint:secondKey};}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('one');const pending=window.extensionProbeHostKey();await Promise.resolve();window.extensionLoadTarget('two');if(element('extNetworkHostKeyProbeBtn').disabled)throw new Error('new target probe stayed locked after target switch');const second=window.extensionProbeHostKey();releaseProbe();await Promise.all([pending,second]);if(element('extHostKeyAlgorithmValue').textContent!==algorithm||element('extHostKeyFingerprintValue').textContent!==secondKey)throw new Error('new target identity pair was not retained in step 1');if(element('extHostKeyConfirmBtn').disabled)throw new Error('new target identity pair was not confirmable');if(probeCalls!==2)throw new Error('new target could not start its own probe');
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
global.localStorage=new Proxy({}, {get(){throw new Error('host identity touched localStorage')},set(){throw new Error('host identity touched localStorage')}});global.sessionStorage=new Proxy({}, {get(){throw new Error('host identity touched sessionStorage')},set(){throw new Error('host identity touched sessionStorage')}});
const algorithm='ssh-ed25519',fingerprint='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';let target={id:'saved',name:'Saved',host:'safe.example',port:22,username:'ubuntu',host_key_algorithm:'',host_key:'',chatgpt2api_port:3000};const responses=[{algorithm:'',fingerprint},{algorithm:'ssh-dss',fingerprint},{algorithm,fingerprint:'SHA256:short'},{algorithm,fingerprint}];let probeCalls=0,confirmCalls=0;global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/probe')body={target_id:'saved',...responses[probeCalls++]};else if(url==='/api/extensions/ssh/host-key/confirm'){confirmCalls+=1;const sent=JSON.parse(options.body);if(sent.algorithm!==algorithm||sent.fingerprint!==fingerprint)throw new Error('confirm omitted identity pair');target={...target,host_key_algorithm:algorithm,host_key:fingerprint};body={target};}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');if(element('extStepHostKeyBtn').disabled)throw new Error('new target host-key setup was not available');if(element('extTestSshLabel').textContent!=='extensions.ssh_deploy_diagnostic')throw new Error('new deployment SSH action had optional wording');const visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};
window.extensionNext(4);if(element('extNetworkHostKeyValue').textContent!=='extensions.host_key_return_help')throw new Error('step 4 did not direct the user back to step 1');window.extensionReturnHostKeySetup();if(visited.at(-1)!==1)throw new Error('step 4 return action did not open step 1');if(probeCalls!==0)throw new Error('step 4 return action probed before explicit step 1 action');
for(let i=0;i<3;i++){await window.extensionStartHostKeySetup();if(!element('extHostKeyConfirmBtn').disabled)throw new Error('malformed identity pair became confirmable');if(!element('extNetworkConnectBtn').disabled)throw new Error('malformed identity pair unlocked connection');if(!element('extensionMessage').textContent.includes('extensions.host_key_invalid_response'))throw new Error('malformed identity pair did not show safe validation error');}await window.extensionStartHostKeySetup();if(visited.includes(4,1))throw new Error('host-key setup jumped to step 4');if(element('extHostKeyAlgorithmValue').textContent!==algorithm||element('extHostKeyFingerprintValue').textContent!==fingerprint)throw new Error('valid identity pair was not displayed in step 1');await window.extensionConfirmHostKey();if(confirmCalls!==1)throw new Error('valid identity pair was not confirmed exactly once');if(visited.at(-1)!==1)throw new Error('new deployment did not remain in step 1 after host-key confirmation');if(element('extTestSshBtn').disabled===false)throw new Error('SSH test unlocked without session credentials');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_host_key_pairing_ui_mock_round_trip_locks_and_clears_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey','extHostKeyConfirm'].includes(id)?['hidden']:[]);elements.set(id,{id,style:{},value:'',textContent:'',innerHTML:'',disabled:false,checked:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){this.focused=true},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const listeners={};const networkRadio={value:'tailscale',checked:true,classList:{toggle(){}}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(type,fn){(listeners[type]||(listeners[type]=[])).push(fn)},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';let target={id:'saved',name:'Saved',host:'safe.example',port:22,username:'ubuntu',host_key_algorithm:'',host_key:'',chatgpt2api_port:3000};let startCalls=0,completeCalls=0,releaseComplete;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/pair/start'){startCalls+=1;body={pairing_id:'pair-one',expires_at:Date.now()/1000+30,helper_command:'printf pairing'};}else if(url==='/api/extensions/ssh/host-key/pair/complete'){completeCalls+=1;const sent=JSON.parse(options.body);if(sent.response!=='GENBOX-PAIR/1 response')throw new Error('pairing response was not forwarded exactly once');return await new Promise(resolve=>{releaseComplete=()=>resolve({ok:true,text:async()=>JSON.stringify({target:{...target,host_key_algorithm:'ssh-ed25519',host_key:key}})})})}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');await window.extensionStartHostKeyPairing();if(startCalls!==1||element('extHostKeyPairingCommand').value!=='printf pairing')throw new Error('mock pairing command did not render');if(element('extHostKeyPairingCompleteBtn').disabled!==true||element('extHostKeyPairingResponse').disabled!==false)throw new Error('empty pairing response state was not enforced');element('extHostKeyPairingResponse').value='GENBOX-PAIR/1 response';(listeners.input||[]).forEach(fn=>fn({target:element('extHostKeyPairingResponse')}));if(element('extHostKeyPairingCompleteBtn').disabled)throw new Error('valid response did not enable submit');const pending=window.extensionCompleteHostKeyPairing();await Promise.resolve();if(completeCalls!==1||!element('extHostKeyPairingResponse').disabled||!element('extHostKeyPairingCopyBtn').disabled||!element('extHostKeyPairingCancelBtn').disabled)throw new Error('submit did not lock pairing controls');releaseComplete();await pending;if(element('extHostKeyPairingCommand').value!==''||element('extHostKeyPairingResponse').value!==''||!element('extHostKeyPairing').classList.contains('hidden'))throw new Error('successful pairing did not clear transient UI state');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_host_key_pairing_ui_mock_expiry_clears_and_restarts_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey','extHostKeyConfirm'].includes(id)?['hidden']:[]);elements.set(id,{id,style:{},value:'',textContent:'',innerHTML:'',disabled:false,checked:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true,classList:{toggle(){}}};const timers=[];global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=fn=>{timers.push(fn);return fn};
const target={id:'saved',name:'Saved',host:'safe.example',port:22,username:'ubuntu',host_key_algorithm:'',host_key:'',chatgpt2api_port:3000};let starts=0;global._authFetch=async(url)=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/pair/start'){starts+=1;body={pairing_id:'pair-'+starts,expires_at:starts===1?Date.now()/1000-1:Date.now()/1000+30,helper_command:'printf pairing-'+starts};}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');await window.extensionStartHostKeyPairing();if(element('extHostKeyPairingCommand').value!==''||!element('extHostKeyPairingCommandWrap').classList.contains('hidden')||!element('extHostKeyPairingState').classList.contains('error'))throw new Error('expired pairing did not clear command and show recovery');await window.extensionStartHostKeyPairing();if(starts!==2||element('extHostKeyPairingCommand').value!=='printf pairing-2'||element('extHostKeyPairingStartBtn').disabled!==true)throw new Error('expired pairing could not be restarted');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_restored_public_task_does_not_recreate_target_binding_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extNetworkHostKey','extHandoff'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}})}return elements.get(id)}
const networkRadio={value:'tailscale',checked:true,classList:{toggle(){}},focus(){}};global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('input[name="extNetwork"]'))return networkRadio;return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';const targets=[{id:'one',name:'One',host:'one.example',port:22,username:'deploy-one',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:3000},{id:'two',name:'Two',host:'two.example',port:22,username:'deploy-two',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:3000}];const completed={id:'done',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',label:'Verify service',status:'success'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:'reverify_ownership_and_rotate_admin_key',failed_phase:null,error_code:null,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]}};let remoteCalls=0;global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={latest_task_id:'done',tasks:[completed]};else if(url.includes('/api/extensions/ssh/')||url==='/api/extensions/network/connect'){remoteCalls+=1;body={};}return {ok:true,status:url.includes('/delivery')?404:200,text:async()=>JSON.stringify(body)}};
const marker=source.lastIndexOf('})();'),instrumented=source.slice(0,marker)+`window.__deploymentState=()=>currentDeployment;`+source.slice(marker);eval(instrumented);window.extensionLoadServices=async()=>{};await window.loadExtensions();if(window.__deploymentState()!==null)throw new Error('restart recreated a target binding from public task state');window.extensionLoadTarget('two');element('extPassword').value='session-only';window.extensionCredentialChanged();const visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};window.extensionSshNext();if(visited.includes(4))throw new Error('public task restore bypassed target SSH verification');if(remoteCalls!==0)throw new Error('public task restore triggered a remote operation');
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
global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/connect'){connectCalls+=1;return await new Promise(resolve=>{releaseConnect=()=>resolve({ok:true,text:async()=>JSON.stringify({task_id:'network-one'})})})}else if(url==='/api/extensions/network/tasks/network-one')body={status:'failed',progress:20,failed_phase:'remote_network_detect',recovery_action:'confirm VPS Tailscale is online',steps:[{id:'remote_network_detect',status:'failed'}],logs:[],error:'safe failure',diagnostics:{exit_status:0,stdout_present:true,json_parsed:true,json_type:'object',backend_state:'needs_login',cgnat_candidate_count:0}};return {ok:true,text:async()=>JSON.stringify(body)}};
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
let postCalls=0,lastBody=null;global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/connect'){postCalls+=1;lastBody=JSON.parse(options.body);if(postCalls===2)return {ok:false,status:503,text:async()=>JSON.stringify({detail:'temporary'})};body={task_id:postCalls===1?'network-inspect':'network-auto'}}else if(url==='/api/extensions/network/tasks/network-inspect')body={status:'needs_action',phase:'remote_enroll',progress:44,recovery_code:'TAILSCALE_AUTH_KEY_REQUIRED',recovery_action:'need key',next_action:{type:'provide_secret',label_key:'extensions.enter_auth_key',handler:'network_retry'},steps:[{id:'remote_enroll',status:'needs_action'}],logs:[],diagnostics:{}};return {ok:true,text:async()=>JSON.stringify(body)}};
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
let connectCalls=0,releasePost,releasePoll;global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/network/connect'){connectCalls+=1;if(connectCalls===1)return await new Promise(resolve=>{releasePost=()=>resolve({ok:true,text:async()=>JSON.stringify({task_id:'stale-post'})})});body={task_id:'stale-poll'}}else if(url==='/api/extensions/network/tasks/stale-poll')return await new Promise(resolve=>{releasePoll=()=>resolve({ok:true,text:async()=>JSON.stringify({status:'completed',progress:100,steps:[{id:'http_probe',status:'success'}],logs:[],result:{local_address:'100.64.0.1',remote_address:'100.64.0.2',peer_reachable:true,genbox_reachable:true,genbox_url:'http://100.64.0.1:8893'}})})});return {ok:true,text:async()=>JSON.stringify(body)}};
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
global._authFetch=async (url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[{id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',chatgpt2api_port:33010}]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')return {ok:false,text:async()=>JSON.stringify({detail:{error:'安全认证提示',diagnostic:{code:'ssh_auth_rejected',stage:'password_requested',password_requested:true,retry_safe:false},host:'must-not-render',user:'must-not-render',raw:'must-not-render'}})};return {ok:true,text:async()=>JSON.stringify(body)}};
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};
const discovery={ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]},capabilities:{can_deploy:true,can_admin:false,docker_available:true,compose_available:true},instances:[],deployment_modes:[{id:'compose',recommended:true,available:true}]};
const plan={id:'plan-one',ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'b'.repeat(64),complete:true,changed_fields:[]},registers_locally:false,remote_write_expected:true,clone_requested:false,admin_required:false};
    let deployCalls=0,deliveryClaims=0,deployAttemptId='',releaseDeploy;
    global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/discover')body=discovery;else if(url==='/api/extensions/deploy/plan')body={plan,discovery};else if(url==='/api/extensions/deploy'){deployCalls+=1;deployAttemptId=JSON.parse(options.body).deployment_attempt_id;return await new Promise(resolve=>{releaseDeploy=()=>resolve({ok:true,status:200,text:async()=>JSON.stringify({task_id:'deploy-one'})})})}else if(url==='/api/extensions/tasks/deploy-one')body={id:'deploy-one',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',label:'Verify service',status:'success'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:'reverify_ownership_and_rotate_admin_key',failed_phase:null,error_code:null,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'c'.repeat(64),complete:true,changed_fields:[]}};else if(url==='/api/extensions/tasks/deploy-one/delivery'){deliveryClaims+=1;if(JSON.parse(options.body).deployment_attempt_id!==deployAttemptId)throw new Error('delivery claim did not use initiating attempt');body={shown_once:false,instance:{handle:'i-'+"d".repeat(32),project:'chatgpt2api',managed:true,running:true,console_url:'https://console.example',api_url:'https://console.example/v1'}}}else if(url==='/api/extensions/instances')body={instances:[]};return {ok:true,status:200,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);window.extensionNext(2);
if(element('extGuidePrimaryBtn').textContent!=='extensions.discover')throw new Error('step 2 did not begin with discovery');
await window.extensionPrimaryAction();if(element('extGuidePrimaryBtn').textContent!=='extensions.create_plan')throw new Error('discovery did not advance to plan creation');
await window.extensionPrimaryAction();if(element('extGuidePrimaryBtn').textContent!=='extensions.confirm_deploy')throw new Error('plan did not advance to explicit deployment confirmation');
const first=window.extensionPrimaryAction();const second=window.extensionPrimaryAction();for(let i=0;i<8&&!releaseDeploy;i+=1)await Promise.resolve();if(deployCalls!==1)throw new Error('double click created duplicate deployment requests');if(!element('extGuidePrimaryBtn').disabled||element('extGuidePrimaryBtn').textContent!=='status.processing')throw new Error('deployment in flight was not locked');releaseDeploy();await Promise.all([first,second]);if(timers.length!==1)throw new Error('deployment poller was not created once');
    let visited=[];const originalNext=window.extensionNext;window.extensionNext=step=>{visited.push(step);return originalNext(step)};await timers[0]();if(deliveryClaims!==1)throw new Error('initiating flow did not claim its delivery exactly once');if(visited.includes(5)||visited.at(-1)!==3)throw new Error('deployment without one-time key falsely skipped to completion');if(!element('extSuccessBanner').classList.contains('hidden'))throw new Error('success banner appeared before private-network verification');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_lost_deploy_response_retries_exact_attempt_without_adopting_other_tab_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();
function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview','extHandoff','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const radios={network:{value:'tailscale',checked:true,classList:{toggle(){}}},intent:{value:'development',checked:true},strategy:{value:'isolated',checked:true},mode:{value:'compose',checked:true},scope:{value:'empty',checked:true},delivery:{value:'once',checked:true}};
global.window=global;global.document={getElementById:element,querySelector(s){if(s.includes('extNetwork'))return radios.network;if(s.includes('extIntent')&&s.includes(':checked'))return radios.intent;if(s.includes('extStrategy')&&s.includes('[value="isolated"]'))return radios.strategy;if(s.includes('extStrategy')&&s.includes(':checked'))return radios.strategy;if(s.includes('extDeployMode'))return radios.mode;if(s.includes('extCloneScope'))return radios.scope;if(s.includes('extCredentialDelivery'))return radios.delivery;if(s.includes('.extension-pane'))return element('heading');return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'en';global.escHtml=v=>String(v||'');global.crypto={getRandomValues(values){values.fill(0xab);return values}};const timers=[];global.setInterval=fn=>{timers.push(fn);return fn};global.clearInterval=()=>{};
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};
const discovery={ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]},capabilities:{can_deploy:true,can_admin:false,docker_available:true,compose_available:true},instances:[],deployment_modes:[{id:'compose',recommended:true,available:true}]};
const plan={id:'plan-one',ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'b'.repeat(64),complete:true,changed_fields:[]},registers_locally:false,remote_write_expected:true,clone_requested:false,admin_required:false};
const publicManifest={contract_version:'phase4-v3',snapshot_digest:'c'.repeat(64),complete:true,changed_fields:[]};
const unrelatedRunning={id:'unrelated-running',status:'running',phase:'connect',progress:77,steps:[{id:'connect',label:'Connect',status:'running'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:null,failed_phase:null,error_code:null,evidence_manifest:publicManifest};
const unrelatedCompleted={id:'unrelated-completed',status:'completed',phase:'verify',progress:100,steps:[{id:'verify',label:'Verify service',status:'success'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:'reverify_ownership_and_rotate_admin_key',failed_phase:null,error_code:null,evidence_manifest:publicManifest};
let accepted=null,deployCalls=0,taskListReads=0,unrelatedTaskReads=0,unrelatedDeliveryCalls=0,acceptedTaskReads=0,firstDeployBody='';
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks'){taskListReads+=1;body={active_task_id:null,latest_task_id:null,tasks:[unrelatedCompleted,unrelatedRunning]}}else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/discover')body=discovery;else if(url==='/api/extensions/deploy/plan')body={plan,discovery};else if(url==='/api/extensions/deploy'){deployCalls+=1;const sent=JSON.parse(options.body);if(!/^[a-f0-9]{32}$/.test(sent.deployment_attempt_id))throw new Error('deploy attempt id missing or invalid');if(deployCalls===1){firstDeployBody=options.body;accepted={id:'accepted-one',status:'running',phase:'connect',progress:5,steps:[{id:'connect',label:'Connect',status:'running'}],created_at:'2026-07-17T00:00:00.000Z',updated_at:'2026-07-17T00:00:01.000Z',recovery_action:null,failed_phase:null,error_code:null,evidence_manifest:publicManifest};throw new TypeError('response stream lost')}if(options.body!==firstDeployBody)throw new Error('ambiguous retry changed the attempt body');body={task_id:'accepted-one'}}else if(url==='/api/extensions/tasks/accepted-one'){acceptedTaskReads+=1;body=accepted}else if(url==='/api/extensions/tasks/unrelated-running'||url==='/api/extensions/tasks/unrelated-completed'){unrelatedTaskReads+=1;body=url.endsWith('running')?unrelatedRunning:unrelatedCompleted}else if(url==='/api/extensions/tasks/unrelated-completed/delivery'){unrelatedDeliveryCalls+=1;body={admin_key:'must-not-be-read'}}return {ok:true,status:200,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);window.extensionNext(2);await window.extensionDiscover();await window.extensionCreatePlan();
await window.extensionStartDeploy();await window.extensionStartDeploy();
if(deployCalls!==2||!accepted)throw new Error('lost response did not retry the exact accepted attempt');
if(taskListReads!==1)throw new Error('lost response used the task list as an ownership oracle');
if(timers.length!==1)throw new Error('exact attempt retry did not start one task poller');
if(unrelatedTaskReads!==0||unrelatedDeliveryCalls!==0)throw new Error('unrelated task polling or delivery was attempted');
if(element('extProgressPercent').textContent==='77%'||!element('extHandoff').classList.contains('hidden'))throw new Error('unrelated task was rendered');
if(element('extGuideFound').textContent==='extensions.guide_step2_confirmation_failed')throw new Error('ambiguous response falsely claimed plan confirmation blocked the task');
if(element('extensionMessage').textContent.includes('extensions.deploy_confirmation_safe_notice'))throw new Error('ambiguous response falsely claimed no task or VPS change');
await timers[0]();
if(acceptedTaskReads!==1)throw new Error('exact accepted task was not polled once');
if(unrelatedTaskReads!==0||unrelatedDeliveryCalls!==0)throw new Error('unrelated task was touched after exact reconciliation');
})().catch(error=>{console.error(error.stack||error);process.exit(1)});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_frontend_interrupted_no_task_and_bounded_ambiguous_recovery_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');
const marker=source.lastIndexOf('})();');
const instrumented=source.slice(0,marker)+`
window.__test={
  setState(s){
    if('currentPlan' in s)currentPlan=s.currentPlan;
    if('currentDiscovery' in s)currentDiscovery=s.currentDiscovery;
    if('currentExtensionStep' in s)currentExtensionStep=s.currentExtensionStep;
    if('deploymentInFlight' in s)deploymentInFlight=s.deploymentInFlight;
    if('deploymentFailed' in s)deploymentFailed=s.deploymentFailed;
    if('deploymentConfirmationFailed' in s)deploymentConfirmationFailed=s.deploymentConfirmationFailed;
    if('sshVerified' in s)sshVerified=s.sshVerified;
    if('currentTargetId' in s)currentTargetId=s.currentTargetId;
    if('targetDirty' in s)targetDirty=s.targetDirty;
    if('trustedHostKey' in s)trustedHostKey=s.trustedHostKey;
    if('taskPoll' in s)taskPoll=s.taskPoll;
    updateNoviceGuide();
  },
  getState(){return {currentPlan,currentDiscovery,deploymentInFlight,deploymentFailed,deploymentConfirmationFailed,taskPoll,deploymentReconcileUnresolved:typeof deploymentReconcileUnresolved==='undefined'?false:deploymentReconcileUnresolved}},
  reconcileAmbiguousDeployment
};
`+source.slice(marker);
function boot(fetchImpl,cryptoImpl){
  const elements=new Map(),timers=[],cleared=[],probeTimeouts=[],clearedProbeTimeouts=[];
  function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview','extHandoff','extSuccessBanner'].includes(id)?['hidden']:[]);elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',checked:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
  const context={console,Uint8Array,Array,Promise,JSON,Number,String,Object,Math,Set,Map,Error,TypeError,RegExp,Date,AbortController,
    document:{getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}},
    i18nText:k=>k,getUiLanguage:()=> 'en',escHtml:v=>String(v||''),_authFetch:fetchImpl,crypto:cryptoImpl,
    setInterval(fn,ms){const timer={fn,ms};timers.push(timer);return timer},clearInterval(timer){if(timer)cleared.push(timer)},
    setTimeout(fn,ms){const timer={fn,ms};probeTimeouts.push(timer);return timer},clearTimeout(timer){if(timer)clearedProbeTimeouts.push(timer)},
    location:{reload(){context.reloads=(context.reloads||0)+1}},reloads:0
  };
  context.window=context;vm.createContext(context);vm.runInContext(instrumented,context);
  return {context,elements,timers,cleared,element};
}
(async()=>{
  const interrupted={id:'exact-interrupted',status:'interrupted',phase:'connect',progress:10,steps:[{id:'connect',label:'Connect',status:'success'}],failed_phase:null,error_code:null,recovery_action:'regenerate_plan_and_reprovide_credentials',evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:false,changed_fields:['legacy.task_state']}};
  const staleTimer={kind:'stale'};
  const first=boot(async url=>({ok:true,status:200,text:async()=>JSON.stringify(url==='/api/extensions/tasks'?{active_task_id:null,latest_task_id:'exact-interrupted',tasks:[interrupted]}:{})}),{getRandomValues(v){v.fill(1);return v}});
  first.element('extPassword').value='session-only';
  first.context.__test.setState({currentPlan:{id:'plan'},currentDiscovery:{ready:true},currentExtensionStep:2,deploymentInFlight:false,deploymentFailed:false,sshVerified:true,currentTargetId:'saved',targetDirty:false,trustedHostKey:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',taskPoll:staleTimer});
  await first.context.extensionRestoreTask();
  const interruptedState=first.context.__test.getState();
  if(interruptedState.deploymentInFlight||!interruptedState.deploymentFailed||interruptedState.currentPlan!==null)throw new Error('interrupted exact attempt retained processing state or stale plan');
  if(!first.cleared.includes(staleTimer))throw new Error('interrupted exact attempt did not stop the stale timer');
  if(first.element('extGuidePrimaryBtn').disabled||first.element('extGuidePrimaryBtn').textContent!=='extensions.enter_password_button')throw new Error('interrupted exact attempt did not expose credential recovery CTA');
  if(!first.element('extensionMessage').textContent.includes('extensions.task_interrupted')||!first.element('extensionMessage').textContent.includes('extensions.recovery_regenerate_plan'))throw new Error('interrupted exact attempt did not render recovery guidance');

  let deployCalls=0,taskReads=0;
  const noTask=boot(async(url,options={})=>{if(url==='/api/extensions/deploy'){deployCalls+=1;return {ok:false,status:400,text:async()=>JSON.stringify({detail:{error:'sanitized snapshot change',diagnostic:{code:'deployment_snapshot_changed',stage:'fresh_discovery',retry_safe:false,task_created:false}}})}}if(url==='/api/extensions/tasks')taskReads+=1;return {ok:true,status:200,text:async()=>JSON.stringify({tasks:[]})}}, {getRandomValues(v){v.fill(2);return v}});
  Object.assign(noTask.element('extName'),{value:'Saved'});Object.assign(noTask.element('extHost'),{value:'vps.example'});Object.assign(noTask.element('extPort'),{value:'22'});Object.assign(noTask.element('extUsername'),{value:'root'});Object.assign(noTask.element('extServicePort'),{value:'33010'});noTask.element('extPassword').value='session-only';noTask.element('extElevation').value='none';
  noTask.context.__test.setState({currentPlan:{id:'plan',service_port:33010,image:'image:test',instance_id:'app',strategy:'isolated',deployment_mode:'compose',clone_source_id:'',clone_scope:'empty'},currentDiscovery:{ready:true},currentExtensionStep:2,deploymentInFlight:false,deploymentFailed:false,sshVerified:true,currentTargetId:'saved',targetDirty:false,trustedHostKey:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'});
  await noTask.context.extensionStartDeploy();const noTaskMessage=noTask.element('extensionMessage').textContent;await noTask.context.extensionStartDeploy();
  const noTaskState=noTask.context.__test.getState();
  if(deployCalls!==1||taskReads!==0)throw new Error('definitive no-task failure retried or reconciled');
  if(noTaskState.deploymentInFlight||noTaskState.currentPlan!==null||noTaskState.currentDiscovery!==null)throw new Error('definitive snapshot failure did not reset to fresh discovery');
  if(!noTaskMessage.includes('extensions.deploy_snapshot_changed')||!noTaskMessage.includes('extensions.deploy_confirmation_safe_notice'))throw new Error('definitive no-task recovery was not specific and explicit');
  if(noTask.element('extGuidePrimaryBtn').disabled||noTask.element('extGuidePrimaryBtn').textContent!=='extensions.discover')throw new Error('definitive snapshot failure did not expose fresh discovery CTA');

  const ambiguous=boot(async()=>({ok:true,status:200,text:async()=>JSON.stringify({active_task_id:null,latest_task_id:null,tasks:[]})}),{getRandomValues(v){v.fill(3);return v}});
  ambiguous.element('extPassword').value='session-only';
  ambiguous.context.__test.setState({currentPlan:{id:'plan'},currentDiscovery:{ready:true},currentExtensionStep:2,deploymentInFlight:false,deploymentFailed:false,sshVerified:true,currentTargetId:'saved',targetDirty:false,trustedHostKey:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'});
  await ambiguous.context.__test.reconcileAmbiguousDeployment({});
  if(ambiguous.timers.length!==1)throw new Error('ambiguous reconciliation timer was not created');
  for(let i=0;i<8&&!ambiguous.cleared.includes(ambiguous.timers[0]);i+=1)await ambiguous.timers[0].fn();
  const ambiguousState=ambiguous.context.__test.getState();
  if(!ambiguous.cleared.includes(ambiguous.timers[0])||ambiguousState.deploymentInFlight||!ambiguousState.deploymentReconcileUnresolved||ambiguousState.currentPlan!==null)throw new Error('ambiguous reconciliation did not reach a bounded manual state');
  if(!ambiguous.element('extensionMessage').textContent.includes('extensions.deploy_task_reconcile_manual'))throw new Error('bounded ambiguous recovery guidance was not visible');
  if(ambiguous.element('extGuidePrimaryBtn').disabled||ambiguous.element('extGuidePrimaryBtn').textContent!=='common.reload')throw new Error('bounded ambiguous recovery did not expose reload CTA');
})().catch(error=>{console.error(error.stack||error);process.exit(1)});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_ambiguous_deployment_probe_timeout_is_single_flight_and_bounded_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const vm=require('vm');let source=fs.readFileSync(process.argv[1],'utf8');
source=source.replace('var deploymentReconcileProbeTimeoutMs=5000,deploymentReconcileIntervalMs=800;','var deploymentReconcileProbeTimeoutMs=5,deploymentReconcileIntervalMs=1;');
const marker=source.lastIndexOf('})();');
const instrumented=source.slice(0,marker)+`
window.__test={
  setReady(){
    currentPlan={id:'plan',service_port:33010,image:'image:test',instance_id:'app',strategy:'isolated',deployment_mode:'compose',clone_source_id:'',clone_scope:'empty'};
    currentDiscovery={ready:true};currentExtensionStep=2;sshVerified=true;currentTargetId='saved';targetDirty=false;trustedHostKey='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';updateNoviceGuide();
  },
  getState(){return {currentPlan,deploymentInFlight,deploymentReconcileUnresolved,taskPoll}}
};
`+source.slice(marker);
const elements=new Map();
function element(id){if(!elements.has(id)){const classes=new Set();elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',checked:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const nativeSetInterval=setInterval,nativeClearInterval=clearInterval,nativeSetTimeout=setTimeout,nativeClearTimeout=clearTimeout;
const intervals=new Set(),timeouts=new Set();
function trackedSetInterval(fn,ms){const id=nativeSetInterval(fn,ms);intervals.add(id);return id}
function trackedClearInterval(id){if(id)intervals.delete(id);nativeClearInterval(id)}
function trackedSetTimeout(fn,ms){let id=nativeSetTimeout(()=>{timeouts.delete(id);fn()},ms);timeouts.add(id);return id}
function trackedClearTimeout(id){if(id)timeouts.delete(id);nativeClearTimeout(id)}
let deployCalls=0,taskReads=0,activeProbes=0,maxActiveProbes=0,aborts=0;
function fetchImpl(url,options={}){
  if(url==='/api/extensions/deploy'){
    deployCalls+=1;
    if(deployCalls===1)return Promise.reject(new Error('lost response'));
    activeProbes+=1;maxActiveProbes=Math.max(maxActiveProbes,activeProbes);
    return new Promise((resolve,reject)=>{const signal=options&&options.signal;if(signal&&signal.addEventListener)signal.addEventListener('abort',()=>{aborts+=1;activeProbes-=1;const error=new Error('aborted');error.name='AbortError';reject(error)},{once:true})});
  }
  if(url==='/api/extensions/tasks'){
    taskReads+=1;activeProbes+=1;maxActiveProbes=Math.max(maxActiveProbes,activeProbes);
    return new Promise((resolve,reject)=>{
      const signal=options&&options.signal;
      if(signal&&signal.addEventListener)signal.addEventListener('abort',()=>{aborts+=1;activeProbes-=1;const error=new Error('aborted');error.name='AbortError';reject(error)},{once:true});
    });
  }
  return Promise.resolve({ok:true,status:200,text:async()=>JSON.stringify({})});
}
const context={console,Uint8Array,Array,Promise,JSON,Number,String,Object,Math,Set,Map,Error,TypeError,RegExp,Date,AbortController,
  document:{getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}},
  i18nText:k=>k,getUiLanguage:()=> 'en',escHtml:v=>String(v||''),_authFetch:fetchImpl,crypto:{getRandomValues(v){v.fill(4);return v}},
  setInterval:trackedSetInterval,clearInterval:trackedClearInterval,setTimeout:trackedSetTimeout,clearTimeout:trackedClearTimeout,
  location:{reload(){context.reloads=(context.reloads||0)+1}},reloads:0
};
context.window=context;vm.createContext(context);vm.runInContext(instrumented,context);
Object.assign(element('extName'),{value:'Saved'});Object.assign(element('extHost'),{value:'vps.example'});Object.assign(element('extPort'),{value:'22'});Object.assign(element('extUsername'),{value:'root'});Object.assign(element('extServicePort'),{value:'33010'});element('extPassword').value='session-only';element('extElevation').value='none';context.__test.setReady();
const watchdog=nativeSetTimeout(()=>{console.error('never-resolving reconciliation did not terminate');process.exit(1)},1000);
(async()=>{
  await context.extensionStartDeploy();await new Promise(resolve=>nativeSetTimeout(resolve,300));nativeClearTimeout(watchdog);
  const state=context.__test.getState();
  if(deployCalls!==7)throw new Error('ambiguous recovery did not make six bounded exact retries: '+deployCalls);
  if(taskReads!==0||aborts!==6)throw new Error('exact retry timeouts or task-list reads were wrong: reads='+taskReads+' aborts='+aborts);
  if(maxActiveProbes!==1||activeProbes!==0)throw new Error('exact deploy retries overlapped or leaked: max='+maxActiveProbes+' active='+activeProbes);
  if(intervals.size!==0||timeouts.size!==0||state.taskPoll!==null)throw new Error('reconciliation timers or probe cleanup remained active');
  if(state.deploymentInFlight||!state.deploymentReconcileUnresolved||state.currentPlan!==null)throw new Error('timed-out reconciliation did not reach manual terminal state');
  if(!element('extensionMessage').textContent.includes('extensions.deploy_task_reconcile_manual'))throw new Error('manual status guidance was not visible');
  if(element('extGuidePrimaryBtn').disabled||element('extGuidePrimaryBtn').textContent!=='common.reload')throw new Error('manual reload CTA was not enabled');
})().catch(error=>{nativeClearTimeout(watchdog);console.error(error.stack||error);process.exit(1)});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_english_crypto_unavailable_preserves_specific_message_and_zero_deploy_post_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');const marker=source.lastIndexOf('})();');
const instrumented=source.slice(0,marker)+`window.__test={setReady(){currentPlan={id:'plan',service_port:33010,image:'image:test',instance_id:'app',strategy:'isolated',deployment_mode:'compose',clone_source_id:'',clone_scope:'empty'};currentExtensionStep=2;sshVerified=true;currentTargetId='saved';targetDirty=false;trustedHostKey='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';updateNoviceGuide()}};`+source.slice(marker);
const elements=new Map();function element(id){if(!elements.has(id))elements.set(id,{style:{},value:'',textContent:'',innerHTML:'',href:'',disabled:false,readOnly:false,placeholder:'',checked:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(){},add(){},remove(){},contains(){return false}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}});return elements.get(id)}
let deployCalls=0;const context={console,Uint8Array,Array,Promise,JSON,Number,String,Object,Math,Set,Map,Error,TypeError,RegExp,Date,document:{getElementById:element,querySelector(){return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}},i18nText:k=>k,getUiLanguage:()=> 'en',escHtml:v=>String(v||''),_authFetch:async url=>{if(url==='/api/extensions/deploy')deployCalls+=1;return {ok:true,status:200,text:async()=>JSON.stringify({task_id:'unexpected'})}},setInterval(){throw new Error('unexpected timer')},clearInterval(){}};context.window=context;vm.createContext(context);vm.runInContext(instrumented,context);
Object.assign(element('extName'),{value:'Saved'});Object.assign(element('extHost'),{value:'vps.example'});Object.assign(element('extPort'),{value:'22'});Object.assign(element('extUsername'),{value:'root'});Object.assign(element('extServicePort'),{value:'33010'});element('extPassword').value='session-only';element('extElevation').value='none';context.__test.setReady();
(async()=>{await context.extensionStartDeploy();if(deployCalls!==0)throw new Error('crypto-unavailable flow submitted deploy POST');if(element('extensionMessage').textContent!=='extensions.deploy_attempt_unavailable')throw new Error('specific English crypto failure was normalized away: '+element('extensionMessage').textContent)})().catch(error=>{console.error(error.stack||error);process.exit(1)});
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';let target={id:'saved',name:'Saved',host:'authoritative.example',port:2222,username:'deploy',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};
const discovery={ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]},capabilities:{can_deploy:true,can_admin:false,docker_available:true,compose_available:true},instances:[],deployment_modes:[{id:'compose',recommended:true,available:true}]};
const plan={id:'plan-one',ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'b'.repeat(64),complete:true,changed_fields:[]},registers_locally:false,remote_write_expected:true,clone_requested:false,admin_required:false};let targetReads=0,deployCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets'){targetReads+=1;body={targets:[target]}}else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={active_task_id:null,latest_task_id:null,tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/discover')body=discovery;else if(url==='/api/extensions/deploy/plan')body={plan,discovery};else if(url==='/api/extensions/deploy'){deployCalls+=1;target={...target,host:'reloaded-authoritative.example',port:2200,username:'reloaded-user'};return {ok:false,status:409,text:async()=>JSON.stringify({detail:{error:'identity changed',diagnostic:{code:'deployment_plan_identity_mismatch',stage:'plan_confirmation',retry_safe:false}}})}}return {ok:true,status:200,text:async()=>JSON.stringify(body)}};
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};
const discovery={ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]},capabilities:{can_deploy:true,can_admin:false,docker_available:true,compose_available:true},instances:[],deployment_modes:[{id:'compose',recommended:true,available:true}]};
const planBodies=[];
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/deploy/plan'){const request=JSON.parse(options.body);planBodies.push(request);body={discovery,plan:{id:'plan-'+planBodies.length,ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'b'.repeat(64),complete:true,changed_fields:[]},registers_locally:false,remote_write_expected:true,clone_requested:request.clone_scope!=='empty',admin_required:request.clone_scope!=='empty'}}}return {ok:true,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);element('extInstanceId').value='chatgpt2api-dev';element('extServicePort').value='33010';element('extImage').value='image:test';element('extCloneSource').value='';
window.extensionSelectIntent(intent);empty.checked=true;await window.extensionCreatePlan();if(planBodies[0].clone_scope!=='empty')throw new Error('first plan did not submit the explicit empty scope');if(!empty.checked||working.checked)throw new Error('successful empty plan was rendered as working-copy');if(!strategy.checked||element('extCloneSource').value!==''||element('extImage').value!=='image:test')throw new Error('plan rendering changed strategy, source, or image semantics');
await window.extensionCreatePlan();if(planBodies[1].clone_scope!=='empty')throw new Error('regenerated plan did not preserve empty scope');if(!empty.checked||working.checked)throw new Error('regenerated empty plan changed the visible scope');
window.extensionSelectIntent(intent);if(!working.checked||empty.checked)throw new Error('explicit development intent no longer defaults to working-copy');await window.extensionCreatePlan();if(planBodies[2].clone_scope!=='working-copy'||!working.checked||empty.checked)throw new Error('working-copy plan behavior changed');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_snapshot_recovery_preserves_empty_draft_and_hides_stale_panels_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
(async()=>{
const elements=new Map();function element(id){if(!elements.has(id)){const classes=new Set(['extDiscoveryResult','extPlanPreview'].includes(id)?['hidden']:[]);elements.set(id,{id,style:{},value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},options:[],selectedIndex:0,classList:{toggle(n,on){if(on)classes.add(n);else classes.delete(n)},add(n){classes.add(n)},remove(n){classes.delete(n)},contains(n){return classes.has(n)}},querySelector(){return element('nested')},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){},closest(){return null}})}return elements.get(id)}
const groups={};function radio(name,value,checked=false){const input={name,value,_checked:false,dataset:{}};Object.defineProperty(input,'checked',{get(){return this._checked},set(on){this._checked=!!on;if(on)(groups[name]||[]).forEach(other=>{if(other!==this)other._checked=false})}});(groups[name]||(groups[name]=[])).push(input);input.checked=checked;return input}
const intent=radio('extIntent','development',true),strategy=radio('extStrategy','isolated',true),empty=radio('extCloneScope','empty',true),working=radio('extCloneScope','working-copy');radio('extDeployMode','compose',true);radio('extCredentialDelivery','once',true);radio('extNetwork','tailscale',true);
global.window=global;global.document={getElementById:element,querySelector(s){const match=s.match(/input\[name="([^"]+)"\](?:\[value="([^"]+)"\])?/);if(match){const choices=groups[match[1]]||[];if(match[2]!==undefined)return choices.find(input=>input.value===match[2])||null;if(s.includes(':checked'))return choices.find(input=>input.checked)||null;return choices[0]||null}if(s.includes('.extension-pane'))return element('heading');return element('query')},querySelectorAll(){return []},addEventListener(){},removeEventListener(){}};
global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});global.crypto={getRandomValues(v){v.fill(7);return v}};
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33011};
const discovery={ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'a'.repeat(64),complete:true,changed_fields:[]},capabilities:{can_deploy:true,can_admin:false,docker_available:true,compose_available:true},instances:[],deployment_modes:[{id:'compose',recommended:true,available:true}]};
const planBodies=[];let deployCalls=0,discoverCalls=0,taskReads=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks'){taskReads+=1;body={tasks:[]}}else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/discover'){discoverCalls+=1;body=discovery}else if(url==='/api/extensions/deploy/plan'){const request=JSON.parse(options.body);planBodies.push(request);body={discovery,plan:{id:'plan-'+planBodies.length,ready:true,evidence_manifest:{contract_version:'phase4-v3',snapshot_digest:'b'.repeat(64),complete:true,changed_fields:[]},registers_locally:false,remote_write_expected:true,clone_requested:request.clone_scope!=='empty',admin_required:request.clone_scope!=='empty'}}}else if(url==='/api/extensions/deploy'){deployCalls+=1;return {ok:false,status:409,text:async()=>JSON.stringify({detail:{error:'sanitized snapshot change',diagnostic:{code:'deployment_snapshot_changed',stage:'fresh_discovery',retry_safe:false,task_created:false}}})}}return {ok:true,status:200,text:async()=>JSON.stringify(body)}};
eval(source);window.extensionLoadServices=async()=>{};await window.loadExtensions();window.extensionLoadTarget('saved');element('extPassword').value='session-only';window.extensionCredentialChanged();await window.extensionTestSSH(false);window.extensionNext(2);element('extInstanceId').value='chatgpt2api-dev';element('extServicePort').value='33011';element('extImage').value='image:test';element('extCloneSource').value='';
window.extensionSelectIntent(intent);empty.checked=true;await window.extensionCreatePlan();if(planBodies[0].clone_scope!=='empty'||!empty.checked||working.checked)throw new Error('initial plan did not retain explicit empty scope');
await window.extensionStartDeploy();
if(deployCalls!==1||taskReads!==1)throw new Error('definitive no-task failure retried or reconciled');
if(!element('extDeployBtn').disabled)throw new Error('snapshot recovery left deploy enabled');
if(!element('extPlanPreview').classList.contains('hidden')||!element('extDiscoveryResult').classList.contains('hidden'))throw new Error('snapshot recovery left stale plan or discovery visible');
if(!empty.checked||working.checked||!strategy.checked||element('extCloneSource').value!==''||element('extServicePort').value!=='33011'||element('extImage').value!=='image:test')throw new Error('snapshot recovery changed the deployment draft');
if(element('extGuidePrimaryBtn').textContent!=='extensions.discover')throw new Error('snapshot recovery did not require fresh discovery');
await window.extensionDiscover();
if(discoverCalls!==1||!empty.checked||working.checked)throw new Error('fresh discovery overwrote the explicit empty scope');
if(element('extDiscoveryResult').classList.contains('hidden')||!element('extPlanPreview').classList.contains('hidden'))throw new Error('fresh discovery did not replace only the discovery panel');
await window.extensionCreatePlan();
if(planBodies.length!==2||planBodies[1].clone_scope!=='empty')throw new Error('regenerated plan did not preserve explicit empty scope');
if(!empty.checked||working.checked||element('extDeployBtn').disabled||element('extPlanPreview').classList.contains('hidden'))throw new Error('regenerated plan did not restore a reviewable empty plan');
if(deployCalls!==1)throw new Error('recovery automatically retried deployment');
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010},discovery={environment:{},instances:[],deployment_modes:[{id:'compose',name:'Compose',summary:'Recommended',recommended:true,available:true}]};const releases=[];let deployCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/deploy/plan'){const request=JSON.parse(options.body);return await new Promise(resolve=>releases.push(()=>resolve({ok:true,text:async()=>JSON.stringify({discovery,plan:{id:'plan',instance_id:request.instance_id,service_port:request.service_port,image:request.image,strategy:request.strategy,deployment_mode:request.deployment_mode,clone_source_id:request.clone_source_id,clone_scope:request.clone_scope,operations:['prepare'],safety:['isolated'],source_baseline:{}}})})))}else if(url==='/api/extensions/deploy'){deployCalls+=1;body={task_id:'must-not-start'}}return {ok:true,text:async()=>JSON.stringify(body)}};
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
global.i18nText=k=>k;global.getUiLanguage=()=> 'zh-CN';global.escHtml=v=>String(v||'');global.clearInterval=()=>{};global.setInterval=()=>({});const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};let deployCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}};else if(url==='/api/extensions/deploy/plan'){const request=JSON.parse(options.body);body={discovery:{environment:{},instances:[],deployment_modes:[]},plan:{id:'bad-plan',instance_id:request.instance_id,service_port:request.service_port,image:request.image,strategy:request.strategy,deployment_mode:request.deployment_mode,clone_source_id:'',clone_scope:malicious,operations:[],safety:[],source_baseline:{}}}}else if(url==='/api/extensions/deploy'){deployCalls+=1;body={task_id:'must-not-start'}}return {ok:true,text:async()=>JSON.stringify(body)}};
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';let saved={id:'saved',name:'My VPS',host:'vps.example',port:22,username:'root',host_key:'',chatgpt2api_port:33010};let saveCalls=0,probeCalls=0,confirmCalls=0,sshCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets'&&options.method==='POST'){saveCalls+=1;body={target:saved}}else if(url==='/api/extensions/targets')body={targets:[]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/host-key/probe'){probeCalls+=1;body={target_id:'saved',algorithm:'ssh-ed25519',fingerprint:key}}else if(url==='/api/extensions/ssh/host-key/confirm'){confirmCalls+=1;saved={...saved,host_key_algorithm:'ssh-ed25519',host_key:key};body={target:saved}}else if(url==='/api/extensions/ssh/test'){sshCalls+=1;body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:true,can_deploy:true}}}return {ok:true,text:async()=>JSON.stringify(body)}};
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'deploy-user',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};let discoveryCalls=0;
global._authFetch=async(url,options={})=>{let body={};if(url==='/api/extensions/targets')body={targets:[target]};else if(url==='/api/extensions/catalog')body={categories:[],items:[]};else if(url==='/api/extensions/targets/batch')body={target_ids:[]};else if(url==='/api/extensions/tasks')body={tasks:[]};else if(url==='/api/extensions/ssh/test')body={ok:true,host_key_algorithm:'ssh-ed25519',host_key:key,privileges:{is_root:false,docker_access:false,passwordless_sudo:false,password_sudo:false,can_deploy:false,diagnostic_code:'no_sudo_or_docker'}};else if(url==='/api/extensions/discover'){discoveryCalls+=1;body={}}return {ok:true,text:async()=>JSON.stringify(body)}};
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'deploy-user',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};const bodies=[];
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
const key='SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';const target={id:'saved',name:'Saved',host:'vps.example',port:22,username:'root',host_key_algorithm:'ssh-ed25519',host_key:key,chatgpt2api_port:33010};const deployment={id:'done',status:'completed',progress:100,host_key_algorithm:'ssh-ed25519',host_key:key,steps:[{id:'verify',status:'success'}],logs:[],result:{instance:{id:'managed',target_id:'saved',managed:true},url:'http://service.example',api_url:'http://service.example/v1',admin_key_available:false}};
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
