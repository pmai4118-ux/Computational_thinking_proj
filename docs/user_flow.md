# P02 — User flow sáu khu vực

Cập nhật 10/11/2026. Phạm vi lần này **chỉ P02 và P06** theo yêu cầu mới nhất. Không mở rộng backlog, sửa P03/P04, triển khai backend hoặc commit. Đây là thiết kế để review; chưa có phê duyệt nghiệp vụ của cả nhóm.

## Mở sơ đồ P02

[p02-user-flow.html](../p02-user-flow.html) mở trực tiếp trên trình duyệt. Chọn một trong sáu khu vực, rồi bấm vào từng khối để xem thao tác và hướng đi.

## Hành trình từng khu vực

1. **Câu hỏi luyện tập** — Thư viện → Chi tiết → Xác nhận mục tiêu → Trả lời → Kết quả.
   [Sơ đồ SVG](user_flow_diagrams/questions.svg)

2. **Phiên phỏng vấn** — Chọn cấu hình → Xác nhận → Trả lời và lưu → Câu tiếp → Tổng kết.
   [Sơ đồ SVG](user_flow_diagrams/interview.svg)

3. **Lộ trình cá nhân hóa** — Mở lộ trình → Kiểm tra dữ liệu nền → Chọn mục → Học và kiểm tra → Cập nhật.
   [Sơ đồ SVG](user_flow_diagrams/roadmap.svg)

4. **Tổng quan** — Mở tổng quan → Đọc trạng thái dữ liệu → Chọn việc cần làm → Quay lại cập nhật.
   [Sơ đồ SVG](user_flow_diagrams/overview.svg)

5. **Đăng nhập** — Chọn Google / email / khách → Xác thực hoặc xác minh → Trở đúng trang đích.
   [Sơ đồ SVG](user_flow_diagrams/login.svg)

6. **Bài kiểm tra đầu vào** — Xác nhận mục tiêu → Làm bài → Rà soát → Lưu và đánh giá → Kết quả nền.
   [Sơ đồ SVG](user_flow_diagrams/assessment.svg)

## Luồng nối trang

- Đăng nhập/khách → Tổng quan hoặc thư viện. Google/email/register/reset chỉ mô phỏng chuyển trạng thái, không xác thực thật.
- Thư viện → chi tiết → xác nhận mục tiêu → làm một câu → bài đã nộp/kết quả mẫu → luyện lại, Tổng quan hoặc Lộ trình.
- Phiên phỏng vấn → chọn mode → xác nhận → bốn nhóm câu → lưu từng bài → tổng kết → mở lại từng bài. Guided xem mẫu từng câu, Simulation cuối phiên.
- Bài đầu vào → mục tiêu → ba phần (trắc nghiệm/tự luận/tình huống) → rà câu thiếu → xác nhận full/partial → kết quả mẫu → Lộ trình.
- Lộ trình → xem trước/kích hoạt mẫu → mục học → câu liên quan → kết quả → Tổng quan. Nội dung kế hoạch chưa được cá nhân hóa bằng thuật toán.
- Tổng quan → tiếp tục phiên/đầu vào, xem bài gốc hoặc luyện lại; ngày/tháng và điểm danh chỉ đổi trạng thái demo.

## Những quy tắc UX phải thấy được

Gửi chat, Dùng bản phiên âm và Nộp bài là ba nút độc lập. Ghi âm là mô phỏng STT với bước sửa/xác nhận; không bật mic thật. Chat không biến thành Answer; hướng dẫn và mô phỏng có phạm vi trợ giúp khác nhau. Lỗi lưu giữ nháp, lỗi phản hồi giữ bài đã nộp. Câu chưa trả lời khác điểm 0. Kết quả mẫu có nhãn; không có chấm năng lực thật.

Chi tiết từng nút/nhánh lỗi: [USE_CASES.md](USE_CASES.md). Thiết kế, token, breakpoint và acceptance P06: [ui_direction.md](ui_direction.md). Những giới hạn thời gian, retention, threshold và policy tài khoản nêu trong use case là đề xuất bàn giao cho owner nghiệp vụ, không tự sửa spec/backlog trong hai task này.

## Tư duy tính toán

Phân rã sáu khu vực/ba luồng nhập-chat-nộp. Nhận diện mẫu trạng thái nháp/lỗi/thử lại/quay lại. Trừu tượng hóa bước người học nhìn thấy, chi tiết trong panel. Thiết kế thuật toán ở mức flow quyết định đủ câu, còn câu, có dữ liệu nền và đúng thời điểm mở kết quả; chưa triển khai thuật toán sản phẩm.
