# PROMPT THIẾT KẾ UI/UX TOÀN DIỆN CHO GOOGLE STITCH (COPY-PASTE READY)
# DỰ ÁN: interviewUS — NỀN TẢNG LUYỆN PHỎNG VẤN KỸ THUẬT CHO SINH VIÊN CNTT & INTERN/FRESHER

> **Hướng dẫn sử dụng:** Sao chép toàn bộ nội dung trong khối code bên dưới và dán trực tiếp vào Google Stitch (hoặc các AI UI Design Tools như v0, Cursor, Lovable) để tạo giao diện chính xác 100% theo yêu cầu thiết kế.

```markdown
Design a comprehensive, modern, production-grade UI/UX for "interviewUS" — a specialized technical interview preparation platform designed for IT students and Intern/Fresher software engineers. All interface text must be 100% in Vietnamese.

==================================================
1. VISUAL IDENTITY & DESIGN TOKENS (2026 MODERN AESTHETIC)
==================================================
- Design Language: Modern Glassmorphism, refined, minimal, calm, and distraction-free educational environment.
- Background: Very pale lavender `#F5F3FA` (Light mode) and Deep Obsidian Slate `#0E0C15` (Dark mode). Soft purple and teal radial gradient blurs behind cards to accentuate the glass material.
- Color Palette:
  * Primary Brand & Main CTA: Electric Violet `#7C3AED` (Light) / `#8B5CF6` (Dark)
  * Secondary / Background tint: `#EDE9FE` (Light) / `#2E1E5B` (Dark)
  * AI Assistant & Interview Voice: Teal `#0D9488` (Light) / `#14B8A6` (Dark)
  * Accent Coral: `#F97360` (Used sparingly for streak milestones and hot tags)
  * Accent Amber: `#D89A16` (Medium difficulty badge and interview tips)
  * Success Emerald: `#16A34A` (Unit tests passed)
  * Danger / Error: `#DC2626` (Connection loss banner, test fail)
- Material Guidelines:
  * Glass surfaces: Moderate opacity `rgba(255, 255, 255, 0.70)`, `backdrop-filter: blur(16px)`, crisp ultra-thin bright border `1px solid rgba(255, 255, 255, 0.85)`, soft multi-layered shadow `0 10px 30px -4px rgba(124, 58, 237, 0.08)`.
  * Crucial Ergonomics Rule: Header, Hero, promotional cards, and dialog modals use Glassmorphism. However, high-focus reading zones (questions, dialogue stream, and code editor) MUST use high-contrast solid backgrounds (`#FFFFFF` in Light, `#161424` in Dark) to prevent eye fatigue during long sessions.
- Geometry:
  * Card Corner Radius: 20px - 28px (Pebble-soft aesthetic).
  * Buttons, inputs, dropdowns: 10px - 14px.
  * Badges & Chips: 9999px (Pill format).
- Typography (2026 Trend):
  * Primary UI Font: "Plus Jakarta Sans" (Clean geometric neo-grotesque with flawless Vietnamese diacritics support and generous x-height).
  * Monospace & Code Font: "JetBrains Mono" or "Geist Mono".
  * Strict constraint: Never use unreadable text below 12px.
- Brand Logo & Mascot:
  * Logo: Rounded speech bubble integrated with code brackets `< / >` in purple-teal gradient, exact brand name "interviewUS" (with "US" in vibrant purple).
  * 3D Mascot ("Us-Bot"): Pearl-white ceramic body, dark purple glass visor face, glowing teal expressive eyes, small programmer antenna/headphones. Friendly, tech-forward.

==================================================
2. GLOBAL NAVIGATION (STICKY GLASS NAVBAR)
==================================================
- Sticky fixed top bar with frosted glass effect.
- Left: Logo "interviewUS" + subtitle "LUYỆN PHỎNG VẤN KỸ THUẬT".
- Center Links:
  1. Trang chủ (Active pill indicator)
  2. Luyện câu hỏi
  3. Phỏng vấn ảo (with glowing teal live indicator)
  4. Lộ trình
  5. Tổng quan
- Right Utilities:
  * Notification bell with red badge counter.
  * Theme switcher: Sáng / Tối / Hệ thống (Light/Dark/System).
  * User profile: Rounded avatar "AN", name "An Nguyễn", level tag "Intern Fresher".

