"""Focused contracts for local, alpha-only cutout refinement."""

import base64
from io import BytesIO

import pytest
from PIL import Image

from image_tools.cutout_refine import (
    MAX_FEATHER_RADIUS,
    CutoutRefineInputError,
    CutoutRefinePersistenceError,
    refine_cutout_alpha,
    save_refined_png_atomic,
    validate_refine_source,
    validate_refined_png,
)


def _png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _data_url(raw: bytes, mime_type: str = "image/png") -> str:
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _source_png(size=(16, 10)) -> bytes:
    image = Image.new("RGBA", size, (24, 96, 180, 255))
    alpha = Image.new("L", size, 0)
    for x in range(size[0] // 2, size[0]):
        for y in range(size[1]):
            alpha.putpixel((x, y), 255)
    image.putalpha(alpha)
    return _png_bytes(image)


def _rgb_source_png(size=(16, 10)) -> bytes:
    image = Image.new("RGB", size, (200, 48, 88))
    return _png_bytes(image)


def _open_rgba(raw: bytes) -> Image.Image:
    with Image.open(BytesIO(raw)) as image:
        image.load()
        return image.copy()


def test_refine_blurs_only_alpha_and_preserves_rgb_dimensions_and_transparency():
    source = _source_png()
    original = _open_rgba(source)

    result = refine_cutout_alpha(_data_url(source), feather_radius=2)
    refined = _open_rgba(result["image_bytes"])

    assert refined.size == original.size
    assert refined.mode == "RGBA"
    assert refined.convert("RGB").tobytes() == original.convert("RGB").tobytes()
    assert refined.getchannel("A").tobytes() != original.getchannel("A").tobytes()
    assert refined.getchannel("A").getextrema()[0] < 255
    assert result["transparent"] is True
    assert result["alpha_changed"] is True
    assert result["selection_applied"] is False


def test_selection_mask_scopes_alpha_refinement():
    source = _source_png()
    original = _open_rgba(source).getchannel("A")
    mask = Image.new("L", original.size, 0)
    for x in range(original.width):
        for y in range(original.height // 2):
            mask.putpixel((x, y), 255)

    result = refine_cutout_alpha(
        base64.b64encode(source).decode("ascii"),
        selection_mask_data=_data_url(_png_bytes(mask)),
        feather_radius=2,
    )
    refined = _open_rgba(result["image_bytes"]).getchannel("A")

    lower_box = (0, original.height // 2, original.width, original.height)
    upper_box = (0, 0, original.width, original.height // 2)
    assert refined.crop(lower_box).tobytes() == original.crop(lower_box).tobytes()
    assert refined.crop(upper_box).tobytes() != original.crop(upper_box).tobytes()
    assert result["selection_applied"] is True


def test_rgba_selection_uses_its_alpha_channel_for_scope():
    source = _source_png()
    original = _open_rgba(source).getchannel("A")
    mask = Image.new("RGBA", original.size, (255, 255, 255, 0))
    for x in range(original.width):
        for y in range(original.height // 2):
            mask.putpixel((x, y), (0, 0, 0, 255))

    result = refine_cutout_alpha(
        source,
        selection_mask_data=_png_bytes(mask),
        feather_radius=2,
    )
    refined = _open_rgba(result["image_bytes"]).getchannel("A")

    selected_point = (original.width // 2 - 1, 1)
    unselected_point = (original.width // 2 - 1, original.height - 1)
    assert refined.getpixel(selected_point) != original.getpixel(selected_point)
    assert refined.getpixel(unselected_point) == original.getpixel(unselected_point)


def test_source_requires_actual_rgba_png_with_meaningful_alpha():
    rgb_png = _png_bytes(Image.new("RGB", (8, 6), (1, 2, 3)))
    with pytest.raises(CutoutRefineInputError) as wrong_mode:
        validate_refine_source(_data_url(rgb_png))
    assert wrong_mode.value.code == "source_image_mode_invalid"

    opaque_png = _png_bytes(Image.new("RGBA", (8, 6), (1, 2, 3, 255)))
    with pytest.raises(CutoutRefineInputError) as no_alpha:
        validate_refine_source(_data_url(opaque_png))
    assert no_alpha.value.code == "source_image_alpha_required"

    jpeg = BytesIO()
    Image.new("RGB", (8, 6), (1, 2, 3)).save(jpeg, format="JPEG")
    with pytest.raises(CutoutRefineInputError) as wrong_format:
        validate_refine_source(_data_url(jpeg.getvalue()))
    assert wrong_format.value.code == "source_image_format_invalid"


def test_mask_dimensions_and_feather_radius_fail_closed_with_safe_details():
    source = _source_png()
    wrong_size_mask = _png_bytes(Image.new("L", (5, 4), 255))
    with pytest.raises(CutoutRefineInputError) as wrong_size:
        refine_cutout_alpha(source, selection_mask_data=wrong_size_mask, feather_radius=1)
    assert wrong_size.value.code == "selection_mask_size_mismatch"
    assert wrong_size.value.to_detail()["expected_width"] == 16
    assert "image_data" not in str(wrong_size.value.to_detail())

    for invalid in (-0.01, MAX_FEATHER_RADIUS + 0.01, float("nan"), True, "secret-path.png"):
        with pytest.raises(CutoutRefineInputError) as radius_error:
            refine_cutout_alpha(source, feather_radius=invalid)
        assert radius_error.value.code == "feather_radius_invalid"
        assert "secret-path.png" not in str(radius_error.value.to_detail())

    jpeg_mask = BytesIO()
    Image.new("L", (16, 10), 255).save(jpeg_mask, format="JPEG")
    with pytest.raises(CutoutRefineInputError) as wrong_format:
        refine_cutout_alpha(source, selection_mask_data=jpeg_mask.getvalue(), feather_radius=1)
    assert wrong_format.value.code == "selection_mask_format_invalid"


def test_zero_radius_and_empty_selection_are_deterministic_noops():
    source = _source_png()
    empty_mask = _png_bytes(Image.new("L", (16, 10), 0))

    first = refine_cutout_alpha(source, selection_mask_data=empty_mask, feather_radius=3)
    second = refine_cutout_alpha(source, selection_mask_data=empty_mask, feather_radius=3)
    zero = refine_cutout_alpha(source, feather_radius=0)

    assert first["image_bytes"] == second["image_bytes"]
    assert first["alpha_changed"] is False
    assert _open_rgba(first["image_bytes"]).tobytes() == _open_rgba(source).tobytes()
    assert zero["alpha_changed"] is False


def test_restore_mode_lifts_alpha_only_inside_selection_and_uses_explicit_source():
    source = _source_png()
    restore_source = _rgb_source_png()
    original = _open_rgba(source)
    mask = Image.new("L", original.size, 0)
    for x in range(original.width):
        for y in range(original.height // 2):
            mask.putpixel((x, y), 255)

    result = refine_cutout_alpha(
        source,
        selection_mask_data=_data_url(_png_bytes(mask)),
        feather_radius=4,
        restore_mode=True,
        restore_source_image_data=_data_url(restore_source),
        restore_min_alpha=192,
    )
    refined = _open_rgba(result["image_bytes"]).getchannel("A")

    assert result["restore_applied"] is True
    assert result["selection_applied"] is True
    assert result["restore_min_alpha"] == 192
    selected_point = (original.width // 2, 1)
    unselected_point = (original.width // 2, original.height - 1)
    assert refined.getpixel(selected_point) >= 192
    assert refined.getpixel(unselected_point) == original.getchannel("A").getpixel(unselected_point)


def test_atomic_save_validates_and_replaces_from_same_directory(tmp_path):
    result = refine_cutout_alpha(_source_png(), feather_radius=2)
    gallery = tmp_path / "gallery"

    target = save_refined_png_atomic(result["image_bytes"], gallery, expected_size=(16, 10))

    assert target.parent == gallery
    assert target.name.startswith("cutout_refined_")
    assert target.suffix == ".png"
    assert target.exists()
    assert not list(gallery.glob("*.tmp"))
    checked = validate_refined_png(target.read_bytes(), expected_size=(16, 10))
    assert checked["transparent"] is True


def test_atomic_save_failure_is_sanitized_and_removes_temporary_file(tmp_path, monkeypatch):
    result = refine_cutout_alpha(_source_png(), feather_radius=2)
    gallery = tmp_path / "private-gallery"

    def fail_replace(_source, _target):
        raise OSError(f"synthetic private path {gallery}")

    monkeypatch.setattr("image_tools.cutout_refine.os.replace", fail_replace)
    with pytest.raises(CutoutRefinePersistenceError) as failure:
        save_refined_png_atomic(result["image_bytes"], gallery, expected_size=(16, 10))

    assert str(gallery) not in str(failure.value.to_detail())
    assert not list(gallery.glob("*.tmp"))
