# Current Project Status

**Last updated:** 2026-08-01
**Current branch:** `codex/p4-deploy-plan-ux-eai`
**Current phase:** Phase 6 Verified Source Cleanup - **In Progress / Destructive Execution Blocked**
**Previous phase:** Phase 5 Batch And Scheduled Incremental Push - **Complete**

## Phase 6 resume point

- **LOCAL / VERIFIED 2026-08-01:** Phase 6 protocol, platform, multi-agent, and
  adversarial-review contracts are committed locally in `0911c16`, `08a66a7`,
  and `ee5f32f`. They define default-retain behavior, receipt and SHA-256
  binding, storage-rooted deletion, crash recovery, server-side environment
  gates, and the A1-A12 adversarial matrix. These are specifications, not an
  implementation or deployment claim.
- **LOCAL / VERIFIED 2026-08-01:** the latest isolated sender candidate is
  commit `32bb3b6` on `codex/genbox-p5-resume-worker`. It includes the shared
  cleanup/settings coordination lock, final destination and policy rechecks,
  handle-based deletion, duplicate-receipt rejection, and bounded streamed
  receipt parsing. The sender full suite passes `105` with `2` platform skips;
  the focused cleanup, storage, and Phase 6 suites also pass. Compile and diff
  checks are clean, and the sender worktree has no uncommitted changes.
- **SECURITY GATE / BLOCKED 2026-08-01:** the fresh independent A1-A12 review
  keeps the merge and destructive-execution gate blocked. The remaining gaps
  are a remaining POSIX directory-entry replacement window between final stat
  and unlink (A4), true FastAPI lifespan/restart evidence (A7), isolated-VPS
  runtime and production non-mutation evidence plus per-item environment
  ownership checks (A9), and a real wall-clock slow-drip receipt test (A12).
  Directory and marker symlink cases remain platform-skipped because this
  Windows host lacks symlink privilege; the directory-junction control passes.
  Cleanup remains disabled in development and no production instance may be
  modified.
- **RELEASE BOUNDARY / VERIFIED 2026-08-01:** the last published experimental
  sender image is still the pre-Phase-6 commit `ca6f1ba`; its immutable digest
  was used only for the isolated sender. Commit `32bb3b6` has not been pushed
  to the owner's experimental repository and has not been published to GHCR.
  The stable GenBox `v2.5.1` release must not claim Phase 6 completion.
- **NEXT ACTION:** close the A4/A7/A9/A12 evidence gaps and repeat the
  independent adversarial review. Only a `PASS` may unlock the Phase 6 branch
  push, a new immutable GHCR image, isolated deployment, and the clean
  GitHub-clone rebuild plus sensitive-information scan. `33018` remains out of
  scope and production remains read-only.

## Current evidence

- **GITHUB + GHCR + ISOLATED-VPS 2026-08-01:** the experimental sender branch
  codex/genbox-p5-resume-worker is published in the owner's experimental
  repository at commit ca6f1ba. The corresponding GHCR package is pinned by
  immutable digest
  ghcr.io/liwei9745/chatgpt2api-genbox-p5@sha256:da5c8200b39833e5a9b2c74be72480bc772608711f0543a423fd49d4d18cd77d
  and was the image applied to the registered isolated sender on service port
  33010. The separately registered 33018 instance and production systems
  were not selected or modified.

- **ISOLATED-VPS 2026-08-01:** the Phase 5 batch, failed-only retry,
  concurrent schedule lease, and late-arriving image checks all have direct
  evidence in docs/PHASE5-EVIDENCE-2026-08-01.md. Five source images were
  retained, and the normal private receiver route was restored after testing.

- **LOCAL 2026-08-01:** the GenBox full test suite passed 582; the reviewed
  Phase 5 evidence, roadmap, and integration capability matrix were committed
  as 5baa2fb and pushed to the current experimental GenBox branch. A clean
  GitHub-clone rebuild and deployment remain a separate release gate.
