from __future__ import annotations

import asyncio
import base64
import json
import struct
import zlib
from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image
from pydantic import ValidationError

import main
import providers
from config import EndpointConfig, ProviderConfig


def _png_bytes(size: tuple[int, int] = (2, 2)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, (12, 34, 56)).save(output, format="PNG")
    return output.getvalue()


def _jpeg_bytes(size: tuple[int, int] = (2, 2)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, (12, 34, 56)).save(output, format="JPEG")
    return output.getvalue()


def _png_with_advertised_size(width: int, height: int) -> bytes:
    payload = bytearray(_png_bytes((1, 1)))
    payload[16:24] = struct.pack(">II", width, height)
    payload[29:33] = struct.pack(">I", zlib.crc32(payload[12:29]) & 0xFFFFFFFF)
    return bytes(payload)


def _provider() -> ProviderConfig:
    return ProviderConfig(
        id="safe-provider",
        name="Safe Provider",
        type="image",
        api_key="synthetic-test-key",
        base_url="https://provider.example.test/v1",
        model="image-model",
        size="2x2",
        endpoint_type="openai",
    )


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _StreamResponse:
    def __init__(
        self,
        headers: dict[str, str],
        payload: bytes = b"",
        *,
        chunks: list[bytes] | None = None,
        status_code: int = 200,
    ):
        self.status_code = status_code
        self.headers = headers
        self._payload = payload
        self._chunks = chunks
        self.iterated = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def aiter_bytes(self):
        self.iterated = True
        for chunk in self._chunks or [self._payload]:
            yield chunk


class _DownloadClient:
    def __init__(self, headers: dict[str, str], payload: bytes):
        self._headers = headers
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, **kwargs):
        return _StreamResponse(self._headers, self._payload)


def test_inline_base64_byte_cap_is_checked_before_decode(monkeypatch):
    monkeypatch.setattr(providers, "GENERATED_IMAGE_MAX_BYTES", 3)
    monkeypatch.setattr(
        providers.base64,
        "b64decode",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not decode")),
    )

    with pytest.raises(providers.GeneratedImageValidationError) as raised:
        providers._decode_generated_image_base64("A" * 5)

    assert raised.value.code == "generated_image_bytes_exceeded"


def test_generic_pixel_cap_rejects_compressed_header_before_load(monkeypatch):
    payload = _png_with_advertised_size(6000, 5000)
    monkeypatch.setattr(
        Image.Image,
        "load",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not load pixels")),
    )

    with pytest.raises(providers.GeneratedImageValidationError) as raised:
        providers._inspect_generated_image(payload)

    assert raised.value.code == "generated_image_pixels_exceeded"
    assert raised.value.details["max_pixels"] == providers.GENERATED_IMAGE_MAX_PIXELS


def test_pillow_decompression_bomb_warning_is_promoted_to_rejection(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)

    with pytest.raises(providers.GeneratedImageValidationError) as raised:
        providers._inspect_generated_image(
            _png_with_advertised_size(15, 10),
            max_pixels=1000,
        )

    assert raised.value.code == "generated_image_decompression_bomb"


def test_decoded_format_must_match_declared_mime():
    with pytest.raises(providers.GeneratedImageValidationError) as raised:
        providers._inspect_generated_image(
            _png_bytes(),
            declared_mime="image/jpeg",
        )

    assert raised.value.code == "generated_image_mime_mismatch"
    assert raised.value.details == {
        "declared_mime": "image/jpeg",
        "actual_mime": "image/png",
    }


@pytest.mark.parametrize(
    ("content_type", "expect_success"),
    [("image/png", True), ("image/jpeg", False)],
)
def test_url_result_validates_decoded_format_against_content_type(
    monkeypatch,
    content_type,
    expect_success,
):
    payload = _png_bytes()
    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda host, port, type=0: [
            (providers.socket.AF_INET, type, 6, "", ("93.184.216.34", port))
        ],
    )
    monkeypatch.setattr(
        providers,
        "_generated_image_http_client",
        lambda: _DownloadClient({"content-type": content_type}, payload),
    )

    data, error = asyncio.run(
        providers._download_generated_image(
            object(),
            "https://images.example.test/result.png",
            max_pixels=providers.GENERATED_IMAGE_MAX_PIXELS,
        )
    )

    if expect_success:
        assert data == payload
        assert error is None
    else:
        assert data is None
        assert "generated_image_mime_mismatch" in error


