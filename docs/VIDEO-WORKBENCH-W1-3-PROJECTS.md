# W1-3 Durable Project Backend

Date: 2026-09-19 UTC. Baseline: `c012133`.
Branch: `codex/wb1-baseline-20260918`.
Status: backend locally verified, full regression passed and scoped review complete.
Full WB-1/browser/platform acceptance remains open.

## Entry And Scope

USER-CONFIRMED: continue the next development stage and the recommended bounded
collaboration. The preserved W1-2 checkpoint has 230 workbench / 2071 full-suite
tests. Stable managed asset IDs, ownership checks, digests and exact library
registration are sufficient dependencies for the ready W1-3 packet.

This is a backend dependency handoff, not a declaration that all W1-2/WB-1
acceptance is complete. Picker/browser journeys stay at W1-4, independent
integrated review at W1-5, and physical limit stress, broader hostile-media,
deployment access-log review and packaged runtimes retain their recorded gates.
No failed backend criterion is waived to start project persistence.

Requirements: VW-01/03/04/11; VA-01 and project portions of VA-12/13.
Use core contract 0.2 and shared fixture/DTO contract 0.3 without schema changes.
No UI, timeline operations, relink, export, provider/paid calls, source deletion,
dependency installation, production, service restart, tags or release.

## Concrete Operations

All routes inherit the configured workbench admin key and mutation CSRF checks.
No query parameters are accepted. Successful responses are `private, no-store`.

- `POST /api/video-workbench/projects`: exact JSON keys `title`,
  `output_profile`; return the frozen project view at revision 1 (HTTP 201).
- `GET /api/video-workbench/projects/{project_id}`: return the stored schema-1
  snapshot. No implicit source import, migration, re-probe or substitution.
- `PUT /api/video-workbench/projects/{project_id}`: exact keys
  `expected_revision`, `document`; return the frozen project view at the next
  revision. A stale expected/document revision returns `conflict` (409).

The create body is at most 4096 bytes. Save transport is bounded to 4 MiB plus
1024 bytes for the envelope; the serialized project itself remains at most
the frozen 4 MiB. Reject duplicate keys, nonfinite numbers, unknown fields and
unknown schema versions rather than normalizing them away.

Server-generated project IDs are `prj_` plus 32 lowercase hex characters.
The server owns revision and timestamps; a save must preserve the loaded
project ID, revision, creation and update timestamps. Revision advances by one
only after atomic publication. Title is trimmed, nonempty, at most 200 Unicode
characters, with no controls or invalid surrogates.
Only the two exact frozen profile objects are accepted: 1920x1080 or 1080x1920,
30/1 FPS, `contain`, and their matching profile IDs.

The W1-3 project shell has the exact `trk_picture`/`picture` and
`trk_audio`/`audio` tracks with empty `clips`, and empty `candidate_refs`.
Nonempty clips/candidates are explicitly `unsupported_capability` until their
designated phases, not silently dropped. Asset references are unique exact
`asset_id`, `kind`, `digest` triplets; IDs are not paths and digests must use
the frozen `sha256:<64 lowercase hex>` spelling.

New references resolve through `AssetService.asset`, checking ready ownership,
kind and server-computed digest. Existing unchanged triplets can remain when
the source is now missing/changed (`not_found`/`conflict`); a project read or
rename must not destroy those references. Other errors fail closed. The frozen
view gains no synthetic asset-availability fields; clients check the existing
asset endpoint. This does not make missing/changed media usable for processing.

## Atomicity And Recovery

Use the existing process/store lock and serialize project read/save against
publication. Store only the frozen JSON at `projects/{project_id}.json`.
No browser-selected paths, new persistent envelope or unapproved snapshot
directory. Ownership is the existing single administrator workspace.

Write a uniquely issued temporary file in the confined projects directory,
flush/fsync, then atomically replace the target. The prior snapshot survives
failed validation/write/replace. Delete only that issued temporary file, never
unknown neighboring files or originals. Surface sanitized storage/cleanup
errors. A process interruption before replacement leaves the old snapshot and
possibly an unclaimed temporary file, which restart retains.
After replacement, a POSIX directory-sync failure is a non-retryable
`conflict/publish`: reload the committed project rather than blindly replaying
the save. The already published revision remains intact. Windows does not
provide this directory-fsync path; sudden-power-loss durability is not claimed.

Reads validate the stored schema and reject corrupt/unknown-version files
without rewriting, guessing migrations or returning an invented default.
External destruction of the committed snapshot is not automatically repaired;
no backup/undelete capability is promised by this slice.

## Task Ownership

- Project implementer: `video_workbench/projects/` and
  `tests/test_video_workbench_projects.py`; no shared-router/document edits.
  Implement `ProjectStore(asset_service).create(owner, title, output_profile)`,
  `.read(owner, project_id)`, `.save(owner, project_id, expected_revision, document)`.
