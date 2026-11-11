class DemoState {
  constructor(saved = {}) {
    this.drafts = saved && typeof saved === 'object' ? saved : {};
    this.questionId = null;
  }

  selectQuestion(question) {
    this.questionId = question.questionId;
    const versionKey = JSON.stringify([question.version, question.rubrics.map(item => [item.rubricId, item.version])]);
    let draft = this.drafts[this.questionId];
    if (!draft || typeof draft.text !== 'string') draft = {text: '', sample: null, report: null};
    if (draft.versionKey !== versionKey) {
      draft = {...draft, versionKey, sample: null, report: null, answerId: this.newAnswerId(), revision: 1};
    }
    this.drafts[this.questionId] = draft;
    return draft;
  }

  newAnswerId() {
    return `answer.${globalThis.crypto.randomUUID()}`;
  }

  current() {
    return this.drafts[this.questionId];
  }

  editAnswer(text) {
    const draft = this.current();
    if (draft.text !== text) {
      draft.text = text;
      draft.report = null;
      draft.revision += 1;
      if (draft.sample && draft.sample.answerText !== text) draft.sample = null;
    }
    return draft;
  }

  loadSample(sample) {
    this.editAnswer(sample.answerText);
    this.current().sample = sample;
  }

  acceptReport(report, submittedText) {
    const draft = this.current();
    if (draft.text !== submittedText || report.inputs.question.questionId !== this.questionId || report.inputs.answer.originalText !== submittedText) return false;
    draft.report = report;
    return true;
  }
}

if (typeof module !== 'undefined') module.exports = {DemoState};
