"""Native Gemini precision contracts using synthetic images and mock HTTP."""
import asyncio
import base64
import json
from io import BytesIO

import httpx
import pytest
from PIL import Image

import providers
from config import ProviderConfig, PrecisionEditProfile


def _encoded(size=(1024, 1024)):
    output = BytesIO()
    Image.new("RGB", size, (32, 96, 160)).save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def _cfg(model="gemini-3-pro-image", sizes=None):
    return ProviderConfig(
        id="synthetic-gemini", name="Synthetic Gemini", type="image",
        api_key="synthetic-key", base_url="https://provider.example.test/v1beta",
        model=model, enabled=True, endpoint_type="gemini",
        capabilities={"precision_edit": True},
        precision_edit_profile=PrecisionEditProfile.GEMINI_GENERATE_CONTENT,
        extra={"model_capabilities": {model: {
            "precision_edit": True,
            "supported_sizes": ["1024x1024", "1376x768", "2752x1536", "5504x3072"] if sizes is None else sizes,
        }}},
    )


def _kwargs(**overrides):
    values = {
        "mode": "precision_edit", "precision_edit_authorized": True,
        "precision_size_mode": "resize", "precision_target_size": "1376x768",
        "precision_resize_prompt": "Extend the background naturally.",
        "precision_output_size_policy": "strict", "precision_canvas_only": True,
        "image_data": "data:image/png;base64," + _encoded(),
    }
    values.update(overrides)
    return values


def _payload(size=(1376, 768), **part_overrides):
    part = {"inlineData": {"mimeType": "image/png", "data": _encoded(size)}}
    part.update(part_overrides)
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [part]}}]}


@pytest.fixture
def transport(monkeypatch, tmp_path):
    calls = []
    state = {"status": 200, "payload": _payload(), "error": None}
    client_type = httpx.AsyncClient

    def handler(request):
        calls.append(request)
        if state["error"]:
            raise state["error"]("synthetic failure", request=request)
        return httpx.Response(state["status"], json=state["payload"])

    def client(**kwargs):
        kwargs.pop("proxy", None)
        return client_type(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client)
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)
    return calls, state


def _run(cfg=None, **kwargs):
    return asyncio.run(providers.generate_for_provider(cfg or _cfg(), "Synthetic edit", **_kwargs(**kwargs)))


@pytest.mark.parametrize(("size", "tier"), [
    ("1376x768", "1K"), ("2752x1536", "2K"), ("5504x3072", "4K"),
])
def test_native_resize_payload_and_exact_result(transport, size, tier):
    calls, state = transport
    state["payload"] = _payload(tuple(map(int, size.split("x"))))
    result = _run(precision_target_size=size)
    assert result.success, result.error
    assert len(calls) == 1
    assert str(calls[0].url) == "https://provider.example.test/v1beta/models/gemini-3-pro-image:generateContent"
    assert calls[0].headers["x-goog-api-key"] == "synthetic-key"
    assert "key=" not in str(calls[0].url)
    payload = json.loads(calls[0].content)
    assert payload["generationConfig"]["imageConfig"] == {"aspectRatio": "16:9", "imageSize": tier}
    assert len(payload["contents"][0]["parts"]) == 2
    assert "Synthetic edit" in payload["contents"][0]["parts"][0]["text"]
    assert "Extend the background naturally." in payload["contents"][0]["parts"][0]["text"]


def test_25_flash_omits_image_size(transport):
    calls, state = transport
    state["payload"] = _payload((1344, 768))
    result = _run(_cfg("gemini-2.5-flash-image", ["1344x768"]), precision_target_size="1344x768")
    assert result.success, result.error
    assert json.loads(calls[0].content)["generationConfig"]["imageConfig"] == {"aspectRatio": "16:9"}


@pytest.mark.parametrize("status", [400, 429, 500, 503])
def test_failure_never_reposts_or_changes_endpoint(transport, status):
    calls, state = transport
    state.update(status=status, payload={"error": {"message": "synthetic-key must be redacted"}})
    result = _run()
    assert not result.success
    assert len(calls) == 1
    assert result.error_code == "precision_edit_upstream_error"
    assert "synthetic-key" not in result.error


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectError, httpx.ReadError])
def test_transport_failure_never_reposts(transport, error):
    calls, state = transport
    state["error"] = error
    result = _run()
    assert not result.success
    assert len(calls) == 1


