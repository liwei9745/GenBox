(function () {
  'use strict';
  var prompt = document.getElementById('videoPrompt');
  if (!prompt) return;
  var dialog = document.createElement('dialog');
  dialog.id = 'videoToolsDialog';
  dialog.className = 'video-tools-dialog';
  dialog.setAttribute('aria-labelledby', 'videoToolsTitle');
  document.body.appendChild(dialog);
  var opener = null;
  dialog.addEventListener('close', function () { if (opener) opener.focus(); });
  dialog.addEventListener('pointerdown', function (event) {
    if (!event.target.closest('#videoToolsTitle')) return;
    event.preventDefault();
    var rect = dialog.getBoundingClientRect();
    var startX = event.clientX;
    var startY = event.clientY;
    var startLeft = rect.left;
    var startTop = rect.top;
    dialog.classList.add('is-dragging');
    function move(moveEvent) {
      var maxLeft = Math.max(8, window.innerWidth - rect.width - 8);
      var maxTop = Math.max(8, window.innerHeight - rect.height - 8);
      var left = Math.max(8, Math.min(maxLeft, startLeft + moveEvent.clientX - startX));
      var top = Math.max(8, Math.min(maxTop, startTop + moveEvent.clientY - startY));
      dialog.style.left = left + 'px';
      dialog.style.top = top + 'px';
      dialog.style.right = 'auto';
      dialog.style.bottom = 'auto';
    }
    function stop() {
      dialog.classList.remove('is-dragging');
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
    }
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
  });

  function button(label, handler) {
    var node = document.createElement('button');
    node.type = 'button';
    node.className = 'btn-ghost';
    node.textContent = label;
    node.addEventListener('click', handler);
    return node;
  }
  function open(title, trigger) {
    opener = trigger;
    dialog.replaceChildren();
    var heading = document.createElement('h3');
    heading.id = 'videoToolsTitle';
    heading.className = 'video-tools-dialog-title';
    heading.title = '拖动标题栏移动窗口';
    heading.textContent = title;
    dialog.appendChild(heading);
    if (!dialog.dataset.positioned) {
      dialog.style.left = Math.max(12, Math.round((window.innerWidth - 440) / 2)) + 'px';
      dialog.style.top = Math.max(12, Math.round((window.innerHeight - 360) / 2)) + 'px';
      dialog.style.right = 'auto';
      dialog.style.bottom = 'auto';
      dialog.dataset.positioned = 'true';
    }
  }
  function actions() {
    var row = document.createElement('div');
    row.className = 'video-tools-actions';
    row.appendChild(button('取消', function () { dialog.close(); }));
    dialog.appendChild(row);
    return row;
  }
  function changed() { prompt.dispatchEvent(new Event('input', {bubbles: true})); }
  function busy() {
    return window.videoElapsedTimer !== null || window.videoPollTimer !== null ||
      Object.keys(window.videoActivePollTasks || {}).length > 0;
  }

  document.getElementById('videoNewSession').addEventListener('click', function () {
    if (busy()) { window.alert('视频任务仍在运行，请等待任务结束后再新建会话。'); return; }
    open('新会话', this);
    var note = document.createElement('p');
    note.textContent = '清空当前提示词、附件和会话预览，保留模型选择与已保存的图库文件。';
    dialog.appendChild(note);
    actions().appendChild(button('确认新会话', function () {
      if (busy()) { dialog.close(); return; }
      prompt.value = '';
      changed();
      window.videoImages = [];
      window.kfImages = [];
      window.renderVideoImagePreview();
      window.renderKfImagePreview();
      ['videoFileInput', 'kfFileInput'].forEach(function (id) { document.getElementById(id).value = ''; });
      window.videoHistoryItems = [];
      window.videoPreviewGroups = {};
      window.videoGroupNavIdx = {};
      window.videoPreviewPlaceholders = {};
      window.currentVideoTaskId = null;
      document.querySelectorAll('#videoPreviewResults video').forEach(function (video) { video.pause(); });
      document.getElementById('videoPreviewResults').replaceChildren();
      document.getElementById('videoPreviewResults').classList.add('hidden');
      document.getElementById('videoPreviewEmpty').classList.remove('hidden');
      document.getElementById('videoPreviewEmpty').style.display = 'flex';
      window.renderVideoHistory();
      window.clearVideoLog();
      document.getElementById('videoProgressBar').classList.add('hidden');
      document.getElementById('videoPerProviderSection').classList.add('hidden');
      ['videoTaskStatus', 'videoResultCount'].forEach(function (id) { document.getElementById(id).textContent = ''; });
      dialog.close();
      prompt.focus();
    }));
    dialog.showModal();
  });
  document.getElementById('videoAttach').addEventListener('click', function () {
    if (window.currentVideoMode === 'ti2vid') window.switchVideoSubTab('i2vid');
    document.getElementById(window.currentVideoMode === 'keyframes' ? 'kfFileInput' : 'videoFileInput').click();
  });
  document.getElementById('videoWebSearch').addEventListener('click', function () {
    open('网络搜索', this);
    var label = document.createElement('label');
    label.htmlFor = 'videoSearchQuery';
    label.textContent = '搜索关键词';
    var input = document.createElement('input');
    input.id = 'videoSearchQuery';
    input.type = 'search';
    input.maxLength = 300;
    var note = document.createElement('p');
    note.textContent = '仅将这里输入的关键词发送至 Bing，并打开新标签页；不会让视频模型自动联网。';
    dialog.append(label, input, note);
    var row = actions();
    function search() {
      if (!input.value.trim()) { input.focus(); return; }
      window.open('https://www.bing.com/search?q=' + encodeURIComponent(input.value.trim()),
        '_blank', 'noopener,noreferrer');
      dialog.close();
    }
    row.appendChild(button('搜索', search));
    input.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); search(); }
    });
    dialog.showModal();
    input.focus();
  });
  document.getElementById('videoQuickPrompt').addEventListener('click', function () {
    open('快速提示词', this);
    var choices = [
      ['镜头推进', '镜头缓慢向主体推进，运动平稳，保持主体清晰。'],
      ['环绕镜头', '镜头平稳环绕主体，保持主体外观与场景连续。'],
      ['自然动作', '主体做自然、连贯的动作，避免突兀跳变。'],
      ['光照氛围', '采用柔和自然光，保持光源方向和阴影一致。'],
      ['主体一致', '保持主体的外观、服装和比例一致。']
    ];
    var list = document.createElement('div');
    list.className = 'video-quick-options';
    choices.forEach(function (choice) {
      var item = button(choice[0] + '：' + choice[1], function () {
        prompt.value += (prompt.value.trim() ? '\n' : '') + choice[1];
        changed();
        dialog.close();
        prompt.focus();
        prompt.setSelectionRange(prompt.value.length, prompt.value.length);
        prompt.scrollTop = prompt.scrollHeight;
      });
      list.appendChild(item);
    });
    dialog.appendChild(list);
    actions();
    dialog.showModal();
  });
})();
