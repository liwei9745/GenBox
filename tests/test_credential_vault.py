import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from extensions.credential_vault import CredentialVault
from extensions.models import ManagedCredential, ManagedCredentialUpsertRequest, VaultPasswordRequest


def test_vault_encrypts_at_rest_and_roundtrips(tmp_path):
    path = tmp_path / "credentials.vault.json"
    vault = CredentialVault(path)
    secret = "admin-plaintext-must-not-appear"

    assert vault.setup("correct horse battery staple")["unlocked"] is True
    metadata = vault.upsert(
        "chatgpt2api-dev",
        ManagedCredential(admin_key=secret, username="operator", note="local note"),
    )

    raw = path.read_text(encoding="utf-8")
    document = json.loads(raw)
    assert secret not in raw
    assert "operator" not in raw
    assert "local note" not in raw
    assert set(document["entries"]["chatgpt2api-dev"]) == {"ciphertext", "updated_at", "fields"}
    assert metadata["fields"] == ["admin_key", "username", "note"]
    assert vault.get("chatgpt2api-dev").admin_key == secret


def test_vault_wrong_password_stays_locked(tmp_path):
    path = tmp_path / "credentials.vault.json"
    vault = CredentialVault(path)
    vault.setup("correct-password")
    vault.upsert("managed-one", ManagedCredential(password="service-password"))
    vault.lock()

    with pytest.raises(ValueError, match="解锁密码错误"):
        vault.unlock("wrong-password")
    assert vault.status()["unlocked"] is False
    with pytest.raises(PermissionError):
        vault.get("managed-one")


def test_vault_crud_and_metadata_while_locked(tmp_path):
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    vault.upsert("managed-one", ManagedCredential(api_key="api-secret"))
    vault.lock()

    assert vault.list_metadata()[0]["instance_id"] == "managed-one"
    with pytest.raises(PermissionError):
        vault.delete("managed-one")
    vault.unlock("vault-password")
    assert vault.delete("managed-one") is True
    assert vault.list_metadata() == []


def test_vault_models_reject_short_password_and_empty_credential():
    with pytest.raises(ValidationError):
        VaultPasswordRequest(password="short")
    with pytest.raises(ValidationError):
        ManagedCredentialUpsertRequest(credential={"note": "not a credential"})


def test_vault_unlock_sets_running_status(tmp_path):
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("unlock-test-password")
    vault.upsert("chatgpt2api-dev", ManagedCredential(admin_key="gbx-test-key"))
    vault.lock()

    assert vault.status()["unlocked"] is False
    assert vault.status()["configured"] is True
    assert vault.status()["entry_count"] == 1

    vault.unlock("unlock-test-password")
    status = vault.status()
    assert status["unlocked"] is True
    assert status["entry_count"] == 1


def test_vault_unlock_rejects_wrong_password(tmp_path):
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("correct-password")
    vault.upsert("chatgpt2api-dev", ManagedCredential(admin_key="gbx-test-key"))
    vault.lock()

    with pytest.raises(ValueError, match="解锁密码错误"):
        vault.unlock("wrong-password")
    assert vault.status()["unlocked"] is False
    assert vault.status()["entry_count"] == 1


def test_vault_routes_and_frontend_are_wired():
    root = Path(__file__).parents[1]
    main = (root / "main.py").read_text(encoding="utf-8")
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    for route in (
        "/api/extensions/vault/status",
        "/api/extensions/vault/setup",
        "/api/extensions/vault/unlock",
        "/api/extensions/vault/lock",
        "/api/extensions/vault/credentials",
    ):
        assert route in main
    assert 'name="extCredentialDelivery"' in html
    assert 'id="extCredentialModal"' in html
    assert "extensionSaveDeliveredCredential" in js
    assert "extensionSaveResetCredential" in js
    assert "extensionOpenCredential" in js
    assert "extensionDeleteCredential" in js
    assert "localStorage" not in js
