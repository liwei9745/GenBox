from typing import Literal

import re

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


HOST_KEY_ALGORITHMS = frozenset({
    "ssh-ed25519",
    "ecdsa-sha2-nistp256",
    "ssh-rsa",
})
HOST_KEY_FINGERPRINT_PATTERN = r"^SHA256:[A-Za-z0-9+/]{43}$"
IMMUTABLE_IMAGE_REFERENCE_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9._/-]{1,240}@sha256:[a-f0-9]{64}$"
)


def is_immutable_image_reference(value: object) -> bool:
    """Return whether a deployable image is pinned to an OCI content digest."""
    return IMMUTABLE_IMAGE_REFERENCE_PATTERN.fullmatch(str(value or "").strip()) is not None


def validate_deployment_image(image: object, strategy: str, clone_scope: str) -> None:
    """Reject mutable image references before a plan can initiate SSH discovery."""
    if strategy != "existing" and clone_scope == "empty" and not is_immutable_image_reference(image):
        raise ValueError(
            "隔离空白实例需要可由服务器拉取的不可变镜像地址，"
            "格式为 registry/name@sha256:<64 位摘要>；本机 Docker 标签和 latest 不能用于部署"
        )


def is_canonical_host_key_trust(algorithm: str, fingerprint: str) -> bool:
    import re

    return (
        algorithm in HOST_KEY_ALGORITHMS
        and re.fullmatch(HOST_KEY_FINGERPRINT_PATTERN, fingerprint or "") is not None
    )


class ExtensionTarget(BaseModel):
    id: str
    name: str
    host: str
    port: int = Field(default=22, ge=1, le=65535)
    username: str
    target_role: Literal["isolated-development", "production-read-only"] = "isolated-development"
    identity_version: int = Field(default=0, ge=0)
    host_key_algorithm: str = ""
    host_key: str = ""
    primary_network: Literal["tailscale", "netbird", "cloudflare"] = "tailscale"
    available_networks: list[Literal["tailscale", "netbird", "cloudflare"]] = Field(default_factory=list)
    network_url: str = ""
    network_verified_at: str = ""
    chatgpt2api_port: int = Field(default=3000, ge=1, le=65535)
    created_at: str = ""
    updated_at: str = ""

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("SSH 用户名不能为空")
        return normalized


class ExtensionInstance(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,39}$")
    target_id: str
    project: str = "chatgpt2api"
    strategy: Literal["existing", "isolated", "new"] = "isolated"
    deployment_mode: Literal["compose", "warp", "python"] = "compose"
    compose_project: str = ""
    service_port: int = Field(ge=1, le=65535)
    install_dir: str
    data_dir: str
    image: str
    version: str = ""
    status: str = "unknown"
    console_url: str = ""
    api_url: str = ""
    managed: bool = False
    ownership: str = ""
    container_id: str = ""
    container_name: str = ""
    clone_source_id: str = ""
    clone_scope: Literal["empty", "media", "working-copy"] = "empty"
    created_at: str = ""
    updated_at: str = ""


class ExtensionConfig(BaseModel):
    targets: list[ExtensionTarget] = Field(default_factory=list)
    instances: list[ExtensionInstance] = Field(default_factory=list)
    batch_target_ids: list[str] = Field(default_factory=list)
    target_generations: dict[str, int] = Field(default_factory=dict)


class ExtensionBatchTargetsRequest(BaseModel):
    target_ids: list[str] = Field(default_factory=list, max_length=100)


class ExtensionHostKeyProbeRequest(BaseModel):
    target_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ExtensionHostKeyResetRequest(ExtensionHostKeyProbeRequest):
    """Explicitly discard the saved host identity before a new pairing."""


class ExtensionHostKeyConfirmRequest(ExtensionHostKeyProbeRequest):
    algorithm: Literal["ssh-ed25519", "ecdsa-sha2-nistp256", "ssh-rsa"]
    fingerprint: str = Field(pattern=HOST_KEY_FINGERPRINT_PATTERN, min_length=50, max_length=50)


