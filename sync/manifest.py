"""
同步清单与本地去重索引。

- SyncManifest: 记录已导入的远端图片（deployment_id::path -> 本地路径/sha256/时间）。
- LocalImageIndex: 本地图库全部 PNG 的内容 SHA-256 增量索引，用于“远端图片是否已存在于本地”。

存储位置（均在 storage/，已被 .gitignore 忽略）：
- storage/sync_manifest.json
- storage/gallery/.hash_index.json
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Optional

from config import GALLERY_DIR, STORAGE_DIR
from sync.client import sha256_bytes

MANIFEST_FILE = STORAGE_DIR / "sync_manifest.json"
LOCAL_INDEX_FILE = GALLERY_DIR / ".hash_index.json"
LOCAL_MD5_INDEX_FILE = GALLERY_DIR / ".md5_index.json"

# 本地索引里记录但文件已丢失的条目，定期清理阈值（秒），默认 7 天不强制
MANIFEST_VERSION = 1


# ──────────────────────────────────────────────────────────────
# 远端导入清单
# ──────────────────────────────────────────────────────────────
class SyncManifest:
    """已导入记录的持久化清单。"""

    def __init__(self):
        self.entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if MANIFEST_FILE.exists():
            try:
                data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
                self.entries = data.get("entries", {}) or {}
            except Exception as e:  # noqa
                print(f"[SyncManifest] 读取失败，重置: {e}")
                self.entries = {}

    def save(self):
        MANIFEST_FILE.write_text(
            json.dumps(
                {"version": MANIFEST_VERSION, "entries": self.entries},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.entries.get(key)

    def is_synced(self, deployment_id: str, path: str, size: int = 0) -> bool:
        e = self.get(f"{deployment_id}::{path}")
        if not e:
            return False
        # 远端 size 未变且 created_at 一致 → 视为已同步（避免每次重新下载校验）
        if size and e.get("size") and e["size"] != size:
            return False
        return True

    def add(self, deployment_id: str, path: str, local_path: str, sha256: str,
            size: int, remote_created_at: str):
        self.entries[f"{deployment_id}::{path}"] = {
            "local_path": local_path,
            "sha256": sha256,
            "size": size,
            "remote_created_at": remote_created_at,
            "synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.save()


# ──────────────────────────────────────────────────────────────
# 本地内容去重索引（增量）
# ──────────────────────────────────────────────────────────────
class LocalImageIndex:
    """本地图库 PNG 的内容哈希索引，用于判断“远端图是否已存在于本地”。"""

    def __init__(self):
        self.index: Dict[str, str] = {}  # sha256 -> filename
        self.md5_index: Dict[str, str] = {}  # md5 -> filename
        self._load()

    def _load(self):
        if LOCAL_INDEX_FILE.exists():
            try:
                self.index = json.loads(LOCAL_INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:  # noqa
                self.index = {}
        if LOCAL_MD5_INDEX_FILE.exists():
            try:
                self.md5_index = json.loads(LOCAL_MD5_INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:  # noqa
                self.md5_index = {}

    def save(self):
        LOCAL_INDEX_FILE.write_text(
            json.dumps(self.index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        LOCAL_MD5_INDEX_FILE.write_text(
            json.dumps(self.md5_index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def contains_hash(self, sha256: str) -> bool:
        return sha256 in self.index

    def contains_md5(self, md5: str) -> bool:
        return md5.lower() in self.md5_index

    def ensure_md5_index(self):
        """增量建立本地原图 MD5 索引，用于匹配 chatgpt2api 文件名内容哈希。"""
        known_files = set(self.md5_index.values())
        current_files = {f.name for f in GALLERY_DIR.glob("*.png")}
        self.md5_index = {
            digest: filename for digest, filename in self.md5_index.items()
            if filename in current_files
        }
        known_files = set(self.md5_index.values())
        for path in GALLERY_DIR.glob("*.png"):
            if path.name in known_files:
                continue
            try:
                digest = hashlib.md5(path.read_bytes()).hexdigest()
                self.md5_index[digest] = path.name
            except Exception:  # noqa
                continue
        self.save()

    def ensure_file_hashed(self, path: Path) -> Optional[str]:
        """若文件尚未索引则计算哈希并写入；返回 sha256。"""
        filename = path.name
        # 反向查：若该文件名已在索引中，直接返回对应 hash（避免重复计算）
        for h, fn in self.index.items():
            if fn == filename:
                return h
        try:
            data = path.read_bytes()
            h = sha256_bytes(data)
        except Exception:  # noqa
            return None
        self.index[h] = filename
        return h

    def rebuild(self):
        """全量重建本地索引（仅在需要时调用）。"""
        self.index = {}
        for f in GALLERY_DIR.glob("*.png"):
            try:
                self.index[sha256_bytes(f.read_bytes())] = f.name
            except Exception:  # noqa
                continue
        self.save()

    def hash_known_locally(self, sha256: str) -> bool:
        return sha256 in self.index
