import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const models = [
  'veo-3.1-generate-preview', 'veo-3.1-fast-generate-preview',
  'veo-3.1-lite-generate-preview', 'veo-3.0-generate-001',
  'gemini-omni-flash-preview', 'gemini-omni-1.1-flash',
];
function extract(source, name) {
  const pattern = new RegExp('(?:function ' + name + '\\(|window\\.' + name + ' = function\\()[\\s\\S]*?\\n\\}');
  const found = source.match(pattern);
  assert.ok(found, name);
  return found[0] + ';';
}
for (const file of ['app-all.js', 'video.js']) {
  const source = fs.readFileSync(new URL('../static/js/' + file, import.meta.url), 'utf8');
  const context = vm.createContext({});
  context.window = context;
  for (const name of ['isModelMatchMode', 'getVideoProviderCapabilities']) {
    vm.runInContext(extract(source, name), context);
  }
  for (const id of models) {
    assert.equal(context.isModelMatchMode(id, 'ti2vid'), true, file + ' ' + id);
    assert.equal(context.isModelMatchMode(id, 'i2vid'), true);
    assert.equal(context.isModelMatchMode(id, 'keyframes'), false);
  }
  for (const id of ['gemini-2.5-flash', 'gemini-2.5-flash-preview-tts', 'gemini-3.1-flash-image', 'imagen-4.0-generate-001']) {
    assert.equal(context.isModelMatchMode(id, 'ti2vid'), false);
    assert.equal(context.isModelMatchMode(id, 'i2vid'), false);
  }
  assert.equal(context.isModelMatchMode('veo_3_1_t2v_fast', 'ti2vid'), true);
  assert.equal(context.isModelMatchMode('veo_3_1_i2v_s', 'ti2vid'), false);
  assert.equal(context.isModelMatchMode('veo_3_1_i2v_s', 'i2vid'), true);
  assert.equal(context.isModelMatchMode('sora-2', 'ti2vid'), true);
  const provider = {models: ['custom'], model_capabilities: {custom: {t2v: false, i2v: true}}};
  assert.equal(context.isModelMatchMode('custom', 'ti2vid', provider), false);
  assert.equal(context.isModelMatchMode('custom', 'i2vid', provider), true);
  assert.equal(context.getVideoProviderCapabilities(provider).i2v, true);
  assert.equal(context.getVideoProviderCapabilities(provider).t2v, undefined);
  assert.equal(context.getVideoProviderCapabilities({models}).t2v, true);
  assert.equal(context.getVideoProviderCapabilities({models}).i2v, true);
  const legacy = {models: ['custom'], model_capabilities: {custom: ['i2v']}};
  const before = JSON.stringify(legacy);
  assert.equal(context.getVideoProviderCapabilities(legacy).i2v, true);
  assert.equal(JSON.stringify(legacy), before);
  if (file === 'app-all.js') {
    for (const name of ['getProviderModelCapabilityRecord', 'filterModelsByType']) {
      vm.runInContext(extract(source, name), context);
    }
    assert.equal(context.filterModelsByType(models, 'video').length, models.length);
    assert.equal(context.filterModelsByType(models, 'image').length, 0);
    assert.equal(context.filterModelsByType(models, 'llm').length, 0);
    assert.equal(context.filterModelsByType(['custom'], 'video', provider).length, 1);
  }
}
console.log('Video model discovery filters passed (bundle and standalone).');
