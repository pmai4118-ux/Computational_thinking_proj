(() => {
  "use strict";

  const root = document.querySelector("[data-replay-studio]");
  if (!root) return;
  const api = window.InterviewApi;
  const runId = root.dataset.runId;
  const initialScript = document.querySelector("#replay-initial-data");
  const errorBox = document.querySelector("#replay-error");
  const statusBox = document.querySelector("#replay-status");
  const answerHost = document.querySelector("#replay-answer-source");
  const alignmentBanner = document.querySelector("#replay-alignment-banner");
  const assumptionsList = document.querySelector("#replay-assumptions-list");
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

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
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
    // Ensure path array fallback even if active_path_ids was empty
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
        el("p", "alert__hint", "Kết quả mô phỏng này hoàn toàn tách biệt — bài làm và điểm gốc không thay đổi.")
      );
    } else {
      alignmentBanner.className = "alert alert--status";
      alignmentBanner.append(el("p", "alert__title", "Đang focus nhánh What-If trên cây quyết định"));
      alignmentBanner.append(
        el("p", "alert__hint", "Bấm trực tiếp node cha hoặc node anh em trên cây phía trên để tua lại và so sánh kết cục.")
      );
    }
  }

  function summarizeNodeOutcome(node, visited) {
    if (node.id === runState.root_node_id) return { cls: "badge--met", text: "Điểm xuất phát" };
    if (!node.is_terminal) {
      return visited.has(node.id)
        ? { cls: "", text: `Đã qua · Tầng ${node.depth}` }
        : { cls: "", text: `Điểm rẽ · Tầng ${node.depth}` };
    }
    if (!visited.has(node.id)) {
      return { cls: "", text: "Chưa mở · Bấm để xem" };
    }
    const invs = node.invariants || [];
    const safetyBroken = invs.some((i) => i.category !== "operational" && i.status === "broken");
    const opRisk = invs.some(
      (i) => i.status === "warning" || (i.category === "operational" && i.status === "broken")
    );
    const hasUncertain = invs.some((i) => i.status === "uncertain");
    if (safetyBroken) return { cls: "badge--unmet", text: "Vỡ bất biến" };
    if (opRisk) return { cls: "badge--unresolved", text: "An toàn · Cảnh báo vận hành" };
    if (hasUncertain || !invs.length) return { cls: "badge--unresolved", text: "Cần kiểm chứng" };
    return { cls: "badge--met", text: "An toàn · Ổn định" };
  }

  function renderVisualTree(state, nodeMap, parentOf, activePathSet) {
    if (!treeNav) return;
    treeNav.replaceChildren();
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
      if (isActive && typeof card.setAttribute === "function") {
        card.setAttribute("aria-current", "step");
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
      } else {
        const meta = summarizeNodeOutcome(node, visited);
        topRow.append(el("span", `badge ${meta.cls} dtree__badge`, meta.text));
      }
      card.append(topRow);
      card.append(el("span", "dtree__label", node.branch_label || node.title));
      card.addEventListener("click", () => navigateToNode(node.id, { scrollToFocus: true }));
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
      btn.addEventListener("click", () => navigateToNode(id, { scrollToFocus: false }));
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

  function isConcurrentOrBlockedStep(step) {
    const text = `${step.time_label || ""} ${step.event || ""} ${step.state_after || ""}`.toLowerCase();
    return (
      text.includes("song song") ||
      text.includes("chờ") ||
      text.includes("chặn") ||
      text.includes("treo") ||
      text.includes("deadlock") ||
      text.includes("vỡ")
    );
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
        nodeBadge.textContent = "Nhánh bạn tự đề xuất · Kết cục";
        nodeBadge.className = "badge badge--met";
      } else if (active.is_terminal) {
        nodeBadge.textContent = "Đang focus · Kết cục nhánh mô phỏng";
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
        const li = el(
          "li",
          `trace-step${isConcurrentOrBlockedStep(step) ? " trace-step--concurrent" : ""}`
        );
        const rail = el("div", "trace-step__rail");
        rail.append(el("span", "trace-step__time", step.time_label || `Bước ${idx + 1}`));
        rail.append(el("span", "trace-step__actor", step.actor));
        li.append(rail);
        const body = el("div", "trace-step__body");
        body.append(el("p", "trace-step__event", step.event));
        if (step.state_after) {
          body.append(el("p", "trace-step__state", `Trạng thái: ${step.state_after}`));
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

      const invs = active.invariants || [];
      const safetyItems = invs.filter((item) => item.category !== "operational");
      const operationalItems = invs.filter((item) => item.category === "operational");

      if (outcomeSummary) {
        outcomeSummary.replaceChildren();
        const safetyPass = safetyItems.filter((i) => i.status === "preserved").length;
        const safetyFail = safetyItems.filter((i) => i.status === "broken").length;
        const safetyBadgeCls = safetyFail > 0
          ? "badge--unmet"
          : safetyPass === safetyItems.length && safetyItems.length > 0
            ? "badge--met"
            : "badge--unresolved";
        outcomeSummary.append(
          el(
            "span",
            `badge ${safetyBadgeCls}`,
            `Tính đúng đắn (Safety): ${safetyPass}/${safetyItems.length} Đạt`
          )
        );

        if (operationalItems.length > 0) {
          const opBroken = operationalItems.some((i) => i.status === "broken");
          const opWarn = operationalItems.some((i) => i.status === "warning" || i.status === "uncertain");
          const opCls = opBroken ? "badge--unmet" : opWarn ? "badge--unresolved" : "badge--met";
          const opLabel = opBroken
            ? "Hiệu năng & Vận hành: Nguy cơ nghẽn / Vỡ"
            : opWarn
              ? "Hiệu năng & Vận hành: Cảnh báo rủi ro"
              : "Hiệu năng & Vận hành: Ổn định";
          outcomeSummary.append(el("span", `badge ${opCls}`, opLabel));
        } else {
          outcomeSummary.append(
            el(
              "span",
              "badge badge--unresolved",
              "Hiệu năng & Vận hành: Bấm 'Phân tích lại cây mới' để tách nhóm chi tiết"
            )
          );
        }
      }

      if (safetyList) {
        safetyList.replaceChildren();
        for (const inv of safetyItems) safetyList.append(renderInvariantCard(inv));
      }
      if (operationalList) {
        operationalList.replaceChildren();
        if (operationalItems.length) {
          for (const inv of operationalItems) operationalList.append(renderInvariantCard(inv));
        } else {
          operationalList.append(
            el(
              "li",
              "invariant-card",
              "Bản phân tích cũ chưa tách riêng chỉ số Hiệu năng & Vận hành. Xem mục Tác động & Đánh đổi ở trên hoặc bấm 'Phân tích lại cây mới'."
            )
          );
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
        const remaining = Math.max(0, (state.custom_branch_limit || 2) - (state.custom_branches_used || 0));
        if (customQuota) {
          customQuota.textContent = remaining > 0
            ? `Còn ${remaining}/${state.custom_branch_limit || 2} lượt tự đề xuất phương án trong phiên Replay này.`
            : `Đã dùng hết ${state.custom_branch_limit || 2}/${state.custom_branch_limit || 2} lượt tự đề xuất. Bạn vẫn có thể bấm xem tất cả các nhánh trên cây.`;
        }
        if (customInput) customInput.disabled = busy || remaining <= 0;
        if (customSubmit) customSubmit.disabled = busy || remaining <= 0;
      }
    }
  }

  async function navigateToNode(nodeId, { scrollToFocus = false } = {}) {
    if (busy || !runState || nodeId === runState.active_node_id) return;
    busy = true;
    setError("");
    setStatus("Đang chuyển focus tới node đã chọn…");
    renderActiveNode(runState);
    try {
      runState = await api.selectReplayNode(runId, nodeId);
      setStatus("");
    } catch (err) {
      setError(err.message || "Chưa chuyển được nhánh. Các nhánh đã mở vẫn được giữ nguyên.");
      setStatus("");
    } finally {
      busy = false;
      renderActiveNode(runState);
      if (scrollToFocus && focusCard && typeof focusCard.scrollIntoView === "function") {
        focusCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }

  async function rewindStep() {
    if (!runState || busy) return;
    const nodeMap = getNodeMap(runState);
    const { parentOf } = deriveParentMap(runState, nodeMap);
    const active = nodeMap.get(runState.active_node_id);
    const parentId = active && (active.parent_id || parentOf.get(active.id));
    if (parentId) await navigateToNode(parentId, { scrollToFocus: false });
  }

  async function chooseBranchOption(nodeId, optionId) {
    if (busy || !runState) return;
    busy = true;
    setError("");
    setStatus("Đang mở nhánh mô phỏng…");
    renderActiveNode(runState);
    try {
      runState = await api.chooseReplayOption(runId, nodeId, optionId);
      setStatus("");
    } catch (err) {
      setError(err.message || "Chưa thể chọn nhánh này. Hãy thử lại.");
      setStatus("");
    } finally {
      busy = false;
      renderActiveNode(runState);
    }
  }

  if (rewindParentBtn) rewindParentBtn.addEventListener("click", rewindStep);
  if (rewindParentTopBtn) rewindParentTopBtn.addEventListener("click", rewindStep);
  if (jumpRootBtn) {
    jumpRootBtn.addEventListener("click", () => runState && navigateToNode(runState.root_node_id));
  }
  if (rewindRootBottomBtn) {
    rewindRootBottomBtn.addEventListener("click", () => runState && navigateToNode(runState.root_node_id));
  }

  if (customForm) {
    customForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (busy || !runState || !customInput) return;
      const proposal = customInput.value.trim();
      if (!proposal) {
        setError("Hãy mô tả ngắn phương án kỹ thuật bạn muốn thử nghiệm (ví dụ: dùng cột version + retry).");
        if (typeof customInput.focus === "function") customInput.focus();
        return;
      }
      busy = true;
      setError("");
      setStatus("Đang mô phỏng phương án tự đề xuất của bạn… Bài gốc và các nhánh cũ vẫn được giữ nguyên.");
      renderActiveNode(runState);
      try {
        runState = await api.addCustomReplayBranch(runId, runState.active_node_id, proposal);
        customInput.value = "";
        setStatus("Đã thêm nhánh thử nghiệm mới lên sơ đồ cây.");
      } catch (err) {
        setError(err.message || "Chưa mô phỏng được nhánh tự đề xuất. Hãy thử lại.");
        setStatus("");
      } finally {
        busy = false;
        renderActiveNode(runState);
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
