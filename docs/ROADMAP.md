# GenBox Extension And chatgpt2api Integration Roadmap

Status values are `Planned`, `In Progress`, `Blocked`, and `Complete`. A phase is
complete only when its acceptance criteria have recorded evidence. Code,
mock-based tests, UI, and live-environment verification are separate evidence.

## Phase 0: Project Fact And Documentation Baseline

**Status:** Complete

**Topic contracts:** `AGENTS.md`, `docs/STATUS.md`

### Goal

Establish accurate sources of truth so development can continue across short AI
sessions without relying on chat history.

### Deliverables

- GenBox-specific `AGENTS.md`.
- Product, architecture, roadmap, status, decisions, lifecycle, and integration
  documents.
- Verified test baseline and explicit runtime-unknown markers.
- Existing topic contracts linked into the documentation hierarchy.

### Acceptance Criteria

- A new contributor can identify the product goal, current phase, next task,
  repository boundaries, and production safety policy from repository files.
- Documentation does not claim a live VPS or overlay IP without dated evidence.
- Current automated tests pass and the command/result is recorded.

## Phase 1: Production Discovery And Development Clone

**Status:** Complete

**Topic contract:** `docs/extensions-deployment-contract.md`

### Goal

Prove that GenBox can inspect an existing chatgpt2api instance without mutation
and create a fully isolated development clone.

### Deliverables

- Read-only VPS and application discovery.
- Source instance ownership and clone eligibility report.
- Blank, media-only, and safe-working-copy clone plans.
- Isolation of directory, volume, port, container, Compose project, management
  key, Push source ID, and Push key.
- Production non-mutation evidence.

### Acceptance Criteria

- Discovery commands are read-only and host-key verified.
- A development clone starts and passes health checks on a non-production port.
- Source and clone data/configuration targets are demonstrably different.
- Production container identity, configuration checksum, start time, and health
  remain unchanged across clone creation.
- Clone failures leave the production source operational.

### Out Of Scope

- Developing features in the production container.
- Automatic source-image deletion.

## Phase 2: Extension Center Deployment Experience

**Status:** Complete

**Acceptance evidence:** Local code, automated tests, and independent review
passed on 2026-07-17. On 2026-07-19 the isolated managed `chatgpt2api-dev`
instance was user-confirmed ready with usable delivery information during the
successful private-network acceptance flow. Production remains outside the
development mutation scope.

**Topic contract:** `docs/extensions-deployment-contract.md`

### Goal

Provide a clear guided path from target configuration through a usable,
isolated chatgpt2api deployment.

### Deliverables

- Catalog with stable unique IDs and honest availability states.
- Target, credential, fingerprint, discovery, plan, execution, and delivery UI.
- Durable deployment task state, cancellation, retry, and recovery.
- Service status, console URL, API URL, login guidance, and copy actions.
- Managed-key rotation with ownership and rollback checks.

### Acceptance Criteria

- The duplicate `gemini2api` catalog identity is resolved.
- Refreshing the browser does not lose an active deployment task.
- Available actions match backend capabilities; planned services cannot execute.
- Delivery information opens and copies correctly without persisting secrets in
  browser storage.
- Deployment failure produces an actionable, sanitized recovery state.

## Phase 3: Private Network Automation

**Status:** Complete

**Acceptance evidence:** On 2026-07-19 the isolated managed development target
completed local status, VPS enrollment/address detection, peer reachability,
VPS-to-GenBox HTTP probing, and MagicDNS destination persistence. The user
confirmed the final `PRIVATE LINK READY` state. Enrollment and SSH session
secrets were absent from persisted target metadata. Full local verification
passed with `247 passed`.

**Topic contracts:** `docs/extensions-deployment-contract.md`,
`docs/INTEGRATION.md`

### Goal

Establish and verify a secure route from chatgpt2api to GenBox.

### Deliverables

- Complete one primary adapter first, with Tailscale as the recommended path.
- NetBird and Cloudflare adapters retained behind accurate readiness states.
- Local and VPS enrollment, service exposure, and application-level probes.
- Final stable GenBox Push URL stored as non-secret destination metadata.
- Credential-gated, single-flight SSH and network checks with deployment state
  kept separate from private-network completion and restart recovery.
