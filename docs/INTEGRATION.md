# GenBox And chatgpt2api Integration Contract

## Scope

This document defines the end-to-end responsibilities shared by GenBox and
chatgpt2api. The current GenBox receiver details are in
`docs/chatgpt2api-push-integration.md`. Deployment and network behavior are in
`docs/extensions-deployment-contract.md`.

## Capability Matrix

| Capability | GenBox | chatgpt2api | Overall State |
|---|---|---|---|
| Pull remote image list and import | Implemented | Existing compatible API required | Implemented in GenBox; live verification pending |
| Receive one pushed image | Implemented | Sender missing in this repository | Partial |
| Per-generation Push selection | Receiver ready | Planned | Planned |
| Manual batch Push | Receiver reusable | Planned | Planned |
| Scheduled incremental Push | Receiver reusable | Planned | Planned |
| Receipt-gated source cleanup | Receipt field implemented | Planned | Planned |
| Guided Compose deployment | Implemented in code | Deployable target | Live clone verification pending |
| Private-network setup | Adapter code exists | Endpoint participant | Live verification pending |

## Destination Configuration

chatgpt2api needs a GenBox destination with:

- Enabled state.
- GenBox Push base URL.
- Stable source ID identifying the sending deployment.
- Push key stored as a secret.
- Optional connection timeout and retry policy.
- Cleanup policy, defaulting to retain sources.
- Schedule settings stored separately from destination identity.

Secrets must be masked on read and excluded from normal logs and exports.

## Push Request V1

Endpoint:

```text
POST /api/sync/push
```

Authentication headers:

```text
X-GenBox-Source: <stable-source-id>
X-GenBox-Key: <source-specific-secret>
```

Multipart fields:

- `image`: image bytes.
- `remote_path`: stable source-relative path, required.
- `created_at`: source creation time, optional.
- `prompt`: generation prompt, optional.
- `model`: model identity, optional.

GenBox validates credentials, media type, image structure, size, and content
hash before importing. The endpoint must remain safe for idempotent retry.

## Receipt Requirements

A successful receipt includes enough information for the sender to verify:

- Request succeeded.
- GenBox accepted or had already imported the same content.
- GenBox-computed SHA-256 matches the sender's bytes.
- The local file was committed.
- `safe_to_delete_source` confirms receiver-side commit eligibility. The current
  v1 receiver returns `true` after a successful or idempotent committed import;
  it does not by itself activate sender-side deletion.

The sender persists the source path, content hash, result, receipt, attempts,
last error, and timestamps. HTTP success alone does not authorize deletion.

## Single-Image Flow

1. The user selects the per-generation Push option.
2. chatgpt2api generates and saves the source normally.
3. The shared Push service calculates SHA-256 and submits the image.
4. The service validates and stores the receipt.
5. The generation UI reports local generation and Push results independently.
6. Failure leaves the source intact and offers retry.

The Push option is per generation. A separate saved preference may be considered
later, but it must not silently enable source cleanup.

## Manual Batch Flow

1. The user filters and selects source images in chatgpt2api Gallery.
2. The server creates a durable batch with one item per image.
3. Workers call the same shared Push service used by single-image Push.
4. The UI reports pending, running, succeeded, already imported, failed, and
   cancelled counts.
5. Retry targets failed items without resending confirmed items unnecessarily.

## Scheduled Incremental Flow

- Default schedule: once per week.
- Custom schedule: weekday/time or cron-like expression, plus optional start and
  end dates.
- The scanner uses a durable cursor with overlap and per-image state so late
  files and clock changes do not cause omission.
- A lease prevents duplicate workers from running the same schedule.
- Restarting the service resumes durable work rather than resetting it.

## Metadata And Tags

GenBox should retain, when available:

- Source service: `chatgpt2api`.
- Source instance ID.
- Transfer method: Push or Pull.
- Stable remote path.
- Source creation time.
- Prompt and model.
- SHA-256 and import time.

At minimum, imported images must be identifiable in the media library as remote
chatgpt2api media. Tag naming and filtering behavior require UI acceptance tests.

## Retry And Error Handling

- Retry transport errors, timeouts, and retryable server errors with bounded
  exponential backoff and jitter.
- Do not retry authentication or invalid-image errors indefinitely.
- Preserve source bytes for every unconfirmed outcome.
- A changed source at the same path creates a new content identity and requires
  a new receipt.
- Logs include source ID and safe item identifiers, never Push keys or account
  credentials.

## Source Cleanup

Cleanup is a separate, explicit user option. It runs after transfer state is
durably committed. Before deletion, the sender rechecks source content identity,
receipt authentication, matching SHA-256, and `safe_to_delete_source=true`.

Development environments do not automatically delete sources. Production
cleanup requires dry-run output, audit records, and clear reclaimed-space
reporting.

## Compatibility And Versioning

- The Push contract begins at v1 and should evolve additively where possible.
- Unknown response fields are ignored; required receipt fields are validated.
- GenBox and chatgpt2api releases document the contract version they test.
- Upstream PRs keep protocol, UI, scheduler, and cleanup changes reviewable in
  separate units.

## End-To-End Acceptance

The integration is complete only when a clean GitHub deployment proves:

1. A new generated image Pushes into GenBox once with expected metadata.
2. The same request is idempotent.
3. A selected batch resumes after interruption.
4. A scheduled scan finds an eligible late image.
5. Failure retains the source.
6. Opt-in cleanup deletes only a receipt-confirmed unchanged source.
7. The original production instance was not modified during development.

## Image Management Push Destination

The chatgpt2api image-management page will expose a zero-code "Push to GenBox"
setting. It uses the verified private-network destination by default. An advanced
editor may change host and port, but the new destination must pass an authenticated
application-level probe before it replaces the saved value. The Push key remains a
separate secret and is never embedded in the URL.
