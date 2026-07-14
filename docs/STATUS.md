# Current Project Status

**Last updated:** 2026-07-14
**Current branch:** `dev`
**Current phase:** Phase 1 - ACCEPTED
**Current objective:** The owner-approved shared-heading and onboarding UI refinement from `docs/ONBOARDING-UI-CONTRACT.md` is now implemented and locally accepted on port `8892`; the next session can begin from owner review or subsequent pre-Push UI follow-up, without entering chatgpt2api Push work yet.
**Test baseline:** 66 tests collected, all passing as of 2026-07-14.
## Status Legend

- `VERIFIED IN CODE/TESTS`: confirmed from current code and local tests, but not
  necessarily exercised against a live VPS.
- `VERIFIED LIVE`: confirmed by a dated command against the named environment.
- `USER-CONFIRMED`: supplied by the project owner but not independently checked.
- `UNVERIFIED`: configured, designed, or previously reported but not currently
  proven against a live environment.

## Verified In Code And Local Tests

- `VERIFIED IN CODE/TESTS` GenBox has an Extension page connected to the main navigation.
- `VERIFIED IN CODE/TESTS` The catalog exposes chatgpt2api as deployable and keeps the other
  listed gateways, account tools, and proxy tools non-deployable.
- `VERIFIED IN CODE/TESTS` VPS target storage excludes SSH password, private key, and sudo
  password values.
- `VERIFIED IN CODE/TESTS` SSH host-key confirmation and read-only environment discovery are
  implemented.
- `VERIFIED IN CODE/TESTS` Discovery covers system resources, Docker/Compose/Python tooling,
  listening ports, containers, and candidate chatgpt2api instances.
- `VERIFIED IN CODE/TESTS` The standard Compose path has plan and remote execution code for an
  isolated chatgpt2api instance.
- `VERIFIED IN CODE/TESTS` Deployment delivery includes console URL, API URL, and a one-time
  generated management key with copy controls in the web UI.
- `VERIFIED IN CODE/TESTS` Network command adapters exist for Tailscale, NetBird, and
  Cloudflare Tunnel. Windows local Tailscale preparation is implemented.
- `VERIFIED IN CODE/TESTS` GenBox supports existing server-side Pull import from a compatible
  chatgpt2api deployment.
- `VERIFIED IN CODE/TESTS` GenBox implements `POST /api/sync/push` with per-source auth, image
  validation, SHA-256, idempotency, local deduplication, and an import receipt.
- `VERIFIED IN CODE/TESTS` On 2026-07-12, the pre-fix baseline collected 47 tests and all
   47 passed on Windows with Python 3.14.3.
- `VERIFIED IN CODE/TESTS` `extensions/orchestrator.py` elevates privileged remote commands
   (clone copy of `/root` data, scrub, config copy, Compose up) with sudo whenever the
   non-root user can elevate, independent of Docker-group access. This fixes the first
   deploy failure where `cp -a /root/chatgpt2api/data` ran without sudo and reported
   `澶嶅埗婧愬疄渚嬫暟鎹け璐.
- `VERIFIED LIVE` On 2026-07-12, the local GenBox server was restarted from this
  checkout after the orchestrator sudo fix. The listener changed from PID 57104 to
  PID 58056 on `0.0.0.0:8891`, and `GET http://127.0.0.1:8891/` returned HTTP 200.
- `VERIFIED LIVE` On 2026-07-12, the local GenBox server was restarted again after
  the AsyncSSH sudo channel-race fix. The listener changed from PID 58056 to PID
  19792 on `0.0.0.0:8891`, and `GET http://127.0.0.1:8891/` returned HTTP 200.
- `VERIFIED IN CODE/TESTS` Deployment completion now opens the step-5 delivery panel
  so console/API URLs and the one-time management key are visible; the full suite
  passes with 50 tests.
- `VERIFIED IN CODE/TESTS` A read-only "宸查儴缃叉湇鍔? list was added to the Extension
  page. It loads `GET /api/extensions/instances` and shows each managed instance's
  id, console/API URLs, port, and deploy time with open/copy actions. It shows no
  secret fields; the management key is recovered via the existing reset flow.
  Full suite passes with 52 tests.
- `VERIFIED IN CODE/TESTS` The "宸查儴缃叉湇鍔? panel was redesigned as a light
  glassmorphism Bento layout: instances grouped into API 浠ｇ悊涓庢ā鍨嬬綉鍏?/ 璐﹀彿绠＄悊 /
  浠ｇ悊缃戠粶, each group collapsible with a chevron and count, 3-col responsive grid
  (1 col mobile), and color-coded status tags (running=green, deployed=blue,
  planned=amber, unavailable=gray). A per-card "閲嶇疆瀵嗛挜" button opens a credential
  modal that re-verifies VPS ownership and calls the existing reset-admin-key
  endpoint. Full suite passes with 53 tests.
