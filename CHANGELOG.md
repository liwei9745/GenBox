# Changelog

All notable GenBox changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- chatgpt2api sender-side per-generation Push.
- Batch and scheduled incremental transfer with durable cursor, retry, and lease.
- Receipt-gated source cleanup and reclaimed-space reporting.
- Durable extension deployment-task recovery after process restart.
- Clean GitHub redeployment acceptance and upstream delivery gates.

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
