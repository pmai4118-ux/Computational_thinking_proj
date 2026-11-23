# Bàn giao nhánh `Demo`

Cập nhật: 23/11/2026. Nhánh: `Demo`. Mốc mã chức năng của lần bàn giao này: `5d32ae4` (trước commit tài liệu).

## 1. Nguồn mã đã gộp

| Thứ tự | Nguồn | Commit tại lúc gộp | Nội dung chính |
| --- | --- | --- | --- |
| 1 | `MERGE-Q01-E05-E06-E09-E04-I04-I06` | `b1195d1` | Luồng chấm và lưu kết quả, API I04, đề xuất và lượt luyện I06; kế thừa Q01, E04–E09 và các phụ thuộc nền tảng. |
| 2 | `codex/c08-seed-bank-validation-import` | `ed7d920` | C08 kiểm tra và import ngân hàng seed đã duyệt. |
| 3 | `main` | `491da84` | Đồng bộ mã chung mới nhất tại thời điểm tạo Demo, trong đó có bất biến điểm tối đa F02. |
| 4 | `codex/u06-exercise-practice` | `f99e690` | Chuỗi UI U03 → U04 → U05 → U06. |
| 5 | Mã tích hợp viết trên `Demo` | `341e833` | Mặc định Antigravity, nối nút U06 với I06, thêm API đọc tổng kết và kiểm tra live. |
| 6 | `codex/c02-programming-questions` | `813df45` → `a19fad8` | Lấy đúng commit sửa ví dụ closure C02 và test của câu hỏi. |
| 7 | `codex/f04-sqlite-repository` | `51f7e7d` → `71bcf90` | Lấy đúng commit F04 khóa ghi trước khi kiểm tra mã gửi bài trùng. |
| 8 | `codex/i01-interview-service` | `e801fbc` → `a9eb06f` | Lấy đúng commit I01 chặn chỉ số chuyển câu âm. |
| 9 | `codex/u07-api-client-integration` | `11a4f7c` → `85838e2` | Đưa phần U07 sang `Demo`, giữ luồng I06 và giải quyết xung đột ở bài tập/test. |
| 10 | I05 viết trên `Demo` | `8ddebf6` | Thêm API và giao diện chuyển câu/kết thúc sớm, test phiên 4 câu. |
| 11 | `codex/c07-demo-aligned-fixtures`, lấy chọn lọc từ `task3-answer-fixtures-Khoa` | `4d5fc33` → `2d41a25` → `5d32ae4` | C07: 24 câu trả lời tổng hợp khớp câu hỏi/rubric của Demo, chia calibration/held-out và kiểm tra cấu trúc. Nhãn còn tạm thời. |

U07 trên `origin` có lịch sử Git không chung gốc với `Demo`, nên chỉ đưa commit U07 sang và xử lý xung đột; không gộp nguyên nhánh U03–U07. Các nguồn C02, F04, I01 cũng được lấy theo commit cụ thể để tránh kéo các merge commit cũ.

Nhánh nguồn C07 chứa câu hỏi Java và một ứng dụng đánh giá khác; merge thử với `Demo` phát hiện 14 xung đột. Chỉ sáu văn bản trả lời C03 được chuyển nguyên từ nguồn; 18 văn bản còn lại được viết lại cho seed Demo. Không đưa code ứng dụng, seed Java hoặc nhãn review không còn hợp lệ từ nhánh đó vào `Demo`.

Các mã nhiệm vụ có commit trong lịch sử `Demo`:

- **Nội dung:** C01–C08. C02–C05 cung cấp 8 câu hỏi đã duyệt, chia đều cho 4 dạng; C06 cung cấp 5 bài tập có nguồn và ánh xạ kỹ năng; C07 có 24 ca tổng hợp **chưa được gán nhãn độc lập**; C08 kiểm tra seed.
- **Nền tảng và hợp đồng:** P01–P08, F01–F06. P04 định nghĩa DTO/API; F04 lưu SQLite; F05 ghép ứng dụng; P07 cung cấp lựa chọn Antigravity.
- **Đánh giá:** E01–E09, Q01. E04 có adapter AI, E05 kiểm tra bằng chứng, E06 tính điểm bằng mã Python, E09 điều phối và lưu kết quả.
- **Phiên và API:** I01–I06. I03 lưu bài chống gửi trùng; I04 đánh giá/đọc lại/retry an toàn; I05 chuyển câu và kết thúc sớm; I06 đề xuất bài tập và tạo lượt luyện từ câu trả lời đã lưu.
- **Giao diện:** U01–U07. U03 là nơi trả lời, U04 là trang căn cứ theo tiêu chí, U05 là trang tổng kết, U06 là trang bài tập, U07 dùng API client chung cho các màn hình.

Đây là danh sách **mã đã hiện diện trong lịch sử nhánh**, không có nghĩa toàn bộ tiêu chí nghiệm thu của mọi mã đều đã được kiểm định đầy đủ. Phần 2 ghi chính xác những luồng đã chạy.

Các điểm nối chính để tiếp tục phát triển:

| Lớp | File chính | Trách nhiệm |
| --- | --- | --- |
| Khởi tạo ứng dụng | `source/main.py` | Ghép router, cấu hình provider và kho SQLite. |
| API | `source/Control/interview_controller.py`, `evaluation_controller.py`, `saved_evaluation_controller.py`, `session_summary_controller.py`, `exercise_controller.py` | Phiên/câu trả lời, chuyển câu, kết thúc sớm, đánh giá, đọc kết quả, tổng kết và bài tập. |
| Nghiệp vụ | `source/service/evaluation_service.py`, `recommendation_service.py`, `question_bank_service.py` | Điều phối đánh giá, ánh xạ điểm thiếu với bài tập, kiểm tra seed. |
| AI và lưu trữ | `source/service/providers/antigravity_provider.py`, `source/Model/repositories/sqlite_repository.py` | Gọi Antigravity và lưu dữ liệu bền vững. |
| Giao diện | `source/view/templates/`, `source/view/static/js/api_client.js` | Trang thiết lập, trả lời, xem kết quả, chuyển câu, tổng kết và luyện tập. |

## 2. Chức năng đang chạy được

