import json
from types import SimpleNamespace

import pytest

from scripts import genbox_lab


class FakeProcess:
    def __init__(self, pid=1234, create_time=100.0, cwd=None, cmdline=None):
        self.pid = pid
        self._create_time = create_time
        self._cwd = str(cwd or genbox_lab.ROOT)
        self._cmdline = cmdline or ["python", "main.py"]
        self.terminated = False
        self.killed = False
        self.returncode = None

    def create_time(self):
        return self._create_time

    def cwd(self):
        return self._cwd

    def cmdline(self):
        return self._cmdline

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def poll(self):
        return self.returncode


def _state(tmp_path, **updates):
    value = {
        "pid": 1234,
        "create_time": 100.0,
        "repo": str(genbox_lab.ROOT),
        "port": 8892,
        "mode": "dev",
        "head": "abc1234",
        "source": "source123",
    }
    value.update(updates)
    return value


def test_stop_without_state_never_kills_foreign_listener(monkeypatch):
    monkeypatch.setattr(genbox_lab, "read_state", lambda: None)
    monkeypatch.setattr(genbox_lab, "listening_pids", lambda port: {9876})

    with pytest.raises(genbox_lab.LabError, match="未登记进程"):
        genbox_lab.stop_lab(8892)


def test_stop_without_listener_is_an_explicit_noop(monkeypatch, capsys):
    monkeypatch.setattr(genbox_lab, "read_state", lambda: None)
    monkeypatch.setattr(genbox_lab, "listening_pids", lambda port: set())

    assert genbox_lab.stop_lab(8892) is False
    assert "当前无监听" in capsys.readouterr().out


def test_pid_reuse_fails_closed_before_termination(monkeypatch, tmp_path):
    process = FakeProcess(create_time=200.0)
    monkeypatch.setattr(genbox_lab.psutil, "Process", lambda pid: process)

    with pytest.raises(genbox_lab.LabError, match="PID 已被其他进程复用"):
        genbox_lab.validate_owned_process(_state(tmp_path), 8892)

    assert process.terminated is False
    assert process.killed is False


def test_wrong_repo_or_command_fails_closed(monkeypatch, tmp_path):
    process = FakeProcess(cwd=tmp_path, cmdline=["python", "other.py"])
    monkeypatch.setattr(genbox_lab.psutil, "Process", lambda pid: process)

    with pytest.raises(genbox_lab.LabError, match="工作目录不是当前 GenBox"):
        genbox_lab.validate_owned_process(_state(tmp_path), 8892)

    assert process.terminated is False


