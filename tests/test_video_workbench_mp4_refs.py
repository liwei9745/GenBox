"""MP4 header preflight is bounded and does not interpret external locations."""

import struct
import threading
from pathlib import Path

import pytest

from video_workbench.media import MediaIngestError
from video_workbench.media import mp4_refs
from video_workbench.media.worker import execution_scope


def box(kind, body=b"", *, extended=False):
    if extended:
        return struct.pack(">I4sQ", 1, kind, len(body) + 16) + body
    return struct.pack(">I4s", len(body) + 8, kind) + body


def movie(entry, *, count=1, extended=False):
    content = box(b"dref", struct.pack(">II", 0, count) + entry, extended=extended)
    for kind in (b"dinf", b"minf", b"mdia", b"trak", b"moov"):
        content = box(kind, content, extended=extended)
    return content


@pytest.mark.parametrize("extended", [False, True])
def test_self_contained_entry_with_bounded_headers(tmp_path, extended):
    path = tmp_path / "synthetic.mp4"
    path.write_bytes(movie(box(b"url ", b"\x00\x00\x00\x01", extended=extended), extended=extended))
    mp4_refs.check_self_contained_mp4(path, timeout=10)


@pytest.mark.parametrize("kind,body", [
    (b"url ", b"\x00\x00\x00\x00https://example.invalid/synthetic\x00"),
    (b"url ", b"\x00\x00\x00\x00file:synthetic.mp4\x00"),
    (b"url ", b"\x00\x00\x00\x01extra"),
    (b"url ", b"\x01\x00\x00\x01"),
    (b"urn ", b"\x00\x00\x00\x01"),
    (b"alis", b"\x00\x00\x00\x01"),
])
def test_external_unknown_or_ambiguous_entries_fail_closed(tmp_path, kind, body):
    path = tmp_path / "synthetic.mp4"
    path.write_bytes(movie(box(kind, body)))
    with pytest.raises(mp4_refs.MP4ReferenceError) as error:
        mp4_refs.check_self_contained_mp4(path, timeout=10)
    assert error.value.code == "unsupported_media"
    assert "synthetic" not in str(error.value)


@pytest.mark.parametrize("payload", [
    b"short",
    struct.pack(">I4s", 7, b"moov"),
    struct.pack(">I4s", 1000, b"moov"),
    struct.pack(">I4s", 1, b"moov"),
    movie(box(b"url ", b"\x00\x00\x00\x01"), count=2),
    movie(b"", count=0),
    box(b"moov", box(b"moov")),
    box(b"dref", struct.pack(">II", 0, 1)),
])
def test_malformed_box_sizes_counts_and_hierarchy_rejected(tmp_path, payload):
    path = tmp_path / "synthetic.mp4"
    path.write_bytes(payload)
    with pytest.raises(mp4_refs.MP4ReferenceError) as error:
        mp4_refs.check_self_contained_mp4(path, timeout=10)
    assert error.value.code == "media_corrupt"


def test_compressed_movie_metadata_cannot_bypass_reference_check(tmp_path):
    path = tmp_path / "synthetic.mp4"
    path.write_bytes(box(b"moov", box(b"cmov", b"synthetic")))
    with pytest.raises(mp4_refs.MP4ReferenceError) as error:
        mp4_refs.check_self_contained_mp4(path, timeout=10)
    assert error.value.code == "unsupported_media"


def test_preflight_obeys_deadline(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.mp4"
    path.write_bytes(box(b"free"))
    ticks = iter((0, 11))
    monkeypatch.setattr(mp4_refs.time, "monotonic", lambda: next(ticks))
    with pytest.raises(mp4_refs.MP4ReferenceError) as error:
        mp4_refs.check_self_contained_mp4(path, timeout=10)
    assert error.value.code == "probe_timeout"


def test_preflight_remains_cancellable(tmp_path):
    path = tmp_path / "synthetic.mp4"
    path.write_bytes(box(b"free"))
    event = threading.Event()
    with execution_scope("synthetic", event):
        event.set()
        with pytest.raises(MediaIngestError) as error:
            mp4_refs.check_self_contained_mp4(path, timeout=10)
        assert error.value.code == "job_cancelled"


def test_media_payload_is_skipped_and_header_reads_are_bounded(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.mp4"
    path.write_bytes(
        box(b"mdat", b"x" * (2 * 1024 * 1024))
        + movie(box(b"url ", b"\x00\x00\x00\x01"))
        + struct.pack(">I4s", 0, b"free")
    )
    opened = Path.open
    reads = []

    class Observed:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def fileno(self):
            return self.handle.fileno()

        def seek(self, *args):
            return self.handle.seek(*args)

        def read(self, size):
            reads.append(size)
            return self.handle.read(size)

    monkeypatch.setattr(Path, "open", lambda self, *a, **kw: Observed(opened(self, *a, **kw)))
    mp4_refs.check_self_contained_mp4(path, timeout=10)
    assert max(reads) <= 8
    assert sum(reads) < 128
