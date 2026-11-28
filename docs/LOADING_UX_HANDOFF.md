# Loading UX và gỡ luyện với câu hỏi khác

Triển khai theo yêu cầu ngày 27/11/2026, dựa trên UI violet/glass và font Be Vietnam Pro hiện có.

## Hành vi đã tích hợp

- Card loading có vòng sáng, skeleton và chuyển động nhẹ; button hiện spinner và chặn gửi lặp khi đang xử lý.
- Phân biệt **đang lưu**, **AI đang đối chiếu** và **đang tải kết quả**. Chỉ báo bài đã lưu sau khi API lưu xác nhận. Vùng nhập tạm khóa trong lúc gửi để nội dung không bị thay đổi giữa chừng.
- Loading xuất hiện sau 120ms nếu công việc vẫn đang chạy, tránh nhấp nháy với phản hồi nhanh. Không trì hoãn hiển thị kết quả để chạy hết animation.
- Tiến độ tổng kết lấy số câu đã có kết quả thực từ response; thời gian chờ không làm tăng phần trăm. Từng câu chưa có số liệu tiến độ dùng thanh indeterminate.
- Màn review tự đọc kết quả bằng GET mỗi 5 giây. Dừng khi xong/lỗi hoặc sau 150 giây, giữ bài và cho tải lại. Không tự POST evaluate khi polling.
- Summary giữ giới hạn hai yêu cầu đánh giá đồng thời; gộp các lượt tải summary chồng nhau để giảm trạng thái nhấp nháy do response về khác thứ tự.
- Modal tạo kế hoạch và trang học liệu dùng cùng loading. Hủy khi đang tạo kế hoạch sẽ bỏ qua response đến muộn, giữ kế hoạch trước đó.
- Giữ thông báo `aria-live` sẵn có, dùng skeleton trang trí ẩn với screen reader và tắt animation khi người dùng chọn reduced motion.

## Tính năng đã gỡ

Đã bỏ toàn bộ nút/luồng tạo lượt luyện bằng câu hỏi khác. Service không còn chọn biến thể hoặc tạo session một câu cho chức năng này. JavaScript client không còn `startPractice`.

Endpoint cũ `POST /api/sessions/{sid}/answers/{aid}/practice` vẫn nhận biết client legacy: kiểm tra quyền sở hữu rồi trả **410 FEATURE_RETIRED**, `retryable=false`; không tạo session. Hai field availability trong DTO tương thích luôn false. Hướng dẫn ôn tập vẫn lấy từ nguồn đã duyệt. Không xóa các bài làm/phiên lịch sử.

## Thành phần và hợp đồng

- View dùng `source/view/static/js/activity.js` và `static/css/activity.css`, được nạp trước JS của từng trang trong `templates/base.html`.
- Đã nối vào workspace, review, summary, setup, hướng dẫn ôn tập và lộ trình/modal kế hoạch.
- Controller/API retirement nằm ở `source/Control/exercise_controller.py`; mã lỗi trong `schemas.py`.
- Service gỡ tính năng ở `recommendation_service.py`; `session_report_service.py` chỉ còn đề xuất hướng dẫn/học liệu, không gợi ý tạo câu hỏi khác.
- Hợp đồng cập nhật tại `api_contract.md`, `data_contract.md` và mục 8 của `PROJECT_SPEC.md` tại workspace.

Phân rã: lưu bài, đối chiếu, đọc kết quả và phục hồi. Nhận diện mẫu: dùng chung activity controller cho các trang. Trừu tượng hóa: trạng thái request và số câu hoàn tất từ server, tách khỏi điểm rubric. Thuật toán: polling GET có giới hạn và bỏ qua response kế hoạch đã hủy.

## Kiểm tra thực chạy

- Python ngoại tuyến: **270 passed, 3 skipped**; không bật AI live opt-in.
- Node: **26 passed**. Có ca xác minh loading nhanh không nhấp nháy, timer được dọn, thời gian không làm tăng tiến độ và review dừng polling sau 150 giây.
- Playwright với fixture và response được giữ/trả lỗi có kiểm soát: lưu → AI đối chiếu → kết quả; khóa ô nhập khi lưu; unknown progress; mobile; mở lại processing và tự GET; lỗi provider rồi retry; batch 0/2 → 1/2 → hoàn tất; UI/API đã gỡ; hủy request kế hoạch; reduced motion.
- Không có page error trong luồng kiểm tra. Ảnh và JSON ở `../../outputs/loading-ux/`; kiểm tra UI dùng fixture, không đánh giá chất lượng provider AI thật.

Lệnh chạy lại:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -u -m pytest -q
node --test test/view/*.test.cjs
```

Smoke trình duyệt: `scripts/check_loading_ux.cjs`. Cần Playwright cho Node (có thể đặt `PLAYWRIGHT_MODULE_PATH`), Chromium hoặc `CHROME_PATH`; chỉ chạy trên preview dùng `EVALUATION_PROVIDER=fixture`. `STITCH_PREVIEW_URL` mặc định cổng 8011, `LOADING_OUTPUT_DIR` mặc định `../outputs/loading-ux`. Bài kiểm tra xác minh nhãn demo trước khi tạo phiên.
