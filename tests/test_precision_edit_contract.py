"""First-wave fail-closed contract tests for annotation-based precision editing."""

import asyncio
import base64
import copy
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

import main
from config import PrecisionEditProfile, ProviderConfig
from image_tools.cutout_registry import CutoutAdapterRegistry


@pytest.fixture(autouse=True)
def isolate_precision_contract_runtime_files(tmp_path, monkeypatch):
    """Keep direct route tests from appending to the developer's real storage."""
    monkeypatch.setattr(main, "LOG_FILE", tmp_path / "logs.jsonl")
    monkeypatch.setattr(main, "HISTORY_FILE", tmp_path / "history.jsonl")


def _image_data(*, size=(12, 8)):
    output = BytesIO()
    Image.new("RGB", size, color=(32, 96, 160)).save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _image_bytes(*, image_format="PNG", size=(12, 8)):
    output = BytesIO()
    Image.new("RGB", size, color=(32, 96, 160)).save(output, format=image_format)
    return output.getvalue()


def _annotation(annotation_type="arrow", **values):
    return {"type": annotation_type, **values}


V3_CANONICAL_ANNOTATIONS = [
    (
        "arrow",
        _annotation(
            "arrow",
            label=1,
            instruction="Move the marker.",
            x1=0.10,
            y1=0.20,
            x2=0.70,
            y2=0.80,
        ),
    ),
    (
        "rectangle",
        _annotation(
            "rectangle",
            label=1,
            instruction="Replace this region.",
            x=0.10,
            y=0.20,
            width=0.60,
            height=0.50,
        ),
    ),
    (
        "ellipse",
        _annotation(
            "ellipse",
            label=1,
            instruction="Retouch this region.",
            x=0.10,
            y=0.20,
            width=0.60,
            height=0.50,
        ),
    ),
    (
        "brush",
        _annotation(
            "brush",
            label=1,
            instruction="Remove this stroke.",
            points=[
                {"x": 0.10, "y": 0.20},
                {"x": 0.40, "y": 0.50},
                {"x": 0.70, "y": 0.60},
            ],
        ),
    ),
    (
        "text",
        _annotation(
            "text",
            label=1,
            text="NEW SIGN",
            instruction="Use this wording.",
            x=0.25,
            y=0.18,
        ),
    ),
]


def _precision_request(**overrides):
    source = _image_data()
    values = {
        "prompt": "Replace the marked cup with a glass cup.",
        "providers": ["precision-provider"],
        "provider_settings": {"precision-provider": {"model": "mock-edit-1"}},
        "mode": "precision_edit",
        "image_data": source,
        "annotation_image_data": source,
        "annotation_contract": "genbox-annotation-v1",
        "annotations": [
            _annotation("arrow", x1=0.10, y1=0.20, x2=0.60, y2=0.70),
            _annotation("rectangle", x=0.20, y=0.20, width=0.30, height=0.40),
            _annotation("text", x=0.25, y=0.18, text="Replace this cup"),
        ],
    }
    values.update(overrides)
    return main.GenerateRequest(**values)


def _precision_resize_only_request(**overrides):
    values = {
        "prompt": "Keep the subject unchanged while expanding the canvas.",
        "providers": ["precision-provider"],
        "provider_settings": {"precision-provider": {"model": "mock-edit-1"}},
        "mode": "precision_edit",
        "image_data": _image_data(),
        "precision_size_mode": "resize",
        "precision_target_size": "64x64",
        "precision_resize_prompt": "Extend the background naturally on every side.",
    }
    values.update(overrides)
    return main.GenerateRequest(**values)


def _expect_error(request, code):
    with pytest.raises(HTTPException) as caught:
        main._validate_generation_request_inputs(request)
    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == code


def _provider(precision_edit=True, supported_sizes=None):
    model_capabilities = {"precision_edit": precision_edit}
    if supported_sizes is not None:
        model_capabilities["supported_sizes"] = supported_sizes
    return SimpleNamespace(
        id="precision-provider",
        name="Mock precision provider",
        model="mock-edit-1",
        color="#5b8def",
        type="image",
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": precision_edit, "i2i": True},
        extra={"model_capabilities": {"mock-edit-1": model_capabilities}},
    )


def _route_request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


def _precision_provider_state(status="queued", progress=0, *, success=None):
    result = None
    if success is not None:
        result = {
            "success": success,
            "local_path": "generated.png" if success else None,
            "generation_id": "provider-result" if success else None,
            "error": "provider failed" if not success else "",
            "model": "precision-provider",
            "seq": 0,
            "elapsed_seconds": 1.0,
        }
    return {
        "status": status,
        "progress": progress,
        "model": "precision-provider",
        "name": "Mock precision provider",
        "color": "#5b8def",
        "seq": 0,
        "qty": 1,
        "log": [],
        "result": result,
    }


def _precision_status_task(status, states, results=None):
    return {
        "status": status,
        "progress": 0,
        "provider_states": states,
        "start_time": main.time.time(),
        "results": results or {},
        "enhanced_prompt": None,
        "llm_error": None,
        "continuous_id": None,
    }


def _read_precision_status(gen_id, task):
    main.image_tasks[gen_id] = task
    try:
        return asyncio.run(main.get_generate_status(gen_id))
    finally:
        main.image_tasks.pop(gen_id, None)
        main.image_task_handles.pop(gen_id, None)


def test_endpoint_only_provider_is_reported_as_configured(monkeypatch):
    endpoint_provider = ProviderConfig(
        id="endpoint-only",
        name="Endpoint only",
        type="image",
        endpoints=[{"name": "Primary", "url": "https://provider.example.test/v1", "key": "endpoint-key"}],
        models=["edit-model"],
    )
    monkeypatch.setattr(main.cfg_mgr.config, "providers", [endpoint_provider])
    payload = asyncio.run(main.list_providers())
    assert payload["providers"][0]["has_key"] is True



def test_precision_edit_accepts_annotation_v1_and_normalizes_objects():
    normalized = main._validate_generation_request_inputs(_precision_request())
    assert normalized["mode"] == "precision_edit"
    assert normalized["images"][0]["width"] == 12
    assert normalized["images"][0]["height"] == 8
    assert normalized["annotation_image"]["width"] == 12
    assert [item["type"] for item in normalized["annotations"]] == ["arrow", "rectangle", "text"]
    assert normalized["precision_size_mode"] == "preserve"
    assert normalized["precision_target_size"] is None


def test_precision_edit_defaults_strategy_and_selection_contract():
    normalized = main._validate_generation_request_inputs(_precision_request())

    assert normalized["precision_strategy"] == "standard"
    assert normalized["precision_selection_mode"] == "annotation"
    assert normalized["precision_selection_feather"] == 0.0


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("precision_strategy", "deep", "precision_strategy_invalid"),
        ("precision_selection_mode", "mask", "precision_selection_mode_invalid"),
        ("precision_selection_feather", -1, "precision_selection_feather_invalid"),
        ("precision_selection_feather", 65, "precision_selection_feather_invalid"),
    ],
)
def test_precision_edit_rejects_invalid_strategy_selection_controls(field, value, code):
    _expect_error(_precision_request(**{field: value}), code)


def test_precision_edit_local_selection_requires_region_annotation():
    _expect_error(
        _precision_request(
            annotation_contract="genbox-annotation-v3",
            precision_selection_mode="local",
            precision_selection_feather=12,
            annotations=[_annotation("text", label=1, text="Keep the person.", x=0.2, y=0.2)],
        ),
        "precision_local_selection_required",
    )


def test_precision_edit_local_selection_accepts_region_and_normalizes_feather():
    normalized = main._validate_generation_request_inputs(
        _precision_request(
            annotation_contract="genbox-annotation-v3",
            precision_selection_mode="local",
            precision_selection_feather=12,
            annotations=[
                _annotation(
                    "ellipse",
                    label=1,
                    instruction="Repair the marked lower body.",
                    x=0.2,
                    y=0.2,
                    width=0.4,
                    height=0.6,
                ),
            ],
        )
    )

    assert normalized["precision_selection_mode"] == "local"
    assert normalized["precision_selection_feather"] == 12.0


def test_precision_edit_local_selection_is_not_available_for_pure_resize():
    _expect_error(
        _precision_resize_only_request(
            precision_selection_mode="local",
            precision_selection_feather=8,
        ),
        "precision_local_selection_requires_annotations",
    )


def test_non_precision_mode_rejects_precision_strategy_fields():
    _expect_error(
        main.GenerateRequest(
            prompt="A lighthouse",
            mode="t2i",
            precision_strategy="fine",
        ),
        "precision_fields_not_allowed",
    )


def test_precision_edit_preserve_rejects_generic_generation_size():
    _expect_error(_precision_request(size="1024x1024"), "precision_preserve_size_conflict")
    _expect_error(_precision_request(upscale_to="2048"), "precision_upscale_not_allowed")
    _expect_error(_precision_request(upscale_ratio="16:9"), "precision_upscale_not_allowed")


def test_precision_edit_preserve_allows_auto_size():
    normalized = main._validate_generation_request_inputs(_precision_request(size="auto"))
    assert normalized["precision_size_mode"] == "preserve"
    assert normalized["precision_target_size"] is None


def test_precision_edit_resize_requires_valid_explicit_target():
    _expect_error(_precision_request(precision_size_mode="resize"), "precision_target_size_invalid")
    _expect_error(
        _precision_request(precision_size_mode="resize", precision_target_size="0x900"),
        "precision_target_size_invalid",
    )


def test_precision_edit_resize_defaults_blank_composition_guidance():
    normalized = main._validate_generation_request_inputs(
        _precision_request(
            precision_size_mode="resize",
            precision_target_size="1792x768",
            precision_resize_prompt="   ",
        )
    )

    assert normalized["precision_resize_prompt"] == main.DEFAULT_PRECISION_RESIZE_GUIDANCE


@pytest.mark.parametrize(
    "target_size",
    [
        "1792X768",
        " 1792x768",
        "1792x768 ",
        "01792x768",
        "1e3x768",
        "1024.5x768",
        "1792-768",
    ],
)
def test_precision_edit_resize_rejects_noncanonical_target_size(target_size):
    _expect_error(
        _precision_request(
            precision_size_mode="resize",
            precision_target_size=target_size,
            precision_resize_prompt="Extend the background sideways.",
        ),
        "precision_target_size_invalid",
    )


def test_precision_edit_resize_accepts_canonical_target_and_guidance():
    normalized = main._validate_generation_request_inputs(
        _precision_request(
            precision_size_mode="resize",
            precision_target_size="1792x768",
            precision_resize_prompt="Extend the background sideways.",
            precision_output_size_policy="fit_crop",
        )
    )
    assert normalized["precision_size_mode"] == "resize"
    assert normalized["precision_target_size"] == "1792x768"
    assert normalized["precision_resize_prompt"] == "Extend the background sideways."
    assert normalized["precision_output_size_policy"] == "fit_crop"


@pytest.mark.parametrize("policy", ["", "crop", "FIT_CROP", "strict "])
def test_precision_resize_rejects_invalid_output_size_policy(policy):
    _expect_error(
        _precision_resize_only_request(precision_output_size_policy=policy),
        "precision_output_size_policy_invalid",
    )


