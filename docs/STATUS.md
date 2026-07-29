# Current Project Status

**Last updated:** 2026-07-29
**Current branch:** `codex/p4-deploy-plan-ux-eai`
**Current phase:** Phase 4 Single-Image Push End To End - **In Progress**

## Current evidence

- **LOCAL 2026-07-29:** safety-plan generation now requires a separate,
  explicit browser confirmation before it performs its two fixed plan-preflight
  read-only checks. Without `approve_plan_discovery=true`, the backend returns
  a recoverable rejection before invoking any environment discovery. The UI
  first validates the local deployment-image input, then explains that the
  approved checks only examine port, directory, and isolation conditions and
  cannot deploy, pull an image, or alter services. A cancelled or unavailable
  confirmation sends no plan request. The approval marker is intentionally
  excluded from the plan-change snapshot, preventing a valid response from
  being discarded as stale. Focused extension suites passed `355`; full local
  `python -m pytest -q` passed `547`; Python compilation, JavaScript syntax,
  and whitespace checks passed. A fresh loopback-only runtime on port `8900`
  loaded `#/extensions` with no console errors and no horizontal overflow at
  `390x844`; no target was selected, no credential was entered, and no SSH,
  VPS, container, discovery, plan, deployment, or network action was
  submitted. This is `LOCAL` UI/API/test evidence only. A previously generated
  user-visible plan predates this guard and is not evidence that the new
  explicit-preflight interaction ran.
- **VERIFIED 2026-07-29:** the user-authorized experimental GHCR sender-image
  publication was queried by immutable digest. Its OCI index exposes both
  `linux/amd64` and `linux/arm64`; its public package metadata identifies the
  corresponding immutable release tag. The locally reviewed sender application
  and Docker build inputs match the published source tree; only publishing
  workflow text differs. The sender workflow's focused image-delivery tests
  passed locally. This verifies a registry artifact for plan input, not a VPS
  pull, deployment, private-route, transfer, or production result.
- **USER-CONFIRMED 2026-07-29:** the user completed the authorized single
  host-key-verified L2 read-only environment check in the local Extensions
  page. The visible result advanced to deployment-option review and stated that
  no deployment had started. No host identity, credential, raw terminal output,
  fingerprint, or VPS address was retained in this record. This is a
  user-visible completion report, not independent `ISOLATED-VPS` verification
  or deployment evidence. The next prerequisite before a safety plan is an
  immutable, server-pullable image digest; no image, plan, or deployment has
  been submitted from this evidence.
- **LOCAL 2026-07-29:** bounded the authorized L2 read-only environment
  discovery so a stalled SSH/Docker read cannot leave the browser indefinitely
  in a loading state. The backend cancels discovery after 45 seconds and
  returns a sanitized timeout diagnostic that does not require host-key
  reconfirmation. The browser aborts an unresponsive request after 65 seconds,
  restores the one read-only-check action, and gives a retry path without
  starting pairing, an SSH deployment diagnostic, plan generation, or
  deployment. Focused route/DOM regressions cover cancellation, secret-free
  error content, request abortion, and restored controls. Python compilation,
  JavaScript syntax checks, diff whitespace checks, and the full local pytest
  suite passed `545`. A fresh loopback-only Lab loaded the committed runtime
  identity and rendered `#/extensions` with no browser-console errors; no
  target was selected and no credential or remote request was submitted. No
  SSH, VPS, remote container, deployment, network, or production action was
  performed. This is `LOCAL` evidence only.
- **LOCAL 2026-07-29:** launched a fresh loopback-only Lab for the current
  worktree and verified its runtime identity reports commit `fe6a3c4` and the
  manual-current-worktree source. Browser inspection confirmed that its visible
  credential action invokes read-only discovery and the advanced deployment
  disclosure starts closed. No target was selected, no credential was submitted,
  and no SSH, VPS, container, deployment, or network request was made. This is
  `LOCAL` runtime/browser evidence only.
- **LOCAL 2026-07-29:** narrowed the L2 credential surface for the one
  host-key-verified read-only environment check. The primary credential action
  and guide both invoke discovery rather than the deployment diagnostic. Sudo
  choices are collapsed under an advanced deployment-only disclosure, and the
  discovery request defensively replaces any stale or accidentally entered
  elevation fields with `none` and empty sudo data. This does not remove the
  separate advanced diagnostic needed before a later deployment. Focused DOM
  regression tests prove that simulated sudo input is absent from the discovery
  request; the full local pytest suite passed `543`; and a local browser check
  confirmed the disclosure is closed by default and the primary action remains
  `Run read-only check`. No target was selected, no credential was submitted,
  and no SSH, VPS, container, deployment, or network request was made. This is
  `LOCAL` evidence only.
- **LOCAL 2026-07-29:** simplified the personal-server path so the credential
  view's primary action now runs the one bounded, host-key-verified read-only
  environment discovery directly. It no longer requires the separate SSH
  deployment-access diagnostic first, so an authorized discovery cannot loop
  through credentials and deployment checks. The guarded discovery uses no
  `sudo`; it advances to the public environment result and only marks deploy
  access verified when the read-only result proves it. A result without deploy
  access remains visible and offers the existing deployment diagnostic as an
  optional later action, without restarting pairing or re-reading the target.
  Node syntax checks, focused UI/route tests, and full local pytest recorded
  `543` tests with `0` failures and `0` errors. No SSH, VPS, remote-container,
  deployment, network, or production operation was performed. This is `LOCAL`
  evidence only.
- **LOCAL 2026-07-29:** browser-checked the current local Lab on a separate
  loopback port. The visible credential-panel primary action says `Run
  read-only check` and invokes only the bounded discovery route, matching the
  novice guide. No target was selected, no credential was submitted, and no SSH
  or VPS request was made during this browser check.
- **LOCAL 2026-07-29:** closed the gap between the L2 read-only discovery
  approval plan and the SSH command executor. The discovery route now passes
  its request-scoped validated plan into a command guard. Every SSH command is
  mapped to an explicit approved operation before it is sent; current session
  user, OS, CPU, memory, home-directory, runtime, Docker/Compose, listener,
  capacity, and derived container-metadata reads are separately named. Unknown
  command drift is rejected locally before SSH execution. A successful
  approved Docker listing may derive only validated per-container summary,
  mount, ownership-label, and mount-derived directory-size operations. The
  guarded L2 path does not use `sudo` and does not read image digests. Existing
  non-L2 planning behavior remains unchanged. Focused discovery/plan tests
  passed `230`; full local pytest recorded `543` tests with `0` failures and
  `0` errors; Python compile, Node syntax, and diff whitespace checks passed.
  No SSH, VPS, remote-container, deployment, network, or production operation
  was performed. This is `LOCAL` evidence only. The next L2 entry condition is
  the user's browser submission of the temporary SSH credential against the
  already confirmed isolated-development target, followed by exactly one
  guarded read-only discovery request.
- **LOCAL 2026-07-29:** fixed the host-identity-change recovery loop in the
  Extensions onboarding. A mismatch now clears only the browser's session
  credentials and enters a dedicated recovery view; it cannot start another
  pairing, manual probe, or discovery until the user explicitly confirms a
  local reset. The reset API accepts only a saved target ID, atomically clears
  its canonical host-key trust and stale network-verification state, increments
  its identity generation to invalidate unfinished pairing challenges, and
  never contacts the host, receives a credential, or accepts a replacement
  identity. The user must then manually begin a fresh confirmation.
  Store/route/DOM regression coverage passed, including cancelled reset,
  minimal request payload, stale-challenge rejection, and no browser-storage or
  credential disclosure. `node --check` passed for both extension bundles,
  Python compilation passed, `git diff --check` passed, and full local pytest
  passed `541`. A launcher-owned Lab at `http://127.0.0.1:8895/#/extensions`
  served the current source with the reset route present and zero browser
  console errors; no target metadata, credential, host-key probe, SSH test,
  discovery, deployment, or remote command was submitted. This is local
  UI/API/test evidence only, not isolated-VPS, SSH, container, deployment, or
  production evidence. The pre-existing `8892` runtime did not expose this
  route and was left running unchanged.
