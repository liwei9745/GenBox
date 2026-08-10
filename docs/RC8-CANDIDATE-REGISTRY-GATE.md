# rc.8 Candidate Registry Gate

**Date:** 2026-08-10
**Status:** PUBLISHED / VERIFIED (non-release candidate only)

## Fixed Candidate Identity

- Workflow branch: `codex/phase6-release-gates-20260810`
- Frozen build source: `9b5ac7ca7153479ad969e70bfe3c1bc42b71b320`
- Repository allowlist: `liwei9745/GenBox`
- Only permitted image reference:
  `ghcr.io/liwei9745/genbox:candidate-9b5ac7c`

The workflow checks out the frozen source SHA directly after its manual
dispatch gates pass. The branch that holds the workflow may advance without
changing the container source that can be published.

## Publish Controls

`.github/workflows/docker.yml` preserves its existing `master`, `dev`, and
`v*` push triggers. The candidate publish job can run only through
`workflow_dispatch`, with `candidate_publish` defaulting to `false`; the
ordinary build job is skipped for that manual dispatch. The publish job is
skipped unless the caller selects the named workflow branch, sets the boolean
to `true`, and supplies the exact SHA and immutable candidate tag above.

The job then requires the existing Actions `GITHUB_TOKEN` to authenticate to
GHCR and performs a read-only GitHub Packages lookup for `genbox` before
Buildx starts. A missing package is accepted for first publication, while
transport or authorization errors fail closed. It refuses to overwrite an
existing version carrying the candidate tag. Authentication, package lookup,
or tag-availability failure stops the run before an image build or push. The
build action has one fixed image tag only; it does not create floating, branch,
SHA, latest, stable, or default tags.

The desktop-client release workflow remains separately tag-gated; this candidate
workflow does not create a Git tag, a GitHub Release, release assets, or a
package promotion.

## Evidence Status

- **Registry target / local account:** read-only lookup confirms the existing
  `liwei9745/genbox` package is reachable from the local authenticated account.
- **Existing image manifest:** the pre-existing `2.5.1` package reference is
  inspectable as `linux/amd64`. It is not rc.8 evidence and is not promoted by
  this change.
- **Candidate tag availability:** a read-only package-version inspection found
  97 existing versions and no `candidate-9b5ac7c` tag before dispatch. The
  workflow repeated that check with its Actions token and then created the one
  permitted candidate version; subsequent candidate-tag reuse is refused.
- **Candidate CI authentication, package write authorization, candidate image
  digest, and candidate runtime health:** **VERIFIED** by Actions run
  `31367080617`. The run checked out the frozen SHA, pushed only
  `candidate-9b5ac7c`, resolved immutable digest
  `sha256:f6dea5c48a56ca0f823ed229c07f20586f80906cf6c4029cdcbe989fdd7f171b`,
  inspected it by digest, and passed the temporary loopback health check.
- **Cross-platform evidence:** `docs/STATUS.md` records a local Windows package
  smoke for the rc.8 code candidate. Exact-candidate hosted CI and macOS
  evidence remain **UNVERIFIED**; no prior result is being relabeled.

One candidate image build and push was performed by the verified Actions run
above. No Git tag, GitHub Release, formal-version image tag, remote deployment,
or VPS operation was performed.
