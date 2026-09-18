# Video Workbench WB-1 Implementation Plan

Date: 2026-09-18 (UTC). Revision: 0.4.
Status: **W1-0/W1-1 complete; W1-2 first media/API gate locally verified; remaining media work pending.**

This plan turns the frozen WB-0 contracts into an executable implementation
strategy for the first vertical slice. It is subordinate to
[PRODUCT](PRODUCT.md), [ARCHITECTURE](ARCHITECTURE.md), [STATUS](STATUS.md),
[ROADMAP](ROADMAP.md), [PRD](VIDEO-WORKBENCH-PRD.md),
[core contract](VIDEO-WORKBENCH-CONTRACT.md), [UX baseline](VIDEO-WORKBENCH-UX.md),
[acceptance matrix](VIDEO-WORKBENCH-ACCEPTANCE.md), and the
[Agent protocol](VIDEO-WORKBENCH-TEAM.md). Bounded unattended execution is
defined by [the autonomous execution protocol](VIDEO-WORKBENCH-AUTONOMOUS-EXECUTION.md).

## 1. Goal

Deliver the local-first asset and durable-project slice:

```text
empty workbench
  -> import external image/video/audio OR choose an exact GenBox library item
  -> validate, hash, probe and publish a managed asset
  -> place asset references in a minimal project
  -> save atomically with optimistic revision checks
  -> refresh/restart and reopen the same project
```

The slice must be useful without an AI key or online provider. It proves that
GenBox can safely own media references and project state before local editing
or cloud editing is attempted.

## 2. Requirements And Gates

Primary requirements: `VW-01`, `VW-02`, `VW-03`, `VW-04`, `VW-10` and `VW-11`.

Primary acceptance cases:

| Case | Evidence required in WB-1 |
| --- | --- |
| VA-01 | Create/read/save/reopen, restart restore, stale revision conflict and invalid-schema preservation |
| VA-02 | External image/video/audio import, bounded bytes, duplicate/interrupted upload safety and unchanged originals |
| VA-03 | Exact-ID library registration, paginated search and lazy thumbnail loading |
| VA-04 | Codec, rotation, VFR, silent, corrupt, oversize, playlist, probe-timeout and disk-full fixtures |
| VA-12 | Local cancellation, confined cleanup, input leases and no destructive source deletion |
| VA-13 | Auth/CSRF, ownership, path/reparse escape, hostile media and secret-redaction checks |
| VA-15 | Keyboard path, focus restoration, responsive shell and truthful save/progress state |
| VA-20 | Reproducible warm-open and media-browser measurements on fixed synthetic fixtures |

WB-1 does not pass any online-editing case. `VA-08` through `VA-11`,
`VA-17` through `VA-19`, and provider-specific UI remain WB-3 work.

## 3. Explicit Non-Goals

- No trim, split, reorder, duplicate, undo/redo or final export behavior.
- No online upload, paid request, provider adapter, model selector or preset.
- No source-video editing, Omni qualification or live provider test.
- No arbitrary URL, watched-folder, directory-crawl or cloud-drive import.
- No replacement of existing generation routes, global task stores or gallery
  semantics.
- No new frontend framework or component library solely to copy a demo.
- No packaging or codec redistribution claim; those remain WB-4 gates.

The UI may show a project shell and asset placement targets, but controls for
deferred operations must be absent or clearly unavailable rather than mocked as
working.

## 4. Frozen Technical Boundary

Use the WB-0 revision 0.2 values without silently broadening them:

- FFmpeg/ffprobe are external workers invoked with argument arrays.
- Accepted input: PNG/JPEG/WebP, MP4/H.264 with optional AAC, WebM/VP9
  input-only, WAV/PCM and MP3.
- One video/audio asset is at most 512 MiB; one still is at most 64 MiB.
- One request is at most 10 files and 1 GiB total.
- Video dimensions are at most 1920x1080; stills are at most 4096x4096.
- At most one video stream, one audio stream, two audio channels and 96 kHz.
- Reject playlists, archives, embedded network references, arbitrary URLs and
  unknown codecs.
- Use opaque server-owned asset/project IDs, integer microseconds and rational
  source time bases.
