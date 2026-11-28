# Bộ thiết kế interviewUS — tên tiếng Anh

Chuẩn hóa từ `D:/stitch_ct_nh_m_5 (1).zip` và bổ sung 2 màn hình từ `stitch_ct_nh_m_5_(2).zip`, ngày 27/11/2026. Đã đổi tên thư mục và các file `code.html`/`screen.png` theo chức năng tiếng Anh; giữ nguyên byte của 17 file thiết kế gốc (`DESIGN.md` ở cả hai gói trùng SHA-256). Không dịch nội dung tiếng Việt trong giao diện.

Mở [trang xem thiết kế](index.html). Mỗi màn có HTML và ảnh tham chiếu:

| Màn hình | HTML | PNG |
|---|---|---|
| Cấu hình lộ trình | [roadmap-settings](roadmap-settings/roadmap-settings.html) | [Ảnh](roadmap-settings/roadmap-settings.png) |
| Lộ trình cá nhân hóa dạng zigzag | [personalized-roadmap](personalized-roadmap/personalized-roadmap.html) | [Ảnh](personalized-roadmap/personalized-roadmap.png) |
| Cửa sổ chi tiết bài học | [lesson-detail](lesson-detail/lesson-detail.html) | [Ảnh](lesson-detail/lesson-detail.png) |
| Hub thiết lập phỏng vấn | [interview-hub](interview-hub/interview-hub.html) | [Ảnh](interview-hub/interview-hub.png) |
| Không gian trả lời | [interview-workspace](interview-workspace/interview-workspace.html) | [Ảnh](interview-workspace/interview-workspace.png) |
| Kết quả: tổng quan rubric | [answer-review-overview](answer-review-overview/answer-review-overview.html) | [Ảnh](answer-review-overview/answer-review-overview.png) |
| Kết quả: bài đã lưu và nhận xét | [answer-review-detail](answer-review-detail/answer-review-detail.html) | [Ảnh](answer-review-detail/answer-review-detail.png) |
| Tổng kết phiên luyện tập | [session-summary](session-summary/session-summary.html) | [Ảnh](session-summary/session-summary.png) |

[Design system gốc](design-system/DESIGN.md) · [Đối chiếu tên cũ/mới và SHA-256](rename-manifest.json).

## Tài liệu để build

- [Đặc tả lộ trình cá nhân hóa kết hợp catalog Java](../../docs/JAVA_BACKEND_PERSONALIZED_ROADMAP_UI_BUILD.md).
- [Đặc tả thay UI phiên phỏng vấn](../../docs/INTERVIEW_UI_STITCH_BUILD.md).
- [Prompt giao AGY triển khai UI phỏng vấn](../../docs/AGY_INTERVIEW_UI_PROMPT.md).
- [Học liệu đầy đủ](../../docs/JAVA_BACKEND_ROADMAP.md) và [catalog có cấu trúc](../../data/learning/java_backend_v1.json).

## Cách dùng đúng bộ mẫu

HTML là nguồn bố cục/style để port vào app; PNG là ảnh đối chiếu. `DESIGN.md` bổ sung chỗ mẫu chưa quy định. Các màn có biến thể token, không thay toàn bộ màu từng màn bằng một màu mặc định từ YAML. Ưu tiên đặc tả dự án và dữ liệu thật cho hành vi/nội dung; số điểm, JD, tên người, lịch sử, badge AI và lời hứa chứng chỉ trong mẫu là nội dung minh họa.

HTML là prototype tĩnh, dùng Tailwind CDN, Google Fonts và icon bên ngoài; mở HTML cần mạng để có đủ style. PNG xem được ngoại tuyến. Không đưa nguyên Tailwind runtime CDN hoặc `href="#"` thành hành vi production. Bản tích hợp dùng FastAPI/Jinja và CSS/JS hiện có; không cần đổi framework.

Ảnh hub có vùng canvas đen rất dài sau footer. Giữ nguyên ảnh gốc để đối chiếu; không dựng vùng đen đó trong sản phẩm.

UI đã được tích hợp vào app theo yêu cầu tiếp theo; xem [bàn giao triển khai](../../docs/STITCH_UI_IMPLEMENTATION.md). App dùng Be Vietnam Pro theo yêu cầu mới, còn HTML/PNG nguyên bản vẫn giữ nguyên để đối chiếu.
