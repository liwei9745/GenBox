"""Focused contract coverage for the external L2 discovery-plan gate."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from extensions.read_only_discovery_plan import (
    DiscoveryPlanValidationError,
    validate_read_only_discovery_plan,
)


FINGERPRINT = "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def valid_plan() -> dict:
    return {
        "authorization": {
            "scope": "read-only-discovery",
            "target_role": "isolated-development",
            "host": "safe.example",
            "port": 22,
            "username": "deploy-user",
            "approval_record_id": "approval-20260729-12345678",
            "approved_at": "2026-07-29T12:00:00+00:00",
        },
        "trust": {
            "expected_host": "safe.example",
            "expected_port": 22,
            "expected_algorithm": "ssh-ed25519",
            "expected_fingerprint": FINGERPRINT,
            "observed_host": "safe.example",
            "observed_port": 22,
            "observed_algorithm": "ssh-ed25519",
            "observed_fingerprint": FINGERPRINT,
        },
        "operations": [
            {"id": "identity"},
            {"id": "docker_version"},
            {"id": "compose_version"},
            {"id": "docker_ps"},
            {"id": "compose_ls"},
            {"id": "listening_ports"},
            {"id": "filesystem_summary", "path": "/srv/genbox-dev"},
            {"id": "capacity", "path": "/srv/genbox-dev"},
        ],
    }


def test_valid_plan_is_normalized_without_any_network_activity():
    plan = valid_plan()
    plan["authorization"]["host"] = "SAFE.EXAMPLE."
    plan["trust"]["expected_host"] = "safe.example"
    plan["trust"]["observed_host"] = "safe.example"

    validated = validate_read_only_discovery_plan(plan)

    assert validated.authorization["host"] == "safe.example"
    assert [item["id"] for item in validated.operations] == [
        "identity", "docker_version", "compose_version", "docker_ps",
        "compose_ls", "listening_ports", "filesystem_summary", "capacity",
    ]


@pytest.mark.parametrize(("mutate", "field"), [
    (lambda plan: plan["authorization"].update(scope="deploy"), "authorization.scope"),
    (lambda plan: plan["trust"].update(observed_host="other.example"), "trust.observed_host"),
    (lambda plan: plan["trust"].update(observed_algorithm="ssh-rsa"), "trust.observed_algorithm"),
    (lambda plan: plan["trust"].update(observed_fingerprint="SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"), "trust.observed_fingerprint"),
    (lambda plan: plan["operations"].append({"id": "shell", "command": "cat /etc/shadow"}), "operations[8].id"),
    (lambda plan: plan["operations"].append({"id": "directory_size", "path": "/srv/../etc"}), "operations[8].path"),
    (lambda plan: plan["operations"].append({"id": "directory_size", "path": "/srv/app;restart"}), "operations[8].path"),
    (lambda plan: plan["operations"].append({"id": "container_label", "container": "app;restart", "label": "com.genbox.managed"}), "operations[8].container"),
])
def test_rejects_target_trust_and_operation_drift(mutate, field):
    plan = valid_plan()
    mutate(plan)

    with pytest.raises(DiscoveryPlanValidationError, match=re.escape(field)) as exc_info:
        validate_read_only_discovery_plan(plan)

    assert exc_info.value.field == field
    assert "safe.example" not in str(exc_info.value)
    assert FINGERPRINT not in str(exc_info.value)


def test_script_accepts_valid_json_without_echoing_target_identity():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/validate_discovery_plan.py"],
        cwd=root,
        input=json.dumps(valid_plan()),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "valid": True,
        "scope": "read-only-discovery",
        "target_role": "isolated-development",
        "operations": [
            "identity", "docker_version", "compose_version", "docker_ps",
            "compose_ls", "listening_ports", "filesystem_summary", "capacity",
        ],
    }
    assert "safe.example" not in result.stdout
    assert FINGERPRINT not in result.stdout


def test_script_reports_only_a_field_for_invalid_plan():
    plan = valid_plan()
    plan["trust"]["observed_fingerprint"] = "SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/validate_discovery_plan.py"],
        cwd=root,
        input=json.dumps(plan),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout) == {"valid": False, "field": "trust.observed_fingerprint"}
    assert "BBBB" not in result.stdout
