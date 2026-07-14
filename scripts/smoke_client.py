"""Launch a packaged GenBox client and verify its local HTTP endpoint."""

from __future__ import annotations

import argparse
import os
import signal
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    source = args.executable.resolve()
    if not source.is_file():
        raise SystemExit(f"Executable not found: {source}")

    with tempfile.TemporaryDirectory(prefix="genbox-smoke-", ignore_cleanup_errors=True) as temporary:
        workdir = Path(temporary)
        executable = workdir / source.name
        shutil.copy2(source, executable)
        executable.chmod(executable.stat().st_mode | 0o111)

        port = free_port()
        env = os.environ.copy()
        env.update(
            {
                "APP_MODE": "dev",
                "GENBOX_PORT": str(port),
                "GENBOX_NO_BROWSER": "1",
                "ALLOWED_ORIGINS": f"http://127.0.0.1:{port}",
            }
        )
        log_path = workdir / "client.log"
        success = False
        popen_options = {}
        if os.name == "nt":
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_options["start_new_session"] = True

        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [str(executable)],
                cwd=workdir,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                **popen_options,
            )
            deadline = time.monotonic() + args.timeout
            url = f"http://127.0.0.1:{port}/api/setup/status"
            try:
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        break
                    try:
                        with urllib.request.urlopen(url, timeout=2) as response:
                            if response.status == 200:
                                success = True
                                break
                    except Exception:
                        time.sleep(0.5)
            finally:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                    )
                else:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        process.kill()
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                if os.name == "nt":
                    time.sleep(1)

        if success:
            print(f"GenBox client smoke test passed on port {port}")
            return 0

        tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
        raise SystemExit(f"GenBox client failed to start. Log tail:\n{tail}")


if __name__ == "__main__":
    raise SystemExit(main())
