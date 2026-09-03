# Precision Edit V4 Research and Contract

**Researched:** 2026-09-03
**Scope:** local precision-edit workbench only; no provider/VPS/release changes

**Primary recommendation:** keep one precision-edit workbench, but split its submit semantics into two explicit paths: annotated edit and pure size expansion. Preserve the current version rail, cutout-as-version behavior, and explicit model authorization gate.

## 2026-09-02 Final Handoff Facts

- **USER-CONFIRMED:** `gpt-image2-b` and similar entries are `gpt-image-2` channel/account aliases. Alias text is presentation only; do not infer capability, supported size, or OpenAI model identity from it.
- **VERIFIED / OFFICIAL OPENAI DOCS:** OpenAI's Images documentation identifies `gpt-image-2` as available for image generation and existing-image edits. The exact-size contract is max side `<= 3840`, both sides divisible by `16`, aspect ratio within `1:3..3:1`, and total pixels `655360..8294400`; sizes above `2560x1440` are experimental. Valid examples include `1280x720`, `1536x864`, `1792x768`, `2560x1440`, and `3840x2160`; `1920x1080` is not valid because `1080` is not divisible by `16`. Do not use the discarded `4000px` claim. A gateway or upstream may return different pixels, so GenBox must verify the returned file and then apply `strict` failure or explicit `fit_crop`; prompt words such as `8K` are style/detail guidance, not an 8K file contract.
- **USER-CONFIRMED / FAILURE ROOT CAUSE:** the observed real output-size failure was requested `1536x864` versus actual `1376x768`; GenBox's exact output gate discarded it as a mismatch.
- **VERIFIED / LOCAL 422 FIX:** the annotated-submit `422` was caused by local annotation metadata (`annotation_data` / `annotation_objects`) leaking into the runtime request envelope. They remain local UI/contract state only and are not sent as backend/provider request fields.
- **VERIFIED / LOCAL CUTOUT:** cutout refine is letterbox-safe, uses quantile-based alpha calibration, and supports explicit selection-gated foreground restore.
- **VERIFIED / LOCAL POPOVER:** the model visibility popover is portaled to the shared `--z-overlay` layer, above the sidebar and below modals, with long-name wrapping and clickable checkbox/footer controls at the tested narrow viewport.
- **VERIFIED / LOCAL FINAL:** final automated evidence is `1109 passed / 0 failed`; final backend, UI, Ops, and Docs reviews reported P0/P1/P2/P3 all `0`; the targeted forbidden route check returned the expected `403`; Playwright passed at `390x844`, `937x920`, and `1200x800`.
- **BOUNDARY:** real paid Provider precision edit, real cutout refine POST, and manual browser acceptance remain **UNVERIFIED** until sanitized user-led evidence is recorded.

## Local Cutout Model Installation Contract

- Contract: `genbox-cutout-model-install-v1` with one fixed source identity,
  `rembg-u2net-human-seg-v0.0.0`. The browser supplies no URL, filesystem path,
  size, or digest.
- The Precision Edit cutout section shows the fixed source, approximately
  176 MB size, and relative local path. The ONNX checkpoint is not embedded in
  GenBox; Python 3.12, NumPy, and ONNX Runtime are included in packaged builds.
- Production reports `download_supported=false`, `install_supported=false`, and
  capability `can_download=false`. The fixed source and license information
  remain visible, but POST download fails closed before DNS/client/network work
  because checkpoint provenance and commercial-use authorization are
  **UNVERIFIED**. Automated tests may explicitly enable the internal downloader
  fixture; that does not enable production download.
- UI states are `missing`, `downloading`, `hash_mismatch`, `error`, and `ready`.
  The production missing state shows a disabled `来源/授权尚未验证` action.
  Downloader tests retain progress, cancellation, hash-mismatch, and retry
  coverage; ready still offers confirmed deletion of an existing local model.
- Refresh resumes the backend-reported active task. Refresh and task polling use
  separate monotonic tokens so stale responses cannot replace newer state.
  Installer state is process/page state and is not saved to browser storage.
