import asyncio

import pytest
from fastapi.testclient import TestClient

import main
from extensions.capabilities import DEPLOYMENT_CAPABILITIES, validate_deployment_capability
from extensions.catalog import public_catalog
from extensions.models import ExtensionDeployRequest, ExtensionPlanRequest, ExtensionTarget, SSHCredential
from extensions.orchestrator import DeploymentPlanManager, ExtensionTaskManager


SECRET_SENTINEL = "capability-test-secret-must-not-leak"
UNSUPPORTED_PROJECT_IDS = [
    "unknown-project",
    "gemini2api-liwei9745",
    "gemini2api-xwteam",
    "grok2api",
    "kiro2api",
]


def target_payload():
    return {
        "id": "capability-target",
        "name": "Capability VPS",
        "host": "vps.example",
        "username": "ubuntu",
        "chatgpt2api_port": 33010,
    }


def request_payload(project_id="chatgpt2api", **overrides):
    payload = {
        "project_id": project_id,
        "target": target_payload(),
        "credential": {"password": SECRET_SENTINEL},
        "service_port": 33010,
    }
    payload.update(overrides)
    return payload


def test_project_id_defaults_and_has_a_safe_format():
    target = ExtensionTarget(**target_payload())
    deploy = ExtensionDeployRequest(target=target, credential=SSHCredential(password="test-only"))
    plan = ExtensionPlanRequest(target=target, credential=SSHCredential(password="test-only"))

    assert deploy.project_id == plan.project_id == "chatgpt2api"
    with pytest.raises(ValueError):
        ExtensionDeployRequest(project_id="Not Safe", target=target, credential=SSHCredential(password="test-only"))


def test_catalog_deployability_is_derived_from_capability_registry():
    items = public_catalog()["items"]
    ids = [item["id"] for item in items]

    assert len(ids) == len(set(ids))
    assert set(DEPLOYMENT_CAPABILITIES) == {"chatgpt2api"}
    for item in items:
        capability = DEPLOYMENT_CAPABILITIES.get(item["id"])
        assert item["deployable"] is (capability is not None and capability.repository == item["repository"])
    assert DEPLOYMENT_CAPABILITIES["chatgpt2api"].repository == "yukkcat/chatgpt2api"


@pytest.mark.parametrize("project_id", UNSUPPORTED_PROJECT_IDS)
def test_plan_route_rejects_unsupported_project_before_discovery(monkeypatch, project_id):
    discovered = []

    async def forbidden_discovery(_request):
        discovered.append(True)
        raise AssertionError("discovery must not run")

    monkeypatch.setattr(main, "discover_environment", forbidden_discovery)
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/deploy/plan", json=request_payload(project_id),
    )

    assert response.status_code == 400
    assert discovered == []
    assert SECRET_SENTINEL not in response.text


@pytest.mark.parametrize("project_id", UNSUPPORTED_PROJECT_IDS)
def test_deploy_route_rejects_unsupported_project_before_task_creation(monkeypatch, project_id):
    created = []

    class Tasks:
        def create(self, _request):
            created.append(True)
            raise AssertionError("task creation must not run")

    monkeypatch.setattr(main, "extension_tasks", Tasks())
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/deploy", json=request_payload(project_id),
    )

    assert response.status_code == 400
    assert created == []
    assert SECRET_SENTINEL not in response.text


@pytest.mark.parametrize("deployment_mode", ["warp", "python"])
def test_routes_reject_unsupported_deployment_modes_before_side_effects(monkeypatch, deployment_mode):
    discovered = []
    created = []

    async def forbidden_discovery(_request):
        discovered.append(True)
        raise AssertionError("discovery must not run")

    class Tasks:
        def create(self, _request):
            created.append(True)
            raise AssertionError("task creation must not run")

    monkeypatch.setattr(main, "discover_environment", forbidden_discovery)
    monkeypatch.setattr(main, "extension_tasks", Tasks())
    client = TestClient(main.app, base_url="http://testserver")

    assert client.post("/api/extensions/deploy/plan", json=request_payload(deployment_mode=deployment_mode)).status_code == 400
    assert client.post("/api/extensions/deploy", json=request_payload(deployment_mode=deployment_mode)).status_code == 400
    assert discovered == []
    assert created == []


def test_compose_plan_route_binds_project_strategy_and_mode(monkeypatch):
    async def discovery(_request):
        return {
            "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": []},
            "instances": [],
        }

    manager = DeploymentPlanManager()
    monkeypatch.setattr(main, "discover_environment", discovery)
    monkeypatch.setattr(main, "deployment_plans", manager)
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/deploy/plan", json=request_payload(),
    )

    assert response.status_code == 200
    plan = response.json()["plan"]
    assert {key: plan[key] for key in ("project_id", "strategy", "deployment_mode")} == {
        "project_id": "chatgpt2api", "strategy": "isolated", "deployment_mode": "compose",
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"project_id": "grok2api"},
        {"strategy": "existing"},
        {"deployment_mode": "warp"},
    ],
)
def test_plan_drift_does_not_consume_valid_plan(changes):
    manager = DeploymentPlanManager()
    target = ExtensionTarget(**target_payload())
    plan_request = ExtensionPlanRequest(target=target, credential=SSHCredential(password=SECRET_SENTINEL), service_port=33010)
    plan = manager.create(plan_request, {
        "environment": {"docker_version": "27.0", "compose_version": "2.30", "listening_ports": []},
        "instances": [],
    })
    deploy_request = ExtensionDeployRequest(
        target=target,
        credential=SSHCredential(password=SECRET_SENTINEL),
        confirmed_plan_id=plan["id"],
    )

    with pytest.raises(ValueError) as excinfo:
        manager.take(plan["id"], deploy_request.model_copy(update=changes))
    assert SECRET_SENTINEL not in str(excinfo.value)
    assert plan["id"] in manager.plans
    assert manager.take(plan["id"], deploy_request)["id"] == plan["id"]


def test_manager_calls_fail_closed_before_task_or_connection(monkeypatch):
    target = ExtensionTarget(**target_payload())
    connected = []

    async def forbidden_connect(_request):
        connected.append(True)
        raise AssertionError("connection must not run")

    monkeypatch.setattr("extensions.orchestrator._connect", forbidden_connect)
    plan_manager = DeploymentPlanManager()
    with pytest.raises(ValueError):
        plan_manager.create(
            ExtensionPlanRequest(project_id="grok2api", target=target, credential=SSHCredential(password="test-only")),
            {"environment": {}, "instances": []},
        )

    async def run():
        task_manager = ExtensionTaskManager()
        with pytest.raises(ValueError):
            task_manager.create(ExtensionDeployRequest(
                project_id="grok2api", target=target, credential=SSHCredential(password="test-only"), confirmed_plan_id="missing",
            ))
        assert task_manager.tasks == {}
        assert task_manager.runners == {}

    asyncio.run(run())
    assert connected == []
    with pytest.raises(ValueError):
        validate_deployment_capability("grok2api", "isolated", "compose")
