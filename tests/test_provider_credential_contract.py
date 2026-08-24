"""Provider credential preservation and model-fetch contract tests."""

import asyncio

import main
from config import EndpointConfig, ProviderConfig
from providers import _fetch_openai_models


def test_masked_provider_update_preserves_saved_credentials_and_endpoints():
    existing = ProviderConfig(
        id="gpt-image",
        name="GPT Image 2",
        type="image",
        api_key="sk-real-primary",
        api_keys=["sk-real-primary", "sk-real-secondary"],
        base_url="https://api.example.test/v1",
        endpoints=[EndpointConfig(url="https://backup.example.test/v1", key="sk-real-backup")],
    )
    req = main.ProviderCreateReq(
        id=existing.id,
        name=existing.name,
        type=existing.type,
        api_key="sk-r****mary",
        api_keys=[],
        base_url=existing.base_url,
        endpoints=[],
    )

    payload = main._merge_provider_secrets(existing, req)

    assert payload["api_key"] == "sk-real-primary"
    assert payload["api_keys"] == ["sk-real-primary", "sk-real-secondary"]
    assert payload["endpoints"][0].key == "sk-real-backup"


def test_effective_multi_key_is_used_before_legacy_single_key():
    provider = ProviderConfig(
        id="gpt-image",
        name="GPT Image 2",
        type="image",
        api_key="sk-legacy",
        api_keys=["sk-rotating"],
        base_url="https://api.example.test/v1",
    )

    assert provider.get_active_endpoints()[0].key == "sk-rotating"


def test_masked_saved_key_is_not_treated_as_usable_credential():
    provider = ProviderConfig(
        id="gpt-image",
        name="GPT Image 2",
        type="image",
        api_key="sk-d****XWSw",
        base_url="https://api.example.test/v1",
    )

    assert provider.get_effective_keys() == []
    assert provider.get_active_endpoints() == []


def test_openai_model_fetch_tries_effective_keys(monkeypatch):
    calls = []

    class Response:
        def __init__(self, status_code, data=None):
            self.status_code = status_code
            self._data = data or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

        def json(self):
            return self._data

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers):
            calls.append(headers["Authorization"])
            if headers["Authorization"].endswith("bad"):
                return Response(401)
            return Response(200, {"data": [{"id": "gpt-image-2"}]})

    monkeypatch.setattr("providers.httpx.AsyncClient", lambda **kwargs: Client())

    provider = ProviderConfig(
        id="gpt-image",
        name="GPT Image 2",
        type="image",
        api_keys=["sk-bad", "sk-good"],
        base_url="https://api.example.test/v1",
    )

    models = asyncio.run(_fetch_openai_models(provider))

    assert models == ["gpt-image-2"]
    assert calls == ["Bearer sk-bad", "Bearer sk-good"]
