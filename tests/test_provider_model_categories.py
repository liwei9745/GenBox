"""Provider model capability filters are present and preserve the selected model."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_provider_model_category_filter_is_rendered():
    source = (ROOT / "static/js/app-all.js").read_text(encoding="utf-8")
    assert "var providerModelCategoryFilters = {};" in source
    assert "function providerModelCategory(model, providerType)" in source
    assert "function getProviderModelCapabilityRecord(provider, model)" in source
    assert "record.image_generation === false" in source
    assert "record.video_generation === false" in source
    assert "ml.indexOf('gemini') === 0" in source
    assert "setProviderModelCategory(idx, category)" in source
    for label in ("全部", "图像", "视频", "文本", "多模态"):
        assert ">" + label + "</button>" in source
    assert "if (p.model && filteredModels.indexOf(p.model) === -1) filteredModels.unshift(p.model);" in source
