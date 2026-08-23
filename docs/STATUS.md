# Current Project Status

**Last updated:** 2026-08-22
**Current branch:** `codex/phase7-campaign-20260820`
**Current phase:** Phase 9 Sender Push Source Cleanup (User-Selected) - **In Progress (receiver-grant shipped in v2.6.1 2026-08-21; sender PR #26 OPEN/MERGEABLE/UNSTABLE; no maintainer review; Vercel authorization failure is external state and cannot be handled automatically; clean E2E gates passed for receiver)**
**Previous phase:** Phase 8 Upstream Delivery - **In Progress (proposal PRs open, awaiting upstream response)**

## Phase 10 Store projection / environment fact slice (2026-08-22)

- **VERIFIED:** commit `933c09d` adds `GET /api/extensions/store` with Installed,
  Recommended, and All views, identity-bound projections, and actions derived
  from backend capability.
- **VERIFIED:** commit `d2d5eb3` makes future, expired, and forged environment
  projections fail closed, including TTL and identity-bound checks.
- **VERIFIED 2026-08-23 (committed in `1383f53`):**
  - `EnvironmentFacts` typed model (`extra=forbid`, unknown values `None`,
    UTC-only `observed_at`) added in `extensions/models.py`; legacy
    `extensions.json` without the field loads as empty.
  - Server-only facts write token (`verified_environment_facts`), atomic
    projection+facts save, per-target identity/TTL validation, probe
    exit-code + output-validity completeness gate, and `discovery.py` fact
    probe summaries without touching any SSH command string.
  - Store recommendations require fresh identity-bound facts for high confidence;
    partial facts are now public as `confidence=unknown` with field-level
    `unknown_facts`/reasons and `actions=[]`, never defaulting unknown facts.
  - External/unmanaged `strategy=existing` deploy is rejected (`403
    external_instance_adoption_required`) at plan and start; external
    delivery/resume/cancel paths remain read-only fail-closed.
- **LOCAL ACCEPTANCE-2 CLOSURE / PASS:** W1-W4 local review records plus
  `docs/PHASE10-FINAL-REVIEW-20260823.md`; final local verification 2026-08-23:
  `684 passed`; four `node --check` commands, explicit `py_compile`, and
  `git diff --check` passed. This PASS is local acceptance-2 closure only; it
  does not claim live or clean-deployment acceptance.
- **PHASE 10B LOCAL EXTENSION / VERIFIED 2026-08-23 (committed in `1383f53`):** frontend
  Store rendering now blocks deploy for unknown/partial/planned/external rows
  and displays null Docker/Compose capabilities as unknown; all 12 catalog
  entries pass metadata completeness checks. Final local verification after
  the frontend regression fix: `686 passed`, Node checks, explicit `py_compile`,
  and `git diff --check` passed. This does not change the live/clean-deployment
  boundary.
- **CLEAN DEPLOYMENT / BLOCKED 2026-08-23:** authorized push to the personal
  GenBox branch completed at `1383f53`; clean clone and local Docker image build
  passed. Compose execution was not accepted because Windows path handling
  could not open the cloned Compose file. A Docker-only fallback stopped at the
  setup-status assertion before Store API checks. All temporary resources were
  cleaned; no VPS, SSH, upstream PR, or production operation occurred.
- **BOUNDARY:** Recommended is high only with complete verified discovery and
  Docker/Compose evidence plus all nine environment facts observed. The current
  slice still requires live/clean-deployment, restart, multi-target, and adapter
  lifecycle verification plus full Store acceptance; Phase 10 remains In
  Progress and is not complete.

## Phase 9 Sender Push Source Cleanup (User-Selected) queued (2026-08-20)

- **USER DECISION / VERIFIED:** per explicit user direction, sender-side source
  cleanup is now a **per-action user selection** for both manual one-shot Push
  and scheduled Push: whether to delete the source image is the user's choice
  for that run, not a forced fixed selection. Recorded in ADR-026.
- **SCOPE:** receiver grant path capable of returning `safe_to_delete_source=true`
  only under authenticated matching receipt + source-bytes SHA-256 match, plus
  sender-side per-run user selection in the chatgpt2api fork. v2.6.0 receiver
  behavior (`false` at `main.py:3621`) is unchanged by this queueing; historical
  evidence keeps `false` as audit trail.
- **ROADMAP:** Phase 9 inserted after Phase 8; original Store/Copilot/Adapters/
  Notifications phases renumbered 10-14. ADR-024/025 boundaries retained.
- **RESUME:** receiver implementation and sender implementation are complete in
  isolated worktrees. Remaining delivery gates are a scoped GenBox release for
  the receiver grant path, maintainer review of the sender PR, and a clean
  end-to-end verification after both sides are available. No production VPS,
  tag, or release is changed by this status update.
- **STEP 1 RECEIVER GRANT PATH / DONE 2026-08-20:** implemented a per-source
  deletion grant (default off) in `sync/push_sources.py`
  (`grant_delete` field + `set_source_grant_delete()` + `deletion_granted()`),
  a PATCH endpoint
  `/api/extensions/push-sources/{handle}/{source_id}/grant-delete`, and the
  receipt grants `safe_to_delete_source=true` only when the managed source was
  explicitly granted AND the request committed this exact path+content
  (`imported`/`already-imported`); `duplicate-local` import from another path is
  never granted and any registry error fails closed. v2.6.0 default
  (`false` at `main.py:3621`) is unchanged until a receiver release carries the
  grant path. Added tests in `tests/test_push_sources.py`
  (`test_receipt_grants_deletion_only_after_explicit_source_grant`,
  `test_grant_delete_api_toggles_managed_source`); full suite
  `619 passed` (previously 617 + 2 new), targeted `45 passed`.
   `docs/INTEGRATION.md` now documents the grant semantics and the per-action
   user selection.
- **SENDER IMPLEMENTATION / VERIFIED 2026-08-21:** isolated sender branch
  `codex/phase6-final-gate-20260809` contains the API, cleanup, batch, schedule,
  outbox, single-image generation flow, and UI selection work. Sender
  regression suite: `147 passed, 7 skipped`; `web-vue` `npm run build` passed.
  The branch is preserved on the owner's fork
  `liwei9745/chatgpt2api` and is not an upstream branch.
- **YUKKCAT PR / VERIFIED OPEN 2026-08-21:** focused PR
  `https://github.com/yukkcat/chatgpt2api/pull/26` is based on yukkcat
  `main=9d3e6fc`, head commit `739eef6`, and comes from the independent fork
  `liwei9745/chatgpt2api-yukkcat`. It contains only the yukkcat-native
  receipt-gated cleanup choice (8 files, one commit); the original repository
  `main` was not overwritten.
- **CURRENT PR STATE / VERIFIED 2026-08-23:** PR #26 is `OPEN`,
  `MERGEABLE`, and `UNSTABLE`; no maintainer review or decision is recorded.
  The failed Vercel check requires external team authorization. It is external
  state and cannot be handled automatically; Phase 9 remains In Progress.
- **PR RECOVERY POLICY / ACCEPTED:** if PR #26 is rejected, do not delete the
  fork or rewrite the upstream repository. Preserve the fork branch and commit,
  record the maintainer reason, create a new revision branch from the latest
  yukkcat `main`, apply only the requested changes, rerun validation, and open a
  replacement PR. A rejection is a review outcome, not permission to force-push
  or replace the original repository.
- **RECEIVER UI / VERIFIED 2026-08-21:** the Extension Center Push-source
  setup now exposes `允许授权删除源图`, default off, backed by the managed
  source PATCH grant endpoint. Failed updates restore the previous checkbox
  state and offline controls remain locked. `node --check static/js/extensions.js`
  passed; full GenBox suite passed `619 tests` after this change. Commit:
  `76a5e53`.
- **RECEIVER UI CONTRACT TEST / VERIFIED 2026-08-21:** added a static browser
  contract test for the grant checkbox, state synchronization, PATCH endpoint,
  failed-update rollback, offline lock, and default-off copy. Full GenBox suite
  now passes `620 tests`; extension contract tests pass `205`. Commit:
  `577f559`.
- **RECEIVER GRANT I18N / VERIFIED 2026-08-21:** the grant checkbox label,
  hint, and toggle success messages now use `i18n.js` keys (zh-CN + en) instead
  of hard-coded Chinese; the static contract test asserts the keys and English
  copy. Full GenBox suite passes `620 tests`; extension tests pass `205`.
  Commit: `fd0a284`. NOTE: earlier PowerShell-assisted edits corrupted motif
  bytes of some zh-CN strings inside already-committed static files; the i18n
  integration and its tests were re-applied cleanly with the `edit` tool, and
  that byte corruption is out of scope for this commit (historical commits are
  preserved as record).
- **V2.6.1 SCOPED RELEASE / PUBLISHED 2026-08-21:** receiver-side deletion
  grant shipped as patch release `v2.6.1` (annotated tag object `51273543…` ->
  commit `2bbd459`). CI runs (push-triggered, head `2bbd459`, both completed
  success): Docker Image `32498587828`; Desktop Clients `32498587781`. GitHub
  Release `GenBox v2.6.1` published 2026-08-21T15:40:22Z (non-draft,
  non-prerelease) with Windows/macOS/Linux zips + exe, Docker Compose bundle
  `GenBox-Docker-Compose-v2.6.1.zip`, and `SHA256SUMS.txt`. GHCR
  `ghcr.io/liwei9745/genbox:2.6.1` and `:2.6` both resolve to digest
  `sha256:7ade2a482ce646bd21c9f6229ad508ef6567263b844128506418a42b23213b66`.
  Build smoke: `python build.py` produced `dist\GenBox.exe` 38,089,061 B,
  SHA-256 `B065FC7688540DC7AF426537E185A0454ADFA51F36DDE9C45500B9497ED863FD`.
- **V2.6.1 CLEAN DEPLOYMENT ACCEPTANCE / PASSED 2026-08-22:** isolated temp
  container `v261acct` (project `v261acc`, host port 18991) from the Release
  compose bundle + GHCR 2.6.1. Receipt matrix over HTTP: status probe
  `contract_version=v1`; default (grant off) push -> `imported` with
  `safe_to_delete_source=false`; replay -> `already-imported` still `false`;
  wrong key -> 401; mismatched `source_sha256` -> 422 with nothing committed;
  managed-instance PATCH endpoint verified bound to enrolled instances (404 on
  synthetic handle). Grant-on behavior covered by repository tests
  `test_receipt_grants_deletion_only_after_explicit_source_grant` and
  `test_grant_delete_api_toggles_managed_source` (push_sources suite passed,
  packaging 11 passed). Container/network/teardown clean; no existing VPS,
  container, or compile environment touched. Resume/heartbeat checkpoint:
  `docs/RESUME-RELEASE-v2.6.1.md` (STATUS: OK).

## Phase 6 close-out (Line A, 2026-08-20)

- **CLOSE-OUT / USER-APPROVED:** Phase 6 closed as receiver-grant-verification
  scope. ROADMAP Phase 6 status updated to Complete; destructive execution,
  adversarial approval, isolated-VPS acceptance, host authority, and human
  authorization are explicitly NOT claimed and carried to a future milestone.
- **STRUCTURAL BASIS / VERIFIED:** `main.py:3621` hard-codes
  `safe_to_delete_source=false` in the scoped release (ADR-024 scope-A), so the
  receiver never grants deletion permission and the Acceptance Criterion
  "only a matching authenticated receipt with `safe_to_delete_source=true`
  authorizes deletion" holds vacuously by design.
- **EVIDENCE RETAINED:** all prior local non-destructive records (sender
  isolated-clone A1-A12 matrix `116/185 passed`; receiver loopback harness 28
  tests; hosted `31256853882`) remain valid as receiving-side attestation only.
- **NON-CLAIMS:** no sender cleanup release, no CI/macOS or isolated-VPS claim,
  no real-media or destructive exercise. Sender cleanup code lives only in
  worktree `E:\AI\chatgpt2api-worktrees\phase6-final-gate-20260809` (never
  pushed, 480 commits ahead of upstream, `cleanup-security.yml` absent from any
  pushed default branch).
- **RESUME:** Phase 7 (Sanitized GitHub Redeployment) is the current phase.

## v2.6.0 stable release prep (2026-08-20)

- **SCOPE-A / FIXED BY COORDINATOR:** stable v2.6.0 scope is "client +
  extension center + image Push receiving". Source-file cleanup is NOT claimed
  anywhere in the release materials and remains disabled / out of scope.
- **BASE / VERIFIED:** prep is based on the rc.8 candidate lineage (branch
  `codex/v2.6.0-rc.8-final-candidate`, consolidated UAT recorded 2026-08-10).
  At prep time no tag or GitHub Release existed; both were created later under
  the published section below.
- **CHANGES APPLIED / VERIFIED LOCALLY:** `genbox_version.py` -> `2.6.0`;
  stable notes `release-notes-v2.6.0{,-zh}.md` created and `RELEASE_NOTES.md`
  repointed to them; `CHANGELOG.md` gained the `[2.6.0]` section and the dense
  Phase 6 `[Unreleased]` detail was folded into a short In Progress note;
  Compose image pinned to `ghcr.io/liwei9745/genbox:2.6.0`; packaging tests
  updated to the stable version; current-version README prose updated;
  `docs/INTEGRATION.md` now states the v1 receiver returns
  `safe_to_delete_source=false` in this release with sender cleanup disabled.
- **LOCAL TESTS / VERIFIED 2026-08-20 (Python 3.14.3, not CI 3.12):**
  `python -m pytest -q tests/test_release_packaging.py` -> `11 passed`;
  `python -m pytest -q tests/test_sync_push_routes.py` -> `27 passed`;
  `python -m pytest -q tests/test_push_sources.py tests/test_credential_vault.py
  tests/test_extensions.py` -> `237 passed`. `node --check` on
  `static/js/app-all.js`, `extensions.js`, `i18n.js`, and `sync.js` -> pass.
  `python scripts/build_readme_lab.py` regenerated
  `static/readme-lab-content.json` deterministically (identical SHA-256 on a
  second run); `python -m py_compile main.py updater.py` -> pass;
  `git diff --check` -> pass.
- **ENVIRONMENT NOTE:** pytest's default temp-root cleanup (removing the
  `pytest-current` directory) hit a Windows `PermissionError` at session
  teardown on 3.14.3; reruns with `--basetemp=<local temp>` complete cleanly.
  No assertion was relaxed; this is an environment-only teardown artifact.
- **FINAL VERIFICATION / VERIFIED 2026-08-20:** full suite
  `python -m pytest -q` -> `617 passed` (run twice, before and after the lab
  release-doc follow-up); semantic and mechanical release reviewers both
  returned PASS; added-lines secret/port scan -> zero hits; the Lab
  `release` sub-document now points to the v2.6.0 notes
  (`scripts/build_readme_lab.py` + `static/readme-lab.html` label + packaging
  test updated, JSON regenerated deterministically). ADR-024 records the
  scope-A/base decision.
- **WINDOWS PACKAGE / VERIFIED 2026-08-20:** `python build.py` succeeded;
  `dist/GenBox.exe` is `38,085,414` bytes with SHA-256
  `94F5D3D8793FD73508EE72288FF17D4836A3E76139A55FD21AE9703CAFCCD713`;
  packaged random-loopback smoke passed. `dist/`, `build/`, and `GenBox.spec`
  are git-ignored and not part of the diff.
- **CURRENT STATE:** v2.6.0 is published; see the published section below.
  This change set records the publish evidence and hardens the CI flaky vault
  test, is committed locally, and is pushed only with a new explicit
  authorization.
- **RESUME INSTRUCTIONS:** verify the local commit (tests green) and decide the
  next roadmap step. Pushing this follow-up commit is a separate
  authorization.

## v2.6.0 stable release published (2026-08-20)

- **PUBLISHED / VERIFIED:** after explicit coordinator approval, commit
  `bd8e435` was created on `codex/v2.6.0-release-prep-20260820`, pushed to
  origin, and annotated tag `v2.6.0` (tag object `d68115a` -> `bd8e435`) was
  pushed, triggering `build.yml` and `docker.yml` on the tag.
- **CI / VERIFIED:** `docker.yml` -> success; GHCR
  `ghcr.io/liwei9745/genbox:2.6.0`, `:2.6`, and `:latest` all resolve.
  `build.yml` first run failed once on the Playwright UI test
  `test_vault_toolbar_button_matches_configured_lock_state` (click timeout on
  `#extVaultLockBtn`, button stayed disabled). The test file is not touched by
  the release prep and the identical job passed at the rc.8 candidate CI run
  (run `31358814412`), so it was judged an environment flake, not a
  regression. The full run was re-run and completed success: test job,
  Windows/macOS/Linux builds, and Create Release all green.
