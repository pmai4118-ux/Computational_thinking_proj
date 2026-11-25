# Danh sách kiểm tra bàn giao, xử lý lỗi chặn và chốt phát hành (Q06 & Q08)

- **Mã công việc:** `Q06` (Sửa lỗi chặn bàn giao) & `Q08` (Chốt release và tổng duyệt thuyết trình)
- **Ngày tổng hợp:** 25/11/2026
- **Phụ thuộc đầu vào:** `Q01`–`Q05` (cho `Q06`); `Q06` và `Q07` (cho `Q08`)
- **Tài liệu đóng gói đi kèm:** [Báo cáo tổng kết & Tư duy tính toán](final_report.md) · [Kịch bản cài đặt & demo](demo_script.md)

---

## 1. Tổng hợp kết quả đầu vào từ Q01–Q05

| Nhiệm vụ nguồn | Trạng thái đầu vào | Tóm tắt bằng chứng / Vấn đề tiếp nhận cho Q06 |
| --- | --- | --- |
| **`Q01`** | Đạt | Ranh giới điểm rubric, bảo toàn `null` ≠ `0`, đáp án tương đương và từ chối trích dẫn bịa đặt đã được kiểm thử ngoại tuyến (`test/service/test_scoring.py`, `test/service/test_evidence_validation.py`). Không còn lỗi chặn. |
| **`Q02`** | Đạt | Lưu trữ SQLite, quyền sở hữu ẩn danh (`403`), chống gửi trùng (`idempotent_replay` / `409 SUBMISSION_CONFLICT`), khóa đánh giá đồng thời (`409 EVALUATION_IN_PROGRESS`), rollback giao dịch và luồng 4 câu + kết thúc sớm + bài tập đã kiểm thử (`test/Model/test_repository.py`, `test/Control/test_interview_flow.py`). |
| **`Q03`** | Đã chạy đo live · **Chặn kết luận độ chính xác** | 12 ca `held_out` chạy qua `antigravity` (`gemini-3.8-flash-medium`) cho thấy 100% trích dẫn khớp nguyên văn, 2/2 ca `injection` nhận `0/6`, nhưng 1 ca (`C07_C02_02`) mất `234,23s` (>120s tổng thời gian khi có retry). **Giới hạn còn mở:** `C07` hiện có `0/12` nhãn phân xử độc lập (`independent_reviews: []`, `adjudicated_evaluation: null`) nên chưa thể tính độ đồng thuận chuyên gia ([evaluation_report.md](evaluation_report.md)). |
| **`Q04`** | Đạt (phạm vi kiểm tra đã ghi) | Không tràn ngang ở 320px/640px/1280px, `Tab`/`Enter`/`Space`/`Escape` hoạt động, vùng `role="status"`/`role="alert"` và viền `:focus-visible` rõ ([usability_check.md](usability_check.md)). Chưa tuyên bố chứng nhận toàn bộ WCAG 2.2. |
| **`Q05`** | Đã đóng các lỗi tái hiện từ `P1` & `P2` | Đã ghi nhận 2 lượt người dùng (`P1`, `P2`) không chứa PII ([user_observations.md](user_observations.md)). Các lỗi UI tái hiện (`Q05-02`–`Q05-15`, bao gồm `UI-01`–`UI-05`) đã sửa kèm test hồi quy; `UI-06` giữ thiết kế `sessionStorage` theo tab và đã làm rõ trên UI; `UI-07` là giới hạn heuristic `fixture`. |

---

## 2. Các lỗi chặn bàn giao & phục hồi đã đóng trong Q06

Mỗi mục dưới đây ghi rõ bước tái hiện trước khi sửa, thay đổi tại đúng tầng MVC-S/Root, và kiểm thử hồi quy sau sửa:

