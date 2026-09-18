# Video Workbench Agent Collaboration Protocol

Date: 2026-09-18 (UTC). Revision: 0.6.
Status: **W1-0/W1-1 complete; WB1-MEDIA running; WB1-PROJECT ready but not started; unattended execution enabled.**

Current execution is coordinator-only. No additional Agent was dispatched for
the media integration checkpoint. Shared wiring is coordinator-owned; an
independent review has not occurred and must not be inferred from local tests.

## Operating Model

One coordinator owns the primary objective. GSD supplies the phase/plan/verify
structure; selectively adapted Agency role descriptions supply expertise.
Borrow specification traceability and independent review practices without
installing competing autonomous controllers.

This governs agents developing GenBox, not a multi-agent runtime in the product.
Follow runtime and user rules for delegation. A role roster is not permission
to spawn agents. Planning this strategy does not execute it.

The bounded unattended rules are normative in
[VIDEO-WORKBENCH-AUTONOMOUS-EXECUTION.md](VIDEO-WORKBENCH-AUTONOMOUS-EXECUTION.md).
They allow low-risk local work to continue, but never grant permission for
production/VPS changes, paid Provider calls, destructive media operations,
contract changes or release publication.

## Sources And Tool Policy

VERIFIED by repository reads on 2026-09-18:

- Agency Agents `msitarzewski/agency-agents`, observed HEAD `ad9264e309bd5e5422c04784372d7841b1e5d604`:
  README, `engineering/engineering-multi-agent-systems-architect.md` and
  `testing/testing-reality-checker.md`.
- GSD old `gsd-build/get-shit-done` README points to `open-gsd/gsd-core`;
  observed new HEAD `c9a5cc3e1288b432305aa8eea881fa2eab883083`.
  Read README and existing-codebase onboarding tutorial.
- `github/spec-kit` README: specification/plan/task traceability.
- `bmad-code-org/BMAD-METHOD` README: product/architecture/UX/development roles.
- `obra/superpowers` README and subagent-development skill: scoped implementation,
  task review and final integrated review.

These are observed documentation, not tested effectiveness or automatic
endorsement of every rule. Do not copy stack-specific commands, arbitrary QA
scores, permissive cleanup or mandatory retry behavior into this project.
Source prompts never override GenBox security, authorization or truth rules.

Before using GSD, record installed version and applicable local modifications.
Pin the chosen version; do not auto-upgrade or overwrite global/local skills.
GSD-generated task artifacts must cite authoritative docs and their revisions.
Do not treat historical `.planning/` notes as current acceptance evidence.

## Roles And Ownership

Proposed module paths below are allocations, not claims that files exist.
Freeze actual paths in W0.5 after code mapping.

| Role | Responsibility | Allowed ownership | Must not do |
| --- | --- | --- | --- |
| Coordinator/integrator | Scope, contracts, task ledger, shared wiring, integration | Master docs, topic contracts, shared `main.py`/HTML/router/build entry points | Invent acceptance or enlarge scope silently |
| Product/UX specialist | Journeys, state matrix, accessibility and layout review | UX draft and approved mockup artifacts | Promise unverified model features |
| Media engineer | Import/probe/proxy, timeline validation, local render | Proposed `video_workbench/assets*`, `projects*`, `render*` and matching tests | Change provider transport or delete source media |
| Frontend implementer | Workbench UI and browser behavior | Proposed isolated workbench JS/CSS and UI tests | Independently change shared API/schema or global styles |
| AI adapter specialist | Capability registry, canonical intents and qualified adapters | Proposed `video_workbench/adapters/`, edit jobs and matching tests | Rewrite existing generation protocols or trigger paid calls |
| Independent reviewer | Contract/security review, regression, actual workflow proof | Read-only code; assigned review report | Approve solely from implementer's summary |

Default execution: coordinator plus at most two implementers; reviewer runs at a
stable integration checkpoint. UX/research roles are activated when useful, not
kept as permanent parallel workers. Small coupled fixes run in one agent.
The current runtime limit always takes precedence over this suggested budget.

## Task Packet

Every dispatch must provide:

```text
task_id / phase / VW requirements / VA acceptance cases
objective and explicitly excluded scope
baseline commit + assigned absolute workspace path
authoritative document revisions and necessary source files
dependencies and input/output schemas
owned files and shared files that must not be edited
allowed tools/side effects; paid/network/media disclosure restrictions
commands to run; fixtures; expected evidence
time/token/tool budget if explicitly established
handoff destination and stop/escalation conditions
```

