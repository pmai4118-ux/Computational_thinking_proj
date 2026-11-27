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
  const activity = window.InterviewActivity?.mount("workspace-activity", statusBox);
  const submitButton = document.querySelector("#submit-answer");
  const retryButton = document.querySelector("#retry-evaluation");
  const openReviewLink = document.querySelector("#open-review");
  const endButton = document.querySelector("#end-session");
  const endConfirmation = document.querySelector("#end-session-confirmation");
  const confirmEndButton = document.querySelector("#confirm-end-session");
  const cancelEndButton = document.querySelector("#cancel-end-session");
  const sessionExpiredRecovery = document.querySelector("#session-expired-recovery");

  const outlineWrap = document.querySelector("#argument-outline-wrap");
  const boxesContainer = document.querySelector("#argument-boxes-container");
  const addBoxButton = document.querySelector("#add-argument-box");
  const canonicalWrap = document.querySelector("#canonical-answer-wrap");
  const viewSwitch = document.querySelector("#editor-view-switch");
  const modeOutlineBtn = document.querySelector("#mode-outline-btn");
  const modePlainBtn = document.querySelector("#mode-plain-btn");
  const toolbar = document.querySelector("#editor-toolbar");

  const api = window.InterviewApi;
  const sessionId = workspace.dataset.sessionId;
  const deferredAssessment = workspace.dataset.evaluationTiming === "after_session";
  const questionId = workspace.dataset.questionId;
  const questionVersion = Number(workspace.dataset.questionVersion);
  const savedAnswerId = workspace.dataset.answerId;
  const savedAnswerRevision = Number(workspace.dataset.answerRevision || "1");
  const draftKey = `draft:${sessionId}:${questionId}`;
  const structuredDraftKey = `draft:v2:${sessionId}:${questionId}:v${questionVersion}`;
  const submissionKey = `submission:${sessionId}:${questionId}`;
  const answerKey = `saved-answer:${sessionId}:${questionId}`;
  const MAX_POLLING_DURATION_MS = 150000;
  const LEAVE_CONFIRM_MESSAGE = "Bạn có chắc chắn muốn rời khỏi phiên làm bài? Bản nháp chưa gửi chưa được lưu trên máy chủ.";
  const DEFAULT_BOX_TITLES = [
    "Phân tích vấn đề",
    "Phương án và đánh đổi",
    "Cách xác minh",
  ];

  let busy = false;
  let allowingNavigation = false;
  let statusPoll = null;
  let waitNotice = null;
  let waitStartedAt = 0;
  let pendingAnswer = savedAnswerId
    ? { answer_id: savedAnswerId, revision: savedAnswerRevision }
    : null;
  let committedText = savedAnswerId && answerField ? answerField.value : null;
  let outlineBoxes = [];
  let outlineActive = false;
  let editorMode = "outline";
  let lastFocusedTextarea = null;

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
    if (!answerField || !answerField.value || !answerField.value.trim()) return false;
    if (!pendingAnswer) return true;
    return !answerField.readOnly && answerField.value !== committedText;
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
    if (!value) activity?.stop();
    if (!value) for (const button of [submitButton, retryButton, endButton, confirmEndButton]) window.InterviewActivity?.buttonBusy(button, false);
    if (submitButton) submitButton.disabled = value;
    retryButton.disabled = value;
    if (endButton) endButton.disabled = value;
    if (confirmEndButton) confirmEndButton.disabled = value;
    if (cancelEndButton) cancelEndButton.disabled = value;
    if (addBoxButton) addBoxButton.disabled = value;
  }

  function updateCounter() {
    if (!answerField || !counter) return;
    const len = answerField.value.length;
    counter.textContent = `${len.toLocaleString("vi-VN")} / 20.000 ký tự`;
    if (counter.classList) {
      counter.classList.toggle("workspace-counter--over", len > 20000);
    }
  }

  function serializeOutlineBoxes(boxes) {
    const parts = [];
    for (const box of boxes) {
      const body = (box.content || "").trim();
      if (!body) continue;
      const heading = (box.title || "").trim();
      if (heading) {
        parts.push(`${heading}:\n${box.content}`);
      } else {
        parts.push(box.content);
      }
    }
    return parts.join("\n\n");
  }

  function syncFromOutlineBoxes() {
    if (!outlineActive || !answerField || answerField.readOnly) return;
    answerField.value = serializeOutlineBoxes(outlineBoxes);
    const savedStructured = storage.set(
      structuredDraftKey,
      JSON.stringify({ version: 2, boxes: outlineBoxes })
    );
    const savedPlain = storage.set(draftKey, answerField.value);
    if (draftLabel) {
      draftLabel.textContent = (savedStructured || savedPlain)
        ? `Bản nháp trong tab này, chưa lưu máy chủ • ${outlineBoxes.length} khung luận điểm`
        : "Bản nháp đang hiển thị; trình duyệt không cho phép lưu cục bộ.";
    }
    updateCounter();
    setError("");
  }

  function setEditorViewMode(nextMode) {
    editorMode = nextMode === "plain" ? "plain" : "outline";
    if (!outlineWrap || !canonicalWrap) return;

    if (editorMode === "plain" || !outlineActive) {
      outlineWrap.hidden = true;
      canonicalWrap.hidden = false;
      if (canonicalWrap.classList) canonicalWrap.classList.remove("sr-only");
    } else {
      outlineWrap.hidden = false;
      canonicalWrap.hidden = false;
      if (canonicalWrap.classList) canonicalWrap.classList.add("sr-only");
    }

    if (modeOutlineBtn) {
      modeOutlineBtn.setAttribute("aria-pressed", editorMode === "outline" ? "true" : "false");
      if (modeOutlineBtn.classList) {
        modeOutlineBtn.classList.toggle("workspace-mode-switch__btn--active", editorMode === "outline");
      }
    }
    if (modePlainBtn) {
      modePlainBtn.setAttribute("aria-pressed", editorMode === "plain" ? "true" : "false");
      if (modePlainBtn.classList) {
        modePlainBtn.classList.toggle("workspace-mode-switch__btn--active", editorMode === "plain");
      }
    }
  }

  function renderOutlineBoxes() {
    if (!boxesContainer || typeof document.createElement !== "function") return;
    boxesContainer.replaceChildren();

    outlineBoxes.forEach((box, idx) => {
      const card = document.createElement("div");
      card.className = "argument-box";

      const head = document.createElement("div");
      head.className = "argument-box__head";

      const titleWrap = document.createElement("div");
      titleWrap.className = "argument-box__title-wrap";

      const num = document.createElement("span");
      num.className = "argument-box__num";
      num.textContent = String(idx + 1);

      const titleInput = document.createElement("input");
      titleInput.type = "text";
      titleInput.className = "argument-box__heading-input";
      titleInput.value = box.title;
      titleInput.placeholder = `Luận điểm ${idx + 1}`;
      titleInput.setAttribute("aria-label", `Tiêu đề khung luận điểm ${idx + 1}`);
      titleInput.addEventListener("input", () => {
        box.title = titleInput.value;
        syncFromOutlineBoxes();
      });

      titleWrap.append(num, titleInput);
      head.append(titleWrap);

      if (outlineBoxes.length > 1) {
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "btn btn--ghost";
        removeBtn.style.minHeight = "2rem";
        removeBtn.style.padding = "0.125rem 0.5rem";
        removeBtn.textContent = "Xóa";
        removeBtn.setAttribute("aria-label", `Xóa khung luận điểm ${idx + 1}`);
        removeBtn.addEventListener("click", () => {
          outlineBoxes.splice(idx, 1);
          renderOutlineBoxes();
          syncFromOutlineBoxes();
        });
        head.append(removeBtn);
      }

      const textarea = document.createElement("textarea");
      textarea.className = "argument-box__textarea";
      textarea.rows = 3;
      textarea.value = box.content;
      textarea.placeholder = "Nhập lập luận, dẫn chứng hoặc các bước kiểm tra…";
      textarea.setAttribute("aria-label", `Nội dung ${box.title || `luận điểm ${idx + 1}`}`);
      textarea.addEventListener("focus", () => {
        lastFocusedTextarea = textarea;
      });
      textarea.addEventListener("input", () => {
        box.content = textarea.value;
        syncFromOutlineBoxes();
      });

      card.append(head, textarea);
      boxesContainer.append(card);
    });
  }

  function initOutlineEditor({ initialPlainDraft = null } = {}) {
    if (
      !outlineWrap ||
      !boxesContainer ||
      typeof document.createElement !== "function" ||
      typeof document.querySelectorAll !== "function"
    ) {
      return;
    }

    let loadedStructured = null;
    try {
      const raw = storage.get(structuredDraftKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && parsed.version === 2 && Array.isArray(parsed.boxes) && parsed.boxes.length > 0) {
          loadedStructured = parsed.boxes.map((b) => ({
            title: typeof b.title === "string" ? b.title : "",
            content: typeof b.content === "string" ? b.content : "",
          }));
        }
      }
    } catch (_error) {
      loadedStructured = null;
    }

    if (loadedStructured) {
      outlineBoxes = loadedStructured;
      answerField.value = serializeOutlineBoxes(outlineBoxes);
      setStatus("Đã khôi phục bản nháp khung luận điểm trong tab trình duyệt.");
    } else if (initialPlainDraft !== null && initialPlainDraft !== "") {
      // Preserve legacy plain-text draft verbatim in one box with empty title so serialization never alters it.
      outlineBoxes = [{ title: "", content: initialPlainDraft }];
      answerField.value = initialPlainDraft;
    } else if (answerField && answerField.value && answerField.value.trim()) {
      outlineBoxes = [{ title: "", content: answerField.value }];
    } else {
      outlineBoxes = DEFAULT_BOX_TITLES.map((title) => ({ title, content: "" }));
    }

    outlineActive = true;
    renderOutlineBoxes();
    if (viewSwitch) viewSwitch.hidden = false;
    if (toolbar) toolbar.hidden = false;
    setEditorViewMode("outline");

    if (addBoxButton) {
      addBoxButton.addEventListener("click", () => {
        outlineBoxes.push({
          title: `Luận điểm ${outlineBoxes.length + 1}`,
          content: "",
        });
        renderOutlineBoxes();
        syncFromOutlineBoxes();
      });
    }

    if (modeOutlineBtn) {
      modeOutlineBtn.addEventListener("click", () => {
        if (editorMode === "plain" && answerField) {
          const plain = answerField.value;
          if (plain !== serializeOutlineBoxes(outlineBoxes)) {
            outlineBoxes = [{ title: "", content: plain }];
            renderOutlineBoxes();
          }
        }
        setEditorViewMode("outline");
      });
    }

    if (modePlainBtn) {
      modePlainBtn.addEventListener("click", () => {
        syncFromOutlineBoxes();
        setEditorViewMode("plain");
        if (answerField) answerField.focus();
      });
    }

    if (toolbar) {
      const insertButtons = document.querySelectorAll("[data-insert-snippet]");
      for (const btn of insertButtons) {
        btn.addEventListener("click", () => {
          const snippet = btn.getAttribute("data-insert-snippet") || "";
          const target = editorMode === "plain"
            ? answerField
            : (lastFocusedTextarea || boxesContainer.querySelector(".argument-box__textarea"));
          if (!target || target.readOnly) return;
          const start = typeof target.selectionStart === "number" ? target.selectionStart : target.value.length;
          const end = typeof target.selectionEnd === "number" ? target.selectionEnd : target.value.length;
          const before = target.value.slice(0, start);
          const after = target.value.slice(end);
          target.value = `${before}${snippet}${after}`;
          if (typeof target.setSelectionRange === "function") {
            const caret = start + snippet.length;
            target.setSelectionRange(caret, caret);
          }
          target.focus();
          if (target === answerField) {
            storage.set(draftKey, answerField.value);
            updateCounter();
          } else {
            const boxIndex = Array.from(boxesContainer.querySelectorAll(".argument-box__textarea")).indexOf(target);
            if (boxIndex >= 0 && outlineBoxes[boxIndex]) {
              outlineBoxes[boxIndex].content = target.value;
              syncFromOutlineBoxes();
            }
          }
        });
      }
    }
  }

  function disableOutlineForReadOnlyServerAnswer() {
    outlineActive = false;
    if (outlineWrap) outlineWrap.hidden = true;
    if (viewSwitch) viewSwitch.hidden = true;
    if (toolbar) toolbar.hidden = true;
    if (canonicalWrap) {
      canonicalWrap.hidden = false;
      if (canonicalWrap.classList) canonicalWrap.classList.remove("sr-only");
    }
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
    if (error.code === "EVALUATION_RETRY_NOT_ALLOWED") {
      return "Lượt đánh giá trước không thể thử lại trên cùng phiên bản. Bài gốc đã lưu; sau khi khắc phục lỗi dịch vụ hoặc điều chỉnh nội dung, bạn có thể gửi bản trả lời mới hoặc kết thúc sớm phiên.";
    }
    if (typeof error.code === "string" && error.code.startsWith("PROVIDER_")) {
      return error.retryable === false
        ? "Dịch vụ AI hiện chưa thể đánh giá lượt gửi này. Bài gốc đã lưu; sau khi khắc phục lỗi dịch vụ hoặc điều chỉnh nội dung, bạn có thể gửi bản trả lời mới hoặc kết thúc sớm phiên."
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
    activity?.stop();
    if (statusPoll !== null) window.clearInterval(statusPoll);
    if (waitNotice !== null) window.clearInterval(waitNotice);
    statusPoll = null;
    waitNotice = null;
  }

  function showWaiting() {
    activity?.start({ kind: "assessment", title: "AI đang đối chiếu câu trả lời", description: "Bài đã lưu nguyên vẹn. AI đang trích bằng chứng để đối chiếu với rubric; điểm được tính theo các tiêu chí đã công bố." });
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
    retryButton.hidden = !canRetry;
    if (!canRetry) {
      answerField.readOnly = false;
      disableOutlineForReadOnlyServerAnswer();
      if (submitButton) {
        submitButton.textContent = "Gửi bản trả lời mới";
        submitButton.hidden = false;
      }
      const restoredDraft = storage.get(draftKey);
      if (restoredDraft && restoredDraft !== committedText) {
        answerField.value = restoredDraft;
        updateCounter();
        draftLabel.textContent = "Đã khôi phục bản nháp thay thế (bài gốc trước đó vẫn được lưu trên máy chủ)";
        setStatus("Đã khôi phục bản nháp bạn đang chỉnh sửa. Phiên bản trước vẫn được lưu nguyên vẹn trên máy chủ (chưa có điểm); hãy bấm Gửi bản trả lời mới hoặc Kết thúc sớm.");
      } else {
        draftLabel.textContent = "Bài trước đã lưu trên máy chủ; bạn có thể chỉnh sửa và gửi bản mới";
        setStatus("Phiên bản trước vẫn được lưu nguyên vẹn (chưa có điểm). Sau khi khắc phục lỗi hoặc điều chỉnh nội dung, hãy bấm Gửi bản trả lời mới hoặc Kết thúc sớm.");
      }
    } else {
      setStatus("Câu trả lời đã lưu trên máy chủ; chưa có điểm đánh giá.");
    }
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
    initOutlineEditor({ initialPlainDraft: restoredDraft });
  } else {
    disableOutlineForReadOnlyServerAnswer();
    if (deferredAssessment) {
      setStatus("Bài đã lưu. Điểm và nhận xét sẽ có sau khi kết thúc phiên.");
      retryButton.hidden = true;
      if (openReviewLink) openReviewLink.hidden = false;
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
  }

  answerField.addEventListener("input", () => {
    if (!answerField.readOnly) {
      const stored = storage.set(draftKey, answerField.value);
      if (outlineActive && editorMode === "plain") {
        storage.remove(structuredDraftKey);
      }
      draftLabel.textContent = stored
        ? "Bản nháp trong tab này, chưa lưu máy chủ"
        : "Bản nháp đang hiển thị; trình duyệt không cho phép lưu cục bộ.";
    }
    updateCounter();
    setError("");
  });

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
      window.InterviewActivity?.buttonBusy(confirmEndButton, true);
      activity?.start({ kind: "loading", title: "Đang kết thúc phiên", description: "Giữ các bài đã gửi và chuẩn bị trang tổng kết." });
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
    if (outlineActive && editorMode === "outline") {
      syncFromOutlineBoxes();
    }
    const text = answerField.value;
    if (!text.trim()) {
      setError("Vui lòng nhập câu trả lời trước khi gửi.");
      if (outlineActive && editorMode === "outline" && boxesContainer) {
        const firstBoxInput = boxesContainer.querySelector(".argument-box__textarea");
        if (firstBoxInput) firstBoxInput.focus();
        else answerField.focus();
      } else {
        answerField.focus();
      }
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
    window.InterviewActivity?.buttonBusy(submitButton, true);
    setStatus("Đang lưu nguyên văn câu trả lời…");
    activity?.start({ kind: "saving", title: "Đang lưu câu trả lời của bạn", description: "Bản nháp vẫn được giữ trong tab này. Chờ máy chủ xác nhận trước khi chuyển bước." });
    const writingFields = [answerField, ...(typeof boxesContainer?.querySelectorAll === "function" ? boxesContainer.querySelectorAll("input, textarea, button") : [])].map(field => ({ field, disabled: field.disabled }));
    for (const item of writingFields) item.field.disabled = true;
    try {
      const submitted = await api.submitAnswer(sessionId, requestBody);
      pendingAnswer = {
        answer_id: submitted.answer.answer_id,
        revision: submitted.answer.revision,
      };
      committedText = text;
      storage.set(answerKey, JSON.stringify(pendingAnswer));
      storage.remove(draftKey);
      storage.remove(structuredDraftKey);
      storage.remove(submissionKey);
      draftLabel.textContent = "Đã lưu câu trả lời trên máy chủ";
      answerField.readOnly = true;
      disableOutlineForReadOnlyServerAnswer();
      submitButton.hidden = true;
      retryButton.hidden = deferredAssessment;
      setBusy(false);
      if (deferredAssessment) reviewAnswer(pendingAnswer);
      else await evaluateSavedAnswer(pendingAnswer);
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
      for (const item of writingFields) item.field.disabled = item.disabled;
      if (statusPoll === null && submitButton && !submitButton.hidden) setBusy(false);
    }
  });
})();
