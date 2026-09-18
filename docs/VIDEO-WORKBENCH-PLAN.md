# Video Workbench Development Plan

Date: 2026-09-18. Revision: 0.1.
Current primary objective: WB-0 scope/contract preparation only.
Authorization: write planning documents and collaboration strategy; no paid
calls, implementation, tool installation, release, or deployment in this task.

## Reading And Authority

Read [PRD](VIDEO-WORKBENCH-PRD.md), [contract](VIDEO-WORKBENCH-CONTRACT.md),
[providers](VIDEO-WORKBENCH-PROVIDERS.md), [AI](VIDEO-WORKBENCH-AI.md),
[UX](VIDEO-WORKBENCH-UX.md), [acceptance](VIDEO-WORKBENCH-ACCEPTANCE.md)
and [team](VIDEO-WORKBENCH-TEAM.md).

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

Research can proceed independently within WB-0. Do not begin later-phase
implementation to avoid an unresolved current gate.

## Phase Ledger

| Phase | Status | Exit gate |
| --- | --- | --- |
| WB-0 | In Progress: document drafts written; review/spikes NOT RUN | Approved scope, frozen schemas/limits, evidence-backed feasibility |
| WB-1 | Planned | VA-01 through VA-04; applicable VA-12/13 |
| WB-2 | Planned | VA-05 through VA-07, local part of VA-15/20 |
| WB-3 | Planned | VA-08 through VA-11, VA-17 through VA-19; applicable VA-12/13 |
| WB-4 | Planned | All required cases, regressions, packaging and independent review |

All implementation and acceptance below is pending.

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

Required decisions before WB-1:

- Engine/dependency selection and supported client/container packaging strategy.
- Supported codec/container matrix and numerical resource limits.
- Project JSON schema, rational FPS/output profiles and proxy time mapping.
- Asset storage paths, revision/lease strategy, upload chunking choice and
  failure cleanup. Resumable upload is optional, restart safety is mandatory.
- Exact API schemas/error enums; frontend/backend agree on sample fixtures.
- Initial low-fidelity UX review and agreed performance test envelope.

Additional decisions before WB-3: verified source upload/edit shape, initial
provider capabilities, private remote-handle lifecycle and storage disclosure,
post-submit reconciliation policy and authorized live-test plan.

## WB-1: Assets And Durable Projects

Implement managed external image/video/audio import, exact-ID library selection,
bounded probing, metadata pagination, lazy thumbnails/proxies and project
create/read/save. Prove auth, atomic publication, malformed-media rejection,
missing dependency, disk-full behavior and restart-safe state.

Possible independent packages after schema freeze: media ingestion backend and
asset-browser frontend with contract fixtures. Coordinator alone wires shared
entry points. Integrate early; frontend mocks are not end-to-end evidence.
Exit: imported assets and projects survive restart without changing originals.

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

W0.1: Drafted, awaiting document review; not phase acceptance.
W0.2-W0.5: Not started. No delegated implementation agents or live trials.
Next action: review the scope and open WB-0 decisions, then prepare bounded
research/spike task packets. Do not silently launch paid calls or auto-upgrade
GSD/Agency tools. Retain existing user changes and release handoff in STATUS.
