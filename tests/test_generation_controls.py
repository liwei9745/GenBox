"""Focused regression tests for image-generation controls."""

import asyncio
from types import SimpleNamespace

import main
from pathlib import Path
from fastapi.testclient import TestClient


def _provider_state(status="queued"):
    return {
        "status": status,
        "progress": 0,
        "model": "provider-a",
        "name": "Provider A",
        "color": "#5b8def",
        "seq": 0,
        "qty": 1,
        "log": [],
        "result": None,
    }


def _image_task(gen_id, provider_states, task_list=None):
    return {
        "status": "queued",
        "progress": 0,
        "mode": "t2i",
        "prompt": "test prompt",
        "enhanced_prompt": None,
        "llm_error": None,
        "providers": ["provider-a"],
        "provider_states": provider_states,
        "task_list": task_list or [("provider-a", 0, 1)],
        "task_index": 0,
        "all_providers": {
            "provider-a": SimpleNamespace(id="provider-a", name="Provider A", model="model-a")
        },
        "kwargs": {},
        "provider_kwargs_map": {"provider-a": {}},
        "start_time": 0,
        "results": {},
        "continuous": False,
        "continuous_id": None,
        "system_prompt": None,
        "original_prompt": "test prompt",
        "upscale_to": None,
        "upscale_method": "lanczos3",
        "upscale_ratio": "original",
    }


def test_generate_request_accepts_multiple_reference_images():
    request = main.GenerateRequest(
        prompt="keep the composition",
        mode="i2i",
        image_data_list=["data:image/png;base64,one", "data:image/png;base64,two"],
    )
    assert request.image_data_list == [
        "data:image/png;base64,one",
        "data:image/png;base64,two",
    ]


def test_generation_ui_uses_visible_ratio_and_dimensions_and_exposes_opt_in_crop():
    js = Path("static/js/app-all.js").read_text(encoding="utf-8")
    html = Path("static/index.html").read_text(encoding="utf-8")

    assert "'21:9-2k':  [2544, 1088]" in js
    assert "document.getElementById('selRatio').value || currentSettings.ratio" in js
    assert "parseInt(document.getElementById('inputW').value, 10)" in js
    assert "id=\"chkExactRatioCrop\"" in html
    assert "exact_ratio_crop" in js


def test_cancel_generate_is_idempotent_and_marks_queued_children_cancelled():
    gen_id = "test-cancel-controls"
    main.image_tasks[gen_id] = {
        "status": "queued",
        "provider_states": {
            "provider-a": {
                "status": "queued",
                "log": [],
            }
        },
    }
    main.image_task_handles.pop(gen_id, None)
    try:
        result = asyncio.run(main.cancel_generate(gen_id))
        assert result == {"ok": True, "status": "cancelled"}
        assert main.image_tasks[gen_id]["status"] == "cancelled"
        assert main.image_tasks[gen_id]["provider_states"]["provider-a"]["status"] == "cancelled"

        again = asyncio.run(main.cancel_generate(gen_id))
        assert again == {"ok": True, "status": "cancelled"}
    finally:
        main.image_tasks.pop(gen_id, None)
        main.image_task_handles.pop(gen_id, None)


def test_cancel_generate_marks_running_task_cancelled_without_handle():
    gen_id = "test-cancel-running-without-handle"
    provider_states = {"provider-a": _provider_state("generating")}
    main.image_tasks[gen_id] = _image_task(gen_id, provider_states)
    main.image_tasks[gen_id]["status"] = "generating"
    main.image_task_handles.pop(gen_id, None)
    try:
        assert asyncio.run(main.cancel_generate(gen_id)) == {"ok": True, "status": "cancelled"}
        assert main.image_tasks[gen_id]["status"] == "cancelled"
        assert provider_states["provider-a"]["status"] == "cancelled"
        assert gen_id not in main.image_task_handles
    finally:
        main.image_tasks.pop(gen_id, None)
        main.image_task_handles.pop(gen_id, None)


