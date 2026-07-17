"""Make the test suite independent from developer-local .env files."""
import os
import sys

import pytest


os.environ["APP_MODE"] = "dev"


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