- **RELEASE / VERIFIED:** GitHub Release `GenBox v2.6.0` published
  2026-08-20T06:07:40Z (not draft/prerelease); body consumed
  `release-notes-v2.6.0-zh.md`; assets include Windows/macOS/Linux zips,
  `GenBox.exe`, the Docker compose bundle, and `SHA256SUMS.txt`.
- **POST-PUBLISH HARDENING / 2026-08-20:** the CI flake above is addressed in
  `tests/test_credential_visibility_browser.py` with explicit enabled-state
  `wait_for_function` preconditions before the button clicks (3/3 consecutive
  local passes). No application code changed.

## Upstream extension proposal PRs (2026-08-20)

- **PRECONDITION / USER-CONFIRMED:** the Phase 7/8 campaign only starts after
  (a) completed development achievements, (b) the new version is pushed to
  GitHub, and (c) a PR is submitted to the chatgpt2api author. Conditions (a)
  and (b) hold via the v2.6.0 publish above. Condition (c) completed below.
- **PROPOSAL / CREATED:** an integration extension proposal was drafted based on
  the verified GenBox Push contract v1 and the existing
  `docs/UPSTREAM-VIBE-CODING-GUIDE.md`. It contains no sender code, no
  credentials, no ports, no IPs, and no environment-specific values.
- **FORK / VERIFIED:** local sender worktree branch has never been pushed and
  differs from its fork by 443 files; the full sender code PR was therefore
  rejected (Phase 8 requires Phase 7 evidence and narrow PRs first). Proposal
  form confirmed by user.
- **basketikun PR / VERIFIED OPEN:**
  `https://github.com/basketikun/chatgpt2api/pull/387` - created
  2026-08-20T13:09:25Z on branch `proposal/genbox-push-extension`
  (commit `fa50ea6`, based on basketikun main `dc105e5`). Files:
  `docs/genbox-push-extension-proposal.md` + one README link line under the
  Experimental section. Basketikun is the fork network parent of
  `liwei9745/chatgpt2api`.
- **yukkcat PR / VERIFIED OPEN:**
  `https://github.com/yukkcat/chatgpt2api/pull/25` - created
  2026-08-20T13:11:35Z on branch `proposal-yukkcat` (commit `6d38a87`, based
  on yukkcat main `9d3e6fc`). Files:
  `docs/references/genbox-push-extension-proposal.md` + `docs/README.md`
  navigation entry. yukkcat is a separate root repository; a dedicated fork
  `liwei9745/chatgpt2api-yukkcat` was created for it.
- **BOUNDARY / VERIFIED:** no GenBox code, tags, releases, or production VPS
  were touched by this work. Both PRs are documentation-only and make no
  claim that sender-side code exists.

## Phase 7 clean redeployment campaign (2026-08-20)

- **BRANCH:** `codex/phase7-campaign-20260820` (based on `03c46a4`); campaign
  plan `docs/CANP7-CAMPAIGN-20260820.md`; this section records the P7.A/P7.B
  evidence and the P7.C summary. Commits `0ed01c9` + `f91a248` were pushed to
  origin 2026-08-20 after explicit gate authorization (docs-only; no tags,
  releases, or VPS touched).
- **P7.A SECRET AND PERSONAL-DATA SCAN / VERIFIED PASS:** tracked files + full
  `git log --all -p` scanned for secret patterns (`sk-*`, `ghp_`,
  `github_pat_`, `AKIA…`, `xox…`, private-key headers, SSH keys, `.pem`,
  `id_*`). Zero software hits; the only literal matches are test sentinels in
  `tests/test_extension_task_store.py` (UI-masking escape-hatch fixtures).
  All port references resolve to three benign classes: Class 1 product default
  ports (`extensions/models.py:168,225` `service_port=33010`;
  `config.py:118`/`main.py:2829` `port=10808`; frontend `d.port || 10808`)
  present since before v2.6.0; Class 2 dated historical evidence text in docs
  (kept as labelled audit trail, not rewritten); Class 3 loopback/example hosts
  (`127.0.0.1`). Report: `docs/PHASE7-SCAN-REPORT-20260820.md`.
- **P7.B CLEAN DEPLOYMENT SINGLE + BATCH PUSH / VERIFIED PASS 2026-08-20:**
  downloaded Release asset `GenBox-Docker-Compose-v2.6.0.zip`, pulled GHCR
  `ghcr.io/liwei9745/genbox:2.6.0` (digest `sha256:102333af…`), and started an
  isolated container (project `p7acc`, container `p7accrec`, host port `18990`,
  synthetic one-shot `ADMIN_KEY` + Push key, prod mode). Live-HTTP acceptance
  over `127.0.0.1:18990`: status probe 200 (contract `v1`); wrong Push key
  rejected 401; single push -> `imported`; identical re-push -> `already-imported`
  (idempotent, same file); same-content different path -> `duplicate-local`;
  10 distinct images with 4-way concurrency -> all `imported` (one deterministic
  re-run over distinct hashes converged 10/10; a prior run hit the content-dedupe
  path as expected); every receipt returns `safe_to_delete_source=false`.
  Container and network removed in teardown; no production VPS, tags, or
  secrets touched. Issue encountered and recorded: `GENBOX_PUSH_KEYS` must be
  injected as an environment variable (compose `environment`), not only via
  `.env` file mount, because `sync/ingest.py:38` reads process env; and the
  value must be valid single-quoted JSON (`""` literal-breaking under compose
  is an operator pitfall, not a product bug).
- **P7.C LOCAL SUITE / VERIFIED PASS 2026-08-20 (Python 3.14.3):**
  `python -m pytest tests/ --tb=no -p no:cacheprovider` -> `41 passed`;
  focused `tests/test_sync_push_routes.py` + `tests/test_phase6_loopback_receiver.py`
  -> `28 passed`. The BytesIO `PermissionError WinError 5` on `pytest-current`
  teardown is the already-documented Windows temp-root cleanup artifact.
- **RESUME:** P8 remaining upstream delivery steps (proposal final wording +
  compatibility notes alignment) are next; campaign commits await gate.

## v2.6.0-rc.8 final candidate and consolidated manual UAT (2026-08-10)

- **CANDIDATE / VERIFIED:** code commit
  `07b89abc4bd0297cf665516c037a95152c78f8fa`, based on rc.7 candidate
  `fbf3769ec40f54095e047efc59c7fc7d730a48ee`. It includes the complete
  verified rc.8 UI chain, including the vault toolbar state label and the
  locked local Push-key deletion guard.
- **LOCAL TESTS / VERIFIED:** focused regression `260 passed`; exact-candidate
  full suite `617 passed`. JavaScript syntax checks, `git diff --check`, and
  candidate diff, commit-message, and executable leak scans passed. The only
  source scan match was an existing synthetic test sentinel, not a credential.
- **WINDOWS PACKAGE / VERIFIED:** `dist/GenBox.exe` built successfully, is
  `38,085,855` bytes, and has SHA-256
  `9D67A45D62E39FA79F6F585FA235E30BDDE18C7989BC90272E20A9F8B386A223`.
  Packaged random-loopback smoke passed.
- **MANUAL UAT / USER-CONFIRMED:** on 2026-08-10, the user completed the
  consolidated 1-10 UAT flow in a loopback-only synthetic lab using the exact
  candidate EXE. It covered the deployed-service entry, no-Key Chinese
  guidance, key creation or rotation, real-line-break configuration copy,
  explicit vault-save choice, vault setup/lock/unlock, independent sensitive
  field visibility, locked deletion guard, local-copy deletion, receiver-side
  configured/not-revoked state, and no plaintext after refresh or restart.
  The lab was stopped after the pass. No screenshots, Push keys, vault files,
  real credentials, media, or runtime logs were added to Git.
- **CONFIRMATION CLARIFICATION / ACCEPTED FOR THIS UAT:** saving a Push key
  uses the explicit GenBox-owned page modal, not a browser or Windows native
  dialog. Its confirm path obtains a 120-second, single-use token bound to the
  instance handle, source ID, and current key digest before an unlocked-vault
  write. The user accepted this confirmation form for the rc.8 UAT. Native
  confirmation remains used for deleting the local Push-key copy.
- **REMOTE STATUS BOUNDARY:** the receiver registry may truthfully report
  configured and not revoked. It cannot prove a remote chatgpt2api sender is
  configured, authenticated, or active; that remains `UNVERIFIED` without
  separate sender and isolated-environment evidence.
- **BOUNDARY:** this is a release candidate only. No tag or formal Release was
  created. No VPS, SSH, `33010`, `33018`, real credential/media, cleanup,
  unlink, execute marker, Phase 6 destructive exercise, or Phase 7 execution
  was used or authorized.

## Phase 6 final-gate worktree baseline (2026-08-09)

- **GENBOX WORKTREE / VERIFIED:** `E:\AI\GenBox-worktrees\p4planux\GenBox-od-phase6-final-gate-20260809`, branch `codex/phase6-final-gate-20260809`, baseline `1c2f870bb6ee616c333a717239349bceb2182a20`, clean at gate start.
- **SENDER WORKTREE / VERIFIED:** `E:\AI\chatgpt2api-worktrees\phase6-final-gate-20260809`, branch `codex/phase6-final-gate-20260809`, baseline `19c2fdbb23a97c713b53955942d325fb725708d1`, clean at gate start.
- This gate is non-destructive and uses only synthetic data, temporary directories, local Docker, and local/hosted evidence that is explicitly labeled. VPS, SSH, `33010`, `33018`, real cleanup, execute markers, production changes, human UAT, Release, and Phase 7 implementation remain outside this worktree's authority.

## Phase 6 exact-SHA CI convergence (2026-08-09)

- **GENBOX LOCAL / VERIFIED:** fixed-baseline focused suite `65 passed`; full suite `611 passed`; browser collection suite `8 passed`; Windows build and packaged loopback smoke passed on an OS-assigned port. Local Docker build/runtime passed with a synthetic administrator key and random loopback port.
- **GENBOX CI / PARTIAL:** workflow run `31300431651` reached the exact pushed commit `79038f2` but failed during collection because hosted test dependencies omitted Playwright. The minimal infrastructure fix is local commit `05c7f3b` (adds Playwright dependency and Chromium install); its push failed twice with TLS/HTTP2 EOF, so exact-SHA post-fix CI is `UNVERIFIED`.
- **SENDER LOCAL / VERIFIED:** full suite `168 passed, 18 skipped, 249 subtests passed`; focused single/batch/schedule/cleanup suite `127 passed, 7 skipped, 20 subtests`; Docker image and `/health` smoke passed with a synthetic auth key on a random loopback port. Sender CI dispatch was unavailable because `cleanup-security.yml` is absent from the repository default branch; this remains `UNVERIFIED`.
- **BOUNDARY:** no product code changed in this convergence pass. Cleanup, unlink, execute markers, VPS/SSH, `33010`, `33018`, production changes, Release/tag/RC, and Phase 7/G-Store implementation remain prohibited.

## Phase 6 local and CI convergence (2026-08-09)

- **SENDER LOCAL / RECORDED VERIFIED (2026-08-08):** the sender evidence record
  at `docs/PHASE6-LOCAL-GATES-EVIDENCE.md` reports synthetic coverage for A1,
  A2, A3, A5, A6, A10, and A11. Its focused commands report `116 passed, 18
  skipped`; full discovery reports `185 passed, 18 skipped`; compilation and
  diff checks pass. Platform skips are explicitly not counted as passes.
- **SENDER CI / RECORDED VERIFIED (2026-08-08):** hosted run `31256853882`
  reports passing Windows and Ubuntu sender service/cleanup/storage suites, an
  eight-case macOS core matrix, and the immutable-anchor image contract. macOS
  A6 multi-process claims and A10 mixed-result cleanup remain `EXTERNAL`; the
  opt-in Docker integration cases, isolated-VPS acceptance, host authority, and
  human authorization also remain external.
- **GENBOX LOCAL / VERIFIED (2026-08-09):**
  `python -m pytest -q tests/test_phase6_loopback_receiver.py
  tests/test_sync_push_routes.py` -> `28 passed`. The new disposable harness
  starts the actual receiver on an OS-assigned `127.0.0.1` port, uses a
  temporary gallery plus generated synthetic source ID, Push key, and PNG, and
  confirms the sender-shaped source remains unchanged. The receipt always has
  `safe_to_delete_source=false`; no cleanup path is exercised or enabled.
- **GENBOX REGRESSION / VERIFIED (2026-08-09):** `python -m pytest -q` ->
  `611 passed`.
- **BLOCKERS / NON-CLAIMS:** this evidence does not authorize cleanup, an
  execute marker, a VPS operation, a deployment, Phase 6 completion, Phase 7,
  or release work. No `33010` or `33018` operation was performed for this
  convergence run. Independent review and the separately authorized external
  gates remain required.

## Client candidate verification (2026-08-06)

- **LOCAL / VERIFIED:** `v2.6.0-rc.1` is a client-only experimental candidate.
  It retains the completed Push UI: a deployed managed chatgpt2api card can
  open Push configuration; users can copy its destination URL, source ID, and
  Push key; and they can explicitly save and later reopen those values in the
  encrypted local credential vault. Push keys are not sent to browser storage
  or URLs.
- **LOCAL / VERIFIED:** `python -m pytest -q tests/test_credential_vault.py
  tests/test_push_sources.py tests/test_extensions.py tests/test_release_packaging.py`
  -> `234 passed`; `python -m pytest -q` -> `589 passed`.
- **LOCAL / VERIFIED:** `python build.py` produced `dist/GenBox.exe`
  (`38,072,785` bytes; SHA-256
  `ED15561345F3BA3900EB882AD8E2EC1EA112957F9EE7D8EE7C5E95CBEC6DB456`).
  `python scripts/smoke_client.py --executable dist/GenBox.exe --timeout 60`
  passed on a random loopback port.
- **BOUNDARY:** this candidate is limited to local validation and branch delivery.

## Image-update feedback investigation (2026-08-02)

- **LOCAL / VERIFIED:** the managed isolated-image update endpoint previously
  awaited the full SSH/Docker operation in the browser request and exposed no
  task ID, status projection, progress, or restart state. The browser therefore
  had no reliable feedback chain after `Confirm update`.
- **LOCAL / VERIFIED:** the apply path now consumes the single-use plan, returns
  a public-only `task_id` immediately, and exposes a status endpoint with queued,
  running, completed, failed, and interrupted states, phase progress, sanitized
  logs, and recovery guidance. The UI polls this task and keeps the modal state
  visible until a terminal result; refresh recovery is represented as an
  `interrupted` task and never replays remote work automatically.
- **LOCAL / VERIFIED:** the task runner retrieves the saved SSH credential only
  in memory, never persists it, and clears it after the bounded operation. The
  existing immutable-image, isolated-target, health-verification, rollback, and
  single-use plan checks remain in force.
- **LOCAL / VERIFIED:** `python -m pytest -q` -> `586 passed`; `python -m
  py_compile main.py`; `node --check static/js/extensions.js`; `git diff --check`.
- **LOCAL + GITHUB / VERIFIED 2026-08-02:** commit `21fd3ad` adds a strict
  public-only schema for persisted image-update tasks, a task-list endpoint and
  browser-refresh recovery, single-flight polling, and remote rollback when
  the local instance registration cannot be committed. The branch
  `codex/p4-deploy-plan-ux-eai` is pushed to the owner's GenBox repository.
- **ISOLATED-VPS / VERIFIED 2026-08-02:** launcher-owned GenBox runtime `8910`
  reported `runtime_head=21fd3ad`. Its single-use managed update plan selected
  only the registered isolated sender on port `33010` and applied immutable
  image `ghcr.io/liwei9745/chatgpt2api-genbox-p5@sha256:ff602c575b3bcabae24f73ef079582ff147cf25c3506dddb9b190f04fe67e5ac`.
  The task returned immediately, persisted its task ID, and reached
  `completed / 100%` with connect, update, and health-verification steps all
  successful. The sender then returned HTTP 200 from `/version` and a healthy
  JSON `/health` response.
- **PRIVATE ROUTE / VERIFIED 2026-08-02:** the sender's saved Push URL initially
  resolved to the stale local `8895` runtime with empty runtime identity, so no
  Push was accepted as evidence there. GenBox's fixed local Tailscale Serve
  action replaced only that single owned stale route and bound the same private
  entry to current runtime `8910 / 21fd3ad`; a new sender-side protocol probe
  then reported GenBox Push v1 ready.
- **PROTOCOL / VERIFIED 2026-08-02:** one recoverable isolated Push was retried
  after the private route was corrected. The sender reached the terminal
  `already imported` outcome, the downloaded source bytes and GenBox manifest
  carried the same SHA-256 (value withheld from Git), and the source remained
  present with the same byte length. This proves receipt/hash binding,
  idempotent retry, and retention for this item; it does not prove cleanup
  execution or crash recovery.
- **PRODUCTION BOUNDARY / VERIFIED 2026-08-02:** the locally registered `33018`
  record retained its original creation/update timestamps. No HTTP, SSH,
  restart, image update, deployment, or cleanup request was sent to `33018`.
