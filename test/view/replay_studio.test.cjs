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
    this.focused = false;
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

function findButtons(node, out = []) {
  if (!node || typeof node === "string") return out;
  if (node.tagName === "BUTTON") out.push(node);
  for (const child of node.children || []) findButtons(child, out);
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

test("replay.js separates Safety vs Operational on nodes and outcomes, preserves keyboard focus, and renders trace milestones", async () => {
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
        trace_steps: [{ actor: "Req 1", event: "Đọc stock = 1", state_after: "stock = 1, orders = 0" }],
        is_terminal: false,
        invariants: [],
        options: [
          { option_id: "opt1", label: "SELECT FOR UPDATE giữ khóa lâu", action_summary: "Khóa bi quan", target_node_id: "leaf1" },
        ],
      },
      {
        id: "leaf1",
        parent_id: "root",
        branch_label: "Giữ FOR UPDATE lâu",
        depth: 1,
        origin: "prebuilt_branch",
        answer_alignment: "what_if_branch",
        title: "Kết cục: Rủi ro chờ khóa kéo dài",
        situation: "Giữ khóa trong lúc gọi tác vụ chậm.",
        consequence_summary: "Dữ liệu đúng nhưng treo pool.",
        system_impact: "Tăng lock wait.",
        tradeoff_note: "Giữ transaction ngắn.",
        assumptions_used: ["2 instance"],
        state_delta: "stock: 1 -> 0",
        trace_steps: [
          { actor: "Req 1", event: "BEGIN → lấy khóa mạnh SELECT stock ... FOR UPDATE (round-trip 1, chặn cả kiểm tra khóa ngoại FOR KEY SHARE).", state_after: "stock = 1, orders = 0", time_label: "t = 0ms" },
          { actor: "Req 2", event: "Đến song song, bị chặn chờ khóa dòng X", state_after: "lock = chờ", time_label: "t = 4ms (song song)" },
          { actor: "Req 1", event: "INSERT INTO orders thành công → COMMIT & nhả khóa ngay (nếu INSERT lỗi sẽ ROLLBACK hoàn tác stock = 1).", state_after: "stock = 0, orders = 1", time_label: "t = 1200ms" },
          { actor: "Req 2", event: "không có dòng nào được cập nhật; kết thúc transaction và trả về hết hàng", state_after: "stock = 0, orders = 1, rowcount = 0", time_label: "t = 1202ms" },
        ],
        is_terminal: true,
        invariants: [
          { category: "safety", name: "stock >= 0", status: "preserved", detail: "Đạt" },
          { category: "operational", name: "Độ trễ & lock wait", status: "warning", detail: "Cảnh báo chờ khóa" },
        ],
        comparison_note: "Không nên chèn tác vụ chậm trong transaction đang mở.",
        options: [],
      },
    ],
  };

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
      chooseReplayOption: async () => baseRun,
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
          trace_steps: [{ actor: "Redis", event: "Lấy khóa TTL 5s", state_after: "stock = 1, lock = Redis", time_label: "t = 0ms" }],
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

  // Initial render highlights exact matched quote and keeps rewind hidden on root.
  assert.match(collectText(studio.querySelector("#replay-answer-source")), /khóa cục bộ/);
  assert.match(collectText(studio.querySelector("#replay-tree-nav")), /Giữ FOR UPDATE lâu/);
  assert.equal(studio.querySelector("#replay-rewind-parent-top").hidden, true);

  // Clicking a node directly in #replay-tree-nav keeps keyboard focus on that newly rendered tree button & announces change.
  const leafTreeBtn = findButtons(studio.querySelector("#replay-tree-nav")).find((b) => b.dataset.nodeId === "leaf1");
  assert.ok(leafTreeBtn);
  await leafTreeBtn.trigger("click");
  assert.deepEqual(selectCall, { runId: "replayrun.1", nodeId: "leaf1" });
  const refocusedLeafBtn = findButtons(studio.querySelector("#replay-tree-nav")).find((b) => b.dataset.nodeId === "leaf1");
  assert.equal(refocusedLeafBtn.focused, true);
  assert.match(studio.querySelector("#replay-live-announcer").textContent, /Tính đúng đắn: Đạt/);
  assert.match(studio.querySelector("#replay-live-announcer").textContent, /Vận hành: Có rủi ro chờ khóa/);

  // Tree node itself separates Safety & Operational labels (never "An toàn · Ổn định").
  const treeText = collectText(studio.querySelector("#replay-tree-nav"));
  assert.match(treeText, /Tính đúng đắn: Đạt/);
  assert.match(treeText, /Vận hành: Có rủi ro chờ khóa/);
  assert.doesNotMatch(treeText, /An toàn · Ổn định/);

  // Trace renders lock lifecycle phase milestones and structured state chips.
  const traceText = collectText(studio.querySelector("#replay-trace-list"));
  assert.match(traceText, /Lấy khóa \/ Ghi/);
  assert.match(traceText, /Chờ khóa/);
  assert.match(traceText, /Commit · Nhả khóa/);
  assert.match(traceText, /Kết thúc \(0 dòng\)/);
  assert.match(traceText, /stock = 0/);
  assert.match(traceText, /orders = 1/);

  // Clicking rewind moves keyboard focus cleanly to #replay-node-title without reload.
  studio.querySelector("#replay-node-title").focused = false;
  await studio.querySelector("#replay-rewind-parent-top").trigger("click");
  assert.deepEqual(selectCall, { runId: "replayrun.1", nodeId: "root" });
  assert.equal(studio.querySelector("#replay-node-title").focused, true);

  // Submit custom branch updates summary, operational panel, and moves focus to #replay-node-title.
  studio.querySelector("#replay-custom-input").value = "Thử dùng Redis lock TTL 5s";
  studio.querySelector("#replay-node-title").focused = false;
  await studio.querySelector("#replay-custom-form").trigger("submit");
  assert.deepEqual(customCall, {
    runId: "replayrun.1",
    parentId: "root",
    text: "Thử dùng Redis lock TTL 5s",
  });
  assert.equal(studio.querySelector("#replay-node-title").focused, true);
  assert.match(collectText(studio.querySelector("#replay-outcome-summary")), /0\/1 Đạt/);
  assert.match(collectText(studio.querySelector("#replay-outcome-summary")), /Có rủi ro chờ khóa/);
  assert.match(collectText(studio.querySelector("#replay-operational-list")), /Lease expiry/);
});

