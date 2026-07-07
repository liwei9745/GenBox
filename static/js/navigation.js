// ══════════════════════════════════════════════════════════════
// Navigation — Mac Dock + SPA Page Switching
// ══════════════════════════════════════════════════════════════

(function () {
  'use strict';

  // ── State ──
  let currentPage = 'dashboard';
  let dragSrcIndex = null;

  // ── Dock Navigation ──
  const dockItems = [
    { id: 'dashboard', label: '系统看板', emoji: '📊', badge: null },
    { id: 'generate', label: '生图', emoji: '✨', badge: null },
    { id: 'video', label: '生视频', emoji: '🎬', badge: null },
    { id: 'gallery', label: '媒体库', emoji: '🖼', badge: null },
    { id: 'history', label: '历史', emoji: '📜', badge: null },
  ];

  const dockSettings = [
    { id: 'provider-settings', label: '模型设置', emoji: '⚙', action: 'openProviderModal()' },
    { id: 'prompt-settings', label: '提示词优化设置', emoji: '🤖', action: "openProviderModal('llm')" },
    { id: 'theme-settings', label: '主题设置', emoji: '🎨', action: 'openThemeModal()' },
    { id: 'log-view', label: '查看日志', emoji: '📋', action: 'openLogModal()' },
    { id: 'refresh', label: '刷新页面', emoji: '↻', action: 'location.reload()' },
  ];

  // ── Build Dock ──
  function buildDock() {
    const wrapper = document.createElement('div');
    wrapper.className = 'dock-wrapper';
    wrapper.innerHTML = `
      <nav class="dock" id="mainDock">
        ${dockItems.map((item, i) => `
          <div class="dock-item${item.id === currentPage ? ' active' : ''}"
               data-page="${item.id}"
               draggable="true"
               data-index="${i}">
            <div class="dock-icon">
              <span class="dock-emoji">${item.emoji}</span>
              ${item.badge ? `<span class="dock-badge">${item.badge}</span>` : ''}
            </div>
            <span class="dock-label">${item.label}</span>
          </div>
        `).join('')}
        <div class="dock-divider"></div>
        <div class="dock-settings-group">
          ${dockSettings.map(item => `
            <div class="dock-item" data-action="${item.action}">
              <div class="dock-icon" style="background:var(--bg-inset);">
                <span class="dock-emoji">${item.emoji}</span>
              </div>
              <span class="dock-label">${item.label}</span>
            </div>
          `).join('')}
        </div>
      </nav>
    `;
    document.body.appendChild(wrapper);
  }

  // ── Switch Page ──
  function switchPage(pageId) {
    // Hide all pages
    document.querySelectorAll('[id^="page"]').forEach(p => p.classList.add('hidden'));

    // Show target page
    const target = document.getElementById('page' + capitalize(pageId));
    if (target) {
      target.classList.remove('hidden');
      target.classList.add('animate-fade-in');
    }

    // Update dock active state
    document.querySelectorAll('.dock-item').forEach(item => {
      item.classList.toggle('active', item.dataset.page === pageId);
    });

    // Update sidebar nav (legacy compat)
    document.querySelectorAll('.nav-item').forEach(item => {
      const navPage = item.id?.replace('nav', '').toLowerCase();
      if (navPage) {
        item.classList.toggle('active', navPage === pageId || 
          (pageId === 'generate' && navPage === 'gen'));
      }
    });

    currentPage = pageId;

    // Trigger page-specific load
    if (typeof window.onPageSwitch === 'function') {
      window.onPageSwitch(pageId);
    }
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  // ── Drag to Reorder ──
  function initDockDrag() {
    const dock = document.getElementById('mainDock');
    if (!dock) return;

    dock.addEventListener('dragstart', (e) => {
      const item = e.target.closest('.dock-item');
      if (!item || !item.dataset.page) return;
      dragSrcIndex = parseInt(item.dataset.index);
      item.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });

    dock.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      const item = e.target.closest('.dock-item');
      if (item) item.classList.add('drag-over');
    });

    dock.addEventListener('dragleave', (e) => {
      const item = e.target.closest('.dock-item');
      if (item) item.classList.remove('drag-over');
    });

    dock.addEventListener('drop', (e) => {
      e.preventDefault();
      const item = e.target.closest('.dock-item');
      if (!item || dragSrcIndex === null) return;

      const targetIndex = parseInt(item.dataset.index);
      if (dragSrcIndex !== targetIndex) {
        // Reorder in data
        const [moved] = dockItems.splice(dragSrcIndex, 1);
        dockItems.splice(targetIndex, 0, moved);
        // Rebuild dock
        rebuildDock();
      }

      item.classList.remove('drag-over');
    });

    dock.addEventListener('dragend', (e) => {
      document.querySelectorAll('.dock-item').forEach(i => {
        i.classList.remove('dragging', 'drag-over');
      });
      dragSrcIndex = null;
    });
  }

  function rebuildDock() {
    const oldDock = document.getElementById('mainDock');
    if (oldDock) oldDock.remove();
    buildDock();
    initDockEvents();
    initDockDrag();
  }

  // ── Dock Events ──
  function initDockEvents() {
    document.querySelectorAll('.dock-item[data-page]').forEach(item => {
      item.addEventListener('click', () => switchPage(item.dataset.page));
    });

    document.querySelectorAll('.dock-item[data-action]').forEach(item => {
      item.addEventListener('click', () => {
        const action = item.dataset.action;
        if (action === 'location.reload()') {
          location.reload();
        } else {
          try { eval(action); } catch (e) { console.warn('Dock action error:', e); }
        }
      });
    });
  }

  // ── Update Badge ──
  window.updateDockBadge = function (pageId, count) {
    const item = document.querySelector(`.dock-item[data-page="${pageId}"] .dock-icon`);
    if (!item) return;
    let badge = item.querySelector('.dock-badge');
    if (count > 0) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'dock-badge';
        item.appendChild(badge);
      }
      badge.textContent = count > 99 ? '99+' : count;
    } else if (badge) {
      badge.remove();
    }
  };

  // ── Expose switchNav for legacy compat ──
  window.switchNav = function (pageId, el) {
    switchPage(pageId);
  };

  // ── Init ──
  function init() {
    // Remove old sidebar if present
    const oldSidebar = document.querySelector('.sidebar');
    if (oldSidebar) oldSidebar.style.display = 'none';

    // Build new dock
    buildDock();
    initDockEvents();
    initDockDrag();

    // Show initial page
    switchPage(currentPage);
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for external use
  window.dockNav = { switchPage, currentPage: () => currentPage };
})();
