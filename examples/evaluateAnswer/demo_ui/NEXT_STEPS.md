# Trạng thái bàn giao PoC

Phạm vi: demo chức năng đánh giá câu trả lời, không phải toàn bộ ứng dụng trong
backlog. Các yêu cầu bàn giao trước đây được đối chiếu dưới đây. Tài liệu này
không coi dữ liệu tự tạo hoặc kiểm thử giả lập là xác nhận chuyên môn/AI thật.

## Đánh giá khả năng demo

| Mục đích buổi demo | Đánh giá hiện tại |
| --- | --- |
| Trình bày luồng đánh giá, thang điểm, bằng chứng và feedback | Sẵn sàng bằng 50 bài mẫu/nhận định ghi sẵn. Python thực hiện kiểm tra và xếp mức thật. |
| Cho người xem nhập bài mới và chứng minh AI hiểu bài đó | Có luồng tích hợp nhưng chưa xác nhận hoạt động trực tiếp: môi trường chưa cấu hình key/provider khả dụng. |
| Chứng minh chất lượng chấm so với người đánh giá | Chưa đủ: cần bộ tham chiếu độc lập và phép thử AI trực tiếp; kiểm thử phần mềm không thay thế bước này. |
| Dùng như sản phẩm nhiều người dùng | Ngoài phạm vi PoC: chưa có phân quyền báo cáo, phiên người dùng và điều phối nhiều server. |

**Kết luận:** có thể trình bày PoC về quy trình ngay. Trước khi hứa demo chấm
bài mới bằng AI, cần hoàn thành cấu hình và thử trực tiếp. Trước khi kết luận
về độ chính xác, cần thêm duyệt tham chiếu và đối chiếu người chấm.

## Phần kỹ thuật đã triển khai

| Yêu cầu | Thực hiện ở đâu / cách kiểm tra |
| --- | --- |
| Đọc question bank qua repository, không checkout Git lúc chạy | `JsonQuestionRepository` → `QuestionBankService`; catalog trong repo. |
| 4 câu đủ bốn nhóm, 6 câu có nhóm không áp dụng | `catalog.json`; `demoBankTest.py`. |
| Chặn dữ liệu chưa duyệt ngoài chế độ demo | `validateQuestion()` kiểm tra reviewer khác curator, source/license/checks; demo có nhãn. |
| Recording khớp version, snapshot và nguyên văn | `getSample()`, `inputDigest()`, `EvidenceReview`; 50 mẫu và kiểm thử mismatch. |
| Preview không gọi AI | `previewAnswer()` dùng recorded interpreter; hoạt động khi thiếu/sai cấu hình AI. |
| Đổi câu, đúng prompt/code/rubric/mẫu; giữ nháp | `DemoPage`, `DemoState`; bộ kiểm thử JS. |
| ID lạ, schema sai, version sai, nguồn chưa duyệt | `demoSchemas`, `QuestionBankService`, `checkVersions`; lỗi có mã, không tạo điểm. |
| MVC-S, logic chỉ có một nơi | `source/main.py` nối View → Control → service → Model/repositories. |
| Answer ID/revision bất biến; retry không gọi lại khi đã xong | `SqliteSubmissionRepository`, `DemoService.processAnswer`; kiểm thử qua restart. |
| Provider lỗi giữ bài, không có report giả | `evaluateAnswer()` lưu input trước gọi; kiểm thử timeout/quota/schema/network. |
| Giao diện hiển thị điểm, bằng chứng, feedback và tải JSON | `DemoPage.renderReport`, `/api/reports/{inputHash}`; API kiểm tra bản tải khớp bản lưu. |
| Lỗi log không lộ key/bài/prompt/transcript | `DemoView.handleError`, provider adapters; kiểm thử che nội dung lỗi. |
| Dữ liệu runtime/secrets không commit | `.gitignore` bỏ qua `secrets/`, `artifacts/`, local reports/answers. |
| Di chuyển sang máy khác | `uv sync --locked`, cấu hình key trên server; không gắn đường dẫn máy cá nhân. |
| Có thể tái hiện | README hướng dẫn chạy/kiểm thử; commit nguồn, input snapshot và provider/model/prompt trong dữ liệu/báo cáo. |

