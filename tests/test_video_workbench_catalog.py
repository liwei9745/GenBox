"""Synthetic catalogue operation counts, not real-library performance claims."""

from copy import deepcopy
import json
import os

from video_workbench.assets import WORKSPACE_OWNER
from test_video_workbench_api import HEADERS, PREFIX, asset_id, runtime, upload


def test_thousand_asset_catalog_scans_journals_once_and_reuses_verified_page(runtime, monkeypatch):
    client, service = runtime
    initial = upload(client, fixture="still.png")
    identity = asset_id(initial)
    template = service.media.assets_root / identity
    manifest = json.loads((template / "asset.json").read_text())
    payload = (template / "original").read_bytes()
    journal = service._read_job(service._job_path("req_test"), WORKSPACE_OWNER)
    # Manufacture only isolated synthetic records to measure catalogue reads
    # independently of native decoder throughput or import deduplication.
    for index in range(1000):
        fake_id = f"asset_synthetic_{index:04d}"
        directory = service.media.assets_root / fake_id
        directory.mkdir()
        (directory / "original").write_bytes(payload)
        (directory / "asset.json").write_text(json.dumps({**manifest, "asset_id": fake_id}))
        data = deepcopy(journal)
        path = service._job_path(f"catalog_{index}")
        data["view"].update(job_id=path.stem, asset_ids=[fake_id])
        data["results"] = [{"index": 0, "state": "ready", "asset_id": fake_id}]
        service._write_job(path, data)

    reads = {"journal": 0, "digest": 0}
    read_job, read_record = service._read_job, service.media._read_record

    def counted_job(*args):
        reads["journal"] += 1
        return read_job(*args)

    def counted_record(directory, *, verify_content=True):
        reads["digest"] += int(verify_content)
        return read_record(directory, verify_content=verify_content)

    monkeypatch.setattr(service, "_read_job", counted_job)
    monkeypatch.setattr(service.media, "_read_record", counted_record)
    args = {"query": "asset_synthetic_", "limit": 20, "kind": "image"}
    first = service.list_assets(WORKSPACE_OWNER, **args)
    assert len(first["items"]) == 20
    assert first["next_cursor"] == "asset_synthetic_0019"
    assert reads == {"journal": 1001, "digest": 21}
    second = service.list_assets(WORKSPACE_OWNER, **args)
    assert first == second
    assert reads == {"journal": 2002, "digest": 21}
    next_page = service.list_assets(WORKSPACE_OWNER, cursor=first["next_cursor"], **args)
    assert next_page["items"][0]["asset_id"] == "asset_synthetic_0020"
    assert len({item["asset_id"] for item in first["items"] + next_page["items"]}) == 40
    before = reads["digest"]
    assert service.list_assets(WORKSPACE_OWNER, kind="audio")["items"] == []
    assert reads["digest"] == before
    last = service.list_assets(WORKSPACE_OWNER, cursor="asset_synthetic_0998", **args)
    assert len(last["items"]) == 1 and last["next_cursor"] is None
    assert len(service._listing_cache) <= 256


def test_warm_listing_does_not_cache_ownership_or_deliver_changed_content(runtime):
    client, service = runtime
    identity = asset_id(upload(client, fixture="still.png"))
    url = PREFIX + "/assets"
    assert len(client.get(url, headers=HEADERS).json()["items"]) == 1
    original = service.media.assets_root / identity / "original"
    stat = original.stat()
    payload = original.read_bytes()
    original.write_bytes(bytes([payload[0] ^ 1]) + payload[1:])
    os.utime(original, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert client.get(url, headers=HEADERS).json()["items"] == []
    assert client.get(url + "/" + identity + "/content", headers=HEADERS).status_code == 404
    original.write_bytes(payload)
    assert len(client.get(url, headers=HEADERS).json()["items"]) == 1
    path = service._job_path("req_test")
    data = json.loads(path.read_text())
    data["owner"] = "foreign"
    path.write_text(json.dumps(data))
    assert client.get(url, headers=HEADERS).status_code == 403
    assert client.get(url + "/" + identity, headers=HEADERS).status_code == 403


def test_cached_library_listing_rechecks_source_identity_and_manifest(runtime):
    client, service = runtime
    source = service.gallery / "synthetic.png"
    from test_video_workbench_api import FIXTURES
    payload = (FIXTURES / "still.png").read_bytes()
    source.write_bytes(payload)
    result = service.register_library(
        WORKSPACE_OWNER, "library", library_kind="image", library_item_id="synthetic",
    )
    identity = result["files"][0]["asset_id"]
    assert len(service.list_assets(WORKSPACE_OWNER)["items"]) == 1
    source.write_bytes(b"changed")
    assert service.list_assets(WORKSPACE_OWNER)["items"] == []
    source.write_bytes(payload)
    assert len(service.list_assets(WORKSPACE_OWNER)["items"]) == 1
    manifest = service.media.assets_root / identity / "asset.json"
    data = json.loads(manifest.read_text())
    valid = json.dumps(data)
    data["metadata"]["width"] = -1
    manifest.write_text(json.dumps(data))
    assert service.list_assets(WORKSPACE_OWNER)["items"] == []
    manifest.write_text(valid)
    assert len(service.list_assets(WORKSPACE_OWNER)["items"]) == 1
    source.unlink()
    assert service.list_assets(WORKSPACE_OWNER)["items"] == []


def test_listing_cache_expiry_and_limit_never_affect_strict_asset_reads(runtime, monkeypatch):
    client, service = runtime
    identity = asset_id(upload(client, fixture="still.png"))
    service.list_assets(WORKSPACE_OWNER)
    key = ("asset", identity)
    cached = service._listing_cache[key]
    service._listing_cache[key] = (cached[0], 0, cached[2])
    count = []
    original = service.media._read_record

    def verify(directory, *, verify_content=True):
        if verify_content:
            count.append(directory)
        return original(directory, verify_content=verify_content)

    monkeypatch.setattr(service.media, "_read_record", verify)
    service.list_assets(WORKSPACE_OWNER)
    service.asset(WORKSPACE_OWNER, identity)
    assert len(count) == 2
    for index in range(300):
        service._for_listing(("test", index), (cached[2].storage_path,), lambda: True)
    assert len(service._listing_cache) == 256


def test_unavailable_change_token_disables_browse_cache(runtime, monkeypatch):
    from video_workbench import assets

    client, service = runtime
    identity = asset_id(upload(client, fixture="still.png"))
    service.list_assets(WORKSPACE_OWNER)
    monkeypatch.setattr(assets, "change_token", lambda *args: None)
    original = service.media.assets_root / identity / "original"
    data = original.read_bytes()
    original.write_bytes(bytes([data[0] ^ 1]) + data[1:])
    assert service.list_assets(WORKSPACE_OWNER)["items"] == []
