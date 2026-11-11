function renderFlowPage(pages) {
  const data = JSON.stringify(pages.map(({ id, name, summary, svg, nodes }) =>
    ({ id, name, summary, svg, nodes: nodes.map(({ id, title, detail }) => ({ id, title, detail })) })
  )).replace(/</g, '\\u003c');
  return `<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sơ đồ P02 · interviewUS</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;color:#252339;background:#f7f6fc;font:16px/1.55 "Segoe UI",sans-serif}
  main{max-width:1460px;margin:auto;padding:32px clamp(14px,4vw,48px)}
  header{margin-bottom:24px}
  h1,h2,h3,p{margin:0 0 8px}
  h1{font-size:clamp(26px,4vw,38px);letter-spacing:-.03em}
  h2{font-size:23px}
  h3{font-size:18px}
  .summary,.hint{color:#625b77}
  nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:22px}
  button{font:inherit;cursor:pointer;border:1px solid #d9d3eb;border-radius:10px;padding:8px 12px;background:white;color:#3b315c}
  button[aria-pressed=true]{background:#653ab1;color:white;border-color:#653ab1}
  button:focus-visible,[tabindex]:focus-visible{outline:3px solid #7449c6;outline-offset:3px}
  .layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:16px;align-items:start}
  .canvas,aside{background:white;border:1px solid #e4dfef;border-radius:14px}
  .canvas{overflow:auto}
  .canvas svg{display:block;width:100%;min-width:860px;height:auto}
  aside{padding:18px}
  .label{margin:14px 0 2px;font-weight:650}
  .download{margin-top:14px}
  .hint{font-size:14px;margin-bottom:12px}
  @media(max-width:1050px){.layout{grid-template-columns:1fr}}
</style>
</head>
<body>
<main>
  <header><h1>Sơ đồ luồng người dùng P02</h1><p class="summary">interviewUS · Sáu khu vực</p></header>
  <nav id="areas" aria-label="Chọn khu vực"></nav>
  <section aria-labelledby="area-title">
    <h2 id="area-title"></h2>
    <p id="summary" class="summary"></p>
    <p class="hint">Bấm vào một khối để xem chi tiết. Trên màn hình hẹp, cuộn ngang trong sơ đồ.</p>
    <div class="layout">
      <div id="canvas" class="canvas" tabindex="0" aria-label="Sơ đồ cuộn ngang"></div>
      <aside aria-live="polite" id="detail">Chọn một khối để xem thao tác và hướng đi.</aside>
    </div>
    <button class="download" id="download" type="button">Tải sơ đồ SVG</button>
  </section>
</main>
<script id="flow-data" type="application/json">${data}</script>
<script>
  const pages = JSON.parse(document.getElementById('flow-data').textContent);
  const areas = document.getElementById('areas');
  const canvas = document.getElementById('canvas');
  const detail = document.getElementById('detail');
  const buttons = new Map();
  let activePage;

  function selectArea(page) {
    activePage = page;
    for (const [id, button] of buttons) button.setAttribute('aria-pressed', String(id === page.id));
    document.getElementById('area-title').textContent = page.name;
    document.getElementById('summary').textContent = page.summary;
    canvas.innerHTML = page.svg;
    canvas.scrollLeft = 0;
    detail.textContent = 'Chọn một khối để xem thao tác và hướng đi.';
  }

  function selectNode(element) {
    const node = activePage.nodes.find(item => item.id === element.dataset.node);
    if (!node) return;
    for (const item of canvas.querySelectorAll('[data-node]')) {
      item.setAttribute('aria-pressed', String(item === element));
    }
    const title = document.createElement('h3');
    title.textContent = node.title.join(' ');
    detail.replaceChildren(title);
    for (const [label, value] of [['Thao tác', node.detail.action], ['Hướng đi', node.detail.next], ['Lưu ý', node.detail.note]]) {
      if (!value) continue;
      const heading = document.createElement('p');
      heading.className = 'label';
      heading.textContent = label;
      const paragraph = document.createElement('p');
      paragraph.textContent = value;
      detail.append(heading, paragraph);
    }
  }

  for (const page of pages) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = page.name;
    button.addEventListener('click', () => selectArea(page));
    buttons.set(page.id, button);
    areas.append(button);
  }
  canvas.addEventListener('click', event => {
    const node = event.target.closest('[data-node]');
    if (node) selectNode(node);
  });
  canvas.addEventListener('keydown', event => {
    const node = event.target.closest('[data-node]');
    if (!node || !['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    selectNode(node);
  });
  document.getElementById('download').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([activePage.svg], { type: 'image/svg+xml' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'p02-' + activePage.id + '.svg';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  selectArea(pages[0]);
</script>
</body>
</html>`;
}

module.exports = { renderFlowPage };
