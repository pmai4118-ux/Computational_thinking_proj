(() => {
  "use strict";

  const workspace = document.querySelector("[data-workspace]");
  const form = document.querySelector("#answer-form");
  if (!workspace || !form) return;

  const answerField = document.querySelector("#answer-text");
  const counter = document.querySelector("#answer-counter");
  const draftLabel = document.querySelector("[data-draft-label]");
  const errorBox = document.querySelector("#workspace-error");
  const statusBox = document.querySelector("#workspace-status");
  const submitButton = document.querySelector("#submit-answer");
  const retryButton = document.querySelector("#retry-evaluation");
  const sessionId = workspace.dataset.sessionId;
  const questionId = workspace.dataset.questionId;
  const questionVersion = Number(workspace.dataset.questionVersion);
  const savedAnswerId = workspace.dataset.answerId;
  const savedAnswerRevision = Number(workspace.dataset.answerRevision || "1");
  const draftKey = `draft:${sessionId}:${questionId}`;
  const submissionKey = `submission:${sessionId}:${questionId}`;
  const answerKey = `saved-answer:${sessionId}:${questionId}`;
  let busy = false;
  let pendingAnswer = savedAnswerId
    ? { answer_id: savedAnswerId, revision: savedAnswerRevision }
    : null;

  const storage = {
    get(key) {
      try { return window.sessionStorage.getItem(key); } catch (_error) { return null; }
    },
    set(key, value) {
      try { window.sessionStorage.setItem(key, value); return true; } catch (_error) { return false; }
    },
    remove(key) {
      try { window.sessionStorage.removeItem(key); } catch (_error) { /* Storage can be disabled. */ }
    },
  };

  function setStatus(message) {
    statusBox.textContent = message;
    statusBox.hidden = false;
  }

  function setError(message) {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  }

  function setBusy(value) {
    busy = value;
    if (submitButton) submitButton.disabled = value;
    retryButton.disabled = value;
  }

  function updateCounter() {
    counter.textContent = `${answerField.value.length.toLocaleString("vi-VN")} / 20.000 ký tự`;
  }

  function createSubmissionId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `subm-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function submissionFor(text) {
    let saved = null;
    try { saved = JSON.parse(storage.get(submissionKey) || "null"); } catch (_error) { saved = null; }
    if (saved && saved.text === text && saved.id) return saved.id;
    const next = { id: createSubmissionId(), text };
    storage.set(submissionKey, JSON.stringify(next));
    return next.id;
  }

  async function readResponse(response) {
    let payload;
    try { payload = await response.json(); } catch (_error) { payload = {}; }
    if (!response.ok) {
      const recovery = payload.recovery_action ? ` ${payload.recovery_action}` : "";
      throw new Error(`${payload.message || `Yêu cầu thất bại (${response.status}).`}${recovery}`);
    }
    return payload;
  }

  async function evaluateSavedAnswer(answer) {
    if (busy || !answer) return;
    setBusy(true);
    setError("");
    setStatus("Bài đã lưu. Đang đánh giá theo rubric…");
    retryButton.hidden = true;
    try {
      const response = await fetch(`/api/answers/${encodeURIComponent(answer.answer_id)}/evaluate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ answer_revision: answer.revision }),
      });
      const result = await readResponse(response);
      if (result.status !== "completed") {
        throw new Error("Đánh giá chưa hoàn tất. Bài đã lưu; bạn có thể thử lại.");
      }
      storage.remove(answerKey);
      window.location.assign(`/sessions/${encodeURIComponent(sessionId)}/review?answer_id=${encodeURIComponent(answer.answer_id)}`);
    } catch (error) {
      setError(error.message || "Chưa thể đánh giá bài đã lưu.");
      setStatus("Câu trả lời đã lưu trên máy chủ; nội dung gốc được giữ nguyên.");
      errorBox.focus();
      retryButton.hidden = false;
    } finally {
      setBusy(false);
    }
  }

  if (!savedAnswerId) {
    const restoredDraft = storage.get(draftKey);
    if (restoredDraft !== null) {
      answerField.value = restoredDraft;
      setStatus("Đã khôi phục bản nháp trên trình duyệt. Bản nháp chưa được lưu trên máy chủ.");
    }
    answerField.addEventListener("input", () => {
      const stored = storage.set(draftKey, answerField.value);
      draftLabel.textContent = stored
        ? "Bản nháp trên trình duyệt (chưa lưu máy chủ)"
        : "Bản nháp đang hiển thị; trình duyệt không cho phép lưu cục bộ.";
      updateCounter();
      setError("");
    });
  } else {
    retryButton.hidden = false;
    setStatus("Bài đã lưu. Nếu chưa có kết quả, hãy thử đánh giá lại bài đã lưu.");
  }

  updateCounter();

  retryButton.addEventListener("click", () => evaluateSavedAnswer(pendingAnswer));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy || !submitButton) return;
    const text = answerField.value;
    if (!text.trim()) {
      setError("Vui lòng nhập câu trả lời trước khi gửi.");
      answerField.focus();
      return;
    }
    if (text.length > 20000) {
      setError("Câu trả lời vượt quá giới hạn 20.000 ký tự.");
      answerField.focus();
      return;
    }

    const requestBody = {
      question_id: questionId,
      question_version: questionVersion,
      client_submission_id: submissionFor(text),
      text,
    };
    setBusy(true);
    setError("");
    setStatus("Đang lưu nguyên văn câu trả lời…");
    try {
      const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/answers`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      const submitted = await readResponse(response);
      pendingAnswer = {
        answer_id: submitted.answer.answer_id,
        revision: submitted.answer.revision,
      };
      storage.set(answerKey, JSON.stringify(pendingAnswer));
      storage.remove(draftKey);
      draftLabel.textContent = "Đã lưu trên máy chủ";
      answerField.readOnly = true;
      submitButton.hidden = true;
      retryButton.hidden = false;
      setBusy(false);
      await evaluateSavedAnswer(pendingAnswer);
    } catch (error) {
      setError(error.message || "Chưa xác nhận được việc lưu bài. Bản nháp vẫn được giữ trên trình duyệt.");
      setStatus("Chưa xác nhận được bài đã lưu. Gửi lại sẽ dùng cùng mã gửi cho cùng nội dung.");
      answerField.focus();
    } finally {
      setBusy(false);
    }
  });
})();