- **LOCAL SENDER / VERIFIED 2026-08-02:** the current isolated sender candidate
  is commit `96d57de`, pushed to the owner's experimental sender repository.
  Windows full verification passes `121 passed, 10 skipped`; clean Linux-
  container full verification passes `130 passed, 1 skipped`. The candidate
  adds a kernel write lease/Windows write-sharing fence, final and post-
  tombstone content rechecks, deterministic cleanup transaction names,
  read-only artifact inspection during recovery, and real exchange/tombstone/
  audit-boundary crash tests. No image built from `96d57de` has been deployed.
- **LINUX SENDER / VERIFIED 2026-08-02:** the same `f0d5beb` source was tested
  in a clean Linux container. POSIX storage-race coverage passed `8` tests with
  one Windows-only junction skip; cleanup, crash, and transport coverage passed
  `56`; and the generic deletion guard plus transfer, batch, and schedule
  regressions passed `38`. Total new Linux evidence is `102 passed, 1 platform
  skip`. This covers replacement races, hard links, symlinks, POSIX exchange,
  crash points around unlink, lifespan recovery, cross-process claims,
  slow-drip and bounded receipts, redirects, destination rotation, and cleanup-
  disabled regressions.
- **A4/A7 FOCUSED / VERIFIED 2026-08-02:** on the updated `96d57de` source,
  Linux storage-race coverage passes `11` tests with one Windows-only skip and
  cleanup/crash/transport coverage passes `46` tests with one platform skip.
  The cross-process writer test proves the result is either a retained changed
  source or deletion after the writer is blocked; it never permits changed
  content to be deleted. Exchange/tombstone crashes leave deterministic,
  hash-checkable artifacts and recovery records `retained` or
  `delete_unknown` without deleting during startup.
- **ISOLATED CLEANUP DRY-RUN / VERIFIED 2026-08-02:** the unlocked local vault
  supplied the isolated `33010` management credential in memory only. The
  deployed sender reported cleanup disabled, environment class `unknown`, and
  execute unavailable. Its non-destructive preview found one candidate, zero
  eligible items, one retained item, and reason `cleanup-policy-disabled`; no
  cleanup execute endpoint was called.

## Phase 6 resume point

- **LOCAL / VERIFIED 2026-08-01:** Phase 6 protocol, platform, multi-agent, and
  adversarial-review contracts are committed locally in `0911c16`, `08a66a7`,
  and `ee5f32f`. They define default-retain behavior, receipt and SHA-256
  binding, storage-rooted deletion, crash recovery, server-side environment
  gates, and the A1-A12 adversarial matrix. These are specifications, not an
  implementation or deployment claim.
- **LOCAL / VERIFIED 2026-08-02:** the current isolated sender candidate is
  commit `96d57de` on `codex/genbox-p5-resume-worker`. It includes shared
  cleanup/settings coordination, final destination and policy rechecks,
  platform-specific exact-delete primitives, duplicate-receipt rejection,
  bounded streamed receipt parsing, durable crash-intent recovery, a real
  FastAPI lifespan recovery test, and a real local chunked slow-drip Push test.
  The sender full suites pass `121` Windows tests with `10` platform skips and
  `130` Linux tests with one platform skip.
- **LOCAL / VERIFIED 2026-08-04:** sender commit `1463c69` closes the A7
  recovery-audit failure: a recovery audit `OSError` now persists a terminal
  `delete_unknown` record rather than leaving `deleting`; the actual FastAPI
  lifespan regression test proves startup completes without deleting the
  retained source. A clean worktree at that exact commit passes `131 passed,
  17 skipped, 10 subtests passed` on Windows and `147 passed, 1 skipped, 10
  subtests passed` in a clean Linux Docker container. No remote command ran.
- **LOCAL / VERIFIED 2026-08-04:** sender commit `9e475cb` closes the A4
  Windows hard-link race. Immediately before deletion it re-hashes the opened
  source and rechecks both handle and path identity plus link count. A real
  Windows thread adds a hard link after the earlier identity check; cleanup
  returns `retained / path-alias` and both source names retain identical bytes.
  The fixed commit passes `132 passed, 17 skipped, 10 subtests passed` on
  Windows and `147 passed, 2 skipped, 10 subtests passed` in a clean Linux
  Docker container. No remote command ran.
- **LOCAL / VERIFIED 2026-08-04:** sender commit `bd9ec81` fixes the explicit
  attestation-path fallback and passes `138 passed, 17 skipped, 9 subtests` on
  Windows plus `153 passed, 2 skipped, 9 subtests` in a clean Linux container.
  The independent A9 review nevertheless returns `BLOCK`: the application
  self-issues its attestation from environment claims, so it does not prove the
  actual Compose/container/image identity. No `33010` or `33018` connection,
  execute marker, or cleanup operation was used.
- **LOCAL / VERIFIED 2026-08-04:** sender commit `5d1b9cd` replaces in-process
  capability/attestation issuance with a host-only Ed25519 signing launcher.
  Startup now requires externally mounted capability, signed-attestation, and
  public-key files; it reads and verifies them but never writes or regenerates
  them. Missing, replayed, expired, tampered, aliased, or runtime-binding-
  mismatched artifacts fail closed. Windows full verification passes `141
  passed, 17 skipped, 9 subtests`; a clean, no-network, read-only Linux
  container passes `55` cleanup-security tests. Browser requests remain
  intent-only. A macOS CI job is configured but has no runner result yet, and
  a fresh independent A9 review is still required. No remote command ran.
- **LOCAL / VERIFIED 2026-08-04:** sender commit `c8a4b01` closes the follow-up
  A9 runtime-launcher gaps. Linux cgroup-v1 now accepts repeated copies of one
  container ID while rejecting different, missing, or malformed IDs. The
  host-only launcher requires an exact immutable repository digest, obtains and
  re-checks Docker's actual container ID before issuing artifacts, derives the
  public key outside the image, mounts only public artifacts read-only, and
  rejects a private key under either application-mounted host tree. It also
  rejects a same-hash digest from another repository. Windows focused sender
  security tests pass `59 passed, 5 skipped`; a no-network, read-only Linux
  container passes `64 passed`. A local Docker image build confirms neither
  host-only issuer nor launcher is in the application image. A fresh
  independent A9 code review returned `PASS`; macOS remains `UNVERIFIED` until
  an actual GitHub runner result exists. No remote command ran.
- **SECURITY GATE / BLOCKED 2026-08-04:** destructive cleanup and release
  approval remain blocked. A7's recovery-audit failure is fixed and locally
  verified on `1463c69`; A4's Windows final identity/hard-link protection is
  locally verified on `9e475cb`; A9 is blocked on `bd9ec81` until an external
  trusted launcher or host-owned signed deployment record replaces in-process
  self-attestation. The
  isolated runtime continues to fail closed as `unknown` with execute
  unavailable; positive per-item ownership, Compose/image/storage binding, and
  an authorized isolated execute/recovery exercise have not been proved.
  Current evidence also confirms matching receipt/source SHA-256, idempotent
  retry, source retention, and no connection or mutation request to production
  `33018`. Cleanup execution remains prohibited until review returns `PASS` and
  the user separately authorizes the bounded isolated test.
- **RELEASE BOUNDARY / VERIFIED 2026-08-02:** sender commit `96d57de` is pushed
  to the owner's experimental branch, but its immutable image has not been
  built or applied. Isolated sender `33010` remains on the previously reviewed
  `f0d5beb` image. This is development evidence, not authorization for source
  deletion, a stable GenBox release, or upstream delivery.
- **FINAL-GATE HANDOFF:** local code, Docker, build, smoke, receipt, retention,
  and fail-closed cleanup evidence is recorded. Exact-SHA hosted CI/macOS,
  isolated-VPS authority, destructive cleanup, human UAT, clean redeployment,
  Phase 7, G-Store execution, and Release remain external or blocked. Do not
  connect to `33018` or enable cleanup without a new explicit authorization.

## Current evidence

- **GITHUB + GHCR + ISOLATED-VPS 2026-08-01:** the experimental sender branch
  codex/genbox-p5-resume-worker is published in the owner's experimental
  repository at commit ca6f1ba. The corresponding GHCR package is pinned by
  immutable digest
  ghcr.io/liwei9745/chatgpt2api-genbox-p5@sha256:da5c8200b39833e5a9b2c74be72480bc772608711f0543a423fd49d4d18cd77d
  and was the image applied to the registered isolated sender on service port
  33010. The separately registered 33018 instance and production systems
  were not selected or modified.

- **ISOLATED-VPS 2026-08-01:** the Phase 5 batch, failed-only retry,
  concurrent schedule lease, and late-arriving image checks all have direct
  evidence in docs/PHASE5-EVIDENCE-2026-08-01.md. Five source images were
  retained, and the normal private receiver route was restored after testing.

- **LOCAL 2026-08-01:** the GenBox full test suite passed 582; the reviewed
  Phase 5 evidence, roadmap, and integration capability matrix were committed
  as 5baa2fb and pushed to the current experimental GenBox branch. A clean
  GitHub-clone rebuild and deployment remain a separate release gate.
- **LOCAL 2026-08-01:** the deployment image field now includes a bilingual
  `Check GenBox integration` action and a compact image-option menu. The
  reviewed GenBox image stays read-only; only the custom option unlocks manual
  digest entry. It validates the immutable digest against the local
  reviewed-image capability catalog only: the current GenBox sender preset
  reports `genbox-push-v1`; the pinned `yukkcat` upstream digest is selectable
  but reports `not_integrated`, leaving the deployment decision to the user.
  An unregistered custom digest is explicitly `unknown`, never presented as
  integrated. The action does not contact a VPS,
  registry, Docker daemon, or image runtime. Focused extension and image
  capability tests passed `213`; Python compilation, JavaScript syntax, and
  diff checks passed. This is local UI and route evidence only.

- **LOCAL 2026-07-31:** the deployment form now presents three image-source
  choices in beginner-friendly order: the verified GenBox integration build is
  selected by default, the upstream image remains visible but disabled until
  its integration PR is merged, and a custom immutable digest can be entered
  manually. The project choice locks the digest field while the custom choice
  clears and unlocks it; both languages have matching labels and status text.
  Extension and managed-image tests passed `208`, `node --check
  static/js/extensions.js`, and `git diff --check`. This is local UI evidence
  only; no VPS or production instance was changed.

- **GITHUB + ISOLATED-VPS 2026-07-31:** sender commits `9e80af3` and
  `efae62f` were published from the owner's experimental repository. The final
  immutable image digest `sha256:c9357b45b1339d2be4e4a02eb48f059562890f14bd9757b924d7fd7621b9e076`
  was applied only to the registered isolated sender through GenBox's controlled
  update path; pull, rebuild, and health verification completed successfully.
  No production instance was selected or modified.

- **ISOLATED-VPS 2026-07-31:** after starting a two-image Gallery batch and
  reloading the sender page, the durable progress dialog reappeared from the
  server-side batch projection while selection reset to zero. This confirms
  browser-refresh recovery. A later one-image duplicate Push remained in
  `sending` beyond the bounded observation window, then disappeared from the
  recoverable projection after its dialog was closed. The current UI has no
  terminal batch-history view, so the final result cannot be observed safely.
  This run is not accepted as a completed idempotent-retry result; terminal
  batch history and the delayed-transfer diagnosis remain blockers for Phase 5
  acceptance.

- **LOCAL 2026-07-31:** the sender now exposes a recoverable-batch projection,
  persists distinct `already-imported` item outcomes, and displays a
  compatibility-safe progress count. Focused sender tests passed `13` and the
  Vue production build passed. Cross-process batch locking and bounded retry
  policy are not yet present in the current sender branch and remain follow-up
  work; do not treat earlier planning text as implementation evidence.

- **LOCAL 2026-08-01:** target-mode parallel review completed in the isolated
  `E:\AI\chatgpt2api-dev` sender checkout. Commit `c7367dc` preserves
  `duplicate-local` receipts as distinct `already-imported` batch outcomes and
  safely handles legacy or malformed retry timestamps. The sender branch
  already contains latest-recoverable hydration, cross-process item claiming,
  bounded retry/backoff, and failure classification. Focused batch, transfer,
  service, and API tests passed `35`; the Vue production build and diff checks
  passed. This is local sender evidence only; no VPS or production instance
  was changed, and isolated Phase 5 acceptance remains pending.

- **LOCAL 2026-08-01:** the next target-mode fix wave closed the P1 outbox
  claim race. Sender commits `dbd661d` and `b9293aa` add a process-shared state
  lock plus a per-entry lock held through transfer completion, recover only
  stale `sending` entries whose claim lock is free, and preserve duplicate
  receipts as `already-imported`. The schedule projection now exposes the same
  duplicate count, and Gallery polling ignores stale or overlapping responses.
  Sender full tests passed `63`; Phase 5 focused tests passed `49`; the Vue
  production build, compile checks, and diff checks passed. A GenBox offline
  control-script compatibility fix was verified with the full GenBox suite:
  `582 passed`. All evidence is local; no VPS or production instance changed.

- **LOCAL + GITHUB 2026-08-01:** the sender branch
  `experimental/codex/genbox-p5-batch-recovery` was pushed to the owner's
  experimental repository after the local test and secret scan. The amd64
  workflow run `30682843048` completed successfully and published the
  immutable experimental image
  `ghcr.io/liwei9745/chatgpt2api-genbox-p5@sha256:3c812bc385b8d911e54183a27a926cef729fc6911fb29e6da64f3582ab2795cf`.
  This digest is a candidate for the isolated sender only; no VPS update has
  been performed from it yet, and production remains unchanged.

- **LOCAL 2026-08-01:** Docker pulled the published image by its full digest
  and reported the same `sha256:3c812bc385b8d911e54183a27a926cef729fc6911fb29e6da64f3582ab2795cf`.
  The GenBox Extensions page shows two registered managed chatgpt2api cards,
  while the local credential vault is locked and therefore keeps both remote
  `Update image` actions disabled. No direct SSH fallback was used. The next
  remote step requires unlocking the local vault, then generating and
  explicitly confirming the bounded update plan for the intended isolated
  instance; production remains untouched.

- **LOCAL + ISOLATED-VPS 2026-07-31:** fixed the managed-service drawer so
  opaque instance handles containing quotes cannot leave the visible `Update
  image` or key-reset actions inert. After each render, the card's encoded
  handle is rebound from its `data-instance-handle` attribute and the malformed
  inline handler is removed. `node --check static/js/extensions.js`,
  `git diff --check`, `python -m pytest -q tests/test_extensions.py` (`202`
  passed), and the focused cross-module suite (`365` passed) succeeded. The
  local development lab was then safely restarted from the current source and
  rendered both managed sender cards without browser errors. The controlled
  remote-update/restart action remains intentionally unavailable until the
  user unlocks the per-instance local credential vault; no direct SSH fallback
  will be used.

- **ISOLATED-VPS 2026-07-31:** an authorized manual scheduled scan was run
  again through the sender Settings UI. It completed with `3` completed, `0`
  waiting, and `0` failed items, with source-image retention still enabled.
  This is an operational health check only and does not replace the remaining
  controlled interruption-recovery or independent-worker lease evidence.

- **ISOLATED-VPS 2026-07-31:** a baseline manual incremental scan completed
  with `2` completed items and no queued or failed items. One newly generated,
  development-only test image was then added within the same scan range. The
  next overlapping manual scan first reported `2` completed and `1` queued,
  then converged to `3` completed, `0` queued, and `0` failed, with all source
  images retained. This verifies late-arriving source discovery on the
  isolated sender without production mutation.

- **ISOLATED-VPS 2026-07-31:** two independently loaded, authenticated
  Settings pages clicked the bounded `run now` UI control concurrently. Both
  requests completed before a visible lease conflict could occur because the
  three-item scan was too short. This is not concurrency-lease acceptance
  evidence; the remaining live check needs an intentionally overlapping scan
  or independent worker process. Cross-process lease protection remains
  locally covered by focused sender tests.

- **ISOLATED-VPS 2026-07-31:** Gallery's visible failed-only retry control
  retried one previously failed item without resubmitting any other item. Its
  terminal receipt projection was `already-imported`, and the page confirmed
  that the source image remained retained. A subsequent two-item Gallery batch
  was started and the browser was refreshed immediately. The reloaded page
  restored that same batch and later reported `2` `already-imported` outcomes
  with source retention. This is user-visible browser-refresh recovery and
  idempotent completion evidence; it does not substitute for a sender-process
  interruption or an independent concurrent-schedule invocation.

- **ISOLATED-VPS 2026-07-31:** the registered isolated sender received the
  reviewed immutable Phase 5 image through the controlled update path. The
  updater accepted only its opaque instance handle and immutable digest, used
  the saved per-instance SSH credential internally, and completed the bounded
  pull, configuration backup, app recreation, and health-check operation. The
  local registration changed only after that health check; the other registered
  instance and all production systems remained unchanged. **Next evidence:**
  reload the sender Settings page and run one manual scheduled scan to verify
  the repaired batch-progress projection in the deployed browser.

