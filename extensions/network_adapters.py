"""Fixed network connector plans for supported overlay/tunnel providers."""
import asyncio
import ipaddress
import json
import shlex
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

from extensions.models import NetworkConnectRequest
from extensions.orchestrator import _connect
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


def validate_tailscale_destination(url: str, *, address: str, serve_port: int, app_port: int) -> str:
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

    host = parsed.hostname.rstrip(".").lower()
    if host != str(expected):
        raise ValueError("GenBox 私网地址必须精确匹配已验证的本机 Tailscale IPv4 地址")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def validate_tailscale_peer_address(output: str) -> str:
    addresses = [line.strip() for line in str(output or "").splitlines() if line.strip()]
    if len(addresses) != 1:
        raise ValueError("VPS 未返回唯一的 Tailscale IPv4 地址")
    try:
        address = ipaddress.ip_address(addresses[0])
    except ValueError as exc:
        raise ValueError("VPS 返回的 Tailscale 地址无效") from exc
    if address.version != 4 or address not in ipaddress.ip_network("100.64.0.0/10"):
        raise ValueError("VPS 返回的地址不是 Tailscale IPv4 地址")
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
        return [
            ("remote_detect", "tailscale status --json >/dev/null && tailscale ip -4"),
        ]
    raise ValueError("当前仅 Tailscale 已具备完整的安全验证链")


class NetworkTaskManager:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.runners: dict[str, asyncio.Task] = {}

    def create(self, request: NetworkConnectRequest) -> str:
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
            "result": None,
            "steps": [{"id": key, "label": label, "status": "pending"} for key, label in NETWORK_STEPS],
            "logs": [],
        }
        self.runners[task_id] = asyncio.create_task(self._run(task_id, request))
        return task_id

    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    async def _run(self, task_id: str, request: NetworkConnectRequest) -> None:
        state = self.tasks[task_id]
        connection = None
        active_index = 0

        def update(index: int, status: str, message: str = ""):
            nonlocal active_index
            active_index = index
            state["phase"] = NETWORK_STEPS[index][0]
            state["steps"][index]["status"] = status
            state["progress"] = int(index / len(NETWORK_STEPS) * 100)
            if message:
                state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": message})

        def sanitized_error(exc: Exception) -> str:
            message = str(exc)
            for secret in (
                request.enrollment_token, request.credential.password, request.credential.sudo_password,
                request.credential.private_key, request.credential.passphrase,
            ):
                if secret:
                    message = message.replace(secret, "[REDACTED]")
            return message[:240]

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
            user_id = (await connection.run("id -u", check=True)).stdout.strip()
            sudo_password = request.credential.sudo_password or request.credential.password
            use_sudo = user_id != "0"
            if use_sudo:
                probe = await connection.run("sudo -n true >/dev/null 2>&1", check=False)
                if probe.exit_status != 0:
                    if not sudo_password:
                        raise PermissionError("安装网络工具需要 sudo 密码")
                    probe = await connection.run("sudo -S -p '' true", input=sudo_password + "\n", check=False)
                    if probe.exit_status != 0:
                        raise PermissionError("VPS 管理员权限验证失败")
            update(2, "success", "VPS 安装条件正常")

            output = ""
            plan = command_plan(request)
            if request.operation_mode == "existing":
                plan = [item for item in plan if item[0] == "remote_detect"]
                update(3, "success", "VPS 已安装，跳过安装")
                update(4, "success", "VPS 已加入网络，跳过重复注册")
            for phase, command in plan:
                index = 3 if phase == "remote_install" else 4 if phase == "remote_enroll" else 5
                update(index, "running", NETWORK_STEPS[index][1])
                needs_sudo = use_sudo and phase in {"remote_install", "remote_enroll"}
                wrapped = f"sudo -S -p '' sh -lc {shlex.quote(command)}" if needs_sudo else command
                run_options = {"check": False}
                if needs_sudo and sudo_password:
                    run_options["input"] = sudo_password + "\n"
                result = await asyncio.wait_for(
                    connection.run(wrapped, **run_options),
                    timeout=30 if phase == "remote_detect" else 300,
                )
                if result.exit_status != 0:
                    raise RuntimeError(f"{NETWORK_STEPS[index][1]}失败")
                output = result.stdout.strip()
                update(index, "success", f"{NETWORK_STEPS[index][1]}完成")

            verification = {}
            if request.provider == "tailscale":
                update(0, "running", "正在配置本机 Tailscale Serve")
                served = enable_genbox_serve()
                local = local_status()
                destination = validate_tailscale_destination(
                    f"http://{served['address']}:{int(local['serve_port'])}",
                    address=served["address"],
                    serve_port=int(local["serve_port"]),
                    app_port=int(local["app_port"]),
                )
                update(0, "success", "本机 Tailscale Serve 已准备好")
                remote_address = validate_tailscale_peer_address(output)
                update(6, "running", "正在等待两台设备完成同步")
                peer_reachable = False
                genbox_reachable = False
                probe = None
                for attempt in range(1, 7):
                    peer_reachable = await asyncio.to_thread(ping_peer, remote_address)
                    if peer_reachable:
                        update(7, "running", "正在从 VPS 访问 GenBox")
                        probe = await connection.run(
                            f"curl -fsS --max-time 10 {shlex.quote(destination)}/api/setup/status",
                            check=False,
                        )
                        genbox_reachable = probe.exit_status == 0 and is_genbox_setup_status(probe.stdout)
                        if genbox_reachable:
                            break
                    if attempt < 6:
                        state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": f"网络正在同步，5 秒后自动重试（{attempt}/6）"})
                        await asyncio.sleep(5)
                update(6, "success" if peer_reachable else "failed", "设备互通检查完成")
                update(7, "success" if genbox_reachable else "failed", "GenBox 应用访问检查完成")
                verification = {
                    "local_address": served["address"],
                    "remote_address": remote_address,
                    "genbox_url": destination,
                    "peer_reachable": peer_reachable,
                    "genbox_reachable": genbox_reachable,
                }
                if not peer_reachable or not genbox_reachable:
                    raise RuntimeError("网络已加入，但仍未连通。请确认 VPS 在线，然后使用“已有工具，只连接和检测”重试。")

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

            state["progress"] = 100
            state["status"] = "completed"
            state["result"] = {"provider": request.provider, "address": output[:200], **verification}
        except Exception as exc:
            phase = NETWORK_STEPS[active_index][0]
            recovery_code, recovery_action = RECOVERY_BY_PHASE[phase]
            state["status"] = "failed"
            state["steps"][active_index]["status"] = "failed"
            state["failed_phase"] = phase
            state["recovery_code"] = recovery_code
            state["recovery_action"] = recovery_action
            state["error"] = sanitized_error(exc)
        finally:
            if connection is not None:
                connection.close()
                await connection.wait_closed()


network_tasks = NetworkTaskManager()
