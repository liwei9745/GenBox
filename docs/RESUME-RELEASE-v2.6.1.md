# Release Heartbeat / Resume Checkpoint — GenBox v2.6.1

> SCHEDULER NOTE: This file is the single resume point for unattended release
> work. If this session is interrupted, a new scheduler/agent must read this
> file first, run the "Verify before continuing" block, then follow the
> "Remaining steps" list. Do not skip receipt verification.

**Guardian:** scheduling agent (unattended-mode). Do not let a network blip or
session restart lose the release position.

## Goal

Ship GenBox **v2.6.1** as a scoped receiver-side patch: managed Push-source
"allow authorized source deletion" grant (default off) + bilingual UI +
browser-contract test. Receiver only; sender/upstream delivery is NOT in scope
(this is the remaining Phase 9 delivery gate; yukkcat PR #26 stays open).

## Completed (verified)

- v2.6.1 prep commit: `2bbd459` (genbox_version=2.6.1, compose/.env pin,
  CHANGELOG [2.6.1], RELEASE_NOTES redirect, notes zh/en created as UTF-8).
- Workspace tests before tag: full `620 passed`; packaging `11 passed`;
  node --check OK (app-all/extensions/i18n); py_compile OK; `python build.py`
  succeeded -> `dist\GenBox.exe` 38,089,061 B, SHA-256
  `B065FC7688540DC7AF426537E185A0454ADFA51F36DDE9C45500B9497ED863FD`.
- Annotated tag `v2.6.1` (object `51273543…` -> commit `2bbd459`) pushed to
  liwei9745/GenBox. Remote tag confirmed.
- CI (2026-08-21, both pushed by the tag):
  - Build Docker Image run `32498587828` -> **success**
  - Build Desktop Clients run `32498587781` -> **success**
- Local git clean before tag; no production VPS touched.

## Verify before continuing (run these each resume)

**STATUS: OK** — verified 2026-08-21 by independent sentinel heartbeat agent
(evidence below, recorded verbatim from `gh` output).

- CI Docker Image run `32498587828` -> status `completed`, conclusion `success`
  (event `push`, headSha `2bbd459a77aa44b30521696ed0672cd221db521d`).
- CI Desktop Clients run `32498587781` -> status `completed`, conclusion
  `success` (event `push`, headSha `2bbd459a77aa44b30521696ed0672cd221db521d`).
  Run jobs: Test release source, Build Linux, Build macOS, Build Windows, and
  `Create Release` — all `success`; the `Create Release` job's final step
  `Create GitHub Release` succeeded (`conclusion: success`).
- GitHub Release `v2.6.1` IS published: `isDraft=false`, `isPrerelease=false`,
  `publishedAt=2026-08-21T15:40:22Z`, name `GenBox v2.6.1`. Assets present (all
  `state=uploaded`):
  - `GenBox-Windows.zip` (29,931,482 B)
  - `GenBox.exe` (30,270,663 B)
  - `GenBox-macOS.zip` (27,297,945 B) / `GenBox-macOS` (27,621,888 B)
  - `GenBox-Linux-x64.zip` (50,122,962 B) / `GenBox-Linux-x64` (50,592,880 B)
  - `GenBox-Docker-Compose-v2.6.1.zip` (15,493 B)
  - `SHA256SUMS.txt` (613 B)
- GHCR resolution (via `gh api`, no docker): package `genbox` is owned by the
  USER account (org endpoint returns 404), so used
  `/user/packages/container/genbox/versions`. Version id `1157898979` carries
  tags `["2bbd459","2.6.1","2.6","latest"]` —
  `ghcr.io/liwei9745/genbox:2.6.1` and `:2.6` both resolve to digest
  `sha256:7ade2a482ce646bd21c9f6229ad508ef6567263b844128506418a42b23213b66`
  (matches tag commit `2bbd459`).
- Command notes: org endpoint `GET /orgs/liwei9745/packages/container/genbox/versions`
  returned HTTP 404 "Not Found"; embedded double quotes in `gh api --jq`
  filters are stripped by the shell wrapper (jq must avoid `"` literals, e.g.
  via `tojson`).

## Next step

Wait for PR #26 maintainer review. If it is rejected, create a revision branch
from the latest yukkcat `main`, apply only the requested changes, rerun
validation, and open a replacement PR; do not overwrite the original
repository.

## Hard limits

- Do not touch production chatgpt2api VPS instances at any point.
- Do not force-push, rebase, or rewrite the pushed tag or history.
- Do not flip any receiver default except through the explicit grant PATCH.
- Keep unlocked secrets out of logs/status files.
