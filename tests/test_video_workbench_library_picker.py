"""Synthetic-only candidate discovery and lazy preview contract evidence."""

import asyncio
from contextlib import contextmanager
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import threading

from PIL import Image
import pytest

from test_video_workbench_api import runtime, FIXTURES, HEADERS, PREFIX, asset_id
from video_workbench.assets import WORKSPACE_OWNER
from video_workbench.media import MediaIngestError
from video_workbench.media.ingest import _fail


LIST = PREFIX + "/library/candidates"
PREVIEW = PREFIX + "/library/preview"


def populate(service, name="synthetic", kind="image"):
    root, fixture, suffix = (
        (service.gallery, "still.png", ".png") if kind == "image"
        else (service.videos, "cfr-h264.mp4", ".mp4")
    )
    path = root / (name + suffix)
    path.write_bytes((FIXTURES / fixture).read_bytes())
    return path


def selection(name="synthetic", kind="image"):
    return {"library_kind": kind, "library_item_id": name}


def test_discovery_paginates_without_probe_hash_or_publication(runtime, monkeypatch):
    client, service = runtime
    for kind in ("image", "video"):
        for name in ("a", "aa", "b", "z"):
            populate(service, name, kind)
    (service.gallery / "ignore.jpg").write_bytes(b"not an accepted library suffix")
    (service.gallery / "directory.png").mkdir()
    (service.gallery / "wrong.PNG").write_bytes(b"wrong suffix case")

    def forbidden(*args, **kwargs):
        pytest.fail("candidate listing must not hash, probe or publish")
    for name in ("_hash_file", "probe", "publish"):
        monkeypatch.setattr(service.media, name, forbidden)
    rows, cursor = [], ""
    while True:
        response = client.get(LIST, headers=HEADERS, params={"cursor": cursor, "limit": 3})
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "private, no-store"
        page = response.json()
        assert set(page) == {"items", "next_cursor"}
        rows.extend(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert [(r["library_kind"], r["library_item_id"]) for r in rows] == [
        (kind, name) for kind in ("image", "video") for name in ("a", "aa", "b", "z")
    ]
    assert all(set(r) == {"library_kind", "library_item_id", "byte_length"} for r in rows)
    assert not service.media.root.exists()
    filtered = client.get(LIST, headers=HEADERS, params={"query": "A", "kind": "video"}).json()
    assert [r["library_item_id"] for r in filtered["items"]] == ["a", "aa"]


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 51}, {"limit": "1.0"}, {"limit": "+2"},
    {"kind": "audio"}, {"query": "x" * 129}, {"query": "\x00"},
    {"cursor": "not-json"}, {"cursor": "x" * 3073}, {"cursor": "="},
    {"path": "../"}, [("kind", "image"), ("kind", "video")],
])
def test_candidate_invalid_inputs(runtime, params):
    client, _ = runtime
    response = client.get(LIST, headers=HEADERS, params=params)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "invalid_request"


def test_cursor_is_bound_to_filters_and_handles_unicode(runtime):
    client, service = runtime
    for name in ("\u56fe1", "\u56fe2", "\u56fe3"):
        populate(service, name)
    params = {"kind": "image", "query": "\u56fe", "limit": 1}
    page = client.get(LIST, headers=HEADERS, params=params).json()
    cursor = page["next_cursor"]
    assert len(cursor) <= 3072
    assert client.get(LIST, headers=HEADERS, params={**params, "cursor": cursor}).json()["items"][0]["library_item_id"] == "\u56fe2"
    for change in ({"query": ""}, {"kind": "video"}):
        assert client.get(LIST, headers=HEADERS, params={**params, "cursor": cursor, **change}).status_code == 422
    (service.gallery / "\u56fe2.png").unlink()
    assert client.get(LIST, headers=HEADERS, params={**params, "cursor": cursor}).json()["items"][0]["library_item_id"] == "\u56fe3"


def test_listing_budget_returns_no_partial_page(runtime, monkeypatch):
    import video_workbench.library as library
    client, service = runtime
    populate(service)
    monkeypatch.setattr(library, "_SCAN_ENTRIES", 0)
    response = client.get(LIST, headers=HEADERS)
    assert response.status_code == 409
    assert "items" not in response.json()
    monkeypatch.setattr(library, "_SCAN_ENTRIES", 100_000)
    monkeypatch.setattr(library, "_SCAN_SECONDS", -1)
    assert client.get(LIST, headers=HEADERS).status_code == 409


def test_listing_directory_mutation_is_a_conflict(runtime, monkeypatch):
    import video_workbench.library as library
    client, service = runtime
    populate(service)
    original = library.os.scandir

    @contextmanager
    def changing_scan(root):
        with original(root) as entries:
            yield entries
        if Path(root) == service.gallery:
            info = service.gallery.stat()
            os.utime(service.gallery, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))
    monkeypatch.setattr(library.os, "scandir", changing_scan)
    assert client.get(LIST, headers=HEADERS).status_code == 409


