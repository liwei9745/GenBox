"""Exact library-source lookup within one page, using synthetic media only."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from video_workbench.assets import WORKSPACE_OWNER
from video_workbench.media import MediaIngestError
from test_video_workbench_api import FIXTURES, HEADERS, PREFIX, runtime


def seed_library(service, count=60):
    payload = (FIXTURES / "still.png").read_bytes()
    source = service.gallery / "synthetic_000.png"
    source.write_bytes(payload)
    response = service.register_library(
        WORKSPACE_OWNER, "library_0", library_kind="image", library_item_id=source.stem,
    )
    asset_id = response["files"][0]["asset_id"]
    base = service.media.assets_root / asset_id
    manifest = json.loads((base / "asset.json").read_text())
    journal = service._read_job(service._job_path("library_0"), WORKSPACE_OWNER)
    # Extra records isolate lookup costs from import/decoder throughput.
    for i in range(1, count):
        source = service.gallery / f"synthetic_{i:03d}.png"
        source.write_bytes(payload)
        identity = f"ast_synthetic_{i:03d}"
        directory = service.media.assets_root / identity
        directory.mkdir()
        (directory / "original").write_bytes(payload)
        (directory / "asset.json").write_text(json.dumps({**manifest, "asset_id": identity}))
        data = deepcopy(journal)
        path = service._job_path(f"library_{i}")
        data["intent"]["source"]["id"] = source.stem
        data["view"].update(job_id=path.stem, asset_ids=[identity])
        data["results"] = [{"index": 0, "state": "ready", "asset_id": identity}]
        service._write_job(path, data)
    return asset_id


def test_library_directory_enumerated_once_per_page_and_refreshed_next_request(runtime, monkeypatch):
    client, service = runtime
    seed_library(service)
    scans = []
    iterdir = Path.iterdir

    def counted(path):
        if path == service.gallery:
            scans.append(path)
        return iterdir(path)

    monkeypatch.setattr(Path, "iterdir", counted)
    first = service.list_assets(WORKSPACE_OWNER, limit=20, query="ast_synthetic_")
    assert len(first["items"]) == 20
    assert len(scans) == 1
    missing = service.gallery / "synthetic_001.png"
    missing.unlink()
    second = service.list_assets(WORKSPACE_OWNER, limit=20, query="ast_synthetic_")
    assert len(scans) == 2
    assert second["items"][0]["asset_id"] == "ast_synthetic_002"
    (service.gallery / "synthetic_002.png").write_bytes(b"changed synthetic bytes")
    third = client.get(PREFIX + "/assets?query=ast_synthetic_&limit=20", headers=HEADERS)
    assert third.status_code == 200
    assert third.json()["items"][0]["asset_id"] == "ast_synthetic_003"
    assert len(scans) == 3


def test_index_preserves_case_suffix_exact_identity_and_rejects_missing(runtime):
    _, service = runtime
    (service.gallery / "Exact.png").write_bytes(b"synthetic")
    (service.gallery / "Exact_extra.png").write_bytes(b"synthetic")
    (service.gallery / "upper.PNG").write_bytes(b"synthetic")
    index = {}
    assert service._library_path("image", "Exact", index=index).name == "Exact.png"
    for identity in ("exact", "Exac", "upper", "Exact_extra_more"):
        with pytest.raises(MediaIngestError) as error:
            service._library_path("image", identity, index=index)
        assert error.value.code == "not_found"
    for identity in ("../Exact", "https://invalid.test/image", "Exact.png/other"):
        with pytest.raises(MediaIngestError) as error:
            service._library_path("image", identity, index=index)
        assert error.value.code == "invalid_request"


def test_index_is_not_authority_after_source_disappears_or_becomes_directory(runtime):
    _, service = runtime
    source = service.gallery / "synthetic.png"
    source.write_bytes(b"synthetic")
    index = {}
    assert service._library_path("image", "synthetic", index=index) == source
    source.unlink()
    with pytest.raises(MediaIngestError) as error:
        service._library_path("image", "synthetic", index=index)
    assert error.value.code == "not_found"
    source.mkdir()
    with pytest.raises(MediaIngestError) as error:
        service._library_path("image", "synthetic", index=index)
    assert error.value.code == "not_found"


def test_index_rechecks_path_guards_after_enumeration(runtime, monkeypatch):
    _, service = runtime
    from types import SimpleNamespace
    source = service.gallery / "synthetic.png"
    source.write_bytes(b"synthetic")
    index = {}
    service._library_path("image", "synthetic", index=index)
    lstat = Path.lstat

    def replaced(path, *args, **kwargs):
        if path == source:
            return SimpleNamespace(st_mode=0o100644, st_file_attributes=0x400)
        return lstat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", replaced)
    with pytest.raises(MediaIngestError) as error:
        service._library_path("image", "synthetic", index=index)
    assert error.value.code == "internal"
