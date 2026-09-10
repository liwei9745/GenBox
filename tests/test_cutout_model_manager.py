"""Security and route contracts for the fixed cutout model installer."""

import asyncio
import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath

import httpx
import pytest
from fastapi.testclient import TestClient

import main
import image_tools.cutout_model_manager as model_manager_module
from image_tools.cutout_model_manager import (
    MODEL_DOWNLOAD_URL,
    MODEL_INSTALL_CONTRACT,
    MODEL_SOURCE_ID,
    CutoutModelManager,
    CutoutModelManagerError,
)
from image_tools.cutout_onnx import CutoutONNXAdapter
from image_tools.cutout_registry import CutoutAdapterRegistry


_PAYLOAD = b"small-local-cutout-model-fixture"
_PUBLIC_DNS = lambda _host, _port: ["8.8.8.8"]


class _BytesStream(httpx.AsyncByteStream):
    def __init__(self, content: bytes):
        self.content = content

    async def __aiter__(self):
        yield self.content

    async def aclose(self):
        return None


def _streaming_response(request: httpx.Request, content: bytes, *, headers=None):
    return httpx.Response(
        200,
        headers=headers or {},
        stream=_BytesStream(content),
        request=request,
    )


def _manifest(payload: bytes = _PAYLOAD) -> dict:
    return {
        "filename": "u2net_human_seg.onnx",
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "md5": hashlib.md5(payload).hexdigest(),
    }


def _manager(
    tmp_path: Path,
    *,
    handler=None,
    resolver=_PUBLIC_DNS,
    download_url=MODEL_DOWNLOAD_URL,
    payload: bytes = _PAYLOAD,
    install_lock_timeout_seconds: float = 0.25,
    download_supported: bool = True,
):
    model_path = tmp_path / "models" / "u2net_human_seg.onnx"
    adapter = CutoutONNXAdapter(model_path=model_path, model_manifest=_manifest(payload))
    client_factory = None
    if handler is not None:
        client_factory = lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            trust_env=False,
        )
    manager = CutoutModelManager(
        adapter,
        download_url=download_url,
        resolver=resolver,
        client_factory=client_factory,
        timeout_seconds=2,
        install_lock_timeout_seconds=install_lock_timeout_seconds,
        download_supported=download_supported,
    )
    return manager, adapter


async def _wait_terminal(manager: CutoutModelManager, task_id: str) -> dict:
    for _attempt in range(300):
        task = manager.get_task(task_id)
        if task and task["status"] in {"completed", "failed", "cancelled"}:
            return task
        await asyncio.sleep(0.01)
    raise AssertionError("cutout model task did not finish")


def _download(manager: CutoutModelManager) -> dict:
    async def scenario():
        started = manager.start_download()
        return await _wait_terminal(manager, started["id"])

    return asyncio.run(scenario())


def test_public_model_contract_is_fixed_and_marks_license_unknown(tmp_path):
    manager, _adapter = _manager(tmp_path)

    status = manager.model_status()

    assert status["contract"] == MODEL_INSTALL_CONTRACT
    assert status["source_id"] == MODEL_SOURCE_ID
    assert status["source_page"] == "https://github.com/danielgatis/rembg/releases/tag/v0.0.0"
    assert status["filename"] == "u2net_human_seg.onnx"
    assert status["installed"] is False
    assert status["valid"] is False
    assert status["state"] == "missing"
    assert status["download_supported"] is True
    assert status["install_supported"] is True
    assert status["license"] == {
        "checkpoint_provenance_status": "UNVERIFIED",
        "commercial_use_status": "UNVERIFIED",
    }
    assert "download_url" not in status
    assert str(manager.model_path) not in str(status)


def test_production_default_disables_download_before_network_or_task_creation(tmp_path):
    calls = []
    model_path = tmp_path / "models" / "u2net_human_seg.onnx"
    adapter = CutoutONNXAdapter(model_path=model_path, model_manifest=_manifest())
    manager = CutoutModelManager(
        adapter,
        resolver=lambda *_args: calls.append("dns") or _PUBLIC_DNS(None, None),
        client_factory=lambda: calls.append("client"),
    )

    status = manager.model_status()
    assert status["download_supported"] is False
    assert status["install_supported"] is False
    assert status["source_page"].startswith("https://github.com/")
    assert status["license"]["commercial_use_status"] == "UNVERIFIED"
    with pytest.raises(CutoutModelManagerError) as exc:
        manager.start_download()

    assert exc.value.code == "cutout_model_download_unavailable"
    assert exc.value.status_code == 409
    assert manager._tasks == {}
    assert calls == []


