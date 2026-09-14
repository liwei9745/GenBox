# Aggregate Provider Precision-Edit Strategy

Date: 2026-09-10
State: Proposed; research and read-only code audit complete, not implemented.

## Objective

Keep accepted GPT editing unchanged while allowing another model in the same
aggregate Provider to use an explicitly selected transport and an independent
size family. A provider display name is not a protocol or model identity.

## Evidence And Correction

- USER-CONFIRMED: The selected model was `nano-banana-2-2k` in the existing
  aggregate Provider. Its displayed failure was upstream HTTP 400 with
  `Invalid data URL`, not a local size gate or decoded-output mismatch.
- VERIFIED (code): The selected OpenAI precision profile sends binary multipart
  image files. It does not directly submit a data URL. The message could arise
  in upstream translation or parsing. It does NOT establish that native Gemini
  is required, that OpenAI compatibility is unavailable, or that sizes are
  unsupported.
- VERIFIED (code): `endpoint_type` and `precision_edit_profile` are currently
  Provider-wide. The prior native-Gemini work does not implement safe,
  independently configured mixed-model transports within an aggregate Provider.
- UNVERIFIED: The aggregate service's precise request schema and support for
  this exact gateway alias. Public documentation search returned no matching
  result and the public homepage fetch failed. No real request was made during
  this strategy work.

## Independent Configuration Axes

1. Connection: existing Provider credentials and configured endpoint identity.
2. Selected model: preserve the exact outbound gateway ID, including case.
3. Precision transport: inherit Provider default, OpenAI image-edit profile,
   Gemini GenerateContent, or a separately implemented native vendor adapter.
4. Model size family: GPT, a specific Nano Banana generation, Qwen, Seedream,
   or an explicit service-specific catalog.
5. Size policy: strict native output versus explicit local crop-to-fit.

An OpenAI-compatible Nano Banana gateway combines an OpenAI transport with a
Nano Banana/service-specific size catalog. Choosing Gemini as the size family
must not silently change the HTTP protocol, hostname, key or outbound model ID.
The `2k` alias suffix is a hint, not proof of the model family or pixel contract.

Store the precision override under the selected model, separate from shared
Provider defaults and existing alias capability inheritance. Resolve an
effective configuration copy per request; never temporarily mutate a global
Provider object. Size-family selection must not copy another model's successful
sizes or authorization records.

## Proposed UI

At the model status location, add:

- `生图协议`: inherit default / OpenAI compatible / Gemini native / supported
  vendor-native adapters. Use a select, with the exact request format in an
  advanced disclosure.
- `尺寸预设`: independent, explicitly selected model family or documented
  service-specific profile. Show the actual width and height.
- `检查配置`: no image generation; reports local validation and any separately
  obtained read-only metadata evidence.
- `试用一次`: separate, clearly potentially billable action showing selected
  model, transport, target pixels, input type and maximum one upstream POST.

An unavailable Qwen or Seedream precision adapter must be visibly unavailable,
not a selectable label backed by an unrelated fallback. Existing Qwen2API
support is not equivalent to the official DashScope image-edit API.
Changing a dropdown does not send a generation request. Selecting another
model restores its own profile and applicable evidence.

## Preflight Layers

### Local Checks (No Network)

Validate credential presence without exposing values, endpoint/version joining,
adapter completeness, selected model binding, MIME versus decoded content,
base64/data-URL or multipart structure, source/annotation dimensions, parameter
schema, selected size mapping, limits and current authorization.

Compile a redacted request summary from the SAME backend resolver that dispatch
uses. Do not accept arbitrary URLs, headers, shell scripts or JSON templates
from the browser as a shortcut to compatibility.

### Read-Only Metadata

Where the service exposes documented model or capability metadata, query it with
bounded GET requests. Treat listed models and reachable routes only as metadata,
not verified image-edit capability. CORS OPTIONS, 404/405, an unavailable model
list, or an advertised `/v1` prefix are not conclusive compatibility tests.

Use configured approved origins only; do not follow redirects with credentials
to another host. Do not upload images or call generation endpoints as a
supposedly free dry run. Do not execute scripts found in provider documentation.

### Explicit Single-Request Trial

The user authorized testing the existing Provider's `nano-banana-2-2k`.
Conservatively consume this as at most one real image-edit POST after selecting
one justified request schema. This is not authorization to enumerate protocols.
Use a non-sensitive synthetic source instead of the user's current canvas,
select one concrete target, and disable automatic retry, endpoint/key rotation
and text-to-image fallback.

