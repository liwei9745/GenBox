# Current Project Status

**Last updated:** 2026-07-23
**Current branch:** `codex/p4-deploy-plan-ux-eai`
**Current phase:** Phase 4 Single-Image Push End To End - **In Progress**

## Current evidence

- **VERIFIED 2026-07-23:** GenBox commits `5397141`, `6f8c710`, and `b037c9d`
  locally implement the personal-user trusted SSH-session pairing path on top of
  Deployment Safety Contract v3. The saved trust record remains the canonical
  SSH host-key algorithm plus `SHA256:` fingerprint pair; pairing does not
  replace SSH credentials or mandatory host-key verification.
- **VERIFIED 2026-07-23:** focused and full local verification completed with
  `486 passed`. Independent fixed-commit architecture, security, and regression
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

## Exact next step

Follow `docs/P4-LOOP-ENGINEERING.md`: L0 and L1 are complete; L2 is the active
loop. Freeze the sanitized receiver commit and image/config contract, then
perform read-only discovery against the explicitly isolated VPS development
clone. Reproduce the same container shape there before attempting the
separately authorized browser-driven single-image E2E. Production remains
read-only.

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
