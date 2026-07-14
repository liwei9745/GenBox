import json
import os
import time
import uuid

from config import STORAGE_DIR
from extensions.models import ExtensionConfig, ExtensionInstance, ExtensionTarget


EXTENSIONS_FILE = STORAGE_DIR / "extensions.json"


def load_config() -> ExtensionConfig:
    if not EXTENSIONS_FILE.exists():
        return ExtensionConfig()
    try:
        return ExtensionConfig(**json.loads(EXTENSIONS_FILE.read_text(encoding="utf-8")))
    except Exception as exc:
        print(f"[Extensions] 配置读取失败: {exc}")
        return ExtensionConfig()


def save_config(config: ExtensionConfig) -> None:
    EXTENSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = EXTENSIONS_FILE.with_name(f".{EXTENSIONS_FILE.name}.{os.getpid()}.tmp")
    temporary.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary, EXTENSIONS_FILE)


def upsert_target(data: dict) -> ExtensionTarget:
    config = load_config()
    target_id = str(data.get("id") or uuid.uuid4().hex[:8])
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    existing = next((item for item in config.targets if item.id == target_id), None)
    target = ExtensionTarget(
        **{
            **(existing.model_dump() if existing else {}),
            **data,
            "id": target_id,
            "created_at": existing.created_at if existing else now,
            "updated_at": now,
        }
    )
    config.targets = [item for item in config.targets if item.id != target_id] + [target]
    save_config(config)
    return target


def list_targets() -> list[ExtensionTarget]:
    return load_config().targets


def get_batch_target_ids() -> list[str]:
    config = load_config()
    valid_ids = {target.id for target in config.targets}
    return [target_id for target_id in config.batch_target_ids if target_id in valid_ids]


def save_batch_target_ids(target_ids: list[str]) -> list[str]:
    config = load_config()
    valid_ids = {target.id for target in config.targets}
    selected = list(dict.fromkeys(target_id for target_id in target_ids if target_id in valid_ids))
    config.batch_target_ids = selected
    save_config(config)
    return selected


def delete_target(target_id: str) -> bool:
    config = load_config()
    remaining = [item for item in config.targets if item.id != target_id]
    if len(remaining) == len(config.targets):
        return False
    config.targets = remaining
    save_config(config)
    return True


def upsert_instance(data: dict) -> ExtensionInstance:
    config = load_config()
    instance_id = str(data.get("id") or "").strip()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    existing = next((item for item in config.instances if item.id == instance_id), None)
    instance = ExtensionInstance(**{
        **(existing.model_dump() if existing else {}),
        **data,
        "id": instance_id,
        "created_at": existing.created_at if existing else now,
        "updated_at": now,
    })
    config.instances = [item for item in config.instances if item.id != instance_id] + [instance]
    save_config(config)
    return instance


def list_instances(target_id: str = "") -> list[ExtensionInstance]:
    items = load_config().instances
    return [item for item in items if not target_id or item.target_id == target_id]


def get_instance(instance_id: str) -> ExtensionInstance | None:
    return next((item for item in load_config().instances if item.id == instance_id), None)
