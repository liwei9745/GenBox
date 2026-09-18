"""Bounded native-worker execution; output never enters public diagnostics."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time


OUTPUT_LIMIT = 64 * 1024
_SLOTS = threading.BoundedSemaphore(2)
_BOOTSTRAP = Path(__file__).with_name("worker_process.py")


class WorkerLimitError(Exception):
    pass


def run_media(command: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess:
    executable = shutil.which(command[0])
    if not executable or getattr(sys, "frozen", False):
        # A packaged launcher requires WB-4 verification. Never invoke a
        # desktop executable as if it were a Python interpreter.
        raise FileNotFoundError
    if not _SLOTS.acquire(blocking=False):
        raise WorkerLimitError
    process = None
    readers = []
    buffers = [bytearray(), bytearray()]
    overflow = threading.Event()
    try:
        kwargs = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": subprocess.CREATE_NO_WINDOW,
        }
        process = subprocess.Popen(
            [sys.executable, "-I", str(_BOOTSTRAP), executable, *command[1:]],
            cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs,
        )

        def drain(pipe, buffer):
            try:
                while chunk := pipe.read(4096):
                    room = OUTPUT_LIMIT - len(buffer)
                    buffer.extend(chunk[:room])
                    if len(chunk) > room:
                        overflow.set()
            finally:
                pipe.close()

        for pipe, buffer in zip((process.stdout, process.stderr), buffers):
            reader = threading.Thread(target=drain, args=(pipe, buffer), daemon=True)
            reader.start()
            readers.append(reader)
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if overflow.wait(0.01):
                raise WorkerLimitError
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(command[0], timeout)
        for reader in readers:
            reader.join(timeout=max(0, deadline - time.monotonic()))
        if any(reader.is_alive() for reader in readers):
            raise subprocess.TimeoutExpired(command[0], timeout)
        if overflow.is_set() or process.returncode == 125:
            raise WorkerLimitError
        return subprocess.CompletedProcess(
            command[0], process.returncode,
            buffers[0].decode("utf-8", errors="replace"),
            buffers[1].decode("utf-8", errors="replace"),
        )
    finally:
        if process is not None:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            process.wait()
            for reader in readers:
                reader.join(timeout=1)
        _SLOTS.release()
