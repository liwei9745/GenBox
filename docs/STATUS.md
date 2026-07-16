# Current Project Status

**Last updated:** 2026-07-16
**Current branch:** `codex/v251-security-hotfix`
**Candidate commit:** `b411aa0`
**Release-preparation status:** rebased onto GPL-3.0-only master; final PR,
tag, Release, and image verification pending.
**Current phase:** v2.5.1 local candidate acceptance — **PASSED**

## Candidate Identity

- `VERIFIED 2026-07-16`: source commit `b411aa0`; packaged runtime version
  `2.5.1`.
- `VERIFIED 2026-07-16`: Windows candidate size `30,328,866` bytes; SHA-256
  `99E105A1A753879481E8133DD3146CA00DD15B70D93C5DAD1DA700CE04953A67`.
- `VERIFIED 2026-07-16`: official v2.4.1 size `25,229,487` bytes; SHA-256
  `E6E45E81221E628C9AB14BE7EEB36608CF46EF62DFC98FAED0AC71FE964AA0D4`.

## Verified Candidate State

- `VERIFIED 2026-07-16`: automated gates passed with `111 passed`, JavaScript
  syntax checks, README Lab generation, and `git diff --check`.
- Windows W0-W4 passed their candidate criteria using combined evidence. For
  W2, `USER-CONFIRMED 2026-07-16` the operator saw the exact prompt and entered
  `1` once. `VERIFIED 2026-07-16` there was no `8892` listener before input;
  PyInstaller used its expected two-level process structure; listener creation
  preceded the `.env` write; and the same listener PID and creation time handled
  two HTTP checks. The process used `dev`, bound only to
  `127.0.0.1:8892`, created no `ADMIN_KEY`, returned the canonical six-field
  setup schema, and allowed unauthenticated provider access.
- `VERIFIED 2026-07-16`: local image `genbox-v251-candidate:b411aa0` was built
  from exact commit `b411aa0` in about 8m27s. Its truncated image ID is
  `sha256:335d4437…e69746a`; size `656,575,011` bytes. The separate ffmpeg
  diagnostic took about 9m45s. Isolated checks passed for
  non-root execution, health/schema, `401`/`401`/`200` authentication,
  persistence, logs without the key, and candidate resource cleanup. The image
  remains local and was not pushed.
- `VERIFIED 2026-07-16`: U1 official v2.4.1 upgrade fixture passed. Windows
  safely rejected in-use EXE
  replacement; replacement after shutdown preserved configuration, providers,
  and marker hashes/mtimes, and v2.5.1 started normally.

## v2.4.1 Baseline Finding

U2 uses combined evidence. `USER-CONFIRMED 2026-07-16` a real Windows 10
console showed readable GBK Chinese, visible raw ANSI escape sequences, the
interactive prompt and choice `1`, and a browser opening. `VERIFIED 2026-07-16`
v2.4.1 wrote `APP_MODE=dev` but did not reload it in the existing process; that
process continued as production on `0.0.0.0:8891` and generated an
administrator secret. The secret value is intentionally omitted from repository
documentation. The exact process was stopped, all key-bearing temporary
artifacts were deleted, and the ports were released.

This is a confirmed old-version baseline defect. It is not a candidate
regression: the independent v2.5.1 W2 acceptance proves immediate same-process
dev mode, loopback binding, and no administrator key. ANSI behavior has not been
separately accepted on v2.5.1, and the Windows evidence is limited to one
Windows 10 machine.

## Release Preparation

- `VERIFIED 2026-07-16`: prepared Chinese and English v2.5.1 release notes,
  changelog entry, README links, and README Lab content. The notes accurately
  retain the sender Push, network-adapter, and Windows-coverage limitations.
- `VERIFIED 2026-07-16`: release-preparation working tree passed `111` tests,
  four JavaScript syntax checks, README Lab generation, and `git diff --check`.
  Pytest's default system temporary directory was inaccessible in this session;
  the same suite passed with a disposable repository-local `--basetemp`, which
  was removed after the run.
- `VERIFIED 2026-07-16`: a high-confidence scan of tracked content found no
  private-key block, OpenAI-style key, GitHub token, or AWS access-key match.
  This is a screening result, not a substitute for final human review of the
  release diff and generated artifacts.
- `VERIFIED 2026-07-16`: GPL-3.0-only PR #7 merged to `master` as `ad802f6`.
  The v2.5.1 branch was then rebased onto that GPL baseline so its source and
  release packages carry the selected license.

## Safety And Scope

- `VERIFIED 2026-07-16`: production-like chatgpt2api remained read-only and
  unchanged.
- `VERIFIED 2026-07-16`: no v2.5.1 tag or GitHub Release, VPS operation, or
  sender Push operation occurred.
- `VERIFIED 2026-07-16`: ports `8891` and `8892` are free; acceptance processes
  and secret-bearing temporary directories were removed.
- `VERIFIED 2026-07-16`: the repository `.env` remained unchanged. Do not
  modify, stage, or commit the owner's `.planning/STATE.md` change.

## Closeout

Candidate acceptance is complete and release publishing is authorized. Next:

1. Run final source and package checks on the GPL-rebased v2.5.1 branch.
2. Force-push the rebased branch, wait for PR #6 CI, then merge it to `master`.
3. Confirm the `master` image workflow, create and push the `v2.5.1` tag, wait
   for desktop and tag-image workflows, then verify the GitHub Release assets.

Do not operate on a VPS or begin chatgpt2api sender Push work as part of this
release closeout.
