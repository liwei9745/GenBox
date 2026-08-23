# Phase 10 W2 Final Independent Audit

**Date:** 2026-08-23  
**Input HEAD:** `524cd13ef49bfe957ec053b058b3f4644d6c938e`  
**Branch:** `codex/phase7-campaign-20260820`  
**Scope:** Read-only audit of the Phase 10 Store/facts/ownership slice. No
business code, STATUS, or ROADMAP was modified. No browser, npm, remote, VPS,
Docker, commit, or push operation was used.

## Verdict

**BLOCKED. W3 final verification is not allowed.**

The current HEAD preserves the 683-test task lifecycle contract and closes the
prior W4 external-route finding at the tested route boundaries. However,
acceptance 2 is not complete: unknown probe facts are not consistently explicit
in the public discovery/Store experience. Missing numeric discovery values are
projected as `0`, missing version values make capability fields `false`, and an
incomplete facts record is rejected before persistence. The Store therefore
fails closed by returning an empty Recommended view, but does not expose the
field-level unknown facts that the Phase 10 contract requires. The reason helper
and frontend renderer exist, but the current server write path cannot produce a
partial facts record for that UI path.

## Acceptance Audit

### 1. Capability-only visible actions

**PASS for the Store action contract.**

Evidence:

- `extensions/capabilities.py:46-58` derives Store actions only from the
  registered `DEPLOYMENT_CAPABILITIES` entry, requiring `status=available`, the
  exact repository identity, and the registered Compose capability.
- `extensions/store.py:839-860` projects a public allowlist and overwrites
  actions with `project_store_actions(item)`; manifest-provided `actions` and
  `capabilities` are ignored.
- `extensions/store.py:971-977` forces installed external instances to
  `actions=[]`; planned and unavailable catalog items also receive no action.
- `static/js/extensions.js:118-120` renders Store buttons only from the backend
  `item.actions` list, with an explicit `deploy` allowlist in the Store action
  factory. External rows short-circuit to a read-only hint.
- Tests passed: `test_store_contract_actions_derive_only_from_capability`,
  `test_store_contract_manifest_recommendation_and_facts_cannot_grant_actions`,
  and `tests/test_extension_store_frontend.py` action-contract tests.

Boundary: other pre-existing service-card controls are not Store catalog
actions. Their managed-instance guards are covered separately below.

### 2. Unknown/invalid/expired/identity-drift facts and unavailable apps

**BLOCKED.** Fail-closed behavior is present, but explicit unknown-fact
presentation is incomplete.

Evidence that passes:

- `extensions/models.py:107-138` defines typed `EnvironmentFacts`, UTC-only
  timestamps, `None` unknown values, and `extra="forbid"`.
- `extensions/store.py:478-539` issues facts only from server-side discovery,
  requires all nine probe statuses to be integer zero, requires all nine output
  validity flags, normalizes values, and binds the token to the current saved
  target digest.
- `extensions/store.py:542-590` repeats the current-target identity check during
  save and writes projection plus facts in one config-lock/load/save transaction.
- `extensions/store.py:602-620` rejects invalid UTC, future, expired, and
  identity-drift facts. `ENVIRONMENT_FACTS_TTL_SECONDS = 3600` is named and
  enforced.
- `extensions/store.py:890-908` can render field-level `未观测` reasons, and
  `static/js/extensions.js:115-121` has bilingual planned/unverified/unknown
  reason and unknown-facts rendering paths.
- `extensions/catalog.py:31-40,52-65,68-81,89-99` keeps planned and
  repository-unverified entries explicit, with empty actions and metadata
  defaults. `tests/test_extension_store_contract.py:1005-1017` verifies concrete
  `grok2api` and `kiro2api` entries remain unavailable and non-executable.

Blocking evidence:

- `extensions/discovery.py:616-617,632-666` converts absent or invalid numeric
  probe output to `0` and exposes missing version-derived capability as `false`.
  This aliases unknown with a measured zero/unavailable value in the public
  discovery result instead of preserving an explicit unknown state.
- `extensions/orchestrator.py:1801-1806` similarly derives public Docker and
  Compose capability booleans from truthiness, without an unknown state.
- `extensions/store.py:998-1010` returns no Recommended item unless facts are
  complete. Because `verified_environment_facts()` rejects any missing/invalid
  field at `:507-519`, a real incomplete discovery cannot reach the
  `reasons`/`unknown_facts` projection. The frontend's field-level unknown
  renderer is therefore not reachable from the normal incomplete-facts path.
