"""Focused contract checks for strict precision resize dimensions."""

from pathlib import Path

from config import gpt_image_2_size_error


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_exposes_strict_tier_ratio_linkage():
    source = (ROOT / "static/js/app-all.js").read_text(encoding="utf-8")
    assert "PRECISION_GPT_IMAGE_2_TIER_RATIOS" in source
    assert "function applyPrecisionResizeTierRatio" in source
    assert "precisionResizeTierRatioSize" in source
    assert "id=\"precisionResizeTier\"" in (ROOT / "static/index.html").read_text(encoding="utf-8")
    assert "id=\"precisionResizeRatio\"" in (ROOT / "static/index.html").read_text(encoding="utf-8")


def test_all_builtin_tier_ratio_dimensions_obey_strict_envelope():
    source = (ROOT / "static/js/app-all.js").read_text(encoding="utf-8")
    table_start = source.index("var PRECISION_GPT_IMAGE_2_TIER_RATIOS")
    table_end = source.index("};", table_start) + 2
    table_sizes = set(__import__("re").findall(r"'([0-9]+x[0-9]+)'", source[table_start:table_end]))
    dimensions = {
        "1024x1024", "1168x656", "656x1168", "1024x768", "768x1024",
        "1008x672", "672x1008", "1344x576", "576x1344",
        "2048x2048", "2048x1152", "1152x2048", "2048x1536", "1536x2048",
        "2016x1344", "1344x2016", "2544x1088", "1088x2544",
        "2880x2880", "3840x2160", "2160x3840", "3328x2480", "2480x3328",
        "3520x2352", "2352x3520", "3840x1648", "1648x3840",
    }
    assert table_sizes == dimensions
    for size in dimensions:
        assert gpt_image_2_size_error(size) is None, size


def test_strict_envelope_rejects_alignment_side_pixels_and_ratio_violations():
    cases = {
        "1025x1024": "precision_target_size_alignment_invalid",
        "3856x2160": "precision_target_size_side_exceeded",
        "16x4096": "precision_target_size_side_exceeded",
        "640x640": "precision_target_size_pixels_too_small",
        "3840x3840": "precision_target_size_pixels_exceeded",
        "4000x1000": "precision_target_size_side_exceeded",
    }
    for size, code in cases.items():
        error = gpt_image_2_size_error(size)
        assert error is not None and error[0] == code, (size, error)
