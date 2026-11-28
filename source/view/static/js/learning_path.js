(() => {
  "use strict";
  const api = window.InterviewApi;
  const $ = (id) => document.getElementById(id);
  const settings = $('learning-settings');
  const reader = $('lesson-dialog');
  const catalogActivity = window.InterviewActivity?.mount('learning-activity', $('learning-loading'));
  const planActivity = window.InterviewActivity?.mount('plan-activity');
  let planGeneration = 0;
  let catalog, lessons, resources, courses;
  let completed = new Set(), itemChecks = new Set(), activePhase = null, lastPlan = null, selectedLesson = null, snapshot = null;
  const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text != null) el.textContent = String(text);
    if (cls) el.className = cls;
    return el;
  };
  const key = () => `interviewus.java-lessons.${catalog.version}`;
  const itemChecksKey = () => `interviewus.java-item-checks.${catalog.version}`;
  const planKey = () => `interviewus.java-plan.${catalog.version}`;
  function readStorage(name, fallback) { try { return JSON.parse(localStorage.getItem(name)) ?? fallback; } catch (_) { return fallback; } }
  function writeStorage(name, value) { try { localStorage.setItem(name, JSON.stringify(value)); } catch (_) { $('plan-status').textContent = 'Trình duyệt chưa lưu được tiến độ; lựa chọn vẫn được giữ trong trang này.'; } }
  function sourceLink(resource) {
    const a = node('a', resource.title);
    const url = new URL(resource.url);
    if (url.protocol !== 'https:') throw new Error('Nguồn học liệu không hợp lệ.');
    a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
    return a;
  }
  const access = {free_reading:'Đọc miễn phí',free_public:'Miễn phí công khai',free_reading_cloud_may_cost:'Bài đọc miễn phí · cloud lab có thể mất phí',free_registration_announced_2024:'Thông báo miễn phí 2024 · cần đăng ký, chưa thử lab hiện tại',paid_or_limited_preview:'Trả phí / preview giới hạn',legacy_optional:'Tài liệu cũ · bổ trợ tùy chọn'};

  function formatDateVi(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
  }

  function syncSettingsUI() {
    const track = $('learning-track')?.value || 'backend';
    const mode = $('learning-mode')?.value || 'full_track';
    const hours = Math.max(1, Math.min(40, Number($('learning-hours')?.value || 8)));
    const weeks = Math.max(1, Math.min(52, Number($('learning-weeks')?.value || 12)));

    document.querySelectorAll('[data-track-chip]').forEach((btn) => {
      const selected = btn.dataset.trackChip === track;
      btn.classList.toggle('is-selected', selected);
      btn.setAttribute('aria-pressed', String(selected));
    });
    document.querySelectorAll('[data-mode-tab]').forEach((btn) => {
      const selected = btn.dataset.modeTab === mode;
      btn.classList.toggle('is-active', selected);
      btn.setAttribute('aria-pressed', String(selected));
    });
    document.querySelectorAll('[data-weeks]').forEach((btn) => {
      const selected = Number(btn.dataset.weeks) === weeks;
      btn.classList.toggle('is-selected', selected);
      btn.setAttribute('aria-pressed', String(selected));
    });
    document.querySelectorAll('[data-hours]').forEach((btn) => {
      const selected = Number(btn.dataset.hours) === hours;
      btn.classList.toggle('is-selected', selected);
      btn.setAttribute('aria-pressed', String(selected));
    });

    if ($('settings-weeks-summary')) $('settings-weeks-summary').textContent = `${weeks} tuần chuẩn bị`;
    if ($('settings-hours-pill')) $('settings-hours-pill').textContent = `${hours} giờ / tuần`;
    if ($('settings-total-hours')) $('settings-total-hours').textContent = `${hours * weeks} giờ`;

    const start = new Date();
    const end = new Date(start.getTime() + weeks * 7 * 86400000);
    if ($('settings-date-start')) $('settings-date-start').textContent = formatDateVi(start);
    if ($('settings-date-end')) $('settings-date-end').textContent = `${formatDateVi(end)} (ước tính)`;

    if (catalog && lessons && $('settings-preview')) {
      const selectedTargets = [...($('target-lessons')?.querySelectorAll('input:checked') || [])].map((x) => x.value);
      const ids = new Set();
      const collect = (id) => {
        if (ids.has(id) || !lessons.has(id)) return;
        ids.add(id);
        for (const dep of lessons.get(id).prerequisite_ids) collect(dep);
      };
      const roots = selectedTargets.length ? selectedTargets : (catalog.tracks[track] || []);
      for (const id of roots) collect(id);
      let unitCount = 0;
      let practiceCount = 0;
      for (const id of ids) {
        const l = lessons.get(id);
        unitCount += l.units.length;
        practiceCount += l.practices.length;
      }
      $('settings-preview').textContent = `${ids.size} lesson · ${unitCount} bài học nhỏ · ${practiceCount} bài thực hành`;
    }
  }

  function renderProfileBanner(profile) {
    const pill = $('baseline-status-pill');
    const copy = $('baseline-summary-copy');
    const ctaLabel = $('baseline-start-label');
    const profileHint = $('settings-profile-hint');
    if (!pill || !copy || !ctaLabel) return;

    const entries = profile && Array.isArray(profile.entries) ? profile.entries : [];
    if (!entries.length) {
      pill.textContent = 'Chưa làm kiểm tra đầu vào';
      copy.textContent = 'Thực hiện phiên phỏng vấn ảo 4 câu để đối chiếu rubric và ghi nhận điểm cần củng cố (chưa có đánh giá Java chuyên biệt).';
      ctaLabel.textContent = 'Kiểm tra đầu vào';
      if (profileHint) profileHint.textContent = 'Chưa có phiên đánh giá hoàn tất trên trình duyệt này.';
      return;
    }

    const met = entries.filter((e) => e.state === 'observed_strength').length;
    const needs = entries.filter((e) => e.state === 'needs_practice').length;
    const unresolved = entries.filter((e) => e.state === 'insufficient_evidence').length;
    pill.textContent = `Đã quan sát ${entries.length} kỹ năng · ${met} đạt`;
    copy.textContent = `Kết quả từ hồ sơ trình duyệt: ${met} kỹ năng đạt, ${needs} cần củng cố, ${unresolved} chưa đủ căn cứ. Có thể làm kiểm tra lại để cập nhật hồ sơ.`;
    ctaLabel.textContent = 'Kiểm tra lại';
    if (profileHint) {
      profileHint.textContent = needs > 0
        ? `Đang có ${needs} kỹ năng cần củng cố phù hợp để ưu tiên vào lộ trình.`
        : 'Chưa phát hiện điểm thiếu cần ưu tiên từ hồ sơ hiện tại.';
    }
  }

  function invalidate() {
    $('learning-confirm').checked = false;
    if (lastPlan) { $('plan-status').textContent = 'Lựa chọn đã đổi. Kế hoạch bên dưới thuộc lần xác nhận trước; hãy tạo lại để cập nhật.'; $('download-plan').hidden = true; }
  }
  function progress() {
    if (!$('self-progress') && !$('self-progress-ring') && !$('self-progress-count')) return;
    const ids = new Set();
    function include(id) { if(ids.has(id)||!lessons.has(id))return; ids.add(id); for(const dep of lessons.get(id).prerequisite_ids)include(dep); }
    for(const id of (lastPlan ? lastPlan.target_lesson_ids : catalog.tracks[$('learning-track').value]))include(id);
    const done = [...ids].filter(id => completed.has(id)).length;
    const pct = ids.size ? Math.round(done / ids.size * 100) : 0;
    if ($('self-progress')) $('self-progress').textContent = `${pct}%`;
    if ($('self-progress-ring')) $('self-progress-ring').style.setProperty('--progress', `${pct}%`);
    if ($('self-progress-count')) $('self-progress-count').textContent = `${done}/${ids.size} lesson đã tự đánh dấu`;
  }
  function renderChecks() {
    $('completed-lessons').replaceChildren(); $('target-lessons').replaceChildren();
    for (const lesson of catalog.lessons) {
      for (const host of ['completed-lessons','target-lessons']) {
        const label = node('label', null, 'learning-check');
        const input = document.createElement('input'); input.type = 'checkbox'; input.value = lesson.id;
        input.checked = host === 'completed-lessons' && completed.has(lesson.id);
        label.append(input, node('span', `${lesson.id} — ${lesson.title}`)); $(host).append(label);
      }
    }
  }
  const PHASE_ICONS = ['terminal', 'database', 'layers', 'cloud_sync', 'workspace_premium'];
  function renderPhases() {
    const phases = [...new Set(catalog.lessons.map(x => x.phase))];
    $('phase-list').replaceChildren();
    phases.forEach((phase,index) => {
      const group = catalog.lessons.filter(x => x.phase === phase);
      const done = group.filter(x=>completed.has(x.id)).length;
      const pct = group.length ? Math.round((done / group.length) * 100) : 0;
      const button = node('button', null, `phase-button${activePhase === phase ? ' is-active' : ''}${done === group.length ? ' is-complete' : ''}`);
      button.type = 'button'; button.setAttribute('aria-pressed', String(activePhase === phase));

      const iconWrap = node('span', null, 'phase-icon-badge');
      iconWrap.append(glyph(PHASE_ICONS[index] || 'folder_open'));

      const body = node('span', null, 'phase-body');
      const meter = node('span', null, 'phase-meter');
      const fill = node('span', null, 'phase-meter__fill');
      fill.style.width = `${pct}%`;
      meter.append(fill);
      body.append(
        node('strong', phase),
        node('small', `${done}/${group.length} bài · ${pct}%${index === 4 ? ' · tùy chọn' : ''}`),
        meter
      );

      const badge = node('span', null, 'phase-num-pill');
      if (done === group.length) {
        badge.append(glyph('check'));
      } else {
        badge.textContent = String(index + 1).padStart(2, '0');
      }

      button.append(iconWrap, body, badge);
      button.addEventListener('click', () => { activePhase=phase; $('lesson-search').value=''; renderPhases(); filterLessons(); });
      $('phase-list').append(button);
    });
  }
  function renderNodes() {
    const planItems = new Map((lastPlan?.ordered_lessons || []).map(x=>[x.lesson_id,x]));
    const current = lastPlan ? lessons.get(lastPlan.ordered_lessons.find(x=>!completed.has(x.lesson_id))?.lesson_id) : catalog.lessons.find(x=>!completed.has(x.id));
    const order = lastPlan ? [...lastPlan.ordered_lessons.map(x=>lessons.get(x.lesson_id)), ...catalog.lessons.filter(x=>!planItems.has(x.id))] : catalog.lessons;
    $('lesson-list').replaceChildren();
    for (const lesson of order) {
      const done=completed.has(lesson.id), item=planItems.get(lesson.id), needs=lesson.prerequisite_ids.filter(id=>!completed.has(id));
      const row=node('article',null,`learning-lesson${done?' is-complete':''}${current?.id===lesson.id?' is-current':''}${needs.length?' has-prerequisites':''}`);
      row.id=`lesson-${lesson.id}`; row.dataset.phase=lesson.phase;
      row.dataset.search=normalize(`${lesson.id} ${lesson.title} ${lesson.phase} ${lesson.skill_ids.join(' ')} ${lesson.units.map(x=>x.title).join(' ')}`);
      const bubble=node('button',null,'lesson-node');bubble.type='button';bubble.setAttribute('aria-label',`Mở ${lesson.id}: ${lesson.title}`);bubble.append(node('small',done?'ĐÃ HỌC':'LESSON'),node('strong',lesson.id.slice(2)));bubble.addEventListener('click',()=>openLesson(lesson.id));
      const card=node('div',null,'lesson-card');
      const meta=node('div',null,'lesson-card-meta');meta.append(node('span',lesson.phase,'stitch-eyebrow'));
      const state=done?'Đã tự đánh dấu':item?.status==='deferred'?'Chưa đủ quỹ thời gian':item?.status==='partially_scheduled'?'Xếp lịch một phần':current?.id===lesson.id?'Bắt đầu từ đây':lastPlan&&!item?'Ngoài kế hoạch':lesson.optional?'Tùy chọn':'Bài học';
      meta.append(node('span',state,`lesson-state${done?' is-done':''}`));
      const trigger=node('button',lesson.title,'lesson-trigger');trigger.type='button';trigger.addEventListener('click',()=>openLesson(lesson.id));
      card.append(meta,node('h3',null),node('p',`${lesson.units.length} bài học nhỏ · ${lesson.practices.length} bài thực hành có nguồn`,'lesson-description'));card.querySelector('h3').append(trigger);
      if(needs.length)card.append(node('p',`Nên học trước: ${needs.join(', ')}`,'lesson-prerequisite'));
      const footer=node('div',null,'lesson-card-footer');footer.append(node('small',`${lesson.estimated_minutes} phút ước tính`));
      const action=node('button',done?'Xem lại bài học →':'Mở bài học →',current?.id===lesson.id?'btn btn--primary':'lesson-open');action.type='button';action.addEventListener('click',()=>openLesson(lesson.id));footer.append(action);card.append(footer);
      row.append(bubble,card);$('lesson-list').append(row);
    }
    filterLessons(); progress();
  }
  function filterLessons() {
    const term=normalize($('lesson-search').value.trim());let count=0;
    document.querySelectorAll('.learning-lesson').forEach(row=>{row.hidden=term?!row.dataset.search.includes(term):row.dataset.phase!==activePhase;if(!row.hidden){row.dataset.side=String(count%2);count++;}});
    const group=catalog.lessons.filter(x=>x.phase===activePhase);
    $('active-phase-title').textContent=term?'Kết quả tìm kiếm':activePhase;
    $('phase-progress-label').textContent=term?`${count} bài học`:`${group.filter(x=>completed.has(x.id)).length}/${group.length} đã tự đánh dấu`;
    $('lesson-filter-status').textContent=`Hiển thị ${count}/${catalog.lessons.length} lesson`;
    let empty=$('no-lessons');if(!empty){empty=node('p','Không tìm thấy bài học. Hãy thử một từ khóa khác.','empty-state');empty.id='no-lessons';$('lesson-list').append(empty);}empty.hidden=count>0;
  }
  function glyph(name, cls = 'material-symbols-outlined') {
    const span = node('span', name, cls);
    span.setAttribute('aria-hidden', 'true');
    return span;
  }

  function createCheckButton(checkId, label) {
    const checked = itemChecks.has(checkId);
    const btn = node('button', null, `stitch-check-btn${checked ? ' is-checked' : ''}`);
    btn.type = 'button';
    btn.setAttribute('aria-pressed', String(checked));
    btn.setAttribute('aria-label', label);
    btn.title = checked ? 'Đã tự đánh dấu hoàn thành mục này' : 'Đánh dấu đã xem mục này';
    btn.append(glyph('check'));
    btn.addEventListener('click', () => {
      const next = !itemChecks.has(checkId);
      if (next) itemChecks.add(checkId);
      else itemChecks.delete(checkId);
      writeStorage(itemChecksKey(), [...itemChecks]);
      btn.classList.toggle('is-checked', next);
      btn.setAttribute('aria-pressed', String(next));
      btn.title = next ? 'Đã tự đánh dấu hoàn thành mục này' : 'Đánh dấu đã xem mục này';
    });
    return btn;
  }

  function makeExternalButton(url, titleText, cls = 'stitch-source-cta') {
    const a = sourceLink({ url, title: '' });
    a.className = cls;
    a.replaceChildren(node('span', titleText), glyph('open_in_new', 'material-symbols-outlined stitch-external-icon'));
    return a;
  }

  function buildSectionHeader(titleText, rightNode) {
    const head = node('div', null, 'lesson-section-head');
    const left = node('div', null, 'lesson-section-head__left');
    const accent = node('span', null, 'lesson-section-accent');
    accent.setAttribute('aria-hidden', 'true');
    left.append(accent, node('h3', titleText, 'reader-heading'));
    head.append(left);
    if (rightNode) head.append(rightNode);
    return head;
  }

  function openLesson(id) {
    const lesson = lessons.get(id);
    if (!lesson) return;
    selectedLesson = id;
    $('lesson-dialog-meta').textContent = `${id} · ${lesson.phase}`;
    $('lesson-dialog-title').textContent = lesson.title;

    const descHost = $('lesson-dialog-description');
    descHost.replaceChildren();
    const specs = [
      ['auto_stories', `${lesson.units.length} bài học nhỏ`],
      ['terminal', `${lesson.practices.length} bài thực hành`],
      ['schedule', `${lesson.estimated_minutes} phút ước tính`],
    ];
    specs.forEach(([iconName, text], idx) => {
      const span = node('span', null, 'lesson-spec-item');
      span.append(glyph(iconName, 'material-symbols-outlined lesson-spec-icon'), node('span', text));
      descHost.append(span);
      if (idx < specs.length - 1) descHost.append(node('span', '•', 'lesson-spec-sep'));
    });

    const prereqHost = $('lesson-dialog-prereq');
    if (prereqHost) {
      prereqHost.replaceChildren();
      prereqHost.hidden = lesson.prerequisite_ids.length === 0;
      if (lesson.prerequisite_ids.length) {
        const iconTile = node('span', null, 'lesson-prereq-icon');
        iconTile.setAttribute('aria-hidden', 'true');
        iconTile.append(glyph('school'));
        const content = node('div', null, 'lesson-prereq-links');
        content.append(node('span', 'Nên học trước:', 'lesson-prereq-label'));
        for (const dep of lesson.prerequisite_ids) {
          const depLesson = lessons.get(dep);
          const a = node('button', null, 'lesson-prereq-chip');
          a.type = 'button';
          a.append(
            node('span', `${dep} – ${depLesson ? depLesson.title : dep}`),
            glyph('arrow_outward', 'material-symbols-outlined lesson-prereq-arrow')
          );
          a.addEventListener('click', () => openLesson(dep));
          content.append(a);
        }
        prereqHost.append(iconTile, content);
      }
    }

    const host = $('lesson-body');
    host.replaceChildren();

    const readingSection = node('section', null, 'lesson-reader-section');
    readingSection.append(buildSectionHeader('Bài đọc & blog tại nguồn', node('span', 'TÀI LIỆU CHÍNH THỨC', 'lesson-section-kicker')));
    const list = node('ol', null, 'learning-units-list');
    lesson.units.forEach((unit, unitIndex) => {
      const li = node('li', null, 'unit-card');
      const idxBadge = node('span', String(unitIndex + 1).padStart(2, '0'), 'unit-index-badge');
      const unitMain = node('div', null, 'unit-card__main');
      unitMain.append(node('h4', unit.title, 'unit-card__title'));

      for (const rid of unit.reading_ids) {
        const r = resources.get(rid);
        const block = node('div', null, 'learning-reading');
        const info = node('div', null, 'learning-reading__info');
        const metaRow = node('div', null, 'learning-reading__meta');
        metaRow.append(
          node('strong', r.provider, 'reading-provider'),
          node('span', '•', 'reading-dot'),
          node('span', access[r.access] || r.access),
          node('span', '•', 'reading-dot'),
          node('span', r.language, 'reading-lang-pill'),
          node('span', '•', 'reading-dot'),
          node('span', r.edition, 'reading-edition')
        );
        info.append(metaRow);

        const dateParts = [];
        if (r.publication_date) dateParts.push(`Công bố: ${r.publication_date}`);
        if (r.updated_date) dateParts.push(`Cập nhật: ${r.updated_date}`);
        const verifiedLine = node('div', null, 'learning-reading__verified');
        verifiedLine.append(
          glyph('verified_user', 'material-symbols-outlined reading-verified-icon'),
          node('span', `Kiểm tra nguồn: ${r.verified_at}${dateParts.length ? ` · ${dateParts.join(' · ')}` : ''}`)
        );
        info.append(verifiedLine);

        if (r.alternative_url) {
          const alt = makeExternalButton(r.alternative_url, 'Nguồn dự phòng chính thức', 'reading-alt-link');
          info.append(alt);
        }

        const actions = node('div', null, 'learning-reading__actions');
        actions.append(
          makeExternalButton(r.url, r.title, 'stitch-source-cta'),
          createCheckButton(`${id}:u:${unit.id || unitIndex}:${r.id || rid}`, `Đánh dấu hoàn thành ${r.title}`)
        );
        block.append(info, actions);
        unitMain.append(block);
      }

      li.append(idxBadge, unitMain);
      list.append(li);
    });
    readingSection.append(list);
    host.append(readingSection);

    const practiceShell = node('section', null, 'practice-section-shell');
    practiceShell.append(buildSectionHeader('Bài thực hành áp dụng', node('span', `${lesson.practices.length} bài thực hành`, 'violet-pill practice-count-pill')));
    const practiceList = node('div', null, 'practice-card-stack');
    lesson.practices.forEach((practice, pIdx) => {
      const block = node('article', null, 'learning-practice');
      const cardHead = node('div', null, 'practice-card-head');
      const kindText = practice.kind === 'project_original'
        ? 'Bài vận dụng do nhóm biên soạn'
        : practice.kind === 'official_assignment'
          ? 'Bài tập gốc tại nguồn'
          : 'Ví dụ / lab trong nguồn';
      const kindIcon = practice.kind === 'project_original' ? 'psychology' : 'code_blocks';
      const kindPill = node('span', null, `practice-kind-pill${practice.kind === 'project_original' ? ' is-original' : ''}`);
      kindPill.append(glyph(kindIcon, 'material-symbols-outlined practice-kind-icon'), node('span', kindText));
      cardHead.append(
        kindPill,
        createCheckButton(`${id}:p:${pIdx}`, `Đánh dấu hoàn thành ${practice.title}`)
      );

      const copyWrap = node('div', null, 'practice-card-copy');
      copyWrap.append(node('h4', practice.title), node('p', practice.instructions));

      block.append(cardHead, copyWrap);

      if (practice.resource_ids && practice.resource_ids.length) {
        if (practice.kind === 'project_original') {
          const refGroup = node('div', null, 'practice-refs-group');
          refGroup.append(node('span', 'TÀI LIỆU THAM KHẢO LIÊN QUAN:', 'practice-refs-label'));
          const refRow = node('div', null, 'practice-refs-row');
          practice.resource_ids.forEach((rid) => {
            const r = resources.get(rid);
            const pill = sourceLink({ url: r.url, title: '' });
            pill.className = 'practice-ref-pill';
            pill.replaceChildren(
              glyph('menu_book', 'material-symbols-outlined practice-ref-icon'),
              node('span', r.title),
              glyph('open_in_new', 'material-symbols-outlined stitch-external-icon')
            );
            refRow.append(pill);
          });
          refGroup.append(refRow);
          block.append(refGroup);
        } else {
          const primaryRes = resources.get(practice.resource_ids[0]);
          const actionBox = node('div', null, 'practice-action-box');
          const boxLeft = node('div', null, 'practice-action-box__info');
          const iconTile = node('span', null, 'practice-action-icon');
          iconTile.setAttribute('aria-hidden', 'true');
          iconTile.append(glyph('terminal'));
          const boxText = node('div', null, 'practice-action-text');
          boxText.append(
            node('strong', primaryRes.title),
            node('small', `${primaryRes.provider} · ${access[primaryRes.access] || primaryRes.access}`)
          );
          boxLeft.append(iconTile, boxText);
          const primaryCta = makeExternalButton(primaryRes.url, 'Mở nguồn thực hành', 'btn btn--primary stitch-practice-cta');
          actionBox.append(boxLeft, primaryCta);
          block.append(actionBox);

          if (practice.resource_ids.length > 1) {
            const extraRow = node('div', null, 'practice-refs-row');
            practice.resource_ids.slice(1).forEach((rid) => {
              const r = resources.get(rid);
              const pill = makeExternalButton(r.url, r.title, 'practice-ref-pill');
              extraRow.append(pill);
            });
            block.append(extraRow);
          }
        }
      }

      const costLine = node('p', null, 'practice-cost-note');
      costLine.append(
        glyph(practice.kind === 'project_original' ? 'verified' : 'info', 'material-symbols-outlined practice-note-icon'),
        node('span', practice.cost_note)
      );
      block.append(costLine);
      practiceList.append(block);
    });
    practiceShell.append(practiceList);
    host.append(practiceShell);

    const courseBox = node('details', null, 'lesson-course-details');
    const courseSummary = node('summary', null, 'lesson-course-summary');
    const summaryLeft = node('span', null, 'lesson-course-summary__left');
    summaryLeft.append(glyph('arrow_right', 'material-symbols-outlined lesson-course-arrow'), node('span', 'Khóa học tham khảo cho lesson này'));
    courseSummary.append(summaryLeft, node('span', `${lesson.course_ids.length} khóa học`, 'lesson-course-count'));
    courseBox.append(courseSummary);

    const courseRows = node('div', null, 'lesson-course-list');
    for (const cid of lesson.course_ids) {
      const course = courses.get(cid);
      const row = node('div', null, 'lesson-course-item');
      const left = node('div', null, 'lesson-course-item__info');
      left.append(glyph('smart_display', 'material-symbols-outlined lesson-course-video-icon'));
      const textWrap = node('div');
      textWrap.append(
        node('strong', course.title),
        node('small', `${access[course.access] || course.access} · ${course.edition}`)
      );
      left.append(textWrap);
      row.append(left, makeExternalButton(course.url, 'Xem khóa học', 'stitch-source-cta stitch-source-cta--compact'));
      courseRows.append(row);
    }
    courseBox.append(courseRows);
    host.append(courseBox);

    if (lesson.completion_note) {
      const note = node('p', null, 'lesson-completion-note learning-note');
      note.append(glyph('verified', 'material-symbols-outlined practice-note-icon'), node('span', lesson.completion_note));
      host.append(note);
    }

    $('lesson-complete').checked = completed.has(id);
    const index = catalog.lessons.findIndex((x) => x.id === id);
    $('next-lesson').hidden = index === catalog.lessons.length - 1;
    if (!reader.open) reader.showModal();
    else reader.scrollTop = 0;
    history.replaceState(null, '', `#lesson-${id}`);
  }
  function renderPlan(plan) {
    lastPlan=plan;const host=$('plan-result');host.replaceChildren();
    const facts=node('div',null,'learning-facts');for(const [value,label] of [[plan.ordered_lessons.length,'lesson cần học'],[Math.round(plan.total_estimated_minutes/6)/10,'giờ ước tính'],[plan.estimated_weeks,'tuần theo quỹ giờ']]){const fact=node('div');fact.append(node('strong',value),node('small',label));facts.append(fact);}host.append(facts);
    if(!plan.feasible)host.append(node('p',`Còn thiếu ${plan.shortfall_minutes} phút. Các bài chưa đủ thời gian vẫn nằm trong lộ trình.`,'learning-warning'));
    const detail=node('details',null,'plan-details');detail.append(node('summary','Xem thứ tự học và phân bổ theo tuần'));
    const ordered=node('ol');for(const item of plan.ordered_lessons){const li=node('li'),a=node('button',`${item.lesson_id} — ${item.title}`,'plan-lesson-link');a.type='button';a.addEventListener('click',()=>openLesson(item.lesson_id));li.append(a,node('small',`${item.allocated_minutes}/${item.estimated_minutes} phút · ${item.status==='scheduled'?'Đã xếp đủ':item.status==='deferred'?'Đang hoãn':'Xếp một phần'}`));ordered.append(li);}detail.append(ordered);
    const weeks=node('div',null,'schedule-list');for(const slot of plan.schedule)weeks.append(node('span',`Tuần ${slot.week}: ${slot.lesson_id} · ${slot.minutes} phút`));detail.append(weeks);for(const warning of plan.warnings)detail.append(node('p',warning,'learning-note'));host.append(detail);
    $('plan-status').textContent=plan.feasible?'Đã tạo kế hoạch phù hợp quỹ thời gian đã xác nhận.':'Đã tạo kế hoạch một phần; hãy điều chỉnh quỹ thời gian hoặc mục tiêu.';$('download-plan').hidden=false;
    $('budget-chip').textContent=`${$('learning-hours').value} giờ/tuần · ${$('learning-weeks').value} tuần`;
    if($('plan-config-tag')){$('plan-config-tag').textContent='Đã thiết lập';$('plan-config-tag').className='plan-status-tag is-configured';}
    renderNodes();renderPhases();renderTodaySchedule();
  }
  const todayDialog = $('today-schedule-dialog');
  function renderTodaySchedule() {
    const summaryEl = $('today-schedule-summary');
    const tasksPanel = $('today-panel-tasks');
    const weekPanel = $('today-panel-week');
    if (!catalog || !lessons || !summaryEl || !tasksPanel || !weekPanel) return;

    const candidateLessons = lastPlan
      ? lastPlan.ordered_lessons.map((item) => ({ lesson: lessons.get(item.lesson_id), item })).filter((x) => x.lesson)
      : catalog.lessons.filter((l) => l.phase === activePhase).map((l) => ({ lesson: l, item: null }));

    const pending = candidateLessons.filter((x) => !completed.has(x.lesson.id));
    const todayItems = (pending.length ? pending : candidateLessons).slice(0, 3);
    const totalMinutes = todayItems.reduce((sum, x) => sum + (x.item?.allocated_minutes || x.lesson.estimated_minutes || 0), 0);
    const doneToday = todayItems.filter((x) => completed.has(x.lesson.id)).length;

    summaryEl.textContent = pending.length
      ? `${todayItems.length} việc cần làm hôm nay · ~${totalMinutes} phút (${doneToday}/${todayItems.length} đã xong)`
      : 'Bạn đã hoàn thành hết các bài trong chặng này!';

    tasksPanel.replaceChildren();
    const stats = node('div', null, 'today-stats-row');
    stats.append(
      node('span', `${todayItems.length} mục ưu tiên`, 'pill'),
      node('span', `~${totalMinutes} phút ước tính`, 'pill'),
      node('span', lastPlan ? 'Theo lộ trình cá nhân hóa' : `Theo chặng ${activePhase}`, 'violet-pill')
    );
    tasksPanel.append(stats);

    const list = node('div', null, 'today-task-list');
    for (const { lesson, item } of todayItems) {
      const done = completed.has(lesson.id);
      const row = node('div', null, `today-task-item${done ? ' is-done' : ''}`);
      const info = node('div', null, 'today-task-item__info');
      info.append(
        node('span', `${lesson.id} · ${lesson.phase}`, 'stitch-eyebrow'),
        node('strong', lesson.title),
        node('small', `${lesson.units.length} bài học nhỏ · ${item?.allocated_minutes || lesson.estimated_minutes} phút`)
      );
      const action = node('button', done ? 'Xem lại' : 'Học ngay →', done ? 'btn btn--secondary' : 'btn btn--primary');
      action.type = 'button';
      action.addEventListener('click', () => {
        todayDialog?.close();
        openLesson(lesson.id);
      });
      row.append(info, action);
      list.append(row);
    }
    tasksPanel.append(list);

    weekPanel.replaceChildren();
    if (lastPlan && Array.isArray(lastPlan.schedule) && lastPlan.schedule.length) {
      const weekList = node('div', null, 'today-week-list');
      for (const slot of lastPlan.schedule.slice(0, 8)) {
        const l = lessons.get(slot.lesson_id);
        const row = node('div', null, 'today-week-row');
        row.append(
          node('span', `Tuần ${slot.week}`, 'violet-pill'),
          node('strong', l ? `${slot.lesson_id} — ${l.title}` : slot.lesson_id),
          node('small', `${slot.minutes} phút`)
        );
        weekList.append(row);
      }
      weekPanel.append(weekList);
    } else {
      weekPanel.append(node('p', 'Chưa thiết lập lộ trình cá nhân hóa. Bấm "Thiết lập lộ trình" để phân bổ bài học theo tuần.', 'learning-note'));
    }
  }
  function switchTodayTab(tabName) {
    document.querySelectorAll('[data-today-tab]').forEach((btn) => {
      const active = btn.dataset.todayTab === tabName;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-selected', String(active));
    });
    if ($('today-panel-tasks')) $('today-panel-tasks').hidden = tabName !== 'tasks';
    if ($('today-panel-week')) $('today-panel-week').hidden = tabName !== 'week';
  }
  $('open-today-schedule')?.addEventListener('click', () => {
    renderTodaySchedule();
    switchTodayTab('tasks');
    todayDialog?.showModal();
  });
  $('close-today-dialog')?.addEventListener('click', () => todayDialog?.close());
  $('today-close-btn')?.addEventListener('click', () => todayDialog?.close());
  $('today-open-settings')?.addEventListener('click', () => {
    todayDialog?.close();
    openSettings();
  });
  document.querySelectorAll('[data-today-tab]').forEach((btn) => {
    btn.addEventListener('click', () => switchTodayTab(btn.dataset.todayTab));
  });
  function formState(){return {track:$('learning-track').value,mode:$('learning-mode').value,hours:$('learning-hours').value,weeks:$('learning-weeks').value,profile:$('learning-profile').checked,targets:[...$('target-lessons').querySelectorAll('input:checked')].map(x=>x.value)};}
  function restoreForm(state){if(!state)return;for(const field of ['track','mode','hours','weeks'])$('learning-'+field).value=state[field];$('learning-profile').checked=state.profile;for(const input of $('target-lessons').querySelectorAll('input'))input.checked=state.targets?.includes(input.value)||false;syncSettingsUI();}
  function openSettings(){snapshot=formState();renderChecks();restoreForm(snapshot);syncSettingsUI();settings.showModal();$('settings-error').hidden=true;}
  function cancelPlan(){planGeneration++;planActivity?.stop();window.InterviewActivity?.buttonBusy($('create-plan'),false);}
  function cancelSettings(){cancelPlan();restoreForm(snapshot);settings.close();}
  $('open-learning-settings').addEventListener('click',openSettings);
  $('close-learning-settings').addEventListener('click',cancelSettings);$('cancel-learning-settings').addEventListener('click',cancelSettings);
  settings.addEventListener('cancel',()=>{cancelPlan();restoreForm(snapshot);});
  function closeReader(){history.replaceState(null,'',location.pathname+location.search);reader.close();}
  $('close-lesson').addEventListener('click',closeReader);
  reader.addEventListener('cancel',event=>{event.preventDefault();closeReader();});
  reader.addEventListener('close',()=>{history.replaceState(null,'',location.pathname+location.search);const trigger=$(`lesson-${selectedLesson}`)?.querySelector('.lesson-trigger');if(trigger&&!trigger.closest('[hidden]'))trigger.focus();});
  $('next-lesson').addEventListener('click',()=>{const index=catalog.lessons.findIndex(x=>x.id===selectedLesson);if(index>=0&&index<catalog.lessons.length-1)openLesson(catalog.lessons[index+1].id);});
  $('lesson-complete').addEventListener('change',()=>{if($('lesson-complete').checked)completed.add(selectedLesson);else completed.delete(selectedLesson);writeStorage(key(),[...completed]);invalidate();renderNodes();renderPhases();renderTodaySchedule();});
  $('learning-form').addEventListener('change',event=>{if(event.target.id!=='learning-confirm')$('learning-confirm').checked=false;syncSettingsUI();});
  $('learning-form').addEventListener('input',()=>syncSettingsUI());
  document.querySelectorAll('[data-track-chip]').forEach(button=>button.addEventListener('click',()=>{$('learning-track').value=button.dataset.trackChip;$('learning-confirm').checked=false;syncSettingsUI();}));
  document.querySelectorAll('[data-mode-tab]').forEach(button=>button.addEventListener('click',()=>{$('learning-mode').value=button.dataset.modeTab;$('learning-confirm').checked=false;syncSettingsUI();}));
  document.querySelectorAll('[data-weeks]').forEach(button=>button.addEventListener('click',()=>{$('learning-weeks').value=button.dataset.weeks;$('learning-confirm').checked=false;syncSettingsUI();}));
  document.querySelectorAll('[data-hours]').forEach(button=>button.addEventListener('click',()=>{$('learning-hours').value=button.dataset.hours;$('learning-confirm').checked=false;syncSettingsUI();}));
  $('learning-form').addEventListener('submit',async event=>{
    event.preventDefault();if($('create-plan').disabled||!$('learning-form').reportValidity())return;
    const generation=++planGeneration;
    planActivity?.start({kind:'loading',title:'Đang sắp xếp kế hoạch học',description:'Giữ thứ tự tiên quyết và phân bổ các bài theo quỹ thời gian bạn vừa xác nhận.'});
    const request={track:$('learning-track').value,mode:$('learning-mode').value,hours_per_week:Number($('learning-hours').value),weeks:Number($('learning-weeks').value),completed_lesson_ids:[...$('completed-lessons').querySelectorAll('input:checked')].map(x=>x.value),target_lesson_ids:[...$('target-lessons').querySelectorAll('input:checked')].map(x=>x.value),use_profile:$('learning-profile').checked,confirm_goal:$('learning-confirm').checked};
    $('create-plan').disabled=true;$('create-plan').setAttribute('aria-busy','true');$('settings-error').hidden=true;
    try{const plan=await api.createLearningPlan(request);if(generation!==planGeneration)return;completed=new Set(request.completed_lesson_ids);writeStorage(key(),[...completed]);writeStorage(planKey(),{request,form:formState(),plan});renderPlan(plan);settings.close();}
    catch(error){if(generation!==planGeneration)return;$('settings-error').textContent=error.message||'Chưa tạo được kế hoạch. Các lựa chọn vẫn được giữ, hãy thử lại.';$('settings-error').hidden=false;}
    finally{if(generation===planGeneration){planActivity?.stop();$('create-plan').disabled=false;$('create-plan').removeAttribute('aria-busy');}}
  });
  $('lesson-search').addEventListener('input',()=>{if(catalog)filterLessons();});
  $('download-plan').addEventListener('click',()=>{if(!lastPlan)return;const url=URL.createObjectURL(new Blob([JSON.stringify(lastPlan,null,2)],{type:'application/json;charset=utf-8'}));const a=node('a');a.href=url;a.download='java-backend-learning-plan.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  async function load(){
    catalogActivity?.start({kind:'loading',title:'Đang mở không gian học tập',description:'Chuẩn bị các chặng, bài đọc và bài thực hành có nguồn cho bạn.'});
    $('learning-loading').hidden=false;$('learning-reload').hidden=true;$('learning-error').hidden=true;
    try{
      const [loadedCatalog, profile] = await Promise.all([
        api.getLearningCatalog(),
        typeof api.getProfile === 'function' ? api.getProfile().catch(() => null) : Promise.resolve(null),
      ]);
      catalog=loadedCatalog;lessons=new Map(catalog.lessons.map(x=>[x.id,x]));resources=new Map(catalog.resources.map(x=>[x.id,x]));courses=new Map(catalog.courses.map(x=>[x.id,x]));
      renderProfileBanner(profile);
      const saved=readStorage(key(),[]);completed=new Set(Array.isArray(saved)?saved.filter(id=>lessons.has(id)):[]);
      const savedChecks=readStorage(itemChecksKey(),[]);itemChecks=new Set(Array.isArray(savedChecks)?savedChecks.filter(x=>typeof x==='string'):[]);
      activePhase=catalog.lessons[0].phase;
      $('catalog-count').textContent=`${catalog.lessons.length} lessons · ${catalog.lessons.reduce((n,l)=>n+l.units.length,0)} bài học nhỏ · ${catalog.lessons.reduce((n,l)=>n+l.practices.length,0)} thực hành`;
      renderChecks();const stored=readStorage(planKey(),null);
      if(stored?.plan?.catalog_version===catalog.version&&Array.isArray(stored.plan.ordered_lessons)&&stored.plan.ordered_lessons.every(x=>lessons.has(x.lesson_id))){restoreForm(stored.form);renderPlan(stored.plan);if(JSON.stringify([...completed].sort())!==JSON.stringify([...stored.plan.completed_lesson_ids].sort()))invalidate();}else{renderPhases();renderNodes();renderTodaySchedule();syncSettingsUI();}
      $('course-list').replaceChildren();for(const course of catalog.courses){const block=node('details',null,'learning-course');const title=node('summary',course.title);block.append(title,node('span',access[course.access]||course.access,'learning-state'),node('p',`${course.provider} · ${course.edition}`),node('p',course.notes),sourceLink(course));$('course-list').append(block);}
      $('catalog-provenance').textContent=`Kiểm tra nguồn ${catalog.researched_at}. MIT 2024 dùng TypeScript cho tư duy chuyển giao. Chưa có đánh giá Java chuyên biệt; tiến độ tự khai không xác nhận thành thạo.`;
      $('learning-content').hidden=false;
      const initial=location.hash.match(/^#lesson-(JB\d\d)$/);if(initial)openLesson(initial[1]);
    }catch(error){$('learning-error').textContent=error.message||'Chưa tải được học liệu. Hãy thử lại.';$('learning-error').hidden=false;$('learning-reload').hidden=false;}
    finally{catalogActivity?.stop();$('learning-loading').hidden=true;}
  }
  $('learning-reload').addEventListener('click',load);load();
})();
