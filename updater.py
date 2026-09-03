"""Read-only GenBox release checker with fail-closed update application."""
import os
import sys
import json
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

import httpx

from genbox_version import __version__


# ═══════════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════════
REPO_OWNER = "liwei9745"
REPO_NAME = "GenBox"
REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
LATEST_RELEASE_API = f"{GITHUB_API}/releases/latest"
RELEASES_URL = f"{REPO_URL}/releases"
UPDATE_RELEASE_RESPONSE_MAX_BYTES = 1024 * 1024
UPDATE_ERROR_RESPONSE_MAX_BYTES = 64 * 1024
UPDATE_APPLY_UNAVAILABLE_CODE = "update_apply_unavailable"

# 当前版本
CURRENT_VERSION = __version__


class UpdateType(Enum):
    SOURCE = "source"      # 源码 (git pull)
    EXE = "exe"            # 可执行文件 (下载替换)
    DOCKER = "docker"      # Docker (pull + restart)
    PIP = "pip"            # pip 包


@dataclass
class UpdateInfo:
    available: bool
    current_version: str
    latest_version: str
    release_notes: str
    update_type: str = "unknown"
    automatic_apply_available: bool = False
    manual_install_required: bool = True


# ═══════════════════════════════════════════════════════════════════
# 环境检测
# ═══════════════════════════════════════════════════════════════════
def detect_update_type() -> UpdateType:
    """检测当前运行环境，决定更新方式"""
    # 检查 Docker
    if Path("/.dockerenv").exists() or os.environ.get("GENBOX_DOCKER"):
        return UpdateType.DOCKER

    # 检查是否 PyInstaller 打包
    if getattr(sys, 'frozen', False):
        return UpdateType.EXE

    # 检查是否 git 仓库
    git_dir = Path(__file__).parent / ".git"
    if git_dir.exists():
        return UpdateType.SOURCE

    # 默认源码方式
    return UpdateType.SOURCE


def get_executable_path() -> Optional[Path]:
    """获取可执行文件路径"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable)
    return None


def get_app_dir() -> Path:
    """获取应用根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


# ═══════════════════════════════════════════════════════════════════
# 版本检测
# ═══════════════════════════════════════════════════════════════════
async def _read_bounded_response(response, max_bytes: int) -> bytes:
    """Read a streamed response without trusting its declared or actual size."""
    content_length = (getattr(response, "headers", {}) or {}).get("content-length")
    if content_length is not None:
        declared_length = int(content_length)
        if declared_length < 0 or declared_length > max_bytes:
            raise ValueError("update_response_bytes_exceeded")

    content = bytearray()
    async for chunk in response.aiter_bytes():
        if len(content) + len(chunk) > max_bytes:
            raise ValueError("update_response_bytes_exceeded")
        content.extend(chunk)
    return bytes(content)


def _redact_release_notes(value: object) -> str:
    """Keep public release notes useful without reflecting credential-like text."""
    text = str(value or "")
    text = re.sub(
        r"(?i)([?&](?:api[_-]?key|key|token|access[_-]?token|signature|sig)=)[^&\s]+",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(r"(?i)\b(Bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)(https://)[^/@\s:]+:[^/@\s]+@",
        r"\1[REDACTED]@",
        text,
    )
    text = re.sub(r"(?i)\b(?:sk|rk|pk)-[A-Za-z0-9._-]{8,}", "[REDACTED]", text)
    text = re.sub(
        r'''(?i)(["'](?:api[_-]?key|token|access[_-]?token|secret)["']\s*:\s*["'])[^"']+(["'])''',
        r"\1[REDACTED]\2",
        text,
    )
    return "".join(
        char for char in text if char in "\n\r\t" or ord(char) >= 32
    )[:2000]


async def check_latest_release() -> Optional[dict]:
    """Fetch only the canonical GitHub latest-release document."""
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            verify=True,
        ) as client:
            async with client.stream(
                "GET",
                LATEST_RELEASE_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "GenBox-Updater",
                },
            ) as response:
                max_bytes = (
                    UPDATE_ERROR_RESPONSE_MAX_BYTES
                    if int(response.status_code) >= 400
                    else UPDATE_RELEASE_RESPONSE_MAX_BYTES
                )
                content = await _read_bounded_response(response, max_bytes)
                if int(response.status_code) >= 400:
                    return None
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def parse_version(tag: str) -> tuple:
    """解析版本号 'v2.2.0' -> (2, 2, 0)"""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?", tag.strip())
    if not match:
        raise ValueError(f"unsupported_version: {tag}")
    major, minor, patch, candidate = match.groups()
    return (
        int(major),
        int(minor),
        int(patch),
        0 if candidate is not None else 1,
        int(candidate or 0),
    )


def compare_versions(current: str, latest: str) -> bool:
    """比较版本号，latest > current 返回 True"""
    return parse_version(latest) > parse_version(current)