- `VERIFIED IN CODE/TESTS` The deployed-services trigger is now one enterprise-style
  header control with a circuit/hexagon mark and the label "鏌ョ湅宸查儴缃叉湇鍔?; the old
  floating grid button and duplicate inline action were removed. The right-side glass
  drawer retains overlay/ESC close behavior and the 5-step wizard is unchanged. Its
  async response handling was fixed so the persisted `chatgpt2api-dev` instance renders
  with running status, port, console/API actions, and key reset; planned services render
  as subordinate rows. Full suite passes with 53 tests.
- `VERIFIED IN CODE/TESTS` The service trigger was moved from the title bar into the
  collapsed service strip, replacing its duplicate text action. Only the explicit
  logo/"鏌ョ湅宸查儴缃叉湇鍔? button opens the drawer; clicking the surrounding strip does
  nothing. The desktop drawer is now up to 1180px wide with three parallel collapsible
  columns: API 浠ｇ悊涓庢ā鍨嬬綉鍏? 璐﹀彿娉ㄥ唽涓?Token 绠＄悊, and 浠ｇ悊缃戠粶涓庤妭鐐瑰伐鍏? it
  becomes one column below 900px. Full suite passes with 53 tests.
- `VERIFIED IN CODE/TESTS` The desktop deployed-services drawer now spans 87vw so
  its left edge sits near the requested 13%-from-left guide on wide screens. The
  three category columns use equal `1fr` tracks with no fixed maximum width;
  below 900px the drawer remains single-column. Full suite passes with 53 tests.
- `VERIFIED IN CODE/TESTS` Managed extension instances now have an opt-in local
  encrypted credential vault. PBKDF2-SHA256 derives a Fernet key from a user
  password; only salt/KDF metadata, field metadata, and ciphertext are persisted
  under `storage/`. The password and derived key are process-memory-only and the
  vault has an explicit lock action. Authenticated APIs cover status, setup,
  unlock, lock, metadata listing, explicit per-instance reveal, upsert, and
  delete, with writes restricted to registered GenBox-managed instances.
- `VERIFIED IN CODE/TESTS` Deployment delivery defaults to show-once and offers
  explicit encrypted local save with a warning. The deployed-services drawer
  shows saved/not-saved state and supports unlock, reveal, copy, edit, and local
  deletion. Remote admin-key reset remains separate and its one-time result can
  update the saved local copy. `node --check static/js/extensions.js` passed and
  `python -m pytest -q` passed all 58 tests on 2026-07-12.
- `VERIFIED LIVE` On 2026-07-12, local GenBox was restarted after the credential
  vault implementation (PID 19792 -> 18436). `GET /api/extensions/vault/status`
  returned HTTP 200 with an unconfigured, locked, zero-entry vault. Vault writes
  explicitly apply owner-only `0600` permissions. No VPS operation was performed.
- `VERIFIED IN CODE/TESTS` Fixed the missing card controls: every managed service
  now shows `淇濆瓨鐧诲綍淇℃伅` when no local entry exists, or `鏌ョ湅鍑瘉` / edit / delete
  through the unlocked vault when saved. The credential editor includes optional
  VPS SSH password, private key, passphrase, sudo password, service username,
  password, API key, management key, and note. User-selected VPS SSH credentials
  are now explicitly permitted in the encrypted vault; enrollment tokens, Push
  keys, and the GenBox administrator key remain prohibited. Full suite remains
  58 tests passing.
- `VERIFIED LIVE` On 2026-07-12, local GenBox was restarted again after the
  credential-control fix (PID 18436 -> 29624). The vault status endpoint returned
  HTTP 200 with the existing vault configured and locked. No VPS operation was
  performed.

## User-Confirmed Requirements

- `USER-CONFIRMED` Existing VPS chatgpt2api is a production source and must not
  be used directly for feature development.
- `USER-CONFIRMED` Development must occur on an isolated clone.
- `USER-CONFIRMED` Completed code must be sanitized, pushed to the owner's
  GitHub repository, and deployed fresh for a second verification.
- `USER-CONFIRMED` Only after clean redeployment may the work be proposed to the
  original author as PRs or an AI-oriented extension proposal.
- `USER-CONFIRMED` The Phase 1 target identity is redacted from distributable
  documentation; discovery used the user-confirmed SSH account and port.
  Credentials remain session-only and are not documented here.

## Phase 1 Acceptance Evidence

- `VERIFIED LIVE` On 2026-07-12, GenBox read-only discovery against the
  user-confirmed redacted target reported Ubuntu 24.04,
  Docker 29.6.0, Compose 5.2.0, Python 3.12.3, ~31 GB free disk, and one
  running Compose chatgpt2api instance named `chatgpt2api-warp` with data dir
  `/root/chatgpt2api/data` (`136 MB`). Source image baseline is the container
  image ID tagged `genbox-chatgpt2api-source:<12-char-container-id>`.
- `VERIFIED LIVE` On 2026-07-12, the user deployed an isolated development clone
  (instance `chatgpt2api-dev`, port `33010`, working-copy scope). The clone is
  running and healthy: the isolated clone version endpoint returned HTTP 200.
  Its console and API URLs were verified but are redacted from distributable documentation.
  Instance record persisted in `storage/extensions.json` with status `running`.