def test_missing_library_roots_are_empty(runtime):
    client, service = runtime
    service.gallery.rmdir()
    service.videos.rmdir()
    assert client.get(LIST, headers=HEADERS).json() == {"items": [], "next_cursor": None}


@pytest.mark.parametrize("kind", ["image", "video"])
def test_lazy_preview_binds_digest_and_only_explicit_import_publishes(runtime, kind):
    client, service = runtime
    source = populate(service, kind=kind)
    before = source.read_bytes()
    response = client.post(PREVIEW, headers=HEADERS, json=selection(kind=kind))
    assert response.status_code == 200, response.text
    digest = "sha256:" + hashlib.sha256(before).hexdigest()
    assert response.headers["x-content-sha256"] == digest
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-type"] == "image/jpeg"
    with Image.open(BytesIO(response.content)) as image:
        assert image.format == "JPEG"
        assert image.size == (320, 180)
    assert not list(service.media.assets_root.glob("*/asset.json"))
    assert not list(service.jobs.glob("*.json"))
    assert not list(service.media.staging_root.glob("*/*"))
    assert not service.runtime._leases
    assert not service._active
    assert source.read_bytes() == before
    assert client.get(PREFIX + "/assets", headers=HEADERS).json()["items"] == []
    registered = client.post(
        PREFIX + "/library", headers={**HEADERS, "X-Request-ID": "req_preview_import"},
        json={**selection(kind=kind), "expected_sha256": digest},
    )
    identity = asset_id(registered)
    assert client.get(PREFIX + "/assets/" + identity, headers=HEADERS).json()["content_sha256"] == digest


def test_preview_digest_rejects_changed_selection(runtime):
    client, service = runtime
    source = populate(service)
    preview = client.post(PREVIEW, headers=HEADERS, json=selection())
    assert preview.status_code == 200
    source.write_bytes(source.read_bytes() + b"changed")
    response = client.post(
        PREFIX + "/library", headers={**HEADERS, "X-Request-ID": "req_stale_preview"},
        json={**selection(), "expected_sha256": preview.headers["x-content-sha256"]},
    )
    assert response.status_code == 409
    assert not list(service.media.assets_root.glob("*/asset.json"))


@pytest.mark.parametrize("headers", [
    {}, {"X-Admin-Key": "wrong"}, {"X-Admin-Key": HEADERS["X-Admin-Key"]},
    {**HEADERS, "Origin": "https://untrusted.invalid"},
    {**HEADERS, "Sec-Fetch-Site": "cross-site"},
])
def test_preview_auth_csrf_precede_source_work(runtime, headers):
    client, service = runtime
    assert client.post(PREVIEW, headers=headers, json=selection()).status_code == 401
    assert not service.media.root.exists()
    assert client.get(LIST).status_code == 401


@pytest.mark.parametrize("body", [
    selection("../escape"), selection("https://invalid"), selection(kind="audio"),
    {**selection(), "path": "/private"}, {**selection(), "expected_sha256": "ignored"},
    {"library_kind": [], "library_item_id": "synthetic"}, [], {},
])
def test_preview_rejects_bad_identity_and_unknown_fields(runtime, body):
    client, service = runtime
    assert client.post(PREVIEW, headers=HEADERS, json=body).status_code == 422
    assert not service.media.assets_root.exists()


@pytest.mark.parametrize("body", [
    b'{"library_kind":"image","library_kind":"video","library_item_id":"x"}',
    b"[" * 2000, b" " * 4097, b"\xff",
])
def test_preview_rejects_malformed_json(runtime, body):
    client, _ = runtime
    assert client.post(PREVIEW, headers=HEADERS, content=body).status_code == 422


