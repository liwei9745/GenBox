import asyncio
import json
import subprocess
import sys
from html.parser import HTMLParser
from types import SimpleNamespace
from pathlib import Path

from extensions.models import (
    ExtensionDeployRequest,
    ExtensionDiscoveryRequest,
    ExtensionHostKeyConfirmRequest,
    ExtensionHostKeyProbeRequest,
    ExtensionKeyResetRequest,
    ExtensionPlanRequest,
    ExtensionTarget,
    ExtensionTestRequest,
    NetworkConnectRequest,
    SSHCredential,
)
import extensions.store as store
from extensions.orchestrator import (
    CLONE_SCRUB_KEYS,
    DeploymentPlanManager,
    ExtensionTaskManager,
    SSHAuthenticationError,
    SSHConnectionError,
    _clone_config_scrub_script,
    _connect,
    _password_sudo_command,
    deployment_plans,
    probe_host_key,
)


def test_ssh_host_key_is_checked_before_credentials_are_used(monkeypatch):
    class Key:
        def export_public_key(self, format_name):
            return "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA test"

    class Connection:
        def get_server_host_key(self):
            return Key()

    calls = []
    probe_calls = []

    class HostKeyNotVerifiable(Exception):
        pass

    async def connect(**kwargs):
        calls.append(kwargs)
        client = kwargs["client_factory"]()
        trusted = client.validate_host_public_key("vps.example", "203.0.113.10", 22, Key())
        if not trusted:
            raise HostKeyNotVerifiable("host key rejected before authentication")
        if kwargs.get("preferred_auth") == ["password"]:
            calls[-1]["provided_password"] = client.password_auth_requested()
        return Connection()

    async def get_server_host_key(host, port, *, config):
        probe_calls.append({"host": host, "port": port, "config": config})
        return Key()

    imported_keys = []

    def import_private_key(value, passphrase):
        imported_keys.append((value, passphrase))
        return "imported-private-key"

    fake_asyncssh = SimpleNamespace(
        SSHClient=object,
        HostKeyNotVerifiable=HostKeyNotVerifiable,
        connect=connect,
        get_server_host_key=get_server_host_key,
        import_private_key=import_private_key,
    )
    monkeypatch.setitem(sys.modules, "asyncssh", fake_asyncssh)
    request = ExtensionTestRequest(
        target=ExtensionTarget(id="vps", name="VPS", host="vps.example", username="ubuntu"),
        credential=SSHCredential(password="ssh-secret"),
    )

    async def run():
        connection, fingerprint = await _connect(request)
        assert connection is None
        assert fingerprint.startswith("SHA256:")
        assert probe_calls == [{"host": "vps.example", "port": 22, "config": []}]

        request.expected_host_key = fingerprint
        connection, trusted_fingerprint = await _connect(request)
        assert connection is not None
        assert trusted_fingerprint == fingerprint
        assert "password" not in calls[0]
        assert calls[0]["provided_password"] == "ssh-secret"
        assert calls[0]["preferred_auth"] == ["password"]
        assert calls[0]["kbdint_auth"] is False
        assert calls[0]["password_auth"] is True

        key_request = ExtensionTestRequest(
            target=request.target,
            credential=SSHCredential(private_key="private-key", passphrase="key-passphrase"),
            expected_host_key=fingerprint,
        )
        key_connection, key_fingerprint = await _connect(key_request)
        assert key_connection is not None
        assert key_fingerprint == fingerprint
        assert imported_keys == [("private-key", "key-passphrase")]
        assert calls[1]["client_keys"] == ["imported-private-key"]
        assert calls[1]["preferred_auth"] == ["publickey"]
        assert calls[1]["kbdint_auth"] is False
        assert calls[1]["password_auth"] is False
        assert "password" not in calls[1]

    asyncio.run(run())


def test_mismatched_ssh_host_key_is_rejected_before_authentication():
    import asyncssh

    authentication_callbacks = []

    class LoopbackServer(asyncssh.SSHServer):
        def begin_auth(self, username):
            authentication_callbacks.append("begin_auth")
            return True

        def password_auth_supported(self):
            authentication_callbacks.append("password_auth_supported")
            return True

        def validate_password(self, username, password):
            authentication_callbacks.append("validate_password")
            return False

    async def run():
        server = await asyncssh.listen(
            "127.0.0.1",
            0,
            server_factory=LoopbackServer,
            server_host_keys=[asyncssh.generate_private_key("ssh-ed25519")],
        )
        try:
            request = ExtensionTestRequest(
                target=ExtensionTarget(
                    id="loopback",
                    name="Loopback",
                    host="127.0.0.1",
                    port=server.get_port(),
                    username="test-user",
                ),
                credential=SSHCredential(password="test-password"),
                expected_host_key="SHA256:not-the-loopback-server-key",
            )
            try:
                await _connect(request)
            except SSHConnectionError as exc:
                assert exc.diagnostic["code"] == "ssh_host_key_mismatch"
            else:
                raise AssertionError("mismatched host key was accepted")
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(run())
    assert authentication_callbacks == []


def test_password_callback_authenticates_against_real_asyncssh_server():
    import asyncssh
    from extensions.orchestrator import _fingerprint

    accepted_passwords = []
    server_key = asyncssh.generate_private_key("ssh-ed25519")

    class LoopbackServer(asyncssh.SSHServer):
        def begin_auth(self, username):
            return True

        def password_auth_supported(self):
            return True

        def validate_password(self, username, password):
            accepted_passwords.append(password)
            return username == "test-user" and password == "test-password"

    async def run():
        server = await asyncssh.listen(
            "127.0.0.1",
            0,
            server_factory=LoopbackServer,
            server_host_keys=[server_key],
        )
        try:
            request = ExtensionTestRequest(
                target=ExtensionTarget(
                    id="loopback",
                    name="Loopback",
                    host="127.0.0.1",
                    port=server.get_port(),
                    username="test-user",
                ),
                credential=SSHCredential(password="test-password"),
                expected_host_key=_fingerprint(server_key),
            )
            connection, fingerprint = await _connect(request)
            assert connection is not None
            assert fingerprint == _fingerprint(server_key)
            connection.close()
            await connection.wait_closed()
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(run())
    assert accepted_passwords == ["test-password"]


