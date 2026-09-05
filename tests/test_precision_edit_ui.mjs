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

expect(html.includes('id="subTabPrecisionEdit"'), 'Precision edit needs an independent visible tab.');
expect(html.includes('id="panelPrecisionEdit"'), 'Precision edit needs an independent panel.');
expect(js.includes("precision_edit"), 'Routing must recognize precision_edit.');
expect(js.includes("mode !== 'precision_edit'"), 'Mode switching must independently show the precision panel.');

expect(js.includes('function sendToPrecisionEdit(e)'), 'Generated images need a precision-edit transfer action.');
expect(js.includes('loadPrecisionEditSourceImage'), 'Transfer must load a generated image into the annotation canvas.');
expect(js.includes("surface.style.aspectRatio = width + ' / ' + height"), 'Canvas surface must follow the source image aspect ratio.');
expect(js.includes("document.getElementById('precisionAnnotationCanvas')"), 'Precision interactions must bind the static annotation canvas.');
expect(js.includes("type: object.type === 'rect' ? 'rectangle' : 'ellipse'") && js.includes('width: Math.abs(x2 - x1)'), 'Rectangle and ellipse annotations must share the backend box geometry contract.');
expect(html.includes('precisionEditProviderEndpoint'), 'Precision edit needs an endpoint selector.');
expect(js.includes('data-cap="precision_edit"'), 'Provider settings need an explicit precision capability control.');
expect(html.includes('btnPrecisionAuthorizeModel'), 'Precision edit needs an explicit model authorization action.');
expect(html.includes('precisionEditGptImage2Compatibility') && html.includes('btnPrecisionRevokeModel'), 'Precision edit needs an explicit GPT Image 2 compatibility choice and revoke action.');
expect(html.includes('btnPrecisionConfirmResizeSize') && html.includes('btnPrecisionRevokeResizeSize'), 'Precision resize needs explicit confirm and revoke actions for the current target size.');
expect(js.includes('/precision-capability'), 'Precision model authorization must use the backend capability endpoint.');
expect(/id="btnPrecisionAuthorizeModel"[^>]*disabled/.test(html), 'Precision authorization must start disabled before provider data is ready.');
expect(/id="precisionEditProviderEndpoint"[^>]*disabled/.test(html) && /id="precisionEditProviderModel"[^>]*disabled/.test(html), 'Precision model selectors must start disabled before provider data is ready.');
const authorizationState = js.slice(js.indexOf('function getPrecisionEditModelAuthorizationState'), js.indexOf('function renderPrecisionEditModelPicker'));
const authorizationFlow = js.slice(js.indexOf('function authorizePrecisionEditModel'), js.indexOf('// ═══════════════════════════════════════════════════════════════════', js.indexOf('function authorizePrecisionEditModel')));
expect(authorizationState.includes('precisionEditModelPickerReady') && authorizationState.includes('endpointOptionCurrent') && authorizationState.includes('modelOptionCurrent'), 'Authorization readiness must validate the current rendered endpoint and model options.');
expect(authorizationState.includes("valueProviderId === providerId") && authorizationState.includes("provider.endpoint_type === 'openai'"), 'Authorization readiness must reject stale provider/model pairs and non-OpenAI endpoints.');
expect(authorizationState.includes('compatibilityResolution.sizeDeclarationValid') && authorizationState.includes('compatibilityActive'), 'Compatibility authorization must require an explicit canonical capability and expose persisted mapping state.');
expect(extractFunction('precisionProviderModelRecords').includes('hasCapabilityRecord && !resolution.structureValid'), 'Newly discovered models without capability metadata must remain visible for explicit user confirmation, while malformed persisted records fail closed.');
expect(authorizationFlow.indexOf('if (!state.canAuthorize) return;') < authorizationFlow.indexOf('confirm(') && authorizationFlow.indexOf('confirm(') < authorizationFlow.indexOf("_authFetch('/api/providers/"), 'Authorization must fail closed before confirmation and provider submission.');
expect(authorizationFlow.includes('payload.compatibility_profile = PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE') && authorizationFlow.includes('function revokePrecisionEditModel'), 'Compatibility confirmation and revocation must use the persisted backend capability route.');
expect(js.includes('precisionEditAuthorizationPending = true;') && js.includes("authorize.setAttribute('aria-busy', precisionEditAuthorizationPending ? 'true' : 'false')"), 'Authorization controls must stay disabled while confirmation is being saved.');
expect(!js.includes("document.getElementById('precisionEditCanvas')"), 'Legacy precision canvas bindings must not remain.');
expect(js.includes("switchSubTab('precision_edit')"), 'Transfer must enter precision_edit mode.');
expect(js.includes("setCreatorWorkbenchMode('image', 'precision')"), 'Precision entry must atomically activate its workbench.');
expect(js.includes("precision-preview-collapsed"), 'Collapsed preview must participate in the layout state model.');
expect(!js.includes("function sendToImageToImage(e) { return sendToPrecisionEdit(e); }"), 'I2I must remain a separate workflow.');

const optionalAuthorizationNodes = {
  btnPrecisionAuthorizeModel: { style: {} },
  btnPrecisionRevokeModel: { style: {}, focus() {} },
  precisionEditCompatibilityOption: { style: {} },
  precisionEditGptImage2Compatibility: { checked: false },
};
const optionalAuthorizationContext = vm.createContext({
  document: { getElementById: (id) => optionalAuthorizationNodes[id] || null },
});
vm.runInContext([
  'var allProviders = [];',
  'var precisionEditModelPickerReady = false;',
  'var precisionEditAuthorizationPending = false;',
  extractFunction('getPrecisionEditModelAuthorizationState'),
  extractFunction('updatePrecisionEditAuthorizationControl'),
].join('\n'), optionalAuthorizationContext);
assert.doesNotThrow(
  () => optionalAuthorizationContext.updatePrecisionEditAuthorizationControl(),
  'Authorization controls must no-op safely when the Precision Edit panel is absent or exposes only partial DOM nodes.',
);
assert.equal(optionalAuthorizationNodes.btnPrecisionAuthorizeModel.disabled, true);
assert.equal(optionalAuthorizationNodes.btnPrecisionRevokeModel.disabled, true);
assert.equal(optionalAuthorizationNodes.precisionEditGptImage2Compatibility.disabled, true);

for (const id of ['precisionToolSelect', 'precisionToolEllipse', 'precisionToolArrow', 'precisionToolRect', 'precisionToolBrush', 'precisionToolEraser', 'precisionToolText', 'btnPrecisionUndo', 'btnPrecisionRedo', 'btnPrecisionClear']) {
  expect(html.includes('id="' + id + '"') || js.includes('id="' + id + '"'), 'Missing annotation control: ' + id);
}
const selectToolIndex = html.indexOf('id="precisionToolSelect"');
const selectToolMarkup = html.slice(Math.max(0, selectToolIndex - 120), html.indexOf('</button>', selectToolIndex) + 9);
const ellipseToolIndex = html.indexOf('id="precisionToolEllipse"');
const ellipseToolMarkup = html.slice(Math.max(0, ellipseToolIndex - 120), html.indexOf('</button>', ellipseToolIndex) + 9);
expect(selectToolMarkup.includes('btn-secondary') && selectToolMarkup.includes('active') && selectToolMarkup.includes('aria-pressed="true"'), 'The explicit Select/Move tool must be the visible default.');
expect(ellipseToolMarkup.includes('btn-ghost') && ellipseToolMarkup.includes('aria-pressed="false"'), 'Drawing tools must not appear selected before the user chooses them.');
for (const fn of ['setPrecisionEditTool', 'undoPrecisionEdit', 'redoPrecisionEdit', 'clearPrecisionEdit', 'buildPrecisionEditAnnotationData']) {
  expect(js.includes('function ' + fn), 'Missing annotation function: ' + fn);
}
expect(js.includes("var PRECISION_ANNOTATION_CONTRACT = 'genbox-annotation-v3'"), 'Annotation contract must use genbox-annotation-v3.');
expect(js.includes("type: object.type === 'rect' ? 'rectangle' : 'ellipse'") && js.includes("type: 'brush', points:"), 'Ellipse and brush annotations must use the v3 geometry contract.');
expect(js.includes("['select', 'ellipse', 'arrow', 'rect', 'brush', 'eraser', 'text']") && js.includes("precisionEditTool = 'select'"), 'V4 tools must expose an explicit selection tool and use it as the safe default.');
expect(js.includes('function erasePrecisionBrushAt') && js.includes("precisionEditTool === 'eraser'"), 'Brush selection needs a history-aware eraser.');
expect(html.includes('id="precisionViewZoom"') && html.includes('min="50" max="200" step="10"') && js.includes('function setPrecisionViewZoom') && js.includes('function fitPrecisionCanvasToWindow'), 'Canvas needs bounded view-only zoom controls.');
expect(js.includes("if (!event.ctrlKey || !precisionEditSourceImageData) return;") && js.includes('event.deltaY < 0 ? 10 : -10'), 'Ctrl+wheel must adjust only a loaded canvas view zoom in fixed steps.');
expect(html.includes("startPrecisionAiErase('people')") && html.includes("startPrecisionAiErase('watermark')") && js.includes('precisionEditPendingInstruction = i18nText'), 'AI removal presets must create per-region instructions.');
expect(js.includes("coordinate_space: 'normalized-0-1'"), 'Annotation coordinates must be normalized.');
expect(js.includes('source_width: precisionEditSourceWidth'), 'Serialization must include source width.');
expect(js.includes('source_height: precisionEditSourceHeight'), 'Serialization must include source height.');
expect(js.includes('objects: precisionEditObjects.map(normalizePrecisionEditObject)'), 'Serialization must include normalized objects.');
expect(!js.includes("setPrecisionEditTool('select');\n  updatePrecisionEditControls();"), 'Panel refresh must not reset the selected annotation tool.');
expect(js.includes('var draft = precisionEditClone([precisionEditDraftObject])[0]'), 'Pointer completion must preserve the internal canvas object shape.');
expect(js.includes("canvas.addEventListener('lostpointercapture', endPrecisionEditPointer)"), 'Lost pointer capture must safely finish an active annotation.');
const annotationTransformSource = js.slice(js.indexOf('function precisionEditIsBoxShape'), js.indexOf('function erasePrecisionBrushAt'));
expect(annotationTransformSource.includes("object.type === 'rect' || object.type === 'ellipse'"), 'Canvas transforms must be limited to rectangle and ellipse shapes.');
expect(annotationTransformSource.includes('normalizedX * normalizedX + normalizedY * normalizedY <= 1'), 'Ellipse selection must use the ellipse equation instead of its rectangular corner area.');
expect(annotationTransformSource.includes('for (var index = precisionEditObjects.length - 1; index >= 0; index--)'), 'Shape selection must prefer the visually topmost object.');
expect(annotationTransformSource.includes("event.pointerType === 'touch' ? PRECISION_HANDLE_TOUCH_PX : PRECISION_HANDLE_MOUSE_PX"), 'Corner handles need a larger touch hit target.');
expect(annotationTransformSource.includes('!event.altKey') && annotationTransformSource.includes("handle ? 'resize' : 'move'"), 'Rectangle and ellipse pointerdown must support selection/resize with Alt forcing a new draft.');
expect(annotationTransformSource.includes('var clampedDx = Math.max(-bounds.left, Math.min(1 - bounds.right, dx))'), 'Moving a shape must clamp its whole box without changing its dimensions.');
expect(annotationTransformSource.includes('PRECISION_ANNOTATION_MIN_SIZE'), 'Shape resize must enforce the normalized minimum box size.');
expect(js.includes('if (selected && precisionEditIsBoxShape(object)) drawPrecisionEditHandles'), 'Selected box shapes must draw visible corner handles.');
expect(annotationTransformSource.includes("handles['point-' + index]"), 'Selected brush paths must expose every normalized point as a touchable control node.');
expect(annotationTransformSource.includes('function precisionEditBrushSegmentIndex') && annotationTransformSource.includes('function beginPrecisionEditBrushNode'), 'Brush paths must support inserting a control node from a pointer hit on an existing segment.');
expect(annotationTransformSource.includes("mode === 'node' && originObject.type === 'brush'") && annotationTransformSource.includes("selectedBrushHandle && selectedObject.points.length > 2"), 'Brush nodes must support pointer movement and eraser-driven deletion while retaining a valid path.');
const fullscreenSource = extractFunction('syncPrecisionFullscreenState');
expect(extractFunction('togglePrecisionCompareFullscreen').includes('document.fullscreenElement === panel') && extractFunction('togglePrecisionCompareFullscreen').includes('panel.requestFullscreen'), 'Fullscreen toggles must request only the complete precision panel.');
expect(fullscreenSource.includes("creator.precision_exit_fullscreen_label") && fullscreenSource.includes("button.setAttribute('title'") && fullscreenSource.includes("button.setAttribute('aria-label'"), 'Fullscreen state must synchronize the button text, tooltip, and accessible label.');
const precisionExportSource = js.slice(js.indexOf('function exportPrecisionEditAnnotationImage'), js.indexOf('function buildPrecisionEditAnnotationData'));
expect(precisionExportSource.includes('drawPrecisionEditObject(context, object, output.width, output.height, false)'), 'Export must omit selection handles from the annotation image.');
expect(js.includes('color: style.color, strokeWidth: style.strokeWidth'), 'New annotations must retain the selected color and line width.');
expect(html.includes('creator.precision_edit_color_short'), 'Color control needs a compact visible label.');
expect(!html.includes('class="precision-edit-intro"'), 'Precision guidance must be merged into the main workbench header.');
expect(!html.includes('class="precision-provider-status"'), 'Model guidance must not use a separate status card.');
expect(html.includes('class="precision-empty-actions"'), 'Upload and gallery actions must live in the empty canvas state.');

for (const field of ['annotation_image_data', 'annotation_contract', 'annotations']) {
  expect(js.includes(field), 'Precision request is missing ' + field + '.');
}
const precisionReadinessSource = extractFunction('getPrecisionEditReadiness');
expect(precisionReadinessSource.includes("precisionEditSizeMode !== 'resize'") && precisionReadinessSource.includes('pureResize: true') && precisionReadinessSource.includes('getPrecisionSizeRequest()'), 'No-annotation precision submit must be limited to a validated pure resize branch.');
const precisionPayloadStart = js.lastIndexOf("} else if (currentMode === 'precision_edit') {", js.indexOf('// The source is never replaced locally'));
const precisionSubmitSource = js.slice(precisionPayloadStart, js.indexOf("} else if (currentMode === 'inpaint') {", precisionPayloadStart));
expect(precisionSubmitSource.includes('applyPrecisionEditPayload(payload,') && precisionSubmitSource.includes('payload.provider_settings = {}'), 'Precision submit must use the shared payload builder and still attach explicit model settings.');
expect(precisionSubmitSource.includes('annotations: precisionAnnotationData ? precisionAnnotationData.objects : []') && !precisionSubmitSource.includes('annotationData: precisionAnnotationData') && !precisionSubmitSource.includes('annotation_objects: currentMode === \'precision_edit\' && precisionAnnotationData ? precisionAnnotationData.objects : []'), 'Precision submit must pass only the allowed annotation array into the shared payload builder.');
expect(js.includes('function serializePrecisionAnnotationForRequest') && js.includes('function serializePrecisionAnnotationsForRequest'), 'Precision request payloads need a dedicated canonical annotation serializer.');
expect(js.includes("annotations: currentMode === 'precision_edit' && payload.annotations ? precisionEditClone(payload.annotations) : []"), 'Precision retry context must store the canonical request annotations, not local UI objects.');
const pureResizeForbiddenPayloadFields = [
  'annotation_image_data',
  'annotation_contract',
  'annotation_data',
  'annotation_objects',
  'annotations',
  'image_data_list',
  'mask',
  'mask_data',
  'mask_contract',
  'upscale',
  'upscale_to',
  'upscale_method',
  'upscale_ratio',
  'precision_aspect_ratio_constraint',
];
const richUiRequestAnnotations = [
  { id: 'arrow-a', type: 'arrow', label: '1', instruction: 'Extend the horizon.', x: 0.1, y: 0.2, x2: 0.4, y2: 0.3, color: '#ff0000', strokeWidth: 9 },
  { id: 'rect-a', type: 'rect', label: '2', instruction: 'Preserve the sign.', x: 0.75, y: 0.8, x2: 0.25, y2: 0.4, color: '#00ff00', strokeWidth: 8 },
  { id: 'ellipse-a', type: 'ellipse', label: '3', instruction: 'Soften the glow.', x: 0.375, y: 0.25, x2: 0.625, y2: 0.5, color: '#0000ff', strokeWidth: 7 },
  { id: 'brush-a', type: 'brush', label: '4', instruction: 'Clean this edge.', points: [{ x: 0.11, y: 0.12 }, { x: 0.13, y: 0.14 }], color: '#123456', strokeWidth: 12 },
  { id: 'text-a', type: 'text', label: '5', text: 'KEEP', instruction: '', x: 0.51, y: 0.52, color: '#654321', strokeWidth: 3, fontSize: 48 },
];
const canonicalRequestAnnotations = [
  { type: 'arrow', label: 1, instruction: 'Extend the horizon.', x1: 0.1, y1: 0.2, x2: 0.4, y2: 0.3 },
  { type: 'rectangle', label: 2, instruction: 'Preserve the sign.', x: 0.25, y: 0.4, width: 0.5, height: 0.4 },
  { type: 'ellipse', label: 3, instruction: 'Soften the glow.', x: 0.375, y: 0.25, width: 0.25, height: 0.25 },
  { type: 'brush', label: 4, instruction: 'Clean this edge.', points: [{ x: 0.11, y: 0.12 }, { x: 0.13, y: 0.14 }] },
  { type: 'text', label: 5, text: 'KEEP', x: 0.51, y: 0.52 },
];
const canonicalRectangleAnnotation = { type: 'rectangle', label: 1, instruction: 'Preserve the foreground.', x: 0.1, y: 0.2, width: 0.6, height: 0.6000000000000001 };
function assertExactAnnotation(annotation, expected, label) {
  assert.deepEqual(Object.keys(annotation).sort(), Object.keys(expected).sort(), `${label} must contain exactly the backend V3 fields.`);
  assert.deepEqual(annotation, expected, `${label} must serialize to the backend-canonical V3 shape.`);
}
function assertPureResizePayload(payload, label, expectedPolicy = 'strict') {
  for (const field of pureResizeForbiddenPayloadFields) {
    assert.equal(Object.prototype.hasOwnProperty.call(payload, field), false, `${label} must omit ${field} entirely, not send an empty or null substitute.`);
  }
  assert.equal(payload.mode, 'precision_edit', `${label} must retain precision edit mode.`);
  assert.equal(payload.operation, 'precision_edit', `${label} must carry the precision operation.`);
  assert.equal(payload.image_data, 'data:image/png;base64,c291cmNl', `${label} must keep the single base image.`);
  assert.equal(payload.precision_size_mode, 'resize', `${label} must use the explicit resize envelope.`);
  assert.equal(payload.precision_target_size, '1536x864', `${label} must retain the target size.`);
  assert.equal(payload.precision_resize_prompt, 'Extend the scene naturally.', `${label} must retain composition guidance.`);
  assert.equal(payload.precision_output_size_policy, expectedPolicy, `${label} must carry the expected output-size policy.`);
  assert.equal(payload.precision_strategy, 'standard', `${label} must default to the standard strategy.`);
  assert.equal(payload.precision_selection_mode, 'annotation', `${label} must default to annotation semantics.`);
  assert.equal(Object.prototype.hasOwnProperty.call(payload, 'precision_selection_feather'), false, `${label} must not send selection feather outside local selection mode.`);
  assert.ok(!payload.precision_resize_prompt.includes('16:9 aspect ratio'), `${label} must not concatenate the aspect constraint into the prompt text.`);
  assert.equal(Object.prototype.hasOwnProperty.call(payload, 'size'), false, `${label} must not fall back to the generic size field.`);
}
function assertAnnotatedPayload(payload, label, expectedSizeMode, expectedPolicy = 'strict', expectedAnnotations = canonicalRequestAnnotations) {
  for (const field of ['annotation_data', 'annotation_objects', 'image_data_list', 'mask', 'mask_data', 'mask_contract', 'upscale', 'upscale_to', 'upscale_method', 'upscale_ratio', 'precision_aspect_ratio_constraint']) {
    assert.equal(Object.prototype.hasOwnProperty.call(payload, field), false, `${label} must omit ${field} entirely, not send an empty or null substitute.`);
  }
  assert.equal(payload.mode, 'precision_edit', `${label} must retain precision edit mode.`);
  assert.equal(payload.operation, 'precision_edit', `${label} must carry the precision operation.`);
  assert.equal(payload.image_data, 'data:image/png;base64,c291cmNl', `${label} must keep the single base image.`);
  assert.equal(payload.precision_size_mode, expectedSizeMode, `${label} must preserve the expected precision size mode.`);
  assert.equal(payload.annotation_image_data, 'data:image/png;base64,YW5ub3RhdGlvbg==', `${label} must keep the annotated image.`);
  assert.equal(payload.annotation_contract, 'genbox-annotation-v3', `${label} must keep the annotation contract.`);
  assert.equal(payload.precision_strategy, 'standard', `${label} must default to the standard strategy.`);
  assert.equal(payload.precision_selection_mode, 'annotation', `${label} must default to annotation semantics.`);
  assert.ok(Array.isArray(payload.annotations) && payload.annotations.length === expectedAnnotations.length, `${label} must carry only the visible annotations array.`);
  expectedAnnotations.forEach((expected, index) => assertExactAnnotation(payload.annotations[index], expected, `${label} annotations[${index}]`));
  if (expectedSizeMode === 'resize') {
    assert.equal(payload.precision_target_size, '1536x864', `${label} must retain the target size.`);
    assert.equal(payload.precision_resize_prompt, 'Extend the scene naturally.', `${label} must retain composition guidance.`);
    assert.equal(payload.precision_output_size_policy, expectedPolicy, `${label} must carry the expected output-size policy.`);
    assert.ok(!payload.precision_resize_prompt.includes('16:9 aspect ratio'), `${label} must not concatenate the aspect constraint into the prompt text.`);
  } else {
    assert.equal(Object.prototype.hasOwnProperty.call(payload, 'precision_target_size'), false, `${label} must not carry a resize target in preserve mode.`);
    assert.equal(Object.prototype.hasOwnProperty.call(payload, 'precision_resize_prompt'), false, `${label} must not carry resize guidance in preserve mode.`);
    assert.equal(Object.prototype.hasOwnProperty.call(payload, 'precision_output_size_policy'), false, `${label} must not carry output-size policy in preserve mode.`);
  }
  assert.equal(Object.prototype.hasOwnProperty.call(payload, 'size'), false, `${label} must not fall back to the generic size field.`);
}
const payloadContext = vm.createContext({
  PRECISION_ANNOTATION_CONTRACT: 'genbox-annotation-v3',
});
vm.runInContext([
  extractFunction('sanitizePrecisionOutputSizePolicy'),
  extractFunction('precisionGreatestCommonDivisor'),
  extractFunction('precisionResizeAspectConstraint'),
  extractFunction('precisionEditObjectInstruction'),
  extractFunction('serializePrecisionAnnotationForRequest'),
  extractFunction('serializePrecisionAnnotationsForRequest'),
  extractFunction('applyPrecisionEditPayload'),
].join('\n'), payloadContext);
const localPayload = JSON.parse(vm.runInContext(`
  var localPayload = {};
  applyPrecisionEditPayload(localPayload, {
    imageData: 'data:image/png;base64,c291cmNl',
    strategy: 'fine',
    selectionMode: 'local',
    selectionFeather: 14,
    sizeMode: 'preserve',
    annotationContract: 'genbox-annotation-v3',
    annotationImageData: 'data:image/png;base64,YW5ub3RhdGlvbg==',
    annotations: [${JSON.stringify(canonicalRectangleAnnotation)}]
  });
  JSON.stringify(localPayload);
`, payloadContext));
assert.equal(localPayload.precision_strategy, 'fine', 'Local selection payload must retain the selected strategy.');
assert.equal(localPayload.precision_selection_mode, 'local', 'Local selection payload must retain local selection semantics.');
assert.equal(localPayload.precision_selection_feather, 14, 'Local selection payload must retain the bounded feather value.');
const firstPureResizePayload = JSON.parse(vm.runInContext(`
  var firstPayload = {
    prompt: 'Extend the background.',
    providers: ['provider-a'],
    enhance_prompt: false,
    mode: 'precision_edit',
    continuous: false,
    system_prompt: null,
    continuous_id: null,
    quantities: { 'provider-a': 1 },
    exact_ratio_crop: false
  };
  applyPrecisionEditPayload(firstPayload, {
    imageData: 'data:image/png;base64,c291cmNl',
    sizeMode: 'resize',
    targetSize: '1536x864',
    resizePrompt: 'Extend the scene naturally.',
    annotationContract: 'genbox-annotation-v3',
    annotationImageData: null,
    annotationData: { objects: [] }
  });
  firstPayload.provider_settings = { 'provider-a': { model: 'edit-model' } };
  JSON.stringify(firstPayload);
`, payloadContext));
assertPureResizePayload(firstPureResizePayload, 'First pure resize payload');
assert.deepEqual(firstPureResizePayload.provider_settings, { 'provider-a': { model: 'edit-model' } }, 'First pure resize payload must retain the explicit selected model.');
const annotatedPreservePayload = JSON.parse(vm.runInContext(`
  var annotatedPayload = {
    prompt: 'Preserve the foreground.',
    providers: ['provider-a'],
    enhance_prompt: false,
    mode: 'precision_edit',
    continuous: false,
    system_prompt: null,
    continuous_id: null,
    quantities: { 'provider-a': 1 },
    exact_ratio_crop: false
  };
  applyPrecisionEditPayload(annotatedPayload, {
    imageData: 'data:image/png;base64,c291cmNl',
    sizeMode: 'preserve',
    annotationContract: 'genbox-annotation-v3',
    annotationImageData: 'data:image/png;base64,YW5ub3RhdGlvbg==',
    annotations: ${JSON.stringify(richUiRequestAnnotations)}
  });
  annotatedPayload.provider_settings = { 'provider-a': { model: 'edit-model' } };
  JSON.stringify(annotatedPayload);
`, payloadContext));
assertAnnotatedPayload(annotatedPreservePayload, 'Annotated preserve payload', 'preserve');
assert.deepEqual(annotatedPreservePayload.provider_settings, { 'provider-a': { model: 'edit-model' } }, 'Annotated preserve payload must retain the explicit selected model.');
const retryPureResizePayload = JSON.parse(vm.runInContext(`
  var retryPayload = {
    prompt: 'Extend the background.',
    providers: ['provider-a'],
    quantities: {},
    mode: 'precision_edit',
    size: '1536x864',
    quality: undefined,
    enhance_prompt: false,
    continuous: false
  };
  delete retryPayload.size;
  applyPrecisionEditPayload(retryPayload, {
    imageData: 'data:image/png;base64,c291cmNl',
    sizeMode: 'resize',
    targetSize: '1536x864',
    resizePrompt: 'Extend the scene naturally.',
    annotationContract: null,
    annotationImageData: null,
    annotationData: null
  });
  JSON.stringify(retryPayload);
`, payloadContext));
assertPureResizePayload(retryPureResizePayload, 'Retry pure resize payload');
const fitCropResizePayload = JSON.parse(vm.runInContext(`
  var fitCropPayload = {
    prompt: 'Extend the background.',
    providers: ['provider-a'],
    enhance_prompt: false,
    mode: 'precision_edit',
    continuous: false,
    quantities: { 'provider-a': 1 }
  };
  applyPrecisionEditPayload(fitCropPayload, {
    imageData: 'data:image/png;base64,c291cmNl',
    sizeMode: 'resize',
    targetSize: '1792x768',
    resizePrompt: 'Use a wide cinematic composition.',
    outputSizePolicy: 'fit_crop'
  });
  JSON.stringify(fitCropPayload);
`, payloadContext));
assert.equal(fitCropResizePayload.precision_output_size_policy, 'fit_crop', 'Fit/crop resize payload must carry the shared output-size policy value.');
assert.equal(Object.prototype.hasOwnProperty.call(fitCropResizePayload, 'precision_aspect_ratio_constraint'), false, 'Fit/crop resize payload must not send the frontend-only aspect hint.');
assert.equal(fitCropResizePayload.precision_resize_prompt, 'Use a wide cinematic composition.', 'Aspect metadata must not be concatenated into the resize guidance.');
const retryProviderSource = [
  extractFunction('sanitizePrecisionOutputSizePolicy'),
  extractFunction('precisionGreatestCommonDivisor'),
  extractFunction('precisionResizeAspectConstraint'),
  extractFunction('precisionEditObjectInstruction'),
  extractFunction('serializePrecisionAnnotationForRequest'),
  extractFunction('serializePrecisionAnnotationsForRequest'),
  extractFunction('applyPrecisionEditPayload'),
  extractFunction('precisionResizeDimensionKey'),
  extractFunction('precisionCapabilitySizeDeclaration'),
  extractFunction('resolvePrecisionModelCapability'),
  extractFunction('precisionProviderModelRecords'),
  extractFunction('precisionRetryModelError'),
  extractFunction('precisionRetryModelForProvider'),
  extractFunction('showPrecisionRetryModelError'),
  extractFunction('retryProvider'),
].join('\n');
expect(retryProviderSource.includes('annotations: lastGenContext.annotations') && !retryProviderSource.includes('annotationData: lastGenContext.annotation_data'), 'Precision retry must reuse only the allowed annotation array, not raw local-only structures.');
const retryProviderRequests = [];
const retryProviderStatuses = [];
const retryProviderAlerts = [];
let retryProviderConfirmCount = 0;
const retryProviderButton = { disabled: false, innerHTML: '' };
const retryProviderContext = vm.createContext({
  lastGenContext: {
    prompt: 'Extend the background.',
    mode: 'precision_edit',
    image_data: 'data:image/png;base64,c291cmNl',
    precision_size_mode: 'resize',
    precision_target_size: '1536x864',
    precision_resize_prompt: 'Extend the scene naturally.',
    precision_output_size_policy: 'fit_crop',
    provider_settings: { 'provider-a': { model: 'edit-model' } },
  },
  document: { getElementById: (id) => id === 'btnGen' ? retryProviderButton : null },
  findProvider: (id) => id === 'provider-a'
    ? { id: 'provider-a', name: 'Provider A', models: ['edit-model'], model_capabilities: { 'edit-model': { precision_edit: true } }, capabilities: { precision_edit: true }, endpoint_type: 'openai' }
    : { id, name: id, models: ['other-model'], model_capabilities: { 'other-model': { precision_edit: true } }, capabilities: { precision_edit: true }, endpoint_type: 'openai' },
  confirm: () => { retryProviderConfirmCount += 1; return true; },
  i18nText: (key) => key,
  setStatus: (value) => retryProviderStatuses.push(value),
  alert: (value) => retryProviderAlerts.push(value),
  _authFetch: async (url, options) => {
    retryProviderRequests.push({ url, options, body: JSON.parse(options.body) });
    return { ok: true, status: 200, json: async () => ({ generation_id: 'gen-retry' }) };
  },
  startGenPolling: () => {},
});
vm.runInContext(retryProviderSource, retryProviderContext);
await vm.runInContext("retryProvider('provider-a_0', 'provider-a')", retryProviderContext);
assert.equal(retryProviderRequests.length, 1, 'Precision retry with an explicit current-provider model must submit exactly one request.');
assert.equal(retryProviderRequests[0].url, '/api/generate');
assertPureResizePayload(retryProviderRequests[0].body, 'Runtime retry precision resize payload', 'fit_crop');
assert.deepEqual(retryProviderRequests[0].body.provider_settings, { 'provider-a': { model: 'edit-model' } }, 'Runtime precision retry must restore the selected model from lastGenContext.provider_settings[pid].');

