# Biên bản bàn giao nguồn câu hỏi và bài tập (P05, C02 – C06)

Tài liệu này là biên bản bàn giao chính thức cho toàn bộ ngân hàng câu hỏi luyện phỏng vấn và danh mục bài tập của **Tuần 1** (`P05`, `C02`, `C03`, `C04`, `C05`, `C06`).

Mọi bản ghi trong [`data/seed/`](../data/seed/) đều được tuyển chọn từ **kho mã nguồn mở và tài liệu kỹ thuật chính thức đã đưa vào thực tế trên GitHub**, được kiểm chứng truy cập thực tế (`HTTP 200`), ghim cứng mã commit SHA (`revision`), xác minh giấy phép SPDX và lưu tách biệt nội dung nguyên bản (`original_content`) với phần dịch/thích nghi tiếng Việt (`adaptation`). Không có bất kỳ câu hỏi hay bài tập nào tự nghĩ mơ hồ hoặc thiếu nguồn gốc truy xuất.

---

## 1. Tổng hợp 5 kho nguồn mở thực tế đã xác minh

| STT | Kho nguồn mở (GitHub) | Commit SHA đã ghim (`revision`) | Giấy phép (SPDX) | File nguồn trực tiếp (đã kiểm chứng HTTP 200) | Bản ghi `source_id` trong [`source_registry.json`](../data/seed/source_registry.json) |
| :-: | --- | --- | :---: | --- | --- |
| 1 | **[python/cpython](https://github.com/python/cpython)** *(Tài liệu chính thức ngôn ngữ Python)* | `94276402cf3b3a5e1fa96cedb33a4dc498a77ed2` | `PSF-2.0` ([LICENSE](https://github.com/python/cpython/blob/94276402cf3b3a5e1fa96cedb33a4dc498a77ed2/LICENSE)) | [`Doc/faq/programming.rst`](https://github.com/python/cpython/blob/94276402cf3b3a5e1fa96cedb33a4dc498a77ed2/Doc/faq/programming.rst) | `source.cpython.faq.mutable_defaults`<br>`source.cpython.faq.late_binding_closures` |
| 2 | **[postgres/postgres](https://github.com/postgres/postgres)** *(Tài liệu chính thức hệ quản trị CSDL PostgreSQL — Chapter 13 Concurrency Control)* | `83cefb7b738c32a66a91537aa502d99891a63b11` | `PostgreSQL` ([COPYRIGHT](https://github.com/postgres/postgres/blob/83cefb7b738c32a66a91537aa502d99891a63b11/COPYRIGHT)) | [`doc/src/sgml/mvcc.sgml`](https://github.com/postgres/postgres/blob/83cefb7b738c32a66a91537aa502d99891a63b11/doc/src/sgml/mvcc.sgml) | `source.c03.concurrent_inventory`<br>`source.postgres.mvcc.deadlocks` |
| 3 | **[TheAlgorithms/Python](https://github.com/TheAlgorithms/Python)** *(Kho thuật toán chuẩn cộng đồng Python)* | `30507bbe41397065728167fb09aa820f9fce8dc7` | `MIT` ([LICENSE.md](https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/LICENSE.md)) | [`searches/binary_search.py`](https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/searches/binary_search.py)<br>[`data_structures/stacks/balanced_parentheses.py`](https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/data_structures/stacks/balanced_parentheses.py) | `source.thealgorithms.python.bisect_left`<br>`source.thealgorithms.python.balanced_parentheses`<br>`source.thealgorithms.python.binary_search_fn` |
| 4 | **[OWASP/CheatSheetSeries](https://github.com/OWASP/CheatSheetSeries)** *(Chuẩn bảo mật thực tế của OWASP Foundation)* | `7af0ef1b745f1a38ce905c00c5a592d5b3a515a9` | `CC-BY-SA-4.0` ([CC-BY-SA-4.0](https://creativecommons.org/licenses/by-sa/4.0/)) | [`cheatsheets/Query_Parameterization_Cheat_Sheet.md`](https://github.com/OWASP/CheatSheetSeries/blob/7af0ef1b745f1a38ce905c00c5a592d5b3a515a9/cheatsheets/Query_Parameterization_Cheat_Sheet.md) | `source.owasp.query_parameterization` |
| 5 | **[yangshun/tech-interview-handbook](https://github.com/yangshun/tech-interview-handbook)** *(Sổ tay phỏng vấn kỹ thuật thực tế)* | `e1d28e8886c0b6ff3e50da991ce0e895134ddc59` | `MIT` ([LICENSE](https://github.com/yangshun/tech-interview-handbook/blob/e1d28e8886c0b6ff3e50da991ce0e895134ddc59/LICENSE)) | [`apps/website/contents/algorithms/array.md`](https://github.com/yangshun/tech-interview-handbook/blob/e1d28e8886c0b6ff3e50da991ce0e895134ddc59/apps/website/contents/algorithms/array.md) | `source.tech_interview_handbook.array_stack` |

---

## 2. Chi tiết bàn giao 8 câu hỏi đã duyệt (`C02` – `C05`)

### 2.1. Công việc `C02` — Nhóm `programming_knowledge` (`skill.programming.code_semantics`)
- **File lưu trữ:** [`data/seed/questions/programming.json`](../data/seed/questions/programming.json)
- **Fixture review độc lập:** [`test/fixtures/question_reviews/c02.json`](../test/fixtures/question_reviews/c02.json)
- **Người tuyển chọn / Người duyệt:** `nkphuc` → `Tin` (`status: "approved"`)

| Mã câu hỏi (`id`) | Mã `source_id` | Nội dung gốc tại nguồn thực tế | Tóm tắt biên tập & thích nghi (`adaptation`) |
| --- | --- | --- | --- |
| `prog.c02.mutable_default_arg.v1` | `source.cpython.faq.mutable_defaults` | Mục *"Why are default values shared between objects?"* trong `Doc/faq/programming.rst` của `python/cpython`: giải thích giá trị mặc định được khởi tạo đúng một lần khi thực thi lệnh `def`. | Chuyển sang tiếng Việt với hàm `append_audit_event(action, events=[])`; bổ sung ràng buộc giữ nguyên danh tính (`is`) của list khi người gọi truyền tường minh `[]` để phân biệt mức điểm `1` (`events or []`) và mức điểm `2` (`events is None`). |
| `prog.c02.closure_late_binding.v1` | `source.cpython.faq.late_binding_closures` | Mục *"Why do lambdas defined in a loop with different values all return the same result?"* trong `Doc/faq/programming.rst` của `python/cpython` (`for x in range(5): squares.append(lambda: x**2)`). | Chuyển sang tiếng Việt với danh sách `validators`; giữ yêu cầu gọi không đối số `validators[i]()` và kiểm thử toàn bộ 5 hàm trả kết quả độc lập (bản v2 căn chỉnh tiêu chí kiểm thử theo đúng API `build_validators()`). |

### 2.2. Công việc `P05` & `C03` — Nhóm `technical_case` (`skill.backend.data_consistency`)
- **File lưu trữ:** [`data/seed/questions/cases.json`](../data/seed/questions/cases.json)
- **Fixture review độc lập:** [`test/fixtures/question_reviews/p05.json`](../test/fixtures/question_reviews/p05.json), [`test/fixtures/question_reviews/c03.json`](../test/fixtures/question_reviews/c03.json)
- **Người tuyển chọn / Người duyệt:** `hwngMP`, `nguyentrg` → `Tin` (`status: "approved"`)

| Mã câu hỏi (`id`) | Mã `source_id` | Nội dung gốc tại nguồn thực tế | Tóm tắt biên tập & thích nghi (`adaptation`) |
| --- | --- | --- | --- |
| `case.c03.inventory_race.v1` | `source.c03.concurrent_inventory` | Tài liệu chính thức PostgreSQL Chapter 13 (`doc/src/sgml/mvcc.sgml`): cơ chế Read Committed, hành vi tìm dòng đích của `UPDATE` / `SELECT FOR UPDATE` khi có giao dịch đồng thời. | Đặt vào tình huống hai yêu cầu mua sản phẩm cuối cùng (`stock = 1`) qua hai instance ứng dụng dùng chung DB, kèm yêu cầu rollback toàn vẹn nếu bước tạo đơn hàng lỗi. |
| `case.c03.transfer_deadlock.v1` | `source.postgres.mvcc.deadlocks` | Tài liệu chính thức PostgreSQL Chapter 13 (`doc/src/sgml/mvcc.sgml`, mục *Deadlocks*): hai giao dịch đồng thời cập nhật chéo tài khoản `11111` và `22222` gây vòng chờ khóa cấp dòng. | Chuyển thành tình huống chuyển điểm hai chiều giữa ví `11111` và `22222`; tách rõ ràng buộc khác với `inventory_race` (khóa nhiều dòng ngược thứ tự thay vì tranh chấp một dòng), yêu cầu chuẩn hóa thứ tự khóa (`lock ordering`) và kiểm thử bảo toàn tổng số dư. |

### 2.3. Công việc `C04` — Nhóm `algorithm_explanation` (`skill.algorithms.correctness_and_complexity`)
- **File lưu trữ:** [`data/seed/questions/algorithms.json`](../data/seed/questions/algorithms.json)
- **Fixture review độc lập:** [`test/fixtures/question_reviews/c04.json`](../test/fixtures/question_reviews/c04.json)
- **Người tuyển chọn / Người duyệt:** `nkphuc` → `Tin` (`status: "approved"`)

| Mã câu hỏi (`id`) | Mã `source_id` | Nội dung gốc tại nguồn thực tế | Tóm tắt biên tập & thích nghi (`adaptation`) |
| --- | --- | --- | --- |
| `algo.c04.bisect_left_bounds.v1` | `source.thealgorithms.python.bisect_left` | Hàm `bisect_left(sorted_collection, item, lo=0, hi=-1)` trong `searches/binary_search.py` của `TheAlgorithms/Python`. | Giữ nguyên mã nguồn hàm `bisect_left`; yêu cầu ứng viên giải thích bất biến phân hoạch `< item` / `>= item`, lý do trả đúng vị trí biên trái khi có phần tử trùng, độ phức tạp `O(log n)` / `O(1)` và ca biên. |
| `algo.c04.balanced_brackets_stack.v1` | `source.thealgorithms.python.balanced_parentheses` | Hàm `balanced_parentheses(parentheses: str) -> bool` trong `data_structures/stacks/balanced_parentheses.py` của `TheAlgorithms/Python`. | Thay lớp bọc `Stack` nội bộ của repo gốc bằng `list[str]` chuẩn của Python để đề bài tự chứa độc lập; yêu cầu giải thích nguyên lý LIFO, điều kiện `return not stack` cuối hàm, bộ nhớ xấu nhất `O(n)` và các ca ngoặc đan chéo `'[(])'`. |

### 2.4. Công việc `C05` — Nhóm `ai_code_review` (`skill.engineering.code_review_and_verification`)
- **File lưu trữ:** [`data/seed/questions/ai_review.json`](../data/seed/questions/ai_review.json)
- **Fixture review độc lập:** [`test/fixtures/question_reviews/c05.json`](../test/fixtures/question_reviews/c05.json)
- **Người tuyển chọn / Người duyệt:** `nguyentrg` → `Tin` (`status: "approved"`)

| Mã câu hỏi (`id`) | Mã `source_id` | Nội dung gốc tại nguồn thực tế | Tóm tắt biên tập & minh bạch lỗi cài đặt (`adaptation`) |
| --- | --- | --- | --- |
| `review.c05.binary_search_precheck.v1` | `source.thealgorithms.python.binary_search_fn` | Nguyên bản hàm `binary_search` trong `searches/binary_search.py` của `TheAlgorithms/Python` có dòng `if any(a > b for a, b in pairwise(sorted_collection)):`. | Sử dụng **nguyên bản mã thực tế** (không tự gán là do AI sinh); đặt vào hợp đồng đường nóng yêu cầu `O(log n)` trên chỉ mục đã sắp sẵn để ứng viên phát hiện bước quét `pairwise` làm suy biến mọi lượt gọi hợp lệ thành `O(n)`. |
| `review.c05.sql_query_parameterization.v1` | `source.owasp.query_parameterization` | Mẫu truy vấn tham số hóa `SELECT account_balance FROM user_data WHERE user_name = ?` trong `Query_Parameterization_Cheat_Sheet.md` của `OWASP/CheatSheetSeries`. | Chuyển sang Python `sqlite3` và **ghi chú minh bạch** hai lỗi trong đoạn mã đề bài (ghép chuỗi f-string gây SQL Injection và `cursor.fetchone()[0]` gây `TypeError` khi vắng người dùng) là do nhóm chủ động cài vào để luyện review, không phải lỗi của tác giả OWASP và không mạo nhận là log sinh từ AI. |

---

## 3. Chi tiết bàn giao 5 bài tập luyện tập (`C06`)

- **File lưu trữ:** [`data/seed/exercises.json`](../data/seed/exercises.json)
- **Ghi công bản quyền:** [`docs/THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

| Mã bài tập (`id`) | Kỹ năng (`related_skill_ids`) | Loại tiêu chí phủ (`target_criterion_types`) | Tiên quyết (`prerequisite_ids`) | Thời lượng ước tính | Mã nguồn (`source_id`) |
| --- | --- | --- | --- | :---: | --- |
| `exercise.programming.mutable_defaults_and_binding` | `skill.programming.code_semantics` | `behavior_explanation`, `contract_preservation`, `test_design` | `[]` | ~25 phút *(ước tính)* | `source.cpython.faq.mutable_defaults` |
| `exercise.backend.atomic_transaction_locking` | `skill.backend.data_consistency` | `failure_analysis`, `invariant_preservation` | `[]` | ~30 phút *(ước tính)* | `source.postgres.mvcc.deadlocks` |
| `exercise.backend.rollback_invariant_test` | `skill.backend.data_consistency` | `test_design`, `invariant_preservation` | `["exercise.backend.atomic_transaction_locking"]` | ~25 phút *(ước tính)* | `source.c03.concurrent_inventory` |
| `exercise.algorithms.loop_invariant_and_bounds` | `skill.algorithms.correctness_and_complexity` | `correctness_argument`, `complexity_analysis`, `test_design` | `[]` | ~30 phút *(ước tính)* | `source.tech_interview_handbook.array_stack` |
| `exercise.engineering.contract_and_security_review` | `skill.engineering.code_review_and_verification` | `failure_analysis`, `contract_preservation`, `test_design` | `[]` | ~25 phút *(ước tính)* | `source.owasp.query_parameterization` |

---

## 4. Lệnh kiểm chứng tự động

Chạy bộ kiểm tra tính toàn vẹn nguồn gốc, giấy phép, độ phủ khung phiên 4 câu, trích dẫn nguyên văn trong review fixture và đồ thị bài tập tiên quyết:

```powershell
uv run --locked python -m pytest test/content/test_seed_catalog.py test/test_api_contract.py -q
```
