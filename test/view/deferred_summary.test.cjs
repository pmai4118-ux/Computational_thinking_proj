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
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.hidden = true;
    this.open = false;
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

function findDetails(root) {
  const result = [];
  for (const child of (root && root.children) || []) {
    if (child.tag === "details") result.push(child);
    result.push(...findDetails(child));
  }
  return result;
}

test("background summary polling shows progress, avoids auto-evaluate, and preserves open answers", async () => {
  const elements = new Map();
  const timers = [];
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
      answer_text: "Nguyên văn câu trả lời đã lưu.",
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
  finished.scored_points_total = 5;
  finished.scored_points_maximum = 6;
  finished.outcomes[0].evaluation_status = "completed";
  finished.outcomes[0].total_score = 5;
  finished.outcomes[0].maximum_score = 6;
  finished.report.status = "complete";
  finished.report.overview.evaluated_count = 1;
  finished.report.details[0].evaluation_status = "completed";

  let phase = 0;
  let evaluateCalls = 0;
  const window = {
    InterviewApi: {
      getSessionSummary: async () => (phase++ === 0 ? pending : finished),
      evaluateAnswer: async () => { evaluateCalls += 1; return { result: { status: "completed" } }; },
    },
    location: { origin: "http://localhost" },
    setTimeout(callback, delay) {
      timers.push({ callback, delay });
      return timers.length;
    },
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

  assert.equal(evaluateCalls, 0);
  assert.equal(element("#summary-state").textContent, "Đã nộp đủ bài");
  assert.equal(element("#summary-eval-state").textContent, "Đang chấm AI (0/1 câu)");
  assert.equal(element("#summary-status").hidden, false);
  assert.equal(timers.length, 1);
  assert.equal(timers[0].delay, 5000);

  const initialDetails = findDetails(element("#outcomes-list"));
  assert.equal(initialDetails.length, 1);
  initialDetails[0].open = true;

  await timers[0].callback();
  await flush();

  assert.equal(evaluateCalls, 0);
  assert.equal(element("#coverage-count").textContent, "Có kết quả 1 / 1 câu");
  assert.equal(element("#summary-eval-state").textContent, "Đã chấm xong (1/1 câu)");
  assert.equal(element("#session-score-value").textContent, "5 / 6 điểm");
  assert.equal(element("#summary-status").hidden, true);
  const refreshedDetails = findDetails(element("#outcomes-list"));
  assert.equal(refreshedDetails.length, 1);
  assert.equal(refreshedDetails[0].open, true);
});
