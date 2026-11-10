# C01 Danh mục kỹ năng và khung phiên

[Phạm vi P01](scope.md) quy định một phiên luyện phỏng vấn Backend Intern/Fresher
gồm bốn câu tiếng Việt. [Danh mục kỹ năng](../data/seed/skills.json) định nghĩa
hành vi quan sát được qua câu trả lời. Giữ nguyên ID khi sửa nhãn hoặc cách diễn
đạt. Nếu thay đổi năng lực cần đánh giá, tạo ID mới và cập nhật khung phiên.

## Gắn kỹ năng với câu hỏi và rubric

[Khung phiên](../data/seed/session_blueprints.json) quy định một câu cho mỗi ô,
theo thứ tự trong `slots`. Một câu đủ điều kiện cho ô khi `category` khớp và
`skill_ids` chứa `skill_id` của ô. Mọi ID khác trong `skill_ids` cũng phải có
trong danh mục.

| Nhóm câu | Skill ID bắt buộc | Bằng chứng chính |
| --- | --- | --- |
| `programming_knowledge` | `skill.programming.code_semantics` | Dự đoán kết quả và giải thích quy tắc ngôn ngữ. |
| `technical_case` | `skill.backend.data_consistency` | Chỉ ra tình huống gây sai dữ liệu và cách bảo vệ bất biến. |
| `algorithm_explanation` | `skill.algorithms.correctness_and_complexity` | Giải thích tính đúng và độ phức tạp của phương án. |
| `ai_code_review` | `skill.engineering.code_review_and_verification` | Chỉ ra lỗi so với yêu cầu và cách kiểm chứng bản sửa. |

Reviewer đối chiếu từng tiêu chí với `eligible_criterion_types` của ô. Chọn loại
phù hợp với yêu cầu trong đề và mô tả dấu hiệu cần thấy ở từng mức điểm. P05 và C08
thống nhất cách lưu loại tiêu chí khi chốt schema rubric.

| Loại tiêu chí | Bằng chứng quan sát được |
| --- | --- |
| `behavior_explanation` | Nêu kết quả và quy tắc giải thích hành vi của mã. |
| `failure_analysis` | Chỉ ra đầu vào hoặc thứ tự thao tác khiến hệ thống vi phạm yêu cầu. |
| `contract_preservation` | Giải thích bản sửa giữ hành vi mà bên gọi cần. |
| `invariant_preservation` | Nêu bất biến và giải thích vì sao cách xử lý giữ được bất biến. |
| `correctness_argument` | Giải thích vì sao phương án cho kết quả đúng, kể cả trường hợp biên. |
| `complexity_analysis` | Gắn chi phí thời gian và bộ nhớ với các bước thực hiện. |
| `test_design` | Nêu đầu vào, thao tác và kết quả mong đợi đủ cụ thể để kiểm chứng. |

## Metadata dùng để duyệt và chọn câu

| Metadata | Yêu cầu |
| --- | --- |
| `role`, `level`, `language` | Dùng `backend_developer`, `intern_fresher` và `vi` cho khung MVP. |
| `difficulty` | Reviewer gắn `foundational` cho câu tập trung vào một quy tắc hoặc một tình huống trực tiếp, `applied` cho câu cần phối hợp nhiều bước, xử lý trường hợp biên hoặc giải thích đánh đổi. Cả hai thuộc phạm vi Intern/Fresher. |
| `source_id` và bản ghi nguồn | Trỏ đến nguồn của đúng đoạn mã hoặc nội dung được dùng. Lưu URL gốc, revision nếu có, tác giả, giấy phép, thời điểm thu thập, nội dung gốc, ghi công và các thay đổi khi dịch hoặc biên tập. |
| Phiên bản và review | Giữ ID và phiên bản của câu và rubric. Chỉ tính bản ghi khi nguồn và giấy phép đã được xác minh, `review.status` là `approved`, người duyệt khác người tuyển chọn và các mục kiểm tra review đã hoàn tất. |
| `example_only` | Loại bản ghi minh họa khỏi ngân hàng dùng để tạo phiên. |

Xem [quy trình nguồn mở](QUESTION_SOURCES.md) và [hợp đồng P03](data_contract.md)
để ghi provenance và review. C02–C05 dùng skill ID theo bảng khi soạn bản ghi
thật. Các ID `example.*` trong [mẫu soạn câu](QUESTION_JSON_FORMAT.md) vẫn dành cho
minh họa.

## Báo thiếu độ phủ

C08 kiểm tra metadata và cung cấp danh sách câu hợp lệ, mỗi ID câu chỉ có một
phiên bản đang dùng. Service [missing_coverage](../source/service/coverage.py)
nhận ánh xạ `category → skill_id` từ khung phiên và danh sách đó. Kết quả là các
nhóm còn thiếu cùng skill ID tương ứng. Ngân hàng rỗng báo thiếu cả bốn nhóm.

I01 áp dụng `on_missing_coverage: error` khi thiếu bất kỳ ô nào. Dừng tạo phiên
và báo nhóm, kỹ năng còn thiếu. Một ID câu chỉ được dùng cho một ô. Khi kiểm tra
các ô còn lại của phiên, loại ID câu đã dùng trước khi kiểm tra độ phủ.

Chạy `uv run --locked python -m pytest test/test_session_coverage.py` để kiểm tra
khung và cách báo thiếu bằng câu tổng hợp. C08 và I01 sẽ xác nhận lại với ngân
hàng câu đã duyệt và luồng mở phiên.
