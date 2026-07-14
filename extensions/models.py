from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ExtensionTarget(BaseModel):
    id: str
    name: str
    host: str
    port: int = Field(default=22, ge=1, le=65535)
    username: str
    host_key: str = ""
    primary_network: Literal["tailscale", "netbird", "cloudflare"] = "tailscale"
    available_networks: list[Literal["tailscale", "netbird", "cloudflare"]] = Field(default_factory=list)
    network_url: str = ""
    network_verified_at: str = ""
    chatgpt2api_port: int = Field(default=3000, ge=1, le=65535)
    created_at: str = ""
    updated_at: str = ""


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
    clone_source_id: str = ""
    clone_scope: Literal["empty", "media", "working-copy"] = "empty"
    created_at: str = ""
    updated_at: str = ""


class ExtensionConfig(BaseModel):
    targets: list[ExtensionTarget] = Field(default_factory=list)
    instances: list[ExtensionInstance] = Field(default_factory=list)
    batch_target_ids: list[str] = Field(default_factory=list)


class ExtensionBatchTargetsRequest(BaseModel):
    target_ids: list[str] = Field(default_factory=list, max_length=100)


class SSHCredential(BaseModel):
    password: str = ""
    private_key: str = ""
    passphrase: str = ""
    sudo_password: str = ""


class ExtensionDeployRequest(BaseModel):
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key: str = ""
    image: str = "ghcr.io/yukkcat/chatgpt2api:latest"
    instance_id: str = Field(default="chatgpt2api-dev", pattern=r"^[a-z0-9][a-z0-9-]{1,39}$")
    strategy: Literal["existing", "isolated", "new"] = "isolated"
    deployment_mode: Literal["compose", "warp", "python"] = "compose"
    confirmed_plan_id: str = ""
    clone_source_id: str = ""
    clone_scope: Literal["empty", "media", "working-copy"] = "empty"


class ExtensionDiscoveryRequest(BaseModel):
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key: str = ""


class ExtensionPlanRequest(ExtensionDiscoveryRequest):
    instance_id: str = Field(default="chatgpt2api-dev", pattern=r"^[a-z0-9][a-z0-9-]{1,39}$")
    strategy: Literal["existing", "isolated", "new"] = "isolated"
    deployment_mode: Literal["compose", "warp", "python"] = "compose"
    service_port: int = Field(default=33010, ge=1, le=65535)
    image: str = "ghcr.io/yukkcat/chatgpt2api:latest"
    clone_source_id: str = ""
    clone_scope: Literal["empty", "media", "working-copy"] = "empty"


class ExtensionKeyResetRequest(ExtensionDiscoveryRequest):
    instance_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,39}$")


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
    note: str = Field(default="", max_length=8192)

    @model_validator(mode="after")
    def require_credential(self):
        if not any((self.admin_key, self.username, self.password, self.api_key)):
            raise ValueError("至少填写一项托管实例凭证")
        return self


class ManagedCredentialUpsertRequest(BaseModel):
    credential: ManagedCredential


class ExtensionTestRequest(BaseModel):
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key: str = ""


class NetworkConnectRequest(BaseModel):
    target: ExtensionTarget
    credential: SSHCredential
    trust_host_key: bool = False
    expected_host_key: str = ""
    provider: Literal["tailscale", "netbird", "cloudflare"]
    enrollment_token: str = Field(default="", max_length=4096)
    operation_mode: Literal["auto", "existing"] = "auto"
    device_name: str = Field(default="genbox-vps", pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
    management_url: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_enrollment_token_for_auto(self):
        if self.operation_mode == "auto" and len(self.enrollment_token) < 8:
            raise ValueError("自动安装需要一次性授权信息")
        return self
