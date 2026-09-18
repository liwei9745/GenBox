# WB-1 Media Diagnostics, Catalogue And Storage Faults

Evidence date: 2026-09-18 UTC, verified with `Get-Date -AsUTC -Format o`.
Branch: `codex/wb1-baseline-20260918`. Starting commit: `0f8b817`.
Status: local usability subgate verified; W1-2 remains in progress.

This is another bounded W1-2 backend subgate, not complete WB-1 acceptance.
The coordinator worked serially. No independent review, user-media test,
live model request, production change or release is claimed.

## Dependency Diagnostics

`GET /api/video-workbench/diagnostics` uses the existing administrator-key
guard and rejects query parameters. Startup and authenticated reads share one
single-flight, 60-second in-memory snapshot. Startup does not resolve the asset
service, create storage or acquire its process lock.

The backend runs only `ffmpeg -version` and `ffprobe -version` through the
existing bounded worker, with a three-second deadline for each tool and the
existing output/concurrency/isolation limits. It never installs dependencies,
opens media, accepts executable paths or exposes native output/build flags.

The auxiliary response is:

```json
{
  "scope": "tool_launch_only",
  "tools": {"ffmpeg": "available", "ffprobe": "available"},
  "available": true,
  "cache_ttl_seconds": 60
}
```

Tool states are `available`, `missing`, `timeout`, `unverified`, `unavailable`
or `unsupported_runtime`. Worker-capacity/isolation failures are `unverified`,
not evidence that the executable is missing. Packaged execution is explicitly
unsupported here. Tool changes may take up to 60 seconds to appear.

This auxiliary diagnostic response changes no frozen asset/job/project DTO or
error code. Successful launch does not certify codecs, decode behavior,
redistribution licensing or a packaged client.

VERIFIED / LOCAL: running `MediaDiagnostics().snapshot()` returned both tools
`available`. The result contains neither executable paths nor native output.

## Catalogue Reads

- Read and validate every job journal once per list request; only upload/library
  ready-result claims can authorize listing. Proxy results and orphan files
  cannot create an ownership claim.
- Filter cursor/query and bounded manifest metadata before byte verification.
  Nonmatching kinds are not fully hashed just to reject them.
- Verify matching assets before returning a cold page. Cache successful
  browsing checks for at most five seconds, with a 256-entry LRU bound.
- Recheck path confinement, manifest metadata, file identity, length and change
  tokens on access. Windows uses `FILE_BASIC_INFO.ChangeTime` for regular files,
  since ordinary `stat` creation time misses same-size writes with restored
  modification time. When no change token is available, caching is disabled.
- Library listing still requires exact source identity and a matching digest;
  source disappearance/change invalidates the browsing check.
- Ownership is never cached. Metadata/content/thumbnail/proxy/processing and
  deduplication paths keep their strict full-byte verification.

This is not a persistent catalogue or an authoritative integrity cache.
Filesystem change tokens are browsing hints, not a replacement for SHA-256
before serving or processing media. Very large journals still require a linear
scan per page, and exact library-source filename lookup is not indexed yet.

The scale test creates 1,000 synthetic asset/journal pairs in temporary storage,
in addition to one fixture import. A 20-result cold page reads 1,001 journals
once and validates 21 originals (one lookahead). Its warm repeat reads the same
1,001 journals once and performs zero additional full-original checks.
Audio filtering of an image-only catalogue adds zero full-original checks.
Cursor, final page, source/manifest mutation, restored-mtime writes, fresh owner
checks, TTL expiry and cache bounds are covered.

These are operation-count measurements, not a real-world latency, large-video
throughput or VA-20 browser-performance claim.

## Storage Failure Behavior

Fault injection covers HTTP low-space admission, initial journal replacement,
atomic original publication, terminal journal writes, persistent background
journal failure, proxy admission and proxy-manifest publication.

- No failed admission launches processing or creates a successful job.
- A published original remains intact if a later journal write fails.
- If terminal state cannot be persisted, declared staging remains. A worker
  exits without leaking private exceptions through thread tracebacks.
