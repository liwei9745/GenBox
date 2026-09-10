from __future__ import annotations

import asyncio
import base64
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import main
from image_tools.cutout_onnx import CutoutAdapterError, CutoutInputError
from image_tools.cutout_registry import (
    RMBG_2_DESCRIPTOR,
    CutoutAdapterRegistry,
    UnavailableCutoutAdapter,
    create_default_registry,
)


class FakeAdapter:
    def __init__(
        self,
        adapter_id: str,
        *,
        available: bool = True,
        failure: Exception | None = None,
    ):
        self.adapter_id = adapter_id
        self.available = available
        self.failure = failure
        self.calls = 0

    def capabilities(self):
        return {
            "contract": "genbox-cutout-v1",
            "available": self.available,
            "executable": self.available,
            "adapter": self.adapter_id,
            "state": "ready" if self.available else "unavailable",
        }

    async def process_async(self, image_data, *, timeout_seconds=None):
        self.calls += 1
        if self.failure:
            raise self.failure
        return {"image_bytes": b"png", "width": 2, "height": 2, "adapter": self.adapter_id}


def _png_bytes(size=(2, 2)) -> bytes:
    output = BytesIO()
    Image.new("RGBA", size, color=(32, 96, 160, 128)).save(output, format="PNG")
    return output.getvalue()


def _image_data() -> str:
    return "data:image/png;base64," + base64.b64encode(_png_bytes()).decode("ascii")


class RouteAdapter(FakeAdapter):
    async def process_async(self, image_data, *, timeout_seconds=None):
        self.calls += 1
        if self.failure:
            raise self.failure
        return {
            "image_bytes": _png_bytes(),
            "width": 2,
            "height": 2,
            "adapter": self.adapter_id,
        }

    def save_atomic(self, image_bytes, gallery_dir, *, expected_size=None):
        assert expected_size == (2, 2)
        target = Path(gallery_dir) / f"{self.adapter_id}.png"
        target.write_bytes(image_bytes)
        return target


def test_rmbg_descriptor_is_explicitly_unverified_and_non_executable():
    adapter = UnavailableCutoutAdapter(RMBG_2_DESCRIPTOR)
    capability = adapter.capabilities()
    assert capability["available"] is False
    assert capability["executable"] is False
    assert capability["state"] == "unavailable"
    assert capability["reason"] == "rmbg_weights_license_and_sha256_unverified"
    assert capability["descriptor"]["weight_sha256"] is None
    assert capability["descriptor"]["license"]["status"] == "NON_COMMERCIAL_ONLY_UNVERIFIED"


def test_registry_probe_keeps_unavailable_adapter_out_of_executable_list():
    registry = CutoutAdapterRegistry([UnavailableCutoutAdapter(RMBG_2_DESCRIPTOR)])
    snapshot = registry.probe()
    assert snapshot["available"] is False
    assert snapshot["executable"] is False
    assert snapshot["adapters"] == []
    assert snapshot["adapter_capabilities"][0]["adapter"] == "rmbg-2.0"


def test_registry_uses_requested_adapter_then_falls_back_on_runtime_failure():
    requested = FakeAdapter(
        "requested",
        failure=CutoutAdapterError("fake_failure", "synthetic failure", status_code=500),
    )
    fallback = FakeAdapter("fallback")
    registry = CutoutAdapterRegistry([requested, fallback])
    result = asyncio.run(registry.process_async(b"input", requested_adapter="requested"))
    assert result["adapter"] == "fallback"
    assert result["fallback_from"] == "requested"


def test_registry_fails_closed_when_no_adapter_is_executable():
    registry = CutoutAdapterRegistry([UnavailableCutoutAdapter(RMBG_2_DESCRIPTOR)])
    with pytest.raises(CutoutAdapterError) as caught:
        asyncio.run(registry.process_async(b"input"))
    assert caught.value.code == "rmbg_weights_license_and_sha256_unverified"
    assert caught.value.details["state"] == "unavailable"
    assert caught.value.details["attempts"][0]["adapter"] == "rmbg-2.0"


