"""Before-journal interruption retains unknown files and closes owned spools."""

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from starlette.datastructures import Headers
from starlette.requests import ClientDisconnect

from video_workbench.assets import AssetService, WORKSPACE_OWNER
from video_workbench.multipart import MediaMultipartParser
from test_video_workbench_api import FIXTURES


@pytest.mark.parametrize("failure", [ClientDisconnect, asyncio.CancelledError])
def test_multipart_disconnect_or_cancellation_closes_all_created_spools(failure):
    async def interrupted():
        yield (
            b'--synthetic\r\nContent-Disposition: form-data; name="files"; '
            b'filename="still.png"\r\nContent-Type: image/png\r\n\r\n'
            + b"x" * (1024 * 1024 + 1)
        )
        raise failure()

    parser = MediaMultipartParser(
        Headers({"content-type": "multipart/form-data; boundary=synthetic"}), interrupted(),
    )

    async def run():
        with pytest.raises(failure):
            await parser.parse()

    asyncio.run(run())
    assert parser._files_to_close_on_error
    assert all(handle.closed for handle in parser._files_to_close_on_error)


def test_real_process_crash_before_journal_retains_unclaimed_stage_without_exposure(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path / "store"
    marker = tmp_path / "staging-started"
    code = f"""
import sys, time
from pathlib import Path
sys.path.insert(0, {str(repo)!r})
from video_workbench.assets import AssetService, WORKSPACE_OWNER
s = AssetService(Path({str(root)!r}), Path({str(tmp_path / 'gallery')!r}), Path({str(tmp_path / 'videos')!r}))
def chunks():
    yield b'synthetic incomplete image'
    Path({str(marker)!r}).write_text('ready')
    time.sleep(60)
s.import_files(WORKSPACE_OWNER, 'prejournal', [('still.png', chunks())])
"""
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", code], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs,
    )
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        process.kill()
        process.wait(timeout=5)
        remnants = list(root.glob("staging/*/.upload-*"))
        assert len(remnants) == 1
        before = remnants[0].read_bytes()
        unknown = remnants[0].parent / "unknown.txt"
        unknown.write_bytes(b"retain")
        restored = AssetService(root, tmp_path / "gallery", tmp_path / "videos")
        try:
            assert restored.list_assets(WORKSPACE_OWNER)["items"] == []
            assert not restored.jobs.exists()
            assert remnants[0].read_bytes() == before
            assert unknown.read_bytes() == b"retain"
            completed = restored.import_files(
                WORKSPACE_OWNER, "explicit_new", [("still.png", (FIXTURES / "still.png").read_bytes())],
            )
            assert completed["job"]["state"] == "succeeded"
            assert remnants[0].read_bytes() == before
            assert not restored._active
        finally:
            restored.close()
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
