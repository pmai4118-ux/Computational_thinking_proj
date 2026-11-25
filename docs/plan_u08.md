# Kế hoạch Thực hiện Nhiệm vụ U08 (Sprint Backlog P0)
# Hoàn thiện loading, lỗi, retry và hết phiên
# Complete all loading, empty, failure, retry and session-expiry states

- **Mã nhiệm vụ:** `[U08]` (Tuần 3 · Giao diện tiếng Việt)
- **Độ ưu tiên:** `P0` (Nhiệm vụ cốt lõi cho trải nghiệm người dùng)
- **Người thực hiện:** `anh khoa`
- **Các tầng kiến trúc liên quan (MVC-S):**
  - **View (V):** `source/view/templates/`, `source/view/static/js/api_client.js`, `workspace.js`, `evidence.js`, `summary.js`, `exercise.js`, CSS tokens/components.
  - **Controller (C):** `source/Control/schemas.py` (`ApiErrorResponse`, `ErrorCode`), `interview_controller.py`, `saved_evaluation_controller.py`.
- **Nhiệm vụ phụ thuộc:** `U07` (Đã tích hợp API client), `E08` (Đã có timeout & bounded retry phía service).
- **Nhiệm vụ kế thừa mở khóa:** `Q04` (Kiểm thử khả năng sử dụng, zoom 200%, phím tắt).

---

## 1. Mục tiêu & Tiêu chí nghiệm thu (Acceptance Criteria / Aim)

> **Mục tiêu cốt lõi để hoàn thành (Aim):**
> - ✓ **Không hiện spinner vô hạn hoặc lỗi không có cách xử lý.**
> - ✓ **Gửi trùng bị ngăn ở cả UI và server, dữ liệu nhập vẫn còn sau lỗi.**
> - | **Giữ nội dung khi lỗi phục hồi được; chống bấm trùng; luôn có cách đi tiếp.**

Cụ thể hóa thành các chỉ số kiểm thử:
1. **Không có spinner vô hạn:** Trạng thái chờ (loading/polling) phải có chặn thời gian (bounded timeout / cap tối đa 150s). Nếu AI phản hồi lâu hoặc đứt kết nối, UI phải dừng chờ và cung cấp hướng xử lý, không treo vô tận.
2. **Mọi lỗi đều có hành động kế tiếp (Next Action / Luôn có cách đi tiếp):** Không hiển thị thông báo lỗi cụt ngủng. Lỗi phải đi kèm nút bấm hoặc đường dẫn hành động phục hồi cụ thể (Thử lại, Bắt đầu phiên mới, Quay về trang chủ...).
3. **Ngăn chặn click đúp / gửi trùng lặp (Chống bấm trùng):** Khóa nút bấm (`disabled`, cờ `busy`) ngay khi kích hoạt ở phía client; backend xử lý idempotent qua `client_submission_id`, không tạo bản ghi rác.
4. **Bảo toàn dữ liệu người dùng (Giữ nội dung khi lỗi phục hồi được):** Khi gặp lỗi (input sai, mất mạng, lỗi AI provider, xung đột, hết phiên), nội dung học viên đã nhập **tuyệt đối không bị xóa**.
5. **Xử lý hết phiên (`SESSION_EXPIRED`) và hết quyền (`SESSION_FORBIDDEN`):** Khóa chức năng gửi vào phiên cũ, giữ nguyên bản nháp trên ô nhập liệu để học viên sao chép, hiển thị hướng dẫn tạo phiên mới.
6. **Lỗi AI không biến thành điểm 0:** Khi AI bị timeout, quá quota hoặc lỗi mạng, giữ nguyên câu trả lời đã lưu, không gán điểm 0, không đánh giá thiếu năng lực, cung cấp nút **Thử đánh giá lại**.
7. **Khả năng tiếp cận (Accessibility - WCAG 2.2):** Quản lý focus chuẩn (focus vào thông báo lỗi hoặc ô cần sửa), thông báo động qua `role="status"` / `role="alert"` (`aria-live="polite"` / `"assertive"`).

---

## 2. Ma trận Trạng thái Toàn diện (State Matrix)