def test_default_http_client_disables_environment_proxy_and_redirects(tmp_path, monkeypatch):
    captured = {}
    sentinel = object()

    def factory(**kwargs):
        captured.update(kwargs)
        return sentinel

    manager, _adapter = _manager(tmp_path)
    monkeypatch.setattr(model_manager_module.httpx, "AsyncClient", factory)

    assert manager._make_client() is sentinel
    assert captured["trust_env"] is False
    assert captured["follow_redirects"] is False
    assert captured["headers"]["Accept-Encoding"] == "identity"


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx",
        "https://user@github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx",
        "https://github.com:444/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx",
        "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx?token=secret",
        "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx#fragment",
        "https://evil.example/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx",
    ],
)
def test_initial_source_rejects_unsafe_url_shapes(tmp_path, unsafe_url):
    with pytest.raises((CutoutModelManagerError, ValueError)):
        _manager(tmp_path, download_url=unsafe_url)


def test_fixed_source_identity_page_and_allowlist_cannot_be_overridden(tmp_path):
    model_path = tmp_path / "u2net_human_seg.onnx"
    adapter = CutoutONNXAdapter(model_path=model_path, model_manifest=_manifest())

    with pytest.raises(ValueError):
        CutoutModelManager(adapter, source_id="other-source")
    with pytest.raises(ValueError):
        CutoutModelManager(adapter, source_page="https://github.com/example/other")
    with pytest.raises(ValueError):
        CutoutModelManager(adapter, allowed_hosts={"github.com", "evil.example"})


def test_download_accepts_only_allowlisted_signed_redirect_and_installs_atomically(tmp_path):
    requests = []

    def handler(request: httpx.Request):
        requests.append(str(request.url))
        if request.url.host == "github.com":
            return httpx.Response(
                302,
                headers={
                    "Location": (
                        "https://release-assets.githubusercontent.com/github-production-release-asset/"
                        "fixture/u2net_human_seg.onnx?sp=read&sig=synthetic-secret"
                    )
                },
                request=request,
            )
        return _streaming_response(
            request,
            _PAYLOAD,
            headers={"Content-Length": str(len(_PAYLOAD))},
        )

    manager, adapter = _manager(tmp_path, handler=handler)
    adapter._session = object()
    adapter._session_fingerprint = (1, "old", "old")

    task = _download(manager)

    assert task["status"] == "completed"
    assert task["phase"] == "completed"
    assert task["progress"] == 100
    assert task["downloaded_bytes"] == len(_PAYLOAD)
    assert manager.model_path.read_bytes() == _PAYLOAD
    assert adapter._session is None
    assert adapter._session_fingerprint is None
    assert not list(manager.model_path.parent.glob("*.part"))
    assert len(requests) == 2
    assert "sig=synthetic-secret" in requests[1]
    assert "synthetic-secret" not in str(task)
    assert "download_url" not in str(task)
    assert str(tmp_path.resolve()) not in str(task)
    assert set(task) == {
        "id",
        "contract",
        "source_id",
        "status",
        "phase",
        "progress",
        "downloaded_bytes",
        "total_bytes",
        "error_code",
        "message",
    }


def test_redirect_to_untrusted_host_is_rejected_without_exposing_location(tmp_path):
    secret_location = "https://evil.example/model.onnx?token=redirect-secret"

    def handler(request: httpx.Request):
        return httpx.Response(302, headers={"Location": secret_location}, request=request)

    manager, _adapter = _manager(tmp_path, handler=handler)
    task = _download(manager)

    assert task["status"] == "failed"
    assert task["error_code"] == "cutout_model_source_rejected"
    assert "evil.example" not in str(task)
    assert "redirect-secret" not in str(task)
    assert not manager.model_path.exists()
    assert not list(manager.model_path.parent.glob("*.part"))