- **LOCAL 2026-08-01:** the deployment image field now includes a bilingual
  `Check GenBox integration` action and a compact image-option menu. The
  reviewed GenBox image stays read-only; only the custom option unlocks manual
  digest entry. It validates the immutable digest against the local
  reviewed-image capability catalog only: the current GenBox sender preset
  reports `genbox-push-v1`; the pinned `yukkcat` upstream digest is selectable
  but reports `not_integrated`, leaving the deployment decision to the user.
  An unregistered custom digest is explicitly `unknown`, never presented as
  integrated. The action does not contact a VPS,
  registry, Docker daemon, or image runtime. Focused extension and image
  capability tests passed `213`; Python compilation, JavaScript syntax, and
  diff checks passed. This is local UI and route evidence only.

- **LOCAL 2026-07-31:** the deployment form now presents three image-source
  choices in beginner-friendly order: the verified GenBox integration build is
  selected by default, the upstream image remains visible but disabled until
  its integration PR is merged, and a custom immutable digest can be entered
  manually. The project choice locks the digest field while the custom choice
  clears and unlocks it; both languages have matching labels and status text.
  Extension and managed-image tests passed `208`, `node --check
  static/js/extensions.js`, and `git diff --check`. This is local UI evidence
  only; no VPS or production instance was changed.

- **GITHUB + ISOLATED-VPS 2026-07-31:** sender commits `9e80af3` and
  `efae62f` were published from the owner's experimental repository. The final
  immutable image digest `sha256:c9357b45b1339d2be4e4a02eb48f059562890f14bd9757b924d7fd7621b9e076`
  was applied only to the registered isolated sender through GenBox's controlled
  update path; pull, rebuild, and health verification completed successfully.
  No production instance was selected or modified.

- **ISOLATED-VPS 2026-07-31:** after starting a two-image Gallery batch and
  reloading the sender page, the durable progress dialog reappeared from the
  server-side batch projection while selection reset to zero. This confirms
  browser-refresh recovery. A later one-image duplicate Push remained in
  `sending` beyond the bounded observation window, then disappeared from the
  recoverable projection after its dialog was closed. The current UI has no
  terminal batch-history view, so the final result cannot be observed safely.
  This run is not accepted as a completed idempotent-retry result; terminal
  batch history and the delayed-transfer diagnosis remain blockers for Phase 5
  acceptance.

- **LOCAL 2026-07-31:** the sender now exposes a recoverable-batch projection,
  persists distinct `already-imported` item outcomes, and displays a
  compatibility-safe progress count. Focused sender tests passed `13` and the
  Vue production build passed. Cross-process batch locking and bounded retry
  policy are not yet present in the current sender branch and remain follow-up
  work; do not treat earlier planning text as implementation evidence.

- **LOCAL 2026-08-01:** target-mode parallel review completed in the isolated
  `E:\AI\chatgpt2api-dev` sender checkout. Commit `c7367dc` preserves
  `duplicate-local` receipts as distinct `already-imported` batch outcomes and
  safely handles legacy or malformed retry timestamps. The sender branch
  already contains latest-recoverable hydration, cross-process item claiming,
  bounded retry/backoff, and failure classification. Focused batch, transfer,
  service, and API tests passed `35`; the Vue production build and diff checks
  passed. This is local sender evidence only; no VPS or production instance
  was changed, and isolated Phase 5 acceptance remains pending.

- **LOCAL 2026-08-01:** the next target-mode fix wave closed the P1 outbox
  claim race. Sender commits `dbd661d` and `b9293aa` add a process-shared state
  lock plus a per-entry lock held through transfer completion, recover only
  stale `sending` entries whose claim lock is free, and preserve duplicate
  receipts as `already-imported`. The schedule projection now exposes the same
  duplicate count, and Gallery polling ignores stale or overlapping responses.
  Sender full tests passed `63`; Phase 5 focused tests passed `49`; the Vue
  production build, compile checks, and diff checks passed. A GenBox offline
  control-script compatibility fix was verified with the full GenBox suite:
  `582 passed`. All evidence is local; no VPS or production instance changed.

