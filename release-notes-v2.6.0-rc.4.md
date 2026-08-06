# GenBox v2.6.0-rc.4

> Final testing candidate for local evaluation. This is not a stable release.

## Candidate Status

rc.4 replaces the blocked rc.3 candidate. It is the v2.6.0 candidate intended
for this manual test pass; no stable tag, formal Release, remote deployment, or
cleanup execution is implied.

## Push Key And Receipt Safety

- Push Keys are not saved locally by default.
- A Push Key can be saved to the local encrypted vault only after the user
  explicitly confirms that choice.
- The server validates a short-lived, one-time confirmation credential bound to
  the instance, source, and current Push Key hash. A browser request cannot
  bypass that validation directly.
- When cleanup has not been explicitly enabled, a Push receipt returns
  `safe_to_delete_source=false` and provides no permission to delete the source.

## Scope

- This candidate contains gate fixes, version material, and necessary tests;
  it does not add product features.
- No stable tag or production release is implied.
