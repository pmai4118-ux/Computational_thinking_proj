# Kịch bản cài đặt và trình diễn ứng dụng (Q07)

Tài liệu này hướng dẫn chi tiết cách chuẩn bị môi trường, kiểm tra dữ liệu nguồn mở và chạy trọn vẹn buổi demo ứng dụng **interviewUS** (Backend Intern / Fresher — Tiếng Việt) mà không cần hỏi trực tiếp tác giả.

---

## 1. Chuẩn bị trước buổi demo (5 phút)

Chạy toàn bộ các lệnh dưới đây bằng PowerShell tại thư mục gốc repository:

```powershell
# 1. Đảm bảo môi trường Python 3.11 đã đồng bộ theo uv.lock
uv sync --locked

# 2. Tạo một file SQLite riêng cho buổi demo (nằm trong .local/, không đưa lên Git)
$env:DATABASE_PATH = ".local/interview-demo-live.sqlite3"

# 3. Kiểm tra và import ngân hàng câu hỏi & bài tập nguồn mở đã duyệt (C08)
uv run --locked python -m source.service.question_bank_service --database $env:DATABASE_PATH
```

**Kết quả kỳ vọng ở bước 3:**
- Mã thoát `0`, trường `"blocked": false`, `"issues": []`.
- `accepted` và `imported` hiển thị đủ **4 skills**, **8 questions** (4 nhóm × 2 biến thể), **8 rubrics**, **5 exercises**.

### Chọn chế độ chạy (Phân biệt rõ Live và Fixture)

#### Đường chạy chính — AI thật qua Antigravity CLI (`antigravity`)
```powershell
# Kiểm tra đăng nhập agy và xác nhận model gemini-3.8-flash-medium sẵn sàng
agy models

# Khởi động máy chủ demo (mặc định EVALUATION_PROVIDER=antigravity, GEMINI_MAX_RETRIES=0)
.\run_demo.ps1
```
- Mở `http://127.0.0.1:8000/health` → xác nhận `{"status":"ok","provider":"antigravity","demo_mode_label":null}`.
- Thời gian chấm AI thật thông thường khoảng **45–80 giây** mỗi câu (giới hạn cấu hình `ANTIGRAVITY_TIMEOUT_SECONDS=120`).

#### Đường chạy dự phòng — Ngoại tuyến xác định (`fixture`)
Chỉ dùng khi phòng trình chiếu mất mạng hoặc tài khoản `agy` hết quota. **Bắt buộc công bố rõ trên màn hình và lời nói đây là chế độ `Dữ liệu minh họa` để kiểm tra luồng phần mềm, không dùng để khẳng định chất lượng chấm của AI.**

```powershell
$env:EVALUATION_PROVIDER = "fixture"
$env:DATABASE_PATH = ".local/interview-demo-fixture.sqlite3"
uv run --locked uvicorn source.main:create_app --factory --host 127.0.0.1 --port 8000
```
- Mở `http://127.0.0.1:8000/health` → xác nhận `"provider":"fixture"` và `"demo_mode_label":"Dữ liệu minh họa"`.

> **Chuẩn bị trình duyệt:** Mở một cửa sổ ẩn danh (Incognito/InPrivate) tới `http://127.0.0.1:8000/` để bắt đầu với lịch sử rỗng và cookie sở hữu phiên ẩn danh mới (`interview_owner_id`).

---

## 2. Bộ câu trả lời tổng hợp dùng cho demo (Không dùng bài làm sinh viên thật)

Mở sẵn các tệp tổng hợp sau trong trình soạn thảo để dán nhanh khi trình diễn:

| Mục đích minh họa | Tệp câu trả lời tổng hợp | Kết quả mong muốn minh họa |
| --- | --- | --- |
| Câu trả lời đúng một phần (có điểm thiếu) | `test/fixtures/answers/ans_c02_02_partial.txt` (nhóm lập trình) hoặc `test/fixtures/answers/ans_c03_02_partial.txt` (nhóm tình huống) | Có tiêu chí `Đạt` và tiêu chí `Chưa đạt` → tạo điểm thiếu đã xác nhận để mở bài tập gợi ý ở bước 5. |
| Câu trả lời mơ hồ (`null` ≠ `0`) | `test/fixtures/answers/ans_c04_05_ambiguous.txt` | Minh họa `Chưa đủ bằng chứng` giữ `score: null` và không cộng điểm tổng bịa đặt. |
| Câu trả lời đầy đủ | `test/fixtures/answers/ans_c05_01_correct.txt` | Minh họa đối chiếu trích dẫn nguyên văn ở mức đạt. |

---

## 3. Kịch bản trình diễn từng bước (8–10 phút)

