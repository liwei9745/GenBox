"""Synthetic aggregate-provider protocol isolation and dispatch contracts."""
import asyncio
import base64
import json
from io import BytesIO

import httpx
import pytest
from PIL import Image

import providers
from config import (
    EndpointConfig,
    PrecisionEditProfile,
    ProviderConfig,
    normalize_precision_model_override,
    precision_size_model,
    resolve_precision_provider,
    precision_connection_info,
    precision_automatic_connection_info,
    precision_documented_gateway_recipe,
    documented_precision_provider_size_presets,
    resolve_image_protocol,
)


MODEL = "nano-banana-2-2k"
FAMILY = "gemini-3.1-flash-image"


def _provider(protocol="gemini"):
    return ProviderConfig(
        id="synthetic-aggregate", name="Synthetic aggregate", type="image",
        api_key="synthetic-key", base_url="https://provider.example.test/v1",
        model="gpt-image-2.5-c", endpoint_type="openai",
        precision_edit_profile=PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE,
        capabilities={"precision_edit": True},
        extra={
            "model_capabilities": {
                "gpt-image-2.5-c": {"precision_edit": True, "supported_sizes": ["1024x1024"]},
                MODEL: {"alias_of": "gpt-image-2.5-c"},
            },
            "precision_model_overrides": {MODEL: {
                "protocol": protocol, "size_model": FAMILY,
                "capabilities": {"precision_edit": True, "supported_sizes": ["2752x1536"]},
            }},
        },
    )


def _image(size):
    output = BytesIO()
    Image.new("RGB", size, (20, 90, 150)).save(output, "PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def _kwargs():
    return {
        "model": MODEL, "mode": "precision_edit",
        "precision_edit_authorized": True, "precision_canvas_only": True,
        "precision_size_mode": "resize", "precision_target_size": "2752x1536",
        "precision_resize_prompt": "Extend the background.",
        "precision_output_size_policy": "strict",
        "image_data": "data:image/png;base64," + _image((1024, 1024)),
    }


def test_resolution_is_deeply_isolated_and_idempotent():
    cfg = _provider()
    before = cfg.model_dump()
    effective = resolve_precision_provider(cfg, MODEL)
    assert effective is not cfg
    assert effective.endpoint_type == "gemini"
    assert effective.model == "gpt-image-2.5-c"
    assert resolve_precision_provider(effective, MODEL) is effective
    assert "precision_model_overrides" not in effective.extra
    assert effective.extra["model_capabilities"][MODEL] == {
        "precision_edit": True, "supported_sizes": ["2752x1536"],
    }
    effective.extra["model_capabilities"]["gpt-image-2.5-c"]["supported_sizes"].append("2048x2048")
    assert cfg.model_dump() == before


def test_gpt_and_case_mismatch_keep_default_configuration():
    cfg = _provider()
    assert resolve_precision_provider(cfg, cfg.model) is cfg
    assert resolve_precision_provider(cfg, MODEL.upper()) is cfg
    assert precision_size_model(cfg, cfg.model) == cfg.model


@pytest.mark.parametrize("protocol", ["openai", "gemini"])
def test_size_family_independent_of_transport_and_grants(protocol):
    cfg = _provider(protocol)
    effective = resolve_precision_provider(cfg, MODEL)
    assert precision_size_model(cfg, MODEL) == FAMILY
    assert precision_size_model(effective, MODEL) == FAMILY
    resolution = providers.resolve_provider_precision_model_capability(cfg, MODEL)
    assert resolution.canonical_model == MODEL
    assert resolution.supported_sizes == ("2752x1536",)
    assert "1024x1024" not in resolution.supported_sizes
    assert not providers.precision_model_uses_gpt_image_2_size_contract(cfg, MODEL)
    assert providers._gemini_precision_native_size(effective, MODEL, "2752x1536") == {
        "aspectRatio": "16:9", "imageSize": "2K",
    }


def test_new_override_does_not_inherit_old_authorization():
    cfg = _provider()
    cfg.extra["precision_model_overrides"][MODEL].pop("capabilities")
    resolution = providers.resolve_provider_precision_model_capability(cfg, MODEL)
    assert not resolution.precision_edit_confirmed
    assert not resolution.supported_sizes


@pytest.mark.parametrize("changes", [
    {"protocol": "qwen"},
    {"protocol": "openai", "profile": "gemini_generate_content"},
    {"profile": "invented_json"},
    {"size_model": "nano-banana-2-2k"},
    {"size_model": []},
    {"capabilities": {"alias_of": "gpt-image-2"}},
    {"capabilities": {"precision_edit": "true"}},
    {"capabilities": {"supported_sizes": ["bad-size"]}},
])
def test_invalid_override_fails_closed(changes):
    value = {"protocol": "gemini"}
    value.update(changes)
    with pytest.raises(ValueError):
        normalize_precision_model_override(value)


@pytest.mark.parametrize("protocol", ["openai", "gemini"])
@pytest.mark.parametrize("status", [200, 400, 503])
def test_aggregate_dispatch_preserves_model_and_single_post(monkeypatch, tmp_path, protocol, status):
    calls = []
    output = _image((2752, 1536))
    response = (
        {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": output}},
        ]}}]}
        if protocol == "gemini"
        else {"data": [{"b64_json": output}]}
    )
    client_type = httpx.AsyncClient

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json=response if status == 200 else {"error": {"message": "synthetic failure"}})

    def client(**kwargs):
        kwargs.pop("proxy", None)
        return client_type(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client)
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)
    cfg = _provider(protocol)
    cfg.endpoints = [
        EndpointConfig(url=cfg.base_url, key="synthetic-key"),
        EndpointConfig(url="https://second.example.test/v1", key="synthetic-key-2"),
    ]
    before = cfg.model_dump()
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic test", **_kwargs()))
    assert result.success is (status == 200), result.error
    assert len(calls) == 1
    assert cfg.model_dump() == before
    if protocol == "gemini":
        assert str(calls[0].url) == f"https://provider.example.test/v1beta/models/{MODEL}:generateContent"
        payload = json.loads(calls[0].content)
        assert payload["generationConfig"]["imageConfig"] == {"aspectRatio": "16:9", "imageSize": "2K"}
    else:
        assert str(calls[0].url) == "https://provider.example.test/v1/images/edits"
        assert MODEL.encode() in calls[0].content
        assert b"2752x1536" in calls[0].content
        assert FAMILY.encode() not in calls[0].content
        assert "multipart/form-data" in calls[0].headers["content-type"]


