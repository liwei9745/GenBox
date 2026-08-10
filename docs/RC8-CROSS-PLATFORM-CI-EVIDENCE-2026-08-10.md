# RC8 Cross-Platform CI Evidence

**Date:** 2026-08-10
**Scope:** candidate-only workflow trigger wiring
**Candidate branch:** `codex/v2.6.0-rc.8-final-candidate`
**Candidate commit:** `9b5ac7ca7153479ad969e70bfe3c1bc42b71b320`

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

## Unverified / Pending Hosted Evidence

- No GitHub Actions run was started from this local validation pass, so there
  is no hosted run ID or cross-platform artifact result to claim here.
- Windows, macOS, and Linux packaging remain `UNVERIFIED` until the candidate
  branch is dispatched or pushed in GitHub Actions. Docker candidate
  verification and registry publication also remain `UNVERIFIED` because no
  hosted run was started; the local workflow contract prevents candidate
  publication.
- No release tag, GitHub Release, deployment, or production endpoint was
  touched.
