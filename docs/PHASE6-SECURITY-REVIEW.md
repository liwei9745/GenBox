# Phase 6 Verified Source Cleanup Security Review

**Review status:** `BLOCK` for destructive execution until the blocking gates
below have implementation and test evidence. This is a design review only; no
cleanup-capable sender, VPS, or production instance was changed.

**Reviewed contracts:**

- [`PHASE6-PROTOCOL-SPEC.md`](PHASE6-PROTOCOL-SPEC.md)
- [`PHASE6-PLATFORM-SPEC.md`](PHASE6-PLATFORM-SPEC.md)
- [`ADVERSARIAL-REVIEW-MATRIX.md`](ADVERSARIAL-REVIEW-MATRIX.md)
- [`DEVELOPMENT-LIFECYCLE.md`](DEVELOPMENT-LIFECYCLE.md)
- ADR-002 and ADR-003 in [`DECISIONS.md`](DECISIONS.md)

## Review Scope

The security invariant is: an unconfirmed, changed, missing, ambiguous, or
failed source survives. GenBox's authenticated Push receipt is evidence that
the receiver committed content; the chatgpt2api sender remains the only actor
that can apply its separately enabled local cleanup policy. A browser request,
HTTP 2xx response, in-memory flag, or log line is not deletion authority.

The review covers receipt authority, replay and identity binding, path and
filesystem safety, worker races, crash recovery, authorization, environment
isolation, secret/privacy exposure, and evidence needed before an isolated
execute test.

## Findings

### SEC-01 - BLOCK: Receipt transport trust is conditional, not cryptographic

Push v1 does not define a signed receipt. The sender therefore relies on the
authenticated request, the configured destination, and the transport path when
it accepts `safe_to_delete_source=true`. A compromised route, wrong endpoint,
or unsafe destination configuration could fabricate a syntactically valid
receipt even when the source was not committed.

**Required control:** the sender must use a previously verified destination
identity, reject redirects, and require either HTTPS with normal certificate
verification or an explicitly verified private-network route whose endpoint
identity was established before Push configuration. Cleanup execution must not
accept a browser-supplied destination, receipt, source ID, or key. A failed or
ambiguous destination check is retention, never deletion.

**Adversarial cases:** wrong host returning a valid-looking JSON receipt;
redirect to a second host; plaintext/public destination substituted after a
valid Push; destination or Push-key rotation followed by replay of an old
receipt.

### SEC-02 - BLOCK: Final hash check alone does not close the TOCTOU race

Rehashing a path immediately before `unlink` is necessary but insufficient if
another worker or process can replace the file between the hash and unlink.
The same path could then name different bytes at deletion time.

**Required control:** use the platform storage primitive and one process-shared
per-item claim for Push, batch, retry, schedule, cancellation, and cleanup.
The primitive must hold the claim through unlink and audit commit, reject
symlinks and traversal, and compare the opened file's identity (inode/file ID,
size, and hash) with the path being removed. Platform-specific no-follow
semantics must be tested on the supported sender filesystem.

**Adversarial cases:** replace the file after hashing; rename a valid file into
the authorized path; run Push and cleanup concurrently; run two cleanup
workers in separate processes.

### SEC-03 - BLOCK: Crash state needs an explicit in-flight/unknown outcome

The proposed terminal statuses do not make the interval between a successful
unlink and a failed audit write unambiguous. Treating a missing file as
`deleted` after restart can overstate reclaimed bytes; treating every missing
file as retained can cause unsafe retry logic elsewhere.

**Required control:** persist a deletion intent (for example `deleting`) and
durably flush it before unlink. After unlink, commit the terminal audit record
with the exact identity. On restart, resolve only that exact target and record
`deleted` when both absence and the pre-unlink identity are provable;
otherwise record `delete_unknown`/`retained` and require an explicit later
operation. Startup must never retry cleanup automatically or select a
replacement candidate.

**Adversarial cases:** crash before intent write, after intent write, after
unlink but before audit commit, during atomic rename, and with a truncated state
file.

