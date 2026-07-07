(function(){
'use strict';

function _af(url, opts) { return window._authFetch(url, opts); }
function _eh(s) { return window.escHtml(s); }
function _ea(s) { return window.escAttr(s); }

/* ═══════════════════════════════════════════════════════════════════
   Video State
   ═══════════════════════════════════════════════════════════════════ */
window.videoProviders = [];
window.currentVideoMode = 'ti2vid';
window.videoImageRole = 'first_frame';
window.videoImages = [];
window.kfImages = [];
window.videoPollTimer = null;
window.videoElapsedTimer = null;
window.videoStartTime = 0;
window.currentVideoTaskId = null;
window.videoHistoryItems = [];
window.selectedVideoProviderIds = [];
window.videoPreviewGroups = {};
window.videoGroupNavIdx = {};
window.videoActivePollTasks = {};

/* ═══════════════════════════════════════════════════════════════════
   Video Log
   ═══════════════════════════════════════════════════════════════════ */
window.videoLog = function(msg, type) {
  var wrap = document.getElementById('videoLogWrap');
  var area = document.getElementById('videoLogArea');
  if (!wrap || !area) return;
  wrap.style.display = 'block';
  var ts = new Date().toLocaleTimeString();
  var colors = { info: 'var(--text-muted)', ok: '#22c55e', warn: '#f59e0b', error: '#ef4444' };
  var color = colors[type] || colors.info;
  var prefix = type === 'ok' ? '\u2714' : type === 'error' ? '\u2718' : type === 'warn' ? '\u26A0' : '\u25B8';
  var line = document.createElement('div');
  line.style.cssText = 'color:' + color + ';';
  line.textContent = '[' + ts + '] ' + prefix + ' ' + msg;
  area.appendChild(line);
  window._smartScroll(area);
};

window.clearVideoLog = function() {
  var area = document.getElementById('videoLogArea');
  if (area) area.innerHTML = '';
  var hasActiveTasks = window.videoPollTimer !== null || Object.keys(window.videoActivePollTasks || {}).length > 0;
  if (hasActiveTasks) {
    document.querySelectorAll('[id^="vlog_"]').forEach(function(el) { el.innerHTML = ''; });
  } else {
    var section = document.getElementById('videoPerProviderSection');
    if (section) { section.style.display = 'none'; section.innerHTML = ''; }
  }
};

window.videoLogProvider = function(providerId, msg, type) {
  var mini = document.getElementById('vlog_' + providerId);
  if (mini) {
    mini.style.display = 'block';
    var ts = new Date().toLocaleTimeString();
    var colors = { info: 'var(--text-muted)', ok: '#22c55e', warn: '#f59e0b', error: '#ef4444' };
    var color = colors[type] || colors.info;
    var prefix = type === 'ok' ? '\u2714' : type === 'error' ? '\u2718' : type === 'warn' ? '\u26A0' : '\u25B8';
    var line = document.createElement('div');
    line.style.cssText = 'color:' + color + ';';
    var stage = '';
    if (msg.indexOf('\u521B\u5EFA') !== -1) stage = '[\u63D0\u4EA4] ';
    else if (msg.indexOf('\u5F00\u59CB') !== -1) stage = '[\u751F\u6210] ';
    else if (msg.indexOf('\u5B8C\u6210') !== -1) stage = '[\u5B8C\u6210] ';
    else if (msg.indexOf('\u5931\u8D25') !== -1 || msg.indexOf('\u51FA\u9519') !== -1) stage = '[\u9519\u8BEF] ';
    else if (msg.indexOf('\u8F6E\u8BE2') !== -1) stage = '[\u8F6E\u8BE2] ';
    line.textContent = '[' + ts + '] ' + stage + prefix + ' ' + msg;
    mini.appendChild(line);
    window._smartScroll(mini);
  }
  window.videoLog(msg, type);
};

/* ═══════════════════════════════════════════════════════════════════
   Video Provider Drag Sort
   ═══════════════════════════════════════════════════════════════════ */
var videoDragProviderId = null;

window.onVideoProviderDragStart = function(e, pid) {
  videoDragProviderId = pid;
  e.dataTransfer.effectAllowed = 'move';
  document.getElementById('vcard_' + pid).classList.add('dragging');
};

window.onVideoProviderDragOver = function(e, pid) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  document.getElementById('vcard_' + pid).classList.add('drag-over');
};

window.onVideoProviderDrop = function(e, pid) {
  e.preventDefault();
  if (!videoDragProviderId || videoDragProviderId === pid) return;
  var fromId = videoDragProviderId;
  var toId = pid;
  var fromIdx = window.videoProviders.findIndex(function(p){ return p.id === fromId; });
  var toIdx = window.videoProviders.findIndex(function(p){ return p.id === toId; });
  if (fromIdx < 0 || toIdx < 0) return;
  var item = window.videoProviders.splice(fromIdx, 1)[0];
  window.videoProviders.splice(toIdx, 0, item);
  var selFrom = window.selectedVideoProviderIds.indexOf(fromId);
  var selTo = window.selectedVideoProviderIds.indexOf(toId);
  if (selFrom >= 0 && selTo >= 0) {
    window.selectedVideoProviderIds.splice(selFrom, 1);
    window.selectedVideoProviderIds.splice(selTo, 0, fromId);
  }
  window.saveProviderOrder();
  window.renderVideoProviderCards();
};

window.resetVideoDragStyle = function() {
  videoDragProviderId = null;
  document.querySelectorAll('.dragging, .drag-over').forEach(function(el){ el.classList.remove('dragging', 'drag-over'); });
};

/* ═══════════════════════════════════════════════════════════════════
   Video Provider Loading
   ═══════════════════════════════════════════════════════════════════ */
window.loadVideoProviders = function() {
  _af('/api/providers').then(function(r){ return r.json(); }).then(function(data){
    window.videoProviders = (data.providers || []).filter(function(p){ return p.type === 'video'; });
    window.renderVideoProviderCards();
  });
};

window.videoGlobalSettings = {
  size: '1152x768', fps: 24, frames: 121,
  customW: 1152, customH: 768,
  steps: null, seed: null
};

window.getVideoProviderCapabilities = function(p) {
  var caps = p.model_capabilities || {};
  var allModels = p.models && p.models.length > 0 ? p.models : (p.model ? [p.model] : []);
  var capSet = {};
  allModels.forEach(function(m) {
    var mc = caps[m] || [];
    if (mc.length === 0) {
      var ml = m.toLowerCase();
      if (ml.indexOf('t2v') !== -1 && ml.indexOf('i2v') === -1 && ml.indexOf('interpolation') === -1) mc.push('t2v', 'ti2vid');
      if (ml.indexOf('i2v') !== -1) mc.push('i2v');
      if (ml.indexOf('interpolation') !== -1) mc.push('keyframes');
    }
    mc.forEach(function(c) { capSet[c] = true; });
  });
  return capSet;
};

window.isModelMatchMode = function(modelName, mode) {
  var ml = (modelName || '').toLowerCase();
  if (mode === 'ti2vid') {
    if (ml.indexOf('t2v') !== -1 && ml.indexOf('i2v') === -1 && ml.indexOf('interpolation') === -1) return true;
    if (ml.indexOf('r2v') !== -1) return true;
    return false;
  }
  if (mode === 'i2vid') {
    if (ml.indexOf('i2v') !== -1) return true;
    return false;
  }
  if (mode === 'keyframes') {
    if (ml.indexOf('interpolation') !== -1) return true;
    return false;
  }
  return true;
};

window.renderVideoProviderCards = function() {
  var container = document.getElementById('videoProviderCards');
  if (!container) return;
  if (!window.videoProviders || window.videoProviders.length === 0) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px 0;">&#35831;&#20808;&#22312;&#35774;&#32622;&#20013;&#28155;&#21152;&#35270;&#39057; Provider</div>';
    return;
  }
  var html = '';
  var activeMode = window.currentVideoMode || 'ti2vid';
  for (var i = 0; i < window.videoProviders.length; i++) {
    (function(p, idx) {
      var isSelected = window.selectedVideoProviderIds.indexOf(p.id) !== -1;
      var cardBg = isSelected ? 'var(--bg-card)' : 'var(--bg-surface)';
      var borderColor = isSelected ? p.color : 'var(--border)';
      var allModels = p.models && p.models.length > 0 ? p.models : (p.model ? [p.model] : []);
      var filteredModels = allModels.filter(function(m) { return window.isModelMatchMode(m, activeMode); });
      if (filteredModels.length === 0) filteredModels = allModels;
      var modelOpts = filteredModels.length > 3
        ? window.buildModelOptsGrouped(filteredModels, '', window.groupVideoModels)
        : filteredModels.map(function(m){ return '<option value="' + _ea(m) + '">' + _eh(m) + '</option>'; }).join('');
      var capSet = window.getVideoProviderCapabilities(p);
      var capBadges = '';
      if (capSet['t2v'] || capSet['ti2vid']) {
        capBadges += '<span style="font-size:9px;padding:1px 4px;border-radius:3px;background:var(--accent);color:#fff;margin-right:3px;">T2V</span>';
      }
      if (capSet['i2v']) {
        capBadges += '<span style="font-size:9px;padding:1px 4px;border-radius:3px;background:#9b59b6;color:#fff;margin-right:3px;">I2V</span>';
      }
      if (capSet['keyframes']) {
        capBadges += '<span style="font-size:9px;padding:1px 4px;border-radius:3px;background:#e67e22;color:#fff;margin-right:3px;">KF</span>';
      }
      html += '<div id="vcard_' + p.id + '" draggable="true" ondragstart="onVideoProviderDragStart(event, \'' + p.id + '\')" ondragover="onVideoProviderDragOver(event, \'' + p.id + '\')" ondrop="onVideoProviderDrop(event, \'' + p.id + '\')" ondragend="resetVideoDragStyle()" style="margin-bottom:8px;border-radius:8px;border:1px solid ' + borderColor + ';background:' + cardBg + ';padding:10px;transition:all 0.2s;">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">' +
          '<div style="display:flex;align-items:center;gap:6px;">' +
            '<input type="checkbox" id="vcheck_' + p.id + '" onclick="toggleVideoProvider(\'' + p.id + '\')" ' + (isSelected ? 'checked' : '') + ' style="cursor:pointer;width:14px;height:14px;accent-color:' + p.color + ';">' +
            '<span style="width:7px;height:7px;border-radius:50%;background:' + p.color + ';display:inline-block;"></span>' +
            (p.id.indexOf('gemini') !== -1
              ? '<span style="font-size:12px;font-weight:700;background:linear-gradient(90deg,#4285f4,#ea4335,#fbbc04,#34a853);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">Gemini Video</span>' +
                '<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:var(--accent);color:#fff;margin-left:4px;">\u63A8\u8350</span>'
              : '<span style="font-size:12px;font-weight:600;color:var(--text-primary);">' + _eh(window.getProviderDisplayName(p.id)) + '</span>' +
                '<span style="font-size:10px;color:var(--text-muted);">' + _eh(p.name) + '</span>'
            ) +
          '</div>' +
          '<div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">' +
            capBadges +
            '<button onclick="refreshProviderModels(\'' + p.id + '\')" title="&#21047;&#26032;&#27169;&#22411;" style="font-size:10px;padding:2px 6px;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-secondary);cursor:pointer;">&#8635;</button>' +
          '</div>' +
        '</div>' +
        '<div style="display:flex;gap:4px;margin-bottom:6px;">' +
          '<div style="flex:1;">' +
            '<div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">&#27169;&#22411; <span style="color:var(--accent);font-size:9px;">(' + (activeMode === 'ti2vid' ? '\u6587\u751F\u89C6\u9891' : activeMode === 'i2vid' ? '\u56FE\u751F\u89C6\u9891' : '\u5173\u952E\u5E27') + ')</span></div>' +
            '<select id="vmodel_' + p.id + '" onchange="onVideoModelChange()" ' + (!isSelected ? 'disabled' : '') + ' style="width:100%;font-size:11px;padding:5px 8px;background:var(--bg-base);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);' + (!isSelected ? 'opacity:0.5;' : '') + '">' +
              (modelOpts || '<option value="">&#26080;&#21487;&#29992;&#27169;&#22411;</option>') +
            '</select>' +
          '</div>' +
        '</div>' +
      '</div>';
    })(window.videoProviders[i], i);
  }
  html = '<div style="font-size:10px;color:var(--text-muted);margin-bottom:8px;">&#21452;&#20987;&#22810;&#20010; Provider &#21487;&#21516;&#26102;&#21521;&#22810;&#20010;&#27169;&#22411;&#25552;&#20132;&#20219;&#52;</div>' + html;
  container.innerHTML = html;
  window.updateVideoGenerateButton();
};

