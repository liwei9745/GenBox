(function () {
  'use strict';
  var enabled = false;
  try { enabled = localStorage.getItem('genbox_precision_ui_trial') === 'on'; } catch (_) {}
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
    var prompt = id === 'precisionResizePromptPreset' ? document.getElementById('precisionResizePrompt') : null;
    if (prompt) prompt.addEventListener('input', refresh);
    var signature = '';
    projections.push(function () {
      var options = Array.from(source.options).filter(function (o) {
        return !(prompt && !o.value) && !o.hidden && !(o.parentElement.tagName === 'OPTGROUP' && o.parentElement.hidden);
      });
      var selected = prompt ? (options.find(function (o) { return o.textContent.trim() === prompt.value.trim(); }) || {}).value : source.value;
      var next = JSON.stringify([selected, source.disabled, options.map(function (o) {
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
        button.setAttribute('aria-pressed', String(o.value === selected));
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
      var unavailable = !checked && (on.hidden || on.classList.contains('hidden'));
      action = checked ? off : on;
      button.setAttribute('aria-checked', String(checked));
      button.disabled = unavailable || action.disabled;
      button.setAttribute('aria-busy', action.getAttribute('aria-busy') || 'false');
      var status = document.getElementById(onId === 'btnPrecisionConfirmResizeSize' ? 'precisionResizeCapabilityStatus' : 'precisionProviderStatus');
      var alreadySupported = unavailable && status && status.dataset.state === 'supported';
      text.textContent = label + (alreadySupported ? ' · 模型已支持' : unavailable ? ' · 暂不可用' : checked ? ' · 已开启' : action.disabled ? ' · 暂不可用' : ' · 未开启');
      button.title = button.disabled && status ? status.textContent : action.textContent;
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
    var originalIcon = icon ? icon.innerHTML : '';
    var iconEnabled = null;
    projections.push(function () {
      if (icon && iconEnabled !== enabled) {
        icon.innerHTML = enabled ? '<svg class="precision-trial-progress-svg" viewBox="0 0 24 24" aria-hidden="true"><circle class="track" cx="12" cy="12" r="9"></circle><path class="pulse" d="M12 3a9 9 0 0 1 9 9"></path></svg>' : originalIcon;
        iconEnabled = enabled;
      }
      ['active', 'completed', 'failed'].forEach(function (state) {
        var name = 'precision-trial-progress-' + (state === 'completed' ? 'success' : state);
        var active = enabled && monitor.classList.contains('precision-task-' + state);
        if (monitor.classList.contains(name) !== active) monitor.classList.toggle(name, active);
      });
    });
    new MutationObserver(refresh).observe(monitor, { attributes:true, attributeFilter:['class'] });
  }
  var composition = document.querySelector('.precision-trial-options.composition');
  if (composition) {
    var label = document.querySelector('label[for="precisionResizePromptPreset"]');
    if (label) {
      label.classList.add('precision-trial-composition-field');
      var heading = document.createElement('strong');
      heading.className = 'precision-trial-heading';
      heading.textContent = '构图预设';
      var subtitle = document.createElement('span');
      subtitle.className = 'precision-trial-heading';
      subtitle.textContent = '选择后填入构图说明';
      label.prepend(heading, subtitle);
    }
  }
  var primary = document.getElementById('btnPrecisionSizePreserve');
  if (primary) {
    primary.parentElement.classList.add('precision-trial-primary');
    primary.parentElement.querySelectorAll('button').forEach(function (button) {
      var symbol = document.createElement('span');
      symbol.className = 'precision-trial-mode-symbol';
      symbol.setAttribute('aria-hidden', 'true');
      symbol.innerHTML = '<svg viewBox="0 0 28 24"><rect x="7" y="5" width="14" height="14" rx="1"/>' +
        (button.id === 'btnPrecisionSizeResize' ? '<path d="M5 2H2v5M23 2h3v5M2 17v5h3M26 17v5h-3"/>' : '') + '</svg>';
      button.prepend(symbol);
    });
  }
  var eraseButtons = panel.querySelectorAll('button[onclick^="startPrecisionAiErase"]');
  projections.push(function () {
    eraseButtons.forEach(function (button) {
      var kind = button.getAttribute('onclick').includes('watermark') ? 'watermark' : 'people';
      var selected = typeof precisionEditPendingInstruction !== 'undefined' && typeof i18nText === 'function' &&
        typeof precisionEditTool !== 'undefined' && precisionEditTool === 'brush' &&
        precisionEditPendingInstruction === i18nText('creator.precision_remove_' + kind + '_instruction');
      if (enabled) button.setAttribute('aria-pressed', String(selected));
      else button.removeAttribute('aria-pressed');
    });
  });
  panel.addEventListener('click', function () { queueMicrotask(refresh); });
  var quick = document.querySelector('.precision-quick-tools');
  if (quick) {
    quick.classList.add('precision-trial-smart-tools');
    quick.querySelectorAll('.precision-action-group').forEach(function (group) {
      group.classList.add('precision-trial-action-card');
      group.querySelectorAll('button').forEach(function (button) {
        button.classList.add('precision-trial-action-button');
      });
    });
    var guidance = document.getElementById('btnPrecisionGuidanceToggle');
    if (guidance) {
      var guidanceText = guidance.querySelector('.precision-guidance-pill-title');
      if (guidanceText) guidanceText.textContent = '一键抠图';
      guidance.setAttribute('aria-label', '一键抠图');
      guidance.title = '一键抠图策略';
    }
    var simpleDuplicate = document.getElementById('btnPrecisionCutoutSimple');
    if (simpleDuplicate) simpleDuplicate.classList.add('precision-trial-duplicate');
    var professionalLauncher = document.getElementById('btnPrecisionCutoutProfessionalOpen');
    if (professionalLauncher) professionalLauncher.classList.add('precision-trial-duplicate');
    var cutoutMode = document.getElementById('precisionCutoutModeSwitch');
    if (cutoutMode) {
      cutoutMode.setAttribute('aria-label', '一键抠图模式');
      cutoutMode.querySelectorAll('button').forEach(function (button) {
        button.title = button.textContent.trim() === '专业模式' ? '打开专业抠图抽屉' : '使用简易抠图';
      });
    }
    var actionGroups = Array.from(quick.querySelectorAll('.precision-action-group'));
    var aiGroup = actionGroups.find(function (group) {
      return (group.firstElementChild && group.firstElementChild.textContent || '').trim() === 'AI 消除';
    });
    var manualGroup = actionGroups.find(function (group) {
      return (group.firstElementChild && group.firstElementChild.textContent || '').trim() === '手动选区';
    });
    [aiGroup, manualGroup].forEach(function (group) {
      if (!group) return;
      group.classList.add('precision-trial-square-tools');
      group.querySelectorAll('button').forEach(function (button, index) {
        var icon = document.createElement('span');
        icon.className = 'precision-trial-tool-icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.innerHTML = index === 0
          ? '<svg viewBox="0 0 32 32"><path d="M7 7h18v18H7z"/><path d="m11 21 4-5 3 3 3-4 3 6"/></svg>'
          : '<svg viewBox="0 0 32 32"><path d="M6 6h20v20H6z"/><path d="M10 16h12M16 10v12"/></svg>';
        button.prepend(icon);
      });
    });
    var cutout = quick.querySelector('.precision-cutout-tool');
    if (cutout) {
      cutout.classList.add('precision-trial-local-card');
      var cutoutTitle = cutout.querySelector('#precisionCutoutTitle');
      var cutoutHeading = cutout.querySelector('.precision-cutout-heading');
      if (cutoutTitle) cutoutTitle.textContent = '一键抠图';
      if (cutoutHeading && cutoutHeading.dataset.trialBound !== 'true') {
        cutoutHeading.dataset.trialBound = 'true';
        cutoutHeading.setAttribute('role', 'button');
        cutoutHeading.setAttribute('tabindex', '0');
        cutoutHeading.setAttribute('aria-expanded', 'true');
        var toggleCutout = function () {
          var collapsed = cutout.classList.toggle('precision-trial-cutout-collapsed');
          cutoutHeading.setAttribute('aria-expanded', String(!collapsed));
        };
        cutoutHeading.addEventListener('click', function (event) {
          if (event.target.closest('.precision-help-trigger')) return;
          toggleCutout();
        });
        cutoutHeading.addEventListener('keydown', function (event) {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleCutout();
          }
        });
      }
    }
  }

  function refresh() {
    panel.classList.toggle('precision-ui-trial', enabled);
    var title = document.getElementById('precisionCutoutTitle');
    if (title && enabled) title.textContent = '一键抠图';
    toggle.textContent = enabled ? '实验界面 · 切回原版' : '原版界面 · 试用新版';
    projections.forEach(function (update) { update(); });
  }
  toggle.onclick = function () {
    enabled = !enabled;
    try { localStorage.setItem('genbox_precision_ui_trial', enabled ? 'on' : 'off'); } catch (_) {}
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
