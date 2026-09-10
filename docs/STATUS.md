# Current Project Status

## 2026-09-10 GPT Acceptance And v2.6.8 Publication

- **USER-CONFIRMED:** GPT target-model precision editing passed manual acceptance.
  The user authorized GitHub publication before testing other vendors.
- **PREPARED:** v2.6.8 version/Compose metadata, bilingual README feature section
  and release notes. All four public size tables are checked against the 27
  code presets. No universal GPT endpoint or other-vendor support is claimed.
- **VERIFIED:** Ten Node suites and 47 packaging/size/extension checks pass.
  New commits contain no checkpoint or user-image additions; credential-pattern
  review found no real key material. Only explicit release files are staged.
- **PENDING:** Hosted clean-source tests, desktop runtime/HTTP smoke tests,
  Docker smoke and formal release asset verification. Existing v2.6.7 tag is
  immutable: its desktop workflow 34011635213 failed a browser test and never
  created a Release; its Docker workflow succeeded. v2.6.6 is the latest public
  Release as verified via GitHub CLI before this publication attempt.
- **RESUME:** Finish v2.6.8 publication and verify assets before reporting success.
  Other-vendor real requests still need explicit authorization and separate UAT.

## 2026-09-10 Precision Quick Start

- **IMPLEMENTED:** Short model, size/composition and smart-tool instructions
  appear in the inspector. The size heading is centered. Local cutout/refinement
  is distinguished from online AI removal; trial authorization remains scoped
  and never submits a request.
- **IMPLEMENTED:** The precision guide now starts with five clickable navigation
  steps. First entry opens it once per browser storage profile; dismissal stores
  only the non-sensitive `seen` flag. Blocked storage falls back to once per JS
  session. Visible dialogs defer navigation; offscreen closed drawers do not.
  Leaving precision before the timer fires does not open the guide elsewhere.
- **VERIFIED:** Node syntax, precision UI and version-metadata assertions passed.
  Ten synthetic Playwright scenarios passed (including first-entry/replay,
  keyboard focus, blocked storage, visible-modal deferral and mobile layout);
  518 precision/workflow/provider/setup-security tests passed. No paid upstream
  request was made. Screenshots and temporary outputs are excluded from Git.
- **RESUME:** Refresh the owned 8895 lab after restart and request combined UI
  acceptance for the instructions, first-use guide, model grouping/scroll and
  version dimensions/time. Target-model presets remain USER-CONFIRMED; other
  vendors still need separate authorized real trials and manual acceptance.

## 2026-09-09 Precision UI Checkpoint And Grouped Model Visibility

- **USER-CONFIRMED:** The user accepted the target-model size presets.
  UI acceptance is deferred until the model-visibility grouping and scroll
  retention fixes are complete. Other vendors' edit/size linkage still needs
  separate manual acceptance; no universal model compatibility is claimed.
- **IMPLEMENTED:** Inspector order is processing, model (native collapsed
  disclosure), size, smart tools. Workflow restore retains per-version
  dimensions and timestamps; decoded image dimensions correct stale metadata.
  Version timestamps do not claim to be original photo capture times.
- **CHECKPOINTS:** `95e06f2` preserves backend precision-size/workflow contracts;
  `ccdd45c` preserves the model-first workbench, gallery/cutout/canvas changes,
  version metadata and their tests. These are local commits, not a release or
  upstream push; unrelated untracked files and screenshots were excluded.
- **FIXED:** Model visibility now groups IDs by name family, with group
  checkboxes, selected counts and indeterminate state. This is navigation only,
  not a capability claim. Individual/group/all draft changes update existing
  nodes without rebuilding the menu, preserving checkbox focus and list scroll.
  Only Confirm saves local visibility preferences; Cancel discards the draft.
- **VERIFIED:** `node --check static/js/app-all.js`,
  `node tests/test_precision_edit_ui.mjs`,
  `node tests/test_precision_version_metadata.mjs`,
  nine synthetic browser scenarios (including desktop/mobile grouping, scroll,
  focus, cancel, empty selection and provider isolation), and 518 focused Python
  tests passed. `git diff --check` passed. No paid upstream request was made.
- **RESUME:** After the owned lab restart, request combined UI UAT for grouping,
  scroll retention, inspector arrangement and per-version dimensions/time.
  Other vendors' actual edit/size linkage remains pending separate testing and
  explicit authorization for any paid request. Keep strict output checking and
  the no-replay image-edit POST guard; exclude temporary outputs from commits.

## 2026-09-09 User-Authorized Precision Size Trials And Resize UI

- **FIXED / USER-CONTROLLED SIZE TRIAL:** A strict-size preset that is not
  declared by the selected model remains visible and selectable. GenBox now
  offers an explicit `授权试用 <size>` action once an authorized edit model and
  valid target are selected. Confirmation stores only the current provider,
  current model, and exact size; it neither inherits historical sizes from a
  different model nor starts or retries an image-edit request automatically.
- **RETAINED / OUTPUT AND BILLING GUARDS:** A trial still requires the user to
  press Generate separately. Strict output-size validation remains fail-closed,
  `裁切适配` remains an explicit local finishing mode, and an ambiguous or
  failed image-edit POST is never replayed automatically.
- **FIXED / RESIZE CONTROL HIERARCHY:** The resize section now uses the same
  restrained glass texture as the workflow-filter control. Its title only shows
  `智能扩图与画布适配`; the mode selector is presented as
  `尺寸方式 | 模型尺寸` with a visible native-select chevron. The former
  secondary heading hint is retained only for assistive technology.
- **VERIFIED / FINAL LOCAL INTEGRATION:** `node --check static/js/app-all.js`,
  the precision UI static suite, seven browser precision-workbench scenarios,
  `224` precision-edit/workflow contracts, `253` provider precision/alias/error
  contracts, and `41` setup-security checks passed. The owned `8895` laboratory
  was restarted and verified online. No paid upstream image-edit request was
  made for this change.
- **USER-CONFIRMED / MANUAL LAB UAT:** On `8895` the workbench displayed the
  title `智能扩图与画布适配` and the selector `尺寸方式 | 模型尺寸`. With
  `gpt-image-2.5-c` at `1024x1024`, the UI first required `授权试用 1024x1024`
  and then showed the saved authorization after the local confirmation. Changing
  to `1168x656` required a new authorization. Switching the endpoint to
  `小恐龙` cleared the usable authorization and showed its model as待确认,
  confirming provider/model/size scoping. This was local UI state only; no
  upstream request, upload, or paid action was performed.

## 2026-09-09 Precision Resize Readiness And Guidance UX

- **FIXED / PURE-RESIZE READINESS:** A resize request with no annotations now
  takes the validated pure-resize path before checking a leftover local
  selection mode. Choosing a size and composition guidance therefore does not
  leave “生成图片” disabled merely because the user previously used a manual
  selection tool. Source, selected authorized model, and size-capability
  validation still remain required.
- **FIXED / COMPOSITION PRESETS:** Selecting a composition preset now replaces
  the current composition guidance instead of appending it. The selector and
  hint say this explicitly; selecting the same item repeatedly cannot duplicate
  prompt text, and users can still edit the resulting text freely.
- **FIXED / RESIZE DISCOVERABILITY:** The former generic “画布尺寸” heading is
  now “智能扩图与画布适配”, with an accent-marked title treatment and a short
  instruction that explains choosing a target size and composition direction
  before model validation.
- **VERIFIED / REGRESSION:** JavaScript syntax, the precision UI static suite,
  seven Playwright precision-workbench scenarios, and `253` provider
  precision/alias/error-safety tests pass. The owned development laboratory at
  `8895` is online after restart.

## 2026-09-09 Professional Cutout Dock And 21:9 Incident Follow-Up

- **FIXED / PROFESSIONAL CUTOUT WORKBENCH:** The professional cutout focus
  view is a real two-column workbench: the live canvas occupies the left
  stage; a same-height, glass-surface local-tool dock occupies the right.
  The dock has a visible resize separator, keyboard-resizable separator,
  collapse control, and a return control. Its geometry is synchronized after
  the canvas reflows and observed while the canvas size changes, so opening,
  resizing, switching images, collapsing, and reopening do not leave the dock
  at an obsolete height.
- **VERIFIED / LIVE LAB UI:** In the owned development laboratory at `8895`,
  a `1438x994` viewport produced equal canvas and dock bounds (`876px` high),
  with the dock clear of the canvas. Collapsing reduced the dock from `410px`
  to `48px` and expanded the canvas; reopening restored it to `410px`. Return
  restored the ordinary workbench. Browser regression coverage also checks
  equal bounds and that every professional control remains inside its card.
- **VERIFIED / 21:9 FAILURE CLASSIFICATION:** The runs ending at
  `2026-09-09 01:14:09` and `01:20:34` reached the `gpt-image2-bc`
  image-edit transport and received upstream HTTP `503`. They are not local
  resize-preflight rejections and do not prove that `21:9` is invalid. No
  automatic replay was added because an edit POST is not safely idempotent.
- **DECISION / SIZE CORRECTION BOUNDARY:** “模型尺寸” must never silently
  rewrite its requested dimensions. A future “裁切适配” implementation may
  explicitly request a confirmed native direction and locally fit/crop the
  returned image to a user-selected target, but it needs a separate request
  and output contract plus tests. It is not a remedy for a transient upstream
  `503`.
- **VERIFIED / REGRESSION:** JavaScript syntax, precision UI checks, seven
  Playwright precision-workbench scenarios, and `253` provider
  precision/alias/error-safety tests pass. The lab was restarted after the
  final visual fix. No paid upstream edit was sent for this verification.

## 2026-09-08 Precision Edit HTTP 503 Non-Replay Fix

- **VERIFIED / MODEL-SIZE EVIDENCE:** Two completed local precision-edit tasks
  now confirm the only strict sizes retained for `gpt-image2-bc`: `1152x2048`
  completed at `2026-09-08 09:16:55`, and `2048x1152` completed at
  `2026-09-08 23:29:21`. The latter originated from a `1024x1024` canvas and
  completed in `90.3` seconds. Earlier requests for `2544x1088`, `3840x1648`,
  and `3840x2160` returned differing output dimensions and remain excluded
  from strict model sizes. They may be offered only through explicit local
  crop-to-fit adaptation, never as an upstream exact-size promise.
- **VERIFIED / INCIDENT CLASSIFICATION:** The user-reported task beginning at
  `2026-09-08 22:54:47` failed at `22:58:03` after dispatch to canonical model
  `gpt-image2-bc` on the `/images/edits` transport profile. The persisted
  structured result is `precision_edit_upstream_error` with HTTP `503`; it is
  neither a local resize preflight rejection nor an output-size mismatch.
  Ordinary text-to-image availability cannot verify a separate image-edit
  endpoint.
- **FIXED / NO EDIT REPLAY:** Precision-edit now has one POST allowance for the
  entire operation. `429`/`5xx` no longer retry the multipart edit request and
  a failed first configured endpoint is not followed by a second endpoint. This
  prevents duplicate work or billing when an upstream has accepted a request
  before reporting a failure; users may explicitly retry later.
- **VERIFIED / REGRESSION:** `253` provider precision/alias/error-safety tests;
  `224` precision contract/workflow tests; JavaScript syntax plus precision and
  generation-error UI tests pass. The owned development lab at `8895` was
  restarted and verified online after the change. No additional paid upstream
  edit request was submitted.
- **FIXED / PROFESSIONAL CUTOUT DOCK:** When the professional dialog is
  portaled to `document.body`, its focused-workbench CSS now retains fixed
  viewport positioning above the canvas. The dedicated right-side dock keeps
  the local algorithm picker, run/refresh controls, selection refinement, and
  foreground restoration visible instead of placing them below the canvas.
  Static UI checks plus seven Playwright precision-workbench scenarios pass
  using the installed local Chrome executable; the owned `8895` lab was
  restarted after this CSS correction.

## 2026-09-08 Precision Crop Presets And Professional Workbench

- **FIXED / CROP PRESET COMPLETENESS:** “裁切适配” now builds independent
  `1K`, `2K`, and `4K` preset groups from the documented dimension catalogue.
  Selecting a tier/ratio resolves to its `crop:` preset rather than falling
  back to “自定义” because that local preset was absent. These options remain
  local fit/crop targets and do not add native-size authority to the upstream
  model whitelist.
- **FIXED / PROFESSIONAL FOCUS MODE:** Opening professional cutout moves its
  local-only controls into a dedicated focus workbench: the live image canvas
  remains visible while unrelated inspector, gallery, generation, and toolbar
  controls are hidden. Closing the dock or pressing `Esc` restores the original
  workbench and focus.
- **VERIFIED / FAILURE CLASSIFICATION:** The user-reported run beginning at
  `2026-09-08 14:23:22` and failing at `14:31:23` was an upstream HTTP `503`.
  It is a temporary provider service failure after dispatch, not a local source
  image, resize preset, or output-validation failure. No automatic retry was
  added because an image-edit POST is not safely idempotent. The redacted
  handling guidance was added to the local `precision-edit-error-diagnosis`
  skill.
- **VERIFIED / REGRESSION:** `node --check static/js/app-all.js`,
  `node tests/test_precision_edit_ui.mjs`, `node tests/test_cutout_model_install_ui.mjs`,
  and the focused precision/cutout pytest suite passed (`483 passed`) on
  2026-09-08. `git diff --check` reported no whitespace errors, only existing
  line-ending warnings.
- **VERIFIED / HEADED LOCAL LAB:** An owned development laboratory was started
  at `http://127.0.0.1:8895` on 2026-09-08. In its live DOM, selecting
  “裁切适配” exposed complete `1K`, `2K`, and `4K` groups and selected
  `2K · 1:1 · 2048 × 2048`; professional cutout hid unrelated controls and
  `Esc` restored the ordinary workbench. This is local UI evidence only, not a
  paid upstream image-edit success. The unrelated legacy `8894` runtime record
  remains mismatched and was not stopped or modified.

## 2026-09-08 Precision Cutout Modes

- **FIXED / SIMPLE-PRO MODE:** The local one-click cutout panel now separates a
  simple mode from a professional dialog. Simple mode exposes only the current
  executable, verified local adapter and the main cutout action. Professional
  mode reuses the existing local algorithm selector, feather, selection, and
  foreground-restore controls in a standalone dialog.
- **RESEARCH BOUNDARY:** `XIAOTsune/MatteBackgroundFree` is MIT code built
  around BiRefNet, but its model weights and dependency chain still require a
  separate authorization/reproducibility review. `Scipline/Image_matting` has
  no verified license declaration in the reviewed metadata and includes a
  remote remove.bg path, so neither project code nor weights were imported.
- **RETAINED SAFETY:** Only adapters reported executable by GenBox's local
  capability registry can be selected or run. No third-party download, remote
  image service, or paid generation request was triggered by this change.

## 2026-09-08 Precision Model-Size Catalogue

- **FIXED / READ-ONLY CATALOG:** `/api/providers` and the provider detail
  endpoint now expose `precision_size_catalog` per model. The projection keeps
  official/documented GPT Image 2 presets separate from the connection's
  explicit, validated `supported_sizes` declaration.
- **FIXED / STRICT BOUNDARY:** `strict_selectable_sizes` is populated only for
  an enabled OpenAI-compatible image provider whose model is explicitly
  confirmed for precision editing and has a valid declared size list. Official
  documentation never expands submission authority; the current laboratory
  gateway therefore remains limited to its confirmed dimensions.
- **VERIFIED / TESTS:** Precision route/provider/alias contracts pass (`419`
  focused tests after this change); Python compilation and `git diff --check`
  pass. No provider request or secret was used.

## 2026-09-08 Precision Resize Mode Separation