window.toggleVideoProvider = function(vpid) {
  var idx = window.selectedVideoProviderIds.indexOf(vpid);
  if (idx !== -1) {
    window.selectedVideoProviderIds.splice(idx, 1);
  } else {
    window.selectedVideoProviderIds.push(vpid);
  }
  window.renderVideoProviderCards();
};

window.updateVideoGenerateButton = function() {
  var btn = document.getElementById('videoGenBtn');
  if (!btn) return;
  var count = window.selectedVideoProviderIds.length;
  if (count === 0) {
    btn.textContent = '\u{1F680} \u9009\u62E9 Provider \u540E\u751F\u6210';
    btn.disabled = true;
  } else if (count === 1) {
    btn.textContent = '\u{1F680} \u751F\u6210\u89C6\u9891';
    btn.disabled = false;
  } else {
    btn.textContent = '\u{1F680} \u540C\u65F6\u5411 ' + count + ' \u4E2A Provider \u63D0\u4EA4';
    btn.disabled = false;
  }
};

window.onVideoModelChange = function(event) {
  var sel = event && event.target;
  if (!sel) return;
  var val = sel.value || '';
  var sizeMap = {
    'landscape': '1152x768',
    'portrait': '768x1152',
    'square': '1024x1024',
    'four_three': '1024x768',
    'three_four': '768x1024',
    '2k': '2048x1024',
    '4k': '3840x2160',
    'ultra': '1920x1080'
  };
  var sizeSel = document.getElementById('videoSize');
  var customSize = document.getElementById('videoCustomSize');
  var wInput = document.getElementById('videoWidth');
  var hInput = document.getElementById('videoHeight');
  if (sizeSel && wInput && hInput) {
    var matched = false;
    for (var key in sizeMap) {
      if (val.toLowerCase().indexOf(key) !== -1) {
        var parts = sizeMap[key].split('x');
        wInput.value = parts[0];
        hInput.value = parts[1];
        sizeSel.value = 'custom';
        if (customSize) customSize.style.display = 'flex';
        matched = true;
        break;
      }
    }
    if (!matched && val.indexOf('ultra') !== -1) {
      wInput.value = 1920; hInput.value = 1080;
      sizeSel.value = 'custom';
      if (customSize) customSize.style.display = 'flex';
    }
  }
};

