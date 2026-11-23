(() => {
  "use strict";

  const page = document.querySelector("[data-session-summary]");
  if (!page) return;
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

  function renderOutcome(outcome) {
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
      item.append(node("p", "", `Điểm thiếu đã xác nhận: ${outcome.confirmed_gap_criterion_ids.join(", ")}`));
    }

    const actions = node("div", "action-row");
    if (outcome.answer_ref && outcome.answer_ref.id) {
      const review = node("a", "btn btn--secondary", "Xem căn cứ và tiêu chí");
      review.href = `/sessions/${encodeURIComponent(sessionId)}/review?answer_id=${encodeURIComponent(outcome.answer_ref.id)}`;
      actions.append(review);
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
    item.append(node("p", "", gap.reason || "API chưa cung cấp lý do chi tiết cho điểm thiếu này."));
    const link = node("a", "btn btn--secondary", "Tìm bài tập cho kỹ năng này");
    link.href = `/sessions/${encodeURIComponent(sessionId)}/exercises?skill_id=${encodeURIComponent(gap.skill_id || "")}`;
    item.append(link);
    return item;
  }

  function renderSummary(data) {
    stateBadge.textContent = stateNames[data.state] || data.state;
    coverageCount.textContent = `Có kết quả ${data.completed_question_count} / ${data.total_question_count} câu`;
    appendValues(unanswered, data.unanswered_categories);
    appendValues(unresolved, data.unresolved_categories);

    outcomesList.replaceChildren();
    for (const outcome of data.outcomes || []) outcomesList.append(renderOutcome(outcome));
    outcomesEmpty.hidden = Boolean(data.outcomes && data.outcomes.length);

    gapsList.replaceChildren();
    for (const gap of data.observed_gaps || []) gapsList.append(renderGap(gap));
    gapsEmpty.hidden = Boolean(data.observed_gaps && data.observed_gaps.length);

    content.hidden = false;
    statusBox.hidden = true;
  }

  async function loadSummary() {
    statusBox.hidden = false;
    statusBox.textContent = "Đang tải kết quả và độ phủ phiên…";
    errorBox.hidden = true;
    content.hidden = true;
    try {
      const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/summary`, {
        headers: { accept: "application/json" },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.message || `Không tải được tổng kết (${response.status}).`);
      renderSummary(payload);
    } catch (error) {
      statusBox.hidden = true;
      errorBox.textContent = `${error.message || "Chưa tải được tổng kết."} Phiên vẫn được giữ nguyên.`;
      errorBox.hidden = false;
      const retry = node("button", "btn btn--secondary", "Tải lại tổng kết");
      retry.type = "button";
      retry.addEventListener("click", loadSummary);
      errorBox.replaceChildren(document.createTextNode(`${error.message || "Chưa tải được tổng kết."} Phiên vẫn được giữ nguyên. `), retry);
    }
  }

  loadSummary();
})();
