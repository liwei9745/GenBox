# GenBox v2.6.0-rc.7

> Final testing candidate for local evaluation. This is not a stable release.

## Candidate Status

rc.7 replaces rc.6 for renewed local manual evaluation. No stable tag, formal
Release, remote deployment, or cleanup execution is implied.

## Local Credential Window

- Each sensitive field has its own Show/Hide control; using one affects only
  that field.
- SSH private keys are masked by default. Showing a key makes it editable, and
  hiding it masks it again.
- The credential window stays within the viewport and scrolls internally, so
  Cancel, Delete, and Save remain usable with long credentials and on small
  screens.

## Push Key And Cleanup Safety

- Push Keys are not saved locally by default.
- A Push Key is saved only after the user explicitly confirms the choice and
  unlocks the local encrypted vault.
- Unless cleanup is explicitly enabled, receipts do not authorize deletion of
  source files.

## Scope

- This candidate contains the credential-window UI repair, necessary tests,
  and version material only; it does not add product features.
- No stable tag, production release, remote deployment, or cleanup execution is
  implied.
