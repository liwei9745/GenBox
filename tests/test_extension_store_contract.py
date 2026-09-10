import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

import main
from extensions.catalog import CATALOG
from extensions.models import (
    EnvironmentFacts,
    EnvironmentProjection,
    ExtensionInstance,
    ExtensionKeyResetRequest,
    ManagedImageUpdatePlanRequest,
    PushSourceGrantDeleteRequest,
    PushSourceProvisionRequest,
    SSHCredential,
)
from extensions.store import (
    get_environment_facts,
    get_environment_projection,
    save_environment_facts,
    save_environment_projection,
    save_target_metadata,
    store_projection,
    target_identity_digest,
)


FACT_PROBE_STATUSES = {
    "os": 0, "arch": 0, "cpu": 0, "memory_mb": 0, "disk_mb": 0,
    "docker": 0, "compose": 0, "python": 0, "uv": 0,
}
FACT_PROBE_OUTPUT_VALIDITY = {key: True for key in FACT_PROBE_STATUSES}
VALID_FACT_ENVIRONMENT = {
    "os": "linux", "arch": "x86_64", "cpu": "8", "memory_mb": "4096",
    "disk_free_mb": "12345", "docker_version": "27.0.0", "compose_version": "2.27.0",
    "python_version": "Python 3.12.0", "uv_version": "uv 0.5.0",
}


def store_instance(*, managed: bool) -> ExtensionInstance:
    return ExtensionInstance(
        id="chatgpt2api-dev" if managed else "external-app",
        target_id="target-a",
        service_port=33010,
        install_dir="/srv/app",
        data_dir="/srv/data",
        image="example.invalid/app@sha256:" + "a" * 64,
        managed=managed,
        ownership="managed" if managed else "compose",
        status="running",
    )


def test_store_projection_is_fail_closed_and_does_not_leak_instance_details():
    projection = store_projection(CATALOG, [store_instance(managed=True), store_instance(managed=False)])
    assert set(projection) == {"installed", "recommended", "all"}
    assert projection["recommended"] == []
    assert next(item for item in projection["installed"] if item["ownership"] == "managed")["actions"] == ["deploy"]
    assert next(item for item in projection["installed"] if item["ownership"] == "external")["actions"] == []
    assert all("container_id" not in item and "install_dir" not in item for item in projection["installed"])
    chatgpt = next(item for item in projection["all"] if item["id"] == "chatgpt2api")
    assert chatgpt["actions"] == ["deploy"]
    planned = [item for item in projection["all"] if item["status"] == "planned"]
    assert planned and all(item["actions"] == [] for item in planned)


