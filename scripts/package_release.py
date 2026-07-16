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


def write_zip(destination: Path, entries: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in entries:
            archive.write(source, name)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--docker-only", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    docker_zip = output / f"{APP_NAME}-Docker-Compose-v{__version__}.zip"
    write_zip(
        docker_zip,
        [
            (ROOT / "docker-compose.yml", "docker-compose.yml"),
            (ROOT / ".env.docker.example", ".env.example"),
            (ROOT / "docs" / "DOCKER-QUICKSTART.md", "README.md"),
            (ROOT / "LICENSE", "LICENSE"),
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
