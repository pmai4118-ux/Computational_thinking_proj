# Quy trình làm việc nhóm, Quản lý nhánh và Nghiệm thu (P08)

| Thuộc tính | Nội dung |
| --- | --- |
| Mã công việc | P08 — Thống nhất cách làm việc và review |
| Người thực hiện | hwngMP (`member-1`, Leader) · Reviewer: Tin (`member-6`, Reviewer) |
| Phụ thuộc | [P04 (`api_contract.md`)](api_contract.md), [P01 (`scope.md`)](scope.md), [`AGENTS.md`](../AGENTS.md) |
| Đầu ra | `docs/team_workflow.md`, [`docs/api_contract.md`](api_contract.md) |

---

## 1. Quy ước nhánh, Commit và Pull Request

1. **Cách đặt tên nhánh (Branch Naming):**
   - Mỗi công việc trong backlog (`TASK_BREAKDOWN.md`) thực hiện trên một nhánh ngắn hạn tách từ `main`:
     - Cú pháp: `<prefix>/<task-id-lowercase>-<short-slug>` (ví dụ: `codex/p04-api-contract`, `feat/f02-domain-models`, `content/c02-programming-questions`).
   - Không gộp nhiều công việc khác tầng MVC-S vào cùng một PR trừ các task nội dung liền kề nhỏ (`C02–C05`).
2. **Định dạng thông điệp Commit (Bắt buộc theo `AGENTS.md`):**
   - Cú pháp: `[T...] <short description>` (có **đúng một dấu cách** sau dấu ngoặc vuông đóng `]`, thay `T...` bằng mã công việc thực tế).
   - Ví dụ hợp lệ:
     - `[P04] Add session API contract schemas and fixtures`
     - `[F02] Add interview domain models`
     - `[C02] Curate two programming-knowledge questions with reviewed rubrics`
3. **Quy trình 1 người thực hiện — 1 người review độc lập:**
   - Không tự merge PR của chính mình khi chưa có thành viên khác kiểm tra.
   - Với các công việc nội dung và rubric (`P05`, `C02–C07`), người duyệt (`reviewer_id`) bắt buộc khác người biên soạn (`curator_id`) và phải chạy/đối chiếu các ca kiểm định độc lập.

---

## 2. Phân công thực hiện và Reviewer cho các công việc đang mở / đã nhận

Bảng dưới đây ghi rõ đầu ra, người thực hiện (`owner`) và người review (`reviewer`) cho từng công việc đã nhận trong Tuần 1–2 để không có task nào thiếu người thẩm định:

