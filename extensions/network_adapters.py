"""Fixed network connector plans for supported overlay/tunnel providers."""
import asyncio
import ipaddress
import json
import posixpath
import re
import shlex
import stat
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

import asyncssh
from pydantic import SecretStr

from extensions.models import NetworkConnectRequest
from extensions.orchestrator import (
    SSHAuthenticationError,
    SSHConnectionError,
    _connect,
    _diagnose_privileges,
    _elevated_command,
)
from extensions.local_tailscale import enable_genbox_serve, local_status, ping_peer
from extensions.store import upsert_target


NETWORK_STEPS = [
    ("local_detect", "检查这台电脑"),
    ("remote_connect", "连接远程 VPS"),
    ("remote_detect", "检查 VPS 环境"),
    ("remote_install", "安装网络工具"),
    ("remote_enroll", "加入同一个网络"),
    ("remote_network_detect", "确认 VPS Tailscale 地址"),
    ("peer_verify", "检查两台设备互通"),
    ("http_probe", "检查 VPS 能否访问 GenBox"),
    ("destination_ready", "保存可用访问地址"),
]

RECOVERY_BY_PHASE = {
    "local_detect": ("TAILSCALE_LOCAL_OFFLINE", "请先登录本机 Tailscale，再重新开始连接。"),
    "remote_connect": ("SSH_CONNECTION_FAILED", "确认隔离开发 VPS 的地址、SSH 凭证和主机指纹后重试。"),
    "remote_detect": ("REMOTE_NETWORK_DETECT_FAILED", "确认隔离开发 VPS 在线且已安装 Tailscale 后重试。"),
    "remote_install": ("REMOTE_NETWORK_INSTALL_FAILED", "检查隔离开发 VPS 的网络和 sudo 权限后重试。"),
    "remote_enroll": ("REMOTE_NETWORK_ENROLL_FAILED", "重新生成一次性 Tailscale 授权信息后重试。"),
    "remote_network_detect": ("REMOTE_TAILSCALE_ADDRESS_INVALID", "确认 VPS 已成功加入 Tailnet 并获得有效的 Tailscale IPv4 地址后重试。"),
    "peer_verify": ("TAILSCALE_PEER_UNREACHABLE", "确认两台设备在线且位于同一 Tailnet 后重试。"),
    "http_probe": ("GENBOX_HTTP_PROBE_FAILED", "确认 Tailscale Serve 与 GenBox 应用均在运行后重试。"),
    "destination_ready": ("DESTINATION_SAVE_FAILED", "确认目标地址有效后重新验证；原有已验证地址不会被替换。"),
}

REMOTE_OS_RELEASE_COMMAND = "cat /etc/os-release"
REMOTE_HOME_COMMAND = "printf %s \"$HOME\""
TAILSCALE_PRESENCE_COMMAND = "command -v tailscale >/dev/null 2>&1"
TAILSCALE_SERVICE_ACTIVE_COMMAND = "systemctl is-active --quiet tailscaled"
TAILSCALE_SERVICE_COMMAND = "systemctl enable --now tailscaled"
TAILSCALE_STATUS_COMMAND = "tailscale status --json"
TAILSCALE_KEYRING_PATH = "/usr/share/keyrings/tailscale-archive-keyring.gpg"
TAILSCALE_REPOSITORY_PATH = "/etc/apt/sources.list.d/tailscale.list"
TAILSCALE_APT_INSTALL_COMMAND = "DEBIAN_FRONTEND=noninteractive apt-get install -y tailscale"
AUTH_CLEANUP_SFTP_TIMEOUT = 10
AUTH_CLEANUP_COMMAND_TIMEOUT = 15
AUTH_CLEANUP_RECONNECT_TIMEOUT = 20
AUTH_CLEANUP_TOTAL_TIMEOUT = 90
TAILSCALE_SUPPORTED_RELEASES = {
    ("ubuntu", "focal"),
    ("ubuntu", "jammy"),
    ("ubuntu", "noble"),
    ("debian", "bullseye"),
    ("debian", "bookworm"),
    ("debian", "trixie"),
}


class NetworkTaskError(RuntimeError):
    def __init__(self, message: str, *, recovery_code: str, recovery_action: str):
        super().__init__(message)
        self.recovery_code = recovery_code
        self.recovery_action = recovery_action


def parse_remote_os_release(output: str) -> tuple[str, str]:
    """Return a validated distro ID and codename without evaluating shell data."""
    values: dict[str, str] = {}
    for line in str(output or "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'").lower()
        if key in {"ID", "VERSION_CODENAME"} and re.fullmatch(r"[a-z0-9._-]{1,40}", value):
            values[key] = value
    release = (values.get("ID", ""), values.get("VERSION_CODENAME", ""))
    if release not in TAILSCALE_SUPPORTED_RELEASES:
        raise NetworkTaskError(
            "当前 VPS 系统暂不支持自动安装 Tailscale",
            recovery_code="REMOTE_OS_UNSUPPORTED",
            recovery_action="当前自动安装只支持 Ubuntu 20.04/22.04/24.04 和 Debian 11/12/13；可先人工安装后改用仅检测模式。",
        )
    return release


def tailscale_repository_urls(os_id: str, codename: str) -> tuple[str, str]:
    release = (str(os_id), str(codename))
    if release not in TAILSCALE_SUPPORTED_RELEASES:
        raise ValueError("unsupported Tailscale repository release")
    base = f"https://pkgs.tailscale.com/stable/{os_id}/{codename}"
    return f"{base}.noarmor.gpg", f"{base}.tailscale-keyring.list"


