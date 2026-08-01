# Phase 6 Verified Source Cleanup Protocol Specification

**Status:** Proposed implementation and test contract. This document does not authorize deployment or deletion.

**Scope:** chatgpt2api sender behavior for the isolated development clone. The GenBox Push v1 receiver wire protocol is unchanged. Production cleanup is disabled and out of scope.

## 1. Safety Invariant And Authority Boundary

### Invariant

An unconfirmed, changed, missing, ambiguous, or failed source image survives. A source image may be deleted only after all of the following are true for the same transfer:

1. The user explicitly enabled the separate cleanup policy.
2. The sender has durably recorded a validated GenBox v1 success receipt.
3. The current source bytes hash to the receipt's SHA-256.
4. The receipt has the JSON boolean safe_to_delete_source: true.
5. The deletion target is the normalized, storage-rooted source path that was sent; it is not a symlink, traversal alias, or substituted file.
6. The isolated-development environment explicitly permits the cleanup test.

The default is retain. A failure to establish any condition is a successful retention decision, never a reason to retry deletion blindly.

### Authority Boundary

GenBox alone determines that it committed uploaded content, through its authenticated Push response. chatgpt2api alone determines whether the user enabled cleanup and performs the local deletion. Neither an HTTP 2xx status, the sender's own state, nor a UI request is deletion authority by itself.

Push v1 does **not** define a separately signed receipt. In this phase, "authenticated receipt" means the sender received the response directly from the configured Push destination during a request authenticated by the source-specific Push key, rejects redirects, and validates the v1 response fields below. The sender must not accept a receipt pasted into the UI, supplied by a browser, or reconstructed from a local success flag.

### Failure Behavior

On timeout, transport failure, non-success status, malformed response, incompatible version, source-ID mismatch, SHA-256 mismatch, missing cleanup permission, state-write failure, rehash failure, path validation failure, or unlink failure, the source remains retained. The outcome and a sanitized reason are recorded for audit; Push keys, prompts, response bodies, and raw paths beyond the item's safe identifier are not exposed in normal logs or UI.

## 2. Existing V1 Interoperability

Phase 6 consumes the existing POST /api/sync/push contract. It does not add a receiver endpoint, a browser-to-GenBox call, or a cleanup flag to the multipart request.

Before a receipt can be used for cleanup, the sender validates:

| Field / property | Required value |
|---|---|
| Transport | Direct request to configured destination; redirects rejected |
| ok | JSON boolean true |
| contract_version | Exact string v1 |
| source_id | Exact configured source ID used for the request |
| sha256 | Lowercase SHA-256 of the uploaded bytes |
| status | imported, already-imported, or duplicate-local |
| safe_to_delete_source | JSON boolean true for cleanup eligibility only |

safe_to_delete_source false, a missing value, or a string such as "true" is not a cleanup receipt. A valid transfer receipt with cleanup permission false is still a successful Push result and remains eligible for normal idempotent display, but it authorizes no deletion.

The v1 receiver's safe_to_delete_source=true means it committed the received content. It does not enable the sender policy, prove the current source still has those bytes, or supersede the development and production gates in this repository.

## 3. Sender-Side Records

The sender must persist a cleanup-authority record before attempting deletion. It may extend the existing Push state/outbox or use a dedicated private state file, but records must be atomically written, permission-restricted, and recoverable after restart.

The durable record is keyed by this transfer identity:

~~~
destination_scope + source_id + normalized_remote_path + source_sha256
~~~

destination_scope is a non-secret, one-way destination identity; it must change when the destination or Push key is rotated. The stored record includes only the minimum needed to decide and audit cleanup:

| Field | Purpose |
|---|---|
| record_version | Sender cleanup-state schema version |
| destination_scope, source_id | Bind authority to the destination and sender identity |
| remote_path, source_sha256 | Bind authority to one normalized source and content identity |
| receipt | Allowlisted fields: version, source ID, SHA-256, status, permission |
| receipt_validated_at | Time the sender completed validation |
| transfer_status | Confirmed transfer outcome, separate from cleanup outcome |
| cleanup_policy_snapshot | Observed policy; never substitutes for a current policy check |
| cleanup_status | not_requested, ineligible, eligible, deleted, retained, or delete_failed |
| decision_reason, decided_at | Sanitized explanation and audit time |
| size_bytes | Reclaimed-space accounting after successful deletion |

