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
  const evalStateBadge = document.querySelector("#summary-eval-state");
  const scoreBox = document.querySelector("#session-score-box");
  const scoreValue = document.querySelector("#session-score-value");
  const scoreBreakdown = document.querySelector("#session-score-breakdown");
  const scoreNote = document.querySelector("#session-score-note");
  const coverageCount = document.querySelector("#coverage-count");
  const unanswered = document.querySelector("#unanswered-categories");
  const unresolved = document.querySelector("#unresolved-categories");
  const outcomesList = document.querySelector("#outcomes-list");
  const outcomesEmpty = document.querySelector("#outcomes-empty");
  const gapsList = document.querySelector("#gaps-list");
  const gapsEmpty = document.querySelector("#gaps-empty");
  let pollTimer = null;

  const categoryNames = {
    programming_knowledge: "Kiến thức lập trình",
    technical_case: "Tình huống kỹ thuật",
    algorithm_explanation: "Giải thích thuật toán",
    ai_code_review: "Đánh giá mã nguồn",
  };
  const stateNames = {
    completed: "Đã nộp đủ bài",
    ended_early: "Đã kết thúc sớm",
    in_progress: "Đang thực hiện",
    expired: "Đã hết hạn",
  };
  const evaluationNames = {
    completed: "Đã chấm xong",
    pending: "Đang chờ AI chấm",
    processing: "Đang chấm AI",
    failed: "Chấm điểm thất bại",
  };

  function node(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  }

  function applyInlineCode(el) {
    const shell = window.interviewUSShell;
    if (el && shell && typeof shell.formatInlineCode === "function") {
      shell.formatInlineCode(el);
    }
  }

  function formatIndex(index) {
    const value = index + 1;
    return value < 10 ? `0${value}` : String(value);
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

  function renderOutcome(outcome, criterionLabels, detail, openKeys, index) {
    const item = node("li", "outcome-card");
    const baseKey = outcome.answer_ref
      ? `${outcome.answer_ref.id}:${outcome.answer_ref.revision}`
      : `${outcome.question_ref.id}:${outcome.question_ref.version}`;

    const meta = node("div", "outcome-meta");
    meta.append(node("span", "criterion-index", formatIndex(index)));
    meta.append(node("span", "badge badge--neutral", categoryNames[outcome.category] || outcome.category));
    const evalBadgeClass = outcome.evaluation_status === "completed"
      ? "badge badge--met"
      : outcome.evaluation_status === "failed"
        ? "badge badge--error"
        : "badge badge--unresolved";
    meta.append(node("span", evalBadgeClass, evaluationNames[outcome.evaluation_status] || "Chưa có trạng thái đánh giá"));

    let scoreText;
    let scorePillText = null;
    let scorePillClass = "badge";
    if (outcome.total_score === null || outcome.total_score === undefined) {
      scoreText = outcome.evaluation_status === "completed" && outcome.unresolved_criteria_count > 0
        ? "Chưa tính tổng điểm (còn tiêu chí chưa đủ bằng chứng)."
        : outcome.evaluation_status === "completed"
          ? "Chưa có điểm tổng hợp trong dữ liệu phiên."
          : "Chưa có điểm vì câu trả lời chưa có kết quả đánh giá.";
      if (outcome.evaluation_status === "completed" && outcome.unresolved_criteria_count > 0) {
        scorePillText = `${outcome.unresolved_criteria_count} tiêu chí chưa đủ căn cứ`;
        scorePillClass = "badge badge--unresolved";
      }
    } else {
      scoreText = `Điểm câu này: ${outcome.total_score} / ${outcome.maximum_score}`;
      scorePillText = `${outcome.total_score} / ${outcome.maximum_score} điểm`;
      scorePillClass = outcome.total_score >= outcome.maximum_score ? "badge badge--met" : "badge badge--unmet";
    }
    if (scorePillText) {
      meta.append(node("span", scorePillClass, scorePillText));
    }
    item.append(meta);

    const heading = node("h3", "outcome-card__prompt", outcome.question_prompt || categoryNames[outcome.category] || outcome.category);
    applyInlineCode(heading);
    item.append(heading);
    item.append(node("p", "outcome-card__score", scoreText));

    if (outcome.evaluation_status === "failed") {
      item.append(node("p", "outcome-card__error", outcome.failure_message || "Chưa thể hoàn tất đánh giá. Câu trả lời vẫn được lưu."));
    }
    if (outcome.unresolved_criteria_count > 0) {
      item.append(node("p", "form-hint", `${outcome.unresolved_criteria_count} tiêu chí chưa đủ bằng chứng (không quy đổi thành 0 điểm).`));
    }
    if (outcome.confirmed_gap_criterion_ids && outcome.confirmed_gap_criterion_ids.length) {
      const gapNames = outcome.confirmed_gap_criterion_ids.map(
        (criterionId) => criterionLabels.get(criterionId) || criterionId
      );
      item.append(node("p", "outcome-card__gaps", `Điểm thiếu đã xác nhận: ${gapNames.join(", ")}`));
    }

    if (detail && detail.findings && detail.findings.length) {
      const findingsDetails = node("details", "outcome-disclosure");
      const findingsKey = `findings:${baseKey}`;
      findingsDetails.dataset.answerKey = findingsKey;
      if (openKeys && openKeys.has(findingsKey)) findingsDetails.open = true;
      const metCount = detail.findings.filter((f) => f.status === "met").length;
      findingsDetails.append(node("summary", "", `Xem chi tiết ${detail.findings.length} tiêu chí (${metCount} đạt)`));
      const findings = node("ul", "outcome-findings");
      for (const finding of detail.findings) {
        const label = finding.status === "met" ? "Đạt" : finding.status === "unmet" ? "Cần cải thiện" : "Chưa đủ căn cứ";
        const evidence = (finding.evidence || []).map((ev) => ev.quote || ev.observation).filter(Boolean);
        const li = node("li", "outcome-finding-item");
        const statusClass = finding.status === "met" ? "badge badge--met" : finding.status === "unmet" ? "badge badge--unmet" : "badge badge--unresolved";
        const headerRow = node("div", "outcome-finding-item__header");
        headerRow.append(node("strong", "", finding.criterion_label));
        headerRow.append(node("span", statusClass, label));
        li.append(headerRow);
        const explanationEl = node("p", "outcome-finding-item__explanation", finding.explanation);
        applyInlineCode(explanationEl);
        li.append(explanationEl);
        if (evidence.length) {
          li.append(node("p", "form-hint outcome-finding-item__quote", `Căn cứ: ${evidence.join("; ")}`));
        }
        findings.append(li);
      }
      findingsDetails.append(findings);
      item.append(findingsDetails);
    }

    if (outcome.question_code) {
      const codeDetails = node("details", "outcome-disclosure");
      const codeKey = `code:${baseKey}`;
      codeDetails.dataset.answerKey = codeKey;
      if (openKeys && openKeys.has(codeKey)) codeDetails.open = true;
      codeDetails.append(node("summary", "", "Xem đoạn mã trong đề bài"));
      codeDetails.append(node("pre", "code-block", outcome.question_code));
      item.append(codeDetails);
    }

    if (outcome.answer_text !== null && outcome.answer_text !== undefined) {
      const details = node("details", "outcome-disclosure");
      const answerKey = outcome.answer_ref ? `${outcome.answer_ref.id}:${outcome.answer_ref.revision}` : "";
      if (answerKey) {
        details.dataset.answerKey = answerKey;
        if (openKeys && openKeys.has(answerKey)) details.open = true;
      }
      details.append(node("summary", "", "Xem câu trả lời đã lưu"));
      details.append(node("pre", "answer-source", outcome.answer_text));
      item.append(details);
    }

    const actions = node("div", "action-row");
    if (outcome.evaluation_status === "failed" && outcome.retryable && outcome.answer_ref) {
      const retry = node("button", "btn btn--secondary", "Thử đánh giá lại");
      retry.type = "button";
      retry.addEventListener("click", async () => {
        retry.disabled = true;
        try {
          await api.evaluateAnswer(sessionId, outcome.answer_ref.id, outcome.answer_ref.revision);
          await loadSummary(true);
        } catch (error) {
          errorBox.textContent = `${error.message || "Chưa thể đánh giá lại."} Bài trả lời vẫn được lưu.`;
          errorBox.hidden = false;
          retry.disabled = false;
        }
      });
      actions.append(retry);
    }
    if (outcome.answer_ref && outcome.answer_ref.id) {
      const review = node("a", "btn btn--secondary", "Xem căn cứ và tiêu chí");
      const reviewUrl = new URL(`/sessions/${encodeURIComponent(sessionId)}/review`, window.location.origin);
      reviewUrl.searchParams.set("answer_id", outcome.answer_ref.id);
      reviewUrl.searchParams.set("revision", String(outcome.answer_ref.revision));
      review.href = reviewUrl.toString();
      actions.append(review);
    }
    if (outcome.category === "technical_case" && outcome.evaluation_status === "completed" && outcome.answer_ref && outcome.answer_ref.id) {
      const replayForm = node("form", "");
      replayForm.method = "post";
      replayForm.action = `/sessions/${encodeURIComponent(sessionId)}/answers/${encodeURIComponent(outcome.answer_ref.id)}/replay/start?revision=${encodeURIComponent(String(outcome.answer_ref.revision))}`;
      const replayBtn = node("button", "btn btn--highlight", "Tua lại Decision Replay");
      replayBtn.type = "submit";
      replayForm.append(replayBtn);
      actions.append(replayForm);
    }
    if (outcome.confirmed_gap_criterion_ids && outcome.confirmed_gap_criterion_ids.length) {
      const exercise = node("a", "btn btn--secondary", "Bài luyện liên quan");
      exercise.href = `/sessions/${encodeURIComponent(sessionId)}/exercises?skill_id=${encodeURIComponent(outcome.skill_id || "")}`;
      actions.append(exercise);
    }
    if (actions.childElementCount) item.append(actions);
    return item;
  }

  function renderGap(gap, index) {
    const item = node("li", "gap-card");
    const head = node("div", "gap-card__head");
    head.append(node("span", "criterion-index", formatIndex(index)));
    if (gap.skill_label) head.append(node("span", "badge badge--unmet", gap.skill_label));
    item.append(head);
    item.append(node("h3", "", gap.criterion_label || gap.skill_label || "Điểm cần luyện"));
    if (gap.skill_label) item.append(node("p", "text-secondary", `Kỹ năng: ${gap.skill_label}`));
    const reasonEl = node("p", "", gap.reason || "Chưa có mô tả chi tiết cho điểm thiếu này.");
    applyInlineCode(reasonEl);
    item.append(reasonEl);
    const link = node("a", "btn btn--secondary", "Tìm bài tập cho kỹ năng này");
    link.href = `/sessions/${encodeURIComponent(sessionId)}/exercises?skill_id=${encodeURIComponent(gap.skill_id || "")}`;
    item.append(link);
    return item;
  }

  function renderReplayBanner(data) {
    const banner = document.querySelector("#summary-replay-banner");
    const textEl = document.querySelector("#summary-replay-text");
    const actionsEl = document.querySelector("#summary-replay-actions");
    if (!banner || !textEl || !actionsEl) return;
    const caseOutcome = (data.outcomes || []).find((item) => item.category === "technical_case");
    if (!caseOutcome) {
      banner.hidden = true;
      return;
    }
    banner.hidden = false;
    actionsEl.replaceChildren();
    const totalQ = Number(data.total_question_count || 0);
    const answeredQ = (data.outcomes || []).filter((item) => item.answer_ref && item.answer_ref.id).length;
    const sessionFullyAnswered = totalQ > 0 && answeredQ >= totalQ;

    if (!sessionFullyAnswered) {
      textEl.textContent = `Cần hoàn tất đủ ${totalQ}/${totalQ} câu của phiên (hiện mới nộp ${answeredQ}/${totalQ}) để mở Decision Replay cho câu Tình huống kỹ thuật.`;
      return;
    }
    if (!caseOutcome.answer_ref || !caseOutcome.answer_ref.id) {
      textEl.textContent = "Chưa có bài trả lời đã lưu cho câu Tình huống kỹ thuật.";
      return;
    }
    if (caseOutcome.evaluation_status === "pending" || caseOutcome.evaluation_status === "processing") {
      textEl.textContent = "Câu Tình huống kỹ thuật đang được AI đối chiếu rubric. Nút mở Decision Replay sẽ kích hoạt ngay sau khi chấm xong.";
      return;
    }
    if (caseOutcome.evaluation_status === "failed") {
      textEl.textContent = "Câu Tình huống kỹ thuật chưa chấm xong do lỗi tạm thời. Hãy bấm 'Thử đánh giá lại' ở thẻ câu bên dưới trước khi mở Decision Replay.";
      return;
    }
    textEl.textContent = "Xem mô phỏng từng bước từ chính bài làm gốc, tua lại rẽ nhánh thử giải pháp khác và đối chiếu bất biến (không làm thay đổi điểm phiên thi).";
    const form = node("form", "");
    form.method = "post";
    form.action = `/sessions/${encodeURIComponent(sessionId)}/answers/${encodeURIComponent(caseOutcome.answer_ref.id)}/replay/start?revision=${encodeURIComponent(String(caseOutcome.answer_ref.revision))}`;
    const btn = node("button", "btn btn--primary", "Mở Decision Replay từ bài làm");
    btn.type = "submit";
    form.append(btn);
    actionsEl.append(form);
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
    const outcomes = data.outcomes || [];
    const hasInFlight = outcomes.some(
      (item) => item.evaluation_status === "pending" || item.evaluation_status === "processing"
    ) || Boolean(report && report.status === "assessing");
    const hasFailed = outcomes.some((item) => item.evaluation_status === "failed")
      || Boolean(report && report.status === "partial_failure");
    if (evalStateBadge) {
      if (hasInFlight) {
        evalStateBadge.className = "badge badge--unresolved";
        evalStateBadge.textContent = `Đang chấm AI (${data.completed_question_count}/${data.total_question_count} câu)`;
      } else if (hasFailed) {
        evalStateBadge.className = "badge badge--error";
        evalStateBadge.textContent = `Có câu chấm lỗi (${data.completed_question_count}/${data.total_question_count} câu)`;
      } else if (data.completed_question_count >= data.total_question_count) {
        evalStateBadge.className = "badge badge--met";
        evalStateBadge.textContent = `Đã chấm xong (${data.completed_question_count}/${data.total_question_count} câu)`;
      } else {
        evalStateBadge.className = "badge badge--neutral";
        evalStateBadge.textContent = `Đã chấm ${data.completed_question_count}/${data.total_question_count} câu`;
      }
    }
    coverageCount.textContent = `Có kết quả ${data.completed_question_count} / ${data.total_question_count} câu`;
    if (scoreBox && scoreValue && scoreNote) {
      const hasTotal = data.scored_points_total !== null
        && data.scored_points_total !== undefined
        && data.scored_points_maximum !== null
        && data.scored_points_maximum !== undefined;
      if (scoreBreakdown) {
        scoreBreakdown.replaceChildren();
        scoreBreakdown.hidden = true;
      }
      if (hasTotal) {
        scoreBox.className = "session-score-box";
        scoreBox.hidden = false;
        scoreValue.textContent = `${data.scored_points_total} / ${data.scored_points_maximum} điểm`;
        scoreNote.textContent = `Tổng điểm ${data.completed_question_count}/${data.total_question_count} câu đã chấm đủ căn cứ trong phiên này (không thay đánh giá năng lực tổng thể).`;
      } else if (outcomes.length > 0) {
        const scoredOutcomes = outcomes.filter((item) => item.total_score !== null && item.total_score !== undefined);
        const scoredSum = scoredOutcomes.reduce((acc, item) => acc + Number(item.total_score), 0);
        const scoredMax = scoredOutcomes.reduce((acc, item) => acc + Number(item.maximum_score || 0), 0);
        const unresolvedQuestionCount = outcomes.filter(
          (item) => item.evaluation_status === "completed" && item.unresolved_criteria_count > 0
        ).length;
        const failedQuestionCount = outcomes.filter((item) => item.evaluation_status === "failed").length;
        const pendingQuestionCount = outcomes.filter(
          (item) => item.evaluation_status === "pending" || item.evaluation_status === "processing"
        ).length;

        scoreBox.className = "session-score-box session-score-box--partial";
        scoreBox.hidden = false;
        scoreValue.textContent = "Chưa cộng tổng điểm";
        if (scoreBreakdown && (scoredOutcomes.length > 0 || unresolvedQuestionCount > 0 || failedQuestionCount > 0 || pendingQuestionCount > 0)) {
          if (scoredOutcomes.length > 0) {
            scoreBreakdown.append(
              node("span", "badge badge--met", `Đã có điểm: ${scoredOutcomes.length}/${outcomes.length} câu (${scoredSum}/${scoredMax})`)
            );
          }
          if (unresolvedQuestionCount > 0) {
            scoreBreakdown.append(
              node("span", "badge badge--unresolved", `${unresolvedQuestionCount} câu chưa đủ căn cứ`)
            );
          }
          if (failedQuestionCount > 0) {
            scoreBreakdown.append(
              node("span", "badge badge--error", `${failedQuestionCount} câu chấm lỗi`)
            );
          }
          if (pendingQuestionCount > 0) {
            scoreBreakdown.append(
              node("span", "badge badge--unresolved", `${pendingQuestionCount} câu đang chấm`)
            );
          }
          scoreBreakdown.hidden = false;
        }
        if (hasInFlight) {
          scoreNote.textContent = "Đang chờ AI chấm hoàn tất các câu đã nộp.";
        } else if (unresolvedQuestionCount > 0 && scoredOutcomes.length > 0) {
          scoreNote.textContent = `${scoredOutcomes.length} câu đã chấm đủ căn cứ (${scoredSum}/${scoredMax} điểm); ${unresolvedQuestionCount} câu còn tiêu chí chưa đủ căn cứ nên không quy đổi thành 0 điểm để cộng tổng.`;
        } else {
          scoreNote.textContent = "Còn câu chưa hoàn tất, lỗi chấm hoặc chưa đủ căn cứ (không quy đổi thành 0 điểm).";
        }
      } else {
        scoreBox.hidden = true;
      }
    }
    appendValues(unanswered, data.unanswered_categories);
    appendValues(unresolved, data.unresolved_categories);
    const overviewHost = document.querySelector(".coverage-card");
    if (overviewHost) {
      const previous = overviewHost.querySelector("[data-report-overview]");
      if (previous) previous.remove();
      if (report && report.overview) {
        const section = node("div", "overview-breakdown");
        section.dataset.reportOverview = "";
        section.append(node("p", "text-secondary", report.overview.scope_note));
        const axes = node("ul", "overview-axes");
        for (const axis of report.overview.axes || []) {
          axes.append(node("li", "", `${axis.label}: ${axis.observed_count ? `${axis.met_count} tiêu chí đạt, ${axis.gap_count} cần cải thiện, ${axis.unresolved_count} chưa đủ căn cứ` : "chưa được quan sát"}.`));
        }
        section.append(axes);
        const strengths = report.overview.strengths || [];
        if (strengths.length > 2) {
          const strengthDetails = node("details", "outcome-disclosure");
          strengthDetails.append(node("summary", "", `Điểm mạnh có căn cứ (${strengths.length} tiêu chí đạt)`));
          const strengthList = node("ul", "overview-strength-list");
          for (const s of strengths) {
            const strengthItem = node("li", "", `${s.criterion_label}: ${s.explanation}`);
            applyInlineCode(strengthItem);
            strengthList.append(strengthItem);
          }
          strengthDetails.append(strengthList);
          section.append(strengthDetails);
        } else {
          section.append(node("h3", "", "Điểm mạnh có căn cứ"));
          const strengthText = node("p", "", strengths.length
            ? strengths.map((item) => `${item.criterion_label}: ${item.explanation}`).join("; ")
            : "Chưa đủ kết quả để xác nhận điểm mạnh.");
          applyInlineCode(strengthText);
          section.append(strengthText);
        }
        overviewHost.append(section);
      }
    }

    const openAnswerIds = new Set();
    const walkOpenDetails = (root) => {
      for (const child of (root && root.children) || []) {
        if ((child.tagName === "DETAILS" || child.tag === "details") && child.open && child.dataset && child.dataset.answerKey) {
          openAnswerIds.add(child.dataset.answerKey);
        }
        walkOpenDetails(child);
      }
    };
    walkOpenDetails(outcomesList);

    const criterionLabels = buildCriterionLabelMap(data.observed_gaps);
    renderReplayBanner(data);
    outcomesList.replaceChildren();
    const outcomeItems = data.outcomes || [];
    for (let index = 0; index < outcomeItems.length; index += 1) {
      const outcome = outcomeItems[index];
      const detail = (report && report.details || []).find((item) =>
        item.question_ref.id === outcome.question_ref.id && item.question_ref.version === outcome.question_ref.version);
      outcomesList.append(renderOutcome(outcome, criterionLabels, detail, openAnswerIds, index));
    }
    outcomesEmpty.hidden = Boolean(outcomeItems.length);

    gapsList.replaceChildren();
    if (report && report.proposals) {
      for (let index = 0; index < report.proposals.length; index += 1) {
        const proposal = report.proposals[index];
        const item = node("li", "gap-card");
        const head = node("div", "gap-card__head");
        head.append(node("span", "criterion-index", formatIndex(index)));
        head.append(node("span", "badge badge--unmet", `Ưu tiên ${proposal.priority}`));
        item.append(head);
        item.append(node("h3", "", `Ưu tiên ${proposal.priority}: ${proposal.finding.criterion_label}`));
        const findingEl = node("p", "", `Căn cứ: ${proposal.finding.explanation}`);
        applyInlineCode(findingEl);
        item.append(findingEl);
        item.append(node("p", "text-secondary", proposal.priority_reason));
        item.append(node("p", "", `Mục tiêu: ${proposal.goal}`));
        item.append(node("p", "", proposal.exercise_titles.length
          ? `Bài luyện theo thứ tự: ${proposal.exercise_titles.join(" → ")}${proposal.estimated_minutes ? ` (ước tính ${proposal.estimated_minutes} phút)` : ""}.`
          : proposal.note));
        if (proposal.exercise_titles.length) item.append(node("p", "form-hint", proposal.note));
        const link = node("a", "btn btn--secondary", "Xem bài luyện phù hợp");
        link.href = `/sessions/${encodeURIComponent(sessionId)}/exercises`;
        item.append(link);
        gapsList.append(item);
      }
    } else {
      const gapItems = data.observed_gaps || [];
      for (let index = 0; index < gapItems.length; index += 1) {
        gapsList.append(renderGap(gapItems[index], index));
      }
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

  async function loadSummary(background = false) {
    window.clearTimeout(pollTimer);
    if (!background) {
      statusBox.hidden = false;
      statusBox.textContent = "Đang tải kết quả và độ phủ phiên…";
      content.hidden = true;
    }
    errorBox.hidden = true;
    try {
      const payload = await api.getSessionSummary(sessionId);
      renderSummary(payload);
      if (payload.state !== "expired" && (payload.outcomes || []).some(
        (item) => item.evaluation_status === "pending" || item.evaluation_status === "processing"
      )) {
        pollTimer = window.setTimeout(() => loadSummary(true), 5000);
      }
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
        retry.addEventListener("click", () => loadSummary());
        errorBox.replaceChildren(document.createTextNode(`${message} `), retry);
      }
      if (background) pollTimer = window.setTimeout(() => loadSummary(true), 10000);
      else errorBox.focus();
    }
  }

  loadSummary();
})();
