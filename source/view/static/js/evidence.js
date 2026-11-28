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
  const activity = window.InterviewActivity?.mount("review-activity", statusBox);
  const criteriaList = document.querySelector("#criteria-list");
  const total = document.querySelector("#evaluation-total");
  const evaluationState = document.querySelector("#evaluation-state");
  const answerSource = document.querySelector("#answer-source");
  const questionPrompt = document.querySelector("#review-question-prompt");
  const questionCode = document.querySelector("#review-question-code");
  const detail = document.querySelector("#evidence-detail");
  const explanation = document.querySelector("#selected-criterion-explanation");

  const tabOverviewBtn = document.querySelector("#review-tab-overview");
  const tabDetailBtn = document.querySelector("#review-tab-detail");
  const tabPanelOverview = document.querySelector("#tab-panel-overview");
  const tabPanelDetail = document.querySelector("#tab-panel-detail");
  const tabCriteriaCount = document.querySelector("#tab-criteria-count");
  const tabQuotesCount = document.querySelector("#tab-quotes-count");

  const scoreDonutArc = document.querySelector("#score-donut-arc");
  const scorePercentLabel = document.querySelector("#score-percent-label");
  const scoreBarsList = document.querySelector("#score-bars-list");
  const assessorSummaryText = document.querySelector("#assessor-summary-text");
  const criteriaCountPill = document.querySelector("#criteria-count-pill");
  const evidencePanelTitle = document.querySelector("#evidence-panel-title");
  const evidencePanelSubtitle = document.querySelector("#evidence-panel-subtitle");
  const evidencePanelIndexBadge = document.querySelector("#evidence-panel-index-badge");
  const evidencePanelScoreBadge = document.querySelector("#evidence-panel-score-badge");

  const detailMetBadge = document.querySelector("#detail-met-count-badge");
  const detailUnmetBadge = document.querySelector("#detail-unmet-count-badge");
  const detailUnresolvedBadge = document.querySelector("#detail-unresolved-count-badge");
  const detailAnswerMeta = document.querySelector("#detail-answer-meta");
  const detailPanelAccent = document.querySelector("#detail-panel-accent");
  const detailPanelSubtitle = document.querySelector("#detail-panel-subtitle");
  const detailPanelBadge = document.querySelector("#detail-panel-badge");
  const detailPanelBody = document.querySelector("#detail-panel-body");
  const jumpPrimaryUnmetBtn = document.querySelector("#jump-primary-unmet-btn");
  const copyAnswerBtn = document.querySelector("#copy-answer-btn");
  const copyAnswerLabel = document.querySelector("#copy-answer-label");

  let evaluation = null;
  let feedbackItems = [];
  let retryingEvaluation = false;
  let reviewRefreshTimer = null;
  let pollingStartedAt = 0;
  let loadingEvaluation = false;
  let selectedCriterionId = null;
  let activeTab = "overview";
  let parsedHighlights = { validRanges: [], invalidQuotes: [] };

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

  function badgeClassForStatus(status) {
    if (status === "met") return "badge--met";
    if (status === "unmet") return "badge--unmet";
    return "badge--unresolved";
  }

  function countWords(text) {
    const trimmed = String(text || "").trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }

  function collectValidEvidenceRanges(text, checks) {
    const points = Array.from(text || "");
    const validRanges = [];
    const invalidQuotes = [];
    const seenQuoteKeys = new Set();

    for (const check of checks || []) {
      for (const item of check.evidence || []) {
        if (item.quote === null || item.quote === undefined) continue;
        const start = item.start_offset;
        const end = item.end_offset;
        const isInt = Number.isInteger(start) && Number.isInteger(end);
        const inBounds = isInt && start >= 0 && end <= points.length && end > start;
        const matches = inBounds && points.slice(start, end).join("") === item.quote;
        if (!matches) {
          invalidQuotes.push({ check, evidence: item });
          continue;
        }
        validRanges.push({
          start,
          end,
          quote: item.quote,
          criterionId: check.criterion_id,
          status: check.status,
          check,
          evidence: item,
        });
        seenQuoteKeys.add(`${start}:${end}:${item.quote}`);
      }
    }

    return { validRanges, invalidQuotes, uniqueQuoteCount: seenQuoteKeys.size };
  }

  function splitIntoAtomicSegments(pointsLength, ranges) {
    if (!ranges.length) {
      return [{ start: 0, end: pointsLength, entries: [] }];
    }
    const boundaries = new Set([0, pointsLength]);
    for (const r of ranges) {
      boundaries.add(r.start);
      boundaries.add(r.end);
    }
    const sorted = Array.from(boundaries).sort((a, b) => a - b);
    const segments = [];
    for (let i = 0; i < sorted.length - 1; i += 1) {
      const segStart = sorted[i];
      const segEnd = sorted[i + 1];
      if (segEnd <= segStart) continue;
      const entries = ranges.filter((r) => r.start <= segStart && r.end >= segEnd);
      segments.push({ start: segStart, end: segEnd, entries });
    }
    return segments;
  }

  function segmentVisualStatus(entries) {
    if (!entries.length) return null;
    const statuses = new Set(entries.map((e) => e.status));
    if (statuses.size === 1) {
      if (statuses.has("met")) return "met";
      if (statuses.has("unmet")) return "unmet";
    }
    return "mixed";
  }

  function switchTab(tabName) {
    activeTab = tabName === "detail" ? "detail" : "overview";
    const isOverview = activeTab === "overview";
    if (tabOverviewBtn) {
      tabOverviewBtn.setAttribute("aria-selected", isOverview ? "true" : "false");
      tabOverviewBtn.tabIndex = isOverview ? 0 : -1;
    }
    if (tabDetailBtn) {
      tabDetailBtn.setAttribute("aria-selected", isOverview ? "false" : "true");
      tabDetailBtn.tabIndex = isOverview ? -1 : 0;
    }
    if (tabPanelOverview) tabPanelOverview.hidden = !isOverview;
    if (tabPanelDetail) tabPanelDetail.hidden = isOverview;
    if (window.location && typeof window.history !== "undefined" && typeof window.history.replaceState === "function") {
      try {
        window.history.replaceState(null, "", isOverview ? "#overview" : "#detail");
      } catch (_error) { /* Ignore restricted history contexts. */ }
    }
  }

  function renderDetailFeedbackPanel(check, activeSegmentEntries) {
    if (!detailPanelBody) return;
    detailPanelBody.replaceChildren();
    const feedback = feedbackItems.find((item) => item.criterion_id === check.criterion_id);
    const checkIndex = (evaluation.criterion_checks || []).findIndex((c) => c.criterion_id === check.criterion_id);

    if (detailPanelAccent) {
      detailPanelAccent.className = `detail-feedback-panel__accent detail-feedback-panel__accent--${check.status === "met" ? "met" : check.status === "unmet" ? "unmet" : "unresolved"}`;
    }
    if (detailPanelSubtitle) {
      detailPanelSubtitle.textContent = `Tiêu chí ${checkIndex + 1} / ${(evaluation.criterion_checks || []).length}: ${check.criterion_label}`;
    }
    if (detailPanelBadge) {
      detailPanelBadge.className = `badge ${badgeClassForStatus(check.status)}`;
      const scoreText = check.score === null || check.score === undefined
        ? "Chưa xác định"
        : `${check.score}/${check.max_score} điểm`;
      detailPanelBadge.textContent = `${statusLabels[check.status] || check.status} • ${scoreText}`;
    }

    if (Array.isArray(activeSegmentEntries) && activeSegmentEntries.length > 1) {
      const overlapWrap = element("div", "evidence-observation");
      overlapWrap.append(element("strong", "", "Đoạn văn bản này liên quan tới nhiều tiêu chí (chồng lấn)"));
      const btnRow = element("div", "action-row");
      for (const entry of activeSegmentEntries) {
        const switchBtn = element("button", `btn ${entry.criterionId === check.criterion_id ? "btn--primary" : "btn--secondary"}`, entry.check.criterion_label);
        switchBtn.type = "button";
        switchBtn.addEventListener("click", () => {
          selectCriterionById(entry.criterionId, { scrollToHighlight: false });
        });
        btnRow.append(switchBtn);
      }
      overlapWrap.append(btnRow);
      detailPanelBody.append(overlapWrap);
    }

    detailPanelBody.append(element("p", "", check.explanation));

    if (feedback) {
      const fbBox = element("div", "evidence-observation");
      fbBox.append(element("strong", "", "Nhận xét chi tiết"));
      fbBox.append(element("p", "", feedback.message));
      if (feedback.suggestion) {
        fbBox.append(element("p", "form-hint", `Gợi ý cải thiện: ${feedback.suggestion}`));
      }
      detailPanelBody.append(fbBox);
    }

    if (check.unresolved_reason) {
      detailPanelBody.append(element("p", "evidence-observation", `Chưa đủ căn cứ: ${check.unresolved_reason}`));
    }

    const observations = (check.evidence || []).filter((item) => item.observation);
    if (observations.length) {
      for (const obs of observations) {
        const obsEl = element("p", "evidence-observation");
        obsEl.append(element("strong", "", "Quan sát trên toàn bài trả lời: "));
        obsEl.append(document.createTextNode(obs.observation));
        detailPanelBody.append(obsEl);
      }
    }

    const checkInvalidQuotes = parsedHighlights.invalidQuotes.filter((q) => q.check.criterion_id === check.criterion_id);
    if (checkInvalidQuotes.length) {
      const warn = element("p", "alert alert--error", "Phát hiện đoạn trích có offset không khớp với bài gốc; không tô sáng tự động để tránh sai lệch.");
      detailPanelBody.append(warn);
    }

    const criterionBadge = element("p", "form-hint", `Tiêu chí đang đối chiếu: ${check.criterion_label}`);
    detailPanelBody.append(criterionBadge);
  }

  function renderEvidence(check, { scrollToHighlight = false, activeSegmentEntries = null } = {}) {
    detail.replaceChildren();
    explanation.textContent = check.explanation;
    const checks = evaluation.criterion_checks || [];
    const checkIndex = checks.findIndex((item) => item.criterion_id === check.criterion_id);

    if (evidencePanelTitle) {
      evidencePanelTitle.textContent = `Căn cứ đánh giá trong bài làm: Tiêu chí ${checkIndex + 1}`;
    }
    if (evidencePanelSubtitle) {
      evidencePanelSubtitle.textContent = check.criterion_label;
    }
    if (evidencePanelIndexBadge) {
      evidencePanelIndexBadge.textContent = `Tiêu chí ${checkIndex + 1} / ${checks.length}`;
    }
    if (evidencePanelScoreBadge) {
      evidencePanelScoreBadge.className = `badge ${badgeClassForStatus(check.status)}`;
      const scoreText = check.score === null || check.score === undefined
        ? "Chưa xác định"
        : `${check.score} / ${check.max_score} điểm`;
      evidencePanelScoreBadge.textContent = `${scoreText} • ${statusLabels[check.status] || check.status}`;
    }

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

    renderAnswerWithHighlights(evaluation.answer_text, quotes, {
      scrollToHighlight,
      selectedCriterion: check.criterion_id,
    });
    renderDetailFeedbackPanel(check, activeSegmentEntries);
  }

  function renderAnswerWithHighlights(text, _selectedQuotes, { scrollToHighlight = false, selectedCriterion = selectedCriterionId } = {}) {
    answerSource.replaceChildren();
    const points = Array.from(text);
    const allRanges = parsedHighlights.validRanges;
    const segments = splitIntoAtomicSegments(points.length, allRanges);

    let scrolled = false;
    for (const seg of segments) {
      const sliceText = points.slice(seg.start, seg.end).join("");
      if (!seg.entries.length) {
        answerSource.append(document.createTextNode(sliceText));
        continue;
      }

      const visualStatus = segmentVisualStatus(seg.entries);
      const isSelectedCriterion = seg.entries.some((e) => e.criterionId === selectedCriterion);
      const classes = [`snippet-mark--${visualStatus}`];
      if (isSelectedCriterion) classes.push("evidence-mark--active");

      const mark = element("mark", classes.join(" "), sliceText);
      mark.setAttribute("tabindex", "0");
      mark.setAttribute("role", "button");
      mark.setAttribute(
        "aria-label",
        `Đoạn trích cho ${seg.entries.map((e) => e.check.criterion_label).join(", ")}`
      );

      const activateSegment = () => {
        const preferred = seg.entries.find((e) => e.criterionId === selectedCriterion) || seg.entries[0];
        selectCriterionById(preferred.criterionId, {
          scrollToHighlight: false,
          activeSegmentEntries: seg.entries,
        });
      };

      mark.addEventListener("click", activateSegment);
      mark.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activateSegment();
        }
      });

      answerSource.append(mark);
      if (scrollToHighlight && isSelectedCriterion && !scrolled && typeof mark.scrollIntoView === "function") {
        mark.scrollIntoView({ block: "nearest" });
        scrolled = true;
      }
    }
  }

  function selectCriterionById(criterionId, { scrollToHighlight = false, activeSegmentEntries = null } = {}) {
    selectedCriterionId = criterionId;
    const checks = evaluation ? (evaluation.criterion_checks || []) : [];
    const targetCheck = checks.find((c) => c.criterion_id === criterionId);
    if (!targetCheck) return;

    const buttons = criteriaList.querySelectorAll(".criterion-button");
    for (const btn of buttons) {
      const isActive = btn.getAttribute("data-criterion-id") === criterionId;
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    }

    if (typeof criteriaList.querySelectorAll === "function") {
      const cards = criteriaList.querySelectorAll(".criterion-card");
      for (const card of cards) {
        const btn = typeof card.querySelectorAll === "function"
          ? card.querySelectorAll(".criterion-button")[0]
          : null;
        const isActive = btn && btn.getAttribute("data-criterion-id") === criterionId;
        if (card.classList) {
          card.classList.toggle("criterion-card--selected", Boolean(isActive));
        }
      }
    }

    renderEvidence(targetCheck, { scrollToHighlight, activeSegmentEntries });
  }

  function stopReviewPolling() {
    if (reviewRefreshTimer !== null) window.clearTimeout(reviewRefreshTimer);
    reviewRefreshTimer = null;
    pollingStartedAt = 0;
  }

  function pollSavedResult() {
    if (typeof window.setTimeout !== "function" || reviewRefreshTimer !== null) return;
    if (!pollingStartedAt) pollingStartedAt = Date.now();
    if (Date.now() - pollingStartedAt >= 150000) {
      stopReviewPolling();
      activity?.stop();
      statusBox.textContent = "Lượt đối chiếu mất nhiều thời gian hơn dự kiến. Bài gốc vẫn được lưu; bạn có thể tải lại kết quả.";
      statusBox.hidden = false;
      retryButton.hidden = false;
      return;
    }
    reviewRefreshTimer = window.setTimeout(() => {
      reviewRefreshTimer = null;
      loadEvaluation();
    }, 5000);
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

  function renderScoreOverview(data) {
    const checks = data.criterion_checks || [];
    const hasUnresolved = checks.some((check) => check.status === "insufficient_evidence");
    const hasNumericTotal = !(data.total_score === null || data.total_score === undefined) && Number(data.maximum_score) > 0;

    if (data.total_score === null || data.total_score === undefined) {
      total.textContent = data.status === "completed" && hasUnresolved
        ? "Chưa tính tổng điểm (còn tiêu chí chưa đủ bằng chứng)"
        : "Chưa có điểm vì đánh giá chưa hoàn tất";
    } else {
      total.textContent = `${data.total_score} / ${data.maximum_score}`;
    }

    if (data.status === "completed" && hasUnresolved) {
      evaluationState.textContent = "Chưa đủ bằng chứng";
      evaluationState.className = "badge badge--unresolved";
    } else if (data.status === "completed") {
      evaluationState.textContent = "Đã đánh giá";
      evaluationState.className = "badge badge--met";
    } else {
      evaluationState.textContent = "Chưa hoàn tất đánh giá";
      evaluationState.className = "badge badge--unresolved";
    }

    if (scoreDonutArc) {
      if (hasNumericTotal) {
        const pct = Math.max(0, Math.min(100, Math.round((data.total_score / data.maximum_score) * 100)));
        scoreDonutArc.setAttribute("stroke-dasharray", `${pct}, 100`);
        scoreDonutArc.setAttribute(
          "class",
          "score-donut-arc"
        );
        if (scorePercentLabel) scorePercentLabel.textContent = `Tỷ lệ theo thang điểm: ${pct}%`;
      } else {
        scoreDonutArc.setAttribute("stroke-dasharray", "0, 100");
        scoreDonutArc.setAttribute("class", "score-donut-arc score-donut-arc--neutral");
        if (scorePercentLabel) scorePercentLabel.textContent = "Chưa tính tỷ lệ do thiếu căn cứ";
      }
    }

    if (scoreBarsList) {
      scoreBarsList.replaceChildren();
      for (const check of checks) {
        const row = element("div");
        const head = element("div", "score-bar-item__head");
        head.append(element("span", "", check.criterion_label));
        let barPct = 0;
        let valueLabel = "Chưa xác định";
        if (!(check.score === null || check.score === undefined) && check.max_score > 0) {
          barPct = Math.max(0, Math.min(100, Math.round((check.score / check.max_score) * 100)));
          valueLabel = `${check.score}/${check.max_score}`;
        }
        head.append(element("span", "", valueLabel));

        const track = element("div", "score-bar-track");
        const fill = element(
          "div",
          `score-bar-fill score-bar-fill--${check.status === "met" ? "met" : check.status === "unmet" ? "unmet" : "unresolved"}`
        );
        if (fill.style) fill.style.width = `${barPct}%`;
        track.append(fill);
        row.append(head, track);
        scoreBarsList.append(row);
      }
    }

    if (assessorSummaryText) {
      const metCount = checks.filter((c) => c.status === "met").length;
      const unmetCount = checks.filter((c) => c.status === "unmet").length;
      const unresolvedCount = checks.filter((c) => c.status === "insufficient_evidence").length;
      assessorSummaryText.textContent = `Đạt ${metCount}/${checks.length} tiêu chí, chưa đạt ${unmetCount}, chưa đủ bằng chứng ${unresolvedCount}. Chọn từng tiêu chí để đối chiếu trích dẫn nguyên văn và gợi ý.`;
    }
  }

  function renderDetailStats(data) {
    const checks = data.criterion_checks || [];
    parsedHighlights = collectValidEvidenceRanges(data.answer_text, checks);

    const uniqueByStatus = { met: new Set(), unmet: new Set(), other: new Set() };
    for (const r of parsedHighlights.validRanges) {
      const key = `${r.start}:${r.end}:${r.quote}`;
      if (r.status === "met") uniqueByStatus.met.add(key);
      else if (r.status === "unmet") uniqueByStatus.unmet.add(key);
      else uniqueByStatus.other.add(key);
    }

    if (tabCriteriaCount) tabCriteriaCount.textContent = `${checks.length} tiêu chí`;
    if (criteriaCountPill) criteriaCountPill.textContent = `${checks.length} tiêu chí`;
    if (tabQuotesCount) tabQuotesCount.textContent = `${parsedHighlights.uniqueQuoteCount} đoạn trích`;
    if (detailMetBadge) detailMetBadge.textContent = `Đạt chuẩn (${uniqueByStatus.met.size} đoạn)`;
    if (detailUnmetBadge) detailUnmetBadge.textContent = `Chưa đạt (${uniqueByStatus.unmet.size} đoạn)`;
    if (detailUnresolvedBadge) {
      detailUnresolvedBadge.hidden = uniqueByStatus.other.size === 0;
      detailUnresolvedBadge.textContent = `Chưa đủ căn cứ (${uniqueByStatus.other.size} đoạn)`;
    }
    if (detailAnswerMeta) {
      const words = countWords(data.answer_text);
      detailAnswerMeta.textContent = `${words.toLocaleString("vi-VN")} từ (đếm trên bài đã lưu)`;
    }
    if (jumpPrimaryUnmetBtn) {
      const hasUnmet = checks.some((c) => c.status === "unmet");
      jumpPrimaryUnmetBtn.hidden = !hasUnmet;
    }
  }

  function renderEvaluation(response) {
    const data = response && response.result;
    if (!data) throw new Error("Máy chủ trả thiếu kết quả đánh giá theo DTO.");
    evaluation = data;
    if (questionPrompt) questionPrompt.textContent = data.question_prompt || "";
    if (questionCode) {
      questionCode.textContent = data.question_code || "";
      questionCode.hidden = !data.question_code;
    }
    feedbackItems = response.feedback_items || [];
    criteriaList.replaceChildren();
    answerSource.textContent = data.answer_text;

    if (data.status === "failed") {
      stopReviewPolling();
      activity?.stop();
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
      activity?.start({ kind: "assessment", title: "AI đang đối chiếu bài làm", description: "Câu trả lời gốc đã lưu. Kết quả sẽ tự cập nhật khi đối chiếu hoàn tất." });
      content.hidden = true;
      if (nextButton) nextButton.hidden = true;
      errorBox.hidden = true;
      if (retryEvalButton) retryEvalButton.hidden = true;
      statusBox.textContent = "Bài trả lời đã lưu và đang được AI đối chiếu rubric. Kết quả sẽ tự cập nhật; bạn cũng có thể tải lại.";
      statusBox.hidden = false;
      retryButton.hidden = false;
      pollSavedResult();
      return;
    }

    stopReviewPolling();
    activity?.stop();
    renderScoreOverview(data);
    renderDetailStats(data);

    let firstSelection = null;
    const checks = data.criterion_checks || [];
    checks.forEach((check, idx) => {
      const card = element("article", "criterion-card");
      const button = element("button", "criterion-button");
      button.type = "button";
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("data-criterion-id", check.criterion_id);
      const title = element("span", "criterion-button__title", `${idx + 1}. ${check.criterion_label}`);
      const status = element(
        "span",
        `badge ${badgeClassForStatus(check.status)}`,
        statusLabels[check.status] || "Chưa có trạng thái"
      );
      button.append(title, status);
      const score = check.score === null || check.score === undefined
        ? (check.status === "insufficient_evidence" ? "Chưa xác định" : "Chưa có điểm")
        : `${check.score} / ${check.max_score} điểm`;
      const metaRow = element("div", "criterion-card__meta");
      metaRow.append(element("span", "form-hint", score));
      metaRow.append(element("span", "form-hint", "Xem căn cứ →"));
      card.append(button, metaRow);

      button.addEventListener("click", () => {
        selectCriterionById(check.criterion_id, { scrollToHighlight: true });
      });
      if (!firstSelection) firstSelection = check;
      criteriaList.append(card);
    });

    content.hidden = false;
    window.InterviewActivity?.reveal(content);
    statusBox.hidden = true;
    errorBox.hidden = true;
    retryButton.hidden = true;
    if (retryEvalButton) retryEvalButton.hidden = true;
    if (nextButton && data.status === "completed" && answerId === page.dataset.currentAnswerId
        && answerRevision === Number(page.dataset.currentAnswerRevision)) {
      nextButton.hidden = false;
    }
    if (firstSelection) {
      selectCriterionById(firstSelection.criterion_id, { scrollToHighlight: false });
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
      if (!info.available || !info.eligible_now) {
        replaySection.hidden = true;
        return;
      }
      replaySection.hidden = false;
      if (replaySummary) {
        const title = info.question_title || "Tình huống kỹ thuật";
        replaySummary.textContent = `${title}: mở phòng thí nghiệm rẽ nhánh thử phương án khác từ bài làm gốc để đối chiếu kết cục (không thay đổi điểm đã công bố).`;
      }
      if (replayForm) {
        replayForm.action = `/sessions/${encodeURIComponent(sessionId)}/answers/${encodeURIComponent(answerId)}/replay/start?revision=${encodeURIComponent(String(answerRevision))}`;
      }
      if (replayButton) {
        replayButton.textContent = info.existing_run_id
          ? "Tiếp tục khám phá cây Decision Replay"
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
        const probeStatusLabels = {
          met: "Đạt",
          unmet: "Chưa đạt",
          insufficient_evidence: "Chưa đủ bằng chứng",
          evaluated: "Đã đánh giá",
          pending: "Đang chờ",
          processing: "Đang đánh giá",
          failed: "Chưa hoàn tất",
        };
        for (const item of plan.existing_probes || []) {
          const box = element("article", "probe-result-card");
          const head = element("div", "probe-result-card__head");
          head.append(element("span", "probe-result-card__title", `Tiêu chí đào sâu: ${item.criterion_label}`));
          const rawStatus = item.outcome_status || item.status || "";
          const localizedStatus = probeStatusLabels[rawStatus] || statusLabels[rawStatus] || "Đã ghi nhận";
          const statusTone = rawStatus === "met" || rawStatus === "evaluated"
            ? "badge--met"
            : rawStatus === "unmet" || rawStatus === "failed"
              ? "badge--unmet"
              : "badge--unresolved";
          head.append(element("span", `badge ${statusTone}`, localizedStatus));
          box.append(head);
          if (item.response_text) box.append(element("p", "text-secondary", `Phần làm rõ đã gửi: ${item.response_text}`));
          if (item.outcome_score !== null && item.outcome_score !== undefined) {
            box.append(element("p", "probe-result-card__score", `Điểm sau làm rõ: ${item.outcome_score} / ${item.outcome_max_score}`));
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
    stopReviewPolling();
    activity?.start({ kind: "assessment", title: "AI đang chấm lại bài đã lưu", description: "Đối chiếu lại cùng câu trả lời và phiên bản rubric; bài gốc được giữ nguyên." });
    window.InterviewActivity?.buttonBusy(retryEvalButton, true);
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
        pollSavedResult();
        statusBox.textContent = "Bài này đang được AI đánh giá. Kết quả sẽ tự cập nhật; bạn cũng có thể tải lại.";
        statusBox.hidden = false;
        if (retryEvalButton) retryEvalButton.hidden = true;
        retryButton.hidden = false;
      } else {
        activity?.stop();
        stopReviewPolling();
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
      window.InterviewActivity?.buttonBusy(retryEvalButton, false);
      retryingEvaluation = false;
    }
  }

  async function loadEvaluation() {
    if (loadingEvaluation || retryingEvaluation) return;
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
    loadingEvaluation = true;
    if (!pollingStartedAt) activity?.start({ kind: "loading", title: "Đang mở kết quả của bạn", description: "Tải đúng bài trả lời đã lưu cùng các tiêu chí và đoạn trích liên quan." });
    try {
      const response = await api.getEvaluation(sessionId, answerId, answerRevision);
      renderEvaluation(response);
    } catch (error) {
      activity?.stop();
      stopReviewPolling();
      if (error.status === 404 && page.dataset.evaluationTiming === "after_session" && nextButton
          && answerId === page.dataset.currentAnswerId
          && answerRevision === Number(page.dataset.currentAnswerRevision)) {
        statusBox.textContent = "Câu trả lời đã lưu. Điểm, căn cứ và đề xuất sẽ được tạo sau khi kết thúc phiên. Bạn có thể chuyển sang câu tiếp theo.";
        statusBox.hidden = false;
        errorBox.hidden = true;
        nextButton.hidden = false;
        retryButton.hidden = true;
        return;
      }
      statusBox.hidden = true;
      const canRetry = error.code !== "SESSION_EXPIRED" && error.code !== "SESSION_FORBIDDEN" && error.status !== 410 && error.status !== 403 && error.retryable !== false;
      errorBox.textContent = `${error.message || "Chưa tải được kết quả."} ${error.recoveryAction || "Bài trả lời gốc vẫn được giữ trên máy chủ."}`;
      errorBox.hidden = false;
      retryButton.hidden = !canRetry;
      errorBox.focus();
    } finally {
      loadingEvaluation = false;
    }
  }

  if (typeof window.addEventListener === "function") window.addEventListener("pagehide", () => { stopReviewPolling(); activity?.stop(); });
  if (tabOverviewBtn && tabDetailBtn) {
    const initialHash = window.location && window.location.hash;
    switchTab(initialHash === "#detail" ? "detail" : "overview");

    tabOverviewBtn.addEventListener("click", () => switchTab("overview"));
    tabDetailBtn.addEventListener("click", () => switchTab("detail"));

    const handleTabKeydown = (event) => {
      if (event.key === "ArrowRight" || event.key === "ArrowLeft" || event.key === "Home" || event.key === "End") {
        event.preventDefault();
        const nextTab = event.key === "End" ? "detail"
          : event.key === "Home" ? "overview"
          : (activeTab === "overview" ? "detail" : "overview");
        switchTab(nextTab);
        const focusBtn = nextTab === "overview" ? tabOverviewBtn : tabDetailBtn;
        if (typeof focusBtn.focus === "function") focusBtn.focus();
      }
    };
    tabOverviewBtn.addEventListener("keydown", handleTabKeydown);
    tabDetailBtn.addEventListener("keydown", handleTabKeydown);
  }

  if (jumpPrimaryUnmetBtn) {
    jumpPrimaryUnmetBtn.addEventListener("click", () => {
      if (!evaluation) return;
      const firstUnmet = (evaluation.criterion_checks || []).find((c) => c.status === "unmet");
      if (!firstUnmet) return;
      switchTab("detail");
      selectCriterionById(firstUnmet.criterion_id, { scrollToHighlight: true });
    });
  }

  if (copyAnswerBtn) {
    copyAnswerBtn.addEventListener("click", async () => {
      if (!evaluation || !evaluation.answer_text) return;
      try {
        if (typeof navigator !== "undefined" && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
          await navigator.clipboard.writeText(evaluation.answer_text);
        }
        if (copyAnswerLabel) copyAnswerLabel.textContent = "Đã sao chép bài gốc";
        window.setTimeout(() => {
          if (copyAnswerLabel) copyAnswerLabel.textContent = "Sao chép bài làm";
        }, 2000);
      } catch (_error) {
        if (copyAnswerLabel) copyAnswerLabel.textContent = "Không thể truy cập clipboard";
      }
    });
  }

  retryButton.addEventListener("click", loadEvaluation);
  if (retryEvalButton) retryEvalButton.addEventListener("click", retrySavedEvaluation);
  if (nextButton) {
    nextButton.addEventListener("click", async () => {
      nextButton.disabled = true;
      window.InterviewActivity?.buttonBusy(nextButton, true);
      activity?.start({ kind: "loading", title: "Đang chuyển bước", description: "Câu trả lời đã lưu. Chuẩn bị nội dung tiếp theo của phiên." });
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
        activity?.stop();
        window.InterviewActivity?.buttonBusy(nextButton, false);
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