| Luồng người dùng | Chức năng và đường đi | Bằng chứng |
| --- | --- | --- |
| Bắt đầu | Trang `/` và `/setup` chọn Backend Developer, Intern/Fresher, tiếng Việt; tạo phiên với 4 câu hỏi từ ngân hàng đã duyệt. `POST /api/sessions`, `GET /api/sessions/{session_id}` kiểm tra cookie sở hữu phiên. | Đã thao tác trên trình duyệt; API và test phiên đạt. |
| Trả lời | Workspace `/sessions/{session_id}` hiển thị đề, mã, ràng buộc; giữ bản nháp trong trình duyệt; `POST /api/sessions/{session_id}/answers` lưu nguyên văn vào SQLite, dùng `client_submission_id` để chống gửi trùng. F04 khóa giao dịch ghi trước khi kiểm tra trùng. | Đã gửi bài trên trình duyệt và nhận `201 Created`; test hai request đồng thời cùng mã gửi chỉ lưu một bài. |
| Chấm bằng AI thật | `POST /api/answers/{answer_id}/evaluate` gọi **Antigravity CLI `agy`** với `gemini-3.8-flash-medium`. AI diễn giải bằng chứng; E05 xác thực tiêu chí/trích dẫn; E06 tính điểm theo rubric bằng Python; E09 lưu kết quả. | Kiểm tra live từ ứng dụng: câu trả lời tổng hợp được chấm **4/6**, ba tiêu chí có trạng thái và căn cứ; `model_id=gemini-3.8-flash-medium`. |
| Đọc kết quả và retry | `GET /api/answers/{answer_id}/evaluation` đọc bản đã lưu; gọi đánh giá lại bản hoàn tất dùng lại kết quả. I04 chặn ghi trùng đồng thời; lỗi phục hồi được giữ nguyên bài gốc và cho retry. | Test I04, E09 và live end-to-end đạt; GET trả cùng `evaluation_id`. |
| Báo cáo câu trả lời | `/sessions/{session_id}/review` cho xem điểm từng tiêu chí, đoạn trích gốc, phản hồi và lý do đạt/chưa đạt/chưa đủ bằng chứng. Kết quả của bản trả lời hiện tại hiện nút chuyển câu. | Trang đã hiển thị căn cứ và nút chuyển câu trong browser test; live Antigravity trả **4/6** cho câu tổng hợp. |
| Chuyển câu và hoàn tất | `POST /api/sessions/{session_id}/next` chỉ tiến khi bản trả lời hiện tại đã đánh giá xong; gọi lặp cùng chỉ số trả trạng thái hiện tại. Nút **Sang câu tiếp theo** mở workspace câu sau; sau câu cuối mở tổng kết `completed`. | Test HTTP đi hết **4/4 câu**, chặn chuyển sớm và không nhảy hai câu khi retry; browser test đã chuyển thực tế từ câu 1 sang câu 2. |
| Kết thúc sớm | Nút **Kết thúc sớm** trong workspace mở xác nhận ngay trên trang rồi gọi `POST /api/sessions/{session_id}/end` với `reason=student_requested`. Báo cáo giữ các câu đã chấm, nêu câu chưa làm; phiên cũ không nhận bài mới. | Test API kiểm tra quyền sở hữu, gọi lặp, trạng thái `ended_early` và bảo toàn kết quả. Browser test xác nhận mở trang tổng kết `Đã kết thúc sớm`. |
| Tổng kết phiên | `/sessions/{session_id}/summary` dùng `GET /api/sessions/{session_id}/summary` để hiển thị số câu đã chấm, câu chưa làm, điểm từng câu và điểm thiếu đã xác nhận; có liên kết về căn cứ từng câu và tiếp tục phiên khi còn dở. Không cộng điểm tổng năng lực cho phần chưa làm. | Test HTTP xác nhận báo cáo đủ 4 câu và báo cáo kết thúc sớm; quyền sở hữu được kiểm tra. |
| Ngân hàng seed | C08 kiểm tra skill ID, rubric, nguồn/giấy phép, trạng thái review và phiên bản; import bản hợp lệ và báo lỗi có vị trí; chặn bộ dữ liệu thiếu độ phủ bắt buộc. Câu chưa review hoặc thiếu giấy phép không được chọn. | Bộ test C08 đạt; dữ liệu hiện có 8 câu hỏi và 5 bài tập. |
| Bài tập và luyện lại | `GET /api/sessions/{session_id}/exercises` trả bài đã duyệt gắn với điểm thiếu, lý do và prerequisite; `GET /api/exercises/{exercise_id}` trả hướng dẫn. Nút **Luyện lại với câu hỏi khác** trên U06 gọi `POST /api/sessions/{session_id}/answers/{answer_id}/practice`, rồi mở workspace của phiên mới. Nếu không có bài/biến thể hợp lệ, UI nêu rõ thay vì tạo đề xuất giả. | Trình duyệt đã mở hướng dẫn và tạo phiên luyện 1 câu bằng câu hỏi khác câu gốc; API trả `201 Created`. |
| API client U07 | `api_client.js` gửi cookie cùng origin, dùng DTO chung và giữ `answer_revision` khi đọc kết quả; các màn hình trả lời, căn cứ, tổng kết, bài tập dùng chung xử lý lỗi. Không chứa SDK/key AI phía trình duyệt. | 10 test U07/U06/trang đánh giá đạt khi tích hợp; browser test xác nhận gửi bài, đọc kết quả và chuyển câu qua API. |

Bộ C07 là tài sản **kiểm định**, không tham gia chấm điểm trong ứng dụng. [Quy trình C07](evaluation_protocol.md) mô tả câu hỏi/rubric, trạng thái nhãn, hai lượt review độc lập còn thiếu và quy tắc dùng bộ held-out. Không dùng `candidate_judgment` làm chuẩn vàng hoặc báo cáo độ chính xác AI.