- **LOCAL + GITHUB 2026-08-01:** the sender branch
  `experimental/codex/genbox-p5-batch-recovery` was pushed to the owner's
  experimental repository after the local test and secret scan. The amd64
  workflow run `30682843048` completed successfully and published the
  immutable experimental image
  `ghcr.io/liwei9745/chatgpt2api-genbox-p5@sha256:3c812bc385b8d911e54183a27a926cef729fc6911fb29e6da64f3582ab2795cf`.
  This digest is a candidate for the isolated sender only; no VPS update has
  been performed from it yet, and production remains unchanged.

- **LOCAL 2026-08-01:** Docker pulled the published image by its full digest
  and reported the same `sha256:3c812bc385b8d911e54183a27a926cef729fc6911fb29e6da64f3582ab2795cf`.
  The GenBox Extensions page shows two registered managed chatgpt2api cards,
  while the local credential vault is locked and therefore keeps both remote
  `Update image` actions disabled. No direct SSH fallback was used. The next
  remote step requires unlocking the local vault, then generating and
  explicitly confirming the bounded update plan for the intended isolated
  instance; production remains untouched.

- **LOCAL + ISOLATED-VPS 2026-07-31:** fixed the managed-service drawer so
  opaque instance handles containing quotes cannot leave the visible `Update
  image` or key-reset actions inert. After each render, the card's encoded
  handle is rebound from its `data-instance-handle` attribute and the malformed
  inline handler is removed. `node --check static/js/extensions.js`,
  `git diff --check`, `python -m pytest -q tests/test_extensions.py` (`202`
  passed), and the focused cross-module suite (`365` passed) succeeded. The
  local development lab was then safely restarted from the current source and
  rendered both managed sender cards without browser errors. The controlled
  remote-update/restart action remains intentionally unavailable until the
  user unlocks the per-instance local credential vault; no direct SSH fallback
  will be used.

- **ISOLATED-VPS 2026-07-31:** an authorized manual scheduled scan was run
  again through the sender Settings UI. It completed with `3` completed, `0`
  waiting, and `0` failed items, with source-image retention still enabled.
  This is an operational health check only and does not replace the remaining
  controlled interruption-recovery or independent-worker lease evidence.

- **ISOLATED-VPS 2026-07-31:** a baseline manual incremental scan completed
  with `2` completed items and no queued or failed items. One newly generated,
  development-only test image was then added within the same scan range. The
  next overlapping manual scan first reported `2` completed and `1` queued,
  then converged to `3` completed, `0` queued, and `0` failed, with all source
  images retained. This verifies late-arriving source discovery on the
  isolated sender without production mutation.

- **ISOLATED-VPS 2026-07-31:** two independently loaded, authenticated
  Settings pages clicked the bounded `run now` UI control concurrently. Both
  requests completed before a visible lease conflict could occur because the
  three-item scan was too short. This is not concurrency-lease acceptance
  evidence; the remaining live check needs an intentionally overlapping scan
  or independent worker process. Cross-process lease protection remains
  locally covered by focused sender tests.

- **ISOLATED-VPS 2026-07-31:** Gallery's visible failed-only retry control
  retried one previously failed item without resubmitting any other item. Its
  terminal receipt projection was `already-imported`, and the page confirmed
  that the source image remained retained. A subsequent two-item Gallery batch
  was started and the browser was refreshed immediately. The reloaded page
  restored that same batch and later reported `2` `already-imported` outcomes
  with source retention. This is user-visible browser-refresh recovery and
  idempotent completion evidence; it does not substitute for a sender-process
  interruption or an independent concurrent-schedule invocation.

- **ISOLATED-VPS 2026-07-31:** the registered isolated sender received the
  reviewed immutable Phase 5 image through the controlled update path. The
  updater accepted only its opaque instance handle and immutable digest, used
  the saved per-instance SSH credential internally, and completed the bounded
  pull, configuration backup, app recreation, and health-check operation. The
  local registration changed only after that health check; the other registered
  instance and all production systems remained unchanged. **Next evidence:**
  reload the sender Settings page and run one manual scheduled scan to verify
  the repaired batch-progress projection in the deployed browser.

