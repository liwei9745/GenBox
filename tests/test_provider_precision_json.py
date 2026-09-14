"""Gateway JSON editing uses a decoded source, strict output checks, and one POST."""
import asyncio
import base64
import json
from io import BytesIO

import httpx
import pytest
from PIL import Image

import providers
from config import EndpointConfig, PrecisionEditProfile, ProviderConfig


MODEL = "nano-banana-2-2k"
JSON_PROFILE = PrecisionEditProfile.OPENAI_IMAGES_EDITS_JSON_DATA_URL_SINGLE_SOURCE_IMAGE


def image_bytes(size=(1024, 1024), fmt="PNG"):
    buffer = BytesIO()
    Image.new("RGB", size, (20, 90, 150)).save(buffer, fmt)
    return buffer.getvalue()


def provider(**changes):
    values = {
        "id": "synthetic-gateway", "name": "Synthetic gateway", "type": "image",
        "api_key": "synthetic-key", "base_url": "https://api.velapi.cc/v1",
        "model": "gpt-image-2.5-c", "endpoint_type": "openai",
        "precision_edit_profile": PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE,
        "capabilities": {"precision_edit": True},
        "extra": {"model_capabilities": {
            MODEL: {"precision_edit": True, "supported_sizes": ["2048x2048"]},
            "gpt-image-2.5-c": {"precision_edit": True, "supported_sizes": ["1024x1024"]},
        }, "precision_model_overrides": {
            MODEL: {
                "protocol": "openai",
                "profile": JSON_PROFILE,
                "capabilities": {"precision_edit": True, "supported_sizes": ["2048x2048"]},
            },
        }},
    }
    values.update(changes)
    return ProviderConfig(**values)


def edit_kwargs():
    return {
        "model": MODEL, "mode": "precision_edit", "precision_edit_authorized": True,
        "precision_canvas_only": True, "precision_size_mode": "resize",
        "precision_target_size": "2048x2048", "precision_resize_prompt": "Expand the background.",
        "precision_output_size_policy": "strict",
        "image_data": "data:image/png;base64," + base64.b64encode(image_bytes()).decode("ascii"),
    }


def mock_http(monkeypatch, output=None, status=200, error=None):
    calls = []
    client_type = httpx.AsyncClient
    payload = {"data": [{"b64_json": base64.b64encode(output or image_bytes((2048, 2048))).decode("ascii")}]}

    def handler(request):
        calls.append(request)
        if error:
            raise error("Synthetic connection error", request=request)
        return httpx.Response(status, json=payload if status == 200 else {"error": {"message": "Synthetic upstream error"}})

    def client(**kwargs):
        kwargs.pop("proxy", None)
        return client_type(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client)
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "synthetic-result.png")
    return calls


def test_gateway_auto_json_uses_exact_model_and_decoded_mime(monkeypatch):
    cfg = provider()
    cfg.extra["precision_model_overrides"] = {
        MODEL: {
            "protocol": "openai",
            "profile": JSON_PROFILE,
            "capabilities": {"precision_edit": True, "supported_sizes": ["1024x1024", "2048x2048"]},
        }
    }
    before = cfg.model_dump()
    calls = mock_http(monkeypatch)
    kwargs = edit_kwargs()
    source = image_bytes(fmt="JPEG")
    kwargs["image_data"] = "data:image/png;base64," + base64.b64encode(source).decode("ascii")
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic edit", **kwargs))
    assert result.success, result.error
    assert len(calls) == 1
    request = calls[0]
    payload = json.loads(request.content)
    assert request.url.path == "/v1/images/edits"
    assert request.headers["content-type"] == "application/json"
    assert payload["image"] == "data:image/jpeg;base64," + base64.b64encode(source).decode("ascii")
    assert payload["model"] == MODEL
    assert payload["size"] == "2048x2048"
    assert payload["quality"] == "medium"
    assert payload["n"] == 1
    assert "Target canvas constraint" in payload["prompt"]
    assert cfg.model_dump() == before


@pytest.mark.parametrize("status", [400, 429, 503])
def test_gateway_json_failure_is_one_post_across_endpoints(monkeypatch, status):
    cfg = provider()
    cfg.endpoints = [
        EndpointConfig(url="https://api.velapi.cc/v1", key="synthetic-key"),
        EndpointConfig(url="https://api.velapi.cc/v1", key="synthetic-key-two"),
    ]
    calls = mock_http(monkeypatch, status=status)
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic edit", **edit_kwargs()))
    assert not result.success
    assert result.error_code == "precision_edit_upstream_error"
    assert len(calls) == 1


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectError])
def test_gateway_json_transport_failure_does_not_replay(monkeypatch, error):
    calls = mock_http(monkeypatch, error=error)
    result = asyncio.run(providers.generate_for_provider(provider(), "Synthetic edit", **edit_kwargs()))
    assert not result.success
    assert len(calls) == 1


