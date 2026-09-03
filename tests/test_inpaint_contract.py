"""Fail-closed request-contract tests for image generation and inpainting."""

import asyncio
import base64
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image

import main


def _image_bytes(*, image_format="PNG", size=(4, 4)):
    buffer = BytesIO()
    Image.new("RGB", size, color=(32, 96, 160)).save(buffer, format=image_format)
    return buffer.getvalue()


def _data_url(*, image_format="PNG", size=(4, 4), declared_mime=None):
    payload = _image_bytes(image_format=image_format, size=size)
    mime = declared_mime or {
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "WEBP": "image/webp",
    }[image_format]
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _provider(
    provider_id="provider-a",
    *,
    endpoint_type="openai",
    inpaint_mask=True,
    enabled=True,
    provider_type="image",
):
    return SimpleNamespace(
        id=provider_id,
        name=f"Provider {provider_id}",
        model="image-model",
        color="#5b8def",
        type=provider_type,
        enabled=enabled,
        endpoint_type=endpoint_type,
        capabilities={"inpaint_mask": inpaint_mask},
    )


def _request(**overrides):
    values = {
        "prompt": "replace the selected area",
        "providers": ["provider-a"],
    }
    values.update(overrides)
    return main.GenerateRequest(**values)


def _contract_error(request, code):
    with pytest.raises(HTTPException) as caught:
        main._validate_generation_request_inputs(request)
    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == code
    return caught.value.detail


def _route_request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


@pytest.mark.parametrize("mode", ["variation", "T2I", " t2i", "t2i ", ""])
def test_mode_is_exact_and_rejected_before_task_allocation(monkeypatch, mode):
    monkeypatch.setattr(main, "generation_counter", 730)
    existing_task_ids = set(main.image_tasks)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.generate(_request(mode=mode), _route_request()))

    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "invalid_mode"
    assert main.generation_counter == 730
    assert set(main.image_tasks) == existing_task_ids


def test_t2i_rejects_image_and_mask_fields():
    image = _data_url()
    _contract_error(_request(mode="t2i", image_data=image), "image_input_not_allowed")
    _contract_error(
        _request(mode="t2i", image_data_list=[image]),
        "image_input_not_allowed",
    )
    _contract_error(_request(mode="t2i", mask_data=image), "mask_input_not_allowed")
    _contract_error(
        _request(mode="t2i", mask_contract=main.INPAINT_MASK_CONTRACT),
        "mask_input_not_allowed",
    )


def test_i2i_requires_images_rejects_masks_and_preserves_legacy_multi_image():
    first = _data_url(size=(4, 4))
    second = _data_url(size=(5, 3))
    _contract_error(_request(mode="i2i"), "i2i_image_required")
    _contract_error(
        _request(mode="i2i", image_data=first, mask_data=first),
        "mask_input_not_allowed",
    )

    legacy = main._validate_generation_request_inputs(
        _request(mode="i2i", image_data=first)
    )
    assert [item["value"] for item in legacy["images"]] == [first]

    multiple = main._validate_generation_request_inputs(
        _request(mode="i2i", image_data_list=[first, second])
    )
    assert [item["value"] for item in multiple["images"]] == [first, second]

    matching_legacy = main._validate_generation_request_inputs(
        _request(mode="i2i", image_data=first, image_data_list=[first, second])
    )
    assert [item["value"] for item in matching_legacy["images"]] == [first, second]
    _contract_error(
        _request(mode="i2i", image_data=second, image_data_list=[first]),
        "i2i_base_image_conflict",
    )


def test_inpaint_enforces_single_base_mask_and_contract():
    base_image = _data_url()
    mask = _data_url()
    _contract_error(
        _request(
            mode="inpaint",
            mask_data=mask,
            mask_contract=main.INPAINT_MASK_CONTRACT,
        ),
        "image_data_required",
    )
    _contract_error(
        _request(
            mode="inpaint",
            image_data=base_image,
            image_data_list=[base_image],
            mask_data=mask,
            mask_contract=main.INPAINT_MASK_CONTRACT,
        ),
        "inpaint_image_data_list_not_allowed",
    )
    _contract_error(
        _request(mode="inpaint", image_data=base_image),
        "inpaint_mask_required",
    )
    _contract_error(
        _request(
            mode="inpaint",
            image_data=base_image,
            mask_data=mask,
            mask_contract="unknown-mask-v1",
        ),
        "inpaint_mask_contract_unsupported",
    )


@pytest.mark.parametrize(
    ("image_data", "code"),
    [
        ("data:image/png;base64,%%%", "invalid_image_base64"),
        (
            "data:image/gif;base64,"
            + base64.b64encode(_image_bytes()).decode("ascii"),
            "unsupported_image_mime",
        ),
        (_data_url(declared_mime="image/jpeg"), "image_mime_mismatch"),
        (
            "data:image/png;base64,"
            + base64.b64encode(b"not an image").decode("ascii"),
            "invalid_image_payload",
        ),
    ],
)
def test_image_payload_validation_rejects_bad_base64_mime_and_payload(image_data, code):
    _contract_error(_request(mode="i2i", image_data=image_data), code)


