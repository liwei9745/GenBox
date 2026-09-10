# P4 Server Connector UX Strategy

**Date:** 2026-07-27
**Evidence scope:** This is a local design and implementation strategy. It does
not claim an installed connector, a live VPS, an SSH session, a provider OAuth
connection, or production evidence.

## 1. Product Decision

The beginner-facing default direction is **Server Connector (recommended)**:
an agent installed on the intended server establishes a restricted outbound
connection and carries only approved GenBox intents. It avoids asking a browser
to handle SSH passwords, private keys, terminal output, or arbitrary commands.

The current Phase 4 deployment path remains **SSH (advanced)** and must stay
fully functional. It is the only deploy-capable route until the connector has a
real agent, authenticated transport, enrollment, operation allowlist, and test
evidence. The UI must not select an unavailable connector in a way that blocks
target setup, host confirmation, discovery, safety-plan generation, deployment,
or private-network verification.

## 2. Explicit User Flow

The first screen names the two routes and their real status:

1. **Server Connector (recommended)** is shown first. When unavailable it says
   `In preparation`, explains that no connector or trusted transport is
   installed, and offers no pretend connect or deploy control.
2. **SSH connection (advanced)** is marked `Available now` and has one command:
   `Continue with SSH`.
3. That command focuses the existing first required field or saved-target
   selector. The existing guide then carries the user through one task at a
   time: save the target, confirm its identity, provide a session credential,
   test SSH/deployment access, then continue to discovery and the safety plan.

This separates the product direction from the working path. It removes the
false choice where a beginner could enter a nonfunctional connector flow, and
it does not alter the backend request models or the existing SSH state machine.

## 3. Connector Contract Before Availability

A real connector needs these bounded states. The browser may show a state only
when the backend has evidence for it.

| State | What the user sees | Permitted recovery |
| --- | --- | --- |
| `not-installed` | Connector recommended, not yet installed | Use SSH now or start a future install flow |
| `install-ready` | One-time enrollment prepared | Copy a backend-owned installer only after the target is bound |
| `awaiting-connection` | Waiting for the agent to call back | Wait, cancel, or create a new enrollment after expiry |
| `connected` | Agent identity and version verified | Run a capability check, never a web shell |
| `permission-check` | Checking the requested bounded capability | Wait for the result |
| `ready` | Approved deployment/discovery capability is ready | Continue with the existing safety-plan flow |
| `failed` | A safe, category-level cause | Retry the relevant bounded action |
| `expired` | Enrollment material was discarded | Start over with new one-time material |

Enrollment material, agent identity secrets, raw agent output, SSH passwords,
private keys, pairing responses, and host fingerprints are not browser storage,
URLs, normal logs, task records, screenshots, or Git content. An agent action
must carry a signed intent with a target binding, narrow capability, expiration,
and replay protection. The agent rejects arbitrary shell commands even when the
browser is authenticated.

## 4. Why Not A Web Terminal Or Generic OAuth

An embedded web terminal would turn GenBox into an SSH credential and terminal
output proxy. It would enlarge the attack surface, leak sensitive output into a
browser-visible context, and violate the rule that browser input cannot supply
arbitrary remote commands.

OAuth is provider-specific. It can help identify a selected cloud VM only after
an approved provider integration and does not grant deployment rights on an
arbitrary existing VPS. It therefore cannot replace the connector transport or
the SSH fallback.

## 5. Safety And Mainline Preservation

- Existing SSH host-key verification keeps the canonical algorithm plus
  SHA-256 fingerprint and continues to fail closed on a mismatch.
- The connector entry creates no target, enrollment, credential, network, SSH,
  or remote-operation request in this increment.
- The SSH fallback keeps session credentials transient and reuses the current
  discovery, plan, deployment, recovery, and local-network gates.
- The initial UI work is LOCAL-only. It is not isolated-VPS or production
  validation and must not be presented as such.

## 6. Delivery Sequence

1. Ship the honest route selector and retain the working SSH fallback.
2. Specify and implement local connector enrollment and a test-only local agent
   protocol without any remote access.
3. Add a real authenticated outbound transport and agent identity lifecycle.
4. Implement capability-scoped discovery and deployment adapters.
5. Run local tests, then separately authorized isolated-VPS verification.
6. Only after evidence exists may the UI mark the connector as available or
   make it the deploy-capable default.
