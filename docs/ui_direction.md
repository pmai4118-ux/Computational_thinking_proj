# P02 — Ghi chú UI cho luồng demo

Người thực hiện: **Qthynhh** · 09/11/2026. Đây là đầu vào để P06 review, không
phải xác nhận đã hoàn tất wireframe, canvas hay UI chạy được.

## 1. Reference và quyết định

Reference là [Purple Glass UI/UX](https://www.figma.com/design/IAFdJtqvSdDrfFHbtxZHxs?node-id=5-403)
và hồ sơ Figma trong workspace. Mapping frame và hạn chế xác minh nằm ở
[user_flow.md](user_flow.md#6-đối-chiếu-thiết-kế-figma).

Giữ nhận diện **interviewUS**, màu tím và bề mặt glass có chọn lọc. Ưu tiên
đọc đề, nhập bài và đọc điểm. Kết quả hiện ngay sau mỗi câu. Không có nhận xét
điểm mạnh/yếu, lời khuyên lộ trình, microphone hay lời hứa đậu phỏng vấn.

## 2. Bố cục đề xuất

```text
S01 — Bắt đầu                   S02 — Thiết lập
[Tên demo + phạm vi]            [Backend Java] [Fresher]
[Bắt đầu luyện tập]             [Chủ đề] [Lý thuyết / Case]
[Tiếp tục nếu có phiên]         [Tóm tắt + Xác nhận bắt đầu]

S03 — Workspace desktop
┌───────────────────────────────────────────────────────────┐
│ Phỏng vấn Java · Câu i/N       Trạng thái lưu     Thoát     │
├──────────────────────────┬────────────────────────────────┤
│ Tiêu đề, chủ đề, nguồn    │ Câu trả lời của bạn            │
│ Nội dung đề, constraints │ [textarea có label]            │
│ Code chỉ đọc nếu có      │ [Gửi câu trả lời]              │
└──────────────────────────┴────────────────────────────────┘

S04 — Panel kết quả (sau khi gửi)
[Nguyên văn bài đã gửi — chỉ đọc]
[Tiêu chí | Điểm / điểm tối đa hoặc trạng thái chưa có điểm]
[Tổng điểm / điểm tối đa nếu evaluator cung cấp]
[Câu tiếp theo]                         [Kết thúc phiên]

S05 — Tổng kết
[Các câu và điểm tương ứng] [Số câu chưa đánh giá]
[Mở lại kết quả] [Bắt đầu phiên mới] [Về đầu]
```

S03/S04 có thể cùng một trang, chuyển composer thành read-only sau submit thành
công. Đề dài cuộn được nhưng không che nút gửi. Mobile xếp đề → bài làm → kết quả;
không ép hai cột hoặc dùng bảng điểm rộng hơn viewport.

## 3. Token khởi điểm từ brief đã có

| Token | Giá trị | Công dụng |
| --- | --- | --- |
| canvas | `#F5F3FA` | Nền |
| surface | `#FFFFFF` | Đề, textarea, bảng điểm |
| subtle | `#EDE9FE` | Vùng chọn hoặc hỗ trợ |
| primary / hover | `#7C3AED` / `#6D28D9` | Nút chính |
| text / secondary | `#211A32` / `#625A73` | Nội dung / metadata |
| teal | `#0D9488` | Accent hỗ trợ, không thay nhãn trạng thái |

Dùng Be Vietnam Pro nếu có sẵn, fallback system sans-serif hỗ trợ tiếng Việt;
không yêu cầu cài font. Nội dung đề/bài cỡ khoảng 16px, giãn dòng thoải mái; code
dùng monospace. Glass dành cho header hoặc bề mặt phụ, textarea/điểm dùng nền đặc.
Đây là giá trị từ brief để P06 kiểm tra contrast thực tế, chưa phải chứng nhận WCAG.

## 4. Component và nội dung trạng thái

| Component | Trạng thái bắt buộc |
| --- | --- |
| Setup | Có dữ liệu, thiếu trường, bank rỗng, đang tạo, tạo thất bại |
| Composer | Trống, đang nhập, lỗi validation, đang gửi, lưu lỗi, đã gửi chỉ đọc |
| Save indicator | Chưa lưu, đang lưu, đã lưu server, lỗi; bản nháp cục bộ ghi nhãn riêng |
| Evaluation panel | Đang đánh giá, lỗi có retry, có điểm, thiếu bằng chứng |
| Next action | Disabled khi chưa hoàn tất, đang chuyển, lỗi chuyển, câu cuối |
| Summary | Đủ kết quả, chưa có điểm ở một số câu, kết thúc sớm, lỗi tải |
| Exit / expired | Xác nhận rời khi có draft, save failure, hết quyền có đường quay lại |

Nhãn chính: “Bắt đầu luyện tập”, “Xác nhận bắt đầu”, “Gửi câu trả lời”,
“Thử lưu lại”, “Thử đánh giá lại”, “Câu tiếp theo”, “Kết thúc phiên”. Không dùng
“Đã lưu” khi chỉ giữ trong bộ nhớ trình duyệt. Không hiển thị max/tổng điểm giả
trong lúc MelBel chưa chốt contract.

## 5. Keyboard và responsive cần kiểm tra khi có UI

- Mọi input có label; trạng thái gửi/lưu/lỗi được thông báo bằng text, không chỉ màu.
- Tab đi theo thứ tự đề → textarea → gửi → kết quả → hành động tiếp; focus rõ.
- Không chặn phím Enter xuống dòng trong textarea. Chỉ submit qua nút hoặc phím
  tắt có mô tả khi nhóm quyết định bổ sung.
- Sau lỗi, đưa focus tới thông báo/trường cần sửa; sau khi đánh giá xong, thông
  báo kết quả sẵn sàng, không tự chuyển câu.
- Cần kiểm tra width 360px và zoom 200% khi implementation tồn tại. P02 chưa thực
  hiện kiểm thử responsive/keyboard của một ứng dụng chạy được.

## 6. Review tiếp theo

P06 cần đối chiếu canvas theo frame links, chốt component/responsive, bổ sung
prototype lỗi/retry. P04 chốt giới hạn input, draft/exit và contract điểm với MelBel.
Không mở rộng P02 thành redesign toàn bộ sản phẩm hoặc triển khai Python.
