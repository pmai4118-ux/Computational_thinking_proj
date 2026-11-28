"""Port the supplied Stitch main markup; keep the original design files intact."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'design/stitch-homepage/homepage.html').read_text(encoding='utf-8')
literal = re.search(r'tailwind.config = (.*?);</script>', source, re.S)[1]
config = json.loads(re.sub(r'([{,]\s*)([A-Za-z_]\w*)(\s*:)', r'\1"\2"\3', literal))
colors = config['theme']['extend']['colors']
for name in config['theme']['extend']['fontFamily']:
    config['theme']['extend']['fontFamily'][name] = ['var(--font-sans)']
variables = []
for name, value in colors.items():
    rgb = ' '.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))
    variables.append(f'  --home-{name}: {rgb};')
    colors[name] = f'rgb(var(--home-{name}) / <alpha-value>)'
config.update(important='.homepage-shell', corePlugins={'preflight': False}, content=[
    './source/view/templates/welcome.html',
])
build = ROOT / 'scripts/homepage'
build.mkdir(exist_ok=True)
(build / 'tailwind.config.cjs').write_text('module.exports = ' + json.dumps(config, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
(build / 'input.css').write_text('@tailwind base;\n@tailwind components;\n@tailwind utilities;\n', encoding='utf-8')
(ROOT / 'source/view/static/css/homepage.colors.css').write_text('.homepage-shell {\n' + '\n'.join(variables) + '\n}\n', encoding='utf-8')

main = re.search(r'<main[^>]*>(.*?)</main>', source, re.S)[1]
main = re.sub(r'<script>.*?</script>', '', main, flags=re.S)
# Delete the entire statistics strip, rather than replace its fake numbers.
main = re.sub(r'<!-- 3 Trust Credentials.*?(?=</div>\s*<!-- Right Column)', '', main, flags=re.S)
replacements = {
    'Phiên bản 3.2 Luminous Glass': 'interviewUS · Luminous Glass',
    'Tối ưu cho màn hình Desktop 1440px': 'Phỏng vấn tự luận &amp; lộ trình Java Backend',
    'Giám khảo kỹ thuật AI trực tiếp': 'Trợ lý luyện phỏng vấn tự luận',
    'LIVE DEMO': 'MINH HỌA',
    'Chủ đề: Java Virtual Machine': 'Quy trình luyện phỏng vấn',
    'Vòng 1 • Technical': 'Tự luận kỹ thuật',
    '“Cơ chế Garbage Collection (GC) trong Java hoạt động như thế nào và làm sao để giảm Stop-the-world?”':
        'Đọc câu hỏi, trình bày cách giải thích của bạn và nhận phản hồi dựa trên bằng chứng trong bài làm.',
    'Độ phức tạp thuật toán: O(N log N)': 'Đối chiếu câu trả lời theo rubric',
    '>Tối ưu</span>': '>Có căn cứ</span>',
    '88%': 'AI',
    'Tỉ lệ đạt chuẩn kỹ thuật': 'Phản hồi theo tiêu chí',
    'Phản xạ nhanh, luận điểm rõ ràng': 'Bằng chứng · nhận xét · gợi ý ôn tập',
    'Us-Bot đang lắng nghe câu trả lời qua micro...': 'Minh họa cách Us-Bot hỗ trợ bạn luyện tập',
    '3 Trụ Cột Đột Phá Năng Lực Phỏng Vấn': 'Luyện tập có định hướng, tiến bộ từng bước',
    'Chuẩn hóa kiến thức và kỹ năng phỏng vấn thực chiến theo quy chuẩn doanh nghiệp.':
        'Kết nối câu trả lời, phản hồi có căn cứ và bài học phù hợp với mục tiêu của bạn.',
    'Luyện Câu Hỏi Kỹ Thuật': 'Câu Hỏi Tự Luận Kỹ Thuật',
    'Hơn 1,200+ câu hỏi tự luận &amp; chuyên sâu chia theo chủ đề.':
        'Luyện giải thích kiến thức, phân tích tình huống và trình bày lập luận trong phiên phỏng vấn.',
    'Lời giải chuẩn mực có phân tích Big-O': 'Tiêu chí đánh giá rõ ràng theo từng câu',
    'Đánh dấu câu đã hoàn thành và xem lại': 'Lưu bài làm và xem lại lịch sử phiên',
    'Khám phá ngân hàng câu hỏi': 'Khám phá cấu trúc phiên',
    'Trụ Cột 01': 'Câu hỏi &amp; lập luận',
    'Trụ Cột 02 • Giả Lập Trực Tiếp': 'Thực hành phỏng vấn',
    'Trụ Cột 03': 'Học theo mục tiêu',
    'Mô phỏng phỏng vấn thực tế 1-on-1 qua tự luận và giọng nói Voice AI.':
        'Trình bày câu trả lời bằng văn bản, xem bằng chứng được đối chiếu và nhận gợi ý cải thiện.',
    'Đánh giá tức thì': 'Phản hồi từng câu',
    'Phản hồi theo thời gian thực': 'Tổng kết cuối phiên',
    'Kiểm tra đầu vào xác định lỗ hổng kiến thức': 'Chọn mục tiêu và bài đã tự học',
    'Lịch nhắc học thông minh và theo dõi tiến độ': 'Bài đọc, thực hành có nguồn và tiến độ học',
    'Bắt đầu phiên phỏng vấn thử đầu tiên miễn phí ngay hôm nay.':
        'Bắt đầu phiên phỏng vấn thử đầu tiên ngay hôm nay.',
    'Không cần thẻ tín dụng. Trải nghiệm tức thì hệ thống đánh giá bằng Us-Bot AI thông minh.':
        'Chọn mục tiêu, xác nhận thiết lập và bắt đầu trình bày câu trả lời của bạn.',
    'Luyện phỏng vấn miễn phí': 'Bắt đầu phỏng vấn',
    'record_voice_over': 'forum',
    'animate-ping': '',
    'animate-pulse': '',
}
for old, new in replacements.items():
    assert old in main, old
    main = main.replace(old, new)
main = main.replace('Hệ thống ngân hàng câu hỏi kỹ thuật chuẩn cấu trúc, phỏng vấn thử nghiệm thực tế với',
    'Luyện trả lời tự luận kỹ thuật với')
paths = {'luyen-cau-hoi': '/interview', 'phong-van-ao': '/interview', 'lo-trinh': '/learning-path'}
for key, url in paths.items():
    main = main.replace(f'data-path="{key}" href="#"', f'href="{url}"')
# The primary hero action opens clarification; the discovery action opens the intro.
main = main.replace('href="/interview">\n<span class="material-symbols-outlined text-[22px]">play_circle',
    'href="/setup">\n<span class="material-symbols-outlined text-[22px]">play_circle', 1)
main = main.replace('onclick="setAppTheme(\'light\')"', 'type="button" data-home-theme="light" aria-pressed="true"')
main = main.replace('onclick="setAppTheme(\'dark\')"', 'type="button" data-home-theme="dark" aria-pressed="false"')
main = main.replace('<h1 class=', '<h1 id="welcome-heading" class=', 1)
main = main.replace('<div class="flex items-center justify-between">', '<div class="home-console-heading flex items-center justify-between">', 1)
# The shared header now owns theme controls; remove the entire floating utility bar.
main = re.sub(r'<!-- Top Floating.*?(?=<!-- HERO SECTION)', '', main, flags=re.S)
main = re.sub(r'<!--.*?-->', '', main, flags=re.S)
main = re.sub(r'(<span class="material-symbols-outlined [^"]*")', r'\1 aria-hidden="true"', main)
main = re.sub(r'\n\s*\n', '\n', main)
ambient = re.search(r'<body[^>]*>(.*?)<header', source, re.S)[1]
ambient = ambient.replace('<div class="pointer-events-none', '<div aria-hidden="true" class="pointer-events-none', 1)
footer = re.search(r'<footer.*?</footer>', source, re.S)[0]
for old, new in {
    'Nền tảng luyện phỏng vấn công nghệ chất lượng cao.': 'Luyện tự luận kỹ thuật &amp; học Java Backend.',
    'data-path="dieu-khoan" href="#"': 'href="/interview"',
    '>Điều khoản<': '>Phỏng vấn ảo<',
    'data-path="quyen-rieng-tu" href="#"': 'href="/learning-path"',
    '>Quyền riêng tư<': '>Lộ trình Java<',
    'href="https://discord.com" rel="noopener noreferrer" target="_blank"': 'href="/history"',
    '>Discord<': '>Lịch sử phiên<',
    'href="https://github.com" rel="noopener noreferrer" target="_blank"': 'href="/setup"',
    '>GitHub<': '>Bắt đầu luyện tập<',
}.items():
    footer = footer.replace(old, new)
template = '''{% extends "base.html" %}
{% set nav_active = "home" %}
{% block title %}Trang chủ — interviewUS{% endblock %}
{% block body_class %}homepage-shell{% endblock %}
{% block extra_head %}
  <link rel="stylesheet" href="/static/css/homepage.colors.css?v=20261127">
  <link rel="stylesheet" href="/static/css/homepage.utilities.css?v=20261127">
  <link rel="stylesheet" href="/static/css/homepage.css?v=20261127">
{% endblock %}
{% block content %}
''' + ambient + '\n<div class="homepage-content relative z-10" aria-labelledby="welcome-heading">\n' + main + '''
</div>
{% endblock %}
{% block site_footer %}
''' + footer + '''
{% endblock %}
'''
(ROOT / 'source/view/templates/welcome.html').write_text(template, encoding='utf-8')
