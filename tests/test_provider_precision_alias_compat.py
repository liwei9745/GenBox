"""Regression coverage for explicitly confirmed precision model aliases."""
from __future__ import annotations

import asyncio
import base64
from io import BytesIO

import pytest
from PIL import Image

import providers
from config import ProviderConfig, PrecisionEditProfile


def _data_url(size=(1024, 1024)) -> str:
    output = BytesIO()
    Image.new("RGB", size, (32, 96, 160)).save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _alias_provider(
    *,
    alias_of: str | None = "gpt-image-2",
    canonical_sizes: list[str] | None = ["1024x1024", "1536x864"],
    canonical_confirmed: bool = True,
) -> ProviderConfig:
    model_capabilities = {
        "gpt-image2-b": {
            "precision_edit": True,
            "supported_sizes": ["1792x768", "1536x864"],
        },
    }
    if alias_of is not None:
        model_capabilities["gpt-image2-b"]["alias_of"] = alias_of
        canonical = {"precision_edit": canonical_confirmed}
        if canonical_sizes is not None:
            canonical["supported_sizes"] = canonical_sizes
        model_capabilities[alias_of] = canonical
    return ProviderConfig(
        id="precision-provider",
        name="Precision Mock",
        type="image",
        api_key="synthetic-key",
        base_url="https://provider.example.test/v1",
        model="gpt-image2-b",
        enabled=True,
        endpoint_type="openai",
        precision_edit_profile=PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE,
        capabilities={"precision_edit": True},
        extra={"model_capabilities": model_capabilities},
    )


def test_precision_preserve_accepts_explicitly_reviewed_alias():
    provider = _alias_provider()

    assert providers._precision_preserve_source_size_error(
        provider, "gpt-image2-b", (1024, 1024)
    ) is None


def test_precision_preserve_keeps_gate_without_confirmed_canonical():
    provider = _alias_provider(canonical_confirmed=False)

    error = providers._precision_preserve_source_size_error(
        provider, "gpt-image2-b", (1024, 1024)
    )

    assert error is not None
    assert error[0] == "precision_edit_source_size_not_declared"


@pytest.mark.parametrize(
    "alias_of",
    ["gpt-image2", "gpt_image2", "gpt-image2-b-extra", "gpt-image2-b"],
)
def test_precision_preserve_does_not_guess_alias_from_name(alias_of):
    provider = _alias_provider(alias_of=None)
    provider.extra["model_capabilities"]["gpt-image2-b"]["alias_of"] = alias_of

    error = providers._precision_preserve_source_size_error(
        provider, "gpt-image2-b", (1024, 1024)
    )

    assert error is not None
    assert error[0] == "precision_edit_source_size_not_declared"


def test_precision_preserve_rejects_explicit_alias_without_canonical_sizes():
    provider = _alias_provider(canonical_sizes=None)

    error = providers._precision_preserve_source_size_error(
        provider, "gpt-image2-b", (1024, 1024)
    )

    assert error is not None
    assert error[0] == "precision_edit_source_size_not_declared"


@pytest.mark.parametrize(
    ("source_size", "expected_code"),
    [
        ((64, 64), "precision_target_size_pixels_too_small"),
        ((1920, 1080), "precision_target_size_alignment_invalid"),
    ],
)
def test_precision_preserve_alias_enforces_canonical_protocol_even_when_declared(
    source_size,
    expected_code,
):
    declared_size = f"{source_size[0]}x{source_size[1]}"
    provider = _alias_provider(canonical_sizes=[declared_size])

    error = providers._precision_preserve_source_size_error(
        provider,
        "gpt-image2-b",
        source_size,
    )

    assert error is not None
    assert error[0] == expected_code


