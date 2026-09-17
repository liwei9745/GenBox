(function() {
  'use strict';
  var current = null;
  var feedback = document.querySelector('.video-composer-status');
  if (feedback && document.getElementById('videoFeedbackSlot')) {
    var slot = document.getElementById('videoFeedbackSlot');
    slot.appendChild(feedback);
    var bottom = document.querySelector('#pageVideo .generate-bottom-row');
    bottom.parentElement.insertBefore(slot, bottom);
  }
  function el(id) { return document.getElementById(id); }
  function options(select, values, selected) {
    select.replaceChildren();
    values.forEach(function(value) {
      var option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    if (values.indexOf(selected) !== -1) select.value = selected;
  }
  function reset() {
    current = null;
    el('videoNativeOptions').classList.add('hidden');
    ['videoDurationPresets', 'videoFramesRow', 'videoFPS', 'videoFPSLabel', 'videoDurationLabel'].forEach(function(id) {
      el(id).classList.remove('hidden');
    });
    document.querySelectorAll('#videoI2VPanel button[onclick*="setVideoImageRole"]').forEach(function(button) {
      button.disabled = false;
    });
  }
  function sync() {
    if (!current) return;
    var resolution = el('videoNativeResolution').value;
    var portrait = el('videoNativeAspect').value === '9:16';
    var dims = {'360p':[640,360], '720p':[1280,720], '1080p':[1920,1080], '4k':[3840,2160]}[resolution];
    el('videoSize').value = 'custom';
    el('videoCustomW').value = dims[portrait ? 1 : 0];
    el('videoCustomH').value = dims[portrait ? 0 : 1];
    el('videoFPS').value = '24';
    var durations = current.spec.duration_options.slice();
    if (current.spec.family === 'veo' && (resolution !== '720p' ||
        (window.currentVideoMode !== 'ti2vid' && window.videoImageRole === 'reference'))) durations = [8];
    var duration = el('videoNativeDuration');
    options(duration, durations.map(String), duration.value);
    duration.disabled = !durations.length;
    el('videoNativeDurationField').classList.toggle('hidden', !durations.length);
    el('videoNativeAutoDuration').classList.toggle('hidden', !!durations.length);
    if (durations.length) el('videoFrames').value = Number(duration.value) * 24;
  }
  function apply(spec, model) {
    current = {spec:spec, model:model, providerId:window.selectedVideoProviderIds[0]};
    el('videoNativeOptions').classList.remove('hidden');
    ['videoDurationPresets', 'videoFramesRow', 'videoFPS', 'videoFPSLabel', 'videoDurationLabel'].forEach(function(id) {
      el(id).classList.add('hidden');
    });
    el('videoSize').classList.add('hidden');
    el('videoSizeLabel').classList.add('hidden');
    el('videoCustomSize').classList.add('hidden');
    options(el('videoNativeResolution'), spec.resolutions, spec.resolutions.indexOf(el('videoNativeResolution').value) !== -1 ?
      el('videoNativeResolution').value : '720p');
    options(el('videoFPS'), ['24'], '24');
    el('videoSteps').closest('.form-group').style.display = 'none';
    el('videoNegPrompt').closest('.form-group').style.display = 'none';
    el('videoSeed').closest('.form-group').style.display = spec.supports_seed ? '' : 'none';
    el('videoAdvancedEmpty').classList.toggle('hidden', spec.supports_seed);
    document.querySelectorAll('#videoI2VPanel button[onclick*="setVideoImageRole"]').forEach(function(button) {
      var match = button.getAttribute('onclick').match(/setVideoImageRole\('([^']+)'/);
      button.disabled = !!match && spec.image_roles.indexOf(match[1]) === -1;
    });
    if (spec.image_roles.indexOf(window.videoImageRole) === -1) {
      var role = spec.image_roles[0];
      var button = Array.from(document.querySelectorAll('#videoI2VPanel button[onclick]')).find(function(candidate) {
        return candidate.getAttribute('onclick').indexOf("'" + role + "'") !== -1;
      });
      if (button) window.setVideoImageRole(role, button);
    }
    sync();
  }
  function prepare(tasks) {
    var firstProvider = window.videoProviders.find(function(provider) {return provider.id === window.selectedVideoProviderIds[0];});
    var official = false;
    try { official = new URL(firstProvider.base_url).hostname === 'generativelanguage.googleapis.com'; } catch (_) {}
    if (!current) {
      if (official) throw new Error('Google 模型参数仍在加载，请稍后再提交。');
      return null;
    }
    var select = el('vmodel_' + window.selectedVideoProviderIds[0]);
    if (!select || select.value !== current.model || current.providerId !== window.selectedVideoProviderIds[0])
      throw new Error('模型参数仍在加载，请稍后再提交。');
    if (tasks.some(function(task) { return task.model !== current.model; }))
      throw new Error('Google 原生视频参数不能跨不同模型共用，请选择相同模型对比，或分别提交。');
    sync();
    return {
      resolution:el('videoNativeResolution').value, aspect_ratio:el('videoNativeAspect').value,
      duration_seconds:current.spec.duration_mode === 'seconds' ? Number(el('videoNativeDuration').value) : null,
      frame_rate:24, num_inference_steps:null, negative_prompt:null,
      seed:current.spec.supports_seed && el('videoSeed').value ? Number(el('videoSeed').value) : null
    };
  }
  window.googleVideoUI = {apply:apply, reset:function() {
    reset();
    el('videoSize').classList.remove('hidden');
    el('videoSizeLabel').classList.remove('hidden');
  }, sync:sync, prepare:prepare};
})();
