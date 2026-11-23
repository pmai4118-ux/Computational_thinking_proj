(() => {
  "use strict";

  const page = document.querySelector("[data-answer-review]");
  if (!page) return;
  const sessionId = page.dataset.sessionId;
  const answerId = page.dataset.answerId;
  const answerRevision = Number(page.dataset.answerRevision);
  const api = window.InterviewApi;
  const statusBox = document.querySelector("#review-status");
  const errorBox = document.querySelector("#review-error");
  const retryButton = document.querySelector("#retry-review-load");
  const content = document.querySelector("#review-content");
  const criteriaList = document.querySelector("#criteria-list");
  const total = document.querySelector("#evaluation-total");
  const evaluationState = document.querySelector("#evaluation-state");
  const answerSource = document.querySelector("#answer-source");
  const detail = document.querySelector("#evidence-detail");
  const explanation = document.querySelector("#selected-criterion-explanation");
  let evaluation = null;
  let feedbackItems = [];

  const statusLabels = {
    met: "Đạt",
    unmet: "Chưa đạt",
    insufficient_evidence: "Chưa đủ bằng chứng",
  };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderEvidence(check) {
    detail.replaceChildren();
    explanation.textContent = check.explanation;
    const feedback = feedbackItems.find((item) => item.criterion_id === check.criterion_id);
    if (feedback) {
      detail.append(element("p", "evidence-observation", feedback.message));
      if (feedback.suggestion) {
        detail.append(element("p", "form-hint", `Gợi ý: ${feedback.suggestion}`));
      }
    }
    if (check.unresolved_reason) {
      detail.append(element("p", "evidence-observation", `Chưa đủ căn cứ: ${check.unresolved_reason}`));
    }
    const quotes = [];
    for (const evidence of check.evidence || []) {
      if (evidence.quote !== null && evidence.quote !== undefined) {
        const quote = element("blockquote", "evidence-quote");
        quote.append(element("strong", "", "Trích dẫn nguyên văn"));
        quote.append(element("p", "", evidence.quote));
        detail.append(quote);
        quotes.push(evidence);
      } else if (evidence.observation) {
        const observation = element("p", "evidence-observation");
        observation.append(element("strong", "", "Quan sát trên toàn bài trả lời: "));
        observation.append(document.createTextNode(evidence.observation));
        detail.append(observation);
      }
    }
    if (!quotes.length && !(check.evidence || []).some((item) => item.observation)) {
      detail.append(element("p", "text-secondary", "Chưa có đoạn trích hoặc quan sát gắn với tiêu chí này."));
    }
    renderAnswerWithHighlights(evaluation.answer_text, quotes);
  }

  function renderAnswerWithHighlights(text, evidenceItems) {
    answerSource.replaceChildren();
    const points = Array.from(text);
    const ranges = evidenceItems
      .filter((item) => Number.isInteger(item.start_offset) && Number.isInteger(item.end_offset))
      .map((item) => ({ start: item.start_offset, end: item.end_offset, quote: item.quote }))
      .filter((item) => item.start >= 0 && item.end <= points.length && item.end >= item.start)
      .sort((left, right) => left.start - right.start);

    let cursor = 0;
    for (const range of ranges) {
      if (range.start < cursor || points.slice(range.start, range.end).join("") !== range.quote) continue;
      answerSource.append(document.createTextNode(points.slice(cursor, range.start).join("")));
      const mark = element("mark", "", points.slice(range.start, range.end).join(""));
      answerSource.append(mark);
      mark.scrollIntoView({ block: "nearest" });
      cursor = range.end;
    }
    answerSource.append(document.createTextNode(points.slice(cursor).join("")));
  }

  function renderEvaluation(response) {
    const data = response && response.result;
    if (!data) throw new Error("Máy chủ trả thiếu kết quả đánh giá theo DTO.");
    evaluation = data;
    feedbackItems = response.feedback_items || [];
    criteriaList.replaceChildren();
    answerSource.textContent = data.answer_text;
    if (data.total_score === null || data.total_score === undefined) {
      const hasUnresolved = (data.criterion_checks || []).some((check) => check.status === "insufficient_evidence");
      total.textContent = data.status === "completed" && hasUnresolved
        ? "Chưa tính tổng điểm (còn tiêu chí chưa đủ bằng chứng)"
        : "Chưa có điểm vì đánh giá chưa hoàn tất";
    } else {
      total.textContent = `${data.total_score} / ${data.maximum_score}`;
    }
    evaluationState.textContent = data.status === "completed" ? "Đã đánh giá" : "Chưa hoàn tất đánh giá";

    for (const check of data.criterion_checks || []) {
      const card = element("article", "criterion-card");
      const button = element("button", "criterion-button");
      button.type = "button";
      button.setAttribute("aria-pressed", "false");
      const title = element("span", "criterion-button__title", check.criterion_label);
      const status = element("span", `badge ${check.status === "met" ? "badge--met" : check.status === "unmet" ? "badge--unmet" : "badge--unresolved"}`,
        statusLabels[check.status] || "Chưa có trạng thái");
      button.append(title, status);
      const score = check.score === null || check.score === undefined
        ? (check.status === "insufficient_evidence" ? "Chưa xác định" : "Chưa có điểm")
        : `${check.score} / ${check.max_score} điểm`;
      const scoreLine = element("p", "form-hint", score);
      card.append(button, scoreLine);
      button.addEventListener("click", () => {
        for (const active of criteriaList.querySelectorAll(".criterion-button")) {
          active.setAttribute("aria-pressed", "false");
        }
        button.setAttribute("aria-pressed", "true");
        renderEvidence(check);
      });
      criteriaList.append(card);
    }

    content.hidden = false;
    statusBox.hidden = true;
    errorBox.hidden = true;
    retryButton.hidden = true;
    const firstButton = criteriaList.querySelector(".criterion-button");
    if (firstButton) firstButton.click();
  }

  async function loadEvaluation() {
    if (!answerId || !Number.isInteger(answerRevision) || answerRevision < 1) {
      statusBox.textContent = "Chưa có bài đã lưu để đối chiếu. Hãy quay lại workspace và gửi câu trả lời trước.";
      return;
    }
    retryButton.hidden = true;
    errorBox.hidden = true;
    content.hidden = true;
    statusBox.hidden = false;
    statusBox.textContent = "Đang tải kết quả đã lưu…";
    try {
      const response = await api.getEvaluation(sessionId, answerId, answerRevision);
      renderEvaluation(response);
    } catch (error) {
      statusBox.hidden = true;
      errorBox.textContent = `${error.message || "Chưa tải được kết quả."} ${error.recoveryAction || "Bài trả lời gốc vẫn được giữ trên máy chủ."}`;
      errorBox.hidden = false;
      retryButton.hidden = false;
    }
  }

  retryButton.addEventListener("click", loadEvaluation);
  loadEvaluation();
})();
