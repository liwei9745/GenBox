import asyncio
import base64
import copy
import hmac
import hashlib
import ipaddress
import io
import json
import os
import posixpath
import re
import secrets
import shlex
import time
import threading
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from extensions.models import ExtensionDeployRequest, ExtensionKeyResetRequest, ExtensionPlanRequest, ExtensionTarget, ExtensionTestRequest, SSHCredential
from extensions.capabilities import validate_deployment_capability
from extensions.deployment_failures import deployment_failure
import extensions.store as extensions_store
from extensions.task_store import TaskStore


DEPLOY_STEPS = [
    ("connect", "连接 VPS"),
    ("docker", "检查 Docker"),
    ("prepare", "创建部署目录"),
    ("pull", "拉取 chatgpt2api 镜像"),
    ("start", "启动服务"),
    ("verify", "等待服务就绪"),
]
PHASE4_DEPLOYMENT_CONTRACT_VERSION = "phase4-v3"
_PUBLIC_INSTANCE_HANDLE_KEY = secrets.token_bytes(32)


def public_instance_handle(target_id: str, instance_id: str) -> str:
    payload = f"{target_id}\0{instance_id}".encode("utf-8")
    digest = hmac.new(_PUBLIC_INSTANCE_HANDLE_KEY, payload, hashlib.sha256).hexdigest()[:32]
    return f"i-{digest}"


