# Current Project Status

**Last updated:** 2026-07-24
**Current branch:** `codex/p4-deploy-plan-ux-eai`
**Current phase:** Phase 4 Single-Image Push End To End - **In Progress**

## Current evidence

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
- **UNVERIFIED / BLOCKED 2026-07-23 19:29 +08:00 (L2):** the only local runtime
  target record is ignored `storage/extensions.json`; it has no saved canonical
  SSH host-key algorithm or `SHA256:` fingerprint. No SSH connection or remote
  command was attempted. Therefore VPS isolation, ownership, Docker/Compose
  state, ports, mounts, capacity, and health remain unverified. The configured
  target must not be treated as production or development evidence until the
  user confirms the isolated clone and supplies/approves its host-key trust pair.

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

Keep L2 paused. The local sender/receiver secret and data-boundary review is
complete; no further P4 runtime proof is permitted without separate
authorization. The next external gate, only after the user confirms an
isolated development target and its canonical SSH host-key pair, is the
approved read-only isolated-VPS discovery set.
Do not treat this LOCAL evidence as VPS or production verification.

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
