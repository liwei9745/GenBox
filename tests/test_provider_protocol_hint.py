"""Coverage for the advisory endpoint protocol hint in Provider settings."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_auto_protocol_hint_is_advisory_and_covers_common_gateway_shapes():
    source = (ROOT / "static/js/app-all.js").read_text(encoding="utf-8")
    assert "function inferProviderProtocol(baseUrl, model)" in source
    assert "generativelanguage.googleapis.com" in source
    assert "url.indexOf('/v1')" in source
    assert "var inferredProtocol = et === 'auto' ? inferProviderProtocol(p.base_url, p.model) : et;" in source
    assert 'class="provider-auto-protocol-hint"' in source
    assert "保存的端点类型仍保持 auto" in source
