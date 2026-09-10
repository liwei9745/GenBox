"""Focused contract checks for strict precision resize dimensions."""

from pathlib import Path
import re

from config import gpt_image_2_size_error


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_exposes_strict_tier_ratio_linkage():
    source = (ROOT / "static/js/app-all.js").read_text(encoding="utf-8")
    assert "PRECISION_GPT_IMAGE_2_TIER_RATIOS" in source
    assert "function applyPrecisionResizeTierRatio" in source
    assert "precisionResizeTierRatioSize" in source
    html = (ROOT / "static/index.html").read_text(encoding="utf-8")
    assert 'id="precisionResizePreset"' in html
    # The compact selector combines tier and ratio into grouped size options.
    groups = re.findall(r'<optgroup label="模型尺寸 · ([124]K)" data-precision-resize-mode="strict">(.*?)</optgroup>', html)
    assert [tier for tier, _ in groups] == ["1K", "2K", "4K"]
    assert all(len(re.findall(r'<option value="\d+x\d+">', options)) == 9 for _, options in groups)


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


def test_published_precision_size_tables_match_presets():
    from genbox_version import __version__

    source = (ROOT / "static/js/app-all.js").read_text(encoding="utf-8")
    table = source.split("var PRECISION_GPT_IMAGE_2_TIER_RATIOS = {", 1)[1].split("\n};", 1)[0]
    tiers = re.findall(r"'[124]k': \{(.*?)\}", table, re.S)
    expected = [dict(re.findall(r"'([\d:]+)': '(\d+x\d+)'", tier)) for tier in tiers]
    for filename in ["README.md", "README_EN.md", f"release-notes-v{__version__}-zh.md", f"release-notes-v{__version__}.md"]:
        text = (ROOT / filename).read_text(encoding="utf-8")
        rows = re.findall(r"^\| (\d+:\d+)[^|]*\| (\d+ × \d+) \| (\d+ × \d+) \| (\d+ × \d+) \|$", text, re.M)
        assert len(rows) == 9, filename
        for ratio, *sizes in rows:
            assert [value.replace(" × ", "x") for value in sizes] == [tier[ratio] for tier in expected], (filename, ratio)