- The existing tests prove empty Recommended and direct helper formatting, but
  do not prove a public response that preserves each unknown field. This is the
  exact gap identified by the strategy's required “field-level fixture and
  public response contract”.

Required closure before W3: preserve typed unknown values through public
discovery/Store projections, or add an explicit public environment-facts status
projection that distinguishes unknown from false/unavailable, then add route
level tests for every missing/invalid probe class.

### 3. External instances advisory/read-only before adoption

**PASS for the implemented local route gates; no adoption is claimed.**

Evidence:

- `main.py:4173-4179` and `main.py:4085-4089` reject external `strategy=existing`
  instances before discovery, plan creation, or task creation with
  `external_instance_adoption_required`.
- `extensions/orchestrator.py:2077-2094` repeats the managed, ownership, and
  target binding check inside plan creation, so direct manager callers cannot
  create an external existing-instance plan.
- Delivery and resume are fail-closed through
  `extensions/orchestrator.py:1100-1136,1138-1183`: delivery requires a
  managed public instance and resume requires a uniquely matching managed
  instance.
- Cancel rejects a task whose binding is explicitly not managed at
  `extensions/orchestrator.py:1076-1098`; the public route is
  `main.py:5070-5074`.
- Push-source and vault routes use managed-instance guards at
  `main.py:4307-4341,4603-4611`; image-update plan/apply/list/status use
  `main.py:4806-4823,4974-5049`; admin-key reset uses the managed guard at
  `extensions/orchestrator.py:2376-2380`.
- `tests/test_extensions.py:3073-3145,3148-3261` covers external deploy
  plan/start, delivery, resume, cancel, vault, image-update, and reset-route
  rejection without remote calls or local instance mutation.

Boundary and residual risk:

- `GET /api/extensions/tasks` and `GET /api/extensions/tasks/{task_id}` expose
  public task projections by task ID and do not independently resolve an
  instance handle. They are read-only status surfaces, not adoption or
  mutation routes; their relationship to an external instance is not proven by
  the route matrix.
- No verified adoption flow exists. No repair, upgrade, backup, rollback,
  uninstall, or external lifecycle completion is claimed. The existing
  `chatgpt2api` deployment path is not evidence that Phase 12 adapter lifecycle
  work is complete.

### 4. Store metadata and secret/identity/path exposure

**PASS for the current public metadata projection, with provenance values still
honest/unverified where the catalog says so.**

Evidence:

- `extensions/store.py:790-824` exposes repository, provenance, license,
  permissions, network exposure, data sensitivity, operational risk, and
  adapter reference through a fixed public whitelist with safe unknown defaults.
- `extensions/catalog.py:5-105` supplies those fields for every catalog item;
  unknown license/risk/exposure values remain explicitly `unknown`, and
  `kiro2api` remains `repository_unverified`.
- `tests/test_extension_store_contract.py:582-590,644-677,892-911` verifies
  required metadata keys, safe defaults, and rejection of secret, host,
  container, identity, credential, and path fields.
- The full suite passed without any metadata or secret-projection failures.

Boundary: this is a public projection and catalog honesty check, not independent
verification of every upstream repository's license or maintenance claims.

## EnvironmentFacts And Compatibility Checks

- **Server-issued token:** PASS. `_VerifiedEnvironmentFacts` is an internal
  dataclass and `verified_environment_facts()` requires server-derived evidence;
  browser payloads do not issue it.
- **Target identity digest:** PASS. The digest covers target endpoint,
  username, identity generation, host-key trust, network selection, and network
  URL at `extensions/store.py:80-93`; current-target comparisons occur before
  token issuance and again under the config lock during save.
- **TTL/UTC:** PASS for `EnvironmentFacts`. UTC is validated by the model and
  freshness rejects future and older-than-3600-second records. The legacy
  `EnvironmentProjection` reader retains its prior naive-time compatibility
  behavior and is not equivalent to the new facts contract.
- **Probe output validity:** PASS for facts issuance. The discovery validators
  reject empty, sentinel, control-character, malformed version, zero, negative,
  boolean, and non-numeric values before a facts token is issued.