- **FIXED / TWO-LEVEL MODE:** “改变尺寸” now exposes a second-level “严格尺寸 / 裁切适配” selector. Strict mode is tied to the selected model's confirmed upstream whitelist; crop-to-fit mode keeps a separate common editing preset family and uses the existing local `fit_crop` post-processing path.
- **FIXED / LINKED PRESETS:** Tier, aspect ratio, pixel dimensions, and the active mode stay synchronized. Switching modes maps the selected dimensions into the matching preset family without changing the backend request contract.
- **VERIFIED / UX BASIS:** A short agent-reach review of mature image resizer patterns found the same separation between exact destination presets and local fit/fill/crop behavior, with explicit final dimensions before export. This is a design reference, not an upstream capability claim.
- **VERIFIED / REGRESSION:** `node --check static/js/app-all.js`, `node tests/test_precision_edit_ui.mjs`, and `python -m pytest tests/test_precision_edit_contract.py tests/test_provider_precision_contract.py tests/test_provider_precision_alias_compat.py -q` passed on 2026-09-08 (`418 passed`).
- **RETAINED BOUNDARY / LAB:** The local `8894` page was reachable during UI inspection, but `python scripts/genbox_lab.py status` reported that its runtime record did not match the current port or mode and refused to terminate or restart anything. No real paid edit request was sent for this change; an owned lab restart or headed user acceptance remains required before calling this live upstream evidence.

## 2026-09-08 Precision Size Evidence Gate

- **VERIFIED / FAILURE ROOT CAUSE:** Recent `gpt-image2-bc` failures are
  upstream output-size mismatches, not source-image format errors. On
  **2026-09-08 09:53:22**, request `3840x1648` returned `3808x1632`; GenBox
  rejected it with `precision_edit_output_size_mismatch`. The same strict
  behavior applies to a `4K · 16:9 · 3840x2160` request that returned
  `2048x1152`.
- **VERIFIED / SIZE EVIDENCE:** Generation `gen_0083_f0c3b3` completed at
  **2026-09-08 09:16:55** with output `1152x2048`. Together with prior
  successful `2048x1152` outputs, these are the only two dimensions currently
  treated as confirmed for the local `gpt-image2-bc` model.
- **FIXED / FAIL-CLOSED PRESETS:** The local laboratory capability record for
  `gpt-image2-bc` now contains only `2048x1152` and `1152x2048`; the
  `gpt_image_2_flexible` policy was revoked. Unverified 2K/4K combinations are
  therefore rejected before dispatch and should be hidden or marked unavailable
  by the UI. This is an empirical whitelist, not a claim of universal upstream
  support.
- **RETAINED BOUNDARY:** Strict output validation remains enabled. A local
  `fit_crop` operation is an explicit post-processing fallback and does not
  prove native 4K support or replay the paid edit request.

## 2026-09-08 Precision Size Preset Clarity

- **FIXED / PRESET DISCOVERABILITY:** The `常用尺寸` menu now visibly lists all
  27 combinations of `1K / 2K / 4K` and the nine supported ratios, including
  `2K · 9:16 · 1152 × 2048` and `4K · 21:9 · 3840 × 1648`.
- **FIXED / UI COPY:** Removed the confusing routine action labelled
  “恢复逐项尺寸确认”. Flexible-size mode remains a deliberate capability
  policy, while individual target confirmation is still available when the
  policy is not enabled.
- **CLARIFIED / LIVE FAILURE:** A strict `4K · 16:9 · 3840 × 2160` request
  failed because the configured upstream returned `2048 × 1152`; GenBox
  correctly rejected the mismatched output instead of presenting it as 4K.

## 2026-09-07 Precision Flexible-Size Capability

- **FIXED / SIZE AUTHORIZATION:** A confirmed precision-edit model can now
  opt into `gpt_image_2_flexible`, which admits every target inside the
  documented GPT Image 2 envelope: 16-pixel alignment, at most `3840` per
  side, aspect ratio from `1:3` to `3:1`, and `655,360` to `8,294,400` pixels.
  Other models remain on the exact `supported_sizes` whitelist. Unknown policy
  strings fail closed.
- **VERIFIED / MATRIX:** Provider tests cover every `1K / 2K / 4K` tier and
  all nine ratio choices, plus a legal custom size and an invalid alignment
  case. The capability API persists an explicit user confirmation and supports
  revocation without silently changing the model's precision-edit permission.
- **VERIFIED / LOCAL RUNTIME:** The local `8894` laboratory was restarted in
  development mode. The selected `gpt-image2-bc` model was explicitly enabled
  for the flexible-size policy through the local capability endpoint. This is
  local authorization, not evidence that an external upstream has natively
  returned every possible size.
- **VERIFIED / REGRESSION:** Precision contract and provider suites passed
  `415`; gallery browser tests passed `6`; JavaScript syntax/static UI checks
  and `git diff --check` passed.
- **RETAINED BOUNDARY:** A minimal, user-authorized live request is still
  needed to verify an additional non-`2048x1152` upstream output. Strict mode
  continues to reject mismatches; local fit/crop remains an explicit fallback
  and never replays a non-idempotent edit request.

## 2026-09-07 Precision Workbench Acceptance Follow-Up IV

- **FIXED / WORKFLOW RESTORE:** Detail restore now loads the complete
  projected version chain and performs a direct second fetch for the original,
  base, and selected artifacts if a bulk fetch misses one. Historical version
  metadata is retained instead of being silently dropped; per-version
  annotation snapshots are indexed so switching `原 / 1 / 2 ...` can restore
  the corresponding annotation set. Records created before annotation
  snapshots existed remain unable to recreate text that was never persisted.
- **FIXED / CANVAS ZOOM:** Browser-conflicting `Ctrl+wheel` was replaced with
  `Shift+wheel`; middle-click reset and resize-handle anchoring remain intact.
  The visible hint text and static/browser contracts now describe Shift.
- **FIXED / SESSION CONTROLS:** On wide desktop layouts, display mode,
  修改前/修改后/对比, 图片全屏, and 工作台全屏 are now nested in one aligned
  control group. Narrow layouts retain responsive wrapping.
- **VERIFIED / REGRESSION:** Workflow and precision contracts passed `221`;
  browser gallery/canvas tests passed `6`; provider precision suites passed
  `170`; JavaScript syntax and static UI assertions passed; `git diff --check`
  reported no whitespace errors beyond existing line-ending warnings.

## 2026-09-07 Precision Workbench Acceptance Follow-Up III

- **VERIFIED / WORKFLOW RESTORE:** Restoring a history workflow now rebuilds
  the projected original plus every safely available result version, preserves
  parent/base/selected-version relationships, and restores the validated
  annotation snapshot associated with the predecessor canvas. Public history
  rows remain redacted; annotation snapshots are exposed only by the explicit
  workflow-detail projection. Older records without a snapshot can still
  restore their available version chain but cannot recreate annotation text
  that was never stored.
- **VERIFIED / LOCAL CANVAS INTERACTION:** Ctrl+wheel zoom retains the cursor
  anchor and middle-button reset remains available. The canvas resize handle
  is positioned in the scroll container's visible lower-right corner, so zoom
  and pan scroll offsets no longer carry it away or resize the canvas.
- **VERIFIED / LOCAL UI:** The annotation editor uses one compact title/object/
  confirm/close row; confirmed annotations use readable glass tiles; version
  shortcuts are upper-left ordered; image-only and workbench fullscreen share
  the display-control row; and the cutout algorithm control retains native
  dropdown semantics with a visible affordance.
- **VERIFIED / REGRESSION:** `tests/test_precision_workflow_history.py` and
  `tests/test_precision_edit_contract.py` passed `221`; provider precision
  suites passed `170`; Playwright gallery/canvas interaction tests passed `6`;
  JavaScript syntax and static precision UI assertions passed; `git diff
  --check` reported no whitespace errors (only existing CRLF warnings).
- **RETAINED BOUNDARY:** The user-confirmed `1792 x 1024` source yielding a
  `2048 x 1152` output is treated as endpoint behavior, not an exact-size
  promise. Any future upstream `ReadError` still requires a fresh,
  user-authorized laboratory retry; non-idempotent precision-edit POSTs remain
  deliberately non-retried to avoid duplicate billing.

## 2026-09-07 Precision Workbench Acceptance Follow-Up II

- **VERIFIED / LOCAL UI:** Removed the expanded-gallery title/instruction
  topbar. Gallery and workflow controls remain equal square-corner cards with
  the same surface treatment whether collapsed or expanded. The gallery now
  renders a wrapping, multi-row poster wall with internal vertical scrolling.
  Image-only and workbench-fullscreen actions share the session control row.
- **VERIFIED / LOCAL ANNOTATION FLOW:** The inspector's duplicate edit list is
  hidden. Confirmed annotation tiles own reopen and deletion flows; deletion
  requires an explicit confirmation and removes the same object that would be
  serialized into the generation payload. The canvas resize control is sticky
  within its visible scrollport so view zoom/pan does not carry it through the
  image.
- **VERIFIED / DIAGNOSIS AND FIX:** The sanitized local record at
  `2026-09-07 16:30:43` identifies a precision-edit `ReadError` after the
  request entered response reading for the selected `gpt-image2-bc` model. It
  is a transport/read-stage failure, distinct from the earlier strict output
  mismatch. Client cleanup now covers read/write transport errors; precision
  edits still do not auto-retry non-idempotent POST requests. UI recovery text
  distinguishes a `/models` connection check from an `/images/edits` request.
- **VERIFIED / CUTOUT AND SIZE UI:** Enabling local cutout refinement for the
  canvas selection reveals annotations, selects a valid box/brush region, and
  highlights the active tool. Strict resize guidance now states that a preset
  fills the form only; it does not authorize the endpoint to produce that size.
  Strict output validation remains fail-closed.
- **VERIFIED / REGRESSION:** `python -m py_compile providers/__init__.py`, JS
  syntax, precision UI/i18n Node checks, and the focused Python suite passed:
  `410 passed in 27.97s`. `git diff --check` reported no whitespace errors;
  only existing CRLF warnings were emitted.
- **RETAINED BOUNDARY:** A fresh, user-authorized laboratory retry is still
  required to prove the external endpoint no longer produces a `ReadError`.
  Local contract results must not be represented as a live upstream recovery.

## 2026-09-07 Precision Workbench UI Follow-Up

- **VERIFIED / LOCAL UI CONTRACT:** Precision generation now fills its command
  row after the runtime action wrapper mounts. The gallery trigger and workflow
  filter are reparented into a symmetric two-card control row, so workflow
  recovery remains available while the gallery wall is collapsed.
- **VERIFIED / LOCAL INTERACTION:** Confirming an annotation hides the floating
  editor and adds a compact, editable summary tile below generation; selecting
  a tile reopens that annotation. The editor remains a separate compact drag
  surface while active. Tool shortcuts now include `F` for workbench fullscreen
  and use capture-phase key handling while excluding editable controls.
- **VERIFIED / LOCAL LAYOUT:** Gallery results use a wrapping poster wall with
  internal vertical overflow rather than a horizontal-only strip. The inspector
  resize handle is constrained to a narrow left-edge separator, and Ctrl+wheel
  over a canvas resize handle clears any residual drag instead of resizing it.
- **VERIFIED / REGRESSION:** JavaScript syntax, precision UI/i18n Node checks,
  and focused Python suites passed: `240` gallery/contract/cutout tests plus
  `169` provider precision tests. `git diff --check` reported no whitespace
  errors (only existing CRLF and temporary-directory warnings).
- **RETAINED BOUNDARY:** This is automated/local visual-contract evidence. A
  headed human acceptance pass is still required for the exact composition,
  splitter hit area, keyboard behavior, and a live annotated image workflow.

## 2026-09-06 Precision-Edit Preserve Preflight Fix

- **VERIFIED / ROOT CAUSE:** The latest repeated failure was a local
  preflight rejection (`precision_edit_size_capability_unknown`) for a model
  already confirmed for precision editing but missing an optional supported-
  size list. No upstream HTTP request was made. Historical successful edits
  and the later strict-size/output-mismatch records remain separate evidence.
- **FIXED / LOCAL CONTRACT:** Preserve mode now forwards the existing source
  canvas when the selected model is explicitly authorized for precision edit;
  an absent optional size list no longer blocks that path. Strict resize still
  requires an explicit declared target size and remains fail-closed.
- **VERIFIED / REGRESSION:** `tests/test_provider_precision_alias_compat.py`
  and `tests/test_provider_precision_contract.py` passed; precision UI/i18n,
  JavaScript syntax, and diff checks passed. The reusable local skill
  `precision-edit-error-diagnosis` was added under the user Codex skills
  directory with a redacted diagnosis workflow.
- **RETAINED BOUNDARY:** This fixes the local gate; a fresh live upstream
  success for the user's current endpoint/model and source image still needs
  an authorized retry in the laboratory.

## 2026-09-06 Precision Workbench And Workflow-History Acceptance (latest)

- **USER-CONFIRMED / HEADED WORKBENCH ACCEPTANCE:** The current precision
  workbench completed two successful sequential results. The session gallery
  showed a result count of `2`, the selected version advanced to the second
  result, and the task reached its completed state. This closes the earlier
  headed sequential-workbench boundary. No user image, prompt, raw log,
  endpoint, or credential is retained in this record.
- **VERIFIED / LOCAL PRODUCT DELIVERY:** The workbench now places a gallery
  Pill below the toolbar and keeps it collapsed by default. The expanded
  surface includes a redacted cross-session workflow browser, a two-level
  operation-card hierarchy, restoration into the precision workbench, and
  date-range plus workflow filtering. Public history projections omit prompts,
  image bytes, hashes, absolute paths, raw logs, and credentials.
- **VERIFIED / REGRESSION:** The complete local Python suite passed `1440`
  tests. Precision UI and i18n Node contracts, JavaScript syntax validation,
  and the repository diff check also passed.
- **RETAINED BOUNDARIES:** Native strict-size success for a non-square target
  remains unverified. When a workflow's original source image was not
  persisted, history restoration can load only the latest available edited
  result. Cutout execution is technically covered, but real-image quality for
  legs, hair, soft edges, and complex backgrounds still requires authorized
  human samples.

## 2026-09-06 Authorized Local Precision-Edit Backend Acceptance

- **VERIFIED / REAL UPSTREAM SEQUENTIAL EDIT:** In the local laboratory, a
  non-sensitive generated geometry image with one minimal rectangle annotation
  completed through the configured `gpt-image2-b` precision-edit path. The
  returned RGB PNG was stored at `1024x1024`. That stored result was then used
  as the input to one further minimal annotated edit through the same provider;
  the second task also completed and stored a `1024x1024` RGB PNG. No user
  image, user prompt, endpoint, credential, or raw provider response is kept
  in this evidence record.
- **VERIFIED / TARGETED REGRESSION:** Provider precision/strict-size/extension
  tests passed `358`; precision UI-static and i18n checks also passed. The
  previously recorded full-suite result remains `1435` Python tests.
- **RETAINED BOUNDARY:** This proves two sequential backend calls with the
  first generated result as the second input. It does not substitute for a
  headed workbench interaction that uses the `设为下一次底图` control, appends
  both results to the current session gallery, and displays its prompt-history
  chunks in the image viewer.
- **RETAINED STRICT-SIZE BOUNDARY:** The successful evidence is square
  preserve-size editing. There is still no native strict-size PASS for a
  non-square target; mismatch responses remain rejected before they can enter
  the editable version or gallery result path.

## 2026-09-06 Precision Edit Current Acceptance Follow-Up

- **VERIFIED / STRICT FAIL-CLOSED:** A user-approved `1792x768` request returned
  `2048x864` from the configured upstream. Strict mode rejected it without
  replacing the editable base or creating a result version. This proves the
  failure boundary, not native strict-size success.
- **VERIFIED / LOCAL REGRESSION:** The focused provider/alias/strict-size/gallery
  suites passed `176` tests. Precision i18n and UI static contracts also passed.
  The size-mismatch recovery text now honestly offers another target size or an
  explicit local-adaptation choice; it does not claim a stored upstream matrix.
