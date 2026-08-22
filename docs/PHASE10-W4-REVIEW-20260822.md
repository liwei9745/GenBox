# Phase 10 W4 Security Review

AGENT: W4 Independent high-intensity Security Reviewer
WAVE: W4
STATUS: BLOCKED
INPUT_HEAD: c1cedd111829e349157f6bfddadca4bfa43ffb33
CHANGED_FILES: docs/PHASE10-W4-REVIEW-20260822.md (review artifact only; no business code changed)
RESULT: BLOCKED. Store projection actions are fail-closed for external, planned, and unavailable items, and visible actions are derived from the capability registry. The W4 ownership evidence is incomplete: the external existing deployment path is reachable through the full deploy/task lifecycle, but the tests stop at plan creation and do not exercise its completion or task routes. The report does not claim adoption, repair, upgrade, rollback, uninstall, or other unimplemented lifecycle functionality.
EVIDENCE: `python -m pytest -q tests/test_extension_store_contract.py tests/test_extensions.py --basetemp=.phase10-w4-review-tmp` -> 257 passed. `python -m py_compile main.py extensions/store.py extensions/capabilities.py` -> passed. `git diff --check` -> passed with no whitespace errors; Git emitted only LF/CRLF conversion warnings. Static review covered the W4 diff, Store contract, strategy, catalog, capabilities, Store, all `main.py` extension routes, orchestrator ownership checks, and the added/modified tests. No browser, npm, remote, or write-side runtime operation was used.
UNKNOWN: No live VPS, isolated deployment, clean deployment, restart, multi-process contention, multi-target Store acceptance, or real adapter adoption flow was verified. No repair, upgrade, backup, rollback, uninstall, or explicit adoption route exists in the reviewed `main.py` route set; those must remain unclaimed. Ownership/cleanup of pre-existing untracked review artifacts and temporary directories remains UNKNOWN.
RISKS: External instances are not given Store actions and the guarded mutation helpers fail closed, but direct callers can still reach the external `strategy=existing` deployment/task path. That path is documented as remote-read-only yet performs local registration and task/delivery state changes; without completion-path tests, the boundary is not proven across the full route lifecycle. Phase 10 must remain In Progress.
NEXT: W4 owner must add route-level ownership tests for the external existing deploy completion path and every instance-handle lifecycle/update entry, including task delivery/resume/cancel, vault credential routes, image-update apply and task projections. Re-review the same input boundary before any Phase 10 close decision.

## Findings

### HIGH: External existing deployment is not closed by a complete route-level ownership gate

`main.py:4065-4103` exposes `/api/extensions/deploy`, and accepts an
`ExtensionDeployRequest` with `strategy="existing"`. The route validates the
generic deployment capability and target role, but does not require the selected
instance to be managed. `extensions/orchestrator.py:2056-2091` deliberately
creates an existing-instance plan with `registers_locally=true` and
`remote_write_expected=false`. The completion path remains reachable:
`extensions/orchestrator.py:923-1038` creates a task, and
`extensions/orchestrator.py:1176-1263` performs SSH reads before calling
`upsert_instance()` and creating a delivery record for the external instance.

This may be intended as a remote-read-only registration flow, but it is still a
deployment/task lifecycle entry that changes GenBox local state and is not a
verified adoption flow. The W4 test at
`tests/test_extensions.py:3069-3119` calls only `extension_deploy_plan()` and
checks `remote_write_expected=false`; it never calls `extension_start_deploy()`
with the confirmed external plan, waits for the task, checks the resulting
instance ownership, checks delivery/resume behavior, or proves that the task
runner cannot perform a remote mutation. The W4 test at
`tests/test_extension_store_contract.py:1005-1069` covers push-source, vault
helper, image-update-plan, and admin-key-reset rejection, but does not cover
this deployment path.

Under the Phase 10 strategy requirement that every instance-handle route have
route-level ownership evidence, this is a blocking evidence gap and a possible
direct-route bypass of the external advisory/read-only boundary.

### MEDIUM: The external route matrix is incomplete beyond the deployment path

