# Kiểm tra khả dụng và theo dõi sửa lỗi giao diện (Q04 & Q05)

Tài liệu này gom hai phần riêng biệt:
1. **Phần A (Q05):** Danh sách vấn đề phát hiện từ quan sát người dùng (`docs/user_observations.md`) cùng task sửa có bằng chứng.
2. **Phần B (Q04 — Chưa thực hiện):** Khung kiểm tra màn hình hẹp 360px, phóng to 200% và thao tác hoàn toàn bằng bàn phím (giữ trạng thái chờ để không tuyên bố hoàn thành Q04 trước khi kiểm tra thật).

---

## Phần A — Task sửa từ quan sát người dùng (Q05)

### Bảng theo dõi vấn đề và hành động sửa

| Mã | Mức độ | Nguồn | Tầng MVC-S & File | Cách tái hiện trước khi sửa | Thay đổi đã áp dụng | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| `Q05-02` | P1 (Cao) | `P1` | View: `workspace.html`, `workspace.css` | Mở `/sessions/{id}` ở màn hình laptop; phần `.workspace-topline` và `.workspace-progress` tách tầng + textarea `22rem` đẩy nút **Gửi câu trả lời** xuống dưới nếp gấp màn hình. | Gộp `Câu X / Y`, `<progress>` và `N câu đã có kết quả` vào một thanh header gọn; giảm khoảng đệm đầu trang và điều chỉnh `min-height` vùng nhập (`15rem`) để thao tác chính dễ thấy hơn. | Đã sửa + test hồi quy |
| `Q05-03` | P1 (Cao) | `P1` | View: `components.css` | Mở câu hỏi có mã Python (như `def append_audit_event...`); khối `.code-block` có nền sáng trùng card và không tự xuống dòng khi dòng quá dài. | Chuyển `.code-block` sang nền tối độ tương phản cao (`#1A1626` / chữ `#F5F3FF`), bật `white-space: pre-wrap` và `overflow-wrap: anywhere` để không bị cắt mất nội dung dòng dài. | Đã sửa + test hồi quy |
| `Q05-04` | P1 (Cao) | `P1` | View: `workspace.html`, `workspace.css`, `components.css` | Ở workspace, **Gửi câu trả lời**, **Xem tổng kết phiên** và **Kết thúc sớm** đều có kích thước lớn tương đương trong cùng khối `.action-row`. | Tách rõ vùng hành động chính (chỉ giữ nút đặc nổi bật **Gửi câu trả lời**) khỏi hàng tiện ích phụ dùng kiểu `.btn--ghost` gọn hơn cho **Xem tổng kết phiên** và **Kết thúc sớm**. | Đã sửa + test hồi quy |
| `Q05-05` | P1 (Cao) | `P1` | View: `workspace.js`, `workspace.css` | Nhập dở câu trả lời trong workspace rồi bấm **Bắt đầu** hoặc **Thiết lập phiên** trên Navbar; trình duyệt rời trang ngay không có xác nhận. | Làm dịu liên kết Navbar khi ở trong workspace và gắn cơ chế xác nhận rời trang (`confirm` / `beforeunload`) khi đang có bản nháp chưa nộp hoặc phiên đang xử lý, đồng thời thông báo rõ bản nháp cục bộ chưa được lưu lên máy chủ. | Đã sửa + test hồi quy |
| `Q05-06` | P1 (Cao) | Audit | View: `welcome.html` | Kết thúc sớm một phiên rồi quay về `/`; danh sách lịch sử hiện badge `ended_early` tiếng Anh và nút **Xem phiên** dẫn vào workspace rỗng. | Hiển thị nhãn tiếng Việt **Đã kết thúc sớm** và trỏ nút **Xem tổng kết** của các phiên không còn `in_progress` thẳng tới `/sessions/{id}/summary`. | Đã sửa + test hồi quy |
| `Q05-07` | P1 (Cao) | Audit | View: `answer_review.html` | Sau khi chấm bài, trang `/sessions/{id}/review` có hai nút `btn--primary` cạnh tranh nhau và không có liên kết mở thẳng tổng kết phiên. | Giữ duy nhất nút **Câu tiếp theo** (hoặc **Hoàn tất phiên**) là `btn--primary`, chuyển **Xem bài tập theo điểm thiếu** sang `btn--secondary` và bổ sung liên kết **Xem tổng kết phiên**. | Đã sửa + test hồi quy |
| `Q05-08` | P2 (TB) | Audit | View: `exercise.js`, `exercise.html` | Mở `/sessions/{id}/exercises?skill_id=...` với kỹ năng không có bài khớp; thông báo nhắc xem toàn bộ nhưng không có liên kết quay lại; badge kỹ năng hiển thị `skill.*`. | Bổ sung liên kết **Xem toàn bộ bài tập của phiên** khi đang lọc hoặc rỗng do bộ lọc; ánh xạ `skill.*` đã biết sang tên kỹ năng tiếng Việt dễ hiểu (giữ fallback nếu gặp mã mới). | Đã sửa + test hồi quy |
| `Q05-09` | P2 (TB) | Audit | View: `summary.js`, `summary.html` | Mở `/sessions/{id}/summary` khi có điểm thiếu; danh sách từng câu in mã kỹ thuật thô `confirmed_gap_criterion_ids`. | Đối chiếu tên tiêu chí tiếng Việt từ `observed_gaps` để hiển thị dễ đọc trong thẻ từng câu (vẫn giữ `confirmed_gap_criterion_ids` làm nguồn ánh xạ). | Đã sửa + test hồi quy |
| `Q05-10` | P2 (TB) | Audit | View: `workspace.js`, `evidence.js` | Thông báo trống ở `evidence.js` chứa từ `"workspace"`; nhãn sau khi lưu ở `workspace.js` thiếu đồng nhất với `docs/ui_direction.md`. | Chuẩn hóa thành `"trang câu hỏi"` và `"Đã lưu câu trả lời trên máy chủ"`. | Đã sửa + test hồi quy |
| `Q05-01` | Hoãn (Post-MVP) | `P1` | Scope / Content / API (`P01`, `C01`, `P04`, `X01`) | Người thử muốn tùy chọn 4/6/8/10 câu thay vì cố định 4 câu. | **Không thay đổi trong MVP:** phạm vi `P01` cố định 4 câu phủ 4 nhóm với ngân hàng seed hiện tại gồm 8 câu đã duyệt. Chuyển sang backlog mở rộng sau cổng release (`X01+`). | Hoãn rõ ràng (Ngoài MVP) |

