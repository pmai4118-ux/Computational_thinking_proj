(() => {
  "use strict";
  const page = document.querySelector("[data-workspace]");
  const form = document.querySelector("#answer-form");
  if (!page || !form) return;

  const api = window.InterviewApi;
  const sessionId = page.dataset.sessionId;
  const questionId = page.dataset.questionId;
  const questionVersion = Number(page.dataset.questionVersion);
  const index = Number(page.dataset.currentIndex || "0");
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
  const label = document.querySelector("#draft-label") || document.querySelector("[data-draft-label]");
  const counter = document.querySelector("#answer-counter");
  const activity = window.InterviewActivity?.mount("workspace-activity", status);

  const outlineWrap = document.querySelector("#argument-outline-wrap");
  const boxesContainer = document.querySelector("#argument-boxes-container");
  const addBoxButton = document.querySelector("#add-argument-box");
  const canonicalWrap = document.querySelector("#canonical-answer-wrap");
  const viewSwitch = document.querySelector("#editor-view-switch");
  const modeOutlineBtn = document.querySelector("#mode-outline-btn");
  const modePlainBtn = document.querySelector("#mode-plain-btn");
  const toolbar = document.querySelector("#editor-toolbar");

  const key = `submission:${sessionId}:${questionId}`;
  const draftKey = `draft:${sessionId}:${questionId}`;
  const structuredDraftKey = `draft:v2:${sessionId}:${questionId}:v${questionVersion}`;
  const codingLang = (codingPanel && codingPanel.dataset && codingPanel.dataset.codingLang) || "python";
  const starterCode = (codingPanel && codingPanel.dataset && codingPanel.dataset.starterCode) || "";
  const DEFAULT_BOX_TITLES = [
    "Phân tích vấn đề",
    "Phương án và đánh đổi",
    "Cách xác minh",
  ];

  const storage = {
    get(storageKey) {
      try {
        const store = window.sessionStorage || (typeof sessionStorage !== "undefined" ? sessionStorage : null);
        return store ? store.getItem(storageKey) : null;
      } catch (_err) {
        return null;
      }
    },
    set(storageKey, value) {
      try {
        const store = window.sessionStorage || (typeof sessionStorage !== "undefined" ? sessionStorage : null);
        if (!store) return false;
        store.setItem(storageKey, value);
        return true;
      } catch (_err) {
        return false;
      }
    },
    remove(storageKey) {
      try {
        const store = window.sessionStorage || (typeof sessionStorage !== "undefined" ? sessionStorage : null);
        if (store) store.removeItem(storageKey);
      } catch (_err) {
        /* Ignore storage errors. */
      }
    },
  };

  let timer = null;
  let saveChain = Promise.resolve();
  let draftDirty = false;
  let submissionUncertain = false;
  let busy = false;
  let leaving = false;
  let outlineBoxes = [];
  let outlineActive = false;
  let editorMode = "outline";
  let lastFocusedTextarea = null;

  function hasCodeEditor() {
    return Boolean(codeField && typeof codeField.value === "string");
  }

  function composeAnswerText() {
    const prose = field ? (field.value || "") : "";
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
    if (!hasCodeEditor() || !field || !field.value) return;
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

  function showError(message) {
    if (!error) return;
    error.textContent = message;
    error.hidden = false;
    error.focus();
  }

  function updateCounter() {
    if (!counter) return;
    const combined = composeAnswerText();
    counter.textContent = `${combined.length.toLocaleString("vi-VN")} / 20.000 ký tự`;
    if (counter.classList) {
      counter.classList.toggle("workspace-counter--over", combined.length > 20000);
    }
    updateCodeMeta();
  }

  function setBusy(value) {
    busy = value;
    if (!value) {
      activity?.stop();
      for (const btn of [submit, exit, next]) {
        window.InterviewActivity?.buttonBusy(btn, false);
      }
    }
    if (submit) submit.disabled = value;
    if (exit) exit.disabled = value || submissionUncertain;
    if (next) next.disabled = value;
    if (addBoxButton) addBoxButton.disabled = value;
    const locked = value || submissionUncertain || Boolean(page.dataset.answerId);
    if (field) field.readOnly = locked;
    if (hasCodeEditor()) codeField.readOnly = locked;
  }

  function submissionId(text) {
    let pending;
    try { pending = JSON.parse(storage.get(key) || "null"); } catch (_) { pending = null; }
    if (pending && pending.text === text && pending.id) return pending.id;
    const id = window.crypto && window.crypto.randomUUID
      ? window.crypto.randomUUID()
      : `subm-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    storage.set(key, JSON.stringify({ id, text }));
    return id;
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

  function syncFromOutlineBoxes() {
    if (!outlineActive || !field || field.readOnly) return;
    field.value = serializeOutlineBoxes(outlineBoxes);
    storage.set(
      structuredDraftKey,
      JSON.stringify({ version: 2, boxes: outlineBoxes })
    );
    storage.set(draftKey, field.value);
    scheduleDraftSave();
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
        removeBtn.className = "btn btn--ghost argument-box__remove";
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
    } catch (_err) {
      loadedStructured = null;
    }

    if (loadedStructured) {
      outlineBoxes = loadedStructured;
      if (field) field.value = serializeOutlineBoxes(outlineBoxes);
    } else if (initialPlainDraft !== null && initialPlainDraft !== "") {
      outlineBoxes = [{ title: "", content: initialPlainDraft }];
      if (field) field.value = initialPlainDraft;
    } else if (field && field.value && field.value.trim()) {
      outlineBoxes = [{ title: "", content: field.value }];
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
        if (editorMode === "plain" && field) {
          const plain = field.value;
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
        if (outlineActive && field && !field.readOnly) {
          field.value = serializeOutlineBoxes(outlineBoxes);
        }
        setEditorViewMode("plain");
        if (field) field.focus();
      });
    }

    if (toolbar) {
      const insertButtons = document.querySelectorAll("[data-insert-snippet]");
      for (const btn of insertButtons) {
        btn.addEventListener("click", () => {
          const snippet = btn.getAttribute("data-insert-snippet") || "";
          const target = editorMode === "plain"
            ? field
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
          if (target === field) {
            storage.set(draftKey, field.value);
            scheduleDraftSave();
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

  restoreSplitDraft();
  if (!page.dataset.answerId) {
    const restoredPlain = (!field || !field.value) ? storage.get(draftKey) : null;
    if (restoredPlain !== null && field) {
      field.value = restoredPlain;
      restoreSplitDraft();
    }
    initOutlineEditor({ initialPlainDraft: restoredPlain });
  } else {
    disableOutlineForReadOnlyServerAnswer();
  }
  let savedText = composeAnswerText();

  function saveDraft(text) {
    if (page.dataset.answerId) return Promise.resolve();
    saveChain = saveChain.catch(() => {}).then(async () => {
      if (!api || typeof api.saveDraft !== "function") {
        if (label) label.textContent = "Script trình duyệt chưa đồng bộ. Hãy tải lại trang (Ctrl+F5).";
        throw new Error("Phiên bản script trình duyệt đã cũ; hãy nhấn Ctrl+F5 để tải lại trang.");
      }
      if (label) label.textContent = "Đang lưu bản nháp…";
      await api.saveDraft(sessionId, { question_id: questionId, question_version: questionVersion, text });
      savedText = text;
      if (composeAnswerText() === text) draftDirty = false;
      if (label) label.textContent = composeAnswerText() === text ? "Đã lưu bản nháp" : "Đang lưu bản nháp…";
    });
    return saveChain;
  }

  async function flushDraft() {
    if (typeof window.clearTimeout === "function") window.clearTimeout(timer);
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
    if (error) error.hidden = true;
    draftDirty = true;
    if (label) label.textContent = "Bản nháp chưa lưu xong";
    if (typeof window.clearTimeout === "function") window.clearTimeout(timer);
    const text = composeAnswerText();
    if (typeof window.setTimeout === "function") {
      timer = window.setTimeout(() => saveDraft(text).catch(() => {
        if (label) label.textContent = "Chưa lưu được bản nháp. Hãy thử Lưu và thoát hoặc sao chép nội dung.";
      }), 600);
    }
  }

  function handleCodeKeydown(event) {
    if (!hasCodeEditor() || codeField.readOnly) return;
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

  if (field) {
    field.addEventListener("input", () => {
      if (!field.readOnly) {
        storage.set(draftKey, field.value);
        if (outlineActive && editorMode === "plain") {
          storage.remove(structuredDraftKey);
        }
      }
      scheduleDraftSave();
    });
  }
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

  if (typeof window.addEventListener === "function") {
    window.addEventListener("beforeunload", (event) => {
      if (!leaving && !page.dataset.answerId && (busy || draftDirty || composeAnswerText() !== savedText)) {
        event.preventDefault(); event.returnValue = "";
      }
    });
  }
  if (exit) {
    exit.addEventListener("click", async (event) => {
      event.preventDefault();
      if (busy) return;
      setBusy(true);
      if (error) error.hidden = true;
      window.InterviewActivity?.buttonBusy(exit, true);
      activity?.start({ kind: "saving", title: "Đang lưu bản nháp", description: "Lưu nội dung hiện tại lên máy chủ để bạn có thể tiếp tục sau." });
      try { await flushDraft(); leaving = true; window.location.assign("/"); }
      catch (err) { showError(`${err.message || "Chưa lưu được bản nháp."} Nội dung vẫn ở ô trả lời; hãy thử lại.`); }
      finally { setBusy(false); }
    });
  }
  if (next) {
    next.addEventListener("click", async (event) => {
      event.preventDefault();
      if (busy) return;
      setBusy(true);
      if (error) error.hidden = true;
      window.InterviewActivity?.buttonBusy(next, true);
      activity?.start({ kind: "loading", title: "Đang chuyển câu hỏi", description: "Chuẩn bị câu hỏi tiếp theo trong phiên." });
      try { await advance(); }
      catch (err) { showError(`${err.message || "Chưa thể chuyển câu."} Bài đã gửi vẫn được giữ.`); }
      finally { setBusy(false); }
    });
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy || !submit) return;
    if (outlineActive && editorMode === "outline" && field && !field.readOnly) {
      field.value = serializeOutlineBoxes(outlineBoxes);
    }
    const text = composeAnswerText();
    if (!text.trim()) {
      showError("Vui lòng nhập câu trả lời hoặc mã nguồn trước khi gửi.");
      if (outlineActive && editorMode === "outline" && boxesContainer) {
        const firstBoxInput = boxesContainer.querySelector(".argument-box__textarea");
        if (firstBoxInput) firstBoxInput.focus();
        else if (field) field.focus();
      } else if (field) {
        field.focus();
      }
      return;
    }
    if (text.length > 20000) {
      showError("Tổng độ dài giải thích và mã nguồn vượt quá 20.000 ký tự.");
      if (field) field.focus();
      return;
    }
    setBusy(true);
    if (error) error.hidden = true;
    window.InterviewActivity?.buttonBusy(submit, true);
    if (status) {
      status.hidden = false;
      status.textContent = "Đang lưu câu trả lời…";
    }
    activity?.start({ kind: "saving", title: "Đang lưu câu trả lời của bạn", description: "Bản nháp đã lưu. Chờ máy chủ xác nhận trước khi chuyển sang bước tiếp theo." });
    let submissionSent = false;
    try {
      await flushDraft();
      submissionSent = true;
      await api.submitAnswer(sessionId, { question_id: questionId, question_version: questionVersion, client_submission_id: submissionId(text), text });
      page.dataset.answerId = "saved";
      storage.remove(draftKey);
      storage.remove(structuredDraftKey);
      storage.remove(key);
      if (field) field.readOnly = true;
      if (hasCodeEditor()) codeField.readOnly = true;
      disableOutlineForReadOnlyServerAnswer();
      submit.hidden = true;
      await advance();
    } catch (err) {
      showError(`${err.message || "Chưa thể lưu hoặc chuyển câu."} Nội dung vẫn được giữ; hãy thử lại hoặc tải lại trang.`);
      if (submissionSent) {
        submissionUncertain = true;
        submit.hidden = true;
        if (status) {
          status.textContent = "Tải lại trang để kiểm tra bài đã gửi và tiếp tục. Bản nháp đã được lưu trước khi gửi.";
          const reload = document.createElement("button");
          reload.type = "button";
          reload.className = "btn btn--secondary";
          reload.textContent = "Tải lại phiên";
          reload.addEventListener("click", () => { leaving = true; window.location.reload(); });
          status.insertAdjacentElement("afterend", reload);
        }
      } else if (status) {
        status.textContent = "Chưa gửi được câu trả lời. Hãy thử lại.";
      }
    } finally { setBusy(false); }
  });
  updateCounter();
})();
