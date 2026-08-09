# Agent Skills Pilot Plan

## Objective

Evaluate a narrowly selected subset of `addyosmani/agent-skills` as a process
overlay for GenBox and chatgpt2api unattended long-running work. This pilot
does not install third-party skills, alter product behavior, use a VPS, run
cleanup, create a release artifact, or claim Phase 6 or Phase 7 completion.

## Governing Constraints

- Existing `AGENTS.md` and current GenBox product, architecture, roadmap,
  decision, and lifecycle documents remain the controlling rules.
- The third-party repository at `C:\tmp\genbox-agent-skills-pilot` is a
  read-only reference fixed at `7676817c12a1317454ae3898a0c5c1eacf5dd3d5`.
- Source cleanup stays disabled. No runtime cleanup endpoint, port `33010`,
  port `33018`, VPS, user data, or credentials may be used.
- Evidence labels remain `LOCAL`, `CI`, `EXTERNAL`, or `UNVERIFIED`; local
  tests do not establish deployment, release, or cross-project completion.

## Tasks

### Task 1: Establish the context packet

**Dependencies:** none.

**Acceptance criteria:** Record the fixed third-party commit and MIT license;
record both pilot branches, baselines, Git identity, and clean status; identify
the existing documents that outrank the pilot.

**Verification:** `git rev-parse`, `git status --porcelain`, and read-only
document review.

**Checkpoint:** Do not proceed if a target worktree differs from its supplied
path, branch, baseline, identity, or clean state.

### Task 2: Review and trim the candidate skills

**Dependencies:** Task 1.

**Acceptance criteria:** Evaluate only context engineering, planning/task
breakdown, incremental implementation, TDD, code review, security/hardening,
CI/CD automation, and debugging/recovery. State adoption, rejection, or trim
decisions and conflicts with GenBox's safety contract.

**Verification:** Review the third-party README, adoption guide, license, and
each candidate `SKILL.md`; cite local source paths and version pin in the pilot
review.

**Checkpoint:** No third-party installation, no overwrite of `AGENTS.md`, and
no copied skill text into product source.

### Task 3: Characterize the existing Phase 6 safety boundary

**Dependencies:** Task 2.

**Acceptance criteria:** Execute existing, focused synthetic tests proving:
cleanup is disabled by default; `safe_to_delete_source` is fail-closed; and
sensitive Push/configuration information stays out of URLs, browser storage,
and public task/projection surfaces.

**Verification:** Focused GenBox pytest files and Sender unittest files, with
syntax/compile checks. Add a test only if the existing suite leaves one of the
three stated claims unsupported.

**Checkpoint:** A test failure follows reproduce-localize-reduce-guard; no
product change is made merely to demonstrate a skill.

### Task 4: Independently review evidence and completion state

**Dependencies:** Task 3.

**Acceptance criteria:** Compare every pilot claim to command output, source,
or test evidence. Classify unavailable external evidence instead of filling it
with inference.

**Verification:** Read-only diff review, `git diff --check`, tracked-file
secret scan limited to pilot changes, and clean-worktree checks.

**Checkpoint:** Stop product-facing execution if a genuine secret, user data,
production target, port `33010`/`33018`, or uncontrolled deletion path appears.

### Task 5: Produce the unattended-workflow recommendation

**Dependencies:** Task 4.

**Acceptance criteria:** Document the trimmed workflow: task quality,
dependencies, checkpoints, recovery states, handoff, external non-blockers,
and final state machine. Make clear that it is an advisory GenBox-specific
design, not an installed global skill.

**Verification:** Cross-check against existing `AGENTS.md`,
`DEVELOPMENT-LIFECYCLE.md`, and Phase 6 evidence. Ensure it does not authorize
cleanup, release, VPS work, or a status change.

**Checkpoint:** No roadmap/status claim changes without phase-specific evidence.

### Task 6: Commit only review artifacts

**Dependencies:** Task 5.

**Acceptance criteria:** Create atomic documentation-only commits in the
respective clean pilot worktrees when each has local changes. Push only a
previously verified writable fork, without force push. Leave both worktrees
clean.

**Verification:** `git diff --check`, `git status --porcelain`, commit/log
inspection, and remote tracking inspection.

**Checkpoint:** A `403`, unavailable remote, or missing writable fork is
`EXTERNAL` after one retry; it does not block the local pilot conclusion.

## Risks And Mitigations

- Third-party guidance can conflict with existing safety rules: preserve GenBox
  documents as the authority and adopt only compatible process fragments.
- Brownfield tests can give false confidence: characterize only existing
  behavior and label all non-local evidence separately.
- Automation can imply authority: use an explicit state machine with blocked
  destructive actions and human authorization gates.

## Parallelization

Documentation review and test inventory can proceed independently. Test
execution and final evidence synthesis remain sequential so each claim is tied
to the exact checked baseline and result.
