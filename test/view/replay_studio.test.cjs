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
    this.id = "";
    this.className = "";
    this.textContent = "";
    this.value = "";
    this.title = "";
    this.hidden = false;
    this.disabled = false;
    this.open = false;
    this.scrollLeft = 0;
    this.scrollTop = 0;
    this.clientWidth = 0;
    this.clientHeight = 0;
    this.scrollWidth = 0;
    this.scrollHeight = 0;
    this.style = {
      setProperty(k, v) {
        this[k] = v;
      },
    };
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
  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }
  addEventListener(name, cb) {
    const arr = this.listeners.get(name) || [];
    arr.push(cb);
    this.listeners.set(name, arr);
  }
  async trigger(name, event = { preventDefault() {}, target: this }) {
    for (const cb of this.listeners.get(name) || []) {
      await cb(event);
    }
  }
  focus() {
    this.focused = true;
    if (this._doc) this._doc.activeElement = this;
  }
  remove() {}
}

function collectText(node) {
  if (!node) return "";
  if (typeof node === "string") return node;
  let out = node.textContent || "";
  for (const child of node.children || []) out += collectText(child);
  return out;
}

function findByTag(node, tag, out = []) {
  if (!node || typeof node === "string") return out;
  if (node.tagName === tag.toUpperCase()) out.push(node);
  for (const child of node.children || []) findByTag(child, tag, out);
  return out;
}

function mountReplayStudio({
  initialRun,
  api,
  viewportSize = { w: 1000, h: 460 },
  treeSize = { w: 540, h: 240 },
  splitView = false,
}) {
  const elements = new Map();
  const docListeners = new Map();
  const scheduledTimers = [];
  const doc = {
    activeElement: null,
    body: { style: {}, append() {} },
    querySelector(selector) {
      if (!elements.has(selector)) {
        const node = new FakeNode(selector === "#replay-sim-details" ? "details" : "div");
        node._doc = doc;
        if (selector === "[data-replay-studio]") node.dataset = { runId: initialRun.run_id };
        if (selector === "#replay-initial-data") node.textContent = JSON.stringify(initialRun);
        if (selector === "#replay-answer-dialog") node.hidden = true;
        if (selector === "#replay-full-prompt-panel") node.hidden = true;
        if (selector === "#replay-detail-layer") node.hidden = true;
        if (selector === "#replay-custom-panel") node.hidden = true;
        if (selector === "#replay-gen-status") node.hidden = true;
        if (selector === "#replay-gen-error") node.hidden = true;
        if (selector === "#replay-tree-viewport") {
          node.clientWidth = viewportSize.w;
          node.clientHeight = viewportSize.h;
        }
        if (selector === "#replay-tree-nav") {
          node.scrollWidth = treeSize.w;
          node.scrollHeight = treeSize.h;
        }
        elements.set(selector, node);
      }
      return elements.get(selector);
    },
    createElement(tag) {
      const node = new FakeNode(tag);
      node._doc = doc;
      return node;
    },
    createTextNode(text) {
      return { textContent: String(text) };
    },
    addEventListener(name, cb) {
      const arr = docListeners.get(name) || [];
      arr.push(cb);
      docListeners.set(name, arr);
    },
    async triggerKeydown(event) {
      for (const cb of docListeners.get("keydown") || []) {
        await cb({ preventDefault() {}, ...event });
      }
    },
  };

  let timerId = 0;
  const fakeSetTimeout = (cb, ms) => {
    const id = ++timerId;
    scheduledTimers.push({ id, cb, ms, cleared: false });
    return id;
  };
  const fakeClearTimeout = (id) => {
    const entry = scheduledTimers.find((t) => t.id === id);
    if (entry) entry.cleared = true;
  };

  vm.runInNewContext(replayScript, {
    window: {
      InterviewApi: api,
      matchMedia: (query = "") => ({
        matches:
          String(query).includes("reduced-motion") ||
          (splitView && String(query).includes("min-width")),
      }),
    },
    document: doc,
    JSON,
    Number,
    String,
    Boolean,
    Array,
    Set,
    Map,
    Math,
    Error,
    Promise,
    setTimeout: fakeSetTimeout,
    clearTimeout: fakeClearTimeout,
  });

  async function runPendingTimers() {
    const pending = scheduledTimers.filter((t) => !t.cleared);
    scheduledTimers.length = 0;
    for (const t of pending) {
      await t.cb();
    }
  }

  return { querySelector: (sel) => doc.querySelector(sel), doc, runPendingTimers };
}