@pytest.mark.parametrize(
    "payload",
    [
        main.GenerateRequest(
            prompt="Synthetic generation",
            mode="t2i",
            precision_output_size_policy="fit_crop",
        ),
        main.GenerateRequest(
            prompt="Synthetic inpaint",
            mode="inpaint",
            image_data=_image_data(),
            mask_data=_image_data(),
            mask_contract=main.INPAINT_MASK_CONTRACT,
            precision_output_size_policy="strict",
        ),
        _precision_request(precision_output_size_policy="strict"),
    ],
)
def test_precision_output_size_policy_is_resize_scoped(payload):
    _expect_error(payload, "precision_output_size_policy_not_allowed")


def test_precision_edit_resize_only_accepts_source_without_annotation_fields():
    normalized = main._validate_generation_request_inputs(_precision_resize_only_request())

    assert normalized["mode"] == "precision_edit"
    assert normalized["precision_canvas_only"] is True
    assert normalized["precision_size_mode"] == "resize"
    assert normalized["precision_target_size"] == "64x64"
    assert "annotation_image" not in normalized
    assert "annotation_contract" not in normalized
    assert "annotations" not in normalized


@pytest.mark.parametrize(
    "request_factory",
    [_precision_request, _precision_resize_only_request],
)
def test_precision_edit_rejects_explicit_empty_image_data_list(request_factory):
    _expect_error(
        request_factory(image_data_list=[]),
        "precision_edit_image_data_list_not_allowed",
    )


@pytest.mark.parametrize(
    ("unknown_field", "value"),
    [
        ("annotationImageData", _image_data()),
        ("annotation_image", _image_data()),
        ("annotations_json", "[]"),
        ("precisionTargetSize", "64x64"),
        ("imageDataList", []),
    ],
)
def test_precision_edit_rejects_unknown_precision_like_request_fields(unknown_field, value):
    payload = _precision_resize_only_request().model_dump(exclude_unset=True)
    payload[unknown_field] = value

    with pytest.raises(ValidationError) as caught:
        main.GenerateRequest(**payload)

    errors = caught.value.errors()
    assert errors[0]["type"] == "precision_unknown_field"
    assert errors[0]["msg"] == "precision_edit contains unsupported precision fields"
    assert str(value) not in errors[0]["msg"]


def test_precision_unknown_alias_is_rejected_by_http_validation_before_task_allocation():
    payload = _precision_resize_only_request().model_dump(exclude_unset=True)
    payload["annotation_image"] = _image_data()
    generation_counter = main.generation_counter

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/generate",
        headers={"Origin": "http://testserver"},
        json=payload,
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "precision_unknown_field"
    assert detail[0]["msg"] == "precision_edit contains unsupported precision fields"
    assert _image_data() not in str(detail)
    assert main.generation_counter == generation_counter


def test_precision_fit_crop_policy_passes_http_route_and_reaches_task_kwargs(monkeypatch):
    provider = _provider(supported_sizes=["64x64"])

    async def fake_process(_generation_id):
        return None

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[provider]),
            get_image_providers=lambda: [provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)
    payload = _precision_resize_only_request(
        precision_output_size_policy="fit_crop"
    ).model_dump(exclude_unset=True)

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/generate",
        headers={"Origin": "http://testserver"},
        json=payload,
    )

    assert response.status_code == 200
    generation_id = response.json()["generation_id"]
    try:
        task = main.image_tasks[generation_id]
        assert task["kwargs"]["precision_output_size_policy"] == "fit_crop"
        assert task["provider_kwargs_map"]["precision-provider"][
            "precision_output_size_policy"
        ] == "fit_crop"
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


def test_non_precision_mode_keeps_existing_unknown_extra_compatibility():
    request = main.GenerateRequest(
        prompt="A lighthouse",
        mode="t2i",
        annotationImageData="legacy-client-extra",
    )

    assert request.mode == "t2i"
    assert not hasattr(request, "annotationImageData")


@pytest.mark.parametrize(
    "stray_field",
    [
        {"annotation_image_data": None},
        {"annotation_contract": ""},
        {"annotations": []},
        {"annotation_contract": "genbox-annotation-v3"},
    ],
)
def test_precision_edit_resize_only_rejects_stray_annotation_fields(stray_field):
    _expect_error(
        _precision_resize_only_request(**stray_field),
        "precision_resize_annotation_fields_conflict",
    )


def test_precision_edit_without_annotations_cannot_use_preserve_mode():
    _expect_error(
        _precision_resize_only_request(
            precision_size_mode="preserve",
            precision_target_size=None,
            precision_resize_prompt=None,
        ),
        "precision_canvas_only_resize_required",
    )


def test_precision_edit_rejects_unknown_contract():
    _expect_error(_precision_request(annotation_contract="annotation-v9"), "precision_annotation_contract_unsupported")


@pytest.mark.parametrize(
    ("annotation", "expected_code"),
    [
        (_annotation("arrow", x1=-0.01, y1=0.1, x2=0.4, y2=0.5), "precision_annotation_coordinate_invalid"),
        (_annotation("arrow", x1=0.1, y1=0.1, x2=1.01, y2=0.5), "precision_annotation_coordinate_invalid"),
        (_annotation("rectangle", x=0.1, y=0.1, width=0.95, height=0.2), "precision_annotation_geometry_invalid"),
    ],
)
def test_precision_edit_rejects_out_of_bounds_coordinates(annotation, expected_code):
    _expect_error(_precision_request(annotations=[annotation]), expected_code)


def test_precision_edit_rejects_overlong_text():
    annotation = _annotation("text", x=0.2, y=0.2, text="x" * 501)
    _expect_error(_precision_request(annotations=[annotation]), "precision_annotation_text_exceeded")


@pytest.mark.parametrize("text", ["<img src=x>", "https://example.invalid", "C:\\Users\\private\\source.png", "../../private/source.png"])
def test_precision_edit_rejects_html_urls_and_paths(text):
    annotation = _annotation("text", x=0.2, y=0.2, text=text)
    _expect_error(_precision_request(annotations=[annotation]), "precision_annotation_text_unsafe")


def test_precision_edit_rejects_annotation_image_size_mismatch():
    _expect_error(_precision_request(annotation_image_data=_image_data(size=(8, 12))), "precision_annotation_image_size_mismatch")


def test_precision_edit_accepts_annotation_v2_and_sorts_by_label():
    normalized = main._validate_generation_request_inputs(
        _precision_request(
            annotation_contract="genbox-annotation-v2",
            annotations=[
                _annotation(
                    "arrow",
                    label=2,
                    instruction="Replace the left cup with a glass cup.",
                    x1=0.10,
                    y1=0.20,
                    x2=0.60,
                    y2=0.70,
                ),
                _annotation(
                    "rectangle",
                    label=1,
                    instruction="Remove the price tag.",
                    x=0.20,
                    y=0.20,
                    width=0.30,
                    height=0.40,
                ),
                _annotation("text", label=3, text="NEW SIGN", x=0.25, y=0.18),
            ],
        )
    )
    assert normalized["annotation_contract"] == "genbox-annotation-v2"
    assert [item["label"] for item in normalized["annotations"]] == [1, 2, 3]
    assert normalized["annotations"][0]["instruction"] == "Remove the price tag."
    assert normalized["annotations"][1]["instruction"] == "Replace the left cup with a glass cup."
    assert "instruction" not in normalized["annotations"][2]


def test_precision_edit_accepts_annotation_v3_ellipse_and_brush():
    normalized = main._validate_generation_request_inputs(
        _precision_request(
            annotation_contract="genbox-annotation-v3",
            annotations=[
                _annotation(
                    "brush",
                    label=2,
                    instruction="Remove the marked reflection.",
                    points=[{"x": 0.1, "y": 0.2}, {"x": 0.4, "y": 0.5}],
                ),
                _annotation(
                    "ellipse",
                    label=1,
                    instruction="Make this badge blue.",
                    x=0.2,
                    y=0.15,
                    width=0.3,
                    height=0.4,
                ),
            ],
        )
    )

    assert normalized["annotation_contract"] == "genbox-annotation-v3"
    assert [item["type"] for item in normalized["annotations"]] == ["ellipse", "brush"]
    assert normalized["annotations"][1]["points"] == [
        {"x": 0.1, "y": 0.2},
        {"x": 0.4, "y": 0.5},
    ]


@pytest.mark.parametrize(("annotation_type", "annotation"), V3_CANONICAL_ANNOTATIONS)
def test_precision_edit_v3_canonical_annotation_closes_request_validation_and_http_task(
    monkeypatch,
    annotation_type,
    annotation,
):
    provider = _provider()
    process_calls = []

    async def fake_process(generation_id):
        process_calls.append(generation_id)

    monkeypatch.setattr(main, "is_prod_mode", lambda: False)
    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[provider]),
            get_image_providers=lambda: [provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)

    request = _precision_request(
        annotation_contract="genbox-annotation-v3",
        annotations=[copy.deepcopy(annotation)],
    )
    normalized = main._validate_generation_request_inputs(request)
    assert normalized["annotations"] == [annotation]

    before_counter = main.generation_counter
    before_tasks = set(main.image_tasks)
    before_handles = set(main.image_task_handles)
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/generate",
        headers={"Origin": "http://testserver"},
        json=request.model_dump(exclude_unset=True),
    )

    assert response.status_code == 200
    generation_id = response.json()["generation_id"]
    try:
        assert main.generation_counter == before_counter + 1
        assert set(main.image_tasks) == before_tasks | {generation_id}
        assert set(main.image_task_handles) == before_handles | {generation_id}
        assert process_calls == [generation_id]
        task = main.image_tasks[generation_id]
        assert task["mode"] == "precision_edit"
        assert task["kwargs"]["precision_size_mode"] == "preserve"
        assert task["kwargs"]["annotation_contract"] == "genbox-annotation-v3"
        assert task["kwargs"]["annotation_image_data"] == request.annotation_image_data
        assert task["kwargs"]["annotations"] == [annotation]
        assert task["kwargs"]["annotations"][0]["type"] == annotation_type
        assert "annotation_data" not in task["kwargs"]
        assert "annotation_objects" not in task["kwargs"]
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


