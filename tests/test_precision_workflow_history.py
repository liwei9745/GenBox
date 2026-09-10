import asyncio
import base64
import hashlib
import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin

import main
import providers


@pytest.fixture(autouse=True)
def isolate_precision_workflow_history(tmp_path, monkeypatch):
    previous_history = dict(main.generation_history)
    main.generation_history.clear()
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    monkeypatch.setattr(main, "GALLERY_DIR", gallery)
    monkeypatch.setattr(main, "HISTORY_FILE", tmp_path / "history.jsonl")
    monkeypatch.setattr(main, "LOG_FILE", tmp_path / "logs.jsonl")
    yield gallery
    main.generation_history.clear()
    main.generation_history.update(previous_history)


def _png(path, *, size=(18, 12), color=(32, 96, 160), prompt=""):
    metadata = PngImagePlugin.PngInfo()
    if prompt:
        metadata.add_text("Prompt", prompt)
    Image.new("RGB", size, color=color).save(path, format="PNG", pnginfo=metadata)
    return path.read_bytes()


def _workflow_metadata(
    workflow_id,
    *,
    source_bytes,
    source_filename=None,
    parent_generation_id=None,
    parent_result_key=None,
    outputs=None,
):
    return {
        "schema": main.PRECISION_WORKFLOW_SCHEMA,
        "workflow_id": workflow_id,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_width": 18,
        "source_height": 12,
        "input_gallery_filename": source_filename,
        "parent_generation_id": parent_generation_id,
        "parent_result_key": parent_result_key,
        "outputs": outputs or {},
    }


def _result(path, *, prompt):
    return {
        "success": True,
        "local_path": str(path),
        "prompt": prompt,
        "original_prompt": prompt,
        "metadata": {"raw_log": "must-not-cross"},
        "model": "precision-provider",
        "seq": 0,
    }


def test_precision_workflow_api_projects_chain_without_sensitive_fields(isolate_precision_workflow_history):
    gallery = isolate_precision_workflow_history
    secret = "SECRET-PROMPT-NEVER-RETURN"
    source_path = gallery / "source_SECRET-PROMPT-NEVER-RETURN.png"
    first_path = gallery / "precision_SECRET-FIRST.png"
    second_path = gallery / "precision_SECRET-SECOND.png"
    source_bytes = _png(source_path, prompt=secret)
    first_bytes = _png(first_path, color=(40, 110, 170), prompt=secret + "-FIRST")
    second_bytes = _png(second_path, color=(50, 120, 180), prompt=secret + "-SECOND")
    workflow_id = "pw_" + "a" * 32

    main.generation_history.update({
        "gen_0001_root": {
            "generation_id": "gen_0001_root",
            "mode": "precision_edit",
            "prompt": secret,
            "system_prompt": "API-KEY-secret-value",
            "created_at": "2026-09-01 10:00:00",
            "logs": ["C:\\private\\raw.log"],
            "results": {"provider": _result(first_path, prompt=secret)},
            "precision_workflow": _workflow_metadata(
                workflow_id,
                source_bytes=source_bytes,
                source_filename=source_path.name,
                outputs={
                    "provider": {
                        "sha256": hashlib.sha256(first_bytes).hexdigest(),
                        "filename": first_path.name,
                        "width": 18,
                        "height": 12,
                    }
                },
            ),
        },
        "gen_0002_child": {
            "generation_id": "gen_0002_child",
            "mode": "precision_edit",
            "prompt": secret + "-CHILD",
            "created_at": "2026-09-02 11:00:00",
            "results": {"provider": _result(second_path, prompt=secret + "-CHILD")},
            "precision_workflow": _workflow_metadata(
                workflow_id,
                source_bytes=first_bytes,
                source_filename=first_path.name,
                parent_generation_id="gen_0001_root",
                parent_result_key="provider",
                outputs={
                    "provider": {
                        "sha256": hashlib.sha256(second_bytes).hexdigest(),
                        "filename": second_path.name,
                        "width": 18,
                        "height": 12,
                    }
                },
            ),
        },
    })

    client = TestClient(main.app)
    response = client.get("/api/precision/workflows")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    workflow = body["items"][0]
    assert workflow["workflow_id"] == workflow_id
    assert workflow["edit_count"] == 2
    assert workflow["summary"] == {
        "edit_count": 2,
        "available_version_count": 2,
        "source_available": True,
        "latest_size": "18x12",
    }
    assert [version["kind"] for version in workflow["versions"]] == ["source", "result", "result"]
    assert workflow["versions"][2]["parent_version_id"] == workflow["versions"][1]["version_id"]
    assert workflow["restore"]["version_id"] == workflow["versions"][2]["version_id"]
    assert workflow["thumbnail"].startswith(f"/api/precision/workflows/{workflow_id}/versions/")

    serialized = json.dumps(body, ensure_ascii=False)
    for forbidden in (
        secret,
        "API-KEY-secret-value",
        "raw.log",
        str(gallery),
        source_path.name,
        first_path.name,
        second_path.name,
        hashlib.sha256(source_bytes).hexdigest(),
        hashlib.sha256(first_bytes).hexdigest(),
    ):
        assert forbidden not in serialized

    image_response = client.get(workflow["restore"]["image_url"])
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    assert secret.encode() not in image_response.content
    with Image.open(BytesIO(image_response.content)) as restored:
        assert restored.size == (18, 12)
        assert "Prompt" not in restored.info


