(() => {
  "use strict";

  const page = document.querySelector("[data-exercise-page]");
  if (!page) return;
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

  function renderExercise(item) {
    const card = node("article", "exercise-card");
    card.append(node("h2", "", item.title));
    card.append(node("p", "", item.summary));
    const meta = node("div", "exercise-meta");
    meta.append(node("span", "badge", `Ước tính: ${item.estimated_duration_minutes == null ? "chưa có thời lượng" : `${item.estimated_duration_minutes} phút`}`));
    for (const skill of item.related_skill_ids || []) meta.append(node("span", "badge", skill));
    card.append(meta);

    const gap = item.matched_gap || {};
    const gapSection = node("section", "exercise-card__section");
    gapSection.append(node("h3", "", "Vì sao có bài tập này"));
    gapSection.append(node("p", "", `${gap.criterion_label || gap.skill_label || "Điểm thiếu đã xác nhận"}: ${gap.reason || "API chưa cung cấp lý do chi tiết."}`));
    card.append(gapSection);

    appendSection(card, "Bài cần học trước", item.prerequisite_ids, "Không yêu cầu bài tiên quyết.");

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
    if (item.eligible_alternate_question_available && item.matched_gap && item.matched_gap.evaluation_id) {
      const button = node("button", "btn btn--primary", "Luyện lại bằng biến thể khác");
      button.type = "button";
      button.dataset.exerciseId = item.exercise_id;
      button.addEventListener("click", () => startPractice(button, item));
      actionSection.append(button);
      actionSection.append(node("p", "form-hint", "Mở một phiên mới với câu hỏi đã duyệt cho đúng điểm cần luyện; câu cũ không bị lặp."));
    } else {
      actionSection.append(node("p", "form-hint", "Phiên này chưa có biến thể khác đủ điều kiện cho bài tập này."));
    }
    card.append(actionSection);
    return card;
  }

  async function startPractice(button, item) {
    const answerRef = item.matched_gap && item.matched_gap.answer_ref;
    const answerId = answerRef && answerRef.id;
    if (!answerId || !item.matched_gap.criterion_id) return;
    button.disabled = true;
    const previous = button.textContent;
    button.textContent = "Đang mở phiên…";
    try {
      const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/answers/${encodeURIComponent(answerId)}/practice`, {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          answer_revision: answerRef.revision,
          criterion_id: item.matched_gap.criterion_id,
          exercise_id: item.exercise_id,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.message || "Chưa thể mở phiên luyện lại.");
      if (!payload.session_id) throw new Error("API không trả về phiên luyện lại.");
      window.location.assign(`/sessions/${encodeURIComponent(payload.session_id)}`);
    } catch (error) {
      button.disabled = false;
      button.textContent = previous;
      errorBox.textContent = `${error.message || "Chưa thể mở phiên luyện lại."} Bài cũ vẫn được giữ nguyên.`;
      errorBox.hidden = false;
      errorBox.focus();
    }
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
      const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/exercises`, {
        headers: { accept: "application/json" },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.message || `Không tải được đề xuất (${response.status}).`);
      renderRecommendations(payload);
    } catch (error) {
      statusBox.hidden = true;
      errorBox.textContent = `${error.message || "Chưa tải được bài tập."} Không có bài luyện thay thế nào được tự tạo.`;
      errorBox.hidden = false;
      const retry = node("button", "btn btn--secondary", "Tải lại đề xuất");
      retry.type = "button";
      retry.addEventListener("click", loadRecommendations);
      errorBox.replaceChildren(document.createTextNode(`${error.message || "Chưa tải được bài tập."} `), retry);
    }
  }

  loadRecommendations();
})();