- **USER-CONFIRMED ISOLATED-VPS 2026-07-31:** after the controlled image
  update, the sender Settings page's manual scheduled scan reported `2`
  completed, `0` waiting, and `0` failed items, with source images retained.
  This confirms the deployed schedule-progress refresh path; batch interruption
  recovery, late-file overlap discovery, and lease behavior remain to be
  exercised before Phase 5 can be accepted.

- **ISOLATED-VPS + GITHUB 2026-07-31:** a focused Gallery usability fix made
  both selected-image actions explicitly name GenBox as their destination. The
  experimental AMD64 workflow built and published a new immutable sender image,
  then the controlled updater replaced only the registered isolated sender and
  completed its health check. The user-facing batch behavior is unchanged;
  this removes ambiguity before the remaining interruption-resume test.

- **USER-CONFIRMED ISOLATED-VPS 2026-07-31:** the updated Gallery completed a
  manual two-image batch Push to GenBox, reporting `2` processed items and
  retaining both source images. This validates the visible manual-batch success
  path, but does not yet prove interruption recovery, late-file discovery,
  concurrent schedule lease behavior, failure-only retry, or the later clean
  redeployment and upstream-delivery gates.

- **LOCAL 2026-07-31:** the deployed-services drawer now shows non-secret
  instance metadata for disambiguation: VPS name and address, SSH port,
  service port, deployment time, and the local credential-save timestamp when
  available. The public projection remains allowlisted and excludes keys,
  passwords, paths, container IDs, and image configuration. Focused extension
  and vault tests passed `341`. The detail rows are now translated in both
  supported UI languages and collapsed by default; service-drawer loading is
  single-flight so repeated route/drawer refreshes do not duplicate controls.

- **LOCAL 2026-07-31:** GenBox now has a controlled update path for an
  already registered managed `chatgpt2api` isolated Compose instance. The
  browser supplies only an opaque instance handle and immutable image digest;
  a single-use five-minute plan is bound to those values. Application occurs
  only after the local credential vault is unlocked, verifies the isolated
  target role and remote ownership marker, pulls before changing `.env`, then
  recreates and health-checks the app. A failed write, start, or health check
  restores the prior configuration and recreates the prior app; the local
  instance image record changes only after health succeeds. The endpoint and
  UI never return saved SSH credentials. Focused GenBox extension suites passed
  `369`. The vault was later unlocked for a controlled-update preflight, which
  then stopped before SSH because its saved SSH credential belongs to a
  different managed isolated instance. The sender instance being verified has
  no locally saved SSH credential yet. Remote controlled update and
  schedule-progress verification therefore remain pending an explicit
  per-instance credential save; no production instance was selected or
  modified.

- **ISOLATED-VPS + LOCAL RECEIVER 2026-07-31:** the authorized isolated
  sender completed a two-item Gallery batch Push with source retention. A
  manual scheduled scan then created two recoverable items but the deployed
  Settings page continued to show its initial queued projection after the
  batches had been handed to the worker. The sender fix makes schedule reads
  refresh batch projections and adds bounded Settings-page polling; focused
  transfer, batch, and schedule tests passed `25`, and the Vue production build
  passed. A new immutable experimental sender image was published from the
  reviewed fix. The already-running isolated instance is still on the prior
  immutable image: remote verification of the fixed schedule progress display
  requires an approved controlled update or replacement deployment. No
  production instance was selected or modified.

- **ISOLATED-VPS + LOCAL RECEIVER 2026-07-31:** an authorized Gallery
  single-item Push initially showed a transient failure state, then recovered
  to a completed receipt with source retention. A second explicit Push of the
  same selected source completed without sender browser errors. The local
  receiver's remote-media thumbnail set was identical immediately before and
  after that retry, proving no duplicate media was created. This is a focused
  user-visible retry/idempotence check only; Phase 5 still requires isolated
  batch-interruption recovery and scheduled late-file discovery evidence. No
  production instance was selected or modified.

- **GITHUB + LOCAL 2026-07-31:** the owner's experimental sender repository
  published a dedicated immutable `linux/amd64` Phase 5 image package after
  correcting the repository workflow permission and package-ownership
  boundaries. The digest was pulled back from GHCR and passed the disposable
  Docker-only Push smoke, including idempotent retry, interrupted-batch
  recovery, scheduled late-file discovery, and source retention. This proves a
  sanitized GitHub-built sender artifact can run locally; it does not prove the
  isolated VPS architecture, deployment, batch interruption, or scheduled scan.

- **LOCAL 2026-07-31 (superseded wording):** the sender batch implementation
    now persists explicit `already-imported` outcomes and exposes the newest
    active or failed batch for Gallery refresh recovery. The current branch
    does not yet provide cross-process batch locking or bounded automatic retry
    policy; those are separate Phase 5 follow-ups. Local Docker smoke evidence
    remains distinct from isolated-VPS acceptance.

- **EVIDENCE LOCK 2026-07-30:** after the isolated sender/receiver verification,
  `python -m pytest -q tests/test_extensions.py tests/test_local_tailscale.py
  tests/test_sync_push_routes.py tests/test_extension_task_store.py` passed
  `365`; `node --check static/js/extensions.js` and `git diff --check` also
  passed. The reviewed diff contains only source, tests, and sanitized project
  documentation. The isolated Studio and Gallery success states supersede the
  earlier transient Gallery failure dialog; source retention and receiver-side
  idempotence remain the authoritative result. No production instance was
  selected or modified.

- **ISOLATED-VPS + LOCAL RECEIVER 2026-07-30:** a selected image from the
  authorized sender Studio generated a new image with “生成后推送到 GenBox”
  enabled. The Studio result first showed “已推送到 GenBox，源图已保留”. The
  same image was then selected in Gallery and pushed again; the sender retained
  the source and the Studio task remained successful after the retry. The
  receiver manifest gained exactly one new entry for this image and the
  repeated request did not create a third entry. This verifies the isolated
  browser Studio single-image Push, authenticated receipt, source retention,
  and idempotent retry. No production instance was selected or modified.

- **LOCAL + ISOLATED-VPS 2026-07-30:** the local Tailscale Serve recovery
  path now understands the current `Foreground` status shape. When its sole
  route is the GenBox-owned HTTP listener but targets a stale loopback port, it
  may reset and recreate only that one route; any unrelated route fails closed
  without mutation. After restarting the registered development lab, its
  private Serve entry was verified to target the current process and the
  loaded status endpoint reported the route healthy. Focused Tailscale,
  network-adapter, and extension tests passed `236`; the focused extension,
  route, and task-store suites then passed `364`.

  The isolated sender's saved destination passed its authenticated v1 readiness
  check. Its Gallery reported the selected generated image as complete with
  source retention enabled. The current GenBox development receiver contained
  one remote-imported media file and its durable manifest contained transfer
  records, confirming that the user-visible success state corresponds to a
  receiver-side import. This verification used only the authorized isolated
  sender and local development receiver; no production instance was selected
  or modified.

- **ISOLATED-VPS 2026-07-30:** an explicitly authorized development-only
  `chatgpt2api` instance was deployed from the published immutable sender
  image. Its directory, Compose project, management key, and GenBox Push
  source are distinct from the pre-existing managed instance. A stale local
  GenBox process behind the existing private Tailscale entry initially rejected
  the sender identity. The registered current GenBox lab was restarted and the
  existing private entry was redirected to that lab; the sender then completed
  an authenticated v1 probe.

  A user-created isolated test image completed a manual authenticated Push and
  then an identical manual retry. The sender validated the success receipt and
  retained the source image after both requests. A local receiver query
  immediately afterward returned exactly one media item, tagged as a remote
  sync import, proving that the retry did not duplicate the image. Source
  deletion remains disabled and no schedule was configured. No production
  instance was selected or mutated. The later evidence-lock result at the top
  completes Phase 4; Phase 5 has not started.

- **LOCAL 2026-07-30:** deployment-plan generation and final deployment
  authorization now use visible in-page confirmation cards instead of browser
  native confirmation dialogs. The cards explain the read-only preflight or
  the isolated deployment scope, keep cancellation on the reviewed page, and
  invoke the existing backend gates only after the user selects the explicit
  continue action. Backend `approve_plan_discovery`, host-key verification,
  immutable-image validation, and `confirmed_plan_id` requirements are
  unchanged. `node --check static/js/extensions.js`, `git diff --check`, and
  the focused extension/Push suites passed `363`. This was local UI/test
  evidence at the time recorded. The later isolated-VPS deployment and
  single-image Push verification is recorded at the top of this document.

- **LOCAL 2026-07-30:** the novice deployment guide now preserves an explicit
  path to plan a second isolated `chatgpt2api` instance after a prior managed
  deployment has completed. The new action clears only the browser's transient
  historical deployment and delivery state; it preserves the saved target and
  does not stop, replace, reconfigure, or send a request to the existing
  instance. It then returns the user to the credential-gated plan workflow.
  `python -m pytest -q tests/test_extensions.py` passed `201`; JavaScript
  syntax and whitespace checks passed. No credential was read or logged, and
  no SSH, VPS, container, network, or deployment action was submitted. This is
  `LOCAL` UI/test evidence only.
- **VERIFIED 2026-07-30:** the published immutable sender image
  `ghcr.io/liwei9745/chatgpt2api@sha256:6892af60bbb85db1963d43474e66d5551f1a0fd212cb88d658d8a3410c1dc9d0`
  was pulled by digest and used directly in the disposable local Push smoke
  against the clean-clone GenBox receiver image. The v1 probe, full final Push
  endpoint input, first import, idempotent retry, and source retention passed;
  the smoke resources were removed afterward. This verifies the published
  sender artifact locally, not a VPS pull, configuration, or isolated-VPS E2E.
- **LOCAL 2026-07-30:** a fresh, empty local clone of
  `liwei9745/GenBox:codex/p4-deploy-plan-ux-eai` resolved to `dea968c` with no
  working-tree changes. Its Dockerfile built a new receiver image using that
  clone as the only build context and `--pull=false`. Paired with the current
  sender image, the disposable internal-network smoke passed the v1 probe,
  full final Push endpoint normalization, first import, idempotent retry,
  metadata verification, and source retention. No runtime configuration, user
  data, image, credential, VPS, registry publication, or production instance
  was used. This is clean-source `LOCAL` evidence, not a clean isolated-VPS
  deployment or end-to-end user workflow acceptance.
- **VERIFIED 2026-07-30:** after a local sanitization review, the current
  GenBox Phase 4 branch was pushed to
  `liwei9745/GenBox:codex/p4-deploy-plan-ux-eai`; the current sender branch
  was pushed to both authorized experimental repositories as
  `codex/genbox-p4-sender-image`. Neither action updated a default branch.
  The sender's immutable GHCR image is the separately verified artifact below.
  A clean GenBox deployment from its pushed branch remains pending; the
  isolated-VPS single-image Push acceptance run is recorded at the top.
- **VERIFIED 2026-07-30:** the authorized experimental GHCR workflow completed
  successfully for sender commit `a4217e3` and published the immutable image
  index `ghcr.io/liwei9745/chatgpt2api@sha256:6892af60bbb85db1963d43474e66d5551f1a0fd212cb88d658d8a3410c1dc9d0`.
  A read-only manifest inspection confirmed `linux/amd64` and `linux/arm64`
  manifests. This is a registry artifact verified by the successful workflow
  and manifest query; it is not evidence that a VPS has pulled, configured, or
  run the image, and it does not complete isolated single-image Push E2E.
- **LOCAL 2026-07-30:** the sender repository built a current local image from
  its source with `--pull=false`, reusing already available base images and
  dependency layers. Its disposable Docker-only Push smoke harness then passed
  with the full final `/api/sync/push` address as the configured sender input.
  On one internal, unpublished network it generated a synthetic 2x2 PNG and
  test-only credentials, then verified the v1 probe, first import, idempotent
  retry, concurrent-transfer coordination, interrupted-batch recovery,
  receiver SHA-256 metadata, and source retention. The harness removed its
  per-run labeled containers and network afterward. No user image, credential,
  VPS, SSH, production container, registry pull, publication, or deployment
  was used. This is `LOCAL` current-image protocol evidence only, not
  `ISOLATED-VPS` or full user-workflow acceptance evidence.
- **LOCAL 2026-07-30:** the final private-network completion view now makes
  the chatgpt2api login handoff explicit for new users. It pre-fills the
  one-time management key delivered in the current page, labels that state,
  supports an intentional refill from that same delivery, and permits a manual
  replacement key. The shortcut copies the submitted value, opens the
  non-secret private console URL in a separate tab, then clears both page
  inputs and disables the delivery refill. It writes neither key to browser
  storage nor to a URL or backend endpoint. The delivery key cannot be
  recovered after refresh or clearing; the user must manually paste it or use
  the existing ownership-verified rotation flow. `tests/test_extensions.py`
  passed `200`; JavaScript syntax and diff whitespace checks passed. A
  loopback request returned the current static bundle reference. No browser
  target was selected, no credential was entered, and no SSH, VPS, container,
  sender, deployment, or network action was submitted. This is `LOCAL` UI/test
  evidence only.
- **LOCAL 2026-07-30:** GenBox now provisions a dedicated Push source for one
  registered, managed `chatgpt2api` instance after its private destination is
  verified. The browser submits only an opaque instance handle; the backend
  resolves the saved target, instance, and destination. The local registry
  atomically persists only an active flag, timestamps, random salt, and
  PBKDF2-HMAC-SHA256 verifier. Raw Push keys are returned only by explicit
  create or rotate actions, never by status/listing; revoke retains a tombstone
  that blocks fallback to a same-named legacy `GENBOX_PUSH_KEYS` entry. The
  final Extensions step shows the non-secret destination and source ID, offers
  create/copy/rotate/revoke actions, clears the one-time key after the explicit
  copy action, and uses neither browser storage nor key-bearing URLs. Focused
  receiver, route, DOM, and task-store suites passed `378`; Python compilation,
  JavaScript syntax, and whitespace checks passed. A fresh loopback server
  returned the current Extensions bundle and static page containing the Push
  panel. No browser target was selected, no credential was entered, and no SSH,
  VPS, container, sender, deployment, or network action was submitted. This is
  `LOCAL` receiver/UI evidence only. The later sender configuration and
  isolated single-image Push E2E verification is recorded at the top.
- **LOCAL 2026-07-30:** the final private-network completion screen now offers
  a console-login helper for the exact managed instance. It pre-fills a
  one-time management key only while that value remains in the current page;
  after a refresh, the user can enter a replacement key manually. An explicit
  action copies the key, opens the private console in a separate tab, then
  clears the helper input. The key is never appended to a URL, sent to a new
  backend endpoint, or persisted in browser storage. The console address may
  be recovered only by matching the existing opaque managed-instance handle to
  public instance metadata. Focused extension suites passed `325`; full local
  `python -m pytest -q` passed `553`; JavaScript syntax, whitespace, and
  loopback static-resource checks passed. No browser target was selected, no
  credential was entered, and no SSH, VPS, container, deployment, or network
  action was submitted. This is `LOCAL` UI/test evidence only.
- **LOCAL 2026-07-30:** a VPS-network task that stops for user input now keeps
  its recovery card actionable in novice mode. The visible recovery button
  directs a missing session credential to the SSH password/private-key field;
  after a session credential is present, it directs the user to the Tailscale
  Auth Key field, then changes to an explicit retry action once the key is
  entered. Filling a field alone never submits a network request.
  The Extensions bundle query version was advanced so a reload receives this
  behavior. Focused extension suites passed `324`; full local
  `python -m pytest -q` passed `552`; JavaScript syntax and whitespace checks
  passed. No browser target was selected, no credential was entered, and no
  SSH, VPS, container, deployment, or network action was submitted. This is
  `LOCAL` UI/test evidence only.
- **LOCAL 2026-07-29:** closing the reviewed safety-plan step now requires one
  final browser confirmation immediately before the deployment request can be
  sent. Cancelling, or a browser that cannot present that confirmation, keeps
  the reviewed plan visible, leaves its deploy action available, and sends no
  deployment request; it does not repeat SSH pairing, credential entry, or
  read-only discovery. Existing plan-expiry, exact-attempt, and reconciliation
  tests explicitly model confirmed browser intent. Focused extension suites
  passed `323`; full local `python -m pytest -q` passed `549`; JavaScript
  syntax and whitespace checks passed. No browser target was selected, no
  credential was entered, and no SSH, VPS, container, plan, deployment, or
  network request was submitted. This is `LOCAL` evidence only.
