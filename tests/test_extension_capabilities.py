import asyncio

import pytest
from fastapi.testclient import TestClient

import main
from extensions.capabilities import DEPLOYMENT_CAPABILITIES, validate_deployment_capability
from extensions.catalog import public_catalog
from extensions.models import (
    ExtensionDeployRequest,
    ExtensionPlanRequest,
    ExtensionTarget as ExtensionTargetModel,
    SSHCredential,
)
from extensions.orchestrator import (
    DeploymentAttemptConflictError,
    DeploymentPlanManager,
    DeploymentResourceConflictError,
    ExtensionTaskManager,
)


SECRET_SENTINEL = "capability-test-secret-must-not-leak"
DEPLOYMENT_ATTEMPT_ID = "0123456789abcdef0123456789abcdef"
PINNED_IMAGE = "ghcr.io/yukkcat/chatgpt2api@sha256:" + ("a" * 64)
TEST_HOST_KEY_ALGORITHM = "ssh-ed25519"
TEST_HOST_KEY = "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
UNSUPPORTED_PROJECT_IDS = [
    "unknown-project",
    "gemini2api-liwei9745",
    "gemini2api-xwteam",
    "grok2api",
    "kiro2api",
]


def ExtensionTarget(**values):
    if values.get("host_key") and "host_key_algorithm" not in values:
        values["host_key_algorithm"] = TEST_HOST_KEY_ALGORITHM
        values["host_key"] = TEST_HOST_KEY
    return ExtensionTargetModel(**values)


def privilege_snapshot():
    return {
        "auth_kind": "password",
        "elevation_contract": "none",
        "is_root": False,
        "docker_access": True,
        "elevated_docker_access": False,
        "passwordless_sudo": False,
        "password_sudo": False,
        "can_admin": False,
        "can_deploy": True,
        "diagnostic_code": "direct_docker",
    }


def environment_snapshot(*, listening_ports=None, disk_free_mb=5000):
    ports = list(listening_ports or [])
    return {
        "docker_version": "27.0",
        "compose_version": "2.30",
        "home_dir": "/home/deploy-user",
        "listening_ports": ports,
        "tcp_listeners": [
            {"protocol": "tcp", "host_port": port} for port in sorted(ports)
        ],
        "listening_ports_probe": {
            "status": 0, "complete": True, "payload_present": True,
        },
        "disk_free_mb": disk_free_mb,
    }


def deployment_discovery(*, listening_ports=None, disk_free_mb=5000):
    return {
        "host_key_algorithm": TEST_HOST_KEY_ALGORITHM,
        "host_key": TEST_HOST_KEY,
        "environment": environment_snapshot(
            listening_ports=listening_ports, disk_free_mb=disk_free_mb,
        ),
        "privileges": privilege_snapshot(),
        "instances": [],
        "path_conditions_version": "phase4-v3",
        "path_conditions": {
            "target_install_dir_absent": True,
            "target_install_parent_claimable": True,
            "target_data_dir_nonoverlap": True,
            "target_compose_project_nonoverlap": True,
            "target_port_unoccupied": True,
        },
    }


def target_payload():
    return {
        "id": "capability-target",
        "name": "Capability VPS",
        "host": "vps.example",
        "username": "deploy-user",
        "chatgpt2api_port": 33010,
    }


def request_payload(project_id="chatgpt2api", **overrides):
    payload = {
        "deployment_attempt_id": DEPLOYMENT_ATTEMPT_ID,
        "project_id": project_id,
        "target": target_payload(),
        "credential": {"password": SECRET_SENTINEL},
        "service_port": 33010,
        "image": PINNED_IMAGE,
    }
    payload.update(overrides)
    return payload


def route_plan_harness(monkeypatch):
    current_target = {
        "value": ExtensionTarget(
            **target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA",
        ),
    }
    manager = DeploymentPlanManager()
    discovered_target_ports = []
    leased_requests = []

    async def discovery(request, *, path_checks=None):
        discovered_target_ports.append(request.target.chatgpt2api_port)
        return deployment_discovery()

    class LeaseOnlyTasks:
        async def create(self, request):
            token, plan = manager.lease(request.confirmed_plan_id, request)
            leased_requests.append((request, plan))
            manager.release(request.confirmed_plan_id, token)
            return "lease-only-no-remote-task"

    monkeypatch.setattr(main, "discover_environment", discovery)
    monkeypatch.setattr(main, "deployment_plans", manager)
    monkeypatch.setattr(main, "extension_tasks", LeaseOnlyTasks())
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: current_target["value"])
    return (
        TestClient(main.app, base_url="http://testserver"),
        manager,
        current_target,
        discovered_target_ports,
        leased_requests,
    )


