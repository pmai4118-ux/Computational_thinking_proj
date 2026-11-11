const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const fixtureDirectory = path.join(root, "examples/evaluateAnswer/inventoryRace");
const readJson = (name) => JSON.parse(fs.readFileSync(path.join(fixtureDirectory, name), "utf8"));

class Element {
  constructor() {
    this.children = [];
    this.dataset = {};
    this.handlers = {};
    this.value = "";
    this.hidden = false;
  }
  append(node) { this.children.push(node); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
}

async function pageWithReport() {
  const inputs = readJson("correct.input.json");
  const recording = readJson("correct.recording.json");
  const report = {
    inputs, providerName: "recorded", modelName: "recorded", promptVersion: "recorded/1",
    results: recording.interpretation.reviews.map((review, index) => ({...review, resultId: String(index), score: 2})),
    feedbackItems: [],
  };
  const elements = new Map();
  const responses = new Map();
  const get = (selector) => {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  };
  get.responses = responses;
  get("#report-content").hidden = true;
  get("#example-select").value = "correct";
  const context = {
    document: {querySelector: get, createElement: () => new Element()},
    fetch: async (url) => responses.get(url) || ({ok: true, json: async () => {
      if (url === "/api/question") return inputs.question;
      if (url === "/api/status") return {liveEvaluationConfigured: true, providerName: "antigravity", modelName: "test"};
      if (url.startsWith("/api/examples/")) {
        const caseName = url.split("/").pop();
        return {caseName, answerText: readJson(`${caseName}.input.json`).answer.originalText};
      }
      if (url === "/api/preview") return report;
      throw new Error(`Unexpected request: ${url}`);
    }}),
  };
  vm.runInNewContext(fs.readFileSync(path.join(root, "examples/evaluateAnswer/demo_ui/static/demo.js"), "utf8"), context);
  await new Promise((resolve) => setImmediate(resolve));
  await get("#load-example-button").handlers.click();
  await get("#preview-button").handlers.click();
  assert.equal(get("#report-content").hidden, false);
  return get;
}

test("editing the answer removes the previous report", async () => {
  const get = await pageWithReport();
  get("#answer-text").value += "\nChanged answer";
  get("#answer-text").handlers.input();
  assert.equal(get("#report-content").hidden, true);
  assert.equal(get("#result-status").hidden, false);
  assert.notEqual(get("#provider-indicator").textContent, "Đang xem kết quả ghi sẵn");
});

test("loading another answer removes the previous report", async () => {
  const get = await pageWithReport();
  get("#example-select").value = "incorrect";
  await get("#load-example-button").handlers.click();
  assert.equal(get("#answer-text").value, readJson("incorrect.input.json").answer.originalText);
  assert.equal(get("#report-content").hidden, true);
});

test("an input event with unchanged text preserves the matching report", async () => {
  const get = await pageWithReport();
  get("#answer-text").handlers.input();
  assert.equal(get("#report-content").hidden, false);
});

test("reloading the same answer preserves the matching report", async () => {
  const get = await pageWithReport();
  await get("#load-example-button").handlers.click();
  assert.equal(get("#report-content").hidden, false);
});

test("loading a sample clears the previous provider error", async () => {
  const get = await pageWithReport();
  get.responses.set("/api/preview", {ok: false, json: async () => ({detail: "Prior failure"})});
  await get("#preview-button").handlers.click();
  assert.equal(get("#result-status").dataset.kind, "error");
  await get("#load-example-button").handlers.click();
  assert.equal(get("#result-status").dataset.kind, "empty");
  assert.equal(get("#report-content").hidden, true);
});

test("changing questions clears the old report and loads only that question's sample answers", async () => {
  const get = await pageWithReport();
  const questionId = "question.c02.string_immutability.v2";
  get.responses.set(`/api/question?questionId=${questionId}`, {
    ok: true,
    json: async () => ({
      questionId,
      title: "Java String immutable · C02",
      prompt: "Giải thích String immutable.",
      code: "first = \"Java\"",
      codeLanguage: "java",
      requirements: ["Nêu kết quả và lý do."],
      expectedLevel: "Intern Fresher",
      exampleOnly: true,
      reviewStatus: "pending_review",
      sourceLabel: "Task 3 · cần review",
      examples: [{caseName: "TC_C02_01", label: "Đúng đầy đủ", canPreview: false}],
    }),
  });
  get.responses.set(`/api/examples/TC_C02_01?questionId=${questionId}`, {
    ok: true,
    json: async () => ({caseName: "TC_C02_01", answerText: "String không đổi."}),
  });

  get("#question-select").value = questionId;
  await get("#question-select").handlers.change();
  assert.equal(get("#report-content").hidden, true);
  assert.equal(get("#question-heading").textContent, "Java String immutable · C02");
  assert.equal(get("#example-select").children[0].value, "TC_C02_01");
  assert.equal(get("#answer-text").value, "");

  await get("#load-example-button").handlers.click();
  assert.equal(get("#answer-text").value, "String không đổi.");
  assert.equal(get("#preview-button").hidden, true);
});

test("validation detail arrays produce a readable error and preserve the answer", async () => {
  const get = await pageWithReport();
  const original = get("#answer-text").value;
  get.responses.set("/api/preview", {ok: false, json: async () => ({detail: [{msg: "invalid field"}]})});
  await get("#preview-button").handlers.click();
  assert.equal(get("#result-status").dataset.kind, "error");
  assert.match(get("#result-status").children[2].textContent, /Nội dung gửi lên/);
  assert.equal(get("#answer-text").value, original);
});

test("a non-JSON server error produces a readable recovery message", async () => {
  const get = await pageWithReport();
  get.responses.set("/api/preview", {ok: false, json: async () => { throw new SyntaxError("private upstream HTML"); }});
  await get("#preview-button").handlers.click();
  assert.equal(get("#result-status").dataset.kind, "error");
  assert.match(get("#result-status").children[2].textContent, /Không đọc được phản hồi/);
  assert.doesNotMatch(get("#result-status").children[2].textContent, /private/);
});
