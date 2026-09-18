# Video Workbench W0.5 Contract And Readiness Review

Date: 2026-09-18. Revision: 0.1.
Status: **WB-0 REVIEWED; WB-1 BLOCKED**

This is the coordinator and independent-reviewer consolidation for the
preparation stages in [the development plan](VIDEO-WORKBENCH-PLAN.md). It
reviews the evidence reports; it does not implement the workbench, qualify a
live provider, or authorize a paid request.

## 1. Reviewed Inputs

| Input | Result | Boundary |
| --- | --- | --- |
| [PRD](VIDEO-WORKBENCH-PRD.md) | ALIGNED | Product scope is independent from the existing generation pages. |
| [Core contract](VIDEO-WORKBENCH-CONTRACT.md) | ALIGNED, limits open | Proposed schema and recovery invariants are usable, but exact numeric limits are not frozen. |
| [Provider contract](VIDEO-WORKBENCH-PROVIDERS.md) | ALIGNED | Adapter-neutral boundary is sound; no live adapter is accepted by this review. |
| [AI boundary](VIDEO-WORKBENCH-AI.md) | ALIGNED | Google/Omni is a candidate, not a universal API or current source-video-edit feature. |
| [Acceptance matrix](VIDEO-WORKBENCH-ACCEPTANCE.md) | ALIGNED | VA-01 through VA-20 remain future implementation gates. |
| [W0.2 media report](VIDEO-WORKBENCH-W0.2-MEDIA.md) | **PASS WITH BLOCKERS** | Synthetic local media, proxy and render evidence is complete; packaging and limits remain open. |
| [W0.3 AI report](VIDEO-WORKBENCH-W0.3-AI.md) | **RESEARCH PASS** | Official online-edit shape is documented; live qualification and recovery remain open. |
| [W0.4 UX report](VIDEO-WORKBENCH-W0.4-UX.md) | **PASS WITH BLOCKERS** | Low-fidelity flow and viewport/accessibility gates are ready for implementation planning. |
| [Agent protocol](VIDEO-WORKBENCH-TEAM.md) | ALIGNED | Coordinator owns shared contracts and status; workers have bounded packets. |

## 2. Decisions Frozen For Planning

The following are accepted as **planning invariants**. They authorize task
decomposition, not implementation completion:

1. **Independent boundary.** The workbench is a separate entry and project
   surface. Existing image/video generation routes and native Google transport
   remain regression-protected and are not rewritten as part of WB-1.
2. **Local-first core.** Asset import, project persistence, deterministic
   timeline editing and export do not require an AI provider or API key.
3. **Opaque identity.** Assets, projects, revisions, clips and jobs use
   server-owned opaque IDs. Browser filenames, paths, URLs and model response
   IDs are never trusted identities.
4. **Non-destructive lineage.** Original media remains unchanged. A render or
   online result is a new derived asset with source digest, revision and
   provider provenance.
5. **Time representation.** Timeline ranges use integer microseconds and
   preserve source rational time bases. Floating-point seconds and nominal FPS
   are not authoritative.
6. **Atomic persistence.** Project saves and publication use expected-revision
   checks and atomic replacement. A stale save is a conflict, not an overwrite.
7. **Provider neutrality.** Online editing uses a canonical edit intent and
   capability descriptor. Provider/model discovery cannot self-grant
   `video_edit`; unsupported fields are rejected, not silently dropped.
8. **Consent and recovery.** Cloud upload follows a fresh, plan-bound consent.
   A timeout after possible submission becomes `submission_unknown`; no
   automatic paid retry, fallback or duplicate POST is allowed.
9. **Truthful progress.** Local and remote stages are distinct. Show stage and
   elapsed time when exact progress is unavailable; publish only after local
   result validation.
10. **Preview-first UX.** The preview and timeline retain bounded usable space;
    asset, inspector, job and provider panels collapse or scroll rather than
    pushing the primary media out of view.

