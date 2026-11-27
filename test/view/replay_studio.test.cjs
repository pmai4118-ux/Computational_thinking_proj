"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const replayScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/replay.js"),
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
    this.dataset = {};
    this.attributes = new Map();
    this.children = [];
    this.listeners = new Map();
  }
  append(...items) {
    for (const item of items) this.children.push(item);
  }
  replaceChildren(...items) {
    this.children = [...items];
  }
  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }
  addEventListener(name, cb) {
    const arr = this.listeners.get(name) || [];
    arr.push(cb);
    this.listeners.set(name, arr);
  }
  async trigger(name, event = { preventDefault() {} }) {
    for (const cb of this.listeners.get(name) || []) {
      await cb(event);
    }
  }
  focus() {
    this.focused = true;
  }
}

function collectText(node) {
  if (!node) return "";
  if (typeof node === "string") return node;
  let out = node.textContent || "";
  for (const child of node.children || []) out += collectText(child);
  return out;
}

function mountReplayStudio({ initialRun, api }) {
  const elements = new Map();
  function querySelector(selector) {
    if (!elements.has(selector)) {
      const node = new FakeNode("div");
      if (selector === "[data-replay-studio]") node.dataset = { runId: initialRun.run_id };
      if (selector === "#replay-initial-data") node.textContent = JSON.stringify(initialRun);
      elements.set(selector, node);
    }
    return elements.get(selector);
  }

  vm.runInNewContext(replayScript, {
    window: { InterviewApi: api },
    document: {
      querySelector,
      createElement: (tag) => new FakeNode(tag),
      createTextNode: (text) => ({ textContent: String(text) }),
    },
    JSON,
    Number,
    String,
    Boolean,
    Array,
    Set,
    Map,
    Math,
    Error,
  });

  return { querySelector };
}