retryProviderRequests.length = 0;
retryProviderStatuses.length = 0;
retryProviderAlerts.length = 0;
retryProviderConfirmCount = 0;
vm.runInContext("lastGenContext.provider_settings = {}", retryProviderContext);
assert.equal(vm.runInContext("retryProvider('provider-a_0', 'provider-a')", retryProviderContext), false, 'Precision retry without an explicit current-provider model must fail closed locally.');
assert.equal(retryProviderRequests.length, 0, 'Precision retry without an explicit model must not fetch.');
assert.equal(retryProviderConfirmCount, 0, 'Precision retry without an explicit model must not ask for retry confirmation.');
assert.ok(retryProviderStatuses[0].includes('precision_edit_retry_model_required'), 'Precision retry local failure must expose a structured error code.');
assert.ok(retryProviderAlerts[0].includes('creator.precision_retry_model_required'), 'Precision retry local failure must show the localized model-required message.');

retryProviderStatuses.length = 0;
retryProviderAlerts.length = 0;
vm.runInContext("lastGenContext.provider_settings = { 'provider-a': { model: 'other-model' } }", retryProviderContext);
assert.equal(vm.runInContext("retryProvider('provider-a_0', 'provider-a')", retryProviderContext), false, 'Precision retry with a model that is not current for this provider must fail closed.');
assert.equal(retryProviderRequests.length, 0, 'Precision retry with the wrong provider model must not fetch.');

retryProviderRequests.length = 0;
retryProviderStatuses.length = 0;
retryProviderAlerts.length = 0;
vm.runInContext("lastGenContext.provider_settings = { 'provider-a': { model: 'edit-model' } }; lastGenContext.annotations = [{ type: 'rectangle', x: 0.1, y: 0.2, width: 0.6, height: 0.6000000000000001, label: 1, instruction: 'Preserve the foreground.' }]; lastGenContext.annotation_image_data = 'data:image/png;base64,YW5ub3RhdGlvbg=='; lastGenContext.annotation_contract = 'genbox-annotation-v3';", retryProviderContext);
await vm.runInContext("retryProvider('provider-a_0', 'provider-a')", retryProviderContext);
assert.equal(retryProviderRequests.length, 1, 'Annotated precision retry must submit exactly one request.');
assertAnnotatedPayload(retryProviderRequests[0].body, 'Runtime retry precision annotated payload', 'resize', 'fit_crop', [canonicalRectangleAnnotation]);
assert.deepEqual(retryProviderRequests[0].body.provider_settings, { 'provider-a': { model: 'edit-model' } }, 'Annotated precision retry must retain the explicit selected model.');

expect(js.includes("payload.operation = 'precision_edit'") && js.includes("mode: currentMode"), 'Precision request must use a distinct backend mode.');
expect(html.includes('id="precisionFileInput"'), 'Precision edit needs a local file input.');
expect(js.includes("upload.addEventListener('change', loadPrecisionEditLocalFile)"), 'Precision file input must load local images.');
expect(js.includes('function loadPrecisionEditLocalFile'), 'Precision local upload needs a handler.');
expect(!js.includes('window.prompt'), 'Precision text must use the inline editor, not window.prompt.');
expect(html.includes('id="precisionTextEditor"') && js.includes('function commitPrecisionEditText'), 'Text annotation needs an inline editor commit path.');
expect(html.includes('id="precisionEditObjectList"'), 'Precision edit needs a change list.');
expect(js.includes('precision_instruction_required') && js.includes("object.type !== 'text'"), 'Every V3 region annotation requires an instruction; text is optional.');
expect(js.includes('normalized.label') && !js.includes('normalized.number = normalized.label') && js.includes('normalized.instruction'), 'Structured annotations must carry label and instruction without a number alias.');
expect(js.includes('payload.provider_settings[precisionEditSelectedModel.providerId] = { model: precisionEditSelectedModel.model }'), 'Precision request must explicitly carry the selected model in provider_settings.');
expect(html.includes('id="precisionAnnotationPreview"') && js.includes('function updatePrecisionAnnotationPreview'), 'Annotation preview needs a real update chain.');
expect(html.includes('id="precisionAnnotationCount"') && js.includes('count.textContent = String(precisionEditObjects.length)'), 'Annotation count needs a real update chain.');
expect(html.includes('id="precisionStrokeWidthValue"') && js.includes('function updatePrecisionStrokeWidthValue'), 'Stroke width output needs a real update chain.');
expect(css.includes('.precision-canvas-surface') && js.includes("surface.style.aspectRatio = width + ' / ' + height"), 'Loaded canvas surface must preserve the source aspect ratio inside the scrollable viewport.');
expect(js.includes('function fetchGenerationStatus') && js.includes("'/api/generate/status/'"), 'Precision polling must use the real generation status endpoint.');
expect(!js.includes('/api/generation/'), 'Precision polling and terminal hydration must never probe the nonexistent legacy route.');
expect(html.includes('id="precisionTaskMonitor"') && js.includes('function updatePrecisionTaskMonitor'), 'Precision mode needs its own task status and log.');
expect(js.includes('function getPrecisionCutoutControls()'), 'Precision initialization needs a defined cutout control lookup.');
expect(js.includes("if (!data) {") && js.includes("status.textContent = '';") && js.includes("log.textContent = '';"), 'An idle precision task monitor must clear dynamic state while preserving its explanatory empty state.');
const taskMonitor = js.slice(js.indexOf('function updatePrecisionTaskMonitor'), js.indexOf('function updatePrecisionCutoutAvailability'));
expect(/id="precisionTaskMonitor" class="[^"]*precision-task-idle/.test(html), 'The initial precision task panel must be explicitly idle.');
expect(taskMonitor.includes("monitor.classList.add('precision-task-idle')") && taskMonitor.includes("monitor.classList.remove('precision-task-idle')"), 'Only an empty precision task payload may use the compact idle state.');
expect(css.includes('.precision-mode-hidden'), 'Precision mode must hide the generic task monitor.');
expect(js.includes('function generationResponseError(response)'), 'Generation errors need structured response parsing.');
expect(js.includes('if (!r.ok) return generationResponseError(r);'), 'Generation submission must preserve structured API errors.');
expect(js.includes('detail.message') && js.includes('detail.code'), 'Structured generation errors must expose message and code.');
expect(js.includes("('HTTP ' + response.status)"), 'Generation errors must retain HTTP status as fallback.');
expect(html.includes('id="precisionVersionRail"') && js.includes('function appendPrecisionEditVersion'), 'Successful precision results need a version rail.');
expect(js.includes("precisionEditSession.selectedVersionId = id;\n  precisionEditSession.view = 'after';") && !js.includes("function selectPrecisionVersion(id) {\n  setPrecisionBaseVersion(id);"), 'Version shortcuts must browse without replacing the annotation base.');
expect(js.includes('result.success || !result.local_path') && js.includes('precisionEditSession.versions.push'), 'Only successful results with local_path may create versions.');
expect(html.includes('id="precisionCompareSlider"') && js.includes('function updatePrecisionCompareSlider'), 'Precision versions need an accessible compare slider.');
for (const eventName of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'lostpointercapture']) {
  expect(js.includes("stage.addEventListener('" + eventName + "'"), 'Compare slider is missing ' + eventName + '.');
}
const compareBinding = js.slice(js.indexOf('function bindPrecisionCompareEvents'), js.indexOf('function renderPrecisionEditSession'));
const compareSizing = js.slice(js.indexOf('function updatePrecisionCompareSlider'), js.indexOf('function togglePrecisionCompareFullscreen'));
expect(compareBinding.includes('var syncCompareSize') && compareBinding.includes('updatePrecisionCompareSlider(slider ? slider.value : 50);'), 'Compare layer resize callbacks must resync the current divider position.');
expect(compareBinding.includes('new ResizeObserver(syncCompareSize)') && compareBinding.includes("window.addEventListener('resize', syncCompareSize)"), 'Compare layer must resync after ResizeObserver and window resize events.');
expect(!/else\s*\{\s*window\.addEventListener\('resize', syncCompareSize\);\s*\}/.test(compareBinding), 'Window resize sync must remain active when ResizeObserver is available.');
expect(compareSizing.includes('after.style.width = width + \'px\';') && !compareSizing.includes('after.width =') && !compareSizing.includes('after.height ='), 'Compare resync may update CSS layout width but must not change image pixel dimensions.');
expect(js.includes("var panel = document.getElementById('panelPrecisionEdit');") && !js.includes("var panel = document.getElementById('precisionSessionPanel');"), 'Fullscreen must target the complete precision workbench panel.');
expect(js.includes('preserveEditor: true') && js.includes('renderObjectList: !(options && options.preserveEditor)'), 'Per-annotation typing must not recreate the active editor.');
expect(html.indexOf('id="precisionSessionPanel"') < html.indexOf('id="precisionCanvasShell"'), 'Version shortcuts must sit above the main canvas.');
expect(html.indexOf('id="precisionVersionRail"') < html.indexOf('data-precision-view="before"') && html.indexOf('data-precision-view="compare"') < html.indexOf('id="btnPrecisionFullscreen"'), 'Versions, view modes, and fullscreen must share the requested order.');
expect(css.includes('.precision-canvas-session') && css.includes('justify-content: flex-end'), 'Canvas session tools must align together at the upper right.');
const responsiveReliability = css.slice(css.indexOf('/* Precision edit responsive reliability:'));
expect(responsiveReliability.includes('.precision-edit-stage-heading') && responsiveReliability.includes('grid-template-columns: minmax(0, 1fr);'), 'The stage heading must stack its metadata and version rail inside the stage column.');
expect(responsiveReliability.includes('.precision-canvas-session') && responsiveReliability.includes('position: static;') && responsiveReliability.includes('max-width: 100%;'), 'Session controls must remain in stage flow instead of overlaying the inspector.');
expect(responsiveReliability.includes('.precision-version-rail') && responsiveReliability.includes('overflow-x: auto;') && responsiveReliability.includes('flex-wrap: nowrap;'), 'A crowded version rail must scroll inside its own bounds.');
expect(responsiveReliability.includes('@media (max-width: 1280px) and (min-width: 641px)') && responsiveReliability.includes('@media (max-width: 900px)') && responsiveReliability.includes('@media (max-width: 640px)'), 'Precision layout must define the reported desktop, stacked, and mobile reflow bands.');
expect(responsiveReliability.includes('overflow-x: clip;') && css.includes('.generate-center.precision-preview-collapsed') && css.includes('overflow: auto;'), 'Precision workbench content must avoid horizontal spill while remaining vertically reachable on short screens.');
for (const id of ['btnPrecisionSizePreserve', 'btnPrecisionSizeResize', 'precisionResizeWidth', 'precisionResizeHeight', 'precisionResizePrompt']) {
  expect(html.includes('id="' + id + '"'), 'Missing precision size control: ' + id);
}
expect(js.includes("var precisionEditSizeMode = 'preserve'"), 'Precision edit must default to preserving the source canvas.');
expect(js.includes("if (currentMode !== 'precision_edit') payload.size = genSize;"), 'Precision edit must not inherit text-to-image size settings.');
expect(js.includes("currentMode !== 'precision_edit' && document.getElementById('chkUpscale').checked"), 'Precision edit must not inherit generic post-generation upscaling.');
expect(js.includes('applyPrecisionEditPayload(payload,') && js.includes("payload.precision_size_mode = context.sizeMode === 'resize' ? 'resize' : 'preserve';"), 'Precision requests must carry an explicit size policy through the shared payload builder.');
expect(js.includes("if (payload.precision_size_mode === 'resize')") && js.includes('payload.precision_target_size = context.targetSize'), 'Target dimensions must only be sent for explicit resize mode.');
expect(js.includes('payload.precision_output_size_policy = sanitizePrecisionOutputSizePolicy(context.outputSizePolicy)') && !js.includes('payload.precision_aspect_ratio_constraint'), 'Resize requests must carry the output-size policy without sending the frontend-only aspect hint.');
expect(js.includes("return candidate.width + ':' + candidate.height + ' aspect ratio'") && js.includes('{ width: 21, height: 9 }'), 'Aspect-ratio metadata must preserve common natural-language ratios such as 21:9.');
expect(html.includes('id="precisionResizePrompt"') && html.includes('required aria-required="true"'), 'Resize composition guidance must be visibly required.');
expect(html.includes('id="precisionResizePromptPreset"') && html.includes('aria-describedby="precisionResizePromptPresetHint"'), 'Resize guidance needs an accessible composition preset selector.');
expect(html.includes('id="precisionAspectRatioHint"') && html.includes('precisionOutputSizePolicyHint precisionAspectRatioHint'), 'Resize policy controls must describe the backend-derived aspect-ratio hint.');
expect(html.includes('id="precisionOutputPolicyStrict"') && html.includes('value="strict" checked') && html.includes('id="precisionOutputPolicyFitCrop"') && html.includes('value="fit_crop"'), 'Resize mode needs the strict and local fit/crop output-size policy controls.');
expect(css.includes('.precision-output-size-policy-options input[type="radio"]') && css.includes('.precision-output-size-policy-options label:has(input:checked)'), 'Output-size policy radios need compact segmented styling that does not inherit full-width text-input layout.');
expect(!js.includes('PRECISION_OUTPUT_SIZE_POLICY_STORAGE_KEY') && !js.includes('genbox_precision_output_size_policy'), 'Precision output-size policy must not add a localStorage key.');
const outputPolicySource = [
  extractFunction('sanitizePrecisionOutputSizePolicy'),
  extractFunction('syncPrecisionOutputSizePolicyControls'),
  extractFunction('setPrecisionOutputSizePolicy'),
  extractFunction('getPrecisionOutputSizePolicy'),
].join('\n');
expect(!outputPolicySource.includes('localStorage') && !outputPolicySource.includes('getItem') && !outputPolicySource.includes('setItem'), 'Precision output-size policy must remain in page-session memory only.');
for (const key of ['keep_style_subject', 'keep_person', 'center_subject', 'extend_left', 'extend_right', 'banner']) {
  expect(html.includes('creator.precision_size_prompt_preset_' + key), 'Missing composition prompt preset: ' + key);
}
expect(html.includes('creator.precision_size_prompt_preset_append_hint'), 'The UI must explain that prompt presets append without overwriting free-form guidance.');
expect(js.includes("creator.precision_size_prompt_preset_keep_style_subject") && js.includes('if (!resizePrompt) resizePrompt'), 'Pure resize must fall back to safe composition guidance when the optional input is empty.');
expect(extractFunction('precisionCapabilitySizeDeclaration').includes("var fields = ['supported_sizes', 'supportedSizes', 'sizes', 'dimensions']"), 'Resize capability parsing must use only explicit model size declaration fields.');
expect(js.includes('function resolvePrecisionModelCapability'), 'Precision aliases need one explicit canonical capability resolver in the UI.');
const resizeDeclarationSource = extractFunction('precisionResizeDimensions');
expect(
  resizeDeclarationSource.includes('/^([1-9]\\d{1,4})x([1-9]\\d{1,4})$/') &&
    resizeDeclarationSource.includes('stringKey === value') &&
    !resizeDeclarationSource.includes('.trim()') &&
    !resizeDeclarationSource.includes('/i') &&
    !resizeDeclarationSource.includes('value.width') &&
    !resizeDeclarationSource.includes('value.w') &&
    js.includes('function precisionResizeDimensionKey'),
  'Declared resize dimensions must use exact canonical WIDTHxHEIGHT provider declarations without trimming, leading zeroes, uppercase separators, or object-shaped aliases.',
);
expect(js.includes("capability.sizes[targetSize] !== true") && js.includes("code: 'precision_edit_size_capability_unknown'") && js.includes("code: 'precision_edit_size_undeclared'"), 'Unknown capabilities and undeclared resize targets must be rejected before submission.');
expect(js.includes("if (precisionEditSizeMode !== 'resize') return { mode: 'preserve' };"), 'Preserve mode must remain independent from resize capability declarations so the provider can use auto sizing.');
const resizeCapabilityUi = js.slice(js.indexOf('function updatePrecisionResizeCapabilityUI'), js.indexOf('function findPrecisionResizeOptionBySize'));
expect(resizeCapabilityUi.includes('option.disabled = false;') && !resizeCapabilityUi.includes('!supported'), 'Local built-in and saved presets must remain selectable regardless of declared provider sizes.');
expect(js.includes('var successfulCompleted = stateKeys.filter') && js.includes("var actualLabel = stateKeys.length ? '实际完成 '"), 'Precision progress must derive real completion from provider terminal success states.');
expect(js.includes('function precisionOutputSizeNotices') && js.includes('creator.precision_output_size_adjusted') && js.includes('creator.precision_output_size_strict_mismatch'), 'Precision progress must surface size-adjusted warnings and strict mismatch recovery hints.');
expect(js.includes("var hasEstimate = !terminal") && js.includes("' · 耗时估算中'") && js.includes("progressBar.classList.toggle('indeterminate', hasEstimate)"), 'Elapsed-time progress estimates must be labelled and rendered as uncertain.');
expect(js.includes("if (hasActualProgress && !hasEstimate)") && js.includes("progressBar.removeAttribute('aria-valuenow')"), 'Estimated progress must never expose aria-valuenow.');
expect(js.includes("var terminalFailed = terminal && String(taskStatus).toLowerCase() !== 'completed'") && js.includes("progressBar.style.width = terminal ? '0%' : ''"), 'Failed and cancelled terminal states must not display 100% progress.');
expect(js.includes('finishGenerationTerminalStatus(terminalData, cancelledPrecisionTask)') && !js.includes('Object.assign({}, precisionTaskMonitorData || {}, terminalData)'), 'Precision cancellation must use the shared complete terminal payload without merging stale monitor state.');
expect(js.includes('if (precisionTaskMonitorTimer) { clearInterval(precisionTaskMonitorTimer); precisionTaskMonitorTimer = null; }') && js.includes('precisionTaskMonitorTerminal = terminal'), 'Precision terminal updates must stop the independent elapsed timer.');
expect(html.includes('id="precisionTaskProgressBar"') && html.includes('role="progressbar"') && html.includes('aria-valuenow="0"'), 'Precision progress needs an accessible initial value.');
expect(responsiveReliability.includes('.precision-task-log-panel.precision-task-idle') && responsiveReliability.includes('min-height: 0;'), 'Mobile task compaction must be scoped to the explicit idle state.');
expect(/id="precisionCanvasResizeHandle"[^>]*type="button"|type="button"[^>]*id="precisionCanvasResizeHandle"/.test(html) && html.includes('aria-controls="precisionCanvasShell"'), 'The canvas resize affordance must be a keyboard-focusable control.');
const canvasResize = js.slice(js.indexOf('function precisionCanvasResizeLimits'), js.indexOf('function getPrecisionCutoutControls'));
expect(canvasResize.includes("closest('.precision-edit-stage-column')") && canvasResize.includes('stage.clientWidth'), 'Canvas resize bounds must come from the actual stage column.');
expect(canvasResize.includes('maxHeight') && canvasResize.includes('visualHeight = visualWidth * precisionEditSourceHeight / precisionEditSourceWidth'), 'Canvas resize must preserve source aspect while bounding visual height.');
expect(canvasResize.includes('event.isPrimary === false') && canvasResize.includes('event.button !== 0'), 'Canvas resizing must accept only the primary pointer action.');
expect(canvasResize.includes("window.addEventListener('pointermove'") && canvasResize.includes("window.addEventListener('pointerup'") && canvasResize.includes('releasePointerCapture'), 'Canvas resizing must keep and release its pointer lifecycle outside the handle bounds.');
expect(canvasResize.includes('new ResizeObserver(reflow)') && canvasResize.includes("window.addEventListener('orientationchange', reflow)"), 'Canvas size must be re-clamped after stage and orientation changes.');
expect(js.includes('reflowPrecisionCanvasVisualSize(true);') && responsiveReliability.includes('.precision-canvas-shell:not(.is-empty)') && responsiveReliability.includes('height: auto;'), 'Loaded canvases must use aspect-derived height instead of the fixed mobile placeholder height.');
expect(js.includes('function bindPrecisionHelpTooltips') && js.includes("trigger.addEventListener('focus'") && js.includes("if (event.key !== 'Escape') return;"), 'Precision help tooltips must remain keyboard reachable and close on Escape.');
expect(js.includes("trigger.addEventListener('click', function() { setPrecisionHelpTooltip(trigger, true); })"), 'Clicking a focused precision help trigger must keep its tooltip open.');
expect(js.includes("trigger.setAttribute('aria-controls', tooltipId)") && js.includes("trigger.setAttribute('aria-expanded', open ? 'true' : 'false')"), 'Precision help triggers must expose their tooltip state to assistive technology.');
expect(js.includes("precisionEditSession.selectedVersionId = id;\n  precisionEditSession.view = 'after';\n  renderPrecisionEditSession();"), 'Successful results must be browsable without silently replacing the source canvas.');

for (const id of ['precisionResizePresetName', 'btnPrecisionSaveResizePreset', 'btnPrecisionDeleteResizePreset', 'btnPrecisionResetResizePresets', 'precisionResizePresetStatus']) {
  expect(html.includes('id="' + id + '"'), 'Missing saved resize preset control: ' + id);
}
expect(/id="precisionResizePresetStatus"[^>]*role="status"[^>]*aria-live="polite"/.test(html), 'Saved resize preset feedback must use a polite live region.');
expect(!/<select\s+id="precisionResizePreset"[^>]*\sonchange=/.test(html), 'The resize preset selector must not retain an inline change handler.');
expect(js.includes("var PRECISION_RESIZE_PRESET_STORAGE_KEY = 'genbox_precision_resize_presets_v1';") && js.includes('var PRECISION_RESIZE_PRESET_SCHEMA_VERSION = 1;') && js.includes('var PRECISION_RESIZE_PRESET_LIMIT = 20;'), 'Saved resize presets need the versioned local-only storage contract and 20-item limit.');

