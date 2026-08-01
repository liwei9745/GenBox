import asyncio
import copy
import hashlib
import json
import re
import subprocess
import sys
import threading
from html.parser import HTMLParser
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi import HTTPException

from extensions.models import (
    ExtensionDeployRequest,
    ExtensionDiscoveryRequest,
    ExtensionHostKeyConfirmRequest,
    ExtensionHostKeyPairingCancelRequest,
    ExtensionHostKeyPairingCompleteRequest,
    ExtensionHostKeyPairingStartRequest,
    ExtensionHostKeyProbeRequest,
    ExtensionHostKeyResetRequest,
    ExtensionKeyResetRequest,
    ExtensionPlanRequest,
    ExtensionTarget as ExtensionTargetModel,
    ExtensionTestRequest,
    NetworkConnectRequest,
    SSHCredential,
    is_canonical_host_key_trust,
    is_immutable_image_reference,
    validate_deployment_image,
)
import extensions.store as store
import extensions.orchestrator as orchestrator
from extensions.orchestrator import (
    CLONE_SCRUB_KEYS,
    DeploymentSnapshotChangedError,
    DeploymentPlanManager,
    ExtensionTaskManager,
    SSHAuthenticationError,
    SSHConnectionError,
    _clone_config_scrub_script,
    _connect,
    _diagnose_privileges,
    _password_sudo_command,
    deployment_plans,
    probe_host_key,
    public_instance_access,
    public_instance_handle,
)


TEST_HOST_KEY_ALGORITHM = "ssh-ed25519"
TEST_HOST_KEY = "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
DEPLOYMENT_ATTEMPT_ID = "0123456789abcdef0123456789abcdef"
PHASE4_PATH_CONDITIONS_VERSION = "phase4-v3"
TEST_DEPLOYMENT_IMAGE = "registry.example/chatgpt2api@sha256:" + ("a" * 64)


def test_public_instance_handle_survives_process_key_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    monkeypatch.setattr(orchestrator, "_PUBLIC_INSTANCE_HANDLE_KEY", None)

    first = orchestrator.public_instance_handle("target-a", "instance-a")
    key_path = tmp_path / ".instance-handle-key"

    assert key_path.is_file()
    assert len(key_path.read_bytes()) == 32

    monkeypatch.setattr(orchestrator, "_PUBLIC_INSTANCE_HANDLE_KEY", None)
    assert orchestrator.public_instance_handle("target-a", "instance-a") == first


def ExtensionTarget(**values):
    """Build a fully trusted target unless a test explicitly exercises legacy trust."""
    if values.get("host_key") == TEST_HOST_KEY and "host_key_algorithm" not in values:
        values["host_key_algorithm"] = TEST_HOST_KEY_ALGORITHM
    return ExtensionTargetModel(**values)


def isolated_empty_path_conditions(**overrides):
    conditions = {
        "target_install_dir_absent": True,
        "target_install_parent_claimable": True,
        "target_data_dir_nonoverlap": True,
        "target_compose_project_nonoverlap": True,
        "target_port_unoccupied": True,
    }
    conditions.update(overrides)
    return conditions


def existing_path_conditions(**overrides):
    conditions = {
        "existing_instance_present": True,
        "existing_instance_identity_matches": True,
    }
    conditions.update(overrides)
    return conditions


def source_clone_path_conditions(**overrides):
    conditions = {
        "source_instance_present": True,
        "source_clone_scope_allowed": True,
        "source_data_path_readable": True,
        "target_install_dir_absent": True,
        "target_install_parent_claimable": True,
        "source_target_paths_nonoverlap": True,
        "target_port_unoccupied": True,
        "clone_capacity_sufficient": True,
    }
    conditions.update(overrides)
    return conditions


def privilege_snapshot(*, elevation="none", can_admin=False, auth_kind="password"):
    return {
        "auth_kind": auth_kind,
        "elevation_contract": elevation,
        "is_root": False,
        "docker_access": True,
        "elevated_docker_access": bool(can_admin),
        "passwordless_sudo": elevation == "passwordless_sudo" and can_admin,
        "password_sudo": elevation == "password_sudo" and can_admin,
        "can_admin": can_admin,
        "can_deploy": True,
        "diagnostic_code": elevation if can_admin else "direct_docker",
    }


def environment_snapshot(
    *, listening_ports=None, disk_free_mb=5000, home_dir="/home/deploy-user",
    listening_ports_probe=None,
):
    ports = list(listening_ports or [])
    probe = copy.deepcopy(
        {"status": 0, "complete": True, "payload_present": True}
        if listening_ports_probe is None else listening_ports_probe
    )
    return {
        "docker_version": "27.0",
        "compose_version": "2.30",
        "home_dir": home_dir,
        "listening_ports": ports,
        "tcp_listeners": [
            {"protocol": "tcp", "host_port": port}
            for port in sorted(ports)
        ],
        "listening_ports_probe": probe,
        "disk_free_mb": disk_free_mb,
    }


def deployment_discovery(
    *, instances=None, privileges=None, listening_ports=None, path_conditions=None,
    listening_ports_probe=None,
):
    normalized_instances = copy.deepcopy(list(instances or []))
    for instance in normalized_instances:
        if "port_bindings" not in instance:
            instance["port_bindings"] = [
                {
                    "host_ip": "0.0.0.0", "host_port": port,
                    "container_port": 80, "protocol": "tcp",
                }
                for port in instance.get("published_ports", [])
            ]
        instance.setdefault("port_bindings_complete", True)
    return {
        "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY,
        "environment": environment_snapshot(
            listening_ports=listening_ports,
            listening_ports_probe=listening_ports_probe,
        ),
        "privileges": privileges or privilege_snapshot(),
        "instances": normalized_instances,
        "path_conditions_version": PHASE4_PATH_CONDITIONS_VERSION,
        "path_conditions": dict(
            isolated_empty_path_conditions() if path_conditions is None else path_conditions
        ),
    }


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
        algorithm, fingerprint = await probe_host_key(request.target)
        assert algorithm == TEST_HOST_KEY_ALGORITHM
        assert is_canonical_host_key_trust(algorithm, fingerprint)
        assert probe_calls == [{"host": "vps.example", "port": 22, "config": []}]

        request.expected_host_key_algorithm = algorithm
        request.expected_host_key = fingerprint
        connection, trusted_fingerprint = await _connect(request)
        assert connection is not None
        assert trusted_fingerprint == fingerprint
        assert "password" not in calls[0]
        assert calls[0]["provided_password"] == "ssh-secret"
        assert calls[0]["server_host_key_algs"] == [algorithm]
        assert calls[0]["preferred_auth"] == ["password"]
        assert calls[0]["kbdint_auth"] is False
        assert calls[0]["password_auth"] is True

        key_request = ExtensionTestRequest(
            target=request.target,
            credential=SSHCredential(private_key="private-key", passphrase="key-passphrase"),
            expected_host_key_algorithm=algorithm,
            expected_host_key=fingerprint,
        )
        key_connection, key_fingerprint = await _connect(key_request)
        assert key_connection is not None
        assert key_fingerprint == fingerprint
        assert imported_keys == [("private-key", "key-passphrase")]
        assert calls[1]["client_keys"] == ["imported-private-key"]
        assert calls[1]["server_host_key_algs"] == [algorithm]
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
                expected_host_key_algorithm=TEST_HOST_KEY_ALGORITHM,
                expected_host_key="SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
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


def test_mismatched_ssh_host_key_algorithm_is_rejected_before_authentication():
    import asyncssh
    from extensions.orchestrator import _fingerprint

    authentication_callbacks = []
    server_key = asyncssh.generate_private_key("ssh-ed25519")

    class LoopbackServer(asyncssh.SSHServer):
        def begin_auth(self, username):
            authentication_callbacks.append("begin_auth")
            return True

        def password_auth_supported(self):
            authentication_callbacks.append("password_auth_supported")
            return True

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
                    id="loopback-algorithm",
                    name="Loopback",
                    host="127.0.0.1",
                    port=server.get_port(),
                    username="test-user",
                ),
                credential=SSHCredential(password="test-password"),
                expected_host_key_algorithm="ecdsa-sha2-nistp256",
                expected_host_key=_fingerprint(server_key),
            )
            with pytest.raises(SSHConnectionError) as caught:
                await _connect(request)
            assert caught.value.diagnostic["code"] == "ssh_host_key_mismatch"
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
                expected_host_key_algorithm=TEST_HOST_KEY_ALGORITHM,
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


def test_rsa_host_key_uses_sha2_negotiation_and_keeps_the_canonical_fingerprint():
    import asyncssh
    from extensions.orchestrator import _fingerprint, _host_key_negotiation_algorithms

    accepted_passwords = []
    server_key = asyncssh.generate_private_key("ssh-rsa", key_size=2048)

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
                    id="rsa-loopback",
                    name="RSA loopback",
                    host="127.0.0.1",
                    port=server.get_port(),
                    username="test-user",
                ),
                credential=SSHCredential(password="test-password"),
                expected_host_key_algorithm="ssh-rsa",
                expected_host_key=_fingerprint(server_key),
            )
            connection, fingerprint = await _connect(request)
            assert fingerprint == _fingerprint(server_key)
            connection.close()
            await connection.wait_closed()
        finally:
            server.close()
            await server.wait_closed()

    assert _host_key_negotiation_algorithms("ssh-rsa") == ["rsa-sha2-512", "rsa-sha2-256"]
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


@pytest.mark.parametrize(
    ("uid", "credential", "docker", "sudo_n", "sudo_password_ok", "expected_code", "can_deploy"),
    [
        ("0", SSHCredential(password="ssh-only"), True, False, False, "uid_0", True),
        ("0", SSHCredential(private_key="key-only"), True, False, False, "uid_0", True),
        ("1000", SSHCredential(password="ssh-only"), True, False, False, "direct_docker", True),
        ("1000", SSHCredential(private_key="key-only"), True, False, False, "direct_docker", True),
        (
            "1000", SSHCredential(password="ssh-only", elevation="passwordless_sudo"),
            False, True, False, "passwordless_sudo", True,
        ),
        (
            "1000", SSHCredential(private_key="key-only", elevation="passwordless_sudo"),
            False, True, False, "passwordless_sudo", True,
        ),
        (
            "1000", SSHCredential(password="ssh-only", sudo_password="sudo-only", elevation="password_sudo"),
            False, False, True, "password_sudo", True,
        ),
        (
            "1000", SSHCredential(private_key="key-only", sudo_password="sudo-only", elevation="password_sudo"),
            False, False, True, "password_sudo", True,
        ),
        ("1000", SSHCredential(password="ssh-only"), False, False, False, "no_sudo_or_docker", False),
    ],
)
def test_privilege_diagnostic_matrix_separates_login_and_elevation(
    uid, credential, docker, sudo_n, sudo_password_ok, expected_code, can_deploy,
):
    class Result:
        def __init__(self, status=0, stdout=""):
            self.exit_status = status
            self.stdout = stdout

    class Connection:
        def __init__(self):
            self.calls = []

        async def run(self, command, check=False, input=None, **_kwargs):
            self.calls.append((command, input))
            if command == "id -u":
                return Result(stdout=uid)
            if command == "docker version >/dev/null 2>&1":
                return Result(0 if docker else 1)
            if command == "sudo -n true >/dev/null 2>&1":
                return Result(0 if sudo_n else 1)
            if command.startswith("sudo -n sh -lc"):
                return Result(0 if sudo_n else 1)
            if command.startswith("IFS= read -r sudo_password;"):
                return Result(0 if sudo_password_ok and input == "sudo-only\n" else 1)
            raise AssertionError(command)

    connection = Connection()
    privileges = asyncio.run(_diagnose_privileges(connection, credential))

    assert privileges["diagnostic_code"] == expected_code
    assert privileges["can_deploy"] is can_deploy
    serialized_commands = json.dumps([command for command, _input in connection.calls])
    assert "ssh-only" not in serialized_commands
    assert "sudo-only" not in serialized_commands


def test_ssh_password_is_reused_for_sudo_only_with_explicit_request():
    class Result:
        def __init__(self, status=0, stdout=""):
            self.exit_status = status
            self.stdout = stdout

    class Connection:
        def __init__(self):
            self.inputs = []

        async def run(self, command, check=False, input=None, **_kwargs):
            self.inputs.append(input)
            if command == "id -u":
                return Result(stdout="1000")
            if command == "docker version >/dev/null 2>&1":
                return Result(1)
            if command == "sudo -n true >/dev/null 2>&1":
                return Result(1)
            if command.startswith("IFS= read -r sudo_password;"):
                return Result(0 if input == "same-secret\n" else 1)
            raise AssertionError(command)

    with pytest.raises(ValueError):
        SSHCredential(password="same-secret", elevation="password_sudo")

    explicit = Connection()
    explicit_result = asyncio.run(_diagnose_privileges(
        explicit,
        SSHCredential(
            password="same-secret",
            elevation="password_sudo",
            reuse_ssh_password=True,
        ),
    ))
    assert explicit_result["diagnostic_code"] == "password_sudo"
    assert explicit_result["can_deploy"] is True
    assert "same-secret\n" in explicit.inputs


def test_private_key_password_sudo_requires_a_separate_sudo_password():
    with pytest.raises(ValueError):
        SSHCredential(
            private_key="key-only",
            elevation="password_sudo",
            reuse_ssh_password=True,
        )


@pytest.mark.parametrize("values", [
    {"password": "ssh-only", "sudo_password": "sudo-only", "elevation": "none"},
    {"password": "ssh-only", "reuse_ssh_password": True, "elevation": "none"},
    {"private_key": "key-only", "sudo_password": "sudo-only", "elevation": "passwordless_sudo"},
    {"password": "ssh-only", "reuse_ssh_password": True, "elevation": "passwordless_sudo"},
    {"password": "ssh-only", "elevation": "password_sudo"},
    {
        "password": "ssh-only", "sudo_password": "sudo-only",
        "reuse_ssh_password": True, "elevation": "password_sudo",
    },
    {"private_key": "key-only", "reuse_ssh_password": True, "elevation": "password_sudo"},
])
def test_elevation_contract_rejects_conflicting_credentials(values):
    with pytest.raises(ValueError):
        SSHCredential(**values)


@pytest.mark.parametrize("values", [
    {"password": "ssh-only", "elevation": "none"},
    {"private_key": "key-only", "elevation": "none"},
    {"password": "ssh-only", "elevation": "passwordless_sudo"},
    {"private_key": "key-only", "elevation": "passwordless_sudo"},
    {"password": "ssh-only", "sudo_password": "sudo-only", "elevation": "password_sudo"},
    {"private_key": "key-only", "sudo_password": "sudo-only", "elevation": "password_sudo"},
    {"password": "ssh-only", "reuse_ssh_password": True, "elevation": "password_sudo"},
])
def test_elevation_contract_accepts_only_explicit_valid_matrix(values):
    credential = SSHCredential(**values)
    assert credential.elevation == values["elevation"]


@pytest.mark.parametrize("credential", [
    {"password": "login-sentinel", "sudo_password": "sudo-sentinel", "elevation": "none"},
    {"password": "login-sentinel", "reuse_ssh_password": True, "elevation": "passwordless_sudo"},
    {"password": "login-sentinel", "elevation": "password_sudo"},
    {"private_key": "key-sentinel", "reuse_ssh_password": True, "elevation": "password_sudo"},
])
def test_extension_server_rejects_invalid_elevation_contract_without_echoing_credentials(credential):
    import main
    from fastapi.testclient import TestClient

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/ssh/test",
        json={
            "target": {"id": "t", "name": "VPS", "host": "host.example", "username": "deploy-user"},
            "credential": credential,
        },
    )
    assert response.status_code == 422
    assert "sentinel" not in response.text


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

        request.expected_host_key_algorithm = TEST_HOST_KEY_ALGORITHM
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
            host_key_algorithm=TEST_HOST_KEY_ALGORITHM,
            host_key=TEST_HOST_KEY,
        ),
        credential=SSHCredential(password="ssh-secret"),
        expected_host_key_algorithm=TEST_HOST_KEY_ALGORITHM,
        expected_host_key=TEST_HOST_KEY,
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


