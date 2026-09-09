"""Provider-layer fail-closed tests for annotation-based precision editing."""
from __future__ import annotations

import asyncio
import base64
import json
from io import BytesIO
from pathlib import Path

import pytest

from PIL import Image

import providers
from config import EndpointConfig, PrecisionEditProfile, ProviderConfig


def _data_url(*, size=(12, 8), color=(32, 96, 160)) -> str:
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _image_bytes(*, image_format="PNG", mode="RGB", size=(12, 8)) -> bytes:
    output = BytesIO()
    if mode == "P":
        image = Image.new("P", size, 1)
        image.putpalette([0, 0, 0, 32, 96, 160] + [0, 0, 0] * 254)
    else:
        color = (32, 96, 160, 128) if mode == "RGBA" else (32, 96, 160)
        image = Image.new(mode, size, color)
    image.save(output, format=image_format)
    return output.getvalue()


def test_save_image_transcodes_jpeg_without_prompt_to_real_png(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)

    saved = providers._save_image(
        _image_bytes(image_format="JPEG"),
        "precision-provider",
        "precision_empty_prompt",
        "",
    )

    payload = tmp_path.joinpath(saved).read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(payload)) as image:
        assert image.format == "PNG"
        assert image.mode == "RGB"


def test_save_image_preserves_prompt_metadata_after_png_normalization(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)

    saved = providers._save_image(
        _image_bytes(image_format="JPEG"),
        "precision-provider",
        "precision_prompt",
        "Synthetic prompt",
    )

    with Image.open(saved) as image:
        assert image.format == "PNG"
        assert image.info["Prompt"] == "Synthetic prompt"
        assert image.info["Model"] == "precision-provider"
        assert image.info["CreatedAt"]


def test_save_image_persists_precision_transform_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)
    precision_metadata = {
        "requested_size": "1536x864",
        "provider_actual_size": "1376x768",
        "final_size": "1536x864",
        "policy": "fit_crop",
        "aspect_ratio_delta": 0.0078125,
        "transform": {
            "operation": "center_cover_crop",
            "scale_factor": 1.125,
            "scaled_size": "1548x864",
            "crop_box": [6, 0, 1542, 864],
            "resample": "LANCZOS",
        },
    }

    saved = providers._save_image(
        _image_bytes(mode="RGBA"),
        "precision-provider",
        "precision_metadata",
        "Synthetic prompt",
        generation_metadata=precision_metadata,
    )

    with Image.open(saved) as image:
        assert image.info["GenBoxGenerationMetadata"] == providers.json.dumps(
            precision_metadata,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "P"])
def test_save_image_normalizes_common_png_modes(monkeypatch, tmp_path, mode):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)

    saved = providers._save_image(
        _image_bytes(mode=mode),
        "precision-provider",
        f"precision_{mode}",
        "",
    )

    with Image.open(saved) as image:
        assert image.format == "PNG"
        assert image.mode == mode


def test_save_image_rejects_unreadable_payload_without_writing(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)

    with pytest.raises(ValueError, match="readable image"):
        providers._save_image(
            b"not-an-image",
            "precision-provider",
            "precision_invalid",
            "",
        )

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("../escaped", "escaped"),
        (r"..\escaped", "escaped"),
        (r"C:\temp\escaped", "C_temp_escaped"),
        ("模型", "model"),
        ("", "model"),
        ("CON", "model_CON"),
    ],
)
def test_gallery_filename_slug_is_ascii_path_safe_and_has_fallback(value, expected):
    slug = providers._safe_gallery_slug(value, "model")

    assert slug == expected
    assert "/" not in slug
    assert "\\" not in slug
    assert ".." not in slug
    assert slug.isascii()


@pytest.mark.parametrize("model_id", ["../escaped", r"..\escaped", "模型", ""])
def test_save_image_confines_unsafe_model_ids_to_gallery(monkeypatch, tmp_path, model_id):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)
    before_parent = set(tmp_path.parent.iterdir())

    saved = Path(providers._save_image(
        _image_bytes(image_format="JPEG"),
        model_id,
        "precision",
        "",
    )).resolve()

    assert saved.parent == tmp_path.resolve()
    assert saved.name.endswith(".png")
    assert "/" not in saved.name
    assert "\\" not in saved.name
    assert ".." not in saved.name
    assert set(tmp_path.parent.iterdir()) == before_parent


def test_save_image_uses_same_directory_atomic_replace(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)
    calls = []
    events = []
    real_replace = providers.os.replace
    real_fsync = providers.os.fsync

    def record_fsync(fd):
        events.append("fsync")
        return real_fsync(fd)

    def record_replace(source, target):
        source_path = Path(source)
        target_path = Path(target)
        assert source_path.parent.resolve() == tmp_path.resolve()
        assert target_path.parent.resolve() == tmp_path.resolve()
        assert source_path.exists()
        assert not target_path.exists()
        with Image.open(source_path) as image:
            assert image.format == "PNG"
            image.load()
        assert events == ["fsync"]
        events.append("replace")
        calls.append((source_path, target_path))
        return real_replace(source_path, target_path)

    monkeypatch.setattr(providers.os, "fsync", record_fsync)
    monkeypatch.setattr(providers.os, "replace", record_replace)

    saved = Path(providers._save_image(
        _image_bytes(image_format="JPEG"),
        "precision-provider",
        "precision_atomic",
        "",
    ))

    assert len(calls) == 1
    assert calls[0][1] == saved
    assert events == ["fsync", "replace"]
    assert saved.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_save_image_replace_failure_cleans_temp_and_preserves_existing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)
    existing = tmp_path / "existing.png"
    existing_payload = _image_bytes()
    existing.write_bytes(existing_payload)

    def fail_replace(_source, _target):
        raise OSError("synthetic atomic publish failure")

    monkeypatch.setattr(providers.os, "replace", fail_replace)

    with pytest.raises(OSError, match="synthetic atomic publish failure"):
        providers._save_image(
            _image_bytes(image_format="JPEG"),
            "precision-provider",
            "precision_atomic_failure",
            "",
        )

    assert existing.read_bytes() == existing_payload
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob("*.png")) == [existing]


def _single_profile_kwargs(**overrides) -> dict:
    source = _data_url(size=(64, 64))
    values = {
        "image_data": source,
        "annotation_image_data": _data_url(size=(64, 64), color=(220, 32, 48)),
    }
    values.update(overrides)
    return _v2_kwargs(**values)


def _provider(
    capable: bool = True,
    endpoint_type: str = "openai",
    supported_sizes=None,
    *,
    model: str = "mock-edit-1",
    precision_edit_profile=None,
) -> ProviderConfig:
    capabilities = {"precision_edit": True} if capable else {}
    model_capabilities = {"precision_edit": True}
    if supported_sizes is not None:
        model_capabilities["supported_sizes"] = supported_sizes
    elif (
        precision_edit_profile == PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
    ):
        # Preserve-mode source dimensions require an explicit reviewed size.
        model_capabilities["supported_sizes"] = ["64x64"]
    extra = {"model_capabilities": {model: model_capabilities}} if capable else {}
    return ProviderConfig(
        id="precision-provider",
        name="Precision Mock",
        type="image",
        api_key="test-key",
        base_url="https://provider.example.test/v1",
        model=model,
        size="1024x1024",
        quality="high",
        enabled=True,
        endpoint_type=endpoint_type,
        capabilities=capabilities,
        precision_edit_profile=precision_edit_profile,
        extra=extra,
    )


