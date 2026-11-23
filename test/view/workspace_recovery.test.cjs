"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/workspace.js"), "utf8"
);

function browser({ savedAnswerId = "", api }) {
  const handlers = new Map();
  const intervals = new Map();
  const elements = new Map();
  let nextInterval = 1;
  let now = 0;
  let navigation = null;

  function element(selector) {
    if (!elements.has(selector)) {
      elements.set(selector, {
        value: "", textContent: "", hidden: true, disabled: false,
        dataset: {},
        addEventListener(name, callback) { handlers.set(`${selector}:${name}`, callback); },
        focus() {},
      });
    }
    return elements.get(selector);
  }

  element("[data-workspace]").dataset = {
    sessionId: "session-1", questionId: "question-1", questionVersion: "1",
    answerId: savedAnswerId, answerRevision: "1",
  };
  const storage = new Map();
  const window = {
    InterviewApi: api,
    crypto: { randomUUID: () => "submission-1" },
    sessionStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key),
    },
    setInterval(callback, delay) {
      const id = nextInterval++;
      intervals.set(id, { callback, delay });
      return id;
    },
    clearInterval: (id) => intervals.delete(id),
    location: {
      origin: "http://localhost",
      assign(url) { navigation = url; },
    },
  };
  vm.runInNewContext(script, {
    window, document: { querySelector: element }, URL,
    Date: { now: () => now }, Math, JSON, Number, String, Boolean, Error,
    encodeURIComponent,
  });
  return {
    element, handlers, intervals,
    setNow(value) { now = value; },
    get navigation() { return navigation; },
  };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test("a timed-out saved answer stays available for retry without a score", async () => {
  const page = browser({
    savedAnswerId: "answer-1",
    api: { getEvaluation: async () => ({ result: {
      status: "failed", failure_code: "PROVIDER_TIMEOUT", retryable: true,
    } }) },
  });
  await flush();
  assert.equal(page.element("#retry-evaluation").hidden, false);
  assert.match(page.element("#workspace-error").textContent, /AI phản hồi quá thời gian/);
  assert.match(page.element("#workspace-status").textContent, /chưa có điểm/);
  assert.equal(page.navigation, null);
});

test("a permanent provider failure does not invite an impossible retry", async () => {
  const page = browser({
    savedAnswerId: "answer-1",
    api: { getEvaluation: async () => ({ result: {
      status: "failed", failure_code: "PROVIDER_CONFIG_ERROR", retryable: false,
    } }) },
  });
  await flush();
  assert.equal(page.element("#retry-evaluation").hidden, true);
  assert.match(page.element("#workspace-error").textContent, /khắc phục lỗi dịch vụ/);
});

test("reopened processing answer polls the saved result without another AI call", async () => {
  let reads = 0;
  let evaluations = 0;
  const page = browser({
    savedAnswerId: "answer-1",
    api: {
      getEvaluation: async () => ({ result: {
        status: ++reads === 1 ? "processing" : "completed",
      } }),
      evaluateAnswer: async () => { evaluations += 1; },
    },
  });
  await flush();
  assert.equal(page.element("#retry-evaluation").hidden, true);
  const poll = [...page.intervals.values()].find((item) => item.delay === 5000);
  assert.ok(poll);
  await poll.callback();
  await flush();
  assert.match(page.navigation, /\/sessions\/session-1\/review\?answer_id=answer-1/);
  assert.equal(evaluations, 0);
});

test("slow live request keeps saved-answer progress visible and opens its result", async () => {
  let finishEvaluation;
  const page = browser({
    api: {
      submitAnswer: async () => ({ answer: { answer_id: "answer-1", revision: 1 } }),
      evaluateAnswer: () => new Promise((resolve) => { finishEvaluation = resolve; }),
    },
  });
  page.element("#answer-text").value = "Câu trả lời đã lưu";
  const submit = page.handlers.get("#answer-form:submit");
  const pending = submit({ preventDefault() {} });
  await flush();
  page.setNow(30000);
  const notice = [...page.intervals.values()].find((item) => item.delay === 10000);
  assert.ok(notice);
  notice.callback();
  assert.match(page.element("#workspace-status").textContent, /đã chờ khoảng 30 giây/);
  assert.equal(page.element("#answer-text").readOnly, true);
  finishEvaluation({ result: { status: "completed" } });
  await pending;
  assert.match(page.navigation, /\/sessions\/session-1\/review\?answer_id=answer-1/);
});
