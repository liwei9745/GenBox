import asyncio
import json
import stat

import asyncssh

from extensions.models import ExtensionTarget, NetworkConnectRequest, SSHCredential
from extensions.network_adapters import (
    NetworkTaskManager,
    command_plan,
    inspect_tailscale_peer_address,
    parse_remote_os_release,
    tailscale_install_plan,
    validate_tailscale_destination,
    validate_tailscale_peer_address,
)


def request(provider: str = "tailscale") -> NetworkConnectRequest:
    return NetworkConnectRequest(
        target=ExtensionTarget(id="vps", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="ssh-secret"),
        trust_host_key=True,
        expected_host_key="SHA256:test",
        provider=provider,
        enrollment_token="",
        operation_mode="existing",
        device_name="genbox-vps",
    )


def test_tailscale_has_a_fixed_install_enroll_verify_plan():
    payload = request().model_dump()
    payload.update(operation_mode="auto", enrollment_token="enrollment-secret-token")
    plan = command_plan(NetworkConnectRequest(**payload))
    assert [phase for phase, _ in plan] == [
        "remote_detect", "remote_detect", "remote_install", "remote_install",
        "remote_enroll", "remote_network_detect",
    ]
    serialized = json.dumps(plan)
    assert "curl -fsSL https://tailscale.com/install.sh | sh" not in serialized
    assert "enrollment-secret-token" not in serialized
    assert "--auth-key=file:<temporary-auth-file>" in serialized


def test_unverified_network_providers_are_rejected_server_side():
    for provider in ("netbird", "cloudflare"):
        payload = request().model_dump()
        payload["provider"] = provider
        try:
            NetworkConnectRequest(**payload)
        except ValueError as exc:
            assert "Tailscale" in str(exc)
        else:
            raise AssertionError(f"{provider} was accepted before it has an equivalent verification chain")


def test_device_name_rejects_shell_metacharacters():
    payload = request().model_dump()
    payload["device_name"] = "name; reboot"
    try:
        NetworkConnectRequest(**payload)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe device name was accepted")


def test_network_task_state_never_exposes_tokens(monkeypatch):
    class Result:
        stdout = ""
        stderr = ""
        exit_status = 0

    class Connection:
        async def run(self, command, **kwargs):
            if "curl -fsS --max-time" in command:
                result = Result()
                result.stdout = json.dumps({
                    "app_mode": "dev", "auth_required": False, "needs_provider_setup": True,
                    "has_configured_provider": False, "has_enabled_provider": False, "provider_count": 0,
                })
                return result
            if command == "id -u":
                result = Result()
                result.stdout = "0\n"
                return result
            if command == "command -v tailscale >/dev/null 2>&1":
                return Result()
            if command == "tailscale status --json":
                result = Result()
                result.stdout = json.dumps({"BackendState": "Running", "TailscaleIPs": ["100.64.0.10"]})
                return result
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892})
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {
            "address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893",
        })
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        saved_targets = []
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda data: saved_targets.append(data))
        manager = NetworkTaskManager()
        task_id = manager.create(request())
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "completed"
        serialized = json.dumps(state)
        assert "ssh-secret" not in serialized
        assert state["result"]["peer_reachable"] is True
        assert state["result"]["genbox_reachable"] is True
        assert len(state["steps"]) == 9
        assert saved_targets[0]["primary_network"] == "tailscale"
        assert saved_targets[0]["network_url"] == "http://genbox.example.ts.net:8893"
        assert state["steps"][3]["status"] == "skipped"
        assert state["steps"][4]["status"] == "skipped"

    asyncio.run(run())


