"""
GenBox 自动更新系统
支持源码更新、桌面客户端更新、Docker 更新
"""
import os
import sys
import subprocess
import shutil
import tempfile
import time
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from enum import Enum

import httpx


# ═══════════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════════
REPO_OWNER = "liwei9745"
REPO_NAME = "GenBox"
REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# GitHub 代理线路（国内优化）
GITHUB_MIRRORS = [
    {"name": "ghfast.top", "url": "https://ghfast.top", "desc": "推荐主线 - 稳定快速"},
    {"name": "gh-proxy.com", "url": "https://gh-proxy.com", "desc": "多CDN节点 - 备选"},
    {"name": "v6.gh-proxy.org", "url": "https://v6.gh-proxy.org", "desc": "IPv6优化"},
    {"name": "hub.gitmirror.com", "url": "https://hub.gitmirror.com", "desc": "稳定镜像"},
    {"name": "bgithub.xyz", "url": "https://bgithub.xyz", "desc": "直连镜像"},
    {"name": "github.com (直连)", "url": "", "desc": "GitHub直连"},
]

# 当前版本
CURRENT_VERSION = "2.4.1"


class UpdateType(Enum):
    SOURCE = "source"      # 源码 (git pull)
    EXE = "exe"            # 可执行文件 (下载替换)
    DOCKER = "docker"      # Docker (pull + restart)
    PIP = "pip"            # pip 包


@dataclass
class MirrorTestResult:
    name: str
    url: str
    latency_ms: float
    available: bool
    error: Optional[str] = None


@dataclass
class UpdateInfo:
    available: bool
    current_version: str
    latest_version: str
    release_notes: str
    download_url: Optional[str] = None
    update_type: str = "unknown"


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
# 线路测试
# ═══════════════════════════════════════════════════════════════════
async def test_mirror(mirror: dict, timeout: float = 5.0) -> MirrorTestResult:
    """测试单条线路的连通性和延迟"""
    test_url = f"{mirror['url']}/{GITHUB_API}" if mirror['url'] else GITHUB_API
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.head(test_url, headers={"User-Agent": "GenBox-Updater"})
            latency = (time.time() - start) * 1000
            return MirrorTestResult(
                name=mirror["name"],
                url=mirror["url"],
                latency_ms=round(latency, 1),
                available=resp.status_code < 400,
            )
    except Exception as e:
        return MirrorTestResult(
            name=mirror["name"],
            url=mirror["url"],
            latency_ms=9999,
            available=False,
            error=str(e)[:100],
        )


async def test_all_mirrors() -> List[MirrorTestResult]:
    """并发测试所有线路，返回排序结果"""
    import asyncio
    tasks = [test_mirror(m) for m in GITHUB_MIRRORS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # 过滤异常，按延迟排序
    valid = [r for r in results if isinstance(r, MirrorTestResult)]
    valid.sort(key=lambda x: (not x.available, x.latency_ms))
    return valid


def get_best_mirror_url(mirror_url: str) -> str:
    """将 GitHub URL 转换为代理 URL"""
    if not mirror_url:
        return GITHUB_API
    return f"{mirror_url}/{GITHUB_API}"


# ═══════════════════════════════════════════════════════════════════
# 版本检测
# ═══════════════════════════════════════════════════════════════════
async def check_latest_release(mirror_url: str = "") -> Optional[dict]:
    """从 GitHub 获取最新 Release"""
    api_url = get_best_mirror_url(mirror_url)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={"User-Agent": "GenBox-Updater"})
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


def parse_version(tag: str) -> tuple:
    """解析版本号 'v2.2.0' -> (2, 2, 0)"""
    v = tag.lstrip("v").split(".")
    return tuple(int(x) for x in v[:3])


def compare_versions(current: str, latest: str) -> bool:
    """比较版本号，latest > current 返回 True"""
    return parse_version(latest) > parse_version(current)


def get_asset_url(release: dict, platform: str) -> Optional[str]:
    """根据平台找到对应的下载资源"""
    assets = release.get("assets", [])
    patterns = {
        "win32": ["windows", "win", ".exe"],
        "linux": ["linux"],
        "darwin": ["macos", "mac", "darwin"],
    }
    pats = patterns.get(platform, [])
    for asset in assets:
        name = asset["name"].lower()
        if any(p in name for p in pats):
            return asset["browser_download_url"]
    return None


