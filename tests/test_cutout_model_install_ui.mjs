import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'static/css/app.css'), 'utf8');
const i18n = fs.readFileSync(path.join(root, 'static/js/i18n.js'), 'utf8');

function expect(condition, message) {
  if (!condition) throw new Error(message);
}

function extractFunction(name) {
  const marker = 'function ' + name + '(';
  const start = js.indexOf(marker);
  expect(start !== -1, 'Missing function: ' + name);
  const bodyStart = js.indexOf('{', start);
  let depth = 0;
  let quote = '';
  let escaped = false;
  let regex = false;
  for (let index = bodyStart; index < js.length; index += 1) {
    const char = js[index];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = '';
      continue;
    }
    if (regex) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '/') regex = false;
      continue;
    }
    if (char === '"' || char === "'" || char === String.fromCharCode(96)) {
      quote = char;
      continue;
    }
    if (char === '/' && js[index + 1] !== '/' && js[index + 1] !== '*') {
      const prefix = js.slice(bodyStart, index);
      if (/(?:\b(?:return|throw|case)|[({[=,:;!&|?])\s*$/.test(prefix)) {
        regex = true;
        continue;
      }
    }
    if (char === '{') depth += 1;
    if (char === '}' && --depth === 0) return js.slice(start, index + 1);
  }
  throw new Error('Unterminated function: ' + name);
}

function classList(initial = []) {
  const values = new Set(initial);
  return {
    add: (...items) => items.forEach((item) => values.add(item)),
    remove: (...items) => items.forEach((item) => values.delete(item)),
    contains: (item) => values.has(item),
    toggle: (item, force) => {
      if (force === true) values.add(item);
      else if (force === false) values.delete(item);
      else if (values.has(item)) values.delete(item);
      else values.add(item);
      return values.has(item);
    },
  };
}

let activeElement = null;

function node(initialClasses = []) {
  return {
    classList: classList(initialClasses),
    dataset: {},
    disabled: false,
    textContent: '',
    value: 0,
    attributes: {},
    listeners: {},
    containedNodes: new Set(),
    setAttribute(name, value) { this.attributes[name] = String(value); },
    getAttribute(name) { return this.attributes[name]; },
    addEventListener(name, callback) { this.listeners[name] = callback; },
    contains(candidate) { return candidate === this || this.containedNodes.has(candidate); },
    focus() { activeElement = this; },
  };
}

const elements = {
  precisionCutoutAdapterPicker: node(),
  precisionCutoutAlgorithm: node(),
  precisionCutoutAlgorithmStatus: node(),
  btnPrecisionCutoutAdapterDetails: node(),
  precisionCutoutAdapterDetails: node(['hidden']),
  precisionCutoutModelInstall: node(),
  precisionCutoutModelStatus: node(),
  btnPrecisionCutoutModelDetails: node(),
  precisionCutoutModelDetails: node(),
  precisionCutoutModelSource: node(),
  precisionCutoutModelSize: node(),
  precisionCutoutModelPath: node(),
  precisionCutoutModelProgress: node(['hidden']),
  precisionCutoutModelProgressBar: node(),
  precisionCutoutModelProgressText: node(),
  btnPrecisionCutoutModelInstall: node(),
  btnPrecisionCutoutModelCancel: node(['hidden']),
  btnPrecisionCutoutModelRetry: node(['hidden']),
  btnPrecisionCutoutModelRemoveCorrupt: node(['hidden']),
  btnPrecisionCutoutModelDelete: node(['hidden']),
};
elements.precisionCutoutModelDetails.containedNodes = new Set([
  elements.btnPrecisionCutoutModelInstall,
  elements.btnPrecisionCutoutModelCancel,
  elements.btnPrecisionCutoutModelRetry,
  elements.btnPrecisionCutoutModelRemoveCorrupt,
  elements.btnPrecisionCutoutModelDelete,
]);

let fetchImpl = async () => { throw new Error('unexpected fetch'); };
let calls = [];
let confirmResult = true;
const confirmations = [];
const cutoutStates = [];
let capabilityProbes = 0;
let scheduled = [];

const context = vm.createContext({
  PRECISION_CUTOUT_CONTRACT: 'genbox-cutout-v1',
  PRECISION_CUTOUT_MODEL_INSTALL_CONTRACT: 'genbox-cutout-model-install-v1',
  PRECISION_CUTOUT_MODEL_SOURCE_ID: 'rembg-u2net-human-seg-v0.0.0',
  PRECISION_CUTOUT_MODEL_RELATIVE_PATH: 'storage/models/cutout/u2net_human_seg.onnx',
  PRECISION_CUTOUT_MODEL_POLL_INTERVAL_MS: 800,
  precisionCutoutCapability: null,
  precisionCutoutSelectedAdapter: '',
  precisionCutoutAdapterDetailsExpanded: false,
  precisionCutoutPending: false,
  precisionCutoutProbeToken: 0,
  precisionCutoutModel: null,
  precisionCutoutModelTask: null,
  precisionCutoutModelRefreshToken: 0,
  precisionCutoutModelTaskToken: 0,
  precisionCutoutModelTaskId: '',
  precisionCutoutModelPollTimer: null,
  precisionCutoutModelMutationPending: false,
  precisionCutoutModelDetailsPreference: null,
  document: {
    get activeElement() { return activeElement; },
    getElementById: (id) => elements[id] || null,
  },
  _authFetch: (...args) => fetchImpl(...args),
  confirm: (message) => { confirmations.push(message); return confirmResult; },
  encodeURIComponent,
  clearTimeout: (id) => { scheduled = scheduled.filter((entry) => entry.id !== id); },
  setTimeout: (callback, delay) => {
    const id = scheduled.length + 1;
    scheduled.push({ id, callback, delay });
    return id;
  },
  i18nText: (key, values = {}) => Object.entries(values).reduce(
    (text, [name, value]) => text.replaceAll('{' + name + '}', String(value)),
    key + (Object.keys(values).length ? ' {progress} {size} {path}' : ''),
  ),
  setPrecisionCutoutUi: (key, state) => cutoutStates.push({ key, state }),
  updatePrecisionCutoutAvailability: async () => {
    capabilityProbes += 1;
    context.precisionCutoutCapability = {
      contract: 'genbox-cutout-v1', available: true, executable: true, adapters: ['u2net-human-seg-onnx'],
    };
    return context.precisionCutoutCapability;
  },
});

for (const name of [
  'getPrecisionCutoutControls',
  'precisionCutoutUiBusy',
  'precisionCutoutIsExecutable',
  'precisionCutoutAdapterId',
  'precisionCutoutAdapterText',
  'precisionCutoutAdapterRecords',
  'precisionCutoutExecutableAdapterRecords',
  'precisionCutoutSelectedAdapterRecord',
  'precisionCutoutAdapterDisplayName',
  'precisionCutoutAdapterEscaped',
  'precisionCutoutAdapterFact',
  'setPrecisionCutoutAdapterDetailsExpanded',
  'togglePrecisionCutoutAdapterDetails',
  'renderPrecisionCutoutAdapterOptions',
  'renderPrecisionCutoutAdapterPicker',
  'setPrecisionCutoutSelectedAdapter',
  'readPrecisionCutoutResponse',
  'precisionCutoutResponseError',
  'precisionCutoutModelRecord',
  'precisionCutoutModelTaskRecord',
  'precisionCutoutModelTaskIsActive',
  'precisionCutoutModelState',
  'formatPrecisionCutoutModelBytes',
  'precisionCutoutModelPhaseKey',
  'setPrecisionCutoutModelDetailsExpanded',
  'syncPrecisionCutoutModelDetails',
  'togglePrecisionCutoutModelDetails',
  'renderPrecisionCutoutModelInstaller',
  'stopPrecisionCutoutModelPolling',
  'disablePrecisionCutoutForModel',
  'pollPrecisionCutoutModelTask',
  'monitorPrecisionCutoutModelTask',
  'refreshPrecisionCutoutModelStatus',
  'refreshPrecisionCutoutSetup',
  'precisionCutoutModelMutationPayload',
  'submitPrecisionCutoutModelDownload',
  'requestPrecisionCutoutModelInstall',
  'deletePrecisionCutoutModel',
  'retryPrecisionCutoutModelDownload',
  'cancelPrecisionCutoutModelDownload',
]) vm.runInContext(extractFunction(name), context);

const adapterCapability = {
  contract: 'genbox-cutout-v1', available: true, executable: true,
  adapters: ['u2net-human-seg-onnx'],
  adapter_capabilities: [
    {
      adapter: 'u2net-human-seg-onnx', algorithm: 'U2Net human segmentation ONNX',
      available: true, executable: true, state: 'ready', source_page: 'fixed-rembg-source',
      license: { name: 'UNVERIFIED', status: 'UNVERIFIED' }, dependencies: ['onnxruntime'],
    },
    {
      adapter: 'rmbg-2.0', algorithm: 'BRIA RMBG-2.0 (BiRefNet architecture)',
      available: false, executable: false, state: 'unavailable', needs_model: true, needs_dependency: true,
      descriptor: { source_page: 'gated-source', license_name: 'bria-rmbg-2.0', license_status: 'NON_COMMERCIAL_ONLY_UNVERIFIED', dependencies: ['torch', 'transformers'] },
    },
    {
      adapter: 'modnet-photographic-portrait', algorithm: 'MODNet photographic portrait matting',
      available: false, executable: false, state: 'unavailable', needs_model: true, needs_dependency: true,
      descriptor: { source_page: 'MODNet source', license_name: 'Apache-2.0 code; checkpoint terms unverified', license_status: 'UNVERIFIED', dependencies: ['onnxruntime', 'Pillow', 'numpy'] },
    },
    {
      adapter: 'birefnet-v1-lite', algorithm: 'BiRefNet v1 lite',
      available: false, executable: false, state: 'unavailable', needs_model: true, needs_dependency: true,
      descriptor: { source_page: 'BiRefNet source', license_name: 'Checkpoint license unverified', license_status: 'UNVERIFIED', dependencies: ['torch', 'Pillow', 'numpy'] },
    },
  ],
};
context.precisionCutoutCapability = adapterCapability;
assert.equal(vm.runInContext('renderPrecisionCutoutAdapterPicker(precisionCutoutCapability).adapter', context), 'u2net-human-seg-onnx');
assert.equal(context.precisionCutoutSelectedAdapter, 'u2net-human-seg-onnx', 'Only an executable adapter may become the default selection.');
assert.equal(elements.precisionCutoutAlgorithm.disabled, false);
assert.ok(elements.precisionCutoutAlgorithm.innerHTML.includes('u2net-human-seg-onnx'));
assert.ok(!elements.precisionCutoutAlgorithm.innerHTML.includes('rmbg-2.0'), 'Unavailable candidates must not become selectable options.');
assert.ok(!elements.precisionCutoutAlgorithm.innerHTML.includes('modnet-photographic-portrait'));
assert.ok(!elements.precisionCutoutAlgorithm.innerHTML.includes('birefnet-v1-lite'));
assert.ok(elements.precisionCutoutAdapterDetails.innerHTML.includes('BRIA RMBG-2.0 (BiRefNet architecture)'));
assert.ok(elements.precisionCutoutAdapterDetails.innerHTML.includes('MODNet photographic portrait matting'));
assert.ok(elements.precisionCutoutAdapterDetails.innerHTML.includes('BiRefNet v1 lite'));
assert.ok(elements.precisionCutoutAdapterDetails.innerHTML.includes('torch, transformers'));
assert.equal(elements.btnPrecisionCutoutAdapterDetails.getAttribute('aria-expanded'), 'false', 'Candidate details must start collapsed.');
assert.equal(vm.runInContext("setPrecisionCutoutSelectedAdapter('rmbg-2.0')", context), false, 'An unavailable adapter must be rejected even if the browser submits its ID.');
assert.equal(context.precisionCutoutSelectedAdapter, 'u2net-human-seg-onnx');

// A cancelled/stale operation flag must not permanently lock the algorithm
// picker when there is no live request controller anymore.
context.precisionCutoutPending = true;
context.precisionCutoutAbortController = null;
assert.equal(vm.runInContext('precisionCutoutUiBusy()', context), false);
assert.equal(vm.runInContext('renderPrecisionCutoutAdapterPicker(precisionCutoutCapability).adapter', context), 'u2net-human-seg-onnx');
assert.equal(elements.precisionCutoutAlgorithm.disabled, false);
context.precisionCutoutAbortController = { signal: { aborted: true } };
assert.equal(vm.runInContext('precisionCutoutUiBusy()', context), false, 'An already-aborted controller must not keep the picker locked.');
context.precisionCutoutPending = false;
context.precisionCutoutAbortController = null;
assert.equal(vm.runInContext('togglePrecisionCutoutAdapterDetails()', context), true);
assert.equal(elements.precisionCutoutAdapterDetails.classList.contains('hidden'), false);

// Multiple executable adapters must be selectable without promoting unverified candidates.
const multiAdapterCapability = JSON.parse(JSON.stringify(adapterCapability));
multiAdapterCapability.adapters.push('modnet-photographic-portrait');
multiAdapterCapability.adapter_capabilities[2].available = true;
multiAdapterCapability.adapter_capabilities[2].executable = true;
multiAdapterCapability.adapter_capabilities[2].state = 'ready';
context.precisionCutoutCapability = multiAdapterCapability;
assert.equal(vm.runInContext('renderPrecisionCutoutAdapterPicker(precisionCutoutCapability).adapter', context), 'u2net-human-seg-onnx');
assert.equal(elements.precisionCutoutAlgorithm.disabled, false);
assert.ok(elements.precisionCutoutAlgorithm.innerHTML.includes('U2Net human segmentation ONNX'));
assert.ok(elements.precisionCutoutAlgorithm.innerHTML.includes('MODNet photographic portrait matting'));
assert.ok(elements.precisionCutoutAlgorithm.innerHTML.includes('creator.cutout_algorithm_modnet_lab_notice'), 'MODNet must remain explicitly experimental in the local lab picker.');
assert.equal(vm.runInContext("setPrecisionCutoutSelectedAdapter('modnet-photographic-portrait')", context), true, 'A second executable adapter must be selectable.');
assert.equal(context.precisionCutoutSelectedAdapter, 'modnet-photographic-portrait');
assert.equal(elements.precisionCutoutAlgorithm.value, 'modnet-photographic-portrait');
assert.equal(vm.runInContext("setPrecisionCutoutSelectedAdapter('u2net-human-seg-onnx')", context), true, 'The original executable adapter must remain selectable after switching.');
assert.equal(context.precisionCutoutSelectedAdapter, 'u2net-human-seg-onnx');

// U2-Net remains the deterministic default even when the backend orders an
// experimental MODNet candidate first.
const reorderedAdapterCapability = JSON.parse(JSON.stringify(multiAdapterCapability));
reorderedAdapterCapability.adapters = ['modnet-photographic-portrait', 'u2net-human-seg-onnx'];
reorderedAdapterCapability.adapter_capabilities.reverse();
context.precisionCutoutSelectedAdapter = '';
context.precisionCutoutCapability = reorderedAdapterCapability;
assert.equal(vm.runInContext('renderPrecisionCutoutAdapterPicker(precisionCutoutCapability).adapter', context), 'u2net-human-seg-onnx');

// If the capability probe reports only unverified candidates, fail closed while retaining guidance.
const unavailableOnlyCapability = JSON.parse(JSON.stringify(adapterCapability));
unavailableOnlyCapability.available = false;
unavailableOnlyCapability.executable = false;
unavailableOnlyCapability.adapters = [];
unavailableOnlyCapability.adapter_capabilities.forEach((record) => {
  record.available = false;
  record.executable = false;
  record.state = 'unavailable';
});
context.precisionCutoutCapability = unavailableOnlyCapability;
assert.equal(vm.runInContext('renderPrecisionCutoutAdapterPicker(precisionCutoutCapability)', context), null, 'No executable adapter may become selected.');
assert.equal(context.precisionCutoutSelectedAdapter, '');
assert.equal(elements.precisionCutoutAlgorithm.disabled, true);
assert.ok(elements.precisionCutoutAlgorithm.innerHTML.includes('creator.cutout_algorithm_unavailable'));
assert.equal(elements.precisionCutoutAlgorithmStatus.textContent, 'creator.cutout_algorithm_unavailable');
assert.ok(elements.precisionCutoutAdapterDetails.innerHTML.includes('U2Net human segmentation ONNX'));
assert.ok(elements.precisionCutoutAdapterDetails.innerHTML.includes('creator.cutout_algorithm_unverified'));

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

function model(overrides = {}) {
  return {
    contract: 'genbox-cutout-model-install-v1',
    source_id: 'rembg-u2net-human-seg-v0.0.0',
    source_page: 'fixed-rembg-source',
    filename: 'u2net_human_seg.onnx',
    installed: false,
    valid: false,
    state: 'missing',
    reason: 'model_missing',
    size_bytes: 175997641,
    sha256: 'synthetic-sha256',
    md5: 'synthetic-md5',
    download_supported: true,
    install_supported: true,
    confirmation_required: true,
    license: {
      checkpoint_provenance_status: 'UNVERIFIED',
      commercial_use_status: 'UNVERIFIED',
    },
    active_task: null,
    ...overrides,
  };
}

function task(status, overrides = {}) {
  return {
    id: 'cutout-model-task-1',
    contract: 'genbox-cutout-model-install-v1',
    source_id: 'rembg-u2net-human-seg-v0.0.0',
    status,
    phase: status,
    progress: status === 'completed' ? 100 : 35,
    downloaded_bytes: 61000000,
    total_bytes: 175997641,
    error_code: '',
    message: '',
    ...overrides,
  };
}

function renderedState(modelValue, taskValue = null, overrideState) {
  context.precisionCutoutModel = modelValue;
  context.precisionCutoutModelTask = taskValue;
  return vm.runInContext('renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask, ' + (overrideState ? JSON.stringify(overrideState) : 'undefined') + ')', context);
}

assert.equal(renderedState(null, null, 'checking'), 'checking');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false', 'Status checks should keep the detail region collapsed by default.');
assert.equal(renderedState(model()), 'missing');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false', 'Missing models should keep verbose install guidance collapsed by default.');
assert.equal(elements.precisionCutoutModelDetails.classList.contains('hidden'), true);
assert.equal(elements.btnPrecisionCutoutModelInstall.classList.contains('hidden'), false);
assert.equal(elements.btnPrecisionCutoutModelInstall.disabled, false);
assert.equal(elements.precisionCutoutModelPath.textContent, 'storage/models/cutout/u2net_human_seg.onnx');

const productionModel = model({ download_supported: false, install_supported: false });
assert.equal(renderedState(productionModel), 'missing');
assert.equal(elements.btnPrecisionCutoutModelInstall.classList.contains('hidden'), false);
assert.equal(elements.btnPrecisionCutoutModelInstall.disabled, true);
assert.equal(elements.btnPrecisionCutoutModelInstall.textContent, 'creator.cutout_model_install_unavailable');
assert.equal(elements.precisionCutoutModelStatus.textContent.startsWith('creator.cutout_model_download_unavailable'), true);
calls = [];
confirmations.length = 0;
fetchImpl = async (...args) => { calls.push(args); throw new Error('disabled install must not fetch'); };
context.precisionCutoutModel = productionModel;
context.precisionCutoutModelTask = null;
assert.equal(await vm.runInContext('requestPrecisionCutoutModelInstall()', context), false);
assert.equal(calls.length, 0);
assert.equal(confirmations.length, 0);

assert.equal(renderedState(model({ state: 'downloading' }), task('downloading')), 'downloading');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false', 'Active downloads should keep verbose progress details collapsed by default.');
assert.equal(elements.precisionCutoutModelProgress.classList.contains('hidden'), false);
assert.equal(elements.precisionCutoutModelProgressBar.value, 35);
assert.equal(elements.btnPrecisionCutoutModelCancel.classList.contains('hidden'), false);

assert.equal(renderedState(model({ installed: true, state: 'hash_mismatch', reason: 'model_hash_mismatch' })), 'hash_mismatch');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false', 'Fingerprint failures should keep recovery details collapsed by default.');
assert.equal(elements.btnPrecisionCutoutModelRetry.classList.contains('hidden'), false);
assert.equal(elements.btnPrecisionCutoutModelRemoveCorrupt.classList.contains('hidden'), false);

assert.equal(renderedState(model({ state: 'error', reason: 'download_failed' })), 'error');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false', 'Installer errors should keep recovery details collapsed by default.');
assert.equal(elements.btnPrecisionCutoutModelRetry.classList.contains('hidden'), false);

const readyModel = model({ installed: true, valid: true, state: 'ready', reason: '', download_supported: true });
elements.btnPrecisionCutoutModelRetry.focus();
assert.equal(activeElement, elements.btnPrecisionCutoutModelRetry);
assert.equal(renderedState(readyModel), 'ready');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false', 'Ready models should use the compact summary by default.');
assert.equal(elements.precisionCutoutModelDetails.classList.contains('hidden'), true);
assert.equal(elements.precisionCutoutModelDetails.getAttribute('aria-hidden'), 'true');
assert.equal(activeElement, elements.btnPrecisionCutoutModelDetails, 'Collapsing details must return focus to the toggle when focus was inside.');
assert.equal(elements.btnPrecisionCutoutModelDelete.classList.contains('hidden'), false);

assert.equal(vm.runInContext('togglePrecisionCutoutModelDetails()', context), true, 'The details control should expand a compact ready card.');
assert.equal(context.precisionCutoutModelDetailsPreference, true);
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'true');
assert.equal(elements.precisionCutoutModelDetails.classList.contains('hidden'), false);
assert.equal(renderedState(readyModel), 'ready');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'true', 'Refresh renders must preserve a user expansion.');
assert.equal(vm.runInContext('togglePrecisionCutoutModelDetails()', context), false);
assert.equal(context.precisionCutoutModelDetailsPreference, false);
assert.equal(renderedState(model({ state: 'error', reason: 'download_failed' })), 'error');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false', 'Attention states should keep verbose recovery details collapsed by default.');
assert.equal(vm.runInContext('togglePrecisionCutoutModelDetails()', context), true, 'Attention-state details should expand on demand.');
assert.equal(context.precisionCutoutModelDetailsPreference, true, 'Expanding attention details should remember the user preference.');
assert.equal(renderedState(readyModel), 'ready');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'true', 'Returning to ready should preserve the remembered expansion.');
context.precisionCutoutModelDetailsPreference = null;
assert.equal(renderedState(readyModel), 'ready');
assert.equal(elements.btnPrecisionCutoutModelDetails.getAttribute('aria-expanded'), 'false');

