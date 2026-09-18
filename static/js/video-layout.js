(function () {
  'use strict';
  var page = document.getElementById('pageVideo');
  var preview = document.getElementById('videoPreviewPanel');
  var prompt = document.getElementById('videoPrompt');
  if (!page || !preview || !prompt) return;
  var layout = page.querySelector('.generate-layout');
  var body = page.querySelector('.video-composer-body');
  var frame = document.createElement('div');
  frame.className = 'video-preview-frame';
  preview.before(frame);
  frame.appendChild(preview);
  var manualHeight = null;
  var scheduled = false;

  function limit() {
    var maximum = Math.min(320, Math.floor(window.innerHeight * 0.38));
    if (window.innerWidth > 900 && window.innerHeight > 640) {
      maximum = Math.min(maximum, layout.clientHeight - 390);
    }
    return Math.max(100, maximum);
  }
  function fit() {
    scheduled = false;
    if (!prompt.getClientRects().length) return;
    var height;
    if (manualHeight !== null) {
      height = Math.max(80, Math.min(manualHeight, limit()));
    } else {
      prompt.style.height = '0px';
      height = Math.max(88, Math.min(prompt.scrollHeight + 2, 160, limit()));
    }
    prompt.style.height = height + 'px';
    prompt.style.maxHeight = limit() + 'px';
    var assetsVisible = Array.from(body.querySelectorAll('.video-assets-panel'))
      .some(function (panel) { return !panel.classList.contains('hidden'); });
    var editorHeight = Math.max(height + 36, assetsVisible ? 196 : 124);
    layout.style.setProperty('--video-editor-height', editorHeight + 'px');
    frame.querySelector('.resize-handle-bottom').setAttribute('aria-valuenow', String(editorHeight));
    frame.querySelector('.resize-handle-bottom').setAttribute('aria-valuemax', String(limit() + 36));
  }
  function schedule() {
    if (!scheduled) { scheduled = true; requestAnimationFrame(fit); }
  }
  function setHeight(height) {
    manualHeight = Math.max(80, Math.min(height, limit()));
    fit();
  }

  preview.querySelectorAll('.resize-handle-left, .resize-handle-bottom').forEach(function (old) {
    var horizontal = old.classList.contains('resize-handle-left');
    var handle = document.createElement('button');
    handle.type = 'button';
    handle.className = old.className;
    handle.setAttribute('role', 'separator');
    handle.setAttribute('aria-orientation', horizontal ? 'vertical' : 'horizontal');
    handle.setAttribute('aria-label', horizontal ? '调整视频参数栏宽度' : '调整视频预览与输入区高度');
    handle.setAttribute('aria-controls', horizontal ? 'videoPreviewPanel' : 'videoPrompt videoPreviewPanel');
    handle.title = horizontal ? '拖动或使用左右方向键调整宽度' : '拖动或使用上下方向键调整高度，双击恢复自动';
    handle.setAttribute('aria-valuemin', horizontal ? '180' : '80');
    handle.setAttribute('aria-valuemax', horizontal ? '420' : String(limit()));
    handle.setAttribute('aria-valuenow', horizontal ? '260' : '176');
    old.remove();
    frame.appendChild(handle);
    function width(value) {
      var next = Math.max(180, Math.min(value, 420, layout.clientWidth * 0.4));
      layout.style.setProperty('--video-sidebar-width', next + 'px');
      handle.setAttribute('aria-valuenow', String(Math.round(next)));
      schedule();
    }
    handle.addEventListener('pointerdown', function (event) {
      if (event.button !== 0) return;
      event.preventDefault();
      var x = event.clientX, y = event.clientY;
      var initialWidth = layout.querySelector('.generate-left').getBoundingClientRect().width;
      var initialHeight = body.getBoundingClientRect().height;
      handle.setPointerCapture(event.pointerId);
      handle.classList.add('dragging');
      function move(e) {
        if (horizontal) width(initialWidth + e.clientX - x);
        else setHeight(initialHeight - 36 - (e.clientY - y));
      }
      function stop() {
        handle.classList.remove('dragging');
        handle.removeEventListener('pointermove', move);
        handle.removeEventListener('pointerup', stop);
        handle.removeEventListener('pointercancel', stop);
        handle.removeEventListener('lostpointercapture', stop);
      }
      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', stop);
      handle.addEventListener('pointercancel', stop);
      handle.addEventListener('lostpointercapture', stop);
    });
    handle.addEventListener('keydown', function (event) {
      var negative = horizontal ? 'ArrowLeft' : 'ArrowDown';
      var positive = horizontal ? 'ArrowRight' : 'ArrowUp';
      if (event.key !== negative && event.key !== positive) return;
      event.preventDefault();
      var delta = event.key === positive ? 16 : -16;
      if (horizontal) width(layout.querySelector('.generate-left').getBoundingClientRect().width + delta);
      else setHeight(body.getBoundingClientRect().height - 36 + delta);
    });
    if (!horizontal) handle.addEventListener('dblclick', function () {
      manualHeight = null;
      fit();
    });
  });

  prompt.addEventListener('input', function () {
    if (!prompt.value) manualHeight = null;
    fit();
  });
  document.getElementById('videoPromptAuto').addEventListener('click', function () {
    manualHeight = null;
    fit();
  });
  // Native textarea resizing is deliberate; keep that height on subsequent input.
  prompt.addEventListener('pointerdown', function (event) {
    var rect = prompt.getBoundingClientRect();
    if (event.clientX < rect.right - 20 || event.clientY < rect.bottom - 20) return;
    function done() {
      setHeight(prompt.getBoundingClientRect().height);
      window.removeEventListener('pointerup', done);
      window.removeEventListener('pointercancel', done);
    }
    window.addEventListener('pointerup', done);
    window.addEventListener('pointercancel', done);
  });
  new ResizeObserver(schedule).observe(layout);
  new MutationObserver(schedule).observe(page, {attributes: true, attributeFilter: ['class']});
  body.querySelectorAll('.video-assets-panel').forEach(function (panel) {
    new MutationObserver(schedule).observe(panel, {attributes: true, attributeFilter: ['class']});
  });
  new ResizeObserver(schedule).observe(document.getElementById('videoFeedbackSlot'));
  window.addEventListener('resize', schedule);
  schedule();
})();