### Lệnh kiểm tra sau khi sửa (Q05)

Chạy tại thư mục gốc repository:

```powershell
uv run --locked python -m pytest test/view/test_q05_usability_fixes.py test/view/ -q
node --test test/view/workspace_recovery.test.cjs
uv run --locked python -m pytest -q
```

### Giới hạn còn lại của Q05
- Hiện mới có **1 biên bản thực tế (`P1`)**; cần thêm ít nhất 1–2 người chưa quen giao diện (`P2`, `P3`) thử lại trên bản đã sửa để xác nhận các điểm vướng mắc của `P1` đã được giải quyết hoàn toàn và không phát sinh hiểu nhầm mới.
- Không thay đổi hợp đồng API (`source/Control/schemas.py`), không thay đổi quy tắc tính điểm Python (`E05`/`E06`), giữ nguyên ngữ nghĩa `score: null` khác `0`.

---

## Phần B — Kiểm tra màn hình hẹp, phóng to 200% và bàn phím (Q04 — Chờ thực hiện)

> [!IMPORTANT]
> **Trạng thái Q04: Chưa thực hiện.** Bảng dưới đây là khung kiểm tra dành riêng cho task `Q04`; không khẳng định đạt Q04 hay tuân thủ WCAG cho đến khi kiểm tra trực tiếp trên trình duyệt và ghi đầy đủ bước tái hiện.

- [ ] Luồng hoàn chỉnh ở độ rộng `360px` không tràn ngang toàn trang và không cắt điều khiển chính.
- [ ] Phóng to trình duyệt `200%` đọc được đề bài, khối code, bảng tiêu chí và nút hành động.
- [ ] Điều hướng hoàn toàn bằng bàn phím (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`) qua toàn bộ màn hình `S01 → S06`.
- [ ] Kiểm tra hiển thị focus (`:focus-visible`), nhãn form (`<label>`), thông báo trạng thái (`role="status"` / `role="alert"`), chọn tiêu chí xem căn cứ và nút retry khi lỗi provider.