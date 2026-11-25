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
  const openReviewLink = document.querySelector("#open-review");
  const endButton = document.querySelector("#end-session");
  const endConfirmation = document.querySelector("#end-session-confirmation");
  const confirmEndButton = document.querySelector("#confirm-end-session");
  const cancelEndButton = document.querySelector("#cancel-end-session");
  const sessionExpiredRecovery = document.querySelector("#session-expired-recovery");
  const api = window.InterviewApi;
  const sessionId = workspace.dataset.sessionId;
  const questionId = workspace.dataset.questionId;
  const questionVersion = Number(workspace.dataset.questionVersion);
  const savedAnswerId = workspace.dataset.answerId;
  const savedAnswerRevision = Number(workspace.dataset.answerRevision || "1");
  const draftKey = `draft:${sessionId}:${questionId}`;
  const submissionKey = `submission:${sessionId}:${questionId}`;
  const answerKey = `saved-answer:${sessionId}:${questionId}`;
  const MAX_POLLING_DURATION_MS = 150000;
  const LEAVE_CONFIRM_MESSAGE = "Bạn có chắc chắn muốn rời khỏi phiên làm bài? Bản nháp chưa gửi chưa được lưu trên máy chủ.";
  let busy = false;
  let allowingNavigation = false;
  let statusPoll = null;
  let waitNotice = null;
  let waitStartedAt = 0;
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

  function hasUnsavedWork() {
    if (allowingNavigation) return false;
    if (busy) return true;
    return !pendingAnswer && Boolean(answerField && answerField.value && answerField.value.trim());
  }

  function setupNavigationGuard() {
    const nav = document.querySelector(".site-nav");
    if (nav && nav.classList && typeof nav.classList.add === "function") {
      nav.classList.add("site-nav--in-session");
    }
    if (typeof document.querySelectorAll === "function") {
      const links = document.querySelectorAll(".site-nav__link, .site-brand__link");
      for (const link of links) {
        if (link && typeof link.addEventListener === "function") {
          link.addEventListener("click", (event) => {
            if (!hasUnsavedWork()) return;
            if (typeof window.confirm === "function" && !window.confirm(LEAVE_CONFIRM_MESSAGE)) {
              event.preventDefault();
            } else {
              allowingNavigation = true;
            }
          });
        }
      }
    }
    if (typeof window.addEventListener === "function") {
      window.addEventListener("beforeunload", (event) => {
        if (!hasUnsavedWork()) return;
        event.preventDefault();
        event.returnValue = LEAVE_CONFIRM_MESSAGE;
      });
    }
  }

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
    if (endButton) endButton.disabled = value;
    if (confirmEndButton) confirmEndButton.disabled = value;
    if (cancelEndButton) cancelEndButton.disabled = value;
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

  function errorText(error) {
    if (error.code === "SESSION_EXPIRED" || error.status === 410) {
      return [
        error.message || "Phiên luyện tập đã hết hạn khả dụng.",
        error.recoveryAction || "Bản nháp được giữ nguyên trên ô nhập. Vui lòng sao chép và bắt đầu phiên mới.",
      ].filter(Boolean).join(" ");
    }
    if (error.code === "SESSION_FORBIDDEN" || error.status === 403) {
      return [
        error.message || "Phiên luyện tập này không thuộc trình duyệt hiện tại.",
        error.recoveryAction || "Bản nháp được giữ nguyên để bạn sao chép và mở phiên hợp lệ.",
      ].filter(Boolean).join(" ");
    }
    if (error.code === "SUBMISSION_CONFLICT" || error.status === 409) {
      return [
        error.message || "Mã gửi bài đã được dùng cho một nội dung khác.",
        error.recoveryAction || "Tải lại câu trả lời đã lưu hoặc tạo mã gửi mới.",
      ].filter(Boolean).join(" ");
    }
    if (error.code === "PROVIDER_TIMEOUT") {
      return "AI phản hồi quá thời gian. Bài đã lưu nguyên vẹn và chưa bị chấm điểm; bạn có thể thử đánh giá lại.";
    }
    if (error.code === "EVALUATION_IN_PROGRESS") {
      return "Bài này đang được AI đánh giá. Hãy chờ kết quả của lượt đang chạy.";
    }
    if (error.code === "EVALUATION_INTERRUPTED") {
      return "Lượt đánh giá trước bị gián đoạn. Bài đã lưu và bạn có thể thử đánh giá lại.";
    }
    if (typeof error.code === "string" && error.code.startsWith("PROVIDER_")) {
      return error.retryable === false
        ? "Dịch vụ AI hiện chưa thể đánh giá bài này. Bài đã lưu; cần khắc phục lỗi dịch vụ trước khi tiếp tục."
        : "Dịch vụ AI chưa hoàn tất đánh giá. Bài đã lưu và bạn có thể thử lại.";
    }
    return [error.message, error.recoveryAction].filter(Boolean).join(" ");
  }

  function hideOpenReview() {
    if (openReviewLink) openReviewLink.hidden = true;
  }

  function showSessionExpired(error) {
    stopWaiting();
    setBusy(false);
    hideOpenReview();
    setError(errorText(error) || "Phiên luyện tập đã hết hạn khả dụng.");
    setStatus("Phiên đã hết hạn; câu trả lời chưa thể ghi vào phiên cũ. Hãy sao chép nội dung và bắt đầu phiên mới.");
    if (submitButton) submitButton.hidden = true;
    if (retryButton) retryButton.hidden = true;
    if (endButton) endButton.hidden = true;
    if (sessionExpiredRecovery) sessionExpiredRecovery.hidden = false;
    errorBox.focus();
  }

  function showSessionForbidden(error) {
    stopWaiting();
    setBusy(false);
    hideOpenReview();
    setError(errorText(error) || "Phiên luyện tập này không thuộc trình duyệt hiện tại.");
    setStatus("Bạn không có quyền gửi vào phiên này. Hãy sao chép nội dung và mở phiên của bạn.");
    if (submitButton) submitButton.hidden = true;
    if (retryButton) retryButton.hidden = true;
    if (endButton) endButton.hidden = true;
    if (sessionExpiredRecovery) sessionExpiredRecovery.hidden = false;
    errorBox.focus();
  }

  function reviewAnswer(answer) {
    allowingNavigation = true;
    storage.remove(answerKey);
    const reviewUrl = new URL(`/sessions/${encodeURIComponent(sessionId)}/review`, window.location.origin);
    reviewUrl.searchParams.set("answer_id", answer.answer_id);
    reviewUrl.searchParams.set("revision", String(answer.revision));
    window.location.assign(reviewUrl.toString());
  }

  function stopWaiting() {
    if (statusPoll !== null) window.clearInterval(statusPoll);
    if (waitNotice !== null) window.clearInterval(waitNotice);
    statusPoll = null;
    waitNotice = null;
  }

  function showWaiting() {
    hideOpenReview();
    waitStartedAt = Date.now();
    setStatus("Bài đã lưu. AI đang đối chiếu câu trả lời với rubric; việc này có thể mất hơn một phút. Bạn có thể quay lại trang này để xem kết quả.");
    waitNotice = window.setInterval(() => {
      const seconds = Math.floor((Date.now() - waitStartedAt) / 1000);
      if (seconds >= 20) {
        setStatus(`Bài đã lưu. AI vẫn đang đánh giá (đã chờ khoảng ${seconds} giây). Bạn có thể quay lại trang này để xem kết quả.`);
      }
    }, 10000);
  }

  function showFailure(error, canRetry = error.retryable !== false) {
    stopWaiting();
    setBusy(false);
    hideOpenReview();
    setError(errorText(error) || "Chưa thể đánh giá bài đã lưu.");
    setStatus("Câu trả lời đã lưu trên máy chủ; chưa có điểm đánh giá.");
    retryButton.hidden = !canRetry;
    errorBox.focus();
  }

  async function readSavedEvaluation(answer) {
    const response = await api.getEvaluation(sessionId, answer.answer_id, answer.revision);
    if (response.result.status === "completed") {
      stopWaiting();
      reviewAnswer(answer);
      return "completed";
    }
    if (response.result.status === "failed") {
      const failure = new Error(response.result.failure_message || "AI chưa hoàn tất đánh giá.");
      failure.code = response.result.failure_code;
      failure.retryable = response.result.retryable;
      showFailure(failure);
      return "failed";
    }
    return "processing";
  }

  function watchEvaluation(answer) {
    if (statusPoll !== null) return;
    setBusy(true);
    retryButton.hidden = true;
    showWaiting();
    let reading = false;
    statusPoll = window.setInterval(async () => {
      if (reading) return;
      if (Date.now() - waitStartedAt >= MAX_POLLING_DURATION_MS) {
        stopWaiting();
        setBusy(false);
        setError("Lượt đánh giá mất nhiều thời gian hơn dự kiến. Bài trả lời của bạn đã được lưu an toàn trên máy chủ (chưa bị tính điểm). Bạn có thể thử đánh giá lại hoặc tải lại trang.");
        setStatus("Câu trả lời đã lưu trên máy chủ; chưa có điểm đánh giá.");
        retryButton.hidden = false;
        errorBox.focus();
        return;
      }
      reading = true;
      try {
        await readSavedEvaluation(answer);
      } catch (error) {
        if (error.code === "SESSION_EXPIRED" || error.status === 410) {
          showSessionExpired(error);
          return;
        }
        if (error.code === "SESSION_FORBIDDEN" || error.status === 403) {
          showSessionForbidden(error);
          return;
        }
        // A temporary read error must not start another evaluation.
        setStatus("Bài đã lưu. Chưa đọc được trạng thái AI; hệ thống sẽ kiểm tra lại.");
      } finally {
        reading = false;
      }
    }, 5000);
  }

  async function evaluateSavedAnswer(answer) {
    if (busy || !answer) return;
    stopWaiting();
    setBusy(true);
    setError("");
    showWaiting();
    retryButton.hidden = true;
    try {
      const response = await api.evaluateAnswer(sessionId, answer.answer_id, answer.revision);
      if (!response.result || response.result.status !== "completed") {
        throw new Error("Đánh giá chưa hoàn tất. Bài đã lưu; bạn có thể thử lại.");
      }
      stopWaiting();
      reviewAnswer(answer);
    } catch (error) {
      if (error.code === "SESSION_EXPIRED" || error.status === 410) {
        showSessionExpired(error);
        return;
      }
      if (error.code === "SESSION_FORBIDDEN" || error.status === 403) {
        showSessionForbidden(error);
        return;
      }
      if (error.code === "EVALUATION_IN_PROGRESS" || error.code === "NETWORK_ERROR") {
        try {
          const state = await readSavedEvaluation(answer);
          if (state === "processing") {
            stopWaiting();
            watchEvaluation(answer);
          }
          return;
        } catch (readError) {
          if (readError.code === "SESSION_EXPIRED" || readError.status === 410) {
            showSessionExpired(readError);
            return;
          }
          if (readError.code === "SESSION_FORBIDDEN" || readError.status === 403) {
            showSessionForbidden(readError);
            return;
          }
          if (error.code === "EVALUATION_IN_PROGRESS") {
            stopWaiting();
            watchEvaluation(answer);
            return;
          }
        }
      }
      showFailure(error, error.code !== "EVALUATION_IN_PROGRESS" && error.retryable !== false);
    } finally {
      if (statusPoll === null && (!submitButton || !submitButton.hidden)) setBusy(false);
    }
  }

  setupNavigationGuard();

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
    hideOpenReview();
    setStatus("Bài đã lưu. Đang kiểm tra kết quả đánh giá gần nhất…");
    readSavedEvaluation(pendingAnswer).then((state) => {
      if (state === "processing") watchEvaluation(pendingAnswer);
    }).catch((error) => {
      if (error.status === 404) {
        retryButton.hidden = false;
        setStatus("Bài đã lưu nhưng chưa được đánh giá. Bạn có thể bắt đầu đánh giá bài đã lưu.");
      } else if (error.code === "SESSION_EXPIRED" || error.status === 410) {
        showSessionExpired(error);
      } else if (error.code === "SESSION_FORBIDDEN" || error.status === 403) {
        showSessionForbidden(error);
      } else {
        showFailure(error);
      }
    });
  }

  updateCounter();

  retryButton.addEventListener("click", () => evaluateSavedAnswer(pendingAnswer));

  if (endButton) {
    endButton.addEventListener("click", () => {
      if (busy) return;
      endConfirmation.hidden = false;
      confirmEndButton.focus();
    });
    cancelEndButton.addEventListener("click", () => {
      endConfirmation.hidden = true;
      endButton.focus();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !endConfirmation.hidden) {
        endConfirmation.hidden = true;
        endButton.focus();
      }
    });
    confirmEndButton.addEventListener("click", async () => {
      if (busy) return;
      setBusy(true);
      setError("");
      setStatus("Đang kết thúc phiên và lưu tổng kết…");
      try {
        await api.endSession(sessionId);
        allowingNavigation = true;
        window.location.assign(`/sessions/${encodeURIComponent(sessionId)}/summary`);
      } catch (error) {
        if (error.code === "SESSION_EXPIRED" || error.status === 410) {
          showSessionExpired(error);
        } else if (error.code === "SESSION_FORBIDDEN" || error.status === 403) {
          showSessionForbidden(error);
        } else {
          setError(errorText(error) || "Chưa thể kết thúc phiên.");
          errorBox.focus();
        }
      } finally {
        setBusy(false);
      }
    });
  }

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
      const submitted = await api.submitAnswer(sessionId, requestBody);
      pendingAnswer = {
        answer_id: submitted.answer.answer_id,
        revision: submitted.answer.revision,
      };
      storage.set(answerKey, JSON.stringify(pendingAnswer));
      storage.remove(draftKey);
      draftLabel.textContent = "Đã lưu câu trả lời trên máy chủ";
      answerField.readOnly = true;
      submitButton.hidden = true;
      retryButton.hidden = false;
      setBusy(false);
      await evaluateSavedAnswer(pendingAnswer);
    } catch (error) {
      if (error.code === "SESSION_EXPIRED" || error.status === 410) {
        showSessionExpired(error);
      } else if (error.code === "SESSION_FORBIDDEN" || error.status === 403) {
        showSessionForbidden(error);
      } else if (error.code === "SUBMISSION_CONFLICT" || error.status === 409) {
        setError(errorText(error) || "Xung đột mã gửi bài. Hãy tải lại câu trả lời đã lưu.");
        setStatus("Mã gửi đã được dùng cho nội dung khác. Nội dung hiện tại vẫn được giữ trên ô nhập.");
        errorBox.focus();
      } else {
        setError(errorText(error) || "Chưa xác nhận được việc lưu bài. Bản nháp vẫn được giữ trên trình duyệt.");
        setStatus("Chưa xác nhận được bài đã lưu. Bạn có thể kiểm tra mạng rồi bấm gửi lại.");
        answerField.focus();
      }
    } finally {
      if (statusPoll === null && submitButton && !submitButton.hidden) setBusy(false);
    }
  });
})();
