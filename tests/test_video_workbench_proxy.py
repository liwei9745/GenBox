"""Preview fidelity and cache safety with synthetic local fixtures."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from video_workbench.media import MediaIngestError, MediaIngestManager
from video_workbench.media.proxy import ProxyRenderer
from video_workbench.media.worker import run_media


FIXTURES = Path(__file__).parent / "fixtures" / "video_workbench"


@pytest.mark.parametrize("fixture", ["cfr-h264.mp4", "cfr-vp9.webm", "av-aac.mp4", "vfr-h264.mp4"])
def test_proxy_preserves_source_and_reuses_verified_cache(tmp_path, fixture):
    manager = MediaIngestManager(tmp_path / "store")
    payload = (FIXTURES / fixture).read_bytes()
    asset = manager.import_content("import", fixture, payload)
    renderer = ProxyRenderer(manager)
    with renderer.reservation():
        pending, manifest = renderer.allocate()
        proxy = renderer.render(asset, pending, manifest)
    assert asset.storage_path.read_bytes() == payload
    assert proxy.path.is_file()
    assert not pending.exists() and not manifest.exists()
    assert renderer.existing(asset) == proxy
    mapping = json.loads(proxy.path.with_suffix(".json").read_text())["mapping"]
    assert mapping["rate_num"] == mapping["rate_den"] == 1


def test_partial_cache_not_served_or_replaced(tmp_path):
    manager = MediaIngestManager(tmp_path / "store")
    asset = manager.import_content("import", "test.mp4", (FIXTURES / "cfr-h264.mp4").read_bytes())
    renderer = ProxyRenderer(manager)
    directory, target, _ = renderer._paths(asset)
    manager._ensure_directory(directory)
    target.write_bytes(b"partial")
    with pytest.raises(MediaIngestError) as error:
        renderer.existing(asset)
    assert error.value.code == "invalid_result"
    assert target.read_bytes() == b"partial"


def test_proxy_rejects_forged_private_source_path(tmp_path, monkeypatch):
    manager = MediaIngestManager(tmp_path / "store")
    asset = manager.import_content("import", "test.mp4", (FIXTURES / "cfr-h264.mp4").read_bytes())
    renderer = ProxyRenderer(manager)
    unrelated = tmp_path / "unrelated.mp4"
    unrelated.write_bytes(b"must not read or modify")
    monkeypatch.setattr(renderer, "_run", lambda *a, **kw: pytest.fail("untrusted path reached worker"))
    with pytest.raises(MediaIngestError) as error:
        renderer.render(replace(asset, storage_path=unrelated), *renderer.allocate())
    assert error.value.code == "conflict"
    assert unrelated.read_bytes() == b"must not read or modify"


def test_proxy_reservation_is_exclusive_and_released(tmp_path):
    renderer = ProxyRenderer(MediaIngestManager(tmp_path / "store"))
    with renderer.reservation():
        with pytest.raises(MediaIngestError) as error:
            with renderer.reservation():
                pytest.fail("second render admitted")
        assert error.value.code == "conflict"
    with renderer.reservation():
        pass


def frame_times(manager, path, suffix=".mp4"):
    result = run_media([
        manager.ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "frame=best_effort_timestamp_time", "-of", "json",
        *manager._input_options(suffix), str(path),
    ], cwd=path.parent, timeout=10)
    assert result.returncode == 0
    return [round(float(item["best_effort_timestamp_time"]) * 1_000_000)
            for item in json.loads(result.stdout)["frames"]]


def test_vfr_frame_intervals_preserved(tmp_path):
    manager = MediaIngestManager(tmp_path / "store")
    asset = manager.import_content("import", "vfr.mp4", (FIXTURES / "vfr-h264.mp4").read_bytes())
    renderer = ProxyRenderer(manager)
    with renderer.reservation():
        proxy = renderer.render(asset, *renderer.allocate())
    source = frame_times(manager, asset.storage_path)
    preview = frame_times(manager, proxy.path)
    assert len(set(b - a for a, b in zip(source, source[1:]))) > 1
    assert len(source) == len(preview)
    assert max(abs((a - source[0]) - (b - preview[0])) for a, b in zip(source, preview)) <= 100


@pytest.mark.parametrize("variant", ["offset", "rotation", "sar", "audio_delay"])
def test_normalization_preserves_display_and_relative_timing(tmp_path, variant):
    manager = MediaIngestManager(tmp_path / "store")
    source = FIXTURES.resolve() / "av-aac.mp4"
    prepared = tmp_path / "synthetic.mp4"
    command = [manager.ffmpeg, "-v", "error", "-nostdin", "-y"]
    if variant == "rotation":
        command += ["-display_rotation:v:0", "90"]
    command += ["-i", str(source)]
    if variant == "audio_delay":
        command += ["-itsoffset", "0.25", "-i", str(source), "-map", "0:v:0", "-map", "1:a:0", "-c", "copy"]
    else:
        command += {
            "offset": ["-c", "copy", "-output_ts_offset", "5"],
            "rotation": ["-c", "copy"],
            "sar": ["-vf", "setsar=2", "-c:v", "libx264", "-threads", "1", "-c:a", "copy"],
        }[variant]
    result = run_media(command + [str(prepared)], cwd=tmp_path, timeout=10)
    assert result.returncode == 0
    asset = manager.import_content("import", "test.mp4", prepared.read_bytes())
    if variant == "rotation":
        assert abs(asset.metadata.rotation) == 90
    renderer = ProxyRenderer(manager)
    with renderer.reservation():
        proxy = renderer.render(asset, *renderer.allocate())
    origin, _, source_streams = renderer._timing(asset.storage_path, ".mp4")
    proxy_origin, _, output_streams = renderer._timing(proxy.path, ".mp4")
    source_video = next(s for s in source_streams if s["codec_type"] == "video")
    output_video = next(s for s in output_streams if s["codec_type"] == "video")
    assert abs(proxy_origin) <= 2000
    source_frames = frame_times(manager, asset.storage_path)
    output_frames = frame_times(manager, proxy.path)
    assert len(source_frames) == len(output_frames)
    assert max(abs((a - origin) - b) for a, b in zip(source_frames, output_frames)) <= 2000
    width, height = source_video["width"], source_video["height"]
    expected_ratio = height / width if variant == "rotation" else (2 if variant == "sar" else 1) * width / height
    assert abs(output_video["width"] / output_video["height"] - expected_ratio) < 0.02