- **LOCAL 2026-07-29:** added a fail-closed L2 read-only discovery-plan gate.
  `scripts/validate_discovery_plan.py` accepts only a secret-free,
  target-bound `read-only-discovery` authorization, matching expected/observed
  canonical SSH host-key identity, and fixed allowlisted operations. It rejects
  arbitrary shell text, target or host-key drift, unknown labels, unsafe
  container identifiers, and non-canonical paths. Its output names only an
  approved scope/role and operation identifiers, or an invalid field; it does
  not echo host identities, fingerprints, paths, or credentials. Focused plan
  and extension tests passed `199`; the full local pytest suite, Python compile
  check, and diff whitespace check passed. This is local validation tooling,
  not SSH, VPS, container, discovery, deployment, private-network, or
  production evidence.
- **LOCAL 2026-07-29:** the Extensions environment-discovery route now creates
  a request-scoped L2 approval record, re-reads the saved target's SSH host key
  without authentication, and validates the fixed read-only plan before it
  supplies the session credential to the existing discovery code. A changed
  host key or rejected plan stops before discovery. The record is never
  persisted, returned to the browser, or written to task/instance state.
  Focused plan and extension tests passed `203`. This route coverage uses
  mocks only; no SSH, VPS, container, deployment, private-network, or
  production action was performed.
- **LOCAL 2026-07-29 browser verification:** an independently launched,
  launcher-owned Lab loaded commit `e493fcc` and served `#/extensions` with
  the Extensions page visible and zero browser-console errors. The runtime
  identity matched that commit. No target metadata, pairing material,
  credential, SSH test, host-key probe, environment discovery, deployment, or
  network request was submitted. This is browser startup evidence only, not
  isolated-VPS or production evidence.
- **VERIFIED 2026-07-23:** GenBox commits `997e78c`, `5394c42`, and `72edab0`
  locally implement the novice-oriented trusted SSH-session pairing path on top of
  Deployment Safety Contract v3. The saved trust record remains the canonical
  SSH host-key algorithm plus `SHA256:` fingerprint pair; pairing does not
  replace SSH credentials or mandatory host-key verification.
- **VERIFIED 2026-07-23:** focused and full local verification completed with
  `501 passed`. Independent fixed-commit architecture, security, and regression
  reviews each returned **APPROVE**. This is local evidence only.
- **VERIFIED 2026-07-23:** local Docker preflight succeeded from image
  `genbox-p4-local:dae8d84`
  (`sha256:62120b3124bf05c5eff4b85f7211804804bbcf617258460bbc8bc4aebe17680`).
  The isolated container was exposed only on `127.0.0.1:18991`, passed its
  Docker healthcheck, and returned `/api/setup/status` with production
  authentication enabled. A temporary 1x1 PNG Push returned `imported`; the
  identical retry returned `already-imported` with the same SHA-256. This proves
  local receiver build/startup, authenticated Push, and idempotency only; it is
  not VPS, private-network, browser, sender, or production evidence.
- **VERIFIED 2026-07-22:** chatgpt2api sender implementation exists at
  `f4a327d5599b020c66d4aab041a5fa0035d5effe`. Its existence does not prove the
  GenBox receiver/deployment candidate or an end-to-end transfer.
- **UNVERIFIED:** a real isolated-VPS, browser-driven, single-image Push end to
  end. No local/mock test, status panel, plan, or sender commit substitutes for
  an authenticated receipt, matching SHA-256, metadata result, idempotent retry,
  source-retention result, and production non-mutation check.
- **VERIFIED 2026-07-23:** production chatgpt2api remains outside the mutation
  scope. Host, port, container, and credential facts are intentionally absent
  without fresh dated discovery evidence.
- **USER-CONFIRMED / BLOCKED 2026-07-27 (L2):** the user identified the selected
  target as an isolated development machine and authorized a bounded
  `read-only-discovery` SSH check. The local client established SSH transport,
  but the server closed the session before current host-key validation or user
  authentication. No discovery command, container action, deployment, or
  mutation ran. This does not prove the current host identity, isolation,
  ownership, Docker/Compose state, ports, mounts, capacity, or health. L2
  remains blocked pending an SSH service/policy correction on the isolated
  development machine and a fresh host-key validation.
- **LOCAL 2026-07-27:** GenBox now classifies an SSH session closed by the server
  separately from authentication rejection and protocol negotiation failure.
  The UI instructs the user to keep the current identity and credential views;
  it does not send the user back to pairing or request another confirmation
  code. Focused extension suites passed `178` and `119` tests; the full local
  suite passed `511`. No target identifiers, fingerprints, credentials, or raw
  SSH errors are stored in this record.
- **LOCAL 2026-07-27:** the prior transport-close result was traced to an RSA
  host-key negotiation mismatch in GenBox. The saved canonical `ssh-rsa` key
  type and SHA-256 fingerprint remain mandatory, while the SSH client now
  negotiates that same RSA key through `rsa-sha2-512` or `rsa-sha2-256`.
  A real local AsyncSSH RSA server passed password authentication and exact
  fingerprint verification. This is not isolated-VPS proof; the next user-run
  connection check is still required before L2 discovery can begin.
- **LOCAL 2026-07-27:** duplicate saved-target recovery now reuses an existing
  normalized SSH endpoint on browser metadata save and shows one canonical
  record per endpoint in the beginner UI without deleting or replacing stored
  host trust. The deployment form now withholds instance name, service port,
  and image until the read-only environment check returns. The Step 2 transition
  now restores the one-action guide, so a successful SSH check exposes the
  read-only environment check instead of a blank waiting state. Focused
  extension tests passed `183`; the full local suite passed `516`; local
  browser verification at `http://127.0.0.1:8892/#/extensions` confirmed those
  three fields were hidden before discovery. No pairing, credential submission,
  SSH, VPS, remote container, production, or deployment operation was
  performed.
- **LOCAL 2026-07-29:** an isolated empty deployment now requires an immutable
  OCI image reference in the form `registry/name@sha256:<64 hex digest>` before
  GenBox starts environment discovery. The browser leaves the image value empty
  and explains that a local Docker tag or `latest` cannot be pulled by another
  machine. The API repeats the same check before SSH discovery, while existing
  instance registration and source-clone workflows retain their supported paths.
  This prevents a plan that is guaranteed to fail because the specialized sender
  image exists only on the developer machine.
- **Verification:** extension-focused tests passed `342`; the full local suite
  passed `520`; `node --check static/js/extensions.js`, `node --check
  static/js/i18n.js`, and `git diff --check` passed. The current-worktree local
  service at port `8894` returned HTTP 200 and served the empty image field plus
  its digest help. Prior local browser inspection of that same current-worktree
  page confirmed the field, accessible help linkage, Chinese copy, and zero
  browser console errors. This is `LOCAL` UI/API evidence only: no registry
  artifact was published, and no SSH, VPS, remote container, deployment, or
  production action was performed.
- **Next local entry:** define a reproducible, sanitized delivery path for the
  specialized sender image. Before building or publishing that artifact, resolve
  the sender-side transfer-coordination findings: configuration-version cache
  invalidation, metadata-conflict handling, and canonical path identity.
- **LOCAL 2026-07-29 sender image preflight:** the current sender revision was
  rebuilt from its repository Dockerfile with locally cached base images, then
  exercised with the disposable Docker-only sender/receiver smoke harness. The
  synthetic first Push imported once, the identical retry was idempotent, and
  the sender retained its source file. The harness published no ports and
  removed its labeled temporary resources. This is not a registry artifact,
  clean-machine build, isolated-VPS, private-network, or production result.
- **LOCAL 2026-07-29 image prerequisite guidance:** after a read-only
  environment check, an isolated empty deployment without an immutable image
  reference now directs the beginner to the image field instead of offering a
  plan action that will fail. The focus action performs no request. Focused
  extension tests passed `187`, and the full GenBox suite passed `520`. This is
  local UI evidence only and involved no registry, SSH, VPS, or deployment.
- **VERIFIED 2026-07-29 GHCR artifact:** the experimental repository
  `liwei9745/chatgpt2api-genbox-p4` completed its explicit, manual-only
  GitHub Actions image publication run. GitHub Packages reports the published
  multi-architecture manifest reference as
  `ghcr.io/liwei9745/chatgpt2api@sha256:f3091475b298749e97e58051574850d63b9a63bf12b54cb74b468f5020a32c5a`.
  The human-readable `sha-c3cabf9` tag is build metadata only; GenBox must use
  the digest reference. This is registry artifact evidence, not SSH, VPS,
  remote-container, deployment, receiver, or end-to-end Push evidence.
