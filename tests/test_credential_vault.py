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


def test_vault_accepts_ssh_only_managed_credential():
    credential = ManagedCredential(ssh_password="isolated-vps-password")

    assert credential.ssh_password == "isolated-vps-password"


def test_vault_encrypts_genbox_push_configuration(tmp_path):
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    push_key = "gpk-local-test-key-must-not-appear"

    vault.setup("vault-password")
    metadata = vault.upsert(
        "managed-one",
        ManagedCredential(
            genbox_push_key=push_key,
            genbox_push_source_id="gbxps-local-test",
            genbox_push_url="http://127.0.0.1:8900/api/sync/push",
        ),
    )

    raw = vault.path.read_text(encoding="utf-8")
    assert push_key not in raw
    assert "gbxps-local-test" not in raw
    assert metadata["fields"] == [
        "genbox_push_key",
        "genbox_push_source_id",
        "genbox_push_url",
    ]
    saved = vault.get("managed-one")
    assert saved.genbox_push_key == push_key
    assert saved.genbox_push_source_id == "gbxps-local-test"


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
    assert 'ext-credential-box' in html
    assert 'class="ext-modal-close"' in html
    assert "extensionSaveDeliveredCredential" in js
    assert "extensionSaveResetCredential" in js
    assert "extensionOpenCredential" in js
    assert "extensionDeleteCredential" in js
    assert "extensionSavePushConfiguration" in js
    assert "extensionCopySavedPushConfiguration" in js
    assert 'id="extCredentialGenboxPushKey"' in html
    assert "genbox_push_key" in js
    assert "localStorage" not in js


def test_push_copy_keeps_the_key_visible_and_vault_save_is_explicit():
    root = Path(__file__).parents[1]
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    copy_block = js.split("window.extensionCopyPushConfiguration", 1)[1].split(
        "window.extensionRotatePushSource", 1
    )[0]
    assert "key.value=''" not in copy_block
    assert "extensionSavePushConfiguration" in js


def test_push_key_is_not_saved_until_the_user_explicitly_upserts_it(tmp_path):
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    assert vault.list_metadata() == []
    with pytest.raises(KeyError):
        vault.get("managed-one")
    vault.upsert("managed-one", ManagedCredential(
        genbox_push_key="gpk-explicit-opt-in-only",
        genbox_push_source_id="gbxps-explicit",
        genbox_push_url="https://genbox.example/api/sync/push",
    ))
    assert vault.get("managed-one").genbox_push_key == "gpk-explicit-opt-in-only"


def test_locked_vault_blocks_push_key_read_and_local_copy_can_be_deleted(tmp_path):
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    vault.upsert("managed-one", ManagedCredential(
        genbox_push_key="gpk-local-copy-to-remove",
        genbox_push_source_id="gbxps-local-copy",
        genbox_push_url="https://genbox.example/api/sync/push",
    ))
    vault.lock()
    with pytest.raises(PermissionError):
        vault.get("managed-one")
    with pytest.raises(PermissionError):
        vault.delete("managed-one")
    vault.unlock("vault-password")
    assert vault.delete("managed-one") is True
    assert vault.list_metadata() == []


def test_generic_credential_editor_cannot_replace_or_resave_push_configuration():
    root = Path(__file__).parents[1]
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    save_block = js.split("window.extensionSaveCredential", 1)[1].split(
        "window.extensionDeleteCredential", 1
    )[0]

    assert "push_key_save_confirmed:false" in save_block
    assert "genbox_push_key:''" in save_block
    assert "genbox_push_source_id:''" in save_block
    assert "genbox_push_url:''" in save_block
    assert "openPushSaveConfirmation('credential'" not in save_block
    assert 'id="extCredentialGenboxPushKey" type="password" autocomplete="off" readonly' in html
    assert 'id="extCredentialGenboxPushSourceId" autocomplete="off" readonly' in html
    assert 'id="extCredentialGenboxPushUrl" autocomplete="off" readonly' in html
    assert "extensions.push_saved_fields_readonly" in html


def test_saved_credential_modal_has_a_per_field_secret_visibility_control():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    for field in (
        "extCredentialAdminKey",
        "extCredentialSshPassword",
        "extCredentialSshPrivateKey",
        "extCredentialSshPassphrase",
        "extCredentialSudoPassword",
        "extCredentialPassword",
        "extCredentialApiKey",
        "extCredentialGenboxPushKey",
    ):
        assert f"extensionToggleCredentialSecret('{field}',this)" in html

    assert 'class="ext-secret-textarea is-masked"' in html
    assert "window.extensionToggleCredentialSecret=function" in js
    assert "field.classList.remove('is-masked')" in js
    assert "field.classList.add('is-masked')" in js
    assert "extensionRevealCredentialFields" not in html


def test_saved_credential_modal_resets_secret_visibility_when_opening():
    root = Path(__file__).parents[1]
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    open_block = js.split("window.extensionOpenCredential", 1)[1].split(
        "window.extensionCloseCredentialModal", 1
    )[0]
    assert ".type='password'" in open_block
    assert "el('extCredentialSshPrivateKey').classList.add('is-masked')" in open_block


def test_saved_credential_modal_bounds_content_and_keeps_actions_reachable():
    root = Path(__file__).parents[1]
    css = (root / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    assert "max-height:calc(100vh - 40px)" in css
    assert "box-sizing:border-box" in css
    assert ".ext-credential-box .ext-reset-actions{position:sticky" in css
