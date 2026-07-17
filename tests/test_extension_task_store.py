import asyncio
import json
import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

import main
from extensions.models import ExtensionDeployRequest, ExtensionTarget, SSHCredential
from extensions.orchestrator import ExtensionTaskManager, deployment_plans
from extensions.task_store import TASK_STORE_SCHEMA_VERSION, TaskStore


def task(task_id, status="completed", updated_at="2026-07-17T00:00:00.000Z", **extra):
    return {
        "id": task_id,
        "status": status,
        "phase": "verify",
        "progress": 100 if status == "completed" else 20,
        "steps": [{"id": "connect", "label": "Connect", "status": "success"}],
        "logs": [{"time": "00:00:00", "message": "Public progress"}],
        "error": None,
        "host_key": "SHA256:public",
        "result": None,
        "created_at": "2026-07-16T00:00:00.000Z",
        "updated_at": updated_at,
        "recovery_action": None,
        **extra,
    }


def test_task_store_roundtrip_uses_versioned_atomic_json(tmp_path, monkeypatch):
    path = tmp_path / "extension_tasks.json"
    store = TaskStore(path)
    calls = []
    real_replace = os.replace

    def record_replace(source, target):
        calls.append((Path(source), Path(target), Path(source).exists()))
        return real_replace(source, target)

    monkeypatch.setattr("extensions.task_store.os.replace", record_replace)
    store.save([task("finished")])

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == TASK_STORE_SCHEMA_VERSION
    assert payload["tasks"][0]["id"] == "finished"
    assert store.load()[0]["status"] == "completed"
    assert calls[-1][1] == path
    assert calls[-1][2] is True
    assert not list(tmp_path.glob("*.tmp"))


def test_completed_failed_and_cancelled_tasks_survive_manager_rebuild(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks = {
        "completed": task("completed", "completed", "2026-07-17T00:00:03.000Z"),
        "failed": task("failed", "failed", "2026-07-17T00:00:02.000Z", error="safe failure"),
        "cancelled": task("cancelled", "cancelled", "2026-07-17T00:00:01.000Z", error="cancelled"),
    }
    manager._persist()

    rebuilt = ExtensionTaskManager(store_path=path)
    assert {name: rebuilt.get(name)["status"] for name in manager.tasks} == {
        "completed": "completed", "failed": "failed", "cancelled": "cancelled",
    }


def test_running_or_queued_task_recovers_as_interrupted_without_runner(tmp_path):
    path = tmp_path / "extension_tasks.json"
    TaskStore(path).save([task("running", "running"), task("queued", "queued")])

    rebuilt = ExtensionTaskManager(store_path=path)
    for task_id in ("running", "queued"):
        state = rebuilt.get(task_id)
        assert state["status"] == "interrupted"
        assert state["recovery_action"] == "regenerate_plan_and_reprovide_credentials"
        assert task_id not in rebuilt.runners
    assert rebuilt.list_summary()["active_task_id"] is None


def test_corrupt_or_unknown_schema_is_quarantined_without_overwriting_original(tmp_path):
    for name, content in (("corrupt", "{not json"), ("unknown", '{"schema_version": 99, "tasks": []}')):
        path = tmp_path / f"{name}.json"
        path.write_text(content, encoding="utf-8")
        store = TaskStore(path)

        assert store.load() == []
        assert store.warning
        quarantined = list(tmp_path.glob(f"{name}.json.invalid.*.json"))
        assert len(quarantined) == 1
        assert quarantined[0].read_text(encoding="utf-8") == content
        assert not path.exists()
        store.save([task("replacement")])
        assert json.loads(path.read_text(encoding="utf-8"))["tasks"][0]["id"] == "replacement"
        assert quarantined[0].read_text(encoding="utf-8") == content


def test_task_store_defensively_redacts_all_deployment_secret_sentinels(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    sentinels = (
        "password-sentinel", "private key-sentinel", "passphrase-sentinel", "sudo-sentinel",
        "admin key-sentinel", "Bearer sentinel", "-----BEGIN PRIVATE KEY-----", "key block-sentinel",
    )
    manager.tasks["public"] = task("public", error=" / ".join(sentinels), logs=[{
        "time": "00:00:00", "message": " / ".join(sentinels),
    }], result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "admin_key": "admin-secret",
        "instance": {"id": "instance-a", "managed": True, "password": "ssh-secret"},
    })
    manager._persist()

    text = path.read_text(encoding="utf-8")
    for sentinel in (*sentinels, "admin-secret", "ssh-secret", "private-key-secret", "passphrase-secret", "sudo-secret", "enrollment-secret"):
        assert sentinel not in text
    assert '"admin_key_available": true' in text
    assert "Sensitive task detail redacted." in text


def test_delivery_is_once_only_and_restart_requires_credential_recovery(tmp_path):
    path = tmp_path / "extension_tasks.json"
    manager = ExtensionTaskManager(store_path=path)
    manager.tasks["delivery"] = task("delivery", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-a", "managed": True},
    })
    manager.deliveries["delivery"] = "gbx-secret-delivery"
    manager._persist()
    assert "gbx-secret-delivery" not in path.read_text(encoding="utf-8")
    assert manager.take_delivery("delivery") == "gbx-secret-delivery"
    assert manager.take_delivery("delivery") is None
    assert manager.get("delivery")["result"]["admin_key_available"] is False
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["tasks"][0]["result"]["admin_key_available"] is False

    manager.tasks["restart"] = task("restart", result={
        "url": "http://service.example", "api_url": "http://service.example/v1",
        "admin_key_available": True, "instance": {"id": "instance-b", "managed": True},
    })
    manager._persist()
    rebuilt = ExtensionTaskManager(store_path=path)
    recovered = rebuilt.get("restart")
    assert recovered["result"]["admin_key_available"] is False
    assert recovered["result"]["credential_recovery_required"] is True
    assert recovered["recovery_action"] == "reverify_ownership_and_rotate_admin_key"
    assert rebuilt.take_delivery("restart") is None