- **LOCAL 2026-07-29 sender build-context containment:** the sender's
  `.dockerignore` now excludes local environment files, runtime configuration,
  data, generated media, logs, databases, and private-key file types before
  Docker receives the build context. Sender unittest discovery passed `47`; a
  new local Docker build completed with the protected paths excluded from its
  small build context. That rebuilt sender then passed the disposable local
  sender/receiver smoke: first import, idempotent retry, and source retention
  all succeeded without published ports. This is a local build/sanitization
  check only, not a clean deployment, VPS, or cross-project transfer result.
- **LOCAL 2026-07-29 digest acceptance regression:** a minimal DOM execution
  test now covers the actual front-end plan gate: a pinned GHCR reference is
  accepted, while a mutable `latest` tag shows the recovery message, moves focus
  to the image input, and makes no request. The backend independently rejects a
  mutable empty isolated deployment before SSH discovery. `python -m pytest -q
  tests/test_extensions.py` passed `188`; full local `python -m pytest -q`
  passed `521`; `node --check static/js/extensions.js`, `node --check
  static/js/i18n.js`, and `git diff --check` passed. The local extensions page
  at `http://127.0.0.1:8892/#/extensions` was inspected without submitting or
  changing any saved target, credential, plan, or connection. This is LOCAL
  UI/test evidence only.

## Phase 4 boundary

Phase 4 is not complete. Its acceptance is phase-scoped: one newly generated
image from an isolated development clone imports once with available metadata;
retry is idempotent; failure retains the source; relevant receiver and sender
tests pass. Batch/scheduling are Phase 5. Cleanup is Phase 6. Clean GitHub
redeployment and upstream/release publication are separate authority and
completion gates.

The receiver-only requirement-by-requirement evidence matrix is maintained in
`docs/P4-SINGLE-IMAGE-PUSH-LOCAL-EVIDENCE.md`. It explicitly separates LOCAL
receiver proof from sender, isolated-VPS, and production claims.

## Local sender per-generation workflow (2026-07-24)

- **Evidence class:** `LOCAL` only. After explicit user authorization, the
  separate dirty `chatgpt2api-dev` worktree was preserved and updated in place;
  no existing dirty changes were discarded.
- **Implementation:** Studio result cards now expose a per-image
  `Push to GenBox` action only when a local relative image path is available.
  The UI reports generation and transfer independently, locks the action while
  uploading, supports idempotent retry, and reports failure with source-retained
  recovery guidance. No API key, receipt body, or image bytes are rendered or
  persisted by the Studio state.
- **Protocol gate:** the sender sends `source_sha256`, requires receiver
  `contract_version: v1` and a positive `max_image_bytes` probe, and accepts a
  Push only when the v1 receipt SHA-256 matches the uploaded bytes.
- **Verification:** sender focused tests -> `12 passed`; sender local full
  pytest -> `12 passed`; `web-vue` `npm run build` passed; `git diff --check`
  passed. Tests use only local mocks and a test-only process environment value.
- **Browser:** local GenBox lab at `http://127.0.0.1:8892/#/extensions`
  loaded with title `GenBox`, zero page errors, and `scrollWidth=390` at a
  390px viewport. This is local page/responsive evidence only; no pairing,
  SSH, Push, or credential action was submitted.
- **Sender browser smoke:** local Vite at `127.0.0.1:5173` used only
  Playwright-routed mock API responses. A synthetic completed image exercised
  the per-generation button through pending, success, and retry/source-retained
  failure states; captured Push requests contained only the expected relative
  path, with zero page errors and `scrollWidth=430` at a 430px viewport.
  This remains LOCAL UI/mock evidence, not live cross-project E2E.
- **Boundary:** no SSH, VPS, remote container, production instance, network
  deployment, or live sender-to-GenBox request was performed. Sender changes
  are committed separately at `78135e1` and `0320b62`; this local evidence does
  not upgrade isolated VPS or cross-project E2E status.
- **Secret/data boundary review (2026-07-24):** `LOCAL` only. The sender's
  GenBox Push settings API continues to mask the Push key before returning
  settings, and the Studio stores only per-image UI status in page memory.
  The receiver accepts only source-scoped Push authentication and verifies the
  sender-provided SHA-256 against uploaded bytes. The review found that a
  transport exception could otherwise be copied into a retry receipt or batch
  result; sender commit `041a2ce` replaces those raw exception strings with
  fixed recovery messages while retaining safe HTTP status categories,
  idempotency, SHA-256 receipt validation, retry state, and source retention.
  Focused and full sender pytest each passed `14` with a test-only process
  value; `web-vue` production build and `git diff --check` passed. New tests
  assert synthetic sensitive exception fragments do not reach a receipt,
  batch response, or connection error. No image bytes, Push key, raw receipt,
  or live network request was used.

## Exact next step

For a local-only UI check, enter the verified immutable GHCR reference into the
isolated-deployment image field and confirm GenBox accepts the digest format.
Do not generate a remote plan or start a deployment from that check. The next
remote gate remains separately authorized isolated-development discovery and
host-key validation; do not treat the registry artifact or local UI/tests as
VPS or production verification.

## Phase 5 sender local batch and schedule work (2026-07-29)

- **Evidence class:** `LOCAL` only. The separate sender worktree now has a
  durable manual batch service for Gallery selections and server-indexed date
  range previews. Items persist only a relative path, SHA-256, status, attempt
  count, timestamps, and a fixed recovery message. Source images are retained;
  no cleanup path was added.
- **Scheduled local behavior:** the sender has a disabled-by-default weekly
  schedule with optional date bounds, an overlap scan cursor, a short durable
  worker lease protected by an atomic cross-process lock, and no more than three
  automatic retries for a failed scheduled item. All scheduled sends enter the
  existing batch service, and single-image, batch, and scheduled paths now share
  an in-process content-identity coordinator so matching in-flight
  `(relative_path, SHA-256, metadata)` requests share one physical send. A
  metadata conflict is surfaced for retry instead of being silently discarded.
  This is not
  isolated-VPS, private-network, receiver, or production evidence.
- **Verification:** `LOCAL` sender unittest discovery passed 43 tests on
  2026-07-29, including focused coordinator coverage for concurrent outbox and
  batch delivery, retry-after-failure, changed-source refusal, path aliases,
  metadata conflicts, secret-safe result handling, and a real scheduler plus
  manual-batch contention path. The Vue production build and `git diff --check`
  also passed.
  Tests use synthetic relative paths and in-memory image bytes only. No real
  VPS, SSH credential, Push key, or external network was used.
- **Local Docker smoke:** `LOCAL` only. The current sender revision built from
  the repository Dockerfile with cached local base images and an explicit tag.
  Its disposable internal-network harness passed the v1 probe, two concurrent
  matching synthetic requests with one physical sender call, first import,
  receiver idempotent retry, SHA-256 receipt, source retention, and recovery of
  a batch item persisted as `sending` after the receiver had already accepted
  its image. It published no ports and cleanup left no run-labeled containers,
  networks, or generated credential files. This is not a VPS, clean-machine,
  registry, or production verification.
- **Browser verification:** `LOCAL` mock only. A standalone standard-library
  mock API accepts one fixed test-only bearer value and serves fixed synthetic
  Gallery records without importing sender application code or reading `data/`,
  configuration, real media, or credentials. Through local Vite, browser checks
  completed login, multi-select, source-retention confirmation, batch progress,
  cancellation of queued items, failed-only retry, progress-panel close,
  date-range preview, weekly schedule save, and run-now feedback. At a narrow
  viewport, the inspected page width had no horizontal overflow. This is a UI
  contract check only: it does not prove a receiver, Docker, VPS, private
  network, real image, remote generation, or production behavior.
- **Next local entry:** retain this sender image and smoke harness as the local
  Phase 5 baseline. The next verification gate is a separately authorized
  isolated-VPS clone; keep Phase 5 marked planned until that evidence is
  recorded. The coordinator is intentionally an in-process guarantee and is not
  evidence of multi-process or isolated-VPS behavior.

## Phase 5 local transfer configuration binding follow-up (2026-07-29)

