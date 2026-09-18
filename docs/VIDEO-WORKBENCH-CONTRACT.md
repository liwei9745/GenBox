# Video Workbench Core Contract

Date: 2026-09-18. Revision: 0.1. Status: Proposed implementation contract.
No routes, schemas or modules described as proposed here exist by implication.
Scope: [PRD](VIDEO-WORKBENCH-PRD.md). Gates: [plan](VIDEO-WORKBENCH-PLAN.md).
Online model extension: [provider contract](VIDEO-WORKBENCH-PROVIDERS.md).

## Current Evidence And Boundaries

VERIFIED by local source inspection on 2026-09-18:

- `main.py::_scan_gallery` lists PNG images and MP4 videos. This is not a
  general audio/video asset registry or a scalable metadata index.
- `main.py::preview_images` returns Base64 images, not a lazy media picker.
- `main.py::get_video_info` uses a substring lookup. Do not reuse that lookup
  to resolve trusted workbench asset identity.
- `_resolve_gallery_file` and `_resolve_video_file` provide existing confined
  resolution patterns to inspect and adapt, not an automatic ownership grant.
- `providers/google_video.py::build_request` accepts generation modes
  `ti2vid`, `i2vid`, `keyframes`; uploaded-video editing needs a separate path.

Proposed modules separate asset ingestion, project storage, timeline validation,
render jobs and online-edit jobs. Thin existing route/UI entry points delegate
to them. Do not rewrite the SPA, replace existing task stores globally, or
change working native/gateway generation as part of this milestone.

## Asset Invariants

The server owns opaque asset IDs and exact mappings to confined managed files.
Requests never contain trusted arbitrary filesystem paths, shell strings,
filter graphs, upstream file identifiers or download URLs.

Proposed asset record:

| Field | Rule |
| --- | --- |
| `asset_id`, `kind`, `origin` | Opaque ID; image/video/audio; upload/library/derived |
| `content_sha256`, `byte_length` | Computed server-side, not trusted from browser |
| `metadata` | Verified codec, duration, dimensions, rotation, audio streams, time base |
| `state` | staging, probing, preparing, ready, rejected, missing |
| `source_asset_id` | Optional lineage; never substitutes for an ownership check |
| `preview_revision` | Invalidates stale thumbnail/proxy caches |

Absolute paths and full probe output remain private. Public asset views contain
bounded metadata and authenticated local media handles, not raw paths/prompts.

External files are streamed to staging on the GenBox host, validated, hashed,
then atomically published in managed storage. Never overwrite the user's file.
Library files are exact references; register and recheck content identity.
Deduplication reuses verified bytes but does not merge unrelated provenance.
Repeated imports must not produce partial visible assets.

Browser MIME and suffix are hints only. Validate actual media; allowlist formats
and probe/decoder protocols. Reject playlists, embedded external references,
archives and arbitrary network fetches. Decode/probe in constrained workers with
time, memory, process and output limits; use argument arrays, never shell input.
Do not block FastAPI's request loop with rendering or unbounded probing.

Bound bytes, dimensions, duration, stream count, project length, clip count,
concurrent jobs and disk reservation. WB-0 must record numeric values and
boundary fixtures before import/processing implementation is enabled.
Missing dependencies return actionable errors, never silent auto-installation.

## Project And Timeline Schema

Proposed project fields: `schema_version`, `project_id`, `revision`, `title`,
`output_profile`, `tracks`, `asset_refs`, `candidate_refs`, timestamps.
Runtime files may contain user edit instructions and remain private, excluded
from Git, release packages, diagnostics and public task views.

- Time is integer microseconds; ranges are half-open `[in_us, out_us)`.
  Store source time bases and rational project FPS separately. Do not accumulate
  floating-point seconds or equate source FPS with project FPS.
- Each video/audio clip references an asset, source interval and timeline start.
  A still uses an explicit positive duration. MVP playback rate is exactly 1.
- The picture track is a contiguous ordered sequence. Reorder/delete recompute
  picture starts; split must preserve total duration within one output frame.
- The independent audio track has explicit positions; picture edits do not
  silently move it. Source video audio follows its own picture clip.
- Validate positive duration, asset existence/type, stream availability, bounds,
  finite numeric values and configured limits on both client and server.
- VFR, rotation, sample aspect and source PTS need tested normalization.
  Proxy mappings must preserve source-time meaning; export reads original
  managed media, not a low-quality preview proxy.
