# Phase 6 Verified Source Cleanup Platform Specification

**Status:** Proposed platform and release contract. This document does not
authorize deletion, VPS mutation, or production enablement.

**Scope:** The chatgpt2api sender's runtime, storage, deployment, and evidence
boundaries for Phase 6. The GenBox Push v1 receiver contract remains unchanged;
the normative receipt and deletion rules are in
[`PHASE6-PROTOCOL-SPEC.md`](PHASE6-PROTOCOL-SPEC.md).

## 1. Platform Invariant And Boundaries

The platform must make the safe operation the easy operation:

- Sources are retained unless every protocol gate, current policy gate, and
  storage identity check succeeds.
- Cleanup is a sender-side action. GenBox reports whether the committed
  receipt permits cleanup; it never receives a delete request and never runs a
  sender filesystem command.
- Development cleanup is hard-disabled unless a separately scoped test-only
  runtime override is present. A browser request, Push checkbox, schedule, or
  inherited environment variable cannot enable it.
- Production instances remain read-only during implementation and isolated
  verification. A Phase 6 test must not reuse production data, credentials,
  ports, Compose names, or Push identities.

The platform specification owns where state lives, how workers claim work, how
an image is deployed and rolled back, and what evidence is required. It does
not redefine receipt fields, source identity, or the cleanup state machine.

## 2. Environment Matrix

Every run declares one environment class. Values below are logical
requirements, not live runtime facts.

| Environment | Allowed purpose | Cleanup mode | Required isolation |
|---|---|---|---|
| Local sender checkout | Unit/service tests and static review | Disabled; fake receiver only | Temporary storage and synthetic bytes |
| Disposable local container | Build and smoke tests | Dry-run only by default | Loopback-only ports, generated keys, throwaway volume |
| Isolated VPS development clone | Authorized end-to-end evidence | One narrowly scoped execute test after approval | Separate directory, volume, Compose project, container/service name, host port, management key, Push source ID/key, schedule and cleanup state |
| Production source instance | Read-only discovery and non-mutation checks | Disabled | Never selected as a test target |
| Clean GitHub deployment | Reproducibility and release gate | Disabled until a later release decision | Fresh clone, fresh configuration, fresh data directory and credentials |

An environment identity record must include a non-secret run identifier,
environment class, image digest or local build identity, storage root, service
port, Compose project/container names where applicable, and evidence timestamp.
It must exclude credentials, private keys, cookies, prompts, raw media, and
unredacted host details.

## 3. Resource And State Isolation

The sender's cleanup records, transfer outbox, batch state, schedule cursor,
worker leases, and audit events must share the same isolated state root as the
development sender, but remain separate logical namespaces. A clone must not
inherit any of the following from its source instance:

- Push destinations, source IDs, Push keys, or receiver receipts.
- Batch items, schedule cursors, worker leases, cleanup decisions, or audit
  history that could authorize a different environment.
- Paths or bind mounts that resolve outside the clone's owned storage root.

State writes use a temporary file in the same directory, flush and filesystem
sync where supported, then an atomic rename. A write failure occurs before any
unlink attempt and produces a retained/delete-failed audit outcome. Recovery
must tolerate a missing or partially written record without guessing that a
deletion succeeded.

The cleanup identity is the protocol identity from the Phase 6 contract:

```text
destination_scope + source_id + normalized_remote_path + source_sha256
```

`destination_scope` must change when the configured destination or Push key is
rotated. A source path reused with new bytes is a new identity, not an update
to an old deletion authorization.

## 4. Storage And Deletion Primitive

The sender must expose one storage-owned deletion primitive. Callers pass a
validated item identity, never an arbitrary path. The primitive must:

1. Resolve the normalized relative path beneath the configured image root.
2. Reject absolute paths, traversal, alternate separators, symlink targets,
   hard-link ambiguity where detectable, and paths outside the root. If the
   storage platform cannot establish the required no-alias guarantee, cleanup
   remains disabled for that target.
3. Recheck regular-file type, existence, byte length, and SHA-256 immediately
   before unlinking.
4. Persist a durable `deleting` intent before the unlink, then hold the
   per-item transfer/cleanup claim through the final filesystem mutation and
   terminal audit commit.
5. Return an explicit result (`deleted`, `retained`, or `delete_failed`) with a
   sanitized reason and zero reclaimed bytes unless unlink and audit commit
   both succeed.

No recovery path may delete a substitute file because the original target is
missing or ambiguous. If the process stops between unlink and audit commit,
restart records only what can be proved for that exact identity; it never
chooses another candidate or infers success from a stale in-memory flag.

## 5. Worker, Lease, And Concurrency Model

Cleanup is serialized per transfer identity and coordinated with every sender
operation that reads or mutates the source:

- Single Push, Gallery batch, scheduled scan, retry, cancellation, and cleanup
  all use the same per-item claim boundary.
- The claim is process-shared, stale-claim recovery is bounded, and the claim
  is released in success and failure paths.
- A cleanup worker rechecks current opt-in, environment mode, receipt identity,
  source hash, path ownership, and file type after claiming the item.
