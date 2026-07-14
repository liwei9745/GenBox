"""sync 模块单元测试（无需联网/无需启动服务）。

覆盖：哈希、URL 安全、base_url 归一化、部署配置持久化、清单去重、本地索引、筛选元数据。
"""
import sys
import hashlib
from pathlib import Path

import pytest

# 确保仓库根在 sys.path（直接运行 pytest 时）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sync.client import sha256_bytes, is_url_safe, _normalize_base_url, ChatGPT2APIClient, extract_image_metadata
from sync.models import RemoteImageRecord, SyncConfig, SyncDeployment
from sync.ingest import authenticate_push_source, load_push_keys, validate_image_payload
import sync.store as store
import sync.manifest as manifest_mod
from PIL import Image
import io


def test_sha256_known():
    assert sha256_bytes(b"hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_normalize_base_url_strips_v1():
    assert _normalize_base_url("http://host:3000/v1/") == "http://host:3000"
    assert _normalize_base_url("http://host:3000/") == "http://host:3000"
    assert _normalize_base_url("http://host:3000") == "http://host:3000"


def test_is_url_safe_blocks_private():
    ok, _ = is_url_safe("http://example.com/x.png")
    # 允许公网（若本机无 DNS 则可能 False，仅断言内网必拦）
    bad, err = is_url_safe("http://127.0.0.1/x.png")
    assert bad is False
    bad2, _ = is_url_safe("http://192.168.1.1/x.png")
    assert bad2 is False
    bad3, _ = is_url_safe("http://10.0.0.5/x.png")
    assert bad3 is False


def test_client_resolve_url():
    c = ChatGPT2APIClient("http://host:3000", "tok")
    assert c.resolve_url("/images/a.png") == "http://host:3000/images/a.png"
    assert c.resolve_url("http://host:3000/images/a.png") == "http://host:3000/images/a.png"


def test_remote_record_aspect():
    sq = RemoteImageRecord(deployment_id="d", path="p", width=512, height=512)
    assert sq.aspect == "square"
    por = RemoteImageRecord(deployment_id="d", path="p", width=512, height=1024)
    assert por.aspect == "portrait"
    lan = RemoteImageRecord(deployment_id="d", path="p", width=1024, height=512)
    assert lan.aspect == "landscape"
    unk = RemoteImageRecord(deployment_id="d", path="p")
    assert unk.aspect == "unknown"
    assert sq.key == "d::p"


def test_extract_image_metadata_correlates_prompt_and_model():
    metadata = extract_image_metadata([{
        "detail": {
            "endpoint": "/v1/images/generations",
            "model": "gpt-image-2",
            "request_text": "short",
            "request_text_full": "original prompt",
            "urls": ["http://remote/images/a.png"],
        }
    }])

    assert metadata["http://remote/images/a.png"] == {
        "prompt": "original prompt",
        "model": "gpt-image-2",
    }


def test_sync_config_roundtrip(tmp_path, monkeypatch):
    f = tmp_path / "sync.json"
    monkeypatch.setattr(store, "SYNC_FILE", f)
    dep = store.upsert_deployment({"name": "VPS", "base_url": "http://h:3000", "api_key": "secret"})
    assert dep.id
    cfg = store.load_sync_config()
    assert len(cfg.deployments) == 1
    assert cfg.deployments[0].api_key == "secret"
    got = store.get_deployment(dep.id)
    assert got is not None and got.base_url == "http://h:3000"
    assert store.delete_deployment(dep.id) is True
    assert store.get_deployment(dep.id) is None


def test_manifest_dedup(tmp_path, monkeypatch):
    mf = tmp_path / "sync_manifest.json"
    monkeypatch.setattr(manifest_mod, "MANIFEST_FILE", mf)
    m = manifest_mod.SyncManifest()
    assert m.is_synced("d", "p1", 100) is False
    m.add("d", "p1", "/g/x.png", "abc", 100, "2026-07-11 12:00:00")
    # size 一致 → 视为已同步
    assert m.is_synced("d", "p1", 100) is True
    # size 变化 → 视为未同步
    assert m.is_synced("d", "p1", 200) is False
    # 重新加载从磁盘恢复
    m2 = manifest_mod.SyncManifest()
    assert m2.is_synced("d", "p1", 100) is True


def test_local_index_hash(tmp_path, monkeypatch):
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    idx_file = gallery / ".hash_index.json"
    md5_file = gallery / ".md5_index.json"
    monkeypatch.setattr(manifest_mod, "GALLERY_DIR", gallery)
    monkeypatch.setattr(manifest_mod, "LOCAL_INDEX_FILE", idx_file)
    monkeypatch.setattr(manifest_mod, "LOCAL_MD5_INDEX_FILE", md5_file)
    img = gallery / "a.png"
    img.write_bytes(b"\x89PNG dummy")
    h = sha256_bytes(img.read_bytes())
    idx = manifest_mod.LocalImageIndex()
    got = idx.ensure_file_hashed(img)
    assert got == h
    assert idx.contains_hash(h) is True
    # 持久化后可重建
    idx.save()
    idx2 = manifest_mod.LocalImageIndex()
    assert idx2.contains_hash(h) is True


def test_local_sha256_index_discovers_existing_files(tmp_path, monkeypatch):
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    monkeypatch.setattr(manifest_mod, "GALLERY_DIR", gallery)
    monkeypatch.setattr(manifest_mod, "LOCAL_INDEX_FILE", gallery / ".hash_index.json")
    monkeypatch.setattr(manifest_mod, "LOCAL_MD5_INDEX_FILE", gallery / ".md5_index.json")
    image = gallery / "existing.png"
    image.write_bytes(b"existing image bytes")

    idx = manifest_mod.LocalImageIndex()
    idx.ensure_sha256_index()

    assert idx.contains_hash(hashlib.sha256(image.read_bytes()).hexdigest()) is True


def test_local_md5_index(tmp_path, monkeypatch):
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    monkeypatch.setattr(manifest_mod, "GALLERY_DIR", gallery)
    monkeypatch.setattr(manifest_mod, "LOCAL_INDEX_FILE", gallery / ".hash_index.json")
    monkeypatch.setattr(manifest_mod, "LOCAL_MD5_INDEX_FILE", gallery / ".md5_index.json")
    image = gallery / "a.png"
    image.write_bytes(b"same image bytes")

    idx = manifest_mod.LocalImageIndex()
    idx.ensure_md5_index()

    digest = hashlib.md5(b"same image bytes").hexdigest()
    assert idx.contains_md5(digest) is True
    assert idx.md5_index[digest] == "a.png"


def test_push_source_auth_requires_matching_identity_and_key():
    raw = '{"vps-a":"secret-a","vps-b":"secret-b"}'
    assert load_push_keys(raw) == {"vps-a": "secret-a", "vps-b": "secret-b"}
    assert authenticate_push_source("vps-a", "secret-a", raw) is True
    assert authenticate_push_source("vps-a", "secret-b", raw) is False
    assert authenticate_push_source("../vps-a", "secret-a", raw) is False


def test_validate_push_image_payload():
    output = io.BytesIO()
    Image.new("RGB", (3, 2), "red").save(output, format="PNG")
    payload = output.getvalue()

    metadata = validate_image_payload(payload, "image/png")

    assert metadata["width"] == 3
    assert metadata["height"] == 2
    assert metadata["size"] == len(payload)
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()


def test_validate_push_image_rejects_non_image():
    with pytest.raises(ValueError, match="invalid image payload"):
        validate_image_payload(b"not an image", "image/png")
