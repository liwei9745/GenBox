# Phase 6 Isolated Drill Authorization Package

**Prepared:** 2026-08-09  
**Status:** review-only; no execution authority granted

This package is a one-time human review checklist for a future isolated Phase
6 drill. It does not authorize cleanup, deployment, a VPS connection, an
execute marker, Phase 6 completion, Phase 7 work, or release work.

## Evidence Being Reviewed

- GenBox commit `4813562e23d63c55f119a1d8f2e8f8192496c751` adds a disposable
  loopback-only receiver contract test and synchronizes Phase 6 facts.
- Sender commit `1d67d06db888604183f8933012fe06a99c897c7b` removes raw source and
  runtime-identity values from cleanup public/audit projections and adds
  regressions.
- Local verification recorded for this convergence run: GenBox `611 passed`;
  Sender `185 passed, 18 explicit skips`; Sender Docker smoke passed with an
  internal network, generated credentials, and synthetic PNG data.
- Independent review passed the candidate diffs. Opt-in Docker integration,
  isolated-VPS acceptance, real host authority/runtime logs, human
  authorization, and destructive cleanup remain external gates.

## Required Human Decision

All approvers must review the exact commits above and explicitly choose one of
the following before any future drill work begins:

- **Decline:** keep Phase 6 blocked. No follow-up action is authorized.
- **Authorize planning only:** permit a new, non-destructive isolated-drill
  plan. No cleanup, execute marker, deletion, deployment, or remote access is
  authorized.
- **Authorize a separately specified drill:** only after a new plan names the
  exact disposable environment, synthetic fixtures, rollback method, command
  allowlist, and stop conditions. This package alone is insufficient.

## Non-Negotiable Drill Boundaries

- Use a newly created disposable environment and temporary directories only.
- Use generated source IDs, Push keys, credentials, and synthetic media only.
- Do not access a VPS, SSH, production service, real user data, or real media.
- Do not use ports `33010` or `33018`.
- Keep cleanup disabled. Do not create, accept, or invoke an execute marker.
- Do not perform `unlink`, deletion, deployment, restart, release, tag, or
  Phase 7 implementation.
- Stop immediately on any indication that the target is not disposable or that
  real data, authority, credentials, or production access could be involved.

## Required Preflight Evidence

Before a separately authorized drill, the designated operator must attach:

- Exact Git commit IDs and clean-worktree output for both repositories.
- The isolated target's written ownership and disposability attestation.
- A redacted command allowlist that cannot reach non-loopback or non-temporary
  paths.
- A generated-fixtures inventory proving no real credential or media exists.
- A rollback/teardown record and a statement that no deletion pathway is
  reachable.
- Fresh independent review of the proposed drill diff and command plan.

## Approval Record

| Role | Name | Decision | Date (UTC) | Notes |
| --- | --- | --- | --- | --- |
| Security reviewer |  |  |  |  |
| System owner |  |  |  |  |
| Designated operator |  |  |  |  |

An incomplete, ambiguous, or conditional record is a decline. Phase 6 remains
**In Progress / Destructive Execution Blocked** until every external gate is
separately satisfied and explicitly approved.
