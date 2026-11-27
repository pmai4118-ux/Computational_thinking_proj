# Nguồn bổ sung cho ngân hàng câu hỏi Backend Intern/Fresher

Tra cứu ngày 27/11/2026. Đây là **nguồn ứng viên**, chưa phải câu hỏi được duyệt.
Không thêm trực tiếp vào `data/seed/questions/` cho đến khi đã ghim phiên bản,
ghi bản gốc và phần thích nghi, tạo rubric, kiểm tra giấy phép tại file cụ thể,
và có người khác review theo `docs/QUESTION_SOURCES.md`.

| Nguồn chính | Tình huống hỏi có thể biên tập | Dạng câu/tiêu chí quan sát | Việc còn phải xác minh |
| --- | --- | --- | --- |
| [Python 3.11: Coroutines and Tasks](https://docs.python.org/3.11/library/asyncio-task.html) | Một tác vụ bị hủy hoặc quá hạn khi gọi dịch vụ; giải thích điều gì xảy ra và cách giữ cleanup | Kiến thức lập trình hoặc tình huống kỹ thuật; giải thích hành vi, phân tích lỗi, kiểm thử | Ghim revision của `Doc/library/asyncio-task.rst` trong CPython; giữ thông báo PSF và tóm tắt thay đổi khi thích nghi. [Giấy phép tài liệu Python](https://github.com/python/cpython/blob/main/Doc/license.rst). |
| [Python 3.11: asyncio Queue](https://docs.python.org/3.11/library/asyncio-queue.html) | Hàng đợi có giới hạn và worker lỗi trước `task_done`; hỏi về `join`, backpressure và ca kiểm thử | Tình huống kỹ thuật; phân tích trạng thái, bảo vệ bất biến, kiểm thử | Ghim revision và kiểm tra phần ví dụ cụ thể được dùng; không lấy nguyên ví dụ nếu chưa hoàn thành metadata/review. |
| [Python 3.11: heapq](https://docs.python.org/3.11/library/heapq.html) | Chọn `k` tác vụ ưu tiên cao nhất từ luồng dữ liệu; giải thích bất biến heap, trường hợp trùng mức ưu tiên và độ phức tạp | Giải thích thuật toán; lập luận tính đúng, phân tích độ phức tạp, kiểm thử biên | Ghim revision của `Doc/library/heapq.rst`; phân biệt rõ với hai câu binary search/ngoặc hiện có, rồi review rubric độc lập. |
| [PostgreSQL 16: Transaction Isolation](https://www.postgresql.org/docs/16/transaction-iso.html) | Hai giao dịch cùng kiểm tra rồi ghi; đối chiếu Read Committed/Serializable và hành động retry | Tình huống kỹ thuật; phân tích lỗi, giữ bất biến, kiểm thử đồng thời | Ghim revision của `doc/src/sgml/mvcc.sgml` và license PostgreSQL cho đúng phiên bản. Cần khác biệt rõ với hai câu về kho hàng/deadlock đang có. |
| [OWASP: SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet) | Review API tạo câu truy vấn động từ tham số sắp xếp; phân biệt tham số dữ liệu với tên cột | Đánh giá mã; phân tích lỗi, giữ hợp đồng an toàn, kiểm thử | Ghim commit của cheat sheet, kiểm tra CC-BY-SA-4.0 và nghĩa vụ ghi công; tránh trùng câu parameterization hiện có. |

Ưu tiên biên tập: (1) cancellation/timeout, (2) queue/backpressure,
(3) heap priority queue, (4) transaction isolation, (5) dynamic SQL identifier. Mỗi câu cần ít nhất
một tiêu chí rubric quan sát được, nhưng **không cần phủ đủ bốn nhóm năng lực**.
Ngân hàng hiện có 8 câu đã duyệt, mỗi dạng 2 biến thể; thêm nguồn ở đây không
tự làm tăng số câu đủ điều kiện cho phiên. Mục tiêu trước mắt là có thêm biến
thể đã review để tránh lặp và thử lại điểm thiếu một cách có ý nghĩa.
