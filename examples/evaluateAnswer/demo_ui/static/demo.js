const answerInput = document.querySelector("#answer-text");
const evaluateButton = document.querySelector("#evaluate-button");
const previewButton = document.querySelector("#preview-button");
const loadExampleButton = document.querySelector("#load-example-button");
const exampleSelect = document.querySelector("#example-select");
const questionSelect = document.querySelector("#question-select");
const countLabel = document.querySelector("#character-count");
const liveStatus = document.querySelector("#live-status");
const resultStatus = document.querySelector("#result-status");
const reportContent = document.querySelector("#report-content");
const providerIndicator = document.querySelector("#provider-indicator");
const DEFAULT_QUESTION_ID = "question.inventoryRace.poc";

let liveConfigured = false;
let loadedExample = null;
let busy = false;
let activeProviderLabel = "Antigravity";
let displayedAnswerText = null;
let currentQuestionId = DEFAULT_QUESTION_ID;
let currentQuestionExamples = [];
let currentQuestion = null;
const answerDrafts = new Map();

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error("Không đọc được phản hồi từ máy chủ. Vui lòng thử lại.");
  }
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : "Nội dung gửi lên chưa hợp lệ hoặc máy chủ gặp lỗi. Vui lòng thử lại.");
  }
  return body;
}

function appendText(parent, tagName, className, text) {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  node.textContent = text;
  parent.append(node);
  return node;
}

function refreshControls() {
  countLabel.textContent = `${answerInput.value.length.toLocaleString("vi-VN")} / 40.000`;
  evaluateButton.disabled = busy || !liveConfigured || !answerInput.value.trim();
  previewButton.hidden = !loadedExample?.canPreview;
  previewButton.disabled = busy || !loadedExample?.canPreview || loadedExample.questionId !== currentQuestionId || answerInput.value !== loadedExample.answerText;
  loadExampleButton.disabled = busy;
  exampleSelect.disabled = busy;
  questionSelect.disabled = busy;
  answerInput.readOnly = busy;
}

function setBusy(isBusy, message = "") {
  busy = isBusy;
  liveStatus.textContent = message;
  liveStatus.dataset.kind = "";
  refreshControls();
}

function showMessage(kind, title, message) {
  displayedAnswerText = null;
  reportContent.hidden = true;
  reportContent.replaceChildren();
  resultStatus.replaceChildren();
  resultStatus.dataset.kind = kind;
  appendText(resultStatus, "span", "empty-icon", kind === "error" ? "!" : "✎");
  appendText(resultStatus, "h3", "", title);
  appendText(resultStatus, "p", "", message);
  resultStatus.hidden = false;
}

function invalidateChangedAnswer() {
  if (displayedAnswerText !== null && answerInput.value !== displayedAnswerText) {
    showMessage("empty", "Câu trả lời đã thay đổi", "Đánh giá lại câu trả lời hiện tại hoặc tải một mẫu để xem kết quả ghi sẵn.");
    providerIndicator.textContent = "Chưa đánh giá câu trả lời hiện tại";
  }
}

function translatedStatus(status) {
  return {
    met: "Đạt",
    unmet: "Chưa đạt",
    insufficientEvidence: "Chưa đủ bằng chứng",
  }[status] || status;
}

function populateQuestionSelect(questions) {
  if (!Array.isArray(questions) || !questions.length) return;
  const selectedId = questionSelect.value || DEFAULT_QUESTION_ID;
  questionSelect.replaceChildren();
  for (const question of questions) {
    const option = document.createElement("option");
    option.value = question.questionId;
    option.textContent = question.title;
    questionSelect.append(option);
  }
  questionSelect.value = questions.some((question) => question.questionId === selectedId)
    ? selectedId
    : DEFAULT_QUESTION_ID;
}

function populateExampleSelect(examples) {
  if (!Array.isArray(examples) || !examples.length) return;
  exampleSelect.replaceChildren();
  for (const example of examples) {
    const option = document.createElement("option");
    option.value = example.caseName;
    option.textContent = example.label;
    option.dataset.canPreview = String(Boolean(example.canPreview));
    exampleSelect.append(option);
  }
  exampleSelect.value = examples[0].caseName;
}