def test_connection_close_after_host_verification_is_sanitized_without_repair_loop(monkeypatch):
    class ConnectionLost(Exception):
        pass

    class PermissionDenied(Exception):
        pass

    class ProtocolError(Exception):
        pass

    class KeyExchangeFailed(Exception):
        pass

    class HostKeyNotVerifiable(Exception):
        pass

    class Client:
        def __init__(self, expected_algorithm, expected_fingerprint, password=""):
            self.expected_algorithm = expected_algorithm
            self.expected_fingerprint = expected_fingerprint
            self._password = password
            self.algorithm = ""
            self.fingerprint = ""
            self.transport_connected = False
            self.host_key_verified = False
            self.authentication_started = False
            self.authentication_completed = False
            self.connection_lost_during_auth = False
            self.password_requested = False

        def password_auth_requested(self):
            self.password_requested = True
            return self._password

    async def connect(**kwargs):
        client = kwargs["client_factory"]()
        client.transport_connected = True
        client.host_key_verified = True
        assert client.password_auth_requested() == "ssh-secret"
        raise ConnectionLost("hidden target details and ssh-secret")

    fake_asyncssh = SimpleNamespace(
        SSHClient=Client,
        ConnectionLost=ConnectionLost,
        ProtocolError=ProtocolError,
        KeyExchangeFailed=KeyExchangeFailed,
        HostKeyNotVerifiable=HostKeyNotVerifiable,
        PermissionDenied=PermissionDenied,
        connect=connect,
    )
    monkeypatch.setitem(sys.modules, "asyncssh", fake_asyncssh)
    request = ExtensionTestRequest(
        target=ExtensionTarget(
            id="vps", name="VPS", host="vps.example", username="root",
            host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
        ),
        credential=SSHCredential(password="ssh-secret"),
        expected_host_key_algorithm=TEST_HOST_KEY_ALGORITHM,
        expected_host_key=TEST_HOST_KEY,
    )

    async def run():
        with pytest.raises(SSHConnectionError) as caught:
            await _connect(request)
        assert caught.value.diagnostic == {
            "code": "ssh_session_closed",
            "stage": "password_requested",
            "retry_safe": False,
            "host_key_verified": True,
            "password_requested": True,
        }
        message = str(caught.value)
        assert "无需重新确认服务器身份" in message
        assert "hidden target details" not in message
        assert "ssh-secret" not in message

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
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM,
        host_key=TEST_HOST_KEY,
    )
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: saved_target)
    request = ExtensionTestRequest(
        target=saved_target,
        credential=SSHCredential(password="ssh-secret"),
        expected_host_key_algorithm=TEST_HOST_KEY_ALGORITHM,
        expected_host_key=TEST_HOST_KEY,
    )

    async def run():
        try:
            await main.extension_test_ssh(request)
        except HTTPException as exc:
            assert exc.status_code == 401
            assert exc.detail["error"] == "safe authentication message"
            assert exc.detail["diagnostic"]["code"] == "ssh_auth_rejected"
            assert exc.detail["diagnostic"]["password_requested"] is True
            serialized = json.dumps(exc.detail)
            assert "ssh-secret" not in serialized
            assert "vps.example" not in serialized
            assert "root" not in serialized
            assert TEST_HOST_KEY_ALGORITHM not in serialized
            assert TEST_HOST_KEY not in serialized
        else:
            raise AssertionError("route did not return the structured SSH diagnostic")

    asyncio.run(run())


def test_host_key_probe_request_has_no_credential_fields():
    assert set(ExtensionHostKeyProbeRequest.model_fields) == {"target_id"}
    assert set(ExtensionHostKeyResetRequest.model_fields) == {"target_id"}
    assert set(ExtensionHostKeyConfirmRequest.model_fields) == {"target_id", "algorithm", "fingerprint"}
    for fingerprint in ("", "MD5:bad", "SHA256:short", "SHA256:bad value"):
        try:
            ExtensionHostKeyConfirmRequest(
                target_id="saved", algorithm=TEST_HOST_KEY_ALGORITHM, fingerprint=fingerprint
            )
        except ValueError:
            pass
        else:
            raise AssertionError("a malformed host fingerprint was accepted")
    for algorithm in ("", "rsa-sha2-512", "ssh-dss"):
        with pytest.raises(ValueError):
            ExtensionHostKeyConfirmRequest(
                target_id="saved", algorithm=algorithm, fingerprint=TEST_HOST_KEY
            )


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

    algorithm, fingerprint = asyncio.run(probe_host_key(ExtensionTarget(
        id="probe", name="Probe", host="safe.example", username="ubuntu",
    )))

    assert algorithm == TEST_HOST_KEY_ALGORITHM
    assert is_canonical_host_key_trust(algorithm, fingerprint)
    assert calls == [{"host": "safe.example", "port": 22, "config": []}]
    assert "username" not in calls[0]
    assert "credential" not in calls[0]
    assert "password" not in calls[0]


def test_host_key_confirm_reprobes_and_persists_only_matching_fingerprint(monkeypatch):
    import main

    algorithm = TEST_HOST_KEY_ALGORITHM
    fingerprint = TEST_HOST_KEY
    target = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", username="ubuntu",
    )
    saved = []

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(
        main, "probe_host_key", lambda _target: asyncio.sleep(0, result=(algorithm, fingerprint))
    )
    monkeypatch.setattr(
        main.extensions_store,
        "confirm_target_host_key",
        lambda expected, alg, value: saved.append((expected, alg, value)) or expected.model_copy(
            update={"host_key_algorithm": alg, "host_key": value}
        ),
    )

    result = asyncio.run(main.extension_confirm_ssh_host_key(
        ExtensionHostKeyConfirmRequest(
            target_id="saved", algorithm=algorithm, fingerprint=fingerprint
        )
    ))

    assert result["target"]["host_key"] == fingerprint
    assert result["target"]["host_key_algorithm"] == algorithm
    assert saved == [(target, algorithm, fingerprint)]


def test_host_key_reset_route_only_discards_local_trust(monkeypatch):
    import main

    reset = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", username="ubuntu",
        identity_version=2,
    )
    calls = []
    monkeypatch.setattr(
        main.extensions_store,
        "reset_target_host_key",
        lambda target_id: calls.append(target_id) or reset,
    )
    monkeypatch.setattr(
        main,
        "probe_host_key",
        lambda _target: (_ for _ in ()).throw(AssertionError("reset must not probe SSH")),
    )

    result = asyncio.run(main.extension_reset_ssh_host_key(
        ExtensionHostKeyResetRequest(target_id="saved")
    ))

    assert calls == ["saved"]
    assert result["reset"] is True
    assert result["target"]["host_key_algorithm"] == ""
    assert result["target"]["host_key"] == ""


def test_host_key_reset_route_returns_not_found_without_remote_probe(monkeypatch):
    import main

    monkeypatch.setattr(main.extensions_store, "reset_target_host_key", lambda _target_id: None)
    monkeypatch.setattr(
        main,
        "probe_host_key",
        lambda _target: (_ for _ in ()).throw(AssertionError("reset must not probe SSH")),
    )

    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.extension_reset_ssh_host_key(
            ExtensionHostKeyResetRequest(target_id="missing")
        ))

    assert caught.value.status_code == 404


def test_host_key_confirm_rejects_changed_or_previously_conflicting_key(monkeypatch):
    import main
    from fastapi import HTTPException

    observed = TEST_HOST_KEY
    submitted = "SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    writes = []

    async def current_key(_target):
        return TEST_HOST_KEY_ALGORITHM, observed

    monkeypatch.setattr(main, "probe_host_key", current_key)
    monkeypatch.setattr(main.extensions_store, "upsert_target", lambda data: writes.append(data))

    for stored_key, requested_key in (("", submitted), (submitted, observed)):
        target = ExtensionTarget(
            id="saved", name="Saved", host="safe.example", username="ubuntu",
            host_key_algorithm=TEST_HOST_KEY_ALGORITHM if stored_key else "",
            host_key=stored_key,
        )
        monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id, item=target: item)
        try:
            asyncio.run(main.extension_confirm_ssh_host_key(
                ExtensionHostKeyConfirmRequest(
                    target_id="saved", algorithm=TEST_HOST_KEY_ALGORITHM,
                    fingerprint=requested_key,
                )
            ))
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("a changed host key was persisted")

    assert writes == []


def test_host_key_confirm_rejects_algorithm_drift(monkeypatch):
    import main
    from fastapi import HTTPException

    target = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", username="ubuntu",
    )
    writes = []
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(
        main,
        "probe_host_key",
        lambda _target: asyncio.sleep(
            0, result=(TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)
        ),
    )
    monkeypatch.setattr(
        main.extensions_store,
        "confirm_target_host_key",
        lambda *args: writes.append(args),
    )

    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.extension_confirm_ssh_host_key(
            ExtensionHostKeyConfirmRequest(
                target_id="saved",
                algorithm="ecdsa-sha2-nistp256",
                fingerprint=TEST_HOST_KEY,
            )
        ))

    assert caught.value.status_code == 409
    assert writes == []


def test_host_key_pairing_round_trip_is_transient_and_reprobes(monkeypatch):
    import main

    target = ExtensionTarget(id="pair", name="Pair", host="safe.example", username="ubuntu")
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(
        main,
        "probe_host_key",
        lambda _target: asyncio.sleep(0, result=(TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)),
    )
    saved = []
    monkeypatch.setattr(
        main.extensions_store,
        "confirm_target_host_key",
        lambda expected, alg, value: saved.append((expected, alg, value)) or expected.model_copy(
            update={"host_key_algorithm": alg, "host_key": value}
        ),
    )
    main.host_key_pairings.clear()
    started = asyncio.run(main.extension_start_ssh_host_key_pairing(
        ExtensionHostKeyPairingStartRequest(target_id="pair")
    ))
    assert "protocol" not in started
    assert "candidate" not in started
    assert TEST_HOST_KEY not in str(started)
    assert "ssh-secret" not in started["helper_command"]
    assert "/etc/ssh/ssh_host_ed25519_key.pub" in started["helper_command"]
    record = main.host_key_pairings._records[started["pairing_id"]]
    proof = hashlib.sha256(
        f"{record.algorithm}:{record.fingerprint}:{record.challenge}".encode("utf-8")
    ).hexdigest()
    response = "GENBOX-PAIR/1 code=" + record.challenge + " proof=" + proof
    completed = asyncio.run(main.extension_complete_ssh_host_key_pairing(
        ExtensionHostKeyPairingCompleteRequest(pairing_id=started["pairing_id"], response=response)
    ))
    assert completed["verified"] is True
    assert saved and saved[0][1:] == (TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)
    assert started["pairing_id"] not in main.host_key_pairings._records


def test_host_key_pairing_rejects_malformed_or_mismatched_response_and_consumes(monkeypatch):
    import main
    from fastapi import HTTPException

    target = ExtensionTarget(id="pair", name="Pair", host="safe.example", username="ubuntu")
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(
        main,
        "probe_host_key",
        lambda _target: asyncio.sleep(0, result=(TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)),
    )
    main.host_key_pairings.clear()
    started = asyncio.run(main.extension_start_ssh_host_key_pairing(
        ExtensionHostKeyPairingStartRequest(target_id="pair")
    ))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.extension_complete_ssh_host_key_pairing(
            ExtensionHostKeyPairingCompleteRequest(
                pairing_id=started["pairing_id"], response="arbitrary shell; echo secret"
            )
        ))
    assert caught.value.status_code == 400
    with pytest.raises(HTTPException) as replay:
        asyncio.run(main.extension_complete_ssh_host_key_pairing(
            ExtensionHostKeyPairingCompleteRequest(
                pairing_id=started["pairing_id"], response="arbitrary shell; echo secret"
            )
        ))
    assert replay.value.status_code == 409

    started = asyncio.run(main.extension_start_ssh_host_key_pairing(
        ExtensionHostKeyPairingStartRequest(target_id="pair")
    ))
    record = main.host_key_pairings._records[started["pairing_id"]]
    with pytest.raises(HTTPException) as mismatch:
        asyncio.run(main.extension_complete_ssh_host_key_pairing(
            ExtensionHostKeyPairingCompleteRequest(
                pairing_id=started["pairing_id"],
                response="GENBOX-PAIR/1 code=" + record.challenge + " proof=" + "0" * 64,
            )
        ))
    assert mismatch.value.status_code == 400
    assert started["pairing_id"] not in main.host_key_pairings._records


def test_host_key_pairing_cancel_discards_record_without_persisting(monkeypatch):
    import main
    from fastapi import HTTPException

    target = ExtensionTarget(id="pair", name="Pair", host="safe.example", username="ubuntu")
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(
        main,
        "probe_host_key",
        lambda _target: asyncio.sleep(0, result=(TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)),
    )
    persisted = []
    monkeypatch.setattr(main.extensions_store, "confirm_target_host_key", lambda *args: persisted.append(args))
    main.host_key_pairings.clear()
    started = asyncio.run(main.extension_start_ssh_host_key_pairing(
        ExtensionHostKeyPairingStartRequest(target_id="pair")
    ))
    pairing_id = started["pairing_id"]

    cancelled = asyncio.run(main.extension_cancel_ssh_host_key_pairing(
        ExtensionHostKeyPairingCancelRequest(pairing_id=pairing_id)
    ))

    assert cancelled == {"cancelled": True}
    assert pairing_id not in main.host_key_pairings._records
    with pytest.raises(HTTPException) as completion:
        asyncio.run(main.extension_complete_ssh_host_key_pairing(
            ExtensionHostKeyPairingCompleteRequest(pairing_id=pairing_id, response="x" * 20)
        ))
    assert completion.value.status_code == 409
    assert persisted == []


def test_host_key_pairing_rejects_target_mutation_without_persisting(monkeypatch):
    import main
    from fastapi import HTTPException

    target = ExtensionTarget(id="pair", name="Pair", host="safe.example", username="ubuntu")
    current = {"target": target}
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: current["target"])
    monkeypatch.setattr(
        main,
        "probe_host_key",
        lambda _target: asyncio.sleep(0, result=(TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)),
    )
    main.host_key_pairings.clear()
    started = asyncio.run(main.extension_start_ssh_host_key_pairing(
        ExtensionHostKeyPairingStartRequest(target_id="pair")
    ))
    record = main.host_key_pairings._records[started["pairing_id"]]
    current["target"] = target.model_copy(update={"host": "changed.example"})
    proof = hashlib.sha256(
        f"{record.algorithm}:{record.fingerprint}:{record.challenge}".encode("utf-8")
    ).hexdigest()
    response = "GENBOX-PAIR/1 code=" + record.challenge + " proof=" + proof
    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.extension_complete_ssh_host_key_pairing(
            ExtensionHostKeyPairingCompleteRequest(pairing_id=started["pairing_id"], response=response)
        ))
    assert caught.value.status_code == 409