def test_common_save_accepts_valid_image_and_transcodes_to_png(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "GALLERY_DIR", tmp_path)

    local_path = providers._save_image(
        _png_bytes(),
        "model",
        "valid",
        "synthetic prompt",
        declared_mime="image/png",
    )

    with Image.open(local_path) as saved:
        assert saved.format == "PNG"
        assert saved.size == (2, 2)
        assert saved.info["Prompt"] == "synthetic prompt"


def test_t2i_oversized_inline_result_returns_structured_error(monkeypatch):
    monkeypatch.setattr(providers, "GENERATED_IMAGE_MAX_BYTES", 3)

    async def fake_post(*args, **kwargs):
        return _Response({"data": [{"b64_json": "A" * 5}]}), object()

    monkeypatch.setattr(providers, "_http_post_with_retry", fake_post)

    result = asyncio.run(providers._gen_openai(_provider(), "synthetic prompt"))

    assert result.success is False
    assert result.error_code == "generated_image_bytes_exceeded"
    assert result.error_details == {
        "validation_code": "generated_image_bytes_exceeded",
        "max_bytes": 3,
    }
    assert "synthetic-test-key" not in result.error


class _VariationClient:
    def __init__(
        self,
        payload=None,
        *,
        status_code=200,
        text="",
        exception=None,
        headers=None,
        raw_body=None,
        chunks=None,
    ):
        self._payload = payload
        self._status_code = status_code
        self._text = text
        self._exception = exception
        self._headers = headers or {}
        self._raw_body = raw_body
        self._chunks = chunks
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def aclose(self):
        return None

    def _body(self):
        if self._raw_body is not None:
            return self._raw_body
        if self._status_code >= 400 and self._text:
            return self._text.encode("utf-8")
        return json.dumps(self._payload).encode("utf-8")

    def stream(self, method, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._exception is not None:
            raise self._exception
        return _StreamResponse(
            self._headers,
            self._body(),
            chunks=self._chunks,
            status_code=self._status_code,
        )

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._exception is not None:
            raise self._exception
        return type(
            "VariationResponse",
            (),
            {
                "status_code": self._status_code,
                "text": self._text,
                "json": lambda self: self.payload,
                "payload": self._payload,
            },
        )()


def _variation_provider() -> ProviderConfig:
    return ProviderConfig(
        id="variation-provider",
        name="Variation Provider",
        type="image",
        model="variation-model",
        endpoints=[
            EndpointConfig(
                url="https://provider.example.test/v1",
                key="synthetic-variation-key",
            )
        ],
    )


def _variation_request(
    image_data: str | None = None,
    *,
    n: int = 1,
) -> main.VariationRequest:
    source = base64.b64encode(_png_bytes()).decode("ascii")
    return main.VariationRequest(
        image_data=image_data or f"data:image/png;base64,{source}",
        provider_id="variation-provider",
        model="variation-model",
        size="1024x1024",
        n=n,
    )


@pytest.mark.parametrize(
    ("provider_output", "expected_validation_code"),
    [
        ("%%%", "generated_image_base64_invalid"),
        ("A" * 5, "generated_image_bytes_exceeded"),
    ],
)
def test_variation_provider_rejects_malformed_or_oversized_base64(
    monkeypatch,
    provider_output,
    expected_validation_code,
):
    import httpx

    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(providers, "GENERATED_IMAGE_MAX_BYTES", 3)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _VariationClient(
            {"data": [{"b64_json": provider_output}]}
        ),
    )
    monkeypatch.setattr(
        main,
        "_save_image",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("rejected provider output must not be saved")
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request()))

    assert raised.value.status_code == 502
    assert raised.value.detail == {
        "code": "image_variation_invalid_response",
        "message": "variation provider returned an invalid image",
        "validation_code": expected_validation_code,
    }
    assert provider_output not in str(raised.value.detail)
    assert "synthetic-variation-key" not in str(raised.value.detail)


def test_variation_provider_rejects_compressed_pixel_bomb_before_save(
    monkeypatch,
):
    import httpx

    provider_output = base64.b64encode(
        _png_with_advertised_size(6000, 5000)
    ).decode("ascii")
    request = _variation_request()
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _VariationClient(
            {"data": [{"b64_json": provider_output}]}
        ),
    )
    original_load = Image.Image.load

    def reject_pixel_bomb_load(image, *args, **kwargs):
        if image.width * image.height > providers.GENERATED_IMAGE_MAX_PIXELS:
            raise AssertionError("pixel bomb must be rejected before load")
        return original_load(image, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "load", reject_pixel_bomb_load)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(request))

    assert raised.value.status_code == 502
    assert raised.value.detail["validation_code"] == "generated_image_pixels_exceeded"


