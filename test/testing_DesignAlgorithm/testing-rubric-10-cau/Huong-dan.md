# Dữ liệu testing chức năng đánh giá câu trả lời tự luận

Bộ dữ liệu có **82 câu trả lời mô phỏng riêng biệt** cho 10 câu có trong danh mục mà phần mềm demo đang đọc. Mỗi ca dùng đúng ID câu hỏi, phiên bản và ID các rubric trong danh mục. Nhãn là dự kiến của bộ kiểm thử, cần người khác trong nhóm duyệt lại nếu dùng để báo cáo độ chính xác.

## Phân bổ

| Bộ | Câu hỏi | Ca đúng hết | Ca sai phân nửa | Ca sai | Ca cần trả null | Tổng |
|---|---|---:|---:|---:|---:|---:|
| A | Toàn bộ 10 câu demo | 10 | 10 | 0 | 10 | 30 |
| B | Q002, Q007, Q010, Q022, Q085 | 40 | 0 | 10 | 2 | 52 |

Ở bộ A, mỗi câu có một ca đúng, một ca sai phân nửa và một ca null. Bài sai phân nửa đạt đúng một trong hai tiêu chí của **mỗi rubric áp dụng**, nên mỗi rubric cho **1/2**.

Ở bộ B, mỗi câu có 8 cách trả lời đúng và 2 cách trả lời sai hoàn toàn. Hai ca null nằm ở Q002 và Q007.

| Ca | Tiêu chí kỳ vọng | Điểm kỳ vọng |
|---|---|---|
| B-Q002-Null-01 | Phân biệt JVM/JRE rõ ràng, nhưng cách phân biệt JDK nằm trong minh họa chưa gửi | Knowledge = null vì có thể là 1 hoặc 2 |
| B-Q007-Null-01 | Giải thích tính bất biến, lợi ích và kết quả concat. Cách nối lặp nằm trong ghi chú chưa gửi | Knowledge = 2; Analysis = null vì có thể là 1 hoặc 2 |

Từ “null” trong tên ca chỉ điểm kỳ vọng của ít nhất một rubric. Ô điểm kỳ vọng để trống trong CSV nghĩa là rubric đó không áp dụng cho câu hỏi. Ca null vẫn có văn bản và có thể trả HTTP 200 kèm báo cáo. Nếu hệ thống không gọi được model hoặc báo bằng chứng sai định dạng, ghi nhận lỗi xử lý riêng.

## Chạy thủ công trên web

1. Mở CSV của bộ cần chạy. Chọn đúng câu hỏi theo questionId hoặc questionTitle trong ứng dụng.
2. Chép nguyên ô answerText vào bài làm, bao gồm đoạn mã nếu có, rồi chọn đánh giá trực tiếp. Nếu giao diện còn đang ở chế độ xem mẫu đã ghi sẵn, chuyển sang gửi bài của mình.
3. Điền actualCriteria, actualScores, modelName và promptVersion. So theo từng criterionId và rubricId. Dùng cột notes để lưu bằng chứng có vấn đề, tên lỗi, hoặc lý do khác nhãn dự kiến. Nếu trích dẫn khác mẫu mà vẫn khớp nguyên văn và hỗ trợ cùng kết luận, ghi nhận là căn cứ tương đương.
4. Đánh dấu đạt khi trạng thái các tiêu chí, các mức điểm và căn cứ đều phù hợp. Ghi riêng lỗi provider hoặc lỗi xử lý, giữ thông tin ca để chạy lại.

## Chạy qua API

- Hai tệp requests.jsonl chứa request body hoàn chỉnh, mỗi dòng là một JSON độc lập gửi đến **POST /api/evaluate** của bản demo. Gửi từng dòng với Content-Type: application/json. Tệp JSONL không phải một request hàng loạt.
- Dùng chế độ live đã cấu hình Gemini để chấm các câu mới. Mỗi ca có answerId riêng và revision = 1. Khi cần gọi lại Gemini cho đúng bài đó, đổi answerId hoặc tăng revision để tránh dùng báo cáo đã lưu.
- JSON tham chiếu chứa tên và rubric thật của 10 câu, mã ca, request, trạng thái từng tiêu chí, trích dẫn/vị trí, điểm và khoảng điểm có thể chọn. Giá trị expectedResults là nhãn so sánh, không đưa vào nội dung gửi model.
- Nếu đổi ngân hàng hoặc phiên bản rubric, đối chiếu lại nhãn theo rubric mới trước khi dùng. Mã băm của catalog hiện dùng nằm trong JSON tham chiếu.

## Phạm vi và kiểm tra

Danh mục demo còn bốn câu có tiêu chí yêu cầu đoạn mã Java (Q009, Q028, Q017, Q018). Bộ A giữ những đoạn mã mà rubric cần để kiểm thử đúng danh mục hiện hành; các đoạn này được gửi như văn bản. Bộ B dùng năm câu trả lời được bằng lời. Các đoạn Java tiêu biểu của bộ A dựa trên mẫu sẵn có trong catalog và được ghép với phần giải thích tiếng Việt.

Đã kiểm tra schema request, liên kết câu hỏi/rubric, ID từng tiêu chí, trích dẫn/vị trí và kết quả của bộ quy tắc xếp điểm trên nhãn tham chiếu. Các nhãn chưa qua duyệt độc lập. Các cột kết quả Gemini được để trống để nhóm điền sau lần chạy trực tiếp.
