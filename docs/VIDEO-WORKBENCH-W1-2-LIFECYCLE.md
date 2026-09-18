# WB-1 Local Preview And Task Lifecycle

Evidence date: 2026-09-18 UTC, verified with `Get-Date -AsUTC -Format o`.
Branch: `codex/wb1-baseline-20260918`. Starting commit: `a772d48`.
Status: local preview/lifecycle subgate verified; W1-2 remains in progress.

This is a bounded continuation of W1-2, not completion of WB-1 or permission
to begin the timeline, online editing, production deployment or release.
The coordinator implemented this slice serially. No independent Agent review
is claimed.

## Local Behavior

- `POST /imports` retains its synchronous response by default.
  `Prefer: respond-async` opts into a queued result after bounded staging;
  the response retains the existing `job`/`files` envelope.
- `POST /jobs/{job_id}/cancel` accepts only an authenticated, CSRF-protected,
  body-free request. It persists `cancel_requested`, signals owned work and
  never restarts completed/cancelled/interrupted work.
- `POST /assets/{asset_id}/proxy`, with `X-Request-ID`, admits a local preview
  preparation job and returns HTTP 202. It accepts no media URL, command,
  filter graph, provider identity or arbitrary JSON fields.
- `GET /assets/{asset_id}/proxy` serves only a validated existing cache through
  authenticated single-range streaming. Missing or partial caches are not
  silently regenerated. Repeating the request ID returns the existing task;
  a new explicit request ID is required for new work.
- Original/thumbnail/proxy delivery holds a lease until completion or
  disconnection, including a disconnect before the first response chunk.
- Application shutdown cancels owned jobs before releasing the store lock.
  A second process cannot recover or mutate a store held by a live runtime.

The frozen public asset/job DTO shapes and error vocabulary remain unchanged.
The job `operation` identifies `import` or local `proxy` preparation.
Internal job journals additionally retain exact staging names and input
digest leases. These private fields never enter the public response.
GenBox still has one authenticated administrator workspace.

## Preview Fidelity

The proxy is H.264 MP4, `yuv420p`, square pixels and at most 1280x720.
Accepted AAC audio is copied when present. The original is never replaced,
and later export must still read the managed original.

The renderer applies a common timestamp origin across streams, preserves VFR
intervals and records a private unit-rate source/proxy mapping. Rotation and
sample aspect ratio are normalized into display geometry. Before publication:

1. Verify original identity and existing-cache identity.
2. Render to exact declared staging files with bounded worker resources.
3. Check codec, dimensions, aspect, rotation, stream count, duration and
   relative stream start times; decode the complete output.
4. Recheck the original digest, flush output/manifest and publish the cache.

The manifest is the commit marker. Bytes without a valid matching manifest
are not served. A crash between file and manifest publication retains an
unservable partial cache; it does not overwrite it on retry. Operator-assisted
cache repair remains a follow-up, not implicit destructive cleanup.

Synthetic tests compare VFR frame intervals and cover shifted source PTS,
90-degree rotation, non-square pixels and delayed audio. This is evidence for
these fixtures, not proof of fidelity for every supported media file.

## Cancellation And Recovery

Native execution has separate two-probe and one-render slots, bounded output,
10-second probe and 120-second render deadlines. Temporary reservations remain
1 GiB per local job. Render admission accounts for outstanding import
reservations and vice versa. A file-size cap and post-render validation reject
truncated/oversized output.

The application owns a liveness pipe to the worker launcher. If it exits,
the launcher terminates only its owned native child via the existing Windows
Job Object or POSIX process group. No stored PID is reused to identify a
process. Cooperative checks also cover hashing and stage-copy boundaries.

Recovery first acquires the exclusive store lock. Nonterminal journals become
durably `interrupted`; they are not replayed. Only exact declared upload/proxy
temporary files may be removed after the journal is terminal. Originals and
valid published assets remain intact.

Unknown files, pre-journal upload remnants and partial publication directories
are retained. This deliberately does not claim complete orphan garbage
collection. Recovery rejects malformed or escaping ledger paths rather than
guessing ownership. A failed cleanup remains a visible `cleanup` failure.
There is no source-media deletion or general cache-eviction API.

## Verification

Inputs are checked-in synthetic fixtures or synthetic temporary test outputs.
No fixture manifest or frozen contract was changed.

Verified checkpoints:

- Existing media/boundary tests after worker repair: `52 passed`.
- Dedicated worker lifecycle tests: `11 passed`.
- Final proxy format/cache/timestamp/display/private-path tests:
  `12 passed in 15.19s`.
- Combined workbench suite before the last two recovery/disconnect cases:
  `114 passed in 37.63s`.
- Final job lifecycle tests, including actual process kill/recovery, streaming
  disconnect and shutdown during pre-journal staging: `12 passed in 7.43s`.

Final suite commands/results:

```text
python -m pytest -q
1959 passed in 293.09s

python -m pytest tests/test_video_workbench_media.py tests/test_video_workbench_media_boundaries.py tests/test_video_workbench_api.py tests/test_video_workbench_jobs.py tests/test_video_workbench_proxy.py tests/test_video_workbench_worker_lifecycle.py tests/test_video_workbench_wb1_contracts.py -q
118 passed in 41.29s

python -m py_compile video_workbench/api.py video_workbench/assets.py video_workbench/runtime.py video_workbench/media/ingest.py video_workbench/media/proxy.py video_workbench/media/worker.py video_workbench/media/worker_process.py
PASS

git diff --check
PASS
```

The full suite includes the existing generation/provider/browser regressions.
Earlier full runs of 1957 and 1958 tests are superseded by the final 1959-test
run, which includes the final private-source-path guard.

The explicitly staged 16-file source/test/document scope excludes runtime data,
private media and the four existing debug directories. Added-line secret and
private-path heuristics passed; no comprehensive secret scanner or independent
security audit is claimed. `gh pr list` returned no open PR for this branch.
The three inspected workflow definitions do not match this branch's push
event. No workflow dispatch, tag, merge or release was performed.

Runtime evidence is Windows with the existing Python 3.14 and FFmpeg 7.0.2
installation. POSIX, packaged execution, large-media stress, independent
review and codec redistribution remain unverified. The external FFmpeg
documentation fetch returned no usable content during this run; implementation
evidence comes from the installed tools and synthetic tests, not a claim that
online documentation was successfully inspected.

## Resume Boundary

Remain on W1-2. Next check startup dependency diagnostics, bounded large-library
lookup/picker support, broader disk-full/hostile-media coverage, and explicit
orphan-repair design. Complete those media criteria before W1-3 project storage
or W1-4 UI integration.

First safe commands in the isolated development worktree:

```powershell
git status --short
git log -3 --oneline
python -m pytest tests/test_video_workbench_jobs.py tests/test_video_workbench_proxy.py -q
```

Keep the four pre-existing `tmp-debug-media*` directories untouched and
unstaged. No paid Provider, private upload, service restart, production/VPS
mutation, dependency installation, release workflow, tag or merge is authorized
by this checkpoint.