def test_target_identity_generation_survives_delete_and_recreate(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    first = store.save_target_metadata({
        "id": "reused", "name": "VPS", "host": "safe.example", "port": 22, "username": "ubuntu",
    })
    first_digest = store.target_identity_digest(first)
    assert first.identity_version == 1
    assert store.delete_target(first.id) is True
    recreated = store.save_target_metadata({
        "id": "reused", "name": "VPS", "host": "safe.example", "port": 22, "username": "ubuntu",
    })
    assert recreated.identity_version == 2
    assert store.target_identity_digest(recreated) != first_digest
    with pytest.raises(ValueError, match="target_changed"):
        store.confirm_target_host_key(first, TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)


def test_pairing_ui_has_manual_fallback_and_trusted_visibility_guards():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
if(!source.includes("el('extHostKeyPairingManualBtn')"))throw new Error('manual fallback control missing');
if(!source.includes('hostKeyPairingFallback=true'))throw new Error('pairing failure does not enter fallback state');
if(!source.includes("manual.classList.toggle('hidden',!hostKeyPairingFallback)"))throw new Error('manual fallback is not surfaced');
if(!source.includes("visible=!!currentTargetId&&!targetDirty&&!trustedHostKey&&!hostKeyReconfirmationRequired"))throw new Error('pairing visibility does not block recovery bypass');
if(!source.includes("if(hostKeyReconfirmationRequired||!requireBackendOnline()"))throw new Error('recovery guard is missing from host-key actions');
if(!source.includes("extensions.identity_reset_action',window.extensionResetHostKey"))throw new Error('recovery guide can still bypass the explicit reset');
if(!source.includes('sequence!==hostKeyProbeSequence||targetId!==currentTargetId||targetDirty'))throw new Error('pairing start response is not target-bound');
if(!source.includes('pairing!==hostKeyPairing||sequence!==hostKeyProbeSequence'))throw new Error('pairing completion response is not target-bound');
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_pairing_ui_has_expiry_cleanup_and_recovery_state():
    root = Path(__file__).parents[1]
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    markup = (root / "static" / "index.html").read_text(encoding="utf-8")
    styles = (root / "static" / "css" / "extensions.css").read_text(encoding="utf-8")

    assert "hostKeyPairingTimer" in source
    assert "expireHostKeyPairing" in source
    assert "hostKeyPairingSubmitting" in source
    assert "captureHostKeyPairingResponse" in source
    assert "isHostKeyPairingResponse" in source
    assert "response.disabled=!backendOnline||!hostKeyPairing||hostKeyPairingSubmitting||hasResponse" in source
    assert "hostKeyPairing.response=value" in source
    assert "response.value=''" in source
    assert "extHostKeyPairingCancelBtn" in markup
    assert "extHostKeyPairingReceived" in markup
    assert "GENBOX-PAIR/1" not in markup
    assert "GENBOX-PAIR/1" not in (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    assert "extensions.host_key_pairing_expired" in source
    assert "hostKeyReconfirmationRequired" in source
    assert "requireHostKeyReconfirmation()" in source
    assert "extensions.ssh_host_key_mismatch" in source
    assert "extensions.guide_step1_identity_changed" in (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    assert "clearSessionCredentials()" in source.split("function requireHostKeyReconfirmation", 1)[1].split("function invalidatePlanRequest", 1)[0]
    assert "hostKeyReconfirmationRequired&&!hostKeyPairing" in source
    assert "'extensions.guide_step1_credential_after'" in source
    assert "does not deploy or use sudo" in (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    assert 'id="extCredentialTestBtn" onclick="extensionDiscover()"' in markup
    assert 'id="extElevationPanel" class="extension-advanced-credentials"' in markup
    assert "function discoveryCredential()" in source
    assert 'id="extHostKeyPairingState"' in markup
    assert "extension-pairing-command-row" in styles
    assert "@media(max-width:700px)" in styles


def test_identity_reconfirmation_hides_and_clears_session_credentials():
    root = Path(__file__).parents[1]
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    markup = (root / "static" / "index.html").read_text(encoding="utf-8")
    messages = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    styles = (root / "static" / "css" / "extensions.css").read_text(encoding="utf-8")

    assert 'id="extHostKeyReconfirmation"' in markup
    assert 'id="extAuth"' in markup
    assert "function updateHostKeyIdentityView()" in source
    assert "needsHostIdentityConfirmation=!!currentTargetId&&!targetDirty&&!trustedHostKey" in source
    assert "auth.classList.toggle('hidden',needsHostIdentityConfirmation)" in source
    assert "notice.classList.toggle('hidden',needsHostIdentityConfirmation)" in source
    assert "recovery.classList.toggle('hidden',!hostKeyReconfirmationRequired)" in source
    assert 'id="extOnboardingIdentity"' in markup
    assert 'id="extOnboardingCredentials"' in markup
    assert "['extHostKeyReconfirmation','extHostKeyPairing','extHostKeyConfirm']" in source
    save_target = source.split("window.extensionSaveTarget=async function()", 1)[1].split("window.extensionDeleteTarget", 1)[0]
    assert "if(!trustedHostKey)clearSessionCredentials()" in save_target
    assert "extensions.identity_reconfirm_credential_title" in messages
    assert "extensions.identity_reconfirm_credential_body" in messages
    assert ".extension-identity-recovery.hidden{display:none}" in styles


def test_pairing_help_exposes_a_local_only_advanced_recovery_path():
    root = Path(__file__).parents[1]
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    markup = (root / "static" / "index.html").read_text(encoding="utf-8")
    styles = (root / "static" / "css" / "extensions.css").read_text(encoding="utf-8")

    assert 'id="extHostKeyPairingHelpBtn"' in markup
    assert 'aria-controls="extHostKeyPairingHelp"' in markup
    assert 'id="extHostKeyPairingHelp"' in markup
    assert 'id="extHostKeyPairingAdvancedBtn"' in markup
    assert "extensionToggleHostKeyPairingHelp" in source
    assert "extensionOpenHostKeyManualHelp" in source
    assert "event.key==='Escape'" in source
    assert "extensionToggleAdvanced()" in source
    assert "/api/extensions/ssh/" not in source.split(
        "window.extensionOpenHostKeyManualHelp=function(){", 1
    )[1].split("\n", 1)[0]
    assert ".extension-pairing-help" in styles


def test_server_connector_entry_is_honest_and_preserves_ssh_fallback():
    root = Path(__file__).parents[1]
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    markup = (root / "static" / "index.html").read_text(encoding="utf-8")
    messages = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    styles = (root / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    strategy = (root / "docs" / "P4-SERVER-CONNECTOR-UX-STRATEGY.md").read_text(encoding="utf-8")

    assert 'id="extConnectorPathTitle"' in markup
    assert 'id="extUseSshFallbackBtn"' in markup
    assert 'onclick="extensionBeginSshSetup()"' in markup
    assert "extensions.connection_connector_unavailable" in markup
    assert "extensions.connection_ssh_status" in messages
    assert "extensions.connection_connector_unavailable" in messages
    assert "window.extensionUseSshFallback=function()" in source
    fallback = source.split("window.extensionUseSshFallback=function()", 1)[1].split("function message", 1)[0]
    assert "_authFetch" not in fallback
    assert "window.extensionBeginSshSetup()" in fallback
    assert ".extension-connection-path-grid" in styles
    assert ".extension-connection-option button{width:100%}" in styles
    assert "remains **SSH (advanced)**" in strategy
    assert "does\nnot claim an installed connector" in strategy.lower()


def test_personal_onboarding_uses_exclusive_views_and_preserves_the_deploy_path():
    root = Path(__file__).parents[1]
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    markup = (root / "static" / "index.html").read_text(encoding="utf-8")
    styles = (root / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    strategy = (root / "docs" / "P4-PERSONAL-SERVER-ONBOARDING-UX-STRATEGY.md").read_text(encoding="utf-8")

    for view_id in (
        "extOnboardingLanding",
        "extOnboardingDetails",
        "extOnboardingIdentity",
        "extOnboardingCredentials",
        "extOnboardingReady",
    ):
        assert f'id="{view_id}"' in markup
    assert "function personalOnboardingView()" in source
    assert "if(!currentTargetId||targetDirty)return 'details'" in source
    assert "if(!trustedHostKey)return 'identity'" in source
    assert "if(!hasCredential()||!sshVerified)return 'credentials'" in source
    assert "return 'ready'" in source
    assert "function renderPersonalOnboarding()" in source
    assert "var renderPersonalOnboardingBase=renderPersonalOnboarding;" in source
    assert "if(currentExtensionStep!==1){var guide=el('extNoviceGuide');if(guide)guide.classList.remove('hidden');return}" in source
    assert "landing.classList.toggle('hidden',view!=='landing')" in source
    assert "credentials.classList.toggle('hidden',view!=='credentials')" in source
    assert "ready.classList.toggle('hidden',view!=='ready')" in source
    assert "if(!trustedHostKey)clearSessionCredentials()" in source
    assert "window.extensionBeginDeploymentPlanning=function(){if(requireVerifiedSsh())extensionNext(2)}" in source
    assert ".extension-onboarding-view" in styles
    assert "Remove the user-visible `连接服务器` mega-step" in strategy
    assert "SSH still binds a target to its canonical host-key algorithm and SHA-256" in strategy


def test_deployment_parameters_are_hidden_until_environment_discovery():
    root = Path(__file__).parents[1]
    markup = (root / "static" / "index.html").read_text(encoding="utf-8")
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    assert '<div id="extDeploymentOptions" class="hidden">' in markup
    assert "options=el('extDeploymentOptions')" in source
    assert "var renderDiscoveryWithDeploymentOptions=renderDiscovery;" in source
    assert "options.classList.remove('hidden')" in source
    assert "window.extensionGoToStep=function(step){if(Number(step)===2&&!requireVerifiedSsh())return;extensionNext(step)}" in source


def test_generated_plan_renders_a_non_secret_review_summary_before_deploy():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    translations = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")

    assert "function renderPlanPreview(plan,body)" in source
    assert "body.instance_id" in source
    assert "body.service_port" in source
    assert "body.image" in source
    assert "plan.registers_locally" in source
    assert "el('extPlanPreview').innerHTML=renderPlanPreview(plan,body)" in source
    assert "extensions.plan_review_confirm" in source
    assert "function confirmDeploymentStart()" in source
    assert "extensions.deploy_confirm_prompt" in source
    assert "extensions.deploy_confirm_cancelled" in source
    preview_function = source.split("function renderPlanPreview(plan,body)", 1)[1].split(
        "window.extensionSelectExisting", 1
    )[0]
    assert "host_fingerprint" not in preview_function
    for key in (
        "extensions.plan_review_title",
        "extensions.plan_review_instance",
        "extensions.plan_review_port",
        "extensions.plan_review_image",
        "extensions.plan_review_method",
        "extensions.plan_review_scope",
        "extensions.plan_review_confirm",
        "extensions.deploy_confirm_prompt",
        "extensions.deploy_confirm_cancelled",
    ):
        assert key in translations
    assert 'id="extPlanConfirm"' in html
    assert 'id="extDeployConfirm"' in html
    assert 'extensionConfirmPlanDiscovery' in source
    assert 'extensionConfirmDeployment' in source
    assert "window.confirm(i18nText('extensions.plan_discovery_confirm'))" not in source
    assert "window.confirm(i18nText('extensions.deploy_confirm_prompt'))" not in source


def test_empty_isolated_deployment_requires_an_immutable_remote_image_before_ssh_discovery(monkeypatch):
    import main

    target = ExtensionTarget(
        id="isolated-target", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY,
    )
    discovery_calls = []

    async def forbidden_discovery(_request, *, path_checks=None):
        discovery_calls.append(path_checks)
        raise AssertionError("image validation must happen before SSH discovery")

    monkeypatch.setattr(main, "discover_environment", forbidden_discovery)
    body = ExtensionPlanRequest(
        target=target,
        credential=SSHCredential(password="session-only"),
        strategy="isolated",
        clone_scope="empty",
        image="chatgpt2api:local",
    )

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(main.extension_deploy_plan(body))

    assert excinfo.value.status_code == 400
    assert "不可变镜像" in str(excinfo.value.detail)
    assert discovery_calls == []


def test_plan_route_requires_explicit_read_only_recheck_approval(monkeypatch):
    import main

    target = ExtensionTarget(
        id="target-plan-approval", name="VPS", host="safe.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
    )
    discovery_called = False

    async def forbidden_discovery(_request, **_kwargs):
        nonlocal discovery_called
        discovery_called = True
        raise AssertionError("plan discovery must not run without explicit approval")

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "discover_environment", forbidden_discovery)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(main.extension_deploy_plan(ExtensionPlanRequest(
            target=target,
            credential=SSHCredential(password="session-only-secret"),
            image=TEST_DEPLOYMENT_IMAGE,
        )))

    detail = excinfo.value.detail
    assert excinfo.value.status_code == 400
    assert detail["diagnostic"]["code"] == "plan_discovery_approval_required"
    assert detail["diagnostic"]["retry_safe"] is True
    assert discovery_called is False
    assert "safe.example" not in str(detail)
    assert "deploy-user" not in str(detail)
    assert "session-only-secret" not in str(detail)


@pytest.mark.parametrize("stall_call", (1, 2))
def test_plan_discovery_timeout_cancels_each_preflight_check(monkeypatch, stall_call):
    import main

    target = ExtensionTarget(
        id="target-plan-timeout", name="VPS", host="safe.example", username="deploy-user",
        target_role="isolated-development",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
    )
    calls = []
    cancelled = []

    async def discovery(_request, **kwargs):
        calls.append(kwargs)
        if len(calls) == stall_call:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(stall_call)
                raise
        return {"instances": []}

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "discover_environment", discovery)
    monkeypatch.setattr(main.deployment_plans, "path_requirements", lambda *_args: {"checks": []})
    monkeypatch.setattr(main, "READ_ONLY_DISCOVERY_TIMEOUT_SECONDS", 0.001)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(main.extension_deploy_plan(ExtensionPlanRequest(
            target=target,
            credential=SSHCredential(password="session-only-secret"),
            image=TEST_DEPLOYMENT_IMAGE,
            approve_plan_discovery=True,
        )))

    detail = excinfo.value.detail
    assert excinfo.value.status_code == 400
    assert detail["diagnostic"] == {
        "code": "plan_discovery_timeout",
        "stage": "plan_discovery",
        "retry_safe": True,
    }
    assert len(calls) == stall_call
    assert cancelled == [stall_call]
    assert "safe.example" not in str(detail)
    assert "deploy-user" not in str(detail)
    assert "session-only-secret" not in str(detail)


def test_immutable_image_gate_allows_existing_and_source_clone_but_not_floating_empty_deployments():
    immutable = "registry.example/chatgpt2api@sha256:" + ("a" * 64)

    assert is_immutable_image_reference(immutable) is True
    assert is_immutable_image_reference("chatgpt2api:local") is False
    assert is_immutable_image_reference("ghcr.io/yukkcat/chatgpt2api:latest") is False

    validate_deployment_image(immutable, "isolated", "empty")
    validate_deployment_image("chatgpt2api:local", "existing", "empty")
    validate_deployment_image("genbox-chatgpt2api-source:local", "isolated", "working-copy")
    with pytest.raises(ValueError, match="不可变镜像"):
        validate_deployment_image("chatgpt2api:local", "isolated", "empty")


def test_image_input_explains_remote_digest_requirement_and_blocks_plan_request_locally():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    translations = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")

    assert 'id="extImage" value="ghcr.io/liwei9745/chatgpt2api@sha256:c9357b45b1339d2be4e4a02eb48f059562890f14bd9757b924d7fd7621b9e076"' in html
    assert 'id="extImagePreset" onchange="extensionSelectImagePreset(this)"' in html
    assert '<option value="project" data-i18n="extensions.image_preset_project">' in html
    assert '<option value="upstream" disabled data-i18n="extensions.image_preset_upstream">' in html
    assert '<option value="custom" data-i18n="extensions.image_preset_custom">' in html
    assert 'id="extImagePresetHelp" data-i18n="extensions.image_source_select_help"' in html
    assert 'aria-describedby="extImageHelp extImagePresetNotice extImageCheckStatus"' in html
    assert 'id="extImageCheckBtn" onclick="extensionCheckImageIntegration()"' in html
    assert 'id="extImageCheckStatus"' in html
    assert 'data-i18n="extensions.image_source_help"' in html
    assert "function needsImmutableImage(body)" in source
    assert "function isImmutableImageReference(value)" in source
    assert "function requireDeployableImage(body)" in source
    assert "guide_step2_image_needed" in source
    assert "extensions.prepare_deploy_image" in source
    assert "if(!requireDeployableImage(body))return" in source
    assert "extensions.image_source_help" in translations
    assert "extensions.image_source_required" in translations
    assert "extensions.image_preset_project" in translations
    assert "extensions.image_preset_upstream" in translations
    assert "extensions.image_preset_custom" in translations
    assert "extensions.image_source_select_help" in translations
    assert "extensions.image_check_action" in translations
    assert "extensions.image_check_integrated" in translations
    assert "extensionSelectImagePreset" in source
    assert "extensionCheckImageIntegration" in source


def test_frontend_immutable_image_validation_accepts_a_pinned_ghcr_reference():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
;(async () => {
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.replace(/\}\)\(\);\s*$/, 'window.__imageReferenceTest={isImmutableImageReference,submitInvalidPlan:async function(){sshVerified=true;return window.extensionCreatePlan()}};})();');
global.window = global;
const controls = new Map();
function control(id) {
  if (!controls.has(id)) {
    controls.set(id, {
      value: '', textContent: '', disabled: false, dataset: {}, focused: false,
      classList: { add(){}, remove(){}, toggle(){} },
      focus(){ this.focused = true; }, setAttribute(){}, removeAttribute(){},
      querySelector(){ return null; }, querySelectorAll(){ return []; },
    });
  }
  return controls.get(id);
}
global.document = {
  getElementById: control,
  querySelector(selector) {
    if (selector.includes('extStrategy')) return { value: 'isolated' };
    if (selector.includes('extDeployMode')) return { value: 'compose' };
    if (selector.includes('extIntent')) return { value: 'development' };
    return null;
  },
  querySelectorAll(){ return []; },
  addEventListener(){},
};
global.i18nText = key => key;
global.escHtml = value => String(value || '');
let requestCount = 0;
global._authFetch = async () => { requestCount += 1; throw new Error('network request was not expected'); };
eval(source);
const digest = 'a'.repeat(64);
if (!window.__imageReferenceTest.isImmutableImageReference('ghcr.io/example/chatgpt2api@sha256:' + digest)) {
  throw new Error('pinned GHCR image was rejected');
}
if (window.__imageReferenceTest.isImmutableImageReference('ghcr.io/example/chatgpt2api:latest')) {
  throw new Error('mutable latest tag was accepted');
}
control('extImage').value = 'ghcr.io/example/chatgpt2api:latest';
await window.__imageReferenceTest.submitInvalidPlan();
if (requestCount !== 0) throw new Error('invalid image started a plan request');
if (!control('extImage').focused) throw new Error('invalid image did not focus the image input');
if (control('extensionMessage').textContent !== 'extensions.image_source_required') {
  throw new Error('invalid image did not show the recovery message');
}
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_frontend_image_presets_toggle_project_and_custom_input_modes():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.replace(/\}\)\(\);\s*$/, 'window.__presetTest={select:window.extensionSelectImagePreset};})();');
global.window = global;
const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    const classes = new Set();
    elements.set(id, {
      value: '', readOnly: false, placeholder: '', textContent: '', disabled: false,
      checked: false,
      classList: { add(name){classes.add(name)}, remove(name){classes.delete(name)}, toggle(name, on){if(on)classes.add(name);else classes.delete(name)}, contains(name){return classes.has(name)} },
      focus(){}, setAttribute(){}, removeAttribute(){}, querySelector(){return null}, querySelectorAll(){return []}, appendChild(){}, contains(){return false},
    });
  }
  return elements.get(id);
}
global.document = {
  getElementById(id) { return id === 'extGuidePrimaryBtn' ? null : element(id); },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
};
global.i18nText = key => key;
eval(source);
const image = element('extImage');
const notice = element('extImagePresetNotice');
window.__presetTest.select('project');
if (!image.readOnly || !image.value.startsWith('ghcr.io/liwei9745/chatgpt2api@sha256:')) throw new Error('project preset did not lock and fill the image input');
if (element('extImagePreset').value !== 'project') throw new Error('project preset did not synchronize the select');
if (notice.textContent !== 'extensions.image_preset_project_status') throw new Error('project status was not shown');
window.__presetTest.select('custom');
if (image.readOnly || image.value !== '' || image.placeholder !== 'extensions.image_custom_placeholder') throw new Error('custom preset did not clear and unlock the image input');
if (element('extImagePreset').value !== 'custom') throw new Error('custom preset did not synchronize the select');
if (notice.textContent !== 'extensions.image_preset_custom_status') throw new Error('custom status was not shown');
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_frontend_image_integration_check_only_uses_local_check_endpoint():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
let source = fs.readFileSync(process.argv[1], 'utf8');
global.window = global;
const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    const classes = new Set();
    elements.set(id, {
      value: '', readOnly: false, placeholder: '', textContent: '', disabled: false, className: '', checked: false,
      classList: { add(name){classes.add(name)}, remove(name){classes.delete(name)}, toggle(name, on){if(on)classes.add(name);else classes.delete(name)}, contains(name){return classes.has(name)} },
      focus(){}, setAttribute(){}, removeAttribute(){}, querySelector(){return null}, querySelectorAll(){return []}, appendChild(){}, contains(){return false},
    });
  }
  return elements.get(id);
}
global.document = {
  getElementById(id) { return id === 'extGuidePrimaryBtn' ? null : element(id); },
  querySelector() { return null; }, querySelectorAll() { return []; }, addEventListener() {},
};
global.i18nText = key => key;
let request;
global._authFetch = async (url, options) => {
  request = {url, options};
  return {ok:true, text:async()=>JSON.stringify({image:element('extImage').value,status:'integrated',integration:'genbox-push-v1'})};
};
eval(source);
element('extImage').value = 'ghcr.io/liwei9745/chatgpt2api@sha256:' + 'c9357b45b1339d2be4e4a02eb48f059562890f14bd9757b924d7fd7621b9e076';
(async () => {
  await window.extensionCheckImageIntegration();
  if (!request || request.url !== '/api/extensions/images/integration-check') throw new Error('wrong integration-check endpoint');
  if (JSON.parse(request.options.body).image !== element('extImage').value) throw new Error('wrong image payload');
  if (element('extImageCheckStatus').textContent !== 'extensions.image_check_integrated') throw new Error('integrated image result was not rendered');
  if (element('extImageCheckBtn').disabled) throw new Error('check button was not restored');
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_step_two_restores_the_visible_novice_action_guide_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.replace(/\}\)\(\);\s*$/, 'window.__guideTest={showStepTwo(){currentExtensionStep=2;renderPersonalOnboarding()}};})();');
const elements = new Map();
function element(id){
  if(!elements.has(id)){
    const classes = new Set(id === 'extNoviceGuide' ? ['hidden'] : []);
    elements.set(id,{value:'',textContent:'',innerHTML:'',disabled:false,dataset:{},classList:{add:n=>classes.add(n),remove:n=>classes.delete(n),toggle:(n,on)=>on?classes.add(n):classes.delete(n),contains:n=>classes.has(n)},querySelector(){return null},querySelectorAll(){return []},focus(){},setAttribute(){},removeAttribute(){}});
  }
  return elements.get(id);
}
global.window = global;
global.document = {getElementById:element,querySelector(){return null},querySelectorAll(){return []},addEventListener(){}};
global.i18nText = key => key;
global.escHtml = value => String(value || '');
eval(source);
window.__guideTest.showStepTwo();
if(element('extNoviceGuide').classList.contains('hidden')) throw new Error('step two left its primary action guide hidden');
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_browser_hides_duplicate_endpoint_records_without_weakening_host_key_checks():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.replace(/\}\)\(\);\s*$/, 'window.__targetTest={visibleSavedTargets:visibleSavedTargets};})();');
global.window = global;
global.document = {getElementById(){return null},querySelector(){return null},querySelectorAll(){return []},addEventListener(){}};
global.i18nText = key => key;
global.escHtml = value => String(value || '');
eval(source);
const first = {id:'old',host:'safe.example',port:22,username:'ubuntu',host_key_algorithm:'ssh-rsa',host_key:'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',updated_at:'2026-07-26'};
const second = {id:'new',host:'SAFE.EXAMPLE.',port:22,username:'ubuntu',host_key_algorithm:'ssh-rsa',host_key:'SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB',updated_at:'2026-07-27'};
const visible = window.__targetTest.visibleSavedTargets([first, second]);
if(visible.length !== 1 || visible[0].id !== 'new') throw new Error('duplicate endpoint records remained selectable');
if(!/^SHA256:/.test(visible[0].host_key)) throw new Error('selected record lost its host-key trust pair');
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_confirm_target_host_key_is_cross_thread_compare_and_swap(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    store.host_key_pairings.clear()
    first = store.save_target_metadata({
        "id": "race", "name": "VPS", "host": "safe.example", "port": 22, "username": "ubuntu",
    })
    expected_a = store.get_target("race")
    expected_b = store.get_target("race")
    barrier = threading.Barrier(2)
    results = []

    def worker(expected, fingerprint):
        barrier.wait()
        try:
            saved = store.confirm_target_host_key(expected, TEST_HOST_KEY_ALGORITHM, fingerprint)
            results.append(("saved", saved.host_key))
        except ValueError as exc:
            results.append(("error", str(exc)))

    threads = [
        threading.Thread(target=worker, args=(expected_a, "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")),
        threading.Thread(target=worker, args=(expected_b, "SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    current = store.get_target("race")
    saved = [item for item in results if item[0] == "saved"]
    failed = [item for item in results if item == ("error", "target_changed")]
    assert current is not None
    assert current.identity_version == first.identity_version
    assert len(saved) == 1
    assert len(failed) == 1
    assert current.host_key == saved[0][1]


def test_extension_ssh_route_hides_unclassified_raw_exception(monkeypatch):
    import main
    from fastapi import HTTPException

    target = ExtensionTarget(
        id="vps", name="VPS", host="hidden.example", username="hidden-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
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
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
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
        (main.extension_deploy_plan, ExtensionPlanRequest(
            target=target, credential=credential, image=TEST_DEPLOYMENT_IMAGE,
            approve_plan_discovery=True,
        )),
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


def test_ssh_ui_has_no_username_default_and_keeps_elevation_secrets_session_only():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    username_tag = next(line for line in html.splitlines() if 'id="extUsername"' in line)
    assert 'value="ubuntu"' not in username_tag
    assert 'value=""' in username_tag
    assert 'id="extPassphrase"' in html
    assert 'id="extElevation"' in html
    assert 'value="none"' in html
    assert 'value="passwordless_sudo"' in html
    assert 'value="password_sudo"' in html
    assert 'id="extReuseSshPassword"' in html
    assert "确认并在 GenBox 本地登记" in html
    assert "passphrase:authMode==='key'?el('extPassphrase').value:''" in js
    assert "reuse_ssh_password:authMode==='password'" in js
    assert "el('extUsername').value=''" in js
    assert "sshVerified=p.can_deploy===true" in js
    assert "localStorage.setItem('extPassphrase'" not in js
    assert "sessionStorage.setItem('extPassphrase'" not in js


def test_network_recovery_and_auth_key_layout_stack_at_phone_width():
    css = (Path(__file__).parents[1] / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    html = (Path(__file__).parents[1] / "static" / "index.html").read_text(encoding="utf-8")

    assert "@media(max-width:480px){.extension-network-recovery{align-items:stretch;flex-direction:column}" in css
    assert ".extension-auth-key-panel .extension-copy-row{display:grid;grid-template-columns:minmax(0,1fr) auto}" in css
    assert 'id="extNetworkToken" type="password"' in html
    assert 'maxlength="4096"' in html


def test_deploy_completion_opens_delivery_pane_without_falsely_finishing_network():
    html = (Path(__file__).parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    script = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    completed_handler = script.split("renderTask=async function", 1)[1].split("reconcileAmbiguousDeployment=", 1)[0]
    resume_handler = script.split("async function restoreCompletedNetworkResume", 1)[1].split("renderTask=async function", 1)[0]

    assert "el('extHandoff').classList.remove('hidden')" in completed_handler
    assert "if(delivery.available)" in completed_handler
    assert "extensionNext(delivery.admin_key?5:3)" in completed_handler
    assert "delivery=restoring?{available:false,error:false}:await claimTaskDelivery(taskId,attemptId)" in completed_handler
    assert "await restoreCompletedNetworkResume(taskId,t.recovery_action)" in completed_handler
    assert "extensions.deploy_complete_save_key_then_network" in completed_handler
    assert "claimTaskDelivery(taskId,attemptId)" in completed_handler
    assert "el('extConsoleUrl').value=access.console_url||''" in completed_handler
    assert "setConsoleLoginAccess(access,delivery.admin_key)" in completed_handler
    assert "el('extApiUrl').value=access.api_url||''" in completed_handler
    assert "removeAttribute('href')" in completed_handler
    assert "t.result" not in completed_handler
    assert "t.host_key" not in completed_handler
    assert "t.logs" not in completed_handler
    assert "'/api/extensions/tasks/'+taskId+'/resume'" in resume_handler
    assert "method:'POST'" in resume_handler
    assert "JSON.stringify({target_id:targetId})" in resume_handler
    assert "data.resumable!==true" in resume_handler
    assert "instance_handle:access.handle" in resume_handler
    assert "/api/extensions/instances?target_id=" not in script
    assert 'id="extConsoleLogin"' in html
    assert 'id="extConsoleLoginKey" type="password" autocomplete="off"' in html
    assert 'id="extConsoleLoginRefill" onclick="extensionUseDeliveredAdminKey()"' in html
    assert 'onclick="extensionOpenConsoleLogin()"' in html
    assert "window.open(url,'_blank','noopener')" in script
    assert "window.extensionUseDeliveredAdminKey=function" in script
    assert "setConsoleLoginKeyStatus('extensions.console_login_key_delivered')" in script
    assert "if(delivery)delivery.value=''" in script
    assert "keyInput.value=''" in script


def test_completed_deployment_keeps_a_visible_path_to_plan_a_new_isolated_instance():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    script = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    translations = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")

    assert 'id="extGuideNewDeploymentBtn"' in html
    assert 'onclick="extensionStartNewIsolatedDeployment()"' in html
    assert "window.extensionStartNewIsolatedDeployment=function" in script
    assert "currentDeployment=null;historicalCompletion=null" in script
    assert "clearDeploymentDelivery()" in script
    assert "extensionNext(2)" in script
    assert "/api/extensions/deploy" not in script.split(
        "window.extensionStartNewIsolatedDeployment=function", 1
    )[1].split("function focusSessionCredential", 1)[0]
    assert '"extensions.start_new_isolated"' in translations
    assert '"extensions.new_isolated_started"' in translations


def test_plan_confirmation_and_ambiguous_deploy_failures_use_distinct_recovery_states():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    script = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    translations = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    handler = script.split("window.extensionStartDeploy=async function", 1)[1].split("function setCheck", 1)[0]
    error_mapper = script.split("function extensionError", 1)[1].split("function clearSessionCredentials", 1)[0]

    assert "intent=planRequestBody()" in handler
    assert "service_port:Number(intent.service_port)" in handler
    assert "confirmed_plan_id:currentPlan.id" in handler
    assert "clearSessionCredentials()" in handler
    assert handler.index("await json(await _authFetch('/api/extensions/deploy'") < handler.index("clearSessionCredentials()")
    assert "attemptId=createDeploymentAttemptId()" in handler
    assert handler.index("historicalCompletion=null") < handler.index("deploymentInFlight=true")
    assert "deployment_attempt_id:attemptId" in handler
    assert "await reconcileAmbiguousDeployment(requestOptions,attemptId)" in handler
    assert "if(deploymentAttemptConflict(e))" in handler
    assert "await recoverDeploymentIdentity(e)" in handler
    assert "if(deploymentNoTask(e)){recoverDefinitiveNoTask(e);return}" in handler
    assert "if(!hasCredential())extensionNext(1)" in script
    assert "diagnostic.task_created===false" in script
    assert "deployment_snapshot_changed:'fresh_discovery'" in script
    assert "deployment_resource_conflict:'resource_reservation'" in script
    assert "deployment_plan_identity_mismatch" in script
    assert "retryDeploymentAttemptWithTimeout(probeState,requestOptions)" in script
    assert "selectDeploymentAttemptTask" not in script
    assert "!knownTaskIds[task.id]" not in script
    assert "task.deployment_attempt_id" not in script
    reconciler = script.split("reconcileAmbiguousDeployment=", 1)[1].split("window.extensionStartDeploy", 1)[0]
    assert "active_task_id" not in reconciler
    assert "latest_task_id" not in reconciler
    assert "message(i18nText('extensions.deploy_task_reconcile_pending'),true)" in script
    assert "deployment_plan_service_port_changed:'extensions.deploy_plan_service_port_changed'" in error_mapper
    assert "deployment_plan_image_changed:'extensions.deploy_plan_image_changed'" in error_mapper
    assert "deployment_plan_identity_changed:'extensions.deploy_plan_identity_changed'" in error_mapper
    assert "deployment_snapshot_changed:'extensions.deploy_snapshot_changed'" in error_mapper
    assert "deployment_resource_conflict:'extensions.deploy_resource_conflict'" in error_mapper
    assert "extensions.deploy_confirmation_safe_notice" in error_mapper
    assert "extensions.deploy_task_reconcile_manual" in script
    assert "attempts>=6" in script
    assert "'extensions.regenerate_safe_plan',window.extensionCreatePlan" in script
    assert '"zh-CN":"重新生成安全计划"' in translations
    assert "VPS 未被修改；无任务已创建。" in translations
    assert "The VPS was not changed and no task was created." in translations
    assert "Do not deploy again; GenBox is reconciling the existing task state." in translations
    assert "Do not deploy again; reload and check task status manually." in translations
    assert "The browser could not generate a secure deployment attempt ID" in translations
    assert "verify SSH again before creating a new plan." in translations
    assert '<script src="/static/js/i18n.js?v=18"></script>' in html
    assert '<script src="/static/js/extensions.js?v=31"></script>' in html


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


def test_browser_target_save_reuses_existing_ssh_endpoint_without_replacing_trust(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    original = store.save_target_metadata({
        "id": "trusted-target", "name": "Original", "host": "safe.example", "port": 22,
        "username": "ubuntu", "target_role": "isolated-development",
    })
    trusted = store.upsert_target({
        **original.model_dump(), "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY,
    })

    saved_again = store.save_target_metadata({
        "name": "Renamed", "host": "SAFE.EXAMPLE.", "port": 22,
        "username": "ubuntu", "target_role": "isolated-development",
    })

    assert saved_again.id == trusted.id
    assert saved_again.host_key_algorithm == TEST_HOST_KEY_ALGORITHM
    assert saved_again.host_key == TEST_HOST_KEY
    assert len(store.list_targets()) == 1


def test_browser_target_save_cannot_set_or_replace_host_key(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    injected = "SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    confirmed = TEST_HOST_KEY

    created = store.save_target_metadata({
        "id": "saved", "name": "Saved", "host": "safe.example", "port": 22,
        "username": "ubuntu", "host_key_algorithm": "ssh-rsa", "host_key": injected,
    })
    assert created.host_key_algorithm == ""
    assert created.host_key == ""

    store.upsert_target({
        **created.model_dump(),
        "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": confirmed,
    })
    unchanged = store.save_target_metadata({
        **created.model_dump(), "name": "Renamed", "host_key": injected,
    })
    assert unchanged.name == "Renamed"
    assert unchanged.host_key_algorithm == TEST_HOST_KEY_ALGORITHM
    assert unchanged.host_key == confirmed

    changed = store.save_target_metadata({
        **unchanged.model_dump(), "host": "new.example", "host_key": injected,
    })
    assert changed.host == "new.example"
    assert changed.host_key_algorithm == ""
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
        **injected.model_dump(), "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY,
        "available_networks": ["tailscale"], "network_url": "http://100.64.0.20:8893",
        "network_verified_at": "2026-07-19 12:00:00",
    })
    renamed = store.save_target_metadata({
        **verified.model_dump(), "name": "Renamed",
        "network_url": "http://100.64.0.99:8893", "network_verified_at": "2099-01-01 00:00:00",
    })
    assert renamed.host_key_algorithm == verified.host_key_algorithm
    assert renamed.host_key == verified.host_key
    assert renamed.available_networks == ["tailscale"]
    assert renamed.network_url == verified.network_url
    assert renamed.network_verified_at == verified.network_verified_at

    changed = store.save_target_metadata({**renamed.model_dump(), "host": "new.example"})
    assert changed.host_key_algorithm == ""
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
    fingerprint = TEST_HOST_KEY
    confirmed = store.confirm_target_host_key(original, TEST_HOST_KEY_ALGORITHM, fingerprint)
    assert confirmed.host_key_algorithm == TEST_HOST_KEY_ALGORITHM
    assert confirmed.host_key == fingerprint

    expected = confirmed
    store.save_target_metadata({**confirmed.model_dump(), "host": "changed.example"})
    try:
        store.confirm_target_host_key(expected, TEST_HOST_KEY_ALGORITHM, fingerprint)
    except ValueError as exc:
        assert str(exc) == "target_changed"
    else:
        raise AssertionError("a stale probe overwrote a concurrently changed target")
    current = store.get_target("saved")
    assert current.host == "changed.example"
    assert current.host_key_algorithm == ""
    assert current.host_key == ""


def test_host_key_confirmation_store_fails_closed_on_concurrent_trust_pair_change(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    original = store.upsert_target({
        "id": "saved", "name": "Saved", "host": "safe.example", "port": 22,
        "username": "ubuntu",
    })
    expected = store.confirm_target_host_key(
        original, TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY
    )
    changed = store.upsert_target({
        **expected.model_dump(),
        "host_key_algorithm": "ecdsa-sha2-nistp256",
        "host_key": "SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    })

    with pytest.raises(ValueError, match="^target_changed$"):
        store.confirm_target_host_key(
            expected, TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY
        )

    current = store.get_target("saved")
    assert current.host_key_algorithm == changed.host_key_algorithm
    assert current.host_key == changed.host_key


def test_host_key_reset_store_is_atomic_idempotent_and_clears_old_network_state(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    trusted = store.upsert_target({
        "id": "saved", "name": "Saved", "host": "safe.example", "port": 22,
        "username": "ubuntu", "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY, "available_networks": ["tailscale"],
        "network_url": "http://100.64.0.20:8893",
        "network_verified_at": "2026-07-29 00:00:00",
    })

    reset = store.reset_target_host_key(trusted.id)

    assert reset is not None
    assert reset.host_key_algorithm == ""
    assert reset.host_key == ""
    assert reset.identity_version == trusted.identity_version + 1
    assert reset.available_networks == []
    assert reset.network_url == ""
    assert reset.network_verified_at == ""
    assert store.load_config().target_generations[trusted.id] == reset.identity_version
    with pytest.raises(ValueError, match="^target_changed$"):
        store.confirm_target_host_key(trusted, TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)

    repeated = store.reset_target_host_key(trusted.id)
    assert repeated is not None
    assert repeated.identity_version == reset.identity_version
    assert store.reset_target_host_key("missing") is None


def test_host_key_reset_invalidates_existing_pairing_before_completion(tmp_path, monkeypatch):
    import main

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = store.upsert_target({
        "id": "pair", "name": "Pair", "host": "safe.example", "port": 22,
        "username": "ubuntu", "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY,
    })
    main.host_key_pairings.clear()
    record = main.host_key_pairings.create(target, TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY)
    reset = store.reset_target_host_key(target.id)
    proof = hashlib.sha256(
        f"{record.algorithm}:{record.fingerprint}:{record.challenge}".encode("utf-8")
    ).hexdigest()

    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.extension_complete_ssh_host_key_pairing(
            ExtensionHostKeyPairingCompleteRequest(
                pairing_id=record.pairing_id,
                response="GENBOX-PAIR/1 code=" + record.challenge + " proof=" + proof,
            )
        ))

    assert caught.value.status_code == 409
    assert reset is not None
    assert store.get_target(target.id).host_key == ""


def test_legacy_fingerprint_only_target_is_untrusted_and_rejected_before_remote_work(monkeypatch):
    import main
    from fastapi import HTTPException

    legacy = ExtensionTarget(
        id="legacy", name="Legacy", host="safe.example", port=22,
        username="ubuntu", host_key_algorithm="", host_key=TEST_HOST_KEY,
    )
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: legacy)
    submitted = ExtensionTestRequest(
        target=legacy,
        credential=SSHCredential(password="session-only"),
    )

    with pytest.raises(HTTPException) as caught:
        main._bind_confirmed_extension_target(submitted)

    assert caught.value.status_code == 409
    assert "指纹" in str(caught.value.detail)


def test_all_ssh_routes_bind_to_the_server_confirmed_target(monkeypatch):
    import main
    from fastapi import HTTPException

    confirmed = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", port=22, username="ubuntu",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
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
        (ExtensionPlanRequest(
            target=submitted, credential=credential, image=TEST_DEPLOYMENT_IMAGE,
        ), main.extension_deploy_plan),
        (ExtensionDeployRequest(deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID, target=submitted, credential=credential), main.extension_start_deploy),
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
            if route is main.extension_start_deploy:
                assert exc.detail["diagnostic"] == {
                    "code": "deployment_plan_identity_changed",
                    "stage": "plan_confirmation",
                    "retry_safe": False,
                    "task_created": False,
                }
                assert "重新生成安全计划" in exc.detail["error"]
            else:
                assert "重新保存并确认" in str(exc.detail)
        else:
            raise AssertionError(f"{route.__name__} accepted a client-supplied target identity")


def test_discover_validates_one_read_only_intent_before_running_discovery(monkeypatch):
    import main

    target = ExtensionTarget(
        id="target-read-only", name="VPS", host="safe.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
    )
    calls = []

    async def fake_probe(_target):
        return TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY

    async def fake_discover(request, *, approved_plan):
        calls.append((request, approved_plan))
        return {"environment": {}, "instances": [], "deployment_modes": []}

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "probe_host_key", fake_probe)
    monkeypatch.setattr(main, "discover_environment", fake_discover)
    monkeypatch.setattr(
        main.deployment_plans,
        "public_discovery",
        lambda discovery, _target_id: {"ready": True, **discovery},
    )

    result = asyncio.run(main.extension_discover(ExtensionDiscoveryRequest(
        target=target, credential=SSHCredential(password="session-only"),
    )))

    assert result["ready"] is True
    assert calls and calls[0][0].target == target
    assert [operation["id"] for operation in calls[0][1].operations] == [
        "identity", "os_release", "cpu_architecture", "cpu_count", "memory_summary",
        "home_directory", "python_version", "uv_version", "docker_version", "compose_version", "docker_ps",
        "compose_ls", "listening_ports", "capacity",
    ]


def test_discover_stops_before_authentication_when_read_only_host_key_drifts(monkeypatch):
    import main

    target = ExtensionTarget(
        id="target-read-only", name="VPS", host="safe.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
    )
    discovery_called = False

    async def fake_probe(_target):
        return TEST_HOST_KEY_ALGORITHM, "SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

    async def forbidden_discovery(_request):
        nonlocal discovery_called
        discovery_called = True
        raise AssertionError("discovery must not run after a host-key mismatch")

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "probe_host_key", fake_probe)
    monkeypatch.setattr(main, "discover_environment", forbidden_discovery)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(main.extension_discover(ExtensionDiscoveryRequest(
            target=target, credential=SSHCredential(password="session-only"),
        )))

    detail = excinfo.value.detail
    assert excinfo.value.status_code == 400
    assert detail["diagnostic"]["code"] == "ssh_host_key_mismatch"
    assert discovery_called is False
    assert "safe.example" not in str(detail)
    assert TEST_HOST_KEY not in str(detail)


def test_discover_stops_when_read_only_plan_validation_rejects(monkeypatch):
    import main
    from extensions.read_only_discovery_plan import DiscoveryPlanValidationError

    target = ExtensionTarget(
        id="target-read-only", name="VPS", host="safe.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
    )
    discovery_called = False

    async def fake_probe(_target):
        return TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY

    async def forbidden_discovery(_request):
        nonlocal discovery_called
        discovery_called = True
        raise AssertionError("discovery must not run after a rejected plan")

    def reject_plan(_plan):
        raise DiscoveryPlanValidationError("operations")

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "probe_host_key", fake_probe)
    monkeypatch.setattr(main, "validate_read_only_discovery_plan", reject_plan)
    monkeypatch.setattr(main, "discover_environment", forbidden_discovery)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(main.extension_discover(ExtensionDiscoveryRequest(
            target=target, credential=SSHCredential(password="session-only"),
        )))

    detail = excinfo.value.detail
    assert excinfo.value.status_code == 400
    assert detail["diagnostic"]["code"] == "read_only_discovery_plan_rejected"
    assert discovery_called is False


def test_discover_times_out_and_cancels_a_stalled_read_only_check(monkeypatch):
    import main

    target = ExtensionTarget(
        id="target-read-only", name="VPS", host="safe.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
    )
    cancelled = []

    async def fake_probe(_target):
        return TEST_HOST_KEY_ALGORITHM, TEST_HOST_KEY

    async def stalled_discovery(_request, *, approved_plan):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    monkeypatch.setattr(main, "probe_host_key", fake_probe)
    monkeypatch.setattr(main, "discover_environment", stalled_discovery)
    monkeypatch.setattr(main, "READ_ONLY_DISCOVERY_TIMEOUT_SECONDS", 0.001)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(main.extension_discover(ExtensionDiscoveryRequest(
            target=target, credential=SSHCredential(password="session-only-secret"),
        )))

    detail = excinfo.value.detail
    assert excinfo.value.status_code == 400
    assert detail["diagnostic"]["code"] == "read_only_discovery_timeout"
    assert detail["diagnostic"]["stage"] == "environment_discovery"
    assert cancelled == [True]
    assert "safe.example" not in str(detail)
    assert "deploy-user" not in str(detail)
    assert "session-only-secret" not in str(detail)
    assert TEST_HOST_KEY not in str(detail)


def test_confirmed_target_binding_overrides_client_trust_fields(monkeypatch):
    import main

    confirmed = ExtensionTarget(
        id="saved", name="Saved", host="safe.example", port=22, username="ubuntu",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
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
    assert bound.expected_host_key_algorithm == confirmed.host_key_algorithm
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


def test_existing_registration_preserves_owned_fields_and_rejects_cross_target_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    original = store.upsert_instance({
        "id": "shared-instance",
        "target_id": "target-a",
        "service_port": 33010,
        "install_dir": "/srv/genbox/app",
        "data_dir": "/srv/genbox/app/data",
        "image": "image@sha256:one",
        "status": "running",
        "managed": True,
        "ownership": "managed",
        "container_id": "abc123",
    })

    refreshed = store.upsert_instance({
        "id": original.id,
        "target_id": "target-a",
        "service_port": 34000,
        "install_dir": "",
        "data_dir": "",
        "image": "",
        "status": "",
        "managed": False,
        "ownership": "",
        "container_id": "",
    })

    assert refreshed.managed is True
    assert refreshed.service_port == 33010
    assert refreshed.status == "running"
    assert refreshed.data_dir == "/srv/genbox/app/data"
    assert refreshed.ownership == "managed"
    assert refreshed.container_id == "abc123"

    with pytest.raises(ValueError, match="instance_id_conflicts_with_another_target"):
        store.upsert_instance({
            "id": original.id,
            "target_id": "target-b",
            "service_port": 33010,
            "install_dir": "/other",
            "data_dir": "/other/data",
            "image": "image@sha256:two",
        })


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
                result.stdout = "/home/deploy-user"
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(request):
        return Connection(), TEST_HOST_KEY

    async def run():
        from extensions import orchestrator

        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
        target = ExtensionTarget(
            id="t", name="VPS", host="host.example", username="deploy-user",
            host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
        )
        credential = SSHCredential(private_key="test-private-key", passphrase="encrypted-key-passphrase")
        fresh_discovery = deployment_discovery(
            privileges={
                **privilege_snapshot(auth_kind="private_key"),
                "is_root": True,
                "elevated_docker_access": True,
                "can_admin": True,
                "diagnostic_code": "uid_0",
            },
            path_conditions=isolated_empty_path_conditions(),
        )
        plan_manager = DeploymentPlanManager()
        plan = plan_manager.create(
            ExtensionPlanRequest(target=target, credential=credential, service_port=33010),
            fresh_discovery,
        )
        monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)
        async def fake_discover(_request, *, path_checks=None):
            return copy.deepcopy(fresh_discovery)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target, credential=credential,
            instance_id="chatgpt2api-dev", confirmed_plan_id=plan["id"],
        )
        task_id = await manager.create(request)
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "completed"
        assert state["progress"] == 100
        assert all(step["status"] == "success" for step in state["steps"])
        assert "test-private-key" not in json.dumps(state)
        assert "encrypted-key-passphrase" not in json.dumps(state)
        assert "result" not in state
        assert task_id in manager.deliveries
        persisted = (tmp_path / "extension_tasks.json").read_text(encoding="utf-8")
        assert "test-private-key" not in persisted
        assert "encrypted-key-passphrase" not in persisted
        rebuilt = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        recovered = rebuilt.get(task_id)
        assert recovered["status"] == "completed"
        assert "result" not in recovered
        assert recovered["recovery_action"] == "reverify_ownership_and_rotate_admin_key"
        assert rebuilt.take_delivery(task_id, DEPLOYMENT_ATTEMPT_ID) is None
        delivered = manager.take_delivery(task_id, DEPLOYMENT_ATTEMPT_ID)
        assert delivered["admin_key"].startswith("gbx-")
        assert set(delivered["instance"]) == {
            "handle", "project", "managed", "strategy", "deployment_mode", "running", "console_url", "api_url",
            "target_name", "vps_host", "vps_port", "service_port", "created_at", "updated_at",
        }
        assert manager.take_delivery(task_id, DEPLOYMENT_ATTEMPT_ID) is None

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
                result.stdout = "/home/deploy-user"
            elif command == "sudo -n true >/dev/null 2>&1":
                result.exit_status = 1
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(request):
        return connection, TEST_HOST_KEY

    async def run():
        from extensions import orchestrator

        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
        target = ExtensionTarget(
            id="t", name="VPS", host="host.example", username="deploy-user",
            host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
        )
        credential = SSHCredential(password="secret", sudo_password="sudo-secret", elevation="password_sudo")
        source = {
            "id": "chatgpt2api-warp", "container_id": "source-container", "name": "source-app",
            "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
            "status": "Up 1 hour", "ports": "0.0.0.0:3000->80/tcp",
            "published_ports": [3000], "service_port": 3000,
            "compose_project": "source-project", "compose_service": "app",
            "working_dir": "/root/chatgpt2api", "data_dir": "/root/chatgpt2api/data",
            "config_file": "/root/chatgpt2api/config.json", "data_size_mb": 10,
            "clone_available": True, "managed": False, "ownership": "compose",
        }
        fresh_discovery = deployment_discovery(
            instances=[source],
            privileges=privilege_snapshot(elevation="password_sudo", can_admin=True),
            listening_ports=[3000],
            path_conditions=source_clone_path_conditions(),
        )
        plan_manager = DeploymentPlanManager()
        plan = plan_manager.create(ExtensionPlanRequest(
            target=target, credential=credential, service_port=33010,
            clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
        ), fresh_discovery)
        monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)
        async def fake_discover(_request, *, path_checks=None):
            return copy.deepcopy(fresh_discovery)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target, credential=credential,
            instance_id="chatgpt2api-dev", confirmed_plan_id=plan["id"],
            clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
        )

        task_id = await manager.create(request)
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
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="deploy-user", host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY)
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
    )
    discovery = deployment_discovery(
        listening_ports=[33010],
        path_conditions=isolated_empty_path_conditions(target_port_unoccupied=False),
    )
    try:
        manager.create(request, discovery)
    except ValueError as exc:
        assert "端口" in str(exc)
    else:
        raise AssertionError("occupied port was accepted")


def test_deployment_plan_is_scoped_and_non_destructive():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="deploy-user", host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY)
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
    )
    plan = manager.create(request, deployment_discovery())
    internal_plan = manager.plans[plan["id"]]
    serialized = json.dumps(plan, ensure_ascii=False)
    assert internal_plan["compose_project"] == "genbox-chatgpt2api-chatgpt2api-dev"
    assert internal_plan["host"] == "host.example"
    assert internal_plan["ssh_port"] == 22
    assert internal_plan["username"] == "deploy-user"
    assert internal_plan["host_fingerprint"] == TEST_HOST_KEY
    assert internal_plan["auth_kind"] == "password"
    assert internal_plan["elevation_contract"] == "none"
    assert internal_plan["verified_capability"]["can_deploy"] is True
    assert "docker rm" not in serialized
    assert "secret" not in serialized


