from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import numpy
import pytest
from PIL import Image

from image_tools.cutout_modnet import MODNET_ADAPTER_ID, ModNetONNXAdapter
from image_tools.cutout_onnx import CutoutOutputError, validate_output_png


def _image_data(size=(12, 8)) -> str:
    output = BytesIO()
    Image.new("RGB", size, (32, 96, 160)).save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _adapter(tmp_path: Path, *, license_confirmed=False):
    model = tmp_path / "modnet.onnx"
    model.write_bytes(b"synthetic-modnet")
    payload = model.read_bytes()
    manifest = {
        "filename": model.name,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "md5": hashlib.md5(payload).hexdigest(),
    }
    return ModNetONNXAdapter(
        model_path=model,
        model_manifest=manifest,
        license_confirmed=license_confirmed,
        license_source="user-provided checkpoint terms",
    )


class _FakeSession:
    def __init__(self, output, providers=None):
        self.output = output
        self.providers_arg = providers

    def get_providers(self):
        return ["CPUExecutionProvider"]

    def get_inputs(self):
        return [SimpleNamespace(name="input", shape=[1, 3, 8, 8])]

    def get_outputs(self):
        return [SimpleNamespace(name="pha", shape=[1, 1, 8, 8])]

    def run(self, _names, _feed):
        return [self.output]


def test_modnet_requires_explicit_license_confirmation(tmp_path):
    adapter = _adapter(tmp_path)
    capability = adapter.capabilities()
    assert capability["available"] is False
    assert capability["executable"] is False
    assert capability["reason"] == "modnet_license_unconfirmed"


def test_modnet_missing_or_mismatched_manifest_fails_closed(tmp_path):
    adapter = _adapter(tmp_path, license_confirmed=True)
    adapter.model_path.unlink()
    missing = adapter.capabilities()
    assert missing["reason"] == "modnet_model_missing"

    adapter.model_path.write_bytes(b"changed")
    mismatch = adapter.capabilities()
    assert mismatch["reason"] in {"modnet_model_size_mismatch", "modnet_model_hash_mismatch"}


def test_modnet_capability_requires_cpu_only_session(tmp_path):
    adapter = _adapter(tmp_path, license_confirmed=True)
    adapter._ort = SimpleNamespace(
        InferenceSession=lambda _path, providers: _FakeSession(
            numpy.zeros((1, 1, 8, 8), dtype=numpy.float32), providers
        )
    )
    adapter._numpy = numpy
    capability = adapter.capabilities()
    assert capability["available"] is True
    assert capability["executable"] is True
    assert capability["adapter"] == MODNET_ADAPTER_ID
    assert capability["input_size"] == [8, 8]
    assert capability["license_confirmed"] is True


def test_modnet_process_returns_same_size_rgba_png(tmp_path):
    adapter = _adapter(tmp_path, license_confirmed=True)
    mask = numpy.zeros((1, 1, 8, 8), dtype=numpy.float32)
    mask[:, :, 2:6, 2:6] = 1.0
    session = _FakeSession(mask)
    adapter._ort = SimpleNamespace(InferenceSession=lambda _path, providers: session)
    adapter._numpy = numpy
    result = adapter.process(_image_data())
    assert result["adapter"] == MODNET_ADAPTER_ID
    checked = validate_output_png(result["image_bytes"], (12, 8))
    assert checked["mode"] == "RGBA"
    assert checked["width"] == 12
    assert checked["height"] == 8


def test_modnet_process_preserves_alpha_endpoints_after_quantization(tmp_path):
    adapter = _adapter(tmp_path, license_confirmed=True)
    # Quantized checkpoints commonly return values just inside the endpoints;
    # the adapter must still emit explicit transparent and opaque pixels.
    mask = numpy.full((1, 1, 8, 8), 0.0001, dtype=numpy.float32)
    mask[:, :, 2:6, 2:6] = 0.9998
    session = _FakeSession(mask)
    adapter._ort = SimpleNamespace(InferenceSession=lambda _path, providers: session)
    adapter._numpy = numpy
    result = adapter.process(_image_data())
    with Image.open(BytesIO(result["image_bytes"])) as image:
        assert image.mode == "RGBA"
        assert image.getchannel("A").getextrema() == (0, 255)


def test_modnet_rejects_invalid_session_shape(tmp_path):
    adapter = _adapter(tmp_path, license_confirmed=True)

    class InvalidSession(_FakeSession):
        def get_inputs(self):
            return [SimpleNamespace(name="input", shape=[1, 4, 8, 8])]

    adapter._ort = SimpleNamespace(
        InferenceSession=lambda _path, providers: InvalidSession(
            numpy.zeros((1, 1, 8, 8), dtype=numpy.float32)
        )
    )
    adapter._numpy = numpy
    capability = adapter.capabilities()
    assert capability["available"] is False
    assert capability["reason"] == "modnet_session_invalid"