- **VERIFIED / FULL REGRESSION:** The full local Python suite passed `1435` tests.
- **VERIFIED / LOCAL UI:** A dedicated `图片全屏` action now sits beside the
  complete-workbench fullscreen action. It opens the selected session image and
  its prompt-history chunks without submitting a generation; responsive browser
  checks cover the two actions at mobile, compact, and desktop widths.
- **VERIFIED / LOCAL CUTOUT TECHNICAL GATE:** Current U2-Net and user-imported
  MODNet adapters each passed the synthetic full-body offline gate with CPU
  execution, blocked Python networking, same-size RGBA output, and alpha `0..255`.
- **VERIFIED / LAB CAPABILITY:** The running local capability endpoint now reports
  both U2-Net and MODNet as `ready` and executable with CPU support. BiRefNet,
  RMBG-2.0, and InSPyReNet remain unavailable and cannot be selected for a task.
- **UNVERIFIED / NEXT HUMAN GATES:** Native strict success for a non-square
  target and authorized human-image cutout quality for legs, hair, soft edges,
  and complex backgrounds remain open. The sequential workbench and
  real-result gallery boundary is closed by the newer acceptance record above;
  Release remains subject to the remaining evidence and packaging gates.

## 2026-09-05 Headed Annotation UAT PASS

- **VERIFIED / HEADED LOCAL UAT:** On a non-sensitive blue-and-green geometric
  test image, the loaded precision canvas created and then edited rectangle,
  ellipse, arrow, and brush annotations successfully at `937x920`. At
  `390x844`, the workbench had no horizontal overflow. No private asset was
  generated or accessed. This is a narrow headed UI observation associated
  with `7677073`; it does not verify provider output, a second precision edit,
  or real-person cutout quality.
- **UNVERIFIED / RETAINED BOUNDARIES:** Native strict success, the second
  annotated edit/session-version path, and authorized real-person cutout
  quality acceptance remain unverified. An earlier `1792` timeout was followed
  by a later strict rejection when the upstream returned `2048x864`.

## 2026-09-05 Precision Edit Evidence Ledger Refresh

- **VERIFIED / REAL UPSTREAM REQUEST:** The `1024` precision-edit probe
  completed successfully with a real `1024x1024` output. This is a narrow
  upstream success, not a general strict-size acceptance.
- **VERIFIED / STRICT FAIL-CLOSED:** The `1536` probe returned `1376x768`.
  Strict preserve validation rejected that output; it did not replace the
  editable base image.
- **UNVERIFIED / THIS RUN:** The `1792` probe ended in `ReadTimeout`, so this
  run produced no verified upstream output for that target. It must not be
  recorded as a strict-size PASS.
- **VERIFIED / LOADED-CANVAS UAT TEST EVIDENCE:** Automated browser coverage
  completed the loaded precision-canvas interaction contract at `390x844`,
  `937x920`, and `1200x800`, including canvas hit targeting, middle-button
  zoom reset and pan, image-only fullscreen, source-menu bounds and keyboard
  interaction, and workbench fullscreen exit. This is test evidence, not a
  substitute for independent human acceptance.
- **VERIFIED / FOLLOW-UP COMMITS:** `b239eb2` (workspace controls),
  `fab6418` (UI transitions), `7677073` (loaded-canvas UAT gaps), and
  `71e159b` (temporary cutout PNG ignore rule) are the relevant 2026-09-05
  commits.
- **UNVERIFIED / RELEASE BLOCKERS:** The cutout structural gate, authorized
  human-image quality acceptance, and redistribution/packaging authorization
  remain incomplete. The Release remains blocked; no external size result,
  local UI test, or local runtime probe changes that decision.

## 2026-09-05 Restarted Dual-Algorithm Runtime Verification

- **VERIFIED / LAB RESTART:** The laboratory was restarted from the current
  worktree and returned HTTP `200` from `/api/runtime/status`, reporting GenBox
  `2.6.6` in development mode on port `8892` with runtime id
  `ad11247da77b`.
- **VERIFIED / REAL LOCAL REQUESTS:** After restart, the same stored gallery
  image was submitted separately with `u2net-human-seg-onnx` and
  `modnet-portrait-onnx`. Both returned HTTP `200`, the requested adapter id,
  same-size RGBA PNG output (`1792x1024`), and alpha extrema `(0,255)`.
  This closes the stale-process/algorithm-mismatch suspicion for the local
  laboratory.
- **QUALITY BOUNDARY:** The quality audit found U²-Net stable enough to remain
  the default. MODNet is technically executable but can leave background or
  remove foreground detail on complex samples; it remains experimental/local
  opt-in and is excluded from Release until broader authorized-sample quality,
  offline, and redistribution evidence is complete.
- **VERIFIED / REGRESSION:** The focused cutout, precision-edit, provider,
  strict-size, gallery, and model-manager suites passed `482` tests on this
  worktree.

## 2026-09-05 Current Cutout Capability Reconciliation (latest)

- **VERIFIED / LOCAL RUNTIME:** the running lab capability endpoint reports
  `u2net-human-seg-onnx` and `modnet-portrait-onnx` as executable. U²-Net
  remains the default; MODNet is an opt-in, locally executable alternative and
  uses the imported fixed checkpoint at
  `storage/models/cutout/modnet/modnet.onnx`.
- **VERIFIED / MODNET EVIDENCE:** the imported MODNet checkpoint is
  `6,632,188` bytes with SHA-256
  `92e49898c3e05a6d7a944fc67a8cb87c4aad754ffb6ebd949528c7d1105fee3a`.
  The capability response reports `available=true`, `executable=true`,
  `cpu_execution_provider=true`, and `license_confirmed=true` for this local
  installation. This proves local technical readiness only; it is not a
  portrait-edge quality acceptance or an upstream-provider result.
- **VERIFIED / CACHE REFRESH:** the static bundle now references
  `app-all.js?v=46`, so the capability picker is refreshed on reload.
- **BOUNDARY:** BiRefNet, RMBG-2.0, and InSPyReNet remain fail-closed
  candidates until fixed weights, redistribution terms, offline inference,
  and portrait-edge quality evidence are complete. MODNet also remains
  excluded from the Release until disconnected CPU execution, authorized
  human-sample edge-quality evidence (legs, hair, and semi-transparent edges),
  regression evidence, and the final compliance checklist are recorded. This
  local result is not evidence of real upstream GPT Image 2 success.

**Reconciliation note:** entries below dated before this record that say the
worktree had no MODNet checkpoint or that U²-Net was the only executable
adapter are historical snapshots from before the fixed MODNet import and
runtime probe. They remain useful as an audit trail but are superseded by this
dated live capability result; they must not be used as the current capability
or Release decision.

## 2026-09-04 MODNet Fixed-Checkpoint Runtime Smoke

- **VERIFIED / LOCAL RUNTIME:** In the isolated local runtime, the fixed
  `onnx-community/modnet-webnn` quantized checkpoint was imported through the
  MODNet manager with explicit Apache-2.0 provenance and size/SHA-256/MD5
  checks. The model is stored under the ignored runtime path
  `storage/models/cutout/modnet/modnet.onnx`; it is not a tracked Release
  artifact.
- **VERIFIED / CPU SMOKE:** ONNX Runtime CPU created a session and processed a
  stored gallery PNG into a same-size RGBA PNG (`1024x1024`) with alpha
  extrema `(0, 255)` in about `0.381s`. This is technical execution evidence,
  not a portrait-edge quality acceptance.
- **BOUNDARY:** The default registry and U²-Net path remain unchanged. MODNet
  must stay opt-in/unavailable for Release until断网运行、授权真人样本的腿部/发丝/半透明边缘验收、回归证据和最终合规清单全部完成。
- **VERIFIED / REGRESSION:** The full Python suite passed `1415` tests on
  2026-09-04; the focused MODNet and precision-edit suites passed as part of
  that run.

## 2026-09-05 Manual Edit Toolbar Narrow-Layout Fix

- **FIXED / LOCAL UI:** The manual-edit/eraser control now wraps its label
  safely in narrow inspectors instead of being clipped on one line. This is a
  CSS-only change and does not alter cutout, precision-edit, or provider logic.
- **VERIFIED / REGRESSION:** `node tests/test_precision_edit_ui.mjs` passed and
  `git diff --check` passed.

## 2026-09-05 Multi-Algorithm Cutout Availability Audit

- **VERIFIED / LOCAL REGRESSION:** Full Python suite passed `1413` tests;
  cutout registry, ONNX adapters, InSPyReNet candidate, precision-edit
  contracts, and strict-size tests remain green.
- **VERIFIED / MODEL INVENTORY:** The worktree contains one actual cutout
  checkpoint, `storage/models/cutout/u2net_human_seg.onnx` (175,997,641 bytes,
  SHA-256 `01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c`).
  No MODNet, InSPyReNet, BiRefNet, or RMBG-2.0 checkpoint is present or
  tracked.
- **VERIFIED / RUNTIME:** The lab capability endpoint reports U²-Net as the
  only `available=true` and `executable=true` adapter. The other algorithms
  remain `UNVERIFIED`/`unavailable` by design.
- **BOUNDARY:** Parallel adapter and authorization work may continue in
  isolated branches/modules, but no second algorithm may enter the executable
  selector or Release until fixed weights, redistribution permission,
  SHA-256, offline CPU inference, transparent-PNG output, and portrait-edge
  quality evidence are all recorded.
- **VERIFIED / LOCAL SMOKE:** A stored RGB gallery image submitted through the
  JSON `image_data` contract returned HTTP `200`, a transparent PNG, and a new
  gallery result from `u2net-human-seg-onnx` (`1254x1254`, 2026-09-05). A
  previously cutout/transparent input correctly failed closed with
  `cutout_output_alpha_invalid`; this is an input-quality guard, not a model
  availability failure.

## 2026-09-04 Precision Edit And Cutout Regression Recheck

- **VERIFIED / LOCAL REGRESSION:** Full Python suite passed `1413` tests;
  precision-edit UI/static contracts, cutout installer UI assertions,
  JavaScript syntax, and `git diff --check` also passed.
- **VERIFIED / LOCAL RUNTIME:** `GET http://127.0.0.1:8892/api/runtime/status`
  returned HTTP `200`, reporting GenBox `2.6.6` in development mode. The
  cutout capability endpoint reports U²-Net as the only `ready` executable
  adapter.
- **VERIFIED / LOCAL SMOKE:** A real stored gallery PNG was submitted to the
  running `/api/image-tools/cutout` endpoint and returned a transparent
  `1024x1024` PNG from `u2net-human-seg-onnx`. This verifies the local U²-Net
  request path only; it does not establish human-edge quality or upstream
  precision-edit success.
- **UNVERIFIED / RELEASE BOUNDARY:** MODNet, InSPyReNet, BiRefNet, and
  RMBG-2.0 remain candidate adapters without a fixed redistributable
  checkpoint, complete license/hash evidence, offline CPU smoke, and real
  portrait-edge quality acceptance. Real upstream precision-edit and strict
  16:9/21:9 generation still require headed-browser evidence.

## 2026-09-04 Optional Cutout Import Runtime Refresh

- **VERIFIED / LOCAL CONTRACT:** A successful MODNet upload now triggers a
  fresh CPU/runtime probe and replaces only the MODNet unavailable placeholder
  when the imported manifest, license, model hashes, dependencies, and ONNX
  session all pass. The default U²-Net adapter is untouched.
- **VERIFIED / REGRESSION:** MODNet import/route/registry/model-manager suites
  pass (`48` focused tests); the broader cutout, strict-size, and precision
  contract run passed `328` tests.
- **UNVERIFIED / BOUNDARY:** This worktree has no approved MODNet checkpoint;
  real MODNet execution and portrait-edge quality remain unavailable and no
  candidate algorithm is enabled for Release.

## 2026-09-04 MODNet Import/Runtime Path Alignment

- **FIXED / LOCAL CONTRACT:** The optional MODNet adapter now derives its
  default checkpoint path from the same canonical directory and filename used
  by the MODNet import manager (`storage/models/cutout/modnet/modnet.onnx`).
  An import can therefore be discovered by the adapter without changing the
  verified U²-Net path.
- **VERIFIED / REGRESSION:** MODNet import, adapter, and model-manager tests
  passed `23` tests; `git diff --check` passed.
- **BOUNDARY:** No MODNet checkpoint is installed in this worktree, so MODNet
  remains `UNVERIFIED`/`executable=false` until license, fixed SHA-256,
  offline CPU inference, and real portrait-edge quality evidence are complete.

## 2026-09-04 Precision Edit Regression Resume

- **VERIFIED / LOCAL REGRESSION:** The focused precision-edit, strict-size,
  session-gallery, provider-contract, and cutout suites passed `280` tests;
  the full Python suite passed `1410` tests. Static precision-edit and cutout
  installer checks also passed, and `git diff --check` reported no whitespace
  errors.
- **VERIFIED / LOCAL RUNTIME:** The lab endpoint returned HTTP `200` from
  `/api/runtime/status`, reporting GenBox `2.6.6`, `DEV`, runtime head
  `a9c8cde` on port `8892`.
- **VERIFIED / UI:** Cutout model details now default to collapsed and expand
  only on user action; the change does not alter the cutout runtime or U²-Net
  selection path.
- **UNVERIFIED / RELEASE BLOCKER:** U²-Net remains the only executable cutout
  adapter. MODNet and InSPyReNet remain candidate adapters until fixed,
  redistributable weights, offline inference, and real portrait-edge quality
  evidence are complete. Real upstream precision-edit and strict 16:9/21:9
  output still require independent headed-browser evidence.

## 2026-09-04 Multi-Algorithm Cutout Registry Expansion

- **VERIFIED / LOCAL CONTRACT:** Added the isolated InSPyReNet fail-closed
  adapter and registered it in the shared cutout registry. The capability
  endpoint can now describe U²-Net, MODNet, BiRefNet, RMBG-2.0, and InSPyReNet
  without importing optional runtimes or downloading weights.
- **UNVERIFIED / RELEASE BLOCKER:** InSPyReNet remains
  `available=false`/`executable=false` until a fixed checkpoint, license
  provenance, SHA-256, offline CPU inference, and portrait-edge quality pass
  are recorded. U²-Net remains the only verified executable default.
- **VERIFIED / REGRESSION:** Registry, InSPyReNet, and MODNet route tests pass
  (`26 passed`); `git diff --check` passes. This does not verify real upstream
  precision-edit requests or visual cutout quality.

## 2026-09-04 Multi-Algorithm Cutout Gate

- **VERIFIED / LOCAL CONTRACT:** The cutout selector and request contract now
  support switching among multiple `executable=true` adapters; unverified
  candidates remain visible only as unavailable details and all-unavailable
  states fail closed. `node tests/test_cutout_model_install_ui.mjs` and
  `node tests/test_precision_edit_ui.mjs` passed.
- **VERIFIED / CANDIDATE PROBE:** A community MODNet ONNX file was loaded by
  `onnxruntime` and produced a valid synthetic RGBA matte (`25,897,433` bytes,
  SHA-256 recorded in `docs/CUTOUT-ALGORITHM-FEASIBILITY-20260904.md`).
- **UNVERIFIED / RELEASE BLOCKER:** The official `ZHKKKe/MODNet` README states
  that its code, model, and demos are Apache-2.0. The fixed ONNX file probed
  here is nevertheless a community conversion, and no independent
  redistribution declaration for that binary has been established. It remains
  `MODNET_DESCRIPTOR` + `UnavailableCutoutAdapter`, `available=false`,
  `executable=false`. BiRefNet and RMBG-2.0 remain unavailable for the same
  evidence/weight gate. The only verified executable algorithm is U2Net.
- **VERIFIED / REGRESSION:** The full Python suite passed `1382` tests on
  2026-09-04 after fixing the calendar browser fixture to dispatch native
  handlers while the static panel is hidden. The change does not relax the
  production visibility or interaction rules.