const presetBinding = js.slice(js.indexOf('function bindPrecisionResizeControls'), js.indexOf('function setPrecisionHelpTooltip'));
expect((presetBinding.match(/select\.addEventListener\('change'/g) || []).length === 1, 'The resize preset selector must have exactly one guarded listener path.');
expect(presetBinding.includes("select.dataset.precisionBound = 'true'"), 'Resize preset listeners must remain idempotently bound.');
expect(presetBinding.includes("promptPreset.dataset.precisionBound = 'true'") && presetBinding.includes("promptPreset.addEventListener('change'"), 'Composition presets need one idempotently bound change listener.');
expect(presetBinding.includes("prompt.dataset.precisionPromptPresetBound = 'true'") && presetBinding.includes("prompt.addEventListener('input'"), 'Manual prompt edits must clear any maxlength validation left by a rejected preset.');

const promptPresetSource = extractFunction('applyPrecisionResizePromptPreset');
expect(!promptPresetSource.includes('localStorage'), 'Composition prompt presets must never be persisted.');
expect(promptPresetSource.includes("current + '\\n' + preset") && !promptPresetSource.includes('textarea.value = preset;'), 'Composition presets must append to existing text instead of overwriting it.');

const presetRendering = js.slice(js.indexOf('function renderPrecisionResizeSavedPresets'), js.indexOf('function updatePrecisionResizeCapabilityUI'));
expect(presetRendering.includes("option.value = 'saved:' + preset.id;") && presetRendering.includes("option.dataset.size = preset.width + 'x' + preset.height;"), 'Saved options must use saved:<id> values with data-size dimensions.');
const presetDeletion = js.slice(js.indexOf('function deleteSelectedPrecisionResizePreset'), js.indexOf('function resetPrecisionResizePresets'));
expect(presetDeletion.includes("option.dataset.precisionSavedPreset !== 'true'") && presetDeletion.includes("option.value.indexOf('saved:') !== 0"), 'Delete must reject built-in and custom non-saved options.');

const presetStateSource = js.slice(js.indexOf('var PRECISION_RESIZE_PRESET_STORAGE_KEY'), js.indexOf('var precisionEditSession'));
const presetDimensionSource = js.slice(js.indexOf('function precisionResizeDimensionKey'), js.indexOf('function precisionResizeDimensions'));
const presetStorageSource = js.slice(js.indexOf('function normalizePrecisionResizePresetName'), js.indexOf('function createPrecisionResizePresetId'));
expect(presetStorageSource.includes("normalized.normalize('NFKC')") && presetStorageSource.includes('\\u0000-\\u001f\\u007f-\\u009f') && presetStorageSource.includes('Array.from(normalized).length > 40'), 'Preset names must be normalized, stripped of controls, and limited to 40 characters.');
expect(js.includes('var PRECISION_MAX_OUTPUT_PIXELS = 64 * 1024 * 1024;'), 'Precision resize needs its own 64Mi output-pixel cap.');
expect(presetDimensionSource.includes('Number.isInteger') && presetDimensionSource.includes('numericWidth < 64') && presetDimensionSource.includes('numericWidth > 8192') && presetDimensionSource.includes('numericWidth * numericHeight > PRECISION_MAX_OUTPUT_PIXELS'), 'Preset dimensions must be bounded integers under the precision output-pixel cap.');
expect(presetStorageSource.includes('JSON.parse(raw)') && /function readPrecisionResizePresets\(\)[\s\S]*catch \(error\) \{[\s\S]*return \[\];/.test(presetStorageSource), 'Malformed saved preset storage must fail closed to an empty list.');
expect(presetStorageSource.includes('sanitized.push({ id: preset.id, name: preset.name, width: preset.width, height: preset.height })'), 'Persistent preset records must be reduced to the four allowed fields.');
for (const forbidden of ['prompt', 'guidance', 'provider', 'model', 'source']) {
  const writeSource = presetStorageSource.slice(presetStorageSource.indexOf('function writePrecisionResizePresets'));
  expect(!new RegExp('\\b' + forbidden + '\\b', 'i').test(writeSource), 'Preset persistence must not include ' + forbidden + '.');
}

const storedValues = new Map();
let storageFailure = '';
const presetContext = {
  window: {
    localStorage: {
      getItem(key) {
        if (storageFailure === 'get') throw new Error('blocked read');
        return storedValues.has(key) ? storedValues.get(key) : null;
      },
      setItem(key, value) {
        if (storageFailure === 'set') throw new Error('blocked write');
        storedValues.set(key, value);
      },
    },
  },
};
vm.createContext(presetContext);
vm.runInContext(`
  var INPAINT_MAX_PIXELS = 24000000;
  var PRECISION_MAX_OUTPUT_PIXELS = 64 * 1024 * 1024;
  ${presetStateSource}
  ${presetDimensionSource}
  ${presetStorageSource}
  globalThis.presetTest = {
    normalizePrecisionResizePresetName,
    precisionResizeDimensionKey,
    readPrecisionResizePresets,
    writePrecisionResizePresets
  };
`, presetContext);
const presetTest = presetContext.presetTest;
expect(presetTest.normalizePrecisionResizePresetName('  Ａ\u0000\t B  ') === 'A B', 'Preset name normalization must apply NFKC, remove controls, and collapse whitespace.');
expect(presetTest.normalizePrecisionResizePresetName('x'.repeat(40)) === 'x'.repeat(40) && presetTest.normalizePrecisionResizePresetName('x'.repeat(41)) === '', 'Preset names must accept 1-40 characters only.');
expect(presetTest.precisionResizeDimensionKey(8192, 8192) === '8192x8192', 'The exact 64Mi-pixel precision boundary must be valid.');
for (const invalidDimensions of [[63, 100], [8193, 100], [100.5, 100], ['100', 100], [8192, 8193]]) {
  expect(presetTest.precisionResizeDimensionKey(...invalidDimensions) === '', 'Invalid preset dimensions must be rejected: ' + invalidDimensions.join('x'));
}

const storageKey = 'genbox_precision_resize_presets_v1';
expect(presetTest.writePrecisionResizePresets([{ id: 'cover', name: ' Cover ', width: 1200, height: 800, prompt: 'private', guidance: 'private', provider: 'private', model: 'private', source: 'private' }]), 'Valid presets must be writable.');
const persisted = JSON.parse(storedValues.get(storageKey));
expect(persisted.version === 1 && Object.keys(persisted).sort().join(',') === 'presets,version', 'Saved preset storage must carry only schema version and presets.');
expect(Object.keys(persisted.presets[0]).sort().join(',') === 'height,id,name,width' && persisted.presets[0].name === 'Cover', 'Saved preset payloads must contain only normalized id/name/width/height fields.');

const duplicateRecords = [
  { id: 'one', name: 'Alpha', width: 1000, height: 1000 },
  { id: 'two', name: 'alpha', width: 1001, height: 1000 },
  { id: 'three', name: 'Gamma', width: 1000, height: 1000 },
  { id: 'one', name: 'Delta', width: 1002, height: 1000 },
  { id: 'five', name: 'Epsilon', width: 1003, height: 1000 },
];
expect(presetTest.writePrecisionResizePresets(duplicateRecords), 'Duplicate filtering must still leave storage usable.');
expect(JSON.parse(storedValues.get(storageKey)).presets.length === 2, 'Duplicate ids, normalized names, and dimensions must be ignored.');

const overLimit = Array.from({ length: 25 }, (_, index) => ({ id: 'id-' + index, name: 'Size ' + index, width: 1000 + index, height: 1000 }));
expect(presetTest.writePrecisionResizePresets(overLimit), 'The preset limit must be enforced without failing the write.');
expect(JSON.parse(storedValues.get(storageKey)).presets.length === 20 && presetTest.readPrecisionResizePresets().length === 20, 'No more than 20 valid presets may be persisted or loaded.');
storedValues.set(storageKey, '{bad json');
expect(presetTest.readPrecisionResizePresets().length === 0, 'Malformed JSON must not escape the storage reader.');
storageFailure = 'get';
expect(presetTest.readPrecisionResizePresets().length === 0, 'Blocked localStorage reads must fail harmlessly.');
storageFailure = 'set';
expect(presetTest.writePrecisionResizePresets([]) === false, 'Blocked localStorage writes must return a harmless failure result.');
storageFailure = '';

const visibilityStateSource = js.slice(js.indexOf('var PRECISION_MODEL_VISIBILITY_STORAGE_KEY'), js.indexOf('var precisionEditSelectedModel'));
const visibilityStorageSource = [
  extractFunction('isPrecisionModelVisibilityStorageKey'),
  extractFunction('precisionModelVisibilityStorageKey'),
  extractFunction('sanitizePrecisionModelVisibility'),
  extractFunction('readPrecisionModelVisibility'),
  extractFunction('writePrecisionModelVisibility'),
  extractFunction('setPrecisionModelVisibility'),
].join('\n');
const visibilityMenuSource = [
  extractFunction('copyPrecisionModelVisibilityState'),
  extractFunction('precisionModelVisibilityLabel'),
  extractFunction('precisionModelVisibilityRecords'),
  extractFunction('precisionModelVisibilityState'),
  extractFunction('precisionModelVisibilityIsVisible'),
  extractFunction('precisionModelVisibilitySelectedCount'),
  extractFunction('precisionModelVisibilitySummary'),
  extractFunction('bindPrecisionModelVisibilityDismiss'),
  extractFunction('focusPrecisionModelVisibilityTrigger'),
  extractFunction('precisionModelVisibilityFocusableItems'),
  extractFunction('focusFirstPrecisionModelVisibilityControl'),
  extractFunction('removePrecisionModelVisibilityPortal'),
  extractFunction('portalPrecisionModelVisibilityMenu'),
  extractFunction('positionPrecisionModelVisibilityMenu'),
  extractFunction('handlePrecisionModelVisibilityDocumentPointer'),
  extractFunction('handlePrecisionModelVisibilityDocumentKeydown'),
  extractFunction('unbindPrecisionModelVisibilityDismiss'),
  extractFunction('openPrecisionModelVisibilityMenu'),
  extractFunction('cancelPrecisionModelVisibilityMenu'),
  extractFunction('precisionModelVisibilityMenuRecords'),
  extractFunction('setPrecisionModelVisibilityDraft'),
  extractFunction('setAllPrecisionModelVisibilityDraft'),
  extractFunction('confirmPrecisionModelVisibilityMenu'),
].join('\n');
expect(visibilityStateSource.includes('PRECISION_MODEL_VISIBILITY_KEY_PATTERN') && visibilityStateSource.includes('PRECISION_MODEL_VISIBILITY_FORBIDDEN_PATTERN'), 'Model visibility storage needs a strict provider/model key schema and forbidden sensitive-key guard.');
expect(visibilityStorageSource.includes('sanitizePrecisionModelVisibility(precisionEditModelVisibility)') && visibilityStorageSource.includes('raw[key] === false'), 'Model visibility persistence must reduce state to hidden-model booleans only.');
expect(!/\b(apiKey|api_key|base_url|credential|error_body|provider_settings|prompt)\b/.test(extractFunction('writePrecisionModelVisibility')), 'Model visibility writer must not persist credential fields, prompts, error bodies, or provider objects.');
expect(visibilityStateSource.includes('precisionModelVisibilityDraft') && visibilityMenuSource.includes('confirmPrecisionModelVisibilityMenu') && visibilityMenuSource.includes('cancelPrecisionModelVisibilityMenu'), 'Model visibility menu needs draft state with explicit confirm and cancel paths.');

const visibilityStoredValues = new Map();
let visibilityStorageFailure = '';
const visibilityContext = {
  window: {
    localStorage: {
      getItem(key) {
        if (visibilityStorageFailure === 'get') throw new Error('blocked read');
        return visibilityStoredValues.has(key) ? visibilityStoredValues.get(key) : null;
      },
      setItem(key, value) {
        if (visibilityStorageFailure === 'set') throw new Error('blocked write');
        visibilityStoredValues.set(key, value);
      },
    },
  },
  renderPrecisionEditModelPicker() {},
};
vm.createContext(visibilityContext);
vm.runInContext(`
  ${visibilityStateSource}
  ${visibilityStorageSource}
  globalThis.visibilityTest = {
    isPrecisionModelVisibilityStorageKey,
    precisionModelVisibilityStorageKey,
    readPrecisionModelVisibility,
    writePrecisionModelVisibility,
    setPrecisionModelVisibility
  };
`, visibilityContext);
const visibilityTest = visibilityContext.visibilityTest;
const visibilityKey = 'genbox_precision_model_visibility_v1';
expect(visibilityTest.isPrecisionModelVisibilityStorageKey('endpoint-a::gpt-image-2'), 'Provider/model visibility key should accept stable non-sensitive identifiers.');
for (const badKey of ['api_key', 'endpoint-a::https://example.test?token=secret', 'endpoint-a::prompt', 'endpoint-a::credential', 'endpoint a::gpt-image-2', 'endpoint-a::bad/model']) {
  expect(!visibilityTest.isPrecisionModelVisibilityStorageKey(badKey), 'Visibility storage key must reject sensitive or non-identifier keys: ' + badKey);
}
visibilityStoredValues.set(visibilityKey, JSON.stringify({
  'endpoint-a::gpt-image-2': false,
  'endpoint-a::gpt-image-3': true,
  'endpoint-a::prompt': false,
  'endpoint-a::credential': false,
  'endpoint-a::bad/model': false,
  api_key: 'secret',
  provider: { api_key: 'secret', base_url: 'https://example.test' },
}));
assert.equal(JSON.stringify(visibilityTest.readPrecisionModelVisibility()), '{"endpoint-a::gpt-image-2":false}', 'Stored model visibility must load only hidden provider/model booleans.');
vm.runInContext(`precisionEditModelVisibility = {
  'endpoint-a::gpt-image-2': false,
  'endpoint-a::gpt-image-3': true,
  'endpoint-a::prompt': false,
  api_key: 'secret',
  provider: { api_key: 'secret' }
};`, visibilityContext);
expect(visibilityTest.writePrecisionModelVisibility(), 'Sanitized model visibility state must be writable.');
assert.equal(visibilityStoredValues.get(visibilityKey), '{"endpoint-a::gpt-image-2":false}', 'Persisted model visibility payload must contain only false boolean entries keyed by provider/model id.');
expect(visibilityTest.setPrecisionModelVisibility('endpoint-a::gpt-image-2', true), 'Restoring visibility should save a sanitized empty preference map.');
assert.equal(visibilityStoredValues.get(visibilityKey), '{}', 'Visible/default model preferences must not be persisted.');
expect(visibilityTest.setPrecisionModelVisibility('endpoint-a::prompt', false) === false, 'Sensitive-looking model visibility keys must fail closed.');
visibilityStorageFailure = 'get';
expect(Object.keys(visibilityTest.readPrecisionModelVisibility()).length === 0, 'Blocked model visibility storage reads must fail harmlessly.');
visibilityStorageFailure = 'set';
expect(visibilityTest.writePrecisionModelVisibility() === false, 'Blocked model visibility storage writes must return a harmless failure result.');
visibilityStorageFailure = '';

const visibilityMenuStoredValues = new Map();
const visibilityFocusEvents = [];
const visibilityTrigger = {
  offsetParent: {},
  focus() {
    visibilityFocusEvents.push('trigger');
    visibilityMenuContext.document.activeElement = visibilityTrigger;
  },
};
const visibilityFocusableItems = ['all', 'model-a', 'cancel', 'confirm'].map((name) => ({
  name,
  offsetParent: {},
  focus() {
    visibilityFocusEvents.push(name);
    visibilityMenuContext.document.activeElement = this;
  },
}));
const visibilityMenuElement = {
  querySelectorAll(selector) {
    return selector === 'button:not([disabled]), input:not([disabled])' ? visibilityFocusableItems : [];
  },
};
const menuProvider = {
  id: 'endpoint-a',
  endpoint_type: 'openai',
  capabilities: { precision_edit: true },
  models: [{ id: 'model-a', alias: 'Alpha' }, { id: 'model-b' }, { id: 'blocked-model' }],
  model_capabilities: {
    'model-a': { precision_edit: true },
    'model-b': { precision_edit: true },
    'blocked-model': { precision_edit: false },
  },
};
const visibilityMenuContext = {
  window: {
    innerWidth: 390,
    innerHeight: 844,
    addEventListener() {},
    removeEventListener() {},
    localStorage: {
      getItem(key) { return visibilityMenuStoredValues.has(key) ? visibilityMenuStoredValues.get(key) : null; },
      setItem(key, value) { visibilityMenuStoredValues.set(key, value); },
    },
  },
  document: {
    documentElement: { clientWidth: 390, clientHeight: 844 },
    body: { appendChild(node) { node.parentNode = this; } },
    activeElement: null,
    getElementById: (id) => id === 'precisionModelVisibilityMenu' ? visibilityMenuElement : null,
    querySelector: (selector) => selector.includes('data-precision-model-visibility-toggle') ? visibilityTrigger : null,
    removeEventListener() {},
  },
  setTimeout: (fn) => { fn(); return 0; },
  findProvider: (id) => id === menuProvider.id ? menuProvider : null,
  i18nText: (key, params) => params ? key + ':' + JSON.stringify(params) : key,
  renderPrecisionEditModelPicker() {},
  updatePrecisionEditControls() {},
};
vm.createContext(visibilityMenuContext);
vm.runInContext(`
  ${visibilityStateSource}
  ${visibilityStorageSource}
  ${extractFunction('precisionResizeDimensionKey')}
  ${extractFunction('precisionCapabilitySizeDeclaration')}
  ${extractFunction('resolvePrecisionModelCapability')}
  ${extractFunction('precisionProviderModelRecords')}
  ${visibilityMenuSource}
  globalThis.visibilityMenuTest = {
    copyPrecisionModelVisibilityState,
    precisionModelVisibilitySelectedCount,
    precisionModelVisibilitySummary,
    focusPrecisionModelVisibilityTrigger,
    precisionModelVisibilityFocusableItems,
    removePrecisionModelVisibilityPortal,
    portalPrecisionModelVisibilityMenu,
    positionPrecisionModelVisibilityMenu,
    handlePrecisionModelVisibilityDocumentKeydown,
    setPrecisionModelVisibilityDraft,
    setAllPrecisionModelVisibilityDraft,
    confirmPrecisionModelVisibilityMenu,
    cancelPrecisionModelVisibilityMenu
  };
`, visibilityMenuContext);
const visibilityMenuTest = visibilityMenuContext.visibilityMenuTest;
vm.runInContext("precisionEditModelVisibility = { 'endpoint-a::model-b': false }; precisionModelVisibilityMenuOpen = true; precisionModelVisibilityMenuProviderId = 'endpoint-a'; precisionModelVisibilityDraft = copyPrecisionModelVisibilityState(precisionEditModelVisibility);", visibilityMenuContext);
assert.equal(visibilityMenuTest.precisionModelVisibilitySelectedCount(visibilityMenuContext.findProvider('endpoint-a').models.map((model) => ({ id: model.id, alias: model.alias || '', unavailable: model.id === 'blocked-model' })), 'endpoint-a', visibilityMenuContext.precisionModelVisibilityDraft), 1, 'Draft visibility must count only available checked models.');
expect(visibilityMenuTest.setPrecisionModelVisibilityDraft('endpoint-a::model-a', false), 'Draft checkbox changes should be accepted before commit.');
assert.equal(visibilityMenuStoredValues.has(visibilityKey), false, 'Draft visibility changes must not write localStorage before confirmation.');
expect(visibilityMenuTest.cancelPrecisionModelVisibilityMenu(), 'Cancel must close an open visibility menu.');
assert.equal(JSON.stringify(visibilityMenuContext.precisionEditModelVisibility), '{"endpoint-a::model-b":false}', 'Cancel must restore the persisted selection from before opening.');
assert.equal(visibilityMenuContext.precisionModelVisibilityDraft, null, 'Cancel must discard the draft state.');
visibilityFocusEvents.length = 0;
vm.runInContext("precisionModelVisibilityMenuOpen = true; precisionModelVisibilityMenuProviderId = 'endpoint-a'; precisionModelVisibilityDraft = copyPrecisionModelVisibilityState(precisionEditModelVisibility);", visibilityMenuContext);
expect(visibilityMenuTest.cancelPrecisionModelVisibilityMenu(true), 'Cancel from the popover button must close the menu.');
assert.deepEqual(visibilityFocusEvents, ['trigger'], 'Cancel from the popover button must restore focus to the rebuilt trigger.');
vm.runInContext("precisionModelVisibilityMenuOpen = true; precisionModelVisibilityMenuProviderId = 'endpoint-a'; precisionModelVisibilityDraft = { 'endpoint-a::model-a': false, 'endpoint-a::model-b': false };", visibilityMenuContext);
assert.equal(visibilityMenuTest.confirmPrecisionModelVisibilityMenu(), false, 'Confirm must fail closed when every available model is hidden.');
assert.equal(visibilityMenuStoredValues.has(visibilityKey), false, 'Fail-closed all-hidden confirmation must not persist a hidden-all state.');
vm.runInContext("precisionModelVisibilityMenuOpen = true; precisionModelVisibilityMenuProviderId = 'endpoint-a'; precisionModelVisibilityDraft = { 'endpoint-a::model-b': false };", visibilityMenuContext);
visibilityFocusEvents.length = 0;
expect(visibilityMenuTest.confirmPrecisionModelVisibilityMenu(), 'Confirm must persist a valid draft with at least one visible model.');
assert.equal(visibilityMenuStoredValues.get(visibilityKey), '{"endpoint-a::model-b":false}', 'Confirmed visibility must persist only hidden model booleans.');
assert.deepEqual(visibilityFocusEvents, ['trigger'], 'Confirm must restore focus to the rebuilt trigger.');
visibilityFocusEvents.length = 0;
vm.runInContext("precisionModelVisibilityMenuOpen = true; precisionModelVisibilityMenuProviderId = 'endpoint-a'; precisionModelVisibilityDraft = copyPrecisionModelVisibilityState(precisionEditModelVisibility);", visibilityMenuContext);
visibilityMenuContext.document.activeElement = visibilityFocusableItems[3];
visibilityMenuTest.handlePrecisionModelVisibilityDocumentKeydown({ key: 'Tab', preventDefault() { visibilityFocusEvents.push('prevent-tab'); } });
assert.deepEqual(visibilityFocusEvents, ['prevent-tab', 'all'], 'Tab on the last popover control must wrap to the first focusable item.');
visibilityFocusEvents.length = 0;
visibilityMenuContext.document.activeElement = visibilityFocusableItems[0];
visibilityMenuTest.handlePrecisionModelVisibilityDocumentKeydown({ key: 'Tab', shiftKey: true, preventDefault() { visibilityFocusEvents.push('prevent-shift-tab'); } });
assert.deepEqual(visibilityFocusEvents, ['prevent-shift-tab', 'confirm'], 'Shift+Tab on the first popover control must wrap to the last focusable item.');
visibilityFocusEvents.length = 0;
visibilityMenuTest.handlePrecisionModelVisibilityDocumentKeydown({ key: 'Escape', preventDefault() { visibilityFocusEvents.push('prevent-escape'); } });
assert.deepEqual(visibilityFocusEvents, ['prevent-escape', 'trigger'], 'Escape must close the popover and restore focus to the trigger.');

const visibilityPositionStyles = {};
const visibilityPositionTrigger = { getBoundingClientRect: () => ({ top: 120, bottom: 154, right: 760 }) };
const visibilityPositionMenu = { style: visibilityPositionStyles };
const visibilityPositionPanel = {
  querySelector(selector) {
    return selector.includes('data-precision-model-visibility-toggle') ? visibilityPositionTrigger : null;
  },
};
visibilityMenuContext.window.innerWidth = 937;
visibilityMenuContext.window.innerHeight = 920;
visibilityMenuContext.document.documentElement.clientWidth = 937;
visibilityMenuContext.document.documentElement.clientHeight = 920;
visibilityMenuContext.document.getElementById = (id) => {
  if (id === 'precisionEditModelVisibility') return visibilityPositionPanel;
  if (id === 'precisionModelVisibilityMenu') return visibilityPositionMenu;
  return null;
};
vm.runInContext("precisionModelVisibilityMenuOpen = true;", visibilityMenuContext);
expect(visibilityMenuTest.positionPrecisionModelVisibilityMenu(), 'Model display menu should position when open.');
assert.equal(visibilityPositionStyles.width, '420px', 'Desktop/937px menu width should clamp at the max width when available.');
assert.ok(parseInt(visibilityPositionStyles.left, 10) >= 12, 'Positioned menu must stay inside the left viewport edge.');
assert.ok(parseInt(visibilityPositionStyles.left, 10) + parseInt(visibilityPositionStyles.width, 10) <= 925, 'Positioned menu must stay inside the right viewport edge.');
assert.ok(parseInt(visibilityPositionStyles.maxHeight, 10) <= 420, 'Positioned menu must cap max-height so the footer remains reachable.');
visibilityMenuContext.window.innerWidth = 390;
visibilityMenuContext.window.innerHeight = 844;
visibilityMenuContext.document.documentElement.clientWidth = 390;
visibilityMenuContext.document.documentElement.clientHeight = 844;
visibilityPositionTrigger.getBoundingClientRect = () => ({ top: 700, bottom: 736, right: 378 });
expect(visibilityMenuTest.positionPrecisionModelVisibilityMenu(), 'Narrow viewport menu should still position.');
assert.equal(visibilityPositionStyles.width, '366px', '390px menu width should be viewport minus 24px.');
assert.equal(visibilityPositionStyles.left, '12px', '390px menu should stay within the viewport without horizontal overflow.');
visibilityMenuContext.window.innerWidth = 280;
visibilityMenuContext.window.innerHeight = 500;
visibilityMenuContext.document.documentElement.clientWidth = 280;
visibilityMenuContext.document.documentElement.clientHeight = 500;
visibilityPositionTrigger.getBoundingClientRect = () => ({ top: 80, bottom: 116, right: 268 });
expect(visibilityMenuTest.positionPrecisionModelVisibilityMenu(), 'Very narrow viewport menu should still position.');
assert.equal(visibilityPositionStyles.width, '256px', 'Very narrow menus must shrink below the old 280px floor.');
assert.equal(visibilityPositionStyles.left, '12px');
visibilityMenuContext.window.visualViewport = { width: 320, height: 460, offsetLeft: 40, offsetTop: 90 };
visibilityPositionTrigger.getBoundingClientRect = () => ({ top: 420, bottom: 456, right: 348 });
expect(visibilityMenuTest.positionPrecisionModelVisibilityMenu(), 'Zoomed visual viewport menu should use visual viewport offsets.');
assert.equal(visibilityPositionStyles.width, '296px');
assert.equal(visibilityPositionStyles.left, '52px');
assert.ok(parseInt(visibilityPositionStyles.top, 10) >= 102, 'Zoomed menus must remain below the visual viewport top edge.');
assert.ok(parseInt(visibilityPositionStyles.top, 10) + parseInt(visibilityPositionStyles.maxHeight, 10) <= 538, 'Zoomed menus must remain above the visual viewport bottom edge.');
assert.equal(visibilityPositionStyles.boxSizing, 'border-box');

const resizeOptions = [
  { value: 'custom', dataset: {}, disabled: true, title: '' },
  { value: '1024x1024', dataset: {}, disabled: true, title: '' },
  { value: '1536x864', dataset: {}, disabled: true, title: '' },
  { value: 'saved:cover', dataset: { precisionSavedPreset: 'true', size: '1200x800' }, disabled: true, title: '' },
];
const resizeNodes = {
  precisionResizePreset: { options: resizeOptions, selectedIndex: 1, value: '1024x1024', disabled: true },
  precisionResizeWidth: { value: '' },
  precisionResizeHeight: { value: '' },
  precisionResizePromptPreset: { value: '', dataset: {} },
  precisionResizePrompt: {
    value: 'Extend the background.', maxLength: 500, validationMessage: '', reportCount: 0, focusCount: 0, inputCount: 0,
    setCustomValidity(value) { this.validationMessage = value; },
    reportValidity() { this.reportCount += 1; return false; },
    focus() { this.focusCount += 1; },
    dispatchEvent() { this.inputCount += 1; return true; },
  },
  precisionOutputPolicyStrict: { value: 'strict', checked: true, dataset: {} },
  precisionOutputPolicyFitCrop: { value: 'fit_crop', checked: false, dataset: {} },
  precisionOutputSizePolicyHint: { textContent: '' },
  precisionAspectRatioHint: { textContent: '' },
  btnPrecisionDeleteResizePreset: { disabled: false },
  btnPrecisionResetResizePresets: { disabled: false },
};
const resizeProvider = { id: 'provider-a', model_capabilities: { 'image-edit': {} } };
const resizeContext = vm.createContext({
  document: {
    getElementById: (id) => resizeNodes[id] || null,
    querySelector: (selector) => selector === 'input[name="precisionOutputSizePolicy"]:checked'
      ? (resizeNodes.precisionOutputPolicyFitCrop.checked ? resizeNodes.precisionOutputPolicyFitCrop : resizeNodes.precisionOutputPolicyStrict)
      : null,
  },
  window: { localStorage: { getItem: () => null, setItem: () => {} } },
  precisionEditSelectedModel: { providerId: 'provider-a', model: 'image-edit' },
  precisionEditSizeMode: 'resize',
  precisionOutputSizePolicy: 'strict',
  precisionResizeSavedPresets: [{ id: 'cover' }],
  INPAINT_MAX_PIXELS: 24000000,
  PRECISION_MAX_OUTPUT_PIXELS: 64 * 1024 * 1024,
  findProvider: (id) => id === resizeProvider.id ? resizeProvider : null,
  updatePrecisionEditControls: () => {},
  Event: class Event { constructor(type, options) { this.type = type; this.options = options; } },
  i18nText: (key, params) => ({
    'creator.precision_size_prompt_preset_keep_style_subject': 'Preserve the original style and main elements, extending naturally.',
    'creator.precision_size_prompt_preset_keep_person': 'Keep the person fixed.',
    'creator.precision_size_prompt_preset_banner': 'Expand to a banner.',
    'creator.precision_size_prompt_preset_too_long': 'Too long.',
    'creator.precision_output_size_policy_strict_hint': 'Strict size matching.',
    'creator.precision_output_size_policy_fit_crop_hint': 'Local fit/crop.',
    'creator.precision_aspect_ratio_hint': `Will send ${params?.size} with ${params?.ratio}.`,
    'creator.precision_aspect_ratio_hint_empty': 'Choose size.',
  }[key] || key),
});
vm.runInContext([
  'precisionResizeDimensionKey', 'precisionResizeDimensions', 'precisionCapabilitySizeDeclaration', 'resolvePrecisionModelCapability', 'precisionProviderModelRecords', 'getPrecisionResizeCapability',
  'precisionResizeInputDimension', 'getPrecisionResizeTargetSize', 'precisionResizePresetSize', 'updatePrecisionResizePresetControls', 'updatePrecisionResizeCapabilityUI',
  'sanitizePrecisionOutputSizePolicy', 'syncPrecisionOutputSizePolicyControls', 'setPrecisionOutputSizePolicy', 'getPrecisionOutputSizePolicy',
  'precisionGreatestCommonDivisor', 'precisionResizeAspectConstraint', 'syncPrecisionAspectRatioHint',
  'applyPrecisionResizePreset', 'applyPrecisionResizePromptPreset', 'getPrecisionSizeRequest',
].map(extractFunction).join('\n'), resizeContext);
vm.runInContext('updatePrecisionResizeCapabilityUI()', resizeContext);
assert.ok(resizeOptions.every((option) => option.disabled === false), 'Every built-in and saved resize option must stay enabled when size capability is unknown.');
vm.runInContext("applyPrecisionResizePreset('1536x864')", resizeContext);
assert.equal(resizeNodes.precisionResizeWidth.value, '1536');
assert.equal(resizeNodes.precisionResizeHeight.value, '864');
resizeNodes.precisionResizePrompt.value = '';
resizeProvider.model_capabilities['image-edit'] = { supported_sizes: ['1536x864'] };
let resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.equal(resizeRequest.mode, 'resize', 'Pure resize must submit even when the optional composition field is empty.');
assert.equal(resizeRequest.prompt, 'Preserve the original style and main elements, extending naturally.', 'Pure resize must send the safe default composition guidance without mutating the text field.');
assert.equal(resizeNodes.precisionResizePrompt.value, '', 'The default pure-resize guidance must not overwrite a deliberately empty input.');
resizeNodes.precisionResizePrompt.value = 'Extend the background.';
resizeProvider.model_capabilities['image-edit'] = {};
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.equal(resizeRequest.rejection.code, 'precision_edit_size_capability_unknown', 'Selecting a local preset must not weaken the unknown-capability submission gate.');
resizeProvider.model_capabilities['image-edit'] = { supported_sizes: ['1024x1024'] };
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.equal(resizeRequest.rejection.code, 'precision_edit_size_undeclared', 'An undeclared selected preset must still be rejected at submission.');
resizeNodes.precisionResizeWidth.value = '1024';
resizeNodes.precisionResizeHeight.value = '1024';
resizeProvider.model_capabilities['image-edit'] = { supported_sizes: ['01792x768', ' 1024x1024 ', '1792X768'] };
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.notEqual(resizeRequest.mode, 'resize', 'Noncanonical provider declarations must not authorize a matching resize target.');
assert.ok(resizeRequest.rejection, 'Noncanonical provider declarations must still produce a frontend rejection.');
resizeNodes.precisionResizeWidth.value = '1792';
resizeNodes.precisionResizeHeight.value = '768';
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.notEqual(resizeRequest.mode, 'resize', 'Uppercase or leading-zero provider declarations must not authorize the canonical target.');
assert.ok(resizeRequest.rejection, 'Ignored noncanonical provider declarations must leave the target rejected.');
resizeProvider.model_capabilities['image-edit'] = { supported_sizes: [{ width: 1792, height: 768 }, { w: 1024, h: 1024 }] };
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.notEqual(resizeRequest.mode, 'resize', 'Object-shaped provider declarations must not authorize a resize target.');
assert.equal(vm.runInContext('getPrecisionResizeCapability().known', resizeContext), false, 'Object-shaped provider declarations must not make resize capability known.');
resizeProvider.model_capabilities['image-edit'] = { supported_sizes: ['01792x768', { width: 1792, height: 768 }, { w: 1024, h: 1024 }] };
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.notEqual(resizeRequest.mode, 'resize', 'Mixed arrays with noncanonical strings and objects must not authorize resize.');
assert.equal(vm.runInContext('getPrecisionResizeCapability().known', resizeContext), false, 'Mixed arrays without canonical strings must keep resize capability unknown.');
resizeProvider.model_capabilities['image-edit'] = { supported_sizes: ['1792x768'] };
  resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
  assert.equal(resizeRequest.mode, 'resize', 'A canonical provider declaration must still authorize its exact resize target.');
  assert.equal(resizeRequest.targetSize, '1792x768');
  assert.equal(resizeRequest.outputSizePolicy, 'strict', 'Precision resize must default to strict output-size matching.');
  assert.equal(Object.prototype.hasOwnProperty.call(resizeRequest, 'aspectRatioConstraint'), false, 'Resize request state must not expose a payload-ready aspect field.');
  assert.ok(resizeNodes.precisionAspectRatioHint.textContent.includes('21:9 aspect ratio'), 'The aspect-ratio hint must explain the backend-derived constraint beside the size fields.');
  resizeNodes.precisionOutputPolicyStrict.checked = false;
  resizeNodes.precisionOutputPolicyFitCrop.checked = true;
  resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
  assert.equal(resizeRequest.outputSizePolicy, 'fit_crop', 'Selecting local fit/crop must update the resize request policy.');
  assert.equal(resizeNodes.precisionOutputSizePolicyHint.textContent, '', 'Reading the policy alone must not rewrite the visible hint.');
  vm.runInContext("setPrecisionOutputSizePolicy('fit_crop')", resizeContext);
  assert.equal(resizeNodes.precisionOutputSizePolicyHint.textContent, 'Local fit/crop.', 'Changing the policy control must switch to the fit/crop explanation.');
  resizeProvider.model_capabilities['image-edit'] = { supported_sizes: ['1024x1024'] };
resizeNodes.precisionResizeWidth.value = '1024';
resizeNodes.precisionResizeHeight.value = '1024';
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.equal(resizeRequest.mode, 'resize');
assert.equal(resizeRequest.targetSize, '1024x1024');
for (const [badWidth, badHeight] of [['1024.5', '1024'], ['1e3', '1024'], ['', '1024'], ['01024', '1024'], ['1024 ', '1024']]) {
  resizeNodes.precisionResizeWidth.value = badWidth;
  resizeNodes.precisionResizeHeight.value = badHeight;
  resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
  assert.equal(resizeRequest.error, 'creator.precision_size_invalid', `Non-canonical target dimensions must not be confirmed as ${badWidth}x${badHeight}.`);
  assert.equal(vm.runInContext('getPrecisionResizeTargetSize()', resizeContext), '', `Non-canonical target size must not produce a strict key for ${badWidth}x${badHeight}.`);
}
resizeNodes.precisionResizeWidth.value = '8192';
resizeNodes.precisionResizeHeight.value = '8192';
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.equal(resizeRequest.rejection.code, 'precision_edit_size_undeclared', 'The exact 64Mi precision boundary must pass local validation and reach the capability gate.');
resizeProvider.model_capabilities['image-edit'] = { supported_sizes: ['8192x8192'] };
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.equal(resizeRequest.targetSize, '8192x8192', 'Confirmed 8192x8192 precision resize must be allowed under the precision cap.');
resizeNodes.precisionResizeWidth.value = '8193';
resizeNodes.precisionResizeHeight.value = '8192';
resizeRequest = vm.runInContext('getPrecisionSizeRequest()', resizeContext);
assert.equal(resizeRequest.error, 'creator.precision_size_invalid', 'A side longer than 8192 must still fail closed even with the 64Mi cap.');

resizeNodes.precisionResizePrompt.value = '';
resizeNodes.precisionResizePromptPreset.value = 'creator.precision_size_prompt_preset_keep_person';
assert.equal(vm.runInContext("applyPrecisionResizePromptPreset('creator.precision_size_prompt_preset_keep_person')", resizeContext), true);
assert.equal(resizeNodes.precisionResizePrompt.value, 'Keep the person fixed.', 'An empty guidance field must receive the selected preset.');
assert.equal(resizeNodes.precisionResizePromptPreset.value, '', 'The preset selector must reset so the same preset can be chosen again.');

resizeNodes.precisionResizePrompt.value = 'Keep the sky unchanged.  ';
resizeNodes.precisionResizePromptPreset.value = 'creator.precision_size_prompt_preset_banner';
assert.equal(vm.runInContext("applyPrecisionResizePromptPreset('creator.precision_size_prompt_preset_banner')", resizeContext), true);
assert.equal(resizeNodes.precisionResizePrompt.value, 'Keep the sky unchanged.\nExpand to a banner.', 'Existing free-form guidance must be preserved and the preset appended on a new line.');
assert.equal(resizeNodes.precisionResizePrompt.validationMessage, '');
assert.ok(resizeNodes.precisionResizePrompt.focusCount >= 2 && resizeNodes.precisionResizePrompt.inputCount >= 2, 'Preset insertion must return focus and announce an input update.');

resizeNodes.precisionResizePrompt.value = 'x'.repeat(495);
const beforeOverflow = resizeNodes.precisionResizePrompt.value;
assert.equal(vm.runInContext("applyPrecisionResizePromptPreset('creator.precision_size_prompt_preset_banner')", resizeContext), false);
assert.equal(resizeNodes.precisionResizePrompt.value, beforeOverflow, 'A preset that exceeds maxlength must not truncate or replace existing guidance.');
assert.equal(resizeNodes.precisionResizePrompt.validationMessage, 'Too long.');
assert.equal(resizeNodes.precisionResizePrompt.reportCount, 1);

function resizeControlNode(initial = {}) {
  const listeners = {};
  return Object.assign({
    value: '', disabled: false, hidden: false, textContent: '', innerHTML: '', dataset: {}, attributes: {},
    classList: classListRecorder(), options: [], selectedIndex: 0,
    addEventListener(type, listener) { (listeners[type] ||= []).push(listener); },
    emit(type) { for (const listener of listeners[type] || []) listener.call(this, { type, currentTarget: this, preventDefault() {} }); },
    dispatchEvent(event) { this.emit(event.type); return true; },
    setCustomValidity(value) { this.validationMessage = value; },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    removeAttribute(name) { delete this.attributes[name]; },
    querySelectorAll() { return []; },
  }, initial);
}

const readinessPresetOptions = [
  resizeControlNode({ value: 'custom', dataset: {} }),
  resizeControlNode({ value: '1024x1024', dataset: {} }),
  resizeControlNode({ value: '1536x864', dataset: {} }),
];
const readinessNodes = {
  precisionResizePreset: resizeControlNode({ value: '1024x1024', selectedIndex: 1, options: readinessPresetOptions }),
  precisionResizeWidth: resizeControlNode({ value: '1024' }),
  precisionResizeHeight: resizeControlNode({ value: '1024' }),
  precisionResizePromptPreset: resizeControlNode({ value: '' }),
  precisionResizePrompt: resizeControlNode({ value: '' }),
  precisionOutputPolicyStrict: resizeControlNode({ value: 'strict', checked: true }),
  precisionOutputPolicyFitCrop: resizeControlNode({ value: 'fit_crop', checked: false }),
  precisionOutputSizePolicyHint: resizeControlNode(),
  precisionAspectRatioHint: resizeControlNode(),
  precisionResizeFields: resizeControlNode(),
  precisionSizeHint: resizeControlNode(),
  btnPrecisionSizePreserve: resizeControlNode(),
  btnPrecisionSizeResize: resizeControlNode(),
  btnPrecisionDeleteResizePreset: resizeControlNode({ dataset: { precisionBound: 'true' } }),
  btnPrecisionResetResizePresets: resizeControlNode({ dataset: { precisionBound: 'true' } }),
  btnPrecisionSaveResizePreset: resizeControlNode({ dataset: { precisionBound: 'true' } }),
  precisionResizePresetName: resizeControlNode({ dataset: { precisionBound: 'true' } }),
  precisionResizeCapabilityStatus: resizeControlNode(),
  btnPrecisionConfirmResizeSize: resizeControlNode(),
  btnPrecisionRevokeResizeSize: resizeControlNode(),
  btnPrecisionAuthorizeModel: resizeControlNode(),
  btnPrecisionRevokeModel: resizeControlNode({ classList: classListRecorder(['hidden']) }),
  precisionEditCompatibilityOption: resizeControlNode({ classList: classListRecorder(['hidden']) }),
  precisionEditGptImage2Compatibility: resizeControlNode({ checked: false }),
  precisionEditStatus: resizeControlNode(),
  btnGen: resizeControlNode({ disabled: true }),
  btnStopGen: resizeControlNode(),
  precisionEditProviderEndpoint: resizeControlNode({ value: 'provider-a', options: [resizeControlNode({ value: 'provider-a' })] }),
  precisionEditProviderModel: resizeControlNode({ value: 'provider-a::image-edit', options: [resizeControlNode({ value: 'provider-a::image-edit' })] }),
};
const readinessProvider = {
  id: 'provider-a', type: 'image', enabled: true, has_key: true, endpoint_type: 'openai',
  capabilities: { precision_edit: true }, models: ['image-edit'], model_capabilities: { 'image-edit': { precision_edit: true } },
};
let resizeCapabilityCalls = [];
let resizeCapabilityDeferred = null;
let authorizationConfirmResult = true;
const readinessContext = vm.createContext({
  document: {
    getElementById: (id) => readinessNodes[id] || null,
    querySelector: (selector) => selector === 'input[name="precisionOutputSizePolicy"]:checked'
      ? (readinessNodes.precisionOutputPolicyFitCrop.checked ? readinessNodes.precisionOutputPolicyFitCrop : readinessNodes.precisionOutputPolicyStrict)
      : null,
  },
  window: { localStorage: { getItem: () => null, setItem: () => {} } },
  Event: class Event { constructor(type, options) { this.type = type; this.options = options; } },
  INPAINT_MAX_PIXELS: 24000000,
  PRECISION_MAX_OUTPUT_PIXELS: 64 * 1024 * 1024,
  PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE: 'gpt-image-2',
  allProviders: [readinessProvider],
  selectedProviders: ['provider-a'],
  precisionEditSelectedModel: { providerId: 'provider-a', model: 'image-edit' },
  precisionEditModelPickerReady: true,
  precisionEditAuthorizationPending: false,
  precisionResizeCapabilityPending: null,
  precisionEditSizeMode: 'preserve',
  precisionOutputSizePolicy: 'strict',
  precisionResizeSavedPresets: [],
  precisionEditSourceImageData: 'data:image/png;base64,c291cmNl',
  precisionEditObjects: [], precisionEditHistory: [], precisionEditRedo: [],
  currentMode: 'precision_edit', genCurrentGenId: null, genCancelRequested: false,
  precisionGenerationControlState: 'idle', precisionSourceTaskEpoch: 0, precisionPendingSourceIntent: null,
  confirm: () => authorizationConfirmResult,
  encodeURIComponent,
  i18nText: (key, params) => key === 'creator.precision_size_prompt_preset_banner'
    ? 'Expand to a banner.'
    : key === 'creator.precision_output_size_policy_strict_hint'
    ? 'Strict size matching.'
    : key === 'creator.precision_output_size_policy_fit_crop_hint'
    ? 'Local fit/crop.'
    : key === 'creator.precision_aspect_ratio_hint'
    ? `Will send ${params?.size} with ${params?.ratio}.`
    : key === 'creator.precision_aspect_ratio_hint_empty'
    ? 'Choose size.'
    : params && params.size ? `${key}:${params.size}` : key,
  escHtml: (value) => String(value), escAttr: (value) => String(value),
  renderPrecisionResizeSavedPresets() {}, renderPrecisionEditObjectList() {}, syncPrecisionEditStyleControls() {},
  setPrecisionResizePresetStatus() {},
  updatePrecisionStrokeWidthValue() {}, updatePrecisionAnnotationPreview() {}, updatePrecisionCutoutRefineControls() {},
  updatePrecisionSourceActions() {}, renderProviderList() {}, setStatus() {},
  findProvider: (id) => id === readinessProvider.id ? readinessProvider : null,
  loadProviders: async () => {
    const body = resizeCapabilityCalls.at(-1).body;
    if (body.compatibility_profile) {
      readinessProvider.model_capabilities[body.model] = { alias_of: body.compatibility_profile };
      return;
    }
    if (!Object.prototype.hasOwnProperty.call(body, 'size')) {
      readinessProvider.model_capabilities[body.model] = {};
      return;
    }
    const sizes = readinessProvider.model_capabilities['image-edit'].supported_sizes || [];
    readinessProvider.model_capabilities['image-edit'].supported_sizes = body.enabled
      ? Array.from(new Set(sizes.concat(body.size)))
      : sizes.filter((size) => size !== body.size);
  },
  _authFetch: async (url, options) => {
    resizeCapabilityCalls.push({ url, options, body: JSON.parse(options.body) });
    if (resizeCapabilityDeferred) return resizeCapabilityDeferred.promise;
    return { ok: true, status: 200, json: async () => ({ ok: true }) };
  },
  renderPrecisionEditModelPicker() {},
});
vm.runInContext([
  'precisionResizeDimensionKey', 'precisionResizeDimensions', 'precisionCapabilitySizeDeclaration', 'resolvePrecisionModelCapability', 'precisionProviderModelRecords', 'getPrecisionResizeCapability',
  'precisionResizeInputDimension', 'getPrecisionResizeTargetSize', 'getPrecisionResizeCapabilityState',
  'precisionResizePresetSize', 'updatePrecisionResizePresetControls', 'updatePrecisionResizeCapabilityUI',
  'sanitizePrecisionOutputSizePolicy', 'syncPrecisionOutputSizePolicyControls', 'setPrecisionOutputSizePolicy', 'getPrecisionOutputSizePolicy',
  'precisionGreatestCommonDivisor', 'precisionResizeAspectConstraint', 'syncPrecisionAspectRatioHint',
  'bindPrecisionResizeControls', 'setPrecisionSizeMode', 'applyPrecisionResizePreset', 'applyPrecisionResizePromptPreset',
  'markPrecisionResizeCustom', 'getPrecisionSizeRequest', 'getPrecisionEditReadiness', 'updatePrecisionEditControls',
  'getPrecisionEditModelAuthorizationState', 'updatePrecisionEditAuthorizationControl', 'authorizePrecisionEditModel', 'revokePrecisionEditModel',
  'submitPrecisionResizeCapability', 'confirmPrecisionResizeCapability', 'revokePrecisionResizeCapability',
  'setGenerationControls',
].map(extractFunction).join('\n'), readinessContext);
readinessContext.bindPrecisionResizeControls();

readinessProvider.model_capabilities = {
  'gpt-image-2': { precision_edit: true, supported_sizes: ['1024x1024'] },
};
readinessContext.updatePrecisionEditAuthorizationControl();
assert.equal(readinessContext.getPrecisionEditModelAuthorizationState().authorized, false);
assert.equal(readinessContext.getPrecisionEditModelAuthorizationState().canUseCompatibility, true, 'Any selected upstream model may opt into an explicit canonical compatibility mapping.');
assert.equal(readinessNodes.precisionEditCompatibilityOption.classList.contains('hidden'), false);
readinessNodes.precisionEditGptImage2Compatibility.checked = true;
authorizationConfirmResult = false;
const callsBeforeCancelledAuthorization = resizeCapabilityCalls.length;
readinessContext.authorizePrecisionEditModel();
assert.equal(resizeCapabilityCalls.length, callsBeforeCancelledAuthorization, 'Cancelling compatibility confirmation must not persist or authorize anything.');
assert.equal(readinessProvider.model_capabilities['image-edit'], undefined);

authorizationConfirmResult = true;
readinessContext.authorizePrecisionEditModel();
await new Promise((resolve) => setImmediate(resolve));
assert.deepEqual(resizeCapabilityCalls.at(-1).body, {
  model: 'image-edit', enabled: true, confirmed: true, compatibility_profile: 'gpt-image-2',
});
assert.deepEqual(readinessProvider.model_capabilities['image-edit'], { alias_of: 'gpt-image-2' });
assert.equal(readinessContext.getPrecisionEditModelAuthorizationState().authorized, true);
assert.equal(readinessContext.precisionEditSelectedModel.model, 'image-edit', 'Compatibility mapping must not rewrite the real outbound model ID.');

readinessContext.revokePrecisionEditModel();
await new Promise((resolve) => setImmediate(resolve));
assert.deepEqual(resizeCapabilityCalls.at(-1).body, { model: 'image-edit', enabled: false, confirmed: true });
assert.equal(readinessContext.getPrecisionEditModelAuthorizationState().authorized, false, 'Revoking confirmation must fail closed until the user confirms again.');
assert.equal(readinessNodes.precisionEditGptImage2Compatibility.checked, false, 'Revoking a compatibility mapping must clear its UI choice.');

readinessProvider.model_capabilities = { 'image-edit': { precision_edit: true } };
resizeCapabilityCalls = [];
readinessNodes.btnPrecisionSizeResize.click = () => readinessContext.setPrecisionSizeMode('resize');
readinessNodes.btnPrecisionSizeResize.click();
assert.ok(readinessNodes.precisionAspectRatioHint.textContent.includes('1024x1024'), 'Entering resize mode must render the read-only backend-derived aspect-ratio hint immediately.');
readinessNodes.precisionOutputPolicyStrict.checked = false;
readinessNodes.precisionOutputPolicyFitCrop.checked = true;
readinessNodes.precisionOutputPolicyFitCrop.emit('change');
assert.equal(readinessNodes.precisionOutputSizePolicyHint.textContent, 'Local fit/crop.', 'The fit/crop radio must update the policy hint through the bound control.');
assert.equal(readinessNodes.btnGen.disabled, true, 'Resize must stay disabled while composition guidance is empty.');
readinessNodes.precisionResizePromptPreset.value = 'creator.precision_size_prompt_preset_banner';
readinessNodes.precisionResizePromptPreset.emit('change');
assert.equal(readinessNodes.precisionResizePrompt.value, 'Expand to a banner.', 'A composition preset change must flow through the same readiness input chain.');
assert.equal(readinessNodes.btnGen.disabled, true, 'A model-authorized resize must remain disabled while the exact target size is unconfirmed.');
assert.ok(readinessNodes.precisionResizeCapabilityStatus.textContent.includes('creator.precision_size_capability_unknown'), 'Unknown size capability needs a visible reason beside the size controls.');
assert.equal(readinessNodes.btnPrecisionConfirmResizeSize.disabled, false, 'Unknown size capability must expose an enabled explicit confirmation action.');
readinessProvider.model_capabilities['image-edit'] = { precision_edit: true, supported_sizes: ['01024x1024', ' 1024x1024 ', '1024X1024'] };
readinessContext.updatePrecisionEditControls();
assert.equal(readinessNodes.btnGen.disabled, true, 'Noncanonical provider declarations must not enable pure resize generation.');
assert.ok(readinessNodes.precisionResizeCapabilityStatus.textContent.includes('creator.precision_size_capability_unknown'), 'Ignored noncanonical provider declarations must leave the capability gate unknown.');
readinessProvider.model_capabilities['image-edit'] = { precision_edit: true, supported_sizes: [{ width: 1024, height: 1024 }, { w: 1024, h: 1024 }] };
readinessContext.updatePrecisionEditControls();
assert.equal(readinessContext.getPrecisionResizeCapabilityState().capability.known, false, 'Object-shaped declarations must not make readiness capability known.');
assert.equal(readinessNodes.btnGen.disabled, true, 'Object-shaped provider declarations must not enable pure resize generation.');
readinessProvider.model_capabilities['image-edit'] = { precision_edit: true, supported_sizes: ['01024x1024', { width: 1024, height: 1024 }] };
readinessContext.updatePrecisionEditControls();
assert.equal(readinessContext.getPrecisionResizeCapabilityState().capability.known, false, 'Mixed arrays without canonical strings must not make readiness capability known.');
assert.equal(readinessNodes.btnGen.disabled, true, 'Mixed arrays without canonical strings must not enable pure resize generation.');

readinessProvider.model_capabilities = {
  'image-edit': { alias_of: 'canonical-edit' },
  'canonical-edit': { precision_edit: true, supported_sizes: ['1024x1024'] },
};
readinessContext.updatePrecisionEditControls();
assert.equal(readinessContext.getPrecisionEditModelAuthorizationState().authorized, true, 'A selected alias containing only alias_of must inherit explicit canonical precision authorization.');
assert.equal(readinessContext.getPrecisionResizeCapabilityState().capability.sizes['1024x1024'], true, 'Resize readiness must use the canonical model size declaration.');
assert.equal(readinessContext.precisionEditSelectedModel.model, 'image-edit', 'Canonical capability resolution must not rewrite the selected outbound alias.');
readinessProvider.model_capabilities['canonical-edit'].alias_of = 'image-edit';
readinessContext.updatePrecisionEditControls();
assert.equal(readinessContext.getPrecisionEditModelAuthorizationState().authorized, false, 'Alias cycles must fail closed in UI authorization.');
assert.equal(readinessContext.getPrecisionResizeCapabilityState().capability.known, false, 'Alias cycles must fail closed in resize readiness.');
readinessProvider.model_capabilities = {
  'image-edit': { alias_of: 'canonical-edit', canonical_model: 'other-edit' },
  'canonical-edit': { precision_edit: true, supported_sizes: ['1024x1024'] },
  'other-edit': { precision_edit: true, supported_sizes: ['1024x1024'] },
};
assert.equal(readinessContext.getPrecisionEditModelAuthorizationState().authorized, false, 'Conflicting alias declarations must fail closed.');
readinessProvider.model_capabilities = { 'image-edit': { precision_edit: true } };

readinessNodes.precisionResizePreset.value = '1536x864';
readinessNodes.precisionResizePreset.selectedIndex = 2;
readinessNodes.precisionResizePreset.emit('change');
assert.equal(readinessNodes.precisionResizeWidth.value, '1536');
assert.equal(readinessNodes.precisionResizeHeight.value, '864');
assert.ok(readinessNodes.btnPrecisionConfirmResizeSize.textContent.includes('1536x864'), 'Preset selection must refresh the current-size confirmation label without switching models.');

resizeCapabilityDeferred = deferred();
const confirmSize = readinessContext.confirmPrecisionResizeCapability();
readinessContext.confirmPrecisionResizeCapability();
assert.equal(resizeCapabilityCalls.length, 1, 'A pending exact-size confirmation must suppress duplicate requests.');
assert.deepEqual(resizeCapabilityCalls[0].body, { model: 'image-edit', enabled: true, confirmed: true, size: '1536x864' });
assert.equal(readinessNodes.btnPrecisionConfirmResizeSize.attributes['aria-busy'], 'true');
resizeCapabilityDeferred.resolve({ ok: true, status: 200, json: async () => ({ ok: true }) });
await confirmSize;
resizeCapabilityDeferred = null;
assert.equal(readinessNodes.btnGen.disabled, false, 'A successful exact-size confirmation must enable pure resize immediately without an annotation or model switch.');
assert.ok(readinessNodes.precisionResizeCapabilityStatus.textContent.includes('creator.precision_size_capability_supported'), 'Confirmed size capability needs an explicit supported state.');
assert.equal(readinessNodes.btnPrecisionRevokeResizeSize.disabled, false, 'A confirmed size must expose a revoke action.');

readinessNodes.precisionResizeWidth.value = '1024';
readinessNodes.precisionResizeWidth.emit('input');
readinessNodes.precisionResizeHeight.value = '1024';
readinessNodes.precisionResizeHeight.emit('input');
assert.equal(readinessNodes.btnGen.disabled, true, 'Changing width or height must recompute readiness immediately without switching models.');
assert.ok(readinessNodes.precisionResizeCapabilityStatus.textContent.includes('creator.precision_size_capability_unsupported'), 'A known model with a different confirmed size must show the undeclared-target reason.');
assert.ok(readinessNodes.btnPrecisionConfirmResizeSize.textContent.includes('1024x1024'));
readinessContext.setGenerationControls('idle');
assert.equal(readinessNodes.btnGen.disabled, true, 'Returning to idle must not stale-enable an unconfirmed precision resize.');

readinessNodes.precisionResizePreset.value = '1536x864';
readinessNodes.precisionResizePreset.selectedIndex = 2;
readinessNodes.precisionResizePreset.emit('change');
assert.equal(readinessNodes.btnGen.disabled, false, 'Returning to an already confirmed target must refresh readiness through the preset event chain.');
await readinessContext.revokePrecisionResizeCapability();
assert.deepEqual(resizeCapabilityCalls.at(-1).body, { model: 'image-edit', enabled: false, confirmed: true, size: '1536x864' });
assert.equal(readinessNodes.btnGen.disabled, true, 'Revoking the current-size confirmation must immediately disable pure resize.');

function createPrecisionPointerHarness(objects, tool = 'rect', selectedId = null) {
  const list = {
    innerHTML: '',
    querySelectorAll() { return []; },
  };
  const canvas = {
    tagName: 'CANVAS',
    width: 1000,
    height: 500,
    style: {},
    captured: new Set(),
    releaseCount: 0,
    getBoundingClientRect() { return { left: 0, top: 0, width: 500, height: 250 }; },
    setPointerCapture(pointerId) { this.captured.add(pointerId); },
    hasPointerCapture(pointerId) { return this.captured.has(pointerId); },
    releasePointerCapture(pointerId) {
      this.captured.delete(pointerId);
      this.releaseCount += 1;
      if (this.onRelease) this.onRelease(pointerId);
    },
  };
  const nodes = {
    precisionAnnotationCanvas: canvas,
    precisionAnnotationColor: { value: '#ef4444' },
    precisionStrokeWidth: { value: '5' },
    precisionEditObjectList: list,
  };
  const context = vm.createContext({
    document: { getElementById: (id) => nodes[id] || null },
    __canvas: canvas,
    __list: list,
    __renderCount: 0,
    __controlsCount: 0,
    __focusedIds: [],
    __textPoints: [],
    __erasePoints: [],
  });
  vm.runInContext(`
    var PRECISION_HISTORY_LIMIT = 30;
    var PRECISION_ANNOTATION_MIN_SIZE = 0.004;
    var PRECISION_HANDLE_MOUSE_PX = 10;
    var PRECISION_HANDLE_TOUCH_PX = 24;
    var PRECISION_ANNOTATION_CONTRACT = 'genbox-annotation-v3';
    var precisionEditSourceImageData = 'data:image/png;base64,c291cmNl';
    var precisionEditSourceWidth = 1000;
    var precisionEditSourceHeight = 500;
    var precisionEditObjects = ${JSON.stringify(objects)};
    var precisionEditHistory = [];
    var precisionEditRedo = [];
    var precisionEditTool = ${JSON.stringify(tool)};
    var precisionEditSelectedId = ${JSON.stringify(selectedId)};
    var precisionEditDraftObject = null;
    var precisionEditPointerId = null;
    var precisionEditPointerTarget = null;
    var precisionEditPointerFinishing = false;
    var precisionEditDragOrigin = null;
    var precisionEditDragMoved = false;
    var precisionEditIdCounter = 0;
    var precisionEditLabelCounter = 20;
    var precisionEditPendingInstruction = '';
    var precisionEditEraserSnapshot = null;
    var precisionEditEraserChanged = false;
    var precisionEditSession = { source: { id: 'original' }, versions: [{ id: 'version-1' }], selectedVersionId: 'version-1', baseVersionId: 'original', taskBaseVersionId: 'original', view: 'after', taskId: 'task-1' };
    function precisionEditStyle() { return { color: '#ef4444', strokeWidth: 5 }; }
    function renderPrecisionEditCanvas() { globalThis.__renderCount += 1; }
    function updatePrecisionEditControls() { globalThis.__controlsCount += 1; }
    function focusPrecisionEditInstruction(id) { globalThis.__focusedIds.push(id); }
    function updatePrecisionEditCanvasCursor() {}
    function setStatus() {}
    function openPrecisionEditTextEditor(point) { globalThis.__textPoints.push({ x: point.x, y: point.y }); }
    function erasePrecisionBrushAt(point) { globalThis.__erasePoints.push({ x: point.x, y: point.y }); return true; }
    function precisionCanvasPanRequested() { return false; }
    function beginPrecisionCanvasPan() { return false; }
    function continuePrecisionCanvasPan() { return false; }
    function endPrecisionCanvasPan() { return false; }
    function i18nText(key) { return key; }
    function escAttr(value) { return String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/"/g, '&quot;'); }
    function escHtml(value) { return String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
    ${[
      'precisionEditClone', 'precisionEditNewId', 'precisionEditNewLabel', 'precisionEditCanvasPoint',
      'capturePrecisionEditHistory', 'precisionEditObjectInstruction', 'normalizePrecisionEditObject',
      'precisionEditObjectBounds', 'precisionEditIsBoxShape', 'precisionEditIsTransformable', 'precisionEditApplyBounds', 'precisionEditPointerTolerance',
      'precisionEditShapeHit', 'findPrecisionEditShape', 'findPrecisionEditObject',
      'precisionEditHandlePoints', 'findPrecisionEditHandle', 'precisionEditBrushSegmentIndex', 'beginPrecisionEditBrushNode', 'beginPrecisionEditTransform',
      'precisionEditObjectById', 'beginPrecisionEditPointer', 'applyPrecisionEditPointerPoint',
      'continuePrecisionEditPointer', 'endPrecisionEditPointer', 'precisionEditObjectName',
      'renderPrecisionEditObjectList', 'buildPrecisionEditAnnotationData',
      'undoPrecisionEdit', 'redoPrecisionEdit',
    ].map(extractFunction).join('\n')}
  `, context);
  canvas.onRelease = (pointerId) => {
    context.endPrecisionEditPointer({ pointerId, currentTarget: canvas });
  };
  return { context, canvas, list };
}

function precisionPointer(canvas, x, y, overrides = {}) {
  return {
    pointerId: overrides.pointerId ?? 1,
    pointerType: overrides.pointerType || 'mouse',
    button: overrides.button ?? 0,
    isPrimary: overrides.isPrimary ?? true,
    altKey: overrides.altKey ?? false,
    clientX: x * 500,
    clientY: y * 250,
    currentTarget: canvas,
    preventDefault() { this.defaultPrevented = true; },
  };
}

function precisionPointerState(context) {
  return JSON.parse(vm.runInContext(`JSON.stringify({
    objects: precisionEditObjects,
    history: precisionEditHistory,
    redo: precisionEditRedo,
    selectedId: precisionEditSelectedId,
    draft: precisionEditDraftObject,
    pointerId: precisionEditPointerId,
    dragOrigin: precisionEditDragOrigin,
    dragMoved: precisionEditDragMoved,
    eraserSnapshot: precisionEditEraserSnapshot,
    session: precisionEditSession
  })`, context));
}

function closeTo(actual, expected, message) {
  assert.ok(Math.abs(actual - expected) < 1e-9, message + `: expected ${expected}, got ${actual}`);
}

const bottomRect = { id: 'rect-bottom', type: 'rect', x: 0.1, y: 0.1, x2: 0.55, y2: 0.55, label: 1, instruction: 'bottom' };
const topEllipse = { id: 'ellipse-top', type: 'ellipse', x: 0.2, y: 0.2, x2: 0.6, y2: 0.6, label: 2, instruction: 'top' };
const ignoredArrow = { id: 'arrow-topmost', type: 'arrow', x: 0.25, y: 0.25, x2: 0.45, y2: 0.45, label: 3, instruction: 'arrow' };
const hitHarness = createPrecisionPointerHarness([bottomRect, topEllipse, ignoredArrow]);
assert.equal(hitHarness.context.findPrecisionEditShape({ x: 0.4, y: 0.4 }, precisionPointer(hitHarness.canvas, 0.4, 0.4)).id, 'ellipse-top', 'Reverse hit testing must select the topmost box shape and skip arrows.');
assert.equal(hitHarness.context.precisionEditShapeHit({ x: 0.4, y: 0.4 }, topEllipse, { x: 0, y: 0 }), true, 'Ellipse center must hit.');
assert.equal(hitHarness.context.precisionEditShapeHit({ x: 0.21, y: 0.21 }, topEllipse, { x: 0, y: 0 }), false, 'Ellipse bounding-box corners must miss the ellipse equation.');
assert.equal(hitHarness.context.precisionEditShapeHit({ x: 0.11, y: 0.11 }, bottomRect, { x: 0, y: 0 }), true, 'Rectangle interior must hit.');
assert.equal(hitHarness.context.precisionEditShapeHit({ x: 0.05, y: 0.05 }, bottomRect, { x: 0, y: 0 }), false, 'Rectangle exterior must miss.');

for (const [handle, point] of Object.entries({ nw: [0.2, 0.2], ne: [0.6, 0.2], sw: [0.2, 0.6], se: [0.6, 0.6] })) {
  assert.equal(hitHarness.context.findPrecisionEditHandle({ x: point[0], y: point[1] }, topEllipse, precisionPointer(hitHarness.canvas, point[0], point[1])), handle, `Exact ${handle} corner must hit its resize handle.`);
}
assert.equal(hitHarness.context.findPrecisionEditHandle({ x: 0.235, y: 0.2 }, topEllipse, precisionPointer(hitHarness.canvas, 0.235, 0.2)), null, 'Mouse handle tolerance must stay compact.');
assert.equal(hitHarness.context.findPrecisionEditHandle({ x: 0.235, y: 0.2 }, topEllipse, precisionPointer(hitHarness.canvas, 0.235, 0.2, { pointerType: 'touch' })), 'nw', 'Touch handle tolerance must be larger than mouse tolerance.');
assert.equal(hitHarness.context.findPrecisionEditHandle({ x: 0.26, y: 0.2 }, topEllipse, precisionPointer(hitHarness.canvas, 0.26, 0.2, { pointerType: 'touch' })), null, 'Points outside touch tolerance must not begin a resize.');

const movableRect = { id: 'box-1', type: 'rect', x: 0.2, y: 0.2, x2: 0.4, y2: 0.5, color: '#123456', strokeWidth: 7, label: 9, instruction: 'Keep this instruction' };
const moveHarness = createPrecisionPointerHarness([movableRect], 'ellipse');
const moveSessionBefore = precisionPointerState(moveHarness.context).session;
moveHarness.context.beginPrecisionEditPointer(precisionPointer(moveHarness.canvas, 0.3, 0.35));
let moveState = precisionPointerState(moveHarness.context);
assert.equal(moveState.selectedId, 'box-1', 'Either box tool must reselect an existing rectangle.');
assert.equal(moveState.draft, null, 'Selecting an existing shape must not create a draft.');
assert.equal(moveState.dragOrigin.mode, 'move');
assert.equal(moveHarness.canvas.captured.has(1), true, 'Move gestures must capture the pointer.');
moveHarness.context.continuePrecisionEditPointer(precisionPointer(moveHarness.canvas, 0.5, 0.45));
moveHarness.context.endPrecisionEditPointer(precisionPointer(moveHarness.canvas, 0.5, 0.45));
moveState = precisionPointerState(moveHarness.context);
assert.equal(moveState.objects.length, 1);
assert.equal(moveState.objects[0].id, 'box-1');
assert.equal(moveState.objects[0].label, 9);
assert.equal(moveState.objects[0].instruction, 'Keep this instruction');
closeTo(moveState.objects[0].x, 0.4, 'Move must translate the left edge');
closeTo(moveState.objects[0].y, 0.3, 'Move must translate the top edge');
closeTo(moveState.objects[0].x2, 0.6, 'Move must translate the right edge');
closeTo(moveState.objects[0].y2, 0.6, 'Move must translate the bottom edge');
assert.equal(moveState.history.length, 1, 'A move gesture must create exactly one undo snapshot.');
assert.equal(moveState.redo.length, 0);
assert.equal(moveState.pointerId, null);
assert.equal(moveHarness.canvas.captured.size, 0, 'Pointer capture must be released after a move.');
assert.equal(moveHarness.canvas.releaseCount, 1, 'Synchronous lostpointercapture must not double-finalize the gesture.');
assert.deepEqual(moveState.session, moveSessionBefore, 'Geometry edits must not alter version/base session state.');

moveHarness.context.renderPrecisionEditObjectList();
assert.ok(moveHarness.list.innerHTML.includes('data-precision-instruction="box-1"'), 'Transformed objects must retain their per-object textarea identity.');
assert.ok(moveHarness.list.innerHTML.includes('Keep this instruction'), 'Transforming a shape must preserve its instruction text.');

moveHarness.context.undoPrecisionEdit();
moveState = precisionPointerState(moveHarness.context);
closeTo(moveState.objects[0].x, 0.2, 'Undo must restore the pre-move box in one step');
assert.equal(moveState.redo.length, 1);
moveHarness.context.redoPrecisionEdit();
moveState = precisionPointerState(moveHarness.context);
closeTo(moveState.objects[0].x, 0.4, 'Redo must restore the moved box in one step');
moveHarness.context.undoPrecisionEdit();
moveHarness.context.beginPrecisionEditPointer(precisionPointer(moveHarness.canvas, 0.3, 0.35, { pointerId: 2 }));
moveHarness.context.endPrecisionEditPointer(precisionPointer(moveHarness.canvas, 0.4, 0.35, { pointerId: 2 }));
moveState = precisionPointerState(moveHarness.context);
assert.equal(moveState.redo.length, 0, 'A new geometry gesture must clear redo history.');

const edgeMoveHarness = createPrecisionPointerHarness([movableRect], 'rect');
edgeMoveHarness.context.beginPrecisionEditPointer(precisionPointer(edgeMoveHarness.canvas, 0.3, 0.35));
edgeMoveHarness.context.endPrecisionEditPointer(precisionPointer(edgeMoveHarness.canvas, 1.6, 0.35));
const edgeMoveState = precisionPointerState(edgeMoveHarness.context);
closeTo(edgeMoveState.objects[0].x, 0.8, 'Move clamping must keep the whole box inside the right edge');
closeTo(edgeMoveState.objects[0].x2, 1, 'Move clamping must reach the right canvas edge');
closeTo(edgeMoveState.objects[0].x2 - edgeMoveState.objects[0].x, 0.2, 'Move clamping must preserve box width');
assert.equal(edgeMoveState.history.length, 1, 'A captured pointerup outside the canvas must still commit once.');

const cancelHarness = createPrecisionPointerHarness([movableRect], 'rect');
cancelHarness.context.beginPrecisionEditPointer(precisionPointer(cancelHarness.canvas, 0.3, 0.35));
cancelHarness.context.continuePrecisionEditPointer(precisionPointer(cancelHarness.canvas, 0.45, 0.4));
cancelHarness.context.endPrecisionEditPointer({ ...precisionPointer(cancelHarness.canvas, 0.45, 0.4), type: 'pointercancel' });
cancelHarness.context.endPrecisionEditPointer({ pointerId: 1, currentTarget: cancelHarness.canvas, type: 'lostpointercapture' });
const cancelState = precisionPointerState(cancelHarness.context);
assert.equal(cancelState.history.length, 1, 'Pointer cancel followed by lost capture must finalize history only once.');
assert.equal(cancelHarness.canvas.releaseCount, 1, 'Pointer cancel must release capture once.');

const ellipseToResize = { id: 'ellipse-1', type: 'ellipse', x: 0.2, y: 0.2, x2: 0.6, y2: 0.7, color: '#abcdef', strokeWidth: 6, label: 7, instruction: 'Resize this region' };
const resizeHarness = createPrecisionPointerHarness([ellipseToResize], 'rect', 'ellipse-1');
resizeHarness.context.beginPrecisionEditPointer(precisionPointer(resizeHarness.canvas, 0.6, 0.7));
let transformState = precisionPointerState(resizeHarness.context);
assert.equal(transformState.dragOrigin.mode, 'resize');
assert.equal(transformState.dragOrigin.handle, 'se');
resizeHarness.context.endPrecisionEditPointer(precisionPointer(resizeHarness.canvas, 0.1, 0.1));
transformState = precisionPointerState(resizeHarness.context);
closeTo(transformState.objects[0].x, 0.2, 'SE resize must keep the opposite left edge fixed');
closeTo(transformState.objects[0].y, 0.2, 'SE resize must keep the opposite top edge fixed');
closeTo(transformState.objects[0].x2, 0.204, 'Resize crossing must clamp to minimum width');
closeTo(transformState.objects[0].y2, 0.204, 'Resize crossing must clamp to minimum height');
assert.equal(transformState.history.length, 1, 'A resize gesture must create exactly one undo snapshot.');
const resizedPayload = JSON.parse(vm.runInContext('JSON.stringify(buildPrecisionEditAnnotationData())', resizeHarness.context));
assert.equal(resizedPayload.contract, 'genbox-annotation-v3');
assert.equal(resizedPayload.coordinate_space, 'normalized-0-1');
assert.equal(resizedPayload.objects[0].type, 'ellipse');
closeTo(resizedPayload.objects[0].x, 0.2, 'Serialized ellipse x must remain normalized');
closeTo(resizedPayload.objects[0].width, 0.004, 'Serialized ellipse width must preserve the minimum size');
assert.equal(resizedPayload.objects[0].label, 7);
assert.equal(resizedPayload.objects[0].instruction, 'Resize this region');
resizeHarness.context.undoPrecisionEdit();
transformState = precisionPointerState(resizeHarness.context);
closeTo(transformState.objects[0].x2, 0.6, 'Resize undo must restore the original corner in one step');
resizeHarness.context.redoPrecisionEdit();
transformState = precisionPointerState(resizeHarness.context);
closeTo(transformState.objects[0].x2, 0.204, 'Resize redo must restore the changed corner in one step');

const edgeResizeHarness = createPrecisionPointerHarness([ellipseToResize], 'ellipse', 'ellipse-1');
edgeResizeHarness.context.beginPrecisionEditPointer(precisionPointer(edgeResizeHarness.canvas, 0.2, 0.2));
edgeResizeHarness.context.endPrecisionEditPointer(precisionPointer(edgeResizeHarness.canvas, -0.5, -0.5));
const edgeResizeState = precisionPointerState(edgeResizeHarness.context);
closeTo(edgeResizeState.objects[0].x, 0, 'NW resize must clamp to the left edge');
closeTo(edgeResizeState.objects[0].y, 0, 'NW resize must clamp to the top edge');
closeTo(edgeResizeState.objects[0].x2, 0.6, 'NW resize must keep the opposite right edge fixed');
closeTo(edgeResizeState.objects[0].y2, 0.7, 'NW resize must keep the opposite bottom edge fixed');
for (const key of ['x', 'y', 'x2', 'y2']) assert.ok(edgeResizeState.objects[0][key] >= 0 && edgeResizeState.objects[0][key] <= 1, 'Resized coordinates must stay normalized.');

const clickHarness = createPrecisionPointerHarness([movableRect], 'rect');
clickHarness.context.beginPrecisionEditPointer(precisionPointer(clickHarness.canvas, 0.3, 0.35));
clickHarness.context.endPrecisionEditPointer(precisionPointer(clickHarness.canvas, 0.3, 0.35));
const clickState = precisionPointerState(clickHarness.context);
assert.equal(clickState.objects.length, 1, 'Clicking a shape without moving must not create another object.');
assert.equal(clickState.history.length, 0, 'Selection-only clicks must not create history.');

const blankSelectHarness = createPrecisionPointerHarness([movableRect], 'select', 'box-1');
blankSelectHarness.context.beginPrecisionEditPointer(precisionPointer(blankSelectHarness.canvas, 0.9, 0.9));
blankSelectHarness.context.endPrecisionEditPointer(precisionPointer(blankSelectHarness.canvas, 0.9, 0.9));
const blankSelectState = precisionPointerState(blankSelectHarness.context);
assert.equal(blankSelectState.selectedId, null, 'Select/Move must clear selection when clicking blank canvas space.');
assert.equal(blankSelectState.objects.length, 1, 'Select/Move blank clicks must not create a shape.');
assert.equal(blankSelectState.draft, null, 'Select/Move blank clicks must not create a draft.');
assert.equal(blankSelectState.history.length, 0, 'Select/Move blank clicks must not create an undo snapshot.');
assert.equal(blankSelectState.redo.length, 0, 'Select/Move blank clicks must not mutate redo history.');
assert.equal(blankSelectState.pointerId, null, 'Select/Move blank clicks must not enter pointer capture.');
assert.equal(blankSelectHarness.canvas.captured.size, 0, 'Select/Move blank clicks must leave the canvas uncaptured.');

const returnHarness = createPrecisionPointerHarness([movableRect], 'rect');
returnHarness.context.beginPrecisionEditPointer(precisionPointer(returnHarness.canvas, 0.3, 0.35));
returnHarness.context.continuePrecisionEditPointer(precisionPointer(returnHarness.canvas, 0.5, 0.45));
returnHarness.context.continuePrecisionEditPointer(precisionPointer(returnHarness.canvas, 0.3, 0.35));
returnHarness.context.endPrecisionEditPointer(precisionPointer(returnHarness.canvas, 0.3, 0.35));
const returnState = precisionPointerState(returnHarness.context);
closeTo(returnState.objects[0].x, 0.2, 'Returning to the gesture origin must restore the original box');
assert.equal(returnState.history.length, 0, 'A transform ending at its origin must not create history.');

const altHarness = createPrecisionPointerHarness([movableRect], 'rect');
altHarness.context.beginPrecisionEditPointer(precisionPointer(altHarness.canvas, 0.3, 0.35, { altKey: true }));
assert.equal(precisionPointerState(altHarness.context).draft.type, 'rect', 'Alt/Option pointerdown must force a new box draft over an existing shape.');

for (const draftTool of ['arrow', 'brush']) {
  const toolHarness = createPrecisionPointerHarness([movableRect], draftTool);
  toolHarness.context.beginPrecisionEditPointer(precisionPointer(toolHarness.canvas, 0.3, 0.35));
  const toolState = precisionPointerState(toolHarness.context);
  assert.equal(toolState.draft.type, draftTool, `${draftTool} must keep drawing over existing shapes.`);
  if (draftTool === 'brush') assert.equal(toolState.draft.points.length, 1, 'Brush drafts must retain their first point.');
}

const textHarness = createPrecisionPointerHarness([movableRect], 'text');
textHarness.context.beginPrecisionEditPointer(precisionPointer(textHarness.canvas, 0.3, 0.35));
assert.equal(textHarness.context.__textPoints.length, 1, 'Text pointerdown must keep opening the inline text editor.');
assert.equal(precisionPointerState(textHarness.context).pointerId, null, 'Text editing must not enter box pointer capture.');

const brushObject = { id: 'brush-1', type: 'brush', points: [{ x: 0.1, y: 0.1 }, { x: 0.4, y: 0.4 }], label: 4, instruction: 'erase' };
const eraserHarness = createPrecisionPointerHarness([brushObject], 'eraser');
eraserHarness.context.beginPrecisionEditPointer(precisionPointer(eraserHarness.canvas, 0.25, 0.25));
const eraserState = precisionPointerState(eraserHarness.context);
assert.equal(eraserHarness.context.__erasePoints.length, 1, 'Eraser pointerdown must still invoke brush erasing.');
assert.equal(eraserState.eraserSnapshot[0].id, 'brush-1', 'Eraser must retain its gesture-start snapshot.');

const selectedEraseObject = { id: 'erase-rect', type: 'rect', x: 0.2, y: 0.2, x2: 0.4, y2: 0.4, label: 8, instruction: 'delete me' };
const selectedEraserHarness = createPrecisionPointerHarness([selectedEraseObject], 'eraser', 'erase-rect');
selectedEraserHarness.context.beginPrecisionEditPointer(precisionPointer(selectedEraserHarness.canvas, 0.3, 0.3));
const selectedEraserState = precisionPointerState(selectedEraserHarness.context);
assert.equal(selectedEraserState.objects.length, 0, 'Eraser must delete a selected annotation when clicked.');
assert.equal(selectedEraserState.history.length, 1, 'Selected annotation deletion must be undoable.');

const arrowObject = { id: 'arrow-1', type: 'arrow', x: 0.2, y: 0.2, x2: 0.4, y2: 0.4, label: 5, instruction: 'move arrow' };
const arrowHarness = createPrecisionPointerHarness([arrowObject], 'arrow', 'arrow-1');
arrowHarness.context.beginPrecisionEditPointer(precisionPointer(arrowHarness.canvas, 0.3, 0.3));
arrowHarness.context.endPrecisionEditPointer(precisionPointer(arrowHarness.canvas, 0.5, 0.4));
const arrowState = precisionPointerState(arrowHarness.context);
assert.equal(arrowState.objects[0].type, 'arrow');
closeTo(arrowState.objects[0].x, 0.4, 'Arrow move must translate its start point');
closeTo(arrowState.objects[0].x2, 0.6, 'Arrow move must translate its end point');
assert.equal(arrowState.history.length, 1, 'Arrow move must be undoable as one gesture.');

const arrowStartHarness = createPrecisionPointerHarness([arrowObject], 'select', 'arrow-1');
arrowStartHarness.context.beginPrecisionEditPointer(precisionPointer(arrowStartHarness.canvas, 0.2, 0.2));
let arrowEndpointState = precisionPointerState(arrowStartHarness.context);
assert.equal(arrowEndpointState.dragOrigin.mode, 'resize', 'Mouse pointerdown on an arrow endpoint must begin endpoint scaling.');
assert.equal(arrowEndpointState.dragOrigin.handle, 'start', 'The arrow start handle must be identified independently.');
arrowStartHarness.context.continuePrecisionEditPointer(precisionPointer(arrowStartHarness.canvas, -0.2, 1.2));
arrowStartHarness.context.endPrecisionEditPointer(precisionPointer(arrowStartHarness.canvas, -0.2, 1.2));
arrowEndpointState = precisionPointerState(arrowStartHarness.context);
closeTo(arrowEndpointState.objects[0].x, 0, 'Arrow start x must clamp to the left canvas edge');
closeTo(arrowEndpointState.objects[0].y, 1, 'Arrow start y must clamp to the bottom canvas edge');
closeTo(arrowEndpointState.objects[0].x2, 0.4, 'Dragging the start handle must preserve the arrow end x');
closeTo(arrowEndpointState.objects[0].y2, 0.4, 'Dragging the start handle must preserve the arrow end y');
assert.equal(arrowEndpointState.objects[0].instruction, 'move arrow', 'Arrow endpoint scaling must preserve its instruction binding.');
assert.equal(arrowEndpointState.history.length, 1, 'One arrow endpoint gesture must create exactly one history snapshot.');
assert.equal(arrowStartHarness.canvas.releaseCount, 1, 'Arrow endpoint scaling must release pointer capture once.');
arrowStartHarness.context.renderPrecisionEditObjectList();
assert.ok(arrowStartHarness.list.innerHTML.includes('data-precision-instruction="arrow-1"'), 'Arrow endpoint scaling must retain the instruction textarea identity.');
assert.ok(arrowStartHarness.list.innerHTML.includes('move arrow'), 'Arrow endpoint scaling must retain instruction text in the object list.');
arrowStartHarness.context.undoPrecisionEdit();
arrowEndpointState = precisionPointerState(arrowStartHarness.context);
closeTo(arrowEndpointState.objects[0].x, 0.2, 'Arrow endpoint undo must restore the start x in one step');
closeTo(arrowEndpointState.objects[0].y, 0.2, 'Arrow endpoint undo must restore the start y in one step');
assert.equal(arrowEndpointState.objects[0].instruction, 'move arrow');
assert.equal(arrowEndpointState.redo.length, 1, 'Arrow endpoint undo must create one redo snapshot.');
arrowStartHarness.context.redoPrecisionEdit();
arrowEndpointState = precisionPointerState(arrowStartHarness.context);
closeTo(arrowEndpointState.objects[0].x, 0, 'Arrow endpoint redo must restore the clamped start x');
closeTo(arrowEndpointState.objects[0].y, 1, 'Arrow endpoint redo must restore the clamped start y');

const arrowEndHarness = createPrecisionPointerHarness([arrowObject], 'select', 'arrow-1');
const touchEndEvent = precisionPointer(arrowEndHarness.canvas, 0.435, 0.4, { pointerType: 'touch', pointerId: 7 });
assert.equal(arrowEndHarness.context.findPrecisionEditHandle({ x: 0.435, y: 0.4 }, arrowObject, touchEndEvent), 'end', 'Touch hit testing must accept a larger target near the arrow end handle.');
assert.equal(arrowEndHarness.context.findPrecisionEditHandle({ x: 0.435, y: 0.4 }, arrowObject, precisionPointer(arrowEndHarness.canvas, 0.435, 0.4)), null, 'The same near-handle point must remain outside the compact mouse target.');
arrowEndHarness.context.beginPrecisionEditPointer(touchEndEvent);
arrowEndpointState = precisionPointerState(arrowEndHarness.context);
assert.equal(arrowEndpointState.dragOrigin.handle, 'end', 'Touch pointerdown must bind the arrow end handle.');
arrowEndHarness.context.endPrecisionEditPointer(precisionPointer(arrowEndHarness.canvas, 1.4, -0.3, { pointerType: 'touch', pointerId: 7 }));
arrowEndpointState = precisionPointerState(arrowEndHarness.context);
closeTo(arrowEndpointState.objects[0].x, 0.2, 'Dragging the end handle must preserve the arrow start x');
closeTo(arrowEndpointState.objects[0].y, 0.2, 'Dragging the end handle must preserve the arrow start y');
closeTo(arrowEndpointState.objects[0].x2, 1, 'Arrow end x must clamp to the right canvas edge');
closeTo(arrowEndpointState.objects[0].y2, 0, 'Arrow end y must clamp to the top canvas edge');
assert.equal(arrowEndpointState.objects[0].instruction, 'move arrow', 'Touch endpoint scaling must preserve the instruction binding.');
assert.equal(arrowEndpointState.history.length, 1, 'One touch endpoint gesture must create exactly one history snapshot.');
arrowEndHarness.context.undoPrecisionEdit();
arrowEndpointState = precisionPointerState(arrowEndHarness.context);
closeTo(arrowEndpointState.objects[0].x2, 0.4, 'Touch endpoint undo must restore the original end x');
closeTo(arrowEndpointState.objects[0].y2, 0.4, 'Touch endpoint undo must restore the original end y');
arrowEndHarness.context.redoPrecisionEdit();
arrowEndpointState = precisionPointerState(arrowEndHarness.context);
closeTo(arrowEndpointState.objects[0].x2, 1, 'Touch endpoint redo must restore the clamped end x');
closeTo(arrowEndpointState.objects[0].y2, 0, 'Touch endpoint redo must restore the clamped end y');

const reverseArrow = { id: 'arrow-reverse', type: 'arrow', x: 0.6, y: 0.2, x2: 0.2, y2: 0.5, label: 9, instruction: 'keep direction' };
const reverseArrowHarness = createPrecisionPointerHarness([reverseArrow], 'arrow', 'arrow-reverse');
reverseArrowHarness.context.beginPrecisionEditPointer(precisionPointer(reverseArrowHarness.canvas, 0.4, 0.35));
reverseArrowHarness.context.endPrecisionEditPointer(precisionPointer(reverseArrowHarness.canvas, 0.5, 0.45));
const reverseArrowState = precisionPointerState(reverseArrowHarness.context);
assert.ok(reverseArrowState.objects[0].x > reverseArrowState.objects[0].x2, 'Moving a reverse arrow must preserve its horizontal direction.');
assert.ok(reverseArrowState.objects[0].y < reverseArrowState.objects[0].y2, 'Moving a reverse arrow must preserve its vertical direction.');

const brushMove = { id: 'brush-move', type: 'brush', points: [{ x: 0.2, y: 0.2 }, { x: 0.4, y: 0.4 }], label: 6, instruction: 'move brush' };
const brushMoveHarness = createPrecisionPointerHarness([brushMove], 'brush', 'brush-move');
brushMoveHarness.context.beginPrecisionEditPointer(precisionPointer(brushMoveHarness.canvas, 0.3, 0.3));
brushMoveHarness.context.endPrecisionEditPointer(precisionPointer(brushMoveHarness.canvas, 0.5, 0.4));
const brushMoveState = precisionPointerState(brushMoveHarness.context);
closeTo(brushMoveState.objects[0].points[0].x, 0.4, 'Brush move must translate every point');
assert.equal(brushMoveState.history.length, 1, 'Brush move must be undoable as one gesture.');

const textObject = { id: 'text-move', type: 'text', x: 0.2, y: 0.2, text: 'Edit me', fontSize: 24, label: 7, instruction: 'move text' };
const textMoveHarness = createPrecisionPointerHarness([textObject], 'text', 'text-move');
textMoveHarness.context.beginPrecisionEditPointer(precisionPointer(textMoveHarness.canvas, 0.25, 0.22));
textMoveHarness.context.endPrecisionEditPointer(precisionPointer(textMoveHarness.canvas, 0.45, 0.42));
const textMoveState = precisionPointerState(textMoveHarness.context);
closeTo(textMoveState.objects[0].x, 0.4, 'Text move must translate the annotation');
assert.equal(textMoveState.objects[0].text, 'Edit me', 'Text move must preserve text content.');

expect(html.includes('id="btnPrecisionCutout"') && js.includes("_authFetch('/api/image-tools/cutout/capabilities'"), 'Cutout must use the real capability endpoint.');
expect(html.includes('data-i18n="creator.cutout_person"') && html.includes('data-i18n="creator.cutout_person_hint"') && html.includes('data-i18n="creator.cutout_unconfigured_clear"'), 'Cutout must explain the person-extraction scope and unavailable fallback in the UI.');
const cutoutFlow = js.slice(js.indexOf('function precisionCutoutHasSource'), js.indexOf('function exportPrecisionEditAnnotationImage'));
expect(cutoutFlow.includes("_authFetch('/api/image-tools/cutout'") && cutoutFlow.includes('adapter: selectedAdapter.adapter') && cutoutFlow.includes('algorithm: selectedAdapter.algorithm'), 'Cutout must POST the canonical adapter ID and matching algorithm description.');
expect(cutoutFlow.includes('if (precisionCutoutPending) return Promise.resolve(false);') && cutoutFlow.includes('precisionCutoutIsExecutable(capability)'), 'Cutout must prevent duplicate clicks and fail closed unless the capability probe is executable.');
expect(cutoutFlow.includes('appendPrecisionCutoutVersion(result, requestWidth, requestHeight, requestParentId)') && !cutoutFlow.includes('loadPrecisionEditSourceImage('), 'Cutout success must append a version without replacing the editable base.');
expect(!cutoutFlow.includes("/api/generate"), 'Cutout must never submit provider generation.');
expect(html.includes('id="precisionCutoutFeather"') && /id="precisionCutoutFeather"[^>]*min="0"[^>]*max="64"/.test(html), 'Cutout refinement needs a bounded 0..64 feather control.');
expect(html.includes('id="precisionCutoutUseSelection"') && html.includes('id="precisionCutoutRestoreMode"') && html.includes('id="precisionCutoutRestoreMinAlpha"') && html.includes('id="btnPrecisionCutoutRefine"') && html.includes('id="btnPrecisionCutoutCancel"'), 'Cutout refinement needs optional selection, restore, submit, and client-cancel controls.');
expect(cutoutFlow.includes("_authFetch('/api/image-tools/cutout/refine'") && cutoutFlow.includes("contract: PRECISION_CUTOUT_REFINE_CONTRACT") && cutoutFlow.includes("payload.selection_mask_contract = PRECISION_CUTOUT_SELECTION_MASK_CONTRACT") && cutoutFlow.includes("payload.restore_mode = true") && cutoutFlow.includes("payload.restore_source_image_data = requestBaseSource") && cutoutFlow.includes("payload.restore_min_alpha = restoreMinAlpha"), 'Cutout refinement must POST the exact local refine contract and thread restore fields through the payload.');
expect(cutoutFlow.includes('result.parent_version_id !== expectedParentId') && cutoutFlow.includes('result.preview_background !== \'checkerboard\'') && cutoutFlow.includes('requestGeneration !== precisionSourceLoadGeneration') && cutoutFlow.includes('appendPrecisionCutoutRefineVersion(result, requestWidth, requestHeight, requestParentId, featherRadius, restoreMode, restoreMinAlpha, selectionApplied)'), 'Refine success must validate its parent, transparent preview contract, current source generation, and restore-aware append path before append.');
expect(cutoutFlow.includes('precisionCutoutOperationToken += 1') && cutoutFlow.includes('precisionCutoutAbortController.abort()'), 'Client cancellation must invalidate and abort the active cutout request so late results cannot append.');
expect(/\.precision-compare-stage,\s*\.precision-compare-after-wrap\s*\{[\s\S]*?background-color:\s*#f3f4f6;[\s\S]*?background-image:/.test(css), 'The after layer needs its own opaque checkerboard so transparent pixels never reveal the original image.');
expect(js.includes('reader.readAsDataURL(blob)') && js.includes('function setPrecisionBaseVersion'), 'Use as next base must convert gallery URLs to data URLs.');
expect(js.includes('function drawPrecisionEditLabel'), 'Structured overlays must draw label numbers for the model.');
expect(js.includes('function precisionEditIsTransformable') && js.includes('function precisionEditApplyBounds'), 'All completed annotation types need a shared local transform path.');
expect(js.includes("canvas.addEventListener('dblclick'") && js.includes('precisionEditTextEditingId'), 'Existing text annotations must have an inline edit path.');
expect(js.includes('function syncPrecisionEditStyleControls') && js.includes('function updatePrecisionSelectedStyle'), 'Selected annotations must expose editable color, width, and text-size state.');
expect(js.includes('precision_edit_eraser_deleted') && js.includes('findPrecisionEditObject(point, event) === selectedObject'), 'Eraser must clearly delete a selected annotation as well as erase brush paths.');
const visibilityRenderSource = extractFunction('renderPrecisionModelVisibility');
expect(js.includes("genbox_precision_model_visibility_v1") && js.includes('data-precision-model-visibility'), 'Model display preferences need a versioned local-only checkbox state.');
expect(
  visibilityRenderSource.includes('data-precision-model-visibility-toggle') &&
    visibilityRenderSource.includes('aria-haspopup="dialog"') &&
    visibilityRenderSource.includes('role="dialog"') &&
    visibilityRenderSource.includes('title="') &&
    visibilityRenderSource.includes('data-precision-model-visibility-action="confirm"') &&
    visibilityRenderSource.includes('data-precision-model-visibility-action="cancel"'),
  'Model display preferences must render as a compact trigger with titled long-name rows and a confirm/cancel popover menu.',
);
expect(
  visibilityMenuSource.includes("event.key === 'Escape'") &&
    visibilityMenuSource.includes("event.key !== 'Tab'") &&
    visibilityMenuSource.includes('focusPrecisionModelVisibilityTrigger(providerId)') &&
    visibilityMenuSource.includes('focusFirstPrecisionModelVisibilityControl()') &&
    visibilityMenuSource.includes('positionPrecisionModelVisibilityMenu()') &&
    visibilityMenuSource.includes("window.addEventListener('resize', positionPrecisionModelVisibilityMenu, true)") &&
    visibilityMenuSource.includes("window.addEventListener('scroll', positionPrecisionModelVisibilityMenu, true)") &&
    visibilityMenuSource.includes("window.visualViewport.addEventListener('resize', positionPrecisionModelVisibilityMenu)") &&
    visibilityMenuSource.includes("window.visualViewport.addEventListener('scroll', positionPrecisionModelVisibilityMenu)") &&
    visibilityMenuSource.includes('document.body.appendChild(menu)') &&
    visibilityMenuSource.includes('panel.contains') &&
    visibilityMenuSource.includes('menu.contains') &&
    visibilityMenuSource.includes('cancelPrecisionModelVisibilityMenu()'),
  'Model display menu must cancel on Escape or outside pointer dismissal, trap Tab focus, portal out of clipping ancestors, and reposition with viewport/scroll changes while open.',
);
expect(
  visibilityRenderSource.includes('var menuRoot = document.getElementById(menuId) || panel;') &&
    visibilityRenderSource.includes("menuRoot.querySelectorAll('[data-precision-model-visibility]')") &&
    visibilityRenderSource.includes("menuRoot.querySelectorAll('[data-precision-model-visibility-action]')"),
  'Model display menu controls must bind from the portaled menu root so checkboxes and footer buttons remain actually clickable.',
);
expect(
  !visibilityRenderSource.includes('setPrecisionModelVisibility(input.dataset.precisionModelVisibility, input.checked)') &&
    visibilityRenderSource.includes('setPrecisionModelVisibilityDraft(input.dataset.precisionModelVisibility, input.checked)'),
  'Model display menu checkboxes must edit a draft instead of writing storage immediately.',
);
expect(
  css.includes('.precision-model-visibility-trigger') &&
    css.includes('.precision-model-visibility-menu') &&
    css.includes('position: fixed;') &&
    css.includes('z-index: var(--z-overlay);') &&
    css.includes('width: clamp(280px, calc(100vw - 24px), 420px);') &&
    css.includes('grid-template-rows: auto auto minmax(88px, 1fr) auto;') &&
    css.includes('.precision-model-visibility-list') &&
    css.includes('overflow: auto;') &&
    css.includes('grid-template-columns: 18px minmax(0, 1fr);') &&
    css.includes('word-break: break-word;'),
  'Model display popover needs fixed viewport positioning, clamped width, row text that cannot sit under the checkbox, a scrolling list, and a fixed footer.',
);
expect(js.includes("record.alias ? record.alias + ' · ' + record.id : record.id"), 'Model alias presentation must remain separate from the real model id.');
for (const key of ['precision_edit_overall_instruction', 'precision_instruction_required', 'precision_pure_resize_ready', 'precision_versions', 'precision_compare', 'precision_size_preserve', 'precision_size_resize', 'precision_edit_ellipse', 'precision_edit_brush', 'precision_edit_eraser', 'precision_zoom', 'precision_zoom_fit', 'precision_zoom_hint', 'precision_quick_tools', 'precision_ai_remove', 'precision_remove_people', 'precision_remove_watermark', 'cutout_person', 'cutout_person_start', 'cutout_person_hint', 'cutout_unconfigured_clear', 'cutout_checking', 'cutout_source_required', 'cutout_processing', 'cutout_busy', 'cutout_timeout', 'cutout_failed', 'cutout_completed', 'cutout_completed_fallback', 'cutout_refine', 'cutout_refine_feather', 'cutout_refine_use_selection', 'cutout_refine_selection_empty', 'cutout_refine_processing', 'cutout_refine_completed', 'cutout_restore_foreground', 'cutout_restore_min_alpha', 'cutout_restore_hint', 'cutout_restore_selection_empty', 'cutout_restore_selection_required', 'cutout_restore_source_required', 'cutout_restore_min_alpha_invalid', 'cutout_restore_ready', 'cutout_restore_processing', 'cutout_restore_failed', 'cutout_restore_completed', 'cutout_cancel_wait', 'cutout_cancelled', 'cutout_capability_refresh', 'cutout_capability_refresh_tooltip', 'cutout_algorithm_modnet_lab_notice']) {
  expect(i18n.includes("MESSAGES['creator." + key + "']"), 'Missing bilingual translation: ' + key);
}

function classListRecorder() {
  const values = new Set();
  return {
    add(...names) { names.forEach((name) => values.add(name)); },
    remove(...names) { names.forEach((name) => values.delete(name)); },
    toggle(name, enabled) { if (enabled) values.add(name); else values.delete(name); },
    contains(name) { return values.has(name); },
  };
}

function cutoutResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) };
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

const cutoutButton = {
  disabled: true,
  dataset: {},
  attributes: {},
  classList: classListRecorder(),
  setAttribute(name, value) { this.attributes[name] = value; },
};
const cutoutRefineButton = {
  disabled: false,
  dataset: {},
  attributes: {},
  classList: classListRecorder(),
  setAttribute(name, value) { this.attributes[name] = String(value); },
};
const cutoutCancelButton = {
  disabled: true,
  dataset: {},
  attributes: {},
  classList: classListRecorder(),
  setAttribute(name, value) { this.attributes[name] = String(value); },
};
const cutoutFeather = { value: '0' };
const cutoutFeatherValue = { value: '', textContent: '' };
const cutoutUseSelection = { checked: false, disabled: false };
const cutoutRestoreMode = { checked: false, disabled: false };
const cutoutRestoreMinAlpha = { value: '255', disabled: false };
const cutoutRestoreMinAlphaValue = { value: '', textContent: '' };
const cutoutRestoreHint = { textContent: '' };
const cutoutSelectionHint = { textContent: '' };
const cutoutStatus = { textContent: '', dataset: {}, classList: classListRecorder() };
const cutoutCalls = [];
const cutoutStatuses = [];
const cutoutCreatedCanvases = [];
const cutoutAbortControllers = [];
let cutoutFetch = async () => { throw new Error('unexpected fetch'); };
const readyCapability = {
  contract: 'genbox-cutout-v1', available: true, executable: true,
  adapters: ['u2net-human-seg-onnx'], state: 'ready',
  adapter_capabilities: [
    {
      adapter: 'u2net-human-seg-onnx', algorithm: 'U2Net human segmentation ONNX',
      available: true, executable: true, state: 'ready', source_page: 'fixed rembg source',
      license: { name: 'UNVERIFIED', status: 'UNVERIFIED' }, dependencies: ['onnxruntime'],
    },
    {
      adapter: 'rmbg-2.0', algorithm: 'BRIA RMBG-2.0 (BiRefNet architecture)',
      available: false, executable: false, state: 'unavailable', needs_model: true, needs_dependency: true,
      descriptor: { source_page: 'gated source', license_name: 'bria-rmbg-2.0', license_status: 'NON_COMMERCIAL_ONLY_UNVERIFIED', dependencies: ['torch', 'transformers'] },
    },
    {
      adapter: 'modnet-portrait-onnx', algorithm: 'MODNet photographic portrait matting ONNX',
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
const cutoutNodes = {
  btnPrecisionCutout: cutoutButton,
  btnPrecisionCutoutRefine: cutoutRefineButton,
  btnPrecisionCutoutCancel: cutoutCancelButton,
  precisionCutoutFeather: cutoutFeather,
  precisionCutoutFeatherValue: cutoutFeatherValue,
  precisionCutoutUseSelection: cutoutUseSelection,
  precisionCutoutRestoreMode: cutoutRestoreMode,
  precisionCutoutRestoreMinAlpha: cutoutRestoreMinAlpha,
  precisionCutoutRestoreMinAlphaValue: cutoutRestoreMinAlphaValue,
  precisionCutoutRestoreHint: cutoutRestoreHint,
  precisionCutoutSelectionHint: cutoutSelectionHint,
  precisionCutoutStatus: cutoutStatus,
};
function fakeCutoutCanvas() {
  const canvas = {
    tagName: 'CANVAS',
    width: 0,
    height: 0,
    ops: [],
    getContext(type) {
      assert.equal(type, '2d');
      const ops = this.ops;
      return {
        set fillStyle(value) { ops.push(['fillStyle', value]); },
        set strokeStyle(value) { ops.push(['strokeStyle', value]); },
        set lineJoin(value) { ops.push(['lineJoin', value]); },
        set lineCap(value) { ops.push(['lineCap', value]); },
        set lineWidth(value) { ops.push(['lineWidth', value]); },
        clearRect(...args) { ops.push(['clearRect', ...args]); },
        fillRect(...args) { ops.push(['fillRect', ...args]); },
        beginPath() { ops.push(['beginPath']); },
        ellipse(...args) { ops.push(['ellipse', ...args]); },
        fill() { ops.push(['fill']); },
        moveTo(...args) { ops.push(['moveTo', ...args]); },
        lineTo(...args) { ops.push(['lineTo', ...args]); },
        stroke() { ops.push(['stroke']); },
      };
    },
    toDataURL(type) {
      assert.equal(type, 'image/png');
      return 'data:image/png;base64,iVBORw0KGgoSELECTION';
    },
  };
  cutoutCreatedCanvases.push(canvas);
  return canvas;
}
const cutoutContext = vm.createContext({
  document: {
    getElementById: (id) => cutoutNodes[id] || null,
    createElement: (tag) => String(tag).toLowerCase() === 'canvas' ? fakeCutoutCanvas() : eventNode(),
  },
  PRECISION_CUTOUT_CONTRACT: 'genbox-cutout-v1',
  PRECISION_CUTOUT_REFINE_CONTRACT: 'genbox-cutout-refine-v1',
  PRECISION_CUTOUT_SELECTION_MASK_CONTRACT: 'genbox-cutout-selection-mask-v1',
  PRECISION_CUTOUT_MAX_FEATHER: 64,
  PRECISION_CUTOUT_CAPABILITY_TIMEOUT_MS: 1000,
  precisionCutoutCapability: null,
  precisionCutoutSelectedAdapter: '',
  precisionCutoutAdapterDetailsExpanded: false,
  precisionCutoutPending: false,
  precisionCutoutProbeToken: 0,
  precisionCutoutAvailabilityAbortController: null,
  precisionCutoutOperationToken: 0,
  precisionCutoutAbortController: null,
  precisionSourceLoadGeneration: 1,
  precisionEditSourceImageData: 'data:image/png;base64,c291cmNl',
  precisionEditSourceWidth: 4,
  precisionEditSourceHeight: 3,
  precisionEditObjects: [],
  precisionEditSession: {
    source: { id: 'original', label: 'Original', data: 'data:image/png;base64,c291cmNl' },
    versions: [], selectedVersionId: 'original', baseVersionId: 'original', taskBaseVersionId: null, view: 'after',
  },
  _authFetch: (...args) => cutoutFetch(...args),
  setTimeout,
  clearTimeout,
  renderPrecisionEditSession: () => {},
  setStatus: (value) => cutoutStatuses.push(value),
  i18nText: (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll('{' + name + '}', String(value)), key),
  AbortController: class FakeAbortController {
    constructor() {
      this.signal = { aborted: false };
      this.abortCount = 0;
      cutoutAbortControllers.push(this);
    }
    abort() {
      this.signal.aborted = true;
      this.abortCount += 1;
    }
  },
});
vm.runInContext([
  'getPrecisionCutoutControls', 'precisionLocalPathUrl', 'appendPrecisionEditImageVersion',
  'precisionCutoutHasSource', 'precisionCutoutUiBusy', 'precisionCutoutIsExecutable', 'precisionCutoutAdapterId', 'precisionCutoutAdapterText',
  'precisionCutoutAdapterRecords', 'precisionCutoutExecutableAdapterRecords', 'precisionCutoutSelectedAdapterRecord', 'precisionCutoutAdapterDisplayName',
  'precisionCutoutAdapterEscaped', 'precisionCutoutAdapterFact', 'setPrecisionCutoutAdapterDetailsExpanded',
  'togglePrecisionCutoutAdapterDetails', 'renderPrecisionCutoutAdapterOptions', 'renderPrecisionCutoutAdapterPicker', 'setPrecisionCutoutSelectedAdapter', 'setPrecisionCutoutUi',
  'precisionCutoutPngData', 'precisionCutoutGalleryUrl', 'precisionCutoutSelectedVersion',
  'precisionCutoutSelectedTransparentVersion', 'precisionCutoutSelectionObjects',
  'exportPrecisionCutoutSelectionMask', 'precisionCutoutFeatherRadius', 'precisionCutoutRestoreMinAlpha', 'updatePrecisionCutoutRefineControls',
  'readPrecisionCutoutResponse', 'precisionCutoutResponseError', 'probePrecisionCutoutCapability',
  'updatePrecisionCutoutAvailability', 'precisionCutoutResultSource', 'appendPrecisionCutoutVersion',
  'startPrecisionCutout', 'precisionCutoutRefineResultSource', 'appendPrecisionCutoutRefineVersion',
  'startPrecisionCutoutRefine', 'cancelPrecisionCutoutOperation',
].map(extractFunction).join('\n'), cutoutContext);

cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  return cutoutResponse(200, readyCapability);
};
await vm.runInContext('updatePrecisionCutoutAvailability()', cutoutContext);
assert.equal(cutoutStatus.dataset.state, 'ready');
assert.equal(cutoutStatus.textContent, 'creator.cutout_ready');
assert.equal(cutoutButton.disabled, false, 'Ready capability plus a local image must enable cutout.');
assert.equal(vm.runInContext('precisionCutoutSelectedAdapter', cutoutContext), 'u2net-human-seg-onnx', 'The first executable adapter must become the canonical default selection.');

const staleCapabilityProbe = deferred();
const freshCapabilityProbe = deferred();
let capabilityProbeCount = 0;
cutoutFetch = async (url) => {
  if (!url.endsWith('/capabilities')) return cutoutResponse(500, {});
  capabilityProbeCount += 1;
  return capabilityProbeCount === 1 ? staleCapabilityProbe.promise : freshCapabilityProbe.promise;
};
const staleAvailability = vm.runInContext('updatePrecisionCutoutAvailability()', cutoutContext);
for (let index = 0; index < 10 && capabilityProbeCount < 1; index += 1) {
  await new Promise((resolve) => setImmediate(resolve));
}
const freshAvailability = vm.runInContext('updatePrecisionCutoutAvailability()', cutoutContext);
for (let index = 0; index < 10 && capabilityProbeCount < 2; index += 1) {
  await new Promise((resolve) => setImmediate(resolve));
}
freshCapabilityProbe.resolve(cutoutResponse(200, readyCapability));
await freshAvailability;
assert.equal(cutoutStatus.dataset.state, 'ready', 'The newest capability probe must restore a usable ready state.');
staleCapabilityProbe.resolve(cutoutResponse(503, { contract: 'genbox-cutout-v1', available: false, executable: false, adapters: [], state: 'unavailable' }));
await staleAvailability;
assert.equal(cutoutStatus.dataset.state, 'ready', 'A stale probe resolving after a newer probe must not overwrite the ready state.');
assert.equal(cutoutButton.disabled, false, 'A stale probe must not leave the selector locked after a newer probe succeeds.');

cutoutFetch = async () => { throw new Error('capability probe unavailable'); };
await vm.runInContext('updatePrecisionCutoutAvailability()', cutoutContext);
assert.equal(cutoutStatus.dataset.state, 'error', 'A rejected capability probe must leave checking and show an error state.');
assert.equal(cutoutButton.disabled, true, 'A rejected capability probe must keep submission disabled.');

cutoutFetch = async () => cutoutResponse(503, {
  contract: 'genbox-cutout-v1', available: false, executable: false,
  adapters: [], state: 'unavailable',
});
await vm.runInContext('updatePrecisionCutoutAvailability()', cutoutContext);
assert.equal(cutoutStatus.dataset.state, 'unavailable', 'A fail-closed 503 capability response must not remain checking.');
assert.equal(cutoutButton.disabled, true);

vm.runInContext('PRECISION_CUTOUT_CAPABILITY_TIMEOUT_MS = 20', cutoutContext);
cutoutFetch = async () => new Promise(() => {});
await vm.runInContext('updatePrecisionCutoutAvailability()', cutoutContext);
assert.equal(cutoutStatus.dataset.state, 'error', 'A hung capability probe must time out into an error state.');
assert.equal(cutoutStatus.dataset.key, 'creator.cutout_check_failed');
assert.equal(cutoutButton.disabled, true, 'A timed-out capability probe must not leave the action enabled.');
vm.runInContext('PRECISION_CUTOUT_CAPABILITY_TIMEOUT_MS = 1000', cutoutContext);

const multiReadyCapability = JSON.parse(JSON.stringify(readyCapability));
multiReadyCapability.adapters.push('modnet-portrait-onnx');
multiReadyCapability.adapter_capabilities[2].available = true;
multiReadyCapability.adapter_capabilities[2].executable = true;
multiReadyCapability.adapter_capabilities[2].state = 'ready';
multiReadyCapability.adapter_capabilities[2].needs_model = false;
multiReadyCapability.adapter_capabilities[2].needs_dependency = false;
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  if (url.endsWith('/capabilities')) return cutoutResponse(200, multiReadyCapability);
  return cutoutResponse(200, multiReadyCapability);
};
await vm.runInContext('updatePrecisionCutoutAvailability()', cutoutContext);
assert.equal(vm.runInContext('precisionCutoutCapability.adapters.length', cutoutContext), 2);
assert.equal(vm.runInContext("setPrecisionCutoutSelectedAdapter('modnet-portrait-onnx')", cutoutContext), true, 'A second executable adapter must be selectable before submission.');
assert.ok(vm.runInContext("precisionCutoutAdapterDisplayName({ adapter: 'modnet-portrait-onnx', algorithm: 'MODNet photographic portrait matting ONNX' })", cutoutContext).includes('creator.cutout_algorithm_modnet_lab_notice'), 'The runtime MODNet id must carry the experimental laboratory notice.');
assert.ok(vm.runInContext("precisionCutoutAdapterDisplayName({ adapter: 'modnet-photographic-portrait', algorithm: 'Legacy MODNet descriptor' })", cutoutContext).includes('creator.cutout_algorithm_modnet_lab_notice'), 'The legacy MODNet descriptor must remain display-compatible.');

cutoutCalls.length = 0;
const postDeferred = deferred();
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  if (url.endsWith('/capabilities')) return cutoutResponse(200, multiReadyCapability);
  return postDeferred.promise;
};
const successfulCutout = vm.runInContext('startPrecisionCutout()', cutoutContext);
for (let index = 0; index < 10 && cutoutCalls.length < 2; index += 1) {
  await new Promise((resolve) => setImmediate(resolve));
}
assert.equal(cutoutCalls.length, 2);
assert.equal(cutoutCalls[1].url, '/api/image-tools/cutout');
assert.equal(cutoutCalls[1].options.method, 'POST');
assert.deepEqual(JSON.parse(cutoutCalls[1].options.body), {
  contract: 'genbox-cutout-v1', image_data: 'data:image/png;base64,c291cmNl',
  adapter: 'modnet-portrait-onnx', algorithm: 'MODNet photographic portrait matting ONNX',
});
assert.equal(cutoutStatus.dataset.state, 'processing');
assert.equal(cutoutButton.disabled, true);
assert.equal(cutoutButton.attributes['aria-busy'], 'true');
postDeferred.resolve(cutoutResponse(200, {
  contract: 'genbox-cutout-v1', success: true, status: 'completed', width: 4, height: 3,
  source_preserved: true, transparent: true, preview_background: 'checkerboard',
  image_data: 'data:image/png;base64,iVBORw0KGgoAAAAA',
  adapter: 'modnet-portrait-onnx',
  gallery_url: '/api/gallery/image/cutout.png', filename: 'cutout.png',
  restore_mode: false, restore_applied: false, restore_min_alpha: null,
}));
assert.equal(await successfulCutout, true);
let cutoutState = vm.runInContext('({ precisionEditSourceImageData, precisionEditSession, precisionCutoutPending })', cutoutContext);
assert.equal(cutoutState.precisionEditSession.versions.length, 1);
assert.equal(cutoutState.precisionEditSession.versions[0].data, '/api/gallery/image/cutout.png');
assert.equal(cutoutState.precisionEditSession.versions[0].parentId, 'original');
assert.equal(cutoutState.precisionEditSession.versions[0].adapter, 'modnet-portrait-onnx');
assert.equal(cutoutState.precisionEditSession.versions[0].fallbackFrom, '');
assert.equal(cutoutState.precisionEditSession.selectedVersionId, 'version-1');
assert.equal(cutoutState.precisionEditSession.baseVersionId, 'original', 'Cutout must not replace the editable base.');
assert.equal(cutoutState.precisionEditSourceImageData, 'data:image/png;base64,c291cmNl');
assert.equal(cutoutState.precisionCutoutPending, false);
assert.equal(cutoutStatus.dataset.state, 'success');
assert.equal(cutoutButton.attributes['aria-busy'], 'false');
assert.ok(cutoutStatuses.includes('creator.cutout_completed'));
vm.runInContext('updatePrecisionCutoutRefineControls()', cutoutContext);
assert.equal(cutoutRestoreMode.disabled, true, 'Restore mode must stay disabled until a canvas selection exists.');
assert.equal(cutoutRestoreMode.checked, false);
assert.equal(cutoutRestoreMinAlpha.disabled, true);
assert.equal(cutoutRestoreMinAlphaValue.textContent, '255');
assert.equal(cutoutRestoreHint.textContent, 'creator.cutout_restore_selection_empty');

vm.runInContext(`
  precisionEditObjects = [
    { id: 'mask-rect', type: 'rect', x: 0.1, y: 0.1, x2: 0.5, y2: 0.45 },
    { id: 'mask-ellipse', type: 'ellipse', x: 0.2, y: 0.2, x2: 0.8, y2: 0.85 },
    { id: 'mask-brush', type: 'brush', strokeWidth: 6, points: [{ x: 0.15, y: 0.2 }, { x: 0.45, y: 0.7 }] },
    { id: 'mask-text', type: 'text', x: 0.2, y: 0.2, text: 'ignored' }
  ];
`, cutoutContext);
vm.runInContext('updatePrecisionCutoutRefineControls()', cutoutContext);
assert.equal(cutoutRestoreMode.disabled, false, 'Restore mode must enable when a transparent cutout version and canvas selection exist.');
assert.equal(cutoutRestoreMode.checked, false);
assert.equal(cutoutRestoreMinAlpha.disabled, true);
assert.equal(cutoutRestoreHint.textContent, 'creator.cutout_restore_hint');
vm.runInContext("precisionEditSession.selectedVersionId = 'original'; updatePrecisionCutoutRefineControls();", cutoutContext);
assert.equal(cutoutRestoreMode.disabled, true, 'Restore mode must fail closed when the selected version is no longer a transparent cutout.');
assert.equal(cutoutRestoreMode.checked, false);
vm.runInContext("precisionEditSession.selectedVersionId = 'version-1'; updatePrecisionCutoutRefineControls();", cutoutContext);
assert.equal(cutoutRestoreMode.disabled, false);
cutoutCreatedCanvases.length = 0;
const exportedSelectionMask = vm.runInContext('exportPrecisionCutoutSelectionMask()', cutoutContext);
assert.ok(exportedSelectionMask.startsWith('data:image/png;base64,iVBORw0KGgo'), 'Cutout refine must export a real frontend PNG selection mask.');
assert.equal(cutoutCreatedCanvases.length, 1, 'Selection mask export must create one canvas.');
assert.equal(cutoutCreatedCanvases[0].width, 4);
assert.equal(cutoutCreatedCanvases[0].height, 3);
const maskOps = cutoutCreatedCanvases[0].ops.map((op) => op[0]);
for (const operation of ['clearRect', 'fillRect', 'ellipse', 'stroke']) {
  assert.ok(maskOps.includes(operation), `Selection mask canvas must draw ${operation}.`);
}
assert.equal(maskOps.includes('fillText'), false, 'Text annotations must not become cutout refine mask pixels.');

for (const [value, expected] of [['0', 0], ['64', 64]]) {
  cutoutFeather.value = value;
  assert.equal(vm.runInContext('precisionCutoutFeatherRadius()', cutoutContext), expected, `Feather ${value}px must be accepted.`);
}
for (const value of ['-1', '65', 'bad']) {
  cutoutFeather.value = value;
  assert.equal(vm.runInContext('precisionCutoutFeatherRadius()', cutoutContext), null, `Feather ${value} must fail closed.`);
}

cutoutFeather.value = '17';
cutoutUseSelection.checked = true;
cutoutCalls.length = 0;
cutoutStatuses.length = 0;
cutoutCreatedCanvases.length = 0;
const refineDeferred = deferred();
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  return refineDeferred.promise;
};
const successfulRefine = vm.runInContext('startPrecisionCutoutRefine()', cutoutContext);
for (let index = 0; index < 10 && cutoutCalls.length < 1; index += 1) {
  await new Promise((resolve) => setImmediate(resolve));
}
assert.equal(cutoutCalls.length, 1);
assert.equal(cutoutCalls[0].url, '/api/image-tools/cutout/refine');
assert.equal(cutoutCalls[0].options.method, 'POST');
assert.equal(cutoutCalls[0].options.signal && cutoutCalls[0].options.signal.aborted, false, 'Refine requests must receive a live abort signal when available.');
const refinePayload = JSON.parse(cutoutCalls[0].options.body);
assert.equal(refinePayload.contract, 'genbox-cutout-refine-v1');
assert.equal(refinePayload.image_data, 'data:image/png;base64,iVBORw0KGgoAAAAA');
assert.equal(refinePayload.feather_radius, 17);
assert.equal(refinePayload.parent_version_id, 'version-1');
assert.equal(refinePayload.selection_mask_contract, 'genbox-cutout-selection-mask-v1');
assert.ok(refinePayload.selection_mask_data.startsWith('data:image/png;base64,iVBORw0KGgo'), 'Refine payload must carry the real canvas mask data.');
assert.equal(cutoutCreatedCanvases.length, 1, 'Refine submit must derive selection data from the frontend canvas path.');
assert.equal(cutoutStatus.dataset.state, 'processing');
assert.equal(cutoutRefineButton.disabled, true);
assert.equal(cutoutCancelButton.classList.contains('hidden'), false, 'An in-flight refine operation must expose the cancel-wait control.');
const validRefineResult = {
  contract: 'genbox-cutout-refine-v1',
  success: true,
  status: 'completed',
  operation: 'alpha_refine',
  local_only: true,
  source_preserved: true,
  transparent: true,
  preview_background: 'checkerboard',
  parent_version_id: 'version-1',
  width: 4,
  height: 3,
  feather_radius: 17,
  restore_mode: false,
  restore_applied: false,
  restore_min_alpha: null,
  selection_applied: true,
  selection_mask_contract: 'genbox-cutout-selection-mask-v1',
  alpha_changed: true,
  alpha_extrema: [0, 255],
  version_id: 'cutout-refine-test-1',
  image_data: 'data:image/png;base64,iVBORw0KGgoREFINED',
  gallery_url: '/api/gallery/image/refined.png',
  filename: 'refined.png',
};
refineDeferred.resolve(cutoutResponse(200, validRefineResult));
assert.equal(await successfulRefine, true);
cutoutState = vm.runInContext('({ precisionEditSession, precisionCutoutPending })', cutoutContext);
assert.equal(cutoutState.precisionEditSession.versions.length, 2);
assert.equal(cutoutState.precisionEditSession.versions[1].parentId, 'version-1', 'Refine success must append a child of the selected cutout version.');
assert.equal(cutoutState.precisionEditSession.versions[1].transparent, true);
assert.equal(cutoutState.precisionEditSession.versions[1].previewBackground, 'checkerboard', 'Refine versions must preserve checkerboard transparency preview metadata.');
assert.equal(cutoutState.precisionEditSession.versions[1].operation, 'alpha_refine');
assert.equal(cutoutState.precisionEditSession.versions[1].remoteVersionId, 'cutout-refine-test-1');
assert.equal(cutoutState.precisionEditSession.versions[1].width, 4);
assert.equal(cutoutState.precisionEditSession.versions[1].height, 3);
assert.equal(cutoutState.precisionEditSession.selectedVersionId, 'version-2');
assert.equal(cutoutState.precisionEditSession.baseVersionId, 'original', 'Refine success must not replace the editable base.');
assert.equal(cutoutState.precisionCutoutPending, false);
assert.ok(cutoutStatuses.includes('creator.cutout_refine_completed'));

cutoutCalls.length = 0;
cutoutStatuses.length = 0;
cutoutFeather.value = '12';
cutoutUseSelection.checked = false;
cutoutRestoreMode.checked = true;
cutoutRestoreMinAlpha.value = '196';
vm.runInContext('updatePrecisionCutoutRefineControls()', cutoutContext);
assert.equal(cutoutUseSelection.checked, true, 'Restore mode must force the selection mask to be used.');
assert.equal(cutoutUseSelection.disabled, true, 'Restore mode must lock the selection checkbox while active.');
assert.equal(cutoutRestoreMode.disabled, false);
assert.equal(cutoutRestoreMinAlpha.disabled, false);
assert.equal(cutoutRestoreMinAlphaValue.textContent, '196');
assert.equal(cutoutRestoreHint.textContent, 'creator.cutout_restore_ready');
assert.equal(vm.runInContext('precisionCutoutRestoreMinAlpha()', cutoutContext), 196);
const restoreDeferred = deferred();
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  return restoreDeferred.promise;
};
const successfulRestore = vm.runInContext('startPrecisionCutoutRefine()', cutoutContext);
for (let index = 0; index < 10 && cutoutCalls.length < 1; index += 1) {
  await new Promise((resolve) => setImmediate(resolve));
}
assert.equal(cutoutCalls.length, 1);
assert.equal(cutoutCalls[0].url, '/api/image-tools/cutout/refine');
const restorePayload = JSON.parse(cutoutCalls[0].options.body);
assert.equal(restorePayload.contract, 'genbox-cutout-refine-v1');
assert.equal(restorePayload.image_data, 'data:image/png;base64,iVBORw0KGgoREFINED');
assert.equal(restorePayload.feather_radius, 12);
assert.equal(restorePayload.parent_version_id, 'version-2');
assert.equal(restorePayload.restore_mode, true);
assert.equal(restorePayload.restore_source_image_data, 'data:image/png;base64,c291cmNl');
assert.equal(restorePayload.restore_min_alpha, 196);
assert.equal(restorePayload.selection_mask_contract, 'genbox-cutout-selection-mask-v1');
assert.ok(restorePayload.selection_mask_data.startsWith('data:image/png;base64,iVBORw0KGgo'), 'Restore payload must reuse the frontend selection mask.');
restoreDeferred.resolve(cutoutResponse(200, {
  contract: 'genbox-cutout-refine-v1',
  success: true,
  status: 'completed',
  operation: 'alpha_refine',
  local_only: true,
  source_preserved: true,
  transparent: true,
  preview_background: 'checkerboard',
  parent_version_id: 'version-2',
  width: 4,
  height: 3,
  feather_radius: 12,
  restore_mode: true,
  restore_applied: true,
  restore_min_alpha: 196,
  selection_applied: true,
  selection_mask_contract: 'genbox-cutout-selection-mask-v1',
  alpha_changed: true,
  alpha_extrema: [0, 255],
  version_id: 'cutout-refine-test-2',
  image_data: 'data:image/png;base64,iVBORw0KGgoRESTORED',
  gallery_url: '/api/gallery/image/restored.png',
  filename: 'restored.png',
}));
assert.equal(await successfulRestore, true);
cutoutState = vm.runInContext('({ precisionEditSession, precisionCutoutPending })', cutoutContext);
assert.equal(cutoutState.precisionEditSession.versions.length, 3);
assert.equal(cutoutState.precisionEditSession.versions[2].parentId, 'version-2', 'Restore success must append a child of the selected transparent version.');
assert.equal(cutoutState.precisionEditSession.versions[2].transparent, true);
assert.equal(cutoutState.precisionEditSession.versions[2].previewBackground, 'checkerboard');
assert.equal(cutoutState.precisionEditSession.versions[2].operation, 'alpha_refine');
assert.equal(cutoutState.precisionEditSession.versions[2].remoteVersionId, 'cutout-refine-test-2');
assert.equal(cutoutState.precisionEditSession.versions[2].restoreMode, true);
assert.equal(cutoutState.precisionEditSession.versions[2].restoreMinAlpha, 196);
assert.equal(cutoutState.precisionEditSession.versions[2].selectionApplied, true);
assert.equal(cutoutState.precisionEditSession.selectedVersionId, 'version-3');
assert.equal(cutoutState.precisionEditSession.baseVersionId, 'original', 'Restore success must not replace the editable base.');
assert.equal(cutoutState.precisionCutoutPending, false);
assert.ok(cutoutStatuses.includes('creator.cutout_restore_completed'));
cutoutRestoreMode.checked = false;
vm.runInContext('updatePrecisionCutoutRefineControls()', cutoutContext);

