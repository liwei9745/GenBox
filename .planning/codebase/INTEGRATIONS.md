# External Integrations

**Analysis Date:** 2026-07-11

## APIs & External Services

**AI Image Generation:**
- OpenAI-compatible image APIs - text-to-image, image edits, and URL/base64 image retrieval through `/images/generations` and `/images/edits` in `providers/__init__.py`.
  - SDK/Client: `httpx`
  - Auth: `GPT_IMAGE_API_KEY`, provider-level `api_key`, provider-level `api_keys`, or endpoint-level key in `storage/providers.json`
- Google Gemini native API - image generation and image editing through `/v1beta/models/{model}:generateContent` in `providers/__init__.py`.
  - SDK/Client: `httpx`
  - Auth: `GEMINI_API_KEY` or provider-level key
- Qwen / Wanx-compatible APIs - image generation and model discovery through OpenAI-like image/model endpoints in `providers/__init__.py`.
  - SDK/Client: `httpx`
  - Auth: `QWEN_API_KEY` or provider-level key
- Agnes AI - image generation through OpenAI-compatible `/images/generations` with Agnes-specific payload fields in `providers/__init__.py`.
  - SDK/Client: `httpx`
  - Auth: `AGNES_API_KEY` or provider-level key

**AI Text / Prompt Optimization:**
- OpenAI-compatible chat completion APIs - prompt optimization through `/chat/completions` in `providers/__init__.py`.
  - SDK/Client: `httpx`
  - Auth: `LLM_API_KEY` or provider-level key

**AI Video Generation:**
- Flow2API / Gemini-style streaming video APIs - SSE chat-completion flow parsed by `/api/video/generate` in `main.py`.
  - SDK/Client: `httpx`
  - Auth: provider-level video `api_key`
- Volcengine Ark / Agent Plan - async task creation and polling through normalized `contents/generations/tasks` paths in `main.py`.
  - SDK/Client: `httpx` for task creation; `requests` for background polling/download paths
  - Auth: provider-level video `api_key`
- Agnes-style video APIs - video task creation through `/videos` in `main.py`.
  - SDK/Client: `httpx`
  - Auth: provider-level video `api_key`

**Provider Discovery and Connectivity:**
- Provider model discovery - OpenAI `/models`, Gemini `/v1beta/models`, and Qwen model endpoints in `providers/__init__.py` and exposed via `/api/providers/fetch-models/{provider_id}` in `main.py`.
  - SDK/Client: `httpx`
  - Auth: provider-level `api_key`
- Dashboard network checks - probes OpenAI, Gemini, Anthropic, Agnes, Qwen, Zhipu, Volcengine, Baidu, Tencent, Moonshot, DeepSeek, and MiniMax endpoints in `/api/dashboard/network` in `main.py`.
  - SDK/Client: `httpx`
  - Auth: none for HEAD connectivity checks
- IP quality check - calls `https://testisp.info/api/check` in `/api/dashboard/ip-info` in `main.py`.
  - SDK/Client: `httpx`
  - Auth: none detected

**Update Services:**
- GitHub Releases API - update checks through `https://api.github.com/repos/liwei9745/GenBox` in `updater.py`, exposed by `/api/update/check` in `main.py`.
  - SDK/Client: `httpx`
  - Auth: none for app-side checks; CI uses `GITHUB_TOKEN`
- GitHub proxy mirrors - `ghfast.top`, `gh-proxy.com`, `v6.gh-proxy.org`, `hub.gitmirror.com`, `bgithub.xyz`, and direct GitHub are tested in `updater.py` and `/api/update/mirrors` in `main.py`.
  - SDK/Client: `httpx`
  - Auth: none detected
- Git operations for source updates - `git fetch`, `git status`, and `git reset --hard` are run by `updater.py` when the app is deployed from source.
  - SDK/Client: `subprocess`
  - Auth: local git remote credentials, if configured outside the app

## Data Storage

**Databases:**
- Not detected. No SQL/NoSQL database client or ORM is present in `requirements.txt`; runtime state uses JSON files, JSONL history, in-memory dictionaries, and filesystem media under `storage/`.
  - Connection: Not applicable
  - Client: Not applicable

**File Storage:**
- Local filesystem only.
- Provider config: `storage/providers.json` managed by `config.py`.
- Image gallery: `storage/gallery/` managed by `providers/__init__.py` and `main.py`.
- Video files: `storage/videos/` managed by video paths in `main.py`.
- History: `storage/history.jsonl` loaded and appended by `main.py`.
- Logs: local server log files such as `server.log` and runtime log APIs in `main.py`.

