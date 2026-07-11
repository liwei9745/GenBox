"""
同步部署配置的持久化存储。

独立存于 storage/sync.json（已被 .gitignore 忽略），与 providers.json 分开，
避免把远端 token 混入 provider 配置。
"""
import json
import uuid
from typing import List

from config import STORAGE_DIR
from sync.models import SyncDeployment, SyncConfig


SYNC_FILE = STORAGE_DIR / "sync.json"


def load_sync_config() -> SyncConfig:
    if SYNC_FILE.exists():
        try:
            raw = json.loads(SYNC_FILE.read_text(encoding="utf-8"))
            return SyncConfig(**raw)
        except Exception as e:  # noqa
            print(f"[SyncStore] 读取失败，使用空配置: {e}")
    return SyncConfig()


def save_sync_config(cfg: SyncConfig):
    SYNC_FILE.write_text(
        cfg.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )


def get_deployment(deployment_id: str) -> SyncDeployment | None:
    for d in load_sync_config().deployments:
        if d.id == deployment_id:
            return d
    return None


def upsert_deployment(data: dict) -> SyncDeployment:
    cfg = load_sync_config()
    dep_id = data.get("id") or str(uuid.uuid4())[:8]
    existing = {d.id: d for d in cfg.deployments}
    dep = SyncDeployment(
        id=dep_id,
        name=data.get("name", dep_id),
        base_url=data.get("base_url", ""),
        api_key=data.get("api_key", ""),
        enabled=data.get("enabled", True),
        api_version=data.get("api_version"),
    )
    existing[dep_id] = dep
    cfg.deployments = list(existing.values())
    save_sync_config(cfg)
    return dep


def delete_deployment(deployment_id: str) -> bool:
    cfg = load_sync_config()
    before = len(cfg.deployments)
    cfg.deployments = [d for d in cfg.deployments if d.id != deployment_id]
    if len(cfg.deployments) != before:
        save_sync_config(cfg)
        return True
    return False


def list_deployments() -> List[SyncDeployment]:
    return load_sync_config().deployments
