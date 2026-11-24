# Kế hoạch Thực hiện Nhiệm vụ Q02 (Sprint Backlog P0)
# Kiểm tra repository và API (Add repository and API workflow checks with mocked provider)

- **Mã nhiệm vụ:** `[Q02]` (Tuần 3 · Kiểm tra & bàn giao)
- **Độ ưu tiên:** `P0` (Bắt buộc cho Release Gate & MVP)
- **Người thực hiện:** `anh khoa`
- **Các tầng kiến trúc liên quan (MVC-S):**
  - **Model (M):** `source/Model/repositories/sqlite_repository.py`, `interfaces.py`, schema SQLite và domain models (`interview.py`, `evaluation.py`, `question.py`, `exercise.py`).
  - **Service (S):** `source/service/interview_service.py`, `evaluation_service.py`, `recommendation_service.py`, `providers/fixture_provider.py`.
  - **Controller (C):** `source/Control/interview_controller.py`, `evaluation_controller.py`, `saved_evaluation_controller.py`, `session_summary_controller.py`, `exercise_controller.py`, `schemas.py`.
  - **QA / Test (T):** `test/Model/test_repository.py`, `test/Control/test_interview_flow.py` (tạo mới), `test/fixtures/`.
- **Nhiệm vụ cần xong trước (Dependencies):**
  - `I04` — Tạo API đánh giá, đọc kết quả và retry (đã hoàn thành).
  - `I05` — Chuyển câu và tổng kết phiên (đã hoàn thành).
  - `I06` — Đề xuất bài tập từ điểm thiếu đã xác nhận (đã hoàn thành).
- **Nhiệm vụ kế thừa mở khóa:**
  - `Q06` — Sửa lỗi release-blocking và chạy lại kiểm thử bị ảnh hưởng.
  - `Q07` — Viết tài liệu cài đặt, cấu hình và kịch bản demo (`docs/demo_script.md`).
  - `Q08` — Đóng băng bản phát hành, tổng duyệt kịch bản và báo cáo bằng chứng CT.

---

## 1. Mục tiêu & Tiêu chí nghiệm thu (Acceptance Criteria)

Theo mô tả task `Q02` và quy chuẩn trong `AGENTS.md`, `docs/TASK_BREAKDOWN.md`, `docs/TASK_INSTRUCTIONS.md`:

### Mục tiêu cốt lõi:
1. **Thiết lập DB tạm và Mock Provider biệt lập:**
   - Mọi kiểm thử phải chạy trên cơ sở dữ liệu SQLite tạm thời thông qua fixture `tmp_path`. Tuyệt đối không đọc/ghi hoặc làm biến đổi DB thật tại `.local/interview.sqlite3`.
   - Sử dụng Mock Provider / Fixture Provider ngoại tuyến (không gọi API mạng, không tốn quota, không yêu cầu API key hay đăng nhập CLI).
2. **Kiểm tra quyền sở hữu và ranh giới bảo mật (Ownership & Access Control):**
   - Phiên phỏng vấn được gắn với token ẩn danh qua cookie `interview_session_owner` (`HttpOnly`, `SameSite=Lax`).
   - Mọi hành vi truy cập trái phép từ bên thứ ba (không có cookie hoặc dùng cookie của phiên khác) đều bị chặn ở mức 403 `SESSION_FORBIDDEN`.
   - ID phiên không tồn tại phải trả về đúng 404 `SESSION_NOT_FOUND`.
3. **Kiểm tra trạng thái, thứ tự và tính lũy kế (State Transitions & Sequence):**
   - Kiểm tra tuần tự nghiêm ngặt do máy chủ quản lý: không thể nhảy câu hỏi (`/next`) khi chưa nộp bài hoặc chưa hoàn tất đánh giá câu hiện tại (trả về 409 `INVALID_STATE_TRANSITION`).
   - Replay bước `/next` với cùng index phải có tính lũy kế (idempotent), không nhảy cóc qua câu kế tiếp.
   - Khi phiên kết thúc (`completed` hoặc `ended_early`), chặn mọi hành vi nộp bài tiếp theo hoặc chuyển câu (409 `INVALID_STATE_TRANSITION`).
