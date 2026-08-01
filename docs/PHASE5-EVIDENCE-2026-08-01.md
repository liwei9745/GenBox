# Phase 5 Isolated Evidence - 2026-08-01

## Scope

This record covers only the registered isolated chatgpt2api development
instance on service port `33010`. The separately registered service on port
`33018` was not selected or modified. No production instance was targeted.

## Sender Release

- Sender commit: `bd91c47` (`fix: resume batch worker after restart`).
- Published amd64 immutable image:
  `ghcr.io/liwei9745/chatgpt2api-genbox-p5@sha256:a3dd34f9550d8a82d54f2518cd0f718f134e4f226cd3b5c5901170eabc0bab08`.
- GitHub Actions amd64 image build: run `30701260233`, completed successfully.
- Local sender verification: `python -m pytest -q` reported `66 passed`.

## Per-Item Batch Receipt Follow-Up

- Sender commit: `ca6f1ba` (`feat: show per-image push batch receipts`).
- The Gallery Push dialog now renders a compact per-item receipt containing
  only the image filename, safe status, and attempt count. It does not render
  a full source path, credentials, headers, prompts, or raw error text.
- Local sender verification after this change: `npm run build` completed and
  `python -m pytest -q` reported `66 passed`.
- GitHub Actions amd64 image build: run `30702231293`, completed successfully.
- The controlled GenBox update flow applied this immutable amd64 image only to
  the registered isolated instance on port `33010`, then reported that its
  health check passed.

The updated digest was
`ghcr.io/liwei9745/chatgpt2api-genbox-p5@sha256:da5c8200b39833e5a9b2c74be72480bc772608711f0543a423fd49d4d18cd77d`.
The registered service on port `33018` was not selected or modified.

## Restart Recovery Evidence

1. The controlled GenBox image-update flow applied the immutable digest only
   to the registered isolated instance and reported a successful health check.
2. A two-image Gallery batch was started with source retention enabled.
3. A temporary local-only receiver delay held the first request while the
   isolated instance was recreated through the same controlled update flow.
   The receiver itself stayed available; the temporary private-route change
   was restored immediately after the test.
4. After the isolated instance health check succeeded, no Gallery retry action
   was used. After the recovery window, the original batch dialog reached two
   `already-imported` outcomes and stated that source images were retained.

This is isolated sender restart/recovery and idempotent receipt evidence. It
does not prove a clean deployment, production behavior, or upstream readiness.

## Remaining Phase 5 Evidence

Phase 5 remains **In Progress**. The remaining live acceptance gaps are:

- A mixed batch with one confirmed successful item and one retryable failed
  item, followed by a failed-only retry that proves the successful peer was
  not submitted again.
- Independent overlapping scheduled scans that visibly demonstrate the worker
  lease rejects or blocks the second scan without duplicate processing.

## Current Resume Blocker

The isolated sender's public root document and all referenced static JavaScript
and CSS assets returned successfully after the update. The available automated
browser session could read the fully loaded Gallery DOM but could not paint or
operate the Gallery selection controls, so it cannot provide honest live mixed
batch evidence. Do not treat this transport/rendering problem as a completed
mixed-batch test. Resume with a working interactive browser session, verify the
new receipt rows, then run the two remaining acceptance checks below.

## Resume Notes

- Keep the local Tailscale Serve route pointed at the active local GenBox
  receiver on port `8895` through Tailnet port `8893`.
- Use only the registered isolated sender on service port `33010` for further
  Phase 5 checks.
- Before the mixed-batch test, confirm the Tailscale Serve route is still
  `8893 -> 127.0.0.1:8895`. Use a reversible local-only receiver-path fault
  after at least one batch receipt has succeeded, restore the route, click
  failed-only retry, and verify the successful receipt's attempt count is
  unchanged.
- Do not mark Phase 5 complete until both remaining live gaps have evidence.
