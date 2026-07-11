# GenBox — External Image Sync

## What This Is

GenBox is a single-process FastAPI desktop/server app (UI bundled as a static SPA) that
generates and manages AI images and videos across multiple providers. This milestone adds
a **remote gallery sync** feature: pull images from an external `chatgpt2api`-compatible
deployment (e.g. the user's VPS at `http://43.131.226.9:3000/v1`) into the local media
library, showing only new images as a selectable, filterable sync window so the user picks
what to import.

## Core Value

The local library should reflect what was generated remotely **without duplicates and
without manual downloading** — the user sees a curated, filterable diff and chooses what
lands in their media cards.

## Business Context

<!-- Internal tool / personal deployment — no monetization. Deleted section per template. -->

## Requirements

### Validated

- ✓ Single-process FastAPI app with admin-key auth (`APP_MODE=prod`) — existing
- ✓ Filesystem-backed media library under `storage/gallery/*.png` + JSONL history — existing
- ✓ Provider config persisted in `storage/providers.json` via `ConfigManager` — existing
- ✓ `httpx` already used for all remote calls — existing
- ✓ Static SPA frontend (`static/index.html` + `static/js/app-all.js`) with gallery tab — existing

### Active

- [ ] **SYNC-01**: User can configure one or more remote `chatgpt2api`-compatible deployments (base URL + admin bearer token) stored securely.
- [ ] **SYNC-02**: App can list remote images via the remote `/api/images` admin endpoint with pagination.
- [ ] **SYNC-03**: App detects which remote images already exist locally (content-based dedup, not filename/URL).
- [ ] **SYNC-04**: App opens a sync window showing only new/changed remote images as selectable cards.
- [ ] **SYNC-05**: User can filter candidates by full-select, date range (day/month), aspect ratio, and file size.
- [ ] **SYNC-06**: User can sync selected images; downloads run in background with progress and land in the local gallery as media cards.
- [ ] **SYNC-07**: Sync state persists in a durable manifest so re-runs skip already-imported images.
- [ ] **SYNC-08**: New sync endpoints are admin-protected; remote credentials are never logged or committed.
- [ ] **SYNC-09**: A generic adapter supports any `chatgpt2api`-compatible deployment, not just one host.

### Out of Scope

- Two-way sync / push from local to remote — conflict/tombstone semantics out of scope for v1; remote is source of truth.
- Video/audio sync — remote gallery is image-only for v1.
- Auto-scheduled continuous sync — manual trigger only in v1 (background task per run).
- Editing remote images — read-only pull.

## Context

- Upstream project: `yukkcat/chatgpt2api` (MIT). Remote API (pinned `2252046f`):
  `GET /api/images` (admin Bearer) lists paginated records with `path`, `created_at`
  (Beijing time, no offset), `size`, optional `width`/`height`, `url`, `thumbnail_url`.
  Originals/thumbnails are served unauthenticated with permissive CORS. `created_at` is
  the only reliable time; filename embeds an MD5 but it is NOT exposed and imported files
  may not follow the format, so **content SHA-256 computed locally is the dedup key**.
- Local app: `main.py` monolith, `storage/gallery/` PNGs, no DB, no tests today.
- The user's remote key was shared in chat and MUST be rotated before any commit; it is
  never written to source or `.env`.

## Constraints

- **Tech stack**: Keep FastAPI + `httpx` + filesystem. No new heavy dependencies; tests use `pytest` (new dev dependency).
- **Security**: New `/api/sync/*` routes admin-gated; remote fetch server-side only (no browser egress, no remote host leak); validate base URL host; rotate leaked key.
- **Compatibility**: Must work against `:latest` but degrade gracefully if remote schema drifts; pin a tested version in docs.
- **Performance**: Downloads in a background task with a concurrency semaphore; rely on a persistent manifest instead of re-hashing the whole gallery each run.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Content SHA-256 (not filename/URL/ETag) as dedup key | Remote exposes no stable hash; MD5/ETag unreliable | — Pending |
| One-way remote→local sync for v1 | Avoids two-way conflict/tombstone complexity | — Pending |
| Persistent manifest `storage/sync_manifest.json` | No DB; needs idempotent re-runs | — Pending |
| Generic adapter (baseUrl + token) | Supports other deployments, not just one VPS | — Pending |
| Server-side fetch of remote files | Prevent SSRF/browser egress + host leak | — Pending |

---

*Last updated: 2026-07-11 after milestone initialization*