4. **Kiểm tra chống trùng lặp và Retry đồng thời (Idempotency & Concurrent Retries):**
   - Gửi trùng câu trả lời với cùng `client_submission_id` và cùng nội dung văn bản: trả về bản ghi cũ với cờ `replayed=True`, không tạo dòng mới trong database.
   - Gửi trùng `client_submission_id` nhưng nội dung văn bản bị sửa đổi: bắn lỗi xung đột 409 `SUBMISSION_CONFLICT`.
   - Khi một đánh giá đang xử lý (`processing`), các request đánh giá đồng thời phải nhận 409 `EVALUATION_IN_PROGRESS` với `retryable=true`.
   - Đánh giá lại một câu đã hoàn tất (`completed`): trả về kết quả đã lưu trong SQLite mà không gọi lại provider.
5. **Kiểm tra lỗi giữa chừng và Rollback giao dịch (Mid-transaction Rollback):**
   - Mô phỏng sự cố database / vi phạm ràng buộc khóa ngoại / lỗi provider giữa chừng: giao dịch phải rollback sạch sẽ, không để lại bản ghi rác (orphan checks hoặc partial evaluations).
   - Nội dung câu trả lời gốc của học viên luôn được bảo toàn nguyên vẹn sau lỗi.
6. **Thực hiện luồng hoàn chỉnh liên tầng (End-to-End Golden Flow):**
   - Đi hết luồng: `Mở phiên (Setup/Create) -> Gửi bài (Submit) -> Đánh giá (Evaluate) -> Chuyển câu (Next) -> Tổng kết (Summary) -> Đề xuất & Luyện tập lại bài tập (Exercise & Practice)`.
   - Không bịa điểm tổng (tuân thủ quy tắc scoring Python-only, không gán 0 cho tiêu chí thiếu căn cứ).
   - Sau khi test chạy xong, toàn bộ file tạm thời trong `tmp_path` được dọn dẹp sạch sẽ.

---

## 2. Kế thừa từ các phần việc đã hoàn thành (Reused Assets)

Dựa trên kết quả tổng hợp từ `project_summary.md` và mã nguồn hiện tại của nhánh `Demo`:

| Thành phần đã có | Vị trí file | Cách thức tái sử dụng cho Q02 |
|---|---|---|
| **App Factory & Composition Root** | `source/main.py` (`create_app`) | Dùng trực tiếp `create_app(settings=...)` để khởi tạo ứng dụng FastAPI đầy đủ các route cho integration test, cắm database tạm và mock provider qua DI container. |
| **Cấu hình môi trường** | `source/config.py` (`Settings`, `load_settings`) | Nạp settings với `provider="fixture"` và `database_path=tmp_path / "..."`. |
| **SQLite Repository Store** | `source/Model/repositories/sqlite_repository.py` | Kiểm thử tầng lưu trữ: schema constraints, foreign keys, transaction rollback, ACID. |
| **Seed Catalog Loader** | `source/service/seed_loader.py` | Nạp 8 câu hỏi đã duyệt (C02–C05) và 5 bài tập (C06) vào DB tạm để chạy luồng thực tế. |
| **Deterministic Fixture Provider** | `source/service/providers/fixture_provider.py` | Tạo mock provider offline trả về `InterpretationBatch` chuẩn với nhãn `"Dữ liệu minh họa"`, hỗ trợ mô phỏng timeout/error. |
| **Các DTO chuẩn contract** | `source/Control/schemas.py` | Validate cấu trúc response từ API (SessionViewDTO, EvaluationResponseDTO, SessionSummaryReportDTO, ExerciseRecommendationsResponse). |
| **Các Unit Test đã có** | `test/Model/test_repository.py` | Đã có 3 test cơ bản (F04). Cần giữ nguyên và bổ sung thêm các case rollback, transaction lock và cleanup cho Q02. |
| **Test controllers riêng lẻ** | `test/Control/test_sessions.py`, `test_evaluations.py`, `test_session_summary.py` | Tái sử dụng các pattern helper (tạo session, set cookie, barrier threading) để dựng file tổng hợp luồng `test_interview_flow.py`. |

---

## 3. Ma trận Kịch bản Kiểm thử chi tiết (Test Scenario Matrix)

### Nhóm A: Kiểm thử Tầng Repository & Transaction (`test/Model/test_repository.py`)