def test_existing_mode_detect_does_not_send_input_or_use_sudo(monkeypatch):
    class Result:
        stdout = ""
        stderr = ""
        exit_status = 0

    class Connection:
        def __init__(self):
            self.calls = []

        async def run(self, command, **kwargs):
            self.calls.append((command, kwargs))
            if "curl -fsS --max-time" in command:
                result = Result()
                result.stdout = json.dumps({
                    "app_mode": "dev", "auth_required": False, "needs_provider_setup": True,
                    "has_configured_provider": False, "has_enabled_provider": False, "provider_count": 0,
                })
                return result
            if command == "id -u":
                result = Result()
                result.stdout = "1000\n"
                return result
            if command == "tailscale status --json":
                result = Result()
                result.stdout = json.dumps({"BackendState": "Running", "TailscaleIPs": ["100.64.0.10"]})
                return result
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(_request):
        return connection, "SHA256:test"

    async def run():
        payload = request().model_dump()
        payload["operation_mode"] = "existing"
        payload["enrollment_token"] = ""
        payload["credential"]["sudo_password"] = "sudo-secret"
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892})
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {
            "address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893",
        })
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda _data: None)
        manager = NetworkTaskManager()
        task_id = manager.create(NetworkConnectRequest(**payload))
        await manager.runners[task_id]
        state = manager.get(task_id)
        detect_calls = [(command, options) for command, options in connection.calls if "tailscale status" in command]
        probe_calls = [command for command, _options in connection.calls if "curl -fsS --max-time 10" in command]
        assert state["status"] == "completed"
        assert state["steps"][2]["status"] == "success"
        assert state["steps"][3]["status"] == "skipped"
        assert state["steps"][4]["status"] == "skipped"
        assert len(detect_calls) == 1
        assert not detect_calls[0][0].startswith("sudo")
        assert "input" not in detect_calls[0][1]
        assert probe_calls == [
            "curl -fsS --max-time 10 http://genbox.example.ts.net:8893/api/setup/status"
        ]
        assert "100.64.0.20" not in probe_calls[0]

    asyncio.run(run())


def test_existing_mode_accepts_warning_prefixed_official_tailscale_json_without_retry(monkeypatch):
    class Result:
        stdout = ""
        stderr = ""
        exit_status = 0

    class Connection:
        def __init__(self):
            self.detect_calls = 0

        async def run(self, command, **kwargs):
            result = Result()
            if "curl -fsS --max-time" in command:
                result.stdout = json.dumps({
                    "app_mode": "dev", "auth_required": False, "needs_provider_setup": True,
                    "has_configured_provider": False, "has_enabled_provider": False, "provider_count": 0,
                })
            elif command == "id -u":
                result.stdout = "0\n"
            elif "tailscale status --json" in command:
                self.detect_calls += 1
                result.stdout = "warning: client update available\n" + json.dumps({
                    "BackendState": "Running",
                    "Self": {"TailscaleIPs": ["100.64.0.10", "fd7a:115c:a1e0::1"]},
                })
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(_request):
        return connection, "SHA256:test"

    async def run():
        payload = request().model_dump()
        payload["operation_mode"] = "existing"
        payload["enrollment_token"] = ""
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892})
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {
            "address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893",
        })
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda _data: None)
        manager = NetworkTaskManager()
        task_id = manager.create(NetworkConnectRequest(**payload))
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "completed"
        assert connection.detect_calls == 1
        assert state["diagnostics"]["json_parsed"] is True
        assert state["diagnostics"]["json_extracted"] is True
        assert state["diagnostics"]["attempt"] == 1
        assert "warning" not in json.dumps(state)

    asyncio.run(run())


def test_existing_mode_needs_login_returns_precise_enrollment_recovery(monkeypatch):
    class Result:
        stdout = ""
        stderr = ""
        exit_status = 0

    class Connection:
        async def run(self, command, **_kwargs):
            result = Result()
            if command == "id -u":
                result.stdout = "0\n"
            elif command == "tailscale status --json":
                result.stdout = json.dumps({"BackendState": "NeedsLogin", "TailscaleIPs": []})
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True})
        manager = NetworkTaskManager()
        task_id = manager.create(request())
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "failed"
        assert state["failed_phase"] == "remote_enroll"
        assert state["recovery_code"] == "TAILSCALE_AUTH_KEY_REQUIRED"
        assert state["next_action"]["type"] == "provide_secret"

    asyncio.run(run())