- **USER-CONFIRMED ISOLATED-VPS 2026-07-31:** after the controlled image
  update, the sender Settings page's manual scheduled scan reported `2`
  completed, `0` waiting, and `0` failed items, with source images retained.
  This confirms the deployed schedule-progress refresh path; batch interruption
  recovery, late-file overlap discovery, and lease behavior remain to be
  exercised before Phase 5 can be accepted.

- **ISOLATED-VPS + GITHUB 2026-07-31:** a focused Gallery usability fix made
  both selected-image actions explicitly name GenBox as their destination. The
  experimental AMD64 workflow built and published a new immutable sender image,
  then the controlled updater replaced only the registered isolated sender and
  completed its health check. The user-facing batch behavior is unchanged;
  this removes ambiguity before the remaining interruption-resume test.

- **USER-CONFIRMED ISOLATED-VPS 2026-07-31:** the updated Gallery completed a
  manual two-image batch Push to GenBox, reporting `2` processed items and
  retaining both source images. This validates the visible manual-batch success
  path, but does not yet prove interruption recovery, late-file discovery,
  concurrent schedule lease behavior, failure-only retry, or the later clean
  redeployment and upstream-delivery gates.

- **LOCAL 2026-07-31:** the deployed-services drawer now shows non-secret
  instance metadata for disambiguation: VPS name and address, SSH port,
  service port, deployment time, and the local credential-save timestamp when
  available. The public projection remains allowlisted and excludes keys,
  passwords, paths, container IDs, and image configuration. Focused extension
  and vault tests passed `341`. The detail rows are now translated in both
  supported UI languages and collapsed by default; service-drawer loading is
  single-flight so repeated route/drawer refreshes do not duplicate controls.

- **LOCAL 2026-07-31:** GenBox now has a controlled update path for an
  already registered managed `chatgpt2api` isolated Compose instance. The
  browser supplies only an opaque instance handle and immutable image digest;
  a single-use five-minute plan is bound to those values. Application occurs
  only after the local credential vault is unlocked, verifies the isolated
  target role and remote ownership marker, pulls before changing `.env`, then
  recreates and health-checks the app. A failed write, start, or health check
  restores the prior configuration and recreates the prior app; the local
  instance image record changes only after health succeeds. The endpoint and
  UI never return saved SSH credentials. Focused GenBox extension suites passed
  `369`. The vault was later unlocked for a controlled-update preflight, which
  then stopped before SSH because its saved SSH credential belongs to a
  different managed isolated instance. The sender instance being verified has
  no locally saved SSH credential yet. Remote controlled update and
  schedule-progress verification therefore remain pending an explicit
  per-instance credential save; no production instance was selected or
  modified.

- **ISOLATED-VPS + LOCAL RECEIVER 2026-07-31:** the authorized isolated
  sender completed a two-item Gallery batch Push with source retention. A
  manual scheduled scan then created two recoverable items but the deployed
  Settings page continued to show its initial queued projection after the
  batches had been handed to the worker. The sender fix makes schedule reads
  refresh batch projections and adds bounded Settings-page polling; focused
  transfer, batch, and schedule tests passed `25`, and the Vue production build
  passed. A new immutable experimental sender image was published from the
  reviewed fix. The already-running isolated instance is still on the prior
  immutable image: remote verification of the fixed schedule progress display
  requires an approved controlled update or replacement deployment. No
  production instance was selected or modified.

- **ISOLATED-VPS + LOCAL RECEIVER 2026-07-31:** an authorized Gallery
  single-item Push initially showed a transient failure state, then recovered
  to a completed receipt with source retention. A second explicit Push of the
  same selected source completed without sender browser errors. The local
  receiver's remote-media thumbnail set was identical immediately before and
  after that retry, proving no duplicate media was created. This is a focused
  user-visible retry/idempotence check only; Phase 5 still requires isolated
  batch-interruption recovery and scheduled late-file discovery evidence. No
  production instance was selected or modified.