- `VERIFIED LIVE` On 2026-07-12, production `chatgpt2api-warp` remains unchanged
  (same container ID, up-time, health). Production non-mutation confirmed.
- `VERIFIED IN CODE/TESTS` Clone configuration scrubbing removes inherited
  management credentials and known GenBox Push destination, identity, and key
  fields; the clone remains Push-disabled until Phase 4 provisions a separate
  destination identity.
- Phase 1 acceptance criteria met: discovery is read-only and host-key verified;
  development clone starts and passes health checks on a non-production port;
  source and clone data/configuration targets are demonstrably different;
  production container identity, configuration, start time, and health remain
  unchanged; clone failure left the production source operational.

## In Progress

- `VERIFIED IN CODE/TESTS` The SPA now uses fixed-key bilingual strings for the
  core navigation, dashboard, image generation, video generation, media library,
  history, extension center, and major runtime status/error copy. Route-level
  language selection now honors `?lang=en` / `?lang=zh-CN` before localStorage,
  which made deterministic browser acceptance possible.
- `VERIFIED LIVE` On 2026-07-13, `GET http://127.0.0.1:8892/` returned HTTP 200.
- `VERIFIED LIVE` On 2026-07-13, browser acceptance using deterministic
  `?lang=` routes confirmed the main routes in both languages:
  `#/dashboard`, `#/generate`, `#/video`, `#/gallery`, `#/history`,
  and `#/extensions`.
- `VERIFIED LIVE` On 2026-07-13, browser interaction confirmed key modals in
  both languages:
  theme / appearance, system logs, Provider management, and remote sync. The
  final cleanup in this loop moved gallery sort labels, theme/workspace preset
  labels, and provider-modal runtime labels onto fixed translation keys so
  English no longer showed mixed Chinese status text in those verified areas.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the old first-run quick-setup
  modal was upgraded into a bilingual beginner onboarding page that keeps the
  existing quick-key inputs but adds a recommended first-run path, direct
  navigation actions, and explicit separation between core creation tasks and
  later Extensions / remote-sync work.
- `VERIFIED LIVE` On 2026-07-13, local browser automation against
  `http://127.0.0.1:8892/?lang=en#/dashboard` and
  `http://127.0.0.1:8892/?lang=zh-CN#/dashboard` forced the onboarding layer
  open and confirmed the new page title, badges, action buttons, and guide copy
  render in both languages.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the onboarding layer gained a
  repeatable `新手引导 / Getting Started` entry in both the desktop sidebar and
  bottom Dock. The entry is required in workspace personalization so it remains
  reachable after first run.
- `VERIFIED LIVE` On 2026-07-13,
  `http://127.0.0.1:8892/static/onboarding-lab.html` returned HTTP 200. The lab
  reads the production i18n table, switches Chinese/English and desktop/mobile
  preview modes, and links to the live application without weakening GenBox's
  `X-Frame-Options: DENY` / `frame-ancestors 'none'` protection. Browser checks
  confirmed both languages, a 390px mobile viewport, and no horizontal or
  button-text overflow.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the image prompt editor was aligned
  with the video prompt design language: title and hint precede the textarea,
  while the full-width primary action sits below it. Browser geometry confirmed
  both image and video buttons are 917px wide in the same viewport and remain
  below their textareas; generation handlers and element IDs are unchanged.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, onboarding was redesigned as a
  full-screen, single-surface workflow. It includes a synchronized language
  selector, dynamically rendered Provider names from Model settings, a dedicated
  chatgpt2api integration band, and a five-step post-dismissal tab tour. The old
  badges, asymmetric path card, nested cards, and visible hard-coded endpoint
  inputs were removed. Browser switching preserved the open guide across
  `zh-CN -> en`, and completing it highlighted Dashboard as step 1/5.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, Dashboard, image, and video headings
  were consolidated onto one 18px title / 8px kicker / 8px gap system. The
  final mark is a 34px transparent linear icon with no border,
  radius, or card background, removing the visual separation between icon and
  text. Browser measurements matched across all three pages. The full suite
  remains 66 tests passing.
- `VERIFIED IN CODE/TESTS` `node --check static/js/i18n.js`,
  `node --check static/js/app-all.js`, and `python -m pytest -q` all passed on
  2026-07-13 with 66 passing tests after the final bilingual cleanup.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the dashboard language selector
  was fixed for URLs that already contain `?lang=`. `setLanguage()` now updates
  the query parameter with `location.replace()` before reloading, so a stored
  English choice is no longer overwritten by a stale `?lang=zh-CN` URL. Browser
  verification switched `zh-CN -> en -> zh-CN` while preserving `#/dashboard`;
  the URL, `<html lang>`, selected option, title, and subtitle matched each
  language. The full suite remains 66 tests passing.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the Local IP visibility control
  was repaired after its former eye glyph had degraded to `??`. It now uses a
  code-defined eye / slashed-eye SVG with fixed translation keys for `显示 IP /
  隐藏 IP` and `Show IP / Hide IP`. Browser interaction verified masking,
  restoration, both icon states, and bilingual accessible labels. The full
  suite remains 66 tests passing.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the Host resources card was fixed
  after successful `/api/dashboard/resources` responses triggered a frontend
  `ReferenceError`: uptime text used `upDays` and `upMins` before declaration.
  Uptime calculation order, duplicated labels, and corrupted separators were
  corrected. The endpoint returned HTTP 200 with CPU and uptime data, and
  browser checks confirmed Chinese and English cards render CPU, memory, disk,
  network I/O, uptime, and top processes without the failure state. The full
  suite remains 66 tests passing.
