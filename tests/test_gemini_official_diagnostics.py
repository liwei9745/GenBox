"""Offline regressions for native Google connectivity and quota diagnostics."""

import asyncio
import json

import httpx
import pytest

import main
import providers
from config import ProviderConfig


def _provider(**changes):
    values = dict(
        id="synthetic-google", name="Synthetic Google", type="image",
        api_key="synthetic-secret-only",
        base_url="https://generativelanguage.googleapis.com",
        model="gemini-3-pro-image-preview", endpoint_type="auto",
    )
    values.update(changes)
    return ProviderConfig(**values)


def _mock_client(monkeypatch, handler):
    original = httpx.AsyncClient
    options = []
    requests = []

    def respond(request):
        requests.append(request)
        return handler(request)

    def client(**kwargs):
        options.append(dict(kwargs))
        kwargs.pop("proxy", None)
        return original(transport=httpx.MockTransport(respond), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    return requests, options


@pytest.mark.parametrize("base", [
    "https://generativelanguage.googleapis.com",
    "https://generativelanguage.googleapis.com/v1beta/",
    "https://generativelanguage.googleapis.com/v1",
])
@pytest.mark.parametrize("status", [200, 401, 403, 429])
def test_native_connectivity_uses_header_auth_and_same_proxy(monkeypatch, base, status):
    cfg = _provider(base_url=base)
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [cfg])
    monkeypatch.setattr(main, "_get_proxy_url", lambda p: "http://127.0.0.1:12345")
    requests, options = _mock_client(
        monkeypatch, lambda _: httpx.Response(status, json={"models": []}),
    )
    result = asyncio.run(main.test_provider(cfg.id))
    assert result["success"] is (status == 200)
    assert result["endpoints"][0]["status_code"] == status
    assert len(requests) == 1
    assert str(requests[0].url) == "https://generativelanguage.googleapis.com/v1beta/models"
    assert requests[0].headers["x-goog-api-key"] == cfg.api_key
    assert "authorization" not in requests[0].headers
    assert cfg.api_key not in json.dumps(result)
    assert options[0]["proxy"] == "http://127.0.0.1:12345"


def test_explicit_openai_connectivity_keeps_protocol(monkeypatch):
    cfg = _provider(endpoint_type="openai", base_url="https://gateway.example.test/v1")
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [cfg])
    requests, _ = _mock_client(monkeypatch, lambda _: httpx.Response(200, json={"data": []}))
    assert asyncio.run(main.test_provider(cfg.id))["success"]
    assert requests[0].url.path == "/v1/models"
    assert requests[0].headers["authorization"] == f"Bearer {cfg.api_key}"
    assert "x-goog-api-key" not in requests[0].headers


@pytest.mark.parametrize("operation", ["generate", "edit"])
def test_quota_evidence_survives_without_request_content_or_retry(monkeypatch, operation):
    cfg = _provider(endpoint_type="gemini")
    prompt = "private synthetic scene instruction"
    image = "c3ludGhldGljLWltYWdl"
    error = {
        "code": 429, "status": "RESOURCE_EXHAUSTED",
        "message": f"Quota exceeded: {cfg.api_key} {prompt} {image}",
        "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
             "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "42s"},
        ],
    }
    requests, _ = _mock_client(monkeypatch, lambda _: httpx.Response(429, json={"error": error}))
    if operation == "edit":
        result = asyncio.run(providers._gen_gemini_edit(
            cfg, prompt, f"data:image/png;base64,{image}", 0.5,
        ))
    else:
        # Include the synthetic image bytes in a text part to test exact redaction.
        prompt = f"{prompt} {image}"
        result = asyncio.run(providers.generate_for_provider(cfg, prompt))
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
    assert result.success is False
    assert result.error_code == "gemini_rate_limit_or_quota"
    assert result.error_details["http_status"] == 429
    assert result.error_details["upstream_status"] == "RESOURCE_EXHAUSTED"
    assert result.error_details["retry_delay"] == "42s"
    assert result.error_details["quota_ids"] == ["GenerateRequestsPerDayPerProjectPerModel"]
    public = json.dumps({"error": result.error, "details": result.error_details})
    assert cfg.api_key not in public
    assert prompt not in public
    assert image not in public
    assert "429" in result.error


@pytest.mark.parametrize("body", [{"error": {"details": {}}}, {"error": "invalid"}, []])
def test_malformed_upstream_error_remains_a_failure(body):
    response = httpx.Response(429, json=body)
    result = providers._gemini_http_failure(response, _provider())
    assert result.success is False
    assert result.error_details["http_status"] == 429


def test_official_list_error_is_not_replaced_by_openai_fallback(monkeypatch):
    cfg = _provider(endpoint_type="gemini")
    requests, _ = _mock_client(monkeypatch, lambda _: httpx.Response(
        403, json={"error": {"status": "PERMISSION_DENIED", "message": cfg.api_key}},
    ))
    with pytest.raises(httpx.HTTPStatusError) as raised:
        asyncio.run(providers.fetch_models_from_upstream(cfg))
    assert len(requests) == 1
    assert requests[0].url.path == "/v1beta/models"
    assert "403" in str(raised.value)
    assert cfg.api_key not in str(raised.value)


def test_official_model_list_keeps_preview_identifiers(monkeypatch):
    cfg = _provider()
    requests, _ = _mock_client(monkeypatch, lambda _: httpx.Response(200, json={
        "models": [{"name": f"models/{cfg.model}", "supportedGenerationMethods": ["generateContent"]}],
    }))
    assert asyncio.run(providers.fetch_models_from_upstream(cfg)) == [cfg.model]
    assert requests[0].url.params["pageSize"] == "1000"
    assert "key" not in requests[0].url.params


def test_connectivity_transport_error_redacts_key(monkeypatch):
    cfg = _provider()
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [cfg])

    def handler(request):
        raise httpx.ConnectError(f"Failed {cfg.api_key}", request=request)

    _mock_client(monkeypatch, handler)
    result = asyncio.run(main.test_provider(cfg.id))
    assert result["success"] is False
    assert cfg.api_key not in json.dumps(result)