Thang PoC 0/1/2 có mô tả và điều kiện khai báo: 0 không dấu hiệu đạt, 1 một dấu
hiệu, 2 cả hai. Điều kiện mức 2 kéo theo điều kiện mức 1. Dấu hiệu mơ hồ làm
điểm chưa xác định nếu hai cách giải quyết mơ hồ cho hai mức khác nhau. Đây là
rubric mới được ghi rõ trong adaptation, không tuyên bố chuyển đổi nguyên vẹn
rubric cũ của Task 3.

## Còn cần xác nhận bên ngoài

| Việc chưa hoàn tất | Lý do và điều kiện hoàn tất |
| --- | --- |
| Duyệt nguồn và giấy phép | Metadata gốc chưa đủ để kết luận quyền sử dụng. Người phụ trách bổ sung URL/giấy phép và xác minh; không đổi `verified` chỉ để qua kiểm tra. |
| Chốt rubric với người phụ trách Task 3 | Người phụ trách xem adaptation, hai dấu hiệu mỗi nhóm và các biên 0/1/2; đồng ý hoặc chỉnh rồi tăng version. |
| Đánh giá tham chiếu độc lập | Người khác curator duyệt từng bài, trạng thái, quote/offset, điểm, feedback và lời giải tương đương; điền `reviewWorksheet.csv`. |
| Kiểm chứng AI live | Cần key/quota thật hoặc Antigravity đã cài và đăng nhập; gửi bài mới, lưu report và đối chiếu người chấm. Kiểm thử giả lập không thay bước này. |

Catalog hiện `pending_review`, các mẫu `synthetic_unreviewed`, `exampleOnly=true`.
Chế độ demo có nhãn vẫn chạy được. Điều kiện bàn giao hoàn toàn chỉ đạt khi cả
bốn mục trên được xác nhận thật. Không có thông tin đăng nhập hoặc người duyệt
nào được tự tạo để đánh dấu hoàn tất.

Thứ tự hoàn thiện đề xuất:

1. Người chạy demo cấu hình Gemini, khởi động lại và gửi một bài mới. Đạt khi có
   report `providerName=gemini`, đúng câu/rubric, bằng chứng và điểm hợp lệ.
2. Người phụ trách nội dung cùng reviewer độc lập chốt rubric, nguồn/giấy phép và
   50 mẫu; điền worksheet, giải quyết bất đồng rồi cập nhật metadata thật.
3. Dùng thêm bài chưa nằm trong recording để so sánh AI với kết quả tham chiếu:
   trạng thái từng dấu hiệu, mức điểm, căn cứ và độ dễ hiểu của feedback. Ghi cả
   trường hợp AI sai, chưa đủ căn cứ và lỗi dịch vụ; không chỉ chọn các bài đạt.

Các bước 2–3 có thể tiến hành song song với việc chuẩn bị demo; trạng thái dữ liệu
vẫn phải giữ là chưa duyệt cho đến khi reviewer xác nhận.

## Phiên bản và bằng chứng tái hiện

- Nguồn: commit `9106f6d44a8e03ec8d7894a443679de2f0b2f05f`, nhánh dữ liệu Task 3.
- Catalog `demoQuestionBank/1`, dataset `poc10/1`; từng câu/rubric có version.
- Report `answerEvaluation/1`; recorded ghi rõ provider/model/prompt minh họa.
- Live ghi metadata thực tế từ interpreter; không trộn kết quả recorded vào
  số liệu đánh giá chất lượng AI.
- Lệnh chạy và kiểm thử, kịch bản kiểm tra UI/live: xem `README.md` cùng thư mục.
- Kết quả chạy thử và SQLite nằm ngoài commit trong `artifacts/`; tài liệu bàn
  giao mô tả yêu cầu và cách tái hiện, không thay cho xác nhận người duyệt.