def test_generation_image_byte_and_pixel_limits(monkeypatch):
    image = _data_url(size=(4, 4))
    decoded_size = len(_image_bytes(size=(4, 4)))

    monkeypatch.setattr(main, "MAX_GENERATION_INPUT_BYTES", decoded_size - 1)
    _contract_error(_request(mode="i2i", image_data=image), "image_too_large")

    monkeypatch.setattr(main, "MAX_GENERATION_INPUT_BYTES", decoded_size + 1)
    monkeypatch.setattr(main, "MAX_GENERATION_INPUT_PIXELS", 15)
    _contract_error(_request(mode="i2i", image_data=image), "image_pixels_exceeded")


def test_inpaint_requires_png_mask_with_matching_dimensions():
    base_image = _data_url(size=(4, 4))
    jpeg_mask = _data_url(image_format="JPEG", size=(4, 4))
    _contract_error(
        _request(
            mode="inpaint",
            image_data=base_image,
            mask_data=jpeg_mask,
            mask_contract=main.INPAINT_MASK_CONTRACT,
        ),
        "unsupported_image_mime",
    )

    wrong_size_mask = _data_url(size=(5, 4))
    _contract_error(
        _request(
            mode="inpaint",
            image_data=base_image,
            mask_data=wrong_size_mask,
            mask_contract=main.INPAINT_MASK_CONTRACT,
        ),
        "inpaint_image_mask_size_mismatch",
    )


@pytest.mark.parametrize(
    "bad_provider",
    [
        _provider("provider-b", endpoint_type="auto"),
        _provider("provider-b", inpaint_mask=False),
        _provider("provider-b", enabled=False),
        _provider("provider-b", provider_type="llm"),
    ],
)
def test_inpaint_requires_every_selected_provider_to_be_authorized_before_task(
    monkeypatch, bad_provider
):
    good_provider = _provider()
    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[good_provider, bad_provider]),
            get_image_providers=lambda: [good_provider, bad_provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "generation_counter", 811)
    existing_task_ids = set(main.image_tasks)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.generate(
                _request(
                    mode="inpaint",
                    providers=["provider-a", "provider-b"],
                    image_data=_data_url(),
                    mask_data=_data_url(),
                    mask_contract=main.INPAINT_MASK_CONTRACT,
                ),
                _route_request(),
            )
        )

    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "inpaint_provider_unsupported"
    assert caught.value.detail["providers"][0]["id"] == "provider-b"
    assert main.generation_counter == 811
    assert set(main.image_tasks) == existing_task_ids


def test_inpaint_rejects_unknown_selected_provider_before_task(monkeypatch):
    good_provider = _provider()
    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[good_provider]),
            get_image_providers=lambda: [good_provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "generation_counter", 812)
    existing_task_ids = set(main.image_tasks)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.generate(
                _request(
                    mode="inpaint",
                    providers=["provider-a", "missing-provider"],
                    image_data=_data_url(),
                    mask_data=_data_url(),
                    mask_contract=main.INPAINT_MASK_CONTRACT,
                ),
                _route_request(),
            )
        )

    assert caught.value.detail["code"] == "inpaint_provider_unsupported"
    assert caught.value.detail["providers"] == [
        {"id": "missing-provider", "reason": "provider_not_found"}
    ]
    assert main.generation_counter == 812
    assert set(main.image_tasks) == existing_task_ids


def test_valid_inpaint_passes_strict_provider_kwargs_without_network(monkeypatch):
    provider = _provider()
    base_image = _data_url(size=(6, 4))
    mask = _data_url(size=(6, 4))
    captured = {}

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[provider]),
            get_image_providers=lambda: [provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_write_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "_save_history_entry", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "image_gen_semaphore", None)
    monkeypatch.setattr(main, "generation_counter", 900)

    import providers

    async def scenario():
        started = asyncio.Event()

        async def fake_generate_for_provider(_provider, _prompt, **kwargs):
            captured.update(kwargs)
            started.set()
            await asyncio.sleep(60)

        monkeypatch.setattr(providers, "generate_for_provider", fake_generate_for_provider)
        result = await main.generate(
            _request(
                mode="inpaint",
                image_data=base_image,
                mask_data=mask,
                mask_contract=main.INPAINT_MASK_CONTRACT,
            ),
            _route_request(),
        )
        gen_id = result["generation_id"]
        handle = main.image_task_handles[gen_id]
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
            assert captured["mode"] == "inpaint"
            assert captured["image_data"] == base_image
            assert captured["mask_data"] == mask
            assert captured["mask_contract"] == main.INPAINT_MASK_CONTRACT
            assert captured["inpaint_authorized"] is True
            assert "image_data_list" not in captured

            cancelled = await main.cancel_generate(gen_id)
            await asyncio.wait_for(handle, timeout=1)
            assert cancelled == {"ok": True, "status": "cancelled"}
            assert main.image_tasks[gen_id]["status"] == "cancelled"
        finally:
            if not handle.done():
                handle.cancel()
                try:
                    await handle
                except asyncio.CancelledError:
                    pass
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)
            main.generation_history.pop(gen_id, None)

    asyncio.run(scenario())