def test_ssh_connection_rejects_missing_or_ambiguous_credentials_before_connect():
    async def run():
        for values in (
            {},
            {"password": "password-secret", "private_key": "private-key-secret"},
        ):
            try:
                SSHCredential(**values)
            except ValueError as exc:
                assert "且只选择一种 SSH 凭据" in str(exc)
            else:
                raise AssertionError("invalid SSH credential combination passed model validation")
            credential = SSHCredential.model_construct(
                password=values.get("password", ""),
                private_key=values.get("private_key", ""),
                passphrase="",
                sudo_password="",
            )
            request = ExtensionTestRequest.model_construct(
                target=ExtensionTarget(
                    id="vps", name="VPS", host="vps.example", username="root",
                ),
                credential=credential,
                trust_host_key=False,
                expected_host_key="SHA256:test",
            )
            try:
                await _connect(request)
            except ValueError as exc:
                message = str(exc)
                assert "且只选择一种 SSH 凭据" in message
                assert "password-secret" not in message
                assert "private-key-secret" not in message
            else:
                raise AssertionError("invalid SSH credential combination reached AsyncSSH")

    asyncio.run(run())


def test_password_auth_rejection_is_sanitized_and_does_not_claim_password_is_wrong(monkeypatch):
    class Key:
        def export_public_key(self, format_name):
            return "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA test"

    class PermissionDenied(Exception):
        pass

    class Client:
        def __init__(self, expected_fingerprint=""):
            self.expected_fingerprint = expected_fingerprint
            self.fingerprint = ""

        def validate_host_public_key(self, host, addr, port, key):
            from extensions.orchestrator import _fingerprint

            self.fingerprint = _fingerprint(key)
            return self.expected_fingerprint == self.fingerprint

    async def connect(**kwargs):
        client = kwargs["client_factory"]()
        assert client.validate_host_public_key("vps.example", "203.0.113.10", 22, Key())
        assert "password" not in kwargs
        assert client.password_auth_requested() == "ssh-secret"
        assert client.password_auth_requested() is None
        raise PermissionDenied("rejected ssh-secret sentinel")

    fake_asyncssh = SimpleNamespace(
        SSHClient=Client,
        HostKeyNotVerifiable=Exception,
        PermissionDenied=PermissionDenied,
        connect=connect,
    )
    monkeypatch.setitem(sys.modules, "asyncssh", fake_asyncssh)
    request = ExtensionTestRequest(
        target=ExtensionTarget(
            id="vps", name="VPS", host="vps.example", username="root",
            host_key="SHA256:ignored",
        ),
        credential=SSHCredential(password="ssh-secret"),
    )

    async def run():
        from extensions.orchestrator import _fingerprint

        request.expected_host_key = _fingerprint(Key())
        try:
            await _connect(request)
        except SSHAuthenticationError as exc:
            message = str(exc)
            assert "不能单独证明密码错误" in message
            assert "请勿连续重试" in message
            assert "ssh-secret" not in message
            assert "sentinel" not in message
            assert "已请求并取得你输入的密码" in message
            assert exc.diagnostic == {
                "code": "ssh_auth_rejected",
                "stage": "password_requested",
                "auth_mode": "password",
                "retry_safe": False,
                "host_key_verified": True,
                "password_requested": True,
                "connection_lost_during_auth": False,
            }
        else:
            raise AssertionError("authentication rejection was not classified")

    asyncio.run(run())


def test_password_auth_rejection_reports_when_password_was_not_selected(monkeypatch):
    class PermissionDenied(Exception):
        pass

    class Client:
        def __init__(self, expected_fingerprint=""):
            self.expected_fingerprint = expected_fingerprint
            self.fingerprint = "SHA256:test"

    async def connect(**kwargs):
        client = kwargs["client_factory"]()
        client.transport_connected = True
        client.authentication_started = True
        raise PermissionDenied("connection closed before password callback")

    fake_asyncssh = SimpleNamespace(
        SSHClient=Client,
        HostKeyNotVerifiable=Exception,
        PermissionDenied=PermissionDenied,
        connect=connect,
    )
    monkeypatch.setitem(sys.modules, "asyncssh", fake_asyncssh)
    request = ExtensionTestRequest(
        target=ExtensionTarget(
            id="vps", name="VPS", host="vps.example", username="root",
            host_key="SHA256:test",
        ),
        credential=SSHCredential(password="ssh-secret"),
        expected_host_key="SHA256:test",
    )

    async def run():
        try:
            await _connect(request)
        except SSHAuthenticationError as exc:
            assert "取用密码前结束" in str(exc)
            assert "ssh-secret" not in str(exc)
            assert exc.diagnostic["stage"] == "authentication_started"
            assert exc.diagnostic["password_requested"] is False
            assert exc.diagnostic["retry_safe"] is False
        else:
            raise AssertionError("pre-password authentication close was not classified")

    asyncio.run(run())


