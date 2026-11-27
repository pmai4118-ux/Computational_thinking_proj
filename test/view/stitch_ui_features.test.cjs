"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const hubScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/interview_hub.js"),
  "utf8"
);
const workspaceScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/workspace.js"),
  "utf8"
);
const evidenceScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/evidence.js"),
  "utf8"
);

class FakeClassList {
  constructor(node) {
    this.node = node;
    this.set = new Set();
  }
  add(...names) {
    for (const n of names) this.set.add(n);
    this.node.className = Array.from(this.set).join(" ");
  }
  remove(...names) {
    for (const n of names) this.set.delete(n);
    this.node.className = Array.from(this.set).join(" ");
  }
  toggle(name, force) {
    if (force === undefined) {
      if (this.set.has(name)) this.set.delete(name);
      else this.set.add(name);
    } else if (force) {
      this.set.add(name);
    } else {
      this.set.delete(name);
    }
    this.node.className = Array.from(this.set).join(" ");
    return this.set.has(name);
  }
  contains(name) {
    return this.set.has(name);
  }
}

class DomNode {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this._className = "";
    this.classList = new FakeClassList(this);
    this.textContent = "";
    this.value = "";
    this.hidden = false;
    this.disabled = false;
    this.readOnly = false;
    this.focused = false;
    this.dataset = {};
    this.style = {};
    this.attributes = new Map();
    this.children = [];
    this.listeners = new Map();
  }
  get className() {
    return this._className;
  }
  set className(val) {
    this._className = String(val || "");
    this.classList.set = new Set(this._className.split(/\s+/).filter(Boolean));
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
    const list = this.listeners.get(name) || [];
    list.push(callback);
    this.listeners.set(name, list);
  }
  dispatch(name, event = {}) {
    for (const cb of this.listeners.get(name) || []) {
      cb({ preventDefault() {}, ...event });
    }
  }
  click() {
    this.dispatch("click");
  }
  focus() {
    this.focused = true;
  }
  scrollIntoView() {}
  _matches(selector) {
    if (selector.startsWith(".")) {
      return this.classList.contains(selector.slice(1));
    }
    if (selector.startsWith("[") && selector.endsWith("]")) {
      return this.attributes.has(selector.slice(1, -1));
    }
    return this.tagName.toLowerCase() === selector.toLowerCase();
  }
  querySelectorAll(selector) {
    const out = [];
    const walk = (n) => {
      for (const c of n.children || []) {
        if (c instanceof DomNode) {
          if (c._matches(selector)) out.push(c);
          walk(c);
        }
      }
    };
    walk(this);
    return out;
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

function textFromTree(node) {
  if (!node) return "";
  if (typeof node.textContent === "string" && (!node.children || node.children.length === 0)) {
    return node.textContent;
  }
  if (Array.isArray(node.children) && node.children.length > 0) {
    return node.children.map(textFromTree).join("");
  }
  return node.textContent || "";
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test("Hub: mode cards switch evaluation_timing and submit via InterviewApi.createSession", async () => {
  const elements = new Map();
  const modeRealistic = new DomNode("button");
  modeRealistic.setAttribute("data-mode-card", "after_session");
  const modeGuided = new DomNode("button");
  modeGuided.setAttribute("data-mode-card", "per_question");

  const el = (selector) => {
    if (!elements.has(selector)) {
      const node = new DomNode();
      if (selector === "#score-donut-arc") {
        // Simulate real browser SVGElement where .className is read-only SVGAnimatedString.
        Object.defineProperty(node, "className", {
          get() { return {}; },
          set() { throw new TypeError("Cannot set property className of #<SVGElement> which has only a getter"); },
        });
      }
      elements.set(selector, node);
    }
    return elements.get(selector);
  };
  el("#role-select").value = "backend_developer";
  el("#level-select").value = "intern_fresher";
  el("#language-select").value = "vi";
  el("#evaluation-timing-input").value = "after_session";

  let createdPayload = null;
  let navigatedTo = null;
  const window = {
    InterviewApi: {
      createSession: async (payload) => {
        createdPayload = payload;
        return { session_id: "session.hub.1" };
      },
    },
    location: { assign: (url) => { navigatedTo = url; } },
  };
  const document = {
    querySelector: el,
    querySelectorAll: (sel) => (sel === "[data-mode-card]" ? [modeRealistic, modeGuided] : []),
  };

  vm.runInNewContext(hubScript, { window, document, encodeURIComponent });

  assert.equal(modeRealistic.getAttribute("aria-pressed"), "true");
  assert.equal(modeGuided.getAttribute("aria-pressed"), "false");

  modeGuided.click();
  assert.equal(modeGuided.getAttribute("aria-pressed"), "true");
  assert.equal(el("#evaluation-timing-input").value, "per_question");

  el("#setup-form").dispatch("submit");
  await flush();

  assert.deepEqual(JSON.parse(JSON.stringify(createdPayload)), {
    role: "backend_developer",
    level: "intern_fresher",
    language: "vi",
    evaluation_timing: "per_question",
  });
  assert.equal(navigatedTo, "/sessions/session.hub.1");
});

test("Workspace: structured outline boxes serialize cleanly into canonical answer-text and preserve legacy draft", async () => {
  const elements = new Map();
  const el = (selector) => {
    if (!elements.has(selector)) {
      const node = new DomNode();
      if (selector === "#score-donut-arc") {
        // Simulate real browser SVGElement where .className is read-only SVGAnimatedString.
        Object.defineProperty(node, "className", {
          get() { return {}; },
          set() { throw new TypeError("Cannot set property className of #<SVGElement> which has only a getter"); },
        });
      }
      elements.set(selector, node);
    }
    return elements.get(selector);
  };
  el("[data-workspace]").dataset = {
    sessionId: "sess-outline",
    questionId: "q-outline",
    questionVersion: "1",
    answerId: "",
    answerRevision: "",
    evaluationTiming: "after_session",
  };
  const storage = new Map();
  let submittedBody = null;

  const window = {
    InterviewApi: {
      submitAnswer: async (_sid, body) => {
        submittedBody = body;
        return { answer: { answer_id: "ans-1", revision: 1 } };
      },
    },
    crypto: { randomUUID: () => "sub-outline-1" },
    sessionStorage: {
      getItem: (k) => storage.get(k) ?? null,
      setItem: (k, v) => storage.set(k, v),
      removeItem: (k) => storage.delete(k),
    },
    setInterval: () => 1,
    clearInterval: () => {},
    location: { origin: "http://localhost", assign() {} },
  };
  const document = {
    querySelector: el,
    querySelectorAll: () => [],
    createElement: (tag) => new DomNode(tag),
    addEventListener() {},
  };

  vm.runInNewContext(workspaceScript, {
    window, document, URL, Date, Math, JSON, Number, String, Boolean, Error, Array, encodeURIComponent,
  });

  const container = el("#argument-boxes-container");
  const textareas = container.querySelectorAll(".argument-box__textarea");
  assert.equal(textareas.length, 3);

  textareas[0].value = "Phân tích giả định hệ thống.";
  textareas[0].dispatch("input");
  textareas[2].value = "Viết test kiểm tra biên.";
  textareas[2].dispatch("input");

  assert.equal(
    el("#answer-text").value,
    "Phân tích vấn đề:\nPhân tích giả định hệ thống.\n\nCách xác minh:\nViết test kiểm tra biên."
  );
  assert.ok(storage.has("draft:v2:sess-outline:q-outline:v1"));

  await el("#answer-form").dispatch("submit");
  await flush();

  assert.equal(
    submittedBody.text,
    "Phân tích vấn đề:\nPhân tích giả định hệ thống.\n\nCách xác minh:\nViết test kiểm tra biên."
  );
});

test("Workspace: restores legacy plain-text draft verbatim without modifying content", () => {
  const elements = new Map();
  const el = (selector) => {
    if (!elements.has(selector)) {
      const node = new DomNode();
      if (selector === "#score-donut-arc") {
        // Simulate real browser SVGElement where .className is read-only SVGAnimatedString.
        Object.defineProperty(node, "className", {
          get() { return {}; },
          set() { throw new TypeError("Cannot set property className of #<SVGElement> which has only a getter"); },
        });
      }
      elements.set(selector, node);
    }
    return elements.get(selector);
  };
  el("[data-workspace]").dataset = {
    sessionId: "sess-legacy",
    questionId: "q-legacy",
    questionVersion: "2",
    answerId: "",
    answerRevision: "",
    evaluationTiming: "after_session",
  };
  const storage = new Map([["draft:sess-legacy:q-legacy", "Nháp văn bản thuần cũ nguyên bản"]]);

  const window = {
    InterviewApi: {},
    crypto: { randomUUID: () => "sub-1" },
    sessionStorage: {
      getItem: (k) => storage.get(k) ?? null,
      setItem: (k, v) => storage.set(k, v),
      removeItem: (k) => storage.delete(k),
    },
    setInterval: () => 1,
    clearInterval: () => {},
    location: { origin: "http://localhost", assign() {} },
  };
  const document = {
    querySelector: el,
    querySelectorAll: () => [],
    createElement: (tag) => new DomNode(tag),
    addEventListener() {},
  };

  vm.runInNewContext(workspaceScript, {
    window, document, URL, Date, Math, JSON, Number, String, Boolean, Error, Array, encodeURIComponent,
  });

  const textareas = el("#argument-boxes-container").querySelectorAll(".argument-box__textarea");
  assert.equal(textareas.length, 1);
  assert.equal(textareas[0].value, "Nháp văn bản thuần cũ nguyên bản");
  assert.equal(el("#answer-text").value, "Nháp văn bản thuần cũ nguyên bản");
});

test("Evidence: handles Unicode emoji offsets, overlapping quotes, XSS literal text, tab switch without evaluate, and copy", async () => {
  const answerText = "Bài 🚀 <script>alert(1)</script> phân tích và kết luận.";
  const points = Array.from(answerText);
  const q1 = "🚀 <script>alert(1)</script> phân tích";
  const q2 = "phân tích và kết luận.";
  const q1Start = points.indexOf("🚀");
  const q1End = q1Start + Array.from(q1).length;
  const q2Start = points.indexOf("p"); // wait: find exact start of "phân tích và kết luận."
  const q2Idx = answerText.indexOf(q2);
  const q2CpStart = Array.from(answerText.slice(0, q2Idx)).length;
  const q2CpEnd = q2CpStart + Array.from(q2).length;

  let evalCalls = 0;
  let copiedText = null;
  const elements = new Map();
  const root = new DomNode("section");
  root.dataset = {
    sessionId: "sess-rev",
    answerId: "ans-rev",
    answerRevision: "1",
    currentIndex: "0",
    currentAnswerId: "ans-rev",
    currentAnswerRevision: "1",
  };
  elements.set("[data-answer-review]", root);

  const el = (selector) => {
    if (!elements.has(selector)) {
      const node = new DomNode();
      if (selector === "#score-donut-arc") {
        // Simulate real browser SVGElement where .className is read-only SVGAnimatedString.
        Object.defineProperty(node, "className", {
          get() { return {}; },
          set() { throw new TypeError("Cannot set property className of #<SVGElement> which has only a getter"); },
        });
      }
      elements.set(selector, node);
    }
    return elements.get(selector);
  };

  const payload = {
    result: {
      status: "completed",
      answer_text: answerText,
      total_score: 2,
      maximum_score: 4,
      criterion_checks: [
        {
          criterion_id: "c1",
          criterion_label: "Tiêu chí 1",
          status: "met",
          score: 2,
          max_score: 2,
          explanation: "Đạt tiêu chí 1.",
          evidence: [{ quote: q1, start_offset: q1Start, end_offset: q1End }],
        },
        {
          criterion_id: "c2",
          criterion_label: "Tiêu chí 2",
          status: "unmet",
          score: 0,
          max_score: 2,
          explanation: "Thiếu tiêu chí 2.",
          evidence: [
            { quote: q2, start_offset: q2CpStart, end_offset: q2CpEnd },
            { quote: "không khớp trong bài", start_offset: 0, end_offset: 5 },
          ],
        },
      ],
    },
    feedback_items: [{ criterion_id: "c2", message: "Cần bổ sung chi tiết", suggestion: "Viết thêm ví dụ" }],
  };

  const window = {
    InterviewApi: {
      getEvaluation: async () => payload,
      evaluateAnswer: async () => { evalCalls += 1; return payload; },
    },
    location: { origin: "http://localhost", hash: "#overview", assign() {} },
    history: { replaceState() {} },
    setTimeout: () => 1,
  };
  const navigator = {
    clipboard: {
      writeText: async (text) => { copiedText = text; },
    },
  };
  const document = {
    querySelector: el,
    createElement: (tag) => new DomNode(tag),
    createTextNode: (t) => ({ textContent: String(t) }),
  };

  vm.runInNewContext(evidenceScript, {
    window, document, navigator, URL, Number, String, Boolean, Array, Set, Error, encodeURIComponent,
  });
  await flush();

  // Exact text preserved without losing characters or executing HTML
  assert.equal(textFromTree(el("#answer-source")), answerText);

  // Overlapping region "phân tích" gets neutral mixed class, not met green!
  const marks = el("#answer-source").querySelectorAll("mark");
  assert.equal(marks.length, 3); // [🚀 <script>..., "phân tích", " và kết luận."]
  assert.ok(marks[0].classList.contains("snippet-mark--met"));
  assert.ok(marks[1].classList.contains("snippet-mark--mixed"));
  assert.ok(marks[2].classList.contains("snippet-mark--unmet"));

  // Switch tab via keyboard without calling evaluateAnswer
  el("#review-tab-overview").dispatch("keydown", { key: "ArrowRight" });
  assert.equal(el("#tab-panel-overview").hidden, true);
  assert.equal(el("#tab-panel-detail").hidden, false);
  assert.equal(evalCalls, 0);

  // Copy button copies exact server answer_text
  el("#copy-answer-btn").click();
  await flush();
  assert.equal(copiedText, answerText);

  // "Xem lỗi chính" selects unmet criterion c2
  el("#jump-primary-unmet-btn").click();
  assert.match(el("#detail-panel-subtitle").textContent, /Tiêu chí 2/);
});
