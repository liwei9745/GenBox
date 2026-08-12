"""Create deterministic non-client release bundles and SHA-256 checksums."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genbox_version import APP_NAME, __version__  # noqa: E402


ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def write_zip(destination: Path, entries: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in sorted(entries, key=lambda entry: entry[1]):
            info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_image_reference(tag: str) -> str:
    if not tag or any(character.isspace() for character in tag):
        raise ValueError("candidate image tag must be a non-empty single token")
    return f"ghcr.io/liwei9745/genbox:{tag}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--docker-only", action="store_true")
    parser.add_argument(
        "--candidate-tag",
        help="create a candidate-only Compose bundle pinned to this GHCR image tag",
    )
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    candidate_tag = args.candidate_tag
    compose_source = ROOT / "docker-compose.yml"
    env_source = ROOT / ".env.docker.example"
    if candidate_tag:
        image = candidate_image_reference(candidate_tag)
        candidate_dir = output / ".candidate-compose"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        compose_source = candidate_dir / "docker-compose.yml"
        env_source = candidate_dir / ".env.example"
        compose_source.write_text(
            (ROOT / "docker-compose.yml").read_text(encoding="utf-8").replace(
                f"ghcr.io/liwei9745/genbox:{__version__}", image
            ),
            encoding="utf-8",
        )
        env_source.write_text(
            (ROOT / ".env.docker.example").read_text(encoding="utf-8").replace(
                f"ghcr.io/liwei9745/genbox:{__version__}", image
            ),
            encoding="utf-8",
        )
        docker_name = f"{APP_NAME}-Docker-Compose-{candidate_tag}.zip"
    else:
        docker_name = f"{APP_NAME}-Docker-Compose-v{__version__}.zip"

    docker_zip = output / docker_name
    write_zip(
        docker_zip,
        [
            (compose_source, "docker-compose.yml"),
            (env_source, ".env.example"),
            (ROOT / "docs" / "DOCKER-QUICKSTART.md", "README.md"),
            (ROOT / "LICENSE", "LICENSE"),
            (ROOT / "COPYRIGHT", "COPYRIGHT"),
            (ROOT / "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        ],
    )
    artifacts = [docker_zip]

    if not args.docker_only:
        source_zip = output / f"{APP_NAME}-Source-v{__version__}.zip"
        subprocess.run(
            ["git", "archive", "--format=zip", f"--output={source_zip}", "HEAD"],
            cwd=ROOT,
            check=True,
        )
        artifacts.append(source_zip)

    checksum_path = output / "SHA256SUMS.txt"
    checksum_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts),
        encoding="ascii",
    )
    for artifact in [*artifacts, checksum_path]:
        print(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