## 3. Decisions Still Open Before WB-1

These are implementation blockers and must be resolved with evidence in the
next review revision:

| Blocker | Required decision | Owner |
| --- | --- | --- |
| Media package matrix | Declared Windows/macOS/Linux/Docker FFmpeg build, codec license/provenance, browser playback behavior | Coordinator + media engineer |
| Import limits | Maximum bytes, dimensions, duration, streams, project length, clip count, concurrent jobs and disk reservation | Coordinator + media engineer |
| Output profile | Initial canvas/FPS/fit mode, H.264/AAC compatibility and A/V sync tolerance | Coordinator + media engineer |
| Asset storage | Exact managed paths, staging cleanup, thumbnail/proxy revisions, library identity and relink rules | Coordinator |
| API schemas | Concrete request/response schemas, error enum, CSRF/auth boundary and idempotency behavior | Coordinator |
| Provider live gate | One authorized synthetic source-video edit, remote handle expiry, cancellation and unknown-submission reconciliation | AI adapter specialist + user authorization |
| UX measurements | Measured minimum preview/timeline sizes and four-viewport browser smoke evidence | Product/UX + coordinator |

No value may be promoted from the `PROPOSED` tables in W0.2 or the acceptance
envelope into a public contract without recording the fixture, command,
runtime identity and reviewer.

## 4. WB-1 Task Packets After Blocker Closure

WB-1 remains blocked, but the following packets are ready to be refined once
the open decisions are ratified:

| Packet | Scope | Must not include |
| --- | --- | --- |
| WB1-MEDIA | Probe/import worker, staging, hashing, metadata, thumbnails/proxies, cleanup and bounded failures | Provider calls, project route wiring owned by coordinator |
| WB1-PROJECT | Project schema serializer, revisions, save conflict, restart restore and exact library references | New media codecs or provider transport |
| WB1-UI | Empty/import/library flow, asset list, timeline shell and responsive/keyboard behavior against fixtures | Shared global CSS or unreviewed schema changes |
| WB1-REVIEW | Auth/path/ownership/disk-full/restart/browser review at four viewports | Implementation edits or release actions |

Each packet must cite the accepted schema revision, VA cases, baseline commit,
owned files, fixture digests, commands and stop conditions. Shared
`main.py`, `static/index.html`, authoritative docs, release files and global
styles remain coordinator-owned and serialized.

## 5. Gate Result

- **G1 / W0.2 media feasibility:** **PASS WITH BLOCKERS**. Local synthetic
  decode/proxy/render path is demonstrated; cross-target packaging and exact
  limits are not accepted.
- **G2 / W0.3 online AI feasibility:** **RESEARCH PASS; LIVE BLOCKED**.
  Official Omni editing documentation is recorded; GenBox source-video edit
  support, private-handle recovery and one authorized live edit are absent.
- **G3 / W0.4 UX feasibility:** **PASS WITH BLOCKERS**. The smallest
  preview-first workflow and state matrix are ready for contract review.
- **G4 / W0.5 contract review:** **BLOCKED** until the open decisions above
  are resolved and independently checked.
- **WB-0:** **IN PROGRESS**.
- **WB-1:** **NOT AUTHORIZED**.

This is the intentional result: the project has a staged target and bounded
task packets, but it has not used a design draft or a mock adapter to bypass
media, schema, privacy or provider gates.

## 6. Resume Instructions

1. Coordinator updates the numeric media/schema/error decisions and records
   their evidence.
2. User authorizes at most one controlled live source-video edit only after
   the consent and provider-account/region conditions are shown; use synthetic
   or explicitly redistributable media.
3. Reviewer reruns the W0.5 checklist and changes the gate only from observed
   evidence.
4. If G4 passes, create the WB-1 implementation plan and dispatch only the
   four bounded packets above. If any gate remains open, keep WB-1 blocked.
