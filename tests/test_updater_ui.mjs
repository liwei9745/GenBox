import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');

function extractFunction(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} must exist`);
  const brace = source.indexOf('{', start);
  let depth = 0;
  for (let index = brace; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1;
    if (source[index] === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(start, index + 1);
    }
  }
  throw new Error(`Unclosed function ${name}`);
}

const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    elements.set(id, {
      textContent: '',
      disabled: false,
      style: {},
      classList: { add() {}, remove() {} },
      setAttribute(name, value) { this[name] = value; },
    });
  }
  return elements.get(id);
}

const requests = [];
const context = {
  console,
  document: { getElementById: element },
  i18nText: (key) => key,
  _authFetch: async (url, options) => {
    requests.push({ url, options });
    return {
      ok: false,
      status: 503,
      json: async () => ({ detail: { code: 'update_apply_unavailable' } }),
    };
  },
};
vm.createContext(context);
vm.runInContext(extractFunction('_applyUpdate'), context);

context._applyUpdate();
await new Promise((resolve) => setImmediate(resolve));

assert.equal(requests.length, 1);
assert.equal(requests[0].url, '/api/update/apply');
assert.equal(requests[0].options.method, 'POST');
assert.deepEqual(JSON.parse(requests[0].options.body), {});
assert.equal(requests[0].options.body.includes('url'), false);
assert.equal(requests[0].options.body.includes('mirror'), false);
assert.equal(source.includes("_authFetch('/api/update/mirrors')"), false);
assert.equal(source.includes('d.download_url'), false);
assert.equal(source.includes('function _testMirrors('), false);
assert.equal(source.includes('mirrorUrl'), false);
assert.equal(source.includes('downloadUrl'), false);
assert.equal(
  element('updateModalStatus').textContent,
  'update.manual_install_guidance',
);

console.log('updater UI safety contract passed');