def test_existing_plan_binds_discovery_and_local_registration_preserves_managed_ownership(tmp_path, monkeypatch):
    from extensions import orchestrator

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = ExtensionTarget(
        id="target-a",
        name="VPS",
        host="host.example",
        username="deploy-user",
        host_key=TEST_HOST_KEY,
        chatgpt2api_port=33010,
    )
    credential = SSHCredential(password="session-secret")
    store.upsert_instance({
        "id": "existing-app",
        "target_id": target.id,
        "service_port": 33010,
        "install_dir": "/trusted/app",
        "data_dir": "/trusted/app/data",
        "image": "trusted-image",
        "status": "running",
        "managed": True,
        "ownership": "managed",
        "container_id": "trusted-container",
    })
    discovered = {
        "id": "existing-app",
        "container_id": "detected-container",
        "name": "existing-container",
        "image": "detected-image",
        "source_image_id": "sha256:detected",
        "status": "",
        "ports": "0.0.0.0:33010->80/tcp",
        "published_ports": [33010],
        "service_port": 33010,
        "compose_project": "existing-project",
        "compose_service": "app",
        "working_dir": "/detected/app",
        "data_dir": "",
        "config_file": "/detected/config.json",
        "data_size_mb": None,
        "clone_available": False,
        "managed": False,
        "ownership": "unmanaged",
    }
    manager = DeploymentPlanManager()
    fresh_discovery = deployment_discovery(
        instances=[discovered], listening_ports=[33010],
        path_conditions=existing_path_conditions(),
    )
    plan = manager.create(
        ExtensionPlanRequest(
            target=target,
            credential=credential,
            instance_id="existing-app",
            strategy="existing",
            service_port=33010,
        ),
        fresh_discovery,
    )
    internal_plan = manager.plans[plan["id"]]
    assert internal_plan["existing_snapshot"] == fresh_discovery["instances"][0]
    assert "session-secret" not in json.dumps(plan)

    class Result:
        def __init__(self, status=0, stdout=""):
            self.exit_status = status
            self.stdout = stdout

    class Connection:
        async def run(self, command, check=False, input=None, **_kwargs):
            if command == 'printf %s "$HOME"':
                return Result(stdout="/home/deploy-user")
            if command == "id -u":
                return Result(stdout="1000")
            if command == "docker version >/dev/null 2>&1":
                return Result(0)
            if command == "sudo -n true >/dev/null 2>&1":
                return Result(1)
            raise AssertionError(f"existing registration attempted unexpected remote command: {command}")

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), TEST_HOST_KEY

    async def run():
        monkeypatch.setattr(orchestrator, "deployment_plans", manager)
        monkeypatch.setattr(orchestrator, "_connect", fake_connect)
        async def fake_discover(_request, *, path_checks=None):
            return copy.deepcopy(fresh_discovery)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        tasks = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        task_id = await tasks.create(ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target,
            credential=credential,
            image=internal_plan["image"],
            instance_id="existing-app",
            strategy="existing",
            confirmed_plan_id=plan["id"],
        ))
        await tasks.runners[task_id]
        assert tasks.get(task_id)["status"] == "completed"

    asyncio.run(run())
    registered = store.get_instance("existing-app")
    assert registered.managed is True
    assert registered.status == "running"
    assert registered.data_dir == "/trusted/app/data"
    assert registered.ownership == "managed"


