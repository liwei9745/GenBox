# GenBox v2.6.0-rc.5

> Final testing candidate for local evaluation. This is not a stable release.

## Candidate Status

rc.5 supersedes rc.4. It is the v2.6.0 candidate intended for this local test
pass; no stable tag, formal Release, remote deployment, or cleanup execution is
implied.

## Push Key Safety

- The Chinese Push Key hints have been clarified, and stale browser cache/state
  handling is fixed so a delayed older request cannot erase a newly created or
  rotated key state.
- A new Push Key is available only immediately after creation or rotation.
- Push Keys are not saved locally by default. Local encrypted-vault saving
  remains pending until the user explicitly opts in and confirms the current
  key.
- Cleanup remains disabled. Push receipts grant no permission to delete a
  source file.

## Scope

- This candidate contains UAT fixes, version material, and necessary tests; it
  does not add product features.
- No stable tag, production release, or cleanup execution is implied.
