"""Authoritative deployment capabilities for extension projects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeploymentCapability:
    project_id: str
    repository: str
    strategies: frozenset[str]
    deployment_modes: frozenset[str]


DEPLOYMENT_CAPABILITIES: dict[str, DeploymentCapability] = {
    "chatgpt2api": DeploymentCapability(
        project_id="chatgpt2api",
        repository="yukkcat/chatgpt2api",
        strategies=frozenset({"existing", "isolated", "new"}),
        deployment_modes=frozenset({"compose"}),
    ),
}


def validate_deployment_capability(
    project_id: str,
    strategy: str,
    deployment_mode: str,
) -> DeploymentCapability:
    """Return an executable capability or fail closed without sensitive detail."""
    capability = DEPLOYMENT_CAPABILITIES.get(project_id)
    if (
        capability is None
        or strategy not in capability.strategies
        or deployment_mode not in capability.deployment_modes
    ):
        raise ValueError("Unsupported deployment capability")
    return capability


def catalog_item_is_deployable(project_id: str, repository: str) -> bool:
    """Derive catalog availability from the executable registry."""
    capability = DEPLOYMENT_CAPABILITIES.get(project_id)
    return capability is not None and capability.repository == repository


def project_store_actions(item: dict) -> list[str]:
    """Project executable Store actions from the authoritative registry only."""
    if not isinstance(item, dict):
        return []
    project_id = str(item.get("id") or "")
    repository = str(item.get("repository") or "")
    if item.get("status") != "available" or not catalog_item_is_deployable(project_id, repository):
        return []
    try:
        validate_deployment_capability(project_id, "isolated", "compose")
    except ValueError:
        return []
    return ["deploy"]
