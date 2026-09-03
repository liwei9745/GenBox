"""Provider-only contract tests for strict mask-based inpainting."""

from __future__ import annotations

import asyncio
import base64
from io import BytesIO

import pytest
from PIL import Image

import providers
from config import ProviderConfig


def _data_url(image: Image.Image, image_format: str = "PNG") -> str:
    output = BytesIO()
    image.save(output, format=image_format)
    mime = "image/png" if image_format == "PNG" else "image/jpeg"
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _base_image() -> str:
    return _data_url(Image.new("RGB", (2, 1), (200, 20, 20)))


def _white_edit_mask() -> str:
    mask = Image.new("L", (2, 1))
    mask.putdata([0, 255])
    return _data_url(mask)


def _provider(endpoint_type: str = "openai") -> ProviderConfig:
    return ProviderConfig(
        id="openai-inpaint",
        name="OpenAI Inpaint",
        type="image",
        api_key="test-key",
        base_url="https://provider.example.test/v1",
        model="gpt-image-test",
        size="2x1",
        quality="high",
        endpoint_type=endpoint_type,
    )


def _inpaint_kwargs() -> dict:
    image_data = _base_image()
    return {
        "mode": "inpaint",
        "image_data": image_data,
        "image_data_list": [image_data],
        "mask_data": _white_edit_mask(),
        "mask_contract": providers.INPAINT_MASK_CONTRACT,
        "inpaint_authorized": True,
        "size": "2x1",
        "quality": "high",
    }


class _Response:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_openai_inpaint_sends_exact_image_mask_multipart(monkeypatch):
    calls = []
    response_image = base64.b64encode(b"generated-image").decode("ascii")

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
            "replace the white-selected area",
            "openai",
            **_inpaint_kwargs(),
        )
    )

    assert result.success is True
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "https://provider.example.test/v1/images/edits"
    assert request["headers"] == {"Authorization": "Bearer test-key"}
    assert request["data"] == {
        "model": "gpt-image-test",
        "prompt": "replace the white-selected area",
        "n": 1,
        "size": "2x1",
        "quality": "high",
    }

    files = request["files"]
    assert [name for name, _ in files] == ["image", "mask"]
    assert all(name != "prompt" for name, _ in files)
    assert files[0][1][0] == "image.png"
    assert files[0][1][2] == "image/png"
    assert files[1][1][0] == "mask.png"
    assert files[1][1][2] == "image/png"

    with Image.open(BytesIO(files[1][1][1])) as provider_mask:
        assert provider_mask.mode == "RGBA"
        assert list(provider_mask.getchannel("A").tobytes()) == [255, 0]


@pytest.mark.parametrize("status_code", [404, 422])
def test_openai_inpaint_4xx_never_falls_back(monkeypatch, status_code):
    calls = []
    fallback_calls = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(url)
            return _Response(status_code, text="unsupported mask request")

    async def forbidden_fallback(*args, **kwargs):
        fallback_calls.append((args, kwargs))
        raise AssertionError("inpaint must not fall back to I2I or T2I")

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(providers, "_gen_openai_i2i_fallback", forbidden_fallback)
    monkeypatch.setattr(providers, "_gen_openai", forbidden_fallback)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "strict edit",
            "openai",
            **_inpaint_kwargs(),
        )
    )

    assert result.success is False
    assert "inpaint_upstream_error" in result.error
    assert f"HTTP {status_code}" in result.error
    assert calls == ["https://provider.example.test/v1/images/edits"]
    assert fallback_calls == []


def test_inpaint_redacts_full_configured_key_before_error_excerpt(monkeypatch):
    provider = _provider()
    opaque_key = "syntheticOpaqueConfiguredKey" + "R" * 96
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
        providers._dispatch_generate(
            provider,
            "strict edit",
            "openai",
            **_inpaint_kwargs(),
        )
    )

    assert result.success is False
    assert "inpaint_upstream_error" in result.error
    assert "HTTP 503" in result.error
    assert "provider_unavailable" in result.error
    assert "[REDACTED]" in result.error
    assert opaque_key not in result.error
    assert opaque_key[:24] not in result.error


def test_inpaint_legacy_exception_redacts_gemini_query_key(monkeypatch):
    provider = _provider(endpoint_type="gemini")
    opaque_key = "OpaqueGeminiInpaintKey"
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
            **_inpaint_kwargs(),
        )
    )

    assert result.success is False
    assert opaque_key not in result.error
    assert "key=[REDACTED]" in result.error