- **Evidence class:** `LOCAL` only. The sender now captures one in-memory,
  non-persisted destination configuration context before deriving its in-flight
  transfer key. The physical send receives that same context and rejects the
  request before any receiver probe or upload if the configured destination
  changes in the gap. The source remains retained and the caller retries under
  the new configuration. The context is not returned by an API, written to
  outbox/batch/schedule state, or logged.
- **Verification:** local sender unittest discovery passed `45` tests,
  including focused coverage for a configuration rotation before send and
  coordinator-to-service context forwarding. Python compilation for the two
  changed sender services, Vue production build, and `git diff --check` passed.
  A newly built local sender image passed the disposable internal-network Push
  smoke with v1 probe, initial import, idempotent retry, matching-request
  coordination, source retention, and interrupted batch recovery. No ports
  were published; the harness uses generated test-only credentials and removes
  its labeled containers, network, and temporary files.
- **Boundary:** no VPS, SSH, remote container, registry publish, real
  credential, user image, or production action was used. This strengthens the
  local Phase 5 sender guarantee only and does not complete isolated-VPS or
  cross-project acceptance.
- **Next local entry:** keep the sender/receiver image tags explicit, run the
  same local smoke after future transfer changes, and wait for a separately
  authorized isolated-VPS clone before advancing the Phase 5 evidence gate.

## Local deployment-plan review summary (2026-07-29)

- **Evidence class:** `LOCAL` only. After a plan is generated, the extension
  UI now renders a review summary from the same non-secret request snapshot:
  instance name, service port, image, deployment mode, and whether the plan is
  for a new isolated instance or local registration of an existing one. The
  summary explicitly states that the separate `Confirm and deploy` action is
  still required. Host identity, paths, credentials, fingerprints, raw
  discovery data, and plan evidence internals remain outside the preview.
- **Verification:** focused extension UI contract tests passed `2`; extension
  task-store regression tests passed `119`; full local pytest passed `517`.
  Both modified browser scripts passed Node syntax checks. A fresh local browser
  page at `#/extensions` loaded with zero page errors; it did not submit
  credentials, SSH tests, discovery, plan creation, or deployment.
- **Boundary:** this makes a locally rendered plan reviewable, but it is not
  isolated-VPS deployment evidence and it does not authorize or start a
  deployment. Any pre-existing page must be reloaded and a fresh plan generated
  to render the new summary.
- **Next local entry:** after reviewing the summary, keep a custom image
  reference limited to a registry the isolated development machine can reach;
  changing image, port, or instance invalidates the old plan and requires a
  fresh review before deployment.

## Read-only discovery target-role gate (2026-07-24)

- **Evidence class:** `LOCAL` only. The extension target form now requires an
  explicit server-purpose field: `isolated-development` or
  `production-read-only`. Existing target records without this field are
  loaded conservatively as `production-read-only`; new targets default to the
  read-only choice until the user explicitly selects otherwise.
- **Behavior:** the selected role is saved with the target. Read-only discovery
  remains available for either role, while deployment-plan generation is
  rejected unless the saved target role is `isolated-development`. The role is
  a local authorization label, not proof of ownership or VPS isolation.
- **Verification:** `python -m pytest -q` -> `506 passed`; focused extension and
  discovery tests -> `195 passed`; `node --check static/js/extensions.js`;
  `node --check static/js/i18n.js`; `git diff --check` all passed. Local browser
  page `http://127.0.0.1:8892/#/extensions` rendered both purpose options and
  no horizontal overflow at the observed viewport. No target role was changed
  or saved in the browser, and no SSH, VPS, remote container, production, or
  deployment action was performed.
- **Next local action:** choose `隔离开发机（推荐）` for the intended isolated
  development target and press `保存`; then re-open the target and confirm the
  saved role before preparing the redacted read-only discovery plan.

## Host identity mismatch recovery (2026-07-24)

- **Evidence class:** `LOCAL` only. When local UI SSH testing receives the
  backend diagnostic `ssh_host_key_mismatch`, the page now stops the flow,
  clears the current session credential fields, discards discovery and plan
  state, and returns to Step 1. It does not display or persist the fingerprint,
  host-key algorithm, raw SSH response, password, or private key.
- **Recovery:** the novice guide explains that the saved server identity no
  longer matches and exposes a single `重新开始` action for the existing
  trusted-terminal confirmation flow. A new pairing must complete before any
  SSH credential test; the backend remains responsible for re-probing,
  algorithm allowlisting, SHA-256 validation, and compare-and-swap persistence.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; `git diff --check`; full local pytest -> `506 passed`.
  Browser inspection of `http://127.0.0.1:8892/#/extensions` was read-only after
  reload; no pairing, SSH, VPS, remote container, production, or deployment
  action was performed.

## Pairing Progress Clarity (2026-07-26)

- **Evidence class:** `LOCAL` only. Review of the pairing completion state
  found no repeat-pairing transition: a completed server identity confirmation
  intentionally remains in Step 1 until an SSH credential test succeeds. The
  prior generic guide sentence said it would move to the next step, which made
  this required credential stage appear to be a loop.
- **Fix:** when the identity is confirmed but no session credential is present,
  the guide now explicitly says that the user remains in Step 1 to test SSH and
  that Step 2 opens only after a successful test. The change does not alter
  host-key verification, credential lifetime, pairing, or any remote action.
- **Verification:** focused extension tests passed locally. No pairing, SSH,
  VPS, remote container, production, or deployment action was performed for
  this review.

## Server Connector Direction, SSH Mainline Preserved (2026-07-27)

- **Evidence class:** `LOCAL` only. The Extensions page now makes the intended
  beginner-facing product direction visible: `服务器连接器（推荐）` is explicitly
  marked `准备中`, while `SSH 连接（高级方式）` is explicitly marked `当前可用`.
  This is an honest route selector, not a connector implementation, enrollment,
  authenticated transport, provider OAuth connection, VPS connection, or
  deployment result.
- **Mainline preservation:** the only active action is `使用 SSH 继续`. It focuses
  the existing Step 1 target form and then retains the current deploy-capable
  sequence unchanged: save target, confirm host identity, supply a transient
  SSH credential, test access, run read-only discovery, and prepare the bounded
  safety plan. The fallback action creates no API request, target, credential,
  pairing, SSH, network, or deployment operation. The unavailable connector
  cannot block or replace this path.
- **Design boundary:** `docs/P4-SERVER-CONNECTOR-UX-STRATEGY.md` and ADR-020
  specify that a real connector needs an installable agent, identity and
  enrollment lifecycle, authenticated outbound transport, signed
  capability-scoped intents, allowlisted agent operations, redacted audit
  events, and local/isolated-VPS evidence before it can become deploy-capable.
  No web terminal is added; browser requests still cannot submit arbitrary
  remote shell commands. Generic OAuth is not treated as an SSH replacement.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; focused `python -m pytest tests/test_extensions.py -q`
  -> `175 passed`; full `python -m pytest -q` -> `507 passed`; and `git diff
  --check` passed locally. Local browser verification at
  `http://127.0.0.1:8892/#/extensions` confirmed the SSH fallback focuses the
  target form, shows its local guidance, produces no relevant page error, and
  has no horizontal overflow at a 390px viewport. No form was submitted and no
  pairing, SSH, VPS, remote container, production, OAuth, or deployment action
  was performed.

## Host Identity Before SSH Credential UX (2026-07-27)

- **Evidence class:** `LOCAL` only. The Step 1 credential area no longer stays
  visible while a saved server has no confirmed host identity, including the
  `ssh_host_key_mismatch` recovery state. The page now shows one clear recovery
  card: the session credential was cleared, confirm the server identity first,
  then enter a password or private key. The hidden area includes the password,
  private-key, sudo, and credential-notice controls.
- **Security and flow:** a host-key mismatch continues to clear all session
  credentials, discovery, plan, and SSH verification state before returning to
  Step 1. Saving a target whose identity is not yet confirmed also clears any
  credential entered prematurely. The credential controls return only after
  canonical host identity confirmation. No password is restored, represented as
  masked text, persisted, logged, or reused across the identity-confirmation
  boundary.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; focused `python -m pytest tests/test_extensions.py -q`
  -> `176 passed`; and `git diff --check` passed locally. The local Extensions
  page reloaded at `http://127.0.0.1:8892/#/extensions` without horizontal
  overflow. Browser verification did not save a target, submit a pairing,
  submit a credential, or attempt SSH, VPS, remote-container, production, or
  deployment access.

