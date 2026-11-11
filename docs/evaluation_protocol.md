# Protocol kiểm định câu trả lời tổng hợp (C07)

## Mục đích và phạm vi

Bộ này kiểm tra khả năng diễn giải câu trả lời theo rubric của bốn câu seed C02–C05. Mỗi câu có sáu biến thể: đúng, thiếu một phần, sai, tương đương hợp lệ, mơ hồ/thiếu ngữ cảnh và chèn chỉ dẫn. Tổng cộng 24 ca. Đây là dữ liệu tổng hợp; không dùng hồ sơ hay câu trả lời của sinh viên thật.

Các câu tham chiếu và rubric phiên bản 1:

- `question.c02.default_arguments.v1` — tham số mặc định mutable.
- `case.c03.inventory_race.v1` — tranh chấp khi trừ tồn kho.
- `question.c04.two_sum.v1` — giải thích thuật toán Two Sum.
- `question.c05.ai_average.v1` — kiểm chứng gợi ý code tính trung bình.

`test/fixtures/answers/` chứa câu trả lời văn bản; `test/fixtures/expected_evaluations.json` chứa nhãn tham chiếu, bằng chứng và liên kết câu hỏi/rubric; `test/fixtures/question_answer_testcases.json` là bản tổng hợp tra cứu. Không đưa các câu trả lời hay nhãn này vào seed được hiển thị cho người học.

## Gán nhãn và bất đồng

Nhãn ghi nhận hai lượt đánh giá (`team.bach` và `team.nguyen`) cùng kết quả phân xử (`team.khoa`). Đối chiếu từng tiêu chí với rubric, trích bằng chứng từ câu trả lời gốc, và giữ `insufficient_evidence` riêng với `unmet`. Năm ca có bất đồng ban đầu phải giữ nguyên điểm của từng người và ghi lý do trước khi dùng kết quả phân xử làm nhãn tham chiếu.

Thông tin người gán nhãn trong JSON là metadata của bộ dữ liệu; trước khi tuyên bố một lần kiểm định độc lập, nhóm cần xác nhận hai lượt được thực hiện độc lập trước khi xem đánh giá của nhau. Không suy ra tính độc lập chỉ từ tên annotator hoặc kết quả cuối.

## Chia tập và cách sử dụng

- **Calibration:** 12 ca, gồm 3 ca mỗi nhóm câu hỏi. Chỉ dùng tập này để phát triển hoặc hiệu chỉnh prompt/model.
- **Held-out:** 12 ca, gồm 3 ca mỗi nhóm câu hỏi. Giữ kín khỏi quá trình hiệu chỉnh; chỉ chạy sau khi khóa prompt/model và ghi phiên bản. Nếu xem kết quả rồi sửa prompt/model, tập này đã bị sử dụng và không còn là đánh giá độc lập; cần một bộ held-out mới.
- Giữ nguyên phân chia trong `expected_evaluations.json`. Không chia lại ngẫu nhiên sau khi đã xem kết quả.

## Quy trình chạy và báo cáo

1. Kiểm tra ID câu hỏi, phiên bản rubric, loại ca, split, câu trả lời và nhãn tham chiếu còn đầy đủ.
2. Chạy trước calibration; lưu phiên bản prompt/model, thời điểm, cấu hình và kết quả theo từng tiêu chí.
3. Khóa cấu hình rồi chạy held-out một lần. So sánh trạng thái, điểm, bằng chứng và phát hiện prompt injection với nhãn tham chiếu; báo cáo theo từng nhóm và loại ca, kèm mọi bất đồng.
4. Nếu thay đổi cấu hình sau khi xem held-out, ghi nhận đó là vòng hiệu chỉnh mới và không dùng cùng tập để tuyên bố kiểm định độc lập.
5. Lỗi provider hoặc thiếu nội dung tham chiếu không được biến thành điểm 0. Bảo toàn câu trả lời gốc khi chạy lại.

`evaluateAnswer` ở nhánh hiện tại có provider `recorded` và ví dụ PoC cho câu case C03. Chạy recorded chỉ kiểm tra đường đi của dữ liệu và quy tắc rubric; nó phát lại đánh giá đã ghi, không đo chất lượng model trực tiếp. Muốn đánh giá model thật cần cấu hình provider/model, lưu phiên bản và chạy held-out theo quy trình trên.

## Giới hạn phù hợp với ngân hàng Backend Java

Bộ C07 hiện gắn với bốn câu seed C02–C05, không bao phủ 100 mục `Q001`–`Q100` trong `raw_question_bank.json`. C02 và C05 hiện dùng ví dụ Python, còn ngân hàng 100 câu tập trung vào Java Backend và chưa có rubric/nhãn tham chiếu cho tất cả câu. Vì vậy, kết quả C07 không được diễn giải thành kiểm định cho toàn bộ ngân hàng Fresher Backend Java. Muốn đạt phạm vi đó, cần chọn câu Java tương ứng, chốt rubric cho từng câu và tạo một held-out mới được gán nhãn độc lập.