- Model installation state is independent from image cutout/refine pending
  state. Completion always probes `/api/image-tools/cutout/capabilities`; the
  cutout action remains disabled unless the model is `ready` and the capability
  response is both `available=true` and `executable=true`.
- The internal downloader accepts a missing `Content-Length` for chunked
  delivery. If the header is present it must be valid and equal the pinned
  size; actual streamed bytes remain capped and must match size, SHA-256, and
  MD5. Waiting for in-flight inference during atomic installation has a fixed
  deadline; timeout ends the task as failed/busy and removes its owned `.part`.
- Automated tests must not download the public checkpoint. Public download,
  real inference, VPS work, and release publication require separate evidence.

## Requirement-to-Code Map

| Requirement | Current code and tests | V4 contract | Evidence status |
|---|---|---|---|
| Source entry from lightbox, local file, or gallery | `sendToPrecisionEdit()`, `loadPrecisionEditSourceImage()`, `openPrecisionGalleryPicker()` in `static/js/app-all.js`; covered by `tests/test_precision_edit_ui.mjs` | Keep one source image loaded into the precision workbench and never branch into a separate tool surface | None |
| Light PS interaction boundary | `precisionEditObjects`, `precisionEditHistory`, `precisionEditRedo`, `precisionEditTool`, `commitPrecisionEditText()`, brush/eraser/ellipse/rectangle support in `static/js/app-all.js`; V4 local regression evidence includes selection/move, arrow endpoint scaling, mask, feather, checkerboard, and reversible history coverage | Allow only canvas-local annotation, local selection/move, arrow endpoint scaling, eraser, text, mask preview, feather preview, checkerboard transparency preview, and reversible history. Feather must stay local to the selected mask edge and never become a full image filter stack | Implemented and locally verified 2026-09-02 |
| Pure size expansion without annotations | V4 local implementation supports resize-only first submit and retry without annotation fields or `image_data_list`; annotated-submit `422` root cause was fixed by keeping `annotation_data` / `annotation_objects` local-only | Use a dedicated no-annotation submit branch for resize-only work. It requires `precision_size_mode=resize`, `precision_target_size`, and `precision_resize_prompt`, and runtime payload omits annotation fields and `image_data_list` entirely, not empty arrays, empty strings, or nulls. Local annotation metadata must not leak into backend/provider request fields | Implemented and locally verified 2026-09-02 |
| Transparent-background cutout semantics | `get_cutout_capabilities()` / `cutout_image()` in `main.py`; `appendPrecisionCutoutVersion()` and `startPrecisionCutout()` in `static/js/app-all.js`; `tests/test_cutout_onnx.py`, `tests/test_cutout_refine.py`, `tests/test_cutout_refine_route.py`, and `tests/test_precision_edit_ui.mjs` | Treat cutout success as a new browseable version with real alpha PNG output. Do not replace the base image; before/after must compare the original against the cutout result. Refine must keep mask mapping letterbox-safe, calibrate alpha by quantile instead of assuming one fixed edge threshold, and allow explicit selection-gated foreground restore from the original base | Implemented and locally verified 2026-09-02; real user-led refine POST remains unverified |
| Model display filtering and alias/capability separation | `renderPrecisionEditModelPicker()`, `getPrecisionEditModelAuthorizationState()`, `authorizePrecisionEditModel()` in `static/js/app-all.js`; `POST /api/providers/{provider_id}/precision-capability` in `main.py`; `tests/test_precision_edit_ui.mjs` and `tests/test_provider_precision_contract.py` | Show image providers and their models as candidates, but keep display label, alias, and model capability separate. Capability must come from explicit provider/model flags plus explicit user confirmation, not from the visible name | None |
| Model display dropdown | V4 local implementation keeps sanitized model visibility localStorage while preserving explicit selected-model payload semantics; final P2 fix portals the popover above the sidebar and binds controls from the portaled root | Use a compact multi-select popover with confirm/cancel. Focus enters the menu, Tab loops inside it, Escape/Cancel/OK restore focus to the trigger, long names wrap beside real checkbox targets, and the popover uses the shared `--z-overlay` layer below modal/toast surfaces | Implemented and locally verified 2026-09-02 |
| Resize output policy and structured prompt | V4 local implementation keeps `precision_output_size_policy` in resize payloads, defaults to `strict`, and derives aspect prompt text in the backend from canonical target size | `fit_crop` is explicit page-session memory only, never localStorage. It is allowed only after one provider call when ratio delta is `<= 5%` and upscale is `<= 1.5`, then GenBox applies center cover crop, LANCZOS, alpha preservation, metadata, and warning. The frontend never sends `precision_aspect_ratio_constraint` and never concatenates the structured aspect prompt | Implemented and locally verified 2026-09-02 |
| Help document entry layout | `precisionWorkbenchHelp` remains the compact canvas-adjacent popover; V4 adds the top icon+text `文档说明` in-app help dialog/page with translation and UI regression coverage | Keep the compact `?` trigger beside the annotation canvas title, and provide a top-level icon+text `文档说明` action that opens an independent in-app precision-edit help dialog/page | Implemented and locally verified 2026-09-02; user visual acceptance still pending |
| Responsive and accessible layout | CSS for `.precision-workbench-help-trigger`, `.precision-canvas-shell`, `.precision-compare-stage`, `.precision-task-log-panel`, `.precision-canvas-resize-handle`, and `.precision-model-visibility-menu`; V4 local checks cover viewport and hit-test contracts | Keep mobile touch targets, viewport bounds, aria labels, live regions, and no horizontal overflow. Canvas resize must stay keyboard focusable. Browser acceptance must cover `390x844`, `937x920`, and `1200x800` for the model popover and the user-visible acceptance set for the full workbench | Local Playwright popover checks verified 2026-09-02; real user-led full workbench visual inspection remains UNVERIFIED |
| State continuity and version browsing | `precisionEditSession`, `renderPrecisionEditSession()`, `selectPrecisionVersion()`, `setPrecisionBaseVersion()`, `appendPrecisionEditVersion()` in `static/js/app-all.js` | Browsing results must only change `selectedVersionId` and `view`. Only an explicit base action may change `baseVersionId` | None |
| Safety boundaries | `tests/test_generation_error_ui.mjs`, `tests/test_i18n.mjs`, `tests/test_precision_edit_contract.py`, `tests/test_provider_precision_contract.py` | Keep error handling structured and sanitized. Do not let precision-edit text or model errors leak raw provider detail into the UI | Existing redaction gates remain relevant |