- Documentation source-of-truth migration from stale `.planning` milestone
  files to the `docs/` documents referenced by `AGENTS.md`.
- Working-tree changes for the extension and Push receiver initiative are not
  yet represented as a clean release candidate.
- Phase 2/3 network automation prep: Tailscale Serve port correction, VPS
  reachability verification, and Push probe readiness.
- `VERIFIED IN CODE` The network configuration page includes an optional mobile
  onboarding QR code that opens Tailscale's official download page. It never
  embeds an Auth Key; the phone joins by signing in with the same Tailscale account.
- `VERIFIED IN CODE/TESTS` The network connection page separates first-time enrollment
  from existing-network verification. Existing verification hides the enrollment token,
  skips installation/enrollment, and checks peer reachability plus VPS-to-GenBox access.
- `VERIFIED IN CODE/TESTS` Existing-network verification no longer sends input to the
  read-only remote detection command, uses the connectivity-check stage for that command,
  and applies a 30-second detection timeout. This fixes the AsyncSSH `Channel not open for sending` failure.

## Not Yet Complete

- Durable deployment task recovery after process or browser restart.
- Full retry behavior and failure rollback for extension deployment.
- Correction of Tailscale Serve so its Tailnet-facing port proxies the actual
  GenBox listener instead of assuming both ports are identical.
- Application-level GenBox Push probes for every supported network adapter.
- Resolution of duplicate catalog IDs for two `gemini2api` repositories.
- chatgpt2api-side Push destination settings and shared sender service.
- Per-generation Push option in chatgpt2api.
- Gallery batch Push, date-range Push, scheduling, cursor, lease, and retry.
- Verified source cleanup and reclaimed-space reporting.
- Sanitized personal GitHub push and clean redeployment.
- Upstream PR or final Vibe Coding proposal.
- Live end-to-end testing across a real private network.
- Browser interaction testing of the new local credential-vault controls; local
  API, encryption-at-rest, wrong-password, CRUD, model, and wiring tests pass.

## Environment Matrix

| Environment | Purpose | Mutability | Status | Last Verified |
|---|---|---|---|---|
| Existing VPS chatgpt2api | Production source | Read-only | `VERIFIED` unchanged | 2026-07-12 |
| VPS development clone | Development and UAT | Mutable and isolated | `VERIFIED` running/healthy | 2026-07-12 |
| Local GenBox checkout | Implementation and unit tests | Mutable | `VERIFIED` tests and bilingual browser acceptance pass | 2026-07-13 |
| Personal GitHub clean deployment | Release verification | Recreate only | Not started | Never |
| Upstream contribution | PR or proposal | Review only | Not started | Never |

- `VERIFIED LIVE` On 2026-07-13, the Tailscale network workflow completed end to end: the local node reached the VPS, the VPS successfully accessed GenBox through the Tailscale Serve DNS URL, and the verified private URL was saved. The URL uses the node DNS name because Tailscale Serve host routing returns 404 when accessed by raw Tailscale IP.
- `USER-CONFIRMED` On 2026-07-13, the project owner temporarily allowed VPS public ports 8892 and 8893 before the successful retry. These public openings are not part of the intended private-network architecture and should be removed after confirming they are unnecessary.

## Runtime Facts

- `VERIFIED IN CODE/TESTS` Current Git branch is `dev` as of 2026-07-12.
- `VERIFIED IN CODE/TESTS` Application startup code listens on `0.0.0.0:8891`.
- `VERIFIED IN CODE/TESTS` Port configuration is environment-based. Development uses Tailscale Serve `8893 -> 127.0.0.1:8892`; production delivery uses `8892 -> 127.0.0.1:8891`.
- `VERIFIED IN CODE/TESTS` The current target record in `storage/extensions.json` contains a
  VPS host, SSH port, and chatgpt2api port. These values are intentionally not
  repeated here because a stored target is not evidence of a live service.
- `VERIFIED LIVE` On 2026-07-12, the redacted development VPS was reachable; running
  containers include `chatgpt2api-warp` (production, unchanged) and
  `chatgpt2api-dev` (development clone, healthy on port `33010`).
- `USER-CONFIRMED` On 2026-07-12, screenshots supplied by the project owner show
  the `chatgpt2api-dev` console accessible on port `33010`, with the image
  management page loaded and 55 images reported.
- `USER-CONFIRMED` On 2026-07-12, the Extension discovery screenshot shows both
  the managed development clone and `chatgpt2api-warp` running. The project owner
  reports that the production container ID, start time, and health state did not
  change during development-clone verification. This screenshot evidence is not
  an independent command-level comparison of the production container metadata.