def test_extension_ssh_route_returns_structured_sanitized_auth_diagnostic(monkeypatch):
    import main
    from fastapi import HTTPException

    async def reject(_request):
        raise SSHAuthenticationError(
            "safe authentication message",
            stage="password_requested",
            auth_mode="password",
            facts={
                "host_key_verified": True,
                "password_requested": True,
                "connection_lost_during_auth": True,
            },
        )

    monkeypatch.setattr(main, "test_extension_connection", reject)
    saved_target = ExtensionTarget(
        id="vps", name="VPS", host="vps.example", username="root",
        host_key="SHA256:test",
    )
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: saved_target)
    request = ExtensionTestRequest(
        target=saved_target,
        credential=SSHCredential(password="ssh-secret"),
        expected_host_key="SHA256:test",
    )

    async def run():
        try:
            await main.extension_test_ssh(request)
        except HTTPException as exc:
            assert exc.status_code == 401
            assert exc.detail["error"] == "safe authentication message"
            assert exc.detail["diagnostic"]["code"] == "ssh_auth_rejected"
            assert exc.detail["diagnostic"]["password_requested"] is True
            assert "ssh-secret" not in json.dumps(exc.detail)
            assert "vps.example" not in json.dumps(exc.detail)
            assert "root" not in json.dumps(exc.detail)
        else:
            raise AssertionError("route did not return the structured SSH diagnostic")

    asyncio.run(run())


def test_host_key_probe_request_has_no_credential_fields():
    assert set(ExtensionHostKeyProbeRequest.model_fields) == {"target_id"}
    assert set(ExtensionHostKeyConfirmRequest.model_fields) == {"target_id", "fingerprint"}
    for fingerprint in ("", "MD5:bad", "SHA256:short", "SHA256:bad value"):
        try:
            ExtensionHostKeyConfirmRequest(target_id="saved", fingerprint=fingerprint)
        except ValueError:
            pass
        else:
            raise AssertionError("a malformed host fingerprint was accepted")


def test_probe_host_key_uses_kex_only_helper_without_identity_or_credentials(monkeypatch):
    class Key:
        def export_public_key(self, format_name):
            return "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA test"

    calls = []

    async def get_server_host_key(host, port, *, config):
        calls.append({"host": host, "port": port, "config": config})
        return Key()

    fake_asyncssh = SimpleNamespace(
        get_server_host_key=get_server_host_key,
    )
    monkeypatch.setitem(sys.modules, "asyncssh", fake_asyncssh)

    fingerprint = asyncio.run(probe_host_key(ExtensionTarget(
        id="probe", name="Probe", host="safe.example", username="ubuntu",
    )))

    assert fingerprint.startswith("SHA256:")
    assert calls == [{"host": "safe.example", "port": 22, "config": []}]
    assert "username" not in calls[0]
    assert "credential" not in calls[0]
    assert "password" not in calls[0]


def test_host_key_confirm_reprobes_and_persists_only_matching_fingerprint(monkeypatch):
    import main

    fingerprint = "SHA256:AAAAAAAAAAAAAAAAAAAA"
    target = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", username="ubuntu",
    )
    saved = []

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "probe_host_key", lambda _target: asyncio.sleep(0, result=fingerprint))
    monkeypatch.setattr(
        main.extensions_store,
        "confirm_target_host_key",
        lambda expected, value: saved.append((expected, value)) or expected.model_copy(update={"host_key": value}),
    )

    result = asyncio.run(main.extension_confirm_ssh_host_key(
        ExtensionHostKeyConfirmRequest(target_id="saved", fingerprint=fingerprint)
    ))

    assert result["target"]["host_key"] == fingerprint
    assert saved == [(target, fingerprint)]


def test_host_key_confirm_rejects_changed_or_previously_conflicting_key(monkeypatch):
    import main
    from fastapi import HTTPException

    observed = "SHA256:AAAAAAAAAAAAAAAAAAAA"
    submitted = "SHA256:BBBBBBBBBBBBBBBBBBBB"
    writes = []

    async def current_key(_target):
        return observed

    monkeypatch.setattr(main, "probe_host_key", current_key)
    monkeypatch.setattr(main.extensions_store, "upsert_target", lambda data: writes.append(data))

    for stored_key, requested_key in (("", submitted), (submitted, observed)):
        target = ExtensionTarget(
            id="saved", name="Saved", host="safe.example", username="ubuntu",
            host_key=stored_key,
        )
        monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id, item=target: item)
        try:
            asyncio.run(main.extension_confirm_ssh_host_key(
                ExtensionHostKeyConfirmRequest(target_id="saved", fingerprint=requested_key)
            ))
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("a changed host key was persisted")

    assert writes == []


def test_extension_ssh_route_hides_unclassified_raw_exception(monkeypatch):
    import main
    from fastapi import HTTPException

    target = ExtensionTarget(
        id="vps", name="VPS", host="hidden.example", username="hidden-user",
        host_key="SHA256:AAAAAAAAAAAAAAAAAAAA",
    )

    async def reject(_request):
        raise RuntimeError("Permission denied for user hidden-user on host hidden.example 192.0.2.77")

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "test_extension_connection", reject)
    request = ExtensionTestRequest(
        target=target,
        credential=SSHCredential(password="test-secret"),
        expected_host_key=target.host_key,
    )

    try:
        asyncio.run(main.extension_test_ssh(request))
    except HTTPException as exc:
        serialized = json.dumps(exc.detail)
        assert exc.status_code == 400
        assert "Permission denied" not in serialized
        assert "hidden-user" not in serialized
        assert "hidden.example" not in serialized
        assert "192.0.2.77" not in serialized
        assert "test-secret" not in serialized
    else:
        raise AssertionError("the route exposed an unclassified exception")


