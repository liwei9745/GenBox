# Roadmap: GenBox External Image Sync

**Milestone:** v1.0 — Remote Gallery Sync
**Created:** 2026-07-11
**Requirements covered:** 9/9 ✓

## Phases

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Sync Configuration & Adapter | Add secure remote-deployment config + generic chatgpt2api client with version probe | SYNC-01, SYNC-09 | User can save ≥1 remote deployment; client probes `/version`+`/auth/status`; creds stored via ConfigManager, not in source |
| 2 | Dedup & Candidate Diff | Compute content SHA-256, build persistent manifest, diff remote vs local | SYNC-02, SYNC-03, SYNC-07 | Remote list paginated; already-local images skipped; manifest persists across runs; re-run is idempotent |
| 3 | Sync API & Background Import | Admin-gated `/api/sync/*` endpoints + background download task with progress, host validation, resumability | SYNC-06, SYNC-08 | Selected images download to gallery as cards; progress reported; endpoints reject unauthenticated calls; host validated |
| 4 | Sync Window UI & Filters | Frontend modal showing selectable new-image cards with filters (select-all, date, ratio, size) | SYNC-04, SYNC-05 | User opens sync window, filters candidates, selects, triggers import; gallery refreshes after |
| 5 | Tests, Verification & Docs | pytest suite (hashing, manifest, filters, auth) + run + update docs/README | (all) | Tests pass; manual sync verified end-to-end; README documents setup + key rotation |

## Phase Details

### Phase 1: Sync Configuration & Adapter
Goal: Let the app securely know about and talk to a remote deployment.
Requirements: SYNC-01, SYNC-09
Success criteria:
1. A "Remote Sync" settings section stores deployments (name, baseUrl, token) via `ConfigManager`.
2. `SyncDeployment` model + `SyncConfig` persisted under `storage/` (not `.env` secrets in git).
3. `chatgpt2api_client.py` probes `/version` and `/auth/status`, raises on non-admin.
4. Generic enough to target any compatible host.

### Phase 2: Dedup & Candidate Diff
Goal: Know which remote images are new.
Requirements: SYNC-02, SYNC-03, SYNC-07
Success criteria:
1. `GET /api/images` listed with pagination + date filter, normalized to a common record.
2. Downloaded bytes hashed with SHA-256; manifest keyed by `deploymentId:path`.
3. Local existing images detected by hash without re-downloading unnecessarily.
4. Manifest load/save idempotent; re-run skips imported images.

### Phase 3: Sync API & Background Import
Goal: Import selected images safely in the background.
Requirements: SYNC-06, SYNC-08
Success criteria:
1. `POST /api/sync/preview` returns candidates; `POST /api/sync/import` starts background task.
2. All `/api/sync/*` require `X-Admin-Key` (prod).
3. Downloads server-side via `httpx`, host-validated, semaphore-limited, retryable.
4. Progress + result reported; files land in `storage/gallery/` and appear as media cards.

### Phase 4: Sync Window UI & Filters
Goal: User picks what to import through a filterable window.
Requirements: SYNC-04, SYNC-05
Success criteria:
1. "Sync from remote" button opens a modal showing only new images as selectable cards.
2. Filters: select-all, today / this month / custom date range (Beijing time), aspect ratio, size bucket.
3. Selected import triggers Phase 3 endpoint; gallery refreshes on completion.

### Phase 5: Tests, Verification & Docs
Goal: Prove it works and document it.
Requirements: (all)
Success criteria:
1. `pytest` covers hashing, manifest, filter matching, endpoint auth.
2. End-to-end manual sync verified against the user's deployment (with rotated key).
3. README/setup notes cover remote config, timezone, key rotation, `:latest` pinning.

## Traceability

All 9 v1 requirements mapped to Phases 1–4; Phase 5 verifies across all.

---
*Roadmap created: 2026-07-11*
