"""Authenticated media slice with isolated synthetic runtime storage."""

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

import main
from video_workbench.assets import AssetService, WORKSPACE_OWNER
from video_workbench.media import MediaIngestError


FIXTURES = Path(__file__).parent / "fixtures" / "video_workbench"
PREFIX = "/api/video-workbench"
HEADERS = {"X-Admin-Key": "synthetic-workbench-test-key", "Origin": "http://testserver"}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "prod")
    monkeypatch.setenv("ADMIN_KEY", HEADERS["X-Admin-Key"])
    gallery, videos = tmp_path / "gallery", tmp_path / "videos"
    gallery.mkdir()
    videos.mkdir()
    service = AssetService(tmp_path / "workbench", gallery, videos)
    monkeypatch.setattr(main, "_workbench_asset_service", service)
    with TestClient(main.app) as client:
        yield client, service
    for staged in list(service.media._issued.values()):
        service.media.cleanup_staged(staged)
    service.close()


def upload(client, request_id="req_test", fixture="cfr-h264.mp4", headers=None):
    return client.post(
        PREFIX + "/imports", headers=HEADERS if headers is None else headers,
        data={"request_id": request_id},
        files={"files": (fixture, (FIXTURES / fixture).read_bytes(), "application/octet-stream")},
    )


def asset_id(response):
    assert response.status_code == 200, response.text
    assert response.json()["job"]["state"] == "succeeded", response.text
    return response.json()["files"][0]["asset_id"]


def test_import_asset_media_range_and_thumbnail_are_authenticated(runtime):
    client, service = runtime
    original = (FIXTURES / "cfr-h264.mp4").read_bytes()
    response = upload(client)
    identity = asset_id(response)
    base = PREFIX + "/assets/" + identity
    view = client.get(base, headers=HEADERS)
    assert view.status_code == 200
    assert view.json()["origin"] == "upload"
    assert view.json()["content_sha256"] == "sha256:" + hashlib.sha256(original).hexdigest()
    for suffix in ("", "/content", "/thumbnail"):
        assert client.get(base + suffix).status_code == 401
    content = client.get(base + "/content", headers=HEADERS)
    assert content.content == original
    partial = client.get(base + "/content", headers={**HEADERS, "Range": "bytes=10-19"})
    assert partial.status_code == 206
    assert partial.content == original[10:20]
    assert partial.headers["content-range"] == f"bytes 10-19/{len(original)}"
    invalid = client.get(base + "/content", headers={**HEADERS, "Range": "bytes=999999999-"})
    assert invalid.status_code == 416
    thumb = client.get(base + "/thumbnail", headers=HEADERS)
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/jpeg"
    job = client.get(PREFIX + "/jobs/" + response.json()["job"]["job_id"], headers=HEADERS)
    assert job.json() == response.json()
    assert str(service.media.root) not in view.text + job.text
    assert client.get(PREFIX + "/assets", headers=HEADERS).json()["items"][0]["asset_id"] == identity
    assert not list(service.media.staging_root.rglob(".upload-*"))


@pytest.mark.parametrize("headers", [
    {}, {"X-Admin-Key": "wrong", "Origin": "http://testserver"},
    {"X-Admin-Key": HEADERS["X-Admin-Key"]},
    {**HEADERS, "Origin": "https://untrusted.invalid"},
    {**HEADERS, "Origin": "null"},
    {**HEADERS, "Sec-Fetch-Site": "cross-site"},
])
def test_auth_and_csrf_reject_before_staging(runtime, headers):
    client, service = runtime
    response = upload(client, headers=headers)
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "auth_required"
    assert not service.media.root.exists()


def test_dev_mode_does_not_grant_workbench_identity(runtime, monkeypatch):
    client, service = runtime
    monkeypatch.setenv("APP_MODE", "dev")
    monkeypatch.delenv("ADMIN_KEY")
    assert upload(client).status_code == 401
    assert not service.media.root.exists()


def test_idempotency_survives_service_restart_and_conflicts_on_changed_bytes(runtime, monkeypatch):
    client, service = runtime
    first = upload(client)
    first_id = asset_id(first)
    service.close()
    restored = AssetService(service.media.root, service.gallery, service.videos)
    monkeypatch.setattr(main, "_workbench_asset_service", restored)
    repeated = upload(client)
    assert repeated.json() == first.json()
    changed = upload(client, fixture="av-aac.mp4")
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "conflict"
    assert len(list(service.media.assets_root.glob("*/asset.json"))) == 1
    assert client.get(PREFIX + "/assets/" + first_id, headers=HEADERS).status_code == 200
    restored.close()


def test_corrupt_import_has_safe_per_file_failure_and_no_assets(runtime):
    client, service = runtime
    response = upload(client, fixture="corrupt.mp4")
    assert response.status_code == 200
    data = response.json()
    assert data["job"]["state"] == "failed"
    assert data["files"][0]["error"]["code"] == "media_corrupt"
    assert str(service.media.root) not in response.text
    assert not service.media.assets_root.exists()