- **VERIFIED / CANDIDATE AUDIT:** The independent InSPyReNet review in
  `docs/CUTOUT-INSPYRENET-FEASIBILITY-20260904.md` confirms MIT code but no
  independently licensed, fixed-SHA checkpoint with a fully offline runtime.
  InSPyReNet therefore remains `UNVERIFIED`, unavailable, and excluded from
  the Release until weight provenance, dependencies, and real portrait-edge
  quality are closed.
- **VERIFIED / OPT-IN ADAPTER:** An isolated MODNet ONNX adapter now exists at
  `image_tools/cutout_modnet.py` with five focused tests. It requires a
  user-provided checkpoint, a complete size/SHA-256/MD5 manifest, and explicit
  license confirmation before it can report `executable=true`; it is not
  registered in the default registry and is excluded from Release artifacts.
- **VERIFIED / RUNTIME PROBE:** The local laboratory capability endpoint
  `/api/image-tools/cutout/capabilities` returned HTTP 200 and reported U²-Net
  as `available=true`/`executable=true`; MODNet, BiRefNet, and RMBG-2.0 were
  correctly reported as `UNVERIFIED`/non-executable. This is local runtime
  evidence only and does not verify any upstream image-edit request.

**Resume:** To enable a second algorithm, obtain a fixed weight with explicit
  redistribution permission, record its license and SHA-256, add an isolated
  adapter plus offline inference tests, then run the capability endpoint and
  headed/manual quality acceptance before changing it to `VERIFIED`.

## 2026-09-04 Precision Session Gallery Calendar Filter

- **VERIFIED / LOCAL UI:** The current-session Precision Edit gallery now uses
  a collapsed date-filter trigger. Its popover provides a seven-column local
  calendar, highlighted dates with generated results, muted empty dates, month
  navigation, single-day/range selection, outside-click/Escape closing, and
  quick ranges for the recent 3/5 days plus the current natural week, month,
  quarter, half-year, and year.
- **VERIFIED / LOCAL COMPATIBILITY:** The existing date inputs remain as hidden
  state fields, so the prior date filtering and clear behavior continue to use
  the same filtering function.
- **VERIFIED / LOCAL REGRESSION:** `node --check static/js/app-all.js`,
  `node tests/test_precision_edit_static_contract.mjs`,
  `python -m pytest -q tests/test_precision_session_gallery_browser.py`, and
  `git diff --check` passed after the calendar change.
- **BOUNDARY:** This is a local UI change. It does not change the external
  provider, real upstream precision-edit success, strict provider dimensions,
  or cutout algorithm availability.

