(function(){
'use strict';

function _af(url, opts) { return window._authFetch(url, opts); }
function _eh(s) { return window.escHtml(s); }
function _ea(s) { return window.escAttr(s); }

/* ═══════════════════════════════════════════════════════════════════
   Sub-Tab Switching
   ═══════════════════════════════════════════════════════════════════ */
window.switchSubTab = function(mode) {
  window.currentMode = mode;
  document.getElementById('panelT2I').classList.toggle('hidden', mode !== 't2i');
  document.getElementById('panelI2I').classList.toggle('hidden', mode !== 'i2i');
  document.getElementById('panelVAR').classList.toggle('hidden', mode !== 'variation');
  document.getElementById('subTabT2I').classList.toggle('active', mode === 't2i');
  document.getElementById('subTabI2I').classList.toggle('active', mode === 'i2i');
  document.getElementById('subTabVAR').classList.toggle('active', mode === 'variation');
  document.getElementById('strengthGroup').style.display = mode === 'i2i' ? '' : 'none';
  document.getElementById('quickCard').style.display = mode === 't2i' ? '' : 'none';
  window.hideEnhance();
};

/* ═══════════════════════════════════════════════════════════════════
   File Upload (i2i & variation)
   ═══════════════════════════════════════════════════════════════════ */
window.handleFileSelect = function(e) { var f = e.target.files[0]; if(f) window.handleFile(f); };
window.handleFile = function(f) {
  if (!f.type.startsWith('image/')) { alert('\u8BF7\u9009\u62E9\u56FE\u7247\u6587\u4EF6'); return; }
  if (f.size > 10*1024*1024) { alert('\u56FE\u7247\u4E0D\u80FD\u8D85\u8FC7 10MB'); return; }
  var reader = new FileReader();
  reader.onload = function(e2) {
    window.uploadedImageData = e2.target.result;
    var p = document.getElementById('uploadPreview');
    p.src = window.uploadedImageData;
    p.classList.remove('hidden');
  };
  reader.readAsDataURL(f);
};

window.variationImageData = null;
window.handleFileSelectVar = function(e) { var f = e.target.files[0]; if(f) window.handleFileVar(f); };
window.handleFileVar = function(f) {
  if (!f.type.startsWith('image/')) { alert('\u8BF7\u9009\u62E9\u56FE\u7247\u6587\u4EF6'); return; }
  if (f.size > 10*1024*1024) { alert('\u56FE\u7247\u4E0D\u80FD\u8D85\u8FC7 10MB'); return; }
  var reader = new FileReader();
  reader.onload = function(e2) {
    window.variationImageData = e2.target.result;
    var p = document.getElementById('uploadPreviewVar');
    p.src = window.variationImageData;
    p.classList.remove('hidden');
  };
  reader.readAsDataURL(f);
};

/* ═══════════════════════════════════════════════════════════════════
   Size Inference
   ═══════════════════════════════════════════════════════════════════ */
window.inferSize = function(p) {
  if (!p) return null;
  var l = p.toLowerCase();
  var wide = ['wide','widescreen','21:9','cinematic','panorama','panoramic','landscape','\u6A2A\u5C4F','\u5BBD\u5C4F','\u7535\u5F71\u611F','\u5168\u666F','banner'];
  var tall = ['portrait','vertical','9:16','phone','mobile','poster','\u7AD6\u5C4F','\u6D77\u62A5','tall'];
  var por  = ['portrait photo','headshot','face','\u4EBA\u50CF','\u5934\u50CF','\u7279\u5199','beauty','fashion','model'];
  for (var i=0;i<wide.length;i++) if(l.indexOf(wide[i])!==-1) return '1792x1024';
  for (var i=0;i<tall.length;i++) if(l.indexOf(tall[i])!==-1) return '1024x1792';
  for (var i=0;i<por.length;i++)  if(l.indexOf(por[i])!==-1)  return '1536x1024';
  return '1024x1024';
};

/* ═══════════════════════════════════════════════════════════════════
   Generation Polling State
   ═══════════════════════════════════════════════════════════════════ */
window.genPollTimer = null;
window.genCurrentGenId = null;
window.genDisplayedResults = {};
window.genStartTs = 0;
window.genTimerInterval = null;
window.genProviderCollapsed = {};

window._smartScroll = function(el) {
  if (!el) return;
  var threshold = 80;
  var nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  if (nearBottom) el.scrollTop = el.scrollHeight;
};

window.renderGenPerProviderBars = function(providerStates) {
  var container = document.getElementById('perProviderSection');
  if (!container) return;

  var groups = {};
  Object.keys(providerStates).forEach(function(key) {
    var s = providerStates[key];
    var gname = s.name || s.model || key;
    if (!groups[gname]) groups[gname] = [];
    groups[gname].push({ key: key, state: s });
  });

  var html = '';
  Object.keys(groups).forEach(function(gname) {
    var items = groups[gname];
    var firstState = items[0].state;
    var isCollapsed = !!window.genProviderCollapsed[gname];
    var groupColor = firstState.color || 'var(--accent)';
    var groupStatus = firstState.status;
    items.forEach(function(it) {
      if (it.state.status === 'generating') groupStatus = 'generating';
    });
    var statusIcon = groupStatus === 'completed' ? '\u2714' : groupStatus === 'failed' ? '\u2718' : groupStatus === 'generating' ? '\u23F3' : '\u2022';
    var completedCount = items.filter(function(it) { return it.state.status === 'completed' && it.state.result && it.state.result.success; }).length;
    var failedCount = items.filter(function(it) { return it.state.status === 'failed' || (it.state.result && !it.state.result.success); }).length;
    var totalCount = items.length;

    html += '<div style="margin-bottom:10px;border:1px solid var(--border);border-radius:10px;background:var(--bg-surface);overflow:hidden;">';
    html += '<div onclick="toggleGenProviderGroup(\'' + gname.replace(/'/g, "\\'") + '\')" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;cursor:pointer;background:var(--bg-card);border-bottom:1px solid ' + (isCollapsed ? 'var(--border)' : 'transparent') + ';">';
    html += '<div style="display:flex;align-items:center;gap:8px;">';
    html += '<span style="font-size:10px;transition:transform 0.2s;display:inline-block;transform:rotate(' + (isCollapsed ? '0' : '90') + 'deg);">\u25B6</span>';
    html += '<span style="font-size:12px;font-weight:700;color:' + groupColor + ';">' + _eh(gname) + '</span>';
    html += '<span style="font-size:10px;color:var(--text-muted);">' + completedCount + '/' + totalCount + '</span>';
    if (failedCount > 0) html += '<span style="font-size:10px;color:#ef4444;">' + failedCount + ' \u5931\u8D25</span>';
    html += '</div>';
    html += '<span style="font-size:10px;color:' + (groupStatus === 'completed' ? '#22c55e' : groupStatus === 'failed' ? '#ef4444' : groupStatus === 'generating' ? 'var(--accent)' : 'var(--text-muted') + ';">' + statusIcon + ' ' + (groupStatus === 'completed' ? '\u5B8C\u6210' : groupStatus === 'generating' ? '\u751F\u6210\u4E2D' : groupStatus === 'failed' ? '\u5931\u8D25' : '\u6392\u961F') + '</span>';
    html += '</div>';

    if (!isCollapsed) {
      html += '<div style="padding:8px 10px;">';
      items.forEach(function(it) {
        var s = it.state;
        var statusText = s.status === 'queued' ? '\u6392\u961F\u4E2D' : s.status === 'generating' ? '\u751F\u6210\u4E2D...' : s.status === 'completed' ? '\u2714 ' + (s.result ? s.result.elapsed_seconds : '') + 's' : '\u2718 \u5931\u8D25';
        var statusColor = s.status === 'completed' ? '#22c55e' : s.status === 'failed' ? '#ef4444' : s.status === 'generating' ? 'var(--accent)' : 'var(--text-muted)';
        var fillClass = s.status === 'generating' ? 'vprog-fill marquee' : s.status === 'completed' ? 'vprog-fill complete' : 'vprog-fill';

        html += '<div style="margin-bottom:6px;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">';
        html += '<span style="font-size:10px;color:var(--text-muted);">#' + (parseInt(it.key.split('_').pop()) + 1) + '</span>';
        html += '<span id="gprog_label_' + it.key + '" style="font-size:10px;color:' + statusColor + ';">' + statusText + '</span>';
        html += '</div>';
        html += '<div style="background:var(--border);border-radius:3px;overflow:hidden;height:4px;margin-bottom:3px;">';
        html += '<div class="' + fillClass + '" id="gprog_fill_' + it.key + '" style="width:' + s.progress + '%;"></div>';
        html += '</div>';
        html += '<div id="glog_' + it.key + '" class="vlog-mini" style="display:block;">';
        html += (s.log || []).map(function(line) { return '<div style="color:var(--text-muted);">' + _eh(line) + '</div>'; }).join('');
        html += '</div>';
        html += '</div>';
      });
      html += '</div>';
    }

    html += '</div>';
  });

  container.innerHTML = html;
  container.style.display = 'block';
  window._smartScroll(container);
};

window.toggleGenProviderGroup = function(name) {
  window.genProviderCollapsed[name] = !window.genProviderCollapsed[name];
  if (window._lastProviderStates) window.renderGenPerProviderBars(window._lastProviderStates);
};

window.genLogProvider = function(key, msg, type) {
  var mini = document.getElementById('glog_' + key);
  var ts = new Date().toLocaleTimeString();
  var logColors = { info: 'var(--text-muted)', ok: '#22c55e', warn: '#f59e0b', error: '#ef4444' };
  var color = logColors[type] || logColors.info;
  if (mini) {
    var prefix = type === 'ok' ? '\u2714' : type === 'error' ? '\u2718' : type === 'warn' ? '\u26A0' : '\u25B8';
    var line = document.createElement('div');
    line.style.cssText = 'color:' + color + ';';
    line.textContent = '[' + ts + '] ' + prefix + ' ' + msg;
    mini.appendChild(line);
    window._smartScroll(mini);
  }
  var area = document.getElementById('genLogArea');
  if (area) {
    var line2 = document.createElement('div');
    line2.style.cssText = 'color:' + color + ';';
    line2.textContent = '[' + ts + '] ' + key + ': ' + msg;
    area.appendChild(line2);
    window._smartScroll(area);
  }
};

window.startGenPolling = function(genId) {
  window.genCurrentGenId = genId;
  window.genDisplayedResults = {};
  var elapsedEl = document.getElementById('elapsedSeconds');
  if (window.genTimerInterval) clearInterval(window.genTimerInterval);
  window.genTimerInterval = setInterval(function() {
    var elapsed = ((Date.now() - window.genStartTs) / 1000).toFixed(1);
    if (elapsedEl) elapsedEl.textContent = elapsed;
  }, 200);
  var pollCount = 0;
  window.genPollTimer = setInterval(function() {
    pollCount++;
    _af('/api/generate/status/' + genId).then(function(r) { return r.json(); }).then(function(data) {
      var pfill = document.getElementById('progressFill');
      var ptxt = document.getElementById('progressText');
      if (pfill) pfill.style.width = data.progress + '%';

      if (ptxt && data.status !== 'completed') {
        var states = data.provider_states || {};
        var names = Object.keys(states).map(function(k) { return states[k].name || k; });
        var generating = Object.values(states).filter(function(s) { return s.status === 'generating'; });
        var done = Object.values(states).filter(function(s) { return s.status === 'completed' || s.status === 'failed'; });
        if (generating.length > 0) {
          if (ptxt) ptxt.textContent = generating.map(function(s) { return s.name || s.model; }).join(', ') + ' \u751F\u6210\u4E2D... (' + done.length + '/' + names.length + ' \u5B8C\u6210)';
        } else if (done.length < names.length) {
          if (ptxt) ptxt.textContent = '\u6392\u961F\u4E2D... (' + done.length + '/' + names.length + ' \u5B8C\u6210)';
        }
      }

      if (data.provider_states) {
        window._lastProviderStates = data.provider_states;
        window.renderGenPerProviderBars(data.provider_states);
        var logEl = document.getElementById('genLogArea');
        if (logEl) {
          var allLogs = [];
          Object.keys(data.provider_states).forEach(function(k) {
            var logs = data.provider_states[k].log || [];
            logs.forEach(function(l) { if (allLogs.indexOf(l) === -1) allLogs.push(l); });
          });
          if (allLogs.length > 0) logEl.textContent = allLogs.join('\n');
        }
        Object.keys(data.provider_states).forEach(function(key) {
          var s = data.provider_states[key];
          if (s.status === 'completed' && s.result && s.result.success && s.result.local_path && !window.genDisplayedResults[key]) {
            window.genDisplayedResults[key] = s.result;
            window.addResultToPreview(key, s.result);
          }
        });
      }

      if (data.status === 'completed') {
        window.stopGenPolling();
        var elapsedEl = document.getElementById('elapsedSeconds');
        if (elapsedEl && data.elapsed_seconds !== undefined) elapsedEl.textContent = data.elapsed_seconds.toFixed(1);
        window.currentResults = data.results || {};
        window.currentGroupTimings = data.group_timings || {};
        if (data.continuous_id) window.continuousSessionId = data.continuous_id;
        if (data.enhanced_prompt) window.showEnhanceResult(data.enhanced_prompt);
        if (data.llm_error && !data.enhanced_prompt) window.showEnhanceResult('\u26A0\uFE0F ' + data.llm_error);
        window.showResults(window.currentResults, '', window.currentGroupTimings);
        var pfill2 = document.getElementById('progressFill');
        if (pfill2) pfill2.style.width = '100%';
        var okCount = Object.values(window.currentResults).filter(function(r) { return r.success; }).length;
        var totalProviders = Object.keys(data.provider_states || {}).length;
        if (ptxt) ptxt.textContent = '\u751F\u6210\u5B8C\u6210! ' + okCount + '/' + totalProviders + ' \u6210\u529F';
        window.setStatus('\u751F\u6210\u5B8C\u6210 \u00B7 ' + okCount + '/' + totalProviders + ' \u6210\u529F \u00B7 ' + (data.elapsed_seconds || 0) + 's');
        window.loadGallery();
        var btn = document.getElementById('btnGen');
        if (btn) { btn.disabled = false; btn.innerHTML = '\u2728 \u751F\u6210\u56FE\u7247'; }
        var closeBtn = document.getElementById('progressCloseBtn');
        if (closeBtn) closeBtn.style.display = 'inline-block';
        var logWrap = document.getElementById('genLogWrap');
        if (logWrap) { var cnt = document.getElementById('genLogCount'); if (cnt) cnt.textContent = '\u5B8C\u6210'; }
      }
    }).catch(function(e) {
      console.error('Poll error:', e);
    });
  }, 1500);
};

window.stopGenPolling = function() {
  if (window.genPollTimer) { clearInterval(window.genPollTimer); window.genPollTimer = null; }
  if (window.genTimerInterval) { clearInterval(window.genTimerInterval); window.genTimerInterval = null; }
};

/* ═══════════════════════════════════════════════════════════════════
   Do Generate
   ═══════════════════════════════════════════════════════════════════ */
window.doGenerate = function() {
  if (window.currentMode === 'variation') {
    window.doVariation();
    return;
  }

  var prompt = '';
  var systemPrompt = null;
  if (window.currentMode === 't2i') {
    prompt = window.getFinalPrompt();
    if (window.promptMode === 'pro') {
      systemPrompt = document.getElementById('txtSysPrompt').value.trim();
    }
  } else {
    prompt = document.getElementById('txtPromptI2I').value.trim();
    if (!prompt && !window.uploadedImageData) { alert('\u8BF7\u4E0A\u4F20\u53C2\u8003\u56FE\u7247\u6216\u8F93\u5165\u4FEE\u6539\u63D0\u793A\u8BCD'); return; }
    if (!window.uploadedImageData) { alert('\u8BF7\u5148\u4E0A\u4F20\u53C2\u8003\u56FE\u7247'); return; }
  }
  if (!prompt) { alert('\u8BF7\u8F93\u5165\u63D0\u793A\u8BCD'); return; }
  if (!window.selectedProviders.length) { alert('\u8BF7\u81F3\u5C11\u9009\u62E9\u4E00\u4E2A\u6A21\u578B'); return; }

  var btn = document.getElementById('btnGen');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin" style="display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;vertical-align:middle;margin-right:4px;"></span>\u63D0\u4EA4\u4E2D...';

  var pbox = document.getElementById('progressBox');
  var ptxt = document.getElementById('progressText');
  var pfill = document.getElementById('progressFill');
  var elapsedEl = document.getElementById('elapsedSeconds');
  var perSection = document.getElementById('perProviderSection');
  var logWrap = document.getElementById('genLogWrap');
  var logArea = document.getElementById('genLogArea');
  var logCount = document.getElementById('genLogCount');
  pbox.classList.remove('hidden');
  ptxt.textContent = '\u6B63\u5728\u63D0\u4EA4...';
  pfill.style.width = '5%';
  elapsedEl.textContent = '0.0';
  if (perSection) { perSection.innerHTML = ''; perSection.style.display = 'none'; }
  if (logWrap) logWrap.style.display = 'block';
  if (logArea) logArea.innerHTML = '';
  if (logCount) logCount.textContent = '';

  window.genStartTs = Date.now();
  var timerInterval = setInterval(function() {
    var elapsed = ((Date.now() - window.genStartTs) / 1000).toFixed(1);
    elapsedEl.textContent = elapsed;
  }, 200);

  var imageSettings = window.loadImageProviderSettings();
  var selectedModel = document.getElementById('selModel').value || '_global';
  var currentSettings = imageSettings[selectedModel] || imageSettings['_global'] || {};
  var genQuality = currentSettings.quality || '';
  var genRatio = currentSettings.ratio || '1:1';
  var genW = currentSettings.w || 1024;
  var genH = currentSettings.h || 1024;
  var genQty = currentSettings.qty || 1;

  var genSize;
  if (genRatio === 'auto') {
    genSize = window.inferSize(prompt);
  } else if (genRatio && window.RATIO_SIZES[genRatio]) {
    var rsz = window.RATIO_SIZES[genRatio];
    genSize = rsz[0] + 'x' + rsz[1];
  } else {
    genSize = genW + 'x' + genH;
  }

  var qtyMap = {};
  for (var qi = 0; qi < window.selectedProviders.length; qi++) {
    qtyMap[window.selectedProviders[qi]] = genQty;
  }

  if (selectedModel !== '_global') {
    for (var pi = 0; pi < window.allProviders.length; pi++) {
      if (window.allProviders[pi].type === 'image' && window.selectedProviders.indexOf(window.allProviders[pi].id) >= 0) {
        window.allProviders[pi].model = selectedModel;
      }
    }
  }

  var payload = {
    prompt: prompt,
    providers: window.selectedProviders,
    enhance_prompt: document.getElementById('chkEnhance').checked,
    llm_provider_id: localStorage.getItem('igs_llm_provider') || undefined,
    mode: window.currentMode,
    size: genSize,
    quality: genQuality || undefined,
    continuous: document.getElementById('chkContinuous').checked,
    system_prompt: systemPrompt,
    continuous_id: window.continuousSessionId || null,
    quantities: qtyMap,
  };
  if (window.currentMode === 'i2i' && window.uploadedImageData) {
    payload.image_data = window.uploadedImageData;
    payload.strength = parseFloat(document.getElementById('selStrength').value);
  }
  if (document.getElementById('chkUpscale').checked) {
    payload.upscale_to = document.getElementById('upscaleSize').value;
    payload.upscale_method = document.getElementById('upscaleMethod').value;
  }

  _af('/api/generate', {
    method: 'POST',
    body: JSON.stringify(payload)
  }).then(function(r) {
    clearInterval(timerInterval);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(data) {
    clearInterval(timerInterval);
    pfill.style.width = '15%';
    ptxt.textContent = '\u4EFB\u52A1\u5DF2\u63D0\u4EA4\uFF0C\u961F\u5217\u5904\u7406\u4E2D...';
    if (data.generation_id) {
      window.startGenPolling(data.generation_id);
    }
  }).catch(function(e) {
    clearInterval(timerInterval);
    window.stopGenPolling();
    pbox.classList.add('hidden');
    alert('\u63D0\u4EA4\u5931\u8D25: ' + e.message);
    window.setStatus('\u63D0\u4EA4\u5931\u8D25: ' + e.message);
    btn.disabled = false;
    btn.innerHTML = '\u2728 \u751F\u6210\u56FE\u7247';
  });
};

window.doVariation = function() {
  if (!window.variationImageData) { alert('\u8BF7\u5148\u4E0A\u4F20\u6E90\u56FE\u7247'); return; }
  if (!window.selectedProviders.length) { alert('\u8BF7\u81F3\u5C11\u9009\u62E9\u4E00\u4E2A\u751F\u56FE\u6A21\u578B'); return; }

  var btn = document.getElementById('btnGen');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin" style="display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;vertical-align:middle;margin-right:4px;"></span>\u63D0\u4EA4\u4E2D...';

  var pbox = document.getElementById('progressBox');
  var ptxt = document.getElementById('progressText');
  var pfill = document.getElementById('progressFill');
  var elapsedEl = document.getElementById('elapsedSeconds');
  pbox.classList.remove('hidden');
  ptxt.textContent = '\u6B63\u5728\u751F\u6210\u53D8\u5F62...';
  pfill.style.width = '10%';
  elapsedEl.textContent = '0.0';

  window.genStartTs = Date.now();
  var timerInterval = setInterval(function() {
    var elapsed = ((Date.now() - window.genStartTs) / 1000).toFixed(1);
    elapsedEl.textContent = elapsed;
  }, 200);

  var payload = {
    image_data: window.variationImageData,
    provider_id: window.selectedProviders[0] || '',
    size: document.getElementById('varSize').value,
    n: parseInt(document.getElementById('varCount').value) || 1,
  };

  _af('/api/images/variations', {
    method: 'POST',
    body: JSON.stringify(payload)
  }).then(function(r) {
    clearInterval(timerInterval);
    if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || 'HTTP ' + r.status); });
    return r.json();
  }).then(function(data) {
    clearInterval(timerInterval);
    pfill.style.width = '100%';
    ptxt.textContent = '\u53D8\u5F62\u5B8C\u6210\uFF01\u5171 ' + (data.images || []).length + ' \u5F20';
    elapsedEl.textContent = ((Date.now() - window.genStartTs) / 1000).toFixed(1);
    btn.disabled = false;
    btn.innerHTML = '\u2728 \u751F\u6210\u56FE\u7247';
    var provId = data.provider_id || window.selectedProviders[0] || 'variation';
    if (data.images && data.images.length) {
      data.images.forEach(function(img, idx) {
        var localPath = img.local_path || '';
        if (localPath) {
          window.addResultToPreview(provId + '_' + idx, {
            local_path: localPath,
            model: provId,
            prompt: '\u53D8\u5F62\u53D8\u4F53',
            seq: idx,
          });
        }
      });
    }
    window.setStatus('\u53D8\u5F62\u5B8C\u6210');
  }).catch(function(e) {
    clearInterval(timerInterval);
    pbox.classList.add('hidden');
    alert('\u53D8\u5F62\u5931\u8D25: ' + e.message);
    window.setStatus('\u53D8\u5F62\u5931\u8D25: ' + e.message);
    btn.disabled = false;
    btn.innerHTML = '\u2728 \u751F\u6210\u56FE\u7247';
  });
};

/* ═══════════════════════════════════════════════════════════════════
   Enhance Result
   ═══════════════════════════════════════════════════════════════════ */
window.showEnhanceResult = function(text) {
  var el = document.getElementById('enhanceResult');
  var et = document.getElementById('enhanceText');
  if (et) et.textContent = text;
  if (el) el.classList.add('show');
};

window.hideEnhance = function() {
  document.getElementById('enhanceResult').classList.remove('show');
};

window.insertEnhance = function() {
  var text = document.getElementById('enhanceText').textContent;
  if (window.currentMode === 't2i') {
    document.getElementById('txtPrompt').value = text;
  } else {
    document.getElementById('txtPromptI2I').value = text;
  }
  window.hideEnhance();
};

window.copyEnhance = function() {
  var text = document.getElementById('enhanceText').textContent;
  navigator.clipboard.writeText(text).then(function(){
    window.setStatus('\u5DF2\u590D\u5236\u5230\u526A\u8D34\u677F');
  });
};

/* ═══════════════════════════════════════════════════════════════════
   Results Display
   ═══════════════════════════════════════════════════════════════════ */
window.showResults = function(results, prompt, timings) {
  try {
  window.currentGroupTimings = timings || window.currentGroupTimings || {};
  var emptyEl = document.getElementById('previewEmpty');
  var container = document.getElementById('previewResults');
  var cnt = document.getElementById('resultCount');
  if (!container) { console.error('previewResults not found'); return; }
  var keys = Object.keys(results);

  container.innerHTML = '';

  window.previewImages = [];
  window.previewGroups = {};
  window.failedGroups = {};
  for (var i = 0; i < keys.length; i++) {
    var pid = keys[i];
    var r = results[pid];
    var realPid = pid.replace(/_\d+$/, '');
    var seq = r.seq !== undefined ? r.seq : -1;
    if (r.success && r.local_path) {
      var fname = r.local_path.split(/[\\/]/).pop();
      var pInfo = window.findProvider(pid) || {name: pid, color: '#5b8def'};
      var displayName = pInfo.name + (seq >= 1 ? ' #' + (seq+1) : '');
      window.previewImages.push({ pid: pid, realPid: realPid, src: '/api/gallery/image/' + fname, name: displayName, color: pInfo.color, fname: fname });
      if (!window.previewGroups[realPid]) window.previewGroups[realPid] = [];
      window.previewGroups[realPid].push(window.previewImages[window.previewImages.length - 1]);
    } else {
      if (!window.failedGroups[realPid]) window.failedGroups[realPid] = [];
      window.failedGroups[realPid].push({ pid: pid, error: r.error || '\u672A\u77E5\u9519\u8BEF', seq: seq });
    }
  }

  var totalSuccess = window.previewImages.length;
  var totalFailed = Object.values(window.failedGroups).reduce(function(s, g){ return s + g.length; }, 0);
  var totalModels = keys.length;
  cnt.textContent = totalSuccess + ' \u5F20\u6210\u529F' + (totalFailed > 0 ? ' \u00B7 ' + totalFailed + ' \u5F20\u5931\u8D25' : '');

  emptyEl.style.display = 'none';

  if (window.previewImages.length === 0) {
    for (var i = 0; i < keys.length; i++) {
      (function(pid){
        var r = results[pid];
        var pInfo = window.findProvider(pid) || {name: pid, color: '#5b8def'};
        var card = document.createElement('div');
        card.className = 'result-card fade-in';
        card.innerHTML =
          '<div class="result-error-box">' +
            '<div class="err-icon">\u26A0</div>' +
            '<div class="err-msg">' + _eh(r.error || '\u672A\u77E5\u9519\u8BEF') + '</div>' +
          '</div>' +
          '<div class="result-info">' +
            '<span class="result-provider-tag" style="background:' + pInfo.color + '20;color:' + pInfo.color + ';">' +
              '<span style="width:6px;height:6px;border-radius:50%;background:' + pInfo.color + ';display:inline-block;"></span>' +
              ' ' + _eh(pInfo.name) +
            '</span>' +
            '<span class="result-status-err">\u2718</span>' +
          '</div>';
        container.appendChild(card);
      })(keys[i]);
    }
    return;
  }

  window.previewIndex = 0;
  window.renderGroupedPreview(container);
  } catch(e) { console.error('[showResults] error:', e); alert('showResults error: ' + e.message); }
};

window.renderPreviewViewer = function(container) {
  container.innerHTML = '';
  if (!window.previewImages.length) return;

  var cur = window.previewImages[window.previewIndex];

  var viewerWrap = document.createElement('div');
  viewerWrap.style.cssText = 'position:relative;flex:1;display:flex;align-items:center;justify-content:center;min-height:200px;overflow:hidden;border-radius:10px;background:var(--bg-surface);';

  if (window.previewImages.length > 1) {
    var btnPrev = document.createElement('button');
    btnPrev.className = 'preview-nav-btn';
    btnPrev.innerHTML = '\u2039';
    btnPrev.style.cssText = 'position:absolute;left:8px;top:50%;transform:translateY(-50%);z-index:5;width:36px;height:36px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:22px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);transition:background 0.15s;';
    btnPrev.onmouseover = function(){ this.style.background='rgba(91,141,239,0.8)'; };
    btnPrev.onmouseout = function(){ this.style.background='rgba(0,0,0,0.6)'; };
    btnPrev.onclick = function(e){ e.stopPropagation(); window.previewPrev(); };
    viewerWrap.appendChild(btnPrev);

    var btnNext = document.createElement('button');
    btnNext.className = 'preview-nav-btn';
    btnNext.innerHTML = '\u203A';
    btnNext.style.cssText = 'position:absolute;right:8px;top:50%;transform:translateY(-50%);z-index:5;width:36px;height:36px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:22px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);transition:background 0.15s;';
    btnNext.onmouseover = function(){ this.style.background='rgba(91,141,239,0.8)'; };
    btnNext.onmouseout = function(){ this.style.background='rgba(0,0,0,0.6)'; };
    btnNext.onclick = function(e){ e.stopPropagation(); window.previewNext(); };
    viewerWrap.appendChild(btnNext);
  }

  var mainImg = document.createElement('img');
  mainImg.id = 'previewMainImg';
  mainImg.src = cur.src;
  mainImg.alt = cur.name;
  mainImg.style.cssText = 'max-width:100%;max-height:60vh;object-fit:contain;border-radius:8px;cursor:pointer;';
  mainImg.onclick = function(){ window.openLightbox(cur.src, cur.name); };
  viewerWrap.appendChild(mainImg);

  var counter = document.createElement('div');
  counter.className = 'preview-counter';
  counter.id = 'previewCounter';
  counter.textContent = (window.previewIndex + 1) + ' / ' + window.previewImages.length;
  counter.style.cssText = 'position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;font-size:12px;font-weight:600;padding:3px 12px;border-radius:20px;backdrop-filter:blur(4px);z-index:5;';
  viewerWrap.appendChild(counter);

  container.appendChild(viewerWrap);

  var infoRow = document.createElement('div');
  infoRow.id = 'previewInfoRow';
  infoRow.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:6px 2px;';
  infoRow.innerHTML =
    '<span class="result-provider-tag" style="background:' + cur.color + '20;color:' + cur.color + ';">' +
      '<span style="width:6px;height:6px;border-radius:50%;background:' + cur.color + ';display:inline-block;"></span>' +
      ' ' + _eh(cur.name) +
    '</span>' +
    '<div style="display:flex;gap:6px;">' +
      '<a class="btn-ghost" href="' + cur.src + '" download style="font-size:10px;padding:4px 8px;">\u2B07 \u4E0B\u8F7D</a>' +
      '<button class="btn-ghost" onclick="openCompare()" style="font-size:10px;padding:4px 8px;">\u2696 \u5BF9\u6BD4</button>' +
    '</div>';
  container.appendChild(infoRow);

  if (window.previewImages.length > 1) {
    var thumbStrip = document.createElement('div');
    thumbStrip.className = 'thumb-strip';
    thumbStrip.id = 'thumbStrip';
    for (var i = 0; i < window.previewImages.length; i++) {
      (function(idx){
        var img = document.createElement('img');
        img.src = window.previewImages[idx].src;
        img.className = idx === window.previewIndex ? 'active' : '';
        img.style.cssText = 'width:56px;height:56px;object-fit:cover;border-radius:8px;cursor:pointer;opacity:' + (idx === window.previewIndex ? '1' : '0.5') + ';border:2px solid ' + (idx === window.previewIndex ? 'var(--accent)' : 'transparent') + ';transition:all 0.15s;flex-shrink:0;';
        img.onclick = function(){ window.previewIndex = idx; window.renderPreviewViewer(document.getElementById('previewResults')); };
        thumbStrip.appendChild(img);
      })(i);
    }
    container.appendChild(thumbStrip);
  }
};

window.addResultToPreview = function(key, result) {
  var container = document.getElementById('previewResults');
  var emptyEl = document.getElementById('previewEmpty');
  var cnt = document.getElementById('resultCount');
  if (!container) return;
  if (emptyEl) emptyEl.style.display = 'none';

  var pid = result.model || key;
  var realPid = key.replace(/_\d+$/, '');
  var seq = result.seq !== undefined ? result.seq : -1;
  var fname = result.local_path.split(/[\\/]/).pop();
  var pInfo = window.findProvider(pid) || { name: pid, color: '#5b8def' };
  var displayName = pInfo.name + (seq >= 1 ? ' #' + (seq + 1) : '');

  var imgEntry = { pid: pid, realPid: realPid, src: '/api/gallery/image/' + fname, name: displayName, color: pInfo.color, fname: fname };
  window.previewImages.push(imgEntry);
  if (!window.previewGroups[realPid]) window.previewGroups[realPid] = [];
  window.previewGroups[realPid].push(imgEntry);

  var groupCard = document.getElementById('prev_group_' + realPid);
  if (!groupCard) {
    groupCard = document.createElement('div');
    groupCard.id = 'prev_group_' + realPid;
    groupCard.className = 'fade-in';
    groupCard.style.cssText = 'padding:14px;background:var(--bg-surface);border-radius:12px;border:1px solid var(--border);';
    var header = document.createElement('div');
    header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;';
    header.innerHTML =
      '<div style="display:flex;align-items:center;gap:8px;">' +
        '<span style="width:8px;height:8px;border-radius:50%;background:' + pInfo.color + ';display:inline-block;"></span>' +
        '<span style="font-weight:700;font-size:13px;color:var(--text-primary);">' + _eh(window.getProviderDisplayName(realPid)) + '</span>' +
      '</div>' +
      '<span id="prev_grp_cnt_' + realPid + '" style="font-size:11px;color:var(--text-muted);"></span>';
    groupCard.appendChild(header);
    var viewerArea = document.createElement('div');
    viewerArea.id = 'prev_grp_viewer_' + realPid;
    viewerArea.style.cssText = 'position:relative;display:flex;align-items:center;justify-content:center;min-height:180px;overflow:hidden;border-radius:10px;background:var(--bg-card);';
    groupCard.appendChild(viewerArea);
    var thumbRow = document.createElement('div');
    thumbRow.id = 'prev_grp_thumbs_' + realPid;
    thumbRow.style.cssText = 'display:flex;gap:6px;margin-top:8px;overflow-x:auto;';
    groupCard.appendChild(thumbRow);
    container.appendChild(groupCard);
  }

  var viewerArea = document.getElementById('prev_grp_viewer_' + realPid);
  if (viewerArea) {
    viewerArea.innerHTML = '<img src="' + imgEntry.src + '" style="max-width:100%;max-height:300px;border-radius:8px;object-fit:contain;cursor:pointer;" onclick="openLightbox(\'' + imgEntry.src + '\', \'' + displayName.replace(/'/g, "\\'") + '\')">';
  }

  var thumbRow = document.getElementById('prev_grp_thumbs_' + realPid);
  if (thumbRow) {
    var thumb = document.createElement('img');
    thumb.src = imgEntry.src;
    thumb.style.cssText = 'width:56px;height:56px;object-fit:cover;border-radius:6px;border:2px solid ' + pInfo.color + ';cursor:pointer;flex-shrink:0;';
    thumb.onclick = function() {
      window.openLightbox(imgEntry.src, displayName);
    };
    thumbRow.appendChild(thumb);
  }

  var totalSuccess = window.previewImages.length;
  if (cnt) cnt.textContent = totalSuccess + ' \u5F20\u6210\u529F';
};

window.renderGroupedPreview = function(container) {
  try {
  if (!container) { console.error('container is null'); return; }
  container.innerHTML = '';
  if (!window.previewImages || !window.previewImages.length) { return; }

  var scrollWrap = document.createElement('div');
  scrollWrap.style.cssText = 'flex:1;overflow-y:auto;padding:8px 0;display:flex;flex-direction:column;gap:16px;';

  var groupKeys = Object.keys(window.previewGroups);

  for (var g = 0; g < groupKeys.length; g++) {
    (function(rp, groupImgs) {
      var pInfo = window.findProvider(rp) || {name: rp, color: '#5b8def'};
      var groupIdx = 0;

      var groupCard = document.createElement('div');
      groupCard.className = 'fade-in';
      groupCard.style.cssText = 'padding:14px;background:var(--bg-surface);border-radius:12px;border:1px solid var(--border);';

      var header = document.createElement('div');
      header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;';
      header.innerHTML =
        '<div style="display:flex;align-items:center;gap:8px;">' +
          '<span style="width:8px;height:8px;border-radius:50%;background:' + pInfo.color + ';display:inline-block;flex-shrink:0;"></span>' +
          '<span style="font-weight:700;font-size:13px;color:var(--text-primary);">' + _eh(window.getProviderDisplayName(rp)) + '</span>' +
        '</div>' +
        '<div style="display:flex;align-items:center;gap:6px;">' +
          '<span id="grp_cnt_' + rp + '" style="font-size:11px;color:var(--text-muted);">' + (groupIdx+1) + ' / ' + groupImgs.length + '</span>' +
          '<div style="display:flex;gap:4px;">' +
            '<button id="grp_prev_' + rp + '" onclick="groupNav(\'' + rp + '\',-1)" style="width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;line-height:1;">\u2039</button>' +
            '<button id="grp_next_' + rp + '" onclick="groupNav(\'' + rp + '\',1)" style="width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;line-height:1;">\u203A</button>' +
          '</div>' +
        '</div>';
      groupCard.appendChild(header);

      var viewerWrap = document.createElement('div');
      viewerWrap.id = 'grp_viewer_' + rp;
      viewerWrap.style.cssText = 'position:relative;display:flex;align-items:center;justify-content:center;min-height:220px;overflow:hidden;border-radius:10px;background:var(--bg-card);';

      function renderGroupImg() {
        viewerWrap.innerHTML = '';
        var cur = groupImgs[groupIdx];
        var cntEl = document.getElementById('grp_cnt_' + rp);
        if (cntEl) cntEl.textContent = (groupIdx+1) + ' / ' + groupImgs.length;

        if (groupImgs.length > 1) {
          var btnP = document.createElement('button');
          btnP.style.cssText = 'position:absolute;left:8px;top:50%;transform:translateY(-50%);z-index:5;width:34px;height:34px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
          btnP.innerHTML = '\u2039';
          btnP.onclick = function(e){ e.stopPropagation(); window.groupNav(rp,-1); };
          viewerWrap.appendChild(btnP);

          var btnN = document.createElement('button');
          btnN.style.cssText = 'position:absolute;right:8px;top:50%;transform:translateY(-50%);z-index:5;width:34px;height:34px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
          btnN.innerHTML = '\u203A';
          btnN.onclick = function(e){ e.stopPropagation(); window.groupNav(rp,1); };
          viewerWrap.appendChild(btnN);
        }

        var imgEl = document.createElement('img');
        imgEl.id = 'grp_img_' + rp;
        imgEl.src = cur.src;
        imgEl.alt = cur.name;
        imgEl.style.cssText = 'max-width:100%;max-height:55vh;object-fit:contain;border-radius:8px;cursor:pointer;';
        imgEl.onclick = function(){ window.openLightbox(cur.src, cur.name); };
        viewerWrap.appendChild(imgEl);
      }
      renderGroupImg();
      groupCard.appendChild(viewerWrap);

      if (groupImgs.length > 1) {
        var thumbRow = document.createElement('div');
        thumbRow.id = 'grp_thumbs_' + rp;
        thumbRow.style.cssText = 'display:flex;gap:8px;margin-top:10px;overflow-x:auto;padding-bottom:2px;';
        for (var ti = 0; ti < groupImgs.length; ti++) {
          (function(ti) {
            var t = document.createElement('img');
            t.src = groupImgs[ti].src;
            t.alt = groupImgs[ti].name;
            var isActive = ti === groupIdx;
            t.style.cssText = 'width:54px;height:54px;object-fit:cover;border-radius:8px;cursor:pointer;opacity:' + (isActive ? '1' : '0.45') + ';border:2px solid ' + (isActive ? pInfo.color : 'transparent') + ';transition:all 0.15s;flex-shrink:0;';
            t.onclick = function() {
              groupIdx = ti;
              renderGroupImg();
              window.renderGroupThumbs(rp, groupImgs, groupIdx, pInfo.color);
            };
            thumbRow.appendChild(t);
          })(ti);
        }
        groupCard.appendChild(thumbRow);
      }

      window['groupNav'] = window['groupNav'] || {};
      window['groupNav_' + rp] = function(dir) {
        groupIdx = (groupIdx + dir + groupImgs.length) % groupImgs.length;
        renderGroupImg();
        var thumbRow = document.getElementById('grp_thumbs_' + rp);
        if (thumbRow) window.renderGroupThumbs(rp, groupImgs, groupIdx, pInfo.color);
      };

      var gtimings = window.currentGroupTimings[rp];
      if (gtimings && gtimings.images && gtimings.images.length > 0) {
        var tTotal = gtimings.total;
        var timingBar = document.createElement('div');
        timingBar.style.cssText = 'margin-top:10px;padding:6px 0 2px;';
        var timingLabel = document.createElement('div');
        timingLabel.style.cssText = 'display:flex;justify-content:space-between;font-size:10px;color:var(--text-secondary);margin-bottom:4px;';
        timingLabel.innerHTML = '<span>\u23F1 \u8017\u65F6\u5206\u5E03</span><span style="font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums;">' + tTotal.toFixed(1) + 's</span>';
        timingBar.appendChild(timingLabel);
        var segWrap = document.createElement('div');
        segWrap.style.cssText = 'display:flex;height:6px;border-radius:3px;overflow:hidden;gap:2px;';
        var segColors = ['#5b8def','#22d3a5','#a78bfa','#fbbf24','#f87171','#5eead4','#fb923c','#818cf8'];
        for (var si = 0; si < gtimings.images.length; si++) {
          var seg = gtimings.images[si];
          var pct = tTotal > 0 ? (seg.elapsed / tTotal * 100) : (100 / gtimings.images.length);
          var segEl = document.createElement('div');
          var sc = gtimings.images.length === 1 ? pInfo.color : segColors[si % segColors.length];
          segEl.style.cssText = 'flex:' + pct.toFixed(1) + ';border-radius:3px;background:' + sc + ';transition:flex 0.4s ease;position:relative;cursor:default;';
          segEl.title = (gtimings.images.length > 1 ? '\u56FE\u7247 #' + (si+1) + ': ' : '') + seg.elapsed.toFixed(1) + 's (' + Math.round(pct) + '%)';
          segWrap.appendChild(segEl);
        }
        timingBar.appendChild(segWrap);
        if (gtimings.images.length > 1) {
          var legend = document.createElement('div');
          legend.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;';
          for (var li = 0; li < gtimings.images.length; li++) {
            var lc = segColors[li % segColors.length];
            var lt = document.createElement('span');
            lt.style.cssText = 'font-size:9px;color:var(--text-muted);display:inline-flex;align-items:center;gap:3px;';
            lt.innerHTML = '<span style="width:6px;height:6px;border-radius:2px;background:' + lc + ';display:inline-block;"></span>#' + (li+1) + ' ' + gtimings.images[li].elapsed.toFixed(1) + 's';
            legend.appendChild(lt);
          }
          timingBar.appendChild(legend);
        }
        groupCard.appendChild(timingBar);
      }

      scrollWrap.appendChild(groupCard);
    })(groupKeys[g], window.previewGroups[groupKeys[g]]);
  }

  if (window.failedGroups && Object.keys(window.failedGroups).length > 0) {
    var failKeys = Object.keys(window.failedGroups);
    for (var fg = 0; fg < failKeys.length; fg++) {
      (function(rp, failItems) {
        var pInfo = window.findProvider(rp) || {name: rp, color: '#5b8def'};
        var failCard = document.createElement('div');
        failCard.className = 'fade-in';
        failCard.style.cssText = 'padding:14px;background:var(--bg-surface);border-radius:12px;border:1px solid rgba(239,68,68,0.3);';

        var failHeader = document.createElement('div');
        failHeader.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:10px;';
        failHeader.innerHTML =
          '<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;display:inline-block;"></span>' +
          '<span style="font-weight:700;font-size:13px;color:#f87171;">' + _eh(window.getProviderDisplayName(rp)) + '</span>' +
          '<span style="font-size:10px;color:#ef4444;background:rgba(239,68,68,0.15);padding:1px 6px;border-radius:10px;margin-left:4px;">\u2718 ' + failItems.length + ' \u5F20\u5931\u8D25</span>';
        failCard.appendChild(failHeader);

        for (var fi = 0; fi < failItems.length; fi++) {
          var item = failItems[fi];
          var seqLabel = item.seq >= 0 ? ' #' + (item.seq + 1) : '';
          var errRow = document.createElement('div');
          errRow.style.cssText = 'font-size:11px;color:#ef4444;background:rgba(239,68,68,0.08);padding:6px 10px;border-radius:6px;margin-bottom:4px;display:flex;align-items:flex-start;gap:6px;';
          errRow.innerHTML = '<span style="color:#f87171;flex-shrink:0;">\u26A0</span><span>' + (window.getProviderDisplayName(rp) + seqLabel) + ': ' + _eh(item.error || '\u672A\u77E5\u9519\u8BEF') + '</span>';
          failCard.appendChild(errRow);
        }

        scrollWrap.appendChild(failCard);
      })(failKeys[fg], window.failedGroups[failKeys[fg]]);
    }
  }

  container.appendChild(scrollWrap);
  } catch(e) { console.error('[renderGroupedPreview] error:', e); alert('renderGroupedPreview error: ' + e.message); }
};

window.groupNav = function(rp, dir) {
  var fn = window['groupNav_' + rp];
  if (fn) fn(dir);
};

window.renderGroupThumbs = function(rp, groupImgs, activeIdx, color) {
  var row = document.getElementById('grp_thumbs_' + rp);
  if (!row) return;
  var thumbs = row.querySelectorAll('img');
  for (var t = 0; t < thumbs.length; t++) {
    var isActive = t === activeIdx;
    thumbs[t].style.opacity = isActive ? '1' : '0.45';
    thumbs[t].style.borderColor = isActive ? color : 'transparent';
  }
};

window.previewPrev = function() {
  if (!window.previewImages.length) return;
  window.previewIndex = (window.previewIndex - 1 + window.previewImages.length) % window.previewImages.length;
  window.renderPreviewViewer(document.getElementById('previewResults'));
};
window.previewNext = function() {
  if (!window.previewImages.length) return;
  window.previewIndex = (window.previewIndex + 1) % window.previewImages.length;
  window.renderPreviewViewer(document.getElementById('previewResults'));
};

window.findProvider = function(pid) {
  for (var i=0;i<window.allProviders.length;i++) {
    if (window.allProviders[i].id === pid) return window.allProviders[i];
  }
  var basePid = pid.replace(/_\d+$/, '');
  if (basePid !== pid) {
    for (var j=0;j<window.allProviders.length;j++) {
      if (window.allProviders[j].id === basePid) return window.allProviders[j];
    }
  }
  return null;
};

window.getProviderDisplayName = function(pid) {
  var pInfo = window.findProvider(pid) || {name: pid, display_name: ''};
  return pInfo.display_name || pInfo.name || pid;
};

/* ═══════════════════════════════════════════════════════════════════
   Quick Prompts
   ═══════════════════════════════════════════════════════════════════ */
window.renderQuickPrompts = function() {
  var area = document.getElementById('quickArea');
  window.quickPrompts = {};

  for (var cat in window.QUICK_PROMPTS) {
    var section = document.createElement('div');
    section.className = 'quick-section';

    var tagsId = 'qt_' + cat.replace(/[^a-z]/gi,'_');

    section.innerHTML =
      '<div class="quick-section-header" onclick="toggleQuickSection(this)">' +
        '<div class="quick-section-title"><span>' + cat + '</span><span style="font-size:10px;color:var(--text-muted);font-weight:400;">(' + window.QUICK_PROMPTS[cat].length + ')</span></div>' +
        '<span class="quick-chevron open">\u25BC</span>' +
      '</div>' +
      '<div class="quick-tags" id="' + tagsId + '">' +
        window.QUICK_PROMPTS[cat].map(function(t){
          return '<button class="quick-tag" onclick="insertQuickPrompt(this)" data-en="' + _eh(t.en) + '">' + _eh(t.label) + '</button>';
        }).join('') +
      '</div>';

    area.appendChild(section);
    window.quickPrompts[cat] = { el: section, open: true };
  }
};

window.toggleQuickSection = function(header) {
  var chevron = header.querySelector('.quick-chevron');
  var tags = header.nextElementSibling;
  var isOpen = chevron.classList.contains('open');

  if (isOpen) {
    chevron.classList.remove('open');
    tags.classList.add('collapsed');
    tags.style.maxHeight = tags.scrollHeight + 'px';
    requestAnimationFrame(function(){ tags.classList.add('collapsed'); });
  } else {
    tags.style.maxHeight = tags.scrollHeight + 'px';
    tags.classList.remove('collapsed');
    chevron.classList.add('open');
  }
};

window.filterQuickPrompts = function(query) {
  query = query.trim().toLowerCase();
  for (var cat in window.quickPrompts) {
    var tags = window.quickPrompts[cat].el.querySelector('.quick-tags');
    var btns = tags.querySelectorAll('.quick-tag');
    var visibleCount = 0;
    btns.forEach(function(btn){
      var label = btn.textContent.toLowerCase();
      var enText = (btn.getAttribute('data-en') || '').toLowerCase();
      var match = !query || label.indexOf(query) !== -1 || enText.indexOf(query) !== -1;
      btn.style.display = match ? '' : 'none';
      if (match) visibleCount++;
    });
    if (query) {
      tags.classList.remove('collapsed');
      tags.style.maxHeight = tags.scrollHeight + 'px';
      window.quickPrompts[cat].el.querySelector('.quick-chevron').classList.add('open');
    }
    window.quickPrompts[cat].el.style.display = visibleCount > 0 ? '' : 'none';
  }
};

window.insertQuickPrompt = function(btn) {
  var text = btn.getAttribute('data-en') || btn.textContent;
  if (window.currentMode === 't2i') {
    var ta = document.getElementById('txtPrompt');
    if (ta.value.trim()) {
      ta.value += ' \u00B7 ' + text;
    } else {
      ta.value = text;
    }
    ta.focus();
  } else {
    var ta2 = document.getElementById('txtPromptI2I');
    if (ta2.value.trim()) {
      ta2.value += ' \u00B7 ' + text;
    } else {
      ta2.value = text;
    }
    ta2.focus();
  }
};

})();
