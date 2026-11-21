# Tuần 2 · Nhật ký triển khai VA

Đọc từng mục theo thứ tự: đầu vào, cách xử lý, cách tự kiểm tra và bằng chứng bàn giao. Chạy lệnh trong terminal tại thư mục gốc repo. Các lệnh dùng dữ liệu giả lập nên không tốn lượt gọi Gemini.

## E07 · Giải thích điểm rubric

Nhánh `codex/e07-feedback` xuất phát từ `codex/week1-delivery`. Mở `source/service/evaluation_service.py`, tìm `build_feedback`. Hai kiểu dữ liệu phản hồi nằm trong `source/Model/evaluation.py`.

1. Nhận kết quả đã chấm cùng rubric. Kiểm tra trạng thái hoàn thành, mã và phiên bản rubric, tập mã tiêu chí để tránh giải thích bằng rubric của câu khác.
2. Ghép từng criterion check với tiêu chí theo ID. Giữ trích dẫn hoặc quan sát từ E05, lấy nguyên điểm E06 và tra mô tả của mức tương ứng. Lời giải thích sử dụng mẫu tiếng Việt.
3. Khi có thiếu sót đã xác nhận và có căn cứ, thêm gợi ý cho chính tiêu chí đó. Khi chưa đủ căn cứ, hiển thị lý do, giữ điểm trống. Ví dụ, test câu ngắn “O(log n), O(1).” kiểm tra việc giữ điểm tối đa do E06 tính.
4. Trên nhánh E07 chạy `uv run --locked python -m pytest -v test/service/test_feedback.py`. Đã đạt 5/5 ca E07 và 90/90 ca toàn nhánh. E09 có thể gọi hàm này để chuyển kết quả cho lớp tiếp theo.