Send minimal sufficient context, not the entire conversation or private media.
Tell implementers they are not alone and must not revert others' changes.
Shared files require coordinator handoff, not competing edits.

## Workspace And Integration Rules

- A spawned agent shares the checkout unless isolation is explicitly established.
  Never claim that starting an agent automatically creates a worktree.
- For isolated implementation, coordinator verifies actual worktree/branch,
  baseline and ownership before dispatch. Branch names use `codex/`.
- In a shared checkout, disjoint file ownership is mandatory; serialize shared
  changes. No agent runs broad Git staging, resets or cleanup.
- Use explicit file lists when committing. A worker must not commit another
  worker's incomplete changes. In shared workspaces the coordinator owns commits.
- For separate branches, integrate approved commits serially; never merge runtime
  files, credentials, screenshots of private data or unrelated changes.
- Re-run interface and workflow tests after integration, even if both branches
  passed independently. Worktree isolation does not resolve schema conflicts.
- Coordinator alone updates authoritative progress and performs approved release
  actions. Workers report findings rather than independently publishing.

## Lifecycle And Handoff

Task states: planned -> ready -> running -> review -> integrated -> accepted.
blocked and needs_revision are explicit alternatives, not hidden success.
Only dispatch ready tasks with satisfied dependencies.

Worker handoff includes task ID, baseline/current commit or diff, changed files,
commands/results, contract deviations, unverified behavior, blockers and next
action. Reviewer checks actual source/tests, not just the report.

The phase ledger in PLAN is the current summary. Detailed execution evidence can
live in one assigned phase report; do not create rival status documents.
After interruption, compare ledger with Git and evidence before redispatching.
Missing evidence means unverified, not automatically failed or accepted.

## Review And Escalation

Review specification compliance first, then correctness, security, UX and
integration. Reviewer should not be the implementation author; if independent
review is unavailable, mark self-review explicitly and retain that release gate.

After two unsuccessful revision cycles on the same issue, coordinator revisits
the contract/task decomposition. Do not waive data-loss, auth, duplicate-billing
or broken-output defects to meet a retry cap. Escalate material scope, privacy,
paid usage, destructive actions and external publication to the user.

No automatic agent-to-agent spawning tree, unlimited debate loop, unsolicited
background automation or repeat paid generation. A blocked agent returns bounded
evidence and a precise dependency rather than waiting silently.

## Frozen WB-1 Ownership Packets

The following ownership is frozen for the next phase. These are task packets,
not evidence that implementation has started:

| Packet | Primary owner | Owned paths (once created) | Review boundary |
| --- | --- | --- | --- |
| WB1-MEDIA | Media engineer | `video_workbench/media/`, probe/proxy/render tests | Coordinator reviews limits and worker invocation |
| WB1-PROJECT | Coordinator + project-storage implementer | `video_workbench/projects/`, schema/revision tests | Independent reviewer checks conflict/restart behavior |
| WB1-UI | Frontend implementer | isolated workbench JS/CSS and browser tests | UX specialist checks four viewports and keyboard path |
| WB1-REVIEW | Independent reviewer | read-only review report and evidence ledger | No implementation edits or release actions |

The AI adapter specialist is **not** assigned to WB-1 implementation. That role
activates in WB-3 for the frozen provider contract, fake adapter A/B tests and
the separately authorized live edit gate. The coordinator serializes shared
`main.py`, `static/index.html`, global styles, authoritative docs and any
release files. No packet may broaden the frozen scope or add a provider-specific
shortcut.

No multi-agent installation is needed merely to execute this plan. Each future
dispatch must use the task-packet fields above and the accepted contract
revision from WB-0.

The detailed wave order, dependencies, exit evidence and stop conditions are
defined in [VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md](VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md).
W1-0/W1-1 evidence has been recorded in
[VIDEO-WORKBENCH-WB1-FIXTURES.md](VIDEO-WORKBENCH-WB1-FIXTURES.md). The
`WB1-MEDIA` and `WB1-PROJECT` packets may now change from `planned` to `ready`;
`WB1-UI` remains dependent on stable route DTOs and fixture-server behavior.

## Unattended Execution State

The coordinator may continue `ready -> running -> review` for bounded local
tasks without asking for a turn-by-turn confirmation. The coordinator must
pause at the gates listed in the autonomous execution protocol and record the
exact recovery command. “Unattended” means bounded continuation within the
current authorized workspace; it is not a background process or permission to
publish, deploy or spend money.