function makeTransferRun() {
  return {
    run_id: "replayrun.wallet",
    root_node_id: "root",
    active_node_id: "n_ordered",
    active_path_ids: ["root", "n_ordered"],
    visited_node_ids: ["root", "n_ordered"],
    linked_answer_text:
      "Em khóa theo thứ tự ID để tránh deadlock.\n\n```sql\nBEGIN;\nSELECT * FROM wallets WHERE wallet_id IN (11111, 22222) ORDER BY wallet_id FOR UPDATE;\nCOMMIT;\n```",
    custom_branches_used: 0,
    custom_branch_limit: 2,
    question_assumptions: ["Ví 11111 = 200, Ví 22222 = 200 (tổng = 400)."],
    nodes: [
      {
        id: "root",
        parent_id: null,
        branch_label: "Điểm xuất phát",
        depth: 0,
        origin: "answer_start",
        answer_alignment: "matched_from_answer",
        answer_quote: "khóa theo thứ tự ID",
        answer_quote_start: 3,
        answer_quote_end: 22,
        title: "Điểm xuất phát từ bài làm",
        situation: "Hai giao dịch chuyển chéo A→B và B→A chạy song song trên hai kết nối DB.",
        consequence_summary: "Thứ tự xin khóa quyết định có phát sinh deadlock hay không.",
        system_impact: "Tác động gốc.",
        tradeoff_note: "Đánh đổi gốc.",
        assumptions_used: ["Ví 11111 = 200, Ví 22222 = 200."],
        state_delta: "Ban đầu: tổng số dư = 400",
        trace_steps: [{ actor: "Hệ thống", event: "Bắt đầu T1 và T2", state_after: "tổng = 400" }],
        is_terminal: false,
        invariants: [],
        options: [
          { option_id: "o_ord", label: "Khóa theo thứ tự ID", action_summary: "Sắp xếp ID tăng dần", target_node_id: "n_ordered" },
          { option_id: "o_dead", label: "Giữ thứ tự cũ + retry", action_summary: "Không đổi thứ tự", target_node_id: "n_deadlock" },
        ],
      },
      {
        id: "n_ordered",
        parent_id: "root",
        branch_label: "Khóa theo thứ tự ID",
        depth: 1,
        origin: "prebuilt_branch",
        answer_alignment: "what_if_branch",
        title: "Khóa theo thứ tự ID",
        situation: "Cả hai giao dịch xin khóa cùng ví 11111 trước rồi mới tới 22222. Không còn vòng chờ khóa.",
        consequence_summary: "Vòng chờ khóa bị triệt tiêu hoàn toàn. Cần quyết định kiểm tra số dư.",
        system_impact: "Tuần tự hóa trên cùng cặp ví.",
        tradeoff_note: "Đảm bảo không deadlock.",
        assumptions_used: ["Ví 11111 = 200, Ví 22222 = 200."],
        state_delta: "T1 khóa (11111 → 22222), T2 chờ ở 11111",
        trace_steps: [{ actor: "T1", event: "SELECT ... ORDER BY wallet_id FOR UPDATE", state_after: "Lock(11111)=T1", time_label: "t = 0ms" }],
        is_terminal: false,
        invariants: [],
        options: [
          { option_id: "o_safe", label: "Giao dịch ngắn", action_summary: "Kiểm tra số dư trong khóa", target_node_id: "n_safe_leaf" },
          { option_id: "o_slow", label: "Giữ khóa lâu", action_summary: "Chèn tác vụ chậm", target_node_id: "n_slow_leaf" },
        ],
      },
      {
        id: "n_deadlock",
        parent_id: "root",
        branch_label: "Giữ thứ tự cũ + retry",
        depth: 1,
        origin: "prebuilt_branch",
        answer_alignment: "what_if_branch",
        title: "Giữ thứ tự cũ + retry",
        situation: "T1 giữ 11111 chờ 22222 trong khi T2 giữ 22222 chờ 11111. PostgreSQL phải hủy một bên.",
        consequence_summary: "Tổng số dư vẫn giữ nguyên nhưng phát sinh deadlock.",
        system_impact: "Tăng độ trễ đuôi.",
        tradeoff_note: "Retry chỉ là lớp dự phòng.",
        assumptions_used: ["Ví 11111 = 200, Ví 22222 = 200."],
        state_delta: "Deadlock 40P01",
        trace_steps: [{ actor: "T1 & T2", event: "Chờ chéo deadlock", state_after: "CIRCULAR WAIT", time_label: "t = 5ms (song song)" }],
        is_terminal: true,
        invariants: [
          { category: "safety", name: "Không phát sinh deadlock", status: "broken", detail: "Vẫn xảy ra vòng chờ chéo." },
          { category: "safety", name: "Tổng số dư vẫn giữ nguyên", status: "preserved", detail: "Rollback giữ tổng = 400." },
          { category: "operational", name: "Độ trễ đuôi", status: "warning", detail: "Chờ deadlock_timeout làm tăng tail latency." },
        ],
        comparison_note: "Retry không loại bỏ nguyên nhân vòng chờ khóa.",
        options: [],
      },
      {
        id: "n_safe_leaf",
        parent_id: "n_ordered",
        branch_label: "Giao dịch ngắn",
        depth: 2,
        origin: "prebuilt_branch",
        answer_alignment: "what_if_branch",
        title: "Giao dịch ngắn",
        situation: "T1 hoàn tất nhanh và nhả khóa; T2 tiếp tục đọc số dư mới nhất.",
        consequence_summary: "Cả hai giao dịch thành công sạch sẽ.",
        system_impact: "Ổn định.",
        tradeoff_note: "Giữ transaction ngắn.",
        assumptions_used: ["Ví 11111 = 200, Ví 22222 = 200."],
        state_delta: "Tổng = 400, Deadlocks = 0",
        trace_steps: [{ actor: "T1", event: "COMMIT & nhả khóa", state_after: "tổng = 400", time_label: "t = 5ms" }],
        is_terminal: true,
        invariants: [
          { category: "safety", name: "Không phát sinh deadlock.", status: "preserved", detail: "Không có vòng chờ." },
          { category: "safety", name: "Tổng số dư vẫn giữ nguyên.", status: "preserved", detail: "Tổng luôn = 400." },
          { category: "operational", name: "Vận hành ổn định", status: "preserved", detail: "Cửa sổ khóa hẹp, không nghẽn kết nối." },
        ],
        comparison_note: "An toàn cả dữ liệu và vận hành.",
        options: [],
      },
      {
        id: "n_slow_leaf",
        parent_id: "n_ordered",
        branch_label: "Giữ khóa lâu",
        depth: 2,
        origin: "prebuilt_branch",
        answer_alignment: "what_if_branch",
        title: "Giữ khóa lâu",
        situation: "Giao dịch chờ tác vụ chậm trước khi nhả khóa.",
        consequence_summary: "Dữ liệu đúng nhưng giữ kết nối lâu.",
        system_impact: "Nghẽn connection pool.",
        tradeoff_note: "Đưa tác vụ chậm ra ngoài transaction.",
        assumptions_used: ["Ví 11111 = 200, Ví 22222 = 200."],
        state_delta: "lock held 2000ms",
        trace_steps: [{ actor: "T2", event: "Chờ khóa dòng 11111", state_after: "lock = chờ", time_label: "t = 4ms (song song)" }],
        is_terminal: true,
        invariants: [
          { category: "safety", name: "Tổng số dư vẫn giữ nguyên", status: "preserved", detail: "Tổng số dư vẫn là 400." },
          { category: "operational", name: "Nguy cơ nghẽn kết nối", status: "warning", detail: "Giữ khóa lâu, có nguy cơ nghẽn kết nối." },
        ],
        comparison_note: "Tránh giữ khóa qua I/O ngoài.",
        options: [],
      },
    ],
  };
}

