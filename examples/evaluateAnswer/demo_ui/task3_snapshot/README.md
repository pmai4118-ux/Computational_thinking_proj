# Snapshot câu hỏi và câu trả lời mẫu Task 3

Các JSON trong thư mục này được sao chép từ nhánh
`origin/task3-answer-fixtures-Khoa`, commit
`9106f6d44a8e03ec8d7894a443679de2f0b2f05f`. Demo không cần checkout hoặc đọc
nhánh Git khi đang chạy. Dữ liệu JSON được giữ nguyên; dòng trống thừa ở cuối
`cases.json` đã được chuẩn hóa để kiểm tra whitespace của Git sạch.

Snapshot gồm bốn nhóm câu hỏi C02–C05 và
`question_answer_testcases.json`. Adapter chỉ bật các câu hỏi có cả rubric nguồn
và bộ câu trả lời tương ứng: Java String immutable, tranh chấp tồn kho, tra cứu
nhân viên bằng HashMap, và HashMap key trong bài code review.

Các seed đang `pending_review`. Adapter chuyển các mức 0/1/2 thành các mốc kiểm
tra tích lũy cho evaluator Task 2 và luôn đặt `exampleOnly=true`. UI chỉ nhận
nội dung câu hỏi, nhãn loại câu trả lời và văn bản câu trả lời. Điểm tham chiếu,
trạng thái chia calibration/held-out và nhận xét annotator không được gửi cho
trình duyệt. Các kết quả AI trực tiếp trên những dữ liệu này chưa phải benchmark.

Khi Task 3 cập nhật rubric hoặc fixture, hãy tạo snapshot mới có commit nguồn
mới và nhờ người review kiểm tra lại adapter; không sửa snapshot để giả lập dữ
liệu đã được phê duyệt.
