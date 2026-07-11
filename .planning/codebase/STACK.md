# Technology Stack

**Analysis Date:** 2026-07-11

## Languages

**Primary:**
- Python 3.10+ - FastAPI backend, provider orchestration, updater, diagnostics, and PyInstaller build scripts in `main.py`, `config.py`, `providers/__init__.py`, `updater.py`, `check_env.py`, and `build.py`.
- Browser JavaScript - static single-page UI, provider management, generation workflows, dashboard, update controls, auth-key handling, and local UI state in `static/js/app-all.js`, `static/js/app.js`, `static/js/generate.js`, `static/js/video.js`, `static/js/providers.js`, and related static modules.

**Secondary:**
- CSS - custom static styling in `static/css/app.css`, `static/css/design-system.css`, `static/css/pages.css`, `static/css/setup.css`, `static/css/glass.css`, and supporting CSS files.
- HTML - FastAPI serves `static/index.html` from the root route in `main.py`.
- PowerShell / Batch / VBScript - local Windows launch helpers in `start.ps1`, `start.bat`, `restart.bat`, `stop.bat`, `launch_silent.vbs`, and `create_shortcut.vbs`.
- Dockerfile / YAML - container and GitHub Actions definitions in `Dockerfile`, `docker-compose.yml`, `.github/workflows/build.yml`, and `.github/workflows/docker.yml`.

## Runtime

**Environment:**
- Local source runtime: Python 3.10+ per `README.md` and `README_EN.md`; app starts with `python main.py`.
- CI and Docker runtime: Python 3.11 in `Dockerfile` and `.github/workflows/build.yml`.
- ASGI runtime: `uvicorn` launched from `main.py` when run as `__main__`.
- Browser runtime: static assets under `static/` call local `/api/*` endpoints using `fetch`.

**Package Manager:**
- pip - dependencies installed from `requirements.txt`.
- Lockfile: missing; versions are pinned directly in `requirements.txt` for most core packages.

## Frameworks

**Core:**
- FastAPI 0.115.0 - API server, route declarations, middleware, static serving, and JSON responses in `main.py`.
- Pydantic 2.9.0 - request/config models in `main.py` and `config.py`.
- Uvicorn 0.30.0 - ASGI server in `requirements.txt` and hidden imports in `build.py`.

**Testing:**
- Not detected as an automated test framework. No `pytest`, `unittest` suite, `jest`, or `vitest` config was detected in the package manifests or root config files.
- Manual environment verification is provided by `check_env.py` and launch scripts such as `start.ps1`.

**Build/Dev:**
- PyInstaller - desktop client packaging is driven by `build.py` and `.github/workflows/build.yml`.
- Docker - image build and runtime are defined in `Dockerfile`; local compose uses `docker-compose.yml`.
- GitHub Actions - desktop artifacts and Docker images are built by `.github/workflows/build.yml` and `.github/workflows/docker.yml`.
- ffmpeg / ffprobe - external system binaries used for video metadata and thumbnails in `main.py`; Docker installs `ffmpeg` in `Dockerfile`.

## Key Dependencies

**Critical:**
- `fastapi==0.115.0` - HTTP API server and route framework for `main.py`.
- `uvicorn[standard]==0.30.0` - ASGI server for local and packaged runs.
- `httpx==0.27.0` - async outbound HTTP client for provider calls, model discovery, dashboard network checks, and updates in `providers/__init__.py`, `main.py`, and `updater.py`.
- `python-multipart==0.0.9` - multipart request support for image edit/upload workflows in `providers/__init__.py` and `main.py`.
- `pillow==10.4.0` - image reading, PNG metadata, local image saving, and upscaling in `providers/__init__.py` and `main.py`.
- `pydantic==2.9.0` - request and configuration models in `main.py` and `config.py`.
- `python-dotenv==1.0.1` - `.env` loading and configuration bootstrap in `config.py` and `main.py`.

**Infrastructure:**
- `aiofiles==23.2.1` - included for async file support and packaged as a PyInstaller hidden import in `build.py`.
- `pydantic-settings==2.5.0` - installed but not central in current source files; configuration is handled by custom Pydantic models in `config.py`.
- `psutil>=5.9.0` - host resource/dashboard diagnostics in `main.py` and `check_env.py`.
- `typing-extensions>=4.0.0` - typing compatibility.
- `requests` - not listed in `requirements.txt`, but installed explicitly by `Dockerfile` and `.github/workflows/build.yml`; used by video download/polling paths in `main.py`.
- `pyinstaller` - installed in CI by `.github/workflows/build.yml` for desktop packaging.

## Configuration

**Environment:**
- `.env` file present - contains runtime environment configuration and secrets; do not read or commit contents.
- `.env.example` file present - template exists but was not read because it matches the forbidden environment-file pattern.
- `config.py` loads `.env` from the app base directory, supports PyInstaller paths, creates `storage/` and `storage/gallery/`, and writes provider/admin updates back to `.env`.
- Runtime provider configuration lives in `storage/providers.json` via `PROVIDERS_FILE` in `config.py`; it is generated from `DEFAULT_PROVIDERS` if missing.
- Important environment keys referenced in code include `APP_MODE`, `ADMIN_KEY`, `ALLOWED_ORIGINS`, `RATE_LIMIT_GENERATE`, `RATE_LIMIT_API`, `VERIFY_SSL`, `GPT_IMAGE_API_KEY`, `GPT_IMAGE_BASE_URL`, `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `QWEN_API_KEY`, `QWEN_BASE_URL`, `LLM_API_KEY`, `LLM_BASE_URL`, and `AGNES_API_KEY` / `AGNES_BASE_URL`.

**Build:**
- `requirements.txt` pins Python dependencies.
- `Dockerfile` builds from `python:3.11-slim`, installs `ffmpeg`, copies the repo, exposes port `8891`, and runs `python main.py`.
- `docker-compose.yml` builds the local image, maps `8891:8891`, mounts `./storage:/app/storage`, and mounts `./.env:/app/.env`.
- `build.py` packages `main.py` into a one-file `GenBox` executable and bundles `static/`, `providers/`, `.env.example`, `requirements.txt`, `check_env.py`, `start.bat`, and `README.md`.
- `.github/workflows/build.yml` builds Windows, macOS, and Linux desktop artifacts with Python 3.11 and PyInstaller.
- `.github/workflows/docker.yml` builds and pushes Docker images to GHCR on `master`, `dev`, tags, and pull requests.

## Platform Requirements

**Development:**
- Python 3.10+ and pip are required per `README.md` and `README_EN.md`.
- Install dependencies with `pip install -r requirements.txt`.
- Start locally with `python main.py`; the default browser URL is `http://localhost:8891`.
- ffmpeg/ffprobe are required for video thumbnail and duration features in `main.py`; `check_env.py` validates ffmpeg availability.
- Modern browser required for the static UI under `static/`.

**Production:**
- Docker deployment uses `Dockerfile` and `docker-compose.yml` with persistent `storage/` and `.env` bind mounts.
- Desktop deployment is a PyInstaller one-file executable created by `build.py` and published by `.github/workflows/build.yml`.
- GitHub Container Registry deployment is configured in `.github/workflows/docker.yml` using `ghcr.io/${{ github.repository }}`.
- Production mode is controlled by `APP_MODE=prod` and requires `X-Admin-Key` auth for protected `/api/*` routes in `main.py`.

---

*Stack analysis: 2026-07-11*
