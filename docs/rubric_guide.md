# Hướng dẫn xây dựng và kiểm duyệt Rubric (P05)

| Thuộc tính | Nội dung |
| --- | --- |
| Mã công việc | P05 — Viết một case và rubric hoàn chỉnh |
| Người thực hiện | hwngMP (`member-1`) · Reviewer độc lập: Tin (`member-6`) |
| Phụ thuộc | [P01 (`scope.md`)](scope.md), [P03 (`data_contract.md`)](data_contract.md), [C01 (`content_guide.md`)](content_guide.md) |
| Đầu ra | [`data/seed/questions/cases.json`](../data/seed/questions/cases.json), [`data/seed/source_registry.json`](../data/seed/source_registry.json), [`test/fixtures/question_reviews/p05.json`](../test/fixtures/question_reviews/p05.json), `docs/rubric_guide.md` |

---

## 1. Nguyên tắc thiết kế Rubric quan sát được (Observable Rubric)

Mỗi câu hỏi trong ngân hàng câu hỏi luyện phỏng vấn phải gắn với một phiên bản Rubric bất biến (`rubric.id`, `rubric.version`) gồm các tiêu chí độc lập:

1. **Tiêu chí gắn với bằng chứng quan sát được (`expected_evidence`):**
   - Không viết mô tả cảm tính như *"hiểu rõ vấn đề"*, *"trình bày mạch lạc"*.
   - Mỗi tiêu chí phải chỉ rõ mệnh đề kỹ thuật hoặc hành vi kiểm chứng được trong câu trả lời của người học, đồng thời gắn `criterion_type` thuộc tập hợp lệ của ô khung phiên trong [`data/seed/session_blueprints.json`](../data/seed/session_blueprints.json) (ví dụ với `technical_case`: `failure_analysis`, `invariant_preservation`, `test_design`).
2. **Thang điểm 3 mức phân biệt rõ ranh giới (`0` – `1` – `2`):**
   - **Mức `0` (`unmet`):** Bỏ qua yêu cầu bắt buộc đã nêu rõ trong đề bài hoặc đề xuất cách xử lý sai bản chất kỹ thuật (ví dụ: dùng khóa bộ nhớ cục bộ `synchronized` trên một instance để chống race condition giữa nhiều instance).
   - **Mức `1` (`unmet` / đạt một phần):** Nhận diện đúng hướng nhưng thiếu một ràng buộc quan trọng của tiêu chí (ví dụ: có khóa/cập nhật nguyên tử ở DB nhưng quên rollback khi bước tạo đơn lỗi, hoặc có test đồng thời nhưng thiếu test rollback).
   - **Mức `2` (`met`):** Đáp ứng trọn vẹn các bằng chứng quan sát được của tiêu chí.
3. **Chấp nhận lời giải tương đương (`equivalent_answers`):**
   - Rubric đánh giá bản chất kỹ thuật và việc bảo toàn bất biến, không chấm theo so khớp từ khóa máy móc với một đáp án mẫu duy nhất.
   - Ví dụ ở case `case.c03.inventory_race.v1`: cả ba cách **Conditional Atomic Update** (`UPDATE ... WHERE stock >= 1`), **Pessimistic Locking** (`SELECT ... FOR UPDATE` trong transaction), và **Optimistic Concurrency Control** (`version` column kèm xử lý conflict/rollback) đều đạt mức `2` ở tiêu chí `c03.atomicity`.

---

## 2. Phân biệt thiếu yêu cầu (`unmet / 0`) và chưa đủ căn cứ (`insufficient_evidence / null`)

