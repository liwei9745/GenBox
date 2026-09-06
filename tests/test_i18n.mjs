import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(root, 'static/js/i18n.js'), 'utf8');
const warnings = [];
const context = {
  window: {
    console: { warn: (...args) => warnings.push(args) },
  },
};

vm.runInNewContext(source, context);
const i18n = context.window.GenBoxI18n;
assert.ok(i18n, 'i18n module must initialize');

context.window.__genboxLanguage = 'zh-CN';
assert.equal(i18n.t('prompt.shuffle'), '换一批');

context.window.__genboxLanguage = 'en';
assert.equal(i18n.t('prompt.shuffle'), 'Shuffle');

const presetKeys = [
  'creator.precision_size_preset_name',
  'creator.precision_size_preset_name_placeholder',
  'creator.precision_size_saved_actions',
  'creator.precision_size_save_preset',
  'creator.precision_size_delete_preset',
  'creator.precision_size_reset_presets',
  'creator.precision_size_preset_name_invalid',
  'creator.precision_size_preset_exists',
  'creator.precision_size_preset_name_duplicate',
  'creator.precision_size_preset_size_duplicate',
  'creator.precision_size_preset_limit',
  'creator.precision_size_preset_storage_error',
  'creator.precision_size_preset_saved',
  'creator.precision_size_preset_delete_saved_only',
  'creator.precision_size_preset_deleted',
  'creator.precision_size_preset_reset_empty',
  'creator.precision_size_preset_reset_confirm',
  'creator.precision_size_preset_reset_done',
  'creator.precision_size_preset_unconfirmed',
  'creator.precision_size_preset_undeclared',
];

const promptPresetKeys = [
  'creator.precision_size_prompt_preset',
  'creator.precision_size_prompt_preset_choose',
  'creator.precision_size_prompt_preset_append_hint',
  'creator.precision_size_prompt_preset_keep_style_subject',
  'creator.precision_size_prompt_preset_keep_person',
  'creator.precision_size_prompt_preset_center_subject',
  'creator.precision_size_prompt_preset_extend_left',
  'creator.precision_size_prompt_preset_extend_right',
  'creator.precision_size_prompt_preset_banner',
  'creator.precision_size_prompt_preset_too_long',
];

const precisionSizeCapabilityKeys = [
  'creator.precision_aspect_ratio_hint_empty',
  'creator.precision_aspect_ratio_hint',
  'creator.precision_output_size_policy',
  'creator.precision_output_size_policy_strict',
  'creator.precision_output_size_policy_fit_crop',
  'creator.precision_output_size_policy_strict_hint',
  'creator.precision_output_size_policy_fit_crop_hint',
  'creator.precision_output_size_adjusted',
  'creator.precision_output_size_strict_mismatch',
  'creator.precision_size_capability_label',
  'creator.precision_size_capability_model_required',
  'creator.precision_size_capability_invalid',
  'creator.precision_size_capability_unknown',
  'creator.precision_size_capability_unsupported',
  'creator.precision_size_capability_supported',
  'creator.precision_size_confirm_action_empty',
  'creator.precision_size_revoke_action_empty',
  'creator.precision_size_confirm_action',
  'creator.precision_size_revoke_action',
  'creator.precision_size_confirm_dialog',
  'creator.precision_size_revoke_dialog',
  'creator.precision_size_confirming',
  'creator.precision_size_revoking',
  'creator.precision_size_confirmed',
  'creator.precision_size_revoked',
  'creator.precision_size_capability_save_failed',
];

const cutoutKeys = [
  'creator.cutout_checking',
  'creator.cutout_check_failed',
  'creator.cutout_source_required',
  'creator.cutout_processing',
  'creator.cutout_busy',
  'creator.cutout_timeout',
  'creator.cutout_failed',
  'creator.cutout_result_invalid',
  'creator.cutout_source_changed',
  'creator.cutout_completed',
];

