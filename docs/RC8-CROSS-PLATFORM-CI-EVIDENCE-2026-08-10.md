# RC8 Cross-Platform CI Evidence

**Date:** 2026-08-10
**Scope:** candidate-only workflow trigger wiring and hosted packaging evidence
**Evidence branch:** `codex/rc8-cross-platform-ci-20260810`
**Hosted source commit:** `e0daf610e1934d78032123b4b4a6c0c62cfdb339`
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

- **Run:** `31358450150` (`workflow_dispatch`, ref
  `codex/rc8-cross-platform-ci-20260810`, head SHA
  `e0daf610e1934d78032123b4b4a6c0c62cfdb339`).
- **Quality:** `Test release source` job `93362426783` — `success` (`617 passed`).
- **Windows:** job `93362617749` — `success`; artifact
  `GenBox-Windows-x64`, digest
  `sha256:ff3a0a0320fe22fac6fa639fc4e1441bc8f4ebc6ccb646096f70eb504b7fbb6c`.
- **macOS:** job `93362617735` — `success`; artifact `GenBox-macOS`, digest
  `sha256:6610e957d918d617d298f7ef25b1ef70ac435de046a3514fec675125a0997a2f`.
- **Linux:** job `93362617747` — `success`; artifact `GenBox-Linux-x64`, digest
  `sha256:454ba2a12fcddc88d44d8b12d86f1cca830e93d9126d43a6522fc2187083ce6e`.
- **Release job:** `Create Release` job `93362921400` — `skipped`; no tag or
  GitHub Release was created.

The hosted jobs checked out `e0daf61`, whose only changes from the source
candidate are workflow wiring and evidence documentation. This document may
receive a later docs-only commit; the hosted source SHA above remains the
tested code/workflow snapshot.

## Unverified / External Boundaries

- Docker registry publication was not attempted. The Docker workflow's manual
  dispatch path skips registry login and forces `push: false`; local Compose
  evidence is recorded separately.
- VPS/SSH, sender-side E2E, source cleanup/unlink/execute markers,
  `33010`/`33018`, real credentials, real media, tags, and formal Releases were
  not used and remain outside this evidence branch.
- No release tag, GitHub Release, deployment, or production endpoint was
  touched.