Theo hợp đồng miền [P03 (`data_contract.md`)](data_contract.md#status-and-null-semantics), cả người chấm độc lập lẫn tầng đánh giá tự động phải phân biệt rạch ròi 4 trạng thái sau:

| Trạng thái | Điểm tiêu chí | Tổng điểm câu (`total_score`) | Khi nào áp dụng |
| --- | :---: | :---: | --- |
| **`met`** | `2` (đạt mức tối đa của tiêu chí) | Cộng tổng khi mọi tiêu chí đều xác định được | Có đoạn trích nguyên văn (`quote` + `start_offset`/`end_offset`) thỏa mãn đầy đủ mô tả mức đạt của tiêu chí. |
| **`unmet`** | `0` hoặc `1` | Cộng tổng khi mọi tiêu chí đều xác định được | Câu trả lời có nội dung để đối chiếu nhưng giải thích sai kỹ thuật (`0`), bỏ qua một phần đề bài bắt buộc (`0`), hoặc mới đáp ứng một phần tiêu chí (`1`). |
| **`insufficient_evidence`** | `null` | `null` | Người học viện dẫn tệp đính kèm, hình ảnh, liên kết ngoài không có trong văn bản câu trả lời hoặc ngữ cảnh bị thiếu khiến không thể xác minh đúng/sai. Bắt buộc ghi rõ `unresolved_reason`. |
| **Lỗi xử lý (`failed`)** | Không tạo điểm | `null` | Lỗi mạng, timeout, hết quota hoặc JSON từ AI provider sai cấu trúc. Giữ nguyên câu trả lời gốc để thử đánh giá lại. |

---

## 3. Quy trình tuyển chọn nguồn mở và review độc lập

1. **Xác minh nguồn và giấy phép (`source_registry.json`):**
   - Chỉ chọn tài liệu/code từ nguồn mở có giấy phép rõ ràng (như MIT License của *Tech Interview Handbook* hoặc *TheAlgorithms/Python*).
   - Lưu đầy đủ `url` tới file gốc, mã `revision` (commit SHA), `authors`, `license.spdx_id`, `license.url`, `required_notice` và `original_content` trước khi dịch/thích nghi.
   - Ghi nhận bản quyền vào [`docs/THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
2. **Biên soạn 4 ca kiểm định chuẩn (`test/fixtures/question_reviews/*.json`):**
   - **Ca 1 (`correct`):** Đạt tối đa theo hướng giải tham chiếu.
   - **Ca 2 (`equivalent`):** Đạt tối đa bằng một phương án kỹ thuật khác hợp lệ.
   - **Ca 3 (`partial` / `unmet`):** Thiếu yêu cầu hoặc sai kỹ thuật để kiểm tra ranh giới `0` và `1`.
   - **Ca 4 (`insufficient_evidence`):** Viện dẫn tài liệu ngoài để kiểm tra việc giữ `score: null` và `total_score: null`.
3. **Thẩm định độc lập và giải quyết bất đồng:**
   - Một thành viên khác (`reviewer_id != curator_id`) chấm độc lập các ca kiểm định dựa trên rubric.
   - Mọi điểm chưa đồng thuận được ghi vào `disagreement_log` kèm cách sửa câu chữ ranh giới mức điểm trước khi chuyển `review.status` sang `"approved"`.

---

## 4. Kết quả thực hiện mẫu đại diện P05 (`case.c03.inventory_race.v1`)

- **Câu hỏi và rubric đã duyệt:** [`data/seed/questions/cases.json`](../data/seed/questions/cases.json) (`id: "case.c03.inventory_race.v1"`, `skill_ids: ["skill.backend.data_consistency"]`).
- **Bản ghi nguồn mở:** [`data/seed/source_registry.json`](../data/seed/source_registry.json) (`id: "source.c03.concurrent_inventory"`, kho `postgres/postgres` file `doc/src/sgml/mvcc.sgml` commit `83cefb7b738c32a66a91537aa502d99891a63b11`, giấy phép `PostgreSQL`).
- **Bộ 4 mẫu trả lời đã đối chiếu độc lập:** [`test/fixtures/question_reviews/p05.json`](../test/fixtures/question_reviews/p05.json).