function renderQuestion(question) {
  currentQuestion = question;
  currentQuestionId = question.questionId || DEFAULT_QUESTION_ID;
  currentQuestionExamples = Array.isArray(question.examples) ? question.examples : [];
  if (question.title) document.querySelector("#question-heading").textContent = question.title;
  document.querySelector("#question-prompt").textContent = question.prompt;
  document.querySelector("#level-badge").textContent = question.expectedLevel;
  const requirements = document.querySelector("#requirements-list");
  requirements.replaceChildren();
  for (const requirement of question.requirements || []) appendText(requirements, "li", "", requirement);

  const codeBlock = document.querySelector("#question-code");
  if (question.code) {
    let codeNode = codeBlock.children[0];
    if (!codeNode) {
      codeNode = document.createElement("code");
      codeBlock.append(codeNode);
    }
    codeNode.textContent = question.code;
    codeBlock.hidden = false;
  } else {
    codeBlock.hidden = true;
    if (codeBlock.children[0]) codeBlock.children[0].textContent = "";
  }

  document.querySelector("#question-source").textContent = question.sourceLabel || "Bài tập minh họa; nội dung chưa được duyệt làm chuẩn đánh giá.";
  document.querySelector("#question-badge-label").textContent = question.reviewStatus === "approved"
    ? "Câu hỏi đã được review"
    : "Dữ liệu demo · đang chờ review";
  document.querySelector("#example-note").textContent = currentQuestionExamples.some((example) => example.canPreview)
    ? "Bản ghi chỉ khớp với nguyên văn câu trả lời mẫu; mở bản ghi không gọi AI."
    : "Mẫu Task 3 chỉ nạp câu trả lời; chưa có bản ghi để xem. Đánh giá trực tiếp vẫn là PoC, chưa phải benchmark đã duyệt.";
  populateExampleSelect(currentQuestionExamples);
}

function renderCriterion(parent, criterion, check) {
  const block = document.createElement("section");
  block.className = "criterion";
  const titleRow = document.createElement("div");
  titleRow.className = "criterion-title-row";
  appendText(titleRow, "span", "criterion-title", criterion.description);
  const state = appendText(titleRow, "span", "criterion-state", translatedStatus(check.status));
  state.dataset.state = check.status;
  block.append(titleRow);

  for (const evidenceItem of check.evidence) {
    const evidence = document.createElement("p");
    evidence.className = "evidence";
    if (evidenceItem.quote) {
      const quote = document.createElement("q");
      quote.textContent = evidenceItem.quote;
      evidence.append(quote);
    }
    appendText(evidence, "span", "", evidenceItem.observation);
    appendText(evidence, "span", "evidence-location", `Nguồn: ${evidenceItem.location}`);
    block.append(evidence);
  }
  parent.append(block);
}

function renderReport(report) {
  displayedAnswerText = report.inputs.answer.originalText;
  resultStatus.hidden = true;
  resultStatus.replaceChildren();
  reportContent.replaceChildren();
  reportContent.hidden = false;

  const meta = document.createElement("div");
  meta.className = "report-meta";
  const isRecorded = report.providerName === "recorded";
  const providerLabel = report.providerName === "antigravity" ? "Antigravity" : "Gemini API";
  appendText(meta, "span", "report-chip", isRecorded ? "Bản ghi demo · không gọi AI" : `${providerLabel} · đánh giá trực tiếp`);
  if (report.inputs.exampleOnly) appendText(meta, "span", "report-chip provisional", "Ví dụ đang chờ review");
  reportContent.append(meta);

  const rubrics = new Map(report.inputs.rubrics.map((rubric) => [rubric.rubricId, rubric]));
  const feedback = new Map(report.feedbackItems.map((item) => [item.resultId, item]));
  for (const result of report.results) {
    const rubric = rubrics.get(result.rubricId);
    if (!rubric) continue;
    const card = document.createElement("section");
    card.className = "rubric-result";
    const top = document.createElement("div");
    top.className = "rubric-top";
    appendText(top, "h3", "", rubric.competency);
    const maxScore = Math.max(...rubric.scoreLevels.map((level) => level.value));
    const scoreLabel = result.score === null ? "Chưa đủ dữ liệu" : `${result.score} / ${maxScore}`;
    appendText(top, "span", `score${result.score === null ? " ungraded" : ""}`, scoreLabel);
    card.append(top);

    const criteria = new Map(rubric.criteria.map((item) => [item.criterionId, item]));
    for (const check of result.criterionChecks) {
      const criterion = criteria.get(check.criterionId);
      if (criterion) renderCriterion(card, criterion, check);
    }

    const feedbackItem = feedback.get(result.resultId);
    if (feedbackItem) {
      const feedbackBlock = document.createElement("div");
      feedbackBlock.className = "feedback-block";
      appendText(feedbackBlock, "h3", "", "Gợi ý cải thiện");
      appendText(feedbackBlock, "p", "", feedbackItem.explanation);
      if (feedbackItem.identifiedIssues.length) {
        const issues = document.createElement("ul");
        for (const issue of feedbackItem.identifiedIssues) appendText(issues, "li", "", issue);
        feedbackBlock.append(issues);
      }
      card.append(feedbackBlock);
    }
    reportContent.append(card);
  }

  appendText(reportContent, "p", "provider-line", `Model: ${report.modelName} · Prompt: ${report.promptVersion}`);
  providerIndicator.textContent = isRecorded ? "Đang xem kết quả ghi sẵn" : `Đã nhận kết quả từ ${providerLabel}`;
}