test("entry starts in overview showing node names and Đã xem (no eval badges), expands into 2-level detail, navigates children/parent/overview, and restores focus & scroll", async () => {
  const baseRun = makeTransferRun();
  let selectCalls = [];
  let chooseCalls = [];

  const studio = mountReplayStudio({
    initialRun: baseRun,
    api: {
      selectReplayNode: async (runId, nodeId) => {
        selectCalls.push({ runId, nodeId });
        return {
          ...baseRun,
          active_node_id: nodeId,
          visited_node_ids: Array.from(new Set([...baseRun.visited_node_ids, nodeId])),
        };
      },
      chooseReplayOption: async (runId, nodeId, optionId) => {
        chooseCalls.push({ runId, nodeId, optionId });
        const parent = baseRun.nodes.find((n) => n.id === nodeId);
        const opt = parent.options.find((o) => o.option_id === optionId);
        return {
          ...baseRun,
          active_node_id: opt.target_node_id,
          visited_node_ids: Array.from(new Set([...baseRun.visited_node_ids, opt.target_node_id])),
        };
      },
    },
  });

  // 1. Entry opens in overview mode even when reopening a run whose saved active_node_id != root.
  assert.equal(studio.querySelector("[data-replay-studio]").dataset.viewMode, "overview");
  assert.equal(studio.querySelector("#replay-overview-layer").hidden, false);
  assert.equal(studio.querySelector("#replay-detail-layer").hidden, true);
  assert.equal(studio.querySelector("#replay-parent-btn").hidden, true);

  // Overview nodes show names + "Đã xem" text, and NEVER show Safety/Operational badges.
  const overviewText = collectText(studio.querySelector("#replay-tree-nav"));
  assert.match(overviewText, /Khóa theo thứ tự ID/);
  assert.match(overviewText, /Đã xem/);
  assert.doesNotMatch(overviewText, /Vận hành:/);
  assert.doesNotMatch(overviewText, /Dữ liệu:/);

  // Overview auto-fits tree to viewport cleanly and supports manual zoom preservation across detail -> overview.
  assert.match(studio.querySelector("#replay-zoom-level").textContent, /118%/);
  await studio.querySelector("#replay-zoom-out").trigger("click");
  assert.equal(studio.querySelector("#replay-zoom-level").textContent, "103%");

  // 2. Click intermediate node "Khóa theo thứ tự ID" -> opens detail view with direct children & "+ Đề xuất nhánh" (composer closed).
  const orderedBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_ordered"
  );
  assert.ok(orderedBtn);
  await orderedBtn.trigger("click");

  assert.equal(studio.querySelector("[data-replay-studio]").dataset.viewMode, "detail");
  assert.equal(studio.querySelector("#replay-overview-layer").hidden, true);
  assert.equal(studio.querySelector("#replay-detail-layer").hidden, false);
  assert.equal(studio.querySelector("#replay-node-title").textContent, "Khóa theo thứ tự ID");
  assert.equal(studio.querySelector("#replay-node-title").focused, true);
  assert.equal(studio.querySelector("#replay-parent-btn").hidden, false);
  assert.equal(studio.querySelector("#replay-sim-details").open, false);
  assert.equal(studio.querySelector("#replay-custom-panel").hidden, true);

  // Direct children + "+ Đề xuất nhánh" appear right below summary.
  const childButtons = findByTag(studio.querySelector("#replay-children-list"), "button");
  const childTexts = childButtons.map((b) => collectText(b));
  assert.ok(childTexts.some((t) => t.includes("Giao dịch ngắn")));
  assert.ok(childTexts.some((t) => t.includes("Giữ khóa lâu")));
  assert.ok(childTexts.some((t) => t.includes("+ Đề xuất nhánh")));

  // 3. Click direct child "Giữ khóa lâu" -> opens terminal detail view with Dữ liệu / Vận hành lines & 2 badges.
  const slowChildBtn = childButtons.find((b) => b.dataset.nodeId === "n_slow_leaf");
  assert.ok(slowChildBtn);
  await slowChildBtn.trigger("click");
  assert.equal(chooseCalls.length, 1);
  assert.equal(studio.querySelector("#replay-node-title").textContent, "Giữ khóa lâu");
  assert.equal(studio.querySelector("#replay-terminal-verdict").hidden, false);
  assert.equal(studio.querySelector("#replay-verdict-safety").textContent, "Tổng số dư vẫn là 400.");
  assert.equal(studio.querySelector("#replay-verdict-operational").textContent, "Giữ khóa lâu, có nguy cơ nghẽn kết nối.");
  const badgesText = collectText(studio.querySelector("#replay-verdict-badges"));
  assert.match(badgesText, /Dữ liệu: Bảo toàn/);
  assert.match(badgesText, /Vận hành: Có rủi ro/);

  // Level 2 simulation details remain collapsed by default and contain trace/criteria when inspected.
  assert.equal(studio.querySelector("#replay-sim-details").open, false);
  const detailsText = collectText(studio.querySelector("#replay-sim-details-body"));
  assert.match(detailsText, /Chờ khóa/);
  assert.match(detailsText, /Nguy cơ nghẽn kết nối/);

  // 4. "Về nhánh trước" navigates cleanly back to parent node from a terminal node.
  await studio.querySelector("#replay-terminal-parent-btn").trigger("click");
  assert.equal(studio.querySelector("#replay-node-title").textContent, "Khóa theo thứ tự ID");

  // 5. "Toàn cây" restores overview, preserves manual zoom level, and returns focus to closed node card.
  await studio.querySelector("#replay-overview-btn").trigger("click");
  assert.equal(studio.querySelector("[data-replay-studio]").dataset.viewMode, "overview");
  assert.equal(studio.querySelector("#replay-zoom-level").textContent, "103%");
  const refocusedTreeBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_ordered"
  );
  assert.equal(refocusedTreeBtn.focused, true);

  // Clicking "Vừa khung" re-fits smoothly back to auto-fit scale.
  await studio.querySelector("#replay-zoom-fit").trigger("click");
  assert.equal(studio.querySelector("#replay-zoom-level").textContent, "118%");
});

