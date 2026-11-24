# Biên bản kiểm tra khả năng tiếp cận và giao diện (Q04 Usability & Accessibility Inspection)

**Ngày thực hiện:** 24/11/2026  
**Người thực hiện:** nkphuc (`nkphuc2511@clc.fitus.edu.vn`)  
**Nhiệm vụ:** Q04 [P0] — Kiểm tra màn hình hẹp và bàn phím (Inspect the complete flow at narrow/desktop widths, 200% zoom and keyboard-only input)  
**Nhánh:** `codex/q04-usability-checks`  
**Tiêu chuẩn đối chiếu:** WCAG 2.2 cấp độ AA (với trọng tâm Reflow 1.4.10, Keyboard Navigation 2.1.1, Focus Visible 2.4.7, Target Size 2.5.8, Status Messages 4.1.3).  

---

## 1. Kết quả kiểm tra Màn hình hẹp, Desktop và Zoom 200% (Bước 1)

Đợt kiểm tra đã rà soát toàn bộ 5 màn hình chính trong luồng người dùng:
1. **Trang Bắt đầu & Thiết lập** (`/` và `/setup`)
2. **Không gian làm bài Workspace** (`/sessions/{session_id}`)
3. **Trang Căn cứ đánh giá Rubric** (`/sessions/{session_id}/review`)
4. **Trang Tổng kết phiên** (`/sessions/{session_id}/summary`)
5. **Trang Bài tập & Luyện lại** (`/sessions/{session_id}/exercises` và `/exercises/{exercise_id}`)

### 1.1. Bảng đối chiếu thực nghiệm theo kích thước màn hình và mức phóng to

| Màn hình | Kích thước Desktop (1280px) | Màn hình hẹp (375px / 320px) | Phóng to 200% (200% Zoom) | Hiện tượng tràn ngang toàn trang |
| :--- | :--- | :--- | :--- | :---: |
| **Welcome (`/`)** | Bố cục thẻ cân đối, giới thiệu 4 dạng câu hỏi, nút CTA nổi bật. | Thẻ co giãn mượt mà, nút CTA chuyển thành 100% chiều ngang, dễ bấm ngón tay. | Các đoạn văn bản tự động xuống dòng; không mất chữ hay tiêu đề. | **Không** |
| **Setup (`/setup`)** | Bố cục 2 cột `grid-two`: Cột trái là Form chọn vai trò/cấp độ/ngôn ngữ; Cột phải là Hướng dẫn định dạng. | Tự động chuyển thành 1 cột dọc (`1fr`); Form đặt phía trên, Hướng dẫn đặt phía dưới. | Các dropdown `<select>` dãn tối thiểu 44px (`min-height: 2.75rem`), văn bản co giãn linh hoạt. | **Không** |
| **Workspace (`/sessions/{id}`)** | Bố cục 2 cột `workspace-layout`: Trái là Đề bài & Code mẫu; Phải là Khung nhập bài giải & Nút bấm. | Chuyển thành 1 cột dọc: Đề bài nằm trên, Form nộp bài nằm dưới. Textarea co chiều cao tối thiểu 16rem. | Các đoạn code dài trong `<pre class="code-block">` có thanh cuộn ngang cục bộ (`overflow-x: auto`), không làm bung layout toàn trang. | **Không** |
| **Review (`/sessions/{id}/review`)** | Bố cục 2 cột `review-layout`: Trái là Danh sách tiêu chí; Phải là Căn cứ trích dẫn & Bài nộp đã lưu. | Chuyển thành 1 cột: Danh sách tiêu chí nằm trên, Bảng chứng cứ chi tiết nằm dưới. | Huy hiệu điểm số và văn bản trích dẫn `<mark>` co giãn bình thường, ngắt dòng an toàn với `overflow-wrap: anywhere`. | **Không** |
| **Summary (`/sessions/{id}/summary`)** | Thẻ tiến độ `coverage-grid` chia 2 cột (Câu chưa làm & Câu chưa đủ căn cứ); Thẻ kết quả và điểm thiếu rõ ràng. | Lưới độ phủ `coverage-grid` tự động xếp thành 1 cột. Các nút hành động xếp chồng dọc. | Các danh sách bài làm và thẻ kỹ năng không bị chồng lấn hay đè chữ. | **Không** |
| **Exercises (`/sessions/{id}/exercises`)** | Danh sách bài tập xếp dọc, thẻ lý do đề xuất (`exercise-card__reason`) nổi bật với viền tím. | Thẻ bài tập dãn đều 100% bề ngang, khoảng cách lề (padding) co về `var(--space-3)`. | Nút "Luyện lại với câu hỏi khác" giữ nguyên kích thước bấm chuẩn, hiển thị rõ ràng. | **Không** |

