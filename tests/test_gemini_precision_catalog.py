"""Native Gemini size catalog and explicit authorization lifecycle."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import main
from config import (
    GEMINI_NATIVE_IMAGE_MODELS,
    PrecisionEditProfile,
    ProviderConfig,
    gemini_precision_model_presets,
    gemini_precision_preset_for_size,
    normalize_precision_capability_size,
)


@pytest.fixture
def native_provider(monkeypatch):
    provider = ProviderConfig(
        id="synthetic-gemini",
        name="Synthetic Gemini",
        type="image",
        endpoint_type="gemini",
        base_url="https://example.invalid",
        api_key="synthetic-test-key",
        model="gemini-3.1-flash-image",
        models=list(sorted(GEMINI_NATIVE_IMAGE_MODELS)),
    )
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(
        config=SimpleNamespace(providers=[provider]),
        save=lambda config: saved.append(config),
    ))
    monkeypatch.setattr(main, "_write_log", lambda *args, **kwargs: None)
    return provider, saved


def confirm(provider, **kwargs):
    payload = {"model": provider.model, "enabled": True, "confirmed": True}
    payload.update(kwargs)
    return asyncio.run(main.set_precision_capability(
        provider.id, main.PrecisionCapabilityReq(**payload),
    ))


def assert_size_preflight(provider, size):
    main._validate_precision_edit_provider_authorization(
        [provider.id], {provider.id: provider},
        {provider.id: {"model": provider.model}},
    )
    main._validate_precision_edit_size_authorization(
        [provider.id], {provider.id: provider},
        {provider.id: {"model": provider.model}},
        {"precision_size_mode": "resize", "precision_target_size": size},
    )


def test_native_confirmation_does_not_rewrite_transport_or_grant_sizes(native_provider):
    provider, saved = native_provider
    confirm(provider)
    assert len(saved) == 1
    assert provider.endpoint_type == "gemini"
    assert provider.precision_edit_profile == PrecisionEditProfile.GEMINI_GENERATE_CONTENT
    record = provider.extra["model_capabilities"][provider.model]
    assert record == {"precision_edit": True}
    catalog = main._public_precision_size_catalog(provider)
    row = next(row for row in catalog if row["model"] == provider.model)
    assert row["precision_capability"]["status"] == "ready"
    assert not row["precision_capability"]["dispatch_authorized"]
    assert row["strict_selectable_sizes"] == []
    assert len(row["documented_presets"]) == 53


@pytest.mark.parametrize("model,size", [
    ("gemini-2.5-flash-image", "1344x768"),
    ("gemini-3-pro-image", "5504x3072"),
    ("gemini-3.1-flash-image", "2752x1536"),
])
def test_native_size_grant_is_required_and_scoped(native_provider, model, size):
    provider, _saved = native_provider
    provider.model = model
    confirm(provider)
    with pytest.raises(HTTPException):
        assert_size_preflight(provider, size)
    confirm(provider, size=size)
    assert_size_preflight(provider, size)
    record = provider.extra["model_capabilities"][model]
    assert record["supported_sizes"] == [size]
    assert len(provider.extra["model_capabilities"]) == 1
    other_provider = provider.model_copy(deep=True)
    other_provider.id = "another-synthetic-provider"
    other_provider.extra = {}
    with pytest.raises(HTTPException):
        assert_size_preflight(other_provider, size)
    confirm(provider, size=size, enabled=False)
    with pytest.raises(HTTPException):
        assert_size_preflight(provider, size)


def test_unmappable_size_never_authorized_or_submitted(native_provider):
    provider, saved = native_provider
    confirm(provider)
    with pytest.raises(HTTPException) as error:
        confirm(provider, size="1000x1000")
    assert error.value.detail["code"] == "gemini_precision_target_not_mappable"
    assert len(saved) == 1
    provider.extra["model_capabilities"][provider.model]["supported_sizes"] = ["1000x1000"]
    with pytest.raises(HTTPException) as error:
        assert_size_preflight(provider, "1000x1000")
    assert error.value.detail["providers"][0]["reason"] == "gemini_precision_target_not_mappable"


def test_unknown_native_model_cannot_be_confirmed(native_provider):
    provider, saved = native_provider
    provider.model = "nano-banana-custom"
    provider.models.append(provider.model)
    with pytest.raises(HTTPException) as error:
        confirm(provider)
    assert error.value.detail["code"] == "gemini_precision_model_unknown"
    assert not saved
    assert provider.endpoint_type == "gemini"


def test_native_flexible_gpt_policy_is_rejected(native_provider):
    provider, _saved = native_provider
    confirm(provider)
    with pytest.raises(HTTPException) as error:
        confirm(provider, flexible_sizes=True)
    assert error.value.detail["code"] == "gemini_precision_policy_invalid"


def test_native_profile_required_for_catalog_and_preflight(native_provider):
    provider, _saved = native_provider
    confirm(provider)
    confirm(provider, size="1024x1024")
    provider.precision_edit_profile = PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE
    with pytest.raises(HTTPException):
        assert_size_preflight(provider, "1024x1024")
    row = next(row for row in main._public_precision_size_catalog(provider) if row["model"] == provider.model)
    assert row["precision_capability"]["status"] == "unknown"
    assert row["strict_selectable_sizes"] == []


def test_native_presets_stay_within_safety_envelope_and_do_not_guess_names():
    for model in GEMINI_NATIVE_IMAGE_MODELS:
        presets = gemini_precision_model_presets(model)
        assert presets
        assert len({item["size"] for item in presets}) == len(presets)
        for preset in presets:
            assert normalize_precision_capability_size(preset["size"])
            assert gemini_precision_preset_for_size(model, preset["size"]) == preset
    assert gemini_precision_model_presets("nano-banana-2") == ()
    assert gemini_precision_model_presets("gemini-3.1-flash-image-preview") == ()
    assert gemini_precision_preset_for_size("gemini-3.1-flash-image", "1536x12288") is None
    assert gemini_precision_preset_for_size("gemini-3.1-flash-image", "792x168") is None


def test_model_specific_mapping_omits_25_image_size():
    flash = gemini_precision_preset_for_size("gemini-2.5-flash-image", "1344x768")
    assert flash["image_config"] == {"aspectRatio": "16:9"}
    pro = gemini_precision_preset_for_size("gemini-3-pro-image", "5504x3072")
    assert pro["image_config"] == {"aspectRatio": "16:9", "imageSize": "4K"}
