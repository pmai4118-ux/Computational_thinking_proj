(() => {
  "use strict";

  const form = document.querySelector("#setup-form");
  if (!form) return;
  const activity = window.InterviewActivity?.mount("setup-activity");

  const timingInput = document.querySelector("#evaluation-timing-input");
  const modeCards = document.querySelectorAll("[data-mode-card]");
  const modeHint = document.querySelector("#selected-mode-hint");
  const submitBtn = document.querySelector("#start-session-btn");
  const apiErrorBox = document.querySelector("#setup-api-error");
  const roleSelect = document.querySelector("#role-select");
  const levelSelect = document.querySelector("#level-select");
  const languageSelect = document.querySelector("#language-select");

  const modeDescriptions = {
    after_session: "Đang chọn: Mô phỏng thực tế (chấm sau khi kết thúc phiên)",
    per_question: "Đang chọn: Luyện có hướng dẫn (nhận phản hồi ngay sau từng câu)",
  };

  function setSelectedMode(timing) {
    const normalized = timing === "per_question" ? "per_question" : "after_session";
    if (timingInput) timingInput.value = normalized;
    for (const card of modeCards) {
      const isSelected = card.getAttribute("data-mode-card") === normalized;
      card.setAttribute("aria-pressed", isSelected ? "true" : "false");
      if (card.classList) {
        card.classList.toggle("hub-mode-card--active", isSelected);
      }
    }
    if (modeHint) {
      modeHint.textContent = modeDescriptions[normalized];
    }
  }

  for (const card of modeCards) {
    card.addEventListener("click", () => {
      setSelectedMode(card.getAttribute("data-mode-card"));
    });
  }

  if (timingInput) timingInput.hidden = true;
  const timingLabel = document.querySelector("#native-timing-label");
  if (timingLabel) timingLabel.hidden = true;
  setSelectedMode(timingInput ? timingInput.value : "after_session");

  let submitting = false;
  form.addEventListener("submit", async (event) => {
    if (submitting) {
      event.preventDefault();
      return;
    }

    const api = window.InterviewApi;
    if (!api || typeof api.createSession !== "function") {
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Đang khởi tạo phiên…";
      }
      return;
    }

    event.preventDefault();
    submitting = true;
    activity?.start({ kind: "loading", title: "Đang chuẩn bị phòng phỏng vấn", description: "Mở phiên và chọn bộ câu hỏi phù hợp với cấu hình bạn đã xác nhận." });
    window.InterviewActivity?.buttonBusy(submitBtn, true);
    if (apiErrorBox) {
      apiErrorBox.textContent = "";
      apiErrorBox.hidden = true;
    }
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Đang khởi tạo phiên…";
    }

    try {
      const created = await api.createSession({
        role: roleSelect ? roleSelect.value : "backend_developer",
        level: levelSelect ? levelSelect.value : "intern_fresher",
        language: languageSelect ? languageSelect.value : "vi",
        evaluation_timing: timingInput ? timingInput.value : "after_session",
      });
      window.location.assign(`/sessions/${encodeURIComponent(created.session_id)}`);
    } catch (error) {
      activity?.stop();
      window.InterviewActivity?.buttonBusy(submitBtn, false);
      submitting = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Xác nhận bắt đầu phỏng vấn";
      }
      if (apiErrorBox) {
        const msg = [
          error && error.message ? error.message : "Chưa thể khởi tạo phiên luyện tập.",
          error && error.recoveryAction ? error.recoveryAction : "Vui lòng kiểm tra lại lựa chọn và thử lại.",
        ].filter(Boolean).join(" ");
        apiErrorBox.textContent = msg;
        apiErrorBox.hidden = false;
        apiErrorBox.focus();
      }
    }
  });
})();
