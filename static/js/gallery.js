(function(){
'use strict';

function _af(url, opts) { return window._authFetch(url, opts); }
function _eh(s) { return window.escHtml(s); }
function _ea(s) { return window.escAttr(s); }

/* ═══════════════════════════════════════════════════════════════════
   Gallery State
   ═══════════════════════════════════════════════════════════════════ */
window.galleryItems = [];
window.activeMediaTab = 'image';

window.switchMediaTab = function(type) {
  window.activeMediaTab = type;
  document.getElementById('mediaTabImage').classList.toggle('active', type === 'image');
  document.getElementById('mediaTabVideo').classList.toggle('active', type === 'video');
  var pushBtn = document.getElementById('btnPushToRef');
  if (pushBtn) {
    if (type === 'image') { pushBtn.style.display = ''; } else { pushBtn.style.display = 'none'; }
  }
  if (document.getElementById('btnGallerySelect') && document.getElementById('btnGallerySelect').classList.contains('active')) {
    window.showGalleryToolbar(true);
  }
  var gridEl = document.getElementById('galleryGrid');
  if (gridEl) gridEl.classList.toggle('gallery-grid-video', type === 'video');
  window.renderGalleryItems(window.galleryItems);
};

window.applyMediaFilters = function() {
  window.renderGalleryItems(window.galleryItems);
};

window.updateGalleryProviderFilter = function() {
  var sel = document.getElementById('galleryProviderFilter');
  if (!sel) return;
  var current = sel.value;
  var pids = {};
  for (var i = 0; i < window.galleryItems.length; i++) {
    pids[window.galleryItems[i].model] = true;
  }
  var opts = '<option value="">\u6240\u6709 Provider</option>';
  var keys = Object.keys(pids).sort();
  for (var k = 0; k < keys.length; k++) {
    var pInfo = window.findProvider(keys[k]) || {name: keys[k]};
    opts += '<option value="' + _ea(keys[k]) + '"' + (current === keys[k] ? ' selected' : '') + '>' + _eh(pInfo.name) + '</option>';
  }
  sel.innerHTML = opts;
};

window.applyGallerySort = function() {
  window.renderGalleryItems(window.galleryItems);
};

window.renderGalleryItems = function(items) {
  var g = document.getElementById('galleryGrid');
  var filtered = items.slice();
  if (window.activeMediaTab === 'image') {
    filtered = filtered.filter(function(it) { return it.type !== 'video'; });
  } else if (window.activeMediaTab === 'video') {
    filtered = filtered.filter(function(it) { return it.type === 'video'; });
  }
  var providerFilter = document.getElementById('galleryProviderFilter');
  var providerVal = providerFilter ? providerFilter.value : '';
  if (providerVal) {
    filtered = filtered.filter(function(it) { return (it.model || '') === providerVal; });
  }
  var searchInput = document.getElementById('gallerySearchInput');
  var searchVal = searchInput ? searchInput.value.trim().toLowerCase() : '';
  if (searchVal) {
    filtered = filtered.filter(function(it) { return (it.prompt || '').toLowerCase().indexOf(searchVal) !== -1; });
  }
  if (!filtered.length) {
    var emptyMsg = window.activeMediaTab === 'video' ? '\u6682\u65E0\u89C6\u9891' : '\u6682\u65E0\u56FE\u7247';
    g.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:60px;font-size:13px;">' + emptyMsg + '</div>';
    return;
  }
  var sortBy = document.getElementById('gallerySortBy') ? document.getElementById('gallerySortBy').value : 'created_at_desc';
  var sorted = filtered.slice();
  sorted.sort(function(a, b) {
    switch(sortBy) {
      case 'created_at_asc': return (a.created_at || '').localeCompare(b.created_at || '');
      case 'model_asc': return (a.model || '').localeCompare(b.model || '');
      case 'model_desc': return (b.model || '').localeCompare(a.model || '');
      case 'prompt_asc': return (a.prompt || '').localeCompare(b.prompt || '');
      default: return (b.created_at || '').localeCompare(a.created_at || '');
    }
  });
  var h = '';
  var inSelectMode = document.getElementById('btnGallerySelect') && document.getElementById('btnGallerySelect').classList.contains('active');
  for (var i = 0; i < sorted.length; i++) {
    (function(item){
      var f = item.local_path.split(/[\\/]/).pop();
      var pInfo = window.findProvider(item.model) || {name: item.model, color: '#5b8def'};
      var isSelected = window.selectedGalleryItems.indexOf(item.id) !== -1;
      var isVideo = item.type === 'video';

      var clickHandler = inSelectMode
        ? 'onclick="toggleGalleryItem(\'' + _ea(item.id) + '\',this)"'
        : (isVideo
          ? 'onclick="playVideoFromGallery(\'' + _ea(item.id) + '\')"'
          : 'onclick="openLightboxFromGallery(\'' + _ea(item.id) + '\')"');

      var typeIcon = '';
      var badgesHtml = '';
      var videoOverlayHtml = '';
      if (isVideo) {
        typeIcon = '<div class="vid-play"><div class="vid-play-btn"><span>\u25B6</span></div></div>';
        badgesHtml = '';
        var durationHtml = item.duration ? '<div class="vid-duration">' + item.duration + 's</div>' : '';
        var promptShort = (item.prompt || '').length > 40 ? (item.prompt || '').substring(0, 40) + '...' : (item.prompt || '\u672A\u547D\u540D\u89C6\u9891');
        var vidUrl = item.video_url || '';
        var vidPreviewHtml = vidUrl ? '<video class="vid-preview-video" preload="metadata" muted loop playsinline data-src="' + _ea(vidUrl) + '"></video>' : '';
        videoOverlayHtml = vidPreviewHtml + '<div class="vid-info">' +
          '<div class="vid-info-title">' + _eh(promptShort) + '</div>' +
          '<div class="vid-info-meta"><span>' + _eh(pInfo.name) + '</span><div class="vid-info-dot"></div><span>' + _eh(item.created_at || '') + '</span></div>' +
        '</div>' + durationHtml + '<div class="vid-progress"><div class="vid-progress-bar"></div></div>';
      }

      var thumbHtml = '<img src="' + item.thumbnail + '" loading="lazy" style="' + (isVideo ? 'object-fit:cover;' : '') + '">';

      h += '<div class="gallery-item' + (isSelected ? ' selected' : '') + (isVideo ? ' gallery-item-video' : '') + '" data-id="' + _ea(item.id) + '" data-fname="' + _ea(f) + '" data-type="' + (isVideo ? 'video' : 'image') + '" ' + clickHandler + '>' +
        thumbHtml +
        typeIcon +
        badgesHtml +
        videoOverlayHtml +
        (inSelectMode ? '' : (isVideo ? '' : '<div class="gallery-zoom-hint">\u{1F50D}</div>')) +
        (isVideo ? '' : '<div class="gallery-item-overlay">' +
          '<div class="gallery-item-label">' + _eh(pInfo.name) + '</div>' +
        '</div>') +
      '</div>';
    })(sorted[i]);
  }
  g.innerHTML = h;
  window.initVideoHoverPreview();
};

var _vidHoverTimers = {};
window.initVideoHoverPreview = function() {
  var grid = document.getElementById('galleryGrid');
  if (!grid || grid._vidHoverBound) return;
  grid._vidHoverBound = true;
  grid.addEventListener('mouseenter', function(e) {
    var card = e.target.closest('.gallery-item-video');
    if (!card || card.classList.contains('vid-previewing')) return;
    var vid = card.querySelector('.vid-preview-video');
    if (!vid || !vid.dataset.src) return;
    var id = card.dataset.id;
    clearTimeout(_vidHoverTimers['out_' + id]);
    _vidHoverTimers['in_' + id] = setTimeout(function() {
      if (!vid.src) vid.src = vid.dataset.src;
      vid.currentTime = 0.5;
      vid.play().then(function() {
        card.classList.add('vid-previewing');
      }).catch(function() {});
    }, 350);
  }, true);
  grid.addEventListener('mouseleave', function(e) {
    var card = e.target.closest('.gallery-item-video');
    if (!card) return;
    var vid = card.querySelector('.vid-preview-video');
    if (!vid) return;
    var id = card.dataset.id;
    clearTimeout(_vidHoverTimers['in_' + id]);
    _vidHoverTimers['out_' + id] = setTimeout(function() {
      vid.pause();
      vid.currentTime = 0;
      card.classList.remove('vid-previewing');
    }, 200);
  }, true);
};

window.playVideoFromGallery = function(itemId) {
  var item = null;
  for (var i = 0; i < window.galleryItems.length; i++) {
    if (window.galleryItems[i].id === itemId) {
      item = window.galleryItems[i];
      break;
    }
  }
  if (!item || !item.video_url) { alert('\u65E0\u6CD5\u64AD\u653E\u89C6\u9891'); return; }
  var lb = document.getElementById('lightbox');
  var lbImg = document.getElementById('lightbox-img');
  var lbVideo = document.getElementById('lightbox-video');
  var lbDl = document.getElementById('lightbox-dl');
  var lbInfo = document.getElementById('lightbox-info');
  var lbPromptBox = document.getElementById('lightbox-prompt-box');
  var lbPrompt = document.getElementById('lightbox-prompt');
  if (lbImg) { lbImg.classList.add('hidden'); lbImg.src = ''; }
  if (lbVideo) {
    lbVideo.src = item.video_url;
    lbVideo.classList.remove('hidden');
    lbVideo.play();
  }
  if (lbDl) {
    lbDl.href = item.video_url;
    lbDl.download = (item.id || 'video') + '.mp4';
    lbDl.textContent = '\u2B07 \u4E0B\u8F7D\u89C6\u9891';
    lbDl.classList.remove('hidden');
  }
  if (lbInfo) lbInfo.textContent = item.prompt || '';
  if (lbPromptBox) lbPromptBox.style.display = 'none';
  lb.classList.add('show');
  document.body.style.overflow = 'hidden';
};

window.loadGallery = function() {
  var g = document.getElementById('galleryGrid');
  _af('/api/gallery?limit=80').then(function(r){return r.json();}).then(function(d){
    var items = d.items || [];
    window.galleryItems = items;
    window.allGalleryIds = items.map(function(it){ return it.id; });
    window.updateGalleryProviderFilter();
    window.renderGalleryItems(items);
  }).catch(function(e){
    g.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:#f87171;padding:40px;">\u52A0\u8F7D\u5931\u8D25</div>';
  });
};

window.openLightboxFromGallery = function(itemId) {
  var item = null;
  for (var i = 0; i < window.galleryItems.length; i++) {
    if (window.galleryItems[i].id === itemId) {
      item = window.galleryItems[i];
      break;
    }
  }
  if (!item) { console.error('[Gallery] \u672A\u627E\u5230\u56FE\u7247\u6570\u636E itemId:', itemId); alert('\u65E0\u6CD5\u6253\u5F00\u56FE\u7247\uFF1A\u672A\u627E\u5230\u6570\u636E'); return; }
  if (!item.local_path) { console.error('[Gallery] local_path \u4E3A\u7A7A:', item); alert('\u65E0\u6CD5\u6253\u5F00\u56FE\u7247\uFF1A\u8DEF\u5F84\u65E0\u6548'); return; }
  var f = item.local_path.split(/[\\/]/).pop();
  var pInfo = window.findProvider(item.model) || {name: item.model, color: '#5b8def'};
  var src = '/api/gallery/image/' + encodeURIComponent(f);
  var prompt = item.prompt || '';
  window.openLightbox(src, pInfo.name, prompt);
};

/* ═══════════════════════════════════════════════════════════════════
   Gallery Select Mode
   ═══════════════════════════════════════════════════════════════════ */
window.gallerySelectMode = false;
window.selectedGalleryItems = [];
window.allGalleryIds = [];

window.toggleGallerySelectMode = function() {
  window.gallerySelectMode = !window.gallerySelectMode;
  var btn = document.getElementById('btnGallerySelect');
  if (window.gallerySelectMode) {
    btn.textContent = '\u2715 \u9000\u51FA\u9009\u62E9';
    btn.style.borderColor = 'var(--accent)';
    btn.style.color = 'var(--accent)';
    btn.classList.add('active');
    window.showGalleryToolbar(true);
  } else {
    btn.textContent = '\u2611 \u9009\u62E9\u6A21\u5F0F';
    btn.style.borderColor = '';
    btn.style.color = '';
    btn.classList.remove('active');
    window.deselectAllGallery();
    window.showGalleryToolbar(false);
  }
  window.loadGallery();
};

window.showGalleryToolbar = function(show) {
  document.getElementById('btnSelAll').classList.toggle('hidden', !show);
  document.getElementById('btnSelNone').classList.toggle('hidden', !show);
  document.getElementById('btnGalleryRename').classList.toggle('hidden', !show);
  document.getElementById('btnPushToRef').classList.toggle('hidden', !show || window.activeMediaTab !== 'image');
  document.getElementById('btnDlSelected').classList.toggle('hidden', !show);
  document.getElementById('btnDelSelected').classList.toggle('hidden', !show);
};

window.selectAllGallery = function() {
  var visIds = [];
  var els = document.querySelectorAll('#galleryGrid .gallery-item');
  for (var i = 0; i < els.length; i++) {
    visIds.push(els[i].getAttribute('data-id'));
  }
  window.selectedGalleryItems = visIds;
  window.updateGallerySelectionUI();
};

window.deselectAllGallery = function() { window.selectedGalleryItems = []; window.updateGallerySelectionUI(); };

window.toggleGalleryItem = function(id, el) {
  if (!window.gallerySelectMode) return;
  event.stopPropagation(); event.preventDefault();
  var idx = window.selectedGalleryItems.indexOf(id);
  if (idx !== -1) { window.selectedGalleryItems.splice(idx, 1); el.classList.remove('selected'); }
  else { window.selectedGalleryItems.push(id); el.classList.add('selected'); }
  window.updateGallerySelectionUI();
};

window.updateGallerySelectionUI = function() {
  document.getElementById('selGalleryCount').textContent = window.selectedGalleryItems.length;
  document.getElementById('dlGalleryCount').textContent = window.selectedGalleryItems.length;
  for (var i = 0; i < window.allGalleryIds.length; i++) {
    (function(id){ var item = document.querySelector('.gallery-item[data-id="'+id+'"]'); if(item) item.classList.toggle('selected', window.selectedGalleryItems.indexOf(id)!==-1); })(window.allGalleryIds[i]);
  }
};

window.batchDownloadGallery = function() {
  if (!window.selectedGalleryItems.length) { alert('Please select images to download'); return; }
  window.setStatus('Preparing download...');
  _af('/api/gallery/batch-download', { method:'POST', body:JSON.stringify(window.selectedGalleryItems) })
    .then(function(r){
      if (!r.ok) throw new Error('Server error ' + r.status);
      return r.blob();
    })
    .then(function(blob){
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'image_gen_studio_' + new Date().toISOString().slice(0,19).replace(/[:-]/g,'') + '.zip';
      document.body.appendChild(a);
      a.click();
      setTimeout(function(){ URL.revokeObjectURL(url); a.remove(); }, 1000);
      window.setStatus('Download started: ' + window.selectedGalleryItems.length + ' images');
    })
    .catch(function(e){ alert('Download failed: ' + e.message); });
};

window.deleteSelectedGallery = function() {
  if (!window.selectedGalleryItems.length) { alert('\u8BF7\u5148\u9009\u62E9\u8981\u5220\u9664\u7684\u56FE\u7247'); return; }
  if (!confirm('\u786E\u5B9A\u5220\u9664\u9009\u4E2D\u7684 ' + window.selectedGalleryItems.length + ' \u5F20\u56FE\u7247\uFF1F\u6B64\u64CD\u4F5C\u4E0D\u53EF\u64A4\u9500\u3002')) return;
  _af('/api/gallery/batch-delete', { method:'POST', body:JSON.stringify(window.selectedGalleryItems) })
    .then(function(r){return r.json();}).then(function(d){ window.setStatus('\u5DF2\u5220\u9664 '+d.total_deleted+' \u5F20\u56FE\u7247'); window.selectedGalleryItems=[]; window.loadGallery(); })
    .catch(function(e){ alert('\u5220\u9664\u5931\u8D25: '+e.message); });
};

/* ═══════════════════════════════════════════════════════════════════
   Gallery Rename + Push
   ═══════════════════════════════════════════════════════════════════ */
window.galleryStartRename = function() {
  if (!window.selectedGalleryItems.length) { alert('\u8BF7\u5148\u9009\u62E9\u8981\u91CD\u547D\u540D\u7684\u56FE\u7247'); return; }
  if (window.selectedGalleryItems.length > 1) { alert('\u91CD\u547D\u540D\u4EC5\u652F\u6301\u5355\u5F20\uFF0C\u8BF7\u53EA\u9009\u4E00\u5F20'); return; }
  var oldId = window.selectedGalleryItems[0];
  var currentName = oldId.split('_')[0] || '';
  var newName = prompt('\u8F93\u5165\u65B0\u540D\u79F0\uFF08\u4EC5\u5B57\u6BCD\u6570\u5B57\u4E0B\u5212\u7EBF\u4E2D\u6587\uFF09\uFF1A', currentName);
  if (!newName || newName === currentName) return;
  _af('/api/gallery/rename', {
    method: 'POST',
    body: JSON.stringify({old_id: oldId, new_name: newName})
  }).then(function(r){
    if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || '\u91CD\u547D\u540D\u5931\u8D25'); });
    return r.json();
  }).then(function(d){
    window.setStatus('\u5DF2\u91CD\u547D\u540D: ' + oldId + ' \u2192 ' + d.new_id);
    var idx = window.selectedGalleryItems.indexOf(oldId);
    if (idx !== -1) window.selectedGalleryItems[idx] = d.new_id;
    for (var i = 0; i < window.previewImages.length; i++) {
      if (window.previewImages[i].fname && window.previewImages[i].fname.indexOf(oldId) === 0) {
        var newFname = d.new_id + window.previewImages[i].fname.substring(oldId.length);
        window.previewImages[i].fname = newFname;
        window.previewImages[i].src = '/api/gallery/image/' + newFname;
      }
    }
    if (window.previewImages.length) window.renderPreviewViewer(document.getElementById('previewResults'));
    window.loadGallery();
  }).catch(function(e){ alert('\u91CD\u547D\u540D\u5931\u8D25: ' + e.message); });
};