| Mã test | Tên kịch bản | Thao tác / Dữ liệu đầu vào | Kết quả mong đợi (Assertion) |
|---|---|---|---|
| **A1** | *Reopen & Verbatim Preservation* (Đã có) | Lưu session, answer có ký tự đặc biệt, evaluation vào SQLite, đóng kết nối và mở lại bằng instance mới. | Dữ liệu nạp lại khớp 100% nguyên văn, evaluation versioned được giữ nguyên. |
| **A2** | *Idempotent Submit & Rollback* (Đã có) | Gửi trùng `client_submission_id`, gửi xung đột text, cố tình lưu evaluation với `answer_ref` không tồn tại. | Gửi trùng trả về bản ghi cũ; text khác bắn lỗi xung đột; evaluation thiếu FK bị rollback toàn bộ, không có dòng rác nào trong `evaluation_criterion_checks`. |
| **A3** | *Concurrent Submissions* (Đã có) | Hai luồng gửi đồng thời cùng `client_submission_id` qua `ThreadPoolExecutor` và `Barrier(2)`. | Đúng 1 luồng lưu mới (`replayed=False`), 1 luồng nhận replayed (`replayed=True`), DB chỉ có 1 bản ghi duy nhất. |
| **A4** (Bổ sung) | *Session State Transition Integrity* | Cập nhật trạng thái session từ `in_progress` -> `completed` và `ended_early` trong repository; cố ghi đè trạng thái không hợp lệ. | Trạng thái được cập nhật an toàn, không làm mất danh sách `question_refs` và `answer_refs`. |
| **A5** (Bổ sung) | *Foreign Key Cascade & Rollback on Check Failure* | Giả lập lỗi giữa chừng khi đang lưu danh sách `CriterionCheck` (chèn 1 check hợp lệ, check thứ 2 vi phạm constraint). | Transaction rollback toàn bộ; bảng `evaluations` và `evaluation_criterion_checks` không tồn tại bất kỳ dòng nào của lượt đánh giá lỗi. |
| **A6** (Bổ sung) | *Isolation from Production DB* | Chạy toàn bộ suite với `tmp_path`. | File `.local/interview.sqlite3` không bị tạo mới hoặc sửa đổi timestamp. |

---

### Nhóm B: Kiểm thử Quyền sở hữu & Lỗi trạng thái API (`test/Control/test_interview_flow.py`)

| Mã test | Tên kịch bản | Thao tác / Dữ liệu đầu vào | Kết quả mong đợi (Assertion) |
|---|---|---|---|
| **B1** | *Anonymous Cookie Ownership Enforcement* | Client A tạo session (nhận cookie `interview_session_owner`). Client B (không cookie) hoặc Client C (cookie khác) cố: đọc session, nộp bài, đánh giá, chuyển câu, kết thúc phiên, đọc summary, đọc bài tập. | Toàn bộ request từ B và C trả về `403 Forbidden` (`error_code="SESSION_FORBIDDEN"`). Client A truy cập thành công 200/201. |
| **B2** | *Non-existent & Invalid Resource IDs* | Gọi API với `session_id`, `answer_id`, `exercise_id` không tồn tại. | Trả về `404 Not Found` (`SESSION_NOT_FOUND`, `ANSWER_NOT_FOUND`, `EXERCISE_NOT_FOUND`), không bao giờ văng 500. |
| **B3** | *Strict Sequence Enforcement* | Client A vừa tạo session, chưa nộp bài câu 0 mà gọi ngay `POST /api/sessions/{id}/next`. | Trả về `409 Conflict` (`error_code="INVALID_STATE_TRANSITION"`). |
| **B4** | *Premature Advance without Completed Evaluation* | Đã nộp bài câu 0, nhưng chưa gọi đánh giá (hoặc đánh giá đang `processing`/`failed`) mà gọi `/next`. | Trả về `409 Conflict` (`INVALID_STATE_TRANSITION`), yêu cầu hoàn tất đánh giá trước khi chuyển câu. |
| **B5** | *Submitting to Completed or Ended Session* | Kết thúc phiên sớm (`/end`) hoặc hoàn tất cả 4 câu, sau đó cố nộp thêm bài mới qua `/answers`. | Trả về `409 Conflict` (`INVALID_STATE_TRANSITION`), bảo toàn dữ liệu phiên đã đóng. |

