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
the source ZIP with the Docker and desktop artifacts. Workflow permissions
default to `contents: read`; only the final release job receives
`contents: write`. Desktop runtime smokes remove Python host-environment paths
and user-site imports. The Windows smoke uses a unique GUID-named directory
under `RUNNER_TEMP` and removes only that owned directory in `finally`.

The Docker publishing workflow applies the same tag/version gate before its
build job. It builds the publishable image once with Buildx and loads that exact
image locally. Runtime-import and loopback HTTP smoke checks run against the
Buildx-reported immutable image ID. The HTTP smoke creates a random-name
container with a per-run ownership label; cleanup requires the recorded
container ID and label to match, so a failed name collision cannot delete a
pre-existing resource. Readiness requires the production setup-status JSON
contract, and bounded failure logs are credential-redacted.

The read-only build job saves that exact smoked image, uploads it as a
short-retention workflow artifact, and exposes its Buildx image ID and generated
tag list as job outputs. A separate publish job is the only Docker job with
`packages: write`; it downloads and loads the saved image, verifies that its
local image ID still equals the Buildx-reported ID, then applies each registry
tag, re-verifies every tag ID, and calls `docker push` without rebuilding.

All external workflow actions in every `.github/workflows/*.yml` file, including
the pull-request quality gate, are pinned to the full commit IDs resolved from
their official version tags. The human-readable `# vX` comments record the
reviewed tag lineage without making the mutable tag the execution reference.
Repository-local `./` actions remain allowed. The pull-request workflow keeps
top-level `contents: read`; uploading test evidence through
`actions/upload-artifact` does not require repository-content write permission.
Packaging regression coverage scans every workflow and rejects an unknown
external action, a mutable tag or branch reference, an unexpected commit, or a
missing reviewed-tag comment.

## Verification

Run the packaging tests and syntax check before release review:

```text
python -m pytest -q tests/test_release_packaging.py
python -m py_compile scripts/package_release.py
bash -n .github/scripts/docker-release-http-smoke.sh
git diff --check
```
