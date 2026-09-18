"""Value objects shared by the isolated WB-1 media implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Literal, Optional


MediaKind = Literal["image", "video", "audio"]


@dataclass(frozen=True)
class MediaLimits:
    """Frozen WB-1 admission and probe limits.

    The values mirror the WB-0 contract. Callers may lower them for tests but
    may not raise them above the frozen boundary.
    """

    max_video_audio_bytes: int = 512 * 1024 * 1024
    max_still_bytes: int = 64 * 1024 * 1024
    max_request_files: int = 10
    max_request_bytes: int = 1024 * 1024 * 1024
    max_video_width: int = 1920
    max_video_height: int = 1080
    max_still_width: int = 4096
    max_still_height: int = 4096
    max_audio_channels: int = 2
    max_audio_sample_rate_hz: int = 96_000
    probe_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        numeric = (
            self.max_video_audio_bytes,
            self.max_still_bytes,
            self.max_request_files,
            self.max_request_bytes,
            self.max_video_width,
            self.max_video_height,
            self.max_still_width,
            self.max_still_height,
            self.max_audio_channels,
            self.max_audio_sample_rate_hz,
        )
        if any(type(value) is not int or value <= 0 for value in numeric):
            raise ValueError("media limits must be positive integers")
        if (
            type(self.probe_timeout_seconds) not in (int, float)
            or not math.isfinite(self.probe_timeout_seconds)
            or not 0 < self.probe_timeout_seconds <= 10
        ):
            raise ValueError("media limits must be positive")
        if self.max_video_audio_bytes > 512 * 1024 * 1024:
            raise ValueError("video/audio limit exceeds frozen WB-1 boundary")
        if self.max_still_bytes > 64 * 1024 * 1024:
            raise ValueError("still limit exceeds frozen WB-1 boundary")
        if self.max_request_files > 10 or self.max_request_bytes > 1024 * 1024 * 1024:
            raise ValueError("request limit exceeds frozen WB-1 boundary")
        if self.max_video_width > 1920 or self.max_video_height > 1080:
            raise ValueError("video dimensions exceed frozen WB-1 boundary")
        if self.max_still_width > 4096 or self.max_still_height > 4096:
            raise ValueError("still dimensions exceed frozen WB-1 boundary")
        if self.max_audio_channels > 2 or self.max_audio_sample_rate_hz > 96_000:
            raise ValueError("audio limit exceeds frozen WB-1 boundary")

    def byte_limit_for(self, kind: MediaKind) -> int:
        return self.max_still_bytes if kind == "image" else self.max_video_audio_bytes


@dataclass(frozen=True)
class ProbeMetadata:
    format: str
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_us: Optional[int] = None
    time_base: Optional[tuple[int, int]] = None
    video_streams: int = 0
    audio_streams: int = 0
    rotation: int = 0
    sample_rate_hz: Optional[int] = None
    channels: Optional[int] = None

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "format": self.format,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "width": self.width,
            "height": self.height,
            "duration_us": self.duration_us,
            "time_base": (
                {"num": self.time_base[0], "den": self.time_base[1]}
                if self.time_base
                else None
            ),
            "video_streams": self.video_streams,
            "audio_streams": self.audio_streams,
            "rotation": self.rotation,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
        }
        return {key: value for key, value in data.items() if value is not None}


@dataclass(frozen=True)
class StagedMedia:
    job_id: str
    filename: str
    kind: MediaKind
    path: Path = field(repr=False)
    byte_length: int
    content_sha256: str


@dataclass(frozen=True)
class AssetRecord:
    asset_id: str
    kind: MediaKind
    origin: Literal["upload", "library", "derived"]
    content_sha256: str
    byte_length: int
    state: str
    metadata: ProbeMetadata
    preview_revision: int = 1
    storage_path: Optional[Path] = field(default=None, repr=False, compare=False)

    def as_view(self) -> dict[str, Any]:
        """Return the bounded public DTO; never expose the managed path."""

        return {
            "asset_id": self.asset_id,
            "kind": self.kind,
            "origin": self.origin,
            "content_sha256": f"sha256:{self.content_sha256}",
            "byte_length": self.byte_length,
            "state": self.state,
            "metadata": self.metadata.as_dict(),
            "preview_revision": self.preview_revision,
        }


@dataclass(frozen=True)
class DerivedMedia:
    """A private derived artifact, such as a thumbnail or proxy."""

    asset_id: str
    kind: str
    preview_revision: int
    byte_length: int
    content_sha256: str
    path: Path = field(repr=False, compare=False)

    def as_view(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "kind": self.kind,
            "preview_revision": self.preview_revision,
            "byte_length": self.byte_length,
            "content_sha256": f"sha256:{self.content_sha256}",
        }
