# Project Research Summary

**Date:** 2026-07-11
**Scope:** Adding remote gallery sync (pull images from a `chatgpt2api`-compatible deployment into the local GenBox media library).

## Key Findings

### Local Architecture (GenBox)
- Single-process **FastAPI monolith** (`main.py`) with a bundled static SPA
  (`static/index.html` + `static/js/app-all.js`). No router modules, no DB.
- Media lives as standalone PNGs in `storage/gallery/`; `_save_image()` writes
  `provider_timestamp_prompt_uuid.png` and embeds PNG text metadata
  (`providers/__init__.py:108`). `_scan_gallery()` rescans `*.png` and infers provider
  from the filename prefix (`main.py:325`).
- Gallery API `GET /api/gallery?limit=80` is capped before global sort; `total` is the
  post-limit count (`main.py:1275`).
- Provider config via `ConfigManager` in `config.py` (reads `storage/providers.json`,
  syncs `.env`). `ProviderConfig` supports `extra` dict for arbitrary settings
  (`config.py:50`).
- Auth: `X-Admin-Key` enforced in `APP_MODE=prod`. `httpx` is the established remote-IO
  client. No tests, no DB, non-atomic writes, substring-based delete lookups
  (`CONCERNS.md`).

### Remote API (chatgpt2api, pinned `2252046f`)
- `GET /api/images` (admin **Bearer**) → paginated `{items, groups, total, ...}`.
  Item fields: `path` (operational identity), `created_at` (**Beijing time, no offset**),
  `size`, optional `width`/`height`, `url`, `thumbnail_url`, `type`.
- `GET /images/{path}` serves originals **unauthenticated**, permissive CORS.
  `GET /image-thumbnails/{path}` builds 320×320 thumbnails.
- `POST /api/images/delete` (admin) by exact `path` or date range.
- Filename format `YYYY/MM/DD/<epoch>_<md5(bytes)>.png`, but **MD5 not exposed** and
  imported files may differ → **must compute SHA-256 locally** for dedup.
- `created_at` must be treated as `Asia/Shanghai`.
- MIT licensed; generic adapter (baseUrl + token + version probe) is viable.
- `:latest` drift risk; pin/tested version recommended.

## Implications for Roadmap

1. **Dedup** = local SHA-256 of downloaded bytes; keep `deploymentId:path` as the remote
   key. Do NOT trust filename/URL/ETag.
2. **Manifest** = `storage/sync_manifest.json` mapping
   `deploymentId:path → {localPath, sha256, size, remoteCreatedAt, syncedAt}`.
3. **Fetch server-side** in a background task behind `httpx`; validate host; no browser
   egress.
4. **Admin-gate** all new `/api/sync/*` routes; store remote creds via `ConfigManager`
   (`extra` or a dedicated sync config), never in source.
5. **Filtering UI** needs date range (Beijing time), aspect ratio, size, and
   select-all — computed from candidate metadata before download.
6. **Tests**: add `pytest` (dev-only) covering hashing, manifest load/save, filter
   matching, and endpoint auth, since none exist today.

## Sources
- Local: `.planning/codebase/{ARCHITECTURE,INTEGRATIONS,STACK,CONCERNS}.md`
- Remote: `github.com/yukkcat/chatgpt2api` @ `2252046f` — `api/system.py`,
  `services/image_service.py`, `services/image_storage_service.py`,
  `services/config.py`, `docker-compose.warp.yml`.
