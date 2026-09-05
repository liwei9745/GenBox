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
  succeeded after transport normalization and returned a 1024x1024 result.
- Two real source-only resize requests produced exact 1792x768 PNG outputs.
- U2-Net and user-imported MODNet passed the local offline quality gate: CPU-only
  execution, blocked Python network access, same-size RGBA PNG output, and alpha
  extrema of 0 to 255. U2-Net remains the default; MODNet remains experimental.
- The headed local UI pass verified gallery source loading, displayed source prompt,
  session date-picker expansion and quick ranges, model visibility menu opening,
  workbench fullscreen toggle, and the experimental MODNet label.

## Verified Safety Behavior

- A real second request used a successful 1792x768 image as its source and included
  a rectangle annotation. The upstream returned an image, but its actual dimensions
  were 2048x864. Strict preserve mode rejected it with
  `precision_edit_output_size_mismatch`; it was not allowed to replace the editable
  base image.
- Previous strict resize probes also observed dimensions differing from requested
  values. The application keeps strict mode fail-closed. `fit_crop` remains an
  explicit local adaptation policy and is never presented as native upstream sizing.

## Commits Frozen By This Record

- `d73906e` - strict size contract
- `3f2655e` - fail-closed multi-algorithm cutout adapters
- `a097516` - precision workbench, gallery, fullscreen, and model UI
- `15bb399` - cutout algorithm boundaries and user documentation
- `ea446ed` - offline cutout quality gate
- `3cfec77` - precision-edit provider transport and MIME repair
- `a2fd40d` - idempotent MODNet refresh and pure-resize UI behavior

## Still Unverified

- Stable native strict output for both 1536x864 and 1792x768 from the configured
  upstream across repeated calls.
- A second annotated precision edit that returns exactly the prior base dimensions
  and becomes a new editable session version.
- Headed interaction completion for every canvas editing gesture, image-only
  fullscreen with loaded media, session-thumbnail date highlighting, and all three
  target viewport sizes.
- Authorized human-sample cutout quality for legs, hair, semi-transparent edges,
  and complex backgrounds.
- MODNet redistribution/packaging approval. It remains user-imported and excluded
  from Release assets.
- Clean-clone build, GitHub push, version/tag, and GitHub Release gates.

## Resume Order

1. Keep strict mode unchanged and investigate upstream size consistency without
   weakening output validation.
2. Complete headed browser UAT with a loaded image and a successful session result.
3. Run authorized human-sample quality acceptance for U2-Net and MODNet.
4. Perform clean-clone and Release gates only after the prior evidence is complete.
