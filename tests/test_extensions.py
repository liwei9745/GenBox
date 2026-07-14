import asyncio
import json
import subprocess
import sys
from pathlib import Path

from extensions.models import ExtensionDeployRequest, ExtensionPlanRequest, ExtensionTarget, SSHCredential
import extensions.store as store
from extensions.orchestrator import (
    CLONE_SCRUB_KEYS,
    DeploymentPlanManager,
    ExtensionTaskManager,
    _clone_config_scrub_script,
    _password_sudo_command,
    deployment_plans,
)


def test_deploy_completion_opens_delivery_pane():
    script = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    completed_handler = script.split("async function renderTask", 1)[1].split("window.extensionStartDeploy", 1)[0]

    assert "el('extHandoff').classList.remove('hidden')" in completed_handler
    assert "extensionNext(5)" in completed_handler
    assert completed_handler.index("extensionNext(5)") > completed_handler.index("/delivery")


def test_target_store_never_persists_credentials(tmp_path, monkeypatch):
    path = tmp_path / "extensions.json"
    monkeypatch.setattr(store, "EXTENSIONS_FILE", path)
    target = store.upsert_target({
        "name": "VPS", "host": "203.0.113.10", "username": "ubuntu",
        "password": "must-not-persist", "private_key": "must-not-persist",
    })
    serialized = json.dumps(json.loads(path.read_text(encoding="utf-8")))
    assert target.host == "203.0.113.10"
    assert "must-not-persist" not in serialized
    assert "password" not in serialized
    assert "private_key" not in serialized


def test_target_store_roundtrip_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = store.upsert_target({"name": "VPS", "host": "host.example", "username": "ubuntu"})
    assert store.list_targets()[0].id == target.id
    assert store.delete_target(target.id) is True
    assert store.list_targets() == []


def test_instance_store_contains_no_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    instance = store.upsert_instance({
        "id": "chatgpt2api-dev", "target_id": "vps-a", "service_port": 33010,
        "install_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev",
        "data_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev/data",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "managed": True,
        "admin_key": "must-not-persist", "password": "must-not-persist",
    })
    serialized = (tmp_path / "extensions.json").read_text(encoding="utf-8")
    assert store.get_instance(instance.id).managed is True
    assert "must-not-persist" not in serialized
    assert "admin_key" not in serialized


def test_deploy_task_reports_success(tmp_path, monkeypatch):
    class Result:
        stdout = "genbox-connected"
        exit_status = 0

    class Connection:
        async def run(self, command, check=False, **kwargs):
            result = Result()
            if command == "id -u":
                result.stdout = "0"
            elif command == 'printf %s "$HOME"':
                result.stdout = "/home/ubuntu"
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def fake_connect(request):
        return Connection(), "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
        manager = ExtensionTaskManager()
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="secret"), trust_host_key=True,
            instance_id="chatgpt2api-dev", confirmed_plan_id="plan-test",
        )
        deployment_plans.plans["plan-test"] = {
            "id": "plan-test", "target_id": "t", "instance_id": "chatgpt2api-dev",
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "genbox-chatgpt2api-chatgpt2api-dev",
            "expires_at": 9999999999,
        }
        task_id = manager.create(request)
        await manager.runners[task_id]
        state = manager.get(task_id)
        assert state["status"] == "completed"
        assert state["progress"] == 100
        assert all(step["status"] == "success" for step in state["steps"])
        assert "secret" not in json.dumps(state)
        assert state["result"]["admin_key_available"] is True
        delivered = manager.take_delivery(task_id)
        assert delivered.startswith("gbx-")
        assert manager.take_delivery(task_id) is None

    asyncio.run(run())


