"""Fixed, bounded tool-launch checks without exposing native output or paths."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import threading
import time

from .worker import WorkerLimitError, run_media


class MediaDiagnostics:
    def __init__(self):
        self._lock = threading.Lock()
        self._snapshot = None
        self._expires = 0.0

    @staticmethod
    def _check(tool):
        if getattr(sys, "frozen", False):
            return "unsupported_runtime"
        try:
            result = run_media([tool, "-version"], cwd=Path(__file__).parent, timeout=3)
            return "available" if result.returncode == 0 else "unavailable"
        except FileNotFoundError:
            return "missing"
        except subprocess.TimeoutExpired:
            return "timeout"
        except WorkerLimitError:
            return "unverified"
        except OSError:
            return "unavailable"

    def snapshot(self):
        # Single-flight plus a short TTL bounds native launches during polling.
        # No AssetService is created, locked or closed by startup diagnostics.
        with self._lock:
            if self._snapshot is None or time.monotonic() >= self._expires:
                tools = {tool: self._check(tool) for tool in ("ffmpeg", "ffprobe")}
                self._snapshot = {
                    "scope": "tool_launch_only",
                    "tools": tools,
                    "available": all(state == "available" for state in tools.values()),
                    "cache_ttl_seconds": 60,
                }
                self._expires = time.monotonic() + 60
            return deepcopy(self._snapshot)
