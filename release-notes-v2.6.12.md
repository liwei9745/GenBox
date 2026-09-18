# GenBox v2.6.12: Video Workbench Interaction And Diagnostics

Release date: 2026-09-18

This patch release builds on the native Google video work from v2.6.11. It
focuses on image-to-video asset controls, preview layout, responsive behavior
and safe failure diagnostics. It does not change the published Provider wire
contracts or issue paid generation requests during release automation.

## Highlights

- Stable vertical reference-role controls with an independent scrolling
  thumbnail area.
- A combined upload/library action card fixed at the top-right of the asset
  workspace.
- Compact video result cards and honest placeholder states that open the full
  preview only after an explicit click.
- Independent live-log layout plus prompt composer growth, scrolling and manual
  resizing.
- Stage-specific native Google transport, response parsing and local-save
  diagnostics without exposing upstream bodies or retrying uncertain requests.
- Responsive browser regression coverage for uploads, gallery dismissal,
  scroll stability and layout behavior.

### GPT Image Expansion Size Presets

| Aspect ratio | 1K | 2K | 4K |
|---|---|---|---|
| 1:1 square | 1024 × 1024 | 2048 × 2048 | 2880 × 2880 |
| 16:9 landscape | 1168 × 656 | 2048 × 1152 | 3840 × 2160 |
| 9:16 portrait | 656 × 1168 | 1152 × 2048 | 2160 × 3840 |
| 4:3 landscape | 1024 × 768 | 2048 × 1536 | 3328 × 2480 |
| 3:4 portrait | 768 × 1024 | 1536 × 2048 | 2480 × 3328 |
| 3:2 landscape | 1008 × 672 | 2016 × 1344 | 3520 × 2352 |
| 2:3 portrait | 672 × 1008 | 1344 × 2016 | 2352 × 3520 |
| 21:9 ultrawide | 1344 × 576 | 2544 × 1088 | 3840 × 1648 |
| 9:21 tall portrait | 576 × 1344 | 1088 × 2544 | 1648 × 3840 |

## Boundaries

- Omni video editing, multi-turn sessions and additional online editing
  providers are not included in this patch.
- Native video remains single-submit with no automatic retry, credential
  rotation or gateway fallback.
- Errors do not contain API keys, prompts, private paths or raw upstream
  responses.
- The independent video editing workbench remains in WB-0 documentation and
  feasibility preparation; it is not shipped functionality.

## Download And Deployment

Tag workflows build Windows, macOS and Linux clients, source and Docker Compose
archives, checksums and a smoke-tested GHCR image:

```text
ghcr.io/liwei9745/genbox:2.6.12
```

Availability is determined by the published GitHub Release assets. Back up
configuration and media before upgrading and retain the previous package or
image for rollback.

This release does not claim universal support for third-party gateways;
commercial-use rights are not established by this release. Automatic update
application and restart remain disabled.