def test_cancel_generate_rejects_unknown_task_without_mutation():
    gen_id = "test-cancel-unknown"
    main.image_tasks.pop(gen_id, None)
    main.image_task_handles.pop(gen_id, None)

    try:
        try:
            asyncio.run(main.cancel_generate(gen_id))
        except main.HTTPException as exc:
            assert exc.status_code == 404
            assert exc.detail == "任务不存在"
        else:
            raise AssertionError("unknown generation cancellation must fail closed")
        assert gen_id not in main.image_tasks
        assert gen_id not in main.image_task_handles
    finally:
        main.image_tasks.pop(gen_id, None)
        main.image_task_handles.pop(gen_id, None)


def test_cancel_generate_preserves_terminal_status():
    for status in ("completed", "failed", "cancelled"):
        gen_id = f"test-cancel-terminal-{status}"
        main.image_tasks[gen_id] = {"status": status, "provider_states": {}}
        try:
            assert asyncio.run(main.cancel_generate(gen_id)) == {"ok": True, "status": status}
            assert main.image_tasks[gen_id]["status"] == status
        finally:
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)


def test_cancel_generate_derives_terminal_children_before_cancelling():
    cases = [
        (
            "all-completed",
            [("completed", 100, True, ""), ("completed", 100, True, "")],
            "completed",
        ),
        (
            "all-failed",
            [("failed", 100, False, "first real error"), ("failed", 65, False, "second real error")],
            "failed",
        ),
        (
            "partial-success",
            [("completed", 100, True, ""), ("failed", 40, False, "partial real error")],
            "completed",
        ),
    ]

    class PendingHandle:
        def __init__(self):
            self.cancel_calls = 0

        def done(self):
            return False

        def cancel(self):
            self.cancel_calls += 1

    for case, child_specs, expected_status in cases:
        gen_id = f"test-cancel-derive-{case}"
        states = {}
        results = {}
        for index, (status, progress, success, error) in enumerate(child_specs):
            key = f"provider-a_{index}"
            state = _provider_state(status)
            state.update({"progress": progress, "seq": index, "qty": len(child_specs)})
            state["result"] = {
                "success": success,
                "local_path": f"result-{index}.png" if success else None,
                "generation_id": f"child-{index}" if success else None,
                "error": error,
                "model": "provider-a",
                "prompt": "test prompt",
                "original_prompt": "test prompt",
                "seq": index,
                "elapsed_seconds": 1.0,
                "started_at": 1.0,
                "finished_at": 2.0,
            }
            states[key] = state
            results[key] = state["result"]

        task = _image_task(gen_id, states)
        task.update({"status": "generating", "results": results})
        handle = PendingHandle()
        main.image_tasks[gen_id] = task
        main.image_task_handles[gen_id] = handle
        try:
            cancelled = asyncio.run(main.cancel_generate(gen_id))
            payload = asyncio.run(main.get_generate_status(gen_id))

            assert cancelled == {"ok": True, "status": expected_status}
            assert payload["status"] == expected_status
            assert task["results"] == results
            assert handle.cancel_calls == 0
            assert main.image_task_handles[gen_id] is handle
            if expected_status == "completed":
                assert payload["results"] == results
            else:
                assert payload["progress"] < 100
                assert [state["result"]["error"] for state in payload["provider_states"].values()] == [
                    "first real error",
                    "second real error",
                ]
        finally:
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)


def test_cancelled_provider_state_is_terminal_for_status_api():
    gen_id = "test-cancelled-status-terminal"
    main.image_tasks[gen_id] = _image_task(gen_id, {"provider-a": _provider_state("cancelled")})
    main.image_tasks[gen_id]["status"] = "generating"
    try:
        status = asyncio.run(main.get_generate_status(gen_id))
        assert status["status"] == "cancelled"
        assert status["results"] == {}
        assert status["group_timings"] == {}
        assert main.image_tasks[gen_id]["status"] == "cancelled"
    finally:
        main.image_tasks.pop(gen_id, None)
        main.image_task_handles.pop(gen_id, None)


