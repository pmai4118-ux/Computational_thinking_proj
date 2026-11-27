# Hợp đồng API nội bộ và dữ liệu mẫu (P04)

| Thuộc tính | Nội dung |
| --- | --- |
| Mã công việc | P04 — Thống nhất API và dữ liệu mẫu |
| Người thực hiện | hwngMP (`member-1`) |
| Phụ thuộc | [P01 (`scope.md`)](scope.md), [P02 (`user_flow.md`)](user_flow.md), [P03 (`data_contract.md`)](data_contract.md), [C01 (`content_guide.md`)](content_guide.md) |
| Đầu ra | `docs/api_contract.md`, [`source/Control/schemas.py`](../source/Control/schemas.py), `test/fixtures/api/*.json` |
| Trạng thái | Bản hợp đồng dùng chung cho phát triển song song Frontend (`U01–U08`) và Backend (`I01–I06`) |

---

## 1. Quy ước chung và phân định phạm vi

1. **Định dạng dữ liệu:** Tất cả request/response JSON dùng chuẩn `snake_case` đồng nhất với hợp đồng miền P03 ([`source/Model/question.py`](../source/Model/question.py), [`source/Model/evaluation.py`](../source/Model/evaluation.py)) và được kiểm tra kiểu nghiêm ngặt (`extra="forbid"`, `frozen=True`) qua [`source/Control/schemas.py`](../source/Control/schemas.py).
2. **Bảo mật thông tin đề bài:** Trước và trong khi người học trả lời, `QuestionPromptDTO` chỉ gửi nội dung đề (`prompt`, `code`, `constraints`), kỹ năng và nguồn ghi công. Tuyệt đối không trả `expected_evidence`, mô tả các mức điểm của rubric hay đáp án tham khảo xuống client ở bước làm bài.
3. **Ngữ nghĩa điểm số và trạng thái:**
   - `score: 0` / `total_score: 0` là điểm 0 thực sự khi câu trả lời vi phạm tiêu chí quan sát được (`status: "unmet"`).
   - `score: null` với `status: "insufficient_evidence"` biểu thị chưa đủ căn cứ để kết luận (kèm `unresolved_reason` bắt buộc). Khi bất kỳ tiêu chí nào trong rubric có `status: "insufficient_evidence"`, `total_score` của câu đó giữ giá trị `null`.
   - Lỗi của AI provider (timeout, hết quota, từ chối, JSON sai) trả về lỗi có cấu trúc (`ApiErrorResponse`), không tạo điểm `0` và không kết luận người học thiếu năng lực.
4. **Liên hệ với lát cắt demo P02:**
   - Sơ đồ P02 ([`docs/user_flow.md`](user_flow.md)) mô tả lát cắt demo 5 màn hình (`S01` → `S05`), trong đó màn hình bài tập (`S06`) được đánh dấu hoãn hiển thị CTA trên bản demo thu gọn.
   - Hợp đồng P04 này vẫn định nghĩa đầy đủ cả 6 nhóm endpoint (bao gồm endpoint đề xuất bài tập cho `I06`/`U06`) để không chặn bất kỳ nhánh phát triển nào trong bảng việc.

---

## 2. Quyền truy cập phiên, lưu nháp và chống gửi trùng

### 2.1. Định danh phiên ẩn danh (Anonymous Session Binding)
- Khi tạo phiên đầu tiên (`POST /api/sessions`), server phát hành cookie `interview_owner_id` (`HttpOnly`, `SameSite=Lax`, `Path=/`).
- Mỗi bản ghi `Session` lưu mã băm/định danh của `interview_owner_id`.
- Mọi thao tác đọc/ghi trên `/api/sessions/{session_id}` hoặc `/api/answers/{answer_id}/*` đều kiểm tra quyền sở hữu:
  - Không khớp `interview_owner_id`: trả `403 Forbidden` với `error_code: "SESSION_FORBIDDEN"`.
  - Phiên hết hạn khả dụng: trả `410 Gone` với `error_code: "SESSION_EXPIRED"`.
  - Không tồn tại ID: trả `404 Not Found` với `error_code: "SESSION_NOT_FOUND"`.

