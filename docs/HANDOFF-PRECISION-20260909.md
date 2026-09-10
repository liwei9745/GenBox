# Precision Edit Handoff - 2026-09-09

## State

The local GenBox laboratory is available at `http://127.0.0.1:8895`.
The precision-resize workbench now uses a user-controlled trial authorization
for sizes that the selected model has not explicitly declared. This is a local
contract completion, not evidence that every upstream model or size works.

## Preserve

- Keep strict output-size validation, explicit crop-to-fit adaptation, and the
  one-POST/no-automatic-retry guard for image edits.
- Keep model aliases and model-size evidence isolated by provider and canonical
  model. Never copy the successful `gpt-image2-bc` size records to
  `gpt-image-2.5-c` or another model.
- Keep the existing workflow history, annotations, gallery, canvas, and local
  cutout changes. The working tree is intentionally dirty and contains prior
  work that must not be reset or deleted wholesale.

## Current User Flow

1. Choose an authorized precision-edit model and a strict target size.
2. When the exact size is not declared, choose `授权试用 <size>` and accept the
   scoped warning.
3. The saved authorization is limited to the current provider, model, and
   exact size. It does not start a request.
4. The user separately selects Generate. A real upstream request requires
   explicit user authorization because it can incur cost.
5. A returned output that does not strictly match still fails; use the separate
   crop-to-fit mode only when the user explicitly chooses it.

## Verification Already Completed

```powershell
node --check static/js/app-all.js
node tests/test_precision_edit_ui.mjs
$env:GENBOX_PLAYWRIGHT_EXECUTABLE='C:\Program Files\Google\Chrome\Application\chrome.exe'
python -m pytest tests/test_precision_session_gallery_browser.py -q
python -m pytest tests/test_precision_edit_contract.py tests/test_precision_workflow_history.py -q
python -m pytest tests/test_provider_precision_contract.py tests/test_provider_precision_alias_compat.py tests/test_provider_error_safety.py -q
python -m pytest tests/test_setup_security.py -q
git diff --check
python scripts/genbox_lab.py status --port 8895
```

Observed results on 2026-09-09: UI static suite passed; browser `7 passed`;
precision/workflow `224 passed`; provider contracts `253 passed`; setup security
`41 passed`.

## Next Work

- 2026-09-10: Short inspector instructions and a five-step clickable quick-start
  guide are implemented. First precision entry opens the guide; dismissal is
  stored as a non-sensitive browser flag and Guide remains available for replay.
  Local cutout/refinement and online AI removal are explicitly distinguished.
  Node checks, ten synthetic browser scenarios and 518 focused Python tests pass.
  These changes await combined UI acceptance, not real-model compatibility signoff.
- The user has accepted target-model size presets. The model-first inspector,
  per-version dimensions/time and grouped model visibility await combined UI
  acceptance in the owned `8895` laboratory.
- Grouped visibility edits are draft-only until Confirm; selection changes
  retain the existing DOM, focused checkbox and list scroll. Group names are
  name-based navigation and never authorize a model or certify its capability.
- Local checkpoints: backend `95e06f2`, frontend `ccdd45c`, grouping `67978be`.
  Unrelated untracked files remain untouched.
- Latest local regression: Node syntax/UI/version-metadata checks passed,
  nine synthetic browser scenarios passed, and 518 focused Python tests passed.
- Other vendors' edit/size linkage needs subsequent independent verification
  and manual acceptance; it is not covered by target-model preset acceptance.
- Only after explicit approval, run one real precision-edit trial for a chosen
  model and size; record sanitized model, target, actual output, and outcome.
- Keep temporary `.pytest-tmp-*` outputs and screenshots out of any eventual
  feature commit unless deliberately selected as sanitized evidence.
