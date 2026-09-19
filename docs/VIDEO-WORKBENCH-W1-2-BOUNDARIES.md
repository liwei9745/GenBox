# W1-2 Media Boundaries And Library Readiness

Date: 2026-09-19 UTC, checked with `Get-Date -AsUTC -Format o`.
Branch: `codex/wb1-baseline-20260918`. Starting commit: `ef04f1f`.
Status: local boundary/index subgate verified; candidate contract pending approval.

The user approved continuing the next bounded development stage. This report
records local synthetic evidence, not complete WB-1 acceptance or permission
to change the frozen public contracts. The coordinator worked serially.

## Implemented

### Exact library-source index

Within one managed-asset list request, a library directory's names are
enumerated once and indexed by exact case-sensitive stem and suffix. Each
selected path still passes confinement, reparse, file-existence and content
checks. The index is private and request-local; it is not an ownership or
integrity cache.

A changed directory identity/modification time invalidates the names index.
A directory changing during enumeration fails closed. A later request always
starts a new index. Unchanged page reads no longer enumerate the same gallery
for each result. The existing upload/library provenance rules and strict
content-serving checks remain intact.

The synthetic lookup test uses 60 registered-library records and verifies one
directory scan for each 20-result page, including removal/change between
requests. Case/suffix mismatches, prefix matches, missing files, directories
substituted for files and reparse replacements are rejected.

This still enumerates directory names and scans journals; it is not a persistent
large-library database or a measured browser-latency guarantee.

### MP4 reference preflight

A new real synthetic MP4 test exposed a gap: disabling FFmpeg data-reference
resolution did not necessarily reject an MP4 declaring an external reference.
The media import now checks the standard `moov/trak/mdia/minf/dinf/dref` path
before invoking the native worker.

Only self-contained `url ` entries without a location payload are accepted.
External URLs, local aliases, URNs, unknown reference types and compressed
movie metadata fail closed. Header sizes, extended sizes, entry counts and
the supported hierarchy are checked. Media payloads are skipped with seeks;
the preflight reads bounded headers, uses the existing probe deadline and
observes cancellation. The full FFmpeg probe/decode and digest checks remain
required. No external location is resolved by this guard.

The real reference-negative test replaces FFmpeg invocation with a failure
sentinel after constructing its synthetic input; rejection occurs before a
native worker can receive it. A separate read-count test verifies that a
two-MiB synthetic media payload is skipped with less than 128 header bytes read.

This is a narrow standard-container preflight, not a general MP4 parser,
decoder replacement, fuzz campaign or comprehensive malicious-media audit.
Unusual structures still require further coverage and independent review.

## Verified Fixture Matrix

All inputs are checked-in synthetic fixtures or generated in isolated test
temporary directories using the existing bounded worker. No new binary fixture,
dependency, codec redistribution or public schema is introduced.

| Case | Observed behavior |
| --- | --- |
| PNG 4096x4096 | accepted, original unchanged |
| PNG width/height 4097 | rejected at the dimension boundary |
| H.264 1920x1080 | accepted, original unchanged |
| H.264 1922x1080 / 1920x1082 | rejected; even dimensions keep the negative encode valid |
| PCM two channels / 96000 Hz | accepted, original unchanged |
| PCM three channels / 96001 Hz | rejected |
| Two video streams / subtitle stream / non-H.264 MP4 | rejected |
| MP4 external data reference | rejected before native invocation |
| Exact / one-byte-over admission | verified with lowered test limits |
| Multipart disconnect / cancellation | all created spool handles closed |
| Actual process kill before journal creation | unclaimed staging retained, not exposed or replayed |

The byte-admission test exercises the same limit enforcement with small
synthetic files; it is not a physical 512-MiB/one-GiB stress test. The test
does not weaken production limits.

After a pre-journal process crash, there is no durable ownership record
authorizing deletion. The test verifies that restart retains the remnant and
an unknown neighboring file, exposes no phantom asset, and accepts a fresh
explicit import. Automatic orphan repair remains unimplemented by design.

## Test History

- Initial new tests: `20 passed, 1 failed`; the failed real external-reference
  case caused the preflight implementation above.
