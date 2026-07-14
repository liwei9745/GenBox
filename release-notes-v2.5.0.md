# GenBox v2.5.0 - Extension Center, Bilingual UX, and Verified Releases

> A major update spanning product experience, remote-service operations, security boundaries, and release infrastructure.

## Highlights

### Extension Center

- Save and manage VPS targets with SSH host-key verification.
- Run read-only discovery and create fixed isolated chatgpt2api deployment plans.
- Deploy and manage isolated instances without browser-supplied shell commands.
- Prepare and verify Tailscale private networking.
- Deliver console/API URLs and manage credentials through show-once or explicit encrypted local storage.

Existing production chatgpt2api instances remain read-only. Development uses separate directories, ports, containers, Compose projects, and credentials.

### GenBox and chatgpt2api foundation

- Existing GenBox-initiated remote Pull remains available.
- The GenBox Push receiver now supports source authentication, SHA-256 validation, idempotency, deduplication, and import receipts.
- Network workflows can prepare a private route and save the final destination URL.

> [!NOTE]
> Sender-side per-generation Push, batch and scheduled transfer, and receipt-gated source cleanup are not complete end to end and are not presented as available in this release.

### Bilingual onboarding and unified UI

- Fixed-key Chinese and English translations replace runtime text scanning.
- Dashboard, Images, Video, Media Library, History, and Extensions share one three-line heading system.
- Four-stage onboarding explains first creation, GenBox capabilities, chatgpt2api, and the value of connecting both products.
- Image and video workspaces provide single-model and multi-model comparison modes.
- Ten coordinated themes, unified monoline icons, collapsible tools, and an auto-hiding Dock.

### Verified release pipeline

Thanks to [@yukkcat](https://github.com/yukkcat) for proposing the Docker Compose bundle in [PR #4](https://github.com/liwei9745/GenBox/pull/4). This release extends that work with:

- GHCR-backed Compose deployment without local source builds.
- A dedicated production Docker environment template.
- Windows, macOS, and Linux client startup smoke tests after packaging.
- A fix for first-run Windows GBK console crashes on Unicode output.
- Locked runtime, test, and PyInstaller build dependencies.
- SHA-256 checksums for release artifacts.

## Artifacts

| File | Purpose |
|---|---|
| `GenBox-Windows.zip` | Ready-to-run Windows client |
| `GenBox-macOS.zip` | macOS client |
| `GenBox-Linux-x64.zip` | Linux/VPS client |
| `GenBox-Docker-Compose-v2.5.0.zip` | Docker Compose deployment bundle |
| `SHA256SUMS.txt` | SHA-256 checksums |

## Upgrade Notes

> [!IMPORTANT]
> The updater in Windows EXE releases v2.4.1 and earlier can select the ZIP asset and then attempts to overwrite its own locked executable. Do not rely on the old in-app updater for this jump. Download `GenBox-Windows.zip`, exit the old client, and replace the executable manually once. v2.5.0 fixes asset selection and performs replacement after the old process exits, enabling the corrected flow for later releases.

1. Back up `.env`, `storage/providers.json`, media, and other runtime data.
2. Never overwrite an existing `storage/` directory with release files.
3. Source Git users must preserve local changes first; the legacy updater follows the current remote branch with `git reset --hard`.
4. Legacy Docker users must adopt the new Compose bundle while preserving `.env` and `storage/`, then run `docker compose pull && docker compose up -d`. The in-app updater cannot migrate an old local `build` configuration to the GHCR image.
5. Verify Model settings, Media Library, administrator login, and remote sync after startup.

Release clients default to `http://localhost:8891`. Source development uses port `8892` through `.env.example`.

## Verification

- 76 automated tests pass, including release-asset selection, Windows post-exit replacement, packaged-client console output, and public screenshot references.
- Chinese and English routes and onboarding pass desktop, narrow, and mobile checks.
- Dependencies install and tests pass in a fresh isolated Python environment.
- A Windows PyInstaller client builds and passes a real HTTP startup smoke test.
- Docker Compose bundle content and production defaults are covered by automated tests.

## Known Limitations

- Sender Push, batch/scheduled transfer, and verified source cleanup remain future phases.
- Durable deployment-task recovery after process restart is incomplete.
- NetBird and Cloudflare Tunnel do not yet have the same acceptance coverage as Tailscale.
- Windows EXE releases v2.4.1 and earlier require one manual upgrade to v2.5.0; legacy Docker Compose installations require manual configuration migration.
- Starlette currently emits a forward-looking `httpx2` migration warning in tests; runtime behavior is unaffected.

See [`docs/STATUS.md`](docs/STATUS.md) for detailed evidence and current boundaries.