## State Model

The current workbench has a V4-ready state model. Future work should preserve it and avoid merging the resize-only and annotated-edit payload paths.

| State | Meaning | Owner |
|---|---|---|
| `precisionEditSourceImageData`, `precisionEditSourceWidth`, `precisionEditSourceHeight` | Active source image and its real dimensions | Source loading / canvas |
| `precisionEditObjects`, `precisionEditHistory`, `precisionEditRedo` | Annotation objects and reversible edit history | Canvas interaction |
| `precisionEditTool`, `precisionEditSelectedId`, `precisionEditPendingInstruction`, `precisionEditTextDraftPoint` | Active tool and in-progress edit state | Canvas interaction |
| selection/move state | The selected object, active handles, move origin, resize origin, and pointer capture lifecycle | Canvas interaction |
| arrow endpoint state | Arrow endpoints and active endpoint handles, preserving normalized start/end coordinates while scaling | Canvas interaction |
| `precisionEditSession` | Current version rail state, selected version, base version, task linkage, and source generation | Version browsing / compare |
| `precisionEditSelectedModel`, `precisionEditModelPickerReady`, `precisionEditAuthorizationPending` | Model choice and explicit authorization gate | Provider selection |
| `precisionCutoutCapability`, `precisionCutoutPending`, `precisionCutoutProbeToken`, `precisionCutoutOperationToken` | Cutout probe and request lifecycle | Cutout boundary |
| `precisionViewZoom`, `precisionCanvasResizeState`, `precisionComparePointerId` | View-only zoom, resize handle, compare slider pointer state | Layout and compare UI |

