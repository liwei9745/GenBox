# Phase 10 Security Review

**Date:** 2026-08-23  
**Scope:** Read-only review of the uncommitted Phase 10 closure at the requested
input HEAD. No business code, tests, STATUS, or ROADMAP were modified by this
review. No browser, npm, remote, VPS, Docker, Compose, commit, or push operation
was used.

## Verdict

**PASS** for the Phase 10 Store/facts/ownership security contract at the local
code and route-test boundary.

The prior unknown-facts finding in `docs/PHASE10-FINAL-AUDIT-20260823.md` is
closed by the current uncommitted changes: partial facts now survive into the
public discovery and Store projections as explicit `None`/`unknown_facts`
values, and the partial Recommended item has `confidence="unknown"` and
`actions=[]`.

## Findings

### F-001: Documentation commit-state drift

**Severity:** Low, evidence hygiene; not a business-code security defect.

`docs/STATUS.md:15` says the local closure was committed, but the reviewed
worktree is uncommitted at `524cd13ef49bfe957ec053b058b3f4644d6c938e` and has
the eight closure files modified. `docs/PHASE10-FINAL-REVIEW-20260823.md:58-59`
also says committing the closure is a next step. The code verdict remains PASS,
but the commit-state wording must be corrected before claiming a committed
closure.

## Acceptance Matrix

- **Unknown facts fail closed:** PASS. `EnvironmentFacts` uses typed nullable
  fields and `extra="forbid"`; discovery maps failed, missing, invalid, zero,
  and malformed probe values to `None`; public discovery exposes field-level
  `unknown_facts` and `reasons`; Docker/Compose capability fields remain
  `None`, not `false`, when unobserved.
- **Partial Recommended projection:** PASS. `extensions/store.py:1028-1037`
  emits the compatible item only with `confidence="unknown"`, field-level
  unknown facts/reasons, and `actions=[]`. The route contract test covers this
  through `POST /api/extensions/discover` and `GET /api/extensions/store`.
- **Complete facts:** PASS. Nine fresh, identity-bound facts plus complete
  Docker/Compose evidence produce `confidence="high"`, observed-value reasons,
  `unknown_facts=[]`, and the registered `deploy` action.
- **Actions capability-only:** PASS. `project_store_actions()` derives actions
  only from the authoritative capability registry, exact repository identity,
  available status, and Compose capability. Manifest `actions`, manifest
  `capabilities`, facts, and recommendation output cannot grant execution.
  External, planned, and unavailable items remain actionless.
- **External instances read-only:** PASS at the reviewed route boundaries.
  External/unmanaged existing-instance plan/start requests fail with
  `external_instance_adoption_required`; delivery, resume, cancel, Push-source,
  vault, image-update, and admin-key paths fail closed before mutation or remote
  calls. No adoption flow is claimed.
- **Metadata whitelist:** PASS. Store output is projected through the explicit
  public field allowlist with safe defaults. Instance paths, container
  identities, host-key material, credentials, tokens, and other sensitive fields
  are absent from Installed/Recommended/All projections.
- **Identity, TTL, atomicity, and legacy:** PASS. Facts bind to the target
  identity digest, reject future/expired/non-UTC records, and are rechecked under
  the config lock. Projection and facts are written in one atomic config
  transaction. Legacy `extensions.json` without `environment_facts` loads as an
  empty facts list; malformed records are isolated and never upgraded into
  trusted facts.
- **SSH command stability:** PASS. The closure diff changes discovery output
  validation and public projection only. The existing SSH command strings in
  `extensions/discovery.py:492-509` are unchanged by the reviewed diff.
- **Phase 11/12 boundary:** PASS. No AI diagnostic model, raw-log prompt,
  repair executor, experience promotion path, new service adapter lifecycle, or
  external adoption flow was added. Phase 11 and Phase 12 remain planned/out of
  scope.

## Evidence

- `git rev-parse HEAD` ->
  `524cd13ef49bfe957ec053b058b3f4644d6c938e`.
- `python -m pytest -q tests/test_extension_store_contract.py tests/test_extensions.py --basetemp=.phase10-security-review-focused-tmp` -> `260 passed`.
- `python -m pytest -q --basetemp=.phase10-security-review-full-tmp` -> `684 passed`.
- Explicit `python -m py_compile` for `main.py` and the reviewed extension
  modules -> pass.
- `node --check` for `extensions.js`, `app-all.js`, `i18n.js`, and `sync.js` ->
  pass.
- `git diff --check 524cd13 --` on the reviewed closure files -> pass; only
  normal LF/CRLF conversion warnings were emitted.
- Static diff inspection -> no discovery SSH command-string changes.

## Unknown

- No live VPS, isolated VPS, clean deployment, browser/UAT, restart,
  multi-process, or multi-target evidence.
- No verified external adoption flow or adapter lifecycle acceptance.
- Catalog provenance and license values were checked for honest local metadata,
  not independently verified against upstream repositories.
- The two review pytest basetemp directories were created by the verification
  commands and intentionally were not deleted. Pre-existing untracked audit,
  review, heartbeat, and PR-audit documents were left untouched.

## Risks

- `public_store_projection()` selects the first saved
  `isolated-development` target; multi-target Store behavior is not evidenced.
- Task status/list projections are read-only but are not independently bound to
  an instance handle; this is outside the Store mutation boundary and remains a
  residual review risk.
- F-001 can cause an operator to mistake this uncommitted closure for a committed
  artifact unless corrected before release or handoff.

## Next

Keep Phase 10 In Progress. Correct the commit-state wording in the status record
when the closure is actually committed, then retain the stated live/clean-
deployment and adapter-lifecycle boundaries. Do not start Phase 11 or Phase 12
from this local PASS alone.

## Handoff

AGENT: Phase 10 high-thinking security Reviewer  
WAVE: Independent closure security review  
STATUS: PASS  
INPUT_HEAD: 524cd13ef49bfe957ec053b058b3f4644d6c938e  
CHANGED_FILES: `docs/PHASE10-SECURITY-REVIEW-20260823.md` added by this review; reviewed closure files were not modified; two pytest basetemp directories were created and retained  
RESULT: PASS. All requested local security-contract checks pass; F-001 is a low-severity documentation evidence discrepancy and does not change the code verdict.  
EVIDENCE: Focused `260 passed`; full `684 passed`; explicit Python compilation pass; four `node --check` passes; `git diff --check` pass; static SSH-command diff pass.  
UNKNOWN: No live VPS, clean deployment, browser/UAT, restart, multi-process, multi-target, adoption, or adapter-lifecycle evidence.  
RISKS: Multi-target Store selection is not evidenced; read-only task projections are not independently instance-bound; commit-state wording is stale.  
NEXT: Keep Phase 10 In Progress; correct F-001 at the appropriate commit/documentation gate; do not claim Phase 11/12 completion.
