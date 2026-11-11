# Biên bản kiểm tra P02 và P06 — 11/11/2026

Mở [demo.html](../demo.html) để thử ứng dụng và [p02-user-flow.html](../p02-user-flow.html) để xem sơ đồ. Hai file mở độc lập trong trình duyệt.

- P02 có sáu sơ đồ, 60 khối và 72 đường nối, kèm mô tả nút và đường phục hồi trong [USE_CASES.md](USE_CASES.md).
- P06 có sáu khu vực ứng dụng trong một HTML. P02 có sáu sơ đồ trong HTML riêng. Ảnh UI tham chiếu nằm trong thư mục nguồn.
- Chrome headless kiểm tra 23 tình huống, gồm luồng làm bài, giữ nháp, mở kết quả đúng thời điểm, tải lại giữ trạng thái, chọn khu vực và mở chi tiết của cả 60 khối P02.
- Ở 390 px, sáu khu vực ứng dụng và trang P02 đều vừa chiều ngang. Vùng sơ đồ cuộn ngang riêng. Lần kiểm tra không có lỗi JavaScript hoặc yêu cầu HTTP/HTTPS. Chưa thực hiện kiểm thử screen reader hay kiểm tra toàn bộ trình duyệt.
- Đổi 23 tên thư mục sang tiếng Anh theo folder-map. Đối chiếu SHA-256 từng file xác nhận cả 46 file nguồn vẫn khớp ZIP.

Thao tác xác thực, ghi âm, phản hồi và kết quả dùng dữ liệu mẫu. Phạm vi bàn giao là P02/P06, chờ nhóm review.

## Kiểm tra bản demo ghép từ Stitch

- Mở đủ 22 màn trên Chrome khi tắt mạng. Mỗi màn tải được CSS Tailwind và ảnh khai báo trong HTML. Lượt kiểm tra cuối ghi nhận 0 yêu cầu HTTP/HTTPS và 0 ngoại lệ JavaScript.
- Thử sáu bước chuyển giữa thư viện, chi tiết, luyện tập, phòng phỏng vấn, xác nhận nộp, kết quả và lộ trình. Nút ghi âm mô phỏng bật và tắt được sau khi bỏ qua hai trình xử lý trỏ vào nút không tồn tại trong bản xuất gốc.
- Đối chiếu ảnh thư viện và phòng phỏng vấn với ảnh Stitch. Bố cục và thành phần lấy trực tiếp từ bản xuất, hiển thị theo kích thước cửa sổ.
- Đối chiếu SHA-256 với ZIP. Cả 46 file nguồn khớp từng byte.
