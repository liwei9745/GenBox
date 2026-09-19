"""Real short synthetic media around the frozen admission boundaries."""

import struct

import pytest

from video_workbench.media import MediaIngestError, MediaIngestManager, MediaLimits
from video_workbench.media.worker import run_media
from test_video_workbench_api import FIXTURES


@pytest.fixture
def manager(tmp_path):
    service = MediaIngestManager(tmp_path / "store")
    yield service
    for staged in list(service._issued.values()):
        service.cleanup_staged(staged)


def generate(tmp_path, arguments, name):
    target = tmp_path / name
    result = run_media(
        ["ffmpeg", "-v", "error", "-nostdin", "-n", *arguments, str(target)],
        cwd=tmp_path, timeout=10,
    )
    assert result.returncode == 0, "synthetic fixture generation failed"
    return target.read_bytes()


@pytest.mark.parametrize("width,height,accepted", [
    (4096, 4096, True), (4097, 32, False), (32, 4097, False),
])
def test_real_png_dimension_boundary(manager, tmp_path, width, height, accepted):
    payload = generate(tmp_path, [
        "-f", "lavfi", "-i", f"color=c=red:s={width}x{height},format=rgb24",
        "-frames:v", "1", "-c:v", "png", "-threads", "1",
    ], "boundary.png")
    staged = manager.stage_stream("png_boundary", "boundary.png", payload)
    if accepted:
        asset = manager.publish(staged, manager.probe(staged))
        assert (asset.metadata.width, asset.metadata.height) == (width, height)
        assert asset.storage_path.read_bytes() == payload
    else:
        with pytest.raises(MediaIngestError) as error:
            manager.probe(staged)
        assert error.value.code == "dimension_limit"
        assert not manager.assets_root.exists()


@pytest.mark.parametrize("width,height,accepted", [
    (1920, 1080, True), (1922, 1080, False), (1920, 1082, False),
])
def test_real_h264_dimension_boundary(manager, tmp_path, width, height, accepted):
    payload = generate(tmp_path, [
        "-f", "lavfi", "-i", f"color=c=blue:s={width}x{height}:r=30",
        "-frames:v", "2", "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-threads", "1",
    ], "boundary.mp4")
    staged = manager.stage_stream("video_boundary", "boundary.mp4", payload)
    if accepted:
        asset = manager.publish(staged, manager.probe(staged))
        assert (asset.metadata.width, asset.metadata.height) == (width, height)
        assert asset.storage_path.read_bytes() == payload
    else:
        with pytest.raises(MediaIngestError) as error:
            manager.probe(staged)
        assert error.value.code == "dimension_limit"
        assert not manager.assets_root.exists()


@pytest.mark.parametrize("channels,rate,accepted", [
    (2, 96000, True), (3, 48000, False), (2, 96001, False),
])
def test_real_pcm_audio_limits(manager, tmp_path, channels, rate, accepted):
    layout = "stereo" if channels == 2 else "2.1"
    payload = generate(tmp_path, [
        "-f", "lavfi", "-i", f"anullsrc=r={rate}:cl={layout}",
        "-t", "0.05", "-c:a", "pcm_s16le", "-threads", "1",
    ], "boundary.wav")
    staged = manager.stage_stream("audio_boundary", "boundary.wav", payload)
    if accepted:
        asset = manager.publish(staged, manager.probe(staged))
        assert asset.metadata.channels == channels
        assert asset.metadata.sample_rate_hz == rate
        assert asset.storage_path.read_bytes() == payload
    else:
        with pytest.raises(MediaIngestError) as error:
            manager.probe(staged)
        assert error.value.code == "unsupported_media"
        assert not manager.assets_root.exists()