- Use atomic publication, optimistic project revisions and confined staging
  cleanup.
- Expose only bounded metadata and authenticated local media handles.

If implementation evidence requires changing a value, stop and produce a
contract revision with fixture evidence and acceptance impact before coding
continues.

## 5. Execution Waves

### W1-0: Baseline And Branch

Coordinator records the exact latest `origin/master` commit, confirms the
v2.6.12 regression baseline, and creates a clean `codex/` implementation
branch. The conflicting documentation PR is not used as the implementation
base. Existing user-created untracked files remain untouched.

Exit evidence:

- baseline commit and test command recorded in the task ledger;
- clean implementation branch is based on latest `origin/master`;
- no production endpoint, private media or paid provider is involved.

### W1-1: Shared Fixtures And Interfaces

Coordinator freezes fixture names, content digests, public DTOs and error codes.
Media and project workers may then proceed in parallel against those fixtures.

Deliverables:

- synthetic fixture manifest with provenance and SHA-256;
- asset/project/job DTO examples derived from the core contract;
- route error mapping and ownership/auth test matrix;
- a small contract-test harness that does not require FFmpeg network access.

Exit evidence: both backend packets can run their tests against the same
fixtures without editing shared schemas.

### W1-2: Media Asset Vertical Slice

The media worker implements staging, admission, hashing, probing, metadata,
thumbnail/proxy jobs, atomic publication, cancellation and cleanup. Library
registration uses exact existing GenBox identity and rechecks content before
creating a workbench reference.

Exit evidence:

- VA-02, VA-03, VA-04 and the media portion of VA-12/13 pass;
- originals are unchanged and all published paths remain confined;
- missing FFmpeg, disk-full, corrupt input and interrupted worker states are
  actionable and sanitized.

### W1-3: Durable Project Vertical Slice

The project worker implements project create/read/save, schema validation,
expected-revision conflicts, restart restore, missing-asset references and
atomic snapshots. It consumes asset IDs and never accepts browser paths.

Exit evidence:

- VA-01 passes across refresh and process restart;
- stale saves cannot overwrite a newer revision;
- invalid schema or failed migration preserves the last valid snapshot;
- project JSON contains no credentials, absolute paths or raw provider data.

### W1-4: Workbench UI Slice

The UI worker connects the frozen local flow to real routes:

```text
empty -> import/library picker -> validation -> asset list
      -> project placement -> save state -> refresh/restart restore
```

The shell follows the preview-first UX baseline: asset browser, bounded
preview/project area, inspector, and a minimal placement surface. It uses
synthetic fixtures for browser tests and keeps online editing controls absent.

Exit evidence:

- VA-03 and VA-15 browser journeys pass at 1440x900, 1114x994, 1024x768 and
  390x844;
- keyboard alternatives, focus restoration, loading, empty, missing and
  error states are covered;
- no panel overlap, unbounded Base64 gallery or fabricated job progress.

### W1-5: Independent Review And Integration

The reviewer checks the integrated commit, not worker summaries. The
coordinator reruns the media, project, UI and existing generation regressions,
then updates the authoritative ledger.

Exit evidence:

- VA-01 through VA-04, applicable VA-12/13/15/20 are individually marked
  `PASS`, `FAIL` or `NOT RUN` with exact commands and runtime identity;
- no critical data-loss, auth, path-escape, secret-leakage or corrupt-output
  issue remains open;
- `docs/STATUS.md`, `docs/ROADMAP.md` and this plan reflect the same result.

## 6. Task Packets And Ownership

The coordinator sends each packet with the full fields required by
`VIDEO-WORKBENCH-TEAM.md`. The packets below are ready to dispatch after W1-0
and W1-1 are accepted.