def tailscale_install_plan(os_id: str, codename: str, nonce: str) -> dict[str, str]:
    """Build the server-owned apt plan. No value comes from browser shell input."""
    if not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("invalid install nonce")
    keyring_url, repository_url = tailscale_repository_urls(os_id, codename)
    keyring_tmp = f"/tmp/.genbox-tailscale-keyring-{nonce}"
    repository_tmp = f"/tmp/.genbox-tailscale-repository-{nonce}"
    curl_prefix = "curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 --max-time 60 --max-filesize 1048576"
    return {
        "keyring_tmp": keyring_tmp,
        "repository_tmp": repository_tmp,
        "prepare_keyring_dir": "install -d -m 0755 /usr/share/keyrings",
        "download_keyring": f"{curl_prefix} --output {shlex.quote(keyring_tmp)} {shlex.quote(keyring_url)}",
        "download_repository": f"{curl_prefix} --output {shlex.quote(repository_tmp)} {shlex.quote(repository_url)}",
        "check_keyring_conflict": f"test ! -e {shlex.quote(TAILSCALE_KEYRING_PATH)} || cmp -s {shlex.quote(keyring_tmp)} {shlex.quote(TAILSCALE_KEYRING_PATH)}",
        "check_repository_conflict": f"test ! -e {shlex.quote(TAILSCALE_REPOSITORY_PATH)} || cmp -s {shlex.quote(repository_tmp)} {shlex.quote(TAILSCALE_REPOSITORY_PATH)}",
        "install_keyring": f"install -m 0644 {shlex.quote(keyring_tmp)} {shlex.quote(TAILSCALE_KEYRING_PATH)}",
        "install_repository": f"install -m 0644 {shlex.quote(repository_tmp)} {shlex.quote(TAILSCALE_REPOSITORY_PATH)}",
        "apt_update": "apt-get update",
        "apt_install": TAILSCALE_APT_INSTALL_COMMAND,
        "cleanup_downloads": f"rm -f -- {shlex.quote(keyring_tmp)} {shlex.quote(repository_tmp)}",
    }


def validate_tailscale_destination(
    url: str,
    *,
    address: str,
    dns_name: str,
    serve_port: int,
    app_port: int,
) -> str:
    """Return a canonical, non-secret Tailnet destination or raise ValueError."""
    if serve_port == app_port:
        raise ValueError("Tailscale Serve 端口不能与 GenBox 应用端口相同")
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise ValueError("GenBox 私网地址格式无效") from exc
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("GenBox 私网地址必须是不含凭证的 http Tailnet 地址")
    if parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("GenBox 私网地址不能包含路径、查询参数或片段")
    if parsed.port != serve_port:
        raise ValueError("GenBox 私网地址必须使用已验证的 Tailscale Serve 端口")

    try:
        expected = ipaddress.ip_address(address)
    except ValueError as exc:
        raise ValueError("本机 Tailscale 地址无效") from exc
    if expected.version != 4 or expected not in ipaddress.ip_network("100.64.0.0/10"):
        raise ValueError("本机地址不是有效的 Tailscale IPv4 地址")

    expected_dns = str(dns_name or "").rstrip(".").lower()
    if (
        len(expected_dns) > 253
        or not expected_dns.endswith(".ts.net")
        or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+ts\.net", expected_dns)
    ):
        raise ValueError("本机没有有效的 Tailscale MagicDNS 名称")

    host = parsed.hostname.rstrip(".").lower()
    if host != expected_dns:
        raise ValueError("GenBox 私网地址必须精确匹配已验证的本机 Tailscale MagicDNS 名称")
    return urlunsplit((parsed.scheme, f"{expected_dns}:{serve_port}", "", "", ""))


def inspect_tailscale_peer_address(output: str) -> tuple[str | None, dict, str | None]:
    """Inspect public Tailscale status without retaining its raw payload."""
    raw = str(output or "").strip()
    candidates: list[str] = []
    diagnostics = {
        "stdout_present": bool(raw),
        "json_parsed": False,
        "json_extracted": False,
        "json_type": "invalid",
        "backend_state": "unknown",
        "top_level_ips_present": False,
        "top_level_ip_count": 0,
        "self_ips_present": False,
        "self_ip_count": 0,
        "cgnat_candidate_count": 0,
    }
    payload = None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        parsed_json = False
        object_start = raw.find("{")
        if object_start >= 0:
            try:
                payload, _end = json.JSONDecoder().raw_decode(raw[object_start:])
            except (TypeError, ValueError):
                payload = None
            else:
                parsed_json = True
                diagnostics["json_extracted"] = object_start > 0
    else:
        parsed_json = True
    diagnostics["json_parsed"] = parsed_json
    if parsed_json:
        diagnostics["json_type"] = (
            "object" if isinstance(payload, dict)
            else "array" if isinstance(payload, list)
            else "null" if payload is None
            else "scalar"
        )
        if not isinstance(payload, dict):
            return None, diagnostics, "VPS Tailscale 状态 JSON 格式无效"
        backend_state = str(payload.get("BackendState") or "")
        diagnostics["backend_state"] = {
            "Running": "running",
            "NeedsLogin": "needs_login",
            "Starting": "starting",
            "Stopped": "stopped",
        }.get(backend_state, "missing" if not backend_state else "other")
        if backend_state != "Running":
            return None, diagnostics, "VPS Tailscale 尚未进入 Running 状态"
        top_level_values = payload.get("TailscaleIPs")
        diagnostics["top_level_ips_present"] = isinstance(top_level_values, list)
        diagnostics["top_level_ip_count"] = len(top_level_values) if isinstance(top_level_values, list) else 0
        self_node = payload.get("Self") if isinstance(payload.get("Self"), dict) else {}
        self_values = self_node.get("TailscaleIPs")
        diagnostics["self_ips_present"] = isinstance(self_values, list)
        diagnostics["self_ip_count"] = len(self_values) if isinstance(self_values, list) else 0
        if isinstance(top_level_values, list):
            candidates.extend(str(value).strip() for value in top_level_values)
        if isinstance(self_values, list):
            candidates.extend(str(value).strip() for value in self_values)
    else:
        candidates.extend(token.strip("[](),;\"'") for token in raw.replace(",", " ").split())

    addresses = set()
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.version == 4 and address in ipaddress.ip_network("100.64.0.0/10"):
            addresses.add(str(address))
    diagnostics["cgnat_candidate_count"] = len(addresses)
    if len(addresses) != 1:
        return None, diagnostics, "VPS 未返回唯一有效的 Tailscale IPv4 地址"
    return next(iter(addresses)), diagnostics, None


