# GenBox v2.6.11: Native Google Video And Model Workbench

Release date: 2026-09-17

## Highlights

- Native Veo video submission, polling and authenticated local download, with
  first-frame, last-frame and reference-image payloads aligned to the SDK.
- Native Gemini Omni Interactions generation using inline video delivery and
  `store=false`, preserving the interaction storage opt-out.
- Model-specific video dimensions and duration controls, searchable model
  selection, provider grouping and output-capability filters.
- Guided Provider configuration and presets; discover models using unsaved
  credentials without returning to the first step. Google discovery paginates
  and uses the effective endpoint credential.
- Generation progress placeholders and bottom-right notifications; restored
  image-to-video upload, corrected composer overflow, logs and failure states.

## Validation And Boundaries

### Precision Edit Size Baseline

Existing presets are retained; endpoint availability still requires testing.

| Aspect | 1K | 2K | 4K |
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

The user confirmed manual acceptance of this work, including real Veo and Omni
generation. Automated tests cover request contracts, UI controls, error privacy,
media limits, cancellation and single-submission behavior. The release process
does not issue additional paid generation requests.

Native Google requests do not automatically retry, rotate credentials or fall
back to custom gateways. Omni editing, extension and multi-turn sessions remain
outside this release. Native seed, inference-step and negative-prompt controls
are not enabled. Account entitlement, region and gateway compatibility vary.
This release does not claim universal support for third-party gateways;
commercial-use rights are not established by this release.
Automatic update application and restart remain disabled.

Tag workflows build Windows, macOS and Linux clients, source and Compose
archives, checksums and the smoke-tested GHCR image:

```text
ghcr.io/liwei9745/genbox:2.6.11
```

Availability is determined by completed workflow artifacts. No additional
architectures are claimed. Back up configuration and media before upgrading;
keep the previous package/image and backup for rollback. User credentials,
media and local test history are excluded.
