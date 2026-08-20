# Phase 7/8 Campaign Orchestration (GenBox)

**Status:** Active
**Date:** 2026-08-20
**Branch:** `codex/phase7-campaign-20260820`
**Base:** `03c46a4` (post v2.6.0 publish)

## Objective

Finish Phase 7 (Sanitized GitHub Redeployment) evidence, close Phase 8
(Upstream Delivery) by aligning the two open proposal PRs and the Vibe Coding
guide, and leave GenBox in a state where the next injection of distinct
workstreams (GenBox-Store foundations, sender-cleanup milestone) can start
without rework.

## Dependency Graph

```text
v2.6.0 published (done)
   |
   +-- P7.A Full-history secret/personal-data scan report  [need]
   +-- P7.B Clean-deploy repeated single+batch Push acceptance [need]
   |        (compose from Release asset + GHCR 2.6.0, then async sync-push tests)
   +-- P7.C Consolidated scan + deploy evidence in STATUS   [need]
   |
   +-- P8.A Align proposal PRs #387/#25 payloads w/ final guide [parallel]
   +-- P8.B Vibe Coding guide finalization (from Draft)        [parallel]
   +-- P8.C Compatibility/migration note in guide + INTEGRATION [need]
   |
   v
Campaign close: ROADMAP Phase 7/8 acceptance sweep + STATUS resume block
```

## Sizing Decisions (risk-based, not per-package)

- _No swarm concurrency for GenBox receiver work_: it is small, sequential,
  and every change re-touches the same 2 test files. Parallelism would create
  merge collisions, not throughput.
- _Loop engineering / single-writer is the mechanism_: maximize the current
  session utilization with compact, gated iterations and explicit checkpoints
  (below) instead of spawning agents over a tiny surface.
- _Fork/loop review gates_: each deliverable still passes the semantic +
  mechanical review pair before commit; this is the no-observation-reduction
  invariant of the "unique writer" policy.

## Per-Deliverable Gates

| Deliverable | Red line before commit |
|---|---|
| P7.A scan report | `git diff --check` ok; added-line port/secret scan zero; real ports/IP trivially redacted or labeled historical |
| P7.B clean deploy | compose up from Release asset; `safe_to_delete_source=false` observed; single + batch acceptance pass; teardown restores state |
| P7.C STATUS | commands + results + resume details only; no transient values copied |
| P8.A/B/C | two PRs remain OPEN; guide wording claims only *proposal* status; no env-specific values |

## Rollback Boundary

- `03c46a4` is the campaign base; any task that cannot be contained in
  `codex/phase7-campaign-20260820` restarts from this commit with corrected
  plan.
- No push/tag/Release/GHCR mutation, no prod VPS/SSH, no sender worktree
  changes (read-only), no `safe_to_delete_source` flip while scope-A governs.
- External PR branches are owned by the fork; PR edit history writes are kept
  to a minimum and only via `gh pr edit` for steering comments, never force
  rewrites after reviewers may have read them.

## Checkpoints

1. Done when: P7.A/B/C committed + STATUS resume block + ROADMAP acceptance
   sweep satisfied.
2. After checkpoint 1: decide store/workstream injection with explicit user
   gate (no silent phase self-promotion).
3. Any residual blockers (e.g., compose-on-Windows flakiness) become a
   documented non-claim, not a silent pass.

## Non-Goals (during this campaign)

- GenBox-Store code, sender cleanup milestone, new releases, tag pushes.
- Re-writing historical evidence text that contains port references; those are
  Phase 7 scan-report items labeled historical, not rewrites of audit trail.