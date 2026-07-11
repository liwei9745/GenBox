# Testing Patterns

**Analysis Date:** 2026-07-11

## Test Framework

**Runner:**
- Not detected. There are no `pytest.ini`, `pyproject.toml`, `tox.ini`, `noxfile.py`, `jest.config.*`, `vitest.config.*`, `package.json`, or `*.test.*` / `*.spec.*` files in the repository.
- Python dependencies in `requirements.txt` do not include `pytest`, `pytest-asyncio`, `coverage`, `httpx` test plugins, or lint/test tooling.
- CI in `.github/workflows/build.yml` installs dependencies and runs `python build.py`; CI in `.github/workflows/docker.yml` builds and publishes a Docker image. Neither workflow runs automated tests.

**Assertion Library:**
- Not detected. Use Python `assert` with `pytest` for new backend tests when a test suite is introduced.
- For FastAPI route tests, use FastAPI/Starlette `TestClient` or `httpx.AsyncClient` against `main.app` once `pytest` tooling is added.

**Run Commands:**
```bash
python main.py              # Manual smoke run for the FastAPI app
python check_env.py         # Manual environment diagnostic
python build.py             # PyInstaller build smoke used by CI
# Not configured: pytest, coverage, JavaScript unit tests, browser E2E tests
```

## Test File Organization

**Location:**
- No automated test directory exists.
- Recommended convention for new tests: create `tests/` at repository root, mirroring production modules: `tests/test_config.py`, `tests/test_key_pool.py`, `tests/test_providers.py`, `tests/test_main_api.py`, and `tests/test_static_js_smoke.py` if browser tooling is added.
- Keep generated media and runtime state out of tests by using temporary directories instead of `storage/`, `storage/gallery/`, and `storage/videos/`.

**Naming:**
- No current naming pattern exists.
- Recommended Python naming: files `test_<module>.py`, functions `test_<behavior>()`, and async tests `async def test_<behavior>()` with `pytest.mark.asyncio` when `pytest-asyncio` is introduced.
- Recommended API test naming: group by route domain, for example `tests/test_providers_api.py` for `/api/providers` behavior in `main.py`, `tests/test_gallery_api.py` for `/api/gallery`, and `tests/test_generate_api.py` for `/api/generate` task creation.

**Structure:**
```text
tests/
├── test_config.py          # `config.py` Pydantic models and ConfigManager behavior
├── test_key_pool.py        # `providers/key_pool.py` round-robin and cooldown behavior
├── test_providers.py       # `providers/__init__.py` protocol detection and result mapping
├── test_main_api.py        # `main.py` FastAPI route behavior with TestClient
└── conftest.py             # temp storage, env isolation, monkeypatch fixtures
```

## Test Structure

**Suite Organization:**
```python
def test_key_pool_returns_keys_in_round_robin_order():
    pool = KeyPool(["k1", "k2"])

    first = await pool.get_key()
    second = await pool.get_key()

    assert [first, second] == ["k1", "k2"]
```

**Patterns:**
- Use behavior-focused test names because production code is function-oriented: `test_detect_protocol_prefers_google_native_url`, `test_create_provider_replaces_existing_provider`, `test_gallery_image_returns_404_for_missing_file`.
- Use temporary filesystem fixtures for code that writes files. `config.py` creates `STORAGE_DIR`, `GALLERY_DIR`, and `PROVIDERS_FILE`; `providers/__init__.py` writes images through `_save_image()`; `main.py` scans and mutates gallery/video files.
- Use environment isolation for code that reads env vars. `config.py` reads `.env` through `load_dotenv`, and `main.py` reads `ALLOWED_ORIGINS`, `RATE_LIMIT_GENERATE`, and `RATE_LIMIT_API`.
- Test FastAPI handlers through the app boundary for route behavior and by direct helper calls for pure validation logic. Route examples live in `main.py` around `list_providers()`, `create_provider()`, `generate()`, `gallery()`, and `llm_optimize()`.
- For frontend behavior, prefer browser-level tests for DOM updates and fetch interactions because `static/js/*.js` relies on `window`, `document`, inline handlers, and global state.

## Mocking

**Framework:**
- Not detected. Recommended Python mocking tools are `pytest.monkeypatch`, `unittest.mock.Mock`, and `unittest.mock.AsyncMock` once tests are added.
- Recommended browser mocking tools are Playwright route interception for E2E or a DOM test runner if a JavaScript package setup is introduced.

