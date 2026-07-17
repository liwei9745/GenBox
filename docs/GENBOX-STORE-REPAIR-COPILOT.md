# GenBox Store And Repair Copilot Contract

This contract defines the future Store and assisted-repair boundary. It does not
change the priority of Phases 3-8 or make an unimplemented app deployable.

## GenBox Store

The Store presents three views:

- **Installed:** registered managed and external instances with honest health
  and support state.
- **Recommended:** apps compatible with the verified local or target environment.
- **All:** the complete catalog, including unavailable entries with clear reasons.

An app manifest describes identity, source, license, risk labels, requirements,
capabilities, and user-facing metadata. A versioned adapter separately owns
discovery, planning, fixed deployment actions, health checks, upgrade, backup,
rollback, uninstall, and repair operations. A manifest never grants execution.

The recommendation engine uses verified environment facts such as operating
system, architecture, memory, storage, container runtime, network constraints,
and existing conflicts. Unknown facts reduce confidence; they are not guessed.
Recommendations explain why an app fits and never bypass adapter capability
checks.

Managed instances may use allowlisted lifecycle and repair actions after
ownership verification. External instances are advisory and read-only unless a
future explicit adoption flow proves ownership, backup, rollback, and isolation.
Every Store item exposes source provenance, license compatibility, maintenance
state, permissions, network exposure, data sensitivity, and operational risk.

## Repair Copilot

Repair follows this ordered chain:

1. Run deterministic checks and safe fallback guidance first.
2. Collect only the minimum required evidence and redact secrets, personal data,
   hosts, paths, commands, and raw logs before model access or persistence.
3. Use a dedicated user-selected diagnostic model configuration, separate from
   application generation settings and credentials.
4. Produce a structured diagnosis: observed facts, confidence, affected owned
   resources, proposed action, risk, rollback, and verification plan.
5. Obtain explicit user authorization for the exact target and action.
6. Execute only adapter-defined, allowlisted repair operations; AI output never
   becomes arbitrary shell.
7. Re-run deterministic health checks and report the verified outcome.
8. Submit sanitized experience for review before it can improve future advice.

Experience records move through `draft`, `reviewed`, `verified`, and
`deprecated`. Promotion requires human review and reproducible evidence.
GenBox never self-trains on raw logs, secrets, prompts, user media, or account
data. AI may not execute arbitrary shell, obtain direct root control, weaken SSH
host verification, or silently retry a mutating repair.

## Delivery Order

Phases 3-8 remain the primary product chain. Store foundations begin only after
those gates permit it. Advisory diagnosis precedes assisted repair; verified
experience reuse and allowlisted repair automation are later phases, not implied
by the initial Store catalog.