test("single violated safety invariant names that exact condition, and missing operational data shows Chưa có kết luận", async () => {
  const baseRun = makeTransferRun();
  // Remove operational invariants from n_slow_leaf to simulate missing/legacy operational data.
  const legacyRun = {
    ...baseRun,
    nodes: baseRun.nodes.map((n) =>
      n.id === "n_slow_leaf"
        ? { ...n, invariants: n.invariants.filter((i) => i.category !== "operational") }
        : n
    ),
  };

  const studio = mountReplayStudio({
    initialRun: legacyRun,
    api: {
      selectReplayNode: async (_runId, nodeId) => ({ ...legacyRun, active_node_id: nodeId }),
    },
  });

  // Open single-violation node n_deadlock
  const deadlockBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_deadlock"
  );
  await deadlockBtn.trigger("click");
  const safetyLine = studio.querySelector("#replay-verdict-safety").textContent;
  assert.match(safetyLine, /Không phát sinh deadlock/);
  assert.match(safetyLine, /Tổng số dư vẫn giữ nguyên/);
  assert.doesNotMatch(safetyLine, /\.,|\.\./);

  // Open multi-preserved node whose names end in periods -> no ".," or ".." punctuation artifacts
  await studio.querySelector("#replay-overview-btn").trigger("click");
  const safeBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_safe_leaf"
  );
  await safeBtn.trigger("click");
  const safeLine = studio.querySelector("#replay-verdict-safety").textContent;
  assert.doesNotMatch(safeLine, /\.,|\.\./);

  // Return to overview and open legacy node missing operational criteria
  await studio.querySelector("#replay-overview-btn").trigger("click");
  const slowBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_slow_leaf"
  );
  await slowBtn.trigger("click");
  assert.equal(studio.querySelector("#replay-verdict-operational").textContent, "Chưa có kết luận");
  assert.doesNotMatch(collectText(studio.querySelector("#replay-verdict-badges")), /Ổn định/);
});

test("slow node fetch displays Đang mở nhánh… inside expanded node, and failed fetch offers Thử lại + recovery", async () => {
  const baseRun = makeTransferRun();
  let resolveFetch;
  let shouldFail = true;

  const studio = mountReplayStudio({
    initialRun: baseRun,
    api: {
      selectReplayNode: (_runId, nodeId) =>
        new Promise((resolve, reject) => {
          resolveFetch = () => {
            if (shouldFail) {
              reject(new Error("Mất kết nối tạm thời."));
            } else {
              resolve({ ...baseRun, active_node_id: nodeId });
            }
          };
        }),
    },
  });

  const deadlockBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_deadlock"
  );
  const openPromise = deadlockBtn.trigger("click");

  // Flush microtasks after morphPromise (instant in reduced motion) to inspect loading state
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(studio.querySelector("#replay-detail-layer").hidden, false);
  assert.equal(studio.querySelector("#replay-detail-loading").hidden, false);
  assert.equal(studio.querySelector("#replay-detail-content").hidden, true);

  // Reject fetch -> error panel with Thử lại appears
  resolveFetch();
  await openPromise;
  assert.equal(studio.querySelector("#replay-detail-loading").hidden, true);
  assert.equal(studio.querySelector("#replay-detail-error").hidden, false);
  assert.match(studio.querySelector("#replay-detail-error-msg").textContent, /Mất kết nối tạm thời/);

  // Retry succeeds -> content reveals
  shouldFail = false;
  const retryPromise = studio.querySelector("#replay-detail-retry-btn").trigger("click");
  await new Promise((r) => setTimeout(r, 0));
  resolveFetch();
  await retryPromise;
  assert.equal(studio.querySelector("#replay-detail-error").hidden, true);
  assert.equal(studio.querySelector("#replay-detail-content").hidden, false);
  assert.equal(studio.querySelector("#replay-node-title").textContent, "Giữ thứ tự cũ + retry");
});

