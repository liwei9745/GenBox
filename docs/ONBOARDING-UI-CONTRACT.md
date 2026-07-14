# Bilingual Onboarding And Shared Heading UI Contract

**Status:** Approved plan for the next development session
**Recorded:** 2026-07-14
**Implementation state:** Planned refinement of an existing local implementation

## Purpose

Define the next iteration of GenBox's shared page-heading system and bilingual
onboarding experience. The result should explain GenBox's creative value,
introduce the chatgpt2api integration accurately, and feel consistent with the
rest of the application.

This document is a design and acceptance contract. It does not mark the next
iteration as implemented.

## Current Baseline

The current code already provides:

- Fixed-key `zh-CN` and `en` translations.
- A full-screen onboarding surface rendered by `setupWizardMarkupV2()`.
- A language selector that can reopen onboarding after a language reload.
- A Provider summary sourced from current model configuration.
- A chatgpt2api onboarding band.
- A five-step post-onboarding navigation tour.
- Shared page-heading rules for Dashboard, Images, Video, Media Library, and History.

The next iteration changes information architecture, copy, logo usage, and
visual rhythm. It must preserve the working bilingual and navigation behavior.

## Design Language

- Flat operational UI with restrained glass surfaces.
- Apple-inspired clarity: strong hierarchy, quiet borders, controlled shadows,
  generous whitespace, and predictable controls.
- Technical character comes from precise spacing, monoline icons, compact
  product-area labels, and clear status language rather than decorative effects.
- Avoid nested cards, marketing-style hero composition, decorative gradients,
  or asymmetric containers that do not support a workflow.
- Use shared design tokens and existing component classes before adding new values.

## Shared Page Heading

Every primary page uses the same three-line content structure:

1. Product-area kicker, for example `GENBOX IMAGE STUDIO`.
2. Localized page title.
3. Localized supporting description.

Requirements:

- Use a common fixed vertical rhythm across all primary routes.
- Keep left and right content padding equal within each header.
- Use the same title size, line height, kicker size, and description spacing.
- Allow English text to wrap without colliding with page controls or changing
  the visual ownership of the header.
- The icon and text form one heading unit. Do not put the icon in a visually
  separate decorative card.
- Verify Dashboard, Images, Video, Media Library, History, and Extensions.

## Logo Requirement

Onboarding must reuse the established GenBox visual identity from the live app.

- Reuse the exact sidebar logo asset, symbol definition, or shared rendering helper.
- Do not introduce a standalone `GX` monogram or a second logo system.
- The logo must remain recognizable in light/dark themes and at mobile size.

## Onboarding Information Architecture

### 1. Opening

Introduce the shortest route to a successful first creation. Keep the existing
global language behavior and a visible close action.

### 2. Capability Overview

Replace the current Provider-name display with concise product capabilities.
This is an introduction, not a configuration surface.

Present the following groups in clear, compact language:

- **Image creation:** text-to-image, image-to-image, upscale/super-resolution,
  multi-model side-by-side comparison, multi-image generation with one or many models.
- **Planned image editing:** local inpainting must be labeled as in development.
- **Video creation:** text-to-video and image-to-video; describe only capabilities
  supported by current code or label later work accurately.
- **Media organization:** centralized image/video classification, history lookup,
  and prompt viewing or reuse.
- **Prompt assistance:** turn natural-language intent into a more professional prompt.
- **Extension center:** guided service deployment and management without requiring
  users to write deployment commands.

Use a flat capability matrix, rows, or grouped columns. Do not show endpoint
names, URLs, API keys, or hard-coded Provider names in this section.

### 3. chatgpt2api Integration

Create a dedicated full-width region that explains why GenBox and chatgpt2api
work well together.

Copy must distinguish readiness accurately:

#### Available Or Implemented In GenBox

- Guided isolated chatgpt2api deployment and managed-instance UI.
- Private-network setup and verification workflows.
- Existing remote Pull synchronization into the media library.
- Authenticated, idempotent GenBox Push receiver foundation.
- Multi-VPS target selection and deployment planning controls where current code supports them.

#### Not Yet Complete End To End

- chatgpt2api sender-side per-generation Push.
- Reliable batch and scheduled incremental Push.
- Verified source cleanup and reclaimed-space reporting.
- Clean GitHub redeployment and upstream delivery gates.

The primary action opens Extensions. Supporting copy may describe the planned
direction, but planned capabilities must never be presented as currently available.

## Interaction Requirements

- Onboarding language selection stays synchronized with the global Dashboard selector.
- Changing language preserves the current route and reopens onboarding when initiated there.
- Closing or completing onboarding may start the existing short navigation tour.
- The persistent Getting Started entry remains available after first run.
- Keyboard focus must enter onboarding and all icon-only controls require accessible labels.
- No secret value is shown, stored, or placed in a URL by onboarding.

## Responsive Requirements

Verify at minimum:

- `1280x720`
- `1033x1074`
- `390x844`

At each size:

- No horizontal overflow.
- Header controls remain visible.
- Long Chinese and English text stays within its container.
- Capability groups become one column when needed.
- Primary actions remain visible without overlapping the footer.
- Logo, title, and language control remain visually connected.

## Bilingual Content Rules

- Every new visible string receives one fixed translation key with `zh-CN` and `en` values in the same change.
- Do not translate model names, user prompts, keys, raw logs, URLs, or user-defined Provider names.
- English and Chinese may use different phrasing lengths while preserving the same meaning and hierarchy.

## Verification Gate

Before this iteration is accepted:

1. `node --check static/js/i18n.js` passes.
2. `node --check static/js/app-all.js` passes.
3. `python -m pytest -q` passes.
4. Chinese and English browser acceptance passes on all required viewports.
5. Shared headings are checked on all primary routes.
6. The onboarding lab is updated to match the live implementation.
7. A secret and personal-data scan finds no sensitive content in changed artifacts.

## Out Of Scope

- Implementing chatgpt2api sender Push.
- Batch or scheduled transfer development.
- Source deletion behavior.
- Production VPS mutation.
- Changing phase status in `docs/ROADMAP.md` without new acceptance evidence.
