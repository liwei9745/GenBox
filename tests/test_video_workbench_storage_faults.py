"""Disk/journal fault injection only touches synthetic temporary stores."""

import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from video_workbench import assets, api
from video_workbench.assets import AssetService, WORKSPACE_OWNER
from video_workbench.media import MediaIngestError
from video_workbench.media import ingest, proxy
from test_video_workbench_api import HEADERS, PREFIX, FIXTURES, asset_id, runtime, upload
from test_video_workbench_jobs import wait_job


def test_http_disk_admission_does_not_stage_or_start_job(runtime, monkeypatch):
    client, service = runtime
    monkeypatch.setattr(api.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    response = upload(client)
    assert response.status_code == 507
    assert response.json()["error"]["code"] == "disk_space"
    assert not service.jobs.exists()
    assert not service.media.staging_root.exists()
    assert not service._active and not service.media._issued


def test_initial_journal_replace_failure_is_redacted_and_cleans_only_owned_stage(runtime, monkeypatch):
    client, service = runtime
    replace = assets.os.replace

    def fail(source, destination):
        if Path(destination).name.startswith("job_"):
            raise OSError("synthetic private disk diagnostic")
        return replace(source, destination)

    monkeypatch.setattr(assets.os, "replace", fail)
    response = upload(client, fixture="still.png")
    assert response.status_code == 507
    assert "private" not in response.text
    assert response.json()["error"]["code"] == "disk_space"
    assert not list(service.jobs.glob("*.json"))
    assert not list(service.media.staging_root.rglob(".upload-*"))
    assert not service.media._issued
    assert not service._active


def test_asset_atomic_publication_failure_does_not_publish_partial_asset(runtime, monkeypatch):
    client, service = runtime
    rename = ingest.os.rename

    def fail(source, destination):
        if Path(source).name.startswith(".publish-"):
            raise OSError("synthetic disk full")
        return rename(source, destination)

    monkeypatch.setattr(ingest.os, "rename", fail)
    response = upload(client, fixture="still.png")
    assert response.status_code == 200
    assert response.json()["job"]["state"] == "failed"
    assert response.json()["files"][0]["error"]["code"] == "disk_space"
    assert not list(service.media.assets_root.glob("*/original"))
    assert not list(service.media.staging_root.rglob(".upload-*"))
    assert not service.media._issued


@pytest.mark.parametrize("operation", ["import", "proxy"])
@pytest.mark.parametrize("restart", [False, True])
def test_async_persistent_journal_failure_retains_declared_files_and_recovers_without_replay(
    runtime, monkeypatch, operation, restart,
):
    client, service = runtime
    if operation == "proxy":
        identity = asset_id(upload(client))
    entered, release = threading.Event(), threading.Event()
    original_probe = service.media.probe
    artifacts = []

    def blocked_probe(staged):
        entered.set()
        assert release.wait(10)
        return original_probe(staged)

    def blocked_render(asset, pending, manifest):
        pending.write_bytes(b"synthetic partial proxy")
        unknown = pending.parent / "retain-unknown.tmp"
        unknown.write_bytes(b"retain")
        artifacts.append(unknown)
        entered.set()
        assert release.wait(10)
        raise OSError("synthetic disk error with private text")

    if operation == "import":
        monkeypatch.setattr(service.media, "probe", blocked_probe)
        response = upload(client, headers={**HEADERS, "Prefer": "respond-async"})
        started = response.json()
    else:
        monkeypatch.setattr(service.proxies, "render", blocked_render)
        started = service.prepare_proxy(WORKSPACE_OWNER, "proxy_fault", identity)
    try:
        assert entered.wait(10)
        path = service.jobs / (started["job"]["job_id"] + ".json")
        durable = service._read_job(path, WORKSPACE_OWNER)
        files = [service.media.staging_root / item["directory"] / item["file"] for item in durable["staging"]]
        write_job = service._write_job

        def disk_full(*args):
            raise ingest._fail("disk_space", "publish", retryable=True)

        monkeypatch.setattr(service, "_write_job", disk_full)
        release.set()
        with service.runtime.lock:
            threads = list(service._threads)
        for thread in threads:
            thread.join(timeout=10)
            assert not thread.is_alive()
        assert not service._active
        assert not service.runtime._leases
        assert service._read_job(path, WORKSPACE_OWNER)["view"]["state"] not in {"succeeded", "failed"}
        assert any(item.exists() for item in files)
        monkeypatch.setattr(service, "_write_job", write_job)
        if restart:
            service.close()
            restored = AssetService(service.media.root, service.gallery, service.videos)
        else:
            restored = service
        try:
            result = restored.job(WORKSPACE_OWNER, started["job"]["job_id"])
            assert result["job"]["state"] == "interrupted"
            assert not restored._active
            assert not any(item.exists() for item in files)
            assert all(item.read_bytes() == b"retain" for item in artifacts)
            originals = list(restored.media.assets_root.glob("*/original"))
            assert originals
            assert all(item.read_bytes() == (FIXTURES / "cfr-h264.mp4").read_bytes() for item in originals)
            assert restored.job(WORKSPACE_OWNER, started["job"]["job_id"]) == result
            assert not restored.media._issued
            with restored.proxies.reservation():
                pass
        finally:
            if restart:
                restored.close()
    finally:
        release.set()


def test_terminal_journal_one_shot_failure_preserves_published_original(runtime, monkeypatch):
    client, service = runtime
    write = service._write_job
    failed = []

    def fail_once(path, data):
        if data["view"]["state"] == "succeeded" and not failed:
            failed.append(True)
            raise ingest._fail("disk_space", "publish", retryable=True)
        return write(path, data)

    monkeypatch.setattr(service, "_write_job", fail_once)
    result = upload(client, fixture="still.png").json()
    assert failed and result["job"]["state"] == "failed"
    assert result["files"][0]["error"]["code"] == "disk_space"
    identity = result["files"][0]["asset_id"]
    assert service.asset(WORKSPACE_OWNER, identity).storage_path.read_bytes() == (FIXTURES / "still.png").read_bytes()
    assert service.job(WORKSPACE_OWNER, result["job"]["job_id"]) == result
    assert upload(client, fixture="still.png").json() == result
    assert not service.media._issued


def test_proxy_disk_admission_preserves_original_and_creates_no_job(runtime, monkeypatch):
    client, service = runtime
    identity = asset_id(upload(client))
    monkeypatch.setattr(proxy.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    with pytest.raises(MediaIngestError) as error:
        service.prepare_proxy(WORKSPACE_OWNER, "proxy_fault", identity)
    assert error.value.code == "disk_space"
    assert not service._job_path("proxy_fault").exists()
    assert not service._active
    assert service.asset(WORKSPACE_OWNER, identity).storage_path.read_bytes() == (FIXTURES / "cfr-h264.mp4").read_bytes()


def test_proxy_manifest_publish_failure_retains_unservable_partial_cache(runtime, monkeypatch):
    client, service = runtime
    identity = asset_id(upload(client))
    rename = proxy.os.rename

    def fail(source, destination):
        if Path(destination).name == "proxy.json":
            raise OSError("synthetic disk full")
        return rename(source, destination)

    monkeypatch.setattr(proxy.os, "rename", fail)
    started = service.prepare_proxy(WORKSPACE_OWNER, "proxy_fault", identity)
    result = wait_job(service, started["job"]["job_id"])
    assert result["job"]["state"] == "failed"
    assert "synthetic disk full" not in json.dumps(result)
    derived = service.media.assets_root / identity / "derived" / "1"
    assert (derived / "proxy.mp4").exists()
    assert not (derived / "proxy.json").exists()
    assert not list(service.media.staging_root.rglob(".proxy-*"))
    url = PREFIX + "/assets/" + identity
    assert client.get(url + "/proxy", headers=HEADERS).status_code == 422
    assert client.get(url + "/content", headers=HEADERS).content == (FIXTURES / "cfr-h264.mp4").read_bytes()
    assert service.prepare_proxy(WORKSPACE_OWNER, "proxy_fault", identity) == result
    assert not service.runtime._leases
