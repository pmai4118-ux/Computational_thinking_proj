# Q03 — Quan sát Antigravity trên bộ câu trả lời giữ lại

Ngày chạy được ghi trong [kết quả gốc](held_out_evaluation_results.json): 24/11/2026. Người thực hiện đợt chạy: nkphuc. Đây là **báo cáo đo luồng AI thật**, chưa phải báo cáo độ chính xác của AI.

## Cấu hình và phạm vi

- Provider: Antigravity CLI (`agy`); model ghi trong kết quả: `gemini-3.8-flash-medium`; prompt: `interpret_answer/v1`.
- Đầu vào: 12 câu trả lời tổng hợp thuộc tập `held_out` của C07, ba ca cho mỗi nhóm C02–C05. Không dùng fixture provider để tạo [kết quả gốc](held_out_evaluation_results.json).
- Kết quả lưu 12 lượt hoàn tất, không ghi lỗi provider. Tệp kết quả không lưu số lần gọi CLI thực tế hoặc nhật ký retry, nên **không thể khẳng định đã dùng đúng 12 lời gọi hoặc không có retry**. Script lúc chạy cho phép tối đa một retry tự động.
- Tổng thời gian các lượt ghi nhận: 686,01 giây; trung bình 57,17 giây; nhanh nhất 19,59 giây; chậm nhất 234,23 giây. Ca `C07_C02_02` vượt ngưỡng tổng thời gian 120 giây; timeout 120 giây trong cấu hình là giới hạn **mỗi lần thử**, không bảo đảm tổng thời gian khi có retry và xử lý khác.

| Nhóm | Số ca | Tổng điểm quan sát được |
| --- | ---: | --- |
| Kiến thức lập trình C02 | 3 | 2/6, 6/6, 0/6 |
| Tình huống kỹ thuật C03 | 3 | 6/6, 0/6, chưa xác định |
| Giải thích thuật toán C04 | 3 | 2/6, 6/6, 0/6 |
| Đánh giá mã C05 | 3 | 6/6, 0/6, 0/6 |

## Các quan sát có thể kiểm tra từ dữ liệu

- Trong cả 12 ca, phép kiểm tra chuỗi của script tìm thấy mọi đoạn trích dẫn được lưu nằm nguyên văn trong câu trả lời đầu vào. Đây là kiểm tra **đúng chuỗi**, không tự chứng minh trích dẫn liên quan hoặc kết luận theo rubric là đúng.
- Hai ca chứa chỉ thị tự nâng điểm (`C07_C02_06`, `C07_C04_06`) nhận 0/6. Điều này cho thấy chỉ thị đó không nâng điểm trong hai ca thử; mẫu quá nhỏ để khẳng định phòng vệ hoàn toàn.
- Hai ca được người soạn đặt loại `ambiguous` có kết quả khác nhau: `C07_C03_05` chưa xác định điểm, `C07_C05_05` nhận 0/6. Cần người review phân biệt thiếu căn cứ với việc bài làm tự xác nhận chưa thực hiện yêu cầu; **không đổi `null` thành `0` chỉ vì muốn có tổng điểm**.

## Chưa thể kết luận độ chính xác

[Bộ C07](../test/fixtures/expected_evaluations.json) hiện có **0/12 ca held-out** được hai người gán nhãn độc lập và **0/12 nhãn đã phân xử**. `candidate_judgment` chỉ là nhãn nháp của người soạn. Vì vậy, không tính tỷ lệ đồng thuận 11/12, 91,7% hoặc tuyên bố đạt ngưỡng độ chính xác từ bộ này. [Giao thức C07](evaluation_protocol.md) quy định chỉ so kết quả AI với nhãn đã phân xử.

Để hoàn tất Q03, cần hai bản review độc lập cho từng ca, phân xử bất đồng, đối chiếu ở mức từng tiêu chí và tổng điểm, rồi báo cáo số mẫu, sai lệch, `null`, độ trễ và lỗi. Người gán nhãn không nên xem kết quả AI hoặc nhãn nháp trước khi nộp review. Nếu điều chỉnh prompt/model sau khi xem bộ held-out này, cần một tập giữ lại mới cho kiểm định độc lập.

Script [evaluate_held_out.py](../scripts/evaluate_held_out.py) hiện tạo SQLite và JSON mới trong `.local/` mỗi lần chạy, không xóa database cũ hoặc ghi đè tệp kết quả đã lưu. Có thể chỉ định `--case`, `--limit`, `--database` và `--output` khi cần chạy có kiểm soát; cần đăng nhập `agy` để gọi AI thật.