| Mã lỗi | Mức độ | Tầng MVC-S & File | Bước tái hiện trước khi sửa | Cách sửa đã áp dụng | Bằng chứng / Kiểm thử hồi quy |
| --- | :---: | --- | --- | --- | --- |
| **`Q06-01`** | **Chặn bàn giao (P0)** | Control: [`source/Control/saved_evaluation_controller.py`](../source/Control/saved_evaluation_controller.py) | 1. Phiên đã có bài nộp chuyển sang trạng thái `expired`.<br>2. Gọi `POST /api/sessions/{id}/answers/{aid}/evaluate` hoặc `POST /api/answers/{aid}/evaluate`.<br>3. `_owned_context()` chỉ gọi `get_session()` mà không kiểm tra `state == "expired"`, khiến hệ thống **vẫn gọi AI thật và tiêu tốn ngân sách** trên phiên đã hết hạn. Ngoài ra, ngoại lệ ngoài `ProviderFailureError` sau khi ghi `EVALUATION_FAILED` bị thoát ra thành HTTP 500 không theo envelope `ApiErrorResponse`. | 1. Kiểm tra `session_view.state.value == "expired"` ngay đầu `evaluate()` và trả `410 SESSION_EXPIRED` (`retryable=False`) trước khi claim hoặc gọi provider.<br>2. Bắt ngoại lệ không mong đợi sau bước lưu `EVALUATION_FAILED` và trả `500` theo chuẩn `ApiErrorResponse(error_code="EVALUATION_FAILED", retryable=True, answer_ref=...)`, bảo toàn bài gốc.<br>3. Dùng `labels.get(...)` phòng thủ trong `_to_response()`. | `test/test_q06_release_blockers.py::test_q06_expired_session_blocks_evaluation_without_calling_provider`<br>`test/test_q06_release_blockers.py::test_q06_unexpected_evaluation_error_returns_structured_api_error_and_preserves_answer` |
| **`Q06-02`** | **Chặn phục hồi (P0)** | View: [`source/view/static/js/workspace.js`](../source/view/static/js/workspace.js), [`source/view/templates/answer_review.html`](../source/view/templates/answer_review.html), [`source/view/static/js/evidence.js`](../source/view/static/js/evidence.js) | 1. Gửi câu trả lời, gặp lỗi `504 PROVIDER_TIMEOUT` (`status: "failed", retryable: true`).<br>2. Tải lại `/sessions/{id}`: giao diện vẫn hiện nút chính nổi bật ***"Xem kết quả câu này"*** (`#open-review`).<br>3. Bấm vào đó (hoặc mở `/sessions/{id}/review?answer_id=...` khi đánh giá đang `failed`/`processing`) dẫn tới khung review rỗng (`0` tiêu chí) và **không có nút "Thử đánh giá lại"**, tạo ngõ cụt phục hồi. | 1. Trong `workspace.js`, ẩn `#open-review` khi trạng thái đang kiểm tra, `processing`, `failed` hoặc `404` để giữ ***"Thử đánh giá lại"*** là hành động phục hồi rõ ràng.<br>2. Trong `answer_review.html` và `evidence.js`, khi kết quả là `failed`, ẩn khung tiêu chí rỗng, hiện cảnh báo lỗi (`role="alert"`, nhận focus) khẳng định bài gốc đã được lưu không có điểm, và cung cấp nút ***"Thử đánh giá lại"*** (`#retry-review-evaluation`, có khóa chống bấm trùng) khi `retryable=true`; khi `processing`, hiện thông báo trạng thái và nút ***"Tải lại kết quả"***. | `test/view/q06_recovery.test.cjs` (4 ca hành vi cho `workspace.js` và `evidence.js`)<br>`test/test_q06_release_blockers.py::test_q06_review_template_and_scripts_provide_failed_evaluation_recovery` |
| **`Q06-03`** | **Cao (P1)** | View: [`source/view/static/js/summary.js`](../source/view/static/js/summary.js), [`source/view/templates/welcome.html`](../source/view/templates/welcome.html) | Khi một phiên ở trạng thái `expired`, `summary.js` hiển thị chuỗi tiếng Anh thô `"expired"`, còn `welcome.html` rơi vào nhánh `else` và gắn nhãn sai là `"Đã lưu"`. | Bổ sung `expired: "Đã hết hạn"` trong `stateNames` của `summary.js` và thêm nhánh `{% elif item.state.value == "expired" %}` (`badge--error`: *"Đã hết hạn"*) trong `welcome.html`. | `test/test_q06_release_blockers.py::test_q06_expired_session_status_is_localized_in_welcome_and_summary` |
| **`Q06-04`** | **Chặn demo Windows (P0)** | Root: [`run_demo.ps1`](../run_demo.ps1) | Trên Windows khi `agy` cài ngoài `PATH` và thành viên đặt `$env:ANTIGRAVITY_EXECUTABLE = "$env:LOCALAPPDATA\agy\bin\agy.exe"` theo đúng `README.md`, `run_demo.ps1` vẫn hardcode `Get-Command agy` và `& agy models`, làm script báo lỗi thiếu `agy` ngay khi khởi động (hoặc gọi nhầm shim `.cmd`/`.bat` mà `AntigravityProvider` từ chối). | Bổ sung `Resolve-AntigravityExecutable` trong `run_demo.ps1`: ưu tiên `$env:ANTIGRAVITY_EXECUTABLE` (kiểm tra đuôi `.exe`), tiếp đến `Get-Command agy` (`.exe`), rồi fallback `$env:LOCALAPPDATA\agy\bin\agy.exe` (tự export `$env:ANTIGRAVITY_EXECUTABLE` cho `uvicorn`) và chạy `& $agyExe models`. | `test/test_q06_release_blockers.py::test_q06_run_demo_script_resolves_configured_antigravity_exe` |

