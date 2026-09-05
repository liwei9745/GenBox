# Precision Edit Acceptance Evidence - 2026-09-05

## Scope

This record freezes the local evidence for the precision-edit and cutout follow-up.
It is not a Release approval. Runtime models, user images, prompts, credentials,
screenshots, and temporary test artifacts are deliberately excluded.

## Verified

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
  the 1536 probe was rejected at `1376x768`, and the 1792 probe ended in
  `ReadTimeout` during this run.
- A second annotated precision edit that returns exactly the prior base dimensions
  and becomes a new editable session version.
- Independent human acceptance for every canvas editing gesture, image-only
  fullscreen with loaded media, and session-thumbnail date highlighting. The
  three-viewport loaded-canvas contract is covered by automated browser evidence.
- The cutout structural gate and authorized human-sample cutout quality for legs,
  hair, semi-transparent edges, and complex backgrounds.
- MODNet redistribution/packaging authorization. It remains user-imported and
  excluded from Release assets.
- Clean-clone build, GitHub push, version/tag, and GitHub Release gates. Release
  remains blocked until the preceding evidence is complete.

## Resume Order

1. Keep strict mode unchanged and investigate upstream size consistency without
   weakening output validation.
2. Complete headed browser UAT with a loaded image and a successful session result.
3. Run authorized human-sample quality acceptance for U2-Net and MODNet.
4. Perform clean-clone and Release gates only after the prior evidence is complete.
