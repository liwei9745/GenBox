"""Create deterministic non-client release bundles and SHA-256 checksums."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genbox_version import APP_NAME, __version__  # noqa: E402
from scripts.third_party_licenses import (  # noqa: E402
    LICENSE_DIRECTORY,
    collect_runtime_licenses,
    validate_collected_licenses,
)


def write_zip(destination: Path, entries: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in entries:
            write_archive_file(archive, source, name)


def write_archive_file(archive: zipfile.ZipFile, source: Path, name: str) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def license_entries(directory: Path) -> list[tuple[Path, str]]:
    directory = validate_collected_licenses(directory)
    return [
        (path, f"{LICENSE_DIRECTORY}/{path.relative_to(directory).as_posix()}")
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class SourcePackagingError(RuntimeError):
    """Raised when a source archive cannot be bound to a frozen commit."""


RELEASE_TAG_PATTERN = re.compile(
    r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-rc\.(?:0|[1-9][0-9]*))?"
)


def validate_release_tag(tag: str, version: str = __version__) -> None:
    expected = f"v{version}"
    if RELEASE_TAG_PATTERN.fullmatch(tag) is None:
        raise SourcePackagingError(
            f"release tag must use canonical v-prefixed semantic version syntax: {tag!r}"
        )
    if tag != expected:
        raise SourcePackagingError(
            f"release tag {tag!r} does not match packaged application version {expected!r}"
        )


def _git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "git command failed").strip()
        raise SourcePackagingError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def resolve_source_commit(requested_revision: str | None) -> str:
    """Resolve and validate the immutable revision used by a source archive.

    A source bundle is never created from the working tree.  Requiring a clean
    checkout also prevents an operator from accidentally packaging an older
    HEAD while assuming that uncommitted release files are included.
    """

    revision = (requested_revision or "").strip()
    if not revision:
        raise SourcePackagingError(
            "source archives require --source-commit <sha>; commit and freeze the "
            "complete release candidate first"
        )
    if revision.startswith("-"):
        raise SourcePackagingError("--source-commit must be a git revision, not an option")

    commit = _git_output("rev-parse", "--verify", f"{revision}^{{commit}}")
    head = _git_output("rev-parse", "--verify", "HEAD^{commit}")
    if head != commit:
        raise SourcePackagingError(
            "frozen source commit does not match HEAD; check out the committed release "
            f"first (HEAD={head}, source={commit})"
        )
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if status.returncode:
        detail = (status.stderr or status.stdout or "git status failed").strip()
        raise SourcePackagingError(f"unable to verify a clean worktree: {detail}")
    if status.stdout.strip():
        changed = "\n".join(status.stdout.strip().splitlines()[:20])
        if len(status.stdout.strip().splitlines()) > 20:
            changed += "\n..."
        raise SourcePackagingError(
            "source archive requires a clean worktree; commit the release files "
            "first and rerun with --source-commit <sha>. Changed paths:\n"
            f"{changed}"
        )
    return commit


def write_source_archive(
    destination: Path,
    source_commit: str,
    packaged_licenses: list[tuple[Path, str]],
) -> None:
    """Archive exactly ``source_commit`` and append the generated license sidecar."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".genbox-source-archive-", dir=destination.parent
    ) as temporary:
        temporary_archive = Path(temporary) / destination.name
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.autocrlf=false",
                "archive",
                "--format=zip",
                f"--output={temporary_archive}",
                source_commit,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout or "git archive failed").strip()
            raise SourcePackagingError(
                f"unable to archive frozen source commit {source_commit}: {detail}"
            )

        with zipfile.ZipFile(temporary_archive, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            existing_names = set(archive.namelist())
            conflicting = [name for _, name in packaged_licenses if name in existing_names]
            if conflicting:
                joined = ", ".join(sorted(conflicting))
                raise SourcePackagingError(
                    "source commit already contains generated license sidecar entries; "
                    f"refusing duplicate paths: {joined}"
                )
            for source, name in packaged_licenses:
                write_archive_file(archive, source, name)
        temporary_archive.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--docker-only", action="store_true")
    parser.add_argument("--licenses-dir", type=Path)
    parser.add_argument(
        "--source-commit",
        help="immutable git commit/revision for the source bundle (requires a clean worktree)",
    )
    parser.add_argument(
        "--validate-release-tag",
        metavar="TAG",
        help="validate TAG against genbox_version.py and exit without packaging",
    )
    args = parser.parse_args()

    if args.validate_release_tag is not None:
        try:
            validate_release_tag(args.validate_release_tag)
        except SourcePackagingError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"release tag verified: {args.validate_release_tag}")
        return 0

    output = args.output.resolve()
    source_commit = None
    if not args.docker_only:
        try:
            source_commit = resolve_source_commit(args.source_commit)
        except SourcePackagingError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="genbox-package-licenses-") as temporary:
        if args.licenses_dir:
            licenses = validate_collected_licenses(args.licenses_dir.resolve())
        else:
            licenses = collect_runtime_licenses(Path(temporary) / LICENSE_DIRECTORY)
        packaged_licenses = license_entries(licenses)

        docker_zip = output / f"{APP_NAME}-Docker-Compose-v{__version__}.zip"
        write_zip(
            docker_zip,
            [
                (ROOT / "docker-compose.yml", "docker-compose.yml"),
                (ROOT / ".env.docker.example", ".env.example"),
                (ROOT / "docs" / "DOCKER-QUICKSTART.md", "README.md"),
                (ROOT / "LICENSE", "LICENSE"),
                (ROOT / "COPYRIGHT", "COPYRIGHT"),
                (ROOT / "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
                *packaged_licenses,
            ],
        )
        artifacts = [docker_zip]

        if not args.docker_only:
            source_zip = output / f"{APP_NAME}-Source-v{__version__}.zip"
            try:
                assert source_commit is not None
                write_source_archive(source_zip, source_commit, packaged_licenses)
            except SourcePackagingError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
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
