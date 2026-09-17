import asyncio
import gzip
import zlib

import httpx
import pytest

import providers


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "identity"])
@pytest.mark.parametrize("status", [200, 400])
def test_bounded_response_decodes_once(encoding, status):
    body = b'{"data":[],"message":"synthetic"}'
    packed = gzip.compress(body) if encoding == "gzip" else zlib.compress(body) if encoding == "deflate" else body

    async def run():
        def handler(request):
            return httpx.Response(status, headers={
                "content-encoding": encoding,
                "content-length": str(len(packed)),
                "content-type": "application/json",
            }, content=packed)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            response = await providers._stream_bounded_provider_response(client, "POST", "https://synthetic.test")
            assert response.content == body
            assert response.status_code == status
            assert response.json()["data"] == []
            assert "content-encoding" not in response.headers
            assert int(response.headers["content-length"]) == len(body)

    asyncio.run(run())


def test_decompressed_response_still_has_byte_limit():
    async def run():
        def handler(request):
            return httpx.Response(200, headers={"content-encoding": "gzip"}, content=gzip.compress(b"x" * 4096))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(providers.ProviderResponseValidationError) as exc:
                await providers._stream_bounded_provider_response(client, "POST", "https://synthetic.test", success_max_bytes=1024)
            assert exc.value.code == "provider_response_bytes_exceeded"
    asyncio.run(run())
