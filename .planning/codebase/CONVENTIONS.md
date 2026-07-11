# Coding Conventions

**Analysis Date:** 2026-07-11

## Naming Patterns

**Files:**
- Use lowercase module names for Python application files: `main.py`, `config.py`, `updater.py`, `check_env.py`, `build.py`.
- Keep provider support code under `providers/`, with implementation modules such as `providers/__init__.py`, `providers/key_pool.py`, and the legacy `providers/config.py`.
- Keep browser JavaScript modules under `static/js/`, grouped by page or feature: `static/js/generate.js`, `static/js/providers.js`, `static/js/gallery.js`, `static/js/video.js`, `static/js/navigation.js`, `static/js/theme.js`.
- Treat `static/js/app-all.js` as a bundled or legacy aggregate surface. Add new browser logic to focused modules such as `static/js/generate.js` or `static/js/video.js` unless the build/runtime explicitly requires updating the aggregate file.

**Functions:**
- Python functions use `snake_case`: `get_base_path()` in `main.py`, `_is_url_safe()` in `main.py`, `_check_rate_limit()` in `main.py`, `_detect_protocol()` in `providers/__init__.py`, and `clean_build()` in `build.py`.
- Private Python helpers use a leading underscore: `_save_image()` and `_dispatch_generate()` in `providers/__init__.py`, `_calc_group_timings()` and `_do_local_upscale()` in `main.py`.
- FastAPI route handlers use short action-oriented names matching their route: `list_providers()`, `create_provider()`, `delete_provider()`, `generate()`, `gallery()`, and `thumbnail()` in `main.py`.
- Browser JavaScript exposes page actions as `window.<verb><Noun>` functions when handlers are invoked from inline HTML: `window.loadProviders`, `window.renderProviderList`, `window.startGenPolling`, `window.loadGallery`, and `window.videoLog` in `static/js/*.js`.
- New JavaScript modules should prefer the modern style in `static/js/theme.js` and `static/js/navigation.js`: `const`/`let`, arrow callbacks, template literals, and private functions inside an IIFE. Match older `var` + `function` style only when editing a legacy module that already uses it, such as `static/js/providers.js` or `static/js/generate.js`.

**Variables:**
- Python constants use `UPPER_SNAKE_CASE`: `BASE_PATH`, `ALLOWED_ORIGINS`, `RATE_LIMIT_GENERATE`, `STORAGE_DIR`, `GALLERY_DIR`, `CURRENT_VERSION`.
- Python module-level mutable state uses lower `snake_case`: `generation_history`, `continuous_sessions`, `image_tasks`, `video_tasks`, and `_rate_limit_store` in `main.py`.
- Pydantic model fields use `snake_case`: `llm_provider_id`, `image_data`, `provider_settings`, `upscale_to`, `skip_proxy`, and `endpoint_type` in `main.py` and `config.py`.
- JavaScript global state is stored on `window` with lower camelCase: `window.allProviders`, `window.selectedProviders`, `window.currentMode`, `window.galleryItems`, `window.videoProviders`, and `window.videoGlobalSettings`.
- JavaScript private module state uses leading underscores sparingly for local helpers and caches: `_adminKey` in `static/js/app.js`, `_videoModelSpecCache` in `static/js/video.js`, `_vidHoverTimers` in `static/js/gallery.js`.

**Types:**
- Python classes use `PascalCase`: `GenerateRequest`, `GenerateResponse`, `ProviderCreateReq`, `ProviderConfig`, `ProvidersConfig`, `KeyPool`, `KeyPoolManager`, `UpdateInfo`, and `MirrorTestResult`.
- Request/response schemas should be Pydantic `BaseModel` classes when exposed through FastAPI, as in `main.py` and `config.py`.
- Lightweight internal result objects may use `@dataclass`, as `ImageResult` in `providers/__init__.py` and `UpdateInfo` in `updater.py`.
- Enumerations use `Enum` with uppercase members, as `UpdateType.SOURCE`, `UpdateType.EXE`, `UpdateType.DOCKER`, and `UpdateType.PIP` in `updater.py`.

## Code Style

