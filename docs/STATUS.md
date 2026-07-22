# Current Project Status

**Last updated:** 2026-07-22
**Current branch:** `codex/p4-deploy-plan-ux-fix`
**Current phase:** Phase 4 Single-Image Push End To End — **In Progress**

## Current evidence

- **VERIFIED 2026-07-22:** GenBox commit `21972ff89419acb80288efdfdaa8750b7809a136`
  is a locally self-checked candidate, but it is independently **BLOCKED** for
  Deployment Safety Contract v3 implementation. In particular, binding
  multiplicity and complete TCP-listener payload handling must be enforced
  before any deployment plan can advance.
- **VERIFIED 2026-07-22:** the approved v3 contract is
  [`docs/deployment-invariants.md`](deployment-invariants.md). It is a
  design/implementation gate, not evidence of a deployment.
- **VERIFIED 2026-07-22:** chatgpt2api sender implementation exists at
  `f4a327d5599b020c66d4aab041a5fa0035d5effe`. Its existence does not prove
  the GenBox receiver/deployment candidate or an end-to-end transfer.
- **UNVERIFIED:** a real isolated-VPS, browser-driven, single-image Push end to
  end. No local/mock test, status panel, plan, or sender commit substitutes for
  an authenticated receipt, matching SHA-256, metadata result, idempotent retry,
  source-retention result, and production non-mutation check.
- **VERIFIED 2026-07-22:** the production chatgpt2api source remains outside
  the current mutation scope. Host, port, container, and credential facts are
  intentionally not recorded here without fresh dated discovery evidence.

## Phase 4 boundary

Phase 4 is not complete. Its roadmap acceptance is phase-scoped: one newly
generated image from an isolated development clone imports once with available
metadata; retry is idempotent; failure retains the source; relevant receiver and
sender tests pass. Batch/scheduling are Phase 5. Cleanup is Phase 6. A clean
GitHub redeployment and upstream/release publication are separate authority and
completion gates.

## Exact next step

Implement Deployment Safety Contract v3 locally against the fixed candidate:
enforce multiplicity-preserving binding comparison, complete TCP-listener
evidence, closed strategy/path conditions, in-memory-only execution snapshots,
public evidence manifests, reservation/CAS ordering, and post-creation
ownership-marker handling. Add the contract-driven focused tests, freeze the
commit, and obtain independent fixed-commit review. Do not start user
deployment, remote discovery, or VPS/browser E2E without separate authorization.

## Resume constraints

- Require SSH host-key verification; production is read-only and all development
  resources must be isolated.
- Keep administrator, Push, management, SSH, and enrollment secrets separate and
  out of URLs, browser storage, Git, normal logs, screenshots, and status text.
- Source deletion remains disabled unless an authenticated receipt, matching
  SHA-256, `safe_to_delete_source=true`, and explicit user opt-in all exist.
- Record any later isolated-E2E evidence as **VERIFIED**, **USER-CONFIRMED**, or
  **UNVERIFIED** as appropriate; never describe local evidence as real E2E.