window.pushGalleryToReference = function() {
  if (!window.selectedGalleryItems.length) { alert('\u8BF7\u5148\u9009\u62E9\u8981\u63A8\u9001\u7684\u56FE\u7247'); return; }
  if (window.selectedGalleryItems.length > 1) { alert('\u63A8\u9001\u4EC5\u652F\u6301\u5355\u5F20\uFF0C\u8BF7\u53EA\u9009\u4E00\u5F20'); return; }
  var itemId = window.selectedGalleryItems[0];
  var el = document.querySelector('.gallery-item[data-id="' + itemId + '"]');
  var fname = el ? el.getAttribute('data-fname') : '';
  if (!fname) { alert('\u65E0\u6CD5\u83B7\u53D6\u56FE\u7247\u6587\u4EF6\u540D'); return; }

  window.setStatus('\u6B63\u5728\u52A0\u8F7D\u53C2\u8003\u56FE\u7247...');
  _af('/api/gallery/image/' + fname + '/base64')
    .then(function(r){
      if (!r.ok) throw new Error('\u83B7\u53D6\u56FE\u7247\u6570\u636E\u5931\u8D25');
      return r.json();
    })
    .then(function(d){
      window.uploadedImageData = d.data;
      window.switchSubTab('i2i');
      window.switchNav('generate', document.getElementById('navGen'));
      var p = document.getElementById('uploadPreview');
      p.src = d.data;
      p.classList.remove('hidden');
      window.toggleGallerySelectMode();
      window.setStatus('\u5DF2\u63A8\u9001\u5230\u53C2\u8003\u56FE\u7247\u533A\u57DF\uFF0C\u53EF\u4EE5\u8F93\u5165\u4FEE\u6539\u63D0\u793A\u8BCD\u540E\u751F\u56FE');
    })
    .catch(function(e){ alert('\u63A8\u9001\u5931\u8D25: ' + e.message); });
};