def test_exact_library_selection_rechecks_identity_and_preserves_original(runtime):
    client, service = runtime
    original = (FIXTURES / "cfr-h264.mp4").read_bytes()
    source = service.videos / "synthetic_exact.mp4"
    source.write_bytes(original)
    body = {"library_kind": "video", "library_item_id": "synthetic"}
    headers = {**HEADERS, "X-Request-ID": "req_library"}
    absent = client.post(PREFIX + "/library", headers=headers, json=body)
    assert absent.status_code == 404
    body["library_item_id"] = "synthetic_exact"
    response = client.post(PREFIX + "/library", headers=headers, json=body)
    identity = asset_id(response)
    assert source.read_bytes() == original
    view = client.get(PREFIX + "/assets/" + identity, headers=HEADERS)
    assert view.json()["origin"] == "library"
    uploaded = asset_id(upload(client, request_id="req_external"))
    assert uploaded != identity
    source.write_bytes(b"synthetic replacement")
    assert client.get(PREFIX + "/assets/" + identity + "/content", headers=HEADERS).status_code == 409
    assert client.get(PREFIX + "/assets/" + uploaded + "/content", headers=HEADERS).content == original
    source.unlink()  # Test-owned synthetic source only.
    assert client.get(PREFIX + "/assets/" + identity, headers=HEADERS).status_code == 404


@pytest.mark.parametrize("item_id", ["../synthetic", "C:\\private\\clip", "https://invalid.test/clip", "SYNTHETIC"])
def test_library_path_url_and_case_alias_not_accepted(runtime, item_id):
    client, service = runtime
    (service.videos / "synthetic.mp4").write_bytes((FIXTURES / "cfr-h264.mp4").read_bytes())
    response = client.post(
        PREFIX + "/library", headers={**HEADERS, "X-Request-ID": "req_invalid"},
        json={"library_kind": "video", "library_item_id": item_id},
    )
    assert response.status_code in {404, 422}
    assert not service.media.assets_root.exists()


def test_library_expected_digest_is_compare_only(runtime):
    client, service = runtime
    source = service.gallery / "synthetic.png"
    source.write_bytes((FIXTURES / "still.png").read_bytes())
    response = client.post(
        PREFIX + "/library", headers={**HEADERS, "X-Request-ID": "req_digest"},
        json={"library_kind": "image", "library_item_id": "synthetic", "expected_sha256": "sha256:" + "0" * 64},
    )
    assert response.status_code == 409
    assert source.is_file()
    assert not service.media.assets_root.exists()


def test_unknown_fields_rejected_without_echo(runtime):
    client, service = runtime
    response = client.post(
        PREFIX + "/library", headers={**HEADERS, "X-Request-ID": "req_unknown"},
        json={"library_kind": "image", "library_item_id": "synthetic", "url": "https://private.invalid/secret"},
    )
    assert response.status_code == 422
    assert "private.invalid" not in response.text
    assert not service.media.root.exists()


def test_upload_count_and_unknown_multipart_field_rejected(runtime):
    client, service = runtime
    for files, data in (
        ([("files", ("test.png", b"x"))] * 11, {"request_id": "req_many"}),
        ([("files", ("test.png", b"x"))], {"request_id": "req_field", "path": "private"}),
    ):
        response = client.post(PREFIX + "/imports", headers=HEADERS, files=files, data=data)
        assert response.status_code == 422
        assert not service.media.assets_root.exists()


def test_orphan_asset_and_other_owner_not_exposed(runtime):
    client, service = runtime
    orphan = service.media.import_content("job_orphan", "still.png", (FIXTURES / "still.png").read_bytes())
    assert client.get(PREFIX + "/assets/" + orphan.asset_id, headers=HEADERS).status_code == 404
    with pytest.raises(MediaIngestError) as error:
        service.asset("another-owner", orphan.asset_id)
    assert error.value.code == "forbidden"


def test_interrupted_job_is_not_replayed(runtime):
    client, service = runtime
    first = upload(client)
    identity = asset_id(first)
    job_id = first.json()["job"]["job_id"]
    path = service.jobs / (job_id + ".json")
    record = json.loads(path.read_text())
    record["view"]["state"] = "preparing"
    path.write_text(json.dumps(record), encoding="utf-8")
    response = upload(client)
    assert response.json()["job"]["state"] == "interrupted"
    assert len(list(service.media.assets_root.glob("*/asset.json"))) == 1
    assert response.json()["job"]["asset_ids"] == [identity]


