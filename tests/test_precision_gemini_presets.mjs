import fs from 'node:fs';
import assert from 'node:assert/strict';

const source = fs.readFileSync('static/js/app-all.js', 'utf8');

assert.match(source, /precisionSelectedModelCatalogEntry/);
assert.match(source, /documented_presets/);
assert.match(source, /precisionCatalogPresetList/);
assert.match(source, /option\.textContent/);
assert.match(
  source,
  /modelMismatch = outputPolicy !== 'fit_crop' && documented\.length > 0/
);
assert.match(
  source,
  /strict selectable sizes remain API facts|strict-size declaration controls generation readiness/
);
assert.match(source, /outputPolicy !== 'fit_crop' && documented\.length > 0 && !!size &&\s*\(!modelPreset \|\| !option\.dataset \|\| option\.dataset\.precisionModelCatalog !== 'true'\)/);
assert.match(source, /precisionSelectedModelPresetTable/);
assert.match(source, /modelPreset\.reliability_warning/);
assert.match(source, /creator\.precision_size_output_limit_warning/);

assert.match(source, /precisionProtocolControls/);
assert.match(source, /savePrecisionProtocolOverride/);
assert.match(source, /checkPrecisionProtocolConfig/);
assert.match(source, /precision-protocol/);
assert.match(source, /precision-preflight/);
assert.match(source, /protocol_override/);
assert.match(source, /size_model/);
console.log('precision Gemini/Nano Banana preset contract passed');
