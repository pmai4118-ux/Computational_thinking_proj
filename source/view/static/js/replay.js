(() => {
  "use strict";

  const root = document.querySelector("[data-replay-studio]");
  if (!root) return;

  const api = window.InterviewApi;
  const runId = root.dataset.runId;
  const initialScript = document.querySelector("#replay-initial-data");
  const liveAnnouncer = document.querySelector("#replay-live-announcer");
  const errorBox = document.querySelector("#replay-error");

  const promptDrawer = document.querySelector("#replay-prompt-drawer");
  const fullPromptToggle = document.querySelector("#replay-toggle-full-prompt");
  const fullPromptPanel = document.querySelector("#replay-full-prompt-panel");

  const treeStage = document.querySelector("#replay-tree-stage");
  const overviewHint = document.querySelector("#replay-overview-hint");
  const modeCompactBtn = document.querySelector("#replay-mode-compact");
  const overviewBtn = document.querySelector("#replay-overview-btn");
  const parentBtn = document.querySelector("#replay-parent-btn");
  const overviewLayer = document.querySelector("#replay-overview-layer");
  const genStatus = document.querySelector("#replay-gen-status");
  const genError = document.querySelector("#replay-gen-error");
  const genErrorMsg = document.querySelector("#replay-gen-error-msg");
  const genRetryBtn = document.querySelector("#replay-gen-retry-btn");
  const treeViewport = document.querySelector("#replay-tree-viewport");
  const treeSurface = document.querySelector("#replay-tree-surface");
  const treeNav = document.querySelector("#replay-tree-nav");
  const zoomOutBtn = document.querySelector("#replay-zoom-out");
  const zoomInBtn = document.querySelector("#replay-zoom-in");
  const zoomFitBtn = document.querySelector("#replay-zoom-fit");
  const zoomLevelEl = document.querySelector("#replay-zoom-level");

  const detailLayer = document.querySelector("#replay-detail-layer");
  const breadcrumbsNav = document.querySelector("#replay-breadcrumbs");
  const detailCloseBtn = document.querySelector("#replay-detail-close-btn");
  const detailCard = document.querySelector("#replay-detail-card");
  const nodeKicker = document.querySelector("#replay-node-kicker");
  const nodeAiTag = document.querySelector("#replay-node-ai-tag");
  const nodeTitle = document.querySelector("#replay-node-title");
  const detailLoading = document.querySelector("#replay-detail-loading");
  const detailError = document.querySelector("#replay-detail-error");
  const detailErrorMsg = document.querySelector("#replay-detail-error-msg");
  const detailRetryBtn = document.querySelector("#replay-detail-retry-btn");
  const detailErrorParentBtn = document.querySelector("#replay-detail-error-parent-btn");
  const detailErrorOverviewBtn = document.querySelector("#replay-detail-error-overview-btn");
  const detailContent = document.querySelector("#replay-detail-content");

  const nodeLead = document.querySelector("#replay-node-lead");
  const nodeSecondary = document.querySelector("#replay-node-secondary");
  const terminalVerdict = document.querySelector("#replay-terminal-verdict");
  const verdictBadges = document.querySelector("#replay-verdict-badges");
  const verdictSafety = document.querySelector("#replay-verdict-safety");
  const verdictOperational = document.querySelector("#replay-verdict-operational");

  const simDetails = document.querySelector("#replay-sim-details");
  const simDetailsBody = document.querySelector("#replay-sim-details-body");

  const childrenSection = document.querySelector("#replay-children-section");
  const childrenList = document.querySelector("#replay-children-list");
  const customPending = document.querySelector("#replay-custom-pending");
  const customExhaustedNote = document.querySelector("#replay-custom-exhausted-note");
  const customPanel = document.querySelector("#replay-custom-panel");
  const customForm = document.querySelector("#replay-custom-form");
  const customParentInput = document.querySelector("#replay-custom-parent-id");
  const customQuota = document.querySelector("#replay-custom-quota");
  const customInput = document.querySelector("#replay-custom-input");
  const customCount = document.querySelector("#replay-custom-count");
  const customError = document.querySelector("#replay-custom-error");
  const customErrorMsg = document.querySelector("#replay-custom-error-msg");
  const customRetryBtn = document.querySelector("#replay-custom-retry-btn");
  const customCancelBtn = document.querySelector("#replay-custom-cancel");
  const customSubmit = document.querySelector("#replay-custom-submit");

  const terminalActions = document.querySelector("#replay-terminal-actions");
  const terminalParentBtn = document.querySelector("#replay-terminal-parent-btn");
  const terminalOverviewBtn = document.querySelector("#replay-terminal-overview-btn");

  const openAnswerBtn = document.querySelector("#replay-open-answer-btn");
  const answerDialog = document.querySelector("#replay-answer-dialog");
  const closeAnswerBtn = document.querySelector("#replay-close-answer-btn");
  const answerQuoteNote = document.querySelector("#replay-answer-quote-note");
  const answerHost = document.querySelector("#replay-answer-source");

  const MORPH_ENTER_MS = 240;
  const MORPH_EXIT_MS = 210;
  const MORPH_EASING = "cubic-bezier(0.23, 1, 0.32, 1)";
  const MAX_PROPOSAL_CHARS = 1000;
  const MIN_ZOOM = 0.45;
  const MAX_ZOOM = 1.5;
  const ZOOM_STEP = 0.15;
  const POLL_INTERVAL_MS = 750;

  let runState = null;
  let viewMode = "overview";
  let focusedNodeId = null;
  let lastOpenedNodeId = null;
  let customPanelOpen = false;
  let customBusy = false;
  let navBusy = false;
  let transitionToken = 0;
  let activeMorph = null;
  let pendingRetryRequest = null;
  let dialogOpen = false;
  let dialogReturnFocus = null;
  let pollTimer = null;
  let renderedTreeButtons = new Map();
  let renderedProposeBtn = null;
  let camera = { scale: 1, tx: 0, ty: 0, userAdjusted: false };
  let savedCamera = null;
  let savedTopologyKey = "";
  let currentTopologyKey = "";
  let newlyRevealedParentForReturn = null;
  const explicitlyOpenedIds = new Set();
  const revealedParents = new Set();
  const collapsedParents = new Set();

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function addClass(node, name) {
    if (!node) return;
    if (node.classList && typeof node.classList.add === "function") {
      node.classList.add(name);
      return;
    }
    const parts = (node.className || "").split(/\s+/).filter(Boolean);
    if (!parts.includes(name)) parts.push(name);
    node.className = parts.join(" ");
  }

  function removeClass(node, name) {
    if (!node) return;
    if (node.classList && typeof node.classList.remove === "function") {
      node.classList.remove(name);
      return;
    }
    node.className = (node.className || "")
      .split(/\s+/)
      .filter((part) => part && part !== name)
      .join(" ");
  }

  function prefersReducedMotion() {
    if (typeof window.matchMedia !== "function") return true;
    try {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (_ignored) {
      return true;
    }
  }

  function isSplitViewport() {
    if (typeof window.matchMedia !== "function") return false;
    try {
      return Boolean(window.matchMedia("(min-width: 60rem)").matches);
    } catch (_ignored) {
      return false;
    }
  }

  function isTreeCanvasVisible() {
    return viewMode === "overview" || isSplitViewport();
  }

  function canAnimateLayout() {
    if (prefersReducedMotion()) return false;
    if (typeof document.body === "undefined" || !document.body) return false;
    return (
      typeof requestAnimationFrame === "function" &&
      detailCard &&
      typeof detailCard.getBoundingClientRect === "function"
    );
  }

  function announce(message) {
    if (!liveAnnouncer || !message) return;
    liveAnnouncer.textContent = liveAnnouncer.textContent === message ? `${message}\u00A0` : message;
  }

  function setPageError(message) {
    if (!errorBox) return;
    if (!message) {
      errorBox.hidden = true;
      errorBox.textContent = "";
      return;
    }
    errorBox.textContent = message;
    errorBox.hidden = false;
    if (typeof errorBox.focus === "function") errorBox.focus();
  }

  function setStageBusy(isBusy) {
    if (treeStage && typeof treeStage.setAttribute === "function") {
      treeStage.setAttribute("aria-busy", isBusy ? "true" : "false");
    }
  }

  function setViewAttr(mode) {
    viewMode = mode;
    if (root && root.dataset) root.dataset.viewMode = mode;
  }

  function getNodeMap(state) {
    const map = new Map();
    for (const n of (state && state.nodes) || []) map.set(n.id, n);
    return map;
  }

  function deriveTreeIndex(state, nodeMap) {
    const parentOf = new Map();
    const childrenByParent = new Map();

    for (const n of (state && state.nodes) || []) {
      if (n.parent_id) parentOf.set(n.id, n.parent_id);
      for (const opt of n.options || []) {
        if (opt.target_node_id && !parentOf.has(opt.target_node_id)) {
          parentOf.set(opt.target_node_id, n.id);
        }
      }
    }
    if (state) parentOf.delete(state.root_node_id);

    // Respect explicit parent.options order first, then any remaining linked children.
    for (const n of (state && state.nodes) || []) {
      const ordered = [];
      const seen = new Set();
      for (const opt of n.options || []) {
        const child = nodeMap.get(opt.target_node_id);
        if (child && !seen.has(child.id)) {
          seen.add(child.id);
          ordered.push({ node: child, optionId: opt.option_id, optionLabel: opt.label });
        }
      }
      childrenByParent.set(n.id, ordered);
    }
    for (const n of (state && state.nodes) || []) {
      if (state && n.id === state.root_node_id) continue;
      const pId = parentOf.get(n.id) || (state && state.root_node_id);
      if (!pId || !nodeMap.has(pId)) continue;
      const list = childrenByParent.get(pId) || [];
      if (!list.some((entry) => entry.node.id === n.id)) {
        list.push({ node: n, optionId: null, optionLabel: n.branch_label || n.title });
        childrenByParent.set(pId, list);
      }
    }

    const computePath = (id) => {
      const path = [];
      const seen = new Set();
      let cur = id;
      while (cur && nodeMap.has(cur) && !seen.has(cur)) {
        seen.add(cur);
        path.push(cur);
        cur = parentOf.get(cur) || null;
      }
      path.reverse();
      return path;
    };

    return { parentOf, childrenByParent, computePath };
  }

  function isNodeSeen(nodeId, state) {
    const visited = new Set((state && state.visited_node_ids) || []);
    if (!state) return false;
    if (nodeId === state.root_node_id) {
      return explicitlyOpenedIds.has(nodeId) || visited.size > 1;
    }
    return visited.has(nodeId) || explicitlyOpenedIds.has(nodeId);
  }

  const TITLE_PREFIX_RULES = [
    { re: /^kết\s*quả\s*mô\s*phỏng\s*[:\-–—]\s*/i, kicker: "Hệ quả" },
    { re: /^kết\s*cục\s*[:\-–—]\s*/i, kicker: "Hệ quả" },
    { re: /^hệ\s*quả\s*[:\-–—]\s*/i, kicker: "Hệ quả" },
    { re: /^thử\s*nhánh\s*tự\s*đề\s*xuất\s*[:\-–—]\s*/i, kicker: "Tự đề xuất" },
    { re: /^tự\s*thử\s*[:\-–—]\s*/i, kicker: "Tự đề xuất" },
    { re: /^phương\s*án\s*bạn\s*đề\s*xuất\s*[:\-–—]\s*/i, kicker: "Tự đề xuất" },
    { re: /^điểm\s*xuất\s*phát(?:\s*từ\s*bài\s*làm)?\s*[:\-–—]\s*/i, kicker: "Xuất phát" },
    { re: /^điểm\s*rẽ(?:\s*tiếp\s*theo)?\s*[:\-–—]\s*/i, kicker: "Điểm rẽ" },
    { re: /^(nhánh\s*\d+(?:\s*\/\s*\d+)?)\s*[:\-–—]\s*/i, kickerFromMatch: 1 },
    { re: /^(phương\s*án\s*\d+)\s*[:\-–—]\s*/i, kickerFromMatch: 1 },
    { re: /^(hướng\s*\d+)\s*[:\-–—]\s*/i, kickerFromMatch: 1 },
    { re: /^(lựa\s*chọn\s*\d+)\s*[:\-–—]\s*/i, kickerFromMatch: 1 },
  ];

  function parseNodeTitleParts(node, state) {
    if (!node) return { kicker: "", title: "" };
    const raw = (node.branch_label || node.title || "").trim();
    const isRoot = Boolean(state && node.id === state.root_node_id);
    const isCustom = node.origin === "custom_user_branch";

    let extractedKicker = "";
    let cleanTitle = raw;

    for (const rule of TITLE_PREFIX_RULES) {
      const m = cleanTitle.match(rule.re);
      if (m) {
        const rest = cleanTitle.slice(m[0].length).trim();
        if (rest) {
          extractedKicker = rule.kickerFromMatch ? m[rule.kickerFromMatch].trim() : rule.kicker;
          cleanTitle = rest.charAt(0).toUpperCase() + rest.slice(1);
          break;
        }
      }
    }

    let kicker = extractedKicker;
    if (!kicker) {
      if (isRoot) {
        kicker = "Xuất phát";
      } else if (isCustom) {
        kicker = "Tự đề xuất";
      } else if (node.is_terminal) {
        kicker = "Hệ quả";
      } else {
        kicker = "Chiến lược";
      }
    }

    return { kicker, title: cleanTitle || raw };
  }

  function nodeDisplayName(node, state) {
    return parseNodeTitleParts(node, state || runState).title;
  }

  function classifyNodeSeverity(node, state) {
    if (!node) return { key: "branch", label: "" };
    const refState = state || runState;
    if (refState && node.id === refState.root_node_id) {
      return { key: "root", label: "" };
    }
    if (!node.is_terminal) {
      return { key: "branch", label: "" };
    }
    const invs = node.invariants || [];
    if (!invs.length) {
      return { key: "neutral", label: "Chưa rõ" };
    }
    if (invs.some((i) => i.status === "broken")) {
      return { key: "danger", label: "Vi phạm" };
    }
    if (invs.some((i) => i.status === "warning" || i.status === "uncertain")) {
      return { key: "warning", label: "Cảnh báo" };
    }
    const safetyItems = invs.filter((i) => i.category !== "operational");
    const operationalItems = invs.filter((i) => i.category === "operational");
    if (
      safetyItems.length > 0 &&
      operationalItems.length > 0 &&
      safetyItems.every((i) => i.status === "preserved") &&
      operationalItems.every((i) => i.status === "preserved")
    ) {
      return { key: "safe", label: "An toàn" };
    }
    return { key: "neutral", label: "Chưa rõ" };
  }

  function buildCardTopRow(parts, sev, isTerminal) {
    const topRow = el("div", "dtree__top-row");
    if (parts.kicker) {
      topRow.append(el("span", "dtree__kicker", parts.kicker));
    }
    if (isTerminal && sev && sev.label) {
      const sevPill = el("span", `dtree__sev dtree__sev--${sev.key}`);
      const dot = el("span", "dtree__sev-dot");
      if (typeof dot.setAttribute === "function") dot.setAttribute("aria-hidden", "true");
      sevPill.append(dot, document.createTextNode(sev.label));
      topRow.append(sevPill);
    }
    return topRow;
  }

  function applyDetailCardSemantic(node, state) {
    if (!detailCard) return;
    removeClass(detailCard, "replay-detail-card--safe");
    removeClass(detailCard, "replay-detail-card--warning");
    removeClass(detailCard, "replay-detail-card--danger");
    if (!node || !node.is_terminal) return;
    const sev = classifyNodeSeverity(node, state);
    if (sev.key === "safe" || sev.key === "warning" || sev.key === "danger") {
      addClass(detailCard, `replay-detail-card--${sev.key}`);
    }
  }

  function updateActivePathSpines() {
    if (!treeNav || typeof treeNav.querySelectorAll !== "function") return;
    const lists = treeNav.querySelectorAll("ul.dtree__children");
    for (const ul of lists) {
      let activeLi = null;
      for (const child of ul.children || []) {
        const cls = child.className || "";
        if (cls.includes("dtree__item") && cls.includes("is-in-path")) {
          activeLi = child;
          break;
        }
      }
      if (!activeLi || !ul.style || typeof ul.style.setProperty !== "function") continue;
      const ulHeight = ul.offsetHeight || 0;
      const childHeight = activeLi.offsetHeight || 0;
      if (!ulHeight || !childHeight) continue;
      const parentMid = ulHeight / 2;
      const childMid = (activeLi.offsetTop || 0) + childHeight / 2;
      const top = Math.min(parentMid, childMid) - 1.25;
      const height = Math.abs(childMid - parentMid) + 2.5;
      ul.style.setProperty("--active-spine-top", `${Math.round(top * 10) / 10}px`);
      ul.style.setProperty("--active-spine-height", `${Math.round(height * 10) / 10}px`);
    }
  }

  function firstSentence(text) {
    const raw = String(text || "").trim();
    if (!raw) return "";
    for (let i = 0; i < raw.length; i += 1) {
      const ch = raw[i];
      if (ch !== "." && ch !== "!" && ch !== "?") continue;
      if (ch === "." && raw[i + 1] === ".") continue;
      if (ch === "." && i > 0 && raw[i - 1] === ".") continue;
      const next = raw[i + 1];
      if (ch === "." && next && /\d/.test(next)) continue;
      if (!next || /\s/.test(next)) {
        return raw.slice(0, i + 1).trim();
      }
    }
    return raw;
  }

  function cleanClause(text) {
    return String(text || "").trim().replace(/[.。;]+$/, "");
  }

  function evaluateNodeDimensions(node) {
    const invs = (node && node.invariants) || [];
    const safetyItems = invs.filter((item) => item.category !== "operational");
    const operationalItems = invs.filter((item) => item.category === "operational");

    const safetyPass = safetyItems.filter((i) => i.status === "preserved");
    const safetyBroken = safetyItems.filter((i) => i.status === "broken");
    const safetyUncertain = safetyItems.filter((i) => i.status === "uncertain" || i.status === "warning");

    let safety;
    if (!safetyItems.length) {
      safety = {
        cls: "badge--neutral",
        badgeText: "Dữ liệu: Chưa có kết luận",
        lineText: "Chưa có kết luận",
      };
    } else if (safetyBroken.length === 1) {
      const violated = cleanClause(safetyBroken[0].name);
      const preservedPart = safetyPass.length
        ? `, vẫn giữ ${safetyPass.map((i) => cleanClause(i.name)).join(", ")}`
        : "";
      safety = {
        cls: "badge--unmet",
        badgeText: "Dữ liệu: Có vi phạm",
        lineText: `Vi phạm ${violated}${preservedPart}.`,
      };
    } else if (safetyBroken.length > 1) {
      const preservedPart = safetyPass.length
        ? `; vẫn giữ ${safetyPass.map((i) => cleanClause(i.name)).join(", ")}`
        : "";
      safety = {
        cls: "badge--unmet",
        badgeText: "Dữ liệu: Vi phạm bất biến",
        lineText: `Vi phạm ${safetyBroken.map((i) => cleanClause(i.name)).join("; ")}${preservedPart}.`,
      };
    } else if (safetyUncertain.length === safetyItems.length) {
      const detail = firstSentence(safetyUncertain[0].detail);
      safety = {
        cls: "badge--unresolved",
        badgeText: "Dữ liệu: Chưa có kết luận",
        lineText: detail ? `Chưa có kết luận — ${detail}` : "Chưa có kết luận",
      };
    } else if (safetyUncertain.length > 0) {
      safety = {
        cls: "badge--unresolved",
        badgeText: "Dữ liệu: Chưa có kết luận",
        lineText: `Giữ được ${safetyPass.map((i) => cleanClause(i.name)).join(", ")}; chưa có kết luận cho ${safetyUncertain.map((i) => cleanClause(i.name)).join(", ")}.`,
      };
    } else {
      const lineText =
        safetyItems.length === 1
          ? firstSentence(safetyItems[0].detail) || `${cleanClause(safetyItems[0].name)}.`
          : `Giữ nguyên ${safetyPass.length}/${safetyItems.length} điều kiện: ${safetyPass.map((i) => cleanClause(i.name)).join("; ")}.`;
      safety = {
        cls: "badge--met",
        badgeText: "Dữ liệu: Bảo toàn",
        lineText,
      };
    }

    let operational;
    if (!operationalItems.length) {
      operational = {
        evaluated: false,
        cls: "badge--neutral",
        badgeText: "Vận hành: Chưa có kết luận",
        lineText: "Chưa có kết luận",
      };
    } else {
      const brokenOp = operationalItems.find((i) => i.status === "broken");
      const warnOp = operationalItems.find((i) => i.status === "warning");
      const uncertainOp = operationalItems.find((i) => i.status === "uncertain");
      const preservedOp = operationalItems.find((i) => i.status === "preserved");
      const primary = brokenOp || warnOp || uncertainOp || preservedOp || operationalItems[0];
      const primarySentence = firstSentence(primary.detail) || primary.name;

      if (brokenOp) {
        operational = {
          evaluated: true,
          cls: "badge--unmet",
          badgeText: "Vận hành: Nguy cơ nghẽn / lỗi",
          lineText: primarySentence,
        };
      } else if (warnOp) {
        operational = {
          evaluated: true,
          cls: "badge--unresolved",
          badgeText: "Vận hành: Có rủi ro",
          lineText: primarySentence,
        };
      } else if (uncertainOp) {
        operational = {
          evaluated: true,
          cls: "badge--unresolved",
          badgeText: "Vận hành: Chưa có kết luận",
          lineText: primarySentence ? `Chưa có kết luận — ${primarySentence}` : "Chưa có kết luận",
        };
      } else {
        operational = {
          evaluated: true,
          cls: "badge--met",
          badgeText: "Vận hành: Ổn định",
          lineText: primarySentence,
        };
      }
    }

    return { safetyItems, operationalItems, safety, operational };
  }

  function classifyTraceStep(step) {
    const timeText = `${step.time_label || ""}`.toLowerCase();
    const eventText = `${step.event || ""}`.toLowerCase();
    const primaryEvent = eventText.replace(/\([^)]*\)/g, " ");
    const stateText = `${step.state_after || ""}`.toLowerCase();
    const fullText = `${timeText} ${eventText} ${stateText}`;
    const isSongSong = timeText.includes("song song") || primaryEvent.includes("song song");

    if (fullText.includes("deadlock") || fullText.includes("circular wait") || fullText.includes("vòng chờ")) {
      return { key: "error", label: "Deadlock / Chặn chéo", isConcurrent: true };
    }
    if (
      primaryEvent.includes("0 dòng") ||
      primaryEvent.includes("rowcount = 0") ||
      primaryEvent.includes("affected_rows = 0") ||
      primaryEvent.includes("không cập nhật dữ liệu") ||
      primaryEvent.includes("trả về hết hàng") ||
      primaryEvent.includes("báo hết hàng")
    ) {
      return { key: "finish", label: "Kết thúc (0 dòng)", isConcurrent: isSongSong };
    }
    if (
      primaryEvent.includes("rollback") ||
      primaryEvent.includes("thất bại") ||
      primaryEvent.includes("hủy") ||
      stateText.includes("vỡ") ||
      stateText.includes("mất hàng")
    ) {
      return { key: "rollback", label: "Rollback / Lỗi", isConcurrent: isSongSong };
    }
    if (primaryEvent.includes("commit")) {
      return { key: "commit", label: "Commit · Nhả khóa", isConcurrent: isSongSong };
    }
    if (primaryEvent.includes("nhả khóa") || primaryEvent.includes("giải phóng")) {
      return { key: "release", label: "Nhả khóa", isConcurrent: isSongSong };
    }
    if (
      primaryEvent.includes("chờ khóa") ||
      primaryEvent.includes("bị chặn") ||
      primaryEvent.includes("tạm chờ") ||
      primaryEvent.includes("đứng chờ") ||
      primaryEvent.includes("đợi ở khóa") ||
      primaryEvent.includes("treo") ||
      stateText.includes("chờ")
    ) {
      return { key: "wait", label: "Chờ khóa", isConcurrent: true };
    }
    if (
      primaryEvent.includes("lấy khóa") ||
      primaryEvent.includes("for update") ||
      primaryEvent.includes("for no key update") ||
      primaryEvent.includes("khóa") ||
      primaryEvent.includes("update")
    ) {
      return { key: "acquire", label: "Lấy khóa / Ghi", isConcurrent: isSongSong };
    }
    if (isSongSong) {
      return { key: "wait", label: "Chạy song song", isConcurrent: true };
    }
    return { key: "step", label: "Thực thi", isConcurrent: false };
  }

  function renderTraceStateChips(stateAfter) {
    const wrap = el("div", "trace-state-chips");
    const parts = String(stateAfter)
      .split(/[,;·]+/)
      .map((item) => item.trim())
      .filter(Boolean);
    if (!parts.length) return null;
    for (const part of parts) {
      const lower = part.toLowerCase();
      const isAlert =
        lower.includes("vỡ") ||
        lower.includes("mất") ||
        lower.includes("deadlock") ||
        lower.includes("âm") ||
        lower.includes("-1");
      wrap.append(el("span", `trace-state-chip${isAlert ? " trace-state-chip--alert" : ""}`, part));
    }
    return wrap;
  }

  function renderInvariantCard(inv) {
    const statusMeta = {
      preserved: { cls: "badge--met", label: "Bảo toàn" },
      warning: { cls: "badge--unresolved", label: "Có rủi ro" },
      broken: { cls: "badge--unmet", label: "Vi phạm" },
      uncertain: { cls: "badge--unresolved", label: "Chưa có kết luận" },
    };
    const meta = statusMeta[inv.status] || statusMeta.uncertain;
    const li = el("li", `invariant-card invariant-card--${inv.status}`);
    const top = el("div", "profile-entry__meta");
    top.append(el("strong", "", inv.name));
    top.append(el("span", `badge ${meta.cls}`, meta.label));
    li.append(top);
    li.append(el("p", "", inv.detail));
    return li;
  }

  function buildTraceSection(node) {
    const steps = (node && node.trace_steps) || [];
    if (!steps.length && !node.state_delta) return null;

    const section = el("div", "replay-detail-section");
    section.append(el("h4", "replay-detail-section__title", "Diễn biến mô phỏng theo mốc thời gian"));

    if (node.state_delta) {
      section.append(el("p", "state-delta-pill", node.state_delta));
    }

    if (steps.length) {
      const legend = el("div", "trace-legend");
      if (typeof legend.setAttribute === "function") {
        legend.setAttribute("aria-label", "Chú thích mốc vòng đời khóa");
      }
      const phases = [
        { cls: "trace-phase--acquire", text: "Lấy khóa / Ghi" },
        { sep: "→" },
        { cls: "trace-phase--wait", text: "Chờ khóa" },
        { sep: "→" },
        { cls: "trace-phase--commit", text: "Commit · Nhả khóa" },
        { sep: "/" },
        { cls: "trace-phase--rollback", text: "Rollback / Lỗi" },
        { sep: "/" },
        { cls: "trace-phase--finish", text: "Kết thúc (0 dòng)" },
      ];
      for (const p of phases) {
        if (p.sep) {
          const s = el("span", "trace-legend__arrow", p.sep);
          if (typeof s.setAttribute === "function") s.setAttribute("aria-hidden", "true");
          legend.append(s);
        } else {
          legend.append(el("span", `trace-phase ${p.cls}`, p.text));
        }
      }
      section.append(legend);

      const list = el("ol", "trace-list");
      steps.forEach((step, idx) => {
        const phase = classifyTraceStep(step);
        const li = el("li", `trace-step${phase.isConcurrent ? " trace-step--concurrent" : ""}`);
        const rail = el("div", "trace-step__rail");
        rail.append(el("span", "trace-step__time", step.time_label || `Bước ${idx + 1}`));
        rail.append(el("span", "trace-step__actor", step.actor));
        rail.append(el("span", `trace-phase trace-phase--${phase.key}`, phase.label));
        li.append(rail);

        const body = el("div", "trace-step__body");
        body.append(el("p", "trace-step__event", step.event));
        if (step.state_after) {
          const chips = renderTraceStateChips(step.state_after);
          if (chips) body.append(chips);
        }
        li.append(body);
        list.append(li);
      });
      section.append(list);
    }

    return section;
  }

  function renderSimulationDetails(node, state, dims) {
    if (!simDetails || !simDetailsBody) return;
    simDetailsBody.replaceChildren();
    simDetails.open = false;

    const isRoot = node.id === state.root_node_id;
    const isCustom = node.origin === "custom_user_branch";
    const assumptions =
      node.assumptions_used && node.assumptions_used.length
        ? node.assumptions_used
        : state.question_assumptions || [];

    if (isCustom && node.user_proposal) {
      const propSec = el("div", "replay-detail-section");
      propSec.append(el("h4", "replay-detail-section__title", "Nội dung đề xuất bạn đã gửi"));
      propSec.append(el("p", "replay-proposal-echo", node.user_proposal));
      simDetailsBody.append(propSec);
    }

    if (node.is_terminal && dims) {
      const criteriaSec = el("div", "replay-detail-section");
      criteriaSec.append(el("h4", "replay-detail-section__title", "Đối chiếu chi tiết theo hai nhóm tiêu chí"));
      const grid = el("div", "outcome-groups-grid");

      const safetyCol = el("div", "stack");
      safetyCol.append(el("h5", "outcome-group-title", "Tính đúng đắn dữ liệu"));
      const safetyUl = el("ul", "profile-entry-list");
      if (dims.safetyItems.length) {
        for (const inv of dims.safetyItems) safetyUl.append(renderInvariantCard(inv));
      } else {
        const empty = el("li", "invariant-card invariant-card--unassessed");
        empty.append(el("strong", "", "Chưa có kết luận"));
        empty.append(el("p", "", "Dữ liệu mô phỏng của lượt này chưa có tiêu chí tính đúng đắn dữ liệu."));
        safetyUl.append(empty);
      }
      safetyCol.append(safetyUl);

      const opCol = el("div", "stack");
      opCol.append(el("h5", "outcome-group-title", "Hiệu năng và vận hành"));
      const opUl = el("ul", "profile-entry-list");
      if (dims.operationalItems.length) {
        for (const inv of dims.operationalItems) opUl.append(renderInvariantCard(inv));
      } else {
        const unassessed = el("li", "invariant-card invariant-card--unassessed");
        const top = el("div", "profile-entry__meta");
        top.append(el("strong", "", "Chưa có kết luận"));
        top.append(el("span", "badge badge--neutral", "Chưa có kết luận"));
        unassessed.append(top);
        unassessed.append(
          el("p", "", "Lượt mô phỏng này chưa có dữ liệu đánh giá nhóm hiệu năng và vận hành.")
        );
        opUl.append(unassessed);
      }
      opCol.append(opUl);

      grid.append(safetyCol, opCol);
      criteriaSec.append(grid);
      simDetailsBody.append(criteriaSec);
    }

    if (!isRoot) {
      const traceSec = buildTraceSection(node);
      if (traceSec) simDetailsBody.append(traceSec);

      const hasImpact = Boolean(node.system_impact || node.tradeoff_note);
      if (hasImpact) {
        const techSec = el("div", "replay-detail-section");
        techSec.append(el("h4", "replay-detail-section__title", "Tác động và đánh đổi kỹ thuật"));
        const impactGrid = el("div", "impact-grid");
        if (node.system_impact) {
          const card = el("div", "impact-card");
          card.append(el("h4", "", "Tác động hệ thống"));
          card.append(el("p", "", node.system_impact));
          impactGrid.append(card);
        }
        if (node.tradeoff_note) {
          const card = el("div", "impact-card");
          card.append(el("h4", "", "Đánh đổi kỹ thuật"));
          card.append(el("p", "", node.tradeoff_note));
          impactGrid.append(card);
        }
        techSec.append(impactGrid);
        if (node.comparison_note) {
          const cmp = el("p", "replay-detail-secondary", node.comparison_note);
          techSec.append(cmp);
        }
        simDetailsBody.append(techSec);
      }
    } else if (node.trace_steps && node.trace_steps.length) {
      const traceSec = buildTraceSection(node);
      if (traceSec) simDetailsBody.append(traceSec);
    }

    if (assumptions.length) {
      const assumpSec = el("div", "replay-detail-section");
      assumpSec.append(el("h4", "replay-detail-section__title", "Giả định mô phỏng"));
      const ul = el("ul", "replay-plain-list");
      for (const item of assumptions) ul.append(el("li", "", item));
      assumpSec.append(ul);
      simDetailsBody.append(assumpSec);
    }

    simDetails.hidden = simDetailsBody.children.length === 0;
  }

  /* ------------------------------------------------------------------------
   * Formatted Submitted Answer Renderer (Paragraphs + Scrollable Code Blocks
   * + Verbatim Quote Highlight, 100% DOM-safe)
   * ------------------------------------------------------------------------ */
  function appendTextWithQuoteHighlight(parent, fullText, rangeStart, rangeEnd, quoteStart, quoteEnd, convertNewlines) {
    const appendChunk = (chunkText, highlight) => {
      if (!chunkText) return;
      if (highlight) {
        const mark = el("mark", "evidence-mark evidence-mark--active");
        if (convertNewlines) {
          const lines = chunkText.split("\n");
          lines.forEach((line, i) => {
            if (i > 0) mark.append(el("br"));
            mark.append(document.createTextNode(line));
          });
        } else {
          mark.append(document.createTextNode(chunkText));
        }
        parent.append(mark);
      } else if (convertNewlines) {
        const lines = chunkText.split("\n");
        lines.forEach((line, i) => {
          if (i > 0) parent.append(el("br"));
          parent.append(document.createTextNode(line));
        });
      } else {
        parent.append(document.createTextNode(chunkText));
      }
    };

    const hasQuote =
      Number.isInteger(quoteStart) &&
      Number.isInteger(quoteEnd) &&
      quoteEnd > quoteStart &&
      quoteStart < rangeEnd &&
      quoteEnd > rangeStart;

    if (!hasQuote) {
      appendChunk(fullText.slice(rangeStart, rangeEnd), false);
      return;
    }

    const hlStart = Math.max(rangeStart, quoteStart);
    const hlEnd = Math.min(rangeEnd, quoteEnd);
    if (hlStart > rangeStart) appendChunk(fullText.slice(rangeStart, hlStart), false);
    if (hlEnd > hlStart) appendChunk(fullText.slice(hlStart, hlEnd), true);
    if (rangeEnd > hlEnd) appendChunk(fullText.slice(hlEnd, rangeEnd), false);
  }

  function renderFormattedAnswer(state) {
    if (!answerHost) return;
    answerHost.replaceChildren();
    const answerText = state && state.linked_answer_text;
    if (!answerText) {
      if (answerQuoteNote) answerQuoteNote.hidden = true;
      answerHost.append(el("p", "text-secondary", "Không có nội dung bài trả lời gắn với lượt này."));
      return;
    }

    const nodeMap = getNodeMap(state);
    const activeNode = nodeMap.get(focusedNodeId || state.root_node_id) || nodeMap.get(state.root_node_id);
    const rootNode = nodeMap.get(state.root_node_id);
    const anchorNode =
      activeNode && activeNode.answer_alignment === "matched_from_answer" && activeNode.answer_quote
        ? activeNode
        : rootNode && rootNode.answer_alignment === "matched_from_answer" && rootNode.answer_quote
          ? rootNode
          : null;

    const qStart = anchorNode && Number.isInteger(anchorNode.answer_quote_start) ? anchorNode.answer_quote_start : null;
    const qEnd = anchorNode && Number.isInteger(anchorNode.answer_quote_end) ? anchorNode.answer_quote_end : null;

    if (answerQuoteNote) {
      if (qStart !== null && qEnd !== null && qEnd > qStart) {
        answerQuoteNote.textContent = "Đoạn tô sáng là trích đoạn khớp với điểm xuất phát trên cây.";
        answerQuoteNote.hidden = false;
      } else {
        answerQuoteNote.hidden = true;
      }
    }

    // Parse fenced code blocks (```lang\n...\n```) while preserving exact character offsets.
    const fenceRegex = /```[^\n]*\n([\s\S]*?)```/g;
    let cursor = 0;
    let match;

    const appendProseRange = (startIdx, endIdx) => {
      if (endIdx <= startIdx) return;
      const slice = answerText.slice(startIdx, endIdx);
      const sepRegex = /\n{2,}/g;
      let segStart = 0;
      let sep;
      while ((sep = sepRegex.exec(slice)) !== null) {
        const rawSeg = slice.slice(segStart, sep.index);
        const leading = rawSeg.length - rawSeg.trimStart().length;
        const trailing = rawSeg.length - rawSeg.trimEnd().length;
        const absStart = startIdx + segStart + leading;
        const absEnd = startIdx + sep.index - trailing;
        if (absEnd > absStart) {
          const p = el("p", "replay-answer-p");
          appendTextWithQuoteHighlight(p, answerText, absStart, absEnd, qStart, qEnd, true);
          answerHost.append(p);
        }
        segStart = sep.index + sep[0].length;
      }
      const tail = slice.slice(segStart);
      const leading = tail.length - tail.trimStart().length;
      const trailing = tail.length - tail.trimEnd().length;
      const absStart = startIdx + segStart + leading;
      const absEnd = endIdx - trailing;
      if (absEnd > absStart) {
        const p = el("p", "replay-answer-p");
        appendTextWithQuoteHighlight(p, answerText, absStart, absEnd, qStart, qEnd, true);
        answerHost.append(p);
      }
    };

    while ((match = fenceRegex.exec(answerText)) !== null) {
      appendProseRange(cursor, match.index);
      const openLineEnd = answerText.indexOf("\n", match.index);
      const codeStart = openLineEnd !== -1 ? openLineEnd + 1 : match.index + 3;
      const codeEnd = match.index + match[0].length - 3;
      const pre = el("pre", "code-block replay-answer-code");
      const code = el("code");
      appendTextWithQuoteHighlight(code, answerText, codeStart, Math.max(codeStart, codeEnd), qStart, qEnd, false);
      pre.append(code);
      answerHost.append(pre);
      cursor = match.index + match[0].length;
    }

    appendProseRange(cursor, answerText.length);
  }

  /* ------------------------------------------------------------------------
   * Modal Dialog (Submitted Answer) — Focus Trap + Escape + Focus Restore
   * ------------------------------------------------------------------------ */
  function getDialogFocusable() {
    if (!answerDialog || typeof answerDialog.querySelectorAll !== "function") {
      return closeAnswerBtn ? [closeAnswerBtn] : [];
    }
    const selectors = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';
    return Array.from(answerDialog.querySelectorAll(selectors)).filter((node) => !node.hidden);
  }

  function openAnswerDialog() {
    if (!answerDialog || dialogOpen) return;
    dialogOpen = true;
    dialogReturnFocus = (document && document.activeElement) || openAnswerBtn;
    if (runState) renderFormattedAnswer(runState);

    answerDialog.hidden = false;
    if (document.body && document.body.style) {
      document.body.style.overflow = "hidden";
    }
    if (!prefersReducedMotion() && typeof requestAnimationFrame === "function") {
      addClass(answerDialog, "is-entering");
      requestAnimationFrame(() => {
        removeClass(answerDialog, "is-entering");
      });
    }

    if (closeAnswerBtn && typeof closeAnswerBtn.focus === "function") {
      closeAnswerBtn.focus();
    }
  }

  function closeAnswerDialog() {
    if (!answerDialog || !dialogOpen) return;
    dialogOpen = false;
    if (document.body && document.body.style) {
      document.body.style.overflow = "";
    }

    const finishClose = () => {
      if (dialogOpen) return;
      removeClass(answerDialog, "is-leaving");
      answerDialog.hidden = true;
      const target = dialogReturnFocus || openAnswerBtn;
      if (target && typeof target.focus === "function") target.focus();
    };

    if (!prefersReducedMotion() && typeof setTimeout === "function") {
      addClass(answerDialog, "is-leaving");
      setTimeout(finishClose, 155);
    } else {
      finishClose();
    }
  }

  function handleGlobalKeydown(event) {
    if (!event) return;
    if (dialogOpen) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeAnswerDialog();
        return;
      }
      if (event.key === "Tab") {
        const focusables = getDialogFocusable();
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const current = document.activeElement;
        if (event.shiftKey && (current === first || !focusables.includes(current))) {
          event.preventDefault();
          if (typeof last.focus === "function") last.focus();
        } else if (!event.shiftKey && current === last) {
          event.preventDefault();
          if (typeof first.focus === "function") first.focus();
        }
      }
      return;
    }

    if (event.key === "Escape" && customPanelOpen && !customBusy) {
      event.preventDefault();
      closeCustomPanel({ returnFocus: true });
      return;
    }

    if (event.key === "Escape" && viewMode === "detail" && !customBusy) {
      event.preventDefault();
      returnToOverview();
    }
  }

  /* ------------------------------------------------------------------------
   * FLIP Spatial Morph Helper (Interruptible & Reduced-Motion Safe)
   * ------------------------------------------------------------------------ */
  function cancelActiveMorph() {
    if (!activeMorph) return;
    const { anim, ghost, sourceEl } = activeMorph;
    activeMorph = null;
    if (anim && typeof anim.cancel === "function") {
      try { anim.cancel(); } catch (_ignored) { /* ignore */ }
    }
    if (ghost && typeof ghost.remove === "function") ghost.remove();
    if (sourceEl) removeClass(sourceEl, "is-morph-source");
    if (detailCard) removeClass(detailCard, "is-morph-hidden");
    if (detailLayer && detailLayer.style) {
      detailLayer.style.position = "";
      detailLayer.style.inset = "";
      detailLayer.style.pointerEvents = "";
    }
    if (overviewLayer) {
      removeClass(overviewLayer, "is-exiting");
      removeClass(overviewLayer, "is-entering");
    }
    if (treeNav && typeof treeNav.querySelectorAll === "function") {
      for (const item of treeNav.querySelectorAll(".dtree__item.is-dimmed")) {
        removeClass(item, "is-dimmed");
      }
    }
  }

  function runMorphRect({ fromRect, toRect, titleText, durationMs, sourceEl }) {
    if (
      !canAnimateLayout() ||
      !fromRect ||
      !toRect ||
      !fromRect.width ||
      !fromRect.height ||
      !toRect.width ||
      !toRect.height
    ) {
      return Promise.resolve();
    }

    const ghost = el("div", "replay-morph-shell");
    ghost.append(el("p", "replay-morph-shell__title", titleText || ""));
    if (typeof ghost.setAttribute === "function") ghost.setAttribute("aria-hidden", "true");
    document.body.append(ghost);

    const hasWaapi = typeof ghost.animate === "function";
    if (!hasWaapi) {
      ghost.remove();
      return Promise.resolve();
    }

    const anim = ghost.animate(
      [
        {
          transform: `translate3d(${fromRect.left}px, ${fromRect.top}px, 0)`,
          width: `${fromRect.width}px`,
          height: `${fromRect.height}px`,
        },
        {
          transform: `translate3d(${toRect.left}px, ${toRect.top}px, 0)`,
          width: `${toRect.width}px`,
          height: `${toRect.height}px`,
        },
      ],
      {
        duration: durationMs,
        easing: MORPH_EASING,
        fill: "forwards",
      }
    );

    activeMorph = { anim, ghost, sourceEl };
    return anim.finished
      .catch(() => {})
      .then(() => {
        if (activeMorph && activeMorph.ghost === ghost) {
          activeMorph = null;
        }
        if (typeof ghost.remove === "function") ghost.remove();
        if (sourceEl) removeClass(sourceEl, "is-morph-source");
      });
  }

  /* ------------------------------------------------------------------------
   * Overview Camera (Auto-Fit, Zoom In/Out, Drag-to-Pan, ResizeObserver)
   * ------------------------------------------------------------------------ */
  function clampZoom(value) {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(value * 100) / 100));
  }

  function applyCamera({ smooth = false } = {}) {
    if (treeViewport) {
      treeViewport.scrollLeft = 0;
      treeViewport.scrollTop = 0;
    }
    if (treeSurface) {
      if (smooth && !prefersReducedMotion()) {
        addClass(treeSurface, "is-camera-smooth");
      } else {
        removeClass(treeSurface, "is-camera-smooth");
      }
      if (treeSurface.style) {
        const tx = Math.round(camera.tx * 10) / 10;
        const ty = Math.round(camera.ty * 10) / 10;
        treeSurface.style.transform = `translate3d(${tx}px, ${ty}px, 0) scale(${camera.scale})`;
      }
    }
    const pct = `${Math.round(camera.scale * 100)}%`;
    if (zoomLevelEl) zoomLevelEl.textContent = pct;
    if (zoomOutBtn) zoomOutBtn.disabled = camera.scale <= MIN_ZOOM + 0.001;
    if (zoomInBtn) zoomInBtn.disabled = camera.scale >= MAX_ZOOM - 0.001;
  }

  function fitTreeToViewport({ animate = true } = {}) {
    camera.userAdjusted = false;
    if (!treeViewport || !treeSurface || !treeNav) {
      camera.scale = 1;
      camera.tx = 0;
      camera.ty = 0;
      applyCamera({ smooth: false });
      return;
    }

    const vpW = treeViewport.clientWidth || 0;
    const vpH = treeViewport.clientHeight || 0;
    const treeW = treeNav.scrollWidth || treeNav.offsetWidth || 0;
    const treeH = treeNav.scrollHeight || treeNav.offsetHeight || 0;

    if (!vpW || !vpH || !treeW || !treeH) {
      camera.scale = 1;
      camera.tx = 0;
      camera.ty = 0;
      applyCamera({ smooth: false });
      return;
    }

    const isNarrow = vpW < 640;
    const padX = isNarrow ? 10 : 28;
    const padTop = 16;
    const padBottom = 56;
    const availW = Math.max(120, vpW - padX * 2);
    const availH = Math.max(120, vpH - padTop - padBottom);

    const rawScale = Math.min(availW / treeW, availH / treeH);
    const minFit = isNarrow ? 0.56 : 0.52;
    const maxFit = isNarrow ? 1.0 : 1.18;
    const scale = clampZoom(Math.min(maxFit, Math.max(minFit, rawScale)));

    const scaledW = treeW * scale;
    const scaledH = treeH * scale;
    const tx = scaledW <= availW ? (vpW - scaledW) / 2 : padX;
    const ty = scaledH <= availH ? padTop + (availH - scaledH) / 2 : padTop;

    camera.scale = scale;
    camera.tx = tx;
    camera.ty = ty;
    applyCamera({ smooth: animate });
  }

  function scheduleFitTree({ animate = true } = {}) {
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(() => {
        if (isTreeCanvasVisible()) fitTreeToViewport({ animate });
      });
    } else if (isTreeCanvasVisible()) {
      fitTreeToViewport({ animate: false });
    }
  }

  function zoomBy(delta, pivotClientX, pivotClientY) {
    const prevScale = camera.scale;
    const nextScale = clampZoom(prevScale + delta);
    if (Math.abs(nextScale - prevScale) < 0.001) return;

    const ratio = nextScale / prevScale;
    let pivotX = 0;
    let pivotY = 0;
    if (treeViewport) {
      const vpW = treeViewport.clientWidth || 0;
      const vpH = treeViewport.clientHeight || 0;
      if (
        typeof pivotClientX === "number" &&
        typeof pivotClientY === "number" &&
        typeof treeViewport.getBoundingClientRect === "function"
      ) {
        const rect = treeViewport.getBoundingClientRect();
        pivotX = pivotClientX - rect.left;
        pivotY = pivotClientY - rect.top;
      } else {
        pivotX = vpW / 2;
        pivotY = vpH / 2;
      }
    }

    camera.tx = pivotX - (pivotX - camera.tx) * ratio;
    camera.ty = pivotY - (pivotY - camera.ty) * ratio;
    camera.scale = nextScale;
    camera.userAdjusted = true;
    applyCamera({ smooth: pivotClientX === undefined });
  }

  /* ------------------------------------------------------------------------
   * Progressive Discovery & Async Background Tree Generation Polling
   * ------------------------------------------------------------------------ */
  function stopGenerationPoll() {
    if (pollTimer !== null) {
      if (typeof clearTimeout === "function") clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function syncRevealedParents(state) {
    if (!state) return;
    if ((state.generation_status || "ready") !== "ready") return;

    revealedParents.add(state.root_node_id);
    for (const vid of state.visited_node_ids || []) {
      if (!collapsedParents.has(vid)) revealedParents.add(vid);
    }

    const nodeMap = getNodeMap(state);
    const { computePath } = deriveTreeIndex(state, nodeMap);
    for (const node of state.nodes || []) {
      if (node.origin === "custom_user_branch") {
        for (const ancId of computePath(node.id)) {
          if (ancId !== node.id && !collapsedParents.has(ancId)) {
            revealedParents.add(ancId);
          }
        }
      }
    }
    if (lastOpenedNodeId && nodeMap.has(lastOpenedNodeId)) {
      for (const ancId of computePath(lastOpenedNodeId)) {
        if (!collapsedParents.has(ancId)) revealedParents.add(ancId);
      }
    }
  }

  function isParentExpandedOnTree(nodeId, state) {
    if (!state) return false;
    if (nodeId === state.root_node_id) return true;
    return revealedParents.has(nodeId) && !collapsedParents.has(nodeId);
  }

  function getExpandableNonRootParentIds(state) {
    if (!state || (state.generation_status || "ready") !== "ready") return [];
    const nodeMap = getNodeMap(state);
    const { childrenByParent } = deriveTreeIndex(state, nodeMap);
    const ids = [];
    for (const node of state.nodes || []) {
      if (node.id === state.root_node_id) continue;
      const kids = childrenByParent.get(node.id) || [];
      if (kids.length > 0) ids.push(node.id);
    }
    return ids;
  }

  function isFullTreeExpanded(state) {
    const expandable = getExpandableNonRootParentIds(state);
    if (!expandable.length) return true;
    return expandable.every((id) => isParentExpandedOnTree(id, state));
  }

  function expandBranchOnTree(parentId, parentLabel) {
    if (!runState) return;
    revealedParents.add(parentId);
    collapsedParents.delete(parentId);
    renderOverviewTree(runState, {
      highlightNodeId: focusedNodeId || lastOpenedNodeId,
      animateParentId: parentId,
    });
    updateStageControls(runState);
    if (!camera.userAdjusted) {
      scheduleFitTree({ animate: true });
    }
    announce(`Đã mở rộng các nhánh con của ${parentLabel}.`);
  }

  function collapseBranchOnTree(parentId, parentLabel) {
    if (!runState) return;
    collapsedParents.add(parentId);
    renderOverviewTree(runState, { highlightNodeId: focusedNodeId || lastOpenedNodeId });
    updateStageControls(runState);
    if (!camera.userAdjusted) {
      scheduleFitTree({ animate: true });
    }
    announce(`Đã thu gọn các nhánh con của ${parentLabel}.`);
  }

  function setCompactTreeMode() {
    if (!runState || customBusy) return;
    const expandable = getExpandableNonRootParentIds(runState);
    for (const id of expandable) {
      collapsedParents.add(id);
    }
    if (viewMode === "detail" && !isSplitViewport()) {
      return returnToOverview();
    }
    renderOverviewTree(runState, { highlightNodeId: focusedNodeId || lastOpenedNodeId });
    updateStageControls(runState);
    if (isTreeCanvasVisible()) {
      camera.userAdjusted = false;
      scheduleFitTree({ animate: true });
    }
    announce("Đã thu gọn các nhánh phụ.");
  }

  function setFullTreeMode() {
    if (!runState || customBusy) return;
    const expandable = getExpandableNonRootParentIds(runState);
    const hadCollapsed = expandable.some((id) => !isParentExpandedOnTree(id, runState));
    for (const id of expandable) {
      revealedParents.add(id);
      collapsedParents.delete(id);
    }
    if (viewMode === "detail" && !isSplitViewport()) {
      return returnToOverview();
    }
    renderOverviewTree(runState, {
      highlightNodeId: focusedNodeId || lastOpenedNodeId,
      animateExpandedAll: hadCollapsed,
    });
    updateStageControls(runState);
    if (isTreeCanvasVisible() && (hadCollapsed || !camera.userAdjusted)) {
      camera.userAdjusted = false;
      scheduleFitTree({ animate: true });
    }
    announce("Đã mở toàn bộ cây quyết định.");
  }

  async function pollGenerationOnce() {
    pollTimer = null;
    if (!runState || (runState.generation_status || "ready") !== "generating") return;
    if (!api || typeof api.getReplayRun !== "function") return;
    try {
      const updated = await api.getReplayRun(runId);
      runState = updated;
      const status = updated.generation_status || "ready";
      if (status === "ready") {
        stopGenerationPoll();
        syncRevealedParents(runState);
        updateStageControls(runState);
        renderOverviewTree(runState, {
          highlightNodeId: lastOpenedNodeId,
          animateRootChildren: true,
        });
        if (answerHost && runState.linked_answer_text) {
          renderFormattedAnswer(runState);
        }
        scheduleFitTree({ animate: true });
        announce("Đã khởi tạo xong các nhánh quyết định. Chọn một nhánh để xem kết quả.");
        return;
      }
      if (status === "failed") {
        stopGenerationPoll();
        updateStageControls(runState);
        renderOverviewTree(runState, { highlightNodeId: null });
        announce("Chưa khởi tạo được cây quyết định. Có thể bấm Thử tạo lại.");
        return;
      }
    } catch (_ignored) {
      /* Transient poll error; retry on next interval */
    }
    if (runState && (runState.generation_status || "ready") === "generating") {
      scheduleGenerationPoll();
    }
  }

  function scheduleGenerationPoll() {
    stopGenerationPoll();
    if (typeof setTimeout !== "function") return;
    pollTimer = setTimeout(() => pollGenerationOnce(), POLL_INTERVAL_MS);
  }

  async function retryTreeGeneration() {
    if (!api || typeof api.retryReplayGeneration !== "function") return;
    if (genRetryBtn) genRetryBtn.disabled = true;
    try {
      const updated = await api.retryReplayGeneration(runId);
      runState = updated;
      updateStageControls(runState);
      renderOverviewTree(runState, { highlightNodeId: null });
      scheduleFitTree({ animate: false });
      if ((updated.generation_status || "ready") === "generating") {
        scheduleGenerationPoll();
      }
    } catch (err) {
      if (genErrorMsg) {
        genErrorMsg.textContent = (err && err.message) || "Chưa thể khởi tạo lại cây quyết định.";
      }
      if (genError) genError.hidden = false;
    } finally {
      if (genRetryBtn) genRetryBtn.disabled = false;
    }
  }

  /* ------------------------------------------------------------------------
   * Stage Toolbar, Overview Tree & Breadcrumb Renderers
   * ------------------------------------------------------------------------ */
  function updateStageControls(state) {
    const genState = (state && state.generation_status) || "ready";
    const nodeMap = getNodeMap(state);
    const { parentOf } = deriveTreeIndex(state, nodeMap);
    const currentId = viewMode === "detail" ? focusedNodeId : null;
    const currentNode = currentId ? nodeMap.get(currentId) : null;
    const parentId = currentNode ? currentNode.parent_id || parentOf.get(currentNode.id) || null : null;
    const splitMode = isSplitViewport();
    const expandable = getExpandableNonRootParentIds(state);
    const fullExpanded = genState === "ready" && isFullTreeExpanded(state);

    if (overviewHint) {
      if (genState !== "ready") {
        overviewHint.hidden = true;
      } else if (viewMode === "overview") {
        overviewHint.textContent = "Chọn một nhánh để xem kết quả";
        overviewHint.hidden = false;
      } else if (splitMode) {
        overviewHint.textContent = "Chọn nhánh khác trên sơ đồ để so sánh nhanh";
        overviewHint.hidden = false;
      } else {
        overviewHint.hidden = true;
      }
    }
    if (modeCompactBtn) {
      if (typeof modeCompactBtn.setAttribute === "function") {
        modeCompactBtn.setAttribute(
          "aria-pressed",
          genState === "ready" && expandable.length > 0 && !fullExpanded ? "true" : "false"
        );
      }
      modeCompactBtn.disabled = customBusy || genState !== "ready" || expandable.length === 0;
    }
    if (overviewBtn) {
      if (typeof overviewBtn.setAttribute === "function") {
        overviewBtn.setAttribute("aria-pressed", fullExpanded ? "true" : "false");
      }
      overviewBtn.disabled = customBusy || genState !== "ready";
    }
    if (parentBtn) {
      const showToolbarParent =
        viewMode === "detail" && Boolean(parentId) && !(currentNode && currentNode.is_terminal);
      parentBtn.hidden = !showToolbarParent;
      parentBtn.disabled = customBusy || !parentId;
    }
  }

  function renderOverviewTree(
    state,
    {
      highlightNodeId = null,
      dimOutsidePath = null,
      animateParentId = null,
      animateRootChildren = false,
      animateExpandedAll = false,
    } = {}
  ) {
    if (!treeNav || !state) return;
    treeNav.replaceChildren();
    renderedTreeButtons = new Map();

    const genState = state.generation_status || "ready";
    if (genStatus) genStatus.hidden = genState !== "generating";
    if (genError) {
      if (genState === "failed") {
        if (genErrorMsg) {
          genErrorMsg.textContent =
            state.generation_error || "Chưa khởi tạo được cây quyết định. Hãy thử tạo lại.";
        }
        genError.hidden = false;
      } else {
        genError.hidden = true;
      }
    }

    const nodeMap = getNodeMap(state);
    const rootNode = nodeMap.get(state.root_node_id) || (state.nodes && state.nodes[0]);
    if (!rootNode) return;

    // While AI is generating the tree in background, show Root + 3 animated skeleton branches!
    if (genState === "generating") {
      currentTopologyKey = "generating";
      const rootParts = parseNodeTitleParts(rootNode, state);
      const rootList = el("ul", "dtree");
      const rootLi = el("li", "dtree__item");
      const wrap = el("div", "dtree__node-wrap");
      const rootCard = el("button", "dtree__node dtree__node--root is-root is-active");
      rootCard.type = "button";
      rootCard.disabled = true;
      rootCard.dataset.nodeId = rootNode.id;
      rootCard.append(buildCardTopRow(rootParts, { key: "root", label: "" }, false));
      rootCard.append(el("span", "dtree__label", rootParts.title));
      wrap.append(rootCard);
      rootLi.append(wrap);

      const skelUl = el("ul", "dtree__children");
      const placeholders = [
        "Đang dựng hướng xử lý 1…",
        "Đang dựng hướng xử lý 2…",
        "Đang dựng hướng xử lý 3…",
      ];
      placeholders.forEach((ariaLabel, idx) => {
        const skelLi = el("li", "dtree__item is-branch-entering");
        if (skelLi.style && typeof skelLi.style.setProperty === "function") {
          skelLi.style.setProperty("--branch-delay", `${idx * 90}ms`);
        }
        const skelCard = el("div", "dtree__skeleton");
        if (typeof skelCard.setAttribute === "function") {
          skelCard.setAttribute("aria-label", ariaLabel);
          skelCard.setAttribute("role", "status");
        }
        const bar1 = el("span", "dtree__skeleton-bar dtree__skeleton-bar--wide");
        const bar2 = el("span", "dtree__skeleton-bar dtree__skeleton-bar--short");
        if (bar1.style && typeof bar1.style.setProperty === "function") {
          bar1.style.setProperty("--skeleton-delay", `${idx * 160}ms`);
          bar2.style.setProperty("--skeleton-delay", `${idx * 160 + 80}ms`);
        }
        skelCard.append(bar1, bar2);
        skelLi.append(skelCard);
        skelUl.append(skelLi);
      });

      rootLi.append(skelUl);
      rootList.append(rootLi);
      treeNav.append(rootList);
      return;
    }

    if (genState === "failed") {
      currentTopologyKey = "failed";
      const rootParts = parseNodeTitleParts(rootNode, state);
      const rootList = el("ul", "dtree");
      const rootLi = el("li", "dtree__item");
      const rootCard = el("button", "dtree__node dtree__node--root is-root");
      rootCard.type = "button";
      rootCard.disabled = true;
      rootCard.append(buildCardTopRow(rootParts, { key: "root", label: "" }, false));
      rootCard.append(el("span", "dtree__label", rootParts.title));
      rootLi.append(rootCard);
      rootList.append(rootLi);
      treeNav.append(rootList);
      return;
    }

    syncRevealedParents(state);
    const { childrenByParent, computePath } = deriveTreeIndex(state, nodeMap);
    const activeId = highlightNodeId || lastOpenedNodeId || null;
    const pathSet = new Set(activeId ? computePath(activeId) : []);
    const visibleIds = [];

    const buildBranch = (node, { animateEnter = false, enterIndex = 0 } = {}) => {
      visibleIds.push(node.id);
      const children = childrenByParent.get(node.id) || [];
      const expanded = children.length > 0 && isParentExpandedOnTree(node.id, state);
      const hasActiveChild = expanded && children.some((entry) => pathSet.has(entry.node.id));
      const inPath = pathSet.has(node.id);
      const isDimmed = dimOutsidePath ? !dimOutsidePath.has(node.id) : false;
      const li = el(
        "li",
        `dtree__item${inPath ? " is-in-path" : ""}${hasActiveChild ? " has-active-child" : ""}${isDimmed ? " is-dimmed" : ""}${animateEnter ? " is-branch-entering" : ""}`
      );
      li.dataset.nodeId = node.id;
      if (animateEnter && li.style && typeof li.style.setProperty === "function") {
        li.style.setProperty("--branch-delay", `${enterIndex * 75}ms`);
      }

      const isRoot = node.id === state.root_node_id;
      const isCustom = node.origin === "custom_user_branch";
      const isSelected = activeId === node.id;
      const seen = isNodeSeen(node.id, state);
      const parts = parseNodeTitleParts(node, state);
      const sev = classifyNodeSeverity(node, state);

      const wrap = el("div", "dtree__node-wrap");
      const card = el(
        "button",
        `dtree__node dtree__node--${sev.key}${isRoot ? " is-root" : ""}${isCustom ? " is-custom" : ""}${isSelected ? " is-active" : ""}`
      );
      card.type = "button";
      card.disabled = navBusy || customBusy;
      card.dataset.nodeId = node.id;
      card.title = parts.title;
      if (typeof card.setAttribute === "function") {
        const ariaParts = [parts.title];
        if (sev.label) ariaParts.push(sev.label);
        if (seen) ariaParts.push("Đã xem");
        card.setAttribute("data-node-id", node.id);
        card.setAttribute("aria-label", ariaParts.join(" — "));
        if (isSelected) card.setAttribute("aria-current", "step");
      }

      card.append(buildCardTopRow(parts, sev, Boolean(node.is_terminal)));
      card.append(el("span", "dtree__label", parts.title));

      if (seen) {
        const seenTag = el("span", "dtree__seen");
        const mark = el("span", "dtree__seen-mark", "✓");
        if (typeof mark.setAttribute === "function") mark.setAttribute("aria-hidden", "true");
        seenTag.append(mark, document.createTextNode("Đã xem"));
        card.append(seenTag);
      }

      card.addEventListener("click", () =>
        openNode(node.id, { sourceEl: card, optionId: null, fromOverview: true })
      );

      renderedTreeButtons.set(node.id, card);
      wrap.append(card);

      if (children.length > 0 && !expanded) {
        const expandPill = el("button", "dtree__expand-pill", `+${children.length} nhánh`);
        expandPill.type = "button";
        expandPill.dataset.expandParent = node.id;
        expandPill.title = `Khám phá ${children.length} nhánh con của ${parts.title}`;
        if (typeof expandPill.setAttribute === "function") {
          expandPill.setAttribute("aria-expanded", "false");
          expandPill.setAttribute("aria-label", `Mở rộng ${children.length} nhánh con của ${parts.title}`);
        }
        expandPill.addEventListener("click", () => expandBranchOnTree(node.id, parts.title));
        wrap.append(expandPill);
      } else if (children.length > 0 && expanded && !isRoot) {
        const foldPill = el("button", "dtree__fold-pill", "−");
        foldPill.type = "button";
        foldPill.dataset.foldParent = node.id;
        foldPill.title = `Thu gọn nhánh con của ${parts.title}`;
        if (typeof foldPill.setAttribute === "function") {
          foldPill.setAttribute("aria-expanded", "true");
          foldPill.setAttribute("aria-label", `Thu gọn nhánh con của ${parts.title}`);
        }
        foldPill.addEventListener("click", () => collapseBranchOnTree(node.id, parts.title));
        wrap.append(foldPill);
      }

      li.append(wrap);

      if (expanded) {
        const shouldAnimateKids =
          (animateParentId && animateParentId === node.id) ||
          (animateRootChildren && isRoot) ||
          (animateExpandedAll && !isRoot);
        const ul = el("ul", "dtree__children");
        children.forEach((entry, idx) => {
          ul.append(
            buildBranch(entry.node, {
              animateEnter: Boolean(shouldAnimateKids),
              enterIndex: idx,
            })
          );
        });
        li.append(ul);
      }

      return li;
    };

    const rootList = el("ul", "dtree");
    rootList.append(buildBranch(rootNode));
    treeNav.append(rootList);
    currentTopologyKey = visibleIds.join(",");
    updateActivePathSpines();
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(updateActivePathSpines);
    }
  }

  function renderBreadcrumbs(state, nodeId) {
    if (!breadcrumbsNav || !state) return;
    breadcrumbsNav.replaceChildren();
    const nodeMap = getNodeMap(state);
    const { computePath } = deriveTreeIndex(state, nodeMap);
    const pathIds = computePath(nodeId);

    pathIds.forEach((id, idx) => {
      const node = nodeMap.get(id);
      if (!node) return;
      const isLast = idx === pathIds.length - 1;
      const label = nodeDisplayName(node);
      if (isLast) {
        const current = el("span", "replay-crumb is-current", label);
        if (typeof current.setAttribute === "function") current.setAttribute("aria-current", "location");
        breadcrumbsNav.append(current);
      } else {
        const btn = el("button", "replay-crumb", label);
        btn.type = "button";
        btn.title = label;
        btn.disabled = customBusy;
        btn.addEventListener("click", () =>
          openNode(id, { sourceEl: null, optionId: null, fromOverview: false })
        );
        breadcrumbsNav.append(btn);
        const sep = el("span", "replay-crumb__sep", "›");
        if (typeof sep.setAttribute === "function") sep.setAttribute("aria-hidden", "true");
        breadcrumbsNav.append(sep);
      }
    });
  }

  /* ------------------------------------------------------------------------
   * Custom User Branch Controls (On-demand Composer, Loading, Retry, Exhausted)
   * ------------------------------------------------------------------------ */
  function updateCustomCharCount() {
    if (!customCount || !customInput) return;
    const len = (customInput.value || "").length;
    customCount.textContent = `${len} / 1.000 ký tự`;
  }

  function clearCustomError() {
    if (!customError) return;
    customError.hidden = true;
    if (customErrorMsg) customErrorMsg.textContent = "";
    if (customRetryBtn) customRetryBtn.hidden = true;
  }

  function showCustomError(message, { showRetry = false } = {}) {
    if (!customError) return;
    if (customErrorMsg) customErrorMsg.textContent = message;
    if (customRetryBtn) customRetryBtn.hidden = !showRetry;
    customError.hidden = false;
    if (typeof customError.focus === "function") customError.focus();
  }

  function closeCustomPanel({ returnFocus = false } = {}) {
    customPanelOpen = false;
    if (customPanel) customPanel.hidden = true;
    if (renderedProposeBtn && typeof renderedProposeBtn.setAttribute === "function") {
      renderedProposeBtn.setAttribute("aria-expanded", "false");
    }
    clearCustomError();
    if (returnFocus && renderedProposeBtn && typeof renderedProposeBtn.focus === "function") {
      renderedProposeBtn.focus();
    }
  }

  function toggleCustomPanel() {
    if (!runState || customBusy) return;
    const limit = runState.custom_branch_limit || 2;
    const remaining = Math.max(0, limit - (runState.custom_branches_used || 0));
    if (remaining <= 0) return;

    customPanelOpen = !customPanelOpen;
    if (customPanel) customPanel.hidden = !customPanelOpen;
    if (renderedProposeBtn && typeof renderedProposeBtn.setAttribute === "function") {
      renderedProposeBtn.setAttribute("aria-expanded", customPanelOpen ? "true" : "false");
    }
    if (customPanelOpen) {
      updateCustomCharCount();
      if (customInput && typeof customInput.focus === "function") customInput.focus();
    } else {
      clearCustomError();
    }
  }

  function renderDirectChildren(state, node) {
    if (!childrenSection || !childrenList) return;
    childrenList.replaceChildren();
    renderedProposeBtn = null;

    if (node.is_terminal) {
      childrenSection.hidden = true;
      if (customPanel) customPanel.hidden = true;
      if (customPending) customPending.hidden = true;
      if (customExhaustedNote) customExhaustedNote.hidden = true;
      return;
    }

    childrenSection.hidden = false;
    const nodeMap = getNodeMap(state);
    const { childrenByParent } = deriveTreeIndex(state, nodeMap);
    const entries = childrenByParent.get(node.id) || [];

    for (const entry of entries) {
      const child = entry.node;
      const seen = isNodeSeen(child.id, state);
      const isCustom = child.origin === "custom_user_branch";
      const parts = parseNodeTitleParts(child, state);
      const sev = classifyNodeSeverity(child, state);
      const btn = el(
        "button",
        `replay-child-card replay-child-card--${sev.key}${isCustom ? " is-custom" : ""}`
      );
      btn.type = "button";
      btn.disabled = customBusy;
      btn.dataset.nodeId = child.id;
      btn.title = parts.title;
      if (typeof btn.setAttribute === "function") {
        const ariaParts = [parts.title];
        if (sev.label) ariaParts.push(sev.label);
        if (seen) ariaParts.push("Đã xem");
        btn.setAttribute("data-node-id", child.id);
        btn.setAttribute("aria-label", ariaParts.join(" — "));
      }

      btn.append(buildCardTopRow(parts, sev, Boolean(child.is_terminal)));
      btn.append(el("span", "dtree__label", parts.title));
      if (seen) {
        const seenTag = el("span", "dtree__seen");
        const mark = el("span", "dtree__seen-mark", "✓");
        if (typeof mark.setAttribute === "function") mark.setAttribute("aria-hidden", "true");
        seenTag.append(mark, document.createTextNode("Đã xem"));
        btn.append(seenTag);
      }

      btn.addEventListener("click", () =>
        openNode(child.id, {
          sourceEl: btn,
          optionId: entry.optionId,
          parentId: node.id,
          fromOverview: false,
        })
      );

      childrenList.append(btn);
    }

    // "+ Đề xuất nhánh" right next to direct children
    const limit = state.custom_branch_limit || 2;
    const used = state.custom_branches_used || 0;
    const remaining = Math.max(0, limit - used);

    const proposeBtn = el("button", "replay-propose-card");
    proposeBtn.type = "button";
    proposeBtn.id = "replay-propose-btn";
    proposeBtn.disabled = customBusy || remaining <= 0;
    if (typeof proposeBtn.setAttribute === "function") {
      proposeBtn.setAttribute("aria-controls", "replay-custom-panel");
      proposeBtn.setAttribute("aria-expanded", customPanelOpen && remaining > 0 ? "true" : "false");
    }

    if (remaining > 0) {
      proposeBtn.append(el("span", "", "+ Đề xuất nhánh"));
      proposeBtn.addEventListener("click", toggleCustomPanel);
    } else {
      proposeBtn.append(el("span", "", "+ Đề xuất nhánh"));
      proposeBtn.append(el("span", "replay-propose-card__sub", `Đã hết lượt (${used}/${limit})`));
    }
    renderedProposeBtn = proposeBtn;
    childrenList.append(proposeBtn);

    if (customParentInput) customParentInput.value = node.id;
    if (customPending) customPending.hidden = !customBusy;

    if (customExhaustedNote) {
      if (remaining <= 0) {
        customExhaustedNote.textContent = `Đã dùng hết ${used}/${limit} lượt đề xuất trong lượt Replay này. Các nhánh đã tạo vẫn mở được từ cây.`;
        customExhaustedNote.hidden = false;
      } else {
        customExhaustedNote.textContent = "";
        customExhaustedNote.hidden = true;
      }
    }

    if (customQuota) {
      customQuota.textContent = `Còn ${remaining}/${limit} lượt thành công`;
    }

    if (remaining <= 0) {
      customPanelOpen = false;
    }
    if (customPanel) {
      customPanel.hidden = !customPanelOpen || remaining <= 0;
    }
    if (customInput) customInput.disabled = customBusy || remaining <= 0;
    if (customSubmit) {
      customSubmit.disabled = customBusy || remaining <= 0;
      customSubmit.textContent = customBusy ? "Đang mô phỏng phương án…" : "Mô phỏng phương án";
    }
    if (customCancelBtn) customCancelBtn.disabled = customBusy;
    updateCustomCharCount();
  }

  /* ------------------------------------------------------------------------
   * Node Detail Content Renderer (2-Level Hierarchy)
   * ------------------------------------------------------------------------ */
  function renderNodeDetailContent(state, nodeId) {
    const nodeMap = getNodeMap(state);
    const { parentOf } = deriveTreeIndex(state, nodeMap);
    const node = nodeMap.get(nodeId);
    if (!node) return;

    const isRoot = node.id === state.root_node_id;
    const isCustom = node.origin === "custom_user_branch";
    const parentId = node.parent_id || parentOf.get(node.id) || null;
    const parts = parseNodeTitleParts(node, state);

    applyDetailCardSemantic(node, state);
    if (detailCard) detailCard.scrollTop = 0;

    if (nodeKicker) {
      if (parts.kicker && !isCustom) {
        nodeKicker.textContent = parts.kicker;
        nodeKicker.hidden = false;
      } else {
        nodeKicker.textContent = "";
        nodeKicker.hidden = true;
      }
    }
    if (nodeAiTag) nodeAiTag.hidden = !isCustom;
    if (nodeTitle) nodeTitle.textContent = parts.title;

    renderBreadcrumbs(state, node.id);
    updateStageControls(state);

    let dims = null;
    if (node.is_terminal) {
      dims = evaluateNodeDimensions(node);
      if (nodeLead) {
        nodeLead.textContent = firstSentence(node.situation || node.consequence_summary);
      }
      if (nodeSecondary) {
        nodeSecondary.textContent = "";
        nodeSecondary.hidden = true;
      }
      if (terminalVerdict) terminalVerdict.hidden = false;
      if (verdictBadges) {
        verdictBadges.replaceChildren();
        verdictBadges.append(el("span", `badge ${dims.safety.cls}`, dims.safety.badgeText));
        verdictBadges.append(el("span", `badge ${dims.operational.cls}`, dims.operational.badgeText));
      }
      if (verdictSafety) verdictSafety.textContent = dims.safety.lineText;
      if (verdictOperational) verdictOperational.textContent = dims.operational.lineText;
    } else if (isRoot) {
      if (nodeLead) nodeLead.textContent = node.situation || "";
      if (nodeSecondary) {
        const fact = (node.state_delta || "").trim();
        nodeSecondary.textContent = fact;
        nodeSecondary.hidden = !fact;
      }
      if (terminalVerdict) terminalVerdict.hidden = true;
    } else {
      const lead = firstSentence(node.situation);
      const consequence = firstSentence(node.consequence_summary);
      if (nodeLead) nodeLead.textContent = lead || consequence || "";
      if (nodeSecondary) {
        const showSecondary = Boolean(consequence && consequence !== lead);
        nodeSecondary.textContent = showSecondary ? consequence : "";
        nodeSecondary.hidden = !showSecondary;
      }
      if (terminalVerdict) terminalVerdict.hidden = true;
    }

    renderSimulationDetails(node, state, dims);
    renderDirectChildren(state, node);

    if (terminalActions) {
      terminalActions.hidden = !node.is_terminal;
    }
    if (terminalParentBtn) {
      terminalParentBtn.hidden = !parentId;
      terminalParentBtn.disabled = customBusy || !parentId;
    }
    if (terminalOverviewBtn) {
      terminalOverviewBtn.disabled = customBusy;
    }
  }

  function buildNodeAnnouncement(node, dims) {
    if (!node) return "";
    const label = nodeDisplayName(node);
    if (node.is_terminal && dims) {
      return `Đã mở kết cục: ${label}. ${dims.safety.badgeText}. ${dims.operational.badgeText}.`;
    }
    return `Đã mở nhánh: ${label}.`;
  }

  /* ------------------------------------------------------------------------
   * Open Node (Overview -> Detail OR Child -> Detail OR Parent -> Detail)
   * Content appears ONLY after BOTH motion completes AND data is ready!
   * ------------------------------------------------------------------------ */
  async function openNode(nodeId, { sourceEl = null, optionId = null, parentId = null, fromOverview = false } = {}) {
    if (!runState || customBusy) return;

    const myToken = ++transitionToken;
    cancelActiveMorph();
    setPageError("");
    pendingRetryRequest = { nodeId, optionId, parentId, fromOverview: false };

    const prevMap = getNodeMap(runState);
    const { parentOf, computePath } = deriveTreeIndex(runState, prevMap);
    const previewNode = prevMap.get(nodeId);
    const previewParts = previewNode ? parseNodeTitleParts(previewNode, runState) : { kicker: "", title: "Đang mở nhánh…" };
    const previewTitle = previewParts.title || "Đang mở nhánh…";
    const previewParentId =
      (previewNode && (previewNode.parent_id || parentOf.get(previewNode.id))) || parentId || null;

    const wasOverview = viewMode === "overview";
    const splitMode = isSplitViewport();

    // Remember overview camera & visible topology before leaving overview
    if (wasOverview) {
      savedCamera = { ...camera };
      savedTopologyKey = currentTopologyKey;
    }

    const animate =
      !splitMode && canAnimateLayout() && sourceEl && typeof sourceEl.getBoundingClientRect === "function";
    const fromRect = animate ? sourceEl.getBoundingClientRect() : null;

    if (fromOverview && animate && treeNav) {
      const pathSet = new Set(computePath(nodeId));
      const items = typeof treeNav.querySelectorAll === "function" ? treeNav.querySelectorAll(".dtree__item") : [];
      for (const item of items) {
        if (item.dataset && !pathSet.has(item.dataset.nodeId)) {
          addClass(item, "is-dimmed");
        }
      }
      addClass(sourceEl, "is-morph-source");
      if (overviewLayer) addClass(overviewLayer, "is-exiting");
    } else if (animate && sourceEl) {
      addClass(sourceEl, "is-morph-source");
    }

    // Prepare detail view shell (same title & border, content hidden until ready)
    customPanelOpen = false;
    clearCustomError();
    focusedNodeId = nodeId;
    lastOpenedNodeId = nodeId;
    setViewAttr("detail");
    updateStageControls(runState);
    renderBreadcrumbs(runState, nodeId);
    applyDetailCardSemantic(previewNode, runState);

    const previewIsCustom = Boolean(previewNode && previewNode.origin === "custom_user_branch");
    if (nodeKicker) {
      if (previewParts.kicker && !previewIsCustom) {
        nodeKicker.textContent = previewParts.kicker;
        nodeKicker.hidden = false;
      } else {
        nodeKicker.textContent = "";
        nodeKicker.hidden = true;
      }
    }
    if (nodeAiTag) nodeAiTag.hidden = !previewIsCustom;
    if (nodeTitle) nodeTitle.textContent = previewTitle;
    if (detailContent) detailContent.hidden = true;
    if (detailError) detailError.hidden = true;
    if (detailLoading) detailLoading.hidden = true;

    let morphPromise = Promise.resolve();
    if (splitMode) {
      if (overviewLayer) overviewLayer.hidden = false;
      if (detailLayer) detailLayer.hidden = false;
      if (detailCard) {
        removeClass(detailCard, "is-morph-hidden");
        detailCard.scrollTop = 0;
      }
      renderOverviewTree(runState, { highlightNodeId: nodeId });
      if (wasOverview && !camera.userAdjusted) {
        scheduleFitTree({ animate: false });
      }
    } else if (animate && fromRect) {
      if (fromOverview && detailLayer && detailLayer.style) {
        // Measure destination rect without unmounting overviewLayer so non-path fade transitions smoothly.
        detailLayer.style.position = "absolute";
        detailLayer.style.inset = "0";
        detailLayer.style.pointerEvents = "none";
        detailLayer.hidden = false;
        if (detailCard) addClass(detailCard, "is-morph-hidden");
        const toRect = detailCard.getBoundingClientRect();
        detailLayer.hidden = true;
        detailLayer.style.position = "";
        detailLayer.style.inset = "";
        detailLayer.style.pointerEvents = "";

        morphPromise = runMorphRect({
          fromRect,
          toRect,
          titleText: previewTitle,
          durationMs: MORPH_ENTER_MS,
          sourceEl,
        }).then(() => {
          if (myToken !== transitionToken) return;
          if (overviewLayer) {
            removeClass(overviewLayer, "is-exiting");
            overviewLayer.hidden = true;
          }
          if (treeNav && typeof treeNav.querySelectorAll === "function") {
            for (const item of treeNav.querySelectorAll(".dtree__item.is-dimmed")) {
              removeClass(item, "is-dimmed");
            }
          }
          if (detailLayer) detailLayer.hidden = false;
          if (detailCard) removeClass(detailCard, "is-morph-hidden");
        });
      } else {
        if (overviewLayer) overviewLayer.hidden = true;
        if (detailLayer) detailLayer.hidden = false;
        if (detailCard) addClass(detailCard, "is-morph-hidden");
        const toRect = detailCard.getBoundingClientRect();

        morphPromise = runMorphRect({
          fromRect,
          toRect,
          titleText: previewTitle,
          durationMs: MORPH_ENTER_MS,
          sourceEl,
        }).then(() => {
          if (myToken !== transitionToken) return;
          if (detailCard) removeClass(detailCard, "is-morph-hidden");
        });
      }
    } else {
      if (overviewLayer) overviewLayer.hidden = true;
      if (detailLayer) detailLayer.hidden = false;
      if (detailCard) removeClass(detailCard, "is-morph-hidden");
    }

    // Fire API sync concurrently with transition
    navBusy = true;
    setStageBusy(true);
    announce(`Đang mở nhánh ${previewTitle}.`);

    let dataReady = false;
    let dataError = null;

    const dataPromise = (async () => {
      if (!api) return runState;
      if (optionId && parentId && typeof api.chooseReplayOption === "function") {
        return api.chooseReplayOption(runId, parentId, optionId);
      }
      if (typeof api.selectReplayNode === "function") {
        return api.selectReplayNode(runId, nodeId);
      }
      return runState;
    })()
      .then((updated) => {
        dataReady = true;
        return updated;
      })
      .catch((err) => {
        dataReady = true;
        dataError = err;
        return null;
      });

    // Wait for morph animation to complete first
    await morphPromise;
    if (myToken !== transitionToken) return;

    // If data is still pending after animation finishes, show "Đang mở nhánh…" inside expanded node
    if (!dataReady) {
      if (detailLoading) detailLoading.hidden = false;
      if (nodeTitle && typeof nodeTitle.focus === "function") {
        nodeTitle.focus({ preventScroll: true });
      }
    }

    const updatedState = await dataPromise;
    if (myToken !== transitionToken) return;

    navBusy = false;
    setStageBusy(false);
    if (detailLoading) detailLoading.hidden = true;

    if (dataError || !updatedState) {
      const msg = (dataError && dataError.message) || "Chưa tải được dữ liệu của nhánh này.";
      if (detailErrorMsg) detailErrorMsg.textContent = msg;
      if (detailErrorParentBtn) {
        detailErrorParentBtn.hidden = !previewParentId;
        detailErrorParentBtn.dataset.parentId = previewParentId || "";
      }
      if (detailError) {
        detailError.hidden = false;
        if (typeof detailError.focus === "function") detailError.focus();
      }
      announce("Chưa mở được nhánh. Có thể thử lại hoặc về toàn cây.");
      return;
    }

    runState = updatedState;
    const resolvedId = updatedState.active_node_id || nodeId;
    const wasRevealedBefore = revealedParents.has(resolvedId);
    focusedNodeId = resolvedId;
    lastOpenedNodeId = resolvedId;
    explicitlyOpenedIds.add(resolvedId);
    collapsedParents.delete(resolvedId);
    revealedParents.add(resolvedId);
    const justRevealed = !wasRevealedBefore && resolvedId !== runState.root_node_id;
    if (justRevealed && !isSplitViewport()) {
      newlyRevealedParentForReturn = resolvedId;
    } else if (isSplitViewport()) {
      newlyRevealedParentForReturn = null;
    }
    pendingRetryRequest = null;

    renderOverviewTree(runState, {
      highlightNodeId: resolvedId,
      animateParentId: isSplitViewport() && justRevealed ? resolvedId : null,
    });
    renderNodeDetailContent(runState, resolvedId);
    if (isSplitViewport() && justRevealed && !camera.userAdjusted) {
      scheduleFitTree({ animate: true });
    }

    if (detailContent) {
      if (!prefersReducedMotion() && typeof requestAnimationFrame === "function") {
        addClass(detailContent, "is-revealing");
        detailContent.hidden = false;
        requestAnimationFrame(() => {
          if (myToken !== transitionToken) return;
          removeClass(detailContent, "is-revealing");
        });
      } else {
        removeClass(detailContent, "is-revealing");
        detailContent.hidden = false;
      }
    }

    if (nodeTitle && typeof nodeTitle.focus === "function") {
      nodeTitle.focus({ preventScroll: true });
    }

    const activeNode = getNodeMap(runState).get(resolvedId);
    const dims = activeNode && activeNode.is_terminal ? evaluateNodeDimensions(activeNode) : null;
    announce(buildNodeAnnouncement(activeNode, dims));
  }

  /* ------------------------------------------------------------------------
   * Return to Overview ("Toàn cây"): Collapse card back to tree spot,
   * restore saved scroll position, and return keyboard focus to the node card.
   * ------------------------------------------------------------------------ */
  async function returnToOverview() {
    if (!runState || customBusy) return;

    if (viewMode === "overview") {
      if (camera.userAdjusted) fitTreeToViewport({ animate: true });
      const targetBtn =
        renderedTreeButtons.get(lastOpenedNodeId) || renderedTreeButtons.get(runState.root_node_id);
      if (targetBtn && typeof targetBtn.focus === "function") {
        targetBtn.focus({ preventScroll: true });
      }
      return;
    }

    const myToken = ++transitionToken;
    cancelActiveMorph();
    navBusy = false;
    setStageBusy(false);
    customPanelOpen = false;
    clearCustomError();
    pendingRetryRequest = null;

    const closingNodeId = focusedNodeId || lastOpenedNodeId || runState.root_node_id;
    const closingNode = getNodeMap(runState).get(closingNodeId);
    const closingTitle = closingNode ? nodeDisplayName(closingNode, runState) : "";
    const splitMode = isSplitViewport();

    const animate = !splitMode && canAnimateLayout() && detailCard && !detailLayer.hidden;
    const fromRect = animate ? detailCard.getBoundingClientRect() : null;

    setViewAttr("overview");
    focusedNodeId = null;
    lastOpenedNodeId = closingNodeId;

    const animateParentId = newlyRevealedParentForReturn;
    newlyRevealedParentForReturn = null;
    renderOverviewTree(runState, { highlightNodeId: closingNodeId, animateParentId });
    updateStageControls(runState);

    if (detailLayer) detailLayer.hidden = true;
    if (overviewLayer) overviewLayer.hidden = false;

    // Preserve user camera if they manually panned/zoomed and tree did not grow;
    // otherwise auto-fit cleanly BEFORE measuring target node card for FLIP return.
    if (savedCamera && savedCamera.userAdjusted && currentTopologyKey === savedTopologyKey) {
      camera = { ...savedCamera };
      applyCamera({ smooth: false });
    } else {
      fitTreeToViewport({ animate: splitMode });
    }

    const targetBtn = renderedTreeButtons.get(closingNodeId) || renderedTreeButtons.get(runState.root_node_id);

    if (animate && fromRect && targetBtn && typeof targetBtn.getBoundingClientRect === "function") {
      const toRect = targetBtn.getBoundingClientRect();
      addClass(targetBtn, "is-morph-source");
      if (overviewLayer) {
        addClass(overviewLayer, "is-entering");
        requestAnimationFrame(() => {
          if (myToken !== transitionToken) return;
          removeClass(overviewLayer, "is-entering");
        });
      }

      await runMorphRect({
        fromRect,
        toRect,
        titleText: closingTitle,
        durationMs: MORPH_EXIT_MS,
        sourceEl: targetBtn,
      });
      if (myToken !== transitionToken) return;
    }

    if (targetBtn && typeof targetBtn.focus === "function") {
      targetBtn.focus({ preventScroll: true });
    }
    announce("Đã trở về toàn cảnh cây quyết định.");
  }

  /* ------------------------------------------------------------------------
   * Navigate Up ("Về nhánh trước")
   * ------------------------------------------------------------------------ */
  function goToParentNode() {
    if (!runState || customBusy || viewMode !== "detail") return;
    const nodeMap = getNodeMap(runState);
    const { parentOf } = deriveTreeIndex(runState, nodeMap);
    const current = nodeMap.get(focusedNodeId);
    const parentId = (current && (current.parent_id || parentOf.get(current.id))) || null;
    if (parentId) {
      return openNode(parentId, { sourceEl: null, optionId: null, fromOverview: false });
    }
  }

  /* ------------------------------------------------------------------------
   * Submit Custom User Branch
   * ------------------------------------------------------------------------ */
  async function submitCustomProposal() {
    if (!runState || customBusy || !customInput) return;
    const parentId = focusedNodeId || runState.active_node_id;
    const proposal = customInput.value.trim();

    if (!proposal) {
      showCustomError("Hãy nhập phương án bạn muốn thử trước khi mô phỏng. Chưa trừ lượt.", { showRetry: false });
      if (typeof customInput.focus === "function") customInput.focus();
      return;
    }
    if (proposal.length > MAX_PROPOSAL_CHARS) {
      showCustomError("Nội dung đề xuất vượt quá 1.000 ký tự. Hãy rút gọn rồi gửi lại; chưa trừ lượt.", { showRetry: false });
      if (typeof customInput.focus === "function") customInput.focus();
      return;
    }

    customBusy = true;
    clearCustomError();
    setStageBusy(true);
    updateStageControls(runState);
    const parentNode = getNodeMap(runState).get(parentId);
    if (parentNode) renderDirectChildren(runState, parentNode);
    announce("Đang mô phỏng phương án bạn tự đề xuất.");

    const sourceElForZoom = renderedProposeBtn || customPanel;

    try {
      const updated = await api.addCustomReplayBranch(runId, parentId, proposal);
      runState = updated;
      customBusy = false;
      setStageBusy(false);
      customInput.value = "";
      updateCustomCharCount();
      customPanelOpen = false;
      clearCustomError();

      const newNodeId = updated.active_node_id;
      const splitMode = isSplitViewport();
      explicitlyOpenedIds.add(newNodeId);
      collapsedParents.delete(parentId);
      revealedParents.add(parentId);
      newlyRevealedParentForReturn = splitMode ? null : parentId;
      const fromRect =
        !splitMode && canAnimateLayout() && sourceElForZoom && typeof sourceElForZoom.getBoundingClientRect === "function"
          ? sourceElForZoom.getBoundingClientRect()
          : null;

      focusedNodeId = newNodeId;
      lastOpenedNodeId = newNodeId;
      renderOverviewTree(runState, {
        highlightNodeId: newNodeId,
        animateParentId: splitMode ? parentId : null,
      });
      if (splitMode && !camera.userAdjusted) {
        scheduleFitTree({ animate: true });
      }

      const newNode = getNodeMap(runState).get(newNodeId);
      const newTitle = newNode ? nodeDisplayName(newNode, runState) : "";

      if (fromRect && detailCard) {
        const myToken = ++transitionToken;
        if (detailContent) detailContent.hidden = true;
        if (nodeTitle) nodeTitle.textContent = newTitle;
        if (nodeAiTag) nodeAiTag.hidden = false;
        addClass(detailCard, "is-morph-hidden");
        const toRect = detailCard.getBoundingClientRect();

        await runMorphRect({
          fromRect,
          toRect,
          titleText: newTitle,
          durationMs: MORPH_ENTER_MS,
          sourceEl: null,
        });
        if (myToken !== transitionToken) return;
        removeClass(detailCard, "is-morph-hidden");
      }

      renderNodeDetailContent(runState, newNodeId);
      if (detailContent) {
        if (!prefersReducedMotion() && typeof requestAnimationFrame === "function") {
          addClass(detailContent, "is-revealing");
          detailContent.hidden = false;
          requestAnimationFrame(() => removeClass(detailContent, "is-revealing"));
        } else {
          detailContent.hidden = false;
        }
      }
      if (nodeTitle && typeof nodeTitle.focus === "function") {
        nodeTitle.focus({ preventScroll: true });
      }
      const dims = newNode && newNode.is_terminal ? evaluateNodeDimensions(newNode) : null;
      announce(`Đã tạo nhánh mới. ${buildNodeAnnouncement(newNode, dims)}`);
    } catch (err) {
      customBusy = false;
      setStageBusy(false);
      customPanelOpen = true;
      updateStageControls(runState);
      if (parentNode) renderDirectChildren(runState, parentNode);
      const baseMsg = (err && err.message) || "Chưa mô phỏng được phương án này.";
      showCustomError(
        `${baseMsg} Nội dung bạn nhập vẫn được giữ nguyên và chưa trừ lượt đề xuất.`,
        { showRetry: true }
      );
      announce("Chưa mô phỏng được phương án; chưa trừ lượt đề xuất.");
    }
  }

  /* ------------------------------------------------------------------------
   * Event Bindings
   * ------------------------------------------------------------------------ */
  if (fullPromptToggle && fullPromptPanel) {
    if (promptDrawer && promptDrawer.tagName === "DETAILS") {
      const syncPromptExpanded = () => {
        if (typeof fullPromptToggle.setAttribute === "function") {
          fullPromptToggle.setAttribute("aria-expanded", promptDrawer.open ? "true" : "false");
        }
      };
      syncPromptExpanded();
      promptDrawer.addEventListener("toggle", syncPromptExpanded);
    } else {
      fullPromptToggle.addEventListener("click", () => {
        const nextExpanded = fullPromptPanel.hidden;
        fullPromptPanel.hidden = !nextExpanded;
        if (typeof fullPromptToggle.setAttribute === "function") {
          fullPromptToggle.setAttribute("aria-expanded", nextExpanded ? "true" : "false");
        }
      });
    }
  }

  if (modeCompactBtn) modeCompactBtn.addEventListener("click", setCompactTreeMode);
  if (overviewBtn) overviewBtn.addEventListener("click", setFullTreeMode);
  if (detailCloseBtn) detailCloseBtn.addEventListener("click", returnToOverview);
  if (terminalOverviewBtn) terminalOverviewBtn.addEventListener("click", returnToOverview);
  if (detailErrorOverviewBtn) detailErrorOverviewBtn.addEventListener("click", returnToOverview);

  if (parentBtn) parentBtn.addEventListener("click", goToParentNode);
  if (terminalParentBtn) terminalParentBtn.addEventListener("click", goToParentNode);
  if (detailErrorParentBtn) {
    detailErrorParentBtn.addEventListener("click", () => {
      const targetParent = detailErrorParentBtn.dataset && detailErrorParentBtn.dataset.parentId;
      if (targetParent) {
        return openNode(targetParent, { sourceEl: null, optionId: null, fromOverview: false });
      }
      return goToParentNode();
    });
  }

  if (detailRetryBtn) {
    detailRetryBtn.addEventListener("click", () => {
      if (pendingRetryRequest) {
        return openNode(pendingRetryRequest.nodeId, pendingRetryRequest);
      }
    });
  }

  if (customInput) {
    customInput.addEventListener("input", updateCustomCharCount);
  }
  if (customCancelBtn) {
    customCancelBtn.addEventListener("click", () => closeCustomPanel({ returnFocus: true }));
  }
  if (customRetryBtn) {
    customRetryBtn.addEventListener("click", () => submitCustomProposal());
  }
  if (customForm) {
    customForm.addEventListener("submit", (event) => {
      event.preventDefault();
      return submitCustomProposal();
    });
  }

  if (genRetryBtn) {
    genRetryBtn.addEventListener("click", () => retryTreeGeneration());
  }

  if (zoomInBtn) {
    zoomInBtn.addEventListener("click", () => zoomBy(ZOOM_STEP));
  }
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener("click", () => zoomBy(-ZOOM_STEP));
  }
  if (zoomFitBtn) {
    zoomFitBtn.addEventListener("click", () => fitTreeToViewport({ animate: true }));
  }

  if (treeViewport && typeof treeViewport.addEventListener === "function") {
    let panState = null;

    treeViewport.addEventListener("pointerdown", (event) => {
      if (!event || !isTreeCanvasVisible()) return;
      if (event.button !== undefined && event.button !== 0) return;
      if (
        event.target &&
        typeof event.target.closest === "function" &&
        event.target.closest("button, a, input, textarea, .replay-zoom-controls")
      ) {
        return;
      }
      panState = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        originTx: camera.tx,
        originTy: camera.ty,
        moved: false,
        isTouch: event.pointerType === "touch",
      };
    });

    treeViewport.addEventListener("pointermove", (event) => {
      if (!panState || !event || event.pointerId !== panState.pointerId) return;
      const dx = event.clientX - panState.startX;
      const dy = event.clientY - panState.startY;
      if (!panState.moved) {
        if (Math.hypot(dx, dy) < 5) return;
        panState.moved = true;
        addClass(treeViewport, "is-panning");
        if (typeof treeViewport.setPointerCapture === "function") {
          try { treeViewport.setPointerCapture(event.pointerId); } catch (_ignored) { /* ignore */ }
        }
      }
      camera.tx = panState.originTx + dx;
      if (!panState.isTouch) {
        camera.ty = panState.originTy + dy;
      }
      camera.userAdjusted = true;
      applyCamera({ smooth: false });
    });

    const endPan = (event) => {
      if (!panState) return;
      if (event && panState.pointerId !== event.pointerId) return;
      removeClass(treeViewport, "is-panning");
      if (
        panState.moved &&
        typeof treeViewport.releasePointerCapture === "function" &&
        event
      ) {
        try { treeViewport.releasePointerCapture(event.pointerId); } catch (_ignored) { /* ignore */ }
      }
      panState = null;
    };

    treeViewport.addEventListener("pointerup", endPan);
    treeViewport.addEventListener("pointercancel", endPan);

    treeViewport.addEventListener(
      "wheel",
      (event) => {
        if (!event || !isTreeCanvasVisible()) return;
        if (!event.ctrlKey && !event.metaKey) return;
        event.preventDefault();
        const delta = event.deltaY < 0 ? ZOOM_STEP * 0.7 : -ZOOM_STEP * 0.7;
        zoomBy(delta, event.clientX, event.clientY);
      },
      { passive: false }
    );

    treeViewport.addEventListener("keydown", (event) => {
      if (!event || !isTreeCanvasVisible()) return;
      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        zoomBy(ZOOM_STEP);
      } else if (event.key === "-") {
        event.preventDefault();
        zoomBy(-ZOOM_STEP);
      } else if (event.key === "0") {
        event.preventDefault();
        fitTreeToViewport({ animate: true });
      }
    });
  }

  if (typeof ResizeObserver === "function" && treeViewport) {
    const ro = new ResizeObserver(() => {
      updateActivePathSpines();
      if (isTreeCanvasVisible() && !camera.userAdjusted) {
        fitTreeToViewport({ animate: false });
      }
    });
    ro.observe(treeViewport);
  }

  if (typeof window.matchMedia === "function") {
    try {
      const splitQuery = window.matchMedia("(min-width: 60rem)");
      if (splitQuery && typeof splitQuery.addEventListener === "function") {
        splitQuery.addEventListener("change", () => {
          if (!runState) return;
          if (viewMode === "detail" && overviewLayer) {
            overviewLayer.hidden = !isSplitViewport();
          }
          updateStageControls(runState);
          updateActivePathSpines();
          if (isTreeCanvasVisible() && !camera.userAdjusted) {
            scheduleFitTree({ animate: false });
          }
        });
      }
    } catch (_ignored) {
      /* ignore */
    }
  }

  if (typeof window.addEventListener === "function") {
    window.addEventListener("pagehide", stopGenerationPoll);
  }

  if (openAnswerBtn && answerDialog) {
    openAnswerBtn.addEventListener("click", openAnswerDialog);
  }
  if (closeAnswerBtn) {
    closeAnswerBtn.addEventListener("click", closeAnswerDialog);
  }
  if (answerDialog) {
    answerDialog.addEventListener("click", (event) => {
      if (event && event.target === answerDialog) closeAnswerDialog();
    });
  }
  if (typeof document.addEventListener === "function") {
    document.addEventListener("keydown", handleGlobalKeydown);
  }

  /* ------------------------------------------------------------------------
   * Bootstrap (ALWAYS enters in Overview mode: shows skeleton branches if
   * generating, progressive Depth-1 branches on brand-new runs, and auto-fits
   * the tree cleanly into the canvas)
   * ------------------------------------------------------------------------ */
  function initializeState(state) {
    runState = state;
    revealedParents.clear();
    collapsedParents.clear();
    setViewAttr("overview");
    focusedNodeId = null;
    lastOpenedNodeId =
      state.active_node_id && state.active_node_id !== state.root_node_id ? state.active_node_id : null;

    if (detailLayer) detailLayer.hidden = true;
    if (overviewLayer) overviewLayer.hidden = false;

    const genState = state.generation_status || "ready";
    const isBrandNewReady =
      genState === "ready" &&
      (!state.visited_node_ids || state.visited_node_ids.length <= 1);

    syncRevealedParents(runState);
    renderOverviewTree(runState, {
      highlightNodeId: lastOpenedNodeId,
      animateRootChildren: isBrandNewReady,
    });
    updateStageControls(runState);
    scheduleFitTree({ animate: false });

    if (genState === "generating") {
      scheduleGenerationPoll();
    }
    if (answerHost && runState.linked_answer_text) {
      renderFormattedAnswer(runState);
    }
  }

  async function bootstrap() {
    if (initialScript && initialScript.textContent && initialScript.textContent.trim()) {
      try {
        initializeState(JSON.parse(initialScript.textContent));
        return;
      } catch (_ignored) {
        /* Fall back to API fetch */
      }
    }
    if (!api || typeof api.getReplayRun !== "function") return;
    setStageBusy(true);
    try {
      const fetched = await api.getReplayRun(runId);
      setStageBusy(false);
      initializeState(fetched);
    } catch (err) {
      setStageBusy(false);
      setPageError((err && err.message) || "Chưa tải được dữ liệu Decision Replay.");
    }
  }

  bootstrap();
})();
