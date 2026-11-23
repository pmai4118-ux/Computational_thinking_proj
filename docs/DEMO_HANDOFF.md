# Bàn giao nhánh `Demo`

Cập nhật: 23/11/2026. Nhánh: `Demo`. Mốc mã đã kiểm tra: `341e833` (trước commit tài liệu này).

## 1. Nguồn mã đã gộp

| Thứ tự | Nguồn | Commit tại lúc gộp | Nội dung chính |
| --- | --- | --- | --- |
| 1 | `MERGE-Q01-E05-E06-E09-E04-I04-I06` | `b1195d1` | Luồng chấm và lưu kết quả, API I04, đề xuất và lượt luyện I06; kế thừa Q01, E04–E09 và các phụ thuộc nền tảng. |
| 2 | `codex/c08-seed-bank-validation-import` | `ed7d920` | C08 kiểm tra và import ngân hàng seed đã duyệt. |
| 3 | `main` | `491da84` | Đồng bộ mã chung mới nhất tại thời điểm tạo Demo, trong đó có bất biến điểm tối đa F02. |
| 4 | `codex/u06-exercise-practice` | `f99e690` | Chuỗi UI U03 → U04 → U05 → U06. |
| 5 | Mã tích hợp viết trên `Demo` | `341e833` | Mặc định Antigravity, nối nút U06 với I06, thêm API đọc tổng kết và kiểm tra live. |

Các mã nhiệm vụ có commit trong lịch sử `Demo`:

- **Nội dung:** C01–C06, C08. C02–C05 cung cấp 8 câu hỏi đã duyệt, chia đều cho 4 dạng; C06 cung cấp 5 bài tập có nguồn và ánh xạ kỹ năng.
- **Nền tảng và hợp đồng:** P02–P08, F02–F06. P04 định nghĩa DTO/API; F04 lưu SQLite; F05 ghép ứng dụng; P07 cung cấp lựa chọn Antigravity.
- **Đánh giá:** E01–E09, Q01. E04 có adapter AI, E05 kiểm tra bằng chứng, E06 tính điểm bằng mã Python, E09 điều phối và lưu kết quả.
- **Phiên và API:** I01–I04, I06. I03 lưu bài chống gửi trùng; I04 đánh giá/đọc lại/retry an toàn; I06 đề xuất bài tập và tạo lượt luyện từ câu trả lời đã lưu.
- **Giao diện:** U01–U06. U03 là nơi trả lời, U04 là trang căn cứ theo tiêu chí, U05 là trang tổng kết, U06 là trang bài tập.

Đây là danh sách **mã đã hiện diện trong lịch sử nhánh**, không có nghĩa toàn bộ tiêu chí nghiệm thu của mọi mã đều đã được kiểm định đầy đủ. Phần 2 ghi chính xác những luồng đã chạy.

Các điểm nối chính để tiếp tục phát triển:

| Lớp | File chính | Trách nhiệm |
| --- | --- | --- |
| Khởi tạo ứng dụng | `source/main.py` | Ghép router, cấu hình provider và kho SQLite. |
| API | `source/Control/interview_controller.py`, `evaluation_controller.py`, `saved_evaluation_controller.py`, `session_summary_controller.py`, `exercise_controller.py` | Phiên/câu trả lời, đánh giá, đọc kết quả, tổng kết và bài tập. |
| Nghiệp vụ | `source/service/evaluation_service.py`, `recommendation_service.py`, `question_bank_service.py` | Điều phối đánh giá, ánh xạ điểm thiếu với bài tập, kiểm tra seed. |
| AI và lưu trữ | `source/service/providers/antigravity_provider.py`, `source/Model/repositories/sqlite_repository.py` | Gọi Antigravity và lưu dữ liệu bền vững. |
| Giao diện | `source/view/templates/`, `source/view/static/` | Trang thiết lập, trả lời, xem kết quả, tổng kết và luyện tập. |

## 2. Chức năng đang chạy được

