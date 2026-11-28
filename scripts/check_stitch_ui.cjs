// Requires a local fixture app and Playwright; never use against a live-provider instance.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');

const preview = process.env.STITCH_PREVIEW_URL || 'http://127.0.0.1:8011';
const check = (value, message) => {
  if (!value) throw new Error(message);
};

async function checkShellAndAlignment(page, routeName) {
  check((await page.locator('#app-sidebar').count()) === 0, `${routeName}: global sidebar must be removed`);
  check((await page.locator('#sidebar-toggle').count()) === 0, `${routeName}: sidebar toggle must be removed`);
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const metrics = await page.evaluate(() => {
    const header = document.querySelector('.site-header__inner')?.getBoundingClientRect();
    const main = document.querySelector('#main-content')?.getBoundingClientRect();
    const footer = document.querySelector('.site-footer__inner')?.getBoundingClientRect();
    const nav = document.querySelector('.site-nav');
    const navRect = nav?.getBoundingClientRect();
    const navDisplay = nav ? getComputedStyle(nav).display : 'none';
    const bodyBg = getComputedStyle(document.body).backgroundImage;
    return {
      innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      headerWidth: header?.width || 0,
      mainWidth: main?.width || 0,
      footerWidth: footer?.width || 0,
      headerLeft: Math.round(header?.left || 0),
      mainLeft: Math.round(main?.left || 0),
      footerLeft: Math.round(footer?.left || 0),
      navDisplay,
      navHeight: navRect?.height || 0,
      hasBodyBg: Boolean(bodyBg && bodyBg !== 'none'),
    };
  });
  check(metrics.scrollWidth <= metrics.innerWidth + 1, `${routeName}: horizontal overflow ${JSON.stringify(metrics)}`);
  check(metrics.navDisplay !== 'none' && metrics.navHeight > 0, `${routeName}: top navigation must stay visible ${JSON.stringify(metrics)}`);
  check(metrics.hasBodyBg, `${routeName}: body must have full-web ambient background`);
  check(Math.abs(metrics.headerLeft - metrics.mainLeft) <= 2 && Math.abs(metrics.footerLeft - metrics.mainLeft) <= 2,
    `${routeName}: header/main/footer container alignment mismatch ${JSON.stringify(metrics)}`);
  if (metrics.innerWidth >= 1900) {
    const ratio = metrics.mainWidth / metrics.innerWidth;
    check(ratio >= 0.78 && ratio <= 0.85, `${routeName}: expected ~80% window width on 1920px, got ${ratio.toFixed(3)}`);
  }
  return metrics;
}

