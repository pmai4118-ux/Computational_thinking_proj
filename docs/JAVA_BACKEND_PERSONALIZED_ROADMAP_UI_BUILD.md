# Build lộ trình cá nhân hóa Java Backend theo thiết kế Stitch

Ngày bàn giao: 27/11/2026. Đây là đặc tả triển khai, kết hợp **UI do người dùng thiết kế** với **catalog đã nghiên cứu và API lộ trình hiện có**. Bản UI đã được tích hợp ở yêu cầu tiếp theo; xem [bàn giao triển khai](STITCH_UI_IMPLEMENTATION.md).

## 1. Đầu vào và phạm vi

Đọc [PROJECT_SPEC.md](../../PROJECT_SPEC.md), nhất là mục 7; [bàn giao tính năng hiện tại](JAVA_BACKEND_IMPLEMENTATION.md); [catalog](../data/learning/java_backend_v1.json); [học liệu Markdown](JAVA_BACKEND_ROADMAP.md).

Nguồn thiết kế bắt buộc:

- [personalized-roadmap.html](../design/stitch-java-backend/personalized-roadmap/personalized-roadmap.html) và [PNG](../design/stitch-java-backend/personalized-roadmap/personalized-roadmap.png).
- [roadmap-settings.html](../design/stitch-java-backend/roadmap-settings/roadmap-settings.html) và [PNG](../design/stitch-java-backend/roadmap-settings/roadmap-settings.png).
- [Design system](../design/stitch-java-backend/design-system/DESIGN.md).

Giữ bố cục, typography, gradient tím, glass, khoảng cách, đường zigzag và trạng thái card từ HTML. Dùng ảnh để so bố cục sau port. Nội dung dữ liệu lấy từ catalog/API; không sao chép số mẫu thành kết quả của người học. Mẫu HTML có token riêng từng trang: ưu tiên CSS/class thực tế của màn đó trước giá trị tổng quát trong DESIGN.md.

Người dùng đã bỏ hướng import JD: không xây parser JD, upload CV/PDF/DOCX hay gọi AI phân tích tuyển dụng. Học liệu chỉ dẫn link để người học tự đọc và thực hành local. Phần này không thêm lý thuyết do AI viết, chạy code, nhận bài code hoặc chấm điểm code trong app.

## 2. Hợp nhất dữ liệu và thiết kế

Catalog hiện có **24 lesson, 78 bài học nhỏ, 48 bài thực hành, 87 nguồn học liệu và 10 chương trình tham khảo**. Track `backend` có JB01–JB23; `advanced` thêm JB24; `foundation` có JB01–JB11. Các số toàn catalog không được dùng làm mẫu số tiến độ cho một kế hoạch chỉ chọn vài lesson.