@pytest.mark.parametrize("variant", ["two_video", "subtitle", "wrong_codec"])
def test_real_disallowed_container_streams(manager, tmp_path, variant):
    arguments = ["-i", str((FIXTURES / "cfr-h264.mp4").resolve())]
    if variant == "two_video":
        arguments += ["-map", "0:v:0", "-map", "0:v:0", "-c", "copy"]
    elif variant == "subtitle":
        subtitle = tmp_path / "synthetic.srt"
        subtitle.write_text("1\n00:00:00,000 --> 00:00:00,500\nSynthetic\n", encoding="ascii")
        arguments += ["-i", str(subtitle), "-map", "0:v:0", "-map", "1:s:0", "-c:v", "copy", "-c:s", "mov_text"]
    else:
        arguments += ["-c:v", "mpeg4", "-threads", "1", "-an"]
    payload = generate(tmp_path, arguments, "unsupported.mp4")
    staged = manager.stage_stream("container", "unsupported.mp4", payload)
    with pytest.raises(MediaIngestError) as error:
        manager.probe(staged)
    assert error.value.code == "unsupported_media"
    assert not manager.assets_root.exists()


def test_real_mp4_external_data_reference_rejected(manager, tmp_path, monkeypatch):
    payload = generate(tmp_path, [
        "-i", str((FIXTURES / "cfr-h264.mp4").resolve()), "-c", "copy",
    ], "self-contained.mp4")
    replacements = []

    def rewrite(data):
        output = bytearray()
        offset = 0
        while offset < len(data):
            length, kind = struct.unpack_from(">I4s", data, offset)
            assert 8 <= length <= len(data) - offset
            body = data[offset + 8:offset + length]
            if kind in {b"moov", b"trak", b"mdia", b"minf", b"dinf"}:
                body = rewrite(body)
            elif kind == b"dref":
                url = b"\x00\x00\x00\x00https://example.invalid/synthetic.mp4\x00"
                body = b"\x00\x00\x00\x00" + struct.pack(">I", 1) + struct.pack(">I4s", 8 + len(url), b"url ") + url
                replacements.append(True)
            output += struct.pack(">I4s", 8 + len(body), kind) + body
            offset += length
        return bytes(output)

    # The default muxer places moov after mdat, so data offsets stay valid.
    assert payload.index(b"mdat") < payload.index(b"moov")
    hostile = rewrite(payload)
    assert replacements
    staged = manager.stage_stream("external_ref", "external.mp4", hostile)
    from video_workbench.media import ingest
    monkeypatch.setattr(ingest, "run_media", lambda *a, **kw: pytest.fail("external reference reached native worker"))
    with pytest.raises(MediaIngestError) as error:
        manager.probe(staged)
    assert error.value.code in {"media_corrupt", "unsupported_media"}
    assert not manager.assets_root.exists()


def test_exact_and_one_byte_over_admission_with_lowered_test_limit(tmp_path):
    payload = (FIXTURES / "still.png").read_bytes()
    for limit, accepted in ((len(payload), True), (len(payload) - 1, False)):
        manager = MediaIngestManager(
            tmp_path / str(limit), limits=MediaLimits(max_still_bytes=limit),
        )
        if accepted:
            staged = manager.stage_stream("exact", "still.png", payload)
            assert staged.byte_length == limit
            manager.cleanup_staged(staged)
        else:
            with pytest.raises(MediaIngestError) as error:
                manager.stage_stream("over", "still.png", payload)
            assert error.value.code == "asset_too_large"
            assert not list(manager.staging_root.rglob(".upload-*"))
        assert not manager._issued


def test_preflight_timeout_is_safe_and_retryable(manager, monkeypatch):
    from video_workbench.media import ingest
    from video_workbench.media.mp4_refs import MP4ReferenceError

    staged = manager.stage_stream("timeout", "synthetic.mp4", (FIXTURES / "cfr-h264.mp4").read_bytes())

    def timeout(*args, **kwargs):
        raise MP4ReferenceError("probe_timeout")

    monkeypatch.setattr(ingest, "check_self_contained_mp4", timeout)
    with pytest.raises(MediaIngestError) as error:
        manager.probe(staged)
    assert error.value.code == "probe_timeout"
    assert error.value.retryable is True
