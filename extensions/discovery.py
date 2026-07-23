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


async def _evaluate_path_conditions(
    connection,
    credential: SSHCredential,
    privileges: dict[str, Any],
    path_checks: dict[str, dict[str, Any]] | None,
    instances: list[dict[str, Any]],
    tcp_listeners: list[dict[str, Any]],
    listeners_complete: bool,
    disk_free_mb: int,
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
                and disk_free_mb >= required_mb
            )
        else:
            conditions[name] = False
    return conditions


async def discover_environment(
    request: ExtensionDiscoveryRequest,
    *,
    path_checks: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    connection, fingerprint = await _connect(request)
    if connection is None:
        raise PermissionError("需要先确认 VPS 主机指纹")
    try:
        privileges = await _diagnose_privileges(connection, request.credential)
        facts: dict[str, str] = {}
        fact_statuses: dict[str, int] = {}
        commands = {
            "os": "(. /etc/os-release 2>/dev/null && printf '%s %s' \"$ID\" \"$VERSION_ID\") || uname -s",
            "arch": "uname -m",
            "cpu": "getconf _NPROCESSORS_ONLN 2>/dev/null || nproc",
            "memory_mb": "awk '/MemTotal/{printf \"%d\", $2/1024}' /proc/meminfo",
            "disk_mb": "df -Pm \"$HOME\" | awk 'NR==2{print $4}'",
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
            _, image_digest = await _run_docker(
                connection,
                "docker image inspect --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{end}}' "
                f"{shlex.quote(image_id)} 2>/dev/null",
                request.credential,
                privileges,
            ) if image_id.startswith("sha256:") else (1, "")
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

        docker_ok = bool(_version_number(facts["docker"]))
        compose_ok = bool(_version_number(facts["compose"]))
        memory_mb = int(facts["memory_mb"] or 0)
        modes = [
            {
                "id": "compose", "name": "标准 Docker Compose", "available": docker_ok and compose_ok,
                "recommended": docker_ok and compose_ok, "summary": "隔离清晰、升级和回滚简单，适合绝大多数用户。",
            },
            {
                "id": "warp", "name": "WARP 稳定出口", "available": docker_ok and compose_ok and memory_mb >= 1800,
                "recommended": False, "summary": "附带 WARP、Privoxy 和 FlareSolverr，资源占用更高。",
            },
            {
                "id": "python", "name": "Python 源码模式", "available": False,
                "recommended": False, "summary": "适合开发调试；自动托管和回滚尚未开放。",
            },
        ]
        recommendation = "existing" if any(item["status"].lower().startswith("up") for item in instances) else "isolated"
        disk_free_mb = int(facts["disk_mb"] or 0)
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
                "os": facts["os"], "arch": facts["arch"], "cpu": int(facts["cpu"] or 0),
                "memory_mb": memory_mb, "disk_free_mb": disk_free_mb,
                "home_dir": facts["home"],
                "docker_version": facts["docker"], "compose_version": facts["compose"],
                "python_version": facts["python"], "uv_version": facts["uv"], "listening_ports": ports,
                "tcp_listeners": tcp_listeners,
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
