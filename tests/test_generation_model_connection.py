"""Offline request-model, connection isolation and diagnostic regressions."""

import asyncio
import base64
import copy
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image

import main
import providers
from config import PrecisionEditProfile, ProviderConfig


MODEL = "nano-banana-2-2k"
GPT = "gpt-image-2.5-c"


def _provider():
    return ProviderConfig(
        id="synthetic-aggregate", name="Synthetic aggregate", type="image",
        api_key="synthetic-key", base_url="https://gateway.example.test/v1",
        model=GPT, models=[GPT, MODEL], enabled=True, endpoint_type="openai",
        precision_edit_profile=PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE,
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {
            GPT: {"precision_edit": True, "supported_sizes": ["1024x1024"]},
            MODEL: {"precision_edit": True, "supported_sizes": ["2048x2048"]},
        }},
    )


def _source():
    buffer = BytesIO()
    Image.new("RGB", (16, 16), (32, 96, 160)).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    provider = _provider()
    saves = []
    config = SimpleNamespace(providers=[provider])
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(
        config=config, save=lambda value: saves.append(value),
        get_image_providers=lambda: [provider],
    ))
    monkeypatch.setattr(main, "LOG_FILE", tmp_path / "logs.jsonl")
    monkeypatch.setattr(main, "HISTORY_FILE", tmp_path / "history.jsonl")
    monkeypatch.setattr(main, "image_tasks", {})
    monkeypatch.setattr(main, "image_task_handles", {})
    monkeypatch.setattr(main, "generation_history", {})
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_prepare_precision_workflow_metadata", lambda *_args: {})

    async def no_generation(_generation_id):
        pass

    monkeypatch.setattr(main, "_process_image_gen", no_generation)
    return provider, saves


def _queue(provider, mode="t2i", **overrides):
    values = {
        "mode": mode, "prompt": "Synthetic edit",
        "providers": [provider.id],
        "provider_settings": {provider.id: {"model": MODEL}},
    }
    if mode == "i2i":
        values["image_data"] = _source()
    if mode == "precision_edit":
        values.update(
            image_data=_source(), precision_size_mode="resize",
            precision_target_size="2048x2048",
            precision_resize_prompt="Extend the background.",
        )
    values.update(overrides)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    result = asyncio.run(main.generate(main.GenerateRequest(**values), request))
    return main.image_tasks[result["generation_id"]]


@pytest.mark.parametrize("mode", ["t2i", "i2i"])
def test_selected_generation_model_is_forwarded_without_changing_default(runtime, mode):
    provider, _ = runtime
    before = copy.deepcopy(provider.model_dump())
    task = _queue(provider, mode)
    assert task["provider_kwargs_map"][provider.id]["model"] == MODEL
    assert provider.model_dump() == before


def test_generation_default_remains_when_no_model_was_selected(runtime):
    provider, _ = runtime
    task = _queue(provider, provider_settings={})
    assert "model" not in task["provider_kwargs_map"][provider.id]
    assert task["all_providers"][provider.id].model == GPT


@pytest.mark.parametrize("model", ["unconfigured-model", "", None, 123, ["invalid"]])
def test_unconfigured_or_malformed_generation_model_cannot_queue(runtime, model):
    provider, _ = runtime
    with pytest.raises(HTTPException) as caught:
        _queue(provider, provider_settings={provider.id: {"model": model}})
    assert caught.value.detail["code"] == "generation_model_invalid"
    assert not main.image_tasks


@pytest.mark.parametrize("mode", ["t2i", "precision_edit"])
def test_queued_configuration_is_frozen_before_shared_settings_change(runtime, mode):
    provider, _ = runtime
    task = _queue(provider, mode)
    snapshot = task["all_providers"][provider.id]
    provider.model = "changed-later"
    provider.extra["model_capabilities"][MODEL]["supported_sizes"].clear()
    provider.endpoint_type = "gemini"
    assert snapshot is not provider
    assert snapshot.model == GPT
    assert snapshot.endpoint_type == "openai"
    assert snapshot.extra["model_capabilities"][MODEL]["supported_sizes"] == ["2048x2048"]


def test_protocol_candidate_validation_happens_before_config_mutation(runtime, monkeypatch):
    provider, saves = runtime
    before = copy.deepcopy(provider.model_dump())

    def invalid_candidate(_provider):
        raise ValueError("Synthetic catalog validation failure")

    monkeypatch.setattr(main, "_public_precision_size_catalog", invalid_candidate)
    with pytest.raises(ValueError):
        asyncio.run(main.set_precision_protocol(provider.id, main.PrecisionProtocolReq(
            model=MODEL, protocol="openai", confirmed=True,
        )))
    assert provider.model_dump() == before
    assert not saves


