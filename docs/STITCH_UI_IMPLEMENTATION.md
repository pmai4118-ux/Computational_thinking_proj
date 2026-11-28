# Bàn giao UI Stitch và lộ trình Java Backend

Cập nhật 27/11/2026. UI đã tích hợp vào app FastAPI/Jinja hiện tại. Học liệu đọc từ catalog, không dán dữ liệu mẫu trong HTML thành kết quả của người học.

## Những phần đã hoạt động

- Shell chung toàn app (không sidebar trái toàn cục): header dính trên cùng dạng kính mờ với thanh điều hướng pill (`Trang chủ`, `Phỏng vấn ảo`, `Lộ trình Java`, `Lịch sử phiên`), bố cục đồng nhất khoảng 80% chiều rộng cửa sổ trên desktop (`min(82vw, 110rem)` từ breakpoint `75rem`), nền tím nhạt phủ toàn màn hình trên mọi trang và xếp lưới thanh điều hướng `2×2` gọn trên mobile mà không tràn ngang.
- Lộ trình `/learning-path`: banner **Kiểm tra đầu vào** (*Kiểm tra kiến thức nền tảng Backend Java*) đọc trạng thái thật từ `/api/profile` và dẫn sang `/setup`; bên dưới là banner *Lộ trình cá nhân hóa*, danh sách năm chặng (sidebar chặng nội trang), node/card zigzag, tìm kiếm không dấu và cửa sổ chi tiết bài học (`#lesson-dialog`) theo mẫu `lesson-detail` (thẻ đọc đánh số, nút nguồn, nút tích hoàn thành bên phải lưu cục bộ, khối thực hành áp dụng, khóa học tham khảo mở rộng và footer dính).
- Catalog đủ **24 lesson, 78 bài học nhỏ, 48 bài thực hành**; mỗi lesson mở tất cả link bài đọc và bài tập, cùng metadata nguồn, điều kiện truy cập và khóa tham khảo.
- Modal cấu hình mục tiêu & quỹ thời gian (`#learning-settings`) theo mẫu Stitch *Luminous Violet Glass*: thanh accent đầu modal, chọn nhanh chip mục tiêu (`foundation` / `backend` / `advanced`), tab chế độ ưu tiên (`full_track` / `confirmed_gaps`), khối timeline bắt đầu / dự kiến hoàn tất + 4 mốc tuần (`4`, `8`, `12`, `24` tuần), 5 mức quỹ giờ/tuần (`4`, `8`, `12`, `15`, `20` giờ) kèm ô nhập tùy chỉnh và ước tính tổng giờ; gọi API `/api/learning-paths/plan` hiện có. Hủy hoàn nguyên form, lỗi giữ lựa chọn, thiếu giờ vẫn hiển thị bài hoãn.
- Đánh dấu học xong là tự khai, lưu trong trình duyệt theo catalog version. Kế hoạch gần nhất lưu cùng phiên bản; thay tiến độ sẽ nhắc xác nhận/tạo lại. Sidebar chặng duyệt toàn catalog, bài ngoài kế hoạch có nhãn riêng; lịch chi tiết dùng thứ tự Service trả về.
- Các màn phỏng vấn được đồng bộ theo shell chung 80% không sidebar và font Be Vietnam Pro: trang chủ 2 cột hero + thông tin cấu trúc phiên, hub thiết lập 3 bước cân lề, workspace có khung luận điểm toàn chiều rộng shell, trang kết quả với hai tab rubric/toàn văn và highlight bằng chứng, màn **Tổng kết phiên** (`/sessions/{id}/summary`) theo mẫu `session-summary` tối giản đa sắc (thẻ tổng quan glass, lưới 4 trục năng lực, thẻ từng câu với icon gradient theo loại câu hỏi + ngăn căn cứ đóng/mở), cùng trang bài tập và lịch sử phiên. Giữ điều phối đánh giá cuối phiên và chế độ phản hồi từng câu hiện có.
- **Be Vietnam Pro** cho nội dung/tiêu đề theo yêu cầu mới của người dùng; Space Grotesk dành cho một số metadata. Bản thiết kế HTML gốc vẫn giữ font gốc để bảo toàn nguồn.
- Hover card có viền tím/glow/nâng nhẹ; nút và sidebar có phản hồi hover/focus. Người dùng chọn giảm chuyển động sẽ không bị ép animation.

## File và ranh giới kiến trúc