window.onVideoSizeChange = function() {
  var sel = document.getElementById('videoSize');
  var custom = document.getElementById('videoCustomSize');
  if (sel.value === 'custom') {
    custom.style.display = 'flex';
  } else {
    custom.style.display = 'none';
  }
};

window.getVideoDimensions = function() {
  var sel = document.getElementById('videoSize');
  if (sel.value === 'custom') {
    return {
      width: parseInt(document.getElementById('videoCustomW').value) || 1152,
      height: parseInt(document.getElementById('videoCustomH').value) || 768
    };
  }
  var parts = sel.value.split('x');
  return { width: parseInt(parts[0]), height: parseInt(parts[1]) };
};

window.setVideoDuration = function(frames, fps, el) {
  document.getElementById('videoFrames').value = frames;
  document.getElementById('videoFPS').value = fps;
  el.parentElement.querySelectorAll('.sub-tab').forEach(function(t){ t.classList.remove('active'); });
  el.classList.add('active');
};

window.toggleVideoAdvanced = function() {
  var adv = document.getElementById('videoAdvanced');
  var chevron = document.getElementById('videoAdvChevron');
  if (adv.style.display === 'none') {
    adv.style.display = 'block';
    chevron.textContent = '\u25BC';
  } else {
    adv.style.display = 'none';
    chevron.textContent = '\u25B6';
  }
};

window.refreshProviderModels = function(vpid) {
  var prov = window.videoProviders.find(function(p){ return p.id === vpid; });
  if (!prov || !prov.models_url) return;
  var btn = document.querySelector('#vcard_' + vpid + ' button[onclick*="refresh"]');
  if (btn) { btn.textContent = '...'; btn.disabled = true; }
  fetch(prov.models_url).then(function(r){ return r.json(); }).then(function(data) {
    var models = data.models || data.items || [];
    prov.models = models;
    prov.model_capabilities = data.model_capabilities || prov.model_capabilities || {};
    var sel = document.getElementById('vmodel_' + vpid);
    if (sel) {
      sel.innerHTML = models.map(function(m){ return '<option value="' + m + '">' + m + '</option>'; }).join('') || '<option value="">\u65E0\u53EF\u7528\u6A21\u578B</option>';
    }
    window.renderVideoProviderCards();
    window.setStatus(prov.name + ' \u6A21\u578B\u5DF2\u5237\u65B0 (' + models.length + '\u4E2A)');
  }).catch(function(e) {
    if (btn) { btn.textContent = '\u21BB'; btn.disabled = false; }
    window.setStatus('\u6A21\u578B\u5237\u65B0\u5931\u8D25: ' + e.message);
  });
};

window.switchVideoSubTab = function(mode) {
  window.currentVideoMode = mode;
  document.getElementById('vSubTabTi2vid').classList.toggle('active', mode === 'ti2vid');
  document.getElementById('vSubTabI2vid').classList.toggle('active', mode === 'i2vid');
  document.getElementById('vSubTabKeyframes').classList.toggle('active', mode === 'keyframes');
  document.getElementById('videoI2VPanel').style.display = (mode === 'i2vid') ? 'block' : 'none';
  document.getElementById('videoKeyframesPanel').style.display = (mode === 'keyframes') ? 'block' : 'none';

  if (mode !== 'i2vid' && window.videoImages.length > 0) {
    window.videoImages = [];
    document.getElementById('videoImagePreview').innerHTML = '';
  }
  if (mode !== 'keyframes' && window.kfImages.length > 0) {
    window.kfImages = [];
    document.getElementById('kfImagePreview').innerHTML = '';
  }

  if (mode === 'i2vid') {
    var unsupported = window.selectedVideoProviderIds.filter(function(vpid) {
      var prov = window.videoProviders.find(function(p){ return p.id === vpid; });
      if (!prov) return true;
      var caps = window.getVideoProviderCapabilities(prov);
      return !caps['i2v'];
    });
    if (unsupported.length > 0) {
      window.setStatus('\u26A0 \u90E8\u5206\u9009\u4E2D Provider \u4E0D\u652F\u6301\u56FE\u751F\u89C6\u9891\u6A21\u5F0F');
    }
  }
  if (mode === 'keyframes') {
    var unsupported = window.selectedVideoProviderIds.filter(function(vpid) {
      var prov = window.videoProviders.find(function(p){ return p.id === vpid; });
      if (!prov) return true;
      var caps = window.getVideoProviderCapabilities(prov);
      return !caps['keyframes'];
    });
    if (unsupported.length > 0) {
      window.setStatus('\u26A0 \u90E8\u5206\u9009\u4E2D Provider \u4E0D\u652F\u6301\u5173\u952E\u5E27\u6A21\u5F0F');
    }
  }
  window.renderVideoProviderCards();
};

window.setVideoImageRole = function(role, el) {
  window.videoImageRole = role;
  el.parentElement.querySelectorAll('.sub-tab').forEach(function(t){ t.classList.remove('active'); });
  el.classList.add('active');
};

/* ═══════════════════════════════════════════════════════════════════
   Video Image Upload
   ═══════════════════════════════════════════════════════════════════ */
window.handleVideoFileSelect = function(evt) {
  var files = evt.target.files;
  for (var i = 0; i < files.length; i++) {
    window.readVideoImageFile(files[i]);
  }
};

window.handleVideoDrop = function(evt) {
  evt.preventDefault();
  evt.currentTarget.classList.remove('dragover');
  var files = evt.dataTransfer.files;
  for (var i = 0; i < files.length; i++) {
    if (files[i].type.startsWith('image/')) window.readVideoImageFile(files[i]);
  }
};

window.readVideoImageFile = function(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    window.videoImages.push(e.target.result);
    window.renderVideoImagePreview();
  };
  reader.readAsDataURL(file);
};

window.renderVideoImagePreview = function() {
  var container = document.getElementById('videoImagePreview');
  container.innerHTML = '';
  window.videoImages.forEach(function(img, idx) {
    var div = document.createElement('div');
    div.style.cssText = 'position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden;border:1px solid var(--border);';
    div.innerHTML = '<img src="' + img + '" style="width:100%;height:100%;object-fit:cover;">' +
      '<div onclick="removeVideoImage(' + idx + ')" style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,0.7);color:#fff;width:18px;height:18px;border-radius:50%;text-align:center;line-height:18px;font-size:11px;cursor:pointer;">\u2715</div>' +
      '<div style="position:absolute;bottom:2px;left:2px;font-size:9px;background:rgba(0,0,0,0.7);color:#fff;padding:1px 4px;border-radius:3px;">' + (idx === 0 ? '\u9996' : idx === window.videoImages.length-1 && window.videoImages.length > 1 ? '\u5C3E' : '\u56FE' + (idx+1)) + '</div>';
    container.appendChild(div);
  });
};

window.removeVideoImage = function(idx) {
  window.videoImages.splice(idx, 1);
  window.renderVideoImagePreview();
};

/* ═══════════════════════════════════════════════════════════════════
   Keyframes Image Upload
   ═══════════════════════════════════════════════════════════════════ */
window.handleKfFileSelect = function(evt) {
  var files = evt.target.files;
  for (var i = 0; i < files.length; i++) {
    window.readKfImageFile(files[i]);
  }
};

window.handleKfDrop = function(evt) {
  evt.preventDefault();
  evt.currentTarget.classList.remove('dragover');
  var files = evt.dataTransfer.files;
  for (var i = 0; i < files.length; i++) {
    if (files[i].type.startsWith('image/')) window.readKfImageFile(files[i]);
  }
};

