# Đặc tả hiện hành — Trợ lý luyện phỏng vấn kỹ thuật

Cập nhật theo yêu cầu người dùng ngày **10/11/2026**. Bản này thay thế yêu cầu bài
code, live-coding, sandbox và vibe coding/kiểm chứng code AI trong đặc tả cũ.
Đây là phạm vi sản phẩm; không phải tuyên bố các tính năng đã được triển khai.

## 1. Mục tiêu và phạm vi

Hỗ trợ sinh viên CNTT, Backend Intern/Fresher luyện trả lời tự luận kỹ thuật bằng
tiếng Việt: giải thích kiến thức, phân tích tình huống, lý giải phương pháp và
đánh đổi. Lưu câu hỏi đã làm, câu trả lời, bằng chứng và phản hồi để ôn tập.

- Câu trả lời là văn bản tự luận. Không yêu cầu người học viết hoặc phân tích mã.
- Giữ blueprint bốn câu/phiên: kiến thức lập trình, tình huống kỹ thuật, giải thích
  thuật toán bằng lời, lập luận kỹ thuật/đánh đổi. Nhóm cuối thay đánh giá code AI;
  danh mục kỹ năng và nội dung chi tiết vẫn cần C01 phê duyệt.
- Có luyện câu độc lập và phiên phỏng vấn; thiết lập/làm rõ mục tiêu trước phiên.
- Trợ lý hỗ trợ câu hỏi gợi mở, bằng chứng định tính và phản hồi có căn cứ.
  Lộ trình MVP trong `scope.md` vẫn hoãn adaptive probing; không coi nó đã có.
- Có lịch sử, xem lại bài, kết quả từng tiêu chí và bài tự luận ôn tập liên quan.

Ngoài phạm vi: bài tập viết/sửa/review code, code editor, lưu code, chạy code,
sandbox/unit test code của người học, liên kết hoặc theo dõi bài LeetCode, vibe
coding và kiểm chứng code AI. Không phân tích cảm xúc, ánh mắt, giọng điệu hay
ngôn ngữ cơ thể; không dự đoán hoặc cam kết đậu phỏng vấn.

## 2. R1–R8 áp dụng cho phạm vi tự luận

| Chuẩn | Yêu cầu |
| --- | --- |
| R1 — Ranh giới | Chỉ đánh giá câu trả lời kỹ thuật tự luận trong phạm vi đã công bố. |
| R2 — Tất định | AI không tự gán điểm cuối. Service đối chiếu bằng chứng đã xác thực với mức rubric và tính điểm theo quy tắc đã phiên bản hóa. Không có sandbox chấm code. |
| R3 — Nguồn gốc | Lưu nguồn chính xác, revision, tác giả/giấy phép nếu biết, nội dung gốc/chuyển thể và review độc lập trước khi phát hành. Không bịa nguồn hoặc công ty từng hỏi. |
| R4 — AI | Trích bằng chứng, diễn giải và hỏi gợi mở trong phần đã triển khai; phân biệt nhận xét với điểm tính bằng quy tắc. |
| R5 — Điều phối | Làm rõ mục tiêu trước phiên; lưu câu trả lời trước khi đánh giá; lỗi provider giữ bài và cho thử lại có giới hạn. |
| R6 — Giao diện | Web gồm đề bài, vùng trả lời văn bản, phản hồi, lịch sử và tiến độ. Không có code editor. |
| R7 — Bảo vệ | Kiểm tra đầu vào, coi câu trả lời là dữ liệu không tin cậy, chống prompt injection; kiểm tra quyền truy cập bài và không ghi dữ liệu riêng vào log. |
| R8 — Đánh giá/cải tiến | Có benchmark tự luận, bốn tầng lỗi, câu đồng cấu bằng lời và kiểm tra thiên lệch chủ đề/cấp độ; ghi bằng chứng ít nhất một vòng cải tiến. Đây là yêu cầu cần thực hiện, chưa phải kết quả đã có. |

## 3. Rubric và điểm

Giữ bốn nhóm đánh giá, điều chỉnh nội dung cho tự luận:

