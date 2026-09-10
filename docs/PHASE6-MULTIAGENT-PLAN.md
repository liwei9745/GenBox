# Phase 6 Multi-Agent Delivery Plan

## Objective

Implement verified source cleanup for the isolated chatgpt2api sender without
deleting a source image unless an authenticated GenBox receipt, matching
SHA-256, `safe_to_delete_source=true`, and explicit user opt-in all agree.
Production cleanup remains disabled.

## Three Reasoning Lenses

### First principles (always on)

Start every task by writing the invariant, the authority boundary, the failure
behavior, and the evidence that would prove success. For cleanup, the invariant
is: an unconfirmed or changed source survives. This lens is the permanent
design and acceptance contract.

### Role perspectives (short-lived)

Use capability roles rather than claiming affiliation with OpenAI, Google,
Anthropic, or any other company. The useful lenses are:

- **Protocol engineer:** receipt fields, hashes, version compatibility, and
  idempotency.
- **Platform/release engineer:** isolated resources, rollback, reproducible
  images, and deployment boundaries.
- **Security engineer:** authority confusion, replay, path escape, secret
  exposure, and destructive-action gates.

Assign one primary lens per task. Do not ask every Agent to solve the same
problem independently.

### Adversarial review (at gates)

Enable a separate reviewer after the design, before merge, and before any
cleanup-capable isolated deployment. The reviewer tries to produce a false
receipt, altered source, replayed receipt, wrong source ID, path escape, and
partial-failure deletion. A failed challenge blocks the task; it is not an
optional commentary pass.

## Team Shape

The orchestrator owns scope, task state, and release decisions. A builder owns
the implementation. A reviewer owns adversarial findings and must not edit the
builder's files during the first review. An ops verifier owns isolated runtime
evidence. Every handoff records files, commands, results, known gaps, and the
next action.

## Target-Mode Lifecycle

1. **Specify:** write the invariant, threat cases, files, and acceptance tests.
2. **Build:** implement only the assigned ownership slice.
3. **Review:** run focused tests plus adversarial cases; return findings by
   severity.
4. **Integrate:** apply fixes, run the full local suite, and inspect the diff.
5. **Isolated verify:** deploy an immutable image only to the isolated target;
   capture receipts, hashes, retention, and rollback evidence.
6. **Close:** update `STATUS.md`, `ROADMAP.md`, and release notes only when the
   evidence meets the phase criteria.

## Duration Policy

- First-principles checks: permanent.
- Role perspectives: enabled per task or review wave, then archived.
- Adversarial review: mandatory at design, merge, and destructive-operation
  gates; not a background process on every keystroke.
- Parallelism: use two to four agents only when ownership boundaries are
  disjoint. Shared files and final release decisions stay with the orchestrator.

## Start Command

Begin a target-mode run with one objective sentence and explicit boundaries:

> Target: complete Phase 6 verified source cleanup on the isolated development
> sender only. Production cleanup is disabled. Run protocol, platform, and
> security review lenses; require adversarial approval before isolated deploy.

The first deliverable is a small Phase 6 spec and test matrix, not code. No
remote mutation is authorized by this sentence alone; deployment still needs a
separate explicit confirmation after the plan is reviewed.