| Mã việc | Tên công việc | Đầu ra chính (`output`) | Người nhận (`owner`) | Người duyệt (`reviewer`) | Trạng thái hợp đồng |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P01** | Chốt phạm vi, vai trò và cấp độ | `docs/scope.md`, `docs/PROJECT_PLAN.md` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Đã chốt baseline |
| **P02** | Vẽ luồng người dùng và phục hồi lỗi | `docs/user_flow.md`, `docs/diagrams/p02-user-flow.svg` | `Qthynhh` (`member-2`) | `hwngMP` (`member-1`) | Đã khớp W01–W08 với P04 |
| **P03** | Định nghĩa dữ liệu, mã và phiên bản | `docs/data_contract.md`, `source/Model/{ids,question,evaluation}.py` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Đã có model & ví dụ |
| **P04** | Thống nhất API và dữ liệu mẫu | `docs/api_contract.md`, `source/Control/schemas.py`, `test/fixtures/api/` | `hwngMP` (`member-1`) | `Qthynhh` (`member-2`) | Đã có fixture & DTO |
| **P05** | Viết một case và rubric hoàn chỉnh | `data/seed/questions/cases.json`, `docs/rubric_guide.md`, `test/fixtures/question_reviews/p05.json` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Đã duyệt 4 ca chuẩn |
| **P06** | Chốt wireframe và bộ quy chuẩn UI | `docs/ui_direction.md`, `source/view/static/css/tokens.css` | `hwngMP` (`member-1`) | `Qthynhh` (`member-2`) | Đã có wireframe & CSS tokens |
| **P07** | Khảo sát Gemini, SDK, quota và ngân sách | `docs/ai_decision.md`, `.env.example`, `source/service/providers/gemini_provider.py` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Đã có adapter & test |
| **P08** | Thống nhất cách làm việc và review | `docs/team_workflow.md`, `docs/api_contract.md` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Hoàn tất quy trình |
| **F01** | Thiết lập dự án và phụ thuộc Python | `pyproject.toml`, `uv.lock`, `README.md`, `test/conftest.py` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Đã khóa môi trường 3.11 |
| **F02** | Xây các kiểu dữ liệu miền | `source/Model/{question,interview,evaluation,exercise}.py` | `Qthynhh` (`member-2`) | `hwngMP` (`member-1`) | Sẵn sàng theo P03/P04 |
| **F03** | Định nghĩa interface repository | `source/Model/repositories/interfaces.py`, `test/fixtures/repositories.py` | `Qthynhh` (`member-2`) | `hwngMP` (`member-1`) | Phụ thuộc F02 |
| **F04** | Tạo schema và lưu trữ SQLite | `source/Model/repositories/{schema.sql,sqlite_repository.py}` | `Qthynhh` (`member-2`) | `hwngMP` (`member-1`) | Phụ thuộc F03 |
| **F06** | Cấu hình biến môi trường và dữ liệu riêng | `.env.example`, `.gitignore`, `source/config.py`, `test/test_config.py` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Đã kiểm tra git ignore |
| **C01** | Định nghĩa skill ID và khung phiên | `data/seed/{skills,session_blueprints}.json`, `docs/content_guide.md` | `hwngMP` (`member-1`) | `Tin` (`member-6`) | Đã có test coverage |
| **C02** | Kiếm các câu hỏi kiến thức lập trình | `data/seed/questions/programming.json`, `test/fixtures/question_reviews/c02.json` | `nkphuc` (`member-5`) | `Tin` (`member-6`) | Dùng skill ID của C01 |
| **C03** | Kiếm các câu hỏi tình huống kỹ thuật | `data/seed/questions/cases.json`, `test/fixtures/question_reviews/c03.json` | `nguyentrg` (`member-3`) | `Tin` (`member-6`) | Mở rộng từ mẫu P05 |
| **C04** | Kiếm các câu hỏi giải thích thuật toán | `data/seed/questions/algorithms.json`, `test/fixtures/question_reviews/c04.json` | `nkphuc` (`member-5`) | `Tin` (`member-6`) | Dùng skill ID của C01 |
| **C05** | Kiếm các câu hỏi đánh giá code AI | `data/seed/questions/ai_review.json`, `test/fixtures/question_reviews/c05.json` | `nguyentrg` (`member-3`) | `Tin` (`member-6`) | Dùng skill ID của C01 |
| **C07** | Chuẩn bị 24 câu trả lời kiểm định | `test/fixtures/answers/`, `test/fixtures/expected_evaluations.json`, `docs/evaluation_protocol.md` | `nguyentrg` (`member-3`) & `anh khoa` (`member-4`) | `Tin` (`member-6`) | Tách rõ calibration / held-out |

---

## 3. Mẫu Ticket và Báo cáo Bàn giao PR (PR Handoff Template)

Mọi PR gửi lên phải điền đầy đủ khung thông tin sau (tương ứng với kỹ năng `$ct-task-workflow`):

