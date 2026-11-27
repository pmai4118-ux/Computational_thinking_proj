(() => {
  "use strict";
  const page = document.querySelector("[data-workspace]");
  const form = document.querySelector("#answer-form");
  if (!page || !form) return;
  const api = window.InterviewApi;
  const sessionId = page.dataset.sessionId;
  const questionId = page.dataset.questionId;
  const questionVersion = Number(page.dataset.questionVersion);
  const index = Number(page.dataset.currentIndex);
  const field = document.querySelector("#answer-text");
  const submit = document.querySelector("#submit-answer");
  const exit = document.querySelector("#save-exit");
  const next = document.querySelector("#continue-saved");
  const status = document.querySelector("#workspace-status");
  const error = document.querySelector("#workspace-error");
  const label = document.querySelector("#draft-label");
  const counter = document.querySelector("#answer-counter");
  const key = `submission:${sessionId}:${questionId}`;
  let timer = null;
  let saveChain = Promise.resolve();
  let savedText = field.value;
  let draftDirty = false;
  let submissionUncertain = false;
  let busy = false;
  let leaving = false;

  function showError(message) {
    error.textContent = message;
    error.hidden = false;
    error.focus();
  }
  function updateCounter() { counter.textContent = `${field.value.length.toLocaleString("vi-VN")} / 20.000 ký tự`; }
  function setBusy(value) {
    busy = value;
    if (submit) submit.disabled = value;
    if (exit) exit.disabled = value || submissionUncertain;
    if (next) next.disabled = value;
    field.readOnly = value || submissionUncertain || Boolean(page.dataset.answerId);
  }
  function submissionId(text) {
    let pending;
    try { pending = JSON.parse(sessionStorage.getItem(key) || "null"); } catch (_) { pending = null; }
    if (pending && pending.text === text && pending.id) return pending.id;
    const id = window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `subm-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    try { sessionStorage.setItem(key, JSON.stringify({ id, text })); } catch (_) { /* Continue with this submission ID. */ }
    return id;
  }
  function saveDraft(text) {
    if (page.dataset.answerId) return Promise.resolve();
    saveChain = saveChain.catch(() => {}).then(async () => {
      if (!api || typeof api.saveDraft !== "function") {
        label.textContent = "Script trình duyệt chưa đồng bộ. Hãy tải lại trang (Ctrl+F5).";
        throw new Error("Phiên bản script trình duyệt đã cũ; hãy nhấn Ctrl+F5 để tải lại trang.");
      }
      label.textContent = "Đang lưu bản nháp…";
      await api.saveDraft(sessionId, { question_id: questionId, question_version: questionVersion, text });
      savedText = text;
      if (field.value === text) draftDirty = false;
      label.textContent = field.value === text ? "Đã lưu bản nháp" : "Đang lưu bản nháp…";
    });
    return saveChain;
  }
  async function flushDraft() {
    window.clearTimeout(timer);
    try { await saveChain; } catch (_) { /* Retry the latest text below. */ }
    if (!page.dataset.answerId) await saveDraft(field.value);
  }
  async function advance() {
    const session = await api.nextQuestion(sessionId, index);
    leaving = true;
    const done = session.progress.answered_count >= session.progress.total_questions;
    window.location.assign(`/sessions/${encodeURIComponent(sessionId)}${done ? "/summary" : ""}`);
  }
  field.addEventListener("input", () => {
    updateCounter(); error.hidden = true;
    draftDirty = true;
    label.textContent = "Bản nháp chưa lưu xong";
    window.clearTimeout(timer);
    const text = field.value;
    timer = window.setTimeout(() => saveDraft(text).catch(() => {
      label.textContent = "Chưa lưu được bản nháp. Hãy thử Lưu và thoát hoặc sao chép nội dung.";
    }), 600);
  });
  window.addEventListener("beforeunload", (event) => {
    if (!leaving && !page.dataset.answerId && (busy || draftDirty || field.value !== savedText)) {
      event.preventDefault(); event.returnValue = "";
    }
  });
  exit.addEventListener("click", async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); error.hidden = true;
    try { await flushDraft(); leaving = true; window.location.assign("/"); }
    catch (err) { showError(`${err.message || "Chưa lưu được bản nháp."} Nội dung vẫn ở ô trả lời; hãy thử lại.`); }
    finally { setBusy(false); }
  });
  if (next) next.addEventListener("click", async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); error.hidden = true;
    try { await advance(); } catch (err) { showError(`${err.message || "Chưa thể chuyển câu."} Bài đã gửi vẫn được giữ.`); }
    finally { setBusy(false); }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy || !submit) return;
    const text = field.value;
    if (!text.trim()) { showError("Vui lòng nhập câu trả lời trước khi gửi."); field.focus(); return; }
    setBusy(true); error.hidden = true;
    status.hidden = false; status.textContent = "Đang lưu câu trả lời…";
    let submissionSent = false;
    try {
      await flushDraft();
      submissionSent = true;
      await api.submitAnswer(sessionId, { question_id: questionId, question_version: questionVersion, client_submission_id: submissionId(text), text });
      page.dataset.answerId = "saved";
      field.readOnly = true;
      submit.hidden = true;
      await advance();
    } catch (err) {
      showError(`${err.message || "Chưa thể lưu hoặc chuyển câu."} Nội dung vẫn được giữ; hãy thử lại hoặc tải lại trang.`);
      if (submissionSent) {
        submissionUncertain = true;
        submit.hidden = true;
        status.textContent = "Tải lại trang để kiểm tra bài đã gửi và tiếp tục. Bản nháp đã được lưu trước khi gửi.";
        const reload = document.createElement("button");
        reload.type = "button";
        reload.className = "btn btn--secondary";
        reload.textContent = "Tải lại phiên";
        reload.addEventListener("click", () => { leaving = true; window.location.reload(); });
        status.insertAdjacentElement("afterend", reload);
      } else {
        status.textContent = "Chưa gửi được câu trả lời. Hãy thử lại.";
      }
    } finally { setBusy(false); }
  });
  updateCounter();
})();
