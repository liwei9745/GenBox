(function () {
  'use strict';
  var key = 'genbox_precision_ui_trial';
  var enabled = false;
  try { enabled = localStorage.getItem(key) === 'on'; } catch (_) {}
  var panel = document.getElementById('panelPrecisionEdit');
  var picker = document.getElementById('precisionModelPicker');
  if (!panel || !picker) return;
  var toolbar = document.createElement('div');
  toolbar.className = 'precision-trial-toolbar';
  var toggle = document.createElement('button');
  toggle.type = 'button';
  toolbar.appendChild(toggle);
  picker.before(toolbar);
  var projections = [];

  function selectProjection(id, label, kind) {
    var source = document.getElementById(id);
    if (!source) return;
    var group = document.createElement('div');
    group.className = 'precision-trial-options ' + kind;
    group.setAttribute('role', 'group');
    group.setAttribute('aria-label', label);
    source.after(group);
    source.classList.add('precision-trial-source');
    var signature = '';
    projections.push(function () {
      var options = Array.from(source.options).filter(function (o) {
        return !o.hidden && !(o.parentElement.tagName === 'OPTGROUP' && o.parentElement.hidden);
      });
      var next = JSON.stringify([source.value, source.disabled, options.map(function (o) {
        return [o.value, o.textContent, o.disabled, o.title];
      })]);
      if (signature === next) return;
      signature = next;
      // Preserve focus when a changed selection causes the projection to refresh.
      var focused = group.contains(document.activeElement) ? document.activeElement.dataset.value : null;
      group.replaceChildren();
      options.forEach(function (o) {
        var button = document.createElement('button');
        button.type = 'button';
        button.dataset.value = o.value;
        button.disabled = source.disabled || o.disabled;
        button.setAttribute('aria-pressed', String(o.value === source.value));
        button.title = o.title || o.textContent;
        if (kind === 'size') {
          var pixels = (o.dataset.size || o.value).match(/(\d+)x(\d+)/);
          if (pixels) {
            var shape = document.createElement('span');
            shape.className = 'precision-trial-aspect';
            var w = Number(pixels[1]), h = Number(pixels[2]);
            shape.style.width = (28 * Math.min(1, w / h)) + 'px';
            shape.style.height = (28 * Math.min(1, h / w)) + 'px';
            shape.setAttribute('aria-hidden', 'true');
            button.appendChild(shape);
          }
        }
        var text = document.createElement('span');
        text.textContent = o.textContent;
        button.appendChild(text);
        button.onclick = function () {
          if (!enabled || source.disabled || o.disabled || o.hidden) return;
          source.value = o.value;
          source.dispatchEvent(new Event('change', { bubbles: true }));
          refresh();
        };
        group.appendChild(button);
        if (focused === o.value) button.focus({ preventScroll: true });
      });
    });
  }

  function switchProjection(onId, offId, label) {
    var on = document.getElementById(onId), off = document.getElementById(offId);
    if (!on || !off) return;
    on.classList.add('precision-trial-source');
    off.classList.add('precision-trial-source');
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'precision-trial-switch';
    button.setAttribute('role', 'switch');
    var thumb = document.createElement('span');
    thumb.className = 'precision-trial-track';
    thumb.setAttribute('aria-hidden', 'true');
    var text = document.createElement('span');
    button.append(thumb, text);
    on.before(button);
    var action = null;
    projections.push(function () {
      var checked = !off.hidden && !off.classList.contains('hidden');
      action = checked ? off : on;
      button.setAttribute('aria-checked', String(checked));
      button.disabled = action.disabled;
      text.textContent = label + (checked ? ' · 已开启' : ' · 未开启');
      button.title = action.textContent;
    });
    // Delegate consent, pending state, cancellation and errors to the existing
    // handlers. Never optimistically grant permission or submit generation.
    button.onclick = function () {
      if (enabled && action && !action.disabled) action.click();
      refresh();
    };
  }

  selectProjection('precisionProtocolSelect', '接入方式', 'segments');
  selectProjection('precisionProtocolSizeModel', '模型尺寸目录', 'composition');
  selectProjection('precisionProtocolProfile', '图片上传方式', 'composition');
  selectProjection('precisionResizeMode', '尺寸方式', 'segments');
  selectProjection('precisionResizePreset', '模型尺寸预设', 'size');
  selectProjection('precisionResizePromptPreset', '构图说明预设', 'composition');
  switchProjection('btnPrecisionAuthorizeModel', 'btnPrecisionRevokeModel', '当前模型改图许可');
  switchProjection('btnPrecisionConfirmResizeSize', 'btnPrecisionRevokeResizeSize', '当前尺寸试用授权');
  ['btnPrecisionProtocolReset', 'btnPrecisionProtocolCheck'].forEach(function (id) {
    var source = document.getElementById(id);
    if (!source) return;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'precision-trial-command';
    button.textContent = source.textContent;
    source.before(button);
    source.classList.add('precision-trial-source');
    button.onclick = function () { if (enabled && !source.disabled) source.click(); refresh(); };
    projections.push(function () { button.disabled = source.disabled; button.hidden = source.hidden; button.textContent = source.textContent; });
  });
  var monitor = document.getElementById('precisionTaskMonitor');
  if (monitor) {
    var icon = monitor.querySelector('.precision-task-heading-icon');
    if (icon) icon.innerHTML = '<svg class="precision-trial-progress-svg" viewBox="0 0 24 24" aria-hidden="true"><circle class="track" cx="12" cy="12" r="9"></circle><path class="pulse" d="M12 3a9 9 0 0 1 9 9"></path></svg>';
    projections.push(function () {
      var state = monitor.className || '';
      monitor.classList.toggle('precision-trial-progress-active', /running|pending|generating|queued/.test(state));
      monitor.classList.toggle('precision-trial-progress-success', /completed|success/.test(state));
      monitor.classList.toggle('precision-trial-progress-failed', /failed|error/.test(state));
    });
  }
  var composition = document.querySelector('.precision-trial-options.composition');
  if (composition) {
    var label = document.querySelector('label[for="precisionResizePromptPreset"]');
    if (label) label.classList.add('precision-trial-composition-field');
  }
  var quick = document.querySelector('.precision-quick-tools');
  if (quick) {
    quick.classList.add('precision-trial-smart-tools');
    quick.querySelectorAll('.precision-action-group').forEach(function (group) {
      group.classList.add('precision-trial-action-card');
      group.querySelectorAll('button').forEach(function (button) {
        button.classList.add('precision-trial-action-button');
      });
    });
    var cutout = quick.querySelector('.precision-cutout-tool');
    if (cutout) cutout.classList.add('precision-trial-local-card');
  }

  function refresh() {
    panel.classList.toggle('precision-ui-trial', enabled);
    toggle.textContent = enabled ? '实验界面 · 切回原版' : '原版界面 · 试用新版';
    projections.forEach(function (update) { update(); });
  }
  toggle.onclick = function () {
    enabled = !enabled;
    try { localStorage.setItem(key, enabled ? 'on' : 'off'); } catch (_) {}
    refresh();
  };
  // Observe only source controls so projection updates cannot create a loop.
  var observer = new MutationObserver(refresh);
  panel.querySelectorAll('.precision-trial-source').forEach(function (source) {
    observer.observe(source, { attributes: true, childList: true, subtree: true, characterData: true });
    source.addEventListener('change', refresh);
  });
  refresh();
})();