- An owned local Lab lifecycle with runtime/source identity plus browser
  heartbeat, so cached pages and stale Python processes cannot masquerade as the
  current Phase 3 build.

### Acceptance Criteria

- GenBox verifies local status, VPS reachability, and VPS-to-GenBox HTTP access.
- The final Push URL does not use `127.0.0.1` or an unintended public endpoint.
- Enrollment tokens are absent from persisted target records and logs.
- Failure identifies the exact failed network stage and recovery action.
- A completed service deployment cannot mark the private network complete,
  populate the GenBox private URL with a service console URL, or force the final
  step after restart.
- Missing or ambiguous SSH credentials fail closed before SSH or network-task
  side effects, and stale or duplicate browser requests cannot unlock later
  steps.
- A stopped, old, or mismatched local backend is shown as offline; remote
  controls remain locked until the browser verifies the current development
  runtime. Local stop/restart cannot terminate an unowned port listener.

## Phase 4: Single-Image Push End To End

**Status:** In Progress

**Current boundary:** The GenBox Push v1 receiver exists and has local tests.
The chatgpt2api sender, per-generation action, and real single-image receipt are
not yet complete.

**Topic contracts:** `docs/INTEGRATION.md`,
`docs/chatgpt2api-push-integration.md`

### Goal

Push one newly generated image from an isolated chatgpt2api development clone to
GenBox and import it with metadata.

### Deliverables

- Stable GenBox Push v1 contract and destination configuration.
- Shared chatgpt2api Push service.
- Per-generation "Push to GenBox" option.
- Receipt verification and durable per-image transfer state.
- Media-library source and metadata tags.

### Acceptance Criteria

- One generated image appears once in the GenBox image library.
- Prompt, model, source, remote path, and creation time are retained when
  available.
- Retrying the request is idempotent.
- Authentication failure, network failure, invalid image, and hash mismatch keep
  the source image.
- GenBox receiver and chatgpt2api sender tests pass.


### chatgpt2api Image Management Destination UI

- Add a "Push to GenBox" destination control to chatgpt2api image management.
- Default to the private GenBox URL produced by Phase 3 network verification.
- Provide an advanced host/port editor for users who changed their GenBox or
  private-entry port.
- Test the destination before saving; reject loopback, unintended public targets,
  invalid ports, and unreachable endpoints with a plain-language recovery action.
- Keep Push authentication separate from the destination URL and never place the
  Push key in browser storage or URLs.

## Phase 5: Batch And Scheduled Incremental Push

**Status:** Planned

**Topic contracts:** `docs/INTEGRATION.md`,
`docs/chatgpt2api-push-integration.md`

### Goal

Transfer existing and future images reliably without manual per-image work.

### Deliverables

- Gallery selection and manual batch Push.
- Date-range selection and preview.
- Default weekly schedule and user-defined schedule/date bounds.
- Persistent cursor, per-image state, worker lease, progress, cancellation, and
  bounded retry.

### Acceptance Criteria

- A batch resumes after interruption without duplicate imports or silent skips.
- Late-arriving files inside the scan range are discovered.
- Concurrent workers cannot process the same schedule simultaneously.
- Users can identify failed images and retry only failures.

## Phase 6: Verified Source Cleanup

**Status:** Planned

**Topic contracts:** `docs/INTEGRATION.md`,
`docs/chatgpt2api-push-integration.md`

### Goal

Allow users to reclaim VPS space without risking unconfirmed media loss.

### Deliverables

- Separate opt-in cleanup policy.
- Receipt and SHA-256 verification before deletion.
- Cleanup audit records and reclaimed-space summary.
- Dry-run and failure reporting.

### Acceptance Criteria

- Cleanup is off by default and disabled in development.
- Only a matching authenticated receipt with
  `safe_to_delete_source=true` authorizes deletion.
- Failed, pending, changed, or unverified files remain on the source.
- Audit output can explain every deletion decision.

## Phase 7: Sanitized GitHub Redeployment

**Status:** Planned

**Topic contract:** `docs/DEVELOPMENT-LIFECYCLE.md`

### Goal

Prove the feature is reproducible from the owner's GitHub repository and does
not depend on uncommitted container changes or sensitive data.

### Deliverables

