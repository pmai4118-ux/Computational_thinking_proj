# Protocol kiểm định câu trả lời tổng hợp (C07)

## Mục đích và phạm vi

Bộ này kiểm tra khả năng diễn giải câu trả lời theo rubric của bốn câu seed C02–C05. Hiện có 74 ca tổng hợp: 19 cho C02, 19 cho C03, 18 cho C04 và 18 cho C05. Tổng phân bố là 12 đúng, 14 thiếu một phần, 12 sai, 12 tương đương, 12 mơ hồ/thiếu ngữ cảnh và 12 chèn chỉ dẫn. Không dùng hồ sơ hay câu trả lời của sinh viên thật.

Các câu tham chiếu và rubric phiên bản 1:

- `question.c02.string_immutability.v2` — tính bất biến của String trong Java.
- `case.c03.inventory_race.v1` — tranh chấp khi trừ tồn kho.
- `question.c04.employee_lookup.v2` — chọn cấu trúc dữ liệu tra cứu nhân viên theo ID (Q028) bằng Java.
- `question.c05.ai_hashmap_key.v2` — review equals/hashCode cho key dùng trong HashMap Java.

`test/fixtures/answers/` chứa câu trả lời văn bản; `test/fixtures/expected_evaluations.json` chứa nhãn, bằng chứng và liên kết câu hỏi/rubric; `test/fixtures/question_answer_testcases.json` là bản tổng hợp tra cứu. Không đưa các câu trả lời hay nhãn này vào seed được hiển thị cho người học.

## Gán nhãn và bất đồng

Trước khi chuyển câu hỏi sang Java, 24 ca đầu có hai lượt đánh giá và một lần phân xử. Sau khi thay C02/C04/C05 bằng câu hỏi Java khác, các review cũ của 18 ca đó đã bị vô hiệu hóa. Hiện chỉ 6 ca C03 gốc giữ đánh giá tham chiếu; 55 ca thuộc các câu hỏi Java mới và 13 ca C03 bổ sung mang trạng thái `provisional_generated_pending_human_review`, chưa có review độc lập hoặc adjudication. Không xem 68 ca này là gold labels.

Đối chiếu từng tiêu chí với rubric, trích bằng chứng từ câu trả lời gốc, và giữ `insufficient_evidence` riêng với `unmet`. Trước khi dùng các ca provisional để đo hiệu quả, hai người cần gán nhãn độc lập, ghi bất đồng và adjudicate; không đổi trạng thái provisional chỉ bằng cách đổi metadata.

Metadata reviewer trong JSON chỉ áp dụng cho 6 ca C03 gốc còn hiệu lực. Không suy ra tính độc lập chỉ từ tên annotator hoặc kết quả cuối.

## Chia tập và cách sử dụng

- **Calibration:** 37 ca, phân tầng theo nhóm câu hỏi và loại câu trả lời. Chỉ dùng tập này để phát triển hoặc hiệu chỉnh prompt/model.
- **Held-out:** 37 ca, phân tầng tương tự. Giữ kín khỏi quá trình hiệu chỉnh; chỉ chạy sau khi khóa prompt/model và ghi phiên bản. Nếu xem kết quả rồi sửa prompt/model, tập này đã bị sử dụng và không còn là đánh giá độc lập; cần một bộ held-out mới.
- Phân chia có 68 ca provisional. Hiện chỉ 6 ca C03 gốc còn review; báo riêng số ca provisional và không gộp chúng vào độ chính xác.
- Giữ nguyên phân chia trong `expected_evaluations.json`. Không chia lại ngẫu nhiên sau khi đã xem kết quả.

## Quy trình chạy và báo cáo

1. Kiểm tra ID câu hỏi, phiên bản rubric, loại ca, split, câu trả lời và nhãn tham chiếu còn đầy đủ.
2. Chạy trước calibration; lưu phiên bản prompt/model, thời điểm, cấu hình và kết quả theo từng tiêu chí.
3. Khóa cấu hình rồi chạy held-out một lần. So sánh trạng thái, điểm, bằng chứng và phát hiện prompt injection với nhãn tham chiếu; báo cáo theo từng nhóm và loại ca, kèm mọi bất đồng.
4. Nếu thay đổi cấu hình sau khi xem held-out, ghi nhận đó là vòng hiệu chỉnh mới và không dùng cùng tập để tuyên bố kiểm định độc lập.
5. Lỗi provider hoặc thiếu nội dung tham chiếu không được biến thành điểm 0. Bảo toàn câu trả lời gốc khi chạy lại.

`evaluateAnswer` ở nhánh hiện tại có provider `recorded` và ví dụ PoC cho câu case C03. Chạy recorded chỉ kiểm tra đường đi của dữ liệu và quy tắc rubric; nó phát lại đánh giá đã ghi, không đo chất lượng model trực tiếp. Muốn đánh giá model thật cần cấu hình provider/model, lưu phiên bản và chạy held-out theo quy trình trên.

## Giới hạn phù hợp với ngân hàng Backend Java

Bộ C07 hiện gắn với bốn câu seed C02–C05, không bao phủ toàn bộ 100 mục `Q001`–`Q100` trong `raw_question_bank.json`. C02, C04 và C05 đã được chuyển sang nội dung Java dựa trên ngân hàng câu hỏi. Toàn bộ 55 ca thuộc C02/C04/C05 đã chuyển Java có nhãn provisional; thêm 13 ca C03 mới cũng provisional, tổng cộng 68/74. Review cũ của C02/C04/C05 đã bị vô hiệu hóa; chỉ 6 ca C03 gốc chưa thay đổi giữ review tham chiếu cũ. Vì vậy, replay dữ liệu hiện xác nhận đường đi kỹ thuật và sự nhất quán fixture, chưa phải đánh giá độ chính xác độc lập. Muốn báo cáo benchmark Java, cần review rubric và gán nhãn độc lập cho các ca provisional, rồi khóa cấu hình trước khi chạy held-out mới.

Ngân hàng `raw_question_bank.json` giữ 100 câu: 77 programming knowledge, 19 technical case, 2 algorithm explanation và 2 AI code critique. Q009/Q010 được thay bằng Binary Search/Bubble Sort; Q017/Q018 được thay bằng hai bài review code. `test/fixtures/synthetic_answer_cases_raw.json` có 101 đầu vào gồm 100 câu và case C03 inventory, với 5 dạng câu trả lời mỗi đầu vào (505 biến thể). Bốn câu thay thế được đánh dấu `scoreable: false`; chúng là fixture tổng hợp chưa review, không phải nhãn gold và chưa được nhập vào `expected_evaluations.json`.
