"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

class Element {
  constructor(tag = "section") {
    this.tag = tag;
    this.children = [];
    this.attributes = new Map();
    this.classes = new Set();
    this.dataset = {};
    this.hidden = false;
    this.textContent = "";
    this.classList = {
      add: (...names) => names.forEach(name => this.classes.add(name)),
      remove: (...names) => names.forEach(name => this.classes.delete(name)),
      toggle: (name, on) => on ? this.classes.add(name) : this.classes.delete(name),
      contains: name => this.classes.has(name),
    };
  }
  set className(value) { this.classes = new Set(value.split(" ")); }
  get className() { return [...this.classes].join(" "); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(name, value) { this.attributes.set(name, value); }
  removeAttribute(name) { this.attributes.delete(name); }
  find(className) {
    if (this.classes.has(className)) return this;
    for (const child of this.children) { const found = child.find(className); if (found) return found; }
    return null;
  }
}

function activityPage() {
  const host = new Element();
  const status = new Element("p");
  const timeouts = new Map(), intervals = new Map(), events = new Map();
  let nextId = 0, now = 0;
  const window = {
    setTimeout: fn => { timeouts.set(++nextId, fn); return nextId; },
    clearTimeout: id => timeouts.delete(id),
    setInterval: fn => { intervals.set(++nextId, fn); return nextId; },
    clearInterval: id => intervals.delete(id),
    addEventListener: (name, fn) => events.set(name, fn),
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../source/view/static/js/activity.js"), "utf8"), {
    window, Date: { now: () => now },
    document: { createElement: tag => new Element(tag), getElementById: id => id === "activity" ? host : null },
  });
  const controller = window.InterviewActivity.mount("activity", status);
  return { host, status, controller, window, timeouts, intervals,
    reveal() { for (const [id, fn] of [...timeouts]) { timeouts.delete(id); fn(); } },
    tick(seconds) { now += seconds * 1000; for (const fn of intervals.values()) fn(); },
    leave() { events.get("pagehide")(); },
  };
}

test("fast responses cancel delayed loading without flashing or leaving timers", () => {
  const p = activityPage();
  p.controller.start({ kind: "saving", title: "Đang lưu bài" });
  assert.equal(p.host.hidden, true);
  p.controller.stop(); p.reveal();
  assert.equal(p.host.hidden, true);
  assert.equal(p.timeouts.size + p.intervals.size, 0);
  assert.equal(p.status.classList.contains("activity-status-sr"), false);
});

test("assessment shows server counts, keeps them unchanged with elapsed time, and cleans up", () => {
  const p = activityPage();
  p.controller.start({ kind: "assessment", completed: 1, total: 4 }); p.reveal();
  assert.equal(p.host.hidden, false);
  assert.equal(p.host.find("activity-count").textContent, "1/4 câu đã có kết quả");
  p.tick(45);
  assert.equal(p.host.find("activity-count").textContent, "1/4 câu đã có kết quả");
  assert.equal(p.host.find("activity-elapsed").textContent, "Đã chờ 45s");
  p.controller.update({ kind: "assessment", completed: 2, total: 4 });
  assert.equal(p.host.find("activity-meter").value, 2);
  p.leave();
  assert.equal(p.host.hidden, true);
  assert.equal(p.timeouts.size + p.intervals.size, 0);
});

test("unknown progress stays indeterminate and user-provided text is rendered as text", () => {
  const p = activityPage();
  p.controller.start({ kind: "assessment", title: "<script>literal</script>" }); p.reveal();
  assert.equal(p.host.find("activity-title").textContent, "<script>literal</script>");
  assert.equal(p.host.find("activity-meter").attributes.has("value"), false);
  assert.equal(p.host.find("activity-count").textContent.includes("%"), false);
  assert.equal(p.window.InterviewActivity.mount("missing"), null);
});
