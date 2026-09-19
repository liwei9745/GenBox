"""Bounded MP4 data-reference preflight; FFmpeg remains the media validator."""

import os
import struct
import time

from .worker import check_cancelled


class MP4ReferenceError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def check_self_contained_mp4(path, *, timeout):
    deadline = time.monotonic() + timeout
    containers = (b"moov", b"trak", b"mdia", b"minf", b"dinf")

    def tick():
        check_cancelled()
        if time.monotonic() >= deadline:
            raise MP4ReferenceError("probe_timeout")

    with path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size

        def read_at(offset, length):
            tick()
            stream.seek(offset)
            raw = stream.read(length)
            if len(raw) != length:
                raise MP4ReferenceError("media_corrupt")
            return raw

        def boxes(start, end):
            while start < end:
                tick()
                if end - start < 8:
                    raise MP4ReferenceError("media_corrupt")
                length, kind = struct.unpack(">I4s", read_at(start, 8))
                header = 8
                if length == 1:
                    if end - start < 16:
                        raise MP4ReferenceError("media_corrupt")
                    length = struct.unpack(">Q", read_at(start + 8, 8))[0]
                    header = 16
                elif length == 0:
                    length = end - start
                if length < header or length > end - start:
                    raise MP4ReferenceError("media_corrupt")
                yield kind, start + header, start + length
                start += length

        def references(start, end):
            if end - start < 8:
                raise MP4ReferenceError("media_corrupt")
            version_flags, count = struct.unpack(">II", read_at(start, 8))
            if version_flags != 0 or not count or count > (end - start - 8) // 12:
                raise MP4ReferenceError("media_corrupt")
            observed = 0
            for kind, body, finish in boxes(start + 8, end):
                observed += 1
                # Only a self-contained URL entry with no location payload is
                # acceptable. Aliases, URNs and unknown entries fail closed.
                if kind != b"url " or finish - body != 4 or read_at(body, 4) != b"\x00\x00\x00\x01":
                    raise MP4ReferenceError("unsupported_media")
            if observed != count:
                raise MP4ReferenceError("media_corrupt")

        def walk(start, end, depth):
            for kind, body, finish in boxes(start, end):
                if kind == b"cmov":
                    # Compressed movie metadata cannot bypass this preflight.
                    raise MP4ReferenceError("unsupported_media")
                if kind in containers:
                    if depth >= len(containers) or kind != containers[depth]:
                        raise MP4ReferenceError("media_corrupt")
                    walk(body, finish, depth + 1)
                elif kind == b"dref":
                    if depth != len(containers):
                        raise MP4ReferenceError("media_corrupt")
                    references(body, finish)

        # Seek past media payloads. Never read the movie or mdat into memory.
        walk(0, size, 0)
