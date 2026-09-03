import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');
const match = source.match(/function generationResponseError\(response\) \{[\s\S]*?\n\}/);
assert.ok(match, 'generationResponseError must remain available as a small standalone helper');

const generationResponseError = vm.runInNewContext('(' + match[0] + ')');

function response(status, body) {
  return {
    status,
    text: () => Promise.resolve(body),
  };
}

await assert.rejects(
  generationResponseError(response(422, JSON.stringify({
    detail: {
      code: 'precision_edit_provider_unsupported',
      message: 'precision_edit requires an explicitly verified OpenAI image-edit model',
    },
  }))),
  (error) => error.message === 'precision_edit requires an explicitly verified OpenAI image-edit model'
    && error.code === 'precision_edit_provider_unsupported',
);

await assert.rejects(
  generationResponseError(response(400, JSON.stringify({ detail: 'plain detail' }))),
  (error) => error.message === 'plain detail' && error.code === undefined,
);

await assert.rejects(
  generationResponseError(response(503, 'not-json')),
  (error) => error.message === 'HTTP 503' && error.code === undefined,
);

assert.match(source, /if \(data\.status === 'failed'\) \{[\s\S]*?stopGenPolling\(\);[\s\S]*?genCurrentGenId = null;[\s\S]*?setGenerationControls\('idle'\);[\s\S]*?showGenerationProgressCloseButton\(true\);/, 'A failed generation must stop polling, release controls, and expose Close.');
assert.match(source, /var failureMessage = generationFailureMessage\(data\);[\s\S]*?ptxt\.textContent = i18nText\('status\.failed_plain'\) \+ ': ' \+ failureMessage/, 'A failed generation must show an explicit failure message.');
assert.match(source, /updateGenerationProgress\(0, i18nText\('status\.failed_plain'\) \+ ': ' \+ failureMessage\)/, 'A failed generation must not expose 100 percent progress.');

console.log('generation error UI regression assertions passed');