confirmResult = false;
confirmations.length = 0;
calls = [];
fetchImpl = async (...args) => { calls.push(args); throw new Error('confirmation must block fetch'); };
context.precisionCutoutModel = model();
context.precisionCutoutModelTask = null;
assert.equal(await vm.runInContext('requestPrecisionCutoutModelInstall()', context), false);
assert.equal(calls.length, 0);
assert.equal(confirmations.length, 1);
assert.ok(confirmations[0].includes('creator.cutout_model_install_confirm'));

confirmResult = true;
calls = [];
fetchImpl = async (url, options = {}) => {
  calls.push({ url, options });
  if (url === '/api/image-tools/cutout/model/download') return response(200, { ok: true, task: task('queued') });
  if (url === '/api/image-tools/cutout/model/download/cutout-model-task-1') return response(200, { task: task('downloading') });
  throw new Error('unexpected URL ' + url);
};
context.precisionCutoutModel = model();
context.precisionCutoutModelTask = null;
context.precisionCutoutPending = true;
assert.equal(await vm.runInContext('requestPrecisionCutoutModelInstall()', context), true);
await new Promise((resolve) => setImmediate(resolve));
assert.equal(calls[0].url, '/api/image-tools/cutout/model/download');
assert.equal(calls[0].options.method, 'POST');
assert.deepEqual(JSON.parse(calls[0].options.body), {
  contract: 'genbox-cutout-model-install-v1',
  source_id: 'rembg-u2net-human-seg-v0.0.0',
  confirmed: true,
});
assert.equal(calls[1].url, '/api/image-tools/cutout/model/download/cutout-model-task-1');
assert.equal(context.precisionCutoutPending, true, 'Model download state must not overwrite cutout/refine operation state.');
assert.equal(context.precisionCutoutModelTask.status, 'downloading');

