# Video Workbench Acceptance Matrix

Date: 2026-09-18 (UTC). Revision: 0.3 (evidence update; case criteria unchanged).
Status: **WB-0 planning gates PASS; W1-2 backend subcases have local evidence; full WB-1-WB-4 cases remain unaccepted.**
No historical generation test result counts as workbench acceptance.

## W1-2 Local Evidence

See [the integration checkpoint](VIDEO-WORKBENCH-W1-2-INTEGRATION.md) for
commands, runtime, fixtures, ownership and limitations. These are subcase
results, not phase acceptance:

| Case | Observed subcase | Result | Still required |
| --- | --- | --- | --- |
| VA-02 | Synthetic external media API, hashes, repeated request and original preservation | PASS locally | File picker/drop UI and complete interrupted-upload recovery |
| VA-03 | Exact library API, changed/missing source rejection, authenticated lazy thumbnails | PASS locally | Library-picker pagination/search journey and performance |
| VA-04 | Existing format fixtures, corruption, disguised playlist, worker deadlines/output and admission faults | PASS locally | Complete rotation/PTS/VFR and stress/disk-full matrix |
| VA-12 | Owned-file cleanup, publication rollback, worker deadline termination | PASS locally | User cancellation, leases and restart cleanup recovery |
| VA-13 | Auth/CSRF, single-workspace ownership, path/reparse guards and bounded errors | PASS locally | Independent integrated review and broader hostile-media coverage |
| VA-01 / VA-15 / VA-16 | Project durability, workbench UI and packaged execution | NOT RUN | Implement and verify at their designated gates |

The old-generation regression suite is compatibility evidence only. No online
Provider acceptance or paid generation was performed.

## WB-0 Preparation Gates

These gates certify preparation artifacts, not product implementation:

| Gate | Expected proof | Result |
| --- | --- | --- |
| WB0-01 Stage goals | G0-G8 ledger and dependency graph in `VIDEO-WORKBENCH-PLAN.md` | PASS |
| WB0-02 Read-only feasibility | W0.2 media, W0.3 provider and W0.4 UX reports; no private upload or paid call | PASS |
| WB0-03 Contract freeze | Core/provider/UX contracts contain first-release scope, schema, limits and error boundary | PASS |
| WB0-04 Acceptance freeze | VA-01 through VA-20 map to phases; WB-0 targets and later live gates remain explicit | PASS |
| WB0-05 Agent protocol | Coordinator ownership, WB1 packets and independent review boundary are recorded | PASS |

The evidence for these gates is the WB-0 document set at commit `44c3f27`
plus the follow-up freeze revision. They do not mark VA-01 through VA-20 as
passed.

## Requirements And Cases

| Case | Requirements | Expected proof | Phase |
| --- | --- | --- | --- |
| VA-01 | VW-01 | Create/save/reopen; restart restores project; stale revisions cannot overwrite; invalid schemas preserve prior snapshot | WB-1, WB-2 |
| VA-02 | VW-02, VW-11 | File picker and drop import image/video/audio; bytes validated; interrupted/duplicate uploads safe; originals unchanged | WB-1 |
| VA-03 | VW-03, VW-04 | Exact-ID library registration; paginated search; lazy thumbnails; no substring substitution or eager Base64 gallery | WB-1 |
| VA-04 | VW-04, VW-11 | Codec/rotation/VFR fixtures, no-audio clip, corrupt file, oversize dimensions, network playlist, probe timeout and disk-full handling | WB-1 |
| VA-05 | VW-05 | Trim/split/reorder/duplicate/delete; still duration; gain/mute; undo/redo; invalid ranges rejected | WB-2 |
| VA-06 | VW-01, VW-04 | Missing source is visible; explicit relink validates content/type/duration; save conflict preserves user draft | WB-2 |
| VA-07 | VW-06 | Mixed-media timeline exports decodable MP4 with expected frames/audio; immutable revision; original hashes unchanged | WB-2 |
| VA-08 | VW-07, VW-11, VW-13 | Capability preflight rejects invalid source/reference roles, model/profile and expired confirmation before any upload/paid call | WB-3 |
| VA-09 | VW-08 | All six presets and free edit produce visible editable intent; conflicting preserve/change fields block submit | WB-3 |
| VA-10 | VW-09 | Linked comparison, retained original/candidate, revision-safe acceptance, mismatch rejection and explicit audio handling | WB-3 |
| VA-11 | VW-10 | Duplicate click, refresh, restart, timeout-after-POST and late results never trigger duplicate paid submissions | WB-3 |
| VA-12 | VW-10, VW-11 | Cancel local work; distinguish upstream unknown; cleanup confined; referenced sources and active leases retained | WB-1 through WB-3 |
| VA-13 | VW-11 | Auth/CSRF, ownership, path/reparse escape, hostile media, SSRF/redirect and secret-redaction tests | Every implementation phase |
| VA-14 | VW-12 | Existing native Google, gateway, provider selection, composer and generation experience regression tests | WB-4 |
| VA-15 | VW-01, VW-05, VW-10 | Responsive workflows, keyboard alternatives, focus, no overlaps, truthful save/progress state | WB-2 through WB-4 |
| VA-16 | VW-12 | Clean packaged runtime: dependencies, codec behavior, import/restore/render on declared supported clients/container | WB-4 |
| VA-17 | VW-07, VW-09 | Explicitly authorized real online video edit, locally playable candidate, user comparison and acceptance | WB-3, WB-4 |
| VA-18 | VW-13 | Two fake adapters with different transport shapes pass the same interface tests; no Google fields in shared UI/project schema | WB-3 |
| VA-19 | VW-11, VW-13 | Provider switch invalidates consent; unsupported options are not dropped; gateway/model listing cannot self-grant editing capability | WB-3 |
| VA-20 | VW-04, VW-05, VW-06 | Reproducible local performance baseline and agreed budgets on fixed fixtures/hardware | WB-0, WB-4 |

