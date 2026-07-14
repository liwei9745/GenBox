"""Fixed network connector plans for supported overlay/tunnel providers."""
import asyncio
import shlex
import time
import uuid

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
    ("peer_verify", "检查两台设备互通"),
    ("http_probe", "检查 VPS 能否访问 GenBox"),
    ("destination_ready", "保存可用访问地址"),
]


def command_plan(request: NetworkConnectRequest) -> list[tuple[str, str]]:
    token = shlex.quote(request.enrollment_token)
    name = shlex.quote(request.device_name)
    if request.provider == "tailscale":
        return [
            ("remote_install", "command -v tailscale >/dev/null || (curl -fsSL https://tailscale.com/install.sh | sh)"),
            ("remote_enroll", f"tailscale up --auth-key={token} --hostname={name} --reset"),
            ("remote_detect", "tailscale status --json >/dev/null && tailscale ip -4"),
        ]
    if request.provider == "netbird":
        management = f" --management-url {shlex.quote(request.management_url)}" if request.management_url else ""
        return [
            ("remote_install", "command -v netbird >/dev/null || (curl -fsSL https://pkgs.netbird.io/install.sh | sh)"),
            ("remote_enroll", f"netbird up --setup-key {token} --name {name}{management}"),
            ("remote_detect", "netbird status"),
        ]
    return [
        (
            "remote_install",
            "command -v cloudflared >/dev/null || "
            "(curl -fsSL -o /tmp/cloudflared.deb "
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb "
            "&& dpkg -i /tmp/cloudflared.deb && rm -f /tmp/cloudflared.deb)",
        ),
        ("remote_enroll", f"cloudflared service uninstall >/dev/null 2>&1 || true; cloudflared service install {token}"),
        ("remote_detect", "systemctl is-active cloudflared"),
    ]


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

        def update(index: int, status: str, message: str = ""):
            state["phase"] = NETWORK_STEPS[index][0]
            state["steps"][index]["status"] = status
            state["progress"] = int(index / len(NETWORK_STEPS) * 100)
            if message:
                state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": message})

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
                served = enable_genbox_serve()
                remote_address = output.splitlines()[0].strip()
                update(5, "running", "正在等待两台设备完成同步")
                peer_reachable = False
                genbox_reachable = False
                probe = None
                for attempt in range(1, 7):
                    peer_reachable = await asyncio.to_thread(ping_peer, remote_address)
                    if peer_reachable:
                        update(6, "running", "正在从 VPS 访问 GenBox")
                        probe = await connection.run(
                            f"curl -fsS --max-time 10 {shlex.quote(served['url'])}/ >/dev/null",
                            check=False,
                        )
                        genbox_reachable = probe.exit_status == 0
                        if genbox_reachable:
                            break
                    if attempt < 6:
                        state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": f"网络正在同步，5 秒后自动重试（{attempt}/6）"})
                        await asyncio.sleep(5)
                update(5, "success" if peer_reachable else "failed", "设备互通检查完成")
                update(6, "success" if genbox_reachable else "failed", "GenBox 访问检查完成")
                verification = {
                    "local_address": served["address"],
                    "remote_address": remote_address,
                    "genbox_url": served["url"],
                    "peer_reachable": peer_reachable,
                    "genbox_reachable": genbox_reachable,
                }
                if not peer_reachable or not genbox_reachable:
                    raise RuntimeError("网络已加入，但仍未连通。请确认 VPS 在线，然后使用“已有工具，只连接和检测”重试。")

                update(7, "running", "正在保存可用访问地址")
                target_data = request.target.model_dump()
                available = list(dict.fromkeys([*target_data.get("available_networks", []), request.provider]))
                target_data.update(
                    primary_network=request.provider,
                    available_networks=available,
                    network_url=served["url"],
                    network_verified_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                )
                upsert_target(target_data)
                update(7, "success", "访问地址已保存")

            state["progress"] = 100
            state["status"] = "completed"
            state["result"] = {"provider": request.provider, "address": output[:200], **verification}
        except Exception as exc:
            state["status"] = "failed"
            state["error"] = str(exc)[:240]
        finally:
            if connection is not None:
                connection.close()
                await connection.wait_closed()


network_tasks = NetworkTaskManager()