def test_runtime_health_rejects_non_genbox_schema(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({"status": "ok"}).encode()

    monkeypatch.setattr(genbox_lab.urllib.request, "urlopen", lambda *args, **kwargs: Response())

    with pytest.raises(genbox_lab.LabError, match="不是当前 GenBox"):
        genbox_lab.runtime_health(8892)


def test_start_records_exact_git_head_and_reports_ready(monkeypatch, tmp_path, capsys):
    child = FakeProcess(pid=4321, create_time=321.0)
    recorded = []
    popen_calls = []
    monkeypatch.setattr(genbox_lab, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(genbox_lab, "git_head", lambda: "b1c7b88")
    monkeypatch.setattr(genbox_lab, "source_fingerprint", lambda: "source456")
    monkeypatch.setattr(genbox_lab, "read_state", lambda: None)
    monkeypatch.setattr(genbox_lab, "listening_pids", lambda port: set())
    monkeypatch.setattr(genbox_lab.subprocess, "Popen", lambda *args, **kwargs: popen_calls.append((args, kwargs)) or child)
    monkeypatch.setattr(genbox_lab.psutil, "Process", lambda pid: child)
    monkeypatch.setattr(genbox_lab, "write_state", lambda value: recorded.append(value))
    monkeypatch.setattr(
        genbox_lab,
        "wait_for_health",
        lambda port, head, source, process: {"version": "2.5.1", "runtime_id": "runtime"},
    )

    assert genbox_lab.start_lab(8892, background=True) == 0
    assert recorded[0]["head"] == "b1c7b88"
    assert recorded[0]["pid"] == 4321
    assert recorded[0]["source"] == "source456"
    assert popen_calls[0][1]["stdout"] is genbox_lab.subprocess.DEVNULL
    assert popen_calls[0][1]["stderr"] is genbox_lab.subprocess.DEVNULL
    assert "HEAD b1c7b88" in capsys.readouterr().out


def test_wait_for_health_reports_early_child_exit():
    child = FakeProcess()
    child.returncode = 7

    with pytest.raises(genbox_lab.LabError, match="退出码 7"):
        genbox_lab.wait_for_health(8892, "abc1234", "source123", child, timeout=0.01)


def test_managed_stop_requires_health_then_terminates(monkeypatch, tmp_path):
    state = _state(tmp_path)
    process = FakeProcess()
    monkeypatch.setattr(genbox_lab, "read_state", lambda: state)
    monkeypatch.setattr(genbox_lab, "listening_pids", lambda port: {process.pid})
    monkeypatch.setattr(genbox_lab.psutil, "Process", lambda pid: process)
    monkeypatch.setattr(genbox_lab, "runtime_health", lambda port, head, source: {"service": "genbox"})
    monkeypatch.setattr(genbox_lab, "remove_state", lambda expected_pid=None: None)

    assert genbox_lab.stop_lab(8892) is True
    assert process.terminated is True
    assert process.killed is False


def test_source_fingerprint_changes_when_provider_runtime_code_changes(tmp_path):
    (tmp_path / "providers").mkdir()
    provider = tmp_path / "providers" / "key_pool.py"
    provider.write_text("VALUE = 1\n", encoding="utf-8")
    first = genbox_lab.source_fingerprint(tmp_path)

    provider.write_text("VALUE = 2\n", encoding="utf-8")

    assert genbox_lab.source_fingerprint(tmp_path) != first


def test_start_health_failure_cleans_only_the_new_child(monkeypatch):
    child = FakeProcess(pid=4321, create_time=321.0)
    removed = []
    monkeypatch.setattr(genbox_lab, "git_head", lambda: "b1c7b88")
    monkeypatch.setattr(genbox_lab, "source_fingerprint", lambda: "source456")
    monkeypatch.setattr(genbox_lab, "read_state", lambda: None)
    monkeypatch.setattr(genbox_lab, "listening_pids", lambda port: set())
    monkeypatch.setattr(genbox_lab.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(genbox_lab.psutil, "Process", lambda pid: child)
    monkeypatch.setattr(genbox_lab, "write_state", lambda value: None)
    monkeypatch.setattr(genbox_lab, "remove_state", lambda expected_pid=None: removed.append(expected_pid))
    monkeypatch.setattr(
        genbox_lab,
        "wait_for_health",
        lambda *args, **kwargs: (_ for _ in ()).throw(genbox_lab.LabError("health failed")),
    )

    with pytest.raises(genbox_lab.LabError, match="health failed"):
        genbox_lab.start_lab(8892, background=True)

    assert child.terminated is True
    assert removed == [4321]


def test_dead_stale_record_with_foreign_listener_is_not_silent(monkeypatch, tmp_path):
    state = _state(tmp_path)
    monkeypatch.setattr(genbox_lab, "read_state", lambda: state)
    monkeypatch.setattr(genbox_lab, "listening_pids", lambda port: {9876})
    monkeypatch.setattr(genbox_lab, "validate_owned_process", lambda *args: (_ for _ in ()).throw(genbox_lab.LabError("gone")))
    monkeypatch.setattr(genbox_lab.psutil, "pid_exists", lambda pid: False)
    monkeypatch.setattr(genbox_lab, "remove_state", lambda expected_pid=None: None)

    with pytest.raises(genbox_lab.LabError, match="未登记进程占用"):
        genbox_lab.stop_lab(8892)