def create_route_plan(client):
    submitted_target = {**target_payload(), "chatgpt2api_port": 33011}
    response = client.post(
        "/api/extensions/deploy/plan",
        json=request_payload(
            target=submitted_target,
            service_port=33011,
            image=PINNED_IMAGE,
        ),
    )
    assert response.status_code == 200
    return submitted_target, response.json()["plan"]


def route_deploy_payload(submitted_target, plan, **overrides):
    payload = request_payload(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=submitted_target,
        service_port=33011,
        image=PINNED_IMAGE,
        instance_id="chatgpt2api-dev",
        strategy="isolated",
        deployment_mode="compose",
        confirmed_plan_id=plan["id"],
        clone_source_id="",
        clone_scope="empty",
    )
    payload.update(overrides)
    return payload


def test_project_id_defaults_and_has_a_safe_format():
    target = ExtensionTarget(**target_payload())
    deploy = ExtensionDeployRequest(deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID, target=target, credential=SSHCredential(password="test-only"))
    plan = ExtensionPlanRequest(target=target, credential=SSHCredential(password="test-only"))

    assert deploy.project_id == plan.project_id == "chatgpt2api"
    with pytest.raises(ValueError):
        ExtensionDeployRequest(deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID, project_id="Not Safe", target=target, credential=SSHCredential(password="test-only"))


def test_deploy_route_requires_attempt_id_and_returns_sanitized_conflict(monkeypatch):
    created = []

    class Tasks:
        async def create(self, request):
            created.append(request.deployment_attempt_id)
            raise DeploymentAttemptConflictError()

    saved = ExtensionTarget(**target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setattr(main, "extension_tasks", Tasks())
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: saved)
    client = TestClient(main.app, base_url="http://testserver")
    missing = request_payload()
    missing.pop("deployment_attempt_id")

    missing_response = client.post("/api/extensions/deploy", json=missing)
    assert missing_response.status_code == 422
    assert created == []

    response = client.post("/api/extensions/deploy", json=request_payload())
    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "error": "deployment_attempt_conflict",
            "diagnostic": {
                "code": "deployment_attempt_conflict",
                "stage": "deployment_attempt",
                "retry_safe": False,
            },
        },
    }
    assert created == [DEPLOYMENT_ATTEMPT_ID]
    assert all(secret not in response.text for secret in (SECRET_SENTINEL, "vps.example", "deploy-user"))


@pytest.mark.parametrize(
    ("scenario", "code", "stage"),
    [
        ("expired_plan", "deployment_plan_unavailable", "plan_lease"),
        ("snapshot_drift", "deployment_snapshot_changed", "fresh_discovery"),
        ("resource_conflict", "deployment_resource_conflict", "resource_reservation"),
    ],
)
def test_deploy_route_definitive_pre_task_failures_are_typed_no_task_diagnostics(
    monkeypatch, scenario, code, stage,
):
    class Tasks:
        async def create(self, request):
            manager = DeploymentPlanManager()
            if scenario == "expired_plan":
                manager.lease("missing-plan", request)
            elif scenario == "snapshot_drift":
                manager.validate_fresh_snapshot(
                    {"discovery_snapshot": {"expected": True}},
                    {"environment": {}, "privileges": {}, "instances": []},
                )
            else:
                raise DeploymentResourceConflictError()

    saved = ExtensionTarget(**target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setattr(main, "extension_tasks", Tasks())
    monkeypatch.setattr(main.extensions_store, "get_target", lambda _target_id: saved)

    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/deploy",
        json=request_payload(confirmed_plan_id="definitive-no-task"),
    )

    assert response.status_code in {400, 409}
    detail = response.json()["detail"]
    expected_diagnostic = {
        "code": code,
        "stage": stage,
        "retry_safe": False,
        "task_created": False,
    }
    if scenario == "snapshot_drift":
        expected_diagnostic.update({
            "snapshot_category": "plan_snapshot",
            "changed_fields": ["discovery_snapshot"],
        })
    assert detail["diagnostic"] == expected_diagnostic
    assert SECRET_SENTINEL not in response.text
    assert all(secret not in response.text for secret in ("vps.example", "deploy-user"))


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
        async def create(self, _request):
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
        async def create(self, _request):
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
    async def discovery(_request, *, path_checks=None):
        return deployment_discovery()

    manager = DeploymentPlanManager()
    monkeypatch.setattr(main, "discover_environment", discovery)
    monkeypatch.setattr(main, "deployment_plans", manager)
    monkeypatch.setattr(
        main.extensions_store,
        "get_target",
        lambda _target_id: ExtensionTarget(
            **target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA",
        ),
    )
    response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/deploy/plan", json=request_payload(),
    )

    assert response.status_code == 200
    plan = response.json()["plan"]
    internal_plan = manager.plans[plan["id"]]
    assert {key: internal_plan[key] for key in ("project_id", "strategy", "deployment_mode")} == {
        "project_id": "chatgpt2api", "strategy": "isolated", "deployment_mode": "compose",
    }