## Submit Contract

V4 treats submit as two mutually exclusive envelopes.

### Annotated edit

- Requires one base image.
- Uses annotation payloads: `annotation_image_data`, `annotation_contract`, `annotations`.
- Uses the selected model explicitly in `provider_settings`.
- Can still carry `precision_size_mode=resize` when the model can resize, but it must also satisfy the resize safety gate.

### Pure size expansion

- Requires one base image.
- Requires `precision_size_mode=resize`.
- Requires `precision_target_size`.
- Requires `precision_resize_prompt`.
- Carries `precision_output_size_policy`; default is `strict`.
- Must not send annotation payloads.
- Must fail closed if any annotation fields are present.
- The browser runtime payload must omit `annotation_image_data`, `annotation_contract`, `annotation_data`, `annotation_objects`, `annotations`, and `image_data_list` entirely. Empty arrays, empty objects, empty strings, and null values are not acceptable substitutes.
- The backend treats presence of any annotation field as a contract error for pure size expansion, even when the value is empty or null.
- For annotated edits, `annotation_data` and `annotation_objects` are local-only UI/contract state and must not be sent as backend/provider request fields.

### Resize result acceptance

- `strict` remains the default and requires the returned image dimensions to exactly match the requested canonical `WxH`.
- `fit_crop` is an explicit page-session choice only; do not persist it to localStorage or treat it as a global product default.
- `fit_crop` may use only one provider call. It can accept a near-miss output only when ratio delta is `<= 5%` and upscale is `<= 1.5`.
- Accepted near-miss output is post-processed by GenBox with a center cover crop and LANCZOS resampling.
- Alpha must be preserved when present, post-processing metadata must record the adjustment, and the UI must show a warning.
- The exact real failure that motivated this policy was requested `1536x864` versus actual `1376x768`; the exact gate correctly discarded it.
- Do not claim that a service will necessarily auto-downscale an exact-size request. The safe claim is that a gateway or upstream may return different pixels and GenBox must verify the returned image.

### Structured prompt

- The frontend sends the base user prompt, canonical `precision_target_size`, and resize guidance, but does not concatenate an aspect-ratio instruction.
- The frontend does not send `precision_aspect_ratio_constraint`; a read-only aspect hint may remain in the UI.
- The backend derives `16:9` or `21:9` from the canonical target `WxH` and appends the structured prompt block server-side.
- Prompt words such as `8K` are descriptive style/detail guidance only; they do not override the exact `precision_target_size` or imply an 8K file.

### Hard rules

- No `image_data_list`.
- No `annotation_image_data`, `annotation_contract`, `annotation_data`, `annotation_objects`, or `annotations` in pure size expansion.
- No generic upscale flags.
- No hidden model fallback.
- No silent conversion of alias text into capability.
- No acceptance of resize targets that are not explicitly declared by the selected model.
- No `4000px` max-edge claim for `gpt-image-2`; use max side `<= 3840`, both sides divisible by `16`, aspect ratio `1:3..3:1`, total pixels `655360..8294400`, and treat sizes above `2560x1440` as experimental.
- `1920x1080` is not a valid exact request because `1080` is not divisible by `16`; valid exact examples include `1280x720`, `1536x864`, `1792x768`, `2560x1440`, and `3840x2160`.

## PS-Style Interaction Boundary

Allowed:

- local upload and gallery import
- region marking with arrow, rectangle, ellipse, brush, and text
- selection and move for existing objects
- endpoint scaling for arrows
- eraser that respects history
- undo, redo, and clear
- adjustable view-only zoom
- compare before / after / compare
- cutout refine preview using a real frontend mask, local feather edge preview, and checkerboard transparency background

Not allowed:

- full layer stack
- freeform raster painting engine
- global blur or filter system
- implicit auto-selection of a model
- automatic replacement of the source base when browsing versions

Feather softens only the selected mask edge in the frontend preview and any serialized refine intent. It must not become a canvas-wide blur, a compositing layer, or a general-purpose image effect.