- Secret and personal-data scan of files and Git history.
- Sanitized commits pushed to the owner's repository.
- Clean environment deployed only from that repository.
- Repeated integration acceptance test.

### Acceptance Criteria

- No real secret, VPS identity, user media, prompt, account, or log is present in
  the repository or distributable artifacts.
- A fresh clone builds and deploys using documented example configuration.
- Single and batch transfer acceptance tests pass in the clean deployment.
- Production source remains unchanged.

## Phase 8: Upstream Delivery

**Status:** Planned

**Topic contracts:** `docs/DEVELOPMENT-LIFECYCLE.md`,
`docs/UPSTREAM-VIBE-CODING-GUIDE.md`

### Goal

Offer the chatgpt2api changes to the original author in a reviewable form.

### Deliverables

- Small PRs for Push foundation, UI/batch flow, and scheduling/cleanup, or a
  complete extension proposal when code contribution is not appropriate.
- An AI-oriented Vibe Coding guide with contracts, task boundaries, prompts, and
  acceptance tests.
- Compatibility and migration notes.

### Acceptance Criteria

- Phase 7 evidence is complete before upstream contact.
- Each PR has a narrow purpose and independent tests.
- Proposal examples contain no environment-specific or sensitive values.

## Phase 9: GenBox Store Foundation

**Status:** Planned

**Topic contract:** `docs/GENBOX-STORE-REPAIR-COPILOT.md`

### Goal

Turn the catalog into a trustworthy Store without making planned apps executable.

### Deliverables

- Installed, Recommended, and All views.
- Separate versioned app manifests and executable adapters.
- Environment compatibility recommendations with explanations and confidence.
- Managed/external ownership boundaries plus license, provenance, security, and
  operational-risk labels.

### Acceptance Criteria

- Every visible action is derived from backend adapter capability, not manifest
  metadata or recommendation output.
- Unknown environment facts and unavailable apps remain explicit and fail closed.
- External instances remain advisory/read-only without a verified adoption flow.
- Store metadata identifies source, license, permissions, exposure, and risk.

## Phase 10: Advisory Repair Copilot

**Status:** Planned

**Topic contract:** `docs/GENBOX-STORE-REPAIR-COPILOT.md`

### Goal

Explain failures safely before any AI-assisted mutation is permitted.

### Deliverables

- Deterministic diagnostic fallback and minimum-evidence collection.
- Redaction boundary and dedicated user-selected diagnostic model configuration.
- Structured diagnoses with facts, confidence, risk, rollback, and verification.
- Explicit authorization UI with advisory-only output.

### Acceptance Criteria

- Raw logs, secrets, personal data, host identities, and credentials never enter
  model prompts or experience records.
- Unknown or unavailable models fall back to deterministic guidance.
- AI cannot submit shell, obtain root, or directly mutate a target.
- Advice clearly distinguishes observed facts from inference.

## Phase 11: Additional Service Adapters

**Status:** Planned

**Topic contracts:** `docs/extensions-deployment-contract.md`,
`docs/GENBOX-STORE-REPAIR-COPILOT.md`

### Goal

Extend the guided deployment model one independently verified adapter at a time.

### Acceptance Criteria

Each service must independently define source repository identity, license,
configuration, secrets, ports, persistence, health check, delivery information,
upgrade, backup, rollback, uninstall, and tests before becoming deployable.

## Phase 12: Verified Repair Experience Flywheel And Allowlisted Assisted Repair

**Status:** Planned

**Topic contract:** `docs/GENBOX-STORE-REPAIR-COPILOT.md`

### Goal

Reuse reviewed operational knowledge and execute bounded repairs without turning
AI advice into general remote administration.

### Deliverables

- Sanitized experience records with `draft`, `reviewed`, `verified`, and
  `deprecated` lifecycle states.
- Human review and reproducibility gates for experience promotion.
- Adapter-owned repair allowlists, exact-target authorization, rollback, and
  deterministic post-repair health verification.

### Acceptance Criteria

- Raw logs are never used for self-training or automatic experience promotion.
- Only `verified` experience may influence reusable repair recommendations.
- Every mutation is user-authorized, ownership-scoped, allowlisted, auditable,
  rollback-aware, and followed by a deterministic health check.
- Failed verification stops the workflow and presents a safe recovery state.
