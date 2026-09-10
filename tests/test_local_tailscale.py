import json

import pytest

import extensions.local_tailscale as module


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def serve_config(proxy="http://127.0.0.1:8892"):
    return json.dumps({
        "TCP": {"8893": {"HTTP": True}},
        "Web": {"genbox.tail.example.ts.net:8893": {"Handlers": {"/": {"Proxy": proxy}}}},
    })


def foreground_serve_config(proxy="http://127.0.0.1:8892"):
    return json.dumps({"Foreground": {"session": json.loads(serve_config(proxy))}})


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
        Result(stdout=status) if args[1] == "status" else Result(stdout=serve_config())
    ))
    result = module.local_status()
    assert result["online"] is True
    assert result["ips"][0] == "100.64.0.20"
    assert result["dns_name"] == "genbox.tail.example.ts.net"
    assert result["serve"] is True


def test_status_accepts_the_foreground_serve_status_shape(monkeypatch):
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    status = json.dumps({
        "BackendState": "Running",
        "Self": {"TailscaleIPs": ["100.64.0.20"], "DNSName": "genbox.tail.example.ts.net."},
    })
    monkeypatch.setattr(module, "_run", lambda args, timeout=20: (
        Result(stdout=status) if args[1] == "status" else Result(stdout=foreground_serve_config())
    ))

    assert module.local_status()["serve"] is True


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
    monkeypatch.setattr(module, "_run", lambda args, timeout=20: (
        calls.append(args) or Result(stdout=serve_config())
        if args[1:3] == ["serve", "status"]
        else Result()
    ))
    result = module.enable_genbox_serve()
    assert calls == [
        ["tailscale", "serve", "status", "--json"],
        ["tailscale", "serve", "status", "--json"],
    ]
    assert result["url"] == "http://genbox.tail.example.ts.net:8893"
    assert result["address"] == "100.64.0.20"


def test_enable_serve_keeps_a_correct_foreground_route(monkeypatch):
    calls = []
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    monkeypatch.setattr(module, "local_status", lambda: {
        "online": True, "ips": ["100.64.0.20"], "dns_name": "genbox.tail.example.ts.net",
    })
    monkeypatch.setattr(module, "_run", lambda args, timeout=20: (
        calls.append(args) or Result(stdout=foreground_serve_config())
        if args[1:3] == ["serve", "status"]
        else Result()
    ))

    module.enable_genbox_serve()

    assert calls == [
        ["tailscale", "serve", "status", "--json"],
        ["tailscale", "serve", "status", "--json"],
    ]


def test_enable_serve_replaces_only_a_single_stale_local_genbox_route(monkeypatch):
    calls = []
    configs = iter([serve_config("http://127.0.0.1:8900"), serve_config()])
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    monkeypatch.setattr(module, "local_status", lambda: {
        "online": True, "ips": ["100.64.0.20"], "dns_name": "genbox.tail.example.ts.net",
    })

    def fake_run(args, timeout=20):
        calls.append(args)
        if args[1:3] == ["serve", "status"]:
            return Result(stdout=next(configs))
        return Result()

    monkeypatch.setattr(module, "_run", fake_run)
    module.enable_genbox_serve()
    assert calls == [
        ["tailscale", "serve", "status", "--json"],
        ["tailscale", "serve", "reset"],
        ["tailscale", "serve", "--bg", "--http=8893", "http://127.0.0.1:8892"],
        ["tailscale", "serve", "status", "--json"],
    ]


def test_enable_serve_refuses_to_reset_a_tailscale_config_with_other_routes(monkeypatch):
    calls = []
    config = json.dumps({
        "TCP": {"8893": {"HTTP": True}, "8080": {"HTTP": True}},
        "Web": {
            "genbox.tail.example.ts.net:8893": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:8900"}}},
            "genbox.tail.example.ts.net:8080": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:8080"}}},
        },
    })
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    monkeypatch.setattr(module, "local_status", lambda: {
        "online": True, "ips": ["100.64.0.20"], "dns_name": "genbox.tail.example.ts.net",
    })
    monkeypatch.setattr(module, "_run", lambda args, timeout=20: calls.append(args) or Result(stdout=config))

    with pytest.raises(RuntimeError, match="other routes"):
        module.enable_genbox_serve()

    assert calls == [["tailscale", "serve", "status", "--json"]]


def test_enable_serve_refuses_to_reset_a_malformed_route(monkeypatch):
    calls = []
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    monkeypatch.setattr(module, "local_status", lambda: {
        "online": True, "ips": ["100.64.0.20"], "dns_name": "genbox.tail.example.ts.net",
    })
    monkeypatch.setattr(
        module,
        "_run",
        lambda args, timeout=20: calls.append(args) or Result(stdout=serve_config("http://127.0.0.1:99999")),
    )

    with pytest.raises(RuntimeError, match="other routes"):
        module.enable_genbox_serve()

    assert calls == [["tailscale", "serve", "status", "--json"]]


def test_ping_rejects_non_tailscale_address(monkeypatch):
    monkeypatch.setattr(module, "find_tailscale", lambda: "tailscale")
    monkeypatch.setattr(module, "_run", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")))
    assert module.ping_peer("192.0.2.10") is False
    assert module.ping_peer("100.64.0.1; reboot") is False
