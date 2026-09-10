"""
GenBox PyInstaller Build Script
Usage: python build.py
"""
import os
import sys
import platform
import subprocess
import shutil
import tempfile
from pathlib import Path

from genbox_version import APP_NAME, __version__
from scripts.third_party_licenses import LICENSE_DIRECTORY, collect_runtime_licenses

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

# Pinned direct runtime distributions. Their metadata is copied into the
# executable so the empty-directory smoke can verify the packaged versions.
PACKAGED_RUNTIME_DISTRIBUTIONS = {
    "fastapi": "0.139.0",
    "uvicorn": "0.51.0",
    "python-multipart": "0.0.32",
    "httpx": "0.28.1",
    "aiofiles": "25.1.0",
    "requests": "2.34.2",
    "asyncssh": "2.24.0",
    "bcrypt": "5.0.0",
    "pillow": "12.3.0",
    "cryptography": "49.0.0",
    "python-dotenv": "1.2.2",
    "pydantic": "2.13.4",
    "pydantic-settings": "2.14.2",
    "psutil": "7.2.2",
    "typing-extensions": "4.16.0",
    "tzdata": "2026.3",
    "numpy": "2.4.3",
    "onnxruntime": "1.24.3",
}

# Direct runtime modules plus transitive modules loaded dynamically by
# Pydantic. Every entry is imported by the packaged runtime smoke.
PACKAGED_RUNTIME_IMPORTS = [
    "fastapi",
    "uvicorn",
    "python_multipart",
    "multipart",
    "httpx",
    "aiofiles",
    "requests",
    "asyncssh",
    "bcrypt",
    "PIL",
    "PIL.Image",
    "cryptography",
    "cryptography.fernet",
    "dotenv",
    "pydantic",
    "pydantic_settings",
    "pydantic_core",
    "annotated_types",
    "typing_inspection",
    "psutil",
    "typing_extensions",
    "tzdata",
    "numpy",
    "onnxruntime",
]

PACKAGED_RUNTIME_SYMBOLS = {
    "fastapi": ("FastAPI",),
    "uvicorn": ("Config",),
    "python_multipart": ("MultipartParser",),
    "multipart": ("MultipartParser",),
    "httpx": ("AsyncClient",),
    "requests": ("Session",),
    "asyncssh": ("connect",),
    "bcrypt": ("hashpw", "kdf"),
    "PIL.Image": ("open",),
    "cryptography.fernet": ("Fernet",),
    "dotenv": ("load_dotenv",),
    "pydantic": ("BaseModel",),
    "pydantic_settings": ("BaseSettings",),
    "pydantic_core": ("SchemaValidator",),
    "psutil": ("Process",),
    "numpy": ("ndarray",),
    "onnxruntime": ("InferenceSession",),
}

# 隐藏导入（PyInstaller 可能检测不到的模块）
HIDDEN_IMPORTS = [
    *PACKAGED_RUNTIME_IMPORTS,
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
    "pydantic.deprecated",
    "dotenv.main",
    "bcrypt._bcrypt",
    "extensions",
    "extensions.credential_vault",
    "extensions.discovery",
    "extensions.local_tailscale",
    "extensions.network_adapters",
    "extensions.orchestrator",
    "sync.ingest",
    "image_tools",
    "image_tools.cutout_onnx",
    "onnxruntime.capi._pybind_state",
    "onnxruntime.capi.onnxruntime_pybind11_state",
]

# Native libraries, data, and dynamically loaded submodules required by the
# frozen runtime. Keep these lists mirrored in create_spec() and build().
COLLECT_ALL_PACKAGES = ["numpy", "onnxruntime", "pydantic_core"]
COLLECT_SUBMODULE_PACKAGES = ["uvicorn", "pydantic_settings"]
COPY_METADATA_DISTRIBUTIONS = list(PACKAGED_RUNTIME_DISTRIBUTIONS)