@pytest.mark.parametrize(
    ("endpoint_type", "protocol"),
    [
        ("auto", "openai"),
        ("openai", "auto"),
        ("gemini", "gemini"),
        ("agnes", "agnes"),
        ("qwen", "qwen"),
    ],
)
def test_unverified_inpaint_protocols_fail_before_http(
    monkeypatch, endpoint_type, protocol
):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("unsupported inpaint protocol must not create an HTTP client")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(endpoint_type),
            "strict edit",
            protocol,
            **_inpaint_kwargs(),
        )
    )

    assert result.success is False
    assert "mask_protocol_unverified" in result.error
    assert client_constructions == []


def test_openai_inpaint_requires_upper_layer_capability_authorization(monkeypatch):
    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("HTTP must not start")),
    )
    kwargs = _inpaint_kwargs()
    kwargs["inpaint_authorized"] = False

    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **kwargs)
    )

    assert result.success is False
    assert "inpaint_capability_not_authorized" in result.error


def test_openai_inpaint_rejects_multiple_base_images_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("inpaint must not create HTTP for multiple base images")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    kwargs = _inpaint_kwargs()
    kwargs["image_data_list"] = [kwargs["image_data"], _base_image()]

    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **kwargs)
    )

    assert result.success is False
    assert "inpaint_single_image_required" in result.error
    assert client_constructions == []


def test_unknown_inpaint_mask_contract_fails_closed_before_http(monkeypatch):
    client_constructions = []

    def forbidden_client(**kwargs):
        client_constructions.append(kwargs)
        raise AssertionError("unknown inpaint capability must not create HTTP")

    monkeypatch.setattr(providers.httpx, "AsyncClient", forbidden_client)
    kwargs = _inpaint_kwargs()
    kwargs["mask_contract"] = "unknown-mask-v1"

    result = asyncio.run(
        providers._dispatch_generate(_provider(), "strict edit", "openai", **kwargs)
    )

    assert result.success is False
    assert "mask_contract_unsupported" in result.error
    assert client_constructions == []


def test_existing_multi_image_i2i_dispatch_is_preserved(monkeypatch):
    captured = {}
    images = ["data:image/png;base64,b25l", "data:image/png;base64,dHdv"]

    async def fake_edit(
        cfg, prompt, image_data, strength, image_data_list=None, **kwargs
    ):
        captured.update(
            image_data=image_data,
            image_data_list=image_data_list,
            strength=strength,
        )
        return providers.ImageResult(success=True, model=cfg.id)

    monkeypatch.setattr(providers, "_gen_openai_edit", fake_edit)

    result = asyncio.run(
        providers._dispatch_generate(
            _provider(),
            "use both references",
            "openai",
            mode="i2i",
            image_data=images[0],
            image_data_list=images,
            strength=0.7,
        )
    )

    assert result.success is True
    assert captured == {
        "image_data": images[0],
        "image_data_list": images,
        "strength": 0.7,
    }


def test_explicit_protocol_kwarg_is_not_forwarded_twice(monkeypatch):
    captured = {}

    async def fake_endpoint(cfg, prompt, url, key, protocol, **kwargs):
        captured.update(protocol=protocol, kwargs=kwargs)
        return providers.ImageResult(success=True, model=cfg.id)

    monkeypatch.setattr(providers, "_try_generate_with_endpoint", fake_endpoint)

    result = asyncio.run(
        providers.generate_for_provider(
            _provider(),
            "explicit protocol",
            protocol="openai",
            mode="t2i",
        )
    )

    assert result.success is True
    assert captured == {"protocol": "openai", "kwargs": {"mode": "t2i"}}


def test_requested_wide_ratio_fails_closed_when_endpoint_returns_square():
    from PIL import Image
    from io import BytesIO

    image = BytesIO()
    Image.new("RGB", (1024, 1024), "white").save(image, format="PNG")
    error = providers._validate_generated_size(image.getvalue(), "2560x1092", _provider())

    assert error is not None
    assert "比例未按请求生效" in error
    assert "2560×1092" in error
    assert "1024×1024" in error


def test_requested_ratio_accepts_matching_endpoint_dimensions():
    from PIL import Image
    from io import BytesIO

    image = BytesIO()
    Image.new("RGB", (2560, 1092), "white").save(image, format="PNG")

    assert providers._validate_generated_size(image.getvalue(), "2560x1092", _provider()) is None


def test_upstream_503_is_explained_in_plain_language():
    error = providers._friendly_generation_error(
        '[GPT Image 2] 503 Service Unavailable | Response: {"code":"provider_unavailable"}'
    )

    assert "上游生图服务暂时不可用（503）" in error
    assert "不是提示词或本机尺寸设置错误" in error
    assert "provider_unavailable" in error