def test_remote_tailscale_address_detection_retries_until_ipv4_is_ready(monkeypatch):
    class Result:
        stdout = ""
        exit_status = 0

    class Connection:
        def __init__(self):
            self.detect_calls = 0

        async def run(self, command, **kwargs):
            result = Result()
            if command == "id -u":
                result.stdout = "0\n"
            elif "tailscale status --json" in command:
                self.detect_calls += 1
                result.stdout = json.dumps({
                    "BackendState": "Running",
                    "TailscaleIPs": [] if self.detect_calls < 3 else ["100.85.69.88", "fd7a:115c:a1e0::f732:4559"],
                })
            elif "curl -fsS --max-time" in command:
                result.stdout = json.dumps({
                    "app_mode": "dev", "auth_required": False, "needs_provider_setup": True,
                    "has_configured_provider": False, "has_enabled_provider": False, "provider_count": 0,
                })
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(_request):
        return connection, "SHA256:test"

    async def no_sleep(_seconds):
        return None

    async def run():
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.asyncio.sleep", no_sleep)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {
            "online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892,
        })
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {
            "address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893",
        })
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda _data: None)
        manager = NetworkTaskManager()
        task_id = manager.create(request())
        await manager.runners[task_id]
        state = manager.get(task_id)

        assert state["status"] == "completed"
        assert connection.detect_calls == 3
        assert state["result"]["remote_address"] == "100.85.69.88"
        assert state["diagnostics"]["attempt"] == 3
        assert state["diagnostics"]["exit_status"] == 0
        assert state["diagnostics"]["backend_state"] == "running"
        assert state["diagnostics"]["cgnat_candidate_count"] == 1
        assert sum("自动重试" in item["message"] for item in state["logs"]) == 2

    asyncio.run(run())


def test_existing_mode_does_not_require_enrollment_token():
    payload = request().model_dump()
    payload["operation_mode"] = "existing"
    payload["enrollment_token"] = ""
    restored = NetworkConnectRequest(**payload)
    assert restored.operation_mode == "existing"


def test_auto_mode_allows_read_only_detection_without_enrollment_token():
    payload = request().model_dump()
    payload["operation_mode"] = "auto"
    payload["enrollment_token"] = ""
    restored = NetworkConnectRequest(**payload)
    assert restored.enrollment_token.get_secret_value() == ""


def test_auto_mode_accepts_opaque_enrollment_token_without_prefix_rules():
    payload = request().model_dump()
    payload.update(operation_mode="auto", enrollment_token="opaque-one-time-key")
    restored = NetworkConnectRequest(**payload)
    assert restored.enrollment_token.get_secret_value() == "opaque-one-time-key"


def test_auto_mode_without_auth_key_only_detects_and_returns_needs_action(monkeypatch):
    class Result:
        def __init__(self, stdout="", exit_status=0):
            self.stdout = stdout
            self.stderr = ""
            self.exit_status = exit_status

    class Connection:
        def __init__(self):
            self.calls = []

        async def run(self, command, **kwargs):
            self.calls.append((command, kwargs))
            if command == "id -u":
                return Result("0\n")
            if command == "cat /etc/os-release":
                return Result("ID=ubuntu\nVERSION_CODENAME=jammy\n")
            if command == "command -v tailscale >/dev/null 2>&1":
                return Result(exit_status=1)
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(_request):
        return connection, "SHA256:test"

    async def run():
        payload = request().model_dump()
        payload.update(operation_mode="auto", enrollment_token="")
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True})
        manager = NetworkTaskManager()
        task_id = manager.create(NetworkConnectRequest(**payload))
        await manager.runners[task_id]
        state = manager.get(task_id)
        commands = [command for command, _ in connection.calls]

        assert state["status"] == "needs_action"
        assert state["steps"][3]["status"] == "needs_action"
        assert state["recovery_code"] == "TAILSCALE_AUTH_KEY_REQUIRED"
        assert state["next_action"]["type"] == "provide_secret"
        assert not any("apt-get" in command or "tailscale up" in command for command in commands)

    asyncio.run(run())


