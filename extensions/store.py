import json
import hmac
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
        raw = json.loads(EXTENSIONS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[Extensions] 配置读取失败: {exc}")
        return ExtensionConfig()
    if not isinstance(raw, dict):
        return ExtensionConfig()
    targets = []
    invalid_targets = 0
    raw_targets = raw.get("targets", [])
    if not isinstance(raw_targets, list):
        raw_targets = []
        invalid_targets += 1
    for item in raw_targets:
        try:
            targets.append(ExtensionTarget(**item))
        except Exception:
            invalid_targets += 1
    instances = []
    invalid_instances = 0
    raw_instances = raw.get("instances", [])
    if not isinstance(raw_instances, list):
        raw_instances = []
        invalid_instances += 1
    for item in raw_instances:
        try:
            instances.append(ExtensionInstance(**item))
        except Exception:
            invalid_instances += 1
    if invalid_targets or invalid_instances:
        print(
            "[Extensions] 已隔离无效配置记录: "
            f"targets={invalid_targets}, instances={invalid_instances}"
        )
    batch_target_ids = raw.get("batch_target_ids", [])
    if not isinstance(batch_target_ids, list):
        batch_target_ids = []
    return ExtensionConfig(
        targets=targets,
        instances=instances,
        batch_target_ids=[str(item) for item in batch_target_ids],
    )


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


def save_target_metadata(data: dict) -> ExtensionTarget:
    """Save browser-editable target metadata without accepting trust material."""
    config = load_config()
    target_id = str(data.get("id") or uuid.uuid4().hex[:8])
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    existing = next((item for item in config.targets if item.id == target_id), None)
    browser_fields = {"name", "host", "port", "username", "chatgpt2api_port"}
    submitted = {key: value for key, value in data.items() if key in browser_fields}
    same_identity = bool(existing) and (
        str(submitted.get("host", existing.host)) == existing.host
        and int(submitted.get("port", existing.port)) == existing.port
        and str(submitted.get("username", existing.username)) == existing.username
    )
    trust_state = {
        "host_key_algorithm": existing.host_key_algorithm if same_identity else "",
        "host_key": existing.host_key if same_identity else "",
        "available_networks": existing.available_networks if same_identity else [],
        "network_url": existing.network_url if same_identity else "",
        "network_verified_at": existing.network_verified_at if same_identity else "",
    }
    target = ExtensionTarget(
        **{
            **(existing.model_dump() if existing else {}),
            **submitted,
            "id": target_id,
            **trust_state,
            "created_at": existing.created_at if existing else now,
            "updated_at": now,
        }
    )
    config.targets = [item for item in config.targets if item.id != target_id] + [target]
    save_config(config)
    return target


def confirm_target_host_key(
    expected: ExtensionTarget,
    algorithm: str,
    fingerprint: str,
) -> ExtensionTarget:
    """Persist a probed identity pair only if target and trust state are unchanged."""
    config = load_config()
    current = next((item for item in config.targets if item.id == expected.id), None)
    if not current:
        raise ValueError("target_missing")
    comparisons = (
        hmac.compare_digest(current.host, expected.host),
        hmac.compare_digest(str(current.port), str(expected.port)),
        hmac.compare_digest(current.username, expected.username),
        hmac.compare_digest(current.host_key_algorithm, expected.host_key_algorithm),
        hmac.compare_digest(current.host_key, expected.host_key),
    )
    if not all(comparisons):
        raise ValueError("target_changed")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    confirmed = current.model_copy(update={
        "host_key_algorithm": algorithm,
        "host_key": fingerprint,
        "updated_at": now,
    })
    config.targets = [item for item in config.targets if item.id != current.id] + [confirmed]
    save_config(config)
    return confirmed


def list_targets() -> list[ExtensionTarget]:
    return load_config().targets


def get_target(target_id: str) -> ExtensionTarget | None:
    return next((item for item in load_config().targets if item.id == target_id), None)


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
    target_id = str(data.get("target_id") or "").strip()
    if existing and existing.target_id != target_id:
        raise ValueError("instance_id_conflicts_with_another_target")
    merged = dict(data)
    if existing:
        for field in (
            "status", "data_dir", "ownership", "container_id", "container_name",
            "install_dir", "compose_project", "image", "console_url", "api_url",
        ):
            unknown_values = {None, "", "unknown"} if field == "status" else {None, ""}
            if merged.get(field) in unknown_values:
                merged.pop(field, None)
        if existing.managed:
            merged["managed"] = True
            merged["ownership"] = existing.ownership or "managed"
            merged["service_port"] = existing.service_port
    instance = ExtensionInstance(**{
        **(existing.model_dump() if existing else {}),
        **merged,
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