def _v2_kwargs(**overrides) -> dict:
    image_data = _data_url()
    values = {
        "mode": "precision_edit",
        "image_data": image_data,
        "annotation_image_data": image_data,
        "annotation_contract": providers.PRECISION_ANNOTATION_CONTRACT_V2,
        "annotations": [
            {
                "type": "arrow",
                "label": 1,
                "instruction": "Replace the marked cup with a glass cup.",
                "x1": 0.10,
                "y1": 0.20,
                "x2": 0.60,
                "y2": 0.70,
            },
            {
                "type": "text",
                "label": 2,
                "text": "NEW SIGN",
                "x": 0.25,
                "y": 0.18,
            },
        ],
        "precision_edit_authorized": True,
        "model": "mock-edit-1",
        "precision_size_mode": "preserve",
        "quality": "high",
    }
    values.update(overrides)
    return values


def _v3_kwargs(**overrides) -> dict:
    values = _v2_kwargs(
        annotation_contract=providers.PRECISION_ANNOTATION_CONTRACT_V3,
        annotations=[
            {
                "type": "ellipse",
                "label": 1,
                "instruction": "Make the marked badge blue.",
                "x": 0.2,
                "y": 0.15,
                "width": 0.3,
                "height": 0.4,
            },
            {
                "type": "brush",
                "label": 2,
                "instruction": "Remove the marked reflection.",
                "points": [{"x": 0.1, "y": 0.2}, {"x": 0.4, "y": 0.5}],
            },
        ],
    )
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "size,expected_code",
    [
        ("1280x720", None),
        ("1536x864", None),
        ("1792x768", None),
        ("2560x1440", None),
        ("3840x2160", None),
        ("1920x1080", "precision_target_size_alignment_invalid"),
        ("640x640", "precision_target_size_pixels_too_small"),
        ("64x10000", "precision_target_size_side_exceeded"),
        ("16x4096", "precision_target_size_side_exceeded"),
        ("64x2048", "precision_target_size_aspect_invalid"),
        ("3840x3840", "precision_target_size_pixels_exceeded"),
    ],
)
def test_gpt_image_2_exact_size_protocol(size, expected_code):
    error = providers.gpt_image_2_size_error(size)
    assert (None if error is None else error[0]) == expected_code


def test_gpt_image_2_legal_size_still_requires_explicit_declaration():
    provider = _provider(model="gpt-image-2", supported_sizes=["1280x720"])
    assert providers._precision_size_error(
        provider, "gpt-image-2", "resize", "1536x864", ""
    ) == (
        "precision_edit_target_size_not_declared",
        "the selected model has not declared this target size",
    )


def test_gpt_image_2_confirmed_whitelist_rejects_unverified_2k_and_4k_presets():
    """A model without the opt-in policy must enforce its empirical whitelist."""
    provider = _provider(
        model="gpt-image2-bc",
        supported_sizes=["2048x1152", "1152x2048"],
    )

    assert providers._precision_size_error(
        provider, "gpt-image2-bc", "resize", "2048x1152", ""
    ) is None
    assert providers._precision_size_error(
        provider, "gpt-image2-bc", "resize", "1152x2048", ""
    ) is None
    for unverified_size in ("3840x1648", "3840x2160", "2544x1088"):
        assert providers._precision_size_error(
            provider, "gpt-image2-bc", "resize", unverified_size, ""
        ) == (
            "precision_edit_target_size_not_declared",
            "the selected model has not declared this target size",
        )


def test_crop_fit_allows_a_legal_target_outside_the_strict_whitelist():
    provider = _provider(
        model="gpt-image2-bc",
        supported_sizes=["2048x1152", "1152x2048"],
    )

    assert providers._precision_size_error(
        provider,
        "gpt-image2-bc",
        "resize",
        "3840x1648",
        "",
        "strict",
    ) == (
        "precision_edit_target_size_not_declared",
        "the selected model has not declared this target size",
    )
    assert providers._precision_size_error(
        provider,
        "gpt-image2-bc",
        "resize",
        "3840x1648",
        "",
        "fit_crop",
    ) is None


@pytest.mark.parametrize(
    "target_size",
    [
        "1024x1024", "1168x656", "656x1168", "1024x768", "768x1024", "1008x672", "672x1008", "1344x576", "576x1344",
        "2048x2048", "2048x1152", "1152x2048", "2048x1536", "1536x2048", "2016x1344", "1344x2016", "2544x1088", "1088x2544",
        "2880x2880", "3840x2160", "2160x3840", "3328x2480", "2480x3328", "3520x2352", "2352x3520", "3840x1648", "1648x3840",
        "1536x864",
    ],
)
def test_flexible_gpt_image_2_policy_accepts_every_legal_tier_ratio_and_custom_size(target_size):
    provider = _provider(model="gateway-gpt-image-2", supported_sizes=["2048x1152"])
    provider.extra["model_capabilities"]["gateway-gpt-image-2"]["size_policy"] = "gpt_image_2_flexible"

    assert providers._precision_size_error(
        provider, "gateway-gpt-image-2", "resize", target_size, ""
    ) is None


def test_flexible_gpt_image_2_policy_still_rejects_illegal_custom_size():
    provider = _provider(model="gateway-gpt-image-2", supported_sizes=["2048x1152"])
    provider.extra["model_capabilities"]["gateway-gpt-image-2"]["size_policy"] = "gpt_image_2_flexible"

    assert providers._precision_size_error(
        provider, "gateway-gpt-image-2", "resize", "1920x1080", ""
    ) == (
        "precision_target_size_alignment_invalid",
        "gpt-image-2 dimensions must be divisible by 16",
    )


def test_gpt_image_2_rejects_illegal_size_even_when_declared():
    provider = _provider(model="gpt-image-2", supported_sizes=["1920x1080"])
    assert providers._precision_size_error(
        provider, "gpt-image-2", "resize", "1920x1080", ""
    ) == (
        "precision_target_size_alignment_invalid",
        "gpt-image-2 dimensions must be divisible by 16",
    )


def _resize_only_kwargs(**overrides) -> dict:
    values = {
        "mode": "precision_edit",
        "image_data": _data_url(size=(64, 48)),
        "precision_canvas_only": True,
        "precision_edit_authorized": True,
        "model": "mock-edit-1",
        "precision_size_mode": "resize",
        "precision_target_size": "64x64",
        "precision_resize_prompt": "Extend the background naturally on every side.",
        "quality": "high",
    }
    values.update(overrides)
    return values


class _Response:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _RetryResponse(_Response):
    def __init__(self, status_code: int, payload=None, text: str = ""):
        super().__init__(status_code, payload=payload, text=text)
        self.reason_phrase = {429: "Too Many Requests", 503: "Service Unavailable"}.get(
            status_code,
            "Bad Request",
        )
        self.request = None


class _StreamResponse:
    def __init__(self, status_code=200, headers=None, chunks=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks or []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


def test_precision_dispatch_rejects_protocol_mismatch_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("precision edit must not open HTTP for an unverified protocol")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "auto",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert "precision_edit_protocol_unverified" in result.error
    assert client_constructions == []


def test_precision_dispatch_requires_explicit_model_capability(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("precision edit must not open HTTP without model capability")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(capable=False),
            "strict edit",
            "openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert "precision_edit_capability_not_authorized" in result.error
    assert client_constructions == []


def test_precision_dispatch_rejects_unknown_contract_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("precision edit must not open HTTP for an unknown contract")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(annotation_contract="annotation-v9"),
        )
    )

    assert result.success is False
    assert "precision_annotation_contract_unsupported" in result.error
    assert client_constructions == []


def test_precision_dispatch_accepts_v2_and_sends_annotation_multipart(monkeypatch):
    calls = []
    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "Overall: keep the lighting.",
            "openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://provider.example.test/v1/images/edits"
    assert request["headers"] == {"Authorization": "Bearer test-key"}
    assert request["data"]["model"] == "mock-edit-1"
    assert request["data"]["size"] == "auto"
    assert request["data"]["quality"] == "high"
    assert "preserve the source canvas (12x8)" in request["data"]["prompt"]
    assert "Label 1 (arrow): edit instruction=\"Replace the marked cup with a glass cup.\"" in request["data"]["prompt"]
    assert "Label 2 (text): output text=\"NEW SIGN\"" in request["data"]["prompt"]
    assert '"number"' not in request["data"]["prompt"]
    files = request["files"]
    assert [name for name, _ in files] == ["image", "image"]
    assert files[0][1][2] == "image/png"
    assert files[1][1][2] == "image/png"


