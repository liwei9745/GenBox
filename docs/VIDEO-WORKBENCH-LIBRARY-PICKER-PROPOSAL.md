# Library Picker Contract Decision

Date: 2026-09-19 UTC.
Status: **USER-CONFIRMED scope; additive API revision 0.1 frozen for implementation.**

The user approved proceeding on 2026-09-19. This approval is limited to the
candidate boundary below. Implementation/test evidence is recorded separately;
approval is not evidence of a working picker UI.

## Why Approval Is Needed

The current frozen asset DTO describes validated managed assets. A gallery
candidate has not yet passed workbench import/probe and has no managed asset
ID. Treating it as a ready asset would misrepresent validation and ownership.
The old gallery response also includes data deliberately excluded from the
workbench contract.

The unattended protocol requires confirmation before adding a public response
shape. The proposed authorization is limited to a new read-only candidate
listing/preview boundary, with no change to existing asset/job/project DTOs,
authentication, media limits or original-media deletion policy.

## Recommended Boundary

- A dedicated workbench-admin-authenticated, cursor-paginated listing accepts
  bounded `kind`, `query`, `cursor` and `limit`. It enumerates only configured
  local image/video library roots, never arbitrary paths, folders or URLs.
- Candidate fields are limited to exact `library_kind`, `library_item_id`
  and informational `byte_length`. Page metadata uses `next_cursor`.
  A candidate is not a validated asset; no ready state or invented codec/
  duration is returned.
- Query matches the existing exact ID for discovery only. Selecting an item
  still resolves its complete exact identity, never a substring.
- The separate candidate-preview operation uses that same exact identity,
  admin authentication, confined path checks, bounded local validation and
  lazy preview work. It must not expose the original via an unauthenticated
  URL or invoke the old rich metadata scanner.
- Source content identity obtained during preview must be bound to selection;
  registration can use the existing `expected_sha256` field to reject a changed
  source. No client-supplied digest is treated as proof by itself.
- Preview-derived temporary data has explicit ownership/lease/cleanup rules.
  No full-image Base64 collection, automatic source import, hidden native
  processing during listing or source deletion is allowed.
- Existing `POST /library` remains the explicit import/registration action.
  Only that validated result enters the managed-asset/project workflow.
- Real source names/bytes, prompts, EXIF metadata, absolute paths and request data
  never enter diagnostics, public task logs, Git or test artifacts.

The appendix below freezes the additive boundary. Existing asset/job/project
DTOs, error codes and media resource ceilings remain unchanged.

## Additive API Appendix (Revision 0.1)

All routes use `/api/video-workbench` and the existing configured administrator
key, including in development mode. Successful responses are `private, no-store`.

### Candidate discovery

`GET /library/candidates` accepts only unique `kind`, `query`, `cursor`, `limit`
parameters. `kind` is omitted, `image`, or `video`; `query` is an ID substring
(Unicode casefold, at most 128 characters, no controls); `limit` is decimal
1..50, default 20. IDs remain exact and case-sensitive for selection.

Response:

```json
{"items":[{"library_kind":"image","library_item_id":"synthetic","byte_length":123}],"next_cursor":null}
```

Order is ascending `(library_kind, library_item_id)` using Unicode codepoint
order. Cursor is unpadded URL-safe Base64 of compact UTF-8 JSON
`[1,kind_or_null,query,last_kind,last_id]`, bounded to 3072 characters.
Reject malformed cursors and changed kind/query with `invalid_request`.
A cursor is a seek position, never a permission or file handle.

Enumerate only direct, exact lowercase `.png` / `.mp4` regular files in the
configured roots. No metadata parsing, hashes, native workers or asset
publication. Keep at most `limit+1` candidate records in memory. Guard each
request with at most 100,000 directory entries and a two-second enumeration
budget; exhaustion or concurrent directory mutation returns `conflict`,
without a misleading partial page. Missing roots are empty; unsafe roots or
matching symlink/reparse files fail closed. No directory recursion.

Pagination is not a snapshot: deletions disappear; additions before the seek
position require refreshing from page one. Byte length is informational and
never an admission verdict. Selection must resolve and validate again.

### Lazy preview and exact import

`POST /library/preview` takes exactly
`{"library_kind":"image|video","library_item_id":"exact_id"}` in at most
4096 bytes of JSON, with existing mutation Origin/Referer/CSRF checks.
No query parameters. This explicit POST accounts for bounded local decode
work; it does not register an asset or create a durable import job.

On success return a JPEG (maximum 320x180, at most 4 MiB) with
`X-Content-SHA256: sha256:<source digest>` and a generic inline filename.
The digest identifies the source, not the JPEG. No Base64, raw path, source
metadata or public URL. The client fetches with authentication and creates a
short-lived browser object URL, revoking it on replacement/close (W1-4).
No range delivery or video proxy is provided for a candidate.

Preview acquires the existing admission lock and store ownership, copies one
source into a server-issued staging file under existing byte/reservation
limits, validates it through the existing probe/decode and MP4 reference
guards, then derives a thumbnail. The staged input is leased during processing.
Re-resolve and rehash the original before returning; changed content is
`conflict`, missing source is `not_found`. Shutdown/disconnect cancellation
is cooperative through the existing worker cancellation event. Each native
invocation retains its existing deadline; no background replay or retry.

Only exact files created by this operation are cleaned, after leases end.
The bounded JPEG is read into response-owned memory before temporary cleanup,
so delivery needs no filesystem lease. Cleanup failure is `cleanup_pending`,
not success; failed derivative cleanup retains the staged input and reservation
until explicit recovery/restart, rather than silently freeing the allowance.
No managed original/manifest or durable candidate cache is
created. Process-crash/pre-journal leftovers are retained; startup never
guesses ownership or deletes unknown files.

The client explicitly imports through existing `POST /library`, passing this
digest as `expected_sha256` and a fresh request ID. A changed source returns
`conflict`; a digest supplied by a client never replaces server hashing.
Selecting/listing/previewing alone must leave `GET /assets` unchanged.

## Acceptance

Use synthetic mixed image/video directories to prove pagination without
duplicates, exact ID/kind matching, bounded queries, no eager probing or
Base64, authenticated lazy previews, source-change/missing/reparse handling,
redacted responses and no modification of originals. Test the future browser
journey separately at W1-4.

## Safe State If Deferred

Current external import, exact-ID library registration, managed-asset listing
and local proxy jobs remain usable through their existing backend routes.
There is no complete independent workbench UI or unregistered-library picker.
No candidate endpoint is enabled and no frozen DTO is widened.