def test_private_dns_answer_is_rejected_before_request(tmp_path):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        return _streaming_response(request, _PAYLOAD)

    manager, _adapter = _manager(
        tmp_path,
        handler=handler,
        resolver=lambda _host, _port: ["127.0.0.1"],
    )
    task = _download(manager)

    assert task["status"] == "failed"
    assert task["error_code"] == "cutout_model_source_rejected"
    assert calls == []


@pytest.mark.parametrize(
    "headers,content,error_code",
    [
        ({"Content-Length": "invalid"}, _PAYLOAD, "cutout_model_content_length_invalid"),
        ({"Content-Length": str(len(_PAYLOAD) + 1)}, _PAYLOAD, "cutout_model_size_mismatch"),
        ({"Content-Length": str(len(_PAYLOAD))}, _PAYLOAD[:-1], "cutout_model_size_mismatch"),
        ({"Content-Length": str(len(_PAYLOAD))}, _PAYLOAD + b"x", "cutout_model_size_exceeded"),
        ({"Content-Length": str(len(_PAYLOAD))}, b"x" * len(_PAYLOAD), "cutout_model_hash_mismatch"),
        (
            {"Content-Length": str(len(_PAYLOAD)), "Content-Encoding": "gzip"},
            _PAYLOAD,
            "cutout_model_content_encoding_rejected",
        ),
    ],
)
def test_size_hash_and_encoding_failures_clean_part_and_preserve_old_model(
    tmp_path,
    headers,
    content,
    error_code,
):
    old_model = b"old-model-must-survive"

    def handler(request: httpx.Request):
        return _streaming_response(request, content, headers=headers)

    manager, _adapter = _manager(tmp_path, handler=handler)
    manager.model_path.parent.mkdir(parents=True, exist_ok=True)
    manager.model_path.write_bytes(old_model)

    task = _download(manager)

    assert task["status"] == "failed"
    assert task["error_code"] == error_code
    assert manager.model_path.read_bytes() == old_model
    assert not list(manager.model_path.parent.glob("*.part"))


def test_chunked_download_without_content_length_uses_actual_size_and_hash(tmp_path):
    def handler(request: httpx.Request):
        return _streaming_response(request, _PAYLOAD)

    manager, _adapter = _manager(tmp_path, handler=handler)
    task = _download(manager)

    assert task["status"] == "completed"
    assert task["downloaded_bytes"] == len(_PAYLOAD)
    assert manager.model_path.read_bytes() == _PAYLOAD
    assert not list(manager.model_path.parent.glob("*.part"))


def test_timeout_is_sanitized_and_retry_can_succeed(tmp_path):
    attempts = {"count": 0}

    def handler(request: httpx.Request):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ReadTimeout("secret signed URL timed out", request=request)
        return _streaming_response(
            request,
            _PAYLOAD,
            headers={"Content-Length": str(len(_PAYLOAD))},
        )

    manager, _adapter = _manager(tmp_path, handler=handler)

    failed = _download(manager)
    completed = _download(manager)

    assert failed["status"] == "failed"
    assert failed["error_code"] == "cutout_model_download_timeout"
    assert "secret" not in str(failed)
    assert completed["status"] == "completed"


class _SlowStream(httpx.AsyncByteStream):
    def __init__(self, started: asyncio.Event):
        self.started = started

    async def __aiter__(self):
        yield _PAYLOAD[:5]
        self.started.set()
        await asyncio.Event().wait()

    async def aclose(self):
        return None


def test_cancel_cleans_partial_file_and_process_single_flight_rejects_overlap(tmp_path):
    async def scenario():
        started = asyncio.Event()

        def handler(request: httpx.Request):
            return httpx.Response(
                200,
                headers={"Content-Length": str(len(_PAYLOAD))},
                stream=_SlowStream(started),
                request=request,
            )

        manager, _adapter = _manager(tmp_path, handler=handler)
        manager.model_path.parent.mkdir(parents=True, exist_ok=True)
        manager.model_path.write_bytes(b"old-valid-model")
        task = manager.start_download()
        await asyncio.wait_for(started.wait(), timeout=1)
        with pytest.raises(CutoutModelManagerError) as busy:
            manager.start_download()
        assert busy.value.status_code == 409

        cancelled = await manager.cancel_download(task["id"])
        assert cancelled["status"] == "cancelled"
        assert cancelled["phase"] == "cancelled"
        assert manager.model_path.read_bytes() == b"old-valid-model"
        assert not list(manager.model_path.parent.glob("*.part"))

    asyncio.run(scenario())