/* ═══════════════════════════════════════════════════════════════════
   History
   ═══════════════════════════════════════════════════════════════════ */
window.allHistoryItems = [];

function _updateHistoryFilterProviders() {
  var sel = document.getElementById('historyFilterProvider');
  if (!sel) return;
  var current = sel.value;
  var pids = {};
  for (var i = 0; i < window.allHistoryItems.length; i++) {
    var providers = window.allHistoryItems[i].providers || [];
    for (var j = 0; j < providers.length; j++) {
      pids[providers[j]] = true;
    }
  }
  var opts = '<option value="">所有 Provider</option>';
  var keys = Object.keys(pids).sort();
  for (var k = 0; k < keys.length; k++) {
    var pInfo = window.findProvider(keys[k]) || {name: keys[k]};
    opts += '<option value="' + _ea(keys[k]) + '"' + (current === keys[k] ? ' selected' : '') + '>' + _eh(pInfo.name) + '</option>';
  }
  sel.innerHTML = opts;
}

window.loadHistory = function() {
  var h = document.getElementById('historyList');
  var search = document.getElementById('historySearch') ? document.getElementById('historySearch').value : '';
  var provider = document.getElementById('historyFilterProvider') ? document.getElementById('historyFilterProvider').value : '';
  var mode = document.getElementById('historyFilterMode') ? document.getElementById('historyFilterMode').value : '';
  var sortBy = document.getElementById('historySortBy') ? document.getElementById('historySortBy').value : 'time_desc';
  var params = 'limit=100';
  if (search) params += '&search=' + encodeURIComponent(search);
  if (provider) params += '&provider=' + encodeURIComponent(provider);
  if (mode) params += '&mode=' + encodeURIComponent(mode);
  _af('/api/history?' + params).then(function(r){return r.json();}).then(function(d){
    var items = d.items || [];
    window.allHistoryItems = items;
    _updateHistoryFilterProviders();
    if (sortBy === 'time_asc') {
      items = items.slice().reverse();
    }
    if (!items.length) {
      h.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:60px;font-size:13px;">暂无历史记录</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < items.length; i++) {
      (function(item){
        var isVideo = item.type === 'video';
        var ok = 0;
        for (var k in item.results) { if (item.results[k].success) ok++; }
        var modeTag = isVideo ? '🎬 视频' : (item.mode === 'i2i' ? '🖼 图生图' : '📝 文生图');
        var tags = '';
        for (var j = 0; j < item.providers.length; j++) {
          var pInfo = window.findProvider(item.providers[j]) || {name: item.providers[j], color: '#5b8def'};
          tags += '<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;background:' + pInfo.color + '15;color:' + pInfo.color + ';border-radius:5px;font-size:10px;font-weight:600;">' +
            '<span style="width:5px;height:5px;border-radius:50%;background:' + pInfo.color + ';"></span>' +
            _eh(pInfo.name) + '</span>';
        }
        var elapsedStr = item.elapsed_seconds ? (' · ' + item.elapsed_seconds.toFixed(1) + 's') : '';
        var statusTag = isVideo && item.status ? (' · <span style="color:' + (item.status === 'completed' ? '#22c3a5' : (item.status === 'failed' ? '#ef4444' : '#fbbf24')) + ';">' + item.status + '</span>') : '';
        html += '<div class="history-item">' +
          '<div class="history-meta">' +
            '<span>' + item.created_at + '</span>' +
            '<span>' + modeTag + '</span>' +
            '<span style="color:' + (ok === item.providers.length ? '#22c3a5' : '#fbbf24') + ';">' + ok + '/' + item.providers.length + ' 成功</span>' +
            '<span style="color:var(--accent);font-size:11px;">' + elapsedStr + statusTag + '</span>' +
          '</div>' +
          '<div class="history-prompt">' + _eh(item.prompt || '') + '</div>' +
          (item.enhanced_prompt && item.enhanced_prompt !== item.prompt ?
            '<div style="font-size:11px;color:var(--accent);margin-top:6px;">✨ ' + _eh(item.enhanced_prompt) + '</div>' : '') +
          '<div class="history-tags" style="margin-top:8px;">' + tags + '</div>' +
          (item.results ? '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">' +
            Object.values(item.results).filter(function(r){return r.success&&(r.local_path||r.video_url);}).map(function(r){
              if (isVideo) {
                return '<div onclick="event.stopPropagation();openLightbox(\'' + (r.video_url || '') + '\')" style="width:80px;height:60px;background:var(--bg-tertiary);border-radius:8px;border:1px solid var(--border);display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:20px;">▶</div>';
              } else {
                var f = r.local_path.split(/[\\/]/).pop();
                return '<img src="/api/gallery/thumb/' + f + '" style="width:60px;height:60px;object-fit:cover;border-radius:8px;border:1px solid var(--border);cursor:pointer;" onclick="openLightbox(\'/api/gallery/image/' + f + '\')">';
              }
            }).join('') + '</div>' : '') +
        '</div>';
      })(items[i]);
    }
    h.innerHTML = html;
  }).catch(function(e){
    h.innerHTML = '<div style="text-align:center;color:#f87171;padding:40px;">加载失败</div>';
  });
};

window.updateHistoryFilterProviders = _updateHistoryFilterProviders;

})();