- A later task read after disk recovery, or a process restart, durably marks
  unfinished work `interrupted` before confined cleanup. Same-process recovery
  also releases issued staging reservations. Work is never replayed.
- Unknown files remain untouched. A half-published proxy remains unservable
  and is not silently overwritten or cleaned up.
- A one-shot terminal write failure remains a failed job with a sanitized
  per-file error, even if the managed original was already published.

The tests use synthetic bytes, temporary stores and injected failures, not a
physically full system disk. Pre-journal leftovers, unknown publish directories
and operator-assisted partial-cache repair remain separate work.

## Verification

Focused checkpoints:

```text
python -m pytest tests/test_video_workbench_diagnostics.py tests/test_video_workbench_catalog.py tests/test_video_workbench_api.py -q
Initial run: 38 passed, 1 failed (Windows restored-mtime cache invalidation).

python -m pytest tests/test_video_workbench_catalog.py tests/test_video_workbench_storage_faults.py tests/test_video_workbench_diagnostics.py -q -W error::pytest.PytestUnhandledThreadExceptionWarning
19 passed in 23.52s after the Windows change-token repair.

python -m pytest tests/test_video_workbench_storage_faults.py tests/test_video_workbench_catalog.py tests/test_video_workbench_jobs.py -q -W error::pytest.PytestUnhandledThreadExceptionWarning
27 passed in 30.40s, including same-process recovery/reservation release.
```

Final regression:

```text
python -m pytest -q -W error::pytest.PytestUnhandledThreadExceptionWarning
1981 passed in 325.02s

python -m pytest tests/test_video_workbench_media.py tests/test_video_workbench_media_boundaries.py tests/test_video_workbench_api.py tests/test_video_workbench_jobs.py tests/test_video_workbench_proxy.py tests/test_video_workbench_worker_lifecycle.py tests/test_video_workbench_wb1_contracts.py tests/test_video_workbench_diagnostics.py tests/test_video_workbench_catalog.py tests/test_video_workbench_storage_faults.py -q -W error::pytest.PytestUnhandledThreadExceptionWarning
140 passed in 64.55s

python -m py_compile video_workbench/api.py video_workbench/assets.py video_workbench/media/ingest.py video_workbench/media/diagnostics.py video_workbench/media/fingerprint.py tests/test_video_workbench_diagnostics.py tests/test_video_workbench_catalog.py tests/test_video_workbench_storage_faults.py
PASS

git diff --check
PASS
```

The full suite includes existing provider/generation/browser regression.
Windows is the verified runtime; POSIX, packaged execution and independent
review remain unverified.

## Change Review And Preservation

VERIFIED / LOCAL: the explicit 15-file staged scope contains only source,
tests and documentation. Existing debug directories, runtime records and
media files are excluded. Added-line token/private-key/private-path heuristics
and `git diff --cached --check` pass. This is a narrow change review, not
a comprehensive secret scanner or independent security audit.

VERIFIED / REMOTE READ: before preservation, `git ls-remote` matched the
starting commit `0f8b817`; `gh pr list` returned no open PR for the dedicated
branch. The three local workflow definitions do not match its push event.
Preservation is limited to this dedicated branch. No tag, merge, release,
workflow dispatch, dependency installation or service restart is included.
Verify the report-containing commit against its remote SHA on resume.

## Resume Boundary

Read `STATUS.md`, this report and the implementation plan. First run
`git status --short` and verify the branch/checkpoint identity. Leave the four
pre-existing `tmp-debug-media*` directories untouched and unstaged.

Remain on W1-2. Audit the remaining media acceptance against actual tests,
especially hostile-container/near-limit fixtures, interrupted pre-journal
handling and browser-ready library selection. Reconcile backend versus W1-4
browser evidence before changing the media gate; do not mark the whole phase
complete because these backend subcases passed. W1-3 projects, W1-4 UI,
independent review, online adapters and packaging remain later gates.