def test_replace_failure_preserves_old_model_and_cleans_part(tmp_path, monkeypatch):
    old_model = b"old-model"

    def handler(request: httpx.Request):
        return _streaming_response(
            request,
            _PAYLOAD,
            headers={"Content-Length": str(len(_PAYLOAD))},
        )

    manager, _adapter = _manager(tmp_path, handler=handler)
    manager.model_path.parent.mkdir(parents=True, exist_ok=True)
    manager.model_path.write_bytes(old_model)
    _adapter._session = object()
    old_session = _adapter._session
    monkeypatch.setattr(model_manager_module.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("synthetic")))

    task = _download(manager)

    assert task["status"] == "failed"
    assert task["error_code"] == "cutout_model_install_failed"
    assert manager.model_path.read_bytes() == old_model
    assert _adapter._session is old_session
    assert not list(manager.model_path.parent.glob("*.part"))


def test_install_lock_deadline_fails_terminal_and_cleans_verified_part(tmp_path):
    def handler(request: httpx.Request):
        return _streaming_response(request, _PAYLOAD)

    manager, adapter = _manager(
        tmp_path,
        handler=handler,
        install_lock_timeout_seconds=0.02,
    )
    manager.model_path.parent.mkdir(parents=True, exist_ok=True)
    manager.model_path.write_bytes(b"old-model")
    assert adapter.acquire_model_operation() is True
    try:
        task = _download(manager)
    finally:
        adapter.release_model_operation()

    assert task["status"] == "failed"
    assert task["phase"] == "failed"
    assert task["error_code"] == "cutout_model_inference_busy"
    assert manager.model_path.read_bytes() == b"old-model"
    assert not list(manager.model_path.parent.glob("*.part"))


def test_delete_is_confirmed_at_route_and_exclusive_with_inference(tmp_path):
    manager, adapter = _manager(tmp_path)
    manager.model_path.parent.mkdir(parents=True, exist_ok=True)
    manager.model_path.write_bytes(_PAYLOAD)
    adapter._session = object()
    adapter._session_fingerprint = (len(_PAYLOAD), "sha", "md5")
    assert adapter.acquire_model_operation() is True
    try:
        with pytest.raises(CutoutModelManagerError) as busy:
            manager.delete_model()
        assert busy.value.status_code == 409
        assert manager.model_path.exists()
    finally:
        adapter.release_model_operation()

    result = manager.delete_model()

    assert result["deleted"] is True
    assert result["model"]["state"] == "missing"
    assert not manager.model_path.exists()
    assert adapter._session is None
    assert adapter._session_fingerprint is None


def test_delete_failure_preserves_old_model_and_cached_session(tmp_path, monkeypatch):
    manager, adapter = _manager(tmp_path)
    manager.model_path.parent.mkdir(parents=True, exist_ok=True)
    manager.model_path.write_bytes(_PAYLOAD)
    adapter._session = object()
    old_session = adapter._session
    monkeypatch.setattr(Path, "unlink", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("synthetic")))

    with pytest.raises(CutoutModelManagerError) as exc:
        manager.delete_model()

    assert exc.value.code == "cutout_model_delete_failed"
    assert adapter._session is old_session


def test_startup_cleanup_removes_only_exact_owned_model_parts(tmp_path):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    owned = model_dir / ("u2net_human_seg.onnx." + "a" * 32 + ".part")
    other_token = model_dir / "u2net_human_seg.onnx.not-a-token.part"
    other_model = model_dir / ("different.onnx." + "b" * 32 + ".part")
    unrelated = model_dir / "unrelated.part"
    for path in (owned, other_token, other_model, unrelated):
        path.write_bytes(b"fixture")

    manager, _adapter = _manager(tmp_path)

    assert not owned.exists()
    assert other_token.exists()
    assert other_model.exists()
    assert unrelated.exists()
    assert manager.cleanup_stale_parts() == 0