window.readKfImageFile = function(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    window.kfImages.push(e.target.result);
    window.renderKfImagePreview();
  };
  reader.readAsDataURL(file);
};

window.renderKfImagePreview = function() {
  var container = document.getElementById('kfImagePreview');
  container.innerHTML = '';
  window.kfImages.forEach(function(img, idx) {
    var div = document.createElement('div');
    div.style.cssText = 'position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden;border:1px solid var(--border);';
    div.innerHTML = '<img src="' + img + '" style="width:100%;height:100%;object-fit:cover;">' +
      '<div onclick="removeKfImage(' + idx + ')" style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,0.7);color:#fff;width:18px;height:18px;border-radius:50%;text-align:center;line-height:18px;font-size:11px;cursor:pointer;">\u2715</div>' +
      '<div style="position:absolute;bottom:2px;left:2px;font-size:9px;background:rgba(0,0,0,0.7);color:#fff;padding:1px 4px;border-radius:3px;">\u5E27' + (idx+1) + '</div>';
    container.appendChild(div);
  });
};

window.removeKfImage = function(idx) {
  window.kfImages.splice(idx, 1);
  window.renderKfImagePreview();
};

/* ═══════════════════════════════════════════════════════════════════
   Video Image Picker
   ═══════════════════════════════════════════════════════════════════ */
window.openVideoPreviewPicker = function() {
  window.setStatus('\u6B63\u5728\u52A0\u8F7D\u56FE\u5E93\u56FE\u7247...');
  _af('/api/preview/images').then(function(r){ return r.json(); }).then(function(data){
    var items = data.items || [];
    if (items.length === 0) {
      alert('\u56FE\u5E93\u6682\u65E0\u56FE\u7247\uFF0C\u8BF7\u5148\u751F\u6210\u56FE\u7247');
      return;
    }
    window.showVideoImagePickerModal(items);
  }).catch(function(e){ alert('\u52A0\u8F7D\u5931\u8D25: ' + e.message); });
};

window.showVideoImagePickerModal = function(items) {
  var overlay = document.createElement('div');
  overlay.id = 'videoPickerOverlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
  var box = document.createElement('div');
  box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:20px;max-width:600px;width:90%;max-height:70vh;overflow-y:auto;';
  box.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><h3 style="font-size:14px;font-weight:700;">\u{1F3AF} \u9009\u62E9\u56FE\u7247</h3><button onclick="document.getElementById(\'videoPickerOverlay\').remove()" style="background:none;border:none;color:var(--text-secondary);font-size:18px;cursor:pointer;">\u2715</button></div>' +
    '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;" id="videoPickerGrid"></div>';
  overlay.appendChild(box);
  document.body.appendChild(overlay);

  var grid = document.getElementById('videoPickerGrid');
  items.forEach(function(item) {
    var card = document.createElement('div');
    card.style.cssText = 'border-radius:8px;overflow:hidden;border:2px solid var(--border);cursor:pointer;transition:border-color 0.15s;';
    card.innerHTML = '<img src="' + item.data + '" style="width:100%;height:90px;object-fit:cover;">' +
      '<div style="font-size:9px;color:var(--text-muted);padding:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + (item.prompt || item.filename).substring(0, 30) + '</div>';
    card.onmouseover = function() { card.style.borderColor = 'var(--accent)'; };
    card.onmouseout = function() { card.style.borderColor = 'var(--border)'; };
    card.onclick = function() {
      if (window.currentVideoMode === 'keyframes') {
        window.kfImages.push(item.data);
        window.renderKfImagePreview();
      } else {
        window.videoImages.push(item.data);
        window.renderVideoImagePreview();
      }
      document.getElementById('videoPickerOverlay').remove();
      window.setStatus('\u5DF2\u6DFB\u52A0\u56FE\u7247');
    };
    grid.appendChild(card);
  });
};

/* ═══════════════════════════════════════════════════════════════════
   Video Generation
   ═══════════════════════════════════════════════════════════════════ */
