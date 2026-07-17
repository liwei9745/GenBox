# Phase 3 Development Snapshot — 2026-07-17

## Identity

- Branch: `codex/phase3-private-network`
- Base release record: `dbb6b50`
- GSD model-routing commit: `98713ce`
- Snapshot scope: local Phase 3 security loops only
- Production/VPS state: no VPS command or network enrollment was run

## Completed Locally

- Network connection requests are Tailscale-only; NetBird and Cloudflare are
  rejected server-side until equivalent verification exists.
- Automated Tailnet enrollment is disabled because the current CLI contract
  would expose an auth key in the remote process argument list. Existing,
  manually enrolled isolated VPS instances may be verified.
- The final GenBox route is restricted to the verified Tailscale `100.64/10`
  address and the configured Serve port. Loopback, public, credential-bearing,
  fragmented, and mismatched-port URLs are rejected.
- VPS verification probes the stable `/api/setup/status` application contract
  and validates its field types instead of accepting any successful root page.
- Network task failures include `failed_phase`, `recovery_code`, and
  `recovery_action`, and the active step is marked failed.
- SSH host-key validation now runs in the AsyncSSH handshake before password or
  private-key authentication. Unknown-host probing disables local SSH config,
  default keys, and SSH agent fallback.
- FastAPI validation errors no longer echo invalid request bodies, preventing
  SSH passwords and other credentials from appearing in HTTP 422 responses.
- A project-specific Loop Engineering protocol was added at
  `docs/PHASE3-LOOP-ENGINEERING.md`.

## Verification Evidence

- Focused network/extension/route suite: `39 passed`.
- Full local suite after the route redaction fix: `118 passed`.
- `python -m py_compile` passed for changed Python modules.
- `node --check static/js/extensions.js` passed.
- `git diff --check` passed.
- Independent security reviews found and drove fixes for SSH trust ordering,
  default-key fallback, enrollment-token argv exposure, MagicDNS ambiguity,
  application probing, and validation-response credential echo.

## In Progress / Not Complete

- The frontend still exposes NetBird, Cloudflare, and automatic enrollment even
  though the backend intentionally rejects them.
- The frontend does not yet render `failed_phase` and `recovery_action`.
- `remote_network_detect` needs a user-facing translation key.
- A mismatched-but-present SSH fingerprint deserves a dedicated regression test.
- Network task state remains process-memory-only and is lost on restart.
- No isolated VPS/Tailnet acceptance evidence exists yet.

## Resume Point

Start with UI truthfulness:

1. Keep Tailscale as the only enabled provider.
2. Show NetBird and Cloudflare as disabled/not ready.
3. Make `existing` the only available operation mode and remove enrollment-token
   guidance from the active path.
4. Render the failed phase and recovery action in the network task UI.
5. Add UI/static contract tests, run focused and full suites, and request an
   independent review before committing.

## Protected Local State

`.planning/STATE.md` contains an owner change and was not modified, staged, or
included in this snapshot.
