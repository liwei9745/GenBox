# Phase 4 Loop Engineering Protocol

## Purpose

Run Phase 4 as a sequence of small, evidence-locked loops. Each loop has one
outcome, explicit non-goals, a frozen input, a bounded verification set, and a
single next action. Local Docker evidence is useful for reducing remote
iterations, but it never upgrades itself into VPS or browser evidence.

## Why The Project Is Ready

The repository already provides the required Loop Engineering foundations:

- `docs/GENBOX-MULTI-AGENT-STRATEGY.md` defines the preservation gate, one
  active objective, single-writer discipline, frozen reviews, evidence classes,
  and stop conditions.
- `docs/STATUS.md` and `docs/ROADMAP.md` are the current state and acceptance
  authorities.
- `docs/DEVELOPMENT-LIFECYCLE.md` separates local, isolated-VPS, sanitization,
  clean-deployment, and upstream gates.
- The local Docker preflight has already proved receiver startup, authenticated
  Push, and idempotent retry at commit `3324ce1`.

The missing piece was an explicit P4 loop ledger. This document supplies that
ledger; it does not change the product scope or relax any safety boundary.

## Operating Rules

1. Keep one active P4 loop. Do not start Phase 5 or message-channel delivery to
   bypass an unresolved Phase 4 gate.
2. Freeze the input commit before review or remote work. Reviewers inspect that
   frozen commit only.
3. Use one writer at a time. Security, transfer-integrity, test, and operations
   reviewers are read-only until findings are collected.
4. Classify every result as `MOCKED`, `LOCAL`, `ISOLATED-VPS`, `USER-CONFIRMED`,
   or `CLEAN-DEPLOYMENT`. Never promote a lower class by wording.
5. Stop on failed tests, ambiguous target identity, overlapping resources,
   leaked secrets, production impact, or an unbounded rollback.
6. A loop closes only with a dated result, known gaps, and one named next loop.

## P4 Loop Ledger

### L0 - Preserve And Scope

**Outcome:** record branch, commit, clean/dirty state, test baseline, active
objective, non-goals, and owner exclusions.

**Exit evidence:** sanitized preservation snapshot and a single P4 objective.

**Current state:** complete for the current work session at commit `3324ce1`.

### L1 - Local Docker Receiver Preflight

**Outcome:** build and run the GenBox receiver in an isolated local container.

**Checks:** image identity, production startup requirements, healthcheck,
`/api/setup/status`, authenticated single-image Push, matching SHA-256, and
idempotent retry.

**Non-goals:** no VPS reachability, no browser E2E, no sender implementation
claim, and no production evidence.

**Exit evidence:** local image/config shape and sanitized request/receipt
results recorded in `docs/STATUS.md`.

**Current state:** complete and classified `LOCAL` at commit `3324ce1`.

### L2 - Isolated VPS Read-Only Discovery

**Outcome:** prove that the selected VPS target is an isolated development clone
and produce a no-mutation deployment plan.

**Checks:** verified SSH host key, ownership, source/clone distinction, Docker
and Compose versions, existing containers, mounts, ports, project names,
capacity, health, and rollback scope.

**Non-goals:** no source edits, restart, deployment, enrollment, media cleanup,
or production schedule change.

**Exit evidence:** timestamped, secret-free discovery and explicit clone plan.

**Gate:** requires user authorization for the identified isolated target.

### L3 - VPS Shape Reproduction

**Outcome:** reproduce the L1 image/config/container shape on the isolated VPS.

**Checks:** unique directory, volume, container, Compose project, port,
administrator key, Push source identity, and healthcheck.

**Non-goals:** no production reuse and no sender-side feature work.

**Exit evidence:** isolated-VPS startup and application status evidence plus
production non-mutation re-check.

### L4 - Private Route And Application Probe

**Outcome:** prove that the intended private route reaches the correct GenBox
receiver and that the application-level probe succeeds.

**Checks:** endpoint identity, route reachability, authenticated probe, and
destination persistence without exposing secrets.

**Non-goals:** no public exposure and no arbitrary remote command path.

### L5 - Single-Image Transfer

**Outcome:** push one newly generated image from the isolated sender clone,
retain available metadata, and receive an authenticated receipt.

**Checks:** source identity, SHA-256, metadata, media-library import, source
retention, and production non-mutation.

### L6 - Retry And Failure Boundary

**Outcome:** prove that the same request is idempotent and that an unconfirmed
or failed transfer retains the source.

**Checks:** duplicate retry, authentication failure, invalid image or transport
failure, receipt validation, and cleanup remaining disabled.

### L7 - Evidence Lock And Review

**Outcome:** freeze the accepted commit and evidence, run independent
architecture/security, transfer-integrity, test, and operations reviews, then
update Phase 4 status only if L0-L6 satisfy the acceptance criteria.

**Non-goals:** no batch/scheduler work, cleanup rollout, GitHub publication, or
upstream PR unless a later gate is explicitly opened.

## Handoff Template

Every loop handoff records:

- loop ID and one-sentence outcome;
- frozen input commit and changed files;
- writer and read-only reviewers;
- commands and results, with evidence class;
- accepted findings, remaining risks, and owner exclusions;
- one exact next loop and its entry condition.

## Current Resume Point

L0 and L1 are complete. The next active loop is L2: isolated VPS read-only
discovery. It may begin only after the target is identified as a development
clone, its host-key trust is confirmed, and the user authorizes that bounded
remote work. Production chatgpt2api remains read-only.