window.startVideoGenerate = function() {
  var prompt = document.getElementById('videoPrompt').value.trim();
  if (!prompt) { alert('\u8BF7\u8F93\u5165\u89C6\u9891\u63D0\u793A\u8BCD'); return; }

  if (window.selectedVideoProviderIds.length === 0) {
    alert('\u8BF7\u5148\u9009\u62E9\u81F3\u5C11\u4E00\u4E2A\u89C6\u9891 Provider');
    return;
  }
  var tasksToGenerate = [];
  for (var vi = 0; vi < window.selectedVideoProviderIds.length; vi++) {
    (function(vpid) {
      var sel = document.getElementById('vmodel_' + vpid);
      if (!sel || sel.disabled || !sel.value) return;
      tasksToGenerate.push({ provider_id: vpid, model: sel.value });
    })(window.selectedVideoProviderIds[vi]);
  }
  if (tasksToGenerate.length === 0) {
    alert('\u8BF7\u4E3A\u6BCF\u4E2A\u9009\u4E2D\u7684 Provider \u9009\u62E9\u89C6\u9891\u6A21\u578B');
    return;
  }

  var dims = window.getVideoDimensions();
  var frames = parseInt(document.getElementById('videoFrames').value) || 121;
  var fps = parseInt(document.getElementById('videoFPS').value) || 24;
  var steps = document.getElementById('videoSteps').value ? parseInt(document.getElementById('videoSteps').value) : null;
  var seed = document.getElementById('videoSeed').value ? parseInt(document.getElementById('videoSeed').value) : null;
  var negPrompt = document.getElementById('videoNegPrompt').value.trim() || null;

  var mode = window.currentVideoMode;
  var images = null;
  var imageRole = null;

  if (mode === 'keyframes') {
    if (window.kfImages.length > 0) images = window.kfImages;
  } else if (mode === 'i2vid') {
    if (window.videoImages.length > 0) {
      images = window.videoImages;
      imageRole = window.videoImageRole;
    }
  }

  if ((frames - 1) % 8 !== 0) {
    var corrected = Math.round((frames - 1) / 8) * 8 + 1;
    if (!confirm('\u5E27\u6570 ' + frames + ' \u4E0D\u7B26\u5408 8n+1 \u89C4\u5219\uFF0C\u5DF2\u4FEE\u6B63\u4E3A ' + corrected + '\u3002\u7EE7\u7EED\u5417\uFF1F')) return;
    frames = corrected;
    document.getElementById('videoFrames').value = frames;
  }

  var btn = document.getElementById('videoGenBtn');
  btn.disabled = true;
  btn.textContent = '\u23F3 \u63D0\u4EA4\u4E2D...';
  document.getElementById('videoProgressBar').style.display = 'block';
  var fill = document.getElementById('videoProgressFill');
  fill.style.width = '0%';
  fill.style.background = '';
  fill.className = 'video-progress-marquee';
  document.getElementById('videoProgressText').textContent = '0%';
  document.getElementById('videoElapsed').textContent = '\u5DF2\u7528\u65F6 0s';
  window.clearVideoLog();
  window.renderVideoPerProviderBars();
  window.videoPreviewGroups = {};
  window.videoGroupNavIdx = {};
  window.videoLog('\u5F00\u59CB\u751F\u6210\u89C6\u9891 - ' + tasksToGenerate.length + ' \u4E2A Provider', 'info');
  window.videoLog('\u63D0\u793A\u8BCD: ' + prompt.substring(0, 80) + (prompt.length > 80 ? '...' : ''), 'info');
  window.videoLog('\u53C2\u6570: ' + dims.width + 'x' + dims.height + ', ' + frames + '\u5E27, ' + fps + 'fps', 'info');

  var submittedCount = 0;
  var totalTasks = tasksToGenerate.length;
  var startTime = Date.now();
  window.videoStartTime = startTime;
  var allTaskData = [];

  window.startVideoElapsedTimer();

  function submitNextTask() {
    if (submittedCount >= totalTasks) {
      window.videoLog('\u5168\u90E8\u63D0\u4EA4\u5B8C\u6210\uFF0C\u5F00\u59CB\u8F6E\u8BE2\u72B6\u6001...', 'info');
      window.startVideoPolling(allTaskData, startTime);
      return;
    }
    var task = tasksToGenerate[submittedCount];
    var payload = {
      prompt: prompt,
      provider_id: task.provider_id,
      model: task.model,
      mode: mode,
      width: dims.width,
      height: dims.height,
      num_frames: frames,
      frame_rate: fps,
    };
    if (images) payload.image = images;
    if (imageRole) payload.image_role = imageRole;
    if (steps) payload.num_inference_steps = steps;
    if (seed !== null) payload.seed = seed;
    if (negPrompt) payload.negative_prompt = negPrompt;

    submittedCount++;
    btn.textContent = '\u23F3 \u5411 ' + submittedCount + '/' + totalTasks + ' \u63D0\u4EA4...';
    document.getElementById('videoTaskStatus').textContent = '\u5DF2\u63D0\u4EA4 ' + submittedCount + '/' + totalTasks;
    var vprogFill = document.getElementById('vprog_fill_' + task.provider_id);
    if (vprogFill) { vprogFill.style.width = '0%'; vprogFill.classList.remove('complete', 'marquee'); }
    var labelEl = document.getElementById('vprog_label_' + task.provider_id);
    if (labelEl) labelEl.textContent = '\u63D0\u4EA4\u4E2D...';
    window.videoLogProvider(task.provider_id, '\u5F00\u59CB\u751F\u6210 - \u6A21\u578B: ' + task.model + ', \u89C4\u683C: ' + payload.width + 'x' + payload.height + ', ' + payload.num_frames + '\u5E27', 'info');

  _af('/api/video/generate', {
    method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || '\u8BF7\u6C42\u5931\u8D25'); });
      return r.json();
    }).then(function(data) {
      data.provider_id = task.provider_id;
      allTaskData.push(data);
      window.videoHistoryItems.unshift(data);
      window.renderVideoHistory();
      window.videoLogProvider(task.provider_id, '\u4EFB\u52A1\u5DF2\u521B\u5EFA - ID: ' + data.task_id.substring(0, 12) + '..., \u72B6\u6001: ' + (data.status || '\u63D0\u4EA4\u4E2D'), 'ok');
      var vprogFill2 = document.getElementById('vprog_fill_' + task.provider_id);
      if (vprogFill2) { vprogFill2.classList.add('marquee'); }
      var labelEl2 = document.getElementById('vprog_label_' + task.provider_id);
      if (labelEl2) labelEl2.textContent = '\u7B49\u5F85\u4E2D (\u5DF2\u521B\u5EFA)';
      if (data.status === 'completed' && data.video_url) {
        if (!window.videoPreviewGroups[task.provider_id]) window.videoPreviewGroups[task.provider_id] = [];
        window.videoPreviewGroups[task.provider_id].push({
          task_id: data.task_id,
          video_url: data.video_url || '',
          video_url_local: data.video_url_local || '',
          prompt: prompt,
          provider_id: task.provider_id,
          elapsed_seconds: 0,
          status: 'completed',
        });
        window.videoGroupNavIdx[task.provider_id] = 0;
        window.renderVideoGroupedPreview();
      }
      if (!window.currentVideoTaskId) window.currentVideoTaskId = data.task_id;
      submitNextTask();
    }).catch(function(e) {
      submittedCount--;
      btn.textContent = '\u23F3 \u5411 ' + submittedCount + '/' + totalTasks + ' \u63D0\u4EA4...';
      window.videoLogProvider(task.provider_id, '\u2718 \u63D0\u4EA4\u5931\u8D25: ' + e.message + ' (\u6A21\u578B: ' + task.model + ')', 'error');
      var labelEl3 = document.getElementById('vprog_label_' + task.provider_id);
      if (labelEl3) labelEl3.textContent = '\u2718 \u63D0\u4EA4\u5931\u8D25';
      if (submittedCount >= totalTasks && allTaskData.length > 0) {
        window.videoLog('\u5DF2\u63D0\u4EA4\u90E8\u5206\u4EFB\u52A1\uFF0C\u5F00\u59CB\u8F6E\u8BE2 (' + allTaskData.length + '/' + totalTasks + ')...', 'warn');
        window.startVideoPolling(allTaskData, startTime);
      } else if (allTaskData.length === 0) {
        window.stopVideoElapsedTimer();
        btn.disabled = false;
        btn.textContent = '\u{1F680} \u751F\u6210\u89C6\u9891';
      }
    });
  }

  submitNextTask();
};

window.startVideoElapsedTimer = function() {
  window.stopVideoElapsedTimer();
  window.videoElapsedTimer = setInterval(function() {
    var elapsed = Math.round((Date.now() - window.videoStartTime) / 1000);
    var el = document.getElementById('videoElapsed');
    if (el) el.textContent = '\u5DF2\u7528\u65F6 ' + elapsed + 's';
  }, 1000);
};

window.stopVideoElapsedTimer = function() {
  if (window.videoElapsedTimer) { clearInterval(window.videoElapsedTimer); window.videoElapsedTimer = null; }
};