def test_preview_missing_corrupt_and_exact_case(runtime):
    client, service = runtime
    populate(service)
    assert client.post(PREVIEW, headers=HEADERS, json=selection("Synthetic")).status_code == 404
    assert client.post(PREVIEW, headers=HEADERS, json=selection("synthe")).status_code == 404
    (service.videos / "broken.mp4").write_bytes(b"corrupt")
    response = client.post(PREVIEW, headers=HEADERS, json=selection("broken", "video"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "media_corrupt"
    assert not list(service.media.staging_root.glob("*/*"))
    assert str(service.media.root) not in response.text


@pytest.mark.parametrize("mutation,code", [("change", "conflict"), ("remove", "not_found")])
def test_change_during_preview_is_rejected_and_cleaned(runtime, monkeypatch, mutation, code):
    client, service = runtime
    source = populate(service)
    original = service.media.preview_staged

    def mutate(staged):
        result = original(staged)
        if mutation == "remove":
            source.unlink()
        else:
            source.write_bytes(source.read_bytes() + b"change")
        return result
    monkeypatch.setattr(service.media, "preview_staged", mutate)
    response = client.post(PREVIEW, headers=HEADERS, json=selection())
    assert response.json()["error"]["code"] == code
    assert not list(service.media.staging_root.glob("*/*"))
    assert not service.runtime._leases


def test_preview_cancel_and_admission_lock(runtime, monkeypatch):
    _, service = runtime
    populate(service)
    event = threading.Event()
    event.set()
    with pytest.raises(MediaIngestError) as error:
        service.library_preview(WORKSPACE_OWNER, **selection(), cancelled=event)
    assert error.value.code == "job_cancelled"
    assert not service._active
    with service._exclusive(), pytest.raises(MediaIngestError) as error:
        service.library_preview(WORKSPACE_OWNER, **selection())
    assert error.value.code == "conflict"
    event.clear()

    def cancel(staged):
        event.set()
        from video_workbench.media.worker import check_cancelled
        check_cancelled()
    monkeypatch.setattr(service.media, "probe", cancel)
    with pytest.raises(MediaIngestError) as error:
        service.library_preview(WORKSPACE_OWNER, **selection(), cancelled=event)
    assert error.value.code == "job_cancelled"
    assert not list(service.media.staging_root.glob("*/*"))
    assert not service.runtime._leases


def test_cleanup_failure_is_not_a_success(runtime, monkeypatch):
    client, service = runtime
    populate(service)
    original = service.media.cleanup_staged
    monkeypatch.setattr(service.media, "cleanup_staged", lambda _: (_ for _ in ()).throw(_fail("cleanup_pending", "cleanup")))
    response = client.post(PREVIEW, headers=HEADERS, json=selection())
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cleanup_pending"
    assert service.media._issued
    assert not service.runtime._leases
    monkeypatch.setattr(service.media, "cleanup_staged", original)
    for staged in list(service.media._issued.values()):
        original(staged)


def test_thumbnail_cleanup_failure_retains_reservation_and_unknown_files(runtime, monkeypatch):
    client, service = runtime
    source = populate(service)
    original_bytes = source.read_bytes()
    original_unlink = Path.unlink
    retained = []

    def fail_thumbnail(path, *args, **kwargs):
        if path.name.startswith(".thumbnail-"):
            retained.append(path)
            raise PermissionError("synthetic cleanup denial")
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fail_thumbnail)
    response = client.post(PREVIEW, headers=HEADERS, json=selection())
    assert response.json()["error"]["code"] == "cleanup_pending"
    assert service.media._issued
    assert retained and retained[0].exists()
    assert source.read_bytes() == original_bytes
    from video_workbench.media.ingest import _RESERVATIONS
    assert any(token is service.media._reservation_token for token, _ in _RESERVATIONS)
    monkeypatch.setattr(Path, "unlink", original_unlink)
    for path in retained:
        path.unlink()
    for staged in list(service.media._issued.values()):
        service.media.cleanup_staged(staged)


@pytest.mark.parametrize("code", ["dependency_missing", "probe_timeout", "disk_space"])
def test_preview_worker_failure_cleans_staging_and_redacts(runtime, monkeypatch, code):
    client, service = runtime
    populate(service)

    def fail(staged):
        raise _fail(code, "probe")
    monkeypatch.setattr(service.media, "probe", fail)
    response = client.post(PREVIEW, headers=HEADERS, json=selection())
    assert response.json()["error"]["code"] == code
    assert str(service.gallery) not in response.text
    assert not service.media._issued
    assert not service.runtime._leases


def test_preview_disconnect_signals_worker_and_cleans_before_return(runtime, monkeypatch):
    from fastapi import FastAPI
    from video_workbench.api import build_router
    from video_workbench.media.worker import current_execution, check_cancelled
    _, service = runtime
    populate(service)
    entered = threading.Event()
    observed = threading.Event()

    def blocking_probe(staged):
        event = current_execution().cancelled
        entered.set()
        assert event.wait(3), "disconnect did not cancel candidate processing"
        observed.set()
        check_cancelled()
    monkeypatch.setattr(service.media, "probe", blocking_probe)
    app = FastAPI()
    app.include_router(build_router(lambda: service, lambda: HEADERS["X-Admin-Key"], lambda: []))

    async def exercise():
        sent = []
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": json.dumps(selection()).encode(), "more_body": False}
            if entered.is_set():
                return {"type": "http.disconnect"}
            await asyncio.sleep(1)
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": PREVIEW, "raw_path": PREVIEW.encode(),
            "query_string": b"", "root_path": "", "server": ("testserver", 80),
            "client": ("127.0.0.1", 1),
            "headers": [(key.lower().encode(), value.encode()) for key, value in HEADERS.items()],
        }
        await asyncio.wait_for(app(scope, receive, send), timeout=5)
        assert sent[0]["status"] == 422
    asyncio.run(exercise())
    assert observed.is_set()
    assert not service._active
    assert not service.media._issued
    assert not service.runtime._leases


def test_preview_symlink_is_never_followed(runtime):
    client, service = runtime
    source = populate(service)
    link = service.gallery / "link.png"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("symlink privilege unavailable")
    for method, route, kwargs in (
        (client.get, LIST, {}),
        (client.post, PREVIEW, {"json": selection("link")}),
    ):
        response = method(route, headers=HEADERS, **kwargs)
        assert response.status_code == 500
    assert source.exists()
    assert not service.media._issued
