/* Shared presentation of actual asynchronous work. Never simulates scores or progress. */
(() => {
  "use strict";
  const controllers = new Set();
  const element = (tag, className, text) => {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  };

  function mount(id, statusElement) {
    const host = document.getElementById(id);
    if (!host) return null;
    let timer = null;
    let revealTimer = null;
    let startedAt = 0;
    let currentKind = null;
    const art = element("div", "activity-art");
    art.setAttribute("aria-hidden", "true");
    art.append(element("span", "activity-orbit activity-orbit--outer"), element("span", "activity-orbit activity-orbit--inner"), element("span", "activity-core", "✦"));
    const copy = element("div", "activity-copy");
    const eyebrow = element("span", "activity-eyebrow");
    const title = element("h2", "activity-title");
    const description = element("p", "activity-description");
    const steps = element("div", "activity-steps");
    steps.append(element("span", "activity-step is-done", "✓ Bài đã lưu"), element("span", "activity-step is-current", "Đối chiếu rubric"), element("span", "activity-step", "Kết quả"));
    const meter = element("progress", "activity-meter");
    meter.setAttribute("aria-label", "Tiến độ xử lý");
    const footer = element("div", "activity-footer");
    const count = element("span", "activity-count");
    const elapsed = element("span", "activity-elapsed");
    elapsed.setAttribute("aria-hidden", "true");
    footer.append(count, elapsed);
    const skeleton = element("div", "activity-skeleton");
    skeleton.setAttribute("aria-hidden", "true");
    for (let index = 0; index < 3; index++) skeleton.append(element("span", "skeleton-line"));
    copy.append(eyebrow, title, description, steps, meter, footer, skeleton);
    host.replaceChildren(art, copy);
    host.classList.add("activity-card");
    host.hidden = true;

    function tick() {
      const seconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
      elapsed.textContent = seconds > 0 ? `Đã chờ ${seconds}s` : "";
      host.classList.toggle("is-long-wait", seconds >= 20);
    }

    function update(options = {}) {
      const kind = options.kind || currentKind || "loading";
      currentKind = kind;
      host.dataset.state = kind;
      const assessment = kind === "assessment";
      eyebrow.textContent = assessment ? "Đang xử lý bài làm" : kind === "saving" ? "Lưu câu trả lời" : "Chuẩn bị nội dung";
      title.textContent = options.title || (assessment ? "AI đang đối chiếu bài làm" : "Đang tải nội dung");
      description.textContent = options.description || (assessment ? "Bài đã lưu. Bạn có thể quay lại trang này để xem kết quả." : "Chỉ một chút nữa, nội dung của bạn đang được chuẩn bị.");
      steps.hidden = !assessment;
      skeleton.hidden = options.skeleton === false;
      const total = Number(options.total);
      const completed = Number(options.completed);
      const measured = Number.isInteger(total) && total > 0 && Number.isInteger(completed) && completed >= 0 && completed <= total;
      if (measured) {
        meter.max = total;
        meter.value = completed;
        count.textContent = `${completed}/${total} câu đã có kết quả`;
        meter.setAttribute("aria-label", `${completed} trên ${total} câu đã có kết quả`);
      } else {
        meter.removeAttribute("value");
        count.textContent = assessment ? "Kết quả xuất hiện khi đối chiếu hoàn tất" : kind === "saving" ? "Đang chờ xác nhận từ máy chủ" : "Đang kết nối với máy chủ";
        meter.setAttribute("aria-label", "Đang xử lý, chưa có số liệu tiến độ");
      }
    }

    function start(options) {
      update(options);
      if (timer !== null || revealTimer !== null) return;
      startedAt = Date.now();
      tick();
      // Fast responses do not flash a loading card. No response is artificially delayed.
      revealTimer = window.setTimeout(() => {
        revealTimer = null;
        host.hidden = false;
        if (statusElement) statusElement.classList.add("activity-status-sr");
      }, 120);
      timer = window.setInterval(tick, 1000);
    }

    function stop() {
      if (timer !== null) window.clearInterval(timer);
      if (revealTimer !== null) window.clearTimeout(revealTimer);
      timer = null;
      revealTimer = null;
      host.hidden = true;
      host.classList.remove("is-long-wait");
      if (statusElement) statusElement.classList.remove("activity-status-sr");
    }

    const controller = { start, update, stop };
    controllers.add(controller);
    return controller;
  }

  function buttonBusy(button, busy) {
    if (!button) return;
    button.disabled = busy;
    if (busy) button.setAttribute("aria-busy", "true");
    else button.removeAttribute("aria-busy");
  }

  function reveal(target) {
    if (!target || !target.classList) return;
    target.classList.remove("result-reveal");
    // Restart only on a genuine new result, never on progress polling.
    void target.offsetWidth;
    target.classList.add("result-reveal");
  }

  window.addEventListener("pagehide", () => controllers.forEach(controller => controller.stop()));
  window.InterviewActivity = Object.freeze({ mount, buttonBusy, reveal });
})();