const precisionReplaceAndHelpKeys = [
  'creator.precision_help_label',
  'creator.precision_help_title',
  'creator.precision_help_steps',
  'creator.precision_help_send_result',
  'creator.precision_docs_open',
  'creator.precision_docs_close',
  'creator.precision_docs_kicker',
  'creator.precision_docs_title',
  'creator.precision_docs_intro',
  'creator.precision_docs_shapes_title',
  'creator.precision_docs_shapes_body',
  'creator.precision_docs_eraser_title',
  'creator.precision_docs_eraser_body',
  'creator.precision_docs_text_title',
  'creator.precision_docs_text_body',
  'creator.precision_docs_cutout_title',
  'creator.precision_docs_cutout_body',
  'creator.precision_docs_cutout_model_title',
  'creator.precision_docs_cutout_model_purpose',
  'creator.precision_docs_cutout_model_links_label',
  'creator.precision_docs_cutout_model_project_guide',
  'creator.precision_docs_cutout_model_upstream',
  'creator.precision_docs_cutout_model_official',
  'creator.precision_docs_cutout_model_step_download',
  'creator.precision_docs_cutout_model_step_place',
  'creator.precision_docs_cutout_model_step_verify',
  'creator.precision_docs_cutout_model_boundary',
  'creator.precision_docs_resize_title',
  'creator.precision_docs_resize_body',
  'creator.precision_docs_versions_title',
  'creator.precision_docs_versions_body',
  'creator.precision_docs_fullscreen_title',
  'creator.precision_docs_fullscreen_body',
  'creator.precision_docs_models_title',
  'creator.precision_docs_models_body',
  'creator.precision_config_docs',
  'creator.precision_retry_model_required',
  'creator.precision_replace_image',
  'creator.precision_replace_task_active',
  'creator.precision_replace_confirm',
  'creator.precision_edit_loading_gallery',
  'creator.precision_edit_gallery_empty',
  'creator.precision_edit_gallery_loaded',
  'creator.precision_session_gallery_show',
  'creator.precision_workflow_history',
  'creator.precision_workflow_history_refresh',
  'creator.precision_workflow_history_filters',
  'creator.precision_workflow_history_filter_trigger',
  'creator.precision_workflow_history_filter_title',
  'creator.precision_workflow_history_action_title',
  'creator.precision_workflow_history_date_unknown',
  'creator.precision_workflow_history_id',
  'creator.precision_workflow_history_id_placeholder',
  'creator.precision_workflow_history_id_invalid',
  'creator.precision_workflow_history_loading',
  'creator.precision_workflow_history_loaded',
  'creator.precision_workflow_history_load_failed',
  'creator.precision_workflow_history_empty',
  'creator.precision_workflow_history_original',
  'creator.precision_workflow_history_step',
  'creator.precision_workflow_history_edits',
  'creator.precision_workflow_history_selected',
  'creator.precision_workflow_history_view_image',
  'creator.precision_workflow_history_restore',
  'creator.precision_workflow_history_restoring',
  'creator.precision_workflow_history_restored',
];

const precisionCompactStatusAndAccessibilityKeys = [
  'creator.cutout_model_ready',
  'creator.cutout_model_verification',
  'creator.cutout_model_verification_value',
  'creator.cutout_model_runtime_probe',
  'creator.cutout_model_runtime_probe_value',
  'creator.cutout_capability_refresh',
  'creator.cutout_capability_refresh_tooltip',
  'creator.cutout_algorithm_modnet_lab_notice',
  'creator.precision_fullscreen_label',
  'creator.precision_image_fullscreen',
  'creator.precision_image_fullscreen_label',
  'creator.precision_image_fullscreen_tooltip',
  'creator.precision_fullscreen_tooltip',
  'creator.precision_exit_fullscreen_label',
  'creator.precision_exit_fullscreen_tooltip',
  'creator.precision_fullscreen_double_click',
  'creator.precision_fullscreen_hint',
  'creator.precision_canvas_interaction_hint',
  'creator.precision_canvas_resize_label',
  'creator.precision_canvas_resize_tooltip',
];

