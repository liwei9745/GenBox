# Video Workbench WB-0 Readiness Review

Date: 2026-09-18. Revision: 0.1.
Status: Reviewed preparation baseline; WB-0 remains in progress.

## Review Scope

This review checks whether the independent video editing workbench documents,
phase gates and Agent ownership remain aligned after the v2.6.12 video UI
repairs. It does not claim implementation, provider qualification or live
editing support.

## Document Alignment

| Area | Source of truth | Result |
| --- | --- | --- |
| Product scope and deferred work | `VIDEO-WORKBENCH-PRD.md` | READY FOR WB-0 REVIEW |
| Asset/project/timeline invariants | `VIDEO-WORKBENCH-CONTRACT.md` | READY, numeric limits still open |
| Online provider boundary | `VIDEO-WORKBENCH-PROVIDERS.md` | READY, adapters not implemented |
| Google/Omni evidence boundary | `VIDEO-WORKBENCH-AI.md` | READY, sources require revalidation |
| Interaction and responsive UX | `VIDEO-WORKBENCH-UX.md` | READY FOR LOW-FIDELITY REVIEW |
| Acceptance and evidence rules | `VIDEO-WORKBENCH-ACCEPTANCE.md` | READY, all new cases NOT RUN |
| Phase dependencies and gates | `VIDEO-WORKBENCH-PLAN.md` / `ROADMAP.md` | ALIGNED |
| Agent ownership and handoff | `VIDEO-WORKBENCH-TEAM.md` | ALIGNED; no implementation dispatch yet |

The v2.6.12 UI changes remain inside the existing generation/video composer.
They do not create WB-1 asset storage, project persistence, timeline editing,
or online source-video editing. Existing native generation routes and provider
wire contracts remain outside the workbench design boundary.

## Open WB-0 Decisions

WB-1 is blocked until these decisions have evidence and an owner:

1. Supported OS/container targets, media engine and codec licensing boundary.
2. Import/probe limits: bytes, dimensions, duration, streams, project length,
   clip count, concurrency and disk reservation.
3. Canonical project schema, rational FPS/output profiles and proxy time mapping.
4. Managed asset layout, exact library identity, upload staging and cleanup.
5. Route schemas, safe error enum, revision conflicts and idempotency behavior.
6. Low-fidelity interaction flow and measurable performance envelope.
7. Provider upload/edit evidence, private handle expiry and unknown-submission
   recovery before WB-3.

These are decisions, not implementation tasks. Guessed values from model names,
demo projects or local ffmpeg availability must not be promoted to contracts.

## Agent Readiness

The coordinator remains the only owner of shared entry points, contracts,
release actions and authoritative status. The first bounded wave is:

- `W0.2 Media feasibility`: read-only codec/engine/limits research and a
  synthetic local render spike; no user media and no remote upload.
- `W0.3 AI adapter feasibility`: official source revalidation, pinned fixtures,
  provider-neutral type proposal and privacy/recovery matrix; no paid call.
- `W0.4 UX flow`: low-fidelity flow, empty/error states and local/cloud consent.
- `W0.5 Coordinator + independent reviewer`: consolidate schemas, limits,
  ownership and task packets; only this gate can authorize WB-1 planning.

Each dispatch must use the task packet in `VIDEO-WORKBENCH-TEAM.md`, name
requirements and acceptance IDs, freeze owned files, disclose side effects and
return evidence. Shared `main.py`, `static/index.html`, release files and
authoritative docs are serialized through the coordinator. A fake adapter is
interface coverage, not live provider support.

## Gate Result

- **WB-0:** IN PROGRESS.
- **WB-1:** BLOCKED pending W0.2-W0.5 evidence and review.
- **v2.6.12 release:** independent from the workbench; it contains only the
  accepted video composer/diagnostic repairs and documentation baseline.
- **Next safe action:** dispatch only the three read-only W0.2-W0.4 packets,
  then perform W0.5 review before creating implementation plans.