function refineCandidate(overrides = {}) {
  return { ...validRefineResult, ...overrides };
}
for (const [overrides, label] of [
  [{ parent_version_id: 'version-other' }, 'mismatched parent'],
  [{ width: 5 }, 'mismatched width'],
  [{ height: 4 }, 'mismatched height'],
  [{ image_data: 'data:image/jpeg;base64,AAAA' }, 'non-PNG image data'],
  [{ gallery_url: '/api/gallery/image/refined.jpg', filename: 'refined.jpg' }, 'non-PNG gallery URL'],
  [{ preview_background: 'solid' }, 'non-checkerboard preview'],
  [{ selection_mask_contract: null }, 'missing applied selection contract'],
]) {
  cutoutContext.__refineCandidate = refineCandidate(overrides);
  assert.equal(vm.runInContext('precisionCutoutRefineResultSource(__refineCandidate, 4, 3, "version-1", 17, false, null, true)', cutoutContext), '', `Refine result validation must reject ${label}.`);
}
cutoutContext.__refineCandidate = refineCandidate({
  parent_version_id: 'version-2',
  feather_radius: 12,
  restore_mode: true,
  restore_applied: true,
  restore_min_alpha: 196,
  selection_applied: true,
  selection_mask_contract: 'genbox-cutout-selection-mask-v1',
  image_data: 'data:image/png;base64,iVBORw0KGgoRESTORED',
  gallery_url: '/api/gallery/image/restored.png',
  filename: 'restored.png',
});
assert.equal(vm.runInContext('precisionCutoutRefineResultSource(__refineCandidate, 4, 3, "version-2", 12, true, 196, true)', cutoutContext), '/api/gallery/image/restored.png', 'Refine result validation must accept explicit restore responses with a matching alpha floor.');
cutoutContext.__refineCandidate = refineCandidate({ selection_applied: false, selection_mask_contract: null });
assert.equal(vm.runInContext('precisionCutoutRefineResultSource(__refineCandidate, 4, 3, "version-1", 17, false, null, false)', cutoutContext), '/api/gallery/image/refined.png', 'Refine result validation must accept no-selection responses only when the contract is explicitly null.');

