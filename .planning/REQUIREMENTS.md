# Requirements: GenBox External Image Sync

**Defined:** 2026-07-11
**Core Value:** The local library reflects what was generated remotely without duplicates and without manual downloading.

## v1 Requirements

### Configuration

- [ ] **SYNC-01**: User can add/edit/remove one or more remote `chatgpt2api`-compatible deployments (name, base URL, admin bearer token) stored securely via `ConfigManager`.
- [ ] **SYNC-09**: The adapter is generic — works against any compatible deployment, not just one host; probes `GET /version` + `GET /auth/status` before use.

### Remote Listing & Dedup

- [ ] **SYNC-02**: App lists remote images via the remote `/api/images` admin endpoint with pagination and date filters.
- [ ] **SYNC-03**: App detects already-local images by computing **content SHA-256** of remote bytes (not filename/URL/ETag); filename/remote-path is only a key, not identity.
- [ ] **SYNC-07**: Sync state persists in a durable manifest so re-runs skip already-imported images.

### Sync Window & Selection

- [ ] **SYNC-04**: A sync window shows only new/changed remote images as selectable cards (thumbnail + metadata).
- [ ] **SYNC-05**: User can filter candidates by: select-all, date range (today / this month / custom range), aspect ratio (portrait/landscape/square), and file size (e.g. <1MB / 1–5MB / >5MB).

### Import

- [ ] **SYNC-06**: User syncs selected images; downloads run in a background task with progress and land in the local gallery as media cards; interrupted runs are resumable/retryable.

### Security

- [ ] **SYNC-08**: New `/api/sync/*` routes are admin-protected; remote credentials are never logged or committed; remote fetch is server-side with host validation (no browser egress, no SSRF).

## v2 Requirements

### Scheduling & Extras

- **SCHD-01**: Optional automatic periodic sync.
- **SCHD-02**: Two-way sync with conflict/tombstone policy.
- **SCHD-03**: Video/audio sync from remote.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Two-way sync (push local→remote) | Conflict/tombstone semantics out of scope for v1; remote is source of truth |
| Video/audio import | Remote gallery is image-only for v1 |
| Auto-scheduled continuous sync | Manual trigger only in v1 |
| Editing remote images | Read-only pull |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SYNC-01 | Phase 1 | Pending |
| SYNC-09 | Phase 1 | Pending |
| SYNC-02 | Phase 2 | Pending |
| SYNC-03 | Phase 2 | Pending |
| SYNC-07 | Phase 2 | Pending |
| SYNC-08 | Phase 3 | Pending |
| SYNC-04 | Phase 4 | Pending |
| SYNC-05 | Phase 4 | Pending |
| SYNC-06 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-11*
*Last updated: 2026-07-11 after initial definition*