- Coordinator: `video_workbench/assets.py` store wiring,
  `video_workbench/api.py`, `tests/test_video_workbench_project_api.py`,
  authoritative documents, integration and explicit-file Git preservation.
- Independent reviewer: read the stable implementation/tests; findings only,
  no implementation edits or acceptance self-approval.

Agents share the verified checkout; this is not a separate worktree per Agent.
Disjoint ownership is mandatory. No broad staging, commits by workers, resets,
unknown-file deletion or modification of the four preexisting debug directories.

## Verification And Resume

Use synthetic fixtures and pytest temporary storage only. Cover create/save/
reopen, true concurrent saves, wrong ownership, unknown fields/versions,
malformed JSON, path/reparse guards, missing/changed reference preservation,
new reference integrity, failed write/replace and actual process restart/crash.
Run focused, all-workbench and full regressions, compile/diff and scoped
secret/private-path checks before preserving the dedicated branch.

On resume: verify branch/status/remote SHA, read `STATUS.md` and this packet.
Do not start W1-4 or claim complete WB-1 from backend tests.

## Local Evidence

Coordinator verified the starting commit and remote SHA as
`c012133ccaca8aeb7968cd0d75715cb3868e765a`; the four preexisting debug directories
were left untouched. No fixture manifest or binary was changed.

Implemented storage: strict schema-1 validation, both exact output profiles,
server-owned ID/revision/timestamps, serialized mutation/runtime ownership,
atomic fsynced snapshots, exact temporary-file cleanup and immutable prior
snapshot preservation on pre-publication failure.

Observed tests:

```text
python -m pytest tests/test_video_workbench_wb1_contracts.py -q
3 passed in 1.20s

python -m pytest tests/test_video_workbench_project_api.py -q -W error::pytest.PytestUnhandledThreadExceptionWarning
33 passed in 5.17s

$tests = @(Get-ChildItem -LiteralPath tests -Filter 'test_video_workbench*.py' | Sort-Object Name | ForEach-Object { $_.FullName })
python -m pytest @tests -q -W error::pytest.PytestUnhandledThreadExceptionWarning
381 passed in 81.98s

python -m pytest -q -W error::pytest.PytestUnhandledThreadExceptionWarning
2222 passed in 340.65s
```

The project unit/API modules contain 151 cases. Unit cases cover exact schema,
4-MiB serialization, owner checks, detached drafts, ID collision, supplied
asset kind/digest, retained missing/changed references, unknown schema/data,
write/fsync/replace/cleanup faults, post-publication uncertainty, concurrent
save/read/close, second-store ownership, reparse/hardlink and replaced-temp
protection. API cases include real synthetic media registration, authentication/
CSRF, malformed JSON, concurrency and actual child-process exits immediately
before and after replacement. They verify old or new complete snapshots,
retained unknown files and successful explicit saving after restart.

Compiler and diff checks pass. Unit-injected POSIX directory-sync failure is
not actual POSIX runtime verification.

## Independent Scoped Review

The separate read-only reviewer inspected the final schema/store, shared route
and asset wiring, and both project test modules against this packet and frozen
contracts. No actionable findings remained. The reviewer verified the
coordinator-identified post-replacement sync fix in actual source and tests,
not solely from the implementer's summary.

Reviewer command:

```text
python -m pytest tests/test_video_workbench_projects.py tests/test_video_workbench_project_api.py tests/test_video_workbench_wb1_contracts.py -q -W error::pytest.PytestUnhandledThreadExceptionWarning
154 passed in 6.97s (no skips)
git diff --check
PASS
```

Review limits: Windows synthetic-local evidence. Reparse tests simulate file
attributes; native POSIX directory sync and actual cross-platform link behavior
are unverified. Process-crash checks do not prove power-loss durability.
This is a W1-3 code check, not W1-5 integrated browser/media acceptance or a
penetration test. No reviewer source changes, commits or external actions.

## Preservation And Next Packet

VERIFIED / LOCAL: sixteen explicit source/test/document files pass staged diff
checks and limited added-line secret/private-path heuristics. This is not a
comprehensive secret-scanner claim. No runtime media, fixture binaries or
existing debug directories are staged.

VERIFIED / REMOTE READ: the branch still matched starting commit `c012133`
before preservation. There is no open branch PR. The three inspected build/
Docker/PR workflow definitions do not trigger on this dedicated branch push.
Preserve only this development branch, with no merge/tag/release/dispatch.
On resume verify the report-containing commit against the remote SHA.

The next packet is W1-4 UI, consuming real import/library/asset/project routes
and the frozen UX baseline. It must verify file-picker/drop, lazy previews,
missing-reference state, save conflict, refresh/reopen, keyboard/focus and
the four specified viewports. Project listing and relink must not be invented
as available APIs; any additional public shape needs its own contract decision.
Timeline editing remains WB-2, online adapters WB-3, and packaged acceptance
WB-4. Do not mark full WB-1 complete from this backend checkpoint.
