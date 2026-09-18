# Video Workbench Interaction Specification

Date: 2026-09-18. Revision: 0.1.
Status: Proposed interaction contract, not a finished mockup or implemented UI.
Scope: [PRD](VIDEO-WORKBENCH-PRD.md). Provider behavior:
[extension contract](VIDEO-WORKBENCH-PROVIDERS.md).

## Navigation And Layout

Add an independent workbench entry; retain the existing image/video generation
routes unchanged. Final route and navigation placement are WB-0 decisions.

Desktop composition: project toolbar at top, asset browser on the left,
unframed preview in the center, selection inspector on the right, timeline below.
Toolbar owns project name/save state, undo/redo and export. The inspector changes
with selection, not by adding duplicate generation controls elsewhere.

Asset browser has two explicit actions: import external files and choose from
GenBox library. Search/type filters operate on paginated metadata. Load thumbnails
on demand; do not fetch all media as Base64 on page open.

Timeline owns playhead, bounded zoom, picture track and audio track. Stable track
heights and minimum panel sizes prevent dynamic labels from shifting controls.
Panels use separators rather than decorative nested cards.

## Primary Interactions

| State / action | Expected behavior |
| --- | --- |
| Empty project | Import and library actions available without selecting an AI model |
| File drop | Show per-file validation/progress; reject unsupported files individually |
| Import to remote GenBox | Disclose transfer to configured GenBox host, separately from AI upload |
| Add media | Explicit add or drag to timeline; still-image duration is visible/editable |
| Trim/split/reorder | Preview affected interval; one reversible editing command |
| Select AI edit | Require a video clip/interval, then show compatible models and presets |
| Switch model | Preserve draft intent, invalidate preflight, revalidate roles/settings |
| Submit | Show cloud/charge disclosure; disable duplicate submit while intent is pending |
| Candidate ready | Side-by-side or toggle comparison, linked seeking, accept/discard |
| Duration mismatch | Keep candidate; explain incompatibility, never stretch automatically |
| Save conflict | Keep local unsaved draft and offer reload/save-as; never silent overwrite |
| Missing asset | Mark affected clip and offer explicit relink; do not guess a substitute |
| Export | Snapshot revision, show queued/running/finalizing state and output destination |

Linked comparison maps both players to the selected interval and stops at the
shorter valid boundary. It must not imply equal durations when they differ.
Default comparison is muted; original/candidate audio selection is explicit.
Acceptance shows the original-audio preservation policy.

## Model And Preset Selection

Searchable model list grouped by provider. Operation and asset compatibility
filters come from the server's capabilities, not names containing "video".
Settings may explain unavailable models; ordinary selection contains only
eligible or explicitly opted-in experimental profiles.

Six preset families appear as compact selectable tools, not claims of guaranteed
output. The selected preset reveals target, changes, preservation intent and
editable final instruction. Advanced options appear only when the adapter
declares them. No hidden prompt changes or invented percentages.

Reference images occupy a distinct optional slot only for verified combinations;
the source-video slot must never be confused with a reference-video slot.

## State And Feedback

Display local save state independently from render/edit job state.
Use stage and elapsed time when actual progress is unavailable. A result is ready
only after local validation and publication, not after submission was accepted.

Keep a compact job/log area above the editing controls, not over preview content
or below an inaccessible overflow boundary. Show sanitized errors with next
actions. Completion/failure notifications use bottom-right positioning with
limited stacking; persistent failures also remain in the relevant job panel.

Cancel messaging distinguishes local processing stopped, upstream cancellation
confirmed, and local waiting stopped while upstream outcome remains unknown.
Refresh reattaches to a job; it never triggers another submission.

## Responsive And Accessible Behavior

Validate at 1440x900, 1114x994 (the user's observed layout), 1024x768 and 390x844.
At narrow widths, collapse side panels into accessible drawers and use bounded
timeline scrolling; keep preview, save status and primary actions reachable.
MVP mobile support means functional access, not full desktop editing parity.

Use existing project tokens and icon conventions. Icon tools need accessible
names, tooltips and keyboard focus. Support keyboard add/reorder/trim through
controls as an alternative to dragging. Dialogs return focus, Escape closes only
the current dismissible layer, and error status is announced appropriately.
Respect reduced motion; text must not overlap or rely on color alone.

WB-0 produces a reviewed low-fidelity flow before detailed visual implementation.
Screenshots use synthetic fixtures only, never exposed keys or private media.
Do not add a separate frontend framework merely to copy a component-library demo.
