# GenBox Documentation Maintenance Map

## Purpose

Keep product documentation useful without turning README or release notes into
an unlimited development diary. Each fact belongs to one document class.

The user-facing navigation hub is [`docs/README.md`](README.md). This file owns
maintenance policy; the hub owns discoverability by audience and task.

## Pinned Documents

These documents are primary entry points and should stay concise, accurate, and
easy to discover.

| Document | Owns | Update trigger |
|---|---|---|
| `README.md` / `README_EN.md` | Product positioning, major current release, installation, documentation links | A user-visible capability, installation path, or stable release changes |
| `docs/PRODUCT.md` | Product goals, users, journeys, scope | Product direction changes |
| `docs/ARCHITECTURE.md` | System boundaries and technical architecture | A durable architecture boundary changes |
| `docs/DECISIONS.md` | Accepted technical and security decisions | Add or supersede an ADR; never silently rewrite history |
| `docs/INTEGRATION.md` | Cross-project protocol contract | GenBox/chatgpt2api protocol changes |
| `docs/DEVELOPMENT-LIFECYCLE.md` | Environment, sanitization, and release gates | Delivery or safety policy changes |

Pinned documents must not contain transient IPs, credentials, task logs, or
unverified environment claims.

## Rolling Development Documents

These documents change as implementation progresses.

| Document | Owns | Maintenance rule |
|---|---|---|
| `docs/STATUS.md` | Verified current state, blockers, commands, resume point | Replace stale state; keep evidence dated and concise |
| `docs/ROADMAP.md` | Phase order, deliverables, acceptance criteria | Change status only when evidence satisfies a gate |
| `HANDOFF.md` | Immediate objective and short resume context | Rewrite at the end of substantial work |
| `CHANGELOG.md` | Version-level changes and `Unreleased` | Add user-visible changes; avoid session-level narration |

## Release-Frozen Documents

`release-notes-vX.Y.Z.md` and `release-notes-vX.Y.Z-zh.md` are immutable after
the corresponding GitHub Release is published, except for factual corrections.
They should contain:

- The release's major user-visible value.
- Installation and upgrade notes.
- Security and compatibility notes.
- Honest available/planned boundaries.
- Verification summary and known limitations.

The root `RELEASE_NOTES.md` is a rolling pointer to the current release
candidate or latest stable release. It may be replaced for each release.

## Topic Contracts

Topic contracts such as `docs/ONBOARDING-UI-CONTRACT.md`,
`docs/extensions-deployment-contract.md`, and
`docs/chatgpt2api-push-integration.md` define acceptance details for one area.
Keep them while the area is active; archive or mark them historical when a
newer contract supersedes them.

## Historical And Generated Material

- `.planning/` is historical project input and does not override `docs/`.
- UI labs and generated reviews are development aids, not completion evidence.
- Raw screenshots, runtime media, logs, local memory, and generated knowledge
  bases must not enter release packages.
- Only sanitized screenshots under `screenshots/sanitized/` may be referenced
  by public documentation.

## Release Documentation Checklist

1. Update the shared version source in `genbox_version.py`.
2. Move completed `CHANGELOG.md` items from `Unreleased` into the version.
3. Create Chinese and English versioned release notes.
4. Update README's highlighted release and available/planned boundaries.
5. Update `docs/STATUS.md` with tests, builds, package hashes, and blockers.
6. Update `HANDOFF.md` with the next primary objective.
7. Run secret, personal-data, link, package-content, and clean-install checks.
8. Freeze versioned release notes after publication.
