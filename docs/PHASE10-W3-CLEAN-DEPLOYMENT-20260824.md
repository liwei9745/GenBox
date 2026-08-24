# Phase 10 Local Clean Deployment W3 Evidence (2026-08-24)

**Date:** 2026-08-24
**Input commit:** `1383f537ad4c1602e6586b6437c939dc80378f5c`
**Branch:** `codex/phase7-campaign-20260820` (pushed to personal GenBox origin)
**Result:** **LOCAL CLEAN DEPLOYMENT W3 = PASS**

## Scope

- Clean clone from the pushed personal GenBox branch at the exact commit, used
  only as a temporary clone under `E:\AI\GenBox-worktrees\p4planux`.
- Local Docker image built from that clean clone (`--pull=false`), random
  loopback host port, unique Compose project/container/network/temporary
  storage, synthetic in-memory `ADMIN_KEY`, synthetic Store fixture.
- Loopback-only HTTP verification of `/api/extensions/store`; no browser, no
  npm, no SSH, no VPS, no upstream PR, no production resource.

## Verified Results

| Check | Result |
|---|---|
| Clean clone HEAD == input commit | PASS |
| Compose startup with absolute `-f` path | PASS |
| Container health | PASS (`healthy`) |
| Unauthenticated `/api/extensions/store` | PASS (`401`) |
| Three Store views (`installed`,`recommended`,`all`) | PASS |
| Partial facts fail closed: Recommended `confidence=unknown`, `actions=[]`, `unknown_facts` covers os/cpu/memory/disk/docker/compose/python/uv | PASS |
| Planned / repository_unverified rows have `actions=[]` | PASS |
| External installed row read-only (`ownership=external`, `actions=[]`) | PASS |
| Public metadata no forbidden public keys; no admin-key value leaked | PASS |
| Store projection identical across `restart genbox` | PASS |

## Notes And Harness Fixes

- The earlier Compose failures were tool/harness path and environment
  interpolation issues, not product defects:
  - MSYS drive-slash paths are read by `docker.exe` as drive-relative and
    fail; absolute drive-letter `-f` paths are required.
  - `--project-directory` does not redirect relative `-f` resolution.
  - `--env-file` does not interpolate `${GENBOX_PORT}`; shell environment
    variables are used for interpolation, and the Shell `$env:` injection
    worked.
  - `ADMIN_KEY` is injected via the Compose override service `environment`
    (literal value), because production startup requires it.
  - PS 5.1 has no `-SkipHttpErrorCheck`; a try/catch status helper is used.
- Final leak assertion inspects public keys recursively rather than substring
  matching, so the legitimate catalog permission label `service_credentials`
  is not mistaken for a credential leak.

## Teardown

Unique container, network, image tag, temporary clone, storage, and generated
local files were removed after the run. No residual clean-run artifact remains.

## Boundary

This is **LOCAL CLEAN DEPLOYMENT / SYNTHETIC STORE API EVIDENCE** on the
personal branch. It does not prove a VPS target, SSH authority, remote
Docker/Compose facts, private-network reachability, real sender integration,
real media transfer, published-image provenance, browser behavior, or adapter
lifecycle completion. Phase 10 remains In Progress until those separate gates
are accepted.

## Handoff

AGENT: orchestrator-run W3 clean deployment
WAVE: W3 local clean deployment Store acceptance
STATUS: PASS (local clean/SYNTHETIC evidence)
INPUT_HEAD: 1383f537ad4c1602e6586b6437c939dc80378f5c
CHANGED_FILES: docs only (evidence + STATUS/heartbeat)
RESULT: PASS across compose startup, Store three views, unknown-facts
fail-closed, planned/external read-only, metadata non-leak, and restart
persistence on a clean clone.
EVIDENCE: `CLEAN_DEPLOYMENT_W3=PASS` observed on port 12265 (run
`genbox-p10-w3-20260824123158`), health healthy, restart healthy, store PASS.
UNKNOWN: VPS/SSH/remote/clean-published-image/browser/lifecycle evidence.
RISKS: None new; the run was isolated, synthetic, loopback-only, and fully
torn down.
NEXT: Update STATUS/ROADMAP/heartbeat to record the PASS and keep Phase 10
In Progress pending the remaining gates.