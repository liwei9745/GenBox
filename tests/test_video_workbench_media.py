"""Focused W1-2 media admission/probe tests using synthetic fixtures only."""

from __future__ import annotations

import io
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from video_workbench.media import MediaIngestError, MediaIngestManager, MediaLimits


FIXTURES = Path(__file__).parent / "fixtures" / "video_workbench"


def _manager(tmp_path: Path, **kwargs) -> MediaIngestManager:
    return MediaIngestManager(tmp_path / "video-workbench", **kwargs)


@pytest.mark.parametrize(
    ("filename", "fixture_name", "kind"),
    [
        ("clip.mp4", "cfr-h264.mp4", "video"),
        ("clip.webm", "cfr-vp9.webm", "video"),
        ("clip-audio.mp4", "av-aac.mp4", "video"),
        ("voice.wav", "audio-pcm.wav", "audio"),
        ("voice.mp3", "audio-mp3.mp3", "audio"),
        ("still.png", "still.png", "image"),
        ("still.jpg", "thumbnail.jpg", "image"),
        ("still.webp", "still.webp", "image"),
    ],
)
def test_import_stages_hashes_probes_and_publishes(
    tmp_path: Path,
    filename: str,
    fixture_name: str,
    kind: str,
) -> None:
    source = FIXTURES / fixture_name
    original = source.read_bytes()
    manager = _manager(tmp_path)

    record = manager.import_content("job-smoke", filename, io.BytesIO(original))

    assert record.kind == kind
    assert record.state == "ready"
    assert record.content_sha256 == hashlib.sha256(original).hexdigest()
    assert record.storage_path is not None
    assert record.storage_path.read_bytes() == original
    assert record.as_view()["content_sha256"].startswith("sha256:")
    assert str(record.storage_path) not in str(record.as_view())
    assert not list(manager.staging_root.rglob("*")) if manager.staging_root.exists() else True


def test_duplicate_content_reuses_verified_asset_without_merging_provenance(tmp_path: Path) -> None:
    source = (FIXTURES / "cfr-h264.mp4").read_bytes()
    manager = _manager(tmp_path)

    first = manager.import_content("job-first", "first.mp4", source, origin="upload")
    second = manager.import_content("job-second", "second.mp4", source, origin="library")

    assert second.asset_id == first.asset_id
    assert second.origin == first.origin
    assert len(list((manager.assets_root).glob("*/asset.json"))) == 1


def test_duplicate_lookup_rejects_tampered_published_bytes(tmp_path: Path) -> None:
    source = (FIXTURES / "cfr-h264.mp4").read_bytes()
    manager = _manager(tmp_path)
    record = manager.import_content("job-tamper", "clip.mp4", source)
    assert record.storage_path is not None
    record.storage_path.write_bytes(b"tampered")

    assert manager.find_by_digest(record.content_sha256) is None
    manifests = list(manager.assets_root.glob("*/asset.json"))
    assert len(manifests) == 1
    assert json.loads(manifests[0].read_text(encoding="utf-8"))["content_sha256"] == record.content_sha256


@pytest.mark.parametrize(
    ("filename", "fixture_name", "code", "stage"),
    [
        ("broken.mp4", "corrupt.mp4", "media_corrupt", "probe"),
        ("playlist.m3u8", "playlist.m3u8", "unsupported_media", "admission"),
        ("archive.zip", "corrupt.mp4", "unsupported_media", "admission"),
        ("unknown.bin", "corrupt.mp4", "unsupported_media", "admission"),
    ],
)
def test_rejected_media_has_bounded_error_and_no_published_asset(
    tmp_path: Path,
    filename: str,
    fixture_name: str,
    code: str,
    stage: str,
) -> None:
    manager = _manager(tmp_path)

    with pytest.raises(MediaIngestError) as caught:
        manager.import_content("job-reject", filename, (FIXTURES / fixture_name).read_bytes())

    assert caught.value.code == code
    assert caught.value.stage == stage
    assert str(tmp_path) not in caught.value.problem.message
    assert not manager.assets_root.exists() or not list(manager.assets_root.iterdir())


def test_filename_and_path_inputs_are_rejected_before_staging(tmp_path: Path) -> None:
    manager = _manager(tmp_path)

    with pytest.raises(MediaIngestError) as caught:
        manager.stage_stream("job-invalid", "../clip.mp4", b"content")
    assert caught.value.code == "invalid_request"
    assert not manager.staging_root.exists() or not list(manager.staging_root.rglob("*"))

    with pytest.raises(MediaIngestError) as caught:
        manager.stage_stream("job-invalid", "clip.mp4", FIXTURES / "cfr-h264.mp4")
    assert caught.value.code == "invalid_request"


def test_admission_limits_are_enforced_before_probe(tmp_path: Path) -> None:
    manager = _manager(
        tmp_path,
        limits=MediaLimits(
            max_video_audio_bytes=32,
            max_request_bytes=64,
        ),
    )

    with pytest.raises(MediaIngestError) as caught:
        manager.import_content("job-large", "clip.mp4", b"x" * 33)
    assert caught.value.code == "asset_too_large"
    assert caught.value.stage == "admission"


def test_batch_count_and_total_limits_are_bounded(tmp_path: Path) -> None:
    manager = _manager(
        tmp_path,
        limits=MediaLimits(
            max_video_audio_bytes=128,
            max_request_bytes=64,
            max_request_files=2,
        ),
    )

    with pytest.raises(MediaIngestError) as caught:
        manager.stage_batch(
            "job-batch",
            [("one.mp4", b"a" * 40), ("two.mp4", b"b" * 30)],
        )
    assert caught.value.code == "asset_too_large"
    assert caught.value.stage == "admission"

    with pytest.raises(MediaIngestError) as caught:
        manager.stage_batch(
            "job-count",
            [("one.mp4", b"a"), ("two.mp4", b"b"), ("three.mp4", b"c")],
        )
    assert caught.value.code == "invalid_request"


def test_missing_probe_dependency_is_actionable(tmp_path: Path) -> None:
    manager = _manager(tmp_path, ffprobe="definitely-not-an-installed-ffprobe")
    staged = manager.stage_stream("job-dependency", "clip.mp4", b"content")

    with pytest.raises(MediaIngestError) as caught:
        manager.probe(staged)
    assert caught.value.code == "dependency_missing"
    assert caught.value.stage == "probe"
    manager.cleanup_staged(staged)


def test_probe_timeout_is_retryable_and_does_not_leak_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    staged = manager.stage_stream("job-timeout", "clip.mp4", b"content")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["ffprobe"], timeout=0.01)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(MediaIngestError) as caught:
        manager.probe(staged)
    assert caught.value.code == "probe_timeout"
    assert caught.value.retryable is True
    assert "ffprobe" not in caught.value.problem.message
    manager.cleanup_staged(staged)