Do not persist Push keys, authorization headers, full request/response bodies, prompts, cookies, or image bytes in cleanup records. Existing batch and outbox projections may expose a non-sensitive cleanup status and aggregate counts, but not credentials or raw receipt payloads.

A previously recorded receipt may be reconsidered only when its transfer identity, current destination scope, current source ID, normalized path, and current source SHA-256 all still match. A path reused with different bytes is a new identity and requires a new Push and receipt.

## 4. Cleanup State Machine

~~~mermaid
stateDiagram-v2
    [*] --> retained: source saved
    retained --> pushing: Push requested
    pushing --> retained: Push or receipt validation fails
    pushing --> receipt_confirmed: validated v1 receipt persisted
    receipt_confirmed --> retained: policy off / development disabled / dry run
    receipt_confirmed --> rechecking: explicit cleanup run
    rechecking --> retained: path or SHA-256 differs
    rechecking --> deleting: all gates pass
    deleting --> deleted: unlink succeeds and audit is committed
    deleting --> retained: unlink fails; record delete_failed
~~~

The physical deletion is the last mutation. The implementation must recheck the policy, environment mode, normalized storage-rooted path, file type, file existence, and SHA-256 immediately before deletion. It must avoid a time-of-check/time-of-use substitution by using a storage-layer deletion helper that resolves the target beneath the image root and rejects symlinks. If that guarantee cannot be made, cleanup remains disabled.

An interrupted cleanup is never inferred as successful. After restart, the sender verifies on-disk state and records deleted only when absence is unambiguous for the exact authorized target, or retained/delete_failed for any ambiguity. It never deletes another candidate while recovering.

## 5. Policy And Invocation Contract

Cleanup is a distinct setting from GenBox Push enabled and from schedules. It is default-off. Enabling Push, clicking a Studio Push action, creating a Gallery batch, retrying a transfer, or enabling a schedule must not implicitly enable cleanup.

The cleanup invocation contract has two modes:

| Mode | Required behavior |
|---|---|
| Dry run | Makes no filesystem mutation. Enumerates eligible, ineligible, and retained items with sanitized reasons and potential reclaimable bytes. |
| Execute | Requires current explicit opt-in and all Section 1 gates. Deletes only currently eligible entries and returns per-item plus aggregate audit results. |

For Phase 6, development is hard-disabled by default. A destructive isolated test requires a separate, narrowly scoped test-only enablement confirmed in runtime configuration; it must not be inherited by production configuration or enabled by a browser request. Production remains disabled until a later, separately authorized release gate provides dry-run output, audit evidence, and clear reclaimed-space reporting.

Concurrency is serialized per transfer identity. A concurrent Push, batch, schedule worker, retry, cancellation, or cleanup attempt must not allow one actor to delete bytes while another has not finished hashing or sending them. The cleanup worker takes a process-shared per-item claim and releases it in all outcomes. It reuses the existing normalized-path and coordinated-transfer boundaries rather than introducing a second path interpretation.

## 6. Audit Projection

Each dry-run or execute operation produces a durable, sanitized audit event. The audit can explain every candidate without exposing a Push key, prompt, or raw receiver payload.

Minimum event fields:

~~~
audit_id, operation_id, mode, timestamp, source_id, item_identifier,
source_sha256, prior_cleanup_status, decision, decision_reason,
size_bytes, reclaimed_bytes, receipt_status
~~~

item_identifier may be the normalized relative path when it is already safe to show under the sender's existing administrative model, otherwise it is a stable opaque identifier. Audit queries return totals for candidates, eligible, deleted, retained, failed, potential bytes, and reclaimed bytes. A deletion is counted as reclaimed only after unlink succeeds and the deleted audit record is durably committed.

## 7. Required Test Matrix

All automated tests use synthetic source bytes, temporary storage, and fake receivers. No test uses a production instance, a real Push key, a real prompt, or a user image.