test("replay.js highlights matched quote, chooses branch without reload, and submits custom branch", async () => {
  const baseRun = {
    run_id: "replayrun.1",
    root_node_id: "root",
    active_node_id: "root",
    active_path_ids: ["root"],
    visited_node_ids: ["root"],
    linked_answer_text: "Em dùng khóa cục bộ để trừ kho.",
    custom_branches_used: 0,
    custom_branch_limit: 2,
    nodes: [
      {
        id: "root",
        parent_id: null,
        branch_label: "Xuất phát từ bài làm",
        depth: 0,
        origin: "answer_start",
        answer_alignment: "matched_from_answer",
        answer_quote: "khóa cục bộ",
        answer_quote_start: 8,
        answer_quote_end: 19,
        title: "Điểm xuất phát",
        situation: "Hai request chạy song song.",
        consequence_summary: "Tóm tắt",
        system_impact: "Tác động gốc",
        tradeoff_note: "Đánh đổi gốc",
        assumptions_used: ["2 instance, PostgreSQL Read Committed"],
        state_delta: "stock = 1",
        trace_steps: [{ actor: "Req 1", event: "Đọc stock = 1", state_after: "stock = 1" }],
        is_terminal: false,
        invariants: [],
        options: [
          { option_id: "opt1", label: "UPDATE WHERE stock >= 1", action_summary: "Nguyên tử tại DB", target_node_id: "leaf1" },
        ],
      },
      {
        id: "leaf1",
        parent_id: "root",
        branch_label: "UPDATE nguyên tử",
        depth: 1,
        origin: "prebuilt_branch",
        answer_alignment: "what_if_branch",
        title: "Kết cục an toàn",
        situation: "Chỉ 1 đơn thành công.",
        consequence_summary: "An toàn",
        system_impact: "Giữ bất biến",
        tradeoff_note: "Kiểm tra rowcount",
        assumptions_used: ["2 instance"],
        state_delta: "stock: 1 -> 0",
        trace_steps: [{ actor: "DB", event: "Commit", state_after: "stock = 0", time_label: "t = 8ms" }],
        is_terminal: true,
        invariants: [
          { category: "safety", name: "stock >= 0", status: "preserved", detail: "Đạt" },
          { category: "operational", name: "Độ trễ & lock wait", status: "warning", detail: "Cảnh báo chờ khóa" },
        ],
        comparison_note: "Khắc phục lỗ hổng khóa cục bộ.",
        options: [],
      },
    ],
  };

  let chosenCall = null;
  let customCall = null;
  let selectCall = null;
  const studio = mountReplayStudio({
    initialRun: baseRun,
    api: {
      selectReplayNode: async (runId, nodeId) => {
        selectCall = { runId, nodeId };
        return {
          ...baseRun,
          active_node_id: nodeId,
          active_path_ids: nodeId === "root" ? ["root"] : ["root", nodeId],
          visited_node_ids: ["root", "leaf1"],
        };
      },
      chooseReplayOption: async (runId, nodeId, optionId) => {
        chosenCall = { runId, nodeId, optionId };
        return {
          ...baseRun,
          active_node_id: "leaf1",
          active_path_ids: ["root", "leaf1"],
          visited_node_ids: ["root", "leaf1"],
        };
      },
      addCustomReplayBranch: async (runId, parentId, text) => {
        customCall = { runId, parentId, text };
        const customNode = {
          id: "custom1",
          parent_id: "root",
          branch_label: "Tự thử: Redis",
          depth: 1,
          origin: "custom_user_branch",
          answer_alignment: "what_if_branch",
          title: "Kết cục Redis",
          situation: "Dùng Redis TTL",
          consequence_summary: "Cần DB bảo vệ",
          system_impact: "Rủi ro hết TTL",
          tradeoff_note: "Thêm hạ tầng",
          assumptions_used: ["2 instance"],
          state_delta: "TTL expiry",
          trace_steps: [{ actor: "Redis", event: "Lock 5s", state_after: "locked", time_label: "t = 0ms" }],
          is_terminal: true,
          invariants: [
            { category: "safety", name: "stock >= 0", status: "uncertain", detail: "Phụ thuộc TTL" },
            { category: "operational", name: "Rủi ro Redis TTL", status: "warning", detail: "Lease expiry" },
          ],
          comparison_note: "Cần transaction DB.",
          options: [],
        };
        return {
          ...baseRun,
          active_node_id: "custom1",
          active_path_ids: ["root", "custom1"],
          visited_node_ids: ["root", "custom1"],
          custom_branches_used: 1,
          nodes: [...baseRun.nodes, customNode],
        };
      },
    },
  });

  // Initial render highlights exact matched quote in left panel, shows visual tree & hides top rewind on root.
  assert.match(collectText(studio.querySelector("#replay-answer-source")), /khóa cục bộ/);
  assert.match(collectText(studio.querySelector("#replay-tree-nav")), /UPDATE nguyên tử/);
  assert.equal(studio.querySelector("#replay-rewind-parent-top").hidden, true);
  assert.equal(studio.querySelector("#replay-ending-section").hidden, true);
  assert.equal(studio.querySelector("#replay-options-section").hidden, false);

  // Submit custom branch from root -> shows separated Safety vs Operational groups + active Rewind buttons.
  studio.querySelector("#replay-custom-input").value = "Thử dùng Redis lock TTL 5s";
  await studio.querySelector("#replay-custom-form").trigger("submit");
  assert.deepEqual(customCall, {
    runId: "replayrun.1",
    parentId: "root",
    text: "Thử dùng Redis lock TTL 5s",
  });
  assert.equal(studio.querySelector("#replay-ending-section").hidden, false);
  assert.equal(studio.querySelector("#replay-rewind-parent").hidden, false);
  assert.equal(studio.querySelector("#replay-rewind-parent-top").hidden, false);
  assert.match(collectText(studio.querySelector("#replay-outcome-summary")), /0\/1 Đạt/);
  assert.match(collectText(studio.querySelector("#replay-outcome-summary")), /Cảnh báo rủi ro/);
  assert.match(collectText(studio.querySelector("#replay-operational-list")), /Lease expiry/);
  assert.match(studio.querySelector("#replay-node-title").textContent, /Kết cục Redis/);

  // Clicking rewind navigates cleanly back to parent node without reload!
  await studio.querySelector("#replay-rewind-parent-top").trigger("click");
  assert.deepEqual(selectCall, { runId: "replayrun.1", nodeId: "root" });
  assert.match(collectText(studio.querySelector("#replay-tree-nav")), /An toàn · Cảnh báo vận hành/);
});
