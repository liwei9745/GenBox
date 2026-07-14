# GenBox Development Handoff

**Updated:** 2026-07-14
**Branch:** `dev`
**Local development port:** `8892`
**Verified test baseline:** `66 passed` on 2026-07-14

## Immediate Objective

Refine the shared page-heading system and bilingual onboarding experience from
the owner-reviewed plan in `docs/ONBOARDING-UI-CONTRACT.md`.

This is still pre-Push UI work. Do not begin chatgpt2api sender, batch Push,
scheduling, or source-cleanup development during this task.

## Current Verified State

- The fixed-key Chinese/English translation module is loaded before the main UI.
- Primary routes and key modals have passed local bilingual browser checks.
- Dashboard language switching updates `?lang=` and preserves the active hash route.
- Image and video prompt cards use the same vertical order: heading, input, full-width action.
- The current onboarding implementation is rendered by `setupWizardMarkupV2()`.
- It currently includes a synchronized language selector, Provider summary,
  chatgpt2api band, and a five-step post-onboarding tab tour.
- Shared page-heading rules live in `static/css/pages.css`, with creator-specific
  adjustments in `static/css/app.css`.
- `python -m pytest -q` passed all 66 tests on 2026-07-14.

## Owner-Approved Next Iteration

1. Make every primary page heading use one balanced three-line rhythm for
   product-area kicker, page title, and supporting description.
2. Replace the onboarding Provider-name strip with a concise capability overview.
3. Rewrite the chatgpt2api section as an attractive integration overview while
   clearly distinguishing available GenBox capabilities from planned Push work.
4. Reuse the established GenBox logo asset or exact sidebar logo definition;
   remove the temporary `GX` mark.
5. Keep the overall visual language flat, restrained, glass-like, and consistent
   with the existing Apple-inspired operational UI.
6. Re-run Chinese and English browser acceptance at desktop and mobile widths.

## Likely Files

- `static/js/app-all.js`
- `static/js/i18n.js`
- `static/css/app.css`
- `static/css/pages.css`
- `static/index.html` only if the shared logo source or static heading markup changes
- `static/onboarding-lab.html` so the lab remains aligned with the live design
- `tests/test_extensions.py` for structural regression markers
- `docs/STATUS.md` after verification

## Required Reading

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. `docs/ARCHITECTURE.md`
4. `docs/STATUS.md`
5. `docs/ROADMAP.md`
6. `docs/ONBOARDING-UI-CONTRACT.md`

## Safety And Scope

- Keep all work local on port `8892`.
- Do not modify, restart, or reconfigure production `chatgpt2api-warp`.
- Do not expose credentials, user prompts, account data, personal media, or raw logs.
- Model names, user prompts, keys, and raw logs remain untranslated.
- Do not describe planned sender Push, batch transfer, scheduling, or cleanup as available.
- Do not update `docs/ROADMAP.md` unless acceptance evidence changes a phase status.

## Verification Commands

```powershell
node --check static/js/i18n.js
node --check static/js/app-all.js
python -m pytest -q
```

Browser acceptance must cover `zh-CN` and `en` on port `8892`, including the
onboarding page and Dashboard, Images, Video, Media Library, History, and
Extensions headings.

## Resume Prompt

> Implement the owner-approved onboarding and shared-heading refinement from
> `docs/ONBOARDING-UI-CONTRACT.md`. Keep work local on port 8892, preserve
> production chatgpt2api-warp, and do not enter the Push phase.