- A: kiến thức kỹ thuật và giải thích phương pháp/thuật toán.
- B: phân tích tình huống, nguyên nhân, giải pháp và kế hoạch xác minh bằng lời.
- C: lập luận, so sánh phương án, đánh đổi và kiểm chứng giả định bằng tài liệu/
  bằng chứng kỹ thuật; thay nội dung kiểm chứng code AI.
- D: giao tiếp, cấu trúc giải thích và phản hồi câu hỏi phản biện.

Rubric phải công bố mức điểm, bằng chứng mong đợi và quy tắc tổng hợp. Với rubric
chuẩn hóa 0–4 có trọng số, Service dùng:

`S = sum(weight_i * score_i / 4) * 100`, với tổng trọng số bằng 1.

Rubric cụ thể và trọng số cần review trước khi sử dụng. Model hiện tại chưa có
trường trọng số/nhóm A–D; không suy diễn các trường này đã được triển khai. Không
ép mọi rubric cũ sang 0–4 mà chưa chốt version và cập nhật consumer.

`insufficient_evidence` giữ `score = null` và lý do; thiếu căn cứ không đồng nghĩa
điểm 0. Theo hợp đồng hiện tại, tiêu chí bắt buộc chưa chấm được thì tổng là null.
Lỗi hệ thống là đánh giá thất bại, không phải kết luận người học sai.

## 4. Mô hình dữ liệu và luồng

Sáu schema chính để thiết kế: Question, Rubric, Criterion, Session, Answer và
EvaluationResult. Cấu trúc phụ: Skill, SourceMetadata, ReviewMetadata, Evidence,
CriterionCheck; Exercise là bài tự luận ôn tập có nguồn. Xem `data_contract.md`.

- Question không có trường code/code_language hay link bài coding bên ngoài.
- Answer lưu nội dung `text` gốc, session, question ID/version, ID/revision và
  thời điểm nộp. Không thêm code hoặc URL submission.
- EvaluationResult tham chiếu đúng answer revision, question/rubric version và
  chứa criterion checks, evidence, trạng thái và điểm đủ căn cứ.
- Nội dung tái sử dụng bất biến theo version; bài nộp bất biến theo revision.

Luồng: chọn mục tiêu → làm rõ/xác nhận → đọc câu hỏi → nhập tự luận → lưu bài →
diễn giải bằng chứng → xác thực → tính rubric trong Service → phản hồi → ôn tập.
Lỗi xử lý giữ nguyên bài để retry, không ghi đè bản đã nộp.

Model giữ dữ liệu và repository; Controller xử lý request; Service thực hiện quy
tắc, tính điểm và tích hợp AI; View thu thập/trình bày. Không đưa nghiệp vụ vào UI.

## 5. Taxonomy và tư duy tính toán

Bốn tầng lỗi phù hợp tự luận:
1. Hổng kiến thức nền → học liệu có nguồn.
2. Hiểu sai khái niệm → phản ví dụ bằng lời.
3. Sai phương pháp/lập luận → so sánh lựa chọn và giả định.
4. Sai áp dụng/diễn giải → xác định bước suy luận, thuật ngữ hoặc tình huống biên
   chưa nhất quán; không suy diễn lỗi triển khai code khi không có bài code.

Phân rã: tách nội dung, phiên/bài làm, bằng chứng/đánh giá và ôn tập.
Nhận diện mẫu: dùng chung trạng thái lưu, đánh giá và retry trên các loại câu.
Trừu tượng hóa: tham chiếu ID/version/revision, tách thiếu căn cứ khỏi điểm 0.
Thiết kế thuật toán: chọn câu theo coverage, lưu idempotent, kiểm tra evidence,
tính điểm tất định và gợi ý ôn từ điểm thiếu đã được xác nhận.

## 6. Tình trạng triển khai và tài liệu cũ

Hiện có dataclass câu hỏi/rubric/bằng chứng/kết quả và typed IDs. Session, Answer,
Exercise, repository, workflow và app factory vẫn thuộc công việc tiếp theo.
`QUESTION_JSON_FORMAT.md` được giữ làm ví dụ lịch sử, không dùng để import theo
phạm vi mới. Các user flow/UI đang được chỉnh riêng cần đối chiếu lại nếu còn code
editor hoặc sandbox; bản đặc tả này ưu tiên hơn các mô tả cũ đó.
