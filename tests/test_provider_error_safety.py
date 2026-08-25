"""Safety and regressions for provider-level error text and generation logging.

These tests do not touch the network. They cover the two production defects
reported against packaged GenBox:
- ``_safe_text`` must never raise ``UnicodeEncodeError: 'ascii'`` and must
  preserve non-ASCII body text instead of dropping it.
- The image-generation error log path in ``main.py`` must not reference an
  undefined ``cfg`` symbol (``NameError: name 'cfg' is not defined``).
"""
from __future__ import annotations

import pytest


def test_safe_text_never_raises_ascii_codec_error():
    from providers import _safe_text

    for value in (
        "plain ascii",
        "中文错误信息",
        "\ud83d\udd00 开始生成 - 模型: GPT Image 2",
        "Invalid token (request id: 1234)",  # upstream style
        None,
        401,
        b"raw bytes",
    ):
        out = _safe_text(value)
        assert isinstance(out, str)
        # Round-trip through an ascii-only sink must not raise.
        assert out.encode("utf-8").decode("utf-8") == out


def test_safe_text_preserves_non_ascii_text():
    from providers import _safe_text

    source = "所有端点均失败: API Key 无效"
    assert _safe_text(source) == source


def test_safe_text_replaces_unrenderable_bytes_without_dropping_info():
    from providers import _safe_text

    value = "前缀: " + "\xff\xfe" + " 后缀"
    out = _safe_text(value)
    assert "前缀" in out
    assert "后缀" in out


def test_generation_error_log_uses_p_cfg_not_undefined_cfg():
    """The generation error writer must reference the in-scope provider cfg.

    Regression: main.py previously used ``cfg.model`` where ``cfg`` was not
    defined in ``_process_image_gen``, surfacing as
    ``NameError: name 'cfg' is not defined`` on every failed provider run.
    """
    source = _read_main()
    assert "generation_error" in source
    block = source.split('"generation_error"', 1)[1].split("state[\"result\"]", 1)[0]
    assert "p_cfg.model" in block
    # Reject a bare undefined ``cfg`` read (e.g. ``= cfg.model``), but allow
    # the in-scope ``p_cfg.model`` expression used in the fix.
    assert "= cfg.model" not in block


def test_generation_quantity_normalizes_invalid_and_stale_values():
    from main import _normalize_generation_quantity

    assert _normalize_generation_quantity(1) == 1
    assert _normalize_generation_quantity("3") == 3
    assert _normalize_generation_quantity(0) == 1
    assert _normalize_generation_quantity("not-a-number") == 1
    assert _normalize_generation_quantity(99) == 10


def _read_main() -> str:
    import pathlib

    return pathlib.Path(__file__).parents[1].joinpath("main.py").read_text(encoding="utf-8")
