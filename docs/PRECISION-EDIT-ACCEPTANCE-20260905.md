# Precision Edit Acceptance Evidence - 2026-09-05

## Scope

This record freezes the local evidence for the precision-edit and cutout follow-up.
It is not a Release approval. Runtime models, user images, prompts, credentials,
screenshots, and temporary test artifacts are deliberately excluded.

## Verified

- **VERIFIED / HEADED ANNOTATION UAT PASS:** On a non-sensitive blue-and-green
  geometric test image at `937x920`, rectangle, ellipse, arrow, and brush
  annotations were each created and edited a second time successfully. At
  `390x844`, the workbench had no horizontal overflow. No private asset was
  generated or accessed. This narrow headed observation is associated with
  `7677073` and does not prove upstream output quality or release readiness.
- The local laboratory ran GenBox 2.6.6 in development mode on port 8892.
- Full Python regression passed: `1429 passed in 75.43s`.
- Precision-edit UI/static, cutout installer UI, and i18n Node checks passed.
- `gpt-image2-b` was accepted as the user-confirmed upstream alias and preserved
  as the outbound model name.
- A real upstream precision edit with intentionally mismatched input MIME metadata
  succeeded after transport normalization and returned a `1024x1024` result.
- Automated loaded-canvas browser UAT coverage passed at `390x844`, `937x920`, and
  `1200x800`. It covers canvas hit targeting, middle-button zoom reset and pan,
  image-only fullscreen, source-menu bounds and keyboard interaction, and
  workbench fullscreen exit. This is automated test evidence, not independent
  human acceptance.
- U2-Net and user-imported MODNet passed local technical checks: CPU-only execution,
  blocked Python network access, same-size RGBA PNG output, and alpha extrema of 0
  to 255. U2-Net remains the default; MODNet remains experimental. This does not
  satisfy the cutout structural gate or human-image quality acceptance.
## Verified Safety Behavior

- The `1536` strict-size probe returned `1376x768`. Strict preserve mode rejected it
  with `precision_edit_output_size_mismatch`; it was not allowed to replace the
  editable base image.
- The `1792` strict-size probe in this run ended in `ReadTimeout`, so it has no
  verified output and is explicitly `UNVERIFIED` for this run.
- The application keeps strict mode fail-closed. `fit_crop` remains an explicit local
  adaptation policy and is never presented as native upstream sizing.

## Supplemental Headed Lab Result - 2026-09-05

- **VERIFIED / REAL UPSTREAM STRICT REJECTION:** With the user-approved local
  test image, one minimal rectangle annotation, the configured `gpt-image2-b`
  alias, and strict target `1792x768`, the upstream returned `2048x864`.
  GenBox rejected the response with `precision_edit_output_size_mismatch` and
  did not replace the editable base image or create a result version. This is
  a successful fail-closed validation, not a native `1792x768` output PASS.
- The stored size-confirmation UI describes a user decision to allow a request;
  it is not evidence that the upstream has already returned that exact size.
  The visible wording was updated accordingly.

## Supplemental Local Regression - 2026-09-06

- **VERIFIED / LOCAL CUTOUT GATE:** The current local U2-Net and user-imported
  MODNet adapters each passed the offline synthetic full-body gate with CPU execution,
  blocked Python networking, same-size RGBA output, and alpha extrema of `0..255`.
  This remains technical-chain evidence only; legs, hair, soft edges, and complex
  backgrounds still require authorized human-image acceptance.
- **VERIFIED / LOCAL REGRESSION:** The strict-size and alias-focused Python
  suites passed `171` tests, and the isolated session-gallery browser contract
  passed `5` tests. The mismatch recovery text now correctly directs the user
  to choose another target size or an explicit local-adaptation choice; it does
  not imply that enabling Change size makes the upstream return an exact size.
- **VERIFIED / FULL REGRESSION:** The full local Python suite passed `1435`
  tests. Precision i18n and UI-static checks also passed after the dedicated
  image-fullscreen action and nested strict-size task-log notice were added.

## Supplemental Authorized Local Backend Verification - 2026-09-06

- **VERIFIED / REAL UPSTREAM SUCCESS:** A non-sensitive generated geometry
  image with one minimal rectangle annotation completed through the configured
  `gpt-image2-b` precision-edit path. The local library stored an RGB PNG at
  `1024x1024`. No user image, user prompt, credential, endpoint, or raw
  provider response is retained in this record.
