"""Deterministic, side-effect-free checks for known GenBox image integrations."""

from extensions.models import is_immutable_image_reference


# Keep this allowlist tied to an immutable, reviewed sender image. Unknown
# custom digests remain deployable after the normal plan review, but are never
# presented as GenBox-integrated without explicit evidence.
PROJECT_IMAGE_REFERENCE = (
    "ghcr.io/liwei9745/chatgpt2api@sha256:"
    "c9357b45b1339d2be4e4a02eb48f059562890f14bd9757b924d7fd7621b9e076"
)

KNOWN_GENBOX_INTEGRATED_IMAGES = frozenset({PROJECT_IMAGE_REFERENCE})


def check_image_integration(image: str) -> dict[str, object]:
    """Classify an image without registry, Docker, or SSH side effects."""
    normalized = str(image or "").strip()
    if not is_immutable_image_reference(normalized):
        raise ValueError("immutable_image_required")
    if normalized in KNOWN_GENBOX_INTEGRATED_IMAGES:
        return {
            "status": "integrated",
            "integration": "genbox-push-v1",
            "evidence": "known-reviewed-image",
        }
    return {
        "status": "unknown",
        "integration": "",
        "evidence": "not-in-local-capability-catalog",
    }
