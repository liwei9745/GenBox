# GenBox v2.6.6 - Precision Edit V4 And CI Repairs

Release date: 2026-09-03

## Included

- Editable precision annotations with arrow, rectangle, ellipse, brush, eraser,
  and text tools, plus undo/redo-safe editing flows.
- Resize-only expansion for supported precision-edit sizes. Resize-only requests
  omit annotation payload fields; exact-size output remains the default, with
  explicit `fit_crop` handling for eligible near-ratio results.
- Result-version comparison, transparent-result rendering, local cutout and
  refine controls, selection-aware feathering and foreground restore, and
  responsive narrow/desktop workbench behavior.
- User-selectable model visibility with fail-closed provider capability and
  alias declarations.
- Provider-output MIME, compressed-byte, decoded-pixel, decompression-bomb, and
  sensitive-error-detail protections.

## Desktop Packaging Repair

- The onefile build now packages the complete direct runtime contract rather
  than relying on dynamic imports being discovered automatically. It includes
  Pydantic Settings and its required runtime modules, required Uvicorn
  submodules, native/data collections, and metadata for all 18 pinned direct
  distributions.
- The generated spec and PyInstaller CLI use the same collection lists. The
  packaged runtime smoke imports every contracted module, checks exact pinned
  distribution versions, and verifies critical API symbols.
- Windows, macOS, and Linux empty-directory checks remove `PYTHONPATH` and
  `PYTHONHOME` and set `PYTHONNOUSERSITE=1` before executing the packaged app.
- Passphrase-protected OpenSSH private keys now have an explicit
  `bcrypt==5.0.0` runtime dependency. Desktop and Docker smoke generate a
  synthetic encrypted Ed25519 OpenSSH key and require
  `asyncssh.import_private_key(..., passphrase)` to succeed.
- bcrypt's complete Apache License 2.0 text is included in desktop, Docker
  image, Docker Compose, and source-package license directories. The collector
  supports the verified Windows and Linux wheel metadata layouts while still
  requiring exactly one matching license file.

## Docker Readiness Repair

- The exact-image HTTP smoke uses a bounded readiness loop instead of treating
  the first startup connection reset as a terminal application failure.
- Each attempt verifies container running state and health, then requires the
  production setup-status response. Terminal failures include bounded,
  credential-redacted logs. The workflow still smokes and publishes the exact
  image ID produced by the single build step.
- Docker build and publish permissions are separated. The publish job reloads
  the exact smoke-tested image artifact and verifies its original image ID
  before tagging and pushing, without rebuilding.
- Release workflow actions are pinned to reviewed full commit SHAs. Default
  permissions are read-only; only the Release and package-publish jobs receive
  their narrowly required write permissions.

## Verification And Boundaries

- A fresh local Python 3.12.8/PyInstaller 6.21.0 Windows onefile build produced
  a 67,631,005-byte executable and passed the v2.6.6 empty-directory version,
  all 18 pinned runtime versions, API symbols, encrypted OpenSSH key, and
  packaged-client HTTP smokes.
- A current-source local Docker image passed exact-image runtime, bcrypt
  license, encrypted OpenSSH key, and bounded HTTP readiness smokes.
- Final local verification passed 42 release-packaging tests and 1,302 total
  repository tests, plus the v2.6.6 tag contract, workflow YAML parsing,
  Python compilation, and diff whitespace validation.
- Automatic update application and restart remain disabled. The in-app version
  check is informational, and installation remains a manual release-artifact
  workflow until the signed-manifest and rollback contract is implemented.
- The ONNX cutout checkpoint remains external. Production network download and
  installation remain disabled because its provenance and commercial-use
  rights are **UNVERIFIED**.
- Real Provider requests, VPS deployment, source cleanup, and cross-project
  end-to-end operation were not part of this release verification.

## Historical v2.6.5 Outcome

- The `v2.6.5` tag was pushed, but Desktop Clients run `33715658824` and Docker
  Image run `33715658700` failed.
- No v2.6.5 GitHub Release, release assets, or GHCR image were created.
- v2.6.6 supersedes that failed tag with the desktop dependency and Docker
  readiness repairs described above.

## Packaging

- Docker Compose defaults are pinned to `ghcr.io/liwei9745/genbox:2.6.6`.
- Desktop, Docker Compose, Docker image, and source distributions include the
  applicable third-party notices and collected runtime license files.
