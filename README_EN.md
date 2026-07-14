# GenBox - Local-First AI Creation and Media Workspace

[![CI](https://github.com/liwei9745/GenBox/actions/workflows/build.yml/badge.svg)](https://github.com/liwei9745/GenBox/actions/workflows/build.yml)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue?logo=docker)](https://github.com/liwei9745/GenBox/pkgs/container/genbox)
[![Python](https://img.shields.io/badge/Python-3.12-yellow?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/github/license/liwei9745/GenBox)](LICENSE)

GenBox combines image generation, video generation, prompt assistance, media management, history, and remote-service operations in one local web workspace. It can run as a desktop client or on a NAS, VPS, or Docker host.

> [!IMPORTANT]
> **v2.5.0 is a major experience and infrastructure update.**
> It adds the Extension Center, guided chatgpt2api deployment and private networking, bilingual UI, four-stage onboarding, shared page headings, an encrypted credential vault, and a verified release pipeline. GenBox includes remote Pull and an authenticated idempotent Push receiver foundation. Sender-side automatic Push, batch and scheduled transfer, and verified cleanup are still future phases.

**Current release candidate: v2.5.0** · [Release notes](release-notes-v2.5.0.md) · [Changelog](CHANGELOG.md) · [Releases](https://github.com/liwei9745/GenBox/releases)

![GenBox Dashboard](screenshots/sanitized/01-dashboard.png)

> Hostname, capacity, and runtime values in the Dashboard screenshot are explicitly labeled demo data and do not identify a real device.

## Highlights

![GenBox Extension Center](screenshots/sanitized/03-extension-center.png)

- Single- and multi-model workspaces for image and video generation.
- Text-to-image, image-to-image, variation, upscaling, text-to-video, image-to-video, and keyframe flows.
- Searchable media library, history, batch actions, and prompt reuse.
- Guided isolated chatgpt2api deployment, private-network preparation, and managed instance delivery.
- Remote Pull into the local media library and a secure GenBox Push receiver foundation.
- Chinese and English UI, coordinated themes, shared page headings, and beginner onboarding.
- Windows, macOS, Linux, and Docker release artifacts with startup smoke tests and SHA-256 checksums.

![GenBox multi-model image workspace](screenshots/sanitized/02-generate-workspace.png)

![GenBox beginner onboarding](screenshots/sanitized/04-onboarding.png)

## Quick Start

### Desktop client

Download the platform archive from [Releases](https://github.com/liwei9745/GenBox/releases/latest). Python is not required.

| Platform | Archive | Start |
|---|---|---|
| Windows | `GenBox-Windows.zip` | Double-click `GenBox.exe` |
| macOS | `GenBox-macOS.zip` | `chmod +x GenBox-macOS && xattr -c GenBox-macOS && ./GenBox-macOS` |
| Linux | `GenBox-Linux-x64.zip` | `chmod +x GenBox-Linux-x64 && ./GenBox-Linux-x64` |

Open `http://localhost:8891` if the browser does not open automatically. Store the first-run administrator key in a password manager.

### Docker Compose

Download `GenBox-Docker-Compose-v2.5.0.zip`, extract it, then run:

```bash
cp .env.example .env
docker compose pull
docker compose up -d
```

Read the first administrator key with `docker compose logs genbox`; it is persisted to the mounted `.env`. Runtime data stays in `./storage`. Set `ALLOWED_ORIGINS` to the real HTTPS or private-network URL before remote access.

### Source

```bash
git clone https://github.com/liwei9745/GenBox.git
cd GenBox
python -m venv .venv
python -m pip install -r requirements.txt
python main.py
```

Source development uses port `8892` from `.env.example`; release clients and Docker use `8891`.

## chatgpt2api and GenBox

Think of chatgpt2api as a creation station on a remote server and GenBox as your own media library.

- chatgpt2api exposes implemented ChatGPT web capabilities through compatible APIs and manages accounts, proxies, diagnostics, and remote images.
- GenBox provides creation workflows, long-term media organization, history, prompt reuse, deployment, and connection management.
- Today GenBox can guide deployment, establish a private link, and Pull remote images.
- Automatic sender Push, batch and scheduled transfer, and receipt-gated cleanup remain future work.

chatgpt2api is a third-party reverse-engineering research project and can put accounts at risk. Do not test with important or high-value accounts.

## Security Boundaries

- Never commit `.env`, `storage/`, vaults, logs, user media, or real credentials.
- Existing production chatgpt2api instances stay read-only during development.
- GenBox administrator credentials and per-source Push keys are separate.
- Source media is retained by default; cleanup requires an authenticated matching receipt and explicit opt-in.
- The browser submits structured deployment intent, never arbitrary remote shell commands.

## Documentation

- [Product](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decisions](docs/DECISIONS.md)
- [Current status](docs/STATUS.md)
- [Roadmap](docs/ROADMAP.md)
- [Documentation maintenance map](docs/DOCUMENTATION-MAP.md)

## Development

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Build dependencies live in `requirements-build.txt`. The release workflow builds all three desktop clients, starts each packaged application, creates the Docker Compose bundle, and publishes SHA-256 checksums.

## License

[MIT](LICENSE)