def test_precision_explicit_image_array_profile_uses_fixed_field_and_alias_model(monkeypatch):
    calls = []
    alias = "gpt-image2-b"
    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(
                model=alias,
                supported_sizes=["64x64"],
                precision_edit_profile=(
                    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_IMAGE_ARRAY
                ),
            ),
            "strict edit",
            "openai",
            **_v2_kwargs(model=alias),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://provider.example.test/v1/images/edits"
    assert request["data"]["model"] == alias
    assert [name for name, _ in request["files"]] == ["image[]", "image[]"]


def test_precision_single_source_image_profile_uses_explicit_alias_mapping_and_real_model_name(monkeypatch):
    calls = []
    alias = "gpt-image2-b"
    source_image = _data_url(size=(1024, 1024), color=(8, 16, 24))
    annotation_image = _data_url(size=(1024, 1024), color=(220, 32, 48))
    source_bytes = base64.b64decode(source_image.split(",", 1)[1])
    response_image = _data_url(size=(1024, 1024)).split(",", 1)[1]

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    provider = _provider(
        model="gpt-image-2",
        supported_sizes=["1024x1024"],
        precision_edit_profile=(
            PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
        ),
    )
    provider.model = alias
    provider.models = [alias]
    provider.extra["model_capabilities"][alias] = {"alias_of": "gpt-image-2"}

    result = asyncio.run(
        providers._dispatch_generate(
            provider,
            "strict edit",
            "openai",
            **_v2_kwargs(
                model=alias,
                image_data=source_image,
                annotation_image_data=annotation_image,
            ),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://provider.example.test/v1/images/edits"
    assert request["data"]["model"] == alias
    assert request["data"]["size"] == "1024x1024"
    assert request["data"]["n"] == 1
    assert "prompt" in request["data"]
    assert [name for name, _ in request["files"]] == ["image"]
    assert request["files"][0][1][0] == "source.png"
    assert request["files"][0][1][1] == source_bytes
    assert request["files"][0][1][2] == "image/png"
    assert request["files"][0][1][1] != base64.b64decode(annotation_image.split(",", 1)[1])


def test_precision_single_source_profile_repairs_allowed_stale_source_mime(monkeypatch):
    calls = []
    alias = "gpt-image2-b"
    source_bytes = _image_bytes(image_format="JPEG", size=(1024, 1024))
    source_image = "data:image/png;base64," + base64.b64encode(source_bytes).decode("ascii")
    annotation_image = _data_url(size=(1024, 1024), color=(220, 32, 48))
    response_image = _data_url(size=(1024, 1024)).split(",", 1)[1]

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    provider = _provider(
        model="gpt-image-2",
        supported_sizes=["1024x1024"],
        precision_edit_profile=(
            PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
        ),
    )
    provider.model = alias
    provider.models = [alias]
    provider.extra["model_capabilities"][alias] = {"alias_of": "gpt-image-2"}

    result = asyncio.run(
        providers._dispatch_generate(
            provider,
            "strict edit",
            "openai",
            **_v2_kwargs(
                model=alias,
                image_data=source_image,
                annotation_image_data=annotation_image,
            ),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    source_part = calls[0][1]["files"][0]
    assert source_part[0] == "image"
    assert source_part[1][0] == "source.jpg"
    assert source_part[1][1] == source_bytes
    assert source_part[1][2] == "image/jpeg"


@pytest.mark.parametrize(
    "unconfirmed_model",
    [
        "custom-image-model",
        "gpt-image2-preview",
        "gpt-image2-unrelated",
        "gpt-image2-c",
        "gpt-image2-d",
    ],
)
def test_precision_unconfirmed_catalog_model_never_inherits_gpt_image_2_before_http(
    monkeypatch,
    unconfirmed_model,
):
    provider = _provider(
        model="gpt-image-2",
        precision_edit_profile=(
            PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
        ),
    )
    provider.model = unconfirmed_model
    provider.models = [unconfirmed_model]
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            provider,
            "strict edit",
            "openai",
            **_v2_kwargs(
                model=unconfirmed_model,
                image_data=_data_url(size=(64, 64)),
                annotation_image_data=_data_url(size=(64, 64), color=(220, 32, 48)),
            ),
        )
    )

    assert result.success is False
    assert "precision_edit_capability_not_authorized" in result.error
    assert client_constructions == []


def test_precision_single_source_image_profile_resize_uses_explicit_target(monkeypatch):
    calls = []
    target_size = "64x64"
    response_image = _data_url(size=(64, 64)).split(",", 1)[1]

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    source = _data_url(size=(64, 64))
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(
                supported_sizes=[target_size],
                precision_edit_profile=(
                    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
                ),
            ),
            "strict edit",
            "openai",
            **_v2_kwargs(
                image_data=source,
                annotation_image_data=_data_url(size=(64, 64), color=(220, 32, 48)),
                precision_size_mode="resize",
                precision_target_size=target_size,
                precision_resize_prompt="Extend the background naturally.",
            ),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    assert calls[0][1]["data"]["size"] == target_size
    assert [name for name, _ in calls[0][1]["files"]] == ["image"]


@pytest.mark.parametrize(
    ("profile", "expected_field"),
    [
        (None, "image"),
        (PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_IMAGE_ARRAY, "image[]"),
        (PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE, "image"),
    ],
)
def test_precision_resize_only_sends_one_source_and_explicit_outpaint_prompt(
    monkeypatch,
    profile,
    expected_field,
):
    calls = []
    alias = "relay-defined-image-alias"
    response_image = _data_url(size=(64, 64)).split(",", 1)[1]

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(
                model=alias,
                supported_sizes=["64x64"],
                precision_edit_profile=profile,
            ),
            "Keep the person and foreground unchanged.",
            "openai",
            **_resize_only_kwargs(model=alias),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://provider.example.test/v1/images/edits"
    assert request["data"]["model"] == alias
    assert request["data"]["size"] == "64x64"
    assert [name for name, _ in request["files"]] == [expected_field]
    prompt = request["data"]["prompt"].lower()
    assert "outpaint" in prompt
    assert "reframe" in prompt
    assert "64x64" in prompt
    assert "keep the person and foreground unchanged" in prompt
    assert "extend the background naturally on every side" in prompt


@pytest.mark.parametrize(
    "stray_fields",
    [
        {"annotation_image_data": None},
        {"annotation_contract": ""},
        {"annotations": []},
        {"annotation_contract": providers.PRECISION_ANNOTATION_CONTRACT_V3},
    ],
)
def test_precision_resize_only_rejects_annotation_fields_before_http(monkeypatch, stray_fields):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["64x64"]),
            "strict resize",
            "openai",
            **_resize_only_kwargs(**stray_fields),
        )
    )

    assert result.success is False
    assert "precision_resize_annotation_fields_conflict" in result.error
    assert client_constructions == []


@pytest.mark.parametrize("request_kwargs", [_v2_kwargs(), _resize_only_kwargs()])
@pytest.mark.parametrize("image_list_value", [[], None])
def test_precision_provider_rejects_image_data_list_key_presence_before_http(
    monkeypatch,
    request_kwargs,
    image_list_value,
):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )
    request_kwargs = dict(request_kwargs)
    request_kwargs["image_data_list"] = image_list_value

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["64x64"]),
            "strict edit",
            "openai",
            **request_kwargs,
        )
    )

    assert result.success is False
    assert "precision_edit_single_image_required" in result.error
    assert client_constructions == []