| Vùng trong mẫu | Dữ liệu/cách triển khai |
|---|---|
| Banner bài kiểm tra nền tảng, 78/100 và vòng tròn 78% | Đổi thành “Điểm xuất phát của bạn”; hiển thị số lesson đã tự đánh dấu và tình trạng bằng chứng chuyển giao. Chưa có baseline Java thì ghi “Chưa có đánh giá Java chuyên biệt”. Vòng tròn chỉ biểu diễn tiến độ tự khai, có nhãn rõ. |
| “Chứng chỉ năng lực Backend Fresher/Junior” | Giữ dòng metadata nhưng đổi thành “Lộ trình tự học Java Backend”; app chưa cấp chứng chỉ. |
| Badge AI Adaptive | Dùng “Cá nhân hóa theo mục tiêu & quỹ thời gian”; thứ tự học do Service tất định. Nếu có gợi ý từ hồ sơ, ghi rõ nguồn bằng chứng, không tuyên bố AI đã đo toàn bộ năng lực Java. |
| Sidebar chọn 5 chặng | 4 phase cốt lõi + 1 phase nâng cao tùy chọn từ catalog. Track không chứa phase nào thì ẩn phase đó; không thêm lesson rỗng để đủ 5. |
| Node zigzag | Một node = một lesson JBxx, không phải một câu phỏng vấn hoặc một unit. Chọn node mở panel bài học. |
| Card đã hoàn thành, dấu xanh | “Đã tự đánh dấu học xong”; không gắn điểm 88/100 hoặc “đã xác minh thành thạo”. |
| Card yếu 65%, vòng đỏ | Chỉ hiện “Cần củng cố theo bằng chứng…” khi có profile bridge phù hợp và người học xác nhận. Không có bằng chứng thì không gắn yếu hoặc 0%. |
| Node khóa | “Nên học tiên quyết trước”; vẫn cho xem tài liệu. Không đặt điểm đậu hay khóa học cứng khi chưa có cơ chế đánh giá tương ứng. |
| Footer 48 bài tự luận, 6 mock interview | Thay bằng số lesson/unit/practice thực của lựa chọn. 48 trong catalog là **bài thực hành tự học**, không phải 48 câu tự luận đã có rubric. Không hứa có 6 mock Java. |
| CTA đánh giá tự luận 4 chiều | Dẫn đến `/setup` với nhãn “Luyện phỏng vấn Backend”; giải thích ngân hàng hiện có chưa phải bộ đánh giá Java chuyên biệt. Không tự tạo session hay đánh dấu lesson đạt. |

## 3. Chi tiết màn lộ trình

1. Dùng navigation chung của app theo hình mẫu, tab Lộ trình active. Không giữ tên/ảnh tài khoản “An Nguyễn” vì app hiện dùng phiên ẩn danh.
2. Giữ hai banner trên cùng: điểm xuất phát; tên lộ trình + chip quỹ thời gian + nút cấu hình. Nút cấu hình mở modal cùng trang, không chuyển sang mock HTML.
3. Desktop: sidebar chặng bên trái, canvas bài học bên phải. Mỗi chặng hiển thị tiêu đề, số lesson trong kế hoạch, số tự đánh dấu; phân biệt bài nằm ngoài kế hoạch với bài chưa học.
4. Canvas giữ nền chấm nhạt, node tròn viền tím, card luân phiên trái/phải và connector cong nét đứt. SVG connector là trang trí `aria-hidden`, không thay thứ tự DOM; DOM theo `ordered_lessons` từ Service. Nếu đáp ứng tiên quyết làm thứ tự phase xen nhau, không tự sort lại và làm sai lịch.
5. Chọn chặng lọc/tập trung các node tương ứng; header tuần cho biết số phút được phân bổ. Kế hoạch thiếu giờ vẫn hiện node deferred và phần thời lượng còn thiếu.
6. Node đang chọn có vòng sáng tím như mẫu. Trạng thái được ghi bằng chữ/icon bên cạnh màu. Trạng thái tự khai và trạng thái đã xếp lịch là hai thuộc tính khác nhau.
7. Mobile dưới 768px: sidebar thành bộ chọn chặng ngang hoặc accordion, node thành một cột, connector dọc. Không ép zigzag rộng gây tràn ngang.

### Panel lesson: phần mở rộng cần build

HTML gốc chưa có màn chi tiết đầy đủ. Dùng drawer/panel đồng bộ glass, typography và button của mẫu; ghi đây là thành phần bổ sung khi review.

