"""W1-1 contract checks; no routes, workers, network or Provider calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "video_workbench"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
EXAMPLES_PATH = FIXTURE_ROOT / "contract_examples.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def test_manifest_is_synthetic_and_matches_checked_in_bytes() -> None:
    manifest = _read_json(MANIFEST_PATH)
    assert manifest["manifest_version"] == 1
    assert manifest["policy"] == {
        "synthetic_only": True,
        "private_media": False,
        "network_fetch": False,
        "paid_provider_call": False,
        "source_deletion": False,
    }

    fixture_ids = set()
    for entry in manifest["fixtures"]:
        fixture_ids.add(entry["id"])
        path = FIXTURE_ROOT / entry["path"]
        assert path.is_file(), entry["id"]
        assert path.stat().st_size == entry["bytes"], entry["id"]
        assert _sha256(path) == entry["sha256"], entry["id"]
    assert len(fixture_ids) == len(manifest["fixtures"])


def test_contract_examples_match_frozen_shape() -> None:
    examples = _read_json(EXAMPLES_PATH)
    assert examples["contract_revision"] == "VIDEO-WORKBENCH-CONTRACT.md@0.2"

    asset = examples["asset_view"]
    assert asset["content_sha256"].startswith("sha256:")
    assert asset["state"] == "ready"
    assert asset["metadata"]["duration_us"] > 0

    project = examples["project_view"]
    assert project["schema_version"] == 1
    assert project["revision"] == 1
    assert [track["kind"] for track in project["tracks"]] == ["picture", "audio"]
    assert project["asset_refs"][0]["digest"] == asset["content_sha256"]

    job = examples["job_view"]
    assert job["operation"] == "import"
    assert job["progress"] is None
    assert "updated_at" in job


def test_error_and_auth_contracts_are_bounded() -> None:
    examples = _read_json(EXAMPLES_PATH)
    expected = {
        "invalid_request",
        "auth_required",
        "forbidden",
        "not_found",
        "conflict",
        "unsupported_media",
        "media_corrupt",
        "asset_too_large",
        "dimension_limit",
        "duration_limit",
        "probe_timeout",
        "dependency_missing",
        "disk_space",
        "job_not_found",
        "job_cancelled",
        "cleanup_pending",
        "provider_unavailable",
        "unsupported_capability",
        "consent_required",
        "submission_unknown",
        "remote_failed",
        "invalid_result",
        "internal",
    }
    assert set(examples["error_codes"]) == expected
    assert len(examples["auth_matrix"]) == 7
    for row in examples["auth_matrix"]:
        assert row["auth"] is True
        assert row["path_rule"]
