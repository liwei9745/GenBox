(function(){
'use strict';

function _af(url, opts) { return window._authFetch(url, opts); }
function _eh(s) { return window.escHtml(s); }
function _ea(s) { return window.escAttr(s); }

/* ═══════════════════════════════════════════════════════════════════
   Lightbox
   ═══════════════════════════════════════════════════════════════════ */
var lightboxCurrentPrompt = '';

window.openLightbox = function(src, label, prompt) {
  var lb = document.getElementById('lightbox');
  var img = document.getElementById('lightbox-img');
  var video = document.getElementById('lightbox-video');
  var dl = document.getElementById('lightbox-dl');
  var info = document.getElementById('lightbox-info');
  var promptBox = document.getElementById('lightbox-prompt-box');
  var promptEl = document.getElementById('lightbox-prompt');
  if (lb && img) {
    img.classList.remove('hidden', 'zoomed');
    if (video) { video.classList.add('hidden'); video.pause(); video.src = ''; }
    img.src = src;
    img.alt = label || '';
    window.lightboxZoom = 1;
    img.style.transform = 'scale(1)';
    if (dl) dl.href = src;
    if (info) info.textContent = label || '';
    lightboxCurrentPrompt = prompt || '';
    if (promptEl) promptEl.textContent = prompt || '';
    if (promptBox) promptBox.style.display = prompt ? 'block' : 'none';
    lb.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
};

window.copyLightboxPrompt = function() {
  if (lightboxCurrentPrompt) {
    navigator.clipboard.writeText(lightboxCurrentPrompt).then(function(){
      window.setStatus('\u5DF2\u590D\u5236\u63D0\u793A\u8BCD\u5230\u526A\u8D34\u677F');
    });
  }
};

window.closeLightbox = function(e) {
  if (e && e.target !== e.currentTarget && !e.target.closest('#lightbox-controls') && e.target.id !== 'lightbox-img') {
    if (e.target.id !== 'lightbox') return;
  }
  var lb = document.getElementById('lightbox');
  var video = document.getElementById('lightbox-video');
  if (video) { video.pause(); video.src = ''; video.classList.add('hidden'); }
  var img = document.getElementById('lightbox-img');
  if (img) img.classList.remove('hidden');
  lb.classList.remove('show');
  document.body.style.overflow = '';
};

window.toggleZoom = function(e) {
  e.stopPropagation();
  if (window.lightboxZoom === 1) {
    window.lightboxZoom = 1.5;
    document.getElementById('lightbox-img').style.transform = 'scale(1.5)';
    document.getElementById('lightbox-img').classList.add('zoomed');
  } else {
    window.zoomReset(e);
  }
};

window.zoomIn = function(e) { e.stopPropagation(); window.lightboxZoom = Math.min(3, window.lightboxZoom + 0.5); document.getElementById('lightbox-img').style.transform = 'scale(' + window.lightboxZoom + ')'; };
window.zoomOut = function(e) { e.stopPropagation(); window.lightboxZoom = Math.max(0.5, window.lightboxZoom - 0.5); document.getElementById('lightbox-img').style.transform = 'scale(' + window.lightboxZoom + ')'; };
window.zoomReset = function(e) { if(e)e.stopPropagation(); window.lightboxZoom = 1; document.getElementById('lightbox-img').style.transform = 'scale(1)'; document.getElementById('lightbox-img').classList.remove('zoomed'); };

/* ═══════════════════════════════════════════════════════════════════
   Compare
   ═══════════════════════════════════════════════════════════════════ */
window.openCompare = function() {
  var keys = Object.keys(window.currentResults);
  if (keys.length < 2) { alert('\u81F3\u5C11\u9700\u8981 2 \u4E2A\u6210\u529F\u7ED3\u679C\u624D\u80FD\u5BF9\u6BD4'); return; }
  var container = document.getElementById('compareItems');
  container.innerHTML = '';
  for (var i = 0; i < keys.length; i++) {
    (function(pid){
      var r = window.currentResults[pid];
      if (!r.success || !r.local_path) return;
      var pInfo = window.findProvider(pid) || {name: pid, color: '#5b8def'};
      var fname = r.local_path.split(/[\\/]/).pop();
      var src = '/api/gallery/image/' + fname;
      var item = document.createElement('div');
      item.className = 'compare-item';
      item.innerHTML =
        '<img src="' + src + '" alt="' + _ea(pid) + '" onclick="openLightbox(\'' + src + '\',\'' + _ea(pid) + '\')">' +
        '<div class="compare-item-info">' +
          '<span style="font-size:11px;font-weight:600;color:' + pInfo.color + ';">' + _eh(pInfo.name) + '</span>' +
          '<a href="' + src + '" download class="btn-ghost" style="padding:3px 8px;font-size:10px;">\u2B07</a>' +
        '</div>';
      container.appendChild(item);
    })(keys[i]);
  }
  document.getElementById('compareModal').classList.add('show');
  document.body.style.overflow = 'hidden';
};

window.openCompareFromLightbox = function(e) {
  e.stopPropagation();
  window.closeLightbox();
  window.openCompare();
};

window.closeCompare = function() {
  document.getElementById('compareModal').classList.remove('show');
  document.body.style.overflow = '';
};

})();