| Luồng người dùng | Chức năng và đường đi | Bằng chứng |
| --- | --- | --- |
| Bắt đầu | Trang `/` và `/setup` chọn Backend Developer, Intern/Fresher, tiếng Việt; tạo phiên với 4 câu hỏi từ ngân hàng đã duyệt. `POST /api/sessions`, `GET /api/sessions/{session_id}` kiểm tra cookie sở hữu phiên. | Đã thao tác trên trình duyệt; API và test phiên đạt. |
| Trả lời | Workspace `/sessions/{session_id}` hiển thị đề, mã, ràng buộc; giữ bản nháp trong trình duyệt; `POST /api/sessions/{session_id}/answers` lưu nguyên văn vào SQLite, dùng `client_submission_id` để chống gửi trùng. | Đã gửi bài trên trình duyệt và nhận `201 Created`; các test I03 đạt. |
| Chấm bằng AI thật | `POST /api/answers/{answer_id}/evaluate` gọi **Antigravity CLI `agy`** với `gemini-3.8-flash-medium`. AI diễn giải bằng chứng; E05 xác thực tiêu chí/trích dẫn; E06 tính điểm theo rubric bằng Python; E09 lưu kết quả. | Kiểm tra live từ ứng dụng: câu trả lời tổng hợp được chấm **4/6**, ba tiêu chí có trạng thái và căn cứ; `model_id=gemini-3.8-flash-medium`. |
| Đọc kết quả và retry | `GET /api/answers/{answer_id}/evaluation` đọc bản đã lưu; gọi đánh giá lại bản hoàn tất dùng lại kết quả. I04 chặn ghi trùng đồng thời; lỗi phục hồi được giữ nguyên bài gốc và cho retry. | Test I04, E09 và live end-to-end đạt; GET trả cùng `evaluation_id`. |
| Báo cáo câu trả lời | `/sessions/{session_id}/review` cho xem điểm từng tiêu chí, đoạn trích gốc và lý do đạt/chưa đạt/chưa đủ bằng chứng. | Trình duyệt hiển thị 4/6 và tiêu chí thiếu kiểm thử; nội dung trích dẫn khớp bài đã gửi. |
| Tổng kết hiện tại | `/sessions/{session_id}/summary` dùng `GET /api/sessions/{session_id}/summary` để hiển thị số câu đã chấm, câu chưa làm, điểm từng câu và điểm thiếu đã xác nhận. API từ chối trình duyệt không sở hữu phiên. | Trình duyệt hiển thị **1/4 câu có kết quả**, 3 nhóm chưa làm và một điểm thiếu; test quyền sở hữu đạt. |
| Ngân hàng seed | C08 kiểm tra skill ID, rubric, nguồn/giấy phép, trạng thái review và phiên bản; import bản hợp lệ và báo lỗi có vị trí; chặn bộ dữ liệu thiếu độ phủ bắt buộc. Câu chưa review hoặc thiếu giấy phép không được chọn. | Bộ test C08 đạt; dữ liệu hiện có 8 câu hỏi và 5 bài tập. |
| Bài tập và luyện lại | `GET /api/sessions/{session_id}/exercises` trả bài đã duyệt gắn với điểm thiếu, lý do và prerequisite; `GET /api/exercises/{exercise_id}` trả hướng dẫn. Nút **Luyện lại với câu hỏi khác** trên U06 gọi `POST /api/sessions/{session_id}/answers/{answer_id}/practice`, rồi mở workspace của phiên mới. Nếu không có bài/biến thể hợp lệ, UI nêu rõ thay vì tạo đề xuất giả. | Trình duyệt đã mở hướng dẫn và tạo phiên luyện 1 câu bằng câu hỏi khác câu gốc; API trả `201 Created`. |

`fixture` là provider mẫu xác định để chạy test ngoại tuyến; kết quả mang nhãn **Dữ liệu minh họa**. Nhánh `Demo` dùng `EVALUATION_PROVIDER=antigravity` theo mặc định và [run_demo.ps1](../run_demo.ps1) ép dùng Antigravity. Khi AI lỗi, ứng dụng báo lỗi và giữ bài đã lưu; không tự đổi sang fixture.

## 3. Kiểm tra đã thực hiện

Chạy từ thư mục gốc repository với môi trường `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .local/pytest-demo-final-2 -p no:cacheprovider --tb=short
```

Kết quả: **197 passed, 3 skipped**. Ba ca skip theo mặc định là ca live E09 qua Antigravity, ca live Demo end-to-end và ca Gemini API tùy chọn. Chúng đã được bật và chạy riêng:

- `E09_LIVE_TEST=1`: **1 passed**, gọi `agy` thật từ bài trả lời đã lưu.
- `DEMO_LIVE_TEST=1`: **1 passed**; Antigravity trả 4/6, một đề xuất bài tập và tạo lượt luyện với câu hỏi khác. Ca này kiểm tra cả API tổng kết và trang liên quan.
- `RUN_GEMINI_LIVE_TEST=1`: **1 passed** với model `gemini-3.5-flash`, chỉ kiểm tra adapter API key dự phòng. Model `gemini-2.5-flash` trả 404 cho tài khoản thử nghiệm; điều này không ảnh hưởng provider Antigravity chính.

Ngoài pytest, đã chạy máy chủ bằng [run_demo.ps1](../run_demo.ps1) và thao tác luồng trên trình duyệt: setup → trả lời → Antigravity chấm → review → tổng kết → hướng dẫn bài tập → nút luyện lại → câu hỏi khác. Đây là một ca **smoke test**, chưa phải phép đo độ chính xác của AI trên bộ câu trả lời chuẩn.

## 4. Giới hạn và việc cần làm tiếp

- **I05 chưa hoàn chỉnh:** chưa có `POST /api/sessions/{session_id}/next` hoặc `/end`. Phiên chọn sẵn 4 câu nhưng UI hiện chưa chuyển từ câu 1 sang câu 2–4 và chưa kết thúc sớm. API đọc tổng kết trên `Demo` chỉ cho báo cáo tiến độ hiện có; không thay thế toàn bộ I05.
- **U07 chưa hoàn chỉnh:** các màn hình nêu ở phần 2 đã nối và kiểm tra; chưa có kiểm định toàn bộ phiên 4 câu qua UI. Cần I05 trước khi nghiệm thu U07 trọn vẹn.
- **Q03 chưa thực hiện trên nhánh này:** chưa có báo cáo so sánh nhiều câu trả lời với đánh giá chuyên gia; điểm 4/6 của ca tổng hợp chỉ chứng minh lời gọi và luồng dữ liệu hoạt động.
- Vai trò/cấp độ/ngôn ngữ đang hỗ trợ: **Backend Developer · Intern/Fresher · tiếng Việt**. Lượt luyện lại do I06 tạo là phiên **1 câu** dựa trên điểm thiếu được xác nhận.

## 5. Cách chạy cho người tiếp nhận

```powershell
uv sync --locked
agy models
.\run_demo.ps1
```

Đăng nhập `agy` trên máy chạy ứng dụng trước khi khởi động. Script xác nhận model và mở ứng dụng tại `http://127.0.0.1:8000/`. SQLite mặc định ở `.local/interview.sqlite3`; không đưa khóa, dữ liệu bài làm hoặc file trong `.local/` lên Git. Không dùng fixture để kết luận chất lượng đánh giá AI.
