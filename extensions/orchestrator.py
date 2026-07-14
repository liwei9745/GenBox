import asyncio
import base64
import hashlib
import io
import json
import os
import re
import secrets
import shlex
import time
import uuid
from typing import Any

from extensions.models import ExtensionDeployRequest, ExtensionKeyResetRequest, ExtensionPlanRequest, ExtensionTestRequest
import extensions.store as extensions_store


DEPLOY_STEPS = [
    ("connect", "连接 VPS"),
    ("docker", "检查 Docker"),
    ("prepare", "创建部署目录"),
    ("pull", "拉取 chatgpt2api 镜像"),
    ("start", "启动服务"),
    ("verify", "等待服务就绪"),
]
IMAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:@-]{2,255}$")
CLONE_SCRUB_KEYS = {
    "auth-key",
    "genbox-destination",
    "genbox-push-key",
    "genbox-push-url",
    "genbox-source-id",
    "push-key",
    "push-source-id",
}


def _fingerprint(key: Any) -> str:
    exported = key.export_public_key(format_name="openssh")
    blob = base64.b64decode(exported.split()[1])
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
    return f"SHA256:{digest}"


def _clone_config_scrub_script() -> str:
    """Return a self-contained script for stripping inherited clone secrets."""
    keys = json.dumps(sorted(CLONE_SCRUB_KEYS))
    return (
        "import json,os,sys; p=sys.argv[1]; d=json.load(open(p,encoding='utf-8')); "
        f"blocked=set({keys}); "
        "norm=lambda k:str(k).lower().replace('_','-'); "
        "clean=lambda v: ({k:clean(x) for k,x in v.items() if norm(k) not in blocked} "
        "if isinstance(v,dict) else [clean(x) for x in v] if isinstance(v,list) else v); "
        "d=clean(d); b=d.get('backup'); "
        "b.update({'enabled':False}) if isinstance(b,dict) else None; "
        "t=p+'.tmp'; open(t,'w',encoding='utf-8').write(json.dumps(d,ensure_ascii=False,indent=2)+'\\n'); os.replace(t,p)"
    )


def _password_sudo_command(command: str) -> str:
    sudo_command = f"sudo -S -p '' sh -lc {shlex.quote(command)}"
    return (
        "IFS= read -r sudo_password; "
        "printf '%s\\n' \"$sudo_password\" | "
        f"{sudo_command}"
    )


async def _connect(request: ExtensionTestRequest | ExtensionDeployRequest):
    try:
        import asyncssh
    except ImportError as exc:
        raise RuntimeError("缺少 asyncssh 依赖，请重新安装 requirements.txt") from exc
    kwargs: dict[str, Any] = {
        "host": request.target.host,
        "port": request.target.port,
        "username": request.target.username,
        "known_hosts": None,
        "connect_timeout": 15,
    }
    if request.credential.private_key:
        kwargs["client_keys"] = [asyncssh.import_private_key(
            request.credential.private_key,
            request.credential.passphrase or None,
        )]
    else:
        kwargs["password"] = request.credential.password
    connection = await asyncssh.connect(**kwargs)
    fingerprint = _fingerprint(connection.get_server_host_key())
    expected = request.expected_host_key or request.target.host_key
    if expected and expected != fingerprint:
        connection.close()
        await connection.wait_closed()
        raise PermissionError("VPS 主机指纹与已保存值不一致")
    if not expected and not request.trust_host_key:
        connection.close()
        await connection.wait_closed()
        return None, fingerprint
    return connection, fingerprint


async def test_connection(request: ExtensionTestRequest) -> dict:
    connection, fingerprint = await _connect(request)
    if connection is None:
        return {"ok": False, "needs_host_key_confirmation": True, "host_key": fingerprint}
    try:
        result = await asyncio.wait_for(connection.run("printf genbox-connected", check=True), timeout=15)
        user_id = (await connection.run("id -u", check=True)).stdout.strip()
        docker = await connection.run("docker version >/dev/null 2>&1", check=False)
        sudo = await connection.run("sudo -n true >/dev/null 2>&1", check=False)
        sudo_password = request.credential.sudo_password or request.credential.password
        sudo_with_password = False
        if user_id != "0" and sudo.exit_status != 0 and sudo_password:
            probe = await connection.run(
                _password_sudo_command("true"),
                input=sudo_password + "\n",
                check=False,
            )
            sudo_with_password = probe.exit_status == 0
        return {
            "ok": result.stdout == "genbox-connected",
            "host_key": fingerprint,
            "privileges": {
                "is_root": user_id == "0",
                "docker_access": docker.exit_status == 0,
                "passwordless_sudo": sudo.exit_status == 0,
                "password_sudo": sudo_with_password,
                "can_deploy": user_id == "0" or docker.exit_status == 0 or sudo.exit_status == 0 or sudo_with_password,
            },
        }
    finally:
        connection.close()
        await connection.wait_closed()


