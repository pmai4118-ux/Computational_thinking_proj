(() => {
  "use strict";

  const root = document.querySelector("[data-replay-studio]");
  if (!root) return;
  const api = window.InterviewApi;
  const runId = root.dataset.runId;
  const initialScript = document.querySelector("#replay-initial-data");
  const liveAnnouncer = document.querySelector("#replay-live-announcer");
  const errorBox = document.querySelector("#replay-error");
  const statusBox = document.querySelector("#replay-status");
  const answerHost = document.querySelector("#replay-answer-source");
  const alignmentBanner = document.querySelector("#replay-alignment-banner");
  const assumptionsList = document.querySelector("#replay-assumptions-list");
  const treeStage = document.querySelector("#replay-tree-stage");
  const treeNav = document.querySelector("#replay-tree-nav");
  const breadcrumbNav = document.querySelector("#replay-breadcrumbs");
  const rewindParentTopBtn = document.querySelector("#replay-rewind-parent-top");
  const jumpRootBtn = document.querySelector("#replay-jump-root");
  const focusCard = document.querySelector("#replay-focus-card");
  const nodeTitle = document.querySelector("#replay-node-title");
  const nodeBadge = document.querySelector("#replay-node-badge");
  const nodeSituation = document.querySelector("#replay-node-situation");
  const nodeStateDelta = document.querySelector("#replay-node-state-delta");
  const traceList = document.querySelector("#replay-trace-list");
  const nodeImpact = document.querySelector("#replay-node-impact");
  const nodeTradeoff = document.querySelector("#replay-node-tradeoff");
  const optionsSection = document.querySelector("#replay-options-section");
  const optionsList = document.querySelector("#replay-options-list");
  const customSection = document.querySelector("#replay-custom-section");
  const customQuota = document.querySelector("#replay-custom-quota");
  const customForm = document.querySelector("#replay-custom-form");
  const customInput = document.querySelector("#replay-custom-input");
  const customCount = document.querySelector("#replay-custom-count");
  const customSubmit = document.querySelector("#replay-custom-submit");
  const endingSection = document.querySelector("#replay-ending-section");
  const outcomeSummary = document.querySelector("#replay-outcome-summary");
  const safetyList = document.querySelector("#replay-safety-list");
  const operationalList = document.querySelector("#replay-operational-list");
  const comparisonNote = document.querySelector("#replay-comparison-note");
  const rewindParentBtn = document.querySelector("#replay-rewind-parent");
  const rewindRootBottomBtn = document.querySelector("#replay-rewind-root-bottom");

  let runState = null;
  let busy = false;
  let renderedTreeButtons = new Map();

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function announce(message) {
    if (!liveAnnouncer || !message) return;
    liveAnnouncer.textContent = liveAnnouncer.textContent === message ? `${message}\u00A0` : message;
  }

  function setBusyState(isBusy) {
    busy = isBusy;
    const val = isBusy ? "true" : "false";
    if (treeStage && typeof treeStage.setAttribute === "function") {
      treeStage.setAttribute("aria-busy", val);
    }
    if (focusCard && typeof focusCard.setAttribute === "function") {
      focusCard.setAttribute("aria-busy", val);
    }
  }

  function setError(message) {
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

  function setStatus(message) {
    if (!statusBox) return;
    if (!message) {
      statusBox.hidden = true;
      statusBox.textContent = "";
      return;
    }
    statusBox.textContent = message;
    statusBox.hidden = false;
  }

  function updateCustomCharCount() {
    if (!customCount || !customInput) return;
    const len = (customInput.value || "").length;
    customCount.textContent = `${len} / 1.000 ký tự`;
  }

  function getNodeMap(state) {
    const map = new Map();
    for (const n of state.nodes || []) map.set(n.id, n);
    return map;
  }

  function deriveParentMap(state, nodeMap) {
    const parentOf = new Map();
    for (const n of state.nodes || []) {
      if (n.parent_id) parentOf.set(n.id, n.parent_id);
      for (const opt of n.options || []) {
        if (opt.target_node_id && !parentOf.has(opt.target_node_id)) {
          parentOf.set(opt.target_node_id, n.id);
        }
      }
    }
    parentOf.delete(state.root_node_id);
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
    return { parentOf, computePath };
  }

  function evaluateNodeDimensions(node) {
    const invs = node.invariants || [];
    const safetyItems = invs.filter((item) => item.category !== "operational");
    const operationalItems = invs.filter((item) => item.category === "operational");

    const safetyPass = safetyItems.filter((i) => i.status === "preserved").length;
    const safetyBroken = safetyItems.some((i) => i.status === "broken");
    const safetyUncertain = safetyItems.some((i) => i.status === "uncertain");

    let safety;
    if (safetyBroken) {
      safety = {
        cls: "badge--unmet",
        nodeText: "Tính đúng đắn: Vỡ bất biến",
        summaryText: `Tính đúng đắn (Safety): ${safetyPass}/${safetyItems.length} Đạt · Vỡ bất biến`,
      };
    } else if (!safetyItems.length || safetyUncertain) {
      safety = {
        cls: "badge--unresolved",
        nodeText: "Tính đúng đắn: Chưa rõ",
        summaryText: `Tính đúng đắn (Safety): ${safetyPass}/${safetyItems.length} Đạt · Chưa rõ`,
      };
    } else {
      safety = {
        cls: "badge--met",
        nodeText: "Tính đúng đắn: Đạt",
        summaryText: `Tính đúng đắn (Safety): ${safetyPass}/${safetyItems.length} Đạt`,
      };
    }

    let operational;
    if (!operationalItems.length) {
      operational = {
        evaluated: false,
        cls: "badge--neutral",
        nodeText: "Vận hành: Chưa đánh giá",
        summaryText: "Hiệu năng & Vận hành: Chưa đánh giá",
      };
    } else if (operationalItems.some((i) => i.status === "broken")) {
      operational = {
        evaluated: true,
        cls: "badge--unmet",
        nodeText: "Vận hành: Nguy cơ nghẽn / Vỡ",
        summaryText: "Hiệu năng & Vận hành: Nguy cơ nghẽn / Vỡ",
      };
    } else if (operationalItems.some((i) => i.status === "warning")) {
      operational = {
        evaluated: true,
        cls: "badge--unresolved",
        nodeText: "Vận hành: Có rủi ro chờ khóa",
        summaryText: "Hiệu năng & Vận hành: Có rủi ro chờ khóa",
      };
    } else if (operationalItems.some((i) => i.status === "uncertain")) {
      operational = {
        evaluated: true,
        cls: "badge--unresolved",
        nodeText: "Vận hành: Chưa rõ",
        summaryText: "Hiệu năng & Vận hành: Chưa rõ",
      };
    } else {
      operational = {
        evaluated: true,
        cls: "badge--met",
        nodeText: "Vận hành: Ổn định",
        summaryText: "Hiệu năng & Vận hành: Ổn định",
      };
    }

    return { safetyItems, operationalItems, safety, operational };
  }

  function renderHighlightedAnswer(answerText, activeNode) {
    if (!answerHost) return;
    answerHost.replaceChildren();
    if (!answerText) {
      answerHost.append(
        el("p", "text-secondary", "Đây là lượt xem thử kịch bản mẫu độc lập (chưa gắn với bài trả lời trong phiên).")
      );
      return;
    }
    const start = activeNode && Number.isInteger(activeNode.answer_quote_start) ? activeNode.answer_quote_start : null;
    const end = activeNode && Number.isInteger(activeNode.answer_quote_end) ? activeNode.answer_quote_end : null;
    if (start !== null && end !== null && end > start && end <= answerText.length) {
      const pre = el("pre", "answer-source replay-answer-pre");
      if (start > 0) pre.append(document.createTextNode(answerText.slice(0, start)));
      const mark = el("mark", "evidence-mark evidence-mark--active", answerText.slice(start, end));
      pre.append(mark);
      if (end < answerText.length) pre.append(document.createTextNode(answerText.slice(end)));
      answerHost.append(pre);
    } else {
      answerHost.append(el("pre", "answer-source replay-answer-pre", answerText));
    }
  }

  function renderAlignmentBanner(activeNode, hasLinkedAnswer) {
    if (!alignmentBanner) return;
    alignmentBanner.replaceChildren();
    if (!hasLinkedAnswer) {
      alignmentBanner.hidden = true;
      return;
    }
    alignmentBanner.hidden = false;
    if (activeNode.answer_alignment === "matched_from_answer" && activeNode.answer_quote) {
      alignmentBanner.className = "alert alert--status";
      alignmentBanner.append(el("p", "alert__title", "Đối chiếu trực tiếp từ bài làm gốc (đoạn tô sáng bên dưới)"));
      alignmentBanner.append(el("p", "alert__hint", `Trích đoạn khớp nguyên văn: "${activeNode.answer_quote}"`));
    } else if (activeNode.answer_alignment === "unspecified") {
      alignmentBanner.className = "alert alert--status";
      alignmentBanner.append(el("p", "alert__title", "Bài làm gốc chưa xác định rõ bước này — không suy đoán"));
      alignmentBanner.append(
        el("p", "alert__hint", "Hệ thống không gán hệ quả chắc chắn cho bài làm của bạn. Hãy chọn một node trên cây để mô phỏng thử.")
      );
    } else if (activeNode.origin === "custom_user_branch") {
      alignmentBanner.className = "alert alert--status";
      alignmentBanner.append(el("p", "alert__title", "Đang focus nhánh thử nghiệm do bạn tự đề xuất"));
      alignmentBanner.append(
        el("p", "alert__hint", "Kết quả kỳ vọng (mô phỏng) này hoàn toàn tách biệt — bài làm và điểm gốc không thay đổi.")
      );
    } else {
      alignmentBanner.className = "alert alert--status";
      alignmentBanner.append(el("p", "alert__title", "Đang focus nhánh What-If trên cây quyết định"));
      alignmentBanner.append(
        el("p", "alert__hint", "Bấm trực tiếp node cha hoặc node anh em trên cây phía trên để tua lại và so sánh kết cục.")
      );
    }
  }

  function renderVisualTree(state, nodeMap, parentOf, activePathSet) {
    if (!treeNav) return;
    treeNav.replaceChildren();
    renderedTreeButtons = new Map();

    const visited = new Set(state.visited_node_ids || []);
    visited.add(state.root_node_id);
    visited.add(state.active_node_id);

    const childrenByParent = new Map();
    for (const node of state.nodes || []) {
      if (node.id === state.root_node_id) continue;
      const pId = parentOf.get(node.id) || state.root_node_id;
      if (!childrenByParent.has(pId)) childrenByParent.set(pId, []);
      childrenByParent.get(pId).push(node);
    }

    const buildBranch = (node) => {
      const branch = el("li", `dtree__item${activePathSet.has(node.id) ? " is-in-path" : ""}`);
      const isActive = node.id === state.active_node_id;
      const isVisited = visited.has(node.id);

      const card = el(
        "button",
        `dtree__node${isActive ? " is-active" : ""}${isVisited ? " is-visited" : " is-unvisited"}${node.is_terminal ? " is-terminal" : ""}`
      );
      card.type = "button";
      card.disabled = busy;
      card.dataset.nodeId = node.id;
      if (typeof card.setAttribute === "function") {
        card.setAttribute("data-node-id", node.id);
        if (isActive) card.setAttribute("aria-current", "step");
      }

      const topRow = el("span", "dtree__top");
      const originText = node.origin === "answer_start"
        ? "Gốc"
        : node.origin === "custom_user_branch"
          ? "Tự đề xuất"
          : node.is_terminal
            ? "Kết cục"
            : `Nhánh ${node.depth}`;
      topRow.append(el("span", "dtree__origin", originText));

      if (isActive) {
        topRow.append(el("span", "badge badge--met dtree__badge", "Đang focus"));
      } else if (node.id === state.root_node_id) {
        topRow.append(el("span", "badge badge--met dtree__badge", "Điểm xuất phát"));
      } else if (!node.is_terminal) {
        topRow.append(
          el("span", "badge dtree__badge", isVisited ? `Đã qua · Tầng ${node.depth}` : `Điểm rẽ · Tầng ${node.depth}`)
        );
      } else if (!isVisited) {
        topRow.append(el("span", "badge dtree__badge", "Chưa mở · Bấm để xem"));
      } else {
        topRow.append(el("span", "badge dtree__badge", "Đã xem"));
      }
      card.append(topRow);
      card.append(el("span", "dtree__label", node.branch_label || node.title));

      if (node.is_terminal && (isVisited || isActive)) {
        const dims = evaluateNodeDimensions(node);
        const statuses = el("span", "dtree__statuses");
        statuses.append(el("span", `badge ${dims.safety.cls} dtree__status-pill`, dims.safety.nodeText));
        statuses.append(el("span", `badge ${dims.operational.cls} dtree__status-pill`, dims.operational.nodeText));
        card.append(statuses);
      }

      card.addEventListener("click", () => navigateToNode(node.id, { scrollToFocus: true, focusMode: "tree" }));
      renderedTreeButtons.set(node.id, card);
      branch.append(card);

      const children = childrenByParent.get(node.id) || [];
      if (children.length) {
        const sub = el("ul", "dtree__children");
        for (const child of children) {
          sub.append(buildBranch(child));
        }
        branch.append(sub);
      }
      return branch;
    };

    const rootNode = nodeMap.get(state.root_node_id);
    if (rootNode) {
      const treeList = el("ul", "dtree");
      treeList.append(buildBranch(rootNode));
      treeNav.append(treeList);
    }
  }

  function renderBreadcrumbs(state, nodeMap, pathIds) {
    if (!breadcrumbNav) return;
    breadcrumbNav.replaceChildren();
    pathIds.forEach((id, idx) => {
      const node = nodeMap.get(id);
      if (!node) return;
      const isLast = idx === pathIds.length - 1;
      const btn = el("button", `replay-crumb${isLast ? " is-current" : ""}`, node.branch_label || node.title);
      btn.type = "button";
      btn.disabled = busy || isLast;
      btn.addEventListener("click", () => navigateToNode(id, { scrollToFocus: false, focusMode: "heading" }));
      breadcrumbNav.append(btn);
      if (!isLast) breadcrumbNav.append(el("span", "replay-crumb__sep", "›"));
    });
  }

  function renderInvariantCard(inv) {
    const statusMeta = {
      preserved: { cls: "badge--met", label: "ĐẠT · Bảo toàn" },
      warning: { cls: "badge--unresolved", label: "CẢNH BÁO · Rủi ro vận hành" },
      broken: { cls: "badge--unmet", label: "VỠ · Vi phạm" },
      uncertain: { cls: "badge--unresolved", label: "CHƯA RÕ · Cần kiểm chứng" },
    };
    const meta = statusMeta[inv.status] || statusMeta.uncertain;
    const li = el("li", `invariant-card invariant-card--${inv.status}`);
    const top = el("div", "profile-entry__meta");
    top.append(el("strong", "", inv.name));
    top.append(el("span", `badge ${meta.cls}`, meta.label));
    li.append(top);
    li.append(el("p", "text-secondary", inv.detail));
    return li;
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

  function buildNodeAnnouncement(active) {
    if (!active) return "";
    if (active.is_terminal) {
      const dims = evaluateNodeDimensions(active);
      return `Đang xem kết cục mô phỏng: ${active.title}. ${dims.safety.nodeText}. ${dims.operational.nodeText}.`;
    }
    return `Đang xem điểm rẽ: ${active.title}.`;
  }

  function restoreFocus(focusMode, nodeId) {
    if (!focusMode) return;
    if (focusMode === "tree") {
      const targetBtn = renderedTreeButtons.get(nodeId);
      if (targetBtn && !targetBtn.disabled && typeof targetBtn.focus === "function") {
        targetBtn.focus({ preventScroll: true });
        return;
      }
    }
    if (nodeTitle && typeof nodeTitle.focus === "function") {
      nodeTitle.focus({ preventScroll: true });
    }
  }

  function renderActiveNode(state) {
    const nodeMap = getNodeMap(state);
    const { parentOf, computePath } = deriveParentMap(state, nodeMap);
    const active = nodeMap.get(state.active_node_id) || state.nodes[0];
    if (!active) return;

    const pathIds =
      state.active_path_ids && state.active_path_ids.length > 1
        ? state.active_path_ids
        : computePath(active.id);
    const activeParentId = active.parent_id || parentOf.get(active.id) || null;
    const activePathSet = new Set(pathIds);

    renderHighlightedAnswer(state.linked_answer_text, active);
    renderAlignmentBanner(active, Boolean(state.linked_answer_text));
    renderVisualTree(state, nodeMap, parentOf, activePathSet);
    renderBreadcrumbs(state, nodeMap, pathIds);

    if (rewindParentTopBtn) {
      rewindParentTopBtn.disabled = busy || !activeParentId;
      rewindParentTopBtn.hidden = !activeParentId;
    }
    if (jumpRootBtn) {
      jumpRootBtn.disabled = busy || active.id === state.root_node_id;
      jumpRootBtn.hidden = active.id === state.root_node_id;
    }

    if (assumptionsList) {
      assumptionsList.replaceChildren();
      for (const item of active.assumptions_used || []) {
        assumptionsList.append(el("li", "", item));
      }
    }

    if (nodeTitle) nodeTitle.textContent = active.title;
    if (nodeBadge) {
      if (active.origin === "answer_start") {
        nodeBadge.textContent = active.answer_alignment === "unspecified" ? "Điểm xuất phát · Chưa xác định rõ" : "Điểm xuất phát từ bài làm";
        nodeBadge.className = `badge ${active.answer_alignment === "unspecified" ? "badge--unresolved" : "badge--met"}`;
      } else if (active.origin === "custom_user_branch") {
        nodeBadge.textContent = "Nhánh bạn tự đề xuất · Kết quả kỳ vọng (mô phỏng)";
        nodeBadge.className = "badge badge--met";
      } else if (active.is_terminal) {
        nodeBadge.textContent = "Đang focus · Kết cục mô phỏng";
        nodeBadge.className = "badge badge--unresolved";
      } else {
        nodeBadge.textContent = `Đang focus · Điểm rẽ Tầng ${active.depth}`;
        nodeBadge.className = "badge badge--met";
      }
    }
    if (nodeSituation) nodeSituation.textContent = active.situation;
    if (nodeStateDelta) {
      nodeStateDelta.textContent = active.state_delta || "";
      nodeStateDelta.hidden = !active.state_delta;
    }

    if (traceList) {
      traceList.replaceChildren();
      (active.trace_steps || []).forEach((step, idx) => {
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
        traceList.append(li);
      });
    }

    if (nodeImpact) nodeImpact.textContent = active.system_impact;
    if (nodeTradeoff) nodeTradeoff.textContent = active.tradeoff_note;

    if (active.is_terminal) {
      if (optionsSection) optionsSection.hidden = true;
      if (customSection) customSection.hidden = true;
      if (endingSection) endingSection.hidden = false;

      const dims = evaluateNodeDimensions(active);

      if (outcomeSummary) {
        outcomeSummary.replaceChildren();
        outcomeSummary.append(el("span", `badge ${dims.safety.cls}`, dims.safety.summaryText));
        outcomeSummary.append(el("span", `badge ${dims.operational.cls}`, dims.operational.summaryText));
      }

      if (safetyList) {
        safetyList.replaceChildren();
        if (dims.safetyItems.length) {
          for (const inv of dims.safetyItems) safetyList.append(renderInvariantCard(inv));
        } else {
          const emptySafety = el("li", "invariant-card invariant-card--unassessed");
          emptySafety.append(el("strong", "", "Chưa có dữ liệu đối chiếu bất biến dữ liệu"));
          safetyList.append(emptySafety);
        }
      }

      if (operationalList) {
        operationalList.replaceChildren();
        if (dims.operationalItems.length) {
          for (const inv of dims.operationalItems) operationalList.append(renderInvariantCard(inv));
        } else {
          const unassessed = el("li", "invariant-card invariant-card--unassessed");
          const top = el("div", "profile-entry__meta");
          top.append(el("strong", "", "Trạng thái vận hành của lượt hiện tại"));
          top.append(el("span", "badge badge--neutral", "CHƯA ĐÁNH GIÁ"));
          unassessed.append(top);
          unassessed.append(
            el(
              "p",
              "text-secondary",
              "Lượt mô phỏng đang xem được tạo trước khi bổ sung nhóm tiêu chí Hiệu năng & Vận hành, nên hệ thống ghi nhận Chưa đánh giá thay vì tự suy đoán. Hãy xem mục Tác động hệ thống / Đánh đổi kỹ thuật ở trên, hoặc bấm 'Tạo lượt mô phỏng mới' ở đầu trang để sinh một lượt tách biệt có đầy đủ cả 2 nhóm tiêu chí (lượt hiện tại vẫn được giữ nguyên)."
            )
          );
          operationalList.append(unassessed);
        }
      }

      if (comparisonNote) {
        comparisonNote.textContent = active.comparison_note || "";
        comparisonNote.hidden = !active.comparison_note;
      }
      if (rewindParentBtn) {
        rewindParentBtn.hidden = !activeParentId;
        rewindParentBtn.disabled = busy || !activeParentId;
      }
      if (rewindRootBottomBtn) {
        rewindRootBottomBtn.hidden = active.id === state.root_node_id;
        rewindRootBottomBtn.disabled = busy || active.id === state.root_node_id;
      }
    } else {
      if (endingSection) endingSection.hidden = true;
      if (optionsSection) optionsSection.hidden = false;
      if (optionsList) {
        optionsList.replaceChildren();
        const visitedSet = new Set(state.visited_node_ids || []);
        for (const opt of active.options || []) {
          const card = el("div", "option-card");
          const header = el("div", "profile-entry__meta");
          header.append(el("strong", "", opt.label));
          if (visitedSet.has(opt.target_node_id)) {
            header.append(el("span", "badge", "Đã xem nhánh này"));
          }
          card.append(header);
          card.append(el("p", "text-secondary", opt.action_summary));
          const btn = el(
            "button",
            "btn btn--primary",
            visitedSet.has(opt.target_node_id) ? "Focus lại kết quả nhánh này" : "Thử & focus nhánh này"
          );
          btn.type = "button";
          btn.disabled = busy;
          btn.addEventListener("click", () => chooseBranchOption(active.id, opt.option_id));
          card.append(btn);
          optionsList.append(card);
        }
      }

      if (customSection) {
        customSection.hidden = false;
        const limit = state.custom_branch_limit || 2;
        const remaining = Math.max(0, limit - (state.custom_branches_used || 0));
        if (customQuota) {
          customQuota.textContent = remaining > 0
            ? `Còn ${remaining}/${limit} lượt tự đề xuất phương án trong lượt Replay này (lỗi hoặc nhập trống không trừ lượt).`
            : `Đã dùng hết ${limit}/${limit} lượt tự đề xuất cho lượt Replay này. Bạn vẫn có thể bấm xem tất cả các nhánh trên cây.`;
        }
        if (customInput) customInput.disabled = busy || remaining <= 0;
        if (customSubmit) customSubmit.disabled = busy || remaining <= 0;
        updateCustomCharCount();
      }
    }
  }

  async function navigateToNode(nodeId, { scrollToFocus = false, focusMode = "heading" } = {}) {
    if (busy || !runState) return;
    if (nodeId === runState.active_node_id) {
      restoreFocus(focusMode, nodeId);
      return;
    }
    setBusyState(true);
    setError("");
    setStatus("Đang chuyển focus tới node đã chọn…");
    announce("Đang tải kết quả mô phỏng của node đã chọn.");
    renderActiveNode(runState);
    let succeeded = false;
    try {
      runState = await api.selectReplayNode(runId, nodeId);
      setStatus("");
      succeeded = true;
    } catch (err) {
      setError(err.message || "Chưa chuyển được nhánh. Các nhánh đã mở vẫn được giữ nguyên.");
      setStatus("");
      announce("Chưa chuyển được node. Vui lòng thử lại.");
    } finally {
      setBusyState(false);
      renderActiveNode(runState);
      if (succeeded) {
        const active = getNodeMap(runState).get(runState.active_node_id);
        restoreFocus(focusMode, runState.active_node_id);
        announce(buildNodeAnnouncement(active));
        if (scrollToFocus && focusCard && typeof focusCard.scrollIntoView === "function") {
          focusCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }
    }
  }

  async function rewindStep() {
    if (!runState || busy) return;
    const nodeMap = getNodeMap(runState);
    const { parentOf } = deriveParentMap(runState, nodeMap);
    const active = nodeMap.get(runState.active_node_id);
    const parentId = active && (active.parent_id || parentOf.get(active.id));
    if (parentId) await navigateToNode(parentId, { scrollToFocus: false, focusMode: "heading" });
  }

  async function chooseBranchOption(nodeId, optionId) {
    if (busy || !runState) return;
    setBusyState(true);
    setError("");
    setStatus("Đang mở nhánh mô phỏng…");
    announce("Đang mở nhánh mô phỏng đã chọn.");
    renderActiveNode(runState);
    let succeeded = false;
    try {
      runState = await api.chooseReplayOption(runId, nodeId, optionId);
      setStatus("");
      succeeded = true;
    } catch (err) {
      setError(err.message || "Chưa thể chọn nhánh này. Hãy thử lại.");
      setStatus("");
      announce("Chưa thể mở nhánh này.");
    } finally {
      setBusyState(false);
      renderActiveNode(runState);
      if (succeeded) {
        const active = getNodeMap(runState).get(runState.active_node_id);
        restoreFocus("heading", runState.active_node_id);
        announce(buildNodeAnnouncement(active));
      }
    }
  }

  if (rewindParentBtn) rewindParentBtn.addEventListener("click", rewindStep);
  if (rewindParentTopBtn) rewindParentTopBtn.addEventListener("click", rewindStep);
  if (jumpRootBtn) {
    jumpRootBtn.addEventListener("click", () => {
      if (runState) navigateToNode(runState.root_node_id, { scrollToFocus: false, focusMode: "heading" });
    });
  }
  if (rewindRootBottomBtn) {
    rewindRootBottomBtn.addEventListener("click", () => {
      if (runState) navigateToNode(runState.root_node_id, { scrollToFocus: false, focusMode: "heading" });
    });
  }

  if (customInput) {
    customInput.addEventListener("input", updateCustomCharCount);
  }

  if (customForm) {
    customForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (busy || !runState || !customInput) return;
      const proposal = customInput.value.trim();
      if (!proposal) {
        setError(
          "Hãy mô tả ngắn phương án kỹ thuật bạn muốn thử nghiệm (chưa trừ lượt tự đề xuất)."
        );
        if (typeof customInput.focus === "function") customInput.focus();
        return;
      }
      setBusyState(true);
      setError("");
      setStatus("Đang mô phỏng phương án tự đề xuất của bạn… Bài gốc và các nhánh cũ vẫn được giữ nguyên.");
      announce("Đang mô phỏng phương án bạn tự đề xuất.");
      renderActiveNode(runState);
      let succeeded = false;
      try {
        runState = await api.addCustomReplayBranch(runId, runState.active_node_id, proposal);
        customInput.value = "";
        updateCustomCharCount();
        setStatus("Đã thêm nhánh mô phỏng mới lên sơ đồ cây.");
        succeeded = true;
      } catch (err) {
        const baseMsg = err.message || "Chưa mô phỏng được nhánh tự đề xuất.";
        setError(`${baseMsg} Chưa trừ lượt tự đề xuất và nội dung bạn nhập vẫn được giữ nguyên.`);
        setStatus("");
        announce("Chưa tạo được nhánh mới; lượt tự đề xuất chưa bị trừ.");
      } finally {
        setBusyState(false);
        renderActiveNode(runState);
        if (succeeded) {
          const active = getNodeMap(runState).get(runState.active_node_id);
          restoreFocus("heading", runState.active_node_id);
          announce(buildNodeAnnouncement(active));
        }
      }
    });
  }

  async function bootstrap() {
    if (initialScript && initialScript.textContent && initialScript.textContent.trim()) {
      try {
        runState = JSON.parse(initialScript.textContent);
        renderActiveNode(runState);
        return;
      } catch (_ignored) { /* Fall back to API fetch */ }
    }
    if (!api || typeof api.getReplayRun !== "function") return;
    setStatus("Đang tải cây Decision Replay…");
    try {
      runState = await api.getReplayRun(runId);
      setStatus("");
      renderActiveNode(runState);
    } catch (err) {
      setStatus("");
      setError(err.message || "Chưa tải được dữ liệu Decision Replay.");
    }
  }

  bootstrap();
})();