def test_supported_remote_os_and_install_plan_are_backend_owned():
    assert parse_remote_os_release('ID="ubuntu"\nVERSION_CODENAME=jammy\n') == ("ubuntu", "jammy")
    plan = tailscale_install_plan("ubuntu", "jammy", "a" * 32)
    serialized = json.dumps(plan)
    assert "pkgs.tailscale.com/stable/ubuntu/jammy" in serialized
    assert "install.sh" not in serialized
    assert "a" * 32 in serialized


def test_tailscale_destination_validator_accepts_only_the_verified_private_route():
    assert validate_tailscale_destination(
        "http://genbox.example.ts.net:8893",
        address="100.64.0.20",
        dns_name="genbox.example.ts.net",
        serve_port=8893,
        app_port=8892,
    ) == "http://genbox.example.ts.net:8893"


def test_tailscale_peer_address_accepts_official_status_json_and_legacy_text():
    assert validate_tailscale_peer_address(json.dumps({
        "BackendState": "Running",
        "TailscaleIPs": ["100.85.69.88", "fd7a:115c:a1e0::f732:4559"],
        "Self": {"TailscaleIPs": ["100.85.69.88"]},
    })) == "100.85.69.88"
    assert validate_tailscale_peer_address(json.dumps({
        "BackendState": "Running",
        "Self": {"TailscaleIPs": ["100.85.69.88", "fd7a:115c:a1e0::f732:4559"]},
    })) == "100.85.69.88"
    assert validate_tailscale_peer_address(
        "warning: backend is warming up\n100.85.69.88\n"
    ) == "100.85.69.88"
    assert validate_tailscale_peer_address(
        "warning: client version differs\n" + json.dumps({
            "BackendState": "Running",
            "TailscaleIPs": ["100.85.69.88"],
        })
    ) == "100.85.69.88"


def test_tailscale_status_diagnostics_are_structured_and_secret_free():
    address, diagnostics, error = inspect_tailscale_peer_address(
        "warning: public client notice\n" + json.dumps({
            "BackendState": "Running",
            "Self": {"TailscaleIPs": ["100.85.69.88", "fd7a:115c:a1e0::f732:4559"]},
        })
    )

    assert address == "100.85.69.88"
    assert error is None
    assert diagnostics == {
        "stdout_present": True,
        "json_parsed": True,
        "json_extracted": True,
        "json_type": "object",
        "backend_state": "running",
        "top_level_ips_present": False,
        "top_level_ip_count": 0,
        "self_ips_present": True,
        "self_ip_count": 2,
        "cgnat_candidate_count": 1,
    }
    serialized = json.dumps(diagnostics)
    assert "100.85.69.88" not in serialized
    assert "warning" not in serialized


def test_tailscale_peer_address_rejects_offline_missing_or_ambiguous_status():
    invalid = (
        json.dumps({"TailscaleIPs": ["100.85.69.88"]}),
        json.dumps({"BackendState": "", "TailscaleIPs": ["100.85.69.88"]}),
        json.dumps({"BackendState": "NeedsLogin", "TailscaleIPs": ["100.85.69.88"]}),
        json.dumps({"BackendState": "Starting", "TailscaleIPs": ["100.85.69.88"]}),
        json.dumps({"BackendState": "Stopped", "TailscaleIPs": ["100.85.69.88"]}),
        json.dumps({"BackendState": "Running", "TailscaleIPs": []}),
        json.dumps({"BackendState": "Running", "TailscaleIPs": ["100.85.69.88", "100.85.69.89"]}),
        json.dumps(["100.85.69.88"]),
        json.dumps("100.85.69.88"),
        "192.0.2.10",
    )
    for output in invalid:
        try:
            validate_tailscale_peer_address(output)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid Tailscale status was accepted: {output}")