test("replay.js marks missing operational checks on legacy runs as Chưa đánh giá instead of Ổn định and keeps input on failed custom submit", async () => {
  const legacyRun = {
    run_id: "replayrun.legacy",
    root_node_id: "root",
    active_node_id: "leaf_slow",
    active_path_ids: ["root", "leaf_slow"],
    visited_node_ids: ["root", "leaf_slow"],
    linked_answer_text: "SELECT FOR UPDATE",
    custom_branches_used: 0,
    custom_branch_limit: 2,
    nodes: [
      {
        id: "root",
        parent_id: null,
        branch_label: "Gốc",
        depth: 0,
        origin: "answer_start",
        answer_alignment: "matched_from_answer",
        answer_quote: "SELECT FOR UPDATE",
        answer_quote_start: 0,
        answer_quote_end: 17,
        title: "Gốc",
        situation: "Gốc",
        consequence_summary: "Gốc",
        system_impact: "Gốc",
        tradeoff_note: "Gốc",
        assumptions_used: [],
        state_delta: "",
        trace_steps: [],
        is_terminal: false,
        invariants: [],
        options: [{ option_id: "o1", label: "Giữ khóa lâu", action_summary: "Chậm", target_node_id: "leaf_slow" }],
      },
      {
        id: "leaf_slow",
        parent_id: "root",
        branch_label: "Rủi ro nghẽn khóa khi giữ FOR UPDATE quá lâu",
        depth: 1,
        origin: "prebuilt_branch",
        answer_alignment: "what_if_branch",
        title: "Rủi ro nghẽn khóa",
        situation: "Chậm trước COMMIT",
        consequence_summary: "Treo pool",
        system_impact: "Tăng lock wait",
        tradeoff_note: "Tránh tác vụ chậm",
        assumptions_used: [],
        state_delta: "",
        trace_steps: [],
        is_terminal: true,
        invariants: [
          { category: "safety", name: "stock >= 0", status: "preserved", detail: "Đạt" },
        ],
        comparison_note: "",
        options: [],
      },
    ],
  };

  const studio = mountReplayStudio({
    initialRun: legacyRun,
    api: {
      selectReplayNode: async (_runId, nodeId) => ({ ...legacyRun, active_node_id: nodeId }),
      addCustomReplayBranch: async () => {
        throw new Error("Quá thời gian mô phỏng.");
      },
    },
  });

  // Tree node and outcome summary must explicitly say "Chưa đánh giá", never "Ổn định".
  const treeText = collectText(studio.querySelector("#replay-tree-nav"));
  assert.match(treeText, /Tính đúng đắn: Đạt/);
  assert.match(treeText, /Vận hành: Chưa đánh giá/);
  assert.doesNotMatch(treeText, /Ổn định/);

  const summaryText = collectText(studio.querySelector("#replay-outcome-summary"));
  assert.match(summaryText, /Hiệu năng & Vận hành: Chưa đánh giá/);
  const opText = collectText(studio.querySelector("#replay-operational-list"));
  assert.match(opText, /CHƯA ĐÁNH GIÁ/);
  assert.match(opText, /Tạo lượt mô phỏng mới/);

  // Rewind to root and test failed custom branch preserves text and reassures quota wasn't deducted.
  await studio.querySelector("#replay-rewind-parent-top").trigger("click");
  studio.querySelector("#replay-custom-input").value = "Thử khóa hàng đợi";
  await studio.querySelector("#replay-custom-form").trigger("submit");
  assert.equal(studio.querySelector("#replay-custom-input").value, "Thử khóa hàng đợi");
  assert.match(studio.querySelector("#replay-error").textContent, /Chưa trừ lượt tự đề xuất/);
});
