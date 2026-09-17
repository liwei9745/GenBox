# GenBox v2.6.10: Gemini Official API Compatibility Repair

Release date: 2026-09-16

This release preserves the accepted Precision Edit, smart expansion, version
comparison, and local cutout workflows while correcting the distinction between
the native Google Gemini API and OpenAI-compatible gateways.

## Highlights

- Native Gemini connectivity checks use `GET /v1beta/models` with
  `x-goog-api-key`.
- Official model-list failures retain their real cause instead of falling back
  to an OpenAI `/models` request.
- Gemini image requests use the documented `TEXT` / `IMAGE` response modality
  values.
- HTTP 429 failures retain bounded, redacted quota identifiers and retry hints.
- Provider models default to enabled and expose a clear `停止使用` / enable
  primary action.
- Provider and Precision workflow loading reuse in-flight requests and defer
  collapsed gallery rendering.

## Configuration

For the official Gemini API, use:

- Base URL: `https://generativelanguage.googleapis.com`
- Protocol: `gemini`, or `auto` with that URL
- Pull models first, then select the complete model ID returned by Google

For an OpenAI-compatible gateway, use its documented compatible Base URL and
select `openai`, or use automatic detection when the URL is unambiguous.
Gateway support does not claim universal support for every Gemini model,
resolution, or image capability.

## Size Compatibility Baseline

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

## Verification and limits

The release passed 160 focused Gemini, Provider, protocol, security, and UI
regression tests plus a read-only model-list connectivity check. No paid image
generation was performed as part of the release process. A successful model
list does not establish project image-generation quota; Google 429 responses
require checking project-level quota and retry guidance. commercial-use rights
are not established by this release. Automatic update application and restart
remain disabled. This release does not claim universal support for all
third-party relay endpoints.
