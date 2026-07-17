# GenBox Multi-Agent Engineering Strategy

## Purpose

Use multiple agents to improve safety and throughput without allowing concurrent
writers, stale planning metadata, or model assumptions to damage verified work.
`docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and
`docs/STATUS.md` remain the sources of truth.

## Stable Model Routing

The currently configured GSD profile uses these known tiers:

| Tier | Model | GenBox responsibilities |
|---|---|---|
| Heavy | `gpt-5.5` | orchestration, architecture, SSH/network security, release decisions, final review |
| Standard | `gpt-5.4` | FastAPI implementation, static UI work, unit/route tests, focused debugging |
| Light | `gpt-5.4-mini` | file inventory, test matrices, documentation checks, syntax and packaging checklists |

`gpt-5.3-codex-spark` may replace the light tier for mechanical code tasks after
a small regression benchmark. `codex-auto-review` is a secondary code-review
signal, never the only security or release approver. `gpt-image-1.5` and
`gpt-image-2` are reserved for bitmap assets and do not participate in code,
security, or planning decisions.

The aliases `gpt-5.6-terra`, `gpt-5.6-luna`, and `gpt-5.6-sol` are treated as
unclassified candidates. Their names are not evidence of capability. Before
assigning them a production role, run the same sanitized tasks through each:

1. Phase-plan critique with scope-fence detection.
2. Security review containing planted SSH, SSRF, and secret-handling defects.
3. FastAPI implementation plus tests.
4. Release-diff review for false completion and secret leakage.

Score correctness, missed P1 issues, invented facts, test quality, latency, and
cost. Promote a candidate only when it beats the current tier on two repeated
runs without weakening safety.

## GenBox Roles

### Orchestrator — Heavy

- Reads authoritative project documents and owns the active objective.
- Splits work into one narrow Loop Engineering slice.
- Is the only role allowed to accept review findings, change scope, stage,
  commit, access external systems, or request VPS authorization.

### Backend/Integration Builder — Standard

- Implements FastAPI, storage, adapters, and fixed SSH/network command plans.
- Writes focused tests with the change.
- Never approves its own work and never touches a live VPS.

### Frontend Builder — Standard

- Maintains the static UI, readiness states, progress, and recovery messaging.
- Must keep UI claims aligned with backend capability.
- Does not change protocol or security decisions without orchestration review.

### Security Reviewer — Heavy

- Read-only by default.
- Reviews authentication ordering, host-key trust, secret lifetime, SSRF,
  destination validation, remote commands, source deletion, and production
  isolation.
- Any P1 returns the task to Build; it cannot be overridden by a passing test.

### Test/Contract Reviewer — Standard or Heavy

- Reviews unit, route, failure, persistence, UI/static, and regression coverage.
- Distinguishes mocked evidence from live isolated-clone evidence.
- Checks that failures identify the exact stage and recovery action.

### Release/Ops Verifier — Light for mechanics, Heavy for approval

- Light model runs deterministic syntax, packaging, checksum, and diff checks.
- Heavy model reviews release claims, licensing, secret scans, rollback, and
  clean-deployment evidence.

## Task Routing by Domain

| Work | Builder | Mandatory reviewer |
|---|---|---|
| SSH, credentials, network routing | `gpt-5.4` | `gpt-5.5` security reviewer |
| FastAPI/storage behavior | `gpt-5.4` | test reviewer; security reviewer if secrets/SSRF involved |
| Static UI/readiness | `gpt-5.4` | contract reviewer |
| Tests/docs/checklists | `gpt-5.4-mini` or Codex Spark candidate | `gpt-5.4` |
| Release/license/production gates | mechanical light tier | `gpt-5.5` final approval |
| Bitmap design assets | `gpt-image-2` | frontend/brand review |

## Collaboration Rules

- Maximum active team: orchestrator plus two read-only reviewers and one builder.
- Only one agent may edit the shared worktree at a time.
- Parallel agents receive non-overlapping, read-only review questions.
- Every handoff states changed files, verification command, known gaps, and next
  action.
- Every non-trivial change follows:
  `Scope -> Build -> Focused tests -> Independent review -> Fix -> Full tests -> Commit`.
- A commit contains one accepted loop and never stages `.planning/STATE.md`,
  runtime storage, credentials, images, logs, or unrelated user changes.

## Smart GSD Policy

GSD is a workflow tool, not a replacement for the GenBox sources of truth.

Use GSD when:

- model-tier configuration or deterministic workflow settings are needed;
- an already aligned phase needs plan review, execution waves, code review,
  security review, validation, or conversational UAT;
- the workflow can run without overwriting user-owned state.

Do not use GSD phase/milestone/pause/resume writers while `.planning/ROADMAP.md`
still describes the historical External Image Sync milestone and
`.planning/STATE.md` contains owner changes. Until those are isolated or
reconciled, use the authoritative `docs/` contracts plus this Loop Engineering
protocol. Generic Codex subagents must be labelled as a workaround; do not claim
that per-agent model overrides were honored unless the runtime exposes typed
agent/model routing.

## External-System Gate

No agent may connect to or mutate a VPS until the orchestrator records:

- explicit user authorization;
- isolated development-clone identity;
- verified host key and ownership boundary;
- separate directory, container, Compose project, volume, port, and credentials;
- rollback limited to GenBox-owned development resources.

Production chatgpt2api remains read-only throughout development.
