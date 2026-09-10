# Phase 10 W1 Review

AGENT: Independent high-intensity architecture/security Reviewer
WAVE: W1 re-review
STATUS: PASS
INPUT_HEAD: c1cedd1
CHANGED_FILES: W1 implementation diff: extensions/models.py; tests/test_extension_store_contract.py. Reviewer output: docs/PHASE10-W1-REVIEW-20260822.md. Other observed untracked paths: docs/PHASE10-AGENT-OPS-20260822.md; docs/PHASE10-ORCHESTRATION-STRATEGY-20260822.md; .phase10-review-tmp/; .phase10-w1-fix-tmp/; .phase10-w1-rereview-tmp/.
RESULT: PASS. Within the explicitly limited W1 scope, EnvironmentFacts has the required model-level safety and unknown-value contract, existing EnvironmentProjection is unchanged, focused tests cover positive and negative boundaries, and no W1 implementation file was modified outside the allowed model/test pair.
EVIDENCE: `python -m pytest -q tests/test_extension_store_contract.py --basetemp=.phase10-w1-rereview-tmp` -> 22 passed; `python -m py_compile extensions/models.py` -> passed; `git diff --check` -> passed with only LF/CRLF warnings; HEAD and worktree were inspected on 2026-08-22. No browser, npm, or remote command was run.
UNKNOWN: W2-only behavior was intentionally not used as a W1 gate: ExtensionConfig/load_config/store/main integration, server-side digest recomputation, TTL/freshness enforcement, and discovery conversion/persistence remain unreviewed here. The two Phase 10 documents and temporary directories have unestablished ownership or cleanup status.
RISKS: PASS is limited to the model contract and model-level tests. W2 must preserve the model's `None` unknown semantics and map discovery's `cpu`/`disk_free_mb` values explicitly rather than treating missing values as measured zero. The worktree is not clean because of pre-existing or generated untracked paths.
NEXT: Hand off W1 PASS to the W2 owner, with the W2 integration work required to consume this contract without widening action or recommendation authority.

## Review Checks

- `extra="forbid"` is present at `extensions/models.py:110`; the focused test rejects an `unexpected` field at `tests/test_extension_store_contract.py:208-214`.
- Unknown optional facts are represented by `None` defaults at `extensions/models.py:115-123`; the focused valid fixture preserves `None` for unknown fields at `tests/test_extension_store_contract.py:190-207`, and invalid zero/string values are rejected at `tests/test_extension_store_contract.py:217-232`.
- Field names and types are model-compatible with the existing discovery shapes: `os`, `arch`, and version fields are strings; `cpu_cores`, `memory_mb`, and `disk_mb` are positive integers or `None`, with W2 responsible for explicit `cpu -> cpu_cores` and `disk_free_mb -> disk_mb` conversion.
- `target_id` rejects empty and whitespace-only values at `extensions/models.py:112-129`; `target_identity_digest` requires exactly 64 lowercase hexadecimal characters at `extensions/models.py:113`; negative cases are exercised at `tests/test_extension_store_contract.py:217-232`.
- `observed_at` accepts only the UTC forms `Z` and `+00:00`; non-UTC offsets and a naive timestamp are rejected by the validator at `extensions/models.py:132-138` and tests at `tests/test_extension_store_contract.py:235-248`.
- `EnvironmentProjection` remains exactly the prior seven-field contract, asserted at `tests/test_extension_store_contract.py:182-187`; the diff only inserts `EnvironmentFacts` after that class.
- Tests are not limited to a happy path: they cover extra-field rejection, explicit unknowns, invalid numeric/type values, blank identity, invalid digest, invalid timestamp, UTC boundary cases, legacy config loading, and the unchanged projection field set.
- The W1 implementation diff contains only `extensions/models.py` and `tests/test_extension_store_contract.py`. The untracked documents are review/context artifacts, and the temporary directories were generated or observed during the requested read-only verification; they are not W1 source changes.
