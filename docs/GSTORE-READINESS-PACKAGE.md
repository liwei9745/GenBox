# G-Store Readiness Package

**Date:** 2026-08-09
**Status:** Design-only preparation. No Phase 9 Store product behavior or new adapter is implemented.

## Manifest Contract (Draft)

Each catalog item should declare a stable `id`, display metadata, repository and immutable artifact references, supported versions, capabilities, required environment facts, license, risk labels, health probes, rollback strategy, and evidence links. A manifest is descriptive input; it cannot grant deployment authority or execute commands.

Required fields:

```text
id, name, version, description, repository, artifact_digest
capabilities[], environment_requirements[], license, risk
adapter_ref, health_contract, rollback_contract, test_contract, evidence_refs[]
```

## Capability Model

Capabilities are explicit, allowlisted verbs such as `deploy`, `start`, `stop`, `restart`, `health_probe`, `read_logs`, `rotate_secret`, and `rollback`. Each capability carries scope, required authorization, side-effect class, and whether it is available in the current environment. A manifest or recommendation never widens backend authority.

## Environment / License / Risk Metadata

Environment metadata covers OS/architecture, Docker/Compose requirements, ports, storage, network mode, resource minimums, private-network needs, and secret sources. License metadata records SPDX identifier, source/artifact obligations, and redistribution notes. Risk metadata records network exposure, credential classes, data sensitivity, destructive actions, rollback quality, and whether isolated verification exists.

## Adapter Contract (Template Only)

An adapter should expose typed plan generation and bounded execution behind server-owned authority:

1. `discover(input)` returns sanitized environment facts.
2. `plan(input)` returns immutable artifact, resources, ports, health checks, and rollback steps.
3. `apply(plan_handle)` executes only a single-use, backend-issued plan.
4. `health(instance_handle)` returns sanitized status.
5. `rollback(instance_handle, plan_handle)` is bounded to adapter-owned resources.
6. `remove(instance_handle)` is separately authorized and never implied by catalog state.

Browser input remains intent-only; raw shell, credentials, host identity, and arbitrary URLs are not adapter parameters.

## Health / Rollback / Testing Requirements

Before an item can move from Planned to deployable, it needs unit and route tests, adapter contract tests, local Docker build/start/health evidence, isolated-environment smoke evidence, rollback proof, secret/data scan, and a clean-deployment reproduction. Failure must preserve state and expose sanitized recovery guidance.

## Dependency Graph

```text
manifest schema
  -> catalog projection
  -> capability/environment/license/risk validation
  -> adapter discovery and immutable plan
  -> single-use authorized apply
  -> health verification
  -> rollback / bounded removal
  -> evidence record and Installed/Recommended/All views
```

The current chatgpt2api entry may remain catalogued and supported by existing code, while all other planned services stay non-deployable until their adapter and evidence contracts are implemented.

## Implementation Order (Future Phase 9)

1. Freeze and version the manifest schema.
2. Add validation and honest capability projections.
3. Introduce adapter interface and test harness.
4. Port the existing chatgpt2api deployment path behind the interface.
5. Add evidence-aware catalog views and lifecycle state.
6. Add rollback and removal authorization flows.
7. Add further adapters only after isolated and clean-deployment gates pass.

This package is preparatory only. It does not change catalog behavior, add adapters, deploy services, or advance the roadmap beyond the current Phase 6/7 gates.
