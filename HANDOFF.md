# GenBox Development Handoff

**Updated:** 2026-07-14
**Branch:** `dev`
**Local development port:** `8892`
**Verified test baseline:** `76 passed`

## Immediate Objective

Finish the local v2.5.0 release-preparation gate. Do not push, tag, merge PR #4,
or create a GitHub Release without owner authorization. Do not begin
chatgpt2api sender Push, batch transfer, scheduling, or source-cleanup work.

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
- `.planning/STATE.md` contains pre-existing owner changes and must stay untouched.

## Remaining Release Gate

1. Run the final secret and personal-data scan against tracked/staged release content.
2. Generate final local archives and `SHA256SUMS.txt`, then inspect archive contents.
3. Recheck the 8892 development preview and ensure no packaging process remains.
4. Create a final local release-preparation commit, excluding `.planning/STATE.md`.
5. Wait for explicit owner authorization before push, tag, PR merge, or Release creation.

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

> Finish the v2.5.0 local release gate from `HANDOFF.md`. Keep development on
> port 8892, preserve production chatgpt2api as read-only, leave
> `.planning/STATE.md` untouched, and do not push, tag, merge PR #4, publish a
> Release, or enter chatgpt2api sender Push development without authorization.