- Header: ID, tiêu đề, phase, thời lượng ước tính, các tiên quyết dạng link đến node.
- “Bài học trong lesson”: render **toàn bộ `units`**. Mỗi unit có một hoặc nhiều link lấy qua `reading_ids` → `resources.id`; không chỉ hiển thị tiêu đề lesson.
- Mỗi link có tên bài, nhà cung cấp, ngôn ngữ, edition, điều kiện đọc, ngày công bố/cập nhật nếu có và ngày kiểm tra riêng. Không suy ra năm công bố từ `verified_at`.
- “Bài thực hành áp dụng”: render **toàn bộ `practices`**, `instructions`, link nguồn cơ sở, môi trường local, ghi chú chi phí. Nhãn `project_original` phải là “Bài vận dụng do nhóm biên soạn”, không giả là assignment chính thức.
- “Khóa học tham khảo”: nối `course_ids` → `courses`; tách miễn phí, cần đăng ký, trả phí/preview. Coursera không gắn “free full course”; MIT 6.102 2024 dùng TypeScript phải được ghi đúng.
- Có nút mở tài liệu mới với `rel="noopener noreferrer"`, tải Markdown và tự đánh dấu học xong. Không có vùng nhập code hoặc upload bài.
- “Đã học xong” là self-report lưu theo version catalog; bỏ đánh dấu và cập nhật lựa chọn phải yêu cầu xác nhận lại kế hoạch. Không sửa điểm phỏng vấn.

## 4. Modal cấu hình: giữ hình thức, thay JD bằng mục tiêu Java

Giữ overlay blur, viền mảnh tím, thanh gradient trên, khối header/icon, ba section đánh số và footer hai nút như mẫu. Nội dung form chỉnh theo phạm vi đã chốt:

| Section mẫu | Build trong đợt UI đầu tiên |
|---|---|
| 1. Mục tiêu nghề nghiệp & JD | Đổi tiêu đề thành “Mục tiêu Java Backend & điểm xuất phát”. Giữ chip vai trò Java Backend Intern/Fresher. Vùng tab lớn thay bằng “Toàn bộ chặng” và “Theo điểm cần củng cố”; thêm chọn track, target lesson và bài đã tự học. Không giữ upload JD giả. |
| 2. Bắt đầu/deadline, chip 1–6 tháng | API đang nhận `weeks` 1–52. Hiển thị số tuần là input chính; các chip ghi rõ 4/8/12/24 tuần, không tự coi 1 tháng = 4 tuần lịch. Chọn deadline chỉ bật khi có triển khai chuyển đổi ngày minh bạch ở mục dưới. |
| 3. Số buổi, khung giờ, thứ trong tuần | `hours_per_week` 1–40 là đầu vào authoritative. Đợt đầu dùng input giờ/tuần và số tuần. Có thể giữ grid ngày/khung giờ dưới dạng phần “Lịch chi tiết — chưa hỗ trợ” disabled với giải thích; không vẽ thành chức năng đã lưu. |
| Footer | Số lesson/unit/practice và tổng giờ của kế hoạch thật. “Hủy” không đổi cấu hình cũ; “Áp dụng & tạo lại lộ trình” yêu cầu xác nhận rõ và gửi POST plan. |

### Nâng cấp lịch chi tiết nếu làm tiếp — chưa tồn tại

Để các nút ngày/giờ hoạt động đúng toàn bộ thiết kế, cần một hạng mục riêng thay vì nhét trường lạ vào API hiện có:

- Dự kiến thêm `calendar_preferences` có `start_date`, `deadline`, `timezone` (mặc định Asia/Ho_Chi_Minh), `slots[{weekday,start_time,duration_minutes}]` và schema version. Đây là **đề xuất**, không phải payload hiện tại.
- Kiểm tra ngày kết thúc sau ngày bắt đầu, slot không chồng lấn, duration dương, ngân sách tuần không quá giới hạn; tuần đầu/cuối chỉ tính slot nằm trong khoảng ngày.
- Từ slot tính ra ngân sách thực, chia theo tiên quyết; trả lịch ngày rõ ràng. Deadline thiếu vẫn giữ bài hoãn và báo thiếu giờ. Không chỉ lưu lựa chọn đẹp rồi bỏ qua khi xếp lịch.
- Nếu lưu server, tách bảng/model plan, quyền sở hữu theo cookie đã có và migration có kiểm tra. Đợt đầu chưa cần thay database. Không tự thêm nhắc lịch/email hay tích hợp Calendar.