def test_precision_workflow_api_filters_by_any_version_date_and_id(isolate_precision_workflow_history):
    gallery = isolate_precision_workflow_history
    source_path = gallery / "source.png"
    result_path = gallery / "result.png"
    source_bytes = _png(source_path)
    result_bytes = _png(result_path)
    workflow_id = "pw_" + "b" * 32
    main.generation_history["gen_date"] = {
        "generation_id": "gen_date",
        "mode": "precision_edit",
        "created_at": "2026-09-03 08:00:00",
        "results": {"provider": _result(result_path, prompt="private")},
        "precision_workflow": _workflow_metadata(
            workflow_id,
            source_bytes=source_bytes,
            source_filename=source_path.name,
            outputs={
                "provider": {
                    "sha256": hashlib.sha256(result_bytes).hexdigest(),
                    "filename": result_path.name,
                    "width": 18,
                    "height": 12,
                }
            },
        ),
    }
    client = TestClient(main.app)

    matched = client.get(
        "/api/precision/workflows",
        params={"date_from": "2026-09-03", "date_to": "2026-09-03", "workflow_id": workflow_id},
    )
    assert matched.status_code == 200
    assert matched.json()["total"] == 1
    assert client.get(
        "/api/precision/workflows",
        params={"date_from": "2026-09-04", "date_to": "2026-09-04"},
    ).json()["total"] == 0
    assert client.get(f"/api/precision/workflows/{workflow_id}").json()["workflow"]["workflow_id"] == workflow_id

    bad_date = client.get("/api/precision/workflows", params={"date_from": "2026-02-30"})
    assert bad_date.status_code == 422
    assert bad_date.json()["detail"]["code"] == "precision_workflow_date_invalid"
    bad_range = client.get(
        "/api/precision/workflows",
        params={"date_from": "2026-09-04", "date_to": "2026-09-03"},
    )
    assert bad_range.status_code == 422
    assert bad_range.json()["detail"]["code"] == "precision_workflow_date_range_invalid"
    assert client.get("/api/precision/workflows", params={"workflow_id": "../../secret"}).status_code == 422


def test_precision_workflow_detail_exposes_validated_annotation_restore_snapshot_only_on_detail(
    isolate_precision_workflow_history,
):
    gallery = isolate_precision_workflow_history
    source_path = gallery / "source.png"
    result_path = gallery / "result.png"
    source_bytes = _png(source_path)
    result_bytes = _png(result_path)
    workflow_id = "pw_" + "c" * 32
    annotation_snapshot = {
        "annotation_contract": main.PRECISION_ANNOTATION_CONTRACT_V3,
        "annotations": [{
            "type": "ellipse", "label": 1, "instruction": "Make the badge blue.",
            "x": 0.2, "y": 0.2, "width": 0.3, "height": 0.2,
        }],
        "precision_strategy": "fine",
        "precision_selection_mode": "annotation",
        "precision_selection_feather": 0,
    }
    main.generation_history["gen_snapshot"] = {
        "generation_id": "gen_snapshot",
        "mode": "precision_edit",
        "created_at": "2026-09-03 08:00:00",
        "results": {"provider": _result(result_path, prompt="private")},
        "precision_workflow": {
            **_workflow_metadata(
                workflow_id,
                source_bytes=source_bytes,
                source_filename=source_path.name,
                outputs={"provider": {
                    "sha256": hashlib.sha256(result_bytes).hexdigest(),
                    "filename": result_path.name,
                    "width": 18,
                    "height": 12,
                }},
            ),
            "annotation_snapshot": annotation_snapshot,
        },
    }

    client = TestClient(main.app)
    listing = client.get("/api/precision/workflows")
    assert listing.status_code == 200
    assert "annotation_snapshot" not in json.dumps(listing.json())

    detail = client.get(f"/api/precision/workflows/{workflow_id}")
    assert detail.status_code == 200
    workflow = detail.json()["workflow"]
    version = workflow["versions"][1]
    assert version["annotation_snapshot"] == annotation_snapshot
    assert workflow["restore"]["base_version_id"] == "original"
    assert workflow["restore"]["annotation_snapshot"] == annotation_snapshot


