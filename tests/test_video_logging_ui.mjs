import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sources = [
  ['standalone', fs.readFileSync(path.join(root, 'static/js/video.js'), 'utf8')],
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

function runGenerationHarness(js) {
  const prompt = 'private video prompt excerpt';
  const logCalls = [];
  const requests = [];
  const elements = {
    videoPrompt: { value: prompt },
    'vmodel_provider-private': { disabled: false, value: 'video-model' },
    videoFrames: { value: '121' },
    videoFPS: { value: '24' },
    videoSteps: { value: '' },
    videoSeed: { value: '' },
    videoNegPrompt: { value: '' },
    videoGenBtn: { disabled: false, textContent: '' },
    videoProgressBar: { style: {} },
    videoProgressFill: { style: {}, className: '' },
    videoProgressText: { textContent: '' },
    videoElapsed: { textContent: '' },
    videoTaskStatus: { textContent: '' },
    'vprog_fill_provider-private': { style: {}, classList: { remove: () => {} } },
    'vprog_label_provider-private': { textContent: '' },
  };
  const submit = (url, options) => {
    requests.push({ url, payload: JSON.parse(options.body) });
    return new Promise(() => {});
  };
  const sandbox = {
    selectedVideoProviderIds: ['provider-private'],
    currentVideoMode: 'ti2vid',
    kfImages: [],
    videoImages: [],
    videoImageRole: 'first_frame',
    videoPreviewGroups: {},
    videoGroupNavIdx: {},
    videoHistoryItems: [],
    currentVideoTaskId: null,
    document: { getElementById: (id) => elements[id] || null },
    alert: () => assert.fail('Valid generation must not alert.'),
    confirm: () => true,
    i18nText: (key) => key,
    getVideoDimensions: () => ({ width: 1280, height: 720 }),
    clearVideoLog: () => {},
    renderVideoPerProviderBars: () => {},
    videoLog: (...args) => logCalls.push(args),
    videoLogProvider: () => {},
    createVideoPreviewPlaceholders: () => {},
    startVideoElapsedTimer: () => {},
    startVideoPolling: () => {},
    renderVideoHistory: () => {},
    renderVideoGroupedPreview: () => {},
    _af: submit,
    _authFetch: submit,
  };
  sandbox.window = sandbox;
  const context = vm.createContext(sandbox);
  vm.runInContext(extractFunction(js, 'startVideoGenerate'), context);
  vm.runInContext('startVideoGenerate()', context);
  return { prompt, logCalls, requests };
}

for (const [label, js] of sources) {
  const generate = extractFunction(js, 'startVideoGenerate');
  assert.match(generate, /(?:window\.)?videoLog\('\\u751F\\u6210\\u8BF7\\u6C42\\u5DF2\\u51C6\\u5907', 'info'\);/, label + ' must log only the fixed generation-ready status.');
  assert.doesNotMatch(generate, /(?:window\.)?videoLog\([^;\n]*\bprompt\b[^;\n]*\);/, label + ' must not write prompt content to the video log.');
  assert.doesNotMatch(generate, /\u63D0\u793A\u8BCD\s*:/, label + ' must not retain the prompt log label.');
  const result = runGenerationHarness(js);
  assert.equal(result.requests.length, 1, label + ' must preserve generation submission.');
  assert.equal(result.requests[0].payload.prompt, result.prompt, label + ' must still send the prompt to the generation API.');
  assert.equal(result.logCalls.some((args) => args.join(' ').includes(result.prompt)), false, label + ' runtime logs must not contain the user prompt.');
  assert.equal(result.logCalls.some((args) => args[0] === '\u751F\u6210\u8BF7\u6C42\u5DF2\u51C6\u5907'), true, label + ' runtime logs must retain a non-sensitive generation status.');
}

console.log('video logging UI assertions passed');