def test_invalid_override_fails_before_request(monkeypatch):
    def no_http(**kwargs):
        pytest.fail("invalid override must not instantiate an HTTP client")

    monkeypatch.setattr(providers.httpx, "AsyncClient", no_http)
    cfg = _provider()
    cfg.extra["precision_model_overrides"][MODEL]["protocol"] = "unknown"
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic test", **_kwargs()))
    assert result.error_code == "precision_protocol_override_invalid"


def test_auto_recipe_has_no_grants_and_does_not_change_gpt():
    cfg = _provider()
    cfg.extra.pop("precision_model_overrides")
    cfg.base_url = "https://api.velapi.cc/v1"
    before = cfg.model_dump()
    effective = resolve_precision_provider(cfg, MODEL)
    assert effective.endpoint_type == "openai"
    assert effective.precision_edit_profile.value == "openai_images_edits_json_data_url_single_source_image"
    assert effective.extra["model_capabilities"] == cfg.extra["model_capabilities"]
    assert resolve_precision_provider(effective, MODEL) is effective
    assert resolve_precision_provider(cfg, cfg.model) is cfg
    assert cfg.model_dump() == before
    presets = documented_precision_provider_size_presets(cfg, MODEL)
    assert len(presets) == 14
    assert {item["tier"] for item in presets} == {"2K"}
    assert len({item["ratio"] for item in presets}) == 14
    assert sum(item["gateway_declared_candidate"] for item in presets) == 5
    assert {
        item["ratio"] for item in presets if item["gateway_declared_candidate"]
    } == {"1:1", "16:9", "9:16", "3:4", "4:3"}
    assert all(item["official_model_candidate"] for item in presets)
    assert all(item["experimental"] for item in presets)
    assert {item["evidence"] for item in presets} == {
        "gateway_documented_candidate", "official_model_candidate",
    }


@pytest.mark.parametrize(
    ("model", "expected_count"),
    [
        ("nano-banana-2-2k", 14),
        ("nano-banana-pro-2k", 8),
    ],
)
def test_gateway_catalog_keeps_complete_native_family_for_exact_alias(model, expected_count):
    cfg = _provider()
    cfg.base_url = "https://api.velapi.cc/v1"
    presets = documented_precision_provider_size_presets(cfg, model)
    assert len(presets) == expected_count
    assert len({item["ratio"] for item in presets}) == expected_count
    assert all(item["tier"] == "2K" for item in presets)
    declared_count = 5 if model == "nano-banana-2-2k" else 3
    assert sum(item["gateway_declared_candidate"] for item in presets) == declared_count
    assert all(item["official_model_candidate"] for item in presets)