## Personal Server Onboarding Redesign (2026-07-27)

- **Evidence class:** `LOCAL` only. The user-visible `连接服务器` mega-step has
  been removed from the initial deployment experience. The entry is now
  `开始部署`: it honestly presents `服务器连接器（推荐）` as unavailable and
  `使用 SSH 设置服务器` as the current working compatibility path. This does not
  implement a connector, OAuth flow, VPS connection, SSH pairing, or deployment.
- **Flow:** the SSH path now renders one exclusive view at a time: server
  details, server identity confirmation, temporary credential check, then a
  ready-to-plan state. A changed server identity clears session credentials and
  stays in its own recovery view; credentials are neither shown as masked text
  nor persisted. The existing discovery, safety-plan, deployment, and network
  sequence remains behind the verified SSH gate.
- **Safety baseline:** canonical SSH host-key algorithm plus `SHA256:`
  fingerprint verification, fail-closed identity changes, session-only
  credentials, backend-owned fixed operations, production read-only treatment,
  isolated-development deployment gate, and receipt-gated source retention are
  unchanged. Personal-use language now hides technical identity details from
  the normal path without weakening those controls.
- **Research and decisions:**
  `docs/P4-PERSONAL-SERVER-ONBOARDING-UX-STRATEGY.md` records applicable public
  product references and the new state model. ADR-021, the SSH pairing strategy,
  the deployment contract, and deployment invariants now distinguish a personal
  safety baseline from enterprise-oriented presentation.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; `git diff --check`; focused
  `python -m pytest tests/test_extensions.py -q` -> `177 passed`; full
  `python -m pytest -q` -> `509 passed`. Local browser
  `http://127.0.0.1:8892/#/extensions` loaded the revised entry, opened only the
  server-details view after its SSH action, kept identity and credential views
  hidden, reported no page errors, and had no horizontal overflow at the
  checked desktop and 390px layouts. No target was saved and no SSH, VPS,
  remote-container, production, OAuth, pairing, or deployment action ran.
- **Next local entry:** keep L2 paused. Reopen the local Extensions page to
  review the static onboarding states only. A real server connector requires its
  own implementation milestone for installable agent, enrollment, authenticated
  outbound transport, revocation, capability allowlists, and local tests; it
  must not block the current SSH deployment mainline.

## SSH Host-Key Algorithm Pinning (2026-07-27)

- **Evidence class:** `LOCAL` only. A likely false mismatch loop was found in
  the SSH compatibility path: host identity pairing probes one algorithm, while
  the later authenticated AsyncSSH connection could negotiate a different
  algorithm offered by the same server. That made a multi-key server look like
  a changed server after a successful pairing.
- **Fix:** the authenticated SSH connection now offers only the saved canonical
  host-key algorithm. The callback still verifies both that algorithm and its
  SHA-256 fingerprint. If the server no longer offers that algorithm, the
  result remains fail-closed and is classified as a host-identity mismatch;
  unrelated secure-negotiation failures remain distinct.
- **Verification:** focused extension tests -> `177 passed`; extension task
  store tests -> `118 passed`; full `python -m pytest -q` -> `509 passed`;
  `python -m py_compile extensions/orchestrator.py`; `git diff --check`.
  Local browser reload at `http://127.0.0.1:8892/#/extensions` rendered the
  revised entry without page errors or horizontal overflow. No credential,
  pairing response, real SSH, VPS, remote container, production, or deployment
  action was submitted.
- **Limit:** this removes the local algorithm-negotiation false positive. If a
  future check still reports a mismatch, GenBox must remain stopped because the
  server identity may genuinely have changed; do not repeat password or pairing
  entry until its trusted source is checked.

## Resume constraints

- Require SSH host-key verification; production is read-only and all development
  resources must be isolated.
- Trusted SSH-session pairing is implemented locally and independently reviewed,
  but its external trusted terminal/known-host record remains an initial trust
  anchor, not VPS ownership evidence or an SSH credential substitute. Do not
  record its challenge, response, command, raw pairing observations, or
  credentials in persisted/public state, logs, browser storage, screenshots,
  URLs, or Git. The canonical trust pair is the only permitted saved outcome.
- Keep administrator, Push, management, SSH, and enrollment secrets separate
  and out of URLs, browser storage, Git, ordinary logs, screenshots, and status
  text.
- Source deletion remains disabled unless an authenticated receipt, matching
  SHA-256, `safe_to_delete_source=true`, and explicit user opt-in all exist.
- Record any later isolated-E2E evidence as **VERIFIED**, **USER-CONFIRMED**, or
  **UNVERIFIED** as appropriate; never describe local evidence as real E2E.

## L2 loop result (2026-07-23)

- **Evidence class:** `UNVERIFIED` / blocked before remote I/O.
- **Commands/results:** `git rev-parse HEAD` -> `00be081feb12525e783d0b6e0547cd654fe40999`; `git status --short --branch` -> clean on `codex/p4-deploy-plan-ux-eai`; `git diff --check` -> clean; local `ssh -V` -> OpenSSH_for_Windows_9.5p1; local Docker client -> `29.6.1`. No remote command ran.
- **Risk:** connecting without a confirmed canonical fingerprint could reach a production or wrong-owner host. Runtime target metadata is ignored, untrusted input and contains no host-key confirmation.
- **Blocker:** missing user-confirmed isolated-target identity and canonical SSH algorithm/fingerprint pair; SSH credential/authorization is not established in this repository.
- **Next loop entry:** after the user confirms the isolated development clone, its owner/scope, and the canonical host-key pair, run only the approved read-only SSH discovery set and capture secret-free output. Do not start L3 until that evidence proves source/clone separation and a bounded rollback target.

## Local verification loop (2026-07-23)

- **Evidence class:** `LOCAL` only. L2 is paused; no SSH, VPS, remote
  container, production, or network deployment action was performed.
- **Docker:** local `genbox-p4-local` image `genbox-p4-local:dae8d84` is
  `running`, Docker health is `healthy`, restart count is `0`, and the local
  endpoint returned HTTP 200 from `/api/setup/status`. Non-sensitive status
  fields reported `app_mode=prod`, `auth_required=true`, and provider setup
  still required.
- **UI:** local `/` returned HTTP 200 with the extension-center and Push UI
  resources present; `node --check static/js/extensions.js` passed. This is
  local page/resource and contract evidence, not browser E2E evidence.
- **Push/failure coverage:** the focused sync, Push-route, and extension suite
  passed `201` tests. It covers authenticated import, idempotent retry,
  authentication rejection, invalid-image rejection, transport/error handling,
  and source-retention assertions. No source-cleanup behavior was enabled.
- **Full local tests:** `python -m pytest -q` -> `486 passed in 10.38s`.
- **Risk/gap:** a real browser automation run and live sender-side transfer
  remain unverified; local tests do not prove isolated-VPS or production
  behavior.
- **Next local entry:** keep the receiver contract frozen and, if browser
  tooling is explicitly added, run a local-only browser smoke test against the
  existing container before reopening L2. Otherwise the next remote gate
  remains separately authorized isolated-VPS discovery.

## Local browser smoke loop (2026-07-23)

- **Evidence class:** `LOCAL` only. Chrome was launched against the existing
  local container at `127.0.0.1:18991`; no SSH, VPS, remote container,
  production, or deployment action was used.
- **Browser result:** Playwright `1.61.0` with local Chrome loaded `/` with
  HTTP 200 and no page errors. The page title was `GenBox` and
  `#navExtensions` was present.
- **Extension workflow:** invoking the existing `switchNav('extensions', ...)`
  made `#pageExtensions` visible. The five-step deployment flow rendered its
  target save, host-key pairing, SSH test, environment discovery, safe-plan,
  and deployment controls. The deployment controls remained gated according
  to missing target/trust state; no action was submitted.
- **Push boundary:** the deployment page did not expose a browser Push action
  in this unauthenticated local state. Push receiver behavior remains covered
  by the 201 focused tests, 486 full tests, and prior local Docker preflight;
  this smoke run does not claim browser Push E2E.