def validate_tailscale_peer_address(output: str) -> str:
    address, _diagnostics, error = inspect_tailscale_peer_address(output)
    if error:
        raise ValueError(error)
    return str(address)


def is_genbox_setup_status(output: str) -> bool:
    try:
        payload = json.loads(output)
    except (TypeError, ValueError):
        return False
    return (
        isinstance(payload, dict)
        and payload.get("app_mode") in {"dev", "prod"}
        and all(isinstance(payload.get(key), bool) for key in (
            "auth_required", "needs_provider_setup", "has_configured_provider", "has_enabled_provider",
        ))
        and isinstance(payload.get("provider_count"), int)
        and not isinstance(payload.get("provider_count"), bool)
    )


def command_plan(request: NetworkConnectRequest) -> list[tuple[str, str]]:
    if request.provider == "tailscale":
        plan = [
            ("remote_detect", REMOTE_OS_RELEASE_COMMAND),
            ("remote_detect", TAILSCALE_PRESENCE_COMMAND),
        ]
        if request.operation_mode == "auto":
            plan.extend([
                ("remote_install", "validated official Tailscale apt repository install"),
                ("remote_install", TAILSCALE_SERVICE_COMMAND),
                ("remote_enroll", "tailscale up --auth-key=file:<temporary-auth-file> --hostname=<validated-device-name> --timeout=60s"),
            ])
        plan.append(("remote_network_detect", TAILSCALE_STATUS_COMMAND))
        return plan
    raise ValueError("当前仅 Tailscale 已具备完整的安全验证链")


