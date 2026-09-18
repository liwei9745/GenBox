# Video Workbench Development Plan

Date: 2026-09-18. Revision: 0.3.
Current primary objective: WB-1 implementation strategy and plan review.
Authorization: write and review planning documents; no WB-1 business code,
paid calls, private-media upload, tool installation, release, or deployment.

## Reading And Authority

Read [PRD](VIDEO-WORKBENCH-PRD.md), [contract](VIDEO-WORKBENCH-CONTRACT.md),
[providers](VIDEO-WORKBENCH-PROVIDERS.md), [AI](VIDEO-WORKBENCH-AI.md),
[UX](VIDEO-WORKBENCH-UX.md), [acceptance](VIDEO-WORKBENCH-ACCEPTANCE.md)
and [team](VIDEO-WORKBENCH-TEAM.md). The detailed WB-1 packet is
[VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md](VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md).

Topic phases use WB IDs; they do not renumber or complete extension phases.
GSD execution artifacts are derived from these documents, not a rival source of
truth. Do not initialize over the existing historical `.planning/` contents.

## Dependency Graph

```text
WB-0 scope + contracts + feasibility
  -> WB-1 assets + project storage
  -> WB-2 deterministic editing/export
  -> WB-3 online edit + provider extension verification
  -> WB-4 integration, live acceptance, packaging
```

Research can proceed independently within a phase, but implementation starts
only after that phase's plan and evidence gates pass.

## Phase Ledger

| Phase | Status | Exit gate |
| --- | --- | --- |
| WB-0 | **Complete (2026-09-18): W0.2-W0.5 evidence and planning freeze accepted** | Approved scope, frozen schemas/limits, evidence-backed feasibility |
| WB-1 | **Plan in review; code not started** | VA-01 through VA-04; applicable VA-12/13 |
| WB-2 | Planned | VA-05 through VA-07, local part of VA-15/20 |
| WB-3 | Planned | VA-08 through VA-11, VA-17 through VA-19; applicable VA-12/13 |
| WB-4 | Planned | All required cases, regressions, packaging and independent review |

All implementation and acceptance below is pending.

## Stage Goals

The workbench is advanced by evidence-backed stage goals. A stage is complete
only when its exit evidence is recorded; a document draft, UI mockup, catalog
entry or fake adapter is not implementation evidence.

| Stage | Goal | Required evidence | Exit decision |
| --- | --- | --- | --- |
| G0 Release baseline | Keep v2.6.12 reproducible and separate from workbench scope | Merged release, hosted checks, client/container assets, status record | Baseline is frozen; no WB code is mixed into release repair work |
| G1 Media feasibility (W0.2) | Prove the local media path can import, probe, proxy and render bounded synthetic assets | Codec/engine matrix, resource limits, synthetic render report, dependency risks | Choose the supported local media engine and limits |
| G2 AI feasibility (W0.3) | Define a provider-neutral online edit contract and qualify the first evidence-backed adapter boundary | Official-source review, canonical intents, capability matrix, privacy/recovery matrix, no-paid-call fixture tests | Freeze adapter contract; keep unsupported capabilities explicit |
| G3 UX feasibility (W0.4) | Validate the smallest usable editor workflow before implementation | Low-fidelity flow, state matrix, consent/error states, performance envelope | Freeze the WB-1 interaction path and measurable UX constraints |
| G4 Contract review (W0.5) | Consolidate G1-G3 into implementation-ready contracts and ownership packets | Reviewed project schema, asset identity, limits, error enum, ownership map and task packets | Authorize WB-1 only after coordinator and independent review pass |
| G5 Asset vertical slice (WB-1) | Import external media and select GenBox library assets into restart-safe projects | Browser journey, persistence/restart evidence, malformed/disk-full/auth tests | Authorize WB-2 local editing |
| G6 Local editing slice (WB-2) | Deliver non-destructive trim/split/reorder/save/export without online AI | Mixed-media render, A/V sync, revision and conflict evidence | Authorize WB-3 online editing |
| G7 Online editing (WB-3) | Add bounded provider adapters, presets and candidate comparison | Fake second adapter, recovery tests, authorized live evidence | Authorize WB-4 integration and packaging |
| G8 Integrated delivery (WB-4) | Verify the complete workbench across supported targets and release boundaries | Independent review, regression, performance, packaging and clean-install evidence | Release or return to the failed stage |

G1-G4 are complete. The current objective is to review the detailed WB-1
implementation plan and then execute only its W1-0/W1-1 preparation tasks.
No WB-1 business code, paid generation call, private-media upload or
provider-specific UI is authorized in this planning step.

## WB-0: Preparation