def test_tailscale_destination_validator_rejects_loopback_public_and_unsafe_urls():
    unsafe = (
        "http://127.0.0.1:8893",
        "http://192.0.2.10:8893",
        "http://100.64.0.20:8893",
        "http://other.example.ts.net:8893",
        "http://genbox.example.com:8893",
        "http://user:password@genbox.example.ts.net:8893",
        "http://genbox.example.ts.net:8893/#fragment",
        "http://genbox.example.ts.net:8892",
    )
    for url in unsafe:
        try:
            validate_tailscale_destination(
                url,
                address="100.64.0.20",
                dns_name="genbox.example.ts.net",
                serve_port=8893,
                app_port=8892,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe destination was accepted: {url}")


def test_network_task_failure_marks_the_active_phase_and_provides_recovery(monkeypatch):
    async def run():
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": False})
        manager = NetworkTaskManager()
        task_id = manager.create(request())
        await manager.runners[task_id]
        state = manager.get(task_id)

        assert state["status"] == "failed"
        assert state["failed_phase"] == "local_detect"
        assert state["steps"][0]["status"] == "failed"
        assert state["recovery_code"] == "TAILSCALE_LOCAL_OFFLINE"
        assert state["recovery_action"]
        assert "enrollment-secret-token" not in json.dumps(state)
        assert "ssh-secret" not in json.dumps(state)

    asyncio.run(run())


def test_network_task_hides_raw_ssh_client_errors_from_state_and_logs(monkeypatch):
    async def reject(_request):
        raise RuntimeError(
            "Permission denied for user hidden-user on host hidden.example 192.0.2.77 ssh-secret"
        )

    async def run():
        monkeypatch.setattr(
            "extensions.network_adapters.local_status",
            lambda: {"online": True},
        )
        monkeypatch.setattr("extensions.network_adapters._connect", reject)
        manager = NetworkTaskManager()
        task_id = manager.create(request())
        await manager.runners[task_id]
        state = manager.get(task_id)
        serialized = json.dumps(state)

        assert state["status"] == "failed"
        assert state["failed_phase"] == "remote_connect"
        assert "原始错误已隐藏" in state["error"]
        for secret in (
            "Permission denied",
            "hidden-user",
            "hidden.example",
            "192.0.2.77",
            "ssh-secret",
        ):
            assert secret not in serialized

    asyncio.run(run())


def test_auto_mode_installs_starts_enrolls_with_sftp_and_cleans_secret(monkeypatch):
    auth_key = "opaque-one-time-auth-key"

    class Result:
        def __init__(self, stdout="", exit_status=0, stderr=""):
            self.stdout = stdout
            self.exit_status = exit_status
            self.stderr = stderr

    class RemoteFile:
        def __init__(self, sftp, path):
            self.sftp = sftp
            self.path = path

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def write(self, value):
            self.sftp.files[self.path] = value

    class SFTP:
        def __init__(self):
            self.files = {}
            self.removed = []

        def open(self, path, mode, attrs=None):
            assert mode == "xb"
            assert attrs.permissions == 0o600
            assert path not in self.files
            return RemoteFile(self, path)

        async def chmod(self, path, mode):
            assert mode == 0o600
            assert path in self.files

        async def lstat(self, path):
            if path not in self.files:
                raise asyncssh.SFTPNoSuchFile("missing")
            value = self.files[path]
            return type("Attrs", (), {
                "size": len(value if isinstance(value, bytes) else value.encode("utf-8")),
                "permissions": stat.S_IFREG | 0o600,
            })()

        async def remove(self, path):
            if path not in self.files:
                raise asyncssh.SFTPNoSuchFile("missing")
            self.removed.append(path)
            del self.files[path]

        def exit(self):
            pass

        async def wait_closed(self):
            pass

    class Connection:
        def __init__(self):
            self.calls = []
            self.installed = False
            self.enrolled = False
            self.sftp = SFTP()

        async def start_sftp_client(self):
            return self.sftp

        async def run(self, command, **kwargs):
            self.calls.append((command, kwargs))
            if command == "id -u":
                return Result("0\n")
            if command == "cat /etc/os-release":
                return Result('ID="ubuntu"\nVERSION_CODENAME=jammy\n')
            if command == "command -v tailscale >/dev/null 2>&1":
                return Result(exit_status=0 if self.installed else 1)
            if command == "printf %s \"$HOME\"":
                return Result("/root")
            if command == "tailscale status --json":
                if not self.enrolled:
                    return Result(json.dumps({"BackendState": "NeedsLogin", "TailscaleIPs": []}))
                return Result(json.dumps({"BackendState": "Running", "TailscaleIPs": ["100.64.0.10"]}))
            if "DEBIAN_FRONTEND=noninteractive apt-get install -y tailscale" in command:
                self.installed = True
                return Result()
            if "tailscale up --auth-key=file:" in command:
                self.enrolled = True
                return Result()
            if "test ! -e" in command or "cmp -s" in command:
                return Result()
            if "test -e /usr/share/keyrings/tailscale-archive-keyring.gpg" in command:
                return Result(exit_status=1)
            if "test -e /etc/apt/sources.list.d/tailscale.list" in command:
                return Result(exit_status=1)
            if "curl -fsS --max-time 10" in command:
                return Result(json.dumps({
                    "app_mode": "dev", "auth_required": False,
                    "needs_provider_setup": True, "has_configured_provider": False,
                    "has_enabled_provider": False, "provider_count": 0,
                }))
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(_request):
        return connection, "SHA256:test"

    async def run():
        payload = request().model_dump()
        payload.update(operation_mode="auto", enrollment_token=auth_key)
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {
            "online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892,
        })
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {
            "address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893",
        })
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        saved = []
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda data: saved.append(data))
        manager = NetworkTaskManager()
        task_id = manager.create(NetworkConnectRequest(**payload))
        await manager.runners[task_id]
        state = manager.get(task_id)

        assert state["status"] == "completed"
        assert state["steps"][3]["status"] == "success"
        assert state["steps"][4]["status"] == "success"
        assert connection.installed is True
        assert connection.enrolled is True
        assert connection.sftp.files == {}
        assert len(connection.sftp.removed) == 1
        assert saved and saved[0]["network_url"] == "http://genbox.example.ts.net:8893"
        serialized_calls = json.dumps(connection.calls)
        assert auth_key not in serialized_calls
        assert auth_key not in json.dumps(state)
        assert auth_key not in json.dumps(saved)
        assert any("pkgs.tailscale.com/stable/ubuntu/jammy" in command for command, _ in connection.calls)
        assert not any("install.sh" in command for command, _ in connection.calls)
        assert any("--auth-key=file:" in command for command, _ in connection.calls)

    asyncio.run(run())


