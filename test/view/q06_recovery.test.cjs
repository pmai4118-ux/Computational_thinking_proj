"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const workspaceScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/workspace.js"),
  "utf8"
);
const evidenceScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/evidence.js"),
  "utf8"
);

class FakeNode {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.className = "";
    this.textContent = "";
    this.value = "";
    this.hidden = false;
    this.disabled = false;
    this.focused = false;
    this.dataset = {};
    this.attributes = new Map();
    this.children = [];
    this.listeners = new Map();
  }

  append(...items) {
    this.children.push(...items);
  }

  replaceChildren(...items) {
    this.children = [...items];
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  addEventListener(name, callback) {
    const existing = this.listeners.get(name) || [];
    existing.push(callback);
    this.listeners.set(name, existing);
  }

  click() {
    for (const cb of this.listeners.get("click") || []) {
      cb({ preventDefault() {} });
    }
  }

  focus() {
    this.focused = true;
  }

  scrollIntoView() {}

  querySelectorAll(selector) {
    const found = [];
    const targetClass = selector.startsWith(".") ? selector.slice(1) : null;
    const walk = (node) => {
      for (const child of node.children || []) {
        if (child instanceof FakeNode) {
          if (targetClass && child.className.split(/\s+/).includes(targetClass)) {
            found.push(child);
          }
          walk(child);
        }
      }
    };
    walk(this);
    return found;
  }
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

function runWorkspaceWithSavedAnswer(api) {
  const elements = new Map();
  function element(selector) {
    if (!elements.has(selector)) {
      const node = new FakeNode("div");
      if (selector === "#retry-evaluation" || selector === "#workspace-error" || selector === "#workspace-status") {
        node.hidden = true;
      }
      elements.set(selector, node);
    }
    return elements.get(selector);
  }

  element("[data-workspace]").dataset = {
    sessionId: "session-q06",
    questionId: "question-1",
    questionVersion: "1",
    answerId: "answer-q06",
    answerRevision: "1",
  };
  const storage = new Map();
  const windowListeners = new Map();
  const window = {
    InterviewApi: api,
    crypto: { randomUUID: () => "subm-q06" },
    addEventListener(name, callback) { windowListeners.set(name, callback); },
    sessionStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key),
    },
    setInterval: () => 1,
    clearInterval: () => {},
    location: { origin: "http://localhost", assign() {} },
  };

  vm.runInNewContext(workspaceScript, {
    window,
    document: {
      querySelector: element,
      addEventListener() {},
    },
    URL,
    Date,
    Math,
    JSON,
    Number,
    String,
    Boolean,
    Error,
    encodeURIComponent,
  });

  return { element, elements };
}

function runEvidencePage(api) {
  const elements = new Map();
  const root = new FakeNode("section");
  root.dataset = {
    sessionId: "session-q06",
    answerId: "answer-q06",
    answerRevision: "1",
    currentIndex: "0",
    currentAnswerId: "answer-q06",
    currentAnswerRevision: "1",
  };
  elements.set("[data-answer-review]", root);

  function querySelector(selector) {
    if (!elements.has(selector)) {
      const node = new FakeNode("div");
      if (
        selector === "#review-error" ||
        selector === "#review-content" ||
        selector === "#retry-review-load" ||
        selector === "#retry-review-evaluation" ||
        selector === "#next-question"
      ) {
        node.hidden = true;
      }
      elements.set(selector, node);
    }
    return elements.get(selector);
  }

  const window = {
    InterviewApi: api,
    location: { origin: "http://localhost", assign() {} },
  };

  vm.runInNewContext(evidenceScript, {
    window,
    document: {
      querySelector,
      createElement: (tag) => new FakeNode(tag),
      createTextNode: (text) => ({ textContent: String(text) }),
    },
    URL,
    Number,
    String,
    Boolean,
    Array,
    Error,
    encodeURIComponent,
  });

  return { querySelector };
}

test("workspace does not expose a partial evaluation before all questions are answered", async () => {
  let reads = 0;
  const page = runWorkspaceWithSavedAnswer({
    getEvaluation: async () => {
      reads += 1;
      return { result: { status: "failed", failure_code: "PROVIDER_TIMEOUT", retryable: true } };
    },
  });
  await flush();

  assert.equal(reads, 0);
  assert.equal(page.elements.has("#open-review"), false);
  assert.equal(page.elements.has("#retry-evaluation"), false);
});

test("Q06-02: review page on retryable failed evaluation exposes retry and renders result on recovery", async () => {
  let evaluateCalls = 0;
  const completedPayload = {
    result: {
      status: "completed",
      answer_text: "Câu trả lời đã lưu nguyên văn.",
      total_score: 2,
      maximum_score: 2,
      criterion_checks: [
        {
          criterion_id: "c1",
          criterion_label: "Tiêu chí 1",
          status: "met",
          score: 2,
          max_score: 2,
          explanation: "Đạt yêu cầu.",
          evidence: [
            {
              quote: "Câu trả lời đã lưu nguyên văn.",
              start_offset: 0,
              end_offset: "Câu trả lời đã lưu nguyên văn.".length,
            },
          ],
        },
      ],
    },
    feedback_items: [],
  };

  const page = runEvidencePage({
    getEvaluation: async () => ({
      result: {
        status: "failed",
        answer_text: "Câu trả lời đã lưu nguyên văn.",
        failure_code: "PROVIDER_TIMEOUT",
        retryable: true,
        total_score: null,
        criterion_checks: [],
      },
      feedback_items: [],
    }),
    evaluateAnswer: async () => {
      evaluateCalls += 1;
      return completedPayload;
    },
  });
  await flush();

  assert.equal(page.querySelector("#review-content").hidden, true);
  assert.equal(page.querySelector("#review-error").hidden, false);
  assert.equal(page.querySelector("#review-error").focused, true);
  assert.equal(page.querySelector("#retry-review-evaluation").hidden, false);

  page.querySelector("#retry-review-evaluation").click();
  await flush();

  assert.equal(evaluateCalls, 1);
  assert.equal(page.querySelector("#review-content").hidden, false);
  assert.equal(page.querySelector("#retry-review-evaluation").hidden, true);
  assert.equal(page.querySelector("#evaluation-total").textContent, "2 / 2");
});

test("Q06-02: review page on permanent failed evaluation hides retry button", async () => {
  const page = runEvidencePage({
    getEvaluation: async () => ({
      result: {
        status: "failed",
        answer_text: "Câu trả lời đã lưu.",
        failure_code: "PROVIDER_CONFIG_ERROR",
        retryable: false,
        total_score: null,
        criterion_checks: [],
      },
      feedback_items: [],
    }),
  });
  await flush();

  assert.equal(page.querySelector("#review-content").hidden, true);
  assert.equal(page.querySelector("#retry-review-evaluation").hidden, true);
  assert.match(page.querySelector("#review-error").textContent, /khắc phục lỗi dịch vụ/);
});

test("Q06-02: review page on processing evaluation shows status and reload button instead of empty criteria", async () => {
  const page = runEvidencePage({
    getEvaluation: async () => ({
      result: {
        status: "processing",
        answer_text: "Câu trả lời đang chờ chấm.",
        total_score: null,
        criterion_checks: [],
      },
      feedback_items: [],
    }),
  });
  await flush();

  assert.equal(page.querySelector("#review-content").hidden, true);
  assert.equal(page.querySelector("#retry-review-evaluation").hidden, true);
  assert.equal(page.querySelector("#retry-review-load").hidden, false);
  assert.match(page.querySelector("#review-status").textContent, /đang được AI đối chiếu rubric/);
});
