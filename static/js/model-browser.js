(function () {
  'use strict';
  function text(zh, en) { return window.__genboxLanguage === 'en' ? en : zh; }
  function node(tag, className, label) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    if (label) el.textContent = label;
    return el;
  }
  function categories(model, provider) {
    var id = model.toLowerCase();
    var caps = getProviderModelCapabilityRecord(provider, model);
    var result = [];
    if (caps.image_generation !== false && (
      caps.image_generation === true || caps.t2i === true || caps.i2i === true ||
      /image|imagen|banana|flux|diffusion|seedream|dall-e|midjourney/.test(id))) result.push('image');
    if (caps.video_generation !== false && (caps.video_generation === true ||
      caps.t2v === true || caps.i2v === true ||
      /veo|^gemini-omni-|sora|kling|video|t2v|i2v|seedance|hailuo|wan2/.test(id))) result.push('video');
    if (/embed/.test(id)) result.push('embedding');
    if (/rerank/.test(id)) result.push('rerank');
    if (/tts|audio|lyria|whisper|transcri/.test(id)) result.push('audio');
    if (!result.length && /^(gemini|gpt-|o[1-9](?:-|$)|claude|qwen|deepseek|gemma|llama|mistral|grok|deep-research)/.test(id)) result.push('text');
    // Multimodal input is not evidence of image output.
    if (caps.multimodal === true || /vision/.test(id)) result.push('multimodal');
    return result.length ? result : ['other'];
  }
  function family(model) {
    var id = model.toLowerCase();
    if (/banana|^gemini-.*image/.test(id)) return 'Nano Banana';
    if (/^gemini/.test(id)) return 'Gemini';
    if (/imagen/.test(id)) return 'Imagen';
    if (/gpt.*image|dall-e/.test(id)) return 'GPT Image / DALL·E';
    var families = [
      [/^gpt|^o[1-9](?:-|$)/, 'GPT'], [/^gemma/, 'Gemma'], [/lyria/, 'Lyria'],
      [/flux/, 'FLUX'], [/qwen/, 'Qwen'], [/seedream|seedance|doubao/, 'Doubao'],
      [/veo/, 'Veo'], [/sora/, 'Sora'], [/kling/, 'Kling'], [/claude/, 'Claude'],
      [/deepseek/, 'DeepSeek'], [/antigravity/, 'Antigravity'], [/deep-research/, 'Deep Research']
    ];
    for (var i = 0; i < families.length; i++) if (families[i][0].test(id)) return families[i][1];
    return text('其他模型', 'Other models');
  }
  function categoryLabels() {
    return [
      ['all', text('全部', 'All')], ['image', text('图像', 'Image')],
      ['video', text('视频', 'Video')], ['text', text('文本', 'Text')],
      ['multimodal', text('多模态', 'Multimodal')], ['audio', text('音频', 'Audio')],
      ['embedding', text('嵌入', 'Embedding')], ['rerank', text('重排', 'Rerank')],
      ['other', text('其他', 'Other')]
    ];
  }
  var activeDialog;
  function open(select, trigger, provider, generation) {
    if (activeDialog) activeDialog.close();
    var dialog = node('dialog', 'model-browser-dialog');
    activeDialog = dialog;
    dialog.setAttribute('aria-label', text('选择模型', 'Choose a model'));
    var header = node('header', 'model-browser-header');
    header.appendChild(node('strong', '', (provider.name || 'Provider') + text(' · 模型', ' · Models')));
    var close = node('button', 'model-browser-close', '\u00d7');
    close.type = 'button';
    close.setAttribute('aria-label', text('关闭模型选择', 'Close model selection'));
    close.title = close.getAttribute('aria-label');
    close.onclick = function () { dialog.close(); };
    header.appendChild(close);
    var search = node('input', 'model-browser-search');
    search.type = 'search';
    search.placeholder = text('搜索模型名称或 ID', 'Search model name or ID');
    search.setAttribute('aria-label', search.placeholder);
    var tabs = node('div', 'model-browser-tabs');
    tabs.setAttribute('role', 'group');
    tabs.setAttribute('aria-label', text('模型类型筛选', 'Model type filters'));
    var list = node('div', 'model-browser-list');
    var status = node('div', 'model-browser-status');
    status.setAttribute('role', 'status');
    var selected = node('div', 'model-browser-current');
    selected.textContent = text('当前：', 'Current: ') + (select.value || text('未选择', 'None'));
    dialog.append(header, search, tabs, list, status, selected);
    var entries = Array.from(select.options).filter(function (option) {
      return option.value && !option.disabled;
    }).map(function (option) {
      return {id: option.value, label: generationModelDisplayName(option.value),
        family: family(option.value), categories: categories(option.value, provider)};
    });
    var category = 'all';
    var collapsed = new Set();
    var labels = categoryLabels();
    function renderTabs() {
      tabs.replaceChildren();
      labels.forEach(function (entry) {
        var count = entries.filter(function (item) { return entry[0] === 'all' || item.categories.indexOf(entry[0]) !== -1; }).length;
        if (generation && !count && entry[0] !== 'all') return;
        var button = node('button', '', entry[1]);
        button.type = 'button';
        button.dataset.category = entry[0];
        button.setAttribute('aria-pressed', String(category === entry[0]));
        button.disabled = !count;
        button.appendChild(node('span', 'model-browser-count', String(count)));
        button.onclick = function () { category = entry[0]; renderTabs(); renderList(); };
        tabs.appendChild(button);
      });
    }
    function renderList() {
      list.replaceChildren();
      var query = search.value.trim().toLowerCase();
      var matches = entries.filter(function (item) {
        return (category === 'all' || item.categories.indexOf(category) !== -1) &&
          (!query || (item.id + ' ' + item.label + ' ' + item.family).toLowerCase().indexOf(query) !== -1);
      });
      var groups = new Map();
      matches.forEach(function (item) {
        if (!groups.has(item.family)) groups.set(item.family, []);
        groups.get(item.family).push(item);
      });
      groups.forEach(function (items, group) {
        var details = node('details', 'model-browser-group');
        details.open = !!query || !collapsed.has(group);
        var summary = node('summary');
        summary.append(node('strong', '', group), node('span', 'model-browser-count', String(items.length)));
        details.appendChild(summary);
        details.ontoggle = function () {
          if (!details.isConnected || query) return;
          if (details.open) collapsed.delete(group); else collapsed.add(group);
        };
        items.forEach(function (item) {
          var row = node('button', 'model-browser-row');
          row.type = 'button';
          row.dataset.model = item.id;
          row.setAttribute('aria-pressed', String(select.value === item.id));
          var copy = node('span', 'model-browser-copy');
          copy.appendChild(node('strong', '', item.label));
          if (item.label !== item.id) copy.appendChild(node('small', '', item.id));
          var badge = node('span', 'model-browser-badge', labels.find(function (entry) { return entry[0] === item.categories[0]; })[1]);
          row.append(copy, badge, node('span', 'model-browser-check', select.value === item.id ? '\u2713' : ''));
          row.onclick = function () {
            if (!select.isConnected || select.disabled) { dialog.close(); return; }
            // Keep the original select and change handler as the submission source.
            select.value = item.id;
            select.dispatchEvent(new Event('change', {bubbles: true}));
            dialog.close();
          };
          details.appendChild(row);
        });
        list.appendChild(details);
      });
      status.textContent = matches.length ? text('显示 ', 'Showing ') + matches.length + ' / ' + entries.length :
        text('没有匹配的模型', 'No matching models');
      list.scrollTop = 0;
    }
    search.oninput = renderList;
    dialog.addEventListener('click', function (event) {
      if (event.target !== dialog) return;
      var rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', function () {
      dialog.remove();
      if (activeDialog === dialog) activeDialog = null;
      if (trigger.isConnected) trigger.focus();
    });
    renderTabs();
    renderList();
    document.body.appendChild(dialog);
    dialog.showModal();
    search.focus();
  }
  function mount(root) {
    root.querySelectorAll('select[data-generation-provider], select[id^="model_"]').forEach(function (select) {
      if (select.dataset.browserReady) return;
      var generation = select.hasAttribute('data-generation-provider');
      var provider = generation ? findProvider(select.dataset.generationProvider) : allProviders[Number(select.id.slice(6))];
      if (!provider) return;
      select.dataset.browserReady = 'true';
      var trigger = node('button', 'model-browser-trigger');
      trigger.type = 'button';
      trigger.setAttribute('aria-haspopup', 'dialog');
      trigger.setAttribute('aria-label', (provider.name || 'Provider') + text('：选择模型', ': Choose model'));
      function sync() {
        trigger.replaceChildren(node('span', '', generationModelDisplayName(select.value) || text('选择模型', 'Choose model')),
          node('span', 'model-browser-caret', '\u2304'));
        trigger.title = select.value;
        trigger.disabled = select.disabled;
      }
      sync();
      select.addEventListener('change', sync);
      // Native selects remain available to existing code; only their view changes.
      select.hidden = true;
      select.after(trigger);
      var legacyFilters = select.parentElement.parentElement.querySelector('.provider-model-filter');
      if (legacyFilters) legacyFilters.hidden = true;
      trigger.onclick = function (event) {
        event.stopPropagation();
        open(select, trigger, findProvider(provider.id) || provider, generation);
      };
    });
  }
  window.genboxModelBrowser = {mount: mount};
  mount(document);
})();
