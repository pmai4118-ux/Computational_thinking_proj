# Bàn giao nhánh `NewDemo`

Cập nhật: 27/11/2026. `NewDemo` được tách từ `Demo-fix` tại commit `5e3769a`,
sau đó bổ sung luồng chấm cuối phiên, báo cáo ba phần, hồ sơ năng lực và chọn
câu hỏi dựa trên hồ sơ. Nhánh này không merge thêm nhánh nguồn nào. Lịch sử các
nhiệm vụ đã gộp vào `Demo` và `Demo-fix` trước đó nằm trong
[DEMO_HANDOFF.md](DEMO_HANDOFF.md); tài liệu này mô tả **bản đang chạy**.

## 1. Phạm vi chức năng

| Chức năng | Cách chạy trong ứng dụng | Bằng chứng kiểm tra |
| --- | --- | --- |
| Chuẩn bị nội dung | Import seed chỉ nhận câu hỏi, rubric, nguồn và bài tập đủ giấy phép, review và độ phủ. Hiện có 8 câu hỏi thuộc 4 dạng, 5 bài tập. | CLI import trên SQLite mới: `blocked=false`, `excluded=0`, `issues=[]`. |
| Bắt đầu phỏng vấn | Trang `/setup` chọn Backend Developer, Intern/Fresher, tiếng Việt. API tạo phiên 4 câu theo blueprint và gắn phiên với cookie ẩn danh của trình duyệt. | Test API và test Antigravity từ trang thiết lập đều đạt. |
| Chọn câu thích ứng | Chọn **một lần lúc tạo phiên**. Ưu tiên câu ít gặp; khi hòa, ưu tiên rubric khớp điểm cần luyện đã xác nhận trong hồ sơ; sau đó dùng ID ổn định. Chi tiết ở mục 2. | Test `test_adaptive_selection.py`, `test_competency_profile.py`. |
| Trả lời và chuyển câu | Mỗi câu trả lời được lưu nguyên văn với revision và mã chống gửi trùng. Chỉ chuyển câu sau khi lưu thành công; có thể kết thúc sớm. | Test phiên 4 câu, gửi trùng, API phiên và JavaScript workspace. |
| Chấm bằng AI thật | Phiên tạo từ giao diện dùng `after_session`: hoàn tất hoặc kết thúc sớm rồi trang tổng kết chấm **những câu đã lưu** bằng provider cấu hình. Mặc định là Antigravity. Không tự chuyển sang fixture khi AI lỗi. | Hai kiểm thử opt-in gọi `agy` thật đạt; `/health` báo `antigravity`. |
| Chờ, lỗi và retry | Tổng kết hiện số câu đã chấm trên số câu đã gửi, tải lại trạng thái đã lưu; timeout giữ bài gốc và để điểm `null`. Lỗi có thể phục hồi cho phép thử lại đúng revision; kết quả hoàn tất được dùng lại, không gọi AI thêm. | Test timeout, retry, cạnh tranh, phục hồi trang và 18 test JavaScript. |
| Báo cáo sau phiên | `GET /api/sessions/{id}/summary` trả `report` gồm **Tổng quan**, **Chi tiết từng câu**, **Đề xuất cải thiện**; trang tổng kết hiển thị cả ba phần. Không suy diễn điểm năng lực tổng thể từ vài câu. | Test `test_deferred_assessment_report.py`, UI summary và live API. |
| Hồ sơ năng lực | Sau khi có kết quả hoàn tất, ghi nhận theo kỹ năng và loại tiêu chí rubric vào SQLite; `GET /api/profile` đọc theo cookie hiện tại. Dùng hồ sơ cho phiên sau. | Test lưu qua khởi động lại, owner isolation, revision, API; live API đọc được hồ sơ sau chấm. |
| Bài tập và luyện lại | Chỉ đề xuất bài đã review từ điểm thiếu được xác nhận; giữ thứ tự tiên quyết. Nếu có biến thể khác đủ điều kiện, tạo phiên luyện một câu từ answer đã lưu. Không đủ căn cứ hoặc không có bài thì ghi rõ. | Test service I06, trang U06 và live end-to-end tạo lượt luyện. |

Các phần nền tảng của `Demo`/`Demo-fix` gồm F04–F05 (lưu trữ và chạy app),
C02–C06/C08 (câu hỏi, rubric, bài tập và kiểm tra seed), E04–E09 (provider,
chấm và kết quả), I01–I06 (phiên, answer, API chấm và luyện), U03–U08 (luồng
giao diện), cùng các bản kiểm tra/sửa Q02, Q05, Q06 và tài liệu tuần 3. C07
đã có bộ câu trả lời kiểm định nhưng **nhãn hai người review và phân xử chưa có**;
không dùng nhãn nháp để tuyên bố độ chính xác AI.

