# Deep Integration Human Authorization Package

**Prepared:** 2026-08-09
**Purpose:** hand off only the work that cannot be self-authorized by local code, CI, or synthetic evidence.

## Review Verdict

| Area | Verdict | Basis |
| --- | --- | --- |
| Receiver/sender contract, idempotency, retention, vault projection | PASS (local) | current focused and full test suites pass; see `DEEP-INTEGRATION-EVIDENCE-MATRIX.md` |
| Cleanup default-off and browser authority rejection | PASS (local fail-closed behavior) | sender cleanup suites and protocol contract |
| G-Store readiness material | PASS (scope) | design-only package; no catalog or adapter implementation was added |
| Docker runtime health smoke | UNVERIFIED | image build passes; local smoke did not obtain an HTTP 200 before the disposable container exited |
| Hosted CI/macOS/Docker integration cases | UNVERIFIED | recorded CI evidence is partial; this run did not create a new hosted result |
| Isolated VPS cleanup execution/recovery | BLOCKED PENDING AUTHORIZATION | requires exact isolated host identity and a bounded synthetic cleanup authorization |
| Production source access or mutation | BLOCKED | no authorization exists; `33018` is explicitly out of scope |
| Clean GitHub deployment and upstream/release work | UNVERIFIED | requires sanitized published commit and a separately provisioned clean environment |

## Required Human Decisions

1. Identify and authorize one isolated development target by canonical host, port, host-key algorithm, and SHA-256 fingerprint.
2. Approve a one-time synthetic-only cleanup marker with source path, content hash, rollback/retention expectation, and post-restart recovery check.
3. Confirm that no production target, including `33018`, is in scope.
4. Authorize a clean deployment from sanitized GitHub sources after independent review of the publishable commit.
5. Perform UI acceptance for the stored-credential opt-in warning and source-retention/cleanup language.

## Prohibited Until Reauthorized

No VPS/SSH access, no remote deployment, no fixed-port operation against `33010` or `33018`, no real credential or user-media use, no cleanup/unlink/execute marker, no production modification, and no release/tag/RC action.

## Evidence To Capture After Approval

Use redacted records only: target identity confirmation, pre/post health, immutable artifact identity, sender and receiver request/receipt hashes, source-retention or authorized cleanup result, restart/recovery result, production non-mutation check, and a fresh secret/data scan. Record the exact command/result in `docs/STATUS.md` only after the activity is authorized and completed.
