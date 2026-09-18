"""Authenticated local-only WB-1 media routes, isolated from generation APIs."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from .assets import WORKSPACE_OWNER
from .media import MediaIngestError
from .media.diagnostics import MediaDiagnostics
from .media.ingest import _fail
from .multipart import MediaMultipartParser


PREFIX = "/api/video-workbench"
_BODY_LIMIT = 1024 * 1024 * 1024 + 64 * 1024
_UPLOAD_SLOTS = threading.BoundedSemaphore(2)
_STATUS = {
    "auth_required": 401, "forbidden": 403, "not_found": 404,
    "job_not_found": 404, "conflict": 409, "asset_too_large": 413,
    "dependency_missing": 503, "disk_space": 507, "internal": 500,
}


def problem_response(code, stage="admission"):
    error = _fail(code, stage)
    return JSONResponse({"error": error.as_dict()}, status_code=_STATUS.get(code, 422))


def _origin(value):
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        return parsed.scheme, parsed.hostname.lower(), parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None


def build_router(get_service, get_admin_key, allowed_origins):
    used_services = set()
    diagnostics = MediaDiagnostics()

    def resolve_service():
        service = get_service()
        used_services.add(service)
        return service

    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(diagnostics.snapshot)
        try:
            yield
        finally:
            for service in tuple(used_services):
                await run_in_threadpool(service.close)
                used_services.discard(service)

    class WorkbenchRoute(APIRoute):
        def get_route_handler(self):
            endpoint = super().get_route_handler()

            async def guarded(request: Request):
                try:
                    # Existing app has one admin workspace, not per-user
                    # tenancy. Never treat dev-mode bypass as an identity.
                    stored = get_admin_key()
                    supplied = request.headers.get("x-admin-key", "")
                    if not stored or not secrets.compare_digest(supplied.encode(), stored.encode()):
                        return problem_response("auth_required", "auth")
                    if request.method not in {"GET", "HEAD", "OPTIONS"}:
                        source = request.headers.get("origin") or request.headers.get("referer", "")
                        trusted = {_origin(str(request.base_url)), *(_origin(value) for value in allowed_origins())}
                        if _origin(source) is None or _origin(source) not in trusted:
                            return problem_response("auth_required", "auth")
                        if request.headers.get("sec-fetch-site") == "cross-site":
                            return problem_response("auth_required", "auth")
                    return await endpoint(request)
                except MediaIngestError as error:
                    return JSONResponse(
                        {"error": error.as_dict()}, status_code=_STATUS.get(error.code, 422),
                    )
                except (OSError, ValueError, TypeError, KeyError):
                    return problem_response("internal", "import")
            return guarded

    router = APIRouter(prefix=PREFIX, route_class=WorkbenchRoute, lifespan=lifespan)

    def no_query(request):
        if request.query_params:
            raise _fail("invalid_request", "admission")

    @router.get("/diagnostics")
    async def media_diagnostics(request: Request):
        no_query(request)
        snapshot = await run_in_threadpool(diagnostics.snapshot)
        return JSONResponse(snapshot, headers={"Cache-Control": "private, no-store"})

    @router.post("/imports")
    async def import_external(request: Request):
        no_query(request)
        if not _UPLOAD_SLOTS.acquire(blocking=False):
            raise _fail("conflict", "admission")
        original_receive = request._receive
        too_large = False
        total = 0
        try:
            service = resolve_service()
            service.media._ensure_directory(service.media.root)
            # Multipart spooling and owned staging coexist during this call.
            # Admit only when both temporary allowances are available.
            if shutil.disk_usage(service.media.root).free < 2 * 1024 * 1024 * 1024:
                raise _fail("disk_space", "staging", retryable=True)
            content_length = request.headers.get("content-length")
            if content_length is not None and (
                not content_length.isdecimal() or len(content_length) > 16
                or int(content_length) > _BODY_LIMIT
            ):
                raise _fail("asset_too_large", "admission")
            content_type = request.headers.get("content-type", "")
            if len(content_type) > 512 or not content_type.lower().startswith("multipart/form-data;"):
                raise _fail("invalid_request", "admission")

            async def bounded_receive():
                nonlocal total, too_large
                message = await original_receive()
                if message["type"] == "http.request":
                    total += len(message.get("body", b""))
                    if total > _BODY_LIMIT:
                        too_large = True
                        # Starlette closes spooled files on MultiPartException.
                        raise MultiPartException("body limit")
                return message

            request._receive = bounded_receive
            parser = MediaMultipartParser(
                request.headers, request.stream(), max_files=10, max_fields=1, max_part_size=1024,
            )
            try:
                form = await parser.parse()
                try:
                    entries = form.multi_items()
                    ids = [value for name, value in entries if name == "request_id" and isinstance(value, str)]
                    files = [value for name, value in entries if name == "files" and isinstance(value, UploadFile)]
                    if len(ids) != 1 or not files or len(entries) != len(files) + 1:
                        raise _fail("invalid_request", "admission")
                    return await run_in_threadpool(
                        service.import_files, WORKSPACE_OWNER, ids[0],
                        [(item.filename, item.file) for item in files],
                        asynchronous=request.headers.get("prefer", "").lower() == "respond-async",
                    )
                finally:
                    await form.close()
            except (HTTPException, MultiPartException):
                raise _fail("asset_too_large" if too_large or parser.size_exceeded else "invalid_request", "admission") from None
        finally:
            request._receive = original_receive
            _UPLOAD_SLOTS.release()

    @router.post("/library")
    async def register_library(request: Request):
        no_query(request)
        payload = bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload) > 4096:
                raise _fail("invalid_request", "admission")
        try:
            body = json.loads(payload)
        except ValueError:
            raise _fail("invalid_request", "admission") from None
        if not isinstance(body, dict) or set(body) - {
            "library_kind", "library_item_id", "expected_sha256",
        } or not {"library_kind", "library_item_id"} <= set(body):
            raise _fail("invalid_request", "admission")
        request_id = request.headers.get("x-request-id", "")
        return await run_in_threadpool(
            resolve_service().register_library, WORKSPACE_OWNER, request_id, **body,
        )

    @router.get("/assets")
    async def list_assets(request: Request):
        parameters = request.query_params
        if set(parameters) - {"cursor", "kind", "query", "limit"} or len(parameters.multi_items()) != len(parameters):
            raise _fail("invalid_request", "admission")
        try:
            limit = int(parameters.get("limit", "20"))
        except ValueError:
            raise _fail("invalid_request", "admission", field="limit") from None
        return await run_in_threadpool(
            resolve_service().list_assets, WORKSPACE_OWNER,
            cursor=parameters.get("cursor", ""), kind=parameters.get("kind"),
            query=parameters.get("query", ""), limit=limit,
        )

    @router.get("/assets/{asset_id}")
    async def asset_view(asset_id: str, request: Request):
        no_query(request)
        asset = await run_in_threadpool(resolve_service().asset, WORKSPACE_OWNER, asset_id)
        return asset.as_view()

    @router.get("/jobs/{job_id}")
    async def job_view(job_id: str, request: Request):
        no_query(request)
        return await run_in_threadpool(resolve_service().job, WORKSPACE_OWNER, job_id)

    @router.post("/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str, request: Request):
        no_query(request)
        async for chunk in request.stream():
            if chunk:
                raise _fail("invalid_request", "admission")
        return await run_in_threadpool(resolve_service().cancel, WORKSPACE_OWNER, job_id)

    @router.post("/assets/{asset_id}/proxy")
    async def prepare_proxy(asset_id: str, request: Request):
        no_query(request)
        async for chunk in request.stream():
            if chunk:
                raise _fail("invalid_request", "admission")
        result = await run_in_threadpool(
            resolve_service().prepare_proxy, WORKSPACE_OWNER, request.headers.get("x-request-id", ""), asset_id,
        )
        return JSONResponse(result, status_code=202)

    @router.get("/assets/{asset_id}/proxy")
    async def proxy_content(asset_id: str, request: Request):
        no_query(request)
        service = resolve_service()
        derived = await run_in_threadpool(service.proxy, WORKSPACE_OWNER, asset_id)
        return _leased_response(service, derived.path, "video/mp4", request, asset_id + "-preview.mp4")

    @router.get("/assets/{asset_id}/thumbnail")
    async def thumbnail(asset_id: str, request: Request):
        no_query(request)
        service = resolve_service()
        asset = await run_in_threadpool(service.asset, WORKSPACE_OWNER, asset_id)
        with service.runtime.lease(asset.storage_path):
            derived = await run_in_threadpool(service.media.derive_thumbnail, asset)
        return _leased_response(service, derived.path, "image/jpeg", request, asset_id + ".jpg")

    @router.get("/assets/{asset_id}/content")
    async def asset_content(asset_id: str, request: Request):
        no_query(request)
        service = resolve_service()
        asset = await run_in_threadpool(service.asset, WORKSPACE_OWNER, asset_id)
        mime = {
            "mp4": "video/mp4", "webm": "video/webm", "png": "image/png",
            "jpeg": "image/jpeg", "webp": "image/webp", "mp3": "audio/mpeg", "wav": "audio/wav",
        }[asset.metadata.format]
        return _leased_response(service, asset.storage_path, mime, request, asset_id + "." + asset.metadata.format)

    return router


def _leased_response(service, path, mime, request, filename):
    lease = service.runtime.lease(path)
    lease.__enter__()
    try:
        return _media_response(path, mime, request, filename, release=lambda: lease.__exit__(None, None, None))
    except BaseException:
        lease.__exit__(None, None, None)
        raise


class _OwnedStreamingResponse(StreamingResponse):
    def __init__(self, *args, close, **kwargs):
        self._close = close
        super().__init__(*args, **kwargs)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            # Disconnect may happen before the generator's first iteration.
            self._close()


def _media_response(path, mime, request, filename, release=lambda: None):
    handle = path.open("rb")
    close_lock = threading.Lock()
    closed = False

    def close():
        nonlocal closed
        with close_lock:
            if not closed:
                closed = True
                try:
                    handle.close()
                finally:
                    release()
    try:
        size = os.fstat(handle.fileno()).st_size
        start, end = 0, size - 1
        raw_range = request.headers.get("range", "")
        if raw_range:
            match = re.fullmatch(r"bytes=([0-9]{0,16})-([0-9]{0,16})", raw_range)
            if not match or not any(match.groups()):
                raise ValueError
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(end, int(last)) if last else end
            else:
                start = max(0, size - int(last))
            if start > end or start >= size:
                raise ValueError
        handle.seek(start)
    except ValueError:
        close()
        return JSONResponse(
            {"error": _fail("invalid_request", "lookup").as_dict()},
            status_code=416, headers={"Content-Range": f"bytes */{size}"},
        )
    except Exception:
        close()
        raise

    def chunks():
        remaining = end - start + 1
        try:
            while remaining > 0:
                chunk = handle.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            close()

    headers = {
        "Accept-Ranges": "bytes", "Content-Length": str(end - start + 1),
        "Cache-Control": "private, no-store",
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    if raw_range:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return _OwnedStreamingResponse(
        chunks(), media_type=mime, headers=headers, status_code=206 if raw_range else 200,
        background=BackgroundTask(close), close=close,
    )
