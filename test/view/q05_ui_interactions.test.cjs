"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const exerciseScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/exercise.js"),
  "utf8"
);
const evidenceScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/evidence.js"),
  "utf8"
);

class FakeNode {
  constructor(tag, onScrollIntoView) {
    this.tagName = tag.toUpperCase();
    this.className = "";
    this.textContent = "";
    this.hidden = false;
    this.disabled = false;
    this.dataset = {};
    this.attributes = new Map();
    this.children = [];
    this.listeners = new Map();
    this._onScrollIntoView = onScrollIntoView;
  }

  append(...items) {
    for (const item of items) {
      this.children.push(item);
    }
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

  remove() {
    this.removed = true;
  }

  scrollIntoView(options) {
    if (this._onScrollIntoView) {
      this._onScrollIntoView(this, options);
    }
  }

  _matches(selector) {
    if (selector.startsWith(".")) {
      const target = selector.slice(1);
      return this.className.split(/\s+/).includes(target);
    }
    if (selector.startsWith("[") && selector.endsWith("]")) {
      const attr = selector.slice(1, -1);
      return this.attributes.has(attr);
    }
    return this.tagName.toLowerCase() === selector.toLowerCase();
  }

  querySelectorAll(selector) {
    const found = [];
    const walk = (node) => {
      for (const child of node.children || []) {
        if (child instanceof FakeNode) {
          if (child._matches(selector)) found.push(child);
          walk(child);
        }
      }
    };
    walk(this);
    return found;
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

function runExercisePage({ payload, skillId = "", exerciseId = "", startPractice = async () => ({}) }) {
  const elements = new Map();
  const root = new FakeNode("section");
  root.dataset = { sessionId: "session.test", skillId, exerciseId };
  elements.set("[data-exercise-page]", root);

  function querySelector(selector) {
    if (!elements.has(selector)) {
      elements.set(selector, new FakeNode("div"));
    }
    return elements.get(selector);
  }

  const document = {
    querySelector,
    createElement: (tag) => new FakeNode(tag),
    createTextNode: (text) => ({ textContent: String(text) }),
  };

  let navigatedTo = null;
  const window = {
    InterviewApi: {
      getExerciseRecommendations: async () => payload,
      getExercise: async () => ({}),
      startPractice,
    },
    location: {
      href: "http://localhost/sessions/session.test/exercises",
      origin: "http://localhost",
      assign(url) {
        navigatedTo = url;
      },
    },
  };

  vm.runInNewContext(exerciseScript, {
    window,
    document,
    URL,
    encodeURIComponent,
    Map,
    Set,
    Array,
    Boolean,
    String,
    Error,
  });

  return { querySelector, getNavigatedTo: () => navigatedTo };
}

function runEvidencePage({ payload }) {
  const scrollCalls = [];
  const elements = new Map();
  const root = new FakeNode("section");
  root.dataset = {
    sessionId: "session.test",
    answerId: "answer.1",
    answerRevision: "1",
    currentIndex: "0",
    currentAnswerId: "answer.1",
    currentAnswerRevision: "1",
  };
  elements.set("[data-answer-review]", root);

  function querySelector(selector) {
    if (!elements.has(selector)) {
      elements.set(selector, new FakeNode("div"));
    }
    return elements.get(selector);
  }

  const document = {
    querySelector,
    createElement: (tag) =>
      new FakeNode(tag, (node, options) => {
        scrollCalls.push({ tag: node.tagName, text: node.textContent, options });
      }),
    createTextNode: (text) => ({ textContent: String(text) }),
  };

  const window = {
    InterviewApi: {
      getEvaluation: async () => payload,
      nextQuestion: async () => ({ state: "completed" }),
    },
    location: {
      origin: "http://localhost",
      assign() {},
    },
  };

  vm.runInNewContext(evidenceScript, {
    window,
    document,
    URL,
    Number,
    String,
    Boolean,
    Array,
    Error,
    encodeURIComponent,
  });

  return { querySelector, scrollCalls };
}

test("UI-01: groups duplicate exercise recommendations into one card with all reasons and no alternate-question action", async () => {
  const makeRec = (criterionId, criterionLabel, reason) => ({
    exercise_id: "exercise.programming.mutable_defaults_and_binding",
    version: 1,
    title: "Thực hành tách trạng thái mặc định và biến tự do trong closure Python",
    summary: "Luyện tập default argument và late binding.",
    related_skill_ids: ["skill.programming.code_semantics"],
    prerequisite_ids: [],
    estimated_duration_minutes: 25,
    matched_gap: {
      skill_id: "skill.programming.code_semantics",
      skill_label: "Ngữ nghĩa mã nguồn",
      question_ref: { id: "prog.c02.closure_late_binding.v1", version: 1 },
      answer_ref: { id: "answer.1", revision: 1 },
      evaluation_id: "eval.1",
      criterion_id: criterionId,
      criterion_label: criterionLabel,
      reason,
    },
    recommendation_reason: `Addresses ${criterionLabel}: ${reason}`,
    source: {
      source_id: "source.cpython.faq.mutable_defaults",
      title: "Python FAQ",
      url: "https://docs.python.org/3/faq/programming.html",
      license_spdx: "PSF-2.0",
      required_notice: null,
    },
    eligible_alternate_question_available: true,
  });

  const payload = {
    session_id: "session.test",
    recommendations: [
      makeRec("c02.late_binding", "Giải thích kết quả", "Thiếu giải thích cơ chế tra cứu biến."),
      makeRec("c02.fix_binding", "Sửa bản cài đặt", "Chưa nêu cách sửa giữ giá trị từng bước."),
      makeRec("c02.test_closure", "Kiểm thử hành vi", "Thiếu ca kiểm thử sau vòng lặp."),
    ],
    unmatched_skill_ids: [],
    message: null,
  };

  const page = runExercisePage({ payload });
  await flush();

  const list = page.querySelector("#exercise-list");
  const cards = list.querySelectorAll(".exercise-card");
  assert.equal(cards.length, 1);

  const reasons = cards[0].querySelectorAll("li").map((item) => item.textContent);
  assert.ok(reasons.some((text) => text.includes("Giải thích kết quả")));
  assert.ok(reasons.some((text) => text.includes("Sửa bản cài đặt")));
  assert.ok(reasons.some((text) => text.includes("Kiểm thử hành vi")));

  const practiceButtons = cards[0]
    .querySelectorAll("button")
    .filter((btn) => btn.textContent.includes("Luyện lại với câu hỏi khác"));
  assert.equal(practiceButtons.length, 0);
});

test("UI-01: preserves prerequisite ordering across distinct exercises when grouping", async () => {
  const payload = {
    session_id: "session.test",
    recommendations: [
      {
        exercise_id: "exercise.backend.atomic_transaction_locking",
        version: 1,
        title: "Bài tiên quyết khóa giao dịch",
        summary: "Khóa mức dòng.",
        related_skill_ids: ["skill.backend.data_consistency"],
        prerequisite_ids: [],
        estimated_duration_minutes: 30,
        matched_gap: {
          criterion_id: "c03.atomicity",
          criterion_label: "Tính nguyên tử",
          reason: "Thiếu rollback.",
          answer_ref: { id: "answer.2", revision: 1 },
        },
        source: { source_id: "source.postgres" },
        eligible_alternate_question_available: true,
      },
      {
        exercise_id: "exercise.backend.rollback_invariant_test",
        version: 1,
        title: "Bài kiểm thử rollback",
        summary: "Viết test đồng thời.",
        related_skill_ids: ["skill.backend.data_consistency"],
        prerequisite_ids: ["exercise.backend.atomic_transaction_locking"],
        estimated_duration_minutes: 25,
        matched_gap: {
          criterion_id: "c03.concurrent_tests",
          criterion_label: "Kiểm thử đồng thời",
          reason: "Thiếu test rollback.",
          answer_ref: { id: "answer.2", revision: 1 },
        },
        source: { source_id: "source.postgres" },
        eligible_alternate_question_available: true,
      },
    ],
    unmatched_skill_ids: [],
    message: null,
  };

  const page = runExercisePage({ payload });
  await flush();

  const titles = page
    .querySelector("#exercise-list")
    .querySelectorAll("h2")
    .map((node) => node.textContent);
  assert.deepEqual(titles, ["Bài tiên quyết khóa giao dịch", "Bài kiểm thử rollback"]);
});

test("UI-04: empty skill filter shows learner-friendly Vietnamese without API jargon", async () => {
  const page = runExercisePage({
    skillId: "skill.unknown",
    payload: {
      session_id: "session.test",
      recommendations: [],
      unmatched_skill_ids: [],
      message: null,
    },
  });
  await flush();

  const emptyReason = page.querySelector("#exercise-empty-reason").textContent;
  assert.match(emptyReason, /Chưa có bài tập phù hợp với kỹ năng/);
  assert.doesNotMatch(emptyReason, /API/);
  const resetLink = page.querySelector("#exercise-empty").querySelector("[data-reset-exercise-filter]");
  assert.ok(resetLink);
  assert.equal(resetLink.textContent, "Xem toàn bộ bài tập của phiên");
});

test("UI-05: initial review render highlights first criterion without auto-scrolling, while clicking scrolls", async () => {
  const answerText = "Đoạn một giải thích biến tự do. Đoạn hai nêu cách kiểm thử cụ thể.";
  const quote1 = "Đoạn một giải thích biến tự do.";
  const quote2 = "Đoạn hai nêu cách kiểm thử cụ thể.";
  const payload = {
    result: {
      status: "completed",
      answer_text: answerText,
      total_score: 4,
      maximum_score: 4,
      criterion_checks: [
        {
          criterion_id: "c1",
          criterion_label: "Tiêu chí 1",
          status: "met",
          score: 2,
          max_score: 2,
          explanation: "Đạt tiêu chí 1.",
          evidence: [
            {
              quote: quote1,
              start_offset: answerText.indexOf(quote1),
              end_offset: answerText.indexOf(quote1) + quote1.length,
            },
          ],
        },
        {
          criterion_id: "c2",
          criterion_label: "Tiêu chí 2",
          status: "met",
          score: 2,
          max_score: 2,
          explanation: "Đạt tiêu chí 2.",
          evidence: [
            {
              quote: quote2,
              start_offset: answerText.indexOf(quote2),
              end_offset: answerText.indexOf(quote2) + quote2.length,
            },
          ],
        },
      ],
    },
    feedback_items: [],
  };

  const page = runEvidencePage({ payload });
  await flush();

  const buttons = page.querySelector("#criteria-list").querySelectorAll(".criterion-button");
  assert.equal(buttons.length, 2);
  assert.equal(buttons[0].getAttribute("aria-pressed"), "true");
  assert.equal(buttons[1].getAttribute("aria-pressed"), "false");
  assert.equal(page.scrollCalls.length, 0);

  buttons[1].click();
  assert.equal(buttons[0].getAttribute("aria-pressed"), "false");
  assert.equal(buttons[1].getAttribute("aria-pressed"), "true");
  assert.equal(page.scrollCalls.length, 1);
  assert.equal(page.scrollCalls[0].text, quote2);
});