def test_variation_provider_preserves_valid_output_flow(monkeypatch):
    import httpx

    output = _png_bytes()
    encoded = base64.b64encode(output).decode("ascii")
    saved = []
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _VariationClient({"data": [{"b64_json": encoded}]}),
    )
    monkeypatch.setattr(
        main,
        "_save_image",
        lambda raw, provider_id, prompt_short, full_prompt: (
            saved.append((raw, provider_id, prompt_short, full_prompt))
            or "gallery/variation.png"
        ),
    )

    response = asyncio.run(main.image_variations(_variation_request()))

    assert response == {
        "success": True,
        "images": [
            {
                "b64_json": encoded,
                "local_path": "gallery/variation.png",
                "provider_id": "variation-provider",
            }
        ],
        "model": "variation-model",
        "provider_id": "variation-provider",
    }
    assert saved == [(output, "variation-provider", "variation", "")]


def test_shared_decoder_rejects_data_url_mime_mismatch():
    encoded = base64.b64encode(_png_bytes()).decode("ascii")

    with pytest.raises(providers.GeneratedImageValidationError) as raised:
        providers._decode_generated_image_base64(
            f"data:image/jpeg;base64,{encoded}"
        )

    assert raised.value.code == "generated_image_mime_mismatch"
    assert raised.value.details == {
        "declared_mime": "image/jpeg",
        "actual_mime": "image/png",
    }


def test_provider_generation_rejects_data_url_mime_mismatch(monkeypatch):
    encoded = base64.b64encode(_png_bytes()).decode("ascii")

    async def fake_post(*args, **kwargs):
        return _Response(
            {"data": [{"b64_json": f"data:image/jpeg;base64,{encoded}"}]}
        ), object()

    monkeypatch.setattr(providers, "_http_post_with_retry", fake_post)

    result = asyncio.run(providers._gen_openai(_provider(), "synthetic prompt"))

    assert result.success is False
    assert result.error_code == "generated_image_mime_mismatch"
    assert result.error_details["validation_code"] == "generated_image_mime_mismatch"


def test_variation_forwards_validated_source_bytes_with_real_mime(monkeypatch):
    import httpx

    monkeypatch.delenv("VERIFY_SSL", raising=False)
    source_bytes = _jpeg_bytes()
    source = "data:image/jpeg;base64," + base64.b64encode(source_bytes).decode("ascii")
    output = base64.b64encode(_png_bytes()).decode("ascii")
    client = _VariationClient({"data": [{"b64_json": output}]})
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    client_kwargs = []

    def client_factory(**kwargs):
        client_kwargs.append(kwargs)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(main, "_save_image", lambda *args, **kwargs: "gallery/variation.png")

    response = asyncio.run(main.image_variations(_variation_request(source)))

    assert response["success"] is True
    _, request = client.calls[0]
    assert request["files"] == {
        "image": ("image.jpg", source_bytes, "image/jpeg")
    }
    assert client_kwargs[0]["verify"] is True


@pytest.mark.parametrize(
    ("source_factory", "expected_code"),
    [
        (
            lambda: "data:image/jpeg;base64,"
            + base64.b64encode(_png_bytes()).decode("ascii"),
            "image_mime_mismatch",
        ),
        (
            lambda: "data:image/gif;base64,"
            + base64.b64encode(_png_bytes()).decode("ascii"),
            "unsupported_image_mime",
        ),
    ],
)
def test_variation_rejects_source_mime_attacks_before_http(
    monkeypatch,
    source_factory,
    expected_code,
):
    import httpx

    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("invalid source must not reach the provider")
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request(source_factory())))

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == expected_code


def test_variation_rejects_oversized_source_before_base64_decode(monkeypatch):
    monkeypatch.setattr(main, "MAX_GENERATION_INPUT_BYTES", 3)
    monkeypatch.setattr(
        main.base64,
        "b64decode",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not decode")),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request("A" * 5)))

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "image_too_large"


def test_variation_rejects_source_pixel_limit_before_http(monkeypatch):
    import httpx

    source = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode("ascii")
    monkeypatch.setattr(main, "MAX_GENERATION_INPUT_PIXELS", 3)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("invalid source must not reach the provider")
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request(source)))

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "image_pixels_exceeded"


def test_variation_rejects_source_decompression_bomb_before_http(monkeypatch):
    import httpx

    source = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode("ascii")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("invalid source must not reach the provider")
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request(source)))

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "image_decompression_bomb"


