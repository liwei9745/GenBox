# GenBox v2.6.5 Release Candidate - Precision Edit V4

Candidate date: 2026-09-03

## Included

- Editable precision annotations with arrow, rectangle, ellipse, brush, eraser,
  and text tools, plus undo/redo-safe editing flows.
- Resize-only expansion for supported precision-edit sizes. Resize-only requests
  omit annotation payload fields; the default exact-size policy remains strict,
  with an explicit `fit_crop` option for eligible near-ratio results.
- Result-version comparison, including transparent result handling on a
  checkerboard surface.
- Local cutout and refine controls, including selection-aware refinement,
  feathering, alpha handling, foreground restore, and stale-response guards.
- A compact cutout-model status and installation framework with progress,
  refresh recovery, cancellation, integrity-failure recovery, and confirmed
  local deletion. Production network download and installation are disabled in
  this candidate.
- User-selectable model visibility. Precision-edit eligibility and aliases use
  explicit provider capability declarations and fail closed when confirmation
  is missing or ambiguous.
- Explicit cancellation and failure states; source/image and provider-output
  MIME consistency checks; compressed-byte and decoded-pixel limits; rejection
  of decompression-bomb warnings or errors before persistence; and sensitive-
  detail redaction in provider-facing error messages.
- Responsive precision-workbench controls for narrow and desktop layouts.

## Acceptance Boundary

- **USER-CONFIRMED 2026-09-02:** the current Precision Edit V4 workflow works
  in the local browser. Automated local tests cover the implementation
  contracts. A real cutout refine POST is not claimed by this acceptance.
- The local cutout adapter runtime is included in the package, but the ONNX
  model file is not bundled. Packaged builds include Python 3.12, NumPy, and
  ONNX Runtime. Production reports network download and installation as
  unsupported because the checkpoint's conversion chain, training-data
  provenance, and commercial-use rights remain **UNVERIFIED**. The browser
  cannot provide a remote URL or local path.
- An operator may manually place the expected model file. It must match the
  fixed size, SHA-256, and MD5 before use. This verifies byte identity only and
  does not establish provenance or usage rights. A future network installer
  remains gated on separate source and authorization approval.
- After installation, GenBox probes the cutout capability again and enables the
  action only when the model state is `ready` and the adapter reports
  `executable=true`.
- Tests cover the disabled production boundary and use local doubles for the
  installer state machine; they do not perform a public model download.
- This evidence is local only. It does not establish VPS, production,
  source-cleanup, remote-deployment, clean-redeployment, or cross-project
  delivery acceptance. Real external provider behavior and output quality can
  vary.

## Packaging

- Docker Compose defaults are pinned to `ghcr.io/liwei9745/genbox:2.6.5`.
- This is a prepared release candidate. No v2.6.5 tag or GitHub Release is
  claimed by these notes.
