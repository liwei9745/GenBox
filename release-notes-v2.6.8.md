# GenBox v2.6.8 - Precision Edit Major Update

Release date: 2026-09-10

Choose a model, choose a size, and mark exactly where you want a change.
This release brings model-first resizing, visual annotation editing, local
person cutout, workflow restoration, and a first-use quick-start guide.

## GPT Resize Presets

**USER-CONFIRMED:** The user accepted the configured GPT target model
`gpt-image-2.5-c`. This is an endpoint model identifier, not a claim about
official OpenAI model names or every compatible provider.

| Aspect | 1K tier | 2K tier | 4K tier |
|---|---|---|---|
| 1:1 | 1024 × 1024 | 2048 × 2048 | 2880 × 2880 |
| 16:9 | 1168 × 656 | 2048 × 1152 | 3840 × 2160 |
| 9:16 | 656 × 1168 | 1152 × 2048 | 2160 × 3840 |
| 4:3 | 1024 × 768 | 2048 × 1536 | 3328 × 2480 |
| 3:4 | 768 × 1024 | 1536 × 2048 | 2480 × 3328 |
| 3:2 | 1008 × 672 | 2016 × 1344 | 3520 × 2352 |
| 2:3 | 672 × 1008 | 1344 × 2016 | 2352 × 3520 |
| 21:9 | 1344 × 576 | 2544 × 1088 | 3840 × 1648 |
| 9:21 | 576 × 1344 | 1088 × 2544 | 1648 × 3840 |

Tiers are preset categories; exact pixel dimensions are listed above, and some
ratios are pixel-aligned approximations. Model size validates actual output
strictly. An undeclared size requires an explicit trial authorization scoped
to the endpoint, model and exact size. Crop to fit performs local cropping and
scaling after one online edit. Composition guidance remains editable.

## Visual Editing And Local Cutout

- Point with arrows, mark regions with rectangles or ellipses, or paint a
  selection and describe the intended change. Editing accuracy depends on the model.
- Move and resize annotations, undo/redo, compare versions, and restore previous
  workflows for further editing.
- Restored results now show their own actual dimensions and available version
  timestamps, not stale source dimensions or claimed photo capture times.
- One-click person cutout uses a configured, validated local model without
  sending the image to an online generation service. Refine edges, feather
  boundaries and recover foreground in the dedicated local workbench.
- Online AI removal is separate from local cutout and still uses the selected
  editing provider.

## Workflow And Safety

- Model selection precedes size selection; capabilities and trial state follow
  the selected endpoint/model.
- Model visibility is grouped, with group selection and retained scroll/focus.
- Short instructions and a one-time clickable quick-start guide help new users.
- Gemini, Qwen and other vendors still await separate manual acceptance.
  Automated tests do not replace real-provider acceptance.
- Trial authorization never submits generation. Image-edit POST requests are
  not automatically retried; a failure or 503 does not prove a size unsupported.
- ONNX checkpoints are **not bundled**. Supply a compatible checkpoint that
  passes integrity and execution checks. Automatic network installation remains
  disabled; provenance, training-data lineage and commercial-use rights remain
  UNVERIFIED. Their commercial-use rights are not established by this release.

This release does not claim universal support across third-party endpoints,
aliases or vendors.

## Upgrade

Back up `storage/` and manually download the appropriate release package.
Desktop clients include Python; local model weights are separate.
Docker Compose uses `ghcr.io/liwei9745/genbox:2.6.8`.
Automatic update application and restart remain disabled.
Desktop/Docker default to port `8891`; source development defaults to `8892`.