- **LOCAL 2026-07-29:** bounded the two fixed read-only checks that run only
  after the user explicitly approves safety-plan generation. The backend now
  cancels either stalled preflight and returns a sanitized, retry-safe
  `plan_discovery_timeout`; the browser independently aborts an unresponsive
  plan request, hides any plan preview, keeps deployment disabled, and tells
  the user that host-key confirmation is not required again. Focused route and
  UI regressions cover both backend preflight positions, browser abortion, and
  safe retry state. `python -m pytest -q` passed `548`; JavaScript syntax,
  Python compilation, and whitespace checks passed. No browser target was
  selected, no credential was entered, and no SSH, VPS, container, plan,
  deployment, or network request was submitted. This is `LOCAL` evidence only.
- **LOCAL 2026-07-29:** safety-plan generation now requires a separate,
  explicit browser confirmation before it performs its two fixed plan-preflight
  read-only checks. Without `approve_plan_discovery=true`, the backend returns
  a recoverable rejection before invoking any environment discovery. The UI
  first validates the local deployment-image input, then explains that the
  approved checks only examine port, directory, and isolation conditions and
  cannot deploy, pull an image, or alter services. A cancelled or unavailable
  confirmation sends no plan request. The approval marker is intentionally
  excluded from the plan-change snapshot, preventing a valid response from
  being discarded as stale. Focused extension suites passed `355`; full local
  `python -m pytest -q` passed `547`; Python compilation, JavaScript syntax,
  and whitespace checks passed. A fresh loopback-only runtime on port `8900`
  loaded `#/extensions` with no console errors and no horizontal overflow at
  `390x844`; no target was selected, no credential was entered, and no SSH,
  VPS, container, discovery, plan, deployment, or network action was
  submitted. This is `LOCAL` UI/API/test evidence only. A previously generated
  user-visible plan predates this guard and is not evidence that the new
  explicit-preflight interaction ran.
- **VERIFIED 2026-07-29:** the user-authorized experimental GHCR sender-image
  publication was queried by immutable digest. Its OCI index exposes both
  `linux/amd64` and `linux/arm64`; its public package metadata identifies the
  corresponding immutable release tag. The locally reviewed sender application
  and Docker build inputs match the published source tree; only publishing
  workflow text differs. The sender workflow's focused image-delivery tests
  passed locally. This verifies a registry artifact for plan input, not a VPS
  pull, deployment, private-route, transfer, or production result.
- **USER-CONFIRMED 2026-07-29:** the user completed the authorized single
  host-key-verified L2 read-only environment check in the local Extensions
  page. The visible result advanced to deployment-option review and stated that
  no deployment had started. No host identity, credential, raw terminal output,
  fingerprint, or VPS address was retained in this record. This is a
  user-visible completion report, not independent `ISOLATED-VPS` verification
  or deployment evidence. The next prerequisite before a safety plan is an
  immutable, server-pullable image digest; no image, plan, or deployment has
  been submitted from this evidence.
- **LOCAL 2026-07-29:** bounded the authorized L2 read-only environment
  discovery so a stalled SSH/Docker read cannot leave the browser indefinitely
  in a loading state. The backend cancels discovery after 45 seconds and
  returns a sanitized timeout diagnostic that does not require host-key
  reconfirmation. The browser aborts an unresponsive request after 65 seconds,
  restores the one read-only-check action, and gives a retry path without
  starting pairing, an SSH deployment diagnostic, plan generation, or
  deployment. Focused route/DOM regressions cover cancellation, secret-free
  error content, request abortion, and restored controls. Python compilation,
  JavaScript syntax checks, diff whitespace checks, and the full local pytest
  suite passed `545`. A fresh loopback-only Lab loaded the committed runtime
  identity and rendered `#/extensions` with no browser-console errors; no
  target was selected and no credential or remote request was submitted. No
  SSH, VPS, remote container, deployment, network, or production action was
  performed. This is `LOCAL` evidence only.
- **LOCAL 2026-07-29:** launched a fresh loopback-only Lab for the current
  worktree and verified its runtime identity reports commit `fe6a3c4` and the
  manual-current-worktree source. Browser inspection confirmed that its visible
  credential action invokes read-only discovery and the advanced deployment
  disclosure starts closed. No target was selected, no credential was submitted,
  and no SSH, VPS, container, deployment, or network request was made. This is
  `LOCAL` runtime/browser evidence only.
- **LOCAL 2026-07-29:** narrowed the L2 credential surface for the one
  host-key-verified read-only environment check. The primary credential action
  and guide both invoke discovery rather than the deployment diagnostic. Sudo
  choices are collapsed under an advanced deployment-only disclosure, and the
  discovery request defensively replaces any stale or accidentally entered
  elevation fields with `none` and empty sudo data. This does not remove the
  separate advanced diagnostic needed before a later deployment. Focused DOM
  regression tests prove that simulated sudo input is absent from the discovery
  request; the full local pytest suite passed `543`; and a local browser check
  confirmed the disclosure is closed by default and the primary action remains
  `Run read-only check`. No target was selected, no credential was submitted,
  and no SSH, VPS, container, deployment, or network request was made. This is
  `LOCAL` evidence only.
- **LOCAL 2026-07-29:** simplified the personal-server path so the credential
  view's primary action now runs the one bounded, host-key-verified read-only
  environment discovery directly. It no longer requires the separate SSH
  deployment-access diagnostic first, so an authorized discovery cannot loop
  through credentials and deployment checks. The guarded discovery uses no
  `sudo`; it advances to the public environment result and only marks deploy
  access verified when the read-only result proves it. A result without deploy
  access remains visible and offers the existing deployment diagnostic as an
  optional later action, without restarting pairing or re-reading the target.
  Node syntax checks, focused UI/route tests, and full local pytest recorded
  `543` tests with `0` failures and `0` errors. No SSH, VPS, remote-container,
  deployment, network, or production operation was performed. This is `LOCAL`
  evidence only.
- **LOCAL 2026-07-29:** browser-checked the current local Lab on a separate
  loopback port. The visible credential-panel primary action says `Run
  read-only check` and invokes only the bounded discovery route, matching the
  novice guide. No target was selected, no credential was submitted, and no SSH
  or VPS request was made during this browser check.
- **LOCAL 2026-07-29:** closed the gap between the L2 read-only discovery
  approval plan and the SSH command executor. The discovery route now passes
  its request-scoped validated plan into a command guard. Every SSH command is
  mapped to an explicit approved operation before it is sent; current session
  user, OS, CPU, memory, home-directory, runtime, Docker/Compose, listener,
  capacity, and derived container-metadata reads are separately named. Unknown
  command drift is rejected locally before SSH execution. A successful
  approved Docker listing may derive only validated per-container summary,
  mount, ownership-label, and mount-derived directory-size operations. The
  guarded L2 path does not use `sudo` and does not read image digests. Existing
  non-L2 planning behavior remains unchanged. Focused discovery/plan tests
  passed `230`; full local pytest recorded `543` tests with `0` failures and
  `0` errors; Python compile, Node syntax, and diff whitespace checks passed.
  No SSH, VPS, remote-container, deployment, network, or production operation
  was performed. This is `LOCAL` evidence only. The next L2 entry condition is
  the user's browser submission of the temporary SSH credential against the
  already confirmed isolated-development target, followed by exactly one
  guarded read-only discovery request.
- **LOCAL 2026-07-29:** fixed the host-identity-change recovery loop in the
  Extensions onboarding. A mismatch now clears only the browser's session
  credentials and enters a dedicated recovery view; it cannot start another
  pairing, manual probe, or discovery until the user explicitly confirms a
  local reset. The reset API accepts only a saved target ID, atomically clears
  its canonical host-key trust and stale network-verification state, increments
  its identity generation to invalidate unfinished pairing challenges, and
  never contacts the host, receives a credential, or accepts a replacement
  identity. The user must then manually begin a fresh confirmation.
  Store/route/DOM regression coverage passed, including cancelled reset,
  minimal request payload, stale-challenge rejection, and no browser-storage or
  credential disclosure. `node --check` passed for both extension bundles,
  Python compilation passed, `git diff --check` passed, and full local pytest
  passed `541`. A launcher-owned Lab at `http://127.0.0.1:8895/#/extensions`
  served the current source with the reset route present and zero browser
  console errors; no target metadata, credential, host-key probe, SSH test,
  discovery, deployment, or remote command was submitted. This is local
  UI/API/test evidence only, not isolated-VPS, SSH, container, deployment, or
  production evidence. The pre-existing `8892` runtime did not expose this
  route and was left running unchanged.
- **LOCAL 2026-07-29:** added a fail-closed L2 read-only discovery-plan gate.
  `scripts/validate_discovery_plan.py` accepts only a secret-free,
  target-bound `read-only-discovery` authorization, matching expected/observed
  canonical SSH host-key identity, and fixed allowlisted operations. It rejects
  arbitrary shell text, target or host-key drift, unknown labels, unsafe
  container identifiers, and non-canonical paths. Its output names only an
  approved scope/role and operation identifiers, or an invalid field; it does
  not echo host identities, fingerprints, paths, or credentials. Focused plan
  and extension tests passed `199`; the full local pytest suite, Python compile
  check, and diff whitespace check passed. This is local validation tooling,
  not SSH, VPS, container, discovery, deployment, private-network, or
  production evidence.
- **LOCAL 2026-07-29:** the Extensions environment-discovery route now creates
  a request-scoped L2 approval record, re-reads the saved target's SSH host key
  without authentication, and validates the fixed read-only plan before it
  supplies the session credential to the existing discovery code. A changed
  host key or rejected plan stops before discovery. The record is never
  persisted, returned to the browser, or written to task/instance state.
  Focused plan and extension tests passed `203`. This route coverage uses
  mocks only; no SSH, VPS, container, deployment, private-network, or
  production action was performed.
- **LOCAL 2026-07-29 browser verification:** an independently launched,
  launcher-owned Lab loaded commit `e493fcc` and served `#/extensions` with
  the Extensions page visible and zero browser-console errors. The runtime
  identity matched that commit. No target metadata, pairing material,
  credential, SSH test, host-key probe, environment discovery, deployment, or
  network request was submitted. This is browser startup evidence only, not
  isolated-VPS or production evidence.
- **VERIFIED 2026-07-23:** GenBox commits `997e78c`, `5394c42`, and `72edab0`
  locally implement the novice-oriented trusted SSH-session pairing path on top of
  Deployment Safety Contract v3. The saved trust record remains the canonical
  SSH host-key algorithm plus `SHA256:` fingerprint pair; pairing does not
  replace SSH credentials or mandatory host-key verification.
- **VERIFIED 2026-07-23:** focused and full local verification completed with
  `501 passed`. Independent fixed-commit architecture, security, and regression
  reviews each returned **APPROVE**. This is local evidence only.
- **VERIFIED 2026-07-23:** local Docker preflight succeeded from image
  `genbox-p4-local:dae8d84`
  (`sha256:62120b3124bf05c5eff4b85f7211804804bbcf617258460bbc8bc4aebe17680`).
  The isolated container was exposed only on `127.0.0.1:18991`, passed its
  Docker healthcheck, and returned `/api/setup/status` with production
  authentication enabled. A temporary 1x1 PNG Push returned `imported`; the
  identical retry returned `already-imported` with the same SHA-256. This proves
  local receiver build/startup, authenticated Push, and idempotency only; it is
  not VPS, private-network, browser, sender, or production evidence.
- **VERIFIED 2026-07-22:** chatgpt2api sender implementation exists at
  `f4a327d5599b020c66d4aab041a5fa0035d5effe`. Its existence does not prove the
  GenBox receiver/deployment candidate or an end-to-end transfer.
- **UNVERIFIED:** a real isolated-VPS, browser-driven, single-image Push end to
  end. No local/mock test, status panel, plan, or sender commit substitutes for
  an authenticated receipt, matching SHA-256, metadata result, idempotent retry,
  source-retention result, and production non-mutation check.
- **VERIFIED 2026-07-23:** production chatgpt2api remains outside the mutation
  scope. Host, port, container, and credential facts are intentionally absent
  without fresh dated discovery evidence.
- **USER-CONFIRMED / BLOCKED 2026-07-27 (L2):** the user identified the selected
  target as an isolated development machine and authorized a bounded
  `read-only-discovery` SSH check. The local client established SSH transport,
  but the server closed the session before current host-key validation or user
  authentication. No discovery command, container action, deployment, or
  mutation ran. This does not prove the current host identity, isolation,
  ownership, Docker/Compose state, ports, mounts, capacity, or health. L2
  remains blocked pending an SSH service/policy correction on the isolated
  development machine and a fresh host-key validation.
- **LOCAL 2026-07-27:** GenBox now classifies an SSH session closed by the server
  separately from authentication rejection and protocol negotiation failure.
  The UI instructs the user to keep the current identity and credential views;
  it does not send the user back to pairing or request another confirmation
  code. Focused extension suites passed `178` and `119` tests; the full local
  suite passed `511`. No target identifiers, fingerprints, credentials, or raw
  SSH errors are stored in this record.
- **LOCAL 2026-07-27:** the prior transport-close result was traced to an RSA
  host-key negotiation mismatch in GenBox. The saved canonical `ssh-rsa` key
  type and SHA-256 fingerprint remain mandatory, while the SSH client now
  negotiates that same RSA key through `rsa-sha2-512` or `rsa-sha2-256`.
  A real local AsyncSSH RSA server passed password authentication and exact
  fingerprint verification. This is not isolated-VPS proof; the next user-run
  connection check is still required before L2 discovery can begin.
- **LOCAL 2026-07-27:** duplicate saved-target recovery now reuses an existing
  normalized SSH endpoint on browser metadata save and shows one canonical
  record per endpoint in the beginner UI without deleting or replacing stored
  host trust. The deployment form now withholds instance name, service port,
  and image until the read-only environment check returns. The Step 2 transition
  now restores the one-action guide, so a successful SSH check exposes the
  read-only environment check instead of a blank waiting state. Focused
  extension tests passed `183`; the full local suite passed `516`; local
  browser verification at `http://127.0.0.1:8892/#/extensions` confirmed those
  three fields were hidden before discovery. No pairing, credential submission,
  SSH, VPS, remote container, production, or deployment operation was
  performed.
- **LOCAL 2026-07-29:** an isolated empty deployment now requires an immutable
  OCI image reference in the form `registry/name@sha256:<64 hex digest>` before
  GenBox starts environment discovery. The browser leaves the image value empty
  and explains that a local Docker tag or `latest` cannot be pulled by another
  machine. The API repeats the same check before SSH discovery, while existing
  instance registration and source-clone workflows retain their supported paths.
  This prevents a plan that is guaranteed to fail because the specialized sender
  image exists only on the developer machine.
- **Verification:** extension-focused tests passed `342`; the full local suite
  passed `520`; `node --check static/js/extensions.js`, `node --check
  static/js/i18n.js`, and `git diff --check` passed. The current-worktree local
  service at port `8894` returned HTTP 200 and served the empty image field plus
  its digest help. Prior local browser inspection of that same current-worktree
  page confirmed the field, accessible help linkage, Chinese copy, and zero
  browser console errors. This is `LOCAL` UI/API evidence only: no registry
  artifact was published, and no SSH, VPS, remote container, deployment, or
  production action was performed.
- **Next local entry:** define a reproducible, sanitized delivery path for the
  specialized sender image. Before building or publishing that artifact, resolve
  the sender-side transfer-coordination findings: configuration-version cache
  invalidation, metadata-conflict handling, and canonical path identity.
- **LOCAL 2026-07-29 sender image preflight:** the current sender revision was
  rebuilt from its repository Dockerfile with locally cached base images, then
  exercised with the disposable Docker-only sender/receiver smoke harness. The
  synthetic first Push imported once, the identical retry was idempotent, and
  the sender retained its source file. The harness published no ports and
  removed its labeled temporary resources. This is not a registry artifact,
  clean-machine build, isolated-VPS, private-network, or production result.
- **LOCAL 2026-07-29 image prerequisite guidance:** after a read-only
  environment check, an isolated empty deployment without an immutable image
  reference now directs the beginner to the image field instead of offering a
  plan action that will fail. The focus action performs no request. Focused
  extension tests passed `187`, and the full GenBox suite passed `520`. This is
  local UI evidence only and involved no registry, SSH, VPS, or deployment.
- **VERIFIED 2026-07-29 GHCR artifact:** the experimental repository
  `liwei9745/chatgpt2api-genbox-p4` completed its explicit, manual-only
  GitHub Actions image publication run. GitHub Packages reports the published
  multi-architecture manifest reference as
  `ghcr.io/liwei9745/chatgpt2api@sha256:f3091475b298749e97e58051574850d63b9a63bf12b54cb74b468f5020a32c5a`.
  The human-readable `sha-c3cabf9` tag is build metadata only; GenBox must use
  the digest reference. This is registry artifact evidence, not SSH, VPS,
  remote-container, deployment, receiver, or end-to-end Push evidence.