---

### Nhóm C: Kiểm thử Gửi trùng, Retry đồng thời & Phục hồi lỗi Provider (`test/Control/test_interview_flow.py`)

| Mã test | Tên kịch bản | Thao tác / Dữ liệu đầu vào | Kết quả mong đợi (Assertion) |
|---|---|---|---|
| **C1** | *Duplicate Answer Submit via API* | Gọi `POST /api/sessions/{id}/answers` 2 lần liên tiếp với cùng `client_submission_id` và cùng `text`. | Lần 1: 201 Created. Lần 2: 201 Created (hoặc 200) với nội dung y hệt, cùng `answer_id`, DB chỉ lưu 1 bản ghi duy nhất. |
| **C2** | *Conflicting Answer Submit via API* | Gọi `POST /api/sessions/{id}/answers` với cùng `client_submission_id` nhưng thay đổi nội dung `text`. | Trả về `409 Conflict` (`error_code="SUBMISSION_CONFLICT"`), câu trả lời cũ trong DB không bị thay đổi. |
| **C3** | *Concurrent Evaluation Lock (EVALUATION_IN_PROGRESS)* | Tạo mock provider bị chặn (`BlockingInterpreter`). 2 luồng đồng thời gọi `POST /api/answers/{id}/evaluate`. | Luồng 1 bắt đầu xử lý, luồng 2 nhận `409 Conflict` (`error_code="EVALUATION_IN_PROGRESS"`, `retryable=true`). Đọc trạng thái qua GET trả về `status="processing"`, `total_score=null`. |
| **C4** | *Provider Timeout Recovery & Retry* | Mock provider ném `ProviderFailureError(TIMEOUT)` ở lần gọi đầu, trả kết quả ở lần gọi sau. | Lần 1 trả về `504 Gateway Timeout` (`error_code="PROVIDER_TIMEOUT"`, `retryable=true`). Câu trả lời gốc vẫn lưu nguyên vẹn trong DB. Lần 2 retry thành công 200 OK (`status="completed"`). |
| **C5** | *Evaluation Idempotence / Cached Result* | Gọi `POST /api/answers/{id}/evaluate` khi đã có kết quả `completed`. | Trả về ngay kết quả đã lưu (200 OK), mock provider không bị gọi thêm lần nào (call count = 1). |

---

### Nhóm D: Kiểm thử Luồng Hoàn chỉnh 4 câu + Đề xuất Bài tập (`test/Control/test_interview_flow.py`)

| Bước trong luồng | Thao tác API | Dữ liệu kiểm tra (Assertion) |
|---|---|---|
| **D1: Mở phiên** | `POST /api/sessions` `{role: "backend_developer", level: "intern_fresher", language: "vi"}` | HTTP 201. Cookie `interview_session_owner` được thiết lập. `current_index == 0`, `total_questions == 4`. `current_question` là câu 1 (C02). |
| **D2: Vòng lặp 4 câu** (Câu 1 -> 4) | - `GET /api/sessions/{id}` lấy câu hiện tại.<br>- `POST /api/sessions/{id}/answers` gửi bài.<br>- `POST /api/answers/{aid}/evaluate` chấm điểm.<br>- `POST /api/sessions/{id}/next` chuyển câu. | - Mỗi câu nộp với `client_submission_id` riêng biệt.<br>- Điểm và căn cứ (evidence quote) được tính toán đúng (Python-only).<br>- `current_index` tăng tuần tự từ 0 -> 1 -> 2 -> 3 -> 4.<br>- Chuyển câu lặp lại (replay cùng index) không làm nhảy cóc. |
| **D3: Hoàn tất phiên** | Sau câu thứ 4, gọi `/next` với `from_question_index=3`. | HTTP 200. Session state chuyển sang `"completed"`. `current_question` là `None`. |
| **D4: Tổng kết phiên** | `GET /api/sessions/{id}/summary` | HTTP 200. `completed_question_count == 4`. `unanswered_categories == []`. `outcomes` đủ 4 kết quả. Không tồn tại trường điểm tổng bịa đặt (`total_score` không xuất hiện ở summary cấp cao). |
| **D5: Lấy đề xuất bài tập** | `GET /api/sessions/{id}/exercises` | HTTP 200. Danh sách `recommendations` chứa các bài tập khớp với điểm thiếu (gaps) được ghi nhận trong phiên. Mỗi bài tập có `source` với license SPDX rõ ràng. |
| **D6: Luyện tập lại có chủ đích** | `POST /api/sessions/{id}/answers/{aid}/practice` với `exercise_id` và `criterion_id` thiếu. | HTTP 201. Tạo thành công một phiên luyện tập mới với câu hỏi thay thế cùng kỹ năng. Phiên mới có ID và tiến độ độc lập. |