calls = [];
fetchImpl = async (url, options = {}) => {
  calls.push({ url, options });
  if (url.endsWith('/cutout-model-task-1') && options.method === 'DELETE') return response(200, { task: task('cancelled') });
  if (url === '/api/image-tools/cutout/model') return response(200, model());
  throw new Error('unexpected cancel URL ' + url);
};
context.precisionCutoutModelTask = task('downloading');
context.precisionCutoutModelTaskId = 'cutout-model-task-1';
assert.equal(await vm.runInContext('cancelPrecisionCutoutModelDownload()', context), true);
assert.equal(calls[0].url, '/api/image-tools/cutout/model/download/cutout-model-task-1');
assert.equal(calls[0].options.method, 'DELETE');
assert.equal(context.precisionCutoutPending, true, 'Cancelling a model download must not cancel an active cutout/refine operation.');

calls = [];
fetchImpl = async (url, options = {}) => {
  calls.push({ url, options });
  if (url === '/api/image-tools/cutout/model/delete') return response(200, { ok: true, deleted: true, model: model() });
  if (url === '/api/image-tools/cutout/model/download') return response(200, { ok: true, task: task('queued') });
  if (url.endsWith('/cutout-model-task-1')) return response(200, { task: task('downloading') });
  throw new Error('unexpected retry URL ' + url);
};
context.precisionCutoutModel = model({ installed: true, state: 'hash_mismatch', reason: 'model_hash_mismatch' });
context.precisionCutoutModelTask = task('failed', { error_code: 'model_hash_mismatch' });
assert.equal(await vm.runInContext('retryPrecisionCutoutModelDownload()', context), true);
await new Promise((resolve) => setImmediate(resolve));
assert.deepEqual(calls.slice(0, 2).map((call) => call.url), [
  '/api/image-tools/cutout/model/delete',
  '/api/image-tools/cutout/model/download',
]);
assert.equal(confirmations.at(-1).includes('creator.cutout_model_remove_retry_confirm'), true);