### 2.2. Lưu bài bất biến và `client_submission_id` (Idempotency)
- Luồng gửi bài luôn tách thành 2 bước rõ ràng theo P02 (`W01`, `W03`, `W04`, `W05`):
  1. **Bước 1 — Lưu nguyên văn bài trả lời (`POST /api/sessions/{session_id}/answers`):**
     - Client sinh `client_submission_id` (UUID/chuỗi duy nhất cho mỗi lần bấm gửi) và giữ nguyên mã này nếu mất mạng cần gửi lại.
     - Nếu `(session_id, client_submission_id)` đã tồn tại với **cùng** `question_id`, `question_version` và `text`: server trả lại đúng `SavedAnswerDTO` đã lưu kèm `idempotent_replay: true` (`200 OK`).
     - Nếu cùng `client_submission_id` nhưng **khác** nội dung hoặc câu hỏi: server trả `409 Conflict` với `error_code: "SUBMISSION_CONFLICT"`.
     - Giới hạn chiều dài câu trả lời: từ `1` đến `20.000` ký tự (sau khi cắt khoảng trắng hai đầu không được rỗng).
  2. **Bước 2 — Yêu cầu đánh giá (`POST /api/answers/{answer_id}/evaluate`):**
     - Chỉ gọi sau khi bước 1 trả về `answer_id`.
     - Nếu `answer_id` (cùng `revision`) đã có `EvaluationResult` ở trạng thái `completed`: trả lại ngay kết quả đã lưu (`200 OK`), không gọi lại provider và không tạo bản ghi trùng.
     - Nếu đang có một yêu cầu đánh giá khác chạy cho cùng `(answer_id, revision)`: trả `409 Conflict` (`error_code: "EVALUATION_IN_PROGRESS"`, `retryable: true`) để UI đọc trạng thái qua `GET /api/answers/{answer_id}/evaluation`.
     - Nếu lần đánh giá trước thất bại (`failed` do timeout/mạng/quota): cho phép bấm **Thử đánh giá lại** với cùng `answer_id` và `answer_revision`, giữ nguyên bài trả lời gốc.

#### Trạng thái và retry của I04
- `POST /api/answers/{answer_id}/evaluate` nhận `answer_revision` (mặc định `1`); `GET /api/answers/{answer_id}/evaluation?answer_revision=...` đọc lần đánh giá mới nhất của bản trả lời đó. Cả hai yêu cầu cookie chủ sở hữu của phiên chứa bài. Endpoint E09 có `session_id` vẫn hoạt động và trả `EvaluationResponseDTO` gồm `result` và `feedback_items`.
- Trước khi gọi provider, server lưu một bản `processing` trong SQLite. Giao dịch claim bảo đảm một worker duy nhất xử lý cùng `(answer_id, revision)`; request khác nhận `409 EVALUATION_IN_PROGRESS`. GET trả `status: processing`, `processing_started_at`, không có điểm hoặc feedback.
- Khi hoàn tất, server cập nhật chính bản claim thành `completed`. Gọi POST lại trả cùng `evaluation_id` và `version` từ DB, không gọi provider. Khi provider lỗi, server lưu `failed` với `failure_code`, thông điệp an toàn và `retryable`; GET trả trạng thái này để UI hiện nút retry. Retry cùng bản trả lời tạo version đánh giá mới; không tạo thêm Answer.
- Retry chỉ được nhận cho timeout, quota, lỗi mạng/HTTP, phản hồi chưa đầy đủ/sai, lỗi đánh giá tạm thời hoặc worker bị gián đoạn. Lỗi cấu hình/đầu vào/từ chối không retry tự động và trả `409 EVALUATION_RETRY_NOT_ALLOWED`. Claim `processing` quá 15 phút được đánh dấu gián đoạn và có thể retry; claim cũ không được ghi đè kết quả mới.

### 2.3. Chính sách bản nháp trình duyệt (Browser Draft Policy)
- Trình duyệt chỉ lưu bản nháp cục bộ theo khóa `draft:{session_id}:{question_id}` trong `sessionStorage` để chống mất dữ liệu khi rớt mạng hoặc hết phiên.
- Bản nháp cục bộ phải hiển thị nhãn *"Bản nháp trên trình duyệt (chưa lưu server)"*, không được hiển thị *"Đã lưu"* cho tới khi `POST /api/sessions/{session_id}/answers` trả về thành công.
- Khi mở phiên mới hoặc đổi `session_id`, không tự nạp bản nháp của phiên khác.

---

## 3. Danh mục Endpoints