@pytest.mark.parametrize(
    ("annotation_type", "presentation_fields"),
    [
        ("arrow", {"color": "#ef4444", "stroke_width": 5}),
        ("rectangle", {"color": "#ef4444", "stroke_width": 5}),
        ("ellipse", {"color": "#ef4444", "stroke_width": 5}),
        ("brush", {"color": "#ef4444", "stroke_width": 5}),
        ("text", {"color": "#ef4444", "stroke_width": 5, "font_size": 24}),
    ],
)
def test_precision_edit_v3_presentation_fields_fail_closed_without_allocating_task(
    monkeypatch,
    annotation_type,
    presentation_fields,
):
    annotation = copy.deepcopy(dict(V3_CANONICAL_ANNOTATIONS)[annotation_type])
    annotation.update(presentation_fields)
    request = _precision_request(
        annotation_contract="genbox-annotation-v3",
        annotations=[annotation],
    )
    expected_detail = {
        "code": "precision_annotation_fields_unsupported",
        "message": "annotations[0] contains missing or unsupported fields",
        "field": "annotations[0]",
        "unsupported_fields": sorted(presentation_fields),
        "missing_fields": [],
    }

    with pytest.raises(HTTPException) as caught:
        main._validate_generation_request_inputs(request)
    assert caught.value.status_code == 422
    assert caught.value.detail == expected_detail

    process_calls = []
    monkeypatch.setattr(main, "is_prod_mode", lambda: False)
    monkeypatch.setattr(main, "_process_image_gen", lambda generation_id: process_calls.append(generation_id))
    before_counter = main.generation_counter
    before_tasks = set(main.image_tasks)
    before_handles = set(main.image_task_handles)
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/generate",
        headers={"Origin": "http://testserver"},
        json=request.model_dump(exclude_unset=True),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail
    assert main.generation_counter == before_counter
    assert set(main.image_tasks) == before_tasks
    assert set(main.image_task_handles) == before_handles
    assert process_calls == []


@pytest.mark.parametrize(
    ("annotation", "unsupported_fields", "missing_fields"),
    [
        (
            _annotation(
                "arrow",
                label=1,
                instruction="Move it.",
                points=[{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
            ),
            ["points"],
            ["x1", "x2", "y1", "y2"],
        ),
        (
            _annotation(
                "arrow",
                label=1,
                instruction="Move it.",
                start={"x": 0.1, "y": 0.2},
                end={"x": 0.7, "y": 0.8},
            ),
            ["end", "start"],
            ["x1", "x2", "y1", "y2"],
        ),
        (
            _annotation(
                "brush",
                label=1,
                instruction="Remove it.",
                path=[{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
            ),
            ["path"],
            ["points"],
        ),
        (
            _annotation(
                "rectangle",
                label=1,
                instruction="Replace it.",
                x=0.1,
                y=0.2,
                x2=0.7,
                y2=0.8,
            ),
            ["x2", "y2"],
            ["height", "width"],
        ),
        (
            _annotation(
                "ellipse",
                label=1,
                instruction="Retouch it.",
                x=0.1,
                y=0.2,
                x2=0.7,
                y2=0.8,
            ),
            ["x2", "y2"],
            ["height", "width"],
        ),
        (
            _annotation(
                "text",
                label=1,
                content="NEW SIGN",
                instruction="Use this wording.",
                x=0.25,
                y=0.18,
            ),
            ["content"],
            ["text"],
        ),
    ],
)
def test_precision_edit_v3_annotation_aliases_fail_closed_at_validation_and_http(
    monkeypatch,
    annotation,
    unsupported_fields,
    missing_fields,
):
    request = _precision_request(
        annotation_contract="genbox-annotation-v3",
        annotations=[annotation],
    )
    expected_detail = {
        "code": "precision_annotation_fields_unsupported",
        "message": "annotations[0] contains missing or unsupported fields",
        "field": "annotations[0]",
        "unsupported_fields": unsupported_fields,
        "missing_fields": missing_fields,
    }

    with pytest.raises(HTTPException) as caught:
        main._validate_generation_request_inputs(request)
    assert caught.value.status_code == 422
    assert caught.value.detail == expected_detail

    monkeypatch.setattr(main, "is_prod_mode", lambda: False)
    before_counter = main.generation_counter
    before_tasks = set(main.image_tasks)
    before_handles = set(main.image_task_handles)
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/generate",
        headers={"Origin": "http://testserver"},
        json=request.model_dump(exclude_unset=True),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail
    assert main.generation_counter == before_counter
    assert set(main.image_tasks) == before_tasks
    assert set(main.image_task_handles) == before_handles


@pytest.mark.parametrize(
    ("annotation", "expected_code"),
    [
        (_annotation("ellipse", label=1, instruction="Edit.", x=0.1, y=0.1, width=0.0, height=0.2), "precision_annotation_geometry_invalid"),
        (_annotation("ellipse", label=1, instruction="Edit.", x=0.8, y=0.1, width=0.3, height=0.2), "precision_annotation_geometry_invalid"),
        (_annotation("brush", label=1, instruction="Edit.", points=[{"x": 0.1, "y": 0.1}]), "precision_annotation_geometry_invalid"),
        (_annotation("brush", label=1, instruction="Edit.", points=[{"x": 0.1, "y": 0.1}, {"x": 0.1, "y": 0.1}]), "precision_annotation_geometry_invalid"),
        (_annotation("brush", label=1, instruction="Edit.", points=[{"x": 0.1, "y": 0.1}, {"x": 1.01, "y": 0.2}]), "precision_annotation_coordinate_invalid"),
        (_annotation("brush", label=1, instruction="Edit.", points=[{"x": 0.1, "y": 0.1}, {"x": 0.2, "y": 0.2, "z": 0.3}]), "precision_annotation_geometry_invalid"),
    ],
)
def test_precision_edit_rejects_invalid_v3_ellipse_and_brush_geometry(annotation, expected_code):
    _expect_error(
        _precision_request(annotation_contract="genbox-annotation-v3", annotations=[annotation]),
        expected_code,
    )


def test_precision_edit_rejects_v3_brush_point_limits():
    too_many = [{"x": index / 1025, "y": 0.5} for index in range(1025)]
    _expect_error(
        _precision_request(
            annotation_contract="genbox-annotation-v3",
            annotations=[_annotation("brush", label=1, instruction="Edit.", points=too_many)],
        ),
        "precision_annotation_geometry_invalid",
    )

    paths = []
    for label in range(1, 6):
        points = [{"x": index / 1023, "y": label / 10} for index in range(1024)]
        paths.append(_annotation("brush", label=label, instruction="Edit.", points=points))
    _expect_error(
        _precision_request(annotation_contract="genbox-annotation-v3", annotations=paths),
        "precision_annotation_geometry_exceeded",
    )


@pytest.mark.parametrize("annotation_type", ["ellipse", "brush"])
def test_precision_edit_v3_requires_instruction_for_new_region_types(annotation_type):
    geometry = (
        {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
        if annotation_type == "ellipse"
        else {"points": [{"x": 0.1, "y": 0.1}, {"x": 0.2, "y": 0.2}]}
    )
    _expect_error(
        _precision_request(
            annotation_contract="genbox-annotation-v3",
            annotations=[_annotation(annotation_type, label=1, instruction="", **geometry)],
        ),
        "precision_annotation_instruction_required",
    )


def test_precision_edit_rejects_v2_arrow_without_instruction():
    _expect_error(
        _precision_request(
            annotation_contract="genbox-annotation-v2",
            annotations=[
                _annotation(
                    "arrow",
                    label=1,
                    instruction="",
                    x1=0.10,
                    y1=0.20,
                    x2=0.60,
                    y2=0.70,
                )
            ],
        ),
        "precision_annotation_instruction_required",
    )


def test_precision_edit_rejects_v2_duplicate_labels():
    _expect_error(
        _precision_request(
            annotation_contract="genbox-annotation-v2",
            annotations=[
                _annotation(
                    "arrow",
                    label=1,
                    instruction="Edit first.",
                    x1=0.10,
                    y1=0.20,
                    x2=0.60,
                    y2=0.70,
                ),
                _annotation(
                    "rectangle",
                    label=1,
                    instruction="Edit second.",
                    x=0.20,
                    y=0.20,
                    width=0.30,
                    height=0.40,
                ),
            ],
        ),
        "precision_annotation_label_duplicate",
    )


def test_precision_edit_rejects_v2_non_positive_label():
    _expect_error(
        _precision_request(
            annotation_contract="genbox-annotation-v2",
            annotations=[
                _annotation(
                    "arrow",
                    label=0,
                    instruction="Edit.",
                    x1=0.10,
                    y1=0.20,
                    x2=0.60,
                    y2=0.70,
                )
            ],
        ),
        "precision_annotation_label_invalid",
    )


def test_precision_edit_requires_explicit_model_in_provider_settings(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[provider]),
            get_image_providers=lambda: [provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.generate(
                _precision_request(provider_settings={}),
                _route_request(),
            )
        )
    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "precision_edit_provider_unsupported"
    assert caught.value.detail["providers"][0]["reason"] == "precision_edit_explicit_model_required"


def test_precision_edit_rejects_provider_without_explicit_edit_capability(monkeypatch):
    provider = _provider(precision_edit=False)
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=SimpleNamespace(providers=[provider]), get_image_providers=lambda: [provider]))
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.generate(_precision_request(), _route_request()))
    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "precision_edit_provider_unsupported"


@pytest.mark.parametrize(
    ("supported_sizes", "target_size", "reason"),
    [
        (None, "1792x768", "precision_edit_size_capability_unknown"),
        (["1024x1024"], "1792x768", "precision_edit_target_size_not_declared"),
        (["not-a-size", "0x768", "9000x9000"], "1792x768", "precision_edit_size_capability_unknown"),
        (
            ["1792X768", " 1792x768", "1792x768 ", "01792x768", "1e3x768", "1024.5x768", "1792-768"],
            "1792x768",
            "precision_edit_size_capability_unknown",
        ),
        (["1792x768"], "1792X768", "precision_target_size_invalid"),
    ],
)
def test_precision_resize_rejects_unknown_or_undeclared_size_before_task(monkeypatch, supported_sizes, target_size, reason):
    provider = _provider(supported_sizes=supported_sizes)
    process_calls = []

    async def forbidden_process(generation_id):
        process_calls.append(generation_id)
        raise AssertionError("unsupported precision resize must not create a task")

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(config=SimpleNamespace(providers=[provider]), get_image_providers=lambda: [provider]),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", forbidden_process)

    request = _precision_request(
        precision_size_mode="resize",
        precision_target_size=target_size,
        precision_resize_prompt="Extend the background sideways.",
    )
    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.generate(request, _route_request()))

    assert caught.value.status_code == 422
    if reason == "precision_target_size_invalid":
        assert caught.value.detail["code"] == reason
    else:
        assert caught.value.detail["code"] == "precision_edit_size_unsupported"
        assert caught.value.detail["providers"][0]["reason"] == reason
    assert process_calls == []


def test_precision_edit_allows_valid_request_with_explicitly_capable_mock_provider(monkeypatch):
    provider = _provider()
    observed = {}

    async def fake_process(generation_id):
        observed["generation_id"] = generation_id

    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=SimpleNamespace(providers=[provider]), get_image_providers=lambda: [provider]))
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)
    response = asyncio.run(main.generate(_precision_request(), _route_request()))
    generation_id = response["generation_id"]
    try:
        task = main.image_tasks[generation_id]
        assert task["mode"] == "precision_edit"
        assert task["kwargs"]["annotation_contract"] == "genbox-annotation-v1"
        assert task["kwargs"]["annotation_image_data"] == task["kwargs"]["image_data"]
        assert task["kwargs"]["annotations"][0]["type"] == "arrow"
        assert observed["generation_id"] == generation_id
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


