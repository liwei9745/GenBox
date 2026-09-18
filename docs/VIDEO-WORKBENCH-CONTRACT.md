# Video Workbench Core Contract

Date: 2026-09-18. Revision: 0.2.
Status: **Frozen WB-0 planning contract; implementation routes do not yet exist.**
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

## WB-0 Freeze: First-Release Contract

This section supersedes earlier `Proposed` wording for the purpose of planning
WB-1. It freezes the first-release boundary and conservative validation limits;
it does not claim that the routes or modules already exist. A limit may be
revised only through a contract revision with new fixture evidence and
acceptance impact.

### Frozen first-release media boundary

The first local editing slice uses **FFmpeg/ffprobe as an external worker
dependency**. The worker is invoked with argument arrays, a confined working
directory and bounded process/resource controls. GenBox must expose a startup
diagnostic when either executable is missing; it must not silently install a
codec package.

| Input / output | Frozen WB-1 planning rule |
| --- | --- |
| Video input | MP4/H.264 with optional AAC, and WebM/VP9 as input-only |
| Audio input | WAV/PCM or MP3; AAC is accepted when carried by an accepted MP4 |
| Still input | PNG, JPEG or WebP after decoder/content validation |
| Output | MP4/H.264 `yuv420p`; AAC when an audio stream is present |
| Preview proxy | H.264 MP4, maximum 1280x720; never used as export source |
| Thumbnail | JPEG, maximum 320x180 display target |
| Video dimensions | Maximum 1920x1080 for WB-1 imports |
| Still dimensions | Maximum 4096x4096 |
| Audio | At most 2 channels and 96 kHz; render may resample to the output profile |
| Stream count | At most one video stream and one audio stream; reject subtitle/data streams |
| Rejected inputs | Playlists, archives, embedded network references, arbitrary URLs and unknown codecs |

These are **FROZEN / PLANNING** limits, not claims of the maximum that the
current host can decode. They are intentionally narrower than FFmpeg's local
capabilities so WB-1 can provide predictable errors and bounded resource use.
WebM/VP9 is not an export promise; packaged-runtime and browser checks remain
WB-4 acceptance evidence.

### Frozen resource limits

| Limit | Value | Enforcement point |
| --- | ---: | --- |
| One asset | 512 MiB video/audio; 64 MiB still | staging admission before probe |
| One import request | 10 files and 1 GiB total | request validation |
| Project duration | 120 seconds | client hint and server validation |
| Picture clips | 20 clips on the single picture track | project validation |
| Audio clips | 20 clips on the single audio track | project validation |
| Tracks | one picture/video track plus one audio track | project validation |
| Still duration | 0.5 to 30 seconds | timeline validation |
| Local media jobs | 2 probe jobs and 1 render job per instance | scheduler |
| Online edit observation | 1 submitted edit per project at a time | job/idempotency boundary |
| Temporary reservation | 1 GiB per local probe/render job | admission and cleanup |
| Project JSON | 4 MiB serialized state | save validation |

The 120-second/20-clip envelope is the same planning target described in the
acceptance matrix. W0.2's synthetic measurements establish feasibility of the
worker path, not a performance guarantee for large media. WB-4 must measure
memory, disk and cross-target behavior before a release claim.

### Frozen output profiles

WB-1 exposes two profiles:

```json
{
  "profile_id": "landscape_1080p_30",
  "canvas": {"width": 1920, "height": 1080},
  "fps": {"num": 30, "den": 1},
  "fit_mode": "contain",
  "video_codec": "h264",
  "pixel_format": "yuv420p",
  "audio_codec": "aac"
}
```

The second profile is `portrait_1080p_30` with a 1080x1920 canvas. The
workbench may select 24/1 or 25/1 as an explicit profile revision later, but
WB-1 uses 30/1 only. Letterbox/contain is explicit; silent crop, stretch and
automatic aspect-ratio changes are forbidden. Source time remains represented
with integer microseconds and rational stream time bases.

### Frozen logical storage layout

These are logical, confined paths; no absolute path is exposed to the browser:

```text
storage/video_workbench/staging/{job_id}/
storage/video_workbench/assets/{asset_id}/original
storage/video_workbench/assets/{asset_id}/derived/{preview_revision}/
storage/video_workbench/projects/{project_id}.json
storage/video_workbench/jobs/{job_id}.json
```

