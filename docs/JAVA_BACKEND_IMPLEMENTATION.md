# Lộ trình Java Backend — bàn giao ngày 27/11/2026

## Dữ liệu và đầu ra

- [Lộ trình bài đọc và bài tập](JAVA_BACKEND_ROADMAP.md): 24 lesson, 78 bài học nhỏ,
  48 bài thực hành, 87 nguồn và 10 chương trình/khóa học tham khảo.
- [Catalog JSON](../data/learning/java_backend_v1.json): dữ liệu có ID, phiên bản,
  kỹ năng, tiên quyết, nguồn, thời lượng và điều kiện truy cập.
- [Kiểm tra HTTP](JAVA_BACKEND_LINK_AUDIT.json): khả năng truy cập tại thời điểm
  kiểm tra; HTTP 200 không xác nhận toàn bộ khóa miễn phí hoặc có quyền sao chép.
- `/learning-path`: giao diện tích hợp trong app, có liên kết ở thanh điều hướng.

Phạm vi mở rộng đã được ghi ở mục 7 của `PROJECT_SPEC.md` theo yêu cầu mới của
người dùng. Phần học liệu cho phép bài thực hành local ở nguồn ngoài; không thêm
code runner, nhận bài code, điểm giả hoặc chứng chỉ vào phiên phỏng vấn.

## Cách phân loại nguồn

1. Oracle/Dev.java, Spring Guides, Microsoft Learn, MIT 6.102 Spring 2024 và
   Harvard CS50 SQL được đối chiếu từ trang chính thức; chỉ dẫn link và metadata.
2. Coursera IBM/Amazon/Duke dùng để tham khảo phạm vi chương trình. “Enroll for
   free” không chứng minh bài chấm, chứng chỉ hoặc toàn bộ khóa miễn phí.
3. Spring Academy: thông báo chính thức ngày 10/04/2024 công bố miễn phí sau
   đăng ký email phù hợp. Chưa đăng nhập thử lab hiện tại; mọi lesson bắt buộc
   đều có bài đọc/lab công khai khác.
4. MIT 2024 sử dụng TypeScript; chỉ dùng nguyên lý thiết kế/kiểm thử/concurrency.
   Khóa Java MIT cũ được liệt kê riêng, không gắn nhãn là phát hành 2024–2026.
5. Ngày kiểm tra và ngày công bố tách riêng. Tài liệu rolling không được tự điền
   năm xuất bản. Spring blog có bài 2024, 2025, 2026 và ghi đúng ngày nguồn.
6. Bài vận dụng do nhóm biên soạn có nhãn `project_original` và nguồn cơ sở;
   không giả là bài gốc của MIT/Microsoft/Coursera. Chưa có review độc lập để
   sử dụng chúng làm bài đánh giá có điểm.

## MVC-S và API

| Lớp | Thành phần | Vai trò |
|---|---|---|
| Model | `source/Model/learning_path.py` | Catalog, resource, course, unit, practice, lesson và request có xác nhận |
| Service | `source/service/learning_path_service.py` | Validate liên kết ID, DAG, chọn mục tiêu, sắp topo và phân bổ tuần |
| Service | `source/service/learning_path_export.py` | Xuất cùng catalog thành Markdown, không tạo lý thuyết riêng |
| Controller | `source/Control/learning_path_controller.py` | Đọc hồ sơ theo cookie và gọi Service; không nhận owner từ payload |
| View | `learning_pages.py`, template, CSS, JS | Form xác nhận, lesson có link, tiến độ tự khai, kế hoạch và tải file |

| Method | Endpoint | Hành vi |
|---|---|---|
| GET | `/learning-path` | Trang học Java Backend |
| GET | `/api/learning-paths/catalog` | Catalog công khai gồm nguồn và điều kiện truy cập |
| GET | `/api/learning-paths/markdown` | Tải Markdown từ cùng catalog |
| POST | `/api/learning-paths/plan` | Tạo kế hoạch tất định theo xác nhận và hồ sơ chủ cookie hiện tại |

Ví dụ request:

```json
{
  "track": "backend",
  "mode": "full_track",
  "hours_per_week": 8,
  "weeks": 12,
  "completed_lesson_ids": ["JB01"],
  "target_lesson_ids": [],
  "use_profile": true,
  "confirm_goal": true
}
```

`track`: `foundation`, `backend`, `advanced`.
`mode`: `full_track`, `confirmed_gaps`.
Target IDs tường minh có thể dùng để yêu cầu một nhóm bài cụ thể. ID không tồn
tại, ID lặp, thời gian không hợp lệ hoặc chưa xác nhận trả 422.

