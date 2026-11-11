class DemoPage {
  constructor() {
    this.labels = {Knowledge: 'Kiến thức', Analysis: 'Phân tích', Testing: 'Test', Implementation: 'Cài đặt'};
    this.sampleLabels = {correct: 'Đúng đầy đủ', partial: 'Đúng một phần', incorrect: 'Sai hoặc thiếu yêu cầu', equivalent: 'Cách trình bày tương đương', ambiguous: 'Chưa đủ căn cứ'};
    this.statusLabels = {met: 'Đạt', unmet: 'Chưa đạt', insufficientEvidence: 'Chưa đủ căn cứ'};
    this.storageKey = 'answerPocDrafts-v2';
    let saved = {};
    try { saved = JSON.parse(sessionStorage.getItem(this.storageKey) || '{}'); } catch {}
    this.state = new DemoState(saved);
    this.busy = false;
    this.liveConfigured = false;
    this.questions = [];
    this.bindEvents();
  }

  element(id) { return document.getElementById(id); }

  makeElement(tag, text, className) {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  }

  bindEvents() {
    this.element('question-select').addEventListener('change', () => this.selectQuestion(this.element('question-select').value));
    this.element('answer-text').addEventListener('input', () => {
      this.state.editAnswer(this.element('answer-text').value);
      this.saveDrafts();
      this.showCurrentReport();
      this.refreshControls();
    });
    this.element('load-example-button').addEventListener('click', () => this.loadExample());
    this.element('preview-button').addEventListener('click', () => this.submitAnswer(true));
    this.element('answer-form').addEventListener('submit', event => { event.preventDefault(); this.submitAnswer(false); });
    this.element('download-button').addEventListener('click', () => this.downloadReport());
  }

  saveDrafts() {
    const saved = Object.fromEntries(Object.entries(this.state.drafts).map(([id, draft]) => [id, {...draft, report: null}]));
    try { sessionStorage.setItem(this.storageKey, JSON.stringify(saved)); } catch { this.showMessage('Không thể lưu bản nháp trong trình duyệt. Hãy sao chép bài trước khi đóng trang.'); }
  }

  async request(url, body) {
    const options = body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) {
      const messages = {providerConfig: 'Chưa cấu hình AI. Bạn vẫn có thể tải bài mẫu và xem kết quả ghi sẵn.', providerQuota: 'Đã hết hạn mức AI. Bài được giữ lại; hãy thử lại sau hoặc xem bản ghi.', providerBilling: 'Tài khoản AI chưa có hạn mức khả dụng. Kiểm tra tài khoản hoặc xem bản ghi.', providerTimeout: 'AI phản hồi quá lâu. Bài được giữ lại, bạn có thể thử lại.', invalidEvidence: 'AI trả bằng chứng chưa hợp lệ. Chưa tạo điểm; bài của bạn vẫn được giữ.', versionMismatch: 'Câu hỏi hoặc rubric đã thay đổi. Tải lại trang để nhận phiên bản mới; bản nháp vẫn được giữ.', exampleChanged: 'Bản ghi chỉ áp dụng cho nguyên văn bài mẫu.', recordingMismatch: 'Bản ghi không khớp phiên bản câu hỏi. Hãy kiểm tra bộ dữ liệu.', answerConflict: 'Lần nộp này đã gắn với nội dung khác. Sửa bài để tạo phiên bản mới.', contentUnapproved: 'Nội dung chưa hoàn tất duyệt độc lập.', questionBankInvalid: 'Không đọc được bộ câu hỏi. Kiểm tra file dữ liệu.'};
      throw new Error(messages[result.code] || 'Không hoàn tất đánh giá. Nội dung bài vẫn được giữ; kiểm tra cấu hình hoặc thử lại.');
    }
    return result;
  }

  async start() {
    try {
      const [questions, runtime] = await Promise.all([this.request('/api/questions'), this.request('/api/status')]);
      this.questions = questions;
      this.liveConfigured = runtime.liveEvaluationConfigured;
      this.element('live-status').textContent = this.liveConfigured ? `Đã có cấu hình ${runtime.providerName}; kết nối và hạn mức sẽ được kiểm tra khi gửi bài.` : 'Chưa cấu hình AI. Bài mẫu và kết quả ghi sẵn vẫn dùng được, không cần key.';
      this.element('question-select').replaceChildren(...questions.map(question => {
        const option = this.makeElement('option', `${question.questionId.replace('demo.', '')} · ${question.title}`);
        option.value = question.questionId;
        return option;
      }));
      this.selectQuestion(questions[0].questionId);
    } catch (error) { this.showMessage(error.message, true); }
  }

  selectQuestion(questionId) {
    this.question = this.questions.find(item => item.questionId === questionId);
    const draft = this.state.selectQuestion(this.question);
    this.element('question-select').value = questionId;
    this.element('question-heading').textContent = this.question.title;
    this.element('question-prompt').textContent = this.question.prompt;
    this.element('question-code').textContent = this.question.context || '';
    this.element('question-code').hidden = !this.question.context;
    this.element('requirements-list').replaceChildren(...this.question.requirements.map(text => this.makeElement('li', text)));
    this.element('question-badge').textContent = this.question.reviewStatus === 'approved' ? 'Đã duyệt nội dung' : 'Dữ liệu demo · chờ duyệt độc lập';
    this.element('source-caption').textContent = `Dữ liệu nguồn: ${this.question.source.sourceCommit.slice(0, 12)} · Phiên bản câu hỏi ${this.question.version}`;
    this.element('example-select').replaceChildren(...this.question.examples.map(sample => {
      const option = this.makeElement('option', this.sampleLabels[sample.caseName]);
      option.value = sample.caseName;
      return option;
    }));
    this.element('answer-text').value = draft.text;
    this.renderRubrics();
    this.showCurrentReport();
    this.refreshControls();
  }

  renderRubrics() {
    this.element('rubric-content').replaceChildren(...this.question.dimensions.map(dimension => {
      const block = this.makeElement('details', undefined, 'rubric-detail');
      block.append(this.makeElement('summary', `${this.labels[dimension.name]} · ${dimension.applies ? 'Có chấm' : 'Không áp dụng'}`));
      if (!dimension.applies) {
        block.append(this.makeElement('p', 'Câu hỏi không yêu cầu phần này. Không tạo điểm và không tính là thiếu bài.'));
        return block;
      }
      const rubric = this.question.rubrics.find(item => item.competency === dimension.name);
      const checks = this.makeElement('ol');
      rubric.criteria.forEach(check => checks.append(this.makeElement('li', `${check.description}: ${check.acceptanceRule}`)));
      block.append(checks);
      const table = this.makeElement('table', undefined, 'score-table');
      const header = this.makeElement('tr');
      header.append(this.makeElement('th', 'Điểm'), this.makeElement('th', 'Điều kiện'));
      table.append(header);
      rubric.scoreLevels.forEach(level => {
        const row = this.makeElement('tr');
        row.append(this.makeElement('td', String(level.value)), this.makeElement('td', level.description));
        table.append(row);
      });
      block.append(table, this.makeElement('p', 'Nếu phần chưa rõ có thể làm đổi mức điểm, kết quả là chưa đủ căn cứ.'));
      return block;
    }));
  }

  refreshControls() {
    const draft = this.state.current();
    const ready = Boolean(this.question);
    this.element('question-select').disabled = this.busy || !ready;
    this.element('answer-text').disabled = this.busy || !ready;
    this.element('load-example-button').disabled = this.busy || !ready;
    this.element('example-select').disabled = this.busy || !ready;
    this.element('evaluate-button').disabled = this.busy || !this.liveConfigured || !draft?.text.trim();
    this.element('preview-button').disabled = this.busy || !draft?.sample || draft.text !== draft.sample.answerText;
    this.element('download-button').disabled = this.busy || !draft?.report;
    this.element('character-count').textContent = `${draft?.text.length || 0} / 40.000`;
    this.element('answer-form').setAttribute('aria-busy', String(this.busy));
  }

  showMessage(text, error = false) {
    this.element('result-status').textContent = text;
    this.element('result-status').dataset.kind = error ? 'error' : 'info';
  }

  showCurrentReport() {
    const report = this.state.current().report;
    this.element('report-content').hidden = !report;
    if (report) this.renderReport(report);
    else { this.element('report-content').replaceChildren(); this.showMessage('Chưa có kết quả cho nội dung hiện tại.'); }
  }

  async loadExample() {
    this.busy = true;
    this.refreshControls();
    try {
      const caseName = this.element('example-select').value;
      const sample = await this.request(`/api/examples/${encodeURIComponent(caseName)}?questionId=${encodeURIComponent(this.question.questionId)}`);
      this.state.loadSample(sample);
      this.element('answer-text').value = sample.answerText;
      this.saveDrafts();
      this.showCurrentReport();
      this.showMessage('Đã tải bài mẫu. Chọn xem kết quả ghi sẵn hoặc đánh giá bằng AI.');
    } catch (error) { this.showMessage(error.message, true); }
    finally { this.busy = false; this.refreshControls(); }
  }

  async submitAnswer(recorded) {
    if (this.busy) return;
    const draft = this.state.current();
    if (!draft.text.trim() || (recorded && !draft.sample)) return;
    const submittedText = draft.text;
    const body = {questionId: this.question.questionId, questionVersion: this.question.version, rubricVersions: Object.fromEntries(this.question.rubrics.map(item => [item.rubricId, item.version])), answerText: submittedText};
    if (recorded) body.caseName = draft.sample.caseName;
    else { body.answerId = draft.answerId; body.revision = draft.revision; }
    this.busy = true;
    this.refreshControls();
    this.showMessage(recorded ? 'Đang kiểm tra và chấm bản ghi…' : 'Đang đối chiếu bằng AI, kiểm tra bằng chứng và xếp mức…');
    try {
      const report = await this.request(recorded ? '/api/preview' : '/api/evaluate', body);
      if (!this.state.acceptReport(report, submittedText)) throw new Error('Kết quả không khớp với bài hiện tại.');
      this.renderReport(report);
      this.element('results-heading').focus();
    } catch (error) { this.showMessage(error.message, true); }
    finally { this.busy = false; this.refreshControls(); }
  }

  renderReport(report) {
    const container = this.element('report-content');
    container.replaceChildren();
    container.hidden = false;
    this.showMessage(report.providerName === 'recorded' ? 'Kết quả ghi sẵn · không phải lượt chấm AI trực tiếp.' : 'Đã hoàn tất đánh giá bằng AI.');
    this.question.dimensions.forEach(dimension => {
      const block = this.makeElement('section', undefined, 'rubric-result');
      const heading = this.makeElement('div', undefined, 'rubric-top');
      heading.append(this.makeElement('h3', this.labels[dimension.name]));
      if (!dimension.applies) {
        heading.append(this.makeElement('span', 'Không áp dụng', 'score ungraded'));
        block.append(heading, this.makeElement('p', 'Không yêu cầu ở câu này; không tạo điểm.'));
        container.append(block);
        return;
      }
      const rubric = report.inputs.rubrics.find(item => item.competency === dimension.name);
      const result = report.results.find(item => item.rubricId === rubric.rubricId);
      const scoreText = result.score === null ? 'Chưa đủ căn cứ' : `${result.score} / ${Math.max(...rubric.scoreLevels.map(level => level.value))}`;
      heading.append(this.makeElement('span', scoreText, `score${result.score === null ? ' ungraded' : ''}`));
      block.append(heading, this.makeElement('p', result.reason));
      result.criterionChecks.forEach(check => {
        const criterion = rubric.criteria.find(item => item.criterionId === check.criterionId);
        const details = this.makeElement('details', undefined, 'criterion');
        details.append(this.makeElement('summary', `${criterion.description} — ${this.statusLabels[check.status]}`));
        check.evidence.forEach(evidence => {
          const evidenceBlock = this.makeElement('div', undefined, 'evidence');
          if (evidence.quote) evidenceBlock.append(this.makeElement('blockquote', evidence.quote));
          evidenceBlock.append(this.makeElement('p', evidence.observation), this.makeElement('span', evidence.location, 'evidence-location'));
          details.append(evidenceBlock);
        });
        block.append(details);
      });
      const feedback = report.feedbackItems.find(item => item.resultId === result.resultId);
      const feedbackBlock = this.makeElement('details', undefined, 'feedback-block');
      feedbackBlock.append(this.makeElement('summary', 'Phản hồi và nội dung cần làm rõ'), this.makeElement('p', feedback.explanation));
      const issues = this.makeElement('ul');
      feedback.identifiedIssues.forEach(issue => issues.append(this.makeElement('li', issue)));
      feedbackBlock.append(issues);
      block.append(feedbackBlock);
      container.append(block);
    });
    container.append(this.makeElement('p', `${report.providerName} · ${report.modelName} · ${report.promptVersion}`, 'provider-line'));
  }

  downloadReport() {
    const report = this.state.current().report;
    if (!report) return;
    const query = new URLSearchParams({providerName: report.providerName, modelName: report.modelName, promptVersion: report.promptVersion});
    const link = document.createElement('a');
    link.href = `/api/reports/${report.inputHash}?${query}`;
    link.download = `${report.inputs.question.questionId}-${report.providerName}-${report.inputHash.slice(0, 12)}.json`;
    document.body.append(link);
    link.click();
    link.remove();
  }
}

new DemoPage().start();