==================================================
3. SCREEN 1: TRANG CHỦ (HOMEPAGE - 1440PX)
==================================================
Structured in exact vertical order:
1. Hero Section (2-Column Balanced Height ~480px):
   - Left Column (55%):
     * Badge: "🌟 Nền tảng luyện phỏng vấn kỹ thuật thế hệ mới"
     * Title: "Luyện từng câu, vững từng bước." (Gradient text on second line)
     * Description: "Hệ thống ngân hàng câu hỏi kỹ thuật chuẩn cấu trúc, phỏng vấn thử nghiệm thực tế với Trợ lý AI và lộ trình cá nhân hóa cho sinh viên CNTT và Intern/Fresher."
     * Primary CTA: "Bắt đầu luyện tập" (Purple button with arrow)
     * Secondary CTA: "Khám phá phỏng vấn ảo" (Glass outlined button)
     * 3 Trust Badges: "800+ câu hỏi có phân tích sâu" • "Rubric 4 tiêu chí minh bạch" • "Đánh giá khách quan, không phán bừa".
   - Right Column (45%):
     * 3D Us-Bot mascot in front of a soft purple-teal radial glow.
     * Floating glass badges: Big-O snippet "Time: O(log n)", AI prompt bubble "Cơ chế Garbage Collection trong JVM?", and Fresher readiness badge "88% Đạt chuẩn".
2. Tiếp tục luyện tập (Conditional Resume Card):
   - Shows active in-progress session: "Mô phỏng Phỏng vấn: Fresher Java & Spring Boot - Vòng Kỹ thuật".
   - Metadata: "Đang ở câu 3/5 • Lần làm gần nhất: 2 giờ trước • 18 phút đã dùng".
   - Progress bar: 60% with purple-teal gradient.
   - Button: "Tiếp tục phiên".
3. Hạt giống XP (Gamified Habit-Building):
   - Educational principle: XP measures daily practice dedication, strictly separated from technical skill score.
   - 6 Stages displayed horizontally:
     1. Hạt giống (100 XP - Reached)
     2. Nảy mầm (CURRENT: 180 XP / 300 XP - 40% progress in stage, highlighted with purple border)
     3. Phát triển thân (Next milestone: 300 XP, needs 120 XP more)
     4. Phân cành (600 XP)
     5. Ra lá (1000 XP)
     6. Kết trái (1500 XP)
   - Clean progress bar with breakdown: "Đã tích lũy 80/200 XP chặng này • Cần thêm 120 XP để lên Phát triển thân".
4. “Hôm nay, bạn muốn luyện gì?” (3 Distinct Pillars):
   - Card 1: Luyện câu hỏi kỹ thuật (Icon books, tags OOP/DSA/SQL, CTA "Chọn câu hỏi").
   - Card 2 [Focal Highlight]: Luyện phỏng vấn ảo (Badge "★ Khuyên dùng cho Intern/Fresher", purple gradient border, tags 1-on-1 AI / Real-time / Báo cáo Rubric, CTA "Tạo phiên phỏng vấn").
   - Card 3: Lộ trình cá nhân hóa (Icon compass, tags Java Backend 30d / React Intern, CTA "Khám phá lộ trình").
5. Câu hỏi đề xuất (Horizontal Carousel with Prev/Next buttons):
   - Display question title, topics, difficulty badge (Dễ/Trung bình/Khó).
   - Provenance transparency: Clearly mark verified companies (e.g. "FPT Software - 2025 (Đã xác minh)") vs unverified items ("Nguồn cộng đồng đóng góp"). Never invent fake company names.
6. Lịch sử gần đây (Horizontal Scroll Cards):
   - Cards showing completed and in-progress sessions with score, date, and "Xem lại" / "Luyện lại" CTA.
7. Clean Compact Footer: Copyright © 2026 interviewUS, terms, privacy, Discord community, and GitHub links.