@pytest.mark.parametrize("resize_only", [False, True])
def test_precision_route_accepts_canonical_only_alias_and_preserves_selected_model(monkeypatch, resize_only):
    provider = _provider(supported_sizes=None)
    provider.model = "channel-alias"
    provider.extra = {
        "model_capabilities": {
            "channel-alias": {"alias_of": "canonical-edit"},
            "canonical-edit": {"precision_edit": True, "supported_sizes": ["64x64"]},
        }
    }
    observed = {}

    async def fake_process(generation_id):
        observed["generation_id"] = generation_id

    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=SimpleNamespace(providers=[provider]), get_image_providers=lambda: [provider]))
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)
    source = _image_data(size=(64, 64))
    request = (
        _precision_resize_only_request(
            image_data=source,
            provider_settings={"precision-provider": {"model": "channel-alias"}},
        )
        if resize_only
        else _precision_request(
            image_data=source,
            annotation_image_data=source,
            provider_settings={"precision-provider": {"model": "channel-alias"}},
        )
    )

    response = asyncio.run(main.generate(request, _route_request()))
    generation_id = response["generation_id"]
    try:
        task = main.image_tasks[generation_id]
        assert task["provider_kwargs_map"]["precision-provider"]["model"] == "channel-alias"
        assert observed["generation_id"] == generation_id
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


def test_precision_model_refresh_preserves_user_confirmed_compatibility_mapping(monkeypatch):
    refreshed_model = "relay-defined-image-alias"
    canonical_capabilities = {
        "gpt-image-2": {
            "precision_edit": True,
            "supported_sizes": ["1024x1024"],
        }
    }
    provider = ProviderConfig(
        id="precision-provider",
        name="Precision Mock",
        type="image",
        api_key="test-key",
        base_url="https://provider.example.test/v1",
        model="gpt-image-2",
        models=["gpt-image-2", refreshed_model],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        precision_edit_profile=(
            PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
        ),
        extra={"model_capabilities": copy.deepcopy(canonical_capabilities)},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    process_calls = []

    async def fake_fetch_models(_provider):
        return [refreshed_model]

    async def fake_process(generation_id):
        process_calls.append(generation_id)

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=config,
            get_image_providers=lambda: [provider],
            save=lambda value: saved.append(value),
        ),
    )
    monkeypatch.setattr(main, "fetch_models_from_upstream", fake_fetch_models)
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)

    confirmation = asyncio.run(
        main.set_precision_capability(
            "precision-provider",
            main.PrecisionCapabilityReq(
                model=refreshed_model,
                enabled=True,
                confirmed=True,
                compatibility_profile="gpt-image-2",
            ),
        )
    )
    assert confirmation["compatibility_profile"] == "gpt-image-2"
    assert provider.extra["model_capabilities"][refreshed_model] == {"alias_of": "gpt-image-2"}
    assert provider.precision_edit_profile == (
        PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
    )

    refresh = asyncio.run(main.fetch_models("precision-provider"))
    assert refresh["models"] == [refreshed_model]
    assert provider.extra["model_capabilities"] == {
        **canonical_capabilities,
        refreshed_model: {"alias_of": "gpt-image-2"},
    }
    assert saved == [config, config]

    request = _precision_resize_only_request(
        image_data=_image_data(size=(1024, 1024)),
        precision_target_size="1024x1024",
        provider_settings={"precision-provider": {"model": refreshed_model}},
    )
    response = asyncio.run(main.generate(request, _route_request()))
    generation_id = response["generation_id"]
    try:
        task = main.image_tasks[generation_id]
        assert task["provider_kwargs_map"]["precision-provider"]["model"] == refreshed_model
        assert process_calls == [generation_id]
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


@pytest.mark.parametrize(
    "unconfirmed_model",
    ["custom-image-model", "gpt-image2-preview", "gpt-image2-c", "gpt-image2-d"],
)
def test_precision_model_refresh_does_not_authorize_unconfirmed_model_name(
    monkeypatch,
    unconfirmed_model,
):
    provider = ProviderConfig(
        id="precision-provider",
        name="Precision Mock",
        type="image",
        api_key="test-key",
        base_url="https://provider.example.test/v1",
        model="gpt-image-2",
        models=["gpt-image-2"],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={
            "model_capabilities": {
                "gpt-image-2": {"precision_edit": True, "supported_sizes": ["64x64"]},
            }
        },
    )
    config = SimpleNamespace(providers=[provider])
    process_calls = []

    async def fake_fetch_models(_provider):
        return [unconfirmed_model]

    async def fake_process(generation_id):
        process_calls.append(generation_id)

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(config=config, get_image_providers=lambda: [provider], save=lambda _value: None),
    )
    monkeypatch.setattr(main, "fetch_models_from_upstream", fake_fetch_models)
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)

    refresh = asyncio.run(main.fetch_models("precision-provider"))
    assert refresh.get("success") is True, refresh
    assert refresh["models"] == [unconfirmed_model]
    assert unconfirmed_model not in provider.extra["model_capabilities"]

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.generate(
                _precision_resize_only_request(
                    image_data=_image_data(size=(64, 64)),
                    provider_settings={"precision-provider": {"model": unconfirmed_model}},
                ),
                _route_request(),
            )
        )
    assert caught.value.detail["code"] == "precision_edit_provider_unsupported"
    assert process_calls == []


def test_precision_compatibility_confirmation_requires_consent_and_revoke_fails_closed(monkeypatch):
    alias = "any-upstream-model-name"
    provider = _provider(supported_sizes=None)
    provider.model = alias
    provider.models = [alias]
    provider.precision_edit_profile = None
    provider.extra = {
        "model_capabilities": {
            "gpt-image-2": {"precision_edit": True, "supported_sizes": ["64x64"]},
        }
    }
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(config=config, get_image_providers=lambda: [provider], save=lambda value: saved.append(value)),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.set_precision_capability(
                "precision-provider",
                main.PrecisionCapabilityReq(
                    model=alias,
                    enabled=True,
                    compatibility_profile="gpt-image-2",
                ),
            )
        )
    assert caught.value.detail["code"] == "precision_confirmation_required"
    assert saved == []
    assert alias not in provider.extra["model_capabilities"]

    asyncio.run(
        main.set_precision_capability(
            "precision-provider",
            main.PrecisionCapabilityReq(
                model=alias,
                enabled=True,
                confirmed=True,
                compatibility_profile="gpt-image-2",
            ),
        )
    )
    assert main._provider_precision_model_capability(provider, alias) is True
    assert provider.extra["model_capabilities"][alias] == {"alias_of": "gpt-image-2"}

    revoked = asyncio.run(
        main.set_precision_capability(
            "precision-provider",
            main.PrecisionCapabilityReq(model=alias, enabled=False, confirmed=True),
        )
    )
    assert revoked["enabled"] is False
    assert main._provider_precision_model_capability(provider, alias) is False
    assert provider.extra["model_capabilities"][alias] == {}
    assert provider.extra["model_capabilities"]["gpt-image-2"]["precision_edit"] is True

    with pytest.raises(HTTPException) as rejected:
        asyncio.run(
            main.generate(
                _precision_resize_only_request(
                    image_data=_image_data(size=(64, 64)),
                    provider_settings={"precision-provider": {"model": alias}},
                ),
                _route_request(),
            )
        )
    assert rejected.value.detail["code"] == "precision_edit_provider_unsupported"


@pytest.mark.parametrize(
    "records",
    [
        {
            "channel-alias": {"alias_of": "canonical-edit"},
            "canonical-edit": {"alias_of": "channel-alias", "precision_edit": True, "supported_sizes": ["64x64"]},
        },
        {
            "channel-alias": {"alias_of": "canonical-edit", "canonical_model": "other-edit"},
            "canonical-edit": {"precision_edit": True, "supported_sizes": ["64x64"]},
            "other-edit": {"precision_edit": True, "supported_sizes": ["64x64"]},
        },
    ],
)
def test_precision_route_rejects_alias_cycle_or_collision_before_task(monkeypatch, records):
    provider = _provider(supported_sizes=None)
    provider.model = "channel-alias"
    provider.extra = {"model_capabilities": records}
    process_calls = []

    async def forbidden_process(generation_id):
        process_calls.append(generation_id)

    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=SimpleNamespace(providers=[provider]), get_image_providers=lambda: [provider]))
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", forbidden_process)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.generate(
                _precision_resize_only_request(
                    image_data=_image_data(size=(64, 64)),
                    provider_settings={"precision-provider": {"model": "channel-alias"}},
                ),
                _route_request(),
            )
        )

    assert caught.value.detail["code"] == "precision_edit_provider_unsupported"
    assert process_calls == []


@pytest.mark.parametrize("alias_field", ["alias_of", "canonical_model"])
def test_precision_gpt_image_2_alias_rejects_illegal_declared_target_before_task(
    monkeypatch,
    alias_field,
):
    alias = "gpt-image2-b"
    provider = ProviderConfig(
        id="precision-provider",
        name="Precision Mock",
        type="image",
        api_key="test-key",
        base_url="https://provider.example.test/v1",
        model=alias,
        models=[alias],
        enabled=True,
        endpoint_type="openai",
        precision_edit_profile=(
            PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
        ),
        capabilities={"precision_edit": True},
        extra={
            "model_capabilities": {
                alias: {alias_field: "gpt-image-2"},
                "gpt-image-2": {
                    "precision_edit": True,
                    "supported_sizes": ["1792x768", "1920x1080"],
                },
            }
        },
    )
    process_calls = []

    async def forbidden_process(generation_id):
        process_calls.append(generation_id)

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[provider]),
            get_image_providers=lambda: [provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", forbidden_process)
    before_counter = main.generation_counter
    before_task_ids = set(main.image_tasks)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.generate(
                _precision_resize_only_request(
                    precision_target_size="1920x1080",
                    provider_settings={
                        "precision-provider": {"model": alias},
                    },
                ),
                _route_request(),
            )
        )

    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "precision_edit_size_unsupported"
    assert caught.value.detail["providers"] == [
        {
            "id": "precision-provider",
            "model": alias,
            "reason": "precision_target_size_alignment_invalid",
            "target_size": "1920x1080",
        }
    ]
    assert main.generation_counter == before_counter
    assert set(main.image_tasks) == before_task_ids
    assert process_calls == []


def test_precision_resize_only_creates_source_only_task_kwargs(monkeypatch):
    provider = _provider(supported_sizes=["64x64"])
    observed = {}

    async def fake_process(generation_id):
        observed["generation_id"] = generation_id

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[provider]),
            get_image_providers=lambda: [provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)

    response = asyncio.run(
        main.generate(
            _precision_resize_only_request(precision_output_size_policy="fit_crop"),
            _route_request(),
        )
    )
    generation_id = response["generation_id"]
    try:
        task = main.image_tasks[generation_id]
        assert task["mode"] == "precision_edit"
        assert task["kwargs"]["precision_canvas_only"] is True
        assert task["kwargs"]["precision_target_size"] == "64x64"
        assert task["kwargs"]["precision_output_size_policy"] == "fit_crop"
        assert "annotation_image_data" not in task["kwargs"]
        assert "annotation_contract" not in task["kwargs"]
        assert "annotations" not in task["kwargs"]
        assert observed["generation_id"] == generation_id
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


