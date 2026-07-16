# GenBox Development Handoff

**Updated:** 2026-07-16

**Branch:** `codex/v251-security-hotfix`

**Candidate commit:** `b411aa0`

**Local development port:** `8892`

**Current phase:** v2.5.1 local candidate acceptance - **BLOCKED**

## Immediate Objective

Resume acceptance of the existing v2.5.1 candidate. Do not begin another
implementation pass unless acceptance exposes a new reproducible code defect.
The remaining work is to close Windows W2 observability, build and verify the
isolated Docker candidate, and complete the official v2.4.1 upgrade matrix.

Do not release, push an image, change the GitHub Ruleset, operate on a VPS, or
enter chatgpt2api sender Push work while any acceptance lane remains blocked.

## Candidate Identity And Code Gates

- Exact source commit: `b411aa0`.
- Source archive SHA-256:
  `9493a812eccd51f900dc7219e429ab35ecb1b42458484c5bc939f557af042bbc`.
- Windows candidate: 30,328,866 bytes; SHA-256
  `99e105a1a753879481e8133dd3146ca00dd15b70d93c5dad1da700ce04953a67`.
- The packaged runtime reports version `2.5.1`.
- `VERIFIED 2026-07-16`: the full suite passed with `111 passed`; JavaScript
  syntax checks, README Lab generation, and `git diff --check` also passed.

## Windows Acceptance

- `VERIFIED W0`: explicit development-mode smoke passed.
- `VERIFIED W1`: a fresh explicit development first run stayed in the same
  process, bound only to loopback on port `8892`, returned the unified setup
  schema and provider state, required no administrator key, and needed no
  restart workaround.
- `BLOCKED W2`: the natural interactive first-run path using choice 1 was not
  safely observable through its console. W1 is useful behavior evidence but is
  not a substitute for this operator-visible path.
- `VERIFIED W3`: non-interactive production startup without an administrator
  key failed closed before opening a listener and emitted only sanitized
  diagnostics.
- `VERIFIED W4`: production HTTP checks returned the expected `401`, `401`, and
  authenticated `200` results; the setup schema was correct, the key was absent
  from logs, and Chrome initial login and onboarding passed. After reload, the
  login UI returned and required the administrator key to be entered again.

The exact claim is: Windows behavior is verified for W0, W1, W3, and W4. The
full Windows acceptance and release gate remain blocked by W2. No new code
defect currently requires repair.

## Other Blocking Lanes

### Docker

- Two local candidate image builds, including the default path and a host
  networking diagnostic, timed out during the operating-system package step.
- The candidate image tag is absent. No v2.5.1 candidate container or Compose
  runtime has been verified.
- Prior public v2.5.0 Docker evidence is historical and cannot substitute for
  v2.5.1 acceptance.
- No candidate-owned container, network, or volume remains. Shared BuildKit
  cache from failed builds may remain and was not globally pruned.

### v2.4.1 Upgrade

- Official v2.4.1 metadata identifies `GenBox.exe` as 25,229,487 bytes with
  SHA-256
  `e6e45e81221e628c9ab14be7eeb36608cf46ef62dfc98faed0ac71fe964aa0d4`.
- The download stopped at approximately 3.9 MB. The partial file and its empty
  download directory were deleted.
- No new v2.4.1 upgrade or GBK-console acceptance evidence was produced.

## Safety State

- `VERIFIED 2026-07-16`: the production-like chatgpt2api instance remained
  unchanged and read-only. No VPS operation occurred.
- No Release, image push, or Ruleset operation occurred.
- Ports `8891` and `8892` are free; no GenBox or acceptance helper remains.
- The acceptance-created Chrome tab was closed. Secret-bearing owned
  directories and the candidate `.env` were deleted; the disposable synthetic
  key no longer identifies any running candidate instance.
- The repository `.env` remained unchanged. The only unrelated owner change is
  `.planning/STATE.md`; leave it untouched.

## Resume Plan

1. Complete W2 with an observable console or a manual operator watching the
   natural interactive choice-1 flow. Record whether the same process binds
   loopback on `8892` without restart.
2. Restore a working Docker apt path, user-approved mirror, or verified cache.
   Build a local image from exact commit `b411aa0` with a unique v2.5.1
   candidate tag, then run isolated Compose acceptance. Do not push the image.
3. Download the official v2.4.1 executable completely and require the published
   size and SHA-256 to match before execution. Run upgrade cases U1 and U2 and
   label the GBK-console result explicitly.
4. Repeat repository, port, process, container, secret, and cleanup inventory;
   obtain independent review before any release decision.

Keep source development on port `8892`. Production chatgpt2api remains
read-only, and sender Push, batch transfer, scheduling, and source cleanup are
still prohibited.