@pytest.mark.parametrize(
    ("provider_payload", "expected_validation_code"),
    [
        ([], "variation_response_not_object"),
        ({}, "variation_response_data_invalid"),
        ({"data": [None]}, "variation_response_item_invalid"),
        ({"data": [{}]}, "variation_response_image_missing"),
        ({"data": [{"b64_json": ""}]}, "variation_response_image_missing"),
    ],
)
def test_variation_rejects_invalid_provider_response_shape(
    monkeypatch,
    provider_payload,
    expected_validation_code,
):
    import httpx

    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _VariationClient(provider_payload),
    )
    monkeypatch.setattr(
        main,
        "_save_image",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("invalid response must not be saved")
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request()))

    assert raised.value.status_code == 502
    assert raised.value.detail == {
        "code": "image_variation_invalid_response",
        "message": "variation provider returned an invalid response",
        "validation_code": expected_validation_code,
    }


def test_variation_output_rejects_data_url_mime_mismatch(monkeypatch):
    import httpx

    encoded = base64.b64encode(_png_bytes()).decode("ascii")
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _VariationClient(
            {"data": [{"b64_json": f"data:image/jpeg;base64,{encoded}"}]}
        ),
    )
    monkeypatch.setattr(
        main,
        "_save_image",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("mismatched output must not be saved")
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request()))

    assert raised.value.status_code == 502
    assert raised.value.detail["validation_code"] == "generated_image_mime_mismatch"


@pytest.mark.parametrize("failure_mode", ["http", "exception"])
def test_variation_upstream_failures_are_structured_and_redacted(
    monkeypatch,
    failure_mode,
):
    import httpx

    endpoint_key = "synthetic-variation-key"
    user = "synthetic-user"
    password = "synthetic-pass"
    query_token = "synthetic-query-token"
    exception_token = "synthetic-exception-token"
    provider = _variation_provider()
    provider.endpoints[0].url = (
        f"https://{user}:{password}@provider.example.test/v1"
        f"?access_token={query_token}"
    )
    if failure_mode == "http":
        client = _VariationClient(
            status_code=503,
            text=(
                f"Authorization: Bearer {exception_token}; "
                f"key={endpoint_key}"
            ),
        )
    else:
        client = _VariationClient(
            exception=RuntimeError(
                f"GET https://{user}:{password}@provider.example.test/fail"
                f"?token={exception_token}; key={endpoint_key}"
            )
        )
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [provider])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request()))

    assert raised.value.status_code == 502
    assert raised.value.detail["code"] == "image_variation_upstream_error"
    evidence = str(raised.value.detail)
    assert "[REDACTED]" in evidence
    for secret in (
        endpoint_key,
        user,
        password,
        query_token,
        exception_token,
    ):
        assert secret not in evidence


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (None, True),
        ("", True),
        ("unexpected", True),
        ("true", True),
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
    ],
)
def test_verify_ssl_defaults_true_and_requires_explicit_opt_out(
    monkeypatch,
    configured,
    expected,
):
    if configured is None:
        monkeypatch.delenv("VERIFY_SSL", raising=False)
    else:
        monkeypatch.setenv("VERIFY_SSL", configured)

    assert main.verify_ssl_enabled() is expected