Response gồm `ordered_lessons`, `schedule`, `available_minutes`,
`total_estimated_minutes`, `shortfall_minutes`, `feasible` và `warnings`.
Một lesson có thể được chia qua nhiều tuần; bài phụ thuộc chỉ được xếp sau toàn
bộ thời lượng tiên quyết. Không đủ ngân sách vẫn giữ bài hoãn trong kết quả.

## Cá nhân hóa và giới hạn bằng chứng

- Kế hoạch dùng nội dung chọn bởi người học, bài tự đánh dấu và quỹ thời gian.
- Hồ sơ cũ chỉ nối kiến thức chuyển giao: `skill.backend.data_consistency` →
  JB15; `skill.algorithms.correctness_and_complexity` → JB06. Không nối kỹ năng
  ngữ nghĩa Python sang mức Java. Quan sát `insufficient_evidence` không thành
  nhãn yếu; không có điểm thiếu phù hợp thì dùng chặng đã xác nhận và giải thích.
- Ngân hàng 8 câu/rubric hiện hữu không bị chỉnh hoặc nhập lại. Có roadmap Java
  không đồng nghĩa đã có bài đánh giá Java chuyên biệt.
- Tiến độ tự đánh dấu lưu `localStorage` theo phiên bản catalog. Kế hoạch trả
  theo request và có thể tải JSON; chưa có bảng server riêng lưu kế hoạch.
- Hồ sơ đọc bằng hash cookie qua service hiện có. Payload không thể chọn owner
  khác. Lỗi đọc repository trả kế hoạch theo lựa chọn cùng cảnh báo; không mất
  các bài tự đánh dấu hoặc tự chuyển lỗi thành kết luận về năng lực.

## Tư duy tính toán

- Phân rã: nguồn → lesson → bài học nhỏ/bài tập → kế hoạch cá nhân.
- Nhận diện mẫu: dùng cùng schema và kiểm tra nguồn/tiên quyết cho mọi lesson.
- Trừu tượng hóa: ID/version, skill, access, thời lượng ước tính và bằng chứng
  chuyển giao; tách tự khai khỏi kết quả đánh giá.
- Thuật toán: mở rộng bao đóng tiên quyết, sắp topo có ưu tiên và chia ngân sách
  tuần; kết quả tái hiện được, không cần LLM tạo thứ tự hoặc số phút.

## Tái tạo và kiểm tra

```powershell
.\.venv\Scripts\python.exe scripts/curate_java_roadmap.py
.\.venv\Scripts\python.exe scripts/export_java_roadmap.py
.\.venv\Scripts\python.exe scripts/check_java_roadmap_links.py
.\.venv\Scripts\python.exe -m pytest -q test/service/test_learning_path.py test/Control/test_learning_path.py
```

`curate_java_roadmap.py` tái tạo bản dữ liệu nghiên cứu ngày 27/11; nó không tự
nghiên cứu lại hoặc cập nhật access/date. Muốn thay dữ liệu cần sửa bản tuyển
chọn, kiểm tra nguồn lại và tăng version. `check_java_roadmap_links.py` chỉ kiểm
tra HTTP, không mua khóa hoặc gửi cookie. Tests dùng fixture/database tạm, không
gọi provider AI thật. Trên Windows sandbox, TestClient cần quyền loopback.

## Kết quả kiểm tra ngày 27/11/2026

- Bộ Python ngoại tuyến: **270 passed, 3 skipped**; ba ca opt-in AI thật không bật.
- Sau điều chỉnh metadata nguồn và giới hạn cá nhân hóa trong chặng đã chọn:
  **12 test lộ trình đạt lại**.
- Bốn suite JavaScript hiện có: **18 passed, 0 failed**.
- Playwright: kiểm tra 24 lesson/78 unit/48 practice, xác nhận lại khi đổi lựa
  chọn, ngân sách thiếu/đủ, tiến độ tự khai qua reload, tìm kiếm, bàn phím,
  download Markdown khớp file và phục hồi lỗi tải catalog/tạo kế hoạch.
- Không tràn ngang ở 320, 390, 768, 1024 và 1440px; không có JavaScript error
  trong luồng kiểm tra. Đây không phải chứng nhận toàn bộ WCAG.
- **99 URL HTTP truy cập được**, gồm 87 nguồn chính, 10 course links và 2 nguồn
  dự phòng. Bốn URL cần HTTP client của Windows do Python trust store báo lỗi;
  vẫn giữ TLS validation, không bỏ xác minh chứng chỉ. Audit lưu phương thức
  và lỗi Python gốc. HTTP 200 không chứng minh khóa học hoàn toàn miễn phí.
- Preview: `http://127.0.0.1:8011/learning-path`, dùng SQLite riêng dưới `.local/`
  và provider fixture; không deploy công khai hoặc dùng dịch vụ trả phí.
