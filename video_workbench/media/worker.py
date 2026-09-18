"""Bounded native-worker execution; output never enters public diagnostics."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

from .errors import media_error

OUTPUT_LIMIT = 64 * 1024
_SLOTS = threading.BoundedSemaphore(2)
_RENDER_SLOT = threading.BoundedSemaphore(1)
_BOOTSTRAP = Path(__file__).with_name("worker_process.py")


@dataclass(frozen=True)
class Execution:
    job_id: str
    cancelled: threading.Event
    defer_cleanup: bool = True


_EXECUTION = ContextVar("workbench_media_execution", default=None)


@contextmanager
def execution_scope(job_id: str, cancelled: threading.Event):
    token = _EXECUTION.set(Execution(job_id, cancelled))
    try:
        check_cancelled()
        yield
    finally:
        _EXECUTION.reset(token)


def current_execution():
    return _EXECUTION.get()


def check_cancelled():
    execution = current_execution()
    if execution is not None and execution.cancelled.is_set():
        raise media_error("job_cancelled", "worker", "本地媒体任务已取消。")


class WorkerLimitError(Exception):
    pass


def run_media(
    command: list[str], *, cwd: Path, timeout: float, kind: str = "probe",
) -> subprocess.CompletedProcess:
    if kind not in {"probe", "render"} or (
        type(timeout) not in (int, float) or not math.isfinite(timeout)
        or not 0 < timeout <= (120 if kind == "render" else 10)
    ):
        raise WorkerLimitError
    check_cancelled()
    executable = shutil.which(command[0])
    if not executable or getattr(sys, "frozen", False):
        # A packaged launcher requires WB-4 verification. Never invoke a
        # desktop executable as if it were a Python interpreter.
        raise FileNotFoundError
    slots = _SLOTS if kind == "probe" else _RENDER_SLOT
    if not slots.acquire(blocking=False):
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
            [sys.executable, "-I", str(_BOOTSTRAP), kind, executable, *command[1:]],
            cwd=cwd, stdin=subprocess.PIPE,
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
            check_cancelled()
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
        check_cancelled()
        return subprocess.CompletedProcess(
            command[0], process.returncode,
            buffers[0].decode("utf-8", errors="replace"),
            buffers[1].decode("utf-8", errors="replace"),
        )
    finally:
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
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
        slots.release()
