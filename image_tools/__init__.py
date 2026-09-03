"""Local image-tool adapters.

The optional tools in this package are deliberately imported lazily.  GenBox
can therefore start normally when an optional model or runtime dependency is
not installed; capability checks report that state instead of making startup
fail.
"""

from .cutout_onnx import (
    ADAPTER_ID,
    CUTOUT_CONTRACT,
    MODEL_MANIFEST,
    CutoutAdapterError,
    CutoutBusyError,
    CutoutONNXAdapter,
    CutoutOutputError,
    CutoutPersistenceError,
    CutoutTimeoutError,
    atomic_save_png,
    validate_input_image,
    validate_output_png,
)
from .cutout_refine import (
    CUTOUT_REFINE_CONTRACT,
    CUTOUT_SELECTION_MASK_CONTRACT,
    MAX_FEATHER_RADIUS,
    CutoutRefineError,
    CutoutRefineInputError,
    CutoutRefineOutputError,
    CutoutRefinePersistenceError,
    refine_cutout_alpha,
    save_refined_png_atomic,
    validate_refine_source,
    validate_refined_png,
    validate_selection_mask,
)

__all__ = [
    "ADAPTER_ID",
    "CUTOUT_CONTRACT",
    "MODEL_MANIFEST",
    "CutoutAdapterError",
    "CutoutBusyError",
    "CutoutONNXAdapter",
    "CutoutOutputError",
    "CutoutPersistenceError",
    "CutoutTimeoutError",
    "atomic_save_png",
    "validate_input_image",
    "validate_output_png",
    "CUTOUT_REFINE_CONTRACT",
    "CUTOUT_SELECTION_MASK_CONTRACT",
    "MAX_FEATHER_RADIUS",
    "CutoutRefineError",
    "CutoutRefineInputError",
    "CutoutRefineOutputError",
    "CutoutRefinePersistenceError",
    "refine_cutout_alpha",
    "save_refined_png_atomic",
    "validate_refine_source",
    "validate_refined_png",
    "validate_selection_mask",
]