- **GITHUB + LOCAL 2026-07-31:** the owner's experimental sender repository
  published a dedicated immutable `linux/amd64` Phase 5 image package after
  correcting the repository workflow permission and package-ownership
  boundaries. The digest was pulled back from GHCR and passed the disposable
  Docker-only Push smoke, including idempotent retry, interrupted-batch
  recovery, scheduled late-file discovery, and source retention. This proves a
  sanitized GitHub-built sender artifact can run locally; it does not prove the
  isolated VPS architecture, deployment, batch interruption, or scheduled scan.

- **LOCAL 2026-07-31 (superseded wording):** the sender batch implementation
    now persists explicit `already-imported` outcomes and exposes the newest
    active or failed batch for Gallery refresh recovery. The current branch
    does not yet provide cross-process batch locking or bounded automatic retry
    policy; those are separate Phase 5 follow-ups. Local Docker smoke evidence
    remains distinct from isolated-VPS acceptance.

- **EVIDENCE LOCK 2026-07-30:** after the isolated sender/receiver verification,
  `python -m pytest -q tests/test_extensions.py tests/test_local_tailscale.py
  tests/test_sync_push_routes.py tests/test_extension_task_store.py` passed
  `365`; `node --check static/js/extensions.js` and `git diff --check` also
  passed. The reviewed diff contains only source, tests, and sanitized project
  documentation. The isolated Studio and Gallery success states supersede the
  earlier transient Gallery failure dialog; source retention and receiver-side
  idempotence remain the authoritative result. No production instance was
  selected or modified.

- **ISOLATED-VPS + LOCAL RECEIVER 2026-07-30:** a selected image from the
  authorized sender Studio generated a new image with “生成后推送到 GenBox”
  enabled. The Studio result first showed “已推送到 GenBox，源图已保留”. The
  same image was then selected in Gallery and pushed again; the sender retained
  the source and the Studio task remained successful after the retry. The
  receiver manifest gained exactly one new entry for this image and the
  repeated request did not create a third entry. This verifies the isolated
  browser Studio single-image Push, authenticated receipt, source retention,
  and idempotent retry. No production instance was selected or modified.

- **LOCAL + ISOLATED-VPS 2026-07-30:** the local Tailscale Serve recovery
  path now understands the current `Foreground` status shape. When its sole
  route is the GenBox-owned HTTP listener but targets a stale loopback port, it
  may reset and recreate only that one route; any unrelated route fails closed
  without mutation. After restarting the registered development lab, its
  private Serve entry was verified to target the current process and the
  loaded status endpoint reported the route healthy. Focused Tailscale,
  network-adapter, and extension tests passed `236`; the focused extension,
  route, and task-store suites then passed `364`.

  The isolated sender's saved destination passed its authenticated v1 readiness
  check. Its Gallery reported the selected generated image as complete with
  source retention enabled. The current GenBox development receiver contained
  one remote-imported media file and its durable manifest contained transfer
  records, confirming that the user-visible success state corresponds to a
  receiver-side import. This verification used only the authorized isolated
  sender and local development receiver; no production instance was selected
  or modified.

- **ISOLATED-VPS 2026-07-30:** an explicitly authorized development-only
  `chatgpt2api` instance was deployed from the published immutable sender
  image. Its directory, Compose project, management key, and GenBox Push
  source are distinct from the pre-existing managed instance. A stale local
  GenBox process behind the existing private Tailscale entry initially rejected
  the sender identity. The registered current GenBox lab was restarted and the
  existing private entry was redirected to that lab; the sender then completed
  an authenticated v1 probe.

  A user-created isolated test image completed a manual authenticated Push and
  then an identical manual retry. The sender validated the success receipt and
  retained the source image after both requests. A local receiver query
  immediately afterward returned exactly one media item, tagged as a remote
  sync import, proving that the retry did not duplicate the image. Source
  deletion remains disabled and no schedule was configured. No production
  instance was selected or mutated. The later evidence-lock result at the top
  completes Phase 4; Phase 5 has not started.

