"""Fail-closed InSPyReNet cutout candidate adapter.

InSPyReNet remains an explicitly unavailable candidate until GenBox has a
fixed, locally supplied checkpoint with verified provenance, license terms,
and an offline runtime probe. This module has no download or implicit model
loading path.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from image_tools.cutout_onnx import CUTOUT_CONTRACT, CutoutUnavailableError


ADAPTER_ID = "inspyrenet"
ALGORITHM = "InSPyReNet salient object segmentation"
SOURCE_PAGE = "https://github.com/plemeri/InSPyReNet"
MODEL_SOURCE = "Official model zoo checkpoint; fixed local artifact not verified"
LICENSE_NAME = "MIT code; checkpoint terms unverified"
LICENSE_STATUS = "UNVERIFIED"
UNAVAILABLE_CODE = "inspyrenet_weights_license_and_sha256_unverified"

DESCRIPTOR: Mapping[str, Any] = {
    "adapter_id": ADAPTER_ID,
    "algorithm": ALGORITHM,
    "status": "UNVERIFIED",
    "source_page": SOURCE_PAGE,
    "weights_source": MODEL_SOURCE,
    "license": {"name": LICENSE_NAME, "status": LICENSE_STATUS},
    "weight_sha256": None,
    "dependencies": ["torch", "Pillow", "numpy"],
    "aliases": ["inspyrenet", "inspyrenet salient object segmentation"],
    "reason": UNAVAILABLE_CODE,
}


class InSPyReNetCutoutAdapter:
    """Descriptive candidate that fails closed until evidence is complete."""

    adapter_id = ADAPTER_ID
    algorithm = ALGORITHM
    algorithm_aliases = tuple(DESCRIPTOR["aliases"])
    contract = CUTOUT_CONTRACT
    descriptor = DESCRIPTOR

    def capabilities(self) -> dict[str, Any]:
        return {
            "contract": CUTOUT_CONTRACT,
            "available": False,
            "executable": False,
            "adapters": [],
            "adapter": ADAPTER_ID,
            "algorithm": ALGORITHM,
            "verification_status": "UNVERIFIED",
            "state": "unavailable",
            "reason": UNAVAILABLE_CODE,
            "code": UNAVAILABLE_CODE,
            "message": "InSPyReNet 尚未完成固定权重、许可证和离线运行验证",
            "needs_model": True,
            "needs_dependency": True,
            "descriptor": dict(DESCRIPTOR),
        }

    capability = capabilities
    get_capabilities = capabilities
    probe = capabilities

    async def process_async(
        self,
        image_data: object,
        *,
        timeout_seconds: Optional[object] = None,
    ) -> Mapping[str, Any]:
        del image_data, timeout_seconds
        raise CutoutUnavailableError(
            UNAVAILABLE_CODE,
            "InSPyReNet 尚未完成固定权重、许可证和离线运行验证",
            state="unavailable",
            adapter=ADAPTER_ID,
            adapters=[],
            needs_model=True,
            needs_dependency=True,
            descriptor=dict(DESCRIPTOR),
        )


def create_inspyrenet_adapter() -> InSPyReNetCutoutAdapter:
    """Return the candidate adapter without importing optional runtimes."""

    return InSPyReNetCutoutAdapter()


__all__ = [
    "ADAPTER_ID",
    "ALGORITHM",
    "DESCRIPTOR",
    "InSPyReNetCutoutAdapter",
    "create_inspyrenet_adapter",
]
