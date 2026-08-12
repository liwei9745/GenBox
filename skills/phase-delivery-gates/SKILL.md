---
name: phase-delivery-gates
description: Audit, plan, document, or review GenBox Phase 6 verified cleanup, Phase 7 sanitized GitHub redeployment, Phase 8 upstream delivery, or Phase 9 service-adapter work. Use when an agent must separate local evidence from external authorization, prepare a safe handoff, update phase status, or decide whether a catalog service may become executable.
---

# Phase Delivery Gates

Use this skill to keep Phase 6 through 9 work evidence-led. Treat the project
contracts as the source of truth and preserve the production read-only boundary.

## Read First

Read, in order:

1. `docs/PRODUCT.md`
2. `docs/ARCHITECTURE.md`
3. `docs/STATUS.md`
4. the active phase in `docs/ROADMAP.md`
5. its topic contracts
6. `docs/PHASE6-9-DELIVERY-GATES.md`

Read `docs/DECISIONS.md` for accepted cleanup, credential, or deployment
decisions. Read `docs/DEVELOPMENT-LIFECYCLE.md` before any sanitization,
redeployment, VPS, release, or upstream work.

## Core Procedure

1. State the exact phase, bounded objective, repository, and environment.
2. Collect code/test evidence before changing a status or completion claim.
3. Label each fact `VERIFIED`, `USER-CONFIRMED`, `EXTERNAL`, or `UNVERIFIED`.
4. Separate a local behavior result from isolated-runtime, clean-redeployment,
   production-non-mutation, and upstream-acceptance evidence.
5. Use `references/phase-6-9-gates.md` to identify missing evidence and one
   safe next action.
6. Update only the owning document: current facts in `STATUS.md`, acceptance
   status in `ROADMAP.md`, durable policy in `DECISIONS.md`, and protocol rules
   in `INTEGRATION.md`.

## Hard Boundaries

- Do not infer authorization from code, tests, a deployment plan, or a prior
  status record.
- Do not access, restart, configure, or mutate a production source instance.
- Do not delete source media unless all sender-side receipt, SHA-256, explicit
  policy, isolated-environment, review, and user-authorization gates pass.
- Do not include secrets, real host identities, user media, prompts, accounts,
  cookies, or unredacted logs in documentation, examples, commits, or status.
- Do not make a catalog entry executable because its metadata or recommendation
  looks complete; require an implemented adapter capability and its dossier.

## Output Shape

For an audit or handoff, report the phase, verified evidence, external or
unverified gates, boundaries respected, files changed, test results, and one
safe resume action. Keep the record concise and dated.