- `VERIFIED LIVE` On 2026-07-12, read-only local commands found Tailscale
  `1.98.8`, `BackendState=Running`, and the Windows node online. Account identity,
  Tailnet DNS name, node keys, and overlay addresses are intentionally omitted.
- `VERIFIED LIVE` On 2026-07-12, `tailscale serve status --json` returned an empty
  configuration and local Tailscale status reported no peer device. The GenBox
  Serve mapping and VPS enrollment therefore remain pending.

## Known Documentation Debt

- `.planning/PROJECT.md` and `.planning/ROADMAP.md` cover the earlier Pull-only
  milestone and contain stale scope and environment examples.
- `.planning/STATE.md` reports 8 tests; the verified current result is 41 tests.
- `.planning/codebase/TESTING.md` predates the current `tests/` suite.
- These files remain historical artifacts and must not override this document.

- The per-card "閲嶇疆瀵嗛挜" reuses the wizard VPS form for host/port/user and the
  host key (`target()`); if the page was refreshed after deployment, re-enter the
  VPS connection info in step 1 first, then use reset. A cleaner per-instance stored
  target is a future improvement.

## Recently Changed Security Policy

- `USER-CHOICE` Secret delivery is no longer hardcoded as show-once-only. The
  default remains show-once with rotation-based recovery, but the user may opt in
  to saving a managed instance secret locally for later viewing. Local save is
  off by default, requires an explicit per-secret choice, and warns before
  enabling. User-selected VPS SSH credentials may be saved in the encrypted
  local vault; enrollment tokens, Push keys, and the GenBox administrator key are
  never saved to browser storage. Recorded as ADR-010 and
  reflected in `AGENTS.md` and `docs/extensions-deployment-contract.md`.

## Priority 1 Verification

- `VERIFIED IN CODE/TESTS` On 2026-07-12, `extensions/local_tailscale.py` separates the Tailnet-facing Serve port (`8892`) from the fixed GenBox upstream port (`8891`).
- `VERIFIED IN CODE/TESTS` `python -m pytest -q tests/test_local_tailscale.py tests/test_network_adapters.py` completed with 8 passing tests.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q --basetemp=.planning/tmp/pytest-tailscale-port-fix` completed with 61 passing tests. The default pytest temp location was inaccessible in the managed sandbox, so the successful run used a repository-local writable base temp.
- `UNVERIFIED` The corrected Serve configuration has not yet been applied to or probed across a live Tailnet.
- `VERIFIED LIVE` Local Tailscale installation and login are complete; the next
  network action is to enable the corrected local Serve mapping, then enroll the
  isolated VPS development target into the same Tailnet through the fixed
  server-side SSH command plan.

## Network Wizard Development Update

- `VERIFIED IN CODE/TESTS` Development defaults now run GenBox at
  `http://localhost:8892` and reserve Tailscale Serve port `8893`. Production
  delivery can set `GENBOX_PORT=8891` and `TAILSCALE_SERVE_PORT=8892`.
- `VERIFIED IN CODE/TESTS` The network wizard now shows separate GenBox-local and
  remote-VPS endpoint panels. The VPS panel currently enables the fully automatic
  install-and-connect path; existing-install and manual paths are visibly deferred.
- `VERIFIED IN CODE/TESTS` Network tasks now expose eight plain-language stages
  from local detection through saved destination URL. Successful Tailscale checks
  persist only provider, available-network list, destination URL, and verification
  time. Enrollment tokens are not persisted.
- `VERIFIED LIVE` On 2026-07-12, the development server listened on port `8892`.
  Browser inspection confirmed the network step displayed GenBox `8892`, planned
  private entry `8893`, and separate local/VPS panels without missing controls.
- `VERIFIED IN CODE/TESTS` Python compilation, JavaScript syntax checking, and the
  complete pytest suite passed with 61 tests.

- `VERIFIED LIVE` The Tailscale wizard now includes a direct link to the official
  Keys page, three plain-language key-generation steps, and an Auth Key field
  explicitly labeled to accept `tskey-auth-...`. Browser inspection confirmed
  both the step-3 guide and step-4 paste prompt render correctly.


- `VERIFIED IN CODE/TESTS/UI` The extension page now uses the "Extension Feature Service Management Console" header, supports mouse and keyboard navigation across steps 1-5, shows a completion banner only after successful link verification, provides a Tailscale admin-console shortcut, and persists non-secret multi-VPS deployment batch target IDs on the GenBox backend. Multi-VPS execution remains sequentially gated by per-target SSH verification and deployment planning.

## Navigation Icon And Theme UI Update

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the formal sidebar and bottom Dock
  replaced their remaining Emoji/text symbols with a unified monoline SVG icon
  language, including image generation, model settings, extensions, themes,
  logs, and refresh actions.
- `VERIFIED IN CODE/TESTS/UI` The theme dialog now fits within the browser
  viewport, keeps its footer visible, scrolls only its content area, and shows
  all 10 presets in two desktop columns or one mobile column without horizontal
  clipping.