If the schema remains unknown, report that fact rather than spend the trial
trying arbitrary payloads. Subsequent protocol trials require another explicit
action or a user-agreed bounded trial matrix.

Record only sanitized model ID, profile, requested pixels, decoded actual
pixels if present, timestamp, status category and whether the requested edit is
visually evident. HTTP success alone is not successful precision editing.

## Evidence And Failure Handling

Maintain distinct states: unconfigured, local-valid, service-declared,
trial-authorized, observed-success, inconclusive, and local-incompatible.
An authorized trial is not a supported-size claim.

Bind new evidence to Provider, endpoint/config revision, selected model,
transport/adapter version, size-family revision and exact target. Credential or
endpoint changes invalidate applicable observations without storing secret
values or secret fingerprints in public state. Legacy GPT records stay on the
unchanged default transport; switching a Nano Banana override must not alter
them. Returning to an unchanged profile may reuse only that profile's evidence.

- HTTP 400: categorize safe provider error hints; inspect field encoding before
  assuming a protocol or size failure.
- Timeout/503: inconclusive upstream result, never automatic alternate POST.
- Valid image but wrong pixels: strict failure remains strict failure. A future
  user-visible candidate recovery may retain a safely decoded local temporary
  result with actual dimensions and a mismatch label, but must not replace the
  base, enter success history or auto-crop. Implement retention, expiry and
  explicit acceptance separately; never retain invalid or unsafe image data.
- Unsupported local adapter or unmappable size: fail before spending a request,
  with an actionable configuration explanation.

## Development And Review Order

1. Backend/config agent: per-model override schema, shared effective resolver,
   endpoint joining, backward-compatible default path and scoped evidence.
2. Adapter agent: confirm the target gateway schema; extend only an allowlisted
   request format if needed. Preserve actual gateway model ID and one-POST budget.
3. Frontend agent: protocol and size-family controls, honest preflight states,
   model-specific catalog rendering and asynchronous selection race protection.
4. Independent reviewer: inspect GPT isolation, request snapshots, secret safety
   and failure behavior. The primary agent integrates and verifies.
5. After local checks, use the authorized single target trial, then provide the
   lab build and observed result to the user for manual acceptance.
6. Qwen/Seedream native adapters follow only after their own schema, runtime,
   response parsing and tests exist. No release or universal compatibility claim
   follows from one Nano Banana success.

## Required Acceptance Tests

- One Provider: GPT -> Nano Banana/OpenAI -> Nano Banana/Gemini -> GPT.
  Original GPT configuration and grants are byte-for-byte unchanged.
- Nano Banana pixel catalogs work with either transport when explicitly mapped;
  GPT pixel validation is not accidentally applied to Gemini catalogs.
- Current preset value, width/height and displayed family stay consistent;
  empty catalogs do not retain previous-model options, crop targets do not move.
- Outbound ID remains the gateway alias; family mapping never renames the model.
- Preflight generates zero image POSTs; repeated UI events share single-flight
  state; stale preflight results cannot authorize a changed selection.
- Authorization/grants from one profile or endpoint revision cannot authorize
  another. Backend rechecks the frozen request revision at dispatch.
- Each trial or Generate action makes at most one upstream image POST across all
  protocols/endpoints, including 400, 429, 503 and ambiguous transport failures.
- Multipart, data URL and Gemini inlineData use their exact intended encodings;
  unsafe JSON/MIME, thought-only output and over-limit images are rejected.
- API route and synthetic desktop/mobile browser tests supplement unit tests;
  source-regex tests alone do not prove switching or end-to-end readiness.

## Primary References

Checked 2026-09-10. Official API documentation does not prove that the aggregate
service implements an identical contract.

- OpenAI image API: https://developers.openai.com/api/reference/resources/images
- Gemini image editing (GenerateContent):
  https://ai.google.dev/gemini-api/docs/generate-content/image-generation
- Gemini GenerateContent schema: https://ai.google.dev/api/generate-content
- Qwen image editing:
  https://help.aliyun.com/zh/model-studio/qwen-image-edit-api
- Seedream image API: https://docs.volcengine.com/docs/82379/1541523

Resume: implement the per-model override and inspection path first. Keep the
existing GPT configuration unchanged. Do not mark the target gateway compatible
until its actual trial evidence exists.