cutoutFeather.value = '8';
cutoutUseSelection.checked = false;
cutoutCalls.length = 0;
const cancelledVersionCount = vm.runInContext('precisionEditSession.versions.length', cutoutContext);
const cancelDeferred = deferred();
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  return cancelDeferred.promise;
};
const cancelledRefine = vm.runInContext('startPrecisionCutoutRefine()', cutoutContext);
for (let index = 0; index < 10 && cutoutCalls.length < 1; index += 1) {
  await new Promise((resolve) => setImmediate(resolve));
}
const activeAbortController = cutoutAbortControllers[cutoutAbortControllers.length - 1];
assert.equal(vm.runInContext('cancelPrecisionCutoutOperation()', cutoutContext), true, 'Cutout cancel must invalidate the active refine token.');
assert.equal(activeAbortController.signal.aborted, true, 'Cutout cancel must abort the active refine request.');
cancelDeferred.resolve(cutoutResponse(200, refineCandidate({
  parent_version_id: 'version-2',
  feather_radius: 8,
  selection_applied: false,
  selection_mask_contract: null,
  version_id: 'cutout-refine-cancelled',
  gallery_url: '/api/gallery/image/cancelled.png',
  filename: 'cancelled.png',
})));
assert.equal(await cancelledRefine, false);
assert.equal(vm.runInContext('precisionEditSession.versions.length', cutoutContext), cancelledVersionCount, 'A cancelled late refine response must not append a version.');