### SEC-04 - BLOCK: The destructive environment gate must be fail-closed

The platform draft correctly separates local, disposable, isolated-VPS, and
production modes. The security gate must still prove that an inherited
environment variable, stale clone state, browser body, or restart cannot turn
cleanup on in production.

**Required control:** cleanup capability defaults to disabled; unknown or missing
environment classification rejects execute; the isolated test override is
server-side, narrowly scoped, and not writable through an HTTP request. Clone
creation must rotate destination, source ID, Push key, schedule, receipt,
lease, and cleanup state. No startup cleanup is permitted.

**Adversarial cases:** production config with a test override; stale state copied
from a clone; browser request containing `execute=true` or an environment
override; restart while execute is pending; wrong Compose project or storage
root selected.

### SEC-05 - BLOCK: Cleanup API must be capability- and CSRF-bound

The sender's cleanup API is a destructive administrative surface. Selecting an
arbitrary path, receipt, or record ID from the browser would recreate the
authority confusion that the protocol is intended to prevent.

**Required control:** require the sender's existing administrator authorization
and CSRF protection for policy changes, dry runs, and execute operations. The
server derives eligible records from its durable state and current policy; the
request may provide only an operation mode and bounded selection of opaque
record IDs. It must reject arbitrary paths, hashes, receipts, destinations,
source IDs, and development overrides. Re-authentication or an explicit
destructive confirmation is recommended for execute.

**Adversarial cases:** unauthenticated request; cross-site POST; execute with a
path outside the image root; forged receipt in the request body; record ID from
another destination scope; replayed execute operation ID.

### SEC-06 - BLOCK: Hard-link and alternate-filesystem identity need evidence

Symlink rejection and lexical path validation do not cover every filesystem
alias. A hard link, bind mount, junction, or platform-specific reparse point
can make a path's ownership ambiguous even when it is beneath the configured
root.

**Required control:** reject or explicitly account for hard links and
platform-specific aliases where detectable; ensure the image root itself is a
trusted, owned directory and does not cross a mount boundary unexpectedly.
Document the supported filesystem semantics and test them on the isolated
sender image. Any ambiguity retains the source.

**Adversarial cases:** hard-linked source and outside-root file; junction or
reparse-point target; image-root symlink; mount replacement after record
creation; alternate separator and Unicode normalization aliases.

### SEC-07 - PASS WITH CONDITIONS: Receipt validation and rotation binding

The protocol's allowlist is sound: exact `v1`, JSON boolean `ok=true`, exact
source ID, lower-case SHA-256 matching the uploaded bytes, an allowlisted
success status, and strict boolean `safe_to_delete_source=true`. Binding the
record to `destination_scope + source_id + normalized_remote_path +
source_sha256` correctly prevents a rotated destination/key or changed path
from reusing an old authorization.

**Conditions for approval:** ignore all response fields not needed for the
decision; bound response size and content type before parsing; reject redirects
and malformed/duplicate JSON fields; persist the validated record atomically
before eligibility; and test `already-imported` and `duplicate-local` as
successful transfer states that still require every cleanup gate.

### SEC-08 - PASS WITH CONDITIONS: Source retention and partial failure

The failure rule is appropriately conservative: timeout, non-success status,
malformed response, hash mismatch, policy-off, state-write failure, path
failure, and unlink failure retain the source. A mixed execute operation may
delete only independently eligible items and must report every retained or
failed item.

**Conditions for approval:** no broad exception handler may convert an unknown
state into success; reclaimed bytes are zero until unlink and audit commit both
succeed; retries are bounded and never blindly repeat an ambiguous deletion;
and successful transfer remains distinct from successful cleanup.

### SEC-09 - P1: Audit records need integrity, privacy, and bounded growth

Sanitized audit projections are required, but the contracts do not yet state
whether records are append-only, permission-restricted, or bounded. Mutable or
unbounded audit files can hide a deletion decision, leak source paths, or fill
the sender volume.

