import asyncio
import shlex

import pytest

from extensions.discovery import (
    ApprovedReadOnlyCommandError,
    _ApprovedReadOnlyConnection,
    _evaluate_path_conditions,
    _parse_canonical_port_bindings,
    _parse_canonical_tcp_listeners,
    _parse_listening_ports,
    _parse_published_ports,
    discover_environment,
)
from extensions.models import ExtensionDiscoveryRequest, ExtensionTarget, SSHCredential
from extensions.read_only_discovery_plan import validate_read_only_discovery_plan


READ_ONLY_FINGERPRINT = "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _approved_plan():
    return validate_read_only_discovery_plan({
        "authorization": {
            "scope": "read-only-discovery", "target_role": "isolated-development",
            "host": "safe.example", "port": 22, "username": "deploy-user",
            "approval_record_id": "approval-20260729-12345678",
            "approved_at": "2026-07-29T12:00:00+00:00",
        },
        "trust": {
            "expected_host": "safe.example", "expected_port": 22,
            "expected_algorithm": "ssh-ed25519", "expected_fingerprint": READ_ONLY_FINGERPRINT,
            "observed_host": "safe.example", "observed_port": 22,
            "observed_algorithm": "ssh-ed25519", "observed_fingerprint": READ_ONLY_FINGERPRINT,
        },
        "operations": [
            {"id": "identity"}, {"id": "os_release"}, {"id": "cpu_architecture"},
            {"id": "cpu_count"}, {"id": "memory_summary"}, {"id": "home_directory"},
            {"id": "python_version"}, {"id": "uv_version"},
            {"id": "docker_version"}, {"id": "compose_version"},
            {"id": "docker_ps"}, {"id": "compose_ls"}, {"id": "listening_ports"},
            {"id": "capacity", "path": "/"},
        ],
    })


def test_sudo_docker_command_preserves_go_template_quotes():
    command = 'docker inspect --format \'{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Source}}{{end}}{{end}}\' abc123'
    wrapped = f"sudo -n sh -lc {shlex.quote(command)}"

    assert shlex.split(wrapped)[-1] == command


def test_approved_executor_rejects_command_drift_before_ssh_execution():
    class Connection:
        def __init__(self):
            self.commands = []

        async def run(self, command, **kwargs):
            self.commands.append(command)

    connection = Connection()
    guarded = _ApprovedReadOnlyConnection(connection, _approved_plan())

    with pytest.raises(ApprovedReadOnlyCommandError):
        asyncio.run(guarded.run("cat /etc/shadow", check=False))

    assert connection.commands == []


def test_structured_docker_port_parser_requires_unique_valid_host_ports():
    assert _parse_published_ports('{"80/tcp":[{"HostIp":"0.0.0.0","HostPort":"33010"}]}') == [33010]
    assert _parse_published_ports(
        '{"80/tcp":[{"HostPort":"33010"}],"443/tcp":[{"HostPort":"33443"}]}'
    ) == [33010, 33443]
    assert _parse_published_ports("not-json") == []


def test_canonical_docker_bindings_include_exposure_identity_and_are_deterministic():
    bindings, complete = _parse_canonical_port_bindings(
        '{"443/UDP":[{"HostIp":"::1","HostPort":"33443"}],'
        '"80/tcp":[{"HostIp":"0.0.0.0","HostPort":"33010"},'
        '{"HostIp":"0.0.0.0","HostPort":"33010"},'
        '{"HostIp":"127.0.0.1","HostPort":"33010"}]}'
    )

    assert complete is True
    assert bindings == [
        {"host_ip": "0.0.0.0", "host_port": 33010, "container_port": 80, "protocol": "tcp"},
        {"host_ip": "0.0.0.0", "host_port": 33010, "container_port": 80, "protocol": "tcp"},
        {"host_ip": "127.0.0.1", "host_port": 33010, "container_port": 80, "protocol": "tcp"},
        {"host_ip": "::1", "host_port": 33443, "container_port": 443, "protocol": "udp"},
    ]


@pytest.mark.parametrize("value", [
    "",
    "not-json",
    '{"80/tcp":[{"HostPort":"33010"}]}',
    '{"80/tcp":[{"HostIp":"0.0.0.0","HostPort":true}]}',
    '{"invalid":[{"HostIp":"0.0.0.0","HostPort":"33010"}]}',
    '{"80/tcp":null}',
])
def test_canonical_docker_bindings_fail_closed_when_identity_is_incomplete(value):
    bindings, complete = _parse_canonical_port_bindings(value)
    assert bindings == []
    assert complete is False


@pytest.mark.parametrize(("status", "output", "listeners", "ports", "complete"), [
    (0, "GENBOX_TCP_LISTENERS_V1\n", [], [], True),
    (0, "", [], [], False),
    (
        0,
        "0.0.0.0:22\n:::33010\n0.0.0.0:22",
        [
            {"protocol": "tcp", "host_port": 22},
            {"protocol": "tcp", "host_port": 22},
            {"protocol": "tcp", "host_port": 33010},
        ],
        [22, 33010],
        True,
    ),
    (0, "LISTEN 0 128 0.0.0.0:22 0.0.0.0:*", [{"protocol": "tcp", "host_port": 22}], [22], True),
    (1, "GENBOX_TCP_LISTENERS_V1\n", [], [], False),
    (0, "unsupported listener output", [], [], False),
])
def test_listener_probe_never_treats_failure_or_garbled_output_as_no_listeners(
    status, output, listeners, ports, complete,
):
    assert _parse_canonical_tcp_listeners(status, output) == (listeners, complete)
    assert _parse_listening_ports(status, output) == (ports, complete)


