# Protocol kiểm định câu trả lời tổng hợp (C07)

## Mục đích và phạm vi

Bộ này kiểm tra khả năng diễn giải câu trả lời theo rubric của bốn câu seed C02–C05. Hiện có 74 ca tổng hợp: 19 cho C02, 19 cho C03, 18 cho C04 và 18 cho C05. Tổng phân bố là 12 đúng, 14 thiếu một phần, 12 sai, 12 tương đương, 12 mơ hồ/thiếu ngữ cảnh và 12 chèn chỉ dẫn. Không dùng hồ sơ hay câu trả lời của sinh viên thật.

Các câu tham chiếu và rubric phiên bản 1:

- `question.c02.default_arguments.v1` — tham số mặc định mutable.
- `case.c03.inventory_race.v1` — tranh chấp khi trừ tồn kho.
- `question.c04.two_sum.v1` — giải thích thuật toán Two Sum.
- `question.c05.ai_average.v1` — kiểm chứng gợi ý code tính trung bình.

`test/fixtures/answers/` chứa câu trả lời văn bản; `test/fixtures/expected_evaluations.json` chứa nhãn, bằng chứng và liên kết câu hỏi/rubric; `test/fixtures/question_answer_testcases.json` là bản tổng hợp tra cứu. Không đưa các câu trả lời hay nhãn này vào seed được hiển thị cho người học.

## Gán nhãn và bất đồng

24 ca ban đầu ghi nhận hai lượt đánh giá (`team.bach` và `team.nguyen`) cùng kết quả phân xử (`team.khoa`). Năm ca có bất đồng ban đầu giữ nguyên điểm của từng người và ghi lý do. 50 ca bổ sung được sinh tổng hợp, có nhãn dự kiến và trạng thái `provisional_generated_pending_human_review`; chưa có đánh giá độc lập của hai annotator, chưa có adjudication, và không được xem là gold labels.

Đối chiếu từng tiêu chí với rubric, trích bằng chứng từ câu trả lời gốc, và giữ `insufficient_evidence` riêng với `unmet`. Trước khi dùng 50 ca mới để đo hiệu quả, hai người cần gán nhãn độc lập, ghi bất đồng và adjudicate; không đổi trạng thái provisional chỉ bằng cách đổi metadata.

Thông tin người gán nhãn trong JSON là metadata của bộ dữ liệu; trước khi tuyên bố một lần kiểm định độc lập, nhóm cần xác nhận hai lượt được thực hiện độc lập trước khi xem đánh giá của nhau. Không suy ra tính độc lập chỉ từ tên annotator hoặc kết quả cuối.

## Fixture phân loại đầu vào bổ sung

`test/fixtures/synthetic_answer_cases.json` chứa 101 câu hỏi và 505 câu trả lời tổng hợp từ file nguồn `Computersystem/synthetic_answer_cases.json`. Mỗi câu trả lời được phân loại theo dạng đầu vào: `structured_non_answer`, `topic_echo_non_answer`, `generic_misconception`, `missing_external_context`, hoặc `off_topic`. Đây là phân loại hình dạng đầu vào, không phải chấm theo rubric. Tất cả ca đặt `scoreable: false`, `expected_evaluation: null`, trạng thái `unscored_input_fixture`; không thêm vào `expected_evaluations.json` hay các chỉ số C07.

Hai nhãn `complete_attempt` và `partial_attempt` trong nguồn chỉ là mẫu cấu trúc/nhắc lại chủ đề, không phải câu trả lời đúng hoặc một phần có nội dung chuyên môn. Không dùng chúng làm ví dụ gold. Bộ 505 ca chỉ hỗ trợ kiểm tra phân loại đầu vào; muốn đo độ chính xác rubric cần câu trả lời thực chất, rubric tương ứng và nhãn tham chiếu được review độc lập.

## Chia tập và cách sử dụng

- **Calibration:** 37 ca, phân tầng theo nhóm câu hỏi và loại câu trả lời. Chỉ dùng tập này để phát triển hoặc hiệu chỉnh prompt/model.
- **Held-out:** 37 ca, phân tầng tương tự. Giữ kín khỏi quá trình hiệu chỉnh; chỉ chạy sau khi khóa prompt/model và ghi phiên bản. Nếu xem kết quả rồi sửa prompt/model, tập này đã bị sử dụng và không còn là đánh giá độc lập; cần một bộ held-out mới.
- Phân chia có cả 50 ca provisional. Chỉ các ca đã được review độc lập mới được tính vào đánh giá tham chiếu; báo riêng số ca provisional và không gộp chúng vào độ chính xác.
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
