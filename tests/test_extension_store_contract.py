from datetime import datetime, timezone
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
    target_identity_digest,
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
    verified = store.verified_environment_projection(
        target,
        {"ok": True},
        {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    assert verified is not None
    save_environment_projection(verified)

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
        verified = store.verified_environment_projection(
            target,
            {"ok": True},
            {"evidence_manifest": {"complete": True}, "capabilities": {
                "docker_available": docker_available,
                "compose_available": compose_available,
            }},
        ) if evidence_complete else None
        if verified is not None:
            save_environment_projection(verified)
        assert store.public_store_projection()["recommended"] == []


def test_projection_identity_and_freshness_fail_closed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    old_projection = EnvironmentProjection(
        target_id=target.id,
        target_identity_digest=store.target_identity_digest(target),
        observed_at="2020-01-01T00:00:00+00:00",
        docker_available=True, compose_available=True, evidence_complete=True,
        confidence="high",
    )
    store.save_config(store.load_config().model_copy(update={"environment_projections": [old_projection]}))
    assert get_environment_projection(target) is None

    future_projection = old_projection.model_copy(update={"observed_at": "2099-01-01T00:00:00+00:00"})
    store.save_config(store.load_config().model_copy(update={"environment_projections": [future_projection]}))
    assert get_environment_projection(target) is None
    changed = store.upsert_target({**target.model_dump(), "network_url": "https://changed.invalid"})
    assert get_environment_projection(changed) is None
    assert store.public_store_projection()["recommended"] == []


def test_store_projection_write_requires_complete_server_evidence(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    for discovery, public in (
        ({"ok": False}, {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }}),
        ({"ok": True}, {"evidence_manifest": {"complete": False}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }}),
        ({"ok": True}, {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": "yes", "compose_available": True,
        }}),
    ):
        assert store.verified_environment_projection(target, discovery, public) is None
    assert store.load_config().environment_projections == []


def test_complete_discovery_projection_is_fresh_and_high(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    verified = store.verified_environment_projection(
        target,
        {"ok": True},
        {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    assert verified is not None
    save_environment_projection(verified)
    projection = get_environment_projection(target)
    assert projection is not None
    assert projection.confidence == "high"


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


def _fresh_projection(
    target,
    *,
    confidence="high",
    docker_available=True,
    compose_available=True,
    evidence_complete=True,
) -> EnvironmentProjection:
    return EnvironmentProjection(
        target_id=target.id,
        target_identity_digest=target_identity_digest(target),
        observed_at=datetime.now(timezone.utc).isoformat(),
        docker_available=docker_available,
        compose_available=compose_available,
        evidence_complete=evidence_complete,
        confidence=confidence,
    )


def test_store_contract_response_hierarchy_and_stable_all_items():
    projection = store_projection(CATALOG, [], environment_projection=None)
    assert set(projection) == {"installed", "recommended", "all"}
    assert isinstance(projection["installed"], list)
    assert isinstance(projection["recommended"], list)
    assert isinstance(projection["all"], list)
    assert projection["all"]
    manifest_keys = {
        "id", "name", "repository", "category", "status", "manifest_version",
        "license", "provenance", "permissions", "network_exposure",
        "data_sensitivity", "operational_risk",
    }
    for item in projection["all"]:
        assert isinstance(item, dict)
        assert isinstance(item.get("id"), str) and item["id"]
        assert manifest_keys <= item.keys()
        assert isinstance(item["actions"], list)


def test_store_contract_never_exposes_sensitive_field_keys():
    projection = store_projection(
        CATALOG,
        [store_instance(managed=True), store_instance(managed=False)],
        environment_projection=None,
    )
    sensitive = {
        "host", "host_key", "container_id", "container_name", "install_dir",
        "data_dir", "image", "compose_project", "service_port", "api_url",
        "console_url", "credentials", "password", "private_key", "passphrase",
        "token", "network_url", "identity_version",
    }
    for view in ("installed", "recommended", "all"):
        for item in projection[view]:
            assert not (sensitive & item.keys()), (view, item)


def test_store_contract_installed_carries_manifest_metadata_and_ownership():
    projection = store_projection(CATALOG, [store_instance(managed=True)])
    item = projection["installed"][0]
    assert item["instance_id"] == "chatgpt2api-dev"
    assert item["instance_status"] == "running"
    assert item["ownership"] == "managed"
    assert item["id"] == "chatgpt2api"
    assert item["repository"] == "yukkcat/chatgpt2api"
    assert item["license"] == "unknown"
    assert item["actions"] == ["deploy"]


def test_store_contract_external_instances_are_read_only():
    projection = store_projection(CATALOG, [store_instance(managed=False)])
    installed = projection["installed"]
    assert len(installed) == 1
    item = installed[0]
    assert item["ownership"] == "external"
    assert item["instance_id"] == "external-app"
    assert isinstance(item["instance_status"], str)
    assert item["actions"] == []


def test_store_contract_recommended_high_medium_unknown_boundaries(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })

    high = _fresh_projection(target, confidence="high")
    recommended = store_projection(CATALOG, [], environment_projection=high)["recommended"]
    assert [item["id"] for item in recommended] == ["chatgpt2api"]
    assert recommended[0]["confidence"] == "high"
    assert recommended[0]["actions"] == ["deploy"]

    for confidence in ("medium", "unknown"):
        assert store_projection(
            CATALOG, [], environment_projection=_fresh_projection(target, confidence=confidence)
        )["recommended"] == []

    assert store_projection(
        CATALOG, [], environment_projection=_fresh_projection(target, compose_available=False)
    )["recommended"] == []
    assert store_projection(
        CATALOG, [], environment_projection=_fresh_projection(target, evidence_complete=False)
    )["recommended"] == []


def test_store_contract_identity_mismatch_fail_closed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    verified = store.verified_environment_projection(
        target,
        {"ok": True},
        {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    assert verified is not None
    save_environment_projection(verified)
    assert store.public_store_projection()["recommended"] != []

    drifted = store.upsert_target({
        **target.model_dump(),
        "host": "drifted.example",
        "identity_version": int(target.identity_version) + 1,
        "host_key": "drifted",
    })
    assert store.get_environment_projection(drifted) is None
    assert store.public_store_projection()["recommended"] == []


def test_store_contract_actions_derive_only_from_capability():
    from extensions.capabilities import project_store_actions

    for item in CATALOG:
        if item["status"] == "available" and item["repository"] == "yukkcat/chatgpt2api":
            assert project_store_actions(item) == ["deploy"]
        else:
            assert project_store_actions(item) == []
    assert project_store_actions({"id": "fake", "repository": "unregistered/invalid", "status": "available"}) == []
    assert project_store_actions({}) == []
    assert project_store_actions("junk") == []
    assert project_store_actions(None) == []


def test_store_contract_bad_inputs_fail_closed():
    empty = store_projection(None, None)
    assert empty == {"installed": [], "recommended": [], "all": []}

    only_catalog = store_projection(CATALOG, None)
    assert only_catalog["installed"] == []
    assert only_catalog["recommended"] == []
    assert only_catalog["all"]

    junk_instances = store_projection(CATALOG, [{"project": "chatgpt2api", "managed": True}])
    assert junk_instances["installed"] == []

    bad_projection = store_projection(
        CATALOG, [], environment_projection={"confidence": "high", "evidence_complete": True}
    )
    assert bad_projection["recommended"] == []
