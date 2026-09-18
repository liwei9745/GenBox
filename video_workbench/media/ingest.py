"""Fail-closed local media admission, staging, hashing and probing.

This module is deliberately independent from ``main.py``.  It can be tested
with synthetic fixtures before an authenticated workbench route is introduced.
Only server-generated IDs and paths are accepted; browser callers will later
provide multipart content through the same streaming boundary.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Iterator, Mapping, Optional

from .errors import MediaIngestError, media_error
from .models import AssetRecord, DerivedMedia, MediaKind, MediaLimits, ProbeMetadata, StagedMedia

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_ARCHIVE_EXTENSIONS = {".7z", ".bz2", ".gz", ".rar", ".tar", ".tgz", ".zip"}
_EXTENSIONS: dict[str, MediaKind] = {
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".mp4": "video",
    ".webm": "video",
    ".wav": "audio",
    ".mp3": "audio",
}
_IMAGE_CODECS = {".png": "png", ".jpg": "mjpeg", ".jpeg": "mjpeg", ".webp": "webp"}
_VIDEO_CODECS = {".mp4": "h264", ".webm": "vp9"}
_AUDIO_CODECS = {".wav": {"pcm"}, ".mp3": {"mp3"}}
_SAFE_MESSAGES = {
    "invalid_request": "素材请求无效。",
    "unsupported_media": "此素材格式不在当前工作台支持范围内。",
    "media_corrupt": "素材无法通过本地媒体校验。",
    "asset_too_large": "素材超过当前工作台允许的大小。",
    "dimension_limit": "素材尺寸超过当前工作台允许的范围。",
    "duration_limit": "素材时长超过当前工作台允许的范围。",
    "probe_timeout": "素材校验超时，请换用较小或更简单的文件。",
    "dependency_missing": "本地媒体校验依赖不可用，请先安装 FFmpeg。",
    "disk_space": "本地媒体暂存空间不足。",
    "internal": "本地媒体处理失败。",
    "not_found": "素材不存在。",
}
_MAX_THUMBNAIL_BYTES = 4 * 1024 * 1024


def _message(code: str) -> str:
    return _SAFE_MESSAGES.get(code, "本地媒体处理失败。")


def _fail(
    code: str,
    stage: str,
    *,
    retryable: bool = False,
    field: Optional[str] = None,
) -> MediaIngestError:
    return media_error(
        code,
        stage,
        _message(code),
        retryable=retryable,
        field=field,
    )


def _safe_filename(value: object) -> str:
    if not isinstance(value, str):
        raise _fail("invalid_request", "admission", field="filename")
    raw = value.strip()
    if (
        not raw
        or len(raw) > 255
        or "\x00" in raw
        or "/" in raw
        or "\\" in raw
        or Path(raw).name != raw
    ):
        raise _fail("invalid_request", "admission", field="filename")
    return raw


def _kind_for_filename(filename: str) -> MediaKind:
    suffix = Path(filename).suffix.lower()
    if suffix in _ARCHIVE_EXTENSIONS or suffix in {".m3u8", ".m3u", ".pls"}:
        raise _fail("unsupported_media", "admission", field="file")
    try:
        return _EXTENSIONS[suffix]
    except KeyError:
        raise _fail("unsupported_media", "admission", field="file") from None


def _safe_id(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise _fail("invalid_request", "admission", field=field)
    return value


def _parse_int(value: object) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _parse_duration_us(value: object) -> Optional[int]:
    if value in (None, "", "N/A"):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or parsed < 0:
        return None
    return int(parsed * Decimal(1_000_000))


def _parse_time_base(value: object) -> Optional[tuple[int, int]]:
    if not isinstance(value, str) or "/" not in value:
        return None
    raw_num, raw_den = value.split("/", 1)
    try:
        num, den = int(raw_num), int(raw_den)
    except (TypeError, ValueError):
        return None
    if den <= 0 or num <= 0:
        return None
    reduced = Fraction(num, den)
    return reduced.numerator, reduced.denominator


def _parse_rotation(stream: Mapping[str, Any]) -> int:
    tags = stream.get("tags")
    if isinstance(tags, Mapping):
        for key in ("rotate", "ROTATE"):
            parsed = _parse_int(tags.get(key))
            if parsed is not None:
                return parsed
    side_data = stream.get("side_data_list")
    if isinstance(side_data, list):
        for item in side_data:
            if isinstance(item, Mapping):
                parsed = _parse_int(item.get("rotation"))
                if parsed is not None:
                    return parsed
    return 0


def _canonical_format(kind: MediaKind, suffix: str) -> str:
    if kind == "image":
        return "jpeg" if suffix in {".jpg", ".jpeg"} else suffix[1:]
    return suffix[1:]


def _codec_matches(kind: MediaKind, suffix: str, streams: list[Mapping[str, Any]]) -> bool:
    video_streams = [item for item in streams if item.get("codec_type") == "video"]
    audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
    if kind == "image":
        return (
            len(video_streams) == 1
            and not audio_streams
            and video_streams[0].get("codec_name") == _IMAGE_CODECS[suffix]
        )
    if kind == "video":
        if len(video_streams) != 1 or video_streams[0].get("codec_name") != _VIDEO_CODECS[suffix]:
            return False
        if suffix == ".mp4":
            return not audio_streams or audio_streams[0].get("codec_name") == "aac"
        return not audio_streams
    if len(audio_streams) != 1 or video_streams:
        return False
    codec = str(audio_streams[0].get("codec_name") or "")
    return any(codec == allowed or codec.startswith(allowed + "_") for allowed in _AUDIO_CODECS[suffix])


class MediaIngestManager:
    """Manage only workbench-owned staging and asset paths."""

    def __init__(
        self,
        root: os.PathLike[str] | str,
        *,
        ffprobe: str = "ffprobe",
        ffmpeg: str = "ffmpeg",
        limits: Optional[MediaLimits] = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.staging_root = self.root / "staging"
        self.assets_root = self.root / "assets"
        self.ffprobe = str(ffprobe)
        self.ffmpeg = str(ffmpeg)
        self.limits = limits or MediaLimits()

    def _ensure_directory(self, path: Path, *, code: str = "disk_space") -> None:
        if path.exists() and (path.is_symlink() or not path.is_dir()):
            raise _fail("internal", "admission")
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise _fail(code, "staging", retryable=code == "disk_space") from None
        if path.is_symlink() or not path.is_dir():
            raise _fail("internal", "staging")

    def _assert_confined(self, path: Path, root: Path) -> None:
        try:
            resolved_root = root.resolve()
            resolved_path = path.resolve(strict=False)
            resolved_path.relative_to(resolved_root)
        except (OSError, ValueError):
            raise _fail("internal", "storage") from None
        current = resolved_root
        try:
            relative_parts = resolved_path.relative_to(resolved_root).parts
        except ValueError:
            raise _fail("internal", "storage") from None
        for part in relative_parts:
            current = current / part
            if current.is_symlink():
                raise _fail("internal", "storage")

    def _prepare_job_dir(self, job_id: str) -> Path:
        safe_job_id = _safe_id(job_id, field="job_id")
        self._ensure_directory(self.root)
        self._ensure_directory(self.staging_root)
        job_dir = self.staging_root / safe_job_id
        if job_dir.exists() and job_dir.is_symlink():
            raise _fail("internal", "staging")
        self._ensure_directory(job_dir)
        self._assert_confined(job_dir, self.staging_root)
        return job_dir

    @staticmethod
    def _iter_chunks(content: object) -> Iterator[bytes]:
        if isinstance(content, (bytes, bytearray, memoryview)):
            yield bytes(content)
            return
        if isinstance(content, (str, os.PathLike)):
            raise _fail("invalid_request", "admission", field="file")
        reader = getattr(content, "read", None)
        if callable(reader):
            while True:
                chunk = reader(1024 * 1024)
                if inspect.isawaitable(chunk):
                    raise _fail("invalid_request", "admission", field="file")
                if chunk in (None, b""):
                    break
                if not isinstance(chunk, (bytes, bytearray, memoryview)):
                    raise _fail("invalid_request", "admission", field="file")
                yield bytes(chunk)
            return
        try:
            iterator = iter(content)  # type: ignore[arg-type]
        except TypeError:
            raise _fail("invalid_request", "admission", field="file") from None
        for chunk in iterator:
            if not isinstance(chunk, (bytes, bytearray, memoryview)):
                raise _fail("invalid_request", "admission", field="file")
            if chunk:
                yield bytes(chunk)

    def stage_stream(self, job_id: str, filename: str, content: object) -> StagedMedia:
        safe_name = _safe_filename(filename)
        kind = _kind_for_filename(safe_name)
        job_dir = self._prepare_job_dir(job_id)
        temp_path: Optional[Path] = None
        digest = hashlib.sha256()
        total = 0
        limit = self.limits.byte_limit_for(kind)
        try:
            # Preserve only the validated extension. FFmpeg uses the suffix as
            # a demuxer hint for image and container formats; the original
            # user filename is never used as a path component.
            fd, raw_temp = tempfile.mkstemp(
                prefix=".upload-",
                suffix=Path(safe_name).suffix.lower(),
                dir=job_dir,
            )
            temp_path = Path(raw_temp)
            if temp_path.is_symlink() or not temp_path.is_file():
                raise _fail("internal", "staging")
            with os.fdopen(fd, "wb") as handle:
                for chunk in self._iter_chunks(content):
                    total += len(chunk)
                    if total > limit:
                        raise _fail("asset_too_large", "admission", field="file")
                    handle.write(chunk)
                    digest.update(chunk)
                if total <= 0:
                    raise _fail("invalid_request", "admission", field="file")
                handle.flush()
                os.fsync(handle.fileno())
            self._assert_confined(temp_path, job_dir)
            return StagedMedia(
                job_id=job_id,
                filename=safe_name,
                kind=kind,
                path=temp_path,
                byte_length=total,
                content_sha256=digest.hexdigest(),
            )
        except MediaIngestError:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise
        except (OSError, ValueError):
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise _fail("disk_space", "staging", retryable=True) from None

    def stage_batch(
        self,
        job_id: str,
        files: Iterable[tuple[str, object]],
    ) -> list[StagedMedia]:
        staged: list[StagedMedia] = []
        total = 0
        try:
            count = 0
            for entry in files:
                count += 1
                if count > self.limits.max_request_files:
                    raise _fail("invalid_request", "admission", field="files")
                if not isinstance(entry, (tuple, list)) or len(entry) != 2:
                    raise _fail("invalid_request", "admission", field="files")
                filename, content = entry
                item = self.stage_stream(job_id, filename, content)
                total += item.byte_length
                if total > self.limits.max_request_bytes:
                    raise _fail("asset_too_large", "admission", field="files")
                staged.append(item)
            if not staged:
                raise _fail("invalid_request", "admission", field="files")
            return staged
        except MediaIngestError:
            for item in staged:
                self.cleanup_staged(item)
            raise

    def _probe_command(self, path: Path) -> list[str]:
        return [
            self.ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]

    def probe(self, staged: StagedMedia) -> ProbeMetadata:
        self._assert_confined(staged.path, self.staging_root)
        if staged.path.is_symlink() or not staged.path.is_file():
            raise _fail("not_found", "probe", field="file")
        try:
            result = subprocess.run(
                self._probe_command(staged.path),
                cwd=str(staged.path.parent),
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.limits.probe_timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            raise _fail("dependency_missing", "probe") from None
        except subprocess.TimeoutExpired:
            raise _fail("probe_timeout", "probe", retryable=True) from None
        except OSError:
            raise _fail("dependency_missing", "probe") from None
        if result.returncode != 0:
            raise _fail("media_corrupt", "probe", field="file")
        try:
            payload = json.loads(result.stdout)
        except (TypeError, ValueError):
            raise _fail("media_corrupt", "probe", field="file") from None
        try:
            return self._validate_probe(staged, payload)
        except MediaIngestError:
            raise
        except (KeyError, TypeError, ValueError):
            raise _fail("media_corrupt", "probe", field="file") from None

    def _validate_probe(self, staged: StagedMedia, payload: Mapping[str, Any]) -> ProbeMetadata:
        streams_raw = payload.get("streams")
        fmt = payload.get("format")
        if not isinstance(streams_raw, list) or not isinstance(fmt, Mapping):
            raise _fail("media_corrupt", "probe", field="file")
        streams = [item for item in streams_raw if isinstance(item, Mapping)]
        if len(streams) != len(streams_raw) or not streams:
            raise _fail("media_corrupt", "probe", field="file")
        if any(item.get("codec_type") not in {"video", "audio"} for item in streams):
            raise _fail("unsupported_media", "probe", field="file")
        video_streams = [item for item in streams if item.get("codec_type") == "video"]
        audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
        if len(video_streams) > 1 or len(audio_streams) > 1:
            raise _fail("unsupported_media", "probe", field="file")
        suffix = Path(staged.filename).suffix.lower()
        if not _codec_matches(staged.kind, suffix, streams):
            raise _fail("unsupported_media", "probe", field="file")
        format_name = str(fmt.get("format_name") or "")
        if not format_name:
            raise _fail("media_corrupt", "probe", field="file")
        primary = video_streams[0] if video_streams else audio_streams[0]
        width = _parse_int(primary.get("width"))
        height = _parse_int(primary.get("height"))
        if staged.kind in {"image", "video"}:
            if not width or not height:
                raise _fail("media_corrupt", "probe", field="file")
            max_width = self.limits.max_still_width if staged.kind == "image" else self.limits.max_video_width
            max_height = self.limits.max_still_height if staged.kind == "image" else self.limits.max_video_height
            if width > max_width or height > max_height:
                raise _fail("dimension_limit", "probe", field="file")
        duration_us = _parse_duration_us(primary.get("duration"))
        if duration_us is None:
            duration_us = _parse_duration_us(fmt.get("duration"))
        if duration_us is not None and duration_us > self.limits.max_asset_duration_us:
            raise _fail("duration_limit", "probe", field="file")
        time_base = _parse_time_base(primary.get("time_base"))
        sample_rate = _parse_int(audio_streams[0].get("sample_rate")) if audio_streams else None
        channels = _parse_int(audio_streams[0].get("channels")) if audio_streams else None
        if channels is not None and channels > self.limits.max_audio_channels:
            raise _fail("unsupported_media", "probe", field="file")
        if sample_rate is not None and sample_rate > self.limits.max_audio_sample_rate_hz:
            raise _fail("unsupported_media", "probe", field="file")
        return ProbeMetadata(
            format=_canonical_format(staged.kind, suffix),
            video_codec=str(video_streams[0].get("codec_name")) if video_streams else None,
            audio_codec=str(audio_streams[0].get("codec_name")) if audio_streams else None,
            width=width,
            height=height,
            duration_us=duration_us,
            time_base=time_base,
            video_streams=len(video_streams),
            audio_streams=len(audio_streams),
            rotation=_parse_rotation(video_streams[0]) if video_streams else 0,
            sample_rate_hz=sample_rate,
            channels=channels,
        )

    def _asset_dir(self, asset_id: str) -> Path:
        safe_asset_id = _safe_id(asset_id, field="asset_id")
        self._ensure_directory(self.assets_root)
        target = self.assets_root / safe_asset_id
        if target.exists() and target.is_symlink():
            raise _fail("internal", "publish")
        self._assert_confined(target, self.assets_root)
        return target

    def _read_record(self, directory: Path) -> Optional[AssetRecord]:
        manifest = directory / "asset.json"
        original = directory / "original"
        if manifest.is_symlink() or original.is_symlink() or not manifest.is_file() or not original.is_file():
            return None
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            metadata = data["metadata"]
            time_base_data = metadata.get("time_base")
            time_base = (
                int(time_base_data["num"]),
                int(time_base_data["den"]),
            ) if time_base_data else None
            probe_metadata = ProbeMetadata(
                format=str(metadata["format"]),
                video_codec=metadata.get("video_codec"),
                audio_codec=metadata.get("audio_codec"),
                width=metadata.get("width"),
                height=metadata.get("height"),
                duration_us=metadata.get("duration_us"),
                time_base=time_base,
                video_streams=int(metadata.get("video_streams", 0)),
                audio_streams=int(metadata.get("audio_streams", 0)),
                rotation=int(metadata.get("rotation", 0)),
                sample_rate_hz=metadata.get("sample_rate_hz"),
                channels=metadata.get("channels"),
            )
            digest = str(data["content_sha256"]).lower()
            if not _SHA256.fullmatch(digest):
                return None
            if int(data["byte_length"]) != original.stat().st_size:
                return None
            actual_digest = hashlib.sha256()
            with original.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    actual_digest.update(chunk)
            if actual_digest.hexdigest() != digest:
                return None
            return AssetRecord(
                asset_id=str(data["asset_id"]),
                kind=str(data["kind"]),  # type: ignore[arg-type]
                origin=str(data["origin"]),  # type: ignore[arg-type]
                content_sha256=digest,
                byte_length=int(data["byte_length"]),
                state=str(data["state"]),
                metadata=probe_metadata,
                preview_revision=int(data.get("preview_revision", 1)),
                storage_path=original,
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def find_by_digest(self, content_sha256: str) -> Optional[AssetRecord]:
        digest = str(content_sha256).lower()
        if not _SHA256.fullmatch(digest):
            raise _fail("invalid_request", "lookup", field="content_sha256")
        if not self.assets_root.exists():
            return None
        if self.assets_root.is_symlink() or not self.assets_root.is_dir():
            raise _fail("internal", "lookup")
        self._assert_confined(self.assets_root, self.root)
        for directory in self.assets_root.iterdir():
            if not directory.is_dir() or directory.is_symlink():
                continue
            record = self._read_record(directory)
            if record and record.content_sha256 == digest:
                return record
        return None

    def publish(
        self,
        staged: StagedMedia,
        metadata: ProbeMetadata,
        *,
        origin: str = "upload",
        asset_id: Optional[str] = None,
    ) -> AssetRecord:
        if origin not in {"upload", "library", "derived"}:
            raise _fail("invalid_request", "publish", field="origin")
        self._assert_confined(staged.path, self.staging_root)
        if staged.path.is_symlink() or not staged.path.is_file():
            raise _fail("not_found", "publish", field="file")
        if metadata.format != Path(staged.filename).suffix.lower().lstrip("."):
            if not (metadata.format == "jpeg" and Path(staged.filename).suffix.lower() in {".jpg", ".jpeg"}):
                raise _fail("invalid_request", "publish", field="metadata")
        duplicate = self.find_by_digest(staged.content_sha256)
        if duplicate is not None:
            self.cleanup_staged(staged)
            return duplicate
        safe_asset_id = asset_id or f"ast_{uuid.uuid4().hex}"
        directory = self._asset_dir(safe_asset_id)
        if directory.exists():
            raise _fail("conflict", "publish", field="asset_id")
        original = directory / "original"
        manifest = directory / "asset.json"
        temp_original: Optional[Path] = None
        temp_manifest: Optional[Path] = None
        published = False
        directory_created = False
        try:
            directory.mkdir(parents=False)
            directory_created = True
            self._assert_confined(directory, self.assets_root)
            fd, raw_original = tempfile.mkstemp(prefix=".original-", suffix=".tmp", dir=directory)
            temp_original = Path(raw_original)
            with os.fdopen(fd, "wb") as output, staged.path.open("rb") as source:
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp_original, original)
            temp_original = None
            record = AssetRecord(
                asset_id=safe_asset_id,
                kind=staged.kind,
                origin=origin,  # type: ignore[arg-type]
                content_sha256=staged.content_sha256,
                byte_length=staged.byte_length,
                state="ready",
                metadata=metadata,
                storage_path=original,
            )
            fd, raw_manifest = tempfile.mkstemp(prefix=".asset-", suffix=".json", dir=directory)
            temp_manifest = Path(raw_manifest)
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as output:
                json.dump(
                    {
                        **record.as_view(),
                        "content_sha256": record.content_sha256,
                    },
                    output,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp_manifest, manifest)
            temp_manifest = None
            published = True
            self.cleanup_staged(staged)
            return record
        except MediaIngestError:
            raise
        except OSError:
            raise _fail("disk_space", "publish", retryable=True) from None
        finally:
            if temp_original is not None:
                temp_original.unlink(missing_ok=True)
            if temp_manifest is not None:
                temp_manifest.unlink(missing_ok=True)
            if directory_created and not published and directory.exists() and not directory.is_symlink():
                for owned_path in (manifest, original):
                    if owned_path.exists() and not owned_path.is_symlink():
                        owned_path.unlink(missing_ok=True)
                try:
                    directory.rmdir()
                except OSError:
                    # A failed publication must not hide its original error.
                    # The directory is still confined and contains no public
                    # manifest, so a later orphan-recovery pass may remove it.
                    pass

    @staticmethod
    def _hash_file(path: Path) -> tuple[int, str]:
        digest = hashlib.sha256()
        total = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                total += len(chunk)
                digest.update(chunk)
        return total, digest.hexdigest()

    def _existing_thumbnail(
        self,
        target: Path,
        asset_id: str,
        revision: int,
    ) -> Optional[DerivedMedia]:
        if target.is_symlink() or not target.is_file():
            return None
        try:
            size, digest = self._hash_file(target)
            if size <= 0 or size > _MAX_THUMBNAIL_BYTES:
                return None
            from PIL import Image

            with Image.open(target) as image:
                image.verify()
            with Image.open(target) as image:
                width, height = image.size
                image_format = image.format
            if image_format != "JPEG" or width > 320 or height > 180:
                return None
            return DerivedMedia(
                asset_id=asset_id,
                kind="thumbnail",
                preview_revision=revision,
                byte_length=size,
                content_sha256=digest,
                path=target,
            )
        except (OSError, ValueError):
            return None

    def derive_thumbnail(
        self,
        asset: AssetRecord,
        *,
        preview_revision: Optional[int] = None,
    ) -> DerivedMedia:
        """Generate a bounded JPEG thumbnail without exposing local paths."""

        if asset.state != "ready" or asset.storage_path is None:
            raise _fail("not_found", "thumbnail", field="asset_id")
        if asset.kind == "audio":
            raise _fail("unsupported_capability", "thumbnail", field="asset_id")
        source = asset.storage_path
        self._assert_confined(source, self.assets_root)
        if source.is_symlink() or not source.is_file():
            raise _fail("not_found", "thumbnail", field="asset_id")
        revision = asset.preview_revision if preview_revision is None else int(preview_revision)
        if revision <= 0:
            raise _fail("invalid_request", "thumbnail", field="preview_revision")
        asset_dir = source.parent
        if asset_dir.is_symlink():
            raise _fail("internal", "thumbnail")
        self._assert_confined(asset_dir, self.assets_root)
        derived_dir = asset_dir / "derived" / str(revision)
        self._ensure_directory(derived_dir)
        self._assert_confined(derived_dir, self.assets_root)
        target = derived_dir / "thumbnail.jpg"
        if target.is_symlink():
            raise _fail("internal", "thumbnail")
        existing = self._existing_thumbnail(target, asset.asset_id, revision)
        if existing is not None:
            return existing
        temporary: Optional[Path] = None
        try:
            fd, raw_temp = tempfile.mkstemp(
                prefix=".thumbnail-",
                suffix=".jpg",
                dir=derived_dir,
            )
            temporary = Path(raw_temp)
            os.close(fd)
            result = subprocess.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=320:180:force_original_aspect_ratio=decrease,"
                    "pad=320:180:(ow-iw)/2:(oh-ih)/2",
                    "-q:v",
                    "5",
                    str(temporary),
                ],
                cwd=str(derived_dir),
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.limits.probe_timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            raise _fail("dependency_missing", "thumbnail") from None
        except subprocess.TimeoutExpired:
            raise _fail("probe_timeout", "thumbnail", retryable=True) from None
        except OSError:
            raise _fail("dependency_missing", "thumbnail") from None
        try:
            if result.returncode != 0 or temporary is None or not temporary.is_file():
                raise _fail("media_corrupt", "thumbnail", field="asset_id")
            output = self._existing_thumbnail(temporary, asset.asset_id, revision)
            if output is None:
                raise _fail("invalid_result", "thumbnail", field="asset_id")
            os.replace(temporary, target)
            temporary = None
            return DerivedMedia(
                asset_id=asset.asset_id,
                kind="thumbnail",
                preview_revision=revision,
                byte_length=output.byte_length,
                content_sha256=output.content_sha256,
                path=target,
            )
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def import_content(
        self,
        job_id: str,
        filename: str,
        content: object,
        *,
        origin: str = "upload",
        asset_id: Optional[str] = None,
    ) -> AssetRecord:
        staged = self.stage_stream(job_id, filename, content)
        try:
            metadata = self.probe(staged)
            return self.publish(staged, metadata, origin=origin, asset_id=asset_id)
        except MediaIngestError:
            self.cleanup_staged(staged)
            raise

    def cleanup_staged(self, staged: StagedMedia) -> None:
        """Remove only a manager-owned temporary file, never the source."""

        self._assert_confined(staged.path, self.staging_root)
        if staged.path.is_symlink():
            raise _fail("internal", "cleanup")
        try:
            staged.path.unlink(missing_ok=True)
            job_dir = staged.path.parent
            if job_dir.is_dir() and not job_dir.is_symlink() and not any(job_dir.iterdir()):
                job_dir.rmdir()
        except OSError:
            raise _fail("cleanup_pending", "cleanup", retryable=True) from None
