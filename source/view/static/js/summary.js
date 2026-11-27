(() => {
  "use strict";

  const page = document.querySelector("[data-session-summary]");
  if (!page) return;
  const api = window.InterviewApi;
  const sessionId = page.dataset.sessionId;
  const statusBox = document.querySelector("#summary-status");
  const errorBox = document.querySelector("#summary-error");
  const content = document.querySelector("#summary-content");
  const activity = window.InterviewActivity?.mount("summary-activity", statusBox);
  const stateBadge = document.querySelector("#summary-state");
  const coverageCount = document.querySelector("#coverage-count");
  const coverageRatio = document.querySelector("#coverage-ratio");
  const unanswered = document.querySelector("#unanswered-categories");
  const unresolved = document.querySelector("#unresolved-categories");
  const unansweredCountEl = document.querySelector("#unanswered-count");
  const unresolvedCountEl = document.querySelector("#unresolved-count");
  const outcomesCountMeta = document.querySelector("#outcomes-count-meta");
  const toggleOutcomesBtn = document.querySelector("#toggle-outcomes-btn");
  const outcomesList = document.querySelector("#outcomes-list");
  const outcomesEmpty = document.querySelector("#outcomes-empty");
  const gapsList = document.querySelector("#gaps-list");
  const gapsEmpty = document.querySelector("#gaps-empty");
  const assessmentCalls = new Set();
  const processingRetryChecks = new Map();
  let refreshTimer = null;
  let loadingSummary = false;
  let refreshRequested = false;
  let previousCompletedCount = -1;
  let allDetailsExpanded = false;

  const categoryNames = {
    programming_knowledge: "Kiến thức lập trình",
    technical_case: "Tình huống kỹ thuật",
    algorithm_explanation: "Giải thích thuật toán",
    ai_code_review: "Đánh giá mã nguồn",
  };
  const categoryIcons = {
    programming_knowledge: "code",
    technical_case: "database",
    algorithm_explanation: "memory",
    ai_code_review: "rate_review",
  };
  const stateNames = {
    completed: "Đã hoàn thành",
    ended_early: "Đã kết thúc sớm",
    in_progress: "Đang thực hiện",
    expired: "Đã hết hạn",
  };
  const evaluationNames = {
    completed: "Đã có kết quả",
    pending: "Đang chờ đánh giá",
    processing: "Đang đánh giá",
    failed: "Đánh giá thất bại",
  };

  function node(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  }

  function iconSpan(symbolName, className = "material-symbols-outlined") {
    const span = node("span", className, symbolName);
    span.setAttribute("aria-hidden", "true");
    return span;
  }

  function appendValues(list, values) {
    list.replaceChildren();
    for (const value of values || []) {
      list.append(node("li", "", categoryNames[value] || value));
    }
    if (!values || values.length === 0) list.append(node("li", "", "Không có"));
  }

  function buildCriterionLabelMap(observedGaps) {
    const labels = new Map();
    for (const gap of observedGaps || []) {
      if (gap.criterion_id && gap.criterion_label) {
        labels.set(gap.criterion_id, gap.criterion_label);
      }
    }
    return labels;
  }

  function updateToggleAllButton(hasDetails) {
    if (!toggleOutcomesBtn) return;
    toggleOutcomesBtn.hidden = !hasDetails;
    if (!hasDetails) return;
    const icon = iconSpan(allDetailsExpanded ? "unfold_less" : "unfold_more");
    const label = node("span", "", allDetailsExpanded ? "Thu gọn tất cả" : "Mở rộng tất cả");
    toggleOutcomesBtn.replaceChildren(icon, label);
    toggleOutcomesBtn.setAttribute("aria-pressed", String(allDetailsExpanded));
  }

  function setCardDetailsExpanded(drawer, triggerBtn, expanded) {
    drawer.hidden = !expanded;
    triggerBtn.setAttribute("aria-expanded", String(expanded));
    const textEl = triggerBtn.querySelector("[data-toggle-label]");
    if (textEl) textEl.textContent = expanded ? "Thu gọn nhận xét" : "Xem nhận xét & căn cứ";
  }

  if (toggleOutcomesBtn && typeof toggleOutcomesBtn.addEventListener === "function") {
    toggleOutcomesBtn.addEventListener("click", () => {
      allDetailsExpanded = !allDetailsExpanded;
      if (outcomesList && typeof outcomesList.querySelectorAll === "function") {
        for (const card of outcomesList.querySelectorAll(".outcome-card")) {
          const drawer = card.querySelector(".outcome-details");
          const trigger = card.querySelector(".outcome-expand-btn");
          if (drawer && trigger) setCardDetailsExpanded(drawer, trigger, allDetailsExpanded);
        }
      }
      updateToggleAllButton(true);
    });
  }

  function renderOutcome(outcome, criterionLabels, detail, index) {
    const item = node("li", "outcome-card");
    item.dataset.evaluationState = outcome.evaluation_status;
    item.dataset.category = outcome.category || "";

    if (["pending", "processing"].includes(outcome.evaluation_status)) {
      const skeleton = node("div", "outcome-skeleton");
      skeleton.setAttribute("aria-hidden", "true");
      item.append(skeleton);
    }

    const mainRow = node("div", "outcome-card__main");
    const identity = node("div", "outcome-card__identity");
    const iconBox = node("div", "outcome-cat-icon");
    iconBox.setAttribute("aria-hidden", "true");
    iconBox.append(iconSpan(categoryIcons[outcome.category] || "quiz"));

    const summaryCol = node("div", "outcome-card__summary");
    const meta = node("div", "outcome-meta");
    meta.append(node("span", "outcome-chip outcome-chip--category", categoryNames[outcome.category] || outcome.category));
    meta.append(node("span", "outcome-chip outcome-chip--neutral", evaluationNames[outcome.evaluation_status] || "Chưa có trạng thái đánh giá"));

    let scoreText;
    let scoreTone = "pending";
    if (outcome.total_score === null || outcome.total_score === undefined) {
      scoreText = outcome.evaluation_status === "completed" && outcome.unresolved_criteria_count > 0
        ? "Chưa tính tổng điểm (còn tiêu chí chưa đủ bằng chứng)."
        : outcome.evaluation_status === "completed"
          ? "Chưa có điểm tổng hợp trong dữ liệu phiên."
          : "Chưa có điểm vì câu trả lời chưa có kết quả đánh giá.";
    } else {
      scoreText = `${outcome.total_score} / ${outcome.maximum_score} điểm`;
      if (outcome.maximum_score && outcome.total_score === outcome.maximum_score) scoreTone = "full";
      else if (outcome.total_score === 0) scoreTone = "zero";
      else scoreTone = "partial";
    }
    const scorePill = node("span", `outcome-score-pill outcome-score-pill--${scoreTone}`);
    const scoreDot = node("span", "outcome-score-pill__dot");
    scoreDot.setAttribute("aria-hidden", "true");
    scorePill.append(scoreDot, node("span", "", scoreText));
    meta.append(scorePill);
    summaryCol.append(meta);

    const questionTitle = outcome.question_prompt || categoryNames[outcome.category] || outcome.category;
    const prefix = Number.isInteger(index) ? `Câu ${index + 1}: ` : "";
    const heading = node("h3", "", `${prefix}${questionTitle}`);
    summaryCol.append(heading);

    if (outcome.unresolved_criteria_count > 0) {
      summaryCol.append(node("p", "outcome-note-line", `${outcome.unresolved_criteria_count} tiêu chí chưa đủ bằng chứng.`));
    }
    if (outcome.confirmed_gap_criterion_ids && outcome.confirmed_gap_criterion_ids.length) {
      const gapNames = outcome.confirmed_gap_criterion_ids.map(
        (criterionId) => criterionLabels.get(criterionId) || criterionId
      );
      summaryCol.append(node("p", "outcome-note-line", `Điểm thiếu đã xác nhận: ${gapNames.join(", ")}`));
    }

    identity.append(iconBox, summaryCol);
    mainRow.append(identity);

    const hasFindings = Boolean(detail && detail.findings && detail.findings.length);
    let drawer = null;
    if (hasFindings) {
      const controls = node("div", "outcome-card__controls");
      const expandBtn = node("button", "outcome-expand-btn");
      expandBtn.type = "button";
      const labelSpan = node("span", "", allDetailsExpanded ? "Thu gọn nhận xét" : "Xem nhận xét & căn cứ");
      labelSpan.dataset.toggleLabel = "";
      expandBtn.append(labelSpan, iconSpan("expand_more"));
      expandBtn.setAttribute("aria-expanded", String(allDetailsExpanded));

      drawer = node("div", "outcome-details");
      drawer.hidden = !allDetailsExpanded;
      const metCount = detail.findings.filter((f) => f.status === "met").length;
      const head = node("div", "outcome-details__head");
      head.append(
        node("span", "", `Chi tiết căn cứ rubric (${metCount}/${detail.findings.length} tiêu chí đạt)`),
        node("span", "", "Đối chiếu tiêu chí đã quan sát")
      );
      drawer.append(head);

      const findingsList = node("ul", "outcome-findings-list");
      for (const finding of detail.findings) {
        const li = node("li", "outcome-finding-item");
        li.dataset.status = finding.status || "unresolved";
        const iconName = finding.status === "met"
          ? "check_circle"
          : finding.status === "unmet"
            ? "cancel"
            : "remove_circle";
        li.append(iconSpan(iconName, "material-symbols-outlined outcome-finding-icon"));

        const bodyWrap = node("div", "");
        const label = finding.status === "met" ? "Đạt" : finding.status === "unmet" ? "Cần cải thiện" : "Chưa đủ căn cứ";
        bodyWrap.append(node("strong", "", `${finding.criterion_label}: ${label}. `));
        bodyWrap.append(document.createTextNode(finding.explanation || ""));
        const evidence = (finding.evidence || []).map((ev) => ev.quote || ev.observation).filter(Boolean);
        if (evidence.length) {
          bodyWrap.append(node("span", "outcome-finding-evidence", `Căn cứ: ${evidence.join("; ")}`));
        }
        li.append(bodyWrap);
        findingsList.append(li);
      }
      drawer.append(findingsList);

      expandBtn.addEventListener("click", () => {
        const nextState = Boolean(drawer.hidden);
        setCardDetailsExpanded(drawer, expandBtn, nextState);
      });

      controls.append(expandBtn);
      mainRow.append(controls);
    }

    item.append(mainRow);
    if (drawer) item.append(drawer);

    const actions = node("div", "outcome-card__actions action-row");
    if (outcome.answer_ref && outcome.answer_ref.id) {
      const review = node("a", "btn btn--secondary", "Xem căn cứ và tiêu chí");
      const reviewUrl = new URL(`/sessions/${encodeURIComponent(sessionId)}/review`, window.location.origin);
      reviewUrl.searchParams.set("answer_id", outcome.answer_ref.id);
      reviewUrl.searchParams.set("revision", String(outcome.answer_ref.revision));
      review.href = reviewUrl.toString();
      actions.append(review);
    }
    if (detail && detail.evaluation_status === "failed" && detail.retryable && detail.answer_ref) {
      const retry = node("button", "btn btn--secondary", "Thử chấm lại câu này");
      retry.type = "button";
      retry.addEventListener("click", async () => {
        retry.disabled = true;
        window.InterviewActivity?.buttonBusy(retry, true);
        activity?.start({ kind: "assessment", title: "AI đang chấm lại bài đã lưu", description: "Giữ nguyên câu trả lời gốc và đối chiếu lại theo rubric của câu hỏi." });
        statusBox.hidden = false;
        statusBox.textContent = "Đang thử chấm lại từ câu trả lời đã lưu…";
        try {
          await api.evaluateAnswer(sessionId, detail.answer_ref.id, detail.answer_ref.revision);
        } catch (error) {
          errorBox.textContent = error.message || "Chưa thể chấm lại. Câu trả lời vẫn được lưu.";
          errorBox.hidden = false;
        } finally {
          retry.disabled = false;
          window.InterviewActivity?.buttonBusy(retry, false);
          loadSummary();
        }
      });
      actions.append(retry);
    }
    if (outcome.confirmed_gap_criterion_ids && outcome.confirmed_gap_criterion_ids.length) {
      const exercise = node("a", "btn btn--secondary", "Bài luyện liên quan");
      exercise.href = `/sessions/${encodeURIComponent(sessionId)}/exercises?skill_id=${encodeURIComponent(outcome.skill_id || "")}`;
      actions.append(exercise);
    }
    if (actions.childElementCount) item.append(actions);
    return item;
  }

  function renderGap(gap) {
    const item = node("li", "gap-card");
    item.append(node("h3", "", gap.criterion_label || gap.skill_label || "Điểm cần luyện"));
    if (gap.skill_label) item.append(node("p", "", `Kỹ năng: ${gap.skill_label}`));
    item.append(node("p", "", gap.reason || "Chưa có mô tả chi tiết cho điểm thiếu này."));
    const link = node("a", "btn btn--secondary", "Tìm bài tập cho kỹ năng này");
    link.href = `/sessions/${encodeURIComponent(sessionId)}/exercises?skill_id=${encodeURIComponent(gap.skill_id || "")}`;
    item.append(link);
    return item;
  }

  function renderSummary(data) {
    const report = data.report;
    const headings = [
      ["#coverage-heading", "Tổng quan"],
      ["#outcomes-heading", "Chi tiết từng câu"],
      ["#gaps-heading", "Đề xuất cải thiện"],
    ];
    for (const [selector, title] of headings) {
      const heading = document.querySelector(selector);
      if (heading) heading.textContent = title;
    }
    stateBadge.textContent = stateNames[data.state] || data.state;
    coverageCount.textContent = `Có kết quả ${data.completed_question_count} / ${data.total_question_count} câu`;
    if (coverageRatio) {
      const ratio = data.total_question_count > 0
        ? Math.round((data.completed_question_count / data.total_question_count) * 100)
        : 0;
      coverageRatio.textContent = `(${ratio}% phản hồi đã có kết quả)`;
    }
    if (unansweredCountEl) {
      unansweredCountEl.textContent = `${(data.unanswered_categories || []).length} câu`;
    }
    if (unresolvedCountEl) {
      unresolvedCountEl.textContent = `${(data.unresolved_categories || []).length} câu`;
    }
    appendValues(unanswered, data.unanswered_categories);
    appendValues(unresolved, data.unresolved_categories);

    const overviewHost = document.querySelector(".coverage-card");
    if (overviewHost) {
      const previous = overviewHost.querySelector("[data-report-overview]");
      if (previous) previous.remove();
      if (report && report.overview) {
        const section = node("div", "");
        section.dataset.reportOverview = "";
        section.append(node("p", "overview-scope-note", report.overview.scope_note));
        const axes = node("ul", "overview-axes-grid");
        for (const axis of report.overview.axes || []) {
          const axisCard = node("li", "overview-axis-card");
          axisCard.dataset.axis = axis.id || "";
          const axisHead = node("div", "overview-axis-card__head");
          const dot = node("span", "overview-axis-dot");
          dot.setAttribute("aria-hidden", "true");
          axisHead.append(dot, node("span", "", axis.label));
          const summaryMeta = axis.observed_count
            ? `${axis.met_count} đạt · ${axis.gap_count} cần cải thiện · ${axis.unresolved_count} chưa đủ căn cứ`
            : "Chưa được quan sát";
          axisCard.append(axisHead, node("span", "overview-axis-card__meta", summaryMeta));
          axes.append(axisCard);
        }
        section.append(axes);
        const strengths = report.overview.strengths || [];
        const strengthsBox = node("div", "overview-strengths-box");
        strengthsBox.append(node("h3", "", "Điểm mạnh có căn cứ"));
        strengthsBox.append(node("p", "", strengths.length
          ? strengths.map((item) => `${item.criterion_label}: ${item.explanation}`).join("; ")
          : "Chưa đủ kết quả để xác nhận điểm mạnh."));
        section.append(strengthsBox);
        overviewHost.append(section);
      }
    }

    const criterionLabels = buildCriterionLabelMap(data.observed_gaps);
    outcomesList.replaceChildren();
    let hasAnyDetails = false;
    const outcomes = data.outcomes || [];
    outcomes.forEach((outcome, index) => {
      const detail = (report && report.details || []).find((item) =>
        item.question_ref.id === outcome.question_ref.id && item.question_ref.version === outcome.question_ref.version);
      if (detail && detail.findings && detail.findings.length) hasAnyDetails = true;
      outcomesList.append(renderOutcome(outcome, criterionLabels, detail, index));
    });
    if (outcomesCountMeta) {
      outcomesCountMeta.textContent = outcomes.length ? `(${outcomes.length} câu trong phiên)` : "";
    }
    updateToggleAllButton(hasAnyDetails);
    outcomesEmpty.hidden = Boolean(outcomes.length);

    gapsList.replaceChildren();
    if (report && report.proposals) {
      for (const proposal of report.proposals) {
        const item = node("li", "gap-card");
        item.append(node("h3", "", `Ưu tiên ${proposal.priority}: ${proposal.finding.criterion_label}`));
        item.append(node("p", "", `Căn cứ: ${proposal.finding.explanation}`));
        item.append(node("p", "", proposal.priority_reason));
        item.append(node("p", "", `Mục tiêu: ${proposal.goal}`));
        item.append(node("p", "", proposal.exercise_titles.length
          ? `Bài luyện theo thứ tự: ${proposal.exercise_titles.join(" → ")}${proposal.estimated_minutes ? ` (ước tính ${proposal.estimated_minutes} phút)` : ""}.`
          : proposal.note));
        if (proposal.exercise_titles.length) item.append(node("p", "", proposal.note));
        const link = node("a", "btn btn--secondary", "Xem bài luyện phù hợp");
        link.href = `/sessions/${encodeURIComponent(sessionId)}/exercises`;
        item.append(link);
        gapsList.append(item);
      }
    } else {
      for (const gap of data.observed_gaps || []) gapsList.append(renderGap(gap));
    }
    gapsEmpty.hidden = Boolean((data.observed_gaps && data.observed_gaps.length) || (report && report.proposals && report.proposals.length));

    content.hidden = false;
    const pending = report && report.status === "assessing";
    statusBox.hidden = !pending;
    if (pending) {
      activity?.start({ kind: "assessment", title: "AI đang đối chiếu phiên phỏng vấn", description: "Bài làm đã lưu. Kết quả từng câu sẽ xuất hiện ngay khi đối chiếu hoàn tất; bạn có thể quay lại trang này bất cứ lúc nào.", completed: report.overview.evaluated_count, total: report.overview.answered_count, skeleton: false });
      statusBox.replaceChildren(document.createTextNode(
        `AI đã chấm ${report.overview.evaluated_count}/${report.overview.answered_count} câu đã lưu. Bạn có thể rời trang và quay lại; các kết quả hoàn tất sẽ được dùng lại. `
      ));
      const progress = node("progress", "");
      progress.max = report.overview.answered_count;
      progress.value = report.overview.evaluated_count;
      progress.setAttribute("aria-label", "Số câu đã chấm trên số câu đã lưu");
      statusBox.append(progress);
    }
    if (!pending) {
      activity?.stop();
      if (previousCompletedCount !== data.completed_question_count) window.InterviewActivity?.reveal(content);
    }
    previousCompletedCount = data.completed_question_count;
    if (report && report.status === "partial_failure") {
      errorBox.textContent = report.message || "Một số câu chưa chấm được. Hãy thử lại từ bài đã lưu.";
      errorBox.hidden = false;
    }
  }

  function scheduleRefresh() {
    if (refreshTimer !== null) window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(loadSummary, 5000);
  }

  async function assessPending(data) {
    if (data.state !== "completed" && data.state !== "ended_early") return;
    const details = data.report && data.report.details || [];
    const now = Date.now();
    const pending = details.filter((item) => item.answer_ref && !assessmentCalls.has(item.answer_ref.id) && (
      item.evaluation_status === "pending" ||
      (item.evaluation_status === "processing" &&
        now - (processingRetryChecks.get(item.answer_ref.id) || 0) >= 60000)
    ));
    if (!pending.length) {
      if (details.some((item) => item.evaluation_status === "processing") || assessmentCalls.size) scheduleRefresh();
      else if (refreshTimer !== null) { window.clearTimeout(refreshTimer); refreshTimer = null; }
      return;
    }
    // At most two provider requests at once; completed revisions are replayed by the API.
    const capacity = Math.max(0, 2 - assessmentCalls.size);
    for (const item of pending.slice(0, capacity)) {
      assessmentCalls.add(item.answer_ref.id);
      if (item.evaluation_status === "processing") processingRetryChecks.set(item.answer_ref.id, now);
      api.evaluateAnswer(sessionId, item.answer_ref.id, item.answer_ref.revision)
        .catch((error) => {
          if (error.code !== "EVALUATION_IN_PROGRESS") {
            errorBox.textContent = error.message || "AI chưa chấm được câu trả lời đã lưu.";
            errorBox.hidden = false;
          }
        })
        .finally(() => {
          assessmentCalls.delete(item.answer_ref.id);
          loadSummary();
        });
    }
    scheduleRefresh();
  }

  async function loadSummary() {
    if (loadingSummary) { refreshRequested = true; return; }
    loadingSummary = true;
    if (refreshTimer !== null) { window.clearTimeout(refreshTimer); refreshTimer = null; }
    if (content.hidden) {
      statusBox.hidden = false;
      statusBox.textContent = "Đang tải kết quả và độ phủ phiên…";
      activity?.start({ kind: "loading", title: "Đang mở tổng kết của bạn", description: "Đọc các câu trả lời đã lưu và kết quả hiện có của phiên." });
    }
    errorBox.hidden = true;
    try {
      const payload = await api.getSessionSummary(sessionId);
      renderSummary(payload);
      assessPending(payload);
    } catch (error) {
      activity?.stop();
      statusBox.hidden = true;
      const missingSummaryRoute = error.status === 404 && error.code === "HTTP_ERROR";
      const message = missingSummaryRoute
        ? "Máy chủ hiện chưa cung cấp giao diện tổng kết phiên. Phiên vẫn được giữ nguyên. Bạn có thể mở bài tập hoặc thử tải lại sau."
        : `${error.message || "Chưa tải được tổng kết."} ${error.recoveryAction || "Phiên vẫn được giữ nguyên."}`;
      errorBox.textContent = message;
      errorBox.hidden = false;
      const canRetry = error.status !== 403 && error.code !== "SESSION_FORBIDDEN";
      if (canRetry) {
        const retry = node("button", "btn btn--secondary", "Tải lại tổng kết");
        retry.type = "button";
        retry.addEventListener("click", loadSummary);
        errorBox.replaceChildren(document.createTextNode(`${message} `), retry);
      }
      errorBox.focus();
    } finally {
      loadingSummary = false;
      if (refreshRequested) { refreshRequested = false; loadSummary(); }
    }
  }

  if (typeof window.addEventListener === "function") window.addEventListener("pagehide", () => {
    if (refreshTimer !== null) window.clearTimeout(refreshTimer);
    activity?.stop();
  });
  loadSummary();
})();
