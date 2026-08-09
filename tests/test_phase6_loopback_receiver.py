import hashlib
import io
import json
import socket
import threading
import time
import uuid

import httpx
import pytest
import uvicorn
from PIL import Image

import main
import sync.manifest as manifest_mod


def _synthetic_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (3, 2), "navy").save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def loopback_receiver(tmp_path, monkeypatch):
    """Start the real receiver only on an OS-assigned IPv4 loopback port."""
    gallery = tmp_path / "receiver-gallery"
    gallery.mkdir()
    source_id = f"synthetic-source-{uuid.uuid4().hex[:16]}"
    push_key = f"synthetic-{uuid.uuid4().hex}"
    monkeypatch.setattr(main, "STORAGE_DIR", tmp_path / "receiver-storage")
    monkeypatch.setattr(main, "GALLERY_DIR", gallery)
    monkeypatch.setattr(manifest_mod, "GALLERY_DIR", gallery)
    monkeypatch.setattr(manifest_mod, "MANIFEST_FILE", tmp_path / "sync_manifest.json")
    monkeypatch.setattr(manifest_mod, "LOCAL_INDEX_FILE", gallery / ".hash_index.json")
    monkeypatch.setattr(manifest_mod, "LOCAL_MD5_INDEX_FILE", gallery / ".md5_index.json")
    monkeypatch.setenv("GENBOX_PUSH_KEYS", json.dumps({source_id: push_key}))

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="critical")
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started, "loopback-only receiver did not start"

    try:
        yield f"http://127.0.0.1:{port}", source_id, push_key, gallery
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        assert not thread.is_alive(), "loopback-only receiver did not stop"


def test_phase6_synthetic_loopback_push_retains_sender_file(loopback_receiver, tmp_path):
    """A disposable sender-shaped input reaches the receiver without cleanup authority."""
    base_url, source_id, push_key, gallery = loopback_receiver
    sender_dir = tmp_path / "synthetic-sender"
    sender_dir.mkdir()
    source = sender_dir / "synthetic-image.png"
    payload = _synthetic_png()
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    headers = {"X-GenBox-Source": source_id, "X-GenBox-Key": push_key}

    with httpx.Client(
        base_url=base_url,
        timeout=5.0,
        trust_env=False,
        headers={"Connection": "close"},
    ) as client:
        status = client.get("/api/sync/push/status", headers=headers)
        pushed = client.post(
            "/api/sync/push",
            headers=headers,
            files={"image": (source.name, payload, "image/png")},
            data={
                "remote_path": f"synthetic/{source_id}/image.png",
                "created_at": "2026-08-09T00:00:00+00:00",
                "prompt": "synthetic phase 6 fixture",
                "model": "synthetic-model",
                "source_sha256": digest,
            },
        )

    assert status.status_code == 200
    assert status.json()["source_id"] == source_id
    assert pushed.status_code == 200
    receipt = pushed.json()
    assert receipt["ok"] is True
    assert receipt["sha256"] == digest
    assert receipt["safe_to_delete_source"] is False
    assert source.read_bytes() == payload
    assert len(list(gallery.glob("*.png"))) == 1