Staging is owned by the import/job ID and may be cleaned only after the job is
terminal. Originals, projects and accepted candidates have separate lifetimes.
Derived thumbnails/proxies are reproducible and may be removed only when no
active lease references them.

### Frozen project JSON shape

The following is the minimum server-validated shape. Additional fields require
a schema revision; unknown fields are rejected rather than silently dropped.

```json
{
  "schema_version": 1,
  "project_id": "prj_opaque",
  "revision": 1,
  "title": "untitled",
  "output_profile": {
    "profile_id": "landscape_1080p_30",
    "canvas": {"width": 1920, "height": 1080},
    "fps": {"num": 30, "den": 1},
    "fit_mode": "contain"
  },
  "asset_refs": [
    {"asset_id": "ast_opaque", "kind": "video", "digest": "sha256:..."}
  ],
  "tracks": [
    {
      "track_id": "trk_picture",
      "kind": "picture",
      "clips": [
        {
          "clip_id": "clip_opaque",
          "asset_id": "ast_opaque",
          "source_in_us": 0,
          "source_out_us": 2000000,
          "timeline_start_us": 0,
          "duration_us": 2000000,
          "playback_rate": {"num": 1, "den": 1}
        }
      ]
    },
    {"track_id": "trk_audio", "kind": "audio", "clips": []}
  ],
  "candidate_refs": [],
  "created_at": "2026-09-18T00:00:00Z",
  "updated_at": "2026-09-18T00:00:00Z"
}
```

The server recomputes digests, duration and asset metadata. `expected_revision`
is required on every save. A stale revision returns `conflict` and leaves both
the stored revision and the caller's draft intact.

### Frozen logical API operations

The implementation may choose framework-specific route spelling, but it must
expose these operations with the listed semantics:

| Operation | Required request fields | Required result |
| --- | --- | --- |
| Import external | multipart bytes, request ID | local asset/job ID; per-file state |
| Register library | exact library item identity | validated opaque asset ID or `missing` |
| List assets | cursor, kind, bounded query | paginated metadata; lazy preview handles |
| Create project | title, output profile | project ID and revision 1 |
| Read project | project ID | latest valid snapshot |
| Save project | project ID, expected revision, validated document | new revision or `conflict` |
| Relink asset | project/clip ID, replacement asset ID | revalidated revision |
| Preflight local/online | project revision, clip IDs, operation | immutable plan ID and warnings |
| Submit job | plan ID, idempotency key, consent ID when online | durable local job ID |
| Read/cancel job | job ID | sanitized state; no resubmission |
| Accept candidate | candidate ID, expected project revision | new revision or `conflict` |

All operations use the existing authenticated application boundary and
appropriate CSRF protection. Browser input cannot contain shell commands,
filesystem paths, arbitrary URLs, provider credentials or upstream request
bodies.

### Frozen error vocabulary

The public error object is:

```json
{
  "code": "unsupported_media",
  "stage": "probe",
  "message": "此素材格式不在当前工作台支持范围内。",
  "retryable": false,
  "field": "file"
}
```

Allowed `code` values are:

`invalid_request`, `auth_required`, `forbidden`, `not_found`, `conflict`,
`unsupported_media`, `media_corrupt`, `asset_too_large`, `dimension_limit`,
`duration_limit`, `probe_timeout`, `dependency_missing`, `disk_space`,
`job_not_found`, `job_cancelled`, `cleanup_pending`, `provider_unavailable`,
`unsupported_capability`, `consent_required`, `submission_unknown`,
`remote_failed`, `invalid_result`, and `internal`.

Messages are localized safe text. Raw exceptions, provider bodies, signed
URLs, credentials and private paths never appear in the public error.

### WB-0 versus later gates

WB-0 freezes the planning contract above. The following remain later-phase
acceptance evidence and are not blockers to declaring the preparation phase
complete:

- cross-platform packaged FFmpeg/browser behavior (`VA-16`, WB-4);
- stress, disk-full, hostile-media and restart tests (`VA-04`, `VA-12`,
  `VA-13`, WB-1/WB-4);
- a real Google or other provider source-video edit (`VA-17`, WB-3/WB-4);
- provider remote-handle expiry, cancellation and reconciliation (`VA-11`,
  WB-3);
- measured performance on declared package targets (`VA-20`, WB-4).

These are still required before the corresponding feature or release can be
accepted. Deferring them does not advertise unsupported capabilities.
