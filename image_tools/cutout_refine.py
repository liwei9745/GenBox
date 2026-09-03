"""Deterministic, local-only alpha refinement for transparent cutout PNGs.

The service accepts image payloads only. It never resolves paths, fetches URLs,
or composites a background. RGB samples are preserved exactly while feathering
is applied to the alpha channel, optionally scoped by a caller-supplied mask.
"""

from __future__ import annotations

import base64
import binascii
import io
import math
import os
import re
import time
import uuid
import warnings
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageChops, ImageFilter


CUTOUT_REFINE_CONTRACT = "genbox-cutout-refine-v1"
CUTOUT_SELECTION_MASK_CONTRACT = "genbox-cutout-selection-mask-v1"
DEFAULT_FEATHER_RADIUS = 0.0
MAX_FEATHER_RADIUS = 64.0
MAX_REFINE_IMAGE_BYTES = int(
    os.getenv("GENBOX_CUTOUT_REFINE_MAX_IMAGE_BYTES", str(25 * 1024 * 1024))
)
MAX_REFINE_OUTPUT_BYTES = int(
    os.getenv("GENBOX_CUTOUT_REFINE_MAX_OUTPUT_BYTES", str(25 * 1024 * 1024))
)
MAX_REFINE_PIXELS = int(os.getenv("GENBOX_CUTOUT_REFINE_MAX_PIXELS", "25000000"))

_DATA_URL_RE = re.compile(
    r"^data:([A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+);base64$",
    re.IGNORECASE,
)