@pytest.mark.parametrize(("published_ports", "service_port", "requested_port"), [
    ([], None, 33010),
    ([33010, 33443], None, 33010),
    ([33011], 33011, 33010),
])
def test_existing_plan_rejects_missing_ambiguous_or_mismatched_structured_port(
    published_ports, service_port, requested_port,
):
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY,
        chatgpt2api_port=requested_port,
    )
    existing = {
        "id": "external-app", "container_id": "container-a", "name": "external-app",
        "image": "example.invalid/app:stable", "source_image_id": "sha256:image",
        "status": "Up 1 hour", "ports": "display-only",
        "published_ports": published_ports, "service_port": service_port,
        "compose_project": "external-project", "compose_service": "app",
        "working_dir": "/srv/external", "data_dir": "/srv/external/data",
        "config_file": "/srv/external/config.json", "data_size_mb": 10,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    with pytest.raises(ValueError):
        DeploymentPlanManager().create(ExtensionPlanRequest(
            target=target, credential=SSHCredential(password="session-only"),
            instance_id="external-app", strategy="existing", service_port=requested_port,
        ), deployment_discovery(
            instances=[existing], listening_ports=published_ports,
            path_conditions=existing_path_conditions(),
        ))


def test_external_registration_accepts_only_the_structured_discovery_port(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    store.upsert_instance({
        "id": "external-app", "target_id": "target-a", "service_port": 32000,
        "install_dir": "/srv/external", "data_dir": "/srv/external/data",
        "image": "example.invalid/app:stable", "managed": False,
    })
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
    )
    existing = {
        "id": "external-app", "container_id": "container-a", "name": "external-app",
        "image": "example.invalid/app:stable", "source_image_id": "sha256:image",
        "status": "Up 1 hour", "ports": "0.0.0.0:33010->80/tcp",
        "published_ports": [33010], "service_port": 33010,
        "compose_project": "external-project", "compose_service": "app",
        "working_dir": "/srv/external", "data_dir": "/srv/external/data",
        "config_file": "/srv/external/config.json", "data_size_mb": 10,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    plan_manager = DeploymentPlanManager()
    plan = plan_manager.create(ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="session-only"),
        instance_id="external-app", strategy="existing", service_port=33010,
    ), deployment_discovery(
        instances=[existing], listening_ports=[33010],
        path_conditions=existing_path_conditions(),
    ))
    internal_plan = plan_manager.plans[plan["id"]]
    updated = store.upsert_instance({
        "id": "external-app", "target_id": "target-a", "service_port": internal_plan["service_port"],
        "install_dir": existing["working_dir"], "data_dir": existing["data_dir"],
        "image": existing["image"], "managed": False,
    })
    assert updated.service_port == 33010


