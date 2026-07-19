# Current Project Status

**Last updated:** 2026-07-19
**Current branch:** `codex/phase3-private-network`
**Current phase:** Phase 4 Single-Image Push End To End — **In Progress**

## Verified Current State

- `VERIFIED 2026-07-19`: Phase 2 local acceptance remains complete, and the
  isolated managed `chatgpt2api-dev` instance is running and presented with
  usable console/API delivery information. The production source remains
  outside the current mutation scope.
- `USER-CONFIRMED 2026-07-19`: the Extension Center completed the guided
  Tailscale flow and displayed `链路已连接`, `VPS 可访问`, a final Tailnet URL,
  and the `PRIVATE LINK READY` success state.
- `VERIFIED 2026-07-19`: `GET
  /api/extensions/network/local/tailscale/status` reported the local client
  installed, online, `Running`, and serving the development GenBox application
  through the separate private-entry port.
- `VERIFIED 2026-07-19`: `GET /api/extensions/targets` showed that the isolated
  target contains a non-loopback, non-public `.ts.net` destination and a fresh
  `network_verified_at` timestamp. The target record contains no enrollment
  token or SSH credential.
- `VERIFIED 2026-07-19`: the final HTTP-probe blocker was caused by discarding
  the Tailscale Serve MagicDNS URL and probing the node's `100.x` address. The
  same Serve returned HTTP 200 through MagicDNS and HTTP 404 through the raw IP.
  The network task now validates, probes, returns, and stores the MagicDNS URL;
  the `100.x` address remains limited to peer identity and reachability checks.
- `VERIFIED 2026-07-19`: the completion panel now updates the value/status cell
  instead of overwriting its label, and a saved `network_url` plus
  `network_verified_at` restores verified display state after target reload.
- `VERIFIED 2026-07-19`: focused network checks passed (`26 passed`); the full
  suite passed (`247 passed`); JavaScript syntax checks, Python compilation, and
  `git diff --check` passed.
- `.planning/STATE.md` remains owner-controlled and was not modified, staged,
  discarded, or committed by this work.

## Phase 2 Result

Phase 2 is complete. The deployment experience has local test/review evidence
and a real isolated managed instance with usable delivery information. This
does not authorize mutation of any production source instance.

## Phase 3 Result

Phase 3 is complete for the Tailscale primary adapter:

- local Tailscale and the separate GenBox Serve entry are verified;
- the isolated VPS is enrolled and has a valid private address;
- peer reachability succeeds;
- the VPS-to-GenBox `/api/setup/status` application probe succeeds;
- the final destination is a validated MagicDNS URL, not loopback, a raw
  public address, or the service console URL;
- enrollment and SSH session secrets are absent from persisted target data;
- failures retain stage-specific, sanitized Chinese diagnostics and recovery
  actions.

NetBird and Cloudflare remain non-executable alternatives and are not part of
this completion claim.

## Next Objective

Begin Phase 4 Loop 1: complete one single-image Push from the isolated
`chatgpt2api-dev` instance into the GenBox media library.

1. Reconfirm the existing GenBox Push v1 receiver contract and source-key
   provisioning without reusing the GenBox administrator key.
2. In the chatgpt2api sender repository/worktree, implement the shared Push
   client and destination status probe using the Phase 3 MagicDNS base URL.
3. Add one per-generation Push action for the isolated development instance.
4. Verify one image imports once with SHA-256 and available metadata; repeat the
   same request to prove idempotency.
5. Confirm every failure path retains the source image. Source deletion remains
   disabled.

## Resume Instructions

1. Do not reinstall Tailscale, generate another Auth Key, or rerun Phase 3
   unless the saved network verification becomes stale or the Tailnet changes.
2. Keep the current private destination as non-secret target metadata. Keep the
   Push key separate from URLs, browser storage, the GenBox administrator key,
   and chatgpt2api management credentials.
3. Use only the isolated `chatgpt2api-dev` instance for Phase 4 development and
   end-to-end testing. Existing production services remain read-only.
4. Before recording Phase 4 success, capture a sanitized receipt, SHA-256,
   metadata result, idempotent retry result, and source-retention evidence.