@pytest.mark.parametrize("policy,success", [("strict", False), ("fit_crop", True)])
def test_gateway_json_output_size_policy_is_preserved(monkeypatch, policy, success):
    calls = mock_http(monkeypatch, output=image_bytes((1920, 1920)))
    kwargs = edit_kwargs()
    kwargs["precision_output_size_policy"] = policy
    result = asyncio.run(providers.generate_for_provider(provider(), "Synthetic edit", **kwargs))
    assert result.success is success
    if success:
        assert result.metadata["provider_actual_size"] == "1920x1920"
        assert result.metadata["final_size"] == "2048x2048"
    else:
        assert result.error_code == "precision_edit_output_size_mismatch"
    assert len(calls) == 1


def test_gateway_json_rejects_bad_input_before_http(monkeypatch):
    calls = mock_http(monkeypatch)
    kwargs = edit_kwargs()
    kwargs["image_data"] = "data:image/png;base64,not-valid"
    result = asyncio.run(providers.generate_for_provider(provider(), "Synthetic edit", **kwargs))
    assert result.error_code == "precision_edit_payload_invalid"
    assert not calls


def test_vel_json_local_data_url_fails_before_http_with_actionable_contract(monkeypatch):
    cfg = provider(
        precision_edit_profile=None,
        extra={"model_capabilities": {
            MODEL: {"precision_edit": True, "supported_sizes": ["2048x2048"]},
        }},
    )
    calls = mock_http(monkeypatch)
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic edit", **edit_kwargs()))
    assert not result.success
    assert result.error_code == "precision_edit_public_image_url_required"
    assert not calls
    assert result.error_details["upstream_request"] is False
    assert "公网" in result.error
    assert "文生图成功不代表改图输入格式兼容" in result.error


@pytest.mark.parametrize("target,tier", [
    ("1024x1024", "1K"), ("2752x1536", "2K"), ("5504x3072", "4K"),
])
def test_klong_auto_recipe_uses_multipart_for_local_image(monkeypatch, target, tier):
    model = "nano-banana2"
    cfg = provider(
        base_url="https://api.klong.lat/v1",
        precision_edit_profile=None,
        extra={"model_capabilities": {
            model: {"precision_edit": True, "supported_sizes": [target]},
        }},
    )
    calls = mock_http(monkeypatch, output=image_bytes(tuple(map(int, target.split("x")))))
    kwargs = {**edit_kwargs(), "model": model, "precision_target_size": target}
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic edit", **kwargs))
    assert result.success, result.error
    assert len(calls) == 1
    request = calls[0]
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert model.encode() in request.content
    assert target.encode() in request.content
    assert ('name="size"\r\n\r\n' + tier + '\r\n').encode() in request.content
    assert b'name="response_format"' in request.content
    assert b"b64_json" in request.content


@pytest.mark.parametrize("value,code", [
    ("valid", None),
    ("data:image/png;base64,invalid", "precision_edit_invalid_response"),
    ("data:image/jpeg;base64,", "precision_edit_invalid_response"),
    ("http://127.0.0.1/image.png", "precision_edit_result_download_rejected"),
])
def test_precision_url_field_inline_image_or_unsafe_address(monkeypatch, value, code):
    raw = base64.b64encode(image_bytes((2048, 2048))).decode("ascii")
    if value == "valid":
        value = "data:image/png;base64," + raw
    elif value == "data:image/jpeg;base64,":
        value += raw
    client_type = httpx.AsyncClient
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": [{"url": value}]})

    def client(**kwargs):
        kwargs.pop("proxy", None)
        return client_type(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client)
    monkeypatch.setattr(providers, "_save_image", lambda *a, **kw: "synthetic-result.png")
    result = asyncio.run(providers.generate_for_provider(provider(), "Synthetic edit", **edit_kwargs()))
    assert result.success is (code is None), result.error
    if code:
        assert result.error_code == code
    assert len(calls) == 1


