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

Phase 5 remains **In Progress**. Two previously open live checks now have
isolated evidence:

- **Mixed batch and failed-only retry (2026-08-01):** A two-image Gallery
  batch ran only on the registered isolated sender. A reversible local-only
  receiver fault allowed one item to reach `already-imported` after one
  attempt while its peer reached a retryable failure after three attempts.
  Source retention remained enabled. After the normal local receiver route
  was restored, only `Retry failed items` was used. The failed peer reached
  `already-imported` after four attempts; the successful peer remained at one
  attempt. This proves the successful peer was not resubmitted, and both
  sender source images remained present.
- **Concurrent schedule lease (2026-08-01):** The weekly schedule was
  temporarily disabled to remove background interference, then restored to
  its prior enabled state after the test. Six concurrent manual scan requests
  were issued from separate authenticated pages of the same isolated sender.
  Three requests displayed `Another automatic Push scan is already running.
  Wait for it to finish.` The other requests completed after the lease was
  available. Final schedule status reported four completed items with zero
  pending and zero failed items, while source retention remained enabled.
  This is direct evidence that an overlapping scan is rejected rather than
  processing the same schedule at the same time.

The remaining live acceptance gap is:

- A newly arriving image inside the configured scan range is discovered after
  an earlier scan has advanced its cursor. The currently retained isolated
  Gallery images have already been recorded by the schedule, so this requires
  a new isolated source image or another approved non-production fixture.

## Current Resume Blocker

The interactive browser session recovered and supplied the evidence above.
The only current blocker is the absence of a new, unrecorded isolated Gallery
image for the late-arrival scan check. Do not create or modify a production
source image to satisfy this test.

## Resume Notes

- Keep the local Tailscale Serve route pointed at the active local GenBox
  receiver on port `8895` through Tailnet port `8893`.
- Use only the registered isolated sender on service port `33010` for further
  Phase 5 checks.
- Generate or otherwise provide one new isolated test image inside the saved
  date bounds. Run a scan once, then introduce the new image without changing
  the range and run the scan again. Record its discovery, Push outcome, source
  retention, and the unchanged production boundary.
- Do not mark Phase 5 complete until the late-arrival check also has direct
  evidence.
