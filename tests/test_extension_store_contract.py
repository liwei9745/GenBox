from pathlib import Path

from fastapi.testclient import TestClient

import main
from extensions.catalog import CATALOG
from extensions.models import ExtensionInstance
from extensions.store import store_projection


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
