(function () {
  'use strict';

  function providerFor(id) {
    var list = window.videoProviders || [];
    return list.find(function (provider) { return provider.id === id; }) || null;
  }

  function providerName(provider, fallback) {
    return provider ? (provider.display_name || provider.name || fallback) : fallback;
  }

  function safeText(value) {
    if (typeof window.escHtml === 'function') return window.escHtml(value == null ? '' : String(value));
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char];
    });
  }

  function videoSource(item) {
    return item && (item.video_url_local || item.video_url || '');
  }

  function openVideoPreviewLightbox(item) {
    var source = videoSource(item);
    var lightbox = document.getElementById('lightbox');
    var image = document.getElementById('lightbox-img');
    var video = document.getElementById('lightbox-video');
    var download = document.getElementById('lightbox-dl');
    var info = document.getElementById('lightbox-info');
    var promptBox = document.getElementById('lightbox-prompt-box');
    var prompt = document.getElementById('lightbox-prompt');
    if (!source || !lightbox || !video) return;

    if (image) {
      image.src = '';
      image.classList.add('hidden');
    }
    video.src = source;
    video.controls = true;
    video.loop = true;
    video.classList.remove('hidden');
    if (download) {
      download.href = source;
      download.download = 'video_' + Date.now() + '.mp4';
      download.classList.remove('hidden');
      download.textContent = typeof window.i18nText === 'function' ? window.i18nText('video.download') : '\u2B07\uFE0F \u4E0B\u8F7D';
    }
    var provider = providerFor(item.provider_id);
    var label = providerName(provider, item.provider_id || '\u89C6\u9891');
    if (info) info.textContent = [label, item.model || '', item.elapsed_seconds ? Math.round(item.elapsed_seconds) + 's' : ''].filter(Boolean).join(' \u00B7 ');

    window.lightboxCurrentPrompt = item.prompt || '';
    if (prompt) prompt.textContent = item.prompt || '';
    if (promptBox) promptBox.style.display = item.prompt ? 'block' : 'none';
    var promptLabel = promptBox && promptBox.querySelector('.lb-prompt-label');
    if (promptLabel) promptLabel.textContent = typeof window.i18nText === 'function' ? window.i18nText('video.prompt_lightbox') : '\uD83D\uDCDD \u751F\u89C6\u9891\u63D0\u793A\u8BCD';

    lightbox.classList.add('show');
    document.body.style.overflow = 'hidden';
    video.play().catch(function () {});
  }

  function renderVideoGroupedPreview() {
    var container = document.getElementById('videoPreviewResults');
    var empty = document.getElementById('videoPreviewEmpty');
    var count = document.getElementById('videoResultCount');
    var groups = window.videoPreviewGroups || {};
    if (!container) return;

    var allItems = [];
    Object.keys(groups).forEach(function (providerId) {
      allItems = allItems.concat(groups[providerId] || []);
    });
    if (!allItems.length) {
      container.style.display = 'none';
      if (empty) empty.style.display = 'flex';
      if (count) count.textContent = '';
      return;
    }

    if (empty) empty.style.display = 'none';
    container.classList.remove('hidden');
    container.style.display = 'grid';
    if (count) count.textContent = allItems.length + ' ' + (typeof window.i18nText === 'function' ? window.i18nText('video.result_count_unit') : '\u4E2A\u7ED3\u679C');
    container.replaceChildren();

    Object.keys(groups).forEach(function (providerId) {
      var items = groups[providerId] || [];
      if (!items.length) return;
      var provider = providerFor(providerId);
      var color = provider && provider.color ? provider.color : 'var(--accent)';
      var name = providerName(provider, providerId);
      var completed = items.filter(function (item) { return item.status === 'completed'; });
      var failed = items.filter(function (item) { return item.status !== 'completed'; });

      var group = document.createElement('section');
      group.className = 'video-result-group fade-in';
      var header = document.createElement('div');
      header.className = 'video-result-group-header';
      var title = document.createElement('div');
      title.className = 'video-result-group-title';
      title.innerHTML = '<span style="width:7px;height:7px;border-radius:50%;background:' + safeText(color) + ';display:inline-block;flex:0 0 auto;"></span><span>' + safeText(name) + '</span>';
      var status = document.createElement('span');
      status.className = 'video-result-group-status';
      status.textContent = (completed.length ? '\u2713 ' + completed.length + ' \u5B8C\u6210' : '') +
        (completed.length && failed.length ? ' \u00B7 ' : '') +
        (failed.length ? '\u2717 ' + failed.length + ' \u5931\u8D25' : '');
      header.appendChild(title);
      header.appendChild(status);
      group.appendChild(header);

      var grid = document.createElement('div');
      grid.className = 'video-result-grid';
      items.forEach(function (item) {
        var card = document.createElement('article');
        card.className = 'prev-card video-result-card ' + (item.status === 'completed' ? 'completed' : 'failed');
        var source = videoSource(item);
        if (item.status === 'completed' && source) {
          card.tabIndex = 0;
          card.setAttribute('aria-label', '\u6253\u5F00 ' + name + ' \u89C6\u9891\u9884\u89C8');
        } else {
          card.setAttribute('role', 'alert');
        }

        var media = document.createElement('div');
        media.className = 'video-result-media';
        if (item.status === 'completed' && source) {
          var video = document.createElement('video');
          video.src = source;
          video.muted = true;
          video.preload = 'metadata';
          video.setAttribute('aria-hidden', 'true');
          video.addEventListener('loadedmetadata', function () {
            try { video.currentTime = Math.min(0.1, video.duration || 0.1); } catch (error) {}
          });
          media.appendChild(video);
          var open = function () { openVideoPreviewLightbox(item); };
          card.addEventListener('click', open);
          card.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              open();
            }
          });
        } else {
          media.classList.add('video-result-error');
          media.textContent = item.error || '\u89C6\u9891\u751F\u6210\u5931\u8D25';
        }
        card.appendChild(media);

        var footer = document.createElement('div');
        footer.className = 'prev-footer';
        footer.innerHTML =
          '<div style="display:flex;align-items:center;gap:5px;min-width:0;">' +
            '<span class="provider-dot" style="background:' + safeText(color) + ';"></span>' +
            '<span class="provider-name">' + safeText(name) + '</span>' +
            (item.model ? '<span style="font-size:9px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + safeText(item.model) + '</span>' : '') +
          '</div>' +
          '<span class="elapsed-badge">' + (item.status === 'completed' ? '\u5B8C\u6210' : '\u5931\u8D25') + '</span>';
        card.appendChild(footer);

        var meta = document.createElement('div');
        meta.className = 'video-result-meta';
        var promptMeta = document.createElement('span');
        promptMeta.textContent = item.prompt || '';
        promptMeta.title = item.prompt || '';
        var elapsedMeta = document.createElement('span');
        elapsedMeta.textContent = item.elapsed_seconds ? '\u23F1 ' + Math.round(item.elapsed_seconds) + 's' : '';
        meta.appendChild(promptMeta);
        meta.appendChild(elapsedMeta);
        card.appendChild(meta);

        if (item.status === 'completed' && source) {
          var actions = document.createElement('div');
          actions.className = 'video-result-actions';
          var download = document.createElement('button');
          download.type = 'button';
          download.className = 'btn-secondary';
          download.textContent = '\u2B07\uFE0F \u4E0B\u8F7D';
          download.addEventListener('click', function (event) {
            event.stopPropagation();
            if (typeof window.downloadVideoFromSrc === 'function') window.downloadVideoFromSrc(source);
          });
          var push = document.createElement('button');
          push.type = 'button';
          push.className = 'btn-secondary';
          push.textContent = '\uD83D\uDDBC \u63A8\u5230\u56FE\u5E93';
          push.addEventListener('click', function (event) {
            event.stopPropagation();
            if (typeof window.pushVideoToGalleryFromSrc === 'function') window.pushVideoToGalleryFromSrc(source);
          });
          actions.appendChild(download);
          actions.appendChild(push);
          card.appendChild(actions);
        }
        grid.appendChild(card);
      });
      group.appendChild(grid);
      container.appendChild(group);
    });
  }

  window.openVideoPreviewLightbox = openVideoPreviewLightbox;
  window.renderVideoGroupedPreview = renderVideoGroupedPreview;
  window.playVideoItem = function (url) {
    var groups = window.videoPreviewGroups || {};
    var found = null;
    Object.keys(groups).some(function (providerId) {
      return (groups[providerId] || []).some(function (item) {
        if (videoSource(item) === url) {
          found = item;
          return true;
        }
        return false;
      });
    });
    if (found) openVideoPreviewLightbox(found);
  };
}());