- `VERIFIED IN CODE/TESTS/UI` Preview scheme C now renders the selected horizontal
  GenBox cube wordmark in blue on a translucent glass surface with cyan/purple
  flowing-light treatment; the icon and wordmark no longer disappear against a
  white background.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q --basetemp=.planning/tmp/icons-theme-modal-20260713`
  completed with 65 passing tests.

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, theme switching now derives the full page gradient, glass surfaces, elevated cards, inputs, borders, overlays, shadows, sidebar, and Dock from each preset. Browser checks confirmed the dashboard, generation, gallery, and extension pages contain no white primary surfaces under the Deep Space theme, while Apple Mono still renders as a coordinated light theme.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q --basetemp=.planning/tmp/theme-system-v10` completed with 65 passing tests.
- `VERIFIED IN CODE/TESTS/UI` Deep-theme Dock styling now applies to every navigation preset, not only Soft Glass. Circular icon plates, borders, and per-icon shadows are removed; Dock and sidebar share the same 1.65px monoline SVG treatment, with selection shown by text color and a small accent dot.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q --basetemp=.planning/tmp/dark-dock-v11` completed with 65 passing tests.

## Fixed-Key Bilingual Refactor

- `VERIFIED IN CODE/TESTS` On 2026-07-13, the UI language system was refactored from Chinese-text scanning plus DOM replacement to a fixed-key translation table in `static/js/i18n.js`. The previous `TreeWalker` and `MutationObserver` text-swap path was removed from `static/js/app-all.js`.
- `VERIFIED IN CODE/TESTS` `static/index.html` now loads the dedicated i18n module and uses explicit `data-i18n`, `data-i18n-title`, `data-i18n-placeholder`, and `data-i18n-aria-label` markers for static UI content instead of relying on runtime text detection.
- `VERIFIED IN CODE/TESTS` The extension center and remote sync scripts now render user-facing dynamic text through fixed translation keys. Runtime task-step labels map from backend `step.id` values to frontend translation keys rather than reusing raw Chinese labels.
- `VERIFIED IN CODE/TESTS` The main app script was repaired after an interrupted bulk replacement pass. JavaScript syntax checks now pass for `static/js/i18n.js`, `static/js/app-all.js`, `static/js/extensions.js`, and `static/js/sync.js`.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q tests/test_extensions.py tests/test_credential_vault.py` completed with 28 passing tests, including coverage that the dedicated i18n module is loaded and page-level i18n markers exist.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q` completed with 66 passing tests.
- `VERIFIED IN CODE/TESTS` On 2026-07-13, `static/js/app-all.js` migrated the remaining visible quick-prompt categories, video-provider card headings, workbench copy, provider-editor text, and history/dashboard runtime labels onto fixed i18n keys. `node --check static/js/app-all.js` and `node --check static/js/i18n.js` both pass after the changes.
- `VERIFIED IN CODE/TESTS` On 2026-07-13, the translation table was further repaired for Chinese-side corrupted values in update status text, proxy/provider dialogs, gallery actions, creator rail/task-monitor copy, and dashboard network/IP labels. The full local suite still passes with 66 tests.
- `VERIFIED UI` On 2026-07-13, in-app browser sweeps on `http://127.0.0.1:8892/` showed the English primary routes are substantially translated: Dashboard, image creation, video creation, Media Library, History, and Extensions all render their fixed-key headings and primary controls in English. User prompts, provider/model names, and remote-instance names remain intentionally untranslated.
- `VERIFIED LIVE` On 2026-07-13, deterministic `?lang=en` / `?lang=zh-CN` route sweeps and follow-up modal checks completed the Chinese and English runtime proof for the existing pages. That acceptance gate is no longer blocking onboarding work.
- `VERIFIED IN CODE/TESTS/UI` The theme catalog was curated to 10 restrained presets. Apple Mono, Deep Space Console, Graphite Workbench, and Cloud Whiteboard remain; six new presets add Gilded Night, Champagne Gold, Mist Gray, Titanium Console, Classic Book Yellow, and Ink Wash Paper. Removed preset IDs now fall back to Apple Mono instead of leaving stale mixed colors.
- `VERIFIED UI` Browser switching confirmed all 10 presets render with the correct light/dark classification. Primary text contrast ranges from 10.38:1 to 17.74:1 and secondary text contrast from 4.97:1 to 8.04:1 against their card surfaces.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q --basetemp=.planning/tmp/curated-themes-v12` completed with 65 passing tests.
## Creator Workbench And Continuous Record Update

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, image and video creation now provide separate multi-model comparison and single-model workbench modes. The single-model image workbench uses a larger prompt area, one selected provider, and a single-screen layout without page scrolling.
- `VERIFIED IN CODE/TESTS/UI` Video provider loading no longer fails when the provider-selection list initializes after the UI. Browser verification loaded the configured `Agnes` and `ark` video providers and left the video generate button available.
- `VERIFIED IN CODE/TESTS/UI` The former continuous-generation control is now presented as `每次独立生成` by default and `保留最近创作记录` when enabled. It does not automatically repeat generation and does not resend historical prompts or images to providers.
- `VERIFIED IN CODE/TESTS` Continuous records are bounded in memory to the latest 3 prompts and 12 image paths. This prevents unbounded session metadata growth while preserving lightweight grouping.
- `VERIFIED RESEARCH/CODE` Longer model context can add latency only when older tokens or media are actually included in a new provider request. Current GenBox provider payloads send only the current prompt and current reference image, so truncating the local continuous record does not change provider inference speed.
- `VERIFIED IN CODE/TESTS` Tailscale development routing remains separate from public exposure: GenBox defaults to application port `8892`, and the private Serve entry defaults to `8893 -> 127.0.0.1:8892`.
- `VERIFIED IN CODE/TESTS` `node --check static/js/app-all.js` and `python -m py_compile main.py` completed successfully.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q tests/test_local_tailscale.py tests/test_network_adapters.py --basetemp=.planning/tmp/pytest-creator-v18-network` completed with 11 passing tests.
- `VERIFIED IN CODE/TESTS` `python -m pytest -q --basetemp=.planning/tmp/pytest-creator-v18-full` completed with 65 passing tests.
## Creator Layout And Task Monitor Update

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the image workbench was reorganized into three clear zones: a central real-time preview, a collapsible right-side creation tool rail, and a collapsible bottom task monitor.
- `VERIFIED IN CODE/TESTS/UI` Low-frequency controls now live in the right tool rail: text/image/variation modes, beginner/pro prompt mode, prompt enhancement, independent/recorded generation, local upscale, and quick prompts. Existing control IDs and click handlers were preserved.
- `VERIFIED IN CODE/TESTS/UI` The prompt editor keeps the primary `生成图片` action beside it. Browser measurement at 1280x720 confirmed preview, task bar, prompt editor, and generation button are simultaneously visible with no page scrolling.
- `VERIFIED IN CODE/TESTS/UI` The task monitor reuses the existing overall progress, per-provider task status, and real-time log elements. It stays as a compact status strip while idle and expands automatically when image generation or variation starts.
- `VERIFIED IN CODE/TESTS/UI` Multi-model task status uses responsive auto-fit columns; single-model mode forces one concentrated status and log column. The right tool rail can collapse from 250-330px to 48px so the preview gains the released width.
- `VERIFIED UI` At a 943x920 viewport, the expanded tool rail measured 250px, the preview retained about 591px, and the page had no horizontal overflow. In collapsed mode, the preview expanded to about 793px.
- `VERIFIED IN CODE/TESTS` `node --check static/js/app-all.js`, `python -m py_compile main.py`, and `python -m pytest -q --basetemp=.planning/tmp/pytest-creator-layout-v20` completed successfully; the full suite passed with 65 tests.
## Creator Primary Action Merge

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the separate prompt-action card was removed. The primary generation action now sits directly at the top of the active editor card.
- `VERIFIED IN CODE/TESTS/UI` In text-to-image mode the integrated header reads `提示词 PROMPT`; in image-to-image and variation modes the same action bar moves to the active card and updates its title, hint, and button label.
- `VERIFIED UI` Browser checks confirmed the old standalone `.creator-primary-action` card count is zero, the action bar is the first child of the active editor panel, and all three image modes retain a visible working generation button.
- `VERIFIED IN CODE/TESTS` `node --check static/js/app-all.js`, `python -m py_compile main.py`, and `python -m pytest -q --basetemp=.planning/tmp/pytest-creator-action-v21` completed successfully; the full suite passed with 65 tests.
## Global Dock Auto-Hide Update

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, the bottom Dock now auto-hides on every primary page: Dashboard, image creation, video creation, Media Library, History, and Extensions.
- `VERIFIED IN CODE/TESTS/UI` Hidden mode leaves a 15px bottom reveal handle and a 24px pointer-sensitive edge. Hovering near the bottom reveals the Dock; clicking the handle pins it open, and clicking again returns it to auto-hide.
- `VERIFIED IN CODE/TESTS/UI` The Dock remains accessible by keyboard focus. Switching pages clears a temporary pin and returns the new page to automatic hiding.
- `VERIFIED UI` Browser checks across all six routes confirmed hidden mode uses opacity zero and disabled pointer interaction. Hovering the reveal handle restored pointer interaction; clicking it pinned the Dock with `aria-expanded=true`.
- `VERIFIED IN CODE/TESTS` `node --check static/js/app-all.js`, `python -m py_compile main.py`, and `python -m pytest -q --basetemp=.planning/tmp/pytest-global-dock-v26` completed successfully; the full suite passed with 65 tests.
## Navigation Routing, Language, And Icon Update

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, primary pages now expose stable hash
  routes. Image and video routes also retain the active creation type and
  single/multi-model mode, for example `#/generate/i2i/single`.
