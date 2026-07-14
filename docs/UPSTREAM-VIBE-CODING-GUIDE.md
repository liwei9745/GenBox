# chatgpt2api GenBox Push Extension: AI Development Guide

**Status:** Draft specification. GenBox receiver code exists, but the complete
chatgpt2api sender, batch scheduler, cleanup flow, and clean redeployment have
not yet passed end-to-end acceptance.

## Purpose

This guide gives the chatgpt2api maintainer, a contributor, or an AI coding
agent enough bounded context to implement the sender side without requiring
access to private GenBox deployment details.

## Read First

1. The target chatgpt2api repository's contribution and agent instructions.
2. Its generation, Gallery, configuration, authentication, persistence, and
   scheduling modules.
3. This document.
4. GenBox `docs/INTEGRATION.md`.
5. GenBox `docs/chatgpt2api-push-integration.md`.

Do not assume file names or framework details until they are verified in the
current upstream revision.

## User Story

As a user generating images on a storage-constrained VPS, I want to send new or
existing images to my GenBox media library, verify that they arrived without
duplicates, and optionally remove only confirmed source copies so I can reduce
VPS disk usage safely.

## Required Capabilities

### Foundation

- GenBox destination settings with masked Push secret.
- Connection test that does not expose the secret.
- One shared server-side Push service.
- Local SHA-256 calculation and receipt validation.
- Durable per-image transfer state.
- No source deletion.

### Generation Integration

- A per-generation "Push to GenBox" option.
- Generation success remains distinct from transfer success.
- Failed Push is retryable from image management.

### Gallery Batch Integration

- Image selection and date-range selection.
- Durable batch progress and cancellation.
- Retry failed items only.
- Clear already-imported result.

### Scheduling

- Default weekly incremental Push.
- Custom weekday/time or supported cron expression.
- Optional start and end dates.
- Persistent cursor with overlap, per-item state, and worker lease.

### Optional Cleanup

- Separate opt-in setting, disabled by default.
- Disabled in development environments.
- Delete only after matching authenticated receipt and unchanged source hash.
- Audit record and reclaimed-space summary.

## Push API Summary

```http
POST <GENBOX_PUSH_URL>/api/sync/push
X-GenBox-Source: <stable-source-id>
X-GenBox-Key: <secret>
Content-Type: multipart/form-data
```

Fields:

```text
image=<binary>
remote_path=<stable-relative-path>
created_at=<optional-source-time>
prompt=<optional-prompt>
model=<optional-model>
```

Validate the returned SHA-256 against locally calculated bytes. Do not treat an
HTTP status alone as confirmation. See GenBox `docs/INTEGRATION.md` for complete
receipt and cleanup rules.

## Suggested Sender Data Model

Adapt names and persistence technology to upstream conventions:

```text
GenBoxDestination
  enabled
  base_url
  source_id
  push_key_secret_ref
  timeout_seconds
  cleanup_enabled = false

TransferItem
  source_path
  source_sha256
  status
  attempts
  receipt_sha256
  genbox_local_file
  last_error_code
  last_attempt_at
  completed_at

PushSchedule
  enabled
  schedule_expression
  start_date
  end_date
  scan_cursor
  lease_owner
  lease_expires_at
```

Store secrets using the upstream project's protected configuration mechanism.
Do not return secret values from ordinary settings APIs.

## State Model

Recommended item states:

```text
pending -> running -> succeeded
                   -> already_imported
                   -> retryable_failure -> pending
                   -> permanent_failure
pending/running -> cancelled
```

Persist state transitions before source cleanup. A process restart must not
convert an unconfirmed item into success.

## Security And Privacy Constraints

- Do not log Push keys, administrator keys, cookies, account tokens, or full
  authorization headers.
- Validate destination URL policy according to upstream deployment needs.
- Keep the GenBox Push key separate from chatgpt2api's management key.
- Do not include real deployment addresses, images, prompts, or credentials in
  tests, fixtures, screenshots, commits, or PR descriptions.
- Do not enable cleanup from the per-generation Push checkbox.
- Do not develop or test by modifying an existing production container.

## Recommended PR Breakdown

### PR 1: Push Foundation

- Destination configuration.
- Shared Push client/service.
- Receipt persistence and idempotent retry.
- Connection test.
- Unit and integration tests.

No Gallery UI, scheduler, or deletion in this PR.

### PR 2: Generation And Gallery UI

- Per-generation option.
- Manual image and date-range batch selection.
- Progress, errors, cancellation, and retry.
- UI and API tests.

### PR 3: Scheduler And Confirmed Cleanup

- Weekly/custom scheduling.
- Cursor, overlap, lease, and restart recovery.
- Explicit cleanup policy, dry run, audit, and space summary.
- Failure and recovery tests.

## Acceptance Test Matrix

| Scenario | Expected Result |
|---|---|
| Valid single image | One GenBox media item and matching receipt |
| Same request repeated | No duplicate media; already-imported success |
| Same path, changed bytes | New content handled by hash policy |
| Invalid Push key | No import; source retained; no secret in logs |
| Network timeout | Retryable failure; source retained |
| Invalid image | Permanent failure; source retained |
| Batch interrupted | Durable state resumes without duplicate success |
| Late file in schedule range | Later overlapping scan discovers it |
| Two scheduler workers | Lease prevents duplicate active processing |
| Cleanup disabled | Source always retained |
| Receipt hash mismatch | Source retained and error recorded |
| Confirmed cleanup enabled | Only unchanged confirmed source is deleted |

## AI Task Prompts

Use one prompt per PR after replacing bracketed repository facts with verified
upstream paths. Do not ask one agent to implement all phases at once.

### Foundation Prompt

```text
Read the repository instructions and inspect the existing configuration,
generation storage, HTTP client, and test patterns. Implement only the GenBox
Push foundation described in this guide: destination settings with masked
secret, one shared server-side Push service, SHA-256 receipt validation,
durable transfer receipts, connection test, and focused tests. Do not add UI,
scheduling, or source deletion. Follow existing abstractions and report exact
test commands and remaining assumptions.
```

### UI And Batch Prompt

```text
Using the existing GenBox Push service, add a per-generation Push option and a
Gallery batch workflow with image/date selection, durable progress,
handlers. Do not add scheduling or deletion. Verify generation success and Push
success remain separate states, then run focused and full tests.
```

### Scheduler And Cleanup Prompt

```text
Add weekly and custom incremental scheduling using a persistent cursor with
overlap, per-image state, and a worker lease. Then add separately enabled source
cleanup with dry run and audit. Deletion is allowed only after an authenticated
receipt, matching SHA-256, safe_to_delete_source=true, and a final unchanged
source hash check. Development environments must never auto-delete. Add restart,
concurrency, retry, and cleanup safety tests.
```

## Contribution Gate

Before opening an upstream PR:

1. Test against an isolated development clone, never the existing production
   instance.
2. Remove environment-specific and sensitive data.
3. Push to the contributor's repository.
4. Deploy from a fresh clone of that repository.
5. Repeat relevant acceptance tests.
6. Confirm the production instance remained unchanged.

Until this gate is complete, present this document as a draft proposal rather
than claiming production-ready integration.
