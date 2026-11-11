const assert = require('node:assert/strict');
const test = require('node:test');
const {DemoState} = require('../source/view/web/demoState.js');
const question = {questionId: 'demo.Q009', version: 1, rubrics: [{rubricId: 'r1', version: 1}]};
const reportFor = (id, text) => ({inputs: {question: {questionId: id}, answer: {originalText: text}}});

test('Editing invalidates the result and creates a new revision', () => {
  const state = new DemoState(); state.selectQuestion(question);
  state.editAnswer('first'); state.acceptReport(reportFor(question.questionId, 'first'), 'first');
  const id = state.current().answerId; const revision = state.current().revision;
  state.editAnswer('second');
  assert.equal(state.current().report, null); assert.equal(state.current().revision, revision + 1); assert.equal(state.current().answerId, id);
});
test('Retrying unchanged input preserves its identity and revision', () => {
  const state = new DemoState(); state.selectQuestion(question); state.editAnswer('same');
  const before = {...state.current()}; state.editAnswer('same'); assert.deepEqual(state.current(), before);
});
test('Each question keeps its own draft', () => {
  const state = new DemoState(); state.selectQuestion(question); state.editAnswer('draft one');
  state.selectQuestion({...question, questionId:'demo.Q002'}); state.editAnswer('draft two');
  state.selectQuestion(question); assert.equal(state.current().text, 'draft one');
});
test('Version change keeps text and invalidates sample and result', () => {
  const state = new DemoState(); state.selectQuestion(question); state.loadSample({answerText:'sample'});
  state.acceptReport(reportFor(question.questionId, 'sample'), 'sample');
  const oldId = state.current().answerId; state.selectQuestion({...question,version:2});
  assert.equal(state.current().text,'sample'); assert.equal(state.current().report,null); assert.equal(state.current().sample,null); assert.notEqual(state.current().answerId,oldId);
});
test('Editing a sample disables recorded preview', () => {
  const state = new DemoState(); state.selectQuestion(question); state.loadSample({answerText:'sample'}); state.editAnswer('edited');
  assert.equal(state.current().sample,null);
});
test('Results for stale text or another question are rejected', () => {
  const state = new DemoState(); state.selectQuestion(question); state.editAnswer('current');
  assert.equal(state.acceptReport(reportFor(question.questionId,'old'),'old'),false);
  assert.equal(state.acceptReport(reportFor('demo.Q002','current'),'current'),false);
  assert.equal(state.current().report,null);
});
test('Saved drafts can be restored after reloading', () => {
  const state = new DemoState(); state.selectQuestion(question); state.editAnswer('kept');
  const loaded = new DemoState(JSON.parse(JSON.stringify(state.drafts))); loaded.selectQuestion(question);
  assert.equal(loaded.current().text,'kept'); assert.equal(loaded.current().answerId,state.current().answerId);
});