def test_precision_resize_only_task_uses_default_guidance_when_blank(monkeypatch):
    provider = _provider(supported_sizes=["64x64"])

    async def fake_process(_generation_id):
        return None

    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(
            config=SimpleNamespace(providers=[provider]),
            get_image_providers=lambda: [provider],
        ),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)
    monkeypatch.setattr(main, "_process_image_gen", fake_process)

    response = asyncio.run(
        main.generate(
            _precision_resize_only_request(precision_resize_prompt=""),
            _route_request(),
        )
    )
    generation_id = response["generation_id"]
    try:
        task = main.image_tasks[generation_id]
        assert (
            task["kwargs"]["precision_resize_prompt"]
            == main.DEFAULT_PRECISION_RESIZE_GUIDANCE
        )
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


def test_precision_task_queued_contract_preserves_zero_progress():
    payload = _read_precision_status(
        "precision-queued",
        _precision_status_task(
            "queued",
            {"precision-provider": _precision_provider_state()},
        ),
    )

    assert payload["status"] == "queued"
    assert payload["progress"] == 0
    assert payload["provider_states"]["precision-provider"]["status"] == "queued"
    assert payload["results"] == {}


def test_precision_task_partial_success_remains_in_progress_with_estimated_progress():
    states = {
        "precision-provider_0": _precision_provider_state("completed", 100, success=True),
        "precision-provider_1": _precision_provider_state("generating", 40),
    }
    successful_result = states["precision-provider_0"]["result"]
    task = _precision_status_task(
        "generating",
        states,
        {"precision-provider_0": successful_result},
    )
    task["group_timings"] = {
        "precision-provider": {
            "total": 1.0,
            "images": [{"seq": 0, "elapsed": 1.0, "success": True}],
        }
    }
    payload = _read_precision_status(
        "precision-partial",
        task,
    )

    assert payload["status"] == "generating"
    assert payload["progress"] == 70
    assert payload["provider_states"]["precision-provider_0"]["status"] == "completed"
    assert payload["provider_states"]["precision-provider_0"]["progress"] == 100
    assert payload["provider_states"]["precision-provider_0"]["result"] == successful_result
    assert payload["provider_states"]["precision-provider_1"]["status"] == "generating"
    assert payload["provider_states"]["precision-provider_1"]["progress"] == 40
    assert payload["results"] == {}
    assert payload["group_timings"] == {}


def test_precision_task_all_failed_is_failed_and_never_reaches_100():
    states = {
        "precision-provider_0": _precision_provider_state("failed", 10, success=False),
        "precision-provider_1": _precision_provider_state("failed", 90, success=False),
    }
    results = {key: state["result"] for key, state in states.items()}
    payload = _read_precision_status(
        "precision-all-failed",
        _precision_status_task("generating", states, results),
    )

    assert payload["status"] == "failed"
    assert payload["progress"] == 50
    assert payload["progress"] < 100
    assert all(state["progress"] < 100 for state in payload["provider_states"].values())
    assert payload["results"] == results


def test_precision_task_mixed_success_and_failure_is_completed_with_partial_results():
    states = {
        "precision-provider_0": _precision_provider_state("completed", 100, success=True),
        "precision-provider_1": _precision_provider_state("failed", 30, success=False),
    }
    results = {key: state["result"] for key, state in states.items()}
    payload = _read_precision_status(
        "precision-mixed",
        _precision_status_task("generating", states, results),
    )

    assert payload["status"] == "completed"
    assert payload["progress"] == 65
    assert payload["provider_states"]["precision-provider_0"]["progress"] == 100
    assert payload["provider_states"]["precision-provider_1"]["progress"] < 100
    assert payload["results"] == results


@pytest.mark.parametrize(
    ("case", "task_status", "child_specs", "expected_status", "expected_progress", "expected_counts"),
    [
        ("completed-cancelled", "generating", [("completed", 100, True), ("cancelled", 100, None)], "cancelled", 99, (1, 0, 1)),
        ("completed-failed", "generating", [("completed", 100, True), ("failed", 100, False)], "completed", 100, (1, 1, 0)),
        ("all-failed", "generating", [("failed", 100, False), ("failed", 100, False)], "failed", 99, (0, 2, 0)),
        ("all-cancelled", "generating", [("cancelled", 100, None), ("cancelled", 100, None)], "cancelled", 99, (0, 0, 2)),
        ("partial-success", "generating", [("completed", 100, True), ("failed", 40, False)], "completed", 70, (1, 1, 0)),
    ],
)
def test_precision_task_terminal_status_matrix_is_consistent(
    case, task_status, child_specs, expected_status, expected_progress, expected_counts
):
    states = {
        f"precision-provider_{index}": _precision_provider_state(status, progress, success=success)
        for index, (status, progress, success) in enumerate(child_specs)
    }
    results = {key: state["result"] for key, state in states.items() if state["result"] is not None}

    payload = _read_precision_status(
        f"precision-terminal-matrix-{case}",
        _precision_status_task(task_status, states, results),
    )

    status_counts = tuple(
        sum(state["status"] == status for state in payload["provider_states"].values())
        for status in ("completed", "failed", "cancelled")
    )
    assert payload["status"] == expected_status
    assert payload["progress"] == expected_progress
    assert status_counts == expected_counts
    if expected_status in ("failed", "cancelled"):
        assert payload["progress"] < 100
    else:
        assert payload["progress"] <= 100
    assert payload["results"] == results
    expected_group_timings = {}
    for result in results.values():
        group = expected_group_timings.setdefault(result["model"], {"total": 0.0, "images": []})
        group["images"].append(
            {
                "seq": result["seq"],
                "elapsed": result["elapsed_seconds"],
                "success": result["success"],
            }
        )
        group["total"] = round(sum(item["elapsed"] for item in group["images"]), 1)
    assert payload["group_timings"] == expected_group_timings


@pytest.mark.parametrize(
    ("gen_id", "task_status", "child_status", "child_progress"),
    [
        ("precision-cancel-queued", "queued", "queued", 0),
        ("precision-cancel-running", "generating", "generating", 47),
    ],
)
def test_precision_task_queued_and_running_cancel_never_reach_100(
    gen_id, task_status, child_status, child_progress
):
    states = {
        "precision-provider": _precision_provider_state(child_status, child_progress),
    }
    main.image_tasks[gen_id] = _precision_status_task(task_status, states)
    main.image_task_handles.pop(gen_id, None)
    try:
        cancelled = asyncio.run(main.cancel_generate(gen_id))
        payload = asyncio.run(main.get_generate_status(gen_id))

        assert cancelled == {"ok": True, "status": "cancelled"}
        assert payload["status"] == "cancelled"
        assert payload["progress"] == child_progress
        assert payload["progress"] < 100
        assert payload["provider_states"]["precision-provider"]["status"] == "cancelled"
        assert payload["provider_states"]["precision-provider"]["progress"] < 100
    finally:
        main.image_tasks.pop(gen_id, None)
        main.image_task_handles.pop(gen_id, None)


@pytest.mark.parametrize("failure_mode", ["result", "exception"])
def test_precision_provider_failure_and_exception_preserve_incomplete_progress(monkeypatch, failure_mode):
    import providers

    async def scenario():
        gen_id = f"precision-runtime-failure-{failure_mode}"

        async def fail_provider(_provider_config, _prompt, **_kwargs):
            if failure_mode == "exception":
                raise RuntimeError("synthetic provider exception")
            return SimpleNamespace(
                success=False,
                local_path=None,
                generation_id=None,
                error="synthetic provider failure",
            )

        monkeypatch.setattr(providers, "generate_for_provider", fail_provider)
        monkeypatch.setattr(main, "_write_log", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(main, "_save_history_entry", lambda *_args, **_kwargs: None)
        provider = _provider()
        state = _precision_provider_state()
        main.image_tasks[gen_id] = {
            **_precision_status_task("queued", {"precision-provider": state}),
            "mode": "precision_edit",
            "prompt": "Edit the marked region.",
            "providers": ["precision-provider"],
            "task_list": [("precision-provider", 0, 1)],
            "all_providers": {"precision-provider": provider},
            "kwargs": {},
            "provider_kwargs_map": {"precision-provider": {}},
            "continuous": False,
            "original_prompt": "Edit the marked region.",
            "upscale_to": None,
        }
        try:
            await main._process_image_gen(gen_id)
            payload = await main.get_generate_status(gen_id)

            assert payload["status"] == "failed"
            assert payload["progress"] == 10
            assert payload["progress"] < 100
            assert state["status"] == "failed"
            assert state["progress"] == 10
        finally:
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)
            main.generation_history.pop(gen_id, None)


def test_precision_fit_crop_metadata_and_warning_reach_status_log(monkeypatch):
    import providers

    async def scenario():
        gen_id = "precision-fit-crop-status"
        metadata = {
            "requested_size": "1536x864",
            "provider_actual_size": "1376x768",
            "final_size": "1536x864",
            "policy": "fit_crop",
            "aspect_ratio_delta": 0.0078125,
            "transform": {"operation": "center_cover_crop"},
        }
        warning = {
            "code": "precision_edit_output_fit_crop_applied",
            "message": "Provider output 1376x768 was locally fit-cropped to requested size 1536x864.",
        }

        async def succeed_provider(_provider_config, _prompt, **_kwargs):
            return providers.ImageResult(
                success=True,
                local_path="gallery/result.png",
                generation_id="provider-result",
                metadata=metadata,
                warnings=[warning],
            )

        monkeypatch.setattr(providers, "generate_for_provider", succeed_provider)
        monkeypatch.setattr(main, "_write_log", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(main, "_save_history_entry", lambda *_args, **_kwargs: None)
        provider = _provider()
        state = _precision_provider_state()
        main.image_tasks[gen_id] = {
            **_precision_status_task("queued", {"precision-provider": state}),
            "mode": "precision_edit",
            "prompt": "Expand the canvas.",
            "providers": ["precision-provider"],
            "task_list": [("precision-provider", 0, 1)],
            "all_providers": {"precision-provider": provider},
            "kwargs": {},
            "provider_kwargs_map": {"precision-provider": {}},
            "continuous": False,
            "original_prompt": "Expand the canvas.",
            "upscale_to": None,
        }
        try:
            await main._process_image_gen(gen_id)
            payload = await main.get_generate_status(gen_id)
            result = payload["results"]["precision-provider"]

            assert payload["status"] == "completed"
            assert result["metadata"] == metadata
            assert result["warnings"] == [warning]
            assert any(
                "precision_edit_output_fit_crop_applied" in entry
                for entry in payload["provider_states"]["precision-provider"]["log"]
            )
        finally:
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)
            main.generation_history.pop(gen_id, None)

    asyncio.run(scenario())