test("custom branch opens on demand, shows pending status, preserves input & quota on failure with Thử lại, attaches under parent on success, and reports exhausted quota", async () => {
  let currentRun = { ...makeTransferRun(), custom_branches_used: 1, custom_branch_limit: 2 };
  let shouldFail = true;
  let pendingResolve = null;

  const studio = mountReplayStudio({
    initialRun: currentRun,
    api: {
      selectReplayNode: async (_runId, nodeId) => {
        currentRun = {
          ...currentRun,
          active_node_id: nodeId,
        };
        return currentRun;
      },
      addCustomReplayBranch: (_runId, parentId, text) =>
        new Promise((resolve, reject) => {
          pendingResolve = () => {
            if (shouldFail) {
              reject(new Error("Quá thời gian mô phỏng."));
            } else {
              const customNode = {
                id: "custom_1",
                parent_id: parentId,
                branch_label: `Tự thử: ${text}`,
                depth: 2,
                origin: "custom_user_branch",
                answer_alignment: "what_if_branch",
                title: "Nhánh tự đề xuất",
                situation: "Áp dụng SET LOCAL lock_timeout 500ms trong giao dịch.",
                consequence_summary: "Fail-fast khi nghẽn.",
                system_impact: "Giảm treo pool.",
                tradeoff_note: "Cần retry khi timeout.",
                assumptions_used: ["PostgreSQL"],
                state_delta: "lock_timeout = 500ms",
                trace_steps: [{ actor: "T2", event: "Timeout nhanh", state_after: "fail-fast", time_label: "t = 500ms" }],
                is_terminal: true,
                invariants: [
                  { category: "safety", name: "Tổng số dư vẫn giữ nguyên", status: "preserved", detail: "Tổng = 400." },
                  { category: "operational", name: "Chống treo kết nối", status: "preserved", detail: "Fail-fast an toàn." },
                ],
                comparison_note: "An toàn vận hành hơn.",
                options: [],
                user_proposal: text,
              };
              const updatedNodes = currentRun.nodes.map((n) =>
                n.id === parentId
                  ? {
                      ...n,
                      options: [
                        ...n.options,
                        { option_id: "opt_c1", label: customNode.branch_label, action_summary: text, target_node_id: "custom_1" },
                      ],
                    }
                  : n
              );
              currentRun = {
                ...currentRun,
                active_node_id: "custom_1",
                visited_node_ids: [...currentRun.visited_node_ids, "custom_1"],
                custom_branches_used: 2,
                custom_branch_limit: 2,
                nodes: [...updatedNodes, customNode],
              };
              resolve(currentRun);
            }
          };
        }),
    },
  });

  // Open intermediate node n_ordered
  const orderedBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_ordered"
  );
  await orderedBtn.trigger("click");
  assert.equal(studio.querySelector("#replay-custom-panel").hidden, true);

  // Click "+ Đề xuất nhánh" to open composer on demand
  const proposeBtn = findByTag(studio.querySelector("#replay-children-list"), "button").find(
    (b) => b.id === "replay-propose-btn"
  );
  assert.ok(proposeBtn);
  await proposeBtn.trigger("click");
  assert.equal(studio.querySelector("#replay-custom-panel").hidden, false);

  // Submit and check pending indicator ("Đang mô phỏng phương án…") + duplicate lock
  studio.querySelector("#replay-custom-input").value = "Thêm SET LOCAL lock_timeout = 500ms";
  const failSubmitPromise = studio.querySelector("#replay-custom-form").trigger("submit");
  assert.equal(studio.querySelector("#replay-custom-pending").hidden, false);
  assert.equal(studio.querySelector("#replay-custom-submit").disabled, true);

  // Fail -> input preserved, quota still 1/2, Thử lại button visible
  pendingResolve();
  await failSubmitPromise;
  assert.equal(studio.querySelector("#replay-custom-pending").hidden, true);
  assert.equal(studio.querySelector("#replay-custom-input").value, "Thêm SET LOCAL lock_timeout = 500ms");
  assert.match(studio.querySelector("#replay-custom-quota").textContent, /1\/2/);
  assert.equal(studio.querySelector("#replay-custom-retry-btn").hidden, false);

  // Retry succeeds -> opens AI terminal node with identification line and submitted proposal in details
  shouldFail = false;
  const okRetryPromise = studio.querySelector("#replay-custom-retry-btn").trigger("click");
  pendingResolve();
  await okRetryPromise;
  assert.equal(studio.querySelector("#replay-node-ai-tag").hidden, false);
  assert.match(collectText(studio.querySelector("#replay-sim-details-body")), /Thêm SET LOCAL lock_timeout = 500ms/);

  // Navigate back to parent -> quota is exhausted (2/2) at action, created branch still selectable!
  await studio.querySelector("#replay-terminal-parent-btn").trigger("click");
  const updatedProposeBtn = findByTag(studio.querySelector("#replay-children-list"), "button").find(
    (b) => b.id === "replay-propose-btn"
  );
  assert.equal(updatedProposeBtn.disabled, true);
  assert.equal(studio.querySelector("#replay-custom-exhausted-note").hidden, false);
  assert.ok(
    findByTag(studio.querySelector("#replay-children-list"), "button").some(
      (b) => b.dataset.nodeId === "custom_1"
    )
  );
});