def test_explicit_json_unknown_gateway_is_allowed_without_gateway_quality(monkeypatch):
    cfg = provider(base_url="https://unknown.example.test/v1", precision_edit_profile=JSON_PROFILE)
    calls = mock_http(monkeypatch)
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic edit", **edit_kwargs()))
    assert result.success
    payload = json.loads(calls[0].content)
    assert payload["image"].startswith("data:image/png;base64,")
    assert "quality" not in payload


def test_json_annotation_edit_keeps_single_source_and_geometry(monkeypatch):
    cfg = provider()
    cfg.extra["precision_model_overrides"] = {
        MODEL: {
            "protocol": "openai",
            "profile": JSON_PROFILE,
            "capabilities": {"precision_edit": True, "supported_sizes": ["1024x1024", "2048x2048"]},
        }
    }
    cfg.extra["model_capabilities"][MODEL]["supported_sizes"].append("1024x1024")
    calls = mock_http(monkeypatch, output=image_bytes())
    kwargs = edit_kwargs()
    kwargs.pop("precision_canvas_only")
    kwargs.pop("precision_target_size")
    kwargs.pop("precision_resize_prompt")
    kwargs.pop("precision_output_size_policy")
    kwargs.update({
        "precision_size_mode": "preserve",
        "annotation_contract": providers.PRECISION_ANNOTATION_CONTRACT_V2,
        "annotation_image_data": kwargs["image_data"],
        "annotations": [{"type": "rectangle", "label": 1,
                         "x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2,
                         "instruction": "Change the selected region to green."}],
    })
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic edit", **kwargs))
    assert result.success, result.error
    payload = json.loads(calls[0].content)
    assert isinstance(payload["image"], str)
    assert "Normalized geometry JSON" in payload["prompt"]
    assert "Change the selected region to green." in payload["prompt"]
    assert "annotation_image_data" not in payload


def test_gateway_error_cannot_echo_source_or_private_edit_instruction(monkeypatch):
    cfg = provider()
    before = cfg.model_dump()
    kwargs = edit_kwargs()
    prompt = "Synthetic private replacement instruction."
    body = "Rejected " + prompt + " with " + kwargs["precision_resize_prompt"] + " " + kwargs["image_data"]
    client_type = httpx.AsyncClient
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400, json={"error": {"message": body}})

    def client(**options):
        options.pop("proxy", None)
        return client_type(transport=httpx.MockTransport(handler), **options)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client)
    result = asyncio.run(providers.generate_for_provider(cfg, prompt, **kwargs))
    assert not result.success
    assert len(calls) == 1
    assert prompt not in result.error
    assert kwargs["precision_resize_prompt"] not in result.error
    assert kwargs["image_data"].partition(",")[2] not in result.error
    assert "data:image/" not in result.error
    assert cfg.model_dump() == before


@pytest.mark.parametrize("snake_case", [False, True])
@pytest.mark.parametrize("private_url", [False, True])
def test_native_file_data_uses_bounded_download_gate(monkeypatch, snake_case, private_url):
    cfg = provider(
        model="gemini-3-pro-image", endpoint_type="gemini",
        base_url="https://native.example.test",
        precision_edit_profile=PrecisionEditProfile.GEMINI_GENERATE_CONTENT,
        extra={"model_capabilities": {"gemini-3-pro-image": {
            "precision_edit": True, "supported_sizes": ["2048x2048"],
        }}},
    )
    file_uri = "https://127.0.0.1/private.png" if private_url else "https://media.example.test/output.png"
    part = (
        {"file_data": {"file_uri": file_uri, "mime_type": "image/png"}}
        if snake_case else {"fileData": {"fileUri": file_uri, "mimeType": "image/png"}}
    )
    client_type = httpx.AsyncClient
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "POST"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [part]}}]})

    def client(**kwargs):
        kwargs.pop("proxy", None)
        return client_type(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client)
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "synthetic-result.png")
    downloaded = []
    if not private_url:
        async def download(_client, url, **kwargs):
            downloaded.append((url, kwargs))
            return image_bytes((2048, 2048)), None
        monkeypatch.setattr(providers, "_download_generated_image", download)
    kwargs = edit_kwargs()
    kwargs["model"] = cfg.model
    result = asyncio.run(providers.generate_for_provider(cfg, "Synthetic edit", **kwargs))
    assert result.success is not private_url
    assert len(calls) == 1
    if private_url:
        assert result.error_code == "precision_edit_result_download_rejected"
    else:
        assert downloaded == [(file_uri, {"max_pixels": providers.PRECISION_MAX_OUTPUT_PIXELS})]
