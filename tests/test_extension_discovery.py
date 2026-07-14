import asyncio
import shlex

from extensions.discovery import discover_environment
from extensions.models import ExtensionDiscoveryRequest, ExtensionTarget, SSHCredential


def test_sudo_docker_command_preserves_go_template_quotes():
    command = 'docker inspect --format \'{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Source}}{{end}}{{end}}\' abc123'
    wrapped = f"sudo -n sh -lc {shlex.quote(command)}"

    assert shlex.split(wrapped)[-1] == command


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
        assert result["environment"]["listening_ports"] == [22, 3000]
        assert not any(token in command for command in commands for token in (" rm ", " stop ", " down", " up "))

    asyncio.run(run())