## Media Fixture Set

Use generated synthetic fixtures or redistributable fixtures with provenance:
short CFR video with audio, VFR video, portrait/rotation metadata, silent clip,
PNG/JPEG/WebP stills, supported WAV/MP3 audio, mixed sample rates, corrupt
containers and boundary-limit files. These match the frozen WB-1 planning
matrix in the core contract; do not silently expand support.

Record source checksums, duration/time-base metadata and expected rendering
outcomes. Never include user footage, private prompts or real credentials.
AI-quality examples need authorized reference footage separate from fixtures.

## Frozen Measurement Targets (Not Yet Measured)

The frozen test envelope is a two-minute project with
20 picture clips, one audio track and 1080p source media; proxy preview up to
720p. Record OS, CPU, RAM, storage, codec build, browser and cache state.

- Warm project open: usable controls within 2 seconds, excluding full media
  decoding and network provider discovery.
- Warm proxy seek: p95 visible response within 500 ms over 30 seeks.
- Local timeline controls: p95 feedback within 100 ms over 100 actions.
- Export duration: within one project frame; synthetic A/V sync within 50 ms.
- No cumulative drift beyond the chosen tolerance after repeated clip splits.
- Cancellation: acknowledge within 1 second; owned local worker stops within
  5 seconds or reports bounded cleanup-pending state.

WB-1/WB-4 must measure these targets and may revise them only through a
contract change. Record render time and memory, but do not promise real-time
encoding across all machines. Cloud latency is measured separately and is not
included in local-interaction promises.

## Test Layers And Evidence

Unit tests cover schema/timeline math, serializers and capability mapping.
Route tests cover auth, validation, idempotency and safe errors.
Integration tests use actual media processing, storage faults and restart.
Browser tests cover user journeys and viewport screenshots.
Live AI tests require per-attempt authorization; CI only uses mocks/fixtures.

Existing baseline commands (not executed for this documentation change):

```powershell
python -m pytest tests/test_google_native_video.py tests/test_gemini_official_diagnostics.py tests/test_provider_model_categories.py -q
python -m pytest tests/test_google_video_browser.py tests/test_video_composer_browser.py tests/test_generation_experience_browser.py -q
```

New suite names/commands are added only when files exist. Do not report a planned
command as runnable verification. Full regression and release checks follow
DEVELOPMENT-LIFECYCLE.md when WB-4 reaches release preparation.

Each evidence entry names case IDs, code commit, runtime identity, fixture
digests, exact command, result, limitations and reviewer. Screenshots alone do
not prove request correctness, durability, billing behavior or output quality.

## Exit Rules

Use NOT RUN, PASS, FAIL, BLOCKED and NOT APPLICABLE with reason.
Only mark PASS for observed evidence. A conditional feature can be unavailable,
but must not be counted as an accepted requirement.

No open critical data-loss, auth, secret leakage, duplicate-billing or corrupt
output defect may be deferred to declare completion. Mock-only AI behavior is
labelled mock-only. WB-2 can be accepted as a local editing slice while WB-3
remains pending; the whole AI workbench remains incomplete.

Release is a separate gate from local implementation and user acceptance.
Independent review, authorized real edits and packaged-runtime results remain
pending until recorded. Do not update historical extension-phase statuses.