const precisionModelVisibilityKeys = [
  'creator.precision_model_display',
  'creator.precision_model_display_all',
  'creator.precision_model_display_summary',
  'creator.precision_model_menu_title',
  'creator.precision_model_menu_hint',
  'creator.precision_model_select_all',
  'creator.precision_model_clear',
  'creator.precision_model_apply',
  'creator.precision_model_keep_one',
  'creator.precision_model_none_available',
];

for (const language of ['zh-CN', 'en']) {
  context.window.__genboxLanguage = language;
  for (const key of presetKeys) {
    const value = i18n.t(key, { name: 'Cover', count: 20 });
    assert.notEqual(value, key, `${key} must exist in ${language}`);
    assert.ok(value.trim(), `${key} must not be empty in ${language}`);
  }
  for (const key of promptPresetKeys) {
    const value = i18n.t(key);
    assert.notEqual(value, key, `${key} must exist in ${language}`);
    assert.ok(value.trim(), `${key} must not be empty in ${language}`);
  }
  for (const key of precisionSizeCapabilityKeys) {
    const value = i18n.t(key, { size: '1536x864', ratio: '16:9 aspect ratio', actual: '1376x768', target: '1536x864' });
    assert.notEqual(value, key, `${key} must exist in ${language}`);
    assert.ok(value.trim(), `${key} must not be empty in ${language}`);
  }
  for (const key of cutoutKeys) {
    const value = i18n.t(key);
    assert.notEqual(value, key, `${key} must exist in ${language}`);
    assert.ok(value.trim(), `${key} must not be empty in ${language}`);
  }
  for (const key of precisionReplaceAndHelpKeys) {
    const value = i18n.t(key);
    assert.notEqual(value, key, `${key} must exist in ${language}`);
    assert.ok(value.trim(), `${key} must not be empty in ${language}`);
  }
  for (const key of precisionModelVisibilityKeys) {
    const value = i18n.t(key, { selected: 2, total: 3, count: 3 });
    assert.notEqual(value, key, `${key} must exist in ${language}`);
    assert.ok(value.trim(), `${key} must not be empty in ${language}`);
  }
  for (const key of precisionCompactStatusAndAccessibilityKeys) {
    const value = i18n.t(key);
    assert.notEqual(value, key, `${key} must exist in ${language}`);
    assert.ok(value.trim(), `${key} must not be empty in ${language}`);
  }
}