- Compatibility run after preflight: `68 passed, 26 failed`. Two old dependency/
  timeout tests used invalid placeholder bytes and therefore hit the new earlier
  guard; their failed assertions also left two test reservations and cascaded
  into 24 admission failures. They now use a valid synthetic MP4 and release
  staging in `finally`, retaining the same error expectations.
- Repaired combined subset: `120 passed in 23.74s`.
- Final new-feature subset:

```text
python -m pytest tests/test_video_workbench_mp4_refs.py tests/test_video_workbench_real_boundaries.py tests/test_video_workbench_library_index.py tests/test_video_workbench_upload_interruptions.py -q -W error::pytest.PytestUnhandledThreadExceptionWarning
42 passed in 8.36s
```

Final full regression:

```text
python -m pytest -q -W error::pytest.PytestUnhandledThreadExceptionWarning
2023 passed in 328.42s

$tests = @(Get-ChildItem -LiteralPath tests -Filter 'test_video_workbench*.py' | Sort-Object Name | ForEach-Object { $_.FullName })
python -m pytest @tests -q -W error::pytest.PytestUnhandledThreadExceptionWarning
182 passed in 70.68s

python -m py_compile video_workbench/assets.py video_workbench/media/ingest.py video_workbench/media/mp4_refs.py tests/test_video_workbench_media.py tests/test_video_workbench_library_index.py tests/test_video_workbench_mp4_refs.py tests/test_video_workbench_real_boundaries.py tests/test_video_workbench_upload_interruptions.py
PASS

git diff --check
PASS
```

Runtime is Windows with the existing local tools. No real media, paid provider,
production/VPS, dependency installation, running-service restart, tag, release
or workflow dispatch is involved. POSIX and packaged clients remain unverified.

## Scoped Review And Preservation

VERIFIED / LOCAL: 16 explicitly selected source/test/document files pass staged
diff checks and added-line token/private-key/private-path heuristics. No media
binary, runtime record or existing debug directory is staged. This is a narrow
change review, not a comprehensive secret scanner or independent security audit.

VERIFIED / REMOTE READ: before preservation, the remote branch SHA matched
`ef04f1f`; there was no open PR for the branch. The three inspected workflow
definitions do not match this dedicated branch's push event. Preservation is
limited to a commit/push on that branch, with no tag, merge or release.
Verify the report-containing commit against the remote SHA on resume.

## Backend Versus Picker Gate

VERIFIED / SOURCE: `video_workbench/api.py` lists already registered managed
assets. `AssetService.register_library` accepts an exact source identity, but
does not discover unregistered library candidates.

VERIFIED / SOURCE: `main.py::_scan_gallery` and `GET /api/gallery` use a limit,
not cursor pagination; return additional prompts/local paths/source metadata;
and perform work unnecessary for a minimal candidate browser. They are not the
frozen workbench asset DTO. Existing behavior is left unchanged.

Therefore neither the new internal source index nor the existing managed-asset
list constitutes the full library picker. Remaining work is split explicitly:

1. **Contract decision:** approve a separate minimal, authenticated candidate
   listing and lazy-preview contract before adding public fields/routes.
   See `VIDEO-WORKBENCH-LIBRARY-PICKER-PROPOSAL.md`.
2. **W1-2 backend:** implement and test the approved candidate contract, without
   calling the legacy rich gallery scan or accepting caller paths/URLs.
3. **W1-4 UI:** picker/drop journeys, keyboard/focus, preview loading and the
   four viewport checks. These remain UI acceptance, not backend test claims.
4. **W1-5 review:** independently review the integrated media/project/UI result.
   Near-limit byte stress, broader hostile-media coverage and packaged runtime
   evidence retain their stated limitations.

Do not change `WB1-MEDIA` to accepted or start a later phase to hide the
unresolved candidate contract.

## Resume

First run `git status --short`, verify the report-containing commit and remote
branch SHA, then read the picker proposal and recorded approval state. Leave
the four existing `tmp-debug-media*` directories untouched and unstaged.
Continue candidate API work only after its new response shape is approved;
do not modify the frozen asset/project/job DTOs to fit a library candidate.