def test_failed_protocol_save_restores_previous_in_memory_configuration(runtime, monkeypatch):
    provider, _ = runtime
    before = copy.deepcopy(provider.model_dump())

    def save_failure(_config):
        raise OSError("Synthetic save failure")

    monkeypatch.setattr(main.cfg_mgr, "save", save_failure)
    with pytest.raises(OSError):
        asyncio.run(main.set_precision_protocol(provider.id, main.PrecisionProtocolReq(
            model=MODEL, protocol="openai", confirmed=True,
        )))
    assert provider.model_dump() == before


def test_provider_form_preserves_model_overrides_when_not_part_of_form(runtime):
    provider, _ = runtime
    provider.extra["precision_model_overrides"] = {
        MODEL: {"protocol": "openai", "capabilities": {"precision_edit": False}},
    }
    req = main.ProviderCreateReq(
        id=provider.id, name=provider.name, type="image", model=GPT, extra={},
    )
    payload = main._merge_provider_secrets(provider, req)
    assert payload["extra"]["precision_model_overrides"] == provider.extra["precision_model_overrides"]
    payload["extra"]["precision_model_overrides"][MODEL]["protocol"] = "gemini"
    assert provider.extra["precision_model_overrides"][MODEL]["protocol"] == "openai"


def test_catalog_resolves_each_model_independently_after_override(runtime):
    provider, _ = runtime
    provider.models = [MODEL, GPT]
    provider.extra["precision_model_overrides"] = {MODEL: {
        "protocol": "gemini", "size_model": "gemini-3.1-flash-image",
        "capabilities": {"precision_edit": True, "supported_sizes": ["2752x1536"]},
    }}
    before = copy.deepcopy(provider.model_dump())
    catalog = {item["model"]: item for item in main._public_precision_size_catalog(provider)}
    assert catalog[MODEL]["precision_capability"]["protocol"] == "gemini"
    assert catalog[MODEL]["strict_selectable_sizes"] == ["2752x1536"]
    assert catalog[GPT]["precision_capability"]["protocol"] == "openai"
    assert catalog[GPT]["strict_selectable_sizes"] == ["1024x1024"]
    assert provider.model_dump() == before


@pytest.mark.parametrize("outcome", ["success", "error", "exception"])
def test_dispatch_log_and_history_include_selected_model_not_provider_default(runtime, monkeypatch, outcome):
    provider, _ = runtime
    logs = []
    persisted = []
    monkeypatch.setattr(main, "_write_log", lambda category, message, details=None: logs.append(
        {"category": category, "message": message, "details": details}
    ))
    monkeypatch.setattr(main, "_save_history_entry", lambda entry: persisted.append(entry))

    async def fake_generate(cfg, prompt, **kwargs):
        assert kwargs["model"] == MODEL
        if outcome == "exception":
            raise RuntimeError("Synthetic failure")
        return providers.ImageResult(
            success=outcome == "success", model=cfg.id,
            image_data=base64.b64decode(_source().split(",", 1)[1]) if outcome == "success" else None,
            error="Synthetic failure" if outcome == "error" else None,
        )

    monkeypatch.setattr(providers, "generate_for_provider", fake_generate)
    task = _queue(provider)
    gen_id = next(key for key, value in main.image_tasks.items() if value is task)
    asyncio.run(main._process_image_gen_impl(gen_id))
    contract = task["results"][provider.id]["request_contract"]
    assert contract["model"] == MODEL
    assert contract["protocol"] == "openai"
    assert contract["route"] == "/images/generations"
    assert contract["evidence"] == "resolved_configuration"
    if outcome == "success":
        assert contract["actual_size"] == "16x16"
    assert persisted[0]["results"][provider.id]["request_contract"] == contract
    for entry in logs:
        if entry["category"] in {"generation_dispatch", "generation_error"}:
            assert entry["details"]["model"] == MODEL
    assert provider.api_key not in str(logs)
    assert provider.base_url not in str(logs)
    assert "Synthetic edit" not in str(logs)


def test_request_contract_redacts_configured_secret_even_if_misused_as_model(runtime):
    provider, _ = runtime
    contract = main._generation_request_contract(provider, "t2i", {"model": provider.api_key})
    assert provider.api_key not in str(contract)


def test_t2i_contract_distinguishes_user_target_from_default_request_size(runtime):
    provider, _ = runtime
    provider.size = "2048x2048"
    contract = main._generation_request_contract(provider, "t2i", {"model": MODEL})
    assert contract["target_size"] is None
    assert contract["request_size"] == "2048x2048"


