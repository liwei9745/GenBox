# GenBox v2.6.7 - Precision Edit Workflow History And Workbench Cleanup

Release date: 2026-09-06

## Included

- Precision Edit now has cross-session workflow history. Visual chains show a
  source image and its edit steps; users can filter by date or workflow, view a
  result, or restore a historical image to the workbench for another edit.
- The current-session gallery lives below the annotation toolbar. It starts as a
  compact "Show Precision Edit gallery" pill and expands downward without
  displacing the core canvas controls.
- Before, after, compare, use-as-next-base, and replace-image actions share one
  compact control row. The replacement control expands from its top-left anchor
  into local-file and media-library choices and remains safely disabled during
  an active task.
- Edit strategy and selection-semantics controls stay inline on wide screens
  and wrap only when a narrow layout needs it.

## Privacy And Safety

- Workflow-history APIs expose only sanitized dates, dimensions, counts, and
  application-local media URLs. They exclude prompts, filenames, paths, hashes,
  logs, credentials, and base64 payloads.
- Workflow image responses are re-encoded to remove image metadata. Restoration
  accepts only validated local API media URLs and keeps the existing base-image
  replacement confirmation flow.

## Verification Scope

- Local verification passed 1,440 Python tests, Precision Edit UI and i18n
  Node tests, JavaScript syntax checks, and `git diff --check`.
- **User-confirmed on 2026-09-06:** two real Precision Edit jobs completed in
  the local development lab and produced two current-session results. This does
  not claim universal support across third-party proxy endpoints, model aliases,
  or output sizes; those remain dependent on the configured Provider.
- ONNX cutout checkpoints are not included in desktop, Docker, or source
  artifacts. Their provenance, training-data lineage, and commercial-use rights
  are not established by this release.
- Automatic update application and restart remain disabled. Until a signed
  update manifest and rollback contract exist, upgrades use manually obtained
  Release artifacts.

## Install And Upgrade

- Desktop clients still include their runtime; Python is not a separate
  requirement.
- Docker Compose defaults to `ghcr.io/liwei9745/genbox:2.6.7`.
- The source-development lab defaults to `http://localhost:8892`; desktop and
  Docker default to `http://localhost:8891`. Port `8893` is configurable for an
  isolated preview or private entry point, not the default development port.
