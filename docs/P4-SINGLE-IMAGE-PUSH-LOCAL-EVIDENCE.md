# P4 Single-Image Push Local Evidence

**Date:** 2026-07-24
**Scope:** GenBox receiver worktree plus explicitly separated local sender evidence
**Evidence class:** `LOCAL`

This matrix distinguishes verified receiver behavior, the separately committed
sender contract, and isolated-VPS work that remains unverified. Local mock
evidence is not a private-network connection or a real isolated end-to-end
transfer.

## Receiver Contract

- Endpoint: `POST /api/sync/push`
- Auth: source-specific `X-GenBox-Source` plus `X-GenBox-Key`; this is separate
  from the GenBox administrator key.
- Request: image bytes, stable source-relative `remote_path`, optional
  `source_sha256`, `created_at`, `prompt`, and `model`.
- Probe: `GET /api/sync/push/status` returns the v1 contract version and the
  image-byte limit used by the running receiver process.
- Receipt: `ok`, `contract_version`, status, source ID, remote path, receiver
  SHA-256, local file, dimensions, and `safe_to_delete_source`.
- Successful status values: `imported`, `already-imported`, and
  `duplicate-local`.

## Local Evidence Matrix

| Requirement | Local evidence | Result | Boundary |
| --- | --- | --- | --- |
| Source authentication is separate from admin authentication | `test_production_push_auth_is_separate_from_admin_auth` | VERIFIED | Does not prove a sender secret store. |
| Destination probe reports the active contract and byte limit | `test_push_status_route_authentication`, `test_push_status_limit_matches_runtime_rejection` | VERIFIED | Local process only. |
| Import receipt contains receiver SHA-256 and stable v1 fields | `test_push_route_imports_then_is_idempotent_and_deduplicates_by_content` | VERIFIED | Sender receipt persistence is separate work. |
| Sender-provided hash is checked before commit when present | `test_matching_source_sha256_is_accepted`, `test_mismatched_or_malformed_source_sha256_does_not_commit` | VERIFIED | Existing v1 senders may omit the optional field. |
| Prompt, model, source path, source identity, and creation time are retained | `test_push_preserves_png_metadata_and_exposes_gallery_source_fields` | VERIFIED | Available metadata only. |
| Same source/path/content retry is idempotent | `test_push_route_imports_then_is_idempotent_and_deduplicates_by_content` | VERIFIED | Local receiver request only. |
| Changed content at the same source path creates a new receipt | `test_push_changed_content_at_same_source_path_creates_a_new_receipt` | VERIFIED | Local receiver request only. |
| Concurrent identical requests commit one local file | `test_concurrent_identical_pushes_create_one_gallery_file` | VERIFIED | In-process test concurrency only. |
| Restart/index recovery does not trust forged or changed local state | `test_push_content_deduplication_survives_local_index_rebuild`, `test_push_does_not_trust_uncommitted_source_hash_metadata`, `test_push_does_not_ack_modified_committed_file`, `test_legacy_manifest_entry_still_requires_matching_source_bytes` | VERIFIED | Local gallery and manifest only. |
| Invalid image, oversize image, malformed hash, and wrong identity avoid a receiver commit | Push-route rejection tests | VERIFIED | Does not prove sender source retention or retry policy. |
| Per-generation Push action and transfer status UI | Sender commits `78135e1`, `0320b62`; sender focused suite `12 passed` | VERIFIED | LOCAL sender evidence only; no live receiver request. |
| Sender source retention on authentication, network, invalid-image, and receipt-hash failure | Sender focused mock tests; failed state records path, SHA-256, attempts, and bounded error | VERIFIED | LOCAL mock receiver only; receiver cannot prove sender filesystem behavior. |
| Isolated clone, private-network transfer, retry, and production non-mutation | Isolated VPS session | UNVERIFIED | Requires separately authorized L2/L3 evidence. |

## Verification Snapshot

The following local-only checks passed on this worktree:

```text
python -m pytest -q tests/test_sync.py tests/test_sync_push_routes.py
43 passed

python -m pytest -q
501 passed

Sender worktree local checks:

```text
CHATGPT2API_AUTH_KEY=<test-only process value> python -m pytest -q
12 passed
npm run build
passed
```

The sender mock suite covers v1 probe compatibility, `source_sha256`, receipt
hash mismatch, authentication/network failure, source retention, persisted
failure state, and idempotent retry. It does not connect to GenBox over a live
network.

Sender Studio browser smoke used the local Vite page at `127.0.0.1:5173` with
Playwright-routed mock API responses only. A synthetic completed image exposed
the per-generation button; the first click was disabled while pending and then
showed the success receipt state, while a second mock failure showed retry and
source-retained recovery. The captured requests contained only the expected
relative image path. The page had zero errors and `scrollWidth=430` at a 430px
viewport. This is LOCAL UI/mock evidence, not a live sender-to-GenBox transfer.

python -m py_compile main.py sync/ingest.py sync/manifest.py
node --check static/js/extensions.js
node --check static/js/i18n.js
node --check static/js/app.js
node --check static/js/app-all.js
git diff --check
```

The local development lab served
`http://127.0.0.1:8892/#/extensions` to Playwright with HTTP 200, title
`GenBox`, no page errors, and no horizontal overflow at `390x844`. No
credentials, pairing material, Push request, SSH action, VPS connection,
remote container action, or production action was submitted.

## Next Gate

Keep L2 paused. The sender-side per-generation action, durable failure state,
and local mock browser smoke are implemented in commits `78135e1` and `0320b62`.
The next local gate is a final secret/data review of those commits; isolated-VPS
discovery remains a separate authorized step after the target owner/scope and
canonical SSH host-key pair are supplied.