def test_legacy_precision_history_is_a_safe_single_step_workflow(isolate_precision_workflow_history):
    gallery = isolate_precision_workflow_history
    result_path = gallery / "legacy_prompt_fragment.png"
    _png(result_path, prompt="legacy private prompt")
    main.generation_history["gen_legacy"] = {
        "generation_id": "gen_legacy",
        "mode": "precision_edit",
        "prompt": "legacy private prompt",
        "created_at": "2026-08-31 09:00:00",
        "results": {"provider": _result(result_path, prompt="legacy private prompt")},
    }

    body = TestClient(main.app).get("/api/precision/workflows").json()

    assert body["total"] == 1
    workflow = body["items"][0]
    assert workflow["workflow_id"] == main._precision_legacy_workflow_id("gen_legacy")
    assert workflow["edit_count"] == 1
    assert workflow["summary"]["source_available"] is False
    assert workflow["versions"][0]["available"] is False
    assert workflow["restore"] is not None
    serialized = json.dumps(body)
    assert "legacy private prompt" not in serialized
    assert result_path.name not in serialized
    assert str(result_path) not in serialized


def test_precision_lineage_metadata_links_a_new_edit_to_an_existing_result(isolate_precision_workflow_history):
    gallery = isolate_precision_workflow_history
    prior_path = gallery / "prior.png"
    prior_bytes = _png(prior_path, color=(70, 80, 90))
    main.generation_history["gen_prior"] = {
        "generation_id": "gen_prior",
        "mode": "precision_edit",
        "created_at": "2026-09-01 09:00:00",
        "results": {"provider": _result(prior_path, prompt="private parent")},
    }
    source_data = "data:image/png;base64," + base64.b64encode(prior_bytes).decode("ascii")

    metadata = main._prepare_precision_workflow_metadata({
        "images": [{"value": source_data, "width": 18, "height": 12}]
    })

    assert metadata["workflow_id"] == main._precision_legacy_workflow_id("gen_prior")
    assert metadata["parent_generation_id"] == "gen_prior"
    assert metadata["parent_result_key"] == "provider"
    assert metadata["input_gallery_filename"] == prior_path.name
    assert "data:image" not in json.dumps(metadata)

    next_path = gallery / "next.png"
    next_bytes = _png(next_path, color=(90, 100, 110))
    finalized = main._finalize_precision_workflow_metadata({
        "precision_workflow": metadata,
        "results": {"provider": _result(next_path, prompt="private child")},
    })
    assert finalized["outputs"]["provider"]["sha256"] == hashlib.sha256(next_bytes).hexdigest()
    assert finalized["outputs"]["provider"]["filename"] == next_path.name
    assert "private child" not in json.dumps(finalized)


def test_precision_generation_completion_persists_lineage_metadata(
    isolate_precision_workflow_history,
    monkeypatch,
):
    gallery = isolate_precision_workflow_history
    source_path = gallery / "source.png"
    output_path = gallery / "output.png"
    source_bytes = _png(source_path)
    output_bytes = _png(output_path, color=(120, 80, 40))
    source_data = "data:image/png;base64," + base64.b64encode(source_bytes).decode("ascii")
    workflow_metadata = main._prepare_precision_workflow_metadata({
        "images": [{"value": source_data, "width": 18, "height": 12}]
    })

    async def fake_generate_for_provider(_provider, _prompt, **_kwargs):
        return main.ImageResult(
            success=True,
            local_path=str(output_path),
            generation_id="provider-result",
            model="provider",
        )

    monkeypatch.setattr(providers, "generate_for_provider", fake_generate_for_provider)
    generation_id = "gen_persist"
    provider = SimpleNamespace(id="provider", name="Provider", model="edit-model")
    main.image_tasks[generation_id] = {
        "status": "queued",
        "progress": 0,
        "mode": "precision_edit",
        "prompt": "private prompt",
        "enhanced_prompt": None,
        "providers": ["provider"],
        "provider_states": {
            "provider": {
                "status": "queued",
                "progress": 0,
                "model": "provider",
                "name": "Provider",
                "color": "#000000",
                "seq": 0,
                "qty": 1,
                "log": [],
                "result": None,
            }
        },
        "task_list": [("provider", 0, 1)],
        "all_providers": {"provider": provider},
        "kwargs": {},
        "provider_kwargs_map": {"provider": {}},
        "start_time": 0,
        "results": {},
        "continuous": False,
        "continuous_id": None,
        "system_prompt": None,
        "original_prompt": "private prompt",
        "precision_workflow": workflow_metadata,
        "upscale_to": None,
    }
    try:
        asyncio.run(main._process_image_gen_impl(generation_id))
    finally:
        main.image_tasks.pop(generation_id, None)

    persisted = main.generation_history[generation_id]["precision_workflow"]
    assert persisted["workflow_id"] == workflow_metadata["workflow_id"]
    assert persisted["outputs"]["provider"]["sha256"] == hashlib.sha256(output_bytes).hexdigest()
    stored_line = json.loads(main.HISTORY_FILE.read_text(encoding="utf-8"))
    assert stored_line["precision_workflow"] == persisted