==================================================
4. SCREEN 2: THIẾT LẬP PHIÊN PHỎNG VẤN (SETUP VIEW - 1440PX)
==================================================
- Header Section: Title "Một buổi phỏng vấn. Nhiều điều để trưởng thành.", description, compact Us-Bot mascot.
- 2-Column Layout (65% Form Left - 35% Companion Info Right):
  * Left Form:
    1. Chế độ phỏng vấn (2 selectable cards):
       - "Có hướng dẫn" (Guided: AI gives hints and leading questions when stuck)
       - "Mô phỏng thực tế" (Realistic: strict countdown, no hints, full rubric report at end)
    2. Vị trí mục tiêu: Dropdown (Backend, Frontend, Fullstack, Mobile, QA).
    3. Cấp độ ứng tuyển: Segmented control [ Intern ] | [ Fresher ].
    4. Chủ đề kiểm tra (Multi-select chips): Java cơ bản, Cấu trúc dữ liệu & Giải thuật, SQL & Database, Spring Boot, Thiết kế hệ thống cơ bản, RESTful API.
    5. Ngôn ngữ code chính: Java, C++, Python, TypeScript.
    6. Thời lượng dự kiến: 15 phút (3 câu), 30 phút (5 câu), 45 phút (7 câu).
    7. Validation warning if zero topics selected.
    8. Primary CTA: "Tiếp tục thiết lập" (Opens Confirmation Modal).
  * Right Sidebar:
    - Card "Trợ lý phỏng vấn ảo": Intro to Us-Bot AI Mentor and non-judgmental evaluation rules.
    - Card "3 Mẹo phỏng vấn kỹ thuật ghi điểm": (1) Think out loud, (2) Clarify constraints & edge cases, (3) Explain algorithmic trade-offs.
- Post-Form: Horizontal carousel of past interview sessions.

==================================================
5. SCREEN 3: MODAL XÁC NHẬN MỤC TIÊU (GOAL CONFIRMATION DIALOG)
==================================================
- Centered glass modal with backdrop blur.
- Title: "Xác nhận mục tiêu phiên phỏng vấn".
- Summary table: Role (Fresher Backend Java), Mode (Mô phỏng thực tế - 30 phút, 5 câu), Language (Java 17 OpenJDK), Selected Topics chips.
- Checklist: [✓] Không gian yên tĩnh trong 30 phút • [✓] Bàn phím sẵn sàng viết code.
- Actions: "Quay lại chỉnh sửa" (Ghost) and "Bắt đầu ngay" (Purple primary CTA).

==================================================
6. SCREEN 4: PHÒNG PHỎNG VẤN CHUYÊN DỤNG (ACTIVE WORKSPACE - 1440PX)
==================================================
Dedicated distraction-free workspace.
- Top Workspace Bar (Height 60px):
  * Left: Mode badge "Mô phỏng thực tế" (Teal) + Session title "Phỏng vấn Fresher Java - Vòng Kỹ thuật".
  * Center: Segmented question indicator "Câu 2 / 5" (dots for passed, active, upcoming) + Countdown timer "⏳ 21:45" in monospace font.
  * Right: Auto-save status "✓ Đã lưu bản nháp (10s trước)" + Action buttons: "Lưu bản nháp" and "Lưu & Thoát" (safe exit).
- Main Question Header Box (Full width above columns or top of left):
  * Question Title: "Câu hỏi 2: Cơ chế hoạt động của HashMap trong Java & Cách xử lý va chạm (Collision Resolution)".
  * Difficulty: "Trung bình" (Amber) • Topic: "Java Core & Collections" • Evaluation: "Rubric 4 bậc".
  * Full prompt text detailing hashCode(), equals(), bucket indexing, Java 8 TREEIFY_THRESHOLD (linked list to Red-Black Tree), and writing simplified hash code.
- WORKSPACE 2-COLUMN SPLIT (EXACT RATIO: 60% LEFT / 40% RIGHT):
  * CỘT TRÁI (60%): Ô NHẬP CÂU TRẢ LỜI CỦA NGƯỜI DÙNG & CODE EDITOR
    - Tabs switcher: "Mã nguồn (Solution.java)" and "Giải thích lý thuyết (Văn bản)".
    - Monospace Code Editor (VS Code / IntelliJ aesthetic): line numbers (1..12), syntax-highlighted Java code with keywords in purple, methods in teal, numbers in orange.
    - Run & Test Bar: Shortcut hint "Ctrl + Enter để chạy thử", button "▶ Chạy thử test case", and button "Nộp & Sang câu tiếp theo".
    - Test Execution Console: Shows 3 unit tests passed (valid key, null key handling, collision simulation) with execution time.
  * CỘT PHẢI (40%): CHATBOT TRỢ LÝ ĐỂ NGƯỜI DÙNG HỎI LÀM RÕ CÂU HỎI VÀ CÁC RÀNG BUỘC
    - Header: Us-Bot AI Avatar, status "Đang trực tuyến • Sẵn sàng giải đáp ràng buộc".
    - Role constraint: Chatbot acts as an empathetic interviewer. It answers questions regarding constraints (e.g., input bounds, null safety, memory limits) and offers counter-questions/prompts WITHOUT leaking the full code solution.
    - Chat message bubble stream:
      * Us-Bot message: "Bạn có thể tự do giả định mảng bucket có kích thước mặc định 16 và hệ số tải 0.75 nhé."
      * Candidate query input: Input box "Hỏi người phỏng vấn để làm rõ yêu cầu, ràng buộc dữ liệu..." + Send button.