- A project output profile owns canvas, FPS, fit mode and export settings.
  Proposed MVP: fit/letterbox rather than silent crop; WB-0 freezes profiles.

Use atomic project writes and optimistic revision checks. A stale save returns
conflict without replacing a newer revision. Preserve the prior valid snapshot
on corruption or failed migration; reject unknown schema versions safely.
Autosave persists current edits; undo/redo is required within a session.
Cross-restart undo history is deferred and must not be advertised as supported.

## Logical API Boundary

Exact route names and machine-readable schemas are WB-0 deliverables; these
operations are a contract checklist, not claims about available endpoints.

| Operation | Input | Output / required behavior |
| --- | --- | --- |
| Import | Bounded multipart bytes and request ID | Asset/job ID; no cloud upload |
| Register library item | Exact library identity | Validated asset ID or missing |
| List media | Cursor, kind, bounded search | Metadata page; lazy thumbnails |
| Create/read/save project | Validated state and expected revision | Project/revision or conflict |
| Relink | Missing asset plus explicit replacement ID | Revalidated references |
| Preflight export/edit | Project revision, clip IDs, profile/provider | Bound plan and warnings |
| Submit | Confirmed plan ID, idempotency key | Durable local job ID |
| Read/cancel job | Local job ID | Sanitized state; ownership checked |
| Accept candidate | Candidate ID and expected project revision | Atomic new revision |

All operations inherit existing authentication and appropriate CSRF checks.
Asset/task/project ownership is checked server-side, including thumbnails,
range requests and downloads. Do not introduce unauthenticated media routes.

## Jobs, Idempotency And Recovery

Persist local IDs, source revision, input digests, operation type and public-safe
state. Credentials stay in the existing provider credential boundary; never copy
them into project or job JSON.

Normal path: queued -> preparing -> submitting (AI only) -> running ->
finalizing -> succeeded. Other states: failed, cancel_requested, cancelled,
interrupted, submission_unknown. Poll/read transient errors are not proof that
upstream generation failed.

- Persist submission intent before the paid POST. Same idempotency key and same
  intent returns the existing job; same key with different intent is a conflict.
- A crash/timeout after possible submission becomes submission_unknown unless
  an independently verified provider reconciliation path resolves it.
  No automatic replay, key rotation, fallback or new paid POST.
- This is duplicate protection, not a claim of upstream exactly-once execution.
- Local work may be explicitly restarted. AI work requires inspection and fresh
  consent if status cannot be reconciled.
- Cancel queued work before side effects; terminate only owned local processes.
  For submitted AI work, distinguish stopping local observation from provider
  cancellation and billing. A late result never auto-replaces a clip.
- Refresh restores job status. Restart marks non-recoverable active jobs
  interrupted/unknown; it never resubmits paid requests.
- Progress uses actual bytes/frames when available; otherwise show stage and
  elapsed time. No fabricated percentages or premature completion.

## Render And Candidate Publication

An export captures an immutable project revision and input digests. Concurrent
edits do not change that export. Render to a temporary file, validate decode,
duration and expected streams, then publish atomically with provenance.
Library publication is idempotent; retrying publication cannot re-render or
resubmit a paid job.

An AI candidate is a new asset with parent segment, instruction revision and
provider/model provenance. Accepting it checks project revision and lineage.
MVP replacement requires compatible duration (within one output frame) and
canvas handling. Otherwise retain it as a candidate and request manual handling;
do not silently time-stretch, ripple or truncate.

Default proposal: preserve the original segment's audio, ignore candidate audio.
Show this policy before acceptance; replacement must preserve sync. More complex
audio replacement is deferred. "Continue this result" and "edit original again"
use different explicit source IDs.

## Storage, Cleanup And Compatibility

Projects, original uploads, proxies, exports and candidates have separate
lifetimes. Removing a timeline clip is not deleting its media. Cache cleanup
only removes reproducible unleased derivatives. Jobs lease their inputs.
Destructive deletion requires ownership, reference checks and explicit user
confirmation; old gallery deletion may leave a missing reference and must never
cause automatic substitution. Deleting a project does not delete source media.

Validate final resolved paths and reject symlink/reparse escapes. Stage-file
cleanup must be confined to owned temporary files, not recursive user folders.
Document upload failures, disk exhaustion and orphan recovery.

Reuse existing provider and library boundaries without silently broadening them.
Dependency/codec redistribution review and desktop/container availability are
WB-0 and WB-4 gates, not implied by having ffmpeg on one development machine.
