"""
GenBox PyInstaller Build Script
Usage: python build.py
"""
import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

from genbox_version import APP_NAME, __version__

# ──────────────────────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────────────────────
APP_VERSION = __version__
MAIN_SCRIPT = "main.py"

# 需要打包的数据文件
DATA_FILES = [
    ("static", "static"),
    ("providers", "providers"),
]

# 隐藏导入（PyInstaller 可能检测不到的模块）
HIDDEN_IMPORTS = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "multipart",
    "pydantic",
    "pydantic.deprecated",
    "httpx",
    "aiofiles",
    "PIL",
    "PIL.Image",
    "psutil",
    "dotenv",
    "dotenv.main",
    "asyncssh",
    "cryptography",
    "cryptography.fernet",
    "extensions",
    "extensions.credential_vault",
    "extensions.discovery",
    "extensions.local_tailscale",
    "extensions.network_adapters",
    "extensions.orchestrator",
    "sync.ingest",
    "tzdata",
]

# 排除的模块（减小体积）
EXCLUDES = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "test",
    "unittest",
]

# ──────────────────────────────────────────────────────────────
# 平台检测
# ──────────────────────────────────────────────────────────────
SYSTEM = platform.system().lower()
ARCH = platform.machine().lower()

if SYSTEM == "windows":
    ICON_PATH = None  # 可以后续添加 .ico
    CONSOLE = True  # 显示控制台窗口，方便查看日志
elif SYSTEM == "darwin":
    ICON_PATH = None  # 可以后续添加 .icns
    CONSOLE = False
else:  # linux
    ICON_PATH = None
    CONSOLE = False


def clean_build():
    """清理旧的构建文件"""
    dirs = ["build", "dist", "__pycache__"]
    for d in dirs:
        if os.path.exists(d):
            print(f"Cleaning {d}/")
            shutil.rmtree(d)
    for f in Path(".").glob("*.spec"):
        print(f"Cleaning {f}")
        f.unlink()


def create_spec():
    """生成 PyInstaller spec 文件"""
    # 构建 datas 参数
    datas_str = ", ".join([f"(r'{src}', r'{dst}')" for src, dst in DATA_FILES])
    hidden_str = ", ".join([f"'{m}'" for m in HIDDEN_IMPORTS])
    excludes_str = ", ".join([f"'{m}'" for m in EXCLUDES])

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    [r'{MAIN_SCRIPT}'],
    pathex=[],
    binaries=[],
    datas=[{datas_str}],
    hiddenimports=[{hidden_str}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[{excludes_str}],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={CONSOLE},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {f"icon=r'{ICON_PATH}'," if ICON_PATH else ""}
)
"""

    spec_file = f"{APP_NAME}.spec"
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)
    print(f"Created {spec_file}")
    return spec_file


def build():
    """执行 PyInstaller 构建"""
    print(f"\n{'='*60}")
    print(f"Building {APP_NAME} v{APP_VERSION}")
    print(f"Platform: {SYSTEM} {ARCH}")
    print(f"{'='*60}\n")

    # 清理
    clean_build()

    # 生成 spec 文件
    spec_file = create_spec()

    # 构建命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        f"--name={APP_NAME}",
    ]

    # 添加数据文件
    for src, dst in DATA_FILES:
        if os.path.exists(src):
            if SYSTEM == "windows":
                cmd.append(f"--add-data={src};{dst}")
            else:
                cmd.append(f"--add-data={src}:{dst}")

    # 添加隐藏导入
    for mod in HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={mod}")

    # 添加排除
    for mod in EXCLUDES:
        cmd.append(f"--exclude-module={mod}")

    # 入口脚本
    cmd.append(MAIN_SCRIPT)

    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print("\nBuild FAILED!")
        sys.exit(1)

    # 输出位置
    if SYSTEM == "windows":
        exe_path = f"dist/{APP_NAME}.exe"
    elif SYSTEM == "darwin":
        exe_path = f"dist/{APP_NAME}"
    else:
        exe_path = f"dist/{APP_NAME}"

    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n{'='*60}")
        print(f"Build SUCCESS!")
        print(f"Output: {exe_path}")
        print(f"Size: {size_mb:.1f} MB")
        print(f"{'='*60}")
    else:
        print(f"\nWarning: {exe_path} not found")


if __name__ == "__main__":
    build()