### Bước 1 — Trang bắt đầu (`/`) & Thiết lập phiên (`/setup`)
1. Chỉ rõ phạm vi MVP trên trang chủ: **Backend Developer · Intern / Fresher · Tiếng Việt**, cấu trúc cố định **4 câu hỏi** thuộc 4 nhóm (Kiến thức lập trình, Tình huống kỹ thuật, Giải thích thuật toán, Đánh giá mã nguồn), thời lượng ước tính 25–35 phút, **không thu thập CV hay thông tin cá nhân**.
2. Chỉ ra trạng thái lịch sử rỗng trên trình duyệt ẩn danh.
3. Bấm **Bắt đầu luyện tập** → kiểm tra trang `/setup` → bấm **Xác nhận bắt đầu**.
4. Nhấn mạnh: Server tự tạo cookie `HttpOnly` (`interview_owner_id`) gắn phiên ẩn danh và rút 4 câu hỏi đã qua review độc lập từ SQLite.

### Bước 2 — Không gian làm bài (`/sessions/{id}`) & Chấm điểm gắn căn cứ
1. Tại Câu 1/4, chỉ ra:
   - Thanh tiến độ gọn (`Câu 1 / 4` + thanh tiến độ + `0 câu đã có kết quả`).
   - Nhãn nguồn mở có giấy phép (`PSF-2.0`, `PostgreSQL`, `MIT`, `CC-BY-SA-4.0`) và liên kết truy xuất nguồn gốc.
   - Khối mã nguồn nền tối dễ đọc, không bị cắt ngang dòng dài.
   - Phân cấp rõ giữa nút chính **Gửi câu trả lời** và các nút phụ **Xem tổng kết phiên** / **Kết thúc sớm**.
2. Dán nội dung từ tệp tổng hợp phù hợp (ví dụ `test/fixtures/answers/ans_c02_02_partial.txt`) vào ô **Câu trả lời của bạn**.
   - Nhấn mạnh nhãn *"Bản nháp trên trình duyệt (chưa lưu máy chủ)"* (chưa báo đã lưu trước khi server xác nhận).
3. Bấm **Gửi câu trả lời**.
   - Giải thích luồng 2 bước tách biệt:
     1. `POST /api/sessions/{id}/answers` lưu nguyên văn câu trả lời vào SQLite với `client_submission_id` chống gửi trùng.
     2. `POST /api/answers/{id}/evaluate` gọi provider diễn giải tiêu chí → **E05** xác thực đủ tiêu chí và kiểm tra từng đoạn trích khớp chính xác chuỗi con nguyên văn → **E06** tính điểm bằng mã Python (AI không tự chấm điểm số) → **E09** lưu kết quả vào SQLite.

### Bước 3 — Trang đối chiếu tiêu chí & Căn cứ (`/sessions/{id}/review`)
1. Trên trang kết quả:
   - Bấm lần lượt từng tiêu chí ở cột trái để thấy đoạn trích nguyên văn được tô sáng tương ứng trong bài trả lời gốc ở cột phải.
   - Nêu rõ quy tắc: nếu có tiêu chí **Chưa đủ bằng chứng**, điểm tiêu chí là `Chưa xác định` (`null`) và **không bao giờ bị ép thành `0`**; tổng điểm câu cũng giữ trạng thái chưa tính thay vì cộng thiếu.
   - Nếu chạy bằng `ans_c04_05_ambiguous.txt` ở câu thuật toán, chỉ trực tiếp trạng thái này trên màn hình.
2. Bấm **Câu tiếp theo** để server chuyển sang Câu 2/4 (server kiểm soát thứ tự, không nhảy cách nếu bấm trùng).

### Bước 4 — Phục hồi lỗi provider & Bảo toàn bài làm (Không làm mất dữ liệu)
Có thể giải thích dựa trên bằng chứng kiểm thử đã xác minh trong `docs/DEMO_HANDOFF.md` hoặc demo trực tiếp bằng cách đặt tạm `$env:ANTIGRAVITY_TIMEOUT_SECONDS = "1"` ở phiên riêng:
1. Khi AI quá hạn chờ (`504 PROVIDER_TIMEOUT`, `retryable=true`), ứng dụng **giữ nguyên văn bản câu trả lời đã lưu trong SQLite**, không tạo điểm `0` và không gán nhãn người học thiếu năng lực.
2. Màn hình hiện thông báo lỗi rõ ràng cùng nút **Thử đánh giá lại** dùng lại đúng `answer_id` đã lưu.
3. Khi đánh giá đã `completed`, việc tải lại trang hoặc gọi lại endpoint đọc kết quả cũ từ SQLite, không gọi AI thêm lần nữa.