**Patterns:**
```python
async def fake_generate_for_provider(cfg, prompt, **kwargs):
    return ImageResult(success=True, local_path="/tmp/fake.png", model=cfg.id, generation_id="gid")

monkeypatch.setattr("providers.generate_for_provider", fake_generate_for_provider)
```

**What to Mock:**
- Network calls through `httpx.AsyncClient` in `providers/__init__.py`, `main.py`, and `updater.py`.
- Upstream provider functions such as `fetch_models_from_upstream()`, `enhance_prompt_with_llm()`, and `enhance_prompt_with_llm_detailed()` imported by `main.py`.
- Time-dependent behavior in `providers/key_pool.py` (`time.time()` cooldown logic), `main.py` generation IDs/progress, and `updater.py` mirror latency checks.
- External processes such as `subprocess.run(...)` in `build.py`, `check_env.py`, `main.py` video metadata extraction, and `updater.py` source updates.
- Browser `fetch`, `localStorage`, clipboard, and DOM APIs used by `static/js/app.js`, `static/js/providers.js`, `static/js/generate.js`, `static/js/gallery.js`, `static/js/video.js`, `static/js/theme.js`, and `static/js/navigation.js`.

**What NOT to Mock:**
- Pydantic validation for request/config models in `main.py` and `config.py`; construct real `GenerateRequest`, `ProviderCreateReq`, `ProviderConfig`, and `ProvidersConfig` objects.
- Pure logic such as `_detect_protocol()`, `get_video_model_spec()`, `get_video_model_spec_dict()`, `_is_url_safe()` with safe public hosts, `parse_version()`, and `compare_versions()`.
- `KeyPool` round-robin and cooldown state transitions in `providers/key_pool.py`; use real instances and controlled time.

## Fixtures and Factories

**Test Data:**
```python
def make_provider(**overrides):
    data = {
        "id": "test-image",
        "name": "Test Image",
        "type": "image",
        "api_key": "test-key",
        "base_url": "https://example.com/v1",
        "model": "test-model",
        "enabled": True,
    }
    data.update(overrides)
    return ProviderConfig(**data)
```

**Location:**
- No fixture location exists yet.
- Put shared factories and filesystem/env fixtures in `tests/conftest.py` once tests are introduced.
- Keep sample provider JSON minimal and synthetic. Do not use `storage/providers.json` as a fixture because it may contain local runtime configuration.

## Coverage

**Requirements:** None enforced.

**View Coverage:**
```bash
# Not configured. Add pytest-cov before using:
# pytest --cov=. --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Best initial coverage targets are pure or mostly isolated functions in `providers/key_pool.py`, `config.py`, `providers/__init__.py`, and `updater.py`.
- High-value examples: `KeyPool.get_key()`, `KeyPool.mark_error()`, `ProviderConfig.get_effective_keys()`, `ProviderConfig.get_active_endpoints()`, `_detect_protocol()`, `get_video_model_spec_dict()`, `parse_version()`, and `compare_versions()`.

**Integration Tests:**
- API integration tests should instantiate the FastAPI app from `main.py` and exercise routes with isolated config/storage. Useful targets include `/api/setup/status`, `/api/providers`, `/api/providers/{provider_id}`, `/api/gallery`, `/api/llm/optimize`, and `/api/generate/status/{gen_id}`.
- Filesystem integration tests should verify gallery scanning, thumbnail/image response behavior, batch deletion/download behavior, and image metadata writing using temporary directories instead of repository `storage/`.
- Provider integration tests should mock upstream `httpx` responses but run real dispatch/mapping code in `providers/__init__.py`.

**E2E Tests:**
- Not used.
- If introduced, use Playwright against `python main.py` because frontend behavior depends on real DOM, localStorage, CSS classes, and route responses across `static/js/app.js`, `static/js/providers.js`, `static/js/generate.js`, `static/js/gallery.js`, and `static/js/video.js`.
- Smoke flows worth automating: first-run/setup state, provider add/edit, image generation request with mocked backend result, gallery filtering/sorting, video provider selection, and dark/light theme persistence.

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_key_pool_returns_earliest_key_when_all_are_cooling_down(monkeypatch):
    pool = KeyPool(["k1", "k2"])
    pool.mark_error("k1", retry_after=60)
    pool.mark_error("k2", retry_after=120)

    key = await pool.get_key()

    assert key == "k1"
```

**Error Testing:**
```python
def test_llm_optimize_rejects_blank_prompt(client):
    response = client.post("/api/llm/optimize", json={"prompt": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "提示词不能为空"
```

---

*Testing analysis: 2026-07-11*
