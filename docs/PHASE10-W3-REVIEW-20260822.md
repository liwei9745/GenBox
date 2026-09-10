# Phase 10 W3 Review

AGENT: W3 Independent high-intensity Store Reviewer
WAVE: W3 finalfix re-review
STATUS: PASS
INPUT_HEAD: c1cedd1
CHANGED_FILES: extensions/discovery.py; extensions/models.py; extensions/orchestrator.py; extensions/store.py; main.py; tests/test_extension_store_contract.py; docs/PHASE10-W3-REVIEW-20260822.md
RESULT: PASS. Both prior W3 findings are closed. Explicit Store projections are rebound to the authoritative projection of the current saved isolated-development target; mismatched, unsaved, and forged fresh projections cannot produce recommendations. Recommendation completeness and reasons now cover all nine non-identity EnvironmentFacts fields, and Python/uv None is explicit `未观测` and not complete. Capability, ownership, metadata, API shape, and old-call boundaries remain fail-closed. No code was modified by this review.
EVIDENCE: Read-only review of the prior W3 report, Phase 10 strategy, extensions/store.py, extensions/models.py, extensions/catalog.py, extensions/capabilities.py, tests/test_extension_store_contract.py, main.py Store route/callers, and static Store UI code. `python -m pytest -q tests/test_extension_store_contract.py --basetemp=.phase10-w3-final-review-tmp` -> 49 passed (2026-08-22). `python -m py_compile extensions/store.py` -> passed. `git diff --check` -> passed; Git emitted only LF/CRLF conversion warnings. No browser, npm, remote, or write-side runtime operation was used.
UNKNOWN: No live VPS, isolated deployment, clean deployment, restart, multi-process contention, or multi-target Store acceptance was performed. Full-suite verification was not requested or run. Existing untracked Phase 10 documents and temporary pytest directories have ownership/cleanup status UNKNOWN. This PASS is limited to W3 finalfix code-contract review and does not claim Phase 10 completion.
RISKS: The Store still selects the first saved `isolated-development` target when multiple such targets exist; multi-target selection and concurrency behavior remain unverified and outside the two closed W3 findings. The worktree remains dirty with cumulative W1/W2/W3 changes and untracked artifacts; this report does not claim ownership of those artifacts.
NEXT: Hand off W3 PASS to the next authorized Phase 10 wave; retain Phase 10 as In Progress until the remaining acceptance evidence and independent verification gates are complete.

## Finding Closure

### Prior HIGH: Explicit projection/facts input was not rebound to the current target

CLOSED. `store_projection()` selects the saved target whose role is
`isolated-development` at `extensions/store.py:911-915`, obtains its fresh
authoritative projection through `get_environment_projection()` at
`extensions/store.py:947-950`, and accepts an explicit projection only when it
matches that authoritative record, including target ID, digest, and all
projection fields, at `extensions/store.py:918-928` and
`extensions/store.py:951-957`. Facts are then checked against the current
target ID and recomputed digest at `extensions/store.py:988-994` through
`_fresh_environment_facts()` at `extensions/store.py:863-887`.

Consequently, an identity mismatch, an unsaved target with no authoritative
projection, an altered projection, or a fresh-looking forged projection leaves
`environment_projection` unavailable or unverified and produces
`recommended=[]`. The regression test at
`tests/test_extension_store_contract.py:854-879` covers a forged target/digest
and altered capability projection. Existing freshness and drift coverage
remains at `tests/test_extension_store_contract.py:819-836` and
`tests/test_extension_store_contract.py:721-755`.

### Prior MEDIUM: Reasons and completeness omitted Python/uv

CLOSED. `_RECOMMENDATION_FACT_FIELDS` now contains all nine non-identity fields,
including `python_version` and `uv_version`, at `extensions/store.py:826-836`.
Both `_environment_fact_reasons()` and `_environment_facts_complete()` consume
that same list at `extensions/store.py:890-908`. A `None` value is rendered as
`<field>=未观测`, added to `unknown_facts`, and causes completeness to be false.

The focused regression test verifies all nine observed values in reasons and
verifies Python/uv `None` is explicit unknown and incomplete at
`tests/test_extension_store_contract.py:772-800`. The complete discovery path
also requires valid normalized Python and uv probe values before issuing a facts
token at `extensions/store.py:507-539`.

## Boundary Checks

- Capability-derived actions remain authoritative: `_store_item()` calls only
  `project_store_actions(item)` at `extensions/store.py:839-860`; the registry
  accepts only the registered `chatgpt2api` Compose capability at
  `extensions/capabilities.py:14-21,40-58`.
- Planned, unavailable, fake, and unsupported catalog entries receive
  `actions=[]`; installed external instances are explicitly forced to
  `actions=[]` at `extensions/store.py:967-977`. Focused coverage is at
  `tests/test_extension_store_contract.py:753-769` and `680-689`.
- Environment facts and recommendation fields do not add actions. The action
  list remains independent of facts, as verified at
  `tests/test_extension_store_contract.py:903-932`.
- Public Store metadata uses `_PUBLIC_STORE_FIELDS` and safe defaults only at
  `extensions/store.py:790-860`; tests cover absent metadata and rejection of
  secret/path fields at `tests/test_extension_store_contract.py:881-900` and
  `651-665`.
- The `/api/extensions/store` route remains `GET` with the existing
  `installed/recommended/all` response shape at `main.py:3682-3689`; route and
  hierarchy coverage remains at `tests/test_extension_store_contract.py:571-589`
  and `632-665`.
- Existing positional and keyword `store_projection()` calls continue to
  return the same three-view shape. Missing or invalid inputs remain
  fail-closed at `extensions/store.py:931-965` and
  `tests/test_extension_store_contract.py:935-950`. The production route still
  calls the unchanged zero-argument `public_store_projection()` path at
  `extensions/store.py:1014-1020`.
- The Store frontend consumes only backend-provided `actions`, renders no
  action for external items, and continues calling `/api/extensions/store` at
  `static/js/extensions.js:117-124`.

## Handoff

AGENT: W3 Independent high-intensity Store Reviewer
WAVE: W3 finalfix re-review
STATUS: PASS
INPUT_HEAD: c1cedd1
CHANGED_FILES: extensions/discovery.py; extensions/models.py; extensions/orchestrator.py; extensions/store.py; main.py; tests/test_extension_store_contract.py; docs/PHASE10-W3-REVIEW-20260822.md
RESULT: Both prior W3 findings are closed; no W3-scope blocking item remains. Capability actions, planned/unavailable fail-closed behavior, external read-only behavior, metadata whitelist, API shape, and old Store calls remain intact.
EVIDENCE: `python -m pytest -q tests/test_extension_store_contract.py --basetemp=.phase10-w3-final-review-tmp` -> 49 passed; `python -m py_compile extensions/store.py` -> passed; `git diff --check` -> passed with LF/CRLF warnings only; no browser/npm/remote activity.
UNKNOWN: Live/isolated/clean-deployment/restart/multi-target evidence and full-suite verification remain unverified.
RISKS: Multi-target selection and cumulative dirty-worktree artifact ownership remain unverified; these do not block the two W3 finalfix findings.
NEXT: Proceed to the next authorized Phase 10 wave while keeping Phase 10 status In Progress.
