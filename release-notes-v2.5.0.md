# GenBox v2.5.0 - Easier to Start, Better for Long-Term Use

> Multi-model creation, the Extension Center, bilingual onboarding, and a verified release pipeline come together in one stable release.

## Which File Should I Download?

| Your system | Recommended download | What to do next |
|---|---|---|
| Windows 10/11 | [GenBox-Windows.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-Windows.zip) | Extract and double-click `GenBox.exe` |
| macOS | [GenBox-macOS.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-macOS.zip) | Extract and run `GenBox-macOS` |
| Linux | [GenBox-Linux-x64.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-Linux-x64.zip) | Extract and add execute permission |
| NAS / VPS / Docker | [GenBox-Docker-Compose-v2.5.0.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-Docker-Compose-v2.5.0.zip) | Extract, configure `.env`, and start Compose |

Desktop archives include the runtime; Python is not required. After startup, open:

```text
http://localhost:8891
```

The standalone `GenBox.exe`, `GenBox-macOS`, and `GenBox-Linux-x64` files are update payloads. New users should normally choose the ZIP archive.

## Get Started in Three Minutes

1. Download and extract the ZIP for your platform.
2. Start GenBox. If the browser does not open, visit `http://localhost:8891`.
3. Add one model service URL, model name, and API key under Model settings.
4. Open Images, select a model, enter a prompt, and generate.

> [!IMPORTANT]
> **Do not use the old in-app updater when moving from Windows v2.4.1 or earlier.** It can select the ZIP and attempt to overwrite the running program. Exit the old client, download `GenBox-Windows.zip`, and replace it manually once. v2.5.0 fixes the update flow used by later versions.

## What Changed?

| Multi-model image workspace | Extension Center |
|---|---|
| ![GenBox multi-model image workspace](screenshots/sanitized/en-02-generate-workspace.png) | ![GenBox Extension Center](screenshots/sanitized/en-03-extension-center.png) |

### Creation experience

- Image and video creation now provide single-model and multi-model comparison workspaces.
- The image workspace adds collapsible creation tools and a task monitor.
- The local media library, history, and prompt reuse remain part of the same workflow.
- Ten coordinated themes, shared monoline icons, and an auto-hiding Dock reduce visual clutter.

### Beginner experience

- Chinese and English now use stable translation keys instead of runtime text scanning.
- Onboarding explains first creation, GenBox capabilities, chatgpt2api, and why the products connect.
- Dashboard, Images, Video, Media Library, History, and Extensions share consistent titles and supporting text.

### Extension Center

- Save VPS targets, verify SSH host keys, and run read-only discovery through guided steps.
- Create fixed deployment plans for isolated chatgpt2api instances.
- Prepare and verify Tailscale private networking.
- Manage service URLs, runtime state, and credentials explicitly saved in the local encrypted vault.

## What Was Fixed?

- Fixed first-run Windows crashes caused by Unicode console output on GBK systems.
- Fixed updater ZIP selection and unsafe self-replacement while the client is running.
- Fixed video Provider initialization timing that could leave model lists empty.
- Fixed white primary surfaces remaining under some dark themes.
- Fixed route, Back/Forward, and refresh behavior so workspace state restores reliably.
- The release workflow now starts Windows, macOS, and Linux clients and verifies their HTTP endpoints.

## Docker Quick Start

```bash
cp .env.example .env
docker compose pull
docker compose up -d
```

Runtime data lives in `storage/`. Before remote access, configure administrator authentication and set `ALLOWED_ORIGINS` to the actual HTTPS or private-network origin.

## Upgrading from an Older Version

1. Back up `.env`, `storage/providers.json`, media, and the rest of `storage/`.
2. Never overwrite an existing `storage/` directory with release files.
3. Follow the one-time manual Windows upgrade above for v2.4.1 and earlier.
4. Legacy Docker users should keep `.env` and `storage/`, adopt the new Compose bundle, and run `docker compose pull && docker compose up -d`.
5. Verify Model settings, Media Library, administrator login, and remote sync after startup.

## Current Limitations

- Sender-side automatic Push after generation, batch/scheduled transfer, and receipt-gated cleanup are not complete end to end.
- Durable deployment-task recovery after a process restart still needs work.
- NetBird and Cloudflare Tunnel do not yet have the same acceptance coverage as Tailscale.
- chatgpt2api is a third-party reverse-engineering research project and can put accounts at risk.

<details>
<summary><strong>Security, checksums, and release verification</strong></summary>

- SHA-256 values for every artifact are published in [SHA256SUMS.txt](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/SHA256SUMS.txt).
- Administrator credentials, per-source Push keys, and Tailscale enrollment information remain separate.
- Source media is retained by default; future cleanup requires an authenticated receipt, matching SHA-256, and explicit opt-in.
- GitHub Actions builds all three desktop clients and performs real HTTP startup smoke tests before publication.
- The Docker Compose bundle pulls `ghcr.io/liwei9745/genbox` without a local source build.

</details>

<details>
<summary><strong>Developer and complete change references</strong></summary>

- [Changelog](CHANGELOG.md)
- [Current status and verification evidence](docs/STATUS.md)
- [Documentation matrix](docs/README.md)
- [All v2.5.0 artifacts](https://github.com/liwei9745/GenBox/releases/tag/v2.5.0)

</details>

Thanks to [@yukkcat](https://github.com/yukkcat) for proposing the GHCR Docker Compose release bundle in [PR #4](https://github.com/liwei9745/GenBox/pull/4).