class _RouteManager:
    def __init__(self, *, download_supported=True):
        self.download_supported = download_supported
        self.task = {
            "id": "cutout-model-0123456789abcdef",
            "contract": MODEL_INSTALL_CONTRACT,
            "source_id": MODEL_SOURCE_ID,
            "status": "queued",
            "phase": "queued",
            "progress": 0,
            "downloaded_bytes": 0,
            "total_bytes": len(_PAYLOAD),
            "error_code": None,
            "message": "下载任务已创建",
        }

    def model_status(self):
        return {
            "contract": MODEL_INSTALL_CONTRACT,
            "source_id": MODEL_SOURCE_ID,
            "source_page": "https://github.com/danielgatis/rembg/releases/tag/v0.0.0",
            "filename": "u2net_human_seg.onnx",
            "installed": False,
            "valid": False,
            "state": "missing",
            "reason": "cutout_model_missing",
            "size_bytes": len(_PAYLOAD),
            "sha256": hashlib.sha256(_PAYLOAD).hexdigest(),
            "md5": hashlib.md5(_PAYLOAD).hexdigest(),
            "download_supported": self.download_supported,
            "install_supported": self.download_supported,
            "confirmation_required": True,
            "license": {
                "checkpoint_provenance_status": "UNVERIFIED",
                "commercial_use_status": "UNVERIFIED",
            },
            "active_task": None,
        }

    def model_projection_from_capability(self, _capability):
        return self.model_status()

    def start_download(self):
        if not self.download_supported:
            raise CutoutModelManagerError(
                "cutout_model_download_unavailable",
                "抠图模型来源和使用授权尚未验证，当前版本不支持联网下载",
                status_code=409,
            )
        return dict(self.task)

    def get_task(self, task_id):
        return dict(self.task) if task_id == self.task["id"] else None

    async def cancel_download(self, task_id):
        if task_id != self.task["id"]:
            return None
        self.task["status"] = "cancelled"
        self.task["phase"] = "cancelled"
        return dict(self.task)

    def delete_model(self):
        return {"deleted": False, "model": self.model_status()}


def _action_body(**updates):
    body = {
        "contract": MODEL_INSTALL_CONTRACT,
        "source_id": MODEL_SOURCE_ID,
        "confirmed": True,
    }
    body.update(updates)
    return body