def test_working_copy_password_sudo_waits_for_ssh_input(tmp_path, monkeypatch):
    class Result:
        stdout = ""
        exit_status = 0

    class Connection:
        def __init__(self):
            self.commands = []

        async def run(self, command, check=False, input=None, **kwargs):
            self.commands.append((command, input))
            if input == "sudo-secret\n" and not command.startswith("IFS= read -r sudo_password;"):
                raise RuntimeError("Channel not open for sending")
            result = Result()
            if command == "id -u":
                result.stdout = "1000"
            elif command == 'printf %s "$HOME"':
                result.stdout = "/home/ubuntu"
            elif command == "sudo -n true >/dev/null 2>&1":
                result.exit_status = 1
            return result

        def close(self):
            pass

        async def wait_closed(self):
            pass

    connection = Connection()

    async def fake_connect(request):
        return connection, "SHA256:test"

    async def run():
        monkeypatch.setattr("extensions.orchestrator._connect", fake_connect)
        monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
        manager = ExtensionTaskManager()
        request = ExtensionDeployRequest(
            target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu", chatgpt2api_port=33010),
            credential=SSHCredential(password="secret", sudo_password="sudo-secret"), trust_host_key=True,
            instance_id="chatgpt2api-dev", confirmed_plan_id="plan-working-copy",
            clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
        )
        deployment_plans.plans["plan-working-copy"] = {
            "id": "plan-working-copy", "target_id": "t", "instance_id": "chatgpt2api-dev",
            "strategy": "isolated", "deployment_mode": "compose", "service_port": 33010,
            "image": request.image, "compose_project": "genbox-chatgpt2api-chatgpt2api-dev",
            "clone_scope": "working-copy", "clone_source_id": "chatgpt2api-warp",
            "clone_source_data_dir": "/root/chatgpt2api/data",
            "clone_source_config_file": "/root/chatgpt2api/config.json",
            "expires_at": 9999999999,
        }

        task_id = manager.create(request)
        await manager.runners[task_id]

        assert manager.get(task_id)["status"] == "completed"
        privileged = [(command, input_data) for command, input_data in connection.commands if input_data == "sudo-secret\n"]
        assert privileged
        assert all(command.startswith("IFS= read -r sudo_password;") for command, _ in privileged)
        assert all("sudo-secret" not in command for command, _ in privileged)

    asyncio.run(run())


def test_password_sudo_command_preserves_shell_quoting():
    wrapped = _password_sudo_command("printf '%s' \"$HOME\"")

    assert wrapped.startswith("IFS= read -r sudo_password;")
    assert "sudo -S -p '' sh -lc" in wrapped
    assert "sudo_password" in wrapped


def test_deployment_plan_rejects_port_conflict():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu")
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
    )
    discovery = {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": [33010]},
        "instances": [],
    }
    try:
        manager.create(request, discovery)
    except ValueError as exc:
        assert "端口" in str(exc)
    else:
        raise AssertionError("occupied port was accepted")


def test_deployment_plan_is_scoped_and_non_destructive():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu")
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
    )
    plan = manager.create(request, {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": []},
        "instances": [],
    })
    serialized = json.dumps(plan, ensure_ascii=False)
    assert plan["compose_project"] == "genbox-chatgpt2api-chatgpt2api-dev"
    assert "docker rm" not in serialized
    assert "secret" not in serialized


def test_isolated_working_copy_plan_requires_space_and_scrubs_push_state():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu")
    request = ExtensionPlanRequest(
        target=target, credential=SSHCredential(password="secret"), service_port=33010,
        clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    discovery = {
        "environment": {
            "docker_version": "27.0", "compose_version": "2.30",
            "listening_ports": [3000], "disk_free_mb": 5000,
        },
        "instances": [{
            "id": "chatgpt2api-warp", "image": "ghcr.io/yukkcat/chatgpt2api:latest",
            "data_dir": "/opt/chatgpt2api/data", "config_file": "/opt/chatgpt2api/config.json",
            "data_size_mb": 1200, "clone_available": True,
        }],
    }
    plan = manager.create(request, discovery)
    assert plan["clone_scope"] == "working-copy"
    assert plan["clone_size_mb"] == 1200
    assert plan["source_baseline"]["container_id"] == ""
    assert plan["source_baseline"]["data_dir"] == "/opt/chatgpt2api/data"
    assert plan["source_baseline"]["config_file"] == "/opt/chatgpt2api/config.json"
    assert any("凭据" in operation for operation in plan["operations"])
    assert any("Push 身份" in operation for operation in plan["operations"])
    assert "secret" not in json.dumps(plan)


def test_working_copy_plan_rejects_image_drift():
    manager = DeploymentPlanManager()
    request = ExtensionPlanRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="secret"), service_port=33010,
        image="ghcr.io/yukkcat/chatgpt2api:latest",
        clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    discovery = {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": [], "disk_free_mb": 5000},
        "instances": [{
            "id": "chatgpt2api-warp", "image": "ghcr.io/yukkcat/chatgpt2api@sha256:abc",
            "data_dir": "/data", "config_file": "/config.json", "data_size_mb": 100,
            "clone_available": True,
        }],
    }

    try:
        manager.create(request, discovery)
    except ValueError as exc:
        assert "镜像基线" in str(exc)
    else:
        raise AssertionError("working copy accepted image drift")