window.startVideoPolling = function(allTaskData, startTime) {
  if (!startTime) startTime = Date.now();
  window.videoStartTime = startTime;
  if (window.videoPollTimer) clearInterval(window.videoPollTimer);

  window.videoActivePollTasks = {};
  window.videoProgressMaxLogged = {};
  window.videoProgressStageLogged = {};

  allTaskData.forEach(function(item) {
    if (item.task_id && item.status !== 'completed' && item.status !== 'failed' && item.status !== 'error') {
      window.videoActivePollTasks[item.task_id] = { provider_id: item.provider_id || 'unknown' };
    }
  });

  var completedCount = 0;
  var totalToComplete = allTaskData.length;
  var pollRound = 0;
  var taskProgressMap = {};

  function updateGlobalProgress() {
    var activeIds = Object.keys(window.videoActivePollTasks);
    var activeCount = activeIds.length;
    var totalPct = 0;
    var count = 0;
    activeIds.forEach(function(atid) {
      var p = taskProgressMap[atid];
      if (p !== undefined) { totalPct += p; count++; }
    });
    var avg = count > 0 ? Math.round(totalPct / count) : 0;
    var fill = document.getElementById('videoProgressFill');
    if (fill) {
      fill.style.width = avg + '%';
      fill.style.background = '';
      fill.className = avg >= 100 && activeCount === 0 ? 'video-progress-solid' : 'video-progress-marquee';
    }
    document.getElementById('videoProgressText').textContent = avg + '%';
  }

  window.videoPollTimer = setInterval(function() {
    var activeIds = Object.keys(window.videoActivePollTasks);
    pollRound++;

    if (activeIds.length === 0) {
      clearInterval(window.videoPollTimer);
      window.videoPollTimer = null;
      window.stopVideoElapsedTimer();
      var fillDone = document.getElementById('videoProgressFill');
      if (fillDone) { fillDone.style.background = ''; fillDone.className = 'video-progress-solid'; fillDone.style.width = '100%'; }
      document.getElementById('videoProgressText').textContent = '100%';
      var btn = document.getElementById('videoGenBtn');
      btn.disabled = false;
      btn.textContent = '\u{1F680} \u751F\u6210\u89C6\u9891';
      window.updateVideoGenerateButton();
      var totalElapsed = Math.round((Date.now() - startTime) / 1000);
      window.setStatus('\u89C6\u9891\u751F\u6210\u5B8C\u6210! (' + completedCount + '/' + totalToComplete + ' \u4E2A\u4EFB\u52A1, \u5171\u8017\u65F6 ' + totalElapsed + 's)');
      window.videoLog('\u2714 \u5168\u90E8\u4EFB\u52A1\u5B8C\u6210! \u5171\u8017\u65F6 ' + totalElapsed + 's', 'ok');
      return;
    }

    window.videoLog('\u8F6E\u8BE2 #' + pollRound + ' - \u8FDB\u884C\u4E2D: ' + activeIds.length + ', \u5B8C\u6210: ' + completedCount + '/' + totalToComplete, 'info');

    activeIds.forEach(function(tid) {
      _af('/api/video/status/' + tid).then(function(r) {
        if (!r.ok) return;
        return r.json();
      }).then(function(data) {
        if (!data) return;
        var status = data.status || '';
        var progress = data.progress || 0;
        var elapsed = data.elapsed_seconds || 0;
        var provId = window.videoActivePollTasks[tid] ? window.videoActivePollTasks[tid].provider_id : 'unknown';

        taskProgressMap[tid] = progress;
        updateGlobalProgress();

        var progFillEl = document.getElementById('vprog_fill_' + provId);
        if (progFillEl) {
          progFillEl.style.width = progress + '%';
          progFillEl.classList.remove('complete');
          progFillEl.classList.add('marquee');
        }
        var progLabel = document.getElementById('vprog_label_' + provId);
        if (progLabel) {
          var stageLabel = data.stage || 'processing';
          progLabel.textContent = '[' + stageLabel + '] ' + Math.round(progress) + '%' + (elapsed ? ' (' + Math.round(elapsed) + 's)' : '');
        }
        if (!window.videoProgressMaxLogged) window.videoProgressMaxLogged = {};
        var prev = window.videoProgressMaxLogged[provId] || -1;
        var stageNow = data.stage || '';
        var prevStage = window.videoProgressStageLogged ? window.videoProgressStageLogged[provId] || '' : '';
        if (!window.videoProgressStageLogged) window.videoProgressStageLogged = {};
        if (progress >= 100 || (progress - prev >= 20) || (stageNow && stageNow !== prevStage)) {
          window.videoProgressMaxLogged[provId] = Math.max(prev, Math.floor(progress / 20) * 20);
          window.videoProgressStageLogged[provId] = stageNow;
          var extras = '';
          if (data.current_step && data.total_steps) extras = ' (step ' + data.current_step + '/' + data.total_steps + ')';
          else if (data.progress_detail) extras = ' ' + data.progress_detail;
          if (status !== 'completed' && status !== 'failed' && status !== 'error' && status !== 'cancelled' && status !== 'timeout') {
            window.videoLogProvider(provId, '\u5904\u7406\u4E2D ' + Math.round(progress) + '% (' + stageLabel + ')' + extras + ' ' + Math.round(elapsed) + 's', 'info');
          }
        }

        if (status === 'completed') {
          delete window.videoActivePollTasks[tid];
          completedCount++;
          if (progFillEl) { progFillEl.style.width = '100%'; progFillEl.classList.remove('marquee'); progFillEl.classList.add('complete'); }
          var labelCompleted = document.getElementById('vprog_label_' + provId);
          if (labelCompleted) labelCompleted.textContent = '\u2714 \u5B8C\u6210 ' + Math.round(elapsed) + 's';
          window.videoLogProvider(provId, '\u751F\u6210\u5B8C\u6210! \u8017\u65F6 ' + Math.round(elapsed) + 's', 'ok');

          if (!window.videoPreviewGroups[provId]) window.videoPreviewGroups[provId] = [];
          window.videoPreviewGroups[provId].push({
            task_id: tid,
            video_url: data.video_url || '',
            video_url_local: data.video_url_local || '',
            prompt: data.prompt || '',
            provider_id: provId,
            elapsed_seconds: elapsed,
            status: 'completed',
          });
          window.videoGroupNavIdx[provId] = 0;
          window.renderVideoGroupedPreview();

          for (var hi = 0; hi < window.videoHistoryItems.length; hi++) {
            if (window.videoHistoryItems[hi].task_id === tid) {
              window.videoHistoryItems[hi] = data;
              break;
            }
          }
          window.renderVideoHistory();
        } else if (status === 'failed' || status === 'error' || status === 'cancelled' || status === 'timeout') {
          delete window.videoActivePollTasks[tid];
          completedCount++;
          var errMsg = data.error || status;
          var progFillFail = document.getElementById('vprog_fill_' + provId);
          if (progFillFail) { progFillFail.style.width = '0%'; progFillFail.classList.remove('marquee', 'complete'); }
          var labelFailed = document.getElementById('vprog_label_' + provId);
          if (labelFailed) labelFailed.textContent = '\u2718 \u5931\u8D25: ' + errMsg.substring(0, 30);
          window.videoLogProvider(provId, '\u2718 \u751F\u6210\u5931\u8D25: ' + errMsg + ' (\u8017\u65F6 ' + Math.round(elapsed) + 's)', 'error');

          if (!window.videoPreviewGroups[provId]) window.videoPreviewGroups[provId] = [];
          window.videoPreviewGroups[provId].push({
            task_id: tid,
            video_url: '',
            video_url_local: '',
            prompt: data.prompt || '',
            provider_id: provId,
            elapsed_seconds: elapsed,
            status: status,
            error: errMsg,
          });
          window.renderVideoGroupedPreview();

          for (var hi2 = 0; hi2 < window.videoHistoryItems.length; hi2++) {
            if (window.videoHistoryItems[hi2].task_id === tid) {
              window.videoHistoryItems[hi2] = data;
              break;
            }
          }
          window.renderVideoHistory();
        }
      }).catch(function(e) { /* single poll failure */ });
    });
  }, 5000);
};

/* ═══════════════════════════════════════════════════════════════════
   Video History
   ═══════════════════════════════════════════════════════════════════ */
window.renderVideoHistory = function() {
  var container = document.getElementById('videoHistoryList');
  if (window.videoHistoryItems.length === 0) {
    container.innerHTML = '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:20px;">\u6682\u65E0\u89C6\u9891</div>';
    return;
  }
  var groups = {};
  window.videoHistoryItems.forEach(function(item) {
    var pid = item.provider_id || 'unknown';
    if (!groups[pid]) groups[pid] = [];
    groups[pid].push(item);
  });

  var html = '';
  Object.keys(groups).forEach(function(pid) {
    var items = groups[pid];
    var prov = window.videoProviders.find(function(p){ return p.id === pid; });
    var provColor = prov ? prov.color : 'var(--accent)';
    var provName = prov ? (prov.name || pid) : pid;
    html += '<div style="font-size:10px;font-weight:600;color:' + provColor + ';padding:4px 0 2px 0;margin-top:4px;">' + provName + ' (' + items.length + ')</div>';
    items.forEach(function(item) {
      var promptShort = (item.prompt || '').substring(0, 40);
      var statusIcon = item.status === 'completed' ? '\u2705' : '\u23F3';
      var elapsed = item.elapsed_seconds ? Math.round(item.elapsed_seconds) + 's' : '';
      var taskId = item.task_id ? item.task_id.substring(0, 8) : '';
      html += '<div onclick="playVideoItem(\'' + (item.video_url_local || item.video_url || '') + '\')" style="background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;padding:6px 8px;margin-bottom:4px;cursor:pointer;transition:border-color 0.15s;" onmouseover="this.style.borderColor=\'' + provColor + '\';" onmouseout="this.style.borderColor=\'var(--border)\';">' +
        '<div style="display:flex;align-items:center;gap:4px;">' +
          '<span>' + statusIcon + '</span>' +
          '<span style="font-size:10px;color:var(--text-primary);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + promptShort + '</span>' +
          '<span style="font-size:9px;color:var(--text-muted);">' + elapsed + '</span>' +
        '</div>' +
      '</div>';
    });
  });
  container.innerHTML = html;
};

