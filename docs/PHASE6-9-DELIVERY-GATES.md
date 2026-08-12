# Phase 6-9 Delivery Gates

**Purpose:** keep cleanup, redeployment, upstream contribution, and new
service-adapter work evidence-led and safely separated. This is a handoff and
review checklist. It does not authorize a VPS connection, a deployment, source
cleanup, a public push, or upstream contact.

## Evidence Vocabulary

Use these labels in status records and review notes:

- **VERIFIED:** a dated command, test, or bounded observation has a retained,
  sanitized result.
- **USER-CONFIRMED:** the user completed or approved a specific visible action;
  include its date and exact scope.
- **EXTERNAL:** needs a separately owned system, repository, CI run, or human
  review. Do not infer it from local tests.
- **UNVERIFIED:** no adequate evidence exists. This is the required label for
  an unknown rather than a reason to fill the gap with an assumption.

Local tests, mock receivers, UI placeholders, a deployment plan, and code on a
branch can establish local behavior. They cannot establish a live sender,
remote host ownership, a clean redeployment, or production non-mutation.

## Phase 6: Verified Source Cleanup

### Entry conditions

- The current sender/receiver contract identifies the source, receipt, and
  SHA-256 binding.
- Cleanup is independently opt-in, default-off, and unavailable to a browser
  request as a hidden development override.
- The exact isolated target and its owner have been explicitly authorized.

### Required evidence before an isolated execute exercise

- A focused test matrix covers false or malformed receipts, changed bytes,
  missing files, traversal and alias attempts, destination rotation, concurrent
  claims, crash recovery, and audit-write/unlink failures.
- The sender persists receipt authority and cleanup audit state before the
  deletion attempt, without keys, prompts, media, or raw response bodies.
- Dry run reports eligible and retained items with sanitized reasons and byte
  totals, without filesystem mutation.
- An independent security review records an explicit verdict for destructive
  execution; a design or local-test pass is not a substitute.
- A written, one-time authorization identifies only synthetic source data, the
  isolated target, expected retention/deletion result, rollback, and post-run
  checks. It explicitly excludes production.

### Execute evidence and stop rule

Record the fixed commit/image identity, pre/post health, source hash, receipt
hash, audit result, reclaimed-byte result, restart/recovery result, and a
production non-mutation check. A changed source, invalid permission, failed
receipt, ambiguous recovery state, or any target-identity mismatch must retain
the source and block phase completion.

## Phase 7: Sanitized GitHub Redeployment

### Publishable-input gate

- Freeze a candidate commit and list every tracked, generated, ignored, and
  packaged input included in the delivery.
- Scan the candidate tree, relevant history, build outputs, screenshots, logs,
  examples, archives, and container/package contents for secrets and personal
  data. Treat a matching scan result as a review item until it is classified;
  never paste sensitive matches into a status file.
- Confirm example configuration contains placeholders only, and that runtime
  storage, vaults, Push keys, administrator keys, user media, prompts, and
  host-specific artifacts are excluded from Git and release bundles.
- Record the sanitizer command class and result, the candidate commit, and the
  reviewer decision. A clean working tree alone is insufficient.

### Clean-redeployment gate

- Provision a new clean destination that does not reuse the development-clone
  source tree, configuration, secret store, volumes, or manual container edits.
- Build and deploy only from the owner's sanitized repository commit and
  documented example configuration with newly generated credentials.
- Repeat the applicable single-image and batch acceptance cases, then compare
  the resulting artifact identity with the recorded commit/build identity.
- Record the production source non-mutation result separately. Do not turn a
  successful local build or earlier isolated-clone result into a Phase 7 pass.

## Phase 8: Upstream Delivery

Prepare upstream material only after the Phase 7 publishable-input and
clean-redeployment gates are verified. Keep the contribution reviewable:

- Split work into Push foundation, generation/Gallery batch flow, and
  scheduler/confirmed-cleanup slices, unless the upstream maintainer requests a
  different boundary.
- For each slice, provide its contract version, migration/configuration notes,
  test commands/results, compatibility assumptions, rollback or disable path,
  and known limitations.
- Use placeholders in all examples. Do not include real hosts, ports, keys,
  images, prompts, accounts, cookies, runtime logs, or a claim that the
  upstream repository has accepted the work.
- When a PR is unsuitable, deliver the same material as a proposal based on
  `docs/UPSTREAM-VIBE-CODING-GUIDE.md`; label it draft until independently
  accepted.

## Phase 9: Additional Service Adapters

Catalog metadata, environment recommendations, and an executable adapter are
separate things. A planned service must remain non-executable until its dossier
and implementation pass review.

For each adapter, create a versioned dossier containing:

| Area | Minimum decision or evidence |
| --- | --- |
| Identity | Canonical source repository, revision/image provenance, license |
| Capability | Exact supported modes and backend capability for each UI action |
| Configuration | Typed inputs, defaults, validation, and example-only values |
| Secrets | Creation, delivery, masking, rotation, revocation, and storage policy |
| Isolation | Instance ID, paths, volumes, names, and port-conflict handling |
| Network | Exposure model, host-key handling, endpoint and application-level probe |
| Operations | Upgrade, backup, rollback, uninstall, ownership, and recovery |
| Verification | Unit/API/UI tests, isolated deployment, and delivery-information check |

The adapter may become available only when its backend enforces the same
capability and ownership boundaries presented in the UI. Environment facts that
are unknown remain unknown; recommendations do not permit execution.

## Status Record Template

Keep `docs/STATUS.md` concise. For a substantive gate, record:

```text
DATE / SCOPE: <phase and exact bounded activity>
COMMIT OR ARTIFACT: <non-secret identity>
VERIFIED: <commands or observations and sanitized results>
EXTERNAL OR UNVERIFIED: <remaining independent gate>
BOUNDARY: <what was not contacted, changed, or authorized>
RESUME: <one safe next action>
```

Replace superseded entries rather than appending a session diary. Move durable
policy changes to `docs/DECISIONS.md`, protocol changes to
`docs/INTEGRATION.md`, and phase acceptance changes to `docs/ROADMAP.md`.