- `VERIFIED UI` Direct navigation, refresh, browser Back, and browser Forward
  restored the matching page and workbench state without route-update loops.
- `VERIFIED IN CODE/TESTS/UI` The dashboard now provides a persistent global
  Simplified Chinese / English selector. English translation covers primary
  navigation, dashboard controls, workbench controls, and common dynamic labels;
  prompts, credentials, provider/model names, and raw logs are excluded.
- `VERIFIED UI` The collapsed creator-tool rail now renders a 48px-wide,
  full-height accent handle with icon, vertical label, arrow, and a short
  attention pulse. Browser checks confirmed it remains visible and clickable.
- `VERIFIED UI` Dashboard, sidebar, and Dock now use the same stacked-image SVG
  for Media Library. DOM comparison confirmed all three SVG definitions match.
- `VERIFIED UI` At `1280x720` and `943x920`, the image workbench had no page or
  horizontal overflow. The prompt action remained visible and the hidden Dock
  retained disabled pointer interaction.
- `VERIFIED IN CODE/TESTS` `node --check static/js/app-all.js`,
  `python -m py_compile main.py`, and
  `python -m pytest -q --basetemp=.planning/tmp/pytest-i18n-routing-v24`
  completed successfully; the full suite passed with 65 tests.

## Enterprise Page Heading Update

