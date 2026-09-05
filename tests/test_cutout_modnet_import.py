from __future__ import annotations

import io
import json
import asyncio
from pathlib import Path

import pytest

from image_tools.cutout_modnet_import import (
    DEFAULT_MODEL_FILENAME,
    MODNET_IMPORT_DIR,
    ModNetImportError,
    ModNetModelImportManager,
)
from image_tools.cutout_modnet import MODNET_MODEL_RELATIVE_PATH, ModNetONNXAdapter


def manager(tmp_path: Path, **kwargs):
    return ModNetModelImportManager(base_path=tmp_path, **kwargs)


def test_import_manager_and_adapter_share_canonical_model_path(tmp_path):
    instance = manager(tmp_path)
    adapter = ModNetONNXAdapter(base_path=tmp_path)
    expected = tmp_path / MODNET_IMPORT_DIR / DEFAULT_MODEL_FILENAME
    assert instance.model_path == expected
    assert adapter.model_path == expected
    assert MODNET_MODEL_RELATIVE_PATH == MODNET_IMPORT_DIR / DEFAULT_MODEL_FILENAME


def test_imports_content_atomically_and_writes_manifest(tmp_path):
    payload = b"onnx-content"
    result = manager(tmp_path).import_bytes(
        payload,
        filename="portrait.onnx",
        license_confirmed=True,
        license_source="user-confirmed local checkpoint license",
    )
    assert result.model_path.read_bytes() == payload
    assert result.model_path.parent == tmp_path / "storage/models/cutout/modnet"
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["size_bytes"] == len(payload)
    assert manifest["sha256"] == result.sha256
    assert manifest["md5"] == result.md5
    assert manifest["license_confirmed"] is True


def test_rejects_paths_urls_and_unconfirmed_license(tmp_path):
    with pytest.raises(ModNetImportError) as exc:
        manager(tmp_path).import_content("C:/secret/modnet.onnx", license_confirmed=True)
    assert exc.value.code == "modnet_upload_content_required"
    with pytest.raises(ModNetImportError) as exc:
        manager(tmp_path).import_content(io.BytesIO(b"x"))
    assert exc.value.code == "modnet_license_unconfirmed"


def test_rejects_oversize_and_empty_upload(tmp_path):
    instance = manager(tmp_path, max_bytes=3)
    with pytest.raises(ModNetImportError) as exc:
        instance.import_bytes(b"1234", license_confirmed=True)
    assert exc.value.code == "modnet_model_too_large"
    with pytest.raises(ModNetImportError) as exc:
        instance.import_bytes(b"", license_confirmed=True)
    assert exc.value.code == "modnet_model_empty"


def test_rejects_manifest_mismatch_without_installing(tmp_path):
    instance = manager(tmp_path)
    with pytest.raises(ModNetImportError) as exc:
        instance.import_bytes(
            b"abc",
            license_confirmed=True,
            expected={"size_bytes": 9},
        )
    # A manifest that omits required hashes is malformed before comparison.
    assert exc.value.code == "modnet_manifest_invalid"
    assert not (tmp_path / "storage/models/cutout/modnet/modnet.onnx").exists()


def test_rejects_unsafe_filename_and_symlink_target(tmp_path):
    with pytest.raises(ModNetImportError):
        manager(tmp_path).import_bytes(b"x", filename="../evil.onnx", license_confirmed=True)
    instance = manager(tmp_path)
    instance.model_dir.mkdir(parents=True)
    target = instance.model_dir / "modnet.onnx"
    target.symlink_to(tmp_path / "outside.onnx")
    with pytest.raises(ModNetImportError) as exc:
        instance.import_bytes(b"x", license_confirmed=True)
    assert exc.value.code == "modnet_target_symlink"


def test_import_upload_reads_starlette_style_content(tmp_path):
    class Upload:
        filename = "from-browser.onnx"

        def __init__(self):
            self.parts = [b"abc", b"123", b""]

        async def read(self, _size):
            return self.parts.pop(0)

    result = asyncio.run(manager(tmp_path).import_upload(
        Upload(), license_confirmed=True, license_source="user-confirmed"
    ))
    assert result.filename == "from-browser.onnx"
    assert result.model_path.read_bytes() == b"abc123"