def test_precision_size_mismatch_details_reach_failed_status(monkeypatch):
    import providers

    async def scenario():
        gen_id = "precision-size-mismatch-status"
        details = {
            "requested_size": "1536x864",
            "actual_size": "1024x768",
            "aspect_ratio_delta": 0.25,
            "allowed_policies": ["strict", "fit_crop"],
        }

        async def fail_provider(_provider_config, _prompt, **_kwargs):
            return providers.ImageResult(
                success=False,
                error="precision_edit_output_size_mismatch: synthetic mismatch",
                error_code="precision_edit_output_size_mismatch",
                error_details=details,
            )

        monkeypatch.setattr(providers, "generate_for_provider", fail_provider)
        monkeypatch.setattr(main, "_write_log", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(main, "_save_history_entry", lambda *_args, **_kwargs: None)
        provider = _provider()
        state = _precision_provider_state()
        main.image_tasks[gen_id] = {
            **_precision_status_task("queued", {"precision-provider": state}),
            "mode": "precision_edit",
            "prompt": "Expand the canvas.",
            "providers": ["precision-provider"],
            "task_list": [("precision-provider", 0, 1)],
            "all_providers": {"precision-provider": provider},
            "kwargs": {},
            "provider_kwargs_map": {"precision-provider": {}},
            "continuous": False,
            "original_prompt": "Expand the canvas.",
            "upscale_to": None,
        }
        try:
            await main._process_image_gen(gen_id)
            payload = await main.get_generate_status(gen_id)
            result = payload["results"]["precision-provider"]

            assert payload["status"] == "failed"
            assert result["error_code"] == "precision_edit_output_size_mismatch"
            assert result["error_details"] == details
            assert result["metadata"] is None
            assert result["warnings"] == []
        finally:
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)
            main.generation_history.pop(gen_id, None)

    asyncio.run(scenario())

    asyncio.run(scenario())


def test_precision_capability_requires_confirmation_and_persists_model_grant(monkeypatch):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="edit-1",
        models=["edit-1"],
        enabled=True,
        endpoint_type="openai",
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.set_precision_capability("custom", main.PrecisionCapabilityReq(model="edit-1", enabled=True)))
    assert caught.value.detail["code"] == "precision_confirmation_required"
    result = asyncio.run(main.set_precision_capability("custom", main.PrecisionCapabilityReq(model="edit-1", enabled=True, confirmed=True)))
    assert result["enabled"] is True
    assert provider.endpoint_type == "openai"
    assert provider.precision_edit_profile == (
        PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE
    )
    assert provider.capabilities["precision_edit"] is True
    assert provider.extra["model_capabilities"]["edit-1"]["precision_edit"] is True
    assert saved == [config]


def test_precision_capability_confirms_and_revokes_model_size_without_leaking_secrets(monkeypatch):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="sk-test-secret",
        base_url="https://secret.example.test/v1",
        model="edit-1",
        models=["edit-1"],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"edit-1": {"precision_edit": True, "supported_sizes": ["1024x1024"]}}},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    result = asyncio.run(
        main.set_precision_capability(
            "custom",
            main.PrecisionCapabilityReq(
                model="edit-1",
                enabled=True,
                confirmed=True,
                size="1792x768",
            ),
        )
    )

    assert result == {
        "ok": True,
        "provider_id": "custom",
        "model": "edit-1",
        "enabled": True,
        "size": "1792x768",
        "supported_sizes": ["1024x1024", "1792x768"],
    }
    assert provider.extra["model_capabilities"]["edit-1"]["supported_sizes"] == ["1024x1024", "1792x768"]
    response_text = repr(result)
    assert "sk-test-secret" not in response_text
    assert "secret.example.test" not in response_text

    duplicate = asyncio.run(
        main.set_precision_capability(
            "custom",
            main.PrecisionCapabilityReq(
                model="edit-1",
                enabled=True,
                confirmed=True,
                size="1792x768",
            ),
        )
    )
    assert duplicate["supported_sizes"] == ["1024x1024", "1792x768"]

    revoked = asyncio.run(
        main.set_precision_capability(
            "custom",
            main.PrecisionCapabilityReq(
                model="edit-1",
                enabled=False,
                confirmed=True,
                size="1792x768",
            ),
        )
    )
    assert revoked["supported_sizes"] == ["1024x1024"]
    assert provider.extra["model_capabilities"]["edit-1"]["precision_edit"] is True
    assert saved == [config, config, config]


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "63x1024"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "8193x1024"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "8192x8193"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "not-a-size"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "01024x1024"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "64x64 "}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "1792X768"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "1e3x768"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "1024.5x768"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "1792-768"}, "precision_size_invalid"),
        ({"model": "edit-1", "enabled": True, "confirmed": True, "size": "1024x1024", "base_url": "https://evil.example"}, "validation_error"),
    ],
)
def test_precision_size_capability_rejects_invalid_size_and_unknown_fields(monkeypatch, payload, code):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="edit-1",
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"edit-1": {"precision_edit": True}}},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    if code == "validation_error":
        with pytest.raises(ValidationError):
            main.PrecisionCapabilityReq(**payload)
    else:
        with pytest.raises(HTTPException) as caught:
            asyncio.run(main.set_precision_capability("custom", main.PrecisionCapabilityReq(**payload)))
        assert caught.value.status_code == 400
        assert caught.value.detail["code"] == code
    assert saved == []


@pytest.mark.parametrize(
    ("provider_kwargs", "model_extra", "code"),
    [
        ({"enabled": False}, {"precision_edit": True}, "precision_provider_not_enabled"),
        ({"type": "llm"}, {"precision_edit": True}, "precision_provider_not_image"),
        ({"api_key": ""}, {"precision_edit": True}, "precision_provider_key_required"),
        ({"endpoint_type": "auto"}, {"precision_edit": True}, "precision_provider_openai_required"),
        ({}, {"precision_edit": False}, "precision_model_precision_edit_required"),
    ],
)
def test_precision_size_capability_requires_authorized_openai_image_model(monkeypatch, provider_kwargs, model_extra, code):
    values = {
        "id": "custom",
        "name": "Custom",
        "type": "image",
        "api_key": "test-key",
        "model": "edit-1",
        "enabled": True,
        "endpoint_type": "openai",
        "capabilities": {"precision_edit": True},
        "extra": {"model_capabilities": {"edit-1": model_extra}},
    }
    values.update(provider_kwargs)
    provider = ProviderConfig(**values)
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.set_precision_capability(
                "custom",
                main.PrecisionCapabilityReq(
                    model="edit-1",
                    enabled=True,
                    confirmed=True,
                    size="1024x1024",
                ),
            )
        )

    assert caught.value.status_code == 400
    assert caught.value.detail["code"] == code
    error_text = repr(caught.value.detail)
    assert "test-key" not in error_text
    assert "base_url" not in error_text
    assert saved == []


def test_precision_size_capability_rejects_full_supported_size_array(monkeypatch):
    existing_sizes = [f"{64 + index}x1024" for index in range(main.MAX_PRECISION_SUPPORTED_SIZES)]
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="edit-1",
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"edit-1": {"precision_edit": True, "supported_sizes": existing_sizes}}},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.set_precision_capability(
                "custom",
                main.PrecisionCapabilityReq(
                    model="edit-1",
                    enabled=True,
                    confirmed=True,
                    size="4096x4096",
                ),
            )
        )

    assert caught.value.status_code == 400
    assert caught.value.detail["code"] == "precision_size_limit_exceeded"
    assert saved == []


def test_precision_size_capability_requires_model_from_provider(monkeypatch):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="edit-1",
        models=["edit-1"],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"edit-1": {"precision_edit": True}}},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.set_precision_capability(
                "custom",
                main.PrecisionCapabilityReq(
                    model="display-alias",
                    enabled=True,
                    confirmed=True,
                    size="1024x1024",
                ),
            )
        )

    assert caught.value.status_code == 400
    assert caught.value.detail["code"] == "precision_model_invalid"
    assert saved == []


def test_precision_capability_route_rejects_unknown_fields_without_body_echo(monkeypatch):
    monkeypatch.setattr(main, "is_prod_mode", lambda: False)
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="edit-1",
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"edit-1": {"precision_edit": True}}},
    )
    config = SimpleNamespace(providers=[provider])
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: None))

    response = TestClient(main.app).post(
        "/api/providers/custom/precision-capability",
        json={
            "model": "edit-1",
            "enabled": True,
            "confirmed": True,
            "size": "1024x1024",
            "api_key": "sk-route-secret",
        },
    )

    assert response.status_code == 422
    response_text = response.text
    assert "sk-route-secret" not in response_text
    assert "test-key" not in response_text


@pytest.mark.parametrize("size", ["01024x1024", "64x64 "])
def test_precision_capability_route_rejects_noncanonical_size_without_persisting(monkeypatch, size):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="edit-1",
        models=["edit-1"],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"edit-1": {"precision_edit": True, "supported_sizes": ["1024x1024"]}}},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    before_extra = copy.deepcopy(provider.extra)
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    response = TestClient(main.app).post(
        "/api/providers/custom/precision-capability",
        json={"model": "edit-1", "enabled": True, "confirmed": True, "size": size},
    )

    assert response.status_code >= 400
    assert response.json()["detail"]["code"] == "precision_size_invalid"
    assert saved == []
    assert provider.extra == before_extra


def test_precision_capability_route_accepts_canonical_size(monkeypatch):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="edit-1",
        models=["edit-1"],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"edit-1": {"precision_edit": True, "supported_sizes": ["1024x1024"]}}},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    response = TestClient(main.app).post(
        "/api/providers/custom/precision-capability",
        json={"model": "edit-1", "enabled": True, "confirmed": True, "size": "1792x768"},
    )

    assert response.status_code == 200
    assert response.json()["supported_sizes"] == ["1024x1024", "1792x768"]
    assert provider.extra["model_capabilities"]["edit-1"]["supported_sizes"] == ["1024x1024", "1792x768"]
    assert saved == [config]


@pytest.mark.parametrize(
    ("model", "model_capabilities"),
    [
        (
            "gpt-image-2",
            {
                "gpt-image-2": {
                    "precision_edit": True,
                    "supported_sizes": ["1024x1024"],
                }
            },
        ),
        (
            "relay-gpt-image-2",
            {
                "relay-gpt-image-2": {"alias_of": "gpt-image-2"},
                "gpt-image-2": {
                    "precision_edit": True,
                    "supported_sizes": ["1024x1024"],
                },
            },
        ),
    ],
)
def test_precision_capability_route_rejects_strict_gpt_image_2_size_without_persisting(
    monkeypatch, model, model_capabilities
):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model=model,
        models=[model],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": model_capabilities},
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    before_extra = copy.deepcopy(provider.extra)
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            main.set_precision_capability(
                "custom",
                main.PrecisionCapabilityReq(
                    model=model,
                    enabled=True,
                    confirmed=True,
                    size="1920x1080",
                ),
            )
        )

    assert caught.value.status_code == 400
    assert caught.value.detail["code"] == "precision_size_invalid"
    assert caught.value.detail["reason_code"] == "precision_target_size_alignment_invalid"
    assert saved == []
    assert provider.extra == before_extra


