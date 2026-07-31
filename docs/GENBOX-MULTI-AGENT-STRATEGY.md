# GenBox Multi-Agent Engineering Strategy

## Purpose

Use role-specialized agents to improve safety and review quality without
allowing concurrent writers, stale planning metadata, model assumptions, or
external automation to damage verified work. `docs/PRODUCT.md`,
`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/STATUS.md` remain the
sources of truth. Files under `.planning/` are historical or tool-local input
when they conflict with those documents.

## First-Principles Task Card

Every non-trivial loop starts with a short task card. This is a reasoning
check, not a new planning system:

1. **User outcome:** what observable user result must become true?
2. **Invariants:** what must remain true even when the operation fails,
   retries, or restarts?
3. **Evidence:** which command, test, or runtime observation can prove it?
4. **Non-goals:** which nearby behavior is explicitly out of scope?

For cross-project Push work, the default invariants are authenticated
receipts, matching SHA-256, idempotent retry, source retention, isolated
resources, and production non-mutation. A passing mock or a plausible UI state
cannot satisfy an isolated-VPS gate by itself.

## Capability Role Cards

Role names describe a review mandate, never a claimed vendor identity. A role
may use public engineering practices associated with a company, but its output
must be grounded in this repository's contracts and evidence. No role may use a
company name as authority, invent a runtime fact, or grant deployment or
publication permission.

- **Orchestrator:** owns the task card, preservation snapshot, scope, evidence
  class, handoffs, and final accept/reject decision. It is the only role that
  stages, commits, or requests external authorization.
- **Receiver/deployment builder:** the single writer for GenBox code, fixed
  plans, UI, and receiver tests. It never edits the sender repository or a live
  VPS.
- **Sender/integration builder:** works only in the isolated chatgpt2api
  repository and owns Push, batch, schedule, receipt, and lease behavior.
- **Security reviewer:** read-only review of credentials, host-key trust,
  SSRF, remote commands, deletion, rollback, and production isolation.
- **Reliability reviewer:** read-only review of restart recovery, idempotency,
  concurrency, leases, bounded retry, and observable progress.
- **UX/contract reviewer:** checks that visible actions, recovery text, API
  contracts, and tests agree and remain understandable to a novice.

Role cards must state allowed files, forbidden actions, required artifacts, and
verification commands. The resolved runtime model is recorded only when the
dispatch system actually exposes that identity; otherwise the collaboration is
generic role collaboration.

## Risk-Triggered Review

Multi-agent review is not a permanent ceremony for every edit. Use this
minimum trigger policy:

| Change surface | Required review |
| --- | --- |
| Copy, styling, isolated UI text | Builder self-check and focused test |
| Local behavior or route contract | One independent test/contract reviewer |
| Credentials, SSH, Push, retries, leases, or cross-project state | Security + reliability + contract reviewers |
| VPS mutation, immutable image update, release, GitHub publication, or upstream PR | All relevant reviewers plus explicit user authorization |

Reviewers inspect a frozen commit or diff and remain read-only. A P1 finding
returns the loop to the writer; passing tests do not override it.

## Mandatory Preservation Gate

Before every non-trivial task, the orchestrator records a sanitized task
snapshot containing:

- current branch and full HEAD commit;
- `git status --short`, tracked/untracked inventory, and diff/stat identity;
- focused or full test baseline appropriate to the task;
- the one active objective and its explicit non-goals;
- owner exclusions that no agent may modify, stage, discard, or commit.

`.planning/STATE.md` is task-scoped and owner-controlled, not a permanent
project-wide exclusion. Do not read or modify it unless the task explicitly
names it and assigns an owner; when assigned, it remains auxiliary recovery
state and cannot override the formal documents. A dirty worktree is not cleaned
automatically. Recovery uses a new corrective commit or `git revert` of a known
agent commit; agents never use reset or checkout to erase owner changes.

Reviewers inspect a fixed commit, fixed diff, or explicit file snapshot. The
builder stops before review starts, the review range stays frozen, all review
results are collected, and only then may the single writer resume fixes.