@pytest.mark.parametrize(("failed_kind", "expected"), [
    (None, True),
    ("absent", False),
    ("claimable_parent", False),
])
def test_isolated_empty_path_probes_require_absence_and_direct_parent_claimability(
    failed_kind, expected,
):
    commands = []

    class Result:
        def __init__(self, exit_status=0):
            self.exit_status = exit_status
            self.stdout = ""

    class Connection:
        async def run(self, command, check=False, **kwargs):
            commands.append(command)
            if failed_kind == "absent" and command.startswith("test ! -e "):
                return Result(1)
            if failed_kind == "claimable_parent" and command.startswith("candidate="):
                return Result(1)
            return Result()

    checks = {
        "target_install_dir_absent": {"kind": "absent", "path": "/home/operator/app"},
        "target_install_parent_claimable": {"kind": "claimable_parent", "path": "/home/operator"},
        "target_data_dir_nonoverlap": {"kind": "data_nonoverlap", "path": "/home/operator/app/data"},
        "target_compose_project_nonoverlap": {"kind": "compose_nonoverlap", "compose_project": "genbox-app"},
        "target_port_unoccupied": {"kind": "tcp_port_unoccupied", "port": 33010},
    }
    conditions = asyncio.run(_evaluate_path_conditions(
        Connection(), SSHCredential(password="test-only"), {}, checks, [], [], True, 4096,
    ))

    assert all(conditions.values()) is expected
    assert not any(command.startswith("sudo ") for command in commands)


def test_docker_helper_retries_failed_size_probe_with_sudo():
    from extensions.discovery import _run_docker

    class Result:
        def __init__(self, status, stdout=""):
            self.exit_status = status
            self.stdout = stdout

    class Connection:
        def __init__(self):
            self.commands = []

        async def run(self, command, check=False, **kwargs):
            self.commands.append(command)
            if command.startswith("du -sm"):
                return Result(1)
            if command.startswith("sudo -n true"):
                return Result(0)
            if command.startswith("sudo -n sh -lc"):
                return Result(0, "2048\t/root/chatgpt2api/data")
            return Result(1)

    connection = Connection()
    status, output = asyncio.run(_run_docker(
        connection, "du -sm /root/chatgpt2api/data 2>/dev/null", "",
    ))

    assert status == 0
    assert output.startswith("2048")
    assert any(command.startswith("sudo -n sh -lc") for command in connection.commands)


def test_discovery_marks_clone_unavailable_when_data_size_cannot_be_read(monkeypatch):
    # The implementation must not treat a permission-denied size probe as an empty source.
    from extensions import discovery

    class Result:
        exit_status = 0
        stdout = ""

    class Connection:
        async def run(self, command, check=False, **kwargs):
            result = Result()
            if "docker inspect --format" in command and ".Mounts" in command:
                result.stdout = "/root/chatgpt2api/data" if '"/app/data"' in command else "/root/chatgpt2api/config.json"
            elif "docker ps" in command:
                result.stdout = '{"ID":"abc123","Image":"ghcr.io/yukkcat/chatgpt2api:latest","Names":"chatgpt2api","Status":"Up 1 hour"}'
            elif "du -sm" in command:
                result.exit_status = 1
            elif "MemTotal" in command:
                result.stdout = "1024"
            elif "getconf" in command:
                result.stdout = "2"
            elif "df -Pm" in command:
                result.stdout = "4096"
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(request):
        return Connection(), "SHA256:test"

    monkeypatch.setattr(discovery, "_connect", fake_connect)
    request = ExtensionDiscoveryRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="secret"),
        trust_host_key=True,
    )
    result = asyncio.run(discovery.discover_environment(request))

    assert result["instances"][0]["data_size_mb"] is None
    assert result["instances"][0]["clone_available"] is False


