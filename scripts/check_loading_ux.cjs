// Browser acceptance test: use an isolated fixture preview, never a live AI provider.
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base=process.env.STITCH_PREVIEW_URL || 'http://127.0.0.1:8011';
const assert=(v,m)=>{if(!v)throw new Error(m)};
const gate=()=>{let release;const promise=new Promise(r=>release=r);return {promise,release}};
(async()=>{
 const out=path.resolve(process.env.LOADING_OUTPUT_DIR || '../outputs/loading-ux');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {})});
 const releases=[];const checks=[];const errors=[];
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1050}});const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
  await p.goto(base+'/setup');assert((await p.locator('.badge--demo').first().textContent()).includes('Dữ liệu minh họa'),'fixture only');
  await p.click('#mode-card-guided');await p.click('#start-session-btn');await p.waitForURL(/\/sessions\/[^/]+$/);
  const save=gate(),score=gate();releases.push(save.release,score.release);
  await p.route('**/api/sessions/*/answers',async r=>{if(r.request().method()==='POST'){await save.promise;await r.continue()}else await r.continue()});
  await p.route('**/api/sessions/*/answers/*/evaluate',async r=>{await score.promise;await r.continue()});
  await p.locator('.argument-box__textarea').first().fill('Tôi phân tích giả định, so sánh phương án và xác minh trường hợp biên. 😀');await p.click('#submit-answer');
  await p.locator('#workspace-activity').waitFor();assert(await p.locator('#workspace-activity').getAttribute('data-state')==='saving','saving state');assert(await p.locator('.argument-box__textarea').first().isDisabled(),'freeze input while save is pending');assert(await p.locator('#submit-answer').getAttribute('aria-busy')==='true','busy submit');
  await p.locator('#workspace-activity').scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,'saving-desktop.png'),animations:'disabled'});
  save.release();await p.waitForFunction(()=>document.querySelector('#workspace-activity').dataset.state==='assessment');assert(await p.locator('#workspace-activity progress').getAttribute('value')===null,'no made-up percent');
  await p.locator('#workspace-activity').scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,'ai-assessment-desktop.png'),animations:'disabled'});await p.setViewportSize({width:390,height:950});await p.locator('#workspace-activity').scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,'ai-assessment-mobile.png'),animations:'disabled'});
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'mobile assessment fits');score.release();await p.waitForURL(/\/review/);await p.locator('#review-content').waitFor();assert(await p.locator('#review-activity').isHidden(),'loader clears on result');checks.push('saving/AI/result states','pending input frozen','indeterminate progress','desktop/mobile');
  await p.unrouteAll();await p.setViewportSize({width:1440,height:1050});
  // A restored processing result is polled with GET; it must not trigger another AI call.
  const reviewUrl=p.url();let reads=0,posts=0;
  const evaluationPath=await p.locator('[data-answer-review]').evaluate(e=>`/api/sessions/${e.dataset.sessionId}/answers/${e.dataset.answerId}/evaluations/${e.dataset.answerRevision}`);
  const real=(await (await context.request.get(base+evaluationPath)).json());
  await p.route('**'+evaluationPath,async r=>{reads++;if(reads===1){const pending=structuredClone(real);pending.result.status='processing';pending.result.total_score=null;pending.result.criterion_checks=[];await r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(pending)})}else await r.continue()});
  p.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/evaluate'))posts++});
  await p.reload();await p.locator('#review-activity').waitFor();await p.screenshot({path:path.join(out,'review-processing.png'),animations:'disabled'});await p.locator('#review-content').waitFor({timeout:12000});assert(reads>=2&&posts===0,'GET polling without resubmission');checks.push('restored processing auto-refreshes with GET');await p.unrouteAll();
  // Provider errors stop the effect and leave a recoverable saved answer.
  await p.goto(base+'/setup');await p.click('#mode-card-guided');await p.click('#start-session-btn');await p.waitForURL(/\/sessions\/[^/]+$/);
  await p.route('**/api/sessions/*/answers/*/evaluate',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'Provider thử nghiệm chưa phản hồi',error_code:'PROVIDER_TIMEOUT',retryable:true})}));
  await p.locator('.argument-box__textarea').first().fill('Bài được lưu trước khi kiểm tra lỗi dịch vụ.');await p.click('#submit-answer');await p.locator('#retry-evaluation').waitFor();assert(await p.locator('#workspace-activity').isHidden(),'error stops animation');assert(await p.locator('#answer-text').inputValue()==='Phân tích vấn đề:\nBài được lưu trước khi kiểm tra lỗi dịch vụ.'||(await p.locator('#answer-text').inputValue()).includes('Bài được lưu trước'),'answer preserved');await p.unrouteAll();await p.click('#retry-evaluation');await p.waitForURL(/\/review/);await p.locator('#review-content').waitFor();checks.push('provider failure stops/retry preserves answer');
  // A batch reports only actual completed answers, independently of elapsed time.
  await p.goto(base+'/setup');await p.click('#start-session-btn');await p.waitForURL(/\/sessions\/[^/]+$/);const sid=p.url().split('/').at(-1);
  for(let i=0;i<2;i++){await p.locator('.argument-box__textarea').first().fill('Phân tích dữ kiện, đưa ra giả định, giải thích lựa chọn và cách xác minh.');await p.click('#submit-answer');await p.waitForURL(/\/review/);await p.locator('#next-question').waitFor();await p.click('#next-question');await p.waitForURL(new RegExp('/sessions/'+sid+'$'));}
  const batches=[];let evalCalls=0;
  await p.route('**/api/sessions/*/answers/*/evaluate',async r=>{const waiting=gate();batches.push(waiting);releases.push(waiting.release);evalCalls++;await waiting.promise;await r.continue()});
  await p.click('#end-session');await p.click('#confirm-end-session');await p.waitForURL(/\/summary/);await p.locator('#summary-activity').waitFor();assert(await p.locator('#summary-activity .activity-count').textContent()==='0/2 câu đã có kết quả','true 0/2');await p.waitForFunction(()=>document.querySelector('#summary-activity progress').max===2);await p.screenshot({path:path.join(out,'summary-processing.png'),animations:'disabled'});
  const batchDeadline=Date.now()+10000;while(batches.length<2){if(Date.now()>batchDeadline)throw Error("batch not started");await new Promise(r=>setTimeout(r,20));}batches[0].release();await p.waitForFunction(()=>document.querySelector('#summary-activity .activity-count').textContent==='1/2 câu đã có kết quả');await p.screenshot({path:path.join(out,'summary-one-complete.png'),animations:'disabled'});batches[1].release();await p.waitForFunction(()=>document.querySelector('#coverage-count').textContent.includes('Có kết quả 2 /'));assert(await p.locator('#summary-activity').isHidden(),'batch complete stops');assert(evalCalls===2,'only one POST per answer');checks.push('batch 0/2 -> 1/2 -> complete');await p.unrouteAll();
  const payload=await (await context.request.get(`${base}/api/sessions/${sid}/exercises`)).json();assert(payload.recommendations.every(x=>x.eligible_alternate_question_available===false),'availability retired');await p.goto(`${base}/sessions/${sid}/exercises`);await p.locator('#exercise-content').waitFor();assert(await p.getByRole('button',{name:/Luyện.*câu hỏi khác/}).count()===0,'no alternate UI');
  const retired=await context.request.post(`${base}/api/sessions/${sid}/answers/legacy/practice`,{data:{answer_revision:1,criterion_id:'old',exercise_id:'old'}});assert(retired.status()===410,'retired endpoint');checks.push('alternate UI/API removed');
  // Slow plan request canceled by the learner cannot overwrite their existing plan.
  await p.goto(base+'/learning-path');await p.locator('#learning-content').waitFor();const planGate=gate();releases.push(planGate.release);await p.route('**/api/learning-paths/plan',async r=>{await planGate.promise;await r.continue()});await p.click('#open-learning-settings');await p.check('#learning-confirm');await p.click('#create-plan');await p.locator('#plan-activity').waitFor();await p.click('#cancel-learning-settings');planGate.release();await p.waitForResponse(r=>r.url().endsWith('/api/learning-paths/plan'));assert(await p.locator('#plan-result').textContent()==='','canceled plan ignored');checks.push('cancel pending plan');await p.unrouteAll();
  await p.emulateMedia({reducedMotion:'reduce'});await p.evaluate(()=>{const activity=window.InterviewActivity.mount('learning-activity');activity.start({kind:'assessment',title:'Kiểm tra giảm chuyển động'});});await p.locator('#learning-activity').waitFor();assert(await p.locator('#learning-activity .activity-orbit').first().evaluate(e=>getComputedStyle(e).animationName)==='none','reduced motion');checks.push('reduced motion');
  assert(!errors.length,'page errors '+errors.join(';'));const result={checks,pageErrors:errors,retiredStatus:retired.status(),preview:base};fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
 }finally{for(const release of releases)release();await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
