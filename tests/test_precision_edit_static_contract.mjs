import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'static/css/app.css'), 'utf8');
const js = fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8');
const i18n = fs.readFileSync(path.join(root, 'static/js/i18n.js'), 'utf8');
const research = fs.readFileSync(path.join(root, 'docs/precision-edit-v4-research.md'), 'utf8');

assert.match(html, /id="btnPrecisionFullscreen"[^>]+aria-pressed="false"/);
assert.match(html, /id="precisionAnnotationCanvas"[^>]+aria-describedby="precisionCanvasInteractionHint precisionFullscreenHint"/);
assert.match(html, /id="precisionCompareStage"[^>]+data-i18n-title="creator\.precision_fullscreen_double_click"/);
assert.ok(html.includes('storage/models/cutout/u2net_human_seg.onnx'));
assert.ok(html.includes('https://github.com/liwei9745/GenBox/blob/master/docs/CLIENT-QUICKSTART.md'));
assert.ok(html.includes('https://github.com/liwei9745/GenBox/blob/master/docs/CUTOUT-MODEL-GUIDE.md'));
assert.ok(!html.includes('https://github.com/liwei9745/GenBox/blob/main/'));
assert.ok(html.includes('https://github.com/danielgatis/rembg/releases/tag/v0.0.0'));
assert.ok(html.includes('https://github.com/xuebinqin/U-2-Net'));
assert.ok(html.includes('creator.precision_docs_cutout_model_boundary'));
assert.ok(html.includes('id="btnPrecisionStrategyFine"'));
assert.ok(html.includes('id="btnPrecisionStrategyStandard"'));
assert.ok(html.includes('id="btnPrecisionStrategyFast"'));
assert.ok(html.includes('id="btnPrecisionSelectionLocal"'));
assert.ok(html.includes('id="precisionSelectionFeather"'));
assert.ok(!/precision-docs-model-guide[\s\S]*?[A-Za-z]:\\/.test(html), 'The model guide must not expose a Windows absolute path.');

assert.match(html, /id="precisionImageFullscreen"[^>]+tabindex="-1"/, 'Image-only fullscreen viewer must be focusable for lifecycle management.');
assert.ok(html.includes('toggleLightboxImageFullscreen(event)'), 'Lightbox must expose current-image-only fullscreen.');
assert.ok(html.includes('id="precisionSessionGallery"'), 'Precision workbench must expose a current-session result gallery.');
assert.ok(html.includes('id="precisionPromptStrip"'), 'Precision workbench must expose split prompt history.');
assert.match(html, /id="btnPrecisionReplaceSource"[^>]+onclick="togglePrecisionSourceMenu\(\)"[^>]+aria-haspopup="menu"[^>]+aria-expanded="false"/,
  'A loaded precision source must expose an accessible replace-image menu trigger.');
assert.match(html, /id="precisionSourceMenu"[^>]+role="menu"[^>]+hidden[\s\S]*?id="btnPrecisionReplaceLocal"[^>]+role="menuitem"[\s\S]*?data-i18n="creator.precision_edit_local_upload"[\s\S]*?id="btnPrecisionReplaceFromGallery"[^>]+role="menuitem"/,
  'The replace-image menu must clearly offer local and gallery choices.');
assert.ok(html.includes('id="btnPrecisionUpload"') && html.includes('id="btnPrecisionGallery"'), 'The initial empty-canvas source choices must remain available.');
assert.match(html, /id="btnPrecisionUseSelectedAsBase"[^>]+onclick="useSelectedPrecisionVersionAsBase\(\)"[^>]+disabled[^>]+aria-disabled="true"/,
  'Selecting a version must expose a separate, initially disabled use-as-next-base command.');
assert.ok(js.includes('function useSelectedPrecisionVersionAsBase()') && js.includes('return setPrecisionBaseVersion(precisionEditSession.selectedVersionId);'),
  'Only the explicit use-as-next-base command may invoke the existing base-version loader.');
