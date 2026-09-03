import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');
const i18n = fs.readFileSync(path.join(root, 'static/js/i18n.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'static/css/app.css'), 'utf8');

function expect(condition, message) {
  if (!condition) throw new Error(message);
}

expect(html.includes('id="btnStopGen"'), 'A dedicated stop-generation button must exist.');
expect(html.includes('onclick="cancelCurrentGeneration()"'), 'The stop button must call cancellation directly.');
expect(js.includes("function setGenerationControls(state)"), 'Generation controls need explicit state management.');
expect(js.includes("setGenerationControls('generating')"), 'The stop button must become visible after a generation id is received.');
expect(js.includes("setGenerationControls('cancelling')"), 'The stop button must disable while cancellation is pending.');
expect(js.includes("setGenerationControls('idle')"), 'Controls must recover after completion, cancellation, or failure.');
expect(js.includes("'/api/generate/cancel/' + encodeURIComponent(cancelGenId)"), 'Cancellation must use the captured current task id.');
expect(i18n.includes('"creator.stop_generation"'), 'Stop-generation text must be translated.');
expect(css.includes('.creator-generate-action #btnStopGen'), 'The stop button needs dedicated stable layout rules.');
expect(html.includes('id="generationProgressBar"') && html.includes('role="progressbar"') && html.includes('aria-valuenow="0"') && html.includes('aria-valuetext="0%"'), 'The main progress bar needs accessible value semantics.');
expect(js.includes('<div role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="') && js.includes('aria-valuetext="' + "' + escAttr(statusText) + '"), 'Per-task progress bars need accessible current values and status text.');
expect(js.includes("var unsuccessfulTerminal = ['failed', 'error', 'cancelled', 'timeout', 'interrupted']") && js.includes('var accessibleProgress = unsuccessfulTerminal ? 0'), 'Failed and cancelled subtasks must not claim 100 percent progress.');
expect(js.includes('resolveCancellationTerminalPayload(cancelGenId, cancelData)') && js.includes('finishGenerationTerminalStatus(terminalData, cancelledPrecisionTask)'), 'Cancellation must resolve the real terminal status through the shared completion path.');
expect(!js.includes('/api/generation/'), 'Generation polling and terminal hydration must never probe the nonexistent legacy route.');
expect(js.includes("_authFetch('/api/generate/status/' + encodeURIComponent(genId))"), 'Generation polling and terminal hydration must use the real status route.');

function extractFunction(name) {
  const marker = 'function ' + name + '(';
  const start = js.indexOf(marker);
  expect(start !== -1, 'Missing function: ' + name);
  const bodyStart = js.indexOf('{', start);
  let depth = 0;
  let quote = '';
  let escaped = false;
  for (let index = bodyStart; index < js.length; index += 1) {
    const char = js[index];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === '\\\\') escaped = true;
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

async function runCancellationRace(cancelStatus) {
  const calls = {
    controls: [], monitor: [], status: [], results: [], versions: [],
    progress: [], close: [], fetchStatus: 0, stopped: 0, gallery: 0,
  };
  const nodes = {
    progressText: { textContent: '' },
    elapsedSeconds: { textContent: '' },
    progressFill: {},
    genLogWrap: {},
    genLogCount: { textContent: '' },
  };
  const completedResult = { success: true, local_path: 'gallery/completed.png' };
  const fullPayload = cancelStatus === 'completed' ? {
    status: 'completed',
    elapsed_seconds: 2.5,
    provider_states: { provider_0: { status: 'completed', log: ['completed final'], result: completedResult } },
    results: { provider_0: completedResult },
    group_timings: { provider: { total: 2.5, images: [] } },
  } : cancelStatus === 'failed' ? {
    status: 'failed',
    error: 'provider failed visibly',
    provider_states: { provider_0: { status: 'failed', log: ['failed final'], result: { success: false, error: 'provider failed visibly' } } },
    results: {},
    group_timings: { provider: { total: 1.5, images: [] } },
  } : {
    status: 'cancelled',
    elapsed_seconds: 1.25,
    provider_states: { provider_0: { status: 'cancelled', log: ['cancelled final'] } },
    results: {},
    group_timings: { provider: { total: 1.25, images: [] } },
  };
  const context = vm.createContext({
    Promise, Object, String, Number, Array, Error, encodeURIComponent,
    document: { getElementById: (id) => nodes[id] || null },
    window: {},
    currentMode: 'precision_edit',
    genCurrentGenId: 'race-task',
    genCancelRequested: false,
    genIsPrecisionTask: true,
    precisionSourceLoadGeneration: 1,
    precisionTaskSourceGeneration: 1,
    precisionEditSession: {
      source: { id: 'original', data: 'data:image/png;base64,c291cmNl' },
      versions: [{ id: 'original', label: '0', data: 'data:image/png;base64,c291cmNl', parentId: null }],
      selectedVersionId: 'original',
      baseVersionId: 'original',
      taskBaseVersionId: 'original',
      taskSourceGeneration: 1,
      taskId: 'race-task',
      view: 'after',
    },
    precisionTaskMonitorData: {
      status: 'generating',
      progress: 73,
      provider_states: {
        provider_0: { status: 'generating', log: ['stale running log'] },
        provider_1: { status: 'queued', log: ['stale queued log'] },
      },
    },
    currentResults: { stale: { success: true, local_path: 'gallery/stale.png' } },
    currentGroupTimings: { stale: {} },
    _authFetch: async (url) => {
      expect(url === '/api/generate/cancel/race-task', 'Cancellation must target the captured generation id.');
      return { ok: true, json: async () => ({ ok: true, status: cancelStatus }) };
    },
    fetchGenerationStatus: async (genId) => {
      expect(genId === 'race-task', 'Terminal status lookup must use the captured generation id.');
      calls.fetchStatus += 1;
      return fullPayload;
    },
    stopGenPolling: () => { calls.stopped += 1; },
    setGenerationControls: (state) => calls.controls.push(state),
    updatePrecisionTaskMonitor: (data) => calls.monitor.push(data),
    updateGenerationProgress: (...args) => calls.progress.push(args),
    showGenerationProgressCloseButton: (show) => calls.close.push(show),
    setStatus: (status) => calls.status.push(status),
    showResults: (results) => calls.results.push(results),
    appendPrecisionEditVersion: (result) => calls.versions.push(result),
    loadGallery: () => { calls.gallery += 1; },
    showEnhanceResult: () => {},
    i18nText: (key) => key,
  });
  const functions = [
    'precisionDisplaySize',
    'precisionDisplaySizeFromFields',
    'precisionOutputSizeNoticeFromRecord',
    'precisionOutputSizeNotices',
    'generationFailureMessage',
    'finishGenerationTerminalStatus',
    'resolveCancellationTerminalPayload',
    'cancelCurrentGeneration',
  ].map(extractFunction).join('\n');
  vm.runInContext(functions, context);
  await vm.runInContext('cancelCurrentGeneration()', context);
  const state = vm.runInContext('({ genCurrentGenId, genCancelRequested, currentResults, currentGroupTimings })', context);
  return { calls, nodes, state };
}

async function runOrdinarySuccessThenFailure() {
  const calls = { results: [], status: [], controls: [], progress: [], close: [] };
  const nodes = {
    progressText: { textContent: '' },
    elapsedSeconds: { textContent: '' },
    progressFill: {},
    genLogWrap: {},
    genLogCount: { textContent: '' },
  };
  const successfulResult = { success: true, local_path: 'gallery/previous-success.png' };
  const context = vm.createContext({
    Promise, Object, String, Number, Array, Error,
    document: { getElementById: (id) => nodes[id] || null },
    currentMode: 't2i',
    genCurrentGenId: 'ordinary-task',
    genCancelRequested: false,
    currentResults: {},
    currentGroupTimings: {},
    stopGenPolling: () => {},
    setGenerationControls: (state) => calls.controls.push(state),
    updateGenerationProgress: (...args) => calls.progress.push(args),
    showGenerationProgressCloseButton: (show) => calls.close.push(show),
    setStatus: (status) => calls.status.push(status),
    showResults: (results) => calls.results.push(results),
    loadGallery: () => {},
    generationFailureMessage: (data) => data.error || 'failed',
    i18nText: (key) => key,
  });
  const finish = extractFunction('finishGenerationTerminalStatus');
  vm.runInContext(finish, context);

  vm.runInContext(`finishGenerationTerminalStatus(${JSON.stringify({
    status: 'completed',
    elapsed_seconds: 2.5,
    results: { provider_0: successfulResult },
    group_timings: { provider: { total: 2.5, images: [] } },
    provider_states: { provider_0: { status: 'completed', result: successfulResult } },
  })}, false)`, context);
  vm.runInContext(`finishGenerationTerminalStatus(${JSON.stringify({
    status: 'failed',
    error: 'all providers failed',
    results: {},
    group_timings: {},
    provider_states: { provider_0: { status: 'failed', error: 'all providers failed' } },
  })}, false)`, context);

  const state = vm.runInContext('({ currentResults, currentGroupTimings })', context);
  return { calls, nodes, state };
}

const cancelled = await runCancellationRace('cancelled');
assert.equal(cancelled.calls.fetchStatus, 1, 'A compact cancelled response must fetch the complete task payload.');
assert.equal(cancelled.calls.monitor.at(-1).status, 'cancelled', 'Precision monitor must publish cancelled only for a real cancelled response.');
assert.equal(cancelled.calls.monitor.at(-1).provider_states.provider_0.status, 'cancelled', 'Cancellation must expose the real provider terminal state.');
assert.deepEqual(Object.keys(cancelled.calls.monitor.at(-1).provider_states), ['provider_0'], 'Cancellation must discard stale queued provider states.');
assert.deepEqual(cancelled.calls.monitor.at(-1).provider_states.provider_0.log, ['cancelled final'], 'Cancellation must replace stale running logs with the complete terminal log.');
assert.equal(cancelled.calls.monitor.at(-1).progress, undefined, 'Cancellation must not retain stale running progress.');
assert.deepEqual(cancelled.calls.controls, ['cancelling', 'idle']);
assert.equal(cancelled.calls.status.at(-1), 'status.cancelled');
assert.equal(cancelled.calls.results.length, 0, 'Cancellation must not invent completed results.');
assert.deepEqual(cancelled.state.currentResults, {}, 'Cancellation must clear stale global results.');
assert.equal(cancelled.state.currentGroupTimings.provider.total, 1.25, 'Cancellation must retain complete terminal timings.');
assert.equal(cancelled.state.genCurrentGenId, null);
assert.equal(cancelled.state.genCancelRequested, false);

const completed = await runCancellationRace('completed');
assert.equal(completed.calls.fetchStatus, 1, 'A compact completed cancellation response must fetch the complete task payload.');
assert.equal(completed.calls.monitor.at(-1).status, 'completed', 'Precision monitor must retain the completed race result.');
assert.equal(completed.calls.results.length, 1, 'Completed race results must use the normal result renderer.');
assert.equal(completed.calls.results[0].provider_0.local_path, 'gallery/completed.png');
assert.equal(completed.calls.versions[0].local_path, 'gallery/completed.png', 'Completed precision output must remain available as a version.');
assert.equal(completed.state.currentResults.provider_0.local_path, 'gallery/completed.png', 'Global results must retain the completed payload.');
assert.ok(!completed.calls.status.includes('status.cancelled'), 'A completed race must never publish cancelled copy.');
assert.equal(completed.state.genCurrentGenId, null);
assert.equal(completed.state.genCancelRequested, false);

const failed = await runCancellationRace('failed');
assert.equal(failed.calls.fetchStatus, 1, 'A compact failed cancellation response must fetch the complete task payload.');
assert.equal(failed.calls.monitor.at(-1).status, 'failed', 'Precision monitor must retain the failed race result.');
assert.equal(failed.calls.results.length, 0, 'A failed race must not render a fake completed result.');
assert.ok(failed.calls.status.at(-1).includes('provider failed visibly'), 'The normal failure path must expose the backend failure.');
assert.ok(!failed.calls.status.includes('status.cancelled'), 'A failed race must never publish cancelled copy.');
assert.equal(failed.nodes.progressText.textContent, 'status.failed_plain: provider failed visibly');
assert.equal(failed.state.genCurrentGenId, null);
assert.equal(failed.state.genCancelRequested, false);

const ordinaryFailure = await runOrdinarySuccessThenFailure();
assert.equal(ordinaryFailure.calls.results.length, 1, 'The ordinary success must render its result before the failure regression step.');
assert.equal(Object.keys(ordinaryFailure.state.currentResults).length, 0, 'An ordinary all-failed terminal payload must clear the previous task result.');
assert.equal(Object.keys(ordinaryFailure.state.currentGroupTimings).length, 0, 'An ordinary all-failed terminal payload must clear the previous task timings.');
assert.equal(ordinaryFailure.calls.status.at(-1), 'status.failed_plain: all providers failed');
assert.equal(ordinaryFailure.nodes.progressText.textContent, 'status.failed_plain: all providers failed');

console.log('stop-generation UI static assertions passed');