cutoutCalls.length = 0;
const staleRefineDeferred = deferred();
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  return staleRefineDeferred.promise;
};
const staleRefineVersionCount = vm.runInContext('precisionEditSession.versions.length', cutoutContext);
const staleRefine = vm.runInContext('startPrecisionCutoutRefine()', cutoutContext);
for (let index = 0; index < 10 && cutoutCalls.length < 1; index += 1) {
  await new Promise((resolve) => setImmediate(resolve));
}
vm.runInContext('precisionSourceLoadGeneration += 1', cutoutContext);
staleRefineDeferred.resolve(cutoutResponse(200, refineCandidate({
  parent_version_id: 'version-2',
  feather_radius: 8,
  selection_applied: false,
  selection_mask_contract: null,
  version_id: 'cutout-refine-stale',
  gallery_url: '/api/gallery/image/stale-refine.png',
  filename: 'stale-refine.png',
})));
assert.equal(await staleRefine, false);
assert.equal(vm.runInContext('precisionEditSession.versions.length', cutoutContext), staleRefineVersionCount, 'A stale source-generation refine response must not append a version.');

async function runCutoutFailure(status, detail, expectedState, expectedKey) {
  cutoutCalls.length = 0;
  cutoutFetch = async (url, options) => {
    cutoutCalls.push({ url, options });
    if (url.endsWith('/capabilities')) return cutoutResponse(200, readyCapability);
    return cutoutResponse(status, { detail });
  };
  const result = await vm.runInContext('startPrecisionCutout()', cutoutContext);
  assert.equal(result, false);
  assert.equal(cutoutCalls.filter((call) => call.url === '/api/image-tools/cutout').length, 1);
  assert.equal(cutoutStatus.dataset.state, expectedState);
  assert.equal(cutoutStatus.textContent, expectedKey);
}

