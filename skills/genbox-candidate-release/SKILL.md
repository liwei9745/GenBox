---
name: genbox-candidate-release
description: Audit and prepare a GenBox experimental or candidate client and Docker image, using local smoke tests, digest-to-commit evidence, secret scanning, and explicit phase-gate reporting.
---

# GenBox Candidate Release

Use this skill for a local `experimental` or `candidate` release rehearsal. A
separately user-authorized candidate publication may create a GitHub Pre-release
and a candidate-only image tag; it never authorizes a stable release, `latest`,
`stable`, or VPS operation.

## Read First

1. `AGENTS.md`
2. `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, and `docs/STATUS.md`
3. The active phase in `docs/ROADMAP.md`
4. `docs/DEVELOPMENT-LIFECYCLE.md`

Treat `.planning/` as historical input only. Do not update a roadmap phase to
complete unless its documented acceptance evidence exists.

## Candidate Boundary

- Use a unique local image tag such as `genbox:<version>-candidate-<commit>`.
- Never use `stable`, `latest`, production ports, VPS/SSH, real credentials, or
  a user media directory.
- Bind all local probes to a dynamically selected loopback port.
- Keep candidate runtime storage and logs in a temporary directory; remove only
  resources created by the candidate run.
- Record unavailable Docker, Compose, GitHub, or Windows evidence as
  `UNVERIFIED`, not as a pass.

## Loop

1. Capture the exact Git commit and require a clean or explicitly scoped
   candidate diff. For separately authorized publication, create one unique
   annotated candidate tag only after all assets are rebuilt from that commit.
2. Run focused tests, the full applicable test suite, JavaScript syntax checks,
   and `git diff --check`.
3. Build the Windows client locally when the PyInstaller toolchain is present,
   then run `scripts/smoke_client.py` against a dynamic loopback port.
4. Build a local candidate Docker image only when the Docker daemon is
   available. Record the immutable image ID/digest and OCI revision together
   with the source commit. Run an isolated Compose loopback probe with generated
   throwaway administrator and Push keys that never enter Git or ordinary logs.
5. Generate the Docker Compose bundle twice and require matching SHA-256 values.
6. Scan tracked files, the candidate diff, generated bundle contents, and Git
   history for secrets and personal data. Known test sentinels are findings to
   classify, never silently suppress.
7. Inspect workflows for candidate-safe triggers/tags: candidate/rc tags must
   create Pre-releases and must not emit semver aliases, `latest`, or `stable`.
   Capture a workflow run URL or mark GitHub Actions evidence `UNVERIFIED` when
   no authenticated query is available.
8. Update `docs/STATUS.md`, `HANDOFF.md`, and a phase-gate matrix with dates,
   commands, results, commit identity, limitations, and the next safe action.

## Failure Lessons

- ZIP output is not reproducible if entry order, timestamp, operating-system
  metadata, or permissions inherit from the host. Fix all four and add a
  byte-for-byte repeat-build regression test.
- A Docker CLI binary is not a Docker daemon. Check daemon access before
  claiming an image or Compose smoke test ran.
- A passing GenBox Push receiver test is not proof that the chatgpt2api sender,
  private network, batch scheduler, cleanup, GitHub redeployment, or upstream
  delivery is complete.
- Historical secret-pattern matches in test fixtures require review. Only a
  real secret or personal data finding blocks publication; retain the evidence
  and explain any benign sentinel.

## Completion Record

Report candidate readiness separately from product-phase readiness. Include:

- Candidate commit and artifact SHA-256 or image digest.
- Passed local gates and `UNVERIFIED` gates.
- Secret-scan scope and findings.
- GitHub Actions evidence or why it is unavailable.
- Phase 6-9 blockers and the next permitted action.
