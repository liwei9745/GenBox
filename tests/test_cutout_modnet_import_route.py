"""HTTP contract tests for the opt-in MODNet browser upload route."""

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

import main
from image_tools.cutout_modnet_import import ModNetModelImportManager
from image_tools.cutout_registry import create_default_registry


def _request(tmp_path: Path, payload: bytes = b"modnet-fixture"):
    manager = ModNetModelImportManager(base_path=tmp_path)
    previous = main.MODNET_IMPORT_MANAGER
    main.MODNET_IMPORT_MANAGER = manager
    manifest = {
        "filename": "portrait.onnx",
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "md5": hashlib.md5(payload).hexdigest(),
    }
    return manager, previous, manifest, payload


def test_modnet_route_accepts_only_content_and_returns_sanitized_result(tmp_path):
    manager, previous, manifest, payload = _request(tmp_path)
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/image-tools/cutout/modnet/import",
                data={
                    "manifest": json.dumps(manifest),
                    "license_confirmed": "true",
                    "license_source": "user supplied checkpoint",
                },
                files={"upload": ("portrait.onnx", payload, "application/octet-stream")},
            )
        assert response.status_code == 201
        body = response.json()
        assert body["ok"] is True
        assert body["filename"] == "portrait.onnx"
        assert body["sha256"] == manifest["sha256"]
        assert "model_path" not in body
        assert "manifest_path" not in body
        # The manager deliberately publishes a fixed target name so adapter
        # discovery cannot be redirected by an uploaded filename.
        assert manager.model_path.read_bytes() == payload
    finally:
        main.MODNET_IMPORT_MANAGER = previous


def test_modnet_route_rejects_unconfirmed_license_and_bad_manifest(tmp_path):
    _manager, previous, manifest, payload = _request(tmp_path)
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/image-tools/cutout/modnet/import",
                data={
                    "manifest": json.dumps(manifest),
                    "license_confirmed": "false",
                },
                files={"upload": ("portrait.onnx", payload, "application/octet-stream")},
            )
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == "modnet_license_unconfirmed"

            response = client.post(
                "/api/image-tools/cutout/modnet/import",
                data={"manifest": json.dumps({"filename": "C:/secret.onnx"}), "license_confirmed": "true"},
                files={"upload": ("portrait.onnx", payload, "application/octet-stream")},
            )
            assert response.status_code == 422
            assert response.json()["detail"]["code"] in {"modnet_manifest_incomplete", "modnet_filename_invalid"}
    finally:
        main.MODNET_IMPORT_MANAGER = previous


def test_modnet_route_rejects_manifest_hash_mismatch_without_install(tmp_path):
    manager, previous, manifest, payload = _request(tmp_path)
    manifest["sha256"] = "0" * 64
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/image-tools/cutout/modnet/import",
                data={"manifest": json.dumps(manifest), "license_confirmed": "true"},
                files={"upload": ("portrait.onnx", payload, "application/octet-stream")},
            )
        # A syntactically valid manifest whose digest does not match the
        # uploaded bytes is a bad request at the import boundary.
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "modnet_manifest_mismatch"
        assert not manager.model_path.exists()
    finally:
        main.MODNET_IMPORT_MANAGER = previous


def test_modnet_import_refreshes_registry_after_runtime_probe(tmp_path, monkeypatch):
    manager, previous, manifest, payload = _request(tmp_path)

    class ReadyModNet:
        adapter_id = "modnet-portrait-onnx"

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def capabilities(self):
            return {
                "available": True,
                "executable": True,
                "state": "ready",
                "algorithm": "MODNet photographic portrait matting ONNX",
            }

    monkeypatch.setattr(main, "ModNetONNXAdapter", ReadyModNet)
    registry = create_default_registry()
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", registry)
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/image-tools/cutout/modnet/import",
                data={
                    "manifest": json.dumps(manifest),
                    "license_confirmed": "true",
                    "license_source": "user supplied checkpoint",
                },
                files={"upload": ("portrait.onnx", payload, "application/octet-stream")},
            )
        assert response.status_code == 201
        assert response.json()["runtime"]["executable"] is True
        assert "modnet-portrait-onnx" in registry.ids()
        assert "modnet-photographic-portrait" not in registry.ids()
        # Capability refreshes are invoked again by the browser-facing
        # endpoint. Once the placeholder has been replaced, they must update
        # the runtime entry in place instead of failing on the old id.
        first_refresh = main._refresh_modnet_registry(manager)
        second_refresh = main._refresh_modnet_registry(manager)
        assert first_refresh["executable"] is True
        assert second_refresh["executable"] is True
        assert registry.ids().count("modnet-portrait-onnx") == 1
        assert "modnet-photographic-portrait" not in registry.ids()
        capability = registry.probe()
        assert "modnet-portrait-onnx" in capability["adapters"]
    finally:
        main.MODNET_IMPORT_MANAGER = previous


def test_modnet_import_keeps_placeholder_when_runtime_probe_fails(tmp_path, monkeypatch):
    _manager, previous, manifest, payload = _request(tmp_path)

    class UnreadyModNet:
        adapter_id = "modnet-portrait-onnx"

        def __init__(self, **kwargs):
            pass

        def capabilities(self):
            return {"available": False, "executable": False, "state": "needs_dependency"}

    monkeypatch.setattr(main, "ModNetONNXAdapter", UnreadyModNet)
    registry = create_default_registry()
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", registry)
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/image-tools/cutout/modnet/import",
                data={"manifest": json.dumps(manifest), "license_confirmed": "true"},
                files={"upload": ("portrait.onnx", payload, "application/octet-stream")},
            )
        assert response.status_code == 201
        assert response.json()["runtime"]["executable"] is False
        assert "modnet-photographic-portrait" in registry.ids()
        assert "modnet-portrait-onnx" not in registry.ids()
    finally:
        main.MODNET_IMPORT_MANAGER = previous
