"""Focused contracts for the optional local ONNX cutout adapter."""

import asyncio
import base64
import hashlib
import time
from io import BytesIO
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import SimpleNamespace

import numpy
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import main
import image_tools.cutout_onnx as cutout_onnx
from image_tools.cutout_onnx import (
    ADAPTER_ID,
    MODEL_RELATIVE_PATH,
    CutoutBusyError,
    CutoutONNXAdapter,
    CutoutOutputError,
    CutoutTimeoutError,
    validate_input_image,
    validate_output_png,
)


def _image_data(size=(12, 8), *, mode="RGB"):
    output = BytesIO()
    image = Image.new(mode, size, color=(32, 96, 160, 255) if mode == "RGBA" else (32, 96, 160))
    image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _rgba_png(size=(12, 8)):
    image = Image.new("RGBA", size, (32, 96, 160, 255))
    image.putpixel((0, 0), (32, 96, 160, 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _open_rgba(raw: bytes) -> Image.Image:
    with Image.open(BytesIO(raw)) as image:
        image.load()
        return image.copy()


def _adapter(tmp_path: Path, *, timeout_seconds=1.0):
    model = tmp_path / "model.onnx"
    model.write_bytes(b"synthetic-model")
    payload = model.read_bytes()
    manifest = {
        "filename": model.name,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "md5": hashlib.md5(payload).hexdigest(),
    }
    return CutoutONNXAdapter(model_path=model, model_manifest=manifest, timeout_seconds=timeout_seconds)


def test_default_model_path_uses_external_runtime_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(cutout_onnx.sys, "frozen", True, raising=False)
    executable = tmp_path / "desktop" / "GenBox.exe"
    executable.parent.mkdir()
    monkeypatch.setattr(cutout_onnx.sys, "executable", str(executable))
    monkeypatch.setattr(cutout_onnx.sys, "_MEIPASS", str(tmp_path / "pyinstaller-temp"), raising=False)

    frozen_adapter = CutoutONNXAdapter()

    expected = (executable.parent / MODEL_RELATIVE_PATH).resolve()
    assert frozen_adapter.base_path == executable.parent.resolve()
    assert frozen_adapter.model_path == expected
    assert not frozen_adapter.model_path.is_relative_to((tmp_path / "pyinstaller-temp").resolve())

    monkeypatch.setattr(cutout_onnx.sys, "frozen", False, raising=False)
    source_adapter = CutoutONNXAdapter()
    assert source_adapter.model_path == (
        Path(cutout_onnx.__file__).resolve().parents[1] / MODEL_RELATIVE_PATH
    ).resolve()
    assert main.CUTOUT_MODEL_PATH == main.BASE_DIR / MODEL_RELATIVE_PATH


class _FakeSession:
    def __init__(self, output=None, providers=None):
        self.output = output
        self.providers_arg = providers
        self.run_calls = []

    def get_providers(self):
        return ["CPUExecutionProvider"]

    def get_inputs(self):
        return [SimpleNamespace(name="input.1", shape=[1, 3, 320, 320])]

    def get_outputs(self):
        return [SimpleNamespace(name="mask", shape=[1, 1, 320, 320])]

    def run(self, _names, feed):
        self.run_calls.append(feed)
        return [self.output]


def _wire_session(adapter, session):
    class _FakeNumpy:
        pass

    adapter._ort = SimpleNamespace(
        InferenceSession=lambda _path, providers: session,
    )
    # Use the real NumPy module for preprocessing; dependency import itself is
    # still lazy in production.
    import numpy

    adapter._numpy = numpy
    return session


def test_manifest_missing_and_hash_mismatch_fail_closed(tmp_path):
    adapter = _adapter(tmp_path)
    adapter.model_path.unlink()
    missing = adapter.capabilities()
    assert missing["available"] is False
    assert missing["executable"] is False
    assert missing["reason"] == "cutout_model_missing"
    assert missing["needs_model"] is True

    adapter.model_path.write_bytes(b"changed-model")
    mismatch = adapter.capabilities()
    assert mismatch["available"] is False
    assert mismatch["reason"] in {"cutout_model_size_mismatch", "cutout_model_hash_mismatch"}


def test_missing_dependency_is_reported_without_importing_a_session(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path)

    def missing(_name):
        raise ImportError("synthetic missing optional dependency")

    monkeypatch.setattr("image_tools.cutout_onnx.importlib.import_module", missing)
    result = adapter.capabilities()
    assert result["available"] is False
    assert result["executable"] is False
    assert result["reason"] == "cutout_dependency_missing"
    assert result["needs_dependency"] is True
    assert adapter._session is None


def test_session_is_created_with_cpu_execution_provider_only(tmp_path):
    adapter = _adapter(tmp_path)
    import numpy

    captured = {}
    session = _FakeSession(output=numpy.zeros((1, 1, 8, 8), dtype=numpy.float32))

    def factory(path, providers):
        captured["path"] = path
        captured["providers"] = providers
        return session

    adapter._ort = SimpleNamespace(InferenceSession=factory)
    adapter._numpy = numpy
    result = adapter.capabilities()
    assert result["available"] is True
    assert result["executable"] is True
    assert captured["providers"] == ["CPUExecutionProvider"]
    assert result["cpu_execution_provider"] is True


def test_non_cpu_session_is_rejected(tmp_path):
    adapter = _adapter(tmp_path)
    import numpy

    class NonCpu(_FakeSession):
        def get_providers(self):
            return ["CPUExecutionProvider", "CUDAExecutionProvider"]

    adapter._ort = SimpleNamespace(InferenceSession=lambda _path, providers: NonCpu())
    adapter._numpy = numpy
    result = adapter.capabilities()
    assert result["available"] is False
    assert result["reason"] == "cutout_cpu_provider_required"


def test_output_validation_requires_rgba_png_matching_dimensions_and_extrema():
    valid = _rgba_png()
    checked = validate_output_png(valid, (12, 8))
    assert checked["mode"] == "RGBA"
    assert checked["format"] == "PNG"

    with pytest.raises(CutoutOutputError) as wrong_mode:
        raw = BytesIO()
        Image.new("RGB", (12, 8), (1, 2, 3)).save(raw, format="PNG")
        validate_output_png(raw.getvalue(), (12, 8))
    assert wrong_mode.value.code == "cutout_output_invalid"

    with pytest.raises(CutoutOutputError) as wrong_size:
        validate_output_png(_rgba_png((8, 12)), (12, 8))
    assert wrong_size.value.code == "cutout_output_size_mismatch"

    with pytest.raises(CutoutOutputError) as no_alpha:
        opaque = Image.new("RGBA", (12, 8), (1, 2, 3, 255))
        raw = BytesIO()
        opaque.save(raw, format="PNG")
        validate_output_png(raw.getvalue(), (12, 8))
    assert no_alpha.value.code == "cutout_output_alpha_invalid"


def test_input_validation_is_bounded_and_never_treats_path_as_image():
    decoded = validate_input_image(_image_data())
    assert decoded["width"] == 12 and decoded["height"] == 8
    with pytest.raises(Exception):
        validate_input_image("C:\\Users\\someone\\image.png")


def test_process_produces_same_size_rgba_result(tmp_path):
    import numpy

    adapter = _adapter(tmp_path)
    # A synthetic non-uniform mask exercises normalization and alpha checks.
    output = numpy.zeros((1, 1, 8, 8), dtype=numpy.float32)
    output[:, :, 2:6, 2:6] = 1.0
    session = _FakeSession(output=output)
    _wire_session(adapter, session)
    result = adapter.process(_image_data())
    checked = validate_output_png(result["image_bytes"], (12, 8))
    assert result["adapter"] == ADAPTER_ID
    assert checked["width"] == 12 and checked["height"] == 8
    assert session.run_calls


@pytest.mark.parametrize(
    "source_size,pad_axis,content_slice,pad_slice,sample_point",
    [
        ((160, 80), "vertical", (slice(80, 240), slice(0, 320)), (slice(0, 40), slice(0, 320)), (80, 40)),
        ((80, 160), "horizontal", (slice(0, 320), slice(80, 240)), (slice(0, 320), slice(0, 40)), (40, 80)),
    ],
)
def test_process_letterboxes_and_preserves_soft_alpha_without_min_max_outlier_spread(
    tmp_path,
    source_size,
    pad_axis,
    content_slice,
    pad_slice,
    sample_point,
):
    adapter = _adapter(tmp_path)
    source = _image_data(size=source_size)
    output = numpy.full((1, 1, 320, 320), 0.1, dtype=numpy.float32)
    if pad_axis == "vertical":
        output[:, :, content_slice[0], 150:170] = 0.9
    else:
        output[:, :, 150:170, content_slice[1]] = 0.9
    output[:, :, 0, 0] = 100.0
    session = _FakeSession(output=output)
    _wire_session(adapter, session)

    result = adapter.process(source)
    checked = validate_output_png(result["image_bytes"], source_size)
    refined = _open_rgba(result["image_bytes"])
    feed = session.run_calls[0]["input.1"]

    assert checked["width"] == source_size[0]
    assert checked["height"] == source_size[1]
    assert refined.size == source_size
    assert feed.shape == (1, 3, 320, 320)
    if pad_axis == "vertical":
        assert numpy.allclose(feed[0, :, 0, :], feed[0, :, 20, :])
        assert not numpy.allclose(feed[0, :, 0, :], feed[0, :, 160, :])
    else:
        assert numpy.allclose(feed[0, :, :, 0], feed[0, :, :, 20])
        assert not numpy.allclose(feed[0, :, :, 0], feed[0, :, :, 160])

    alpha = refined.getchannel("A")
    assert alpha.getpixel(sample_point) >= 220
    assert alpha.getpixel((0, 0)) <= 40


def test_single_flight_busy_and_soft_timeout_keep_lock_until_worker_finishes(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path, timeout_seconds=0.25)
    import numpy

    session = _FakeSession(output=numpy.zeros((1, 1, 8, 8), dtype=numpy.float32))
    _wire_session(adapter, session)
    started = asyncio.Event()

    def slow(_decoded, _session_info):
        started_loop = started
        # The worker cannot await, so signal through a thread-safe callback.
        started_loop._loop.call_soon_threadsafe(started_loop.set)
        time.sleep(0.45)
        return {"image_bytes": _rgba_png(), "width": 12, "height": 8, "adapter": ADAPTER_ID}

    monkeypatch.setattr(adapter, "_run_inference", slow)

    async def scenario():
        started._loop = asyncio.get_running_loop()
        first = asyncio.create_task(adapter.process_async(_image_data()))
        await asyncio.wait_for(started.wait(), timeout=1)
        with pytest.raises(CutoutBusyError):
            await adapter.process_async(_image_data())
        with pytest.raises(CutoutTimeoutError) as timeout:
            await first
        assert timeout.value.details["cancel_supported"] is False
        assert adapter.busy is True
        await asyncio.sleep(0.35)
        assert adapter.busy is False

    asyncio.run(scenario())


def test_atomic_save_uses_same_directory_and_leaves_no_temp_on_success(tmp_path):
    adapter = _adapter(tmp_path)
    gallery = tmp_path / "gallery"
    target = adapter.save_atomic(_rgba_png(), gallery, expected_size=(12, 8))
    assert target.parent == gallery
    assert target.suffix == ".png"
    assert target.exists()
    assert not list(gallery.glob("*.tmp"))
    assert validate_output_png(target.read_bytes(), (12, 8))["mode"] == "RGBA"


def test_cutout_success_response_omits_internal_filesystem_path(tmp_path, monkeypatch):
    class SuccessfulAdapter:
        def capabilities(self):
            return {"available": True, "executable": True}

        async def process_async(self, _image_data_value):
            return {
                "image_bytes": _rgba_png(),
                "width": 12,
                "height": 8,
                "adapter": ADAPTER_ID,
            }

        def save_atomic(self, image_bytes, gallery_dir, *, expected_size):
            assert expected_size == (12, 8)
            target = Path(gallery_dir) / "cutout response.png"
            target.write_bytes(image_bytes)
            return target.resolve()

    monkeypatch.setattr(main, "CUTOUT_ADAPTER", SuccessfulAdapter())
    monkeypatch.setattr(main, "CUTOUT_ADAPTERS", (ADAPTER_ID,))
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={"contract": "genbox-cutout-v1", "image_data": _image_data()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "local_path" not in payload
    public_strings = [
        value
        for key, value in payload.items()
        if isinstance(value, str) and key not in {"gallery_url", "image_data"}
    ]
    assert all(not PurePosixPath(value).is_absolute() for value in public_strings)
    assert all(not PureWindowsPath(value).is_absolute() for value in public_strings)
    assert all(str(tmp_path.resolve()) not in value for value in public_strings)
    assert payload["filename"] == "cutout response.png"
    assert payload["gallery_url"] == "/api/gallery/image/cutout%20response.png"
    assert payload["image_data"].startswith("data:image/png;base64,")
    assert payload["source_preserved"] is True
    assert payload["transparent"] is True
    assert payload["preview_background"] == "checkerboard"


def test_cutout_runtime_error_response_does_not_expose_internal_path(tmp_path, monkeypatch):
    internal_path = tmp_path.resolve() / "private-model.onnx"

    class FailingAdapter:
        def capabilities(self):
            return {"available": True, "executable": True}

        async def process_async(self, _image_data_value):
            raise RuntimeError(f"synthetic failure at {internal_path}")

    monkeypatch.setattr(main, "CUTOUT_ADAPTER", FailingAdapter())
    monkeypatch.setattr(main, "CUTOUT_ADAPTERS", (ADAPTER_ID,))

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={"contract": "genbox-cutout-v1", "image_data": _image_data()},
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert str(internal_path) not in " ".join(str(value) for value in detail.values())
    assert detail == {
        "code": "cutout_failed",
        "message": "本地抠图失败，未保存结果",
        "contract": "genbox-cutout-v1",
        "available": True,
        "executable": True,
        "adapters": [ADAPTER_ID],
        "cancel_supported": False,
    }
