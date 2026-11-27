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
  const retryEvalButton = document.querySelector("#retry-review-evaluation");
  const nextButton = document.querySelector("#next-question");
  const content = document.querySelector("#review-content");
  const criteriaList = document.querySelector("#criteria-list");
  const total = document.querySelector("#evaluation-total");
  const evaluationState = document.querySelector("#evaluation-state");
  const answerSource = document.querySelector("#answer-source");
  const questionPrompt = document.querySelector("#review-question-prompt");
  const questionCode = document.querySelector("#review-question-code");
  const detail = document.querySelector("#evidence-detail");
  const explanation = document.querySelector("#selected-criterion-explanation");
  let evaluation = null;
  let feedbackItems = [];
  let retryingEvaluation = false;

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

  function renderEvidence(check, { scrollToHighlight = false } = {}) {
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
    renderAnswerWithHighlights(evaluation.answer_text, quotes, { scrollToHighlight });
  }

  function renderAnswerWithHighlights(text, evidenceItems, { scrollToHighlight = false } = {}) {
    answerSource.replaceChildren();
    const points = Array.from(text);
    const ranges = evidenceItems
      .filter((item) => Number.isInteger(item.start_offset) && Number.isInteger(item.end_offset))
      .map((item) => ({ start: item.start_offset, end: item.end_offset, quote: item.quote }))
      .filter((item) => item.start >= 0 && item.end <= points.length && item.end >= item.start)
      .sort((left, right) => left.start - right.start);

    let cursor = 0;
    let scrolled = false;
    for (const range of ranges) {
      if (range.start < cursor || points.slice(range.start, range.end).join("") !== range.quote) continue;
      answerSource.append(document.createTextNode(points.slice(cursor, range.start).join("")));
      const mark = element("mark", "", points.slice(range.start, range.end).join(""));
      answerSource.append(mark);
      if (scrollToHighlight && !scrolled && typeof mark.scrollIntoView === "function") {
        mark.scrollIntoView({ block: "nearest" });
        scrolled = true;
      }
      cursor = range.end;
    }
    answerSource.append(document.createTextNode(points.slice(cursor).join("")));
  }

  function selectCriterion(button, check, { scrollToHighlight = false } = {}) {
    for (const active of criteriaList.querySelectorAll(".criterion-button")) {
      active.setAttribute("aria-pressed", "false");
    }
    button.setAttribute("aria-pressed", "true");
    renderEvidence(check, { scrollToHighlight });
  }

  function failureMessageFor(data) {
    if (data.failure_code === "PROVIDER_TIMEOUT") {
      return "AI phản hồi quá thời gian. Câu trả lời gốc vẫn được lưu nguyên vẹn và chưa bị chấm điểm; bạn có thể thử đánh giá lại.";
    }
    if (data.failure_code === "EVALUATION_INTERRUPTED") {
      return "Lượt đánh giá trước bị gián đoạn. Câu trả lời gốc đã được lưu và bạn có thể thử đánh giá lại.";
    }
    if (data.retryable) {
      return "Chưa thể hoàn tất đánh giá cho bài đã lưu. Câu trả lời gốc vẫn còn nguyên và chưa có điểm; bạn có thể thử đánh giá lại.";
    }
    return "Dịch vụ AI hiện chưa thể đánh giá bài này. Câu trả lời gốc vẫn được giữ; hãy khắc phục lỗi dịch vụ rồi quay lại tổng kết.";
  }

  function renderEvaluation(response) {
    const data = response && response.result;
    if (!data) throw new Error("Máy chủ trả thiếu kết quả đánh giá theo DTO.");
    evaluation = data;
    questionPrompt.textContent = data.question_prompt || "";
    questionCode.textContent = data.question_code || "";
    questionCode.hidden = !data.question_code;
    feedbackItems = response.feedback_items || [];
    criteriaList.replaceChildren();
    answerSource.textContent = data.answer_text;

    if (data.status === "failed") {
      content.hidden = true;
      if (nextButton) nextButton.hidden = true;
      retryButton.hidden = true;
      errorBox.textContent = failureMessageFor(data);
      errorBox.hidden = false;
      statusBox.textContent = "Câu trả lời gốc đã được lưu trên máy chủ; chưa có điểm đánh giá.";
      statusBox.hidden = false;
      if (retryEvalButton) {
        retryEvalButton.hidden = !data.retryable;
        retryEvalButton.disabled = false;
      }
      errorBox.focus();
      return;
    }

    if (data.status === "processing" || data.status === "pending") {
      content.hidden = true;
      if (nextButton) nextButton.hidden = true;
      errorBox.hidden = true;
      if (retryEvalButton) retryEvalButton.hidden = true;
      statusBox.textContent = "Bài trả lời đã lưu và đang được AI đối chiếu rubric. Hãy bấm Tải lại kết quả sau ít giây.";
      statusBox.hidden = false;
      retryButton.hidden = false;
      return;
    }

    if (data.total_score === null || data.total_score === undefined) {
      const hasUnresolved = (data.criterion_checks || []).some((check) => check.status === "insufficient_evidence");
      total.textContent = data.status === "completed" && hasUnresolved
        ? "Chưa tính tổng điểm (còn tiêu chí chưa đủ bằng chứng)"
        : "Chưa có điểm vì đánh giá chưa hoàn tất";
    } else {
      total.textContent = `${data.total_score} / ${data.maximum_score}`;
    }
    evaluationState.textContent = data.status === "completed" ? "Đã đánh giá" : "Chưa hoàn tất đánh giá";

    let firstSelection = null;
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
        selectCriterion(button, check, { scrollToHighlight: true });
      });
      if (!firstSelection) firstSelection = { button, check };
      criteriaList.append(card);
    }

    content.hidden = false;
    statusBox.hidden = true;
    errorBox.hidden = true;
    retryButton.hidden = true;
    if (retryEvalButton) retryEvalButton.hidden = true;
    if (nextButton && data.status === "completed" && answerId === page.dataset.currentAnswerId
        && answerRevision === Number(page.dataset.currentAnswerRevision)) {
      nextButton.hidden = false;
    }
    if (firstSelection) {
      selectCriterion(firstSelection.button, firstSelection.check, { scrollToHighlight: false });
    }
    if (data.status === "completed") {
      loadAdaptiveProbePlan();
      loadAnswerReplayAction();
    }
  }

  async function loadAnswerReplayAction() {
    const replaySection = document.querySelector("#answer-replay-section");
    const replaySummary = document.querySelector("#answer-replay-summary");
    const replayForm = document.querySelector("#answer-replay-form");
    const replayButton = document.querySelector("#answer-replay-submit");
    if (!replaySection || typeof api.getAnswerReplay !== "function") return;
    try {
      const info = await api.getAnswerReplay(sessionId, answerId, answerRevision);
      if (!info.available || !info.scenario) {
        replaySection.hidden = true;
        return;
      }
      replaySection.hidden = false;
      if (replaySummary) {
        replaySummary.textContent = `${info.scenario.title}: ${info.scenario.summary} (Bài trả lời gốc và điểm vẫn giữ nguyên).`;
      }
      if (replayForm) {
        replayForm.action = `/sessions/${encodeURIComponent(sessionId)}/answers/${encodeURIComponent(answerId)}/replay/start?revision=${encodeURIComponent(String(answerRevision))}`;
      }
      if (replayButton) {
        replayButton.textContent = info.existing_run_id
          ? "Tiếp tục / tua lại Decision Replay từ bài làm"
          : "Mở Decision Replay từ bài làm này";
      }
    } catch (_error) {
      replaySection.hidden = true;
    }
  }

  async function loadAdaptiveProbePlan() {
    const probeSection = document.querySelector("#adaptive-probe-section");
    if (!probeSection || typeof api.getFollowUpPlan !== "function") return;
    const probePolicy = document.querySelector("#probe-policy");
    const probeReason = document.querySelector("#probe-reason");
    const probePrompt = document.querySelector("#probe-prompt");
    const probeForm = document.querySelector("#probe-form");
    const probeResponse = document.querySelector("#probe-response");
    const probeSubmit = document.querySelector("#probe-submit");
    const probeError = document.querySelector("#probe-error");
    const probeResults = document.querySelector("#probe-results");
    const probeVariantNote = document.querySelector("#probe-variant-note");

    const renderPlan = (plan) => {
      probeSection.hidden = false;
      if (probePolicy) {
        probePolicy.textContent = `${plan.policy_summary} (Câu này: ${plan.answer_probes_used}/${plan.answer_probe_limit} · Phiên này: ${plan.session_probes_used}/${plan.session_probe_limit}).`;
      }
      if (probeVariantNote) probeVariantNote.textContent = plan.alternate_variant_note || "";
      if (probeError) probeError.hidden = true;
      if (probeResults) {
        probeResults.replaceChildren();
        for (const item of plan.existing_probes || []) {
          const box = element("article", "card card--subtle stack");
          box.append(element("p", "", `Tiêu chí đào sâu: ${item.criterion_label} (${item.outcome_status || item.status})`));
          if (item.response_text) box.append(element("p", "text-secondary", `Phần làm rõ đã gửi: ${item.response_text}`));
          if (item.outcome_score !== null && item.outcome_score !== undefined) {
            box.append(element("p", "", `Điểm sau làm rõ: ${item.outcome_score} / ${item.outcome_max_score}`));
          }
          if (item.outcome_explanation) box.append(element("p", "", item.outcome_explanation));
          probeResults.append(box);
        }
      }
      if (plan.can_probe && plan.probe_prompt) {
        if (probeReason) probeReason.textContent = plan.choice_reason || "";
        if (probePrompt) probePrompt.textContent = plan.probe_prompt;
        if (probeForm) {
          probeForm.hidden = false;
          probeForm.dataset.criterionId = plan.recommended_criterion_id || "";
        }
      } else {
        const stopLabels = {
          all_criteria_met: "Tất cả tiêu chí của câu trả lời này đã đạt — dừng hỏi đào sâu.",
          answer_probe_limit_reached: "Đã hoàn tất 1/1 lượt hỏi đào sâu cho câu trả lời này (đạt điều kiện dừng).",
          session_probe_limit_reached: "Đã đạt giới hạn 2/2 lượt hỏi đào sâu trong phiên này (đạt điều kiện dừng).",
          session_expired: "Phiên đã hết hạn nên không mở thêm lượt hỏi đào sâu.",
        };
        if (probeReason) probeReason.textContent = stopLabels[plan.stop_reason] || "";
        if (probePrompt) probePrompt.textContent = "";
        if (probeForm) probeForm.hidden = true;
      }
    };

    try {
      const plan = await api.getFollowUpPlan(sessionId, answerId, answerRevision);
      renderPlan(plan);
      if (probeForm && !probeForm.dataset.bound) {
        probeForm.dataset.bound = "1";
        probeForm.addEventListener("submit", async (event) => {
          event.preventDefault();
          const text = probeResponse ? probeResponse.value.trim() : "";
          if (!text) {
            if (probeError) {
              probeError.textContent = "Vui lòng nhập nội dung làm rõ trước khi gửi.";
              probeError.hidden = false;
            }
            return;
          }
          if (probeSubmit) probeSubmit.disabled = true;
          if (probeError) probeError.hidden = true;
          try {
            await api.submitFollowUp(sessionId, answerId, {
              answer_revision: answerRevision,
              criterion_id: probeForm.dataset.criterionId || null,
              response_text: text,
            });
            if (probeResponse) probeResponse.value = "";
            const updatedPlan = await api.getFollowUpPlan(sessionId, answerId, answerRevision);
            renderPlan(updatedPlan);
          } catch (err) {
            if (probeError) {
              probeError.textContent = err.message || "Chưa gửi được câu trả lời đào sâu.";
              probeError.hidden = false;
            }
          } finally {
            if (probeSubmit) probeSubmit.disabled = false;
          }
        });
      }
    } catch (_error) {
      probeSection.hidden = true;
    }
  }

  async function retrySavedEvaluation() {
    if (retryingEvaluation || !answerId || !Number.isInteger(answerRevision) || answerRevision < 1) return;
    retryingEvaluation = true;
    if (retryEvalButton) retryEvalButton.disabled = true;
    retryButton.hidden = true;
    errorBox.hidden = true;
    statusBox.textContent = "Đang gửi yêu cầu đánh giá lại bài đã lưu…";
    statusBox.hidden = false;
    try {
      const response = await api.evaluateAnswer(sessionId, answerId, answerRevision);
      renderEvaluation(response);
    } catch (error) {
      if (error.code === "EVALUATION_IN_PROGRESS") {
        statusBox.textContent = "Bài này đang được AI đánh giá. Hãy bấm Tải lại kết quả sau ít giây.";
        statusBox.hidden = false;
        if (retryEvalButton) retryEvalButton.hidden = true;
        retryButton.hidden = false;
      } else {
        const canRetry = error.code !== "SESSION_EXPIRED" && error.code !== "SESSION_FORBIDDEN" && error.status !== 410 && error.status !== 403 && error.retryable !== false;
        errorBox.textContent = `${error.message || "Chưa thể đánh giá lại bài đã lưu."} ${error.recoveryAction || "Bài trả lời gốc vẫn được giữ trên máy chủ."}`;
        errorBox.hidden = false;
        statusBox.textContent = "Câu trả lời gốc đã được lưu trên máy chủ; chưa có điểm đánh giá.";
        statusBox.hidden = false;
        if (retryEvalButton) {
          retryEvalButton.hidden = !canRetry;
          retryEvalButton.disabled = !canRetry;
        }
        errorBox.focus();
      }
    } finally {
      retryingEvaluation = false;
    }
  }

  async function loadEvaluation() {
    if (!answerId || !Number.isInteger(answerRevision) || answerRevision < 1) {
      statusBox.textContent = "Chưa có bài đã lưu để đối chiếu. Hãy quay lại trang câu hỏi và gửi câu trả lời trước.";
      return;
    }
    retryButton.hidden = true;
    if (retryEvalButton) retryEvalButton.hidden = true;
    errorBox.hidden = true;
    content.hidden = true;
    statusBox.hidden = false;
    statusBox.textContent = "Đang tải kết quả đã lưu…";
    try {
      const response = await api.getEvaluation(sessionId, answerId, answerRevision);
      renderEvaluation(response);
    } catch (error) {
      statusBox.hidden = true;
      const canRetry = error.code !== "SESSION_EXPIRED" && error.code !== "SESSION_FORBIDDEN" && error.status !== 410 && error.status !== 403 && error.retryable !== false;
      errorBox.textContent = `${error.message || "Chưa tải được kết quả."} ${error.recoveryAction || "Bài trả lời gốc vẫn được giữ trên máy chủ."}`;
      errorBox.hidden = false;
      retryButton.hidden = !canRetry;
      errorBox.focus();
    }
  }

  retryButton.addEventListener("click", loadEvaluation);
  if (retryEvalButton) retryEvalButton.addEventListener("click", retrySavedEvaluation);
  if (nextButton) {
    nextButton.addEventListener("click", async () => {
      nextButton.disabled = true;
      errorBox.hidden = true;
      statusBox.textContent = "Đang chuyển câu theo kết quả đã lưu…";
      statusBox.hidden = false;
      try {
        const session = await api.nextQuestion(sessionId, Number(page.dataset.currentIndex));
        const destination = session.state === "completed"
          ? `/sessions/${encodeURIComponent(sessionId)}/summary`
          : `/sessions/${encodeURIComponent(sessionId)}`;
        window.location.assign(destination);
      } catch (error) {
        statusBox.hidden = true;
        errorBox.textContent = `${error.message || "Chưa thể chuyển câu."} ${error.recoveryAction || "Kết quả đã lưu vẫn được giữ nguyên."}`;
        errorBox.hidden = false;
        errorBox.focus();
        const canRetryNext = error.code !== "SESSION_EXPIRED" && error.code !== "SESSION_FORBIDDEN" && error.status !== 410 && error.status !== 403;
        nextButton.disabled = !canRetryNext;
      }
    });
  }
  loadEvaluation();
})();
