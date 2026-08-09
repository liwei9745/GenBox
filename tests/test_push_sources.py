import asyncio
import json
import subprocess
from pathlib import Path

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


def _push_key_confirmation(client, instance_handle, source_id, push_key):
    response = client.post(
        f"/api/extensions/vault/credentials/{instance_handle}/push-key/confirmation",
        json={"source_id": source_id, "push_key": push_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"confirmation_token", "expires_in_seconds"}
    assert body["expires_in_seconds"] == 120
    return body["confirmation_token"]


def _save_push_key(client, instance_handle, created, confirmation_token="", **extra):
    payload = {
        "source_id": created["source"]["source_id"],
        "destination_url": created["destination_url"],
        "push_key": created["push_key"],
        "confirmation_token": confirmation_token,
        **extra,
    }
    return client.put(
        f"/api/extensions/vault/credentials/{instance_handle}/push-key", json=payload,
    )


def test_push_key_save_requires_server_confirmation_and_never_auto_saves(source_registry, tmp_path, monkeypatch):
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    client = TestClient(main.app)

    created = client.post("/api/extensions/push-sources", json={
        "instance_handle": handle, "save_push_key_locally": True,
    })
    assert created.status_code == 200
    created = created.json()
    assert vault.list_metadata() == []

    # A browser-supplied opt-in flag cannot replace the server confirmation.
    bypass = _save_push_key(client, handle, created, save_push_key_locally=True)
    assert bypass.status_code == 409
    assert vault.list_metadata() == []

    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    saved = _save_push_key(client, handle, created, token)
    assert saved.status_code == 200
    assert saved.json() == {"saved_locally": True, "remote_unchanged": True}
    assert vault.get(instance.id).genbox_push_key == created["push_key"]

    rotated = client.post(
        f"/api/extensions/push-sources/{handle}/{created['source']['source_id']}/rotate",
        json={"save_push_key_locally": True},
    )
    assert rotated.status_code == 200
    rotated = rotated.json()
    assert rotated["local_save"]["requested"] is False
    assert vault.get(instance.id).genbox_push_key != rotated["push_key"]


def test_push_key_confirmation_is_bound_short_lived_and_single_use(source_registry, tmp_path, monkeypatch):
    target, _instance, handle = _managed_instance(tmp_path, monkeypatch)
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
    client = TestClient(main.app)
    created = client.post("/api/extensions/push-sources", json={"instance_handle": handle}).json()

    missing = _save_push_key(client, handle, created, save_push_key_locally=True)
    assert missing.status_code == 409

    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    wrong_key = _save_push_key(client, handle, created, token, push_key="gpk-forged")
    assert wrong_key.status_code == 409

    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    wrong_source = _save_push_key(client, handle, created, token, source_id="gbxps-wrong-source")
    assert wrong_source.status_code == 409

    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    wrong_instance = _save_push_key(client, other_handle, created, token)
    assert wrong_instance.status_code == 409

    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    main._push_key_save_confirmations._records[token]["expires_at"] = 0
    expired = _save_push_key(client, handle, created, token)
    assert expired.status_code == 409

    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    assert _save_push_key(client, handle, created, token).status_code == 200
    replayed = _save_push_key(client, handle, created, token)
    assert replayed.status_code == 409
    assert vault.list_metadata()[0]["instance_id"] != other.id


def test_push_key_confirmation_keeps_vault_failures_recoverable(source_registry, tmp_path, monkeypatch):
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    client = TestClient(main.app)
    created = client.post("/api/extensions/push-sources", json={"instance_handle": handle}).json()

    vault.lock()
    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    locked = _save_push_key(client, handle, created, token)
    assert locked.status_code == 423
    assert vault.list_metadata() == []

    vault.unlock("vault-password")
    original_upsert = vault.upsert
    monkeypatch.setattr(vault, "upsert", lambda *_args: (_ for _ in ()).throw(OSError("write failed")))
    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    failed = _save_push_key(client, handle, created, token)
    assert failed.status_code == 503
    assert vault.list_metadata() == []

    monkeypatch.setattr(vault, "upsert", original_upsert)
    token = _push_key_confirmation(client, handle, created["source"]["source_id"], created["push_key"])
    assert _save_push_key(client, handle, created, token).status_code == 200
    assert vault.get(instance.id).genbox_push_key == created["push_key"]


def test_push_key_local_copy_full_synthetic_lifecycle_preserves_remote_source(
    source_registry, tmp_path, monkeypatch,
):
    """Saving or deleting the optional local copy never changes the remote source."""
    _target, instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("synthetic-vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    client = TestClient(main.app)

    created = client.post("/api/extensions/push-sources", json={"instance_handle": handle})
    assert created.status_code == 200
    created = created.json()

    rotated = client.post(
        f"/api/extensions/push-sources/{handle}/{created['source']['source_id']}/rotate"
    )
    assert rotated.status_code == 200
    rotated = rotated.json()
    assert authenticate_push_source(created["source"]["source_id"], created["push_key"]) is False
    assert authenticate_push_source(created["source"]["source_id"], rotated["push_key"]) is True

    token = _push_key_confirmation(
        client, handle, rotated["source"]["source_id"], rotated["push_key"],
    )
    saved = _save_push_key(client, handle, rotated, token)
    assert saved.status_code == 200
    assert saved.json() == {"saved_locally": True, "remote_unchanged": True}

    vault.lock()
    with pytest.raises(PermissionError):
        vault.get(instance.id)

    vault.unlock("synthetic-vault-password")
    assert vault.get(instance.id).genbox_push_key == rotated["push_key"]
    assert vault.delete(instance.id) is True
    assert vault.list_metadata() == []
    assert authenticate_push_source(created["source"]["source_id"], rotated["push_key"]) is True


def test_push_key_save_ui_requires_a_current_key_confirmation_and_unlocked_vault():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    state_block = js.split("function setPushSourceAccess", 1)[1].split(
        "async function resolvePushSourceHandle", 1,
    )[0]
    save_block = js.split("window.extensionSavePushConfiguration", 1)[1].split(
        "window.extensionOpenExistingPushSource", 1,
    )[0]

    # Without a just-created, rotated, or unlocked locally stored key, saving is unavailable.
    assert (
        "save.classList.toggle('hidden',!key.value)" in state_block
        or "save.classList.toggle('hidden',!pushKey)" in state_block
        or "save.disabled" in state_block
    )
    assert "extensions.push_key_not_available" in save_block
    assert "pushKeySaveEligible" in save_block
    assert "||!key.value)" in save_block

    # A visible GenBox-owned dialog gates the server-side confirmation. Merely
    # opening or canceling it must not request or consume the one-time token.
    assert "extensions.push_save_opt_in_required" in save_block
    assert 'id="extPushSaveConfirmModal"' in html
    assert 'role="dialog"' in html.split('id="extPushSaveConfirmModal"', 1)[1].split("</div>", 1)[0]
    assert 'id="extPushSaveConfirmBtn"' in html
    assert 'id="extPushSaveConfirmCancelBtn"' in html
    assert "openPushSaveConfirmation('push-source'" in save_block
    assert "if(!fromConfirmation)" in save_block
    assert "confirm(i18nText('extensions.push_save_confirm'))" not in save_block
    assert "window.extensionConfirmPushSave" in js
    assert "window.extensionCancelPushSaveConfirmation" in js
    assert "await extLoadVaultState()" in save_block
    assert "!extVaultStatus.configured||!extVaultStatus.unlocked" in save_block
    assert "/push-key/confirmation" in save_block
    assert "confirmation_token:confirmation.confirmation_token" in save_block
    assert "save_push_key_locally:true" in save_block
    assert "key=el('extPushKey')" in save_block
    assert "key=el('extPushKey').value" not in save_block


def test_push_key_browser_runtime_ignores_stale_prepare_and_records_only_redacted_request_shapes():
    """Exercise the browser state machine without retaining a key or token in test output."""
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
global.window=global;
const elements=new Map();
function element(id){
  if(!elements.has(id)){
    const classes=new Set();
    elements.set(id,{value:'',textContent:'',innerHTML:'',disabled:false,checked:false,type:'text',className:'',dataset:{},
      classList:{add:n=>classes.add(n),remove:n=>classes.delete(n),toggle:(n,on)=>on?classes.add(n):classes.delete(n),contains:n=>classes.has(n)},
      focus(){},select(){},setAttribute(){},removeAttribute(){},querySelector(){return null},querySelectorAll(){return []},appendChild(){},insertBefore(){},remove(){}});
  }
  return elements.get(id);
}
global.document={
  getElementById:element,
  querySelector(){return null},querySelectorAll(){return []},addEventListener(){},removeEventListener(){},
  createElement(){return element('created-'+elements.size)},body:element('document-body'),execCommand(){return true},
};
const zh={
  'extensions.push_source_not_configured':'尚未创建 Push 凭据。创建后，将把地址、来源 ID 和一次性密钥填入 chatgpt2api。',
  'extensions.push_key_ready_to_save':'新 Push 密钥仅在本次创建或轮换后可见。请先复制配置，再勾选本地保存并确认。',
};
global.i18nText=key=>zh[key]||key;
global.escHtml=value=>String(value||'');global.confirm=()=>true;
const handle='managed-runtime';const sourceId='source-'+Math.random().toString(36).slice(2);
const freshKey='key-'+Math.random().toString(36).slice(2);const confirmation='token-'+Math.random().toString(36).slice(2);
const shapes=[];let holdStatus=false;let releaseStatus;
function response(body){return {ok:true,status:200,text:async()=>JSON.stringify(body)}}
global._authFetch=async(url,options={})=>{
  const method=options.method||'GET';const body=options.body?JSON.parse(options.body):{};
  shapes.push({method,url,fields:Object.keys(body).sort()});
  if(url==='/api/extensions/push-sources/'+encodeURIComponent(handle)){
    if(holdStatus)return new Promise(resolve=>{releaseStatus=()=>resolve(response({configured:false,destination_url:'https://local.invalid/api/sync/push'}))});
    return response({configured:false,destination_url:'https://local.invalid/api/sync/push'});
  }
  if(url==='/api/extensions/push-sources')return response({instance_handle:handle,configured:true,destination_url:'https://local.invalid/api/sync/push',source:{source_id:sourceId},push_key:freshKey});
  if(url==='/api/extensions/vault/status')return response({configured:true,unlocked:true,entry_count:0});
  if(url==='/api/extensions/vault/credentials')return response({credentials:[]});
  if(url==='/api/extensions/vault/credentials/'+encodeURIComponent(handle)+'/push-key/confirmation'){
    if(body.source_id!==sourceId||body.push_key!==freshKey)throw new Error('confirmation did not receive current browser state');
    return response({confirmation_token:confirmation,expires_in_seconds:120});
  }
  if(url==='/api/extensions/vault/credentials/'+encodeURIComponent(handle)+'/push-key'){
    if(body.source_id!==sourceId||body.push_key!==freshKey||body.confirmation_token!==confirmation||body.save_push_key_locally!==true)throw new Error('save request lost its explicit confirmation chain');
    return response({saved_locally:true,remote_unchanged:true});
  }
  throw new Error('unexpected request shape');
};
eval(source);
(async()=>{
  await window.extensionOpenExistingPushSource(handle);
  if(element('extPushSourceStatus').textContent!==zh['extensions.push_source_not_configured'])throw new Error('unconfigured state exposed a translation key or wrong guidance');
  if(!element('extPushSaveBtn').classList.contains('hidden')||!element('extPushSaveOptIn').disabled)throw new Error('unconfigured state allowed local save');
  holdStatus=true;
  const stale=window.extensionPreparePushSource();
  await Promise.resolve();
  await window.extensionCreatePushSource();
  releaseStatus();await stale;
  if(!element('extPushKey').value||element('extPushSaveBtn').classList.contains('hidden'))throw new Error('stale prepare cleared the newly created key');
  if(element('extPushSourceStatus').textContent!==zh['extensions.push_key_ready_to_save'])throw new Error('new key did not render save guidance');
  element('extPushSaveOptIn').checked=true;
  await window.extensionSavePushConfiguration();
  if(shapes.some(item=>item.url.endsWith('/push-key')||item.url.endsWith('/push-key/confirmation')))throw new Error('opening confirmation requested or consumed a save credential');
  await window.extensionConfirmPushSave();
  if(element('extPushKey').value||!element('extPushSaveBtn').classList.contains('hidden'))throw new Error('saved key was not cleared from browser memory');
  const saved=shapes.filter(item=>item.url.endsWith('/push-key'));
  const confirmed=shapes.filter(item=>item.url.endsWith('/push-key/confirmation'));
  if(saved.length!==1||confirmed.length!==1)throw new Error('confirmation-to-save request chain was not exactly once');
  if(JSON.stringify(shapes).includes(freshKey)||JSON.stringify(shapes).includes(confirmation))throw new Error('redacted network trace retained a secret value');
  if(shapes.some(item=>item.url.includes(freshKey)||item.url.includes(confirmation)))throw new Error('a secret reached a request URL');
})().catch(error=>{console.error(error);process.exitCode=1});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_generic_credential_route_cannot_bypass_push_key_confirmation(source_registry, tmp_path, monkeypatch):
    _target, _instance, handle = _managed_instance(tmp_path, monkeypatch)
    vault = CredentialVault(tmp_path / "credentials.vault.json")
    vault.setup("vault-password")
    monkeypatch.setattr(main, "credential_vault", vault)
    client = TestClient(main.app)
    created = client.post("/api/extensions/push-sources", json={"instance_handle": handle}).json()

    response = client.put(f"/api/extensions/vault/credentials/{handle}", json={
        "credential": {
            "admin_key": "managed-admin-key",
            "genbox_push_key": created["push_key"],
            "genbox_push_source_id": created["source"]["source_id"],
            "genbox_push_url": created["destination_url"],
        },
        "push_key_save_confirmed": True,
    })
    assert response.status_code == 409
    assert vault.list_metadata() == []
