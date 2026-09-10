from __future__ import annotations

import io
import socket
from types import SimpleNamespace

from PIL import Image

from image_tools.cutout_quality_gate import (
    CutoutQualityGateError,
    QUALITY_GATE_CONTRACT,
    SYNTHETIC_SAMPLE_SIZE,
    run_adapter_gate,
    run_quality_gate,
)


def _rgba_png(size=SYNTHETIC_SAMPLE_SIZE) -> bytes:
    image = Image.new("RGBA", size, (24, 48, 72, 255))
    image.putpixel((0, 0), (24, 48, 72, 0))
    image.putpixel((1, 0), (24, 48, 72, 128))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class _Adapter:
    adapter_id = "test-adapter"

    def __init__(self, *, cpu=True, connect=False):
        self.cpu = cpu
        self.connect = connect
        self.invalidated = False

    def invalidate_session(self):
        self.invalidated = True

    def capabilities(self):
        return {
            "available": True,
            "executable": True,
            "cpu_execution_provider": self.cpu,
            "model": {
                "filename": "model.onnx",
                "size_bytes": 123,
                "sha256": "a" * 64,
                "md5": "b" * 32,
            },
        }

    def process(self, _image_data):
        if self.connect:
            socket.create_connection(("example.invalid", 443))
        return {"image_bytes": _rgba_png()}


def test_gate_reports_cpu_offline_rgba_size_and_alpha_evidence():
    adapter = _Adapter()
    report = run_adapter_gate(adapter)

    assert report["contract"] == QUALITY_GATE_CONTRACT
    assert report["passed"] is True
    assert adapter.invalidated is True
    assert report["runtime"]["cpu_execution_provider"] is True
    assert report["runtime"]["python_network_blocked"] is True
    assert report["runtime"]["network_attempts"] == 0
    assert report["output"]["format"] == "PNG"
    assert report["output"]["mode"] == "RGBA"
    assert report["output"]["size"] == list(SYNTHETIC_SAMPLE_SIZE)
    assert report["output"]["alpha"]["extrema"] == [0, 255]
    assert report["output"]["alpha"]["soft_alpha_pixels"] == 1
    assert report["quality_scope"]["authorized_human_legs_hair_soft_edges"] == "UNVERIFIED"


def test_gate_fails_closed_when_adapter_attempts_network():
    report = run_adapter_gate(_Adapter(connect=True))

    assert report["passed"] is False
    assert report["code"] == "network_attempt_blocked"
    assert report["runtime"]["network_attempts"] == 1


def test_gate_rejects_adapter_without_explicit_cpu_only_capability():
    report = run_adapter_gate(_Adapter(cpu=False))

    assert report["passed"] is False
    assert report["code"] == "cpu_provider_unverified"


def test_quality_gate_reports_unknown_optional_model_without_local_paths(tmp_path):
    report = run_quality_gate(base_path=tmp_path, adapter_ids=("missing",))

    assert report["passed"] is False
    assert report["results"][0]["code"] == "adapter_unknown"
    assert str(tmp_path) not in str(report)


def test_quality_gate_routes_each_adapter_through_isolated_worker(tmp_path, monkeypatch):
    calls = []

    def fake_worker(adapter_id, base_path):
        calls.append((adapter_id, base_path))
        return {"adapter": adapter_id, "passed": True}

    monkeypatch.setattr(
        "image_tools.cutout_quality_gate._isolated_adapter_gate_report",
        fake_worker,
    )

    report = run_quality_gate(base_path=tmp_path, adapter_ids=("first", "second"))

    assert report["passed"] is True
    assert [item[0] for item in calls] == ["first", "second"]
    assert all(item[1] == tmp_path.resolve() for item in calls)
