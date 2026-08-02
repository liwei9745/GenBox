import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import extensions.orchestrator as orchestrator
import extensions.store as extension_store
import main
from extensions.models import (
    ManagedCredential,
    ManagedImageUpdateApplyRequest,
    ManagedImageUpdatePlanRequest,
    SSHCredential,
)
from extensions.orchestrator import public_instance_handle


TEST_HOST_KEY = "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
OLD_IMAGE = "registry.example/chatgpt2api@sha256:" + "a" * 64
NEW_IMAGE = "registry.example/chatgpt2api@sha256:" + "b" * 64


def managed_target_and_instance(tmp_path, monkeypatch, *, target_role="isolated-development"):
    monkeypatch.setattr(extension_store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = extension_store.upsert_target({
        "id": "update-target", "name": "Update target", "host": "dev.example",
        "username": "root", "target_role": target_role,
        "host_key_algorithm": "ssh-ed25519", "host_key": TEST_HOST_KEY,
    })
    instance = extension_store.upsert_instance({
        "id": "update-app", "target_id": target.id, "project": "chatgpt2api",
        "strategy": "isolated", "deployment_mode": "compose", "compose_project": "update-app",
        "service_port": 33010, "install_dir": "/srv/update-app", "data_dir": "/srv/update-app/data",
        "image": OLD_IMAGE, "managed": True, "ownership": "managed", "status": "running",
    })
    return target, instance, public_instance_handle(target.id, instance.id)


class Vault:
    def __init__(self, credential):
        self.credential = credential
        self.calls = []

    def get(self, instance_id):
        self.calls.append(instance_id)
        return self.credential


def test_update_plan_rejects_mutable_image_before_vault_or_ssh(tmp_path, monkeypatch):
    _target, _instance, handle = managed_target_and_instance(tmp_path, monkeypatch)
    vault = Vault(ManagedCredential(ssh_password="must-not-read", password="metadata"))
    monkeypatch.setattr(main, "credential_vault", vault)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.extension_managed_image_update_plan(ManagedImageUpdatePlanRequest(
            instance_handle=handle, image="registry.example/chatgpt2api:latest",
        )))

    assert exc.value.status_code == 400
    assert vault.calls == []


def test_update_plan_rejects_production_target_before_vault_or_ssh(tmp_path, monkeypatch):
    _target, _instance, handle = managed_target_and_instance(
        tmp_path, monkeypatch, target_role="production-read-only",
    )
    vault = Vault(ManagedCredential(ssh_password="must-not-read", password="metadata"))
    monkeypatch.setattr(main, "credential_vault", vault)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.extension_managed_image_update_plan(ManagedImageUpdatePlanRequest(
            instance_handle=handle, image=NEW_IMAGE,
        )))

    assert exc.value.status_code == 403
    assert vault.calls == []


def test_update_plan_is_single_use_and_never_returns_vault_secret(tmp_path, monkeypatch):
    _target, instance, handle = managed_target_and_instance(tmp_path, monkeypatch)
    vault = Vault(ManagedCredential(ssh_password="session-secret", password="metadata"))
    monkeypatch.setattr(main, "credential_vault", vault)
    calls = []
    seen_passwords = []

    async def update(**kwargs):
        calls.append(kwargs)
        seen_passwords.append(kwargs["credential"].password)
        return {"health_verified": True}

    monkeypatch.setattr(main, "update_managed_image", update)
    plan = asyncio.run(main.extension_managed_image_update_plan(ManagedImageUpdatePlanRequest(
        instance_handle=handle, image=NEW_IMAGE,
    )))
    serialized_plan = json.dumps(plan)
    assert "session-secret" not in serialized_plan
    assert plan["instance_handle"] == handle
    assert plan["image"] == NEW_IMAGE

    async def apply_and_wait():
        applied = await main.extension_managed_image_update_apply(ManagedImageUpdateApplyRequest(
            plan_id=plan["plan_id"],
        ))
        assert applied["ok"] is True
        assert applied["task_id"]
        for _ in range(20):
            state = main.managed_image_update_tasks.get(applied["task_id"])
            if state and state["status"] == "completed":
                return applied, state
            await asyncio.sleep(0)
        raise AssertionError("managed image update task did not complete")

    applied, state = asyncio.run(apply_and_wait())
    assert state["instance_handle"] == handle
    assert state["image"] == NEW_IMAGE
    assert len(calls) == 1
    assert calls[0]["instance_id"] == instance.id
    assert seen_passwords == ["session-secret"]
    assert calls[0]["credential"].password is None
    assert "session-secret" not in json.dumps(applied)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.extension_managed_image_update_apply(ManagedImageUpdateApplyRequest(
            plan_id=plan["plan_id"],
        )))
    assert exc.value.status_code == 409


