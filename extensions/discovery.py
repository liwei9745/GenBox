"""Read-only VPS environment and chatgpt2api instance discovery."""
from __future__ import annotations

import json
import re
import shlex
from typing import Any

from extensions.models import ExtensionDiscoveryRequest
from extensions.orchestrator import _connect


async def _run(connection, command: str) -> tuple[int, str]:
    result = await connection.run(command, check=False)
    return result.exit_status, result.stdout.strip()


async def _run_docker(connection, command: str, password: str) -> tuple[int, str]:
    status, output = await _run(connection, command)
    if status == 0:
        return status, output
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


async def discover_environment(request: ExtensionDiscoveryRequest) -> dict[str, Any]:
    connection, fingerprint = await _connect(request)
    if connection is None:
        raise PermissionError("需要先确认 VPS 主机指纹")
    try:
        facts: dict[str, str] = {}
        commands = {
            "os": "(. /etc/os-release 2>/dev/null && printf '%s %s' \"$ID\" \"$VERSION_ID\") || uname -s",
            "arch": "uname -m",
            "cpu": "getconf _NPROCESSORS_ONLN 2>/dev/null || nproc",
            "memory_mb": "awk '/MemTotal/{printf \"%d\", $2/1024}' /proc/meminfo",
            "disk_mb": "df -Pm \"$HOME\" | awk 'NR==2{print $4}'",
            "docker": "docker version --format '{{.Server.Version}}' 2>/dev/null",
            "compose": "docker compose version --short 2>/dev/null",
            "python": "python3 --version 2>/dev/null",
            "uv": "uv --version 2>/dev/null",
            "ports": "(ss -H -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | awk '{print $4}'",
            "containers": "docker ps -a --no-trunc --format '{{json .}}' 2>/dev/null",
        }
        sudo_password = request.credential.sudo_password or request.credential.password
        for key, command in commands.items():
            runner = _run_docker if key in {"docker", "compose", "containers"} else _run
            if runner is _run_docker:
                _, facts[key] = await runner(connection, command, sudo_password)
            else:
                _, facts[key] = await runner(connection, command)

        ports = sorted({
            int(match.group(1))
            for line in facts["ports"].splitlines()
            if (match := re.search(r":(\d+)$", line.strip()))
        })
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
            ), sudo_password)
            managed, instance_id, compose_project, working_dir, compose_service = (labels.split("|") + ["", "", "", "", ""])[:5]
            is_app = compose_service == "app" or "yukkcat/chatgpt2api" in image.lower()
            if not is_app:
                continue
            _, configured_image = await _run_docker(
                connection,
                f"docker inspect --format '{{{{.Config.Image}}}}' {container_id} 2>/dev/null",
                sudo_password,
            )
            _, image_id = await _run_docker(
                connection,
                f"docker inspect --format '{{{{.Image}}}}' {container_id} 2>/dev/null",
                sudo_password,
            )
            _, image_digest = await _run_docker(
                connection,
                "docker image inspect --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{end}}' "
                f"{shlex.quote(image_id)} 2>/dev/null",
                sudo_password,
            ) if image_id.startswith("sha256:") else (1, "")
            source_image = image_digest or (
                f"genbox-chatgpt2api-source:{container_id[:12]}"
                if image_id.startswith("sha256:") else configured_image or image
            )
            _, data_dir = await _run_docker(connection, (
                f"docker inspect --format '{{{{range .Mounts}}}}{{{{if eq .Destination \"/app/data\"}}}}"
                f"{{{{.Source}}}}{{{{end}}}}{{{{end}}}}' {container_id} 2>/dev/null"
            ), sudo_password)
            _, config_file = await _run_docker(connection, (
                f"docker inspect --format '{{{{range .Mounts}}}}{{{{if eq .Destination \"/app/config.json\"}}}}"
                f"{{{{.Source}}}}{{{{end}}}}{{{{end}}}}' {container_id} 2>/dev/null"
            ), sudo_password)
            data_size_mb = 0
            if data_dir.startswith("/"):
                size_status, size_output = await _run_docker(
                    connection,
                    f"du -sm {shlex.quote(data_dir)} 2>/dev/null",
                    sudo_password,
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
        return {
            "ok": True,
            "host_key": fingerprint,
            "environment": {
                "os": facts["os"], "arch": facts["arch"], "cpu": int(facts["cpu"] or 0),
                "memory_mb": memory_mb, "disk_free_mb": int(facts["disk_mb"] or 0),
                "docker_version": facts["docker"], "compose_version": facts["compose"],
                "python_version": facts["python"], "uv_version": facts["uv"], "listening_ports": ports,
            },
            "instances": instances,
            "deployment_modes": modes,
            "recommendation": recommendation,
            "warnings": (["检测到已有实例，默认不执行任何修改。"] if instances else []),
        }
    finally:
        connection.close()
        await connection.wait_closed()