# 排除的模块（减小体积）
EXCLUDES = [
    "tkinter",
    "matplotlib",
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


def create_spec(data_files=None):
    """生成 PyInstaller spec 文件"""
    data_files = DATA_FILES if data_files is None else data_files
    # 构建 datas 参数
    datas_str = ", ".join([f"(r'{src}', r'{dst}')" for src, dst in data_files])
    hidden_str = ", ".join([f"'{m}'" for m in HIDDEN_IMPORTS])
    excludes_str = ", ".join([f"'{m}'" for m in EXCLUDES])
    collect_packages_str = repr(COLLECT_ALL_PACKAGES)
    collect_submodules_str = repr(COLLECT_SUBMODULE_PACKAGES)
    copy_metadata_str = repr(COPY_METADATA_DISTRIBUTIONS)

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

block_cipher = None
datas = [{datas_str}]
binaries = []
hiddenimports = [{hidden_str}]
for package in {collect_packages_str}:
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports
for package in {collect_submodules_str}:
    hiddenimports += collect_submodules(package)
for distribution in {copy_metadata_str}:
    datas += copy_metadata(distribution)

a = Analysis(
    [r'{MAIN_SCRIPT}'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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


def create_runtime_smoke_hook(directory: Path) -> Path:
    """Create a build-local hook for packaged version and import smoke flags."""
    imports = repr(PACKAGED_RUNTIME_IMPORTS)
    expected_versions = repr(PACKAGED_RUNTIME_DISTRIBUTIONS)
    required_symbols = repr(PACKAGED_RUNTIME_SYMBOLS)
    hook = directory / "genbox_runtime_smoke.py"
    hook.write_text(
        f'''import importlib
from importlib import metadata
import json
import sys

if "--version" in sys.argv:
    print("{APP_NAME} {APP_VERSION}")
    raise SystemExit(0)

if "--runtime-import-smoke" in sys.argv:
    modules = {{name: importlib.import_module(name) for name in {imports}}}
    expected_versions = {expected_versions}
    versions = {{name: metadata.version(name) for name in expected_versions}}
    if versions != expected_versions:
        raise SystemExit(f"unexpected packaged runtime versions: {{versions}}")
    missing_symbols = []
    for module_name, attributes in {required_symbols}.items():
        for attribute in attributes:
            if not hasattr(modules[module_name], attribute):
                missing_symbols.append(f"{{module_name}}.{{attribute}}")
    if missing_symbols:
        raise SystemExit(f"missing packaged runtime symbols: {{missing_symbols}}")
    passphrase = "genbox-runtime-smoke-only"
    private_key = modules["asyncssh"].generate_private_key("ssh-ed25519")
    encrypted_key = private_key.export_private_key("openssh", passphrase)
    imported_key = modules["asyncssh"].import_private_key(encrypted_key, passphrase)
    if imported_key.get_algorithm() != "ssh-ed25519":
        raise SystemExit("encrypted OpenSSH private-key smoke returned wrong algorithm")
    print(
        json.dumps(
            {{
                "encrypted_openssh": "ok",
                "status": "ok",
                "symbols": "ok",
                "versions": versions,
            }},
            sort_keys=True,
        )
    )
    raise SystemExit(0)
''',
        encoding="utf-8",
    )
    return hook


def build():
    """执行 PyInstaller 构建"""
    print(f"\n{'='*60}")
    print(f"Building {APP_NAME} v{APP_VERSION}")
    print(f"Platform: {SYSTEM} {ARCH}")
    print(f"{'='*60}\n")

    # 清理
    clean_build()

    with tempfile.TemporaryDirectory(prefix="genbox-release-licenses-") as temporary:
        temporary_path = Path(temporary)
        license_source = collect_runtime_licenses(temporary_path / LICENSE_DIRECTORY)
        runtime_smoke_hook = create_runtime_smoke_hook(temporary_path)
        build_data_files = [*DATA_FILES, (str(license_source), LICENSE_DIRECTORY)]

        # 生成 spec 文件
        spec_file = create_spec(build_data_files)

        # 构建命令
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--noconfirm",
            "--clean",
            f"--name={APP_NAME}",
            f"--runtime-hook={runtime_smoke_hook}",
        ]

        # 添加数据文件
        for src, dst in build_data_files:
            if os.path.exists(src):
                if SYSTEM == "windows":
                    cmd.append(f"--add-data={src};{dst}")
                else:
                    cmd.append(f"--add-data={src}:{dst}")

        # 添加隐藏导入
        for mod in HIDDEN_IMPORTS:
            cmd.append(f"--hidden-import={mod}")

        # Include dynamically loaded native libraries, data, and submodules.
        for package in COLLECT_ALL_PACKAGES:
            cmd.append(f"--collect-all={package}")
        for package in COLLECT_SUBMODULE_PACKAGES:
            cmd.append(f"--collect-submodules={package}")
        for distribution in COPY_METADATA_DISTRIBUTIONS:
            cmd.append(f"--copy-metadata={distribution}")

        # 添加排除
        for mod in EXCLUDES:
            cmd.append(f"--exclude-module={mod}")

        # 入口脚本
        cmd.append(MAIN_SCRIPT)

        print(f"Running: {' '.join(cmd)}\n")
        result = subprocess.run(cmd, capture_output=False)

        if result.returncode == 0:
            shutil.copytree(
                license_source,
                Path("dist") / LICENSE_DIRECTORY,
                dirs_exist_ok=True,
            )

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