`fixture` là provider mẫu xác định để chạy test ngoại tuyến; kết quả mang nhãn **Dữ liệu minh họa**. Nhánh `Demo` dùng `EVALUATION_PROVIDER=antigravity` theo mặc định và [run_demo.ps1](../run_demo.ps1) ép dùng Antigravity. Khi AI lỗi, ứng dụng báo lỗi và giữ bài đã lưu; không tự đổi sang fixture. Điểm fixture chỉ kiểm tra luồng phần mềm, không chứng minh chất lượng AI.

### Khi Antigravity phản hồi chậm

Câu trả lời được lưu trước khi gọi AI. Màn hình báo đang đối chiếu rubric, cập nhật thời gian chờ sau 20 giây; nếu tải lại trang, UI đọc trạng thái đã lưu và kiểm tra lại mỗi 5 giây. Khi hoàn tất, UI mở điểm và căn cứ. `run_demo.ps1` mặc định không tự gọi AI lần hai: mỗi lần chờ tối đa 120 giây theo cấu hình Antigravity (cộng thời gian khởi chạy/dọn tiến trình); người dùng có thể đặt `GEMINI_MAX_RETRIES=1` nếu muốn tự thử lại một lần. Nếu hết hạn, API trả `504 PROVIDER_TIMEOUT`, ghi `failed` có thể retry, giữ nguyên bài gốc và **không tạo điểm**. Nút **Thử đánh giá lại** gửi lại đúng bản trả lời đã lưu; lần gọi sau khi đã `completed` chỉ đọc kết quả cũ.

Ngày 23/11/2026, bài kiểm tra end-to-end gọi Antigravity thật hoàn tất trong **74,82 giây**, chấm **4/6**, trả một khuyến nghị và tạo lượt luyện lại. Một phép thử Antigravity thật khác đặt timeout 1 giây xác nhận `504 PROVIDER_TIMEOUT`, `retryable=true`, kết quả lưu `failed` với `total_score=null`, văn bản bài gốc còn nguyên. Bộ kiểm thử giao diện bằng Node xác nhận thông báo chờ lâu, đọc lại kết quả sau khi mở lại trang, và chỉ hiện retry khi lỗi cho phép (`4 passed`). Các thời gian trên là số đo từng lần chạy, không phải cam kết độ trễ.

## 3. Kiểm tra đã thực hiện

Chạy từ thư mục gốc repository với môi trường `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .local/pytest-demo-c07-full -p no:cacheprovider --tb=short
```

Kết quả sau tích hợp C07: **206 passed, 3 skipped**. Ba ca skip theo mặc định là ca E09 qua Antigravity, ca Demo live end-to-end và ca Gemini API key tùy chọn. Đã bật lại hai ca Antigravity sau tích hợp:

- `DEMO_LIVE_TEST=1` với `test/Control/test_demo_live_flow.py`: **1 passed trong 49,14 giây** khi chạy với quyền truy cập phiên đăng nhập `agy`. Antigravity gọi model `gemini-3.8-flash-medium` thật, trả `completed`, **4/6**, một khuyến nghị và tạo lượt luyện với câu hỏi khác. Ca này dùng SQLite mới và gọi API từ tạo phiên tới luyện lại. Lần chạy đầu trong sandbox bị `PROVIDER_TIMEOUT` vì không đọc được phiên đăng nhập Antigravity; API trả lỗi có thể retry và giữ bài gốc.
- `E09_LIVE_TEST=1` với `test/service/test_evaluation_flow.py::test_live_agy_saved_answer`: **1 passed trong 45,81 giây**. Service gọi provider thật một lần, lưu kết quả và dùng lại kết quả khi gọi lại bản trả lời đã hoàn tất.
- Test C07 mới xác nhận đủ 24 văn bản, 4 nhóm × 6 dạng, chia 12 calibration / 12 held-out, ID/phiên bản/fingerprint khớp seed đã duyệt và không có nhãn nào bị khai là adjudicated.
- Ca Gemini API key tùy chọn từng đạt ở mốc `341e833`, nhưng **không chạy lại** trong lần tích hợp này vì `Demo` dùng Antigravity làm provider chính.

