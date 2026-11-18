# P06 — Quy chuẩn UI, Wireframe và Design Tokens (trên nền P02)

| Thuộc tính | Nội dung |
| --- | --- |
| Mã công việc | P06 — Chốt wireframe và bộ quy chuẩn UI |
| Người thực hiện | Qthynhh (`member-2`, đầu vào P02) · hwngMP (`member-1`, chốt P06 & tokens) |
| Phụ thuộc | [P01 (`scope.md`)](scope.md), [P02 (`user_flow.md`)](user_flow.md), [P04 (`api_contract.md`)](api_contract.md) |
| Đầu ra | `docs/ui_direction.md`, [`docs/user_flow.md`](user_flow.md), [`source/view/static/css/tokens.css`](../source/view/static/css/tokens.css) |

---

## 1. Định hướng thẩm mỹ và nguyên tắc hiển thị

- **Nhận diện:** Giữ định hướng **interviewUS — Purple Glass UI/UX** ([Figma reference](https://www.figma.com/design/IAFdJtqvSdDrfFHbtxZHxs?node-id=5-403)), sử dụng nền sáng hơi tím (`#F5F3FA`) và bề mặt kính mờ (`backdrop-filter`) có chọn lọc cho thanh trạng thái/điều hướng.
- **Ưu tiên độ đọc cho văn bản kỹ thuật tiếng Việt:**
  - Khung đề bài, đoạn mã nguồn, ô nhập câu trả lời (`textarea`), đoạn trích dẫn bằng chứng (`evidence quote`) và bảng tiêu chí bắt buộc đặt trên nền đặc `#FFFFFF` để đảm bảo độ tương phản cao nhất.
  - Phông chữ ưu tiên `"Be Vietnam Pro"` kèm chuỗi fallback hệ thống hỗ trợ đầy đủ dấu tiếng Việt chồng tầng (`--line-height-relaxed: 1.65`, chiều dài dòng tối đa `72ch`).
- **Minh bạch trạng thái:**
  - Không dùng màu sắc đơn lẻ để báo trạng thái tiêu chí; mọi trạng thái (`Đạt`, `Chưa đạt`, `Chưa đủ bằng chứng`, `Lỗi đánh giá`) phải đi kèm nhãn văn bản tiếng Việt tường minh.
  - Khi chạy với `EVALUATION_PROVIDER=fixture`, thanh trạng thái hiển thị huy hiệu **`Dữ liệu minh họa`** để không nhầm với kết quả chấm từ AI thật.

---

## 2. Wireframe Desktop (`>= 768px`) và Màn hình hẹp (`360px` / `200% zoom`)

### 2.1. Màn hình Workspace (`S03`) và Kết quả đối chiếu căn cứ (`S04`) — Desktop

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ interviewUS · Phiên Backend Intern/Fresher · Câu 1/4   [Dữ liệu minh họa]     │
│ Trạng thái lưu: Đã lưu trên máy chủ (rev 1)                  [Kết thúc phiên] │
├─────────────────────────────────────┬─────────────────────────────────────────┤
│ CỘT TRÁI: ĐỀ BÀI & BÀI TRẢ LỜI GỐC  │ CỘT PHẢI: KẾT QUẢ RUBRIC & CĂN CỨ       │
│                                     │                                         │
│ [Tình huống kỹ thuật · Nguồn: MIT]  │ Tổng điểm câu: 5 / 6                    │
│ Kho còn một sản phẩm. Hai yêu cầu   │ (Chỉ hiển thị khi đủ căn cứ mọi tiêu chí)│
│ mua đến đồng thời tới hai instance… │                                         │
│                                     │ ▸ [Đạt · 2/2] c03.race                  │
│ Ràng buộc:                          │   Nhận ra thao tác tranh chấp           │
│ • DB dùng chung giữa các instance   │   [Xem căn cứ trên bài làm (ký tự 0–67)]│
│ • Tạo đơn lỗi phải rollback tồn kho │                                         │
│                                     │ ▸ [Đạt · 2/2] c03.atomicity             │
│ ─────────────────────────────────── │   Giữ bất biến tại dữ liệu chia sẻ      │
│ Bài trả lời đã lưu (chỉ đọc ở S04): │   [Xem căn cứ trên bài làm (193–294)]   │
│                                     │                                         │
│ "Hai yêu cầu có thể cùng đọc        │ ▼ [Chưa đạt · 1/2] c03.concurrent_tests │
│  stock=1 trước khi ghi...           │   Kiểm thử bất biến (ĐANG CHỌN)         │
│  ...==>[Em kiểm thử bằng hai luồng  │   Căn cứ trích dẫn:                     │
│  gửi đồng thời qua hai instance:    │   "Em kiểm thử bằng hai luồng gửi đồng  │
│  chỉ đúng 1 đơn thành công và       │    thời qua hai instance..."            │
│  stock = 0.]<=="                    │   Nhận xét: Có kiểm thử đồng thời nhưng │
│                                     │   chưa nêu kiểm thử chèn lỗi để xác nhận│
│                                     │   rollback tồn kho.                     │
│                                     │                                         │
│                                     │ [Câu tiếp theo]        [Kết thúc phiên] │
└─────────────────────────────────────┴─────────────────────────────────────────┘
```

### 2.2. Màn hình hẹp (`360px` / Mobile / Zoom `200%`)

Ở chiều rộng `< 768px` hoặc khi phóng to `200%`, bố cục chuyển về **một cột dọc** theo thứ tự ưu tiên nhiệm vụ, không cuộn ngang toàn trang và không cắt nút điều khiển:

```text
┌────────────────────────────────────┐
│ Phiên Backend · Câu 1/4            │
│ [Đã lưu trên máy chủ]  [Kết thúc]  │
├────────────────────────────────────┤
│ 1. ĐỀ BÀI & RÀNG BUỘC              │
│ Kho còn một sản phẩm...            │
│ (Khối code cuộn ngang riêng nếu dài)│
├────────────────────────────────────┤
│ 2. CÂU TRẢ LỜI CỦA BẠN             │
│ [Textarea có nhãn rõ ở S03 /       │
│  Văn bản đánh dấu căn cứ ở S04]    │
│ [Gửi câu trả lời] (rộng 100%)      │
├────────────────────────────────────┤
│ 3. KẾT QUẢ TỪNG TIÊU CHÍ (S04)     │
│ Tổng điểm câu: 5 / 6               │
│ ┌────────────────────────────────┐ │
│ │ [Chưa đạt · 1/2] Kiểm thử      │ │
│ │ Bấm "Xem căn cứ" -> cuộn mượt  │ │
│ │ tới đoạn trích trong bài làm   │ │
│ └────────────────────────────────┘ │
│ [Câu tiếp theo] (rộng 100%)        │
└────────────────────────────────────┘
```

### 2.3. Tương tác chọn tiêu chí để xem đúng căn cứ (`Evidence Navigation`)
- Mỗi thẻ tiêu chí trong `S04` là một nút/khối có thể focus bằng bàn phím (`Tab` / `Enter` / `Space`).
- Khi người học chọn một tiêu chí:
  1. Nếu tiêu chí có `quote` kèm `start_offset` và `end_offset`: vùng văn bản bài trả lời gốc làm nổi bật đúng đoạn `answer_text[start_offset:end_offset]` bằng lớp `--color-evidence-highlight-active-bg` (`#DDD6FE`) và viền trái `--color-evidence-highlight-border` (`#7C3AED`), đồng thời cuộn đoạn đó vào vùng nhìn thấy.
  2. Nếu tiêu chí chỉ có `observation` (ví dụ: ghi nhận phần nội dung bị bỏ qua hoặc viện dẫn tệp đính kèm vắng mặt): hiển thị hộp thông báo `"Quan sát trên toàn bài trả lời"` ngay dưới tiêu chí và giải thích lý do (`unresolved_reason` nếu `insufficient_evidence`), không tô sáng giả một đoạn văn bản không liên quan.

---

## 3. Hệ thống Design Tokens ([`source/view/static/css/tokens.css`](../source/view/static/css/tokens.css))

| Nhóm | Biến CSS | Giá trị | Mục đích sử dụng |
| --- | --- | --- | --- |
| **Bề mặt** | `--color-canvas` | `#F5F3FA` | Nền trang chính |
| | `--color-surface` | `#FFFFFF` | Nền thẻ đề bài, ô trả lời, bảng tiêu chí |
| | `--color-subtle` | `#EDE9FE` | Nền phụ, chip kỹ năng, vùng tóm tắt |
| **Thương hiệu** | `--color-primary` / `--color-primary-hover` | `#7C3AED` / `#6D28D9` | Nút hành động chính và viền tiêu chí đang chọn |
| | `--color-accent-teal` | `#0D9488` | Nhấn phụ cho thông tin tiến độ/nguồn mở |
| **Văn bản** | `--color-text` | `#211A32` | Văn bản chính (tỷ lệ tương phản `> 13:1` trên nền trắng) |
| | `--color-text-secondary` | `#584F6B` | Nhãn phụ, metadata nguồn (tỷ lệ tương phản `> 6.5:1`) |
| **Trạng thái tiêu chí** | `--color-status-met-*` | `#ECFDF5` / `#059669` / `#065F46` | Tiêu chí `met` (`Đạt`) |
| | `--color-status-unmet-*` | `#FEF2F2` / `#DC2626` / `#991B1B` | Tiêu chí `unmet` (`Chưa đạt`) |
| | `--color-status-unresolved-*` | `#FFFBEB` / `#D97706` / `#92400E` | Tiêu chí `insufficient_evidence` (`Chưa đủ bằng chứng`) |
| | `--color-status-error-*` | `#FFF1F2` / `#E11D48` / `#881337` | Lỗi lưu bài hoặc lỗi AI provider (`failed`) |
| **Đánh dấu căn cứ** | `--color-evidence-highlight-active-bg` | `#DDD6FE` | Đánh dấu đoạn trích nguyên văn đang được chọn |

---

## 4. Từ điển nhãn giao diện tiếng Việt chuẩn hóa

Mọi màn hình (`U01–U08`) dùng thống nhất một tên cho cùng một hành động và trạng thái:

| Ngữ cảnh | Nhãn chuẩn phải dùng | Nhãn/hành vi bị cấm |
| --- | --- | --- |
| Mở phiên mới ở `S01` / `S02` | `Bắt đầu luyện tập` / `Xác nhận bắt đầu` | Không thu thập CV hoặc thông tin cá nhân ngoài role/level |
| Ô nhập bài ở `S03` | `Câu trả lời của bạn` (có `<label for="...">`) | Không dùng `placeholder` thay cho `<label>` |
| Trạng thái bản nháp | `Bản nháp trên trình duyệt (chưa lưu máy chủ)` | Không báo `Đã lưu` khi mới lưu ở `sessionStorage` |
| Trạng thái lưu máy chủ | `Đã lưu câu trả lời trên máy chủ` | — |
| Nút gửi bài | `Gửi câu trả lời` (khi đang xử lý: `Đang gửi và đánh giá…`, khóa bấm trùng) | Không chặn phím `Enter` xuống dòng trong `textarea` |
| Tiêu chí thiếu căn cứ | `Chưa đủ bằng chứng` (hiển thị điểm: `Chưa xác định`) | Không hiển thị `0/2` khi `score: null` |
| Tổng điểm câu có tiêu chí `null` | `Chưa tính tổng điểm (còn tiêu chí chưa đủ bằng chứng)` | Không tự cộng các tiêu chí còn lại thành tổng điểm |
| Lỗi đánh giá từ provider | `Bài trả lời đã lưu. Chưa đánh giá được — bấm "Thử đánh giá lại"` | Không xóa nội dung bài hoặc biến lỗi mạng thành điểm `0` |
| Điều hướng sau kết quả | `Câu tiếp theo` / `Kết thúc phiên` / `Xem căn cứ trên bài làm` | Không tự động chuyển câu khi vừa chấm xong |

---

## 5. Quy tắc bàn phím, Focus và Trạng thái giao diện (`U01` / `Q04`)

1. **Điều hướng bàn phím:** Thứ tự `Tab` đi tuần tự: `Thanh tiến độ / Kết thúc phiên` → `Đề bài & Ràng buộc` → `Ô nhập câu trả lời` → `Gửi câu trả lời` → `Danh sách tiêu chí & Nút Xem căn cứ` → `Câu tiếp theo`.
2. **Focus rõ ràng:** Mọi phần tử tương tác hiển thị viền `--focus-ring: 2px solid #6D28D9` với `outline-offset: 2px` qua `:focus-visible`.
3. **Thông báo trạng thái động:** Vùng thông báo lưu bài, đang đánh giá và báo lỗi gắn `role="status"` hoặc `role="alert"` (`aria-live="polite"` / `"assertive"`), chuyển focus về thông báo lỗi hoặc trường cần sửa sau khi request thất bại.
4. **Tôn trọng giảm chuyển động:** Tự động tắt hiệu ứng chuyển cảnh và cuộn mượt khi hệ điều hành bật `prefers-reduced-motion: reduce`.