- **LOCAL 2026-07-30:** deployment-plan generation and final deployment
  authorization now use visible in-page confirmation cards instead of browser
  native confirmation dialogs. The cards explain the read-only preflight or
  the isolated deployment scope, keep cancellation on the reviewed page, and
  invoke the existing backend gates only after the user selects the explicit
  continue action. Backend `approve_plan_discovery`, host-key verification,
  immutable-image validation, and `confirmed_plan_id` requirements are
  unchanged. `node --check static/js/extensions.js`, `git diff --check`, and
  the focused extension/Push suites passed `363`. This was local UI/test
  evidence at the time recorded. The later isolated-VPS deployment and
  single-image Push verification is recorded at the top of this document.

- **LOCAL 2026-07-30:** the novice deployment guide now preserves an explicit
  path to plan a second isolated `chatgpt2api` instance after a prior managed
  deployment has completed. The new action clears only the browser's transient
  historical deployment and delivery state; it preserves the saved target and
  does not stop, replace, reconfigure, or send a request to the existing
  instance. It then returns the user to the credential-gated plan workflow.
  `python -m pytest -q tests/test_extensions.py` passed `201`; JavaScript
  syntax and whitespace checks passed. No credential was read or logged, and
  no SSH, VPS, container, network, or deployment action was submitted. This is
  `LOCAL` UI/test evidence only.
- **VERIFIED 2026-07-30:** the published immutable sender image
  `ghcr.io/liwei9745/chatgpt2api@sha256:6892af60bbb85db1963d43474e66d5551f1a0fd212cb88d658d8a3410c1dc9d0`
  was pulled by digest and used directly in the disposable local Push smoke
  against the clean-clone GenBox receiver image. The v1 probe, full final Push
  endpoint input, first import, idempotent retry, and source retention passed;
  the smoke resources were removed afterward. This verifies the published
  sender artifact locally, not a VPS pull, configuration, or isolated-VPS E2E.
- **LOCAL 2026-07-30:** a fresh, empty local clone of
  `liwei9745/GenBox:codex/p4-deploy-plan-ux-eai` resolved to `dea968c` with no
  working-tree changes. Its Dockerfile built a new receiver image using that
  clone as the only build context and `--pull=false`. Paired with the current
  sender image, the disposable internal-network smoke passed the v1 probe,
  full final Push endpoint normalization, first import, idempotent retry,
  metadata verification, and source retention. No runtime configuration, user
  data, image, credential, VPS, registry publication, or production instance
  was used. This is clean-source `LOCAL` evidence, not a clean isolated-VPS
  deployment or end-to-end user workflow acceptance.
- **VERIFIED 2026-07-30:** after a local sanitization review, the current
  GenBox Phase 4 branch was pushed to
  `liwei9745/GenBox:codex/p4-deploy-plan-ux-eai`; the current sender branch
  was pushed to both authorized experimental repositories as
  `codex/genbox-p4-sender-image`. Neither action updated a default branch.
  The sender's immutable GHCR image is the separately verified artifact below.
  A clean GenBox deployment from its pushed branch remains pending; the
  isolated-VPS single-image Push acceptance run is recorded at the top.
- **VERIFIED 2026-07-30:** the authorized experimental GHCR workflow completed
  successfully for sender commit `a4217e3` and published the immutable image
  index `ghcr.io/liwei9745/chatgpt2api@sha256:6892af60bbb85db1963d43474e66d5551f1a0fd212cb88d658d8a3410c1dc9d0`.
  A read-only manifest inspection confirmed `linux/amd64` and `linux/arm64`
  manifests. This is a registry artifact verified by the successful workflow
  and manifest query; it is not evidence that a VPS has pulled, configured, or
  run the image, and it does not complete isolated single-image Push E2E.