| Màn hình | Tình huống / Trạng thái | Mã lỗi / Điều kiện | Phản hồi giao diện (UI) | Hành động phục hồi & Dữ liệu giữ lại |
|---|---|---|---|---|
| **S01 · Trang chủ** (`welcome.html`) | Phiên trống (Empty) | `sessions.length == 0` | Hiển thị lời chào, giải thích ứng dụng, ẩn bảng danh sách phiên | Nút CTA "Bắt đầu làm bài" dẫn tới `/setup`. |
| | Lỗi từ phiên khác redirect về | 403 / 404 từ session | Banner cảnh báo `role="alert"` trên đầu trang | Hiển thị rõ lý do và danh sách các phiên thuộc về mình. |
| **S02 · Thiết lập** (`setup.html`) | Đang tạo phiên (Pending) | Submit form `/setup` | Nút submit bị `disabled`, đổi chữ "Đang chuẩn bị phiên…" | Chống click đúp tạo phiên trùng. |
| | Dữ liệu không hợp lệ (422) | `INVALID_INPUT` / 413 | Banner lỗi, `aria-invalid="true"` trên ô sai, focus ô sai | Giữ nguyên các dropdown khác đã chọn. |
| | Thiếu ngân hàng câu hỏi (503) | `INSUFFICIENT_QUESTION_BANK` | Báo cụ thể nhóm kỹ năng chưa đủ câu duyệt | Không tạo phiên rỗng; hướng dẫn kiểm tra dữ liệu seed. |
| **S03 · Không gian làm bài** (`workspace.html`) | Đang soạn thảo (Draft) | Sự kiện gõ phím | Bộ đếm ký tự cập nhật (`aria-live="polite"`), auto-save sessionStorage | Giữ bản nháp cục bộ gắn với `sessionId:questionId`. |
| | Ô nhập trống / vượt 20.000 ký tự | Kiểm tra client / 422 | Báo lỗi cạnh ô nhập, `role="alert"`, focus textarea | Giữ nguyên văn bản, không gửi request lên server. |
| | Đang lưu bài (Submitting) | Bấm Gửi câu trả lời | Disable submit + kết thúc sớm, `role="status"` "Đang lưu nguyên văn…" | Giữ văn bản trong textarea, giữ `client_submission_id`. |
| | Đang đợi AI chấm (Evaluating) | Polling trạng thái mỗi 5s | Báo "Đã chờ X giây…", có giới hạn tối đa 150s, không spinner vĩnh viễn | Bài đã an toàn trên DB, học viên có thể reload mà không mất bài. |
| | Timeout AI chấm (504) | `PROVIDER_TIMEOUT` | Báo "AI phản hồi quá thời gian", hiện nút "Thử đánh giá lại" | Giữ nguyên bài gốc trên server, điểm giữ null (không phải 0). |
| | Lỗi AI tạm thời (429, 502) | Quota / Network / JSON sai | Báo lỗi dịch vụ, hiện nút "Thử đánh giá lại" | Giữ bài gốc, cho phép retry cùng `answer_id`. |
| | Lỗi AI vĩnh viễn (503, 502) | Config / Billing / Refusal | Báo lỗi cấu hình/từ chối, ẩn nút retry | Không tạo vòng lặp retry vô ích; bài gốc vẫn lưu. |
| | Hết phiên (410) | `SESSION_EXPIRED` | Báo "Phiên đã hết hạn khả dụng", khóa gửi bài, hiện nút "Mở phiên mới" | Giữ nguyên bản nháp trong textarea để học viên copy. |
| | Không có quyền (403) | `SESSION_FORBIDDEN` | Báo phiên không thuộc trình duyệt này | Giữ nguyên bản nháp để copy, dẫn link về `/setup`. |
| | Hết câu hỏi (Empty) | `current_question == null` | Card thông báo "Không còn câu hỏi đang chờ", hiện tiến độ | Nút CTA "Mở tổng kết phiên" điều hướng mượt sang S05. |
| **S04 · Xem kết quả** (`answer_review.html`) | Đang nạp kết quả (Loading) | `getEvaluation` ban đầu | `role="status"` "Đang tải kết quả đã lưu…", ẩn vùng kết quả | Tránh giật layout giao diện. |
| | Lỗi tải kết quả (404 / Lỗi mạng) | Không nạp được đánh giá | Banner lỗi kèm nút "Thử tải lại kết quả", focus vùng lỗi | Không làm mất bài trả lời đã lưu. |
| | Tiêu chí thiếu căn cứ | `insufficient_evidence` | Badge "Chưa đủ bằng chứng", điểm null (không gán 0), hiện lý do | Vẫn cho phép bấm "Câu tiếp theo" nếu toàn bài `completed`. |
| | Đang chuyển câu (Next question) | Bấm "Câu tiếp theo" | Disable nút, báo "Đang chuyển câu theo kết quả đã lưu…" | Ngăn click đúp làm server tăng 2 câu liên tiếp. |
| | Lỗi chuyển câu (409 / Lỗi mạng) | Chưa hoàn tất câu hiện tại | Bật lại nút, báo lỗi chi tiết, focus vùng thông báo | Giữ nguyên kết quả câu hiện tại trên màn hình. |
| **S05 · Tổng kết** (`summary.html`) | Đang nạp tổng kết (Loading) | `getSessionSummary` | `role="status"` "Đang tải kết quả và độ phủ phiên…" | Tránh hiển thị dữ liệu rỗng chớp nhoáng. |
| | Chưa có câu hoàn tất / Không có điểm thiếu | Phiên kết thúc sớm / Đạt hết | Hiện vùng rỗng thân thiện (`outcomes-empty`, `gaps-empty`) | Báo rõ "Không ghi nhận điểm thiếu nào", không crash UI. |
| | Lỗi tải tổng kết (500 / Network) | Mất mạng khi tải summary | Báo lỗi kèm nút "Tải lại tổng kết" | Khẳng định dữ liệu phiên vẫn an toàn trên máy chủ. |
| **S06 · Đề xuất bài tập** (`exercise.html`) | Đang nạp bài tập (Loading) | `getExerciseRecommendations` | "Đang tải đề xuất từ phiên…", ẩn danh sách bài | Giữ màn hình ổn định. |
| | Không có bài tập phù hợp (Empty) | `recommendations.length == 0` | Báo rõ kỹ năng chưa có bài duyệt, "Không tự tạo bài thay thế" | Đảm bảo tính trung thực dữ liệu, không bịa bài tập. |
| | Đang tạo lượt luyện lại (Pending) | Bấm "Luyện lại với câu hỏi khác" | Disable nút, đổi nhãn "Đang tạo lượt luyện…", báo trạng thái | Ngăn bấm liên tiếp tạo nhiều phiên luyện trùng lặp. |
| | Lỗi tạo lượt luyện lại | Hết câu hỏi đủ điều kiện | Bật lại nút, giải thích lý do, giữ nguyên màn hình bài tập | Không phá vỡ luồng học viên. |

