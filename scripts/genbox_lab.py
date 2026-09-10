"""Safe local lifecycle manager for the GenBox development lab."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "storage" / ".genbox-lab-runtime.json"
DEFAULT_PORT = 8892
REQUIRED_HEALTH_KEYS = {
    "service",
    "version",
    "mode",
    "port",
    "started_at",
    "runtime_id",
    "runtime_head",
    "runtime_source",
}


class LabError(RuntimeError):
    pass


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _resolved(value: str | Path) -> str:
    return os.path.normcase(str(Path(value).resolve()))


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def source_fingerprint(root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    files = [path for path in root.glob("*.py") if path.is_file()]
    for directory_name in ("extensions", "providers", "scripts", "static", "sync"):
        directory = root / directory_name
        if directory.is_dir():
            files.extend(path for path in directory.rglob("*") if path.is_file())
    for path in sorted(files, key=lambda item: item.as_posix().lower()):
        if path.suffix.lower() not in {".py", ".js", ".html", ".css", ".json"}:
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def read_state() -> dict | None:
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError) as exc:
        raise LabError("实验室运行记录损坏；为安全起见不会结束任何进程。") from exc
    return value if isinstance(value, dict) else None


def write_state(value: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_name(f".{STATE_PATH.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding="utf-8")
    os.replace(temporary, STATE_PATH)


def remove_state(expected_pid: int | None = None) -> None:
    state = read_state()
    if expected_pid is not None and state and state.get("pid") != expected_pid:
        return
    STATE_PATH.unlink(missing_ok=True)


def listening_pids(port: int) -> set[int]:
    owners: set[int] = set()
    try:
        connections = psutil.net_connections(kind="tcp")
    except (psutil.AccessDenied, OSError) as exc:
        raise LabError("无法核对端口归属；请用管理员 PowerShell 重试。") from exc
    for connection in connections:
        if (
            connection.status == psutil.CONN_LISTEN
            and connection.laddr
            and connection.laddr.port == port
            and connection.pid
        ):
            owners.add(int(connection.pid))
    return owners


def validate_owned_process(state: dict, port: int) -> psutil.Process:
    required = {"pid", "create_time", "repo", "port", "mode", "head", "source"}
    if not required.issubset(state):
        raise LabError("实验室运行记录不完整；不会结束任何进程。")
    if int(state["port"]) != port or state["mode"] != "dev":
        raise LabError("实验室运行记录与当前端口或模式不一致；不会结束任何进程。")
    if _resolved(state["repo"]) != _resolved(ROOT):
        raise LabError("实验室运行记录属于其他目录；不会结束任何进程。")
    try:
        process = psutil.Process(int(state["pid"]))
        if abs(process.create_time() - float(state["create_time"])) > 0.05:
            raise LabError("PID 已被其他进程复用；不会结束该进程。")
        if _resolved(process.cwd()) != _resolved(ROOT):
            raise LabError("PID 的工作目录不是当前 GenBox；不会结束该进程。")
        command_line = [item for item in process.cmdline() if item]
    except psutil.NoSuchProcess as exc:
        raise LabError("已登记的 GenBox 进程已经退出。") from exc
    except (psutil.AccessDenied, OSError) as exc:
        raise LabError("无法完整核对进程身份；不会结束任何进程。") from exc
    main_candidates = [
        Path(item) if Path(item).is_absolute() else Path(process.cwd()) / item
        for item in command_line if Path(item).name.lower() == "main.py"
    ]
    if not main_candidates or all(_resolved(item) != _resolved(ROOT / "main.py") for item in main_candidates):
        raise LabError("PID 的启动命令不是 GenBox main.py；不会结束该进程。")
    if process.pid not in listening_pids(port):
        raise LabError("已登记进程没有监听实验室端口；不会结束该进程。")
    return process


def runtime_health(port: int, expected_head: str | None = None, expected_source: str | None = None) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/runtime/status",
        headers={"Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError, TypeError) as exc:
        raise LabError("实验室健康接口尚未就绪。") from exc
    if set(payload) != REQUIRED_HEALTH_KEYS:
        raise LabError("端口响应不是当前 GenBox 运行身份接口。")
    if payload["service"] != "genbox" or payload["mode"] != "dev" or payload["port"] != port:
        raise LabError("端口响应的服务、模式或端口与 GenBox Lab 不匹配。")
    if expected_head and payload["runtime_head"] != expected_head:
        raise LabError("后端加载的代码提交与当前工作区不一致。")
    if expected_source and payload["runtime_source"] != expected_source:
        raise LabError("后端加载的源码快照与当前工作区不一致。")
    return payload


def wait_for_health(port: int, head: str, source: str, process: subprocess.Popen, timeout: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LabError(f"GenBox 启动进程提前退出，退出码 {process.returncode}。")
        try:
            return runtime_health(port, head, source)
        except LabError as exc:
            last_error = str(exc)
            time.sleep(0.25)
    raise LabError(f"GenBox 在 {timeout:.0f} 秒内未就绪：{last_error}")


def _stop_verified(process: psutil.Process, *, force_after: float = 5.0) -> None:
    process.terminate()
    try:
        process.wait(timeout=force_after)
        return
    except psutil.TimeoutExpired:
        pass
    state = read_state()
    verified = validate_owned_process(state or {}, int(state.get("port", 0)) if state else 0)
    if verified.pid != process.pid:
        raise LabError("强制停止前进程身份发生变化；已拒绝继续。")
    verified.kill()
    verified.wait(timeout=5)


def stop_lab(port: int, *, quiet_absent: bool = False) -> bool:
    state = read_state()
    owners = listening_pids(port)
    if not state:
        if owners:
            raise LabError(f"端口 {port} 被未登记进程占用（PID: {', '.join(map(str, sorted(owners)))})；未结束它。")
        if not quiet_absent:
            print(f"[GenBox Lab] {port} 当前无监听，无需停止。")
        return False
    try:
        process = validate_owned_process(state, port)
        runtime_health(port, str(state["head"]), str(state["source"]))
    except LabError as exc:
        if not psutil.pid_exists(int(state.get("pid", -1))):
            remove_state()
            if owners:
                raise LabError(f"已清理失效运行记录，但端口 {port} 被未登记进程占用（PID: {', '.join(map(str, sorted(owners)))})；未结束它。")
            if not quiet_absent:
                print(f"[GenBox Lab] 已清理失效运行记录；{port} 当前无监听。")
            return False
        raise
    _stop_verified(process)
    remove_state(process.pid)
    print(f"[GenBox Lab] 已安全停止 PID {process.pid}。")
    return True


def start_lab(port: int, *, background: bool = False) -> int:
    head = git_head()
    source = source_fingerprint()
    state = read_state()
    if state:
        try:
            process = validate_owned_process(state, port)
            health = runtime_health(port, str(state["head"]), str(state["source"]))
            if str(state["source"]) != source:
                raise LabError("当前源码已变化，请执行 restart 加载最新代码。")
            print(
                f"[GenBox Lab] 已在运行 | PID {process.pid} | HEAD {state['head']} | "
                f"v{health['version']} | http://127.0.0.1:{port}"
            )
            return 0
        except LabError:
            if psutil.pid_exists(int(state.get("pid", -1))):
                raise
            remove_state()
    owners = listening_pids(port)
    if owners:
        raise LabError(f"端口 {port} 被未登记进程占用（PID: {', '.join(map(str, sorted(owners)))})；未结束它。")

    environment = os.environ.copy()
    environment.update(
        {
            "APP_MODE": "dev",
            "GENBOX_PORT": str(port),
            "GENBOX_NO_BROWSER": "1",
            "GENBOX_RUNTIME_HEAD": head,
            "GENBOX_RUNTIME_SOURCE": source,
            "PYTHONPATH": "",
        }
    )
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "main.py")],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL if background else None,
        stderr=subprocess.DEVNULL if background else None,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    owner = psutil.Process(process.pid)
    write_state(
        {
            "pid": process.pid,
            "create_time": owner.create_time(),
            "repo": str(ROOT),
            "port": port,
            "mode": "dev",
            "head": head,
            "source": source,
        }
    )
    try:
        health = wait_for_health(port, head, source, process)
    except Exception:
        try:
            _stop_verified(owner)
        except Exception:
            pass
        remove_state(process.pid)
        raise

    print(f"[GenBox Lab] READY | PID {process.pid} | HEAD {head} | v{health['version']}")
    print(f"[GenBox Lab] 打开 http://127.0.0.1:{port}/#/extensions")
    if background:
        return 0
    try:
        return process.wait()
    except KeyboardInterrupt:
        _stop_verified(owner)
        return 0
    finally:
        remove_state(process.pid)


def status_lab(port: int) -> int:
    state = read_state()
    if not state:
        owners = listening_pids(port)
        if owners:
            raise LabError(f"端口 {port} 被未登记进程占用（PID: {', '.join(map(str, sorted(owners)))})。")
        print(f"[GenBox Lab] OFFLINE | {port} 无监听")
        return 1
    process = validate_owned_process(state, port)
    health = runtime_health(port, str(state["head"]), str(state["source"]))
    current_source = source_fingerprint()
    if str(state["source"]) != current_source:
        raise LabError("后端仍在运行，但当前源码已变化；请执行 restart。")
    print(
        f"[GenBox Lab] ONLINE | PID {process.pid} | HEAD {state['head']} | "
        f"v{health['version']} | runtime {health['runtime_id']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the local GenBox development lab safely.")
    parser.add_argument("action", choices=("start", "stop", "restart", "status"), nargs="?", default="start")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--background", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        raise LabError("端口必须在 1 到 65535 之间。")
    if args.action == "stop":
        stop_lab(args.port)
        return 0
    if args.action == "status":
        return status_lab(args.port)
    if args.action == "restart":
        stop_lab(args.port, quiet_absent=True)
    return start_lab(args.port, background=args.background)


if __name__ == "__main__":
    configure_console()
    try:
        raise SystemExit(main())
    except LabError as exc:
        print(f"[GenBox Lab] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
