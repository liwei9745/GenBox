// The generate page has two splitters. The horizontal one resizes the left column;
// the vertical one must resize the canvas row against the input row. It used to flex
// .generate-preview, a grandchild of the flex container, so dragging it did nothing.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const js = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'static/css/app.css'), 'utf8');
const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');

assert.match(html, /id="resizeBottom"[^>]+onmousedown="startResize\(event,\s*'bottom'\)"/,
  'The bottom bar must stay wired to the vertical splitter.');

const start = js.indexOf('function startResize(e, direction) {');
assert.ok(start > 0, 'startResize must exist.');
const end = js.indexOf('\n}', start);
const body = js.slice(start, end + 2);

// .generate-center is a column flex container; its children are the canvas row (which
// holds the preview) and the input row. Those are what a vertical drag has to size.
assert.match(body, /center\.querySelector\('\.creator-canvas-row'\)/,
  'The vertical splitter must target the canvas row that holds the preview.');
assert.match(body, /canvasRow\.style\.height = Math\.round\(newTop\) \+ 'px'/,
  'The canvas row must get an explicit height, or its content keeps forcing the old one.');
assert.match(body, /canvasRow\.style\.maxHeight = Math\.round\(newTop\) \+ 'px'/,
  'An explicit maximum stops the CSS basis from fighting the drag.');
assert.match(body, /bottomRow\.style\.height = Math\.round\(newBottom\) \+ 'px'/,
  'The neighbour must be sized too, otherwise it never gives up any space.');
assert.match(body, /var newBottom = total - newTop/,
  'A splitter trades space: what one pane gains, the other loses, so the total is stable.');
assert.match(body, /Math\.max\(220, Math\.min\(startPreviewH \+ dy, total - 210\)\)/,
  'Both panes keep the floor their stylesheet declares, and the drag cannot overflow the column.');
assert.doesNotMatch(body, /preview\.style\.flex = previewFlex/,
  'Flexing the grandchild .generate-preview is the bug that made the bar dead.');
assert.match(body, /left\.style\.width = newW \+ 'px'/,
  'The horizontal splitter must keep resizing the left column.');

// The clamp mirrors the stylesheet floors: 220px for the canvas row, 210px for the
// input row. If either changes, the splitter constants have to change with it.
assert.match(css, /\.creator-input-row\s*\{[\s\S]{0,200}?min-height:\s*210px/,
  'The input row minimum the clamp mirrors must still be 210px.');
assert.match(css, /\.creator-canvas-row\s*\{[\s\S]{0,200}?min-height:\s*220px/,
  'The canvas row minimum the clamp mirrors must still be 220px.');
assert.match(css, /\.generate-center\s*\{[\s\S]{0,200}?flex-direction:\s*column/,
  'The column flex container is the assumption the splitter is built on.');

console.log('generate page splitter contract: OK');
