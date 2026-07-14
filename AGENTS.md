# GenBox Agent Instructions

## Project Mission

GenBox is a FastAPI application with a static web UI for AI media generation and
local media management. The current product initiative adds an extension center
that connects GenBox with remote services, beginning with `yukkcat/chatgpt2api`.

The primary integration moves generated images from a remote chatgpt2api host to
the GenBox media library through single-image, batch, and scheduled incremental
pushes. The extension center also provides guided deployment for users who do
not want to read source code or run deployment commands manually.

## Required Reading

Before changing code, read these files in order:

1. `docs/PRODUCT.md`
2. `docs/ARCHITECTURE.md`
3. `docs/STATUS.md`
4. The current phase in `docs/ROADMAP.md`
5. The topic-specific contract referenced by that phase

Use `docs/DECISIONS.md` when a task touches an accepted architecture or security
decision. Use `docs/DEVELOPMENT-LIFECYCLE.md` for any VPS, release, or upstream
work.

## Sources Of Truth

- Product intent and scope: `docs/PRODUCT.md`
- Architecture and repository boundaries: `docs/ARCHITECTURE.md`
- Ordered phases and acceptance criteria: `docs/ROADMAP.md`
- Current verified state and next task: `docs/STATUS.md`
- Accepted technical decisions: `docs/DECISIONS.md`
- Environment and release gates: `docs/DEVELOPMENT-LIFECYCLE.md`
- Cross-project protocol: `docs/INTEGRATION.md`

Files under `.planning/` describe earlier milestones and may be stale. They are
historical input, not the current source of truth when they conflict with the
documents above.

## Fact Discipline

- Do not present a configured IP, port, hostname, container, or credential as a
  live runtime fact without a dated verification command and result.
- Label external facts as `VERIFIED`, `UNVERIFIED`, or `USER-CONFIRMED`.
- Do not describe a design document, UI placeholder, catalog entry, or mocked
  test as a completed end-to-end feature.
- Distinguish GenBox receiver work from chatgpt2api sender work. Completion in
  one repository does not mean the integration is complete.
- Before editing a claim about current progress, compare it with code and tests.

## Environment Safety

- Treat every existing chatgpt2api instance on a VPS as production unless the
  user explicitly identifies it as an isolated development instance.
- Never develop inside, replace, restart, migrate, or reconfigure a production
  instance as part of feature development.
- Production containers, Compose files, configuration, and data are read-only
  sources for discovery and approved copying.
- Create an isolated development clone before remote development. It must use a
  separate directory, data volume, port, container name, Compose project,
  management key, Push source ID, and Push key.
- Source-image deletion is disabled in development and disabled by default in
  production.
- Do not run a destructive remote command unless the exact target, ownership,
  backup, rollback, and user authorization have been verified.

## Security Rules

- Never commit or document real passwords, API keys, tokens, cookies, private
  keys, user images, prompts, account data, or unredacted logs.
- Secrets must never enter URLs, Git, normal logs, task status, generated
  examples, or screenshots.
- A managed instance secret (for example a deployment management key) is
  delivered once. Its default handling is show-once-and-rotate: it is not
  persisted by GenBox, and a lost key is recovered by rotation, not by storage.
- The user may opt in to saving a managed instance secret locally so it can be
  viewed again later. Local saving is off by default, requires an explicit
  per-secret user choice, and must clearly warn the user before enabling it.
  Even when enabled, this applies to managed instance secrets and VPS SSH
  credentials the user explicitly chooses to keep; enrollment tokens, Push
  keys, and the GenBox administrator key are never saved to browser storage.
- Whether a secret is shown once or saved locally is a user decision, not a
  hardcoded product rule.
- Keep the GenBox administrator key separate from per-source Push keys.
- Require SSH host-key verification. Do not disable host verification as a
  convenience.
- Browser requests must not supply arbitrary remote shell commands.
- A source image may be deleted only after an authenticated success receipt,
  matching SHA-256, `safe_to_delete_source=true`, and explicit user opt-in.

## Development Workflow

1. Confirm the current phase and objective in `docs/STATUS.md`.
2. Inspect existing code and tests before proposing a new abstraction.
3. Make the smallest change that satisfies the current acceptance criteria.
4. Add or update tests in proportion to the behavior and risk.
5. Verify locally, then use the isolated VPS development clone when required.
6. Update `docs/STATUS.md` with commands, results, blockers, and resume details.
7. Update `docs/ROADMAP.md` only when acceptance evidence justifies a status
   change. Record durable decisions in `docs/DECISIONS.md`.

Keep one primary objective in progress. Do not start a later phase to avoid an
unresolved acceptance criterion in the current phase.

## Completion And Release Gates

A cross-project feature is not complete until:

1. Relevant local tests pass.
2. It passes on an isolated VPS development clone.
3. The production chatgpt2api instance remains unchanged.
4. Code and artifacts pass secret and personal-data review.
5. Sanitized code is pushed to the project owner's GitHub repository.
6. A clean deployment created only from that repository passes verification.

Only after all six gates may an upstream PR or extension proposal be prepared.
Follow `docs/DEVELOPMENT-LIFECYCLE.md` and record evidence in `docs/STATUS.md`.

## Documentation Maintenance

- Keep `docs/STATUS.md` concise and current; replace stale state instead of
  appending an unlimited session history.
- Put product intent in `PRODUCT.md`, architecture in `ARCHITECTURE.md`, phases
  in `ROADMAP.md`, and durable choices in `DECISIONS.md`.
- Do not copy transient IP addresses or secrets into stable documents.
- End each substantial task with explicit resume instructions for the next
  agent or session.