## 5. API hiện có — dùng trực tiếp

| Method | URL | Dùng cho |
|---|---|---|
| GET | `/api/learning-paths/catalog` | Toàn bộ catalog và metadata |
| GET | `/api/learning-paths/markdown` | Tải cùng nội dung dạng Markdown |
| GET | `/api/profile` | Hồ sơ theo cookie hiện tại; không lấy owner từ form |
| POST | `/api/learning-paths/plan` | Kế hoạch sau khi xác nhận |

Ví dụ request hợp lệ, không thêm JD/calendar vào DTO này:

```json
{
  "track": "backend",
  "mode": "full_track",
  "hours_per_week": 15,
  "weeks": 12,
  "completed_lesson_ids": ["JB01", "JB02"],
  "target_lesson_ids": [],
  "use_profile": true,
  "confirm_goal": true
}
```

Response đọc `ordered_lessons`, `schedule`, `completion_basis`, `completed_lesson_ids`, `confirmed_gap_lesson_ids`, `target_lesson_ids`, `total_estimated_minutes`, `available_minutes`, `shortfall_minutes`, `feasible`, `estimated_weeks`, `warnings`, `privacy_note` và version. Mỗi ordered lesson có `lesson_id`, `title`, `estimated_minutes`, `allocated_minutes`, `remaining_minutes`, `priority`, `reasons`, `status`; mỗi schedule row có `week`, `lesson_id`, `minutes`.

Không dùng `allocated_minutes / estimated_minutes` làm mức thành thạo. Không đủ thời gian phải giữ toàn bộ lesson chưa xếp được; trạng thái và cảnh báo dựa response thay vì UI tự tính lại theo cảm tính.

## 6. Luồng cá nhân hóa

Mở trang → tải catalog và tiến độ self-report cùng version → người học chọn mục tiêu/quỹ giờ/bài đã biết → nếu dùng profile thì giải thích bằng chứng phù hợp → xác nhận → POST plan → render sidebar, node và lịch → mở lesson → tự đọc/làm bài ngoài app → tự đánh dấu → xác nhận lại nếu tạo kế hoạch mới.

Service hiện làm bao đóng tiên quyết, sắp thứ tự topo và chia phút theo tuần, không cần LLM sinh lộ trình. Giữ hai profile bridge đã kiểm soát: `skill.backend.data_consistency` → JB15 và `skill.algorithms.correctness_and_complexity` → JB06, trong giới hạn track đã chọn. Không suy ra trình độ Java từ ngữ nghĩa Python; không có bằng chứng không coi là yếu hoặc 0 điểm.

`localStorage` hiện lưu tiến độ tự khai theo version catalog; chưa đồng bộ đa thiết bị. Kế hoạch trả theo request, chưa có server plan persistence. UI phải ghi đúng giới hạn, xử lý storage bị chặn, không mất lựa chọn khi API lỗi. Nút X/Hủy đóng modal và trả focus; chỉnh form nhưng chưa áp dụng không thay kế hoạch đang xem.

## 7. Ma trận lesson/chặng