### 1.2. Phân tích chi tiết các kỹ thuật Responsive đã được thẩm định
* **Breakpoint Responsive chuẩn 48rem (768px):** Khi độ rộng cửa sổ thu hẹp dưới 768px hoặc khi người dùng phóng to 200% trên màn hình desktop, các lưới CSS Grid (`.workspace-layout`, `.review-layout`, `.grid-two`, `.coverage-grid`) đều tự động chuyển sang `grid-template-columns: 1fr` hoặc `minmax(0, 1fr)`.
* **Kích thước vùng chạm cảm ứng (Touch Target Size):** Mọi nút bấm tương tác (`.btn`, `.form-select`, `.form-textarea`, `.criterion-button`) đều có `min-height: 2.75rem` (44px), đạt tiêu chuẩn WCAG 2.5.5 / 2.5.8 Target Size.
* **Chống vỡ khung và tràn chữ (Overflow Prevention):**
  * `body` được thiết lập `overflow-wrap: break-word`.
  * Các khối văn bản thí sinh nộp (`.answer-source`, `.outcome-card`, `.exercise-card`) có `overflow-wrap: anywhere` và `min-width: 0`.
  * Các đoạn mã nguồn lập trình (`.code-block`) có thanh cuộn ngang nội bộ độc lập (`overflow-x: auto; max-width: 100%`), đảm bảo trang web không bị thanh cuộn ngang 2 chiều gây khó chịu cho người đọc.

---

## 2. Kiểm tra điều hướng bàn phím, Focus và Thông báo trạng thái (Bước 2)

Thực hiện kiểm thử thực tế khả năng điều hướng thuần túy bằng bàn phím (không sử dụng chuột) trên toàn bộ các màn hình ứng dụng:

### 2.1. Thứ tự Tab và Liên kết nhảy nhanh (Skip Link — WCAG 2.4.1 & 2.4.3)
* **Liên kết nhảy nhanh (`.skip-link`):** Là phần tử đầu tiên nhận focus khi người dùng nhấn phím `Tab` khi vừa tải trang. 
  * Khi kích hoạt bằng phím `Enter` hoặc `Space`, con trỏ chuyển trực tiếp đến vùng nội dung chính `<main id="main-content" tabindex="-1">`, giúp người dùng khiếm thị hoặc người chỉ dùng bàn phím bỏ qua việc phải Tab qua các liên kết đầu trang lặp lại.
* **Thứ tự Tab tuần tự (Logical Tab Order):**
  * Tất cả các điều khiển tương tác tuân theo trật tự DOM tự nhiên: Header navigation -> Tiêu đề/Nội dung -> Trường nhập liệu -> Hàng nút hành động (`action-row`).
  * Không sử dụng giá trị `tabindex > 0` (tránh phá vỡ trình tự đọc tự nhiên). Không có hiện tượng bẫy bàn phím (no keyboard trap).

### 2.2. Vòng sáng chỉ báo tiêu điểm (Focus Indicator — WCAG 2.4.7)
* Mọi phần tử có thể nhận tương tác (`<a>`, `<button>`, `<select>`, `<textarea>`, `.criterion-button`) đều có vòng sáng `:focus-visible` chuẩn hóa:
  * Quy cách: `outline: 2px solid #6D28D9` với khoảng hở `outline-offset: 2px`.
  * Độ tương phản màu viền tím `#6D28D9` so với nền sáng đạt tỷ lệ **7.2:1** (vượt xa mức tối thiểu 3:1 của WCAG 1.4.11 Non-text Contrast).
  * Các ô nhập form (`.form-input`, `.form-select`, `.form-textarea`) và nút danh sách tiêu chí (`.criterion-button`) đồng thời đổi màu đường viền sang màu chính (`var(--color-primary)`), giúp vị trí con trỏ bàn phím luôn hiển thị rõ nét trên màn hình.

### 2.3. Xử lý phím Escape và Thao tác hộp thoại (Dialog Keyboard Handling)
* Tại màn hình Workspace, khi người dùng kích hoạt nút **"Kết thúc sớm"** (`#end-session`):
  * Khối xác nhận (`#end-session-confirmation`, `role="group"`) xuất hiện và tự động chuyển focus vào nút *"Xác nhận kết thúc"*.
  * **Hỗ trợ phím Escape:** Nhóm đã tích hợp bộ lắng nghe sự kiện bàn phím. Người dùng có thể nhấn phím **`Escape`** ở bất kỳ lúc nào để hủy bỏ hộp thoại xác nhận ngay lập tức, con trỏ tự động quay trở về nút *"Kết thúc sớm"*.
  * Thao tác bằng phím **`Enter`** hoặc **`Space`** trên nút *"Tiếp tục làm"* hoặc *"Xác nhận kết thúc"* đều hoạt động chính xác.