**Last updated:** 2026-09-04
**Current branch:** `codex/phase7-campaign-20260820`
**Current phase:** Phase 9 Sender Push Source Cleanup (User-Selected) - **In Progress (receiver-grant shipped in v2.6.1 2026-08-21; sender PR #26 OPEN/MERGEABLE/UNSTABLE; no maintainer review; Vercel authorization failure is external state and cannot be handled automatically; clean E2E gates passed for receiver)**
**Previous phase:** Phase 8 Upstream Delivery - **In Progress (proposal PRs open, awaiting upstream response)**

## 2026-09-04 Precision Session Gallery Confirmation

- **VERIFIED / LOCAL LAB:** `GET http://127.0.0.1:8892/api/runtime/status`
  returned HTTP `200`; the development runtime reports GenBox `2.6.6`.
- **VERIFIED / LOCAL REGRESSION:** `python -m pytest -q` passed `1382` tests
  in `73.35s`; the focused session-gallery browser suite passed `2` tests and
  the precision-edit static/UI contracts passed.
- **VERIFIED / LOCAL INTERACTION:** The focused gallery browser coverage now
  dispatches a thumbnail click and confirms the selected version changes to
  the clicked result before applying date filtering.
- **VERIFIED / SCOPE:** The blank area below the annotation canvas is the
  current-session Precision Edit gallery, with thumbnails, version switching,
  date filtering, clear-filter, empty state, and split prompt history.
- **VERIFIED / HEADED AX TREE:** The live loopback workbench exposes the
  `当前会话结果` region below the canvas with its result count, date fields,
  clear action, and list semantics; the same headed page exposes the version
  controls, fullscreen action, and annotation toolbar without a missing gallery
  region.
- **BOUNDARY:** This confirms local behavior only. Real upstream generation,
  strict provider 16:9/21:9 output, second-pass provider editing, and cutout
  quality remain separate external/manual acceptance items.

## 2026-09-04 Precision Session Gallery Layout And Toolbar Regression Fix

- **VERIFIED / LOCAL UI:** The lower blank area of the Precision Edit stage is
  the current-session gallery (`当前会话结果`). It renders generated result
  thumbnails, selected-version switching, result count, date-from/date-to
  filtering, clear-filter, empty state, and split prompt history. It is scoped
  to the current editing session and does not replace the media library.
- **FIXED / LOCAL CSS:** The manual-edit toolbar now assigns the label and
  eraser/tool group to separate grid columns on wide layouts, with style
  controls on the second row. This removes the previously observed overlap;
  narrow layouts retain their responsive one-column behavior.
- **FIXED / LOCAL UI:** Prompt-history expansion now opens the last visible
  prompt after date filtering, instead of comparing against the unfiltered
  entry count.
- **VERIFIED / LOCAL REGRESSION:** `python -m pytest -q` passed `1382` tests
  in `73.35s`; focused gallery, static contract, UI, JavaScript syntax, and
  `git diff --check` validations also passed.
- **VERIFIED / LOCAL LAB:** On 2026-09-04, `GET
  http://127.0.0.1:8892/api/runtime/status` returned HTTP `200` and reported
  GenBox `2.6.6` in `dev` mode on port `8892`, runtime head `a9c8cde`.
- **BOUNDARY:** This confirms the local gallery and layout behavior only. Real
  upstream precision-edit generation, strict 16:9/21:9 provider output,
  second-pass editing on a generated result, and cutout quality remain
  separate external/manual evidence requirements.

## 2026-09-04 Historical Precision Edit Acceptance Audit

## 2026-09-04 Precision Session Gallery And Image Viewer Follow-Up

- **VERIFIED / HEADED LOCAL CHECK:** A headed Chromium pass against the live
  loopback lab rendered the session gallery empty state and measured the
  manual-edit section at `372x100px`, confirming the controls occupy a stable
  two-row region without clipping. Evidence screenshot:
  `screenshots/local-ui/precision-headed-20260904.png`.
- **VERIFIED / LOCAL UI FIX:** The compact manual-edit toolbar now keeps its
  helper description screen-reader-only, so the visible controls remain in a
  stable two-row layout instead of being pushed into a clipped third row.
- **VERIFIED / LOCAL REGRESSION:** Added browser coverage for the successful
  generation-to-session-gallery write path (source session plus `local_path`
  result). `python -m pytest -q
  tests/test_precision_session_gallery_browser.py` now passes `2` tests.
- **VERIFIED / LOCAL UI:** The lower blank area is implemented as the
  current-session Precision Edit gallery. It supports result thumbnails,
  selected-version switching, date-from/date-to filtering, clear-filter,
  empty state, responsive narrow-layout scrolling, and prompt-history display.
- **VERIFIED / LOCAL UI:** Image-only fullscreen now opens from the current
  comparison image (including double-click), displays the selected image
  caption and original/edit/multi-round prompt history in split chunks, and
  supports copy, Escape/background close, and wheel zoom with middle-click
  reset. The existing media-library lightbox entry remains separate.
- **VERIFIED / LOCAL REGRESSION:** `python -m pytest -q` passed `1382` tests;
  `node tests/test_precision_edit_static_contract.mjs`,
  `node tests/test_precision_edit_ui.mjs`, `node --check static/js/app-all.js`,
  and `git diff --check` passed.
- **VERIFIED / LOCAL LAB:** After a source-aware restart, the loopback lab
  returned HTTP 200 and reported GenBox `v2.6.6` in development mode on port
  `8892`.
- **BOUNDARY:** The gallery and viewer are locally verified UI/contract
  behavior. Real upstream image generation, automatic result persistence from
  a provider response, and headed-browser generation with real user images
  remain separate external evidence requirements.

- **VERIFIED / LOCAL:** The lower blank area is now a current-session Precision
  Edit gallery. It renders result thumbnails, highlights the selected version,
  switches the main comparison view on click, supports date-from/date-to
  filtering, and shows split prompt history. The date filter is wired through
  `renderPrecisionSessionShowcase()` and uses each entry's `createdAt` value.
- **VERIFIED / LOCAL:** The historical UI/code requests for two-line narrow
  manual controls, linked 1K/2K/4K ratio presets and custom preset handling,
  wheel zoom with middle-click reset, chained-version base selection, model
  visibility controls, and documentation entry points are present in the
  current worktree.
- **GAPS FOUND:** The cutout registry has only U2Net executable; MODNet,
  BiRefNet, and RMBG-2.0 remain unavailable adapters pending fixed weights,
  dependency and license evidence.
- **HUMAN / EXTERNAL EVIDENCE NEEDED:** Real `gpt-image2-b` precision-edit
  requests, strict upstream 16:9/21:9 output, cutout leg quality, a second
  edit on a generated version, and headed-browser visual/interaction checks
  still have no current independent PASS. This audit therefore does not mark
  the whole historical request complete or release-ready.

## 2026-09-04 Precision Edit Strategy And Local Selection Follow-Up

- **VERIFIED / LOCAL IMPLEMENTATION:** Precision Edit now exposes explicit
  page-session controls for `fine`, `standard`, and `fast` processing, with
  `standard` as the default. It also exposes `annotation` versus `local`
  selection semantics and a bounded `0-64px` local-selection feather control.
- **VERIFIED / LOCAL CONTRACT:** The backend rejects invalid strategy/mode/
  feather values, rejects local mode without a rectangle, ellipse, or brush
  region, and rejects the new fields outside `mode=precision_edit`. Pure
  resize remains the no-annotation envelope and cannot use local selection.
- **VERIFIED / LOCAL PROVIDER BOUNDARY:** Provider transport remains the
  existing allowlisted OpenAI-compatible multipart profile. Strategy, local
  selection guidance, bounded feather guidance, and person/leg protection are
  appended as constrained prompt instructions. Local selection is explicitly
  described as model guidance, not a verified pixel mask.
- **VERIFIED / LOCAL REGRESSION:** Precision/provider/alias contract tests
  passed `497`; the full Python suite excluding browser and release-packaging
  environment-sensitive modules passed `1295`, and all `9` MJS contract suites,
  JavaScript syntax checks, Python compilation, and `git diff --check` passed.
- **VERIFIED / FULL LOCAL REGRESSION:** With the repository's Python 3.14
  runtime (`C:\Python314\python.exe`), the complete Python suite passed `1350`
  tests in `71.29s`, including release-packaging and browser modules. An
  earlier `pytest` command used the unrelated Python 3.11 executable and was
  not used as final evidence.
- **UNVERIFIED / EXTERNAL BOUNDARY:** No real paid Provider precision-edit
  request, manual browser acceptance, or VPS operation was performed. The new
  prompt constraints therefore remain locally tested behavior rather than
  real upstream image-quality evidence.
- **BOUNDARY / RESUME:** Existing uncommitted work and test artifacts were
  preserved. Continue from the current worktree; rerun the focused commands
  above before any release or upstream claim.

## 2026-09-03 Wave 0 Baseline (local clock 2026-09-04 +08:00)

- **VERIFIED / LOCAL LAB:** `./start-lab.ps1 -Action restart -Background`
  restarted only the local lab. `http://127.0.0.1:8892/` and
  `/api/runtime/status` both returned HTTP `200`; runtime reported GenBox
  `v2.6.6`, `dev` mode, port `8892`, and HEAD `a9c8cde`.
- **VERIFIED / LOCAL REGRESSION:** the current full Python suite passed `1325`;
  focused provider/inpaint/precision tests passed `149`, all provider tests
  passed `289`, and Python compile, JavaScript syntax, and `git diff --check`
  passed.
- **EVIDENCE:** detailed command output and the pre-existing uncommitted-file
  inventory are recorded in
  `docs/PHASE9-10-WAVE0-BASELINE-20260903T173700Z.md`.
- **BOUNDARY:** no cleanup, revert, commit, tag, Release, VPS access, or
  production mutation was performed. Real upstream Provider precision-edit,
  cutout inference, and headed-browser acceptance remain **UNVERIFIED**.

## 2026-09-03 Local Error-Safety Follow-Up

- **VERIFIED / LOCAL LAB:** `.\start-lab.ps1 -Action start -Background` reported
  the owned lab already running at `127.0.0.1:8892`. Read-only probes returned
  HTTP `200` for
  `/`, `/api/runtime/status`, and `/api/image-tools/cutout/capabilities`; the
  runtime reported `v2.6.6` in `dev` mode and cutout reported
  `available=true`, `executable=true`, `state=ready`.
- **VERIFIED / PROVIDER ERROR REDACTION:** `_friendly_generation_error()` now
  applies provider-aware redaction before taking a bounded 200-character
  technical excerpt. Configured provider keys and generic Bearer, URL-userinfo,
  query-token, JSON-field, and prefixed-key patterns remain masked. Multi-endpoint
  summaries keep their bounded per-endpoint status evidence.
- **VERIFIED / LOCAL TESTS:** provider/error-focused coverage passed `44`; the
  current provider safety/precision/inpaint/transport set passed `267`; the
  full repository suite excluding the Docker Bash harness passed `1278`.
  All `9` MJS contract suites, five JavaScript `node --check` checks,
  `python -m py_compile providers/__init__.py`, and `git diff --check` passed.
- **UNVERIFIED / LOCAL HARNESS:** the direct full-suite run reached `1313`
  passing tests, with `6` failures isolated to
  `tests/test_release_packaging.py`: this machine resolves `bash` to
  `C:\Windows\System32\bash.exe`, which returns an
  `E_ACCESSDENIED`/UTF-16 payload instead of the expected smoke-script output.
  No application or provider test failed; rerun those six checks on a host with
  a compatible Bash runtime.
- **BOUNDARY / RESUME:** no Provider request, VPS action, production mutation,
  cleanup, commit, tag, Release, or push was performed. Real Provider precision
  edit and user-led browser acceptance remain **UNVERIFIED**; preserve the
  existing release and isolated-lab boundaries for the next session.

## 2026-09-03 Local Continuation Verification

- **VERIFIED / LOCAL LAB:** after source-change detection required a safe lab
  restart, `./start-lab.ps1 -Action restart -Background` restarted only the
  local GenBox lab. Read-only probes returned HTTP `200` for `/` and
  `/api/runtime/status`; the runtime reported version `2.6.6`, `dev` mode,
  port `8892`, and HEAD `a9c8cde`.
- **VERIFIED / LOCAL REGRESSION:** the focused precision/provider contract set
  passed `450`; the full Python suite passed `1321` in `71.32s`. All MJS
  contract suites, `node --check static/js/app-all.js`, Python compilation, and
  `git diff --check` passed.
- **BOUNDARY:** this continuation changed no implementation or release
  identity. Real Provider precision-edit success, real cutout inference, and
  independent user-led browser acceptance remain **UNVERIFIED**.

## v2.6.6 release evidence (updated 2026-09-03)

- **VERIFIED / LOCAL PRECISION AND CUTOUT 2026-09-03:** implicit
  `gpt-image2-*` matching is removed; Precision Edit accepts persisted
  capability/alias metadata or an explicit, revocable `gpt-image-2`
  compatibility confirmation and otherwise fails closed. Cutout attention
  states force details open without overwriting the remembered ready-state
  preference, and focus is restored before details are hidden.
- **VERIFIED / FINAL LOCAL GATE 2026-09-03:** the full repository suite passed
  `1313` tests in `86.58s`; release-packaging coverage passed `42` tests in
  `15.14s` after the candidate commit. Both
  `tests/test_precision_edit_ui.mjs` and
  `tests/test_cutout_model_install_ui.mjs` passed, as did the applicable
  `node --check` checks, Python `py_compile`,
  `python scripts/build_readme_lab.py --check`, and `git diff --check`.
  Independent review of the implementation and evidence returned `PASS`.
- **VERIFIED / LOCAL LAB 2026-09-03:** the root page,
  `/api/runtime/status`, and cutout capability endpoint each returned HTTP
  `200` on the loopback development service at port `8892`; runtime status
  reported GenBox `v2.6.6` in development mode and cutout reported `ready`.
- **VERIFIED / PRECISION UI AND README SCREENSHOT 2026-09-03:** the `sr-only`
  UI bug is fixed; `tests/test_precision_edit_ui.mjs`, the applicable
  `node --check`, and `198` focused Python tests passed. The final public
  Precision Edit screenshot is `1600x1000`; both README and sanitized copies
  have SHA-256
  `ba7e44693fc6d718cb04e49c14092d00e752ab73c7b902a5038ea12012e61993`.
  Its top action area is visibly rendered, assistive-only guidance is correctly
  hidden, the ready model panel is collapsed, and the composite contains no
  sensitive data.
- **VERIFIED / LOCAL CUTOUT MODEL 2026-09-03:** the separately installed
  `u2net_human_seg.onnx` matched `175997641` bytes and SHA-256
  `01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c`;
  capability probing and a synthetic local ONNX inference passed. The model is
  not tracked in Git, bundled in GenBox, or present in a GenBox Release asset.
- **VERIFIED / GITHUB CANDIDATE 2026-09-03:** commit
  `788924de268728e8a07d792d5f7495fdfe7f3f67` was fast-forward pushed to
  `codex/phase7-campaign-20260820`. GenBox PR `#9`, titled
  `release: merge v2.6.6 campaign and precision follow-up`, remains `OPEN` and
  `MERGEABLE`. Master PR Quality Gate run `33743177728`, job
  `Test pull request`, completed successfully in `1m38s` against exact head
  `221e1ac82480fb3651cbfd18ec9e49b8eaf3fd80`. This is verified hosted PR
  quality-gate evidence only; it is not a `master` merge or a new Release.
- **UNVERIFIED / EXTERNAL BOUNDARIES:** no real Provider precision-edit E2E was
  performed. Public model download, redistribution/commercial authorization,
  and real-photo acceptance remain `UNVERIFIED`. `liwei9745/rembg` remains an
  independent fork of `danielgatis/rembg`; the fork does not copy the parent's
  Release assets or grant model-weight rights.
- **BOUNDARY / RESUME:** no VPS, remote-container, production, or other network
  mutation was performed. The implementation and preceding evidence commit are
  pushed; only this hosted-CI record in `STATUS.md` awaits an evidence commit.
  PR `#9` has not been merged to `master`, approval is not complete, and no new
  GitHub Release has been created.

- **VERIFIED / HISTORICAL V2.6.5 TAG FAILURE 2026-09-03:** the annotated
  `v2.6.5` tag points to commit `aa8b5ecda13384ad5734dc077ea73c674c1e02cd`
  and was pushed. Desktop Clients run `33715658824` failed its three packaged
  runtime smokes because `pydantic_settings` was absent from each frozen
  executable. Docker Image run `33715658700` failed its HTTP startup smoke.
  No v2.6.5 GitHub Release, release assets, or GHCR image were created.
- **VERIFIED / V2.6.6 RELEASE IDENTITY 2026-09-03:** release commit
  `1f7bdb1058c7492d00cf74575fc5ecb83cbc6cb9` was pushed by fast-forward to
  `codex/phase7-campaign-20260820`. The annotated `v2.6.6` tag was created once
  and its remote dereference points exactly to that commit. No force push,
  retag, tag deletion, or tag-history rewrite was performed.
- **VERIFIED / HOSTED DESKTOP CI 2026-09-03:** natural tag-push run
  `33726318721` (`https://github.com/liwei9745/GenBox/actions/runs/33726318721`)
  started at `2026-09-03T07:05:03Z` and completed successfully at
  `2026-09-03T07:10:28Z`. The release identity and source-test jobs passed;
  Windows, macOS, and Linux each passed the packaged empty-directory runtime
  smoke and packaged-client smoke; the automatic Create Release job passed.
  The run was not manually dispatched or rerun.
- **VERIFIED / HOSTED DOCKER CI 2026-09-03:** natural tag-push run
  `33726318653` (`https://github.com/liwei9745/GenBox/actions/runs/33726318653`)
  started at `2026-09-03T07:05:03Z` and completed successfully at
  `2026-09-03T07:10:54Z`. The release identity gate passed, the exact Buildx
  image passed runtime-import and bounded HTTP readiness smokes, and the saved
  smoke-tested image was reloaded, identity-checked, and pushed without a
  rebuild. The run was not manually dispatched or rerun.
- **VERIFIED / GITHUB RELEASE 2026-09-03:** automatic Release
  `https://github.com/liwei9745/GenBox/releases/tag/v2.6.6` was published at
  `2026-09-03T07:10:18Z` as non-draft and non-prerelease. Its nine uploaded
  assets are the raw Windows, macOS, and Linux clients; the three corresponding
  platform ZIPs; `GenBox-Source-v2.6.6.zip`;
  `GenBox-Docker-Compose-v2.6.6.zip`; and `SHA256SUMS.txt`.
- **VERIFIED / RELEASE ASSET INTEGRITY 2026-09-03:** every one of the eight
  artifact lines in the published `SHA256SUMS.txt` matches the corresponding
  GitHub Release asset API SHA-256 digest. The checksum asset itself has API
  digest `sha256:c6b5fec2790e11ba24e167c06d456edd36f45861cdd157c3003840e62c5e93d5`.
  A fresh published Docker Compose ZIP download also matched
  `sha256:9ce22f428cf39f1ec6fc2799705ae4cbe6427339b955e0633d34184e87e833c6`
  and contained exactly the Compose/environment/quick-start files, public
  license and notices, and validated bcrypt 5.0.0, NumPy 2.4.3, and ONNX
  Runtime 1.24.3 license sidecars.
- **VERIFIED / GHCR V2.6.6 2026-09-03:** container package version ID
  `1203664665` was created at `2026-09-03T07:10:47Z`. Its immutable manifest
  digest is
  `sha256:8a4ec98e0dc274e546417996bd4a4f610e5364718080e38cde635dfe348b6fe6`
  and it carries tags `1f7bdb1`, `2.6.6`, `2.6`, and `latest`.
- **VERIFIED / SOURCE-EXPORT PRIVACY REMEDIATION:** the source export policy now
  excludes internal
  `.planning`, handoff/review, Phase 10 evidence, and the historical Phase 7
  secret-scan report through Git-native `export-ignore`; it does not edit those
  internal documents or remove public product, architecture, status, roadmap,
  or release documentation. Packaging regression coverage builds a real Git
  archive and rejects unexpected local-user paths, credential shapes, runtime
  vault/media data, ONNX/compiled/archive binaries, and non-minimal image
  metadata. The remediation was committed in the frozen release commit and
  reproduced from a fresh clean clone before the branch and tag were pushed.
- **VERIFIED / LOCAL EXPORT-POLICY REGRESSION 2026-09-03:** the packaging suite
  passed `33`; the full repository suite passed `1293`. Tests use a real Git
  fixture and controlled synthetic path/credential sentinels, confirm internal
  evidence is absent while public documentation remains present, and prove the
  scanner rejects an unexpected host-local path, credential, vault file, or
  ONNX payload. No remote operation was performed.
- **VERIFIED / CURRENT-CANDIDATE SOURCE-EXPORT RECHECK 2026-09-03:** the Docker
  log-redaction Bearer sentinel is assembled from source-safe shell fragments at
  runtime, so the redaction check still receives and removes the complete
  synthetic value without embedding a contiguous high-confidence credential
  shape in the public source. The unchanged source-export sanitizer scanned the
  current candidate view (`270` files, including `243` text files and `27`
  images) with zero violations. No scanner allowlist was broadened.
- **VERIFIED / LOCAL DESKTOP ONEFILE CONTRACT FIX 2026-09-03:** `build.py` now
  derives hidden-import smoke coverage from the complete direct runtime
  requirement set, explicitly includes the dynamically loaded Pydantic and
  multipart modules, collects required submodules/native data, and copies
  metadata for all `18` pinned direct distributions, including bcrypt. The
  generated spec and the PyInstaller CLI use the same hidden-import, submodule,
  native/data, and metadata lists. The smoke verifies every pinned version plus
  critical API symbols instead of checking only NumPy and ONNX Runtime.
- **VERIFIED / LOCAL WINDOWS ONEFILE 2026-09-03:** a fresh temporary Python
  `3.12.8` environment with PyInstaller `6.21.0` built `GenBox.exe`
  successfully (`67,631,005` bytes). From an empty directory with
  `PYTHONPATH`/`PYTHONHOME` removed and `PYTHONNOUSERSITE=1`, `--version`
  returned `GenBox 2.6.6`; `--runtime-import-smoke` returned `status=ok`, all
  `18` pinned distribution versions, `symbols=ok`, and
  `encrypted_openssh=ok`. The packaged client smoke also passed on ephemeral
  loopback port `53009`.
- **VERIFIED / LOCAL DESKTOP REGRESSION 2026-09-03:** final
  `python -m pytest -q tests/test_release_packaging.py` passed `42`; final
  `python -m pytest -q` passed `1302`; Python compilation passed for the
  version, build, license collector, and packaging-test modules. The desktop
  workflow now applies the same environment scrub to Windows, macOS, and Linux
  empty-directory checks.
- **VERIFIED / LOCAL ENCRYPTED OPENSSH KEY PACKAGING FIX 2026-09-03:** the v2.6.6
  runtime adds locally verified `bcrypt==5.0.0` for AsyncSSH's bcrypt KDF path.
  Desktop and Docker runtime smokes generate a synthetic encrypted Ed25519
  OpenSSH private key and require `asyncssh.import_private_key` with its
  synthetic passphrase to succeed. `bcrypt._bcrypt` is included explicitly
  without collecting the whole package. The complete installed Apache-2.0
  license is required in desktop, Docker-image, Docker Compose, and source
  packages. The collector accepts bcrypt's verified Windows
  `.dist-info/LICENSE` and Linux `.dist-info/licenses/LICENSE` wheel layouts,
  still requires exactly one matching file, and writes the fixed public path
  `THIRD_PARTY_LICENSES/bcrypt/LICENSE`. No real key or passphrase is used or
  persisted.
- **VERIFIED / HOSTED DESKTOP FOLLOW-UP:** the later natural v2.6.6 run recorded
  above established Windows, macOS, and Linux hosted success and created the
  published platform artifacts. The earlier local Windows result remains local
  evidence and is not presented as the hosted result.
- **VERIFIED / CI HTTP-SMOKE ROOT CAUSE 2026-09-03:** GitHub Actions run
  `33715658700` built image ID
  `sha256:e518cb38b5caefa5299a6d1b0fd0744fe57a8981f25eca412bd576de0020e972`
  once, and the runtime-import smoke completed at `2026-09-03T04:38:33.787Z`.
  The HTTP step began at `04:38:33.958Z`, and its first request failed at
  `04:38:34.178Z` with curl error 56, about 214 milliseconds after step start.
  The command retried connection-refused errors only, so the early connection
  reset ended the step without a second readiness attempt, health evidence, or
  container logs. The evidence identifies a startup-readiness race; that run
  does not contain evidence of an application crash.
- **LOCAL / CI CONTRACT FIX 2026-09-03:** the same-image HTTP smoke now uses a
  90-second bounded readiness loop. Every attempt verifies container state,
  liveness, and Docker health, then requires `/api/setup/status` to report
  `app_mode=prod` and `auth_required=true`. Retry delay is capped at five
  seconds. A stopped or unhealthy container ends the loop; terminal failure
  prints bounded, credential-redacted container logs and fails. The build-once,
  exact image-ID assertion, no-rebuild push, and per-tag image-ID gate remain
  unchanged.
- **VERIFIED / LOCAL EXACT-IMAGE HTTP SMOKE 2026-09-03:** an immutable Git
  archive of commit `aa8b5ecda13384ad5734dc077ea73c674c1e02cd` built local
  image ID
  `sha256:713279850f9b6fe75d87ad101178d9fb79d7b3892298ceeced5ce2b28c1e7c0a`.
  A uniquely named container created from that exact ID was still in Docker
  health `starting` on both probes and passed the production setup-status JSON
  contract on readiness attempt 2. The owned container was removed; no image
  was pushed and no shared container or deployment was changed.
- **VERIFIED / LOCAL CURRENT-SOURCE V2.6.6 DOCKER 2026-09-03:** the normal
  repository-root build now excludes `.pytest*` development artifacts from the
  Docker context and accepts the verified Linux bcrypt license metadata layout.
  It built exact image ID
  `sha256:7e9cb290ec41fec391e264887dfde474e346a06c5a1a3b1e23bf5796fdf55f1a`.
  The exact-image runtime smoke verified bcrypt `5.0.0`, NumPy `2.4.3`, ONNX
  Runtime `1.24.3`, the synthetic encrypted Ed25519 OpenSSH key round trip,
  `main` import, the bcrypt notice, and the physical Apache-2.0 license file.
  The standalone ownership-aware HTTP smoke passed the production setup-status
  contract on readiness attempt 2 through a local Docker Desktop loopback
  adapter, then removed its exact owned container. No image was pushed and no
  shared container or deployment was changed.
- **VERIFIED / LOCAL RELEASE-WORKFLOW SECURITY HARDENING 2026-09-03:** desktop,
  Docker, and pull-request workflows now default to `contents: read`; only the
  desktop Release job receives `contents: write`, and only the separate Docker
  publish job receives `packages: write`. Artifact upload in the pull-request
  workflow receives no repository-content write permission. All external
  actions in all three workflows are pinned to the full 40-character commits
  resolved read-only from their official `vX` tags on 2026-09-03, with tag
  comments retained for review. The Windows packaged-runtime smoke uses a
  unique GUID-owned `RUNNER_TEMP` directory and removes it in `finally`.
- **VERIFIED / LOCAL OWNERSHIP AND SAME-IMAGE CONTRACT 2026-09-03:** the Docker
  HTTP smoke now uses a random container name plus a per-run ownership label.
  Cleanup runs only after successful creation and only when both the recorded
  container ID and owner label match; collision or ownership mismatch refuses
  deletion. The read-only build job saves and uploads the exact smoked image;
  the publish job reloads it, verifies the original Buildx image ID, then tags,
  re-verifies, and pushes without rebuilding.
- **VERIFIED / LOCAL WORKFLOW REGRESSION 2026-09-03:** the final packaging suite
  passed `42`, including executable mocked Docker cases for connection reset
  followed by success, stopped container, readiness deadline, credential-log
  redaction, pre-existing name collision, ownership mismatch, and both verified
  bcrypt wheel license layouts. The suite also scans every workflow external
  action for its reviewed full commit and allows only repository-local `./`
  actions without a commit reference. The full repository suite passed `1302`.
  All three workflow YAML files parsed (`10` jobs total), all six Docker inline
  Bash blocks and the standalone smoke script passed Bash syntax validation,
  the Windows block passed PowerShell parsing, and the working-tree diff passed
  whitespace validation. The pull-request evidence heredoc now has an explicit
  terminator and emits no end-of-file syntax warning.
- **VERIFIED / HOSTED WORKFLOW FOLLOW-UP:** the later natural v2.6.6 runs
  recorded above proved the corrected hosted desktop and same-image Docker
  paths. The Docker publish job pushed only the saved smoke-tested image after
  reloading and identity verification; no manual publication bypass was used.

- **VERIFIED / LOCAL UPDATER FAIL-CLOSED GATE 2026-09-03:** automatic source,
  executable, and Docker update application now terminates with structured
  `update_apply_unavailable` before DNS, HTTP, Git, file replacement, or
  restart. The apply body is an empty forbid-extra model; URL and mirror fields
  or query parameters are rejected. Browser mirror selection is retired and
  the UI directs users to the fixed canonical GitHub Releases page for manual
  installation without sending a URL or mirror.
- **VERIFIED / READ-ONLY CHECK BOUNDARY 2026-09-03:** version checking uses only
  the fixed canonical GitHub latest-release HTTPS endpoint with TLS
  verification, redirects and proxy-environment routing disabled, bounded
  streamed JSON, strict version parsing, and release-note redaction. This is an
  informational check, not artifact-authenticity or automatic-update evidence.
- **DECISION:** ADR-027 requires a signed release manifest, embedded public key,
  pre-replacement signature and digest verification, rollback design, and
  adversarial tests before automatic update or restart can be enabled again.
- **BOUNDARY / RESUME:** no release key, signing pipeline, network request,
  update application, Git mutation, file replacement, restart, VPS action,
  commit, tag, Release, or push was performed. Resume automatic-updater work
  only after the release-signing contract and trusted public key are approved;
  until then preserve the read-only check and manual-install flow.

- **VERIFIED / LOCAL CUTOUT MODEL FRAMEWORK 2026-09-03:** the Precision Edit
  cutout section retains the fixed `genbox-cutout-model-install-v1` source and
  license-information framework, but production reports
  `download_supported=false`, `install_supported=false`, and capability
  `can_download=false`. POST download fails closed before DNS/client/network
  work and the disabled UI says `来源/授权尚未验证`. The UI/API state framework
  and test-only injected fixtures retain verification, progress, cancellation,
  and retry coverage, but the v2.6.6 candidate does not deliver a production
  network installer. An operator may manually place the fixed-size/fingerprint model;
  local models still require `ready` plus `executable=true` before cutout is
  enabled.
- **VERIFIED / DISTRIBUTION BOUNDARY 2026-09-03:** packaged builds include
  Python 3.12, NumPy, and ONNX Runtime, but not the ONNX checkpoint. Automated
  public-model download is disabled because conversion history, training-data
  provenance, and commercial-use rights remain **UNVERIFIED**. The internal
  verifier accepts chunked responses without `Content-Length`; any present
  length must be valid and exact, and streamed bytes still must match the fixed
  size, SHA-256, and MD5. Installation waits for inference only to a fixed
  deadline, then fails terminally and removes its owned `.part`.
- **VERIFIED / AUTOMATED UI ONLY 2026-09-03:** local MJS coverage exercises the
  installer state machine and API envelope without downloading the public model.
  A real public download and real model inference remain **UNVERIFIED**.
- **VERIFIED / RELEASE AND INSTALLER GATES 2026-09-03:** the combined targeted
  release-packaging and cutout suite passed `89`; both cutout installer and
  precision-edit MJS suites passed; Python/JavaScript syntax checks, workflow
  YAML parsing (`6` jobs), and `git diff HEAD --check` passed. That local gate
  performed no public model download, Provider request, VPS, release, tag,
  push, or cleanup action.
- **VERIFIED / RELEASE AND DOCKER WORKFLOW CONTRACT 2026-09-03:**
  changelog, rolling notes, bilingual v2.6.6 notes, and third-party notices are
  aligned to version `2.6.6`. The public notes contain stable release content;
  this status is the source for transient publication and hosted-CI state. The
  notes state that production model network download/install and automatic
  update application remain disabled, while checkpoint provenance and
  commercial-use rights remain **UNVERIFIED**. Local
  `python -m pytest -q tests/test_release_packaging.py` passed `42` with the
  v2.6.6 version, notes, Compose pin, and tag contract. The tested
  Docker workflow requires a tag to match the packaged version before build,
  uses the single `steps.build.outputs.imageid` for runtime-import and HTTP
  smoke checks, and verifies each publish tag resolves to that same image ID
  before push. The later natural hosted runs recorded above passed this
  contract and published the v2.6.6 Release and GHCR image.
- **VERIFIED / LOCAL V2.6.6 RELEASE CONTRACT 2026-09-03:**
  `python -m pytest -q tests/test_release_packaging.py` passed `42`;
  `python -m pytest -q` passed `1302`;
  `python scripts/package_release.py --validate-release-tag v2.6.6` passed;
  workflow YAML parsed with `6` desktop jobs and `3` Docker jobs; Python
  compilation and `git diff --check` passed. These verification commands
  performed no remote action.

- **VERIFIED / LOCAL PROVIDER-OUTPUT SAFETY:** provider-returned images now
  share bounded decoding and validation before persistence, including encoded
  and decoded byte limits, decoded-pixel limits, declared-versus-decoded MIME
  consistency, and decompression-bomb rejection. Variation output uses the
  same bounded decoder. The current provider, precision/inpaint, and
  generation-control regression passed `252`; earlier variation safety and
  variation/generation targets passed `12` and `24`.
- **VERIFIED / LOCAL RELEASE-NOTICE GATE:** bcrypt `==5.0.0`, NumPy `==2.4.3`,
  and ONNX Runtime `==1.24.3` are recorded in `THIRD_PARTY_NOTICES.md` with
  their declared license information and collected physical license assets.
  The release packaging test asserts dependency distribution, notice coverage,
  candidate dates/links, tag/version gates, and the same-image Docker
  smoke/publish contract; the current v2.6.6 local suite passed `42`. The
  earlier combined release and cutout target passed `89` before this candidate
  wording correction.
- **USER-CONFIRMED / LOCAL BROWSER:** the current Precision Edit V4 workflow
  works in the local browser. This supersedes only the September 2 manual
  browser-acceptance blocker; a real cutout refine POST remains **UNVERIFIED**.
- **VERIFIED / PACKAGING CONTRACT:** the local cutout adapter runtime is
  packaged, but the ONNX model file remains external and operator-provided. It
  is not bundled, must pass the fixed size and hash checks, and the capability
  fails closed until the model is installed and validated.
- **BOUNDARY:** v2.6.6 hosted CI, Release assets, checksums, and GHCR publication
  are verified. No VPS, production deployment, source cleanup, Provider call,
  cutout-model download/inference, clean-redeployment acceptance, or new
  cross-project acceptance was performed by this release operation. Automatic
  update application remains disabled under ADR-027, and cutout-model
  provenance and commercial-use rights remain **UNVERIFIED**. The historical
  `v2.6.5` tag was not moved or deleted.
- **RESUME:** preserve the immutable v2.6.6 tag and published assets. Treat VPS
  deployment, source cleanup, real Provider validation, cutout-model rights,
  and signed automatic-update work as separately authorized gates with fresh
  evidence; do not infer them from this successful publication.

## Current bounded development strategy (2026-09-02)

- **CURRENT PRODUCT PRIORITY / USER-CONFIRMED 2026-09-02:** precision edit V4
  remains the sole active product-development scope for local acceptance. Local
  implementation, regression evidence, and user-confirmed browser acceptance
  are recorded below; real refine POST and real Provider precision edit still
  require user-led validation. Extension-center, deployment, Push, video, VPS,
  cleanup, release, and other unrelated feature work remain deferred.
- **CURRENT CONTRACT:** `docs/precision-edit-v4-research.md` is the active
  local precision-edit V4 research/contract document for this bounded work.
- **BOUNDARY:** local evidence does not change the official Phase 9/10
  completion state and does not authorize external Provider, VPS, production,
  cleanup, commit, tag, Release, or push actions.

## Precision edit V4 final local implementation evidence (2026-09-02)

- **VERIFIED / LOCAL FAILURE CLASSIFICATION 2026-09-02:** the current
  `gen_0047` failure is a local source-size capability gate rejection before
  any HTTP request is made. It is not evidence that the selected model lacks
  precision-edit support. Historical successful precision-edit paths
  `gen_0024`, `gen_0026`, `gen_0027`, and `gen_0035` demonstrate that this
  path has previously succeeded. Earlier failures remain separately classified
  as an upstream `503` and a strict output-size mismatch; they must not be
  conflated with unsupported-model claims.
- **VERIFIED / LOCAL CAPABILITY RULE 2026-09-02:** alias resolution accepts
  only an explicit `alias_of` or `canonical_model` declaration. The resolved
  canonical model must declare `precision_edit=true`, declare valid
  `supported_sizes`, and include the source size. Missing declarations,
  unconfirmed mappings, and similar-name collisions remain fail-closed. The
  actual requested model name is preserved and is never rewritten.
- **USER-CONFIRMED / LOCAL SNAPSHOT:** a repository-external snapshot was
  captured under OS temp as `genbox-precision-v4-snapshot-20260902-095532`.
  The stable status record intentionally keeps only this basename and no user
  absolute path.
- **USER-CONFIRMED / LOCAL UX IMPLEMENTED:** the precision workbench covers the
  user's nine requested areas locally: object selection/move; arrow, rectangle,
  and ellipse secondary movement/scaling; eraser and text flows with complete
  in-app help; cutout refine with feather range `0..64`, letterbox-safe mask
  mapping, quantile-based alpha calibration, optional selection mask, explicit
  foreground restore, alpha/version handling, and stale-response guards; resize-only first
  submit and retry with no annotation fields or `image_data_list`; compact `?`
  help immediately beside the annotation canvas plus top `文档说明` dialog;
  transparent After/Compare rendering over a checkerboard; and strict
  non-sensitive model-display preference persistence with alias/capability
  separation. The model display dropdown is a portaled compact multi-select
  popover at the shared `--z-overlay` layer above the sidebar and below modals;
  long model names wrap inside checkbox rows, controls remain clickable at
  narrow widths, focus enters the menu, Tab loops inside it, and
  Escape/Cancel/OK restore focus to the trigger.
- **USER-CONFIRMED / PAYLOAD CONTRACT:** resize-only generation payloads omit
  `annotation_image_data`, `annotation_contract`, `annotation_data`,
  `annotation_objects`, `annotations`, and `image_data_list` entirely, including
  on retry. Empty arrays, empty objects, empty strings, and null values are not
  accepted as substitutes for omission.
- **VERIFIED / LOCAL 422 FIX 2026-09-02:** the annotated-submit `422` root
  cause was frontend leakage of local-only annotation metadata into the runtime
  request envelope. `annotation_data` and `annotation_objects` are now retained
  only for local UI/contract state and are not sent as provider/backend request
  fields; pure resize still omits every annotation field listed above.
- **USER-CONFIRMED / MODEL ALIAS FACT:** `gpt-image2-b` and similar entries are
  `gpt-image-2` channel/account aliases. Do not infer capability, supported
  size, or OpenAI model identity from alias text alone.
- **VERIFIED / LOCAL ALIAS SIZE FIX 2026-09-02:** the
  `source_size_not_declared` failure was caused by custom model aliases such as
  `gpt-image2-b` being treated as canonical model identities, so the provider
  size declaration was not resolved for the selected model. Compatibility now
  accepts an explicit `alias_of`/`canonical_model` relationship and resolves
  capability through the declared canonical model; undeclared sizes and
  ambiguous model-name collisions continue to fail closed.
- **USER-CONFIRMED / SIZE-EXPANSION BUG CLOSURE:** the local precision
  size-expansion failure was traced to frontend capability/readiness drift: the
  UI could lose the explicitly selected model on retry, accept stale or loose
  provider size declarations, and refresh readiness too late after exact-size
  authorization changes. The closed local contract now keeps the explicit model
  on first submit and retry, uses explicit current-`WxH` capability
  confirm/revoke, refreshes readiness on the resize events that affect
  generation eligibility, accepts provider resize capability only as canonical
  string-only `WxH` declarations, ignores noncanonical strings and object-shaped
  `{width,height}`/`{w,h}` aliases, and applies the precision-specific
  `64 * 1024 * 1024` output-pixel cap.
- **USER-CONFIRMED / EXACT SIZE ROOT CAUSE:** the observed real output-size
  failure was requested `1536x864` versus actual `1376x768`; the exact-output
  gate discarded it as `precision_edit_output_size_mismatch`.
- **VERIFIED / OPENAI DOCS 2026-09-02:** official OpenAI Images documentation
  identifies `gpt-image-2` as usable for image generation and existing-image
  edits. The accepted exact-size contract is: each side `<= 3840`, width and
  height are multiples of `16`, aspect ratio is within `1:3..3:1`, and total
  pixels are `655360..8294400`; sizes above `2560x1440` are experimental.
  Valid exact examples include `1280x720`, `1536x864`, `1792x768`,
  `2560x1440`, and `3840x2160`. `1920x1080` is not a valid exact request
  because `1080` is not divisible by `16`. Do not record or rely on a `4000px`
  max-edge claim. A gateway or upstream may still return a different size;
  GenBox must verify the returned pixels and then fail under `strict` or apply
  only explicit `fit_crop`. Prompt words such as `8K` are style/detail
  guidance, not a request for an 8K output file.
- **USER-CONFIRMED / RESIZE POLICY:** `precision_output_size_policy` remains in
  resize payloads. The default is `strict`. `fit_crop` is explicit
  page-session memory only and is not written to localStorage. It may accept a
  single provider call only when ratio delta is `<= 5%` and upscale is
  `<= 1.5`; GenBox then applies a center cover crop with LANCZOS, preserves
  alpha where present, records metadata, and surfaces a warning. No
  `precision_aspect_ratio_constraint` is sent or saved.
- **USER-CONFIRMED / STRUCTURED PROMPT:** the backend derives and appends the
  `16:9` or `21:9` structured prompt block from the canonical target `WxH`.
  The frontend does not concatenate prompt text and does not send a separate
  aspect field. A read-only aspect hint may remain in the UI.
- **USER-CONFIRMED / LOCAL REVIEWS:** final backend, UI, Ops, and Docs reviews
  reported P0/P1/P2/P3 all `0`; the targeted unauthorized/forbidden route
  check returned the expected `403`.
- **VERIFIED / LOCAL FINAL REGRESSIONS 2026-09-02:** alias/provider coverage
  passed `131`; precision-related coverage passed `319`; the full repository
  suite passed `1143`. All four MJS suites passed. Four `node --check`
  commands, explicit `py_compile`, and `git diff --check` passed. Independent
  review passed with `0` blockers.
- **VERIFIED / LOCAL LAB 2026-09-02:** before final restart,
  `Get-NetTCPConnection -LocalPort 8892 -State Listen` showed the owned local
  listener at `127.0.0.1:8892` as PID `50984`. `.\start-lab.ps1 -Action stop`
  safely stopped PID `50984`; `.\start-lab.ps1 -Action start -Background`
  reported READY as PID `19960`, HEAD `f0e97f8`, version `2.6.4`. Fresh
  read-only probes returned HTTP `200` for `/`, `/api/runtime/status`, and the
  cutout capability endpoint; `/` had content length `193352`.
  `/api/runtime/status` reported `version=2.6.4`, `runtime_head=f0e97f8`,
  `runtime_id=a3d0fc431733`, `runtime_source=41cf5ae2cf9ba4ff`, `mode=dev`,
  and `port=8892`. `Get-NetTCPConnection` confirmed the current listener on
  `127.0.0.1:8892` is PID `19960`. Cutout capabilities reported
  `state=ready`, `available=true`, `executable=true`, and
  `adapter=u2net-human-seg-onnx`. The local lab was left running for user
  acceptance.
- **VERIFIED / LOCAL FRONTEND UPDATE 2026-09-02:** cutout refine now exposes
  an explicit foreground-restore mode with selection-gated enablement, restore
  alpha control, restore payload fields, and restore-aware completion/status
  copy. Verification passed `node tests/test_precision_edit_ui.mjs`,
  `python -m pytest -q tests/test_cutout_refine.py tests/test_cutout_refine_route.py`,
  `node --check static/js/app-all.js`, `node --check static/js/i18n.js`, and
  `git diff --check`.
- **VERIFIED / LOCAL PLAYWRIGHT 2026-09-02:** synthetic three-viewport browser
  checks passed at `390x844`, `937x920`, and `1200x800`: the model visibility
  popover hit-tests to menu controls instead of `ASIDE#sidebar`, uses
  `--z-overlay`, stays within viewport bounds with no horizontal overflow,
  keeps its footer visible, wraps long model names without covering checkboxes,
  and remains below the precision docs modal.
- **UNVERIFIED / USER ACCEPTANCE REQUIRED:** real user-led browser visual
  inspection with a non-sensitive local image, real cutout refine POST, and real
  Provider precision edit remain **UNVERIFIED** until the user performs and
  records sanitized acceptance evidence. Real Provider success and user-browser
  manual acceptance are not established by the local evidence above.
- **BOUNDARY:** no VPS, production instance, cleanup, commit, tag, Release,
  push, or unrelated phase work was performed. No external Provider success is
  claimed.
- **RESUME:** with the existing local service still running, use a
  non-sensitive image at
  `http://127.0.0.1:8892/#/generate/precision_edit/precision`. Manually verify
  the three viewport sizes above; source load; object select/move; arrow
  endpoint scaling; rectangle/ellipse movement and resizing; eraser, text,
  undo/redo; compact `?` and top `文档说明` dialog; resize-only first submit and
  retry payload omission; transparent After/Compare checkerboard; cutout refine
  mask/feather/alpha/version/stale guard; and one explicitly selected Provider
  precision edit. Record only sanitized status, elapsed time, and result; do not
  record filenames, prompts, credentials, host identity, user media, or raw
  Provider responses.

## Precision edit upstream-error redaction closure (2026-08-31)

- **VERIFIED / LOCAL SECURITY FIX:** `providers/__init__.py` now sends the
  technical detail retained by `_friendly_generation_error()` through the
  shared sensitive-text redactor. The redactor also recognizes quoted JSON
  credential fields and preserves useful surrounding JSON while masking API
  keys, Bearer credentials, token-bearing query parameters, URL userinfo,
  prefixed `sk-`-style secrets, and exact credentials configured on the
  provider. The precision-edit upstream-error path is covered directly; all
  test values are synthetic.
- **VERIFIED / LOCAL TESTS:** focused provider error and precision contracts
  passed `54 passed`; the broader precision/inpaint/generation-control target
  passed `156 passed`; the full repository suite passed `851 passed`.
  `tests/test_precision_edit_ui.mjs`, `tests/test_generation_error_ui.mjs`,
  `tests/test_stop_generation_ui.mjs`, and `tests/test_i18n.mjs` passed. Four
  relevant `node --check` commands, `py_compile` for `main.py`,
  `providers/__init__.py`, and `config.py`, and `git diff --check` passed.
- **VERIFIED / LOCAL LAB:** after the fix, the owned lab was restarted with
  `start-lab.ps1` and reported READY on `127.0.0.1:8892` as PID `33476`,
  version `2.6.4`, mode `dev`, and HEAD `f0e97f8`. Both `/` and
  `/api/runtime/status` returned HTTP `200` on 2026-08-31.
- **BOUNDARY / RESUME:** no VPS, production instance, cleanup, execute marker,
  tag, Release, or real provider credential was used. Real browser pointer
  interaction, real GPT Image 2 editing, and a configured cutout adapter remain
  **UNVERIFIED** and require explicit user-led acceptance. Resume by performing
  only those manual interactions with a non-sensitive image and separately
  selected external endpoint; do not infer external success from local tests.

## Precision edit V3 latest validation status (2026-08-29)

- **VERIFIED / LOCAL AUTOMATED:** the precision-edit validation suites passed
  `147 passed`; this covers the precision-edit contracts, provider capability
  and error behavior, inpaint compatibility, generation controls, and related
  safety regressions.
- **VERIFIED / LOCAL CAPABILITY AND CREDENTIALS:** the image-capability and
  provider-credential suites passed `8 passed`.
- **VERIFIED / LOCAL UI AND STATIC CHECKS:** `tests/test_precision_edit_ui.mjs`,
  `tests/test_generation_error_ui.mjs`, `tests/test_stop_generation_ui.mjs`,
  and `tests/test_i18n.mjs` passed. `node --check` passed for
  `static/js/app-all.js`, `static/js/i18n.js`, `static/js/app.js`, and
  `static/js/generate.js`; `py_compile` passed for `main.py`,
  `providers/__init__.py`, and `config.py`; `git diff --check` passed.
- **8892 PAGE EVIDENCE:** only the previously recorded static/structure checks
  are accepted as **PASS**. The following browser interactions remain
  **UNVERIFIED**: real local image upload, pointer drawing for annotations,
  the reusable main-canvas before/after comparison drag line, version switching,
  and dragging the canvas container border to resize its viewing area.
- **EXTERNAL EVIDENCE:** real GPT Image 2 editing, a real transparent-background
  cutout adapter, and external or isolated end-to-end verification remain
  **UNVERIFIED**. Mock data, static contracts, and local tests do not establish
  real provider success. No Phase 9 or Phase 10 completion is implied.
- **ENVIRONMENT NOTE:** the first pytest attempt hit a Windows temporary-directory
  permission error involving `pytest-current`; rerunning with independent
  `--basetemp` directories completed successfully. This is recorded as a local
  test-environment issue, not as a product failure.
- **RESUME:** after an authorized Agent confirms the local lab is online, load a
  non-sensitive test image in `#/generate/precision_edit/precision` and manually
  verify the five interaction groups above without submitting a generation.
  Then separately arrange a reachable, explicitly selected GPT Image 2 endpoint,
  a configured cutout adapter, and isolated/external E2E evidence. Update this
  document only with dated observations and keep the evidence labels separate.

## Precision edit V3 local delivery slice (2026-08-28)

- LOCAL VERIFIED: the current working tree adds the genbox-annotation-v3 contract for ellipse and freehand brush annotations, per-region instructions, normalized coordinates, undo/redo-safe erasing, view-only canvas zoom, and a stable source-aspect canvas surface. The existing arrow, rectangle, and text workflows remain available.
- LOCAL VERIFIED: the precision workbench now exposes ellipse, arrow, rectangle, brush, eraser, and text tools; mobile controls use a two-row touch layout; the main canvas remains the reusable source/result surface; and the right-side task log/model picker stays in the focused workbench.
- LOCAL VERIFIED: the cutout UI is fail-closed. Without an executable local cutout adapter, the person-extraction action remains disabled and explains that brush selection can still be sent to the edit model. No cutout adapter was installed or enabled in this slice.
- VERIFIED 2026-08-28: node tests/test_precision_edit_ui.mjs passed; focused backend/provider tests passed 49; node --check static/js/app-all.js, Python compilation, and git diff --check passed. The loopback service owning 127.0.0.1:8892 was rechecked as the expected python.exe main.py process, served the current V3 JavaScript with HTTP 200, and returned no browser console errors after refresh. Desktop and mobile DOM checks confirmed no horizontal overflow; mobile canvas width recovered from the prior 2px regression and tool buttons measured at least 44px high.
- UNVERIFIED: a real image upload gesture, pointer drawing against a user image, real GPT Image 2 edit output, upstream 21:9/resize behavior, and transparent-background cutout output still require a user-selected test image and a reachable compatible upstream/adapter. The service was not replaced or deployed remotely.
- Resume: continue from the current working tree. For the next acceptance pass, load a non-sensitive test image in the precision workbench, exercise each pointer tool and the version comparison, then separately verify a real image-edit endpoint and any cutout adapter before changing the fail-closed gate.

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
- **LOCAL CLEAN DEPLOYMENT W3 / PASS 2026-08-24:** clean clone from the pushed
  personal branch at `1383f537...` with a local Docker image passed the full
  Compose Store acceptance: three views, `401` without auth, unknown-facts
  fail-closed (`confidence=unknown`, `actions=[]`, field-level `unknown_facts`),
  planned/external rows read-only, no forbidden public keys, and identical
  projection across `restart`. Prior Compose failures were Windows harness
  path/interpolation issues, not product defects; the corrected runner uses
  absolute `-f` paths, shell-env interpolation, literal `ADMIN_KEY` override,
  and a key-aware leak assertion. Isolated, synthetic, loopback-only; torn down
  with zero residuals. Evidence: `docs/PHASE10-W3-CLEAN-DEPLOYMENT-20260824.md`.
  This remains local/synthetic evidence and does not prove VPS, published-image,
  browser, or adapter-lifecycle acceptance.
- **LOCAL MULTI-TARGET / PASS 2026-08-24 (HEAD `6e11ab6`):** Store installed
  projection is scoped to the first `isolated-development` target, keeping
  installed instances aligned with the target-bound projection and facts; the
  no-isolated-target legacy behavior remains covered. Focused verification:
  `267 passed`; full verification: `693 passed`. The four `node --check`
  commands, explicit PowerShell-expanded `py_compile`, and `git diff --check`
  passed. This is local evidence only; it does not prove live or isolated-VPS
  multi-target behavior.
- **PRECISION EDIT / CUTOUT LOCAL 2026-08-27:** annotation v2 now requires
  stable labels plus per-arrow/rectangle instructions, keeps text instructions
  optional, sends only `label` (no `number` alias), draws label numbers on
  the overlay, and converts version URLs back to data URLs for continued
  editing. Cutout is fail-closed: no adapter returns structured `503` from
  both capabilities and submission before image processing. Focused suites
  pass; full suite `778 passed`; Node UI contract assertions, `node --check`,
  explicit `py_compile`, and `git diff --check` pass; local lab restarted on
  `8892` with HTTP `200`. Local evidence only; no live provider generation,
  VPS, clean deployment, tag, or Release was performed. Phase 10 remains In
  Progress.
- **PRECISION EDIT UX FOLLOW-UP / VERIFIED LOCALLY 2026-08-28:** the reusable
  main canvas now owns the version rail and before/after comparison surface;
  the right inspector starts with fail-closed Cutout, followed by per-annotation
  instructions, an explicit processing-progress empty state, and endpoint/model
  selection. Fixed a deterministic initialization error caused by an undefined
  Cutout control helper, kept per-object textareas connected while typing,
  separated version browsing from base replacement, moved fullscreen to the
  main canvas, and added complete pointer/capture handling for the comparison
  slider. A synthetic repository image loaded at its native 1440 x 900 aspect
  ratio; a rectangle annotation persisted; its instruction accepted Chinese
  text while retaining focus; no browser console error was observed.
  git diff --check, JavaScript syntax checks, both Node UI regression suites,
  and the focused Python contracts (50 passed) succeeded. Lab restart reported
  READY on http://127.0.0.1:8892/ at HEAD f0e97f8. Real GPT Image 2 precision
  generation and a configured Cutout adapter remain **UNVERIFIED**; no VPS,
  production, commit, push, tag, or Release action was performed. Resume by
  having the user manually inspect the open precision-edit page, then diagnose
  only reproducible UI or provider failures from fresh logs.
- **PRECISION EDIT SIZE SAFETY / VERIFIED LOCALLY 2026-08-28:** the main-canvas
  header now keeps the version rail, Before, After, Compare, and Fullscreen
  controls together, with Fullscreen at the far right. Precision editing
  defaults to preserving the source dimensions and aspect ratio and does not
  inherit text-to-image ratio or size controls. A separate explicit Change size
  mode provides presets, custom width/height, and composition guidance; 21:9
  maps to 1792 x 768 as a requested target only. The request contract carries
  `precision_size_mode`, `precision_target_size`, and
  `precision_resize_prompt`. Preserve mode asks the provider for `size=auto`;
  resize mode sends only the explicit target. Returned dimensions are checked
  before saving, and a mismatch fails closed with
  `precision_edit_output_size_mismatch` instead of silently cropping, stretching,
  or replacing the annotation canvas. Completed versions remain browseable but
  are not automatically promoted to the next editing base. `git diff --check`,
  JavaScript syntax checks, both Node UI suites, and focused precision/inpaint
  Python contracts passed (`56 passed`). Independent read-only review found no
  remaining P1/P2 after closing two size-contract bypasses: precision editing
  cannot inherit generic post-generation upscaling, and resize mode requires
  non-empty composition guidance in the frontend, backend, and Provider layer.
  Browser interaction verified the default preserve state, expandable resize
  controls, required guidance field, right-aligned Fullscreen control, and no
  new console errors. The lab is running at http://127.0.0.1:8892/ (PID 24324,
  HTTP 200); the unrelated listener on 8891 was not changed. Real GPT Image 2 editing and
  arbitrary resize/outpaint, including 21:9, remain **UNVERIFIED**. No VPS,
  production, commit, push, tag, or Release action was performed. Resume with a
  user-selected real endpoint only after fresh logs are available, and record
  unsupported target-size responses as provider limitations rather than local
  success.
