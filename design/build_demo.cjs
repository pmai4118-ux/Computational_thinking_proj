/* Merge the original Stitch documents, keeping each document's CSS isolated. */
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const sourceDir = path.join(__dirname, 'demo-web');
const cached = JSON.parse(fs.readFileSync(path.join(__dirname, 'stitch-assets.json'), 'utf8'));
const navigation = fs.readFileSync(path.join(__dirname, 'stitch-navigation.js'), 'utf8');
const titles = {
  'public-home': 'Trang chủ công khai',
  'member-home': 'Trang chủ thành viên',
  'question-library': 'Thư viện câu hỏi',
  'question-detail': 'Chi tiết câu hỏi',
  'guided-practice': 'Luyện tập có hướng dẫn',
  'interview-setup': 'Thiết lập phỏng vấn',
  'interview-workspace-structured': 'Phòng phỏng vấn theo luận điểm',
  'interview-workspace': 'Phòng phỏng vấn 70/30',
  'interview-report': 'Báo cáo phỏng vấn',
  'entry-assessment': 'Bài kiểm tra đầu vào',
  'incomplete-submission-dialog': 'Xác nhận nộp bài còn thiếu',
  'assessment-result': 'Kết quả kiểm tra',
  'learning-roadmap': 'Lộ trình cá nhân hóa',
  dashboard: 'Tổng quan',
  history: 'Lịch sử luyện tập',
  'auth-google': 'Đăng nhập 40/60',
  'auth-standard': 'Đăng nhập và đăng ký',
  'profile-goals': 'Hồ sơ và mục tiêu',
  'account-settings': 'Cài đặt tài khoản',
  'study-schedule': 'Lịch rảnh và nhắc học',
  'notification-panel': 'Bảng thông báo',
  'notification-center': 'Trung tâm thông báo'
};
const assets = [];
const byContent = new Map();
function slot(text) {
  if (!byContent.has(text)) {
    byContent.set(text, assets.length);
    assets.push(text);
  }
  return '@@STITCH_ASSET_' + byContent.get(text) + '@@';
}
function asset(url, kind) {
  const decoded = url.replaceAll('&amp;', '&');
  if (!cached[decoded]?.[kind]) throw Error('Missing ' + kind + ' for ' + decoded);
  return cached[decoded][kind];
}
const safeScript = code => code.replace(/<\/script/gi, '<\\/script');
const navigationSlot = slot('<script>' + safeScript(navigation) + '</script>');
const policy = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; font-src data:; base-uri \'none\'; form-action \'none\'">';
const screens = Object.entries(titles).map(([id, title]) => {
  const file = path.join(sourceDir, id, 'code.html');
  let html = fs.readFileSync(file, 'utf8');
  html = html.replace(/<html\b/i, '<html data-stitch-screen="' + id + '"');
  html = html.replace(/<head\b[^>]*>/i, head => head + policy);
  html = html.replace(/<script\b[^>]*\bsrc="(https:\/\/cdn\.tailwindcss\.com[^"]*)"[^>]*>\s*<\/script>/gi,
    (_, url) => slot('<script>' + safeScript(asset(url, 'script')) + '</script>'));
  html = html.replace(/<link\b[^>]*\bhref="(https:\/\/fonts\.googleapis\.com\/css2[^"]*)"[^>]*>/gi,
    (_, url) => slot('<style>' + asset(url, 'css') + '</style>'));
  html = html.replace(/<link\b[^>]*\bhref="https:\/\/fonts\.(?:googleapis|gstatic)\.com"[^>]*>/gi, '');
  html = html.replace(/https:\/\/lh3\.googleusercontent\.com\/[^"'<> )\s\\]+/g, url => slot(asset(url, 'image')));
  if (id === 'guided-practice') {
    // Stitch references two hint controls absent from this export. Skip their listeners
    // so the original voice toggle can still initialize in the merged document.
    html = html.replace('toggleBtn.addEventListener(', 'toggleBtn?.addEventListener(')
      .replace('collapseBtn.addEventListener(', 'collapseBtn?.addEventListener(');
  }
  html = html.replace(/<\/body>/i, navigationSlot + '</body>');
  return { id, title, html };
});
const folders = fs.readdirSync(sourceDir).filter(folder => fs.existsSync(path.join(sourceDir, folder, 'code.html')));
if (folders.length !== screens.length || folders.some(folder => !Object.hasOwn(titles, folder))) {
  throw Error('Screen list does not match the Stitch exports');
}
const packed = JSON.stringify({ screens, assets }).replace(/</g, '\\u003c');
const shell = fs.readFileSync(path.join(__dirname, 'stitch-shell.txt'), 'utf8');
const output = shell.replace('@@STITCH_PAYLOAD@@', () => packed);
fs.writeFileSync(path.join(root, 'demo.html'), output);
console.log(JSON.stringify({ file: 'demo.html', screens: screens.length, cachedAssets: assets.length, bytes: Buffer.byteLength(output) }));