def test_precision_resize_only_fields_require_precision_mode_before_http(monkeypatch):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["64x64"]),
            "strict resize",
            "openai",
            **_resize_only_kwargs(mode="t2i"),
        )
    )

    assert result.success is False
    assert "precision_edit_mode_required" in result.error
    assert client_constructions == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "t2i", "precision_output_size_policy": "fit_crop"},
        _v2_kwargs(precision_output_size_policy="strict"),
    ],
)
def test_precision_output_size_policy_rejects_non_resize_provider_dispatch(monkeypatch, kwargs):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **client_kwargs: client_constructions.append(client_kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **kwargs,
        )
    )

    assert result.success is False
    assert result.error_code in {
        "precision_edit_mode_required",
        "precision_output_size_policy_not_allowed",
    }
    assert client_constructions == []


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"precision_size_mode": "preserve", "precision_target_size": ""}, "precision_canvas_only_resize_required"),
        ({"precision_resize_prompt": ""}, "precision_resize_prompt_required"),
        ({"precision_resize_prompt": "https://example.invalid/private"}, "precision_resize_prompt_invalid"),
    ],
)
def test_precision_resize_only_rejects_invalid_mode_or_guidance_before_http(
    monkeypatch,
    overrides,
    expected_code,
):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["64x64"]),
            "strict resize",
            "openai",
            **_resize_only_kwargs(**overrides),
        )
    )

    assert result.success is False
    assert expected_code in result.error
    assert client_constructions == []


@pytest.mark.parametrize("source_size", [(63, 64), (8193, 64)])
def test_precision_single_source_image_rejects_unsafe_preserve_source_size_before_http(
    monkeypatch,
    source_size,
):
    source = _data_url(size=source_size)
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(
                precision_edit_profile=(
                    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
                ),
            ),
            "strict edit",
            "openai",
            **_v2_kwargs(
                image_data=source,
                annotation_image_data=_data_url(size=source_size, color=(220, 32, 48)),
            ),
        )
    )

    assert result.success is False
    assert "precision_edit_source_size_invalid" in result.error
    assert client_constructions == []


def test_precision_single_source_image_rejects_undeclared_preserve_source_size_before_http(monkeypatch):
    source = _data_url(size=(64, 64))
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(
                supported_sizes=["1024x1024"],
                precision_edit_profile=(
                    PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
                ),
            ),
            "strict edit",
            "openai",
            **_v2_kwargs(
                image_data=source,
                annotation_image_data=_data_url(size=(64, 64), color=(220, 32, 48)),
            ),
        )
    )

    assert result.success is False
    assert "precision_edit_source_size_not_declared" in result.error
    assert client_constructions == []


def test_precision_profile_enum_rejects_arbitrary_transport_values():
    with pytest.raises(ValueError):
        _provider(precision_edit_profile="https://attacker.example.test/custom")


@pytest.mark.parametrize("retry_status", [429, 503])
def test_precision_retryable_status_is_not_replayed(monkeypatch, retry_status):
    calls = []
    sleeps = []

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _RetryResponse(retry_status, text="temporary failure")

        async def aclose(self):
            return None

    async def no_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers.asyncio, "sleep", no_sleep)
    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **_v2_kwargs())
    )

    assert result.success is False
    assert result.error_code == "precision_edit_upstream_error"
    assert len(calls) == 1
    assert {url for url, _ in calls} == {"https://provider.example.test/v1/images/edits"}
    assert [[name for name, _ in request["files"]] for _, request in calls] == [
        ["image", "image"],
    ]
    assert sleeps == []


@pytest.mark.parametrize("retry_status", [429, 503])
@pytest.mark.parametrize(
    "profile",
    [None, PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE],
)
def test_precision_retryable_status_stops_after_one_attempt(monkeypatch, retry_status, profile):
    calls = []
    sleeps = []
    request_kwargs = _single_profile_kwargs() if profile else _v2_kwargs()

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _RetryResponse(retry_status, text="temporary failure")

        async def aclose(self):
            return None

    async def no_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers.asyncio, "sleep", no_sleep)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(precision_edit_profile=profile),
            "strict edit",
            "openai",
            **request_kwargs,
        )
    )

    assert result.success is False
    assert "precision_edit_upstream_error" in result.error
    assert f"HTTP {retry_status}" in result.error
    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize(
    "profile",
    [None, PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE],
)
def test_precision_4xx_is_not_retried(monkeypatch, profile):
    calls = []
    sleeps = []
    request_kwargs = _single_profile_kwargs() if profile else _v2_kwargs()

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _RetryResponse(422, text="invalid request")

        async def aclose(self):
            return None

    async def no_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers.asyncio, "sleep", no_sleep)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(precision_edit_profile=profile),
            "strict edit",
            "openai",
            **request_kwargs,
        )
    )

    assert result.success is False
    assert "precision_edit_upstream_error" in result.error
    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("retry_status", [429, 503])
@pytest.mark.parametrize(
    "profile, expected_fields",
    [
        (None, ["image", "image"]),
        (
            PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE,
            ["image"],
        ),
    ],
)
def test_precision_multi_endpoint_stops_after_one_non_replayable_post(
    monkeypatch,
    retry_status,
    profile,
    expected_fields,
):
    provider = _provider(precision_edit_profile=profile)
    request_kwargs = _single_profile_kwargs() if profile else _v2_kwargs()
    provider.endpoints = [
        EndpointConfig(
            name=f"endpoint-{index}",
            url=f"https://endpoint-{index}.example.test/v1",
            key=f"test-key-{index}",
        )
        for index in range(1, 4)
    ]
    calls = []
    sleeps = []

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            if "endpoint-1." in url:
                return _RetryResponse(422, text="endpoint contract rejected")
            return _RetryResponse(retry_status, text="temporary failure")

        async def aclose(self):
            return None

    async def no_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers.asyncio, "sleep", no_sleep)

    result = asyncio.run(
        providers.generate_for_provider(
            provider,
            "strict edit",
            protocol="openai",
            **request_kwargs,
        )
    )

    assert result.success is False
    assert result.error_code == "precision_edit_upstream_error"
    assert len(calls) == 1
    assert [url for url, _ in calls] == [
        "https://endpoint-1.example.test/v1/images/edits",
    ]
    assert all(
        [name for name, _ in request["files"]] == expected_fields
        for _, request in calls
    )
    assert sleeps == []


