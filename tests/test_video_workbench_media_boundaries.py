"""Adversarial local fixtures; no real media, credentials or provider traffic."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from video_workbench.media import MediaIngestError, MediaIngestManager, MediaLimits
from video_workbench.media import ingest, worker


FIXTURES = Path(__file__).parent / "fixtures" / "video_workbench"


@pytest.fixture
def manager(tmp_path):
    instance = MediaIngestManager(tmp_path / "workbench")
    yield instance
    for staged in list(instance._issued.values()):
        instance.cleanup_staged(staged)


def stage(manager, job="job_test", fixture="cfr-h264.mp4", name="clip.mp4"):
    return manager.stage_stream(job, name, (FIXTURES / fixture).read_bytes())


@pytest.mark.parametrize("value", [True, 1.2, "10", 0, -1])
def test_limits_require_positive_integers(value):
    with pytest.raises(ValueError):
        MediaLimits(max_request_files=value)


@pytest.mark.parametrize("value", [True, float("inf"), float("nan"), 0, -1, 11])
def test_deadline_is_finite_and_bounded(value):
    with pytest.raises(ValueError):
        MediaLimits(probe_timeout_seconds=value)


def test_batch_total_failure_cleans_last_file_and_releases_reservation(tmp_path):
    manager = MediaIngestManager(tmp_path / "workbench", limits=MediaLimits(max_request_bytes=64))
    with pytest.raises(MediaIngestError):
        manager.stage_batch("job_total", [("a.mp4", b"a" * 40), ("b.mp4", b"b" * 30)])
    assert not list(manager.staging_root.rglob(".upload-*"))
    assert not any(token is manager._reservation_token for token, _ in ingest._RESERVATIONS)


def test_interrupted_iterator_cleans_owned_files(manager):
    def interrupted():
        yield ("a.mp4", b"abc")
        raise RuntimeError("synthetic interruption")
    with pytest.raises(RuntimeError):
        manager.stage_batch("job_interrupted", interrupted())
    assert not manager._issued
    assert not list(manager.staging_root.rglob(".upload-*"))


def test_forged_stage_cannot_delete_or_probe_another_file(manager):
    staged = stage(manager)
    forged = replace(staged, job_id="job_other")
    for operation in (manager.cleanup_staged, manager.probe):
        with pytest.raises(MediaIngestError) as error:
            operation(forged)
        assert error.value.code == "invalid_request"
    assert staged.path.is_file()


def test_changed_bytes_rejected_before_publication(manager):
    staged = stage(manager)
    metadata = manager.probe(staged)
    staged.path.write_bytes(b"changed")
    with pytest.raises(MediaIngestError) as error:
        manager.publish(staged, metadata)
    assert error.value.code == "media_corrupt"
    assert not manager.assets_root.exists()


def test_unverified_metadata_is_not_publishable(manager):
    staged = stage(manager)
    metadata = manager.probe(staged)
    with pytest.raises(MediaIngestError) as error:
        manager.publish(staged, replace(metadata, width=1))
    assert error.value.code == "invalid_request"
    assert not manager.assets_root.exists()


def test_same_origin_upload_deduplicates(manager):
    first = manager.import_content("job_one", "one.mp4", (FIXTURES / "cfr-h264.mp4").read_bytes())
    second = manager.import_content("job_two", "two.mp4", (FIXTURES / "cfr-h264.mp4").read_bytes())
    assert first.asset_id == second.asset_id


def test_renamed_playlist_is_rejected_without_network(manager):
    staged = stage(manager, fixture="playlist.m3u8", name="pretend.mp4")
    with pytest.raises(MediaIngestError) as error:
        manager.probe(staged)
    assert error.value.code == "media_corrupt"
    command = manager._probe_command(staged)
    assert command[command.index("-protocol_whitelist") + 1] == "file"
    assert command[command.index("-format_whitelist") + 1] == "mov"
    assert command[command.index("-enable_drefs") + 1] == "0"


def test_truncated_still_cannot_pass_header_probe(manager):
    payload = (FIXTURES / "still.png").read_bytes()[:50]
    staged = manager.stage_stream("job_truncated", "still.png", payload)
    with pytest.raises(MediaIngestError) as error:
        manager.probe(staged)
    assert error.value.code == "media_corrupt"


def test_duration_is_not_limited_to_project_duration(manager):
    staged = stage(manager)
    payload = {
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "180"},
        "streams": [{
            "codec_type": "video", "codec_name": "h264", "width": 640,
            "height": 360, "time_base": "1/15360", "duration": "180",
        }],
    }
    assert manager._validate_probe(staged, payload).duration_us == 180_000_000
    payload["streams"][0]["width"] = -1
    with pytest.raises(MediaIngestError):
        manager._validate_probe(staged, payload)


def test_actual_container_not_suffix_must_match(manager):
    staged = stage(manager)
    payload = {
        "format": {"format_name": "mpegts", "duration": "2"},
        "streams": [{
            "codec_type": "video", "codec_name": "h264", "width": 640,
            "height": 360, "time_base": "1/15360", "duration": "2",
        }],
    }
    with pytest.raises(MediaIngestError):
        manager._validate_probe(staged, payload)


def test_thumbnail_timeout_cleans_temporary_file(manager, monkeypatch):
    asset = manager.import_content("job_thumb", "clip.mp4", (FIXTURES / "cfr-h264.mp4").read_bytes())
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("synthetic", 1)
    monkeypatch.setattr(ingest, "run_media", timeout)
    with pytest.raises(MediaIngestError) as error:
        manager.derive_thumbnail(asset)
    assert error.value.code == "probe_timeout"
    assert not list(manager.assets_root.rglob(".thumbnail-*"))
    assert asset.storage_path.is_file()


def test_disk_reservation_before_staging(tmp_path, monkeypatch):
    manager = MediaIngestManager(tmp_path / "workbench")
    monkeypatch.setattr(ingest.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    with pytest.raises(MediaIngestError) as error:
        stage(manager)
    assert error.value.code == "disk_space"
    assert not list(manager.staging_root.rglob(".upload-*"))


def test_only_two_import_jobs_admitted(manager):
    stage(manager, "job_one")
    stage(manager, "job_two")
    with pytest.raises(MediaIngestError) as error:
        stage(manager, "job_three")
    assert error.value.code == "conflict"


def test_worker_bounds_output_and_releases_slot(tmp_path):
    with pytest.raises(worker.WorkerLimitError):
        worker.run_media(
            [sys.executable, "-c", "print('x' * 200000)"],
            cwd=tmp_path, timeout=5,
        )
    result = worker.run_media([sys.executable, "-c", "print('ok')"], cwd=tmp_path, timeout=5)
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"


def test_worker_timeout_terminates_owned_process(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        worker.run_media(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=tmp_path, timeout=0.2,
        )


def test_reparse_attribute_rejected_before_creation(manager, monkeypatch):
    original = Path.lstat
    malicious = manager.root / "staging"
    def lstat(path, *args, **kwargs):
        if path == malicious:
            return SimpleNamespace(st_mode=0o40755, st_file_attributes=0x400)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(MediaIngestError):
        stage(manager)
    assert not manager._issued


def test_symlink_root_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("host cannot create symlinks; reparse guard tested separately")
    with pytest.raises(MediaIngestError):
        MediaIngestManager(alias)
    assert not list(target.iterdir())


def test_copy_mutation_does_not_publish_partial_record(manager, monkeypatch):
    staged = stage(manager)
    metadata = manager.probe(staged)
    monkeypatch.setattr(ingest.shutil, "copyfileobj", lambda source, target, **kw: target.write(b"changed"))
    with pytest.raises(MediaIngestError) as error:
        manager.publish(staged, metadata)
    assert error.value.code == "media_corrupt"
    assert not list(manager.assets_root.iterdir())
    assert not list(staged.path.parent.glob(".publish-*"))