def test_post_connect_routes_hide_unclassified_remote_exceptions(monkeypatch):
    import main
    from fastapi import HTTPException

    target = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", username="ubuntu",
        host_key="SHA256:AAAAAAAAAAAAAAAAAAAA",
    )
    credential = SSHCredential(password="test-secret")
    raw = "hidden-user hidden.example 192.0.2.77 ssh-secret remote-output"

    async def reject(_request):
        raise RuntimeError(raw)

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "discover_environment", reject)
    monkeypatch.setattr(main, "reset_managed_admin_key", reject)
    cases = (
        (main.extension_discover, ExtensionDiscoveryRequest(target=target, credential=credential)),
        (main.extension_deploy_plan, ExtensionPlanRequest(target=target, credential=credential)),
        (main.extension_reset_admin_key, ExtensionKeyResetRequest(
            target=target, credential=credential, instance_id="managed-one",
        )),
    )

    for route, request_body in cases:
        try:
            asyncio.run(route(request_body))
        except HTTPException as exc:
            serialized = json.dumps(exc.detail)
            assert exc.status_code == 400
            assert exc.detail["diagnostic"]["retry_safe"] is False
            for sentinel in (
                "hidden-user", "hidden.example", "192.0.2.77",
                "ssh-secret", "remote-output", "test-secret",
            ):
                assert sentinel not in serialized
        else:
            raise AssertionError(f"{route.__name__} exposed a raw remote exception")


def test_network_ui_is_tailscale_and_existing_only_with_failure_recovery_contract():
    class ExtensionNetworkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.inputs = []
            self.options_by_select = {}
            self.elements_by_id = {}
            self._active_select = None

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if attributes.get("id"):
                self.elements_by_id[attributes["id"]] = attributes
            if tag == "input":
                self.inputs.append(attributes)
            elif tag == "select":
                self._active_select = attributes.get("id")
                self.options_by_select.setdefault(self._active_select, [])
            elif tag == "option" and self._active_select:
                self.options_by_select[self._active_select].append(attributes)

        def handle_endtag(self, tag):
            if tag == "select":
                self._active_select = None

    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    script = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    translations = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    parser = ExtensionNetworkParser()
    parser.feed(html)

    providers = {item["value"]: item for item in parser.inputs if item.get("name") == "extNetwork"}
    assert "checked" in providers["tailscale"]
    assert "disabled" not in providers["tailscale"]
    assert "disabled" in providers["netbird"]
    assert "disabled" in providers["cloudflare"]

    operation_modes = [item["value"] for item in parser.inputs if item.get("name") == "extNetworkOperation"]
    assert operation_modes == ["auto", "existing"]
    assert [item["value"] for item in parser.options_by_select["extRemoteNetworkMode"]] == ["auto", "existing"]
    token_input = next(item for item in parser.inputs if item.get("id") == "extNetworkToken")
    assert token_input["type"] == "password"
    assert token_input["autocomplete"] == "off"
    assert parser.elements_by_id["extTailscaleKeyGuide"]["aria-hidden"] == "true"
    assert "extNoviceGuide" in parser.elements_by_id
    assert "extGuidePrimaryBtn" in parser.elements_by_id
    assert "extNetworkDiagnosticDetail" in parser.elements_by_id

    connect_handler = script.rpartition("window.extensionConnectNetwork=async function")[2].partition("function renderLocalTailscale")[0]
    render_handler = script.partition("function renderNetworkTask")[2].partition("window.extensionRetryNetworkCheck")[0]
    assert "provider:'tailscale'" in connect_handler
    assert "enrollment_token:token" in connect_handler
    assert "operation_mode:mode" in connect_handler
    assert "el('extNetworkToken').value=''" in connect_handler
    assert "snapshot=networkRequestContext(mode)" in connect_handler
    assert "networkContextMatches(snapshot,mode)" in connect_handler
    assert "clearSessionCredentials()" not in connect_handler
    assert "t.failed_phase" in render_handler
    assert "networkRecoveryText(t)" in render_handler
    assert "t.status==='needs_action'" in render_handler
    assert "status.skipped" in script
    assert "networkDiagnosticText(t.diagnostics)" in render_handler
    assert "extensions.network_diag_magicdns" in script
    assert "extensions.network_diag_http_error" in script
    assert "extensions.network_diag_invalid_genbox_response" in script
    assert "value=row&&row.children?row.children[1]:null" in script
    assert "restoreTargetNetworkState(item)" in script
    assert "item.network_url&&item.network_verified_at" in script
    assert "extNetworkRecoveryDetail" in render_handler
    assert "extensions.network_failed_plain" in render_handler

    translation_entry = translations.partition('"task.network.remote_network_detect"')[2].splitlines()[0]
    assert "确认 VPS Tailscale 地址" in translation_entry
    assert "Confirm VPS Tailscale address" in translation_entry