**Formatting:**
- No formatter configuration is present. There is no `.prettierrc`, `.editorconfig`, `pyproject.toml`, `ruff.toml`, `setup.cfg`, or `eslint.config.*` detected in the repository root.
- Python code uses 4-space indentation, top-level imports, and section dividers for major regions. Follow the existing divider style in `main.py`, `config.py`, `providers/__init__.py`, and `updater.py` for large modules.
- Python line length is flexible. Existing files contain compact one-line conditionals and long data literals, for example `if req.size: kwargs["size"] = req.size` in `main.py` and `HIDDEN_IMPORTS` in `build.py`.
- JavaScript uses 2-space indentation in `static/js/*.js`, `'use strict';`, and IIFE wrappers: `(function(){ ... })();` or `(function () { ... })();`.
- JavaScript string style is mixed. Legacy modules use single quotes and concatenated HTML strings (`static/js/providers.js`, `static/js/generate.js`); newer modules use template literals (`static/js/navigation.js`) and `const`/`let` (`static/js/theme.js`, `static/js/video.js`). Match the file being edited.

**Linting:**
- No lint command or lint config is detected. CI in `.github/workflows/build.yml` and `.github/workflows/docker.yml` does not run `ruff`, `flake8`, `mypy`, `eslint`, or formatting checks.
- Use local consistency as the rule of record: keep imports grouped, keep route handlers near related endpoints, and avoid broad style churn in existing large files such as `main.py`, `providers/__init__.py`, `static/js/generate.js`, and `static/js/video.js`.

## Import Organization

**Order:**
1. Python standard library imports first: `os`, `sys`, `platform`, `asyncio`, `json`, `time`, `uuid`, `Path`, and typing imports in `main.py`, `config.py`, `providers/__init__.py`, and `updater.py`.
2. Third-party imports next: `fastapi`, `pydantic`, `httpx`, `PIL`, and `dotenv`.
3. Local imports last: `from config import ...` and `from providers import ...` in `main.py`, `from config import ...` in `providers/__init__.py`, and `from .key_pool import key_pool_manager` inside the function that needs it.

**Path Aliases:**
- Python uses direct root-relative imports from repository root modules, for example `from config import cfg_mgr` in `main.py` and `providers/__init__.py`.
- Relative imports are used inside packages only when importing sibling provider modules, for example `from .key_pool import key_pool_manager` in `providers/__init__.py`.
- JavaScript does not use module imports or a bundler. Files communicate through `window` globals and must be loaded by HTML in dependency order.

## Error Handling

**Patterns:**
- Public API validation errors should use `HTTPException` with explicit status codes and Chinese user-facing messages, as in `main.py` route handlers for `/api/generate`, `/api/providers/{provider_id}`, `/api/gallery/image/{filename}`, and `/api/llm/optimize`.
- Middleware may return `JSONResponse` directly when rejecting requests, as `csrf_protection()` does in `main.py` with `status_code=403` and a structured `code` field.
- Provider/network operations return structured success objects rather than throwing across layers. `generate_for_provider()` in `providers/__init__.py` returns `ImageResult(success=False, error=...)`; `/api/providers/fetch-models/{provider_id}` in `main.py` returns `{"success": False, "detail": ...}` on upstream failures.
- Long-running generation and video flows record errors into task state and logs rather than failing the whole request. `_process_image_gen()` in `main.py` writes failure details to `state["result"]` and `_write_log(...)`.
- Use truncated external error text in API responses and logs to avoid huge payloads or accidental leakage, following `str(e)[:100]`, `resp.text[:300]`, and `translate_upstream_error(e.response.text[:500])` patterns in `main.py` and `providers/__init__.py`.
- Do not silently ignore meaningful failures in new code. Existing scripts sometimes use `except Exception: pass` for best-effort metadata or UI behavior (`main.py`, `static/js/theme.js`, `static/js/gallery.js`), but new business logic should preserve an error message in response state, log state, or UI status.

## Logging

**Framework:** console and JSONL-style application logging.

**Patterns:**
- Backend operational messages use `print(...)` in scripts and low-level operations: `build.py`, `check_env.py`, `providers/config.py`, and video polling code in `main.py`.
- Application events use `_write_log(...)` in `main.py` for provider changes, generation creation, deletion, and generation errors.
- Frontend UI status should use `window.setStatus(...)` and feature log areas rather than `console.log`. Examples include `static/js/app.js`, `static/js/providers.js`, `static/js/generate.js`, and `static/js/video.js`.
- Frontend developer diagnostics use `console.warn` or `console.error` only for non-user-facing browser failures, such as dock action errors in `static/js/navigation.js`, polling errors in `static/js/app-all.js`, and video model spec fetch failures in `static/js/video.js`.

