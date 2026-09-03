"""Route contracts for local alpha-only cutout refinement."""

import base64
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

import main


def _png_data_url(image: Image.Image) -> str:
    output = BytesIO()
    image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _source_image(size=(16, 10)) -> Image.Image:
    image = Image.new("RGBA", size, (24, 96, 180, 255))
    alpha = Image.new("L", size, 0)
    for x in range(size[0] // 2, size[0]):
        for y in range(size[1]):
            alpha.putpixel((x, y), 255)
    image.putalpha(alpha)
    return image


def _restore_source_image(size=(16, 10)) -> Image.Image:
    return Image.new("RGB", size, (220, 48, 120))


def _selection_mask(size=(16, 10)) -> Image.Image:
    mask = Image.new("L", size, 0)
    for x in range(size[0]):
        for y in range(size[1] // 2):
            mask.putpixel((x, y), 255)
    return mask


def _client() -> TestClient:
    return TestClient(main.app, base_url="http://testserver")


def test_cutout_refine_route_persists_new_rgba_version_without_flattening(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    response = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-refine-v1",
            "image_data": _png_data_url(_source_image()),
            "selection_mask_data": _png_data_url(_selection_mask()),
            "selection_mask_contract": "genbox-cutout-selection-mask-v1",
            "feather_radius": 2,
            "parent_version_id": "version-17",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract"] == "genbox-cutout-refine-v1"
    assert payload["transparent"] is True
    assert payload["preview_background"] == "checkerboard"
    assert payload["source_preserved"] is True
    assert payload["selection_applied"] is True
    assert payload["selection_mask_contract"] == "genbox-cutout-selection-mask-v1"
    assert payload["parent_version_id"] == "version-17"
    assert payload["version_id"].startswith("cutout-refine-")
    assert "local_path" not in payload

    saved = tmp_path / payload["filename"]
    assert saved.is_file()
    assert payload["gallery_url"].endswith(payload["filename"])
    response_bytes = base64.b64decode(payload["image_data"].split(",", 1)[1])
    assert saved.read_bytes() == response_bytes
    with Image.open(BytesIO(response_bytes)) as refined:
        refined.load()
        assert refined.mode == "RGBA"
        assert refined.size == (16, 10)
        alpha_extrema = refined.getchannel("A").getextrema()
        assert alpha_extrema[0] < 255
        assert alpha_extrema[1] > 0


def test_cutout_refine_route_rejects_partial_or_unknown_selection_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    base = {
        "contract": "genbox-cutout-refine-v1",
        "image_data": _png_data_url(_source_image()),
        "feather_radius": 1,
    }

    partial = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={**base, "selection_mask_data": _png_data_url(_selection_mask())},
    )
    assert partial.status_code == 422
    assert partial.json()["detail"]["code"] == "cutout_refine_selection_fields_conflict"

    unknown = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            **base,
            "selection_mask_data": _png_data_url(_selection_mask()),
            "selection_mask_contract": "unknown-selection-v9",
        },
    )
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "cutout_refine_selection_contract_unsupported"

    empty = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            **base,
            "selection_mask_data": None,
            "selection_mask_contract": "genbox-cutout-selection-mask-v1",
        },
    )
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "cutout_refine_selection_mask_required"
    assert list(tmp_path.iterdir()) == []


def test_cutout_refine_route_rejects_invalid_source_and_bounds_before_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    rgb_source = _png_data_url(Image.new("RGB", (8, 6), (1, 2, 3)))
    invalid_source = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-refine-v1",
            "image_data": rgb_source,
            "feather_radius": 1,
        },
    )
    assert invalid_source.status_code == 422
    assert invalid_source.json()["detail"]["code"] == "source_image_mode_invalid"

    excessive_feather = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-refine-v1",
            "image_data": _png_data_url(_source_image()),
            "feather_radius": main.MAX_FEATHER_RADIUS + 1,
        },
    )
    assert excessive_feather.status_code == 422
    assert excessive_feather.json()["detail"]["code"] == "feather_radius_invalid"

    unsafe_parent = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-refine-v1",
            "image_data": _png_data_url(_source_image()),
            "parent_version_id": "../../private/source.png",
        },
    )
    assert unsafe_parent.status_code == 422
    assert unsafe_parent.json()["detail"]["code"] == "cutout_refine_parent_version_invalid"
    assert list(tmp_path.iterdir()) == []


def test_cutout_refine_route_restore_mode_requires_explicit_source_and_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    base = {
        "contract": "genbox-cutout-refine-v1",
        "image_data": _png_data_url(_source_image()),
        "feather_radius": 2,
    }

    missing_source = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={**base, "restore_mode": True, "selection_mask_data": _png_data_url(_selection_mask()), "selection_mask_contract": "genbox-cutout-selection-mask-v1"},
    )
    assert missing_source.status_code == 422
    assert missing_source.json()["detail"]["code"] == "cutout_refine_restore_source_required"

    orphan_source = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={**base, "restore_source_image_data": _png_data_url(_restore_source_image())},
    )
    assert orphan_source.status_code == 422
    assert orphan_source.json()["detail"]["code"] == "cutout_refine_restore_fields_conflict"

    missing_selection = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            **base,
            "restore_mode": True,
            "restore_source_image_data": _png_data_url(_restore_source_image()),
        },
    )
    assert missing_selection.status_code == 422
    assert missing_selection.json()["detail"]["code"] == "cutout_refine_restore_selection_mask_required"


def test_cutout_refine_route_restore_mode_lifts_alpha_only_inside_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    response = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-refine-v1",
            "image_data": _png_data_url(_source_image()),
            "restore_mode": True,
            "restore_source_image_data": _png_data_url(_restore_source_image()),
            "selection_mask_data": _png_data_url(_selection_mask()),
            "selection_mask_contract": "genbox-cutout-selection-mask-v1",
            "feather_radius": 4,
            "restore_min_alpha": 196,
            "parent_version_id": "version-17",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["restore_applied"] is True
    assert payload["selection_applied"] is True
    assert payload["restore_min_alpha"] == 196
    saved = tmp_path / payload["filename"]
    assert saved.is_file()
    with Image.open(BytesIO(base64.b64decode(payload["image_data"].split(",", 1)[1]))) as restored:
        restored.load()
        alpha = restored.getchannel("A")
        assert alpha.getpixel((3, 1)) >= 196
        assert alpha.getpixel((3, 9)) == 0
        assert restored.mode == "RGBA"


def test_cutout_refine_route_sanitizes_unexpected_runtime_error(tmp_path, monkeypatch):
    internal_path = Path(tmp_path) / "private-source.png"

    def fail_refine(*_args, **_kwargs):
        raise RuntimeError(f"synthetic failure at {internal_path}")

    monkeypatch.setattr(main, "refine_cutout_alpha", fail_refine)
    response = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-refine-v1",
            "image_data": _png_data_url(_source_image()),
        },
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "cutout_refine_failed"
    assert str(internal_path) not in str(detail)


def test_cutout_refine_route_rejects_malformed_internal_result_before_save(monkeypatch):
    monkeypatch.setattr(main, "refine_cutout_alpha", lambda *_args, **_kwargs: {"image_bytes": b"not-png"})
    save_calls = []
    monkeypatch.setattr(
        main,
        "save_refined_png_atomic",
        lambda *_args, **_kwargs: save_calls.append(True),
    )

    response = _client().post(
        "/api/image-tools/cutout/refine",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-refine-v1",
            "image_data": _png_data_url(_source_image()),
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "cutout_refine_output_invalid"
    assert save_calls == []
