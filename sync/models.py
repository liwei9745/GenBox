"""
sync 模块：远程 chatgpt2api 兼容部署的图片同步。

设计要点（见 .planning/research/SUMMARY.md）：
- 去重键 = 下载内容的 SHA-256（远端不暴露稳定 hash，文件名/URL/ETag 不可靠）。
- 远端身份键 = deployment_id + path（path 是远端操作身份）。
- 凭证只存于 storage/sync.json（已被 .gitignore 忽略），绝不入库/打印。
- 下载在服务端用 httpx 完成，且校验主机（防 SSRF / 浏览器外泄）。
- created_at 按 Asia/Shanghai 解释（远端无时区偏移）。
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SyncDeployment(BaseModel):
    """一个远程 chatgpt2api 兼容部署的连接配置。"""
    id: str
    name: str
    base_url: str
    api_key: str = ""          # 远端 admin Bearer token；仅存于 storage/，不入库
    enabled: bool = True
    api_version: Optional[str] = None  # 可选：锁定远端版本，便于 :latest 漂移时降级


class SyncConfig(BaseModel):
    """同步总配置（多个部署）。"""
    deployments: List[SyncDeployment] = []


class RemoteImageRecord(BaseModel):
    """归一化后的远端图片记录。"""
    deployment_id: str
    path: str                    # 远端操作身份（用于 fetch/delete）
    name: str = ""
    filename: str = ""
    url: str = ""               # 原始文件地址（服务端下载用）
    thumbnail_url: str = ""
    created_at: str = ""        # Asia/Shanghai 字符串，无偏移
    size: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    remote_type: str = "image"
    prompt: str = ""
    model: str = ""

    @property
    def key(self) -> str:
        return f"{self.deployment_id}::{self.path}"

    @property
    def aspect(self) -> str:
        if not self.width or not self.height:
            return "unknown"
        if self.width == self.height:
            return "square"
        return "portrait" if self.height > self.width else "landscape"


class SyncCandidate(BaseModel):
    """预览时返回给前端的候选（含去重状态与筛选元数据）。"""
    deployment_id: str
    path: str
    name: str = ""
    url: str = ""
    thumbnail_url: str = ""
    created_at: str = ""
    size: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    aspect: str = "unknown"
    sha256: str = ""             # 下载后计算；未下载时为 ""
    status: str = "new"          # new | duplicate-local | already-synced
    reason: str = ""
    prompt: str = ""
    model: str = ""


class SyncImportRequest(BaseModel):
    deployment_id: str
    paths: List[str] = Field(default_factory=list)   # 要导入的远端 path 列表
