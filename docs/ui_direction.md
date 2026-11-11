# P06 — Định hướng UI và wireframe tương tác interviewUS

Cập nhật 10/11/2026. Chỉ thực hiện **P02 + P06**, không triển khai backend, sửa hợp đồng/spec/backlog hoặc commit. Trạng thái: bản thiết kế có thể review; chưa coi người dùng/nhóm đã duyệt nghiệp vụ. Tham chiếu [P02 user flow](user_flow.md), [use case/nút](USE_CASES.md) và bộ UI ZIP được giữ nguyên nội dung tại [design/demo-web](../design/demo-web/IMPORT_README.md).

## 1. Đầu ra mở chính

[demo.html](../demo.html) ghép trực tiếp 22 file `code.html` trong [thư mục nguồn Stitch](../design/demo-web/IMPORT_README.md). Mỗi màn có khung riêng để giữ bố cục, CSS, font và JavaScript gốc. Tailwind, font và ảnh được nhúng để mở offline. Chọn **Chọn màn hình** ở góc dưới bên phải để mở mọi màn, kể cả các biến thể.

Các liên kết gốc và nút chính được nối giữa các màn. Nội dung đề, nhận xét, điểm số và tài khoản lấy từ bản mẫu Stitch. Thao tác ngoài luồng nối màn phụ thuộc vào phần JavaScript có sẵn trong từng file gốc. Các phần dưới đây mô tả thiết kế và hành vi dự kiến để nhóm review.

## 2. Hướng thiết kế

Giữ nhận diện violet/glass của ZIP, nhưng giảm lớp trang trí ở vùng đọc/soạn. Bố cục đề–luận điểm–chat là trọng tâm; không dùng trang dashboard mẫu thay cho công việc người học. Nội dung và trạng thái đều tiếng Việt có dấu. Thư mục màn hình dùng tên tiếng Anh ASCII để dễ đọc và tránh tên mất chữ; việc đổi tên không thay byte HTML/PNG gốc.

| Token | Giá trị | Mục đích |
| --- | --- | --- |
| Primary | #7434DF | Hành động chính, tab đang chọn |
| Primary dark | #5722B0 | Hover và nhấn mạnh chữ |
| Lavender | #EDE3FF | Tab/chip và nền trợ giúp |
| Background | #F8F6FC | Nền ứng dụng |
| Text | #272133 | Chữ chính |
| Muted | #746B80 | Thông tin phụ |
| Border | #E8E1F0 | Phân chia nội dung |
| Teal | #087B70 | Trạng thái đã lưu/hoàn tất mẫu |
| Error | #B54146 | Lỗi/thao tác cần xác nhận |

Font Segoe UI, fallback Arial/system sans-serif, hỗ trợ tiếng Việt và offline. Body 15–16px, heading 27–32px, nhãn 12–14px; text tối thiểu 10–12px chỉ ở metadata phụ. Bán kính khối 14–18px, điều khiển 8–12px; dùng màu chữ/trạng thái cùng nhãn, không chỉ màu sắc. Không hứa E2EE hoặc thành tích tuyển dụng từ ảnh.

## 3. Bố cục theo khu vực

| Khu vực | Desktop | Màn hình hẹp |
| --- | --- | --- |
| Câu hỏi | Rail lọc trái; tìm kiếm và lưới câu bên phải | Tìm kiếm + danh sách một cột; không cắt form |
| Workspace luyện/phiên | 70% đề, input selector, luận điểm, nút lưu/nộp; 30% chat | Tab Bài làm/Trợ lý, đổi tab giữ nháp |
| Lộ trình | Chặng trái; node học/tiên quyết và hành động phải | Chặng và node xếp dọc |
| Tổng quan | Việc hôm nay/lịch sử + lịch bên phải | Thống kê, hoạt động và lịch xếp dọc |
| Đăng nhập | 40% form, 60% nội dung/mascot | Giữ form, ẩn cột minh họa phụ |
| Đầu vào | Ba phần và navigator, form theo loại câu, trợ lý đúng phạm vi | Navigator xuống dòng, radio/textarea đầy đủ nhãn |

Breakpoint: 1180px thu điều hướng; 900px workspace/mobile tabs và form auth một cột; 600px thẻ/cột xếp dọc. Sơ đồ P02 có thể cuộn ngang riêng để giữ chữ đọc được; ứng dụng/form không tràn ngang toàn trang. Giảm chuyển động theo prefers-reduced-motion.