def test_network_recovery_and_auth_key_layout_stack_at_phone_width():
    css = (Path(__file__).parents[1] / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    html = (Path(__file__).parents[1] / "static" / "index.html").read_text(encoding="utf-8")

    assert "@media(max-width:480px){.extension-network-recovery{align-items:stretch;flex-direction:column}" in css
    assert ".extension-auth-key-panel .extension-copy-row{display:grid;grid-template-columns:minmax(0,1fr) auto}" in css
    assert 'id="extNetworkToken" type="password"' in html
    assert 'maxlength="4096"' in html


def test_deploy_completion_opens_delivery_pane_without_falsely_finishing_network():
    script = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    completed_handler = script.split("async function renderTask", 1)[1].split("window.extensionStartDeploy", 1)[0]

    assert "el('extHandoff').classList.remove('hidden')" in completed_handler
    assert "if(deliveryAvailable){extensionNext(5)" in completed_handler
    assert "else{extensionNext(3)}" in completed_handler
    assert "extensionNext(restoring?3:5)" not in completed_handler
    assert "extensions.deploy_complete_save_key_then_network" in completed_handler
    assert "setCheck('url',true,t.result.url)" not in completed_handler
    assert completed_handler.index("extensionNext(5)") < completed_handler.index("claimTaskDelivery(taskId)")


def test_target_store_never_persists_credentials(tmp_path, monkeypatch):
    path = tmp_path / "extensions.json"
    monkeypatch.setattr(store, "EXTENSIONS_FILE", path)
    target = store.upsert_target({
        "name": "VPS", "host": "203.0.113.10", "username": "ubuntu",
        "password": "must-not-persist", "private_key": "must-not-persist",
    })
    serialized = json.dumps(json.loads(path.read_text(encoding="utf-8")))
    assert target.host == "203.0.113.10"
    assert "must-not-persist" not in serialized
    assert "password" not in serialized
    assert "private_key" not in serialized


def test_target_store_roundtrip_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = store.upsert_target({"name": "VPS", "host": "host.example", "username": "ubuntu"})
    assert store.list_targets()[0].id == target.id
    assert store.delete_target(target.id) is True
    assert store.list_targets() == []


def test_browser_target_save_cannot_set_or_replace_host_key(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    injected = "SHA256:BBBBBBBBBBBBBBBBBBBB"
    confirmed = "SHA256:AAAAAAAAAAAAAAAAAAAA"

    created = store.save_target_metadata({
        "id": "saved", "name": "Saved", "host": "safe.example", "port": 22,
        "username": "ubuntu", "host_key": injected,
    })
    assert created.host_key == ""

    store.upsert_target({**created.model_dump(), "host_key": confirmed})
    unchanged = store.save_target_metadata({
        **created.model_dump(), "name": "Renamed", "host_key": injected,
    })
    assert unchanged.name == "Renamed"
    assert unchanged.host_key == confirmed

    changed = store.save_target_metadata({
        **unchanged.model_dump(), "host": "new.example", "host_key": injected,
    })
    assert changed.host == "new.example"
    assert changed.host_key == ""


def test_browser_target_save_cannot_inject_network_verification_and_identity_change_clears_it(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    injected = store.save_target_metadata({
        "id": "saved", "name": "Saved", "host": "safe.example", "port": 22,
        "username": "ubuntu", "chatgpt2api_port": 33010,
        "primary_network": "cloudflare", "available_networks": ["tailscale"],
        "network_url": "http://100.64.0.99:8893", "network_verified_at": "2099-01-01 00:00:00",
    })
    assert injected.available_networks == []
    assert injected.network_url == ""
    assert injected.network_verified_at == ""
    assert injected.primary_network == "tailscale"

    verified = store.upsert_target({
        **injected.model_dump(), "host_key": "SHA256:AAAAAAAAAAAAAAAAAAAA",
        "available_networks": ["tailscale"], "network_url": "http://100.64.0.20:8893",
        "network_verified_at": "2026-07-19 12:00:00",
    })
    renamed = store.save_target_metadata({
        **verified.model_dump(), "name": "Renamed",
        "network_url": "http://100.64.0.99:8893", "network_verified_at": "2099-01-01 00:00:00",
    })
    assert renamed.host_key == verified.host_key
    assert renamed.available_networks == ["tailscale"]
    assert renamed.network_url == verified.network_url
    assert renamed.network_verified_at == verified.network_verified_at

    changed = store.save_target_metadata({**renamed.model_dump(), "host": "new.example"})
    assert changed.host_key == ""
    assert changed.available_networks == []
    assert changed.network_url == ""
    assert changed.network_verified_at == ""


def test_host_key_confirmation_store_fails_closed_on_concurrent_identity_change(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    original = store.upsert_target({
        "id": "saved", "name": "Saved", "host": "safe.example", "port": 22,
        "username": "ubuntu",
    })
    fingerprint = "SHA256:AAAAAAAAAAAAAAAAAAAA"
    confirmed = store.confirm_target_host_key(original, fingerprint)
    assert confirmed.host_key == fingerprint

    expected = confirmed
    store.save_target_metadata({**confirmed.model_dump(), "host": "changed.example"})
    try:
        store.confirm_target_host_key(expected, fingerprint)
    except ValueError as exc:
        assert str(exc) == "target_changed"
    else:
        raise AssertionError("a stale probe overwrote a concurrently changed target")
    current = store.get_target("saved")
    assert current.host == "changed.example"
    assert current.host_key == ""


def test_all_ssh_routes_bind_to_the_server_confirmed_target(monkeypatch):
    import main
    from fastapi import HTTPException

    confirmed = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", port=22, username="ubuntu",
        host_key="SHA256:AAAAAAAAAAAAAAAAAAAA",
    )
    submitted = confirmed.model_copy(update={
        "host": "attacker.example",
        "host_key": "SHA256:BBBBBBBBBBBBBBBBBBBB",
    })
    credential = SSHCredential(password="test-secret")
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: confirmed)

    requests_and_routes = [
        (ExtensionTestRequest(target=submitted, credential=credential), main.extension_test_ssh),
        (ExtensionDiscoveryRequest(target=submitted, credential=credential), main.extension_discover),
        (ExtensionPlanRequest(target=submitted, credential=credential), main.extension_deploy_plan),
        (ExtensionDeployRequest(target=submitted, credential=credential), main.extension_start_deploy),
        (ExtensionKeyResetRequest(target=submitted, credential=credential, instance_id="managed-one"), main.extension_reset_admin_key),
        (NetworkConnectRequest(
            target=submitted, credential=credential, provider="tailscale", operation_mode="existing",
        ), main.extension_connect_network),
    ]

    for request_body, route in requests_and_routes:
        try:
            asyncio.run(route(request_body))
        except HTTPException as exc:
            assert exc.status_code == 409
            assert "重新保存并确认" in str(exc.detail)
        else:
            raise AssertionError(f"{route.__name__} accepted a client-supplied target identity")


def test_confirmed_target_binding_overrides_client_trust_fields(monkeypatch):
    import main

    confirmed = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", port=22, username="ubuntu",
        host_key="SHA256:AAAAAAAAAAAAAAAAAAAA",
    )
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: confirmed)
    submitted = ExtensionDiscoveryRequest(
        target=confirmed.model_copy(update={"host_key": "SHA256:BBBBBBBBBBBBBBBBBBBB"}),
        credential=SSHCredential(password="test-secret"),
        expected_host_key="SHA256:BBBBBBBBBBBBBBBBBBBB",
        trust_host_key=False,
    )

    bound = main._bind_confirmed_extension_target(submitted)
    assert bound.target == confirmed
    assert bound.expected_host_key == confirmed.host_key
    assert bound.trust_host_key is True