async function loadInitialContent() {
  try {
    let questions = null;
    try {
      questions = await requestJson("/api/questions");
    } catch {
      // Keep the static selector options if the catalog endpoint is unavailable.
    }
    populateQuestionSelect(questions);
    const selectedId = questionSelect.value || DEFAULT_QUESTION_ID;
    const questionUrl = selectedId === DEFAULT_QUESTION_ID
      ? "/api/question"
      : `/api/question?questionId=${encodeURIComponent(selectedId)}`;
    const [question, status] = await Promise.all([requestJson(questionUrl), requestJson("/api/status")]);
    renderQuestion(question);
    questionSelect.value = currentQuestionId;
    liveConfigured = status.liveEvaluationConfigured;
    activeProviderLabel = status.providerName === "antigravity" ? "Antigravity" : "Gemini API";
    document.querySelector("#runtime-caption").textContent = status.providerName === "antigravity"
      ? "Dùng hạn mức tài khoản Antigravity"
      : "Gọi Gemini bằng API key";
    if (liveConfigured) {
      liveStatus.textContent = `${activeProviderLabel} · ${status.modelName}. ${status.providerName === "antigravity" ? "Dùng tài khoản Google đã đăng nhập qua agy." : "Đã cấu hình API key trên máy chủ."}`;
      liveStatus.dataset.kind = "success";
    } else {
      liveStatus.textContent = `Chưa sẵn sàng dùng ${activeProviderLabel}. Bạn vẫn có thể xem các câu trả lời mẫu ghi sẵn.`;
      liveStatus.dataset.kind = "";
    }
    refreshControls();
  } catch (error) {
    liveStatus.textContent = `Không tải được nội dung: ${error.message}`;
    liveStatus.dataset.kind = "error";
  }
}

questionSelect.addEventListener("change", async () => {
  const requestedId = questionSelect.value || DEFAULT_QUESTION_ID;
  if (requestedId === currentQuestionId) return;
  const previousId = currentQuestionId;
  answerDrafts.set(previousId, answerInput.value);
  setBusy(true, "Đang chuyển câu hỏi…");
  showMessage("loading", "Đang tải câu hỏi", "Đang nạp rubric và các câu trả lời mẫu tương ứng.");
  try {
    const question = await requestJson(`/api/question?questionId=${encodeURIComponent(requestedId)}`);
    renderQuestion(question);
    questionSelect.value = currentQuestionId;
    answerInput.value = answerDrafts.get(currentQuestionId) || "";
    loadedExample = null;
    showMessage("empty", "Đã đổi câu hỏi", "Câu trả lời cũ của từng câu hỏi được giữ riêng. Chọn một câu trả lời mẫu hoặc nhập câu trả lời mới.");
    providerIndicator.textContent = "Chưa đánh giá câu hỏi hiện tại";
    liveStatus.textContent = "Rubric và câu trả lời mẫu đã được đổi theo câu hỏi.";
    liveStatus.dataset.kind = "success";
  } catch (error) {
    questionSelect.value = previousId;
    showMessage("error", "Không tải được câu hỏi", error.message);
    liveStatus.textContent = "Câu trả lời đang nhập vẫn được giữ lại.";
    liveStatus.dataset.kind = "error";
  } finally {
    busy = false;
    refreshControls();
  }
});

answerInput.addEventListener("input", () => {
  answerDrafts.set(currentQuestionId, answerInput.value);
  invalidateChangedAnswer();
  refreshControls();
  if (loadedExample && answerInput.value !== loadedExample.answerText) {
    liveStatus.textContent = liveConfigured
      ? "Câu trả lời đã thay đổi; bản ghi mẫu không còn khớp. Có thể gửi để đánh giá trực tiếp."
      : "Câu trả lời đã thay đổi; cần cấu hình kết nối AI để đánh giá nội dung tự nhập.";
    liveStatus.dataset.kind = "";
  }
});

