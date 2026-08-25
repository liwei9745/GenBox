# Changelog

All notable GenBox changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [2.6.4] - 2026-08-25

- Fixed: Packaged Windows first-run setup and startup summaries now show
  bilingual Chinese/English guidance with UTF-8 output.
- Fixed: Image generation uses the visible quantity control and ignores stale
  cached values; invalid quantities fail safe to one image.

## [2.6.3] - 2026-08-24

- Fixed: Provider forms no longer send masked API-key placeholders as real
  credentials after reload.
- Fixed: Provider model discovery preserves multi-key and endpoint settings and
  retries valid effective keys for OpenAI-compatible `/models` endpoints.
- Fixed: Store installed projections remain scoped to the active Store target
  in multi-target configurations.
- Fixed: Windows launchers set UTF-8 console/Python output and show bilingual
  startup and failure guidance.
- Security: masked or unavailable credentials fail closed and require explicit
  re-entry instead of being transmitted upstream.

## [2.6.1] - 2026-08-21

- Added: managed per-source deletion-grant capability in the Extension Center,
  default off, so a Push receipt can carry `safe_to_delete_source=true` only for
  an explicitly granted source that committed this exact path and content.
- Added: bilingual (zh-CN/en) controls and messages for the deletion grant, with
  a browser-contract test.
- Changed: current version is 2.6.1; Docker Compose image default pinned to
  `ghcr.io/liwei9745/genbox:2.6.1`.
- Security: source-file cleanup remains disabled by default; a receipt never
  grants deletion unless the managed source owner explicitly enabled the grant.

## [2.6.0] - 2026-08-20

### Added

- Extension Center guided deployment for isolated `chatgpt2api` instances with
  managed-instance delivery.
- Authenticated image Push receiving into the GenBox media library: single-
  image Push, manual batch Push, and scheduled incremental Push, with source
  validation, content-hash deduplication, metadata import, and receipts.
- Managed Push-source provisioning with show-once credentials and an explicit
  encrypted local credential-vault opt-in.
- Packaged-client pre-release version ordering support for the in-app updater.

### Changed

- Current version is `2.6.0`; Docker Compose defaults are pinned to
  `ghcr.io/liwei9745/genbox:2.6.0`.

### Security

- Push Keys remain unsaved by default; encrypted local-vault saving requires
  explicit opt-in after the vault is unlocked.
- Source-file cleanup remains disabled; Push receipts grant no source-deletion
  permission.

### Verification

- Recorded rc.8 local evidence (2026-08-10): focused regression `260 passed`;
  exact-candidate full suite `617 passed`; Windows packaged client built and
  passed a loopback smoke; JavaScript syntax, diff-whitespace, and credential
  scans passed.
- Stable packaging prep (2026-08-20): `tests/test_release_packaging.py` passes
  `11` tests, `tests/test_sync_push_routes.py` passes `27`, and
  `tests/test_push_sources.py` `tests/test_credential_vault.py`
  `tests/test_extensions.py` pass `237`. JavaScript syntax checks, README Lab
  regeneration, and Python compilation pass. See `docs/STATUS.md` for the
  exact commands and results.

## [Unreleased]

### In Progress / Experimental

- Sender-side cleanup and upstream delivery for the chatgpt2api integration
  remain separate work and are not claimed by the v2.6.0 stable release.
- Cleanup stays disabled; sender-side and clean-redeployment evidence remain
  pending as separate release gates.
- Historical Phase 6 development detail for the isolated sender (candidate
  commits, the A1-A12 adversarial review, isolated-port operations, and
  preview dry-runs) is recorded in `docs/STATUS.md` and the phase roadmap.

### Planned

- Receipt-gated source cleanup and reclaimed-space reporting (Phase 6).
- Upstream delivery proposal and reviewable PR slices after the clean-release
  gate.

## [2.6.0-rc.8] - 2026-08-09

- Unified manual-UAT candidate replacing rc.7; no stable release is implied.
- Added persistent Dock modes for automatic hiding, locked visible, and locked
  hidden. Only the bottom-center 40% reveal zone responds in automatic mode.
- Fixed the Push Key local-save choice so it is a clear, standard checkbox next
  to its explanatory text, remains off by default, and is unavailable without
  a newly created or rotated key.
- Fixed both Push configuration copy actions to use real line breaks.
- Replaced the Push Key save path's native browser confirmation with a visible
  GenBox confirmation dialog. Canceling requests no server confirmation token;
  confirming retains the existing unlocked-vault and 120-second single-use
  server confirmation requirements.
- Split Push status into configured, source revocation state, local-copy state, and
  remote authentication. The UI reports remote authentication as unverified
  unless real evidence exists, and never equates a local source record with an
  active remote sender.