@pytest.mark.parametrize(("configured", "expected"), [(None, True), ("off", False)])
def test_common_provider_client_uses_shared_tls_setting(
    monkeypatch,
    configured,
    expected,
):
    if configured is None:
        monkeypatch.delenv("VERIFY_SSL", raising=False)
    else:
        monkeypatch.setenv("VERIFY_SSL", configured)
    encoded = base64.b64encode(_png_bytes()).decode("ascii")
    client = _VariationClient({"data": [{"b64_json": encoded}]})
    client_kwargs = []

    def client_factory(**kwargs):
        client_kwargs.append(kwargs)
        return client

    monkeypatch.setattr(providers.httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(
        providers,
        "_save_image",
        lambda *args, **kwargs: "gallery/provider.png",
    )

    result = asyncio.run(
        providers.generate_for_provider(_provider(), "synthetic prompt")
    )

    assert result.success is True
    assert client_kwargs[0]["verify"] is expected


def test_ip_pinned_image_download_never_disables_tls(monkeypatch):
    captured = []

    def client_factory(**kwargs):
        captured.append(kwargs)
        return object()

    monkeypatch.setenv("VERIFY_SSL", "off")
    monkeypatch.setattr(providers.httpx, "AsyncClient", client_factory)

    providers._generated_image_http_client()

    assert captured[0]["verify"] is True


def test_provider_content_length_over_limit_rejects_before_iteration():
    response = _StreamResponse({"content-length": "5"}, b"12345")

    with pytest.raises(providers.ProviderResponseValidationError) as raised:
        asyncio.run(providers._read_bounded_provider_response(response, 4))

    assert raised.value.code == "provider_response_bytes_exceeded"
    assert response.iterated is False


def test_provider_content_length_exact_limit_is_accepted():
    response = _StreamResponse({"content-length": "4"}, b"1234")

    content = asyncio.run(providers._read_bounded_provider_response(response, 4))

    assert content == b"1234"
    assert response.iterated is True


def test_provider_chunked_response_over_limit_is_rejected_incrementally():
    response = _StreamResponse({}, chunks=[b"12", b"345"])

    with pytest.raises(providers.ProviderResponseValidationError) as raised:
        asyncio.run(providers._read_bounded_provider_response(response, 4))

    assert raised.value.code == "provider_response_bytes_exceeded"


def test_provider_chunked_response_exact_limit_is_accepted():
    response = _StreamResponse({}, chunks=[b"12", b"34"])

    content = asyncio.run(providers._read_bounded_provider_response(response, 4))

    assert content == b"1234"


def test_provider_error_response_uses_separate_64k_cap():
    client = _VariationClient(
        status_code=503,
        raw_body=b"failure",
        headers={
            "content-length": str(providers.PROVIDER_ERROR_RESPONSE_MAX_BYTES + 1)
        },
    )

    with pytest.raises(providers.ProviderResponseValidationError) as raised:
        asyncio.run(
            providers._stream_bounded_provider_response(
                client,
                "POST",
                "https://provider.example.test/v1/images/generations",
                response_image_count=4,
            )
        )

    assert raised.value.code == "provider_response_bytes_exceeded"
    assert raised.value.details == {
        "max_bytes": providers.PROVIDER_ERROR_RESPONSE_MAX_BYTES
    }


def test_common_generation_oversized_json_is_structured_and_redacted(monkeypatch):
    response_limit = providers._provider_json_response_max_bytes(1)
    client = _VariationClient(
        raw_body=b"{}",
        headers={"content-length": str(response_limit + 1)},
    )
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: client)

    result = asyncio.run(
        providers.generate_for_provider(_provider(), "synthetic prompt")
    )

    assert result.success is False
    assert result.error_code == "provider_response_bytes_exceeded"
    assert result.error_details == {
        "validation_code": "provider_response_bytes_exceeded",
        "max_bytes": response_limit,
    }
    assert "synthetic-test-key" not in result.error


def test_variation_oversized_json_stops_before_json_parse(monkeypatch):
    import httpx

    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(
        providers,
        "_provider_json_response_max_bytes",
        lambda image_count=1: 4,
    )
    monkeypatch.setattr(
        main,
        "_parse_provider_json_response",
        lambda response: (_ for _ in ()).throw(
            AssertionError("oversized response must not be parsed")
        ),
    )
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _VariationClient(
            raw_body=b"{}",
            headers={"content-length": "5"},
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request()))

    assert raised.value.status_code == 502
    assert raised.value.detail == {
        "code": "image_variation_invalid_response",
        "message": "variation provider returned an invalid response",
        "validation_code": "provider_response_bytes_exceeded",
        "max_bytes": 4,
    }


@pytest.mark.parametrize("n", [0, 5])
def test_variation_count_must_be_between_one_and_four(n):
    with pytest.raises(ValidationError):
        _variation_request(n=n)


@pytest.mark.parametrize(
    ("requested_count", "actual_count"),
    [(1, 2), (2, 1), (1, 0)],
)
def test_variation_rejects_response_item_count_mismatch(
    monkeypatch,
    requested_count,
    actual_count,
):
    import httpx

    encoded = base64.b64encode(_png_bytes()).decode("ascii")
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _VariationClient(
            {"data": [{"b64_json": encoded} for _ in range(actual_count)]}
        ),
    )
    monkeypatch.setattr(
        main,
        "_save_image",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("mismatched response items must not be saved")
        ),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main.image_variations(_variation_request(n=requested_count)))

    assert raised.value.status_code == 502
    assert raised.value.detail == {
        "code": "image_variation_invalid_response",
        "message": "variation provider returned an invalid response",
        "validation_code": "variation_response_item_count_mismatch",
        "requested_count": requested_count,
        "actual_count": actual_count,
    }


def test_variation_sends_valid_count_without_clamping(monkeypatch):
    import httpx

    encoded = base64.b64encode(_png_bytes()).decode("ascii")
    client = _VariationClient(
        {"data": [{"b64_json": encoded} for _ in range(4)]}
    )
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [_variation_provider()])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(
        main,
        "_save_image",
        lambda *args, **kwargs: "gallery/variation.png",
    )

    response = asyncio.run(main.image_variations(_variation_request(n=4)))

    assert response["success"] is True
    assert len(response["images"]) == 4
    assert client.calls[0][1]["data"]["n"] == 4