@pytest.mark.parametrize(
    "profile",
    [None, PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE],
)
def test_precision_cancellation_closes_client_and_never_switches_endpoint(monkeypatch, profile):
    provider = _provider(precision_edit_profile=profile)
    request_kwargs = _single_profile_kwargs() if profile else _v2_kwargs()
    provider.endpoints = [
        EndpointConfig(
            name=f"endpoint-{index}",
            url=f"https://endpoint-{index}.example.test/v1",
            key=f"test-key-{index}",
        )
        for index in range(1, 3)
    ]
    calls = []
    closed = []

    async def scenario():
        started = asyncio.Event()
        blocked = asyncio.Event()

        class Client:
            async def post(self, url, **kwargs):
                calls.append((url, kwargs))
                started.set()
                await blocked.wait()
                raise AssertionError("cancelled POST must not resume")

            async def aclose(self):
                closed.append(True)

        monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
        task = asyncio.create_task(
            providers.generate_for_provider(
                provider,
                "strict edit",
                protocol="openai",
                **request_kwargs,
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    assert len(calls) == 1
    assert calls[0][0] == "https://endpoint-1.example.test/v1/images/edits"
    assert closed == [True]


def test_precision_cancellation_survives_client_close_failure(monkeypatch):
    provider = _provider()
    provider.endpoints = [
        EndpointConfig(
            name=f"endpoint-{index}",
            url=f"https://endpoint-{index}.example.test/v1",
            key=f"test-key-{index}",
        )
        for index in range(1, 3)
    ]
    calls = []
    close_calls = []

    async def scenario():
        started = asyncio.Event()
        blocked = asyncio.Event()

        class Client:
            async def post(self, url, **kwargs):
                calls.append((url, kwargs))
                started.set()
                await blocked.wait()
                raise AssertionError("cancelled POST must not resume")

            async def aclose(self):
                close_calls.append(True)
                raise RuntimeError("synthetic close failure")

        monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
        task = asyncio.create_task(
            providers.generate_for_provider(
                provider,
                "strict edit",
                protocol="openai",
                **_v2_kwargs(),
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    assert len(calls) == 1
    assert calls[0][0] == "https://endpoint-1.example.test/v1/images/edits"
    assert close_calls == [True]


def test_openai_t2i_keeps_generations_json_transport(monkeypatch):
    calls = []
    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

        async def aclose(self):
            return None

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(providers._gen_openai(_provider(), "text to image", size="12x8"))

    assert result.success is True
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://provider.example.test/v1/images/generations"
    assert request["json"]["model"] == "mock-edit-1"
    assert "files" not in request


def test_precision_preserve_allows_auto_but_rejects_other_generic_size_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("invalid preserve size must not open HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    rejected = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(size="1024x1024"),
        )
    )

    assert rejected.success is False
    assert "precision_preserve_size_conflict" in rejected.error
    assert client_constructions == []

    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            assert kwargs["data"]["size"] == "auto"
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")
    allowed = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(size="auto"),
        )
    )

    assert allowed.success is True


def test_precision_dispatch_accepts_v3_and_describes_new_geometry(monkeypatch):
    calls = []
    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(kwargs)
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(_provider(), "Keep the lighting.", "openai", **_v3_kwargs())
    )

    assert result.success is True
    prompt = calls[0]["data"]["prompt"]
    assert 'Label 1 (ellipse): edit instruction="Make the marked badge blue."' in prompt
    assert 'Label 2 (brush): edit instruction="Remove the marked reflection."' in prompt
    assert '"type":"ellipse"' in prompt
    assert '"type":"brush"' in prompt
    assert '"points":[{"x":0.1,"y":0.2},{"x":0.4,"y":0.5}]' in prompt
    assert "Remove all annotation arrows, rectangles, ellipses, freehand strokes" in prompt


@pytest.mark.parametrize(
    ("annotation", "expected_instruction", "expected_geometry"),
    [
        (
            {
                "type": "arrow", "label": 1, "instruction": "Move the marker.",
                "x1": 0.1, "y1": 0.2, "x2": 0.7, "y2": 0.8,
            },
            'Label 1 (arrow): edit instruction="Move the marker."',
            '"type":"arrow","label":1,"x1":0.1,"y1":0.2,"x2":0.7,"y2":0.8',
        ),
        (
            {
                "type": "rectangle", "label": 1, "instruction": "Replace this region.",
                "x": 0.1, "y": 0.2, "width": 0.6, "height": 0.5,
            },
            'Label 1 (rectangle): edit instruction="Replace this region."',
            '"type":"rectangle","label":1,"x":0.1,"y":0.2,"width":0.6,"height":0.5',
        ),
        (
            {
                "type": "ellipse", "label": 1, "instruction": "Retouch this region.",
                "x": 0.1, "y": 0.2, "width": 0.6, "height": 0.5,
            },
            'Label 1 (ellipse): edit instruction="Retouch this region."',
            '"type":"ellipse","label":1,"x":0.1,"y":0.2,"width":0.6,"height":0.5',
        ),
        (
            {
                "type": "brush", "label": 1, "instruction": "Remove this stroke.",
                "points": [{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
            },
            'Label 1 (brush): edit instruction="Remove this stroke."',
            '"type":"brush","label":1,"points":[{"x":0.1,"y":0.2},{"x":0.7,"y":0.8}]',
        ),
        (
            {
                "type": "text", "label": 1, "text": "NEW SIGN",
                "instruction": "Use this wording.", "x": 0.25, "y": 0.18,
            },
            'Label 1 (text): output text="NEW SIGN"; additional edit instruction="Use this wording."',
            '"type":"text","label":1,"x":0.25,"y":0.18',
        ),
    ],
)
def test_precision_v3_provider_prompt_consumes_only_canonical_semantic_fields(
    monkeypatch,
    annotation,
    expected_instruction,
    expected_geometry,
):
    calls = []
    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(kwargs)
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "Keep every unmarked area unchanged.",
            "openai",
            **_v3_kwargs(annotations=[annotation]),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    prompt = calls[0]["data"]["prompt"]
    assert expected_instruction in prompt
    assert expected_geometry in prompt
    assert '"color"' not in prompt
    assert '"stroke_width"' not in prompt
    assert '"font_size"' not in prompt


@pytest.mark.parametrize(
    ("annotation", "presentation_fields"),
    [
        (
            {
                "type": "arrow", "label": 1, "instruction": "Move the marker.",
                "x1": 0.1, "y1": 0.2, "x2": 0.7, "y2": 0.8,
            },
            {"color": "#ef4444", "stroke_width": 5},
        ),
        (
            {
                "type": "rectangle", "label": 1, "instruction": "Replace this region.",
                "x": 0.1, "y": 0.2, "width": 0.6, "height": 0.5,
            },
            {"color": "#ef4444", "stroke_width": 5},
        ),
        (
            {
                "type": "ellipse", "label": 1, "instruction": "Retouch this region.",
                "x": 0.1, "y": 0.2, "width": 0.6, "height": 0.5,
            },
            {"color": "#ef4444", "stroke_width": 5},
        ),
        (
            {
                "type": "brush", "label": 1, "instruction": "Remove this stroke.",
                "points": [{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
            },
            {"color": "#ef4444", "stroke_width": 5},
        ),
        (
            {
                "type": "text", "label": 1, "text": "NEW SIGN",
                "instruction": "Use this wording.", "x": 0.25, "y": 0.18,
            },
            {"color": "#ef4444", "stroke_width": 5, "font_size": 24},
        ),
    ],
)
def test_precision_v3_provider_rejects_presentation_fields_before_http(
    monkeypatch,
    annotation,
    presentation_fields,
):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("presentation fields must be rejected before provider HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    styled_annotation = dict(annotation)
    styled_annotation.update(presentation_fields)
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "Keep every unmarked area unchanged.",
            "openai",
            **_v3_kwargs(annotations=[styled_annotation]),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_annotations_invalid"
    assert "precision_annotations_invalid" in result.error
    assert client_constructions == []


def test_precision_dispatch_defensively_rejects_invalid_v3_geometry_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("invalid v3 geometry must be rejected before HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    invalid_annotations = [
        {
            "type": "ellipse", "label": 1, "instruction": "Edit.",
            "x": 0.8, "y": 0.1, "width": 0.3, "height": 0.2,
        },
        {
            "type": "brush", "label": 1, "instruction": "Edit.",
            "points": [{"x": 0.1, "y": 0.1}, {"x": 0.1, "y": 0.1}],
        },
        {
            "type": "brush", "label": 1, "instruction": "Edit.",
            "points": [{"x": 0.1, "y": 0.1}, {"x": 1.1, "y": 0.2}],
        },
    ]

    for annotations in invalid_annotations:
        result = asyncio.run(
            providers._dispatch_generate(
                _provider(), "strict edit", "openai", **_v3_kwargs(annotations=[annotations])
            )
        )
        assert result.success is False
        assert "precision_annotations_invalid" in result.error

    assert client_constructions == []


def test_precision_dispatch_defensively_rejects_v3_brush_without_instruction(monkeypatch):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )
    brush = {
        "type": "brush",
        "label": 1,
        "instruction": "",
        "points": [{"x": 0.1, "y": 0.1}, {"x": 0.2, "y": 0.2}],
    }
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(), "strict edit", "openai", **_v3_kwargs(annotations=[brush])
        )
    )
    assert result.success is False
    assert "precision_annotations_invalid" in result.error
    assert client_constructions == []


def test_precision_dispatch_sends_target_only_for_explicit_resize(monkeypatch):
    calls = []
    output = BytesIO()
    Image.new("RGB", (1792, 768), (32, 96, 160)).save(output, format="PNG")
    response_image = base64.b64encode(output.getvalue()).decode("ascii")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(kwargs)
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["1792x768"]),
            "strict edit",
            "openai",
            **_v2_kwargs(
                precision_size_mode="resize",
                precision_target_size="1792x768",
                precision_resize_prompt="Extend the background sideways.",
            ),
        )
    )

    assert result.success is True
    assert calls[0]["data"]["size"] == "1792x768"
    assert "Target canvas constraint: output exactly 1792x768 (21:9)." in calls[0]["data"]["prompt"]
    assert "Extend the background sideways." in calls[0]["data"]["prompt"]