def test_complete_matching_projection_recommends_only_registry_action(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    verified = store.verified_environment_projection(
        target,
        {"ok": True},
        {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    assert verified is not None
    save_environment_projection(verified)
    facts = store.verified_environment_facts(
        target, {"ok": True, "environment": VALID_FACT_ENVIRONMENT}, {"evidence_manifest": {
            "complete": True, "fact_probe_complete": True,
            "fact_probe_statuses": FACT_PROBE_STATUSES,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    )
    assert facts is not None
    save_environment_facts(facts)

    projection = store.public_store_projection()
    assert [item["id"] for item in projection["recommended"]] == ["chatgpt2api"]
    item = projection["recommended"][0]
    assert item["confidence"] == "high"
    assert item["reasons"] == [
        "os=linux", "arch=x86_64", "cpu_cores=8", "memory_mb=4096",
        "disk_mb=12345", "docker_version=27.0.0", "compose_version=2.27.0",
        "python_version=Python 3.12.0", "uv_version=uv 0.5.0",
    ]
    assert item["unknown_facts"] == []
    assert item["actions"] == ["deploy"]


def test_projection_missing_or_incomplete_capabilities_never_recommend_high(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    for docker_available, compose_available, evidence_complete in (
        (False, True, True), (True, False, True), (True, True, False),
    ):
        verified = store.verified_environment_projection(
            target,
            {"ok": True},
            {"evidence_manifest": {"complete": True}, "capabilities": {
                "docker_available": docker_available,
                "compose_available": compose_available,
            }},
        ) if evidence_complete else None
        if verified is not None:
            save_environment_projection(verified)
        assert store.public_store_projection()["recommended"] == []


def test_projection_identity_and_freshness_fail_closed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    old_projection = EnvironmentProjection(
        target_id=target.id,
        target_identity_digest=store.target_identity_digest(target),
        observed_at="2020-01-01T00:00:00+00:00",
        docker_available=True, compose_available=True, evidence_complete=True,
        confidence="high",
    )
    store.save_config(store.load_config().model_copy(update={"environment_projections": [old_projection]}))
    assert get_environment_projection(target) is None

    future_projection = old_projection.model_copy(update={"observed_at": "2099-01-01T00:00:00+00:00"})
    store.save_config(store.load_config().model_copy(update={"environment_projections": [future_projection]}))
    assert get_environment_projection(target) is None
    changed = store.upsert_target({**target.model_dump(), "network_url": "https://changed.invalid"})
    assert get_environment_projection(changed) is None
    assert store.public_store_projection()["recommended"] == []


def test_store_projection_write_requires_complete_server_evidence(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    for discovery, public in (
        ({"ok": False}, {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }}),
        ({"ok": True}, {"evidence_manifest": {"complete": False}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }}),
        ({"ok": True}, {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": "yes", "compose_available": True,
        }}),
    ):
        assert store.verified_environment_projection(target, discovery, public) is None
    assert store.load_config().environment_projections == []


def test_complete_discovery_projection_is_fresh_and_high(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    verified = store.verified_environment_projection(
        target,
        {"ok": True},
        {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    assert verified is not None
    save_environment_projection(verified)
    projection = get_environment_projection(target)
    assert projection is not None
    assert projection.confidence == "high"


def test_browser_target_metadata_cannot_inject_environment_projection(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
        "environment_projections": [{"target_id": "store-target"}],
        "docker_available": True,
    })
    assert target.id == "store-target"
    assert store.load_config().environment_projections == []


def test_environment_projection_model_contains_no_remote_metadata_fields():
    fields = set(EnvironmentProjection.model_fields)
    assert fields == {
        "target_id", "target_identity_digest", "observed_at", "docker_available",
        "compose_available", "evidence_complete", "confidence",
    }


def test_environment_facts_rejects_extra_fields_and_preserves_unknowns():
    facts = EnvironmentFacts(
        target_id="target-a",
        target_identity_digest="a" * 64,
        observed_at="2026-08-22T12:00:00Z",
        os=None,
        arch="x86_64",
        cpu_cores=None,
        memory_mb=4096,
        disk_mb=None,
        docker_version="27.0.0",
        compose_version=None,
        python_version="3.12.0",
        uv_version=None,
    )
    assert facts.os is None
    assert facts.cpu_cores is None
    assert facts.disk_mb is None
    with pytest.raises(ValidationError):
        EnvironmentFacts(
            target_id="target-a",
            target_identity_digest="a" * 64,
            observed_at="2026-08-22T12:00:00Z",
            unexpected="value",
        )


def test_environment_facts_rejects_invalid_types_and_identity_fields():
    base = {
        "target_id": "target-a",
        "target_identity_digest": "a" * 64,
        "observed_at": "2026-08-22T12:00:00Z",
    }
    with pytest.raises(ValidationError):
        EnvironmentFacts(**base, cpu_cores=0)
    with pytest.raises(ValidationError):
        EnvironmentFacts(**base, memory_mb="unknown")
    with pytest.raises(ValidationError):
        EnvironmentFacts(**{**base, "target_id": "   "})
    with pytest.raises(ValidationError):
        EnvironmentFacts(**{**base, "target_identity_digest": "not-a-digest"})
    with pytest.raises(ValidationError):
        EnvironmentFacts(**{**base, "observed_at": "not-a-timestamp"})


def test_environment_facts_observed_at_requires_utc():
    base = {
        "target_id": "target-a",
        "target_identity_digest": "a" * 64,
    }
    assert EnvironmentFacts(**base, observed_at="2026-08-22T12:00:00Z").observed_at.endswith("Z")
    assert EnvironmentFacts(**base, observed_at="2026-08-22T12:00:00+00:00").observed_at.endswith("+00:00")
    for observed_at in (
        "2026-08-22T20:00:00+08:00",
        "2026-08-22T07:00:00-05:00",
        "2026-08-22T12:00:00",
    ):
        with pytest.raises(ValidationError):
            EnvironmentFacts(**base, observed_at=observed_at)


def test_legacy_config_without_environment_facts_still_loads(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    store.EXTENSIONS_FILE.write_text(
        '{"targets": [], "instances": [], "environment_projections": []}',
        encoding="utf-8",
    )
    config = store.load_config()
    assert config.targets == []
    assert config.instances == []
    assert config.environment_projections == []
    assert config.environment_facts == []


def test_environment_facts_load_isolates_bad_records_and_browser_input(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
        "environment_facts": [{"target_id": "facts-target"}],
    })
    valid = {
        "target_id": target.id,
        "target_identity_digest": target_identity_digest(target),
        "observed_at": "2026-08-22T12:00:00Z",
        "os": "linux",
    }
    store.EXTENSIONS_FILE.write_text(
        __import__("json").dumps({"environment_facts": [valid, {"unexpected": True}]}),
        encoding="utf-8",
    )
    config = store.load_config()
    assert len(config.environment_facts) == 1
    assert config.environment_facts[0].os == "linux"


def test_verified_environment_facts_maps_and_normalizes_discovery(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    verified = store.verified_environment_facts(
        target,
        {"ok": True, "environment": {
            "os": " linux ", "arch": "x86_64", "cpu": "8", "memory_mb": 4096,
            "disk_free_mb": 12345, "docker_version": "27", "compose_version": "v2",
            "python_version": "3.12", "uv_version": "0.5",
            "observed_at": "2099-01-01T00:00:00Z",
        }},
        {"evidence_manifest": {
            "complete": True, "fact_probe_complete": True,
            "fact_probe_statuses": FACT_PROBE_STATUSES,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    )
    assert verified is not None
    facts = verified.facts
    assert facts.os == "linux"
    assert facts.arch == "x86_64"
    assert facts.cpu_cores == 8
    assert facts.memory_mb == 4096
    assert facts.disk_mb == 12345
    assert facts.observed_at != "2099-01-01T00:00:00Z"
    save_environment_facts(verified)
    assert get_environment_facts(target) is not None

    unknown = store.verified_environment_facts(
        target,
        {"ok": True, "environment": {
            "os": "", "arch": None, "cpu": 0, "memory_mb": -1,
            "disk_free_mb": "not-a-number", "docker_version": "",
        }},
        {"evidence_manifest": {
            "complete": True, "fact_probe_complete": True,
            "fact_probe_statuses": FACT_PROBE_STATUSES,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    )
    assert unknown is not None
    assert unknown.facts.os is None
    assert unknown.facts.arch is None
    assert unknown.facts.cpu_cores is None
    assert unknown.facts.memory_mb is None
    assert unknown.facts.disk_mb is None
    assert unknown.facts.docker_version is None


def test_environment_facts_require_complete_verified_discovery(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    environment = {"os": "linux"}
    assert store.verified_environment_facts(
        target, {"ok": False, "environment": environment},
        {"evidence_manifest": {"complete": True}},
    ) is None
    assert store.verified_environment_facts(
        target, {"ok": True, "environment": environment},
        {"evidence_manifest": {
            "complete": False, "fact_probe_complete": True,
            "fact_probe_statuses": FACT_PROBE_STATUSES,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    ) is None


def test_environment_facts_identity_and_time_fail_closed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    base = EnvironmentFacts(
        target_id=target.id,
        target_identity_digest=target_identity_digest(target),
        observed_at="2026-08-22T12:00:00Z",
        os="linux",
    )
    for observed_at in ("2099-01-01T00:00:00Z", "2020-01-01T00:00:00Z", "invalid"):
        if observed_at == "invalid":
            store.EXTENSIONS_FILE.write_text(
                __import__("json").dumps({"environment_facts": [{**base.model_dump(), "observed_at": observed_at}]}),
                encoding="utf-8",
            )
        else:
            store.save_config(store.load_config().model_copy(update={
                "environment_facts": [base.model_copy(update={"observed_at": observed_at})],
            }))
        assert get_environment_facts(target) is None
    store.save_config(store.load_config().model_copy(update={"environment_facts": [base]}))
    drifted = target.model_copy(update={"host": "other.example", "identity_version": target.identity_version + 1})
    assert get_environment_facts(drifted) is None


def test_main_store_hook_saves_projection_and_facts(monkeypatch):
    projection_token = object()
    facts_token = object()
    calls = []
    monkeypatch.setattr(main.extensions_store, "verified_environment_projection", lambda *args: projection_token)
    monkeypatch.setattr(main.extensions_store, "verified_environment_facts", lambda *args: facts_token)
    monkeypatch.setattr(main.extensions_store, "save_environment_observation", lambda *values: calls.append(values))
    main._save_store_environment_projection(object(), {}, {})
    assert calls == [(projection_token, facts_token)]


def test_main_store_hook_does_not_save_partial_observation(monkeypatch):
    calls = []
    monkeypatch.setattr(main.extensions_store, "verified_environment_projection", lambda *args: object())
    monkeypatch.setattr(main.extensions_store, "verified_environment_facts", lambda *args: None)
    monkeypatch.setattr(main.extensions_store, "save_environment_observation", lambda *args: calls.append(args))
    main._save_store_environment_projection(object(), {}, {})
    assert calls == []


def test_environment_facts_reject_incomplete_probe_status_without_writing(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    statuses = {**FACT_PROBE_STATUSES, "memory_mb": 1}
    partial = store.verified_environment_facts(
        target, {"ok": True, "environment": {"os": "linux"}},
        {"evidence_manifest": {
            "complete": True, "fact_probe_complete": False,
            "fact_probe_statuses": statuses,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    )
    assert partial is not None
    assert partial.facts.os == "linux"
    assert partial.facts.memory_mb is None
    assert store.load_config().environment_facts == []


@pytest.mark.parametrize("field, value", [
    ("os", ""),
    ("arch", "unknown"),
    ("docker_version", "\n"),
    ("compose_version", "not-a-version"),
    ("compose_version", None),
    ("python_version", "unavailable"),
    ("uv_version", ""),
    ("cpu", "0"),
    ("memory_mb", "not-a-number"),
    ("disk_free_mb", -1),
])
def test_environment_facts_rejects_empty_or_invalid_probe_output(
    tmp_path, monkeypatch, field, value,
):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    environment = {**VALID_FACT_ENVIRONMENT, field: value}
    verified = store.verified_environment_facts(
        target, {"ok": True, "environment": environment},
        {"evidence_manifest": {
            "complete": True, "fact_probe_complete": True,
            "fact_probe_statuses": FACT_PROBE_STATUSES,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    )
    assert verified is not None
    assert getattr(verified.facts, {
        "os": "os", "arch": "arch", "docker_version": "docker_version",
        "compose_version": "compose_version", "python_version": "python_version",
        "uv_version": "uv_version", "cpu": "cpu_cores", "memory_mb": "memory_mb",
        "disk_free_mb": "disk_mb",
    }[field]) is None
    assert store.load_config().environment_facts == []


def test_environment_facts_rejects_failed_probe_status(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    statuses = {**FACT_PROBE_STATUSES, "docker": 1}
    verified = store.verified_environment_facts(
        target, {"ok": True, "environment": VALID_FACT_ENVIRONMENT},
        {"evidence_manifest": {
            "complete": True, "fact_probe_complete": False,
            "fact_probe_statuses": statuses,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    )
    assert verified is not None
    assert verified.facts.docker_version is None
    assert store.load_config().environment_facts == []


def test_atomic_environment_observation_keeps_both_records_on_save_failure(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    projection = store.verified_environment_projection(
        target, {"ok": True}, {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    facts = store.verified_environment_facts(
        target, {"ok": True, "environment": VALID_FACT_ENVIRONMENT}, {"evidence_manifest": {
            "complete": True, "fact_probe_complete": True,
            "fact_probe_statuses": FACT_PROBE_STATUSES,
            "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
        }},
    )
    assert projection is not None and facts is not None
    before = store.load_config()
    monkeypatch.setattr(store, "save_config", lambda _config: (_ for _ in ()).throw(OSError("write failed")))
    with pytest.raises(OSError):
        store.save_environment_observation(projection, facts)
    assert store.load_config().model_dump() == before.model_dump()


def test_environment_facts_save_rejects_unsaved_and_stale_targets(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "facts-target", "name": "Facts target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    discovery = {"ok": True, "environment": {}}
    public = {"evidence_manifest": {
        "complete": True, "fact_probe_complete": True,
        "fact_probe_statuses": FACT_PROBE_STATUSES,
        "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
    }}
    unsaved = target.model_copy(update={"id": "not-saved", "identity_version": 1})
    unsaved_token = store.verified_environment_facts(
        unsaved, {"ok": True, "environment": VALID_FACT_ENVIRONMENT}, public,
    )
    assert unsaved_token is None

    stale_token = store.verified_environment_facts(target, {
        "ok": True, "environment": VALID_FACT_ENVIRONMENT,
    }, public)
    assert stale_token is not None
    changed = store.upsert_target({**target.model_dump(), "host": "changed.example"})
    assert changed.id == target.id
    with pytest.raises(ValueError, match="saved_target_identity_required"):
        store.save_environment_facts(stale_token)


def test_store_route_has_stable_views_and_no_sensitive_fields(monkeypatch):
    monkeypatch.setattr(main.extensions_store, "public_store_projection", lambda: store_projection(CATALOG, []))
    response = TestClient(main.app, base_url="http://testserver").get("/api/extensions/store")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"installed", "recommended", "all"}
    required = {"id", "manifest_version", "repository", "provenance", "license", "permissions", "network_exposure", "data_sensitivity", "operational_risk", "actions"}
    assert all(required <= item.keys() for item in body["all"])
    assert all(secret not in response.text for secret in ("container_id", "install_dir", "data_dir", "private_key", "password"))


def test_discovery_and_store_routes_expose_partial_facts_without_actions(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    fingerprint = "SHA256:" + "A" * 43
    target = store.upsert_target({
        "id": "unknown-route-target", "name": "Unknown target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
        "host_key_algorithm": "ssh-ed25519", "host_key": fingerprint,
    })
    statuses = {key: 0 for key in FACT_PROBE_STATUSES}
    validity = {key: True for key in FACT_PROBE_STATUSES}
    validity.update({
        "os": False, "cpu": False, "memory_mb": False, "disk_mb": False,
        "docker": False, "compose": False, "python": False, "uv": False,
    })
    incomplete_discovery = {
        "ok": True,
        "host_key_algorithm": "ssh-ed25519",
        "host_key": fingerprint,
        "privileges": {"can_deploy": False, "can_admin": False},
        "environment": {
            "os": None, "arch": "x86_64", "cpu": None, "memory_mb": None,
            "disk_free_mb": None, "docker_version": None, "compose_version": None,
            "python_version": None, "uv_version": None, "listening_ports": [],
            "tcp_listeners": [],
            "listening_ports_probe": {"status": 0, "complete": True, "payload_present": True},
            "fact_probe_statuses": statuses,
            "fact_probe_output_validity": validity,
            "fact_probe_complete": False,
        },
        "instances": [],
        "deployment_modes": [{"id": "compose", "available": None, "recommended": False}],
    }

    async def fake_intent(_body):
        return object()

    async def fake_discovery(_body, *, approved_plan):
        return incomplete_discovery

    monkeypatch.setattr(main, "_validate_read_only_discovery_intent", fake_intent)
    monkeypatch.setattr(main, "discover_environment", fake_discovery)
    body = {
        "target": target.model_dump(),
        "credential": {"password": "session-only"},
    }
    discovery_response = TestClient(main.app, base_url="http://testserver").post(
        "/api/extensions/discover", json=body,
    )
    assert discovery_response.status_code == 200
    discovery_public = discovery_response.json()
    assert discovery_public["environment"] == {
        "os": None, "arch": "x86_64", "cpu_cores": None, "memory_mb": None,
        "disk_mb": None, "docker_version": None, "compose_version": None,
        "python_version": None, "uv_version": None,
    }
    assert set(discovery_public["unknown_facts"]) == {
        "os", "cpu_cores", "memory_mb", "disk_mb", "docker_version",
        "compose_version", "python_version", "uv_version",
    }
    assert discovery_public["capabilities"]["docker_available"] is None
    assert discovery_public["capabilities"]["compose_available"] is None

    store_response = TestClient(main.app, base_url="http://testserver").get(
        "/api/extensions/store",
    )
    assert store_response.status_code == 200
    store_public = store_response.json()
    assert set(store_public) == {"installed", "recommended", "all"}
    recommended = next(item for item in store_public["recommended"] if item["id"] == "chatgpt2api")
    assert recommended["confidence"] == "unknown"
    assert recommended["actions"] == []
    assert set(recommended["unknown_facts"]) == {
        "os", "cpu_cores", "memory_mb", "disk_mb", "docker_version",
        "compose_version", "python_version", "uv_version",
    }
    assert all(item["actions"] == [] for item in store_public["all"] if item["status"] != "available")


def test_store_ui_consumes_api_actions_without_planned_rows():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    source = (root / "static" / "js" / "extensions.js").read_text(encoding="utf-8")
    assert 'id="extStore"' in html
    assert "data-store-view=\"installed\"" in html
    assert "data-store-view=\"recommended\"" in html
    assert "data-store-view=\"all\"" in html
    assert "/api/extensions/store" in source
    assert "Array.isArray(item.actions)" in source
    store_render = source.split("function renderStoreItem", 1)[1].split("window.extensionStoreView", 1)[0]
    assert "extPlannedRows" not in store_render


def _fresh_projection(
    target,
    *,
    confidence="high",
    docker_available=True,
    compose_available=True,
    evidence_complete=True,
) -> EnvironmentProjection:
    return EnvironmentProjection(
        target_id=target.id,
        target_identity_digest=target_identity_digest(target),
        observed_at=datetime.now(timezone.utc).isoformat(),
        docker_available=docker_available,
        compose_available=compose_available,
        evidence_complete=evidence_complete,
        confidence=confidence,
    )


def _fresh_facts(target, **overrides) -> EnvironmentFacts:
    values = {
        "target_id": target.id,
        "target_identity_digest": target_identity_digest(target),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "os": "linux",
        "arch": "x86_64",
        "cpu_cores": 8,
        "memory_mb": 4096,
        "disk_mb": 12345,
        "docker_version": "27.0.0",
        "compose_version": "2.27.0",
        "python_version": "3.12.0",
        "uv_version": "0.5.0",
    }
    return EnvironmentFacts(**{**values, **overrides})


def test_store_contract_response_hierarchy_and_stable_all_items():
    projection = store_projection(CATALOG, [], environment_projection=None)
    assert set(projection) == {"installed", "recommended", "all"}
    assert isinstance(projection["installed"], list)
    assert isinstance(projection["recommended"], list)
    assert isinstance(projection["all"], list)
    assert projection["all"]
    manifest_keys = {
        "id", "name", "repository", "category", "status", "manifest_version",
        "license", "provenance", "permissions", "network_exposure",
        "data_sensitivity", "operational_risk", "adapter_ref",
    }
    for item in projection["all"]:
        assert isinstance(item, dict)
        assert isinstance(item.get("id"), str) and item["id"]
        assert manifest_keys <= item.keys()
        assert isinstance(item["actions"], list)


def test_store_contract_never_exposes_sensitive_field_keys():
    projection = store_projection(
        CATALOG,
        [store_instance(managed=True), store_instance(managed=False)],
        environment_projection=None,
    )
    sensitive = {
        "host", "host_key", "container_id", "container_name", "install_dir",
        "data_dir", "image", "compose_project", "service_port", "api_url",
        "console_url", "credentials", "password", "private_key", "passphrase",
        "token", "network_url", "identity_version",
    }
    for view in ("installed", "recommended", "all"):
        for item in projection[view]:
            assert not (sensitive & item.keys()), (view, item)


def test_store_contract_installed_carries_manifest_metadata_and_ownership():
    projection = store_projection(CATALOG, [store_instance(managed=True)])
    item = projection["installed"][0]
    assert item["instance_id"] == "chatgpt2api-dev"
    assert item["instance_status"] == "running"
    assert item["ownership"] == "managed"
    assert item["id"] == "chatgpt2api"
    assert item["repository"] == "yukkcat/chatgpt2api"
    assert item["license"] == "unknown"
    assert item["actions"] == ["deploy"]


def test_store_contract_external_instances_are_read_only():
    projection = store_projection(CATALOG, [store_instance(managed=False)])
    installed = projection["installed"]
    assert len(installed) == 1
    item = installed[0]
    assert item["ownership"] == "external"
    assert item["instance_id"] == "external-app"
    assert isinstance(item["instance_status"], str)
    assert item["actions"] == []


def test_store_contract_recommended_high_medium_unknown_boundaries(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })

    high = _fresh_projection(target, confidence="high")
    store.save_config(store.load_config().model_copy(update={
        "environment_projections": [high],
        "environment_facts": [_fresh_facts(target)],
    }))
    recommended = store_projection(
        CATALOG, [], environment_projection=high, environment_facts=_fresh_facts(target)
    )["recommended"]
    assert [item["id"] for item in recommended] == ["chatgpt2api"]
    assert recommended[0]["confidence"] == "high"
    assert recommended[0]["actions"] == ["deploy"]

    for confidence in ("medium", "unknown"):
        assert store_projection(
            CATALOG, [], environment_projection=_fresh_projection(target, confidence=confidence)
        )["recommended"] == []

    assert store_projection(
        CATALOG, [], environment_projection=_fresh_projection(target, compose_available=False)
    )["recommended"] == []
    assert store_projection(
        CATALOG, [], environment_projection=_fresh_projection(target, evidence_complete=False)
    )["recommended"] == []


def test_store_contract_identity_mismatch_fail_closed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    verified = store.verified_environment_projection(
        target,
        {"ok": True},
        {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    assert verified is not None
    save_environment_projection(verified)
    store.save_config(store.load_config().model_copy(update={
        "environment_facts": [_fresh_facts(target)],
    }))
    assert store.public_store_projection()["recommended"] != []

    drifted = store.upsert_target({
        **target.model_dump(),
        "host": "drifted.example",
        "identity_version": int(target.identity_version) + 1,
        "host_key": "drifted",
    })
    assert store.get_environment_projection(drifted) is None
    assert store.public_store_projection()["recommended"] == []


def test_store_contract_actions_derive_only_from_capability():
    from extensions.capabilities import project_store_actions

    for item in CATALOG:
        if item["status"] == "available" and item["repository"] == "yukkcat/chatgpt2api":
            assert project_store_actions(item) == ["deploy"]
        else:
            assert project_store_actions(item) == []
    assert project_store_actions({"id": "fake", "repository": "unregistered/invalid", "status": "available"}) == []
    assert project_store_actions({}) == []
    assert project_store_actions("junk") == []
    assert project_store_actions(None) == []


def test_store_contract_reasons_use_current_facts_without_inventing_values():
    from extensions import store

    facts = EnvironmentFacts(
        target_id="target-a", target_identity_digest="a" * 64,
        observed_at=datetime.now(timezone.utc).isoformat(), os="linux", arch="x86_64",
        cpu_cores=8, memory_mb=4096, disk_mb=12345, docker_version="27.0.0",
        compose_version="2.27.0", python_version="3.12.0", uv_version="0.5.0",
    )
    reasons, unknown = store._environment_fact_reasons(facts)
    assert reasons == [
        "os=linux", "arch=x86_64", "cpu_cores=8", "memory_mb=4096",
        "disk_mb=12345", "docker_version=27.0.0", "compose_version=2.27.0",
        "python_version=3.12.0", "uv_version=0.5.0",
    ]
    assert unknown == []

    partial = facts.model_copy(update={
        "os": None, "memory_mb": None, "compose_version": None,
        "python_version": None, "uv_version": None,
    })
    reasons, unknown = store._environment_fact_reasons(partial)
    assert "os=未观测" in reasons
    assert "memory_mb=未观测" in reasons
    assert "compose_version=未观测" in reasons
    assert "python_version=未观测" in reasons
    assert "uv_version=未观测" in reasons
    assert unknown == ["os", "memory_mb", "compose_version", "python_version", "uv_version"]
    assert store._environment_facts_complete(partial) is False


def test_store_contract_partial_facts_do_not_recommend_or_satisfy_requirements(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    partial = _fresh_facts(target, memory_mb=None, disk_mb=None)
    projection = _fresh_projection(target)
    result = store_projection(
        CATALOG, [], environment_projection=projection, environment_facts=partial,
    )
    assert [item["id"] for item in result["recommended"]] == ["chatgpt2api"]
    item = result["recommended"][0]
    assert item["confidence"] == "unknown"
    assert item["actions"] == []
    assert item["unknown_facts"] == ["memory_mb", "disk_mb"]


def test_store_contract_missing_expired_or_drifted_facts_fail_closed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    projection = _fresh_projection(target)
    assert store_projection(CATALOG, [], environment_projection=projection)["recommended"] == []
    assert store_projection(
        CATALOG, [], environment_projection=projection,
        environment_facts=_fresh_facts(target, observed_at="2020-01-01T00:00:00Z"),
    )["recommended"] == []
    assert store_projection(
        CATALOG, [], environment_projection=projection,
        environment_facts=_fresh_facts(target, target_identity_digest="b" * 64),
    )["recommended"] == []


def test_store_contract_unverified_projection_never_recommends_with_complete_facts(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    projection = _fresh_projection(target, evidence_complete=False)
    assert store_projection(
        CATALOG, [], environment_projection=projection,
        environment_facts=_fresh_facts(target),
    )["recommended"] == []


def test_store_contract_explicit_projection_must_match_current_saved_target(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    authoritative = _fresh_projection(target)
    store.save_config(store.load_config().model_copy(update={
        "environment_projections": [authoritative],
    }))
    forged = authoritative.model_copy(update={
        "target_id": "other-target", "target_identity_digest": "b" * 64,
    })
    forged_facts = _fresh_facts(target, target_id="other-target", target_identity_digest="b" * 64)
    result = store_projection(
        CATALOG, [], environment_projection=forged, environment_facts=forged_facts,
    )
    assert result["recommended"] == []

    altered = authoritative.model_copy(update={"docker_available": False})
    assert store_projection(
        CATALOG, [], environment_projection=altered, environment_facts=_fresh_facts(target),
    )["recommended"] == []


def test_store_contract_metadata_defaults_are_safe_and_whitelisted():
    item = {
        "id": "missing-metadata",
        "status": "planned",
        "internal_secret": "must-not-appear",
        "install_dir": "/private/path",
    }
    projection = store_projection([item], [])
    public = projection["all"][0]
    assert public["repository"] == ""
    assert public["provenance"] == "unavailable"
    assert public["license"] == "unknown"
    assert public["permissions"] == []
    assert public["network_exposure"] == "unknown"
    assert public["data_sensitivity"] == "unknown"
    assert public["operational_risk"] == "unknown"
    assert public["adapter_ref"] == ""
    assert "internal_secret" not in public
    assert "install_dir" not in public
    assert public["actions"] == []


def test_store_contract_facts_do_not_change_capability_actions(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    projection = EnvironmentProjection(
        target_id=target.id, target_identity_digest=target_identity_digest(target),
        observed_at=datetime.now(timezone.utc).isoformat(), docker_available=True,
        compose_available=True, evidence_complete=True, confidence="high",
    )
    store.save_config(store.load_config().model_copy(update={
        "environment_projections": [projection],
    }))
    no_facts = store_projection(CATALOG, [], environment_projection=projection)
    with_facts = store_projection(
        CATALOG, [], environment_projection=projection,
        environment_facts=EnvironmentFacts(
            target_id=target.id, target_identity_digest=target_identity_digest(target),
            observed_at=datetime.now(timezone.utc).isoformat(), os="linux", arch="x86_64",
            cpu_cores=8, memory_mb=4096, disk_mb=12345, docker_version="27.0.0",
            compose_version="2.27.0", python_version="3.12.0", uv_version="0.5.0",
        ),
    )
    assert [item["actions"] for item in no_facts["all"]] == [
        item["actions"] for item in with_facts["all"]
    ]
    assert with_facts["recommended"][0]["actions"] == ["deploy"]


def test_store_contract_bad_inputs_fail_closed():
    empty = store_projection(None, None)
    assert empty == {"installed": [], "recommended": [], "all": []}

    only_catalog = store_projection(CATALOG, None)
    assert only_catalog["installed"] == []
    assert only_catalog["recommended"] == []
    assert only_catalog["all"]

    junk_instances = store_projection(CATALOG, [{"project": "chatgpt2api", "managed": True}])
    assert junk_instances["installed"] == []

    bad_projection = store_projection(
        CATALOG, [], environment_projection={"confidence": "high", "evidence_complete": True}
    )
    assert bad_projection["recommended"] == []


def test_store_contract_manifest_recommendation_and_facts_cannot_grant_actions(tmp_path, monkeypatch):
    from extensions import capabilities, store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "store-target", "name": "Store target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    projection = _fresh_projection(target)
    store.save_config(store.load_config().model_copy(update={
        "environment_projections": [projection],
    }))
    facts = _fresh_facts(target)
    available = {
        **next(item for item in CATALOG if item["id"] == "chatgpt2api"),
        "actions": ["repair", "upgrade", "deploy"],
        "capabilities": {"deploy": True, "repair": True},
    }
    planned = {
        **next(item for item in CATALOG if item["status"] == "planned"),
        "actions": ["deploy", "repair"],
        "capabilities": {"deploy": True},
    }

    result = store_projection(
        [available, planned], [store_instance(managed=True)],
        environment_projection=projection, environment_facts=facts,
    )
    assert result["recommended"][0]["id"] == "chatgpt2api"
    assert result["recommended"][0]["actions"] == ["deploy"]
    assert next(item for item in result["all"] if item["status"] == "planned")["actions"] == []

    monkeypatch.setattr(capabilities, "DEPLOYMENT_CAPABILITIES", {})
    disabled = store_projection(
        [available, planned], [store_instance(managed=True)],
        environment_projection=projection, environment_facts=facts,
    )
    assert disabled["recommended"][0]["actions"] == []
    assert all(item["actions"] == [] for item in disabled["installed"] + disabled["all"])


def test_store_contract_all_explains_concrete_unavailable_catalog_entries():
    projection = store_projection(CATALOG, [])
    entries = {item["id"]: item for item in projection["all"]}

    planned = entries["grok2api"]
    assert planned["status"] == "planned"
    assert planned["provenance"] == "catalogued_repository"
    assert planned["actions"] == []

    unverified = entries["kiro2api"]
    assert unverified["status"] == "repository_unverified"
    assert unverified["provenance"] == "repository_unverified"
    assert unverified["actions"] == []


def test_external_instances_cannot_reach_managed_route_operations(tmp_path, monkeypatch):
    from extensions import orchestrator

    monkeypatch.setattr(main.extensions_store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target = save_target_metadata({
        "id": "target-a", "name": "Target", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    instance = main.extensions_store.upsert_instance({
        "id": "external-app", "target_id": target.id, "service_port": 33010,
        "install_dir": "/srv/external", "data_dir": "/srv/external/data",
        "image": "registry.example/app@sha256:" + "a" * 64,
        "status": "running", "managed": False, "ownership": "external",
    })
    handle = main.public_instance_handle(target.id, instance.id)

    for guard in (
        lambda: main._managed_push_source_access(handle),
        lambda: main._managed_vault_instance(handle),
        lambda: main._managed_image_update_instance(handle),
    ):
        with pytest.raises(HTTPException) as exc_info:
            guard()
        assert exc_info.value.status_code == 404

    image = "registry.example/app@sha256:" + "b" * 64
    route_calls = (
        lambda: main.extension_push_source_status(handle),
        lambda: main.extension_push_source_create(
            PushSourceProvisionRequest(instance_handle=handle),
        ),
        lambda: main.extension_push_source_rotate(handle, "source-id"),
        lambda: main.extension_push_source_delete(handle, "source-id"),
        lambda: main.extension_push_source_grant_delete(
            handle, "source-id", PushSourceGrantDeleteRequest(enabled=True),
        ),
        lambda: main.extension_managed_image_update_plan(
            ManagedImageUpdatePlanRequest(instance_handle=handle, image=image),
        ),
    )
    for call in route_calls:
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(call())
        assert exc_info.value.status_code == 404

    remote_calls = []

    async def forbidden_connect(*_args, **_kwargs):
        remote_calls.append(True)
        raise AssertionError("external instance reached remote mutation")

    monkeypatch.setattr(orchestrator, "_connect", forbidden_connect)
    reset_request = ExtensionKeyResetRequest(
        target=target,
        credential=SSHCredential(password="session-only"),
        trust_host_key=True,
        expected_host_key_algorithm=target.host_key_algorithm,
        expected_host_key=target.host_key,
        instance_id=handle,
    )
    monkeypatch.setattr(main, "_bind_confirmed_extension_target", lambda body: body)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(main.extension_reset_admin_key(reset_request))
    assert exc_info.value.status_code == 400
    assert remote_calls == []


def test_store_contract_installed_scoped_to_current_store_target(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    target_a = store.save_target_metadata({
        "id": "target-a", "name": "Target A", "host": "safe.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    target_b = store.save_target_metadata({
        "id": "target-b", "name": "Target B", "host": "other.example",
        "username": "deploy-user", "target_role": "production-read-only",
    })
    store.upsert_instance({
        "id": "instance-a", "target_id": target_a.id, "service_port": 33010,
        "install_dir": "/srv/a", "data_dir": "/srv/a/data",
        "image": "registry.example/app@sha256:" + "a" * 64,
        "status": "running", "managed": True, "ownership": "managed",
    })
    store.upsert_instance({
        "id": "instance-b", "target_id": target_b.id, "service_port": 33011,
        "install_dir": "/srv/b", "data_dir": "/srv/b/data",
        "image": "registry.example/app@sha256:" + "b" * 64,
        "status": "running", "managed": True, "ownership": "managed",
    })

    installed_ids = [item["instance_id"] for item in store.public_store_projection()["installed"]]
    assert "instance-a" in installed_ids
    assert "instance-b" not in installed_ids


def test_store_contract_first_isolated_development_is_store_scope(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    first = store.save_target_metadata({
        "id": "target-first", "name": "First", "host": "first.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    second = store.save_target_metadata({
        "id": "target-second", "name": "Second", "host": "second.example",
        "username": "deploy-user", "target_role": "isolated-development",
    })
    store.upsert_instance({
        "id": "instance-first", "target_id": first.id, "service_port": 33010,
        "install_dir": "/srv/first", "data_dir": "/srv/first/data",
        "image": "registry.example/app@sha256:" + "a" * 64,
        "status": "running", "managed": True, "ownership": "managed",
    })
    store.upsert_instance({
        "id": "instance-second", "target_id": second.id, "service_port": 33011,
        "install_dir": "/srv/second", "data_dir": "/srv/second/data",
        "image": "registry.example/app@sha256:" + "b" * 64,
        "status": "running", "managed": True, "ownership": "managed",
    })
    verified = store.verified_environment_projection(
        first,
        {"ok": True},
        {"evidence_manifest": {"complete": True}, "capabilities": {
            "docker_available": True, "compose_available": True,
        }},
    )
    assert verified is not None
    store.save_environment_projection(verified)
    facts = store.verified_environment_facts(
        first, {"ok": True, "environment": VALID_FACT_ENVIRONMENT}, {
            "evidence_manifest": {
                "complete": True, "fact_probe_complete": True,
                "fact_probe_statuses": FACT_PROBE_STATUSES,
                "fact_probe_output_validity": FACT_PROBE_OUTPUT_VALIDITY,
            },
        },
    )
    assert facts is not None
    store.save_environment_facts(facts)

    projection = store.public_store_projection()
    installed_ids = [item["instance_id"] for item in projection["installed"]]
    assert installed_ids == ["instance-first"]
    assert "instance-second" not in installed_ids
    assert [item["id"] for item in projection["recommended"]] == ["chatgpt2api"]
    assert projection["recommended"][0]["confidence"] == "high"


def test_store_contract_no_isolated_target_keeps_legacy_installed(tmp_path, monkeypatch):
    from extensions import store

    monkeypatch.setattr(store, "EXTENSIONS_FILE", tmp_path / "extensions.json")
    store.save_target_metadata({
        "id": "target-b", "name": "Target B", "host": "other.example",
        "username": "deploy-user", "target_role": "production-read-only",
    })
    store.upsert_instance({
        "id": "instance-b", "target_id": "target-b", "service_port": 33011,
        "install_dir": "/srv/b", "data_dir": "/srv/b/data",
        "image": "registry.example/app@sha256:" + "b" * 64,
        "status": "running", "managed": True, "ownership": "managed",
    })

    installed_ids = [item["instance_id"] for item in store.public_store_projection()["installed"]]
    assert "instance-b" in installed_ids