test("submitted answer modal formats paragraphs & code blocks, highlights quote, closes on Escape, and returns focus", async () => {
  const baseRun = makeTransferRun();
  const studio = mountReplayStudio({ initialRun: baseRun, api: {} });

  const openBtn = studio.querySelector("#replay-open-answer-btn");
  const dialog = studio.querySelector("#replay-answer-dialog");
  const closeBtn = studio.querySelector("#replay-close-answer-btn");

  assert.equal(dialog.hidden, true);
  openBtn.focus();
  await openBtn.trigger("click");

  assert.equal(dialog.hidden, false);
  assert.equal(closeBtn.focused, true);

  const answerBody = studio.querySelector("#replay-answer-source");
  const paragraphs = findByTag(answerBody, "p");
  const preBlocks = findByTag(answerBody, "pre");
  const marks = findByTag(answerBody, "mark");
  assert.equal(paragraphs.length, 1);
  assert.equal(preBlocks.length, 1);
  assert.equal(marks.length, 1);
  assert.equal(collectText(marks[0]), "khóa theo thứ tự ID");
  assert.match(collectText(preBlocks[0]), /ORDER BY wallet_id FOR UPDATE/);

  // Escape closes dialog and restores focus to trigger button
  openBtn.focused = false;
  await studio.doc.triggerKeydown({ key: "Escape" });
  assert.equal(dialog.hidden, true);
  assert.equal(openBtn.focused, true);
});

test("brand-new run hides deeper Depth-2 branches behind +N nhánh until learner explores or unfolds them", async () => {
  const brandNewRun = {
    ...makeTransferRun(),
    active_node_id: "root",
    active_path_ids: ["root"],
    visited_node_ids: ["root"],
    generation_status: "ready",
  };

  const studio = mountReplayStudio({
    initialRun: brandNewRun,
    api: {
      selectReplayNode: async (_runId, nodeId) => ({
        ...brandNewRun,
        active_node_id: nodeId,
        visited_node_ids: ["root", nodeId],
      }),
    },
  });

  // Initially ONLY Root + Depth-1 are rendered; Depth-2 leaves stay hidden behind "+2 nhánh".
  const initialTreeText = collectText(studio.querySelector("#replay-tree-nav"));
  assert.match(initialTreeText, /Khóa theo thứ tự ID/);
  assert.match(initialTreeText, /\+2 nhánh/);
  assert.doesNotMatch(initialTreeText, /Giao dịch ngắn/);
  assert.doesNotMatch(initialTreeText, /Giữ khóa lâu/);

  // Clicking "+2 nhánh" directly unfolds Depth-2 branches onto the tree!
  const expandBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.expandParent === "n_ordered"
  );
  assert.ok(expandBtn);
  await expandBtn.trigger("click");
  const unfoldedText = collectText(studio.querySelector("#replay-tree-nav"));
  assert.match(unfoldedText, /Giao dịch ngắn/);
  assert.match(unfoldedText, /Giữ khóa lâu/);

  // Clicking the fold "−" pill collapses them back cleanly.
  const foldBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.foldParent === "n_ordered"
  );
  assert.ok(foldBtn);
  await foldBtn.trigger("click");
  assert.doesNotMatch(collectText(studio.querySelector("#replay-tree-nav")), /Giao dịch ngắn/);

  // Opening "Khóa theo thứ tự ID" and returning to Toàn cây automatically unfolds its discovered children.
  const orderedBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_ordered"
  );
  await orderedBtn.trigger("click");
  await studio.querySelector("#replay-overview-btn").trigger("click");
  assert.match(collectText(studio.querySelector("#replay-tree-nav")), /Giao dịch ngắn/);
});

test("async generating run renders skeleton branches immediately, polls until ready, and supports retry after failure", async () => {
  const readyRun = {
    ...makeTransferRun(),
    active_node_id: "root",
    active_path_ids: ["root"],
    visited_node_ids: ["root"],
    generation_status: "ready",
  };
  const pendingRun = {
    run_id: readyRun.run_id,
    root_node_id: "root",
    active_node_id: "root",
    active_path_ids: ["root"],
    visited_node_ids: ["root"],
    generation_status: "generating",
    generation_error: null,
    nodes: [
      {
        id: "root",
        parent_id: null,
        branch_label: "Điểm xuất phát",
        depth: 0,
        origin: "answer_start",
        answer_alignment: "unspecified",
        title: "Điểm xuất phát",
        situation: "Đang khởi tạo…",
        consequence_summary: "",
        system_impact: "",
        tradeoff_note: "",
        options: [],
      },
    ],
  };

  let pollPhase = 0;
  let retried = false;
  const studio = mountReplayStudio({
    initialRun: pendingRun,
    api: {
      getReplayRun: async () => {
        pollPhase += 1;
        if (pollPhase === 1) {
          return { ...pendingRun, generation_status: "failed", generation_error: "AI quá thời gian." };
        }
        return readyRun;
      },
      retryReplayGeneration: async () => {
        retried = true;
        return pendingRun;
      },
    },
  });

  // Immediately shows generating banner and 3 skeleton branch placeholders without blocking entry.
  assert.equal(studio.querySelector("#replay-gen-status").hidden, false);
  const skeletons = findByTag(studio.querySelector("#replay-tree-nav"), "div").filter((n) =>
    (n.className || "").includes("dtree__skeleton")
  );
  assert.equal(skeletons.length, 3);

  // First poll fails -> shows error & Thử tạo lại button.
  await studio.runPendingTimers();
  assert.equal(studio.querySelector("#replay-gen-status").hidden, true);
  assert.equal(studio.querySelector("#replay-gen-error").hidden, false);
  assert.match(studio.querySelector("#replay-gen-error-msg").textContent, /AI quá thời gian/);

  // Clicking Thử tạo lại re-enters generating skeleton state and polls until ready!
  await studio.querySelector("#replay-gen-retry-btn").trigger("click");
  assert.equal(retried, true);
  assert.equal(studio.querySelector("#replay-gen-status").hidden, false);

  await studio.runPendingTimers();
  assert.equal(studio.querySelector("#replay-gen-status").hidden, true);
  assert.equal(studio.querySelector("#replay-gen-error").hidden, true);
  const treeText = collectText(studio.querySelector("#replay-tree-nav"));
  assert.match(treeText, /Khóa theo thứ tự ID/);
  assert.match(treeText, /\+2 nhánh/);
  assert.doesNotMatch(treeText, /Giao dịch ngắn/);
});