@pytest.mark.parametrize(("updates", "code"), [
    ({"precision_strategy": "invalid"}, "precision_strategy_invalid"),
    ({"precision_selection_mode": "local"}, "precision_local_selection_requires_annotations"),
    ({"precision_selection_feather": 2}, "precision_selection_feather_not_allowed"),
    ({"annotation_data": {}}, "precision_resize_annotation_fields_conflict"),
    ({"precision_edit_authorized": False}, "precision_edit_capability_not_authorized"),
    ({"image_data_list": []}, "precision_edit_single_image_required"),
    ({"precision_target_size": "1536x864"}, "precision_edit_target_size_not_declared"),
])
def test_shared_dispatch_validation_before_http(transport, updates, code):
    calls, _ = transport
    result = _run(**updates)
    assert result.error_code == code
    assert calls == []


def test_declared_but_unmappable_size_fails_before_post(transport):
    calls, _ = transport
    result = _run(_cfg(sizes=["1536x864"]), precision_target_size="1536x864")
    assert not result.success
    assert calls == []


def test_model_name_never_implies_alias_or_mapping(transport):
    calls, _ = transport
    result = _run(_cfg("nano-banana-pro"))
    assert not result.success
    assert calls == []


def test_explicit_alias_keeps_outbound_model(transport):
    calls, _ = transport
    cfg = _cfg()
    cfg.extra["model_capabilities"]["nano-banana-pro"] = {"alias_of": cfg.model}
    cfg.model = "nano-banana-pro"
    result = _run(cfg)
    assert result.success, result.error
    assert "/nano-banana-pro:generateContent" in str(calls[0].url)


@pytest.mark.parametrize("payload", [
    {"candidates": [{"content": {"parts": [{"text": "No image"}]}}]},
    {"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []},
    [],
    {"candidates": "bad"},
    _payload(thought=True),
])
def test_no_final_image_is_not_success(transport, payload):
    calls, state = transport
    state["payload"] = payload
    result = _run()
    assert not result.success
    assert len(calls) == 1


def test_thought_image_skipped_for_final_image(transport):
    _, state = transport
    state["payload"]["candidates"][0]["content"]["parts"].insert(0, {
        "thought": True, "inlineData": {"mimeType": "image/png", "data": _encoded((64, 64))},
    })
    result = _run()
    assert result.success, result.error


def test_mime_mismatch_rejected(transport):
    _, state = transport
    state["payload"]["candidates"][0]["content"]["parts"][0]["inlineData"]["mimeType"] = "image/jpeg"
    result = _run()
    assert result.error_code == "precision_edit_invalid_response"


def test_strict_output_mismatch_not_saved(transport):
    calls, state = transport
    state["payload"] = _payload((1024, 1024))
    result = _run()
    assert result.error_code == "precision_edit_output_size_mismatch"
    assert len(calls) == 1


def test_preserve_uses_native_source_mapping_and_annotation(transport):
    calls, state = transport
    state["payload"] = _payload((1024, 1024))
    kwargs = _kwargs()
    for field in ("precision_target_size", "precision_resize_prompt", "precision_output_size_policy"):
        kwargs.pop(field)
    kwargs.update(
        precision_size_mode="preserve", precision_canvas_only=False,
        annotation_image_data=kwargs["image_data"],
        annotation_contract="genbox-annotation-v2",
        annotations=[{"type": "arrow", "label": 1, "instruction": "Replace the cup.",
                      "x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6}],
    )
    result = asyncio.run(providers.generate_for_provider(_cfg(), "", **kwargs))
    assert result.success, result.error
    payload = json.loads(calls[0].content)
    assert payload["generationConfig"]["imageConfig"] == {"aspectRatio": "1:1", "imageSize": "1K"}
    assert len(payload["contents"][0]["parts"]) == 3
    assert "Replace the cup." in payload["contents"][0]["parts"][0]["text"]