def test_precision_capability_route_accepts_legal_gpt_image_2_size(monkeypatch):
    provider = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        api_key="test-key",
        model="gpt-image-2",
        models=["gpt-image-2"],
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={
            "model_capabilities": {
                "gpt-image-2": {
                    "precision_edit": True,
                    "supported_sizes": ["1024x1024"],
                }
            }
        },
    )
    config = SimpleNamespace(providers=[provider])
    saved = []
    monkeypatch.setattr(main, "cfg_mgr", SimpleNamespace(config=config, save=lambda value: saved.append(value)))

    result = asyncio.run(
        main.set_precision_capability(
            "custom",
            main.PrecisionCapabilityReq(
                model="gpt-image-2",
                enabled=True,
                confirmed=True,
                size="2048x1152",
            ),
        )
    )

    assert result["supported_sizes"] == ["1024x1024", "2048x1152"]
    assert provider.extra["model_capabilities"]["gpt-image-2"]["supported_sizes"] == [
        "1024x1024",
        "2048x1152",
    ]
    assert saved == [config]


def test_precision_resize_generation_uses_size_confirmed_through_capability_api(monkeypatch):
    provider = ProviderConfig(
        id="precision-provider",
        name="Precision Mock",
        type="image",
        api_key="test-key",
        model="mock-edit-1",
        enabled=True,
        endpoint_type="openai",
        capabilities={"precision_edit": True},
        extra={"model_capabilities": {"mock-edit-1": {"precision_edit": True}}},
    )
    config = SimpleNamespace(providers=[provider])
    monkeypatch.setattr(
        main,
        "cfg_mgr",
        SimpleNamespace(config=config, get_image_providers=lambda: [provider], save=lambda value: None),
    )
    monkeypatch.setattr(main, "_check_rate_limit", lambda *_args: True)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(main.generate(_precision_resize_only_request(), _route_request()))
    assert caught.value.detail["code"] == "precision_edit_size_unsupported"

    asyncio.run(
        main.set_precision_capability(
            "precision-provider",
            main.PrecisionCapabilityReq(
                model="mock-edit-1",
                enabled=True,
                confirmed=True,
                size="64x64",
            ),
        )
    )

    observed = {}

    async def fake_process(generation_id):
        observed["generation_id"] = generation_id

    monkeypatch.setattr(main, "_process_image_gen", fake_process)
    response = asyncio.run(main.generate(_precision_resize_only_request(), _route_request()))
    generation_id = response["generation_id"]
    try:
        task = main.image_tasks[generation_id]
        assert task["kwargs"]["precision_target_size"] == "64x64"
        assert "annotation_image_data" not in task["kwargs"]
        assert observed["generation_id"] == generation_id
    finally:
        main.image_tasks.pop(generation_id, None)
        main.image_task_handles.pop(generation_id, None)


@pytest.mark.parametrize(
    "profile",
    [
        PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_IMAGE_ARRAY,
        PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE,
    ],
)
def test_provider_update_without_profile_preserves_explicit_profile(profile):
    model_capabilities = {
        "relay-model": {"alias_of": "gpt-image-2"},
        "gpt-image-2": {"precision_edit": True, "supported_sizes": ["64x64"]},
    }
    existing = ProviderConfig(
        id="custom",
        name="Custom",
        type="image",
        precision_edit_profile=profile,
        extra={"model_capabilities": model_capabilities},
    )
    request = main.ProviderCreateReq(id="custom", name="Custom", type="image", extra={})

    payload = main._merge_provider_secrets(existing, request)

    assert payload["precision_edit_profile"] == profile
    assert payload["extra"]["model_capabilities"] == model_capabilities


def test_cutout_capabilities_fail_closed_without_adapters(monkeypatch):
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", CutoutAdapterRegistry())
    client = TestClient(main.app, base_url="http://testserver")
    response = client.get("/api/image-tools/cutout/capabilities")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "cutout_adapter_unavailable"
    assert detail["contract"] == "genbox-cutout-v1"
    assert detail["available"] is False
    assert detail["adapters"] == []


def test_cutout_capabilities_refreshes_imported_optional_modnet(monkeypatch):
    refreshed = []

    class _ImportedModNet:
        def status(self):
            return {"installed": True, "valid": True}

    class _Registry:
        def probe(self):
            return {
                "contract": "genbox-cutout-v1",
                "available": True,
                "executable": True,
                "adapters": ["u2net-human-seg-onnx", "modnet-portrait-onnx"],
                "adapter_capabilities": [],
                "state": "ready",
            }

    monkeypatch.setattr(main, "MODNET_IMPORT_MANAGER", _ImportedModNet())
    monkeypatch.setattr(main, "_refresh_modnet_registry", lambda manager: refreshed.append(manager))
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", _Registry())
    client = TestClient(main.app, base_url="http://testserver")

    response = client.get("/api/image-tools/cutout/capabilities")

    assert response.status_code == 200
    assert refreshed and refreshed[0].__class__ is _ImportedModNet
    assert response.json()["adapters"] == ["u2net-human-seg-onnx", "modnet-portrait-onnx"]


def test_cutout_submission_fails_closed_without_adapters(monkeypatch):
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", CutoutAdapterRegistry())
    client = TestClient(main.app, base_url="http://testserver")
    response = client.post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={"contract": "genbox-cutout-v1", "image_data": _image_data()},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "cutout_adapter_unavailable"
    assert detail["available"] is False
    assert detail["adapters"] == []


