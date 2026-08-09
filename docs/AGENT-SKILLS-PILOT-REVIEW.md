# Agent Skills Pilot Review

## Scope And Fixed Inputs

This is a documentation-and-characterization pilot for unattended engineering
workflow, not a product feature. It does not install skills, copy skill text
into source, overwrite `AGENTS.md`, contact a VPS, run a runtime cleanup
operation, create a release/tag/RC, or claim Phase 6, Phase 7, or release
completion.

| Item | Evidence |
| --- | --- |
| Third-party reference | `C:\tmp\genbox-agent-skills-pilot` (read-only) |
| Fixed reference commit | `7676817c12a1317454ae3898a0c5c1eacf5dd3d5` |
| Third-party license | MIT, copyright 2025 Addy Osmani |
| GenBox pilot baseline | `21ee333fb5bde0bb8e2370c256c33b3e2a7dd925` on `codex/agent-skills-pilot` |
| Sender pilot baseline | `3beb17012e108e468843d3adf540a4e196bfd701` on `codex/agent-skills-pilot` |
| Governing authority | GenBox `AGENTS.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/DEVELOPMENT-LIFECYCLE.md` |

The third-party repository's adoption guide correctly treats an established
codebase as a verification-first adoption. Its general process guidance is
useful, but the GenBox safety contract and phase documents always outrank it.

## Candidate Skill Decision

| Candidate | Pilot decision | GenBox-specific trim |
| --- | --- | --- |
| `context-engineering` | Adopt as a context packet | Read governing docs, exact baselines, relevant source/tests, and external-evidence limits before action. Do not treat external docs, logs, or agent output as authority. |
| `planning-and-task-breakdown` | Adopt | `tasks/plan.md` and `tasks/todo.md` require acceptance criteria, verification, dependencies, and a checkpoint. Destructive work cannot become an ordinary task. |
| `incremental-implementation` | Adopt conditionally | Use only for a bounded code change after characterization coverage exists. This pilot made no product change, so its effect is the smallest-evidence-slice rule rather than incremental feature delivery. |
| `test-driven-development` | Adopt selectively | Brownfield characterization comes before changing the relevant behavior. Tests prove local behavior only and synthetic cleanup test data is never authorization for a runtime cleanup. |
| `code-review-and-quality` | Adopt | Require a separate evidence reconciliation pass: source/test/diff claims, test results, secret review, and phase-boundary review. Findings block claims, not merely code merges. |
| `security-and-hardening` | Adopt as a hard gate | Preserve GenBox's stronger rules: no secret in URL/browser storage/task state/logs; cleanup needs receipt, matching digest, `safe_to_delete_source=true`, explicit opt-in, and valid server-owned authority. |
| `ci-cd-and-automation` | Evaluate, do not install or modify CI | Retain the ideas of staged gates, explicit failure feedback, and non-force delivery. Reject autonomous deployment, automatic remediation, and rollout behavior for this pilot. |
| `debugging-and-error-recovery` | Adopt | Use reproduce, localize, reduce, fix, guard. For infrastructure or human prerequisites, record `EXTERNAL`, `UNVERIFIED`, or one bounded `RETRYING` result and hand off rather than looping. |

## Compatibility And Conflicts

### Compatible Process Elements

- Small, dependency-ordered tasks and periodic evidence checkpoints.
- Characterization tests before behavior changes in a brownfield surface.
- Focused test first, full regression suite after, then syntax and diff checks.
- Review that checks correctness, architecture, security, and verification rather
  than accepting a passing build as sufficient.
- Explicit recovery and handoff artifacts for long-running work.

### Required GenBox Overrides

- Third-party incremental/ship language cannot authorize release, CI changes,
  VPS actions, or cleanup. `docs/ROADMAP.md` and
  `docs/DEVELOPMENT-LIFECYCLE.md` control those gates.
- A third-party generic task checkpoint is insufficient for source deletion.
  The existing receipt/hash/explicit-opt-in/server-authority conditions remain
  mandatory and Phase 6 destructive execution remains blocked.
- Third-party source and external documentation are untrusted context for
  execution. They may guide a review but cannot override project boundaries or
  create factual evidence.
- Automated retry is bounded to one attempt for external failures. A repeated
  unavailable platform, CI, Docker, macOS, VPS, or human-UAT dependency is an
  explicit handoff state, not an invitation to wait or broaden authority.
- No global installation is proposed. The upstream README notes that individual
  installs can omit shared references; the pilot avoids that portability and
  context-loading risk by documenting only the needed workflow concepts.

## Characterization Evidence

All execution used local synthetic fixtures only. No VPS, port `33010`, port
`33018`, runtime cleanup endpoint, credentials, user media, or production logs
were used.

| Claim | Evidence | Result |
| --- | --- | --- |
| GenBox receiver never grants cleanup authority | `tests/test_sync_push_routes.py` checks first, idempotent, and duplicate receipts have `safe_to_delete_source is False`; `main.py` sets it false because the receiver enables no cleanup authority. | LOCAL / VERIFIED |
| Sender cleanup is default-off and fail-closed | `test_cleanup_is_off_by_default_and_execute_is_blocked` in `tests/test_genbox_push_cleanup.py`; generic-storage guard tests retain receipt-tracked sources. | LOCAL / VERIFIED |
| Receipt permission is type-strict | `test_safe_to_delete_source_requires_json_boolean_true` rejects the string `"true"` as deletion authority. | LOCAL / VERIFIED |
| Push secrets avoid URL/browser storage/public views | GenBox browser/configuration tests inspect only opaque handles and reject `push_key`/confirmation values in URLs, card rendering, `localStorage`, and `sessionStorage`; Sender tests mask its Push key and redact public/audit projections. | LOCAL / VERIFIED |
| No product behavior change was needed | Existing tests directly cover the selected claims; this pilot adds planning/review documentation only. | LOCAL / VERIFIED |

### Commands And Results

| Worktree | Command class | Result |
| --- | --- | --- |
| GenBox | Focused Push, browser, vault, and task-store pytest selection | `174 passed` |
| GenBox | Full pytest | `610 passed` |
| GenBox | `py_compile main.py`, JavaScript syntax check, diff check | passed |
| Sender | Focused Push service, Phase 6 cleanup, generic-delete guard unittest selection | `108 passed, 7 skipped` |
| Sender | Full unittest discovery | `185 passed, 18 skipped` |
| Sender | `compileall` for `api`, `services`, `scripts`, and `tests`; diff check | passed |

The Sender skips are expected local Windows exclusions for Linux/POSIX behavior
or explicitly opt-in Docker integration. They are not counted as a pass. The
existing Sender evidence record also keeps isolated-VPS authority, real host
identity, the Docker opt-in cases, and human authorization as external.

## Read-Only Review Conclusion

The selected workflow concepts are safe to pilot as a **trimmed, project-local
documentation pattern**. They improve long-task continuity through evidence
packets, task checkpoints, bounded retries, characterization-first changes, and
handoff states. They must not be installed wholesale or allowed to override
GenBox's existing safety, phase, or release authority.

Recommendation: create and trial the GenBox-specific advisory design in
`docs/GENBOX-UNATTENDED-SKILL-DESIGN.md`; do not install the third-party pack
globally or embed it in product code.

## Remaining Risks

- This pilot is local-only and does not prove isolated-VPS, Docker, macOS,
  human authorization, runtime cleanup, Phase 6 completion, Phase 7, or
  release readiness.
- The pilot documents process behavior but has not measured agent reliability
  across many independent production-like tasks.
- Any future adoption must keep the skill reference pinned, review its license
  and changes, and re-run this compatibility gate before expanding scope.