- **BOUNDARY:** Recommended is high only with complete verified discovery and
  Docker/Compose evidence plus all nine environment facts observed. The current
  slice still requires live/isolated-VPS verification, real multi-target behavior,
  adapter lifecycle verification, and full Store acceptance; Phase 10 remains In
  Progress and is not complete.

## v2.6.4 packaged startup and image quantity release (2026-08-25)

- **VERIFIED:** release commit `00bba347f4c0a28769c59c0cce2e256b59f90f16`
  was pushed and annotated tag `v2.6.4` points to that commit. GitHub Actions
  Docker and Desktop Clients workflows both completed successfully.
- **VERIFIED:** local validation passed: full suite `700 passed`,
  startup/provider/release/setup focused suite `57 passed`, five `node --check`
  commands, expanded Python `py_compile`, and `git diff --check`.
- **VERIFIED:** a freshly downloaded, extracted `GenBox-Windows.zip` from the
  published `v2.6.4` Release was manually started in a disposable local temp
  directory. Its first-run prompt showed Chinese/English labels; after choosing
  local mode, a second run on an isolated loopback port started successfully
  and was stopped cleanly. The initial default-port run encountered a local
  port collision only and was not treated as a package failure.
- **VERIFIED:** the packaged first-run path now configures UTF-8 stdout/stderr
  and bilingual messages directly in `main.py`; the prior `v2.6.3` launcher
  script-only change did not cover `GenBox.exe` and is superseded for this path.