## Cutout Refine Frontend Contract

V4 cutout refine remains a local UI refinement layer over a cutout result, not a second provider workflow.

- The preview must render the cutout result over a checkerboard transparency background so alpha is visually inspectable.
- The refine mask must be a real frontend mask derived from pointer input, not only a style overlay or CSS highlight.
- Mask coordinates must stay letterbox-safe when the displayed canvas and source image aspect differ.
- Feather must apply to the mask edge preview and remain bounded; it must not blur the original image or the entire result.
- Alpha calibration must use quantile-based image evidence instead of assuming a single fixed threshold for every cutout result.
- Foreground restore is explicit, selection-gated, and uses the original base image only inside the user-selected region with a bounded minimum alpha.
- Refine history must be reversible with the same undo/redo model as annotations.
- A stale cutout result or stale refine response must not append to the active version rail after the source generation changes.
- The refine UI must not submit `/api/generate` or call a provider.

## Before / After Semantics

- **Before** means the current base source.
- **After** means the selected result version.
- **Compare** means a slider between the two.
- **Use as next base** is the only action that may change the base version.
- A successful cutout result is a browseable transparent-background version, not a replacement of the source canvas.

This matters because the workbench already separates `selectedVersionId` from `baseVersionId`. V4 should keep that split intact.

## Model Filtering and Alias Separation

Current behavior already separates:

- provider selection
- model selection
- explicit capability confirmation
- transport profile allowlisting

V4 should keep those concerns separate and visible:

- Show only enabled image providers.
- Show model labels as labels, not as proof of capability.
- Keep the actual selected model string in the submit payload.
- Require explicit confirmation before using an untrusted OpenAI-compatible model for precision edit.
- Revalidate the current rendered endpoint/model pair before authorizing.

In short: alias is presentation, capability is authorization, and model choice is the payload.

As user-confirmed on 2026-09-02, `gpt-image2-b` and similar names are `gpt-image-2` channel/account aliases. They must remain labels unless the selected provider/model pair is explicitly authorized with matching capability metadata.

## Help Entry Layout

Keep the quick help affordance exactly where it is most useful:

- in the precision-workbench title row
- next to the canvas dimensions
- as a compact trigger with a popover
- keyboard reachable and closable with Escape

V4 also includes a top-level icon+text action labeled `文档说明`:

- It appears in the precision workbench's top control/header area, not inside the canvas popover.
- It opens an independent in-app precision-edit help dialog or page.
- It is reachable by keyboard, exposes dialog/page semantics, and returns focus to the triggering control on close.
- It covers the full workflow: load source, annotate, select/move, arrow endpoint scaling, pure size expansion, cutout refine, model confirmation, before/after compare, and safety boundaries.
- It may link outward to project documentation, but the primary help experience should be in-app.

## Responsive and Accessible Contract

Acceptance standard:

- no horizontal overflow on narrow screens
- canvas shell preserves source aspect ratio
- resize handle remains at least 44px on touch layouts
- compare slider remains usable with pointer and keyboard
- help popover stays inside the viewport
- idle task panel still exposes status through aria-live
- saved preset feedback uses a polite live region
- `937x920`, `1000x994`, and `390x844` browser checks show no incoherent overlap, clipped help UI, or horizontal overflow
- the top `文档说明` action and compact canvas `?` popover both remain visible and independently operable at those viewports

## Test Matrix

