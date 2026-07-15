"""Red regression tests for the v2.5.1 setup and bootstrap security contract.

These tests intentionally describe the approved behavior before the production
implementation is repaired. They must not generate secrets, write ``.env``,
bind a port, or start an external process.
"""

import ast
import re
from types import SimpleNamespace
from pathlib import Path

import pytest
import uvicorn
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import config
import main


ROOT = Path(__file__).parents[1]
CANONICAL_SETUP_STATUS_KEYS = {
    "app_mode",
    "auth_required",
    "needs_provider_setup",
    "has_configured_provider",
    "has_enabled_provider",
    "provider_count",
}


def _api_routes(path: str, method: str) -> list[APIRoute]:
    return [
        route
        for route in main.app.routes
        if isinstance(route, APIRoute)
        and route.path == path
        and method in route.methods
    ]


def test_setup_status_registers_exactly_one_get_route():
    assert len(_api_routes("/api/setup/status", "GET")) == 1


@pytest.mark.parametrize(
    ("app_mode", "providers", "expected"),
    [
        (
            "dev",
            [
                SimpleNamespace(type="image", api_key="", enabled=True),
                SimpleNamespace(type="video", api_key="", enabled=False),
            ],
            {
                "app_mode": "dev",
                "auth_required": False,
                "needs_provider_setup": True,
                "has_configured_provider": False,
                "has_enabled_provider": True,
                "provider_count": 2,
            },
        ),
        (
            "prod",
            [
                SimpleNamespace(type="image", api_key="configured-placeholder", enabled=True),
                SimpleNamespace(type="video", api_key="", enabled=False),
            ],
            {
                "app_mode": "prod",
                "auth_required": True,
                "needs_provider_setup": False,
                "has_configured_provider": True,
                "has_enabled_provider": True,
                "provider_count": 2,
            },
        ),
        (
            "unexpected-mode",
            [
                SimpleNamespace(type="image", api_key="", enabled=False),
                SimpleNamespace(type="video", api_key="", enabled=False),
            ],
            {
                "app_mode": "prod",
                "auth_required": True,
                "needs_provider_setup": True,
                "has_configured_provider": False,
                "has_enabled_provider": False,
                "provider_count": 2,
            },
        ),
    ],
)
def test_setup_status_uses_canonical_non_secret_schema_and_semantics(
    monkeypatch, app_mode, providers, expected
):
    admin_sentinel = "existing-admin-placeholder-must-not-be-returned"
    monkeypatch.setenv("APP_MODE", app_mode)
    monkeypatch.setattr(main, "get_admin_key", lambda: admin_sentinel)
    monkeypatch.setattr(main.cfg_mgr, "_config", SimpleNamespace(providers=providers))
    response = TestClient(main.app).get("/api/setup/status")

    assert response.status_code == 200
    assert set(response.json()) == CANONICAL_SETUP_STATUS_KEYS
    assert response.json() == expected
    assert all("admin" not in key.lower() for key in response.json())
    assert admin_sentinel not in response.text


@pytest.mark.parametrize(
    ("provider", "expected_configured"),
    [
        (SimpleNamespace(type="image", api_key="   ", enabled=True), False),
        (
            SimpleNamespace(
                type="image",
                api_key="",
                api_keys=["  ", "configured-placeholder"],
                enabled=True,
            ),
            True,
        ),
        (
            SimpleNamespace(
                type="video",
                api_key="",
                endpoints=[SimpleNamespace(key=" \t ")],
                enabled=True,
            ),
            False,
        ),
        (
            SimpleNamespace(
                type="video",
                api_key="",
                endpoints=[SimpleNamespace(key="endpoint-placeholder")],
                enabled=True,
            ),
            True,
        ),
    ],
)
def test_setup_status_strips_all_provider_key_sources(
    monkeypatch, provider, expected_configured
):
    monkeypatch.setenv("APP_MODE", "dev")
    monkeypatch.setattr(main.cfg_mgr, "_config", SimpleNamespace(providers=[provider]))

    response = TestClient(main.app).get("/api/setup/status")

    assert response.status_code == 200
    assert set(response.json()) == CANONICAL_SETUP_STATUS_KEYS
    assert response.json()["has_configured_provider"] is expected_configured
    assert response.json()["needs_provider_setup"] is not expected_configured


def test_existing_prod_admin_key_cannot_be_rotated_without_authentication(monkeypatch):
    generated = []

    def fake_generate_admin_key():
        generated.append("called")
        return "replacement-placeholder-never-a-real-secret"

    monkeypatch.setattr(main, "is_prod_mode", lambda: True)
    monkeypatch.setattr(main, "get_admin_key", lambda: "existing-placeholder")
    monkeypatch.setattr(main, "generate_admin_key", fake_generate_admin_key)

    response = TestClient(main.app).post("/api/setup/first-run")

    assert response.status_code in {401, 404, 410}
    assert generated == []
    assert "admin_key" not in response.json()


