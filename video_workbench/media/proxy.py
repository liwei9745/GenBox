"""Validated, immutable preview derivatives; originals remain export sources."""

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from . import ingest
from .ingest import _fail
from .models import DerivedMedia
from .errors import MediaIngestError
from .worker import WorkerLimitError, check_cancelled, run_media


def _time_us(value):
    try:
        if not isinstance(value, str) or len(value) > 64:
            raise ValueError
        number = Decimal(value) * 1_000_000
        if not number.is_finite() or abs(number) > 2**63 - 1:
            raise ValueError
        return int(number)
    except (ValueError, InvalidOperation):
        raise _fail("invalid_result", "proxy") from None


class ProxyRenderer:
    def __init__(self, media):
        self.media = media

    @contextmanager
    def reservation(self):
        token = object()
        with ingest._RESERVATION_LOCK:
            if ingest._RENDER_RESERVATIONS:
                raise _fail("conflict", "admission")
            self.media._ensure_directory(self.media.root)
            free = shutil.disk_usage(self.media.root).free
            if free < (len(ingest._RESERVATIONS) + 1) * ingest._RESERVATION_BYTES:
                raise _fail("disk_space", "proxy", retryable=True)
            ingest._RENDER_RESERVATIONS.add(token)
        try:
            yield
        finally:
            with ingest._RESERVATION_LOCK:
                ingest._RENDER_RESERVATIONS.discard(token)

    def _run(self, command, cwd, *, render=False):
        try:
            result = run_media(command, cwd=cwd, timeout=120 if render else 10,
                               kind="render" if render else "probe")
        except FileNotFoundError:
            raise _fail("dependency_missing", "proxy") from None
        except subprocess.TimeoutExpired:
            raise _fail("probe_timeout", "proxy", retryable=True) from None
        except (WorkerLimitError, OSError):
            raise _fail("internal", "proxy") from None
        if result.returncode:
            raise _fail("invalid_result", "proxy")
        return result

    def _timing(self, path, suffix):
        result = self._run([
            self.media.ffprobe, "-v", "error", "-of", "json",
            "-show_entries",
            "format=start_time,duration:stream=codec_type,codec_name,start_time,duration,time_base,"
            "sample_aspect_ratio,width,height,pix_fmt:stream_tags=rotate:stream_side_data=rotation",
            *self.media._input_options(suffix), str(path),
        ], path.parent)
        try:
            data = json.loads(result.stdout)
            streams = data["streams"]
            if not isinstance(streams, list) or not 1 <= len(streams) <= 2:
                raise ValueError
            origin = _time_us(data["format"]["start_time"])
            duration = _time_us(data["format"]["duration"])
            if duration <= 0:
                raise ValueError
            for stream in streams:
                stream["start_us"] = _time_us(stream["start_time"])
            return origin, duration, streams
        except (ValueError, TypeError, KeyError):
            raise _fail("invalid_result", "proxy") from None

    def _paths(self, asset):
        directory = self.media.assets_root / asset.asset_id / "derived" / str(asset.preview_revision)
        self.media._assert_confined(directory, self.media.assets_root)
        return directory, directory / "proxy.mp4", directory / "proxy.json"

    def existing(self, asset):
        _, target, manifest = self._paths(asset)
        for path in (target, manifest):
            self.media._assert_confined(path, self.media.assets_root)
        if not target.exists() and not manifest.exists():
            return None
        try:
            with manifest.open("rb") as handle:
                raw = handle.read(4097)
            if len(raw) > 4096:
                raise ValueError
            data = json.loads(raw)
            if (
                not isinstance(data, dict)
                or data.get("source_sha256") != asset.content_sha256
                or data.get("preview_revision") != asset.preview_revision
                or data.get("profile") != "h264-preview-v1"
                or not isinstance(data.get("mapping"), dict)
                or set(data["mapping"]) != {"source_origin_us", "proxy_origin_us", "rate_num", "rate_den"}
                or any(type(value) is not int for value in data["mapping"].values())
                or data["mapping"]["rate_num"] != 1 or data["mapping"]["rate_den"] != 1
            ):
                raise ValueError
            length, digest = self.media._hash_file(target)
            if (length, digest) != (data["byte_length"], data["content_sha256"]) or length <= 0:
                raise ValueError
            return DerivedMedia(asset.asset_id, "proxy", asset.preview_revision, length, digest, target)
        except MediaIngestError:
            raise
        except (OSError, ValueError, TypeError, KeyError):
            # Do not overwrite corrupt or half-published caches, especially
            # while another request may have a lease on the old bytes.
            raise _fail("invalid_result", "proxy") from None

    def allocate(self):
        directory = self.media.staging_root / ("stage_" + uuid.uuid4().hex)
        self.media._ensure_directory(directory)
        name = ".proxy-" + uuid.uuid4().hex
        return directory / (name + ".mp4"), directory / (name + ".json")

    def render(self, asset, pending, pending_manifest):
        if asset.kind != "video":
            raise _fail("unsupported_capability", "proxy")
        verified = self.media._read_record(self.media.assets_root / asset.asset_id)
        if verified is None or verified != asset or verified.storage_path != asset.storage_path:
            raise _fail("conflict", "proxy")
        existing = self.existing(asset)
        if existing:
            return existing
        for path in (pending, pending_manifest):
            self.media._assert_confined(path, self.media.staging_root)
            if path.exists():
                raise _fail("conflict", "proxy")
        origin, duration, source_streams = self._timing(asset.storage_path, "." + asset.metadata.format)
        # Copy a common timestamp origin for all streams. Passthrough plus
        # the demuxer time base preserves VFR intervals; audio is not reset.
        self._run([
            self.media.ffmpeg, "-v", "error", "-nostdin", "-n", "-xerror",
            "-filter_threads", "1", "-copyts", "-start_at_zero",
            *self.media._input_options("." + asset.metadata.format), "-i", str(asset.storage_path),
            "-map", "0:v:0", "-map", "0:a:0?", "-map_metadata", "-1", "-map_chapters", "-1",
            "-vf", "scale=w='max(2,trunc(iw*sar*min(1,min(1280/(iw*sar),720/ih))/2)*2)':"
            "h='max(2,trunc(ih*min(1,min(1280/(iw*sar),720/ih))/2)*2)',setsar=1",
            "-c:v", "libx264", "-threads", "1", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-bf", "0", "-fps_mode:v", "passthrough",
            "-enc_time_base:v", "demux", "-c:a", "copy", "-avoid_negative_ts", "disabled",
            "-movflags", "+faststart", "-fs", str(512 * 1024 * 1024), "-f", "mp4", str(pending),
        ], pending.parent, render=True)
        length, digest = self.media._hash_file(pending)
        if not 0 < length < 512 * 1024 * 1024:
            raise _fail("invalid_result", "proxy")
        with pending.open("r+b") as handle:
            os.fsync(handle.fileno())
        proxy_origin, proxy_duration, output_streams = self._timing(pending, ".mp4")
        video = [item for item in output_streams if item.get("codec_type") == "video"]
        if (
            len(video) != 1 or video[0].get("codec_name") != "h264"
            or video[0].get("pix_fmt") != "yuv420p"
            or not 0 < video[0].get("width", 0) <= 1280
            or not 0 < video[0].get("height", 0) <= 720
            or video[0].get("sample_aspect_ratio") != "1:1"
            or ingest._parse_rotation(video[0]) != 0
            or len(source_streams) != len(output_streams)
            or abs(proxy_duration - duration) > 50_000
            or abs(proxy_origin) > 2_000
        ):
            raise _fail("invalid_result", "proxy")
        for source in source_streams:
            matches = [item for item in output_streams if item.get("codec_type") == source.get("codec_type")]
            if (
                len(matches) != 1
                or abs(matches[0]["start_us"] - (source["start_us"] - origin)) > 2_000
                or (source.get("codec_type") == "audio" and matches[0].get("codec_name") != "aac")
            ):
                raise _fail("invalid_result", "proxy")
        # Full decode must succeed before the cache manifest makes bytes visible.
        self._run([
            self.media.ffmpeg, "-v", "error", "-nostdin", "-xerror",
            *self.media._input_options(".mp4"), "-i", str(pending),
            "-map", "0:v:0", "-map", "0:a:0?", "-threads", "1", "-f", "null", "-",
        ], pending.parent, render=True)
        if self.media._hash_file(asset.storage_path) != (asset.byte_length, asset.content_sha256):
            raise _fail("conflict", "proxy")
        data = {
            "profile": "h264-preview-v1", "source_sha256": asset.content_sha256,
            "preview_revision": asset.preview_revision, "byte_length": length, "content_sha256": digest,
            "mapping": {"source_origin_us": origin, "proxy_origin_us": proxy_origin, "rate_num": 1, "rate_den": 1},
        }
        with pending_manifest.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        directory, target, manifest = self._paths(asset)
        self.media._ensure_directory(directory)
        for path in (target, manifest):
            self.media._assert_confined(path, directory)
            if path.exists():
                raise _fail("conflict", "proxy")
        check_cancelled()
        os.rename(pending, target)
        os.rename(pending_manifest, manifest)
        return DerivedMedia(asset.asset_id, "proxy", asset.preview_revision, length, digest, target)