await runCutoutFailure(409, { code: 'cutout_busy', message: 'busy' }, 'busy', 'creator.cutout_busy');
await runCutoutFailure(504, { code: 'cutout_timeout', message: 'timeout' }, 'timeout', 'creator.cutout_timeout');
await runCutoutFailure(500, { code: 'cutout_failed', message: 'failed' }, 'error', 'creator.cutout_failed');

cutoutCalls.length = 0;
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  return cutoutResponse(503, { detail: {
    contract: 'genbox-cutout-v1', available: false, executable: false,
    adapters: [], state: 'unavailable', code: 'cutout_adapter_unavailable',
  } });
};
assert.equal(await vm.runInContext('startPrecisionCutout()', cutoutContext), false);
assert.equal(cutoutCalls.length, 1, 'Unavailable capability must stop before POST.');
assert.equal(cutoutStatus.dataset.state, 'unavailable');

cutoutCalls.length = 0;
vm.runInContext("precisionEditSourceImageData = null; precisionEditSourceWidth = 0; precisionEditSourceHeight = 0;", cutoutContext);
assert.equal(await vm.runInContext('startPrecisionCutout()', cutoutContext), false);
assert.equal(cutoutCalls.length, 0, 'Missing local image must not probe or POST.');
assert.equal(cutoutStatus.dataset.state, 'source-required');

vm.runInContext("precisionEditSourceImageData = 'data:image/png;base64,c291cmNl'; precisionEditSourceWidth = 4; precisionEditSourceHeight = 3; precisionCutoutCapability = null;", cutoutContext);
cutoutCalls.length = 0;
const capabilityDeferred = deferred();
cutoutFetch = async (url, options) => {
  cutoutCalls.push({ url, options });
  if (url.endsWith('/capabilities')) return capabilityDeferred.promise;
  return cutoutResponse(200, {
    contract: 'genbox-cutout-v1', success: true, status: 'completed', width: 4, height: 3,
    source_preserved: true, transparent: true, preview_background: 'checkerboard',
    image_data: 'data:image/png;base64,iVBORw0KGgoAAAAA', gallery_url: '/api/gallery/image/cutout-2.png',
    adapter: 'u2net-human-seg-onnx',
  });
};
const firstClick = vm.runInContext('startPrecisionCutout()', cutoutContext);
const duplicateClick = vm.runInContext('startPrecisionCutout()', cutoutContext);
assert.equal(await duplicateClick, false);
assert.equal(cutoutCalls.length, 1, 'Duplicate click during probe must not create another request.');
capabilityDeferred.resolve(cutoutResponse(200, readyCapability));
assert.equal(await firstClick, true);
assert.equal(cutoutCalls.filter((call) => call.url === '/api/image-tools/cutout').length, 1);

const precisionPanelStart = html.indexOf('id="panelPrecisionEdit"');
const precisionPanelEnd = html.indexOf('</div>', html.indexOf('id="precisionFileInput"', precisionPanelStart));
const precisionPanelMarkup = html.slice(precisionPanelStart, precisionPanelEnd);
expect((html.match(/id="imageWorkbenchTitle"/g) || []).length === 1, 'Precision mode must reuse one workbench title instead of rendering duplicate page titles.');
expect(!/<h[1-6][^>]*class="[^"]*precision[^\"]*"/i.test(precisionPanelMarkup) && !/role="heading"/i.test(precisionPanelMarkup), 'The precision panel must not add a duplicate internal heading.');
const precisionActionMount = js.slice(js.indexOf('function mountCreatorGenerateAction'), js.indexOf('function openPrecisionGalleryPicker'));
expect(precisionActionMount.includes("header.classList.toggle('precision-action-header',mode==='precision_edit');"), 'Precision mode must mark its generated action header so the duplicate workspace title can be hidden.');
expect(css.includes('.creator-generate-header.precision-action-header > #creatorGenerateActionTitle') && css.includes('.creator-generate-header.precision-action-header > #creatorGenerateActionHint'), 'Precision mode must hide only the generated workspace title and hint, while retaining its controls.');
expect(html.includes('id="imageModePrecision"') && html.includes('id="subTabPrecisionEdit"'), 'Precision navigation labels must remain explicit controls, not content headings.');
expect(/id="precisionWorkbenchHelpTrigger"[^>]*aria-controls="precisionWorkbenchHelpPopover"[^>]*aria-expanded="false"/.test(html), 'Workbench help must expose a collapsed ARIA control relationship.');
expect((html.match(/id="precisionWorkbenchHelp"/g) || []).length === 1 && (html.match(/id="precisionWorkbenchHelpTrigger"/g) || []).length === 1 && (html.match(/id="precisionWorkbenchHelpPopover"/g) || []).length === 1, 'Precision workbench help must have one wrapper, trigger, and popover.');
const precisionModeBarMarkup = html.slice(html.indexOf('<div class="creator-mode-bar">'), html.indexOf('<div class="generate-layout">'));
expect(!precisionModeBarMarkup.includes('id="precisionWorkbenchHelp"'), 'Precision help must not remain beside the global workbench title.');
const canvasTitleIndex = html.indexOf('data-i18n="creator.precision_edit_canvas"');
const compactHelpIndex = html.indexOf('id="precisionWorkbenchHelp"', canvasTitleIndex);
const dimensionsIndex = html.indexOf('id="precisionCanvasDimensions"', canvasTitleIndex);
const stageActionsIndex = html.indexOf('class="precision-stage-actions"', dimensionsIndex);
const sourceActionsIndex = html.indexOf('id="precisionSourceActions"', stageActionsIndex);
const docsTriggerIndex = html.indexOf('id="btnPrecisionDocs"', stageActionsIndex);
expect(canvasTitleIndex !== -1 && compactHelpIndex > canvasTitleIndex && dimensionsIndex > compactHelpIndex, 'Precision canvas title row must order label, compact help trigger, then dimensions.');
expect(stageActionsIndex > dimensionsIndex && sourceActionsIndex > stageActionsIndex && docsTriggerIndex > stageActionsIndex, 'Precision source actions and the docs trigger must live in the right-side stage actions.');
expect(/id="precisionReplaceDisabledHint" class="sr-only precision-source-action-status"/.test(html), 'The replacement status must start as a screen-reader-only hint with a dedicated component class.');
const srOnlyUtilityIndex = css.lastIndexOf('[class~="sr-only"]');
const srOnlyUtility = css.slice(srOnlyUtilityIndex);
expect(srOnlyUtilityIndex > css.lastIndexOf('.precision-source-action-status.is-visible'), 'The screen-reader-only utility must remain after precision component layout rules.');
expect(/\[class~="sr-only"\]\s*\{[\s\S]*?position:\s*absolute;[\s\S]*?width:\s*1px;[\s\S]*?height:\s*1px;[\s\S]*?overflow:\s*hidden;[\s\S]*?clip:\s*rect\(0, 0, 0, 0\);[\s\S]*?clip-path:\s*inset\(50%\);[\s\S]*?white-space:\s*nowrap;[\s\S]*?\}\s*$/.test(srOnlyUtility), 'The loaded stylesheet must end with the complete screen-reader-only clipping contract.');
expect(!/display:\s*none|visibility:\s*hidden/.test(srOnlyUtility), 'Screen-reader-only content must stay in the accessibility tree.');
expect(/\.precision-workbench-help-trigger\s*\{[\s\S]*?position:\s*relative;[\s\S]*?z-index:\s*81;[\s\S]*?width:\s*44px;[\s\S]*?height:\s*44px;[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/.test(css), 'Precision help must retain its focus-ring stacking and 44px touch target.');
expect(/\.precision-workbench-help-trigger\s*\{[\s\S]*?border:\s*0;[\s\S]*?background:\s*transparent;[\s\S]*?color:\s*var\(--text-muted\);[\s\S]*?font-size:\s*0;/.test(css), 'The 44px help target must not render as an oversized visible circle.');
expect(/\.precision-workbench-help-trigger::before\s*\{[\s\S]*?content:\s*"";[\s\S]*?width:\s*26px;[\s\S]*?height:\s*26px;[\s\S]*?border:\s*1px solid var\(--border-strong\);[\s\S]*?border-radius:\s*50%;[\s\S]*?background:\s*var\(--bg-surface\);/.test(css), 'Precision help must render a compact inner circle using the established help-icon styling.');
expect(/\.precision-workbench-help-trigger::after\s*\{[\s\S]*?content:\s*"\?";[\s\S]*?font-size:\s*12px;[\s\S]*?font-weight:\s*700;[\s\S]*?line-height:\s*1;/.test(css), 'The compact inner help mark must retain the established question-mark typography.');
expect(/\.precision-workbench-help-trigger:hover::before,\s*\.precision-workbench-help-trigger:focus-visible::before,\s*\.precision-workbench-help-trigger\[aria-expanded="true"\]::before\s*\{[\s\S]*?border-color:\s*var\(--accent\);[\s\S]*?outline:\s*2px solid color-mix\(in srgb, var\(--accent\) 24%, transparent\);[\s\S]*?outline-offset:\s*2px;/.test(css), 'Hover, keyboard focus, and pinned-open states must remain visible on the compact inner help circle.');
expect(js.includes("else setPrecisionWorkbenchHelp(false,false,true);"), 'Leaving precision mode must close help and reset its pinned interaction state.');
expect(/href="https:\/\/github\.com\/liwei9745\/GenBox\/blob\/master\/docs\/CLIENT-QUICKSTART\.md#start--[^\"]+" target="_blank" rel="noopener noreferrer"/.test(html), 'Workbench help documentation links must use the stable master-branch HTTPS target with noopener and noreferrer.');
expect(/href="https:\/\/github\.com\/liwei9745\/GenBox\/blob\/master\/docs\/CUTOUT-MODEL-GUIDE\.md" target="_blank" rel="noopener noreferrer"/.test(html), 'Cutout model help must use the stable master-branch GenBox guide link.');
expect(!html.includes('https://github.com/liwei9745/GenBox/blob/main/'), 'GenBox documentation links must not target the nonexistent main branch.');
const docsDialogIndex = html.indexOf('id="precisionDocsDialog"');
expect(/id="btnPrecisionDocs"[^>]*aria-haspopup="dialog"[^>]*aria-controls="precisionDocsDialog"[\s\S]*?<svg[\s\S]*?<span data-i18n="creator\.precision_docs_open">/.test(html), 'The top precision docs action must be an icon+text dialog trigger.');
expect(/id="precisionDocsDialog"[^>]*role="dialog"[^>]*aria-modal="true"[^>]*aria-hidden="true"[^>]*aria-labelledby="precisionDocsTitle"[^>]*aria-describedby="precisionDocsIntro"/.test(html), 'Precision docs must be an independent modal dialog with labelledby and description.');
expect(docsDialogIndex > -1 && html.indexOf('id="precisionDocsPanel" tabindex="-1"', docsDialogIndex) > docsDialogIndex && html.indexOf('id="btnPrecisionDocsClose"', docsDialogIndex) > docsDialogIndex, 'Precision docs dialog must include a focusable panel and close control.');
expect(/class="glass-panel precision-docs-panel" id="precisionDocsPanel"/.test(html), 'Precision docs must reuse the established glass modal surface.');
expect(/class="precision-docs-body" id="precisionDocsBody" tabindex="0"/.test(html), 'Precision docs content must remain a keyboard-scrollable region.');
for (const key of ['precision_docs_shapes', 'precision_docs_eraser', 'precision_docs_text', 'precision_docs_cutout', 'precision_docs_resize', 'precision_docs_versions', 'precision_docs_models']) {
  expect(html.includes('creator.' + key + '_title') && html.includes('creator.' + key + '_body'), 'Precision docs dialog must cover ' + key + '.');
}
for (const selector of ['.precision-stage-actions', '.precision-docs-trigger', '.precision-docs-dialog', '.precision-docs-dialog.hidden', '.precision-docs-panel', '.precision-docs-body']) {
  expect(css.includes(selector), 'Precision docs CSS is missing ' + selector + '.');
}
expect(css.includes('max-height: calc(100vh - 32px);') && css.includes('@media (max-width: 640px)') && css.includes('max-height: calc(100vh - 20px);'), 'Precision docs dialog must stay within desktop and mobile viewport bounds.');
for (const key of ['precision_docs_open', 'precision_docs_close', 'precision_docs_kicker', 'precision_docs_title', 'precision_docs_intro', 'precision_docs_shapes_title', 'precision_docs_shapes_body', 'precision_docs_eraser_title', 'precision_docs_eraser_body', 'precision_docs_text_title', 'precision_docs_text_body', 'precision_docs_cutout_title', 'precision_docs_cutout_body', 'precision_docs_resize_title', 'precision_docs_resize_body', 'precision_docs_versions_title', 'precision_docs_versions_body', 'precision_docs_models_title', 'precision_docs_models_body']) {
  expect(i18n.includes("MESSAGES['creator." + key + "']"), 'Missing precision docs translation: ' + key);
}

function eventNode() {
  const listeners = new Map();
  const attributes = {};
  return {
    dataset: {},
    classList: classListRecorder(),
    focusCount: 0,
    addEventListener(type, listener) {
      const list = listeners.get(type) || [];
      list.push(listener);
      listeners.set(type, list);
    },
    emit(type, event = {}) {
      const payload = {
        type,
        target: this,
        preventDefault() { this.defaultPrevented = true; },
        stopPropagation() { this.propagationStopped = true; },
        ...event,
      };
      (listeners.get(type) || []).forEach((listener) => listener(payload));
      return payload;
    },
    setAttribute(name, value) { attributes[name] = String(value); },
    getAttribute(name) { return Object.prototype.hasOwnProperty.call(attributes, name) ? attributes[name] : null; },
    focus() { this.focusCount += 1; },
  };
}

const helpWrapper = eventNode();
const helpTrigger = eventNode();
const helpPopover = eventNode();
const helpLink = eventNode();
helpTrigger.setAttribute('aria-expanded', 'false');
const helpDocumentListeners = new Map();
const helpDocument = {
  activeElement: null,
  getElementById(id) {
    return ({ precisionWorkbenchHelp: helpWrapper, precisionWorkbenchHelpTrigger: helpTrigger, precisionWorkbenchHelpPopover: helpPopover })[id] || null;
  },
  addEventListener(type, listener) {
    const list = helpDocumentListeners.get(type) || [];
    list.push(listener);
    helpDocumentListeners.set(type, list);
  },
  emit(type, event = {}) {
    const payload = { type, preventDefault() { this.defaultPrevented = true; }, ...event };
    (helpDocumentListeners.get(type) || []).forEach((listener) => listener(payload));
    return payload;
  },
};
helpTrigger.focus = function focusHelpTrigger() {
  this.focusCount += 1;
  if (helpDocument.activeElement === this) return;
  helpDocument.activeElement = this;
  this.emit('focus');
};
helpWrapper.contains = (node) => [helpWrapper, helpTrigger, helpPopover, helpLink].includes(node);
const helpContext = vm.createContext({
  document: helpDocument,
  setTimeout: (callback) => callback(),
});
vm.runInContext(['setPrecisionWorkbenchHelp', 'bindPrecisionWorkbenchHelp'].map(extractFunction).join('\n'), helpContext);
vm.runInContext('bindPrecisionWorkbenchHelp()', helpContext);
helpTrigger.focus();
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'true', 'Keyboard focus must open workbench help.');
helpDocument.activeElement = null;
helpWrapper.emit('focusout');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'false', 'Leaving workbench help by keyboard must close an unpinned popover.');
helpWrapper.emit('mouseenter');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'true', 'Hover must open workbench help.');
helpWrapper.emit('mouseleave');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'false', 'Leaving hover must close an unpinned workbench help popover.');
helpWrapper.emit('mouseenter');
helpDocument.emit('pointerdown', { target: helpTrigger });
helpTrigger.focus();
helpTrigger.emit('click');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'true', 'The real hover, pointerdown, focus, then first click sequence must leave workbench help open.');
helpDocument.emit('pointerdown', { target: helpTrigger });
helpTrigger.emit('click');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'false', 'A subsequent trigger tap must toggle workbench help closed.');
helpDocument.emit('pointerdown', { target: helpTrigger });
helpTrigger.emit('click');
helpDocument.activeElement = helpLink;
helpWrapper.emit('focusout');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'true', 'Moving focus into the help popover must not close it.');
helpDocument.emit('pointerdown', { target: eventNode() });
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'false', 'Pointer activity outside workbench help must close it.');
helpDocument.emit('pointerdown', { target: helpTrigger });
helpTrigger.focus();
helpTrigger.emit('click');
helpDocument.activeElement = helpLink;
helpWrapper.emit('focusout');
const linkEscapeFocusCount = helpTrigger.focusCount;
const escape = helpDocument.emit('keydown', { key: 'Escape' });
assert.equal(escape.defaultPrevented, true, 'Escape must consume the open workbench-help interaction.');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'false', 'Escape must close workbench help.');
assert.equal(helpTrigger.focusCount, linkEscapeFocusCount + 1, 'Escape must restore focus to the workbench-help trigger.');
assert.equal(helpDocument.activeElement, helpTrigger, 'Escape from a help link must restore focus to the help trigger.');
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'false', 'The synchronous focus event caused by Escape focus restoration must not reopen workbench help.');

helpWrapper.emit('mouseenter');
const triggerEscapeFocusCount = helpTrigger.focusCount;
const triggerEscape = helpDocument.emit('keydown', { key: 'Escape' });
assert.equal(triggerEscape.defaultPrevented, true, 'Escape on the focused trigger must still close open transient help.');
assert.equal(helpTrigger.focusCount, triggerEscapeFocusCount, 'Escape must not refocus a trigger that already owns focus.');
helpDocument.activeElement = null;
helpTrigger.focus();
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'true', 'Escape on an already focused trigger must not suppress the next real Tab focus.');

helpTrigger.emit('click');
assert.equal(helpTrigger._precisionHelpState.pinned, true, 'A deliberate click must pin help before mode exit.');
vm.runInContext('setPrecisionWorkbenchHelp(false, false, true)', helpContext);
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'false', 'Leaving precision mode must close workbench help.');
assert.equal(helpTrigger._precisionHelpState.pinned, false, 'Leaving precision mode must clear the pinned state.');
helpDocument.activeElement = null;
helpTrigger.focus();
assert.equal(helpTrigger.getAttribute('aria-expanded'), 'true', 'Returning to precision mode must allow the first keyboard focus to open help.');