def test_deployment_without_docker_or_elevation_fails_before_remote_write(tmp_path, monkeypatch):
    async def run():
        from extensions import orchestrator

        monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
        target = ExtensionTarget(
            id="t", name="VPS", host="host.example", username="deploy-user",
            host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
        )
        credential = SSHCredential(password="session-only")
        initial = deployment_discovery(path_conditions=isolated_empty_path_conditions())
        plan_manager = DeploymentPlanManager()
        plan = plan_manager.create(
            ExtensionPlanRequest(target=target, credential=credential, service_port=33010),
            initial,
        )
        drifted = copy.deepcopy(initial)
        drifted["privileges"] = {
            **privilege_snapshot(),
            "docker_access": False,
            "can_deploy": False,
            "diagnostic_code": "no_sudo_or_docker",
        }
        remote_writes = []
        async def fake_discover(_request, *, path_checks=None):
            return copy.deepcopy(drifted)
        async def forbidden_run(*_args, **_kwargs):
            remote_writes.append(True)
            raise AssertionError("deployment runner must not start")
        monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        monkeypatch.setattr(manager, "_run", forbidden_run)
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target,
            credential=credential,
            instance_id="chatgpt2api-dev",
            confirmed_plan_id=plan["id"],
        )
        with pytest.raises(ValueError):
            await manager.create(request)
        assert plan["id"] in plan_manager.plans
        assert manager.tasks == {}
        assert manager.runners == {}
        assert not (tmp_path / "extension_tasks.json").exists()
        assert remote_writes == []

    asyncio.run(run())


@pytest.mark.parametrize(
    ("field", "fresh_value"),
    [
        ("status", "Up 25 hours"),
        ("data_size_mb", 141),
        ("ports", "0.0.0.0:3000->80/tcp, :::3000->80/tcp"),
        ("clone_available", False),
        ("image", "mirror.example/chatgpt2api@sha256:" + ("a" * 64)),
        ("environment.listening_ports", [3000, 3010]),
    ],
)
def test_empty_instance_confirmation_ignores_unrelated_volatile_instance_observations(
    tmp_path, monkeypatch, field, fresh_value,
):
    from extensions import orchestrator

    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    credential = SSHCredential(password="session-only")
    unrelated = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 24 hours", "ports": "0.0.0.0:3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 140,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(
        instances=[unrelated],
        listening_ports=[3000],
        path_conditions=isolated_empty_path_conditions(),
    )
    plan_manager = DeploymentPlanManager()
    plan = plan_manager.create(
        ExtensionPlanRequest(
            target=target, credential=credential, strategy="isolated",
            clone_scope="empty", service_port=33011,
        ),
        initial,
    )
    fresh = copy.deepcopy(initial)
    if field == "environment.listening_ports":
        fresh["environment"]["listening_ports"] = fresh_value
        fresh["environment"]["tcp_listeners"] = [
            {"protocol": "tcp", "host_port": port} for port in fresh_value
        ]
    else:
        fresh["instances"][0][field] = fresh_value

    async def fake_discover(_request, *, path_checks=None):
        assert path_checks == plan_manager.plans[plan["id"]]["path_requirements"]
        return copy.deepcopy(fresh)

    async def no_remote_run(*_args, **_kwargs):
        return None

    async def run():
        monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        task_manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        monkeypatch.setattr(task_manager, "_run", no_remote_run)
        task_id = await task_manager.create(ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target, credential=credential, strategy="isolated",
            clone_scope="empty", service_port=33011, confirmed_plan_id=plan["id"],
        ))
        assert task_id in task_manager.tasks
        assert plan["id"] not in plan_manager.plans

    asyncio.run(run())


def test_empty_plan_snapshot_drift_reports_sanitized_category_and_fields():
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    source = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 24 hours", "ports": "0.0.0.0:3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 140,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(
        instances=[source], listening_ports=[3000],
        path_conditions=isolated_empty_path_conditions(),
    )
    manager = DeploymentPlanManager()
    plan = manager.create(
        ExtensionPlanRequest(
            target=target, credential=SSHCredential(password="session-only"),
            strategy="isolated", clone_scope="empty", service_port=33011,
        ),
        initial,
    )
    fresh = copy.deepcopy(initial)
    fresh["instances"][0]["source_image_id"] = "sha256:untrusted-value-must-not-escape"

    with pytest.raises(DeploymentSnapshotChangedError) as excinfo:
        manager.validate_fresh_snapshot(plan, fresh)

    diagnostic = excinfo.value.diagnostic
    assert diagnostic["code"] == "deployment_snapshot_changed"
    assert diagnostic["stage"] == "fresh_discovery"
    assert diagnostic["task_created"] is False
    assert diagnostic["snapshot_category"] == "stable_snapshot"
    assert diagnostic["changed_fields"] == ["instances.source_image_id"]
    serialized = json.dumps(diagnostic, ensure_ascii=False)
    assert "untrusted-value-must-not-escape" not in serialized
    assert "host.example" not in serialized
    assert "deploy-user" not in serialized


@pytest.mark.parametrize("fresh_binding", [
    {"host_ip": "127.0.0.1", "host_port": 3000, "container_port": 80, "protocol": "tcp"},
    {"host_ip": "0.0.0.0", "host_port": 3000, "container_port": 80, "protocol": "udp"},
    {"host_ip": "0.0.0.0", "host_port": 3000, "container_port": 81, "protocol": "tcp"},
])
def test_empty_plan_rejects_host_ip_protocol_or_container_port_binding_drift(fresh_binding):
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    source = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 24 hours", "ports": "0.0.0.0:3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "port_bindings": [{
            "host_ip": "0.0.0.0", "host_port": 3000,
            "container_port": 80, "protocol": "tcp",
        }],
        "port_bindings_complete": True,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 140,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(
        instances=[source], listening_ports=[3000],
        path_conditions=isolated_empty_path_conditions(),
    )
    manager = DeploymentPlanManager()
    plan = manager.create(ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="session-only"),
        strategy="isolated", clone_scope="empty", service_port=33011,
    ), initial)
    fresh = copy.deepcopy(initial)
    fresh["instances"][0]["port_bindings"] = [fresh_binding]

    with pytest.raises(DeploymentSnapshotChangedError) as excinfo:
        manager.validate_fresh_snapshot(plan, fresh)

    assert excinfo.value.diagnostic["snapshot_category"] == "stable_snapshot"
    assert excinfo.value.diagnostic["changed_fields"] == ["instances.port_bindings"]


def test_empty_plan_accepts_raw_port_display_reordering_when_bindings_are_unchanged():
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    source = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 24 hours",
        "ports": "0.0.0.0:3000->80/tcp, :::3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "port_bindings": [
            {"host_ip": "0.0.0.0", "host_port": 3000, "container_port": 80, "protocol": "tcp"},
            {"host_ip": "::", "host_port": 3000, "container_port": 80, "protocol": "tcp"},
        ],
        "port_bindings_complete": True,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 140,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(
        instances=[source], listening_ports=[3000],
        path_conditions=isolated_empty_path_conditions(),
    )
    manager = DeploymentPlanManager()
    plan = manager.create(ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="session-only"),
        strategy="isolated", clone_scope="empty", service_port=33011,
    ), initial)
    fresh = copy.deepcopy(initial)
    fresh["instances"][0]["ports"] = ":::3000->80/tcp, 0.0.0.0:3000->80/tcp"

    manager.validate_fresh_snapshot(plan, fresh)


def test_plan_creation_and_confirmation_fail_closed_without_canonical_bindings():
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    source = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 24 hours", "ports": "0.0.0.0:3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "port_bindings": [], "port_bindings_complete": False,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 140,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    invalid = deployment_discovery(instances=[source], listening_ports=[3000])
    manager = DeploymentPlanManager()
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="session-only"),
        strategy="isolated", clone_scope="empty", service_port=33011,
    )
    with pytest.raises(ValueError, match="deployment_port_bindings_incomplete"):
        manager.create(request, invalid)

    valid = copy.deepcopy(invalid)
    valid["instances"][0]["port_bindings"] = [{
        "host_ip": "0.0.0.0", "host_port": 3000,
        "container_port": 80, "protocol": "tcp",
    }]
    valid["instances"][0]["port_bindings_complete"] = True
    plan = manager.create(request, valid)
    with pytest.raises(DeploymentSnapshotChangedError) as excinfo:
        manager.validate_fresh_snapshot(plan, invalid)
    assert excinfo.value.diagnostic["changed_fields"] == ["instances.port_bindings"]


def test_duplicate_binding_multiplicity_drift_is_not_collapsed_to_a_set():
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    duplicated = {
        "id": "source", "container_id": "container-a", "name": "source",
        "image": "registry.example/app@sha256:" + "a" * 64,
        "source_image_id": "sha256:" + "b" * 64,
        "status": "Up", "ports": "display-only", "published_ports": [3000],
        "service_port": 3000,
        "port_bindings": [
            {"host_ip": "0.0.0.0", "host_port": 3000, "container_port": 80, "protocol": "tcp"},
            {"host_ip": "0.0.0.0", "host_port": 3000, "container_port": 80, "protocol": "tcp"},
        ],
        "port_bindings_complete": True,
        "compose_project": "source", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 1,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(instances=[duplicated], listening_ports=[3000])
    manager = DeploymentPlanManager()
    public_plan = manager.create(ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="session-only"),
        strategy="isolated", clone_scope="empty", service_port=33011,
    ), initial)
    fresh = copy.deepcopy(initial)
    fresh["instances"][0]["port_bindings"].pop()

    with pytest.raises(DeploymentSnapshotChangedError) as excinfo:
        manager.validate_fresh_snapshot(manager.plans[public_plan["id"]], fresh)

    assert excinfo.value.diagnostic["changed_fields"] == ["instances.port_bindings"]
    assert public_plan["id"] in manager.plans


@pytest.mark.parametrize("case", [
    "missing_version", "null_version", "unknown_version", "missing_key",
    "unknown_key", "null_value", "false_value", "strategy_mismatch",
])
def test_closed_path_condition_schema_rejects_every_non_exact_variant(case):
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    discovery = deployment_discovery()
    if case == "missing_version":
        discovery.pop("path_conditions_version")
    elif case == "null_version":
        discovery["path_conditions_version"] = None
    elif case == "unknown_version":
        discovery["path_conditions_version"] = "phase4-v4"
    elif case == "missing_key":
        discovery["path_conditions"].pop("target_install_parent_claimable")
    elif case == "unknown_key":
        discovery["path_conditions"]["unexpected"] = True
    elif case == "null_value":
        discovery["path_conditions"]["target_install_dir_absent"] = None
    elif case == "false_value":
        discovery["path_conditions"]["target_install_parent_claimable"] = False
    else:
        discovery["path_conditions"] = {
            "existing_instance_present": True,
            "existing_instance_identity_matches": True,
        }

    manager = DeploymentPlanManager()
    with pytest.raises(ValueError) as excinfo:
        manager.create(ExtensionPlanRequest(
            target=target, credential=SSHCredential(password="session-only"),
            strategy="isolated", clone_scope="empty", service_port=33011,
        ), discovery)

    assert str(excinfo.value) == "deployment_path_conditions_invalid"
    assert excinfo.value.diagnostic["code"] == "deployment_path_conditions_invalid"
    assert manager.plans == {}


@pytest.mark.parametrize("case", [
    "missing_version", "missing_key", "unknown_key", "null_value",
    "false_value", "strategy_mismatch",
])
def test_plan_route_rejects_non_closed_path_evidence_before_plan_creation(monkeypatch, case):
    import main

    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    initial = deployment_discovery()
    invalid = copy.deepcopy(initial)
    if case == "missing_version":
        invalid.pop("path_conditions_version")
    elif case == "missing_key":
        invalid["path_conditions"].pop("target_install_parent_claimable")
    elif case == "unknown_key":
        invalid["path_conditions"]["unexpected"] = True
    elif case == "null_value":
        invalid["path_conditions"]["target_install_dir_absent"] = None
    elif case == "false_value":
        invalid["path_conditions"]["target_install_parent_claimable"] = False
    else:
        invalid["path_conditions"] = existing_path_conditions()
    calls = []

    async def fake_discover(_request, *, path_checks=None):
        calls.append(copy.deepcopy(path_checks))
        return copy.deepcopy(initial if len(calls) == 1 else invalid)

    manager = DeploymentPlanManager()
    monkeypatch.setattr(main, "deployment_plans", manager)
    monkeypatch.setattr(main, "discover_environment", fake_discover)
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
    body = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="session-only"),
        strategy="isolated", clone_scope="empty", service_port=33011,
        image=TEST_DEPLOYMENT_IMAGE, approve_plan_discovery=True,
    )

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(main.extension_deploy_plan(body))

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail["diagnostic"]["code"] == "deployment_path_conditions_invalid"
    assert calls[0] is None
    assert set(calls[1]) == set(isolated_empty_path_conditions())
    assert manager.plans == {}


@pytest.mark.parametrize("payload_case", ["missing", "null", "invalid"])
def test_listener_success_requires_a_complete_structured_payload(payload_case):
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    discovery = deployment_discovery()
    if payload_case == "missing":
        discovery["environment"].pop("tcp_listeners")
    elif payload_case == "null":
        discovery["environment"]["tcp_listeners"] = None
    else:
        discovery["environment"]["tcp_listeners"] = [{"protocol": "udp", "host_port": 33011}]

    manager = DeploymentPlanManager()
    with pytest.raises(ValueError, match="^deployment_listener_probe_incomplete$"):
        manager.create(ExtensionPlanRequest(
            target=target, credential=SSHCredential(password="session-only"),
            strategy="isolated", clone_scope="empty", service_port=33011,
        ), discovery)

    assert manager.plans == {}


