# GenBox v2.6.4 - Packaged Startup and Quantity Fixes

## Included

- Packaged Windows first-run setup and startup summaries show bilingual
  Chinese/English guidance with UTF-8 output.
- Image generation uses the visible quantity control instead of stale cached
  per-model values.
- Invalid or out-of-range image quantities fail safe to one through ten.

## Security and Limits

- No production VPS, upstream repository, or remote deployment was changed.
- This release does not claim browser generation or clean-deployment acceptance.

## Verification

- Full local regression suite: `700 passed`.
- Startup/provider/release/setup focused suite: `57 passed`.
- JavaScript syntax, Python compilation, and `git diff --check` passed.