## Comments

**When to Comment:**
- Use module docstrings for Python modules that define a subsystem: `main.py`, `config.py`, `providers/__init__.py`, `providers/key_pool.py`, `updater.py`, and `build.py`.
- Use section dividers for large files to keep related endpoints and helpers navigable, as in `main.py`, `providers/__init__.py`, and `static/js/*.js`.
- Use comments for non-obvious protocol or deployment rules: SSRF blocked IP ranges in `main.py`, PyInstaller path handling in `main.py` and `config.py`, protocol detection priority in `providers/__init__.py`, and GitHub mirror/update flow in `updater.py`.
- Avoid comments that restate single-line code. Existing comments are useful when they explain compatibility, fallback behavior, or user-facing constraints.

**JSDoc/TSDoc:**
- JavaScript uses occasional JSDoc for async utility functions, for example `window.getVideoModelSpec` and `window.updateVideoUIByModelSpec` in `static/js/video.js`.
- Add JSDoc for functions whose return shape is consumed by multiple UI flows or cached on `window`; simple DOM handlers do not need JSDoc.

## Function Design

**Size:**
- Prefer small helpers for reusable backend behavior: `_is_url_safe()`, `_check_rate_limit()`, `_calc_group_timings()`, `_detect_protocol()`, `_http_post_with_retry()`, and `get_video_model_spec_dict()`.
- Route handlers in `main.py` often include validation, transformation, persistence, and response assembly in one function. When adding new routes, keep the handler readable and move reusable network, filesystem, or protocol logic into helpers in `main.py` or `providers/__init__.py`.
- JavaScript feature modules currently contain large render functions that build HTML strings. For new frontend work, keep repeated HTML fragments in focused builder functions like `window.buildRatioBtns()` in `static/js/providers.js` and `buildDock()` in `static/js/navigation.js`.

**Parameters:**
- FastAPI request bodies should be typed Pydantic models for structured payloads, such as `GenerateRequest`, `ProviderCreateReq`, and `LLMOptimizeRequest` in `main.py`.
- Query/path parameters are simple typed function arguments in route handlers, such as `provider_id: str`, `filename: str`, and `limit: int = 50` in `main.py`.
- Provider functions accept a `ProviderConfig` plus `prompt` and `**kwargs` for cross-provider options, as in `generate_for_provider()` and `_dispatch_generate()` in `providers/__init__.py`.
- JavaScript event handlers exposed to inline HTML usually accept primitive IDs or event objects, as `window.onImageModelChange(pid, newModel)`, `window.setProviderRatio(pid, ratio, el)`, and `window.handleFileSelect(e)`.

**Return Values:**
- FastAPI route handlers return JSON-compatible dictionaries or `FileResponse`/`Response` objects directly from `main.py`.
- Provider generation returns `ImageResult` objects with `success`, `local_path`, `error`, `model`, and related metadata from `providers/__init__.py`.
- Helper functions should return simple `dict`, `list`, `tuple`, `Path`, or booleans unless a dataclass/Pydantic model already exists for the concept.
- Frontend functions that mutate UI state usually return `undefined`; functions that load remote data return Promises when callers chain them, as `window.loadProviders()` in `static/js/providers.js`.

## Module Design

**Exports:**
- Python modules export by normal top-level names; there is no explicit `__all__`. Import only needed names from `config.py` and `providers/__init__.py` to keep dependencies visible.
- `providers/__init__.py` is both package initializer and main provider service module. Keep provider generation abstractions there unless a new provider-specific file becomes large enough to justify extraction.
- Browser modules export through `window` because the app does not use ES modules. Keep local helper functions private inside each IIFE and expose only handlers or shared utilities needed by HTML or other modules.

**Barrel Files:**
- `providers/__init__.py` acts as the provider package barrel and implementation surface. It is imported from `main.py` for `generate_multi`, `enhance_prompt_with_llm`, `ImageResult`, `fetch_models_from_upstream`, `_save_image`, and `translate_upstream_error`.
- There are no JavaScript barrel files. `static/js/app-all.js` is an aggregate script, but modular source files in `static/js/` are the clearer maintenance surface.

---

*Convention analysis: 2026-07-11*