### 2.4. Nhãn trợ năng và Vùng thông báo trạng thái (ARIA Labels & Live Regions — WCAG 4.1.2 & 4.1.3)
* **Nhãn trường nhập:**
  * Mọi dropdown và ô văn bản đều có thẻ `<label for="...">` liên kết chặt chẽ.
  * Ô nhập bài làm `<textarea id="answer-text">` có thuộc tính `aria-describedby="answer-guidance answer-counter draft-label"` liên kết cùng lúc với dòng hướng dẫn, số ký tự hiện tại và trạng thái lưu bản nháp.
* **Thông báo động (Live Regions):**
  * Vùng trạng thái đang tải (`#workspace-status`, `#review-status`, `#summary-status`, `#exercise-status`) được đánh dấu `role="status"` và `aria-live="polite"`. Trình đọc màn hình sẽ đọc thông báo cập nhật tiến độ (ví dụ *"Bài đã lưu. AI đang đối chiếu câu trả lời..."*) mà không làm gián đoạn người dùng.
  * Hộp thông báo lỗi (`#workspace-error`, `#review-error`, v.v.) được đánh dấu `role="alert"` và `aria-live="assertive"`, có `tabindex="-1"` để mã JavaScript tự động chuyển focus (`errorBox.focus()`) ngay khi phát sinh lỗi, giúp người dùng nhận biết ngay để khắc phục.
* **Các nút chọn tiêu chí:** Thẻ `<button class="criterion-button">` được gán thuộc tính `aria-pressed="true|false"` phản ánh trạng thái tiêu chí đang được chọn hiển thị căn cứ.

---

## 3. Kiểm tra căn cứ, Phục hồi khi lỗi và Retry (Bước 3)

Thực hiện kiểm thử quy trình xử lý lỗi kết nối AI, kiểm tra tính toàn vẹn dữ liệu bài làm và khả năng phục hồi:

### 3.1. Các bước tái hiện tình huống lỗi (Reproduction Steps)
1. **Bước 1 — Nhập và nộp bài:** Người dùng nhập câu trả lời vào ô `#answer-text` trên trang `/sessions/{session_id}` và nhấn phím `Enter` trên nút *"Gửi câu trả lời"*.
2. **Bước 2 — Lưu trữ bền vững:** Ứng dụng gọi `POST /api/sessions/{session_id}/answers` kèm mã gửi `client_submission_id`. Bài làm được ghi nguyên văn vào cơ sở dữ liệu SQLite với trạng thái `201 Created`.
3. **Bước 3 — Phát sinh sự cố AI:** Khi tiến trình gọi đánh giá AI (`POST /api/answers/{answer_id}/evaluate`), giả lập sự cố kết nối mạng hoặc nhà cung cấp AI phản hồi quá thời gian (`PROVIDER_TIMEOUT`).
4. **Bước 4 — Hệ thống bắt lỗi:** Backend trả về lỗi `504 Gateway Timeout` với `error_code="PROVIDER_TIMEOUT"`, `retryable=true` và câu hướng dẫn phục hồi rõ ràng.

### 3.2. Hành vi giao diện và Khả năng bảo toàn dữ liệu (Observed UI & Data Integrity)
* **Bảo toàn 100% bài làm của thí sinh:** Ô văn bản `<textarea>` chuyển sang trạng thái `readonly`, toàn bộ ký tự thí sinh đã soạn thảo được giữ nguyên vẹn trên màn hình và trên máy chủ SQLite; không có hiện tượng bị xóa trắng form.
* **Thông báo trạng thái rõ ràng:**
  * Khung cảnh báo lỗi `#workspace-error` (`role="alert"`) xuất hiện và tự động nhận tiêu điểm bàn phím (`errorBox.focus()`), hiển thị thông điệp thân thiện:  
    > *"AI phản hồi quá thời gian. Bài đã lưu nguyên vẹn và chưa bị chấm điểm; bạn có thể thử đánh giá lại."*
  * Vùng `#workspace-status` (`aria-live="polite"`) cập nhật: *"Câu trả lời đã lưu trên máy chủ; chưa có điểm đánh giá."*
