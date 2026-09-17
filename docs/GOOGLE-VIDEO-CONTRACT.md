# Google Native Video Contract

## Evidence

VERIFIED documentation retrieval on 2026-09-17 via Agent Reach/Jina:

- https://ai.google.dev/gemini-api/docs/veo?hl=en
- https://ai.google.dev/gemini-api/docs/omni
- https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash
- https://ai.google.dev/gemini-api/docs/interactions
- https://github.com/googleapis/python-genai/blob/6669bb635753e5071e489038945d494be58094bc/google/genai/models.py
- https://github.com/googleapis/python-genai/blob/6669bb635753e5071e489038945d494be58094bc/google/genai/_gaos/types/interactions/videoresponseformat.py

VERIFIED SDK source retrieval via `gh api` on 2026-09-17: `_Image_to_mldev`
serializes `bytesBase64Encoded` and `mimeType` directly; reference images and
last frames use that converter too. Veo guide REST examples showed `inlineData`,
which conflicts with this SDK contract. The adapter now follows the pinned SDK
converter for all three image roles. Tests use fixtures derived from that
independent converter instead of copying the original implementation.

The Veo guide says seed is available, but the pinned SDK rejects seed in Gemini
Developer API mode. The adapter conservatively hides/rejects seed until that
discrepancy can be resolved. This does not change custom gateway seed support.

Local mock and browser tests are not live Google generation evidence.
Three local history entries on 2026-09-17 confirm HTTP 400 for both Omni aliases
and Veo 3.1. Their upstream bodies were discarded by the previous implementation:
the historical Omni cause cannot be reconstructed.

USER-CONFIRMED after that repair: Veo generation succeeds; Omni still returns
HTTP 400 identifying `delivery` and `store`. VERIFIED documentation re-read on
2026-09-17: Omni examples return inline Base64 MP4 in REST `steps[].content[]`;
the SDK explicitly supports `delivery="inline"`. Interactions documents
`store=false` as the storage opt-out. The guide separately recommends URI
delivery and stateless operation but does not establish their compatibility.
INFERENCE: the reported error points to this combination, not Veo routing.
Omni now explicitly uses inline delivery with `store=false`; this avoids the
suspect combination without silently opting users into interaction retention.
USER-CONFIRMED on 2026-09-17: all manual acceptance passed after the inline
change, including real Omni and Veo generation. No agent-run paid retry ran.

## Routing And Transport

The effective endpoint's exact hostname selects the native Google adapter.
Its API key is used only in `x-goog-api-key`; generated requests target the
fixed HTTPS Google API origin. Custom gateways keep their existing adapters.
The first configured active endpoint is used, with no key rotation or retry.

Veo posts to `models/{model}:predictLongRunning`, polls the returned validated
operation name, extracts `response.generateVideoResponse.generatedSamples`,
and downloads the first result. Omni posts to `/interactions` with
`background=false`, `store=false`, `stream=false`, and inline delivery. It extracts
Base64 MP4 from REST `steps[].content[]`, decodes in bounded blocks and saves
atomically with signature validation. The Omni response limit allows Base64
expansion of the 256 MiB video cap plus 1 MiB of JSON envelope; other JSON
responses retain their 8 MiB cap. Cancellation interrupts response reading
and decoding. Neither Base64 media nor interaction IDs enter public task data.
The existing validated URI/file-state download path remains compatible if an
upstream response returns a URI; it never retries a generation or changes store.
The SDK-only `output_video` shortcut is not treated as a REST contract.

Local asynchronous tasks expose a UUID and local file route, not API keys,
upstream operation IDs, signed remote URLs or raw upstream errors. Downloads
have a 256 MiB cap, use a temporary file and check MP4 signature before rename.
Only the Google API origin and Google Storage redirects are allowed. API keys
are never forwarded to Storage. Cancellation stops local polling/download;
it does not claim cancellation of upstream billing or already submitted work.

Error responses are read with a 64 KiB diagnostic limit. Only allowlisted
status values, known parameter names and fixed category labels are retained.
Arbitrary upstream messages, field paths, descriptions and bodies are never
returned or logged. Errors identify submission, operation polling, file polling
or download; malformed/oversized error bodies preserve a generic HTTP failure.

## Parameters

- Veo 3.1: 4, 6, 8 seconds; 720p/1080p/4k; Lite excludes 4k.
  1080p/4k and reference-image requests require 8 seconds.
- Veo 3.0: conservatively exposes 8 seconds, 720p/1080p.
- Veo 2.0: 5 through 8 seconds, 720p.
- Omni: 360p/720p/1080p/4k; model-controlled 3-10 second output. No explicit
  duration request field was verified, so no synthetic duration field is sent.
- Native output FPS is 24. The UI hides editable frame-count and `8n+1`
  constraints. Those are not Google-native video inputs.
- First-frame, reference, first/last image combinations are mapped separately.
  Unsupported role/count combinations fail before a generation POST.
- No inference-step, negative-prompt or seed field is sent. Native seed is
  rejected locally, for the SDK compatibility reason described above.

Input is limited to local PNG/JPEG/WebP data URLs, max 10 MiB per image; the
adapter verifies the image container and MIME match before submitting, and
never fetches arbitrary caller-supplied image URLs. Editing uploaded
videos, extending previous interactions and multi-turn sessions are not
implemented. A failed native request never falls back to Flow2API.

## Resume

Run `tests/test_google_native_video.py`, `tests/test_google_video_browser.py`
and the existing video suites before changing contracts. Existing manual
acceptance is user-confirmed; any additional paid call still requires explicit
authorization and must never be triggered by release automation.
