"""Collect pinned runtime license files from installed distributions."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path


LICENSE_DIRECTORY = "THIRD_PARTY_LICENSES"
MINIMUM_PYTHON = (3, 11)
SUPPORTED_PLATFORMS = {"windows", "darwin", "linux"}
SUPPORTED_ARCHITECTURES = {"amd64", "x86_64", "arm64", "aarch64"}
RUNTIME_LICENSES = {
    "numpy": {
        "version": "2.4.3",
        "files": {
            "LICENSE.txt": lambda path: ".dist-info/licenses/LICENSE.txt" in path,
        },
    },
    "onnxruntime": {
        "version": "1.24.3",
        "files": {
            "LICENSE": lambda path: path.replace("\\", "/") == "onnxruntime/LICENSE",
            "ThirdPartyNotices.txt": lambda path: path.replace("\\", "/")
            == "onnxruntime/ThirdPartyNotices.txt",
        },
    },
}


def validate_build_platform() -> None:
    system = platform.system().lower()
    architecture = platform.machine().lower()
    if sys.version_info < MINIMUM_PYTHON:
        raise RuntimeError("release builds require Python 3.11 or newer")
    if system not in SUPPORTED_PLATFORMS:
        raise RuntimeError(f"unsupported release platform: {system}")
    if architecture not in SUPPORTED_ARCHITECTURES:
        raise RuntimeError(f"unsupported release architecture: {architecture}")


def _find_distribution_file(distribution, predicate) -> Path:
    matches = [
        file
        for file in distribution.files or []
        if predicate(str(file).replace("\\", "/"))
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one matching license file in {distribution.metadata['Name']}; "
            f"found {len(matches)}"
        )
    source = Path(distribution.locate_file(matches[0])).resolve()
    if not source.is_file():
        raise RuntimeError(f"installed license file is missing: {matches[0]}")
    return source


def collect_runtime_licenses(destination: Path) -> Path:
    """Collect verified license assets, failing closed on metadata drift."""
    validate_build_platform()
    destination = Path(destination)
    if destination.exists():
        raise RuntimeError(f"license collection destination already exists: {destination}")
    destination.mkdir(parents=True)

    manifest = {"schema_version": 1, "distributions": []}
    for distribution_name, contract in RUNTIME_LICENSES.items():
        try:
            distribution = importlib.metadata.distribution(distribution_name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise RuntimeError(
                f"required release distribution is not installed: {distribution_name}"
            ) from exc
        actual_name = distribution.metadata["Name"]
        actual_version = distribution.version
        if actual_name.lower() != distribution_name:
            raise RuntimeError(
                f"unexpected distribution name for {distribution_name}: {actual_name}"
            )
        if actual_version != contract["version"]:
            raise RuntimeError(
                f"release license metadata requires {distribution_name}=={contract['version']}; "
                f"installed {actual_version}"
            )

        package_destination = destination / distribution_name
        package_destination.mkdir()
        collected_files = []
        for output_name, predicate in contract["files"].items():
            source = _find_distribution_file(distribution, predicate)
            shutil.copyfile(source, package_destination / output_name)
            collected_files.append(f"{distribution_name}/{output_name}")
        manifest["distributions"].append(
            {
                "name": actual_name,
                "version": actual_version,
                "files": collected_files,
            }
        )

    (destination / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def validate_collected_licenses(directory: Path) -> Path:
    directory = Path(directory)
    manifest_path = directory / "MANIFEST.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"license manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = [
        {
            "name": name,
            "version": contract["version"],
            "files": [f"{name}/{filename}" for filename in contract["files"]],
        }
        for name, contract in RUNTIME_LICENSES.items()
    ]
    if manifest != {"schema_version": 1, "distributions": expected}:
        raise RuntimeError("license manifest does not match the pinned runtime contract")
    for item in expected:
        for relative_path in item["files"]:
            path = directory / relative_path
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"collected license asset is missing or empty: {relative_path}")
    return directory