---

## 3. Các bước triển khai chi tiết (Implementation Steps)

### Bước 1: Chuẩn hóa tầng DTO và Giao thức Lỗi (`source/Control/schemas.py`)
- Đối soát `ErrorCode` và `ApiErrorResponse` với `docs/api_contract.md`.
- Đảm bảo `ApiErrorResponse` luôn trả đủ:
  - `error_code`: Mã lỗi chuẩn dạng chuỗi định danh.
  - `message`: Thông điệp tiếng Việt thân thiện, rõ ràng.
  - `retryable`: Boolean xác định client có được hiện nút retry không.
  - `recovery_action`: Hướng dẫn cụ thể hành động kế tiếp cho người dùng.
  - `field_errors`: Mapping lỗi từng trường cho form input.
  - `client_submission_id`, `session_id`, `answer_ref`: Dữ liệu ngữ cảnh để client khôi phục.

### Bước 2: Tối ưu Transport Client (`source/view/static/js/api_client.js`)
- Cải thiện hàm `createApiError`:
  - Trích xuất `field_errors` vào thuộc tính `error.fieldErrors`.
  - Phân tích `payload.detail` dạng danh sách (chuẩn FastAPI `RequestValidationError`) thành thông báo tiếng Việt có nghĩa.
  - Xử lý các mã lỗi đặc biệt: `SESSION_EXPIRED` (410), `SESSION_FORBIDDEN` (403), `SUBMISSION_CONFLICT` (409), `PROVIDER_TIMEOUT` (504).
  - Đảm bảo khi mất kết nối mạng (`TypeError: fetch failed`), trả về `NETWORK_ERROR` kèm `retryable: true` và thông điệp giữ nguyên bản nháp.

