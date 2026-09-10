from __future__ import annotations

import asyncio

import pytest

from image_tools.cutout_inspyrenet import (
    ADAPTER_ID,
    UNAVAILABLE_CODE,
    InSPyReNetCutoutAdapter,
    create_inspyrenet_adapter,
)
from image_tools.cutout_onnx import CutoutUnavailableError


def test_inspyrenet_is_fail_closed_and_does_not_require_optional_imports():
    adapter = create_inspyrenet_adapter()
    capability = adapter.capabilities()
    assert isinstance(adapter, InSPyReNetCutoutAdapter)
    assert capability["adapter"] == ADAPTER_ID
    assert capability["available"] is False
    assert capability["executable"] is False
    assert capability["adapters"] == []
    assert capability["verification_status"] == "UNVERIFIED"
    assert capability["reason"] == UNAVAILABLE_CODE
    assert capability["descriptor"]["weight_sha256"] is None


def test_inspyrenet_process_returns_structured_unavailable_error_without_network():
    with pytest.raises(CutoutUnavailableError) as exc:
        asyncio.run(InSPyReNetCutoutAdapter().process_async(b"not-an-image"))
    assert exc.value.code == UNAVAILABLE_CODE
    assert exc.value.details["adapter"] == ADAPTER_ID
    assert exc.value.details["needs_model"] is True
    assert exc.value.details["needs_dependency"] is True


def test_descriptor_exposes_reviewable_provenance_and_aliases():
    descriptor = InSPyReNetCutoutAdapter().descriptor
    assert descriptor["source_page"].startswith("https://github.com/")
    assert descriptor["license"]["status"] == "UNVERIFIED"
    assert "inspyrenet" in descriptor["aliases"]