| Lesson | Chặng | Nội dung | Tiên quyết | Units | Practices | Phút |
|---|---|---|---|---|---|---|
| [JB01](JAVA_BACKEND_ROADMAP.md#jb01) | Java nền tảng | Môi trường Java, IDE và Maven | Không | 3 | 2 | 240 |
| [JB02](JAVA_BACKEND_ROADMAP.md#jb02) | Java nền tảng | Cú pháp, kiểu dữ liệu và xử lý giá trị | JB01 | 3 | 2 | 240 |
| [JB03](JAVA_BACKEND_ROADMAP.md#jb03) | Java nền tảng | OOP, interface và dữ liệu bất biến | JB02 | 4 | 2 | 240 |
| [JB04](JAVA_BACKEND_ROADMAP.md#jb04) | Java nền tảng | Exception, thời gian và ranh giới dữ liệu | JB03 | 3 | 2 | 240 |
| [JB05](JAVA_BACKEND_ROADMAP.md#jb05) | Java nền tảng | Generics, Collections và equals/hashCode | JB03 | 3 | 2 | 240 |
| [JB06](JAVA_BACKEND_ROADMAP.md#jb06) | Java nền tảng | Lambda, Stream và phân tích chi phí | JB05 | 3 | 2 | 240 |
| [JB07](JAVA_BACKEND_ROADMAP.md#jb07) | Java nền tảng | Đặc tả, bất biến và kiểm thử nền tảng | JB03 | 4 | 2 | 240 |
| [JB08](JAVA_BACKEND_ROADMAP.md#jb08) | Java nền tảng | Concurrency, virtual thread và JVM tools | JB04, JB07 | 4 | 2 | 300 |
| [JB09](JAVA_BACKEND_ROADMAP.md#jb09) | Web và dữ liệu | HTTP và hợp đồng REST API | JB02 | 3 | 2 | 240 |
| [JB10](JAVA_BACKEND_ROADMAP.md#jb10) | Web và dữ liệu | SQL, truy vấn và quan hệ dữ liệu | JB02 | 3 | 2 | 240 |
| [JB11](JAVA_BACKEND_ROADMAP.md#jb11) | Web và dữ liệu | Thiết kế schema, index và tối ưu truy vấn | JB10 | 3 | 2 | 240 |
| [JB12](JAVA_BACKEND_ROADMAP.md#jb12) | Spring Backend | Spring Core, Boot và cấu hình | JB01, JB03, JB04 | 4 | 2 | 240 |
| [JB13](JAVA_BACKEND_ROADMAP.md#jb13) | Spring Backend | REST Controller, validation và xử lý lỗi | JB09, JB12 | 3 | 2 | 240 |
| [JB14](JAVA_BACKEND_ROADMAP.md#jb14) | Spring Backend | JDBC, JPA và truy vấn repository | JB05, JB10, JB12 | 3 | 2 | 300 |
| [JB15](JAVA_BACKEND_ROADMAP.md#jb15) | Spring Backend | Transaction, isolation và tranh chấp dữ liệu | JB11, JB14 | 4 | 2 | 300 |
| [JB16](JAVA_BACKEND_ROADMAP.md#jb16) | Spring Backend | Spring Security, session và JWT | JB13 | 3 | 2 | 300 |
| [JB17](JAVA_BACKEND_ROADMAP.md#jb17) | Spring Backend | Kiểm thử web, database và tích hợp | JB07, JB13, JB14 | 3 | 2 | 300 |
| [JB18](JAVA_BACKEND_ROADMAP.md#jb18) | Vận hành và mở rộng | Gọi dịch vụ ngoài và phục hồi lỗi | JB13, JB17 | 3 | 2 | 240 |
| [JB19](JAVA_BACKEND_ROADMAP.md#jb19) | Vận hành và mở rộng | Cache, Redis và tính nhất quán | JB14, JB15 | 3 | 2 | 240 |
| [JB20](JAVA_BACKEND_ROADMAP.md#jb20) | Vận hành và mở rộng | Messaging, scheduler và batch | JB15, JB18 | 3 | 2 | 360 |
| [JB21](JAVA_BACKEND_ROADMAP.md#jb21) | Vận hành và mở rộng | Docker, build và CI cho Java | JB17 | 3 | 2 | 240 |
| [JB22](JAVA_BACKEND_ROADMAP.md#jb22) | Vận hành và mở rộng | Quan sát hệ thống và kiểm tra hiệu năng | JB18, JB21 | 4 | 2 | 300 |
| [JB23](JAVA_BACKEND_ROADMAP.md#jb23) | Vận hành và mở rộng | Capstone Java Backend và ôn phỏng vấn | JB15, JB16, JB17, JB21 | 3 | 2 | 600 |
| [JB24](JAVA_BACKEND_ROADMAP.md#jb24) | Nâng cao tùy chọn | Tùy chọn: cloud, microservices và reactive | JB20, JB22, JB23 | 3 | 2 | 360 |

Thời lượng là ước tính tuyển chọn để lập kế hoạch. Không diễn giải tổng số giờ là bảo đảm đủ mọi kỹ năng nghề nghiệp hoặc cam kết đậu phỏng vấn. Nguồn chi tiết của từng unit/practice đã nằm trong catalog và Markdown, không tạo bộ link rời dễ lệch version.

## 8. File triển khai và thứ tự làm

1. Đọc/port hai HTML mẫu, giữ bản trong `design/` nguyên vẹn. Chốt shared tokens trong `source/view/static/css/tokens.css` theo từng scope; tránh làm hỏng trang phỏng vấn.
2. Đổi `source/view/templates/learning_path.html`, `source/view/static/css/learning_path.css`, `source/view/static/js/learning_path.js` để có hai banner, sidebar và zigzag/modal.
3. Dùng `InterviewApi.getLearningCatalog()`/`createLearningPlan()` trong `api_client.js`; giữ `/learning-path` và download Markdown. Không đổi FastAPI/Jinja sang React hoặc Java chỉ vì nội dung học là Java.
4. Tách render nguồn, panel lesson, modal state, node state và calendar-disabled state; không hard-code 24 card từ mock. Giữ tìm kiếm và link trực tiếp đến `#lesson-JBxx`.
5. Chỉ chỉnh Model/Service/Controller khi thực sự mở rộng hợp đồng lịch chi tiết; cập nhật contract/test trước khi UI gửi thêm field. Không sửa seed câu hỏi hoặc rubric trong công việc này.

## 9. Tiêu chí nghiệm thu

- So ảnh thật sau build với hai PNG ở cùng chiều rộng; giữ silhouette, font, màu, độ rộng card/sidebar, overlay và đường zigzag. Kiểm tra 390, 768, 1024, 1440px; không tràn ngang ở 320px.
- Đủ 24 lesson trong catalog; track backend 23 lesson; mỗi lesson mở được tất cả units và ít nhất 2 practices, có nguồn/điều kiện truy cập. Đọc dữ liệu động, không dán lại toàn bộ link vào JS.
- Tạo full track, confirmed gaps, chọn target và tiên quyết; tự đánh dấu/bỏ đánh dấu; reload; đổi version; từ chối xác nhận; lịch thiếu/đủ giờ; tải Markdown; lỗi tải catalog/profile/plan và retry.
- Không xuất hiện JD/upload giả, điểm Java giả, chứng chỉ, mock count giả, 48 rubric tự luận hay mác khóa miễn phí trái metadata.
- Tab/Enter/Space hoạt động; modal trap focus/Escape/restore focus; node là button/link có nhãn; màu không là tín hiệu duy nhất; reduced-motion; SVG trang trí không cản screen reader.
- Chạy test lộ trình hiện có và test hồi quy JS phù hợp khi thay logic. Chụp màn hình desktop/mobile, ghi rõ phần lịch chi tiết chưa triển khai. Không ghi “đạt” cho ca chưa chạy.

## 10. Bốn yếu tố tư duy tính toán

- **Phân rã:** catalog/nguồn → unit/practice → lesson → kế hoạch → trạng thái UI.
- **Nhận diện mẫu:** một renderer cho mọi lesson và trạng thái lỗi, một modal xác nhận cho các track.
- **Trừu tượng hóa:** dùng ID/version, prerequisite, quỹ phút; tách tiến độ tự khai khỏi bằng chứng đánh giá.
- **Thiết kế thuật toán:** giữ thuật toán Service; UI chỉ ánh xạ thứ tự và lịch thành sidebar/node, không tự chế thứ tự khác.
