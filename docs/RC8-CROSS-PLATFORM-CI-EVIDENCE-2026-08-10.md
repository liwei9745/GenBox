# RC8 Cross-Platform CI Evidence

**Date:** 2026-08-10
**Scope:** candidate-only workflow trigger wiring and hosted packaging evidence
**Evidence branch:** `codex/rc8-cross-platform-ci-20260810`
**Evidence commit:** `08abac5309855533d2930f7b2e06f7e660048602`
**Source candidate commit:** `9b5ac7ca7153479ad969e70bfe3c1bc42b71b320`
**Candidate code baseline:** `07b89abc4bd0297cf665516c037a95152c78f8fa`

## Changes

- `.github/workflows/build.yml` now includes the exact RC8 candidate branch in
  its `push.branches` filter. Its existing manual `workflow_dispatch` trigger
  is unchanged.
- `.github/workflows/docker.yml` keeps publication limited to `master`, `dev`,
  and version tags. It exposes a manual `workflow_dispatch` path for candidate
  verification, skips registry login for that path, and sets the build action's
  `push` flag only for ordinary push events.
- `.github/workflows/build.yml` includes the exact RC8 candidate branch for
  desktop build verification. The release job additionally excludes manual
  dispatch, so a candidate verification run cannot create a GitHub Release.
- No product source, packaging script, Dockerfile, or release metadata was
  changed.

## Locally Verified

- `git rev-parse HEAD` matches the candidate commit above.
- PyYAML successfully parsed both workflow files.
- The desktop workflow contains the exact candidate branch and both workflows
  expose `workflow_dispatch`.
- The Docker workflow does not contain the candidate branch in its automatic
  `push.branches` filter.
- Docker candidate verification does not log in or publish an image; ordinary
  `master`/`dev`/tag push behavior remains unchanged.
- Manual desktop candidate verification cannot enter the release job.
- `git diff --check` completed successfully. Git reported only its normal
  working-copy LF/CRLF conversion warning for these workflow files.

## Hosted Run

- **Run:** `31357670110` (`workflow_dispatch`, ref
  `codex/rc8-cross-platform-ci-20260810`, head SHA
  `08abac5309855533d2930f7b2e06f7e660048602`).
- **Quality:** `Test release source` job `93360309578` — `success`.
- **Windows:** job `93360494585` — `success`; artifact
  `GenBox-Windows-x64`, digest
  `sha256:a24853c3f37bca33a4f1e2c3b3855afa615e413b2a234eba710e5bf939e0650b`.
- **macOS:** job `93360494560` — `success`; artifact `GenBox-macOS`, digest
  `sha256:9b8fae965c24dfdb5a1eac2282feb298abf22f6d0843c9374aa5f7351b7b4258`.
- **Linux:** job `93360494573` — `success`; artifact `GenBox-Linux-x64`, digest
  `sha256:125a0d7e1912950e86738674d6cedb0c5974de693e4445d23c38f0b5428ee9dd`.
- **Release job:** `Create Release` job `93360687538` — `skipped`; no tag or
  GitHub Release was created.

The hosted jobs checked out the evidence commit above. Product source and
packaging behavior are unchanged from the source candidate; only workflow and
evidence documentation are added on this branch.

## Unverified / External Boundaries

- Docker registry publication was not attempted. The Docker workflow's manual
  dispatch path skips registry login and forces `push: false`; local Compose
  evidence is recorded separately.
- VPS/SSH, sender-side E2E, source cleanup/unlink/execute markers,
  `33010`/`33018`, real credentials, real media, tags, and formal Releases were
  not used and remain outside this evidence branch.
- No release tag, GitHub Release, deployment, or production endpoint was
  touched.
