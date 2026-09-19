"""Local asset service for the single authenticated GenBox workspace."""

from __future__ import annotations

from contextlib import contextmanager
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import uuid

from .media import MediaIngestError, MediaIngestManager
from .media.ingest import _fail, _safe_id
from .media.worker import check_cancelled, execution_scope
from .media.proxy import ProxyRenderer
from .media.fingerprint import change_token
from .runtime import StoreRuntime
from .library import list_candidates, validate_identity
from .projects import ProjectStore


WORKSPACE_OWNER = "genbox-admin"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")
_TERMINAL = {"succeeded", "failed", "cancelled", "interrupted"}


def _now():
    return datetime.now(timezone.utc).isoformat()


class AssetService:
    """No caller-supplied path, owner, provider or remote-media identity."""

    def __init__(self, root: Path, gallery: Path, videos: Path):
        self.media = MediaIngestManager(root)
        self.gallery = Path(gallery).absolute()
        self.videos = Path(videos).absolute()
        self.jobs = self.media.root / "jobs"
        self._mutation = threading.Lock()
        self.runtime = StoreRuntime(self.media)
        self._active = {}
        self._threads = set()
        self._recovered = False
        self.proxies = ProxyRenderer(self.media)
        self._listing_cache = OrderedDict()
        self.projects = ProjectStore(self)

    def _ready(self, owner):
        self._owner(owner)
        with self.runtime.lock:
            self.runtime.acquire()
            if not self._recovered:
                self._recover()
                self._recovered = True

    def _recover(self):
        if not self.jobs.exists():
            return
        self.media._assert_confined(self.jobs, self.media.root)
        for path in self.jobs.glob("job_*.json"):
            data = self._read_job(path, WORKSPACE_OWNER)
            if data["view"]["state"] not in _TERMINAL:
                data["view"].update(state="interrupted", stage="recovery", updated_at=_now())
                self._write_job(path, data)
            self._recover_staging(path, data)

    def _recover_staging(self, path, data):
        # Only exact declared upload files are eligible. Unknown publish
        # directories and files from a pre-journal crash remain untouched.
        entries = data.get("staging", [])
        if not isinstance(entries, list) or len(entries) > 10:
            raise _fail("internal", "recovery")
        owned = []
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"directory", "file"}:
                raise _fail("internal", "recovery")
            directory, name = entry["directory"], entry["file"]
            if (
                not isinstance(directory, str) or not re.fullmatch(r"stage_[a-f0-9]{32}", directory)
                or not isinstance(name, str) or not re.fullmatch(
                    r"(?:\.upload-[a-z0-9_]+\.(?:mp4|webm|png|jpg|jpeg|webp|wav|mp3)"
                    r"|\.proxy-[a-f0-9]{32}\.(?:mp4|json))", name,
                )
            ):
                raise _fail("internal", "recovery")
            target = self.media.staging_root / directory / name
            self.media._assert_confined(target, self.media.staging_root / directory)
            if self.runtime.leased(target):
                raise _fail("cleanup_pending", "recovery", retryable=True)
            owned.append(target)
        try:
            for target in owned:
                issued = self.media._issued.get(target)
                if issued is not None:
                    self.media.cleanup_staged(issued)
                else:
                    target.unlink(missing_ok=True)
        except (OSError, MediaIngestError):
            data["view"].update(state="failed", stage="cleanup", updated_at=_now())
            self._write_job(path, data)
            return
        if entries:
            data["staging"] = []
            data["leases"] = []
            self._write_job(path, data)

    def close(self):
        with self.runtime.lock:
            for _, event in self._active.values():
                event.set()
            threads = list(self._threads)
        for thread in threads:
            thread.join(timeout=5)
        # Staging precedes a journal/active entry. Keep the process lock until
        # admission has exited as well, including synchronous import calls.
        if not self._mutation.acquire(timeout=5):
            raise _fail("cleanup_pending", "shutdown", retryable=True)
        try:
            with self.runtime.lock:
                if self._active or any(thread.is_alive() for thread in threads):
                    raise _fail("cleanup_pending", "shutdown", retryable=True)
                self.runtime.close()
        finally:
            self._mutation.release()

    @staticmethod
    def _owner(owner):
        if owner != WORKSPACE_OWNER:
            raise _fail("forbidden", "ownership")

    @contextmanager
    def _exclusive(self):
        if not self._mutation.acquire(blocking=False):
            raise _fail("conflict", "admission", field="request_id")
        try:
            yield
        finally:
            self._mutation.release()

    def _write_job(self, path, record):
        self.media._ensure_directory(self.jobs)
        self.media._assert_confined(path, self.jobs)
        temporary = None
        try:
            fd, raw = tempfile.mkstemp(prefix=".job-", suffix=".json", dir=self.jobs)
            temporary = Path(raw)
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                json.dump(record, output, ensure_ascii=True, separators=(",", ":"))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        except OSError:
            raise _fail("disk_space", "publish", retryable=True) from None
        finally:
            if temporary:
                self.media._unlink_temporary(temporary, self.jobs)

    def _read_job(self, path, owner):
        self._owner(owner)
        self.media._assert_confined(path, self.jobs)
        try:
            with path.open("rb") as handle:
                raw = handle.read(64 * 1024 + 1)
            if len(raw) > 64 * 1024:
                raise ValueError
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("owner") != owner:
                raise _fail("forbidden", "ownership")
            if (
                not isinstance(data, dict)
                or data.get("owner") != owner
                or not isinstance(data.get("view"), dict)
                or data["view"].get("job_id") != path.stem
                or not isinstance(data.get("results"), list)
            ):
                raise ValueError
            return data
        except FileNotFoundError:
            raise _fail("job_not_found", "lookup") from None
        except MediaIngestError:
            raise
        except (OSError, ValueError):
            raise _fail("internal", "lookup") from None

    def _job_path(self, request_id):
        if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
            raise _fail("invalid_request", "admission", field="request_id")
        # Stable request lookup without storing a browser string in a path.
        digest = hashlib.sha256(request_id.encode("ascii")).hexdigest()
        return self.jobs / f"job_{digest}.json"

    def _start_job(self, owner, request_id, intent):
        self._owner(owner)
        path = self._job_path(request_id)
        if path.exists():
            existing = self._read_job(path, owner)
            if existing.get("intent") != intent:
                raise _fail("conflict", "admission", field="request_id")
            if existing["view"]["state"] not in _TERMINAL and path.stem not in self._active:
                # Never replay an interrupted import. A new request ID is an
                # explicit new import; already published bytes remain intact.
                existing["view"].update(state="interrupted", stage="import", updated_at=_now())
                self._write_job(path, existing)
            return path, existing, False
        now = _now()
        data = {
            "owner": owner,
            "intent": intent,
            "view": {
                "job_id": path.stem, "operation": "import", "state": "preparing",
                "stage": "probe", "progress": None, "asset_ids": [], "project_id": None,
                "request_id": request_id, "created_at": now, "updated_at": now,
            },
            "results": [],
        }
        self._write_job(path, data)
        return path, data, True

    @staticmethod
    def _response(data):
        return {"job": dict(data["view"]), "files": list(data["results"])}

    def _for_listing(self, key, paths, verify):
        def fingerprint():
            stats = []
            for path in paths:
                self.media._reject_link(path)
                info = path.stat()
                changed = change_token(path, info)
                if changed is None:
                    return None
                stats.append((
                    info.st_dev, info.st_ino, info.st_mode, info.st_size,
                    info.st_mtime_ns, changed,
                ))
            return tuple(stats)

        try:
            before = fingerprint()
        except FileNotFoundError:
            raise _fail("not_found", "lookup", field="asset_id") from None
        with self.runtime.lock:
            cached = self._listing_cache.get(key)
            if before is not None and cached and cached[0] == before and time.monotonic() < cached[1]:
                self._listing_cache.move_to_end(key)
                return cached[2]
        result = verify()
        # Cached checks are browsing hints only, never ownership grants or
        # authority to deliver/process bytes. Sensitive paths always rehash.
        try:
            unchanged = before is not None and fingerprint() == before
        except FileNotFoundError:
            unchanged = False
        if result is not None and unchanged:
            with self.runtime.lock:
                self._listing_cache[key] = (before, time.monotonic() + 5, result)
                self._listing_cache.move_to_end(key)
                while len(self._listing_cache) > 256:
                    self._listing_cache.popitem(last=False)
        return result

    def _check_library_claim(self, intent, *, listing=False, source_index=None):
        source = intent["source"]
        resolved = self._library_path(source["kind"], source["id"], index=source_index)

        def verify():
            return self.media._hash_file(resolved)[1]

        digest = self._for_listing(
            ("library", source["kind"], source["id"]), (resolved,), verify,
        ) if listing else verify()
        if digest != source["digest"]:
            raise _fail("conflict", "lookup", field="asset_id")

    def _asset_authorized(self, owner, asset_id):
        self._owner(owner)
        _safe_id(asset_id, field="asset_id")
        if not self.jobs.exists():
            raise _fail("not_found", "lookup", field="asset_id")
        self.media._assert_confined(self.jobs, self.media.root)
        for path in self.jobs.glob("job_*.json"):
            record = self._read_job(path, owner)
            if record["intent"].get("operation") not in {"upload", "library"}:
                continue
            if any(
                result.get("asset_id") == asset_id and result.get("state") == "ready"
                for result in record["results"]
            ):
                if record["intent"]["operation"] == "library":
                    self._check_library_claim(record["intent"])
                return
        # Unclaimed/orphan assets are never exposed by a content hash.
        raise _fail("not_found", "lookup", field="asset_id")

    def asset(self, owner, asset_id):
        self._ready(owner)
        self._asset_authorized(owner, asset_id)
        directory = self.media.assets_root / asset_id
        record = self.media._read_record(directory)
        if record is None:
            raise _fail("not_found", "lookup", field="asset_id")
        return record

    def import_files(self, owner, request_id, files, *, asynchronous=False):
        self._owner(owner)
        self._job_path(request_id)
        with self._exclusive():
            self._ready(owner)
            staged = self.media.stage_batch(f"stage_{uuid.uuid4().hex}", files)
            data = None
            path = None
            created = False
            handed_off = False
            try:
                intent = {
                    "operation": "upload",
                    "files": [
                        {"digest": item.content_sha256, "kind": item.kind, "suffix": Path(item.filename).suffix.lower()}
                        for item in staged
                    ],
                }
                with self.runtime.lock:
                    path, data, created = self._start_job(owner, request_id, intent)
                if created:
                    self._prepare_execution(path, data, staged)
                    if asynchronous:
                        with self.runtime.lock:
                            response = self._response(data)
                            thread = threading.Thread(
                                target=self._background,
                                args=(self._execute_import, path, data, staged, "upload"), daemon=True,
                            )
                            self._threads.add(thread)
                            try:
                                thread.start()
                            except RuntimeError:
                                self._threads.discard(thread)
                                self._active.pop(path.stem, None)
                                data["view"].update(state="failed", stage="worker", updated_at=_now())
                                self._write_job(path, data)
                                raise _fail("internal", "worker") from None
                            handed_off = True
                        return response
                    handed_off = True
                    self._execute_import(path, data, staged, "upload")
            finally:
                if not handed_off:
                    if created and data["view"]["state"] not in _TERMINAL:
                        self._abort_preparation(path, data)
                    self._cleanup_files(staged, path, data)
            return self._response(data)

    @staticmethod
    def _background(operation, *args):
        try:
            operation(*args)
        except (MediaIngestError, OSError):
            # If even failure/cleanup persistence is unavailable, retain the
            # journal and declared files. A later read/restart marks unfinished
            # work interrupted; never replay or emit native/private error text.
            pass

    def _abort_preparation(self, path, data):
        with self.runtime.lock:
            data["view"].update(state="failed", stage="admission", updated_at=_now())
            self._write_job(path, data)

    def _prepare_execution(self, path, data, staged):
        with self.runtime.lock:
            data["staging"] = [
                {"directory": item.job_id, "file": item.path.name} for item in staged
            ]
            data["leases"] = [{"digest": item.content_sha256} for item in staged]
            data["view"].update(state="queued", stage="import", updated_at=_now())
            self._write_job(path, data)
            self._active[path.stem] = (data, threading.Event())

    def _execute_import(self, path, data, staged, origin):
        with self.runtime.lock:
            event = self._active[path.stem][1]
        try:
            with execution_scope(path.stem, event):
                with self.runtime.lock:
                    check_cancelled()
                    data["view"].update(state="preparing", stage="probe", updated_at=_now())
                    self._write_job(path, data)
                self._publish_files(path, data, staged, origin)
        except Exception as error:
            with self.runtime.lock:
                cancelled = isinstance(error, MediaIngestError) and error.code == "job_cancelled"
                safe = error if isinstance(error, MediaIngestError) else _fail("internal", "import")
                completed = {item["index"] for item in data["results"]}
                for index in range(len(staged)):
                    if index not in completed:
                        data["results"].append({"index": index, "state": "rejected", "error": safe.as_dict()})
                if len(completed) == len(staged) and data["results"]:
                    data["results"][-1]["error"] = safe.as_dict()
                data["view"].update(
                    state="cancelled" if cancelled else "failed", stage="import", updated_at=_now(),
                )
                self._write_job(path, data)
        finally:
            try:
                self._cleanup_files(staged, path, data)
            finally:
                with self.runtime.lock:
                    self._active.pop(path.stem, None)
                    self._threads.discard(threading.current_thread())

    def cancel(self, owner, job_id):
        self._ready(owner)
        self._validate_job_id(job_id)
        with self.runtime.lock:
            path = self.jobs / f"{job_id}.json"
            data = self._read_job(path, owner)
            if data["view"]["state"] in _TERMINAL:
                return self._response(data)
            active = self._active.get(job_id)
            if active is None:
                data["view"].update(state="interrupted", stage="recovery", updated_at=_now())
            else:
                data, event = active
                data["view"].update(state="cancel_requested", updated_at=_now())
                event.set()
            self._write_job(path, data)
            return self._response(data)

    def proxy(self, owner, asset_id):
        asset = self.asset(owner, asset_id)
        if asset.kind != "video":
            raise _fail("unsupported_capability", "proxy")
        derived = self.proxies.existing(asset)
        if derived is None:
            raise _fail("not_found", "proxy")
        return derived

    def prepare_proxy(self, owner, request_id, asset_id):
        self._owner(owner)
        self._job_path(request_id)
        with self._exclusive():
            asset = self.asset(owner, asset_id)
            if asset.kind != "video":
                raise _fail("unsupported_capability", "proxy")
            intent = {
                "operation": "proxy", "asset_id": asset.asset_id,
                "digest": asset.content_sha256, "preview_revision": asset.preview_revision,
            }
            with self.runtime.lock:
                path = self._job_path(request_id)
                if path.exists():
                    _, data, _ = self._start_job(owner, request_id, intent)
                    return self._response(data)
                reservation = self.proxies.reservation()
                reservation.__enter__()
                try:
                    pending, manifest = self.proxies.allocate()
                    path, data, _ = self._start_job(owner, request_id, intent)
                    data["staging"] = [
                        {"directory": item.parent.name, "file": item.name} for item in (pending, manifest)
                    ]
                    data["leases"] = [{"asset_id": asset.asset_id, "digest": asset.content_sha256}]
                    data["view"].update(operation="proxy", state="queued", stage="proxy")
                    self._write_job(path, data)
                    self._active[path.stem] = (data, threading.Event())
                    response = self._response(data)
                    thread = threading.Thread(
                        target=self._background,
                        args=(self._execute_proxy, path, data, asset, pending, manifest, reservation), daemon=True,
                    )
                    self._threads.add(thread)
                    try:
                        thread.start()
                    except RuntimeError:
                        self._threads.discard(thread)
                        self._active.pop(path.stem, None)
                        data["view"].update(state="failed", stage="worker", updated_at=_now())
                        self._write_job(path, data)
                        raise _fail("internal", "worker") from None
                    return response
                except BaseException:
                    reservation.__exit__(None, None, None)
                    raise

    def _execute_proxy(self, path, data, asset, pending, manifest, reservation):
        try:
            with execution_scope(path.stem, self._active[path.stem][1]):
                with self.runtime.lease(asset.storage_path):
                    with self.runtime.lock:
                        check_cancelled()
                        data["view"].update(state="running", stage="proxy", updated_at=_now())
                        self._write_job(path, data)
                    self.proxies.render(asset, pending, manifest)
                    with self.runtime.lock:
                        check_cancelled()
                        data["results"] = [{"index": 0, "state": "ready", "asset_id": asset.asset_id}]
                        data["view"].update(
                            state="succeeded", stage="proxy", asset_ids=[asset.asset_id], updated_at=_now(),
                        )
                        self._write_job(path, data)
        except Exception as error:
            with self.runtime.lock:
                cancelled = isinstance(error, MediaIngestError) and error.code == "job_cancelled"
                safe = error if isinstance(error, MediaIngestError) else _fail("internal", "proxy")
                data["results"] = [{"index": 0, "state": "rejected", "error": safe.as_dict()}]
                data["view"].update(state="cancelled" if cancelled else "failed", updated_at=_now())
                self._write_job(path, data)
        finally:
            try:
                with self.runtime.lock:
                    persisted = self._read_job(path, data["owner"])
                    if persisted["view"]["state"] in _TERMINAL:
                        self._recover_staging(path, persisted)
            finally:
                reservation.__exit__(None, None, None)
                with self.runtime.lock:
                    self._active.pop(path.stem, None)
                    self._threads.discard(threading.current_thread())

    def _cleanup_files(self, staged, path, data):
        if data is not None and path is not None and data.get("staging"):
            persisted = self._read_job(path, data["owner"])
            declared = {(entry["directory"], entry["file"]) for entry in persisted.get("staging", [])}
            owns_files = any((item.job_id, item.path.name) in declared for item in staged)
            if owns_files and persisted["view"]["state"] not in _TERMINAL:
                raise _fail("cleanup_pending", "cleanup", retryable=True)
        pending = []
        for index, item in enumerate(staged):
            if self.media._issued.get(item.path) is not item:
                continue
            try:
                self.media.cleanup_staged(item)
            except MediaIngestError:
                pending.append(index)
        if not pending:
            if data is not None and path is not None and data["view"]["state"] in _TERMINAL:
                with self.runtime.lock:
                    data["staging"] = []
                    data["leases"] = []
                    self._write_job(path, data)
            return
        error = _fail("cleanup_pending", "cleanup", retryable=True)
        if data is None or path is None:
            raise error
        # A ready asset remains ready and addressable. Only the cleanup stage
        # failed; a repeated request ID returns this result without republishing.
        for result in data["results"]:
            if result["index"] in pending and result["state"] == "ready":
                result["error"] = error.as_dict()
        data["view"].update(state="failed", stage="cleanup", updated_at=_now())
        self._write_job(path, data)

    def _publish_files(self, path, data, staged, origin):
        for index, item in enumerate(staged):
            check_cancelled()
            try:
                with self.runtime.lease(item.path):
                    asset = self.media.publish(item, self.media.probe(item), origin=origin)
                with self.runtime.lock:
                    data["results"].append({"index": index, "state": "ready", "asset_id": asset.asset_id})
                    data["view"]["asset_ids"].append(asset.asset_id)
            except MediaIngestError as error:
                if error.code == "job_cancelled":
                    raise
                with self.runtime.lock:
                    data["results"].append({"index": index, "state": "rejected", "error": error.as_dict()})
            with self.runtime.lock:
                data["view"]["updated_at"] = _now()
                self._write_job(path, data)
        with self.runtime.lock:
            check_cancelled()
            data["view"].update(
                state="failed" if any(item["state"] == "rejected" for item in data["results"]) else "succeeded",
                stage="import", updated_at=_now(),
            )
            self._write_job(path, data)

    def _library_path(self, kind, item_id, *, index=None):
        validate_identity(kind, item_id)
        root, suffix = (self.gallery, ".png") if kind == "image" else (self.videos, ".mp4")
        self.media._assert_confined(root, root)
        if not root.is_dir():
            raise _fail("not_found", "lookup", field="library_item_id")
        # Compare actual names, including case, instead of resolving a guessed
        # filename on case-insensitive filesystems or using substring matching.
        if index is None:
            matches = [
                item for item in root.iterdir()
                if item.stem == item_id and item.suffix == suffix
            ]
        else:
            # A list request shares only names, never a persistent ownership or
            # content decision. Confine/recheck every selected file below.
            info = root.stat()
            stamp = (info.st_dev, info.st_ino, info.st_mtime_ns)
            if kind not in index or index[kind][0] != stamp:
                names = {}
                for item in root.iterdir():
                    if item.suffix == suffix:
                        names[item.stem] = item if item.stem not in names else None
                after = root.stat()
                if stamp != (after.st_dev, after.st_ino, after.st_mtime_ns):
                    raise _fail("conflict", "lookup", field="library_item_id")
                index[kind] = (stamp, names)
            candidate = index[kind][1].get(item_id)
            matches = [candidate] if candidate is not None else []
        if len(matches) != 1:
            raise _fail("not_found", "lookup", field="library_item_id")
        path = matches[0]
        self.media._assert_confined(path, root)
        if not path.is_file():
            raise _fail("not_found", "lookup", field="library_item_id")
        return path

    def library_candidates(self, owner, **parameters):
        return list_candidates(self, owner, **parameters)

    def library_preview(self, owner, *, library_kind, library_item_id, cancelled=None):
        self._owner(owner)
        validate_identity(library_kind, library_item_id)
        event = cancelled if cancelled is not None else threading.Event()
        operation_id = f"preview_{uuid.uuid4().hex}"
        staged = None
        cleanup_pending = False
        with self._exclusive():
            self._ready(owner)
            with self.runtime.lock:
                self._active[operation_id] = (owner, event)
            try:
                with execution_scope(operation_id, event):
                    source = self._library_path(library_kind, library_item_id)
                    with source.open("rb") as handle:
                        staged = self.media.stage_stream(
                            f"stage_{uuid.uuid4().hex}", "candidate" + source.suffix, handle,
                        )
                    with self.runtime.lease(staged.path):
                        self.media.probe(staged)
                        content = self.media.preview_staged(staged)
                        current = self._library_path(library_kind, library_item_id)
                        if self.media._hash_file(current) != (staged.byte_length, staged.content_sha256):
                            raise _fail("conflict", "lookup", field="library_item_id")
                    check_cancelled()
                    return content, "sha256:" + staged.content_sha256
            except MediaIngestError as error:
                # A failed derivative cleanup retains its input reservation;
                # never free the allowance while owned output remains on disk.
                cleanup_pending = error.code == "cleanup_pending"
                raise
            finally:
                try:
                    if staged is not None and not cleanup_pending:
                        self.media.cleanup_staged(staged)
                finally:
                    with self.runtime.lock:
                        self._active.pop(operation_id, None)

    def register_library(self, owner, request_id, *, library_kind, library_item_id, expected_sha256=None):
        self._owner(owner)
        self._job_path(request_id)
        if expected_sha256 is not None and (
            not isinstance(expected_sha256, str) or not _DIGEST.fullmatch(expected_sha256)
        ):
            raise _fail("invalid_request", "admission", field="expected_sha256")
        with self._exclusive():
            self._ready(owner)
            source = self._library_path(library_kind, library_item_id)
            with source.open("rb") as handle:
                staged = self.media.stage_stream(f"stage_{uuid.uuid4().hex}", source.name, handle)
            data = None
            path = None
            created = False
            try:
                if expected_sha256 and expected_sha256 != "sha256:" + staged.content_sha256:
                    raise _fail("conflict", "admission", field="expected_sha256")
                intent = {
                    "operation": "library",
                    "source": {"kind": library_kind, "id": library_item_id, "digest": staged.content_sha256},
                }
                path, data, created = self._start_job(owner, request_id, intent)
                if created:
                    # Recheck the exact source, not only the copied bytes.
                    if self.media._hash_file(source)[1] != staged.content_sha256:
                        raise _fail("conflict", "admission", field="library_item_id")
                    self._prepare_execution(path, data, [staged])
                    self._execute_import(path, data, [staged], "library")
            finally:
                if created and data["view"]["state"] not in _TERMINAL:
                    self._abort_preparation(path, data)
                self._cleanup_files([staged], path, data)
            return self._response(data)

    @staticmethod
    def _validate_job_id(job_id):
        _safe_id(job_id, field="job_id")
        if not re.fullmatch(r"job_[0-9a-f]{64}", job_id):
            raise _fail("job_not_found", "lookup")

    def job(self, owner, job_id):
        self._ready(owner)
        self._validate_job_id(job_id)
        with self.runtime.lock:
            data = self._read_job(self.jobs / f"{job_id}.json", owner)
            if data["view"]["state"] not in _TERMINAL and job_id not in self._active:
                data["view"].update(state="interrupted", stage="recovery", updated_at=_now())
                path = self.jobs / f"{job_id}.json"
                self._write_job(path, data)
                self._recover_staging(path, data)
            return self._response(data)

    def list_assets(self, owner, *, cursor="", kind=None, query="", limit=20):
        self._ready(owner)
        if kind not in {None, "image", "video", "audio"} or (
            type(limit) is not int or not 1 <= limit <= 50
            or not isinstance(query, str) or len(query) > 128
        ):
            raise _fail("invalid_request", "admission")
        if cursor:
            _safe_id(cursor, field="cursor")
        claims = {}
        if self.jobs.exists():
            self.media._assert_confined(self.jobs, self.media.root)
            for path in self.jobs.glob("job_*.json"):
                data = self._read_job(path, owner)
                if data["intent"].get("operation") not in {"upload", "library"}:
                    continue
                for item in data["results"]:
                    if item.get("state") == "ready":
                        asset_id = _safe_id(item["asset_id"], field="asset_id")
                        claims.setdefault(asset_id, data["intent"])
        selected = []
        source_index = {}
        for asset_id in sorted(claims):
            if asset_id <= cursor or query.casefold() not in asset_id.casefold():
                continue
            try:
                directory = self.media.assets_root / asset_id
                self.media._assert_confined(directory, self.media.assets_root)
                # Reject nonmatching kinds using bounded manifest parsing;
                # metadata alone is never added to the response.
                metadata = self.media._read_record(directory, verify_content=False)
                if metadata is None or (kind is not None and metadata.kind != kind):
                    continue
                record = self._for_listing(
                    ("asset", asset_id),
                    (directory, directory / "asset.json", directory / "original"),
                    lambda: self.media._read_record(directory),
                )
                if record is None or record != metadata:
                    continue
                if claims[asset_id]["operation"] == "library":
                    self._check_library_claim(claims[asset_id], listing=True, source_index=source_index)
            except MediaIngestError as error:
                if error.code in {"not_found", "conflict"}:
                    continue
                raise
            if kind is None or record.kind == kind:
                selected.append(record.as_view())
            if len(selected) > limit:
                break
        return {
            "items": selected[:limit],
            "next_cursor": selected[limit - 1]["asset_id"] if len(selected) > limit else None,
        }