- `VERIFIED IN CODE/TESTS/UI` On 2026-07-13, Dashboard, image creation,
  video creation, Media Library, and History now share one compact enterprise
  heading system: theme-colored monoline mark, product-area label, primary
  title, and supporting description. Emoji were removed from these headings.
- `VERIFIED UI` Apple Mono and Deep Space themes both derive heading surfaces,
  icon color, border, and accent treatment from the active theme variables.
- `VERIFIED UI` At `943x920`, all five routes rendered without page or
  horizontal overflow. At `1280x720`, the single-model image heading remained
  about 66px high and the prompt editor stayed fully visible.
- `VERIFIED IN CODE/TESTS` `node --check static/js/app-all.js`,
  `python -m py_compile main.py`, and
  `python -m pytest -q --basetemp=.planning/tmp/pytest-enterprise-headings-v25`
  completed successfully; the full suite passed with 65 tests.

## Shared Heading And Onboarding Refinement

- `USER-CONFIRMED` On 2026-07-14, the owner-approved refinement plan was
  recorded in `docs/ONBOARDING-UI-CONTRACT.md`.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-14, Dashboard, Images, Video, Media
  Library, History, and Extensions now use one shared three-line heading rhythm
  for kicker, title, and supporting description, with aligned spacing and no
  separate decorative icon card.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-14, onboarding replaced the Provider
  name strip with a six-card capability overview that summarizes image creation,
  planned local inpainting, video creation, media organization, prompt
  assistance, and no-code extension management without exposing Provider names,
  endpoints, or keys.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-14, onboarding now reuses the live
  GenBox sidebar logo SVG and removes the temporary `GX` monogram from the
  guide surface.
- `VERIFIED RESEARCH/CODE/TESTS/UI` On 2026-07-14, onboarding now follows four
  explicit stages: three-minute first creation, GenBox capability overview,
  chatgpt2api introduction, and a plain-language explanation of why the two
  products connect. The chatgpt2api introduction is distilled from the public
  `yukkcat/chatgpt2api` README and covers its OpenAI-compatible gateway,
  conversation/image workspace, account/proxy diagnostics, and self-hosted
  storage, with a visible third-party reverse-engineering risk note.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-14, the GenBox connection section uses
  the beginner-facing model of a remote creation station plus a local media
  library, while still separating currently available deployment/private
  networking/Pull/receiver foundations from planned sender Push, batch and
  scheduled transfer, verified cleanup, and release-gate work.
- `VERIFIED IN CODE/TESTS/UI` On 2026-07-14, `static/onboarding-lab.html` was
  updated to mirror the live capability-matrix and integration-overview design.
- `VERIFIED IN CODE/TESTS` On 2026-07-14, `node --check static/js/i18n.js`,
  `node --check static/js/app-all.js`, and `python -m pytest -q` all passed;
  the suite remains 66 passing tests.
- `VERIFIED LIVE` On 2026-07-14, local browser acceptance against
  `http://127.0.0.1:8892/` passed in both `zh-CN` and `en` at `1280x720`,
  `1033x1074`, and `390x844`, covering the six primary routes, onboarding, and
  `static/onboarding-lab.html`, with no horizontal overflow and no regression
  to Provider-name onboarding content.

## Next Tasks

1. Gather owner review on the local `8892` implementation of the heading and
   onboarding refinement before starting another UI pass.
2. Keep subsequent work in the pre-Push UI scope unless the project owner
   explicitly authorizes entry into chatgpt2api sender Push development.
3. Preserve the local accepted baseline: `node --check static/js/i18n.js`,
   `node --check static/js/app-all.js`, `python -m pytest -q`, and bilingual
   browser acceptance on `1280x720`, `1033x1074`, and `390x844`.

## Resume Instructions

Phase 1 remains accepted. Resume with `AGENTS.md`, `HANDOFF.md`, this file, and
`docs/ONBOARDING-UI-CONTRACT.md`. The heading/onboarding refinement is now
implemented and locally accepted on port `8892`; the next session should begin
from owner review or follow-up polish, not from the old Provider-strip plan.
Keep all work local on port `8892`, preserve production `chatgpt2api-warp`, and
do not enter the sender Push phase unless explicitly redirected. The current
verified baseline is 66 passing tests plus bilingual browser acceptance on
2026-07-14.
