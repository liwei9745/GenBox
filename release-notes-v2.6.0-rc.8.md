# GenBox v2.6.0-rc.8

> Unified manual-UAT candidate for local evaluation. This is not a stable release.

## Candidate Status

rc.8 replaces rc.7 for one consolidated browser acceptance pass. It does not
create a stable tag, formal Release, remote deployment, or cleanup authority.

## Dock Interaction

- The Dock now has persistent automatic, locked-visible, and locked-hidden modes.
- Automatic reveal responds only within the bottom-center 40% of the viewport.
- Locked-hidden mode blocks hover and reveal-handle activation.

## Push Configuration Experience

- The local-save choice is a clear standard checkbox beside its encrypted-save
  explanation and remains unchecked by default.
- Saving is unavailable without a newly created or rotated Push Key.
- Both configuration copy actions now use real line breaks instead of literal
  `\n` text.
- Saving a new Push Key uses a GenBox-owned confirmation dialog. Canceling does
  not request or consume a server confirmation credential.
- The panel separately reports source configuration, source revocation state, local-copy
  state, and remote authentication. Remote authentication stays `Unverified`
  without real sender evidence; a local source record is never labeled active.
- Saved Push fields in the general credential window are view-and-copy only.
  Creation, rotation, and local saving remain restricted to the dedicated flow.

## Security Boundaries

- Push Keys are not saved by default.
- Saving requires explicit opt-in, a user click in the GenBox confirmation
  dialog, and an unlocked encrypted local vault.
- The server confirmation remains 120 seconds, single-use, and bound to the
  instance, source, and current key hash.
- Unless cleanup is explicitly enabled, receipts do not authorize source-file
  deletion.

## Scope

- This candidate contains only the unified-UAT UI fixes, required tests, and
  version material.
- It does not include a formal Release, tag, VPS operation, remote deployment,
  or cleanup execution.