- **Next local entry:** keep this browser smoke as the local UI baseline. Any
  further browser work must remain pointed at `127.0.0.1:18991` and avoid
  credential submission or deployment actions; L2 remains paused.

## Authenticated browser smoke and fix (2026-07-23)

- **Evidence class:** `LOCAL` only. A fresh local image was built as
  `genbox-p4-local:login-fix` and run temporarily on `127.0.0.1:18992` with
  the existing local Docker environment file. The temporary container was
  removed after verification; the baseline `genbox-p4-local` container stayed
  running and healthy.
- **Finding/fix:** wrong-key browser login previously kept `#loginError`
  hidden because `.hidden { display: none !important }` overrode the inline
  style. `_setLoginError()` now toggles the `hidden` class in both
  `static/js/app.js` and `static/js/app-all.js`.
- **Browser result:** wrong key kept the login page visible and showed the
  error (`display=block`, `hidden=false`). The local admin key then logged in
  successfully and exposed the extension navigation. No deployment, SSH, or
  remote action was submitted; credentials remained in process memory only.
- **Verification:** `python -m pytest tests/test_setup_security.py -q` -> `39
  passed`; `node --check` passed for both bundles; full `python -m pytest -q`
  -> `486 passed in 11.11s`.
- **Next local entry:** use the authenticated browser baseline for any further
  local UI checks. The deployment wizard and Push receiver remain gated by
  their existing contracts; L2 stays paused until separately resumed.

## Server confirmation-code UX and local verification (2026-07-24)

- **Evidence class:** `LOCAL` only. The revised
  `docs/P4-HOST-KEY-PAIRING-UX-STRATEGY.md` makes the novice-facing task
  “确认这台服务器”: generate a short-lived confirmation, copy the fixed helper
  to an already trusted terminal, paste the confirmation code, then confirm.
  Users do not need to read or compare algorithms, fingerprints, or protocol
  prefixes; manual verification remains an advanced recovery path.
- **Security boundary:** the start response no longer returns the candidate
  host-key algorithm or fingerprint to the browser. The fixed helper produces
  a one-time confirmation code plus an identity-bound digest proof, not a raw
  fingerprint; the pasted value is immediately removed from the input and held
  only in page memory until submission. Backend algorithm allowlisting, full
  `SHA256:` comparison, single-use expiry, target binding, re-probe, and CAS
  persistence remain unchanged.
- **Verification:** Node syntax checks passed for `static/js/extensions.js` and
  `static/js/i18n.js`; Python compilation passed; focused pairing tests passed
  `288`; full `python -m pytest -q` passed `502`; `git diff --check` passed.
  Node DOM mocks cover copy, confirmation-code hiding, one-time submit,
  control locking, success cleanup, expiry, restart, and response redaction.
- **Browser result:** the local lab at `http://127.0.0.1:8892/#/extensions`
  loaded with title `GenBox`, rendered the confirmation-code copy without the
  raw protocol prefix, and reported no browser errors. At `390px` width,
  `scrollWidth` equaled the viewport width. No target was saved or selected for
  pairing, no confirmation was generated, and no SSH, VPS, remote container,
  production, or network deployment action was attempted.
- **Recovery follow-up:** the default panel now exposes “没有已登录终端？”
  before a pairing attempt. Local browser evidence used a temporary TEST-NET
  target, expanded the help, opened the advanced manual path, and confirmed
  keyboard focus moved to that path; Escape returned focus to the help button.
  The temporary target was deleted afterward. This path only changes local UI
  state and did not start host probing, SSH, pairing, or remote work. Focused
  tests now cover its ARIA relationship, Escape behavior, and absence of an SSH
  endpoint call in the handler.
- **Novice-guide alignment (2026-07-24):** `LOCAL` only. After target save, the
  guide now presents "Start server confirmation" and starts only the
  confirmation-code path; it no longer labels that primary action as reading a
  host fingerprint. While a confirmation is active, the guide directs the user
  to copy, run, and paste the code rather than allowing a second start. Cancel,
  expiry, and a rejected submission restore the restart action. The manual
  host-key flow remains an advanced recovery path and the backend canonical
  algorithm plus `SHA256:` comparison is unchanged.
- **Verification:** Node syntax checks passed for `static/js/extensions.js` and
  `static/js/i18n.js`; focused pairing/guide tests passed `4`; full
  `python -m pytest -q` passed `503`; `git diff --check` passed. The new Node
  DOM assertion verifies that the novice button starts pairing without a host
  probe and that cancel restores the start action.
- **Browser result:** the local Lab at `http://127.0.0.1:8892/#/extensions`
  rendered the saved-target guide with the server-confirmation action and the
  no-password/no-private-key explanation. At `390px`, `scrollWidth` equaled
  `innerWidth`. A temporary non-routable local UI target was deleted after the
  check. No confirmation was started, no SSH or VPS action occurred, and no
  credentials, pairing material, remote container, production, or network
  deployment action was used.
- **Keyboard recovery follow-up (2026-07-24):** `LOCAL` only. Cancel, expiry,
  and rejected confirmation submission now return keyboard focus to the visible
  restart control after clearing temporary pairing material. Focused Node DOM
  assertions cover all three recovery paths; the complete local suite passed
  `504`, JavaScript syntax checks passed, and `git diff --check` passed. The
  local Lab browser check loaded `#/extensions` at `390px` with title `GenBox`,
  `aria-live="polite"` on the pairing panel, and no horizontal overflow. No
  target was saved, pairing started, credential entered, or remote action used.
- **Pairing-cancel follow-up (2026-07-24):** `LOCAL` only. The visible
  cancel action now immediately clears page-only pairing material and restores
  the restart control, then sends only the one-time pairing identifier to a
  local cancellation endpoint. The same best-effort local cleanup runs when a
  target is edited or switched, and at browser-side expiry. The endpoint
  discards that transient in-memory record without host probing, target lookup,
  credential input, command input, response input, or disclosure of whether
  the record existed. A direct backend test proves a cancelled record cannot be
  completed or persist trust; the Node DOM mock proves cancellation and target
  editing submit only `pairing_id` and do not call the host-key probe endpoint.
  JavaScript syntax checks passed,
  focused extension suites passed `291`, full `python -m pytest -q` passed
  `505`, and `git diff --check` passed. The local Lab browser check at
  `http://127.0.0.1:8892/#/extensions` had title `GenBox`,
  `aria-live="polite"`, empty pairing fields, no browser errors, and
  `scrollWidth=390` at a `390px` viewport. No pairing was started, no
  credential was entered, and no SSH, VPS, remote container, production, or
  network deployment action was performed.
- **Next local entry:** keep L2 paused. Future local UI work may use mocks and
  the local browser only; do not submit credentials or generate a real pairing
  command. Reopen L2 only after separately verified isolated-target identity,
  canonical host-key trust, and explicit authorization are supplied.

## Local sender contract review (2026-07-23)

- **Evidence class:** `LOCAL` / read-only review. The separate
  `chatgpt2api-dev` worktree contains uncommitted sender changes; no files were
  edited, reverted, staged, or committed there.
- **Observed sender surface:** a shared GenBox Push service, destination
  settings and connection probe, receipt SHA-256 validation, source-retention
  gating, gallery batch Push, and date-range Push are present in the dirty
  worktree. The focused sender service suite passed `8` tests using only a
  test-only process environment value.
- **Gap:** no generation-completion or per-generation single-image Push action
  was found in the reviewed sender UI/runtime. This remains a sender-side
  Phase 4B item and is not implemented or claimed by the GenBox receiver.
- **Boundary:** no sender network request, SSH/VPS action, remote container
  operation, or production mutation was performed. Cross-project E2E remains
  `UNVERIFIED` and L2 remains paused.
- **Next local entry:** obtain explicit authorization before editing the dirty
  sender worktree; then add the per-generation action and focused tests there,
  preserving all existing changes and using only a local/mock receiver.

## Local source-browser loop (2026-07-23)

- **Evidence class:** `LOCAL` only. The local development lab was started from
  commit `f965063` at `http://127.0.0.1:8892`; no SSH, VPS, remote container,
  sender, or production operation was performed.
- **Browser result:** `#/extensions` loaded with title `GenBox`. A temporary
  non-routable `example.invalid` target was used only to expose the pairing
  panel; the two numbered steps, copy-command entry, paste-result entry, and
  explicit submit affordance were present. No pairing command was generated and
  no host probe was submitted.