| Packet | Owner | Dependencies | Owned paths | Must not edit |
| --- | --- | --- | --- | --- |
| WB1-MEDIA | Media engineer | W1-1 fixture/DTO freeze | `video_workbench/media/`, media tests and fixture helpers | Provider transport, shared `main.py`, global CSS, project schema |
| WB1-PROJECT | Project-storage implementer with coordinator | W1-1 asset DTO and schema freeze | `video_workbench/projects/`, project tests | Media codecs, provider calls, unrelated task stores |
| WB1-UI | Frontend implementer | route DTOs, fixture server, UX baseline | isolated workbench JS/CSS and browser tests | Global styles, provider controls, schema changes |
| WB1-REVIEW | Independent reviewer | integrated checkpoint from W1-2 through W1-4 | read-only review report and evidence ledger | implementation edits, release actions and acceptance self-approval |

The coordinator owns `main.py`, `static/index.html`, shared route registration,
global styles, authoritative documents, release files and final commits.
Workers are not alone in the checkout and must not revert unrelated user
changes or stage broad file sets.

## 7. Verification Loop

Every packet follows:

1. **Ready:** dependencies and owned paths are recorded.
2. **Running:** worker reports commands, fixtures and changed files.
3. **Review:** coordinator checks contract deltas and reviewer checks behavior.
4. **Needs revision:** failed evidence returns to the same packet; after two
   failed cycles, revisit decomposition instead of waiving the defect.
5. **Integrated:** coordinator runs cross-packet tests.
6. **Accepted:** only observed evidence changes the phase ledger.

Minimum local checks before integration:

```powershell
python -m pytest <targeted tests> -q
python -m py_compile <changed Python files>
node --check <changed JavaScript files>
git diff --check
```

Browser tests must use synthetic fixtures and record viewport, browser,
runtime identity and screenshot limitations. Full regression is required after
integration because the workbench shares GenBox authentication and library
boundaries.

## 8. Risks And Stop Conditions

Stop and return to the coordinator when:

- an API needs a new schema field or limit not present in the frozen contract;
- a library lookup cannot prove exact identity and content digest;
- a worker needs arbitrary shell, public media URLs or unbounded resource use;
- a task would mutate an original source or delete media;
- FFmpeg behavior differs across targets in a way that changes the promise;
- UI work requires provider-specific controls before WB-3;
- a test would upload private media or make a paid request.

Known risks are handled by the later gates, not hidden:

- packaged codec availability and licensing remain WB-4 work;
- exact browser playback of WebM/VP9 remains input-only until measured;
- remote GenBox import latency is reported as transfer progress, not local
  processing progress;
- project placement is a shell in WB-1; editing semantics belong to WB-2.

## 9. WB-1 Exit Gate

WB-1 may advance to WB-2 only when all of the following are recorded:

1. External and exact-library asset journeys pass with synthetic fixtures.
2. Projects survive refresh/restart and stale saves fail closed.
3. Originals, credentials, paths and untrusted provider identifiers remain
   protected.
4. Import, probe, thumbnail/proxy and cleanup failures are bounded and
   observable.
5. Four viewport browser evidence and keyboard paths pass.
6. Existing generation/provider regression tests still pass.
7. Independent review signs the evidence ledger.
8. `STATUS.md` and `ROADMAP.md` are updated by the coordinator.

Passing this gate authorizes WB-2 local editing only. It does not authorize
online provider work, real video edits or a release.

## 10. Current Execution State

W1-0 and W1-1 are complete on the isolated branch
`codex/wb1-baseline-20260918`, based on `origin/master` at `02ce25e`.
The shared fixture/DTO/error/auth packet is recorded in
[VIDEO-WORKBENCH-WB1-FIXTURES.md](VIDEO-WORKBENCH-WB1-FIXTURES.md).
The media module and authenticated asset router are implemented. See
[W1-2 integration evidence](VIDEO-WORKBENCH-W1-2-INTEGRATION.md).
Project persistence, proxy/cancellation workflows, UI and independent review
remain outstanding. The single administrator owns the current workspace;
this implementation does not introduce multi-user tenancy.

## 11. Immediate Next Action

Preserve the locally verified integration checkpoint, then continue the
remaining W1-2 media gates: proxy handling, cancellation and
lease/recovery behavior, large-library performance and a browser-ready picker.
Do not start W1-3/W1-4 merely to bypass those acceptance gaps. The coordinator
has approval for the narrow new-router wiring; this does not authorize changes
to existing Provider transports, authentication semantics elsewhere, frozen
DTOs, production or release operations.
