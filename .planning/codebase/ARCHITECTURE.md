# Architecture

**Analysis Date:** 2026-07-11

## System Overview

```text
+-------------------------------------------------------------+
|                    Browser SPA Shell                         |
| `static/index.html` loads `static/js/app-all.js` and CSS      |
+------------------+------------------+-----------------------+
| Dashboard        | Image Generate   | Video / Gallery       |
| `static/js/app.js` | `static/js/generate.js` | `static/js/video.js` |
| `static/js/gallery.js` | `static/js/providers.js` | `static/js/modals.js` |
+--------+---------+--------+---------+-----------+-----------+
         |                  |                     |
         v                  v                     v
+-------------------------------------------------------------+
|                      FastAPI Monolith                        |
| `main.py` owns routing, auth, task state, media IO, dashboard |
+------------------+------------------+-----------------------+
| Provider Config  | Image Providers  | Video/Update Helpers  |
| `config.py`      | `providers/__init__.py` | `updater.py`     |
| `providers/key_pool.py`                                      |
+--------+---------+--------+---------+-----------+-----------+
         |                  |                     |
         v                  v                     v
+-------------------------------------------------------------+
| Runtime Storage and External AI APIs                         |
| `storage/providers.json`, `storage/history.jsonl`,           |
| `storage/gallery/`, `storage/videos/`, upstream model APIs    |
+-------------------------------------------------------------+
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | HTTP API, SPA serving, middleware, background image/video task orchestration, gallery/history/dashboard endpoints | `main.py` |
| Configuration manager | Provider schema, proxy schema, video model specs, `.env` synchronization, admin key helpers | `config.py` |
| Image provider dispatcher | Protocol detection, OpenAI/Gemini/Qwen/Agnes image calls, LLM prompt optimization, upstream model discovery | `providers/__init__.py` |
| Key pool manager | Per-provider API key round-robin, cooldown, status reporting | `providers/key_pool.py` |
| Update service | GitHub release checks, mirror testing, source/exe/docker update application | `updater.py` |
| SPA document | Single-page app markup, page sections, modals, dock, script bundle include | `static/index.html` |
| Browser bundle | Runtime UI state, API polling, provider management, image/video/gallery/dashboard interactions | `static/js/app-all.js` |
| Frontend source modules | Modular source equivalents for app, provider, generation, gallery, modal, navigation, theme, video behavior | `static/js/*.js` except `static/js/app-all.js` |
| Styling system | App shell, page layouts, design tokens, utilities, animations, dock and setup styles | `static/css/*.css` |
| Runtime persistence | Mutable provider config, histories, logs, gallery images, generated videos, thumbnails | `storage/` |

## Pattern Overview

**Overall:** Single-process FastAPI monolith with a static browser SPA and filesystem-backed runtime state.

**Key Characteristics:**
- Keep HTTP routes, task registries, background task creation, media file serving, and dashboard aggregation in `main.py`.
- Keep provider configuration and persistent provider schema in `config.py`; access it through the global `cfg_mgr` singleton.
- Route all image provider calls through `providers.generate_for_provider()` in `providers/__init__.py` so protocol detection, proxy selection, key rotation, retries, and error translation stay centralized.
- Keep browser state in the global `window` namespace or global variables in `static/js/app-all.js`; `static/index.html` binds actions through inline `onclick` handlers.
- Persist runtime data in `storage/` rather than a database.

## Layers

**Browser UI:**
- Purpose: Render the interactive single-page experience for dashboard, image generation, video generation, provider management, gallery, history, setup, and modals.
- Location: `static/index.html`, `static/js/app-all.js`, `static/css/`
- Contains: Inline app shell markup, global JS handlers, localStorage state, fetch polling, modal controls, provider cards, progress bars.
- Depends on: FastAPI JSON/file endpoints under `/api/*`, static assets under `/static/*`, browser localStorage.
- Used by: End users through `GET /` in `main.py`.

**API and Orchestration:**
- Purpose: Serve the SPA, expose REST endpoints, validate request models, create background tasks, aggregate status, enforce security middleware.
- Location: `main.py`
- Contains: Pydantic request/response models, FastAPI route functions, middleware, in-memory task dictionaries, file serving, ffmpeg/ffprobe helpers, startup flow.
- Depends on: `config.py`, `providers/__init__.py`, `providers/key_pool.py`, `updater.py`, `storage/`, external APIs through `httpx`.
- Used by: `static/js/app-all.js` and deployment entrypoints.

**Configuration and Secrets Boundary:**
- Purpose: Load and save provider/proxy/admin configuration, expose provider lists by type, synchronize selected settings to `.env`.
- Location: `config.py`
- Contains: `ProviderConfig`, `EndpointConfig`, `ProxyConfig`, `VideoModelSpec`, `ProvidersConfig`, `ConfigManager`, admin key helpers.
- Depends on: `storage/providers.json`, `.env`, `python-dotenv`, `pydantic`.
- Used by: `main.py`, `providers/__init__.py`.

**Provider Gateway:**
- Purpose: Normalize image and LLM upstream integrations behind provider config.
- Location: `providers/__init__.py`, `providers/key_pool.py`
- Contains: `ImageResult`, `_detect_protocol()`, `generate_for_provider()`, `_dispatch_generate()`, protocol-specific generation helpers, `enhance_prompt_with_llm_detailed()`, `fetch_models_from_upstream()`, `KeyPoolManager`.
- Depends on: `config.py`, `httpx`, `Pillow`, external model APIs.
- Used by: Image generation, LLM optimization, provider testing/model discovery routes in `main.py`.

**Runtime Storage:**
- Purpose: Store mutable app state without a database.
- Location: `storage/`
- Contains: `storage/providers.json`, `storage/history.jsonl`, `storage/video_history.jsonl`, `storage/logs.jsonl`, `storage/gallery/`, `storage/videos/`, `storage/video_thumbs/`.
- Depends on: Local filesystem permissions.
- Used by: `config.py`, `main.py`, `providers/__init__.py`.

**Distribution and Operations:**
- Purpose: Package and run the app as source, executable, or Docker container.
- Location: `build.py`, `Dockerfile`, `docker-compose.yml`, `start.bat`, `start.ps1`, `stop.bat`, `restart.bat`, `.github/workflows/`
- Contains: PyInstaller spec generation, container image definition, startup scripts, CI workflows.
- Depends on: Python, PyInstaller, Docker, ffmpeg for video metadata/thumbnails.
- Used by: maintainers and deployment flows.

## Data Flow

### Image Generation Request Path

1. Browser gathers prompt, selected image providers, quantities, mode, dimensions, and per-provider settings in `static/js/app-all.js` and posts to `/api/generate` (`main.py:739`).
2. `generate()` applies rate limiting, optional LLM prompt enhancement through `enhance_prompt_with_llm()`, creates a `gen_id`, stores task state in `image_tasks`, and starts `_process_image_gen()` with `asyncio.create_task()` (`main.py:740`, `main.py:843`, `main.py:860`).
3. `_process_image_gen()` runs provider subtasks under `image_gen_semaphore`, calling `providers.generate_for_provider()` for each provider/quantity (`main.py:870`, `providers/__init__.py:187`).
4. `generate_for_provider()` selects endpoint/key mode, chooses protocol via `_detect_protocol()`, dispatches to protocol-specific upstream calls, writes images through `_save_image()`, and returns `ImageResult` (`providers/__init__.py:138`, `providers/__init__.py:187`, `providers/__init__.py:273`, `providers/__init__.py:108`).
5. The browser polls `/api/generate/status/{gen_id}` and renders provider progress/results from `image_tasks` (`main.py:1028`, `static/js/generate.js:186`).
6. Completed records are persisted to `storage/history.jsonl`; images are stored under `storage/gallery/` and served by `/api/gallery/image/{filename}` (`main.py:292`, `main.py:1275`, `main.py:1301`).

### Video Generation Request Path

1. Browser video UI loads video providers from `/api/providers` and posts generation parameters to `/api/video/generate` (`static/js/video.js:125`, `main.py:1889`).
2. `video_generate()` selects a `ProviderConfig`, adapts frame/resolution/FPS parameters using video specs from `providers.get_video_model_spec()`, detects provider type, and builds provider-specific payloads (`main.py:1895`, `main.py:1917`, `main.py:1989`).
3. The route calls upstream video APIs with `httpx`, creates a task entry in `video_tasks`, and stores provider/task metadata (`main.py:2019`, `main.py:2083`, `main.py:2102`, `main.py:2116`).
4. Browser polls `/api/video/status/{task_id}`; when a video file exists, the API returns `video_url_local` and serves media through `/api/video/file/{filename}` (`main.py:2338`, `main.py:2352`).
5. Video history and thumbnails use `storage/video_history.jsonl`, `storage/videos/`, and `storage/video_thumbs/` (`main.py:1637`, `main.py:1643`, `main.py:1603`).

### Provider Configuration Flow

1. Browser opens provider management and calls `/api/providers` (`static/js/providers.js:11`, `main.py:429`).
2. API returns masked key/endpoint data and key pool status from `providers.key_pool.key_pool_manager` (`main.py:432`, `main.py:443`).
3. Create/update/delete/reorder requests modify `cfg_mgr.config.providers` and call `cfg_mgr.save()` (`main.py:480`, `main.py:504`, `main.py:519`).
4. `ConfigManager.save()` writes `storage/providers.json` and synchronizes selected environment values to `.env` (`config.py:368`, `config.py:380`).

### Authentication and Setup Flow

1. In production mode, `admin_auth_middleware()` allows static files and setup endpoints but requires `X-Admin-Key` for protected `/api/*` routes (`main.py:3072`).
2. Browser stores the admin key in localStorage and attaches it through `_authFetch()` (`static/js/app.js:113`).
3. First-run setup uses `/api/setup/status`, `/api/setup/first-run`, and `/api/setup/confirm` (`main.py:3093`, `main.py:3107`, `main.py:3114`).
4. Admin key creation and verification live in `config.py` (`config.py:578`, `config.py:593`, `config.py:602`).

**State Management:**
- Server process state is module-level dictionaries in `main.py`: `generation_history`, `image_tasks`, `continuous_sessions`, `video_tasks`, and rate-limit stores.
- Persistent state is append-only JSONL and files under `storage/`, plus provider JSON in `storage/providers.json`.
- Frontend state is global JS variables in `static/js/app-all.js` and localStorage keys such as `igs_admin_key`, `genbox_provider_settings`, and provider ordering.

## Key Abstractions

**ProviderConfig:**
- Purpose: Single schema for image, LLM, and video providers.
- Examples: `config.py:67`, `main.py:136`, `storage/providers.json`
- Pattern: Pydantic model with `type`, credentials, endpoint list, model list, capabilities, proxy flags, and `extra` for provider-specific settings.

**ConfigManager:**
- Purpose: Lazy-load, save, reload, filter, and environment-sync provider configuration.
- Examples: `config.py:312`, `config.py:432`, `config.py:436`, `config.py:440`
- Pattern: Module-level singleton `cfg_mgr`; use `cfg_mgr.config` for reads and `cfg_mgr.save(cfg)` for mutations.

**ImageResult:**
- Purpose: Uniform provider result contract for success/failure, image bytes/URL/local path, model, error, and generation ID.
- Examples: `providers/__init__.py:96`, `providers/__init__.py:187`, `main.py:928`
- Pattern: Dataclass returned by all provider generation branches.

**KeyPoolManager:**
- Purpose: Manage per-provider API key rotation and cooldown across requests.
- Examples: `providers/key_pool.py:56`, `providers/key_pool.py:140`, `main.py:2722`
- Pattern: Module-level singleton `key_pool_manager`, with an `asyncio.Lock` inside each `KeyPool` for round-robin selection.

**VideoModelSpec:**
- Purpose: Describe video model constraints for resolution, duration, FPS, frame rules, prompts, seeds, and image input count.
- Examples: `config.py:116`, `config.py:133`, `providers/__init__.py:54`, `main.py:2370`
- Pattern: Declarative model-spec registry consumed by API validation/adaptation and frontend UI shaping.

## Entry Points

**Application server:**
- Location: `main.py`
- Triggers: `python main.py`, Docker `CMD ["python", "main.py"]`, packaged executable.
- Responsibilities: First-run setup, optional browser launch, `uvicorn.run(app, host="0.0.0.0", port=8891)` (`main.py:3129`, `main.py:3301`).

**Browser SPA:**
- Location: `static/index.html`
- Triggers: `GET /` from `root()` (`main.py:409`).
- Responsibilities: Render app shell and load `/static/js/app-all.js?v=17` (`static/index.html:807`).

**Static assets:**
- Location: `static/`
- Triggers: `app.mount("/static", StaticFiles(...))` (`main.py:3123`).
- Responsibilities: Serve CSS and JS bundle/source files.

**Provider gateway:**
- Location: `providers/__init__.py`
- Triggers: `main.py` imports `generate_for_provider`, `enhance_prompt_with_llm_detailed`, and `fetch_models_from_upstream`.
- Responsibilities: Upstream model calls, model list discovery, error translation, media save.

**Build/package:**
- Location: `build.py`
- Triggers: `python build.py`.
- Responsibilities: Generate and run PyInstaller build with bundled `static/`, `providers/`, `.env.example`, and scripts (`build.py:20`).

**Container:**
- Location: `Dockerfile`
- Triggers: Docker build/run or compose.
- Responsibilities: Python 3.11 runtime, ffmpeg installation, non-root `genbox` user, port `8891`, healthcheck (`Dockerfile:1`, `Dockerfile:4`, `Dockerfile:23`, `Dockerfile:25`).

## Architectural Constraints

- **Threading:** The server uses the single asyncio event loop for FastAPI and upstream calls. It starts background image work with `asyncio.create_task()` (`main.py:843`) and uses a daemon thread only to open the browser on startup (`main.py:3293`). Video thumbnail generation can run in a daemon thread (`main.py:1623`).
- **Global state:** `main.py` owns mutable globals for `generation_history`, `generation_counter`, `continuous_sessions`, `image_tasks`, `image_gen_semaphore`, `video_tasks`, and rate limiting (`main.py:232`, `main.py:251`, `main.py:261`). `config.py` owns `cfg_mgr` (`config.py:453`), and `providers/key_pool.py` owns `key_pool_manager` (`providers/key_pool.py:163`).
- **Persistence:** Do not assume database transactions. Writes go to `storage/providers.json`, `.env`, JSONL history/log files, and gallery/video files.
- **Static bundle:** `static/index.html` loads `static/js/app-all.js`; module files under `static/js/` are source-like references and are not loaded by the page unless `index.html` changes.
- **Packaging paths:** Use `BASE_PATH`/`BASE_DIR` helpers in `main.py` and `config.py` for PyInstaller compatibility (`main.py:20`, `config.py:18`).
- **Circular imports:** `main.py` imports from `providers`, and `providers/__init__.py` imports from `config.py`. Keep provider code independent of `main.py` to avoid route-level cycles.
- **External tools:** Video metadata and thumbnails depend on ffprobe/ffmpeg availability (`main.py:306`, `main.py:1603`, `Dockerfile:4`).

## Anti-Patterns

### Bypassing the Provider Gateway

**What happens:** New image provider calls are added directly in `main.py` route handlers.
**Why it's wrong:** It skips `_detect_protocol()`, `_get_proxy_url()`, key-pool rotation, shared retry behavior, and `ImageResult` normalization in `providers/__init__.py`.
**Do this instead:** Add or extend provider protocol helpers in `providers/__init__.py` and call them through `generate_for_provider()`.

### Treating Frontend Modules as Runtime Imports

**What happens:** Changes are made only in `static/js/generate.js`, `static/js/providers.js`, or `static/js/video.js` expecting the browser to load them directly.
**Why it's wrong:** `static/index.html` loads only `static/js/app-all.js` at runtime (`static/index.html:807`).
**Do this instead:** Keep `static/js/app-all.js` updated or change `static/index.html` to load the modular files in a deliberate order.

### Writing Secrets to Documentation or Logs

**What happens:** Provider keys, endpoint keys, or admin keys are printed in API responses, logs, docs, or mapping artifacts.
**Why it's wrong:** `.env` and provider settings contain credentials; committed docs must not leak them.
**Do this instead:** Follow existing masking in provider endpoints (`main.py:435`, `main.py:449`) and note only that `.env` exists.

### Adding Persistent State Outside `storage/`

**What happens:** Runtime features write JSON, media, or logs into arbitrary root directories.
**Why it's wrong:** Docker, PyInstaller, and local startup flows expect mutable runtime state under `storage/` through `STORAGE_DIR` and `GALLERY_DIR` (`config.py:39`).
**Do this instead:** Add new runtime files beneath `storage/` and reference them through `config.py` constants or local `STORAGE_DIR` derivatives.

## Error Handling

**Strategy:** Convert user-facing validation errors to `HTTPException`, keep background task errors in task state/logs, and translate upstream provider errors before returning them to the UI.

**Patterns:**
- Raise `HTTPException` for missing providers, bad requests, and missing files in route handlers (`main.py:769`, `main.py:1906`, `main.py:2357`).
- Capture provider failures into `ImageResult(success=False, error=...)` rather than throwing through generation fan-out (`providers/__init__.py:215`, `providers/__init__.py:235`).
- Store image background task exceptions in `image_tasks[gen_id]["provider_states"]` and `results` for polling (`main.py:942`).
- Translate upstream text with `translate_upstream_error()` before exposing video/provider failures (`main.py:2040`, `main.py:2065`).
- Use `_write_log()` to append operational logs to `storage/logs.jsonl` (`main.py:1551`).

## Cross-Cutting Concerns

**Logging:** Use `_write_log(category, message, details)` in `main.py` for app logs persisted to `storage/logs.jsonl`; use `print()` sparingly in lower-level config/provider helpers.

**Validation:** Request bodies use Pydantic models in `main.py` and config models in `config.py`. Filename/path access is mostly constrained by `GALLERY_DIR` and `VIDEO_DIR`; URL proxying includes `_is_url_safe()` SSRF checks in `main.py`.

**Authentication:** Production API authentication is enforced by `admin_auth_middleware()` with `X-Admin-Key`; development mode bypasses admin-key checks through `verify_admin_key()` in `config.py`.

**Rate Limiting:** `_check_rate_limit()` in `main.py` stores per-IP request timestamps in `_rate_limit_store` and is applied to `/api/generate`.

**Security Headers and CSRF:** `add_security_headers()` and `csrf_protection()` middlewares run in `main.py` before route handling.

---

*Architecture analysis: 2026-07-11*