document.querySelector("#answer-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!answerInput.value.trim() || !liveConfigured) return;
  setBusy(true, "Đang gửi câu trả lời để đánh giá…");
  showMessage("loading", "Đang phân tích câu trả lời", `Đang chờ ${activeProviderLabel} đối chiếu câu trả lời với rubric và kiểm tra bằng chứng.`);
  providerIndicator.textContent = `Đang chờ ${activeProviderLabel}`;
  try {
    renderReport(await requestJson("/api/evaluate", {
      method: "POST",
      body: JSON.stringify({ questionId: currentQuestionId, answerText: answerInput.value }),
    }));
    liveStatus.textContent = "Đã hoàn tất đánh giá.";
    liveStatus.dataset.kind = "success";
  } catch (error) {
    showMessage("error", "Chưa thể đánh giá câu trả lời", error.message);
    liveStatus.textContent = "Câu trả lời vẫn được giữ lại. Bạn có thể thử lại hoặc xem một kết quả ghi sẵn.";
    liveStatus.dataset.kind = "error";
    providerIndicator.textContent = "Chưa có đánh giá";
  } finally {
    busy = false;
    refreshControls();
  }
});

loadExampleButton.addEventListener("click", async () => {
  setBusy(true, "Đang tải câu trả lời mẫu…");
  try {
    const caseName = exampleSelect.value;
    const query = currentQuestionId === DEFAULT_QUESTION_ID
      ? ""
      : `?questionId=${encodeURIComponent(currentQuestionId)}`;
    const sample = await requestJson(`/api/examples/${encodeURIComponent(caseName)}${query}`);
    const metadata = currentQuestionExamples.find((example) => example.caseName === caseName);
    loadedExample = {
      ...sample,
      questionId: sample.questionId || currentQuestionId,
      caseName: sample.caseName || caseName,
      canPreview: metadata?.canPreview ?? currentQuestionId === DEFAULT_QUESTION_ID,
    };
    answerInput.value = sample.answerText;
    answerDrafts.set(currentQuestionId, answerInput.value);
    invalidateChangedAnswer();
    if (displayedAnswerText === null) {
      showMessage(
        "empty",
        "Đã tải câu trả lời mẫu",
        loadedExample.canPreview
          ? "Chọn “Xem kết quả ghi sẵn” để mở bản ghi, hoặc “Đánh giá bằng AI” để đánh giá trực tiếp."
          : "Task 3 chưa có bản ghi điểm. Chọn “Đánh giá bằng AI” để xem một lần chạy trực tiếp, vẫn mang tính minh họa.",
      );
    }
    providerIndicator.textContent = "Đã tải câu trả lời mẫu";
    liveStatus.textContent = loadedExample.canPreview
      ? "Đã tải câu trả lời mẫu. Có thể mở bản ghi mà không gọi AI."
      : "Đã tải câu trả lời mẫu từ Task 3. Bản ghi điểm chưa được cung cấp; có thể đánh giá trực tiếp bằng AI.";
    liveStatus.dataset.kind = "success";
  } catch (error) {
    liveStatus.textContent = error.message;
    liveStatus.dataset.kind = "error";
  } finally {
    busy = false;
    refreshControls();
  }
});

previewButton.addEventListener("click", async () => {
  if (!loadedExample?.canPreview || loadedExample.questionId !== currentQuestionId || answerInput.value !== loadedExample.answerText) return;
  setBusy(true, "Đang mở bản ghi đánh giá mẫu…");
  try {
    const report = await requestJson("/api/preview", {
      method: "POST",
      body: JSON.stringify({ caseName: loadedExample.caseName, answerText: answerInput.value }),
    });
    renderReport(report);
    liveStatus.textContent = "Đang hiển thị bản ghi đã lưu; không có lời gọi AI.";
    liveStatus.dataset.kind = "success";
  } catch (error) {
    showMessage("error", "Không thể mở bản ghi mẫu", error.message);
    liveStatus.textContent = "Bản ghi không khớp với câu trả lời hiện tại.";
    liveStatus.dataset.kind = "error";
  } finally {
    busy = false;
    refreshControls();
  }
});

refreshControls();
loadInitialContent();
