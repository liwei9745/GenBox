# Current Project Status

**Last updated:** 2026-07-23
**Current branch:** `codex/p4-deploy-plan-ux-eai`
**Current phase:** Phase 4 Single-Image Push End To End - **In Progress**

## Current evidence

- **VERIFIED 2026-07-23:** GenBox commit
  `656e4c773eda6990f3c7a2f5e4ea68286db87593` locally implements Deployment
  Safety Contract v3 and the host-identity UX correction. The saved trust record
  is the canonical SSH host-key algorithm plus `SHA256:` fingerprint pair.
  Current first-time confirmation remains manual; this commit does not implement
  trusted SSH-session pairing.
- **VERIFIED 2026-07-23:** focused and full local verification completed with
  `480 passed`. Independent fixed-commit architecture, security, and regression
  reviews each returned **APPROVE**. This is local evidence only.
- **VERIFIED 2026-07-22:** chatgpt2api sender implementation exists at
  `f4a327d5599b020c66d4aab041a5fa0035d5effe`. Its existence does not prove the
  GenBox receiver/deployment candidate or an end-to-end transfer.
- **UNVERIFIED:** a real isolated-VPS, browser-driven, single-image Push end to
  end. No local/mock test, status panel, plan, or sender commit substitutes for
  an authenticated receipt, matching SHA-256, metadata result, idempotent retry,
  source-retention result, and production non-mutation check.
- **VERIFIED 2026-07-23:** production chatgpt2api remains outside the mutation
  scope. Host, port, container, and credential facts are intentionally absent
  without fresh dated discovery evidence.

## Phase 4 boundary

Phase 4 is not complete. Its acceptance is phase-scoped: one newly generated
image from an isolated development clone imports once with available metadata;
retry is idempotent; failure retains the source; relevant receiver and sender
tests pass. Batch/scheduling are Phase 5. Cleanup is Phase 6. Clean GitHub
redeployment and upstream/release publication are separate authority and
completion gates.

## Exact next step

Implement trusted SSH-session pairing locally for personal users. A user with an
already trusted SSH terminal session will run a GenBox-generated fixed one-line
helper and paste its one-line response back. The future exchange must be
short-lived, single-use, in-memory, bound to the saved target identity version
and candidate canonical host-key pair, and re-probe before saving trust. Add
focused tests, freeze a commit, and obtain independent fixed-commit review.
Only then seek separate authorization for remote discovery or isolated
VPS/browser single-image E2E.

## Resume constraints

- Require SSH host-key verification; production is read-only and all development
  resources must be isolated.
- Trusted SSH-session pairing is planned, not implemented. Its external trusted
  terminal/known-host record is an initial trust anchor, not VPS ownership
  evidence or an SSH credential substitute. Do not record its challenge,
  response, command, raw pairing observations, or credentials in
  persisted/public state, logs, browser storage, screenshots, URLs, or Git.
  The canonical trust pair is the only permitted saved outcome.
- Keep administrator, Push, management, SSH, and enrollment secrets separate
  and out of URLs, browser storage, Git, ordinary logs, screenshots, and status
  text.
- Source deletion remains disabled unless an authenticated receipt, matching
  SHA-256, `safe_to_delete_source=true`, and explicit user opt-in all exist.
- Record any later isolated-E2E evidence as **VERIFIED**, **USER-CONFIRMED**, or
  **UNVERIFIED** as appropriate; never describe local evidence as real E2E.
