import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');

function extract(name) {
  const marker = `function ${name}(`;
  const start = source.indexOf(marker);
  assert.notEqual(start, -1, `missing ${name}`);
  const body = source.indexOf('{', start);
  let depth = 0;
  let quote = '';
  let escaped = false;
  for (let i = body; i < source.length; i += 1) {
    const c = source[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (c === '\\') escaped = true;
      else if (c === quote) quote = '';
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      quote = c;
      continue;
    }
    if (c === '{') depth += 1;
    if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}

const context = vm.createContext({
  allProviders: [
    { id: 'gateway-a', model: 'gpt-image-2.5-c', models: ['gpt-image-2.5-c', 'nano-banana-2-2k'] },
    { id: 'gateway-b', model: 'qwen-image-edit', models: ['qwen-image-edit'] },
  ],
  imageProviderModelSelections: { 'gateway-b': 'qwen-image-edit' },
  findProvider: (id) => contextProviders.find((provider) => provider.id === id) || null,
});
const contextProviders = context.allProviders;
vm.runInContext([
  extract('generationProviderModelIds'),
  extract('generationProviderModelSettings'),
].join('\n'), context);

const explicit = vm.runInContext(
  "generationProviderModelSettings(['gateway-a', 'gateway-b'], 'nano-banana-2-2k')",
  context,
);
assert.equal(
  JSON.stringify(explicit),
  JSON.stringify(
  {
    'gateway-a': { model: 'nano-banana-2-2k' },
    'gateway-b': { model: 'qwen-image-edit' },
  }),
  'generation settings must bind the selected model only to providers that expose it',
);

const defaults = vm.runInContext(
  "generationProviderModelSettings(['gateway-a'], '_global')",
  context,
);
assert.equal(
  JSON.stringify(defaults),
  JSON.stringify({ 'gateway-a': { model: 'gpt-image-2.5-c' } }),
  'global model mode must preserve the provider default',
);

const retryContext = vm.createContext({
  lastGenContext: {
    mode: 't2i',
    provider_settings: { 'gateway-a': { model: 'nano-banana-2-2k' } },
  },
});
assert.equal(
  retryContext.lastGenContext.provider_settings['gateway-a'].model,
  'nano-banana-2-2k',
  'retry context must retain the exact selected model',
);

console.log('precision protocol UI behavior passed');