| Area | Existing tests | Command | V4 expectation |
|---|---|---|---|
| Annotation validation | `tests/test_precision_edit_contract.py` | `pytest tests/test_precision_edit_contract.py` | Confirms current V1/V2/V3 contract rules remain fail-closed |
| Provider authorization and size gates | `tests/test_provider_precision_contract.py` | `pytest tests/test_provider_precision_contract.py` | Confirms model capability, size declarations, and allowlisted transport stay separate |
| Workbench UI and accessibility | `tests/test_precision_edit_ui.mjs` | `node tests/test_precision_edit_ui.mjs` | Confirms state, compare, help, resize, cutout, and responsive behavior |
| Selection and move interaction | V4 UI regression coverage | included in local final evidence | Existing rectangle/ellipse/brush/text objects can be selected, moved, and left within normalized canvas bounds without corrupting history |
| Arrow endpoint scaling | V4 UI regression coverage | included in local final evidence | Dragging one arrow endpoint changes only that endpoint, preserves the opposite endpoint, clamps to canvas bounds, and records one undo step |
| Runtime payload purity for no-annotation resize | V4 UI/backend regression coverage | included in local final evidence | Pure size expansion payload omits annotation fields and `image_data_list` entirely, including empty/null values |
| Three-viewport browser acceptance | local structural coverage; real visual inspection remains UNVERIFIED | manual browser run at `937x920`, `1000x994`, and `390x844` still required | Confirms source image, compact `?`, top `文档说明`, model picker, size controls, compare surface, cutout refine controls, and task panel do not overlap or overflow |
| Cutout refine frontend | V4 UI regression coverage; real refine POST remains UNVERIFIED | included in local final evidence plus manual POST acceptance still required | Confirms real mask state, feather-bounded preview, checkerboard transparency, undo/redo, and no provider generation submit |
| Error surface safety | `tests/test_generation_error_ui.mjs` | `node tests/test_generation_error_ui.mjs` | Confirms structured error handling and no raw status leakage |
| Translation coverage | `tests/test_i18n.mjs` | `node tests/test_i18n.mjs` | Confirms precision strings and help copy exist in both languages |
| Cutout adapter contract | `tests/test_cutout_onnx.py` | `pytest tests/test_cutout_onnx.py` | Confirms alpha PNG, executable gating, and safe persistence |
| Generation controls regressions | `tests/test_generation_controls.py`, `tests/test_stop_generation_ui.mjs` | `pytest tests/test_generation_controls.py` and `node tests/test_stop_generation_ui.mjs` | Confirms precision mode does not break shared generation controls |
| V4 no-annotation size submit | V4 UI/backend regression coverage | included in local final evidence | Resize-only first submit and retry omit annotation fields and `image_data_list` entirely |

## Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Future refactor can merge resize-only and annotated edit again | A resize-only path becomes fragile if it silently inherits annotation requirements | Keep the explicit no-annotation submit contract and regression coverage |
| Empty annotation fields can accidentally look harmless | Empty/null values still widen the backend mode surface and can confuse routing | Preserve complete omission of annotation fields and `image_data_list` in runtime payloads for pure size expansion |
| Model list refresh can stale out authorization state | A user can see one endpoint/model, then the provider list changes underneath | Revalidate the rendered option pair before authorization and submit |
| Cutout and version append are async | A late response can append the wrong version if source generation changed | Keep the existing source-generation tokens and stale-response guards |
| Mobile layout regressions are easy | Help popovers and compare controls can overlap or clip | Keep the current viewport and aria tests in the matrix |
| Feather can drift into a global image effect | A vague UI control would become untestable and surprise users | Keep feather serialized explicitly and bounded to the selected mask edge |

## Explicit Non-Goals

- No full Photoshop clone.
- No layers panel.
- No general-purpose raster effects.
- No provider-backed cutout refine.
- No implicit model guessing.
- No silent capability upgrades from alias text.
- No source replacement when browsing versions.
- No provider/VPS/deployment/store work in this phase.
- No arbitrary shell, network, or filesystem access from the precision UI.

## Sources

- `main.py`
- `providers/__init__.py`
- `config.py`
- `static/index.html`
- `static/js/app-all.js`
- `static/css/app.css`
- `tests/test_precision_edit_contract.py`
- `tests/test_provider_precision_contract.py`
- `tests/test_precision_edit_ui.mjs`
- `tests/test_cutout_onnx.py`
- `tests/test_generation_error_ui.mjs`
- `tests/test_i18n.mjs`
- `tests/test_generation_controls.py`
- OpenAI Images guide: `https://platform.openai.com/docs/guides/images`
- OpenAI Images API reference: `https://platform.openai.com/docs/api-reference/images`