test("auto-fit scales wide trees down to fit the canvas and supports zoom in / out / reset controls", async () => {
  const studio = mountReplayStudio({
    initialRun: makeTransferRun(),
    api: {},
    viewportSize: { w: 720, h: 420 },
    treeSize: { w: 1100, h: 360 },
  });

  // Auto-fit shrinks a 1100px wide tree into a 720px viewport cleanly (approx 60%).
  const initialPct = Number.parseInt(studio.querySelector("#replay-zoom-level").textContent, 10);
  assert.ok(initialPct >= 52 && initialPct <= 68, `Expected auto-fit scale ~60%, got ${initialPct}%`);

  await studio.querySelector("#replay-zoom-in").trigger("click");
  const zoomedInPct = Number.parseInt(studio.querySelector("#replay-zoom-level").textContent, 10);
  assert.equal(zoomedInPct, initialPct + 15);

  await studio.querySelector("#replay-zoom-out").trigger("click");
  assert.equal(Number.parseInt(studio.querySelector("#replay-zoom-level").textContent, 10), initialPct);

  await studio.querySelector("#replay-zoom-in").trigger("click");
  await studio.querySelector("#replay-zoom-fit").trigger("click");
  assert.equal(Number.parseInt(studio.querySelector("#replay-zoom-level").textContent, 10), initialPct);
});

test("desktop split-view keeps tree interactive on left, highlights active path, switches detail in 1 click, and closes cleanly", async () => {
  const baseRun = makeTransferRun();
  const studio = mountReplayStudio({
    initialRun: baseRun,
    splitView: true,
    api: {
      selectReplayNode: async (_runId, nodeId) => ({
        ...baseRun,
        active_node_id: nodeId,
        visited_node_ids: Array.from(new Set([...baseRun.visited_node_ids, nodeId])),
      }),
    },
  });

  // Clicking a node on desktop opens Split-View while keeping #replay-overview-layer visible!
  const deadlockBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_deadlock"
  );
  await deadlockBtn.trigger("click");

  assert.equal(studio.querySelector("[data-replay-studio]").dataset.viewMode, "detail");
  assert.equal(studio.querySelector("#replay-overview-layer").hidden, false);
  assert.equal(studio.querySelector("#replay-detail-layer").hidden, false);
  assert.equal(studio.querySelector("#replay-node-title").textContent, "Giữ thứ tự cũ + retry");
  assert.match(studio.querySelector("#replay-detail-card").className, /replay-detail-card--danger/);

  // Active path classes are marked from root -> active node on the visible tree.
  const listItems = findByTag(studio.querySelector("#replay-tree-nav"), "li");
  const rootLi = listItems.find((li) => li.dataset.nodeId === "root");
  const deadlockLi = listItems.find((li) => li.dataset.nodeId === "n_deadlock");
  assert.match(rootLi.className, /has-active-child/);
  assert.match(deadlockLi.className, /is-in-path/);

  // Clicking another node directly on the left tree switches the right detail panel in 1 click.
  const safeBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_safe_leaf"
  );
  await safeBtn.trigger("click");
  assert.equal(studio.querySelector("#replay-node-title").textContent, "Giao dịch ngắn");
  assert.match(studio.querySelector("#replay-detail-card").className, /replay-detail-card--safe/);

  const updatedItems = findByTag(studio.querySelector("#replay-tree-nav"), "li");
  assert.match(updatedItems.find((li) => li.dataset.nodeId === "n_ordered").className, /has-active-child/);
  assert.match(updatedItems.find((li) => li.dataset.nodeId === "n_safe_leaf").className, /is-in-path/);

  // Clicking × Đóng returns to full-width overview and restores focus to the closed node card.
  await studio.querySelector("#replay-detail-close-btn").trigger("click");
  assert.equal(studio.querySelector("[data-replay-studio]").dataset.viewMode, "overview");
  assert.equal(studio.querySelector("#replay-detail-layer").hidden, true);
  const closedBtn = findByTag(studio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_safe_leaf"
  );
  assert.equal(closedBtn.focused, true);

  // Escape also closes detail drawer cleanly when no modal/composer is open.
  await closedBtn.trigger("click");
  assert.equal(studio.querySelector("[data-replay-studio]").dataset.viewMode, "detail");
  await studio.doc.triggerKeydown({ key: "Escape" });
  assert.equal(studio.querySelector("[data-replay-studio]").dataset.viewMode, "overview");
});

