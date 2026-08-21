from pathlib import Path

from fastapi.testclient import TestClient

import main
from extensions.catalog import CATALOG
from extensions.models import EnvironmentProjection, ExtensionInstance
from extensions.store import (
    get_environment_projection,
    save_environment_projection,
    save_target_metadata,
    store_projection,
)


def store_instance(*, managed: bool) -> ExtensionInstance:
    return ExtensionInstance(
        id="chatgpt2api-dev" if managed else "external-app",
        target_id="target-a",
        service_port=33010,
        install_dir="/srv/app",
        data_dir="/srv/data",
        image="example.invalid/app@sha256:" + "a" * 64,
        managed=managed,
        ownership="managed" if managed else "compose",
        status="running",
    )


def test_store_projection_is_fail_closed_and_does_not_leak_instance_details():
    projection = store_projection(CATALOG, [store_instance(managed=True), store_instance(managed=False)])
    assert set(projection) == {"installed", "recommended", "all"}
    assert projection["recommended"] == []
    assert next(item for item in projection["installed"] if item["ownership"] == "managed")["actions"] == ["deploy"]
    assert next(item for item in projection["installed"] if item["ownership"] == "external")["actions"] == []
    assert all("container_id" not in item and "install_dir" not in item for item in projection["installed"])
    chatgpt = next(item for item in projection["all"] if item["id"] == "chatgpt2api")
    assert chatgpt["actions"] == ["deploy"]
    planned = [item for item in projection["all"] if item["status"] == "planned"]
    assert planned and all(item["actions"] == [] for item in planned)


def test_complete_matching_projection_recommends_only_registry_action(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    save_environment_projection(
        target, docker_available=True, compose_available=True, evidence_complete=True,
        observed_at="2099-01-01T00:00:00+00:00",
    )

    projection = store.public_store_projection()
    assert [item["id"] for item in projection["recommended"]] == ["chatgpt2api"]
    item = projection["recommended"][0]
    assert item["confidence"] == "high"
    assert item["reasons"]
    assert item["actions"] == ["deploy"]


def test_projection_missing_or_incomplete_capabilities_never_recommend_high(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    for docker_available, compose_available, evidence_complete in (
        (False, True, True), (True, False, True), (True, True, False),
    ):
        save_environment_projection(
            target,
            docker_available=docker_available,
            compose_available=compose_available,
            evidence_complete=evidence_complete,
            observed_at="2099-01-01T00:00:00+00:00",
        )
        assert store.public_store_projection()["recommended"] == []


def test_projection_identity_and_freshness_fail_closed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    save_environment_projection(
        target, docker_available=True, compose_available=True, evidence_complete=True,
        observed_at="2020-01-01T00:00:00+00:00",
    )
    assert get_environment_projection(target) is None

    save_environment_projection(
        target, docker_available=True, compose_available=True, evidence_complete=True,
        observed_at="2099-01-01T00:00:00+00:00",
    )
    changed = store.upsert_target({**target.model_dump(), "network_url": "https://changed.invalid"})
    assert get_environment_projection(changed) is None
    assert store.public_store_projection()["recommended"] == []


def test_browser_target_metadata_cannot_inject_environment_projection(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
        "environment_projections": [{"target_id": "store-target"}],
        "docker_available": True,
    })
    assert target.id == "store-target"
    assert store.load_config().environment_projections == []


def test_environment_projection_model_contains_no_remote_metadata_fields():
    fields = set(EnvironmentProjection.model_fields)
    assert fields == {
        "target_id", "target_identity_digest", "observed_at", "docker_available",
        "compose_available", "evidence_complete", "confidence",
    }


def test_store_route_has_stable_views_and_no_sensitive_fields(monkeypatch):
    monkeypatch.setattr(main.extensions_store, "public_store_projection", lambda: store_projection(CATALOG, []))
    response = TestClient(main.app, base_url="http://testserver").get("/api/extensions/store")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"installed", "recommended", "all"}
    required = {"id", "manifest_version", "repository", "provenance", "license", "permissions", "network_exposure", "data_sensitivity", "operational_risk", "actions"}
    assert all(required <= item.keys() for item in body["all"])
    assert all(secret not in response.text for secret in ("container_id", "install_dir", "data_dir", "private_key", "password"))


def test_store_ui_consumes_api_actions_without_planned_rows():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    assert 'id="extStore"' in html
    assert "data-store-view=\"installed\"" in html
    assert "data-store-view=\"recommended\"" in html
    assert "data-store-view=\"all\"" in html
    assert "/api/extensions/store" in source
    assert "Array.isArray(item.actions)" in source
    store_render = source.split("function renderStoreItem", 1)[1].split("window.extensionStoreView", 1)[0]
    assert "extPlannedRows" not in store_render
