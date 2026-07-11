# Codebase Structure

**Analysis Date:** 2026-07-11

## Directory Layout

```text
GenBox-od/
|-- main.py                 # FastAPI app, routes, middleware, task orchestration
|-- config.py               # Provider/proxy/admin config models and persistence
|-- providers/              # Image/LLM provider gateway and key-pool support
|-- static/                 # Browser SPA HTML, CSS, and JavaScript
|-- storage/                # Runtime mutable state: provider config, logs, histories, media
|-- docs/                   # Screenshots and supporting documentation
|-- wiki-knowledge/         # Generated/reference architecture and API wiki content
|-- skills/                 # Agent skill package source content in this repository
|-- screenshots/            # Screenshot utility scripts and captured/sanitized assets
|-- .github/workflows/      # CI and Docker publishing workflows
|-- .planning/codebase/     # GSD codebase maps written by mapper agents
|-- build.py                # PyInstaller build script
|-- updater.py              # Self-update service logic
|-- check_env.py            # Local environment diagnostics
|-- list_providers.py       # Provider inspection helper
|-- Dockerfile              # Container image definition
|-- docker-compose.yml      # Container deployment configuration
|-- requirements.txt        # Python dependencies
|-- start.bat/start.ps1     # Windows startup helpers
|-- stop.bat/restart.bat    # Windows process control helpers
|-- README.md/README_EN.md  # User-facing documentation
`-- .env.example            # Example environment configuration; do not read `.env`
```

## Directory Purposes

**Root Application Files:**
- Purpose: Keep the deployable Python service and operational scripts at repository root.
- Contains: `main.py`, `config.py`, `updater.py`, `build.py`, `check_env.py`, `list_providers.py`, scripts, Docker files, docs.
- Key files: `main.py`, `config.py`, `requirements.txt`, `Dockerfile`, `build.py`, `updater.py`.

**`providers/`:**
- Purpose: Central provider gateway for image generation, LLM prompt optimization, upstream model listing, and API key rotation.
- Contains: `providers/__init__.py`, `providers/key_pool.py`, `providers/config.py`, `providers/__pycache__/`.
- Key files: `providers/__init__.py`, `providers/key_pool.py`.
- Guidance: Use `providers/__init__.py` for provider protocol behavior. `providers/config.py` is an older duplicate-style config module; the active app imports `config.py` at the root.

**`static/`:**
- Purpose: Static browser SPA served by FastAPI.
- Contains: `static/index.html`, `static/js/`, `static/css/`.
- Key files: `static/index.html`, `static/js/app-all.js`, `static/css/app.css`, `static/css/pages.css`.

**`static/js/`:**
- Purpose: Frontend behavior for app setup, navigation, provider management, image generation, video generation, gallery, modals, theme, and bundle output.
- Contains: `static/js/app-all.js`, `static/js/app.js`, `static/js/generate.js`, `static/js/providers.js`, `static/js/video.js`, `static/js/gallery.js`, `static/js/modals.js`, `static/js/navigation.js`, `static/js/theme.js`.
- Key files: `static/js/app-all.js` is the runtime script loaded by `static/index.html`; modular files are source/reference modules.

**`static/css/`:**
- Purpose: Styling for the full SPA.
- Contains: `static/css/app.css`, `static/css/pages.css`, `static/css/design-system.css`, `static/css/utilities.css`, `static/css/animations.css`, `static/css/bubbles.css`, `static/css/dock.css`, `static/css/glass.css`, `static/css/setup.css`.
- Key files: `static/css/app.css`, `static/css/pages.css`; both are linked from `static/index.html`.

**`storage/`:**
- Purpose: Runtime mutable application data.
- Contains: `storage/providers.json`, `storage/history.jsonl`, `storage/video_history.jsonl`, `storage/logs.jsonl`, `storage/gallery/`, `storage/videos/`, `storage/video_thumbs/`.
- Key files: `storage/providers.json` for provider configuration; `storage/history.jsonl` and `storage/video_history.jsonl` for generated media history.
- Generated: Yes.
- Committed: Treat as runtime data; avoid committing user-generated media or credentials.

**`docs/`:**
- Purpose: Project documentation and screenshots.
- Contains: `docs/branches-guide.md`, `docs/screenshots/`.
- Key files: `docs/branches-guide.md`.

**`wiki-knowledge/`:**
- Purpose: Reference knowledge base for architecture, concepts, entities, and API summaries.
- Contains: `wiki-knowledge/WIKI-SCHEMA.md`, `wiki-knowledge/wiki/`, `wiki-knowledge/wiki/api/`, `wiki-knowledge/wiki/concepts/`, `wiki-knowledge/wiki/entities/`.
- Key files: `wiki-knowledge/wiki/concepts/GenBox-架构.md`, `wiki-knowledge/wiki/api/API-生成与图像.md`.

**`skills/`:**
- Purpose: Skill package source content that is part of this repository distribution.
- Contains: Skill directories such as `skills/spec-driven-development/`, `skills/frontend-ui-engineering/`, `skills/test-driven-development/`, and others.
- Key files: `skills/*/SKILL.md`.
- Guidance: This directory is repository content, not application runtime logic for GenBox.

**`screenshots/`:**
- Purpose: Screenshot utility scripts and captured/sanitized screenshots.
- Contains: `screenshots/recapture.py`, `screenshots/sanitize.py`, `screenshots/inspect_dom.py`, screenshot assets.
- Key files: `screenshots/recapture.py`, `screenshots/sanitize.py`.

**`.github/workflows/`:**
- Purpose: CI and container workflows.
- Contains: `.github/workflows/build.yml`, `.github/workflows/docker.yml`.
- Key files: `.github/workflows/build.yml`, `.github/workflows/docker.yml`.

**`.planning/codebase/`:**
- Purpose: GSD-generated codebase maps consumed by planning and execution commands.
- Contains: `ARCHITECTURE.md`, `STRUCTURE.md` after this mapping.
- Generated: Yes.
- Committed: Yes when orchestrator chooses to commit planning artifacts.

## Key File Locations

**Entry Points:**
- `main.py`: Main service entrypoint, FastAPI `app`, route definitions, middleware, startup setup, uvicorn launch.
- `static/index.html`: SPA entry document served by `GET /`.
- `static/js/app-all.js`: Runtime frontend script loaded by `static/index.html`.
- `Dockerfile`: Container entrypoint through `CMD ["python", "main.py"]`.
- `build.py`: PyInstaller packaging entrypoint.

**Configuration:**
- `config.py`: Active provider, proxy, video model spec, and admin key configuration model.
- `storage/providers.json`: Runtime provider configuration written by `ConfigManager.save()`.
- `.env.example`: Safe example environment file.
- `.env`: Present in the workspace and used by the app, but do not read or quote it.
- `requirements.txt`: Python dependency manifest.
- `docker-compose.yml`: Docker deployment configuration; inspect carefully for secrets before quoting any content.

**Core Logic:**
- `main.py`: HTTP routes for providers, setup, image generation, video generation, gallery, history, logs, dashboard, proxy, keypool, updates, and server control.
- `providers/__init__.py`: Provider protocol detection, image generation, prompt enhancement, upstream model fetch, result normalization.
- `providers/key_pool.py`: API key rotation and cooldown.
- `updater.py`: Release checking and update application.
- `config.py`: Runtime config persistence and admin security helpers.

**Frontend Logic:**
- `static/index.html`: App shell markup and inline event bindings.
- `static/js/app-all.js`: Loaded browser bundle containing global UI functions.
- `static/js/app.js`: Modular source for app globals, auth, setup wizard, dashboard, utilities.
- `static/js/providers.js`: Modular source for provider lists, per-provider settings, drag sort, provider modal behavior.
- `static/js/generate.js`: Modular source for image generation, polling, preview, lightbox, comparison, LLM optimization.
- `static/js/video.js`: Modular source for video generation, video provider cards, model specs, polling, gallery image selection.
- `static/js/gallery.js`: Modular source for gallery and history UI.
- `static/js/navigation.js`: Modular source for page navigation.
- `static/js/modals.js`: Modular source for modal behavior.
- `static/js/theme.js`: Modular source for theme persistence and presets.

**Styling:**
- `static/css/app.css`: Primary application stylesheet linked by `static/index.html`.
- `static/css/pages.css`: Page-specific stylesheet linked by `static/index.html`.
- `static/css/design-system.css`: Design tokens/components source.
- `static/css/utilities.css`: Utility classes.
- `static/css/dock.css`: Dock navigation styling.
- `static/css/setup.css`: Setup/wizard styling.

**Runtime Data:**
- `storage/gallery/`: Generated image files.
- `storage/videos/`: Generated/downloaded video files.
- `storage/video_thumbs/`: Generated video thumbnails.
- `storage/history.jsonl`: Image generation history.
- `storage/video_history.jsonl`: Video generation history.
- `storage/logs.jsonl`: Operational logs.

**Testing and Diagnostics:**
- `check_env.py`: Environment diagnostics.
- `screenshots/inspect_dom.py`: DOM inspection helper.
- `screenshots/recapture.py`: Screenshot capture helper.
- `screenshots/sanitize.py`: Screenshot sanitization helper.
- No dedicated `tests/` directory or test config is detected in this architecture scan.

## Naming Conventions

**Files:**
- Python modules use snake_case: `main.py`, `config.py`, `key_pool.py`, `check_env.py`, `list_providers.py`.
- Frontend JavaScript files use short lowercase feature names: `app.js`, `generate.js`, `providers.js`, `video.js`, `gallery.js`, `modals.js`.
- Stylesheets use lowercase feature names or hyphenated names: `app.css`, `pages.css`, `design-system.css`, `setup.css`.
- Documentation uses uppercase root docs or descriptive kebab-case release notes: `README.md`, `CHANGELOG.md`, `release-notes-v2.3.2-zh.md`.
- Runtime JSONL files use feature names: `storage/history.jsonl`, `storage/video_history.jsonl`, `storage/logs.jsonl`.

**Directories:**
- Runtime app directories use simple lowercase names: `providers/`, `static/`, `storage/`, `docs/`, `screenshots/`.
- Static subdirectories use asset type names: `static/js/`, `static/css/`.
- GSD planning output lives under dot-prefixed `.planning/codebase/`.
- Skill package directories under `skills/` use kebab-case: `skills/spec-driven-development/`, `skills/frontend-ui-engineering/`.

## Where to Add New Code

**New FastAPI Endpoint:**
- Primary code: Add route and local request/response model in `main.py` near related route groups.
- Shared config/schema: Add Pydantic config models or helper methods in `config.py` only when the endpoint needs persistent provider/proxy/admin state.
- Frontend caller: Update `static/js/app-all.js`; if maintaining modular sources, mirror the change in the matching `static/js/*.js` file.

**New Image Provider Protocol:**
- Primary code: Add protocol detection and dispatch in `providers/__init__.py` through `_detect_protocol()` and `_dispatch_generate()`.
- Provider schema: Extend `ProviderConfig.extra` usage or explicit fields in `config.py` only if the setting is provider-wide and persisted.
- Tests/verification: Exercise through `/api/providers/test/{provider_id}`, `/api/providers/fetch-models/{provider_id}`, and `/api/generate`.

**New Video Provider Type:**
- Primary code: Add detection/build/polling helpers in `main.py` near `_detect_video_provider_type()`, payload builders, and `/api/video/generate`.
- Model constraints: Add or update `VIDEO_MODEL_SPECS` and `get_video_model_spec()` mappings in `config.py` and `providers/__init__.py`.
- Frontend: Update `static/js/app-all.js` and `static/js/video.js` if UI behavior depends on new provider capabilities.

**New Provider Setting:**
- Schema: Add field to `ProviderConfig` in `config.py` when it must persist server-side.
- API: Include handling in `ProviderCreateReq` in `main.py` and provider CRUD routes.
- UI: Add modal/list rendering in `static/js/app-all.js` and source mirror `static/js/providers.js`.
- Storage: Let `cfg_mgr.save()` write the value to `storage/providers.json`.

**New Gallery or Media Feature:**
- API and filesystem work: Add to the gallery/video route groups in `main.py` and store files below `storage/gallery/`, `storage/videos/`, or a new subdirectory under `storage/`.
- Frontend: Update gallery or video UI in `static/js/app-all.js` and matching modular source.
- Metadata: Prefer JSONL or sidecar JSON under `storage/` over new root-level files.

**New Dashboard Metric:**
- Backend aggregation: Add to `/api/dashboard` in `main.py`.
- Frontend rendering: Update dashboard rendering in `static/js/app-all.js` and source mirror `static/js/app.js`.
- Storage dependencies: Read from `storage/` or existing globals; keep expensive filesystem scans bounded.

**New Frontend Page/View:**
- Markup: Add page section to `static/index.html` inside the app shell.
- Navigation: Add dock/nav behavior in `static/js/app-all.js` and source mirror `static/js/navigation.js`.
- Styling: Add page layout rules to `static/css/pages.css`; shared tokens/utilities belong in `static/css/design-system.css` or `static/css/utilities.css`.

**New Operational Script:**
- Place source-level diagnostics beside existing helpers at repository root, e.g. `check_env.py` style.
- Place screenshot/DOM tooling under `screenshots/`.
- Place packaging/deployment changes in `build.py`, `Dockerfile`, `docker-compose.yml`, or `.github/workflows/`.

**Utilities:**
- Backend helpers tightly coupled to routes can stay in `main.py` near the route group.
- Provider helpers belong in `providers/__init__.py` unless they only manage key state, in which case use `providers/key_pool.py`.
- Reusable config helpers belong in `config.py`.

## Special Directories

**`storage/`:**
- Purpose: Runtime mutable data and generated media.
- Generated: Yes.
- Committed: Usually no for user-specific runtime contents; `storage/providers.json` can contain sensitive configuration and must be handled carefully.

**`static/`:**
- Purpose: Files served directly by FastAPI.
- Generated: Partly. `static/js/app-all.js` behaves like a bundle while other JS files are modular sources.
- Committed: Yes.

**`providers/__pycache__/` and `__pycache__/`:**
- Purpose: Python bytecode cache.
- Generated: Yes.
- Committed: No.

**`.planning/codebase/`:**
- Purpose: GSD architecture, structure, stack, testing, conventions, and concerns maps.
- Generated: Yes.
- Committed: Project-dependent; these documents are intended for future GSD commands.

**`.github/workflows/`:**
- Purpose: CI/build/deploy automation.
- Generated: No.
- Committed: Yes.

**`wiki-knowledge/`:**
- Purpose: Reference documentation/knowledge graph material for the project.
- Generated: Likely yes.
- Committed: Yes if used as project knowledge.

**`skills/`:**
- Purpose: Skill package content shipped in this repository.
- Generated: No.
- Committed: Yes.

**`.env` and `.env.*`:**
- Purpose: Environment configuration and secrets.
- Generated: Yes.
- Committed: No.
- Handling: Note existence only; never read or quote contents.

---

*Structure analysis: 2026-07-11*