class NetworkTaskManager:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.runners: dict[str, asyncio.Task] = {}
        self.active: dict[tuple[str, str], str] = {}

    def create(self, request: NetworkConnectRequest) -> str:
        active_key = (request.target.id, request.provider)
        active_task_id = self.active.get(active_key)
        if active_task_id:
            active_state = self.tasks.get(active_task_id)
            if active_state and active_state.get("status") in {"queued", "running"}:
                return active_task_id
            self.active.pop(active_key, None)
        task_id = uuid.uuid4().hex[:12]
        self.tasks[task_id] = {
            "id": task_id,
            "status": "queued",
            "provider": request.provider,
            "progress": 0,
            "phase": "local_detect",
            "error": None,
            "failed_phase": None,
            "recovery_code": None,
            "recovery_action": None,
            "next_action": None,
            "result": None,
            "diagnostics": None,
            "steps": [{"id": key, "label": label, "status": "pending"} for key, label in NETWORK_STEPS],
            "logs": [],
        }
        self.active[active_key] = task_id
        self.runners[task_id] = asyncio.create_task(self._run(task_id, request))
        return task_id

    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    async def _run(self, task_id: str, request: NetworkConnectRequest) -> None:
        state = self.tasks[task_id]
        connection = None
        auth_sftp = None
        auth_path = ""
        auth_cleanup_reconnect_attempted = False
        active_index = 0
        active_key = (request.target.id, request.provider)
        enrollment_token = request.enrollment_token.get_secret_value()

        def update(index: int, status: str, message: str = ""):
            nonlocal active_index
            active_index = index
            state["phase"] = NETWORK_STEPS[index][0]
            state["steps"][index]["status"] = status
            state["progress"] = int(index / len(NETWORK_STEPS) * 100)
            if message:
                state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": message})

        def sanitized_error(exc: Exception) -> str:
            if isinstance(exc, (SSHAuthenticationError, SSHConnectionError)):
                return str(exc)[:240]
            return "此步骤未完成，原始错误已隐藏。请按恢复提示检查后再试。"

        def next_action_for(code: str) -> dict:
            if code in {"TAILSCALE_NOT_INSTALLED", "TAILSCALE_AUTH_KEY_REQUIRED", "TAILSCALE_AUTH_REJECTED"}:
                return {"type": "provide_secret", "label_key": "extensions.enter_auth_key", "handler": "network_retry", "mutates_target": True}
            if code == "GENBOX_HTTP_PROBE_FAILED":
                return {"type": "prepare_local_network", "label_key": "extensions.check_local_entry", "handler": "local_network", "mutates_target": False}
            if code in {"REMOTE_OS_UNSUPPORTED", "TAILSCALE_REPOSITORY_CONFLICT", "AUTH_FILE_CLEANUP_FAILED"}:
                return {"type": "manual_review", "label_key": "extensions.manual_check_required", "handler": "show_advanced", "mutates_target": False}
            return {"type": "retry", "label_key": "extensions.recheck_link", "handler": "network_retry", "mutates_target": code in {"TAILSCALE_REPOSITORY_SETUP_FAILED", "TAILSCALE_INSTALL_FAILED", "TAILSCALED_START_FAILED", "TAILSCALE_SERVICE_UNAVAILABLE"}}

        def pause_for_action(index: int, code: str, action: str, message: str) -> None:
            update(index, "needs_action", message)
            state["status"] = "needs_action"
            state["failed_phase"] = None
            state["recovery_code"] = code
            state["recovery_action"] = action
            state["next_action"] = next_action_for(code)
            state["error"] = None

        async def cleanup_auth_file() -> None:
            nonlocal auth_path, auth_sftp, auth_cleanup_reconnect_attempted
            if not auth_path or connection is None:
                return
            removed = False
            verified_absent = False
            if auth_sftp is not None:
                try:
                    await asyncio.wait_for(auth_sftp.remove(auth_path), timeout=AUTH_CLEANUP_SFTP_TIMEOUT)
                    removed = True
                except asyncssh.SFTPNoSuchFile:
                    removed = True
                    verified_absent = True
                except Exception:
                    removed = False
            if removed and not verified_absent and auth_sftp is not None:
                try:
                    await asyncio.wait_for(auth_sftp.lstat(auth_path), timeout=AUTH_CLEANUP_SFTP_TIMEOUT)
                except asyncssh.SFTPNoSuchFile:
                    verified_absent = True
                except Exception:
                    verified_absent = False

            async def command_cleanup(cleanup_connection) -> bool:
                try:
                    fallback = await asyncio.wait_for(
                        cleanup_connection.run(f"rm -f -- {shlex.quote(auth_path)}", check=False),
                        timeout=AUTH_CLEANUP_COMMAND_TIMEOUT,
                    )
                    if fallback.exit_status != 0:
                        return False
                    verify = await asyncio.wait_for(
                        cleanup_connection.run(f"test ! -e {shlex.quote(auth_path)}", check=False),
                        timeout=AUTH_CLEANUP_COMMAND_TIMEOUT,
                    )
                    return verify.exit_status == 0
                except Exception:
                    return False

            if not verified_absent:
                verified_absent = await command_cleanup(connection)
            reconnect = None
            if not verified_absent and not auth_cleanup_reconnect_attempted:
                auth_cleanup_reconnect_attempted = True
                try:
                    reconnect, _fingerprint = await asyncio.wait_for(
                        _connect(request),
                        timeout=AUTH_CLEANUP_RECONNECT_TIMEOUT,
                    )
                    if reconnect is not None:
                        verified_absent = await command_cleanup(reconnect)
                except Exception:
                    verified_absent = False
                finally:
                    if reconnect is not None:
                        reconnect.close()
                        try:
                            await reconnect.wait_closed()
                        except Exception:
                            pass
            if not verified_absent:
                raise NetworkTaskError(
                    "一次性 Auth Key 临时文件清理失败",
                    recovery_code="AUTH_FILE_CLEANUP_FAILED",
                    recovery_action="请立即登录该隔离 VPS，删除 GenBox 创建的 .genbox-tailscale-auth-* 临时文件，然后重新生成一次性 Auth Key。",
                )
            auth_path = ""

        async def shielded_auth_cleanup() -> None:
            cleanup_task = asyncio.create_task(cleanup_auth_file())
            try:
                await asyncio.shield(asyncio.wait_for(cleanup_task, timeout=AUTH_CLEANUP_TOTAL_TIMEOUT))
            except asyncio.CancelledError:
                await asyncio.shield(asyncio.wait_for(cleanup_task, timeout=AUTH_CLEANUP_TOTAL_TIMEOUT))
                raise

        try:
            state["status"] = "running"
            update(0, "running", "正在检查这台电脑的网络状态")
            if request.provider == "tailscale" and not local_status()["online"]:
                raise RuntimeError("这台电脑的 Tailscale 还没有登录")
            update(0, "success", "这台电脑已准备好")

            update(1, "running", "正在连接远程 VPS")
            connection, _fingerprint = await _connect(request)
            if connection is None:
                raise PermissionError("需要先确认 VPS 主机指纹")
            update(1, "success", "远程 VPS 连接成功")

            update(2, "running", "正在检查 VPS 安装条件")
            privileges = None
            sudo_checked = False

            async def ensure_admin() -> None:
                nonlocal privileges, sudo_checked
                if sudo_checked:
                    return
                privileges = await _diagnose_privileges(connection, request.credential)
                if not privileges["can_admin"]:
                    code = privileges["diagnostic_code"]
                    recovery_code, recovery_action = {
                        "sudo_password_required": (
                            "SUDO_PASSWORD_REQUIRED",
                            "请选择密码 sudo 并提供独立 sudo 密码；仅在密码 SSH 认证下可显式选择复用。",
                        ),
                        "sudo_password_rejected": (
                            "SUDO_PASSWORD_REJECTED",
                            "sudo 密码未通过验证；请检查提权凭据后重试。",
                        ),
                        "passwordless_sudo_unavailable": (
                            "PASSWORDLESS_SUDO_UNAVAILABLE",
                            "当前账号没有免密 sudo；请选择密码 sudo 或使用具备管理员权限的账号。",
                        ),
                    }.get(code, (
                        "ADMIN_ELEVATION_REQUIRED",
                        "安装或配置网络工具需要显式且已验证的管理员提权能力。",
                    ))
                    raise NetworkTaskError(
                        "VPS 管理员提权条件未满足",
                        recovery_code=recovery_code,
                        recovery_action=recovery_action,
                    )
                sudo_checked = True

            async def run_admin(command: str, *, timeout: int = 300):
                await ensure_admin()
                shell_command, input_data = _elevated_command(command, request.credential, privileges)
                return await asyncio.wait_for(
                    connection.run(shell_command, input=input_data, check=False),
                    timeout=timeout,
                )

            async def read_remote_status(attempt: int):
                result = await asyncio.wait_for(
                    connection.run(TAILSCALE_STATUS_COMMAND, check=False),
                    timeout=30,
                )
                address, diagnostics, diagnostic_error = inspect_tailscale_peer_address(result.stdout)
                diagnostics.update(
                    installed=True,
                    exit_status=int(result.exit_status),
                    stderr_present=bool(str(getattr(result, "stderr", "") or "").strip()),
                    attempt=attempt,
                )
                state["diagnostics"] = diagnostics
                if (
                    result.exit_status != 0
                    or not diagnostics["json_parsed"]
                    or diagnostics["json_type"] != "object"
                ):
                    address = None
                return result, address, diagnostics, diagnostic_error

            async def install_tailscale(os_id: str, codename: str) -> None:
                plan = tailscale_install_plan(os_id, codename, uuid.uuid4().hex)
                keyring_existed = False
                repository_existed = False
                created_keyring = False
                created_repository = False
                try:
                    keyring_existed = (await run_admin(f"test -e {shlex.quote(TAILSCALE_KEYRING_PATH)}", timeout=30)).exit_status == 0
                    repository_existed = (await run_admin(f"test -e {shlex.quote(TAILSCALE_REPOSITORY_PATH)}", timeout=30)).exit_status == 0
                    for command_name in ("prepare_keyring_dir", "download_keyring", "download_repository"):
                        result = await run_admin(plan[command_name])
                        if result.exit_status != 0:
                            raise NetworkTaskError(
                                "Tailscale 官方软件源准备失败",
                                recovery_code="TAILSCALE_REPOSITORY_SETUP_FAILED",
                                recovery_action="确认隔离 VPS 可以访问 pkgs.tailscale.com，且 sudo 权限可用后重试。",
                            )
                    for command_name in ("check_keyring_conflict", "check_repository_conflict"):
                        result = await run_admin(plan[command_name], timeout=30)
                        if result.exit_status != 0:
                            raise NetworkTaskError(
                                "VPS 已有不同的 Tailscale 软件源文件",
                                recovery_code="TAILSCALE_REPOSITORY_CONFLICT",
                                recovery_action="GenBox 没有覆盖现有软件源；请人工确认现有 Tailscale 仓库后，再使用仅检测模式。",
                            )
                    if not keyring_existed:
                        result = await run_admin(plan["install_keyring"], timeout=30)
                        if result.exit_status != 0:
                            raise NetworkTaskError(
                                "Tailscale 软件源密钥安装失败",
                                recovery_code="TAILSCALE_REPOSITORY_SETUP_FAILED",
                                recovery_action="确认 /usr/share/keyrings 可写且 sudo 权限可用后重试。",
                            )
                        created_keyring = True
                    if not repository_existed:
                        result = await run_admin(plan["install_repository"], timeout=30)
                        if result.exit_status != 0:
                            raise NetworkTaskError(
                                "Tailscale 软件源配置失败",
                                recovery_code="TAILSCALE_REPOSITORY_SETUP_FAILED",
                                recovery_action="确认 /etc/apt/sources.list.d 可写且 sudo 权限可用后重试。",
                            )
                        created_repository = True
                    for command_name in ("apt_update", "apt_install"):
                        result = await run_admin(plan[command_name])
                        if result.exit_status != 0:
                            raise NetworkTaskError(
                                "VPS Tailscale 软件包安装失败",
                                recovery_code="TAILSCALE_INSTALL_FAILED",
                                recovery_action="现有应用没有被修改；请检查 VPS 软件源、磁盘空间和 sudo 权限后重新安装。",
                            )
                except Exception:
                    rollback_paths = []
                    if created_repository:
                        rollback_paths.append(TAILSCALE_REPOSITORY_PATH)
                    if created_keyring:
                        rollback_paths.append(TAILSCALE_KEYRING_PATH)
                    if rollback_paths:
                        await run_admin("rm -f -- " + " ".join(shlex.quote(path) for path in rollback_paths), timeout=30)
                    raise
                finally:
                    try:
                        await run_admin(plan["cleanup_downloads"], timeout=30)
                    except Exception:
                        pass

            output = ""
            update(2, "running", "正在确认 VPS 是否已安装 Tailscale")
            remote_release = None
            os_release_text = ""
            if request.operation_mode == "auto":
                os_release = await asyncio.wait_for(
                    connection.run(REMOTE_OS_RELEASE_COMMAND, check=False),
                    timeout=30,
                )
                if os_release.exit_status != 0:
                    raise NetworkTaskError(
                        "无法识别 VPS 系统版本",
                        recovery_code="REMOTE_OS_UNSUPPORTED",
                        recovery_action="自动安装只支持已验证的 Ubuntu/Debian systemd 系统；可先人工安装后改用仅检测模式。",
                    )
                os_release_text = os_release.stdout
            presence = await asyncio.wait_for(
                connection.run(TAILSCALE_PRESENCE_COMMAND, check=False),
                timeout=30,
            )
            installed = presence.exit_status == 0
            state["diagnostics"] = {
                "installed": installed,
                "stdout_present": False,
                "json_parsed": False,
                "json_extracted": False,
                "json_type": "not_checked",
                "backend_state": "not_checked",
                "top_level_ips_present": False,
                "top_level_ip_count": 0,
                "self_ips_present": False,
                "self_ip_count": 0,
                "cgnat_candidate_count": 0,
                "exit_status": int(presence.exit_status),
                "stderr_present": False,
                "attempt": 0,
            }
            update(2, "success", "VPS 系统与 Tailscale 状态已确认")

            if not installed:
                if request.operation_mode != "auto":
                    update(3, "failed", "VPS 尚未安装 Tailscale")
                    raise NetworkTaskError(
                        "VPS 尚未安装 Tailscale",
                        recovery_code="TAILSCALE_NOT_INSTALLED",
                        recovery_action="选择“自动检测、安装并加入”并提供一次性 Auth Key。",
                    )
                if not enrollment_token:
                    pause_for_action(
                        3,
                        "TAILSCALE_AUTH_KEY_REQUIRED",
                        "VPS 尚未安装 Tailscale。粘贴一次性 Auth Key 后，GenBox 才会安装并继续加入网络。",
                        "已确认 VPS 尚未安装 Tailscale，等待一次性 Auth Key",
                    )
                    return
                remote_release = parse_remote_os_release(os_release_text)
                update(3, "running", "正在使用固定官方流程安装 Tailscale")
                await install_tailscale(*remote_release)
                verify_install = await asyncio.wait_for(
                    connection.run(TAILSCALE_PRESENCE_COMMAND, check=False),
                    timeout=30,
                )
                if verify_install.exit_status != 0:
                    raise NetworkTaskError(
                        "安装结束后 VPS 仍找不到 Tailscale",
                        recovery_code="TAILSCALE_INSTALL_FAILED",
                        recovery_action="请检查 apt 安装结果后重试；GenBox 不会自动卸载已有软件包。",
                    )
                installed = True
                service_result = await run_admin(TAILSCALE_SERVICE_COMMAND, timeout=60)
                if service_result.exit_status != 0:
                    raise NetworkTaskError(
                        "Tailscale 已安装，但后台服务启动失败",
                        recovery_code="TAILSCALED_START_FAILED",
                        recovery_action="请检查 VPS 的 systemd/tailscaled 状态后重试；已经安装的软件会保留。",
                    )
                update(3, "success", "VPS Tailscale 已安装并启动")
            else:
                update(3, "skipped", "VPS 已安装 Tailscale，无需重复安装")

            status_result, detected_address, diagnostics, _diagnostic_error = await read_remote_status(1)
            backend_state = diagnostics.get("backend_state")
            service_unavailable = status_result.exit_status != 0 or backend_state == "stopped"
            if service_unavailable:
                if request.operation_mode != "auto":
                    update(3, "failed", "VPS Tailscale 后台服务未运行")
                    raise NetworkTaskError(
                        "VPS Tailscale 后台服务未运行",
                        recovery_code="TAILSCALE_SERVICE_UNAVAILABLE",
                        recovery_action="选择自动准备模式启动服务，或人工启动 tailscaled 后使用仅检测模式。",
                    )
                if not enrollment_token:
                    pause_for_action(
                        3,
                        "TAILSCALE_AUTH_KEY_REQUIRED",
                        "Tailscale 已安装但服务未运行。粘贴一次性 Auth Key 后，GenBox 才会启动服务并继续检查是否需要加入网络。",
                        "已确认 Tailscale 服务未运行，等待一次性 Auth Key",
                    )
                    return
                if remote_release is None:
                    remote_release = parse_remote_os_release(os_release_text)
                update(3, "running", "Tailscale 已安装，正在启动后台服务")
                service_result = await run_admin(TAILSCALE_SERVICE_COMMAND, timeout=60)
                if service_result.exit_status != 0:
                    raise NetworkTaskError(
                        "Tailscale 后台服务启动失败",
                        recovery_code="TAILSCALED_START_FAILED",
                        recovery_action="请检查 VPS 的 systemd/tailscaled 状态后重试。",
                    )
                status_result, detected_address, diagnostics, _diagnostic_error = await read_remote_status(1)
                backend_state = diagnostics.get("backend_state")
                update(3, "success", "VPS Tailscale 后台服务已启动")

            if backend_state == "starting":
                for attempt in range(2, 6):
                    await asyncio.sleep(2)
                    status_result, detected_address, diagnostics, _diagnostic_error = await read_remote_status(attempt)
                    backend_state = diagnostics.get("backend_state")
                    if backend_state != "starting":
                        break

            if detected_address:
                update(4, "skipped", "VPS 已加入 Tailnet，无需重复注册")
            elif backend_state == "needs_login" and request.operation_mode == "auto":
                if not enrollment_token:
                    pause_for_action(
                        4,
                        "TAILSCALE_AUTH_KEY_REQUIRED",
                        "VPS 已安装 Tailscale，现在只需要一个一次性 Auth Key 加入同一 Tailnet。",
                        "VPS 已准备好，等待一次性 Auth Key",
                    )
                    return
                if remote_release is None:
                    remote_release = parse_remote_os_release(os_release_text)
                update(4, "running", "正在使用一次性 Auth Key 加入 Tailnet")
                try:
                    home_result = await asyncio.wait_for(
                        connection.run(REMOTE_HOME_COMMAND, check=False),
                        timeout=30,
                    )
                    home_dir = str(home_result.stdout or "").strip()
                    if home_result.exit_status != 0 or not home_dir.startswith("/") or ".." in home_dir.split("/") or not re.fullmatch(r"/[A-Za-z0-9._/-]{1,200}", home_dir):
                        raise NetworkTaskError(
                            "无法确认远程用户目录",
                            recovery_code="AUTH_FILE_CREATE_FAILED",
                            recovery_action="请确认 SSH 用户拥有可写的 HOME 目录后重试。",
                        )
                    auth_path = posixpath.join(home_dir, f".genbox-tailscale-auth-{uuid.uuid4().hex}")
                    auth_sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=30)
                    secret_bytes = enrollment_token.encode("utf-8")
                    try:
                        async with auth_sftp.open(
                            auth_path,
                            "xb",
                            attrs=asyncssh.SFTPAttrs(permissions=0o600),
                        ) as remote_file:
                            await remote_file.write(secret_bytes)
                        await auth_sftp.chmod(auth_path, 0o600)
                        attrs = await auth_sftp.lstat(auth_path)
                    except Exception as exc:
                        raise NetworkTaskError(
                            "无法安全创建一次性 Auth Key 临时文件",
                            recovery_code="AUTH_FILE_CREATE_FAILED",
                            recovery_action="请确认 SSH 用户 HOME 目录可写，并重新生成一次性 Auth Key 后重试。",
                        ) from exc
                    permissions = int(attrs.permissions or 0)
                    if attrs.size != len(secret_bytes) or permissions & 0o777 != 0o600 or not stat.S_ISREG(permissions):
                        raise NetworkTaskError(
                            "一次性 Auth Key 临时文件权限验证失败",
                            recovery_code="AUTH_FILE_PERMISSION_FAILED",
                            recovery_action="GenBox 已停止加入网络；请检查远程文件系统权限后重新生成一次性 Auth Key。",
                        )
                    enroll_command = (
                        f"tailscale up --auth-key=file:{shlex.quote(auth_path)} "
                        f"--hostname {shlex.quote(request.device_name)} --timeout=60s"
                    )
                    enroll_result = await run_admin(enroll_command, timeout=60)
                    if enroll_result.exit_status != 0:
                        raise NetworkTaskError(
                            "VPS 未接受一次性 Tailscale Auth Key",
                            recovery_code="TAILSCALE_AUTH_REJECTED",
                            recovery_action="该 Auth Key 可能已使用、过期或不属于同一 Tailnet；请重新生成一次性 Key 后重试。",
                        )
                finally:
                    if auth_path:
                        await shielded_auth_cleanup()
                update(4, "success", "VPS 已提交加入 Tailnet 请求，密钥临时文件已删除")
                status_result, detected_address, diagnostics, _diagnostic_error = await read_remote_status(1)
                backend_state = diagnostics.get("backend_state")
            elif backend_state == "needs_login" and request.operation_mode == "existing":
                update(4, "failed", "VPS Tailscale 尚未登录")
                raise NetworkTaskError(
                    "VPS Tailscale 尚未登录",
                    recovery_code="TAILSCALE_AUTH_KEY_REQUIRED",
                    recovery_action="选择“自动检测、安装并加入”，粘贴一次性 Auth Key 后重试。",
                )
            elif backend_state == "running":
                update(4, "skipped", "VPS 已在 Tailnet，正在等待地址同步")
            else:
                update(4, "failed", "VPS Tailscale 状态无法安全判断")
                raise NetworkTaskError(
                    "VPS Tailscale 状态无法安全判断",
                    recovery_code="TAILSCALE_SERVICE_UNAVAILABLE",
                    recovery_action="请检查 tailscaled 服务状态；GenBox 不会在未知状态下安装、重置或重复注册。",
                )

            update(5, "running", NETWORK_STEPS[5][1])
            if not detected_address:
                for attempt in range(2, 6):
                    state["logs"].append({
                        "time": time.strftime("%H:%M:%S"),
                        "message": f"VPS Tailscale 地址尚未就绪，2 秒后自动重试（{attempt - 1}/5）",
                    })
                    await asyncio.sleep(2)
                    status_result, detected_address, diagnostics, _diagnostic_error = await read_remote_status(attempt)
                    if detected_address:
                        break
            if not detected_address:
                if diagnostics.get("backend_state") == "needs_login":
                    raise NetworkTaskError(
                        "VPS 仍未加入 Tailnet",
                        recovery_code="TAILSCALE_AUTH_REJECTED",
                        recovery_action="请重新生成一次性 Auth Key，并确认它属于与本机相同的 Tailnet。",
                    )
                raise NetworkTaskError(
                    "VPS 已运行 Tailscale，但地址仍未就绪",
                    recovery_code="TAILSCALE_RUNNING_NO_IPV4",
                    recovery_action="请稍后重新读取地址；GenBox 不会重复安装或重复注册。",
                )
            output = detected_address
            update(5, "success", "已确认 VPS Tailscale 地址")

            verification = {}
            if request.provider == "tailscale":
                update(0, "running", "正在配置本机 Tailscale Serve")
                served = enable_genbox_serve()
                local = local_status()
                destination = validate_tailscale_destination(
                    served["url"],
                    address=served["address"],
                    dns_name=str(local.get("dns_name") or ""),
                    serve_port=int(local["serve_port"]),
                    app_port=int(local["app_port"]),
                )
                update(0, "success", "本机 Tailscale Serve 已准备好")
                remote_address = validate_tailscale_peer_address(output)
                update(6, "running", "正在等待两台设备完成同步")
                peer_reachable = False
                peer_seen_reachable = False
                app_probe_attempted = False
                genbox_reachable = False
                probe = None
                for attempt in range(1, 7):
                    peer_reachable = await asyncio.to_thread(ping_peer, remote_address)
                    if peer_reachable:
                        peer_seen_reachable = True
                        update(7, "running", "正在从 VPS 访问 GenBox")
                        app_probe_attempted = True
                        probe = await connection.run(
                            f"curl -fsS --max-time 10 {shlex.quote(destination)}/api/setup/status",
                            check=False,
                        )
                        probe_stdout = str(getattr(probe, "stdout", "") or "")
                        probe_stderr = str(getattr(probe, "stderr", "") or "")
                        probe_valid_setup_status = is_genbox_setup_status(probe_stdout)
                        genbox_reachable = probe.exit_status == 0 and probe_valid_setup_status
                        state["diagnostics"].update(
                            http_probe_exit_status=int(probe.exit_status),
                            http_probe_stdout_present=bool(probe_stdout.strip()),
                            http_probe_stderr_present=bool(probe_stderr.strip()),
                            http_probe_valid_setup_status=probe_valid_setup_status,
                        )
                        if genbox_reachable:
                            break
                    if attempt < 6:
                        state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": f"网络正在同步，5 秒后自动重试（{attempt}/6）"})
                        await asyncio.sleep(5)
                verification = {
                    "local_address": served["address"],
                    "remote_address": remote_address,
                    "genbox_url": destination,
                    "peer_reachable": peer_seen_reachable,
                    "genbox_reachable": genbox_reachable,
                }
                if not peer_seen_reachable:
                    update(6, "failed", "两台设备暂时无法互通")
                    if state["steps"][7]["status"] == "running":
                        state["steps"][7]["status"] = "pending"
                    raise NetworkTaskError(
                        "两台设备都已加入网络，但目前不能互相访问",
                        recovery_code="TAILSCALE_PEER_UNREACHABLE",
                        recovery_action="请在 Tailscale 管理台确认电脑和 VPS 都在线并位于同一 Tailnet，然后重新检测互通。",
                    )
                update(6, "success", "两台设备可以互通")
                if app_probe_attempted and not genbox_reachable:
                    update(7, "failed", "VPS 无法打开 GenBox 私网入口")
                    probe_exit_status = int(probe.exit_status) if probe is not None else -1
                    recovery_action = {
                        6: "VPS 无法解析本机 Tailscale MagicDNS 名称。请确认 Tailnet 已启用 MagicDNS，且 VPS 接受 Tailscale DNS 后重试。",
                        7: "VPS 已到达私网，但 GenBox 私网入口端口没有接受连接。请重新执行“检查本机私网入口”后重试。",
                        22: "VPS 已连接到私网入口，但入口返回了 HTTP 错误。请重新准备本机 Tailscale Serve 后重试。",
                        28: "VPS 访问 GenBox 私网入口超时。请检查 Tailnet 访问规则和两台设备在线状态后重试。",
                    }.get(
                        probe_exit_status,
                        "请重新执行“检查本机私网入口”，确认 GenBox 与 Tailscale Serve 都在线后重试。",
                    )
                    raise NetworkTaskError(
                        "私网已经连通，但 VPS 无法打开 GenBox",
                        recovery_code="GENBOX_HTTP_PROBE_FAILED",
                        recovery_action=recovery_action,
                    )
                update(7, "success", "VPS 可以访问 GenBox 应用")

                update(8, "running", "正在保存可用访问地址")
                target_data = request.target.model_dump()
                available = list(dict.fromkeys([*target_data.get("available_networks", []), request.provider]))
                target_data.update(
                    primary_network=request.provider,
                    available_networks=available,
                    network_url=destination,
                    network_verified_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                )
                upsert_target(target_data)
                update(8, "success", "访问地址已保存")

            if auth_path:
                await shielded_auth_cleanup()
            state["progress"] = 100
            state["status"] = "completed"
            state["result"] = {"provider": request.provider, "address": output[:200], **verification}
        except asyncio.CancelledError:
            state["status"] = "cancelled"
            state["steps"][active_index]["status"] = "failed"
            state["failed_phase"] = NETWORK_STEPS[active_index][0]
            state["recovery_code"] = "NETWORK_TASK_CANCELLED"
            state["recovery_action"] = "任务已取消；重新开始时会从 VPS 的真实状态重新检测。"
            state["next_action"] = next_action_for("NETWORK_TASK_CANCELLED")
            state["error"] = "任务已取消"
            raise
        except Exception as exc:
            phase = NETWORK_STEPS[active_index][0]
            if isinstance(exc, NetworkTaskError):
                recovery_code, recovery_action = exc.recovery_code, exc.recovery_action
            else:
                recovery_code, recovery_action = RECOVERY_BY_PHASE[phase]
            state["status"] = "failed"
            state["steps"][active_index]["status"] = "failed"
            state["failed_phase"] = phase
            state["recovery_code"] = recovery_code
            state["recovery_action"] = recovery_action
            state["next_action"] = next_action_for(recovery_code)
            state["error"] = sanitized_error(exc)
        finally:
            if auth_path and connection is not None:
                try:
                    await shielded_auth_cleanup()
                except Exception:
                    state["status"] = "failed"
                    state["steps"][4]["status"] = "failed"
                    state["failed_phase"] = "remote_enroll"
                    state["recovery_code"] = "AUTH_FILE_CLEANUP_FAILED"
                    state["recovery_action"] = "请立即登录该隔离 VPS，删除 GenBox 创建的 .genbox-tailscale-auth-* 临时文件，然后重新生成一次性 Auth Key。"
                    state["next_action"] = next_action_for("AUTH_FILE_CLEANUP_FAILED")
                    state["error"] = "一次性 Auth Key 临时文件清理未完成，原始错误已隐藏。"
            request.enrollment_token = SecretStr("")
            enrollment_token = ""
            if auth_sftp is not None:
                auth_sftp.exit()
                try:
                    await auth_sftp.wait_closed()
                except Exception:
                    pass
            if connection is not None:
                connection.close()
                await connection.wait_closed()
            if self.active.get(active_key) == task_id:
                self.active.pop(active_key, None)


network_tasks = NetworkTaskManager()
