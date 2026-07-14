"""Local Tailscale lifecycle using fixed, non-user-controlled commands."""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


LOGIN_URL_PATTERN = re.compile(r"https://login\.tailscale\.com/[A-Za-z0-9/?&=_-]+")
GENBOX_PORT = int(os.getenv("GENBOX_PORT", "8892"))
TAILSCALE_SERVE_PORT = int(os.getenv("TAILSCALE_SERVE_PORT", "8893"))


def find_tailscale() -> str:
    found = shutil.which("tailscale")
    if found:
        return found
    if sys.platform == "win32":
        for root in (os.getenv("ProgramFiles"), os.getenv("ProgramFiles(x86)"), os.getenv("LOCALAPPDATA")):
            if not root:
                continue
            candidate = Path(root) / "Tailscale" / "tailscale.exe"
            if candidate.is_file():
                return str(candidate)
    return ""


def _run(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def local_status() -> dict:
    binary = find_tailscale()
    if not binary:
        return {"installed": False, "online": False, "backend_state": "NotInstalled", "ips": [], "dns_name": "", "serve": False, "app_port": GENBOX_PORT, "serve_port": TAILSCALE_SERVE_PORT}
    result = _run([binary, "status", "--json"])
    if result.returncode != 0:
        return {"installed": True, "online": False, "backend_state": "NeedsLogin", "ips": [], "dns_name": "", "serve": False, "app_port": GENBOX_PORT, "serve_port": TAILSCALE_SERVE_PORT}
    try:
        data = json.loads(result.stdout)
    except (TypeError, ValueError):
        data = {}
    self_node = data.get("Self") if isinstance(data.get("Self"), dict) else {}
    raw_ips = self_node.get("TailscaleIPs")
    ips = [str(value) for value in raw_ips if str(value)] if isinstance(raw_ips, list) else []
    backend_state = str(data.get("BackendState") or "Unknown")
    serve_result = _run([binary, "serve", "status", "--json"])
    return {
        "installed": True,
        "online": backend_state == "Running" and bool(ips),
        "backend_state": backend_state,
        "ips": ips,
        "dns_name": str(self_node.get("DNSName") or "").rstrip("."),
        "serve": serve_result.returncode == 0 and f"127.0.0.1:{GENBOX_PORT}" in serve_result.stdout,
        "app_port": GENBOX_PORT,
        "serve_port": TAILSCALE_SERVE_PORT,
    }


def begin_login() -> dict:
    binary = find_tailscale()
    if not binary:
        raise RuntimeError("璇峰厛瀹夎 Tailscale")
    try:
        result = _run([binary, "up", "--timeout=8s"], timeout=12)
        output = f"{result.stdout}\n{result.stderr}"
    except subprocess.TimeoutExpired as exc:
        output = f"{exc.stdout or ''}\n{exc.stderr or ''}"
    match = LOGIN_URL_PATTERN.search(output)
    status = local_status()
    return {"started": True, "login_url": match.group(0) if match else "", "online": status["online"]}


def enable_genbox_serve(port: int = TAILSCALE_SERVE_PORT) -> dict:
    status = local_status()
    if not status["online"]:
        raise RuntimeError("璇峰厛鐧诲綍 Tailscale")
    binary = find_tailscale()
    result = _run([
        binary, "serve", "--bg", f"--http={port}", f"http://127.0.0.1:{GENBOX_PORT}",
    ])
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Tailscale Serve 閰嶇疆澶辫触")[:240])
    ipv4 = next((ip for ip in status["ips"] if ":" not in ip), "")
    if not ipv4:
        raise RuntimeError("\u672c\u673a\u6ca1\u6709 Tailscale IPv4 \u5730\u5740")
    dns_name = str(status.get("dns_name") or "").rstrip(".")
    if not dns_name:
        raise RuntimeError("\u672c\u673a\u6ca1\u6709 Tailscale DNS \u540d\u79f0\uff0c\u8bf7\u786e\u8ba4\u5df2\u542f\u7528 MagicDNS")
    return {"enabled": True, "url": f"http://{dns_name}:{port}", "address": ipv4}


def ping_peer(address: str) -> bool:
    binary = find_tailscale()
    if not binary or not re.fullmatch(r"100(?:\.\d{1,3}){3}", str(address or "")):
        return False
    return _run([binary, "ping", "--c", "1", "--timeout=8s", address], timeout=12).returncode == 0


class LocalInstallTaskManager:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.runners: dict[str, asyncio.Task] = {}

    def create(self) -> str:
        task_id = uuid.uuid4().hex[:12]
        self.tasks[task_id] = {"id": task_id, "status": "queued", "progress": 0, "error": None}
        self.runners[task_id] = asyncio.create_task(self._run(task_id))
        return task_id

    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    async def _run(self, task_id: str) -> None:
        state = self.tasks[task_id]
        if sys.platform != "win32":
            state.update(status="failed", error="鏈満涓€閿畨瑁呭綋鍓嶄粎鏀寔 Windows")
            return
        winget = shutil.which("winget")
        if not winget:
            state.update(status="failed", error="鏈壘鍒?winget锛岃浠?Microsoft Store 瀹夎 App Installer")
            return
        state.update(status="running", progress=20)
        process = await asyncio.create_subprocess_exec(
            winget, "install", "--id", "Tailscale.Tailscale", "--exact", "--silent",
            "--accept-package-agreements", "--accept-source-agreements",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0 and not find_tailscale():
            state.update(status="failed", progress=100, error=(stderr.decode(errors="replace") or "Tailscale 瀹夎澶辫触")[-240:])
            return
        state.update(status="completed", progress=100, error=None)


local_install_tasks = LocalInstallTaskManager()
