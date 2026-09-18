# WB-1 Media Integration Checkpoint

Evidence date: 2026-09-18 (UTC; clock verified with `Get-Date -AsUTC -Format o`).
Branch: `codex/wb1-baseline-20260918`.
Starting commit: `aea3546`.
Status: local media/API integration gate passed; WB-1 remains in progress.

This checkpoint covers the next authorized shared-entry gate. It does not
complete WB-1, approve a release, or implement online video editing.

## Scope And Ownership

The coordinator owns the media implementation, new `video_workbench/api.py`,
`assets.py`, `multipart.py`, matching tests and minimal `main.py` wiring.
No additional Agent was dispatched. Independent review remains a later gate;
the implementer's tests are not independent review.

User approval covers bounded local media/API integration. It does not cover
changing frozen DTOs/limits, production/VPS mutation, paid Provider requests,
private uploads, dependency installation, release workflows, tags or merges.
No existing service was restarted.

## Implemented Surface

All new routes are under `/api/video-workbench`:

| Method / suffix | Behavior |
| --- | --- |
| `POST /imports` | Multipart `request_id` plus 1-10 `files`; durable import result with per-file state |
| `POST /library` | Frozen registration JSON; `X-Request-ID` header supplies retry identity |
| `GET /jobs/{job_id}` | Sanitized import state/results; never replays interrupted work |
| `GET /assets` | Cursor, kind, bounded query and page size; asset metadata only |
| `GET /assets/{asset_id}` | Verified public asset DTO |
| `GET /assets/{asset_id}/content` | Authenticated original bytes, including bounded single-range requests |
| `GET /assets/{asset_id}/thumbnail` | Authenticated bounded JPEG derivative, generated on demand |

Import executes in a threadpool, not the FastAPI event loop. It is currently
a synchronous HTTP workflow with a durable result journal, not a background
queue with cancellation/progress events. No browser UI is connected yet.

The library operation accepts the existing exact `(kind, item ID)` pair:
PNG `stem` in the image library or MP4 `stem` in the video library. It does
not use the old substring helper, accept filesystem paths, or fetch URLs.
The source is never changed. The journal retains exact source identity and
digest privately; later asset access rechecks it. Missing sources return
`not_found`; changed sources return `conflict`, never an automatic substitute.
The managed validated copy is not a claim that a deleted library source still
exists.

## Authentication And Error Boundary

GenBox currently has one administrator workspace, not a multi-user account
system. The router derives the internal `genbox-admin` owner only after
constant-time validation against the existing configured admin key.
Ownership is not supplied by request JSON and is not derived from a key hash,
so key rotation does not change the workspace owner.

The workbench requires a configured key even in dev mode. The existing
development-mode bypass remains unchanged for older APIs; it is not treated
as authentication for new media access. No key is generated, saved, logged,
placed in a URL or copied into a job/asset document by this implementation.

Mutations additionally require an explicit same/trusted Origin or Referer.
Unknown fields, arbitrary paths/URLs and invalid identities are rejected.
Asset content, thumbnails and ranges all use the same authentication and
ownership boundary. Assets lacking a committed owning journal are not served
through hash lookup.

Public assets and jobs retain the frozen DTO shapes. The import response
envelope contains `job` and `files`; each file has `index`, `state`, and an
`asset_id` or frozen safe `error`. If publication succeeds but cleanup fails,
the asset remains `ready` with a cleanup error; the job identifies its failed
`cleanup` stage without hiding or republishing the successful asset.
Raw worker output, filenames of external
uploads, filesystem paths and prompts are not projected.

## Repairs Before Exposure

- Aggregate-limit failure now cleans the final staged file as well as prior
  files; interrupted iterators also clean issued files.
- Cleanup and probing require the exact manager-issued staging object.
  A forged object cannot remove another job's file.
- Lexical paths are checked before resolution, including Windows reparse
  attributes and all ancestors, before managed directories are created.
- Staging, post-probe bytes and copied publication bytes are rehashed.
  Metadata must come from that staged file's successful probe.
- Complete asset directories are published by rename from a private staging
  directory; public readers do not observe half-written manifests.
- Upload deduplication verifies stored bytes. Library registrations retain
  distinct provenance even when bytes match an upload or another source.
- Native input uses fixed demuxers and a `file`-only protocol allowlist.
  MOV-family external data references and absolute external paths are disabled.
  Accepted input is decoded as well as probed.
- Negative/missing media metadata, invalid limits, nonfinite deadlines and
  malformed persisted manifests fail closed.
