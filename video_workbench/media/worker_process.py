"""Private native-worker bootstrap. Never accepts arguments from HTTP callers."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import signal


MEMORY_BYTES = 1024 * 1024 * 1024
MAX_OUTPUT_FILE_BYTES = 4 * 1024 * 1024


def _windows_job():
    """Place this launcher and its child in a kill-on-close resource job."""
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IOCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimits),
            ("IoInfo", IOCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    handle = kernel.CreateJobObjectW(None, None)
    limits = ExtendedLimits()
    # JOB_MEMORY | ACTIVE_PROCESS | KILL_ON_JOB_CLOSE.
    limits.BasicLimitInformation.LimitFlags = 0x200 | 0x8 | 0x2000
    limits.BasicLimitInformation.ActiveProcessLimit = 2
    limits.JobMemoryLimit = MEMORY_BYTES
    if not handle or not kernel.SetInformationJobObject(
        handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
    ) or not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        raise OSError("worker isolation unavailable")
    # The launcher exclusively owns the handle. Terminating it closes the job
    # and terminates the native child as well; the child cannot inherit it.
    return handle


def main() -> int:
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    command = sys.argv[2:]
    if not command or kind not in {"probe", "render"}:
        return 125
    try:
        if os.name == "nt":
            job_handle = _windows_job()
        else:
            import resource

            cpu_seconds = 120 if kind == "render" else 10
            output_bytes = 512 * 1024 * 1024 if kind == "render" else MAX_OUTPUT_FILE_BYTES
            resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            resource.setrlimit(resource.RLIMIT_FSIZE, (output_bytes, output_bytes))
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

        def watch_parent():
            # The application owns the write end. EOF also occurs on a crash,
            # so no stale PID lookup or unrelated-process termination is needed.
            while os.read(sys.stdin.fileno(), 1):
                pass
            if os.name != "nt" and os.getpgrp() == os.getpid():
                os.killpg(os.getpgrp(), signal.SIGKILL)
            os._exit(125)

        threading.Thread(target=watch_parent, daemon=True).start()
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL)
        return child.wait()
    except (OSError, ValueError):
        return 125
    return 125


if __name__ == "__main__":
    raise SystemExit(main())
