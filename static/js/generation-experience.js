(function () {
  'use strict';
  function text(zh, en) { return window.__genboxLanguage === 'en' ? en : zh; }
  function element(tag, className, label) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (label) node.textContent = label;
    return node;
  }
  var notified = new Set();
  function notice(kind, title, description) {
    var stack = document.getElementById('generationNotifications');
    if (!stack) {
      stack = element('section', 'generation-notifications');
      stack.id = 'generationNotifications';
      stack.setAttribute('aria-label', text('生图通知', 'Generation notifications'));
      document.body.appendChild(stack);
    }
    var card = element('article', 'generation-notice ' + kind);
    card.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    var content = element('div');
    content.appendChild(element('strong', '', title));
    content.appendChild(element('p', '', description));
    var close = element('button', 'generation-notice-close', '\u00d7');
    close.type = 'button';
    close.setAttribute('aria-label', text('关闭通知', 'Dismiss notification'));
    close.title = close.getAttribute('aria-label');
    var timer;
    function dismiss() { clearTimeout(timer); card.remove(); }
    close.onclick = dismiss;
    card.append(content, close);
    stack.appendChild(card);
    while (stack.children.length > 3) stack.firstElementChild.remove();
    // Errors remain until dismissed; successful notices pause while inspected.
    function schedule() { if (kind === 'success') timer = setTimeout(dismiss, 8000); }
    card.onmouseenter = card.onfocusin = function () { clearTimeout(timer); };
    card.onmouseleave = card.onfocusout = schedule;
    schedule();
  }
  function progress(states) {
    Object.keys(states || {}).forEach(function (key) {
      var card = document.getElementById('prev_ph_' + key);
      var holder = card && card.querySelector('.prev-placeholder');
      if (!holder || card.classList.contains('failed')) return;
      var status = String(states[key].status || 'queued');
      var terminal = ['completed', 'failed', 'cancelled'].indexOf(status) !== -1;
      if (!holder.classList.contains('generation-placeholder')) {
        holder.classList.add('generation-placeholder');
        holder.replaceChildren();
        var bar = element('div', 'generation-placeholder-track');
        bar.setAttribute('role', 'progressbar');
        bar.setAttribute('aria-label', text('图片生成进度', 'Image generation progress'));
        bar.appendChild(element('span'));
        holder.append(bar, element('div', 'generation-placeholder-label'));
      }
      var label = status === 'completed' ? text('生成完成', 'Generated') :
        status === 'failed' ? text('生成失败', 'Generation failed') :
        status === 'cancelled' ? text('已取消', 'Cancelled') :
        status === 'queued' ? text('排队中', 'Queued') : text('生成中', 'Generating');
      holder.dataset.state = status;
      holder.setAttribute('aria-busy', String(!terminal));
      holder.querySelector('.generation-placeholder-label').textContent = label;
      var track = holder.querySelector('[role="progressbar"]');
      track.setAttribute('aria-valuetext', label);
      var badge = card.querySelector('.elapsed-badge');
      if (badge) badge.textContent = label;
      // The server's elapsed-time estimate is not upstream progress.
      track.removeAttribute('aria-valuenow');
      if (terminal) {
        card.classList.remove('generating');
        var elapsed = card.querySelector('.elapsed-badge');
        if (elapsed) elapsed.textContent = label;
      }
    });
  }
  window.genboxGenerationUX = {
    progress: progress,
    submissionFailed: function () {
      notice('error', text('提交失败', 'Submission failed'),
        text('任务未能提交，请查看任务状态。', 'The task could not be submitted. Check task status.'));
    },
    finish: function (data, taskId) {
      if (!taskId || notified.has(taskId)) return;
      notified.add(taskId);
      if (notified.size > 100) notified.delete(notified.values().next().value);
      var states = data.provider_states || {};
      var settled = {};
      Object.keys(states).forEach(function (key) {
        settled[key] = {status: ['completed', 'failed', 'cancelled'].indexOf(states[key].status) !== -1
          ? states[key].status : data.status};
      });
      // Include placeholders when a terminal error has no per-provider payload.
      document.querySelectorAll('[id^="prev_ph_"]').forEach(function (card) {
        var key = card.id.slice(8);
        if (!settled[key]) settled[key] = {status: data.status};
      });
      progress(settled);
      var results = Object.values(data.results || {});
      var ok = results.filter(function (item) { return item && item.success; }).length;
      var total = Math.max(Object.keys(states).length, results.length);
      var kind = data.status === 'cancelled' ? 'info' :
        data.status === 'failed' || !ok ? 'error' : ok < total ? 'warning' : 'success';
      var title = kind === 'info' ? text('生成已取消', 'Generation cancelled') :
        kind === 'error' ? text('生成失败', 'Generation failed') :
        kind === 'warning' ? text('部分生成完成', 'Partially completed') : text('生成完成', 'Generation complete');
      notice(kind, title, text('成功 ', 'Successful: ') + ok + ' / ' + total);
    }
  };

  window.genboxProviderSteps = function (body) {
    var stepState = window.__genboxProviderStepState || (window.__genboxProviderStepState = {});
    body.querySelectorAll('input[id^="name_"]').forEach(function (name) {
      var idx = name.id.slice(5);
      var form = name.parentElement.parentElement;
      if (form.dataset.stepsReady) return;
      form.dataset.stepsReady = 'true';
      form.classList.add('provider-guided-form');
      var stableIdInput = form.querySelector('#id_' + idx);
      var stableId = stableIdInput && stableIdInput.value ? stableIdInput.value : ('index:' + idx);
      var rows = Array.from(form.children);
      var nav = element('nav', 'provider-steps');
      nav.setAttribute('aria-label', text('模型配置步骤', 'Provider setup steps'));
      var labels = [text('接入配置', 'Connection'), text('选择模型', 'Models'), text('保存', 'Save')];
      var panels = labels.map(function () { return element('section', 'provider-step-panel'); });
      rows.forEach(function (row) {
        var target = row.querySelector('#model_' + idx) || row.id === 'capsSection_' + idx ? 1 :
          row.querySelector('#en_' + idx) ? 2 : 0;
        panels[target].appendChild(row);
      });
      var advanced = element('details', 'provider-step-advanced');
      advanced.appendChild(element('summary', '', text('高级接入设置', 'Advanced connection settings')));
      Array.from(panels[0].children).forEach(function (row) {
        if (row.querySelector('#keys_' + idx) || row.querySelector('#epList_' + idx) ||
            row.querySelector('#display_name_' + idx) || row.querySelector('#id_' + idx) ||
            row.querySelector('#skip_proxy_' + idx)) advanced.appendChild(row);
      });
      panels[0].appendChild(advanced);
      var current = Number.isFinite(stepState[stableId]) ? stepState[stableId] : 0;
      var previous = element('button', 'btn-secondary', text('上一步', 'Previous'));
      var next = element('button', 'btn-primary', text('下一步', 'Next'));
      previous.type = next.type = 'button';
      function select(step) {
        current = step;
        stepState[stableId] = step;
        panels.forEach(function (panel, i) { panel.hidden = i !== step; });
        Array.from(nav.children).forEach(function (button, i) {
          if (i === step) button.setAttribute('aria-current', 'step');
          else button.removeAttribute('aria-current');
        });
        previous.disabled = step === 0;
        next.hidden = step === 2;
      }
      labels.forEach(function (label, i) {
        var button = element('button', '', (i + 1) + '  ' + label);
        button.type = 'button';
        button.setAttribute('aria-controls', 'provider-step-' + idx + '-' + i);
        panels[i].id = 'provider-step-' + idx + '-' + i;
        panels[i].setAttribute('aria-label', label);
        button.onclick = function () { select(i); };
        nav.appendChild(button);
      });
      previous.onclick = function () { select(Math.max(0, current - 1)); };
      next.onclick = function () { select(Math.min(2, current + 1)); };
      var presets = element('label', 'provider-preset-field', text('接入预设', 'Connection preset'));
      var dropdown = element('select', 'modal-input');
      dropdown.setAttribute('aria-label', presets.textContent);
      [
        ['', text('保留当前配置', 'Keep current configuration')],
        ['google', 'Google Gemini API'],
        ['openai', 'OpenAI API'],
        ['custom', text('OpenAI 兼容中转', 'OpenAI-compatible gateway')]
      ].forEach(function (entry) { dropdown.add(new Option(entry[1], entry[0])); });
      var configs = {
        google: {url: 'https://generativelanguage.googleapis.com', protocol: 'gemini'},
        openai: {url: 'https://api.openai.com/v1', protocol: 'openai'}
      };
      dropdown.onchange = function () {
        if (!dropdown.value) return;
        var url = document.getElementById('url_' + idx);
        var protocol = document.getElementById('endpoint_type_' + idx);
        var chosen = configs[dropdown.value];
        // No preset is saved or tested here. Never silently redirect a saved key.
        if (!window.confirm(text('更改接入预设？请核对地址和对应密钥后再保存。', 'Change connection preset? Check the address and matching key before saving.'))) {
          dropdown.value = '';
          return;
        }
        if (chosen) url.value = chosen.url;
        protocol.value = chosen ? chosen.protocol : 'openai';
        var hint = form.querySelector('.provider-auto-protocol-hint');
        if (hint) hint.hidden = true;
        url.dispatchEvent(new Event('input', {bubbles: true}));
        protocol.dispatchEvent(new Event('change', {bubbles: true}));
        if (!chosen) url.focus();
      };
      presets.appendChild(dropdown);
      panels[0].prepend(presets);
      var footer = element('div', 'provider-step-navigation');
      footer.append(previous, next);
      form.append(nav, panels[0], panels[1], panels[2], footer);
      select(current);
    });
  };
})();