- **LOCAL 2026-07-29 sender build-context containment:** the sender's
  `.dockerignore` now excludes local environment files, runtime configuration,
  data, generated media, logs, databases, and private-key file types before
  Docker receives the build context. Sender unittest discovery passed `47`; a
  new local Docker build completed with the protected paths excluded from its
  small build context. That rebuilt sender then passed the disposable local
  sender/receiver smoke: first import, idempotent retry, and source retention
  all succeeded without published ports. This is a local build/sanitization
  check only, not a clean deployment, VPS, or cross-project transfer result.
- **LOCAL 2026-07-29 digest acceptance regression:** a minimal DOM execution
  test now covers the actual front-end plan gate: a pinned GHCR reference is
  accepted, while a mutable `latest` tag shows the recovery message, moves focus
  to the image input, and makes no request. The backend independently rejects a
  mutable empty isolated deployment before SSH discovery. `python -m pytest -q
  tests/test_extensions.py` passed `188`; full local `python -m pytest -q`
  passed `521`; `node --check static/js/extensions.js`, `node --check
  static/js/i18n.js`, and `git diff --check` passed. The local extensions page
  at `http://127.0.0.1:8892/#/extensions` was inspected without submitting or
  changing any saved target, credential, plan, or connection. This is LOCAL
  UI/test evidence only.

## Phase 4 boundary

Phase 4 is not complete. Its acceptance is phase-scoped: one newly generated
image from an isolated development clone imports once with available metadata;
retry is idempotent; failure retains the source; relevant receiver and sender
tests pass. Batch/scheduling are Phase 5. Cleanup is Phase 6. Clean GitHub
redeployment and upstream/release publication are separate authority and
completion gates.

The receiver-only requirement-by-requirement evidence matrix is maintained in
`docs/P4-SINGLE-IMAGE-PUSH-LOCAL-EVIDENCE.md`. It explicitly separates LOCAL
receiver proof from sender, isolated-VPS, and production claims.

## Local sender per-generation workflow (2026-07-24)

- **Evidence class:** `LOCAL` only. After explicit user authorization, the
  separate dirty `chatgpt2api-dev` worktree was preserved and updated in place;
  no existing dirty changes were discarded.
- **Implementation:** Studio result cards now expose a per-image
  `Push to GenBox` action only when a local relative image path is available.
  The UI reports generation and transfer independently, locks the action while
  uploading, supports idempotent retry, and reports failure with source-retained
  recovery guidance. No API key, receipt body, or image bytes are rendered or
  persisted by the Studio state.
- **Protocol gate:** the sender sends `source_sha256`, requires receiver
  `contract_version: v1` and a positive `max_image_bytes` probe, and accepts a
  Push only when the v1 receipt SHA-256 matches the uploaded bytes.
- **Verification:** sender focused tests -> `12 passed`; sender local full
  pytest -> `12 passed`; `web-vue` `npm run build` passed; `git diff --check`
  passed. Tests use only local mocks and a test-only process environment value.
- **Browser:** local GenBox lab at `http://127.0.0.1:8892/#/extensions`
  loaded with title `GenBox`, zero page errors, and `scrollWidth=390` at a
  390px viewport. This is local page/responsive evidence only; no pairing,
  SSH, Push, or credential action was submitted.
- **Sender browser smoke:** local Vite at `127.0.0.1:5173` used only
  Playwright-routed mock API responses. A synthetic completed image exercised
  the per-generation button through pending, success, and retry/source-retained
  failure states; captured Push requests contained only the expected relative
  path, with zero page errors and `scrollWidth=430` at a 430px viewport.
  This remains LOCAL UI/mock evidence, not live cross-project E2E.
- **Boundary:** no SSH, VPS, remote container, production instance, network
  deployment, or live sender-to-GenBox request was performed. Sender changes
  are committed separately at `78135e1` and `0320b62`; this local evidence does
  not upgrade isolated VPS or cross-project E2E status.
- **Secret/data boundary review (2026-07-24):** `LOCAL` only. The sender's
  GenBox Push settings API continues to mask the Push key before returning
  settings, and the Studio stores only per-image UI status in page memory.
  The receiver accepts only source-scoped Push authentication and verifies the
  sender-provided SHA-256 against uploaded bytes. The review found that a
  transport exception could otherwise be copied into a retry receipt or batch
  result; sender commit `041a2ce` replaces those raw exception strings with
  fixed recovery messages while retaining safe HTTP status categories,
  idempotency, SHA-256 receipt validation, retry state, and source retention.
  Focused and full sender pytest each passed `14` with a test-only process
  value; `web-vue` production build and `git diff --check` passed. New tests
  assert synthetic sensitive exception fragments do not reach a receipt,
  batch response, or connection error. No image bytes, Push key, raw receipt,
  or live network request was used.

## Exact next step

For a local-only UI check, enter the verified immutable GHCR reference into the
isolated-deployment image field and confirm GenBox accepts the digest format.
Do not generate a remote plan or start a deployment from that check. The next
remote gate remains separately authorized isolated-development discovery and
host-key validation; do not treat the registry artifact or local UI/tests as
VPS or production verification.

## Phase 5 sender local batch and schedule work (2026-07-29)

- **Evidence class:** `LOCAL` only. The separate sender worktree now has a
  durable manual batch service for Gallery selections and server-indexed date
  range previews. Items persist only a relative path, SHA-256, status, attempt
  count, timestamps, and a fixed recovery message. Source images are retained;
  no cleanup path was added.
- **Scheduled local behavior:** the sender has a disabled-by-default weekly
  schedule with optional date bounds, an overlap scan cursor, a short durable
  worker lease protected by an atomic cross-process lock, and no more than three
  automatic retries for a failed scheduled item. All scheduled sends enter the
  existing batch service, and single-image, batch, and scheduled paths now share
  an in-process content-identity coordinator so matching in-flight
  `(relative_path, SHA-256, metadata)` requests share one physical send. A
  metadata conflict is surfaced for retry instead of being silently discarded.
  This is not
  isolated-VPS, private-network, receiver, or production evidence.
- **Verification:** `LOCAL` sender unittest discovery passed 43 tests on
  2026-07-29, including focused coordinator coverage for concurrent outbox and
  batch delivery, retry-after-failure, changed-source refusal, path aliases,
  metadata conflicts, secret-safe result handling, and a real scheduler plus
  manual-batch contention path. The Vue production build and `git diff --check`
  also passed.
  Tests use synthetic relative paths and in-memory image bytes only. No real
  VPS, SSH credential, Push key, or external network was used.
- **Local Docker smoke:** `LOCAL` only. The current sender revision built from
  the repository Dockerfile with cached local base images and an explicit tag.
  Its disposable internal-network harness passed the v1 probe, two concurrent
  matching synthetic requests with one physical sender call, first import,
  receiver idempotent retry, SHA-256 receipt, source retention, and recovery of
  a batch item persisted as `sending` after the receiver had already accepted
  its image. It published no ports and cleanup left no run-labeled containers,
  networks, or generated credential files. This is not a VPS, clean-machine,
  registry, or production verification.
- **Browser verification:** `LOCAL` mock only. A standalone standard-library
  mock API accepts one fixed test-only bearer value and serves fixed synthetic
  Gallery records without importing sender application code or reading `data/`,
  configuration, real media, or credentials. Through local Vite, browser checks
  completed login, multi-select, source-retention confirmation, batch progress,
  cancellation of queued items, failed-only retry, progress-panel close,
  date-range preview, weekly schedule save, and run-now feedback. At a narrow
  viewport, the inspected page width had no horizontal overflow. This is a UI
  contract check only: it does not prove a receiver, Docker, VPS, private
  network, real image, remote generation, or production behavior.
- **Next local entry:** retain this sender image and smoke harness as the local
  Phase 5 baseline. The next verification gate is a separately authorized
  isolated-VPS clone; keep Phase 5 marked planned until that evidence is
  recorded. The coordinator is intentionally an in-process guarantee and is not
  evidence of multi-process or isolated-VPS behavior.

## Phase 5 local transfer configuration binding follow-up (2026-07-29)

- **Evidence class:** `LOCAL` only. The sender now captures one in-memory,
  non-persisted destination configuration context before deriving its in-flight
  transfer key. The physical send receives that same context and rejects the
  request before any receiver probe or upload if the configured destination
  changes in the gap. The source remains retained and the caller retries under
  the new configuration. The context is not returned by an API, written to
  outbox/batch/schedule state, or logged.
- **Verification:** local sender unittest discovery passed `45` tests,
  including focused coverage for a configuration rotation before send and
  coordinator-to-service context forwarding. Python compilation for the two
  changed sender services, Vue production build, and `git diff --check` passed.
  A newly built local sender image passed the disposable internal-network Push
  smoke with v1 probe, initial import, idempotent retry, matching-request
  coordination, source retention, and interrupted batch recovery. No ports
  were published; the harness uses generated test-only credentials and removes
  its labeled containers, network, and temporary files.
- **Boundary:** no VPS, SSH, remote container, registry publish, real
  credential, user image, or production action was used. This strengthens the
  local Phase 5 sender guarantee only and does not complete isolated-VPS or
  cross-project acceptance.
- **Next local entry:** keep the sender/receiver image tags explicit, run the
  same local smoke after future transfer changes, and wait for a separately
  authorized isolated-VPS clone before advancing the Phase 5 evidence gate.

## Local deployment-plan review summary (2026-07-29)

- **Evidence class:** `LOCAL` only. After a plan is generated, the extension
  UI now renders a review summary from the same non-secret request snapshot:
  instance name, service port, image, deployment mode, and whether the plan is
  for a new isolated instance or local registration of an existing one. The
  summary explicitly states that the separate `Confirm and deploy` action is
  still required. Host identity, paths, credentials, fingerprints, raw
  discovery data, and plan evidence internals remain outside the preview.
- **Verification:** focused extension UI contract tests passed `2`; extension
  task-store regression tests passed `119`; full local pytest passed `517`.
  Both modified browser scripts passed Node syntax checks. A fresh local browser
  page at `#/extensions` loaded with zero page errors; it did not submit
  credentials, SSH tests, discovery, plan creation, or deployment.
- **Boundary:** this makes a locally rendered plan reviewable, but it is not
  isolated-VPS deployment evidence and it does not authorize or start a
  deployment. Any pre-existing page must be reloaded and a fresh plan generated
  to render the new summary.
- **Next local entry:** after reviewing the summary, keep a custom image
  reference limited to a registry the isolated development machine can reach;
  changing image, port, or instance invalidates the old plan and requires a
  fresh review before deployment.

## Read-only discovery target-role gate (2026-07-24)

- **Evidence class:** `LOCAL` only. The extension target form now requires an
  explicit server-purpose field: `isolated-development` or
  `production-read-only`. Existing target records without this field are
  loaded conservatively as `production-read-only`; new targets default to the
  read-only choice until the user explicitly selects otherwise.
- **Behavior:** the selected role is saved with the target. Read-only discovery
  remains available for either role, while deployment-plan generation is
  rejected unless the saved target role is `isolated-development`. The role is
  a local authorization label, not proof of ownership or VPS isolation.
- **Verification:** `python -m pytest -q` -> `506 passed`; focused extension and
  discovery tests -> `195 passed`; `node --check static/js/extensions.js`;
  `node --check static/js/i18n.js`; `git diff --check` all passed. Local browser
  page `http://127.0.0.1:8892/#/extensions` rendered both purpose options and
  no horizontal overflow at the observed viewport. No target role was changed
  or saved in the browser, and no SSH, VPS, remote container, production, or
  deployment action was performed.
- **Next local action:** choose `隔离开发机（推荐）` for the intended isolated
  development target and press `保存`; then re-open the target and confirm the
  saved role before preparing the redacted read-only discovery plan.

## Host identity mismatch recovery (2026-07-24)

- **Evidence class:** `LOCAL` only. When local UI SSH testing receives the
  backend diagnostic `ssh_host_key_mismatch`, the page now stops the flow,
  clears the current session credential fields, discards discovery and plan
  state, and returns to Step 1. It does not display or persist the fingerprint,
  host-key algorithm, raw SSH response, password, or private key.
- **Recovery:** the novice guide explains that the saved server identity no
  longer matches and exposes a single `重新开始` action for the existing
  trusted-terminal confirmation flow. A new pairing must complete before any
  SSH credential test; the backend remains responsible for re-probing,
  algorithm allowlisting, SHA-256 validation, and compare-and-swap persistence.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; `git diff --check`; full local pytest -> `506 passed`.
  Browser inspection of `http://127.0.0.1:8892/#/extensions` was read-only after
  reload; no pairing, SSH, VPS, remote container, production, or deployment
  action was performed.

## Pairing Progress Clarity (2026-07-26)

- **Evidence class:** `LOCAL` only. Review of the pairing completion state
  found no repeat-pairing transition: a completed server identity confirmation
  intentionally remains in Step 1 until an SSH credential test succeeds. The
  prior generic guide sentence said it would move to the next step, which made
  this required credential stage appear to be a loop.
- **Fix:** when the identity is confirmed but no session credential is present,
  the guide now explicitly says that the user remains in Step 1 to test SSH and
  that Step 2 opens only after a successful test. The change does not alter
  host-key verification, credential lifetime, pairing, or any remote action.
- **Verification:** focused extension tests passed locally. No pairing, SSH,
  VPS, remote container, production, or deployment action was performed for
  this review.

## Server Connector Direction, SSH Mainline Preserved (2026-07-27)

- **Evidence class:** `LOCAL` only. The Extensions page now makes the intended
  beginner-facing product direction visible: `服务器连接器（推荐）` is explicitly
  marked `准备中`, while `SSH 连接（高级方式）` is explicitly marked `当前可用`.
  This is an honest route selector, not a connector implementation, enrollment,
  authenticated transport, provider OAuth connection, VPS connection, or
  deployment result.
- **Mainline preservation:** the only active action is `使用 SSH 继续`. It focuses
  the existing Step 1 target form and then retains the current deploy-capable
  sequence unchanged: save target, confirm host identity, supply a transient
  SSH credential, test access, run read-only discovery, and prepare the bounded
  safety plan. The fallback action creates no API request, target, credential,
  pairing, SSH, network, or deployment operation. The unavailable connector
  cannot block or replace this path.
- **Design boundary:** `docs/P4-SERVER-CONNECTOR-UX-STRATEGY.md` and ADR-020
  specify that a real connector needs an installable agent, identity and
  enrollment lifecycle, authenticated outbound transport, signed
  capability-scoped intents, allowlisted agent operations, redacted audit
  events, and local/isolated-VPS evidence before it can become deploy-capable.
  No web terminal is added; browser requests still cannot submit arbitrary
  remote shell commands. Generic OAuth is not treated as an SSH replacement.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; focused `python -m pytest tests/test_extensions.py -q`
  -> `175 passed`; full `python -m pytest -q` -> `507 passed`; and `git diff
  --check` passed locally. Local browser verification at
  `http://127.0.0.1:8892/#/extensions` confirmed the SSH fallback focuses the
  target form, shows its local guidance, produces no relevant page error, and
  has no horizontal overflow at a 390px viewport. No form was submitted and no
  pairing, SSH, VPS, remote container, production, OAuth, or deployment action
  was performed.

## Host Identity Before SSH Credential UX (2026-07-27)

- **Evidence class:** `LOCAL` only. The Step 1 credential area no longer stays
  visible while a saved server has no confirmed host identity, including the
  `ssh_host_key_mismatch` recovery state. The page now shows one clear recovery
  card: the session credential was cleared, confirm the server identity first,
  then enter a password or private key. The hidden area includes the password,
  private-key, sudo, and credential-notice controls.
- **Security and flow:** a host-key mismatch continues to clear all session
  credentials, discovery, plan, and SSH verification state before returning to
  Step 1. Saving a target whose identity is not yet confirmed also clears any
  credential entered prematurely. The credential controls return only after
  canonical host identity confirmation. No password is restored, represented as
  masked text, persisted, logged, or reused across the identity-confirmation
  boundary.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; focused `python -m pytest tests/test_extensions.py -q`
  -> `176 passed`; and `git diff --check` passed locally. The local Extensions
  page reloaded at `http://127.0.0.1:8892/#/extensions` without horizontal
  overflow. Browser verification did not save a target, submit a pairing,
  submit a credential, or attempt SSH, VPS, remote-container, production, or
  deployment access.

## Personal Server Onboarding Redesign (2026-07-27)

- **Evidence class:** `LOCAL` only. The user-visible `连接服务器` mega-step has
  been removed from the initial deployment experience. The entry is now
  `开始部署`: it honestly presents `服务器连接器（推荐）` as unavailable and
  `使用 SSH 设置服务器` as the current working compatibility path. This does not
  implement a connector, OAuth flow, VPS connection, SSH pairing, or deployment.
- **Flow:** the SSH path now renders one exclusive view at a time: server
  details, server identity confirmation, temporary credential check, then a
  ready-to-plan state. A changed server identity clears session credentials and
  stays in its own recovery view; credentials are neither shown as masked text
  nor persisted. The existing discovery, safety-plan, deployment, and network
  sequence remains behind the verified SSH gate.
