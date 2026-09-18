# Video Workbench Product Requirements

Date: 2026-09-18. Revision: 0.2.
Status: **WB-0 scope frozen; no workbench implementation or acceptance.**

## Authority And Reading Order

[PRODUCT](PRODUCT.md), [ARCHITECTURE](ARCHITECTURE.md),
[STATUS](STATUS.md), and [ROADMAP](ROADMAP.md) remain authoritative.
This topic does not replace the extension-center initiative or close its gates.

Read this PRD, [contract](VIDEO-WORKBENCH-CONTRACT.md),
[provider extension contract](VIDEO-WORKBENCH-PROVIDERS.md),
[AI boundary](VIDEO-WORKBENCH-AI.md), [acceptance](VIDEO-WORKBENCH-ACCEPTANCE.md),
[UX specification](VIDEO-WORKBENCH-UX.md), [plan](VIDEO-WORKBENCH-PLAN.md),
and [team protocol](VIDEO-WORKBENCH-TEAM.md), in that order.

USER-CONFIRMED direction: independent editing workbench, online AI rather than
local generative models, reusable editing presets, GenBox library selection,
external media import, and gradual expansion toward everyday video editing.
USER-CONFIRMED addition: support future online video-editing models through
extensible provider interfaces; the workbench must not be Google-specific.
The first-release scope is frozen by WB-0. Numeric media limits and the
provider-neutral contract are frozen in
[VIDEO-WORKBENCH-CONTRACT.md](VIDEO-WORKBENCH-CONTRACT.md) and
[VIDEO-WORKBENCH-PROVIDERS.md](VIDEO-WORKBENCH-PROVIDERS.md); UX gates are
frozen in [VIDEO-WORKBENCH-UX.md](VIDEO-WORKBENCH-UX.md).

## Product Outcome

Create a short finished video without leaving GenBox: choose library assets or
import files, arrange and trim them, optionally edit a selected video segment
through a supported online model, compare a candidate, and export a new file.
Original assets remain unchanged. Ordinary editing works without an AI key.

## First-Release Scope

| ID | Requirement | Delivery phase |
| --- | --- | --- |
| VW-01 | Independent route and project create/open/save/restore | WB-1, WB-2 |
| VW-02 | File picker and drag/drop import for images, videos, audio | WB-1 |
| VW-03 | Searchable, paginated GenBox image/video library picker | WB-1 |
| VW-04 | Validated metadata, thumbnails, preview proxies, missing-media recovery | WB-1, WB-2 |
| VW-05 | One ordered picture/video track and one independent audio track; trim, split, reorder, duplicate, delete, undo/redo | WB-2 |
| VW-06 | Export a new MP4 from an immutable project revision and publish to the video library | WB-2 |
| VW-07 | Optional online edit of one source-video segment, capability preflight and explicit submission consent | WB-3 |
| VW-08 | Six editing preset families plus free instruction; editable modify/preserve intent | WB-3 |
| VW-09 | Original/candidate comparison, explicit replacement, retained lineage and original | WB-3 |
| VW-10 | Recoverable tasks, honest progress, bounded cancellation and duplicate-submit protection | WB-1 through WB-3 |
| VW-11 | Authentication, bounded hostile-media handling, privacy and non-destructive cleanup | Every phase |
| VW-12 | Existing generation regression gates and reproducible packaged-runtime verification | WB-4 |
| VW-13 | Provider-neutral editing contract, explicit adapter registration and capability-filtered model selection | WB-0, WB-3 |

WB-2 delivers a useful non-AI editing slice, not completion of this AI workbench.
WB-3 additionally requires an authorized real edit; mock success is insufficient.

The six preset families are add, remove, replace, attribute change, global
change, and combined changes. They are instruction templates, not six
independently verified model capabilities. High motion is a difficult scenario,
not a guaranteed enhancement feature.

## Scope Details

- Both import entrances are first-class. External uploads go to the GenBox
  host's managed storage; on a remote GenBox instance this is a network upload,
  not storage on the browser's own machine.
- Uploaded images, videos and audio share a workbench asset registry. Existing
  GenBox library images/videos are registered by exact identity. Audio support
  does not imply that the existing global gallery already supports audio.
- The MVP picture track is sequential, with hard cuts and explicit still-image
  durations. No overlapping picture clips, transitions or speed changes.
- Source video audio can be retained or muted; the extra audio track supports
  trim, position, gain and mute. Fancy mixing and automatic ducking are later.
- Still images can join the timeline. AI video editing requires a video segment;
  an image is not silently converted into a video-edit request.
- Reference-image selection is designed as a distinct role but submission is
  capability-gated until the source-plus-reference combination is verified.
- AI replacement never silently stretches adjacent clips, replaces source files,
  discards audio, or changes project aspect ratio.

## Deferred Scope

Multi-track compositing, animated text, subtitles/ASR, online TTS, transitions,
keyframe effects, speed ramps, automatic reframing, transcription-based editing,
natural-language timeline automation, templates and batch AI editing are
follow-on milestones, not hidden first-release requirements.

Also excluded: arbitrary URL downloads, cloud-drive sync, watched folders,
directory crawling, mobile-app parity, collaborative editing, local generative
model deployment, voice cloning, guaranteed identity/motion locks, and copying
SAIS Omni-Video code/assets without a separate license review.

## User Journeys

1. Import an external clip and audio file, add a library image, trim and arrange,
   save, restart, reopen, then export a playable new video.
2. Select a video segment, choose a preset, inspect the instruction and cloud
   submission details, authorize one edit, compare, then accept or discard.
3. Recover from a missing library file by explicitly relinking a compatible
   asset; never select the first filename that happens to match.
4. Cancel an import/render/edit wait, see the accurate local/upstream status,
   and retain both the project and all original assets.

## Scope Change Control

Every implementation task names VW requirement IDs and acceptance cases.
A scope change updates this PRD, affected contracts, tests and plan before coding.
The coordinator records impact and obtains user confirmation for material scope,
cost, privacy or compatibility changes. New ideas default to the deferred list.
Numeric media limits, engine selection and performance targets require WB-0
evidence; they are not assumed from a demo or from an online-model name.