def test_instance_store_contains_no_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    instance = store.upsert_instance({
        "id": "chatgpt2api-dev", "target_id": "vps-a", "service_port": 33010,
        "install_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev",
        "data_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev/data",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "managed": True,
        "admin_key": "must-not-persist", "password": "must-not-persist",
    })
    serialized = (tmp_path / "extensions.json").read_text(encoding="utf-8")
    assert store.get_instance(instance.id).managed is True
    assert "must-not-persist" not in serialized
    assert "admin_key" not in serialized


def test_deploy_task_reports_success(tmp_path, monkeypatch):
    class Result:
        stdout = "genbox-connected"
        exit_status = 0

    class Connection:
        async def run(self, command, check=False, **kwargs):
            result = Result()
            if command == "id -u":
                result.stdout = "0"
            elif command == 'printf %s "$HOME"':
                result.stdout = "/home/ubuntu"
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="secret"), trust_host_key=True,
            instance_id="chatgpt2api-dev", confirmed_plan_id="plan-test",
        )
        deployment_plans.plans["plan-test"] = {
            "id": "plan-test", "project_id": "chatgpt2api", "target_id": "t", "instance_id": "chatgpt2api-dev",
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "genbox-chatgpt2api-chatgpt2api-dev",
            "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "completed"
        assert state["progress"] == 100
        assert all(step["status"] == "success" for step in state["steps"])
        assert "secret" not in json.dumps(state)
        assert state["result"]["admin_key_available"] is True
        persisted = (tmp_path / "extension_tasks.json").read_text(encoding="utf-8")
        assert "secret" not in persisted
        rebuilt = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        recovered = rebuilt.get(task_id)
        assert recovered["status"] == "completed"
        assert recovered["result"]["url"] == "http://host.example:33010"
        assert recovered["result"]["admin_key_available"] is False
        assert recovered["result"]["credential_recovery_required"] is True
        assert rebuilt.take_delivery(task_id) is None
        delivered = manager.take_delivery(task_id)
        assert delivered.startswith("gbx-")
        assert manager.take_delivery(task_id) is None

    asyncio.run(run())


def test_working_copy_password_sudo_waits_for_ssh_input(tmp_path, monkeypatch):
    class Result:
        stdout = ""
        exit_status = 0

    class Connection:
        def __init__(self):
            self.commands = []

        async def run(self, command, check=False, input=None, **kwargs):
            self.commands.append((command, input))
            if input == "sudo-secret\n" and not command.startswith("IFS= read -r sudo_password;"):
                raise RuntimeError("Channel not open for sending")
            result = Result()
            if command == "id -u":
                result.stdout = "1000"
            elif command == 'printf %s "$HOME"':
                result.stdout = "/home/ubuntu"
            elif command == "sudo -n true >/dev/null 2>&1":
                result.exit_status = 1
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(request):
        return connection, "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="secret", sudo_password="sudo-secret"), trust_host_key=True,
            instance_id="chatgpt2api-dev", confirmed_plan_id="plan-working-copy",
            clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
        )
        deployment_plans.plans["plan-working-copy"] = {
            "id": "plan-working-copy", "project_id": "chatgpt2api", "target_id": "t", "instance_id": "chatgpt2api-dev",
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "genbox-chatgpt2api-chatgpt2api-dev",
            "clone_scope": "working-copy", "clone_source_id": "chatgpt2api-warp",
            "clone_source_data_dir": "/root/chatgpt2api/data",
            "clone_source_config_file": "/root/chatgpt2api/config.json",
            "expires_at": 9999999999,
        }

        task_id = manager.create(request)
        await manager.runners[task_id]

        assert manager.get(task_id)["status"] == "completed"
        privileged = [(command, input_data) for command, input_data in connection.commands if input_data == "sudo-secret\n"]
        assert privileged
        assert all(command.startswith("IFS= read -r sudo_password;") for command, _ in privileged)
        assert all("sudo-secret" not in command for command, _ in privileged)

    asyncio.run(run())


def test_password_sudo_command_preserves_shell_quoting():
    wrapped = _password_sudo_command("printf '%s' \"$HOME\"")

    assert wrapped.startswith("IFS= read -r sudo_password;")
    assert "sudo -S -p '' sh -lc" in wrapped
    assert "sudo_password" in wrapped


def test_deployment_plan_rejects_port_conflict():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu")
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
    )
    discovery = {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": [33010]},
        "instances": [],
    }
    try:
        manager.create(request, discovery)
    except ValueError as exc:
        assert "端口" in str(exc)
    else:
        raise AssertionError("occupied port was accepted")


