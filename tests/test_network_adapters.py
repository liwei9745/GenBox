import asyncio
import json

from extensions.models import ExtensionTarget, NetworkConnectRequest, SSHCredential
from extensions.network_adapters import NetworkTaskManager, command_plan, validate_tailscale_destination


def request(provider: str = "tailscale") -> NetworkConnectRequest:
    return NetworkConnectRequest(
        target=ExtensionTarget(id="vps", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="ssh-secret"),
        trust_host_key=True,
        expected_host_key="SHA256:test",
        provider=provider,
        enrollment_token="enrollment-secret-token",
        operation_mode="existing",
        device_name="genbox-vps",
    )


def test_tailscale_has_a_fixed_install_enroll_verify_plan():
    plan = command_plan(request())
    assert [phase for phase, _ in plan] == ["remote_detect"]
    assert "enrollment-secret-token" not in plan[0][1]


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
        stdout = "100.64.0.10\n"
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
            "address": "100.64.0.20", "url": "http://100.64.0.20:8893",
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
        assert "enrollment-secret-token" not in serialized
        assert "ssh-secret" not in serialized
        assert state["result"]["peer_reachable"] is True
        assert state["result"]["genbox_reachable"] is True
        assert len(state["steps"]) == 9
        assert saved_targets[0]["primary_network"] == "tailscale"
        assert saved_targets[0]["network_url"] == "http://100.64.0.20:8893"
        assert "enrollment-secret-token" not in json.dumps(saved_targets)

    asyncio.run(run())


def test_existing_mode_detect_does_not_send_input_or_use_sudo(monkeypatch):
    class Result:
        stdout = "100.64.0.10\n"
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
            "address": "100.64.0.20", "url": "http://100.64.0.20:8893",
        })
        monkeypatch.setattr("extensions.network_adapters.ping_peer", lambda _address: True)
        monkeypatch.setattr("extensions.network_adapters.upsert_target", lambda _data: None)
        manager = NetworkTaskManager()
        task_id = manager.create(NetworkConnectRequest(**payload))
        await manager.runners[task_id]
        state = manager.get(task_id)
        detect_calls = [(command, options) for command, options in connection.calls if "tailscale status" in command]
        assert state["status"] == "completed"
        assert state["steps"][2]["status"] == "success"
        assert len(detect_calls) == 1
        assert not detect_calls[0][0].startswith("sudo")
        assert "input" not in detect_calls[0][1]

    asyncio.run(run())


def test_existing_mode_does_not_require_enrollment_token():
    payload = request().model_dump()
    payload["operation_mode"] = "existing"
    payload["enrollment_token"] = ""
    restored = NetworkConnectRequest(**payload)
    assert restored.operation_mode == "existing"


def test_auto_mode_requires_enrollment_token():
    payload = request().model_dump()
    payload["operation_mode"] = "auto"
    payload["enrollment_token"] = ""
    try:
        NetworkConnectRequest(**payload)
    except ValueError as exc:
        assert "自动加入 Tailnet" in str(exc)
    else:
        raise AssertionError("auto mode accepted an empty enrollment token")


def test_tailscale_destination_validator_accepts_only_the_verified_private_route():
    assert validate_tailscale_destination(
        "http://100.64.0.20:8893",
        address="100.64.0.20",
        serve_port=8893,
        app_port=8892,
    ) == "http://100.64.0.20:8893"


def test_tailscale_destination_validator_rejects_loopback_public_and_unsafe_urls():
    unsafe = (
        "http://127.0.0.1:8893",
        "http://192.0.2.10:8893",
        "http://genbox.example.ts.net:8893",
        "http://user:password@genbox.example.ts.net:8893",
        "http://genbox.example.ts.net:8893/#fragment",
        "http://genbox.example.ts.net:8892",
    )
    for url in unsafe:
        try:
            validate_tailscale_destination(url, address="100.64.0.20", serve_port=8893, app_port=8892)
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
