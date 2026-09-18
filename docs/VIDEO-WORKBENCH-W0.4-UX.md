# Video Workbench W0.4 UX Feasibility Report

Date: 2026-09-18. Revision: 0.1.
Status: **IN PROGRESS / PROPOSED**. This report freezes the smallest
interaction path for WB-1 planning. It is not a mockup, an implemented UI, or
evidence that the workbench exists.

Related authority:

- [Product requirements](VIDEO-WORKBENCH-PRD.md)
- [Interaction specification](VIDEO-WORKBENCH-UX.md)
- [Core contract](VIDEO-WORKBENCH-CONTRACT.md)
- [Acceptance matrix](VIDEO-WORKBENCH-ACCEPTANCE.md)
- [Development plan](VIDEO-WORKBENCH-PLAN.md)
- [Agent protocol](VIDEO-WORKBENCH-TEAM.md)

## 1. Scope And Evidence Discipline

This report covers W0.4 only:

- the smallest usable local editing flow;
- external import and GenBox library selection as separate choices;
- missing, invalid, interrupted and conflicting states;
- online-edit consent and candidate comparison at the interaction level;
- responsive and accessible behavior;
- measurable UX budgets that WB-0 can ratify before WB-1.

It does not select the media engine, promise a provider capability, define final
route names, or implement UI. Those decisions belong to W0.2, W0.3 and W0.5.

Labels used in this report:

- **VERIFIED**: observed in repository source or an existing focused test on
  2026-09-18. This is evidence about the current application, not workbench
  completion.
- **USER-CONFIRMED**: supplied through the user's observed UI feedback.
- **PROPOSED**: interaction or threshold recommended for the workbench.
- **UNVERIFIED**: requires a future implementation, browser run, or provider
  qualification.

Screenshots and visual comments are useful UX input, but never prove persistence,
ownership, media correctness, billing behavior, or online-provider success.

## 2. Current Evidence And Reusable Patterns

| Finding | Status | Evidence / implication |
| --- | --- | --- |
| The current video page has a preview area, input composer, mode tabs, image-role controls and a result/history area. | **VERIFIED** | `static/index.html:1187-1300`; this is a useful vocabulary source, not a workbench architecture. |
| The current layout keeps the preview and composer inside bounded grid/flex regions and has responsive fallbacks. | **VERIFIED** | `static/css/video-workbench.css:1-42,770-861`; preserve stable dimensions and avoid allowing text or assets to push controls out of view. |
| Prompt input can grow from content, be manually resized, and restore automatic sizing. | **VERIFIED** | `static/js/video-layout.js:23-48,110-139`; `tests/test_video_composer_browser.py:116-151`. The workbench should use the same idea but reserve space for preview/timeline. |
| Results use compact cards, a generating placeholder, and a lightbox rather than always taking over the page. | **VERIFIED** | `static/css/video-workbench.css:597-769`; `tests/test_video_composer_browser.py:225-250,253-269`. Candidate comparison needs a workbench-specific linked player, not full-screen replacement as the only path. |
| Logs have an independent scrollable panel and should not consume the prompt/preview area. | **VERIFIED** | `static/index.html:1209`; `static/css/video-workbench.css:549-584`; `tests/test_video_composer_browser.py:154-188`. Adopt a collapsible job drawer/panel. |
| The current gallery picker has a close button, Escape/backdrop dismissal, focus restoration, loading failure and empty states in focused tests. | **VERIFIED** | `tests/test_video_composer_browser.py:324-386`. The workbench library picker must preserve these guarantees and add exact asset identity. |
| Image-role controls are capability-filtered and explain why unsupported roles are disabled. | **VERIFIED** | `static/js/google-video-ui.js:74-107`; `static/css/video-workbench.css:207-280`; `tests/test_video_composer_browser.py:253-269`. Workbench role controls must come from provider capabilities, never from model-name text. |
| The current media/gallery implementation is not yet a general asset registry or scalable lazy media picker. | **VERIFIED** | `VIDEO-WORKBENCH-CONTRACT.md:10-20`; `main.py::_scan_gallery`, `preview_images`, `get_video_info` are explicitly bounded legacy paths. WB-1 must not copy substring lookup or eager Base64 loading. |
| The user experienced cramped preview space, input panels that could dominate the viewport, hard-to-close floating tools, ambiguous image-role/add-image controls, logs in the wrong region, slow model loading and failed video submissions. | **USER-CONFIRMED** | Conversation/browser comments through 2026-09-18. These are design pain points, not claims about the new workbench implementation. |

