# Changelog

All notable changes to GenBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] - 2026-07-09

### Added
- **Auto-update system**: version detection, GitHub CDN mirror testing, source/exe/docker update support
- **Security hardening** (Strix audit):
  - API Key masking: `/api/providers` no longer returns raw keys, shows `api_key_masked` instead
  - SSRF protection: private IP blackhole (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, etc.)
  - CSP header: `script-src 'self' 'unsafe-inline'`, `frame-ancestors 'none'`
  - CSRF protection: Origin/Referer header validation for POST/PUT/DELETE
- Provider modal "系统更新" section with mirror speed test

### Changed
- Authentication mode: dev mode no auth, prod mode requires ADMINKEY (unchanged, by design)

---

## [2.2.0] - 2026-07-09

### Added
- i2i layout: reference image (20%) + prompt (80%) side-by-side
- Video preview placeholder cards with spinner animation (4:3 ratio)
- Video page gallery picker with model filter dropdown
- Gallery picker shows source model name for each image
- Close button in provider modal (red background, more visible)
- Video model dropdown filters out image-only models
- Failed generations write detailed errors to logs.jsonl

### Changed
- `/api/generate` now returns `provider_states` in initial response for immediate placeholder creation
- `/api/preview/images` returns 40 items (up from 20) with model info
- Video preview placeholders use same style as image placeholders (`.prev-card.generating`)

### Fixed
- i2i generation not showing placeholder spinner (`.hidden` class with `!important` overrode inline styles)
- Lightbox "send to i2i" sending URL instead of base64 (backend decode failure)
- Lightbox "send to video" sending URL instead of base64
- Video page gallery picker only showing current model's images
- Video generation failing immediately when using images from lightbox

---

## [Unreleased]

### Added
- Provider capabilities system for explicit i2i/i2v support declaration
- Capabilities UI in provider settings (image: t2i/i2i, video: t2v/i2v)
- Dynamic capabilities section updates when changing provider type
- Quick action buttons in lightbox (图生图/生视频)
- Quick action buttons in gallery overlay
- Video model fallback list for better UX

### Changed
- Capabilities checkboxes now show only relevant options per provider type
- Improved error messages for model fetching

### Fixed
- Dock alignment and visual consistency
- Hover effects for dock action items

---

## [2.0.0-test.6] - 2026-07-09

### Fixed
- macOS and Linux binary name conflict
- Headless Linux server compatibility (no display)

---

## [2.0.0-test.1] - 2026-07-09

### Added
- Initial cross-platform desktop builds
- Windows executable (GenBox.exe)
- macOS executable (GenBox-macOS)
- Linux executable (GenBox-Linux)

---

## [1.0.0] - 2026-07-08

### Added
- Frosted glass UI redesign
- Mac-style dock navigation
- Multi-provider parallel generation
- Grouped previews with lightbox
- Resizable panels
- Docker support
- Sanitized screenshots
- English README

### Changed
- Complete UI overhaul from dark theme to frosted glass
- Single HTML file architecture to modular CSS/JS
- Provider protocol detection (URL-first)

### Fixed
- Image preview z-index issues
- Video lightbox prompt display
- Resize handle functionality
- Cache versioning

---

## [0.9.0] - 2026-07-07

### Added
- Multi-provider image generation
- Video generation support
- Media library management
- Dashboard with system monitoring

---

## [0.1.0] - 2026-07-01

### Added
- Initial release
- Basic image generation
- Provider configuration