Bàn giao: [PR E07 #29](https://github.com/pmai4118-ux/Computational_thinking_proj/pull/29).

## E08 · Giới hạn và xử lý lỗi Gemini REST

Nhánh `codex/e08-provider-failures` xuất phát từ `codex/week1-delivery`. Phần này được kiểm tra độc lập với PR E07. F06 cung cấp settings, adapter E04 cung cấp request và bộ phân tích JSON. Mở `source/config.py` và `source/service/providers/gemini_provider.py`.

1. Đọc cấu hình ở chế độ Gemini. Kiểm tra kích thước toàn bộ request UTF-8 trước khi gửi, truyền timeout cho transport, giới hạn token sinh và số byte đọc về.
2. Trước **mỗi lần gửi**, giữ một lượt trong bảng SQLite `gemini_budget` của `DATABASE_PATH`. Các tiến trình dùng chung file sẽ dùng chung ngân sách. Khởi động lại vẫn giữ số lượt đã dùng. Nếu ngân sách còn 1 và lần đầu timeout, retry bị chặn trước khi gửi. Khi lập provider trực tiếp cho unit test mà không cấp đường dẫn, bộ đếm nằm trong bộ nhớ của instance.
3. Chỉ thử lại tối đa một lần khi gặp timeout, lỗi mạng tạm thời đã phân loại, HTTP 429 hoặc HTTP 500/502/503/504. Dừng ngay khi hết ngân sách, gặp lỗi thanh toán, từ chối vì an toàn hoặc nhận JSON sai. HTTP 429 kéo dài cũng dừng sau số lần cho phép. Lỗi trả về qua `GeminiProviderError` để caller xử lý; chỉ batch diễn giải thành công mới sang bước chấm.
4. Tra log bằng mã request dùng chung giữa các lần thử. Mỗi bản ghi có số lần thử, thời gian ms, kết quả và tổng token khi phản hồi thành công cung cấp số này. Các trường được chọn cụ thể để tránh ghi khóa, prompt, câu trả lời, header và nội dung lỗi thô.

| Biến môi trường | Mặc định | Ý nghĩa |
| --- | ---: | --- |
| GEMINI_INPUT_BYTES | 250000 | Giới hạn byte cho toàn bộ request |
| GEMINI_RESPONSE_BYTES | 1000000 | Giới hạn byte cho response |
| GEMINI_OUTPUT_TOKENS | 4096 | Giới hạn token yêu cầu model sinh |
| GEMINI_TIMEOUT_SECONDS | 30 | Timeout cho mỗi lần gọi, từ 1 đến 120 giây |
| GEMINI_REQUEST_BUDGET | 50 | Trần lượt gửi tích lũy cho cùng database, gồm cả retry. Đặt 0 để chặn mọi lượt gửi |
| GEMINI_MAX_RETRIES | 1 | Chấp nhận 0 hoặc 1 lần thử lại |

Mức 50 là mặc định triển khai, nhóm có thể đặt theo ngân sách thật. Tăng trần cho cùng database sẽ cấp thêm phần chênh lệch. Chạy test từ nhánh E08:

```powershell
uv run --locked python -m pytest -v test/service/test_provider_failures.py
```

Test mock xác minh số lần transport thực sự được gọi, loại lỗi, trường hợp phục hồi, việc dùng chung ngân sách sau khi tạo lại provider và nội dung log. Để kiểm tra hồi quy, chạy:

```powershell
uv run --locked python -m pytest -q
```

Kết quả chạy trên nhánh E08: **10/10** test E08 và **95/95** test toàn nhánh đạt. Chưa gọi API thật.

## Quy trình bàn giao cho các task sau

1. Đọc mục có mã task trong `docs/TASK_INSTRUCTIONS.md`. Kiểm tra code của các task tiên quyết trên nhánh nền.
2. Tạo nhánh riêng. Ghi vào README này luồng dữ liệu, file chính, quyết định triển khai và ví dụ nghiệm thu của task.
3. Chạy test riêng rồi chạy toàn bộ test. Ghi số test theo đúng nhánh, phân biệt test mock, test giao diện và lần chạy provider thật.
4. Dùng `git status --short`, thêm đúng file của task, commit với tiêu đề `[Mã task] Mô tả` rồi push nhánh. Trên GitHub chọn nhánh nền làm base và nhánh task làm compare.
5. Ghi cách tái hiện kết quả vào PR, dán link PR vào task trên bảng sprint và chuyển sang **Chờ review**.


### Bổ sung cho đường chạy thực tế của nhóm qua Antigravity CLI

Chọn provider `antigravity`, model `gemini-3.8-flash-medium` và đăng nhập CLI. Nếu Windows chưa nhận lệnh qua PATH, trong PowerShell đặt biến cho phiên hiện tại:

```powershell
$env:EVALUATION_PROVIDER = "antigravity"
$env:ANTIGRAVITY_EXECUTABLE = "$env:LOCALAPPDATA\agy\bin\agy.exe"
$env:ANTIGRAVITY_MODEL = "gemini-3.8-flash-medium"
```

Adapter agy dùng timeout ANTIGRAVITY_TIMEOUT_SECONDS và cùng bộ đếm SQLite, các biến GEMINI_REQUEST_BUDGET, GEMINI_MAX_RETRIES, GEMINI_INPUT_BYTES, GEMINI_RESPONSE_BYTES với Gemini REST. Giới hạn token sinh ở bảng trên áp dụng cho REST. Mỗi lần chạy subprocess tiêu một lượt ngân sách. Adapter thử lại timeout hoặc quota tạm thời trong giới hạn cấu hình và ghi mã yêu cầu, lần thử, độ trễ và mã lỗi. Năm ca giả lập cho CLI kiểm tra timeout, quota, xác thực, từ chối và đầu ra sai. Chạy riêng bằng `python -m pytest -q test/service/test_provider_failures.py -k agy`. Lần thử trực tiếp trước khi hoàn tất thiết lập CLI chưa trả về kết quả đánh giá hợp lệ.
Kiểm tra live trên máy nhóm: CLI trả sự kiện SUCCESS nhưng adapter từ chối payload đánh giá; chưa tạo điểm. Parser đã hỗ trợ structured_output dạng object hoặc chuỗi JSON và báo vị trí lỗi schema. Test hồi quy kiểm tra cả payload chuỗi hợp lệ và thiếu tiêu chí. Ngày 21/11/2026, nhóm chạy lại trên Windows bằng Antigravity CLI 1.5.13 với một câu trả lời mẫu, ngân sách 1 lượt và retry bằng 0. Terminal in `gemini-3.8-flash-medium 2`: adapter trả về hai quan sát rubric. Lần chạy này kiểm tra đường diễn giải; các tình huống lỗi được tái hiện bằng test ngoại tuyến.
Nghiệm thu E08 sau tích hợp: 16/16 test riêng và 101/101 test toàn nhánh đạt.

## E09 · Đánh giá bản nộp đã lưu

Điểm vào cho I04 là `evaluation_service.evaluate_saved_answer(answer_ref)`, trả về cặp kết quả và feedback. App factory cung cấp interpreter và ba repository. E09 đọc nguyên văn bài theo ID và revision, rồi đọc đúng phiên bản câu hỏi và rubric. E02 cung cấp quan sát fixture. E05 kiểm tra đủ tiêu chí và đối chiếu trích dẫn. E06 tính điểm, E07 giải thích theo từng tiêu chí và F04 lưu kết quả cùng các kiểm tra trong một giao dịch. Khi mở lại, E07 dựng feedback từ dữ liệu đã lưu.

Dùng SQLite tạm trong mỗi test. Retry sau khi đã lưu dùng lại kết quả. Khi hai lượt bắt đầu đồng thời, cả hai có thể gọi provider; lúc ghi, SQLite khóa ghi và trả lại kết quả đã commit đầu tiên cho cả hai.

- Chạy ngoại tuyến: `python -m pytest -v test/service/test_evaluation_flow.py`.
- Theo dõi riêng luồng bài ngắn đúng rubric: thêm `-k short_verified`. Fixture khai báo ý đã đạt, Python xác minh trích dẫn và tính điểm; test mở lại SQLite để so sánh.
- Gây lỗi: thêm `-k failure` để kiểm tra rollback, nguyên văn bài nộp và lỗi feedback.
- Gọi thật trong PowerShell đã đăng nhập: đặt `$env:E09_LIVE_TEST="1"` và `$env:ANTIGRAVITY_EXECUTABLE="$env:LOCALAPPDATA\agy\bin\agy.exe"`, rồi chạy `python -m pytest -v test/service/test_evaluation_flow.py -k live_agy --tb=line`. Mỗi lần chạy dùng database tạm, cho phép một lượt và tắt retry. Sau đó chạy `Remove-Item Env:E09_LIVE_TEST`. Lần thử E09 trong phiên phát triển dừng ở adapter do CLI không trả kết quả hoàn chỉnh. Lần chạy E08 thành công không thay thế bước kiểm tra E09 này.
Lần test E09 trên máy nhóm nhận SUCCESS nhưng criterion_checks.crit.atomicity vi phạm quy tắc căn cứ; không tạo điểm. Adapter hiện yêu cầu rõ cách dùng quote, observation và offsets, đồng thời báo từng quy tắc bị vi phạm mà không in bài làm.
Nghiệm thu sau bản sửa (21/11/2026): bộ test ngoại tuyến toàn nhánh đạt 115 passed, 1 skipped. Trên máy nhóm, test_live_agy_saved_answer với Flash Medium đạt 1 passed, 9 deselected trong 18,07 giây. Test đọc bản nộp từ SQLite, gọi provider một lần, kiểm tra căn cứ, chấm điểm, dựng feedback, lưu và trả lại cùng kết quả khi gọi lại.