### UX interpretation

The common failure pattern is **control density competing with the thing being
inspected**. The workbench therefore uses a preview-first shell, bounded
inspectors, explicit drawers and a timeline with stable minimum height. Prompt
editing, asset role selection, logs and provider settings must not silently
shrink the media preview below its agreed minimum.

## 3. Design Principles To Freeze

1. **Preview first.** The user can see the current project or selected segment
   while editing; controls do not cover the only useful preview.
2. **Asset identity before convenience.** A library selection refers to an
   exact server-owned asset ID. A filename or similar thumbnail is never an
   implicit substitute.
3. **One action, one role.** Import external files and choose from the GenBox
   library are separate actions. Source video, reference image and optional
   audio are visually and semantically distinct.
4. **Progressive disclosure.** Basic editing is available without an AI key.
   Provider/model, advanced settings and cloud consent appear only when the
   selected operation needs them.
5. **Save state is not job state.** “Saved”, “saving”, “conflict” and “local
   draft” are separate from import/render/online-edit progress.
6. **No silent destructive behavior.** Remove from timeline is not delete from
   storage. Candidate acceptance never overwrites the original.
7. **Truthful progress.** Use stage and elapsed time when byte/frame progress is
   unavailable. Never invent a percentage or call a submitted task complete
   before local validation/publication.
8. **Keyboard and pointer parity.** Dragging is optional convenience; every
   critical operation has a focused control or keyboard alternative.
9. **Provider-neutral language.** The workbench names operation and capability,
   not vendor-specific request fields. Unsupported options remain visible as
   unavailable with a reason.

## 4. Low-Fidelity Shell

### 4.1 Desktop composition

**PROPOSED** default at 1440x900 and 1114x994:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Project title  Saved/Saving/Conflict   Undo Redo   Preview   Export         │
├───────────────┬───────────────────────────────────────┬─────────────────────┤
│ Asset browser │                                       │ Selection inspector │
│               │             Preview / player          │                     │
│ Import files  │  playhead, safe-area, current frame   │ clip metadata       │
│ GenBox library│                                       │ trim / audio / edit  │
│ search/filter │  compact job drawer/log (collapsible) │ provider + preset   │
├───────────────┴───────────────────────────────────────┴─────────────────────┤
│ Timeline: ordered picture/video track + independent audio track             │
│ playhead  zoom  scroll  add/trim/split/reorder/duplicate/delete              │
└─────────────────────────────────────────────────────────────────────────────┘
```

- The top toolbar owns project title, save state, undo/redo and export.
- The asset browser owns import and library selection. It does not own
  timeline-edit commands.
- The center preview is unframed or lightly framed and remains visible while
  the inspector changes.
- The inspector is selection-dependent. It must not duplicate generation
  controls in several places.
- The timeline has a stable minimum height and bounded horizontal scrolling.
- A job drawer/panel is anchored near the preview but collapsible. It contains
  sanitized stage, elapsed time, cancel/inspect actions and logs. It does not
  cover the preview or become an unbounded page-height block.

**PROPOSED layout constraint:** the preview area retains at least one 16:9
preview slot of 320x180 CSS pixels on desktop before the user explicitly
collapses it. WB-0 should measure the actual shell with the selected timeline
and inspector minimums; W0.5 may revise the number based on evidence.

### 4.2 Narrow layout

**PROPOSED** at 1024x768 and 390x844:

```text
┌───────────────────────┐
│ title  save  overflow │
├───────────────────────┤
│ preview / play        │
├───────────────────────┤
│ selected clip summary │
│ Edit / Assets / Job   │  <- accessible drawers or tabs
├───────────────────────┤
│ timeline (horizontal) │
├───────────────────────┤
│ primary action bar    │
└───────────────────────┘
```

- On narrow screens, asset browser, inspector and job log become drawers or
  tabs; only one secondary drawer is open at a time.
- Preview, save state and the primary action remain reachable without hunting
  through an overflow region.
- Timeline scrolling is horizontal and bounded; it must not create page-wide
  horizontal overflow.
- The primary action bar is sticky only within the workbench shell, not over
  system/browser UI.
- Mobile support means a complete import/save/basic-edit/export path; it does
  not promise desktop-level precision or multi-panel parity.

## 5. Primary User Flows

### 5.1 Create, import, arrange, save

**PROPOSED / WB-1 minimum path:**

```text
Open workbench
  -> Empty project state
  -> Import external files OR choose from GenBox library
  -> Validate/probe each asset
  -> Add selected asset to timeline
  -> Set still duration if applicable
  -> Save project
  -> Refresh/reopen
  -> Restore same project revision and asset identities
