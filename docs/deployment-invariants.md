# Deployment Safety Contract

**Version:** Phase 4 v3
**Status:** Accepted normative contract; locally implemented and independently
reviewed at `656e4c7`. Isolated VPS/browser evidence remains pending and
**UNVERIFIED**.

This is the normative deployment-safety specification for Phase 4. It does not
claim that a local test or a plan is an isolated-VPS end-to-end result.

## Invariants

| ID | Requirement and protected failure |
|---|---|
| DEP-INV-001 | SSH host-key verification and fixed adapter commands are mandatory. A trusted SSH host identity is the canonical `(algorithm, SHA256:fingerprint)` pair; the browser supplies structured intent, never shell. This prevents target substitution and command injection. |
| DEP-INV-002 | Production sources are read-only. A development deployment uses distinct directory, data, container, Compose project, port, management key, and Push identity. This prevents production mutation and resource overlap. |
| DEP-INV-003 | Docker bindings are a canonical, multiplicity-preserving multiset of `(host_ip, host_port, container_port, protocol)`. Set conversion is forbidden. |
| DEP-INV-004 | Phase 4 TCP listener evidence is a separate complete canonical multiset of `(tcp, host_port)` from reliable `ss`/`netstat` evidence. It neither infers address/container-port exposure nor generalizes to UDP. |
| DEP-INV-005 | Required discovery evidence is complete and fresh for the selected strategy. A successful probe without its required payload rejects before side effects. |
| DEP-INV-006 | Exact identities, multisets, thresholds, conditions, and display-only fields are compared only as specified below; unknown classification rejects. |
| DEP-INV-007 | `isolated-empty` requires an exact read-only proof that the normalized install directory is absent and that its normalized parent is claimable. Existing ownership is not a precondition for an absent directory. |
| DEP-INV-008 | The runner atomically creates the exact reserved directory, then writes its ownership marker. Marker verification is required before rollback, cleanup, or mutation of managed resources. |
| DEP-INV-009 | Plans follow lease, fresh read-only discovery, validation, reservation, CAS consumption, public-task persistence, then runner execution. Every earlier rejection has no remote write. |
| DEP-INV-010 | Raw normalized operational identities exist only in the in-memory `execution_snapshot`. Persisted/public evidence is the restricted `evidence_manifest`; tasks, logs, browser state, and diagnostics never receive raw operational identities. |
| DEP-INV-011 | Clean redeployment requires an immutable repository image digest. A local image ID is allowed only as immediate isolated source-clone evidence, never as clean-redeploy provenance. |
| DEP-INV-012 | Diagnostics use only an allowlist of logical field IDs, stage, reason code, and opaque digest. They exclude secrets, host identities, paths, binding values, image IDs, and command output. |

## Strategy and field matrix

`E` exact identity; `M` canonical multiset; `T` threshold; `C` closed
condition/completeness evidence; `D` display-only or ignored.

| Field | Isolated-empty | Existing | Isolated source-clone |
|---|---|---|---|
| Target ID and SSH host-key algorithm plus SHA-256 fingerprint pair | E | E | E |
| Adapter capability/version and privilege contract | E+C | E+C | E+C |
| TCP listener payload | M+C | C | M+C |
| Docker bindings for discovered instances | M+C | M+C | M+C |
| Requested host TCP port | E and absent from listener M | E | E and absent from listener M |
| Target instance | E, absent | E, present | E, new absent |
| Source instance | D | D | E, present |
| Image identity | immutable repository digest E | discovered E | source digest E; local image ID only for immediate evidence |
| Compose project/service | E target | E | E source and target |
| Operational paths | E in memory only | E in memory only | E in memory only |
| Ownership/managed state | D before creation | E | E source and target after creation |
| Capacity | T+C | D | T+C |
| Health | D | E+C | E+C source |

Canonicalization preserves binding multiplicity; normalizes host IP, port,
protocol, paths, Compose identity, ownership identity, and privilege contract
before comparison. Display strings cannot establish identity. Missing, `null`,
and empty are distinct: a required value must be present, non-null, and valid;
an empty multiset is valid only where the strategy explicitly requires absence.

## Closed path-condition schemas

`path_conditions_version` MUST equal `phase4-v3`. Unknown keys, missing keys,
`null`, false, or a strategy-inapplicable required key reject. Producers must
be fresh read-only discovery or in-memory validation; each negative outcome is
tested at the route boundary.

| Strategy | Required conditions |
|---|---|
| isolated-empty | `target_install_dir_absent`, `target_install_parent_claimable`, `target_data_dir_nonoverlap`, `target_compose_project_nonoverlap`, `target_port_unoccupied` |
| existing | `existing_instance_present`, `existing_instance_identity_matches` |
| isolated source-clone | `source_instance_present`, `source_clone_scope_allowed`, `source_data_path_readable`, `target_install_dir_absent`, `target_install_parent_claimable`, `source_target_paths_nonoverlap`, `target_port_unoccupied`, `clone_capacity_sufficient` |

## Snapshot, state, and evidence

`execution_snapshot` is ephemeral, in-memory comparison/command data. Its
digest binds the plan to fresh discovery. `evidence_manifest` is the only
persistable/public form: contract version, opaque snapshot digest, completeness
outcome, and allowlisted changed-field IDs. It contains no raw identities.

The required order is:

`lease -> fresh read-only discovery -> strategy/schema and snapshot validation -> reservation -> CAS consume -> persist public task -> runner creates exact directory -> runner writes marker -> managed deployment work`.

Failed persistence after CAS releases the reservation and marks the plan
terminal/non-reusable; it does not keep a diagnostic lease. A missing, altered,
or ambiguous marker blocks rollback, cleanup, and managed-resource mutation.

## Gates and deferrals

Implementation must cover schema/parser/manager/HTTP binder-route/task-store
layers, including missing/null/false/unknown/strategy-mismatch cases, binding
multiplicity, listener-payload omission, concurrent exact-directory claims,
marker ordering, and post-CAS persistence failure. Property, state-machine, and
mutation tests are appropriate for canonicalization and side-effect ordering.

Before isolated-VPS work, a fixed-commit independent review MUST start
`APPROVE` or `BLOCK`; it blocks on any pre-side-effect bypass, information leak,
lost binding multiplicity, incomplete listener evidence, or unsafe ownership
mutation. Local evidence remains local evidence.

Phase 4.5 defers generalized UDP/address-aware adapters, persistent
cross-process leases, image-transfer mechanisms, and broader deployment-doc
refactoring. Phase 5 owns batch/scheduling; Phase 6 owns cleanup.