class ExtensionHostKeyPairingStartRequest(ExtensionHostKeyProbeRequest):
    """Start a transient trusted-terminal host identity pairing."""


class ExtensionHostKeyPairingCompleteRequest(BaseModel):
    pairing_id: str = Field(pattern=r"^[A-Za-z0-9_-]{20,128}$", min_length=20, max_length=128)
    response: str = Field(min_length=20, max_length=512)


class ExtensionHostKeyPairingCancelRequest(BaseModel):
    pairing_id: str = Field(pattern=r"^[A-Za-z0-9_-]{20,128}$", min_length=20, max_length=128)


class SSHCredential(BaseModel):
    password: str = ""
    private_key: str = ""
    passphrase: str = ""
    sudo_password: str = ""
    elevation: Literal["none", "passwordless_sudo", "password_sudo"] = "none"
    reuse_ssh_password: bool = False

    @model_validator(mode="after")
    def require_exactly_one_authentication_method(self):
        if bool(self.password) == bool(self.private_key):
            raise ValueError("请选择且只选择一种 SSH 凭据：密码或私钥")
        if self.elevation in {"none", "passwordless_sudo"}:
            if self.sudo_password or self.reuse_ssh_password:
                raise ValueError("当前提权方式不接受 sudo 密码或 SSH 密码复用")
        elif self.elevation == "password_sudo":
            if self.reuse_ssh_password and not self.password:
                raise ValueError("只有密码 SSH 认证可以显式复用 SSH 密码进行 sudo 提权")
            if self.sudo_password and self.reuse_ssh_password:
                raise ValueError("sudo 密码与 SSH 密码复用只能选择一种")
            if not self.sudo_password and not self.reuse_ssh_password:
                raise ValueError("密码 sudo 必须提供独立 sudo 密码或显式选择复用 SSH 密码")
        return self


class ExtensionDeployRequest(BaseModel):
    deployment_attempt_id: str = Field(pattern=r"^[a-f0-9]{32}$", min_length=32, max_length=32)
    project_id: str = Field(default="chatgpt2api", pattern=r"^[a-z0-9][a-z0-9-]*$")
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key_algorithm: str = ""
    expected_host_key: str = ""
    image: str = "ghcr.io/yukkcat/chatgpt2api:latest"
    instance_id: str = Field(default="chatgpt2api-dev", pattern=r"^[a-z0-9][a-z0-9-]{1,39}$")
    strategy: Literal["existing", "isolated", "new"] = "isolated"
    deployment_mode: Literal["compose", "warp", "python"] = "compose"
    service_port: int = Field(default=33010, ge=1, le=65535)
    confirmed_plan_id: str = ""
    clone_source_id: str = ""
    clone_scope: Literal["empty", "media", "working-copy"] = "empty"


class ExtensionDeliveryClaimRequest(BaseModel):
    deployment_attempt_id: str = Field(pattern=r"^[a-f0-9]{32}$", min_length=32, max_length=32)


class ExtensionTaskResumeRequest(BaseModel):
    target_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class PushSourceProvisionRequest(BaseModel):
    """Request a Push source for one opaque managed-instance handle."""

    instance_handle: str = Field(pattern=r"^i-[a-f0-9]{32}$")
    save_push_key_locally: bool = False


class PushSourceRotateRequest(BaseModel):
    save_push_key_locally: bool = False


class PushKeyLocalSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=256)
    destination_url: str = Field(min_length=1, max_length=500)
    push_key: str = Field(min_length=1, max_length=8192)
    confirmation_token: str = Field(default="", min_length=0, max_length=512)
    save_push_key_locally: bool = False


