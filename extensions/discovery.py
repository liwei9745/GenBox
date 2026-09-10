"""Read-only VPS environment and chatgpt2api instance discovery."""
from __future__ import annotations

import ipaddress
import json
import posixpath
import re
import shlex
from typing import Any

from extensions.models import ExtensionDiscoveryRequest, SSHCredential
from extensions.orchestrator import _connect, _diagnose_privileges, _elevated_command
from extensions.read_only_discovery_plan import (
    ValidatedDiscoveryPlan,
    extend_read_only_discovery_plan,
)


async def _run(connection, command: str) -> tuple[int, str]:
    result = await connection.run(command, check=False)
    return result.exit_status, result.stdout.strip()


async def _run_docker(
    connection,
    command: str,
    credential: SSHCredential | str,
    privileges: dict[str, Any] | None = None,
) -> tuple[int, str]:
    status, output = await _run(connection, command)
    if status == 0:
        return status, output
    if privileges is not None:
        if not privileges.get("can_admin"):
            return status, output
        wrapped, input_data = _elevated_command(command, credential, privileges)
        result = await connection.run(wrapped, input=input_data, check=False)
        return result.exit_status, result.stdout.strip()

    # Compatibility for focused helper tests: the third argument is an
    # explicitly supplied sudo password, never an SSH-password fallback.
    password = credential if isinstance(credential, str) else credential.sudo_password
    probe = await connection.run("sudo -n true >/dev/null 2>&1", check=False)
    if probe.exit_status == 0:
        return await _run(connection, f"sudo -n sh -lc {shlex.quote(command)}")
    if not password:
        return status, output
    result = await connection.run(
        f"sudo -S -p '' sh -lc {shlex.quote(command)}",
        input=password + "\n",
        check=False,
    )
    return result.exit_status, result.stdout.strip()


def _version_number(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)+)", value or "")
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def _fact_text_output_valid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    return bool(
        value
        and len(value) <= 256
        and value.casefold() not in {"unknown", "unavailable", "none", "null"}
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    )


def _fact_version_output_valid(value: Any) -> bool:
    return _fact_text_output_valid(value) and re.search(r"\d", value) is not None


