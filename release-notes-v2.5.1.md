# GenBox v2.5.1 - Safer Startup and Sign-in

> v2.5.1 is a focused security and reliability update. It closes unsafe
> first-run authentication paths, makes the browser fail closed when setup
> status is unclear, and pins the Docker Compose bundle to this exact version.

## Which File Should I Download?

| Your system | Recommended download | What to do next |
|---|---|---|
| Windows 10/11 | [GenBox-Windows.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-Windows.zip) | Extract and double-click `GenBox.exe` |
| macOS | [GenBox-macOS.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-macOS.zip) | Extract and run `GenBox-macOS` |
| Linux | [GenBox-Linux-x64.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-Linux-x64.zip) | Extract, add execute permission, and run |
| NAS / VPS / Docker | [GenBox-Docker-Compose-v2.5.1.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-Docker-Compose-v2.5.1.zip) | Extract, configure `.env`, and start Compose |

Desktop archives include the runtime; Python is not required. After startup,
open `http://localhost:8891`.

The standalone `GenBox.exe`, `GenBox-macOS`, and `GenBox-Linux-x64` files are
update payloads. New users should normally choose the ZIP archive.

## What Was Fixed?

- Production startup now fails closed when `ADMIN_KEY` is missing. The service
  does not create or reveal an administrator key through a browser endpoint.
- The only unauthenticated setup endpoint now returns a fixed, non-secret
  readiness schema. Previous HTTP routes that could perform first-run setup are
  no longer available without administrator authentication.
- The web UI treats a missing, malformed, failed, or denied setup-status result
  as protected. It shows the sign-in screen instead of assuming that access is
  allowed.
- Login and provider-loading requests now ignore late responses from older
  attempts, so a stale authentication failure cannot erase a newer successful
  sign-in.
- Local desktop first-run mode takes effect in the same process, binds only to
  `127.0.0.1:8892`, and does not create an administrator key.
- The Docker Compose example now pins
  `ghcr.io/liwei9745/genbox:2.5.1` instead of using a moving `latest` tag.

## Upgrade Safely

1. Back up `.env`, `storage/providers.json`, media, and the rest of `storage/`.
2. Never overwrite an existing `storage/` directory with release files.
3. Windows users upgrading from v2.4.1 or earlier must exit GenBox, download
   `GenBox-Windows.zip`, and replace the application manually once. Do not use
   the old in-app updater for that one upgrade.
4. Docker users should keep their existing `.env` and `storage/`, replace only
   the Compose bundle, then run `docker compose pull` followed by
   `docker compose up -d`.
5. After startup, verify Model settings, Media Library, administrator login in
   production mode, and any configured remote-sync settings.

## Docker Quick Start

```bash
cp .env.example .env
# Set a strong, user-supplied ADMIN_KEY before starting in production.
docker compose pull
docker compose up -d
```

The service refuses to start in production when `ADMIN_KEY` is blank. Keep the
key out of screenshots, logs, URLs, and support requests.

## Verification and Known Limits

- The v2.5.1 candidate passed 111 automated tests, JavaScript syntax checks,
  README Lab generation, package checks, Windows startup/upgrade acceptance,
  and isolated local Docker acceptance on 2026-07-16.
- Windows acceptance evidence is from one Windows 10 machine. ANSI rendering
  was not separately accepted for v2.5.1.
- GitHub Actions will rebuild the three desktop packages and publish their
  SHA-256 values when the final `v2.5.1` tag is authorized and pushed.
- Sender-side automatic Push after generation, batch/scheduled transfer, and
  receipt-gated source cleanup are not complete end to end.
- NetBird and Cloudflare Tunnel do not yet have the same acceptance coverage as
  Tailscale.

## References

- [Changelog](CHANGELOG.md)
- [Current verification status](docs/STATUS.md)
- [All v2.5.1 artifacts](https://github.com/liwei9745/GenBox/releases/tag/v2.5.1)