---

## 4. Thiết kế Kỹ thuật Chi tiết & Cấu trúc File

### 4.1. File `test/Control/test_interview_flow.py` (File cốt lõi cần tạo mới)
File này sẽ là integration test suite toàn diện, tích hợp toàn bộ router của FastAPI qua `create_app` và sử dụng `TestClient`.

Cấu trúc các hàm test dự kiến:
```python
# test/Control/test_interview_flow.py

class TestInterviewWorkflowIntegration:
    """End-to-end integration and boundary tests for Task Q02."""

    # 1. Setup & Factory Fixture
    @pytest.fixture
    def test_env(self, tmp_path: Path):
        """Build an isolated FastAPI instance backed by SQLite in tmp_path with a Mock FixtureProvider."""
        ...

    # 2. Q02 Step 2: Ownership, Authorization & ID boundaries
    def test_q02_session_ownership_and_forbidden_stranger_access(self, test_env):
        """Stranger client without owner cookie receives 403 on all session mutating/reading endpoints."""
        ...

    def test_q02_resource_not_found_handling(self, test_env):
        """Non-existent sessions, answers, and exercises return standard 404 ApiErrorResponse."""
        ...

    # 3. Q02 Step 2: State sequence, duplicate submit & idempotent transitions
    def test_q02_strict_question_sequence_and_idempotent_next(self, test_env):
        """Cannot skip questions or advance without evaluation; replaying next is idempotent."""
        ...

    def test_q02_duplicate_submission_and_conflict_handling(self, test_env):
        """Identical submission ID returns existing answer; differing text triggers 409 conflict."""
        ...

    def test_q02_concurrent_evaluation_and_timeout_retry(self, test_env):
        """Simultaneous evaluations return 409 EVALUATION_IN_PROGRESS; timeout preserves answer and allows clean retry."""
        ...

    # 4. Q02 Step 3: Complete Golden Flow (Mở phiên -> Nộp bài -> Chấm -> Next -> Summary -> Bài tập)
    def test_q02_full_four_question_interview_flow_to_exercise_practice(self, test_env):
        """Complete 4-question interview session followed by summary verification, exercise recommendations, and targeted retry."""
        ...

    # 5. Q02 Early Termination Flow
    def test_q02_early_session_termination_preserves_records_and_disables_advancing(self, test_env):
        """Ending early marks session ended_early, preserves answered items, and rejects subsequent submissions."""
        ...
```

### 4.2. File `test/Model/test_repository.py` (Cập nhật và hoàn thiện)
Bổ sung các test case cấp độ repository để đảm bảo tính toàn vẹn của ACID và schema:
- `test_q02_repository_session_state_transitions_and_history_invariants`:
  - Kiểm tra việc chuyển đổi `SessionState` từ `IN_PROGRESS` sang `COMPLETED` và `ENDED_EARLY`.
  - Đảm bảo danh sách `question_refs` và `answer_refs` không bị mất mát hay xáo trộn.
- `test_q02_repository_transaction_rollback_on_failed_evaluation_checks`:
  - Giả lập lỗi ghi đè dữ liệu hoặc ngoại lệ giữa chừng khi chèn các dòng `CriterionCheck`.
  - Xác nhận bằng câu lệnh SQL raw: `SELECT COUNT(*) FROM evaluation_criterion_checks` bằng 0 khi transaction thất bại.
- `test_q02_test_environment_cleanup_guarantee`:
  - Đảm bảo cơ sở dữ liệu tạm thời được đóng và giải phóng tài nguyên đúng cách, không lưu lại lock file hay làm rò rỉ kết nối trên Windows (`sqlite3.OperationalError: database is locked`).

