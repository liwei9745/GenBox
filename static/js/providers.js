(function(){
'use strict';

function _af(url, opts) { return window._authFetch(url, opts); }
function _eh(s) { return window.escHtml(s); }
function _ea(s) { return window.escAttr(s); }

/* ═══════════════════════════════════════════════════════════════════
   Provider Loading & Rendering
   ═══════════════════════════════════════════════════════════════════ */
window.loadProviders = function() {
  return _af('/api/providers').then(function(r){ return r.json(); }).then(function(data){
    window.allProviders = data.providers || [];
    window.loadProviderOrder();
    window.renderProviderList();
    window.loadModelDropdown();
    window.setStatus('Provider \u5DF2\u52A0\u8F7D \u00B7 ' + window.allProviders.filter(function(p){return p.type==='image';}).length + ' \u4E2A\u751F\u56FE\u6A21\u578B');
  }).catch(function(e){ if (e.message !== 'AUTH_REQUIRED') window.setStatus('Provider \u52A0\u8F7D\u5931\u8D25'); });
};

window.onImageModelChange = function(pid, newModel) {
  for (var i = 0; i < window.allProviders.length; i++) {
    if (window.allProviders[i].id === pid) {
      window.allProviders[i].model = newModel;
      break;
    }
  }
};

window.renderProviderList = function() {
  var container = document.getElementById('providerList');
  var html = '';
  var imageProviders = window.allProviders.filter(function(p){ return p.type === 'image'; });

  for (var i = 0; i < imageProviders.length; i++) {
    (function(p, idx){
      var sel = window.selectedProviders.indexOf(p.id) !== -1;
      var configured = p.api_key || p.has_key;
      var disabled = !p.enabled || !configured;

      var allModels = p.models && p.models.length > 0 ? p.models : (p.model ? [p.model] : []);
      var filteredModels = window.filterModelsByType(allModels, 'image');
      if (filteredModels.length === 0) filteredModels = allModels;
      var modelOpts = filteredModels.length > 3
        ? window.buildModelOptsGrouped(filteredModels, p.model || '', window.groupImageModels)
        : filteredModels.map(function(m){ return '<option value="' + _ea(m) + '"' + (p.model===m?' selected':'') + '>' + _eh(m) + '</option>'; }).join('');

      html += '<div class="provider-card ' + (sel ? 'selected' : '') + ' ' + (disabled ? 'disabled' : '') + '" ' +
              'draggable="' + (!disabled) + '" ' +
              'ondragstart="onProviderDragStart(event, \'' + p.id + '\', ' + idx + ')" ' +
              'ondragover="onProviderDragOver(event, \'' + p.id + '\')" ' +
              'ondrop="onProviderDrop(event, \'' + p.id + '\')" ' +
              'ondragend="resetDragStyle()" ' +
              'onclick="' + (disabled ? '' : 'toggleProvider(\'' + p.id + '\')') + '" data-id="' + p.id + '">' +
        '<div class="provider-dot" style="background:' + (p.color || '#5b8def') + ';"></div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div class="provider-name">' + _eh(p.name) + '</div>' +
        '</div>' +
        '<div class="provider-check"></div>' +
      '</div>' +
      '<div style="padding:2px 0 6px 22px;">' +
        '<select onchange="onImageModelChange(\'' + p.id + '\', this.value)" ' + (!sel ? 'disabled' : '') + ' style="width:100%;font-size:11px;padding:4px 8px;background:var(--bg-base);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);' + (!sel ? 'opacity:0.5;' : '') + '">' +
          (modelOpts || '<option value="">\u65E0\u53EF\u7528\u6A21\u578B</option>') +
        '</select>' +
      '</div>';
    })(imageProviders[i], i);
  }

  container.innerHTML = html || '<div style="color:var(--text-muted);font-size:12px;padding:8px 0;">\u6682\u65E0\u6A21\u578B\uFF0C<a href="#" onclick="openProviderModal();return false;" style="color:var(--accent);">\u53BB\u6DFB\u52A0</a></div>';
  window.updateSelCount();
};

window.buildRatioBtns = function(pid, activeRatio) {
  var ratios = [
    ['1:1','1:1'], ['2:3','2:3'], ['3:2','3:2'], ['3:4','3:4'], ['4:3','4:3'],
    ['9:16','9:16'], ['16:9','16:9'], ['21:9','21:9'],
    ['auto','auto']
  ];
  var html = '';
  for (var i = 0; i < ratios.length; i++) {
    var r = ratios[i][0];
    var label = ratios[i][1];
    var isActive = r === activeRatio;
    html += '<button class="pratio-btn ' + (isActive ? 'active' : '') + '" ' +
            'onclick="event.stopPropagation();setProviderRatio(\'' + pid + '\',\'' + r + '\',this)" ' +
            'title="' + r + '">' + label + '</button>';
  }
  return html;
};

window.setProviderRatio = function(pid, ratio, el) {
  el.parentElement.querySelectorAll('.pratio-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  if (ratio !== 'auto' && window.RATIO_SIZES[ratio]) {
    var sz = window.RATIO_SIZES[ratio];
    document.getElementById('pw_' + pid).value = sz[0];
    document.getElementById('ph_' + pid).value = sz[1];
  }
  window.saveProviderSetting(pid, 'ratio', ratio);
};

window.setProviderQuality = function(pid, val, el) {
  el.parentElement.querySelectorAll('.pquality-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  window.saveProviderSetting(pid, 'quality', val);
};

window.adjustProviderQty = function(pid, delta) {
  var el = document.getElementById('pqty_' + pid);
  var v = parseInt(el.textContent) || 1;
  v = Math.max(1, Math.min(10, v + delta));
  el.textContent = v;
  window.providerQuantities[pid] = v;
  window.saveProviderSetting(pid, 'qty', v);
};

window.onProviderSizeChange = function(pid) {
  var w = parseInt(document.getElementById('pw_' + pid).value) || 1024;
  var h = parseInt(document.getElementById('ph_' + pid).value) || 1024;
  window.saveProviderSetting(pid, 'w', w);
  window.saveProviderSetting(pid, 'h', h);
  var matched = '';
  for (var ratio in window.RATIO_SIZES) {
    var sz = window.RATIO_SIZES[ratio];
    if (sz[0] === w && sz[1] === h) { matched = ratio; break; }
  }
  var ratioBtns = document.getElementById('pratio_' + pid);
  if (ratioBtns) {
    ratioBtns.querySelectorAll('.pratio-btn').forEach(function(b){
      b.classList.toggle('active', b.title === matched);
    });
  }
  window.saveProviderSetting(pid, 'ratio', matched);
};

/* ═══════════════════════════════════════════════════════════════════
   Per-Provider Settings Persistence
   ═══════════════════════════════════════════════════════════════════ */
window.loadProviderSettings = function() {
  try {
    return JSON.parse(localStorage.getItem('genbox_provider_settings') || '{}');
  } catch(e) { return {}; }
};

window.saveProviderSetting = function(pid, key, val) {
  var all = window.loadProviderSettings();
  if (!all[pid]) all[pid] = {};
  all[pid][key] = val;
  try { localStorage.setItem('genbox_provider_settings', JSON.stringify(all)); } catch(e) {}
};

window.saveAllProviderSettings = function() {
  var imageProviders = window.allProviders.filter(function(p){ return p.type === 'image'; });
  var all = window.loadProviderSettings();
  for (var i = 0; i < imageProviders.length; i++) {
    var p = imageProviders[i];
    if (!all[p.id]) all[p.id] = {};
    var wEl = document.getElementById('pw_' + p.id);
    var hEl = document.getElementById('ph_' + p.id);
    var qEl = document.getElementById('pqty_' + p.id);
    if (wEl) all[p.id].w = parseInt(wEl.value) || 1024;
    if (hEl) all[p.id].h = parseInt(hEl.value) || 1024;
    if (qEl) all[p.id].qty = parseInt(qEl.textContent) || 1;
    var qCard = document.querySelector('.provider-card[data-id="' + p.id + '"]');
    if (qCard) {
      var qBtn = qCard.querySelector('.pquality-btn.active');
      if (qBtn) all[p.id].quality = qBtn.title === '\u81EA\u52A8' ? '' : qBtn.title === '\u4F4E' ? 'low' : qBtn.title === '\u4E2D' ? 'medium' : 'high';
      var rBtn = qCard.querySelector('.pratio-btn.active');
      if (rBtn) all[p.id].ratio = rBtn.title;
    }
  }
  try {
    localStorage.setItem('genbox_provider_settings', JSON.stringify(all));
    window.setStatus('\u2705 \u6A21\u578B\u8BBE\u7F6E\u5DF2\u4FDD\u5B58');
  } catch(e) { window.setStatus('\u274C \u4FDD\u5B58\u5931\u8D25'); }
};

/* ═══════════════════════════════════════════════════════════════════
   Provider Drag Sort
   ═══════════════════════════════════════════════════════════════════ */
var dragProviderId = null;
var dragProviderOriginalIndex = null;

window.onProviderDragStart = function(e, pid, idx) {
  dragProviderId = pid;
  dragProviderOriginalIndex = idx;
  e.dataTransfer.effectAllowed = 'move';
  var card = document.querySelector('.provider-card[data-id="' + pid + '"]');
  if (card) card.classList.add('dragging');
};

window.onProviderDragOver = function(e, pid) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  var card = document.querySelector('.provider-card[data-id="' + pid + '"]');
  if (card) card.classList.add('drag-over');
};

window.onProviderDrop = function(e, pid) {
  e.preventDefault();
  if (!dragProviderId || dragProviderId === pid) return;
  var imageProviders = window.allProviders.filter(function(p){ return p.type === 'image'; });
  var fromIdx = imageProviders.findIndex(function(p){ return p.id === dragProviderId; });
  var toIdx = imageProviders.findIndex(function(p){ return p.id === pid; });
  if (fromIdx < 0 || toIdx < 0) return;
  var item = imageProviders.splice(fromIdx, 1)[0];
  imageProviders.splice(toIdx, 0, item);
  var allFromIdx = window.allProviders.findIndex(function(p){ return p.id === dragProviderId && p.type === 'image'; });
  var allToIdx = window.allProviders.findIndex(function(p){ return p.id === pid && p.type === 'image'; });
  if (allFromIdx >= 0 && allToIdx >= 0) {
    var allItem = window.allProviders.splice(allFromIdx, 1)[0];
    window.allProviders.splice(allToIdx, 0, allItem);
  }
  var selFrom = window.selectedProviders.indexOf(dragProviderId);
  var selTo = window.selectedProviders.indexOf(pid);
  if (selFrom >= 0 && selTo >= 0) {
    window.selectedProviders.splice(selFrom, 1);
    window.selectedProviders.splice(selTo, 0, dragProviderId);
  }
  window.saveProviderOrder();
  window.renderProviderList();
};

window.resetDragStyle = function() {
  dragProviderId = null;
  dragProviderOriginalIndex = null;
  document.querySelectorAll('.dragging, .drag-over').forEach(function(el){ el.classList.remove('dragging', 'drag-over'); });
};

window.saveProviderOrder = function() {
  try {
    var imageProviders = window.allProviders.filter(function(p){ return p.type === 'image'; });
    localStorage.setItem('providerOrder', JSON.stringify(imageProviders.map(function(p){ return p.id; })));
  } catch(e) {}
};

window.loadProviderOrder = function() {
  try {
    var saved = localStorage.getItem('providerOrder');
    if (!saved) return;
    var order = JSON.parse(saved);
    var imageProviders = window.allProviders.filter(function(p){ return p.type === 'image'; });
    var reordered = [];
    order.forEach(function(id) {
      var p = imageProviders.find(function(x){ return x.id === id; });
      if (p) reordered.push(p);
    });
    imageProviders.forEach(function(p) {
      if (reordered.indexOf(p) === -1) reordered.push(p);
    });
    for (var i = 0; i < window.allProviders.length; i++) {
      if (window.allProviders[i].type === 'image') {
        window.allProviders[i] = reordered.shift() || window.allProviders[i];
      }
    }
  } catch(e) {}
};

window.toggleProvider = function(id) {
  var idx = window.selectedProviders.indexOf(id);
  if (idx !== -1) window.selectedProviders.splice(idx, 1);
  else window.selectedProviders.push(id);
  window.renderProviderList();
};

window.updateSelCount = function() {
  document.getElementById('selCountBadge').textContent = window.selectedProviders.length;
};

/* ═══════════════════════════════════════════════════════════════════
   Provider Edit
   ═══════════════════════════════════════════════════════════════════ */
window.providerEditOpenIdx = -1;

window.toggleProviderEdit = function(idx) {
  window.providerEditOpenIdx = window.providerEditOpenIdx === idx ? -1 : idx;
  window.renderProviderEdit();
};

window.renderProviderEdit = function() {
  var body = document.getElementById('providerEditBody');
  var html = '';
  var pIdx = window.providerEditOpenIdx;

  html += '<div id="proxySection" style="margin-bottom:14px;padding:12px;border-radius:10px;border:1px solid var(--border);background:var(--bg-surface);">';
  html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">';
  html += '<div style="display:flex;align-items:center;gap:6px;">';
  html += '<span style="font-size:13px;">\u{1F310}</span>';
  html += '<span style="font-size:12px;font-weight:700;color:var(--text-primary);">\u7F51\u7EDC\u4EE3\u7406</span>';
  html += '<span id="proxyStatusBadge" style="font-size:9px;padding:2px 6px;border-radius:8px;background:#6b728022;color:#6b7280;font-weight:600;">\u672A\u914D\u7F6E</span>';
  html += '</div>';
  html += '<span style="font-size:10px;color:var(--text-muted);">\u7528\u4E8E\u8FDE\u63A5\u56FD\u5916\u6A21\u578B\u5382\u5546\uFF08OpenAI\u3001Gemini \u7B49\uFF09</span>';
  html += '</div>';
  html += '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">';
  html += '<label style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-secondary);cursor:pointer;">';
  html += '<input type="checkbox" id="proxyEnabled" style="accent-color:var(--accent);width:14px;height:14px;"> \u542F\u7528\u4EE3\u7406';
  html += '</label>';
  html += '<select id="proxyType" style="padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<option value="http">HTTP</option>';
  html += '<option value="socks5">SOCKS5</option>';
  html += '</select>';
  html += '<input type="text" id="proxyHost" placeholder="\u4E3B\u673A IP" style="width:120px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);" value="127.0.0.1">';
  html += '<input type="number" id="proxyPort" placeholder="\u7AEF\u53E3" style="width:70px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);" value="10808">';
  html += '<input type="text" id="proxyUser" placeholder="\u7528\u6237\u540D(\u53EF\u9009)" style="width:100px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<input type="password" id="proxyPass" placeholder="\u5BC6\u7801(\u53EF\u9009)" style="width:100px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<button onclick="saveProxyConfig()" style="padding:5px 12px;font-size:11px;border-radius:6px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;">\u4FDD\u5B58</button>';
  html += '<button onclick="testProxyConfig()" id="proxyTestBtn" style="padding:5px 12px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">\u6D4B\u8BD5\u8FDE\u63A5</button>';
  html += '</div>';
  html += '<div id="proxyTestResult" style="font-size:10px;margin-top:6px;"></div>';
  html += '</div>';

  window._loadProxyConfig();

  var groups = [
    { type: 'image', icon: '\u{1F3A8}', title: '\u751F\u56FE\u6A21\u578B', hint: '\u7528\u4E8E\u751F\u6210\u56FE\u7247\u7684\u6A21\u578B\uFF0C\u5982 Stable Diffusion\u3001Midjourney\u3001Flux \u7B49', accent: '#22c55e' },
    { type: 'video', icon: '\u{1F3AC}', title: '\u751F\u89C6\u9891\u6A21\u578B', hint: '\u7528\u4E8E\u751F\u6210\u89C6\u9891\u7684\u6A21\u578B\uFF0C\u5982 Gemini Veo\u3001Sora \u7B49', accent: '#3b82f6' },
    { type: 'llm', icon: '\u{1F916}', title: '\u63D0\u793A\u8BCD\u4F18\u5316', hint: '\u7528\u4E8E\u4F18\u5316\u63D0\u793A\u8BCD\u7684\u5927\u8BED\u8A00\u6A21\u578B\uFF0C\u5982 GPT-4o\u3001Claude \u7B49', accent: '#f59e0b' },
  ];

  html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;min-height:420px;">';

  groups.forEach(function(group) {
    var provsInGroup = window.allProviders.filter(function(p){ return p.type === group.type; });

    html += '<div style="display:flex;flex-direction:column;border:1px solid var(--border);border-radius:12px;background:var(--bg-surface);overflow:hidden;">' +
      '<div style="padding:12px 14px;border-bottom:1px solid var(--border);background:var(--bg-card);display:flex;align-items:center;justify-content:space-between;">' +
        '<div style="display:flex;align-items:center;gap:8px;">' +
          '<span style="font-size:15px;">' + group.icon + '</span>' +
          '<span style="font-size:13px;font-weight:700;color:var(--text-primary);">' + group.title + '</span>' +
          '<span style="font-size:10px;padding:2px 6px;border-radius:8px;background:' + group.accent + '22;color:' + group.accent + ';font-weight:600;">' + provsInGroup.length + '</span>' +
        '</div>' +
        '<div style="font-size:10px;color:var(--text-muted);max-width:180px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="' + group.hint + '">' + group.hint + '</div>' +
      '</div>' +
      '<div style="flex:1;overflow-y:auto;max-height:520px;padding:8px;">';

    if (provsInGroup.length === 0) {
      html += '<div style="text-align:center;padding:30px 10px;color:var(--text-muted);font-size:12px;">' +
        '<div style="font-size:24px;margin-bottom:8px;">' + group.icon + '</div>' +
        '\u6682\u65E0' + group.title + '<br><span style="font-size:11px;color:var(--text-muted);">\u70B9\u51FB\u4E0B\u65B9\u6DFB\u52A0</span>' +
      '</div>';
    }

    provsInGroup.forEach(function(p) {
      var idx = window.allProviders.indexOf(p);
      var isOpen = pIdx === idx;
      var modelOpts = '';
      if (p.models && p.models.length) {
        var filteredModels = window.filterModelsByType(p.models, p.type);
        var groupFn = p.type === 'video' ? window.groupVideoModels : (p.type === 'image' ? window.groupImageModels : null);
        modelOpts = (groupFn && filteredModels.length > 3)
          ? window.buildModelOptsGrouped(filteredModels, p.model || '', groupFn)
          : filteredModels.map(function(m){ return '<option value="' + _ea(m) + '"' + (p.model===m?' selected':'') + '>' + _eh(m) + '</option>'; }).join('');
        if (filteredModels.length === 0 && p.models.length > 0) {
          modelOpts = '<option value="" disabled>\u65E0\u5339\u914D\u5F53\u524D\u7C7B\u578B\u7684\u6A21\u578B (\u5171' + p.models.length + '\u4E2A)</option>';
        }
      } else {
        modelOpts = '<option value="" disabled>\u8BF7\u5148\u62C9\u53D6\u6A21\u578B</option>';
        if (p.model) modelOpts = '<option value="' + _ea(p.model) + '" selected>' + _eh(p.model) + ' (\u624B\u52A8)</option>' + modelOpts;
      }
      var keyVal = p.api_key_masked || '';
      var keyPlaceholder = p.has_key ? (keyVal || '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (\u5DF2\u914D\u7F6E)') : '\u7559\u7A7A\u4F7F\u7528 .env \u6216\u624B\u52A8\u8F93\u5165';
      var statusColor = p.enabled ? '#22c55e' : '#6b7280';
      var statusTitle = p.enabled ? '\u5DF2\u542F\u7528' : '\u5DF2\u7981\u7528';

      html += '<div style="margin-bottom:8px;border:1px solid ' + (isOpen ? group.accent : 'var(--border)') + ';border-radius:8px;background:var(--bg-card);overflow:hidden;transition:border-color 0.2s;">' +
        '<div style="display:flex;align-items:center;padding:10px 12px;cursor:pointer;gap:8px;" onclick="toggleProviderEdit(' + idx + ')">' +
          '<input type="color" class="color-dot" value="' + (p.color||'#5b8def') + '" id="color_' + idx + '" onclick="event.stopPropagation();" style="width:22px;height:22px;border-radius:6px;border:none;cursor:pointer;flex-shrink:0;">' +
          '<div style="flex:1;min-width:0;">' +
            '<div style="display:flex;align-items:center;gap:6px;">' +
              '<span style="font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + _eh(p.name) + '</span>' +
              '<span style="width:5px;height:5px;border-radius:50%;background:' + statusColor + ';flex-shrink:0;" title="' + statusTitle + '"></span>' +
              (p.key_count > 1 ? '<span style="font-size:9px;padding:1px 5px;border-radius:6px;background:#3b82f622;color:#3b82f6;font-weight:600;flex-shrink:0;" title="' + p.key_count + ' \u4E2A API Key \u8F6E\u8BE2">\u{1F511}\u00D7' + p.key_count + '</span>' : '') +
            '</div>' +
            '<div style="font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
              _eh(p.model || '\u672A\u9009\u6A21\u578B') + (p.base_url ? ' \u00B7 ' + _eh(p.base_url.replace(/^https?:\/\//, '').substring(0, 30)) : '') +
            '</div>' +
          '</div>' +
          '<div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">' +
            '<button onclick="event.stopPropagation();testProvider(\'' + p.id + '\')" style="font-size:9px;padding:3px 8px;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-secondary);cursor:pointer;white-space:nowrap;">\u6D4B\u8BD5</button>' +
            '<button onclick="event.stopPropagation();deleteProvider(\'' + p.id + '\')" style="font-size:9px;padding:3px 8px;border-radius:4px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;white-space:nowrap;">\u5220\u9664</button>' +
            '<span style="font-size:10px;color:var(--text-muted);transition:transform 0.2s;display:inline-block;transform:rotate(' + (isOpen ? '90' : '0') + 'deg);">\u25B6</span>' +
          '</div>' +
        '</div>';

      if (isOpen) {
        html += '<div style="padding:0 12px 12px;border-top:1px solid var(--border);">' +
          '<div style="padding-top:10px;">' +
            '<div style="display:flex;gap:6px;margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="\u663E\u793A\u540D\u79F0" value="' + _eh(p.name) + '" id="name_' + idx + '">' +
              '<select class="modal-input" style="width:88px;padding:6px 8px;font-size:11px;" id="type_' + idx + '">' +
                '<option value="image" ' + (p.type==='image'?'selected':'') + '>\u{1F3A8} \u751F\u56FE</option>' +
                '<option value="video" ' + (p.type==='video'?'selected':'') + '>\u{1F3AC} \u751F\u89C6\u9891</option>' +
                '<option value="llm" ' + (p.type==='llm'?'selected':'') + '>\u{1F916} LLM</option>' +
              '</select>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">' +
              '<span style="font-size:10px;color:var(--text-muted);white-space:nowrap;">\u770B\u677F\u540D</span>' +
              '<input type="text" class="modal-input" style="flex:1;padding:5px 8px;font-size:11px;" placeholder="\u7559\u7A7A\u4F7F\u7528\u4E0A\u65B9\u540D\u79F0" value="' + _eh(p.display_name || '') + '" id="display_name_' + idx + '">' +
            '</div>' +
            '<div style="margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="width:100%;padding:6px 10px;font-size:11px;box-sizing:border-box;" placeholder="Provider ID (\u552F\u4E00\u6807\u8BC6)" value="' + _eh(p.id) + '" id="id_' + idx + '" ' + (p.id?'readonly style="padding:6px 10px;font-size:11px;background:var(--bg-surface);box-sizing:border-box;"':'') + '>' +
            '</div>' +
            '<div style="display:flex;gap:6px;margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="Base URL" value="' + _eh(p.base_url) + '" id="url_' + idx + '">' +
              '<input type="password" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="' + keyPlaceholder + '" value="' + _eh(keyVal) + '" id="key_' + idx + '">' +
            '</div>' +
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">\u{1F504} \u591A\u8D26\u53F7\u8F6E\u8BE2\uFF08\u53EF\u9009\uFF0C\u6BCF\u884C\u4E00\u4E2A Key\uFF09</span>' +
                (p.keypool ? '<span style="font-size:9px;padding:2px 6px;border-radius:8px;background:' + (p.keypool.available_keys > 0 ? '#22c55e22;color:#22c55e' : '#ef444422;color:#ef4444') + ';font-weight:600;">' + p.keypool.available_keys + '/' + p.keypool.total_keys + ' \u53EF\u7528</span>' : '') +
              '</div>' +
              '<textarea class="modal-input" id="keys_' + idx + '" rows="3" style="width:100%;padding:6px 10px;font-size:10px;font-family:monospace;resize:vertical;box-sizing:border-box;" placeholder="sk-xxx1&#10;sk-xxx2&#10;sk-xxx3&#10;\uFF08\u7559\u7A7A\u5219\u4F7F\u7528\u4E0A\u65B9\u5355\u4E2A API Key\uFF09">' + _eh((p.api_keys || []).join('\n')) + '</textarea>' +
            '</div>' +
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">\u{1F310} \u591A\u7AEF\u70B9\u5BB9\u707E\uFF08\u53EF\u9009\uFF0C\u7AEF\u70B9\u5931\u6548\u81EA\u52A8\u5207\u6362\uFF09</span>' +
                '<span id="epCount_' + idx + '" style="font-size:9px;color:var(--text-muted);">' + (p.endpoints ? p.endpoints.length : 0) + ' \u4E2A\u7AEF\u70B9</span>' +
              '</div>' +
              '<div id="epList_' + idx + '" style="display:flex;flex-direction:column;gap:6px;">' +
                (p.endpoints || []).map(function(ep, ei) {
                  return '<div class="ep-item" style="border-radius:8px;border:1px solid var(--border);background:var(--bg-base);padding:8px 10px;">' +
                    '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">' +
                      '<span style="font-size:9px;color:var(--text-muted);flex-shrink:0;">#' + (ei+1) + '</span>' +
                      '<input type="text" placeholder="\u7AEF\u70B9\u5907\u6CE8\u540D\uFF08\u5982\uFF1A\u4E3B\u7AD9\u3001\u5907\u7528\uFF09" value="' + _ea(ep.name || '') + '" data-ep-idx="' + ei + '" data-field="name" style="flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-weight:500;">' +
                      '<label style="display:flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);cursor:pointer;flex-shrink:0;" title="\u542F\u7528/\u7981\u7528\u6B64\u7AEF\u70B9">' +
                        '<input type="checkbox" ' + (ep.enabled !== false ? 'checked' : '') + ' data-ep-idx="' + ei + '" data-field="enabled" style="accent-color:#22c55e;width:13px;height:13px;">' +
                        '<span>\u542F\u7528</span>' +
                      '</label>' +
                      '<button onclick="removeEndpoint(' + idx + ',' + ei + ')" title="\u5220\u9664\u6B64\u7AEF\u70B9" style="font-size:10px;padding:3px 7px;border-radius:5px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;flex-shrink:0;">\u2715</button>' +
                    '</div>' +
                    '<div style="display:flex;gap:6px;">' +
                      '<input type="text" placeholder="URL\uFF08\u5982 https://api.example.com/v1\uFF09" value="' + _ea(ep.url || '') + '" data-ep-idx="' + ei + '" data-field="url" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
                      '<input type="password" placeholder="API Key" value="' + _ea(ep.key || '') + '" data-ep-idx="' + ei + '" data-field="key" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
                    '</div>' +
                  '</div>';
                }).join('') +
              '</div>' +
              '<button onclick="addEndpoint(' + idx + ')" style="margin-top:6px;font-size:10px;padding:4px 10px;border-radius:6px;border:1px dashed var(--border);background:transparent;color:var(--accent);cursor:pointer;display:flex;align-items:center;gap:4px;">+ \u6DFB\u52A0\u7AEF\u70B9</button>' +
            '</div>' +
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;gap:6px;align-items:center;margin-bottom:3px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">\u9ED8\u8BA4\u6A21\u578B</span>' +
                '<span style="font-size:9px;color:var(--accent);">\u21BB \u4ECE\u4E0A\u6E38\u62C9\u53D6</span>' +
                (p.models && p.models.length ? '<span style="font-size:9px;color:var(--text-muted);">(' + window.filterModelsByType(p.models, p.type).length + '/' + p.models.length + ' \u5339\u914D' + p.type + ')</span>' : '') +
              '</div>' +
              '<div style="display:flex;gap:6px;">' +
                '<select class="modal-input" style="flex:1;padding:6px 8px;font-size:11px;" id="model_' + idx + '">' + modelOpts + '</select>' +
                '<button class="btn-secondary" onclick="fetchModels(' + idx + ')" id="fetchBtn_' + idx + '" style="flex-shrink:0;padding:6px 10px;font-size:10px;">\u21BB \u62C9\u53D6</button>' +
              '</div>' +
              '<div id="fetchStatus_' + idx + '" style="font-size:10px;color:var(--text-muted);margin-top:2px;"></div>' +
            '</div>' +
            '<div style="display:flex;align-items:center;justify-content:space-between;">' +
              '<label style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                '<input type="checkbox" id="en_' + idx + '" ' + (p.enabled?'checked':'') + ' style="accent-color:var(--accent);width:14px;height:14px;"> \u542F\u7528' +
              '</label>' +
              '<div style="display:flex;gap:6px;">' +
                '<button class="btn-primary" onclick="saveProvider(' + idx + ')" style="padding:5px 14px;font-size:11px;">\u4FDD\u5B58</button>' +
                '<button class="btn-secondary" onclick="testProvider(\'' + p.id + '\')" style="padding:5px 10px;font-size:11px;">\u6D4B\u8BD5</button>' +
                '<button class="btn-ghost" onclick="deleteProvider(\'' + p.id + '\')" style="color:#f87171;border-color:#f8717133;padding:5px 10px;font-size:11px;">\u5220\u9664</button>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>';
      }

      html += '</div>';
    });

    html += '</div></div>';
  });

  html += '</div>';

  body.innerHTML = html || '<div style="color:var(--text-muted);text-align:center;padding:40px;font-size:13px;">\u6682\u65E0 Provider\uFF0C\u70B9\u51FB\u4E0A\u65B9 [+ \u6DFB\u52A0] \u521B\u5EFA</div>';
};

window.saveProvider = function(idx) {
  var pid = document.getElementById('id_' + idx).value || '';
  var currentModels = [];
  try {
    var cached = localStorage.getItem('igs_models_' + pid);
    if (cached) currentModels = JSON.parse(cached);
  } catch(e){}
  if (!currentModels.length) {
    var modelSelect = document.getElementById('model_' + idx);
    if (modelSelect && modelSelect.options) {
      for (var mi = 0; mi < modelSelect.options.length; mi++) {
        var v = modelSelect.options[mi].value;
        if (v && !v.startsWith('\u8BF7\u5148')) currentModels.push(v);
      }
    }
  }

  var p = {
    id: document.getElementById('id_' + idx).value.trim() || 'p_' + Date.now(),
    name: document.getElementById('name_' + idx).value,
    type: document.getElementById('type_' + idx).value,
    base_url: document.getElementById('url_' + idx).value,
    api_key: document.getElementById('key_' + idx).value,
    api_keys: (document.getElementById('keys_' + idx).value || '').split('\n').map(function(s){ return s.trim(); }).filter(function(s){ return s.length > 0; }),
    endpoints: window.collectEndpoints(idx),
    model: document.getElementById('model_' + idx).value,
    color: document.getElementById('color_' + idx).value,
    enabled: document.getElementById('en_' + idx).checked,
    models: currentModels,
    display_name: (document.getElementById('display_name_' + idx) || {value:''}).value,
    quality: '', extra: {}
  };
  _af('/api/providers', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(p)
  }).then(function(r){ return r.json(); }).then(function(data){
    window.setStatus('Provider "' + p.name + '" \u5DF2\u4FDD\u5B58');
    window.loadProviders().then(function(){
      window.renderProviderEdit();
    });
  }).catch(function(e){ if (e.message !== 'AUTH_REQUIRED') window.setStatus('\u4FDD\u5B58\u5931\u8D25: ' + e.message); });
};

window.deleteProvider = function(id) {
  if (!confirm('\u786E\u5B9A\u5220\u9664 "' + id + '"\uFF1F')) return;
  _af('/api/providers/' + id, {method:'DELETE'}).then(function(r){return r.json();}).then(function(){
    window.setStatus('\u5DF2\u5220\u9664: ' + id);
    window.loadProviders().then(function(){
      window.renderProviderEdit();
    });
  }).catch(function(e){ window.setStatus('\u5220\u9664\u5931\u8D25: ' + e.message); });
};

window.addEndpoint = function(idx) {
  var list = document.getElementById('epList_' + idx);
  if (!list) return;
  var ei = list.children.length;
  var div = document.createElement('div');
  div.className = 'ep-item';
  div.style.cssText = 'border-radius:8px;border:1px solid var(--border);background:var(--bg-base);padding:8px 10px;';
  div.innerHTML =
    '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">' +
      '<span style="font-size:9px;color:var(--text-muted);flex-shrink:0;">#' + (ei+1) + '</span>' +
      '<input type="text" placeholder="\u7AEF\u70B9\u5907\u6CE8\u540D\uFF08\u5982\uFF1A\u4E3B\u7AD9\u3001\u5907\u7528\uFF09" data-ep-idx="' + ei + '" data-field="name" style="flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-weight:500;">' +
      '<label style="display:flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);cursor:pointer;flex-shrink:0;" title="\u542F\u7528/\u7981\u7528\u6B64\u7AEF\u70B9">' +
        '<input type="checkbox" checked data-ep-idx="' + ei + '" data-field="enabled" style="accent-color:#22c55e;width:13px;height:13px;">' +
        '<span>\u542F\u7528</span>' +
      '</label>' +
      '<button onclick="removeEndpoint(' + idx + ',' + ei + ')" title="\u5220\u9664\u6B64\u7AEF\u70B9" style="font-size:10px;padding:3px 7px;border-radius:5px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;flex-shrink:0;">\u2715</button>' +
    '</div>' +
    '<div style="display:flex;gap:6px;">' +
      '<input type="text" placeholder="URL\uFF08\u5982 https://api.example.com/v1\uFF09" data-ep-idx="' + ei + '" data-field="url" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
      '<input type="password" placeholder="API Key" data-ep-idx="' + ei + '" data-field="key" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
    '</div>';
  list.appendChild(div);
  var nameInput = div.querySelector('[data-field="name"]');
  if (nameInput) nameInput.focus();
  var cnt = document.getElementById('epCount_' + idx);
  if (cnt) cnt.textContent = list.children.length + ' \u4E2A\u7AEF\u70B9';
};

window.removeEndpoint = function(idx, ei) {
  var list = document.getElementById('epList_' + idx);
  if (!list) return;
  var items = list.querySelectorAll('.ep-item');
  if (items[ei]) items[ei].remove();
  var remaining = list.querySelectorAll('.ep-item');
  for (var r = 0; r < remaining.length; r++) {
    var inputs = remaining[r].querySelectorAll('input');
    for (var j = 0; j < inputs.length; j++) {
      inputs[j].setAttribute('data-ep-idx', r);
    }
    var btn = remaining[r].querySelector('button');
    if (btn) btn.setAttribute('onclick', 'removeEndpoint(' + idx + ',' + r + ')');
  }
  var cnt = document.getElementById('epCount_' + idx);
  if (cnt) cnt.textContent = remaining.length + ' \u4E2A\u7AEF\u70B9';
};

window.collectEndpoints = function(idx) {
  var list = document.getElementById('epList_' + idx);
  if (!list) return [];
  var items = list.querySelectorAll('.ep-item');
  var endpoints = [];
  for (var i = 0; i < items.length; i++) {
    var inputs = items[i].querySelectorAll('input');
    var ep = { name: '', url: '', key: '', enabled: true };
    for (var j = 0; j < inputs.length; j++) {
      var field = inputs[j].getAttribute('data-field');
      if (field === 'enabled') ep.enabled = inputs[j].checked;
      else if (field === 'name') ep.name = inputs[j].value;
      else if (field === 'url') ep.url = inputs[j].value;
      else if (field === 'key') ep.key = inputs[j].value;
    }
    if (ep.url || ep.key) endpoints.push(ep);
  }
  return endpoints;
};

window.testProvider = function(id) {
  var btn = event && event.target;
  if (btn) { btn.disabled = true; btn.textContent = '\u6D4B\u8BD5\u4E2D...'; }
  _af('/api/providers/test/' + id).then(function(r){return r.json();}).then(function(d){
    if (d.endpoints && d.endpoints.length > 0) {
      var lines = d.endpoints.map(function(ep) {
        var icon = ep.success ? '\u2705' : '\u274C';
        var latency = ep.latency_ms ? ep.latency_ms + 'ms' : '';
        var name = ep.name || ep.url;
        return icon + ' ' + name + (ep.success ? ' (' + latency + ')' : ' - ' + (ep.error || '\u5931\u8D25') + ' (' + latency + ')');
      });
      alert((d.success ? '\u2705 \u81F3\u5C11\u4E00\u4E2A\u7AEF\u70B9\u53EF\u7528' : '\u274C \u6240\u6709\u7AEF\u70B9\u5931\u8D25') + '\n\n' + lines.join('\n'));
    } else {
      alert(d.success ? '\u2705 \u6D4B\u8BD5\u6210\u529F!' : '\u274C \u5931\u8D25: ' + (d.error||''));
    }
  }).catch(function(e){ alert('\u274C \u6D4B\u8BD5\u5931\u8D25: ' + e.message); })
  .finally(function(){ if (btn) { btn.disabled = false; btn.textContent = '\u6D4B\u8BD5'; } });
};

window.fetchModels = function(idx) {
  var pid = document.getElementById('id_' + idx).value;
  var urlVal = document.getElementById('url_' + idx).value;
  var keyVal = document.getElementById('key_' + idx).value;
  var nameVal = document.getElementById('name_' + idx).value;
  var typeVal = document.getElementById('type_' + idx).value;
  var colorVal = document.getElementById('color_' + idx).value;
  var enVal = document.getElementById('en_' + idx).checked;

  var btn = document.getElementById('fetchBtn_' + idx);
  var st  = document.getElementById('fetchStatus_' + idx);
  btn.disabled = true; btn.textContent = '...';
  st.textContent = '\u8FDE\u63A5\u4E2D...'; st.style.color = 'var(--text-muted)';

  var tmp = { id:pid||'tmp', name:nameVal, type:typeVal, base_url:urlVal, api_key:keyVal, model:'', color:colorVal, enabled:enVal, models:[], quality:'', extra:{} };

  _af('/api/providers', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(tmp)})
  .then(function(){ return _af('/api/providers/fetch-models/' + pid); })
  .then(function(r){ return r.json(); })
  .then(function(data){
    if (data.success) {
      st.textContent = '\u2705 \u62C9\u53D6\u6210\u529F ' + data.count + ' \u4E2A\u6A21\u578B' + (data.is_fallback ? ' (\u63A8\u8350\u5217\u8868)' : '');
      st.style.color = '#22c3a5';
      try { localStorage.setItem('igs_models_' + pid, JSON.stringify(data.models)); } catch(e){}
      window.loadProviders().then(function(){ window.renderProviderEdit(); });
    } else {
      st.textContent = '\u274C ' + (data.detail || '\u5931\u8D25');
      st.style.color = '#f87171';
    }
  }).catch(function(e){
    st.textContent = '\u274C ' + e.message; st.style.color = '#f87171';
  }).finally(function(){
    btn.disabled = false; btn.textContent = '\u21BB \u62C9\u53D6';
  });
};

window.reloadProviders = function() {
  _af('/api/providers/reload', {method:'POST'}).then(function(){
    window.loadProviders().then(function(){ window.renderProviderEdit(); });
    window.setStatus('\u914D\u7F6E\u5DF2\u91CD\u65B0\u52A0\u8F7D');
  });
};

/* ═══════════════════════════════════════════════════════════════════
   Proxy Config
   ═══════════════════════════════════════════════════════════════════ */
window._loadProxyConfig = function() {
  _af('/api/proxy')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var el = document.getElementById('proxyEnabled');
      if (el) el.checked = d.enabled;
      var t = document.getElementById('proxyType');
      if (t) t.value = d.type || 'http';
      var h = document.getElementById('proxyHost');
      if (h) h.value = d.host || '127.0.0.1';
      var p = document.getElementById('proxyPort');
      if (p) p.value = d.port || 10808;
      var u = document.getElementById('proxyUser');
      if (u) u.value = d.username || '';
      var badge = document.getElementById('proxyStatusBadge');
      if (badge) {
        if (d.enabled) {
          badge.textContent = d.host + ':' + d.port;
          badge.style.background = '#22c55e22';
          badge.style.color = '#22c55e';
        } else {
          badge.textContent = '\u672A\u542F\u7528';
          badge.style.background = '#6b728022';
          badge.style.color = '#6b7280';
        }
      }
    });
};

window.saveProxyConfig = function() {
  var data = {
    enabled: document.getElementById('proxyEnabled').checked,
    type: document.getElementById('proxyType').value,
    host: document.getElementById('proxyHost').value.trim(),
    port: parseInt(document.getElementById('proxyPort').value) || 10808,
    username: document.getElementById('proxyUser').value.trim(),
    password: document.getElementById('proxyPass').value,
  };
  _af('/api/proxy', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
  .then(function(r){ return r.json(); })
  .then(function(d) {
    var badge = document.getElementById('proxyStatusBadge');
    if (badge) {
      if (data.enabled) {
        badge.textContent = data.host + ':' + data.port;
        badge.style.background = '#22c55e22';
        badge.style.color = '#22c55e';
      } else {
        badge.textContent = '\u672A\u542F\u7528';
        badge.style.background = '#6b728022';
        badge.style.color = '#6b7280';
      }
    }
    var result = document.getElementById('proxyTestResult');
    if (result) result.innerHTML = '<span style="color:#22c55e;">\u2713 \u4EE3\u7406\u914D\u7F6E\u5DF2\u4FDD\u5B58</span>';
  });
};

window.testProxyConfig = function() {
  var btn = document.getElementById('proxyTestBtn');
  var result = document.getElementById('proxyTestResult');
  if (btn) { btn.textContent = '\u23F3 \u6D4B\u8BD5\u4E2D...'; btn.disabled = true; }
  if (result) result.innerHTML = '<span style="color:var(--text-muted);">\u6B63\u5728\u6D4B\u8BD5\u4EE3\u7406\u8FDE\u901A\u6027...</span>';

  _af('/api/proxy/test', { method: 'POST' })
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (btn) { btn.textContent = '\u6D4B\u8BD5\u8FDE\u63A5'; btn.disabled = false; }
      if (!d.ok) {
        var msgs = [];
        var keys = Object.keys(d.results || {});
        for (var i = 0; i < keys.length; i++) {
          var r = d.results[keys[i]];
          msgs.push(keys[i] + ': ' + (r.status === 'ok' ? r.ms + 'ms \u2713' : '\u2717 ' + (r.error || '\u4E0D\u901A')));
        }
        if (result) result.innerHTML = '<span style="color:#f59e0b;">\u26A0 \u90E8\u5206\u4E0D\u901A</span><br>' + msgs.join('<br>');
      } else {
        var msgs2 = [];
        var keys2 = Object.keys(d.results || {});
        for (var j = 0; j < keys2.length; j++) {
          var r2 = d.results[keys2[j]];
          msgs2.push(keys2[j] + ': ' + r2.ms + 'ms \u2713');
        }
        if (result) result.innerHTML = '<span style="color:#22c55e;">\u2713 \u4EE3\u7406\u8FDE\u901A\u6B63\u5E38</span><br>' + msgs2.join('<br>');
      }
    })
    .catch(function(e) {
      if (btn) { btn.textContent = '\u6D4B\u8BD5\u8FDE\u63A5'; btn.disabled = false; }
      if (result) result.innerHTML = '<span style="color:#ef4444;">\u2717 \u6D4B\u8BD5\u5931\u8D25: ' + window.escHtml(e.message) + '</span>';
    });
};

window.openProviderModal = function() {
  document.getElementById('providerModal').classList.add('show');
  window.renderProviderEdit();
};
window.closeProviderModal = function() {
  document.getElementById('providerModal').classList.remove('show');
};

})();
