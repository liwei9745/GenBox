# GenBox Development Handoff

**Updated:** 2026-07-16
**Branch:** `codex/v251-release-record`
**Release commit:** `ae2b174`
**Release status:** v2.5.1 published under GPL-3.0-only — **VERIFIED**
**Development port:** `8892`
**Current phase:** v2.5.1 local candidate acceptance — **PASSED**

## Outcome

The exact v2.5.1 candidate completed its automated, Windows, Docker, and
official v2.4.1 upgrade acceptance, then published as GPL-3.0-only from merged
commit `ae2b174`. No production or VPS operation was performed.

## Candidate Identity

- `VERIFIED 2026-07-16`: source commit `b411aa0`; packaged runtime version
  `2.5.1`.
- `VERIFIED 2026-07-16`: Windows candidate size `30,328,866` bytes; SHA-256
  `99E105A1A753879481E8133DD3146CA00DD15B70D93C5DAD1DA700CE04953A67`.
- `VERIFIED 2026-07-16`: official v2.4.1 baseline size `25,229,487` bytes;
  SHA-256
  `E6E45E81221E628C9AB14BE7EEB36608CF46EF62DFC98FAED0AC71FE964AA0D4`.

## Evidence

- `VERIFIED 2026-07-16`: automated gates passed with `111 passed`; all four
  JavaScript syntax checks, README Lab generation, and `git diff --check`
  passed.
- Windows W0-W4 have combined machine and operator evidence. For W2,
  `USER-CONFIRMED 2026-07-16` the operator saw the exact first-run prompt and
  entered `1` exactly once. `VERIFIED 2026-07-16` port `8892` had no listener
  before input; the PyInstaller launch used its expected two-level process
  structure; the listener process creation time preceded the `.env` write; and
  the same listener PID and creation time handled two HTTP checks. That process
  ran in `dev`, listened only on `127.0.0.1:8892`, created no `ADMIN_KEY`,
  returned the canonical six-field setup status, and allowed unauthenticated
  provider access.
- `VERIFIED 2026-07-16`: local Docker image
  `genbox-v251-candidate:b411aa0` was built from exact commit `b411aa0` in about
  8m27s and passed isolated acceptance. Its image ID was recorded in truncated
  form as `sha256:335d4437…e69746a`; size `656,575,011` bytes. The separate
  ffmpeg diagnostic took about 9m45s.
  Evidence covered non-root execution, health/setup schema, expected
  `401`/`401`/`200` authentication behavior, persistence, key-free logs, and
  cleanup of candidate runtime resources. The local image is retained and was
  not pushed.
- `VERIFIED 2026-07-16` U1: the official v2.4.1 fixture passed upgrade
  acceptance. Replacing the EXE
  while it was running failed safely under Windows locking; replacement after
  shutdown succeeded. Configuration, providers, and marker hashes and mtimes
  remained unchanged, and v2.5.1 started normally.
- U2 baseline combines observation and machine evidence.
  `USER-CONFIRMED 2026-07-16` the official v2.4.1 natural Windows 10 console
  displayed readable GBK Chinese, visibly exposed raw ANSI escape sequences,
  showed the interactive prompt, accepted choice `1`, and opened its browser.
  `VERIFIED 2026-07-16` the old process did not reload its newly written
  `APP_MODE=dev`; it continued in production mode on `0.0.0.0:8891` and
  generated an administrator secret. This is a confirmed v2.4.1 baseline
  defect, not a v2.5.1 regression. The secret value is intentionally omitted
  from repository documentation; the exact process was stopped, all
  key-bearing temporary artifacts were deleted, and both ports were released.
  The independent v2.5.1 W2 result proves the same-process mode-reload and
  loopback fix.

ANSI rendering was not separately re-tested on v2.5.1. Windows evidence is from
one Windows 10 machine, which remains a platform-coverage limitation.

## Release Preparation Evidence

- `VERIFIED 2026-07-16`: Chinese and English v2.5.1 release notes, changelog,
  README links, and README Lab content were prepared. They describe only the
  verified startup-authentication, browser fail-closed, and version-pinned
  Docker Compose changes, and retain known limitations.
- `VERIFIED 2026-07-16`: the release-preparation working tree passed `111`
  tests, four JavaScript syntax checks, README Lab generation, and
  `git diff --check`. The normal system pytest temporary directory was denied
  by the environment; the full suite passed with a disposable repository-local
  temporary directory, removed after verification.
- `VERIFIED 2026-07-16`: a high-confidence tracked-content scan found no
  private-key block, OpenAI-style key, GitHub token, or AWS access-key match.
- `VERIFIED 2026-07-16`: GPL-3.0-only PR #7 merged to `master` as `ad802f6`.
  This v2.5.1 branch is rebased onto the GPL baseline.
- `VERIFIED 2026-07-16`: PR #6 merged as `ae2b174`, tag `v2.5.1` was pushed,
  and GitHub Release `GenBox v2.5.1` published eight assets.
- `VERIFIED 2026-07-16`: Docker workflow `29510804581` and desktop/Release
  workflow `29510804145` both succeeded. The downloaded Docker bundle checksum
  matched `SHA256SUMS.txt` and includes GPL, copyright, and third-party notices.

## Safety State

- `VERIFIED 2026-07-16`: production-like chatgpt2api remained read-only and
  unchanged.
- `VERIFIED 2026-07-16`: no VPS operation or sender Push operation occurred.
- `VERIFIED 2026-07-16`: ports `8891` and `8892` are free. Acceptance processes
  and secret-bearing temporary directories were removed.
- `VERIFIED 2026-07-16`: the repository `.env` was unchanged.
  `.planning/STATE.md` is an unrelated owner change and must not be modified,
  staged, or committed.

## Next Action

1. Resume roadmap Phase 3: Private Network Automation.
2. Start with `docs/extensions-deployment-contract.md` and `docs/INTEGRATION.md`.
3. Keep production chatgpt2api read-only and do not enter sender Push work until
   the roadmap phase order and acceptance evidence allow it.