| ID | Layer | Scenario | Expected result |
|---|---|---|---|
| P6-01 | Unit | Default settings and Push-only settings | Cleanup is off; source is retained. |
| P6-02 | Unit | User enables cleanup but development gate is off | Execute refuses deletion; audit says development-disabled. |
| P6-03 | Unit | Dry run with a valid record | No unlink; item and potential bytes are reported. |
| P6-04 | Unit | Valid v1 receipt with all required fields | Record becomes eligible only after durable receipt write. |
| P6-05 | Unit | HTTP 2xx with ok false, wrong contract, wrong source ID, bad status, or bad SHA-256 | No eligibility and source retained. |
| P6-06 | Unit | Permission missing, false, null, or string "true" | No eligibility and source retained. |
| P6-07 | Unit | Valid receipt but source content changes before cleanup | Rehash mismatch; no unlink; audit says source-changed. |
| P6-08 | Unit | File missing before cleanup | No deletion attempt against another path; audit says source-missing. |
| P6-09 | Unit | Path traversal, absolute path, alias, symlink, or outside-root target | Rejected before hashing/unlinking. |
| P6-10 | Unit | Destination source ID or Push key rotates after receipt | Destination scope mismatch prevents cleanup. |
| P6-11 | Unit | Same path with a new SHA-256 | Old record cannot authorize deletion; new receipt required. |
| P6-12 | Unit | already-imported and duplicate-local validated receipts | Eligible only when all cleanup gates pass. |
| P6-13 | Unit | State-file or audit-file write fails before unlink | No unlink; source retained. |
| P6-14 | Unit | Unlink raises an error | Source remains or error is recorded; reclaimed_bytes is zero. |
| P6-15 | Unit | Crash/restart between receipt persistence and cleanup | Restart retains source until explicit later cleanup. |
| P6-16 | Unit | Crash/ambiguous state during deletion | Recovery never guesses success or deletes a different item. |
| P6-17 | Unit | Concurrent cleanup requests for one identity | Exactly one claimant may attempt unlink; one terminal decision. |
| P6-18 | Unit | Cleanup races schedule, batch, retry, or Studio Push | Delete waits/fails closed; no send reads deleted bytes. |
| P6-19 | Service | Push response redirects | Redirect rejected; no cleanup record or delete. |
| P6-20 | Service | Transport error, timeout, 4xx, 5xx, malformed JSON | Source retained; no eligible record. |
| P6-21 | API | Cleanup endpoints require sender administrator authorization | Unauthorized request cannot preview or execute cleanup. |
| P6-22 | API | Browser requests development override or arbitrary source path | Rejected; server-side policy and stored records decide targets. |
| P6-23 | API | Execute returns mixed valid, changed, and ineligible records | Only valid unchanged item deletes; all decisions are explainable. |
| P6-24 | UI/API | Policy is off by default and needs explicit confirmation | No implicit enablement through Push or schedule controls. |
| P6-25 | UI/API | Dry-run presentation and execute summary | Counts and byte totals agree with sanitized audit projection. |
| P6-26 | Regression | Existing single, batch, retry, schedule tests with cleanup disabled | Existing workflows retain every source and preserve outcomes. |
| P6-27 | Isolated VPS | Authorized dev-only valid cleanup | One synthetic unchanged receipt-confirmed source is removed; audit and bytes match. |
| P6-28 | Isolated VPS | Changed-source, false-permission, and receiver-failure controls | All controls remain; production is not selected or modified. |

## 8. Acceptance Evidence And Non-Claims

Phase 6 acceptance requires the local test matrix relevant to changed code, the isolated-development evidence in P6-27 and P6-28, sanitized audit review, and confirmation that the production source instance was not modified. A clean GitHub redeployment remains Phase 7 work, not implied by this specification or by local tests.

This document specifies sender cleanup only. It does not claim that GenBox has added signed receipts, that cleanup has been implemented, or that a receiver, sender, and production deployment have completed end-to-end cleanup.

## 9. Implementation Handoff

Start with the durable cleanup-authority record and dry-run evaluator, then add the storage-rooted deletion primitive, execute path, audit projection, API/UI, and isolated-test gate. Keep the existing v1 Push validation as the only source of receipt eligibility. Do not alter receiver code, mutate a VPS, or enable production cleanup as part of this phase's implementation work.

