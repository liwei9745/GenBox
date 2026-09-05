from __future__ import annotations

import asyncio
import hashlib
import io
import json
from pathlib import Path

import pytest

from image_tools.modnet_model_manager import (
    MODNET_IMPORT_CONTRACT,
    ModNetModelManager,
    ModNetModelManagerError,
)


PAYLOAD = b"synthetic-modnet-checkpoint"


def _manifest(payload: bytes = PAYLOAD) -> dict:
    return {
        "filename": "MODNet-v1.onnx",
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "md5": hashlib.md5(payload).hexdigest(),
        "license_confirmed": True,
        "license_source": "user-provided checkpoint terms",
    }


def _import(manager: ModNetModelManager, payload: bytes = PAYLOAD, **overrides):
    values = _manifest(payload)
    values.update(overrides)
    asyncio.run(manager.import_upload(io.BytesIO(payload), **values))
    return manager.status()


def test_import_is_atomic_and_status_hides_local_paths(tmp_path: Path):
    manager = ModNetModelManager(base_path=tmp_path)
    status = _import(manager)
    assert status["contract"] == MODNET_IMPORT_CONTRACT
    assert status["installed"] is True
    assert status["valid"] is True
    assert status["executable"] is False
    assert status["filename"] == "MODNet-v1.onnx"
    assert str(tmp_path) not in json.dumps(status)
    assert manager.model_path.read_bytes() == PAYLOAD
    assert manager.manifest_path.exists()


@pytest.mark.parametrize(
    "overrides, code",
    [
        ({"size_bytes": len(PAYLOAD) + 1}, "modnet_manifest_mismatch"),
        ({"sha256": "0" * 64}, "modnet_manifest_mismatch"),
        ({"md5": "0" * 32}, "modnet_manifest_mismatch"),
        ({"license_confirmed": False}, "modnet_license_unconfirmed"),
        ({"filename": "..\\escape.onnx"}, "modnet_filename_invalid"),
        ({"filename": "/tmp/escape.onnx"}, "modnet_filename_invalid"),
    ],
)
def test_import_rejects_bad_manifest_and_leaves_no_temp_files(tmp_path: Path, overrides, code):
    manager = ModNetModelManager(base_path=tmp_path)
    with pytest.raises(ModNetModelManagerError) as exc:
        _import(manager, **overrides)
    assert exc.value.code == code
    model_dir = tmp_path / "storage" / "models" / "cutout" / "modnet"
    assert not list(model_dir.glob("*.tmp"))
    assert manager.status()["installed"] is False


def test_import_rejects_over_limit_stream(tmp_path: Path):
    manager = ModNetModelManager(base_path=tmp_path, max_bytes=8)
    payload = b"0123456789"
    with pytest.raises(ModNetModelManagerError) as exc:
        _import(manager, payload, size_bytes=len(payload))
    assert exc.value.code == "modnet_model_too_large"


def test_failed_replacement_does_not_follow_existing_symlink(tmp_path: Path):
    manager = ModNetModelManager(base_path=tmp_path)
    model_dir = tmp_path / "storage" / "models" / "cutout" / "modnet"
    model_dir.mkdir(parents=True)
    outside = tmp_path / "outside.onnx"
    outside.write_bytes(b"keep")
    manager.model_path.symlink_to(outside)
    with pytest.raises(ModNetModelManagerError) as exc:
        _import(manager)
    assert exc.value.code == "modnet_target_symlink"
    assert outside.read_bytes() == b"keep"


def test_import_rejects_symlinked_model_directory(tmp_path: Path):
    manager = ModNetModelManager(base_path=tmp_path)
    model_root = tmp_path / "storage" / "models" / "cutout"
    model_root.mkdir(parents=True)
    outside = tmp_path / "outside-modnet"
    outside.mkdir()
    (model_root / "modnet").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ModNetModelManagerError) as exc:
        _import(manager)
    assert exc.value.code == "modnet_import_directory_invalid"
    assert not (outside / "modnet.onnx").exists()


def test_delete_isolated_model_only(tmp_path: Path):
    manager = ModNetModelManager(base_path=tmp_path)
    _import(manager)
    status = manager.delete()
    assert status["installed"] is False
    assert not manager.model_path.exists()
    assert not manager.manifest_path.exists()