- **Atomic projection plus facts write:** PASS. The main hook calls only
  `save_environment_observation()`, which updates both records under one config
  lock and preserves the prior file when save fails.
- **Legacy `extensions.json`:** PASS as compatibility read behavior. Missing
  `environment_facts` loads as an empty list; malformed fact records are isolated;
  old projections are not upgraded into facts.
- **Discovery command strings:** PASS by static diff. The Phase 10 discovery
  diff adds validation/projection fields only; the existing SSH command strings
  at `extensions/discovery.py:470-486` were not changed.

## Phase 11/12 Boundary

**PASS.** No Phase 11 AI diagnostic model, raw-log model prompt, AI repair
executor, or experience promotion path was added. No new Phase 12 service
adapter lifecycle was added. Planned/unverified catalog entries remain
non-executable, and no external adoption flow is represented as complete.

## W4 Task Lifecycle Contract

**PASS.** The required full suite result is `683 passed`; this includes the
existing `tests/test_extension_task_store.py` contract. The W5 record's earlier
15 failures were on the pre-fix cumulative tree at `c1cedd1`; they are not
reproducible at the audited HEAD `524cd13`.

## Commands And Results

Commands were run read-only on Windows PowerShell 5.1 from the requested
worktree. Results:

- `git status --short --branch` -> PASS at audit start: branch
  `codex/phase7-campaign-20260820`, ahead 8, only untracked
  `docs/PHASE9-10-OPS-HEARTBEAT.md`. The requested pytest command later created
  untracked `.phase10-w2-audit-tmp/`; it was not deleted.
- `git diff --stat` -> PASS, no tracked diff output.
- `python -m pytest -q --basetemp=.phase10-w2-audit-tmp` -> PASS, `683 passed
  in 55.41s`.
- `node --check static/js/extensions.js` -> PASS, exit 0.
- Exact requested `python -m py_compile main.py extensions/*.py` -> FAIL at the
  PowerShell invocation layer with `Errno 22 Invalid argument` because the
  wildcard was passed literally. No source compile error was reported.
- Explicit equivalent compile command covering `main.py` and all 14
  `extensions/*.py` modules -> PASS, exit 0.
- `git diff --check` -> PASS, no output.
- `git diff --check origin/codex/phase7-campaign-20260820..HEAD` -> BLOCKED by
  existing trailing whitespace in the tracked strategy document's Markdown
  hard-break lines at lines 3-5. No business-code whitespace error was found;
  the document was not changed because this audit is read-only except for this
  report.
- HEAD check -> PASS, exact HEAD is
  `524cd13ef49bfe957ec053b058b3f4644d6c938e`.

No browser, npm, remote/VPS, Docker, or Compose command was run. No unknown
temporary file was removed.

## Final Handoff

AGENT: Phase 10 W2 high-thinking independent audit Agent  
WAVE: W2 final independent audit  
STATUS: BLOCKED  
INPUT_HEAD: 524cd13ef49bfe957ec053b058b3f4644d6c938e  
CHANGED_FILES: docs/PHASE10-FINAL-AUDIT-20260823.md only; no business code, STATUS, or ROADMAP changed  
RESULT: BLOCKED. Acceptance 1, 3, and 4 pass at the reviewed local contract boundaries; acceptance 2 fails its explicit unknown-facts public-projection requirement. The 683-test lifecycle contract is green at the audited HEAD.  
EVIDENCE: Full pytest `683 passed`; Node syntax check passed; explicit all-module py_compile passed; requested wildcard py_compile failed only because PowerShell passed the wildcard literally; git diff check passed for the working tree; static review covered the required docs, Store/capability/facts/discovery/orchestrator/main/frontend code, and route tests.  
UNKNOWN: No live VPS, isolated deployment, clean deployment, browser/UAT, restart, multi-process, multi-target, or real adoption evidence. Provenance/license semantic verification for upstream repositories remains outside this local audit. Existing untracked heartbeat and generated pytest temp directory ownership remains external/unknown.  
RISKS: Public discovery aliases unknown numeric facts to zero/false; incomplete facts cannot reach the field-level unknown-facts Store renderer; status/read-only task projections are not independently instance-bound; strategy document has pre-existing trailing whitespace.  
NEXT: Keep Phase 10 In Progress. The next single action is to close the acceptance-2 public unknown-facts contract and add route-level tests, then rerun the same verification and request W3 final verification.
