# Codebase Concerns

**Analysis Date:** 2026-07-11

Concerns relevant to adding an external-image synchronization feature (pulling gallery
images from a remote chatgpt2api deployment into the local media library). Findings are
derived from `ARCHITECTURE.md`, `INTEGRATIONS.md`, `STACK.md`, and the upstream
`yukkcat/chatgpt2api` API contract (pinned commit `2252046f`).

## Technical Debt

- **No automated tests.** No pytest/unittest setup, no test CI job. `screenshots/` only
  contains manual Playwright capture scripts. Any sync logic needs its own test harness
  (hashing, manifest migration, idempotency, interrupted downloads).
- **No database.** Runtime state is JSON/JSONL + in-memory dicts + filesystem
  (`storage/`). Sync metadata must live in a JSON manifest under `storage/`, not a DB.
- **Stale duplicate config.** `providers/config.py` is an unreferenced duplicate of
  `config.py` with a different storage root — do not extend it.
- **Two code paths for frontend.** `static/js/app-all.js` is the active bundle;
  `static/js/gallery.js` mirrors its logic but is inactive. Edits must go to `app-all.js`
  (and ideally the modular source kept in sync later). `index.html` only loads
  `app-all.js`.

## Bugs / Fragile Areas

- **Non-atomic writes.** Image saves and `history.jsonl` appends are not atomic or
  locked. Generation, sync, rename, and delete can race. Sync must use a lock or
  sequential writes per file.
- **Substring delete/rename lookup.** Gallery delete/rename uses substring matching on
  IDs; overlapping IDs can hit the wrong file. Sync-created files need unambiguous,
  namespaced filenames.
- **No path containment check on gallery file endpoints.** User-supplied filenames are
  joined without explicit resolved-path containment. Sync must validate every downloaded
  path stays under `storage/gallery/`.
- **Gallery list capped before global sort.** `/api/gallery?limit=80` returns only 80
  records and `total` is the post-limit count. The sync candidate view must paginate or
  read full set so totals and dedup are accurate.
- **Mutable filename-stem IDs.** Local IDs are filename stems; provider identity is
  inferred from the first `_`-delimited segment. Rename/producers with underscores break
  provenance. Sync should keep its own stable manifest keyed by remote deployment+path.

## Security

- **Admin-key auth on local API.** `main.py` enforces `X-Admin-Key` in `APP_MODE=prod`.
  New sync endpoints must be admin-protected; the remote API also requires `Authorization:
  Bearer <admin key>`.
- **Secret handling.** Never log or commit remote API keys. Store remote credentials in
  `storage/providers.json` / `.env` via the existing `ConfigManager` pattern, not in
  source. The user's current remote key must be rotated before any public commit.
- **Unauthenticated remote file URLs.** chatgpt2api serves originals/thumbnails without
  auth and with permissive CORS. The local app must fetch server-side (not expose the
  remote URL to the browser) to avoid leaking the remote host and to control egress.
- **SSRF surface.** A sync feature fetches arbitrary remote URLs. Validate the base URL
  scheme/host against the configured deployment and block redirects to internal hosts.

## Performance

- **Synchronous file downloads.** No streaming/background job framework exists beyond
  `asyncio.create_task` for generation. Sync should run as a background task with progress
  reporting, not block the request thread.
- **Full re-scan on every gallery load.** `_scan_gallery()` rescans `*.png` each call.
  Sync should rely on a persistent manifest for diffing, not re-hash the whole gallery
  each run.
- **Large media.** Remote galleries can be large; download should be resumable/retryable
  and respect concurrency limits (semaphore), similar to `image_gen_semaphore`.

## Integration Risks (upstream chatgpt2api)

- **No stable content hash in API.** Filenames embed an MD5 of image bytes, but imported
  files need not follow that format and MD5 is not exposed separately. Dedup must compute
  SHA-256 of downloaded bytes locally; filename/URL/ETag are NOT reliable identity.
- **Timezone.** `created_at` is serialized in `Asia/Shanghai` without offset. Date
  filtering in the sync UI must treat remote times as Beijing time.
- **`:latest` drift.** The deployment pulls `ghcr.io/yukkcat/chatgpt2api:latest`; API
  behavior can change. Pin/support a known version and degrade gracefully on schema
  mismatch.
- **No optimistic concurrency / tombstones.** Remote delete uses exact `path`; local
  deletes leave no durable record. A one-way (remote→local) sync for v1 avoids two-way
  conflict complexity.
- **Licensing.** Upstream is MIT; a generic adapter can support other compatible
  deployments, but generated images / third-party container assets are out of scope of
  that license.

## Recommended Watch-items for Implementation

1. Add a `storage/sync_manifest.json` (or per-deployment manifest) recording
   `deploymentId:remotePath → localPath, sha256, size, remoteCreatedAt, syncedAt`.
2. Reuse `httpx` (already a dependency) for all remote calls; add a download semaphore.
3. Gate all new `/api/sync/*` routes behind existing admin auth.
4. Add a small `tests/` pytest suite for hashing, manifest load/save, filter matching,
   and endpoint auth — since none exists today.
5. Keep remote credentials out of `.env` git history; rotate the user's current key.
