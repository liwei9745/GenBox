# GenBox - Local-First AI Creation and Media Workspace

[![CI](https://github.com/liwei9745/GenBox/actions/workflows/build.yml/badge.svg)](https://github.com/liwei9745/GenBox/actions/workflows/build.yml)
[![GitHub Stars](https://img.shields.io/github/stars/liwei9745/GenBox?style=flat&logo=github)](https://github.com/liwei9745/GenBox/stargazers)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue?logo=docker)](https://github.com/liwei9745/GenBox/pkgs/container/genbox)
[![Python](https://img.shields.io/badge/Python-3.12-yellow?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/github/license/liwei9745/GenBox)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/liwei9745/GenBox/pulls)
[![DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/liwei9745/GenBox)

GenBox combines image generation, video generation, prompt assistance, media management, history, and remote-service operations in one local web workspace. It can run as a desktop client or on a NAS, VPS, or Docker host.

> Found GenBox useful? Star the [repository](https://github.com/liwei9745/GenBox/stargazers), report issues through [GitHub Issues](https://github.com/liwei9745/GenBox/issues), or join the [GenBox / ChatGPT2API QQ group](https://qm.qq.com/q/yegwCqJisS).

> [!IMPORTANT]
> **v2.5.0 is a major experience and infrastructure update.**
> It adds the Extension Center, guided chatgpt2api deployment and private networking, bilingual UI, four-stage onboarding, shared page headings, an encrypted credential vault, and a verified release pipeline. GenBox includes remote Pull and an authenticated idempotent Push receiver foundation. Sender-side automatic Push, batch and scheduled transfer, and verified cleanup are still future phases.

**Current stable release: v2.5.0** · [Release notes](release-notes-v2.5.0.md) · [Changelog](CHANGELOG.md) · [Releases](https://github.com/liwei9745/GenBox/releases)

![GenBox Dashboard](screenshots/sanitized/01-dashboard.png)

> Hostname, capacity, and runtime values in the Dashboard screenshot are explicitly labeled demo data and do not identify a real device.

## Contents

- [Highlights](#highlights)
- [Quick Start](#quick-start)
- [Capabilities](#capabilities)
- [chatgpt2api and GenBox](#chatgpt2api-and-genbox)
- [Providers and Configuration](#providers-and-configuration)
- [Security Boundaries](#security-boundaries)
- [Technology and Repository Layout](#technology-and-repository-layout)
- [Documentation](#documentation)
- [Development and Contributing](#development-and-contributing)
- [Acknowledgements](#acknowledgements)
- [Star History](#star-history)

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

### First run and troubleshooting

| Mode | Intended use | Access model |
|---|---|---|
| Local | Personal desktop and first use | Local access without administrator authentication |
| Production | NAS, VPS, LAN, or remote access | Administrator key and explicit `ALLOWED_ORIGINS` |
| Docker | Repeatable long-running deployment | Production mode with mounted `.env` and `storage/` |

- On Windows, run `GenBox.exe` from a terminal when a double-click exits immediately so the error remains visible.
- On macOS, run `xattr -c GenBox-macOS` or allow the client under Privacy & Security.
- On Linux, run `chmod +x GenBox-Linux-x64` before starting the client.

## Capabilities

| Area | Current capability |
|---|---|
| Image creation | Text-to-image, image-to-image, variation, upscaling, and single/multi-model workspaces |
| Video creation | Text-to-video, image-to-video, keyframes, shared prompts, and task monitoring |
| Media management | Search, filters, sorting, history, batch actions, and prompt reuse |
| Extension Center | VPS discovery, fixed deployment plans, isolated chatgpt2api instances, Tailscale preparation, and encrypted optional credential storage |
| Remote transfer | GenBox-initiated Pull and an authenticated idempotent Push receiver foundation |

## chatgpt2api and GenBox

Think of chatgpt2api as a creation station on a remote server and GenBox as your own media library.

- chatgpt2api exposes implemented ChatGPT web capabilities through compatible APIs and manages accounts, proxies, diagnostics, and remote images.
- GenBox provides creation workflows, long-term media organization, history, prompt reuse, deployment, and connection management.
- Today GenBox can guide deployment, establish a private link, and Pull remote images.
- Automatic sender Push, batch and scheduled transfer, and receipt-gated cleanup remain future work.

chatgpt2api is a third-party reverse-engineering research project and can put accounts at risk. Do not test with important or high-value accounts.

## Providers and Configuration

GenBox can connect to OpenAI-compatible image and LLM endpoints, Gemini-compatible services, Qwen/Wanx services, and Agnes image/video APIs. Actual model availability depends on the endpoints configured by the user.

| Variable | Purpose |
|---|---|
| `APP_MODE` | `dev` for local use or `prod` for administrator authentication |
| `GENBOX_PORT` | `8891` for release clients/Docker and `8892` for source development by default |
| `ADMIN_KEY` | Administrator credential in production mode |
| `ALLOWED_ORIGINS` | Allowed HTTPS or private-network browser origins |
| `GENBOX_IMAGE` | GHCR image used by Docker updates |

See [`.env.example`](.env.example) and [`.env.docker.example`](.env.docker.example) for complete templates.

## Security Boundaries

- Never commit `.env`, `storage/`, vaults, logs, user media, or real credentials.
- Existing production chatgpt2api instances stay read-only during development.
- GenBox administrator credentials and per-source Push keys are separate.
- Source media is retained by default; cleanup requires an authenticated matching receipt and explicit opt-in.
- The browser submits structured deployment intent, never arbitrary remote shell commands.

## Technology and Repository Layout

- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic.
- Frontend: native HTML/CSS/JavaScript with fixed-key Chinese and English i18n.
- Remote operations: AsyncSSH, Docker Compose, Tailscale.
- Media and security: Pillow, SHA-256, cryptography/Fernet.
- Delivery: PyInstaller, GitHub Actions, GHCR, release checksums.

Core modules live under `providers/`, `extensions/`, `sync/`, `static/`, `tests/`, `scripts/`, and `docs/`.

## Documentation

- [Product](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decisions](docs/DECISIONS.md)
- [Current status](docs/STATUS.md)
- [Roadmap](docs/ROADMAP.md)
- [Documentation maintenance map](docs/DOCUMENTATION-MAP.md)

## Development and Contributing

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Build dependencies live in `requirements-build.txt`. The release workflow builds all three desktop clients, starts each packaged application, creates the Docker Compose bundle, and publishes SHA-256 checksums.

Read [AGENTS.md](AGENTS.md) and the [development lifecycle](docs/DEVELOPMENT-LIFECYCLE.md) before contributing. Never commit `.env`, `storage/`, logs, credentials, or user media.

## Acknowledgements

| Project / service | Author / team | Relationship to GenBox |
|---|---|---|
| [yukkcat/chatgpt2api](https://github.com/yukkcat/chatgpt2api) | [yukkcat](https://github.com/yukkcat) | Current Extension Center deployment and integration reference |
| [basketikun/chatgpt2api](https://github.com/basketikun/chatgpt2api) | [basketikun](https://github.com/basketikun) | One of the foundations of earlier GPT Image/chatgpt2api support |
| [4k-image-api](https://github.com/jianjianai/4k-image-api) | [jianjianai](https://github.com/jianjianai) | Image transformation and Lanczos upscaling reference |
| [flow2api](https://github.com/TheSmallHanCat/flow2api) | [TheSmallHanCat](https://github.com/TheSmallHanCat) | Gemini image/video integration reference |
| [gemini2api](https://github.com/xwteam/gemini2api) | [xwteam](https://github.com/xwteam) | Gemini-compatible API reference |
| [AIClient2API](https://github.com/justlovemaki/AIClient2API) | [justlovemaki](https://github.com/justlovemaki) | Multi-protocol AI gateway reference |
| [Agnes AI](https://platform.agnes-ai.com) | [Sapiens AI](https://agnes-ai.com) | Agnes image and video APIs |

Special thanks to [@yukkcat](https://github.com/yukkcat) for proposing the GHCR Docker Compose bundle in [PR #4](https://github.com/liwei9745/GenBox/pull/4).

### Upstream project contributors

<a href="https://github.com/basketikun/chatgpt2api/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=basketikun/chatgpt2api" alt="basketikun/chatgpt2api contributors" />
</a>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=liwei9745/GenBox&type=Date)](https://www.star-history.com/#liwei9745/GenBox&Date)

## License

[MIT](LICENSE)
