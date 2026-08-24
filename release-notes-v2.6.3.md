# GenBox v2.6.3 - Provider and Store Reliability

## Included

- Provider forms preserve saved credentials without reusing masked placeholders.
- OpenAI-compatible model discovery supports effective multi-key rotation.
- Model discovery no longer overwrites endpoint pools or Provider settings.
- Multi-target Store installed projections remain bound to the Store target.
- Windows launchers set UTF-8 console/Python output and show bilingual startup
  and failure guidance.

## Security and Limits

- Masked or unavailable credentials fail closed and require explicit re-entry.
- No production VPS, upstream repository, or remote deployment is changed by
  this release.

## Verification

- Full local regression suite: `698 passed`.
- Provider/startup/release focused contract suite: `16 passed`.
- JavaScript syntax, Python compilation, and `git diff --check` passed.
