// ══════════════════════════════════════════════════════════════
// Theme — Light/Dark Mode Toggle + Persistence
// ══════════════════════════════════════════════════════════════

(function () {
  'use strict';

  const STORAGE_KEY = 'genbox-theme';
  const DARK_CLASS = 'dark';

  // ── Get stored theme or system preference ──
  function getStoredTheme() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) return stored;
    } catch (e) {}
    // Fall back to system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  // ── Apply theme ──
  function applyTheme(theme) {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
      document.body.classList.add(DARK_CLASS);
    } else {
      root.removeAttribute('data-theme');
      document.body.classList.remove(DARK_CLASS);
    }

    // Update toggle icon if present
    const toggle = document.getElementById('themeToggle');
    if (toggle) {
      toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
      toggle.title = theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式';
    }

    // Dispatch event for other components
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  }

  // ── Toggle theme ──
  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (e) {}
  }

  // ── Listen for system preference changes ──
  function watchSystemTheme() {
    if (!window.matchMedia) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', (e) => {
      // Only auto-switch if user hasn't manually set a preference
      try {
        if (!localStorage.getItem(STORAGE_KEY)) {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      } catch (err) {}
    });
  }

  // ── Init ──
  function init() {
    const theme = getStoredTheme();
    applyTheme(theme);
    watchSystemTheme();

    // Expose for external use
    window.themeToggle = toggleTheme;
    window.setTheme = applyTheme;
    window.getTheme = () => document.documentElement.getAttribute('data-theme') || 'light';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