| Nhóm màn hình | Phương thức & Đường dẫn | Request DTO | Response DTO |Fixture mẫu |
| --- | --- | --- | --- | --- |
| **S01 / S02 · Mở phiên** | `POST /api/sessions` | `CreateSessionRequest` | `SessionViewDTO` (`201 Created`) | [`session_created.json`](../test/fixtures/api/session_created.json) |
| **S01 / S03 · Đọc phiên** | `GET /api/sessions/{session_id}` | — | `SessionViewDTO` (`200 OK`) | [`session_created.json`](../test/fixtures/api/session_created.json) |
| **S03 · Lưu bài trả lời** | `POST /api/sessions/{session_id}/answers` | `SubmitAnswerRequest` | `SubmitAnswerResponse` (`201` / `200`) | [`answer_submitted.json`](../test/fixtures/api/answer_submitted.json) |
| **S03 / S04 · Đánh giá bài** | `POST /api/answers/{answer_id}/evaluate` | `EvaluateAnswerRequest` | `EvaluationResultDTO` (`200 OK`) | [`evaluation_completed.json`](../test/fixtures/api/evaluation_completed.json) |
| **S04 · Đọc kết quả** | `GET /api/answers/{answer_id}/evaluation` | — | `EvaluationResultDTO` (`200 OK`) | [`evaluation_insufficient_evidence.json`](../test/fixtures/api/evaluation_insufficient_evidence.json) |
| **S04 → S03/S05 · Chuyển câu** | `POST /api/sessions/{session_id}/next` | `NextQuestionRequest` | `SessionViewDTO` (`200 OK`) | [`session_created.json`](../test/fixtures/api/session_created.json) |
| **S03 / S04 → S05 · Kết thúc sớm** | `POST /api/sessions/{session_id}/end` | `EndSessionRequest` | `SessionSummaryDTO` (`200 OK`) | [`session_summary.json`](../test/fixtures/api/session_summary.json) |
| **S05 · Tổng kết phiên** | `GET /api/sessions/{session_id}/summary` | — | `SessionSummaryDTO` (`200 OK`) | [`session_summary.json`](../test/fixtures/api/session_summary.json) |
| **S06 · Đề xuất bài tập** | `GET /api/sessions/{session_id}/exercises` | — | `ExerciseRecommendationsResponse` (`200 OK`) | [`exercise_recommendations.json`](../test/fixtures/api/exercise_recommendations.json) |
| **S06 · Chi tiết bài tập** | `GET /api/exercises/{exercise_id}?version={version}` | — | `ExerciseDetailDTO` (`200 OK`) | Chỉ trả nội dung đã duyệt và nguồn đã xác minh |
| **S06 · Đã gỡ ngày 27/11/2026** | `POST /api/sessions/{session_id}/answers/{answer_id}/practice` | Payload cũ chỉ để nhận biết client legacy | `ApiErrorResponse` (`410 Gone`, `FEATURE_RETIRED`) | Kiểm tra quyền phiên trước, không tạo phiên luyện mới |

### Quy tắc đề xuất và luyện lại (I06)
- Mỗi `matched_gap` trong đề xuất trả `answer_ref` (`id`, `revision`) của bài đã chấm để giao diện gọi thao tác luyện lại đúng bản trả lời; không suy đoán từ câu hiện tại của phiên.
- Chỉ tiêu chí `unmet` có điểm dưới mức tối đa trong kết quả `completed` của bản trả lời mới nhất mới tạo điểm thiếu; `insufficient_evidence`, lỗi provider và câu chưa trả lời không tạo khuyến nghị.
- Bài tập phải có trạng thái duyệt `approved`, nguồn có giấy phép đã xác minh, cùng `skill_id` và `criterion_type` với điểm thiếu. Bài tiên quyết được đưa trước bài phụ thuộc; chuỗi tiên quyết thiếu hoặc có vòng lặp bị bỏ qua. `recommendation_reason` giải thích trực tiếp điểm thiếu hoặc quan hệ tiên quyết.
- Khi không có điểm thiếu hoặc không có bài phù hợp, `recommendations` rỗng và `message` nêu rõ lý do; `unmatched_skill_ids` liệt kê kỹ năng có điểm thiếu nhưng không có bài hợp lệ.
- Lượt luyện mới chỉ được tạo từ bản trả lời thuộc phiên của cookie hiện tại, với tiêu chí và bài tập thực sự nằm trong khuyến nghị. Chỉ chọn câu hỏi đã duyệt, đúng kỹ năng/loại tiêu chí, khác câu gốc; nếu không có biến thể hợp lệ thì trả `409`, không tạo phiên rỗng. Phiên luyện mới có một câu và dùng lại cơ chế nộp bài, chấm điểm, quyền sở hữu hiện có.

