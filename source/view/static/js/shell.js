/* Shared Studio Blocks Shell Behaviors — interviewUS
 * Handles accessible mobile navigation drawer, aria-current synchronization,
 * and safe DOM-based inline backtick code formatting. No network calls.
 */
(() => {
  "use strict";

  const SKIP_TAGS = new Set([
    "CODE",
    "PRE",
    "TEXTAREA",
    "SCRIPT",
    "STYLE",
    "INPUT",
    "OPTION",
    "SELECT",
  ]);

  function syncActiveNav() {
    const pageId = (document.body && document.body.dataset && document.body.dataset.page) || "";
    const links = document.querySelectorAll("#site-nav-menu .site-nav__link[data-nav]");
    for (const link of links) {
      if (pageId && link.dataset.nav === pageId) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  }

  function initMobileDrawer() {
    const header = document.querySelector(".site-header");
    const toggle = document.querySelector("#site-nav-toggle");
    const nav = document.querySelector("#site-nav-menu");
    if (!header || !toggle || !nav) return;

    header.setAttribute("data-nav-enhanced", "true");

    const setOpen = (open, { restoreFocus = false } = {}) => {
      header.classList.toggle("is-nav-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Đóng menu điều hướng" : "Mở menu điều hướng");
      if (!open && restoreFocus && typeof toggle.focus === "function") {
        toggle.focus();
      }
    };

    toggle.addEventListener("click", () => {
      const isOpen = toggle.getAttribute("aria-expanded") === "true";
      setOpen(!isOpen);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && header.classList.contains("is-nav-open")) {
        setOpen(false, { restoreFocus: true });
      }
    });

    document.addEventListener("click", (event) => {
      if (
        header.classList.contains("is-nav-open") &&
        event.target instanceof Node &&
        !header.contains(event.target)
      ) {
        setOpen(false);
      }
    });

    if (typeof window.matchMedia === "function") {
      const desktopQuery = window.matchMedia("(min-width: 48.01rem)");
      const handleViewportChange = (ev) => {
        if (ev.matches && header.classList.contains("is-nav-open")) {
          setOpen(false);
        }
      };
      if (typeof desktopQuery.addEventListener === "function") {
        desktopQuery.addEventListener("change", handleViewportChange);
      }
    }
  }

  /**
   * Safely converts inline `code` backtick spans in text nodes inside `root`
   * into <code class="sbx-inline-code"> elements using DOM APIs (no innerHTML).
   */
  function formatInlineCode(root) {
    if (!root || typeof document.createTreeWalker !== "function") return;
    const textNodes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let current = walker.nextNode();
    while (current) {
      const parent = current.parentElement;
      if (
        parent &&
        !SKIP_TAGS.has(parent.tagName) &&
        !parent.closest("code, pre, textarea, script, style") &&
        current.nodeValue &&
        current.nodeValue.includes("`")
      ) {
        textNodes.push(current);
      }
      current = walker.nextNode();
    }

    const pattern = /`([^`\r\n]+)`/g;
    for (const textNode of textNodes) {
      const source = textNode.nodeValue || "";
      if (source.includes("```")) continue;
      pattern.lastIndex = 0;
      let lastIndex = 0;
      let match = pattern.exec(source);
      if (!match) continue;

      const fragment = document.createDocumentFragment();
      while (match) {
        if (match.index > lastIndex) {
          fragment.appendChild(document.createTextNode(source.slice(lastIndex, match.index)));
        }
        const codeEl = document.createElement("code");
        codeEl.className = "sbx-inline-code";
        codeEl.textContent = match[1];
        fragment.appendChild(codeEl);
        lastIndex = match.index + match[0].length;
        match = pattern.exec(source);
      }
      if (lastIndex < source.length) {
        fragment.appendChild(document.createTextNode(source.slice(lastIndex)));
      }
      if (textNode.parentNode) {
        textNode.parentNode.replaceChild(fragment, textNode);
      }
    }
  }

  function formatAllInlineCode() {
    const targets = document.querySelectorAll("[data-inline-code]");
    for (const target of targets) {
      formatInlineCode(target);
    }
  }

  function init() {
    syncActiveNav();
    initMobileDrawer();
    formatAllInlineCode();
  }

  window.interviewUSShell = Object.freeze({
    formatInlineCode,
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