class CutoutRefineError(RuntimeError):
    """A structured error that is safe to return from a local API route."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        **details: Any,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.status_code = int(status_code)
        self.details = dict(details)

    def to_detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "contract": CUTOUT_REFINE_CONTRACT,
            "operation": "alpha_refine",
            "local_only": True,
        }
        detail.update(self.details)
        return detail


class CutoutRefineInputError(CutoutRefineError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(code, message, status_code=422, **details)


class CutoutRefineOutputError(CutoutRefineError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(code, message, status_code=500, **details)


class CutoutRefinePersistenceError(CutoutRefineError):
    def __init__(self, message: str = "The refined cutout could not be saved") -> None:
        super().__init__(
            "cutout_refine_persistence_failed",
            message,
            status_code=500,
        )


def _decode_png_payload(value: object, *, field: str) -> bytes:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        if not raw:
            raise CutoutRefineInputError(
                f"{field}_required",
                f"{field} must contain a PNG image payload",
            )
        return raw

    if not isinstance(value, str) or not value.strip():
        raise CutoutRefineInputError(
            f"{field}_required",
            f"{field} must contain a base64 PNG image payload",
        )

    original = value.strip()
    encoded = original
    if original.lower().startswith("data:"):
        header, separator, encoded = original.partition(",")
        match = _DATA_URL_RE.fullmatch(header) if separator else None
        if match is None:
            raise CutoutRefineInputError(
                f"{field}_data_url_invalid",
                f"{field} must be a base64 PNG data URL",
            )
        if match.group(1).lower() != "image/png":
            raise CutoutRefineInputError(
                f"{field}_mime_invalid",
                f"{field} must declare image/png",
            )

    max_encoded_length = ((MAX_REFINE_IMAGE_BYTES + 2) // 3) * 4
    if len(encoded) > max_encoded_length:
        raise CutoutRefineInputError(
            f"{field}_too_large",
            f"{field} exceeds the configured byte limit",
            max_bytes=MAX_REFINE_IMAGE_BYTES,
        )
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, TypeError, ValueError):
        raise CutoutRefineInputError(
            f"{field}_base64_invalid",
            f"{field} is not valid base64",
        ) from None
    if not raw:
        raise CutoutRefineInputError(
            f"{field}_base64_invalid",
            f"{field} decoded to an empty image",
        )
    return raw


def _load_png_payload(value: object, *, field: str) -> dict[str, Any]:
    raw = _decode_png_payload(value, field=field)
    if len(raw) > MAX_REFINE_IMAGE_BYTES:
        raise CutoutRefineInputError(
            f"{field}_too_large",
            f"{field} exceeds the configured byte limit",
            max_bytes=MAX_REFINE_IMAGE_BYTES,
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as probe:
                width, height = (int(probe.width), int(probe.height))
                image_format = str(probe.format or "").upper()
                mode = str(probe.mode or "")
                if width <= 0 or height <= 0 or width * height > MAX_REFINE_PIXELS:
                    raise CutoutRefineInputError(
                        f"{field}_pixels_exceeded",
                        f"{field} exceeds the configured pixel limit",
                        max_pixels=MAX_REFINE_PIXELS,
                    )
                probe.verify()
            with Image.open(io.BytesIO(raw)) as loaded:
                loaded.load()
                image = loaded.copy()
    except CutoutRefineError:
        raise
    except Exception:
        raise CutoutRefineInputError(
            f"{field}_payload_invalid",
            f"{field} is not a readable image",
        ) from None

    if image_format != "PNG":
        raise CutoutRefineInputError(
            f"{field}_format_invalid",
            f"{field} must contain PNG bytes",
        )
    return {
        "bytes": raw,
        "image": image,
        "width": width,
        "height": height,
        "mode": mode,
        "format": image_format,
        "mime_type": "image/png",
    }


def _load_refine_source(value: object) -> dict[str, Any]:
    checked = _load_png_payload(value, field="source_image")
    image = checked["image"]
    if image.mode != "RGBA":
        raise CutoutRefineInputError(
            "source_image_mode_invalid",
            "source_image must be an RGBA PNG",
        )
    alpha_extrema = image.getchannel("A").getextrema()
    if not alpha_extrema or alpha_extrema[0] >= 255 or alpha_extrema[1] <= 0:
        raise CutoutRefineInputError(
            "source_image_alpha_required",
            "source_image must contain visible and transparent alpha samples",
        )
    checked["alpha_extrema"] = tuple(int(part) for part in alpha_extrema)
    return checked


def _load_restore_source(value: object, expected_size: tuple[int, int]) -> dict[str, Any]:
    checked = _load_png_payload(value, field="restore_source_image")
    actual_size = (checked["width"], checked["height"])
    required_size = tuple(int(part) for part in expected_size)
    if actual_size != required_size:
        raise CutoutRefineInputError(
            "restore_source_size_mismatch",
            "restore_source_image dimensions must match source_image",
            expected_width=required_size[0],
            expected_height=required_size[1],
            actual_width=actual_size[0],
            actual_height=actual_size[1],
        )
    image = checked["image"]
    if image.mode not in {"RGB", "RGBA"}:
        raise CutoutRefineInputError(
            "restore_source_mode_invalid",
            "restore_source_image must be an RGB or RGBA PNG",
        )
    checked["image"] = image.convert("RGB")
    return checked


def validate_refine_source(value: object) -> dict[str, Any]:
    """Validate an RGBA PNG data URL, raw base64 string, or in-memory bytes."""

    checked = _load_refine_source(value)
    return {key: item for key, item in checked.items() if key != "image"}


def _selection_channel(image: Image.Image) -> Image.Image:
    if "A" in image.getbands():
        alpha = image.getchannel("A")
        if alpha.getextrema() != (255, 255):
            return alpha.copy()
    if image.mode == "P" and "transparency" in image.info:
        alpha = image.convert("RGBA").getchannel("A")
        if alpha.getextrema() != (255, 255):
            return alpha
    return image.convert("L")


def _load_selection_mask(value: object, expected_size: tuple[int, int]) -> dict[str, Any]:
    checked = _load_png_payload(value, field="selection_mask")
    actual_size = (checked["width"], checked["height"])
    required_size = tuple(int(part) for part in expected_size)
    if actual_size != required_size:
        raise CutoutRefineInputError(
            "selection_mask_size_mismatch",
            "selection_mask dimensions must match source_image",
            expected_width=required_size[0],
            expected_height=required_size[1],
            actual_width=actual_size[0],
            actual_height=actual_size[1],
        )
    mask = _selection_channel(checked["image"])
    extrema = mask.getextrema() or (0, 0)
    checked["mask"] = mask
    checked["selection_extrema"] = tuple(int(part) for part in extrema)
    return checked


def validate_selection_mask(value: object, expected_size: tuple[int, int]) -> dict[str, Any]:
    """Validate and describe a PNG mask using alpha when it carries scope.

    RGBA/LA masks with non-opaque alpha use that alpha channel. Other PNG masks
    use their luminance, so both transparent canvas masks and black/white masks
    have deterministic behavior.
    """

    checked = _load_selection_mask(value, expected_size)
    return {
        key: item
        for key, item in checked.items()
        if key not in {"image", "mask"}
    }


def _validated_feather_radius(value: object) -> float:
    if isinstance(value, bool):
        raise CutoutRefineInputError(
            "feather_radius_invalid",
            "feather_radius must be a finite number within the supported range",
            minimum=0,
            maximum=MAX_FEATHER_RADIUS,
        )
    try:
        radius = float(value)
    except (TypeError, ValueError):
        radius = math.nan
    if not math.isfinite(radius) or radius < 0 or radius > MAX_FEATHER_RADIUS:
        raise CutoutRefineInputError(
            "feather_radius_invalid",
            "feather_radius must be a finite number within the supported range",
            minimum=0,
            maximum=MAX_FEATHER_RADIUS,
    )
    return radius


def _validated_restore_min_alpha(value: object) -> int:
    if isinstance(value, bool):
        raise CutoutRefineInputError(
            "restore_min_alpha_invalid",
            "restore_min_alpha must be a finite number within the supported range",
            minimum=0,
            maximum=255,
        )
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        threshold = math.nan
    if not math.isfinite(threshold) or threshold < 0 or threshold > 255:
        raise CutoutRefineInputError(
            "restore_min_alpha_invalid",
            "restore_min_alpha must be a finite number within the supported range",
            minimum=0,
            maximum=255,
        )
    return int(round(threshold))


def validate_refined_png(
    value: object,
    expected_size: Optional[tuple[int, int]] = None,
) -> dict[str, Any]:
    """Require a bounded, readable RGBA PNG that retains meaningful alpha."""

    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise CutoutRefineOutputError(
            "refined_output_invalid",
            "The refined cutout is not PNG bytes",
        )
    raw = bytes(value)
    if not raw or len(raw) > MAX_REFINE_OUTPUT_BYTES:
        raise CutoutRefineOutputError(
            "refined_output_invalid",
            "The refined cutout is empty or exceeds the output byte limit",
            max_bytes=MAX_REFINE_OUTPUT_BYTES,
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as probe:
                image_format = str(probe.format or "").upper()
                mode = str(probe.mode or "")
                size = (int(probe.width), int(probe.height))
                if size[0] <= 0 or size[1] <= 0 or size[0] * size[1] > MAX_REFINE_PIXELS:
                    raise CutoutRefineOutputError(
                        "refined_output_pixels_exceeded",
                        "The refined cutout exceeds the configured pixel limit",
                        max_pixels=MAX_REFINE_PIXELS,
                    )
                probe.verify()
            with Image.open(io.BytesIO(raw)) as loaded:
                loaded.load()
                alpha_extrema = (
                    loaded.getchannel("A").getextrema()
                    if loaded.mode == "RGBA"
                    else None
                )
    except CutoutRefineError:
        raise
    except Exception:
        raise CutoutRefineOutputError(
            "refined_output_invalid",
            "The refined cutout is not a readable PNG",
        ) from None

    if image_format != "PNG" or mode != "RGBA":
        raise CutoutRefineOutputError(
            "refined_output_invalid",
            "The refined cutout must be an RGBA PNG",
        )
    if expected_size is not None and size != tuple(
        int(part) for part in expected_size
    ):
        raise CutoutRefineOutputError(
            "refined_output_size_mismatch",
            "The refined cutout dimensions must match the source image",
        )
    if not alpha_extrema or alpha_extrema[0] >= 255 or alpha_extrema[1] <= 0:
        raise CutoutRefineOutputError(
            "refined_output_alpha_invalid",
            "The refined cutout must retain visible and transparent alpha samples",
        )
    return {
        "bytes": raw,
        "width": size[0],
        "height": size[1],
        "mode": "RGBA",
        "format": "PNG",
        "mime_type": "image/png",
        "transparent": True,
        "alpha_extrema": tuple(int(part) for part in alpha_extrema),
    }


def refine_cutout_alpha(
    image_data: object,
    selection_mask_data: object = None,
    feather_radius: object = DEFAULT_FEATHER_RADIUS,
    *,
    restore_mode: object = False,
    restore_source_image_data: object = None,
    restore_min_alpha: object = 255,
) -> dict[str, Any]:
    """Feather only the source alpha, optionally within a PNG selection mask."""

    radius = _validated_feather_radius(feather_radius)
    if not isinstance(restore_mode, bool):
        raise CutoutRefineInputError(
            "restore_mode_invalid",
            "restore_mode must be true or false",
        )
    source = _load_refine_source(image_data)
    image = source["image"]
    original_alpha = image.getchannel("A")
    restore_applied = bool(restore_mode)
    restore_rgb = None
    if restore_applied:
        if restore_source_image_data is None:
            raise CutoutRefineInputError(
                "restore_source_required",
                "restore_source_image is required when restore_mode is enabled",
            )
        restore_source = _load_restore_source(
            restore_source_image_data,
            (source["width"], source["height"]),
        )
        restore_rgb = restore_source["image"]
        restore_floor = _validated_restore_min_alpha(restore_min_alpha)
        candidate_alpha = ImageChops.lighter(
            original_alpha,
            Image.new("L", image.size, restore_floor),
        )
        if radius > 0:
            candidate_alpha = candidate_alpha.filter(ImageFilter.GaussianBlur(radius=radius))
    else:
        if restore_source_image_data is not None:
            raise CutoutRefineInputError(
                "restore_fields_conflict",
                "restore_source_image is only accepted when restore_mode is enabled",
            )
        candidate_alpha = (
            original_alpha.filter(ImageFilter.GaussianBlur(radius=radius))
            if radius > 0
            else original_alpha.copy()
        )

    selection_applied = selection_mask_data is not None
    selection_contract: Optional[str] = None
    if selection_applied:
        selection = _load_selection_mask(
            selection_mask_data,
            (source["width"], source["height"]),
        )
        final_alpha = Image.composite(candidate_alpha, original_alpha, selection["mask"])
        selection_contract = CUTOUT_SELECTION_MASK_CONTRACT
        if restore_applied and restore_rgb is not None:
            rgb = Image.composite(restore_rgb, image.convert("RGB"), selection["mask"])
        else:
            rgb = image.convert("RGB")
    else:
        if restore_applied:
            raise CutoutRefineInputError(
                "restore_selection_required",
                "restore_mode requires a selection mask",
            )
        final_alpha = candidate_alpha
        rgb = image.convert("RGB")

    alpha_changed = final_alpha.tobytes() != original_alpha.tobytes()
    image = rgb.convert("RGBA")
    image.putalpha(final_alpha)
    output = io.BytesIO()
    image.save(output, format="PNG", compress_level=6)
    checked = validate_refined_png(
        output.getvalue(),
        expected_size=(source["width"], source["height"]),
    )
    return {
        "contract": CUTOUT_REFINE_CONTRACT,
        "selection_contract": selection_contract,
        "image_bytes": checked["bytes"],
        "width": checked["width"],
        "height": checked["height"],
        "mime_type": "image/png",
        "mode": "RGBA",
        "transparent": True,
        "feather_radius": radius,
        "restore_mode": restore_applied,
        "restore_min_alpha": restore_floor if restore_applied else None,
        "restore_applied": restore_applied,
        "selection_applied": selection_applied,
        "alpha_changed": alpha_changed,
        "alpha_extrema": checked["alpha_extrema"],
    }


def save_refined_png_atomic(
    png_bytes: object,
    gallery_dir: os.PathLike[str] | str,
    *,
    expected_size: Optional[tuple[int, int]] = None,
) -> Path:
    """Validate and atomically persist one refined PNG in its target directory."""

    checked = validate_refined_png(png_bytes, expected_size=expected_size)
    directory = Path(gallery_dir)
    temporary: Optional[Path] = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise OSError("gallery is not a directory")
        filename = (
            f"cutout_refined_{time.strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid.uuid4().hex[:12]}.png"
        )
        target = directory / filename
        temporary = directory / f".{filename}.{uuid.uuid4().hex}.tmp"
        with temporary.open("xb") as handle:
            handle.write(checked["bytes"])
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(target))
        return target
    except CutoutRefineError:
        raise
    except Exception:
        try:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        except OSError:
            pass
        raise CutoutRefinePersistenceError() from None


# Compatibility spelling for callers that naturally prefix the atomic action.
atomic_save_refined_png = save_refined_png_atomic


__all__ = [
    "CUTOUT_REFINE_CONTRACT",
    "CUTOUT_SELECTION_MASK_CONTRACT",
    "DEFAULT_FEATHER_RADIUS",
    "MAX_FEATHER_RADIUS",
    "MAX_REFINE_IMAGE_BYTES",
    "MAX_REFINE_OUTPUT_BYTES",
    "MAX_REFINE_PIXELS",
    "CutoutRefineError",
    "CutoutRefineInputError",
    "CutoutRefineOutputError",
    "CutoutRefinePersistenceError",
    "atomic_save_refined_png",
    "refine_cutout_alpha",
    "save_refined_png_atomic",
    "validate_refine_source",
    "validate_refined_png",
    "validate_selection_mask",
]
