# W1-2 Candidate Library Backend

Date: 2026-09-19 UTC. Branch: `codex/wb1-baseline-20260918`.
Starting checkpoint: `5923d55`.
Status: candidate backend implemented and locally verified; full WB-1 remains open.

## Authorization And Contract

USER-CONFIRMED: continue the approved candidate-library scope, following the
current bounded unattended plan. The exact additive boundary is revision 0.1
of `VIDEO-WORKBENCH-LIBRARY-PICKER-PROPOSAL.md`.

No change to asset/job/project DTOs, configured admin authentication, byte/
worker limits, old gallery behavior, Provider transports or source deletion.
Coordinator-only execution; no independent review or extra Agent dispatch.

## Implementation

- `GET /library/candidates`: authenticated, bounded, keyset-paginated exact
  PNG/MP4 identities, optional kind/search filter and informational byte length.
  No metadata extraction, hashing, decoding, asset registration or recursive
  traversal. Memory retains at most `limit+1` rows while enumerating.
- Cursor binds kind/query and the last exact kind/ID. Unknown/duplicate query
  parameters and malformed/stale-filter cursors are rejected. Enumeration
  budget exhaustion and concurrent directory mutation return conflict, not
  an incomplete success page.
- `POST /library/preview`: authenticated/CSRF-protected explicit lazy decode,
  existing staging and media validation, bounded JPEG and source SHA-256
  response header. Shared thumbnail command/validation are reused.
- Preview source is copied, hashed and validated, leased during processing,
  then exactly re-resolved/rehashed. No managed asset, manifest, durable import
  job or candidate cache is created.
- The JPEG is buffered within its four-MiB limit and exact temporary files
  are cleaned before response delivery. Failure is not reported as success.
  Derivative-cleanup failure retains input/reservation for recovery.
- Disconnect/shutdown uses the existing cooperative worker cancellation.
  Unknown or process-crash/pre-journal remnants are not deleted.
- Existing explicit `POST /library` with preview `expected_sha256` rejects
  changed selection. Only successful registration publishes an asset.

## Synthetic Verification

The new module contains 48 test cases. Fixtures are checked-in synthetic
PNG/MP4 bytes copied into pytest-owned directories. No new binary fixture or
dependency was added.

Observed commands:

```text
python -m pytest tests/test_video_workbench_library_picker.py tests/test_video_workbench_api.py tests/test_video_workbench_library_index.py -q -W error::pytest.PytestUnhandledThreadExceptionWarning
80 passed in 15.65s

$tests = @(Get-ChildItem -LiteralPath tests -Filter 'test_video_workbench*.py' | Sort-Object Name | ForEach-Object { $_.FullName })
python -m pytest @tests -q -W error::pytest.PytestUnhandledThreadExceptionWarning
230 passed in 76.36s

python -m py_compile video_workbench/api.py video_workbench/assets.py video_workbench/library.py video_workbench/media/ingest.py tests/test_video_workbench_library_picker.py
PASS

python -m pytest -q -W error::pytest.PytestUnhandledThreadExceptionWarning
2071 passed in 332.93s

git diff --check
PASS
```

Coverage includes Unicode/filter-bound pagination, no eager probe/hash,
missing roots, scan bounds and concurrent directory mutation, exact
case/substring refusal, real PNG/MP4 thumbnail generation, digest-bound import,
source change/removal, malformed/extra/duplicate inputs, authentication/CSRF,
symlinks, cooperative ASGI disconnect, admission conflict, dependency/timeout/
disk failures and derivative/input cleanup failures with retained ownership.
Tests assert originals unchanged, no implicit publication, no path in public
errors and released input leases.

One initial test incorrectly patched the process-wide monotonic clock while
running through TestClient. It was corrected to lower the enumeration budget;
production limits and expected rejection behavior were not loosened.

## Limits And Remaining Gates

- Local Windows evidence only. No paid Provider, private media, remote upload,
  production/VPS, service restart, release, tag or workflow dispatch.
- This is a backend subgate, not the completed picker/browser journey or
  completed WB-1. W1-4 owns focus/keyboard/object-URL lifecycle and responsive
  UI; W1-5 owns independent integrated review.
- Keyset pagination is not a filesystem snapshot. An item added before the
  seek position appears only after refresh. Listing does not certify media.
- Scan limits are cooperative entry/time checks around local filesystem work,
  not preemption of a blocked OS filesystem call or a persistent gallery index.
- Preview is a thumbnail, not a candidate video proxy. Repeated explicit
  previews revalidate; no durable preview cache/background replay is claimed.
- There is no automatic orphan deletion or user-facing recovery UI for cleanup
  failures. An explicit owned-file recovery or process restart is required
  before retained in-process reservations are cleared.
- Application code does not emit source IDs/query/body to diagnostics. Deployed
  ASGI/reverse-proxy access-log handling of GET search/cursor values remains an
  environment-level redaction check before use with private library identities.
- No comprehensive hostile-media audit, large-media byte stress, cross-platform
  packaging or independent security review is claimed.

## Resume

VERIFIED / PRESERVATION REVIEW: fourteen explicit source/test/document files
pass staged diff checks and limited added-line secret/private-path heuristics.
The four preexisting debug directories, fixture bytes and runtime media are
not staged. This is scoped self-review, not an independent audit or a
comprehensive secret scanner.

VERIFIED / REMOTE READ: before preservation, remote branch SHA matched
`5923d55`; `gh pr list --head codex/wb1-baseline-20260918 --state open`
returned no PRs. The three inspected workflow files do not trigger for this
dedicated development-branch push. Commit/push is authorized only on that
branch, with no release/tag/merge/dispatch. Verify the report-containing commit
against the remote SHA when resuming.

Run `git status --short --branch` in the WB-1 worktree, verify the
report-containing commit against the remote branch, then read `STATUS.md`.
Retain the four preexisting `tmp-debug-media*` directories untouched/unstaged.
Assess the W1-2 handoff and remaining acceptance evidence before starting the
W1-3 project-store task packet. Keep provider work deferred.