---

## 3. Bảng kiểm cổng bàn giao (Release Gate Checklist)

| Hạng mục kiểm tra | Trạng thái | Lệnh / Bằng chứng đối chiếu |
| --- | :---: | --- |
| Ranh giới kiến trúc MVC-S (`Model`, `service`, `Control`, `view`, `main.py`) | **Đạt** | Kiểm tra AST tự động trong `test/test_q06_release_blockers.py::test_q06_mvcs_layer_import_boundaries_hold` (0 vi phạm). |
| Bảo toàn câu trả lời gốc khi lỗi provider & phục hồi retry không tạo điểm `0` | **Đạt** | `test/Control/test_evaluations.py`, `test/Control/test_interview_flow.py`, `test/view/workspace_recovery.test.cjs`, `test/view/q06_recovery.test.cjs`. |
| Tính điểm xác định bằng Python (`E05`/`E06`), phân biệt `score: null` ≠ `0` | **Đạt** | `test/service/test_scoring.py`, `test/service/test_evidence_validation.py`, `test/test_api_contract.py`. |
| Phiên 4 câu hoàn chỉnh, kết thúc sớm, tổng kết, bài tập & luyện lại biến thể khác | **Đạt** | `test/Control/test_interview_flow.py`, `test/Control/test_session_summary.py`, `test/service/test_recommendations.py`, `test/view/q05_ui_interactions.test.cjs`. |
| Ngân hàng seed nguồn mở đã duyệt (8 câu hỏi, 5 bài tập, có giấy phép/SHA) | **Đạt** | `uv run --locked python -m source.service.question_bank_service --database .local/interview-q06-check.sqlite3` (`blocked: false`). |
| Không lộ khóa API, `.env`, `.local/`, `*.sqlite3` hay dữ liệu sinh viên thật | **Đạt** | `test/test_q07_docs_and_env.py`, `test/test_config.py`, kiểm tra `git status --short` trước khi bàn giao. |
| Hợp đồng API P04 không sai lệch sau khi sửa lỗi | **Đạt** | `test/test_api_contract.py` (không sửa đổi `source/Control/schemas.py`). |

---

## 4. Giới hạn còn lại & Hạng mục mở cho Q07 / Q08 (Ghi nhận trung thực)

Các mục sau **chưa được xem là hoàn tất** và phải nêu minh bạch trong báo cáo `Q08` và buổi thuyết trình:

1. **Kiểm định độ chính xác AI (`C07` / `Q03`):** Bộ 24 câu trả lời tổng hợp `C07` hiện chỉ có nhãn nháp (`candidate_judgment`, `0/12` ca held-out được 2 người gán nhãn độc lập và phân xử). Do đó **không tuyên bố tỷ lệ đồng thuận độ chính xác** của `gemini-3.8-flash-medium` cho tới khi hoàn tất 2 lượt gán nhãn độc lập và biên bản phân xử.
2. **Độ trễ tổng của Antigravity khi bật retry tự động (`Q03`):** Một ca held-out (`C07_C02_02`) mất `234,23s` khi cho phép 1 retry tự động; `run_demo.ps1` mặc định đặt `GEMINI_MAX_RETRIES=0` để giới hạn mỗi lần thử ở `120s` và để người học chủ động bấm *"Thử đánh giá lại"*.
3. **Xác nhận cài đặt trên máy sạch (`Q07` Bước 3):** Cần một thành viên khác tự chạy cài đặt, import seed và thử luồng theo `README.md` và `docs/demo_script.md` trên checkout sạch rồi điền bảng mục 6 của [demo_script.md](demo_script.md#6-clean-machine-verification-checklist-q07-step-3).
4. **Kiểm tra trình duyệt độc lập & `P3` (`Q04`/`Q05`):** Cần xác nhận thực tế lại `UI-05` (vị trí cuộn trang review) và mức phóng to 200% trên Chrome/Edge độc lập khi tổng duyệt `Q08`; lượt người thử `P3` là tùy chọn bổ sung.
5. **Giới hạn thiết kế đã chấp nhận cho MVP:**
   - Phạm vi cố định **Backend Developer · Intern/Fresher · Tiếng Việt · 4 câu hỏi/phiên** (`Q05-01` chuyển sang backlog sau MVP `X01+`).
   - Bản nháp chưa nộp lưu bằng `sessionStorage` chỉ tồn tại trong tab trình duyệt hiện tại (`UI-06`, đã ghi chú rõ cạnh ô nhập liệu).
   - Chế độ `fixture` mang nhãn **Dữ liệu minh họa** chỉ dùng để kiểm tra luồng phần mềm ngoại tuyến, không chứng minh chất lượng đánh giá AI (`UI-07`).

---

## 5. Lệnh tái hiện kiểm tra Q06 & Q08

Chạy từ thư mục gốc repository trên PowerShell cục bộ:

```powershell
# 1. Bộ test Q06, Q07, Q08 và toàn bộ View
uv run --locked python -m pytest test/test_q06_release_blockers.py test/test_q07_docs_and_env.py test/test_q08_release_package.py test/view/ -q

# 2. Bộ test hành vi JavaScript bằng Node.js
node --test test/view/workspace_recovery.test.cjs test/view/q05_ui_interactions.test.cjs test/view/q06_recovery.test.cjs

# 3. Toàn bộ bộ pytest ngoại tuyến (không cần khóa API)
uv run --locked python -m pytest -q

# 4. Kiểm tra import seed C08 trên SQLite mới
uv run --locked python -m source.service.question_bank_service --database .local/interview-q08-release.sqlite3
```

---

## 6. Cổng chốt Release & Tổng duyệt thuyết trình (Q08)

> [!NOTE]
> Các mục đánh dấu **Chờ chốt** dưới đây chỉ chuyển sang **Đạt** sau khi nhóm chốt commit demo cuối cùng, chạy lại kiểm tra và tổng duyệt trực tiếp. Không tự điền trước kết quả chưa chạy.

### 6.1. Hồ sơ chốt commit phát hành (Release Freeze)

| Hạng mục chốt release | Trạng thái | Ghi nhận thực tế (điền khi chốt) |
| --- | :---: | --- |
| Commit demo đã chốt (`git rev-parse --short HEAD`) | Chờ chốt | Điền mã SHA sau khi merge PR vào `main` |
| Toàn bộ `uv run --locked python -m pytest -q` trên commit nhánh tích hợp | **Đạt** (trên `Demo-fix`) | `248 passed, 3 skipped` (chạy lại lần cuối sau khi merge PR) |
| Toàn bộ 3 tệp `node --test` (`workspace_recovery`, `q05_ui_interactions`, `q06_recovery`) | **Đạt** (trên `Demo-fix`) | `15 passed, 0 failed` |
| Kiểm tra import seed `C08` trên SQLite mới (`blocked: false`) | **Đạt** (trên `Demo-fix`) | `4 skills, 9 sources, 8 rubrics, 8 questions, 5 exercises`, `issues: []` |
| Kiểm tra live Antigravity (`DEMO_LIVE_TEST=1`, `E09_LIVE_TEST=1`) trên máy trình chiếu | Chờ chốt | Chạy xác nhận ngay trước giờ trình chiếu |
| Kiểm tra `git status --short` sạch (không track `.local/`, `.env`, `*.sqlite3`) | **Đạt** (trên `Demo-fix`) | Không có khóa API hay cơ sở dữ liệu cục bộ nào bị theo dõi |
| Xác nhận cài đặt trên máy sạch bởi thành viên khác (`Q07` Bước 3) | Chờ chốt | Theo dõi tại [demo_script.md](demo_script.md#6-clean-machine-verification-checklist-q07-step-3) |

### 6.2. Bảng kiểm tổng duyệt Demo 5 chặng (Q08 Bước 3)

| Chặng demo | Điều kiện kiểm chứng khi tổng duyệt | Trạng thái |
| --- | --- | :---: |
| **1. Mở phiên 4 câu** | Trang `/` hiển thị lịch sử sạch (hoặc nhãn phiên dễ đọc `UI-03`), `/setup` tạo phiên 4 câu phủ 4 nhóm với cookie `HttpOnly`. | Chờ chốt |
| **2. Nguồn mở & bản quyền** | Chỉ ra nhãn giấy phép nguồn mở (`PSF-2.0`, `PostgreSQL`, `MIT`, `CC-BY-SA-4.0`) và đối chiếu [QUESTION_PROVENANCE_HANDOFF.md](QUESTION_PROVENANCE_HANDOFF.md). | Chờ chốt |
| **3. Chấm điểm & Căn cứ (`null` ≠ `0`)** | Chọn từng tiêu chí để tô sáng trích dẫn nguyên văn trong bài làm; minh họa `Chưa đủ bằng chứng` giữ `score: null` và không bịa điểm tổng. | Chờ chốt |
| **4. Lỗi provider & Retry giữ bài** | Minh họa `504 PROVIDER_TIMEOUT` (hoặc bằng chứng đo thực tế) giữ nguyên văn bản trên SQLite, `total_score=null` và nút **Thử đánh giá lại** hoạt động trên workspace/review. | Chờ chốt |
| **5. Tổng kết, Bài tập & Luyện lại** | Mở tổng kết phiên (`completed` / `ended_early`), xem thẻ bài tập đã gom (`UI-01`) kèm lý do/tiên quyết/thời lượng ước tính và tạo phiên luyện 1 câu bằng biến thể khác (`I06`). | Chờ chốt |

### 6.3. Bảng kiểm tính trung thực của Slide & Báo cáo cuối

- [x] [docs/final_report.md](final_report.md) đã bao gồm sơ đồ kiến trúc MVC-S (Mermaid), minh chứng 4 trụ cột Tư duy tính toán gắn với mã nguồn, nguồn gốc 5 kho nguồn mở, ví dụ rubric `case.c03.inventory_race.v1` và số liệu thực tế từ `Q03`/`Q04`/`Q05`/`Q06`.
- [x] Phân biệt rõ **tính năng đã làm (MVP)**, **phần mở rộng hoãn (`X01–X12`)**, và **giả thuyết chưa kiểm chứng** (`C07` chưa có nhãn phân xử cho `Q03`, không dự đoán kết quả tuyển dụng, không tuyên bố chứng nhận toàn bộ WCAG).
- [ ] Đối chiếu lại toàn bộ con số trên slide cuối cùng khớp 100% với kết quả chạy trên commit chốt release.