```

1. Empty state presents two equal primary actions: **导入外部素材** and
   **从 GenBox 媒体库选择**. It does not require selecting an AI model.
2. External file selection shows a per-file queue with validation and progress.
   A failed file does not hide or roll back successful files.
3. Library selection supports bounded search/filter and pagination. Thumbnails
   load lazily; metadata remains visible while a thumbnail is loading.
4. Adding to the timeline is explicit by button or drag. A still image shows a
   visible duration field before export.
5. Save feedback is always visible in the toolbar. Refresh/reopen restores the
   last valid revision, not a partially written state.

Maps to PRD VW-01 through VW-04 and acceptance VA-01 through VA-04.

### 5.2 Deterministic local edit and export

**PROPOSED / WB-2 preparation path:**

```text
Select clip
  -> trim or split
  -> reorder / duplicate / delete from timeline
  -> optional source-audio retain/mute or independent audio gain/mute
  -> undo/redo
  -> save revision
  -> export immutable revision
  -> validate output
  -> publish a new video asset
```

- Every edit is reversible within the session.
- Deleting a clip only removes its timeline reference; it does not delete the
  original asset.
- Export shows a revision ID or equivalent human-readable revision context,
  then validates decode, duration and expected streams before publication.
- Output errors keep the project and originals intact and expose a retry path
  that does not silently mutate the project.

Maps to VW-05, VW-06 and acceptance VA-05 through VA-07.

### 5.3 Online edit with a qualified provider

**PROPOSED / WB-3 preparation path:**

```text
Select a video clip/interval
  -> choose "AI edit"
  -> capability preflight
  -> choose eligible provider/model
  -> choose preset or free instruction
  -> review change/preserve intent
  -> review data/cost/retention disclosure
  -> explicit one-time consent
  -> durable local task
  -> observe / cancel / refresh
  -> locally validate candidate
  -> compare with original
  -> accept candidate OR keep/discard
```

- The entry point is disabled or explains the missing requirement when the
  selection is not a video segment.
- Capability preflight runs before any source upload or paid request. It
  validates source type, interval, reference roles, model/profile and
  confirmation freshness.
- The six preset families are **add**, **remove**, **replace**, **attribute
  change**, **global change** and **combined changes**. They are editable
  starting points, not promises that every model can perform the operation.
- The selected preset exposes target, requested changes and preservation intent
  in editable language. Contradictory instructions block submission and point
  to the conflicting fields.
- A provider switch preserves the local draft but invalidates preflight and
  requires new validation/consent.

Maps to VW-07, VW-08, VW-10, VW-11, VW-13 and acceptance VA-08, VA-09, VA-11,
VA-12 and VA-19.

### 5.4 Compare and accept a candidate

**PROPOSED:**

```text
Candidate locally validated
  -> show original + candidate labels
  -> linked seek/toggle or side-by-side
  -> explicit audio choice (muted / original audio / candidate audio if allowed)
  -> accept replacement OR retain candidate OR discard
  -> create new project revision