```markdown
## [<Mã task>] <Tiêu đề ngắn gọn>

- **Người thực hiện (Implementer):** <tên thành viên>
- **Người duyệt (Reviewer):** <tên thành viên khác>
- **Phụ thuộc đầu vào (Dependencies):** <danh sách mã task đã kiểm tra trong working tree>
- **Tầng MVC-S và File thay đổi:**
  - `Model` / `View` / `Control` / `Service` / `Docs` / `QA`: <liệt kê đường dẫn file>

### 1. Tóm tắt thay đổi và tác động hợp đồng
- Nêu rõ các hàm/lớp/tài liệu đã thêm hoặc cập nhật.
- Nếu có điều chỉnh hợp đồng dùng chung (`docs/data_contract.md`, `docs/api_contract.md`, `data/seed/skills.json`), liệt kê các fixture đã cập nhật đồng thời.

### 2. Lệnh kiểm tra và Bằng chứng nghiệm thu (Acceptance Evidence)
- Lệnh đã chạy:
  ```powershell
  uv run --locked python -m pytest <đường_dẫn_test>
  ```
- Kết quả quan sát được (số test pass, kịch bản thành công và kịch bản lỗi đã kiểm chứng).
- Phân biệt rõ kiểm tra đơn vị cô lập (isolated unit/fixture check) với kiểm tra qua điểm vào ứng dụng (`source/main.py`).

### 3. Giới hạn còn lại và Công việc được mở khóa (Unblocked Tasks)
- Các giới hạn chưa thực hiện trong phạm vi task này.
- Các task tiếp theo có thể bắt đầu ngay sau khi PR này được merge.
```

---

## 4. Lịch tích hợp ngắn và Quy tắc đồng bộ Hợp đồng + Fixture

1. **Tích hợp theo lát cắt dọc (Short Integration Cadence):**
   - Nhóm tích hợp code vào `main` theo từng chặng ngắn (1–2 ngày/lần) thay vì đợi cuối tuần.
   - Bất kỳ thay đổi nào trên [`source/Control/schemas.py`](../source/Control/schemas.py) hoặc [`docs/api_contract.md`](api_contract.md) **bắt buộc** cập nhật đồng thời các tệp JSON trong [`test/fixtures/api/`](../test/fixtures/api/) và chạy pass `test/test_api_contract.py` trong cùng một PR.
2. **Bảo vệ ranh giới kiến trúc MVC-S:**
   - `source/Model/` không được import `View`, `Control` hoặc `service`.
   - `source/service/` không được import `View` hoặc `Control`.
   - `source/Control/` không phụ thuộc vào template/component cụ thể của `View` và không viết truy vấn SQL hay gọi mạng trực tiếp.
   - `source/view/` chỉ hiển thị dữ liệu từ DTO của Controller, không tự tính điểm rubric hoặc tự biến `score: null` thành `0`.

---

## 5. Định nghĩa Hoàn thành (Definition of Done)

Một công việc chỉ được chuyển từ `doing` sang `done` trên bảng việc khi thỏa mãn đủ **6 điều kiện**:

1. **Đúng tầng MVC-S:** Tất cả file nằm đúng thư mục quy định trong `AGENTS.md` và không vi phạm chiều phụ thuộc.
2. **Đủ cả kịch bản thuận và kịch bản lỗi:** Có kiểm thử tự động (hoặc biên bản walkthrough đối với tài liệu) cho luồng chính và các trường hợp lỗi biên (`null` vs `0`, gửi trùng `client_submission_id`, timeout provider, thiếu quyền phiên).
3. **Bảo toàn ngữ nghĩa dữ liệu và bản quyền:** Giữ nguyên câu trả lời gốc của người học; chỉ import câu hỏi có nguồn mở đã xác minh giấy phép và `review.status == "approved"` bởi người duyệt độc lập.
4. **Tái lập được trên máy thành viên khác:** Lệnh `uv run --locked python -m pytest` chạy pass mà không cần cấu hình ngầm hay khóa API cá nhân.
5. **Đồng bộ tài liệu — schema — fixture:** Không để tài liệu hợp đồng lệch với code hoặc fixture kiểm thử.
6. **Có xác nhận của Reviewer:** Đã gán tên `reviewer` và ghi nhận kết quả kiểm tra vào `notes` hoặc PR.
