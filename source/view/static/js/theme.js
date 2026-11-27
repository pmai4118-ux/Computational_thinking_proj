/* Apply the shared preference before styles paint; all pages use the same key. */
(() => {
  'use strict';
  const root = document.documentElement;
  const key = 'interviewus.theme';
  const valid = value => value === 'light' || value === 'dark';
  let theme = 'light';
  try {
    const saved = localStorage.getItem(key);
    const legacy = localStorage.getItem('interviewus.home-theme');
    if (valid(saved)) theme = saved;
    else if (valid(legacy)) theme = legacy;
  } catch { /* Storage may be unavailable; controls still work for this page. */ }
  const apply = (mode, persist = false) => {
    if (!valid(mode)) return;
    theme = mode;
    root.dataset.theme = mode;
    document.querySelectorAll('[data-theme-mode]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.themeMode === mode));
    });
    if (persist) {
      try { localStorage.setItem(key, mode); } catch { /* Optional preference. */ }
    }
  };
  apply(theme);
  document.addEventListener('DOMContentLoaded', () => {
    apply(theme);
    document.querySelectorAll('[data-theme-mode]').forEach(button => {
      button.addEventListener('click', () => apply(button.dataset.themeMode, true));
    });
  }, { once: true });
  window.addEventListener('storage', event => {
    if (event.key === key) apply(valid(event.newValue) ? event.newValue : 'light');
  });
})();