class PushKeyLocalSaveConfirmationRequest(BaseModel):
    """Request a one-time server confirmation for one displayed Push key."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=256)
    push_key: str = Field(min_length=1, max_length=8192)


class ExtensionDiscoveryRequest(BaseModel):
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key_algorithm: str = ""
    expected_host_key: str = ""


class ExtensionPlanRequest(ExtensionDiscoveryRequest):
    project_id: str = Field(default="chatgpt2api", pattern=r"^[a-z0-9][a-z0-9-]*$")
    instance_id: str = Field(default="chatgpt2api-dev", pattern=r"^[a-z0-9][a-z0-9-]{1,39}$")
    strategy: Literal["existing", "isolated", "new"] = "isolated"
    deployment_mode: Literal["compose", "warp", "python"] = "compose"
    service_port: int = Field(default=33010, ge=1, le=65535)
    image: str = "ghcr.io/yukkcat/chatgpt2api:latest"
    clone_source_id: str = ""
    clone_scope: Literal["empty", "media", "working-copy"] = "empty"
    approve_plan_discovery: bool = False


class ImageIntegrationCheckRequest(BaseModel):
    image: str = Field(min_length=1, max_length=320)


class ExtensionKeyResetRequest(ExtensionDiscoveryRequest):
    instance_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,39}$")


class ManagedImageUpdatePlanRequest(BaseModel):
    """A browser may request only a reviewed immutable-image update plan."""

    instance_handle: str = Field(pattern=r"^i-[a-f0-9]{32}$")
    image: str = Field(min_length=20, max_length=320)


class ManagedImageUpdateApplyRequest(BaseModel):
    plan_id: str = Field(pattern=r"^[A-Za-z0-9_-]{20,128}$")


class VaultPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=1024)


class ManagedCredential(BaseModel):
    admin_key: str = Field(default="", max_length=8192)
    ssh_password: str = Field(default="", max_length=8192)
    ssh_private_key: str = Field(default="", max_length=16384)
    ssh_passphrase: str = Field(default="", max_length=8192)
    sudo_password: str = Field(default="", max_length=8192)
    username: str = Field(default="", max_length=512)
    password: str = Field(default="", max_length=8192)
    api_key: str = Field(default="", max_length=8192)
    genbox_push_key: str = Field(default="", max_length=8192)
    genbox_push_source_id: str = Field(default="", max_length=256)
    genbox_push_url: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=8192)

    @model_validator(mode="after")
    def require_credential(self):
        # SSH-only access is valid for controlled maintenance and image updates.
        if not any((
            self.admin_key,
            self.ssh_password,
            self.ssh_private_key,
            self.username,
            self.password,
            self.api_key,
            self.genbox_push_key,
        )):
            raise ValueError("至少填写一项托管实例凭证")
        return self


class ManagedCredentialUpsertRequest(BaseModel):
    credential: ManagedCredential
    push_key_save_confirmed: bool = False


class ExtensionTestRequest(BaseModel):
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key_algorithm: str = ""
    expected_host_key: str = ""


class NetworkConnectRequest(BaseModel):
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key_algorithm: str = ""
    expected_host_key: str = ""
    provider: Literal["tailscale", "netbird", "cloudflare"]
    enrollment_token: SecretStr = Field(default_factory=lambda: SecretStr(""), max_length=4096)
    operation_mode: Literal["auto", "existing"] = "auto"
    device_name: str = Field(default="genbox-vps", pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
    management_url: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_enrollment_token_for_auto(self):
        enrollment_token = self.enrollment_token.get_secret_value()
        if self.provider != "tailscale":
            raise ValueError("当前仅 Tailscale 已具备完整的安全验证链；NetBird 和 Cloudflare 暂不可用")
        if self.operation_mode == "auto" and enrollment_token and len(enrollment_token) < 8:
            raise ValueError("Tailscale Auth Key 长度无效")
        if self.operation_mode == "existing" and enrollment_token:
            raise ValueError("仅检测已有连接时不应提交 Tailscale Auth Key")
        return self