(async () => {
  const out = path.resolve(process.env.STITCH_OUTPUT_DIR || '../outputs/stitch-ui');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}),
  });
  const errors = [];
  const totals = { lessons: 0, units: 0, practices: 0 };
  const layouts = [];
  try {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      permissions: ['clipboard-read', 'clipboard-write'],
      reducedMotion: 'reduce',
    });
    const page = await context.newPage();
    page.on('pageerror', (error) => errors.push(error.message));

    // 1. Welcome page (/) and Interview Intro (/interview) -> Setup (/setup)
    await page.goto(`${preview}/`);
    await checkShellAndAlignment(page, 'home-desktop');
    await page.screenshot({ path: path.join(out, 'home-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 390, height: 900 });
    await checkShellAndAlignment(page, 'home-mobile');
    await page.screenshot({ path: path.join(out, 'home-mobile.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 1920, height: 1080 });

    await page.goto(`${preview}/interview`);
    await checkShellAndAlignment(page, 'interview-desktop');
    check((await page.locator('#open-interview-setup').getAttribute('href')) === '/setup', 'interview landing opens setup');
    await page.screenshot({ path: path.join(out, 'interview-desktop.png'), fullPage: false, animations: 'disabled' });

    // 2. Learning path (/learning-path)
    await page.goto(`${preview}/learning-path`);
    await page.locator('#learning-content').waitFor();
    check((await page.locator('#baseline-heading').textContent()).includes('Kiểm tra kiến thức nền tảng Backend Java'), 'baseline assessment heading');
    check((await page.locator('#baseline-start-btn').getAttribute('href')) === '/setup', 'baseline assessment links to /setup');
    check((await page.locator('#plan-config-tag').textContent()).trim() === 'Chưa thiết lập', 'initial plan tag unconfigured');
    check((await page.locator('.learning-lesson').count()) === 24, '24 nodes');
    for (let phase = 0; phase < 5; phase += 1) {
      await page.locator('.phase-button').nth(phase).click();
      const ids = await page.locator('.learning-lesson:visible').evaluateAll((rows) => rows.map((x) => x.id));
      for (const id of ids) {
        await page.locator(`#${id} .lesson-trigger`).click();
        await page.locator('#lesson-dialog').waitFor();
        totals.lessons += 1;
        totals.units += await page.locator('.learning-units-list > li').count();
        totals.practices += await page.locator('.learning-practice').count();
        check(
          await page.locator('#lesson-body a').evaluateAll((anchors) => anchors.every((x) => x.href.startsWith('https://') && x.rel.includes('noopener'))),
          `safe sourced links ${id}`
        );
        await page.keyboard.press('Escape');
      }
    }
    check(totals.units === 78 && totals.practices === 48, `complete lesson content ${JSON.stringify(totals)}`);
    await page.locator('.phase-button').first().click();
    await page.locator('#lesson-JB01 .lesson-trigger').click();
    await page.check('#lesson-complete');
    const firstCheck = page.locator('#lesson-body .stitch-check-btn').first();
    await firstCheck.click();
    check((await firstCheck.getAttribute('aria-pressed')) === 'true', 'lesson unit check toggles');
    await page.click('#next-lesson');
    check((await page.locator('#lesson-dialog-meta').textContent()).startsWith('JB02'), 'next reader lesson');
    await page.screenshot({ path: path.join(out, 'lesson-detail-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 390, height: 900 });
    await page.screenshot({ path: path.join(out, 'lesson-detail-mobile.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.keyboard.press('Escape');
    await page.locator('#lesson-dialog').waitFor({ state: 'hidden' });
    await page.reload();
    await page.locator('#learning-content').waitFor();
    check((await page.locator('#phase-progress-label').textContent()).startsWith('1/'), 'self-report persisted');
    check(await page.locator('#lesson-JB01').evaluate((el) => el.classList.contains('is-complete')), 'completed lesson marked after reload');
    await page.locator('#lesson-JB01 .lesson-trigger').click();
    check((await page.locator('#lesson-body .stitch-check-btn').first().getAttribute('aria-pressed')) === 'true', 'lesson unit check persisted');
    await page.keyboard.press('Escape');

    await page.click('#open-learning-settings');
    await page.click('[data-track-chip="foundation"]');
    check((await page.inputValue('#learning-track')) === 'foundation', 'track chip syncs select');
    await page.click('[data-hours="15"]');
    check((await page.inputValue('#learning-hours')) === '15', 'hours chip syncs input');
    await page.click('[data-weeks="8"]');
    check((await page.inputValue('#learning-weeks')) === '8', 'weeks chip syncs input');
    await page.fill('#learning-hours', '1');
    await page.fill('#learning-weeks', '1');
    await page.check('#learning-confirm');
    await page.click('#create-plan');
    await page.locator('#learning-settings').waitFor({ state: 'hidden' });
    check((await page.locator('.learning-warning').count()) === 1, 'shortfall visible');
    check((await page.locator('#plan-config-tag').textContent()).trim() === 'Đã thiết lập', 'plan tag updates to configured');

    await page.click('#open-learning-settings');
    await page.selectOption('#learning-track', 'advanced');
    await page.fill('#learning-hours', '40');
    await page.fill('#learning-weeks', '20');
    check(!(await page.isChecked('#learning-confirm')), 'reconfirm changed form');
    await page.check('#learning-confirm');
    await page.click('#create-plan');
    await page.locator('#learning-settings').waitFor({ state: 'hidden' });
    check((await page.locator('.learning-warning').count()) === 0, 'feasible budget');

    await page.click('#open-learning-settings');
    await page.fill('#learning-hours', '5');
    await page.click('#cancel-learning-settings');
    await page.click('#open-learning-settings');
    check((await page.inputValue('#learning-hours')) === '40', 'cancel restores settings');
    await page.keyboard.press('Escape');

    await page.click('#open-learning-settings');
    await page.route('**/api/learning-paths/plan', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: '{"message":"Thử lỗi mạng"}' }));
    await page.fill('#learning-hours', '7');
    await page.check('#learning-confirm');
    await page.click('#create-plan');
    await page.locator('#settings-error').waitFor();
    check((await page.inputValue('#learning-hours')) === '7', 'plan error retains form');
    check(await page.isEnabled('#create-plan'), 'retry enabled');
    await page.unroute('**/api/learning-paths/plan');
    await page.click('#cancel-learning-settings');

    await page.fill('#lesson-search', 'transaction');
    check((await page.locator('.learning-lesson:visible').count()) > 0, 'search works');
    await page.fill('#lesson-search', '');

    for (const width of [1920, 1600, 1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1050 });
      const dims = await checkShellAndAlignment(page, `roadmap-${width}`);
      layouts.push({ route: 'roadmap', width, scroll: dims.scrollWidth });
    }
    await page.setViewportSize({ width: 390, height: 900 });
    await page.screenshot({ path: path.join(out, 'roadmap-mobile.png'), fullPage: false, animations: 'disabled' });
    await page.click('#open-learning-settings');
    await page.screenshot({ path: path.join(out, 'settings-mobile.png'), fullPage: false, animations: 'disabled' });
    await page.keyboard.press('Escape');

    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: path.join(out, 'roadmap-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.click('#open-learning-settings');
    await page.screenshot({ path: path.join(out, 'settings-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.keyboard.press('Escape');
    await page.locator('#lesson-JB01 .lesson-trigger').click();
    await page.screenshot({ path: path.join(out, 'lesson-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.keyboard.press('Escape');

    check((await page.locator('.badge--demo').first().textContent()).includes('Dữ liệu minh họa'), 'This smoke test requires EVALUATION_PROVIDER=fixture.');

    // 3. Setup, Workspace, Review, Summary
    const evaluateRequests = [];
    page.on('request', (req) => {
      if (req.method() === 'POST' && req.url().endsWith('/evaluate')) evaluateRequests.push(req.url());
    });

    await page.goto(`${preview}/setup`);
    check((await page.locator('body').evaluate((e) => getComputedStyle(e).fontFamily)).startsWith('"Be Vietnam Pro"'), 'Vietnamese font shared');
    await checkShellAndAlignment(page, 'setup-desktop');
    check((await page.locator('.session-history').count()) === 0, 'setup hides session history');
    await page.screenshot({ path: path.join(out, 'setup-desktop.png'), fullPage: false, animations: 'disabled' });

    await page.click('#start-session-btn');
    await page.waitForURL(/\/sessions\/[^/]+$/);
    const sessionId = page.url().split('/').at(-1);
    await checkShellAndAlignment(page, 'workspace-desktop');
    await page.locator('.argument-box__textarea').first().fill('Tôi phân tích giả định, so sánh giải pháp và xác minh kết quả bằng bằng chứng. 😀 <script>alert(1)</script>');
    await page.reload();
    check((await page.locator('.argument-box__textarea').first().inputValue()).includes('😀'), 'outline draft survives reload');
    await page.screenshot({ path: path.join(out, 'workspace-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 390, height: 1000 });
    await checkShellAndAlignment(page, 'workspace-mobile');
    await page.screenshot({ path: path.join(out, 'workspace-mobile.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 1920, height: 1080 });

    await page.click('#submit-answer');
    await page.waitForURL(/\/review/);
    await page.locator('#next-question').waitFor();
    check(evaluateRequests.length === 0, 'no AI before end');

    await page.click('#next-question');
    await page.waitForURL(new RegExp(`/sessions/${sessionId}$`));
    await page.locator('#end-session').click();
    await page.locator('#confirm-end-session').click();
    await page.waitForURL(/\/summary/);
    await page.waitForFunction(() => document.querySelector('#coverage-count')?.textContent.includes('Có kết quả 1 /'), null, { timeout: 15000 });
    check(evaluateRequests.length > 0, 'summary assesses after end');
    await checkShellAndAlignment(page, 'summary-desktop');
    const toggleBtn = page.locator('#toggle-outcomes-btn');
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
      check((await toggleBtn.getAttribute('aria-pressed')) === 'true', 'summary expand all works');
      await toggleBtn.click();
    }
    await page.screenshot({ path: path.join(out, 'summary-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 390, height: 1000 });
    await checkShellAndAlignment(page, 'summary-mobile');
    await page.screenshot({ path: path.join(out, 'summary-mobile.png'), fullPage: false, animations: 'disabled' });
    await page.setViewportSize({ width: 1920, height: 1080 });

    await page.goto(`${preview}/setup`);
    await page.click('#mode-card-guided');
    await page.click('#start-session-btn');
    await page.waitForURL(/\/sessions\/[^/]+$/);
    await page.locator('.argument-box__textarea').first().fill('Phân tích mục tiêu, nêu giả định và cân nhắc phương án. Tôi kiểm tra các trường hợp biên, giải thích kết quả và đánh đổi. 😀');
    await page.click('#submit-answer');
    await page.waitForURL(/\/review/);
    await page.locator('#review-content').waitFor({ timeout: 15000 });
    const before = evaluateRequests.length;
    await checkShellAndAlignment(page, 'review-overview-desktop');
    await page.screenshot({ path: path.join(out, 'review-overview-desktop.png'), fullPage: false, animations: 'disabled' });
    await page.click('#review-tab-detail');
    await page.locator('#tab-panel-detail').waitFor();
    check(evaluateRequests.length === before, 'tabs do not evaluate');
    await page.screenshot({ path: path.join(out, 'review-detail-desktop.png'), fullPage: false, animations: 'disabled' });
    check((await page.locator('#answer-source').textContent()).includes('😀'), 'saved text intact');
    await page.locator('#review-tab-detail').focus();
    await page.keyboard.press('ArrowLeft');
    check((await page.locator('#review-tab-overview').getAttribute('aria-selected')) === 'true', 'keyboard tabs');

    for (const route of ['review', 'setup', 'home']) {
      if (route === 'setup') await page.goto(`${preview}/setup`);
      if (route === 'home') await page.goto(`${preview}/`);
      for (const width of [1920, 1440, 1024, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 1050 });
        const dims = await checkShellAndAlignment(page, `${route}-${width}`);
        layouts.push({ route, width, scroll: dims.scrollWidth });
      }
      await page.setViewportSize({ width: 390, height: 1000 });
      await page.screenshot({ path: path.join(out, `${route}-mobile.png`), fullPage: false, animations: 'disabled' });
    }

    const recovery = await context.newPage();
    await recovery.route('**/api/learning-paths/catalog', (route) => route.abort());
    await recovery.goto(`${preview}/learning-path`);
    await recovery.locator('#learning-reload').waitFor();
    await recovery.unroute('**/api/learning-paths/catalog');
    await recovery.click('#learning-reload');
    await recovery.locator('#learning-content').waitFor();
    await recovery.close();

    check(!errors.length, `page errors ${errors.join('; ')}`);
    const result = {
      totals,
      layouts,
      checks: [
        'no global sidebar',
        'full-web ambient background',
        'header/main/footer aligned',
        'visible top nav on desktop & mobile',
        'all readings/practices',
        'self-report persistence',
        'budget shortfall/feasible',
        'form cancel',
        'network recovery',
        'Vietnamese font',
        'outline draft',
        'deferred evaluation',
        'per-question evaluation',
        'review keyboard tabs',
        'immutable answer text',
      ],
      pageErrors: errors,
    };
    fs.writeFileSync(path.join(out, 'verification.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
