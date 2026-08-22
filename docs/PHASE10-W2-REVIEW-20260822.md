# Phase 10 W2 Review

AGENT: W2 Independent high-intensity security Reviewer
WAVE: W2 final review
STATUS: PASS
INPUT_HEAD: c1cedd1
CHANGED_FILES: extensions/discovery.py; extensions/models.py; extensions/orchestrator.py; extensions/store.py; main.py; tests/test_extension_store_contract.py; reviewer output: docs/PHASE10-W2-REVIEW-20260822.md
RESULT: PASS. The prior W2 blocking findings are closed: probe evidence requires successful exit status plus non-empty, typed, valid output; missing, failed, empty, invalid, and explicit-unknown probe values cannot mint successful facts; verifier and save paths both enforce the current saved target identity; and projection plus facts use one atomic config lock/load/save observation. No W2-scope blocking finding remains. No code was modified by this review.
EVIDENCE: Read-only review of the prior W2 findings, current diff against input HEAD c1cedd1, extensions/models.py, extensions/store.py, main.py, extensions/discovery.py, extensions/orchestrator.py, tests/test_extension_store_contract.py, and scope paths static/catalog/Phase 12. `python -m pytest -q tests/test_extension_store_contract.py tests/test_extensions.py --basetemp=.phase10-w2-final-review-tmp` -> 247 passed (2026-08-22). `python -m py_compile extensions/models.py extensions/store.py main.py extensions/discovery.py extensions/orchestrator.py` -> passed. `git diff --check` -> passed with LF/CRLF warnings only. No browser, npm, remote, or write-side runtime operation was used.
UNKNOWN: No live VPS, isolated deployment, clean deployment, restart, or multi-process contention evidence was performed. This PASS is limited to the W2 code contract and requested local verification; it does not claim Phase 10 full acceptance or live environment evidence. Existing untracked Phase 10 documents and temporary pytest directories have ownership/cleanup status UNKNOWN.
RISKS: `get_environment_facts()` and the projection reader remain freshness gates for future consumers; no live clock/restart/concurrency acceptance was performed. The worktree remains dirty with W1/W2 changes and untracked artifacts; this report does not claim ownership of those artifacts.
NEXT: Hand off W2 PASS to the next Phase 10 wave; retain Phase 10 as In Progress until the remaining roadmap acceptance and live/clean-deployment evidence are independently verified.

## Blocking Findings

None. The prior two W2 HIGH findings are closed.

## Closed Checks

- Probe output is validated at discovery time with non-sensitive metadata:
  `_fact_text_output_valid()`, `_fact_version_output_valid()`, and
  `_fact_positive_int_output_valid()` reject empty, control-character,
  sentinel-unknown, overlong, non-version, zero, negative, boolean, and
  non-numeric values (`extensions/discovery.py:64-88`). The returned evidence
  includes per-probe status and output-validity maps
  (`extensions/discovery.py:633-672`). The original SSH command strings remain
  unchanged at `extensions/discovery.py:446-463`.
- The public manifest preserves only the fixed probe names and requires all
  statuses to be integer zero and all output-validity flags to be true
  (`extensions/orchestrator.py:1734-1759`). The facts verifier independently
  requires both evidence maps, normalizes every mapped field, and refuses to
  mint a token if any normalized value is `None`
  (`extensions/store.py:478-538`). Explicit unknowns therefore remain unknown
  rather than becoming a successful facts record; the regression tests cover
  empty, sentinel, malformed version, zero, negative, and non-numeric values
  (`tests/test_extension_store_contract.py:457-480`).
- `verified_environment_facts()` looks up `target.id` in current persisted
  config and compares the server-recomputed digest before issuing its token
  (`extensions/store.py:526-538`). `save_environment_facts()` and the combined
  observation writer repeat the current-target digest check under lock
  (`extensions/store.py:540-557`, `561-589`). Unsaved and stale targets are
  covered by `tests/test_extension_store_contract.py:528-555`.
- `save_environment_observation()` performs one `_config_lock()`,
  `load_config()`, mutation of both records, and `save_config()` sequence
  (`extensions/store.py:561-589`); the main hook invokes only this combined
  entry point (`main.py:4139-4145`). Save failure leaves the prior config
  unchanged (`tests/test_extension_store_contract.py:500-526`).
- `EnvironmentFacts` remains in config/load/save with legacy omission support,
  per-record malformed isolation, `extra="forbid"`, server-generated UTC
  timestamp, and no projection-to-facts conversion
  (`extensions/models.py:107-147`, `extensions/store.py:260-288`). TTL,
  future/invalid/expired time, and identity-drift rejection remain covered by
  `extensions/store.py:591-609` and the contract tests.
- The W2 diff does not modify `static/`, catalog files, or Phase 12 documents.
  The fact record maps only typed environment summaries; it does not persist
  credentials, tokens, cookies, host-key material, raw commands, complete
  paths, logs, or user data.