calls = [];
fetchImpl = async (url, options = {}) => {
  calls.push({ url, options });
  return response(200, { ok: true, deleted: true, model: model() });
};
context.precisionCutoutModel = readyModel;
context.precisionCutoutModelTask = null;
context.precisionCutoutPending = false;
assert.equal(await vm.runInContext("deletePrecisionCutoutModel('ready')", context), true);
assert.equal(calls[0].url, '/api/image-tools/cutout/model/delete');
assert.equal(calls[0].options.method, 'POST');
assert.equal(context.precisionCutoutCapability, null);
assert.ok(cutoutStates.some((entry) => entry.state === 'unavailable'));

let resolveOlder;
let resolveNewer;
const older = new Promise((resolve) => { resolveOlder = resolve; });
const newer = new Promise((resolve) => { resolveNewer = resolve; });
let refreshCall = 0;
fetchImpl = async () => (++refreshCall === 1 ? older : newer);
context.precisionCutoutModel = null;
context.precisionCutoutModelTask = null;
capabilityProbes = 0;
const olderRefresh = vm.runInContext('refreshPrecisionCutoutModelStatus()', context);
const newerRefresh = vm.runInContext('refreshPrecisionCutoutModelStatus()', context);
resolveNewer(response(200, readyModel));
assert.equal(await newerRefresh, true);
resolveOlder(response(200, model()));
assert.equal(await olderRefresh, false);
assert.equal(context.precisionCutoutModel.state, 'ready', 'An older refresh response must not replace newer model state.');
assert.equal(capabilityProbes, 1, 'A ready model must be followed by exactly one executable capability probe.');

