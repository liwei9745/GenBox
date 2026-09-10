# GenBox v2.6.0-rc.1

> Experimental client candidate for local evaluation of the completed GenBox
> and chatgpt2api integration. This is not a stable release.

## Included

- Single-image Push into the GenBox media library.
- Batch Push with retry and idempotent import behavior.
- Scheduled incremental Push with persisted progress and late-image handling.
- Deployed chatgpt2api instances can reopen their GenBox Push configuration,
  copy it, and keep the newly issued Push key show-once by default. An
  explicit confirmation can save the key, source ID, and URL in the encrypted
  local credential vault; local deletion never changes the remote source.
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
