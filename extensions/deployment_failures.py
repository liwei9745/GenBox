"""Server-controlled deployment failure states safe for persistence and UI display."""

from __future__ import annotations

from dataclasses import dataclass


DEPLOY_FAILED_PHASES = frozenset({"connect", "docker", "prepare", "pull", "start", "verify"})


@dataclass(frozen=True)
class DeploymentFailure:
    failed_phase: str
    error_code: str
    recovery_action: str
    public_message: str


FAILURES = {
    "host_key_confirmation_required": DeploymentFailure(
        "connect", "host_key_confirmation_required", "confirm_host_key",
        "SSH host key confirmation is required before deployment can continue.",
    ),
    "connection_failed": DeploymentFailure(
        "connect", "connection_failed", "check_ssh_connection_and_credentials",
        "The secure SSH connection could not be established.",
    ),
    "docker_unavailable": DeploymentFailure(
        "docker", "docker_unavailable", "fix_docker_access_and_regenerate_plan",
        "Docker is unavailable to the deployment user.",
    ),
    "preparation_failed": DeploymentFailure(
        "prepare", "preparation_failed", "inspect_owned_partial_deployment_and_regenerate_plan",
        "The managed deployment directory could not be prepared safely.",
    ),
    "image_prepare_failed": DeploymentFailure(
        "pull", "image_prepare_failed", "check_image_access_and_regenerate_plan",
        "The approved container image could not be prepared.",
    ),
    "service_start_failed": DeploymentFailure(
        "start", "service_start_failed", "inspect_owned_instance_and_regenerate_plan",
        "The managed service could not be started.",
    ),
    "service_verification_failed": DeploymentFailure(
        "verify", "service_verification_failed", "inspect_owned_instance_and_regenerate_plan",
        "The managed service did not pass its readiness check and was stopped.",
    ),
    "service_verification_stop_unconfirmed": DeploymentFailure(
        "verify", "service_verification_failed", "verify_owned_instance_stopped_before_retry",
        "The managed service failed verification and its stopped state could not be confirmed.",
    ),
    "instance_registration_failed": DeploymentFailure(
        "verify", "instance_registration_failed", "reconcile_owned_instance_registration",
        "The remote service succeeded, but GenBox could not register the managed instance locally.",
    ),
}

DEPLOY_ERROR_CODES = frozenset(failure.error_code for failure in FAILURES.values())
DEPLOY_RECOVERY_ACTIONS = frozenset(failure.recovery_action for failure in FAILURES.values())
VALID_FAILURE_COMBINATIONS = frozenset(
    (failure.failed_phase, failure.error_code, failure.recovery_action)
    for failure in FAILURES.values()
)


def deployment_failure(key: str) -> DeploymentFailure:
    return FAILURES[key]