/* ═══════════════════════════════════════════════════════════════════
   Video Per-Provider Bars
   ═══════════════════════════════════════════════════════════════════ */
window.renderVideoPerProviderBars = function() {
  var container = document.getElementById('videoPerProviderSection');
  if (!container) return;
  var html = '';
  window.selectedVideoProviderIds.forEach(function(pid) {
    var prov = window.videoProviders.find(function(p) { return p.id === pid; });
    var name = prov ? (prov.name || pid) : pid;
    var color = prov ? prov.color : 'var(--accent)';
    html +=
      '<div style="margin-bottom:14px;border:1px solid var(--border);border-radius:8px;padding:10px;background:var(--bg-surface);">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">' +
          '<span style="font-size:12px;font-weight:700;color:' + color + ';">' + name + '</span>' +
          '<span id="vprog_label_' + pid + '" style="font-size:10px;color:var(--text-muted);">\u7B49\u5F85\u4E2D...</span>' +
        '</div>' +
        '<div style="background:var(--border);border-radius:4px;overflow:hidden;height:6px;margin-bottom:6px;">' +
          '<div class="vprog-fill" id="vprog_fill_' + pid + '" style="height:100%;width:0%;"></div>' +
        '</div>' +
        '<div id="vlog_' + pid + '" style="max-height:90px;overflow-y:auto;background:var(--bg-base);border:1px solid var(--border);border-radius:4px;padding:5px 7px;font-family:monospace;font-size:10px;line-height:1.6;color:var(--text-muted);">' +
          '<div style="color:var(--text-muted);">[\u7CFB\u7EDF] \u7B49\u5F85\u63D0\u4EA4...</div>' +
        '</div>' +
      '</div>';
  });
  container.innerHTML = html;
  container.style.display = 'block';
};

/* ═══════════════════════════════════════════════════════════════════
   Video Grouped Preview
   ═══════════════════════════════════════════════════════════════════ */
