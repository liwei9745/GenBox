# Library Picker Contract Decision

Date: 2026-09-19 UTC.
Status: **PROPOSED; not approved, frozen or implemented.**

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

Before implementation, freeze exact route spelling, cursor encoding and bounds,
candidate JSON, preview/digest transport, stale-selection errors, concurrency/
lease behavior and tests in an additive contract appendix. Existing error codes
and resource ceilings remain unchanged.

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