- **VERIFIED:** image generation derives `quantities` from the visible `selQty`
  control, while backend normalization bounds malformed/stale values to `1..10`.
  This addresses a stale local-storage value creating `3/3` tasks while the UI
  displayed `1`.
- **BOUNDARY:** local package startup evidence does not claim a successful live
  provider generation, VPS validation, production deployment, or clean
  deployment acceptance. Phase 10 remains In Progress.

## v2.6.3 stable release published (2026-08-24)

- **VERIFIED:** release commit `72d7f16c78036dcbbef3d7808ca7b71d4d66b603`
  was pushed to the personal GitHub repository and annotated tag `v2.6.3`
  points to that commit.
- **VERIFIED:** local release validation passed: full suite `698 passed`,
  provider/startup/release focused suite `16 passed`, four `node --check`
  commands, expanded Python `py_compile`, and `git diff --check`.
- **VERIFIED:** tag-triggered GitHub Actions succeeded for Docker Image and
  Desktop Clients, including Linux, Windows, macOS, Docker Compose packaging,
  checksums, and Release creation.
- **VERIFIED:** GitHub Release `GenBox v2.6.3` is published and not draft or
  prerelease, with Windows/macOS/Linux binaries and zips, `GenBox.exe`, Docker
  Compose bundle, and `SHA256SUMS.txt`.
- **VERIFIED:** Windows `start.bat` and `start.ps1` now set UTF-8 console and
  Python output settings and show bilingual startup/error guidance. This is
  source/package evidence; manual verification on every Windows code page is
  not claimed.
- **BOUNDARY:** no VPS, production container, upstream PR, browser generation,
  or clean-deployment acceptance was performed by this release task. Phase 10
  remains In Progress.

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