def test_model_routes_enforce_fixed_body_and_return_public_fields(monkeypatch):
    route_manager = _RouteManager()
    monkeypatch.setattr(main, "CUTOUT_MODEL_MANAGER", route_manager)
    client = TestClient(main.app, base_url="http://testserver")

    status = client.get("/api/image-tools/cutout/model")
    assert status.status_code == 200
    assert status.json()["license"]["commercial_use_status"] == "UNVERIFIED"

    for body, code in (
        (_action_body(contract="unknown-v9"), "cutout_model_contract_unsupported"),
        (_action_body(source_id="unknown-source"), "cutout_model_source_unsupported"),
        (_action_body(confirmed=False), "cutout_model_confirmation_required"),
    ):
        response = client.post(
            "/api/image-tools/cutout/model/download",
            headers={"Origin": "http://testserver"},
            json=body,
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == code

    extra = client.post(
        "/api/image-tools/cutout/model/download",
        headers={"Origin": "http://testserver"},
        json={**_action_body(), "url": "https://evil.example", "path": "C:/private", "sha256": "0" * 64},
    )
    assert extra.status_code == 422

    unconfirmed_delete = client.post(
        "/api/image-tools/cutout/model/delete",
        headers={"Origin": "http://testserver"},
        json=_action_body(confirmed=False),
    )
    assert unconfirmed_delete.status_code == 422
    assert unconfirmed_delete.json()["detail"]["code"] == "cutout_model_confirmation_required"

    started = client.post(
        "/api/image-tools/cutout/model/download",
        headers={"Origin": "http://testserver"},
        json=_action_body(),
    )
    assert started.status_code == 202
    assert started.json() == {"ok": True, "task": route_manager.task}
    task_id = route_manager.task["id"]
    assert client.get(f"/api/image-tools/cutout/model/download/{task_id}").json() == {
        "task": route_manager.task
    }
    cancelled = client.delete(
        f"/api/image-tools/cutout/model/download/{task_id}",
        headers={"Origin": "http://testserver"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["task"]["status"] == "cancelled"
    deleted = client.post(
        "/api/image-tools/cutout/model/delete",
        headers={"Origin": "http://testserver"},
        json=_action_body(),
    )
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

    public_payload = str([status.json(), started.json(), cancelled.json(), deleted.json()])
    assert MODEL_DOWNLOAD_URL not in public_payload
    assert not any(
        PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()
        for value in [status.json()["filename"], started.json()["task"]["message"]]
    )


def test_model_mutations_keep_admin_auth_and_csrf_protection(monkeypatch):
    route_manager = _RouteManager()
    monkeypatch.setattr(main, "CUTOUT_MODEL_MANAGER", route_manager)
    monkeypatch.setattr(main, "is_prod_mode", lambda: True)
    monkeypatch.setattr(main, "verify_admin_key", lambda value: value == "test-admin-key")
    client = TestClient(main.app, base_url="http://testserver")

    unauthenticated = client.post(
        "/api/image-tools/cutout/model/download",
        headers={"Origin": "http://testserver"},
        json=_action_body(),
    )
    assert unauthenticated.status_code == 401

    cross_origin = client.post(
        "/api/image-tools/cutout/model/download",
        headers={"Origin": "http://attacker.invalid", "X-Admin-Key": "test-admin-key"},
        json=_action_body(),
    )
    assert cross_origin.status_code == 403
    assert cross_origin.json()["code"] == "CSRF_REJECTED"

    authorized = client.post(
        "/api/image-tools/cutout/model/download",
        headers={"Origin": "http://testserver", "X-Admin-Key": "test-admin-key"},
        json=_action_body(),
    )
    assert authorized.status_code == 202


def test_production_download_route_fails_closed_without_starting_task(monkeypatch):
    route_manager = _RouteManager(download_supported=False)
    monkeypatch.setattr(main, "CUTOUT_MODEL_MANAGER", route_manager)
    client = TestClient(main.app, base_url="http://testserver")

    status = client.get("/api/image-tools/cutout/model")
    response = client.post(
        "/api/image-tools/cutout/model/download",
        headers={"Origin": "http://testserver"},
        json=_action_body(),
    )

    assert status.status_code == 200
    assert status.json()["download_supported"] is False
    assert status.json()["install_supported"] is False
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "cutout_model_download_unavailable",
        "message": "抠图模型来源和使用授权尚未验证，当前版本不支持联网下载",
        "contract": MODEL_INSTALL_CONTRACT,
        "source_id": MODEL_SOURCE_ID,
    }


def test_capability_reports_download_disabled_for_production_manifest(monkeypatch):
    route_manager = _RouteManager(download_supported=False)

    class ReadyAdapter:
        adapter_id = "u2net-human-seg-onnx"

        def capabilities(self):
            return {
                "contract": "genbox-cutout-v1",
                "available": True,
                "executable": True,
                "adapters": ["u2net-human-seg-onnx"],
                "state": "ready",
            }

    monkeypatch.setattr(main, "CUTOUT_MODEL_MANAGER", route_manager)
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", CutoutAdapterRegistry([ReadyAdapter()]))

    response = TestClient(main.app, base_url="http://testserver").get(
        "/api/image-tools/cutout/capabilities"
    )

    assert response.status_code == 200
    assert response.json()["can_download"] is False
    assert response.json()["model"]["install_supported"] is False


def test_capability_keeps_legacy_fields_and_adds_model_projection(monkeypatch):
    route_manager = _RouteManager()

    class ReadyAdapter:
        adapter_id = "u2net-human-seg-onnx"

        def capabilities(self):
            return {
                "contract": "genbox-cutout-v1",
                "available": True,
                "executable": True,
                "adapters": ["u2net-human-seg-onnx"],
                "adapter": "u2net-human-seg-onnx",
                "state": "ready",
            }

    monkeypatch.setattr(main, "CUTOUT_MODEL_MANAGER", route_manager)
    monkeypatch.setattr(main, "CUTOUT_REGISTRY", CutoutAdapterRegistry([ReadyAdapter()]))

    response = TestClient(main.app, base_url="http://testserver").get(
        "/api/image-tools/cutout/capabilities"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract"] == "genbox-cutout-v1"
    assert payload["available"] is True
    assert payload["executable"] is True
    assert payload["adapters"] == ["u2net-human-seg-onnx"]
    assert payload["model"]["contract"] == MODEL_INSTALL_CONTRACT
    assert payload["model"]["source_id"] == MODEL_SOURCE_ID
    assert payload["model"]["license"]["checkpoint_provenance_status"] == "UNVERIFIED"
    assert payload["can_download"] is True
