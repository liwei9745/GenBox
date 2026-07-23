import hashlib
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import main
import sync.manifest as manifest_mod


SOURCE_ID = "chatgpt2api-dev"
PUSH_KEY = "dummy-push-key-for-tests"
ADMIN_KEY = "dummy-admin-key-for-tests"
REQUIRED_RECEIPT_FIELDS = {
    "ok",
    "status",
    "source_id",
    "remote_path",
    "sha256",
    "local_file",
    "safe_to_delete_source",
}


def _png_bytes(color: str = "red") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (4, 3), color).save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def push_environment(tmp_path, monkeypatch):
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    monkeypatch.setattr(main, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(main, "GALLERY_DIR", gallery)
    monkeypatch.setattr(manifest_mod, "GALLERY_DIR", gallery)
    monkeypatch.setattr(manifest_mod, "MANIFEST_FILE", tmp_path / "sync_manifest.json")
    monkeypatch.setattr(manifest_mod, "LOCAL_INDEX_FILE", gallery / ".hash_index.json")
    monkeypatch.setattr(manifest_mod, "LOCAL_MD5_INDEX_FILE", gallery / ".md5_index.json")
    monkeypatch.setenv("GENBOX_PUSH_KEYS", json.dumps({SOURCE_ID: PUSH_KEY}))
    return gallery


def _headers(source_id: str = SOURCE_ID, key: str = PUSH_KEY) -> dict[str, str]:
    return {"X-GenBox-Source": source_id, "X-GenBox-Key": key}


def _push(
    client: TestClient,
    payload: bytes,
    remote_path: str = "2026/07/19/image.png",
    *,
    content_type: str = "image/png",
    headers: dict[str, str] | None = None,
    created_at: str = "2026-07-19T12:34:56+08:00",
    prompt: str = "a red square",
    model: str = "gpt-image-2",
):
    return client.post(
        "/api/sync/push",
        headers=_headers() if headers is None else headers,
        files={"image": ("image.png", payload, content_type)},
        data={
            "remote_path": remote_path,
            "created_at": created_at,
            "prompt": prompt,
            "model": model,
        },
    )


def test_push_status_route_authentication(push_environment):
    client = TestClient(main.app)

    ok = client.get("/api/sync/push/status", headers=_headers())
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
    assert ok.json()["source_id"] == SOURCE_ID

    wrong = client.get("/api/sync/push/status", headers=_headers(key="wrong-key"))
    assert wrong.status_code == 401

    missing = client.get("/api/sync/push/status")
    assert missing.status_code == 401


def test_production_push_auth_is_separate_from_admin_auth(push_environment, monkeypatch):
    monkeypatch.setenv("APP_MODE", "prod")
    monkeypatch.setenv("ADMIN_KEY", ADMIN_KEY)
    client = TestClient(main.app)
    payload = _png_bytes("orange")

    status = client.get("/api/sync/push/status", headers=_headers())
    pushed = _push(client, payload)
    assert status.status_code == 200
    assert pushed.status_code == 200
    assert "X-Admin-Key" not in _headers()

    admin_header = {"X-Admin-Key": ADMIN_KEY}
    assert client.get("/api/sync/push/status", headers=admin_header).status_code == 401
    assert client.get(
        "/api/sync/push/status",
        headers={**admin_header, **_headers(key="wrong-key")},
    ).status_code == 401
    assert _push(client, payload, headers=admin_header).status_code == 401
    assert _push(
        client,
        payload,
        headers={**admin_header, **_headers(key="wrong-key")},
    ).status_code == 401

    assert client.get("/api/gallery?limit=1").status_code == 401
    assert client.get("/api/gallery?limit=1", headers=admin_header).status_code == 200


def test_push_routes_fail_closed_for_malformed_key_configuration(push_environment, monkeypatch):
    monkeypatch.setenv("GENBOX_PUSH_KEYS", "{not-json")
    client = TestClient(main.app)

    status = client.get("/api/sync/push/status", headers=_headers())
    assert status.status_code == 503
    assert "GENBOX_PUSH_KEYS" in status.json()["detail"]

    pushed = _push(client, _png_bytes())
    assert pushed.status_code == 503
    assert "GENBOX_PUSH_KEYS" in pushed.json()["detail"]


def test_push_route_rejects_wrong_or_missing_identity(push_environment):
    client = TestClient(main.app)
    payload = _png_bytes()

    assert _push(client, payload, headers=_headers(key="wrong-key")).status_code == 401
    assert _push(client, payload, headers={}).status_code == 401


def test_push_route_rejects_malformed_source_without_echoing_key(push_environment):
    client = TestClient(main.app)
    secret = "secret-that-must-not-appear-in-errors"

    response = _push(
        client,
        _png_bytes(),
        headers={"X-GenBox-Source": "../invalid source", "X-GenBox-Key": secret},
    )

    assert response.status_code == 401
    assert secret not in response.text


def test_push_route_imports_then_is_idempotent_and_deduplicates_by_content(push_environment):
    client = TestClient(main.app)
    payload = _png_bytes()
    digest = hashlib.sha256(payload).hexdigest()

    first = _push(client, payload)
    assert first.status_code == 200
    first_receipt = first.json()
    assert REQUIRED_RECEIPT_FIELDS <= first_receipt.keys()
    assert first_receipt == {
        **first_receipt,
        "ok": True,
        "status": "imported",
        "source_id": SOURCE_ID,
        "remote_path": "2026/07/19/image.png",
        "sha256": digest,
        "safe_to_delete_source": True,
    }
    assert first_receipt["local_file"]

    repeated = _push(client, payload)
    assert repeated.status_code == 200
    repeated_receipt = repeated.json()
    assert REQUIRED_RECEIPT_FIELDS <= repeated_receipt.keys()
    assert repeated_receipt["status"] == "already-imported"
    assert repeated_receipt["local_file"] == first_receipt["local_file"]

    duplicate = _push(client, payload, remote_path="2026/07/19/other.png")
    assert duplicate.status_code == 200
    duplicate_receipt = duplicate.json()
    assert REQUIRED_RECEIPT_FIELDS <= duplicate_receipt.keys()
    assert duplicate_receipt["status"] == "duplicate-local"
    assert duplicate_receipt["local_file"] == first_receipt["local_file"]
    assert len(list(push_environment.glob("*.png"))) == 1


def test_push_changed_content_at_same_source_path_creates_a_new_receipt(push_environment):
    client = TestClient(main.app)
    remote_path = "2026/07/19/image.png"

    first = _push(client, _png_bytes("red"), remote_path=remote_path).json()
    changed = _push(client, _png_bytes("blue"), remote_path=remote_path).json()
    repeated_changed = _push(client, _png_bytes("blue"), remote_path=remote_path).json()

    assert first["status"] == "imported"
    assert changed["status"] == "imported"
    assert changed["sha256"] != first["sha256"]
    assert changed["local_file"] != first["local_file"]
    assert repeated_changed["status"] == "already-imported"
    assert repeated_changed["sha256"] == changed["sha256"]
    assert repeated_changed["local_file"] == changed["local_file"]
    assert len(list(push_environment.glob("*.png"))) == 2


@pytest.mark.parametrize(
    "remote_path",
    [
        "../secret.png",
        "/absolute.png",
        "C:/absolute.png",
        "folder\\image.png",
        "https://example.test/image.png",
        "folder//image.png",
        "folder/",
        " image.png",
    ],
)
def test_push_route_rejects_illegal_remote_path(push_environment, remote_path):
    response = _push(TestClient(main.app), _png_bytes(), remote_path=remote_path)
    assert response.status_code == 400


def test_push_route_rejects_non_image_and_wrong_content_type(push_environment):
    client = TestClient(main.app)

    non_image = _push(client, b"not an image", content_type="image/png")
    assert non_image.status_code == 422

    wrong_content_type = _push(client, _png_bytes(), content_type="application/octet-stream")
    assert wrong_content_type.status_code == 422


def test_push_preserves_png_metadata_and_exposes_gallery_source_fields(push_environment):
    client = TestClient(main.app)
    created_at = "2026-07-19T12:34:56+08:00"
    prompt = "保留 UTF-8 提示词"
    model = "gpt-image-2"
    receipt = _push(
        client,
        _png_bytes("blue"),
        created_at=created_at,
        prompt=prompt,
        model=model,
    ).json()

    image_path = push_environment / receipt["local_file"]
    with Image.open(image_path) as image:
        assert image.info["Prompt"] == prompt
        assert image.info["Model"] == model
        assert image.info["CreatedAt"] == created_at
        assert image.info["SourcePath"] == "2026/07/19/image.png"
        assert image.info["SourceDeployment"] == SOURCE_ID
        assert image.info["Source"] == "cloud"
        assert image.info["Tags"] == "cloud-sync"

    gallery = client.get("/api/gallery?limit=10")
    assert gallery.status_code == 200
    item = next(entry for entry in gallery.json()["items"] if entry["id"] == image_path.stem)
    assert item["source_path"] == "2026/07/19/image.png"
    assert item["source_deployment"] == SOURCE_ID
    assert item["source_created_at"] == created_at


def test_concurrent_identical_pushes_create_one_gallery_file(push_environment):
    payload = _png_bytes("green")
    barrier = threading.Barrier(2)

    def send_once():
        barrier.wait(timeout=5)
        return _push(TestClient(main.app), payload)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: send_once(), range(2)))

    assert all(response.status_code == 200 for response in responses)
    statuses = sorted(response.json()["status"] for response in responses)
    assert statuses == ["already-imported", "imported"]
    assert len(list(push_environment.glob("*.png"))) == 1
    assert len({response.json()["local_file"] for response in responses}) == 1


def test_manifest_and_local_indexes_use_atomic_replace(push_environment, monkeypatch):
    calls: list[tuple[Path, Path]] = []
    original_replace = manifest_mod.os.replace

    def record_replace(source, destination):
        calls.append((Path(source), Path(destination)))
        return original_replace(source, destination)

    monkeypatch.setattr(manifest_mod.os, "replace", record_replace)
    manifest = manifest_mod.SyncManifest()
    manifest.add(SOURCE_ID, "a.png", "local.png", "abc", 3, "")
    index = manifest_mod.LocalImageIndex()
    index.index["abc"] = "local.png"
    index.md5_index["def"] = "local.png"
    index.save()

    destinations = {destination for _, destination in calls}
    assert manifest_mod.MANIFEST_FILE in destinations
    assert manifest_mod.LOCAL_INDEX_FILE in destinations
    assert manifest_mod.LOCAL_MD5_INDEX_FILE in destinations
    assert not list(push_environment.parent.rglob("*.tmp"))