def test_deployment_plan_is_scoped_and_non_destructive():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu")
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
    )
    plan = manager.create(request, {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": []},
        "instances": [],
    })
    serialized = json.dumps(plan, ensure_ascii=False)
    assert plan["compose_project"] == "genbox-chatgpt2api-chatgpt2api-dev"
    assert "docker rm" not in serialized
    assert "secret" not in serialized


def test_isolated_working_copy_plan_requires_space_and_scrubs_push_state():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu")
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
        clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    discovery = {
        "environment": {
            "docker_version": "27.0", "compose_version": "2.30",
            "listening_ports": [3000], "disk_free_mb": 5000,
        },
        "instances": [{
            "id": "chatgpt2api-warp", "image": "ghcr.io/yukkcat/chatgpt2api:latest",
            "data_dir": "/opt/chatgpt2api/data", "config_file": "/opt/chatgpt2api/config.json",
            "data_size_mb": 1200, "clone_available": True,
        }],
    }
    plan = manager.create(request, discovery)
    assert plan["clone_scope"] == "working-copy"
    assert plan["clone_size_mb"] == 1200
    assert plan["source_baseline"]["container_id"] == ""
    assert plan["source_baseline"]["data_dir"] == "/opt/chatgpt2api/data"
    assert plan["source_baseline"]["config_file"] == "/opt/chatgpt2api/config.json"
    assert any("凭据" in operation for operation in plan["operations"])
    assert any("Push 身份" in operation for operation in plan["operations"])
    assert "secret" not in json.dumps(plan)


def test_working_copy_plan_rejects_image_drift():
    manager = DeploymentPlanManager()
    request = ExtensionPlanRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="secret"), service_port=33010,
        image="ghcr.io/yukkcat/chatgpt2api:latest",
        clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    discovery = {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": [], "disk_free_mb": 5000},
        "instances": [{
            "id": "chatgpt2api-warp", "image": "ghcr.io/yukkcat/chatgpt2api@sha256:abc",
            "data_dir": "/data", "config_file": "/config.json", "data_size_mb": 100,
            "clone_available": True,
        }],
    }

    try:
        manager.create(request, discovery)
    except ValueError as exc:
        assert "镜像基线" in str(exc)
    else:
        raise AssertionError("working copy accepted image drift")


def test_working_copy_plan_uses_existing_local_image_baseline():
    manager = DeploymentPlanManager()
    baseline_image = "genbox-chatgpt2api-source:abc123456789"
    request = ExtensionPlanRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="secret"), service_port=33010,
        image=baseline_image, clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    plan = manager.create(request, {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": [], "disk_free_mb": 5000},
        "instances": [{
            "id": "chatgpt2api-warp", "image": baseline_image,
            "source_image_id": "sha256:production-image", "data_dir": "/data",
            "config_file": "/config.json", "data_size_mb": 100, "clone_available": True,
        }],
    })

    assert plan["image"] == baseline_image
    assert plan["clone_source_image_id"] == "sha256:production-image"
    assert any("不拉取 latest" in operation for operation in plan["operations"])


def test_clone_config_scrub_removes_inherited_push_identity_and_keys(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "auth-key": "production-admin-key",
        "genbox_destination": {"url": "https://genbox.example", "push_key": "production-push-key"},
        "nested": {"genbox_source_id": "production-source", "keep": True},
        "backup": {"enabled": True},
    }), encoding="utf-8")

    subprocess.run([sys.executable, "-c", _clone_config_scrub_script(), str(config_path)], check=True)
    scrubbed = json.loads(config_path.read_text(encoding="utf-8"))

    assert "auth-key" in CLONE_SCRUB_KEYS
    assert "auth-key" not in scrubbed
    assert "genbox_destination" not in scrubbed
    assert "genbox_source_id" not in scrubbed["nested"]
    assert scrubbed["nested"]["keep"] is True
    assert scrubbed["backup"]["enabled"] is False


def test_clone_plan_rejects_insufficient_disk():
    manager = DeploymentPlanManager()
    request = ExtensionPlanRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="secret"), service_port=33010,
        clone_source_id="chatgpt2api-warp", clone_scope="media",
    )
    try:
        manager.create(request, {
            "environment": {
                "docker_version": "27.0", "compose_version": "2.30",
                "listening_ports": [], "disk_free_mb": 100,
            },
                "instances": [{
                    "id": "chatgpt2api-warp", "data_dir": "/data", "config_file": "/config.json",
                    "image": "ghcr.io/yukkcat/chatgpt2api:latest",
                    "data_size_mb": 1000, "clone_available": True,
                }],
        })
    except ValueError as exc:
        assert "磁盘" in str(exc)
    else:
        raise AssertionError("clone with insufficient disk was accepted")