test("semantic color coding + accessible status tags classify safe/warning/danger and avoid false safe on missing operational data", async () => {
  const baseRun = makeTransferRun();
  const runWithLegacy = {
    ...baseRun,
    nodes: baseRun.nodes.map((n) =>
      n.id === "n_slow_leaf"
        ? { ...n, invariants: n.invariants.filter((i) => i.category !== "operational") }
        : n
    ),
  };

  // Standard run with full operational invariants
  const fullStudio = mountReplayStudio({ initialRun: baseRun, api: {} });
  const fullButtons = findByTag(fullStudio.querySelector("#replay-tree-nav"), "button");
  const safeCard = fullButtons.find((b) => b.dataset.nodeId === "n_safe_leaf");
  const warnCard = fullButtons.find((b) => b.dataset.nodeId === "n_slow_leaf");
  const dangerCard = fullButtons.find((b) => b.dataset.nodeId === "n_deadlock");

  assert.match(safeCard.className, /dtree__node--safe/);
  assert.match(collectText(safeCard), /An toàn/);
  assert.match(warnCard.className, /dtree__node--warning/);
  assert.match(collectText(warnCard), /Cảnh báo/);
  assert.match(dangerCard.className, /dtree__node--danger/);
  assert.match(collectText(dangerCard), /Vi phạm/);

  // Legacy run missing operational invariants must NOT show green "An toàn"
  const legacyStudio = mountReplayStudio({ initialRun: runWithLegacy, api: {} });
  const legacyCard = findByTag(legacyStudio.querySelector("#replay-tree-nav"), "button").find(
    (b) => b.dataset.nodeId === "n_slow_leaf"
  );
  assert.match(legacyCard.className, /dtree__node--neutral/);
  assert.match(collectText(legacyCard), /Chưa rõ/);
  assert.doesNotMatch(collectText(legacyCard), /An toàn/);
});

test("repetitive prefixes are extracted into micro-labels while card labels and detail titles stay crisp", async () => {
  const prefixedRun = {
    ...makeTransferRun(),
    nodes: makeTransferRun().nodes.map((n) => {
      if (n.id === "n_ordered") {
        return { ...n, branch_label: "Nhánh 1: SELECT FOR UPDATE ngắn gọn" };
      }
      if (n.id === "n_deadlock") {
        return { ...n, branch_label: "Kết quả mô phỏng: Bán lố và âm kho (-1)" };
      }
      return n;
    }),
  };

  const studio = mountReplayStudio({
    initialRun: prefixedRun,
    splitView: true,
    api: {
      selectReplayNode: async (_runId, nodeId) => ({ ...prefixedRun, active_node_id: nodeId }),
    },
  });

  const treeBtns = findByTag(studio.querySelector("#replay-tree-nav"), "button");
  const branchBtn = treeBtns.find((b) => b.dataset.nodeId === "n_ordered");
  const leafBtn = treeBtns.find((b) => b.dataset.nodeId === "n_deadlock");

  const branchKicker = findByTag(branchBtn, "span").find((s) => s.className === "dtree__kicker");
  const branchLabel = findByTag(branchBtn, "span").find((s) => s.className === "dtree__label");
  assert.equal(branchKicker.textContent, "Nhánh 1");
  assert.equal(branchLabel.textContent, "SELECT FOR UPDATE ngắn gọn");

  const leafKicker = findByTag(leafBtn, "span").find((s) => s.className === "dtree__kicker");
  const leafLabel = findByTag(leafBtn, "span").find((s) => s.className === "dtree__label");
  assert.equal(leafKicker.textContent, "Hệ quả");
  assert.equal(leafLabel.textContent, "Bán lố và âm kho (-1)");

  await leafBtn.trigger("click");
  assert.equal(studio.querySelector("#replay-node-kicker").textContent, "Hệ quả");
  assert.equal(studio.querySelector("#replay-node-title").textContent, "Bán lố và âm kho (-1)");
  assert.doesNotMatch(collectText(studio.querySelector("#replay-breadcrumbs")), /Kết quả mô phỏng:/);
});

test("segmented control toggles Thu gọn and Toàn cây with synchronized aria-pressed states", async () => {
  const brandNewRun = {
    ...makeTransferRun(),
    active_node_id: "root",
    active_path_ids: ["root"],
    visited_node_ids: ["root"],
    generation_status: "ready",
  };
  const studio = mountReplayStudio({ initialRun: brandNewRun, splitView: true, api: {} });

  const compactBtn = studio.querySelector("#replay-mode-compact");
  const fullBtn = studio.querySelector("#replay-overview-btn");

  assert.equal(compactBtn.getAttribute("aria-pressed"), "true");
  assert.equal(fullBtn.getAttribute("aria-pressed"), "false");
  assert.doesNotMatch(collectText(studio.querySelector("#replay-tree-nav")), /Giao dịch ngắn/);

  // Switch to Toàn cây -> expands all deeper branches
  await fullBtn.trigger("click");
  assert.equal(compactBtn.getAttribute("aria-pressed"), "false");
  assert.equal(fullBtn.getAttribute("aria-pressed"), "true");
  assert.match(collectText(studio.querySelector("#replay-tree-nav")), /Giao dịch ngắn/);

  // Switch back to Thu gọn -> folds deeper branches cleanly
  await compactBtn.trigger("click");
  assert.equal(compactBtn.getAttribute("aria-pressed"), "true");
  assert.equal(fullBtn.getAttribute("aria-pressed"), "false");
  assert.doesNotMatch(collectText(studio.querySelector("#replay-tree-nav")), /Giao dịch ngắn/);
});
