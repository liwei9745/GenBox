# GenBox Development Handoff

**Updated:** 2026-07-14
**Branch:** `dev`
**Local development port:** `8892`
**Verified test baseline:** `76 passed`

## Immediate Objective

Run post-release clean-install and upgrade-path acceptance against the public
v2.5.0 artifacts. Do not begin chatgpt2api sender Push, batch transfer,
scheduling, or source-cleanup work during this gate.

## Current Verified State

- Snapshot commit `11dfd51` captures the Extension Center and onboarding milestone.
- PR #4's GHCR-backed Docker Compose bundle intent is integrated and credited;
  the GitHub PR itself remains unmerged.
- Runtime, development, and PyInstaller dependency sets are pinned separately.
- GitHub Actions tests source, builds three packaged clients, smoke-tests each,
  packages desktop and Docker artifacts, and generates SHA-256 checksums.
- Windows `dist/GenBox.exe` was rebuilt after updater changes and passed a real
  HTTP smoke test on 2026-07-14.
- The v2.5.0 updater now selects standalone assets, rejects archives, and replaces
  packaged clients only after the running process exits.
- v2.4.1 and earlier Windows EXE users need one manual upgrade to v2.5.0 because
  the old updater selects the ZIP first and cannot overwrite its locked process.
- Legacy Docker users must migrate to the new Compose bundle while preserving
  `.env` and `storage/`; the old in-app update cannot rewrite host Compose config.
- `python -m pytest -q` passes all 76 tests. JavaScript syntax checks, Python
  compilation, and `git diff --check` pass.
- README screenshots were replaced with four current v2.5.0 captures from an
  isolated client. Dashboard device values are labeled synthetic demo data.
- GitHub Release `v2.5.0` is public at tag commit `a675f8c`. Desktop Actions run
  `29308338415` and Docker tag run `29308338400` completed successfully.
- All seven downloadable payloads match the published `SHA256SUMS.txt`; the
  Docker archive contains only its four documented public deployment files.
- `.planning/STATE.md` contains pre-existing owner changes and must stay untouched.

## Post-Release Gate

1. Install the Windows ZIP in a clean directory and verify first-run setup.
2. Deploy the public Docker Compose bundle with new credentials and empty storage.
3. Verify the documented one-time manual upgrade from v2.4.1 or earlier.
4. Confirm README screenshots and quick-start links render correctly on GitHub.
5. Record results before selecting the next pre-Push phase.

## Safety And Scope

- Keep local development on port `8892`; packaged desktop and Docker defaults are `8891`.
- Treat production chatgpt2api as read-only and do not restart or reconfigure it.
- Do not expose credentials, user prompts, account data, personal media, or raw logs.
- Do not describe sender Push, batch/scheduled transfer, or cleanup as available.

## Verification Commands

```powershell
node --check static/js/i18n.js
node --check static/js/app-all.js
node --check static/js/extensions.js
node --check static/js/sync.js
python -m pytest -q
python scripts/smoke_client.py --executable dist/GenBox.exe
```

## Resume Prompt

> Run the v2.5.0 post-release clean-install and upgrade acceptance from
> `HANDOFF.md`. Keep development on port 8892, preserve production chatgpt2api
> as read-only, leave `.planning/STATE.md` untouched, and do not enter
> chatgpt2api sender Push development.