| Task | Owner | Dependencies | Deliverable |
| --- | --- | --- | --- |
| W0.1 | Coordinator | User direction | Requirements, scope/deferred list, acceptance IDs, team protocol |
| W0.2 | Media engineer | W0.1 | Decoder/export/OS dependency matrix, bounded import limits, synthetic render spike |
| W0.3 | AI adapter specialist | W0.1 | Current official edit sources, pinned fixtures, provider-neutral type proposal, privacy/recovery limits |
| W0.4 | Product/UX specialist | W0.1 | Low-fidelity flows, empty/error states, local vs cloud consent |
| W0.5 | Coordinator + reviewer | W0.2-W0.4 | Reviewed schemas, ownership map, measurable budget, task packages |

W0.2-W0.4 may be researched in parallel when explicitly dispatched. Media spike
and mock protocol tests may not upload private media or call paid APIs.

Decisions frozen for WB-1 planning:

- FFmpeg/ffprobe worker boundary and the conservative input/output/resource
  matrix in the core contract.
- Project JSON schema, rational time representation, output profiles and proxy
  mapping.
- Logical asset/project/job storage, revision/lease strategy, bounded
  multipart import and restart-safe cleanup.
- Logical API operations, error enum, auth/CSRF, conflict and idempotency
  semantics.
- Low-fidelity UX path, fixed viewports and frozen interaction/performance
  targets.

Additional decisions before WB-3: verified source upload/edit shape, initial
provider capabilities, private remote-handle lifecycle and storage disclosure,
post-submit reconciliation policy and authorized live-test plan. Packaged
cross-target media behavior remains a WB-4 gate.

## WB-1: Assets And Durable Projects

Implement managed external image/video/audio import, exact-ID library selection,
bounded probing, metadata pagination, lazy thumbnails/proxies and project
create/read/save. Prove auth, atomic publication, malformed-media rejection,
missing dependency, disk-full behavior and restart-safe state.

Possible independent packages after schema freeze: media ingestion backend and
asset-browser frontend with contract fixtures. Coordinator alone wires shared
entry points. Integrate early; frontend mocks are not end-to-end evidence.
Exit: imported assets and projects survive restart without changing originals.
Detailed execution strategy:
[VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md](VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md).

## WB-2: Local Editing Vertical Slice

Implement sequential picture track, audio track, trim/split/reorder/duplicate,
undo/redo, save conflict and missing-media handling. Render immutable project
revisions with the selected engine; validate output and publish once.

Independent packages: timeline/UI state and render executor against the same
fixtures. Add real mixed-media render and A/V sync tests, then browser journey:
external video + audio + library image -> arrange -> save -> restart -> export.
Exit: useful non-AI editing slice accepted; AI workbench is not yet complete.

## WB-3: Online Editing And Extensibility

Implement the adapter registry and canonical intent before Google-specific
transport. Integrate one evidence-backed source-video-edit adapter, bounded
upload/poll/result handling and six editable preset families.

Test a second fake adapter with different sync/async behavior to detect vendor
coupling. This does not advertise another live provider.
Implement source/candidate comparison, explicit replacement/audio policy,
unknown-submission recovery and no automatic paid retry.

Independent packages: adapter/backend and candidate/preset UI against frozen
schemas. A reference-image combination remains unavailable until qualified.
Exit includes a specifically authorized real edit and comparison. Without that
authorization, record the live gate as pending rather than declaring completion.

## WB-4: Hardening And Delivery Readiness

Independent reviewer reruns critical cases against the integrated commit.
Test all declared package targets, dependency discovery, safe cancellation,
export correctness, user-facing failures and performance budgets.
Run existing generation/provider/browser regression suites and full tests.

Release actions require current explicit authorization and the existing
development lifecycle. Review dependency distribution, sanitized source,
clean-install behavior and package artifacts before any new tag.
This plan neither verifies nor re-runs the pending v2.6.12 release workflows.

## Subsequent Backlog

Only after WB-4: additional qualified live editing adapters; ASR/subtitles/TTS;
transitions/text/PiP/keyframes; intelligent reframing; text-driven rough cuts;
recipes and confirmed-cost batches. Each needs its own requirements and gates.

## Current Handoff

W0.1: Complete as the planning baseline.
W0.2: Evidence report complete; frozen planning matrix accepted. Cross-target
packaging and fault evidence remain later-phase gates.
W0.3: Official-source research report complete; source-video editing remains
unavailable until WB-3 qualification.
W0.4: Low-fidelity UX baseline frozen; browser journey evidence remains
implementation acceptance.
W0.5: PASS recorded in
[VIDEO-WORKBENCH-W0.5-REVIEW.md](VIDEO-WORKBENCH-W0.5-REVIEW.md);
WB-1 detailed implementation plan is drafted for review; implementation has not
started.

Next action: review
[VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md](VIDEO-WORKBENCH-WB1-IMPLEMENTATION-PLAN.md),
then execute W1-0 and W1-1 on a clean branch based on the latest `origin/master`.
Do not silently launch paid calls, upload private media, or auto-upgrade
GSD/Agency tools.
Retain existing user changes and release handoff in STATUS.