- **Safety baseline:** canonical SSH host-key algorithm plus `SHA256:`
  fingerprint verification, fail-closed identity changes, session-only
  credentials, backend-owned fixed operations, production read-only treatment,
  isolated-development deployment gate, and receipt-gated source retention are
  unchanged. Personal-use language now hides technical identity details from
  the normal path without weakening those controls.
- **Research and decisions:**
  `docs/P4-PERSONAL-SERVER-ONBOARDING-UX-STRATEGY.md` records applicable public
  product references and the new state model. ADR-021, the SSH pairing strategy,
  the deployment contract, and deployment invariants now distinguish a personal
  safety baseline from enterprise-oriented presentation.
- **Verification:** `node --check static/js/extensions.js`; `node --check
  static/js/i18n.js`; `git diff --check`; focused
  `python -m pytest tests/test_extensions.py -q` -> `177 passed`; full
  `python -m pytest -q` -> `509 passed`. Local browser
  `http://127.0.0.1:8892/#/extensions` loaded the revised entry, opened only the
  server-details view after its SSH action, kept identity and credential views
  hidden, reported no page errors, and had no horizontal overflow at the
  checked desktop and 390px layouts. No target was saved and no SSH, VPS,
  remote-container, production, OAuth, pairing, or deployment action ran.
- **Next local entry:** keep L2 paused. Reopen the local Extensions page to
  review the static onboarding states only. A real server connector requires its
  own implementation milestone for installable agent, enrollment, authenticated
  outbound transport, revocation, capability allowlists, and local tests; it
  must not block the current SSH deployment mainline.

## SSH Host-Key Algorithm Pinning (2026-07-27)

- **Evidence class:** `LOCAL` only. A likely false mismatch loop was found in
  the SSH compatibility path: host identity pairing probes one algorithm, while
  the later authenticated AsyncSSH connection could negotiate a different
  algorithm offered by the same server. That made a multi-key server look like
  a changed server after a successful pairing.
- **Fix:** the authenticated SSH connection now offers only the saved canonical
  host-key algorithm. The callback still verifies both that algorithm and its
  SHA-256 fingerprint. If the server no longer offers that algorithm, the
  result remains fail-closed and is classified as a host-identity mismatch;
  unrelated secure-negotiation failures remain distinct.
- **Verification:** focused extension tests -> `177 passed`; extension task
  store tests -> `118 passed`; full `python -m pytest -q` -> `509 passed`;
  `python -m py_compile extensions/orchestrator.py`; `git diff --check`.
  Local browser reload at `http://127.0.0.1:8892/#/extensions` rendered the
  revised entry without page errors or horizontal overflow. No credential,
  pairing response, real SSH, VPS, remote container, production, or deployment
  action was submitted.
- **Limit:** this removes the local algorithm-negotiation false positive. If a
  future check still reports a mismatch, GenBox must remain stopped because the
  server identity may genuinely have changed; do not repeat password or pairing
  entry until its trusted source is checked.

## Resume constraints

- Require SSH host-key verification; production is read-only and all development
  resources must be isolated.
- Trusted SSH-session pairing is implemented locally and independently reviewed,
  but its external trusted terminal/known-host record remains an initial trust
  anchor, not VPS ownership evidence or an SSH credential substitute. Do not
  record its challenge, response, command, raw pairing observations, or
  credentials in persisted/public state, logs, browser storage, screenshots,
  URLs, or Git. The canonical trust pair is the only permitted saved outcome.
- Keep administrator, Push, management, SSH, and enrollment secrets separate
  and out of URLs, browser storage, Git, ordinary logs, screenshots, and status
  text.
- Source deletion remains disabled unless an authenticated receipt, matching
  SHA-256, `safe_to_delete_source=true`, and explicit user opt-in all exist.
- Record any later isolated-E2E evidence as **VERIFIED**, **USER-CONFIRMED**, or
  **UNVERIFIED** as appropriate; never describe local evidence as real E2E.

## L2 loop result (2026-07-23)

- **Evidence class:** `UNVERIFIED` / blocked before remote I/O.
- **Commands/results:** `git rev-parse HEAD` -> `00be081feb12525e783d0b6e0547cd654fe40999`; `git status --short --branch` -> clean on `codex/p4-deploy-plan-ux-eai`; `git diff --check` -> clean; local `ssh -V` -> OpenSSH_for_Windows_9.5p1; local Docker client -> `29.6.1`. No remote command ran.
- **Risk:** connecting without a confirmed canonical fingerprint could reach a production or wrong-owner host. Runtime target metadata is ignored, untrusted input and contains no host-key confirmation.
- **Blocker:** missing user-confirmed isolated-target identity and canonical SSH algorithm/fingerprint pair; SSH credential/authorization is not established in this repository.
- **Next loop entry:** after the user confirms the isolated development clone, its owner/scope, and the canonical host-key pair, run only the approved read-only SSH discovery set and capture secret-free output. Do not start L3 until that evidence proves source/clone separation and a bounded rollback target.

## Local verification loop (2026-07-23)

- **Evidence class:** `LOCAL` only. L2 is paused; no SSH, VPS, remote
  container, production, or network deployment action was performed.
- **Docker:** local `genbox-p4-local` image `genbox-p4-local:dae8d84` is
  `running`, Docker health is `healthy`, restart count is `0`, and the local
  endpoint returned HTTP 200 from `/api/setup/status`. Non-sensitive status
  fields reported `app_mode=prod`, `auth_required=true`, and provider setup
  still required.
- **UI:** local `/` returned HTTP 200 with the extension-center and Push UI
  resources present; `node --check static/js/extensions.js` passed. This is
  local page/resource and contract evidence, not browser E2E evidence.
- **Push/failure coverage:** the focused sync, Push-route, and extension suite
  passed `201` tests. It covers authenticated import, idempotent retry,
  authentication rejection, invalid-image rejection, transport/error handling,
  and source-retention assertions. No source-cleanup behavior was enabled.
- **Full local tests:** `python -m pytest -q` -> `486 passed in 10.38s`.
- **Risk/gap:** a real browser automation run and live sender-side transfer
  remain unverified; local tests do not prove isolated-VPS or production
  behavior.
- **Next local entry:** keep the receiver contract frozen and, if browser
  tooling is explicitly added, run a local-only browser smoke test against the
  existing container before reopening L2. Otherwise the next remote gate
  remains separately authorized isolated-VPS discovery.

## Local browser smoke loop (2026-07-23)

- **Evidence class:** `LOCAL` only. Chrome was launched against the existing
  local container at `127.0.0.1:18991`; no SSH, VPS, remote container,
  production, or deployment action was used.
- **Browser result:** Playwright `1.61.0` with local Chrome loaded `/` with
  HTTP 200 and no page errors. The page title was `GenBox` and
  `#navExtensions` was present.
- **Extension workflow:** invoking the existing `switchNav('extensions', ...)`
  made `#pageExtensions` visible. The five-step deployment flow rendered its
  target save, host-key pairing, SSH test, environment discovery, safe-plan,
  and deployment controls. The deployment controls remained gated according
  to missing target/trust state; no action was submitted.
- **Push boundary:** the deployment page did not expose a browser Push action
  in this unauthenticated local state. Push receiver behavior remains covered
  by the 201 focused tests, 486 full tests, and prior local Docker preflight;
  this smoke run does not claim browser Push E2E.
- **Next local entry:** keep this browser smoke as the local UI baseline. Any
  further browser work must remain pointed at `127.0.0.1:18991` and avoid
  credential submission or deployment actions; L2 remains paused.

## Authenticated browser smoke and fix (2026-07-23)

- **Evidence class:** `LOCAL` only. A fresh local image was built as
  `genbox-p4-local:login-fix` and run temporarily on `127.0.0.1:18992` with
  the existing local Docker environment file. The temporary container was
  removed after verification; the baseline `genbox-p4-local` container stayed
  running and healthy.
- **Finding/fix:** wrong-key browser login previously kept `#loginError`
  hidden because `.hidden { display: none !important }` overrode the inline
  style. `_setLoginError()` now toggles the `hidden` class in both
  `static/js/app.js` and `static/js/app-all.js`.
- **Browser result:** wrong key kept the login page visible and showed the
  error (`display=block`, `hidden=false`). The local admin key then logged in
  successfully and exposed the extension navigation. No deployment, SSH, or
  remote action was submitted; credentials remained in process memory only.
- **Verification:** `python -m pytest tests/test_setup_security.py -q` -> `39
  passed`; `node --check` passed for both bundles; full `python -m pytest -q`
  -> `486 passed in 11.11s`.
- **Next local entry:** use the authenticated browser baseline for any further
  local UI checks. The deployment wizard and Push receiver remain gated by
  their existing contracts; L2 stays paused until separately resumed.

## Server confirmation-code UX and local verification (2026-07-24)

- **Evidence class:** `LOCAL` only. The revised
  `docs/P4-HOST-KEY-PAIRING-UX-STRATEGY.md` makes the novice-facing task
  “确认这台服务器”: generate a short-lived confirmation, copy the fixed helper
  to an already trusted terminal, paste the confirmation code, then confirm.
  Users do not need to read or compare algorithms, fingerprints, or protocol
  prefixes; manual verification remains an advanced recovery path.
- **Security boundary:** the start response no longer returns the candidate
  host-key algorithm or fingerprint to the browser. The fixed helper produces
  a one-time confirmation code plus an identity-bound digest proof, not a raw
  fingerprint; the pasted value is immediately removed from the input and held
  only in page memory until submission. Backend algorithm allowlisting, full
  `SHA256:` comparison, single-use expiry, target binding, re-probe, and CAS
  persistence remain unchanged.
- **Verification:** Node syntax checks passed for `static/js/extensions.js` and
  `static/js/i18n.js`; Python compilation passed; focused pairing tests passed
  `288`; full `python -m pytest -q` passed `502`; `git diff --check` passed.
  Node DOM mocks cover copy, confirmation-code hiding, one-time submit,
  control locking, success cleanup, expiry, restart, and response redaction.
- **Browser result:** the local lab at `http://127.0.0.1:8892/#/extensions`
  loaded with title `GenBox`, rendered the confirmation-code copy without the
  raw protocol prefix, and reported no browser errors. At `390px` width,
  `scrollWidth` equaled the viewport width. No target was saved or selected for
  pairing, no confirmation was generated, and no SSH, VPS, remote container,
  production, or network deployment action was attempted.
- **Recovery follow-up:** the default panel now exposes “没有已登录终端？”
  before a pairing attempt. Local browser evidence used a temporary TEST-NET
  target, expanded the help, opened the advanced manual path, and confirmed
  keyboard focus moved to that path; Escape returned focus to the help button.
  The temporary target was deleted afterward. This path only changes local UI
  state and did not start host probing, SSH, pairing, or remote work. Focused
  tests now cover its ARIA relationship, Escape behavior, and absence of an SSH
  endpoint call in the handler.
- **Novice-guide alignment (2026-07-24):** `LOCAL` only. After target save, the
  guide now presents "Start server confirmation" and starts only the
  confirmation-code path; it no longer labels that primary action as reading a
  host fingerprint. While a confirmation is active, the guide directs the user
  to copy, run, and paste the code rather than allowing a second start. Cancel,
  expiry, and a rejected submission restore the restart action. The manual
  host-key flow remains an advanced recovery path and the backend canonical
  algorithm plus `SHA256:` comparison is unchanged.
- **Verification:** Node syntax checks passed for `static/js/extensions.js` and
  `static/js/i18n.js`; focused pairing/guide tests passed `4`; full
  `python -m pytest -q` passed `503`; `git diff --check` passed. The new Node
  DOM assertion verifies that the novice button starts pairing without a host
  probe and that cancel restores the start action.
- **Browser result:** the local Lab at `http://127.0.0.1:8892/#/extensions`
  rendered the saved-target guide with the server-confirmation action and the
  no-password/no-private-key explanation. At `390px`, `scrollWidth` equaled
  `innerWidth`. A temporary non-routable local UI target was deleted after the
  check. No confirmation was started, no SSH or VPS action occurred, and no
  credentials, pairing material, remote container, production, or network
  deployment action was used.
- **Keyboard recovery follow-up (2026-07-24):** `LOCAL` only. Cancel, expiry,
  and rejected confirmation submission now return keyboard focus to the visible
  restart control after clearing temporary pairing material. Focused Node DOM
  assertions cover all three recovery paths; the complete local suite passed
  `504`, JavaScript syntax checks passed, and `git diff --check` passed. The
  local Lab browser check loaded `#/extensions` at `390px` with title `GenBox`,
  `aria-live="polite"` on the pairing panel, and no horizontal overflow. No
  target was saved, pairing started, credential entered, or remote action used.
- **Pairing-cancel follow-up (2026-07-24):** `LOCAL` only. The visible
  cancel action now immediately clears page-only pairing material and restores
  the restart control, then sends only the one-time pairing identifier to a
  local cancellation endpoint. The same best-effort local cleanup runs when a
  target is edited or switched, and at browser-side expiry. The endpoint
  discards that transient in-memory record without host probing, target lookup,
  credential input, command input, response input, or disclosure of whether
  the record existed. A direct backend test proves a cancelled record cannot be
  completed or persist trust; the Node DOM mock proves cancellation and target
  editing submit only `pairing_id` and do not call the host-key probe endpoint.
  JavaScript syntax checks passed,
  focused extension suites passed `291`, full `python -m pytest -q` passed
  `505`, and `git diff --check` passed. The local Lab browser check at
  `http://127.0.0.1:8892/#/extensions` had title `GenBox`,
  `aria-live="polite"`, empty pairing fields, no browser errors, and
  `scrollWidth=390` at a `390px` viewport. No pairing was started, no
  credential was entered, and no SSH, VPS, remote container, production, or
  network deployment action was performed.
- **Next local entry:** keep L2 paused. Future local UI work may use mocks and
  the local browser only; do not submit credentials or generate a real pairing
  command. Reopen L2 only after separately verified isolated-target identity,
  canonical host-key trust, and explicit authorization are supplied.

## Local sender contract review (2026-07-23)

- **Evidence class:** `LOCAL` / read-only review. The separate
  `chatgpt2api-dev` worktree contains uncommitted sender changes; no files were
  edited, reverted, staged, or committed there.
- **Observed sender surface:** a shared GenBox Push service, destination
  settings and connection probe, receipt SHA-256 validation, source-retention
  gating, gallery batch Push, and date-range Push are present in the dirty
  worktree. The focused sender service suite passed `8` tests using only a
  test-only process environment value.
- **Gap:** no generation-completion or per-generation single-image Push action
  was found in the reviewed sender UI/runtime. This remains a sender-side
  Phase 4B item and is not implemented or claimed by the GenBox receiver.
- **Boundary:** no sender network request, SSH/VPS action, remote container
  operation, or production mutation was performed. Cross-project E2E remains
  `UNVERIFIED` and L2 remains paused.
- **Next local entry:** obtain explicit authorization before editing the dirty
  sender worktree; then add the per-generation action and focused tests there,
  preserving all existing changes and using only a local/mock receiver.

## Local source-browser loop (2026-07-23)

- **Evidence class:** `LOCAL` only. The local development lab was started from
  commit `f965063` at `http://127.0.0.1:8892`; no SSH, VPS, remote container,
  sender, or production operation was performed.
- **Browser result:** `#/extensions` loaded with title `GenBox`. A temporary
  non-routable `example.invalid` target was used only to expose the pairing
  panel; the two numbered steps, copy-command entry, paste-result entry, and
  explicit submit affordance were present. No pairing command was generated and
  no host probe was submitted.
- **Responsive result:** at a temporary `390x844` viewport the page stayed at
  `scrollWidth=390` with no horizontal overflow. The viewport override was
  reset afterward, and the temporary target was removed through the local API.
- **Residual browser note:** the P4 `extensions.guide_connect_title` warning
  was fixed in `c75488b`; the remaining `prompt.shuffle` and
  `dashboard.no_activity` warnings are outside the P4 contract. No page errors
  were observed.
- **Next local entry:** keep the receiver contract frozen; any further browser
  check must remain local and must not start pairing or submit credentials.

## Local receiver hash-index resilience (2026-07-23)

- **Evidence class:** `LOCAL` only, frozen at commit `dda0ea8`. GenBox now
  records the non-secret source content SHA-256 in receiver-owned PNG metadata
  and restores confirmed hashes from the atomic `SyncManifest` when rebuilding
  the local index after a restart.
- **Integrity boundary:** manifest entries are accepted only when their SHA-256
  is canonical, their file exists, and the resolved file remains inside the
  configured gallery. Standalone or forged image metadata is not trusted as a
  receipt and cannot produce a false `duplicate-local` result.
- **Verification:** the focused sync/Push suite passed `36` tests; the full
  local suite passed `494` tests. Coverage includes index deletion/rebuild,
  cross-path idempotency after rebuild, path confinement, forged metadata
  rejection, metadata retention, and concurrent identical Pushes.
