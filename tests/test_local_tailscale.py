import json

import extensions.local_tailscale as module


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_status_reports_not_installed(monkeypatch):
    monkeypatch.setattr(module, "find_tailscale", lambda: "")
    assert module.local_status() == {
        "installed": False,
        "online": False,
        "backend_state": "NotInstalled",
        "ips": [],
        "dns_name": "",
        "serve": False,
        "app_port": 8892,
        "serve_port": 8893,
    }


def test_status_parses_running_node_and_serve(monkeypatch):
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    status = json.dumps({
        "BackendState": "Running",
        "Self": {"TailscaleIPs": ["100.64.0.20", "fd7a::1"], "DNSName": "genbox.tail.example.ts.net."},
    })
    monkeypatch.setattr(module, "_run", lambda args, timeout=20: (
        Result(stdout=status) if args[1] == "status" else Result(stdout='{"TCP":{"8893":{"HTTP":true}},"Web":{"x":{"Handlers":{"/":{"Proxy":"http://127.0.0.1:8892"}}}}}')
    ))
    result = module.local_status()
    assert result["online"] is True
    assert result["ips"][0] == "100.64.0.20"
    assert result["dns_name"] == "genbox.tail.example.ts.net"
    assert result["serve"] is True


def test_status_handles_null_tailscale_ips_before_login(monkeypatch):
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    status = json.dumps({"BackendState": "NeedsLogin", "Self": {"TailscaleIPs": None, "DNSName": ""}})
    monkeypatch.setattr(module, "_run", lambda args, timeout=20: (
        Result(stdout=status) if args[1] == "status" else Result(returncode=1)
    ))
    result = module.local_status()
    assert result["installed"] is True
    assert result["online"] is False
    assert result["ips"] == []


def test_enable_serve_uses_fixed_local_target(monkeypatch):
    calls = []
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    monkeypatch.setattr(module, "local_status", lambda: {
        "online": True, "ips": ["100.64.0.20"], "dns_name": "genbox.tail.example.ts.net",
    })
    monkeypatch.setattr(module, "_run", lambda args, timeout=20: calls.append(args) or Result())
    result = module.enable_genbox_serve()
    assert calls == [[
        "tailscale", "serve", "--bg", "--http=8893", "http://127.0.0.1:8892",
    ]]
    assert result["url"] == "http://genbox.tail.example.ts.net:8893"
    assert result["address"] == "100.64.0.20"


def test_ping_rejects_non_tailscale_address(monkeypatch):
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    monkeypatch.setattr(module, "_run", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")))
    assert module.ping_peer("192.0.2.10") is False
    assert module.ping_peer("100.64.0.1; reboot") is False
