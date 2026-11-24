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

  function node(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  }

  function safeExternalUrl(value) {
    try {
      const parsed = new URL(value, window.location.href);
      return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : null;
    } catch (_error) {
      return null;
    }
  }

  function appendSection(card, title, values, emptyText) {
    const section = node("section", "exercise-card__section");
    section.append(node("h3", "", title));
    const listNode = node("ul", "");
    if (values && values.length) {
      for (const value of values) {
        const entry = node("li", "");
        entry.append(document.createTextNode("Mã bài: "));
        entry.append(node("code", "", value));
        listNode.append(entry);
      }
    } else {
      listNode.append(node("li", "", emptyText));
    }
    section.append(listNode);
    card.append(section);
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
      detail.append(node("p", "", data.instructions));
      if (data.observable_outcome) {
        detail.append(node("h3", "", "Kết quả cần đạt"));
        detail.append(node("p", "", data.observable_outcome));
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

  function renderExercise(item) {
    const card = node("article", "exercise-card");
    card.append(node("h2", "", item.title));

    const gap = item.matched_gap || {};
    const gapSection = node("section", "exercise-card__reason");
    gapSection.append(node("h3", "", "Vì sao bài này phù hợp"));
    gapSection.append(node("p", "", `${gap.criterion_label || gap.skill_label || "Điểm thiếu đã xác nhận"}: ${gap.reason || "API chưa cung cấp lý do chi tiết."}`));
    card.append(gapSection);

    card.append(node("p", "exercise-card__summary", item.summary));

    const meta = node("div", "exercise-meta");
    meta.append(node("span", "badge", `Thời lượng ước tính: ${item.estimated_duration_minutes == null ? "chưa có" : `${item.estimated_duration_minutes} phút`}`));
    for (const skill of item.related_skill_ids || []) meta.append(node("span", "badge", skill));
    card.append(meta);

    appendSection(card, "Bài cần học trước", item.prerequisite_ids, "Không yêu cầu bài tiên quyết.");

    const detailSection = node("section", "exercise-card__section");
    const detailButton = node("button", "btn btn--secondary", "Xem hướng dẫn bài tập");
    detailButton.type = "button";
    const detail = node("div", "exercise-card__detail");
    detail.hidden = true;
    detailButton.addEventListener("click", () => loadExerciseDetail(item, detailButton, detail));
    detailSection.append(detailButton, detail);
    card.append(detailSection);

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
      sourceSection.append(node("p", "", source.title || source.source_id || "API chưa cung cấp nguồn tham khảo."));
    }
    if (source.license_spdx) sourceSection.append(node("p", "form-hint", `Giấy phép: ${source.license_spdx}`));
    if (source.required_notice) sourceSection.append(node("p", "form-hint", source.required_notice));
    card.append(sourceSection);

    const actionSection = node("section", "exercise-card__section");
    actionSection.append(node("h3", "", "Luyện lại bằng câu hỏi khác"));
    if (item.eligible_alternate_question_available && gap.answer_ref && gap.answer_ref.id) {
      const button = node("button", "btn btn--primary", "Luyện lại với câu hỏi khác");
      button.type = "button";
      button.addEventListener("click", () => startPractice(item, button));
      actionSection.append(button);
    } else if (item.eligible_alternate_question_available) {
      actionSection.append(node("p", "form-hint", "Chưa có mã bài trả lời đã chấm để bắt đầu lượt luyện lại."));
    } else {
      actionSection.append(node("p", "form-hint", "Phiên này chưa có biến thể khác đủ điều kiện cho bài tập này."));
    }
    card.append(actionSection);
    return card;
  }

  function renderRecommendations(data) {
    message.textContent = data.message || "";
    list.replaceChildren();
    let recommendations = data.recommendations || [];
    if (exerciseId) recommendations = recommendations.filter((item) => item.exercise_id === exerciseId);
    if (skillId) recommendations = recommendations.filter((item) => (item.related_skill_ids || []).includes(skillId));

    for (const recommendation of recommendations) list.append(renderExercise(recommendation));
    const noMatches = recommendations.length === 0;
    empty.hidden = !noMatches;
    list.hidden = noMatches;
    if (noMatches && data.unmatched_skill_ids && data.unmatched_skill_ids.length) {
      emptyReason.textContent = `Chưa tìm thấy bài đã duyệt cho kỹ năng: ${data.unmatched_skill_ids.join(", ")}. Không tạo bài thay thế tự động.`;
    } else if (noMatches && (exerciseId || skillId)) {
      emptyReason.textContent = "Không có bài tập trong phản hồi API khớp với lựa chọn này. Hãy xem toàn bộ bài tập của phiên.";
    } else if (noMatches) {
      emptyReason.textContent = data.message || "Không có bài tập khớp với điểm thiếu đã xác nhận trong phiên.";
    }
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