- **LOCAL 2026-07-30:** the sender repository built a current local image from
  its source with `--pull=false`, reusing already available base images and
  dependency layers. Its disposable Docker-only Push smoke harness then passed
  with the full final `/api/sync/push` address as the configured sender input.
  On one internal, unpublished network it generated a synthetic 2x2 PNG and
  test-only credentials, then verified the v1 probe, first import, idempotent
  retry, concurrent-transfer coordination, interrupted-batch recovery,
  receiver SHA-256 metadata, and source retention. The harness removed its
  per-run labeled containers and network afterward. No user image, credential,
  VPS, SSH, production container, registry pull, publication, or deployment
  was used. This is `LOCAL` current-image protocol evidence only, not
  `ISOLATED-VPS` or full user-workflow acceptance evidence.
- **LOCAL 2026-07-30:** the final private-network completion view now makes
  the chatgpt2api login handoff explicit for new users. It pre-fills the
  one-time management key delivered in the current page, labels that state,
  supports an intentional refill from that same delivery, and permits a manual
  replacement key. The shortcut copies the submitted value, opens the
  non-secret private console URL in a separate tab, then clears both page
  inputs and disables the delivery refill. It writes neither key to browser
  storage nor to a URL or backend endpoint. The delivery key cannot be
  recovered after refresh or clearing; the user must manually paste it or use
  the existing ownership-verified rotation flow. `tests/test_extensions.py`
  passed `200`; JavaScript syntax and diff whitespace checks passed. A
  loopback request returned the current static bundle reference. No browser
  target was selected, no credential was entered, and no SSH, VPS, container,
  sender, deployment, or network action was submitted. This is `LOCAL` UI/test
  evidence only.
- **LOCAL 2026-07-30:** GenBox now provisions a dedicated Push source for one
  registered, managed `chatgpt2api` instance after its private destination is
  verified. The browser submits only an opaque instance handle; the backend
  resolves the saved target, instance, and destination. The local registry
  atomically persists only an active flag, timestamps, random salt, and
  PBKDF2-HMAC-SHA256 verifier. Raw Push keys are returned only by explicit
  create or rotate actions, never by status/listing; revoke retains a tombstone
  that blocks fallback to a same-named legacy `GENBOX_PUSH_KEYS` entry. The
  final Extensions step shows the non-secret destination and source ID, offers
  create/copy/rotate/revoke actions, clears the one-time key after the explicit
  copy action, and uses neither browser storage nor key-bearing URLs. Focused
  receiver, route, DOM, and task-store suites passed `378`; Python compilation,
  JavaScript syntax, and whitespace checks passed. A fresh loopback server
  returned the current Extensions bundle and static page containing the Push
  panel. No browser target was selected, no credential was entered, and no SSH,
  VPS, container, sender, deployment, or network action was submitted. This is
  `LOCAL` receiver/UI evidence only. The later sender configuration and
  isolated single-image Push E2E verification is recorded at the top.
- **LOCAL 2026-07-30:** the final private-network completion screen now offers
  a console-login helper for the exact managed instance. It pre-fills a
  one-time management key only while that value remains in the current page;
  after a refresh, the user can enter a replacement key manually. An explicit
  action copies the key, opens the private console in a separate tab, then
  clears the helper input. The key is never appended to a URL, sent to a new
  backend endpoint, or persisted in browser storage. The console address may
  be recovered only by matching the existing opaque managed-instance handle to
  public instance metadata. Focused extension suites passed `325`; full local
  `python -m pytest -q` passed `553`; JavaScript syntax, whitespace, and
  loopback static-resource checks passed. No browser target was selected, no
  credential was entered, and no SSH, VPS, container, deployment, or network
  action was submitted. This is `LOCAL` UI/test evidence only.