# ═══════════════════════════════════════════════════════════════════
# 更新执行
# ═══════════════════════════════════════════════════════════════════
async def apply_source_update(mirror_url: str = "") -> dict:
    """源码更新：git fetch + reset"""
    app_dir = get_app_dir()
    git_dir = app_dir / ".git"
    if not git_dir.exists():
        return {"success": False, "error": "非 git 仓库，无法源码更新"}

    # 配置 git 代理（如果使用镜像）
    if mirror_url:
        proxy_url = f"{mirror_url}/https://github.com/"
        subprocess.run(
            ["git", "config", f"url.{proxy_url}.insteadOf", "https://github.com/"],
            cwd=app_dir, capture_output=True
        )

    try:
        # 获取当前分支，计算对应的上游 ref（避免写死 origin/master 把 dev 等分支覆盖）
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=app_dir, capture_output=True, text=True
        ).stdout.strip()
        target = f"origin/{branch}" if branch else "origin/master"
        verify = subprocess.run(
            ["git", "rev-parse", "--verify", target],
            cwd=app_dir, capture_output=True, text=True
        )
        if verify.returncode != 0:
            target = "origin/master"

        # fetch
        r = subprocess.run(
            ["git", "fetch", "--all", "--tags"],
            cwd=app_dir, capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            return {"success": False, "error": f"fetch 失败: {r.stderr[:200]}"}

        # 检查是否有更新（相对当前分支上游）
        r = subprocess.run(
            ["git", "status", "-sb"],
            cwd=app_dir, capture_output=True, text=True
        )
        behind = "behind" in r.stdout

        if not behind:
            return {"success": True, "message": "已是最新版本"}

        # reset 到当前分支上游
        r = subprocess.run(
            ["git", "reset", "--hard", target],
            cwd=app_dir, capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            return {"success": False, "error": f"reset 失败: {r.stderr[:200]}"}

        # 安装依赖
        req_file = app_dir / "requirements.txt"
        if req_file.exists():
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                cwd=app_dir, capture_output=True, timeout=120
            )

        return {"success": True, "message": "源码更新完成，建议重启服务"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "更新超时，请检查网络"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def apply_exe_update(download_url: str, mirror_url: str = "") -> dict:
    """可执行文件更新：下载 + 替换"""
    exe_path = get_executable_path()
    if not exe_path:
        return {"success": False, "error": "无法获取可执行文件路径"}

    # 构造下载 URL
    if mirror_url:
        dl_url = f"{mirror_url}/{download_url}"
    else:
        dl_url = download_url

    try:
        # 下载
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(dl_url, headers={"User-Agent": "GenBox-Updater"})
            resp.raise_for_status()

        # 备份当前版本
        backup = exe_path.with_suffix(".exe.bak")
        if backup.exists():
            backup.unlink()
        shutil.copy2(exe_path, backup)

        # 写入新版本
        exe_path.write_bytes(resp.content)

        # 创建重启脚本
        restart_script = exe_path.parent / "_restart.bat"
        restart_script.write_text(
            f'''@echo off
chcp 65001 >nul
timeout /t 1 /nobreak >nul
start "" "{exe_path}"
del "%~f0"
''', encoding="utf-8"
        )

        # 启动重启脚本（异步）
        subprocess.Popen(
            ["cmd", "/c", str(restart_script)],
            creationflags=0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NO_WINDOW
        )

        return {"success": True, "message": "更新完成，正在重启..."}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def apply_docker_update() -> dict:
    """Docker 更新：pull 新镜像"""
    try:
        # 拉取最新镜像
        r = subprocess.run(
            ["docker", "pull", f"{REPO_NAME.lower()}:latest"],
            capture_output=True, text=True, timeout=300
        )
        if r.returncode != 0:
            return {"success": False, "error": f"docker pull 失败: {r.stderr[:200]}"}

        return {
            "success": True,
            "message": "镜像已更新，请运行 docker-compose up -d 重启容器"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════════════════
async def check_update(mirror_url: str = "") -> UpdateInfo:
    """检查是否有可用更新"""
    release = await check_latest_release(mirror_url)
    if not release:
        return UpdateInfo(
            available=False,
            current_version=CURRENT_VERSION,
            latest_version=CURRENT_VERSION,
            release_notes="无法获取版本信息",
        )

    latest = release.get("tag_name", CURRENT_VERSION)
    has_update = compare_versions(CURRENT_VERSION, latest)
    update_type = detect_update_type()

    # 找下载链接
    download_url = None
    if update_type == UpdateType.EXE:
        download_url = get_asset_url(release, sys.platform)

    return UpdateInfo(
        available=has_update,
        current_version=CURRENT_VERSION,
        latest_version=latest,
        release_notes=release.get("body", "")[:2000],
        download_url=download_url,
        update_type=update_type.value,
    )


async def apply_update(mirror_url: str = "", download_url: str = "") -> dict:
    """执行更新"""
    update_type = detect_update_type()

    if update_type == UpdateType.DOCKER:
        return await apply_docker_update()
    elif update_type == UpdateType.EXE:
        if not download_url:
            return {"success": False, "error": "缺少下载链接"}
        return await apply_exe_update(download_url, mirror_url)
    else:
        return await apply_source_update(mirror_url)