def test_documented_gateway_catalog_and_manual_reset_preserve_gpt(runtime):
    provider, _ = runtime
    provider.base_url = "https://api.velapi.cc/v1"
    gpt_capability = copy.deepcopy(provider.extra["model_capabilities"][GPT])
    catalog = {item["model"]: item for item in main._public_precision_size_catalog(provider)}
    nano = catalog[MODEL]
    assert nano["precision_connection"]["protocol"] == "openai"
    assert nano["precision_connection"]["profile"] == "openai_images_edits_json_data_url_single_source_image"
    assert nano["precision_connection"]["source"] == "gateway_documentation"
    assert {item["tier"] for item in nano["documented_presets"]} == {"2K"}
    assert nano["strict_selectable_sizes"] == ["2048x2048"]
    assert "1024x1024" not in nano["strict_selectable_sizes"]

    applied = asyncio.run(main.set_precision_protocol(provider.id, main.PrecisionProtocolReq(
        model=MODEL, protocol="openai", confirmed=True,
    )))
    assert applied["catalog"]["precision_connection"]["profile"] == nano["precision_connection"]["profile"]
    assert applied["catalog"]["precision_capability"]["status"] == "unknown"
    assert not applied["catalog"]["strict_selectable_sizes"]
    restored = asyncio.run(main.set_precision_protocol(provider.id, main.PrecisionProtocolReq(
        model=MODEL, protocol="inherit", confirmed=True,
    )))
    assert restored["catalog"]["precision_connection"] == nano["precision_connection"]
    assert provider.extra["model_capabilities"][GPT] == gpt_capability
    assert provider.precision_edit_profile == PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE


def test_documented_gateway_preflight_reports_connection_without_http(runtime, monkeypatch):
    provider, _ = runtime
    provider.base_url = "https://api.velapi.cc/v1"

    def no_http(**_kwargs):
        pytest.fail("Local preflight must not create an HTTP client")

    monkeypatch.setattr(providers.httpx, "AsyncClient", no_http)
    result = asyncio.run(main.precision_preflight(provider.id, main.PrecisionPreflightReq(
        model=MODEL, size="2048x2048",
    )))
    assert result["ok"]
    assert result["upstream_requests"] == 0
    assert result["upstream_verified"] is False
    assert result["profile"] == "openai_images_edits_json_data_url_single_source_image"
    assert result["precision_connection"]["source"] == "gateway_documentation"
    assert provider.base_url not in str(result)
    assert provider.api_key not in str(result)


def test_gateway_precision_contract_reports_edit_route_and_profile(runtime):
    provider, _ = runtime
    provider.base_url = "https://api.velapi.cc/v1"
    contract = main._generation_request_contract(provider, "precision_edit", {"model": MODEL})
    assert contract["route"] == "/images/edits"
    assert contract["protocol"] == "openai"
    assert contract["profile"] == "openai_images_edits_json_data_url_single_source_image"


def test_native_auto_authorization_does_not_force_shared_provider_to_openai(runtime):
    provider, _ = runtime
    model = "gemini-3.1-flash-image"
    provider.base_url = "https://generativelanguage.googleapis.com"
    provider.endpoint_type = "auto"
    provider.precision_edit_profile = None
    provider.model = model
    provider.models = [model]
    provider.extra = {"model_capabilities": {model: {}}}
    asyncio.run(main.set_precision_capability(provider.id, main.PrecisionCapabilityReq(
        model=model, enabled=True, confirmed=True,
    )))
    assert provider.endpoint_type == "auto"
    assert provider.precision_edit_profile is None
    asyncio.run(main.set_precision_capability(provider.id, main.PrecisionCapabilityReq(
        model=model, enabled=True, confirmed=True, size="2048x2048",
    )))
    catalog = main._public_precision_size_catalog(provider)[0]
    assert catalog["precision_connection"]["protocol"] == "gemini"
    assert catalog["strict_selectable_sizes"] == ["2048x2048"]


@pytest.mark.parametrize("manual", [False, True])
def test_failed_size_authorization_save_leaves_no_in_memory_grant(runtime, monkeypatch, manual):
    provider, _ = runtime
    if manual:
        provider.extra["precision_model_overrides"] = {MODEL: {
            "protocol": "openai", "capabilities": {
                "precision_edit": True, "supported_sizes": ["2048x2048"],
            },
        }}
    before = copy.deepcopy(provider.model_dump())

    def save_failure(_config):
        raise OSError("Synthetic storage failure")

    monkeypatch.setattr(main.cfg_mgr, "save", save_failure)
    with pytest.raises(OSError):
        asyncio.run(main.set_precision_capability(provider.id, main.PrecisionCapabilityReq(
            model=MODEL, enabled=True, confirmed=True, size="2752x1536",
        )))
    assert provider.model_dump() == before


def test_legacy_openai_profile_matches_catalog_preflight_and_runtime(runtime):
    provider, _ = runtime
    provider.precision_edit_profile = None
    catalog = main._public_precision_size_catalog(provider)
    nano = next(item for item in catalog if item["model"] == MODEL)
    expected = PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE.value
    assert nano["precision_connection"]["profile"] == expected
    assert nano["precision_connection"]["automatic"]["profile"] == expected
    assert nano["precision_capability"]["request_profile"] == expected
    assert main._generation_request_contract(provider, "precision_edit", {"model": MODEL})["profile"] == expected
    assert providers._precision_edit_transport_profile(provider) == providers.PRECISION_EDIT_TRANSPORT_PROFILES[expected]