window.renderVideoGroupedPreview = function() {
  var container = document.getElementById('videoPreviewResults');
  var emptyEl = document.getElementById('videoPreviewEmpty');
  var countEl = document.getElementById('videoResultCount');
  if (!container) return;

  var allItems = [];
  Object.keys(window.videoPreviewGroups).forEach(function(pid) {
    allItems = allItems.concat(window.videoPreviewGroups[pid]);
  });

  if (allItems.length === 0) {
    container.style.display = 'none';
    if (emptyEl) emptyEl.style.display = 'flex';
    if (countEl) countEl.textContent = '';
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';
  container.style.display = 'flex';
  if (countEl) countEl.textContent = allItems.length + ' \u4E2A\u7ED3\u679C';
  container.innerHTML = '';

  var groupKeys = Object.keys(window.videoPreviewGroups);

  for (var g = 0; g < groupKeys.length; g++) {
    (function(provId, items) {
      var prov = window.videoProviders.find(function(p){ return p.id === provId; });
      var provColor = prov ? prov.color : '#5b8def';
      var provName = prov ? (prov.display_name || prov.name || provId) : provId;
      var navIdx = window.videoGroupNavIdx[provId] || 0;

      var groupCard = document.createElement('div');
      groupCard.className = 'fade-in';
      groupCard.style.cssText = 'padding:14px;background:var(--bg-surface);border-radius:12px;border:1px solid var(--border);';

      var header = document.createElement('div');
      header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;';
      var completedItems = items.filter(function(i){ return i.status === 'completed'; });
      var failedItems = items.filter(function(i){ return i.status !== 'completed'; });
      var statusText = '';
      if (failedItems.length > 0) statusText += '<span style="color:#ef4444;">\u2717 ' + failedItems.length + ' \u5931\u8D25</span> ';
      if (completedItems.length > 0) statusText += '<span style="color:#22c55e;">\u2713 ' + completedItems.length + ' \u5B8C\u6210</span>';

      header.innerHTML =
        '<div style="display:flex;align-items:center;gap:8px;">' +
          '<span style="width:8px;height:8px;border-radius:50%;background:' + provColor + ';display:inline-block;flex-shrink:0;"></span>' +
          '<span style="font-weight:700;font-size:13px;color:var(--text-primary);">' + _eh(provName) + '</span>' +
          '<span style="font-size:10px;color:var(--text-muted);">' + statusText + '</span>' +
        '</div>';
      if (completedItems.length > 1) {
        header.innerHTML +=
          '<div style="display:flex;align-items:center;gap:6px;">' +
            '<span id="vgrp_cnt_' + provId + '" style="font-size:11px;color:var(--text-muted);">' + (navIdx+1) + ' / ' + completedItems.length + '</span>' +
            '<div style="display:flex;gap:4px;">' +
              '<button onclick="videoGroupNav(\'' + provId + '\',-1)" style="width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;">\u2039</button>' +
              '<button onclick="videoGroupNav(\'' + provId + '\',1)" style="width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;">\u203A</button>' +
            '</div>' +
          '</div>';
      }
      groupCard.appendChild(header);

      var viewerWrap = document.createElement('div');
      viewerWrap.id = 'vgrp_viewer_' + provId;
      viewerWrap.style.cssText = 'position:relative;display:flex;align-items:center;justify-content:center;min-height:200px;overflow:hidden;border-radius:10px;background:#000;';

      function renderVideoItem() {
        viewerWrap.innerHTML = '';
        var cur = completedItems[window.videoGroupNavIdx[provId] || 0];
        if (!cur) { viewerWrap.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:20px;">\u65E0\u5B8C\u6210\u7684\u89C6\u9891</div>'; return; }

        var cntEl = document.getElementById('vgrp_cnt_' + provId);
        if (cntEl) cntEl.textContent = ((window.videoGroupNavIdx[provId]||0)+1) + ' / ' + completedItems.length;

        if (completedItems.length > 1) {
          var btnP = document.createElement('button');
          btnP.style.cssText = 'position:absolute;left:8px;top:50%;transform:translateY(-50%);z-index:5;width:34px;height:34px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
          btnP.innerHTML = '\u2039';
          btnP.onclick = function(e){ e.stopPropagation(); window.videoGroupNav(provId,-1); };
          viewerWrap.appendChild(btnP);

          var btnN = document.createElement('button');
          btnN.style.cssText = 'position:absolute;right:8px;top:50%;transform:translateY(-50%);z-index:5;width:34px;height:34px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
          btnN.innerHTML = '\u203A';
          btnN.onclick = function(e){ e.stopPropagation(); window.videoGroupNav(provId,1); };
          viewerWrap.appendChild(btnN);
        }

        var videoEl = document.createElement('video');
        var videoSrc = cur.video_url_local || cur.video_url;
        if (!videoSrc) {
          viewerWrap.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:20px;text-align:center;">\u26A0 \u89C6\u9891\u5730\u5740\u4E3A\u7A7A\uFF0C\u53EF\u80FD\u4ECD\u5728\u5904\u7406\u4E2D\u6216\u4E0B\u8F7D\u5931\u8D25</div>';
          return;
        }
        videoEl.src = videoSrc;
        videoEl.controls = true;
        videoEl.loop = true;
        videoEl.style.cssText = 'width:100%;max-height:40vh;border-radius:8px;background:#000;';
        viewerWrap.appendChild(videoEl);
        videoEl.play().catch(function(){});
      }
      renderVideoItem();
      groupCard.appendChild(viewerWrap);

      var btnRow = document.createElement('div');
      btnRow.style.cssText = 'display:flex;gap:6px;margin-top:8px;';
      var curItem = completedItems[window.videoGroupNavIdx[provId] || 0];
      if (curItem) {
        var videoSrc = curItem.video_url_local || curItem.video_url || '';
        btnRow.innerHTML =
          '<button class="btn-secondary" style="flex:1;font-size:11px;padding:6px;" onclick="downloadVideoFromSrc(\'' + videoSrc.replace(/'/g, "\\'") + '\')">\u2B07\uFE0F \u4E0B\u8F7D</button>' +
          '<button class="btn-secondary" style="flex:1;font-size:11px;padding:6px;" onclick="pushVideoToGalleryFromSrc(\'' + videoSrc.replace(/'/g, "\\'") + '\')">\u{1F5BC} \u63A8\u5230\u56FE\u5E93</button>';
      }
      groupCard.appendChild(btnRow);

      if (curItem && curItem.elapsed_seconds) {
        var info = document.createElement('div');
        info.style.cssText = 'font-size:10px;color:var(--text-muted);margin-top:6px;text-align:right;';
        info.textContent = '\u23F1 ' + Math.round(curItem.elapsed_seconds) + 's';
        groupCard.appendChild(info);
      }

      if (failedItems.length > 0) {
        failedItems.forEach(function(fi) {
          var errDiv = document.createElement('div');
          errDiv.style.cssText = 'font-size:11px;color:#ef4444;background:rgba(239,68,68,0.08);padding:6px 10px;border-radius:6px;margin-top:6px;display:flex;align-items:flex-start;gap:6px;';
          errDiv.innerHTML = '<span style="flex-shrink:0;">\u26A0</span><span>' + _eh(fi.error || '\u751F\u6210\u5931\u8D25') + '</span>';
          groupCard.appendChild(errDiv);
        });
      }

      if (completedItems.length > 1) {
        var thumbRow = document.createElement('div');
        thumbRow.id = 'vgrp_thumbs_' + provId;
        thumbRow.style.cssText = 'display:flex;gap:8px;margin-top:10px;overflow-x:auto;padding-bottom:2px;';
        for (var ti = 0; ti < completedItems.length; ti++) {
          (function(ti) {
            var tItem = completedItems[ti];
            var isActive = ti === (window.videoGroupNavIdx[provId] || 0);
            var wrap = document.createElement('div');
            wrap.style.cssText = 'width:80px;height:50px;border-radius:6px;overflow:hidden;cursor:pointer;flex-shrink:0;border:2px solid ' + (isActive ? provColor : 'transparent') + ';opacity:' + (isActive ? '1' : '0.5') + ';transition:all 0.15s;position:relative;background:#000;';
            var vid = document.createElement('video');
            vid.src = tItem.video_url_local || tItem.video_url;
            vid.muted = true;
            vid.style.cssText = 'width:100%;height:100%;object-fit:cover;';
            wrap.appendChild(vid);
            wrap.onclick = function() {
              window.videoGroupNavIdx[provId] = ti;
              renderVideoItem();
              var thumbs = thumbRow.children;
              for (var k = 0; k < thumbs.length; k++) {
                thumbs[k].style.borderColor = k === ti ? provColor : 'transparent';
                thumbs[k].style.opacity = k === ti ? '1' : '0.5';
              }
              var cntEl2 = document.getElementById('vgrp_cnt_' + provId);
              if (cntEl2) cntEl2.textContent = (ti+1) + ' / ' + completedItems.length;
            };
            thumbRow.appendChild(wrap);
          })(ti);
        }
        groupCard.appendChild(thumbRow);
      }

      container.appendChild(groupCard);
    })(groupKeys[g], window.videoPreviewGroups[groupKeys[g]]);
  }
};

window.videoGroupNav = function(provId, dir) {
  var items = window.videoPreviewGroups[provId];
  if (!items || items.length === 0) return;
  var completedItems = items.filter(function(i){ return i.status === 'completed'; });
  if (completedItems.length === 0) return;
  var cur = window.videoGroupNavIdx[provId] || 0;
  window.videoGroupNavIdx[provId] = (cur + dir + completedItems.length) % completedItems.length;
  window.renderVideoGroupedPreview();
};

window.downloadVideoFromSrc = function(src) {
  if (!src) { alert('\u6CA1\u6709\u89C6\u9891\u53EF\u4E0B\u8F7D'); return; }
  var a = document.createElement('a');
  a.href = src;
  a.download = 'video_' + Date.now() + '.mp4';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

window.pushVideoToGalleryFromSrc = function(src) {
  if (!src) return;
  var video = document.createElement('video');
  video.src = src;
  video.currentTime = 0.5;
  video.onloadeddata = function() {
    var canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    var b64 = canvas.toDataURL('image/png');
    _af('/api/gallery/rename', {
      method: 'POST',
      body: JSON.stringify({ old_name: 'video_frame', new_name: 'video_frame_' + Date.now() }),
    }).catch(function(){});
    alert('\u89C6\u9891\u9996\u5E27\u5DF2\u63A8\u9001');
  };
  video.load();
};

window.playVideoItem = function(url) {
  if (!url) return;
  var found = false;
  Object.keys(window.videoPreviewGroups).forEach(function(pid) {
    window.videoPreviewGroups[pid].forEach(function(item, idx) {
      if ((item.video_url_local || item.video_url) === url) {
        window.videoGroupNavIdx[pid] = idx;
        found = true;
      }
    });
  });
  if (found) {
    window.renderVideoGroupedPreview();
    return;
  }
  var emptyEl = document.getElementById('videoPreviewEmpty');
  if (emptyEl) emptyEl.style.display = 'none';
  var container = document.getElementById('videoPreviewResults');
  container.style.display = 'flex';
  container.innerHTML = '<div style="width:100%;border-radius:10px;overflow:hidden;background:#000;"><video src="' + url + '" controls loop autoplay style="width:100%;max-height:40vh;border-radius:10px;"></video></div>';
};

window.downloadVideo = function() {
  var src = '';
  Object.keys(window.videoPreviewGroups).forEach(function(pid) {
    var items = window.videoPreviewGroups[pid].filter(function(i){ return i.status === 'completed'; });
    var idx = window.videoGroupNavIdx[pid] || 0;
    if (items[idx]) src = items[idx].video_url_local || items[idx].video_url || '';
  });
  if (!src) { alert('\u6CA1\u6709\u89C6\u9891\u53EF\u4E0B\u8F7D'); return; }
  window.downloadVideoFromSrc(src);
};

window.pushVideoToGallery = function() {
  var src = '';
  Object.keys(window.videoPreviewGroups).forEach(function(pid) {
    var items = window.videoPreviewGroups[pid].filter(function(i){ return i.status === 'completed'; });
    var idx = window.videoGroupNavIdx[pid] || 0;
    if (items[idx]) src = items[idx].video_url_local || items[idx].video_url || '';
  });
  if (!src) { alert('\u6CA1\u6709\u89C6\u9891'); return; }
  window.pushVideoToGalleryFromSrc(src);
};

})();