class ExtensionTaskManager:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.runners: dict[str, asyncio.Task] = {}
        self.deliveries: dict[str, str] = {}

    def create(self, request: ExtensionDeployRequest) -> str:
        plan = deployment_plans.take(request.confirmed_plan_id, request)
        task_id = uuid.uuid4().hex[:12]
        self.tasks[task_id] = {
            "id": task_id, "status": "queued", "phase": "connect", "progress": 0,
            "steps": [{"id": key, "label": label, "status": "pending"} for key, label in DEPLOY_STEPS],
            "logs": [], "error": None, "host_key": "", "result": None,
        }
        self.runners[task_id] = asyncio.create_task(self._run(task_id, request, plan))
        return task_id

    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        runner = self.runners.get(task_id)
        if not runner or runner.done():
            return False
        runner.cancel()
        return True

    def take_delivery(self, task_id: str) -> str | None:
        return self.deliveries.pop(task_id, None)

    async def _run(self, task_id: str, request: ExtensionDeployRequest, plan: dict) -> None:
        state = self.tasks[task_id]
        connection = None

        def step(index: int, status: str, log: str = ""):
            state["phase"] = DEPLOY_STEPS[index][0]
            state["steps"][index]["status"] = status
            state["progress"] = int(index / len(DEPLOY_STEPS) * 100)
            if log:
                state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": log})

        try:
            state["status"] = "running"
            step(0, "running", "正在建立安全 SSH 连接")
            connection, fingerprint = await _connect(request)
            state["host_key"] = fingerprint
            if connection is None:
                raise PermissionError("需要先确认 VPS 主机指纹")
            step(0, "success", "SSH 连接成功")

            user_id = (await connection.run("id -u", check=True)).stdout.strip()
            home_dir = (await connection.run("printf %s \"$HOME\"", check=True)).stdout.strip()
            docker_probe = await connection.run("docker version >/dev/null 2>&1", check=False)
            sudo_probe = await connection.run("sudo -n true >/dev/null 2>&1", check=False)
            sudo_password = request.credential.sudo_password or request.credential.password
            password_sudo_ok = False
            if user_id != "0" and sudo_probe.exit_status != 0 and sudo_password:
                password_probe = await connection.run(
                    _password_sudo_command("true"),
                    input=sudo_password + "\n",
                    check=False,
                )
                password_sudo_ok = password_probe.exit_status == 0
            use_sudo = user_id != "0" and (sudo_probe.exit_status == 0 or password_sudo_ok)
            docker_available = docker_probe.exit_status == 0 or use_sudo
            if user_id != "0" and not docker_available:
                raise PermissionError("当前用户没有 Docker 访问权限，且无法提权")
            if use_sudo and sudo_probe.exit_status != 0 and not password_sudo_ok:
                raise PermissionError("需要 sudo 密码才能部署（复制 /root 数据或提权 Docker）")

            async def run_command(command: str, privileged: bool, timeout: int = 300):
                if not use_sudo or not privileged:
                    return await asyncio.wait_for(connection.run(command, check=False), timeout=timeout)
                wrapped = _password_sudo_command(command)
                return await asyncio.wait_for(
                    connection.run(wrapped, input=(sudo_password + "\n") if sudo_password else "", check=False),
                    timeout=timeout,
                )

            if plan["strategy"] == "existing":
                for index in range(1, len(DEPLOY_STEPS)):
                    step(index, "success", "接入已有实例：未执行远程变更")
                console_url = f"http://{request.target.host}:{plan['service_port']}"
                instance = extensions_store.upsert_instance({
                    "id": plan["instance_id"], "target_id": request.target.id, "strategy": "existing",
                    "deployment_mode": "compose", "compose_project": plan.get("compose_project", ""),
                    "service_port": plan["service_port"], "install_dir": plan.get("install_dir", ""),
                    "data_dir": "", "image": plan["image"], "status": "detected",
                    "console_url": console_url, "api_url": f"{console_url}/v1", "managed": False,
                })
                state["progress"] = 100
                state["status"] = "completed"
                state["result"] = {
                    "url": console_url, "api_url": f"{console_url}/v1", "instance": instance.model_dump(),
                    "admin_key_available": False,
                }
                return

            install_dir = f"{home_dir}/genbox-apps/chatgpt2api/{plan['instance_id']}"
            compose_project = plan["compose_project"]
            admin_key = f"gbx-{secrets.token_urlsafe(32)}"
            compose_content = """services:
  app:
    image: ${CHATGPT2API_IMAGE}
    restart: unless-stopped
    ports:
      - "${CHATGPT2API_PORT}:80"
    volumes:
      - ./data:/app/data
      - ./config.json:/app/config.json
    environment:
      CHATGPT2API_AUTH_KEY: ${CHATGPT2API_AUTH_KEY}
      STORAGE_BACKEND: json
      TZ: Asia/Shanghai
    labels:
      com.genbox.managed: "true"
      com.genbox.project: "chatgpt2api"
      com.genbox.instance: ${GENBOX_INSTANCE_ID}
"""
            env_content = "\n".join([
                f"CHATGPT2API_IMAGE={plan['image']}",
                f"CHATGPT2API_PORT={plan['service_port']}",
                f"CHATGPT2API_AUTH_KEY={admin_key}",
                f"GENBOX_INSTANCE_ID={plan['instance_id']}",
                "",
            ])
            config_content = "{}\n"

            async def write_remote(path: str, content: str) -> None:
                encoded = base64.b64encode(content.encode()).decode()
                result = await connection.run(
                    f"umask 077; base64 -d > {shlex.quote(path)}",
                    input=encoded,
                    check=False,
                )
                if result.exit_status != 0:
                    raise RuntimeError("写入部署配置失败")

            image_prepare = f"docker pull {shlex.quote(plan['image'])}"
            if plan.get("clone_source_image_id"):
                source_image_id = plan["clone_source_image_id"]
                image_prepare = f"docker image inspect {shlex.quote(source_image_id)} >/dev/null"
                if plan["image"].startswith("genbox-chatgpt2api-source:"):
                    image_prepare += f" && docker tag {shlex.quote(source_image_id)} {shlex.quote(plan['image'])}"
            commands = [
                ("docker version --format '{{.Server.Version}}'", True),
                (f"test ! -e {shlex.quote(install_dir + '/.genbox-instance')} && mkdir -p {shlex.quote(install_dir + '/data')}", False),
                (image_prepare, True),
            ]
            for offset, (command, privileged) in enumerate(commands, start=1):
                step(offset, "running", DEPLOY_STEPS[offset][1])
                result = await run_command(command, privileged)
                if result.exit_status != 0:
                    raise RuntimeError(f"{DEPLOY_STEPS[offset][1]}失败")
                done_log = f"{DEPLOY_STEPS[offset][1]}完成"
                if offset == 3:
                    done_log = (
                        "复用生产镜像基线，未拉取 latest"
                        if plan.get("clone_source_image_id") else "拉取指定镜像完成"
                    )
                step(offset, "success", done_log)
            cloned_config = False
            if plan.get("clone_scope") in {"media", "working-copy"}:
                source_data = plan["clone_source_data_dir"]
                target_data = f"{install_dir}/data"
                if plan["clone_scope"] == "media":
                    clone_command = (
                        f"mkdir -p {shlex.quote(target_data + '/images')}; "
                        f"if test -d {shlex.quote(source_data + '/images')}; then "
                        f"cp -a {shlex.quote(source_data + '/images/.')} {shlex.quote(target_data + '/images/')}; fi; "
                        f"for f in image_index.json; do test ! -f {shlex.quote(source_data)}/$f || "
                        f"cp -a {shlex.quote(source_data)}/$f {shlex.quote(target_data)}/$f; done"
                    )
                else:
                    clone_command = f"cp -a {shlex.quote(source_data + '/.')} {shlex.quote(target_data + '/')}"
                cloned = await run_command(clone_command, True, timeout=900)
                if cloned.exit_status != 0:
                    raise RuntimeError("复制源实例数据失败")
                scrubbed = await run_command(
                    f"rm -f {shlex.quote(target_data)}/genbox_destination.json "
                    f"{shlex.quote(target_data)}/genbox_push_receipts.json "
                    f"{shlex.quote(target_data)}/genbox_push_schedule.json "
                    f"{shlex.quote(target_data)}/genbox_push_schedule.lease",
                    True,
                )
                if scrubbed.exit_status != 0:
                    raise RuntimeError("清理克隆推送凭据失败")
                if plan["clone_scope"] == "working-copy" and plan.get("clone_source_config_file"):
                    copied_config = await run_command(
                        f"cp {shlex.quote(plan['clone_source_config_file'])} {shlex.quote(install_dir + '/config.json')}",
                        True,
                    )
                    if copied_config.exit_status != 0:
                        raise RuntimeError("复制源实例设置失败")
                    scrub_script = _clone_config_scrub_script()
                    scrub_config = await run_command(
                        f"python3 -c {shlex.quote(scrub_script)} {shlex.quote(install_dir + '/config.json')}",
                        True,
                    )
                    if scrub_config.exit_status != 0:
                        raise RuntimeError("清理克隆设置中的自动任务失败")
                    cloned_config = True
            await write_remote(f"{install_dir}/compose.yml", compose_content)
            await write_remote(f"{install_dir}/.env", env_content)
            if not cloned_config:
                await write_remote(f"{install_dir}/config.json", config_content)
            await write_remote(f"{install_dir}/.genbox-instance", json.dumps({
                "id": plan["instance_id"], "project": compose_project, "managed": True,
            }))
            step(4, "running", DEPLOY_STEPS[4][1])
            start = await run_command(
                f"cd {shlex.quote(install_dir)} && docker compose -p {shlex.quote(compose_project)} -f compose.yml up -d",
                True,
            )
            if start.exit_status != 0:
                raise RuntimeError("启动服务失败")
            step(4, "success", "启动服务完成")
            step(5, "running", DEPLOY_STEPS[5][1])
            verify = await connection.run(
                "for i in 1 2 3 4 5 6 7 8 9 10; do "
                f"curl -fsS http://127.0.0.1:{plan['service_port']}/version >/dev/null && exit 0; sleep 3; done; exit 1",
                check=False,
            )
            if verify.exit_status != 0:
                await run_command(
                    f"cd {shlex.quote(install_dir)} && docker compose -p {shlex.quote(compose_project)} -f compose.yml down",
                    True,
                )
                raise RuntimeError("等待服务就绪失败，新实例已停止")
            step(5, "success", "等待服务就绪完成")
            state["progress"] = 100
            state["status"] = "completed"
            console_url = f"http://{request.target.host}:{plan['service_port']}"
            instance = extensions_store.upsert_instance({
                "id": plan["instance_id"], "target_id": request.target.id, "strategy": plan["strategy"],
                "deployment_mode": "compose", "compose_project": compose_project,
                "service_port": plan["service_port"], "install_dir": install_dir,
                "data_dir": f"{install_dir}/data", "image": plan["image"], "status": "running",
                "console_url": console_url, "api_url": f"{console_url}/v1", "managed": True,
                "clone_source_id": plan.get("clone_source_id", ""), "clone_scope": plan.get("clone_scope", "empty"),
            })
            self.deliveries[task_id] = admin_key
            state["result"] = {
                "url": console_url, "api_url": f"{console_url}/v1", "instance": instance.model_dump(),
                "admin_key_available": True,
            }
        except asyncio.CancelledError:
            state["status"] = "cancelled"
            state["error"] = "任务已取消"
        except Exception as exc:
            state["status"] = "failed"
            state["error"] = str(exc)[:240]
        finally:
            if connection is not None:
                connection.close()
                await connection.wait_closed()


