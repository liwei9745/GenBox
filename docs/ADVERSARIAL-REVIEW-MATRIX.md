# Adversarial Review Matrix

This matrix is the short, reusable checklist for high-risk GenBox loops. It
does not authorize an operation; it defines what must be disproven before the
operation is accepted.

## Review Protocol

1. Freeze the exact commit or diff and record the task card.
2. Give the reviewer sanitized inputs and explicit owner exclusions.
3. The reviewer attempts failure, replay, overlap, and scope-boundary cases
   without changing code or remote state.
4. Record each result as `PASS`, `FAIL`, or `NOT RUN` with evidence class.
5. Any P1 stops the loop. The writer may resume only after findings are
   accepted and the snapshot is re-frozen.

## Matrix

| Area | Attack question | Required evidence | Stop condition |
| --- | --- | --- | --- |
| Target identity | Could the operation reach the wrong host or instance? | Verified host key, opaque handle resolution, ownership marker | Ambiguous identity or mismatch |
| Secret lifetime | Can a password, key, token, or Push key reach a URL, log, task, browser storage, or Git? | Sanitized diff, route projection, log review | Any secret exposure or unsafe persistence |
| Remote command scope | Can browser input become arbitrary shell or an unbounded path? | Fixed command plan and request schema review | Browser-supplied shell or unconstrained path |
| Isolation | Can a clone share directory, volume, port, Compose project, source ID, or management key with production? | Discovery evidence and non-mutation check | Any overlap or missing rollback owner |
| Idempotency | Does replay import twice or produce conflicting state? | Same request twice, receipt status, SHA-256, media count | Duplicate import or unverified success |
| Interruption | What happens if the sender or worker stops during `sending`? | Restart during an active batch, durable post-restart state | Lost item, silent skip, or unsafe deletion |
| Lease contention | Can two workers claim the same schedule or item? | Independent worker overlap with durable lease outcome | Two owners or unverifiable ownership |
| Retry boundary | Are only temporary failures retried and is the retry bounded? | Failure classification, attempt count, backoff, terminal state | Infinite retry or retry of auth/invalid data failure |
| Source retention | Can a source disappear before an authenticated success receipt? | Cleanup disabled, failed/pending source inspection | Deletion without matching receipt and opt-in |
| Recovery UX | Can a novice tell what happened and what to do next? | Refresh/reload state, visible action, localized error | UI claims success without backend evidence |

## Phase 5 Minimum Gate

Phase 5 cannot be marked complete until the following are all `PASS` on the
isolated development clone:

- manual batch resumes after a sender-process interruption;
- overlapping workers produce one durable lease owner and no duplicate work;
- late files inside the scan range are discovered;
- failed-only retry does not resubmit successful items;
- source images remain retained for every failed, pending, and idempotent
  outcome;
- production health and data remain unchanged.

Local tests and a browser refresh are useful supporting evidence, but do not
replace the two live checks above.
