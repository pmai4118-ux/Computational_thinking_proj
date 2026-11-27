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
  const invariantsList = document.querySelector("#replay-invariants-list");
  const comparisonNote = document.querySelector("#replay-comparison-note");
  const rewindParentBtn = document.querySelector("#replay-rewind-parent");

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
        el("p", "alert__hint", "Hệ thống không gán hệ quả chắc chắn cho bài làm của bạn. Hãy chọn một hướng bên phải để mô phỏng thử.")
      );
    } else if (activeNode.origin === "custom_user_branch") {
      alignmentBanner.className = "alert alert--status";
      alignmentBanner.append(el("p", "alert__title", "Đang xem nhánh thử nghiệm do bạn tự đề xuất"));
      alignmentBanner.append(
        el("p", "alert__hint", "Kết quả mô phỏng này hoàn toàn tách biệt — bài làm và điểm gốc không thay đổi.")
      );
    } else {
      alignmentBanner.className = "alert alert--status";
      alignmentBanner.append(el("p", "alert__title", "Đang mô phỏng nhánh What-If để so sánh với bài gốc"));
      alignmentBanner.append(
        el("p", "alert__hint", "Bạn có thể bấm vào bất kỳ nhánh nào ở cây bên dưới để nhảy qua lại và so sánh kết cục.")
      );
    }
  }

  function renderExploredTree(state, nodeMap) {
    if (!treeNav) return;
    treeNav.replaceChildren();
    const visited = new Set(state.visited_node_ids || []);
    visited.add(state.root_node_id);
    visited.add(state.active_node_id);

    const childrenByParent = new Map();
    for (const node of state.nodes || []) {
      if (!visited.has(node.id)) continue;
      const key = node.parent_id || "__root__";
      if (!childrenByParent.has(key)) childrenByParent.set(key, []);
      childrenByParent.get(key).push(node);
    }

    const walk = (node, listEl) => {
      const item = el("li", "replay-tree__item");
      const isActive = node.id === state.active_node_id;
      const btn = el(
        "button",
        `replay-tree__btn${isActive ? " is-active" : ""}${node.is_terminal ? " is-terminal" : ""}`
      );
      btn.type = "button";
      btn.disabled = busy;
      if (isActive && typeof btn.setAttribute === "function") {
        btn.setAttribute("aria-current", "step");
      }
      const tag = node.origin === "answer_start"
        ? "Xuất phát"
        : node.origin === "custom_user_branch"
          ? "Tự đề xuất"
          : node.is_terminal
            ? "Kết cục"
            : `Bước ${node.depth}`;
      btn.append(el("span", "replay-tree__tag", tag));
      btn.append(el("span", "replay-tree__label", node.branch_label || node.title));
      btn.addEventListener("click", () => navigateToNode(node.id));
      item.append(btn);

      const children = childrenByParent.get(node.id) || [];
      if (children.length) {
        const sub = el("ul", "replay-tree__branch");
        for (const child of children) walk(child, sub);
        item.append(sub);
      }
      listEl.append(item);
    };

    const rootNode = nodeMap.get(state.root_node_id);
    if (rootNode) {
      const topList = el("ul", "replay-tree");
      walk(rootNode, topList);
      treeNav.append(topList);
    }
  }

  function renderBreadcrumbs(state, nodeMap) {
    if (!breadcrumbNav) return;
    breadcrumbNav.replaceChildren();
    const pathIds = state.active_path_ids || [state.root_node_id];
    pathIds.forEach((id, idx) => {
      const node = nodeMap.get(id);
      if (!node) return;
      const isLast = idx === pathIds.length - 1;
      const btn = el("button", `replay-crumb${isLast ? " is-current" : ""}`, node.branch_label || node.title);
      btn.type = "button";
      btn.disabled = busy || isLast;
      btn.addEventListener("click", () => navigateToNode(id));
      breadcrumbNav.append(btn);
      if (!isLast) breadcrumbNav.append(el("span", "replay-crumb__sep", "›"));
    });
  }

  function renderActiveNode(state) {
    const nodeMap = getNodeMap(state);
    const active = nodeMap.get(state.active_node_id) || state.nodes[0];
    if (!active) return;

    renderHighlightedAnswer(state.linked_answer_text, active);
    renderAlignmentBanner(active, Boolean(state.linked_answer_text));
    renderExploredTree(state, nodeMap);
    renderBreadcrumbs(state, nodeMap);

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
        nodeBadge.textContent = "Kết cục nhánh mô phỏng";
        nodeBadge.className = "badge badge--unresolved";
      } else {
        nodeBadge.textContent = `Điểm rẽ quyết định · Tầng ${active.depth}`;
        nodeBadge.className = "badge";
      }
    }
    if (nodeSituation) nodeSituation.textContent = active.situation;
    if (nodeStateDelta) {
      nodeStateDelta.textContent = active.state_delta || "";
      nodeStateDelta.hidden = !active.state_delta;
    }

    if (traceList) {
      traceList.replaceChildren();
      for (const step of active.trace_steps || []) {
        const li = el("li", "trace-step");
        li.append(el("span", "trace-step__actor", step.actor));
        const body = el("div", "trace-step__body");
        body.append(el("p", "trace-step__event", step.event));
        if (step.state_after) {
          body.append(el("p", "trace-step__state", `Trạng thái: ${step.state_after}`));
        }
        li.append(body);
        traceList.append(li);
      }
    }

    if (nodeImpact) nodeImpact.textContent = active.system_impact;
    if (nodeTradeoff) nodeTradeoff.textContent = active.tradeoff_note;

    if (active.is_terminal) {
      if (optionsSection) optionsSection.hidden = true;
      if (customSection) customSection.hidden = true;
      if (endingSection) endingSection.hidden = false;
      if (invariantsList) {
        invariantsList.replaceChildren();
        const statusMeta = {
          preserved: { cls: "badge--met", label: "ĐẠT · Bảo toàn" },
          broken: { cls: "badge--unmet", label: "VỠ · Vi phạm" },
          uncertain: { cls: "badge--unresolved", label: "CHƯA RÕ · Cần kiểm chứng" },
        };
        for (const inv of active.invariants || []) {
          const meta = statusMeta[inv.status] || statusMeta.uncertain;
          const li = el("li", "invariant-card");
          const top = el("div", "profile-entry__meta");
          top.append(el("strong", "", inv.name));
          top.append(el("span", `badge ${meta.cls}`, meta.label));
          li.append(top);
          li.append(el("p", "text-secondary", inv.detail));
          invariantsList.append(li);
        }
      }
      if (comparisonNote) {
        comparisonNote.textContent = active.comparison_note || "";
        comparisonNote.hidden = !active.comparison_note;
      }
      if (rewindParentBtn) {
        rewindParentBtn.hidden = !active.parent_id;
        rewindParentBtn.disabled = busy;
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
            visitedSet.has(opt.target_node_id) ? "Mở lại kết quả nhánh này" : "Thử hướng đi này"
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
            : `Đã dùng hết ${state.custom_branch_limit || 2}/${state.custom_branch_limit || 2} lượt tự đề xuất. Bạn vẫn có thể bấm xem tất cả các nhánh đã mở.`;
        }
        if (customInput) customInput.disabled = busy || remaining <= 0;
        if (customSubmit) customSubmit.disabled = busy || remaining <= 0;
      }
    }
  }

  async function navigateToNode(nodeId) {
    if (busy || !runState || nodeId === runState.active_node_id) return;
    busy = true;
    setError("");
    setStatus("Đang chuyển tới điểm rẽ đã chọn…");
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
    }
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

  if (rewindParentBtn) {
    rewindParentBtn.addEventListener("click", () => {
      if (!runState) return;
      const active = getNodeMap(runState).get(runState.active_node_id);
      if (active && active.parent_id) navigateToNode(active.parent_id);
    });
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
        setStatus("Đã thêm nhánh thử nghiệm mới vào cây Decision Replay.");
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