def test_registry_rejects_duplicate_ids():
    registry = CutoutAdapterRegistry([FakeAdapter("same")])
    with pytest.raises(ValueError):
        registry.register(FakeAdapter("same"))


def test_default_registry_preserves_legacy_u2net_selection_and_advertises_algorithms():
    u2net = FakeAdapter("u2net-human-seg-onnx")
    registry = create_default_registry(u2net)

    assert registry.resolve_request() == "u2net-human-seg-onnx"
    snapshot = registry.probe()
    assert snapshot["adapter"] == "u2net-human-seg-onnx"
    assert snapshot["adapters"] == ["u2net-human-seg-onnx"]
    assert len(snapshot["adapter_capabilities"]) == 5
    u2net_capability = snapshot["adapter_capabilities"][0]
    assert u2net_capability["algorithm"] == "U2Net human segmentation ONNX"
    assert "u2net" in u2net_capability["aliases"]
    adapters = {item["adapter"] for item in snapshot["adapter_capabilities"]}
    assert "rmbg-2.0" in adapters
    assert "inspyrenet" in adapters
    assert snapshot["adapter_capabilities"][-1]["executable"] is False


@pytest.mark.parametrize(
    "algorithm",
    [
        "U2Net human segmentation ONNX",
        "u2net",
        "u2net_human_seg",
        "u2net-human-seg-onnx",
    ],
)
def test_algorithm_must_be_the_selected_adapters_canonical_name_or_alias(algorithm):
    registry = create_default_registry(FakeAdapter("u2net-human-seg-onnx"))
    assert registry.resolve_request(
        adapter="u2net-human-seg-onnx",
        algorithm=algorithm,
    ) == "u2net-human-seg-onnx"


def test_registry_rejects_unknown_or_noncanonical_selection_fields():
    registry = create_default_registry(FakeAdapter("u2net-human-seg-onnx"))

    with pytest.raises(CutoutInputError) as unknown_adapter:
        registry.resolve_request(adapter="U2Net")
    assert unknown_adapter.value.code == "cutout_adapter_unknown"

    with pytest.raises(CutoutInputError) as padded_adapter:
        registry.resolve_request(adapter=" u2net-human-seg-onnx ")
    assert padded_adapter.value.code == "cutout_adapter_invalid"

    with pytest.raises(CutoutInputError) as unknown_algorithm:
        registry.resolve_request(algorithm="automatic-best-model")
    assert unknown_algorithm.value.code == "cutout_algorithm_unknown"

    with pytest.raises(CutoutInputError) as conflict:
        registry.resolve_request(adapter="u2net-human-seg-onnx", algorithm="rmbg")
    assert conflict.value.code == "cutout_adapter_algorithm_conflict"

    with pytest.raises(CutoutInputError) as implicit_switch:
        registry.resolve_request(algorithm="rmbg")
    assert implicit_switch.value.code == "cutout_adapter_algorithm_conflict"
    assert implicit_switch.value.details["adapter"] == "u2net-human-seg-onnx"


def test_unverified_requested_adapter_never_executes_or_falls_back():
    verified = FakeAdapter("verified")
    unverified = FakeAdapter("unverified")
    registry = CutoutAdapterRegistry(default_adapter_id="verified")
    registry.register(verified, verified=True, algorithm="Verified")
    registry.register(unverified, verified=False, algorithm="Unverified")

    with pytest.raises(CutoutAdapterError) as caught:
        asyncio.run(registry.process_async(b"input", adapter="unverified"))

    assert caught.value.code == "cutout_adapter_unavailable"
    assert unverified.calls == 0
    assert verified.calls == 0