## 2. Quy tắc chọn câu hỏi thích ứng

**Thời điểm:** khi gọi `POST /api/sessions` hoặc mở phiên từ `/setup`. Bộ chọn
không đổi câu còn lại giữa chừng dựa vào một answer vừa nộp, vì answer đó chưa
được chấm. Lượt luyện lại qua API bài tập là luồng riêng sau phiên.

**Tập câu hợp lệ:** câu phiên bản mới nhất đã duyệt, đúng vai trò, cấp độ, ngôn
ngữ và độ khó blueprint; nguồn có giấy phép đã xác minh và rubric đã duyệt.
Blueprint hiện yêu cầu một câu cho mỗi dạng: kiến thức lập trình, tình huống kỹ
thuật, giải thích thuật toán, đánh giá mã khi dùng AI. Bộ chọn không lặp một
câu trong phiên và kiểm tra rằng lựa chọn hiện tại vẫn để đủ câu cho các slot
còn lại. Thiếu độ phủ thì trả lỗi rõ, không tạo phiên thiếu câu.

**Thứ tự cho từng slot:**

1. Đếm số lần câu đã xuất hiện trong các phiên cũ của cùng chủ trình duyệt,
   kể cả phiên chưa hoàn tất; chọn câu có số lần gặp **ít nhất**.
2. Nếu số lần gặp bằng nhau, cộng độ ưu tiên của các loại tiêu chí rubric của
   câu khớp với **điểm cần luyện hiện tại** của cùng skill trong hồ sơ. Một mục
   chỉ là điểm cần luyện khi quan sát hoàn tất **mới nhất** có trạng thái
   `unmet` và điểm hợp lệ. Trong tối đa ba lần có điểm gần nhất, độ ưu tiên là
   trung bình có trọng số của tỷ lệ điểm còn thiếu `1 - score/max_score`, với
   trọng số `1, 2, 3` theo thứ tự cũ đến mới. Câu khớp nhiều hoặc khớp điểm
   thiếu nặng hơn được ưu tiên.
3. Nếu vẫn hòa, dùng question ID để chọn ổn định, có thể tái hiện.

Ví dụ: cùng dạng có hai câu đều chưa gặp. Hồ sơ ghi skill Python còn thiếu
`test_design`; câu có rubric kiểm tra `test_design` được chọn trước câu không
kiểm tra tiêu chí này. Nếu câu đó đã gặp một lần còn câu kia chưa gặp, quy tắc
ít gặp được ưu tiên. Nếu chưa có kết quả chấm, hồ sơ trống và hệ thống vẫn chọn
theo số lần gặp rồi ID.

Đây là cá nhân hóa có ràng buộc trên ngân hàng nhỏ, **chưa phải kiểm tra thích
ứng được hiệu chuẩn thống kê**. Hiện chỉ có hai câu mỗi dạng nên khả năng đổi
biến thể còn hạn chế. Danh sách nguồn để mở rộng sau review nằm ở
[QUESTION_SOURCE_CANDIDATES.md](QUESTION_SOURCE_CANDIDATES.md); nguồn mới chưa
được đưa vào phiên nếu chưa qua kiểm tra C08.

## 3. Hồ sơ năng lực và báo cáo

`competency_profiles` lưu một hàng cho mỗi
`(owner_token_hash, skill_id, criterion_type)`. Hàng ghi số lần đạt, chưa đạt,
chưa đủ căn cứ, tối đa ba mức điểm gần nhất, trạng thái mới nhất, xu hướng,
mức độ dày bằng chứng và tham chiếu đến phiên, answer revision, kết quả, tiêu
chí. Cookie chỉ được lưu dưới dạng hash. Dữ liệu gốc vẫn là answer và
`EvaluationResult`; hồ sơ là phần tổng hợp có thể tái tạo.

Chỉ phiên `completed` hoặc `ended_early`, câu trả lời **revision mới nhất** và
kết quả đánh giá `completed` mới góp vào hồ sơ. Service tái tạo hồ sơ sau lượt
chấm hoàn tất, khi đọc `/api/profile` hoặc khi bắt đầu phiên mới; do đó kết
quả cũ được backfill và một lần retry không làm tăng số quan sát giả. Kết quả
được sắp theo thời điểm chấm. `met` mới nhất là điểm mạnh đã quan sát;
`unmet` mới nhất là điểm cần luyện; `insufficient_evidence` mới nhất không bị
gán điểm 0 hay coi là yếu. Chưa có chấm xong thì API trả danh sách rỗng.

