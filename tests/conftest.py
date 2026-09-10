"""Make the test suite independent from developer-local .env files."""
import os
import sys
from pathlib import Path

import pytest


os.environ["APP_MODE"] = "dev"
# Conftest is imported before test modules; task_store reads this before main's
# process-global manager is imported during collection.
os.environ["GENBOX_EXTENSION_TASKS_FILE"] = str(Path.cwd() / f".pytest-extension-tasks-{os.getpid()}.json")


@pytest.fixture(scope="session", autouse=True)
def isolate_main_runtime_files(tmp_path_factory):
    """Keep all pytest generation logs and history outside repository storage."""
    import main

    runtime_dir = tmp_path_factory.mktemp("main-runtime-files")
    main.LOG_FILE = runtime_dir / "logs.jsonl"
    main.HISTORY_FILE = runtime_dir / "history.jsonl"
    yield runtime_dir


@pytest.fixture(autouse=True)
def isolate_extension_task_manager(tmp_path, monkeypatch):
    """Keep process-global extension task state out of developer storage."""
    from extensions.orchestrator import ExtensionTaskManager
    import extensions.orchestrator as orchestrator

    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    monkeypatch.setattr(orchestrator, "extension_tasks", manager)
    main = sys.modules.get("main")
    if main is not None:
        monkeypatch.setattr(main, "extension_tasks", manager)
    yield manager
