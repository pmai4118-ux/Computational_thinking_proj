// Run against a local fixture preview; does not submit answers or call an AI provider.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const base = process.env.HOMEPAGE_PREVIEW_URL || 'http://127.0.0.1:8015';
const out = path.resolve('../outputs/homepage-stitch');
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_PATH });
  const context = await browser.newContext({ viewport: { width: 1280, height: 1000 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [], requests = [], layouts = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (r.url().startsWith(base)) requests.push({ method: r.method(), url: r.url() }); });
  try {
    await page.goto(base, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('h1').count(), 1);
    assert.equal(await page.locator('.homepage-content section').count(), 3);
    const text = await page.locator('.homepage-content').innerText();
    assert(!/1[,.]200|94[,.]8|15[,.]000|88%|Voice AI|micro|Vượt vòng Tech|Trụ Cột 0/.test(text), 'No fabricated statistics or unsupported voice claims');
    assert.equal(await page.locator('.homepage-content a[href="#"]').count(), 0);
    assert.equal(await page.locator('.homepage-content a[href="/setup"]').count(), 1);
    await page.screenshot({ path: path.join(out, 'homepage-light-desktop.png'), fullPage: true });
    for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const metrics = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
        clipped: [...document.querySelectorAll('.homepage-content a, .homepage-content button')].filter(el => {
          const r = el.getBoundingClientRect(); return r.x < -1 || r.right > innerWidth + 1;
        }).map(el => el.textContent.trim()) }));
      assert(metrics.scroll <= width + 1, `Page overflow: ${JSON.stringify(metrics)}`);
      assert.deepEqual(metrics.clipped, [], `Clipped actions at ${width}px`);
      layouts.push(metrics);
      if (width === 390) await page.screenshot({ path: path.join(out, 'homepage-light-mobile.png'), fullPage: true });
    }
    await page.setViewportSize({ width: 1280, height: 1000 });
    assert.equal(await page.getByText('interviewUS · Luminous Glass', {exact:true}).count(), 0);
    await page.locator('[data-theme-mode="dark"]').click();
    assert.equal(await page.locator('[data-theme-mode="dark"]').getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.screenshot({ path: path.join(out, 'homepage-dark-desktop.png'), fullPage: true });
    await page.locator('[data-theme-mode="light"]').click();
    assert.equal(await page.locator('[data-theme-mode="light"]').getAttribute('aria-pressed'), 'true');
    await page.locator('.homepage-content a[href="/setup"]').click();
    assert.equal(new URL(page.url()).pathname, '/setup');
    await page.locator('#start-session-btn').waitFor({ state: 'visible' });
    await page.goto(`${base}/`);
    await page.locator('.homepage-content a[href="/learning-path"]').click();
    assert.equal(new URL(page.url()).pathname, '/learning-path');
    assert.equal(errors.length, 0, errors.join('\n'));
    assert(!requests.some(r => r.method !== 'GET' || /\/api\/(sessions|evaluations)/.test(r.url)), 'Home must not create a session or request AI evaluation');
    const result = { passed: true, layouts, errors, noBackgroundMutation: true };
    fs.writeFileSync(path.join(out, 'checks.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