### Quy tắc chuyển câu (`POST /api/sessions/{session_id}/next`)
- Client gửi `from_question_index` (chỉ số câu hiện tại mà người học đang xem kết quả).
- Server chỉ tăng sang câu kế tiếp khi câu tại `from_question_index` đã có kết quả đánh giá `completed` (bao gồm cả trường hợp `completed` nhưng có tiêu chí `insufficient_evidence`).
- Nếu client gửi lặp lại cùng `from_question_index` sau khi server đã chuyển sang `from_question_index + 1`, server trả lại `SessionViewDTO` hiện tại mà không nhảy cách qua hai câu (`W05`).
- Nếu câu hiện tại chưa được đánh giá xong (`pending`/`processing`/`failed`), server từ chối chuyển câu với `409 Conflict` (`error_code: "INVALID_STATE_TRANSITION"`).

### Quy tắc kết thúc sớm (`POST /api/sessions/{session_id}/end`)
- Chỉ cookie sở hữu phiên mới được kết thúc; request hiện hỗ trợ `reason: "student_requested"`.
- Gọi lại sau khi đã kết thúc trả cùng trạng thái và báo cáo, không xóa bài làm hay kết quả đã lưu. Phiên kết thúc sớm không nhận thêm câu trả lời hoặc yêu cầu chuyển câu.
- `SessionSummaryDTO` giữ kết quả và liên kết căn cứ của các câu đã chấm, nêu những nhóm chưa làm/chưa đủ căn cứ; không tự tính một điểm tổng năng lực từ phiên chưa đầy đủ.

---

## 4. Bảng mã lỗi chuẩn (`ApiErrorResponse`)

Mọi phản hồi lỗi đều tuân theo schema `ApiErrorResponse` trong [`source/Control/schemas.py`](../source/Control/schemas.py) và có mẫu đối chiếu tại [`test/fixtures/api/errors.json`](../test/fixtures/api/errors.json):

| HTTP Status | `error_code` | `retryable` | Tình huống và hướng dẫn phục hồi trên UI |
| :---: | --- | :---: | --- |
| `422` | `INVALID_INPUT` | `false` | Câu trả lời rỗng, vượt 20.000 ký tự, hoặc cấu hình role/level không hợp lệ. Giữ nguyên nội dung đã nhập và focus vào trường lỗi. |
| `403` | `SESSION_FORBIDDEN` | `false` | Cookie phiên không khớp chủ sở hữu của `session_id`/`answer_id`. Giữ bản nháp để người học sao chép và mở phiên mới hợp lệ. |
| `404` | `SESSION_NOT_FOUND` / `EXERCISE_NOT_FOUND` | `false` | Không tìm thấy phiên, câu trả lời hoặc bài tập. Cung cấp nút quay về màn hình Bắt đầu / Tổng kết. |
| `410` | `SESSION_EXPIRED` | `false` | Phiên đã hết hạn. Khóa gửi vào phiên cũ, giữ bản nháp trên màn hình và hướng dẫn tạo phiên mới. |
| `409` | `SUBMISSION_CONFLICT` | `false` | Gửi trùng `client_submission_id` với nội dung khác. Đọc lại bài đã lưu hoặc sinh mã gửi mới nếu tạo lượt trả lời mới. |
| `409` | `EVALUATION_IN_PROGRESS` | `true` | Đang có tiến trình chấm cho cùng bài. Hiển thị trạng thái đang xử lý, không tạo yêu cầu chấm mới song song. |
| `409` | `EVALUATION_RETRY_NOT_ALLOWED` | `false` | Lỗi đánh giá trước không thể phục hồi bằng retry; đọc trạng thái `failed` và xử lý cấu hình hoặc liên hệ hỗ trợ. |
| `409` | `INVALID_STATE_TRANSITION` | `false` | Bấm chuyển câu khi câu hiện tại chưa đánh giá xong hoặc phiên đã kết thúc. |
| `503` | `INSUFFICIENT_QUESTION_BANK` | `false` | Ngân hàng câu hỏi đã duyệt chưa đủ phủ 4 nhóm theo khung `C01`. Báo rõ nhóm kỹ năng thiếu, không mở phiên rỗng. |
| `504` | `PROVIDER_TIMEOUT` | `true` | Quá hạn chờ Gemini/provider. Giữ nguyên `answer_ref` đã lưu và hiện nút **Thử đánh giá lại**. |
| `429` | `PROVIDER_QUOTA_EXCEEDED` | `true` | Hết hạn mức gọi API tạm thời. Giữ nguyên `answer_ref`, thông báo thử lại sau hoặc chuyển sang chế độ dữ liệu mẫu. |
| `502` | `PROVIDER_OUTPUT_INVALID` / `PROVIDER_NETWORK_ERROR` / `PROVIDER_HTTP_ERROR` / `PROVIDER_INCOMPLETE_RESPONSE` | `true` | Provider lỗi hoặc trả dữ liệu không hợp lệ. Giữ bài gốc và cho phép retry. |
| `502` / `503` / `422` | `PROVIDER_REFUSAL` / `PROVIDER_CONFIG_ERROR` / `PROVIDER_BILLING_REQUIRED` / `PROVIDER_INPUT_LIMIT` | `false` | Lỗi không thể giải quyết bằng retry cùng cấu hình và đầu vào. Giữ bài gốc và báo hướng xử lý. |

