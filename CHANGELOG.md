# Changelog

All notable changes to GenBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
