# P4 Remote Preflight

**Date:** 2026-07-23
**Scope:** Phase 4 isolated VPS/browser single-image E2E preparation

## Current Local Baseline

- Current branch: `codex/p4-deploy-plan-ux-eai`
- Current local candidate commit: `b037c9d`
- Prior pairing implementation commits:
  - `5397141`
  - `6f8c710`
  - `b037c9d`

## Local Verification Snapshot

- Targeted pairing and trust-update regression checks passed locally on
  2026-07-23:
  - `python -m pytest tests/test_extensions.py -k "cross_thread_compare_and_swap or target_identity_generation_survives_delete_and_recreate or pairing"`
  - result: `6 passed, 164 deselected`
- `python -m py_compile extensions/store.py main.py` passed.

## Known Local Reality Before Remote Work

- `docs/STATUS.md` is stale for the pairing line of progress and should not be
  treated as the source of truth for the latest local implementation commit.
- The worktree currently contains uncommitted documentation/planning changes
  unrelated to the remote E2E itself.
- Real isolated VPS/browser single-image E2E remains **UNVERIFIED**.

## Recommended Freeze Before Remote E2E

Before any live remote verification, freeze a clean local basis:

1. Decide whether the current documentation/planning edits should be committed
   separately or temporarily set aside.
2. Use a clean, known commit identity for the remote session.
3. Record that commit identity as the exact GenBox receiver candidate under test.

## Stage 1: Read-Only Discovery Checklist

These steps are authorized only as read-only discovery against the intended
isolated development target or its source of truth.

1. Confirm the intended VPS target and canonical SSH host-key trust pair.
2. Confirm that the target is the isolated development clone, not production.
3. Capture source container, Compose project, image, mounts, ports, labels,
   health, and data size.
4. Capture destination capacity and port conflicts.
5. Produce a no-mutation clone or test plan if any ambiguity remains.
6. Review every remote command for source mutation before execution.

## Required Evidence For Read-Only Discovery

- Timestamped discovery output with secrets removed
- Source identifiers and pre-test health
- Destination directory, port, Compose project, and instance ID
- Required space calculation
- Rollback and cleanup target limited to owned development resources

## Stage 2: Isolated E2E Preconditions

Do not start the single-image E2E unless all are true:

- The target under test is the isolated development clone
- Production source remains outside mutation scope
- Host-key trust is confirmed
- The final GenBox destination URL is the intended private path
- Sender commit identity is known
- Receiver commit identity is known
- Source retention remains enabled
- A rollback target exists and is limited to development resources

## Stage 3: Single-Image E2E Acceptance Matrix

The remote E2E is not complete unless the session captures:

1. One newly generated image is pushed from the isolated clone
2. GenBox imports it once
3. The authenticated receipt matches the image SHA-256
4. Available metadata is retained
5. Retrying the same request is idempotent
6. Source retention remains correct on failure and on the non-cleanup path
7. Production non-mutation is re-checked after the run

## Immediate Stop Conditions

Stop and review immediately if any of the following appear:

- target or source identity is ambiguous
- a planned command can mutate production
- clone and source paths, ports, or Compose identities overlap
- a secret appears in output that would be persisted or committed
- rollback cannot be limited to owned development resources
- production health changes during discovery or test work

## Next Practical Step

Do not begin live VPS/browser E2E from the current dirty worktree state.

First freeze the local basis for the remote session, then begin Stage 1
read-only discovery on the isolated target only.