def test_task_list_route_is_sorted_and_reports_active_latest_and_404(tmp_path, monkeypatch):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks = {
        "older": task("older", "failed", "2026-07-17T00:00:01.000Z"),
        "active-a": task("active-a", "running", "2026-07-17T00:00:02.000Z"),
        "active-z": task("active-z", "queued", "2026-07-17T00:00:02.000Z"),
        "latest": task("latest", "completed", "2026-07-17T00:00:03.000Z"),
    }
    monkeypatch.setattr(main, "extension_tasks", manager)
    client = TestClient(main.app, base_url="http://testserver")

    response = client.get("/api/extensions/tasks")
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data["tasks"]] == ["latest", "active-z", "active-a", "older"]
    assert data["active_task_id"] == "active-z"
    assert data["latest_task_id"] == "latest"
    assert client.get("/api/extensions/tasks/missing").status_code == 404


def test_task_manager_keeps_fifty_terminal_tasks_without_pruning_active_tasks(tmp_path):
    manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
    manager.tasks = {
        f"done-{index}": task(f"done-{index}", "completed", f"2026-07-17T00:00:00.{index:03d}Z")
        for index in range(52)
    }
    manager.tasks["active-running"] = task("active-running", "running")
    manager.tasks["active-queued"] = task("active-queued", "queued")
    manager._persist()

    assert len([item for item in manager.tasks.values() if item["status"] == "completed"]) == 50
    assert {"active-running", "active-queued"}.issubset(manager.tasks)


