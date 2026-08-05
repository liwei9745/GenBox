# Changelog

All notable GenBox changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### In Progress

- Phase 6 sender candidate `5d1b9cd` now requires host-issued signed cleanup
  attestation artifacts. Windows and clean Linux security tests pass; macOS
  CI and independent A9 review remain pending. Cleanup remains disabled.

- Fixed the managed isolated-image update feedback chain: `Confirm update` now
  returns a task ID, the UI polls sanitized progress and terminal state, and
  refresh recovery rediscovers active/interrupted tasks without replaying them.
  Persisted task records now use a strict public schema, overlapping polls are
  prevented, and a local registration failure rolls the remote update back.
  Local verification passes `586` tests.
- Applied the reviewed immutable sender image once through GenBox's controlled
  path to the isolated port `33010` instance. The managed task reached
  `completed / 100%`, the sender health endpoint passed, and production port
  `33018` was not connected or changed.
- Rebound the single GenBox-owned stale private-entry route from an unidentified
  old runtime to the current `8910 / 21fd3ad` lab. A sender-side Push v1 probe
  then passed. One recoverable Push produced matching source/receiver SHA-256
  evidence, an idempotent `already imported` result, and source retention.

- Phase 6 source-cleanup contracts are now documented for the isolated sender:
  default retention, validated GenBox v1 receipts, SHA-256 rechecks,
  storage-rooted deletion, crash recovery, server-side environment gates, and
  adversarial test cases.
- Destructive cleanup is still disabled. The contracts are not an
  implementation, a deployment, or a stable-release feature claim.
- The isolated sender's current implementation candidate is commit `f0d5beb`.
  It includes shared cleanup/settings coordination, final destination and
  policy rechecks, platform-specific exact deletion, duplicate-receipt
  rejection, bounded streamed receipt parsing, durable crash-intent recovery,
  a real FastAPI lifespan recovery test, and a real local chunked slow-drip
  Push test. The full sender suite passes `121` tests with `5` platform skips.
- The independent A1-A12 review still blocks merge and destructive execution.
  The current sender source subsequently passed `102` Linux tests with one
  Windows-only platform skip, adding direct POSIX replacement-race, hard-link,
  symlink, exchange, crash-recovery, cross-process claim, and bounded-transport
  evidence for A4/A7/A12. A fresh independent review is still required, and A9
  remains open for authorized per-item isolated deletion ownership evidence.
  Cleanup stays disabled.
- Ran the isolated `33010` cleanup preview without executing deletion. The
  sender reported cleanup disabled, environment class `unknown`, and execute
  unavailable; one candidate was retained with reason
  `cleanup-policy-disabled`. No cleanup execute endpoint was called, and
  GenBox selected or sent no control-plane operation to production `33018`.
- Commit `f0d5beb` is published on the owner's experimental sender branch, and
  its immutable GHCR image was applied only to the isolated sender. Publication
  and isolated update evidence do not override the remaining destructive
  cleanup and release-review blocks.
- Sender commit `96d57de` is now published on the same experimental branch.
  It adds a POSIX write lease and Windows write-sharing fence, final and post-
  tombstone content checks, deterministic interrupted-cleanup artifacts, and
  real multi-process exchange/tombstone/audit-boundary crash tests. Local
  verification passes `130` Linux tests with one skip and `121` Windows tests
  with ten skips. No image from this commit has been deployed.
- Sender commit `1463c69` closes the Phase 6 A7 recovery-audit failure. A
  recovery audit write error now leaves a persisted terminal `delete_unknown`,
  and the FastAPI lifespan regression verifies that startup completes without
  deleting the source. Clean verification passes `131` Windows tests with `17`
  skips and `147` Linux-container tests with one skip. This does not authorize
  cleanup: A4, A9, isolated execution, and release publication remain blocked.
- Sender commit `9e475cb` closes the Phase 6 A4 Windows hard-link race. Before
  deletion it re-hashes the opened source and checks opened-handle, path, and
  link-count identity again; a real Windows concurrent hard-link race retains
  both source names. Clean verification passes `132` Windows tests with `17`
  skips and `147` Linux-container tests with two skips. A9, isolated execution,
  independent re-review, and release publication remain blocked.
- Sender commit `3acb1e8` closes the A9 implementation gap: cleanup capability
  is issued from a protected startup attestation and held in process memory;
  copied clone state, marker, environment, or replayed capability cannot grant
  authority. Receipt/state/audit/lease records are bound to the runtime identity
  digest. Windows verification passes `137` tests with `17` skips and clean
  Linux-container verification passes `152` tests with `2` skips. No cleanup
  execution or connection to `33010`/`33018` was performed; independent review
  and isolated positive ownership acceptance remain blocked.
- Sender commit `bd9ec81` fixes the explicit attestation-path fallback and
  passes `138` Windows tests with `17` skips plus `153` clean Linux-container
  tests with `2` skips. Independent A9 review found that the application still
  signs its own attestation from environment claims, so A9 remains blocked
  pending a host/launcher-issued signed deployment record.

### Planned

- Receipt-gated source cleanup and reclaimed-space reporting (Phase 6).
- Upstream delivery proposal and reviewable PR slices after the clean-release gate.

### Completed In Experimental Branch

- Completed isolated Phase 5 batch and scheduled incremental Push acceptance:
  interruption recovery, failed-only retry, late-arriving image discovery,
  concurrent schedule lease rejection, bounded retry, and source retention.
- Published the experimental sender branch and immutable GHCR image used by the
  isolated sender; the production instance remains unchanged.
- Rebuilt GenBox and the sender from clean GitHub clones, ran their full local
  suites, and verified loopback-only startup from those clean builds.
- Completed the tracked-file and Git-history sanitization review; only test
  sentinels, documentation placeholders, and synthetic network fixtures were
  found.

### Release Boundary

- These entries describe the experimental branch, not a new stable GenBox tag.
- The frozen `v2.5.1` notes remain unchanged until a separately approved
  version tag and GitHub Release are created.

## [2.6.0-rc.1] - 2026-08-05

### Experimental Candidate

- Prepared the client experimental candidate for the completed GenBox and
  chatgpt2api integration: single-image Push, batch Push, and scheduled
  incremental Push remain available with source retention by default.
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
