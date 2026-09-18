"""Task lifecycle and recovery use isolated stores and synthetic media only."""

import json
import asyncio
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from video_workbench.assets import AssetService, WORKSPACE_OWNER
from video_workbench.media import MediaIngestError
from video_workbench.media.worker import check_cancelled
from test_video_workbench_api import HEADERS, PREFIX, runtime, upload


FIXTURES = Path(__file__).parent / "fixtures" / "video_workbench"


def wait_job(service, job_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = service.job(WORKSPACE_OWNER, job_id)
        with service.runtime.lock:
            active = job_id in service._active
        if not active:
            return result
        time.sleep(0.02)
    pytest.fail("job did not stop within five seconds")


def test_async_cancel_duplicate_and_csrf(runtime, monkeypatch):
    client, service = runtime
    entered = threading.Event()

    def probe(staged):
        entered.set()
        while True:
            check_cancelled()
            time.sleep(0.01)

    monkeypatch.setattr(service.media, "probe", probe)
    response = upload(client, headers={**HEADERS, "Prefer": "respond-async"})
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    assert response.json()["job"]["state"] == "queued"
    assert entered.wait(5)
    repeated = upload(client, headers={**HEADERS, "Prefer": "respond-async"})
    assert repeated.json()["job"]["job_id"] == job_id
    assert repeated.json()["job"]["state"] == "preparing"
    assert len(service._active) == 1
    url = PREFIX + "/jobs/" + job_id + "/cancel"
    assert client.post(url).status_code == 401
    assert client.post(url, headers={"X-Admin-Key": HEADERS["X-Admin-Key"]}).status_code == 401
    assert client.post(url, headers=HEADERS, json={"path": "untrusted"}).status_code == 422
    result = client.post(url, headers=HEADERS)
    assert result.json()["job"]["state"] == "cancel_requested"
    terminal = wait_job(service, job_id)
    assert terminal["job"]["state"] == "cancelled"
    assert terminal["files"][0]["error"]["code"] == "job_cancelled"
    assert not service.media._issued
    assert not list(service.media.staging_root.rglob(".upload-*"))
    assert client.post(url, headers=HEADERS).json() == terminal
    assert upload(client).json() == terminal


def test_async_success_has_original_and_no_private_journal_fields(runtime):
    client, service = runtime
    response = upload(client, headers={**HEADERS, "Prefer": "respond-async"})
    result = wait_job(service, response.json()["job"]["job_id"])
    assert result["job"]["state"] == "succeeded"
    assert set(result) == {"job", "files"}
    assert "staging" not in json.dumps(result) and "leases" not in json.dumps(result)
    record = service.asset(WORKSPACE_OWNER, result["files"][0]["asset_id"])
    assert record.storage_path.read_bytes() == (FIXTURES / "cfr-h264.mp4").read_bytes()
    assert service.runtime._leases == {}


def test_store_lock_prevents_second_runtime_and_releases_on_close(tmp_path):
    first = AssetService(tmp_path / "store", tmp_path / "gallery", tmp_path / "videos")
    second = AssetService(first.media.root, first.gallery, first.videos)
    try:
        first._ready(WORKSPACE_OWNER)
        with pytest.raises(MediaIngestError) as error:
            second._ready(WORKSPACE_OWNER)
        assert error.value.code == "conflict"
        first.close()
        second._ready(WORKSPACE_OWNER)
    finally:
        first.close()
        second.close()


def test_recovery_preserves_original_and_unknown_files(tmp_path):
    first = AssetService(tmp_path / "store", tmp_path / "gallery", tmp_path / "videos")
    payload = (FIXTURES / "still.png").read_bytes()
    result = first.import_files(WORKSPACE_OWNER, "synthetic", [("still.png", payload)])
    job_id = result["job"]["job_id"]
    original = first.asset(WORKSPACE_OWNER, result["files"][0]["asset_id"]).storage_path
    path = first.jobs / (job_id + ".json")
    data = first._read_job(path, WORKSPACE_OWNER)
    staged = first.media.stage_stream("stage_" + "a" * 32, "still.png", payload)
    unknown = staged.path.parent / "unknown-retain.tmp"
    unknown.write_bytes(b"unclaimed")
    data["view"]["state"] = "preparing"
    data["staging"] = [{"directory": staged.job_id, "file": staged.path.name}]
    data["leases"] = [{"digest": staged.content_sha256}]
    first._write_job(path, data)
    first.close()
    # Simulate loss of volatile ownership after process exit.
    first.media._issued.pop(staged.path)
    first.media._release_reservation(staged.job_id)
    restored = AssetService(first.media.root, first.gallery, first.videos)
    try:
        recovered = restored.job(WORKSPACE_OWNER, job_id)
        assert recovered["job"]["state"] == "interrupted"
        assert json.loads(path.read_text())["view"]["state"] == "interrupted"
        assert not staged.path.exists()
        assert unknown.read_bytes() == b"unclaimed"
        assert original.read_bytes() == payload
        assert restored.import_files(
            WORKSPACE_OWNER, "synthetic", [("still.png", payload)],
        )["job"]["state"] == "interrupted"
    finally:
        restored.close()


def test_recovery_rejects_ledger_escape_without_deletion(tmp_path):
    service = AssetService(tmp_path / "store", tmp_path / "gallery", tmp_path / "videos")
    service._ready(WORKSPACE_OWNER)
    outside = tmp_path / "unrelated"
    outside.write_bytes(b"retain")
    path, data, _ = service._start_job(WORKSPACE_OWNER, "synthetic", {"operation": "upload"})
    data["staging"] = [{"directory": "../", "file": "unrelated"}]
    service._write_job(path, data)
    service.close()
    restored = AssetService(service.media.root, service.gallery, service.videos)
    try:
        with pytest.raises(MediaIngestError):
            restored._ready(WORKSPACE_OWNER)
        assert outside.read_bytes() == b"retain"
        assert not restored._recovered
    finally:
        restored.close()


def test_active_lease_blocks_store_close_and_is_released(runtime):
    client, service = runtime
    result = upload(client).json()
    record = service.asset(WORKSPACE_OWNER, result["files"][0]["asset_id"])
    with service.runtime.lease(record.storage_path):
        assert service.runtime.leased(record.storage_path)
        with pytest.raises(MediaIngestError) as error:
            service.close()
        assert error.value.code == "conflict"
    assert not service.runtime.leased(record.storage_path)
    for range_header in ("bytes=0-10", "bytes=999999999-"):
        client.get(
            PREFIX + "/assets/" + record.asset_id + "/content",
            headers={**HEADERS, "Range": range_header},
        )
        assert service.runtime._leases == {}


def test_proxy_routes_jobs_cache_ranges_and_ownership(runtime):
    client, service = runtime
    result = upload(client).json()
    asset_id = result["files"][0]["asset_id"]
    url = PREFIX + "/assets/" + asset_id + "/proxy"
    headers = {**HEADERS, "X-Request-ID": "synthetic_proxy"}
    assert client.get(url, headers=HEADERS).status_code == 404
    assert client.post(url).status_code == 401
    assert client.post(url, headers={"X-Admin-Key": HEADERS["X-Admin-Key"]}).status_code == 401
    assert client.post(url, headers=headers, json={"command": "untrusted"}).status_code == 422
    started = client.post(url, headers=headers)
    assert started.status_code == 202
    job_id = started.json()["job"]["job_id"]
    completed = wait_job(service, job_id)
    assert completed["job"]["state"] == "succeeded", completed
    assert completed["job"]["operation"] == "proxy"
    assert client.post(url, headers=headers).json() == completed
    derived = service.proxy(WORKSPACE_OWNER, asset_id)
    assert client.get(url).status_code == 401
    response = client.get(url, headers={**HEADERS, "Range": "bytes=0-15"})
    assert response.status_code == 206 and response.content == derived.path.read_bytes()[:16]
    assert service.runtime._leases == {}
    assert not list(service.media.staging_root.rglob(".proxy-*"))
    assert client.get(PREFIX + "/assets/" + asset_id + "/content", headers=HEADERS).content == (
        FIXTURES / "cfr-h264.mp4"
    ).read_bytes()
    with pytest.raises(MediaIngestError) as error:
        service.proxy("foreign", asset_id)
    assert error.value.code == "forbidden"
    derived.path.write_bytes(b"tampered synthetic cache")
    assert client.get(url, headers=HEADERS).status_code == 422


def test_proxy_cancel_releases_lease_reservation_and_only_owned_staging(runtime, monkeypatch):
    client, service = runtime
    asset_id = upload(client).json()["files"][0]["asset_id"]
    entered = threading.Event()
    unknown = []

    def render(asset, pending, manifest):
        pending.write_bytes(b"partial synthetic")
        unclaimed = pending.parent / "unclaimed.txt"
        unclaimed.write_bytes(b"retain")
        unknown.append(unclaimed)
        entered.set()
        while True:
            check_cancelled()
            time.sleep(0.01)

    monkeypatch.setattr(service.proxies, "render", render)
    url = PREFIX + "/assets/" + asset_id + "/proxy"
    result = client.post(url, headers={**HEADERS, "X-Request-ID": "synthetic_proxy"})
    job_id = result.json()["job"]["job_id"]
    assert entered.wait(5)
    original = service.asset(WORKSPACE_OWNER, asset_id).storage_path
    assert service.runtime.leased(original)
    assert client.post(url, headers={**HEADERS, "X-Request-ID": "another_proxy"}).status_code == 409
    client.post(PREFIX + "/jobs/" + job_id + "/cancel", headers=HEADERS)
    completed = wait_job(service, job_id)
    assert completed["job"]["state"] == "cancelled"
    assert not service.runtime.leased(original)
    assert unknown[0].read_bytes() == b"retain"
    assert not list(service.media.staging_root.rglob(".proxy-*.mp4"))
    with service.proxies.reservation():
        pass
    assert original.read_bytes() == (FIXTURES / "cfr-h264.mp4").read_bytes()


def test_library_proxy_does_not_bypass_original_identity_recheck(runtime):
    client, service = runtime
    source = service.videos / "synthetic.mp4"
    source.write_bytes((FIXTURES / "cfr-h264.mp4").read_bytes())
    imported = service.register_library(
        WORKSPACE_OWNER, "synthetic_library", library_kind="video", library_item_id="synthetic",
    )
    asset_id = imported["files"][0]["asset_id"]
    started = service.prepare_proxy(WORKSPACE_OWNER, "synthetic_proxy", asset_id)
    assert wait_job(service, started["job"]["job_id"])["job"]["state"] == "succeeded"
    source.write_bytes(b"changed synthetic source")
    response = client.get(PREFIX + "/assets/" + asset_id + "/proxy", headers=HEADERS)
    assert response.status_code == 409


def test_actual_process_crash_recovers_durable_proxy_job_without_replay(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path / "store"
    marker = tmp_path / "started.json"
    code = f"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, {str(repo)!r})
from video_workbench.assets import AssetService, WORKSPACE_OWNER
s = AssetService(Path({str(root)!r}), Path({str(tmp_path / 'gallery')!r}), Path({str(tmp_path / 'videos')!r}))
payload = Path({str((FIXTURES / 'cfr-h264.mp4').resolve())!r}).read_bytes()
imported = s.import_files(WORKSPACE_OWNER, 'import', [('test.mp4', payload)])
asset_id = imported['files'][0]['asset_id']
def synthetic_render(asset, pending, manifest):
    pending.write_bytes(b'partial synthetic proxy')
    (pending.parent / 'unknown.tmp').write_bytes(b'retain')
    Path({str(marker)!r}).write_text(json.dumps({{'asset_id': asset_id, 'staging': pending.parent.name}}))
    time.sleep(60)
s.proxies.render = synthetic_render
s.prepare_proxy(WORKSPACE_OWNER, 'proxy', asset_id)
time.sleep(60)
"""
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", code], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs,
    )
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        data = json.loads(marker.read_text())
        rival = AssetService(root, tmp_path / "gallery", tmp_path / "videos")
        with pytest.raises(MediaIngestError) as error:
            rival._ready(WORKSPACE_OWNER)
        assert error.value.code == "conflict"
        rival.close()
        process.kill()
        process.wait(timeout=5)
        restored = AssetService(root, tmp_path / "gallery", tmp_path / "videos")
        try:
            job_id = "job_" + hashlib.sha256(b"proxy").hexdigest()
            state = restored.job(WORKSPACE_OWNER, job_id)
            assert state["job"]["state"] == "interrupted"
            assert not restored._active
            assert not list(root.glob("staging/*/.proxy-*.mp4"))
            assert (root / "staging" / data["staging"] / "unknown.tmp").read_bytes() == b"retain"
            assert restored.asset(WORKSPACE_OWNER, data["asset_id"]).storage_path.read_bytes() == (
                FIXTURES / "cfr-h264.mp4"
            ).read_bytes()
            assert restored.prepare_proxy(WORKSPACE_OWNER, "proxy", data["asset_id"]) == state
        finally:
            restored.close()
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def test_disconnect_before_first_chunk_releases_media_lease(runtime):
    from starlette.requests import ClientDisconnect, Request
    from video_workbench.api import _leased_response

    client, service = runtime
    result = upload(client).json()
    asset = service.asset(WORKSPACE_OWNER, result["files"][0]["asset_id"])
    scope = {"type": "http", "headers": [], "asgi": {"spec_version": "2.4"}}
    response = _leased_response(service, asset.storage_path, "video/mp4", Request(scope), "test.mp4")
    assert service.runtime.leased(asset.storage_path)

    async def disconnected():
        async def send(message):
            raise OSError("synthetic disconnect")

        async def receive():
            return {"type": "http.disconnect"}

        with pytest.raises(ClientDisconnect):
            await response(scope, receive, send)

    asyncio.run(disconnected())
    assert not service.runtime.leased(asset.storage_path)


def test_shutdown_keeps_store_locked_during_prejournal_staging(tmp_path, monkeypatch):
    service = AssetService(tmp_path / "store", tmp_path / "gallery", tmp_path / "videos")
    rival = AssetService(service.media.root, service.gallery, service.videos)
    entered, release, closing = threading.Event(), threading.Event(), threading.Event()
    original = service.media.stage_batch
    errors = []

    def staging(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(service.media, "stage_batch", staging)

    def importing():
        try:
            service.import_files(
                WORKSPACE_OWNER, "synthetic", [("still.png", (FIXTURES / "still.png").read_bytes())],
            )
        except Exception as error:
            errors.append(error)

    def shutdown():
        closing.set()
        try:
            service.close()
        except Exception as error:
            errors.append(error)

    importer, closer = threading.Thread(target=importing), threading.Thread(target=shutdown)
    importer.start()
    try:
        assert entered.wait(5)
        closer.start()
        assert closing.wait(5)
        with pytest.raises(MediaIngestError) as error:
            rival._ready(WORKSPACE_OWNER)
        assert error.value.code == "conflict"
        release.set()
        importer.join(timeout=5)
        closer.join(timeout=5)
        assert not importer.is_alive() and not closer.is_alive()
        assert not errors
        rival._ready(WORKSPACE_OWNER)
    finally:
        release.set()
        importer.join(timeout=6)
        if closer.ident is not None:
            closer.join(timeout=6)
        service.close()
        rival.close()
