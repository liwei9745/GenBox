# Release Packaging

`scripts/package_release.py` has two packaging paths:

- `--docker-only` builds the Docker/Compose bundle from the current checkout.
  This path does not require a clean Git worktree.
- The source bundle is bound to one immutable Git commit. It never copies
  files directly from the working tree.

## Source Bundle

Create and review the release commit first, then run the packager with its full
commit ID (or another revision that resolves to the current `HEAD`):

```text
python scripts/package_release.py --output artifacts --source-commit <sha>
```

The source path fails closed when the revision is invalid, does not resolve to
`HEAD`, or the worktree contains staged, unstaged, or untracked files. Commit
the complete candidate and rerun the command; do not use an uncommitted tree
as a release source.

The resulting ZIP contains the exact Git-archive view and bytes from the frozen
commit, plus the generated `THIRD_PARTY_LICENSES/` sidecar. The sidecar is
validated against the pinned runtime-license manifest and is included in both
Docker and source bundles. The source archive is assembled in a temporary file
and is published only after the commit tree and sidecar have been written.

Git-native `export-ignore` rules remove internal planning, handoff, review, and
Phase 10 evidence documents from the public source view without changing the
frozen commit. Product, architecture, status, roadmap, release, and operator
documentation remain included. Packaging tests create a real Git archive and
scan its exported text for host-local user paths and high-confidence credential
shapes. They also reject runtime vault/media data, ONNX or compiled/archive
binaries, and image metadata beyond the minimal JFIF container fields used by
the public screenshots.

For tag-triggered releases, `.github/workflows/build.yml` first validates that
the canonical `v`-prefixed tag exactly matches `genbox_version.__version__`.
Every quality, desktop-build, and release job depends on that gate. The release
job passes `${{ github.sha }}` as `--source-commit`, then checksums and uploads
the source ZIP with the Docker and desktop artifacts.

The Docker publishing workflow applies the same tag/version gate before its
build job. It builds the publishable image once with Buildx and loads that exact
image locally. Runtime-import and loopback HTTP smoke checks run against the
Buildx-reported immutable image ID. Before publishing, every generated registry
tag must still resolve to that same image ID; the workflow then uses
`docker push` for those already-smoked tags and does not rebuild the image.

## Verification

Run the packaging tests and syntax check before release review:

```text
python -m pytest -q tests/test_release_packaging.py
python -m py_compile scripts/package_release.py
git diff --check
```