- A concurrent Push wins by retaining the source when cleanup cannot obtain a
  claim. Cleanup never waits indefinitely or retries deletion blindly.
- A schedule lease prevents duplicate schedule workers; cleanup does not create
  a second scheduler or bypass the sender's existing batch/outbox ownership.

On restart, in-flight cleanup entries are reconciled only from the durable
intent and exact on-disk observation. They may become `deleted` only when the
authorized target is unambiguously absent and the pre-delete intent proves
which identity was being removed; otherwise they become retained or
delete-failed and await an explicit dry run or execute operation. Automatic
startup cleanup is prohibited.

## 6. Configuration And Feature Gates

The implementation should expose separate logical settings for:

- Push enabled.
- Cleanup policy enabled (default `false`).
- Dry-run versus execute invocation.
- Environment cleanup capability (default disabled; isolated test-only enable
  requires runtime configuration outside browser control).
- Audit retention and maximum operation size, with conservative bounded
  defaults.

Changing Push or schedule settings must not change cleanup policy. The server
must reject browser attempts to provide a development override, source path,
receipt, destination scope, or cleanup decision. The server derives all
eligible targets from durable sender records.

Configuration changes are versioned in the audit stream with the actor and
effective timestamp, but never include secret values. A destination or key
rotation invalidates prior cleanup authority by changing `destination_scope`.

## 7. Deployment, Upgrade, And Rollback

An isolated cleanup-capable build is deployed only by immutable image digest or
an equivalent reproducible local build identity. Before deployment:

1. Run the focused sender cleanup matrix and the existing Push, batch, retry,
   and schedule suites with cleanup disabled.
2. Run syntax/compile checks, diff/secret scans, and a disposable container
   smoke test.
3. Record the candidate digest, source commit, test commands/results, and
   isolated target identity without secrets.
4. Create a bounded update plan for the isolated target only. Production is not
   an eligible target for this phase.

The updater pulls the candidate before changing configuration, backs up the
prior image/configuration, recreates only the owned isolated service, and waits
for a deterministic health check. On pull, write, start, or health failure it
restores the prior configuration and image, recreates the prior service, and
leaves source media retained. Local registration changes only after health
succeeds.

An execute test is a separate approval gate after deployment health is proven.
The rollback target is limited to the isolated instance's owned directory,
volume, Compose project, and container. No direct SSH fallback or production
restart is part of Phase 6 evidence.

## 8. Observability And Audit Projection

Every dry-run and execute operation writes sanitized, durable audit events. The
projection must support per-item explanations and aggregate totals for:

- candidates, eligible, deleted, retained, failed;
- potential bytes and reclaimed bytes; and
- receipt statuses (`imported`, `already-imported`, `duplicate-local`, or
  ineligible/unknown).

Minimum event fields are defined by the protocol specification. Platform
projections may add environment run ID, image/build identity, worker ID, and
operation duration, but must not expose Push keys, authorization headers,
prompts, response bodies, cookies, private keys, or arbitrary raw paths.

Logs and metrics are operational aids, not deletion authority. A 2xx response,
an in-memory success flag, a missing terminal audit event, or a process exit
code cannot be used to infer that a source was deleted. Reclaimed bytes are
counted only after unlink succeeds and the terminal audit commit is durable;
an audit-write failure leaves a recoverable `deleting` intent rather than
silently claiming success.

## 9. Platform Acceptance Evidence

Before Phase 6 can be marked complete, the handoff must include:

| Evidence | Required result |
|---|---|
| Local focused matrix | Receipt, hash, policy, path, state-write, concurrency, and restart cases pass with synthetic bytes |
| Regression suite | Existing Push, batch, retry, and schedule behavior passes with cleanup disabled |
| Disposable build | Immutable/reproducible build starts and serves health checks; no production data mounted |
| Isolated valid cleanup | One explicitly approved synthetic unchanged source is deleted; matching audit and reclaimed bytes are recorded |
| Isolated controls | Changed source, false/missing permission, receiver failure, path escape, and concurrent attempt all retain sources |
| Production boundary | Timestamped checks show the production instance was not selected or modified |
| Sanitization | Tracked files, generated artifacts, logs, and Git history contain no real secret or personal media |

Evidence is labeled `VERIFIED`, `UNVERIFIED`, or `USER-CONFIRMED` with an
absolute date and command/result. Local or mock evidence never substitutes for
isolated-VPS evidence, and isolated evidence never authorizes production
cleanup.

## 10. Non-Claims And Implementation Handoff

This specification does not claim that cleanup is implemented, that a receipt
is cryptographically signed, or that any VPS has been changed. It does not add
a receiver endpoint or alter Push v1.

Implementation order:

1. Add the durable cleanup record and atomic state/audit writer.
2. Add the storage-rooted deletion primitive and per-item claim boundary.
3. Add dry-run evaluation and execute orchestration behind the server-side
   development gate.
4. Add sanitized API/UI projections and aggregate reclaimed-space reporting.
5. Run the local matrix, then obtain explicit approval for isolated evidence.

Any failure in path ownership, receipt identity, hash recheck, state durability,
or environment classification is a retention decision and blocks destructive
execution until reviewed.