**Required control:** write audit events atomically with restrictive file
permissions, use a bounded retention/rotation policy, and expose only opaque
identifiers unless a normalized relative path is explicitly safe. Never include
Push keys, authorization headers, prompts, cookies, response bodies, raw host
details, or user media. Record operation IDs so replayed API calls are
detectable.

### SEC-10 - P2: Receipt client resource limits should be explicit

An authenticated receiver can still return an oversized or slow response. The
sender should cap response bytes, enforce connect/read deadlines, and avoid
logging response bodies. This is primarily availability protection, but it
prevents malformed responses from reaching cleanup decision code.

## Adversarial Gate Matrix

| Gate | Challenge | Required result | Status |
|---|---|---|---|
| A1 | False receipt from wrong endpoint | No eligibility; source retained | `BLOCK` until evidence |
| A2 | Redirect or transport downgrade | Request rejected; no record | `BLOCK` until evidence |
| A3 | Replay after destination/key rotation | Scope mismatch; no deletion | `PASS` in design, test required |
| A4 | Changed bytes at same path | Final identity/hash mismatch; retained | `BLOCK` until race test |
| A5 | Symlink, hard link, junction, traversal | Rejected before unlink | `BLOCK` until filesystem tests |
| A6 | Two processes claim one item | One claimant; no duplicate unlink | `BLOCK` until process test |
| A7 | Crash around unlink/audit commit | No guessed success or substitute deletion | `BLOCK` until recovery test |
| A8 | Browser-forged path/receipt/override | Authorization and schema rejection | `BLOCK` until API test |
| A9 | Production or stale-clone state selected | Execute unavailable; production unchanged | `BLOCK` until isolation evidence |
| A10 | Mixed execute outcomes | Only eligible unchanged items delete; totals reconcile | `PASS` in design, test required |
| A11 | Secrets or prompts in audit/logs | Sanitized output only | `PASS` in design, scan required |
| A12 | Oversized/slow malformed receipt | Bounded failure; source retained | `P1` test required |

## Explicit Decision Gates

### Design Gate: `BLOCK`

The protocol and platform drafts establish the right authority boundary and
default-retain behavior, but SEC-01 through SEC-06 require explicit
implementation contracts and adversarial tests before destructive code is
accepted.

### Merge Gate: `BLOCK` unless all of the following are demonstrated locally

- Storage-owned deletion primitive with process-shared claim and no-follow
  identity checks.
- Durable deletion intent, atomic state/audit writes, and restart recovery that
  never guesses success.
- Server-side environment capability gate that cannot be enabled by browser
  input or inherited production state.
- Authenticated, CSRF-protected cleanup API deriving targets from durable
  records only.
- Strict receipt validation, destination-scope rotation invalidation, bounded
  response handling, and no secret-bearing logs.
- Focused tests for A1-A12 plus existing Push, batch, retry, and schedule
  regressions with cleanup disabled.

### Isolated Execute Gate: `BLOCK` until merge gate is `PASS`

After a fixed reviewed commit is deployed to a disposable isolated clone, run
one synthetic valid cleanup and the changed-source, false-permission,
receiver-failure, path-alias, concurrency, and crash controls. Capture
timestamped, secret-free evidence and prove the production source was not
selected or modified. Any failed or ambiguous control blocks the execute test
and reverts to source retention.

## Review Conclusion

The Phase 6 contracts are directionally safe and preserve the project's
accepted ADR-002/ADR-003 rules. They are not yet an approval to delete source
media. The highest-risk gaps are transport trust for an unsigned v1 receipt,
filesystem TOCTOU/alias handling, crash consistency around unlink and audit,
and proving that the destructive capability cannot escape the isolated target.
Resolve those gates, rerun this adversarial matrix on the fixed commit, and
record the result as `PASS`, `FAIL`, or `NOT RUN` with `VERIFIED`, `UNVERIFIED`,
or `USER-CONFIRMED` evidence labels.