```

- Comparison is linked to the selected interval and stops at the shorter valid
  boundary. It must not imply equal duration when durations differ.
- The original asset and candidate remain separately addressable with visible
  lineage and provider/model provenance.
- If duration, canvas or stream compatibility fails, the candidate stays
  inspectable but **accept** is blocked with an explanation. The UI never
  silently time-stretches, ripples adjacent clips, crops the project or drops
  audio.
- Default proposal: comparison starts muted; acceptance clearly states that
  original audio is preserved and candidate audio is ignored unless a qualified
  operation explicitly allows otherwise.

Maps to VW-09, VW-10 and acceptance VA-10, VA-17.

## 6. State Matrix

Every row is **PROPOSED** unless the evidence column says otherwise. State text
must be concise, actionable and available to screen readers.

| State | Visible behavior | Primary action | Must not happen |
| --- | --- | --- | --- |
| Empty project | Preview explains that no clips are present; import and library actions are equally prominent. | Import or choose library assets. | Require an AI model/key before local editing. |
| Project loading | Shell keeps title and cancel/back affordance; preview skeleton does not shift toolbar/timeline. | Wait, cancel if allowed. | Show a false “saved” or accept edits against unknown revision. |
| File validating | Each file has validating/probing status and bounded metadata when ready. | Continue with valid files; inspect rejected file. | Trust browser MIME/suffix alone or hide which file failed. |
| Import success | Asset is registered with stable display identity and thumbnail/proxy state. | Add to timeline. | Expose raw filesystem paths or eagerly load all media as Base64. |
| Import failure | Per-file error names reason and next action: unsupported, corrupt, too large, timeout, disk full, auth/permission. | Retry same file, remove failed item, or choose another. | Roll back unrelated successful files or suggest a silent conversion. |
| Duplicate import | Explain that verified bytes already exist and offer reuse while retaining provenance. | Reuse or keep separate reference. | Merge unrelated lineage or create partial duplicate state. |
| Missing asset | Timeline marks exact missing clip and preview shows a bounded missing state. | Relink by explicit asset ID and revalidate. | Choose the first matching filename or silently substitute. |
| Save in progress | Toolbar says saving and keeps current draft editable where safe. | Wait or continue bounded local edits. | Claim durable save before atomic success. |
| Save conflict | Keep local draft, show newer revision timestamp/owner-neutral details. | Reload newer, save as new revision/project, or review diff. | Silent overwrite or discard local work. |
| Unsupported edit | Explain capability/format/role mismatch at the control that caused it. | Change selection, role, profile or provider. | Hide an option, drop a field, or submit a guessed fallback. |
| Provider discovery loading | Model selector shows loading state and retains the user's draft. | Wait, retry, or use local editing. | Freeze the entire workbench or show “no model” as a permanent result. |
| Preflight failed | List each failed check and whether it is local, capability, auth, privacy or cost related. | Fix inputs/settings or cancel. | Upload or submit after failed preflight. |
| Consent required | Show provider, model, source interval, payload class, retention/handle lifetime, cost status and cancellation/recovery policy. | Review and explicitly authorize once. | Treat opening a selector as consent or send a paid request early. |
| Task queued/running | Show stage, elapsed time, local/upstream distinction and a bounded log drawer. | Cancel local work, inspect or refresh. | Fabricate percentage, resubmit on refresh, or hide unknown status. |
| Submission unknown | Explain that local observation stopped and upstream outcome is unresolved. | Reconcile through supported read path or start a new explicitly authorized attempt. | Automatically replay, rotate key, fallback or create a second paid request. |
| Candidate ready | Original/candidate labels, validation state, duration/canvas/audio warnings and provenance are visible. | Compare, accept, retain or discard. | Treat provider “accepted” as locally ready. |
| Candidate mismatch | Candidate stays viewable, accept is disabled with exact mismatch. | Keep candidate or retry with corrected constraints. | Auto-stretch, crop, ripple or replace. |
| Completed export | Show local file/library destination and revision provenance. | Open, download, publish/reuse. | Claim publication before atomic validation. |
| Persistent failure | Error remains in job panel/history with sanitized detail and retry conditions. | Retry only after a changed/fixed condition; export diagnostics without secrets. | Put raw keys, prompts, private paths or unredacted upstream logs in UI. |

## 7. Asset And Role Interaction

### 7.1 Import and library actions

**PROPOSED** asset browser header:

```text
素材
[导入外部素材] [从 GenBox 媒体库选择]
搜索 ________  类型 ▾  排序 ▾
```

- The two actions are separate first-class buttons. A composite button may be
  used visually only if each action remains a separately focusable, named
  control.
- A selected asset card exposes type, duration/dimensions, verified status and
  exact identity. Hover-only labels are insufficient.
- The library picker opens a dismissible dialog/drawer with close, Escape and
  backdrop behavior. Focus returns to the invoking button.
- Do not put a fixed “add” control in the scrolling thumbnail content where it
  moves away from the role controls. The add action belongs to the asset
  browser header or a sticky, bounded toolbar.

### 7.2 Video edit roles

**PROPOSED** for operations that support references:

```text
Source video  [required]
Reference image(s)  [optional, capability-gated]
Audio         [optional, local track or qualified provider input]
```

Role labels are text-first and icon-second. A role is not represented by a
repeated emoji/icon alone. Any disabled role shows a reason and keyboard
accessible description. The UI must never infer “first frame”, “last frame” or
“reference” from list position without a visible role assignment.

The current generation page's four image-role cards and labels are useful
evidence for capability explanations, but the independent workbench should
prefer an explicit asset-role list with thumbnails and removable assignments.
The standalone last-frame/reference combinations remain **UNVERIFIED** until
W0.3 qualifies a concrete provider/model/input shape.

## 8. Model And Preset Selection

**PROPOSED:**

1. Open provider/model selection only after a video interval is selected.
2. Searchable list is grouped by provider, then filtered by operation,
   source/reference roles, output profile, authorization and current health.
3. Server capability metadata controls eligibility. Names containing “video” do
   not grant editing capability.
4. Keep the user's free instruction and preset draft when the model changes.
   Invalidate preflight and show what changed.
5. Advanced controls appear only when the selected adapter declares them.
   Unsupported controls are not rendered as editable fields that will be
   silently discarded.
6. Model discovery loading, empty, stale and error states are independently
   actionable. Local editing remains usable when online discovery is unavailable.

The six preset families are an orientation aid for users, not an assertion that
the first provider supports all six. A preset card must show:

```text
目标对象 / 改变内容 / 保留内容 / 可编辑指令 / 能力要求
```

## 9. Cloud Consent, Privacy And Recovery

Before a remote edit can be submitted, the **PROPOSED** consent surface shows:

- selected provider and model;
- source clip/interval and any reference assets;
- payload categories sent (video, image, audio, instruction, metadata);
- whether GenBox uploads bytes or uses a private remote handle;
- expected retention/expiry of remote handles when known;
- cost or quota disclosure, or “not reported by provider”;
- local result destination and lineage;
- cancellation behavior and the possibility of an unresolved upstream outcome;
- a one-time confirmation action tied to the exact preflight plan.

No real user/private media or paid request is part of W0.4. The online path is
**UNVERIFIED** until W0.3 supplies official/provider-specific evidence and W0.5
freezes the API and privacy fields. A user closing the dialog, switching
provider/model, changing source/reference, or editing the instruction after
preflight must invalidate consent.

## 10. Responsive And Accessible Gates

The following are **PROPOSED WB-0 targets**, not current measurements:

### Fixed acceptance viewports

Browser checks must cover:

- `1440x900` desktop;
- `1114x994` observed user layout;
- `1024x768` short desktop/tablet;
- `390x844` narrow mobile.

At all viewports:

- no page-wide horizontal overflow from the workbench shell;
- no clipped primary action, save status or dialog close control;
- no overlapping text, icons, thumbnails, timeline labels or resize handles;
- preview and timeline retain a usable minimum; exact pixel values are to be
  ratified with W0.2 media/proxy evidence and W0.5 contract review.

### Interaction and performance budgets

- Warm project open reaches usable controls within **2 seconds**, excluding
  full media decode and remote provider discovery.
- Warm proxy seek has p95 visible feedback within **500 ms** over 30 seeks.
- Local timeline actions have p95 visual feedback within **100 ms** over 100
  actions.
- Cancellation is acknowledged within **1 second**; an owned local worker stops
  within **5 seconds** or reports a bounded cleanup-pending state.
- Cloud latency, provider queue time and model generation quality are measured
  separately and do not weaken local interaction promises.
- Text input grows only within a bounded shell budget; after the limit it
  scrolls internally. Manual resize is bounded and has a restore-auto action.
  Exact editor-height limits remain **PROPOSED** until the viewport/media
  measurements are recorded.

### Accessibility

- All icon-only controls expose an accessible name and tooltip where the meaning
  is not obvious.
- Critical controls are reachable by keyboard in logical order. Dragging,
  timeline reorder and resize have keyboard alternatives.
- Pointer/touch targets are at least **44x44 CSS pixels** where the platform
  layout permits; smaller visual icons may sit inside a larger hit area.
- Dialogs/drawers trap focus only while open, return focus on close and let
  Escape close the current dismissible layer.
- Save, import, render, provider discovery and task state changes use a
  suitable live-region/status pattern; errors do not rely on color alone.
- Respect `prefers-reduced-motion`; never communicate progress only by animation.
- Focus outlines remain visible against light/dark themes; disabled controls
  explain why they are disabled.

## 11. WB-1 Minimal Interaction Path To Freeze

Subject to W0.2 media limits, W0.3 provider boundary and W0.5 schema review,
WB-1 should implement only this vertical path:

1. Open a new or existing independent workbench project.
2. Import one external video, one image and one audio file through a bounded
   file picker/drop path.
3. Register/select one exact GenBox library image or video through paginated,
   lazy metadata/thumbnail results.
4. Show per-asset validation, rejection and missing-media states.
5. Add valid assets to one ordered picture/video track and one independent audio
   track; expose still-image duration.
6. Save atomically with a revision and restore after refresh/restart.
7. Keep original bytes untouched and make remove-from-timeline non-destructive.
8. Show safe cancellation and bounded cleanup for import/probe jobs.
9. Prove the responsive and keyboard path at the four fixed viewports.

WB-1 deliberately excludes online provider selection, AI presets, candidate
replacement and export-engine selection until the corresponding WB-0 gates
close. This keeps a usable asset/project slice from concealing unresolved
provider or media-engine decisions.

Acceptance linkage: VA-01 through VA-04, applicable VA-12/VA-13, and the
responsive/local parts of VA-15 and VA-20.

## 12. Open Decisions And Blockers

| Decision | Owner / phase | UX impact | State |
| --- | --- | --- | --- |
| Supported media engine, codecs, client/container targets and numeric limits | W0.2 + W0.5 | Probe messages, progress, preview availability and boundary copy | **UNVERIFIED** |
| Exact project/asset/job schemas, revision and idempotency errors | W0.5 | Save conflict, restore, relink and task recovery states | **UNVERIFIED** |
| Exact library asset identity and lazy thumbnail route | W0.5 | Search results, selection confirmation and missing-media recovery | **UNVERIFIED** |
| Provider upload/edit shape, roles, private-handle lifetime and cost/privacy fields | W0.3 + W0.5 | Consent, preflight, unsupported role and submission-unknown wording | **UNVERIFIED** |
| Final route/navigation placement and visual tokens | W0.5 | Entry discoverability and regression boundary | **PROPOSED; not frozen** |
| Measured minimum preview/timeline dimensions at four viewports | W0.2 + W0.5 | Panel collapse rules and no-overlap acceptance | **UNVERIFIED** |
| Detailed visual mockup and copy review | Coordinator + user | Final wording, density and prioritization | **UNVERIFIED** |

No UX blocker requires code to start. There are, however, implementation
blockers for WB-1: W0.2 must freeze media limits and W0.5 must approve schemas,
ownership and the measured envelope. The provider-specific online flow remains
blocked by W0.3 evidence and must not be implemented as a Google-only shortcut.

## 13. W0.4 Exit Recommendation

**PROPOSED decision: READY FOR W0.5 REVIEW, NOT READY FOR WB-1 AUTHORIZATION.**

W0.4 has a coherent low-fidelity path, state matrix, consent boundary and
measurable responsive/accessibility targets. The following evidence is still
required before the coordinator can mark WB-0 complete:

1. W0.2 media/engine report with bounded fixture behavior;
2. W0.3 provider-neutral capability and privacy/recovery report;
3. W0.5 review that freezes schemas, numerical limits, error enum, ownership
   packets and the final WB-1 interaction path;
4. a future synthetic browser smoke test or low-fidelity review at all four
   viewports. No screenshot alone may substitute for state, persistence or
   security evidence.

### Resume instructions

The coordinator should merge this report into the W0.5 review packet, compare
its proposed minimums with W0.2 measurements, and resolve every **UNVERIFIED**
row before creating WB-1 implementation task packets. Do not edit shared
application entry points from this report and do not start paid/provider calls
or private-media uploads.