def test_precision_dispatch_rejects_resize_without_guidance_before_http(monkeypatch):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["1792x768"]),
            "strict edit",
            "openai",
            **_v2_kwargs(
                precision_size_mode="resize",
                precision_target_size="1792x768",
                precision_resize_prompt="",
            ),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_resize_prompt_required"
    assert client_constructions == []


def test_precision_dispatch_adds_strategy_leg_protection_and_local_selection_guidance(monkeypatch):
    calls = []
    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(kwargs)
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["64x64"]),
            "Repair the lower body.",
            "openai",
            **_v3_kwargs(
                precision_strategy="fine",
                precision_selection_mode="local",
                precision_selection_feather=14,
            ),
        )
    )

    assert result.success is True
    prompt = calls[0]["data"]["prompt"]
    assert "careful, high-fidelity edit pass" in prompt
    assert "model guidance, not a verified pixel inpaint mask" in prompt
    assert "approximately 14px soft transition" in prompt
    assert "complete, continuous, anatomically separate legs" in prompt
    assert "omit, merge, duplicate, shorten" in prompt


def test_precision_dispatch_rejects_invalid_strategy_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("invalid precision strategy must not open HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(precision_strategy="deep"),
        )
    )

    assert result.success is False
    assert "precision_strategy_invalid" in result.error
    assert client_constructions == []


def test_precision_dispatch_rejects_local_selection_without_region_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("invalid local selection must not open HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(
                precision_selection_mode="local",
                precision_selection_feather=8,
            ),
        )
    )

    assert result.success is False
    assert "precision_local_selection_required" in result.error
    assert client_constructions == []


@pytest.mark.parametrize("field", ["annotation_data", "annotation_objects"])
def test_precision_resize_only_rejects_browser_local_annotation_state_before_http(monkeypatch, field):
    client_constructions = []
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: client_constructions.append(kwargs),
    )

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["64x64"]),
            "expand the canvas",
            "openai",
            **_resize_only_kwargs(**{field: {} if field == "annotation_data" else []}),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_resize_annotation_fields_conflict"
    assert client_constructions == []


@pytest.mark.parametrize(
    ("supported_sizes", "target_size", "expected_code"),
    [
        (None, "1792x768", "precision_edit_size_capability_unknown"),
        (["1024x1024"], "1792x768", "precision_edit_target_size_not_declared"),
        (["invalid", "0x768", "9000x9000"], "1792x768", "precision_edit_size_capability_unknown"),
        (
            ["1792X768", " 1792x768", "1792x768 ", "01792x768", "1e3x768", "1024.5x768", "1792-768"],
            "1792x768",
            "precision_edit_size_capability_unknown",
        ),
        (["1792x768"], "1792X768", "precision_target_size_invalid"),
        (["1792x768"], "01792x768", "precision_target_size_invalid"),
    ],
)
def test_precision_dispatch_rejects_unknown_or_undeclared_resize_before_http(monkeypatch, supported_sizes, target_size, expected_code):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("unsupported precision resize must not open HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=supported_sizes),
            "strict edit",
            "openai",
            **_v2_kwargs(
                precision_size_mode="resize",
                precision_target_size=target_size,
                precision_resize_prompt="Extend the background sideways.",
            ),
        )
    )

    assert result.success is False
    assert expected_code in result.error
    assert client_constructions == []


@pytest.mark.parametrize(
    "image_url",
    [
        "http://images.example.test/result.png",
        "https://user:secret@images.example.test/result.png",
        "https://127.0.0.1/result.png",
        "https://10.0.0.1/result.png",
        "https://100.64.0.1/result.png",
        "https://100.100.100.200/latest/meta-data",
        "https://168.63.129.16/machine",
        "https://169.254.169.254/latest/meta-data",
        "https://192.0.2.1/result.png",
        "https://240.0.0.1/result.png",
        "https://[::1]/result.png",
        "https://[fd00:ec2::254]/latest/meta-data",
        "https://metadata.google.internal/computeMetadata/v1/",
        "https://images.example.test:22/result.png",
    ],
)
def test_generated_image_url_rejects_ssrf_targets_before_http(image_url):
    stream_calls = []

    class Client:
        def stream(self, *args, **kwargs):
            stream_calls.append((args, kwargs))
            raise AssertionError("unsafe image URL must not open HTTP")

    data, error = asyncio.run(providers._download_generated_image(Client(), image_url))

    assert data is None
    assert error
    assert stream_calls == []


def test_generated_image_redirect_is_revalidated_before_next_hop(monkeypatch):
    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda host, port, type=0: [(providers.socket.AF_INET, type, 6, "", ("93.184.216.34", port))],
    )
    stream_calls = []

    class DownloadClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, method, url, **kwargs):
            stream_calls.append(url)
            return _StreamResponse(302, {"location": "https://169.254.169.254/latest/meta-data"})

    monkeypatch.setattr(providers, "_generated_image_http_client", DownloadClient)

    data, error = asyncio.run(
        providers._download_generated_image(object(), "https://images.example.test/result.png")
    )

    assert data is None
    assert "link-local" in error
    assert stream_calls == ["https://93.184.216.34/result.png"]


@pytest.mark.parametrize(
    ("headers", "chunks", "expected"),
    [
        ({"content-type": "text/html"}, [b"not an image"], "Content-Type"),
        ({"content-type": "image/png", "content-length": str(providers.GENERATED_IMAGE_MAX_BYTES + 1)}, [], "too large"),
        ({"content-type": "image/png"}, [b"x" * (providers.GENERATED_IMAGE_MAX_BYTES + 1)], "too large"),
    ],
)
def test_generated_image_download_enforces_type_and_size(monkeypatch, headers, chunks, expected):
    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda host, port, type=0: [(providers.socket.AF_INET, type, 6, "", ("93.184.216.34", port))],
    )

    class DownloadClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, method, url, **kwargs):
            return _StreamResponse(200, headers, chunks)

    monkeypatch.setattr(providers, "_generated_image_http_client", DownloadClient)

    data, error = asyncio.run(
        providers._download_generated_image(object(), "https://images.example.test/result.png")
    )

    assert data is None
    assert expected in error


def test_generated_image_dns_result_is_pinned_against_rebinding(monkeypatch):
    resolutions = []

    def rebinding_getaddrinfo(host, port, type=0):
        resolutions.append(host)
        address = "93.184.216.34" if len(resolutions) == 1 else "169.254.169.254"
        return [(providers.socket.AF_INET, type, 6, "", (address, port))]

    monkeypatch.setattr(providers.socket, "getaddrinfo", rebinding_getaddrinfo)
    requests = []

    class DownloadClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, method, url, **kwargs):
            requests.append((url, kwargs))
            return _StreamResponse(200, {"content-type": "image/png"}, [b"image"])

    monkeypatch.setattr(providers, "_generated_image_http_client", DownloadClient)

    data, error = asyncio.run(
        providers._download_generated_image(object(), "https://images.example.test/result.png")
    )

    assert data == b"image"
    assert error is None
    assert resolutions == ["images.example.test"]
    assert requests == [(
        "https://93.184.216.34/result.png",
        {
            "headers": {"Host": "images.example.test"},
            "extensions": {"sni_hostname": "images.example.test"},
            "follow_redirects": False,
        },
    )]


