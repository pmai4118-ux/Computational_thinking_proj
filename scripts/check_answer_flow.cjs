// Full browser flow on an isolated fixture server; real-provider smoke is separate.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const base = process.env.ANSWER_PREVIEW_URL || 'http://127.0.0.1:8017';
const out = path.resolve('../outputs/answer-flow');
(async () => {
  fs.mkdirSync(out,{recursive:true});
  const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
  const checks=[], errors=[];
  try {
    for (const mode of ['after_each','after_session']) {
      const context = await browser.newContext({viewport:{width:mode==='after_each'?1440:390,height:1000},reducedMotion:'reduce'});
      const page = await context.newPage();
      page.on('pageerror',e=>errors.push(e.message));
      page.on('dialog',dialog=>dialog.accept());
      let saves=0, evaluations=0;
      page.on('request',r=>{
        if(r.method()==='POST' && /\/api\/sessions\/[^/]+\/answers$/.test(r.url())) saves++;
        if(r.method()==='POST' && r.url().endsWith('/evaluate')) evaluations++;
      });
      await page.goto(base+'/setup');
      assert((await page.locator('.badge--demo').textContent()).includes('Dữ liệu minh họa'));
      if(mode==='after_each') await page.click('#mode-card-guided');
      else await page.getByRole('button',{name:'Giao diện tối',exact:true}).click();
      await page.click('#start-session-btn');
      await page.waitForURL(/\/sessions\/[^/]+$/);
      const sessionUrl=page.url(), sid=new URL(sessionUrl).pathname.split('/').at(-1);
      const submitted=[];
      for(let index=0;index<4;index++) {
        await page.locator('[data-workspace]').waitFor();
        if(index===0) {
          await page.click('#submit-answer');
          await page.getByText('Vui lòng nhập câu trả lời trước khi gửi.',{exact:true}).waitFor();
          assert.equal(saves,0,'Empty input must not reach submission endpoint');
        }
        const body=`Bài kiểm thử ${mode}, câu ${index+1}: tiếng Việt có dấu 😀\nTôi phân tích giả định, so sánh phương án và kiểm tra trường hợp biên.\n<script>window.__injected = true</script>`;
        if(index%2===0) {
          await page.locator('.argument-box__textarea').first().fill(body);
        } else {
          await page.click('#mode-plain-btn');
          await page.locator('#answer-text').fill(body);
        }
        const canonical=await page.locator('#answer-text').inputValue();
        if(index===0) {
          await page.reload();
          await page.locator('.argument-box__textarea').first().waitFor();
          assert.equal(await page.locator('#answer-text').inputValue(),canonical,'Draft must survive reload intact');
        }
        let gateRelease;
        if(index===1) {
          const gate=new Promise(resolve=>{gateRelease=resolve});
          await page.route('**/api/sessions/*/answers',async route=>{
            if(route.request().method()==='POST') await gate;
            await route.continue();
          });
        }
        const savedResponse=page.waitForResponse(r=>r.request().method()==='POST' && /\/api\/sessions\/[^/]+\/answers$/.test(r.url()));
        await page.click('#submit-answer');
        if(index===1) {
          await page.waitForFunction(()=>document.querySelector('#submit-answer').disabled);
          await page.locator('#submit-answer').evaluate(button=>button.click());
          gateRelease();
        }
        const saved=await savedResponse;
        assert.equal(saved.status(),201);
        const payload=await saved.json();
        assert.equal(payload.answer.text,canonical,'Server must preserve submitted text');
        submitted.push({id:payload.answer.answer_id,text:canonical});
        await page.waitForURL(/\/review/);
        await page.locator('#next-question').waitFor({state:'visible'});
        assert.equal(await page.evaluate(()=>window.__injected),undefined,'Answer is data, never executable HTML');
        if(mode==='after_session') assert.equal(evaluations,0,'Deferred mode must not evaluate before session end');
        if(mode==='after_each') {
          await page.locator('#review-content').waitFor({state:'visible'});
          const result=await (await context.request.get(`${base}/api/sessions/${sid}/answers/${payload.answer.answer_id}/evaluations/${payload.answer.revision}`)).json();
          assert.equal(result.result.answer_text,canonical);
        }
        if(index===3) {
          await page.evaluate(()=>window.scrollTo(0,0));
          await page.screenshot({path:path.join(out,`${mode}-last-answer.png`),fullPage:true});
        }
        await page.click('#next-question');
        await page.waitForURL(index===3?/\/summary$/:sessionUrl);
        if(index===1) await page.unrouteAll();
      }
      await page.waitForFunction(()=>document.querySelector('#coverage-count')?.textContent.includes('4 / 4'));
      const summary=await (await context.request.get(`${base}/api/sessions/${sid}/summary`)).json();
      assert.equal(summary.state,'completed');
      assert.equal(summary.completed_question_count,4);
      assert.equal(saves,4,'Exactly one save per question, including duplicate click');
      assert.equal(evaluations,4,'Exactly one evaluation per saved answer');
      const beforeReload=evaluations;
      await page.reload();
      await page.waitForFunction(()=>document.querySelector('#coverage-count')?.textContent.includes('4 / 4'));
      assert.equal(evaluations,beforeReload,'Reloading summary must reuse saved results');
      await page.screenshot({path:path.join(out,`${mode}-summary.png`),fullPage:true});
      await page.goto(base+'/history');
      assert.equal(await page.locator(`a[href="/sessions/${sid}/summary"]`).count()>0,true,'Completed session appears in history');
      const stranger=await browser.newContext();
      const forbidden=await stranger.request.get(`${base}/api/sessions/${sid}/summary`);
      assert.equal(forbidden.status(),403,'Another browser cannot read this session');
      await stranger.close();
      checks.push({mode,questions:4,saves,evaluations,draftRestored:true,unicodePreserved:true,duplicateClickSafe:true,summaryReloadSafe:true,privateHistory:true});
      await context.close();
    }
    assert.deepEqual(errors,[]);
    const result={passed:true,checks,pageErrors:errors};
    fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
