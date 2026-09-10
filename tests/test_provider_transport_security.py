"""Security contracts for direct Provider HTTP clients."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import providers
from config import ProviderConfig


class _StreamResponse:
    def __init__(
        self,
        payload=None,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        chunks: list[bytes] | None = None,
    ):
        self.status_code = status_code
        self._body = json.dumps(payload or {}).encode("utf-8")
        self.headers = headers or {}
        self._chunks = chunks
        self.iterated = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def aiter_bytes(self):
        self.iterated = True
        for chunk in self._chunks or [self._body]:
            yield chunk


class _StreamingClient:
    def __init__(self, responses: list[_StreamResponse]):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def stream(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def _provider(*, provider_type: str = "image", endpoint_type: str = "openai"):
    return ProviderConfig(
        id=f"synthetic-{endpoint_type}",
        name=f"Synthetic {endpoint_type}",
        type=provider_type,
        api_key="synthetic-provider-key",
        base_url="https://provider.example.test/v1beta"
        if endpoint_type == "gemini"
        else "https://provider.example.test/v1",
        model="synthetic-model",
        endpoint_type=endpoint_type,
    )


@pytest.mark.parametrize("operation", ["generate", "edit"])
def test_gemini_generation_uses_header_auth_without_query_key(monkeypatch, operation):
    client = _StreamingClient([_StreamResponse({"candidates": []})])
    client_options = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_options.append(kwargs) or client,
    )
    monkeypatch.setattr(providers, "verify_ssl_enabled", lambda: False)
    cfg = _provider(endpoint_type="gemini")

    if operation == "generate":
        result = asyncio.run(providers._gen_gemini(cfg, "synthetic prompt"))
    else:
        result = asyncio.run(
            providers._gen_gemini_edit(
                cfg,
                "synthetic prompt",
                "data:image/png;base64,AA==",
                0.5,
            )
        )

    assert result.success is False
    assert client_options[0]["verify"] is False
    method, url, request_options = client.calls[0]
    assert method == "POST"
    assert url == (
        "https://provider.example.test/v1beta/models/"
        "synthetic-model:generateContent"
    )
    assert "?" not in url
    assert cfg.api_key not in url
    assert request_options["headers"] == {"x-goog-api-key": cfg.api_key}


@pytest.mark.parametrize("detailed", [False, True])
def test_llm_clients_use_shared_tls_and_small_stream_cap(monkeypatch, detailed):
    response = _StreamResponse(
        {"choices": [{"message": {"content": "improved prompt"}}]}
    )
    client = _StreamingClient([response])
    client_options = []
    observed_limits = []
    original_read = providers._read_bounded_provider_response

    async def recording_read(stream_response, max_bytes):
        observed_limits.append(max_bytes)
        return await original_read(stream_response, max_bytes)

    monkeypatch.setattr(providers, "_read_bounded_provider_response", recording_read)
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_options.append(kwargs) or client,
    )
    monkeypatch.setattr(providers, "verify_ssl_enabled", lambda: False)
    monkeypatch.setattr(
        providers.cfg_mgr,
        "get_llm_provider",
        lambda: _provider(provider_type="llm"),
    )

    if detailed:
        result = asyncio.run(providers.enhance_prompt_with_llm_detailed("prompt"))
        assert result["text"] == "improved prompt"
        assert result["optimized"] is True
    else:
        assert asyncio.run(providers.enhance_prompt_with_llm("prompt")) == "improved prompt"

    assert client_options[0]["verify"] is False
    assert observed_limits == [providers.PROVIDER_LLM_RESPONSE_MAX_BYTES]
    assert client.calls[0][0] == "POST"


@pytest.mark.parametrize(
    ("fetcher", "endpoint_type", "payload", "expected", "auth_header"),
    [
        (
            providers._fetch_openai_models,
            "openai",
            {"data": [{"id": "gpt-image-2"}]},
            ["gpt-image-2"],
            "Authorization",
        ),
        (
            providers._fetch_gemini_models,
            "gemini",
            {
                "models": [
                    {
                        "name": "models/gemini-image",
                        "supportedGenerationMethods": ["generateContent"],
                    }
                ]
            },
            ["gemini-image"],
            "x-goog-api-key",
        ),
        (
            providers._fetch_qwen_models,
            "qwen",
            {"data": [{"id": "qwen-image"}]},
            ["qwen-image"],
            "Authorization",
        ),
    ],
)
def test_model_list_clients_use_shared_tls_and_bounded_streaming(
    monkeypatch,
    fetcher,
    endpoint_type,
    payload,
    expected,
    auth_header,
):
    client = _StreamingClient([_StreamResponse(payload)])
    client_options = []
    observed_limits = []
    original_read = providers._read_bounded_provider_response

    async def recording_read(stream_response, max_bytes):
        observed_limits.append(max_bytes)
        return await original_read(stream_response, max_bytes)

    monkeypatch.setattr(providers, "_read_bounded_provider_response", recording_read)
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_options.append(kwargs) or client,
    )
    monkeypatch.setattr(providers, "verify_ssl_enabled", lambda: False)
    cfg = _provider(endpoint_type=endpoint_type)

    assert asyncio.run(fetcher(cfg)) == expected

    assert client_options[0]["verify"] is False
    assert observed_limits == [providers.PROVIDER_MODEL_LIST_RESPONSE_MAX_BYTES]
    method, url, request_options = client.calls[0]
    assert method == "GET"
    assert cfg.api_key not in url
    assert "?key=" not in url
    assert auth_header in request_options["headers"]
    if endpoint_type == "gemini":
        assert request_options["headers"] == {"x-goog-api-key": cfg.api_key}


def test_direct_json_cap_rejects_declared_length_before_iteration(monkeypatch):
    response = _StreamResponse(
        {},
        headers={
            "content-length": str(providers.PROVIDER_MODEL_LIST_RESPONSE_MAX_BYTES + 1)
        },
    )
    client = _StreamingClient([response])
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **_kwargs: client)

    with pytest.raises(providers.ProviderResponseValidationError) as raised:
        asyncio.run(providers._fetch_openai_models(_provider()))

    assert raised.value.code == "provider_response_bytes_exceeded"
    assert response.iterated is False


def test_direct_json_cap_rejects_chunked_overflow_incrementally():
    response = _StreamResponse({}, chunks=[b"12", b"345"])
    client = _StreamingClient([response])

    with pytest.raises(providers.ProviderResponseValidationError) as raised:
        asyncio.run(
            providers._stream_bounded_provider_response(
                client,
                "GET",
                "https://provider.example.test/v1/models",
                success_max_bytes=4,
            )
        )

    assert raised.value.code == "provider_response_bytes_exceeded"
    assert response.iterated is True


def test_non_streaming_fallback_dispatches_requested_get_method():
    sentinel = object()

    class Client:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return sentinel

        async def post(self, *_args, **_kwargs):
            raise AssertionError("GET fallback must not dispatch POST")

    client = Client()
    result = asyncio.run(
        providers._stream_bounded_provider_response(
            client,
            "GET",
            "https://provider.example.test/v1/models",
            headers={"Authorization": "Bearer synthetic"},
        )
    )

    assert result is sentinel
    assert client.calls == [
        (
            "https://provider.example.test/v1/models",
            {"headers": {"Authorization": "Bearer synthetic"}},
        )
    ]


def test_gemini_generation_failure_does_not_expose_header_key(monkeypatch):
    cfg = _provider(endpoint_type="gemini")

    class FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def stream(self, _method, _url, **_kwargs):
            raise RuntimeError(f"upstream echoed {cfg.api_key}")

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **_kwargs: FailingClient())

    result = asyncio.run(
        providers.generate_for_provider(
            cfg,
            "synthetic prompt",
            protocol="gemini",
        )
    )

    assert result.success is False
    assert cfg.api_key not in result.error
    assert "[REDACTED]" in result.error


def test_qwen_model_fetch_logs_only_redacted_exception(monkeypatch, capsys):
    cfg = _provider(endpoint_type="qwen")

    class FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def stream(self, _method, _url, **_kwargs):
            raise RuntimeError(f"upstream echoed {cfg.api_key}")

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **_kwargs: FailingClient())

    assert asyncio.run(providers._fetch_qwen_models(cfg))
    output = capsys.readouterr().out

    assert cfg.api_key not in output
    assert "[REDACTED]" in output


def test_provider_production_source_has_no_gemini_query_key_auth():
    source = Path(providers.__file__).read_text(encoding="utf-8")
    assert "?key=" not in source
