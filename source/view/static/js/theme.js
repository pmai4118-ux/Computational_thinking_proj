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
    const shell = document.getElementById('app-shell');
    const sidebar = document.getElementById('app-sidebar');
    const toggle = document.getElementById('app-sidebar-toggle');
    const collapseBtn = document.getElementById('app-sidebar-collapse');
    const closeBtn = document.getElementById('app-sidebar-close');
    const backdrop = document.getElementById('app-sidebar-backdrop');
    if (shell && collapseBtn) {
      const syncCollapse = (collapsed) => {
        shell.classList.toggle('is-collapsed', collapsed);
        collapseBtn.setAttribute('aria-expanded', String(!collapsed));
        collapseBtn.title = collapsed ? 'Mở rộng thanh bên' : 'Thu gọn thanh bên';
        collapseBtn.setAttribute('aria-label', collapseBtn.title);
        const icon = collapseBtn.querySelector('.material-symbols-outlined');
        if (icon) icon.textContent = collapsed ? 'dock_to_right' : 'dock_to_left';
      };
      try {
        syncCollapse(localStorage.getItem('interviewus.sidebar') === 'collapsed');
      } catch { syncCollapse(false); }
      collapseBtn.addEventListener('click', () => {
        const collapsed = !shell.classList.contains('is-collapsed');
        syncCollapse(collapsed);
        try { localStorage.setItem('interviewus.sidebar', collapsed ? 'collapsed' : 'expanded'); } catch { /* ignore */ }
      });
    }
    if (sidebar && toggle) {
      const setOpen = (open) => {
        sidebar.classList.toggle('is-open', open);
        toggle.setAttribute('aria-expanded', String(open));
        if (backdrop) backdrop.hidden = !open;
      };
      toggle.addEventListener('click', () => setOpen(!sidebar.classList.contains('is-open')));
      closeBtn?.addEventListener('click', () => setOpen(false));
      backdrop?.addEventListener('click', () => setOpen(false));
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('is-open')) setOpen(false);
      });
    }
    const settingsBtn = document.getElementById('app-sidebar-settings');
    const settingsDialog = document.getElementById('app-settings-dialog');
    if (settingsBtn && settingsDialog) {
      settingsBtn.addEventListener('click', () => settingsDialog.showModal());
      document.getElementById('close-app-settings')?.addEventListener('click', () => settingsDialog.close());
      document.getElementById('done-app-settings')?.addEventListener('click', () => settingsDialog.close());
    }
    document.getElementById('app-sidebar-logout')?.addEventListener('click', () => {
      if (!window.confirm('Đặt lại phiên ẩn danh hiện tại trên trình duyệt này?')) return;
      try { localStorage.clear(); } catch { /* ignore */ }
      window.location.href = '/';
    });
  }, { once: true });
  window.addEventListener('storage', event => {
    if (event.key === key) apply(valid(event.newValue) ? event.newValue : 'light');
  });
})();
