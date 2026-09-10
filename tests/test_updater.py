import asyncio
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
import updater


def _release(*names: str) -> dict:
    return {
        "assets": [
            {"name": name, "browser_download_url": f"https://example.invalid/{name}"}
            for name in names
        ]
    }


def test_windows_asset_prefers_executable_over_zip() -> None:
    release = _release("GenBox-Windows.zip", "SHA256SUMS.txt", "GenBox.exe")

    assert updater.get_asset_url(release, "win32") == "https://example.invalid/GenBox.exe"


def test_asset_fallback_never_selects_archive() -> None:
    release = _release("custom-windows.zip", "custom-windows.exe")

    assert updater.get_asset_url(release, "win32") == "https://example.invalid/custom-windows.exe"


def test_asset_returns_none_when_only_archive_exists() -> None:
    assert updater.get_asset_url(_release("GenBox-Windows.zip"), "win32") is None


def test_windows_restart_script_replaces_after_stopping_process() -> None:
    target = Path("C:/GenBox/GenBox.exe")
    staged = Path("C:/GenBox/.GenBox.exe.update")
    script = updater._windows_restart_script(
        target,
        staged,
        Path("C:/GenBox/GenBox.exe.bak"),
        4321,
    )

    assert "taskkill /PID 4321 /T /F" in script
    assert script.index("taskkill") < script.index(f'move /Y "{target}"')
    assert f'move /Y "{staged}" "{target}"' in script


class _StreamResponse:
    def __init__(self, payload: bytes, *, status_code=200, headers=None, chunks=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.payload = payload
        self.chunks = chunks
        self.iterated = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def aiter_bytes(self):
        self.iterated = True
        for chunk in self.chunks or [self.payload]:
            yield chunk


class _Client:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def stream(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def test_release_check_uses_only_canonical_https_with_tls_and_bounds(monkeypatch):
    payload = json.dumps({"tag_name": "v9.9.9", "body": "notes"}).encode()
    response = _StreamResponse(payload)
    client = _Client(response)
    client_options = []
    monkeypatch.setattr(
        updater.httpx,
        "AsyncClient",
        lambda **kwargs: client_options.append(kwargs) or client,
    )

    release = asyncio.run(updater.check_latest_release())

    assert release == {"tag_name": "v9.9.9", "body": "notes"}
    assert client_options == [
        {
            "timeout": 15,
            "follow_redirects": False,
            "trust_env": False,
            "verify": True,
        }
    ]
    method, url, request_options = client.calls[0]
    assert method == "GET"
    assert url == "https://api.github.com/repos/liwei9745/GenBox/releases/latest"
    assert request_options["headers"]["Accept"] == "application/vnd.github+json"


def test_release_check_rejects_oversized_content_length_before_iteration(monkeypatch):
    response = _StreamResponse(
        b"{}",
        headers={"content-length": str(updater.UPDATE_RELEASE_RESPONSE_MAX_BYTES + 1)},
    )
    monkeypatch.setattr(updater.httpx, "AsyncClient", lambda **_kwargs: _Client(response))

    assert asyncio.run(updater.check_latest_release()) is None
    assert response.iterated is False


def test_release_check_rejects_chunked_overflow_incrementally():
    response = _StreamResponse(b"", chunks=[b"12", b"345"])

    with pytest.raises(ValueError, match="update_response_bytes_exceeded"):
        asyncio.run(updater._read_bounded_response(response, 4))

    assert response.iterated is True


def test_release_notes_redact_credential_like_text():
    secret = "synthetic-release-secret"
    notes = updater._redact_release_notes(
        f"url=https://example.invalid/file?token={secret} Bearer {secret} "
        f'{{"api_key":"{secret}"}} https://user:{secret}@example.invalid '
        "sk-synthetic12345678"
    )

    assert secret not in notes
    assert notes.count("[REDACTED]") == 5


def test_normal_check_route_exposes_no_download_or_mirror_input(monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")

    async def release():
        return {"tag_name": "v9.9.9", "body": "safe release notes"}

    monkeypatch.setattr(updater, "check_latest_release", release)
    response = TestClient(main.app).get("/api/update/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["automatic_apply_available"] is False
    assert payload["manual_install_required"] is True
    assert "download_url" not in payload
    assert "url" not in payload
    assert "mirror" not in payload


@pytest.mark.parametrize(
    "apply_function",
    [
        updater.apply_update,
        updater.apply_source_update,
        updater.apply_exe_update,
        updater.apply_docker_update,
    ],
)
def test_all_automatic_apply_functions_are_inert(apply_function):
    result = asyncio.run(apply_function())

    assert result["success"] is False
    assert result["code"] == "update_apply_unavailable"
    assert result["automatic_apply_available"] is False
    assert result["manual_install_required"] is True


@pytest.mark.parametrize("field", ["url", "download_url", "mirror", "mirror_url"])
def test_apply_route_forbids_hostile_extra_fields(field, monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")
    response = TestClient(main.app).post(
        "/api/update/apply",
        json={field: "https://attacker.invalid/payload"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("parameter", ["url", "download_url", "mirror", "mirror_url"])
def test_apply_route_forbids_query_parameters(parameter, monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")
    response = TestClient(main.app).post(
        f"/api/update/apply?{parameter}=https%3A%2F%2Fattacker.invalid",
        json={},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "update_apply_parameters_forbidden"


def test_apply_route_returns_unavailable_before_any_side_effect(monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("automatic apply must not start a side effect")

    async def forbidden_async(*_args, **_kwargs):
        raise AssertionError("legacy apply helper must remain unreachable")

    monkeypatch.setattr(updater.httpx, "AsyncClient", forbidden)
    monkeypatch.setattr(updater, "apply_update", forbidden_async)
    monkeypatch.setattr(updater, "apply_source_update", forbidden_async)
    monkeypatch.setattr(updater, "apply_exe_update", forbidden_async)
    monkeypatch.setattr(updater, "apply_docker_update", forbidden_async)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(os, "replace", forbidden)
    monkeypatch.setattr(os, "execv", forbidden)

    response = TestClient(main.app).post("/api/update/apply", json={})

    assert response.status_code == 503
    assert response.json()["detail"] == updater.update_apply_unavailable_detail()


def test_check_route_rejects_browser_mirror_before_http(monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")
    monkeypatch.setattr(
        updater.httpx,
        "AsyncClient",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("hostile mirror must be rejected before HTTP")
        ),
    )

    response = TestClient(main.app).get(
        "/api/update/check?mirror=https%3A%2F%2Fattacker.invalid"
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "update_check_parameters_forbidden"


def test_legacy_mirror_route_is_retired_without_http(monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")
    monkeypatch.setattr(
        updater.httpx,
        "AsyncClient",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("retired mirror route must not perform HTTP")
        ),
    )

    response = TestClient(main.app).get("/api/update/mirrors")

    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "update_mirror_check_unavailable"
