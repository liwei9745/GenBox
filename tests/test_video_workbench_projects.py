"""Frozen project snapshots exercised only in synthetic temporary stores."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import threading
from types import SimpleNamespace

import pytest

from video_workbench.assets import AssetService, WORKSPACE_OWNER
from video_workbench.media import MediaIngestError
from video_workbench.media.ingest import _fail
from video_workbench.projects import schema, store


OWNER = WORKSPACE_OWNER
PROFILE = {
    "profile_id": "landscape_1080p_30",
    "canvas": {"width": 1920, "height": 1080},
    "fps": {"num": 30, "den": 1},
    "fit_mode": "contain",
}
REF = {"asset_id": "ast_synthetic_01", "kind": "image", "digest": "sha256:" + "a" * 64}


@pytest.fixture
def service(tmp_path):
    result = AssetService(tmp_path / "store", tmp_path / "gallery", tmp_path / "videos")
    yield result
    result.close()


def create(service, **kwargs):
    return service.projects.create(OWNER, kwargs.get("title", "Synthetic project"), kwargs.get("profile", PROFILE))


def path_for(service, document):
    return service.projects.root / (document["project_id"] + ".json")


def save(service, document, **kwargs):
    return service.projects.save(
        OWNER, document["project_id"], kwargs.get("revision", document["revision"]), document,
    )


def ready_asset(ref=REF):
    return SimpleNamespace(
        asset_id=ref["asset_id"], kind=ref["kind"],
        content_sha256=ref["digest"].removeprefix("sha256:"), state="ready",
    )


def reference_project(service, monkeypatch):
    monkeypatch.setattr(service, "asset", lambda owner, identity: ready_asset())
    document = create(service)
    document["asset_refs"] = [dict(REF)]
    return save(service, document)


@pytest.mark.parametrize("portrait", [False, True])
def test_create_save_read_restart_has_exact_detached_frozen_shape(service, portrait):
    profile = deepcopy(PROFILE)
    if portrait:
        profile["profile_id"] = "portrait_1080p_30"
        profile["canvas"] = {"width": 1080, "height": 1920}
    created = create(service, title="  Synthetic project  ", profile=profile)
    assert set(created) == {
        "schema_version", "project_id", "revision", "title", "output_profile",
        "tracks", "asset_refs", "candidate_refs", "created_at", "updated_at",
    }
    schema.project_id(created["project_id"])
    assert created["schema_version"] == created["revision"] == 1
    assert created["title"] == "Synthetic project"
    assert created["created_at"] == created["updated_at"]
    assert created["asset_refs"] == created["candidate_refs"] == []
    assert created["tracks"] == [
        {"track_id": "trk_picture", "kind": "picture", "clips": []},
        {"track_id": "trk_audio", "kind": "audio", "clips": []},
    ]
    assert created["output_profile"] == profile
    profile["canvas"]["width"] = 1
    assert service.projects.read(OWNER, created["project_id"]) == created
    created["title"] = "  Renamed project  "
    result = save(service, created)
    assert result["revision"] == 2
    assert result["title"] == "Renamed project"
    assert result["created_at"] == created["created_at"]
    assert schema.timestamp(result["updated_at"]) >= schema.timestamp(created["updated_at"])
    assert created["revision"] == 1
    raw = path_for(service, result).read_bytes()
    assert json.loads(raw) == result
    result["title"] = "not saved"
    assert service.projects.read(OWNER, result["project_id"])["title"] == "Renamed project"
    service.close()
    restored = AssetService(service.media.root, service.gallery, service.videos)
    try:
        assert restored.projects.read(OWNER, result["project_id"]) == json.loads(raw)
        assert path_for(service, result).read_bytes() == raw
    finally:
        restored.close()


@pytest.mark.parametrize("value", ["", "  ", None, True, "a" * 201, "line\nbreak", "\x7f", "\ud800"])
def test_invalid_create_title_has_no_project_side_effect(service, value):
    with pytest.raises(MediaIngestError) as error:
        create(service, title=value)
    assert error.value.code == "invalid_request"
    assert not service.projects.root.exists()


def test_unicode_title_accepts_exact_character_limit(service):
    document = create(service, title="\u754c" * 200)
    assert len(document["title"]) == 200
    assert service.projects.read(OWNER, document["project_id"]) == document


@pytest.mark.parametrize("change", [
    lambda profile: profile.update(video_codec="h264"),
    lambda profile: profile.update(profile_id="unknown"),
    lambda profile: profile.update(fit_mode="cover"),
    lambda profile: profile["canvas"].update(width=1080),
    lambda profile: profile["canvas"].update(height=1080.0),
    lambda profile: profile["fps"].update(num=24),
    lambda profile: profile["fps"].update(den=True),
    lambda profile: profile["fps"].update(extra=0),
])
def test_profile_is_exact_not_coerced(service, change):
    profile = deepcopy(PROFILE)
    change(profile)
    with pytest.raises(MediaIngestError) as error:
        create(service, profile=profile)
    assert error.value.code == "invalid_request"
    assert not service.projects.root.exists()


@pytest.mark.parametrize("change", [
    lambda doc: doc.update(schema_version=True),
    lambda doc: doc.update(schema_version=2),
    lambda doc: doc.update(revision=True),
    lambda doc: doc.update(revision=1.0),
    lambda doc: doc.update(revision=0),
    lambda doc: doc.update(extra="not frozen"),
    lambda doc: doc.update(created_at="2026-09-19"),
    lambda doc: doc.update(created_at="2026-02-30T00:00:00Z"),
    lambda doc: doc.update(updated_at="2026-09-19T12:00:00"),
    lambda doc: doc.update(created_at="2026-09-19T12:00:00+02:00"),
    lambda doc: doc.update(title="\x00"),
    lambda doc: doc.update(asset_refs={}),
    lambda doc: doc.update(candidate_refs={}),
    lambda doc: doc.update(tracks=[]),
    lambda doc: doc["tracks"].reverse(),
    lambda doc: doc["tracks"][0].update(extra=True),
    lambda doc: doc["tracks"][0].update(clips={}),
])
def test_invalid_save_preserves_previous_snapshot_and_draft(service, change):
    document = create(service)
    path = path_for(service, document)
    before = path.read_bytes()
    change(document)
    draft = deepcopy(document)
    with pytest.raises(MediaIngestError) as error:
        save(service, document, revision=1)
    assert error.value.code == "invalid_request"
    assert path.read_bytes() == before
    assert document == draft


@pytest.mark.parametrize("field", ["created_at", "updated_at"])
def test_client_cannot_change_server_timestamps(service, field):
    document = create(service)
    before = path_for(service, document).read_bytes()
    document[field] = "2026-01-01T00:00:00Z"
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "invalid_request"
    assert path_for(service, document).read_bytes() == before


@pytest.mark.parametrize("field", ["candidate_refs", "clips"])
def test_future_timeline_and_candidates_are_explicitly_unsupported(service, field):
    document = create(service)
    before = path_for(service, document).read_bytes()
    if field == "clips":
        document["tracks"][0]["clips"] = [{"clip_id": "clip_synthetic"}]
    else:
        document[field] = [{"asset_id": "ast_synthetic"}]
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "unsupported_capability"
    assert path_for(service, document).read_bytes() == before


@pytest.mark.parametrize("expected", [True, 1.0, 0, -1, "1", None])
def test_expected_revision_requires_positive_integer(service, expected):
    document = create(service)
    with pytest.raises(MediaIngestError) as error:
        save(service, document, revision=expected)
    assert error.value.code == "invalid_request"
    assert service.projects.read(OWNER, document["project_id"]) == document


@pytest.mark.parametrize("stale_expected", [False, True])
def test_stale_document_or_expected_revision_is_conflict(service, stale_expected):
    document = create(service)
    result = save(service, document)
    draft = deepcopy(result if stale_expected else document)
    before = path_for(service, document).read_bytes()
    with pytest.raises(MediaIngestError) as error:
        save(service, draft, revision=1 if stale_expected else 2)
    assert (error.value.code, error.value.stage) == ("conflict", "save")
    assert path_for(service, document).read_bytes() == before


def test_project_identity_cannot_be_reassigned(service):
    document = create(service)
    other = create(service)
    with pytest.raises(MediaIngestError) as error:
        service.projects.save(OWNER, other["project_id"], 1, document)
    assert error.value.code == "invalid_request"
    assert service.projects.read(OWNER, other["project_id"]) == other


@pytest.mark.parametrize("operation", ["create", "read", "save"])
def test_wrong_owner_rejected_without_lookup(service, operation):
    document = create(service)
    with pytest.raises(MediaIngestError) as error:
        if operation == "create":
            service.projects.create("someone-else", "Synthetic", PROFILE)
        elif operation == "read":
            service.projects.read("someone-else", document["project_id"])
        else:
            service.projects.save("someone-else", document["project_id"], 1, document)
    assert (error.value.code, error.value.stage) == ("forbidden", "ownership")
    assert service.projects.read(OWNER, document["project_id"]) == document


@pytest.mark.parametrize("identity", ["../outside", "/absolute", "C:\\synthetic", "prj_short", "prj_" + "A" * 32, True])
def test_project_path_is_never_caller_selected(service, identity):
    with pytest.raises(MediaIngestError) as error:
        service.projects.read(OWNER, identity)
    assert error.value.code == "invalid_request"


def test_unknown_project_returns_not_found(service):
    with pytest.raises(MediaIngestError) as error:
        service.projects.read(OWNER, "prj_" + "a" * 32)
    assert error.value.code == "not_found"


def test_generated_id_collision_never_overwrites(service, monkeypatch):
    monkeypatch.setattr(store.uuid, "uuid4", lambda: SimpleNamespace(hex="a" * 32))
    document = create(service)
    before = path_for(service, document).read_bytes()
    with pytest.raises(MediaIngestError) as error:
        create(service, title="Overwrite attempt")
    assert error.value.code == "conflict"
    assert path_for(service, document).read_bytes() == before


@pytest.mark.parametrize("change", [
    lambda ref: ref.update(digest="a" * 64),
    lambda ref: ref.update(digest="sha256:" + "A" * 64),
    lambda ref: ref.update(kind="unknown"),
    lambda ref: ref.update(kind=[]),
    lambda ref: ref.update(asset_id="../outside"),
    lambda ref: ref.update(asset_id="https://example.invalid/media"),
    lambda ref: ref.update(extra=1),
])
def test_reference_shape_is_exact(service, change):
    document = create(service)
    ref = dict(REF)
    change(ref)
    document["asset_refs"] = [ref]
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "invalid_request"


def test_duplicate_asset_identity_rejected(service):
    document = create(service)
    document["asset_refs"] = [dict(REF), {**REF, "digest": "sha256:" + "b" * 64}]
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "invalid_request"


def test_new_reference_resolves_owner_kind_digest_and_read_does_not_reprobe(service, monkeypatch):
    calls = []

    def asset(owner, identity):
        calls.append((owner, identity))
        return ready_asset()

    monkeypatch.setattr(service, "asset", asset)
    document = create(service)
    document["asset_refs"] = [dict(REF)]
    result = save(service, document)
    assert calls == [(OWNER, REF["asset_id"])]
    assert service.projects.read(OWNER, result["project_id"]) == result
    assert len(calls) == 1


@pytest.mark.parametrize("code", ["not_found", "conflict", "forbidden", "internal", "disk_space"])
def test_new_unavailable_reference_fails_closed(service, monkeypatch, code):
    document = create(service)
    before = path_for(service, document).read_bytes()

    def unavailable(*args):
        raise _fail(code, "lookup")

    monkeypatch.setattr(service, "asset", unavailable)
    document["asset_refs"] = [dict(REF)]
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == code
    assert path_for(service, document).read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("kind", "video"), ("state", "missing"), ("content_sha256", "b" * 64), ("asset_id", "ast_different"),
])
def test_new_asset_must_be_ready_with_matching_server_identity(service, monkeypatch, field, value):
    record = ready_asset()
    setattr(record, field, value)
    monkeypatch.setattr(service, "asset", lambda *args: record)
    document = create(service)
    document["asset_refs"] = [dict(REF)]
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "conflict"


@pytest.mark.parametrize("code", ["not_found", "conflict"])
def test_rename_retains_only_exact_previous_missing_or_changed_reference(service, monkeypatch, code):
    document = reference_project(service, monkeypatch)

    def unavailable(*args):
        raise _fail(code, "lookup")

    monkeypatch.setattr(service, "asset", unavailable)
    document["title"] = "Renamed despite unavailable original"
    saved = save(service, document)
    assert saved["asset_refs"] == [REF]
    assert service.projects.read(OWNER, saved["project_id"]) == saved
    saved["asset_refs"][0]["digest"] = "sha256:" + "b" * 64
    with pytest.raises(MediaIngestError) as error:
        save(service, saved)
    assert error.value.code == code
    assert service.projects.read(OWNER, saved["project_id"])["asset_refs"] == [REF]


@pytest.mark.parametrize("code", ["forbidden", "internal", "disk_space", "cleanup_pending"])
def test_existing_reference_does_not_hide_other_asset_failures(service, monkeypatch, code):
    document = reference_project(service, monkeypatch)
    before = path_for(service, document).read_bytes()

    def failed(*args):
        raise _fail(code, "lookup")

    monkeypatch.setattr(service, "asset", failed)
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == code
    assert path_for(service, document).read_bytes() == before


def test_reference_removal_does_not_touch_media_or_require_resolution(service, monkeypatch):
    document = reference_project(service, monkeypatch)
    monkeypatch.setattr(service, "asset", lambda *args: pytest.fail("Removed reference resolved"))
    document["asset_refs"] = []
    assert save(service, document)["asset_refs"] == []


@pytest.mark.parametrize("raw", [
    b"{broken", b"[]", b'{"schema_version":1,"schema_version":1}',
    b'{"x":NaN}', b'{"x":Infinity}', b"\xff", b"[" * 1100,
])
def test_malformed_stored_json_fails_closed_without_rewriting(service, raw):
    document = create(service)
    path = path_for(service, document)
    path.write_bytes(raw)
    for operation in ("read", "save"):
        with pytest.raises(MediaIngestError) as error:
            if operation == "read":
                service.projects.read(OWNER, document["project_id"])
            else:
                save(service, document)
        assert error.value.code == "internal"
        assert path.read_bytes() == raw


@pytest.mark.parametrize("change", [
    lambda doc: doc.update(schema_version=2),
    lambda doc: doc.update(schema_version=True),
    lambda doc: doc.update(revision=True),
    lambda doc: doc.update(project_id="prj_" + "b" * 32),
    lambda doc: doc.update(title=" untrimmed "),
    lambda doc: doc.update(created_at="invalid"),
    lambda doc: doc.update(extra="unknown"),
    lambda doc: doc.update(candidate_refs=["unsupported"]),
])
def test_malformed_stored_schema_fails_closed(service, change):
    document = create(service)
    path = path_for(service, document)
    change(document)
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    with pytest.raises(MediaIngestError) as error:
        service.projects.read(OWNER, path.stem)
    assert error.value.code == "internal"
    assert path.read_bytes() == raw


def test_serialized_project_has_actual_frozen_four_mib_limit(service):
    assert schema.MAX_PROJECT_BYTES == 4 * 1024 * 1024
    document = create(service)
    path = path_for(service, document)
    before = path.read_bytes()
    document["asset_refs"] = [
        {**REF, "asset_id": "ast_" + str(index).zfill(6) + "a" * 118}
        for index in range(20000)
    ]
    assert len(json.dumps(document).encode()) > schema.MAX_PROJECT_BYTES
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "invalid_request"
    assert path.read_bytes() == before
    raw = b" " * (schema.MAX_PROJECT_BYTES + 1)
    path.write_bytes(raw)
    with pytest.raises(MediaIngestError) as error:
        service.projects.read(OWNER, document["project_id"])
    assert error.value.code == "internal"
    assert path.read_bytes() == raw


def test_reference_count_is_not_an_unfrozen_clip_limit(service, monkeypatch):
    document = create(service)
    document["asset_refs"] = [{**REF, "asset_id": "ast_" + str(i)} for i in range(64)]
    refs = {ref["asset_id"]: ref for ref in document["asset_refs"]}
    monkeypatch.setattr(service, "asset", lambda owner, identity: ready_asset(refs[identity]))
    assert len(save(service, document)["asset_refs"]) == 64


@pytest.mark.parametrize("fault", ["mkstemp", "write", "fsync", "replace"])
def test_failed_write_retains_prior_snapshot_and_unknown_neighbors(service, monkeypatch, fault):
    document = create(service)
    path = path_for(service, document)
    before = path.read_bytes()
    unknown = service.projects.root / ".project-unknown.tmp"
    unknown.write_bytes(b"retain unknown bytes")

    def fail(*args, **kwargs):
        raise OSError("synthetic private storage failure")

    if fault == "mkstemp":
        monkeypatch.setattr(store.tempfile, "mkstemp", fail)
    elif fault == "write":
        fdopen = store.os.fdopen

        class BrokenWriter:
            def __init__(self, *args, **kwargs):
                self.handle = fdopen(*args, **kwargs)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.handle.close()

            def fileno(self):
                return self.handle.fileno()

            def write(self, raw):
                self.handle.write(raw[:10])
                fail()

        monkeypatch.setattr(store.os, "fdopen", lambda fd, mode: BrokenWriter(fd, mode) if mode == "wb" else fdopen(fd, mode))
    else:
        monkeypatch.setattr(store.os, fault, fail)
    document["title"] = "Uncommitted"
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "disk_space"
    assert "private" not in str(error.value)
    assert path.read_bytes() == before
    assert list(service.projects.root.glob(".project-*.tmp")) == [unknown]
    assert unknown.read_bytes() == b"retain unknown bytes"


def test_failed_cleanup_reports_pending_and_never_deletes_unknown_file(service, monkeypatch):
    document = create(service)
    before = path_for(service, document).read_bytes()
    unknown = service.projects.root / "retain.tmp"
    unknown.write_bytes(b"unknown")
    unlink = Path.unlink

    def fail_replace(*args):
        raise OSError("synthetic storage failure")

    def fail_cleanup(path, *args, **kwargs):
        if path.parent == service.projects.root and path.name.startswith(".project-"):
            raise OSError("synthetic cleanup failure")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(store.os, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "cleanup_pending"
    assert path_for(service, document).read_bytes() == before
    assert unknown.read_bytes() == b"unknown"
    assert len(list(service.projects.root.glob(".project-*.tmp"))) == 1


def test_publication_flushes_before_atomic_replace(service, monkeypatch):
    document = create(service)
    fsync, replace = store.os.fsync, store.os.replace
    events = []

    def sync(fd):
        events.append("fsync")
        return fsync(fd)

    def publish(source, destination):
        assert events == ["fsync"]
        assert json.loads(Path(source).read_bytes())["revision"] == 2
        assert json.loads(Path(destination).read_bytes())["revision"] == 1
        events.append("replace")
        return replace(source, destination)

    monkeypatch.setattr(store.os, "fsync", sync)
    monkeypatch.setattr(store.os, "replace", publish)
    assert save(service, document)["revision"] == 2
    assert events[:2] == ["fsync", "replace"]


def test_postpublication_directory_sync_failure_requires_reload_of_committed_revision(service, monkeypatch):
    document = create(service)

    def failed_sync():
        raise OSError("synthetic private directory sync failure")

    monkeypatch.setattr(service.projects, "_sync_directory", failed_sync)
    document["title"] = "Committed rename"
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert (error.value.code, error.value.stage, error.value.retryable) == ("conflict", "publish", False)
    assert "private" not in str(error.value)
    restored = service.projects.read(OWNER, document["project_id"])
    assert restored["revision"] == 2
    assert restored["title"] == "Committed rename"
    assert not list(service.projects.root.glob(".project-*.tmp"))
    with pytest.raises(MediaIngestError) as stale:
        save(service, document)
    assert (stale.value.code, stale.value.stage) == ("conflict", "save")


def test_unknown_tempfiles_survive_restart(service):
    document = create(service)
    unknown = service.projects.root / ".project-unclaimed.tmp"
    unknown.write_bytes(b"uncommitted synthetic bytes")
    service.close()
    reopened = AssetService(service.media.root, service.gallery, service.videos)
    try:
        assert reopened.projects.read(OWNER, document["project_id"]) == document
        assert unknown.read_bytes() == b"uncommitted synthetic bytes"
    finally:
        reopened.close()


def test_concurrent_saves_publish_exactly_one_new_revision(service):
    document = create(service)
    gate = threading.Barrier(2)

    def attempt(title):
        draft = deepcopy(document)
        draft["title"] = title
        gate.wait(timeout=5)
        try:
            return save(service, draft)
        except MediaIngestError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ["First synthetic draft", "Second synthetic draft"]))
    successes = [result for result in results if isinstance(result, dict)]
    failures = [result for result in results if isinstance(result, MediaIngestError)]
    assert len(successes) == len(failures) == 1
    assert failures[0].code == "conflict"
    assert successes[0]["revision"] == 2
    assert service.projects.read(OWNER, document["project_id"]) == successes[0]


def test_read_is_serialized_against_publication(service, monkeypatch):
    document = create(service)
    entered, release = threading.Event(), threading.Event()
    replace = store.os.replace

    def pause(source, destination):
        entered.set()
        assert release.wait(5)
        return replace(source, destination)

    monkeypatch.setattr(store.os, "replace", pause)
    with ThreadPoolExecutor(max_workers=2) as executor:
        saving = executor.submit(save, service, document)
        assert entered.wait(5)
        reading = executor.submit(service.projects.read, OWNER, document["project_id"])
        try:
            assert not reading.done()
        finally:
            release.set()
        assert reading.result(timeout=5) == saving.result(timeout=5)


def test_close_waits_for_read_to_release_runtime_ownership(service, monkeypatch):
    document = create(service)
    entered, release = threading.Event(), threading.Event()
    read = service.projects._read

    def pause(path):
        entered.set()
        assert release.wait(5)
        assert service.runtime._handle is not None
        return read(path)

    monkeypatch.setattr(service.projects, "_read", pause)
    with ThreadPoolExecutor(max_workers=2) as executor:
        reading = executor.submit(service.projects.read, OWNER, document["project_id"])
        assert entered.wait(5)
        closing = executor.submit(service.close)
        try:
            assert not closing.done()
        finally:
            release.set()
        assert reading.result(timeout=5) == document
        closing.result(timeout=5)
    with pytest.raises(MediaIngestError) as error:
        service.projects.read(OWNER, document["project_id"])
    assert error.value.code == "conflict"


def test_second_service_cannot_acquire_live_store(service):
    document = create(service)
    second = AssetService(service.media.root, service.gallery, service.videos)
    try:
        with pytest.raises(MediaIngestError) as error:
            second.projects.read(OWNER, document["project_id"])
        assert (error.value.code, error.value.stage) == ("conflict", "runtime")
    finally:
        second.close()


@pytest.mark.parametrize("target", ["directory", "file"])
def test_reparse_storage_is_rejected_before_read_or_write(service, monkeypatch, target):
    document = create(service)
    path = path_for(service, document)
    before = path.read_bytes()
    guarded = service.projects.root if target == "directory" else path
    lstat = Path.lstat

    def reparse(candidate):
        info = lstat(candidate)
        if candidate == guarded:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info

    monkeypatch.setattr(Path, "lstat", reparse)
    for operation in ("read", "save"):
        with pytest.raises(MediaIngestError) as error:
            if operation == "read":
                service.projects.read(OWNER, document["project_id"])
            else:
                save(service, document)
        assert error.value.code == "internal"
    assert path.read_bytes() == before


def test_hardlinked_snapshot_fails_closed(service, tmp_path):
    document = create(service)
    path = path_for(service, document)
    outside = tmp_path / "retained-synthetic.json"
    try:
        os.link(path, outside)
    except OSError:
        pytest.skip("Hard links unavailable in this temporary filesystem")
    before = outside.read_bytes()
    with pytest.raises(MediaIngestError) as error:
        service.projects.read(OWNER, document["project_id"])
    assert error.value.code == "internal"
    assert outside.read_bytes() == before


def test_temporary_replacement_is_not_deleted_as_issued_file(service, monkeypatch):
    document = create(service)
    before = path_for(service, document).read_bytes()
    fsync = store.os.fsync
    retained = service.projects.root / "retain-original-issued.tmp"
    replacement = []

    def replace_issued(fd):
        fsync(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            pending = next(service.projects.root.glob(".project-*.tmp"))
            # Windows disallows renaming an open fd; substitution is injected
            # immediately before the final issued-file identity check instead.
            replacement.append(pending)

    check = service.projects._assert_issued

    def swap(path, issued):
        if replacement:
            replacement.clear()
            path.rename(retained)
            path.write_bytes(b"unknown replacement")
        return check(path, issued)

    monkeypatch.setattr(store.os, "fsync", replace_issued)
    monkeypatch.setattr(service.projects, "_assert_issued", swap)
    with pytest.raises(MediaIngestError) as error:
        save(service, document)
    assert error.value.code == "cleanup_pending"
    assert path_for(service, document).read_bytes() == before
    unknown = next(service.projects.root.glob(".project-*.tmp"))
    assert unknown.read_bytes() == b"unknown replacement"
    assert retained.exists()