// A failed model-status refresh still has a live recovery path through the
// independently authoritative algorithm capability endpoint.
fetchImpl = async () => { throw new Error('model status unavailable'); };
context.precisionCutoutModel = readyModel;
context.precisionCutoutModelTask = null;
capabilityProbes = 0;
assert.equal(await vm.runInContext('refreshPrecisionCutoutSetup()', context), true);
assert.equal(capabilityProbes, 1, 'Failed model refresh must fall back to a capability recheck.');

let resolveStaleTask;
fetchImpl = async () => new Promise((resolve) => { resolveStaleTask = resolve; });
context.precisionCutoutModel = model({ state: 'downloading' });
context.precisionCutoutModelTask = task('downloading');
context.precisionCutoutModelTaskId = 'cutout-model-task-1';
context.precisionCutoutModelTaskToken = 20;
const stalePoll = vm.runInContext("pollPrecisionCutoutModelTask('cutout-model-task-1', 20)", context);
vm.runInContext('stopPrecisionCutoutModelPolling()', context);
resolveStaleTask(response(200, { task: task('completed') }));
assert.equal(await stalePoll, false);
assert.equal(context.precisionCutoutModelTask.status, 'downloading', 'A stale task response must not update installer state.');

const activeTaskModel = model({ state: 'downloading', active_task: task('downloading') });
calls = [];
fetchImpl = async (url) => {
  calls.push(url);
  if (url === '/api/image-tools/cutout/model') return response(200, activeTaskModel);
  return response(200, { task: task('downloading') });
};
assert.equal(await vm.runInContext('refreshPrecisionCutoutModelStatus()', context), true);
await new Promise((resolve) => setImmediate(resolve));
assert.ok(calls.includes('/api/image-tools/cutout/model/download/cutout-model-task-1'), 'Refresh must resume polling the backend-reported active task.');