def test_working_copy_plan_uses_existing_local_image_baseline():
    manager = DeploymentPlanManager()
    baseline_image = "genbox-chatgpt2api-source:abc123456789"
    request = ExtensionPlanRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="secret"), service_port=33010,
        image=baseline_image, clone_source_id="chatgpt2api-warp", clone_scope="working-copy",
    )
    plan = manager.create(request, {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": [], "disk_free_mb": 5000},
        "instances": [{
            "id": "chatgpt2api-warp", "image": baseline_image,
            "source_image_id": "sha256:production-image", "data_dir": "/data",
            "config_file": "/config.json", "data_size_mb": 100, "clone_available": True,
        }],
    })

    assert plan["image"] == baseline_image
    assert plan["clone_source_image_id"] == "sha256:production-image"
    assert any("不拉取 latest" in operation for operation in plan["operations"])


def test_clone_config_scrub_removes_inherited_push_identity_and_keys(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "auth-key": "production-admin-key",
        "genbox_destination": {"url": "https://genbox.example", "push_key": "production-push-key"},
        "nested": {"genbox_source_id": "production-source", "keep": True},
        "backup": {"enabled": True},
    }), encoding="utf-8")

    subprocess.run([sys.executable, "-c", _clone_config_scrub_script(), str(config_path)], check=True)
    scrubbed = json.loads(config_path.read_text(encoding="utf-8"))

    assert "auth-key" in CLONE_SCRUB_KEYS
    assert "auth-key" not in scrubbed
    assert "genbox_destination" not in scrubbed
    assert "genbox_source_id" not in scrubbed["nested"]
    assert scrubbed["nested"]["keep"] is True
    assert scrubbed["backup"]["enabled"] is False


def test_clone_plan_rejects_insufficient_disk():
    manager = DeploymentPlanManager()
    request = ExtensionPlanRequest(
        target=ExtensionTarget(id="t", name="VPS", host="host.example", username="ubuntu"),
        credential=SSHCredential(password="secret"), service_port=33010,
        clone_source_id="chatgpt2api-warp", clone_scope="media",
    )
    try:
        manager.create(request, {
            "environment": {
                "docker_version": "27.0", "compose_version": "2.30",
                "listening_ports": [], "disk_free_mb": 100,
            },
                "instances": [{
                    "id": "chatgpt2api-warp", "data_dir": "/data", "config_file": "/config.json",
                    "image": "ghcr.io/yukkcat/chatgpt2api:latest",
                    "data_size_mb": 1000, "clone_available": True,
                }],
        })
    except ValueError as exc:
        assert "磁盘" in str(exc)
    else:
        raise AssertionError("clone with insufficient disk was accepted")


