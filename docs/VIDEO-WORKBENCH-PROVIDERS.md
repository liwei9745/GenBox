# Video Editing Provider Extension Contract

Date: 2026-09-18. Revision: 0.2.
Status: **Frozen WB-0 provider-neutral contract; no live edit adapter enabled.**
Requirement: VW-13. Parent: [core contract](VIDEO-WORKBENCH-CONTRACT.md).

## Goal And Non-Goals

USER-CONFIRMED: users should eventually be able to choose additional online
video-editing models, not only Google. Build a provider-neutral workbench with
a narrow, explicit adapter interface. Google Omni is the first validation
candidate, not the universal wire protocol.

The initial scope delivers the interface and one verified live path, not support
for every vendor. Do not name an unresearched model as supported. In particular,
text-to-video, image-to-video and video understanding do not establish
source-video editing capability. A model-list result or OpenAI-compatible
endpoint is not a video-edit API specification.

## Capability Descriptor

Each registered adapter exposes versioned, validated capability data per model
and effective endpoint. Model IDs are provider-scoped, not globally unique.

| Field group | Required meaning |
| --- | --- |
| Identity | `adapter_id`, `contract_version`, provider/model IDs, protocol family |
| Operations | Explicit `video_edit`; future extension/reference operations separately declared |
| Inputs | Source/reference roles, counts, codec/container/MIME, byte/duration/dimension limits, allowed combinations |
| Outputs | Formats, duration behavior, canvas/FPS support, audio behavior |
| Parameters | Allowlisted enum/range/default with semantic meaning; no arbitrary request JSON |
| Transport | Upload method, sync/async submission, status/result transport, documented reconciliation |
| Privacy | Upload retention, session storage, deletion support, required disclosures |
| Task controls | Cancel support, idempotency behavior, safe polling and throttling limits |
| Evidence | Source URLs/date/version, fixtures, live-test scope, known regional/account restrictions |
| Readiness | unavailable, experimental, verified; unavailable reason and last verification |

All capability claims start unavailable until an implemented adapter and source
evidence exist. Experimental adapters require explicit user opt-in. Verified
means a particular tested operation/input profile, not every combination.
Provider discovery may supply metadata, but cannot grant a capability by itself.
Account availability and protocol support are separate: a supported API can
still deny a user's account or region.

An administrator may configure a registered provider's credentials, endpoint,
and model ID. Manual model IDs do not bypass preflight or grant editing support.
Custom hosts need the project's endpoint validation/credential rules; require
revalidation when host/protocol changes. Do not alter existing native Google
hostname routing or gateway generation compatibility.

## Canonical Edit Intent

The workbench submits a validated intent:

```text
project_id, expected_revision, clip_id
source_asset_id, source_interval_us, source_digest
references[]: {asset_id, digest, role}
instruction, preset_id, preservation_intent
provider_id, model_id, capability_revision
output_preferences, validated_adapter_options
audio_policy, disclosure_revision, consent_id, idempotency_key
```

The server derives trusted digests and revisions. The browser does not supply
remote file handles, API keys, filesystem paths, callback URLs or request bodies.
Stored instructions are private project data, never ordinary logs.

Never silently discard an unsupported reference, output setting or preservation
option. Reject with a field-specific safe error or obtain explicit user approval
for a changed plan. No fake universal strength/identity/seed slider.

## Adapter Lifecycle

Proposed internal interface; WB-0 freezes exact Python types and exceptions.

| Operation | Responsibility |
| --- | --- |
| `describe_capabilities(context, model)` | Return trusted descriptor, not a credential-bearing object |
| `validate_intent(intent, capabilities)` | Reject unsupported combinations without network side effects |
| `prepare_media(intent, asset_reader)` | Produce bounded local input plan; no remote upload before consent |
| `upload_inputs(plan, private_context)` | Upload authorized inputs; return private scoped handles |
| `submit(prepared, private_context)` | One paid POST; return immediate result or private job reference |
| `poll(job_reference, private_context)` | Optional bounded status reads; normalize state, never resubmit |
| `fetch_result(result_reference, sink)` | Stream to controlled temporary output with size/host checks |
| `cancel(job_reference, private_context)` | Optional; distinguish unsupported, requested and confirmed |
| `cleanup(handles, private_context)` | Delete only owned temporary uploads if supported |
| `reconcile(private_receipt, private_context)` | Optional verified read-only recovery; otherwise unknown |