def get_asset_url(release: dict, platform: str) -> Optional[str]:
    """根据平台找到对应的下载资源"""
    assets = release.get("assets", [])
    preferred_names = {
        "win32": ["genbox.exe"],
        "linux": ["genbox-linux-x64", "genbox-linux"],
        "darwin": ["genbox-macos", "genbox-darwin"],
    }
    by_name = {
        asset.get("name", "").lower(): asset.get("browser_download_url")
        for asset in assets
        if asset.get("browser_download_url")
    }
    for name in preferred_names.get(platform, []):
        if name in by_name:
            return by_name[name]

    # Compatibility fallback for custom release names. Archives are never valid
    # self-update payloads because replacing an executable with a ZIP corrupts it.
    patterns = {
        "win32": ["windows", "win", ".exe"],
        "linux": ["linux"],
        "darwin": ["macos", "mac", "darwin"],
    }
    archive_suffixes = (".zip", ".tar", ".tar.gz", ".tgz", ".dmg")
    for asset in assets:
        name = asset.get("name", "").lower()
        if not name.endswith(archive_suffixes) and any(
            pattern in name for pattern in patterns.get(platform, [])
        ):
            return asset.get("browser_download_url")
    return None


def _windows_restart_script(exe_path: Path, staged_path: Path, backup_path: Path, pid: int) -> str:
    """Build the detached helper that replaces a locked Windows executable."""
    return f'''@echo off
chcp 65001 >nul
timeout /t 2 /nobreak >nul
taskkill /PID {pid} /T /F >nul 2>&1

for /L %%I in (1,1,30) do (
  move /Y "{exe_path}" "{backup_path}" >nul 2>&1 && goto replace
  timeout /t 1 /nobreak >nul
)
goto failed

:replace
move /Y "{staged_path}" "{exe_path}" >nul 2>&1
if errorlevel 1 (
  move /Y "{backup_path}" "{exe_path}" >nul 2>&1
  goto failed
)
start "" /D "{exe_path.parent}" "{exe_path}"
goto cleanup

:failed
start "" /D "{exe_path.parent}" "{exe_path}"

:cleanup
del "%~f0"
'''


def _posix_restart_script(exe_path: Path, staged_path: Path, backup_path: Path, pid: int) -> str:
    """Build the detached helper used by packaged Linux and macOS clients."""
    return f'''#!/bin/sh
sleep 2
kill {pid} 2>/dev/null || true
i=0
while kill -0 {pid} 2>/dev/null && [ "$i" -lt 30 ]; do
  sleep 1
  i=$((i + 1))
done
mv -f "{exe_path}" "{backup_path}" || exit 1
if ! mv -f "{staged_path}" "{exe_path}"; then
  mv -f "{backup_path}" "{exe_path}"
  exit 1
fi
chmod +x "{exe_path}"
cd "{exe_path.parent}" || exit 1
nohup "{exe_path}" >/dev/null 2>&1 &
rm -f "$0"
'''


def update_apply_unavailable_detail() -> dict:
    """Public fail-closed reason shared by every disabled apply path."""
    return {
        "code": UPDATE_APPLY_UNAVAILABLE_CODE,
        "message": "automatic update is unavailable; install manually from the canonical GitHub Release after verifying the release information",
        "automatic_apply_available": False,
        "manual_install_required": True,
        "release_source": "canonical_github_release",
    }


async def apply_source_update() -> dict:
    return {"success": False, **update_apply_unavailable_detail()}


async def apply_exe_update() -> dict:
    return {"success": False, **update_apply_unavailable_detail()}


async def apply_docker_update() -> dict:
    return {"success": False, **update_apply_unavailable_detail()}


# ═══════════════════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════════════════
async def check_update() -> UpdateInfo:
    """检查是否有可用更新"""
    release = await check_latest_release()
    if not release:
        return UpdateInfo(
            available=False,
            current_version=CURRENT_VERSION,
            latest_version=CURRENT_VERSION,
            release_notes="无法获取版本信息",
        )

    latest = str(release.get("tag_name", "")).strip()
    try:
        has_update = compare_versions(CURRENT_VERSION, latest)
    except (TypeError, ValueError):
        return UpdateInfo(
            available=False,
            current_version=CURRENT_VERSION,
            latest_version=CURRENT_VERSION,
            release_notes="无法验证版本信息",
        )
    update_type = detect_update_type()

    return UpdateInfo(
        available=has_update,
        current_version=CURRENT_VERSION,
        latest_version=latest,
        release_notes=_redact_release_notes(release.get("body", "")),
        update_type=update_type.value,
    )


async def apply_update() -> dict:
    """Remain unavailable until signed manifests and an embedded key exist."""
    return {"success": False, **update_apply_unavailable_detail()}