def test_public_plan_exposes_only_an_opaque_evidence_manifest_for_the_snapshot():
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    manager = DeploymentPlanManager()
    plan = manager.create(ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="session-only"),
        strategy="isolated", clone_scope="empty", service_port=33011,
    ), deployment_discovery())

    assert "execution_snapshot" not in plan
    assert "discovery_snapshot" not in plan
    assert "path_requirements" not in plan
    assert plan["evidence_manifest"]["contract_version"] == "phase4-v3"
    assert plan["evidence_manifest"]["complete"] is True
    assert re.fullmatch(r"[a-f0-9]{64}", plan["evidence_manifest"]["snapshot_digest"])


def test_extension_plan_discovery_and_instance_routes_expose_only_public_product_projections(
    tmp_path, monkeypatch,
):
    import main

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    algorithm = TEST_HOST_KEY_ALGORITHM
    fingerprint = "SHA256:PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP"
    image = "registry.invalid/sentinel-image@sha256:" + "a" * 64
    target = store.upsert_target({
        "id": "public-target", "name": "VPS", "host": "sentinel-host.example",
        "port": 2222, "username": "sentinel-user",
        "host_key_algorithm": algorithm, "host_key": fingerprint,
        "chatgpt2api_port": 34567,
    })
    discovered_instance = {
        "id": "sentinel-source", "name": "sentinel-container", "container_id": "sentinel-container-id",
        "image": image, "status": "running", "published_ports": [34567], "service_port": 34567,
        "port_bindings": [{
            "host_ip": "127.0.0.1", "host_port": 34567,
            "container_port": 80, "protocol": "tcp",
        }],
        "port_bindings_complete": True,
        "compose_project": "sentinel-compose", "working_dir": "/srv/sentinel/work",
        "data_dir": "/srv/sentinel/data", "config_file": "/srv/sentinel/config.json",
        "data_size_mb": 128, "managed": False, "ownership": "external",
        "clone_available": True,
    }
    discovery = deployment_discovery(instances=[discovered_instance])
    discovery["host_key_algorithm"] = algorithm
    discovery["host_key"] = fingerprint
    discovery["environment"]["home_dir"] = "/home/sentinel-user"
    plan_manager = DeploymentPlanManager()
    monkeypatch.setattr(main, "deployment_plans", plan_manager)

    async def fake_discovery(_body, *, path_checks=None, approved_plan=None):
        return copy.deepcopy(discovery)

    async def fake_probe(_target):
        return algorithm, fingerprint

    monkeypatch.setattr(main, "discover_environment", fake_discovery)
    monkeypatch.setattr(main, "probe_host_key", fake_probe)
    credential = SSHCredential(password="sentinel-session-secret")
    discovery_response = asyncio.run(main.extension_discover(ExtensionDiscoveryRequest(
        target=target, credential=credential,
    )))
    plan_response = asyncio.run(main.extension_deploy_plan(ExtensionPlanRequest(
        target=target, credential=credential, instance_id="public-new-app",
        strategy="isolated", clone_scope="empty", service_port=33011, image=image,
        approve_plan_discovery=True,
    )))

    store.upsert_instance({
        "id": "sentinel-managed", "target_id": target.id, "project": "chatgpt2api",
        "strategy": "isolated", "deployment_mode": "compose", "compose_project": "sentinel-compose",
        "service_port": 34567, "install_dir": "/srv/sentinel/work", "data_dir": "/srv/sentinel/data",
        "image": image, "status": "running", "console_url": "https://sentinel.example/console",
        "api_url": "https://sentinel.example/api", "managed": True, "ownership": "managed",
        "container_id": "sentinel-container-id", "container_name": "sentinel-container",
    })
    instance_response = asyncio.run(main.extension_instances())

    assert set(discovery_response) == {
        "ready", "evidence_manifest", "capabilities", "instances", "deployment_modes",
    }
    assert set(discovery_response["capabilities"]) == {
        "can_deploy", "can_admin", "docker_available", "compose_available",
    }
    assert set(discovery_response["instances"][0]) == {
        "handle", "managed", "running", "clone_available",
    }
    assert set(plan_response) == {"plan", "discovery"}
    assert set(plan_response["plan"]) == {
        "id", "evidence_manifest", "ready", "registers_locally",
        "remote_write_expected", "clone_requested", "admin_required",
    }
    assert plan_response["discovery"] == discovery_response
    assert set(instance_response["instances"][0]) == {
        "handle", "project", "managed", "strategy", "deployment_mode", "running", "console_url", "api_url",
        "target_name", "vps_host", "vps_port", "service_port", "created_at", "updated_at",
    }
    assert instance_response["instances"][0]["console_url"] == "https://sentinel.example/console"
    assert instance_response["instances"][0]["api_url"] == "https://sentinel.example/api"
    assert instance_response["instances"][0]["target_name"] == "VPS"
    assert instance_response["instances"][0]["vps_host"] == "sentinel-host.example"
    assert instance_response["instances"][0]["vps_port"] == 2222
    assert instance_response["instances"][0]["service_port"] == 34567

    serialized = json.dumps({
        "discovery": discovery_response,
        "plan": plan_response,
        "instances": instance_response,
    }, ensure_ascii=False)
    for sentinel in (
        fingerprint, "sentinel-user", "/srv/sentinel",
        "sentinel-image", "127.0.0.1",
        "sentinel-compose", "sentinel-container", "sentinel-session-secret",
    ):
        assert sentinel not in serialized


def test_public_instance_access_dto_rejects_credential_or_query_bearing_urls(monkeypatch):
    monkeypatch.setattr(orchestrator.extensions_store, "get_target", lambda _target_id: None)
    instance = SimpleNamespace(
        id="managed-app", target_id="target-a", project="chatgpt2api",
        managed=True, status="running",
        console_url="https://user:password@service.example/console",
        api_url="https://service.example/v1?token=secret",
        install_dir="/srv/private", data_dir="/srv/private/data",
        image="registry.invalid/private", container_id="raw-container",
    )

    public = public_instance_access(instance)
    assert set(public) == {
        "handle", "project", "managed", "strategy", "deployment_mode", "running", "console_url", "api_url",
        "target_name", "vps_host", "vps_port", "service_port", "created_at", "updated_at",
    }
    assert public["console_url"] == ""
    assert public["api_url"] == ""
    serialized = json.dumps(public)
    assert all(value not in serialized for value in (
        "password", "token", "/srv/private", "registry.invalid", "raw-container", "target-a",
    ))


def test_public_instance_access_dto_allowlists_bounded_project_identifier(monkeypatch):
    monkeypatch.setattr(orchestrator.extensions_store, "get_target", lambda _target_id: None)
    base = {
        "id": "managed-app", "target_id": "target-a", "managed": True,
        "status": "running", "console_url": "", "api_url": "",
    }

    assert public_instance_access(SimpleNamespace(**base, project="provider-2"))["project"] == "provider-2"
    for unsafe in ("Provider", "<img src=x>", "-provider", "p" * 65):
        assert public_instance_access(SimpleNamespace(**base, project=unsafe))["project"] == "chatgpt2api"


def test_opaque_instance_handles_round_trip_into_existing_plan_confirmation():
    import main

    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
    )
    credential = SSHCredential(password="session-only")
    existing = {
        "id": "existing-app", "container_id": "container-a", "name": "existing-app",
        "image": "example.invalid/app@sha256:" + "b" * 64,
        "status": "Up 1 hour", "published_ports": [33010], "service_port": 33010,
        "compose_project": "existing-project", "working_dir": "/srv/existing",
        "data_dir": "/srv/existing/data", "config_file": "/srv/existing/config.json",
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    discovery = deployment_discovery(
        instances=[existing], listening_ports=[33010], path_conditions=existing_path_conditions(),
    )
    handle = public_instance_handle(target.id, existing["id"])
    public = DeploymentPlanManager.public_discovery(discovery, target.id)
    assert public["instances"][0]["handle"] == handle

    submitted = ExtensionPlanRequest(
        target=target, credential=credential, instance_id=handle,
        strategy="existing", service_port=1, image="example.invalid/placeholder:tag",
    )
    resolved = main._resolve_plan_discovery_references(submitted, discovery)
    assert resolved.instance_id == existing["id"]
    assert resolved.service_port == existing["service_port"]
    assert resolved.image == existing["image"]

    manager = DeploymentPlanManager()
    plan = manager.create(resolved, discovery)
    confirmation = manager.resolve_public_references(ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=target,
        credential=credential,
        instance_id=handle,
        strategy="existing",
        service_port=1,
        image="example.invalid/placeholder:tag",
        confirmed_plan_id=plan["id"],
    ))
    assert confirmation.instance_id == existing["id"]
    assert confirmation.service_port == existing["service_port"]
    assert confirmation.image == existing["image"]


def test_discovered_raw_i_prefixed_ids_remain_compatible_for_existing_and_clone_paths():
    import main

    target = ExtensionTarget(
        id="target-raw-i", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
    )
    credential = SSHCredential(password="session-only")
    image = "example.invalid/app@sha256:" + "d" * 64
    discovery = deployment_discovery(instances=[
        {"id": "i-existing-raw", "image": image, "service_port": 33010},
        {"id": "i-clone-source", "image": image, "service_port": 33011},
    ])

    existing = main._resolve_plan_discovery_references(ExtensionPlanRequest(
        target=target, credential=credential, strategy="existing",
        instance_id="i-existing-raw", service_port=33010, image=image,
    ), discovery)
    assert existing.instance_id == "i-existing-raw"
    assert existing.service_port == 33010

    clone = main._resolve_plan_discovery_references(ExtensionPlanRequest(
        target=target, credential=credential, strategy="isolated",
        instance_id="clone-target", service_port=33012, image=image,
        clone_source_id="i-clone-source", clone_scope="working-copy",
    ), discovery)
    assert clone.clone_source_id == "i-clone-source"
    assert clone.image == image

    ambiguous = copy.deepcopy(discovery)
    ambiguous["instances"].append(copy.deepcopy(ambiguous["instances"][0]))
    with pytest.raises(ValueError, match="deployment_instance_handle_invalid"):
        main._resolve_plan_discovery_references(ExtensionPlanRequest(
            target=target, credential=credential, strategy="existing",
            instance_id="i-existing-raw", service_port=33010, image=image,
        ), ambiguous)


def test_discovered_raw_and_opaque_handle_collision_fails_closed_for_existing_and_clone(monkeypatch):
    import main

    collision = "i-collision"
    target = ExtensionTarget(
        id="target-collision", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
    )
    credential = SSHCredential(password="session-only")
    discovery = deployment_discovery(instances=[
        {"id": collision, "image": "raw-image", "service_port": 33010},
        {"id": "opaque-instance", "image": "opaque-image", "service_port": 33011},
    ])
    monkeypatch.setattr(
        main, "public_instance_handle",
        lambda _target_id, instance_id: collision if instance_id == "opaque-instance" else "i-other",
    )

    with pytest.raises(ValueError, match="deployment_instance_handle_invalid"):
        main._resolve_plan_discovery_references(ExtensionPlanRequest(
            target=target, credential=credential, strategy="existing",
            instance_id=collision, service_port=33010,
        ), discovery)
    with pytest.raises(ValueError, match="deployment_instance_handle_invalid"):
        main._resolve_plan_discovery_references(ExtensionPlanRequest(
            target=target, credential=credential, strategy="isolated",
            instance_id="new-instance", service_port=33012,
            clone_source_id=collision, clone_scope="working-copy",
        ), discovery)

    monkeypatch.setattr(main, "public_instance_handle", lambda _target_id, _instance_id: collision)
    same = main._resolve_plan_discovery_references(ExtensionPlanRequest(
        target=target, credential=credential, strategy="existing",
        instance_id=collision, service_port=33010,
    ), deployment_discovery(instances=[discovery["instances"][0]]))
    assert same.instance_id == collision


def test_stored_raw_and_opaque_handle_collision_blocks_vault_and_reset(monkeypatch):
    import main

    collision = "i-collision"
    raw = SimpleNamespace(id=collision, target_id="target-a", managed=True)
    opaque = SimpleNamespace(id="opaque-instance", target_id="target-a", managed=True)
    monkeypatch.setattr(main.extensions_store, "list_instances", lambda target_id="": [raw, opaque])
    monkeypatch.setattr(
        main, "public_instance_handle",
        lambda _target_id, instance_id: collision if instance_id == "opaque-instance" else "i-other",
    )

    assert main._resolve_stored_instance_handle(collision) is None
    assert main._resolve_stored_instance_handle(collision, "target-a") is None
    with pytest.raises(HTTPException) as vault_error:
        main._managed_vault_instance(collision)
    assert vault_error.value.status_code == 404

    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY,
    )
    request = ExtensionKeyResetRequest(
        target=target, credential=SSHCredential(password="session-only"),
        trust_host_key=True, expected_host_key=TEST_HOST_KEY, instance_id=collision,
    )
    monkeypatch.setattr(main, "_bind_confirmed_extension_target", lambda body: body)
    monkeypatch.setattr(
        main, "reset_managed_admin_key",
        lambda _body: (_ for _ in ()).throw(AssertionError("collision reached remote reset")),
    )
    with pytest.raises(HTTPException) as reset_error:
        asyncio.run(main.extension_reset_admin_key(request))
    assert reset_error.value.status_code == 400

    monkeypatch.setattr(main.extensions_store, "list_instances", lambda target_id="": [raw])
    monkeypatch.setattr(main, "public_instance_handle", lambda _target_id, _instance_id: collision)
    assert main._resolve_stored_instance_handle(collision) is raw


@pytest.mark.parametrize("probe", [
    {"status": 1, "complete": False},
    {"status": 0, "complete": False},
    {"status": False, "complete": True},
])
def test_plan_creation_rejects_untrustworthy_listener_probe_with_sanitized_diagnostic(probe):
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    manager = DeploymentPlanManager()
    discovery = deployment_discovery(
        listening_ports=[], listening_ports_probe=probe,
        path_conditions=isolated_empty_path_conditions(),
    )

    with pytest.raises(ValueError) as excinfo:
        manager.create(ExtensionPlanRequest(
            target=target, credential=SSHCredential(password="session-only"),
            strategy="isolated", clone_scope="empty", service_port=33011,
        ), discovery)

    assert str(excinfo.value) == "deployment_listener_probe_incomplete"
    assert excinfo.value.diagnostic == {
        "code": "deployment_listener_probe_incomplete",
        "stage": "plan_confirmation",
        "retry_safe": False,
        "task_created": False,
    }
    assert manager.plans == {}


@pytest.mark.parametrize("probe_case", ["occupied", "incomplete", "failed", "garbled"])
def test_deploy_route_rejects_occupied_or_untrustworthy_listener_probe_without_side_effects(
    tmp_path, monkeypatch, probe_case,
):
    import main
    from extensions import orchestrator

    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    credential = SSHCredential(password="session-only")
    initial = deployment_discovery(
        listening_ports=[3000], path_conditions=isolated_empty_path_conditions(),
    )
    plan_manager = DeploymentPlanManager()
    plan = plan_manager.create(ExtensionPlanRequest(
        target=target, credential=credential, strategy="isolated",
        clone_scope="empty", service_port=33011,
    ), initial)
    fresh = copy.deepcopy(initial)
    if probe_case == "occupied":
        fresh["environment"]["listening_ports"].append(33011)
        fresh["environment"]["tcp_listeners"].append({"protocol": "tcp", "host_port": 33011})
        fresh["path_conditions"]["target_port_unoccupied"] = False
    else:
        fresh["environment"]["listening_ports"] = []
        fresh["environment"]["tcp_listeners"] = []
        fresh["environment"]["listening_ports_probe"] = {
            "status": 1 if probe_case == "failed" else 0,
            "complete": False,
            "payload_present": False,
        }
    remote_writes = []

    async def fake_discover(_request, *, path_checks=None):
        return copy.deepcopy(fresh)

    async def forbidden_run(*_args, **_kwargs):
        remote_writes.append(True)

    async def run():
        monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        task_manager = ExtensionTaskManager(store_path=tmp_path / f"{probe_case}.json")
        monkeypatch.setattr(task_manager, "_run", forbidden_run)
        monkeypatch.setattr(main, "extension_tasks", task_manager)
        monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: target)
        body = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target, credential=credential, strategy="isolated",
            clone_scope="empty", service_port=33011, confirmed_plan_id=plan["id"],
        )
        with pytest.raises(HTTPException) as excinfo:
            await main.extension_start_deploy(body)

        assert excinfo.value.status_code == 400
        diagnostic = excinfo.value.detail["diagnostic"]
        assert diagnostic["code"] == "deployment_snapshot_changed"
        assert diagnostic["task_created"] is False
        assert diagnostic["snapshot_category"] == (
            "requested_port" if probe_case == "occupied" else "listener_evidence"
        )
        assert diagnostic["changed_fields"] == [
            "environment.listening_ports" if probe_case == "occupied"
            else "environment.listening_ports_probe"
        ]
        assert plan["id"] in plan_manager.plans
        assert "_lease_token" not in plan_manager.plans[plan["id"]]
        assert task_manager.tasks == {}
        assert task_manager.runners == {}
        assert task_manager.resource_reservations.active_count == 0
        assert remote_writes == []
        assert not (tmp_path / f"{probe_case}.json").exists()

    asyncio.run(run())