| Thành phần | File |
|---|---|
| Shell/Header/Footer | `source/view/templates/base.html`, `partials/icons.html`, `static/css/components.css` |
| UI lộ trình | `source/view/templates/learning_path.html`, `static/css/learning_path.css`, `static/js/learning_path.js`, `static/css/stitch.css` |
| Font/tokens | `source/view/static/css/tokens.css`, font stylesheet trong `base.html` |
| UI phỏng vấn hiện tại | `setup.html`, `workspace.html`, `answer_review.html`, `summary.html`, `exercise.html`, `history.html`; CSS/JS tương ứng trong `source/view/static/` |
| Dữ liệu học liệu | `data/learning/java_backend_v1.json` |
| Kế hoạch | `source/service/learning_path_service.py` qua `/api/learning-paths/plan` |

Đợt UI này tập trung ở **View**: trình bày, tương tác và trạng thái trình duyệt. Giữ Model/Controller/Service, schema chấm điểm và quyền truy cập hiện có. Không tạo kế hoạch hay điểm số bằng LLM trong client. Kết quả rubric vẫn do Service tính; đổi tab không gọi đánh giá lại.

## Chỗ thiết kế được điều chỉnh theo phạm vi thật

1. Thay JD/upload CV bằng lựa chọn mục tiêu Java; không khôi phục tính năng import JD đã bỏ.
2. Lịch hiện theo **tuần và giờ/tuần**. Chưa có lịch từng ngày/khung giờ, nhắc lịch hoặc đồng bộ Calendar.
3. Tiến độ tự khai không phải điểm năng lực/chứng chỉ. Không dùng 78/100, lịch sử hay tên người mẫu từ ảnh để giả dữ liệu thật.
4. Bài thực hành ngoài app không trở thành câu phỏng vấn có rubric. Ngân hàng phỏng vấn chưa được chuyển thành ngân hàng Java chuyên biệt.
5. Các control ngoài phạm vi như Voice AI/adaptive hints không được bật giả. HTML/PNG nguồn vẫn giữ nguyên; app dùng dữ liệu và trạng thái hỗ trợ thật.
6. Bản xem thử dùng provider **fixture**, có nhãn dữ liệu minh họa. Đây là kiểm tra giao diện/luồng; không chứng minh chất lượng phản hồi của provider AI thật.

## Bằng chứng kiểm tra

- Bộ Python ngoại tuyến đầy đủ: **270 passed, 3 skipped** (AI live opt-in không bật); nhóm View, lộ trình và hợp đồng liên quan: **56 passed**.
- JavaScript (`node --test test/view/*.test.cjs`): **26 passed, 0 failed**, gồm hồi quy lưu/retry, hoạt động tiến độ, khung luận điểm và xử lý quote Unicode/chồng lấn/XSS literal.
- Playwright (`scripts/check_stitch_ui.cjs` qua server fixture nội bộ): xác nhận không còn `#app-sidebar` / `#sidebar-toggle`, nền tím toàn viewport, căn lề header/main/footer (~80% chiều rộng trên `1920px`), điều hướng top nav hiển thị trên desktop & mobile, banner Kiểm tra đầu vào (`/setup`), modal cấu hình (track chips, tabs ưu tiên, preset giờ/tuần, hủy hoàn nguyên, phục hồi lỗi), mở cả **24 lesson / 78 units / 48 practices** cùng nút tích hoàn thành bên phải lưu qua reload, trang tổng kết đa sắc với nút mở/thu gọn căn cứ, nháp khung luận điểm và hai mode phỏng vấn; `pageErrors: []`.
- Viewport kiểm tra không tràn ngang (`scrollWidth === innerWidth`): lộ trình `320–1920px`; hub, review và trang chủ `320–1920px`. Kiểm tra bàn phím cho tab kết quả và modal (`Escape`); đây là kiểm tra có phạm vi, không phải chứng nhận toàn bộ WCAG.

Lệnh kiểm thử trong repo:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
uv run --locked python -u -m pytest -q
node --test test/view/*.test.cjs
```

Bài smoke trình duyệt có thể chạy lại: `scripts/check_stitch_ui.cjs`. Chỉ chạy với app `EVALUATION_PROVIDER=fixture`; script kiểm tra nhãn demo trước khi tạo phiên. Cần Playwright có thể import bằng Node (`PLAYWRIGHT_MODULE_PATH` nếu nằm ngoài repo), `CHROME_PATH` nếu dùng Chrome có sẵn, và `STITCH_PREVIEW_URL` khi đổi cổng. Kết quả/ảnh ghi vào `../outputs/stitch-ui` hoặc `STITCH_OUTPUT_DIR`. Chưa commit/push/deploy công khai trong công việc này.


## Cập nhật loading và phạm vi ôn tập

Đã bổ sung [loading UX và gỡ luyện câu khác](LOADING_UX_HANDOFF.md).
Bài làm có trạng thái lưu/đối chiếu/tải kết quả và phục hồi khi lỗi;
không còn nút hoặc API tạo lượt luyện bằng câu hỏi khác.
