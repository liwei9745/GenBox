import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import extensions.store as extension_store
import main
import sync.push_sources as push_sources
from extensions.orchestrator import public_instance_handle
from extensions.credential_vault import CredentialVault
from sync.ingest import authenticate_push_source


def _managed_instance(tmp_path, monkeypatch):
    monkeypatch.setattr(extension_store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = extension_store.upsert_target({
        "id": "isolated-dev", "name": "Isolated development", "host": "dev.example",
        "username": "root", "network_url": "http://100.64.0.8:8900",
        "network_verified_at": "2026-07-29T12:00:00Z",
    })
    instance = extension_store.upsert_instance({
        "id": "chatgpt2api-dev", "target_id": target.id, "project": "chatgpt2api",
        "service_port": 33010, "install_dir": "/srv/chatgpt2api-dev",
        "data_dir": "/srv/chatgpt2api-dev/data", "image": "example.invalid/app@sha256:" + "a" * 64,
        "managed": True, "ownership": "managed",
    })
    return target, instance, public_instance_handle(target.id, instance.id)


@pytest.fixture
def source_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(push_sources, "PUSH_SOURCES_FILE", tmp_path / "push_sources.json")
    return tmp_path / "push_sources.json"


def test_push_source_registry_persists_only_a_verifier(source_registry):
    source, key = push_sources.create_source("target-a", "chatgpt2api-dev")

    raw = source_registry.read_text(encoding="utf-8")
    assert source["source_id"].startswith("gbxps-")
    assert key.startswith("gpk-")
    assert key not in raw
    assert "key_hash" in raw
    assert push_sources.authenticate_source(source["source_id"], key) is True
    assert push_sources.authenticate_source(source["source_id"], "wrong") is False
    assert push_sources.list_sources("target-a", "chatgpt2api-dev") == [source]


def test_push_source_rotation_and_revocation_disable_old_credentials(source_registry, monkeypatch):
    source, old_key = push_sources.create_source("target-a", "chatgpt2api-dev")
    rotated, new_key = push_sources.rotate_source(source["source_id"], "target-a", "chatgpt2api-dev")

    assert rotated["source_id"] == source["source_id"]
    assert push_sources.authenticate_source(source["source_id"], old_key) is False
    assert push_sources.authenticate_source(source["source_id"], new_key) is True
    assert push_sources.revoke_source(source["source_id"], "target-a", "chatgpt2api-dev") is True
    assert push_sources.authenticate_source(source["source_id"], new_key) is False

    # A tombstone must block a legacy environment mapping with the same ID.
    monkeypatch.setenv("GENBOX_PUSH_KEYS", json.dumps({source["source_id"]: new_key}))
    assert authenticate_push_source(source["source_id"], new_key) is False


def test_unknown_legacy_push_source_stays_compatible(source_registry, monkeypatch):
    monkeypatch.setenv("GENBOX_PUSH_KEYS", '{"legacy-source":"legacy-key"}')

    assert authenticate_push_source("legacy-source", "legacy-key") is True
    assert authenticate_push_source("legacy-source", "wrong") is False


def test_target_revocation_disables_all_of_its_sources(source_registry):
    first, first_key = push_sources.create_source("target-a", "first")
    second, second_key = push_sources.create_source("target-b", "second")

    assert push_sources.revoke_target_sources("target-a") == 1
    assert push_sources.authenticate_source(first["source_id"], first_key) is False
    assert push_sources.authenticate_source(second["source_id"], second_key) is True


def test_invalid_managed_registry_fails_closed_before_legacy_lookup(source_registry, monkeypatch):
    source_registry.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("GENBOX_PUSH_KEYS", '{"legacy-source":"legacy-key"}')

    assert authenticate_push_source("legacy-source", "legacy-key") is False


def test_push_source_api_binds_destination_to_managed_instance(source_registry, tmp_path, monkeypatch):
    target, instance, handle = _managed_instance(tmp_path, monkeypatch)

    created = asyncio.run(main.extension_push_source_create(main.PushSourceProvisionRequest(instance_handle=handle)))
    assert created["instance_handle"] == handle
    assert created["destination_url"] == "http://100.64.0.8:8900/api/sync/push"
    assert created["shown_once"] is True
    assert created["source"]["source_id"].startswith("gbxps-")
    assert created["push_key"].startswith("gpk-")

    status = asyncio.run(main.extension_push_source_status(handle))
    assert status["configured"] is True
    assert status["source"] == created["source"]
    assert "push_key" not in json.dumps(status)

    rotated = asyncio.run(main.extension_push_source_rotate(handle, created["source"]["source_id"]))
    assert authenticate_push_source(created["source"]["source_id"], created["push_key"]) is False
    assert authenticate_push_source(created["source"]["source_id"], rotated["push_key"]) is True
    assert asyncio.run(main.extension_push_source_delete(handle, created["source"]["source_id"])) == {
        "instance_handle": handle, "revoked": True,
    }
    assert authenticate_push_source(created["source"]["source_id"], rotated["push_key"]) is False


def test_push_source_http_routes_show_a_key_only_for_create_or_rotate(source_registry, tmp_path, monkeypatch):
    _target, _instance, handle = _managed_instance(tmp_path, monkeypatch)
    client = TestClient(main.app)

    created = client.post("/api/extensions/push-sources", json={"instance_handle": handle})
    assert created.status_code == 200
    body = created.json()
    assert body["push_key"].startswith("gpk-")

    status = client.get(f"/api/extensions/push-sources/{handle}")
    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert "push_key" not in status.text

    rotated = client.post(
        f"/api/extensions/push-sources/{handle}/{body['source']['source_id']}/rotate"
    )
    assert rotated.status_code == 200
    assert rotated.json()["push_key"].startswith("gpk-")


def test_push_source_api_rejects_raw_or_non_managed_instance_handles(source_registry, tmp_path, monkeypatch):
    target, instance, _handle = _managed_instance(tmp_path, monkeypatch)
    with pytest.raises(main.HTTPException) as raw_error:
        asyncio.run(main.extension_push_source_status(instance.id))
    assert raw_error.value.status_code == 404

    extension_store.upsert_instance({
        "id": "unmanaged", "target_id": target.id, "project": "chatgpt2api",
        "service_port": 33011, "install_dir": "/srv/unmanaged", "data_dir": "/srv/unmanaged/data",
        "image": "example.invalid/app@sha256:" + "b" * 64,
    })
    unmanaged_handle = public_instance_handle(target.id, "unmanaged")
    with pytest.raises(main.HTTPException) as unmanaged_error:
        asyncio.run(main.extension_push_source_status(unmanaged_handle))
    assert unmanaged_error.value.status_code == 404


def test_target_delete_revokes_its_managed_push_source(source_registry, tmp_path, monkeypatch):
    target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    created = asyncio.run(main.extension_push_source_create(main.PushSourceProvisionRequest(instance_handle=handle)))

    assert asyncio.run(main.extension_delete_target(target.id)) == {"deleted": True}
    assert authenticate_push_source(created["source"]["source_id"], created["push_key"]) is False


def test_push_key_vault_opt_in_rotation_and_local_delete(source_registry, tmp_path, monkeypatch):
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    created = asyncio.run(main.extension_push_source_create(main.PushSourceProvisionRequest(instance_handle=handle)))
    assert vault.list_metadata() == []
    saved = asyncio.run(main.extension_vault_save_push_key(handle, main.PushKeyLocalSaveRequest(
        source_id=created["source"]["source_id"], destination_url=created["destination_url"],
        push_key=created["push_key"], save_push_key_locally=True,
    )))
    assert saved == {"saved_locally": True, "remote_unchanged": True}
    assert vault.get(instance.id).genbox_push_key == created["push_key"]
    rotated = asyncio.run(main.extension_push_source_rotate(
        handle, created["source"]["source_id"], main.PushSourceRotateRequest(save_push_key_locally=True)))
    assert vault.get(instance.id).genbox_push_key == rotated["push_key"]
    assert vault.get(instance.id).genbox_push_key != created["push_key"]
    assert asyncio.run(main.extension_vault_delete_push_key(handle)) == {"deleted": True, "remote_unchanged": True}
    assert authenticate_push_source(rotated["source"]["source_id"], rotated["push_key"]) is True
    with pytest.raises(KeyError):
        vault.get(instance.id)


def test_rotation_reports_recoverable_vault_failure_and_allows_retry(source_registry, tmp_path, monkeypatch):
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    created = asyncio.run(main.extension_push_source_create(
        main.PushSourceProvisionRequest(instance_handle=handle)
    ))
    original_upsert = vault.upsert
    calls = 0

    def fail_once(instance_id, credential):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated local vault write failure")
        return original_upsert(instance_id, credential)

    monkeypatch.setattr(vault, "upsert", fail_once)
    rotated = asyncio.run(main.extension_push_source_rotate(
        handle,
        created["source"]["source_id"],
        main.PushSourceRotateRequest(save_push_key_locally=True),
    ))

    assert rotated["remote_rotated"] is True
    assert rotated["push_key"].startswith("gpk-")
    assert rotated["local_save"] == {
        "requested": True,
        "saved": False,
        "pending": True,
        "recovery_action": "save_push_key_locally",
        "error": "vault_save_failed",
    }
    assert authenticate_push_source(created["source"]["source_id"], created["push_key"]) is False
    assert authenticate_push_source(created["source"]["source_id"], rotated["push_key"]) is True
    with pytest.raises(KeyError):
        vault.get(instance.id)

    retried = asyncio.run(main.extension_vault_save_push_key(handle, main.PushKeyLocalSaveRequest(
        source_id=rotated["source"]["source_id"],
        destination_url=rotated["destination_url"],
        push_key=rotated["push_key"],
        save_push_key_locally=True,
    )))
    assert retried == {"saved_locally": True, "remote_unchanged": True}
    assert vault.get(instance.id).genbox_push_key == rotated["push_key"]


def test_push_key_save_rejects_foreign_source_and_wrong_key(source_registry, tmp_path, monkeypatch):
    target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    other = extension_store.upsert_instance({
        "id": "chatgpt2api-other", "target_id": target.id, "project": "chatgpt2api",
        "service_port": 33011, "install_dir": "/srv/chatgpt2api-other",
        "data_dir": "/srv/chatgpt2api-other/data",
        "image": "example.invalid/app@sha256:" + "b" * 64,
        "managed": True, "ownership": "managed",
    })
    other_handle = public_instance_handle(target.id, other.id)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    created = asyncio.run(main.extension_push_source_create(
        main.PushSourceProvisionRequest(instance_handle=handle)
    ))
    foreign = asyncio.run(main.extension_push_source_create(
        main.PushSourceProvisionRequest(instance_handle=other_handle)
    ))

    with pytest.raises(main.HTTPException) as wrong_key:
        asyncio.run(main.extension_vault_save_push_key(handle, main.PushKeyLocalSaveRequest(
            source_id=created["source"]["source_id"],
            destination_url=created["destination_url"],
            push_key="gpk-browser-forged-value",
            save_push_key_locally=True,
        )))
    assert wrong_key.value.status_code == 409

    with pytest.raises(main.HTTPException) as foreign_source:
        asyncio.run(main.extension_vault_save_push_key(handle, main.PushKeyLocalSaveRequest(
            source_id=foreign["source"]["source_id"],
            destination_url=created["destination_url"],
            push_key=foreign["push_key"],
            save_push_key_locally=True,
        )))
    assert foreign_source.value.status_code == 409
    assert vault.list_metadata() == []


def test_locked_vault_leaves_remote_push_key_recoverable_for_retry(source_registry, tmp_path, monkeypatch):
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    vault.lock()
    monkeypatch.setattr(main, "credential_vault", vault)
    created = asyncio.run(main.extension_push_source_create(
        main.PushSourceProvisionRequest(instance_handle=handle)
    ))

    with pytest.raises(main.HTTPException) as locked:
        asyncio.run(main.extension_vault_save_push_key(handle, main.PushKeyLocalSaveRequest(
            source_id=created["source"]["source_id"],
            destination_url=created["destination_url"],
            push_key=created["push_key"],
            save_push_key_locally=True,
        )))
    assert locked.value.status_code == 423
    assert authenticate_push_source(created["source"]["source_id"], created["push_key"]) is True
    assert vault.list_metadata() == []

    vault.unlock("vault-password")
    retried = asyncio.run(main.extension_vault_save_push_key(handle, main.PushKeyLocalSaveRequest(
        source_id=created["source"]["source_id"],
        destination_url=created["destination_url"],
        push_key=created["push_key"],
        save_push_key_locally=True,
    )))
    assert retried == {"saved_locally": True, "remote_unchanged": True}
    assert vault.get(instance.id).genbox_push_key == created["push_key"]


def test_rotation_with_locked_vault_returns_key_and_pending_save_state(source_registry, tmp_path, monkeypatch):
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    vault.lock()
    monkeypatch.setattr(main, "credential_vault", vault)
    created = asyncio.run(main.extension_push_source_create(
        main.PushSourceProvisionRequest(instance_handle=handle)
    ))

    rotated = asyncio.run(main.extension_push_source_rotate(
        handle,
        created["source"]["source_id"],
        main.PushSourceRotateRequest(save_push_key_locally=True),
    ))
    assert rotated["remote_rotated"] is True
    assert rotated["local_save"] == {
        "requested": True,
        "saved": False,
        "pending": True,
        "recovery_action": "save_push_key_locally",
        "error": "vault_locked",
    }
    assert authenticate_push_source(created["source"]["source_id"], created["push_key"]) is False
    assert authenticate_push_source(rotated["source"]["source_id"], rotated["push_key"]) is True

    vault.unlock("vault-password")
    asyncio.run(main.extension_vault_save_push_key(handle, main.PushKeyLocalSaveRequest(
        source_id=rotated["source"]["source_id"],
        destination_url=rotated["destination_url"],
        push_key=rotated["push_key"],
        save_push_key_locally=True,
    )))
    assert vault.get(instance.id).genbox_push_key == rotated["push_key"]


def test_generic_credential_push_update_requires_confirmation_and_current_source_key(source_registry, tmp_path, monkeypatch):
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    created = asyncio.run(main.extension_push_source_create(
        main.PushSourceProvisionRequest(instance_handle=handle)
    ))
    credential = main.ManagedCredential(
        admin_key="managed-admin-key",
        genbox_push_key=created["push_key"],
        genbox_push_source_id=created["source"]["source_id"],
        genbox_push_url=created["destination_url"],
    )

    with pytest.raises(ValueError, match="explicit create or rotation confirmation"):
        main.ManagedCredentialUpsertRequest(credential=credential)

    with pytest.raises(main.HTTPException) as forged:
        asyncio.run(main.extension_vault_upsert(handle, main.ManagedCredentialUpsertRequest(
            credential=credential.model_copy(update={"genbox_push_key": "gpk-browser-forged-value"}),
            push_key_save_confirmed=True,
        )))
    assert forged.value.status_code == 409

    saved = asyncio.run(main.extension_vault_upsert(handle, main.ManagedCredentialUpsertRequest(
        credential=credential,
        push_key_save_confirmed=True,
    )))
    assert "genbox_push_key" in saved["credential"]["fields"]
    assert vault.get(instance.id).genbox_push_key == created["push_key"]