- **Boundary:** this strengthens receiver-side local evidence only. It does not
  implement the sender's per-generation action and does not upgrade the
  isolated-VPS or cross-project E2E evidence.
- **Next local entry:** obtain explicit sender-worktree authorization, preserve
  its existing dirty changes, and use only a local/mock receiver for sender
  development.

## Local receiver hash-index integrity follow-up (2026-07-23)

- **Evidence class:** `LOCAL` only. The receiver now records the SHA-256 of the
  bytes actually written to the gallery in each manifest entry and validates
  that digest before acknowledging `already-imported` or restoring a durable
  source-hash index.
- **Integrity behavior:** a stale persisted index is rehashed and discarded
  when a gallery file changes. A modified file therefore cannot create a false
  `duplicate-local` receipt; the incoming image is imported as a new local
  file. Manifest paths remain confined to the configured gallery. Legacy
  entries without a local digest retain compatibility only when the file bytes
  still match their recorded source SHA-256.
- **Verification:** `python -m pytest -q tests/test_sync_push_routes.py
  tests/test_sync.py` -> `37 passed`; `python -m pytest -q` -> `495 passed`;
  `node --check static/js/extensions.js`, `node --check static/js/i18n.js`,
  and `git diff --check` passed.
- **Boundary:** this is receiver-side local evidence only. It does not add the
  sender's per-generation action, establish an isolated VPS, or provide a
  cross-project/production E2E claim.
- **Next local entry:** keep L2 paused. The next feature still requires
  explicit authorization to edit the separate dirty `chatgpt2api-dev`
  worktree; use only a local/mock receiver there and preserve its existing
  changes.

## Local browser verification after receiver follow-up (2026-07-23)

- **Evidence class:** `LOCAL` only. The repository lifecycle manager started
  the current worktree on `http://127.0.0.1:8892`; no SSH, VPS, remote
  container, production, or network deployment action was performed.
- **Browser result:** local Playwright loaded
  `http://127.0.0.1:8892/#/extensions` with HTTP 200 and page title `GenBox`;
  the extension navigation and page nodes were present. At `390x844`,
  `scrollWidth` equaled `innerWidth` (`390`), so no horizontal overflow was
  observed. The session was unauthenticated and submitted no credentials,
  pairing material, or deployment action.
- **Lifecycle:** the local lab was stopped after the smoke check. This is UI
  loading/responsive evidence only and does not claim browser Push E2E.

## Local Push v1 receipt contract (2026-07-23)

- **Evidence class:** `LOCAL` only. The authenticated Push status probe and
  every successful single-image receipt now declare `contract_version: "v1"`.
  This gives a sender a stable additive compatibility signal without exposing
  credentials or changing the source-retention decision.
- **Verification:** focused sync/Push tests passed `37`; the full local suite
  passed `495`; Python compilation for `main.py`, `sync/ingest.py`, and
  `sync/manifest.py` passed; all four frontend bundle syntax checks passed.
  A local browser smoke at `#/extensions` returned HTTP 200 with zero page
  errors and no narrow-screen horizontal overflow.
- **Boundary:** this is receiver-side contract evidence only. The sender's
  per-generation action, authenticated cross-project transfer, isolated VPS,
  and production non-mutation remain unverified.

## Local legacy manifest integrity follow-up (2026-07-24)

- **Evidence class:** `LOCAL` only. Legacy `SyncManifest` entries that predate
  `local_sha256` are still accepted for compatibility only after the gallery
  file is rehashed and matches their recorded source SHA-256. Missing or
  malformed source hashes fail closed.
- **Verification:** focused sync/Push tests passed `39`; the full local suite
  passed `497`; Python compilation and all four frontend bundle syntax checks
  passed; `git diff --check` passed. A local Playwright smoke at
  `http://127.0.0.1:8892/#/extensions` returned HTTP 200 with zero page errors
  and `scrollWidth=innerWidth=390` at the narrow viewport. The lab was stopped
  afterward.
- **Failure boundary:** an invalid-image rejection is covered locally and
  leaves the receiver gallery, manifest, and content indexes untouched. This
  is not sender-side source-retention or network-failure evidence.
- **Boundary:** this closes a receiver-side local integrity gap only. It does
  not implement the sender's per-generation action or establish isolated-VPS,
  cross-project, or production evidence.

## Local Push limit probe consistency (2026-07-24)

- **Evidence class:** `LOCAL` only. The v1 status probe now reports the same
  process-level image byte limit used by `validate_image_payload`, so a sender
  cannot receive a preflight limit that differs from the active receiver.
- **Verification:** the focused sync/Push suite passed `39`; the full local
  suite passed `497`; Python compilation, all four frontend bundle syntax
  checks, and `git diff --check` passed. Local browser loading at
  `http://127.0.0.1:8892/#/extensions` remained HTTP 200 with zero page errors
  and no narrow-screen overflow; the lab was stopped afterward.
- **Boundary:** this is destination probe/receiver contract evidence only. It
  does not prove sender UI behavior, network reachability, or remote E2E.

## Local sender-hash mismatch gate (2026-07-24)

- **Evidence class:** `LOCAL` only. Push accepts an optional canonical
  `source_sha256` from a sender. When present, GenBox compares it with the
  uploaded bytes before touching gallery, manifest, or content indexes; absent
  values remain compatible with existing v1 senders.
- **Verification:** focused sync/Push tests passed `42`; the full local suite
  passed `500`; matching, malformed, and mismatched digest cases are covered.
  Python compilation, all four frontend bundle syntax checks, and
  `git diff --check` passed. Local browser loading at
  `http://127.0.0.1:8892/#/extensions` returned HTTP 200 with zero page errors
  and no narrow-screen overflow; the lab was stopped afterward.
- **Boundary:** this is receiver-side pre-commit validation only. It does not
  prove sender source retention, sender UI, network reachability, isolated VPS,
  or production behavior.

## Local Push limit rejection follow-up (2026-07-24)

- **Evidence class:** `LOCAL` only. The authenticated status probe's
  `max_image_bytes` is now tested against the actual rejection path: when a
  payload exceeds the active process limit, Push returns `422` and leaves the
  receiver gallery unchanged.
- **Verification:** focused sync/Push tests passed `43`; the full local suite
  passed `501`; Python compilation, all four frontend bundle syntax checks,
  and `git diff --check` passed. Local browser loading at
  `http://127.0.0.1:8892/#/extensions` remained HTTP 200 with zero page errors
  and no narrow-screen overflow; the lab was stopped afterward.
- **Boundary:** this is receiver-side capacity/error evidence only. It does
  not prove sender retry policy, source retention, network reachability, or
  remote/production behavior.

## Local P4 guide translation cleanup (2026-07-23)

- **Evidence class:** `LOCAL` only, frozen at commit `c75488b`. The extension
  guide title now has an explicit Chinese/English translation entry instead of
  relying on the source HTML fallback.
- **Browser result:** the local `8892` page loaded `#/extensions` with title
  `GenBox`; the guide rendered `先连接你的服务器`, and no
  `extensions.guide_connect_title` warning remained. No target was selected,
  no pairing command was generated, and no SSH action was submitted.
- **Verification:** `python -m pytest -q tests/test_extensions.py
  tests/test_extension_task_store.py` -> `287 passed`; full local suite ->
  `494 passed`; both extension JavaScript syntax checks passed.
- **Boundary:** two unrelated pre-existing i18n warnings remain; they do not
  affect the P4 host-key pairing flow and are not claimed as fixed here.

## Local GenBox sender development image slice (2026-07-28)

- **Evidence class:** `LOCAL` only. The separate chatgpt2api worktree on branch
  `codex/genbox-p4-sender-image` now contains the first GenBox Push v1 sender
  slice, committed as `23a674e`. It stores a destination/source configuration,
  masks the Push key in API responses, probes the receiver, validates the
  returned contract/source/SHA-256 receipt, and always retains the source image.
- **Verification:** sender focused Python tests passed `8`; Python compilation
  and `git diff --check` passed; the Vue production build passed with
  `npm run build`. Tests use local fakes only and no real credentials or image
  data.
- **Security boundary:** redirects are refused so credentials and image bytes
  are not forwarded to a different origin; non-boolean deletion hints are not
  treated as permission. No source deletion, batch push, scheduling, arbitrary
  remote shell, SSH, VPS, or production action was performed.
- **Build blocker:** local Docker Desktop remained `starting`; the attempted
  build returned a local Docker Engine 500 ping error and produced no verified
  image ID. This is not image-build, VPS, or deployment evidence.
- **Next local entry:** restore a running local Docker Engine, build and inspect
  the tagged image locally, then run only local receiver/sender smoke tests.

## Local sender runtime-smoke image (2026-07-28)

- **Evidence class:** `LOCAL` only. A temporary container created from local
  image `genbox/chatgpt2api:2.7.0-genbox-p4.0.1-runtime-smoke` started on a
  loopback-only port, reported version `2.7.0-genbox-p4.0.1-dev`, and exposed
  the GenBox Push settings route. The temporary container was removed after
  verification.
- **Verification:** an unauthenticated request to the settings route was
  rejected; an authorized local test request returned only the masked settings
  shape and no Push key. No Push was configured or sent, and no source image,
  SSH, VPS, remote container, production system, registry push, or external
  deployment was used.
- **Build qualification:** this image is a local runtime smoke artifact made by
  overlaying the current complete application source and Vue build onto an
  existing local chatgpt2api image. It proves local startup and the new route
  boundary, but does not replace a clean build from the repository Dockerfile.
  The canonical Dockerfile still cannot resolve its base-image metadata because
  Docker Desktop's configured local registry mirror returns EOF.
- **Next local entry:** repair or replace that Docker registry mirror, then
  rebuild from the repository Dockerfile and repeat the same loopback-only
  smoke checks before any isolated-VPS work.

## Local canonical sender image build (2026-07-28)

- **Evidence class:** `LOCAL` only. The stale Docker Desktop registry mirror
  was removed from the local daemon configuration after a backup was created.
  Direct Docker Hub metadata requests still fail through the local network
  path, so compatible Node and Python base images were fetched from an
  alternate registry into the local Docker cache and tagged locally with the
  names required by the unchanged repository Dockerfile.
- **Verification:** `docker build --pull=false` using the original Dockerfile
  completed and produced local image `genbox/chatgpt2api:2.7.0-genbox-p4.0.1-dev`.
  A loopback-only temporary container started from that image, returned version
  `2.7.0-genbox-p4.0.1-dev`, rejected an unauthenticated settings request, and
  returned masked GenBox Push settings for a local authorized test request. The
  temporary container and earlier overlay smoke image were removed afterward.
- **Qualification:** this is a reproducible local Dockerfile build while the
  two required base-image tags remain cached. It is not a registry-pushed
  artifact, clean-machine proof, isolated-VPS proof, cross-project Push E2E,
  or production evidence. The upstream Vue lockfile also reports `11` existing
  dependency audit findings during `npm ci`; no audit remediation was included
  in this sender slice.
- **Next local entry:** retain the cache-backed image for local development,
  add a mocked Push round-trip container test if needed, and separately resolve
  the environment's Docker Hub proxy route before requiring clean-machine
  rebuild evidence.

## Local sender-receiver Push container round trip (2026-07-28)

- **Evidence class:** `LOCAL` only. The canonical chatgpt2api sender image and
  a freshly built current GenBox receiver image ran on a temporary Docker-only
  network with one synthetic 1x1 PNG and test-only credentials. The sender
  completed the authenticated v1 probe, the first Push imported the image, and
  the identical retry returned an accepted idempotent status. The sender also
  verified that its source file remained present after both requests.
- **Fix:** this live local check exposed that `curl_cffi` does not support the
  `files` request argument used by the sender implementation. Sender commit
  `6a099cd` now creates a `CurlMime` multipart body, matching the installed
  library API. Focused and full sender unittest discovery each passed `8`, and
  the canonical sender Dockerfile built successfully before the round trip.
- **Cleanup and boundary:** temporary sender/receiver containers, network,
  synthetic image, and test-only configuration were removed. No user image,
  Push key, credential, SSH, VPS, remote container, production system, or
  external deployment was used. This proves a local container round trip only;
  isolated-VPS and production evidence remain unverified.
- **Next local entry:** add this disposable two-container round trip to a
  repeatable local test harness, then keep batch, scheduling, and cleanup work
  in their separate roadmap phases.

## Repeatable local GenBox Push smoke harness (2026-07-28)

- **Evidence class:** `LOCAL` only. The separate chatgpt2api worktree now has
  a disposable two-container smoke harness for a prebuilt local sender image
  and a prebuilt local GenBox receiver image. It creates an internal Docker
  network with per-run labels, publishes no ports, and uses generated test-only
  credentials from temporary environment files that are removed on exit.
- **Verification:** the harness passed the authenticated Push v1 probe, first
  synthetic-image import, idempotent retry, source SHA-256 receipt, receiver
  image dimensions and metadata, and sender source-retention check. Its focused
  harness tests passed `7`; the sender Push test suite passed `9`; Python
  syntax compilation and `git diff --check` passed. Normal completion left no
  labeled containers, networks, or temporary credential files.
- **Safety boundary:** it refuses implicit or `latest` image references and
  never builds, pulls, publishes, or deploys. Cleanup removes only exact
  resources whose fixed local-smoke label and per-run label both match; a label
  mismatch fails closed. This is not VPS, production, registry, batch, or
  scheduled-Push evidence.
- **Next local entry:** build the sender and receiver images from their current
  source revisions as separate local steps, then use this harness after any
  Push-protocol or image-build change. Keep isolated-VPS verification behind
  its explicit lifecycle gate.

## Per-generation GenBox Push sender flow (2026-07-28)

- **Evidence class:** `LOCAL` only. The separate chatgpt2api sender worktree
  now offers an opt-in "Push to GenBox after generation" setting in Studio.
  A generated image is saved first and then added to a persistent local outbox;
  Push runs independently, so an unavailable destination cannot turn a
  successful image generation into a failure. Failed items keep their source
  and expose a scoped retry action. Restart recovery requeues an interrupted
  in-flight item. Prompt text is transient only and is not written to the
  outbox state.
- **Verification:** sender unittest discovery passed `22`; Python compilation
  and Vue production build passed. A current local Dockerfile image passed the
  disposable two-container v1 probe, first-import, idempotent-retry, and
  source-retention smoke harness. A loopback-only browser check of the sender
  Studio confirmed the setting, its local-save/failure boundary text, and its
  checkbox interaction. All test credentials and image data were synthetic.
- **Safety boundary:** no real image, prompt, SSH credential, Push key, VPS,
  remote container, production system, registry push, or external deployment
  was used. This does not prove an isolated-VPS route, a real upstream image
  generation, batch Push, scheduled Push, cleanup, or production behavior.
- **Next local entry:** treat the next work as a separate Phase 5
  batch/scheduler design or an explicitly authorized isolated-VPS Phase 4
  gate; neither is implied by this local evidence.

## Phase 5 isolated acceptance run (2026-08-01)

This earlier browser run is superseded by the final isolated evidence in
docs/PHASE5-EVIDENCE-2026-08-01.md. Its duplicate progress dialog and zero-
count projection were captured before the sender worker/projection fixes and
are retained only as historical debugging context. They are not current
blockers and must not be used to describe the final Phase 5 result.

The final isolated evidence records successful batch interruption/recovery,
failed-only retry, concurrent schedule lease rejection, late-arriving image
discovery, source retention, and restoration of the private receiver route.
The production boundary remains unchanged. Clean GitHub-clone redeployment,
full sanitization review, and public release remain later gates.

## Clean GitHub redeployment and sanitization check (2026-08-01)

- **CLEAN-GITHUB-CLONE:** a new clone of the GenBox experimental branch at
  commit f6f3186 built successfully from its repository Dockerfile. The
  isolated Compose deployment reported a healthy container; its setup-status
  endpoint and home page both returned HTTP 200. The clean clone test suite
  passed 582 tests. The deployment used only generated local configuration and
  a separate temporary storage directory.
- **CLEAN-SENDER-CLONE:** a new clone of the experimental sender branch at
  commit ca6f1ba built successfully from its Dockerfile, including the Vue
  production build. The sender test suite passed 66 tests. A disposable
  loopback-only container started with a generated test key and returned HTTP
  200 for its home page; no VPS, production data, or user credentials were
  mounted.
- **SANITIZATION:** tracked-file and Git-history scans for private-key blocks,
  provider tokens, GitHub tokens, Tailscale enrollment tokens, and non-example
  administrator keys found no real credential. Matches were limited to test
  sentinels, ghp_xxx-style documentation placeholders, and synthetic network
  fixtures. The clean clones had no Git worktree changes.
- **BOUNDARY:** this proves reproducible clean local deployment and sanitized
  source state. It does not authorize a production upgrade or an upstream PR;
  those remain separate release decisions.