def _fact_positive_int_output_valid(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value > 0
    return isinstance(value, str) and re.fullmatch(r"[1-9]\d*", value.strip()) is not None


def _fact_positive_int(value: Any) -> int | None:
    if not _fact_positive_int_output_valid(value):
        return None
    return value if isinstance(value, int) else int(value.strip())


def _fact_text(value: Any) -> str | None:
    return value.strip() if _fact_text_output_valid(value) else None


def _fact_version(value: Any) -> str | None:
    return value.strip() if _fact_version_output_valid(value) else None


def _capability_state(status: Any, value: Any) -> bool | None:
    """Return true only for an observed version; failed probes stay unknown."""
    if status == 0 and _fact_version_output_valid(value):
        return True
    return None


def _parse_published_ports(value: str) -> list[int]:
    try:
        bindings = json.loads(value or "{}")
    except (TypeError, ValueError):
        return []
    if not isinstance(bindings, dict):
        return []
    ports: set[int] = set()
    for items in bindings.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                port = int(item.get("HostPort") or 0)
            except (TypeError, ValueError):
                continue
            if 1 <= port <= 65535:
                ports.add(port)
    return sorted(ports)


def _parse_canonical_port_bindings(value: str) -> tuple[list[dict[str, Any]], bool]:
    if not isinstance(value, str) or not value.strip():
        return [], False
    try:
        raw_bindings = json.loads(value)
    except (TypeError, ValueError):
        return [], False
    if not isinstance(raw_bindings, dict):
        return [], False
    canonical: list[tuple[str, int, int, str]] = []
    for container_identity, bindings in raw_bindings.items():
        match = re.fullmatch(r"(\d{1,5})/([A-Za-z0-9]+)", str(container_identity or ""))
        if not match:
            return [], False
        container_port = int(match.group(1))
        protocol = match.group(2).lower()
        if not 1 <= container_port <= 65535 or protocol not in {"tcp", "udp", "sctp"}:
            return [], False
        if not isinstance(bindings, list) or not bindings:
            return [], False
        for binding in bindings:
            if not isinstance(binding, dict):
                return [], False
            host_ip = str(binding.get("HostIp") or "").strip()
            if host_ip.startswith("[") and host_ip.endswith("]"):
                host_ip = host_ip[1:-1]
            raw_host_port = binding.get("HostPort")
            if isinstance(raw_host_port, bool):
                return [], False
            try:
                host_ip = ipaddress.ip_address(host_ip).compressed
                host_port = int(raw_host_port or 0)
            except (TypeError, ValueError):
                return [], False
            if not 1 <= host_port <= 65535:
                return [], False
            canonical.append((host_ip, host_port, container_port, protocol))
    return [
        {
            "host_ip": host_ip,
            "host_port": host_port,
            "container_port": container_port,
            "protocol": protocol,
        }
        for host_ip, host_port, container_port, protocol in sorted(canonical)
    ], True


def _listener_port(value: str) -> int | None:
    token = str(value or "").strip().rstrip(",")
    if not token or ":" not in token:
        return None
    port_text = token.rsplit(":", 1)[-1]
    if not port_text.isdigit():
        return None
    port = int(port_text)
    return port if 1 <= port <= 65535 else None


def _parse_canonical_tcp_listeners(status: int, value: str) -> tuple[list[dict[str, Any]], bool]:
    if status != 0 or not isinstance(value, str):
        return [], False
    raw_lines = value.splitlines()
    framed = bool(raw_lines and raw_lines[0].strip() == "GENBOX_TCP_LISTENERS_V1")
    if framed:
        raw_lines = raw_lines[1:]
    elif not any(line.strip() for line in raw_lines):
        return [], False
    listeners: list[dict[str, Any]] = []
    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith(("active internet connections", "proto ", "state ", "netid ")):
            continue
        parts = line.split()
        candidates = [line] if len(parts) == 1 else parts[3:5]
        port = None
        for candidate in candidates:
            port = _listener_port(candidate)
            if port is not None:
                break
        if port is None:
            return [], False
        listeners.append({"protocol": "tcp", "host_port": port})
    listeners.sort(key=lambda item: item["host_port"])
    return listeners, True


def _parse_listening_ports(status: int, value: str) -> tuple[list[int], bool]:
    listeners, complete = _parse_canonical_tcp_listeners(status, value)
    return sorted({item["host_port"] for item in listeners}), complete


def _normalized_remote_path(value: Any) -> str:
    raw = str(value or "").strip()
    return posixpath.normpath(raw) if raw.startswith("/") else ""


def _paths_overlap(first: Any, second: Any) -> bool:
    left = _normalized_remote_path(first)
    right = _normalized_remote_path(second)
    if not left or not right:
        return False
    return left == right or left.startswith(right.rstrip("/") + "/") or right.startswith(left.rstrip("/") + "/")


class ApprovedReadOnlyCommandError(PermissionError):
    """Raised locally before an unapproved SSH command can be sent."""


class _ApprovedReadOnlyConnection:
    """Bind the legacy discovery implementation to a validated operation plan.

    `docker_ps` is the only bootstrap operation. Its structured output may add
    narrowly validated operations for matching containers; every other command
    must already map to one of those approved operations.
    """

    _SYSTEM_SUMMARY_OPERATIONS = {
        "id -u": "identity",
        "(. /etc/os-release 2>/dev/null && printf '%s %s' \"$ID\" \"$VERSION_ID\") || uname -s": "os_release",
        "uname -m": "cpu_architecture",
        "getconf _NPROCESSORS_ONLN 2>/dev/null || nproc": "cpu_count",
        "awk '/MemTotal/{printf \"%d\", $2/1024}' /proc/meminfo": "memory_summary",
        "printf %s \"$HOME\"": "home_directory",
        "python3 --version 2>/dev/null": "python_version",
        "uv --version 2>/dev/null": "uv_version",
    }

    def __init__(self, connection: Any, plan: ValidatedDiscoveryPlan):
        self._connection = connection
        self._plan = plan
        self._containers: set[str] = set()
        self._mount_paths: set[str] = set()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def _contains(self, operation: dict[str, str]) -> bool:
        return operation in self._plan.operations

    def _extend(self, operations: list[dict[str, str]]) -> None:
        additions = [operation for operation in operations if not self._contains(operation)]
        if additions:
            self._plan = extend_read_only_discovery_plan(self._plan, additions)

    @staticmethod
    def _container_from_command(command: str) -> str:
        try:
            tokens = shlex.split(command)
        except ValueError:
            return ""
        return tokens[-2] if len(tokens) >= 2 and tokens[-1] == "2>/dev/null" else (tokens[-1] if tokens else "")

    def _operations_for(self, command: str) -> list[dict[str, str]]:
        if command in self._SYSTEM_SUMMARY_OPERATIONS:
            return [{"id": self._SYSTEM_SUMMARY_OPERATIONS[command]}]
        if command == "df -Pm / | awk 'NR==2{print $4}'":
            return [{"id": "capacity", "path": "/"}]
        if command == "docker version --format '{{.Server.Version}}' 2>/dev/null":
            return [{"id": "docker_version"}]
        if command == "docker compose version --short 2>/dev/null":
            return [{"id": "compose_version"}]
        if command == "docker ps -a --no-trunc --format '{{json .}}' 2>/dev/null":
            return [{"id": "docker_ps"}]
        if command == "docker compose ls --format json 2>/dev/null":
            return [{"id": "compose_ls"}]
        if command.startswith("if output=$(ss -H -ltn 2>/dev/null)"):
            return [{"id": "listening_ports"}]
        if command.startswith("docker inspect --format"):
            container = self._container_from_command(command)
            if container not in self._containers:
                return []
            if ".Config.Labels" in command:
                return [
                    {"id": "container_label", "container": container, "label": label}
                    for label in (
                        "com.genbox.managed",
                        "com.genbox.instance",
                        "com.docker.compose.project",
                        "com.docker.compose.project.working_dir",
                        "com.docker.compose.service",
                    )
                ]
            if ".Mounts" in command:
                return [{"id": "container_mounts", "container": container}]
            return [{"id": "container_summary", "container": container}]
        if command.startswith("du -sm "):
            try:
                path = shlex.split(command)[2]
            except (IndexError, ValueError):
                return []
            return [{"id": "directory_size", "path": path}] if path in self._mount_paths else []
        return []

    def _learn(self, command: str, stdout: str) -> None:
        if command == "docker ps -a --no-trunc --format '{{json .}}' 2>/dev/null":
            discovered: list[dict[str, str]] = []
            for line in stdout.splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                container = str(item.get("ID") or "")
                image = str(item.get("Image") or "")
                name = str(item.get("Names") or "")
                if not container or "chatgpt2api" not in f"{image} {name}".lower():
                    continue
                self._containers.add(container)
                discovered.extend([
                    {"id": "container_summary", "container": container},
                    {"id": "container_mounts", "container": container},
                ])
                discovered.extend(
                    {"id": "container_label", "container": container, "label": label}
                    for label in (
                        "com.genbox.managed",
                        "com.genbox.instance",
                        "com.docker.compose.project",
                        "com.docker.compose.project.working_dir",
                        "com.docker.compose.service",
                    )
                )
            self._extend(discovered)
        elif command.startswith("docker inspect --format") and ".Mounts" in command:
            path = stdout.strip()
            if path.startswith("/"):
                try:
                    self._extend([{"id": "directory_size", "path": path}])
                except ValueError:
                    return
                self._mount_paths.add(path)

    async def run(self, command: str, **kwargs: Any) -> Any:
        operations = self._operations_for(command)
        if not operations or not all(self._contains(operation) for operation in operations):
            raise ApprovedReadOnlyCommandError("unapproved_read_only_discovery_operation")
        result = await self._connection.run(command, **kwargs)
        self._learn(command, str(getattr(result, "stdout", "") or ""))
        return result


async def _evaluate_path_conditions(
    connection,
    credential: SSHCredential,
    privileges: dict[str, Any],
    path_checks: dict[str, dict[str, Any]] | None,
    instances: list[dict[str, Any]],
    tcp_listeners: list[dict[str, Any]],
    listeners_complete: bool,
    disk_free_mb: int | None,
) -> dict[str, bool]:
    conditions: dict[str, bool] = {}
    for name, check in (path_checks or {}).items():
        if not isinstance(name, str) or not isinstance(check, dict):
            conditions[str(name)] = False
            continue
        kind = str(check.get("kind") or "")
        path = _normalized_remote_path(check.get("path"))
        if kind in {"absent", "directory", "file", "claimable_parent"}:
            if not path:
                conditions[name] = False
                continue
            if kind == "claimable_parent":
                command = (
                    f"candidate={shlex.quote(path)}; "
                    "while test ! -e \"$candidate\"; do next=$(dirname \"$candidate\"); "
                    "test \"$next\" != \"$candidate\" || break; candidate=$next; done; "
                    "test -d \"$candidate\" && test -w \"$candidate\""
                )
            else:
                predicate = {"absent": "! -e", "directory": "-d", "file": "-f"}[kind]
                command = f"test {predicate} {shlex.quote(path)}"
            if kind in {"absent", "claimable_parent"}:
                status, _ = await _run(connection, command)
            else:
                status, _ = await _run_docker(connection, command, credential, privileges)
            conditions[name] = status == 0
            continue
        if kind == "data_nonoverlap":
            observed_paths = [
                item.get(field)
                for item in instances
                for field in ("working_dir", "data_dir", "config_file")
            ]
            conditions[name] = bool(path) and not any(_paths_overlap(path, observed) for observed in observed_paths)
        elif kind == "compose_nonoverlap":
            compose_project = str(check.get("compose_project") or "").strip().casefold()
            conditions[name] = bool(compose_project) and not any(
                str(item.get("compose_project") or "").strip().casefold() == compose_project
                for item in instances
            )
        elif kind == "tcp_port_unoccupied":
            port = check.get("port")
            conditions[name] = (
                listeners_complete
                and isinstance(port, int)
                and not isinstance(port, bool)
                and not any(item.get("host_port") == port for item in tcp_listeners)
            )
        elif kind in {"instance_present", "instance_identity_matches"}:
            instance_id = str(check.get("instance_id") or "")
            instance = next((item for item in instances if item.get("id") == instance_id), None)
            if kind == "instance_present":
                conditions[name] = instance is not None
            else:
                conditions[name] = bool(
                    instance
                    and instance.get("service_port") == check.get("service_port")
                    and instance.get("container_id") == check.get("container_id")
                )
        elif kind == "clone_scope_allowed":
            conditions[name] = check.get("allowed") is True
        elif kind == "source_target_paths_nonoverlap":
            source_id = str(check.get("source_id") or "")
            source = next((item for item in instances if item.get("id") == source_id), None)
            source_paths = [source.get(field) for field in ("working_dir", "data_dir", "config_file")] if source else []
            conditions[name] = bool(source and path) and not any(_paths_overlap(path, observed) for observed in source_paths)
        elif kind == "capacity_sufficient":
            required_mb = check.get("required_mb")
            conditions[name] = (
                isinstance(required_mb, int)
                and not isinstance(required_mb, bool)
                and disk_free_mb is not None
                and disk_free_mb >= required_mb
            )
        else:
            conditions[name] = False
    return conditions


async def discover_environment(
    request: ExtensionDiscoveryRequest,
    *,
    path_checks: dict[str, dict[str, Any]] | None = None,
    approved_plan: ValidatedDiscoveryPlan | None = None,
) -> dict[str, Any]:
    connection, fingerprint = await _connect(request)
    if connection is None:
        raise PermissionError("需要先确认 VPS 主机指纹")
    try:
        if approved_plan is None:
            privileges = await _diagnose_privileges(connection, request.credential)
        else:
            connection = _ApprovedReadOnlyConnection(connection, approved_plan)
            user_id = (await connection.run("id -u", check=True)).stdout.strip()
            privileges = {
                "auth_kind": "password" if request.credential.password else "private_key",
                "elevation_contract": request.credential.elevation,
                "is_root": user_id == "0",
                "docker_access": False,
                "elevated_docker_access": False,
                "passwordless_sudo": False,
                "password_sudo": False,
                "sudo_password_supplied": False,
                "can_admin": user_id == "0",
                "can_deploy": False,
                "diagnostic_code": "read_only_discovery",
            }
        facts: dict[str, str] = {}
        fact_statuses: dict[str, int] = {}
        commands = {
            "os": "(. /etc/os-release 2>/dev/null && printf '%s %s' \"$ID\" \"$VERSION_ID\") || uname -s",
            "arch": "uname -m",
            "cpu": "getconf _NPROCESSORS_ONLN 2>/dev/null || nproc",
            "memory_mb": "awk '/MemTotal/{printf \"%d\", $2/1024}' /proc/meminfo",
            "disk_mb": "df -Pm / | awk 'NR==2{print $4}'",
            "home": "printf %s \"$HOME\"",
            "docker": "docker version --format '{{.Server.Version}}' 2>/dev/null",
            "compose": "docker compose version --short 2>/dev/null",
            "python": "python3 --version 2>/dev/null",
            "uv": "uv --version 2>/dev/null",
            "ports": (
                "if output=$(ss -H -ltn 2>/dev/null); then printf 'GENBOX_TCP_LISTENERS_V1\\n%s\\n' \"$output\"; "
                "elif output=$(netstat -ltn 2>/dev/null); then printf 'GENBOX_TCP_LISTENERS_V1\\n%s\\n' \"$output\"; "
                "else exit 1; fi"
            ),
            "containers": "docker ps -a --no-trunc --format '{{json .}}' 2>/dev/null",
        }
        for key, command in commands.items():
            runner = _run_docker if key in {"docker", "compose", "containers"} else _run
            if runner is _run_docker:
                fact_statuses[key], facts[key] = await runner(connection, command, request.credential, privileges)
            else:
                fact_statuses[key], facts[key] = await runner(connection, command)

        tcp_listeners, ports_complete = _parse_canonical_tcp_listeners(
            fact_statuses["ports"], facts["ports"]
        )
        ports = sorted({item["host_port"] for item in tcp_listeners})
        instances = []
        for line in facts["containers"].splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            image = str(item.get("Image") or "")
            names = str(item.get("Names") or "")
            if "chatgpt2api" not in f"{image} {names}".lower():
                continue
            container_id = str(item.get("ID") or "")
            _, labels = await _run_docker(connection, (
                f"docker inspect --format '{{{{index .Config.Labels \"com.genbox.managed\"}}}}|"
                f"{{{{index .Config.Labels \"com.genbox.instance\"}}}}|"
                f"{{{{index .Config.Labels \"com.docker.compose.project\"}}}}|"
                f"{{{{index .Config.Labels \"com.docker.compose.project.working_dir\"}}}}|"
                f"{{{{index .Config.Labels \"com.docker.compose.service\"}}}}' {container_id} 2>/dev/null"
            ), request.credential, privileges)
            managed, instance_id, compose_project, working_dir, compose_service = (labels.split("|") + ["", "", "", "", ""])[:5]
            is_app = compose_service == "app" or "yukkcat/chatgpt2api" in image.lower()
            if not is_app:
                continue
            _, configured_image = await _run_docker(
                connection,
                f"docker inspect --format '{{{{.Config.Image}}}}' {container_id} 2>/dev/null",
                request.credential,
                privileges,
            )
            _, image_id = await _run_docker(
                connection,
                f"docker inspect --format '{{{{.Image}}}}' {container_id} 2>/dev/null",
                request.credential,
                privileges,
            )
            if approved_plan is None and image_id.startswith("sha256:"):
                _, image_digest = await _run_docker(
                    connection,
                    "docker image inspect --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{end}}' "
                    f"{shlex.quote(image_id)} 2>/dev/null",
                    request.credential,
                    privileges,
                )
            else:
                image_digest = ""
            source_image = image_digest or (
                f"genbox-chatgpt2api-source:{container_id[:12]}"
                if image_id.startswith("sha256:") else configured_image or image
            )
            structured_port_status, structured_ports = await _run_docker(
                connection,
                f"docker inspect --format '{{{{json .NetworkSettings.Ports}}}}' {shlex.quote(container_id)} 2>/dev/null",
                request.credential,
                privileges,
            )
            published_ports = _parse_published_ports(structured_ports)
            port_bindings, port_bindings_complete = _parse_canonical_port_bindings(structured_ports)
            port_bindings_complete = structured_port_status == 0 and port_bindings_complete
            _, data_dir = await _run_docker(connection, (
                f"docker inspect --format '{{{{range .Mounts}}}}{{{{if eq .Destination \"/app/data\"}}}}"
                f"{{{{.Source}}}}{{{{end}}}}{{{{end}}}}' {container_id} 2>/dev/null"
            ), request.credential, privileges)
            _, config_file = await _run_docker(connection, (
                f"docker inspect --format '{{{{range .Mounts}}}}{{{{if eq .Destination \"/app/config.json\"}}}}"
                f"{{{{.Source}}}}{{{{end}}}}{{{{end}}}}' {container_id} 2>/dev/null"
            ), request.credential, privileges)
            data_size_mb = 0
            if data_dir.startswith("/"):
                size_status, size_output = await _run_docker(
                    connection,
                    f"du -sm {shlex.quote(data_dir)} 2>/dev/null",
                    request.credential,
                    privileges,
                )
                size_match = re.match(r"^(\d+)(?:\s|$)", size_output)
                if size_status == 0 and size_match:
                    data_size_mb = int(size_match.group(1))
                else:
                    data_size_mb = None
            normalized_id = re.sub(r"[^a-z0-9-]+", "-", (instance_id or names).lower()).strip("-")[:40]
            if len(normalized_id) < 2:
                normalized_id = f"instance-{container_id[:8]}"
            instances.append({
                "id": normalized_id,
                "container_id": container_id[:12],
                "name": names,
                "image": source_image,
                "source_image_id": image_id,
                "status": str(item.get("Status") or ""),
                "ports": str(item.get("Ports") or ""),
                "published_ports": published_ports,
                "service_port": published_ports[0] if len(published_ports) == 1 else None,
                "port_bindings": port_bindings,
                "port_bindings_complete": port_bindings_complete,
                "compose_project": compose_project,
                "compose_service": compose_service,
                "working_dir": working_dir,
                "data_dir": data_dir,
                "config_file": config_file,
                "data_size_mb": data_size_mb,
                "clone_available": bool(
                    data_dir.startswith("/") and config_file.startswith("/") and data_size_mb is not None
                ),
                "managed": managed.lower() == "true",
                "ownership": "managed" if managed.lower() == "true" else ("compose" if compose_project else "unmanaged"),
            })

        os_value = _fact_text(facts["os"]) if fact_statuses["os"] == 0 else None
        arch_value = _fact_text(facts["arch"]) if fact_statuses["arch"] == 0 else None
        cpu_value = _fact_positive_int(facts["cpu"]) if fact_statuses["cpu"] == 0 else None
        memory_mb = _fact_positive_int(facts["memory_mb"]) if fact_statuses["memory_mb"] == 0 else None
        disk_free_mb = _fact_positive_int(facts["disk_mb"]) if fact_statuses["disk_mb"] == 0 else None
        docker_value = _fact_version(facts["docker"]) if fact_statuses["docker"] == 0 else None
        compose_value = _fact_version(facts["compose"]) if fact_statuses["compose"] == 0 else None
        python_value = _fact_version(facts["python"]) if fact_statuses["python"] == 0 else None
        uv_value = _fact_version(facts["uv"]) if fact_statuses["uv"] == 0 else None
        docker_ok = _capability_state(fact_statuses["docker"], facts["docker"])
        compose_ok = _capability_state(fact_statuses["compose"], facts["compose"])
        if approved_plan is not None:
            privileges["docker_access"] = fact_statuses["docker"] == 0 and docker_value is not None
            privileges["can_deploy"] = bool(
                privileges["docker_access"]
                and (privileges["is_root"] or privileges["elevation_contract"] == "none")
            )
            privileges["diagnostic_code"] = (
                "read_only_direct_docker" if privileges["can_deploy"] else "read_only_access_unverified"
            )
        modes = [
            {
                "id": "compose", "name": "标准 Docker Compose", "available": docker_ok and compose_ok,
                "recommended": docker_ok and compose_ok, "summary": "隔离清晰、升级和回滚简单，适合绝大多数用户。",
            },
            {
                "id": "warp", "name": "WARP 稳定出口", "available": (
                    docker_ok is True and compose_ok is True
                    and memory_mb is not None and memory_mb >= 1800
                ),
                "recommended": False, "summary": "附带 WARP、Privoxy 和 FlareSolverr，资源占用更高。",
            },
            {
                "id": "python", "name": "Python 源码模式", "available": False,
                "recommended": False, "summary": "适合开发调试；自动托管和回滚尚未开放。",
            },
        ]
        recommendation = "existing" if any(item["status"].lower().startswith("up") for item in instances) else "isolated"
        fact_probe_names = ("os", "arch", "cpu", "memory_mb", "disk_mb", "docker", "compose", "python", "uv")
        fact_probe_statuses = {key: fact_statuses[key] for key in fact_probe_names}
        fact_probe_output_validity = {
            "os": _fact_text_output_valid(facts["os"]),
            "arch": _fact_text_output_valid(facts["arch"]),
            "cpu": _fact_positive_int_output_valid(facts["cpu"]),
            "memory_mb": _fact_positive_int_output_valid(facts["memory_mb"]),
            "disk_mb": _fact_positive_int_output_valid(facts["disk_mb"]),
            "docker": _fact_version_output_valid(facts["docker"]),
            "compose": _fact_version_output_valid(facts["compose"]),
            "python": _fact_version_output_valid(facts["python"]),
            "uv": _fact_version_output_valid(facts["uv"]),
        }
        path_conditions = await _evaluate_path_conditions(
            connection,
            request.credential,
            privileges,
            path_checks,
            instances,
            tcp_listeners,
            ports_complete,
            disk_free_mb,
        )
        return {
            "ok": True,
            "host_key_algorithm": request.expected_host_key_algorithm or request.target.host_key_algorithm,
            "host_key": fingerprint,
            "privileges": privileges,
            "environment": {
                "os": os_value, "arch": arch_value, "cpu": cpu_value,
                "memory_mb": memory_mb, "disk_free_mb": disk_free_mb,
                "home_dir": facts["home"],
                "docker_version": docker_value, "compose_version": compose_value,
                "python_version": python_value, "uv_version": uv_value, "listening_ports": ports,
                "tcp_listeners": tcp_listeners,
                "fact_probe_statuses": fact_probe_statuses,
                "fact_probe_output_validity": fact_probe_output_validity,
                "fact_probe_complete": all(
                    status == 0 and fact_probe_output_validity[key]
                    for key, status in fact_probe_statuses.items()
                ),
                "listening_ports_probe": {
                    "status": fact_statuses["ports"],
                    "complete": ports_complete,
                    "payload_present": ports_complete,
                },
            },
            "instances": instances,
            "path_conditions_version": "phase4-v3",
            "path_conditions": path_conditions,
            "deployment_modes": modes,
            "recommendation": recommendation,
            "warnings": (["检测到已有实例，默认不执行任何修改。"] if instances else []),
        }
    finally:
        connection.close()
        await connection.wait_closed()
