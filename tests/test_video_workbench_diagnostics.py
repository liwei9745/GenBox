"""Dependency health is bounded, authenticated and independent of media stores."""

from concurrent.futures import ThreadPoolExecutor
import subprocess
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from video_workbench.api import build_router
from video_workbench.media import diagnostics
from video_workbench.media.worker import WorkerLimitError


def test_diagnostics_startup_auth_redaction_and_single_flight(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        time.sleep(0.01)
        return subprocess.CompletedProcess(command, 0, "synthetic private path", "private build flags")

    monkeypatch.setattr(diagnostics, "run_media", run)
    app = FastAPI()

    def no_store():
        pytest.fail("diagnostics must not resolve a media store")

    app.include_router(build_router(no_store, lambda: "synthetic-key", lambda: []))
    with TestClient(app) as client:
        assert len(calls) == 2
        assert client.get("/api/video-workbench/diagnostics").status_code == 401
        headers = {"X-Admin-Key": "synthetic-key"}
        assert client.get("/api/video-workbench/diagnostics?command=untrusted", headers=headers).status_code == 422
        response = client.get("/api/video-workbench/diagnostics", headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        assert response.json() == {
            "scope": "tool_launch_only", "tools": {"ffmpeg": "available", "ffprobe": "available"},
            "available": True, "cache_ttl_seconds": 60,
        }
        assert "private" not in response.text
    assert len(calls) == 2
    assert [item[0] for item in calls] == [["ffmpeg", "-version"], ["ffprobe", "-version"]]
    assert all(item[1]["timeout"] == 3 for item in calls)
    cache = diagnostics.MediaDiagnostics()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: cache.snapshot(), range(8)))
    assert len(calls) == 4
    results[0]["tools"]["ffmpeg"] = "altered"
    assert cache.snapshot()["tools"]["ffmpeg"] == "available"
    cache._expires = 0
    cache.snapshot()
    assert len(calls) == 6


@pytest.mark.parametrize("error,state", [
    (FileNotFoundError("private"), "missing"),
    (subprocess.TimeoutExpired("private", 3), "timeout"),
    (WorkerLimitError("private"), "unverified"),
    (PermissionError("private"), "unavailable"),
])
def test_diagnostics_failure_classification(monkeypatch, error, state):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(diagnostics, "run_media", fail)
    result = diagnostics.MediaDiagnostics().snapshot()
    assert result["tools"] == {"ffmpeg": state, "ffprobe": state}
    assert not result["available"]
    assert "private" not in str(result)


def test_packaged_diagnostics_do_not_claim_missing_or_launch(monkeypatch):
    monkeypatch.setattr(diagnostics.sys, "frozen", True, raising=False)
    monkeypatch.setattr(diagnostics, "run_media", lambda *a, **kw: pytest.fail("must not launch"))
    result = diagnostics.MediaDiagnostics().snapshot()
    assert set(result["tools"].values()) == {"unsupported_runtime"}
    assert not result["available"]


def test_nonzero_exit_is_not_available(monkeypatch):
    monkeypatch.setattr(
        diagnostics, "run_media", lambda *a, **kw: subprocess.CompletedProcess("tool", 1, "", "private"),
    )
    assert set(diagnostics.MediaDiagnostics().snapshot()["tools"].values()) == {"unavailable"}
