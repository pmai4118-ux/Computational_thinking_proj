"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/summary.js"), "utf8"
);
const flush = () => new Promise((resolve) => setImmediate(resolve));

class Node {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this.hidden = true;
    this.textContent = "";
    this.listeners = new Map();
  }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  setAttribute() {}
  querySelector() { return null; }
  focus() {}
  get childElementCount() { return this.children.length; }
}

test("finished interview starts saved-answer scoring and shows real completed-count progress", async () => {
  const elements = new Map();
  const element = (selector) => {
    if (!elements.has(selector)) elements.set(selector, new Node());
    return elements.get(selector);
  };
  element("[data-session-summary]").dataset.sessionId = "session-1";
  const pending = {
    state: "completed", completed_question_count: 0, total_question_count: 1,
    unanswered_categories: [], unresolved_categories: [], outcomes: [{
      question_ref: { id: "question-1", version: 1 }, question_prompt: "Question",
      category: "programming_knowledge", evaluation_status: "pending",
      answer_ref: { id: "answer-1", revision: 1 }, confirmed_gap_criterion_ids: [],
    }], observed_gaps: [], report: {
      status: "assessing", overview: {
        scope_note: "Observed only", answered_count: 1, evaluated_count: 0,
        axes: [], strengths: [], gaps: [],
      }, details: [{
        question_ref: { id: "question-1", version: 1 },
        answer_ref: { id: "answer-1", revision: 1 },
        evaluation_status: "pending", findings: [],
      }], proposals: [],
    },
  };
  const finished = structuredClone(pending);
  finished.completed_question_count = 1;
  finished.outcomes[0].evaluation_status = "completed";
  finished.report.status = "complete";
  finished.report.overview.evaluated_count = 1;
  finished.report.details[0].evaluation_status = "completed";
  let evaluated = false;
  let calls = 0;
  const window = {
    InterviewApi: {
      getSessionSummary: async () => evaluated ? finished : pending,
      evaluateAnswer: async () => { calls += 1; evaluated = true; return { result: { status: "completed" } }; },
    },
    location: { origin: "http://localhost" },
    setTimeout: () => 1,
    clearTimeout() {},
  };
  const document = {
    querySelector: element,
    createElement: (tag) => new Node(tag),
    createTextNode: (value) => ({ textContent: value }),
  };
  vm.runInNewContext(script, { window, document, URL, encodeURIComponent });
  await flush();
  await flush();
  assert.equal(calls, 1);
  assert.equal(element("#coverage-count").textContent, "Có kết quả 1 / 1 câu");
  assert.equal(element("#summary-status").hidden, true);
});
