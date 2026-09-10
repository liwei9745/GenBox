# GenBox v2.6.0-rc.3

> Final testing candidate for local evaluation. This is not a stable release.

## Candidate Status

rc.3 is the clean replacement for the unsuitable rc.1 and original rc.2
candidates. It is the only v2.6.0 candidate intended for this test pass.

## Push Key Vault Behavior

- Push Keys are not saved locally by default.
- Saving a newly issued Push Key requires an explicit user choice and
  confirmation, after which it is encrypted in the local credential vault.
- A locked vault cannot reveal saved Push Keys.
- Rotation requires fresh confirmation before the new key is saved.
- Deleting the local copy does not affect the remote Push source.

## Scope

- No new feature work is included in this candidate.
- No stable tag or production release is implied.
