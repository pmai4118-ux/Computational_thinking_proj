/* Navigation for the links and buttons already drawn in the Stitch exports. */
(() => {
  const screen = document.documentElement.dataset.stitchScreen;
  const shared = {
    'trang-chu': 'member-home',
    'luyen-cau-hoi': 'question-library',
    'thu-vien-tu-luan': 'question-library',
    'phong-van-ao': 'interview-setup',
    'luyen-phong-van-ao': 'interview-setup',
    'luyen-phong-van-us-bot': 'interview-setup',
    'lo-trinh': 'learning-roadmap',
    'tong-quan': 'dashboard',
    'cai-dat-tai-khoan': 'account-settings',
    'dang-nhap': 'auth-google',
    'dang-ky': 'auth-standard'
  };
  const byScreen = {
    'question-library': [
      [/^luyện câu này/, 'question-detail'],
      [/^bắt đầu/, 'question-detail'],
      [/tiêu chuẩn chấm điểm/, 'interview-report']
    ],
    'question-detail': [[/quay lại thư viện|^thư viện câu hỏi/, 'question-library'], [/bắt đầu làm bài tự luận/, 'guided-practice']],
    'guided-practice': [[/quay lại thư viện/, 'question-library'], [/^nộp bài/, 'interview-report']],
    'interview-setup': [
      [/^bắt đầu thiết lập|^tiếp tục phiên/, 'interview-workspace-structured'],
      [/^chỉnh sửa nâng cao/, 'profile-goals'],
      [/^xem tất cả kết quả/, 'history'],
      [/^xem lại bản phân tích/, 'interview-report']
    ],
    'interview-workspace': [[/^nộp câu trả lời/, 'interview-report'], [/xem chi tiết rubric/, 'interview-report']],
    'interview-workspace-structured': [[/^nộp câu trả lời/, 'interview-report'], [/^câu trước$/, 'interview-workspace']],
    'interview-report': [[/^luyện lại phiên/, 'interview-setup'], [/^luyện ngay/, 'question-library']],
    'entry-assessment': [[/^nộp bài kiểm tra/, 'incomplete-submission-dialog'], [/^xem lại$/, 'assessment-result']],
    'incomplete-submission-dialog': [[/^tôi hiểu.*nộp/, 'assessment-result'], [/^quay lại|^tiếp tục viết|^làm câu này/, 'entry-assessment']],
    'assessment-result': [[/^bài kiểm tra đầu vào$/, 'entry-assessment'], [/^kích hoạt lộ trình|^đến lộ trình|^bắt đầu bài 1|^tùy chỉnh lộ trình/, 'learning-roadmap']],
    'learning-roadmap': [
      [/^kiểm tra lại kiến thức nền/, 'entry-assessment'],
      [/^xem chi tiết đánh giá/, 'assessment-result'],
      [/^xem lại bài tự luận|^xem rubric/, 'interview-report'],
      [/^luyện bài tự luận/, 'guided-practice']
    ],
    dashboard: [
      [/^tiếp tục phiên/, 'interview-workspace-structured'],
      [/^xem tất cả bài nộp/, 'history'],
      [/^luyện ngay|^viết lại câu/, 'guided-practice'],
      [/^xem bài|^xem chi tiết|^xem bằng chứng/, 'interview-report']
    ],
    history: [
      [/^tiếp tục phiên/, 'interview-workspace-structured'],
      [/^xem phân tích năng lực/, 'assessment-result'],
      [/^xem lại bài nộp|^xem báo cáo|^xem bài làm/, 'interview-report'],
      [/^luyện lại/, 'question-library']
    ],
    'auth-google': [[/trải nghiệm.*ẩn danh/, 'question-library'], [/^tiếp tục bằng tài khoản gmail|^đăng nhập với email trường/, 'member-home']],
    'auth-standard': [[/trải nghiệm.*ẩn danh/, 'question-library'], [/^quay về trang chủ/, 'public-home'], [/^google$|^github$|^đăng nhập tài khoản trường/, 'member-home']],
    'profile-goals': [[/lịch rảnh.*a03/, 'study-schedule'], [/lưu thay đổi.*lộ trình/, 'learning-roadmap']],
    'account-settings': [[/lịch rảnh/, 'study-schedule'], [/^mục tiêu.*chuyên ngành/, 'profile-goals']],
    'study-schedule': [[/hồ sơ.*mục tiêu/, 'profile-goals']],
    'notification-panel': [[/tất cả thông báo/, 'notification-center'], [/^vào phòng/, 'interview-workspace-structured'], [/^tiếp tục học|^luyện ngay/, 'guided-practice']],
    'notification-center': [[/chỉnh sửa lịch rảnh/, 'study-schedule'], [/^vào phòng/, 'interview-workspace-structured'], [/^xem báo cáo/, 'interview-report'], [/^vào luyện ngay/, 'guided-practice'], [/khám phá câu hỏi/, 'question-library']]
  };

  function navigate(target) {
    window.parent.postMessage({ type: 'stitch-demo:navigate', target }, '*');
  }

  function labelOf(element) {
    const copy = element.cloneNode(true);
    for (const icon of copy.querySelectorAll('.material-symbols-outlined, .material-icons, svg')) icon.remove();
    return copy.textContent.trim().replace(/\s+/g, ' ').toLocaleLowerCase('vi');
  }

  document.addEventListener('click', event => {
    const element = event.target.closest('a, button');
    if (!element || element.disabled) return;
    const route = element.dataset.path;
    const label = labelOf(element);
    const icon = element.querySelector('.material-symbols-outlined')?.textContent.trim();
    const local = (byScreen[screen] || []).find(([pattern]) => pattern.test(label))?.[1];
    const target = local || (route === 'trang-chu' && screen === 'public-home' ? 'public-home' : shared[route])
      || (icon === 'notifications' ? 'notification-panel' : null);
    if (target) {
      event.preventDefault();
      navigate(target);
    } else if (element.tagName === 'A' && !/^#.+/.test(element.getAttribute('href') || '')) {
      event.preventDefault();
    }
  }, true);

  document.addEventListener('submit', event => {
    event.preventDefault();
    if (screen === 'auth-google' || screen === 'auth-standard') navigate('member-home');
  }, true);
})();
