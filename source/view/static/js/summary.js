(() => {
  "use strict";

  const page = document.querySelector("[data-session-summary]");
  if (!page) return;
  const api = window.InterviewApi;
  const sessionId = page.dataset.sessionId;
  const statusBox = document.querySelector("#summary-status");
  const errorBox = document.querySelector("#summary-error");
  const content = document.querySelector("#summary-content");
  const stateBadge = document.querySelector("#summary-state");
  const coverageCount = document.querySelector("#coverage-count");
  const unanswered = document.querySelector("#unanswered-categories");
  const unresolved = document.querySelector("#unresolved-categories");
  const outcomesList = document.querySelector("#outcomes-list");
  const outcomesEmpty = document.querySelector("#outcomes-empty");
  const gapsList = document.querySelector("#gaps-list");
  const gapsEmpty = document.querySelector("#gaps-empty");
  const assessmentCalls = new Set();
  const processingRetryChecks = new Map();
  let refreshTimer = null;

  const categoryNames = {
    programming_knowledge: "Kiến thức lập trình",
    technical_case: "Tình huống kỹ thuật",
    algorithm_explanation: "Giải thích thuật toán",
    ai_code_review: "Đánh giá mã nguồn",
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

  function renderOutcome(outcome, criterionLabels, detail) {
    const item = node("li", "outcome-card");
    const heading = node("h3", "", outcome.question_prompt || categoryNames[outcome.category] || outcome.category);
    item.append(heading);

    const meta = node("div", "outcome-meta");
    meta.append(node("span", "badge", categoryNames[outcome.category] || outcome.category));
    meta.append(node("span", "badge", evaluationNames[outcome.evaluation_status] || "Chưa có trạng thái đánh giá"));
    item.append(meta);

    let scoreText;
    if (outcome.total_score === null || outcome.total_score === undefined) {
      scoreText = outcome.evaluation_status === "completed" && outcome.unresolved_criteria_count > 0
        ? "Chưa tính tổng điểm (còn tiêu chí chưa đủ bằng chứng)."
        : outcome.evaluation_status === "completed"
          ? "Chưa có điểm tổng hợp trong dữ liệu phiên."
        : "Chưa có điểm vì câu trả lời chưa có kết quả đánh giá.";
    } else {
      scoreText = `Điểm câu này: ${outcome.total_score} / ${outcome.maximum_score}`;
    }
    item.append(node("p", "", scoreText));

    if (outcome.unresolved_criteria_count > 0) {
      item.append(node("p", "", `${outcome.unresolved_criteria_count} tiêu chí chưa đủ bằng chứng.`));
    }
    if (outcome.confirmed_gap_criterion_ids && outcome.confirmed_gap_criterion_ids.length) {
      const gapNames = outcome.confirmed_gap_criterion_ids.map(
        (criterionId) => criterionLabels.get(criterionId) || criterionId
      );
      item.append(node("p", "", `Điểm thiếu đã xác nhận: ${gapNames.join(", ")}`));
    }
    if (detail && detail.findings && detail.findings.length) {
      const findings = node("ul", "");
      for (const finding of detail.findings) {
        const label = finding.status === "met" ? "Đạt" : finding.status === "unmet" ? "Cần cải thiện" : "Chưa đủ căn cứ";
        const evidence = (finding.evidence || []).map((item) => item.quote || item.observation).filter(Boolean);
        findings.append(node("li", "", `${finding.criterion_label}: ${label}. ${finding.explanation}${evidence.length ? ` Căn cứ: ${evidence.join("; ")}` : ""}`));
      }
      item.append(findings);
    }

    const actions = node("div", "action-row");
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
        statusBox.hidden = false;
        statusBox.textContent = "Đang thử chấm lại từ câu trả lời đã lưu…";
        try {
          await api.evaluateAnswer(sessionId, detail.answer_ref.id, detail.answer_ref.revision);
        } catch (error) {
          errorBox.textContent = error.message || "Chưa thể chấm lại. Câu trả lời vẫn được lưu.";
          errorBox.hidden = false;
        } finally {
          retry.disabled = false;
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
    appendValues(unanswered, data.unanswered_categories);
    appendValues(unresolved, data.unresolved_categories);
    const overviewHost = document.querySelector(".coverage-card");
    if (overviewHost) {
      const previous = overviewHost.querySelector("[data-report-overview]");
      if (previous) previous.remove();
      if (report && report.overview) {
        const section = node("div", "");
        section.dataset.reportOverview = "";
        section.append(node("p", "", report.overview.scope_note));
        const axes = node("ul", "");
        for (const axis of report.overview.axes || []) {
          axes.append(node("li", "", `${axis.label}: ${axis.observed_count ? `${axis.met_count} tiêu chí đạt, ${axis.gap_count} cần cải thiện, ${axis.unresolved_count} chưa đủ căn cứ` : "chưa được quan sát"}.`));
        }
        section.append(axes);
        const strengths = report.overview.strengths || [];
        section.append(node("h3", "", "Điểm mạnh có căn cứ"));
        section.append(node("p", "", strengths.length
          ? strengths.map((item) => `${item.criterion_label}: ${item.explanation}`).join("; ")
          : "Chưa đủ kết quả để xác nhận điểm mạnh."));
        overviewHost.append(section);
      }
    }

    const criterionLabels = buildCriterionLabelMap(data.observed_gaps);
    outcomesList.replaceChildren();
    for (const outcome of data.outcomes || []) {
      const detail = (report && report.details || []).find((item) =>
        item.question_ref.id === outcome.question_ref.id && item.question_ref.version === outcome.question_ref.version);
      outcomesList.append(renderOutcome(outcome, criterionLabels, detail));
    }
    outcomesEmpty.hidden = Boolean(data.outcomes && data.outcomes.length);

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
      statusBox.replaceChildren(document.createTextNode(
        `AI đã chấm ${report.overview.evaluated_count}/${report.overview.answered_count} câu đã lưu. Bạn có thể rời trang và quay lại; các kết quả hoàn tất sẽ được dùng lại. `
      ));
      const progress = node("progress", "");
      progress.max = report.overview.answered_count;
      progress.value = report.overview.evaluated_count;
      progress.setAttribute("aria-label", "Số câu đã chấm trên số câu đã lưu");
      statusBox.append(progress);
    }
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
    if (content.hidden) {
      statusBox.hidden = false;
      statusBox.textContent = "Đang tải kết quả và độ phủ phiên…";
    }
    errorBox.hidden = true;
    try {
      const payload = await api.getSessionSummary(sessionId);
      renderSummary(payload);
      assessPending(payload);
    } catch (error) {
      statusBox.hidden = true;
      const missingSummaryRoute = error.status === 404 && error.code === "HTTP_ERROR";
      const message = missingSummaryRoute
        ? "Máy chủ hiện chưa cung cấp API tổng kết phiên. Phiên vẫn được giữ nguyên. Bạn có thể mở bài tập hoặc thử tải lại sau."
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
    }
  }

  loadSummary();
})();
