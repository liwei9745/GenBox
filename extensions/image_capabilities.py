"""Deterministic, side-effect-free checks for known GenBox image integrations."""

from extensions.models import is_immutable_image_reference


# Keep this allowlist tied to an immutable, reviewed sender image. Unknown
# custom digests remain deployable after the normal plan review, but are never
# presented as GenBox-integrated without explicit evidence.
PROJECT_IMAGE_REFERENCE = (
    "ghcr.io/liwei9745/chatgpt2api@sha256:"
    "c9357b45b1339d2be4e4a02eb48f059562890f14bd9757b924d7fd7621b9e076"
)
UPSTREAM_IMAGE_REFERENCE = (
    "ghcr.io/yukkcat/chatgpt2api@sha256:"
    "6b6386007d01c5d22475d9f097ab4b4b5876ee4d76229442ef9ac57172ebd0a7"
)

KNOWN_GENBOX_INTEGRATED_IMAGES = frozenset({PROJECT_IMAGE_REFERENCE})
KNOWN_NON_INTEGRATED_IMAGES = frozenset({UPSTREAM_IMAGE_REFERENCE})


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
    if normalized in KNOWN_NON_INTEGRATED_IMAGES:
        return {
            "status": "not_integrated",
            "integration": "",
            "evidence": "known-upstream-image",
        }
    return {
        "status": "unknown",
        "integration": "",
        "evidence": "not-in-local-capability-catalog",
    }