def test_generated_image_download_disables_proxy_resolution(monkeypatch):
    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda host, port, type=0: [(providers.socket.AF_INET, type, 6, "", ("93.184.216.34", port))],
    )
    client_kwargs = []

    class DownloadClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, method, url, **kwargs):
            return _StreamResponse(200, {"content-type": "image/png"}, [b"image"])

    def async_client(**kwargs):
        client_kwargs.append(kwargs)
        return DownloadClient()

    monkeypatch.setattr(providers.httpx, "AsyncClient", async_client)

    data, error = asyncio.run(
        providers._download_generated_image(object(), "https://images.example.test/result.png")
    )

    assert data == b"image"
    assert error is None
    assert client_kwargs == [
        {"timeout": 180.0, "proxy": None, "trust_env": False, "verify": True}
    ]


def test_precision_response_prefers_b64_over_unsafe_url(monkeypatch):
    response_image = _data_url().split(",", 1)[1]
    stream_calls = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return _Response(
                200,
                {"data": [{"b64_json": response_image, "url": "https://127.0.0.1/ignored.png"}]},
            )

        def stream(self, *args, **kwargs):
            stream_calls.append((args, kwargs))
            if args[0] != "POST":
                raise AssertionError("b64_json must prevent URL download")
            payload = json.dumps(
                {
                    "data": [
                        {
                            "b64_json": response_image,
                            "url": "https://127.0.0.1/ignored.png",
                        }
                    ]
                }
            ).encode("utf-8")
            return _StreamResponse(200, {"content-length": str(len(payload))}, [payload])

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")

    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **_v2_kwargs())
    )

    assert result.success is True
    assert len(stream_calls) == 1
    assert stream_calls[0][0][0] == "POST"


def test_precision_dispatch_rejects_wrong_preserve_output_size(monkeypatch):
    output = BytesIO()
    Image.new("RGB", (10, 10), (32, 96, 160)).save(output, format="PNG")
    response_image = base64.b64encode(output.getvalue()).decode("ascii")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **_v2_kwargs())
    )
    assert result.success is False
    assert "precision_edit_output_size_mismatch" in result.error


def test_precision_preserve_rejects_recent_2048x864_upstream_result_with_recovery_facts(monkeypatch):
    """The 2026-09-07 failure remains a post-transport strict-size rejection."""
    calls = []
    response_image = _data_url(size=(12, 8)).split(",", 1)[1]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    # Keep the fixture small while reproducing the exact dimensions from the
    # latest laboratory failure: source 1792x768, upstream result 2048x864.
    monkeypatch.setattr(providers, "_image_dimensions", lambda _data: (1792, 768))
    monkeypatch.setattr(
        providers,
        "_inspect_precision_output",
        lambda _data: ((2048, 864), "PNG", False),
    )
    saved_images = []
    monkeypatch.setattr(
        providers,
        "_save_image",
        lambda *args, **kwargs: saved_images.append(args) or "unexpected.png",
    )
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_edit_output_size_mismatch"
    assert result.error_details == {
        "requested_size": "1792x768",
        "actual_size": "2048x864",
        "aspect_ratio_delta": pytest.approx(0.01587302),
        "allowed_policies": ["strict"],
    }
    assert len(calls) == 1, "the failure must be classified after an upstream response"
    assert saved_images == [], "strict mismatch must not replace the editable base"


def test_precision_resize_strict_rejects_1376x768_for_1536x864_without_retry(monkeypatch):
    calls = []
    saved_images = []
    response_image = base64.b64encode(
        _image_bytes(size=(1376, 768))
    ).decode("ascii")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(
        providers,
        "_save_image",
        lambda *args, **kwargs: saved_images.append((args, kwargs)) or "unexpected.png",
    )
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["1536x864"]),
            "strict resize",
            "openai",
            **_resize_only_kwargs(
                precision_target_size="1536x864",
                precision_output_size_policy="strict",
            ),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_edit_output_size_mismatch"
    assert "主动使用改变尺寸" not in result.error
    assert "可更换目标尺寸再次请求" in result.error
    assert "已由该上游严格验证" not in result.error
    assert result.error_details == {
        "requested_size": "1536x864",
        "actual_size": "1376x768",
        "aspect_ratio_delta": pytest.approx(0.0078125),
        "allowed_policies": ["strict", "fit_crop"],
    }
    assert len(calls) == 1
    assert saved_images == []


def test_precision_resize_fit_crop_converts_once_preserves_alpha_and_records_metadata(monkeypatch):
    calls = []
    saved = {}
    response_image = base64.b64encode(
        _image_bytes(mode="RGBA", size=(1376, 768))
    ).decode("ascii")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    def save_image(data, *args, **kwargs):
        saved["data"] = data
        saved["metadata"] = kwargs["generation_metadata"]
        return "gallery/result.png"

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", save_image)
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["1536x864"]),
            "fit resize",
            "openai",
            **_resize_only_kwargs(
                precision_target_size="1536x864",
                precision_output_size_policy="fit_crop",
            ),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    with Image.open(BytesIO(saved["data"])) as image:
        assert image.format == "PNG"
        assert image.size == (1536, 864)
        assert image.mode == "RGBA"
        assert image.getchannel("A").getextrema() == (128, 128)
    assert result.metadata == saved["metadata"]
    assert result.metadata["requested_size"] == "1536x864"
    assert result.metadata["provider_actual_size"] == "1376x768"
    assert result.metadata["final_size"] == "1536x864"
    assert result.metadata["policy"] == "fit_crop"
    assert result.metadata["aspect_ratio_delta"] == pytest.approx(0.0078125)
    assert result.metadata["transform"]["operation"] == "center_cover_crop"
    assert result.metadata["transform"]["scale_factor"] == pytest.approx(1.125)
    assert result.metadata["transform"]["resample"] == "LANCZOS"
    assert result.metadata["transform"]["alpha_preserved"] is True
    assert result.warnings == [{
        "code": "precision_edit_output_fit_crop_applied",
        "message": "Provider output 1376x768 was locally fit-cropped to requested size 1536x864.",
    }]


@pytest.mark.parametrize(
    ("actual_size", "expected_delta"),
    [
        ((1024, 768), 0.25),
        ((960, 540), 0.0),
    ],
)
def test_precision_resize_fit_crop_rejects_unsafe_transform(monkeypatch, actual_size, expected_delta):
    calls = []
    response_image = base64.b64encode(_image_bytes(size=actual_size)).decode("ascii")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=["1536x864"]),
            "fit resize",
            "openai",
            **_resize_only_kwargs(
                precision_target_size="1536x864",
                precision_output_size_policy="fit_crop",
            ),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_edit_output_size_mismatch"
    assert result.error_details["requested_size"] == "1536x864"
    assert result.error_details["actual_size"] == f"{actual_size[0]}x{actual_size[1]}"
    assert result.error_details["aspect_ratio_delta"] == pytest.approx(expected_delta)
    assert result.error_details["allowed_policies"] == ["strict", "fit_crop"]
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("target_size", "ratio_label", "policy"),
    [
        ("1792x768", "21:9", "strict"),
        ("1536x864", "16:9", "fit_crop"),
    ],
)
def test_precision_resize_prompt_appends_exact_canvas_constraint_once(
    monkeypatch,
    target_size,
    ratio_label,
    policy,
):
    calls = []
    width, height = (int(value) for value in target_size.split("x", 1))
    response_image = base64.b64encode(_image_bytes(size=(width, height))).decode("ascii")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(kwargs)
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(supported_sizes=[target_size]),
            "Keep the user instruction intact.",
            "openai",
            **_resize_only_kwargs(
                precision_target_size=target_size,
                precision_output_size_policy=policy,
            ),
        )
    )

    assert result.success is True
    prompt = calls[0]["data"]["prompt"]
    assert prompt.count("Target canvas constraint:") == 1
    assert f"exactly {target_size} ({ratio_label})" in prompt
    assert "Expand/outpaint the canvas" in prompt
    assert "preserve the existing subject, visual identity, and style" in prompt
    assert "Keep the user instruction intact." in prompt