def _public_access_url(value: Any) -> str:
    try:
        parsed = urlsplit(str(value or "").strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            return ""
        parsed.port
    except ValueError:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _public_project(value: Any) -> str:
    project = str(value or "").strip()
    if len(project) > 64 or re.fullmatch(r"[a-z0-9][a-z0-9-]*", project) is None:
        return "chatgpt2api"
    return project


def public_instance_access(instance: Any) -> dict[str, Any]:
    """Return the complete allowlisted, non-secret instance/access DTO."""
    status = str(getattr(instance, "status", "") or "").lower()
    return {
        "handle": public_instance_handle(
            str(getattr(instance, "target_id", "") or ""),
            str(getattr(instance, "id", "") or ""),
        ),
        "project": _public_project(getattr(instance, "project", "")),
        "managed": getattr(instance, "managed", False) is True,
        "running": status.startswith("up") or status in {"running", "healthy"},
        "console_url": _public_access_url(getattr(instance, "console_url", "")),
        "api_url": _public_access_url(getattr(instance, "api_url", "")),
    }


class SSHAuthenticationError(PermissionError):
    """A sanitized authentication failure safe to return to the browser."""

    def __init__(self, message: str, *, stage: str, auth_mode: str, facts: dict[str, bool] | None = None):
        super().__init__(message)
        self.diagnostic = {
            "code": "ssh_auth_rejected",
            "stage": stage,
            "auth_mode": auth_mode,
            "retry_safe": False,
            **(facts or {}),
        }


class SSHConnectionError(ConnectionError):
    """A fixed, non-sensitive SSH failure safe for API and task responses."""

    def __init__(self, message: str, *, code: str, stage: str):
        super().__init__(message)
        self.diagnostic = {"code": code, "stage": stage, "retry_safe": False}


class DeploymentNoTaskError(ValueError):
    """A sanitized deterministic failure that proves task creation never occurred."""

    def __init__(self, message: str, *, code: str, stage: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
        self.diagnostic = {
            "code": code,
            "stage": stage,
            "retry_safe": False,
            "task_created": False,
        }


class DeploymentResourceConflictError(DeploymentNoTaskError):
    """A deterministic conflict that does not expose remote resource details."""

    def __init__(self):
        super().__init__(
            "deployment_resource_conflict",
            code="deployment_resource_conflict",
            stage="resource_reservation",
            status_code=409,
        )


class DeploymentAttemptConflictError(ValueError):
    """A sanitized attempt-id reuse conflict safe for a synchronous response."""

    def __init__(self):
        super().__init__("deployment_attempt_conflict")
        self.diagnostic = {
            "code": "deployment_attempt_conflict",
            "stage": "deployment_attempt",
            "retry_safe": False,
        }


class DeploymentPlanConfirmationError(DeploymentNoTaskError):
    """A sanitized, field-specific failure before task or remote side effects."""

    def __init__(self, message: str, *, code: str):
        super().__init__(message, code=code, stage="plan_confirmation")


class DeploymentPlanUnavailableError(DeploymentNoTaskError):
    def __init__(self):
        super().__init__(
            "deployment_plan_unavailable",
            code="deployment_plan_unavailable",
            stage="plan_lease",
        )


class DeploymentSnapshotChangedError(DeploymentNoTaskError):
    _CATEGORIES = {
        "plan_snapshot", "stable_snapshot", "capacity_threshold", "path_requirements",
        "existing_instance", "requested_port", "target_instance", "listener_evidence",
    }

    def __init__(self, *, category: str = "stable_snapshot", changed_fields: list[str] | None = None):
        super().__init__(
            "deployment_snapshot_changed",
            code="deployment_snapshot_changed",
            stage="fresh_discovery",
        )
        safe_category = category if category in self._CATEGORIES else "stable_snapshot"
        safe_fields = sorted({
            field for field in (changed_fields or [])
            if isinstance(field, str) and re.fullmatch(r"[a-z][a-z0-9_.-]{0,79}", field)
        })[:24]
        self.diagnostic["snapshot_category"] = safe_category
        if safe_fields:
            self.diagnostic["changed_fields"] = safe_fields


class DeploymentResourceReservations:
    """Process-local claims; the atomic remote directory claim remains the restart guard."""

    def __init__(self):
        self.lock = threading.RLock()
        self.claims: dict[tuple[Any, ...], str] = {}
        self.reservations: dict[str, frozenset[tuple[Any, ...]]] = {}

    @staticmethod
    def _normalized_host(value: Any) -> str:
        host = str(value or "").strip().lower().rstrip(".")
        candidate = host[1:-1] if host.startswith("[") and host.endswith("]") else host
        try:
            return ipaddress.ip_address(candidate).compressed
        except ValueError:
            return host

    @staticmethod
    def _normalized_path(value: Any) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        return posixpath.normpath("/" + raw.lstrip("/"))

    @classmethod
    def _claims_for(cls, plan: dict) -> frozenset[tuple[Any, ...]]:
        target_scopes = {
            ("target_id", str(plan.get("target_id") or "").strip().casefold()),
            ("endpoint", cls._normalized_host(plan.get("host")), int(plan.get("ssh_port") or 0)),
            ("host_key", str(plan.get("host_fingerprint") or "").strip()),
        }
        target_scopes = {scope for scope in target_scopes if any(scope[1:])}
        resources = {
            ("instance_id", str(plan.get("instance_id") or "").strip()),
            ("install_dir", cls._normalized_path(plan.get("install_dir"))),
            ("compose_project", str(plan.get("compose_project") or "").strip().casefold()),
            ("service_port", int(plan.get("service_port") or 0)),
        }
        resources = {resource for resource in resources if resource[1] not in {"", 0}}
        return frozenset((scope, resource) for scope in target_scopes for resource in resources)

    def acquire(self, plan: dict) -> str:
        claims = self._claims_for(plan)
        token = uuid.uuid4().hex
        with self.lock:
            if any(claim in self.claims for claim in claims):
                raise DeploymentResourceConflictError()
            for claim in claims:
                self.claims[claim] = token
            self.reservations[token] = claims
        return token

    def release(self, token: str) -> None:
        if not token:
            return
        with self.lock:
            claims = self.reservations.pop(token, frozenset())
            for claim in claims:
                if self.claims.get(claim) == token:
                    self.claims.pop(claim, None)

    @property
    def active_count(self) -> int:
        with self.lock:
            return len(self.reservations)


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


def _authentication_kind(credential: SSHCredential) -> str:
    return "private_key" if credential.private_key else "password"


def _elevation_contract(credential: SSHCredential) -> str:
    return credential.elevation


def _elevation_password(credential: SSHCredential) -> str:
    if credential.sudo_password:
        return credential.sudo_password
    if credential.reuse_ssh_password and credential.password:
        return credential.password
    return ""


def _elevated_command(command: str, credential: SSHCredential, privileges: dict[str, Any]) -> tuple[str, str]:
    if privileges.get("is_root"):
        return command, ""
    contract = privileges.get("elevation_contract")
    if contract == "passwordless_sudo" and privileges.get("passwordless_sudo"):
        return f"sudo -n sh -lc {shlex.quote(command)}", ""
    if contract == "password_sudo" and privileges.get("password_sudo"):
        password = _elevation_password(credential)
        if password:
            return _password_sudo_command(command), password + "\n"
    raise PermissionError("当前请求没有经过验证的管理员提权能力")


async def _diagnose_privileges(connection, credential: SSHCredential) -> dict[str, Any]:
    user_id = (await connection.run("id -u", check=True)).stdout.strip()
    is_root = user_id == "0"
    auth_kind = _authentication_kind(credential)
    contract = _elevation_contract(credential)
    docker = await connection.run("docker version >/dev/null 2>&1", check=False)
    docker_access = docker.exit_status == 0
    passwordless_sudo = False
    password_sudo = False
    sudo_password_supplied = bool(_elevation_password(credential))
    elevated_docker_access = False

    if is_root:
        elevated_docker_access = docker_access
    else:
        sudo_probe = await connection.run("sudo -n true >/dev/null 2>&1", check=False)
        passwordless_sudo = sudo_probe.exit_status == 0
        if contract == "password_sudo" and sudo_password_supplied:
            password_probe = await connection.run(
                _password_sudo_command("true"),
                input=_elevation_password(credential) + "\n",
                check=False,
            )
            password_sudo = password_probe.exit_status == 0

        if contract == "passwordless_sudo" and passwordless_sudo:
            elevated_docker = await connection.run(
                "sudo -n sh -lc 'docker version >/dev/null 2>&1'",
                check=False,
            )
            elevated_docker_access = elevated_docker.exit_status == 0
        elif contract == "password_sudo" and password_sudo:
            elevated_docker = await connection.run(
                _password_sudo_command("docker version >/dev/null 2>&1"),
                input=_elevation_password(credential) + "\n",
                check=False,
            )
            elevated_docker_access = elevated_docker.exit_status == 0

    can_admin = is_root or (
        contract == "passwordless_sudo" and passwordless_sudo
    ) or (
        contract == "password_sudo" and password_sudo
    )
    contract_verified = is_root or contract == "none" or (
        contract == "passwordless_sudo" and passwordless_sudo
    ) or (
        contract == "password_sudo" and password_sudo
    )
    can_deploy = contract_verified and (docker_access or elevated_docker_access)
    if is_root and can_deploy:
        diagnostic_code = "uid_0"
    elif is_root:
        diagnostic_code = "docker_unavailable"
    elif contract == "passwordless_sudo" and passwordless_sudo and can_deploy:
        diagnostic_code = "passwordless_sudo"
    elif contract == "password_sudo" and password_sudo and can_deploy:
        diagnostic_code = "password_sudo"
    elif contract == "password_sudo" and not sudo_password_supplied:
        diagnostic_code = "sudo_password_required"
    elif contract == "password_sudo" and not password_sudo:
        diagnostic_code = "sudo_password_rejected"
    elif contract == "passwordless_sudo" and not passwordless_sudo:
        diagnostic_code = "passwordless_sudo_unavailable"
    elif docker_access:
        diagnostic_code = "direct_docker"
    elif not passwordless_sudo:
        diagnostic_code = "no_sudo_or_docker"
    else:
        diagnostic_code = "docker_unavailable"
    return {
        "auth_kind": auth_kind,
        "elevation_contract": contract,
        "is_root": is_root,
        "docker_access": docker_access,
        "elevated_docker_access": elevated_docker_access,
        "passwordless_sudo": passwordless_sudo,
        "password_sudo": password_sudo,
        "sudo_password_supplied": sudo_password_supplied,
        "can_admin": can_admin,
        "can_deploy": can_deploy,
        "diagnostic_code": diagnostic_code,
    }


async def _connect(request: ExtensionTestRequest | ExtensionDeployRequest):
    has_password = bool(request.credential.password)
    has_private_key = bool(request.credential.private_key)
    if has_password == has_private_key:
        raise ValueError("请选择且只选择一种 SSH 凭据：密码或私钥")
    try:
        import asyncssh
    except ImportError as exc:
        raise RuntimeError("缺少 asyncssh 依赖，请重新安装 requirements.txt") from exc
    expected = request.expected_host_key or request.target.host_key

    class _FingerprintClient(asyncssh.SSHClient):
        def __init__(self, expected_fingerprint: str = "", password: str = ""):
            self.expected_fingerprint = expected_fingerprint
            self._password = password
            self.fingerprint = ""
            self.transport_connected = False
            self.host_key_verified = False
            self.authentication_started = False
            self.authentication_completed = False
            self.connection_lost_during_auth = False
            self.password_requested = False

        def connection_made(self, conn: Any) -> None:
            self.transport_connected = True

        def begin_auth(self, username: str) -> None:
            self.authentication_started = True

        def auth_completed(self) -> None:
            self.authentication_completed = True

        def connection_lost(self, exc: Exception | None) -> None:
            self.connection_lost_during_auth = bool(exc) and not self.authentication_completed

        def password_auth_requested(self) -> str | None:
            if self.password_requested or not self._password:
                return None
            self.password_requested = True
            return self._password

        def validate_host_public_key(self, host: str, addr: str, port: int, key: Any) -> bool:
            self.fingerprint = _fingerprint(key)
            self.host_key_verified = bool(self.expected_fingerprint) and hmac.compare_digest(
                self.expected_fingerprint, self.fingerprint,
            )
            return self.host_key_verified

    base_kwargs: dict[str, Any] = {
        "host": request.target.host,
        "port": request.target.port,
        "username": request.target.username,
        # An empty known-hosts list deliberately invokes our fingerprint callback.
        # `known_hosts=None` disables host-key validation entirely.
        "known_hosts": b"",
        "connect_timeout": 15,
        "config": [],
        "agent_path": None,
        # None disables AsyncSSH's fallback to ~/.ssh keys and SSH agents.
        "client_keys": None,
    }

    if not expected:
        return None, await probe_host_key(request.target)

    trusted_client = _FingerprintClient(
        expected,
        request.credential.password if not request.credential.private_key else "",
    )
    kwargs = {**base_kwargs, "client_factory": lambda: trusted_client}
    if request.credential.private_key:
        try:
            imported_key = asyncssh.import_private_key(
                request.credential.private_key,
                request.credential.passphrase or None,
            )
        except Exception as exc:
            raise SSHConnectionError(
                "SSH 私钥或私钥口令无法解析，请重新检查后再试。",
                code="ssh_private_key_invalid",
                stage="credential_validation",
            ) from exc
        kwargs["client_keys"] = [imported_key]
        kwargs["preferred_auth"] = ["publickey"]
        kwargs["kbdint_auth"] = False
        kwargs["password_auth"] = False
    else:
        kwargs["preferred_auth"] = ["password"]
        kwargs["kbdint_auth"] = False
        kwargs["password_auth"] = True
    try:
        connection = await asyncssh.connect(**kwargs)
    except asyncssh.PermissionDenied as exc:
        if trusted_client.authentication_completed:
            stage = "authentication_completed"
        elif trusted_client.password_requested:
            stage = "password_requested"
        elif trusted_client.authentication_started:
            stage = "authentication_started"
        elif trusted_client.host_key_verified:
            stage = "host_key_verified"
        elif trusted_client.transport_connected:
            stage = "transport_connected"
        else:
            stage = "connection_started"
        if request.credential.private_key:
            detail = (
                "VPS 拒绝了本次 SSH 私钥认证。请确认公钥已加入目标账号、私钥与口令匹配，"
                "并避免连续重试。"
            )
        else:
            stage_detail = (
                "本次诊断显示 AsyncSSH 已请求并取得你输入的密码，但这不等于服务器已经收到或完成校验。"
                if trusted_client.password_requested else
                "本次诊断显示连接在 AsyncSSH 取用密码前结束。"
            )
            detail = (
                "VPS 拒绝了本次 SSH 密码认证，但这条结果不能单独证明密码错误。"
                "也可能是账号或 PAM 策略、登录限制，或 SSH 客户端兼容问题。"
                f"{stage_detail}"
                "如果同一账号和密码能通过系统 ssh 登录，请查看 VPS 的 sshd/PAM 日志，"
                "或改用 GenBox 专用 SSH 私钥；请勿连续重试。"
            )
        raise SSHAuthenticationError(
            detail,
            stage=stage,
            auth_mode="publickey" if request.credential.private_key else "password",
            facts={
                "host_key_verified": trusted_client.host_key_verified,
                "password_requested": trusted_client.password_requested,
                "connection_lost_during_auth": trusted_client.connection_lost_during_auth,
            },
        ) from exc
    except asyncssh.HostKeyNotVerifiable as exc:
        raise SSHConnectionError(
            "VPS 当前 SSH 主机指纹与已确认记录不一致，已拒绝继续连接。",
            code="ssh_host_key_mismatch",
            stage="host_key_verification",
        ) from exc
    except (TimeoutError, asyncio.TimeoutError) as exc:
        raise SSHConnectionError(
            "SSH 连接超时，请确认 VPS 在线且 SSH 端口可访问。",
            code="ssh_transport_timeout",
            stage="transport_connect",
        ) from exc
    except OSError as exc:
        raise SSHConnectionError(
            "SSH 网络连接未建立，请检查地址、端口和本机网络。",
            code="ssh_transport_failed",
            stage="transport_connect",
        ) from exc
    except Exception as exc:
        raise SSHConnectionError(
            "SSH 客户端未完成连接，原始错误已隐藏。请勿连续重试。",
            code="ssh_protocol_failed",
            stage="ssh_protocol",
        ) from exc
    return connection, trusted_client.fingerprint


async def probe_host_key(target: ExtensionTarget) -> str:
    """Read a server public SSH identity without attempting authentication."""
    try:
        import asyncssh
    except ImportError as exc:
        raise SSHConnectionError(
            "缺少 SSH 组件，无法读取 VPS 主机指纹。",
            code="ssh_component_missing",
            stage="host_key_probe",
        ) from exc

    try:
        # AsyncSSH's dedicated helper stops after SSH key exchange, returns the
        # presented public host key, aborts the transport, and never begins
        # user authentication. The result is only a candidate until the user
        # verifies it and the confirm endpoint re-probes the same identity.
        key = await asyncio.wait_for(
            asyncssh.get_server_host_key(
                target.host,
                target.port,
                config=[],
            ),
            timeout=15,
        )
    except (TimeoutError, asyncio.TimeoutError) as exc:
        raise SSHConnectionError(
            "读取 VPS 主机指纹超时，请确认 SSH 地址和端口可访问。",
            code="ssh_host_key_timeout",
            stage="host_key_probe",
        ) from exc
    except OSError as exc:
        raise SSHConnectionError(
            "无法连接 VPS 的 SSH 端口，请检查网络、地址和端口。",
            code="ssh_transport_failed",
            stage="host_key_probe",
        ) from exc
    except Exception as exc:
        raise SSHConnectionError(
            "读取 VPS 主机指纹时连接未完成，原始错误已隐藏。",
            code="ssh_host_key_probe_failed",
            stage="host_key_probe",
        ) from exc
    if key is None:
        raise SSHConnectionError(
            "VPS 未按预期返回可确认的 SSH 主机指纹。",
            code="ssh_host_key_unavailable",
            stage="host_key_probe",
        )
    return _fingerprint(key)


async def test_connection(request: ExtensionTestRequest) -> dict:
    connection, fingerprint = await _connect(request)
    if connection is None:
        return {"ok": False, "needs_host_key_confirmation": True, "host_key": fingerprint}
    try:
        result = await asyncio.wait_for(connection.run("printf genbox-connected", check=True), timeout=15)
        privileges = await _diagnose_privileges(connection, request.credential)
        return {
            "ok": result.stdout == "genbox-connected",
            "host_key": fingerprint,
            "privileges": privileges,
        }
    finally:
        connection.close()
        await connection.wait_closed()


class ExtensionTaskManager:
    def __init__(
        self,
        store: TaskStore | None = None,
        store_path=None,
        resource_reservations: DeploymentResourceReservations | None = None,
    ):
        self.store = store or TaskStore(store_path)
        self.lock = threading.RLock()
        self.tasks: dict[str, dict] = {task["id"]: task for task in self.store.load() if task.get("id")}
        self.runners: dict[str, asyncio.Task] = {}
        self.deliveries: dict[str, dict[str, Any]] = {}
        self.resource_reservations = resource_reservations or DeploymentResourceReservations()
        self.task_reservations: dict[str, str] = {}
        self.deployment_attempts: dict[str, dict[str, Any]] = {}
        self.attempt_tasks: dict[str, dict[str, str]] = {}
        self._recover_tasks()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _persist(self) -> None:
        with self.lock:
            self._trim_terminal_tasks()
            self.store.save(list(self.tasks.values()))

    def _trim_terminal_tasks(self) -> None:
        terminal = [task for task in self.tasks.values() if task.get("status") not in {"queued", "running"}]
        terminal.sort(key=lambda task: (task.get("updated_at", ""), task.get("id", "")), reverse=True)
        for task in terminal[50:]:
            task_id = task["id"]
            self.tasks.pop(task_id, None)
            self.deliveries.pop(task_id, None)
            self.runners.pop(task_id, None)
            for attempt_id, record in list(self.attempt_tasks.items()):
                if record.get("task_id") == task_id:
                    self.attempt_tasks.pop(attempt_id, None)
        for task_id, runner in list(self.runners.items()):
            if runner.done():
                self.runners.pop(task_id, None)

    def _recover_tasks(self) -> None:
        with self.lock:
            changed = False
            for state in self.tasks.values():
                if state.get("status") in {"queued", "running"}:
                    state["status"] = "interrupted"
                    state["recovery_action"] = TaskStore.interrupted_recovery_action(state.get("phase"))
                    state["updated_at"] = self._now()
                    changed = True
            before = len(self.tasks)
            self._trim_terminal_tasks()
            if changed or len(self.tasks) != before:
                self.store.save(list(self.tasks.values()))

    @staticmethod
    def _deployment_context_fingerprint(request: ExtensionDeployRequest) -> str:
        context = {
            "project_id": request.project_id,
            "confirmed_plan_id": request.confirmed_plan_id,
            "target_id": request.target.id,
            "host": request.target.host,
            "ssh_port": request.target.port,
            "username": request.target.username.strip(),
            "host_fingerprint": request.expected_host_key or request.target.host_key,
            "auth_kind": _authentication_kind(request.credential),
            "elevation_contract": _elevation_contract(request.credential),
            "instance_id": request.instance_id,
            "strategy": request.strategy,
            "deployment_mode": request.deployment_mode,
            "service_port": request.service_port,
            "image": request.image,
            "clone_source_id": request.clone_source_id,
            "clone_scope": request.clone_scope,
        }
        encoded = json.dumps(context, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _existing_attempt_task_locked(self, attempt_id: str, context_fingerprint: str) -> str | None:
        record = self.attempt_tasks.get(attempt_id)
        if not record:
            return None
        task_id = record.get("task_id", "")
        if task_id not in self.tasks:
            self.attempt_tasks.pop(attempt_id, None)
            return None
        if not hmac.compare_digest(record.get("context_fingerprint", ""), context_fingerprint):
            raise DeploymentAttemptConflictError()
        return task_id

    async def create(self, request: ExtensionDeployRequest) -> str:
        context_fingerprint = self._deployment_context_fingerprint(request)
        loop = asyncio.get_running_loop()
        owner = False
        with self.lock:
            existing_task_id = self._existing_attempt_task_locked(
                request.deployment_attempt_id,
                context_fingerprint,
            )
            if existing_task_id:
                return existing_task_id
            attempt = self.deployment_attempts.get(request.deployment_attempt_id)
            if attempt:
                if not hmac.compare_digest(attempt["context_fingerprint"], context_fingerprint):
                    raise DeploymentAttemptConflictError()
                future = attempt["future"]
            else:
                future = loop.create_future()
                future.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
                self.deployment_attempts[request.deployment_attempt_id] = {
                    "context_fingerprint": context_fingerprint,
                    "future": future,
                }
                owner = True
        if not owner:
            return await asyncio.shield(future)
        try:
            task_id = await self._create_owned(request, context_fingerprint)
        except BaseException as exc:
            if not future.done():
                future.set_exception(exc)
            raise
        else:
            if not future.done():
                future.set_result(task_id)
            return task_id
        finally:
            with self.lock:
                if self.deployment_attempts.get(request.deployment_attempt_id, {}).get("future") is future:
                    self.deployment_attempts.pop(request.deployment_attempt_id, None)

    async def _create_owned(self, request: ExtensionDeployRequest, context_fingerprint: str) -> str:
        request = deployment_plans.resolve_public_references(request)
        validate_deployment_capability(request.project_id, request.strategy, request.deployment_mode)
        lease_token, leased_plan = deployment_plans.lease(request.confirmed_plan_id, request)
        reservation_token = ""
        try:
            from extensions.discovery import discover_environment

            fresh_discovery = await discover_environment(
                request,
                path_checks=leased_plan.get("path_requirements", {}),
            )
            deployment_plans.validate_fresh_snapshot(leased_plan, fresh_discovery)
            reservation_token = self.resource_reservations.acquire(leased_plan)
            plan = deployment_plans.consume_lease(request.confirmed_plan_id, lease_token, request)
        except BaseException:
            self.resource_reservations.release(reservation_token)
            deployment_plans.release(request.confirmed_plan_id, lease_token)
            raise

        task_id = ""
        runner = None
        previous_tasks = None
        previous_runners = None
        previous_deliveries = None
        previous_task_reservations = None
        previous_attempt_tasks = None
        try:
            task_id = uuid.uuid4().hex[:12]
            with self.lock:
                previous_tasks = copy.deepcopy(self.tasks)
                previous_runners = dict(self.runners)
                previous_deliveries = dict(self.deliveries)
                previous_task_reservations = dict(self.task_reservations)
                previous_attempt_tasks = copy.deepcopy(self.attempt_tasks)
                self.tasks[task_id] = TaskStore.public_task({
                    "id": task_id, "status": "queued", "phase": "connect", "progress": 0,
                    "steps": [{"id": key, "label": label, "status": "pending"} for key, label in DEPLOY_STEPS],
                    "created_at": self._now(), "updated_at": self._now(), "recovery_action": None,
                    "failed_phase": None, "error_code": None,
                    "evidence_manifest": copy.deepcopy(plan.get("evidence_manifest")),
                })
                self.task_reservations[task_id] = reservation_token
                self._persist()
                self.attempt_tasks[request.deployment_attempt_id] = {
                    "context_fingerprint": context_fingerprint,
                    "task_id": task_id,
                }
                runner = asyncio.create_task(self._run(task_id, request, plan))
                self.runners[task_id] = runner
                runner.add_done_callback(lambda completed: self._discard_done_runner(task_id, completed))
        except BaseException:
            with self.lock:
                if previous_tasks is not None:
                    self.tasks = previous_tasks
                    self.runners = previous_runners or {}
                    self.deliveries = previous_deliveries or {}
                    self.task_reservations = previous_task_reservations or {}
                    self.attempt_tasks = previous_attempt_tasks or {}
                if runner is not None:
                    runner.cancel()
            self.resource_reservations.release(reservation_token)
            raise
        return task_id

    def _discard_done_runner(self, task_id: str, runner: asyncio.Task) -> None:
        reservation_token = ""
        with self.lock:
            if self.runners.get(task_id) is runner and runner.done():
                self.runners.pop(task_id, None)
                reservation_token = self.task_reservations.pop(task_id, "")
        self.resource_reservations.release(reservation_token)

    def _release_task_reservation(self, task_id: str) -> None:
        # Never hold the task lock while taking the reservation lock.
        with self.lock:
            reservation_token = self.task_reservations.pop(task_id, "")
        self.resource_reservations.release(reservation_token)

    def get(self, task_id: str) -> dict | None:
        with self.lock:
            state = self.tasks.get(task_id)
            if not state:
                return None
            return TaskStore.public_task(state)

    def cancel(self, task_id: str) -> bool:
        with self.lock:
            state = self.tasks.get(task_id)
            if not state or state.get("status") not in {"queued", "running"}:
                return False
            runner = self.runners.get(task_id)
            if not runner or runner.done():
                return False
            # Stop the runner first: a failed public-state save must never leave
            # the credential-bearing remote workflow executing.
            runner.cancel()
            state["status"] = "cancelled"
            state.pop("result", None)
            state["failed_phase"] = None
            state["error_code"] = None
            state["recovery_action"] = None
            self.deliveries.pop(task_id, None)
            state["updated_at"] = self._now()
            self._persist()
            return True

    def take_delivery(self, task_id: str) -> dict[str, Any] | None:
        with self.lock:
            state = self.tasks.get(task_id)
            if not state or state.get("status") != "completed":
                self.deliveries.pop(task_id, None)
                return None
            delivery = self.deliveries.get(task_id)
            if not isinstance(delivery, dict):
                return None
            previous_recovery_action = state.get("recovery_action")
            previous_updated_at = state.get("updated_at")
            self.deliveries.pop(task_id, None)
            state["recovery_action"] = (
                "reverify_ownership_and_rotate_admin_key"
                if delivery.get("admin_key") else None
            )
            state["updated_at"] = self._now()
            try:
                self._persist()
            except BaseException:
                state["recovery_action"] = previous_recovery_action
                state["updated_at"] = previous_updated_at
                self.deliveries[task_id] = delivery
                raise
            return copy.deepcopy(delivery)

    def list_summary(self) -> dict:
        with self.lock:
            tasks = sorted(self.tasks.values(), key=lambda task: (task.get("updated_at", ""), task.get("id", "")), reverse=True)
            active = next((task["id"] for task in tasks if task.get("status") in {"queued", "running"}), None)
            public_tasks = [TaskStore.public_task(task) for task in tasks]
            return {
                "tasks": public_tasks,
                "active_task_id": active,
                "latest_task_id": tasks[0]["id"] if tasks else None,
                "store_warning": self.store.warning,
            }

    async def _run(self, task_id: str, request: ExtensionDeployRequest, plan: dict) -> None:
        with self.lock:
            state = self.tasks[task_id]
        connection = None
        failure_key = "connection_failed"

        def step(index: int, status: str, log: str = ""):
            with self.lock:
                state["phase"] = DEPLOY_STEPS[index][0]
                state["steps"][index]["status"] = status
                state["progress"] = int(index / len(DEPLOY_STEPS) * 100)
                state["updated_at"] = self._now()
                self._persist()

        try:
            with self.lock:
                state["status"] = "running"
                state["updated_at"] = self._now()
                self._persist()
            step(0, "running", "正在建立安全 SSH 连接")
            validate_deployment_capability(request.project_id, request.strategy, request.deployment_mode)
            connection, _fingerprint = await _connect(request)
            if connection is None:
                failure_key = "host_key_confirmation_required"
                raise PermissionError("需要先确认 VPS 主机指纹")
            step(0, "success", "SSH 连接成功")

            home_dir = (await connection.run("printf %s \"$HOME\"", check=True)).stdout.strip()
            planned_home_dir = plan.get("execution_snapshot", {}).get("environment", {}).get("home_dir")
            if planned_home_dir and home_dir != planned_home_dir:
                raise PermissionError("远程用户主目录已变化，请重新发现并生成计划")
            failure_key = "docker_unavailable"
            privileges = await _diagnose_privileges(connection, request.credential)
            verified_capability = plan.get("verified_capability")
            if isinstance(verified_capability, dict) and verified_capability.get("diagnostic_code") != "legacy_discovery":
                bound_fields = (
                    "is_root", "docker_access", "elevated_docker_access",
                    "passwordless_sudo", "password_sudo", "can_admin", "can_deploy",
                    "diagnostic_code",
                )
                if any(verified_capability.get(key) != privileges.get(key) for key in bound_fields):
                    raise PermissionError("远程部署能力已变化，请重新检测并生成计划")
            if not privileges["can_deploy"]:
                raise PermissionError("当前用户没有 Docker 访问权限，且无法提权")
            if plan.get("clone_scope") in {"media", "working-copy"} and not privileges["can_admin"]:
                raise PermissionError("复制源实例数据需要已验证的管理员提权能力")

            async def run_command(command: str, privilege: str, timeout: int = 300):
                if privilege == "none" or (privilege == "docker" and privileges["docker_access"]):
                    return await asyncio.wait_for(connection.run(command, check=False), timeout=timeout)
                wrapped, input_data = _elevated_command(command, request.credential, privileges)
                return await asyncio.wait_for(
                    connection.run(wrapped, input=input_data, check=False),
                    timeout=timeout,
                )

            if plan["strategy"] == "existing":
                for index in range(1, len(DEPLOY_STEPS)):
                    step(index, "success", "接入已有实例：未执行远程变更")
                existing_snapshot = plan.get("existing_snapshot", {})
                console_url = f"http://{request.target.host}:{plan['service_port']}"
                failure_key = "instance_registration_failed"
                instance = extensions_store.upsert_instance({
                    "id": plan["instance_id"], "target_id": request.target.id, "project": plan["project_id"], "strategy": "existing",
                    "deployment_mode": "compose", "compose_project": existing_snapshot.get("compose_project") or plan.get("compose_project", ""),
                    "service_port": plan["service_port"], "install_dir": existing_snapshot.get("working_dir") or plan.get("install_dir", ""),
                    "data_dir": existing_snapshot.get("data_dir") or "", "image": existing_snapshot.get("image") or plan["image"],
                    "status": existing_snapshot.get("status") or "unknown",
                    "console_url": console_url, "api_url": f"{console_url}/v1",
                    "managed": bool(existing_snapshot.get("managed")),
                    "ownership": existing_snapshot.get("ownership") or "",
                    "container_id": existing_snapshot.get("container_id") or "",
                    "container_name": existing_snapshot.get("name") or "",
                })
                with self.lock:
                    if state.get("status") == "cancelled":
                        raise asyncio.CancelledError
                    state["progress"] = 100
                    state["status"] = "completed"
                    self.deliveries[task_id] = {
                        "admin_key": None,
                        "instance": public_instance_access(instance),
                    }
                    state["recovery_action"] = None
                    state["updated_at"] = self._now()
                    self._persist()
                return

            install_dir = plan["install_dir"]
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
      com.genbox.project: "${GENBOX_PROJECT_ID}"
      com.genbox.instance: ${GENBOX_INSTANCE_ID}
"""
            env_content = "\n".join([
                f"CHATGPT2API_IMAGE={plan['image']}",
                f"CHATGPT2API_PORT={plan['service_port']}",
                f"CHATGPT2API_AUTH_KEY={admin_key}",
                f"GENBOX_INSTANCE_ID={plan['instance_id']}",
                f"GENBOX_PROJECT_ID={plan['project_id']}",
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
            install_parent = posixpath.dirname(install_dir.rstrip("/"))
            commands = [
                ("docker version --format '{{.Server.Version}}'", "docker"),
                (
                    f"umask 077; mkdir -p {shlex.quote(install_parent)} "
                    f"&& mkdir {shlex.quote(install_dir)}",
                    "none",
                ),
                (image_prepare, "docker"),
            ]
            ownership_marker = {
                "id": plan["instance_id"], "project": compose_project, "managed": True,
            }

            async def verify_ownership_marker() -> None:
                script = (
                    "import json,sys; "
                    "p=json.load(open(sys.argv[1],encoding='utf-8')); "
                    "raise SystemExit(0 if p=={'id':sys.argv[2],'project':sys.argv[3],'managed':True} else 1)"
                )
                marker = await connection.run(
                    f"python3 -c {shlex.quote(script)} "
                    f"{shlex.quote(install_dir + '/.genbox-instance')} "
                    f"{shlex.quote(plan['instance_id'])} {shlex.quote(compose_project)}",
                    check=False,
                )
                if marker.exit_status != 0:
                    raise PermissionError("deployment_ownership_marker_mismatch")

            for offset, (command, privilege) in enumerate(commands, start=1):
                failure_key = {1: "docker_unavailable", 2: "preparation_failed", 3: "image_prepare_failed"}[offset]
                step(offset, "running", DEPLOY_STEPS[offset][1])
                result = await run_command(command, privilege)
                if result.exit_status != 0:
                    raise RuntimeError(f"{DEPLOY_STEPS[offset][1]}失败")
                done_log = f"{DEPLOY_STEPS[offset][1]}完成"
                if offset == 2:
                    await write_remote(
                        f"{install_dir}/.genbox-instance",
                        json.dumps(ownership_marker, separators=(",", ":")),
                    )
                    await verify_ownership_marker()
                    data_created = await run_command(
                        f"umask 077; mkdir {shlex.quote(install_dir + '/data')}",
                        "none",
                    )
                    if data_created.exit_status != 0:
                        raise RuntimeError("deployment_data_directory_failed")
                if offset == 3:
                    done_log = (
                        "复用生产镜像基线，未拉取 latest"
                        if plan.get("clone_source_image_id") else "拉取指定镜像完成"
                    )
                step(offset, "success", done_log)
            cloned_config = False
            failure_key = "preparation_failed"
            await verify_ownership_marker()
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
                cloned = await run_command(clone_command, "admin", timeout=900)
                if cloned.exit_status != 0:
                    raise RuntimeError("复制源实例数据失败")
                scrubbed = await run_command(
                    f"rm -f {shlex.quote(target_data)}/genbox_destination.json "
                    f"{shlex.quote(target_data)}/genbox_push_receipts.json "
                    f"{shlex.quote(target_data)}/genbox_push_schedule.json "
                    f"{shlex.quote(target_data)}/genbox_push_schedule.lease",
                    "admin",
                )
                if scrubbed.exit_status != 0:
                    raise RuntimeError("清理克隆推送凭据失败")
                if plan["clone_scope"] == "working-copy" and plan.get("clone_source_config_file"):
                    copied_config = await run_command(
                        f"cp {shlex.quote(plan['clone_source_config_file'])} {shlex.quote(install_dir + '/config.json')}",
                        "admin",
                    )
                    if copied_config.exit_status != 0:
                        raise RuntimeError("复制源实例设置失败")
                    scrub_script = _clone_config_scrub_script()
                    scrub_config = await run_command(
                        f"python3 -c {shlex.quote(scrub_script)} {shlex.quote(install_dir + '/config.json')}",
                        "admin",
                    )
                    if scrub_config.exit_status != 0:
                        raise RuntimeError("清理克隆设置中的自动任务失败")
                    cloned_config = True
            await verify_ownership_marker()
            await write_remote(f"{install_dir}/compose.yml", compose_content)
            await write_remote(f"{install_dir}/.env", env_content)
            if not cloned_config:
                await write_remote(f"{install_dir}/config.json", config_content)
            failure_key = "service_start_failed"
            step(4, "running", DEPLOY_STEPS[4][1])
            await verify_ownership_marker()
            start = await run_command(
                f"cd {shlex.quote(install_dir)} && docker compose -p {shlex.quote(compose_project)} -f compose.yml up -d",
                "docker",
            )
            if start.exit_status != 0:
                raise RuntimeError("启动服务失败")
            step(4, "success", "启动服务完成")
            failure_key = "service_verification_failed"
            step(5, "running", DEPLOY_STEPS[5][1])
            verify = await connection.run(
                "for i in 1 2 3 4 5 6 7 8 9 10; do "
                f"curl -fsS http://127.0.0.1:{plan['service_port']}/version >/dev/null && exit 0; sleep 3; done; exit 1",
                check=False,
            )
            if verify.exit_status != 0:
                try:
                    await verify_ownership_marker()
                    stopped = await run_command(
                        f"cd {shlex.quote(install_dir)} && docker compose -p {shlex.quote(compose_project)} -f compose.yml down",
                        "docker",
                    )
                    if stopped.exit_status != 0:
                        failure_key = "service_verification_stop_unconfirmed"
                except asyncio.CancelledError:
                    raise
                except Exception:
                    failure_key = "service_verification_stop_unconfirmed"
                raise RuntimeError("等待服务就绪失败，新实例已停止")
            step(5, "success", "等待服务就绪完成")
            console_url = f"http://{request.target.host}:{plan['service_port']}"
            failure_key = "instance_registration_failed"
            instance = extensions_store.upsert_instance({
                "id": plan["instance_id"], "target_id": request.target.id, "project": plan["project_id"], "strategy": plan["strategy"],
                "deployment_mode": "compose", "compose_project": compose_project,
                "service_port": plan["service_port"], "install_dir": install_dir,
                "data_dir": f"{install_dir}/data", "image": plan["image"], "status": "running",
                "console_url": console_url, "api_url": f"{console_url}/v1", "managed": True, "ownership": "managed",
                "clone_source_id": plan.get("clone_source_id", ""), "clone_scope": plan.get("clone_scope", "empty"),
            })
            with self.lock:
                if state.get("status") == "cancelled":
                    raise asyncio.CancelledError
                state["progress"] = 100
                state["status"] = "completed"
                self.deliveries[task_id] = {
                    "admin_key": admin_key,
                    "instance": public_instance_access(instance),
                }
                state["recovery_action"] = "reverify_ownership_and_rotate_admin_key"
                state["updated_at"] = self._now()
                self._persist()
        except asyncio.CancelledError:
            with self.lock:
                state["status"] = "cancelled"
                state.pop("result", None)
                state["failed_phase"] = None
                state["error_code"] = None
                state["recovery_action"] = None
                self.deliveries.pop(task_id, None)
                state["updated_at"] = self._now()
                self._persist()
        except Exception:
            with self.lock:
                if state.get("status") != "cancelled":
                    failure = deployment_failure(failure_key)
                    state["status"] = "failed"
                    state["phase"] = failure.failed_phase
                    for failed_step in state["steps"]:
                        if failed_step.get("id") == failure.failed_phase:
                            failed_step["status"] = "failed"
                    state["failed_phase"] = failure.failed_phase
                    state["error_code"] = failure.error_code
                    state["recovery_action"] = failure.recovery_action
                    state.pop("error", None)
                    state.pop("result", None)
                    self.deliveries.pop(task_id, None)
                    state["updated_at"] = self._now()
                    self._persist()
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
                try:
                    await connection.wait_closed()
                except Exception:
                    pass
            self._release_task_reservation(task_id)


extension_tasks = ExtensionTaskManager()


class DeploymentPlanManager:
    _CAPABILITY_SNAPSHOT_FIELDS = (
        "auth_kind", "elevation_contract", "is_root", "docker_access",
        "elevated_docker_access", "passwordless_sudo", "password_sudo",
        "can_admin", "can_deploy", "diagnostic_code",
    )
    _EXISTING_SNAPSHOT_FIELDS = (
        "id", "container_id", "name", "image", "source_image_id", "status", "ports",
        "published_ports", "service_port", "port_bindings", "port_bindings_complete",
        "compose_project", "compose_service", "working_dir",
        "data_dir", "config_file", "data_size_mb", "clone_available", "managed", "ownership",
    )
    _ENVIRONMENT_SNAPSHOT_FIELDS = (
        "docker_version", "compose_version", "home_dir", "listening_ports",
        "tcp_listeners", "listening_ports_probe",
    )
    _EMPTY_PLAN_OBSERVATION_FIELDS = (
        "image", "status", "ports", "data_size_mb", "clone_available",
    )
    _PATH_CONDITION_KEYS = {
        "isolated-empty": frozenset({
            "target_install_dir_absent", "target_install_parent_claimable",
            "target_data_dir_nonoverlap", "target_compose_project_nonoverlap",
            "target_port_unoccupied",
        }),
        "existing": frozenset({
            "existing_instance_present", "existing_instance_identity_matches",
        }),
        "isolated-source-clone": frozenset({
            "source_instance_present", "source_clone_scope_allowed",
            "source_data_path_readable", "target_install_dir_absent",
            "target_install_parent_claimable", "source_target_paths_nonoverlap",
            "target_port_unoccupied", "clone_capacity_sufficient",
        }),
    }

    def __init__(self):
        self.plans: dict[str, dict] = {}
        self.lock = threading.RLock()

    def create(
        self,
        request: ExtensionPlanRequest,
        discovery: dict,
        *,
        path_requirements: dict[str, dict[str, Any]] | None = None,
    ) -> dict:
        with self.lock:
            return self._create(request, discovery, path_requirements=path_requirements)

    @staticmethod
    def _identity_fields(request: ExtensionPlanRequest | ExtensionDeployRequest) -> dict[str, Any]:
        fingerprint = request.expected_host_key or request.target.host_key
        return {
            "target_id": request.target.id,
            "host": request.target.host,
            "ssh_port": request.target.port,
            "username": request.target.username.strip(),
            "host_fingerprint": fingerprint,
            "auth_kind": _authentication_kind(request.credential),
            "elevation_contract": _elevation_contract(request.credential),
        }

    @staticmethod
    def _capability_snapshot(discovery: dict) -> dict[str, Any]:
        privileges = discovery.get("privileges")
        if not isinstance(privileges, dict):
            return {}
        return {
            key: copy.deepcopy(privileges.get(key))
            for key in DeploymentPlanManager._CAPABILITY_SNAPSHOT_FIELDS
        }

    @staticmethod
    def _existing_snapshot(existing: dict) -> dict[str, Any]:
        return {
            key: copy.deepcopy(existing.get(key))
            for key in DeploymentPlanManager._EXISTING_SNAPSHOT_FIELDS
        }

    @staticmethod
    def _environment_snapshot(environment: dict) -> dict[str, Any]:
        return {
            "docker_version": copy.deepcopy(environment.get("docker_version")),
            "compose_version": copy.deepcopy(environment.get("compose_version")),
            "home_dir": copy.deepcopy(environment.get("home_dir")),
            "listening_ports": sorted(int(port) for port in environment.get("listening_ports", [])),
            "tcp_listeners": copy.deepcopy(environment.get("tcp_listeners")),
            "listening_ports_probe": copy.deepcopy(environment.get("listening_ports_probe")),
        }

    @staticmethod
    def _canonical_tcp_listeners(value: Any) -> list[dict[str, Any]] | None:
        if not isinstance(value, list):
            return None
        canonical: list[tuple[str, int]] = []
        for listener in value:
            if not isinstance(listener, dict) or set(listener) != {"protocol", "host_port"}:
                return None
            protocol = str(listener.get("protocol") or "").lower()
            host_port = listener.get("host_port")
            if (
                protocol != "tcp"
                or isinstance(host_port, bool)
                or not isinstance(host_port, int)
                or not 1 <= host_port <= 65535
            ):
                return None
            canonical.append((protocol, host_port))
        return [
            {"protocol": protocol, "host_port": host_port}
            for protocol, host_port in sorted(canonical, key=lambda item: item[1])
        ]

    @classmethod
    def _listener_probe_complete(cls, environment: dict) -> bool:
        probe = environment.get("listening_ports_probe")
        status = probe.get("status") if isinstance(probe, dict) else None
        listeners = cls._canonical_tcp_listeners(environment.get("tcp_listeners"))
        display_ports = environment.get("listening_ports")
        return bool(
            isinstance(probe, dict)
            and isinstance(status, int)
            and not isinstance(status, bool)
            and status == 0
            and probe.get("complete") is True
            and probe.get("payload_present") is True
            and listeners is not None
            and listeners == environment.get("tcp_listeners")
            and isinstance(display_ports, list)
            and all(isinstance(port, int) and not isinstance(port, bool) for port in display_ports)
            and sorted(set(display_ports)) == sorted({item["host_port"] for item in listeners})
        )

    @staticmethod
    def _canonical_port_bindings(value: Any) -> list[dict[str, Any]] | None:
        if not isinstance(value, list):
            return None
        canonical: list[tuple[str, int, int, str]] = []
        for binding in value:
            if not isinstance(binding, dict):
                return None
            try:
                host_ip = ipaddress.ip_address(str(binding.get("host_ip") or "")).compressed
                host_port = int(binding.get("host_port"))
                container_port = int(binding.get("container_port"))
            except (TypeError, ValueError):
                return None
            protocol = str(binding.get("protocol") or "").lower()
            if (
                isinstance(binding.get("host_port"), bool)
                or isinstance(binding.get("container_port"), bool)
                or not 1 <= host_port <= 65535
                or not 1 <= container_port <= 65535
                or protocol not in {"tcp", "udp", "sctp"}
            ):
                return None
            canonical.append((host_ip, host_port, container_port, protocol))
        return [
            {
                "host_ip": host_ip,
                "host_port": host_port,
                "container_port": container_port,
                "protocol": protocol,
            }
            for host_ip, host_port, container_port, protocol in sorted(canonical)
        ]

    @classmethod
    def _port_bindings_complete(cls, discovery: dict) -> bool:
        for instance in discovery.get("instances", []):
            bindings = instance.get("port_bindings") if isinstance(instance, dict) else None
            if (
                not isinstance(instance, dict)
                or instance.get("port_bindings_complete") is not True
                or cls._canonical_port_bindings(bindings) != bindings
            ):
                return False
        return True

    @staticmethod
    def _snapshot_digest(snapshot: dict[str, Any]) -> str:
        encoded = json.dumps(
            snapshot,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _evidence_manifest(cls, snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "contract_version": PHASE4_DEPLOYMENT_CONTRACT_VERSION,
            "snapshot_digest": cls._snapshot_digest(snapshot),
            "complete": True,
            "changed_fields": [],
        }

    @staticmethod
    def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": plan.get("id"),
            "evidence_manifest": copy.deepcopy(plan.get("evidence_manifest")),
            "ready": True,
            "registers_locally": plan.get("strategy") == "existing",
            "remote_write_expected": plan.get("strategy") != "existing",
            "clone_requested": plan.get("clone_scope") in {"media", "working-copy"},
            "admin_required": plan.get("clone_scope") in {"media", "working-copy"},
        }

    @classmethod
    def public_discovery(cls, discovery: dict[str, Any], target_id: str) -> dict[str, Any]:
        snapshot = cls._discovery_snapshot(discovery)
        manifest = cls._evidence_manifest(snapshot)
        privileges = snapshot.get("privileges", {})
        environment = snapshot.get("environment", {})
        complete = cls._port_bindings_complete(discovery) and cls._listener_probe_complete(
            discovery.get("environment", {})
        )
        manifest["complete"] = complete
        manifest["changed_fields"] = [] if complete else ["discovery.completeness"]
        modes = []
        for mode in discovery.get("deployment_modes", []):
            if not isinstance(mode, dict) or mode.get("id") not in {"compose", "warp", "python"}:
                continue
            modes.append({
                "id": mode["id"],
                "available": mode.get("available") is True,
                "recommended": mode.get("recommended") is True,
            })
        instances = []
        for item in discovery.get("instances", []):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                continue
            status = str(item.get("status") or "").lower()
            instances.append({
                "handle": public_instance_handle(target_id, item["id"]),
                "managed": item.get("managed") is True,
                "running": status.startswith("up") or status in {"running", "healthy"},
                "clone_available": item.get("clone_available") is True,
            })
        capabilities = {
            "can_deploy": privileges.get("can_deploy") is True,
            "can_admin": privileges.get("can_admin") is True,
            "docker_available": bool(environment.get("docker_version")),
            "compose_available": bool(environment.get("compose_version")),
        }
        return {
            "ready": capabilities["can_deploy"] and complete,
            "evidence_manifest": manifest,
            "capabilities": capabilities,
            "instances": instances,
            "deployment_modes": modes,
        }

    def resolve_public_references(self, request: ExtensionDeployRequest) -> ExtensionDeployRequest:
        with self.lock:
            plan = self.plans.get(request.confirmed_plan_id)
            if not plan:
                return request
            updates: dict[str, Any] = {}
            target_id = str(plan.get("target_id") or "")
            if plan.get("strategy") == "existing":
                expected = public_instance_handle(target_id, str(plan.get("instance_id") or ""))
                if request.instance_id == expected:
                    updates.update({
                        "instance_id": plan["instance_id"],
                        "service_port": plan["service_port"],
                        "image": plan["image"],
                    })
                elif request.instance_id != plan.get("instance_id"):
                    raise DeploymentPlanConfirmationError(
                        "deployment_plan_identity_changed",
                        code="deployment_plan_identity_changed",
                    )
            if plan.get("clone_scope") in {"media", "working-copy"}:
                expected = public_instance_handle(target_id, str(plan.get("clone_source_id") or ""))
                if request.clone_source_id == expected:
                    updates.update({
                        "clone_source_id": plan["clone_source_id"],
                        "image": plan["image"],
                    })
                elif request.clone_source_id != plan.get("clone_source_id"):
                    raise DeploymentPlanConfirmationError(
                        "deployment_plan_identity_changed",
                        code="deployment_plan_identity_changed",
                    )
            return request.model_copy(update=updates) if updates else request

    @staticmethod
    def _normalized_plan_path(value: Any) -> str:
        raw = str(value or "").strip()
        return posixpath.normpath(raw) if raw.startswith("/") else ""

    @staticmethod
    def _path_condition_strategy(request: ExtensionPlanRequest | ExtensionDeployRequest) -> str:
        if request.strategy == "existing":
            return "existing"
        if request.clone_scope == "empty":
            return "isolated-empty"
        return "isolated-source-clone"

    @classmethod
    def path_requirements(
        cls,
        request: ExtensionPlanRequest | ExtensionDeployRequest,
        discovery: dict,
    ) -> dict[str, dict[str, Any]]:
        strategy = cls._path_condition_strategy(request)
        environment = discovery.get("environment", {})
        instances = discovery.get("instances", [])
        if strategy == "existing":
            existing = next(
                (item for item in instances if item.get("id") == request.instance_id),
                {},
            )
            return {
                "existing_instance_present": {
                    "kind": "instance_present", "instance_id": request.instance_id,
                },
                "existing_instance_identity_matches": {
                    "kind": "instance_identity_matches", "instance_id": request.instance_id,
                    "container_id": existing.get("container_id"),
                    "service_port": existing.get("service_port"),
                },
            }
        home_dir = cls._normalized_plan_path(environment.get("home_dir"))
        install_dir = cls._normalized_plan_path(
            f"{home_dir}/genbox-apps/{request.project_id}/{request.instance_id}"
            if home_dir else ""
        )
        install_parent = posixpath.dirname(install_dir) if install_dir else ""
        target_port = {"kind": "tcp_port_unoccupied", "port": request.service_port}
        if strategy == "isolated-empty":
            return {
                "target_install_dir_absent": {"kind": "absent", "path": install_dir},
                "target_install_parent_claimable": {"kind": "claimable_parent", "path": install_parent},
                "target_data_dir_nonoverlap": {"kind": "data_nonoverlap", "path": f"{install_dir}/data"},
                "target_compose_project_nonoverlap": {
                    "kind": "compose_nonoverlap",
                    "compose_project": f"genbox-chatgpt2api-{request.instance_id}",
                },
                "target_port_unoccupied": target_port,
            }
        source = next(
            (item for item in instances if item.get("id") == request.clone_source_id),
            {},
        )
        required_mb = int(source.get("data_size_mb") or 0) + 512
        return {
            "source_instance_present": {
                "kind": "instance_present", "instance_id": request.clone_source_id,
            },
            "source_clone_scope_allowed": {
                "kind": "clone_scope_allowed",
                "allowed": request.strategy == "isolated" and request.clone_scope in {"media", "working-copy"},
            },
            "source_data_path_readable": {
                "kind": "directory", "path": source.get("data_dir"),
            },
            "target_install_dir_absent": {"kind": "absent", "path": install_dir},
            "target_install_parent_claimable": {"kind": "claimable_parent", "path": install_parent},
            "source_target_paths_nonoverlap": {
                "kind": "source_target_paths_nonoverlap",
                "path": install_dir,
                "source_id": request.clone_source_id,
            },
            "target_port_unoccupied": target_port,
            "clone_capacity_sufficient": {
                "kind": "capacity_sufficient", "required_mb": required_mb,
            },
        }

    @classmethod
    def _validate_path_conditions(
        cls,
        request: ExtensionPlanRequest | ExtensionDeployRequest,
        discovery: dict,
        path_requirements: dict[str, dict[str, Any]],
    ) -> None:
        strategy = cls._path_condition_strategy(request)
        expected_keys = cls._PATH_CONDITION_KEYS[strategy]
        conditions = discovery.get("path_conditions")
        if (
            discovery.get("path_conditions_version") != PHASE4_DEPLOYMENT_CONTRACT_VERSION
            or not isinstance(conditions, dict)
            or set(path_requirements) != expected_keys
            or set(conditions) != expected_keys
            or any(conditions.get(key) is not True for key in expected_keys)
        ):
            raise DeploymentPlanConfirmationError(
                "deployment_path_conditions_invalid",
                code="deployment_path_conditions_invalid",
            )

    @classmethod
    def _discovery_snapshot(cls, discovery: dict) -> dict[str, Any]:
        instances = [cls._existing_snapshot(item) for item in discovery.get("instances", [])]
        instances.sort(key=lambda item: (str(item.get("id") or ""), str(item.get("container_id") or "")))
        return {
            "host_key": copy.deepcopy(discovery.get("host_key")),
            "environment": cls._environment_snapshot(discovery.get("environment", {})),
            "instances": instances,
            "privileges": cls._capability_snapshot(discovery),
        }

    @staticmethod
    def _snapshot_shape_valid(snapshot: Any) -> bool:
        return (
            isinstance(snapshot, dict)
            and "host_key" in snapshot
            and isinstance(snapshot.get("environment"), dict)
            and isinstance(snapshot.get("instances"), list)
            and isinstance(snapshot.get("privileges"), dict)
        )

    @classmethod
    def _fresh_snapshot_projection(cls, plan: dict, snapshot: dict) -> dict[str, Any]:
        projected = copy.deepcopy(snapshot)
        environment = projected.get("environment")
        if isinstance(environment, dict):
            # Completeness and requested-port occupancy are validated
            # separately. Unrelated listener churn is not ownership drift.
            environment.pop("listening_ports", None)
            environment.pop("tcp_listeners", None)
        if plan.get("strategy") != "existing" and plan.get("clone_scope") == "empty":
            # Empty plans consume none of the unrelated instances' display or
            # clone-eligibility observations. Requested-port occupancy is
            # checked separately; structured identity, ports, paths, and
            # source_image_id remain exact in this projection.
            for instance in projected.get("instances", []):
                if not isinstance(instance, dict):
                    continue
                for field in cls._EMPTY_PLAN_OBSERVATION_FIELDS:
                    instance.pop(field, None)
        return projected

    @classmethod
    def _snapshot_changed_fields(cls, expected: dict, actual: dict) -> list[str]:
        changed: set[str] = set()
        if expected.get("host_key") != actual.get("host_key"):
            changed.add("host_key")
        expected_environment = expected.get("environment", {})
        actual_environment = actual.get("environment", {})
        for field in cls._ENVIRONMENT_SNAPSHOT_FIELDS:
            if expected_environment.get(field) != actual_environment.get(field):
                changed.add(f"environment.{field}")
        expected_instances = expected.get("instances", [])
        actual_instances = actual.get("instances", [])
        if len(expected_instances) != len(actual_instances):
            changed.add("instances")
        for expected_instance, actual_instance in zip(expected_instances, actual_instances):
            for field in cls._EXISTING_SNAPSHOT_FIELDS:
                if expected_instance.get(field) != actual_instance.get(field):
                    changed.add(f"instances.{field}")
        expected_privileges = expected.get("privileges", {})
        actual_privileges = actual.get("privileges", {})
        for field in cls._CAPABILITY_SNAPSHOT_FIELDS:
            if expected_privileges.get(field) != actual_privileges.get(field):
                changed.add(f"privileges.{field}")
        return sorted(changed) or ["discovery_snapshot"]

    def _create(
        self,
        request: ExtensionPlanRequest,
        discovery: dict,
        *,
        path_requirements: dict[str, dict[str, Any]] | None = None,
    ) -> dict:
        validate_deployment_capability(request.project_id, request.strategy, request.deployment_mode)
        if not request.target.id:
            raise ValueError("请先保存 VPS 配置，再生成部署计划")
        identity = self._identity_fields(request)
        if not identity["host_fingerprint"]:
            raise ValueError("请先确认 SSH 主机指纹，再生成部署计划")
        discovered_host_key = str(discovery.get("host_key") or identity["host_fingerprint"])
        if discovered_host_key != identity["host_fingerprint"]:
            raise ValueError("发现结果与已确认 SSH 主机指纹不一致")
        discovery = copy.deepcopy(discovery)
        discovery["host_key"] = discovered_host_key
        verified_capability = self._capability_snapshot(discovery)
        if not verified_capability.get("can_deploy"):
            raise ValueError("当前 SSH 用户没有经过验证的 Docker 部署能力")
        if verified_capability.get("auth_kind") not in {"unknown", identity["auth_kind"]}:
            raise ValueError("发现结果与当前 SSH 认证种类不一致，请重新检测")
        if verified_capability.get("elevation_contract") != identity["elevation_contract"]:
            raise ValueError("发现结果与当前提权方式不一致，请重新检测")
        if not self._port_bindings_complete(discovery):
            raise DeploymentPlanConfirmationError(
                "deployment_port_bindings_incomplete",
                code="deployment_port_bindings_incomplete",
            )
        environment = discovery.get("environment", {})
        if not self._listener_probe_complete(environment):
            raise DeploymentPlanConfirmationError(
                "deployment_listener_probe_incomplete",
                code="deployment_listener_probe_incomplete",
            )
        computed_path_requirements = self.path_requirements(request, discovery)
        if path_requirements is not None and path_requirements != computed_path_requirements:
            raise DeploymentPlanConfirmationError(
                "deployment_path_conditions_invalid",
                code="deployment_path_conditions_invalid",
            )
        path_requirements = computed_path_requirements
        if request.strategy == "existing":
            existing = next((item for item in discovery.get("instances", []) if item.get("id") == request.instance_id), None)
            if not existing:
                raise ValueError("请选择检测到的已有实例")
            discovered_port = existing.get("service_port")
            if not isinstance(discovered_port, int):
                raise ValueError("已有实例的宿主机端口缺失或存在多个映射，已拒绝登记")
            if request.service_port != discovered_port:
                raise ValueError("请求端口与结构化 Docker 发现端口不一致")
            registered = extensions_store.get_instance(request.instance_id)
            if registered and registered.target_id != request.target.id:
                raise ValueError("instance_id_conflicts_with_another_target")
            if registered and registered.managed and registered.service_port != discovered_port:
                raise ValueError("GenBox 管理实例的已登记端口与远程结构化发现不一致")
            self._validate_path_conditions(request, discovery, path_requirements)
            plan_id = uuid.uuid4().hex[:16]
            execution_snapshot = self._discovery_snapshot(discovery)
            plan = {
                "id": plan_id, "project_id": request.project_id, **identity, "instance_id": request.instance_id,
                "strategy": "existing", "deployment_mode": "compose", "service_port": discovered_port,
                "image": existing.get("image") or request.image,
                "compose_project": existing.get("compose_project") or "",
                "install_dir": existing.get("working_dir") or "",
                "verified_capability": verified_capability,
                "existing_snapshot": self._existing_snapshot(existing),
                "execution_snapshot": execution_snapshot,
                "evidence_manifest": self._evidence_manifest(execution_snapshot),
                "required_disk_mb": 0,
                "path_requirements": path_requirements,
                "local_side_effect": "确认并在 GenBox 本地登记现有实例；远程环境保持不变",
                "operations": ["登记已有实例入口", "保留现有容器、配置和数据不变"],
                "safety": ["不执行任何远程写入", "不重启、不停止、不删除已有实例", "管理密钥由用户自行提供"],
                "expires_at": time.time() + 600,
            }
            self.plans[plan_id] = plan
            return self._public_plan(plan)
        if request.deployment_mode != "compose":
            raise ValueError("当前仅标准 Docker Compose 已达到安全执行条件")
        if not IMAGE_PATTERN.fullmatch(request.image):
            raise ValueError("镜像引用格式无效")
        if not environment.get("docker_version") or not environment.get("compose_version"):
            raise ValueError("VPS 缺少 Docker 或 Docker Compose v2")
        if request.service_port in environment.get("listening_ports", []):
            raise ValueError(f"端口 {request.service_port} 已被占用")
        if any(item.get("id") == request.instance_id for item in discovery.get("instances", [])):
            raise ValueError("实例 ID 已存在，请选择接入已有实例或更换名称")
        home_dir = str(environment.get("home_dir") or "").rstrip("/")
        if not home_dir.startswith("/"):
            raise ValueError("VPS 用户主目录未被可靠发现，无法绑定安全部署路径")
        install_dir = f"{home_dir}/genbox-apps/{request.project_id}/{request.instance_id}"
        required_mb = 512
        if request.clone_scope != "empty" and not verified_capability.get("can_admin"):
            raise ValueError("复制现有实例数据需要经过验证的管理员提权能力")
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
        if int(environment.get("disk_free_mb") or 0) < required_mb:
            raise ValueError(f"磁盘空间不足，安全部署至少需要 {required_mb} MB")
        source_baseline = {
            key: clone_source.get(key, "")
            for key in (
                "id", "container_id", "name", "image", "status", "ports",
                "published_ports", "service_port", "port_bindings", "port_bindings_complete",
                "compose_project", "working_dir", "data_dir", "config_file",
                "data_size_mb", "managed", "ownership",
            )
        } if clone_source else {}
        self._validate_path_conditions(request, discovery, path_requirements)
        plan_id = uuid.uuid4().hex[:16]
        execution_snapshot = self._discovery_snapshot(discovery)
        plan = {
            "id": plan_id, "project_id": request.project_id, **identity, "instance_id": request.instance_id,
            "strategy": request.strategy, "deployment_mode": request.deployment_mode,
            "service_port": request.service_port, "image": request.image,
            "compose_project": f"genbox-chatgpt2api-{request.instance_id}",
            "install_dir": install_dir,
            "clone_scope": request.clone_scope,
            "clone_source_id": request.clone_source_id,
            "clone_source_data_dir": clone_source.get("data_dir", "") if clone_source else "",
            "clone_source_config_file": clone_source.get("config_file", "") if clone_source else "",
            "clone_source_image_id": clone_source.get("source_image_id", "") if clone_source else "",
            "clone_size_mb": int(clone_source.get("data_size_mb") or 0) if clone_source else 0,
            "source_baseline": source_baseline,
            "verified_capability": verified_capability,
            "execution_snapshot": execution_snapshot,
            "evidence_manifest": self._evidence_manifest(execution_snapshot),
            "required_disk_mb": required_mb,
            "path_requirements": path_requirements,
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
        return self._public_plan(plan)

    def lease(self, plan_id: str, request: ExtensionDeployRequest) -> tuple[str, dict]:
        with self.lock:
            plan = self._take(plan_id, request, consume=False)
            if plan.get("_lease_token"):
                raise ValueError("部署计划正在进行远程复核，请勿重复提交")
            token = uuid.uuid4().hex
            plan["_lease_token"] = token
            return token, copy.deepcopy(plan)

    def release(self, plan_id: str, token: str) -> None:
        with self.lock:
            plan = self.plans.get(plan_id)
            if plan and hmac.compare_digest(str(plan.get("_lease_token") or ""), token):
                plan.pop("_lease_token", None)

    def consume_lease(self, plan_id: str, token: str, request: ExtensionDeployRequest) -> dict:
        with self.lock:
            plan = self.plans.get(plan_id)
            if not plan or not hmac.compare_digest(str(plan.get("_lease_token") or ""), token):
                raise ValueError("部署计划复核租约无效，请重新提交")
            self._take(plan_id, request, consume=False)
            consumed = self.plans.pop(plan_id)
            consumed.pop("_lease_token", None)
            return consumed

    def restore(self, plan: dict) -> None:
        restored = copy.deepcopy(plan)
        restored.pop("_lease_token", None)
        with self.lock:
            if restored.get("expires_at", 0) >= time.time() and restored.get("id") not in self.plans:
                self.plans[restored["id"]] = restored

    def validate_fresh_snapshot(self, plan: dict, discovery: dict) -> None:
        if "execution_snapshot" not in plan and isinstance(plan.get("id"), str):
            plan = self.plans.get(plan["id"], plan)
        expected = plan.get("execution_snapshot")
        if not self._snapshot_shape_valid(expected):
            raise DeploymentSnapshotChangedError(
                category="plan_snapshot",
                changed_fields=["discovery_snapshot"],
            )
        manifest = plan.get("evidence_manifest")
        if (
            not isinstance(manifest, dict)
            or manifest.get("contract_version") != PHASE4_DEPLOYMENT_CONTRACT_VERSION
            or manifest.get("complete") is not True
            or manifest.get("snapshot_digest") != self._snapshot_digest(expected)
        ):
            raise DeploymentSnapshotChangedError(
                category="plan_snapshot",
                changed_fields=["evidence_manifest"],
            )
        environment = discovery.get("environment", {})
        if not self._port_bindings_complete(discovery):
            raise DeploymentSnapshotChangedError(
                category="stable_snapshot",
                changed_fields=["instances.port_bindings"],
            )
        if not self._listener_probe_complete(environment):
            raise DeploymentSnapshotChangedError(
                category="listener_evidence",
                changed_fields=["environment.listening_ports_probe"],
            )
        if plan.get("strategy") == "existing":
            existing = next(
                (item for item in discovery.get("instances", []) if item.get("id") == plan.get("instance_id")),
                None,
            )
            if not existing:
                raise DeploymentSnapshotChangedError(
                    category="existing_instance",
                    changed_fields=["instances.id"],
                )
            if existing.get("service_port") != plan.get("service_port"):
                raise DeploymentSnapshotChangedError(
                    category="existing_instance",
                    changed_fields=["instances.service_port"],
                )
        else:
            if plan.get("service_port") in environment.get("listening_ports", []):
                raise DeploymentSnapshotChangedError(
                    category="requested_port",
                    changed_fields=["environment.listening_ports"],
                )
            if any(item.get("id") == plan.get("instance_id") for item in discovery.get("instances", [])):
                raise DeploymentSnapshotChangedError(
                    category="target_instance",
                    changed_fields=["instances.id"],
                )
        path_requirements = plan.get("path_requirements")
        path_conditions = discovery.get("path_conditions")
        if (
            not isinstance(path_requirements, dict)
            or discovery.get("path_conditions_version") != PHASE4_DEPLOYMENT_CONTRACT_VERSION
            or not isinstance(path_conditions, dict)
            or set(path_conditions) != set(path_requirements)
            or any(path_conditions.get(name) is not True for name in path_requirements)
        ):
            raise DeploymentSnapshotChangedError(
                category="path_requirements",
                changed_fields=["path_conditions"],
            )
        actual = self._discovery_snapshot(discovery)
        expected = self._fresh_snapshot_projection(plan, expected)
        actual = self._fresh_snapshot_projection(plan, actual)
        if actual != expected:
            raise DeploymentSnapshotChangedError(
                category="stable_snapshot",
                changed_fields=self._snapshot_changed_fields(expected, actual),
            )
        required_disk_mb = int(plan.get("required_disk_mb") or 0)
        disk_free_mb = int(discovery.get("environment", {}).get("disk_free_mb") or 0)
        if disk_free_mb < required_disk_mb:
            raise DeploymentSnapshotChangedError(
                category="capacity_threshold",
                changed_fields=["environment.disk_free_mb"],
            )

    def take(self, plan_id: str, request: ExtensionDeployRequest) -> dict:
        with self.lock:
            return self._take(plan_id, request)

    def _take(self, plan_id: str, request: ExtensionDeployRequest, *, consume: bool = True) -> dict:
        validate_deployment_capability(request.project_id, request.strategy, request.deployment_mode)
        plan = self.plans.get(plan_id)
        if not plan or plan["expires_at"] < time.time():
            raise DeploymentPlanUnavailableError()
        if consume and plan.get("_lease_token"):
            raise ValueError("部署计划正在进行远程复核，请勿重复提交")
        identity_request = request
        plan_has_bound_identity = all(key in plan for key in (
            "host", "ssh_port", "username", "host_fingerprint", "auth_kind", "elevation_contract",
        ))
        if plan_has_bound_identity and request.trust_host_key:
            live_target = extensions_store.get_target(request.target.id)
            if not live_target:
                raise DeploymentPlanConfirmationError(
                    "VPS 连接身份与已确认部署计划不一致，请重新生成安全计划",
                    code="deployment_plan_identity_changed",
                )
            identity_request = request.model_copy(update={
                "target": live_target,
                "expected_host_key": live_target.host_key,
            })
        current_identity = self._identity_fields(identity_request)
        if plan_has_bound_identity and any(plan.get(key) != value for key, value in current_identity.items()):
            raise DeploymentPlanConfirmationError(
                "VPS 连接身份与已确认部署计划不一致，请重新生成安全计划",
                code="deployment_plan_identity_changed",
            )
        if (
            plan.get("project_id") != request.project_id
            or plan["instance_id"] != request.instance_id
            or plan["strategy"] != request.strategy
            or plan["deployment_mode"] != request.deployment_mode
        ):
            raise ValueError("部署请求与已确认计划不一致")
        if plan["service_port"] != request.service_port:
            raise DeploymentPlanConfirmationError(
                "服务端口与已确认部署计划不一致，请重新生成安全计划",
                code="deployment_plan_service_port_changed",
            )
        if plan["image"] != request.image:
            raise DeploymentPlanConfirmationError(
                "容器镜像与已确认部署计划不一致，请重新生成安全计划",
                code="deployment_plan_image_changed",
            )
        if plan.get("clone_source_id", "") != request.clone_source_id or plan.get("clone_scope", "empty") != request.clone_scope:
            raise ValueError("克隆范围已变更，请重新生成计划")
        if consume:
            self.plans.pop(plan_id)
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
    try:
        privileges = await _diagnose_privileges(connection, request.credential)
    except Exception:
        connection.close()
        await connection.wait_closed()
        raise
    if not privileges["can_deploy"]:
        connection.close()
        await connection.wait_closed()
        raise PermissionError("当前 SSH 用户没有经过验证的 Docker 管理能力")

    async def run_docker(command: str):
        if privileges["docker_access"]:
            return await connection.run(command, check=False)
        wrapped, input_data = _elevated_command(command, request.credential, privileges)
        return await connection.run(wrapped, input=input_data, check=False)

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
        restart = await run_docker(
            f"cd {shlex.quote(instance.install_dir)} && docker compose -p {shlex.quote(instance.compose_project)} "
            "-f compose.yml up -d --force-recreate app"
        )
        verified = await connection.run(
            f"cd {shlex.quote(instance.install_dir)} && set -a && . ./.env && set +a && "
            "for i in 1 2 3 4 5 6 7 8 9 10; do "
            f"curl -fsS -X POST -H \"Authorization: Bearer $CHATGPT2API_AUTH_KEY\" "
            f"http://127.0.0.1:{instance.service_port}/auth/login >/dev/null && exit 0; sleep 2; done; exit 1",
            check=False,
        )
        if restart.exit_status != 0 or verified.exit_status != 0:
            await run_docker(
                f"cp {shlex.quote(env_backup)} {shlex.quote(env_path)}; "
                f"cd {shlex.quote(instance.install_dir)} && docker compose -p {shlex.quote(instance.compose_project)} "
                "-f compose.yml up -d --force-recreate app"
            )
            raise RuntimeError("新密钥验证失败，已恢复原配置")
        await connection.run(f"rm -f {shlex.quote(env_backup)}", check=False)
        return {"ok": True, "instance_id": instance.id, "admin_key": new_key, "shown_once": True}
    finally:
        connection.close()
        await connection.wait_closed()
