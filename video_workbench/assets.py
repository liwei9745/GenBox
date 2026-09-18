"""Local asset service for the single authenticated GenBox workspace."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import uuid

from .media import MediaIngestError, MediaIngestManager
from .media.ingest import _fail, _safe_id


WORKSPACE_OWNER = "genbox-admin"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")


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
            if existing["view"]["state"] not in {"succeeded", "failed"}:
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

    def _asset_authorized(self, owner, asset_id):
        self._owner(owner)
        _safe_id(asset_id, field="asset_id")
        if not self.jobs.exists():
            raise _fail("not_found", "lookup", field="asset_id")
        self.media._assert_confined(self.jobs, self.media.root)
        for path in self.jobs.glob("job_*.json"):
            record = self._read_job(path, owner)
            if any(
                result.get("asset_id") == asset_id and result.get("state") == "ready"
                for result in record["results"]
            ):
                if record["intent"]["operation"] == "library":
                    source = record["intent"]["source"]
                    resolved = self._library_path(source["kind"], source["id"])
                    if self.media._hash_file(resolved)[1] != source["digest"]:
                        raise _fail("conflict", "lookup", field="asset_id")
                return
        # Unclaimed/orphan assets are never exposed by a content hash.
        raise _fail("not_found", "lookup", field="asset_id")

    def asset(self, owner, asset_id):
        self._asset_authorized(owner, asset_id)
        directory = self.media.assets_root / asset_id
        record = self.media._read_record(directory)
        if record is None:
            raise _fail("not_found", "lookup", field="asset_id")
        return record

    def import_files(self, owner, request_id, files):
        self._owner(owner)
        self._job_path(request_id)
        with self._exclusive():
            staged = self.media.stage_batch(f"stage_{uuid.uuid4().hex}", files)
            data = None
            path = None
            try:
                intent = {
                    "operation": "upload",
                    "files": [
                        {"digest": item.content_sha256, "kind": item.kind, "suffix": Path(item.filename).suffix.lower()}
                        for item in staged
                    ],
                }
                path, data, created = self._start_job(owner, request_id, intent)
                if created:
                    self._publish_files(path, data, staged, "upload")
            finally:
                self._cleanup_files(staged, path, data)
            return self._response(data)

    def _cleanup_files(self, staged, path, data):
        pending = []
        for index, item in enumerate(staged):
            if self.media._issued.get(item.path) is not item:
                continue
            try:
                self.media.cleanup_staged(item)
            except MediaIngestError:
                pending.append(index)
        if not pending:
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
            try:
                asset = self.media.publish(item, self.media.probe(item), origin=origin)
                data["results"].append({"index": index, "state": "ready", "asset_id": asset.asset_id})
                data["view"]["asset_ids"].append(asset.asset_id)
            except MediaIngestError as error:
                data["results"].append({"index": index, "state": "rejected", "error": error.as_dict()})
            data["view"]["updated_at"] = _now()
            self._write_job(path, data)
        data["view"].update(
            state="failed" if any(item["state"] == "rejected" for item in data["results"]) else "succeeded",
            stage="import", updated_at=_now(),
        )
        self._write_job(path, data)

    def _library_path(self, kind, item_id):
        if kind not in {"image", "video"} or (
            not isinstance(item_id, str) or not 0 < len(item_id) <= 255
            or item_id in {".", ".."} or any(char in item_id for char in "/\\:\x00")
            or any(ord(char) < 32 for char in item_id)
        ):
            raise _fail("invalid_request", "admission", field="library_item_id")
        root, suffix = (self.gallery, ".png") if kind == "image" else (self.videos, ".mp4")
        self.media._assert_confined(root, root)
        if not root.is_dir():
            raise _fail("not_found", "lookup", field="library_item_id")
        # Compare actual names, including case, instead of resolving a guessed
        # filename on case-insensitive filesystems or using substring matching.
        matches = [
            item for item in root.iterdir()
            if item.stem == item_id and item.suffix == suffix
        ]
        if len(matches) != 1:
            raise _fail("not_found", "lookup", field="library_item_id")
        path = matches[0]
        self.media._assert_confined(path, root)
        if not path.is_file():
            raise _fail("not_found", "lookup", field="library_item_id")
        return path

    def register_library(self, owner, request_id, *, library_kind, library_item_id, expected_sha256=None):
        self._owner(owner)
        self._job_path(request_id)
        if expected_sha256 is not None and (
            not isinstance(expected_sha256, str) or not _DIGEST.fullmatch(expected_sha256)
        ):
            raise _fail("invalid_request", "admission", field="expected_sha256")
        with self._exclusive():
            source = self._library_path(library_kind, library_item_id)
            with source.open("rb") as handle:
                staged = self.media.stage_stream(f"stage_{uuid.uuid4().hex}", source.name, handle)
            data = None
            path = None
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
                    self._publish_files(path, data, [staged], "library")
            finally:
                self._cleanup_files([staged], path, data)
            return self._response(data)

    def job(self, owner, job_id):
        _safe_id(job_id, field="job_id")
        if not re.fullmatch(r"job_[0-9a-f]{64}", job_id):
            raise _fail("job_not_found", "lookup")
        data = self._read_job(self.jobs / f"{job_id}.json", owner)
        if data["view"]["state"] == "preparing" and not self._mutation.locked():
            # Read projection only: safe across reload; no implicit replay.
            data["view"]["state"] = "interrupted"
        return self._response(data)

    def list_assets(self, owner, *, cursor="", kind=None, query="", limit=20):
        self._owner(owner)
        if kind not in {None, "image", "video", "audio"} or (
            type(limit) is not int or not 1 <= limit <= 50
            or not isinstance(query, str) or len(query) > 128
        ):
            raise _fail("invalid_request", "admission")
        if cursor:
            _safe_id(cursor, field="cursor")
        ids = set()
        if self.jobs.exists():
            self.media._assert_confined(self.jobs, self.media.root)
            for path in self.jobs.glob("job_*.json"):
                data = self._read_job(path, owner)
                ids.update(item["asset_id"] for item in data["results"] if item.get("state") == "ready")
        selected = []
        for asset_id in sorted(ids):
            if asset_id <= cursor or query.casefold() not in asset_id.casefold():
                continue
            try:
                record = self.asset(owner, asset_id)
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
