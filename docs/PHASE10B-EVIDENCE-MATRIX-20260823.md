# Phase 10B Local Evidence Matrix

**Date:** 2026-08-23
**Input HEAD:** `56d8fd0`
**Scope:** Local Store closure only. No browser, npm install, remote, VPS,
Docker, Compose, or push operation was performed by this local lane. The
frontend/catalog additions are currently uncommitted.

## Acceptance Matrix

| Acceptance | Local result | Evidence | Remaining boundary |
|---|---|---|---|
| Visible actions derive only from backend capability | PASS | `project_store_actions()` contract, Store frontend action allowlist, `686` full tests | No live deployment evidence |
| Unknown facts and unavailable apps explicit/fail closed | PASS locally | Unknown values remain `None`; null Docker/Compose stays unknown; partial Recommended uses `confidence=unknown`, `unknown_facts`, reasons, `actions=[]`; frontend unknown rendering tests; catalog planned/unavailable tests | No browser/UAT or clean deployment |
| External instances advisory/read-only before adoption | PASS at local route contracts | Deploy plan/start, delivery, resume, cancel, vault, image-update and push-source guards; external rows no actions | No verified adoption flow; no live target |
| Store metadata identifies source/license/permissions/exposure/risk | PASS for local catalog contract | 12 catalog entries audited; 59 catalog/store tests; public whitelist and safe defaults | Upstream provenance/license semantics remain unverified externally |

## Lane Results

- Frontend lane: `static/js/extensions.js` now blocks deploy rendering for
  unknown/partial/non-deployable rows and presents null capabilities as
  unknown. Static frontend tests: `9 passed`; Node checks passed.
- Catalog lane: all 12 catalog entries passed field completeness and honest
  unavailable-state checks. Catalog/store focused tests: `59 passed`; no
  catalog source change was needed.
- Merged focused suite with Python 3.14: `275 passed`.
- Final full suite after frontend regression fix with Python 3.14: `686 passed`;
  Node checks, explicit `py_compile`, and `git diff --check` passed.
- Default `python` on this Windows environment has no pytest module; no
  dependency was installed. The existing Python 3.14 launcher was used.

## Status Decision

This matrix supports a **local Phase 10B PASS**. It does not close Phase 10:
clean deployment, live VPS, restart/multi-target behavior, and adapter
lifecycle evidence remain separate gates. Phase 9 PR #26 also remains an
external maintainer-review state.

## Next

Keep the changes uncommitted until a final diff review and explicit local
commit authorization. Do not push or start Phase 11/12 from this matrix alone.