def test_precision_preserve_prompt_does_not_append_resize_canvas_constraint(monkeypatch):
    calls = []
    response_image = _data_url().split(",", 1)[1]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(kwargs)
            return _Response(200, {"data": [{"b64_json": response_image}]})

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_save_image", lambda *args, **kwargs: "gallery/result.png")
    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **_v2_kwargs())
    )

    assert result.success is True
    assert "Target canvas constraint:" not in calls[0]["data"]["prompt"]


def test_precision_dispatch_rejects_v2_arrow_without_instruction_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("precision edit must not open HTTP without annotation instructions")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    kwargs = _v2_kwargs()
    kwargs["annotations"] = [
        {
            "type": "arrow",
            "label": 1,
            "x1": 0.10,
            "y1": 0.20,
            "x2": 0.60,
            "y2": 0.70,
        }
    ]

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **kwargs,
        )
    )

    assert result.success is False
    assert "precision_annotations_invalid" in result.error
    assert client_constructions == []


def test_precision_dispatch_4xx_never_falls_back(monkeypatch):
    calls = []
    fallback_calls = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(url)
            return _Response(422, text="unsupported edit request")

    async def forbidden_fallback(*args, **kwargs):
        fallback_calls.append((args, kwargs))
        raise AssertionError("precision edit must not fall back to I2I or T2I")

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_gen_openai_i2i_fallback", forbidden_fallback)
    monkeypatch.setattr(providers, "_gen_openai", forbidden_fallback)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert "precision_edit_upstream_error" in result.error
    assert calls == ["https://provider.example.test/v1/images/edits"]
    assert fallback_calls == []


def test_precision_dispatch_redacts_upstream_error_detail(monkeypatch):
    secrets = (
        "syntheticJsonKey123",
        "syntheticBearer456",
        "synthetic-user",
        "synthetic-pass",
        "syntheticQuery789",
        "test-key",
    )

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return _Response(
                503,
                text=(
                    '{"code":"provider_unavailable","api_key":"syntheticJsonKey123",'
                    '"authorization":"Bearer syntheticBearer456",'
                    '"url":"https://synthetic-user:synthetic-pass@example.test/fail'
                    '?access_token=syntheticQuery789","echo":"test-key"}'
                ),
            )

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert "precision_edit_upstream_error" in result.error
    assert "provider_unavailable" in result.error
    assert "[REDACTED]" in result.error
    for secret in secrets:
        assert secret not in result.error


def test_precision_upstream_error_exposes_only_structured_transport_facts(monkeypatch):
    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return _Response(503, text="temporary unavailable")

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_edit_upstream_error"
    assert result.error_details == {
        "model": "mock-edit-1",
        "profile": "/images/edits",
        "status_code": 503,
    }


def test_precision_read_error_closes_client_and_reports_non_replay_facts(monkeypatch):
    calls = []
    closed = []

    class Client:
        async def post(self, url, **_kwargs):
            calls.append(url)
            raise providers.httpx.ReadError(
                "synthetic upstream closed response",
                request=providers.httpx.Request("POST", url),
            )

        async def aclose(self):
            closed.append(True)

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **_kwargs: Client())
    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert result.error_code == "precision_edit_connection_error"
    assert calls == ["https://provider.example.test/v1/images/edits"]
    assert closed == [True]
    assert result.error_details == {
        "model": "mock-edit-1",
        "profile": "/images/edits",
        "transport_stage": "response_read",
        "transport_error": "ReadError",
        "automatic_retry": "suppressed_non_idempotent_image_edit",
    }


def test_precision_redacts_full_configured_key_before_error_excerpt(monkeypatch):
    provider = _provider()
    opaque_key = "syntheticOpaqueConfiguredKey" + "Q" * 96
    provider.api_key = opaque_key
    body = (
        '{"code":"provider_unavailable","diagnostic":"'
        + "x" * 145
        + opaque_key
        + ' remains unavailable"}'
    )

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return _Response(503, text=body)

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())

    result = asyncio.run(
        providers._dispatch_generate(provider, "strict edit", "openai", **_v2_kwargs())
    )

    assert result.success is False
    assert "precision_edit_upstream_error" in result.error
    assert "HTTP 503" in result.error
    assert "provider_unavailable" in result.error
    assert "[REDACTED]" in result.error
    assert opaque_key not in result.error
    assert opaque_key[:24] not in result.error


def test_precision_legacy_exception_redacts_gemini_query_key(monkeypatch):
    provider = _provider(endpoint_type="gemini")
    opaque_key = "OpaqueGeminiPrecisionKey"
    provider.api_key = opaque_key

    async def fail_dispatch(*args, **kwargs):
        raise RuntimeError(
            "upstream GET https://generativelanguage.example/v1beta/models/"
            f"mock:generateContent?key={opaque_key}&alt=json"
        )

    monkeypatch.setattr(providers, "_dispatch_generate", fail_dispatch)

    result = asyncio.run(
        providers.generate_for_provider(
            provider,
            "strict edit",
            protocol="gemini",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert opaque_key not in result.error
    assert "key=[REDACTED]" in result.error


def test_precision_multi_endpoint_failure_keeps_each_status_and_bounds_summaries(monkeypatch):
    """Endpoint retries must report actionable, bounded evidence without leaking keys."""
    provider = _provider()
    provider.endpoints = [
        EndpointConfig(
            name=f"edit-endpoint-{index}",
            url=f"https://endpoint-{index}.example.test/v1",
            key=f"test-key-{index}",
        )
        for index in range(1, 9)
    ]
    calls = []

    async def fail_each_endpoint(cfg, prompt, url, key, protocol, **kwargs):
        calls.append((url, key, protocol, kwargs["mode"]))
        status = 503 if url.endswith("1.example.test/v1") else 429
        return providers.ImageResult(
            success=False,
            error=f"[{cfg.name}] precision_edit_upstream_error: HTTP {status}: " + "x" * 1200,
            model=cfg.id,
        )

    monkeypatch.setattr(providers, "_try_generate_with_endpoint", fail_each_endpoint)

    result = asyncio.run(
        providers.generate_for_provider(
            provider,
            "strict edit",
            protocol="openai",
            **_v2_kwargs(),
        )
    )

    assert result.success is False
    assert len(calls) == 8
    for index in range(1, 9):
        assert f"edit-endpoint-{index}" in result.error
        assert f"test-key-{index}" not in result.error
    assert "HTTP 503" in result.error
    assert "HTTP 429" in result.error
    assert "x" * 500 not in result.error
    assert len(result.error) <= 2400


@pytest.mark.parametrize("payload", [{"data": []}, {"data": [None]}, {"data": ["not-an-image-object"]}])
def test_precision_dispatch_maps_empty_or_non_object_success_data_to_invalid_response(monkeypatch, payload):
    """HTTP 200 with malformed image data must fail closed instead of indexing ``data[0]``."""
    calls = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(url)
            return _Response(200, payload)

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())

    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **_v2_kwargs())
    )

    assert result.success is False
    assert "precision_edit_invalid_response" in result.error
    assert "IndexError" not in result.error
    assert calls == ["https://provider.example.test/v1/images/edits"]
