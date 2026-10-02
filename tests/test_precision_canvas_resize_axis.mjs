// The canvas resize grip sits on the bottom-right corner of the canvas shell and
// advertises a corner resize (44x44, cursor: nwse-resize). Its drag handler must
// therefore follow the axis the pointer actually moved along; driving the size only
// from dx ignored vertical drags, which made a down/up drag look like a sideways jump.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const js = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'static/css/app.css'), 'utf8');

assert.match(css, /\.precision-canvas-resize-handle\s*\{[\s\S]*?cursor:\s*nwse-resize/,
  'The canvas grip must advertise the corner resize it implements.');

const start = js.indexOf('function continuePrecisionCanvasResize(event) {');
assert.ok(start > 0, 'continuePrecisionCanvasResize must exist.');
const end = js.indexOf('\n}', start);
assert.ok(end > start, 'continuePrecisionCanvasResize must be a complete function.');
const source = js.slice(start, end + 2);

// Evaluate the shipped function itself, so this cannot drift from the bundle.
const runner = new Function(
  'precisionCanvasResizeState',
  'applyPrecisionCanvasVisualSize',
  'event',
  source + '\nreturn continuePrecisionCanvasResize(event);',
);

function drag(state, clientX, clientY) {
  const applied = [];
  runner(
    { pointerId: 7, ...state },
    (value) => applied.push(value),
    { pointerId: 7, clientX, clientY, preventDefault() {} },
  );
  return applied[0];
}

const base = { startX: 100, startY: 100, startWidth: 400 };
assert.equal(drag(base, 100, 140), 440, 'A straight downward drag must grow the canvas.');
assert.equal(drag(base, 100, 60), 360, 'A straight upward drag must shrink the canvas.');
assert.equal(drag(base, 140, 100), 440, 'A rightward drag must keep growing the canvas.');
assert.equal(drag(base, 60, 100), 360, 'A leftward drag must keep shrinking the canvas.');
assert.equal(drag(base, 150, 130), 450, 'With dx dominant the horizontal delta wins.');
assert.equal(drag(base, 120, 150), 450, 'With dy dominant the vertical delta wins.');
assert.equal(drag(base, 100, 100), 400, 'A motionless pointer must not resize anything.');

// The same class of bug - a handle whose axis does not match its affordance - is
// guarded for the rest of the family too. (Audited 2026-10-02: the corner grip was
// the only mismatch; every other handle already followed the right axis.)
assert.match(js, /function continuePrecisionCanvasVerticalResize\(event\) \{[\s\S]{0,400}?event\.clientY/,
  'A row-resize handle must follow the Y axis.');
assert.match(js, /function continuePrecisionInspectorResize\(event\) \{[\s\S]{0,400}?event\.clientX/,
  'A col-resize handle must follow the X axis.');
assert.match(js, /function continuePrecisionCutoutProfessionalDockResize\(event\) \{[\s\S]{0,400}?event\.clientX/,
  'The cutout dock separator must follow the X axis.');
assert.match(css, /\.precision-inspector-resize-handle[\s\S]{0,600}?cursor:\s*col-resize/,
  'The inspector separator must advertise a column resize.');
assert.match(css, /\.precision-canvas-vertical-resize-handle\s*\{[\s\S]{0,600}?cursor:\s*row-resize/,
  'The canvas bottom bar must advertise a row resize.');

// The canvas limit must be measured against the real space above the app status bar.
// A viewport-based allowance let the shell grow under the status bar, where its
// bottom-right grip stopped receiving pointer events (elementFromPoint returned the
// status bar instead of the grip).
assert.match(js, /function precisionCanvasAvailableHeight\(shell\) \{/,
  'The canvas limit needs a measurement of the space that actually exists.');
assert.match(js, /document\.querySelector\('\.status-bar'\)/,
  'That boundary is the app status bar.');
assert.match(js, /var availableHeight = precisionCanvasAvailableHeight\(shell\);/,
  'precisionCanvasResizeLimits must use it.');
assert.match(js, /var maxHeight = availableHeight > 0 \? Math\.max\(240, Math\.min\(760, availableHeight\)\) : 760;/,
  'The limit must come from that measurement, not from the viewport.');

console.log('precision canvas resize axis: OK');
