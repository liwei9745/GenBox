"""Project route/asset integration using only synthetic temporary stores."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import main
import pytest

from test_video_workbench_api import runtime, PREFIX, HEADERS, upload, asset_id, FIXTURES
from video_workbench.assets import AssetService


PROJECTS = PREFIX + "/projects"
PROFILE = {
    "profile_id": "landscape_1080p_30", "canvas": {"width": 1920, "height": 1080},
    "fps": {"num": 30, "den": 1}, "fit_mode": "contain",
}


def create(client, title="Synthetic project"):
    response = client.post(PROJECTS, headers=HEADERS, json={"title": title, "output_profile": PROFILE})
    assert response.status_code == 201, response.text
    return response.json()


def save(client, document, expected=None):
    return client.put(
        PROJECTS + "/" + document["project_id"], headers=HEADERS,
        json={"expected_revision": document["revision"] if expected is None else expected, "document": document},
    )


def test_create_read_save_and_reopen_with_real_asset(runtime, monkeypatch):
    client, service = runtime
    document = create(client)
    identity = asset_id(upload(client, fixture="still.png"))
    asset = client.get(PREFIX + "/assets/" + identity, headers=HEADERS).json()
    document["asset_refs"] = [{"asset_id": identity, "kind": "image", "digest": asset["content_sha256"]}]
    document["title"] = "Renamed synthetic project"
    response = save(client, document)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["revision"] == 2
    assert saved["created_at"] == document["created_at"]
    assert saved["tracks"] == document["tracks"]
    assert saved["asset_refs"] == document["asset_refs"]
    assert set(saved) == {
        "schema_version", "project_id", "revision", "title", "output_profile",
        "asset_refs", "tracks", "candidate_refs", "created_at", "updated_at",
    }
    assert response.headers["cache-control"] == "private, no-store"
    stale = save(client, document)
    assert stale.status_code == 409
    path = PROJECTS + "/" + saved["project_id"]
    assert client.get(path, headers=HEADERS).json() == saved
    service.close()
    restored = AssetService(service.media.root, service.gallery, service.videos)
    monkeypatch.setattr(main, "_workbench_asset_service", restored)
    assert client.get(path, headers=HEADERS).json() == saved
    assert client.get(PREFIX + "/assets/" + identity, headers=HEADERS).status_code == 200
    assert str(service.media.root) not in response.text
    restored.close()


@pytest.mark.parametrize("headers", [
    {}, {"X-Admin-Key": "wrong"}, {"X-Admin-Key": HEADERS["X-Admin-Key"]},
    {**HEADERS, "Origin": "https://untrusted.invalid"},
    {**HEADERS, "Origin": "null"},
    {**HEADERS, "Sec-Fetch-Site": "cross-site"},
])
def test_project_mutation_auth_precedes_storage(runtime, headers):
    client, service = runtime
    assert client.post(PROJECTS, headers=headers, json={"title": "Synthetic", "output_profile": PROFILE}).status_code == 401
    assert client.put(PROJECTS + "/prj_" + "0" * 32, headers=headers, json={}).status_code == 401
    assert client.get(PROJECTS + "/prj_" + "0" * 32).status_code == 401
    assert not service.media.root.exists()


@pytest.mark.parametrize("body", [
    b'{"title":"A","title":"B","output_profile":{}}',
    b'{"title":"A","output_profile":NaN}',
    b'{"title":"A","output_profile":Infinity}',
    b"[" * 2000, b" " * 4097, b"\xff",
    b'{"title":"A","output_profile":{},"api_key":"synthetic"}',
])
def test_create_rejects_malformed_duplicate_nonfinite_or_unknown_fields(runtime, body):
    client, _ = runtime
    response = client.post(PROJECTS, headers=HEADERS, content=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_project_routes_reject_queries_and_oversized_save(runtime):
    client, service = runtime
    document = create(client)
    path = PROJECTS + "/" + document["project_id"]
    for response in (
        client.post(PROJECTS + "?extra=1", headers=HEADERS, json={"title": "Synthetic", "output_profile": PROFILE}),
        client.get(path + "?extra=1", headers=HEADERS),
        client.put(path + "?extra=1", headers=HEADERS, json={"expected_revision": 1, "document": document}),
        client.put(path, headers=HEADERS, content=b" " * (4 * 1024 * 1024 + 1025)),
    ):
        assert response.status_code == 422
    assert client.get(path, headers=HEADERS).json() == document
    assert len(list((service.media.root / "projects").glob("prj_*.json"))) == 1


@pytest.mark.parametrize("change", [
    {"schema_version": 2}, {"schema_version": True}, {"revision": True},
    {"project_id": "prj_" + "0" * 32}, {"created_at": "2000-01-01T00:00:00Z"},
    {"updated_at": "2000-01-01T00:00:00Z"}, {"path": "/synthetic/path"},
    {"title": "\x00"}, {"title": "x" * 201},
    {"asset_refs": [{"asset_id": "../escape", "kind": "image", "digest": "sha256:" + "0" * 64}]},
])
def test_invalid_document_never_changes_last_valid_snapshot(runtime, change):
    client, service = runtime
    document = create(client)
    file = service.media.root / "projects" / (document["project_id"] + ".json")
    before = file.read_bytes()
    response = save(client, {**document, **change})
    assert response.status_code in {404, 409, 422}, response.text
    assert file.read_bytes() == before
    assert client.get(PROJECTS + "/" + document["project_id"], headers=HEADERS).json() == document


def test_unimplemented_timeline_and_candidates_are_explicitly_rejected(runtime):
    client, _ = runtime
    document = create(client)
    clip = deepcopy(document)
    clip["tracks"][0]["clips"] = [{"clip_id": "clip_synthetic"}]
    candidate = deepcopy(document)
    candidate["candidate_refs"] = ["ast_synthetic"]
    for draft in (clip, candidate):
        response = save(client, draft)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unsupported_capability"


def test_new_reference_digest_and_kind_are_verified(runtime):
    client, _ = runtime
    document = create(client)
    identity = asset_id(upload(client, fixture="still.png"))
    asset = client.get(PREFIX + "/assets/" + identity, headers=HEADERS).json()
    for reference in (
        {"asset_id": identity, "kind": "image", "digest": "sha256:" + "0" * 64},
        {"asset_id": identity, "kind": "video", "digest": asset["content_sha256"]},
        {"asset_id": "ast_" + "0" * 32, "kind": "image", "digest": asset["content_sha256"]},
    ):
        response = save(client, {**document, "asset_refs": [reference]})
        assert response.status_code in {404, 409, 422}
    assert client.get(PROJECTS + "/" + document["project_id"], headers=HEADERS).json() == document


@pytest.mark.parametrize("change", ["missing", "changed"])
def test_existing_unavailable_library_reference_survives_read_and_rename(runtime, change):
    client, service = runtime
    source = service.gallery / "synthetic.png"
    source.write_bytes((FIXTURES / "still.png").read_bytes())
    imported = client.post(
        PREFIX + "/library", headers={**HEADERS, "X-Request-ID": "req_project_library"},
        json={"library_kind": "image", "library_item_id": "synthetic"},
    )
    identity = asset_id(imported)
    asset = client.get(PREFIX + "/assets/" + identity, headers=HEADERS).json()
    document = create(client)
    document["asset_refs"] = [{"asset_id": identity, "kind": "image", "digest": asset["content_sha256"]}]
    saved = save(client, document)
    assert saved.status_code == 200, saved.text
    document = saved.json()
    if change == "missing":
        source.unlink()
    else:
        source.write_bytes(source.read_bytes() + b"synthetic change")
    assert client.get(PROJECTS + "/" + document["project_id"], headers=HEADERS).json() == document
    assert client.get(PREFIX + "/assets/" + identity, headers=HEADERS).status_code in {404, 409}
    document["title"] = "Rename while reference unavailable"
    renamed = save(client, document)
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["asset_refs"] == document["asset_refs"]
    other = create(client, "New project cannot reuse unavailable source")
    assert save(client, {**other, "asset_refs": document["asset_refs"]}).status_code in {404, 409}


def test_two_simultaneous_saves_cannot_overwrite_each_other(runtime):
    client, _ = runtime
    document = create(client)

    def competing_save(title):
        return save(client, {**document, "title": title})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(competing_save, ("Synthetic A", "Synthetic B")))
    assert sorted(r.status_code for r in responses) == [200, 409]
    winner = next(r.json() for r in responses if r.status_code == 200)
    assert winner["revision"] == 2
    assert client.get(PROJECTS + "/" + document["project_id"], headers=HEADERS).json() == winner


@pytest.mark.parametrize("moment", ["before", "after"])
def test_process_crash_at_replace_preserves_valid_snapshot_and_unknown_files(runtime, monkeypatch, moment):
    client, service = runtime
    document = create(client)
    folder = service.media.root / "projects"
    file = folder / (document["project_id"] + ".json")
    before = file.read_bytes()
    unknown = folder / ".unclaimed-synthetic"
    unknown.write_bytes(b"must be retained")
    service.close()
    script = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from video_workbench.assets import AssetService, WORKSPACE_OWNER
service = AssetService(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
document = service.projects.read(WORKSPACE_OWNER, sys.argv[5])
document["title"] = "Interrupted synthetic save"
original_replace = os.replace
def crash_before_replace(source, target):
    if Path(target).name == document["project_id"] + ".json":
        if sys.argv[6] == "after":
            original_replace(source, target)
        os._exit(73)
    return original_replace(source, target)
os.replace = crash_before_replace
service.projects.save(WORKSPACE_OWNER, document["project_id"], document["revision"], document)
os._exit(74)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(Path(__file__).resolve().parents[1]),
         str(service.media.root), str(service.gallery), str(service.videos), document["project_id"], moment],
        capture_output=True, timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    assert result.returncode == 73, result.stderr.decode(errors="replace")
    expected = document
    if moment == "before":
        assert file.read_bytes() == before
    else:
        expected = json.loads(file.read_bytes())
        assert expected["revision"] == 2
        assert expected["title"] == "Interrupted synthetic save"
    remnants = set(folder.iterdir()) - {file, unknown}
    assert bool(remnants) == (moment == "before")
    restored = AssetService(service.media.root, service.gallery, service.videos)
    monkeypatch.setattr(main, "_workbench_asset_service", restored)
    assert client.get(PROJECTS + "/" + document["project_id"], headers=HEADERS).json() == expected
    assert unknown.read_bytes() == b"must be retained"
    assert all(path.exists() for path in remnants)
    expected["title"] = "Explicit save after restart"
    assert save(client, expected).status_code == 200
    assert all(path.exists() for path in remnants)
    restored.close()


def test_corrupt_or_future_snapshot_is_not_rewritten(runtime):
    client, service = runtime
    document = create(client)
    file = service.media.root / "projects" / (document["project_id"] + ".json")
    for raw in (
        b"{", json.dumps({**document, "schema_version": 999}).encode(),
        json.dumps({**document, "secret": "synthetic-extra-field"}).encode(),
    ):
        file.write_bytes(raw)
        response = client.get(PROJECTS + "/" + document["project_id"], headers=HEADERS)
        assert response.status_code in {422, 500}
        assert str(file) not in response.text
        assert file.read_bytes() == raw