extension_tasks = ExtensionTaskManager()


class DeploymentPlanManager:
    def __init__(self):
        self.plans: dict[str, dict] = {}

    def create(self, request: ExtensionPlanRequest, discovery: dict) -> dict:
        if not request.target.id:
            raise ValueError("请先保存 VPS 配置，再生成部署计划")
        if request.strategy == "existing":
            existing = next((item for item in discovery.get("instances", []) if item.get("id") == request.instance_id), None)
            if not existing:
                raise ValueError("请选择检测到的已有实例")
            plan_id = uuid.uuid4().hex[:16]
            plan = {
                "id": plan_id, "target_id": request.target.id, "instance_id": request.instance_id,
                "strategy": "existing", "deployment_mode": "compose", "service_port": request.service_port,
                "image": existing.get("image") or request.image,
                "compose_project": existing.get("compose_project") or "",
                "install_dir": existing.get("working_dir") or "",
                "operations": ["登记已有实例入口", "保留现有容器、配置和数据不变"],
                "safety": ["不执行任何远程写入", "不重启、不停止、不删除已有实例", "管理密钥由用户自行提供"],
                "expires_at": time.time() + 600,
            }
            self.plans[plan_id] = plan
            return {key: value for key, value in plan.items() if key != "expires_at"}
        if request.deployment_mode != "compose":
            raise ValueError("当前仅标准 Docker Compose 已达到安全执行条件")
        if not IMAGE_PATTERN.fullmatch(request.image):
            raise ValueError("镜像引用格式无效")
        environment = discovery.get("environment", {})
        if not environment.get("docker_version") or not environment.get("compose_version"):
            raise ValueError("VPS 缺少 Docker 或 Docker Compose v2")
        if request.service_port in environment.get("listening_ports", []):
            raise ValueError(f"端口 {request.service_port} 已被占用")
        if any(item.get("id") == request.instance_id for item in discovery.get("instances", [])):
            raise ValueError("实例 ID 已存在，请选择接入已有实例或更换名称")
        clone_source = None
        if request.clone_scope != "empty":
            if request.strategy != "isolated":
                raise ValueError("只有隔离测试实例允许克隆数据")
            clone_source = next((
                item for item in discovery.get("instances", []) if item.get("id") == request.clone_source_id
            ), None)
            if not clone_source or not clone_source.get("clone_available"):
                raise ValueError("所选源实例没有可读取的数据卷、配置挂载或数据大小")
            if request.image != clone_source.get("image"):
                raise ValueError("安全工作副本必须使用源实例镜像基线，请重新选择源实例")
            required_mb = int(clone_source["data_size_mb"]) + 512
            if int(environment.get("disk_free_mb") or 0) < required_mb:
                raise ValueError(f"磁盘空间不足，安全克隆至少需要 {required_mb} MB")
        source_baseline = {
            key: clone_source.get(key, "")
            for key in (
                "id", "container_id", "name", "image", "status", "ports",
                "compose_project", "working_dir", "data_dir", "config_file",
                "data_size_mb", "managed", "ownership",
            )
        } if clone_source else {}
        plan_id = uuid.uuid4().hex[:16]
        plan = {
            "id": plan_id, "target_id": request.target.id, "instance_id": request.instance_id,
            "strategy": request.strategy, "deployment_mode": request.deployment_mode,
            "service_port": request.service_port, "image": request.image,
            "compose_project": f"genbox-chatgpt2api-{request.instance_id}",
            "clone_scope": request.clone_scope,
            "clone_source_id": request.clone_source_id,
            "clone_source_data_dir": clone_source.get("data_dir", "") if clone_source else "",
            "clone_source_config_file": clone_source.get("config_file", "") if clone_source else "",
            "clone_source_image_id": clone_source.get("source_image_id", "") if clone_source else "",
            "clone_size_mb": int(clone_source.get("data_size_mb") or 0) if clone_source else 0,
            "source_baseline": source_baseline,
            "operations": [
                "创建独立实例目录和 data 目录", "写入权限为 0600 的实例配置",
                "复用生产镜像基线，不拉取 latest" if clone_source else "拉取指定镜像",
                "启动独立 Compose 项目", "验证 /version",
            ] + ([
                "复制历史媒体与索引" if request.clone_scope == "media" else "创建源实例工作副本",
                "移除克隆中的 GenBox 凭据、Push 身份、回执和调度状态；开发副本默认禁用 Push",
            ] if clone_source else []),
            "safety": ["不停止或删除任何已有容器", "端口冲突时阻止执行", "验证失败时仅停止新实例"],
            "expires_at": time.time() + 600,
        }
        self.plans[plan_id] = plan
        return {key: value for key, value in plan.items() if key != "expires_at"}

    def take(self, plan_id: str, request: ExtensionDeployRequest) -> dict:
        plan = self.plans.pop(plan_id, None)
        if not plan or plan["expires_at"] < time.time():
            raise ValueError("部署计划不存在或已过期，请重新检测")
        if plan["target_id"] != request.target.id or plan["instance_id"] != request.instance_id:
            raise ValueError("部署请求与已确认计划不一致")
        if plan["image"] != request.image or plan["service_port"] != request.target.chatgpt2api_port:
            raise ValueError("端口或镜像已变更，请重新生成计划")
        if plan.get("clone_source_id", "") != request.clone_source_id or plan.get("clone_scope", "empty") != request.clone_scope:
            raise ValueError("克隆范围已变更，请重新生成计划")
        return plan