def test_obsolete_http_bootstrap_routes_are_absent_and_not_auth_exempt():
    obsolete_paths = {"/api/setup/first-run", "/api/setup/confirm"}

    assert obsolete_paths.isdisjoint(main.AUTH_EXEMPT_PATHS)
    assert not [
        route
        for path in obsolete_paths
        for route in _api_routes(path, "POST")
    ]


def test_http_server_seam_passes_safe_dev_and_prod_hosts_to_uvicorn(monkeypatch):
    runner = getattr(main, "run_http_server", None)
    calls = []

    def fake_uvicorn_run(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(uvicorn, "run", fake_uvicorn_run)
    assert callable(runner)

    runner("dev", 8892)
    runner("dev", 8892, host="0.0.0.0")
    runner("prod", 8891)
    runner("prod", 8891, host="127.0.0.2")

    assert len(calls) == 4
    assert [kwargs["host"] for _, kwargs in calls] == [
        "127.0.0.1",
        "127.0.0.1",
        "0.0.0.0",
        "127.0.0.2",
    ]
    assert [kwargs["port"] for _, kwargs in calls] == [8892, 8892, 8891, 8891]
    assert all(
        (args and args[0] is main.app) or kwargs.get("app") is main.app
        for args, kwargs in calls
    )


def test_runtime_environment_seam_prefers_executable_data_dir_immediately(
    tmp_path, monkeypatch
):
    executable_data_dir = tmp_path / "executable-data"
    meipass_dir = tmp_path / "meipass"
    executable_data_dir.mkdir()
    meipass_dir.mkdir()
    variable = "GENBOX_TEST_RUNTIME_ENV_SOURCE"
    (executable_data_dir / ".env").write_text(
        f"{variable}=executable-data\n", encoding="utf-8"
    )
    (meipass_dir / ".env").write_text(f"{variable}=meipass\n", encoding="utf-8")
    monkeypatch.setenv(variable, "stale-process-value")
    prepare = getattr(main, "prepare_runtime_environment", None)

    assert callable(prepare)
    prepare(executable_data_dir, meipass_dir)

    assert main.os.environ[variable] == "executable-data"


def test_runtime_environment_preserves_explicit_process_port(monkeypatch, tmp_path):
    executable_data_dir = tmp_path / "executable-data"
    bundle_dir = tmp_path / "bundle"
    executable_data_dir.mkdir()
    bundle_dir.mkdir()
    (executable_data_dir / ".env").write_text(
        "GENBOX_PORT=19001\nAPP_MODE=dev\n", encoding="utf-8"
    )
    monkeypatch.setenv("GENBOX_PORT", "8891")
    monkeypatch.setattr(config, "PROCESS_ENV_GENBOX_PORT", "8891")

    main.prepare_runtime_environment(executable_data_dir, bundle_dir)

    assert main.os.environ["GENBOX_PORT"] == "8891"
    assert main.os.environ["APP_MODE"] == "dev"


def test_explicit_process_dev_mode_skips_first_run_write_and_starts_local(
    monkeypatch
):
    writes = []
    server_calls = []

    monkeypatch.setenv("APP_MODE", " DeV ")
    monkeypatch.setenv("GENBOX_PORT", "8892")
    monkeypatch.delenv("ADMIN_KEY", raising=False)
    monkeypatch.setattr(main.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(config, "_read_env", lambda: {})
    monkeypatch.setattr(config, "_write_env", lambda updates: writes.append(updates))
    monkeypatch.setattr(main, "prepare_runtime_environment", lambda *args: None)
    monkeypatch.setattr(
        main,
        "run_http_server",
        lambda *args, **kwargs: server_calls.append((args, kwargs)),
    )

    main.run_application()

    assert writes == []
    assert server_calls == [(('dev', 8892), {})]


def test_truly_unconfigured_headless_start_selects_prod_then_fails_closed(
    monkeypatch
):
    writes = []
    server_calls = []

    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.delenv("ADMIN_KEY", raising=False)
    monkeypatch.setenv("GENBOX_PORT", "8891")
    monkeypatch.setenv("GENBOX_NO_BROWSER", "1")
    monkeypatch.setattr(main.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(config, "_read_env", lambda: {})
    monkeypatch.setattr(config, "_write_env", lambda updates: writes.append(updates))
    monkeypatch.setattr(main, "prepare_runtime_environment", lambda *args: None)
    monkeypatch.setattr(
        main,
        "run_http_server",
        lambda *args, **kwargs: server_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        main,
        "generate_admin_key",
        lambda: (_ for _ in ()).throw(
            AssertionError("headless startup must not generate an ADMIN_KEY")
        ),
    )

    with pytest.raises(SystemExit, match="requires ADMIN_KEY"):
        main.run_application()

    assert writes == [{"APP_MODE": "prod"}]
    assert server_calls == []


def test_run_application_orders_setup_prepare_and_same_process_server(monkeypatch, tmp_path):
    events = []
    executable_data_dir = tmp_path / "executable-data"
    bundle_dir = tmp_path / "bundle"

    def fake_first_run_setup():
        events.append(("setup",))

    def fake_prepare_runtime_environment(*args, **kwargs):
        events.append(("prepare", args, kwargs))
        monkeypatch.setenv("APP_MODE", "prod")
        monkeypatch.setenv("GENBOX_PORT", "9911")

    def fake_run_http_server(app_mode, port, **kwargs):
        events.append(("server", app_mode, port, kwargs))

    def fail_if_admin_key_is_generated():
        raise AssertionError("run_application must not generate or replace an ADMIN_KEY")

    def fail_if_env_is_written(*args, **kwargs):
        raise AssertionError("run_application test must not write an .env file")

    monkeypatch.setenv("APP_MODE", "dev")
    monkeypatch.setenv("GENBOX_PORT", "8892")
    monkeypatch.setenv("ADMIN_KEY", "existing-admin-placeholder")
    monkeypatch.setattr(main, "BASE_DIR", executable_data_dir, raising=False)
    monkeypatch.setattr(main, "BASE_PATH", bundle_dir)
    monkeypatch.setattr(main, "_first_run_setup", fake_first_run_setup, raising=False)
    monkeypatch.setattr(
        main,
        "prepare_runtime_environment",
        fake_prepare_runtime_environment,
        raising=False,
    )
    monkeypatch.setattr(main, "run_http_server", fake_run_http_server, raising=False)
    monkeypatch.setattr(main, "generate_admin_key", fail_if_admin_key_is_generated)
    monkeypatch.setattr(config, "_write_env", fail_if_env_is_written)
    monkeypatch.setattr(main, "_write_env", fail_if_env_is_written, raising=False)
    runner = getattr(main, "run_application", None)

    assert callable(runner)
    runner()

    assert [event[0] for event in events] == ["setup", "prepare", "server"]
    assert events[1][1] == (executable_data_dir, bundle_dir)
    assert events[1][2] == {}
    assert events[-1][1:3] == ("prod", 9911)


@pytest.mark.parametrize("admin_value", [None, "", "   "])
def test_headless_prod_without_admin_key_fails_closed_before_server(
    monkeypatch, admin_value
):
    server_calls = []

    def fail_if_admin_key_is_generated():
        raise AssertionError("headless startup must not generate an ADMIN_KEY")

    def fail_if_env_is_written(*args, **kwargs):
        raise AssertionError("headless fail-closed test must not write .env")

    monkeypatch.setenv("APP_MODE", "prod")
    monkeypatch.setenv("GENBOX_PORT", "8891")
    monkeypatch.setenv("GENBOX_NO_BROWSER", "1")
    if admin_value is None:
        monkeypatch.delenv("ADMIN_KEY", raising=False)
    else:
        monkeypatch.setenv("ADMIN_KEY", admin_value)
    monkeypatch.setattr(main, "_first_run_setup", lambda: None)
    monkeypatch.setattr(main, "prepare_runtime_environment", lambda *args: None)
    monkeypatch.setattr(
        main,
        "run_http_server",
        lambda *args, **kwargs: server_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(main, "generate_admin_key", fail_if_admin_key_is_generated)
    monkeypatch.setattr(config, "_write_env", fail_if_env_is_written)
    monkeypatch.setattr(main, "_write_env", fail_if_env_is_written, raising=False)

    with pytest.raises(SystemExit, match="requires ADMIN_KEY") as exc_info:
        main.run_application()

    assert server_calls == []
    assert "http" not in str(exc_info.value).lower()


@pytest.mark.parametrize(
    ("app_mode", "expected_status"),
    [
        ("dev", 200),
        (" DeV ", 200),
        ("DEV", 200),
        ("prod", 401),
        ("", 401),
        ("unexpected-mode", 401),
    ],
)
def test_only_normalized_dev_bypasses_real_api_auth(
    monkeypatch, app_mode, expected_status
):
    monkeypatch.setenv("APP_MODE", app_mode)
    monkeypatch.setenv("ADMIN_KEY", "existing-admin-placeholder")
    monkeypatch.setattr(main.cfg_mgr, "_config", SimpleNamespace(providers=[]))

    response = TestClient(main.app).get("/api/providers")

    assert response.status_code == expected_status


def test_main_guard_directly_delegates_to_run_application():
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    main_guard = None

    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        if not (
            isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ):
            continue
        main_guard = node
        break

    assert main_guard is not None
    direct_calls = [
        statement.value.func.id
        for statement in main_guard.body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
    ]
    assert "run_application" in direct_calls

    class ExecutedGuardCallVisitor(ast.NodeVisitor):
        def __init__(self):
            self.calls = set()

        def visit_FunctionDef(self, node):
            return None

        def visit_AsyncFunctionDef(self, node):
            return None

        def visit_ClassDef(self, node):
            return None

        def visit_Lambda(self, node):
            return None

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                self.calls.add(node.func.id)
            elif (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
            ):
                self.calls.add(f"{node.func.value.id}.{node.func.attr}")
            self.generic_visit(node)

    visitor = ExecutedGuardCallVisitor()
    for statement in main_guard.body:
        visitor.visit(statement)

    forbidden_legacy_calls = {
        "_first_run_setup",
        "load_dotenv",
        "uvicorn.run",
        "run_http_server",
        "prepare_runtime_environment",
    }
    assert visitor.calls.isdisjoint(forbidden_legacy_calls)


def test_frontend_setup_flow_consumes_only_canonical_status_schema():
    source = (ROOT / "static" / "js" / "app-all.js").read_text(encoding="utf-8")
    start = source.index("function checkSetupWizard()")
    end = source.index("function closeSetupWizard()", start)
    setup_flow = source[start:end]

    for field in ("auth_required", "needs_provider_setup"):
        assert re.search(rf"\bd\.{re.escape(field)}\b", setup_flow), field

    for legacy_field in ("needs_first_run", "prod_mode", "has_admin_key", "needs_setup"):
        assert not re.search(rf"\bd\.{legacy_field}\b", setup_flow), legacy_field


def test_frontend_does_not_call_obsolete_http_bootstrap():
    scripts = sorted((ROOT / "static" / "js").glob("*.js"))
    assert scripts

    for script in scripts:
        source = script.read_text(encoding="utf-8")
        assert "/api/setup/first-run" not in source, script


def test_frontend_never_persists_admin_key_in_browser_storage():
    scripts = sorted((ROOT / "static" / "js").glob("*.js"))
    assert scripts

    for script in scripts:
        source = script.read_text(encoding="utf-8")
        # A future hotfix may retain deletion-only cleanup for the legacy key.
        without_legacy_purge = re.sub(
            r"localStorage\.removeItem\(\s*(['\"])igs_admin_key\1\s*\)\s*;?",
            "",
            source,
        )
        assert "igs_admin_key" not in without_legacy_purge, script

        allowed_local_keys = {
            "'genbox_image_settings'",
            "'genbox_provider_settings'",
            "'providerOrder'",
            "'genbox_update_check'",
            "'genbox_update_ignored'",
            "'igs_continuous_generation'",
            "'igs_creator_tools_collapsed'",
            "'igs_font_size'",
            "'igs_image_workbench'",
            "'igs_language'",
            "'igs_llm_provider'",
            "'igs_nav_style'",
            "'igs_theme'",
            "'igs_video_workbench'",
            "'igs_workspace_custom'",
            "'igs_workspace_mode'",
        }
        allowed_session_keys = {"'igs_reopen_onboarding'"}
        allowed_dynamic_local_keys = {
            "'igs_models_'+pid",
            "'igs_'+kind+'_workbench'",
        }
        web_storage_call = re.compile(
            r"(?P<store>(?:global\.)?(?:localStorage|sessionStorage))\s*\.\s*"
            r"(?P<method>getItem|setItem|removeItem)\s*\(\s*"
            r"(?P<key>[^,\)]+)"
        )

        for match in web_storage_call.finditer(without_legacy_purge):
            store = match.group("store").removeprefix("global.")
            key_expression = re.sub(r"\s+", "", match.group("key"))
            if key_expression == "STORAGE_KEY":
                assert script.name == "theme.js"
                assert "const STORAGE_KEY = 'genbox-theme';" in source
                continue
            if store == "localStorage":
                assert key_expression in allowed_local_keys | allowed_dynamic_local_keys, (
                    script,
                    match.group(0),
                )
            else:
                assert key_expression in allowed_session_keys, (script, match.group(0))

        # No IndexedDB, Cache Storage, or persistent-cookie key operation is
        # approved today. Adding one requires an explicit reviewed allowlist key.
        unapproved_persistent_storage = [
            r"(?:indexedDB|IDBDatabase|IDBObjectStore)\b",
            r"(?:\bcaches\b|CacheStorage|\bcacheStorage\b)\s*\.",
            r"\b(?:objectStore|idbStore)\s*\.",
            r"cookieStore\s*\.",
            r"document\s*\.\s*cookie\b",
        ]
        for pattern in unapproved_persistent_storage:
            assert not re.search(pattern, without_legacy_purge), (script, pattern)