def test_asset_list_filter_limit_and_unknown_queries(runtime):
    client, service = runtime
    asset_id(upload(client, request_id="req_image", fixture="still.png"))
    asset_id(upload(client, request_id="req_video"))
    page = client.get(PREFIX + "/assets?limit=1", headers=HEADERS).json()
    assert len(page["items"]) == 1
    assert page["next_cursor"]
    second = client.get(PREFIX + "/assets", headers=HEADERS, params={"cursor": page["next_cursor"], "limit": 1}).json()
    assert len(second["items"]) == 1
    assert second["items"][0]["asset_id"] != page["items"][0]["asset_id"]
    images = client.get(PREFIX + "/assets?kind=image", headers=HEADERS).json()
    assert [item["kind"] for item in images["items"]] == ["image"]
    assert client.get(PREFIX + "/assets?path=private", headers=HEADERS).status_code == 422


def test_oversized_or_truncated_multipart_headers_fail_closed(runtime):
    client, service = runtime
    for body in (
        b'--boundary\r\nContent-Disposition: form-data; name="files"; filename="' + b"x" * 9000,
        b'--boundary\r\nContent-Disposition: form-data; name="files"; filename="test.png"\r\n\r\nabc',
    ):
        response = client.post(
            PREFIX + "/imports",
            headers={**HEADERS, "Content-Type": "multipart/form-data; boundary=boundary"},
            content=body,
        )
        assert response.status_code == 422
        assert not service.media.assets_root.exists()


def test_streamed_body_cap_without_content_length(runtime, monkeypatch):
    import video_workbench.api as api
    client, service = runtime
    monkeypatch.setattr(api, "_BODY_LIMIT", 64)
    response = client.post(
        PREFIX + "/imports",
        headers={**HEADERS, "Content-Type": "multipart/form-data; boundary=boundary"},
        content=iter([b'--boundary\r\nContent-Disposition: form-data; name="request_id"\r\n\r\n', b"x" * 100]),
    )
    assert response.status_code == 413
    assert not service.media.assets_root.exists()


def test_manifest_tampering_is_not_exposed(runtime):
    client, service = runtime
    identity = asset_id(upload(client))
    path = service.media.assets_root / identity / "asset.json"
    data = json.loads(path.read_text())
    data["metadata"]["width"] = -100
    path.write_text(json.dumps(data), encoding="utf-8")
    assert client.get(PREFIX + "/assets/" + identity, headers=HEADERS).status_code == 404


def test_job_other_owner_is_denied(runtime):
    client, service = runtime
    response = upload(client)
    identity = asset_id(response)
    job_path = service.jobs / (response.json()["job"]["job_id"] + ".json")
    data = json.loads(job_path.read_text())
    data["owner"] = "another-owner"
    job_path.write_text(json.dumps(data), encoding="utf-8")
    assert client.get(PREFIX + "/assets/" + identity, headers=HEADERS).status_code == 403


def test_library_symlink_source_is_rejected(runtime, tmp_path):
    client, service = runtime
    outside = tmp_path / "outside.png"
    outside.write_bytes((FIXTURES / "still.png").read_bytes())
    try:
        (service.gallery / "linked.png").symlink_to(outside)
    except OSError:
        pytest.skip("host does not permit symlink creation")
    response = client.post(
        PREFIX + "/library", headers={**HEADERS, "X-Request-ID": "req_link"},
        json={"library_kind": "image", "library_item_id": "linked"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal"
    assert not service.media.assets_root.exists()
    assert outside.read_bytes() == (FIXTURES / "still.png").read_bytes()


def test_idempotent_library_registration_preserves_exact_provenance(runtime):
    client, service = runtime
    payload = (FIXTURES / "still.png").read_bytes()
    (service.gallery / "first.png").write_bytes(payload)
    (service.gallery / "second.png").write_bytes(payload)
    def register(source, request_id):
        return client.post(
            PREFIX + "/library", headers={**HEADERS, "X-Request-ID": request_id},
            json={"library_kind": "image", "library_item_id": source},
        )
    first = register("first", "req_first")
    first_id = asset_id(first)
    second_id = asset_id(register("second", "req_second"))
    assert first_id != second_id
    assert register("first", "req_first").json() == first.json()


def test_cleanup_failure_preserves_published_asset_and_reports_cleanup_stage(runtime, monkeypatch):
    from video_workbench.media.ingest import _fail
    client, service = runtime
    def fail_cleanup(_staged):
        raise _fail("cleanup_pending", "cleanup", retryable=True)
    with monkeypatch.context() as patch:
        patch.setattr(service.media, "cleanup_staged", fail_cleanup)
        response = upload(client)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["job"]["state"] == "failed"
    assert data["job"]["stage"] == "cleanup"
    assert data["files"][0]["state"] == "ready"
    assert data["files"][0]["error"]["code"] == "cleanup_pending"
    identity = data["files"][0]["asset_id"]
    assert client.get(PREFIX + "/assets/" + identity + "/content", headers=HEADERS).content == (
        FIXTURES / "cfr-h264.mp4"
    ).read_bytes()
    assert len(list(service.media.assets_root.glob("*/asset.json"))) == 1