def test_cutout_submission_fails_closed_before_image_validation_without_adapters(monkeypatch):
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", CutoutAdapterRegistry())
    client = TestClient(main.app, base_url="http://testserver")
    response = client.post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={"contract": "genbox-cutout-v1", "image_data": "not-an-image"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "cutout_adapter_unavailable"


def test_cutout_rejects_unknown_contract_before_adapter_check():
    client = TestClient(main.app, base_url="http://testserver")
    response = client.post(
        "/api/image-tools/cutout",
        headers={"Origin": "http://testserver"},
        json={"contract": "genbox-cutout-v9", "image_data": _image_data()},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "cutout_contract_unsupported"


def test_gallery_image_route_uses_payload_mime_for_legacy_jpeg_with_png_suffix(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    image_bytes = _image_bytes(image_format="JPEG")
    (tmp_path / "legacy.png").write_bytes(image_bytes)

    response = TestClient(main.app, base_url="http://testserver").get(
        "/api/gallery/image/legacy.png"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == image_bytes


@pytest.mark.parametrize(
    "route",
    [
        "/api/gallery/image/legacy.png",
        "/api/gallery/thumb/legacy.png",
    ],
)
def test_gallery_memory_routes_support_single_byte_ranges_with_sniffed_mime(
    monkeypatch,
    tmp_path,
    route,
):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    image_bytes = _image_bytes(image_format="JPEG")
    image_path = tmp_path / "legacy.png"
    image_path.write_bytes(image_bytes)
    total = len(image_bytes)
    client = TestClient(main.app, base_url="http://testserver")

    full = client.get(route)
    assert full.status_code == 200
    assert full.headers["content-type"] == "image/jpeg"
    assert full.headers["accept-ranges"] == "bytes"
    assert full.headers["content-length"] == str(total)
    assert full.content == image_bytes

    range_cases = [
        ("bytes=2-5", 2, 5),
        ("bytes=7-", 7, total - 1),
        ("bytes=-6", total - 6, total - 1),
    ]
    for range_header, start, end in range_cases:
        response = client.get(route, headers={"Range": range_header})
        assert response.status_code == 206
        assert response.headers["content-type"] == "image/jpeg"
        assert response.headers["accept-ranges"] == "bytes"
        assert response.headers["content-range"] == f"bytes {start}-{end}/{total}"
        assert response.headers["content-length"] == str(end - start + 1)
        assert response.content == image_bytes[start : end + 1]

    multiple = client.get(route, headers={"Range": "bytes=0-1,4-5"})
    assert multiple.status_code == 200
    assert multiple.headers["content-type"] == "image/jpeg"
    assert multiple.headers["accept-ranges"] == "bytes"
    assert "content-range" not in multiple.headers
    assert multiple.headers["content-length"] == str(total)
    assert multiple.content == image_bytes

    mixed_satisfiability = client.get(
        route,
        headers={"Range": f"bytes=0-1,{total}-"},
    )
    assert mixed_satisfiability.status_code == 200
    assert mixed_satisfiability.headers["content-type"] == "image/jpeg"
    assert mixed_satisfiability.headers["accept-ranges"] == "bytes"
    assert "content-range" not in mixed_satisfiability.headers
    assert mixed_satisfiability.headers["content-length"] == str(total)
    assert mixed_satisfiability.content == image_bytes

    for range_header in (
        "bytes=8-3",
        f"bytes={total}-",
        f"bytes={total}-{total + 1},{total + 2}-",
        "items=0-1",
    ):
        response = client.get(route, headers={"Range": range_header})
        assert response.status_code == 416
        assert response.headers["accept-ranges"] == "bytes"
        assert response.headers["content-range"] == f"bytes */{total}"
        assert response.headers["content-length"] == "0"
        assert response.content == b""
        assert str(image_path) not in response.text
        assert str(tmp_path) not in response.text


@pytest.mark.parametrize(
    "route",
    [
        "/api/gallery/image/legacy.png",
        "/api/gallery/thumb/legacy.png",
    ],
)
@pytest.mark.parametrize(
    "range_header",
    [
        pytest.param(f"bytes={'9' * 5000}-{'9' * 5000}", id="closed"),
        pytest.param(f"bytes={'9' * 5000}-", id="open"),
        pytest.param(f"bytes=-{'9' * 5000}", id="suffix"),
    ],
)
def test_gallery_memory_routes_reject_oversized_range_numbers(
    monkeypatch,
    tmp_path,
    route,
    range_header,
):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    image_bytes = _image_bytes(image_format="JPEG")
    image_path = tmp_path / "legacy.png"
    image_path.write_bytes(image_bytes)
    total = len(image_bytes)

    response = TestClient(main.app, base_url="http://testserver").get(
        route,
        headers={"Range": range_header},
    )

    assert response.status_code == 416
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == f"bytes */{total}"
    assert response.headers["content-length"] == "0"
    assert response.content == b""
    assert str(image_path) not in response.text
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize(
    "route",
    [
        "/api/gallery/image/legacy.png",
        "/api/gallery/thumb/legacy.png",
    ],
)
@pytest.mark.parametrize(
    "range_header",
    [
        "bytes=0-1,garbage",
        "bytes=,",
        "bytes=0-1,",
        "bytes=,0-1",
        "bytes=0-1,8-3",
        f"bytes=0-1,-{'9' * 21}",
    ],
)
def test_gallery_memory_routes_reject_malformed_multiple_ranges(
    monkeypatch,
    tmp_path,
    route,
    range_header,
):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    image_bytes = _image_bytes(image_format="JPEG")
    image_path = tmp_path / "legacy.png"
    image_path.write_bytes(image_bytes)
    total = len(image_bytes)

    response = TestClient(main.app, base_url="http://testserver").get(
        route,
        headers={"Range": range_header},
    )

    assert response.status_code == 416
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == f"bytes */{total}"
    assert response.headers["content-length"] == "0"
    assert response.content == b""
    assert str(image_path) not in response.text
    assert str(tmp_path) not in response.text


def test_gallery_base64_uses_payload_mime_and_passes_precision_validation(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    image_bytes = _image_bytes(image_format="JPEG")
    (tmp_path / "legacy.png").write_bytes(image_bytes)
    client = TestClient(main.app, base_url="http://testserver")

    response = client.get("/api/gallery/image/legacy.png/base64")

    assert response.status_code == 200
    image_data = response.json()["data"]
    header, encoded = image_data.split(",", 1)
    assert header == "data:image/jpeg;base64"
    assert base64.b64decode(encoded, validate=True) == image_bytes
    validated = main._validate_generation_request_inputs(
        _precision_request(
            prompt="",
            image_data=image_data,
            annotation_image_data=_image_data(),
        )
    )
    assert validated["images"][0]["mime_type"] == "image/jpeg"
    assert validated["annotation_image"]["mime_type"] == "image/png"


def test_preview_images_uses_payload_mime_for_legacy_jpeg_with_png_suffix(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    image_bytes = _image_bytes(image_format="JPEG")
    (tmp_path / "legacy.png").write_bytes(image_bytes)

    response = TestClient(main.app, base_url="http://testserver").get(
        "/api/preview/images"
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    header, encoded = response.json()["items"][0]["data"].split(",", 1)
    assert header == "data:image/jpeg;base64"
    assert base64.b64decode(encoded, validate=True) == image_bytes


@pytest.mark.parametrize(
    ("payload", "error_code"),
    [
        (b"not-an-image", "gallery_image_invalid"),
        (_image_bytes(image_format="GIF"), "gallery_image_mime_unsupported"),
    ],
)
def test_gallery_routes_fail_closed_for_invalid_or_unsupported_payloads(
    monkeypatch,
    tmp_path,
    payload,
    error_code,
):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    image_path = tmp_path / "legacy.png"
    image_path.write_bytes(payload)
    client = TestClient(main.app, base_url="http://testserver")

    for route in (
        "/api/gallery/image/legacy.png",
        "/api/gallery/image/legacy.png/base64",
    ):
        response = client.get(route)
        assert response.status_code == 415
        assert response.json()["detail"]["code"] == error_code
        assert str(image_path) not in response.text
        assert "not-an-image" not in response.text

    preview = client.get("/api/preview/images")
    assert preview.status_code == 200
    assert preview.json()["items"] == []
    assert str(image_path) not in preview.text


@pytest.mark.parametrize(
    "filename",
    [
        "../outside.png",
        r"..\outside.png",
        "/outside.png",
        r"C:\outside.png",
        "nested/outside.png",
        r"nested\outside.png",
        "%2e%2e%5coutside.png",
        "outside.png:stream",
        "outside.jpg",
        "",
        ".",
        "..",
    ],
)
def test_gallery_filename_resolution_rejects_non_child_paths(monkeypatch, tmp_path, filename):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)

    with pytest.raises(HTTPException) as caught:
        main._resolve_gallery_file(filename)

    assert caught.value.status_code == 404
    assert str(tmp_path.parent) not in str(caught.value.detail)


@pytest.mark.parametrize(
    "route",
    [
        "/api/gallery/image/..%5Coutside.png",
        "/api/gallery/image/..%5Coutside.png/base64",
    ],
)
def test_gallery_routes_reject_url_decoded_windows_traversal_without_path_leak(
    monkeypatch,
    tmp_path,
    route,
):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(_image_bytes(image_format="JPEG"))

    response = TestClient(main.app, base_url="http://testserver").get(route)

    assert response.status_code in {400, 404}
    assert str(outside) not in response.text
    assert str(tmp_path.parent) not in response.text


def test_gallery_routes_offload_one_payload_read_per_file(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    (tmp_path / "legacy.png").write_bytes(_image_bytes(image_format="JPEG"))
    calls = []
    real_loader = main._load_gallery_image_payload

    async def record_to_thread(function, *args, **kwargs):
        calls.append((function, args))
        return function(*args, **kwargs)

    monkeypatch.setattr(main.asyncio, "to_thread", record_to_thread)
    client = TestClient(main.app, base_url="http://testserver")

    for route in (
        "/api/gallery/image/legacy.png",
        "/api/gallery/image/legacy.png/base64",
        "/api/preview/images",
    ):
        before = len(calls)
        response = client.get(route)
        assert response.status_code == 200
        assert len(calls) == before + 1
        assert calls[-1][0] is real_loader


def test_preview_images_rejects_files_outside_gallery_confinement(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "GALLERY_DIR", tmp_path)
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(_image_bytes())
    link = tmp_path / "linked.png"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows environment")

    response = TestClient(main.app, base_url="http://testserver").get("/api/preview/images")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert str(outside) not in response.text


def _configure_media_roots(monkeypatch, tmp_path):
    gallery = tmp_path / "gallery"
    videos = tmp_path / "videos"
    thumbs = tmp_path / "video_thumbs"
    gallery.mkdir()
    videos.mkdir()
    thumbs.mkdir()
    monkeypatch.setattr(main, "GALLERY_DIR", gallery)
    monkeypatch.setattr(main, "VIDEO_DIR", videos)
    monkeypatch.setattr(main, "VIDEO_THUMBS_DIR", thumbs)
    return gallery, videos, thumbs


@pytest.mark.parametrize(
    ("route", "outside_name"),
    [
        ("/api/gallery/thumb/..%5Coutside.png", "outside.png"),
        ("/api/video/file/..%5Coutside.mp4", "outside.mp4"),
    ],
)
def test_media_routes_reject_existing_windows_traversal_without_path_leak(
    monkeypatch,
    tmp_path,
    route,
    outside_name,
):
    _configure_media_roots(monkeypatch, tmp_path)
    outside = tmp_path / outside_name
    outside.write_bytes(b"outside-media")

    response = TestClient(main.app, base_url="http://testserver").get(route)

    assert response.status_code == 404
    assert str(outside) not in response.text
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize(
    "route",
    [
        "/api/gallery/thumb/nested%2Foutside.png",
        "/api/gallery/thumb/nested%255Coutside.png",
        "/api/video/file/nested%2Foutside.mp4",
        "/api/video/file/nested%255Coutside.mp4",
    ],
)
def test_media_routes_reject_encoded_separators_without_path_leak(monkeypatch, tmp_path, route):
    _configure_media_roots(monkeypatch, tmp_path)

    response = TestClient(main.app, base_url="http://testserver").get(route)

    assert response.status_code == 404
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize(
    ("route", "root_name", "leaf_name"),
    [
        ("/api/gallery/thumb/linked.png", "gallery", "linked.png"),
        ("/api/video/file/linked.mp4", "videos", "linked.mp4"),
    ],
)
def test_media_routes_reject_symlinked_files(
    monkeypatch,
    tmp_path,
    route,
    root_name,
    leaf_name,
):
    gallery, videos, _thumbs = _configure_media_roots(monkeypatch, tmp_path)
    outside = tmp_path / ("outside.png" if leaf_name.endswith(".png") else "outside.mp4")
    outside.write_bytes(b"outside-media")
    link = {"gallery": gallery, "videos": videos}[root_name] / leaf_name
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows environment")

    response = TestClient(main.app, base_url="http://testserver").get(route)

    assert response.status_code == 404
    assert str(outside) not in response.text
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize(
    ("route", "root_name", "base_name"),
    [
        ("/api/gallery/thumb/source.png%3Asecret", "gallery", "source.png"),
        ("/api/video/file/source.mp4%3Asecret", "videos", "source.mp4"),
    ],
)
def test_media_routes_reject_existing_windows_ads(
    monkeypatch,
    tmp_path,
    route,
    root_name,
    base_name,
):
    gallery, videos, _thumbs = _configure_media_roots(monkeypatch, tmp_path)
    root = {"gallery": gallery, "videos": videos}[root_name]
    base = root / base_name
    base.write_bytes(b"base-media")
    ads_path = f"{base}:secret"
    try:
        with open(ads_path, "wb") as stream:
            stream.write(b"secret-stream")
    except OSError:
        pytest.skip("alternate data streams are unavailable on this filesystem")

    response = TestClient(main.app, base_url="http://testserver").get(route)

    assert response.status_code == 404
    assert str(base) not in response.text
    assert str(tmp_path) not in response.text


def test_thumbnail_keeps_gallery_existing_video_thumb_and_fallback_paths(monkeypatch, tmp_path):
    gallery, videos, thumbs = _configure_media_roots(monkeypatch, tmp_path)
    gallery_bytes = _image_bytes(image_format="JPEG")
    (gallery / "source.png").write_bytes(gallery_bytes)
    existing_thumb = _image_bytes(image_format="JPEG")
    (thumbs / "existing_thumb.jpg").write_bytes(existing_thumb)
    (videos / "fallback.mp4").write_bytes(b"video-bytes")
    generated_thumb = thumbs / "fallback_thumb.jpg"
    generated_bytes = _image_bytes()
    generated_calls = []

    def generate(video_path):
        generated_calls.append(video_path)
        generated_thumb.write_bytes(generated_bytes)
        return generated_thumb

    monkeypatch.setattr(main, "_generate_video_thumbnail", generate)
    client = TestClient(main.app, base_url="http://testserver")

    gallery_response = client.get("/api/gallery/thumb/source.png")
    existing_response = client.get("/api/gallery/thumb/existing.mp4")
    fallback_response = client.get("/api/gallery/thumb/fallback.mp4")

    assert gallery_response.status_code == 200
    assert gallery_response.headers["content-type"] == "image/jpeg"
    assert gallery_response.content == gallery_bytes
    assert existing_response.status_code == 200
    assert existing_response.headers["content-type"] == "image/jpeg"
    assert existing_response.content == existing_thumb
    assert fallback_response.status_code == 200
    assert fallback_response.headers["content-type"] == "image/png"
    assert fallback_response.content == generated_bytes
    assert generated_calls == [(videos / "fallback.mp4").resolve()]


@pytest.mark.parametrize(
    ("payload", "error_code"),
    [
        (b"not-an-image", "gallery_image_invalid"),
        (_image_bytes(image_format="GIF"), "gallery_image_mime_unsupported"),
    ],
)
def test_thumbnail_rejects_invalid_or_unsupported_image_payloads(
    monkeypatch,
    tmp_path,
    payload,
    error_code,
):
    gallery, _videos, _thumbs = _configure_media_roots(monkeypatch, tmp_path)
    image_path = gallery / "unsafe.png"
    image_path.write_bytes(payload)

    response = TestClient(main.app, base_url="http://testserver").get(
        "/api/gallery/thumb/unsafe.png"
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == error_code
    assert str(image_path) not in response.text
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize(
    ("suffix", "media_type"),
    [
        (".mp4", "video/mp4"),
        (".webm", "video/webm"),
        (".mov", "video/quicktime"),
    ],
)
def test_video_file_keeps_legal_extensions_and_range_response(
    monkeypatch,
    tmp_path,
    suffix,
    media_type,
):
    _gallery, videos, _thumbs = _configure_media_roots(monkeypatch, tmp_path)
    video_bytes = b"0123456789"
    (videos / f"source{suffix}").write_bytes(video_bytes)

    response = TestClient(main.app, base_url="http://testserver").get(
        f"/api/video/file/source{suffix}",
        headers={"Range": "bytes=2-5"},
    )

    assert response.status_code == 206
    assert response.headers["content-type"] == media_type
    assert response.headers["content-range"] == "bytes 2-5/10"
    assert response.content == b"2345"