### Bước 3: Hoàn thiện Logic Xử lý Trạng thái Màn hình Làm bài (`workspace.js` & `workspace.html`)
- **Khống chế Polling chống Spinner vô hạn:**
  - Thiết lập ngưỡng thời gian tối đa cho `watchEvaluation` (ví dụ 150 giây).
  - Nếu sau 150s chưa có kết quả cuối cùng, tự động dừng interval, chuyển trạng thái thông báo: *"Lượt đánh giá mất nhiều thời gian hơn dự kiến. Câu trả lời đã được lưu an toàn trên máy chủ; bạn có thể tải lại trang hoặc bấm Thử đánh giá lại."* và hiển thị nút retry.
- **Xử lý triệt để Hết phiên (`SESSION_EXPIRED`) và Hết quyền (`SESSION_FORBIDDEN`):**
  - Khi nhận mã lỗi `SESSION_EXPIRED` hoặc `SESSION_FORBIDDEN`:
    - Ẩn hoặc disable nút "Gửi câu trả lời" và "Thử đánh giá lại".
    - Giữ nguyên toàn bộ nội dung trong ô `textarea` để học viên dễ dàng sao chép.
    - Hiển thị nút hành động phục hồi: *"Bắt đầu phiên mới"* (dẫn tới `/setup`).
    - Focus vào vùng thông báo lỗi để Screen Reader đọc ngay lập tức.
- **Bảo toàn Bản nháp và Ngăn Click đúp:**
  - Nút Submit bị disable ngay khi form được submit (`setBusy(true)`).
  - Nếu submit thất bại (mạng đứt, lỗi 500, lỗi 422), nút Submit được kích hoạt lại để học viên bấm gửi lại mà không bị mất chữ.

### Bước 4: Hoàn thiện Trạng thái Lỗi & Phục hồi trên các Màn hình Khác
- **`evidence.js` (S04):**
  - Bổ sung nút "Tải lại kết quả" khi `getEvaluation` lỗi mạng hoặc lỗi tạm thời.
  - Khóa nút "Câu tiếp theo" khi đang chuyển câu, mở lại nếu có lỗi và focus vào thông báo lỗi.
  - Ẩn nút retry vô nghĩa nếu phiên đã hết hạn.
- **`summary.js` (S05):**
  - Hiển thị trạng thái tải nhẹ nhàng, xử lý lỗi nạp summary bằng nút "Tải lại tổng kết".
  - Hiển thị empty state rõ ràng khi chưa có kết quả hoặc không có điểm thiếu.
- **`exercise.js` (S06):**
  - Disable nút "Luyện lại với câu hỏi khác" ngay khi bấm để chống tạo phiên đôi.
  - Hiển thị empty state trung thực khi không có bài tập phù hợp, không bịa dữ liệu.

### Bước 5: Viết Bộ Kiểm thử Tự động Nghiệm thu (`test/view/test_u08_error_states.py`)
- Viết các test case pytest mô phỏng chính xác các tình huống:
  1. `test_u08_submit_answer_retains_input_on_network_or_server_error`: Mô phỏng submit lỗi, xác nhận văn bản và submission_id được giữ lại.
  2. `test_u08_session_expired_locks_submission_and_preserves_draft`: Giả lập phiên hết hạn (410 GONE), kiểm tra không cho gửi đè và cung cấp hướng dẫn tạo phiên mới.
  3. `test_u08_duplicate_submission_prevention_and_idempotency`: Xác nhận chống click đúp ở UI và replay kết quả đã lưu ở server.
  4. `test_u08_provider_timeout_keeps_answer_without_zero_score_and_offers_retry`: Xác nhận timeout provider giữ nguyên bài, điểm null và có nút retry.
  5. `test_u08_no_infinite_polling_and_accessible_focus`: Kiểm tra giới hạn polling và thuộc tính accessibility (`role`, `aria-live`, focus).

---

## 4. Kế hoạch Kiểm tra & Bàn giao (Handoff Checklist)

- [ ] Toàn bộ test case mới trong `test/view/test_u08_error_states.py` đều vượt qua (`passed`).
- [ ] Toàn bộ bộ test hiện tại (`pytest`) không bị hồi quy (regression).
- [ ] Giao diện tiếng Việt chuẩn mực, tôn trọng người học, không chứa thuật ngữ lập trình thô ráp trong thông báo lỗi.
- [ ] PR title tuân thủ quy tắc: `[U08] Hoàn thiện loading, lỗi, retry và hết phiên`.
