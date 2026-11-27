"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/workspace.js"), "utf8"
);

function browser({ api, index = 0 }) {
  const handlers = new Map();
  const timers = new Map();
  const elements = new Map();
  const storage = new Map();
  let nextTimer = 1;
  let navigation = null;

  function element(selector) {
    if (!elements.has(selector)) {
      elements.set(selector, {
        value: "", textContent: "", hidden: false, disabled: false,
        dataset: {}, readOnly: false,
        addEventListener(name, callback) { handlers.set(`${selector}:${name}`, callback); },
        focus() { this.focused = true; },
        insertAdjacentElement(_position, node) { this.inserted = node; },
      });
    }
    return elements.get(selector);
  }

  element("[data-workspace]").dataset = {
    sessionId: "session-1", questionId: "question-1", questionVersion: "1",
    currentIndex: String(index), answerId: "",
  };
  element("#workspace-error").hidden = true;
  element("#workspace-status").hidden = true;

  const sessionStorage = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  };
  const window = {
    InterviewApi: api,
    crypto: { randomUUID: () => "submission-1" },
    sessionStorage,
    addEventListener(name, callback) { handlers.set(`window:${name}`, callback); },
    setTimeout(callback, delay) {
      const id = nextTimer++;
      timers.set(id, { callback, delay });
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
    location: { origin: "http://localhost", assign(url) { navigation = url; } },
  };

  vm.runInNewContext(script, {
    window,
    document: {
      querySelector: element,
      createElement: () => ({
        addEventListener(name, callback) { this[`on${name}`] = callback; },
      }),
    },
    sessionStorage, URL,
    Date: { now: () => 1000 }, Math, JSON, Number, String, Boolean, Error,
    encodeURIComponent,
  });

  return {
    element, handlers, timers, sessionStorage,
    async fireTimer(delay) {
      const match = [...timers.entries()].find(([, timer]) => timer.delay === delay);
      assert.ok(match, `expected a ${delay}ms timer`);
      timers.delete(match[0]);
      await match[1].callback();
    },
    get navigation() { return navigation; },
  };
}

const input = (page, text) => {
  page.element("#answer-text").value = text;
  page.handlers.get("#answer-text:input")();
};

test("draft autosaves to the session API after typing", async () => {
  const saves = [];
  const page = browser({ api: { saveDraft: async (...args) => saves.push(args) } });
  input(page, "Bản nháp đã nhập");
  await page.fireTimer(600);
  assert.equal(saves.length, 1);
  assert.equal(saves[0][0], "session-1");
  assert.equal(saves[0][1].question_id, "question-1");
  assert.equal(saves[0][1].text, "Bản nháp đã nhập");
  assert.equal(page.element("#draft-label").textContent, "Đã lưu bản nháp");
});

test("save and exit waits for the latest draft before leaving", async () => {
  const saves = [];
  const page = browser({ api: { saveDraft: async (_id, draft) => saves.push(draft.text) } });
  input(page, "Nội dung mới nhất");
  await page.handlers.get("#save-exit:click")({ preventDefault() {} });
  assert.deepEqual(saves, ["Nội dung mới nhất"]);
  assert.equal(page.navigation, "/");
});

test("blank answer is rejected without submitting", async () => {
  let submits = 0;
  const page = browser({ api: { submitAnswer: async () => { submits += 1; } } });
  await page.handlers.get("#answer-form:submit")({ preventDefault() {} });
  assert.equal(submits, 0);
  assert.equal(page.element("#workspace-error").hidden, false);
  assert.equal(page.element("#answer-text").focused, true);
});

test("submission saves the draft, locks the answer, and advances in order", async () => {
  const calls = [];
  const page = browser({ api: {
    saveDraft: async (_id, draft) => calls.push(`draft:${draft.text}`),
    submitAnswer: async (_id, payload) => { calls.push(`answer:${payload.text}`); },
    nextQuestion: async (_id, from) => {
      calls.push(`next:${from}`);
      return { progress: { answered_count: 1, total_questions: 4 } };
    },
  } });
  input(page, "Câu trả lời đã gửi");
  await page.handlers.get("#answer-form:submit")({ preventDefault() {} });
  assert.equal(calls.join("|"), "draft:Câu trả lời đã gửi|answer:Câu trả lời đã gửi|next:0");
  assert.equal(page.navigation, "/sessions/session-1");
  assert.equal(page.element("#answer-text").readOnly, true);
  assert.equal(page.element("#submit-answer").hidden, true);
});

test("final answer opens the summary only after the session count is complete", async () => {
  const page = browser({ index: 3, api: {
    saveDraft: async () => {},
    submitAnswer: async () => {},
    nextQuestion: async () => ({ progress: { answered_count: 4, total_questions: 4 } }),
  } });
  input(page, "Câu trả lời thứ tư");
  await page.handlers.get("#answer-form:submit")({ preventDefault() {} });
  assert.equal(page.navigation, "/sessions/session-1/summary");
});

test("a failed advance after saving prevents a duplicate submission", async () => {
  let submits = 0;
  const page = browser({ api: {
    saveDraft: async () => {},
    submitAnswer: async () => { submits += 1; },
    nextQuestion: async () => { throw new Error("Kết nối bị ngắt"); },
  } });
  input(page, "Câu đã lưu ở máy chủ");
  await page.handlers.get("#answer-form:submit")({ preventDefault() {} });
  assert.equal(submits, 1);
  assert.equal(page.element("#submit-answer").hidden, true);
  assert.equal(page.element("#answer-text").readOnly, true);
  assert.match(page.element("#workspace-status").textContent, /Tải lại trang/);
  assert.ok(page.element("#workspace-status").inserted);
});

test("beforeunload warns while an unsaved draft is dirty", () => {
  const page = browser({ api: {} });
  input(page, "Bản nháp chưa lưu");
  let prevented = false;
  const event = { preventDefault() { prevented = true; }, returnValue: null };
  page.handlers.get("window:beforeunload")(event);
  assert.equal(prevented, true);
  assert.equal(event.returnValue, "");
});

test("failed draft save keeps the answer visible and stays on the question", async () => {
  const page = browser({ api: { saveDraft: async () => { throw new Error("Không lưu được"); } } });
  input(page, "Bản nháp vẫn giữ trong ô");
  await page.handlers.get("#save-exit:click")({ preventDefault() {} });
  assert.equal(page.navigation, null);
  assert.equal(page.element("#answer-text").value, "Bản nháp vẫn giữ trong ô");
  assert.match(page.element("#workspace-error").textContent, /Không lưu được/);
});

test("stale api client without saveDraft shows clear reload guidance instead of TypeError", async () => {
  const page = browser({ api: {} });
  input(page, "Nội dung cần giữ nguyên");
  await page.handlers.get("#answer-form:submit")({ preventDefault() {} });
  assert.equal(page.navigation, null);
  assert.equal(page.element("#answer-text").value, "Nội dung cần giữ nguyên");
  assert.match(page.element("#workspace-error").textContent, /Ctrl\+F5/);
  assert.match(page.element("#draft-label").textContent, /Ctrl\+F5/);
});
