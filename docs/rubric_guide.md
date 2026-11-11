# Hướng dẫn xây dựng và kiểm duyệt Rubric (Rubric Guide - P05)

Tài liệu hướng dẫn quy chuẩn xây dựng, phân cấp mức điểm quan sát được và quy trình kiểm duyệt rubric cho các câu hỏi phỏng vấn kỹ thuật trong dự án *interviewUS* (Computational Thinking).

---

## 1. Nguyên tắc thiết kế Rubric quan sát được (Observable Rubric)

Mỗi câu hỏi phỏng vấn kỹ thuật trong hệ thống (đặc biệt là dạng Technical Case Study) phải có một Rubric gắn kèm bao gồm các tiêu chí độc lập.

1. **Tiêu chí định lượng qua hành vi quan sát được (Observable Criteria):**
   * Không đánh giá mơ hồ như *"ứng viên hiểu bài"*, *"ứng viên trả lời tốt"*.
   * Phải chỉ rõ bằng chứng (expected evidence) cần tìm thấy trong câu trả lời (ví dụ: *"chỉ ra hiện tượng hai luồng cùng đọc stock=1 trước khi ghi"* hoặc *"sử dụng transaction có rollback"*).
2. **Thang điểm 3 mức chuẩn (0 - 1 - 2):**
   * **Mức 0 (Chưa đạt / Unmet):** Hoàn toàn bỏ qua yêu cầu cốt lõi, đưa ra giải pháp sai bản chất kỹ thuật (ví dụ: chỉ dùng lock trong bộ nhớ JVM cho hệ thống nhiều instance), hoặc vi phạm bất biến của bài toán.
   * **Mức 1 (Một phần / Partial):** Nhận biết được vấn đề nhưng giải pháp chưa toàn diện (ví dụ: biết khóa row ở DB nhưng quên transaction rollback khi tạo đơn lỗi).
   * **Mức 2 (Đạt chuẩn / Met):** Đáp ứng đầy đủ bằng chứng quan sát được, bảo vệ được bất biến hệ thống và xử lý đúng các trường hợp biên (edge cases).
3. **Chấp nhận các phương án giải quyết tương đương (Equivalent Answers):**
   * Rubric không được ép buộc một cú pháp hoặc một giải pháp duy nhất.
   * Ví dụ với bài toán race condition tồn kho: chấp nhận **Pessimistic Locking** (`SELECT ... FOR UPDATE`), **Atomic Conditional Update** (`UPDATE ... WHERE stock >= 1`), hoặc **Optimistic Locking** (`version` column) kèm cơ chế retry hợp lý.

---

## 2. Phân biệt "Điểm 0 (Unmet)" và "Chưa đủ căn cứ (Insufficient Evidence)"

Một nguyên tắc cốt lõi của hệ thống chấm điểm minh bạch:

| Trạng thái | Điểm số | Định nghĩa và trường hợp áp dụng |
| :--- | :---: | :--- |
| **Đạt (Met)** | `1` hoặc `2` | Có trích dẫn cụ thể (evidence quote) từ câu trả lời khớp với tiêu chí của rubric. |
| **Không đạt (Unmet)** | `0` | Ứng viên có trình bày nhưng giải thích sai, hoặc hoàn toàn bỏ qua tiêu chí bắt buộc đã nêu rõ trong đề bài. |
| **Chưa đủ căn cứ (Insufficient Evidence)** | `null` | Ứng viên viện dẫn tài liệu, link ngoài, file đính kèm không có trong phiên phỏng vấn (ví dụ: *"Xem code tại link github sau"*), hoặc câu trả lời không liên quan khiến hệ thống không thể đối chiếu. Trường hợp này **giữ score = null và total_score = null**, không tự ý gán điểm 0. |
| **Lỗi xử lý (Provider Failure)** | `null` | Lỗi timeout, quá quota LLM hoặc lỗi kết nối. Tuyệt đối không quy lỗi hệ thống thành điểm số của người học. |

---

## 3. Quy trình Review độc lập (Independent Review)

Theo quy định chất lượng nội dung tại [QUESTION_SOURCES.md](QUESTION_SOURCES.md):

1. **Người tuyển chọn (Curator):** Soạn thảo đề bài, dịch/adapt từ nguồn mở có ghi nhận bản quyền trong `data/seed/source_registry.json`, và thiết kế rubric ban đầu.
2. **Người thẩm định độc lập (Reviewer):** Phải là một thành viên khác trong nhóm (reviewer_id khác curator_id).
3. **Kiểm tra bộ dữ liệu kiểm định (Calibration Cases):**
   * Reviewer kiểm tra tối thiểu 3 ca trả lời mẫu:
     * **Correct:** Lời giải đúng chuẩn (đạt điểm tối đa).
     * **Partial:** Lời giải đúng một phần.
     * **Ambiguous / Insufficient:** Lời giải thiếu dữ liệu hoặc dẫn link ngoài để kiểm tra khả năng xử lý `null`.
   * Đối chiếu kết quả chấm độc lập; nếu có bất đồng (disagreement) phải hiệu chỉnh lại mô tả tiêu chí trong rubric cho đến khi hai bên đồng thuận hoàn toàn.
4. **Tiêu chuẩn phê duyệt (Approved Status):**
   Chỉ chuyển trạng thái rubric sang `approved` khi tất cả các kiểm tra sau đều đạt `true`:
   * [x] `source_and_license_verified`: Nguồn gốc và giấy phép MIT/Apache/CC rõ ràng.
   * [x] `original_and_adaptation_preserved`: Bản gốc và bản dịch tiếng Việt tách biệt.
   * [x] `technical_correctness_checked`: Tính chính xác về mặt kỹ thuật backend.
   * [x] `rubric_levels_distinct`: Ranh giới giữa mức 0, 1, 2 tách bạch, quan sát được.
   * [x] `equivalent_answers_checked`: Ghi rõ ghi chú chấp nhận các giải pháp thay thế.
   * [x] `review_cases_checked`: Đã có testcase hiệu chuẩn và kiểm tra độc lập.