deployment_plans = DeploymentPlanManager()


async def reset_managed_admin_key(request: ExtensionKeyResetRequest) -> dict:
    instance = extensions_store.get_instance(request.instance_id)
    if not instance or not instance.managed or instance.target_id != request.target.id:
        raise PermissionError("只能重置由 GenBox 管理且归属当前 VPS 的实例")
    if instance.deployment_mode != "compose":
        raise ValueError("当前仅支持重置 Compose 实例")
    connection, _ = await _connect(request)
    if connection is None:
        raise PermissionError("需要先确认 VPS 主机指纹")
    new_key = f"gbx-{secrets.token_urlsafe(32)}"
    backup_suffix = str(int(time.time()))
    try:
        marker = await connection.run(
            f"cat {shlex.quote(instance.install_dir + '/.genbox-instance')}", check=False,
        )
        try:
            ownership = json.loads(marker.stdout)
        except ValueError:
            ownership = {}
        if marker.exit_status != 0 or ownership.get("id") != instance.id or ownership.get("managed") is not True:
            raise PermissionError("远程实例所有权标记不匹配，已拒绝重置")
        env_path = f"{instance.install_dir}/.env"
        env_backup = f"{env_path}.bak-{backup_suffix}"
        backup = await connection.run(
            f"umask 077; cp {shlex.quote(env_path)} {shlex.quote(env_backup)}",
            check=False,
        )
        if backup.exit_status != 0:
            raise RuntimeError("创建密钥轮换快照失败")
        env_content = "\n".join([
            f"CHATGPT2API_IMAGE={instance.image}", f"CHATGPT2API_PORT={instance.service_port}",
            f"CHATGPT2API_AUTH_KEY={new_key}", f"GENBOX_INSTANCE_ID={instance.id}", "",
        ])
        for path, content in ((env_path, env_content),):
            encoded = base64.b64encode(content.encode()).decode()
            written = await connection.run(
                f"umask 077; base64 -d > {shlex.quote(path)}", input=encoded, check=False,
            )
            if written.exit_status != 0:
                raise RuntimeError("写入新管理密钥失败")
        restart = await connection.run(
            f"cd {shlex.quote(instance.install_dir)} && docker compose -p {shlex.quote(instance.compose_project)} "
            "-f compose.yml up -d --force-recreate app",
            check=False,
        )
        verified = await connection.run(
            f"cd {shlex.quote(instance.install_dir)} && set -a && . ./.env && set +a && "
            "for i in 1 2 3 4 5 6 7 8 9 10; do "
            f"curl -fsS -X POST -H \"Authorization: Bearer $CHATGPT2API_AUTH_KEY\" "
            f"http://127.0.0.1:{instance.service_port}/auth/login >/dev/null && exit 0; sleep 2; done; exit 1",
            check=False,
        )
        if restart.exit_status != 0 or verified.exit_status != 0:
            await connection.run(
                f"cp {shlex.quote(env_backup)} {shlex.quote(env_path)}; "
                f"cd {shlex.quote(instance.install_dir)} && docker compose -p {shlex.quote(instance.compose_project)} "
                "-f compose.yml up -d --force-recreate app",
                check=False,
            )
            raise RuntimeError("新密钥验证失败，已恢复原配置")
        await connection.run(f"rm -f {shlex.quote(env_backup)}", check=False)
        return {"ok": True, "instance_id": instance.id, "admin_key": new_key, "shown_once": True}
    finally:
        connection.close()
        await connection.wait_closed()
