# GenBox v2.6.0-rc.6

> Final testing candidate for local evaluation. This is not a stable release.

## Candidate Status

rc.6 replaces rc.5 after the rc.5 manual acceptance click path did not pass.
It is the v2.6.0 candidate for renewed local manual evaluation; no stable tag,
formal Release, remote deployment, or cleanup execution is implied.

## Deployed Push Configuration

- Fixed the `Manage Push configuration` entry on deployed service cards.
- Selecting it now directly displays a visible GenBox Push configuration modal
  bound to the current managed instance.
- Closing the modal, including with Escape, returns to the deployed-services
  drawer instead of navigating to a hidden deployment step.

## Push Key And Cleanup Safety

- Push Keys are not saved locally by default.
- A Push Key is saved only after the user explicitly confirms the choice and
  unlocks the local encrypted vault.
- Unless cleanup is explicitly enabled, receipts do not authorize deletion of
  source files.

## Scope

- This candidate contains the UAT entry repair, version material, and necessary
  tests only; it does not add product features.
- No stable tag, production release, remote deployment, or cleanup execution is
  implied.