def test_extensions_page_has_its_own_vertical_scroll_container():
    css = (Path(__file__).parents[1] / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    assert ".extension-layout{min-height:0;overflow-y:auto" in css
    assert "align-items:start" in css
    assert ".extension-workspace{min-width:0;height:max-content" in css


def test_deployed_services_section_is_wired():
    html = (Path(__file__).parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    js = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    assert "已部署服务" in html
    assert 'id="extDrawerList"' in html
    assert 'id="extFab"' in html
    assert 'id="extDrawerOverlay"' in html
    assert "extensionOpenDrawer" in js
    assert "extensionCloseDrawer" in js
    assert "extensionLoadServices" in js
    assert "i18nText('vault.save_login')" in js
    assert "VPS SSH 密码" in html
    assert "extCredentialSshPrivateKey" in html
    assert "window.loadExtensions=async function()" in js
    assert "extensionLoadServices()" in js
    assert "extensionToggleGroup" in js
    assert "extensionOpenResetModal" in js
    assert "extensionCopyText" in js
    assert "extResetKeyModal" in html
    assert "查看已部署服务" in html
    assert "ext-service-launcher" in html
    assert "response=await response" in js
    assert "grok2api" in js
    assert "gemini2api" in js
    assert "mimocode2api" in js
    assert "i18nText('extensions.accounts_short')" in js
    assert "i18nText('extensions.network_short')" in js
    assert '<div class="ext-deployed-collapsed">' in html
    assert '<button type="button" id="extFab"' in html


def test_deployed_services_cards_use_non_secret_fields_only():
    js = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    card_block = js[js.index("ext-bento-grid"):js.index("ext-bento-group-body")]
    assert "console_url" in card_block
    assert "api_url" in card_block
    assert "admin_key" not in card_block
    css = (Path(__file__).parents[1] / "static" / "css" / "extensions.css").read_text(encoding="utf-8")
    assert ".ext-service-card{" in css
    assert ".ext-bento-grid{" in css
    assert ".ext-status-running{" in css
    assert ".ext-status-deployed{" in css
    assert ".ext-status-planned{" in css
    assert ".ext-status-unavailable{" in css
    assert "width:87vw;max-width:none" in css
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in css


def test_deployed_services_reset_requires_ssh_credential():
    js = (Path(__file__).parents[1] / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    assert "extensionConfirmResetKey" in js
    assert "i18nText('extensions.owner_credential_required')" in js
    assert "/api/extensions/instances/reset-admin-key" in js


def test_instance_metadata_persists_after_deploy(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    instance = store.upsert_instance({
        "id": "chatgpt2api-dev", "target_id": "vps-a", "service_port": 33010,
        "install_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev",
        "data_dir": "/home/ubuntu/genbox-apps/chatgpt2api/chatgpt2api-dev/data",
        "image": "ghcr.io/yukkcat/chatgpt2api:latest", "managed": True,
        "console_url": "http://192.0.2.10:33010",
        "api_url": "http://192.0.2.10:33010/v1",
        "status": "running",
    })
    raw = json.loads((tmp_path / "extensions.json").read_text(encoding="utf-8"))
    found = [i for i in raw["instances"] if i["id"] == "chatgpt2api-dev"]
    assert len(found) == 1
    assert found[0]["service_port"] == 33010
    assert found[0]["status"] == "running"
    assert found[0]["console_url"] == "http://192.0.2.10:33010"
    assert found[0]["api_url"] == "http://192.0.2.10:33010/v1"
    retrieved = store.get_instance("chatgpt2api-dev")
    assert retrieved.console_url == "http://192.0.2.10:33010"
    assert retrieved.status == "running"


def test_batch_target_selection_persists_only_valid_ids(tmp_path, monkeypatch):
    import extensions.store as store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    first = store.upsert_target({"id": "one", "name": "One", "host": "one.example", "username": "ubuntu"})
    second = store.upsert_target({"id": "two", "name": "Two", "host": "two.example", "username": "ubuntu"})

    assert store.save_batch_target_ids([second.id, "missing", first.id, second.id]) == ["two", "one"]
    assert store.get_batch_target_ids() == ["two", "one"]


def test_i18n_module_and_page_markers_exist():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "js" / "app-all.js").read_text(encoding="utf-8")
    i18n_js = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")

    assert '/static/js/i18n.js' in html
    assert 'data-i18n=' in html
    assert 'GenBoxI18n' in i18n_js
    assert 'var MESSAGES =' in i18n_js
    assert "url.searchParams.set('lang', next)" in i18n_js
    assert 'global.location.replace(url.toString())' in i18n_js
    assert 'i18nText(' in app_js
    assert 'ipVisibilityIcon' in app_js
    assert '>??</button>' not in app_js
    assert 'var upDays = Math.floor(upSec / 86400);' in app_js
    assert 'setupWizardMarkupV2' in app_js
    assert 'genboxLogoSvgMarkup' in app_js
    assert 'onboardingCapabilityGroupsMarkup' in app_js
    assert 'onboardingChatgptFeatureMarkup' in app_js
    assert 'onboarding-capability-grid' in app_js
    assert '04 / CONNECT TO GENBOX' in app_js
    assert 'GENBOX EXTENSION SERVICES' in html
    assert 'startOnboardingTour' in app_js
    assert 'TreeWalker' not in app_js
    assert 'MutationObserver' not in app_js