def test_plan_and_deploy_routes_preserve_new_service_port_without_remote_execution(monkeypatch):
    client, manager, _current_target, discovered_target_ports, leased_requests = route_plan_harness(monkeypatch)
    submitted_target, plan = create_route_plan(client)
    internal_plan = manager.plans[plan["id"]]

    assert discovered_target_ports == [33010, 33010]
    assert internal_plan["service_port"] == 33011
    assert internal_plan["image"] == PINNED_IMAGE

    deploy_response = client.post(
        "/api/extensions/deploy",
        json=route_deploy_payload(submitted_target, plan),
    )

    assert deploy_response.status_code == 200
    assert deploy_response.json() == {"task_id": "lease-only-no-remote-task"}
    assert len(leased_requests) == 1
    leased_request, leased_plan = leased_requests[0]
    assert leased_request.target.chatgpt2api_port == 33010
    assert leased_plan["service_port"] == 33011
    assert plan["id"] in manager.plans


@pytest.mark.parametrize(
    ("override", "diagnostic_code"),
    [
        ({"service_port": 33012}, "deployment_plan_service_port_changed"),
        ({"image": "ghcr.io/yukkcat/chatgpt2api@sha256:" + ("b" * 64)}, "deployment_plan_image_changed"),
    ],
)
def test_deploy_route_rejects_field_tamper_without_task_or_plan_consumption(
    monkeypatch, override, diagnostic_code,
):
    client, manager, _current_target, _discovered_ports, leased_requests = route_plan_harness(monkeypatch)
    submitted_target, plan = create_route_plan(client)

    response = client.post(
        "/api/extensions/deploy",
        json=route_deploy_payload(submitted_target, plan, **override),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error": {
            "deployment_plan_service_port_changed": "服务端口与已确认部署计划不一致，请重新生成安全计划",
            "deployment_plan_image_changed": "容器镜像与已确认部署计划不一致，请重新生成安全计划",
        }[diagnostic_code],
        "diagnostic": {
            "code": diagnostic_code,
            "stage": "plan_confirmation",
            "retry_safe": False,
            "task_created": False,
        },
    }
    assert leased_requests == []
    assert plan["id"] in manager.plans
    assert "_lease_token" not in manager.plans[plan["id"]]
    assert SECRET_SENTINEL not in response.text
    assert str(next(iter(override.values()))) not in response.text


def test_deploy_route_rejects_live_identity_drift_with_structured_safe_reason(monkeypatch):
    client, manager, current_target, _discovered_ports, leased_requests = route_plan_harness(monkeypatch)
    submitted_target, plan = create_route_plan(client)
    changed_host = "changed.example"
    current_target["value"] = current_target["value"].model_copy(update={"host": changed_host})
    submitted_target = {**submitted_target, "host": changed_host}

    response = client.post(
        "/api/extensions/deploy",
        json=route_deploy_payload(submitted_target, plan),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error": "VPS 连接身份与已确认部署计划不一致，请重新生成安全计划",
        "diagnostic": {
            "code": "deployment_plan_identity_changed",
            "stage": "plan_confirmation",
            "retry_safe": False,
            "task_created": False,
        },
    }
    assert leased_requests == []
    assert plan["id"] in manager.plans
    assert "_lease_token" not in manager.plans[plan["id"]]
    assert changed_host not in response.text
    assert SECRET_SENTINEL not in response.text


