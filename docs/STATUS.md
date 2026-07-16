# Current Project Status

**Last updated:** 2026-07-16

**Current branch:** `codex/v251-security-hotfix`

**Candidate commit:** `b411aa0`

**Current phase:** v2.5.1 local candidate acceptance - **BLOCKED**

**Current objective:** Finish the remaining candidate acceptance lanes. Do not
resume implementation unless acceptance reveals a new reproducible code defect,
and do not enter chatgpt2api sender Push or other later-phase work.

## Status Legend

- `VERIFIED`: confirmed by a dated command or direct acceptance observation.
- `USER-CONFIRMED`: supplied by the project owner but not independently checked.
- `BLOCKED`: required evidence is incomplete or the environment cannot safely
  produce it.

## Candidate And Automated Gates

- `VERIFIED 2026-07-16` Exact source commit: `b411aa0`.
- `VERIFIED` Source archive SHA-256:
  `9493a812eccd51f900dc7219e429ab35ecb1b42458484c5bc939f557af042bbc`.
- `VERIFIED` Windows candidate size: 30,328,866 bytes; SHA-256:
  `99e105a1a753879481e8133dd3146ca00dd15b70d93c5dad1da700ce04953a67`.
- `VERIFIED` The packaged runtime reports version `2.5.1`.
- `VERIFIED 2026-07-16` The full Python suite passed with `111 passed`.
  JavaScript syntax checks, README Lab generation, and `git diff --check` also
  passed.

## Windows Acceptance Matrix

- `VERIFIED W0` Explicit development-mode smoke passed.
- `VERIFIED W1` A fresh explicit development first run stayed in the same
  process, bound to loopback on port `8892`, returned the unified setup schema
  and provider state, required no administrator key, and did not need a restart.
- `BLOCKED W2` The natural interactive choice-1 path could not be safely
  observed through its console. W1 does not replace this operator-visible
  acceptance case.
- `VERIFIED W3` Non-interactive production startup without an administrator key
  failed closed before opening a listener and produced sanitized diagnostics.
- `VERIFIED W4` Production HTTP checks returned the expected `401`, `401`, and
  authenticated `200` results. The setup schema was correct, no administrator
  key appeared in logs, and Chrome initial login and onboarding passed. After
  reload, the login UI returned and required the administrator key to be
  entered again.

**Windows verdict:** behavior is verified for W0, W1, W3, and W4. Full Windows
acceptance and the release gate remain blocked by W2. No new code defect
currently requires repair.

## Docker Acceptance

`BLOCKED` Two candidate image builds, using the default path and a host-network
diagnostic, timed out during the operating-system package step. The candidate
tag is absent, so no v2.5.1 candidate runtime or Compose result exists. The old
public v2.5.0 image evidence is historical and is not a substitute.

No candidate-owned container, network, or volume remains. Failed builds may
have left shared BuildKit cache; it was not globally pruned because that could
affect unrelated projects.

## v2.4.1 Upgrade Acceptance

`BLOCKED` Official release metadata identifies the v2.4.1 Windows executable as
25,229,487 bytes with SHA-256
`e6e45e81221e628c9ab14be7eeb36608cf46ef62dfc98faed0ac71fe964aa0d4`.
The attempted download stopped at approximately 3.9 MB. The partial file and
its empty download directory were deleted. No new U1/U2 upgrade or GBK-console
evidence was produced.

## Safety And Cleanup

- `VERIFIED 2026-07-16` Production-like chatgpt2api remained unchanged and
  read-only. No VPS operation occurred.
- No Release, image push, or GitHub Ruleset operation occurred.
- Ports `8891` and `8892` are free, with no GenBox or acceptance helper left
  running.
- The acceptance-created Chrome tab was closed. Secret-bearing owned
  directories and the candidate `.env` were deleted; the disposable synthetic
  key no longer identifies any running candidate instance.
- The repository `.env` remained unchanged. The only unrelated working-tree
  change is the owner's `.planning/STATE.md`; do not modify it.

## Resume Conditions

1. Observe W2 through a safe console or a manual operator during the natural
   interactive choice-1 flow.
2. Restore a working Docker apt path, user-approved mirror, or verified cache,
   then build and test a uniquely tagged local v2.5.1 image from exact commit
   `b411aa0` without pushing it.
3. Complete the official v2.4.1 download and require the published size and
   SHA-256 to match before running U1/U2, including explicit GBK result
   labeling.
4. Repeat inventory, cleanup, and independent review before any release
   decision.

Keep local development on port `8892`. Treat production chatgpt2api as
read-only. Sender Push, batch transfer, scheduling, source cleanup, VPS work,
release publication, and image pushing remain out of scope.