- Saved Push fields in the general credential window are view-and-copy only;
  creating, rotating, or saving a Push Key remains restricted to the dedicated
  confirmation flow.
- Cleanup remains disabled unless separately enabled. Without that opt-in,
  receipts grant no source-file deletion permission.

## [2.6.0-rc.7] - 2026-08-07

- Final testing candidate replacing rc.6; no stable release is implied.
- Fixed independent show/hide controls for every sensitive field in the local
  credential window. SSH private keys are safely masked by default.
- Fixed the responsive, long-credential window so its content scrolls within
  the viewport and Cancel, Delete, and Save remain reachable on small screens.
- Push Keys remain unsaved by default. Local encrypted-vault saving still
  requires explicit user confirmation after the vault is unlocked.
- Cleanup remains disabled unless explicitly enabled. Without that opt-in,
  receipts grant no source-file deletion permission.

## [2.6.0-rc.6] - 2026-08-07

- Final testing candidate replacing rc.5 after its manual acceptance click
  path did not pass; no stable release is implied.
- Fixed the deployed-service `Manage Push configuration` entry. It now opens a
  visible GenBox Push configuration modal bound to the selected instance rather
  than closing the service drawer and navigating to a hidden deployment step.
- Push Keys remain unsaved by default. Local encrypted-vault saving requires
  the user's explicit confirmation after the vault is unlocked.
- Cleanup remains disabled unless explicitly enabled. Without that opt-in,
  receipts grant no source-file deletion permission.

## [2.6.0-rc.5] - 2026-08-07

- Final testing candidate replacing rc.4; no stable release is implied.
- Clarified the Chinese Push Key guidance and fixed stale browser cache/state
  handling, so an older asynchronous response cannot erase a newly created or
  rotated key state.
- A new Push Key is available only immediately after creation or rotation.
  Local encrypted-vault saving remains off by default and requires the user's
  explicit confirmation before the current key is saved.
- Cleanup remains disabled and Push receipts grant no source-deletion
  permission.

## [2.6.0-rc.4] - 2026-08-06

- Final testing candidate replacing the blocked rc.3 candidate; no stable
  release is implied.
- Push Keys are not saved locally by default. Local encrypted-vault saving
  requires explicit user confirmation and a short-lived, single-use server
  confirmation credential bound to the managed instance, source, and current
  Push Key hash; browser requests cannot bypass that server validation.
- Push receipts now fail closed: while cleanup is not explicitly enabled, they
  always return `safe_to_delete_source=false` and do not grant source deletion
  permission.

## [2.6.0-rc.3] - 2026-08-06

- Final testing candidate replacing the unsuitable rc.1 and original rc.2
  candidates; no stable release is implied.
- Frozen the Push Key vault behavior: saving is opt-in after explicit user
  confirmation, the default is no local save, locked vault contents cannot be
  read, rotation requires fresh confirmation, and local deletion leaves the
  remote Push source unchanged.

## [2.6.0-rc.2] - 2026-08-06

- Revised ADR-022 and aligned Push Key handling with the encrypted local vault.
- Push Keys are shown once by default; only explicit user confirmation enables
  local encrypted-vault saving. Rotation requires fresh consent and local
  deletion leaves the remote source unchanged.

## [2.6.0-rc.1] - 2026-08-05

### Experimental Candidate

- Prepared the client experimental candidate for the completed GenBox and
  chatgpt2api integration: single-image Push, batch Push, and scheduled
  incremental Push remain available with source retention by default.
- Added management of Push configuration for deployed chatgpt2api instances:
  users can copy the destination URL, source ID, and Push key, then explicitly
  save or reopen that configuration from the encrypted local credential vault.
- Added pre-release version ordering support for the packaged-client updater.

### Release Boundary

- `v2.6.0-rc.1` is an experimental candidate only. No stable tag or GitHub
  Release is created by this change.
- Source-file cleanup remains disabled and is not a usable candidate feature.
- Phase 6 security gates remain outside this candidate; unresolved A1, A2, A3,
  A10, and A11 findings continue to block any stable release or cleanup claim.

## [2.5.1] - 2026-07-16

### Security

- Removed unauthenticated HTTP first-run setup actions and made production
  startup fail closed when `ADMIN_KEY` is missing.
- Made setup-status handling and login recovery fail closed in the browser;
  stale asynchronous authentication responses cannot replace newer state.

### Fixed

- Applied local desktop first-run mode in the current process, with loopback
  binding and no generated administrator key.
- Pinned the Docker Compose default image to `ghcr.io/liwei9745/genbox:2.5.1`
  instead of a moving `latest` tag.

## [2.5.0] - 2026-07-14

### Added