def test_extensions_page_has_its_own_vertical_scroll_container():
    css = (Path(__file__).parents[1] / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    assert ".extension-layout{min-height:0;overflow-y:auto" in css
    assert "align-items:start" in css
    assert ".extension-workspace{min-width:0;height:max-content" in css


def test_deployed_services_section_is_wired():
    html = (Path(__file__).parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    js = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    assert "已部署服务" in html
    assert 'id="extDrawerList"' in html
    assert 'id="extFab"' in html
    assert 'id="extDrawerOverlay"' in html
    assert "extensionOpenDrawer" in js
    assert "extensionCloseDrawer" in js
    assert "extensionLoadServices" in js
    assert "i18nText('vault.save_login')" in js
    assert "VPS SSH 密码" in html
    assert "extCredentialSshPrivateKey" in html
    assert "window.loadExtensions=async function()" in js
    assert "extensionLoadServices()" in js
    assert "extensionToggleGroup" in js
    assert "extensionOpenResetModal" in js
    assert "extensionCopyText" in js
    assert "extResetKeyModal" in html
    assert "查看已部署服务" in html
    assert "ext-service-launcher" in html
    assert "response=await response" in js
    assert "grok2api" in js
    assert "gemini2api" in js
    assert "mimocode2api" in js
    assert "i18nText('extensions.accounts_short')" in js
    assert "i18nText('extensions.network_short')" in js
    assert '<div class="ext-deployed-collapsed">' in html
    assert '<button type="button" id="extFab"' in html


def test_deployed_services_cards_use_non_secret_fields_only():
    js = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    card_block = js[js.index("ext-bento-grid"):js.index("ext-bento-group-body")]
    assert "console_url" in card_block
    assert "api_url" in card_block
    assert "admin_key" not in card_block
    css = (Path(__file__).parents[1] / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    assert ".ext-service-card{" in css
    assert ".ext-bento-grid{" in css
    assert ".ext-status-running{" in css
    assert ".ext-status-deployed{" in css
    assert ".ext-status-planned{" in css
    assert ".ext-status-unavailable{" in css
    assert "width:87vw;max-width:none" in css
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in css


def test_deployed_services_reset_requires_ssh_credential():
    js = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    assert "extensionConfirmResetKey" in js
    assert "i18nText('extensions.owner_credential_required')" in js
    assert "/api/extensions/instances/reset-admin-key" in js


def test_instance_metadata_persists_after_deploy(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    instance = store.upsert_instance({
        "id": "chatgpt2api-dev", "target_id": "vps-a", "service_port": 33010,
        "install_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev",
        "data_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev/data",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "managed": True,
        "console_url": "http://192.0.2.10:33010",
        "api_url": "http://192.0.2.10:33010/v1",
        "status": "running",
    })
    raw = json.loads((tmp_path / "extensions.json").read_text(encoding="utf-8"))
    found = [i for i in raw["instances"] if i["id"] == "chatgpt2api-dev"]
    assert len(found) == 1
    assert found[0]["service_port"] == 33010
    assert found[0]["status"] == "running"
    assert found[0]["console_url"] == "http://192.0.2.10:33010"
    assert found[0]["api_url"] == "http://192.0.2.10:33010/v1"
    retrieved = store.get_instance("chatgpt2api-dev")
    assert retrieved.console_url == "http://192.0.2.10:33010"
    assert retrieved.status == "running"


def test_batch_target_selection_persists_only_valid_ids(tmp_path, monkeypatch):
    import extensions.store as store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    first = store.upsert_target({"id": "one", "name": "One", "host": "one.example", "username": "ubuntu"})
    second = store.upsert_target({"id": "two", "name": "Two", "host": "two.example", "username": "ubuntu"})

    assert store.save_batch_target_ids([second.id, "missing", first.id, second.id]) == ["two", "one"]
    assert store.get_batch_target_ids() == ["two", "one"]


def test_i18n_module_and_page_markers_exist():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "js" / "app-all.js").read_text(encoding="utf-8")
    i18n_js = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")

    assert '/static/js/i18n.js' in html
    assert 'data-i18n=' in html
    assert 'GenBoxI18n' in i18n_js
    assert 'var MESSAGES =' in i18n_js
    assert "url.searchParams.set('lang', next)" in i18n_js
    assert 'global.location.replace(url.toString())' in i18n_js
    assert 'i18nText(' in app_js
    assert 'ipVisibilityIcon' in app_js
    assert '>??</button>' not in app_js
    assert 'var upDays = Math.floor(upSec / 86400);' in app_js
    assert 'setupWizardMarkupV2' in app_js
    assert 'genboxLogoSvgMarkup' in app_js
    assert 'onboardingCapabilityGroupsMarkup' in app_js
    assert 'onboardingChatgptFeatureMarkup' in app_js
    assert 'onboarding-capability-grid' in app_js
    assert '04 / CONNECT TO GENBOX' in app_js
    assert 'GENBOX EXTENSION SERVICES' in html
    assert 'startOnboardingTour' in app_js
    assert 'TreeWalker' not in app_js
    assert 'MutationObserver' not in app_js


def test_vps_password_fields_support_explicit_visibility_toggle_without_autofill():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    extensions_js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    assert 'id="extPassword" type="password" autocomplete="off"' in html
    assert 'id="extSudoPassword" type="password" autocomplete="off"' in html
    assert 'id="extTestSshBtn"' in html
    assert 'id="extSshNextBtn"' in html
    assert 'onclick="extensionSshNext()"' in html
    assert 'id="extSshNextLabel"' in html
    assert 'id="extCredentialNotice"' in html
    assert 'data-i18n="extensions.ssh_not_saved_notice"' in html
    assert "extensionTogglePassword('extPassword',this)" in html
    assert "extensionTogglePassword('extSudoPassword',this)" in html
    assert "window.extensionTogglePassword=function" in extensions_js
    assert "input.type=visible?'text':'password'" in extensions_js
    assert "button.setAttribute('aria-pressed',String(visible))" in extensions_js
    assert "sshTestInFlight||!requireCredential()" in extensions_js
    assert "else{extensionNext(3)}" in extensions_js


def test_beginner_mode_hides_duplicate_workflow_buttons_until_advanced_is_opened():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    css = (root / "static" / "css" / "extensions.css").read_text(encoding="utf-8")

    assert 'class="extension-discovery-bar extension-advanced-only"' in html
    assert 'class="extension-actions extension-inline-actions extension-advanced-only"' in html
    assert 'id="extPlanBtn"' in html
    assert 'id="extDeployBtn"' in html
    assert 'class="extension-actions extension-advanced-only"><button class="btn-ghost" onclick="extensionNext(1)"' in html
    assert 'id="extNetworkHostKeyProbeBtn"' in html
    assert '.extension-workspace:not(.show-advanced) .extension-advanced-only{display:none!important}' in css