def test_precision_preserve_rejects_unknown_model_before_http(monkeypatch):
    provider = _alias_provider(alias_of=None)
    provider.extra["model_capabilities"]["gpt-image2-b"].pop("supported_sizes")
    constructions = []

    def forbidden_client(**kwargs):
        constructions.append(kwargs)
        raise AssertionError("unknown precision size must fail before HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    source = _data_url()
    result = asyncio.run(
        providers._dispatch_generate(
            provider,
            "strict edit",
            "openai",
            mode="precision_edit",
            image_data=source,
            annotation_image_data=source,
            annotation_contract=providers.PRECISION_ANNOTATION_CONTRACT_V2,
            annotations=[
                {
                    "type": "arrow",
                    "label": 1,
                    "instruction": "Keep the marked subject unchanged.",
                    "x1": 0.1,
                    "y1": 0.1,
                    "x2": 0.2,
                    "y2": 0.2,
                },
            ],
            precision_edit_authorized=True,
            precision_size_mode="preserve",
            model="gpt-image2-b",
        )
    )

    assert result.success is False
    assert "precision_edit_size_capability_unknown" in result.error
    assert constructions == []


@pytest.mark.parametrize("alias_field", ["alias_of", "canonical_model"])
@pytest.mark.parametrize(
    ("target_size", "ratio_label"),
    [("1536x864", "16:9"), ("1792x768", "21:9")],
)
def test_precision_canonical_only_alias_supports_declared_strict_sizes_and_keeps_outbound_alias(
    monkeypatch,
    alias_field,
    target_size,
    ratio_label,
):
    provider = _alias_provider(canonical_sizes=["1024x1024", target_size])
    provider.extra["model_capabilities"]["gpt-image2-b"] = {alias_field: "gpt-image-2"}
    calls = []
    response_size = tuple(int(part) for part in target_size.split("x", 1))
    response_image = _data_url(size=response_size).split(",", 1)[1]

    class Response:
        status_code = 200

        def json(self):
            return {"data": [{"b64_json": response_image}]}

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")
    source = _data_url(size=(1024, 1024))

    assert providers._precision_preserve_source_size_error(
        provider, "gpt-image2-b", (1024, 1024)
    ) is None
    result = asyncio.run(
        providers._dispatch_generate(
            provider,
            "expand the canvas",
            "openai",
            mode="precision_edit",
            image_data=source,
            precision_canvas_only=True,
            precision_edit_authorized=True,
            precision_size_mode="resize",
            precision_target_size=target_size,
            precision_resize_prompt="Extend the background without cropping the subject.",
            model="gpt-image2-b",
        )
    )

    assert result.success is True
    assert calls[0][1]["data"]["model"] == "gpt-image2-b"
    assert calls[0][1]["data"]["size"] == target_size
    assert f"({ratio_label})" in calls[0][1]["data"]["prompt"]


def test_precision_alias_resize_enforces_canonical_protocol_even_when_declared():
    provider = _alias_provider(canonical_sizes=["1792x768", "1920x1080"])

    assert providers.precision_model_uses_gpt_image_2_size_contract(
        provider,
        "gpt-image2-b",
    ) is True
    assert providers._precision_size_error(
        provider,
        "gpt-image2-b",
        "resize",
        "1920x1080",
        "",
    ) == (
        "precision_target_size_alignment_invalid",
        "gpt-image-2 dimensions must be divisible by 16",
    )


def test_unconfirmed_alias_still_uses_normal_t2i_and_keeps_outbound_model(monkeypatch):
    provider = _alias_provider(canonical_confirmed=False)
    calls = []
    response_image = _data_url().split(",", 1)[1]

    class Response:
        status_code = 200

        def json(self):
            return {"data": [{"b64_json": response_image}]}

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

        async def aclose(self):
            return None

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(
            provider,
            "ordinary text to image",
            "openai",
            mode="t2i",
            model="gpt-image2-b",
            size="1024x1024",
        )
    )

    assert result.success is True
    assert len(calls) == 1
    assert calls[0][0] == "https://provider.example.test/v1/images/generations"
    assert calls[0][1]["json"]["model"] == "gpt-image2-b"


@pytest.mark.parametrize(
    "records",
    [
        {
            "gpt-image2-b": {"alias_of": "gpt-image-2"},
            "gpt-image-2": {"alias_of": "gpt-image2-b", "precision_edit": True, "supported_sizes": ["64x64"]},
        },
        {
            "gpt-image2-b": {"alias_of": "middle"},
            "middle": {"alias_of": "gpt-image-2"},
            "gpt-image-2": {"precision_edit": True, "supported_sizes": ["64x64"]},
        },
        {
            "gpt-image2-b": {"alias_of": "gpt-image-2", "canonical_model": "other"},
            "gpt-image-2": {"precision_edit": True, "supported_sizes": ["64x64"]},
            "other": {"precision_edit": True, "supported_sizes": ["64x64"]},
        },
        {
            "gpt-image2-b": {"alias_of": "gpt-image-2"},
            "gpt-image-2": {"precision_edit": True, "supported_sizes": ["64x64", "invalid"]},
        },
    ],
)
def test_precision_invalid_alias_graph_or_sizes_reject_before_http(monkeypatch, records):
    provider = _alias_provider(canonical_sizes=["64x64"])
    provider.extra["model_capabilities"] = records
    constructions = []
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: constructions.append(kwargs))

    result = asyncio.run(
        providers._dispatch_generate(
            provider,
            "expand the canvas",
            "openai",
            mode="precision_edit",
            image_data=_data_url(size=(64, 64)),
            precision_canvas_only=True,
            precision_edit_authorized=True,
            precision_size_mode="resize",
            precision_target_size="64x64",
            precision_resize_prompt="Extend the background naturally.",
            model="gpt-image2-b",
        )
    )

    assert result.success is False
    assert constructions == []
