import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sources = [
  ['standalone', fs.readFileSync(path.join(root, 'static/js/gallery.js'), 'utf8')],
  ['bundle', fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8')],
];

function extractFunction(js, name) {
  const declaration = 'function ' + name + '(';
  const assignment = 'window.' + name + ' = function(';
  const declarationStart = js.indexOf(declaration);
  const assignmentStart = js.indexOf(assignment);
  const start = declarationStart === -1 ? assignmentStart : declarationStart;
  assert.notEqual(start, -1, 'Missing function: ' + name);
  const bodyStart = js.indexOf('{', start);
  let depth = 0;
  let quote = '';
  let escaped = false;
  for (let index = bodyStart; index < js.length; index += 1) {
    const char = js[index];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = '';
      continue;
    }
    if (char === '"' || char === "'" || char === String.fromCharCode(96)) {
      quote = char;
      continue;
    }
    if (char === '{') depth += 1;
    if (char === '}' && --depth === 0) return js.slice(start, index + 1);
  }
  throw new Error('Unterminated function: ' + name);
}

function createHarness(js, items) {
  const consoleCalls = [];
  const alerts = [];
  const lightboxCalls = [];
  const sandbox = {
    galleryItems: items,
    console: {
      error: (...args) => consoleCalls.push(['error', ...args]),
      log: (...args) => consoleCalls.push(['log', ...args]),
    },
    alert: (message) => alerts.push(message),
    i18nText: (key) => key,
    findProvider: () => ({ name: 'Provider', color: '#000000' }),
    openLightbox: (...args) => lightboxCalls.push(args),
    encodeURIComponent,
  };
  sandbox.window = sandbox;
  const context = vm.createContext(sandbox);
  vm.runInContext(extractFunction(js, 'openLightboxFromGallery'), context);
  return { context, consoleCalls, alerts, lightboxCalls };
}

for (const [label, js] of sources) {
  const missing = createHarness(js, []);
  vm.runInContext("openLightboxFromGallery('private-item-id')", missing.context);
  assert.deepEqual(missing.consoleCalls, [['error', '[Gallery] item_not_found']], label);

  const invalid = createHarness(js, [{
    id: 'private-item-id',
    prompt: 'private prompt content',
    local_path: '',
    user_metadata: 'private account metadata',
  }]);
  vm.runInContext("openLightboxFromGallery('private-item-id')", invalid.context);
  assert.deepEqual(invalid.consoleCalls, [['error', '[Gallery] invalid_local_path']], label);

  const valid = createHarness(js, [{
    id: 'private-item-id',
    model: 'private-model-name',
    prompt: 'private prompt content',
    local_path: 'private/folder/private-image.png',
    user_metadata: 'private account metadata',
  }]);
  vm.runInContext("openLightboxFromGallery('private-item-id')", valid.context);
  assert.deepEqual(valid.consoleCalls, [['log', '[Gallery] lightbox_opened']], label);
  assert.deepEqual(valid.lightboxCalls, [[
    '/api/gallery/image/private-image.png',
    'Provider',
    'private prompt content',
  ]], label);

  const loggedText = [...missing.consoleCalls, ...invalid.consoleCalls, ...valid.consoleCalls]
    .flat()
    .map(String)
    .join('\n');
  for (const sensitiveValue of [
    'private-item-id',
    'private prompt content',
    'private/folder/private-image.png',
    'private-image.png',
    'private-model-name',
    'private account metadata',
  ]) {
    assert.equal(loggedText.includes(sensitiveValue), false, label + ' console output leaked: ' + sensitiveValue);
  }
}

console.log('gallery logging UI assertions passed');