- **VERIFIED / SECOND BACKEND EDIT:** The preceding generated result was used
  as the source for one further minimal annotated request through the same
  configured path. That request completed and stored another `1024x1024` RGB
  PNG. This verifies sequential backend input/output compatibility at the
  preserve-size target.
- **VERIFIED / TARGETED REGRESSION:** Provider precision/strict-size/extension
  tests passed `358`; precision UI-static and i18n checks passed alongside
  them. This supplements, rather than replaces, the earlier full `1435` Python
  suite result.
- **BOUNDARY:** The second request was a controlled local backend submission.
  It is not a headed proof that the workbench `设为下一次底图` UI action updated
  the current browser session before a second UI submission. Non-square native
  strict-size success also remains unverified; strict mismatch rejection is
  intentionally unchanged.

## Supplemental Workbench And Workflow-History Acceptance - 2026-09-06

- **USER-CONFIRMED / HEADED SEQUENTIAL RESULT:** The current precision
  workbench completed two successful sequential results. The session gallery
  displayed `2` results, the selected version advanced to the second result,
  and the task reached its completed state. This supersedes the earlier
  headed-workbench limitation above. No user image, prompt, raw log, endpoint,
  or credential is retained in this evidence record.
- **VERIFIED / WORKFLOW-HISTORY EXPERIENCE:** A gallery Pill now sits below
  the toolbar and is collapsed by default. Expanding it provides a redacted
  cross-session workflow browser, a two-level operation-card hierarchy,
  restoration into the precision workbench, and date-range plus workflow
  filtering. The public projection contains only safe summaries, opaque
  identifiers, dates, counts, dimensions, availability, and sanitized media
  references.
- **VERIFIED / ACCEPTANCE REGRESSION:** The complete Python suite passed
  `1440` tests. Precision UI and i18n Node contracts, JavaScript syntax
  validation, and the repository diff check also passed.
- **RETAINED BOUNDARIES:** Native strict-size success for a non-square target
  remains unverified. If the original source image was not persisted, workflow
  restoration can recover only the latest available edited result. Cutout
  adapters still require authorized real-image quality review for legs, hair,
  soft edges, and complex backgrounds.

## Commits Frozen By This Record

- `d73906e` - strict size contract
- `3f2655e` - fail-closed multi-algorithm cutout adapters
- `a097516` - precision workbench, gallery, fullscreen, and model UI
- `15bb399` - cutout algorithm boundaries and user documentation
- `ea446ed` - offline cutout quality gate
- `3cfec77` - precision-edit provider transport and MIME repair
- `a2fd40d` - idempotent MODNet refresh and pure-resize UI behavior
- `b239eb2` - precision workspace controls
- `fab6418` - precision-edit UI transitions
- `7677073` - loaded precision-canvas UAT gaps
- `71e159b` - temporary cutout PNG ignore rule

## Still Unverified

- Stable native strict output for the configured upstream across repeated calls;
  the 1536 probe was rejected at `1376x768`, the earlier 1792 probe ended in
  `ReadTimeout`, and the later 2026-09-05 `1792x768` probe returned `2048x864` and
  was correctly rejected.
- Independent human acceptance beyond the narrow headed annotation UAT above,
  including image-only fullscreen details outside the accepted sequential
  result workflow. The current two-result session, version selection, task
  completion, and workflow-history surface are accepted; broader visual review
  remains separate.
- Restoration of an unpersisted original source image. In that case the
  history workflow can restore only its latest available edited result.
- The cutout structural gate and authorized human-sample cutout quality for legs,
  hair, semi-transparent edges, and complex backgrounds.
- MODNet redistribution/packaging authorization. It remains user-imported and
  excluded from Release assets.
- Clean-clone build, GitHub push, version/tag, and GitHub Release gates. Release
  remains blocked until the preceding evidence is complete.

## Resume Order

1. Keep strict mode unchanged and investigate upstream size consistency without
   weakening output validation.
2. Run authorized human-sample quality acceptance for U2-Net and MODNet.
3. Perform clean-clone and Release gates only after the prior evidence is complete.