def test_network_manager_single_flight_returns_same_active_task(monkeypatch):
    release = asyncio.Event()

    async def fake_run(_task_id, _request):
        await release.wait()

    async def run():
        manager = NetworkTaskManager()
        monkeypatch.setattr(manager, "_run", fake_run)
        first = manager.create(request())
        second = manager.create(request())
        assert second == first
        assert len(manager.runners) == 1
        release.set()
        await manager.runners[first]

    asyncio.run(run())


def test_manager_rejects_plain_text_tailscale_ip_as_completed_status(monkeypatch):
    class Result:
        stdout = ""
        stderr = ""
        exit_status = 0

    class Connection:
        async def run(self, command, **_kwargs):
            result = Result()
            if command == "id -u":
                result.stdout = "0\n"
            elif command == "tailscale status --json":
                result.stdout = "warning: 100.64.0.10"
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True})
        manager = NetworkTaskManager()
        task_id = manager.create(request())
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "failed"
        assert state["result"] is None
        assert state["failed_phase"] in {"remote_install", "remote_enroll"}

    asyncio.run(run())


def test_auto_mode_starts_stopped_service_without_reinstall_or_consuming_auth_key(monkeypatch):
    class Result:
        def __init__(self, stdout="", exit_status=0, stderr=""):
            self.stdout = stdout
            self.exit_status = exit_status
            self.stderr = stderr

    class Connection:
        def __init__(self):
            self.calls = []
            self.started = False
            self.sftp_started = False

        async def start_sftp_client(self):
            self.sftp_started = True
            raise AssertionError("a Running node must not consume the Auth Key")

        async def run(self, command, **kwargs):
            self.calls.append((command, kwargs))
            if command == "id -u":
                return Result("0\n")
            if command == "cat /etc/os-release":
                return Result("ID=debian\nVERSION_CODENAME=bookworm\n")
            if command == "command -v tailscale >/dev/null 2>&1":
                return Result()
            if command == "tailscale status --json":
                if not self.started:
                    return Result(exit_status=1, stderr="daemon unavailable")
                return Result(json.dumps({"BackendState": "Running", "TailscaleIPs": ["100.64.0.10"]}))
            if "systemctl enable --now tailscaled" in command:
                self.started = True
                return Result()
            if "curl -fsS --max-time 10" in command:
                return Result(json.dumps({
                    "app_mode": "dev", "auth_required": False,
                    "needs_provider_setup": True, "has_configured_provider": False,
                    "has_enabled_provider": False, "provider_count": 0,
                }))
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(_request):
        return connection, "SHA256:test"

    async def run():
        payload = request().model_dump()
        payload.update(operation_mode="auto", enrollment_token="unused-one-time-key")
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892})
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {"address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893"})
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda _data: None)
        manager = NetworkTaskManager()
        task_id = manager.create(NetworkConnectRequest(**payload))
        await manager.runners[task_id]
        state = manager.get(task_id)
        commands = [command for command, _ in connection.calls]

        assert state["status"] == "completed"
        assert connection.started is True
        assert connection.sftp_started is False
        assert state["steps"][4]["status"] == "skipped"
        assert not any("apt-get" in command or "pkgs.tailscale.com" in command for command in commands)
        assert not any("tailscale up" in command for command in commands)

    asyncio.run(run())