def test_approved_discovery_executes_only_plan_mapped_commands(monkeypatch):
    commands = []

    class Result:
        exit_status = 0

        def __init__(self, stdout=""):
            self.stdout = stdout

    class Connection:
        async def run(self, command, check=False, **kwargs):
            commands.append(command)
            if command == "id -u":
                return Result("0")
            if "docker ps -a" in command:
                return Result('{"ID":"abc123456789","Image":"ghcr.io/yukkcat/chatgpt2api:latest","Names":"chatgpt2api","Status":"Up 1 hour","Ports":"0.0.0.0:3000->80/tcp"}')
            if "docker inspect --format" in command:
                if ".Config.Image" in command:
                    return Result("ghcr.io/yukkcat/chatgpt2api:latest")
                if "{{.Image}}" in command:
                    return Result("sha256:source-image")
                if ".NetworkSettings.Ports" in command:
                    return Result('{"80/tcp":[{"HostIp":"0.0.0.0","HostPort":"3000"}]}')
                if 'Destination \\"/app/data\\"' in command or 'Destination "/app/data"' in command:
                    return Result("/opt/chatgpt2api/data")
                if 'Destination \\"/app/config.json\\"' in command or 'Destination "/app/config.json"' in command:
                    return Result("/opt/chatgpt2api/config.json")
                return Result("false||legacy-project|/opt/chatgpt2api|app")
            if "docker version" in command:
                return Result("27.1.0")
            if "docker compose version" in command:
                return Result("2.29.0")
            if "MemTotal" in command:
                return Result("4096")
            if "df -Pm" in command:
                return Result("50000")
            if "du -sm" in command:
                return Result("120")
            if "_NPROCESSORS" in command:
                return Result("4")
            if "ss -H" in command:
                return Result("0.0.0.0:22\n0.0.0.0:3000")
            return Result("ubuntu 24.04")

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), READ_ONLY_FINGERPRINT

    async def run():
        monkeypatch.setattr("extensions.discovery._connect", fake_connect)
        return await discover_environment(
            ExtensionDiscoveryRequest(
                target=ExtensionTarget(id="t", name="VPS", host="safe.example", username="deploy-user"),
                credential=SSHCredential(password="test-only"), trust_host_key=True,
            ),
            approved_plan=_approved_plan(),
        )

    result = asyncio.run(run())

    assert result["instances"][0]["clone_available"] is True
    assert result["privileges"]["diagnostic_code"] == "read_only_direct_docker"
    assert not any("docker image inspect" in command for command in commands)
    assert not any(command.startswith("sudo ") for command in commands)
def test_discovery_is_read_only_and_classifies_existing_instance(monkeypatch):
    commands = []

    class Result:
        exit_status = 0

        def __init__(self, stdout=""):
            self.stdout = stdout

    class Connection:
        async def run(self, command, check=False):
            commands.append(command)
            if "docker ps -a" in command:
                return Result('{"ID":"abc123456789","Image":"ghcr.io/yukkcat/chatgpt2api:latest","Names":"chatgpt2api","Status":"Up 1 hour","Ports":"0.0.0.0:3000->80/tcp"}')
            if "docker image inspect" in command:
                return Result("ghcr.io/yukkcat/chatgpt2api@sha256:source-digest")
            if "docker inspect --format" in command:
                if ".Config.Image" in command:
                    return Result("ghcr.io/yukkcat/chatgpt2api:latest")
                if "{{.Image}}" in command:
                    return Result("sha256:source-image")
                if ".NetworkSettings.Ports" in command:
                    return Result('{"80/tcp":[{"HostIp":"0.0.0.0","HostPort":"3000"}]}')
                if 'Destination \\"/app/data\\"' in command or 'Destination \"/app/data\"' in command:
                    return Result("/opt/chatgpt2api/data")
                if 'Destination \\"/app/config.json\\"' in command or 'Destination \"/app/config.json\"' in command:
                    return Result("/opt/chatgpt2api/config.json")
                return Result("||legacy-project|/opt/chatgpt2api|app")
            if "docker version" in command:
                return Result("27.1.0")
            if "docker compose version" in command:
                return Result("2.29.0")
            if "MemTotal" in command:
                return Result("4096")
            if "df -Pm" in command:
                return Result("50000")
            if "du -sm" in command:
                return Result("120")
            if "_NPROCESSORS" in command:
                return Result("4")
            if "ss -H" in command:
                return Result("0.0.0.0:22\n0.0.0.0:3000")
            return Result("ubuntu 24.04")

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.discovery._connect", fake_connect)
        result = await discover_environment(ExtensionDiscoveryRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
            credential=SSHCredential(password="secret"), trust_host_key=True,
        ))
        assert result["recommendation"] == "existing"
        assert result["instances"][0]["ownership"] == "compose"
        assert result["instances"][0]["clone_available"] is True
        assert result["instances"][0]["data_size_mb"] == 120
        assert result["instances"][0]["image"] == "ghcr.io/yukkcat/chatgpt2api@sha256:source-digest"
        assert result["instances"][0]["source_image_id"] == "sha256:source-image"
        assert result["instances"][0]["service_port"] == 3000
        assert result["instances"][0]["published_ports"] == [3000]
        assert result["instances"][0]["port_bindings_complete"] is True
        assert result["instances"][0]["port_bindings"] == [{
            "host_ip": "0.0.0.0", "host_port": 3000,
            "container_port": 80, "protocol": "tcp",
        }]
        assert result["environment"]["listening_ports"] == [22, 3000]
        assert result["environment"]["tcp_listeners"] == [
            {"protocol": "tcp", "host_port": 22},
            {"protocol": "tcp", "host_port": 3000},
        ]
        assert result["environment"]["listening_ports_probe"] == {
            "status": 0, "complete": True, "payload_present": True,
        }
        assert result["path_conditions_version"] == "phase4-v3"
        assert not any(token in command for command in commands for token in (" rm ", " stop ", " down", " up "))

    asyncio.run(run())
