# GenBox v2.6.0-rc.1

> Experimental client candidate for local evaluation of the completed GenBox
> and chatgpt2api integration. This is not a stable release.

## Included

- Single-image Push into the GenBox media library.
- Batch Push with retry and idempotent import behavior.
- Scheduled incremental Push with persisted progress and late-image handling.
- Packaged-client updater support for `-rc.N` version ordering.

## Important Limits

- Source-file cleanup remains disabled by default and is not available in this
  candidate.
- Phase 6 security work is not part of this candidate. Unresolved A1, A2, A3,
  A10, and A11 gates still block any stable release or cleanup claim.
- No stable tag or GitHub Release is created for this candidate.

## Evaluation Notes

Use the existing local test and Windows client build procedures. Treat any
remote deployment or production-instance evidence as outside this candidate.