def test_background_cancel_does_not_write_completed_or_leak_handle(monkeypatch):
    import providers

    async def scenario():
        gen_id = "test-background-cancel"
        started = asyncio.Event()
        calls = 0
        history_writes = []

        async def fake_generate_for_provider(p_cfg, prompt, **kwargs):
            nonlocal calls
            calls += 1
            started.set()
            await asyncio.sleep(60)
            return SimpleNamespace(
                success=True,
                local_path=None,
                generation_id="should-not-complete",
                error="",
            )

        monkeypatch.setattr(providers, "generate_for_provider", fake_generate_for_provider)
        monkeypatch.setattr(main, "_write_log", lambda *args, **kwargs: None)
        monkeypatch.setattr(main, "_save_history_entry", history_writes.append)

        provider_states = {
            "provider-a_0": _provider_state("queued"),
            "provider-a_1": _provider_state("queued"),
        }
        provider_states["provider-a_0"]["seq"] = 0
        provider_states["provider-a_0"]["qty"] = 2
        provider_states["provider-a_1"]["seq"] = 1
        provider_states["provider-a_1"]["qty"] = 2
        main.image_tasks[gen_id] = _image_task(
            gen_id,
            provider_states,
            task_list=[("provider-a", 0, 2), ("provider-a", 1, 2)],
        )
        handle = asyncio.create_task(main._process_image_gen(gen_id))
        main.image_task_handles[gen_id] = handle
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
            result = await main.cancel_generate(gen_id)
            await asyncio.wait_for(handle, timeout=1)

            assert result == {"ok": True, "status": "cancelled"}
            assert not handle.cancelled()
            assert calls == 1
            assert main.image_tasks[gen_id]["status"] == "cancelled"
            assert main.image_tasks[gen_id]["results"] == {}
            assert gen_id not in main.generation_history
            assert gen_id not in main.image_task_handles
            assert history_writes == []
            assert provider_states["provider-a_0"]["status"] == "cancelled"
            assert provider_states["provider-a_1"]["status"] == "cancelled"
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


def test_generation_status_route_projects_all_terminal_outcomes(monkeypatch):
    client = TestClient(main.app, base_url="http://testserver")

    def result(seq, success, error="", elapsed=1.0):
        return {
            "success": success,
            "local_path": f"result-{seq}.png" if success else None,
            "generation_id": f"child-{seq}" if success else None,
            "error": error,
            "model": "provider-a",
            "prompt": "test prompt",
            "original_prompt": "test prompt",
            "seq": seq,
            "elapsed_seconds": elapsed,
            "started_at": 10.0,
            "finished_at": 10.0 + elapsed,
        }

    cases = [
        (
            "partial-success-cancelled",
            "generating",
            [("completed", 100, result(0, True, elapsed=2.4)), ("generating", 42, None)],
            "cancelled",
            1,
            1,
        ),
        (
            "all-failed",
            "failed",
            [("failed", 40, result(0, False, "first real error", 1.2)), ("failed", 60, result(1, False, "second real error", 2.3))],
            "failed",
            0,
            2,
        ),
        (
            "all-cancelled",
            "cancelled",
            [("cancelled", 40, None), ("cancelled", 70, None)],
            "cancelled",
            0,
            0,
        ),
        (
            "completed",
            "completed",
            [("completed", 100, result(0, True, elapsed=3.1)), ("failed", 55, result(1, False, "nonfatal error", 1.7))],
            "completed",
            1,
            2,
        ),
    ]

    for gen_id, task_status, child_specs, expected_status, success_count, timing_count in cases:
        states = {}
        results = {}
        for index, (child_status, progress, child_result) in enumerate(child_specs):
            state = _provider_state(child_status)
            state.update({"progress": progress, "seq": index, "qty": len(child_specs)})
            state["result"] = child_result
            key = f"provider-a_{index}"
            states[key] = state
            if child_result is not None:
                results[key] = child_result
        task = _image_task(gen_id, states, task_list=[("provider-a", 0, 2), ("provider-a", 1, 2)])
        task.update({"status": task_status, "results": results, "start_time": 10.0, "elapsed_seconds": 7.5})
        main.image_tasks[gen_id] = task
        try:
            if expected_status == "cancelled" and success_count:
                monkeypatch.setattr(main, "_write_log", lambda *_args, **_kwargs: None)
                cancel_response = client.post(f"/api/generate/cancel/{gen_id}")
                assert cancel_response.status_code == 200
                assert cancel_response.json()["status"] == "cancelled"
            response = client.get(f"/api/generate/status/{gen_id}")
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == expected_status
            assert set(payload["provider_states"]) == set(states)
            assert payload["results"] == results
            assert len(payload["group_timings"].get("provider-a", {}).get("images", [])) == timing_count
            assert payload["group_timings"].get("provider-a", {}).get("total", 0) == round(
                sum(item["elapsed_seconds"] for item in results.values()), 1
            ) if results else payload["group_timings"] == {}
            if expected_status in ("failed", "cancelled"):
                assert payload["progress"] < 100
            if expected_status == "cancelled" and success_count:
                assert payload["results"]["provider-a_0"]["local_path"] == "result-0.png"
                assert payload["group_timings"]["provider-a"]["images"][0]["elapsed"] == 2.4
            if expected_status == "failed":
                assert [item["error"] for item in payload["results"].values()] == [
                    "first real error", "second real error"
                ]
            assert sum(item["success"] for item in payload["results"].values()) == success_count
        finally:
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)