for (const id of [
  'precisionCutoutModelInstall', 'precisionCutoutModelStatus', 'btnPrecisionCutoutModelDetails',
  'precisionCutoutModelDetails', 'precisionCutoutModelProgress',
  'btnPrecisionCutoutModelInstall', 'btnPrecisionCutoutModelCancel', 'btnPrecisionCutoutModelRetry',
  'btnPrecisionCutoutModelRemoveCorrupt', 'btnPrecisionCutoutModelDelete', 'btnPrecisionCutoutCapabilityRefresh',
]) expect(html.includes('id="' + id + '"'), 'Missing cutout model installer element: ' + id);
expect(html.includes('aria-controls="precisionCutoutModelDetails"'), 'The details toggle must name its controlled region.');
expect(html.includes('id="btnPrecisionCutoutCapabilityRefresh"'), 'Capability recheck must remain available after a failed model status refresh.');
expect(js.includes("cutoutCapabilityRefresh.addEventListener('click', refreshPrecisionCutoutSetup)"), 'Capability recheck must bind to the recovery flow.');
expect(html.includes('data-details-expanded="false"'), 'The installer details must start collapsed.');
expect(html.includes('id="btnPrecisionCutoutModelDetails" role="button" tabindex="0" aria-expanded="false"'), 'The collapsed details toggle must remain accessible.');
expect(html.includes('id="precisionCutoutModelDetails" aria-hidden="true"'), 'The initial details region must be hidden.');
expect(/id="btnPrecisionCutoutModelDetails"[^>]*role="button"[^>]*tabindex="0"/.test(html), 'The whole cutout status summary must be keyboard-focusable and clickable.');
expect(js.includes("cutoutModelDetailsToggle.addEventListener('click', togglePrecisionCutoutModelDetails)"), 'The details control must be bound once with the other Precision Edit controls.');
expect(js.includes("cutoutModelDetailsToggle.addEventListener('keydown'") && js.includes("event.key !== 'Enter' && event.key !== ' '"), 'The clickable cutout status summary must support Enter and Space.');
expect(html.includes('storage/models/cutout/u2net_human_seg.onnx'), 'The UI must show the fixed relative model path.');
expect(html.includes('rembg-u2net-human-seg-v0.0.0'), 'The UI must show the fixed source identity.');
expect(!/precisionCutoutModel[^>]*(?:input|type="url")/i.test(html), 'The installer must not expose a remote URL input.');
expect(js.includes("_authFetch('/api/image-tools/cutout/model/download/' + encodeURIComponent(taskId), { method: 'DELETE' })"), 'Cancellation must use DELETE download/{task_id}.');
expect(!js.includes('/api/image-tools/cutout/model/tasks/'), 'The obsolete model task path must not be used.');
expect(!js.includes('localStorage') || !js.slice(js.indexOf('function precisionCutoutModelRecord'), js.indexOf('function precisionCutoutFeatherRadius')).includes('localStorage'), 'Installer task state must not be persisted in browser storage.');
for (const selector of ['.precision-cutout-model-install', '.precision-cutout-model-summary', '.precision-cutout-model-toggle', '.precision-cutout-model-details', '.precision-cutout-model-facts', '.precision-cutout-model-progress', '.precision-cutout-model-actions']) {
  expect(css.includes(selector), 'Missing compact installer CSS: ' + selector);
}
expect(css.includes('overflow-wrap: anywhere;') && css.includes('word-break: break-all;'), 'Long model facts must not overflow narrow layouts.');
for (const key of [
  'cutout_model_title', 'cutout_model_checking', 'cutout_model_missing', 'cutout_model_downloading',
  'cutout_model_hash_mismatch', 'cutout_model_error', 'cutout_model_ready', 'cutout_model_install_confirm',
  'cutout_model_remove_retry_confirm', 'cutout_model_delete_confirm', 'cutout_model_license_warning',
  'cutout_model_download_unavailable', 'cutout_model_install_unavailable', 'cutout_model_details',
]) expect(i18n.includes("MESSAGES['creator." + key + "']"), 'Missing bilingual installer translation: ' + key);

console.log('cutout model installer UI assertions passed');