@pytest.mark.parametrize("url", [
    "https://api.velapi.cc.example.test/v1", "http://api.velapi.cc/v1",
    "https://api.velapi.cc:8443/v1", "https://api.velapi.cc/v1?key=synthetic-key",
    "https://synthetic-key@api.velapi.cc/v1", "https://api.velapi.cc/custom",
])
def test_auto_recipe_requires_exact_safe_origin_and_route(url):
    cfg = _provider()
    cfg.base_url = url
    assert precision_documented_gateway_recipe(cfg, MODEL) == {}


def test_observed_size_warnings_are_scoped_without_capping_4k_sides():
    cfg = _provider()
    cfg.base_url = "https://api.klong.lat/v1"
    cfg.extra.pop("precision_model_overrides", None)
    before = cfg.model_dump()
    presets = {p["size"]: p for p in documented_precision_provider_size_presets(cfg, "nano-banana2")}
    assert presets["6144x768"]["reliability_warning"] == "observed_geometry_mismatch"
    assert presets["2048x8192"]["reliability_warning"] == "observed_output_safety_limit"
    assert presets["3392x5056"]["reliability_warning"] == ""
    assert presets["5504x3072"]["tier"] == "4K"
    assert cfg.model_dump() == before
    for model in ("nano-banana-pro", "gpt-image-2"):
        assert not any(p["reliability_warning"] for p in documented_precision_provider_size_presets(cfg, model))
    cfg.base_url = "https://api.velapi.cc/v1"
    assert not any(p["reliability_warning"] for p in documented_precision_provider_size_presets(cfg, MODEL))


def test_auto_recipe_rejects_mixed_active_endpoints():
    cfg = _provider()
    cfg.base_url = "https://api.velapi.cc/v1"
    cfg.endpoints = [
        EndpointConfig(url=cfg.base_url, key="synthetic-key"),
        EndpointConfig(url="https://unknown.example.test/v1", key="synthetic-key-two"),
    ]
    assert precision_documented_gateway_recipe(cfg, MODEL) == {}


def test_manual_priority_and_auto_default_json_are_separate():
    cfg = _provider()
    cfg.base_url = "https://api.velapi.cc/v1"
    assert precision_connection_info(cfg, MODEL)["protocol"] == "gemini"
    assert precision_automatic_connection_info(cfg, MODEL)["protocol"] == "openai"
    cfg.extra["precision_model_overrides"][MODEL]["protocol"] = "openai"
    effective = resolve_precision_provider(cfg, MODEL)
    assert effective.precision_edit_profile.value == "openai_images_edits_json_data_url_single_source_image"
    info = precision_connection_info(cfg, MODEL)
    assert info["source"] == "manual"
    assert info["automatic"]["source"] == "gateway_documentation"
    assert cfg.api_key not in json.dumps(info)
    assert "api.velapi.cc" not in json.dumps(info)


@pytest.mark.parametrize("model,family", [
    ("nano-banana2", "gemini-3.1-flash-image"),
    ("nano-banana-pro", "gemini-3-pro-image"),
])
def test_klong_exact_alias_does_not_rewrite_outbound_model(model, family):
    cfg = _provider()
    cfg.base_url = "https://api.klong.lat/v1"
    info = precision_automatic_connection_info(cfg, model)
    assert info["protocol"] == "openai"
    assert info["size_model"] == family
    assert info["profile"] == "openai_images_edits_multipart_single_source_image"
    assert precision_documented_gateway_recipe(cfg, model.upper()) == {}
    assert precision_documented_gateway_recipe(cfg, "gemini-3.1-flash-image-preview") == {}


@pytest.mark.parametrize("url,model,protocol", [
    ("https://provider.example.test/v1", "gpt-image-2", "openai"),
    ("https://generativelanguage.googleapis.com", "gemini-3.1-flash-image", "gemini"),
])
def test_auto_endpoint_resolves_supported_adapter_without_mutation(url, model, protocol):
    cfg = ProviderConfig(id="synthetic", name="Synthetic", type="image", base_url=url, model=model)
    effective = resolve_precision_provider(cfg, model)
    assert effective.endpoint_type == protocol
    assert effective.precision_edit_profile
    assert resolve_image_protocol(cfg) == providers._detect_protocol(cfg) == protocol
    assert cfg.endpoint_type == "auto"
