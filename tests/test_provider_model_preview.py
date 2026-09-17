"""Draft model discovery must not save credentials or require a persisted ID."""

import pytest
from fastapi.testclient import TestClient

import main
from config import ProviderConfig

PATH = "/api/providers/fetch-models-preview"


@pytest.fixture
def isolated(monkeypatch):
    saved = ProviderConfig(
        id="saved", name="Saved", type="video",
        base_url="https://provider.example.test/v1",
        api_key="synthetic-saved-key", api_keys=["synthetic-pool-key"],
        model="old-video", models=["old-video"],
        endpoints=[{"url": "https://endpoint.example.test/v1", "key": "synthetic-endpoint-key"}],
    )
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [saved])
    monkeypatch.setattr(main, "is_prod_mode", lambda: False)
    monkeypatch.setattr(main.cfg_mgr, "save", lambda *_: pytest.fail("Preview must not persist"))
    return saved


def payload(**changes):
    return {"id": "", "name": "Draft", "type": "video",
            "base_url": "https://provider.example.test/v1",
            "api_key": "synthetic-new-key", **changes}


@pytest.mark.parametrize("failed", [False, True])
def test_new_draft_preview_is_ephemeral_and_redacted(monkeypatch, isolated, failed):
    before = isolated.model_dump()
    seen = []

    async def fetch(cfg):
        seen.append(cfg)
        if failed:
            raise ValueError(f"Upstream rejected {cfg.api_key}")
        return ["veo-3.1-generate-preview"]

    monkeypatch.setattr(main, "fetch_models_from_upstream", fetch)
    response = TestClient(main.app).post(PATH, json=payload())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["success"] is not failed
    assert len(seen) == 1 and seen[0].api_key == "synthetic-new-key"
    assert "synthetic-new-key" not in response.text
    assert len(main.cfg_mgr.config.providers) == 1
    assert isolated.model_dump() == before


def test_existing_preview_reuses_secrets_only_for_unchanged_urls(monkeypatch, isolated):
    before = isolated.model_dump()
    seen = []

    async def fetch(cfg):
        seen.append(cfg)
        return []

    monkeypatch.setattr(main, "fetch_models_from_upstream", fetch)
    client = TestClient(main.app)
    body = payload(id="saved", api_key="", endpoints=[
        {"url": "https://changed.example.test/v1", "key": ""},
        {"url": "https://endpoint.example.test/v1", "key": "****"},
    ])
    assert client.post(PATH, json=body).json()["success"]
    draft = seen[0]
    assert draft.api_key == "synthetic-saved-key"
    assert draft.api_keys == ["synthetic-pool-key"]
    assert draft.endpoints[0].key == ""
    assert draft.endpoints[1].key == "synthetic-endpoint-key"
    assert isolated.model_dump() == before
    body["base_url"] = "https://changed.example.test/v1"
    assert client.post(PATH, json=body).json()["success"]
    assert seen[1].api_key == "" and seen[1].api_keys == []


def test_new_primary_key_is_not_shadowed_by_saved_pool(isolated):
    draft = main._provider_discovery_draft(main.ProviderCreateReq(**payload(id="saved")))
    assert draft.get_effective_keys() == ["synthetic-new-key"]
    assert draft.endpoints == []
    assert isolated.api_keys == ["synthetic-pool-key"]


def test_empty_list_is_not_replaced_by_saved_models(monkeypatch, isolated):
    async def fetch(cfg):
        return []

    monkeypatch.setattr(main, "fetch_models_from_upstream", fetch)
    data = TestClient(main.app).post(PATH, json=payload(id="saved", api_key="")).json()
    assert data["success"] and data["models"] == [] and data["count"] == 0
    assert isolated.models == ["old-video"]


def test_preview_requires_admin_and_valid_origin(monkeypatch, isolated):
    async def unexpected(cfg):
        pytest.fail("Unauthorized discovery must not reach upstream")

    monkeypatch.setattr(main, "fetch_models_from_upstream", unexpected)
    monkeypatch.setattr(main, "is_prod_mode", lambda: True)
    monkeypatch.setattr(main, "verify_admin_key", lambda key: key == "synthetic-admin")
    client = TestClient(main.app)
    assert client.post(PATH, json=payload()).status_code == 401
    assert client.post(PATH, json=payload(), headers={
        "X-Admin-Key": "synthetic-admin", "Origin": "https://untrusted.example.test",
    }).status_code == 403


def test_preview_validation_does_not_echo_secret(isolated):
    response = TestClient(main.app).post(PATH, json=payload(api_keys={"key": "synthetic-private-value"}))
    assert response.status_code == 422
    assert "synthetic-private-value" not in response.text
