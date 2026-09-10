import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../static/js/app-all.js', import.meta.url), 'utf8');
function extract(name) {
  const start = source.indexOf('function ' + name + '(');
  assert.ok(start >= 0, name);
  const end = source.indexOf('\nfunction ', start + 1);
  return source.slice(start, end < 0 ? source.length : end);
}
const images = [];
const badge = { hidden: true, textContent: '' };
const context = vm.createContext({
  console, Date, Number, String,
  Image: class {
    constructor() { images.push(this); }
    set src(value) { this.data = value; }
  },
  document: { getElementById: () => badge },
  precisionSourceLoadGeneration: 1,
  precisionEditSourceImageData: 'source-data',
  precisionEditSourceWidth: 1024,
  precisionEditSourceHeight: 1024,
  i18nText: () => 'Original',
});
for (const name of ['precisionEditSessionEntries', 'precisionEditSessionEntry', 'precisionWorkflowHistoryRestoredSession',
  'precisionVersionDimensions', 'precisionVersionDisplayTime', 'precisionVersionInfoText', 'updatePrecisionCanvasImageInfo',
  'appendPrecisionEditVersion', 'appendPrecisionEditImageVersion']) {
  vm.runInContext(extract(name), context);
}
context.precisionEditSession = context.precisionWorkflowHistoryRestoredSession({
  versions: [
    { version_id: 'original', width: 1024, height: 1024, created_at: '2026-09-01T10:00:00Z' },
    { version_id: 'v1', parent_version_id: 'original', created_at: '2026-09-02T11:00:00Z' },
    { version_id: 'v2', parent_version_id: 'v1', width: 800, height: 600 },
  ],
}, { original: 'source-data', v1: 'first-result', v2: 'second-result' });
const session = context.precisionEditSession;
session.selectedVersionId = 'v1';
context.updatePrecisionCanvasImageInfo();
assert.ok(!badge.textContent.includes('1024'), 'Unknown result dimensions must never fall back to the source.');
assert.ok(badge.textContent.includes(context.precisionVersionDisplayTime('2026-09-02T11:00:00Z')));
assert.equal(images.length, 1);
context.updatePrecisionCanvasImageInfo();
assert.equal(images.length, 1, 'Repeated rendering must not restart a pending image load.');
session.selectedVersionId = 'v2';
context.updatePrecisionCanvasImageInfo();
images[0].naturalWidth = 1152;
images[0].naturalHeight = 2048;
images[0].onload();
assert.ok(badge.textContent.includes('800'), 'Late v1 loading must not switch the selected v2 badge.');
assert.ok(!badge.textContent.includes('2026-'), 'Missing result timestamps must remain absent.');
images[1].naturalWidth = 1600;
images[1].naturalHeight = 1200;
images[1].onload();
assert.ok(badge.textContent.includes('1600'), 'Decoded dimensions must override stale projected metadata.');
session.view = 'before';
context.updatePrecisionCanvasImageInfo();
assert.ok(badge.textContent.includes('1152'));
assert.ok(badge.textContent.includes(context.precisionVersionDisplayTime('2026-09-02T11:00:00Z')));
assert.ok(!badge.textContent.includes('1600'));
session.view = 'compare';
context.updatePrecisionCanvasImageInfo();
assert.ok(badge.textContent.includes('1152') && badge.textContent.includes('1600'));
session.selectedVersionId = 'original';
session.view = 'after';
context.updatePrecisionCanvasImageInfo();
assert.ok(badge.textContent.includes('1024'));
assert.ok(badge.textContent.includes(context.precisionVersionDisplayTime('2026-09-01T10:00:00Z')));
assert.equal(context.precisionVersionDisplayTime('2026-09-09 11:12:13'), '2026-09-09 11:12:13', 'Naive dates must keep their local wall-clock meaning.');
assert.equal(context.precisionVersionDisplayTime('2026-02-30 11:12:13'), '');
assert.equal(context.precisionVersionDisplayTime('unknown'), '');
assert.equal(context.precisionVersionDisplayTime(''), '');
assert.equal(context.precisionVersionDisplayTime('2026-09-09T19:12:13+08:00'), context.precisionVersionDisplayTime('2026-09-09T11:12:13Z'));
assert.equal(context.precisionVersionDisplayTime('2026-09-09T11:12:13Z'), (() => {
  const date = new Date('2026-09-09T11:12:13Z');
  const pad = part => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
})(), 'Offset dates must be formatted in the browser timezone.');
context.precisionCutoutAdapterId = () => '';
context.precisionLocalPathUrl = path => path;
context.renderPrecisionEditSession = () => {};
context.schedulePrecisionAutoBaseVersion = () => {};
context.appendPrecisionEditVersion({ success: true, local_path: 'new-result', created_at: '2026-09-09T11:12:13Z', width: 2048, height: 1152 });
assert.equal(session.versions.at(-1).createdAt, '2026-09-09T11:12:13Z', 'Real result timestamps must be passed through.');
assert.equal(session.versions.at(-1).width, 2048);
const registeredAfter = Date.now();
context.appendPrecisionEditVersion({ success: true, local_path: 'new-result-without-time' });
assert.ok(Date.parse(session.versions.at(-1).createdAt) >= registeredAfter, 'New versions without upstream time need a real registration timestamp.');
assert.equal(session.versions.find(version => version.id === 'v2').createdAt, '', 'Restored missing timestamps must not be replaced with registration time.');
console.log('precision version metadata assertions passed');