assert.match(css, /precision-version-base-action\s*\{[\s\S]*?grid-column:\s*2;[\s\S]*?grid-row:\s*2;[\s\S]*?max-width:\s*100%;[\s\S]*?text-overflow:\s*ellipsis;/,
  'The base-version command must occupy a bounded second row instead of overflowing the version rail.');
const precisionCanvasShellIndex = html.indexOf('id="precisionCanvasShell"');
const precisionSessionShowcaseIndex = html.indexOf('class="precision-session-showcase"');
assert.ok(precisionCanvasShellIndex !== -1 && precisionSessionShowcaseIndex > precisionCanvasShellIndex, 'Current-session results must render below the precision canvas.');
assert.match(html, /class="precision-session-showcase" aria-label="精准改图图库"[\s\S]*?class="precision-session-showcase-heading"[\s\S]*?精准改图图库[\s\S]*?class="precision-workflow-history-filters"/,
  'Date filtering must be available through workflow history beside the gallery.');
assert.match(html, /id="btnPrecisionWorkflowHistoryFilter"[^>]+aria-haspopup="dialog"[^>]+aria-expanded="false"/,
  'The workflow filter must advertise its collapsed dialog state.');
['近3日', '近5日', '>周<', '>月<', '>季度<', '>半年<', '>年<'].forEach((label) => assert.ok(html.includes(label), `Date filter must expose ${label}.`));
assert.ok(html.includes('id="precisionSessionGallery" class="precision-session-gallery" role="list"'), 'Session gallery must expose list semantics for result thumbnails.');
assert.ok(i18n.includes("creator.precision_session_results"), 'Session gallery heading must have an i18n translation key.');
assert.ok(i18n.includes("creator.precision_session_empty"), 'Session gallery empty state must have an i18n translation key.');
assert.ok(/precision-session-empty/.test(fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8')), 'Session gallery must render an explicit localized empty state.');
assert.ok(html.includes('id="galleryDateFrom"') && html.includes('id="galleryDateTo"'), 'Gallery must expose date range filters.');
assert.ok(html.includes('id="precisionWorkflowHistoryCalendar"') && html.includes('data-workflow-date-range'), 'Workflow history must expose its own calendar and date presets.');
assert.ok(html.includes("setPrecisionWorkflowHistoryDateRange('3d')") && html.includes('clearPrecisionWorkflowHistoryDateFilter()'), 'Workflow date controls must have dedicated handlers.');
assert.ok(css.includes('.precision-image-fullscreen') && css.includes('.precision-session-gallery'), 'Showcase/fullscreen styles must be responsive and scoped.');
assert.ok(css.includes('grid-auto-flow: column') && css.includes('max-width: 100%'), 'Session gallery must stay bounded while supporting multiple result thumbnails.');
assert.match(css, /precision-session-showcase-heading\s*\{[\s\S]*?flex-wrap:\s*wrap/, 'Session gallery heading must wrap instead of overflowing at intermediate widths.');
assert.match(css, /precision-manual-tool-group > \.precision-style-controls\s*\{[\s\S]*?grid-row:\s*2/, 'Manual-edit style controls must occupy a dedicated second row.');
assert.match(css, /precision-manual-tool-group\s*\{[\s\S]*?grid-template-rows:\s*auto auto/, 'Manual-edit controls must reserve two rows even when the inspector is narrow on a wide viewport.');
const primaryToolbarIndex = html.indexOf('class="precision-toolbar-row precision-toolbar-primary"');
const historyToolbarIndex = html.indexOf('class="precision-toolbar-row precision-toolbar-history"');
assert.ok(primaryToolbarIndex !== -1 && historyToolbarIndex > primaryToolbarIndex, 'Annotation history must occupy the toolbar second row.');
assert.match(css, /precision-workbench \.precision-toolbar\s*\{[\s\S]*?display:\s*grid;[\s\S]*?grid-template-rows:\s*auto auto;[\s\S]*?overflow:\s*visible;/,
  'The precision toolbar must use two bounded rows instead of a horizontally clipped strip.');
assert.match(css, /precision-toolbar-primary\s*\{[\s\S]*?repeat\(auto-fit,[\s\S]*?minmax/, 'The first toolbar row must adapt without drifting or clipping.');
assert.ok(html.includes('id="btnPrecisionCutoutCapabilityRefresh"'), 'Cutout model/algorithm recovery must expose a recheck action outside collapsed details.');
assert.ok(js.includes('function refreshPrecisionCutoutSetup()') && js.includes('return updatePrecisionCutoutAvailability()'), 'A failed model refresh must recover through the independent capability probe.');
assert.ok(js.includes("record.adapter === 'u2net-human-seg-onnx'") && js.includes("record.adapter === 'modnet-portrait-onnx'"), 'U2-Net must be the explicit default while the runtime MODNet adapter is labeled separately.');
assert.ok(i18n.includes('creator.cutout_algorithm_modnet_lab_notice'), 'MODNet experimental local-lab guidance must be translated.');
assert.ok(/function filterPrecisionSessionEntries\(entries\)/.test(fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8')), 'Session date filtering must stay local to precision session entries.');
assert.ok(/function bindPrecisionImageFullscreenLifecycle\(\)/.test(fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8')));
assert.match(html, /id="precisionImageFullscreen"[^>]+ondblclick="if\(event\.target===this \|\|/,
  'Image-only fullscreen must not close when the prompt history panel is double-clicked.');
assert.ok(fs.readFileSync(path.join(root, 'static/js/app-all.js'), 'utf8').includes("event.target !== target && !(event.target && event.target.closest && event.target.closest('.precision-image-fullscreen-figure'))"),
  'Image-only fullscreen wheel and middle-click handlers must ignore the prompt history panel.');

assert.ok(css.includes('#panelPrecisionEdit:fullscreen'));
assert.ok(!css.includes('.precision-edit-workspace:fullscreen'), 'Fullscreen must use #panelPrecisionEdit as its sole API root.');
assert.ok(css.includes('height: 100dvh;'));
assert.match(css, /#panelPrecisionEdit:fullscreen[\s\S]+?overflow:\s*hidden;/);
assert.match(css, /@media \(max-width: 760px\)[\s\S]+?precision-edit-inspector[\s\S]+?overflow-y:\s*auto;/);
assert.match(css, /#panelPrecisionEdit:fullscreen textarea[\s\S]+?max-width:\s*100%;/);

assert.ok(research.includes('本地模型已就绪'));
assert.ok(research.includes('storage/models/cutout/u2net_human_seg.onnx'));
assert.ok(research.includes('#panelPrecisionEdit` or `.precision-edit-workspace'));

console.log('precision-edit static documentation and fullscreen contracts passed');
