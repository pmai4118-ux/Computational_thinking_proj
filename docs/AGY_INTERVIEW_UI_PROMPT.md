# Prompt giao AGY build lại UI phỏng vấn

Copy phần trong khối bên dưới vào AGY. Prompt chỉ yêu cầu build UI phỏng vấn; lộ trình có đặc tả riêng.

```text
Bạn hãy trực tiếp triển khai lại UI phỏng vấn trong repo:
K:\HCMUS\HK4_2026-2027\TDTT\Computational_thinking_proj

Mục tiêu: giao diện phải bám sát HTML tôi đã thiết kế, không tự nghĩ một giao diện mới chỉ cùng màu tím. Giữ layout, typography, spacing, card, gradient/glass, icon, tab và thứ tự nội dung của mẫu; thay số và nội dung minh họa bằng dữ liệu thật.

Trước khi code, đọc:
1. K:\HCMUS\HK4_2026-2027\TDTT\AGENTS.md và PROJECT_SPEC.md hiện hành ở cùng thư mục (phạm vi phỏng vấn tự luận, mục 7 tách học liệu tự học).
2. docs/INTERVIEW_UI_STITCH_BUILD.md — đây là đặc tả mapping UI/API, trạng thái và nghiệm thu của công việc này.
3. design/stitch-java-backend/README.md và design-system/DESIGN.md.
4. Mở và đọc CẢ HTML lẫn PNG của bốn màn sau trong design/stitch-java-backend/:
   - interview-hub/interview-hub.html và interview-hub.png
   - interview-workspace/interview-workspace.html và interview-workspace.png
   - answer-review-overview/answer-review-overview.html và answer-review-overview.png
   - answer-review-detail/answer-review-detail.html và answer-review-detail.png
5. docs/api_contract.md, docs/data_contract.md, source/Control/schemas.py, source/view/pages.py và JS đang chạy.

Hãy kiểm tra git status/diff, giữ nguyên thay đổi chưa commit của tôi và bản thiết kế gốc. Tái dùng FastAPI/Jinja2/CSS/JavaScript hiện có; không đổi framework hoặc tạo một app demo rời.

Phần phải build:
- /setup: hub ba bước theo mẫu, hai mode card, các card cấu hình, CTA và lịch sử từ chủ cookie hiện tại. Phiên chính chỉ có 4 câu. Mode mặc định after_session; per_question chỉ bật nếu nối đúng lựa chọn qua adapter/API và có fallback form tương đương. Nhãn phản hồi cuối phiên/từng câu phải đúng, không hứa gợi ý thích ứng chưa có.
- /sessions/{id}: banner tiến độ và card xếp dọc như workspace mẫu, đề/ràng buộc/nguồn từ server, vùng nhập tự luận với khung luận điểm, nháp trong tab, bộ đếm tổng 20.000 ký tự, gửi/tiếp tục/kết thúc sớm. Nếu làm nhiều khung thì serialize rõ ràng thành một Answer.text, giữ tương thích draft cũ và gửi idempotent. Không làm mất bài khi lỗi.
- /sessions/{id}/review: hai tab theo hai HTML kết quả. Tab 1 có điểm tổng, danh sách tiêu chí, evidence và feedback. Tab 2 có toàn văn đã lưu, highlight bằng chứng tương tác và nhận xét theo đoạn. Đây là hai View của cùng answer revision, không phải hai kết quả riêng.
- Giữ link kết quả cũ, summary, exercises và navigation tới /learning-path. Summary vẫn điều phối đánh giá sau khi kết thúc phiên với giới hạn đồng thời hiện có.

Ràng buộc dữ liệu/hành vi:
- Dùng API thật và hook dataset/DOM hiện có; nếu đổi hook phải cập nhật JS/test đồng bộ. Không hard-code câu late binding, tên An Nguyễn, lịch sử, 88/100, 1/6 hoặc số đoạn trích vào giao diện live.
- Giữ after_session: lưu câu trả lời rồi next, không gọi evaluate khi phiên còn đang làm. Kết thúc/hoàn tất mới đánh giá từ summary. per_question dùng luồng hiện có nếu chọn rõ.
- Điểm/max và criterion checks lấy từ Service. insufficient_evidence giữ score=null, không thành 0; provider fail không thành người học sai. Không thêm công thức điểm, ngưỡng đậu/rớt hoặc đổi rubric.
- Highlight phải khớp quote và offset Unicode code point trên đúng answer_text/revision; xử lý ranges chồng nhau, observation không có quote và emoji. Bấm quote cập nhật đúng criterion/feedback. Copy trả nguyên văn bài server đã lưu. Không innerHTML từ answer/provider.
- Giữ ownership cookie, client_submission_id, retry/polling, immutable revision và xác nhận kết thúc sớm. Chuyển tab không gọi evaluate.
- Phần chưa có API (3 hints, topic Java/Spring theo roadmap, 5/10 câu, voice, tài khoản, notifications) không được vẽ thành chức năng giả. Theo ma trận trong docs/INTERVIEW_UI_STITCH_BUILD.md: giữ ngôn ngữ thị giác của vùng đó, dùng dữ liệu hỗ trợ thật, hoặc disabled/ẩn kèm giải thích phù hợp. Không tự mở rộng scope.
- Không import JD/CV, không voice/STT, không code editor/runner hay yêu cầu viết/sửa/review code mới. Trích đoạn code legacy nếu còn hiển thị chỉ read-only thuộc đề cũ; không tự sửa seed hoặc migrate nội dung/rubric trong task UI này.
- Bộ Java Backend roadmap là học liệu tự học; ngân hàng phỏng vấn hiện tại chưa phải bộ Java chuyên biệt. Không gắn nhãn sai để giống mock.
- Giữ HTML nguồn trong design/ nguyên vẹn. Port CSS vào assets hiện tại; không phụ thuộc Tailwind runtime CDN để triển khai production. Header/footer và các thành phần dùng lại có thể tách partial; tránh CSS làm hỏng roadmap.

Nghiệm thu:
1. Chạy app và kiểm tra trình duyệt qua setup -> trả lời/lưu/next -> kết thúc -> summary -> hai tab review. Kiểm tra cả mode nào đã bật, retry, resume, double-click, hết hạn/khác chủ, insufficient evidence, copy và nháp.
2. So screenshot với PNG ở cùng chiều rộng; giữ bố cục, font, kích thước card, tab, khoảng cách và sắc tím của từng mẫu. Vùng đen dài dưới footer ảnh hub là canvas xuất dư, không dựng vào app.
3. Kiểm tra 320/390/768/1024/1440px, không tràn ngang; keyboard/focus/ARIA tabs, accordion; không console error. Có ảnh desktop và mobile.
4. Chạy các test hồi quy hiện có phù hợp với file đã sửa; thêm test khi đổi adapter, draft/serialize hoặc logic highlight. Dùng fixture, không gọi AI trả phí trong test mặc định. Không báo test chưa chạy là đã đạt.
5. Báo các file thay đổi, kết quả test, ảnh đối chiếu và chức năng chưa hỗ trợ. Chỉ hoàn thành khi UI đã gắn dữ liệu thật; không dừng ở kế hoạch hay HTML tĩnh. Không tự commit/push/deploy.

Bắt đầu thực hiện, xử lý các lựa chọn kỹ thuật thường lệ theo đặc tả và code hiện tại. Chỉ hỏi lại nếu gặp mâu thuẫn không thể giải quyết từ các tài liệu và yêu cầu này.
```
