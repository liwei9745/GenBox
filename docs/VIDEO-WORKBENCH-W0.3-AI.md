# Video Workbench W0.3: Online AI Provider Feasibility

Date: 2026-09-18
Revision: 0.1
Status: **Research PASS; live online-edit qualification BLOCKED/UNVERIFIED**
Owner: AI adapter specialist
Parent phase: WB-0 / G2
Scope: Online video-editing capability, provider-neutral contract, and recovery
boundary. This report does not implement an adapter, upload private media, or
make a paid generation request.

## Executive Decision

**VERIFIED / RESEARCH:** An online video-editing workbench is technically
feasible if GenBox treats provider support as a capability-qualified adapter
rather than as a model-name feature. Google Gemini Omni Flash is a credible
first adapter candidate because Google's current documentation describes
uploaded-video editing through the Files API and Interactions API.

**VERIFIED / LOCAL:** GenBox's current native Google adapter is a video
**generation** adapter. It supports text-to-video, image-to-video, and
first/last/reference-image generation. It does not upload source videos for
editing, use the Files API for input media, maintain an Interactions session,
or reconcile a submitted edit after restart. The existing adapter must not be
described as source-video editing support.

**PROPOSED:** Freeze the provider-neutral canonical edit intent and capability
descriptor in W0.5. Implement the first online-edit adapter only after the
source-video upload shape, privacy disclosure, remote-handle lifecycle,
submission recovery, and one authorized live edit are separately accepted.

**BLOCKER:** Documentation and mock fixtures cannot qualify a live editing
profile. A user-authorized, synthetic or explicitly redistributable source clip
is still required for VA-17. No such call was made in this research pass.

## Evidence Discipline

The following labels are used throughout this report:

- **VERIFIED / OFFICIAL:** observed in a current first-party API or SDK
  source on 2026-09-18.
- **VERIFIED / LOCAL:** observed in the GenBox checkout, tests, or local
  history; this is not live provider evidence.
- **USER-CONFIRMED:** accepted by the user in an earlier manual generation
  workflow; it does not extend to source-video editing.
- **UNVERIFIED:** plausible or documented in principle, but not proven for
  GenBox's exact provider, account, region, input combination, or adapter.
- **PROPOSED:** a workbench contract or implementation choice to review in
  W0.5.

## Official Sources And Pinned Revisions

All web sources below were re-read on **2026-09-18**. The URLs are kept in the
report so a later phase can revalidate changing limits before implementation.

