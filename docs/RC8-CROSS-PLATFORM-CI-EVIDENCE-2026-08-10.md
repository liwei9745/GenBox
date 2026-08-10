# RC8 Cross-Platform CI Evidence

**Date:** 2026-08-10
**Scope:** candidate-only workflow trigger wiring and hosted packaging evidence
**Evidence branch:** `codex/rc8-cross-platform-ci-20260810`
**Hosted source commit:** `9b5ac7ca7153479ad969e70bfe3c1bc42b71b320`
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

- **Run:** `31358814412` (`workflow_dispatch`, ref
  `codex/v2.6.0-rc.8-final-candidate`, head SHA
  `9b5ac7ca7153479ad969e70bfe3c1bc42b71b320`).
- **Quality:** `Test release source` job `93363442086` — `success` (`617 passed`).
- **Windows:** job `93363724112` — `success`; artifact
  `GenBox-Windows-x64`, digest
  `sha256:cdf3998e9d93fd385386d89f5f79dc622b5be719ccf44e91f9f05cd8c1b138a4`.
- **macOS:** job `93363724106` — `success`; artifact `GenBox-macOS`, digest
  `sha256:6d8755760085d3bc6f6c368587855a65b6bf78d6df7c93ed44719e4673c6debb`.
- **Linux:** job `93363724098` — `success`; artifact `GenBox-Linux-x64`, digest
  `sha256:dd9ccc6feada8b1c30b5e3bfe821fd07afd3138665f786d453b66f4218e8afdc`.
- **Release job:** `Create Release` job `93363969869` — `skipped`; no tag or
  GitHub Release was created.

This run checked out the original candidate commit itself. The evidence branch
contains only workflow wiring and dated documentation; its hosted run is kept
separate from this exact-candidate result.

## Unverified / External Boundaries

- Docker registry publication was not attempted. The Docker workflow's manual
  dispatch path skips registry login and forces `push: false`; local Compose
  evidence is recorded separately.
- VPS/SSH, sender-side E2E, source cleanup/unlink/execute markers,
  `33010`/`33018`, real credentials, real media, tags, and formal Releases were
  not used and remain outside this evidence branch.
- The independent release-gate pass also observed pre-existing orphaned
  SSH/WSL processes with remote-host command lines. They were not started or
  used by this run, no established session was part of the evidence, and owner
  attribution is required before any release approval.
- No release tag, GitHub Release, deployment, or production endpoint was
  touched.
