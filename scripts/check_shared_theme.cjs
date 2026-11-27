// Use an isolated fixture preview. Verifies shared shell and a real answer flow.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const base = process.env.THEME_PREVIEW_URL || 'http://127.0.0.1:8016';
const out = path.resolve('../outputs/shared-theme');
(async () => {
  fs.mkdirSync(out, {recursive:true});
  const browser = await chromium.launch({headless:true, executablePath:process.env.CHROME_PATH});
  const context = await browser.newContext({viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
  const page = await context.newPage(), errors = [], checks = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    await page.goto(base);
    assert((await page.locator('.badge--demo').textContent()).includes('Dữ liệu minh họa'), 'Fixture preview required');
    await page.getByRole('button',{name:'Giao diện tối',exact:true}).click();
    let reference;
    for (const route of ['/', '/interview', '/setup', '/history', '/learning-path']) {
      await page.goto(base+route, {waitUntil:'networkidle'});
      if (route === '/learning-path') await page.locator('.lesson-card').first().waitFor();
      await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.locator('html').getAttribute('data-theme'),'dark', `Preference retained on ${route}`);
      assert.equal(await page.locator('[data-theme-mode="dark"]').getAttribute('aria-pressed'),'true');
      const shell = await page.evaluate(() => {
        const s = selector => getComputedStyle(document.querySelector(selector));
        const header = document.querySelector('.site-header').getBoundingClientRect();
        return {height:header.height, background:s('.site-header').backgroundColor,
          radius:s('.site-nav').borderRadius, font:s('.site-brand__text').fontFamily,
          heading:s('h1').fontFamily, nav:s('.site-nav__link').fontFamily};
      });
      assert(shell.heading.includes('Be Vietnam Pro'), `Heading font on ${route}`);
      if (!reference) reference=shell;
      assert.deepEqual(shell,reference,`Identical header/font on ${route}`);
      for (const width of [320,390,768,1024,1440]) {
        await page.setViewportSize({width,height:1000});
        await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
        const metrics = await page.evaluate(() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,
          clipped:[...document.querySelectorAll('.site-header a, .site-header button')].filter(el=>{
            const r=el.getBoundingClientRect();return r.x < -1 || r.right>innerWidth+1;
          }).map(el=>el.textContent.trim())}));
        assert(metrics.scroll<=width+1, `${route}: ${JSON.stringify(metrics)}`);
        assert.deepEqual(metrics.clipped, [], `${route}: clipped header`);
        if(width===390 && ['/', '/setup'].includes(route)) await page.screenshot({path:path.join(out, (route==='/'?'home':'setup')+'-dark-mobile.png'),fullPage:true});
      }
      await page.screenshot({path:path.join(out,(route==='/'?'home':route.slice(1))+'-dark-desktop.png'),fullPage:true});
      checks.push(route+' dark, shared header/font, 320–1440px');
    }
    await page.click('#open-learning-settings');
    await page.locator('#learning-settings').waitFor({state:'visible'});
    await page.screenshot({path:path.join(out,'learning-settings-dark.png'),fullPage:true});
    await page.keyboard.press('Escape');
    await page.goto(base+'/setup');
    await page.click('#mode-card-guided');
    await page.click('#start-session-btn');
    await page.waitForURL(/\/sessions\/[^/]+$/);
    const sessionUrl=page.url();
    await page.locator('.argument-box__textarea').first().fill('Tôi xác định giả định, so sánh lựa chọn và giải thích cách xác minh kết quả.');
    await page.screenshot({path:path.join(out,'workspace-dark.png'),fullPage:true});
    await page.click('#submit-answer');
    await page.waitForURL(/\/review/);
    await page.locator('#review-content').waitFor({state:'visible'});
    await page.screenshot({path:path.join(out,'review-dark.png'),fullPage:true});
    await page.click('#next-question');
    await page.waitForURL(sessionUrl);
    await page.click('#end-session');
    await page.click('#confirm-end-session');
    await page.waitForURL(/\/summary/);
    await page.locator('#coverage-count').waitFor({state:'visible'});
    await page.screenshot({path:path.join(out,'summary-dark.png'),fullPage:true});
    checks.push('Answer, review and summary keep dark theme and existing workflow');
    await page.getByRole('button',{name:'Giao diện sáng',exact:true}).click();
    await page.goto(base+'/');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    await page.screenshot({path:path.join(out,'home-light-desktop.png'),fullPage:true});
    // Keyboard and optional storage: controls remain usable without localStorage.
    const blocked = await browser.newContext();
    await blocked.addInitScript(() => { Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage disabled')}}); });
    const fallback = await blocked.newPage();
    await fallback.goto(base);
    await fallback.getByRole('button',{name:'Giao diện tối',exact:true}).focus();
    await fallback.keyboard.press('Enter');
    assert.equal(await fallback.locator('html').getAttribute('data-theme'),'dark');
    await blocked.close();
    assert.deepEqual(errors,[]);
    const result={passed:true,checks,errors};
    fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e => {console.error(e);process.exitCode=1});