def test_auth_file_cleanup_reconnects_once_and_fails_closed_when_reconnect_is_unavailable(monkeypatch):
    class Result:
        def __init__(self, stdout="", exit_status=0):
            self.stdout = stdout
            self.stderr = ""
            self.exit_status = exit_status

    class RemoteFile:
        def __init__(self, shared):
            self.shared = shared

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def write(self, value):
            self.shared["secret_file"] = value

    class BrokenRemoveSFTP:
        def __init__(self, shared):
            self.shared = shared

        def open(self, _path, mode, attrs=None):
            assert mode == "xb" and attrs.permissions == 0o600
            return RemoteFile(self.shared)

        async def chmod(self, _path, mode):
            assert mode == 0o600

        async def lstat(self, _path):
            value = self.shared["secret_file"]
            if value is None:
                raise asyncssh.SFTPNoSuchFile("missing")
            return type("Attrs", (), {"size": len(value), "permissions": stat.S_IFREG | 0o600})()

        async def remove(self, _path):
            raise ConnectionError("original SSH channel closed")

        def exit(self):
            pass

        async def wait_closed(self):
            pass

    class PrimaryConnection:
        def __init__(self, shared):
            self.shared = shared
            self.sftp = BrokenRemoveSFTP(shared)

        async def start_sftp_client(self):
            return self.sftp

        async def run(self, command, **_kwargs):
            if command == "id -u":
                return Result("0\n")
            if command == "cat /etc/os-release":
                return Result("ID=ubuntu\nVERSION_CODENAME=jammy\n")
            if command == "command -v tailscale >/dev/null 2>&1":
                return Result()
            if command == "tailscale status --json":
                state = "Running" if self.shared["enrolled"] else "NeedsLogin"
                ips = ["100.64.0.10"] if self.shared["enrolled"] else []
                return Result(json.dumps({"BackendState": state, "TailscaleIPs": ips}))
            if command == 'printf %s "$HOME"':
                return Result("/root")
            if "tailscale up --auth-key=file:" in command:
                self.shared["enrolled"] = True
                return Result()
            if command.startswith("rm -f -- ") or command.startswith("test ! -e "):
                await asyncio.sleep(0.02)
                raise ConnectionError("original SSH connection is gone")
            if "curl -fsS --max-time 10" in command:
                return Result(json.dumps({
                    "app_mode": "dev", "auth_required": False,
                    "needs_provider_setup": True, "has_configured_provider": False,
                    "has_enabled_provider": False, "provider_count": 0,
                }))
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    class CleanupConnection:
        def __init__(self, shared):
            self.shared = shared

        async def run(self, command, **_kwargs):
            if command.startswith("rm -f -- "):
                self.shared["secret_file"] = None
                return Result()
            if command.startswith("test ! -e "):
                return Result(exit_status=0 if self.shared["secret_file"] is None else 1)
            return Result(exit_status=1)

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def execute(reconnect_succeeds):
        shared = {"secret_file": None, "enrolled": False}
        primary = PrimaryConnection(shared)
        connect_calls = 0

        async def fake_connect(_request):
            nonlocal connect_calls
            connect_calls += 1
            if connect_calls == 1:
                return primary, "SHA256:test"
            if reconnect_succeeds:
                return CleanupConnection(shared), "SHA256:test"
            raise ConnectionError("reconnect unavailable")

        payload = request().model_dump()
        payload.update(operation_mode="auto", enrollment_token="cleanup-one-time-key")
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892})
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {"address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893"})
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda _data: None)
        manager = NetworkTaskManager()
        task_id = manager.create(NetworkConnectRequest(**payload))
        await manager.runners[task_id]
        return manager.get(task_id), shared, connect_calls

    async def run():
        monkeypatch.setattr("extensions.network_adapters.AUTH_CLEANUP_COMMAND_TIMEOUT", 0.005)
        success, success_shared, success_calls = await execute(True)
        assert success["status"] == "completed"
        assert success_shared["secret_file"] is None
        assert success_calls == 2

        failed, failed_shared, failed_calls = await execute(False)
        assert failed["status"] == "failed"
        assert failed["recovery_code"] == "AUTH_FILE_CLEANUP_FAILED"
        assert failed_shared["secret_file"] is not None
        assert failed_calls == 2
        assert "cleanup-one-time-key" not in json.dumps(failed)

    asyncio.run(run())