| Source | Evidence used |
| --- | --- |
| [Gemini Omni video generation and editing](https://ai.google.dev/gemini-api/docs/omni) | Uploaded-video editing, Files API upload, Interactions input/output, URI/inline delivery, stateful editing, regional and duration limits |
| [Gemini Omni Flash model page](https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash) | Stable/preview model IDs, modalities, output duration/resolution/FPS and input-video limit |
| [Interactions API overview](https://ai.google.dev/gemini-api/docs/interactions/interactions-overview) | `store`, `background`, `previous_interaction_id`, retention and deletion behavior |
| [Interactions quickstart](https://ai.google.dev/gemini-api/docs/interactions/quickstart) | Stateful versus stateless request lifecycle |
| [Gemini Files API](https://ai.google.dev/gemini-api/docs/files) | Upload processing states, 48-hour user-file lifetime, project/per-file limits and download boundary |
| [Gemini video guide](https://ai.google.dev/gemini-api/docs/video) | Product-level distinction between Omni conversational editing and Veo generation/extension |
| [Veo guide](https://ai.google.dev/gemini-api/docs/veo) | Official Developer API generation, long-running operation and supported image/video-generation workflows |
| [Veo first/last frame guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-first-and-last-frames) | First/last-frame wire shape and model-specific duration/resolution values; Cloud/Agent Platform facts are not silently applied to Developer API |
| [Google Gen AI SDK `models.py`](https://github.com/googleapis/python-genai/blob/ad00721acd27258ae45180dbb7dadfaa8f8bed71/google/genai/models.py) | Pinned SDK source observed at commit `ad00721acd27258ae45180dbb7dadfaa8f8bed71` |
| [Google Gen AI SDK video response format](https://github.com/googleapis/python-genai/blob/ad00721acd27258ae45180dbb7dadfaa8f8bed71/google/genai/_gaos/types/interactions/videoresponseformat.py) | Pinned `delivery`, `resolution`, `aspect_ratio`, `duration`, and `gcs_uri` fields |
| [SAIS-FUXI/Omni-Video README](https://github.com/SAIS-FUXI/Omni-Video/blob/adcee0a4a5b439ad3615f825298221b21177d4e3/README.md) | First-party open-source local model taxonomy, v2v entry point, local hardware and inference parameters; repository commit `adcee0a4a5b439ad3615f825298221b21177d4e3` |
| [Omni-Video 2 technical report](https://arxiv.org/abs/2602.08820) | User-provided local PDF `2602.08820v2.pdf`, SHA-256 `7ccd3f4631df83bc8dd9111be47ee23a67cf3f82be68f9d2f308180753876269`; architecture, edit taxonomy and evaluation framing |

The SAIS repository and report are first-party research sources for a separate
model. They are not Google's API documentation and do not prove a hosted
endpoint, account availability, or online service-level behavior.

## 1. Current GenBox Boundary

### Existing native adapter

**VERIFIED / LOCAL** by source inspection:

- `providers/google_video.py::model_spec()` recognizes the exact native model
  IDs `gemini-omni-1.1-flash`, `gemini-omni-flash-preview`, selected Veo 3.1,
  Veo 3.0, and Veo 2 IDs.
- `build_request()` accepts only `ti2vid`, `i2vid`, and `keyframes`.
- The current input image path accepts local PNG/JPEG/WebP data URLs, verifies
  the decoded container and MIME, and limits each image to 10 MiB after
  decoding.
- Omni requests use `POST /v1beta/interactions` with `background=false`,
  `store=false`, `stream=false`, and inline video delivery. The response is
  parsed from REST `steps[].content[]`; the SDK convenience field
  `interaction.output_video` is not treated as a REST field.
- Veo requests use
  `POST /v1beta/models/{model}:predictLongRunning`, then bounded operation
  polling and an allowlisted download path.
- Native output is constrained locally to 24 FPS. The current adapter does not
  send inference-step, negative-prompt, or seed fields for native Google.
- `main.py` routes the official Google hostname to this adapter and leaves
  custom gateways on their existing generation protocols.

### Missing source-video-edit behavior

**VERIFIED / LOCAL / NOT IMPLEMENTED:**

- No source-video field is accepted by the current `VideoGenerateRequest`
  path.
- No Google Files API upload or `PROCESSING` to `ACTIVE` input-file poll exists
  in the current native adapter.
- No `previous_interaction_id` or stateful session store exists in the current
  generation task.
- No remote upload-handle retention, expiry, cleanup, or restart
  reconciliation contract exists.
- No source-video edit candidate lineage, segment hash, or explicit accept/
  discard workflow exists in the current generation route.

The existing `GOOGLE-VIDEO-CONTRACT.md` correctly keeps uploaded-video editing,
previous interactions, and multi-turn sessions outside the accepted generation
contract. This W0.3 report does not broaden that contract.

### Local fixture evidence

**VERIFIED / LOCAL / MOCK-ONLY:** `tests/test_google_native_video.py` uses a
synthetic PNG data URL and a tiny synthetic MP4 signature. The suite checks
request construction, image-role mapping, bounded inline decoding, malformed
output handling, safe errors, cancellation, polling, redirect allowlists, and
the rule that a failed or uncertain request is never automatically resubmitted.
`tests/test_google_video_browser.py` covers local browser/provider behavior.
These tests do not call Google and do not qualify source-video editing.

## 2. Official Google Capability Review

### 2.1 Gemini Omni Flash

**VERIFIED / OFFICIAL:** The current model documentation identifies:

- Stable model ID: `gemini-omni-1.1-flash`.
- Preview model ID: `gemini-omni-flash-preview`.
- Input modalities include text, image, and video; output is video.
- Output is documented as 3 to 10 seconds, 24 FPS, with 360p, 720p,
  1080p, and 4K output options.
- The Omni guide documents conversational editing with the Interactions API,
  including editing an uploaded video through a Files API URI.
- Input videos for editing or extension must be 10 seconds or less when
  uploaded. This is a provider limit, not a general GenBox project limit.
- The current guide allows up to three short video references in a prompt;
  each video reference is limited to 3 seconds. This is distinct from the
  10-second source-video editing limit and must not be collapsed into one
  generic "video duration" field.
- Audio references are not a supported Omni reference role in the current
  guide, and audio carried by a video reference is ignored for reference
  conditioning. The workbench must therefore keep audio policy separate from
  the visual-reference role.
- The guide warns that uploaded-video editing/extension is not available in
  the EEA, Switzerland, and the United Kingdom. Account, project, model
  rollout, safety and other regional restrictions still require preflight.
- The guide recommends Files API input for larger videos. Direct Base64 input
  is documented but is not the preferred workbench path for source videos.

**VERIFIED / OFFICIAL transport facts:**

- Input upload flow: `files.upload()` -> poll the File resource while it is
  `PROCESSING` -> use the file URI once it is `ACTIVE`.
- Interaction input contains a video URI and a text edit instruction.
- REST output is an `interaction` whose model output is in
  `steps[].content[]`. The REST example uses a video part with MIME and either
  inline Base64 data or a URI.
- `response_format` supports video delivery modes `inline` and `uri`, plus
  resolution and aspect-ratio fields. URI delivery is recommended for outputs
  larger than 4 MB; a returned remote file must be polled/validated before
  download.

**VERIFIED / OFFICIAL privacy and state facts:**

- Interactions are stored by default (`store=true`) so the server can support
  `previous_interaction_id`, background execution and observability.
- `store=false` opts out of interaction storage, but is incompatible with
  background execution and prevents use of `previous_interaction_id` for later
  turns.
- Stateful multi-turn video editing therefore requires an explicit retention
  and privacy disclosure. It cannot be added by simply reusing the current
  stateless `store=false` generation request.
- The Files API documents a 20 GB per-project storage limit, a 2 GB per-file
  maximum, and automatic deletion of user-uploaded files after 48 hours.
  User-uploaded files cannot be downloaded through the Files API; generated
  model output files can be downloaded. A GenBox adapter must not assume a
  remote input URI is durable.

**UNVERIFIED for GenBox:**

- The exact source-video MIME/count combinations that should be enabled for
  the workbench. The model page describes video inputs and up to three videos
  per prompt, but a first release should start with one selected source
  segment until the adapter proves each additional role.
- Whether source-video editing preserves, removes, or regenerates audio for
  every supported input. The current workbench contract proposes retaining
  original audio by default, but this is not evidence of Omni behavior.
- Whether a GenBox source segment with an audio stream should be stripped,
  retained as a separate local track, or sent with audio removed must be
  decided by the adapter after an authorized test. Omni's current reference
  rules do not make video-reference audio an editing control.
- The exact behavior and retention of URI-delivered output under
  `store=false`, including whether a subsequent status read returns inline
  data instead of a URI. The adapter must follow the response actually
  documented and observed for the selected endpoint.
- Provider cancellation semantics, billability after a timeout, and
  duplicate behavior after an interrupted POST.
- A successful edit from a GenBox-managed synthetic clip, in any region or
  account.

### 2.2 Veo

**VERIFIED / OFFICIAL:** The Gemini Developer API Veo workflow is a
long-running video-generation operation:

- Submit to `models/{model}:predictLongRunning`.
- Poll the returned operation until completion.
- Read the generated sample and download the returned video.
- Supported workflows include text-to-video, image-to-video, first/last-frame
  interpolation and reference-image generation for eligible models.
- Current documented Veo 3.1 durations are 4, 6, or 8 seconds; reference-image
  requests require 8 seconds. Veo 2 uses a different duration range.
- Native output is 24 FPS. Model-specific output resolutions and reference
  image limits differ by model.

**BOUNDARY:** Veo generation and extension documentation does not establish
that an arbitrary user-uploaded source video can be edited by an instruction
in the same way as Omni. Cloud/Agent Platform documentation may expose a
different endpoint, storage model, or extension contract; those facts cannot
be copied into the Gemini Developer API adapter without a separate provider
record.

**PROPOSED handling:** Keep Veo as a separate generation/extension capability.
Do not use it as an automatic fallback for an unsupported `video_edit`
operation. A Veo source-video edit row remains `unavailable` until a specific
official endpoint/model/input contract and an authorized live test exist.

### 2.3 Google endpoint families must remain separate

The following are related official Google products but not one universal wire
protocol:

| Family | Endpoint/transport | Workbench consequence |
| --- | --- | --- |
| Gemini Developer API Omni | `/v1beta/interactions`, API-key auth, Files API input | Candidate source-video edit adapter |
| Gemini Developer API Veo | `predictLongRunning`, operation polling and file download | Existing generation adapter; no automatic video-edit fallback |
| Gemini Enterprise Agent Platform / Vertex-style examples | Cloud Storage URIs, `gcs_uri`, Cloud project/location and different request forms | Separate future adapter; not interchangeable with the current API-key adapter |

Model discovery, an OpenAI-compatible gateway, or a provider display label
does not grant any of these capabilities.

## 3. SAIS-FUXI/Omni-Video 2 Research Boundary

**VERIFIED / FIRST-PARTY RESEARCH:** The SAIS repository and the
user-provided `2602.08820v2` report describe a local unified video model with
video-to-video editing. The README exposes an inference task such as
`v2v-A14B` or `v2v-1.3B`, a source clip path, an edit prompt, and local
generation parameters. It recommends CUDA/PyTorch execution and approximately
80 GB VRAM for the A14B model. The documented example uses `832*480`, 41
frames, 8 FPS, and 40 sampling steps.

The report describes a prompt reasoner plus a condition adapter around a
diffusion backbone. It organizes edit examples into local add, local remove,
local replace, global edit, attribute change and complex edit, with high-motion
and multi-element examples. These categories are useful for GenBox preset
labels and evaluation cases.

**NOT an online capability:** The paper's target captions, VAE references,
MLLM tokens, diffusion steps, solver, guidance scale and local checkpoint
requirements are implementation details of that model. They must not appear
as universal controls in the provider-neutral UI or be sent to Google.

**UNVERIFIED / licensing:** GitHub did not expose an SPDX license for the
repository at the pinned revision, and a direct `LICENSE` content lookup was
not available. No code, weights, demo media, or copied prompts may enter
GenBox until a separate provenance and license review is complete.

**PROPOSED reuse in GenBox:** Use the six categories as editable preset
families and use the report's preservation/evaluation ideas as acceptance
questions. Treat every provider's actual support as a separate capability
record.

## 4. Provider-Neutral Canonical Edit Intent

The browser submits a validated intent; the server resolves asset identity,
digests, credentials and provider wire fields. The following is **PROPOSED**
for W0.5 schema freeze:

```json
{
  "schema_version": "wb-edit-intent/v1",
  "project_id": "opaque-project-id",
  "expected_revision": 12,
  "clip_id": "opaque-clip-id",
  "source": {
    "asset_id": "opaque-asset-id",
    "source_interval_us": [1000000, 7000000],
    "content_sha256": "server-derived-sha256"
  },
  "references": [
    {
      "asset_id": "opaque-reference-id",
      "role": "reference_image",
      "content_sha256": "server-derived-sha256"
    }
  ],
  "instruction": "Change the jacket to a gray coat. Keep everything else the same.",
  "preset_id": "replace.attribute",
  "requested_changes": [
    {
      "kind": "replace",
      "target": "subject clothing",
      "from": "black jacket",
      "to": "gray coat"
    }
  ],
  "preservation_intent": {
    "subject_identity": "preserve",
    "motion_and_timing": "preserve",
    "camera_and_layout": "preserve",
    "background": "preserve",
    "audio": "retain_original_by_default"
  },
  "output_preferences": {
    "aspect_ratio": "project",
    "resolution": "provider_default",
    "fps": "provider_default",
    "duration_policy": "source_segment_or_provider_default"
  },
  "provider": {
    "provider_id": "google-native",
    "model_id": "gemini-omni-1.1-flash",
    "capability_revision": "capability-record-revision"
  },
  "audio_policy": "retain_original_unless_explicitly_replaced",
  "disclosure_revision": "cloud-video-edit-v1",
  "consent_id": "server-issued-consent-id",
  "idempotency_key": "server-issued-idempotency-key"
}
```

Required invariants:

- `asset_id`, interval, digest and project revision are server-validated.
- The browser never supplies a filesystem path, remote URI, API key, callback
  URL, arbitrary request body or provider upload handle.
- A provider switch invalidates the prior preflight and consent.
- Unsupported references, output settings or preservation options fail with a
  field-specific error; they are never silently discarded.
- A preservation value is an instruction, not a guaranteed identity,
  geometry, motion or audio lock.
- `source_interval_us` is half-open and integer-based. Long projects do not
  authorize automatic chunking into multiple paid edits.

## 5. Capability Descriptor And Matrix

Each adapter must return a server-trusted descriptor per provider, model and
effective endpoint. **PROPOSED** minimum fields:

```text
adapter_id, contract_version, provider_id, model_id, endpoint_family
operations, source_roles, reference_roles, input_count_limits
mime/codecs, byte/duration/dimension limits, output_formats
output_duration/fps/resolution behavior, allowlisted_options
upload_method, submit_mode, status_transport, result_transport
privacy_retention, deletion_support, cancellation_support
reconciliation_support, regions/accounts, source_urls, retrieved_at
sdk_revision, evidence_level, readiness, unavailable_reason
```

Readiness values:

- `unavailable`: the UI must not offer the operation.
- `experimental`: explicit opt-in, visible warnings, no implied quality.
- `verified`: only the tested provider/model/input profile, not every model
  combination.

| Capability profile | Official evidence | Initial readiness | W0.3 decision |
| --- | --- | --- | --- |
| Omni source-video instruction edit, one source segment, <=10 s | Official Omni guide documents Files API input and editing | `experimental` at most; no GenBox adapter yet | Freeze as first adapter candidate; live test required |
| Omni inline video result | Official REST response uses `steps[].content[]` with inline video | `verified` for current native generation mock contract; not source edit | Keep in generation adapter; do not reuse as edit completion proof |
| Omni URI video result | Official response format supports `delivery=uri`; larger output recommended | `unavailable` for workbench until result/expiry/recovery fixture and live shape are verified | Implement behind adapter capability, not shared job code |
| Omni stateful multi-turn edit | Official Interactions API supports `previous_interaction_id` with stored interactions | `unavailable` for first workbench slice | Requires retention consent, private IDs, deletion/recovery policy |
| Omni stateless follow-up edit | `store=false` can be stateless, but all history/steps must be managed by client | `unavailable` | High privacy and replay complexity; do not use as a shortcut |
| Omni source plus reference image/video | Model is multimodal; up to three short video references (3 s each) are documented, but exact source-plus-reference edit combinations are not qualified | `unavailable` | Separate capability rows and tests; do not treat reference audio as supported |
| Veo text/image/first-last/reference generation | Official Veo guide and current native adapter | `verified` only for current generation profiles | Existing generation path; not a source-video edit adapter |
| Veo arbitrary source-video instruction edit | No accepted Gemini Developer API contract in current evidence | `unavailable` | No fallback from `video_edit` to Veo generation |
| Cloud/Agent Platform video extension/edit | Official Cloud docs have different storage and request examples | `unavailable` in this adapter | Separate future adapter and credential/endpoint contract |
| SAIS Omni-Video 2 local v2v | First-party repository and report provide local inference | `unavailable` online; local deployment out of scope | Presets/evaluation inspiration only |
| Any other official API or gateway | No adapter-specific source/fixture/live evidence | `unavailable` | Register only after qualification sequence |

## 6. Upload, Submission, Result And Recovery Contract

This is **PROPOSED** common orchestration behavior; provider adapters own the
wire mapping.

### Preflight

1. Resolve the exact source clip and interval from a managed asset.
2. Verify provider, model, endpoint family, region/account availability,
   source duration, MIME/codec, dimensions and selected references against the
   descriptor.
3. Show the instruction, preset, source duration, provider/model, remote
   storage handling, possible charge, and unknown pricing.
4. Bind confirmation to the source digest, interval, instruction, model,
   capability revision and output settings.
5. Require separate cloud-upload consent. Local import consent is not cloud
   transmission consent.

### Input upload

1. Prepare only the selected segment and explicitly selected references.
   Strip unnecessary metadata where compatible with the output contract.
2. Upload to the provider only after consent. Keep provider handles in a
   private, bounded recovery store; never expose them in task IDs, URLs,
   browser storage or ordinary logs.
3. Poll documented processing states with a bounded interval and deadline.
   For Omni Files API, `PROCESSING` must become `ACTIVE` before submission;
   `FAILED` is an `upload_failed` result.
4. Do not make a second upload or paid submission because a client refresh
   lost a private handle. Mark the job `submission_unknown` or require a new
   confirmation, depending on what the adapter can reconcile.

### Submission and polling

1. Persist the local intent and idempotency key before the paid POST.
2. Submit exactly once. The common job engine records `submitting` and
   `submission_unknown` separately from `failed`.
3. A timeout, connection break or process crash after the POST is not proof
   that the provider did not accept the work. Never auto-retry, rotate keys,
   switch providers, or silently fall back.
4. Normalize provider states to `queued`, `running`, `succeeded`, `failed`,
   `cancel_requested`, `cancelled`, `interrupted`, or `submission_unknown`.
5. Provider-specific cancellation must state whether it stops only local
   observation or is confirmed by the provider. It must not promise billing
   reversal.

### Result and publication

1. Parse the provider's documented result shape, not an SDK-only convenience
   field.
2. For Omni inline output, read the REST `steps` model output and validate
   Base64, MIME, byte limit, MP4 signature, duration and decodability.
3. For Omni URI output or Veo file output, allow only adapter-approved
   provider/storage origins, poll the documented file/operation state, and
   download to a bounded temporary file.
4. Publish a new local candidate atomically only after validation. Keep the
   source asset, original timeline and instruction lineage unchanged.
5. Result acceptance is a separate user action. A late result never silently
   replaces a project clip.

### Cleanup and restart

- Delete owned remote temporary inputs only when the provider documents the
  operation and the adapter can verify ownership. Do not claim
  `store=false` means no transient processing or output storage.
- The Files API's 48-hour expiry is not a durable recovery strategy. The
  adapter should delete earlier when supported and record only sanitized
  cleanup state.
- After restart, an unverified provider handle becomes `interrupted` or
  `submission_unknown`; it is never replayed automatically.
- A safe reconciliation path may read a private provider status by an
  allowlisted handle. If reconciliation is not implemented, ask for explicit
  user review and fresh consent.

## 7. Privacy, Security And Cost Requirements

**PROPOSED for all adapters:**

- Send the smallest selected segment, not the whole project or gallery.
- Do not expose GenBox-local media through an arbitrary public URL.
- Keep API keys, remote file handles, interaction IDs, signed URLs and raw
  provider responses server-side.
- Redact prompts, source names, account data, media bytes and provider IDs from
  ordinary logs and tracked evidence.
- Enforce region/account restrictions before upload where the provider exposes
  them; an HTTP 200 model list is not proof that editing is available.
- Treat possible charges as unknown unless the current official pricing source
  and account tier are known. The UI must not invent a cost estimate.
- Do not use uploaded private media, real credentials, or a paid provider call
  in CI. Live evidence requires an explicit per-attempt authorization.

## 8. Qualification Sequence For The First Real Adapter

The following sequence is required before enabling `google-native/video_edit`:

1. Freeze the canonical intent, capability descriptor, safe error enum and
   private-handle lifecycle in W0.5.
2. Add deterministic fixtures for a short synthetic source clip, a no-audio
   clip, a clip with audio, malformed/oversized media and a boundary 10-second
   clip. Fixture provenance and SHA-256 belong to W0.2 evidence.
3. Add request/response fixtures for Files upload, processing poll, Omni
   Interactions submission, inline result, URI result, malformed result,
   timeout-after-submit and cleanup.
4. Add adapter tests for unsupported region/account, unsupported MIME/length,
   upload failure, 429/5xx, polling timeout, cancellation, invalid result,
   provider-handle redaction and no automatic resubmission.
5. Add two fake adapters with different synchronous/asynchronous transport
   shapes. Shared project/schema/UI code must pass without Google-specific
   fields.
6. Obtain explicit authorization for **one** real edit using a synthetic or
   explicitly redistributable source clip. Record only model, endpoint family,
   time, local job ID, sanitized state, and output validation.
7. Qualify one input profile at a time. Untested duration, MIME, reference
   roles, regions, output delivery modes and multi-turn behavior remain
   `experimental` or `unavailable`.

## 9. W0.3 Exit Assessment

| Gate | Status | Evidence or blocker |
| --- | --- | --- |
| Official online edit source review | **PASS** | Google Omni, Interactions, Files, Veo, SDK and Cloud boundary sources re-read 2026-09-18 |
| Existing GenBox adapter boundary | **PASS** | `providers/google_video.py`, `main.py`, `GOOGLE-VIDEO-CONTRACT.md` and local tests inspected |
| Provider-neutral canonical intent | **PROPOSED / READY FOR W0.5** | Schema above; server-derived identity and consent invariants defined |
| Capability descriptor/matrix | **PROPOSED / READY FOR W0.5** | Exact model/endpoint/role/transport/privacy/readiness rows above |
| No-paid-call deterministic fixtures | **PASS / MOCK-ONLY** | Existing native Google tests; source-video edit fixtures still to add in WB-3 |
| Real Google source-video edit | **UNVERIFIED / BLOCKED** | No authorized live call in W0.3; no private media uploaded |
| Provider recovery after uncertain submit | **UNVERIFIED** | Requires adapter implementation and fake/live recovery tests |
| Omni multi-turn editing | **UNVERIFIED / DEFERRED** | Requires retention consent, `store=true`, private interaction IDs and deletion policy |
| Veo as source-video editor | **UNAVAILABLE** | No accepted Developer API edit contract in current evidence |
| SAIS Omni-Video 2 as online provider | **UNAVAILABLE** | Local CUDA model/repository, not a hosted API |

**Recommendation to coordinator:** mark W0.3 as research-complete and send this
report to W0.5. Do not mark WB-0 complete and do not start WB-1 until W0.2,
W0.4 and the W0.5 contract review also pass. Do not expose source-video edit
as selectable in the current video-generation UI.

## Resume Instructions

The next agent should:

1. Compare this report with W0.2 media limits and W0.4 consent/error flows.
2. Freeze or revise the canonical schema and capability rows in W0.5.
3. Keep `providers/google_video.py`, `main.py`, `static/index.html`, and
   `docs/STATUS.md` unchanged unless the coordinator assigns a later phase.
4. When implementation is authorized, create a separate source-video-edit
   adapter behind the provider extension contract; do not expand the current
   generation request modes in place.
5. Before any live request, obtain explicit authorization, verify the region and
   account, use synthetic/authorized media, and record sanitized evidence only.