### 4.3. Thư mục `test/fixtures/` (Hoàn thiện các mock helper nếu cần)
- Đảm bảo `test/fixtures/repositories.py` và mock providers có đủ các helper:
  - `BlockingInterpreter`: Phục vụ kiểm tra khóa đồng thời (`EVALUATION_IN_PROGRESS`).
  - `FlakyInterpreter`: Phục vụ kiểm tra lỗi timeout có thể thử lại (`PROVIDER_TIMEOUT`, `retryable=true`).
  - `DeterministicFixtureProvider`: Đảm bảo luôn trả về `demo_mode_label="Dữ liệu minh họa"`, bằng chứng có offset chuẩn xác khớp với câu trả lời mẫu.

---

## 5. Các bước triển khai theo thứ tự (Step-by-Step Implementation)

### Bước 1: Chuẩn bị Môi trường và Mock Fixture cho Integration Test
1. Tạo helper khởi tạo app test trong `test/Control/test_interview_flow.py`:
   - Nhận `tmp_path: Path` từ pytest.
   - Tạo file database tạm `db_path = tmp_path / "flow_test.sqlite3"`.
   - Nạp seed catalog qua `load_seed_catalog_into_repository`.
   - Cung cấp mock interpreter (dựa trên `FixtureProvider` hoặc cấu hình linh hoạt kiểm soát lỗi).
   - Khởi tạo app FastAPI qua `create_app` với `Settings(provider=ProviderMode.FIXTURE, database_path=db_path)`.
2. Tạo 2 TestClient:
   - `owner_client`: Nhận và gửi cookie `interview_session_owner`.
   - `stranger_client`: Không có cookie hoặc có cookie của một session khác để kiểm tra ranh giới bảo mật.

### Bước 2: Viết Kiểm thử Quyền sở hữu, Trạng thái và Xử lý Lỗi (Ownership, States & Errors)
1. Viết test `test_q02_session_ownership_and_forbidden_stranger_access`:
   - Gọi từng endpoint đọc/ghi của phiên với `stranger_client`, assert status `403` và `error_code == "SESSION_FORBIDDEN"`.
2. Viết test `test_q02_resource_not_found_handling`:
   - Gọi các ID rác, assert status `404` và format `ApiErrorResponse` chuẩn P04.
3. Viết test `test_q02_strict_question_sequence_and_idempotent_next`:
   - Thử gọi `/next` khi chưa trả lời -> assert `409 INVALID_STATE_TRANSITION`.
   - Thử gọi `/next` khi chưa chấm điểm -> assert `409 INVALID_STATE_TRANSITION`.
   - Sau khi câu hiện tại hoàn tất, gọi `/next` 2 lần liên tiếp -> assert lần 2 trả về trạng thái hiện tại, không nhảy 2 câu.
4. Viết test `test_q02_duplicate_submission_and_conflict_handling`:
   - Gửi 2 lần cùng `client_submission_id` và cùng nội dung -> assert 201/200, `replayed=True`, không tạo dòng thừa.
   - Gửi cùng `client_submission_id` với nội dung bị sửa đổi -> assert `409 SUBMISSION_CONFLICT`.

### Bước 3: Viết Kiểm thử Retry Đồng thời và Rollback Giao dịch
1. Viết test `test_q02_concurrent_evaluation_and_timeout_retry`:
   - Dùng `BlockingInterpreter` và `ThreadPoolExecutor` để kích hoạt 2 request đánh giá cùng lúc.
   - Luồng 2 phải nhận `409 EVALUATION_IN_PROGRESS` kèm `retryable=true`.
   - Dùng `FlakyInterpreter` gây lỗi timeout ở lần 1, kiểm tra câu trả lời vẫn nguyên vẹn trong DB, lần 2 thử lại thành công.
2. Viết bổ sung trong `test/Model/test_repository.py`:
   - Kiểm tra rollback mức database khi vi phạm khóa ngoại hoặc xảy ra exception giữa transaction, đảm bảo không có orphan records.