**Caching:**
- Browser `localStorage` caches UI settings, admin key, model lists, provider order, theme, and update preferences in `static/js/app-all.js` and `static/js/video.js`.
- In-memory backend state stores generation tasks, video tasks, rate-limit windows, continuous sessions, and key-pool status in `main.py` and `providers/key_pool.py`.
- No Redis, Memcached, or external cache service detected.

## Authentication & Identity

**Auth Provider:**
- Custom admin-key authentication.
  - Implementation: `config.py` generates and hashes `ADMIN_KEY`; `main.py` enforces `X-Admin-Key` for protected `/api/*` routes in production mode.
  - Mode control: `APP_MODE=prod` enables auth; non-production mode bypasses admin-key checks in `main.py`.
  - First-run setup: `/api/setup/first-run`, `/api/setup/status`, and `/api/setup/confirm` in `main.py`.
  - Client storage: admin key is saved in browser `localStorage` by `static/js/app-all.js`.

## Monitoring & Observability

**Error Tracking:**
- None detected as an external service. No Sentry, OpenTelemetry, Datadog, or similar dependency is listed in `requirements.txt`.

**Logs:**
- Console printing and local log APIs are used in `main.py`.
- Server log files `server.log` and `server.err` are present in the repository root.
- `/api/logs` and `/api/dashboard` in `main.py` expose local operational state to the UI.

## CI/CD & Deployment

**Hosting:**
- Local desktop/server runtime on `http://localhost:8891` via `main.py`.
- Docker runtime via `Dockerfile` and `docker-compose.yml`.
- GHCR container image publishing via `.github/workflows/docker.yml`.
- GitHub Releases desktop artifact publishing via `.github/workflows/build.yml`.

**CI Pipeline:**
- GitHub Actions desktop build: `.github/workflows/build.yml` builds Windows, macOS, and Linux PyInstaller artifacts and publishes release assets on tags.
- GitHub Actions Docker build: `.github/workflows/docker.yml` builds and pushes Docker images to `ghcr.io` except on pull-request builds.

## Environment Configuration

**Required env vars:**
- `APP_MODE` - controls development vs production auth behavior in `config.py` and `main.py`.
- `ADMIN_KEY` - production admin key stored in `.env` and checked by `main.py`.
- `ALLOWED_ORIGINS` - CORS allow-list for FastAPI middleware in `main.py`.
- `GPT_IMAGE_API_KEY`, `GPT_IMAGE_BASE_URL` - default GPT Image provider config in `config.py`.
- `GEMINI_API_KEY`, `GEMINI_BASE_URL` - default Gemini provider config in `config.py`.
- `QWEN_API_KEY`, `QWEN_BASE_URL` - default Qwen provider config in `config.py`.
- `LLM_API_KEY`, `LLM_BASE_URL` - prompt optimization provider config in `config.py`.
- `AGNES_API_KEY`, `AGNES_BASE_URL` - Agnes image/video provider config in `config.py`.
- `RATE_LIMIT_GENERATE`, `RATE_LIMIT_API` - optional in-memory rate-limit tuning in `main.py`.
- `VERIFY_SSL` - optional outbound SSL verification toggle used by selected `httpx` checks in `main.py`.

**Secrets location:**
- `.env` file present - contains runtime secrets and environment configuration; contents were not read.
- `storage/providers.json` stores provider API keys, endpoint keys, proxy credentials, and model/provider settings via `config.py`.
- Docker compose mounts `./.env:/app/.env` and `./storage:/app/storage` in `docker-compose.yml`.
- GitHub Actions uses `secrets.GITHUB_TOKEN` for GHCR login and release publishing in `.github/workflows/docker.yml` and `.github/workflows/build.yml`.

## Webhooks & Callbacks

**Incoming:**
- No public webhook receiver endpoints detected. API routes in `main.py` are browser/client driven under `/api/*`.
- Protected incoming API surface includes provider management, generation, gallery, logs, dashboard, proxy, update, and setup routes in `main.py`.

**Outgoing:**
- AI provider calls are initiated from generation, model-discovery, and provider-test routes in `main.py` and `providers/__init__.py`.
- Video task polling and media downloads are initiated by background threads in `main.py`.
- Update checks and downloads are initiated by `updater.py` via routes in `main.py`.
- Dashboard probes issue outbound connectivity checks to AI vendor endpoints and `testisp.info` in `main.py`.

---

*Integration audit: 2026-07-11*
