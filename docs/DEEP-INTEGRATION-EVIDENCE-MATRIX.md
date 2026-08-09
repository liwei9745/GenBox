# Deep Integration Evidence Matrix

**Date:** 2026-08-09
**Scope:** GenBox receiver plus the separately owned chatgpt2api sender worktree.
**Meaning:** `VERIFIED` is backed by a dated local/CI artifact; `EXTERNAL` requires an authorized isolated or clean-deployment run; `UNVERIFIED` means no claim is made.

## Contract Coverage

| Area | GenBox evidence | chatgpt2api evidence | Current state | Remaining gate |
| --- | --- | --- | --- | --- |
| Source identity and Push key separation | `docs/INTEGRATION.md`, push-route auth tests, managed-source provisioning tests | destination settings and secret-storage tests | VERIFIED locally in both repos | clean deployment confirmation |
| Single-image Push | `tests/test_phase6_loopback_receiver.py`, `tests/test_sync_push_routes.py` | shared Push service and generation-flow tests | VERIFIED locally; isolated retry evidence recorded in `docs/STATUS.md` | clean GitHub deployment |
| Idempotent receipt | receiver imported/already-imported/duplicate-local tests | receipt persistence and retry tests | VERIFIED | clean deployment replay |
| Metadata and source retention | receiver metadata/hash tests; loopback source remains unchanged | sender stores path/hash/receipt and retains source on failure | VERIFIED | external cleanup authorization is separate |
| Manual batch Push | reusable receiver contract | batch, failed-only retry, cancellation, progress tests | VERIFIED locally; isolated Phase 5 evidence recorded | clean deployment |
| Scheduled incremental Push | reusable receiver contract | cursor, overlap, lease, late-arrival and restart tests | VERIFIED locally; isolated Phase 5 evidence recorded | clean deployment |
| Credential vault and UI projection | managed-source registry, vault, masked projection and browser-flow tests | Push key never rendered in ordinary settings responses | VERIFIED locally | human UI acceptance |
| Cleanup safety | receipt SHA-256 and `safe_to_delete_source` contract; intent-only API | cleanup guards, crash recovery, storage-race coverage | VERIFIED as fail-closed local behavior | authorized isolated execution only |

## Evidence Levels

| Evidence | Result | Notes |
| --- | --- | --- |
| GenBox focused receiver/loopback suite | VERIFIED | 28 passing tests per `docs/STATUS.md` on 2026-08-09 |
| GenBox full regression | VERIFIED | 611 passing tests per `docs/STATUS.md` on 2026-08-09 |
| Sender focused/full suites | RECORDED VERIFIED | sender Phase 6/5 records include Windows and clean Linux results; rerun output is tracked separately from this matrix |
| Local Docker/build/smoke | RECORDED VERIFIED | GenBox client build and loopback smoke are documented; no production endpoint was touched |
| Hosted CI | RECORDED VERIFIED / PARTIAL | sender run `31256853882` is recorded; macOS multi-process and Docker integration cases remain external/unverified |
| Isolated VPS | PARTIAL | isolated sender `33010` evidence exists for single, batch, schedule and idempotent retry; cleanup execute and clean redeployment remain blocked |
| Production `33018` | NOT RUN | no SSH, HTTP, restart, deployment, cleanup, or execute marker is authorized or claimed |
| Secrets and personal-data scan | REQUIRED GATE | must cover tracked files, history, artifacts, logs, screenshots and build outputs before any public push |

## This Worktree Verification (2026-08-09)

| Check | Result |
| --- | --- |
| GenBox receiver, route, source, entry-browser and vault focus | `65 passed` |
| chatgpt2api single, batch, schedule, receipt and cleanup focus | `141 passed, 18 skipped, 249 subtests passed` |
| GenBox full regression | `611 passed` |
| chatgpt2api full regression | `168 passed, 18 skipped, 249 subtests passed` |
| GenBox Python/JavaScript syntax and diff checks | passed |
| chatgpt2api Python syntax and diff checks | passed |
| Windows GenBox build and executable loopback smoke | passed; client smoke used an OS-assigned local port |
| Docker image build | passed |
| Docker runtime health smoke | VERIFIED: image started with synthetic `ADMIN_KEY`, random mapped loopback port `32769`, and `/api/setup/status` returned `200`; disposable container removed afterward. Earlier failures were missing-key/port harness conditions. |
| High-signal working-tree secret scan | no credential hit; the only sender match was the intentional `ghp_x...` placeholder in `.env.example` |

## External / Manual Gates

The following are intentionally **not** claimed complete: human UAT; exact host/port/host-key authorization; isolated cleanup execute marker; real cleanup approval; clean deployment from sanitized GitHub sources; upstream release/PR approval; and any production mutation. These remain the unified authorization package for a later human-controlled gate.

## Handoff Rule

Deep integration is code/local/CI ready when the rows above remain `VERIFIED` or `RECORDED VERIFIED`, the worktrees are clean, and only the listed external gates remain. This document does not authorize remote access, cleanup, release, or catalog implementation.