def test_background_completion_cleans_image_task_handle(monkeypatch):
    import providers

    async def scenario():
        gen_id = "test-background-completion-cleanup"

        async def fake_generate_for_provider(p_cfg, prompt, **kwargs):
            return SimpleNamespace(
                success=True,
                local_path=None,
                generation_id="completed",
                error="",
            )

        monkeypatch.setattr(providers, "generate_for_provider", fake_generate_for_provider)
        monkeypatch.setattr(main, "_write_log", lambda *args, **kwargs: None)
        monkeypatch.setattr(main, "_save_history_entry", lambda *args, **kwargs: None)
        main.image_tasks[gen_id] = _image_task(gen_id, {"provider-a": _provider_state("queued")})
        handle = asyncio.create_task(main._process_image_gen(gen_id))
        main.image_task_handles[gen_id] = handle
        try:
            await asyncio.wait_for(handle, timeout=1)
            assert main.image_tasks[gen_id]["status"] == "completed"
            assert gen_id not in main.image_task_handles
        finally:
            main.image_tasks.pop(gen_id, None)
            main.image_task_handles.pop(gen_id, None)
            main.generation_history.pop(gen_id, None)

    asyncio.run(scenario())


def test_ui_exposes_inpaint_entry_multiple_uploads_and_cancel_request():
    from pathlib import Path

    root = Path(__file__).parents[1]
    html = (root / "static/index.html").read_text(encoding="utf-8")
    js = (root / "static/js/app-all.js").read_text(encoding="utf-8")
    assert "data-i18n=\"creator.inpaint\"" in html
    assert 'id="fileInput" accept="image/*" multiple' in html
    assert "image_data_list" in js
    assert "/api/generate/cancel/" in js
    translations = (root / "static/js/i18n.js").read_text(encoding="utf-8")
    assert "当前模型不能做局部重绘" in translations
    assert "只能普通生图" in translations
    assert "id=\"inpaintManualChoice\"" in html
    assert "setInpaintManualChoice(this.checked)" in html
    assert "pointer-events: none" in (root / "static/css/app.css").read_text(encoding="utf-8")
    assert "event.stopPropagation();onImageModelChange" in js
    assert "function modelSupportsGenerationMode" in js
    assert "currentMode === 'inpaint'" in js
    assert 'id="generationModelHelp"' in html
    assert "function updateGenerationModelHelp" in js
    assert "setGenerationControls('submitting')" in js
    assert "setGenerationControls('cancelling')" in js
    assert "stopButton.disabled = true" in js
    assert 'id="subTabPrecisionEdit"' in html
    assert 'data-i18n="common.precision_edit"' in html
    assert "function sendToPrecisionEdit" in js
    send_to_precision = js[js.index("function sendToPrecisionEdit") : js.index("function sendToVideo")]
    source_assignment = send_to_precision.index("var imageData = d.data;")
    source_validation = send_to_precision.index(
        "if (typeof imageData !== 'string' || !imageData) throw new Error(i18nText('image.data_failed'));"
    )
    source_load = send_to_precision.index("loadPrecisionEditSourceImage(imageData, prompt, {")
    assert source_assignment < source_validation < source_load
    assert "image.sent_precision_edit" in translations
