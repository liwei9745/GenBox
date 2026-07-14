import asyncio
import json

from extensions.models import ExtensionTarget, NetworkConnectRequest, SSHCredential
from extensions.network_adapters import NetworkTaskManager, command_plan


def request(provider: str = "tailscale") -> NetworkConnectRequest:
    return NetworkConnectRequest(
        target=ExtensionTarget(id="vps", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="ssh-secret"),
        trust_host_key=True,
        expected_host_key="SHA256:test",
        provider=provider,
        enrollment_token="enrollment-secret-token",
        device_name="genbox-vps",
    )


def test_each_provider_has_fixed_install_enroll_verify_plan():
    for provider in ("tailscale", "netbird", "cloudflare"):
        plan = command_plan(request(provider))
        assert [phase for phase, _ in plan] == ["remote_install", "remote_enroll", "remote_detect"]
        assert len(plan) == 3


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
                return Result()
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
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True})
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
        assert len(state["steps"]) == 8
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
        monkeypatch.setattr("extensions.network_adapters.local_status", lambda: {"online": True})
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
    payload["enrollment_token"] = ""
    try:
        NetworkConnectRequest(**payload)
    except ValueError:
        pass
    else:
        raise AssertionError("auto mode accepted an empty enrollment token")
