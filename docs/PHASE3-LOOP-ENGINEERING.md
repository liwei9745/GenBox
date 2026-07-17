# Phase 3 Loop Engineering Protocol

## Objective

Complete Private Network Automation through small, reviewable loops. The first
complete path is Tailscale. Production chatgpt2api remains read-only; no VPS
operation occurs until local gates pass and the user identifies an isolated
development clone.

## Team Roles

- **Orchestrator:** owns scope, task state, safety decisions, and final gates.
- **Builder:** makes the smallest code and test change for the active loop.
- **Security reviewer:** independently checks trust boundaries, secret handling,
  SSRF/destination controls, and unsafe remote commands.
- **Test reviewer:** independently checks route coverage, failure paths, and
  regression gaps.

Current Codex sessions may supply generic subagents rather than typed GSD
agents. Review findings are therefore labelled as independent role reviews, not
as proof that a particular model was used.

## Loop Lifecycle

`Inbox -> Scoped -> Build -> Focused test -> Independent review -> Fix or Gate -> Done`

Every loop records:

1. One narrow outcome and an explicit non-goal.
2. Tests written or updated before/with the behavior change.
3. Focused test result, then full-suite result before a commit.
4. At least one independent review for security-sensitive work.
5. A handoff stating changed files, verification commands, remaining risks, and
   the next loop.

## Ordered Loops

1. **Readiness and failure contract:** Tailscale-only gate, structured failed
   phase/recovery state, no task-state secrets.
2. **Destination proof:** validate and persist only the verified Tailnet route;
   require an application-level GenBox probe.
3. **Enrollment safety:** do not expose enrollment tokens through task state,
   logs, or remote process arguments. Until a safe automated mechanism is
   proven, accept only an already-enrolled isolated VPS.
4. **SSH trust chain:** validate the expected host key in the SSH handshake
   before any password, private key, agent key, or local SSH configuration can
   participate.
5. **Route and UI truthfulness:** route-level validation/redaction coverage and
   UI readiness that matches backend capability.
6. **Local release gate:** full test suite, syntax checks, diff/secret review,
   and independent final review.
7. **Isolated VPS acceptance:** only after explicit user authorization and a
   verified isolated clone; collect non-secret evidence for local status, peer
   reachability, application probe, stored destination, and production
   non-mutation.

## Stop Conditions

Stop and return to the prior loop when a review finds a P1 issue, a test fails,
or a proposed action could touch production. Stop and request user direction if
an isolated clone, host-key identity, ownership, or rollback boundary is
ambiguous.

## Current Position

Loops 1-4 have passed focused tests and independent security review. Loop 5 is
in progress: route-level validation found and fixed a FastAPI 422 request-body
credential echo. The next gate is full regression and final review; no VPS
action is authorized yet.
