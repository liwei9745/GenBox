# Changelog

All notable changes to GenBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Cross-platform desktop builds (Windows, macOS, Linux)
- GitHub Actions CI/CD workflow
- PyInstaller build configuration
- Release notes template

### Changed
- Updated main.py for PyInstaller path compatibility
- Updated config.py for PyInstaller path compatibility
- Improved headless Linux server support

### Fixed
- CORS security configuration
- SSL verification options
- Admin key hashing
- Rate limiting for API endpoints
- Security headers

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
