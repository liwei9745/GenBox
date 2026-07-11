"""CSRF middleware regression tests."""
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

import main
import sync.store as sync_store


def test_same_origin_mutation_is_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_store, "SYNC_FILE", tmp_path / "sync.json")
    client = TestClient(main.app, base_url="http://testserver")

    response = client.post(
        "/api/sync/deployments",
        headers={"Origin": "http://testserver"},
        json={"name": "test", "base_url": "http://example.com", "api_key": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["deployment"]["name"] == "test"
    assert "api_key" not in response.json()["deployment"]


def test_cross_origin_mutation_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_store, "SYNC_FILE", tmp_path / "sync.json")
    client = TestClient(main.app, base_url="http://testserver")

    response = client.post(
        "/api/sync/deployments",
        headers={"Origin": "http://attacker.invalid"},
        json={"name": "test", "base_url": "http://example.com", "api_key": "secret"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_REJECTED"
    assert not (tmp_path / "sync.json").exists()


def test_thumbnail_proxy_is_same_origin_and_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_store, "SYNC_FILE", tmp_path / "sync.json")
    monkeypatch.setattr(main, "STORAGE_DIR", tmp_path)
    dep = sync_store.upsert_deployment({
        "name": "remote",
        "base_url": "http://images.example.com:3000",
        "api_key": "secret",
    })
    calls = []

    async def fake_download(self, url):
        calls.append(url)
        return b"fake-png-bytes"

    monkeypatch.setattr(main.ChatGPT2APIClient, "download", fake_download)
    client = TestClient(main.app, base_url="http://testserver")
    params = {
        "deployment_id": dep.id,
        "url": "http://images.example.com:3000/image-thumbnails/a.png",
    }

    first = client.get("/api/sync/thumbnail", params=params)
    second = client.get("/api/sync/thumbnail", params=params)

    assert first.status_code == 200
    assert first.content == b"fake-png-bytes"
    assert second.status_code == 200
    assert len(calls) == 1


def test_thumbnail_proxy_rejects_other_hosts(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_store, "SYNC_FILE", tmp_path / "sync.json")
    dep = sync_store.upsert_deployment({
        "name": "remote",
        "base_url": "http://images.example.com:3000",
        "api_key": "secret",
    })
    client = TestClient(main.app, base_url="http://testserver")

    response = client.get("/api/sync/thumbnail", params={
        "deployment_id": dep.id,
        "url": "http://attacker.invalid/image.png",
    })

    assert response.status_code == 400


def test_synced_image_preserves_prompt_model_and_cloud_tags(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    source = BytesIO()
    Image.new("RGB", (2, 2), "red").save(source, format="PNG")

    local_path, _ = main._save_synced_image(
        source.getvalue(), "remote", "2026/07/a.png", "2026-07-11 12:00:00",
        "original prompt", "gpt-image-2",
    )

    with Image.open(local_path) as saved:
        assert saved.info["Prompt"] == "original prompt"
        assert saved.info["Model"] == "gpt-image-2"
        assert saved.info["Source"] == "cloud"
        assert saved.info["Tags"] == "cloud-sync"


def test_refresh_synced_image_metadata_repairs_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    path = tmp_path / "remote_old.png"
    Image.new("RGB", (2, 2), "blue").save(path, format="PNG")

    changed = main._refresh_synced_image_metadata(
        str(path), "remote", "2026/07/old.png", "2026-07-11 12:00:00",
        "recovered prompt", "gpt-image-2",
    )

    assert changed is True
    with Image.open(path) as saved:
        assert saved.info["Prompt"] == "recovered prompt"
        assert saved.info["Model"] == "gpt-image-2"
        assert saved.info["Source"] == "cloud"