- **Responsive result:** at a temporary `390x844` viewport the page stayed at
  `scrollWidth=390` with no horizontal overflow. The viewport override was
  reset afterward, and the temporary target was removed through the local API.
- **Residual browser note:** the P4 `extensions.guide_connect_title` warning
  was fixed in `c75488b`; the remaining `prompt.shuffle` and
  `dashboard.no_activity` warnings are outside the P4 contract. No page errors
  were observed.
- **Next local entry:** keep the receiver contract frozen; any further browser
  check must remain local and must not start pairing or submit credentials.

## Local receiver hash-index resilience (2026-07-23)

- **Evidence class:** `LOCAL` only, frozen at commit `dda0ea8`. GenBox now
  records the non-secret source content SHA-256 in receiver-owned PNG metadata
  and restores confirmed hashes from the atomic `SyncManifest` when rebuilding
  the local index after a restart.
- **Integrity boundary:** manifest entries are accepted only when their SHA-256
  is canonical, their file exists, and the resolved file remains inside the
  configured gallery. Standalone or forged image metadata is not trusted as a
  receipt and cannot produce a false `duplicate-local` result.
- **Verification:** the focused sync/Push suite passed `36` tests; the full
  local suite passed `494` tests. Coverage includes index deletion/rebuild,
  cross-path idempotency after rebuild, path confinement, forged metadata
  rejection, metadata retention, and concurrent identical Pushes.
- **Boundary:** this strengthens receiver-side local evidence only. It does not
  implement the sender's per-generation action and does not upgrade the
  isolated-VPS or cross-project E2E evidence.
- **Next local entry:** obtain explicit sender-worktree authorization, preserve
  its existing dirty changes, and use only a local/mock receiver for sender
  development.

## Local receiver hash-index integrity follow-up (2026-07-23)

- **Evidence class:** `LOCAL` only. The receiver now records the SHA-256 of the
  bytes actually written to the gallery in each manifest entry and validates
  that digest before acknowledging `already-imported` or restoring a durable
  source-hash index.
- **Integrity behavior:** a stale persisted index is rehashed and discarded
  when a gallery file changes. A modified file therefore cannot create a false
  `duplicate-local` receipt; the incoming image is imported as a new local
  file. Manifest paths remain confined to the configured gallery. Legacy
  entries without a local digest retain compatibility only when the file bytes
  still match their recorded source SHA-256.
- **Verification:** `python -m pytest -q tests/test_sync_push_routes.py
  tests/test_sync.py` -> `37 passed`; `python -m pytest -q` -> `495 passed`;
  `node --check static/js/extensions.js`, `node --check static/js/i18n.js`,
  and `git diff --check` passed.
- **Boundary:** this is receiver-side local evidence only. It does not add the
  sender's per-generation action, establish an isolated VPS, or provide a
  cross-project/production E2E claim.
- **Next local entry:** keep L2 paused. The next feature still requires
  explicit authorization to edit the separate dirty `chatgpt2api-dev`
  worktree; use only a local/mock receiver there and preserve its existing
  changes.

## Local browser verification after receiver follow-up (2026-07-23)

- **Evidence class:** `LOCAL` only. The repository lifecycle manager started
  the current worktree on `http://127.0.0.1:8892`; no SSH, VPS, remote
  container, production, or network deployment action was performed.
- **Browser result:** local Playwright loaded
  `http://127.0.0.1:8892/#/extensions` with HTTP 200 and page title `GenBox`;
  the extension navigation and page nodes were present. At `390x844`,
  `scrollWidth` equaled `innerWidth` (`390`), so no horizontal overflow was
  observed. The session was unauthenticated and submitted no credentials,
  pairing material, or deployment action.
- **Lifecycle:** the local lab was stopped after the smoke check. This is UI
  loading/responsive evidence only and does not claim browser Push E2E.

## Local Push v1 receipt contract (2026-07-23)

- **Evidence class:** `LOCAL` only. The authenticated Push status probe and
  every successful single-image receipt now declare `contract_version: "v1"`.
  This gives a sender a stable additive compatibility signal without exposing
  credentials or changing the source-retention decision.
- **Verification:** focused sync/Push tests passed `37`; the full local suite
  passed `495`; Python compilation for `main.py`, `sync/ingest.py`, and
  `sync/manifest.py` passed; all four frontend bundle syntax checks passed.
  A local browser smoke at `#/extensions` returned HTTP 200 with zero page
  errors and no narrow-screen horizontal overflow.
- **Boundary:** this is receiver-side contract evidence only. The sender's
  per-generation action, authenticated cross-project transfer, isolated VPS,
  and production non-mutation remain unverified.

## Local legacy manifest integrity follow-up (2026-07-24)

- **Evidence class:** `LOCAL` only. Legacy `SyncManifest` entries that predate
  `local_sha256` are still accepted for compatibility only after the gallery
  file is rehashed and matches their recorded source SHA-256. Missing or
  malformed source hashes fail closed.
- **Verification:** focused sync/Push tests passed `39`; the full local suite
  passed `497`; Python compilation and all four frontend bundle syntax checks
  passed; `git diff --check` passed. A local Playwright smoke at
  `http://127.0.0.1:8892/#/extensions` returned HTTP 200 with zero page errors
  and `scrollWidth=innerWidth=390` at the narrow viewport. The lab was stopped
  afterward.
- **Failure boundary:** an invalid-image rejection is covered locally and
  leaves the receiver gallery, manifest, and content indexes untouched. This
  is not sender-side source-retention or network-failure evidence.
- **Boundary:** this closes a receiver-side local integrity gap only. It does
  not implement the sender's per-generation action or establish isolated-VPS,
  cross-project, or production evidence.

## Local Push limit probe consistency (2026-07-24)

- **Evidence class:** `LOCAL` only. The v1 status probe now reports the same
  process-level image byte limit used by `validate_image_payload`, so a sender
  cannot receive a preflight limit that differs from the active receiver.
- **Verification:** the focused sync/Push suite passed `39`; the full local
  suite passed `497`; Python compilation, all four frontend bundle syntax
  checks, and `git diff --check` passed. Local browser loading at
  `http://127.0.0.1:8892/#/extensions` remained HTTP 200 with zero page errors
  and no narrow-screen overflow; the lab was stopped afterward.
- **Boundary:** this is destination probe/receiver contract evidence only. It
  does not prove sender UI behavior, network reachability, or remote E2E.

## Local sender-hash mismatch gate (2026-07-24)

- **Evidence class:** `LOCAL` only. Push accepts an optional canonical
  `source_sha256` from a sender. When present, GenBox compares it with the
  uploaded bytes before touching gallery, manifest, or content indexes; absent
  values remain compatible with existing v1 senders.
- **Verification:** focused sync/Push tests passed `42`; the full local suite
  passed `500`; matching, malformed, and mismatched digest cases are covered.
  Python compilation, all four frontend bundle syntax checks, and
  `git diff --check` passed. Local browser loading at
  `http://127.0.0.1:8892/#/extensions` returned HTTP 200 with zero page errors
  and no narrow-screen overflow; the lab was stopped afterward.
- **Boundary:** this is receiver-side pre-commit validation only. It does not
  prove sender source retention, sender UI, network reachability, isolated VPS,
  or production behavior.

## Local Push limit rejection follow-up (2026-07-24)

- **Evidence class:** `LOCAL` only. The authenticated status probe's
  `max_image_bytes` is now tested against the actual rejection path: when a
  payload exceeds the active process limit, Push returns `422` and leaves the
  receiver gallery unchanged.
- **Verification:** focused sync/Push tests passed `43`; the full local suite
  passed `501`; Python compilation, all four frontend bundle syntax checks,
  and `git diff --check` passed. Local browser loading at
  `http://127.0.0.1:8892/#/extensions` remained HTTP 200 with zero page errors
  and no narrow-screen overflow; the lab was stopped afterward.
- **Boundary:** this is receiver-side capacity/error evidence only. It does
  not prove sender retry policy, source retention, network reachability, or
  remote/production behavior.

## Local P4 guide translation cleanup (2026-07-23)

- **Evidence class:** `LOCAL` only, frozen at commit `c75488b`. The extension
  guide title now has an explicit Chinese/English translation entry instead of
  relying on the source HTML fallback.