def test_transient_peer_success_with_invalid_app_probe_fails_http_probe_without_running_steps(monkeypatch):
    class Result:
        def __init__(self, stdout="", exit_status=0):
            self.stdout = stdout
            self.stderr = ""
            self.exit_status = exit_status

    class Connection:
        async def run(self, command, **_kwargs):
            if command == "id -u":
                return Result("0\n")
            if command == "command -v tailscale >/dev/null 2>&1":
                return Result()
            if command == "tailscale status --json":
                return Result(json.dumps({"BackendState": "Running", "TailscaleIPs": ["100.64.0.10"]}))
            if "curl -fsS --max-time 10" in command:
                return Result("<html>not GenBox</html>")
            return Result()

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:test"

    async def no_sleep(_seconds):
        return None

    async def run():
        ping_results = iter([True, False, False, False, False, False])
        saved = []
        monkeypatch.setattr("extensions.network_adapters._connect", fake_connect)
        monkeypatch.setattr("extensions.network_adapters.asyncio.sleep", no_sleep)
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True, "dns_name": "genbox.example.ts.net", "serve_port": 8893, "app_port": 8892})
        monkeypatch.setattr("extensions.network_adapters.enable_genbox_serve", lambda: {"address": "100.64.0.20", "url": "http://genbox.example.ts.net:8893"})
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: next(ping_results))
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda data: saved.append(data))
        manager = NetworkTaskManager()
        task_id = manager.create(request())
        await manager.runners[task_id]
        state = manager.get(task_id)

        assert state["status"] == "failed"
        assert state["failed_phase"] == "http_probe"
        assert state["recovery_code"] == "GENBOX_HTTP_PROBE_FAILED"
        assert state["steps"][6]["status"] == "success"
        assert state["steps"][7]["status"] == "failed"
        assert all(step["status"] != "running" for step in state["steps"])
        assert saved == []

    asyncio.run(run())
