# Current Project Status

**Last updated:** 2026-07-18
**Current branch:** `codex/phase3-private-network` (Phase 3 connection-state Loop 1)
**Current phase:** Phase 3 Private Network Automation — **Local workflow corrected; runtime acceptance pending**

## Current Development Snapshot

- `VERIFIED 2026-07-18`: Phase 3 connection-state Loop 1 separates deployed
  service state from private-network completion. Restoring a historical
  completed deployment now resumes at network selection instead of marking the
  GenBox private URL complete or forcing the final step.
- `VERIFIED 2026-07-18`: SSH actions now fail closed unless the VPS target is
  saved and exactly one session credential is present. SSH testing and network
  connection creation are single-flight; stale SSH responses cannot verify a
  changed target or credential.
- `VERIFIED 2026-07-18`: confirmed public SSH host fingerprints are written
  back to target metadata without saving SSH or sudo credentials. A restored
  Phase 3 flow may therefore re-enter a session credential and start the
  network task directly; a separate SSH test is required only when the host
  fingerprint is missing or changed.
- `VERIFIED 2026-07-18`: one-time managed-service delivery cannot be consumed in
  a hidden pane. An unclaimed key opens the visible delivery pane first and is
  claimed at most once; an already-claimed historical deployment resumes at
  network selection.
- `VERIFIED 2026-07-18`: Loop 1 focused regression passed (`103 passed`), full
  suite passed (`191 passed`), JavaScript syntax checks, Python compilation,
  and `git diff --check` passed. Independent UX, security, and test reviews
  initially blocked three race/delivery/model-validation gaps; all three were
  corrected before this verification.

- `VERIFIED 2026-07-18`: the isolated `chatgpt2api-dev` test instance was
  deployed successfully. Existing production resources remain outside the
  current mutation scope.
- `VERIFIED 2026-07-18`: local Tailscale is online and the private GenBox entry
  is served on port `8893`. This is local network evidence, not yet the complete
  VPS-to-GenBox application probe required by Phase 3.
- `VERIFIED 2026-07-18`: SSH password and sudo-password inputs now have explicit
  visibility controls, password and public-key modes are mutually exclusive,
  and authentication rejection messages no longer claim that the password is
  necessarily wrong. These changes are committed through `0550d8d`.
- `VERIFIED 2026-07-18`: the VPS sshd journal shows that the user's system
  OpenSSH session was accepted with password authentication. A nearby
  `Connection closed ... [preauth]` record cannot be reliably attributed to the
  credential-bearing GenBox attempt because the host-key probe also opens a
  credential-free SSH connection.
- `UNVERIFIED 2026-07-18`: the exact reason AsyncSSH does not complete password
  authentication remains unknown. No current evidence justifies changing VPS
  SSH policy, enabling keyboard-interactive authentication, or treating the
  password as invalid.
- `VERIFIED 2026-07-18`: a secret-free diagnostic change records
  only whether the host key was verified, AsyncSSH requested the password, and
  the connection was lost during authentication. Focused checks passed
  (`29 passed`), full suite passed (`183 passed`), Python compilation and
  `git diff --check` passed. The diagnostic does not persist credentials,
  usernames, hosts, IPs, fingerprints, or raw AsyncSSH exceptions.

- `VERIFIED 2026-07-16`: v2.5.1 was published under GPL-3.0-only at release
  commit `ae2b174`.
- `VERIFIED 2026-07-17`: Phase 2 catalog-identity Loop 1 is merged through
  commits `445d004`, `c7cce88`, and `5cb1c13`; `chatgpt2api` remains the only
  deployable catalog item.
- `VERIFIED 2026-07-17`: Phase 2 Loop 2 durable task recovery is merged through
  commits `852d1f2`, `ae1796b`, `b7c22bf`, and `306a600`; browser refresh and
  restart interruption behavior remain covered.
- `VERIFIED 2026-07-17`: Phase 2 Loop 3A backend capability enforcement is
  complete. Frozen implementation commit `9effee7` received two independent
  read-only final approvals and was cherry-picked to the current integration
  branch as `30e5e28`.
- `VERIFIED 2026-07-17`: the backend capability registry is the execution source
  of truth. Only the supported `chatgpt2api` Compose combinations can plan or
  deploy; planned or unknown projects and unsupported modes fail closed before
  discovery, task creation, or SSH side effects.
- `VERIFIED 2026-07-17`: main-worktree Loop 3A verification passed: focused
  checks `62 passed`; full suite `160 passed`; Python compilation and
  `git diff --check` passed; the incremental high-confidence secret-pattern scan
  found `0` matches; the repository-local temporary test directories were
  cleaned.
- `VERIFIED 2026-07-17`: Phase 2 Loop 3B structured deployment failure and
  recovery is complete. Frozen implementation `0ce7b4f`, future Store/Repair
  planning `d3fb82f`, and persistence hardening `f01f66c` were integrated on the
  current branch as `291c6fc`, `d70ec59`, and `6fa1728`.
- `VERIFIED 2026-07-17`: API/UI final review approved Loop 3B. Security review
  initially blocked persistence validation, then approved after the corrective
  commit enforced recovery-action state contracts and pre-replace validation.
- `VERIFIED 2026-07-17`: main-worktree Loop 3B verification passed: focused
  checks `78 passed`; full suite `176 passed`; Node syntax checks for
  `static/js/extensions.js` and `static/js/i18n.js`, Python compilation,
  `git diff --check`, and temporary-directory cleanup passed; the incremental
  high-confidence secret-pattern scan found `0` matches.
- `VERIFIED 2026-07-17`: the deployed-service delivery UI gap was fixed in
  frozen commit `0cb7f07` and integrated on the current branch as `1659d50`.
  Independent API/UI and security reviews both approved the correction.
- `VERIFIED 2026-07-17`: Phase 2 local acceptance passed all five Roadmap
  criteria: unique catalog identity, refresh recovery, backend capability
  enforcement, safe delivery/open/copy behavior, and structured sanitized
  failure recovery.
- `VERIFIED 2026-07-17`: final main-worktree checks passed: focused `92 passed`,
  full suite `178 passed`, both extension JavaScript syntax checks, Python
  compilation, `git diff --check`, high-confidence sensitive-pattern scan
  `0` matches, and temporary-directory cleanup.
- `USER-CONFIRMED 2026-07-17`: future Store and Repair Copilot direction is
  captured in `docs/GENBOX-STORE-REPAIR-COPILOT.md` and Roadmap Phases 9-12.
  This planning does not change the priority of the core Phase 3-8 chain and is
  not evidence that Store or AI repair features are implemented.
- `.planning/STATE.md` remains owner-controlled and was not modified, staged,
  discarded, or committed.

## Next Objective

Restart the administrator laboratory on the Loop 1 build. Load the saved VPS.
If its confirmed host fingerprint is present, enter one fresh session credential
and start the Phase 3 private-network check directly from steps 3-4; do not run a
separate SSH test. If the fingerprint is missing, perform exactly one SSH test
to confirm and persist it, then run the network check. Record the sanitized task
stage and VPS-to-GenBox probe result without repeated retries.

## Phase 3 Gate

Phase 3 remote acceptance remains open until the isolated VPS can authenticate
and complete the VPS-to-GenBox HTTP probe. Production remains read-only. The
current diagnostic authorizes no VPS mutation and stores no SSH credential.