- Extension Center navigation, catalog, VPS targets, SSH host-key confirmation, read-only discovery, fixed deployment plans, isolated chatgpt2api deployment, and managed-instance delivery.
- Tailscale local/VPS preparation, private-link verification, saved destination metadata, and multi-VPS planning controls.
- Encrypted local credential vault with explicit setup, unlock, reveal, update, delete, and lock operations.
- Authenticated, idempotent `POST /api/sync/push` receiver with source identity, SHA-256 validation, deduplication, metadata import, and receipts.
- Fixed-key Chinese and English translations across primary routes and key dialogs.
- Four-stage onboarding covering first creation, GenBox capabilities, chatgpt2api, and connection value.
- Single-model and multi-model image/video workspaces, collapsible creator tools, task monitor, and persistent hash routes.
- Docker Compose release bundle based on the GHCR image, derived from the approach proposed by @yukkcat in PR #4.
- Separate runtime, development, and PyInstaller build requirements.
- Three-platform packaged-client startup smoke tests and release SHA-256 checksums.
- Release packaging tests and deterministic Docker bundle generation.
- Packaged-client self-update tests covering exact release-asset selection and Windows post-exit replacement.

### Changed

- Unified Dashboard, Images, Video, Media Library, History, and Extensions headings.
- Replaced runtime DOM text scanning with explicit i18n keys.
- Curated the theme catalog to ten coordinated light and dark presets.
- Development defaults use `8892`; desktop and Docker release defaults use `8891`.
- Docker Compose pulls `ghcr.io/liwei9745/genbox:latest` instead of building source locally.
- Centralized version metadata in `genbox_version.py`.
- README and documentation were reorganized into pinned, rolling, release-frozen, and historical classes.
- Packaged-client updates now reject archive payloads and replace the executable only after the running process exits.
- Replaced the legacy screenshot gallery with current v2.5.0 Dashboard, image workspace, Extension Center, and onboarding captures; host-specific Dashboard values are reproducibly replaced with labeled demo data.

### Security

- Production chatgpt2api remains read-only; deployment uses isolated resources and generated credentials.
- Managed-instance secrets default to show-once and require explicit opt-in for encrypted local storage.
- GenBox administrator and Push source credentials remain separate.
- Runtime data, local memory, raw screenshots, private environment identities, and tool output are excluded from release candidates.
- Source cleanup remains disabled until authenticated receipt and hash gates are implemented end to end.

### Fixed

- Windows packaged-client first-run crash when GBK console output encountered Unicode symbols.
- AsyncSSH privileged-command channel sequencing and sudo application for isolated clone operations.
- Dashboard language switching with existing `?lang=` parameters.
- Host-resource uptime rendering and Local IP visibility controls.
- Video-provider initialization, creator action placement, and Dock auto-hide behavior.

### Verification

- 70 automated tests pass.
- Fresh isolated dependency installation and tests pass.
- Windows PyInstaller client builds and passes a real HTTP startup smoke test.
- Chinese/English desktop, narrow, and mobile onboarding checks pass without horizontal overflow.

## [2.4.1] - 2026-07-10

### Changed

- Reworked the cloud-sync dialog into a guided three-step chatgpt2api workflow.
- Improved terminology, filtering, selection, and import feedback.

## [2.4.0] - 2026-07-10

### Added

- GenBox-initiated remote image Pull from compatible chatgpt2api deployments.
- Date filtering, content deduplication, source metadata, prompt recovery, and cloud-source tags.

## [2.3.2] - 2026-07-10

### Added

- Theme and UI refinements following the security and update-system release.

## [2.3.1] - 2026-07-09

### Fixed

- Follow-up packaging and update-system corrections.

## [2.3.0] - 2026-07-09

### Added

- Automatic update checks and GitHub mirror testing.
- API-key masking, SSRF protection, CSRF validation, and stricter CSP headers.
- Production-mode first-run setup and administrator authentication.
- Per-provider proxy bypass and expanded environment documentation.

## [2.2.0] - 2026-07-09

### Added

- Image-to-image reference layout, video placeholders, gallery picker, and model filtering.
- Detailed generation failure logging.

### Fixed

- Image/video lightbox transfer, placeholder visibility, and gallery provider filtering.

## [2.1.0] - 2026-07-09

### Added

- Provider capability declarations and quick image/video actions.

### Fixed

- Dock alignment, hover behavior, and video fallback lists.

## [2.0.0] - 2026-07-09

### Added

- Cross-platform Windows, macOS, and Linux clients.
- Production authentication and first-run runtime selection.
- Headless Linux support.

## [1.0.0] - 2026-07-08

### Added

- Frosted-glass UI, Dock navigation, multi-provider generation, media management, and Docker support.

## [0.9.0] - 2026-07-07

### Added

- Multi-provider image generation, video generation, Media Library, and Dashboard monitoring.

## [0.1.0] - 2026-07-01

### Added

- Initial GenBox release and basic provider configuration.