context.window.__genboxLanguage = 'zh-CN';
assert.equal(i18n.t('creator.precision_size_preset_limit', { count: 20 }), '最多保存 20 个尺寸预设。');
assert.equal(i18n.t('creator.precision_size_preset_saved', { name: '横版封面' }), '已保存“横版封面”。');
assert.equal(i18n.t('creator.precision_size_prompt_preset_keep_style_subject'), '保持原有画面风格与主体元素，向四周自然扩展');
assert.equal(i18n.t('creator.precision_size_prompt_preset_append_hint'), '选择预设会追加到已有说明，不会覆盖；之后仍可自由编辑。');
assert.equal(i18n.t('creator.precision_aspect_ratio_hint', { size: '1792x768', ratio: '21:9 aspect ratio' }), '将发送像素尺寸 1792x768；后端会由它推导“21:9 aspect ratio”构图约束。“8K”等风格词不等于实际输出像素。');
assert.equal(i18n.t('creator.precision_output_size_policy_fit_crop_hint'), '若上游输出接近目标，GenBox 会本地居中裁切并高质量缩放到目标尺寸，不再次调用模型，并记录原始尺寸。');
assert.equal(i18n.t('creator.precision_output_size_strict_mismatch', { actual: '1376x768', target: '1536x864' }), '上游实际 1376x768，目标 1536x864；严格匹配已失败。可改用本地适配，不会自动重试付费请求。');
assert.equal(i18n.t('creator.precision_docs_text_body'), '文字工具单击画布添加文字；切到“选择/移动”后可拖动移动，双击已有文字可再次编辑，选中后可调整字号和颜色。');
assert.equal(i18n.t('creator.precision_docs_eraser_body'), '橡皮擦可点击删除选中的对象，也可在画笔轨迹上拖动擦除；移动、缩放、擦除和清除都可撤销/重做。');
assert.equal(i18n.t('creator.precision_model_display_summary', { selected: 2, total: 3 }), '已显示 2/3 个');
assert.equal(i18n.t('creator.precision_model_menu_hint'), '只影响本机列表可见性；提交仍使用真实模型 ID。');
assert.equal(i18n.t('creator.cutout_model_ready'), '本地模型已就绪');
assert.equal(i18n.t('creator.precision_docs_cutout_model_step_place'), '在 GenBox 数据目录下创建对应文件夹，并把文件放到所有系统统一的相对位置：');
assert.equal(i18n.t('creator.cutout_algorithm_modnet_lab_notice'), '本地实验室（实验性）：人像优化，复杂背景可能误抠');
context.window.__genboxLanguage = 'en';
assert.equal(i18n.t('creator.precision_size_preset_limit', { count: 20 }), 'You can save up to 20 size presets.');
assert.equal(i18n.t('creator.precision_size_preset_saved', { name: 'Landscape cover' }), 'Saved “Landscape cover”.');
assert.equal(i18n.t('creator.precision_size_prompt_preset_banner'), 'Expand to a banner composition while retaining key elements.');
assert.equal(i18n.t('creator.precision_aspect_ratio_hint', { size: '1792x768', ratio: '21:9 aspect ratio' }), 'Will send pixel size 1792x768; the backend derives “21:9 aspect ratio” as the composition constraint. Style words like “8K” do not set the actual output pixels.');
assert.equal(i18n.t('creator.precision_output_size_policy_strict_hint'), 'Strict is the default. If the upstream size differs, the task fails with the actual size and does not auto-retry a paid request.');
assert.equal(i18n.t('creator.precision_output_size_adjusted', { actual: '1376x768', target: '1536x864' }), 'Upstream returned 1376x768; locally fit/cropped to 1536x864.');
assert.equal(i18n.t('creator.cutout_timeout'), 'Local cutout timed out; the underlying work may still be finishing. Try again later.');
assert.equal(i18n.t('creator.cutout_completed'), 'Cutout complete. A new browseable version was added.');
assert.equal(i18n.t('creator.precision_docs_text_body'), 'With the text tool, click once on the canvas to add text. Switch to Select/Move to drag it, double-click existing text to edit it again, and adjust font size or color while it is selected.');
assert.equal(i18n.t('creator.precision_docs_eraser_body'), 'The eraser can click to delete the selected object, or drag over brush strokes to erase them. Move, resize, erase, and clear actions all support undo/redo.');
assert.equal(i18n.t('creator.precision_model_display_all', { count: 3 }), 'All 3 models');
assert.equal(i18n.t('creator.precision_model_menu_hint'), 'Controls local list visibility only; submissions still use the real model ID.');
assert.equal(i18n.t('creator.cutout_model_ready'), 'Local model ready');
assert.equal(i18n.t('creator.precision_docs_cutout_model_boundary'), 'Automated download is currently disabled. GenBox has not verified the model conversion chain, training-data provenance, license, or commercial-use rights. Review the upstream materials and confirm suitability for your use before downloading or using it.');
assert.equal(i18n.t('creator.cutout_algorithm_modnet_lab_notice'), 'Local lab (experimental): optimized for portraits; complex backgrounds may be cut incorrectly');

assert.deepEqual(warnings, [], 'Known translations must not emit missing-key warnings');
console.log('prompt, precision resize preset, and cutout i18n assertions passed');
