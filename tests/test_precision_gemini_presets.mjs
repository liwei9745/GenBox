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
assert.match(source, /outputPolicy !== 'fit_crop' && documented\.length > 0 && !!size && !modelPreset/);
assert.match(source, /precisionSelectedModelPresetTable/);

console.log('precision Gemini/Nano Banana preset contract passed');