- **Browser result:** the local `8892` page loaded `#/extensions` with title
  `GenBox`; the guide rendered `先连接你的服务器`, and no
  `extensions.guide_connect_title` warning remained. No target was selected,
  no pairing command was generated, and no SSH action was submitted.
- **Verification:** `python -m pytest -q tests/test_extensions.py
  tests/test_extension_task_store.py` -> `287 passed`; full local suite ->
  `494 passed`; both extension JavaScript syntax checks passed.
- **Boundary:** two unrelated pre-existing i18n warnings remain; they do not
  affect the P4 host-key pairing flow and are not claimed as fixed here.

## Local GenBox sender development image slice (2026-07-28)

- **Evidence class:** `LOCAL` only. The separate chatgpt2api worktree on branch
  `codex/genbox-p4-sender-image` now contains the first GenBox Push v1 sender
  slice, committed as `23a674e`. It stores a destination/source configuration,
  masks the Push key in API responses, probes the receiver, validates the
  returned contract/source/SHA-256 receipt, and always retains the source image.
- **Verification:** sender focused Python tests passed `8`; Python compilation
  and `git diff --check` passed; the Vue production build passed with
  `npm run build`. Tests use local fakes only and no real credentials or image
  data.
- **Security boundary:** redirects are refused so credentials and image bytes
  are not forwarded to a different origin; non-boolean deletion hints are not
  treated as permission. No source deletion, batch push, scheduling, arbitrary
  remote shell, SSH, VPS, or production action was performed.
- **Build blocker:** local Docker Desktop remained `starting`; the attempted
  build returned a local Docker Engine 500 ping error and produced no verified
  image ID. This is not image-build, VPS, or deployment evidence.
- **Next local entry:** restore a running local Docker Engine, build and inspect
  the tagged image locally, then run only local receiver/sender smoke tests.

## Local sender runtime-smoke image (2026-07-28)

- **Evidence class:** `LOCAL` only. A temporary container created from local
  image `genbox/chatgpt2api:2.7.0-genbox-p4.0.1-runtime-smoke` started on a
  loopback-only port, reported version `2.7.0-genbox-p4.0.1-dev`, and exposed
  the GenBox Push settings route. The temporary container was removed after
  verification.
- **Verification:** an unauthenticated request to the settings route was
  rejected; an authorized local test request returned only the masked settings
  shape and no Push key. No Push was configured or sent, and no source image,
  SSH, VPS, remote container, production system, registry push, or external
  deployment was used.
- **Build qualification:** this image is a local runtime smoke artifact made by
  overlaying the current complete application source and Vue build onto an
  existing local chatgpt2api image. It proves local startup and the new route
  boundary, but does not replace a clean build from the repository Dockerfile.
  The canonical Dockerfile still cannot resolve its base-image metadata because
  Docker Desktop's configured local registry mirror returns EOF.
- **Next local entry:** repair or replace that Docker registry mirror, then
  rebuild from the repository Dockerfile and repeat the same loopback-only
  smoke checks before any isolated-VPS work.

## Local canonical sender image build (2026-07-28)

- **Evidence class:** `LOCAL` only. The stale Docker Desktop registry mirror
  was removed from the local daemon configuration after a backup was created.
  Direct Docker Hub metadata requests still fail through the local network
  path, so compatible Node and Python base images were fetched from an
  alternate registry into the local Docker cache and tagged locally with the
  names required by the unchanged repository Dockerfile.
- **Verification:** `docker build --pull=false` using the original Dockerfile
  completed and produced local image `genbox/chatgpt2api:2.7.0-genbox-p4.0.1-dev`.
  A loopback-only temporary container started from that image, returned version
  `2.7.0-genbox-p4.0.1-dev`, rejected an unauthenticated settings request, and
  returned masked GenBox Push settings for a local authorized test request. The
  temporary container and earlier overlay smoke image were removed afterward.
- **Qualification:** this is a reproducible local Dockerfile build while the
  two required base-image tags remain cached. It is not a registry-pushed
  artifact, clean-machine proof, isolated-VPS proof, cross-project Push E2E,
  or production evidence. The upstream Vue lockfile also reports `11` existing
  dependency audit findings during `npm ci`; no audit remediation was included
  in this sender slice.
- **Next local entry:** retain the cache-backed image for local development,
  add a mocked Push round-trip container test if needed, and separately resolve
  the environment's Docker Hub proxy route before requiring clean-machine
  rebuild evidence.

## Local sender-receiver Push container round trip (2026-07-28)

- **Evidence class:** `LOCAL` only. The canonical chatgpt2api sender image and
  a freshly built current GenBox receiver image ran on a temporary Docker-only
  network with one synthetic 1x1 PNG and test-only credentials. The sender
  completed the authenticated v1 probe, the first Push imported the image, and
  the identical retry returned an accepted idempotent status. The sender also
  verified that its source file remained present after both requests.
- **Fix:** this live local check exposed that `curl_cffi` does not support the
  `files` request argument used by the sender implementation. Sender commit
  `6a099cd` now creates a `CurlMime` multipart body, matching the installed
  library API. Focused and full sender unittest discovery each passed `8`, and
  the canonical sender Dockerfile built successfully before the round trip.
- **Cleanup and boundary:** temporary sender/receiver containers, network,
  synthetic image, and test-only configuration were removed. No user image,
  Push key, credential, SSH, VPS, remote container, production system, or
  external deployment was used. This proves a local container round trip only;
  isolated-VPS and production evidence remain unverified.
- **Next local entry:** add this disposable two-container round trip to a
  repeatable local test harness, then keep batch, scheduling, and cleanup work
  in their separate roadmap phases.

## Repeatable local GenBox Push smoke harness (2026-07-28)

- **Evidence class:** `LOCAL` only. The separate chatgpt2api worktree now has
  a disposable two-container smoke harness for a prebuilt local sender image
  and a prebuilt local GenBox receiver image. It creates an internal Docker
  network with per-run labels, publishes no ports, and uses generated test-only
  credentials from temporary environment files that are removed on exit.
- **Verification:** the harness passed the authenticated Push v1 probe, first
  synthetic-image import, idempotent retry, source SHA-256 receipt, receiver
  image dimensions and metadata, and sender source-retention check. Its focused
  harness tests passed `7`; the sender Push test suite passed `9`; Python
  syntax compilation and `git diff --check` passed. Normal completion left no
  labeled containers, networks, or temporary credential files.
- **Safety boundary:** it refuses implicit or `latest` image references and
  never builds, pulls, publishes, or deploys. Cleanup removes only exact
  resources whose fixed local-smoke label and per-run label both match; a label
  mismatch fails closed. This is not VPS, production, registry, batch, or
  scheduled-Push evidence.
- **Next local entry:** build the sender and receiver images from their current
  source revisions as separate local steps, then use this harness after any
  Push-protocol or image-build change. Keep isolated-VPS verification behind
  its explicit lifecycle gate.

## Per-generation GenBox Push sender flow (2026-07-28)

- **Evidence class:** `LOCAL` only. The separate chatgpt2api sender worktree
  now offers an opt-in "Push to GenBox after generation" setting in Studio.
  A generated image is saved first and then added to a persistent local outbox;
  Push runs independently, so an unavailable destination cannot turn a
  successful image generation into a failure. Failed items keep their source
  and expose a scoped retry action. Restart recovery requeues an interrupted
  in-flight item. Prompt text is transient only and is not written to the
  outbox state.
- **Verification:** sender unittest discovery passed `22`; Python compilation
  and Vue production build passed. A current local Dockerfile image passed the
  disposable two-container v1 probe, first-import, idempotent-retry, and
  source-retention smoke harness. A loopback-only browser check of the sender
  Studio confirmed the setting, its local-save/failure boundary text, and its
  checkbox interaction. All test credentials and image data were synthetic.
- **Safety boundary:** no real image, prompt, SSH credential, Push key, VPS,
  remote container, production system, registry push, or external deployment
  was used. This does not prove an isolated-VPS route, a real upstream image
  generation, batch Push, scheduled Push, cleanup, or production behavior.
- **Next local entry:** treat the next work as a separate Phase 5
  batch/scheduler design or an explicitly authorized isolated-VPS Phase 4
  gate; neither is implied by this local evidence.
