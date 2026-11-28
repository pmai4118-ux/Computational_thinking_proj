/* Apply shared theme & shell preferences before paint; resilient when storage is disabled. */
(() => {
  'use strict';
  const root = document.documentElement;
  const THEME_KEY = 'interviewus.theme';
  const LEGACY_THEME_KEY = 'interviewus.home-theme';
  const SIDEBAR_KEY = 'interviewus.sidebar';
  const valid = value => value === 'light' || value === 'dark';

  let theme = 'light';
  try {
    const saved = localStorage.getItem(THEME_KEY);
    const legacy = localStorage.getItem(LEGACY_THEME_KEY);
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
      try { localStorage.setItem(THEME_KEY, mode); } catch { /* Optional preference. */ }
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

    let syncCollapse = () => {};
    if (shell && collapseBtn) {
      syncCollapse = (collapsed) => {
        shell.classList.toggle('is-collapsed', collapsed);
        collapseBtn.setAttribute('aria-expanded', String(!collapsed));
        collapseBtn.title = collapsed ? 'Mở rộng thanh bên' : 'Thu gọn thanh bên';
        collapseBtn.setAttribute('aria-label', collapseBtn.title);
        const icon = collapseBtn.querySelector('.material-symbols-outlined');
        if (icon) icon.textContent = collapsed ? 'dock_to_right' : 'dock_to_left';
      };
      try {
        syncCollapse(localStorage.getItem(SIDEBAR_KEY) === 'collapsed');
      } catch {
        syncCollapse(false);
      }
      collapseBtn.addEventListener('click', () => {
        const collapsed = !shell.classList.contains('is-collapsed');
        syncCollapse(collapsed);
        try {
          localStorage.setItem(SIDEBAR_KEY, collapsed ? 'collapsed' : 'expanded');
        } catch { /* Optional preference. */ }
      });
    }

    if (sidebar && toggle) {
      const setOpen = (open, restoreFocus = false) => {
        sidebar.classList.toggle('is-open', open);
        toggle.setAttribute('aria-expanded', String(open));
        if (backdrop) backdrop.hidden = !open;
        if (!open && restoreFocus) toggle.focus();
      };
      toggle.addEventListener('click', () => setOpen(!sidebar.classList.contains('is-open')));
      closeBtn?.addEventListener('click', () => setOpen(false, true));
      backdrop?.addEventListener('click', () => setOpen(false, false));
      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && sidebar.classList.contains('is-open')) {
          setOpen(false, true);
        }
      });
    }

    const settingsBtn = document.getElementById('app-sidebar-settings');
    const settingsDialog = document.getElementById('app-settings-dialog');
    const resetBtn = document.getElementById('app-reset-preferences');
    const resetStatus = document.getElementById('app-reset-status');

    if (settingsBtn && settingsDialog) {
      settingsBtn.addEventListener('click', () => {
        if (resetStatus) {
          resetStatus.hidden = true;
          resetStatus.textContent = '';
        }
        if (typeof settingsDialog.showModal === 'function') {
          settingsDialog.showModal();
        }
      });
      document.getElementById('close-app-settings')?.addEventListener('click', () => settingsDialog.close());
      document.getElementById('done-app-settings')?.addEventListener('click', () => settingsDialog.close());
      settingsDialog.addEventListener('click', (event) => {
        if (event.target === settingsDialog) settingsDialog.close();
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        try {
          localStorage.removeItem(THEME_KEY);
          localStorage.removeItem(LEGACY_THEME_KEY);
          localStorage.removeItem(SIDEBAR_KEY);
        } catch { /* Storage may be unavailable; still reset current view. */ }
        apply('light', false);
        syncCollapse(false);
        if (resetStatus) {
          resetStatus.textContent = 'Đã đặt lại giao diện sáng và thanh bên mặc định. Các phiên luyện tập trên máy chủ vẫn được giữ nguyên.';
          resetStatus.hidden = false;
        }
      });
    }
  }, { once: true });

  window.addEventListener('storage', event => {
    if (event.key === THEME_KEY) {
      apply(valid(event.newValue) ? event.newValue : 'light');
    }
  });
})();