The reviewed route set contains task delivery/resume/cancel at
`main.py:4254-4273` and `main.py:5033-5037`, vault credential routes at
`main.py:4523-4937`, and image-update apply/task routes at
`main.py:4973-5012`. The W4 external test invokes only selected helper guards
and the image-update plan. It does not invoke the public vault routes, image
update apply or task projections, or deployment task lifecycle routes.

The implementation has useful lower-level checks: `_managed_vault_instance()`
at `main.py:4581-4585`, `_managed_image_update_instance()` at
`main.py:4780-4796`, and `reset_managed_admin_key()` at
`extensions/orchestrator.py:2348-2352` reject unmanaged instances. Those checks
are not equivalent to a complete route-level proof, especially for routes that
accept only a task ID or return local task state. W4 cannot PASS the stated
ownership acceptance without this matrix.

### MEDIUM: Planned/unavailable visibility is implemented, but the W4 evidence does not prove the full catalog contract

`extensions/store.py:965-976` keeps catalog items in `all` and forces external
installed actions to an empty list. `extensions/capabilities.py:46-58` returns
no action unless the item is `available` and matches the registered capability.
The tests at `tests/test_extension_store_contract.py:644-660` and `769-780`
cover the All shape and empty actions for non-deployable catalog items, and
`964-1002` verifies that manifest/facts cannot add actions.

However, the tests do not explicitly select the concrete
`repository_unverified` catalog item and a planned item, assert both are
present in `all`, and assert their status/provenance gives an actionable
unavailable explanation. The public Store allowlist at
`extensions/store.py:790-806` has no dedicated unavailable-reason field; the
current response relies on `status` and `provenance`. The code is fail-closed
for actions, but this is incomplete acceptance evidence for the contract's
"All with clear reasons" requirement.

## Passing Boundary Checks

- External Store projections force `actions=[]` at `extensions/store.py:967-977`; the contract test checks this at `tests/test_extension_store_contract.py:692-700`.
- Store actions are computed only by `project_store_actions()` at `extensions/store.py:859` and `971-976`, backed by `DEPLOYMENT_CAPABILITIES` at `extensions/capabilities.py:14-21`; manifest and facts injection tests pass at `tests/test_extension_store_contract.py:769-780` and `964-1002`.
- The public metadata projection uses `_PUBLIC_STORE_FIELDS` plus safe defaults at `extensions/store.py:790-824`; tests reject sensitive field keys at `tests/test_extension_store_contract.py:663-677` and route-level response leakage at `582-590`.
- No reviewed test or status claim treats adoption, repair, upgrade, rollback, uninstall, or a complete adapter lifecycle as finished. The existing external plan test is limited to a remote-read-only plan and must not be promoted to adoption evidence.

## Handoff

AGENT: W4 Independent high-intensity Security Reviewer
WAVE: W4
STATUS: BLOCKED
INPUT_HEAD: c1cedd111829e349157f6bfddadca4bfa43ffb33
CHANGED_FILES: docs/PHASE10-W4-REVIEW-20260822.md
RESULT: Store capability/action and metadata key boundaries pass locally; W4 ownership acceptance is blocked by the untested and not explicitly gated external existing deploy/task completion path, plus incomplete instance-handle route coverage.
EVIDENCE: Focused tests 257 passed; requested py_compile passed; requested git diff check passed with only line-ending warnings. Review was read-only apart from creating this report. No browser, npm, remote, commit, or push operation occurred.
UNKNOWN: Full external route lifecycle behavior under real task execution; whether existing-instance local registration is an explicitly approved advisory flow or an adoption boundary; live/isolated/clean-deployment/restart/multi-target evidence; ownership of pre-existing untracked artifacts.
RISKS: Direct deployment/task invocation can create local registration and task/delivery state for an external instance even though Store exposes no action. Missing route-level tests leave the external advisory/read-only guarantee unproven.
NEXT: Add and run the missing external route matrix, decide and enforce the intended policy for existing-instance local registration, then request an independent W4 re-review. Keep Phase 10 In Progress until the matrix is evidenced.
