# Phase 9 Sender Push Source Cleanup (User-Selected) - Implementation Plan

**Status:** Implementation complete in isolated worktrees; delivery gates open
**Date:** 2026-08-21
**Branch:** `codex/phase7-campaign-20260820`; sender code lives in the isolated
chatgpt2api fork worktree
**Topic contracts:** `docs/INTEGRATION.md`,
`docs/chatgpt2api-push-integration.md`, `docs/DEVELOPMENT-LIFECYCLE.md`

## Objective

Let the chatgpt2api sender delete a source image only after a GenBox push
receipt confirms the transfer, with the **user deciding per action** (manual
one-shot and scheduled forwarding) whether to delete the source image. Deletion
is never a forced fixed choice.

## Read-Only Inventory (2026-08-20, no production/WIP touched)

Sender worktree:
`E:\AI\chatgpt2api-worktrees\phase6-final-gate-20260809`
(branch `codex/phase6-final-gate-20260809`, head `19c2fdb`, 515 commits ahead of
upstream main).

Reusable existing modules (sender side):

- `services/genbox_push_cleanup.py` (60 KB) - `GenBoxPushCleanupService` with:
  - `policy_enabled()` reading `cleanup_enabled` from settings.
  - `record_receipt(source_id, remote_path, ..., safe_to_delete_source)` that
    only promotes a record to `receipt-confirmed` when
    `safe_to_delete_source is True`.
  - `_inspect(record)` -> `(decision, reason, size)` where a non-`True`
    `safe_to_delete_source` yields `retained` (line ~749).
  - `run(dry_run=True|False)` with durable state machine
    (`deleted` / `deleting` / `delete_failed` / `delete_unknown`) and
    per-record audit events. Execute requires both `policy_enabled()` and
    `environment_gate.can_execute()`.
  - `CleanupEnvironmentGate` (`can_execute`, `runtime_identity_digest`,
    `destination_trusted`) enforcing isolated-runtime identity so cleanup
    cannot run against production hosts.
  - Source-bytes identity is enforced before the storage boundary (digest must
    match the receipt SHA-256).
- `services/cleanup_attestation.py` / `cleanup_attestation_anchor.py` -
  attestation anchoring for auditable cleanup decisions.
- `scripts/issue_cleanup_attestation.py`,
  `scripts/start_isolated_cleanup_runtime.py` - operational scripts for
  isolated runs.
- `api/genbox_push.py` - push API endpoints on the sender side.

Gap to the ADR-026 decision: the existing executor is policy-enabled globally
(dry-run preview vs execute), not per-action user selection. The per-run
selection for manual one-shot and scheduled forwarding is the new UI/API
surface this phase adds; the receipt/identity/digest gating already exists and
is reused unchanged.

## Workstream Boundary

- This repository (GenBox receiver): design and scoped release of a grant path
  capable of returning `safe_to_delete_source=true` only under the matching
  authenticated receipt + source-bytes SHA-256 match. v2.6.0 behavior
  (`main.py:3621` -> `false`) stays until that path is implemented, tested, and
  released under the scoped release process.
- Sender fork (chatgpt2api): per-action user selection surfaced in
  manual one-shot and scheduled flows, wired to the existing
  `GenBoxPushCleanupService` with dry-run preview before each execute.

## Plan / Milestone Steps

1. **Receiver grant path (GenBox side, this repo, after this plan is gated):**
   - Add a scoped, default-disabled receiver capability that can issue
     `safe_to_delete_source=true` only after: authenticated source,
     valid receipt flow, and source-bytes SHA-256 match.
   - Keep `false` default and wired regression tests; update `INTEGRATION.md`
     commit-semantics wording coordinated with Phase 8 proposal PRs.
2. **Sender per-action selection (fork side, isolated clone):**
   - Manual one-shot Push: expose a per-run "delete source after confirmed
     push" checkbox, default off, wired to
     `GenBoxPushCleanupService.run(dry_run=False)` with a dry-run preview
     first.
   - Scheduled push: per-schedule-run user confirmation with the same boundary;
     deletion disabled unless the user selected it for that run.
3. **Tests:** manual-selection, scheduled-selection, receipt mismatch retains
   source, `false` never deletes, deletion disabled in development,
   identity-gate blocks production hosts.
4. **Delivery:** sanitized sender code as narrow PRs per Phase 8 practice;
   receiver change via scoped release after clean-deployment evidence.

## Acceptance Criteria (from ROADMAP Phase 9)

- Deletion only when: user selected it for that manual or scheduled run AND
  authenticated matching receipt with `safe_to_delete_source=true` AND source
  bytes match receipt SHA-256.
- Without selection, `false`, or any mismatch: source always retained.
- Deletion disabled in development; requires explicit per-run, per-user
  selection in production.
- Receiver default and `main.py:3621` boundary updated under scoped release
  process with regression tests; historical `false` records kept as audit
  trail.
- No real media, credentials, or VPS identities in tests/fixtures/PRs.

## Gates / Next Decision

Implementation is complete in isolated worktrees. The remaining gates are:

- GenBox: scoped release of the receiver grant path, followed by clean-deploy
  verification; v2.6.0 remains unchanged.
- yukkcat: PR #26 is open from the independent fork
  `liwei9745/chatgpt2api-yukkcat`, based on `9d3e6fc`, with one focused commit
  `739eef6`.
- GenBox receiver UI: the per-source grant checkbox is now wired to the
  managed-source PATCH endpoint, defaults off, and passes the full `619-test`
  receiver suite.
- A static browser contract test now protects the grant checkbox, PATCH wiring,
  rollback, and offline lock; the full GenBox suite is `620 passed`.
- Rejection recovery: preserve the fork and rejected commit, create a new branch
  from the latest upstream `main`, apply only requested review changes, rerun
  build/validation, and submit a replacement PR. Never overwrite upstream main.

No production container, tag, release, or upstream main branch is changed by
this plan. The next local development task is receiver release-readiness
verification and documentation, not another unrelated feature phase.

Next local work: Phase 10 first Store slice is now in progress; PR #26 remains
external review gate.
