"""Synthetic subprocess evidence; never starts a provider or a user service."""

import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from video_workbench.media.errors import MediaIngestError
from video_workbench.media import worker


def wait_for(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    pytest.fail("synthetic worker did not reach expected state")


def test_cancel_before_launch_and_context_reset(tmp_path, monkeypatch):
    cancelled = threading.Event()
    cancelled.set()
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *a, **kw: pytest.fail("launched"))
    with pytest.raises(MediaIngestError) as error:
        with worker.execution_scope("synthetic", cancelled):
            worker.run_media([sys.executable, "-c", "pass"], cwd=tmp_path, timeout=5)
    assert error.value.code == "job_cancelled"
    assert worker.current_execution() is None


def test_cancel_stops_running_child_and_releases_render_slot(tmp_path):
    marker = tmp_path / "started"
    finished = tmp_path / "finished"
    code = (
        "from pathlib import Path; import time;"
        f"Path({str(marker)!r}).touch(); time.sleep(2);"
        f"Path({str(finished)!r}).touch()"
    )
    cancelled = threading.Event()
    errors = []

    def run():
        try:
            with worker.execution_scope("synthetic", cancelled):
                worker.run_media([sys.executable, "-c", code], cwd=tmp_path, timeout=5, kind="render")
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    try:
        wait_for(marker.exists)
        start = time.monotonic()
        cancelled.set()
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert time.monotonic() - start < 5
        assert len(errors) == 1 and isinstance(errors[0], MediaIngestError)
        assert errors[0].code == "job_cancelled"
        time.sleep(2.1)
        assert not finished.exists()
        assert worker.run_media(
            [sys.executable, "-c", "print('ok')"], cwd=tmp_path, timeout=5, kind="render",
        ).returncode == 0
    finally:
        cancelled.set()
        thread.join(timeout=6)


def test_parent_crash_closes_liveness_pipe_and_stops_child(tmp_path):
    marker = tmp_path / "started"
    finished = tmp_path / "finished"
    child_code = (
        "from pathlib import Path; import time;"
        f"Path({str(marker)!r}).touch(); time.sleep(2);"
        f"Path({str(finished)!r}).touch()"
    )
    repo = Path(__file__).resolve().parents[1]
    parent_code = (
        f"import sys; sys.path.insert(0, {str(repo)!r});"
        "from pathlib import Path; from video_workbench.media.worker import run_media;"
        f"run_media([sys.executable, '-c', {child_code!r}], cwd=Path({str(tmp_path)!r}), timeout=5)"
    )
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    parent = subprocess.Popen(
        [sys.executable, "-I", "-c", parent_code], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs,
    )
    try:
        wait_for(marker.exists)
        parent.kill()
        parent.wait(timeout=5)
        time.sleep(2.5)
        assert not finished.exists()
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=5)


def test_render_slot_does_not_consume_probe_slots(tmp_path):
    assert worker._RENDER_SLOT.acquire(blocking=False)
    try:
        with pytest.raises(worker.WorkerLimitError):
            worker.run_media([sys.executable, "-c", "pass"], cwd=tmp_path, timeout=5, kind="render")
        assert worker.run_media(
            [sys.executable, "-c", "pass"], cwd=tmp_path, timeout=5,
        ).returncode == 0
    finally:
        worker._RENDER_SLOT.release()


@pytest.mark.parametrize(("kind", "timeout"), [
    ("probe", 11), ("render", 121), ("other", 1), ("render", float("nan")),
    ("render", float("inf")), ("probe", True), ("render", 0),
])
def test_invalid_worker_budget_never_launches(tmp_path, kind, timeout):
    with pytest.raises(worker.WorkerLimitError):
        worker.run_media([sys.executable, "-c", "pass"], cwd=tmp_path, timeout=timeout, kind=kind)