**Bốn dạng câu hỏi không phải bốn nhóm năng lực.** Báo cáo gộp các tiêu chí
rubric thực sự được đánh giá thành Kiến thức, Phân tích vấn đề, Đề xuất giải
pháp và Kiểm chứng. Một câu có thể chỉ đo một vài nhóm. Nhóm không có tiêu chí
trong phiên được ghi là chưa quan sát, không bị chấm 0.

- **Tổng quan:** số câu trả lời, số câu có kết quả, độ phủ và điểm mạnh/điểm
  thiếu có căn cứ theo từng nhóm.
- **Chi tiết:** đề, answer gốc, điểm theo câu và từng tiêu chí, giải thích,
  trích dẫn/quan sát và phần chưa đủ căn cứ.
- **Đề xuất:** tối đa ba điểm thiếu ưu tiên từ kết quả đã chấm, mục tiêu cải
  thiện, bài luyện đã review theo tiên quyết, thời lượng ước tính và khả năng
  luyện bằng biến thể khác. Thiếu bài phù hợp được nói rõ.

Báo cáo thuộc **phiên hiện tại**; hồ sơ năng lực theo dõi **qua các phiên**.
Hồ sơ hiện có API và được dùng để chọn câu, chưa có màn hình riêng. Chưa có
đăng nhập hoặc đồng bộ giữa trình duyệt/thiết bị; mất cookie thì không tự nối
lại lịch sử.

## 4. Kiểm tra trên bản `NewDemo`

Chạy lại ngày 27/11/2026 từ repository root bằng `.venv` và Node.js:

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .local\pytest-full-recheck-20261127` | **258 passed, 3 skipped**. Ba skip mặc định là hai ca Antigravity opt-in và một ca Gemini REST cần API key. |
| `node --test test/view/workspace_recovery.test.cjs test/view/q05_ui_interactions.test.cjs test/view/q06_recovery.test.cjs test/view/deferred_summary.test.cjs` | **18 passed, 0 failed**. |
| `.\.venv\Scripts\python.exe -m source.service.question_bank_service --database .local\verification-20261127.sqlite3` | 4 skill, 9 nguồn, 8 rubric, 8 câu, 5 bài tập; `blocked=false`, `issues=[]`. |
| Bật `E09_LIVE_TEST=1` và `DEMO_LIVE_TEST=1`, chạy hai ca live trong `test/service/test_evaluation_flow.py` và `test/Control/test_demo_live_flow.py` | **2 passed trong 88,67 giây**; gọi Antigravity thật, lưu/dùng lại kết quả, đọc báo cáo và hồ sơ, tạo lượt luyện. |
| HTTP vào web đang chạy: `/`, `/setup`, `/health`, `/api/profile` | Đều trả **200**; `/health` báo `provider=antigravity`. |
| `git diff --check` | Không có lỗi whitespace. |

Fixture trong test ngoại tuyến là bộ phản hồi cố định để kiểm tra luồng phần
mềm, không phải AI thật. Hai ca live trên dùng tài khoản `agy` đã đăng nhập
và SQLite tạm riêng. Test bốn câu hoàn chỉnh dùng fixture; ca live end-to-end
chấm một answer sau khi kết thúc sớm. Chưa chạy bốn lượt AI thật liên tiếp
trong một phiên, chưa kiểm chứng độ chính xác chấm so với hai nhãn chuyên gia,
và chưa test trực quan mọi kích thước màn hình trên bản này. Không suy ra độ
trễ ổn định từ hai lượt gọi; timeout giữ answer và cho retry khi lỗi phục hồi.

## 5. Chạy thử và kiểm tra nhanh

```powershell
uv sync --locked
agy models
.\run_demo.ps1
```

Mở `http://127.0.0.1:8000/`; `/health` phải báo `provider=antigravity`.
Đăng nhập `agy` trên máy chạy ứng dụng. Dùng đường dẫn SQLite mới dưới `.local/`
nếu muốn bắt đầu dữ liệu sạch; không xóa database cũ để giữ lịch sử người học.
Khi provider timeout, mở lại tổng kết và bấm thử lại trên answer đã lưu. Không
đưa cookie, dữ liệu người học, `.local/` hoặc kết quả live cục bộ lên Git.
