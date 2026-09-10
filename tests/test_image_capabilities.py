import asyncio

import pytest
from fastapi import HTTPException

import main
from extensions.image_capabilities import PROJECT_IMAGE_REFERENCE, UPSTREAM_IMAGE_REFERENCE, check_image_integration
from extensions.models import ImageIntegrationCheckRequest


def test_known_project_image_is_confirmed_without_external_inspection():
    result = check_image_integration(PROJECT_IMAGE_REFERENCE)

    assert result == {
        "status": "integrated",
        "integration": "genbox-push-v1",
        "evidence": "known-reviewed-image",
    }


def test_unknown_but_immutable_image_is_not_presented_as_integrated():
    result = check_image_integration("registry.example/chatgpt2api@sha256:" + "a" * 64)

    assert result == {
        "status": "unknown",
        "integration": "",
        "evidence": "not-in-local-capability-catalog",
    }


def test_upstream_image_is_selectable_but_explicitly_not_integrated():
    result = check_image_integration(UPSTREAM_IMAGE_REFERENCE)

    assert result == {
        "status": "not_integrated",
        "integration": "",
        "evidence": "known-upstream-image",
    }


def test_image_integration_route_rejects_mutable_reference_without_remote_work():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.extension_image_integration_check(ImageIntegrationCheckRequest(
            image="ghcr.io/example/chatgpt2api:latest",
        )))

    assert exc.value.status_code == 400
    assert exc.value.detail == "immutable_image_required"