## 4. Component và tương tác phải review

- Điều hướng bằng hash trong cùng file; nút trong các khu vực dẫn đúng chi tiết, modal, workspace, kết quả, Tổng quan và lộ trình. Không dùng href="#" làm nút giả.
- Button chính/phụ/disabled, form có label, radio, chip chọn, editor block thêm/di chuyển/xóa có xác nhận, badge nháp/đã nộp.
- Modal xác nhận mục tiêu, xóa luận điểm, kết thúc sớm, nộp thiếu, đổi trạng thái tài khoản và đặt lại demo. Có Đóng/hủy; native dialog giữ focus trong modal.
- Ba nút độc lập: **Gửi chat**, **Dùng bản phiên âm**, **Nộp bài**. Mô phỏng ghi âm không xin mic; nội dung phiên âm được sửa/xác nhận rồi chèn vào luận điểm. Chuyển trang lúc còn bản ghi phải xác nhận.
- Chat: chip chỉ điền ô, Enter gửi/Shift+Enter xuống dòng, giới hạn gợi ý theo mode, tin trả về gắn đúng câu. Không làm thay đổi bài nộp.
- Chế độ Guided hiển thị kết quả mẫu từng câu; Simulation chỉ nhận bài và đi tiếp, tổng kết mới mở phản hồi. Không chấm bài thật.
- Đầu vào: ba loại câu, điều hướng giữ nháp, rà câu trống, xác nhận nộp thiếu, xem bài chỉ đọc sau nộp. Số 3 câu trong demo là bộ tối thiểu minh họa, không chốt blueprint sản phẩm.
- Tổng quan phản ánh thao tác demo vừa làm, tiếp tục đúng phiên/bài dở. Không kho audio; đọc văn bản đã xác nhận và luyện lại tạo lượt mới.
- Tình huống demo chọn được: bình thường, lỗi lưu, lỗi phản hồi AI, lỗi chat, lỗi phiên âm, từ chối mic. Nhánh lỗi phải giữ nháp/bài và có đường đi tiếp.

## 5. Dữ liệu demo và giới hạn

LocalStorage chỉ giữ trạng thái minh họa trong trình duyệt: nháp, các bài thử, tin chat theo kịch bản, tài khoản mẫu, dấu ôn tập và tiến độ. Không lưu mật khẩu. Có nút Đặt lại demo và xác nhận trước xóa. Không dùng dữ liệu người học thật khi review.

Tất cả đề, kết quả tự luận, phản hồi, lời trợ lý, kế hoạch và thao tác auth/voice đều được ghi nhãn mô phỏng. Đúng/sai choice chỉ đối chiếu đáp án mẫu của bộ wireframe, không phải engine đánh giá sản phẩm. Điểm rubric cố định phục vụ layout, không phản ánh nội dung vừa nhập. Ghi âm, gửi email, reset tài khoản và Google không diễn ra thật.

## 6. Checklist bàn giao P06

1. Một file mở chính chạy offline, không có request mạng hoặc dependency ngoài.
2. Sáu khu vực và các subview có đường chuyển/Back/hủy hợp lý; giữ bài khi quay lại.
3. Chọn câu, setup/mode, editor, modal, chat, voice confirmation, đầu vào ba phần, kết quả/lịch sử/lộ trình đều minh họa được.
4. Desktop 1440px và mobile 390px không tràn form; kiểm tra zoom 200%, bàn phím, focus và các trạng thái lỗi đại diện.
5. Token/wording tiếng Việt nhất quán; folder-map ghi tên cũ → mới; nội dung 46 file nguồn vẫn khớp ZIP.
6. Reviewer đối chiếu từng quy tắc với P02; ghi riêng phần chưa kiểm tra, không tự tuyên bố WCAG hoặc task triển khai đã Done.

Chạy `node design/build_demo.cjs` từ repo để tạo lại file demo. Trình ghép đọc `design/demo-web/*/code.html`, tài nguyên offline trong `design/stitch-assets.json` và quy tắc nối màn trong `design/stitch-navigation.js`. Chạy `node design/cache_stitch_assets.cjs` khi cần lấy lại tài nguyên gốc qua mạng.
