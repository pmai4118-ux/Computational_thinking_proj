# Quy trình kiểm định câu trả lời tổng hợp (C07)

## Phạm vi dữ liệu hiện có

`test/fixtures/expected_evaluations.json` tham chiếu 24 câu trả lời **tổng hợp**, lưu riêng trong `test/fixtures/answers/`. Mỗi nhóm câu hỏi của ngân hàng đã review trên `Demo` có sáu dạng: đúng, thiếu, sai, tương đương, mơ hồ và chèn chỉ dẫn. Bộ này không chứa hồ sơ hoặc bài làm của sinh viên thật và không được import vào ngân hàng câu hỏi dùng cho phiên học.

| Nhóm | Câu hỏi và rubric trong `Demo` | Số ca |
| --- | --- | ---: |
| C02 | `prog.c02.mutable_default_arg.v1` / `rubric.c02.mutable_default_arg.v1` | 6 |
| C03 | `case.c03.inventory_race.v1` / `rubric.c03.inventory_race.v1` | 6 |
| C04 | `algo.c04.bisect_left_bounds.v1` / `rubric.c04.bisect_left_bounds.v1` | 6 |
| C05 | `review.c05.binary_search_precheck.v1` / `rubric.c05.binary_search_precheck.v1` | 6 |

Sáu văn bản C03 được lấy từ `origin/task3-answer-fixtures-Khoa` tại `4d5fc33`. Mười tám văn bản còn lại được viết lại cho câu hỏi và rubric hiện có trên `Demo`. Nhánh nguồn dùng câu Java khác cho C02/C04/C05 và một rubric C03 khác dù cùng ID. Vì thế **không chuyển nhãn review cũ** sang bộ này. `question_fingerprint_sha256` khóa nội dung đề, mã, ràng buộc và rubric được dùng khi soạn mỗi ca. Test sẽ báo nếu seed thay đổi mà fixture chưa được xem lại.

## Trạng thái nhãn

**Cả 24 ca hiện chỉ có nhãn nháp** `candidate_judgment`; `independent_reviews` rỗng và `adjudicated_evaluation` là `null`. Các nhãn nháp là giả thuyết để chuẩn bị review, không phải gold labels. Không tính agreement, độ chính xác hoặc điểm benchmark của AI từ các nhãn này. Việc chạy thành công test cấu trúc và gọi Antigravity chỉ chứng minh luồng kỹ thuật hoạt động.

Để hoàn tất C07, hai người cần gán từng tiêu chí độc lập từ đề, rubric và văn bản trả lời, **không xem `candidate_judgment` hoặc nhãn của nhau trước khi nộp**. Mỗi lượt review ghi reviewer, phiên bản rubric, trạng thái/điểm từng tiêu chí, trích dẫn nguyên văn, lý do và thời điểm. Ghi mọi bất đồng, sau đó một người phân xử chốt `adjudicated_evaluation`. Chỉ đánh dấu ca là `adjudicated` khi đã có hai review độc lập và biên bản phân xử. Nếu thay câu hỏi hoặc rubric, vô hiệu hóa review liên quan và gán nhãn lại.

## Chia bộ và chạy model

Mỗi nhóm có ba ca `calibration` và ba ca `held_out`: tổng cộng 12/12. Mỗi dạng câu trả lời có hai ca ở mỗi bộ. Phân chia được ghi cố định trong JSON trước khi chạy model; không chia lại sau khi nhìn kết quả. Chỉ dùng `calibration` để sửa prompt, ngưỡng hoặc model. Với `held_out`, trước khi đánh giá phải khóa và ghi rõ phiên bản prompt/model, ngân sách và tiêu chí chấp nhận. Nếu xem kết quả held-out rồi sửa cấu hình, bộ đó không còn là kiểm định độc lập cho cấu hình mới.

Khi có nhãn đã phân xử, Q03 mới so sánh kết quả Antigravity theo từng tiêu chí, trích dẫn, câu hỏi, loại câu trả lời và trạng thái chưa đủ căn cứ; ghi độ trễ, lỗi và kích thước mẫu. Bài có chèn chỉ dẫn phải được xử lý như dữ liệu người học: không làm theo lệnh tự gán điểm trong câu trả lời. Lỗi provider không được quy đổi thành điểm 0, và bản trả lời gốc phải được giữ để retry.

Kiểm tra cấu trúc hiện tại:

```powershell
.\.venv\Scripts\python.exe -m pytest -q test/test_c07_demo_fixtures.py
```

Ca live của `Demo` kiểm tra Antigravity thật theo luồng ứng dụng. Nó không dùng bộ held-out C07 để tuyên bố độ chính xác khi các nhãn còn tạm thời.
