# P4 Read-Only Discovery Plan

## Purpose

This is the local gate used before an authorized Phase 4 L2 SSH discovery. It
does not connect to a server, read credentials, resolve a host, or change a
remote or local target record. Its only job is to fail closed unless the
authorization, saved host trust, current host-key observation, and requested
operations describe exactly one target.

## Input Contract

`scripts/validate_discovery_plan.py` reads a JSON object from standard input
with exactly these top-level objects:

- `authorization`: literal scope `read-only-discovery`, target role, target
  host/port/user, a non-secret approval-record identifier, and its timestamp.
- `trust`: expected and current observed host/port/host-key algorithm/SHA256
  fingerprint. All corresponding values must match.
- `operations`: non-empty unique operations from the fixed allowlist.

The tool accepts no credential field, arbitrary command text, URLs, shell
syntax, redirection, pipes, parent traversal, or unrecognized operation.
Failure output names only the invalid field. It never echoes target identities,
fingerprints, paths, or input values.

## Fixed Operations

The allowlist is intentionally limited to remote identity, Docker and Compose
versions, Docker and Compose summaries, listener summaries, and bounded
container or filesystem metadata. The authoritative command implementation
remains backend-owned in `extensions/discovery.py`; the browser never supplies
shell text.

## Operator Boundary

An approved plan is an authorization boundary for a single read-only discovery,
not a deployment plan. A later executor must still use strict host-key
verification and the backend-owned operations. It must stop on any target or
host-key mismatch and may not register an instance, overwrite target metadata,
start or stop containers, modify files, copy data, change networking, or read
secrets. Passing this local validator is not VPS evidence.

`POST /api/extensions/discover` creates this request-scoped plan only after it
has re-read the saved target's host key without SSH authentication. A mismatch
stops before credentials are offered to the remote server. The ephemeral
approval identifier and timestamp are discarded after validation; they are not
returned to the browser or written to target, task, log, or instance state.