### Bước 5 — Hoàn tất / Kết thúc sớm, Tổng kết phiên (`/summary`) & Bài tập (`/exercises`)
1. Tiếp tục trả lời đủ 4/4 câu **hoặc** bấm **Kết thúc sớm** → **Xác nhận kết thúc** để mở trang `/sessions/{id}/summary`.
2. Trên trang Tổng kết:
   - Chỉ ra độ phủ (`Có kết quả X / 4 câu`), danh sách nhóm **Câu chưa làm**, **Câu chưa đủ căn cứ**, kết quả từng câu và mục **Điểm cần luyện tiếp**.
   - Nhấn mạnh ứng dụng **không bịa ra một điểm năng lực tổng hợp** từ các câu khác rubric hay từ câu chưa làm.
3. Bấm **Xem bài tập** (hoặc **Bài luyện liên quan**) để mở `/sessions/{id}/exercises`:
   - Chỉ ra mục **Vì sao bài này phù hợp** gắn đúng điểm thiếu đã xác nhận, **Bài cần học trước** (tiên quyết), **Thời lượng ước tính** và **Nguồn nội dung** có giấy phép.
   - Bấm **Xem hướng dẫn bài tập** để tải hướng dẫn đã kiểm duyệt.
   - Bấm **Luyện lại với câu hỏi khác** (`I06`): hệ thống tạo phiên luyện mới **1/1 câu** dùng biến thể đã duyệt khác với câu gốc đã làm. (Nếu hết biến thể hoặc không có bài khớp, giao diện báo rõ thay vì tự bịa bài.)

---

## 4. Điểm nhấn Tư duy tính toán (Computational Thinking) & Giới hạn cần nêu rõ

- **Phân rã (Decomposition):** Tách rạch ròi theo kiến trúc **MVC-S** (`View → Control → service → Model`), tách lưu bài khỏi bước đánh giá AI, tách diễn giải ngôn ngữ (AI) khỏi xác thực bằng chứng (`E05`) và tính điểm (`E06`).
- **Nhận diện mẫu (Pattern Recognition):** Chuẩn hóa 4 dạng câu hỏi, 3 trạng thái tiêu chí (`met`, `unmet`, `insufficient_evidence`), các trạng thái phục hồi lỗi (`loading`, `empty`, `invalid_input`, `timeout`, `retry`, `expired`).
- **Trừu tượng hóa & Thuật toán (Abstraction & Algorithms):** Phiên bản hóa bất biến cho Question/Rubric/Answer/Evaluation; kiểm chứng chỉ số ký tự Unicode (`answer.text[start:end]`); sắp xếp tiên quyết cho bài tập (`I06`).
- **Giới hạn hiện tại (nêu trung thực khi trình bày):**
  - Phạm vi hiện hỗ trợ **Backend Developer · Intern/Fresher · Tiếng Việt** với phiên cố định 4 câu (8 câu hỏi nguồn mở đã duyệt, 5 bài tập).
  - Bộ 24 câu trả lời tổng hợp `C07` hiện mới có nhãn nháp (`candidate_judgment`), chưa hoàn tất 2 lượt gán nhãn độc lập & phân xử nên chưa báo cáo tỷ lệ đồng thuận `Q03`.
  - Điểm chấm trong buổi demo chứng minh luồng kỹ thuật hoạt động; không phải đánh giá năng lực tuyển dụng toàn diện.

---

## 5. Ràng buộc bảo mật trước khi bàn giao / thuyết trình

- Chạy `git status --short` để xác nhận **không** có file trong `.local/`, `.env`, `*.sqlite3` hay khóa API nào bị theo dõi.
- Không mở file `.env` cá nhân hay in `$env:GEMINI_API_KEY` trên màn hình chia sẻ.
- Nếu chuyển sang chế độ `fixture`, phải giữ nguyên huy hiệu **Dữ liệu minh họa** trên thanh tiêu đề.

---

## 6. Clean-Machine Verification Checklist (Q07 Step 3)

> [!NOTE]
> **Trạng thái bước 3 của Q07: Chờ một thành viên khác thực hiện trên checkout sạch.** Không tự đánh dấu đạt trước khi có người khác tự chạy theo `README.md` và tài liệu này mà không cần hỏi tác giả.

| Hạng mục kiểm tra từ checkout sạch | Trạng thái | Người thực hiện (Ẩn danh / Vai trò) | Ghi chú điểm còn thiếu / cần sửa |
| --- | --- | --- | --- |
| `uv python install 3.11` & `uv sync --locked` & `uv pip check` | Chờ kiểm tra | — | — |
| `uv run --locked python -m pytest -q` (không cần khóa API) | Chờ kiểm tra | — | — |
| Import seed `question_bank_service --database .local/interview-clean.sqlite3` | Chờ kiểm tra | — | — |
| Chạy chế độ `fixture`, xác nhận huy hiệu `Dữ liệu minh họa` và đi trọn luồng | Chờ kiểm tra | — | — |
| Chạy chế độ live `antigravity` qua `.\run_demo.ps1` (hoặc `gemini` với khóa cá nhân) | Chờ kiểm tra | — | — |
| Kiểm tra `git status` không phát sinh khóa/DB bị track | Chờ kiểm tra | — | — |