const docsBodyClassList = classListRecorder();
const docsScrollBody = { scrollTop: 73 };
const docsDocument = {
  activeElement: null,
  body: { classList: docsBodyClassList },
  getElementById(id) {
    return ({
      precisionDocsDialog: docsDialog,
      precisionDocsPanel: docsPanel,
      precisionDocsBody: docsScrollBody,
      btnPrecisionDocs: docsTrigger,
      btnPrecisionDocsClose: docsClose,
      precisionDocsDone: docsDone,
    })[id] || null;
  },
};
function docsElement() {
  const node = eventNode();
  node.disabled = false;
  node.hidden = false;
  node.focus = function focusDocsElement() {
    this.focusCount += 1;
    docsDocument.activeElement = this;
  };
  return node;
}
const docsDialog = docsElement();
const docsPanel = docsElement();
const docsTrigger = docsElement();
const docsClose = docsElement();
const docsDone = docsElement();
docsDialog.classList.add('hidden');
docsDialog.setAttribute('aria-hidden', 'true');
docsDialog.querySelectorAll = () => [docsClose, docsDone];
const docsContext = vm.createContext({
  document: docsDocument,
});
vm.runInContext(['precisionDocsFocusable', 'openPrecisionDocsDialog', 'closePrecisionDocsDialog', 'bindPrecisionDocsDialog'].map(extractFunction).join('\n'), docsContext);
docsDocument.activeElement = docsTrigger;
assert.equal(vm.runInContext('openPrecisionDocsDialog()', docsContext), true, 'The precision docs trigger must open the in-app dialog.');
assert.equal(docsDialog.classList.contains('hidden'), false);
assert.equal(docsDialog.getAttribute('aria-hidden'), 'false');
assert.equal(docsBodyClassList.contains('precision-docs-open'), true, 'Opening docs must lock the page behind the dialog.');
assert.equal(docsScrollBody.scrollTop, 0, 'Opening docs must reset the scrollable document body to the beginning.');
assert.equal(docsClose.focusCount, 1, 'Opening docs must focus the close control.');
assert.equal(docsDocument.activeElement, docsClose);
assert.equal(docsDialog.dataset.precisionDocsBound, 'true', 'Precision docs binding must be idempotent.');

const docsShiftTab = docsDialog.emit('keydown', { key: 'Tab', shiftKey: true });
assert.equal(docsShiftTab.defaultPrevented, true, 'Shift+Tab on the first docs control must stay inside the dialog.');
assert.equal(docsDocument.activeElement, docsDone, 'Shift+Tab on the first docs control must wrap to the last control.');
const docsTab = docsDialog.emit('keydown', { key: 'Tab', shiftKey: false });
assert.equal(docsTab.defaultPrevented, true, 'Tab on the last docs control must stay inside the dialog.');
assert.equal(docsDocument.activeElement, docsClose, 'Tab on the last docs control must wrap to the first control.');
docsDone.disabled = true;
assert.equal(vm.runInContext('precisionDocsFocusable(document.getElementById("precisionDocsDialog")).length', docsContext), 1, 'Disabled docs controls must be removed from the focus trap list.');
docsDone.disabled = false;

const docsTriggerFocusBeforeEscape = docsTrigger.focusCount;
const docsEscape = docsDialog.emit('keydown', { key: 'Escape' });
assert.equal(docsEscape.defaultPrevented, true, 'Escape must be consumed by the docs dialog.');
assert.equal(docsEscape.propagationStopped, true, 'Escape must not leak from the docs dialog to page shortcuts.');
assert.equal(docsDialog.classList.contains('hidden'), true, 'Escape must close the docs dialog.');
assert.equal(docsDialog.getAttribute('aria-hidden'), 'true');
assert.equal(docsBodyClassList.contains('precision-docs-open'), false, 'Closing docs must release page scroll lock.');
assert.equal(docsTrigger.focusCount, docsTriggerFocusBeforeEscape + 1, 'Closing docs must restore focus to the triggering control.');
assert.equal(docsDocument.activeElement, docsTrigger);

docsDocument.activeElement = docsTrigger;
assert.equal(vm.runInContext('openPrecisionDocsDialog()', docsContext), true);
const docsPointerClose = docsDialog.emit('pointerdown', { target: docsDialog });
assert.equal(docsPointerClose.defaultPrevented, undefined, 'Backdrop pointer close should not fake keyboard handling.');
assert.equal(docsDialog.classList.contains('hidden'), true, 'Clicking the docs backdrop must close the dialog.');

docsDocument.activeElement = docsTrigger;
assert.equal(vm.runInContext('openPrecisionDocsDialog()', docsContext), true);
assert.equal(vm.runInContext('closePrecisionDocsDialog(false)', docsContext), true, 'Docs close must allow callers to suppress focus restoration.');
assert.equal(docsDocument.activeElement, docsClose, 'Suppressed docs close must leave focus untouched.');

function simpleElement(value = '') {
  return {
    value,
    disabled: false,
    clickCount: 0,
    attributes: {},
    classList: classListRecorder(),
    click() { this.clickCount += 1; },
    setAttribute(name, next) { this.attributes[name] = String(next); },
    removeAttribute(name) { delete this.attributes[name]; },
  };
}

const replacementNodes = {
  precisionSourceActions: simpleElement(),
  btnPrecisionReplaceSource: simpleElement(),
  btnPrecisionReplaceFromGallery: simpleElement(),
  precisionReplaceDisabledHint: simpleElement(),
  precisionFileInput: simpleElement(),
  precisionResizeWidth: simpleElement('1200'),
  precisionResizeHeight: simpleElement('800'),
  precisionResizePrompt: simpleElement('Extend the scene.'),
  txtPromptPrecision: simpleElement('Make it warmer.'),
  precisionResizePresetName: simpleElement('Cover'),
  precisionResizePreset: simpleElement('saved:cover'),
  precisionResizePromptPreset: simpleElement('creator.precision_size_prompt_preset_banner'),
  precisionVersionRail: simpleElement(),
  precisionCompareBefore: simpleElement(),
  precisionCompareAfter: simpleElement(),
  precisionAnnotationColor: simpleElement('#123456'),
  precisionStrokeWidth: simpleElement('9'),
  precisionViewZoom: simpleElement('140'),
};
const replacementStatuses = [];
let replacementConfirm = true;
let replacementFetches = 0;
const replacementContext = vm.createContext({
  document: {
    getElementById: (id) => replacementNodes[id] || null,
  },
  precisionEditSourceImageData: null,
  precisionEditSourceWidth: 1200,
  precisionEditSourceHeight: 800,
  precisionEditObjects: [], precisionEditHistory: [], precisionEditRedo: [],
  precisionEditSelectedId: null, precisionEditDraftObject: null, precisionEditPointerId: null, precisionEditPointerTarget: null,
  precisionEditDragOrigin: null, precisionEditDragMoved: false, precisionEditTextDraftPoint: null,
  precisionEditPendingInstruction: '', precisionEditEraserSnapshot: null, precisionEditEraserChanged: false,
  precisionEditSession: { source: null, versions: [], selectedVersionId: 'original', baseVersionId: 'original', taskBaseVersionId: null, view: 'after', taskId: null },
  precisionEditSizeMode: 'preserve', precisionCutoutPending: false, precisionTaskMonitorData: null,
  precisionCutoutProbeToken: 0, precisionCutoutOperationToken: 0, precisionVersionLoadToken: 0,
  precisionCanvasResizeState: null, precisionEditPointerFinishing: false, precisionEditSourceImage: {}, precisionEditIdCounter: 8, precisionEditLabelCounter: 9,
  precisionComparePointerId: 3, precisionComparePointerTarget: {}, precisionTaskSourceGeneration: 4,
  precisionSourceLoadGeneration: 7, precisionPendingSourceIntent: null,
  precisionEditSelectedModel: { providerId: 'endpoint-a', model: 'edit-a' }, precisionEditTool: 'brush', precisionViewZoom: 140,
  precisionGenerationControlState: 'idle', genIsPrecisionTask: false, genCurrentGenId: null, genCancelRequested: false,
  lastGenContext: { mode: 'precision_edit' },
  confirm: () => replacementConfirm,
  setStatus: (value) => replacementStatuses.push(value),
  i18nText: (key) => key,
  cancelPrecisionEditText: () => {}, endPrecisionCanvasResize: () => {}, updatePrecisionTaskMonitor: () => {},
  _authFetch: () => { replacementFetches += 1; return Promise.resolve({ json: () => Promise.resolve({ items: [] }) }); },
  alert: () => {}, escHtml: (value) => value, escAttr: (value) => value, setCreatorWorkbenchMode: () => {}, loadPrecisionEditSourceImage: () => {},
});
vm.runInContext([
  'precisionSourceTaskIsActive', 'updatePrecisionSourceActions', 'precisionSourceHasDirtyState', 'preparePrecisionSourceReplacement',
  'requestPrecisionLocalSource', 'resetPrecisionSourceSpecificState', 'openPrecisionGalleryPicker',
].map(extractFunction).join('\n'), replacementContext);
vm.runInContext('updatePrecisionSourceActions()', replacementContext);
assert.equal(replacementNodes.precisionSourceActions.classList.contains('hidden'), true, 'Replace actions must stay hidden before a source has loaded.');
assert.equal(replacementNodes.precisionReplaceDisabledHint.classList.contains('sr-only'), true, 'The inactive replacement status must remain visually hidden.');
assert.equal(replacementNodes.precisionReplaceDisabledHint.classList.contains('is-visible'), false, 'The inactive replacement status must not use the visible state class.');
vm.runInContext("precisionEditSourceImageData = 'data:image/png;base64,source'; updatePrecisionSourceActions()", replacementContext);
assert.equal(replacementNodes.precisionSourceActions.classList.contains('hidden'), false, 'Replace actions must appear after a source image loads.');
assert.equal(replacementNodes.btnPrecisionReplaceSource.disabled, false);
assert.equal(replacementNodes.btnPrecisionReplaceFromGallery.disabled, false);
vm.runInContext("genIsPrecisionTask = true; genCurrentGenId = 'active-task'; updatePrecisionSourceActions()", replacementContext);
assert.equal(replacementNodes.btnPrecisionReplaceSource.disabled, true, 'An active precision task must disable local replacement in the UI.');
assert.equal(replacementNodes.btnPrecisionReplaceFromGallery.disabled, true, 'An active precision task must disable gallery replacement in the UI.');
assert.equal(replacementNodes.btnPrecisionReplaceSource.attributes['aria-disabled'], 'true');
assert.equal(replacementNodes.precisionReplaceDisabledHint.classList.contains('sr-only'), false, 'An active precision task must expose the replacement status visually.');
assert.equal(replacementNodes.precisionReplaceDisabledHint.classList.contains('is-visible'), true, 'An active precision task must use the explicit visible status class.');
assert.equal(vm.runInContext('requestPrecisionLocalSource()', replacementContext), false, 'Local source handler must fail closed while a precision task is active.');
assert.equal(replacementNodes.precisionFileInput.clickCount, 0, 'Active-task local replacement must not open the file picker.');
assert.equal(vm.runInContext('openPrecisionGalleryPicker()', replacementContext), false, 'Gallery handler must fail closed while a precision task is active.');
assert.equal(replacementFetches, 0, 'Active-task gallery replacement must not fetch gallery data.');

vm.runInContext("genIsPrecisionTask = false; genCurrentGenId = null; precisionEditObjects = [{ id: 'dirty' }]; precisionEditSession = { source: { id: 'original' }, versions: [{ id: 'version-1' }], selectedVersionId: 'version-1', baseVersionId: 'version-1', taskBaseVersionId: 'version-1', view: 'compare', taskId: 'old-task' }; precisionEditSizeMode = 'resize';", replacementContext);
vm.runInContext('updatePrecisionSourceActions()', replacementContext);
assert.equal(replacementNodes.precisionReplaceDisabledHint.classList.contains('sr-only'), true, 'The replacement status must return to screen-reader-only presentation when the task becomes idle.');
assert.equal(replacementNodes.precisionReplaceDisabledHint.classList.contains('is-visible'), false, 'The visible status class must clear when the task becomes idle.');
replacementConfirm = false;
const beforeCancelledReplacement = vm.runInContext('JSON.stringify({ precisionEditObjects, precisionEditSession, precisionEditSizeMode, precisionEditSourceImageData, precisionEditTool, precisionEditSelectedModel, precisionViewZoom })', replacementContext);
assert.equal(vm.runInContext('preparePrecisionSourceReplacement()', replacementContext), false, 'Cancelling dirty-source confirmation must stop replacement.');
assert.equal(vm.runInContext('JSON.stringify({ precisionEditObjects, precisionEditSession, precisionEditSizeMode, precisionEditSourceImageData, precisionEditTool, precisionEditSelectedModel, precisionViewZoom })', replacementContext), beforeCancelledReplacement, 'Cancelling replacement must leave precision state unchanged.');
replacementConfirm = true;
assert.equal(vm.runInContext('preparePrecisionSourceReplacement()', replacementContext), true, 'Confirming a dirty-source replacement must permit the source transition.');
vm.runInContext('resetPrecisionSourceSpecificState(8)', replacementContext);
const resetState = JSON.parse(vm.runInContext('JSON.stringify({ source: precisionEditSourceImageData, objects: precisionEditObjects, history: precisionEditHistory, redo: precisionEditRedo, session: precisionEditSession, sizeMode: precisionEditSizeMode, tool: precisionEditTool, model: precisionEditSelectedModel, zoom: precisionViewZoom })', replacementContext));
assert.equal(resetState.source, null);
assert.deepEqual(resetState.objects, []);
assert.deepEqual(resetState.history, []);
assert.deepEqual(resetState.redo, []);
assert.deepEqual(resetState.session.versions, []);
assert.equal(resetState.session.taskId, null, 'A confirmed replacement must clear source-specific task state.');
assert.equal(resetState.sizeMode, 'preserve');
assert.equal(resetState.tool, 'brush', 'Source replacement must preserve the active annotation tool.');
assert.deepEqual(resetState.model, { providerId: 'endpoint-a', model: 'edit-a' }, 'Source replacement must preserve endpoint/model selection.');
assert.equal(resetState.zoom, 140, 'Source replacement must preserve view zoom.');
assert.equal(replacementNodes.precisionAnnotationColor.value, '#123456', 'Source replacement must preserve annotation color.');
assert.equal(replacementNodes.precisionStrokeWidth.value, '9', 'Source replacement must preserve annotation line width.');

const readers = [];
const localLoadCalls = [];
const localFileContext = vm.createContext({
  precisionPendingSourceIntent: null,
  precisionSourceLoadGeneration: 0,
  FileReader: class FakeFileReader {
    constructor() { readers.push(this); this.result = ''; }
    readAsDataURL(file) { this.file = file; }
  },
  preparePrecisionSourceReplacement: () => true,
  loadPrecisionEditSourceImage: (...args) => localLoadCalls.push(args),
  alert: () => {},
  i18nText: (key) => key,
});
vm.runInContext(extractFunction('loadPrecisionEditLocalFile'), localFileContext);
const localInputA = { files: [{ type: 'image/png', name: 'a.png' }], value: 'a' };
const localInputB = { files: [{ type: 'image/png', name: 'b.png' }], value: 'b' };
vm.runInContext('loadPrecisionEditLocalFile', localFileContext)({ currentTarget: localInputA });
vm.runInContext('loadPrecisionEditLocalFile', localFileContext)({ currentTarget: localInputB });
readers[1].result = 'data:image/png;base64,B';
readers[1].onload();
readers[0].result = 'data:image/png;base64,A';
readers[0].onload();
assert.equal(localLoadCalls.length, 1, 'A late FileReader completion must not replace the newer local file selection.');
assert.equal(localLoadCalls[0][0], 'data:image/png;base64,B');

let activeFileReaderCount = 0;
const activeFileContext = vm.createContext({
  precisionPendingSourceIntent: { approved: true },
  precisionSourceLoadGeneration: 17,
  precisionSourceTaskIsActive: () => true,
  FileReader: class ActiveFileReader {
    constructor() { activeFileReaderCount += 1; }
    readAsDataURL() {}
  },
  preparePrecisionSourceReplacement: () => { throw new Error('An existing approved intent must still be rechecked against active task state.'); },
  loadPrecisionEditSourceImage: () => { throw new Error('Active task must never begin a source image load.'); },
  alert: () => {}, i18nText: (key) => key,
});
vm.runInContext(extractFunction('loadPrecisionEditLocalFile'), activeFileContext);
const activeFileInput = { files: [{ type: 'image/png', name: 'late-choice.png' }], value: 'late-choice' };
vm.runInContext('loadPrecisionEditLocalFile', activeFileContext)({ currentTarget: activeFileInput });
assert.equal(activeFileReaderCount, 0, 'A task that becomes active while the OS file picker is open must fail closed before FileReader starts.');
assert.equal(vm.runInContext('precisionSourceLoadGeneration', activeFileContext), 17, 'A late local picker change during an active task must not advance the source generation.');

const imageLoads = [];
const imageHarnessNodes = {
  precisionAnnotationCanvas: { width: 0, height: 0, classList: classListRecorder() },
  precisionCanvasShell: { classList: classListRecorder() },
  precisionBaseImage: { classList: classListRecorder() },
  precisionUploadZone: { classList: classListRecorder() },
  precisionCanvasDimensions: { textContent: '' },
  precisionCanvasSurface: { style: {}, classList: classListRecorder() },
  txtPromptPrecision: simpleElement(),
};
const imageLoadContext = vm.createContext({
  document: { getElementById: (id) => imageHarnessNodes[id] || null },
  Image: class FakeImage { constructor() { imageLoads.push(this); this.naturalWidth = 1200; this.naturalHeight = 800; } },
  INPAINT_MAX_PIXELS: 24000000,
  precisionSourceLoadGeneration: 0, precisionEditSourceImageData: null, precisionEditSourceWidth: 0, precisionEditSourceHeight: 0,
  precisionEditObjects: [], precisionEditHistory: [], precisionEditRedo: [], precisionEditLabelCounter: 0, precisionEditSelectedId: null, precisionEditDraftObject: null,
  precisionEditSizeMode: 'preserve', precisionEditSession: { source: { id: 'original' }, versions: [], selectedVersionId: 'original', baseVersionId: 'original' },
  ensurePrecisionEditPanel: () => {}, resetPrecisionSourceSpecificState: () => {}, requestAnimationFrame: (callback) => callback(),
  reflowPrecisionCanvasVisualSize: () => {}, fitPrecisionCanvasToWindow: () => {}, setPrecisionSizeMode: () => {}, renderPrecisionEditCanvas: () => {}, updatePrecisionEditControls: () => {}, renderPrecisionEditSession: () => {}, updatePrecisionCutoutAvailability: () => {}, updatePrecisionSourceActions: () => {},
  alert: () => {}, i18nText: (key) => key,
});
vm.runInContext(extractFunction('loadPrecisionEditSourceImage'), imageLoadContext);
vm.runInContext("loadPrecisionEditSourceImage('data:image/png;base64,A', '', { preserveSession: true })", imageLoadContext);
vm.runInContext("loadPrecisionEditSourceImage('data:image/png;base64,B', '', { preserveSession: true })", imageLoadContext);
imageLoads[1].onload();
imageLoads[0].onload();
assert.equal(vm.runInContext('precisionEditSourceImageData', imageLoadContext), 'data:image/png;base64,B', 'A late Image.onload completion must not replace the newer source image.');

const galleryDeferred = deferred();
let galleryCreated = 0;
let galleryJsonCalls = 0;
const galleryContext = vm.createContext({
  precisionEditSourceImageData: 'data:image/png;base64,source', precisionSourceLoadGeneration: 4,
  precisionSourceHasDirtyState: () => false, preparePrecisionSourceReplacement: () => true, precisionSourceTaskIsActive: () => false,
  _authFetch: () => galleryDeferred.promise, setStatus: () => {}, i18nText: (key) => key,
  document: { createElement: () => { galleryCreated += 1; return eventNode(); }, body: { appendChild: () => {} }, getElementById: () => null },
  alert: () => {}, escHtml: (value) => value, escAttr: (value) => value, setCreatorWorkbenchMode: () => {}, loadPrecisionEditSourceImage: () => {},
});
vm.runInContext(extractFunction('openPrecisionGalleryPicker'), galleryContext);
assert.equal(vm.runInContext('openPrecisionGalleryPicker()', galleryContext), true);
galleryDeferred.resolve({
  ok: true,
  json: () => {
    galleryJsonCalls += 1;
    vm.runInContext('precisionSourceLoadGeneration = 6', galleryContext);
    return Promise.resolve({ items: [{ data: 'data:image/png;base64,stale' }] });
  },
});
await new Promise((resolve) => setImmediate(resolve));
await new Promise((resolve) => setImmediate(resolve));
assert.equal(galleryJsonCalls, 1, 'The stale gallery harness must parse a successful HTTP response before the source-generation guard runs.');
assert.equal(galleryCreated, 0, 'The source-generation guard must prevent a parsed stale gallery response from rendering a picker.');

const versionContext = vm.createContext({
  precisionSourceLoadGeneration: 2,
  precisionEditSession: { source: { id: 'original' }, versions: [] },
  precisionLocalPathUrl: (value) => '/api/gallery/image/' + value,
  appendPrecisionEditImageVersion: (value) => versionContext.appended.push(value),
  appended: [],
});
vm.runInContext(extractFunction('appendPrecisionEditVersion'), versionContext);
vm.runInContext("appendPrecisionEditVersion({ success: true, local_path: 'old.png' }, 1)", versionContext);
assert.deepEqual(versionContext.appended, [], 'An old generation must not append a precision result version.');
vm.runInContext("appendPrecisionEditVersion({ success: true, local_path: 'current.png' }, 2)", versionContext);
assert.deepEqual(versionContext.appended, ['/api/gallery/image/current.png']);

const terminalAppends = [];
const terminalContext = vm.createContext({
  document: { getElementById: () => null },
  precisionTaskSourceGeneration: 1, precisionSourceLoadGeneration: 2,
  precisionEditSession: { taskSourceGeneration: 1 },
  currentResults: {}, currentGroupTimings: {}, genCurrentGenId: 'old-task', genCancelRequested: false,
  stopGenPolling: () => {}, updatePrecisionTaskMonitor: () => {}, showResults: () => {}, loadGallery: () => {}, setGenerationControls: () => {}, showGenerationProgressCloseButton: () => {}, setStatus: () => {},
  appendPrecisionEditVersion: (...args) => terminalAppends.push(args), i18nText: (key) => key,
  window: {},
});
vm.runInContext(extractFunction('finishGenerationTerminalStatus'), terminalContext);
assert.equal(vm.runInContext("finishGenerationTerminalStatus({ status: 'completed', results: { old: { success: true, local_path: 'old.png' } }, provider_states: {}, elapsed_seconds: 1 }, true)", terminalContext), true);
assert.deepEqual(terminalAppends, [], 'A terminal result from an old source generation must not append a version.');

const sizeNoticeNodes = {
  precisionTaskMonitor: { classList: classListRecorder() },
  precisionTaskStatus: { textContent: '' },
  precisionTaskProgress: { textContent: '' },
  precisionTaskElapsed: { textContent: '' },
  precisionTaskLog: { textContent: '' },
  precisionTaskProgressBar: {
    style: {},
    attributes: {},
    classList: classListRecorder(),
    setAttribute(name, value) { this.attributes[name] = String(value); },
    removeAttribute(name) { delete this.attributes[name]; },
  },
  precisionTaskProgressFill: {
    style: {},
    attributes: {},
    classList: classListRecorder(),
    setAttribute(name, value) { this.attributes[name] = String(value); },
    removeAttribute(name) { delete this.attributes[name]; },
  },
};
const sizeNoticeContext = vm.createContext({
  document: { getElementById: (id) => sizeNoticeNodes[id] || null },
  precisionTaskMonitorData: null,
  precisionTaskMonitorStartedAtMs: 0,
  precisionTaskMonitorElapsedSeconds: null,
  precisionTaskMonitorTerminal: false,
  precisionTaskMonitorTimer: null,
  precisionSourceTaskStatus: 'idle',
  precisionSourceTaskEpoch: 0,
  precisionPendingSourceIntent: null,
  Date,
  Number,
  Object,
  String,
  Array,
  Math,
  clearInterval: () => {},
  setInterval: () => 1,
  i18nText: (key, params) => ({
    'status.queued': 'queued',
    'status.failed': 'failed',
    'creator.precision_output_size_adjusted': `Upstream returned ${params.actual}; locally fit/cropped to ${params.target}.`,
    'creator.precision_output_size_strict_mismatch': `Upstream returned ${params.actual}, target was ${params.target}; strict matching failed.`,
  }[key] || key),
  _smartScroll: () => {},
  updatePrecisionSourceActions: () => {},
});
vm.runInContext([
  extractFunction('precisionTaskMonitorIsTerminal'),
  extractFunction('precisionTaskMonitorStartedAt'),
  extractFunction('renderPrecisionTaskMonitorElapsed'),
  extractFunction('precisionDisplaySize'),
  extractFunction('precisionDisplaySizeFromFields'),
  extractFunction('precisionOutputSizeNoticeFromRecord'),
  extractFunction('precisionOutputSizeNotices'),
  extractFunction('updatePrecisionTaskMonitor'),
  extractFunction('generationFailureMessage'),
].join('\n'), sizeNoticeContext);
vm.runInContext(`updatePrecisionTaskMonitor({
  status: 'completed',
  provider_states: {
    provider: {
      status: 'completed',
      log: ['provider done'],
      result: { success: true, actual_size: '1376x768', adjusted_size: '1536x864', size_adjusted_warning: true }
    }
  },
  elapsed_seconds: 1
})`, sizeNoticeContext);
assert.ok(sizeNoticeNodes.precisionTaskLog.textContent.includes('Upstream returned 1376x768; locally fit/cropped to 1536x864.'), 'Precision task log must render backend size-adjustment warnings.');
assert.equal(vm.runInContext(`generationFailureMessage({
  status: 'failed',
  provider_states: {
    provider: { result: { code: 'precision_edit_output_size_mismatch', actual_size: '1376x768', target_size: '1536x864' } }
  }
})`, sizeNoticeContext), 'Upstream returned 1376x768, target was 1536x864; strict matching failed.', 'Strict mismatch details must become the visible failure message.');

cutoutCalls.length = 0;
vm.runInContext("precisionSourceLoadGeneration = 21; precisionCutoutPending = false; precisionCutoutOperationToken = 0; precisionEditSourceImageData = 'data:image/png;base64,c291cmNl'; precisionEditSourceWidth = 4; precisionEditSourceHeight = 3; precisionEditSession.source = { id: 'original', data: precisionEditSourceImageData }; precisionEditSession.baseVersionId = 'original';", cutoutContext);
const staleCutoutResponse = deferred();
const cutoutVersionCountBeforeStaleResponse = vm.runInContext('precisionEditSession.versions.length', cutoutContext);
cutoutFetch = async (url) => {
  cutoutCalls.push(url);
  if (url.endsWith('/capabilities')) return cutoutResponse(200, readyCapability);
  return staleCutoutResponse.promise;
};
const staleCutout = vm.runInContext('startPrecisionCutout()', cutoutContext);
for (let index = 0; index < 10 && cutoutCalls.length < 2; index += 1) await new Promise((resolve) => setImmediate(resolve));
assert.equal(cutoutCalls.length, 2, 'The stale-cutout harness must reach the image operation before switching source generations.');
vm.runInContext('precisionSourceLoadGeneration = 22', cutoutContext);
staleCutoutResponse.resolve(cutoutResponse(200, {
  contract: 'genbox-cutout-v1', success: true, status: 'completed', width: 4, height: 3,
  image_data: 'data:image/png;base64,iVBORw0KGgoAAAAA', gallery_url: '/api/gallery/image/stale-cutout.png',
}));
assert.equal(await staleCutout, false, 'An old cutout response must resolve harmlessly after source replacement.');
assert.equal(vm.runInContext('precisionEditSession.versions.length', cutoutContext), cutoutVersionCountBeforeStaleResponse, 'An old cutout response must not append a version.');

cutoutCalls.length = 0;
cutoutStatuses.length = 0;
cutoutFetch = async (url) => {
  cutoutCalls.push(url);
  if (url.endsWith('/capabilities')) return cutoutResponse(200, readyCapability);
  return cutoutResponse(200, {
    contract: 'genbox-cutout-v1', success: true, status: 'completed', width: 4, height: 3,
    source_preserved: true, transparent: true, preview_background: 'checkerboard',
    image_data: 'data:image/png;base64,iVBORw0KGgoFALLBACK', gallery_url: '/api/gallery/image/fallback.png',
    filename: 'fallback.png', adapters: ['u2net-human-seg-onnx'],
    adapter: 'u2net-human-seg-onnx', fallback_from: 'requested-adapter',
  });
};
assert.equal(await vm.runInContext('startPrecisionCutout()', cutoutContext), true, 'A bounded backend fallback response should still append a valid result.');
cutoutState = vm.runInContext('({ precisionEditSession, precisionCutoutPending })', cutoutContext);
const fallbackVersion = cutoutState.precisionEditSession.versions.at(-1);
assert.equal(fallbackVersion.adapter, 'u2net-human-seg-onnx');
assert.equal(fallbackVersion.fallbackFrom, 'requested-adapter');
assert.ok(cutoutStatus.textContent.includes('creator.cutout_completed_fallback'));
assert.ok(cutoutStatuses.some((status) => status.includes('creator.cutout_completed_fallback')));

expect(/@media \(max-width: 400px\)\s*\{[\s\S]*?\.precision-workbench-help-popover\s*\{[\s\S]*?right:\s*auto;[\s\S]*?left:\s*12px;[\s\S]*?width:\s*min\(320px, calc\(100vw - 114px\)\);[\s\S]*?max-width:\s*calc\(100vw - 114px\);[\s\S]*?margin:\s*0;[\s\S]*?\}[\s\S]*?\}/.test(css), 'The narrow-mobile contract must tolerate fractional viewport widths while keeping the help popover inside viewport bounds.');

console.log('precision-edit UI static assertions passed');