def test_cancelled_runner_cannot_overwrite_persisted_cancelled_state(tmp_path, monkeypatch):
    class Result:
        stdout = ""
        exit_status = 0

    blocked = asyncio.Event()
    entered_verify = asyncio.Event()

    class Connection:
        async def run(self, command, check=False, **kwargs):
            result = Result()
            if command == "id -u":
                result.stdout = "0"
            elif command == 'printf %s "$HOME"':
                result.stdout = "/home/ubuntu"
            elif "curl -fsS" in command:
                entered_verify.set()
                await blocked.wait()
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(_request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        manager = ExtensionTaskManager(store_path=tmp_path / "extension_tasks.json")
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="test-only"), trust_host_key=True,
            instance_id="chatgpt2api-dev", confirmed_plan_id="cancel-race",
        )
        deployment_plans.plans["cancel-race"] = {
            "id": "cancel-race", "target_id": "t", "instance_id": "chatgpt2api-dev",
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "genbox-chatgpt2api-chatgpt2api-dev", "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        await entered_verify.wait()
        assert manager.cancel(task_id) is True
        blocked.set()
        await manager.runners[task_id]
        assert manager.get(task_id)["status"] == "cancelled"
        assert manager.get(task_id)["result"] is None
        persisted = json.loads((tmp_path / "extension_tasks.json").read_text(encoding="utf-8"))
        assert persisted["tasks"][0]["status"] == "cancelled"

    asyncio.run(run())


def test_extensions_ui_recovery_contract_executes_in_node():
    source = Path(__file__).parents[1] / "static" / "js" / "extensions.js"
    node = r'''
const fs = require('fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
(async () => {
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    style: {}, value: '', textContent: '', innerHTML: '', href: '', readOnly: false, dataset: {},
    classList: { toggle(){}, add(){}, remove(){} },
    querySelector(){ return element('nested'); }, querySelectorAll(){ return []; }, focus(){}, setAttribute(){}, removeAttribute(){},
  });
  return elements.get(id);
}
const timers = [];
const cleared = [];
const calls = [];
let summary = {};
global.window = global;
global.document = { getElementById: element, querySelector(){ return element('query'); }, querySelectorAll(){ return []; }, addEventListener(){}, removeEventListener(){} };
global.i18nText = key => key;
global.getUiLanguage = () => 'en';
global.escHtml = value => String(value || '');
global.extensionNext = () => {};
global.setCheck = () => {};
global.setInterval = (fn, ms) => { const timer = {fn, ms}; timers.push(timer); return timer; };
global.clearInterval = timer => { if (timer) cleared.push(timer); };
global._authFetch = async url => {
  calls.push(url);
  return { ok: true, text: async () => JSON.stringify(url === '/api/extensions/tasks' ? summary : {}) };
};
eval(source);
const hook = window.__extensionTaskRecovery;
if (!hook) throw new Error('recovery hook missing');
const base = (id, status, result) => ({ id, status, progress: 10, steps: [], logs: [], result, recovery_action: 'regenerate_plan_and_reprovide_credentials' });
let selection = hook.select({ active_task_id: 'active', latest_task_id: 'latest', tasks: [base('latest', 'completed', {instance:{id:'latest',managed:true},url:'http://latest',api_url:'http://latest/v1',admin_key_available:false}), base('active', 'running', null)] });
if (selection.taskId !== 'active') throw new Error('active task was not preferred');
selection = hook.select({ active_task_id: null, latest_task_id: 'latest', tasks: [base('latest', 'completed', {instance:{id:'latest',managed:true},url:'http://latest',api_url:'http://latest/v1',admin_key_available:false})] });
if (selection.taskId !== 'latest') throw new Error('latest task fallback was not selected');
summary = { active_task_id: 'active', latest_task_id: 'latest', tasks: [base('latest', 'completed', {instance:{id:'latest',managed:true},url:'http://latest',api_url:'http://latest/v1',admin_key_available:false}), base('active', 'running', null)] };
await hook.restore();
if (timers.length !== 1 || timers[0].ms !== 800) throw new Error('active polling was not started');
await timers[0].fn();
if (!calls.includes('/api/extensions/tasks/active')) throw new Error('active task was not polled');
summary = { active_task_id: null, latest_task_id: 'interrupted', tasks: [base('interrupted', 'interrupted', null)] };
await hook.restore();
if (!cleared.length || !element('extensionMessage').textContent.includes('extensions.recovery_regenerate_plan')) throw new Error('interrupted recovery was not rendered');
calls.length = 0;
summary = { active_task_id: null, latest_task_id: 'completed', tasks: [{...base('completed', 'completed', {instance:{id:'completed',managed:true},url:'http://done',api_url:'http://done/v1',admin_key_available:false,credential_recovery_required:true}), recovery_action:'reverify_ownership_and_rotate_admin_key'}] };
await hook.restore();
if (calls.some(url => url.includes('/delivery'))) throw new Error('unavailable delivery was requested');
if (!element('extensionMessage').textContent.includes('extensions.recovery_rotate_admin_key')) throw new Error('credential recovery was not rendered');
if (source.includes('localStorage')) throw new Error('extension task recovery uses localStorage');
})();
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
