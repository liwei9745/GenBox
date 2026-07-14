# Development, Verification, And Upstream Lifecycle

## Purpose

This lifecycle protects an existing chatgpt2api service while developing the
GenBox integration and proves that completed work is reproducible before it is
offered upstream.

## Environment Classification

### Production Source Instance

An existing VPS chatgpt2api deployment. It may contain active accounts,
credentials, images, schedules, and user configuration. It is read-only for
development work.

Allowed operations:

- Host-key verified connection.
- Read-only system and Docker discovery.
- Approved read-only size, path, configuration-shape, and health inspection.
- Copying an explicitly selected data scope into a new destination.

Disallowed operations:

- Editing source files or environment variables.
- Developing inside the running container.
- Restarting, recreating, stopping, upgrading, or relabeling the source.
- Pointing production schedules at a development GenBox endpoint.
- Deleting source media.

### Isolated VPS Development Clone

A disposable but stateful environment for development and integration testing.
It must have unique values for:

- Host directory and data directory.
- Docker volume or bind mount.
- Container and service names.
- Compose project.
- Host port.
- Management key.
- GenBox Push source ID and key.
- Schedule and receipt state.

Inherited Push destinations, receipts, schedules, worker leases, and management
keys must be removed or regenerated before the clone starts.

### Local GenBox Environment

The current code checkout used for implementation, unit tests, and local UI
testing. Runtime secrets and user media remain outside version control.

### Personal GitHub Clean Deployment

A newly created environment built only from sanitized files committed to the
project owner's GitHub repository. It must not reuse the development clone's
source tree or uncommitted edits.

### Upstream Review Environment

The code and documentation submitted to the original chatgpt2api project as
small PRs or a feature proposal after all prior gates pass.

## Stage 1: Read-Only Discovery

1. Confirm the intended VPS and SSH host key.
2. Record the exact source container, Compose project, image, mounts, ports,
   labels, health, and data size.
3. Record destination capacity and port conflicts.
4. Produce a clone plan without executing it.
5. Review every command for source mutation.

Required evidence:

- Timestamped discovery output with secrets removed.
- Source identifiers and pre-clone health.
- Destination directory, port, Compose project, and instance ID.
- Required space calculation.
- Rollback and cleanup target limited to the new destination.

## Stage 2: Create The Development Clone

1. Create only the destination directories and isolated Compose resources.
2. Copy the user-approved scope: blank, media-only, or safe working copy.
3. Remove inherited integration and secret state.
4. Generate development-only credentials.
5. Start the clone and run application health checks.
6. Re-check the production source for non-mutation.

The production source must remain available throughout. A failed clone is
cleaned up only within its owned destination after evidence is captured.

## Stage 3: Implement And Verify

Use the isolated clone for chatgpt2api sender changes and GenBox for receiver and
deployment changes. Verification proceeds from focused tests to end-to-end use:

1. Unit and route tests.
2. Local GenBox UI behavior.
3. Private-network reachability.
4. Single-image Push.
5. Idempotent retry.
6. Batch progress, interruption, and resume.
7. Scheduled incremental scan and worker lease.
8. Cleanup dry run; real cleanup remains disabled until its phase.

Record commands and outcomes in `docs/STATUS.md`. A passing mock test does not
replace live isolation or network evidence.

## Stage 4: Sanitization Gate

Before any public or personal remote push, inspect tracked files, untracked
artifacts, generated bundles, images, logs, configuration, and Git history for:

- VPS IPs, domains, SSH users, private keys, and known-host details.
- Tailscale, NetBird, and Cloudflare enrollment tokens.
- GenBox administrator and Push keys.
- chatgpt2api management keys, cookies, accounts, and tokens.
- Provider API keys.
- Real images, prompts, call logs, JSON/JSONL runtime data, and backups.
- Host-specific mount paths and unredacted inspect output.

Examples use placeholders. Removing a secret from the current file is
insufficient if it remains in Git history or a distributable artifact.

## Stage 5: Personal GitHub And Clean Redeployment

1. Push reviewed, sanitized commits to the project owner's repository.
2. Provision a clean destination.
3. Clone only that repository.
4. Configure it using documented example values and newly generated secrets.
5. Build and deploy without copying the development source tree.
6. Repeat the relevant acceptance matrix.
7. Verify again that the original production source is unchanged.

This gate detects ignored dependencies, manual container edits, missing files,
and environment assumptions.

## Stage 6: Upstream Delivery

Preferred PR sequence:

1. Push configuration, shared service, receipt persistence, and tests.
2. Per-generation option and Gallery batch UI.
3. Scheduler, lease, retry, and optional confirmed cleanup.

When direct code contribution is unsuitable, provide
`docs/UPSTREAM-VIBE-CODING-GUIDE.md` as an implementation-ready proposal.

## Completion Evidence

A feature may be called complete only when the record includes:

- Commit or diff identity.
- Test commands and results.
- Development-clone environment identity without secrets.
- End-to-end request and receipt evidence.
- Production non-mutation checks.
- Sanitization result.
- Personal GitHub commit and clean deployment result.
- Known limitations and rollback path.

## Stop Conditions

Stop remote work and request review when:

- The target or source instance identity is ambiguous.
- A planned command can mutate the production source.
- Clone and source paths, volumes, ports, or Compose identities overlap.
- A secret appears in a command result that would be persisted or committed.
- Rollback cannot be limited to GenBox-owned development resources.
- Production health changes during clone or test work.