def test_deploy_route_rejects_submitted_identity_tamper_before_task_creation(monkeypatch):
    client, manager, _current_target, _discovered_ports, leased_requests = route_plan_harness(monkeypatch)
    submitted_target, plan = create_route_plan(client)
    tampered_host = "tampered.example"
    submitted_target = {**submitted_target, "host": tampered_host}

    response = client.post(
        "/api/extensions/deploy",
        json=route_deploy_payload(submitted_target, plan),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "error": "VPS 连接身份与已确认部署计划不一致，请重新生成安全计划",
        "diagnostic": {
            "code": "deployment_plan_identity_changed",
            "stage": "plan_confirmation",
            "retry_safe": False,
            "task_created": False,
        },
    }
    assert leased_requests == []
    assert plan["id"] in manager.plans
    assert "_lease_token" not in manager.plans[plan["id"]]
    assert tampered_host not in response.text
    assert SECRET_SENTINEL not in response.text


def test_plan_requires_a_verified_capability_snapshot():
    manager = DeploymentPlanManager()
    target = ExtensionTarget(**target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA")
    discovery = deployment_discovery()
    discovery.pop("privileges")

    with pytest.raises(ValueError):
        manager.create(
            ExtensionPlanRequest(target=target, credential=SSHCredential(password=SECRET_SENTINEL), service_port=33010),
            discovery,
        )


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
    target = ExtensionTarget(**target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA")
    plan_request = ExtensionPlanRequest(target=target, credential=SSHCredential(password=SECRET_SENTINEL), service_port=33010)
    plan = manager.create(plan_request, deployment_discovery())
    deploy_request = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=target,
        credential=SSHCredential(password=SECRET_SENTINEL),
        confirmed_plan_id=plan["id"],
    )

    with pytest.raises(ValueError) as excinfo:
        manager.take(plan["id"], deploy_request.model_copy(update=changes))
    assert SECRET_SENTINEL not in str(excinfo.value)
    assert plan["id"] in manager.plans
    assert manager.take(plan["id"], deploy_request)["id"] == plan["id"]


def _port_bound_plan(service_port=33011):
    manager = DeploymentPlanManager()
    live_target = ExtensionTarget(**target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA")
    submitted_target = live_target.model_copy(update={"chatgpt2api_port": service_port})
    credential = SSHCredential(password=SECRET_SENTINEL)
    plan = manager.create(
        ExtensionPlanRequest(
            target=submitted_target,
            credential=credential,
            service_port=service_port,
        ),
        deployment_discovery(),
    )
    request = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=submitted_target,
        credential=credential,
        trust_host_key=True,
        expected_host_key=live_target.host_key,
        service_port=service_port,
        confirmed_plan_id=plan["id"],
    )
    return manager, live_target, submitted_target, plan, request


def test_plan_take_allows_new_service_port_when_live_ssh_identity_is_unchanged(monkeypatch):
    from extensions import orchestrator

    manager, live_target, _submitted_target, plan, request = _port_bound_plan()
    internal_plan = manager.plans[plan["id"]]
    assert live_target.chatgpt2api_port == 33010
    assert internal_plan["service_port"] == request.target.chatgpt2api_port == 33011
    monkeypatch.setattr(orchestrator.extensions_store, "get_target", lambda _target_id: live_target)

    assert manager.take(plan["id"], request)["id"] == plan["id"]


def test_plan_take_rejects_tampered_submitted_service_port(monkeypatch):
    from extensions import orchestrator

    manager, live_target, _submitted_target, plan, request = _port_bound_plan()
    monkeypatch.setattr(orchestrator.extensions_store, "get_target", lambda _target_id: live_target)
    tampered_request = request.model_copy(update={"service_port": 33012})

    with pytest.raises(ValueError):
        manager.take(plan["id"], tampered_request)

    assert plan["id"] in manager.plans
    assert manager.take(plan["id"], request)["id"] == plan["id"]


def test_plan_take_rejects_live_ssh_identity_drift_even_with_bound_request_port(monkeypatch):
    from extensions import orchestrator

    manager, live_target, _submitted_target, plan, request = _port_bound_plan()
    current = {"target": live_target.model_copy(update={"host": "changed.example"})}
    monkeypatch.setattr(orchestrator.extensions_store, "get_target", lambda _target_id: current["target"])

    with pytest.raises(ValueError):
        manager.take(plan["id"], request)

    assert plan["id"] in manager.plans
    current["target"] = live_target
    assert manager.take(plan["id"], request)["id"] == plan["id"]


def test_target_auth_and_elevation_drift_leave_plan_available():
    discovery = deployment_discovery()
    base_target = ExtensionTarget(**target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA")
    base_credential = SSHCredential(password=SECRET_SENTINEL)

    def drifted_request(kind, plan_id):
        target = base_target
        credential = base_credential
        if kind == "host":
            target = target.model_copy(update={"host": "changed.example"})
        elif kind == "port":
            target = target.model_copy(update={"port": 2222})
        elif kind == "username":
            target = target.model_copy(update={"username": "another-user"})
        elif kind == "fingerprint":
            target = target.model_copy(update={"host_key": "SHA256:BBBBBBBBBBBBBBBBBBBB"})
        elif kind == "auth_kind":
            credential = SSHCredential(private_key="test-private-key")
        elif kind == "elevation":
            credential = SSHCredential(password=SECRET_SENTINEL, elevation="passwordless_sudo")
        return ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=target,
            credential=credential,
            confirmed_plan_id=plan_id,
        )

    for kind in ("host", "port", "username", "fingerprint", "auth_kind", "elevation"):
        manager = DeploymentPlanManager()
        plan = manager.create(
            ExtensionPlanRequest(
                target=base_target,
                credential=base_credential,
                service_port=33010,
            ),
            discovery,
        )
        valid = ExtensionDeployRequest(
            deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
            target=base_target,
            credential=base_credential,
            confirmed_plan_id=plan["id"],
        )

        with pytest.raises(ValueError):
            manager.take(plan["id"], drifted_request(kind, plan["id"]))

        assert plan["id"] in manager.plans
        assert manager.take(plan["id"], valid)["id"] == plan["id"]


@pytest.mark.parametrize("drift_kind", ["identity", "service_port", "image"])
def test_plan_confirmation_drift_creates_no_connection_task_or_persistent_record(
    tmp_path, monkeypatch, drift_kind,
):
    from extensions import orchestrator

    target = ExtensionTarget(**target_payload(), host_key="SHA256:AAAAAAAAAAAAAAAAAAAA")
    credential = SSHCredential(password=SECRET_SENTINEL)
    manager = DeploymentPlanManager()
    plan = manager.create(
        ExtensionPlanRequest(target=target, credential=credential, service_port=33010),
        deployment_discovery(),
    )
    connected = []

    async def forbidden_connect(_request):
        connected.append(True)
        raise AssertionError("connection must not run")

    monkeypatch.setattr(orchestrator, "deployment_plans", manager)
    monkeypatch.setattr(orchestrator, "_connect", forbidden_connect)
    tasks_path = tmp_path / "extension_tasks.json"
    tasks = ExtensionTaskManager(store_path=tasks_path)
    valid = ExtensionDeployRequest(
        deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
        target=target,
        credential=credential,
        confirmed_plan_id=plan["id"],
    )
    if drift_kind == "identity":
        drifted = valid.model_copy(update={
            "target": target.model_copy(update={"username": "changed-user"}),
        })
    elif drift_kind == "service_port":
        drifted = valid.model_copy(update={"service_port": 33011})
    else:
        drifted = valid.model_copy(update={"image": PINNED_IMAGE})

    async def run_drift():
        with pytest.raises(ValueError):
            await tasks.create(drifted)

    asyncio.run(run_drift())

    assert plan["id"] in manager.plans
    assert tasks.tasks == {}
    assert tasks.runners == {}
    assert connected == []
    assert not tasks_path.exists()


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
            await task_manager.create(ExtensionDeployRequest(
                deployment_attempt_id=DEPLOYMENT_ATTEMPT_ID,
                project_id="grok2api", target=target, credential=SSHCredential(password="test-only"), confirmed_plan_id="missing",
            ))
        assert task_manager.tasks == {}
        assert task_manager.runners == {}

    asyncio.run(run())
    assert connected == []
    with pytest.raises(ValueError):
        validate_deployment_capability("grok2api", "isolated", "compose")