Lệnh tái hiện hai ca Antigravity khi máy đã đăng nhập `agy`:

```powershell
$env:DEMO_LIVE_TEST = '1'
.\.venv\Scripts\python.exe -m pytest -q test/Control/test_demo_live_flow.py
$env:E09_LIVE_TEST = '1'
.\.venv\Scripts\python.exe -m pytest -q test/service/test_evaluation_flow.py::test_live_agy_saved_answer
```

Browser test với server fixture sau tích hợp: thiết lập phiên → gửi câu 1 → xem điểm/căn cứ → bấm **Sang câu tiếp theo** → workspace hiện **câu 2/4**. Một phiên khác đã mở trang bài tập, tải hướng dẫn đã duyệt và bấm **Luyện lại với câu hỏi khác**; server trả `201` và mở phiên mới **1/1 câu** bằng câu hỏi khác. Phiên thứ ba bấm **Kết thúc sớm** → **Xác nhận kết thúc**; server trả `200` và trang tổng kết hiện **Đã kết thúc sớm**, **0/4** câu có kết quả. Test HTTP tự động đi hết 4 câu, kiểm tra retry chuyển câu, tổng kết và kết thúc sớm. Browser test fixture và ca Antigravity live dùng hai cấu hình riêng; chúng kiểm tra hai mặt của cùng hợp đồng API.

## 4. Giới hạn và việc cần làm tiếp

- **Kiểm tra UI:** browser test đã thao tác chuyển câu 1 → 2, lượt luyện lại và kết thúc sớm; toàn bộ 4 câu được kiểm tra qua API với fixture. Chưa có browser test tự động đi hết 4 câu với Antigravity thật.
- **U08/Q02 chưa nghiệm thu đầy đủ:** các lỗi chính, retry và quyền sở hữu đã có test; chưa có bộ kiểm tra toàn diện mọi trạng thái giao diện và mọi trường hợp repository/API.
- **Q03 chưa thực hiện trên nhánh này:** chưa có báo cáo so sánh nhiều câu trả lời với đánh giá chuyên gia; điểm 4/6 của ca tổng hợp chỉ chứng minh lời gọi và luồng dữ liệu hoạt động.
- **C07 chưa đủ điều kiện nghiệm thu nhãn:** 24 ca đã tích hợp đúng đề/rubric, nhưng người dùng xác nhận chưa có hai bản review độc lập. Tất cả nhãn hiện là nháp; cần hai người gán nhãn và phân xử trước khi dùng cho Q03 hoặc tuyên bố độ chính xác của Antigravity.
- **Seed trên SQLite cũ:** bản sửa C02 thay đổi mã ví dụ trong seed cùng phiên bản câu hỏi. Ứng dụng không ghi đè câu hỏi đã lưu trong database cũ. Dùng một `DATABASE_PATH` mới để nhận seed đã sửa, giữ nguyên dữ liệu phiên cũ; không xóa database của người học.
- Vai trò/cấp độ/ngôn ngữ đang hỗ trợ: **Backend Developer · Intern/Fresher · tiếng Việt**. Lượt luyện lại do I06 tạo là phiên **1 câu** dựa trên điểm thiếu được xác nhận.

## 5. Cách chạy cho người tiếp nhận

```powershell
uv sync --locked
agy models
.\run_demo.ps1
```

Đăng nhập `agy` trên máy chạy ứng dụng trước khi khởi động. Script xác nhận model và mở ứng dụng tại `http://127.0.0.1:8000/`. SQLite mặc định ở `.local/interview.sqlite3`. Nếu máy đã chạy bản cũ và cần seed C02 đã sửa, đặt đường dẫn mới trước khi chạy:

```powershell
$env:DATABASE_PATH = '.local/interview-demo-20261123.sqlite3'
.\run_demo.ps1
```

Không đưa khóa, dữ liệu bài làm hoặc file trong `.local/` lên Git. Không dùng fixture để kết luận chất lượng đánh giá AI.