@pytest.mark.parametrize(
    ("drift", "category", "changed_field"),
    [
        ("requested_port", "requested_port", "environment.listening_ports"),
        ("target_instance", "target_instance", "instances.id"),
        ("docker_version", "stable_snapshot", "environment.docker_version"),
        ("home_dir", "stable_snapshot", "environment.home_dir"),
        ("container_id", "stable_snapshot", "instances.container_id"),
        ("source_image_id", "stable_snapshot", "instances.source_image_id"),
        ("published_ports", "stable_snapshot", "instances.published_ports"),
        ("compose_project", "stable_snapshot", "instances.compose_project"),
        ("data_dir", "stable_snapshot", "instances.data_dir"),
        ("managed", "stable_snapshot", "instances.managed"),
        ("ownership", "stable_snapshot", "instances.ownership"),
        ("capability", "stable_snapshot", "privileges.can_deploy"),
    ],
)
def test_empty_plan_snapshot_keeps_security_bindings_fail_closed(drift, category, changed_field):
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    source = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 24 hours", "ports": "0.0.0.0:3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 140,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(instances=[source], listening_ports=[3000])
    manager = DeploymentPlanManager()
    plan = manager.create(
        ExtensionPlanRequest(
            target=target, credential=SSHCredential(password="session-only"),
            instance_id="chatgpt2api-dev", strategy="isolated",
            clone_scope="empty", service_port=33011,
        ),
        initial,
    )
    fresh = copy.deepcopy(initial)
    if drift == "requested_port":
        fresh["environment"]["listening_ports"].append(33011)
        fresh["environment"]["tcp_listeners"].append({"protocol": "tcp", "host_port": 33011})
        fresh["path_conditions"]["target_port_unoccupied"] = False
    elif drift == "target_instance":
        fresh["instances"].append({
            **fresh["instances"][0], "id": "chatgpt2api-dev", "container_id": "target-container",
        })
    elif drift in {"docker_version", "home_dir"}:
        fresh["environment"][drift] = {
            "docker_version": "28.0",
            "home_dir": "/home/changed-user",
        }[drift]
    elif drift == "capability":
        fresh["privileges"]["can_deploy"] = False
    else:
        fresh["instances"][0][drift] = {
            "container_id": "changed-container",
            "source_image_id": "sha256:changed-image",
            "published_ports": [3001],
            "compose_project": "changed-project",
            "data_dir": "/srv/changed/data",
            "managed": True,
            "ownership": "managed",
        }[drift]

    with pytest.raises(DeploymentSnapshotChangedError) as excinfo:
        manager.validate_fresh_snapshot(plan, fresh)

    assert excinfo.value.diagnostic["snapshot_category"] == category
    assert changed_field in excinfo.value.diagnostic["changed_fields"]


@pytest.mark.parametrize("plan_kind", ["existing", "source_clone"])
@pytest.mark.parametrize(
    ("field", "fresh_value"),
    [
        ("status", "Up 25 hours"),
        ("ports", "0.0.0.0:3000->80/tcp, :::3000->80/tcp"),
        ("data_size_mb", 141),
        ("clone_available", False),
        ("image", "mirror.example/chatgpt2api@sha256:" + ("a" * 64)),
    ],
)
def test_existing_and_source_clone_snapshot_contracts_remain_exact(plan_kind, field, fresh_value):
    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33011,
    )
    credential = SSHCredential(password="session-only", elevation="passwordless_sudo")
    source = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 24 hours", "ports": "0.0.0.0:3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 140,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(
        instances=[source],
        privileges=privilege_snapshot(elevation="passwordless_sudo", can_admin=True),
        listening_ports=[3000],
        path_conditions=source_clone_path_conditions(),
    )
    manager = DeploymentPlanManager()
    if plan_kind == "existing":
        request = ExtensionPlanRequest(
            target=target, credential=credential, instance_id="source-app",
            strategy="existing", service_port=3000,
        )
        initial["path_conditions"] = existing_path_conditions()
    else:
        request = ExtensionPlanRequest(
            target=target, credential=credential, instance_id="chatgpt2api-dev",
            strategy="isolated", service_port=33011, image=source["image"],
            clone_source_id="source-app", clone_scope="working-copy",
        )
    plan = manager.create(request, initial)
    fresh = copy.deepcopy(initial)
    if field == "environment.listening_ports":
        fresh["environment"]["listening_ports"] = fresh_value
        fresh["environment"]["tcp_listeners"] = [
            {"protocol": "tcp", "host_port": port} for port in fresh_value
        ]
    else:
        fresh["instances"][0][field] = fresh_value

    with pytest.raises(DeploymentSnapshotChangedError):
        manager.validate_fresh_snapshot(plan, fresh)


@pytest.mark.parametrize("drift", [
    "ports", "instances", "compose", "source_container", "image", "mount",
    "source_size", "disk", "path", "capability",
])
def test_fresh_remote_snapshot_drift_preserves_plan_and_creates_no_task(tmp_path, monkeypatch, drift):
    from extensions import orchestrator

    target = ExtensionTarget(
        id="target-a", name="VPS", host="host.example", username="deploy-user",
        host_key=TEST_HOST_KEY, chatgpt2api_port=33010,
    )
    credential = SSHCredential(password="session-only", elevation="passwordless_sudo")
    source = {
        "id": "source-app", "container_id": "source-container", "name": "source-app",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "source_image_id": "sha256:source-image",
        "status": "Up 1 hour", "ports": "0.0.0.0:3000->80/tcp",
        "published_ports": [3000], "service_port": 3000,
        "compose_project": "source-project", "compose_service": "app",
        "working_dir": "/srv/source", "data_dir": "/srv/source/data",
        "config_file": "/srv/source/config.json", "data_size_mb": 100,
        "clone_available": True, "managed": False, "ownership": "compose",
    }
    initial = deployment_discovery(
        instances=[source],
        privileges=privilege_snapshot(elevation="passwordless_sudo", can_admin=True),
        listening_ports=[3000],
        path_conditions=source_clone_path_conditions(),
    )
    plan_manager = DeploymentPlanManager()
    plan = plan_manager.create(ExtensionPlanRequest(
        target=target, credential=credential, service_port=33010,
        clone_source_id="source-app", clone_scope="working-copy",
    ), initial)
    fresh = copy.deepcopy(initial)
    if drift == "ports":
        fresh["environment"]["listening_ports"].append(33010)
        fresh["environment"]["tcp_listeners"].append({"protocol": "tcp", "host_port": 33010})
        fresh["path_conditions"]["target_port_unoccupied"] = False
    elif drift == "instances":
        fresh["instances"].append({**source, "id": "new-app", "container_id": "new-container"})
    elif drift == "compose":
        fresh["instances"][0]["compose_project"] = "changed-project"
    elif drift == "source_container":
        fresh["instances"][0]["container_id"] = "changed-container"
    elif drift == "image":
        fresh["instances"][0]["source_image_id"] = "sha256:changed-image"
    elif drift == "mount":
        fresh["instances"][0]["data_dir"] = "/srv/changed/data"
    elif drift == "source_size":
        fresh["instances"][0]["data_size_mb"] = 101
    elif drift == "disk":
        fresh["environment"]["disk_free_mb"] = 100
    elif drift == "path":
        fresh["path_conditions"]["target_install_dir_absent"] = False
    elif drift == "capability":
        fresh["privileges"]["can_deploy"] = False
        fresh["privileges"]["diagnostic_code"] = "docker_unavailable"

    async def fake_discover(_request, *, path_checks=None):
        return copy.deepcopy(fresh)

    runner_started = []
    async def forbidden_run(*_args, **_kwargs):
        runner_started.append(True)

    async def run():
        monkeypatch.setattr(orchestrator, "deployment_plans", plan_manager)
        monkeypatch.setattr("extensions.discovery.discover_environment", fake_discover)
        task_manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        monkeypatch.setattr(task_manager, "_run", forbidden_run)
        request = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target, credential=credential, confirmed_plan_id=plan["id"],
            clone_source_id="source-app", clone_scope="working-copy",
        )
        with pytest.raises(ValueError):
            await task_manager.create(request)
        assert plan["id"] in plan_manager.plans
        assert "_lease_token" not in plan_manager.plans[plan["id"]]
        assert task_manager.tasks == {}
        assert task_manager.runners == {}
        assert task_manager.deliveries == {}
        assert runner_started == []
        assert not (tmp_path / "extension_tasks.json").exists()

    asyncio.run(run())


def test_target_username_is_required_normalized_and_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    with pytest.raises(ValueError):
        store.save_target_metadata({"name": "VPS", "host": "host.example", "username": "   "})

    saved = store.save_target_metadata({
        "name": "VPS",
        "host": "host.example",
        "username": "  deploy-operator  ",
    })

    assert saved.username == "deploy-operator"
    assert store.get_target(saved.id).username == "deploy-operator"


def test_target_role_is_saved_and_legacy_targets_are_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    legacy = store.save_target_metadata({
        "name": "Legacy", "host": "legacy.example", "username": "operator",
    })
    assert legacy.target_role == "production-read-only"
    isolated = store.save_target_metadata({
        "name": "Dev", "host": "dev.example", "username": "operator",
        "target_role": "isolated-development",
    })
    assert isolated.target_role == "isolated-development"
    with pytest.raises(ValueError):
        store.save_target_metadata({
            "id": isolated.id, "name": "Dev", "host": "dev.example", "username": "operator",
            "target_role": "not-a-role",
        })


def test_legacy_blank_username_quarantines_only_that_target_and_preserves_instances(tmp_path, monkeypatch):
    path = tmp_path / "extensions.json"
    monkeypatch.setattr(store, "EXTENSIONS_FILE", path)
    valid_instance = {
        "id": "legacy-app", "target_id": "legacy-target", "service_port": 33010,
        "install_dir": "/srv/legacy-app", "data_dir": "/srv/legacy-app/data",
        "image": "example.invalid/app:stable", "status": "running",
    }
    path.write_text(json.dumps({
        "targets": [
            {"id": "valid-target", "name": "Valid", "host": "valid.example", "username": "operator"},
            {"id": "legacy-target", "name": "Legacy", "host": "legacy.example", "username": "   "},
        ],
        "instances": [valid_instance],
        "batch_target_ids": ["valid-target", "legacy-target"],
    }), encoding="utf-8")

    loaded = store.load_config()
    assert [target.id for target in loaded.targets] == ["valid-target"]
    assert [instance.id for instance in loaded.instances] == ["legacy-app"]
    assert loaded.instances[0].target_id == "legacy-target"

    store.save_config(loaded)
    round_trip = store.load_config()
    assert [target.username for target in round_trip.targets] == ["operator"]
    assert [instance.id for instance in round_trip.instances] == ["legacy-app"]
    serialized = path.read_text(encoding="utf-8")
    assert '"username": "   "' not in serialized


def test_isolated_working_copy_plan_requires_space_and_scrubs_push_state():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="deploy-user", host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY)
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret", elevation="passwordless_sudo"), service_port=33010,
        clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    discovery = deployment_discovery(
        listening_ports=[3000],
        privileges=privilege_snapshot(elevation="passwordless_sudo", can_admin=True),
        instances=[{
            "id": "chatgpt2api-warp", "image": "ghcr.io/yukkcat/chatgpt2api:latest",
            "data_dir": "/opt/chatgpt2api/data", "config_file": "/opt/chatgpt2api/config.json",
            "data_size_mb": 1200, "clone_available": True,
            "port_bindings": [], "port_bindings_complete": True,
        }],
        path_conditions=source_clone_path_conditions(),
    )
    plan = manager.create(request, discovery)
    internal_plan = manager.plans[plan["id"]]
    assert internal_plan["clone_scope"] == "working-copy"
    assert internal_plan["clone_size_mb"] == 1200
    assert internal_plan["source_baseline"]["container_id"] == ""
    assert internal_plan["source_baseline"]["data_dir"] == "/opt/chatgpt2api/data"
    assert internal_plan["source_baseline"]["config_file"] == "/opt/chatgpt2api/config.json"
    assert any("凭据" in operation for operation in internal_plan["operations"])
    assert any("Push 身份" in operation for operation in internal_plan["operations"])
    assert "secret" not in json.dumps(plan)


def test_working_copy_plan_rejects_image_drift():
    manager = DeploymentPlanManager()
    request = ExtensionPlanRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="deploy-user", host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY),
        credential=SSHCredential(password="secret", elevation="passwordless_sudo"), service_port=33010,
        image="ghcr.io/yukkcat/chatgpt2api:latest",
        clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    discovery = {
        "environment": environment_snapshot(),
        "privileges": privilege_snapshot(elevation="passwordless_sudo", can_admin=True),
        "instances": [{
            "id": "chatgpt2api-warp", "image": "ghcr.io/yukkcat/chatgpt2api@sha256:abc",
            "data_dir": "/data", "config_file": "/config.json", "data_size_mb": 100,
            "clone_available": True, "port_bindings": [], "port_bindings_complete": True,
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
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="deploy-user", host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY),
        credential=SSHCredential(password="secret", elevation="passwordless_sudo"), service_port=33010,
        image=baseline_image, clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    plan = manager.create(request, deployment_discovery(
        privileges=privilege_snapshot(elevation="passwordless_sudo", can_admin=True),
        instances=[{
            "id": "chatgpt2api-warp", "image": baseline_image,
            "source_image_id": "sha256:production-image", "data_dir": "/data",
            "config_file": "/config.json", "data_size_mb": 100, "clone_available": True,
            "port_bindings": [], "port_bindings_complete": True,
        }],
        path_conditions=source_clone_path_conditions(),
    ))
    internal_plan = manager.plans[plan["id"]]

    assert internal_plan["image"] == baseline_image
    assert internal_plan["clone_source_image_id"] == "sha256:production-image"
    assert any("不拉取 latest" in operation for operation in internal_plan["operations"])


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
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="deploy-user", host_key_algorithm=TEST_HOST_KEY_ALGORITHM, host_key=TEST_HOST_KEY),
        credential=SSHCredential(password="secret", elevation="passwordless_sudo"), service_port=33010,
        clone_source_id="chatgpt2api-warp", clone_scope="media",
    )
    try:
        manager.create(request, {
            "environment": environment_snapshot(disk_free_mb=100),
                "privileges": privilege_snapshot(elevation="passwordless_sudo", can_admin=True),
                "instances": [{
                    "id": "chatgpt2api-warp", "data_dir": "/data", "config_file": "/config.json",
                    "image": "ghcr.io/yukkcat/chatgpt2api:latest",
                    "data_size_mb": 1000, "clone_available": True,
                    "port_bindings": [], "port_bindings_complete": True,
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


def test_push_source_setup_is_instance_bound_and_does_not_persist_or_put_keys_in_urls():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")

    assert 'id="extPushSource"' in html
    assert 'id="extPushDestinationUrl" readonly' in html
    assert 'id="extPushSourceId" readonly' in html
    assert 'id="extPushKey" type="password" readonly autocomplete="off"' in html
    assert "extensionCreatePushSource" in html
    assert "extensionRotatePushSource" in html
    assert "extensionRevokePushSource" in html
    block = js.split("function pushSourceHandle", 1)[1].split("window.extensionTogglePassword", 1)[0]
    assert "/api/extensions/push-sources/" in block
    assert "JSON.stringify({instance_handle:handle})" in block
    assert "encodeURIComponent(handle)" in block
    assert "key.value=''" in block
    assert "localStorage" not in block
    assert "sessionStorage" not in block
    assert "window.open" not in block
    assert "push_key" not in block.split("JSON.stringify({instance_handle:handle})", 1)[1].split("}))", 1)[0]


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
    assert 'id="extVaultPassword"' in html
    assert 'onkeydown="extensionVaultPasswordKeydown(event)"' in html
    assert "window.extensionVaultPasswordKeydown" in js
    assert "event.key!=='Enter'||event.isComposing" in js
    assert "window.extensionVaultUnlock()" in js
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
    card_block = js.split("extRenderServiceGroups=function", 1)[1].split("renderDiscovery=function", 1)[0]
    assert "item.handle" in card_block
    assert "item.project" in card_block
    assert "item.managed" in card_block
    assert "item.running" in card_block
    assert "data-instance-handle" in card_block
    assert "item.console_url" in card_block
    assert "item.api_url" in card_block
    assert "common.open_console" in card_block
    assert "extensionCopyServiceUrl" in card_block
    assert "extAttachServiceMetadata" in js
    assert "extServicesLoadInFlight" in js
    assert "item.vps_host" in js
    assert "item.service_port" in js
    assert "credential_saved_at" in js
    assert "extensions.view_details" in js
    assert "admin_key" not in card_block
    assert "extWireManagedServiceActions" in js
    assert "data-instance-handle" in js.split("function extWireManagedServiceActions", 1)[1]
    assert "removeAttribute('onclick')" in js
    assert "stopImmediatePropagation" in js
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
    assert 'extensions.guide_connect_title' in i18n_js
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
    assert "delivery=restoring?{available:false,error:false}:await claimTaskDelivery(taskId,attemptId)" in extensions_js
    assert 'id="extTargetRole"' in html
    assert 'value="isolated-development"' in html
    assert 'value="production-read-only"' in html
    assert "target_role:el('extTargetRole').value" in extensions_js


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