- **LOCAL 2026-07-30:** a VPS-network task that stops for user input now keeps
  its recovery card actionable in novice mode. The visible recovery button
  directs a missing session credential to the SSH password/private-key field;
  after a session credential is present, it directs the user to the Tailscale
  Auth Key field, then changes to an explicit retry action once the key is
  entered. Filling a field alone never submits a network request.
  The Extensions bundle query version was advanced so a reload receives this
  behavior. Focused extension suites passed `324`; full local
  `python -m pytest -q` passed `552`; JavaScript syntax and whitespace checks
  passed. No browser target was selected, no credential was entered, and no
  SSH, VPS, container, deployment, or network action was submitted. This is
  `LOCAL` UI/test evidence only.
- **LOCAL 2026-07-29:** closing the reviewed safety-plan step now requires one
  final browser confirmation immediately before the deployment request can be
  sent. Cancelling, or a browser that cannot present that confirmation, keeps
  the reviewed plan visible, leaves its deploy action available, and sends no
  deployment request; it does not repeat SSH pairing, credential entry, or
  read-only discovery. Existing plan-expiry, exact-attempt, and reconciliation
  tests explicitly model confirmed browser intent. Focused extension suites
  passed `323`; full local `python -m pytest -q` passed `549`; JavaScript
  syntax and whitespace checks passed. No browser target was selected, no
  credential was entered, and no SSH, VPS, container, plan, deployment, or
  network request was submitted. This is `LOCAL` evidence only.
- **LOCAL 2026-07-29:** bounded the two fixed read-only checks that run only
  after the user explicitly approves safety-plan generation. The backend now
  cancels either stalled preflight and returns a sanitized, retry-safe
  `plan_discovery_timeout`; the browser independently aborts an unresponsive
  plan request, hides any plan preview, keeps deployment disabled, and tells
  the user that host-key confirmation is not required again. Focused route and
  UI regressions cover both backend preflight positions, browser abortion, and
  safe retry state. `python -m pytest -q` passed `548`; JavaScript syntax,
  Python compilation, and whitespace checks passed. No browser target was
  selected, no credential was entered, and no SSH, VPS, container, plan,
  deployment, or network request was submitted. This is `LOCAL` evidence only.
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

## Phase 5 isolated acceptance run (2026-08-01)

This earlier browser run is superseded by the final isolated evidence in
docs/PHASE5-EVIDENCE-2026-08-01.md. Its duplicate progress dialog and zero-
count projection were captured before the sender worker/projection fixes and
are retained only as historical debugging context. They are not current
blockers and must not be used to describe the final Phase 5 result.

The final isolated evidence records successful batch interruption/recovery,
failed-only retry, concurrent schedule lease rejection, late-arriving image
discovery, source retention, and restoration of the private receiver route.
The production boundary remains unchanged. Clean GitHub-clone redeployment,
full sanitization review, and public release remain later gates.

## Clean GitHub redeployment and sanitization check (2026-08-01)

- **CLEAN-GITHUB-CLONE:** a new clone of the GenBox experimental branch at
  commit f6f3186 built successfully from its repository Dockerfile. The
  isolated Compose deployment reported a healthy container; its setup-status
  endpoint and home page both returned HTTP 200. The clean clone test suite
  passed 582 tests. The deployment used only generated local configuration and
  a separate temporary storage directory.
- **CLEAN-SENDER-CLONE:** a new clone of the experimental sender branch at
  commit ca6f1ba built successfully from its Dockerfile, including the Vue
  production build. The sender test suite passed 66 tests. A disposable
  loopback-only container started with a generated test key and returned HTTP
  200 for its home page; no VPS, production data, or user credentials were
  mounted.
- **SANITIZATION:** tracked-file and Git-history scans for private-key blocks,
  provider tokens, GitHub tokens, Tailscale enrollment tokens, and non-example
  administrator keys found no real credential. Matches were limited to test
  sentinels, ghp_xxx-style documentation placeholders, and synthetic network
  fixtures. The clean clones had no Git worktree changes.
- **BOUNDARY:** this proves reproducible clean local deployment and sanitized
  source state. It does not authorize a production upgrade or an upstream PR;
  those remain separate release decisions.
