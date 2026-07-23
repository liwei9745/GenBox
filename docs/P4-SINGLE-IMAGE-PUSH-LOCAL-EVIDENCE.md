# P4 Single-Image Push Local Evidence

**Date:** 2026-07-24
**Scope:** GenBox receiver worktree only
**Evidence class:** `LOCAL`

This matrix distinguishes verified receiver behavior from the sender and
isolated-VPS work that remains outside this worktree. It does not claim a
chatgpt2api sender implementation, a private-network connection, or a real
end-to-end transfer.

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
| Per-generation Push action and transfer status UI | Sender worktree | UNVERIFIED | Requires explicit sender-worktree authorization. |
| Sender source retention on authentication, network, invalid-image, and receipt-hash failure | Sender worktree | UNVERIFIED | Receiver cannot delete or preserve sender files. |
| Isolated clone, private-network transfer, retry, and production non-mutation | Isolated VPS session | UNVERIFIED | Requires separately authorized L2/L3 evidence. |

## Verification Snapshot

The following local-only checks passed on this worktree:

```text
python -m pytest -q tests/test_sync.py tests/test_sync_push_routes.py
43 passed

python -m pytest -q
501 passed

python -m py_compile main.py sync/ingest.py sync/manifest.py
node --check static/js/extensions.js
node --check static/js/i18n.js
node --check static/js/app.js
node --check static/js/app-all.js
git diff --check
```

The local development lab served
`http://127.0.0.1:8892/#/extensions` to Playwright with HTTP 200, no page
errors, and no horizontal overflow at `390x844`. No credentials, pairing
material, Push request, SSH action, VPS connection, remote container action, or
production action was submitted. The lab was stopped after the check.

## Next Gate

Keep L2 paused. The next feature is the sender-side per-generation action in
the separate dirty `chatgpt2api-dev` worktree. It requires explicit
authorization, preservation of its existing changes, and a local/mock receiver
only. Isolated-VPS discovery remains a separate authorized step after the
target owner/scope and canonical SSH host-key pair are supplied.
