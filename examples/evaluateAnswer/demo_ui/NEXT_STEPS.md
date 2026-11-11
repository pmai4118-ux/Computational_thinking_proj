# Yêu cầu bàn giao cho người tiếp theo

Đây là yêu cầu tiếp nối cho demo Task 2, chưa phải ticket backlog đã được nhóm
phân công. Core evaluator hiện tại được giữ nguyên; phần tiếp theo tập trung vào
tích hợp nội dung đã duyệt và kết nối luồng demo với ứng dụng MVC-S.

## P0 — Dùng được nội dung Task 3 đã review

- Thay snapshot demo bằng giao diện đọc từ question-bank repository/service đã
  thống nhất; không phụ thuộc checkout một Git branch ở runtime.
- Chỉ cho phép câu hỏi có `review.status=approved`, đủ provenance/giấy phép và
  rubric-version khớp. Giữ nội dung `pending_review` ở chế độ trình diễn có nhãn.
- Chốt adapter cho rubric 0/1/2 với người sở hữu Task 3; chứng minh mốc điểm cao
  hơn bao hàm mốc thấp hơn và không đổi tiêu chí nguồn âm thầm.
- Có người review độc lập cho từng đáp án mẫu: trạng thái từng criterion, trích
  dẫn bằng chứng, điểm, feedback và phương án diễn đạt tương đương. Tách dữ liệu
  đã review khỏi các mẫu tổng hợp đang chờ review.
- Tạo recording `answerEvaluation/1` khớp chính xác question/rubric version và
  input digest cho câu hỏi demo được chọn; preview phải hoạt động khi provider
  không sẵn sàng và không gọi AI.

## P1 — Luồng câu hỏi và câu trả lời đầy đủ

- Chọn câu hỏi từ API/repository; khi đổi câu hỏi phải nạp đúng prompt, code,
  yêu cầu, rubric và câu trả lời mẫu, xóa kết quả cũ, giữ nháp riêng theo câu hỏi.
- Nhận diện câu hỏi/câu trả lời lạ, JSON sai schema, rubric/version không khớp
  và nguồn chưa được duyệt bằng lỗi có thể khôi phục; không tạo kết quả chấm.
- Khi nối vào app chính, giữ MVC-S: View gọi Controller, Controller gọi Service,
  Service dùng Model/repository; không để View tự đọc JSON hoặc tính điểm.
- Dùng answer ID và revision bất biến cho mỗi lần nộp. Retry cùng snapshot phải
  tái sử dụng báo cáo; provider lỗi không sửa câu trả lời và không lưu điểm.

## P1 — Chất lượng demo và an toàn dữ liệu

- Bổ sung kiểm tra API và UI cho đổi câu hỏi, giữ nháp, mẫu khớp câu hỏi, sai ID,
  thiếu recording, provider lỗi và giữ nguyên câu trả lời.
- Kiểm tra bàn phím, trạng thái tải/lỗi, bố cục hẹp và ngôn ngữ tiếng Việt.
- Chỉ ghi log mã lỗi đã làm sạch; không log API key, câu trả lời, prompt đầy đủ
  hoặc transcript Antigravity.
- Ghi lại chính xác commit dữ liệu, phiên bản model/prompt, chế độ recorded/live,
  lệnh tái hiện và kết quả kiểm tra. Kết quả recorded không được gộp với đánh giá
  chất lượng từ provider trực tiếp.

## Điều kiện hoàn tất bàn giao

Người review khác người triển khai xác nhận nội dung nguồn, license/provenance,
rubric và toàn bộ đáp án tham chiếu; chọn câu hỏi và nạp đáp án từ repository;
preview recorded chạy không cần credentials; AI live dùng cùng API contract và
đúng rubric đã chọn; chạy bộ kiểm tra dự án theo `AGENTS.md`; không đưa secrets,
thư mục `artifacts/` hoặc dữ liệu cá nhân vào commit.
