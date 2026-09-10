import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../static/js/app-all.js', import.meta.url), 'utf8');
const body = source.split("zoomShell.addEventListener('wheel', function(event) {")[1]
  .split('}, { passive: false, capture: true });')[0];
assert.ok(body);
const calls = [];
const context = vm.createContext({
  precisionEditSourceImageData: 'synthetic',
  precisionViewZoom: 100,
  zoomShell: {},
  precisionCanvasZoomHotspotContains: () => true,
  setPrecisionViewZoom: value => calls.push(value),
});
const wheel = vm.runInContext(`(function(event) {${body}})`, context);
function event(deltaX, deltaY, shiftKey = true) {
  return { deltaX, deltaY, shiftKey, target: null,
    preventDefault() {}, stopPropagation() {} };
}
wheel(event(0, -120));
wheel(event(-120, 0));
wheel(event(0, 120));
wheel(event(120, 0));
assert.deepEqual(calls, [110, 110, 90, 90]);
wheel(event(0, 0));
wheel(event(0, -120, false));
context.precisionEditSourceImageData = null;
wheel(event(-120, 0));
assert.equal(calls.length, 4);
context.precisionEditSourceImageData = 'synthetic';
context.precisionCanvasZoomHotspotContains = () => false;
wheel(event(-120, 0));
assert.equal(calls.length, 4);
console.log('precision wheel axis contracts passed');
