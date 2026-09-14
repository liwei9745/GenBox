# GenBox v2.6.9: Precision Edit Compatibility and Size Fixes

Release date: 2026-09-14

Preserves accepted GPT annotation editing, expansion, version comparison and
local person-cutout workflows while improving Gemini / Nano Banana connections.

## Fixes

- Prevent double decompression of bounded gateway responses.
- Send explicit 1K / 2K / 4K tiers for Klong Nano Banana edits instead of
  leaving target pixel dimensions to ambiguous upstream tier inference.
- Accept validated inline image responses; retain size, MIME, pixel and
  download safety checks.
- Freeze each queued task's selected model and configuration.
- Isolate reversible connection overrides and exact-size grants per model.

## Acceptance and Limits

Most current Klong `nano-banana2` presets are **USER-CONFIRMED**.
A synthetic live expansion to `2752x1536` returned exactly that size, passing
strict checks without local cropping/scaling, using one POST without retry.

`6144x768` returned `5856x704` and is labelled experimental for observed
geometry mismatch. `2048x8192` is within the target envelope, but its observed
`2048x8256` output exceeds the application's 8192-side safety limit and remains
rejected. That preset now displays an output-limit warning.

A resolution tier is not a universal 4096-pixel side cap: matching `3392x5056`
output has already been recorded. These warnings do not revoke saved grants,
modify GPT presets, or certify other gateways. HTTP 503, credentials and
transport errors are not size-support evidence.

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

## Configuration

Select the endpoint and `nano-banana2`, prefer Auto connection, then choose a
model-size preset and composition guidance. Authorize undeclared sizes only
when intending an explicit trial. Restore Auto connection to clear manual
overrides. Local connection inspection makes no upstream request and cannot
guarantee model availability.

Strict output checks, source preservation and no automatic paid-edit retry
remain unchanged. Release automation makes no paid calls and includes no user
media, prompts, credentials or runtime logs. Cutout weights remain
operator-provided and are not bundled; their commercial-use rights are not
established by this release. Automatic update application and restart remain
disabled.