## Single Active Objective Ledger

Only one primary product slice may be `In Progress`. Its identity comes from
`docs/STATUS.md` and `docs/ROADMAP.md`; a later phase cannot be started merely
to avoid an unresolved acceptance criterion.

Every task reads the minimal capsule: `AGENTS.md`, `docs/STATUS.md`, the current
roadmap phase, and that phase's explicit topic contract. Read decisions only
when architecture/security is touched; read lifecycle only for VPS, release, or
upstream work; read `.planning/STATE.md` only when explicitly assigned.

Each loop records:

1. objective and non-goals;
2. frozen input commit or diff;
3. writer and read-only reviewers;
4. tests and evidence type (mocked, local runtime, isolated VPS, or clean
   GitHub deployment);
5. accepted findings, remaining risks, and the next resume point.

## Configured Target Routing

The GSD configuration expresses the following desired routing:

| Tier | Configured target | GenBox responsibilities |
|---|---|---|
| Heavy | `gpt-5.5` | orchestration, architecture, SSH/network security, release judgment, final review |
| Standard | `gpt-5.4` | FastAPI implementation, static UI work, tests, focused debugging |
| Light | `gpt-5.4-mini` | inventories, test matrices, documentation and deterministic checklists |

This table is a target configuration, not proof of runtime model selection.
At the start of every multi-agent run, inspect the available dispatch schema:

- If dispatch exposes typed `agent_type` and supported reasoning controls,
  typed GSD role routing may be used and the resolved routing must be recorded.
- If dispatch is generic, collaboration is labelled **generic role
  collaboration, opaque model**. Role prompts may be applied, but no result may
  claim that a particular model actually ran.
- If correctness depends on typed dispatch or worktree isolation, fail closed
  instead of silently degrading.

`gpt-image-2` is invoked only through image-generation tooling for bitmap
assets; it is never a code, security, planning, or release agent.
`codex-auto-review` is a secondary signal and never the sole approval source.

## Model Calibration And Fallback

Candidate aliases such as `gpt-5.6-terra`, `gpt-5.6-luna`,
`gpt-5.6-sol`, or a mechanical Codex Spark model are unclassified until they
pass a versioned, sanitized benchmark for a specific role.

Calibration rules:

- baseline and candidate receive identical prompts, files, hidden checks, and
  scope fences;
- run each role benchmark at least three times;
- record model ID, date, runtime, supported reasoning level, latency, and usage
  only when reliable usage data exists;
- security candidates must find 100% of planted P1 SSH, SSRF, secret, deletion,
  and production-isolation defects and propose no unsafe fix;
- planning candidates must identify every scope fence and invent no runtime
  fact;
- builder candidates must pass hidden tests and preserve a minimal diff;
- promotion is per role, never global.

A promoted model is demoted after a missed P1, invented environment fact,
unsafe external action, repeated hidden-test regression, or material quality
loss. Immediate fallback is the configured `gpt-5.5`, `gpt-5.4`, or
`gpt-5.4-mini` target for that role.

## GenBox Roles And Repository Boundaries

### Orchestrator

- Owns the preservation gate, active objective, scope, task state, and evidence
  classification.
- Is the only role that accepts findings, resumes the writer, stages, commits,
  or requests external authorization.
- Technical approval never substitutes for the user's authorization to push,
  tag, publish a Release or image, or mutate VPS resources.

### GenBox Receiver/Deployment Builder

- Is the only writer during its build window.
- Implements GenBox FastAPI, storage, static UI, deployment adapters, and fixed
  SSH/network plans with focused tests.
- Does not implement chatgpt2api sender behavior in this repository and never
  touches a live VPS.

### Future chatgpt2api Sender Builder

- Operates only in the separately identified chatgpt2api repository and an
  isolated worktree/development clone.
- Owns generation Push, batch/schedule state, cursor/lease, receipt persistence,
  and optional cleanup logic when their phases become active.
- Is not dispatched during Phase 3.

### Security Reviewer

- Is read-only and reviews a frozen snapshot.
- Checks authentication ordering, host-key trust, secret lifetime, SSRF,
  destination validation, remote commands, source deletion, and production
  isolation.