def test_input_failure_does_not_trigger_runtime_fallback():
    requested = FakeAdapter(
        "requested",
        failure=CutoutInputError("invalid_image_payload", "invalid input"),
    )
    fallback = FakeAdapter("fallback")
    registry = CutoutAdapterRegistry([requested, fallback])

    with pytest.raises(CutoutInputError):
        asyncio.run(registry.process_async(b"input", adapter="requested"))

    assert requested.calls == 1
    assert fallback.calls == 0


def test_runtime_fallback_is_bounded_to_one_verified_executable_candidate():
    failure = CutoutAdapterError("fake_failure", "synthetic failure", status_code=500)
    requested = FakeAdapter("requested", failure=failure)
    first_fallback = FakeAdapter(
        "first-fallback",
        failure=CutoutAdapterError("fallback_failure", "synthetic failure", status_code=500),
    )
    untouched = FakeAdapter("untouched")
    registry = CutoutAdapterRegistry([requested, first_fallback, untouched])

    with pytest.raises(CutoutAdapterError) as caught:
        asyncio.run(registry.process_async(b"input", adapter="requested"))

    assert caught.value.code == "cutout_all_adapters_failed"
    assert caught.value.details["fallback_attempts"] == 1
    assert requested.calls == 1
    assert first_fallback.calls == 1
    assert untouched.calls == 0


def test_cutout_route_legacy_request_defaults_to_u2net(tmp_path, monkeypatch):
    u2net = RouteAdapter("u2net-human-seg-onnx")
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", create_default_registry(u2net))
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={"contract": "genbox-cutout-v1", "image_data": _image_data()},
    )

    assert response.status_code == 200
    assert response.json()["adapter"] == "u2net-human-seg-onnx"
    assert "fallback_from" not in response.json()
    assert u2net.calls == 1


def test_cutout_route_returns_explicit_bounded_fallback(tmp_path, monkeypatch):
    requested = RouteAdapter(
        "requested",
        failure=CutoutAdapterError("runtime_failed", "synthetic failure", status_code=500),
    )
    fallback = RouteAdapter("fallback")
    registry = CutoutAdapterRegistry(default_adapter_id="requested")
    registry.register(requested, verified=True, algorithm="Requested algorithm", algorithm_aliases=("requested-alias",))
    registry.register(fallback, verified=True, algorithm="Fallback algorithm")
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", registry)
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-v1",
            "image_data": _image_data(),
            "adapter": "requested",
            "algorithm": "requested-alias",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["adapter"] == "fallback"
    assert payload["fallback_from"] == "requested"
    assert requested.calls == 1
    assert fallback.calls == 1


@pytest.mark.parametrize(
    ("selection", "code"),
    [
        ({"adapter": "unknown"}, "cutout_adapter_unknown"),
        ({"algorithm": "unknown"}, "cutout_algorithm_unknown"),
        (
            {"adapter": "u2net-human-seg-onnx", "algorithm": "rmbg"},
            "cutout_adapter_algorithm_conflict",
        ),
    ],
)
def test_cutout_route_rejects_unknown_or_conflicting_selection(selection, code, monkeypatch):
    u2net = RouteAdapter("u2net-human-seg-onnx")
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", create_default_registry(u2net))

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-v1",
            "image_data": _image_data(),
            **selection,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code
    assert u2net.calls == 0


def test_cutout_route_never_executes_unverified_candidate(monkeypatch):
    verified = RouteAdapter("verified")
    unverified = RouteAdapter("unverified")
    registry = CutoutAdapterRegistry(default_adapter_id="verified")
    registry.register(verified, verified=True, algorithm="Verified")
    registry.register(unverified, verified=False, algorithm="Unverified")
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", registry)

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={
            "contract": "genbox-cutout-v1",
            "image_data": _image_data(),
            "adapter": "unverified",
            "algorithm": "Unverified",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "cutout_adapter_unavailable"
    assert unverified.calls == 0
    assert verified.calls == 0