- Resilience: Error banner simulation for temporary connection drops ("Bài làm của bạn đã được lưu an toàn tại bộ nhớ máy. [Thử kết nối lại]"). Code is NEVER lost.

==================================================
7. SCREEN 5: MÀN HÌNH KẾT QUẢ & ĐÁNH GIÁ SAU PHỎNG VẤN (POST-INTERVIEW REPORT)
==================================================
Displayed immediately after completing the interview session:
- Top Header: Congratulatory banner with session name "Báo cáo Kết quả Phỏng vấn: Fresher Java Backend".
- Hero Score Card:
  * Overall Total Score on 100-point scale: Prominently displayed as `86 / 100` inside a radial gradient ring.
  * Overall verdict: "ĐẠT CHUẨN NĂNG LỰC FRESHER (Pass with Distinction)".
- BẢNG ĐIỂM 4 TIÊU CHÍ RUBRIC (4-PART RUBRIC BREAKDOWN):
  1. Độ chính xác thuật toán & Logic (Algorithm & Logic): `23 / 25`
  2. Tối ưu hóa thời gian & bộ nhớ (Time & Space Efficiency): `21 / 25`
  3. Xử lý trường hợp biên & Ràng buộc (Edge Cases & Constraints): `22 / 25`
  4. Quy chuẩn code sạch & Trình bày (Clean Code & Communication): `20 / 25`
- KHUNG LỰA CHỌN CÂU HỎI TIẾP THEO (NEXT QUESTION RECOMMENDATION):
  * Based on identified improvement areas, provides 3 recommended follow-up questions with difficulty tags and "Luyện câu này ngay" CTA (e.g. "Triển khai Cây Đỏ-Đen (Red-Black Tree)", "Tối ưu hóa câu truy vấn SQL với Composite Index").
- KHUNG Ở DƯỚI: ĐÁNH GIÁ CHI TIẾT PHẢN HỒI NGƯỜI DÙNG (DETAILED QUALITATIVE FEEDBACK):
  * Section 1: "Điểm mạnh nổi bật (Strengths)": Clear handling of null keys, structured explanation of hash buckets.
  * Section 2: "Điểm cần cải thiện (Areas for Improvement)": Should mention bitwise `(n - 1) & hash` optimization over `%` operator.
  * Section 3: "Khuyến nghị tài liệu & lộ trình tiếp theo": Direct links to Oracle Docs and recommended practice questions.
- Footer Actions: "Tải báo cáo PDF", "Xem lại từng câu trả lời", "Về Trang chủ".

==================================================
8. SCREEN 6: RESPONSIVE MOBILE EXPERIENCE (390PX VIEWPORT)
==================================================
- iPhone 16 / Pixel width (390px) optimized for one-hand touch ergonomics.
- Mobile Homepage:
  * Sticky compact header with logo and avatar.
  * Hero elements stacked vertically: Title -> Subtitle -> 2 CTAs -> Centered mini mascot.
  * In-progress resume card placed directly below hero.
  * XP Seed displayed as a compact horizontal bar with current XP & stage name.
  * 3 Pillars stacked vertically with "Luyện phỏng vấn ảo" prioritized at the top.
  * Horizontal carousels with smooth touch swipe (`scroll-snap-type: x mandatory`).
- Mobile Interview Room:
  * Compact top bar with question index and timer.
  * 3-Segmented Switcher tab: [ Đề bài ] | [ 60% Trả lời / Code ] | [ 40% Chatbot ràng buộc ].
  * Touch-friendly code shortcut keys for `{`, `}`, `(`, `)`, `;`, `"`.

==================================================
OUTPUT REQUIREMENT
==================================================
Render the UI with crisp contrast, Be Vietnam Pro / Plus Jakarta Sans typography, high quality Glassmorphism CSS, and accurate Vietnamese copy. Priority is given to the Desktop Homepage, Setup View, 60/40 Interview Room, and Post-Interview Rubric Result Screen.
```
