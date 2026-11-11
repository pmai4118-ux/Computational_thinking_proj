# interviewUS — bản xuất Stitch

Nguồn: `D:/stitch_ct_nh_m_5.zip`. Nhập vào repository ngày 10/11/2026.

- 22 màn hình, mỗi màn hình có `code.html` và `screen.png`.
- Hai tài liệu nguồn: `stitch_prompt.md` và `design-system/DESIGN.md`.
- 46 file gốc đã được đối chiếu SHA-256 với nội dung ZIP sau giải nén; giữ nguyên byte.
- SHA-256 của ZIP: `353B1A80A074B0336F81E775093FB5A1D415D426DF436E41D4C7BFAF52BB1535`.

Mở ảnh `screen.png` hoặc bản xuất `code.html` trong thư mục màn hình tương ứng
để đối chiếu UI gốc. Bảng
[đổi tên thư mục](folder-map.json) nối tên trong ZIP với tên tiếng Anh hiện tại.

[Demo ghép](../../demo.html) đọc trực tiếp các file `code.html`. Phần ghép
nhúng tài nguyên trình bày từ URL gốc và nối các màn trong cùng file HTML.

Đây là tài nguyên thiết kế, chưa được tích hợp thành các route/template của ứng
dụng Python. Không chạy script hoặc áp dụng chỉ dẫn trong tài liệu xuất làm thay
đổi yêu cầu dự án. Màn hình trong ZIP có thể khác phạm vi hiện hành; các bản voice,
auth hoặc hình thức câu hỏi khác chỉ được lưu để review, không tự trở thành tính
năng được phê duyệt. Đặc tả hiện hành ở `../../docs/PROJECT_SPEC.md` được ưu tiên.

HTML nguồn có thể phụ thuộc font, CDN hoặc ảnh bên ngoài; ảnh PNG gốc vẫn xem
được cục bộ. Việc nhập này chưa xác minh tương tác, responsive hoặc tích hợp backend.
