# Video Workbench W0.5 Contract And Readiness Review

Date: 2026-09-18. Revision: 0.2.
Status: **WB-0 PASS; WB-1 implementation not started**

This is the coordinator and independent-reviewer consolidation for the
preparation stages in [the development plan](VIDEO-WORKBENCH-PLAN.md). It
reviews the evidence reports; it does not implement the workbench, qualify a
live provider, or authorize a paid request.

## 1. Reviewed Inputs

| Input | Result | Boundary |
| --- | --- | --- |
| [PRD](VIDEO-WORKBENCH-PRD.md) | ALIGNED | Product scope is independent from the existing generation pages. |
| [Core contract](VIDEO-WORKBENCH-CONTRACT.md) | **FROZEN FOR WB-1 PLANNING** | Schema, media boundary, numeric limits, storage and error vocabulary are explicit; implementation routes do not yet exist. |
| [Provider contract](VIDEO-WORKBENCH-PROVIDERS.md) | **FROZEN FOR WB-0/WB-3** | Adapter-neutral boundary is sound; live profiles remain unavailable. |
| [AI boundary](VIDEO-WORKBENCH-AI.md) | ALIGNED | Google/Omni is a candidate, not a universal API or current source-video-edit feature. |
| [Acceptance matrix](VIDEO-WORKBENCH-ACCEPTANCE.md) | ALIGNED | VA-01 through VA-20 remain future implementation gates. |
| [W0.2 media report](VIDEO-WORKBENCH-W0.2-MEDIA.md) | **PASS** | Synthetic local media, proxy and render evidence supports the frozen WB-1 planning matrix; package smoke remains WB-4. |
| [W0.3 AI report](VIDEO-WORKBENCH-W0.3-AI.md) | **RESEARCH PASS** | Official online-edit shape is documented; live qualification and recovery remain open. |
| [W0.4 UX report](VIDEO-WORKBENCH-W0.4-UX.md) | **PASS** | Low-fidelity flow and viewport/accessibility targets are frozen for WB-1 planning; browser proof remains implementation evidence. |
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

## 3. Later-Phase Evidence (Not WB-0 Blockers)

The following remain mandatory for the phases that implement or release them.
They do not invalidate the WB-0 preparation pass because the current objective
was read-only feasibility and contract freeze:

| Blocker | Required decision | Owner |
| --- | --- | --- |
| Packaged media matrix | Windows/macOS/Linux/Docker FFmpeg build, codec provenance and browser playback | WB-4 |
| Import fault evidence | Oversized/corrupt/VFR/rotation/disk-full/cleanup/restart behavior | WB-1/WB-4 |
| Local render evidence | A/V sync, immutable publication and measured performance | WB-2/WB-4 |
| Provider live gate | One authorized synthetic source-video edit, remote handle expiry, cancellation and reconciliation | WB-3/WB-4 |
| UX browser evidence | Four viewport journey, keyboard path and measured shell dimensions | WB-1/WB-4 |

The frozen planning values in the core contract are not runtime proof. Each
later implementation gate must record fixture, command, runtime identity,
result and reviewer before advertising the corresponding feature.

## 4. WB-1 Task Packets For Plan Review

WB-1 implementation has not started. The following packets are ready to be
refined into the reviewed WB-1 implementation plan:

| Packet | Scope | Must not include |
| --- | --- | --- |
| WB1-MEDIA | Probe/import worker, staging, hashing, metadata, thumbnails/proxies, cleanup and bounded failures | Provider calls, project route wiring owned by coordinator |
| WB1-PROJECT | Project schema serializer, revisions, save conflict, restart restore and exact library references | New media codecs or provider transport |
| WB1-UI | Empty/import/library flow, asset list, timeline shell and responsive/keyboard behavior against fixtures | Shared global CSS or unreviewed schema changes |
| WB1-REVIEW | Auth/path/ownership/disk-full/restart/browser review at four viewports | Implementation edits or release actions |

Each packet must cite the frozen schema revision, VA cases, baseline commit,
owned files, fixture digests, commands and stop conditions. Shared
`main.py`, `static/index.html`, authoritative docs, release files and global
styles remain coordinator-owned and serialized.

## 5. Gate Result

- **G1 / W0.2 media feasibility:** **PASS**. Local synthetic
  decode/proxy/render path is demonstrated and the conservative WB-1 media
  matrix and limits are frozen. Cross-target packaging is a later gate.
- **G2 / W0.3 online AI feasibility:** **RESEARCH PASS; LIVE BLOCKED**.
  Official Omni editing documentation is recorded; GenBox source-video edit
  support, private-handle recovery and one authorized live edit are absent.
- **G3 / W0.4 UX feasibility:** **PASS**. The smallest preview-first
  workflow, state matrix and measurable target envelope are frozen.
- **G4 / W0.5 contract review:** **PASS**. Scope, contract, limits,
  acceptance gates and ownership packets are frozen for planning.
- **WB-0:** **PASS**.
- **WB-1:** **PLANNED; implementation not started**.

This is the intentional result: the project may now prepare a WB-1
implementation plan, but it has not used a design draft or a mock adapter to
claim local editing, online editing or packaged-runtime support.

## 6. Resume Instructions

1. Create the WB-1 implementation plan from the frozen contract revision; do
   not edit application entry points until the plan is reviewed.
2. Dispatch only the four bounded WB-1 packets in
   `VIDEO-WORKBENCH-TEAM.md`, with explicit file ownership.
3. Keep source-video provider work unavailable until WB-3 obtains separate
   user authorization and live evidence.
4. Run the later acceptance gates before claiming any implementation or
   release completion.