`private_context` resolves existing credentials server-side with least privilege.
Adapters cannot bypass the common consent, job-store or publication boundary.
The adapter handles upstream field mapping; the shared engine handles local IDs,
leases, progress, candidate lineage, validation and atomic library publication.

Normalize errors to safe codes such as unsupported_input, account_unavailable,
upload_failed, rate_limited, submission_unknown, remote_failed,
invalid_result and cleanup_pending. Include stage and known field names, not
raw responses or signed URLs. HTTP success is not enough to publish a result.

Support sync inline output and async job polling without assuming Google
Interactions. Result links must pass adapter-owned origin/redirect allowlists;
never forward credentials to unrelated hosts. If a service requires a public
input URL, keep that adapter unavailable until a separate secure signed-upload
design is approved. Do not expose local media publicly to make it work.
Webhooks and dynamic third-party plugin loading are outside the MVP.

## Extension Registration And UI

Register reviewed adapters in a fixed server-side registry. This is a Python
extension boundary, not permission to load code from a browser or model response.
Dependencies and migrations are reviewed, versioned and regression-tested.

The UI requests edit capabilities for the selected operation and assets.
Display provider groups with search and capability filters; show unavailable
reasons in settings, not selectable nonworking options in an ordinary task.
Do not reuse generation-only filtering as proof of edit eligibility.

Keep common controls shared; render advanced fields only from a safe declarative
schema of known controls. Never render provider-supplied HTML or executable code.
Changing provider invalidates prior preflight and rechecks every selected asset.
Do not replace the current project selection or lose its draft instruction.

## Adapter Qualification

For every additional adapter:

1. Research official editing documentation; record exact endpoint/model/input
   combinations, account limits, privacy behavior and pricing uncertainty.
2. Add pinned request/response fixtures and adapter contract tests.
3. Test secret redaction, arbitrary URL/path rejection, upload failure, 429,
   timeout after submit, polling, cancellation, malformed/oversized results,
   cleanup and no automatic resubmission.
4. Prove the same canonical intent does not require vendor fields in the UI.
5. Obtain explicit authorization for one real edit using permitted footage.
6. Record the tested capability profile and independent acceptance evidence.
7. Enable only that profile; keep untested combinations experimental/unavailable.

WB-3 must exercise the shared interface with two fake adapters having different
upload/status/output shapes, plus the first implemented real adapter. Fake
coverage proves architectural separation, not support for a second live model.
Adding another provider must not require changing project schema or existing
generation requests unless an explicit versioned contract change is approved.

## WB-0 Provider Freeze

The following rules are frozen for the first-release workbench:

1. `video_edit` is a capability, not a model-name category. A discovered model
   or OpenAI-compatible endpoint cannot grant it.
2. The browser submits the canonical intent and validated adapter options only.
   The server resolves credentials, endpoint details and vendor request bodies.
3. The first workbench release exposes no live online-edit provider by default.
   Google Omni is a research candidate from W0.3; its source-video edit profile
   remains `research_only/unavailable` until a dedicated adapter, privacy/
   recovery contract and authorized evidence pass WB-3.
4. Veo and the existing native Google generation adapter remain generation
   capabilities. They do not inherit source-video editing from model names.
5. Unsupported roles, settings and preservation requests return
   `unsupported_capability`; they are never silently removed from the intent.
6. The shared lifecycle, consent, idempotency and `submission_unknown` state
   from the core contract applies equally to Google, future official APIs and
   custom gateways.

### Frozen capability states

| Provider profile | Operation | WB-0 state | What would promote it |
| --- | --- | --- | --- |
| Google Gemini Omni Flash | uploaded source-video edit | `research_only/unavailable` | Implemented adapter, official request fixtures, privacy/recovery review and VA-17 |
| Google Veo | text/image/video generation and extension profiles already in GenBox | outside workbench edit registry | Existing generation regression plus separate edit qualification |
| Other online models | source-video edit | `unavailable` | Provider-specific official contract and adapter qualification |
| Fake adapter A/B | interface tests only | `test_only` | WB-3 contract coverage; never user-visible support |

This freeze intentionally lets WB-1 build local assets and projects without
pretending that an online model is already supported. Provider-specific UI is
deferred to WB-3 after capability data exists.
