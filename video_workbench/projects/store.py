"""Owner-bound atomic project snapshots using the existing store runtime."""

import os
from pathlib import Path
import stat
import tempfile
import uuid

from ..media import MediaIngestError
from ..media.ingest import _fail
from . import schema


class ProjectStore:
    def __init__(self, asset_service):
        self.service = asset_service
        self.root = asset_service.media.root / "projects"

    def _path(self, identity):
        identity = schema.project_id(identity)
        path = self.root / (identity + ".json")
        self.service.media._assert_confined(path, self.root)
        return path

    def create(self, owner, title, output_profile):
        self.service._owner(owner)
        clean_title = schema.title(title)
        profile = schema.output_profile(output_profile)
        with self.service._exclusive(), self.service.runtime.lock:
            self.service._ready(owner)
            identity = "prj_" + uuid.uuid4().hex
            path = self._path(identity)
            if path.exists():
                raise _fail("conflict", "publish")
            now = schema.now()
            document = {
                "schema_version": 1, "project_id": identity, "revision": 1,
                "title": clean_title, "output_profile": profile, "asset_refs": [],
                "tracks": [
                    {"track_id": "trk_picture", "kind": "picture", "clips": []},
                    {"track_id": "trk_audio", "kind": "audio", "clips": []},
                ],
                "candidate_refs": [], "created_at": now, "updated_at": now,
            }
            self._write(path, schema.encode(document))
            return document

    def read(self, owner, project_id):
        self.service._owner(owner)
        # Keep runtime ownership through the read; close must not release the
        # process lock between readiness and opening the committed snapshot.
        with self.service.runtime.lock:
            self.service._ready(owner)
            return self._read(self._path(project_id))

    def save(self, owner, project_id, expected_revision, document):
        self.service._owner(owner)
        identity = schema.project_id(project_id)
        schema.positive_revision(expected_revision, "expected_revision")
        draft = schema.validate(document, normalize_title=True)
        if draft["project_id"] != identity:
            raise schema.invalid("project_id")
        with self.service._exclusive(), self.service.runtime.lock:
            self.service._ready(owner)
            path = self._path(identity)
            previous = self._read(path)
            if expected_revision != previous["revision"] or draft["revision"] != previous["revision"]:
                raise _fail("conflict", "save", field="expected_revision")
            if any(draft[field] != previous[field] for field in ("created_at", "updated_at")):
                raise schema.invalid("timestamps")
            self._validate_assets(owner, draft["asset_refs"], previous["asset_refs"])
            draft["revision"] = previous["revision"] + 1
            # Clock adjustment must not produce an invalid chronological state.
            draft["updated_at"] = max(
                (schema.now(), previous["updated_at"]), key=schema.timestamp,
            )
            self._write(path, schema.encode(draft))
            return draft

    def _validate_assets(self, owner, refs, previous):
        retained = {(ref["asset_id"], ref["kind"], ref["digest"]) for ref in previous}
        for ref in refs:
            try:
                asset = self.service.asset(owner, ref["asset_id"])
                if (
                    asset.asset_id != ref["asset_id"] or asset.state != "ready"
                    or asset.kind != ref["kind"]
                    or "sha256:" + asset.content_sha256 != ref["digest"]
                ):
                    raise _fail("conflict", "save", field="asset_refs")
            except MediaIngestError as error:
                if error.code not in {"not_found", "conflict"} or (
                    ref["asset_id"], ref["kind"], ref["digest"],
                ) not in retained:
                    raise

    def _read(self, path):
        self.service.media._assert_confined(path, self.root)
        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            flags |= getattr(os, "O_NONBLOCK", 0)
            fd = os.open(path, flags)
            with os.fdopen(fd, "rb") as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise _fail("internal", "lookup")
                if info.st_size > schema.MAX_PROJECT_BYTES:
                    raise _fail("internal", "lookup")
                raw = handle.read(schema.MAX_PROJECT_BYTES + 1)
            document = schema.validate(schema.decode(raw))
            if document["project_id"] != path.stem:
                raise _fail("internal", "lookup")
            return document
        except FileNotFoundError:
            raise _fail("not_found", "lookup", field="project_id") from None
        except (OSError, MediaIngestError, ValueError, RecursionError):
            raise _fail("internal", "lookup") from None

    def _write(self, path, raw):
        media = self.service.media
        media._ensure_directory(self.root)
        media._assert_confined(path, self.root)
        temporary = None
        issued = None
        published = False
        try:
            fd, name = tempfile.mkstemp(prefix=".project-", suffix=".tmp", dir=self.root)
            temporary = Path(name)
            with os.fdopen(fd, "wb") as handle:
                info = os.fstat(handle.fileno())
                issued = (info.st_dev, info.st_ino)
                media._assert_confined(temporary, self.root)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            media._assert_confined(path, self.root)
            self._assert_issued(temporary, issued)
            os.replace(temporary, path)
            published = True
            temporary = None
            self._sync_directory()
        except OSError:
            if published:
                # Replacement already committed: callers must reload rather
                # than interpret a directory-sync error as a retryable save.
                raise _fail("conflict", "publish") from None
            raise _fail("disk_space", "publish", retryable=True) from None
        finally:
            if temporary is not None:
                try:
                    self._assert_issued(temporary, issued)
                    temporary.unlink()
                except FileNotFoundError:
                    pass
                except (OSError, MediaIngestError):
                    raise _fail("cleanup_pending", "cleanup", retryable=True) from None

    def _sync_directory(self):
        if os.name != "nt":
            directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

    def _assert_issued(self, path, issued):
        self.service.media._assert_confined(path, self.root)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != issued or info.st_nlink != 1:
            raise _fail("cleanup_pending", "cleanup", retryable=True)
