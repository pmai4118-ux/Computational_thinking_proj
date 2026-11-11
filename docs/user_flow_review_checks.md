> **Lịch sử trước revision UI-2026-11-10.2.** Mô tả chỉ văn bản/hoãn voice ở dưới không còn là phạm vi hiện hành. Xem [USE_CASES.md](USE_CASES.md), [PROJECT_SPEC.md](PROJECT_SPEC.md) và [Sơ đồ P02](../p02-user-flow.html). Không dùng kiểm tra cũ làm bằng chứng cho yêu cầu mới.

# Kiểm tra bản review user flow — 10/11/2026

Trạng thái: sẵn sàng để người dùng review, chưa có xác nhận phê duyệt nghiệp vụ.

## Đã kiểm tra

- `node docs/build_user_flow_review.cjs`: tạo đủ 34 mã duy nhất; mọi action target
  và journey reference tồn tại; mỗi màn hình có Back, lưu dữ liệu và nhánh lỗi.
- `node --check docs/build_user_flow_review.cjs`: không có lỗi cú pháp.
- `git diff --check -- docs/user_flow.md docs/ui_direction.md`: không có lỗi whitespace.
- Chrome headless trên Windows, desktop 1440 × 1050: mở lần lượt 34 màn hình,
  đúng tiêu đề, số hành động và form ghi chú của từng mã.
- Mở 12 walkthrough và 12 form quyết định; không có ID DOM trùng sau render.
- Tìm kiếm I04 lọc đúng mục điều hướng.
- Trạng thái Cần sửa và ghi chú còn nguyên sau reload; ký tự HTML được giữ như text.
- Nút Xuất ghi chú tạo nội dung JSON có đúng metadata và ý kiến review.
- Mobile viewport 390 × 844, trang I04 không tràn ngang; đã xem ảnh desktop/mobile.
- Không ghi nhận JavaScript runtime exception trong lượt kiểm tra hoàn tất.
- Ghi chú thử nghiệm được xóa khỏi profile browser QA sau kiểm tra.

## Giới hạn

Đây là kiểm tra tài liệu/reader HTML, không kiểm tra backend interviewUS, provider,
SQLite, tính điểm, XP, xóa dữ liệu thật hoặc prototype Figma. Chưa kiểm tra đầy đủ
screen reader, keyboard-only, mọi breakpoint/theme hoặc in PDF. Không đánh dấu
nghiệp vụ được người dùng duyệt chỉ vì reader hoạt động.

Các thay đổi user flow chưa commit/push. Bản demo rubric hẹp vẫn được lưu riêng
trong `user_flow_interview.md`; quyết định full-product nằm ở `user_flow.md`.