- Any P1 returns the task to Build and cannot be overridden by passing tests.

### Transfer Integrity Reviewer

- Reviews the cross-project contract independently of either builder.
- Covers SHA-256 matching, idempotency, authenticated receipts, metadata,
  source retention, cleanup permission, cursor/lease durability, and Push/Pull
  regression.
- Becomes mandatory for Phases 4-6; Phase 3 may consult it only on destination
  contract compatibility.

### Test/Contract Reviewer

- Checks unit, route, UI/static, failure, persistence, and regression coverage.
- Separates mocked evidence from local runtime, isolated VPS, and clean
  redeployment evidence.
- Verifies that UI availability and recovery text match backend behavior.

### Release/Ops Verifier

- Runs deterministic syntax, packaging, checksum, diff, and inventory checks.
- A heavy reviewer separately judges licensing, secrets, rollback, release
  claims, and clean-deployment evidence.
- Neither role may perform an external publication without explicit user
  authorization for that action.

## Safe Collaboration Lifecycle

For one shared worktree, the only allowed concurrency shapes are:

- one active writer and no reviewer reading a changing review range; or
- up to three parallel read-only reviewers inspecting the same frozen snapshot.

The default loop is:

`Preserve -> Scope -> Single-writer build -> Focused tests -> Freeze -> Parallel read-only reviews -> Collect -> Single-writer fix -> Full tests -> Commit`

Every handoff includes changed files, frozen commit/diff, verification commands,
evidence classification, known gaps, owner exclusions, and the next action. A
commit contains one accepted loop and never stages runtime storage, credentials,
media, logs, or unrelated owner changes; `.planning/STATE.md` is staged only
when it is explicitly task-owned and its auxiliary scope is verified.

## Smart GSD Policy

GSD is optional workflow support, not a replacement for GenBox's authoritative
documents or Loop Engineering.

Before invoking any GSD skill:

1. read its complete `SKILL.md` and every required workflow/reference;
2. inspect its dispatch requirements and complete write set;
3. reject it if it may modify `.planning/STATE.md` without explicit task-owner
   authorization, historical `.planning/ROADMAP.md`, unrelated phase
   directories, create unsafe worktrees, auto-commit, or start parallel writers;
4. declare whether execution is typed GSD routing or the generic opaque-model
   workaround;
5. declare allowed artifact paths and whether commits are forbidden.

Currently safe uses include configuration through GSD's merge-aware setter and
read-only review workflows whose write set has been explicitly constrained.
Current unsafe/default-denied uses include milestone/phase/pause/resume writers,
automatic documentation commits, and execute-phase parallel waves without
verified typed dispatch plus explicit worktree isolation.

The project GSD defaults are intentionally conservative:

- parallel execution off;
- planning-document auto-commit off;
- plan checker on;
- execution verifier on;
- source grounding on.

## Separate Completion And Authority Gates

Passing one gate never implies the next:

1. **Local technical gate:** accepted commit, focused/full tests, frozen-diff
   reviews.
2. **Isolated VPS gate:** explicitly identified development clone, verified
   host key and ownership, separate resources, application probe, rollback, and
   production non-mutation evidence.
3. **Sanitization gate:** secret, personal-data, generated-artifact, and Git
   history review.
4. **Personal GitHub clean-deployment gate:** sanitized push followed by a
   deployment built only from that repository and repeated acceptance checks.
5. **Upstream/release gate:** separately authorized PR, merge, tag, Release, or
   image publication.

Model or reviewer approval is technical evidence only. External mutation and
publication always require the applicable user authorization and environment
identity.

## External-System Stop Conditions

No agent may connect to or mutate a VPS until the orchestrator records explicit
authorization, the isolated clone identity, verified host key, separate
directory/container/Compose project/volume/port/credentials, and rollback
limited to owned development resources. Production chatgpt2api remains
read-only. Ambiguous identity, overlapping resources, leaked secrets, changed
production health, or an unbounded rollback stops the task immediately.
