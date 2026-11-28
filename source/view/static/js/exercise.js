(() => {
  "use strict";

  const page = document.querySelector("[data-exercise-page]");
  if (!page) return;
  const api = window.InterviewApi;
  const sessionId = page.dataset.sessionId;
  const exerciseId = page.dataset.exerciseId;
  const skillId = page.dataset.skillId;
  const statusBox = document.querySelector("#exercise-status");
  const errorBox = document.querySelector("#exercise-error");
  const content = document.querySelector("#exercise-content");
  const message = document.querySelector("#exercise-message");
  const list = document.querySelector("#exercise-list");
  const empty = document.querySelector("#exercise-empty");
  const emptyReason = document.querySelector("#exercise-empty-reason");
  let startingPractice = false;

  const skillLabels = {
    "skill.programming.code_semantics": "Ngữ nghĩa mã nguồn & ngôn ngữ lập trình",
    "skill.backend.data_consistency": "Nhất quán dữ liệu & giao dịch Backend",
    "skill.algorithms.correctness_and_complexity": "Tính đúng đắn & độ phức tạp thuật toán",
    "skill.engineering.code_review_and_verification": "Đánh giá mã nguồn & kiểm chứng",
  };
  const knownExerciseTitles = {
    "exercise.programming.mutable_defaults_and_binding": "Thực hành đối số mặc định và bắt giữ biến trong closure (Python)",
    "exercise.backend.atomic_transaction_locking": "Thiết kế giao dịch nguyên tử và chuẩn hóa thứ tự khóa trong PostgreSQL",
    "exercise.backend.rollback_invariant_test": "Viết kiểm thử đồng thời và bảo toàn bất biến khi rollback",
    "exercise.algorithms.loop_invariant_and_bounds": "Chứng minh bất biến vòng lặp và biên tìm kiếm nhị phân",
    "exercise.engineering.contract_and_security_review": "Rà soát hợp đồng hàm và tham số hóa truy vấn SQL an toàn",
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

  function formatSkillLabel(id) {
    return skillLabels[id] || id;
  }

  function safeExternalUrl(value) {
    try {
      const parsed = new URL(value, window.location.href);
      return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : null;
    } catch (_error) {
      return null;
    }
  }

  function appendSection(container, title, values, emptyText, exerciseTitleMap) {
    const section = node("section", "exercise-card__section");
    section.append(node("h3", "", title));
    const listNode = node("ul", "");
    if (values && values.length) {
      for (const value of values) {
        const entry = node("li", "");
        const friendlyTitle = (exerciseTitleMap && exerciseTitleMap.get(value)) || knownExerciseTitles[value];
        if (friendlyTitle) {
          entry.textContent = friendlyTitle;
        } else {
          entry.append(document.createTextNode("Bài tiên quyết: "));
          entry.append(node("code", "", value));
        }
        listNode.append(entry);
      }
    } else {
      listNode.append(node("li", "", emptyText));
    }
    section.append(listNode);
    container.append(section);
  }

  function ensureFilterResetLink(container) {
    const existing = container.querySelector("[data-reset-exercise-filter]");
    if (existing) existing.remove();
    if (!exerciseId && !skillId) return;
    const resetLink = node("a", "btn btn--secondary", "Xem toàn bộ bài tập của phiên");
    resetLink.href = `/sessions/${encodeURIComponent(sessionId)}/exercises`;
    resetLink.setAttribute("data-reset-exercise-filter", "true");
    container.append(resetLink);
  }

  async function loadExerciseDetail(item, button, detail) {
    button.disabled = true;
    button.textContent = "Đang tải hướng dẫn…";
    errorBox.hidden = true;
    try {
      const data = await api.getExercise(item.exercise_id, item.version);
      if (data.exercise_id !== item.exercise_id || data.version !== item.version) {
        throw new Error("Nội dung bài tập không khớp phiên bản đã đề xuất.");
      }
      detail.replaceChildren();
      detail.append(node("h3", "", "Hướng dẫn thực hiện"));
      const instructionsEl = node("p", "", data.instructions);
      applyInlineCode(instructionsEl);
      detail.append(instructionsEl);
      if (data.observable_outcome) {
        detail.append(node("h3", "", "Kết quả cần đạt"));
        const outcomeEl = node("p", "", data.observable_outcome);
        applyInlineCode(outcomeEl);
        detail.append(outcomeEl);
      }
      detail.hidden = false;
      button.hidden = true;
    } catch (error) {
      errorBox.textContent = [error.message || "Không tải được hướng dẫn bài tập.", error.recoveryAction].filter(Boolean).join(" ");
      errorBox.hidden = false;
      errorBox.focus();
      button.textContent = "Thử tải lại hướng dẫn";
      button.disabled = false;
    }
  }

  async function startPractice(item, button) {
    const gap = item.matched_gap || {};
    const answer = gap.answer_ref;
    if (startingPractice || !answer || !answer.id || !answer.revision) return;
    startingPractice = true;
    button.disabled = true;
    button.textContent = "Đang tạo lượt luyện…";
    errorBox.hidden = true;
    statusBox.textContent = "Đang chọn câu hỏi đã duyệt khác câu gốc…";
    statusBox.hidden = false;
    try {
      const created = await api.startPractice(sessionId, answer.id, {
        answer_revision: answer.revision,
        criterion_id: gap.criterion_id,
        exercise_id: item.exercise_id,
      });
      if (!created.session_id || !created.current_question) {
        throw new Error("Phiên luyện mới chưa có câu hỏi hợp lệ.");
      }
      window.location.assign(`/sessions/${encodeURIComponent(created.session_id)}`);
    } catch (error) {
      errorBox.textContent = [error.message || "Chưa thể tạo lượt luyện lại.", error.recoveryAction].filter(Boolean).join(" ");
      errorBox.hidden = false;
      errorBox.focus();
      statusBox.hidden = true;
      const canRetry = error.code !== "SESSION_EXPIRED" && error.code !== "SESSION_FORBIDDEN" && error.status !== 410 && error.status !== 403;
      button.textContent = canRetry ? "Thử tạo lượt luyện lại" : "Không thể tạo lượt luyện";
      button.disabled = !canRetry;
      startingPractice = false;
    }
  }

  function groupRecommendations(recommendations) {
    const groups = new Map();
    for (const item of recommendations || []) {
      const key = `${item.exercise_id}@${item.version}`;
      let group = groups.get(key);
      if (!group) {
        group = {
          primary: item,
          items: [],
          skillIds: [],
          reasons: [],
          reasonKeys: new Set(),
          practiceTargets: [],
          practiceKeys: new Set(),
          hasEligibleAlternate: false,
        };
        groups.set(key, group);
      }
      group.items.push(item);
      for (const skill of item.related_skill_ids || []) {
        if (!group.skillIds.includes(skill)) group.skillIds.push(skill);
      }
      const gap = item.matched_gap || {};
      const label = gap.criterion_label || gap.skill_label || "Điểm thiếu đã xác nhận";
      const detailText = gap.reason || item.recommendation_reason || "Liên quan tới tiêu chí chưa đạt trong phiên.";
      const reasonText = `${label}: ${detailText}`;
      const reasonKey = `${gap.criterion_id || ""}|${(gap.answer_ref && gap.answer_ref.id) || ""}|${reasonText}`;
      if (!group.reasonKeys.has(reasonKey)) {
        group.reasonKeys.add(reasonKey);
        group.reasons.push(reasonText);
      }
      if (item.eligible_alternate_question_available) {
        group.hasEligibleAlternate = true;
        const answer = gap.answer_ref;
        if (answer && answer.id) {
          const practiceKey = `${answer.id}@${answer.revision || 1}`;
          if (!group.practiceKeys.has(practiceKey)) {
            group.practiceKeys.add(practiceKey);
            group.practiceTargets.push(item);
          }
        }
      }
    }
    return Array.from(groups.values());
  }

  function renderExercise(group, exerciseTitleMap, index) {
    const item = group.primary;
    const card = node("article", "exercise-card");

    const head = node("div", "exercise-card__head");
    head.append(node("span", "exercise-card__index", formatIndex(index)));
    const meta = node("div", "exercise-meta");
    meta.append(node("span", "badge badge--neutral", `Thời lượng ước tính: ${item.estimated_duration_minutes == null ? "chưa có" : `${item.estimated_duration_minutes} phút`}`));
    for (const skill of group.skillIds) meta.append(node("span", "badge badge--unmet", formatSkillLabel(skill)));
    head.append(meta);
    card.append(head);

    card.append(node("h2", "", item.title));
    const summaryEl = node("p", "exercise-card__summary", item.summary);
    applyInlineCode(summaryEl);
    card.append(summaryEl);

    const gapSection = node("section", "exercise-card__reason");
    gapSection.append(node("h3", "", "Vì sao bài này phù hợp"));
    if (group.reasons.length > 1) {
      const reasonList = node("ul", "exercise-card__reasons");
      for (const reasonText of group.reasons) {
        const li = node("li", "", reasonText);
        applyInlineCode(li);
        reasonList.append(li);
      }
      gapSection.append(reasonList);
    } else {
      const reasonP = node("p", "", group.reasons[0] || "Liên quan tới tiêu chí chưa đạt trong phiên.");
      applyInlineCode(reasonP);
      gapSection.append(reasonP);
    }
    card.append(gapSection);

    const detailGrid = node("div", "exercise-card__grid");
    appendSection(detailGrid, "Bài cần học trước", item.prerequisite_ids, "Không yêu cầu bài tiên quyết.", exerciseTitleMap);

    const source = item.source || {};
    const sourceSection = node("section", "exercise-card__section");
    sourceSection.append(node("h3", "", "Nguồn nội dung"));
    const sourceUrl = source.url ? safeExternalUrl(source.url) : null;
    if (sourceUrl) {
      const link = node("a", "", source.title || source.source_id || "Mở nguồn tham khảo");
      link.href = sourceUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      sourceSection.append(link);
    } else {
      sourceSection.append(node("p", "", source.title || source.source_id || "Chưa có nguồn tham khảo đi kèm."));
    }
    if (source.license_spdx) sourceSection.append(node("p", "form-hint", `Giấy phép: ${source.license_spdx}`));
    if (source.required_notice) sourceSection.append(node("p", "form-hint", source.required_notice));
    detailGrid.append(sourceSection);
    card.append(detailGrid);

    const actionSection = node("section", "exercise-card__section exercise-card__section--actions");
    actionSection.append(node("h3", "", "Hành động luyện tập"));
    const actionsRow = node("div", "exercise-card__actions-row");

    if (group.practiceTargets.length > 0) {
      const practiceGroup = node("div", "exercise-card__practice-actions");
      for (const target of group.practiceTargets) {
        const targetGap = target.matched_gap || {};
        const label = group.practiceTargets.length > 1 && targetGap.criterion_label
          ? `Luyện lại với câu hỏi khác (${targetGap.criterion_label})`
          : "Luyện lại với câu hỏi khác";
        const button = node("button", "btn btn--primary", label);
        button.type = "button";
        button.addEventListener("click", () => startPractice(target, button));
        practiceGroup.append(button);
      }
      actionsRow.append(practiceGroup);
    }

    const detailButton = node("button", "btn btn--secondary", "Xem hướng dẫn bài tập");
    detailButton.type = "button";
    const detail = node("div", "exercise-card__detail");
    detail.hidden = true;
    detailButton.addEventListener("click", () => loadExerciseDetail(item, detailButton, detail));
    actionsRow.append(detailButton);
    actionSection.append(actionsRow);

    if (group.practiceTargets.length === 0) {
      if (group.hasEligibleAlternate) {
        actionSection.append(node("p", "form-hint", "Chưa có mã bài trả lời đã chấm để bắt đầu lượt luyện lại."));
      } else {
        actionSection.append(node("p", "form-hint", "Phiên này chưa có biến thể khác đủ điều kiện cho bài tập này."));
      }
    }
    actionSection.append(detail);
    card.append(actionSection);
    return card;
  }

  function renderRecommendations(data) {
    list.replaceChildren();
    let recommendations = data.recommendations || [];
    if (exerciseId) recommendations = recommendations.filter((item) => item.exercise_id === exerciseId);
    if (skillId) recommendations = recommendations.filter((item) => (item.related_skill_ids || []).includes(skillId));

    const exerciseTitleMap = new Map();
    for (const rec of data.recommendations || []) {
      if (rec.exercise_id && rec.title) exerciseTitleMap.set(rec.exercise_id, rec.title);
    }
    const grouped = groupRecommendations(recommendations);
    for (let index = 0; index < grouped.length; index += 1) {
      list.append(renderExercise(grouped[index], exerciseTitleMap, index));
    }
    const noMatches = grouped.length === 0;
    empty.hidden = !noMatches;
    list.hidden = noMatches;
    if (noMatches) {
      message.textContent = "";
      message.hidden = true;
      if (data.unmatched_skill_ids && data.unmatched_skill_ids.length) {
        emptyReason.textContent = `Chưa tìm thấy bài đã duyệt cho kỹ năng: ${data.unmatched_skill_ids.map(formatSkillLabel).join(", ")}. Không tạo bài thay thế tự động.`;
      } else if (skillId) {
        emptyReason.textContent = "Chưa có bài tập phù hợp với kỹ năng đã chọn trong phiên này. Bạn có thể mở toàn bộ bài tập của phiên.";
      } else if (exerciseId) {
        emptyReason.textContent = "Chưa tìm thấy bài tập đã chọn trong danh sách đề xuất của phiên này. Bạn có thể mở toàn bộ bài tập của phiên.";
      } else {
        emptyReason.textContent = data.message || "Chưa có bài tập phù hợp với điểm thiếu đã xác nhận trong phiên.";
      }
    } else {
      message.textContent = data.message || "";
      message.hidden = !data.message;
    }
    ensureFilterResetLink(noMatches ? empty : content);
    content.hidden = false;
    statusBox.hidden = true;
  }

  async function loadRecommendations() {
    statusBox.hidden = false;
    statusBox.textContent = "Đang tải đề xuất từ phiên…";
    errorBox.hidden = true;
    content.hidden = true;
    try {
      const payload = await api.getExerciseRecommendations(sessionId);
      renderRecommendations(payload);
    } catch (error) {
      statusBox.hidden = true;
      errorBox.textContent = `${error.message || "Chưa tải được bài tập."} ${error.recoveryAction || "Không có bài luyện thay thế nào được tự tạo."}`;
      errorBox.hidden = false;
      const canRetry = error.status !== 403 && error.code !== "SESSION_FORBIDDEN";
      if (canRetry) {
        const retry = node("button", "btn btn--secondary", "Tải lại đề xuất");
        retry.type = "button";
        retry.addEventListener("click", loadRecommendations);
        errorBox.replaceChildren(document.createTextNode(`${error.message || "Chưa tải được bài tập."} `), retry);
      }
      errorBox.focus();
    }
  }

  loadRecommendations();
})();