- Removed the accidental 120-second **asset** restriction. The frozen
  120-second limit applies to projects; project validation remains W1-3 work.
  Asset decoding remains bounded by worker deadlines and byte/dimension limits.
- Thumbnail failures clean only their owned temporary output.
- Multipart parsing bounds count, field/header/body allocations, per-kind
  bytes and truncated input; spooled files close on parse errors/disconnection.

## Resource Evidence And Limits

VERIFIED LOCAL: Windows, Python 3.14.3, Node v24.14.0 and FFmpeg/ffprobe
7.0.2-full_build-www.gyan.dev. The synthetic suite exercised real native
probing, decoding and thumbnails on this runtime.

Implementation controls:

- two native-worker slots and at most two owned import reservations;
- 1 GiB temporary reservation per admitted media job, plus preflight for
  multipart spool coexistence; insufficient free space fails closed;
- 10-second native deadline, 64 KiB retained output per stream;
- Windows job object: combined 1 GiB memory, two processes including launcher,
  kill-on-close; fixed one-thread decoder/filter settings;
- POSIX launcher: address-space/CPU/file-size/file-descriptor/process limits
  and process-group termination.

These are resource controls, not a claim of an exploit-proof OS sandbox.
Managed storage must remain writable only by the GenBox operator. Lexical
checks do not claim protection from a same-privilege local attacker racing
directory replacement. Disk reservations are conservative admission checks,
not filesystem quotas against unrelated processes.

UNVERIFIED: POSIX execution, packaged launchers, large-media stress and
cross-target codec redistribution. Packaged execution fails closed until a
verified launcher exists; this is not a desktop-release feature claim.

## Verification

All inputs were checked-in synthetic fixtures or generated temporary test data.
The fixture manifest/contract tests passed without changing fixture digests.

```text
python -m pytest tests/test_video_workbench_api.py tests/test_video_workbench_media.py tests/test_video_workbench_media_boundaries.py tests/test_video_workbench_wb1_contracts.py -q
83 passed in 15.90s

python -m pytest tests/test_google_native_video.py tests/test_gemini_official_diagnostics.py tests/test_provider_model_categories.py -q
131 passed in 1.88s

python -m pytest tests/test_google_video_browser.py tests/test_video_composer_browser.py tests/test_generation_experience_browser.py -q
78 passed in 148.19s

python -m py_compile main.py video_workbench/api.py video_workbench/assets.py video_workbench/multipart.py video_workbench/media/ingest.py video_workbench/media/models.py video_workbench/media/worker.py video_workbench/media/worker_process.py
PASS

git diff --check
PASS
```

Final `python -m pytest -q`: **1924 passed in 265.86s** after the cleanup-state
repair. An earlier pre-repair full run passed 1923 tests and is superseded by
this final result. Browser regression is evidence for existing generation
screens, not the unimplemented workbench UI.

The 20 staged source/test/document files passed added-line secret and local
path heuristics plus explicit staged-path review. No comprehensive secret
scanner was installed or run. Existing runtime files and the four untracked
debug directories are excluded. The dedicated development branch has no open
PR at the checked checkpoint; its name does not match the inspected desktop,
Docker or push-quality workflow triggers. No workflow dispatch or release
action is authorized by this evidence.

## Remaining W1-2 Work

1. Proxy pipeline, source-time mapping, cancellation, input leases and durable
   orphan/cleanup recovery. Current cleanup reservations are process-local;
   no automatic source deletion or restart cleanup is implemented.
2. Startup dependency diagnostics and a browser-ready paginated library picker.
   Current asset lookup rehashes originals and scans journals; performance on
   large libraries is not accepted.
3. Broader malicious-container, rotation/PTS, disk exhaustion and restart
   fault-injection coverage. Passing the current fixtures is not all of VA-04.
4. Independent review at an integrated checkpoint, then W1-3 project storage
   and W1-4 UI. Do not advance simply to avoid the remaining media criteria.

## Resume

In the existing isolated implementation worktree:

```powershell
git status --short
git log -3 --oneline
python -m pytest tests/test_video_workbench_api.py tests/test_video_workbench_media_boundaries.py -q
```

Read `STATUS.md`, this checkpoint and the unattended protocol before editing.
Leave the four pre-existing `tmp-debug-media*` directories untouched and
unstaged. Continue a bounded W1-2 task; do not publish, use Provider credentials,
restart the user's running app, or change the frozen contract without the
appropriate new approval.