class FakeConnection:
    def __init__(self, instance_id, *, marker_matches=True, fail_health=False):
        self.instance_id = instance_id
        self.marker_matches = marker_matches
        self.fail_health = fail_health
        self.commands = []
        self.closed = False

    async def run(self, command, input=None, check=False):
        self.commands.append((command, input))
        if ".genbox-instance" in command:
            marker = {"id": self.instance_id if self.marker_matches else "wrong", "managed": True}
            return SimpleNamespace(exit_status=0, stdout=json.dumps(marker))
        if command.startswith("cat "):
            return SimpleNamespace(exit_status=0, stdout="CHATGPT2API_IMAGE=" + OLD_IMAGE + "\nTOKEN=not-returned\n")
        if "curl -fsS" in command:
            return SimpleNamespace(exit_status=1 if self.fail_health else 0, stdout="")
        return SimpleNamespace(exit_status=0, stdout="")

    def close(self):
        self.closed = True

    async def wait_closed(self):
        return None


def test_update_rejects_marker_mismatch_before_image_pull(tmp_path, monkeypatch):
    target, instance, _handle = managed_target_and_instance(tmp_path, monkeypatch)
    connection = FakeConnection(instance.id, marker_matches=False)

    async def connect(_request):
        return connection, None

    async def privileges(_connection, _credential):
        return {"can_deploy": True, "docker_access": True}

    monkeypatch.setattr(orchestrator, "_connect", connect)
    monkeypatch.setattr(orchestrator, "_diagnose_privileges", privileges)

    with pytest.raises(PermissionError):
        asyncio.run(orchestrator.update_managed_image(
            instance_id=instance.id, target=target, credential=SSHCredential(password="session"), image=NEW_IMAGE,
        ))

    assert not any("docker pull" in command for command, _input in connection.commands)
    assert connection.closed is True


def test_update_task_projection_recovers_inflight_state(tmp_path, monkeypatch):
    manager = main.ManagedImageUpdateTaskManager()
    manager.path = tmp_path / "managed-image-tasks.json"
    manager.tasks = {
        "iu-task-restart": {
            "id": "iu-task-restart", "status": "running", "phase": "update", "progress": 25,
            "instance_handle": "i-" + "a" * 32, "image": NEW_IMAGE,
            "steps": [], "logs": [], "created_at": "2026-08-02T00:00:00Z",
            "updated_at": "2026-08-02T00:00:01Z",
        }
    }
    manager._persist()
    recovered = main.ManagedImageUpdateTaskManager()
    recovered.path = manager.path
    recovered._load()
    state = recovered.get("iu-task-restart")
    assert state["status"] == "interrupted"
    assert "更新任务中断" in state["error"]


def test_update_rolls_back_env_and_keeps_local_image_on_health_failure(tmp_path, monkeypatch):
    target, instance, _handle = managed_target_and_instance(tmp_path, monkeypatch)
    connection = FakeConnection(instance.id, fail_health=True)

    async def connect(_request):
        return connection, None

    async def privileges(_connection, _credential):
        return {"can_deploy": True, "docker_access": True}

    monkeypatch.setattr(orchestrator, "_connect", connect)
    monkeypatch.setattr(orchestrator, "_diagnose_privileges", privileges)

    with pytest.raises(RuntimeError):
        asyncio.run(orchestrator.update_managed_image(
            instance_id=instance.id, target=target, credential=SSHCredential(password="session"), image=NEW_IMAGE,
        ))

    commands = [command for command, _input in connection.commands]
    pull_index = next(index for index, command in enumerate(commands) if "docker pull" in command)
    backup_index = next(index for index, command in enumerate(commands) if "cp /srv/update-app/.env" in command)
    write_index = next(index for index, command in enumerate(commands) if "base64 -d > /srv/update-app/.env" in command)
    health_index = next(index for index, command in enumerate(commands) if "curl -fsS" in command)
    rollback_index = max(index for index, command in enumerate(commands) if "cp /srv/update-app/.env.genbox-image-update-" in command)
    assert pull_index < backup_index < write_index < health_index < rollback_index
    assert extension_store.get_instance(instance.id).image == OLD_IMAGE