### Bước 4: Viết Kiểm thử Luồng Hoàn chỉnh (End-to-End Golden Flow)
1. Viết test `test_q02_full_four_question_interview_flow_to_exercise_practice`:
   - Mở phiên mới: kiểm tra có đúng 4 câu hỏi thuộc 4 danh mục (`technical_case`, `code_review`, `architecture`, `debugging`).
   - Duyệt qua từng câu 0..3:
     - Nộp câu trả lời synthetic có căn cứ phù hợp với rubric.
     - Kích hoạt chấm điểm qua API `/evaluate`.
     - Kiểm tra kết quả chấm điểm (điểm, checks, evidence quotes trùng khớp tuyệt đối với substring văn bản).
     - Gọi `/next` để tiến tới câu tiếp theo.
   - Kiểm tra trạng thái cuối cùng: session chuyển thành `completed`.
   - Lấy tổng kết phiên qua `/summary`:
     - Kiểm tra số câu hoàn tất là 4, không còn danh mục nào chưa trả lời.
     - Không có điểm tổng tùy tiện (tuân thủ quy tắc Scoring).
   - Lấy danh sách đề xuất bài tập qua `/exercises`:
     - Kiểm tra các đề xuất khớp với kỹ năng và tiêu chí chưa đạt.
     - Kiểm tra metadata bản quyền của bài tập.
   - Kích hoạt luyện tập lại qua `/practice`:
     - Tạo phiên luyện tập 1 câu mới, kiểm tra phiên mới sẵn sàng làm bài.
2. Viết test `test_q02_early_session_termination_preserves_records_and_disables_advancing`:
   - Mở phiên, làm 1 câu, sau đó gọi `/end` với lý do `student_requested`.
   - Kiểm tra trạng thái phiên là `ended_early`, câu đã làm được lưu trong summary, câu chưa làm thuộc `unanswered_categories`.
   - Kiểm tra nộp bài mới bị từ chối 409.

### Bước 5: Chạy Kiểm thử, Đo lường & Xác nhận Tiêu chí Bàn giao
1. Chạy suite kiểm thử riêng cho nhiệm vụ Q02:
   ```powershell
   .venv\Scripts\python.exe -m pytest test/Model/test_repository.py test/Control/test_interview_flow.py -v
   ```
2. Chạy toàn bộ test suite để đảm bảo không phát sinh lỗi hồi quy (regression):
   ```powershell
   .venv\Scripts\python.exe -m pytest -q
   ```
3. Xác nhận rằng:
   - Tất cả test pass 100%.
   - File `.local/interview.sqlite3` không bị chạm vào.
   - Không có kết nối mạng hay gọi LLM thật ra bên ngoài.

---

## 6. Lệnh thực thi & Bằng chứng nghiệm thu (Verification Commands)

### Lệnh chạy kiểm thử:
```powershell
# Chạy riêng các file của Q02
.venv\Scripts\python.exe -m pytest test/Model/test_repository.py test/Control/test_interview_flow.py -v

# Chạy toàn bộ test suite dự án (bảo đảm không hồi quy)
.venv\Scripts\python.exe -m pytest
```

### Bằng chứng nghiệm thu cần ghi lại:
1. Kết quả đầu ra của pytest hiển thị tất cả các test trong `test/Model/test_repository.py` và `test/Control/test_interview_flow.py` đều `PASSED`.
2. Bằng chứng kiểm tra timestamp của file `.local/interview.sqlite3` không thay đổi trước và sau khi chạy test:
   ```powershell
   Get-Item .local/interview.sqlite3 | Select-Object LastWriteTime
   ```
3. Bằng chứng xác nhận các mã lỗi chuẩn (403, 404, 409, 504) và cấu trúc `ApiErrorResponse` trả về chính xác theo hợp đồng API.

---

## 7. Quy ước Commit & Pull Request

- **Quy ước Commit:**
  `[Q02] Add repository and API workflow integration checks with mocked provider`
- **Tiêu đề Pull Request:**
  `[Q02] Kiểm tra repository và API với mocked provider`
- **Nội dung PR:**
  - Mô tả các test suite đã bổ sung (`test_repository.py` và `test_interview_flow.py`).
  - Ghi rõ các khía cạnh đã được bảo vệ: quyền sở hữu (ownership), thứ tự câu hỏi (sequence), gửi trùng (idempotency), retry đồng thời (concurrency), rollback giao dịch và luồng hoàn chỉnh 4 câu + bài tập.
  - Hướng dẫn reviewer chạy lại lệnh `.venv\Scripts\python.exe -m pytest test/Control/test_interview_flow.py` để tái hiện kết quả.