## Precision edit media showcase slice (2026-09-03)

- **Evidence class:** `LOCAL STATIC/UI CONTRACT`. The precision-edit display
  now has an image-only fullscreen overlay (separate from the workbench
  Fullscreen API root), split prompt chunks for the original and each edit,
  a current-session result thumbnail rail, and gallery start/end date filters.
- **Verification:** `node tests/test_precision_edit_static_contract.mjs` and
  `node tests/test_precision_edit_ui.mjs` passed; `node --check
  static/js/app-all.js` and `git diff --check` passed for the touched display
  surfaces.
- **Boundary:** no browser visual capture, mobile device run, provider call,
  or VPS deployment was performed. Date filtering relies on parseable
  `created_at` values returned by the gallery API; malformed timestamps are
  excluded when a date range is active.
- **Resume:** run the browser smoke/UAT for image-only fullscreen while the
  precision workbench itself is fullscreen, then verify prompt/history and
  date-range interactions at desktop and narrow mobile widths.

## Multi-algorithm cutout registry slice (2026-09-04)

- **Evidence class:** `LOCAL CODE/UNIT TEST`. Added
  `image_tools/cutout_registry.py` with ordered adapter probing, explicit
  executable-only fallback, and bounded failure isolation. The existing
  `u2net-human-seg-onnx` adapter is untouched.
- **Second algorithm status:** `rmbg-2.0` (BRIA RMBG-2.0 source) is recorded as
  `UNVERIFIED` and `unavailable`. Its gated weights were not downloaded, no
  SHA-256 was independently verified, and license/commercial-use approval is
  unresolved; runtime dependencies are metadata only (`torch`, `transformers`,
  `Pillow`, `numpy`). No capability is advertised from this descriptor.
- **Verification command/result:**
  `$env:PYTHONPATH='.'; pytest -q tests/test_cutout_registry.py tests/test_cutout_onnx.py tests/test_cutout_refine.py`
  -> `28 passed`.
- **Boundary:** this is not evidence of a runnable RMBG model or end-to-end
  route integration. `main.py`, providers, static UI, VPS, and remote systems
  were not changed or exercised.

## Precision edit goal-mode verification refresh (2026-09-04)

- **Lab reachability:** `start-lab.ps1 -Action start -Background` reported
  GenBox `v2.6.6` ready on loopback port `8892`; `/` and
  `/api/runtime/status` both returned HTTP `200`. This is local-only evidence.
- **Focused contracts:** with `PYTHONPATH=.` the precision edit, strict-size,
  provider-alias, provider-precision, and cutout-registry selection passed
  `377` tests.
- **Full local regression:** with `PYTHONPATH=.` the full Python suite passed
  `1361` tests in `77.64s`. All nine JavaScript `.mjs` contract files passed;
  `node --check static/js/app-all.js`, Python compilation of `main.py` and
  `providers/__init__.py`, and `git diff --check` also passed.
- **Second cutout algorithm:** the independent feasibility record is
  `docs/CUTOUT-ALGORITHM-FEASIBILITY-20260904.md`. RMBG-2.0 remains
  `UNVERIFIED`/non-executable because gated weights, an independently verified
  digest, and redistribution/commercial-use rights are not established.
- **Remaining acceptance boundary:** real `gpt-image2-b` precision editing,
  real-person cutout quality (including leg retention), and a fresh headed
  browser UAT are still `UNVERIFIED`. No VPS, cleanup, execute marker, commit,
  tag, or Release action was performed.
- **Resume:** obtain an authorized, redistributable second cutout model and
  verify its local inference path, or explicitly accept the current single
  executable algorithm for v2.6.6; then run headed browser UAT with user-owned
  provider credentials before release approval.
- **Candidate policy refresh:** a GitHub repository popularity snapshot on
  2026-09-04 identified InSPyReNet (MIT repository, 745 stars), a
  Transformers.js browser-removal candidate (MIT repository, 1,014 stars),
  and an Apache-2.0 browser candidate (466 stars) for further evaluation.
  These are research candidates only: repository Star/license does not prove
  model-weight licensing, quality, or redistributability. AGPL/GPL candidates
  remain external-reference-only for the default Release. The next decision is
  user-selectable download/install guidance after weight terms and local
  inference are independently verified; no candidate is currently packaged.

## Precision edit manual-toolbar layout follow-up (2026-09-04)

- **VERIFIED / LOCAL UI FIX:** the manual-edit toolbar now reserves two rows at
  all inspector widths. The label and eraser remain on row one while color,
  stroke-width, and text-size controls occupy a bounded second row; this fixes
  the clipped one-line presentation seen during headed review without relying
  on viewport width.
- **VERIFIED / CONTRACTS:** `node tests/test_precision_edit_static_contract.mjs`,
  `node tests/test_precision_edit_ui.mjs`, `node --check static/js/app-all.js`,
  and `git diff --check` passed after the change. The full local Python suite
  also passed `1379` tests in `68.94s`.
- **VERIFIED / LOCAL LAB:** the owned loopback lab was safely restarted after
  source-change detection; `/api/runtime/status` returned HTTP 200 and
  reported GenBox `v2.6.6` in `dev` mode on port `8892`.
- **BOUNDARY:** this closes the narrow-toolbar layout defect only. Real
  provider generation, external strict-size output, cutout quality, and full
  headed UAT remain separately marked `UNVERIFIED` until observed.

## Precision edit session gallery headed check (2026-09-04)

- **VERIFIED / HEADED LOCAL UI:** the loopback workbench visibly renders the
  `当前会话结果` gallery below the canvas, including result count, thumbnail
  list area, start/end date filters, and a clear-filter control. The empty
  state correctly explains that results appear after a successful edit.
- **BOUNDARY:** this confirms the gallery surface and empty state only. The
  current session had zero successful provider results, so automatic insertion
  of a real upstream result remains `UNVERIFIED`.

- **VERIFIED / BROWSER CONTRACT:** `python -m pytest -q
  tests/test_precision_session_gallery_browser.py` -> `1 passed in 3.23s`.
  The test injects two dated session results, verifies count `2`, filters to
  one result, then clears the filter and verifies count `2` again. This is
  local browser behavior evidence, not proof of upstream generation.
- **FOLLOW-UP REGRESSION:** `node tests/test_cutout_model_install_ui.mjs`,
  `node tests/test_precision_edit_ui.mjs`, and focused Python contracts
  (`tests/test_precision_session_gallery_browser.py`,
  `tests/test_cutout_registry.py`, `tests/test_precision_edit_contract.py`)
  passed: `233 passed` plus both JavaScript contract suites.
- **LAB REFRESH:** after source-change detection, the local lab was safely
  restarted with `start-lab.ps1 -Action restart -Background`; runtime status
  returned HTTP `200` with GenBox `2.6.6`, `dev`, loopback port `8892`, and
  runtime head `a9c8cde` on 2026-09-04.
- **FULL REGRESSION REFRESH:** using the workspace Python runtime,
  `$env:PYTHONPATH='.'; python -m pytest -q` completed with `1382 passed in
  74.30s` on 2026-09-04. The plain `pytest` launcher is a separate Python
  installation without Playwright and is not used as the evidence command.

## Precision edit gallery follow-up audit (2026-09-04)

- **VERIFIED / LIVE LOCAL LAB:** `/api/runtime/status` returned HTTP `200`,
  `version=2.6.6`, `mode=dev`, and loopback port `8892`.
- **VERIFIED / HEADED UI:** the workbench renders `当前会话结果` directly
  below the canvas. The empty state, result counter, date range fields, and
  clear-filter control are present; populated results are covered by the
  browser contract test.
- **VERIFIED / REGRESSION:** the focused gallery/strict-size/cutout registry
  set passed `236` tests, and the complete workspace suite passed `1382`
  tests in `68.44s` using `PYTHONPATH=.`.
- **BOUNDARY:** this remains local UI and contract evidence. A real upstream
  edit and automatic insertion of its result are still `UNVERIFIED` until a
  user-owned provider call succeeds.

## Multi-algorithm cutout parallel audit (2026-09-04)

- **VERIFIED / LOCAL REGRESSION:** `$env:PYTHONPATH='.'; python -m pytest -q`
  completed with `1387 passed` in `72.30s` on the current worktree.
- **VERIFIED / PARALLEL REVIEW:** the candidate-algorithm review confirmed that
  only `u2net-human-seg-onnx` is registered as `VERIFIED` and executable.
  `MODNet` remains an isolated opt-in adapter requiring a user-supplied model
  manifest and explicit license confirmation; `BiRefNet`, `RMBG-2.0`, and
  `InSPyReNet` remain `UNVERIFIED`/non-executable because fixed weights,
  redistribution terms, and offline quality evidence are not complete.
- **Boundary:** no candidate was added to the default registry, no U²-Net path
  was changed, and no Release artifact was produced. Real upstream precision
  editing and headed user acceptance remain separate `UNVERIFIED` gates.
- **Resume:** obtain one authorized, fixed-hash second-algorithm checkpoint,
  validate offline CPU inference and leg/hair edge quality, then integrate it
  serially after the isolated adapter tests pass.

## MODNet user-import boundary follow-up (2026-09-04)

- **VERIFIED / DOCUMENTATION:** `docs/MODNET-USER-IMPORT-GUIDE.md` records the
  isolated MODNet adapter boundary and the implemented user-upload contract;
  `docs/DOCUMENTATION-MAP.md` links the guide.
- **VERIFIED / ROUTE:** `POST /api/image-tools/cutout/modnet/import` accepts only
  multipart file content plus a complete size/SHA-256/MD5 manifest and explicit
  license confirmation. The response is sanitized and never exposes local paths.
- **VERIFIED / STORAGE:** `image_tools/cutout_modnet_import.py` writes to the
  isolated `storage/models/cutout/modnet/` directory, enforces a bounded upload,
  rejects path/URL and symlink targets, and atomically publishes the fixed
  `modnet.onnx` target with a non-secret manifest.
- **VERIFIED / TEST:** `$env:PYTHONPATH='.'; python -m pytest -q
  tests/test_cutout_modnet.py tests/test_cutout_modnet_import.py
  tests/test_cutout_modnet_import_route.py tests/test_modnet_model_manager.py
  tests/test_cutout_registry.py` -> `45 passed`.
- **VERIFIED / REGRESSION:** `$env:PYTHONPATH='.'; python -m pytest -q` ->
  `1410 passed` in `75.52s` on 2026-09-04; Python compilation and
  `git diff --check` also passed.
- **CURRENT LIMIT:** importing a checkpoint never enables it automatically;
  status remains `executable=false` until CPU-only runtime probing, fixed-weight
  provenance, redistribution rights, and real portrait quality evidence are
  independently accepted. U²-Net default behavior and the shared registry were
  not changed; no candidate model was downloaded or packaged.
- **Resume:** if a second executable algorithm is desired, supply a fixed,
  authorized checkpoint and complete the independent runtime, licensing, and
  quality review before any registry integration or Release claim.

## Multi-algorithm status recheck (2026-09-04)

- **VERIFIED / LIVE LOCAL LAB:** `GET /api/image-tools/cutout/capabilities`
  returned HTTP `200`; only `u2net-human-seg-onnx` is
  `available=true` and `executable=true`. The installed U²-Net checkpoint is
  `175,997,641` bytes with SHA-256
  `01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c`.
- **VERIFIED / REGRESSION:** focused cutout, MODNet import, registry, and
  precision contracts passed `260` tests; `node tests/test_precision_edit_ui.mjs`
  and `node tests/test_cutout_model_install_ui.mjs` also passed.
- **BOUNDARY:** MODNet, InSPyReNet, BiRefNet, and RMBG-2.0 remain
  `UNVERIFIED`/non-executable. No candidate has complete fixed-weight
  provenance, redistribution terms, offline CPU evidence, and portrait-edge
  quality evidence, so none may be enabled or packaged in a Release.
- **Resume:** parallel work is allowed in isolated adapter, model-evidence,
  quality-benchmark, and UI/test branches. Integrate serially only after all
  gates pass; keep U²-Net as the unchanged default during this work.

## MODNet fixed-checkpoint technical probe (2026-09-04)

- **VERIFIED / SOURCE IDENTITY:** the fixed `onnx-community/modnet-webnn`
  quantized checkpoint at revision
  `6af52070d14deafc5e55ce6cc4d752a322cdff76` was downloaded to an isolated
  temporary path. Size is `6,632,188` bytes and SHA-256 is
  `92e49898c3e05a6d7a944fc67a8cb87c4aad754ffb6ebd949528c7d1105fee3a`.
- **VERIFIED / TECHNICAL SMOKE:** the existing opt-in MODNet adapter started
  an ONNX Runtime CPU session and, after the alpha endpoint fix, produced a
  same-size RGBA PNG with alpha extrema `(0, 255)`. The focused MODNet/import/
  registry suite passed `33` tests, including a regression for quantized alpha
  endpoint preservation.
- **BOUNDARY:** this is technical evidence only. The checkpoint has not yet
  passed full license-text/republication review, disconnected runtime testing,
  or authorized human-image quality review (legs, hair, and soft edges). It is
  still not registered as the default executable algorithm and is not a Release
  artifact.

## Precision workbench interaction pass (2026-09-07)

- **VERIFIED / LOCAL UI:** the precision canvas now limits wheel zoom to its
  centered image-inspection hotspot; outside that hotspot the page scrolls
  normally. A middle click still restores the normal view. Keyboard tool
  shortcuts are documented and do not run while typing in a form control.
- **VERIFIED / CONTINUATION:** a successful precision-edit result is loaded as
  the next editable base image. Cutout and cutout-refinement results keep their
  existing explicit-base behavior.
- **VERIFIED / RESPONSIVE UI:** the session gallery uses a compact disclosure;
  task status has an idle pill and an automatically expanded task card; the
  right inspector can be resized on desktop with pointer or keyboard controls
  and remains single-column on narrow screens. Workflow dialogs and source
  menus stay above or within their viewport bounds.
- **VERIFIED / COMMANDS:** `node tests/test_precision_edit_ui.mjs`, `node
  tests/test_i18n.mjs`, `node --check static/js/app-all.js`, `git diff --check`,
  and `$env:PYTHONPATH='.'; python -m pytest -q
  tests/test_precision_session_gallery_browser.py` passed (`5 passed`).
- **BOUNDARY:** this is local UI and browser-contract evidence. It does not
  claim a new real upstream image-edit call or any release/publication result.

## Precision workbench canvas affordances (2026-09-07)

- **VERIFIED / UI IMPLEMENTATION:** the session-gallery outer surface now keeps
  its low-contrast metal/glass texture across the full row while retaining the
  centered compact disclosure pill.
- **VERIFIED / UI IMPLEMENTATION:** the selected ellipse, rectangle, arrow,
  brush, and text annotation receives a visible canvas-only highlight with
  handles/label above it; export rendering still passes `selected=false`.
- **VERIFIED / UI IMPLEMENTATION:** selected-region instructions now use a
  canvas-adjacent glass popover with a bounded pointer-drag handle, close action,
  and live textarea updates. The inspector list retains only a compact summary.
  The popover is hidden when no annotation is selected and falls back to a
  bottom sheet on narrow screens.
- **VERIFIED / COMMANDS:** `node --check static/js/app-all.js`, `node
  tests/test_precision_edit_ui.mjs`, `node tests/test_i18n.mjs`, and `git diff
  --check` passed on 2026-09-07.
- **BOUNDARY:** this pass is local UI and static/browser-contract evidence. It
  does not claim a new real upstream image-edit call or a cutout quality gate.
- **RESUME:** perform headed manual acceptance with a loaded image: draw each
  supported annotation, verify the highlight, edit text in the draggable
  popover, drag it inside the canvas, close/reopen by selecting the annotation,
  and verify the full-row gallery texture at desktop and narrow widths.
