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
  const codingPanel = document.querySelector("[data-coding-panel]");
  const codingBody = document.querySelector("#coding-box-body");
  const codeField = document.querySelector("#answer-code");
  const toggleCodeBtn = document.querySelector("#toggle-coding-box");
  const starterCodeBtn = document.querySelector("#insert-starter-code");
  const clearCodeBtn = document.querySelector("#clear-code");
  const codeLineCount = document.querySelector("#code-line-count");
  const submit = document.querySelector("#submit-answer");
  const exit = document.querySelector("#save-exit");
  const next = document.querySelector("#continue-saved");
  const status = document.querySelector("#workspace-status");
  const error = document.querySelector("#workspace-error");
  const expiredRecovery = document.querySelector("#session-expired-recovery");
  const label = document.querySelector("#draft-label");
  const counter = document.querySelector("#answer-counter");
  const key = `submission:${sessionId}:${questionId}`;
  const codingLang = (codingPanel && codingPanel.dataset && codingPanel.dataset.codingLang) || "python";
  const starterCode = (codingPanel && codingPanel.dataset && codingPanel.dataset.starterCode) || "";
  let timer = null;
  let saveChain = Promise.resolve();
  let draftDirty = false;
  let submissionUncertain = false;
  let busy = false;
  let leaving = false;

  function hasCodeEditor() {
    return Boolean(codeField && typeof codeField.value === "string");
  }

  function composeAnswerText() {
    const prose = field.value || "";
    const code = hasCodeEditor() ? codeField.value : "";
    if (!code.trim()) return prose;
    const cleanCode = code.replace(/\s+$/, "");
    const block = `\`\`\`${codingLang}\n${cleanCode}\n\`\`\``;
    return prose.trim() ? `${prose.replace(/\s+$/, "")}\n\n${block}` : block;
  }

  function setCodingPanelOpen(open) {
    if (!codingBody) return;
    codingBody.hidden = !open;
    if (toggleCodeBtn) {
      if (typeof toggleCodeBtn.setAttribute === "function") {
        toggleCodeBtn.setAttribute("aria-expanded", open ? "true" : "false");
      }
      toggleCodeBtn.textContent = open ? "Ẩn khung viết mã" : "Mở khung viết mã";
    }
  }

  function restoreSplitDraft() {
    if (!hasCodeEditor() || !field.value) return;
    const raw = field.value;
    const match = raw.match(/(?:^|\r?\n\r?\n)```([A-Za-z0-9_+-]*)\r?\n([\s\S]*?)\r?\n```\s*$/);
    if (!match) return;
    const extractedCode = match[2];
    const prosePart = raw.slice(0, match.index).replace(/\s+$/, "");
    field.value = prosePart;
    codeField.value = extractedCode;
    setCodingPanelOpen(true);
  }

  function updateCodeMeta() {
    if (!codeLineCount || !hasCodeEditor()) return;
    const raw = codeField.value;
    const lines = raw ? raw.split(/\r?\n/).length : 0;
    codeLineCount.textContent = `${lines} dòng mã`;
  }

  function showError(message, err) {
    error.textContent = message;
    error.hidden = false;
    if (expiredRecovery && err && (err.code === "SESSION_EXPIRED" || err.status === 410)) {
      expiredRecovery.hidden = false;
    }
    if (typeof error.focus === "function") {
      error.focus();
    }
  }

  function updateCounter() {
    const combined = composeAnswerText();
    counter.textContent = `${combined.length.toLocaleString("vi-VN")} / 20.000 ký tự`;
    updateCodeMeta();
  }

  function setBusy(value) {
    busy = value;
    if (submit) submit.disabled = value;
    if (exit) exit.disabled = value || submissionUncertain;
    if (next) next.disabled = value;
    const locked = value || submissionUncertain || Boolean(page.dataset.answerId);
    field.readOnly = locked;
    if (hasCodeEditor()) codeField.readOnly = locked;
  }

  function submissionId(text) {
    let pending;
    try { pending = JSON.parse(sessionStorage.getItem(key) || "null"); } catch (_) { pending = null; }
    if (pending && pending.text === text && pending.id) return pending.id;
    const id = window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `subm-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    try { sessionStorage.setItem(key, JSON.stringify({ id, text })); } catch (_) { /* Continue with this submission ID. */ }
    return id;
  }

  restoreSplitDraft();
  let savedText = composeAnswerText();

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
      if (composeAnswerText() === text) draftDirty = false;
      label.textContent = composeAnswerText() === text ? "Đã lưu bản nháp" : "Đang lưu bản nháp…";
    });
    return saveChain;
  }

  async function flushDraft() {
    window.clearTimeout(timer);
    try { await saveChain; } catch (_) { /* Retry the latest text below. */ }
    if (!page.dataset.answerId) await saveDraft(composeAnswerText());
  }

  async function advance() {
    const session = await api.nextQuestion(sessionId, index);
    leaving = true;
    const done = session.progress.answered_count >= session.progress.total_questions;
    window.location.assign(`/sessions/${encodeURIComponent(sessionId)}${done ? "/summary" : ""}`);
  }

  function scheduleDraftSave() {
    updateCounter();
    error.hidden = true;
    draftDirty = true;
    label.textContent = "Bản nháp chưa lưu xong";
    window.clearTimeout(timer);
    const text = composeAnswerText();
    timer = window.setTimeout(() => saveDraft(text).catch(() => {
      label.textContent = "Chưa lưu được bản nháp. Hãy thử Lưu và thoát hoặc sao chép nội dung.";
    }), 600);
  }

  function exitCodeEditorFocus() {
    const targets = [submit, next, exit, field];
    for (const target of targets) {
      if (target && !target.hidden && !target.disabled && typeof target.focus === "function") {
        target.focus();
        return;
      }
    }
    if (typeof codeField.blur === "function") {
      codeField.blur();
    }
  }

  function handleCodeKeydown(event) {
    if (!hasCodeEditor()) return;

    // WCAG 2.1.2: Escape cleanly exits the Tab-indented code editor without keyboard trap.
    if (event.key === "Escape") {
      if (typeof event.preventDefault === "function") event.preventDefault();
      exitCodeEditorFocus();
      return;
    }

    if (codeField.readOnly) return;
    const start = typeof codeField.selectionStart === "number" ? codeField.selectionStart : codeField.value.length;
    const end = typeof codeField.selectionEnd === "number" ? codeField.selectionEnd : start;
    const value = codeField.value;

    if (event.key === "Tab") {
      event.preventDefault();
      const lineStart = value.lastIndexOf("\n", start - 1) + 1;
      if (event.shiftKey) {
        const selected = value.slice(lineStart, end);
        const lines = selected.split("\n");
        let removedFirst = 0;
        let totalRemoved = 0;
        const updated = lines.map((line, idx) => {
          const match = line.match(/^( {1,4}|\t)/);
          if (!match) return line;
          const len = match[0].length;
          if (idx === 0) removedFirst = len;
          totalRemoved += len;
          return line.slice(len);
        }).join("\n");
        codeField.value = value.slice(0, lineStart) + updated + value.slice(end);
        codeField.selectionStart = Math.max(lineStart, start - removedFirst);
        codeField.selectionEnd = Math.max(codeField.selectionStart, end - totalRemoved);
      } else if (start !== end && value.slice(start, end).includes("\n")) {
        const selected = value.slice(lineStart, end);
        const lines = selected.split("\n");
        const updated = lines.map((line) => `    ${line}`).join("\n");
        codeField.value = value.slice(0, lineStart) + updated + value.slice(end);
        codeField.selectionStart = start + 4;
        codeField.selectionEnd = end + lines.length * 4;
      } else {
        codeField.value = `${value.slice(0, start)}    ${value.slice(end)}`;
        codeField.selectionStart = start + 4;
        codeField.selectionEnd = start + 4;
      }
      scheduleDraftSave();
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      const lineStart = value.lastIndexOf("\n", start - 1) + 1;
      const currentLine = value.slice(lineStart, start);
      const indentMatch = currentLine.match(/^([ \t]*)/);
      const baseIndent = indentMatch ? indentMatch[1] : "";
      const extraIndent = codingLang.toLowerCase() === "python" && currentLine.trimEnd().endsWith(":") ? "    " : "";
      const insertion = `\n${baseIndent}${extraIndent}`;
      codeField.value = value.slice(0, start) + insertion + value.slice(end);
      const caret = start + insertion.length;
      codeField.selectionStart = caret;
      codeField.selectionEnd = caret;
      scheduleDraftSave();
    }
  }

  field.addEventListener("input", scheduleDraftSave);
  if (hasCodeEditor()) {
    codeField.addEventListener("input", scheduleDraftSave);
    codeField.addEventListener("keydown", handleCodeKeydown);
  }
  if (toggleCodeBtn && codingBody) {
    toggleCodeBtn.addEventListener("click", () => {
      const opening = Boolean(codingBody.hidden);
      setCodingPanelOpen(opening);
      if (opening && hasCodeEditor() && typeof codeField.focus === "function") {
        codeField.focus();
      }
    });
  }
  if (starterCodeBtn && starterCode && hasCodeEditor()) {
    starterCodeBtn.addEventListener("click", () => {
      if (codeField.readOnly) return;
      setCodingPanelOpen(true);
      const current = codeField.value;
      codeField.value = current.trim() ? `${current.replace(/\s+$/, "")}\n\n${starterCode}` : starterCode;
      if (typeof codeField.focus === "function") codeField.focus();
      scheduleDraftSave();
    });
  }
  if (clearCodeBtn && hasCodeEditor()) {
    clearCodeBtn.addEventListener("click", () => {
      if (codeField.readOnly) return;
      codeField.value = "";
      scheduleDraftSave();
    });
  }

  window.addEventListener("beforeunload", (event) => {
    if (!leaving && !page.dataset.answerId && (busy || draftDirty || composeAnswerText() !== savedText)) {
      event.preventDefault(); event.returnValue = "";
    }
  });
  exit.addEventListener("click", async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); error.hidden = true;
    try { await flushDraft(); leaving = true; window.location.assign("/"); }
    catch (err) { showError(`${err.message || "Chưa lưu được bản nháp."} Nội dung vẫn ở ô trả lời; hãy thử lại.`, err); }
    finally { setBusy(false); }
  });
  if (next) next.addEventListener("click", async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); error.hidden = true;
    try { await advance(); } catch (err) { showError(`${err.message || "Chưa thể chuyển câu."} Bài đã gửi vẫn được giữ.`, err); }
    finally { setBusy(false); }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy || !submit) return;
    const text = composeAnswerText();
    if (!text.trim()) { showError("Vui lòng nhập câu trả lời hoặc mã nguồn trước khi gửi."); field.focus(); return; }
    if (text.length > 20000) { showError("Tổng độ dài giải thích và mã nguồn vượt quá 20.000 ký tự."); field.focus(); return; }
    setBusy(true); error.hidden = true;
    status.hidden = false; status.textContent = "Đang lưu câu trả lời…";
    let submissionSent = false;
    try {
      await flushDraft();
      submissionSent = true;
      await api.submitAnswer(sessionId, { question_id: questionId, question_version: questionVersion, client_submission_id: submissionId(text), text });
      page.dataset.answerId = "saved";
      field.readOnly = true;
      if (hasCodeEditor()) codeField.readOnly = true;
      submit.hidden = true;
      await advance();
    } catch (err) {
      showError(`${err.message || "Chưa thể lưu hoặc chuyển câu."} Nội dung vẫn được giữ; hãy thử lại hoặc tải lại trang.`, err);
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
