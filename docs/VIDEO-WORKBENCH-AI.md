# Video Workbench Online AI Boundary

Date: 2026-09-18. Revision: 0.1. Status: Research-to-implementation checklist.
Read [core contract](VIDEO-WORKBENCH-CONTRACT.md) and
[provider extension contract](VIDEO-WORKBENCH-PROVIDERS.md), then
[existing Google contract](GOOGLE-VIDEO-CONTRACT.md).

## Evidence Levels

- USER-CONFIRMED: existing native Veo and Omni generation passed manual
  acceptance before this milestone. That is not uploaded-video editing evidence.
- VERIFIED / LOCAL: the current adapter accepts only generation modes and uses
  Omni inline output with `store=false`; preserve that working behavior.
- PRIOR RESEARCH / REVALIDATION REQUIRED: the Google Omni guide described video
  upload editing, short input limits, regional restrictions, ignored reference
  audio and stateful editing. Re-fetch the guide and pin SDK/request evidence in
  WB-0. Do not present remembered limits as current supported UI capabilities.
- UNVERIFIED: GenBox source-video upload/edit E2E, reference-image combinations,
  cancellation/reconciliation, cloud cleanup and candidate quality.

SAIS Omni-Video 2 and Google Gemini Omni are different models. The paper
2602.08820v2 supplies edit taxonomy and evaluation ideas, not Google's API
contract or success rates. Local model conditioning weights cannot be exposed
as meaningful controls for an unrelated hosted API.

## Capability Matrix To Freeze In WB-0

| Capability | First-release handling | Required evidence |
| --- | --- | --- |
| Local editing/export | Independent of AI provider | Media fixtures and real rendered output |
| Uploaded-video edit | First adapter candidate: official Google Omni; shared interface is provider-neutral | Current docs, request fixtures, authorized real call |
| Source plus reference image | Disabled until verified | Exact role/count schema and authorized acceptance |
| Reference videos | Deferred | Separate source/reference and compatibility research |
| Multi-turn cloud session | Deferred | Storage/retention consent and session lifecycle |
| Veo as edit fallback | Not allowed by default | Separate documented capability, not model-name inference |
| Other official APIs and gateways | Extension interface in first release; additional live adapters separately gated | Adapter-specific edit contract; no protocol guessing |
| ASR/TTS/voice edits | Outside first release | Separate provider and consent contract |

Each capability record must include endpoint family, exact model ID, supported
roles/counts, formats/limits, region/account constraints, source URL, retrieval
date, pinned SDK revision, evidence level and verified failure behavior.
Model discovery alone never marks editing supported.
Generic job, project and UI code must not branch on Google response fields or
assume its storage, duration, upload or polling behavior for other adapters.

## Preflight And Submission

1. Validate the selected source asset and interval against current capability
   data. Long projects do not authorize automatic chunk-by-chunk AI rewriting.
2. Prepare only the selected segment and expressly selected references. Strip
   unnecessary metadata and avoid transmitting unrelated media or project data.
3. Show provider/model, media count and duration, instruction, storage handling,
   possible charges and unknown pricing. Do not invent a fee estimate.
4. Bind confirmation to source hashes, interval, instruction, model and settings.
   Changing any of them invalidates the plan.
5. Upload only after explicit cloud consent and submission. Confirming local
   import is not permission to send data to a model provider.
6. Validate upload state with bounded polling before one paid generation POST.
   Transport unknowns follow submission_unknown, not silent retries.
7. Parse documented REST output, validate media and store a new local candidate.
   Do not treat an SDK convenience attribute as a REST field.
8. Clean up owned remote temporary files where the verified API permits it.
   Report cleanup failure safely; never claim `store=false` means no temporary
   remote media storage. Do not enable persistent sessions to work around errors.

Provider upload handles stay in a private, narrowly scoped recovery mechanism
whose storage/expiry is decided in WB-0; never in public task IDs, URLs or logs.
If safe recovery is not implemented, explicitly report unknown/orphaned upload
status after restart and do not submit a duplicate generation.

## Preset And Prompt Contract

Each preset has a stable ID, target description, requested changes, preserved
properties, optional verified references and an editable final instruction.
Families: add, remove, replace, attribute, global and combined.

Preservation options are instructions, not hard spatial, identity or motion
locks. Conflicts such as preserve background + replace background require
resolution before submission. Combined edits warn about complexity.

Compile a concise provider-specific instruction from the user-confirmed plan.
Do not invent objects through automatic analysis, send hidden instructions, or
blindly translate the research paper's internal target captions into API input.
Optional scene understanding and multi-object suggestion are later features.

## Evaluation And Consent

Use synthetic or explicitly authorized test footage, not private user history.
Evaluate requested change, collateral changes, temporal consistency, motion/
subject continuity, duration, decodability and audio policy. Record per-case
observations; no uncalibrated numeric "quality score" or universal success claim.

One authorized paid trial cannot certify every preset. Untested presets retain
experimental status. Failed generation does not authorize another attempt.
Record local job ID, model, time and sanitized outcome, never raw keys, prompts,
upstream bodies, remote identifiers or user media in tracked evidence.

## Research Sources For WB-0

Revalidate these sources; this document does not certify their current contents:

- https://ai.google.dev/gemini-api/docs/omni
- https://ai.google.dev/gemini-api/docs/interactions
- https://ai.google.dev/gemini-api/docs/veo
- https://github.com/googleapis/python-genai
- https://github.com/SAIS-FUXI/Omni-Video
- Technical report: arXiv 2602.08820v2, especially edit taxonomy and evaluation.

Do not copy third-party code, examples or media into GenBox without provenance
and dependency/license review. Reading documentation is not permission to run
installers, upload user footage, or make paid calls.