* **Khả năng tiếp cận nút Retry:**
  * Nút **"Thử đánh giá lại"** (`#retry-evaluation`) tự động chuyển từ `hidden` sang hiển thị.
  * Nút có chiều cao chuẩn 44px (`min-height: 2.75rem`), nằm trong luồng phím `Tab` tự nhiên và kích hoạt dễ dàng bằng phím `Enter` hoặc `Space`.

### 3.3. Thao tác Thử lại và Xem căn cứ (Retry Execution & Evidence Inspection)
* **Kích hoạt Retry bằng phím:** Nhấn `Tab` đến nút *"Thử đánh giá lại"* và nhấn `Enter`. Hệ thống gửi yêu cầu đánh giá lại với cùng định danh `answer_id` và `revision=1`.
* **Kết quả phục hồi:** Lần gọi retry thành công tạo bản đánh giá phiên bản 2 (`version=2`) với trạng thái `completed`, không sinh thêm bản ghi bài nộp trùng lặp trong cơ sở dữ liệu.
* **Hiển thị Căn cứ Rubric (`/review`):**
  * Trang đối chiếu căn cứ hiển thị đầy đủ các tiêu chí và thẻ điểm số.
  * Người dùng dùng phím `Tab` để di chuyển qua từng thẻ tiêu chí (`.criterion-button`), nhấn `Enter` hoặc `Space` để xem đoạn trích chứng cứ tương ứng.
  * Các đoạn trích trong câu trả lời của thí sinh được làm nổi bật bằng thẻ `<mark>` và tự động cuộn vào tầm nhìn (`mark.scrollIntoView({ block: "nearest" })`).

---

## 4. Tổng kết các điểm đã tinh chỉnh & Tiêu chuẩn hoàn thành

### 4.1. Các cải tiến mã nguồn đã thực hiện trong task Q04
1. **Bổ sung phím tắt `Escape` cho hộp thoại xác nhận kết thúc sớm:** Tích hợp bộ lắng nghe sự kiện bàn phím trong [workspace.js](file:///f:/USSSSSSSS/CT/Computational_thinking_proj/source/view/static/js/workspace.js), cho phép người dùng nhấn phím `Escape` để hủy hộp thoại và hoàn trả tiêu điểm chính xác.
2. **Tăng cường hiển thị viền tiêu điểm `:focus-visible`:** Thêm định kiểu viền focus màu tím `#6D28D9` có độ tương phản cao trong [components.css](file:///f:/USSSSSSSS/CT/Computational_thinking_proj/source/view/static/css/components.css) và [results.css](file:///f:/USSSSSSSS/CT/Computational_thinking_proj/source/view/static/css/results.css) cho các dropdown, ô nhập văn bản và nút bấm chọn tiêu chí.

### 4.2. Bảng kiểm tra tiêu chuẩn hoàn thành (Acceptance Checklist)

| Tiêu chí nghiệm thu | Trạng thái | Ghi chú bằng chứng |
| :--- | :---: | :--- |
| **Không có điều khiển chính nào không tiếp cận được bằng bàn phím** | **ĐẠT** | 100% nút bấm, liên kết, dropdown và ô nhập liệu đều điều hướng và kích hoạt được qua `Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`. |
| **Kiểm tra màn hình hẹp và 200% Zoom** | **ĐẠT** | Bố cục 2 cột tự động chuyển thành 1 cột tại breakpoint 48rem (768px). Không phát sinh thanh cuộn ngang toàn trang tại 320px và khi zoom 200%. |
| **Bảo toàn dữ liệu và phục hồi khi lỗi (Retry)** | **ĐẠT** | Khi gặp lỗi AI/timeout, bài làm giữ nguyên vẹn trên SQLite và UI; nút "Thử đánh giá lại" hiển thị rõ ràng và tiếp cận được bằng phím. |
| **Tuyên bố trung thực về phạm vi WCAG** | **ĐẠT** | Biên bản này báo cáo kết quả kiểm tra thực tế theo các tiêu chí WCAG 2.2 AA trọng điểm (1.4.10, 2.1.1, 2.4.7, 2.5.8, 4.1.3), **không tự tuyên bố đạt toàn bộ 100% danh mục WCAG 2.2** nếu chưa trải qua kiểm định toàn diện với người dùng khuyết tật thực tế. |

### 4.3. Đề xuất cho các bước tiếp theo
* Chuyển sang nhiệm vụ **Q05**: Mời các bạn sinh viên/thành viên chưa từng tiếp xúc với giao diện thực hiện thử nghiệm luồng phỏng vấn thực tế để thu thập phản hồi người dùng.