---

## 5. Kiểm tra hoàn thành (Acceptance Checks)

Chạy kiểm thử tự động xác nhận toàn bộ fixture mẫu khớp schema P04:

```powershell
uv run --locked python -m pytest test/test_api_contract.py
```

- [x] Mọi fixture thành công (`session_created.json`, `answer_submitted.json`, `evaluation_completed.json`, `evaluation_insufficient_evidence.json`, `session_summary.json`, `exercise_recommendations.json`) đều parse hợp lệ qua DTO trong `source/Control/schemas.py` mà UI không phải đoán tên trường.
- [x] Mọi trích dẫn (`quote`, `start_offset`, `end_offset`) trong fixture khớp chính xác với chuỗi con trong `answer_text`.
- [x] Có đầy đủ fixture lỗi cho đầu vào sai (`INVALID_INPUT`), phiên không thuộc người dùng (`SESSION_FORBIDDEN`), xung đột mã gửi (`SUBMISSION_CONFLICT`) và lỗi timeout giữ nguyên `answer_ref` (`PROVIDER_TIMEOUT`).

## Additive API — Java learning paths (27/11/2026)

The existing interview DTOs remain unchanged. New endpoints:
`GET /api/learning-paths/catalog`, `GET /api/learning-paths/markdown`, and
`POST /api/learning-paths/plan`. The page is `/learning-path`.

Plan input is `LearningPlanRequest` in `source/Model/learning_path.py`:
confirmed goal, track/mode, integer hours/week and weeks, optional target and
self-reported completed lesson IDs, and whether to consult the current owner's
profile. Never accept an owner token/hash in JSON. Unknown/duplicate IDs or an
unconfirmed goal return 422. Response includes all remaining required lessons,
allocated/deferred minutes, feasible/shortfall and explanatory warnings.
Details and example: [Java roadmap handoff](JAVA_BACKEND_IMPLEMENTATION.md).


## Bổ sung 27/11/2026 — gỡ luyện với câu hỏi khác

Theo yêu cầu người dùng, không còn thao tác hoặc service tạo phiên một câu khác
sau khi chấm bài. Endpoint POST `/api/sessions/{session_id}/answers/{answer_id}/practice`
được đánh dấu deprecated và trả 410 `FEATURE_RETIRED` cho chủ phiên, với
`retryable=false`. Quyền sở hữu vẫn được kiểm tra trước (khác chủ trả 403).
Các field tương thích `eligible_alternate_question_available` trong recommendations
và `alternate_question_available` trong report luôn false.
GET recommendations/details vẫn cung cấp hướng dẫn ôn tập có nguồn.

Loading và tự cập nhật kết quả chỉ đọc/trình bày trạng thái thật; polling review
là GET mỗi 5 giây, dừng sau 150 giây hoặc khi hoàn tất/lỗi. Polling không gọi POST
evaluate. Summary giữ tối đa hai lượt đánh giá đồng thời, gộp các lượt tải trạng
thái chồng nhau và giữ nguyên bài gốc khi provider lỗi.


## Trang lịch sử phiên — 27/11/2026

- `GET /` và `GET /setup` hiển thị tối đa 3 phiên gần nhất của chủ cookie hiện tại,
  kèm nút **Xem tất cả** tới `/history`.
- `GET /history` là tab lịch sử đầy đủ, sắp theo thời điểm tạo giảm dần; cùng thời
  điểm thì dùng session ID để giữ thứ tự ổn định. Phiên thiếu timestamp xếp cuối.
- Các trang dùng chung danh sách với trạng thái và link tiếp tục/xem tổng kết.
  Danh sách trống/ít hơn 3 không thêm phiên minh họa. Không nhận owner từ query.
- Đây là thay đổi View và chuẩn hóa thứ tự Service, không đổi DTO/DB hoặc tạo
  lượt đánh giá AI khi liệt kê lịch sử.
