# Hướng dẫn thực hiện từng công việc

Các đường dẫn tương đối thuộc repository ứng dụng Python, không phải thư mục dashboard. Tạo file khi chưa có; chỉ ghi kiểm tra đã thực sự thực hiện. Câu hỏi VA được tuyển chọn từ nguồn mở có giấy phép và được review.

## P01 — Chốt phạm vi, vai trò và cấp độ

File cần mở hoặc tạo:

- `docs/scope.md`
- `docs/PROJECT_PLAN.md`

Các bước:

1. Chốt Backend Intern/Fresher và bốn nhóm câu: lập trình, case, thuật toán, đánh giá code AI.
2. Ghi rõ nguồn câu hỏi là tài liệu/mã nguồn mở có giấy phép; nhóm chọn lọc, dịch và xây rubric.
3. Liệt kê MVP, phần hoãn, người duyệt và hạn dự kiến; thống nhất trước khi nhận các việc phụ thuộc.

Kiểm tra hoàn thành:

- Từng thành viên mô tả cùng một luồng bốn câu và đầu ra.
- Các mục chưa chốt được đánh dấu rõ, không xem là yêu cầu đã xác nhận.

## P02 — Vẽ luồng người dùng và cách phục hồi lỗi

File cần mở hoặc tạo:

- `docs/user_flow.md`
- `docs/ui_direction.md`

Các bước:

1. Vẽ luồng bắt đầu, thiết lập, workspace, kết quả, tổng kết và bài tập.
2. Với mỗi màn hình ghi dữ liệu đầu vào, hành động chính và API dự kiến.
3. Bổ sung nhánh rỗng, gửi trùng, API lỗi, retry và hết phiên; giữ câu trả lời đang nhập.

Kiểm tra hoàn thành:

- Đi theo sơ đồ từ đầu tới bài tập mà không gặp ngõ cụt.
- Một người khác chỉ ra được cách phục hồi khi API đánh giá thất bại.

## P03 — Định nghĩa dữ liệu, mã và phiên bản

File cần mở hoặc tạo:

- `docs/data_contract.md`
- `source/Model/question.py`
- `source/Model/evaluation.py`

Các bước:

1. Liệt kê Skill, Question, Rubric, Criterion, Session, Answer, Evidence, Result và Exercise.
2. Định nghĩa ID, tham chiếu, enum trạng thái, trường null và phiên bản; thêm URL nguồn, giấy phép, revision nguồn, người review.
3. Viết một bộ JSON ví dụ có quan hệ đầy đủ và một bộ sai để cả nhóm thảo luận.

Kiểm tra hoàn thành:

- Truy được phản hồi về tiêu chí, rubric và đúng câu trả lời gốc.
- Phân biệt được điểm 0, chưa đủ bằng chứng và lỗi xử lý.

## P04 — Thống nhất API và dữ liệu mẫu

File cần mở hoặc tạo:

- `docs/api_contract.md`
- `source/Control/schemas.py`
- `test/fixtures/api/`

Các bước:

1. Viết request/response mẫu cho mở phiên, gửi bài, đánh giá, chuyển câu, tổng kết và bài tập.
2. Chốt mã lỗi, quyền truy cập phiên, client submission ID và quy tắc retry.
3. Đưa JSON thành fixture chung để UI và backend phát triển đồng thời.

Kiểm tra hoàn thành:

- UI hiển thị được một kết quả từ fixture mà không đoán tên trường.
- Có ví dụ cho đầu vào sai, phiên không thuộc người dùng và timeout.

## P05 — Viết một case và rubric hoàn chỉnh

File cần mở hoặc tạo:

- `data/seed/questions/cases.json`
- `docs/rubric_guide.md`
- `data/seed/source_registry.json`

Các bước:

1. Chọn một case từ nguồn mở phù hợp; ghi link file gốc, giấy phép và revision trước khi sử dụng.
2. Giữ bản gốc riêng, dịch/adapt có ghi thay đổi; định nghĩa tiêu chí và mức điểm quan sát được.
3. Soạn ví dụ đúng, thiếu và mơ hồ; nhờ người khác chấm độc lập và sửa điểm bất đồng.

Kiểm tra hoàn thành:

- Rubric chấp nhận lời giải đúng khác đáp án tham chiếu.
- Reviewer dùng rubric phân biệt được thiếu yêu cầu với chưa đủ căn cứ.

## P06 — Chốt wireframe và bộ quy chuẩn UI

File cần mở hoặc tạo:

- `docs/ui_direction.md`
- `docs/user_flow.md`
- `source/view/static/css/tokens.css`

Các bước:

1. Phác thảo workspace và kết quả, ưu tiên câu hỏi, ô trả lời và đoạn căn cứ.
2. Chốt màu, font có dấu tiếng Việt, khoảng cách, cỡ chữ và nhãn hành động.
3. Review bản hẹp/desktop và trạng thái focus, loading, lỗi trước khi xây component.

Kiểm tra hoàn thành:

- Wireframe thể hiện được chọn tiêu chí để xem đúng căn cứ.
- Các nhãn nhất quán và có phương án trình bày ở màn hình hẹp.

## P07 — Khảo sát Gemini, SDK, quota và ngân sách

File cần mở hoặc tạo:

- `docs/ai_decision.md`
- `.env.example`
- `source/service/providers/gemini_provider.py`

Các bước:

1. Kiểm tra tài khoản AI Studio, model có structured output, quota và SDK thực tế.
2. Thử một yêu cầu tổng hợp nhỏ; ghi schema, thời gian, lỗi và mức dùng nếu có khóa.
3. Chốt model qua cấu hình, ngân sách thử nghiệm và chế độ mẫu khi chưa có quyền dùng API.

Kiểm tra hoàn thành:

- Không đưa khóa vào Git, trình duyệt hoặc ảnh demo.
- Ghi kết quả thật hoặc blocker thật; không ghi fixture là thử API thành công.

## P08 — Thống nhất cách làm việc và review

File cần mở hoặc tạo:

- `docs/team_workflow.md`
- `docs/api_contract.md`

Các bước:

1. Chốt bảng việc, cách đặt nhánh và quy trình một người làm/một người review.
2. Tạo mẫu ticket gồm đầu ra, phụ thuộc, kiểm tra và bằng chứng PR.
3. Thống nhất lịch tích hợp ngắn; đổi hợp đồng phải cập nhật fixture cùng lúc.

Kiểm tra hoàn thành:

- Mỗi việc được nhận đều có đầu ra và người review rõ.
- Định nghĩa Xong bao gồm tích hợp và bằng chứng kiểm tra.

## F01 — Thiết lập dự án và phụ thuộc Python

F01 đã có trên `main`. Xem các lệnh cài đặt và kết quả kiểm tra trên Windows trong [README](../README.md#python-development-setup).

File cần mở hoặc tạo:

- `pyproject.toml`
- `uv.lock`
- `README.md`
- `source/__init__.py`
- `test/conftest.py`

Các bước:

1. Dùng CPython 3.11 và chạy `uv sync --locked` để cài các phiên bản đã khóa.
2. Giữ nguyên tên và chữ hoa của các package MVC-S.
3. Chạy `uv run --locked python -m pytest` và `uv pip check` theo README.

Kiểm tra hoàn thành:

- Thành viên khác cài được trên môi trường sạch.
- README phân biệt lệnh đã chạy với lệnh dự kiến, không khẳng định app rỗng đã chạy được.

## F02 — Xây các kiểu dữ liệu miền

File cần mở hoặc tạo:

- `source/Model/question.py`
- `source/Model/interview.py`
- `source/Model/evaluation.py`
- `source/Model/exercise.py`

Các bước:

1. Tạo dataclass/kiểu miền theo P03, giữ domain không phụ thuộc web.
2. Thêm ràng buộc ID, enum, tham chiếu và immutable version.
3. Viết fixture hợp lệ và fixture vi phạm từng ràng buộc quan trọng.

Kiểm tra hoàn thành:

- Không có import View, Controller hoặc Service trong Model.
- Điểm null không bị ép về 0 và câu trả lời gốc không bị thay đổi.

## F03 — Định nghĩa interface repository

File cần mở hoặc tạo:

- `source/Model/repositories/interfaces.py`
- `test/fixtures/repositories.py`

Các bước:

1. Liệt kê thao tác đọc nội dung, tạo phiên, lưu bài và lưu kết quả mà Service cần.
2. Định nghĩa Protocol và kiểu trả về; mô tả trường hợp không tìm thấy/lỗi lưu.
3. Tạo fake in-memory nhỏ dùng cho các luồng kiểm tra.

Kiểm tra hoàn thành:

- Service chạy với fake mà không import sqlite3.
- Interface không trả đối tượng HTTP hoặc component giao diện.

## F04 — Tạo schema và lưu trữ SQLite

File cần mở hoặc tạo:

- `source/Model/repositories/schema.sql`
- `source/Model/repositories/sqlite_repository.py`
- `test/Model/test_repository.py`

Các bước:

1. Tạo schema có khóa và phiên bản cho nội dung, phiên, bài và kết quả.
2. Cài repository theo F03, dùng truy vấn tham số và transaction cho thao tác nhiều bản ghi.
3. Kiểm tra đóng/mở lại DB, lỗi giữa transaction và ghi bài trùng.

Kiểm tra hoàn thành:

- Mở lại DB vẫn đọc đúng bài gốc và rubric đã dùng.
- Ghi thất bại không để lại kết quả dang dở hoặc bản trả lời trùng.

## F05 — Kết nối app, router và các lớp

File cần mở hoặc tạo:

- `source/main.py`
- `source/config.py`
- `source/Control/`
- `source/view/pages.py`

Các bước:

1. Tạo app factory và đọc cấu hình tại composition root.
2. Khởi tạo repository, provider, service và controller rồi inject theo interface.
3. Mount trang khung, static assets và health endpoint; tách khỏi logic feature.

Kiểm tra hoàn thành:

- Thay được provider/repository giả trong một lần khởi tạo.
- main.py không chứa thuật toán chấm điểm hoặc SQL.

## F06 — Cấu hình biến môi trường và dữ liệu riêng

File cần mở hoặc tạo:

- `.env.example`
- `.gitignore`
- `source/config.py`
- `README.md`

Các bước:

1. Khai báo tên biến cho provider, model, timeout và đường dẫn DB bằng placeholder.
2. Bổ sung ignore có mục tiêu cho khóa, DB, log và bản ghi riêng.
3. Kiểm tra cấu hình thiếu/sai và hướng dẫn sửa; không in khóa ra lỗi.

Kiểm tra hoàn thành:

- git status không liệt kê khóa thật hoặc DB phát sinh.
- Chế độ thật thiếu khóa báo lỗi rõ; chế độ mẫu được đánh dấu minh họa.

## C01 — Định nghĩa skill ID và khung phiên

File cần mở hoặc tạo:

- `data/seed/skills.json`
- `data/seed/session_blueprints.json`
- `docs/content_guide.md`

Các bước:

1. Chốt skill ID ổn định và định nghĩa quan sát được cho từng kỹ năng.
2. Ánh xạ bốn nhóm câu vào blueprint phiên tối thiểu.
3. Định nghĩa metadata nguồn mở, độ khó dự kiến và trạng thái review để chọn câu.

Kiểm tra hoàn thành:

- Mỗi câu hỏi có skill ID nằm trong danh mục.
- Blueprint báo thiếu dữ liệu thay vì lặp câu hoặc bỏ nhóm câu âm thầm.

## C02 — Kiếm các câu hỏi về kiến thức lập trình

File cần mở hoặc tạo:

- `data/seed/questions/programming.json`
- `data/seed/source_registry.json`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/QUESTION_JSON_FORMAT.md`

Các bước:

1. Tìm hai câu kiến thức từ nguồn mở có giấy phép phù hợp, không chỉ trang đọc miễn phí.
2. Ghi URL file, tác giả, giấy phép, revision, thời điểm lấy; dịch và ghi thay đổi.
3. Gắn skill ID, rubric, ví dụ lời giải tương đương và reviewer nội dung.
4. Mở mẫu JSON và rubric bên dưới; tạo bản ghi thật với nguồn đã xác minh, giữ draft trong lúc chuẩn hóa và gửi review.

Kiểm tra hoàn thành:

- Có thể mở nguồn và tìm đúng nội dung đã chọn.
- Mỗi câu qua kiểm tra nội dung, ghi công và import; chưa review không được đưa vào phiên.
- JSON parse được, source_id khớp source registry và rubric có ID/version. Chỉ approved sau review độc lập; mọi mẫu example_only=true phải bị loại khỏi import thật.

Mẫu JSON câu hỏi, nguồn, fixture và rubric có trong docs/QUESTION_JSON_FORMAT.md và khối Mẫu JSON & rubric của việc này trên board.

## C03 — Kiếm các câu hỏi về tình huống kỹ thuật

File cần mở hoặc tạo:

- `data/seed/questions/cases.json`
- `data/seed/source_registry.json`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/QUESTION_JSON_FORMAT.md`

Các bước:

1. Chọn/adapt hai case kỹ thuật từ nguồn mở có quyền tái sử dụng.
2. Giữ ràng buộc và căn cứ kỹ thuật; ghi rõ phần bối cảnh do nhóm thay đổi.
3. Xây rubric cho từng biến thể và nhờ reviewer so độ khó/cấu trúc kiểm tra.
4. Mở mẫu JSON và rubric bên dưới; tạo bản ghi thật với nguồn đã xác minh, giữ draft trong lúc chuẩn hóa và gửi review.

Kiểm tra hoàn thành:

- Cùng chủ đề không bị khẳng định là tương đương khi khác ràng buộc.
- Nguồn, thay đổi và lý do chấp nhận từng lời giải được ghi lại.
- JSON parse được, source_id khớp source registry và rubric có ID/version. Chỉ approved sau review độc lập; mọi mẫu example_only=true phải bị loại khỏi import thật.

Mẫu JSON câu hỏi, nguồn, fixture và rubric có trong docs/QUESTION_JSON_FORMAT.md và khối Mẫu JSON & rubric của việc này trên board.

## C04 — Kiếm các câu hỏi về giải thích thuật toán

File cần mở hoặc tạo:

- `data/seed/questions/algorithms.json`
- `data/seed/source_registry.json`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/QUESTION_JSON_FORMAT.md`

Các bước:

1. Chọn hai thuật toán/bài giải nguồn mở phù hợp intern/fresher, ví dụ từ TheAlgorithms/Python.
2. Biến nội dung thành yêu cầu giải thích đúng đắn, dữ liệu biên và độ phức tạp; ghi bản gốc và phần thích nghi.
3. Review đáp án, rubric và các cách giải khác hợp lệ.
4. Mở mẫu JSON và rubric bên dưới; tạo bản ghi thật với nguồn đã xác minh, giữ draft trong lúc chuẩn hóa và gửi review.

Kiểm tra hoàn thành:

- Không sao chép đề từ liên kết bên ngoài nếu đề đó không thuộc giấy phép nguồn.
- Rubric không chấm theo khớp chữ với một lời giải duy nhất.
- JSON parse được, source_id khớp source registry và rubric có ID/version. Chỉ approved sau review độc lập; mọi mẫu example_only=true phải bị loại khỏi import thật.

Mẫu JSON câu hỏi, nguồn, fixture và rubric có trong docs/QUESTION_JSON_FORMAT.md và khối Mẫu JSON & rubric của việc này trên board.

## C05 — Kiếm các câu hỏi về đánh giá code khi dùng AI

File cần mở hoặc tạo:

- `data/seed/questions/ai_review.json`
- `data/seed/source_registry.json`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/QUESTION_JSON_FORMAT.md`

Các bước:

1. Chọn đoạn code nguồn mở có giấy phép và tạo tình huống kiểm tra code khi dùng trợ lý AI.
2. Nếu chủ động thêm lỗi, ghi rõ đây là bản sửa phục vụ bài tập, không gán lỗi cho tác giả gốc.
3. Viết yêu cầu phát hiện lỗi, kiểm chứng, sửa và giải thích; review test biên.
4. Mở mẫu JSON và rubric bên dưới; tạo bản ghi thật với nguồn đã xác minh, giữ draft trong lúc chuẩn hóa và gửi review.

Kiểm tra hoàn thành:

- Không tuyên bố code do AI sinh nếu không có căn cứ.
- Giấy phép, attribution, bản sửa và các lỗi kỳ vọng đều truy xuất được.
- JSON parse được, source_id khớp source registry và rubric có ID/version. Chỉ approved sau review độc lập; mọi mẫu example_only=true phải bị loại khỏi import thật.

Mẫu JSON câu hỏi, nguồn, fixture và rubric có trong docs/QUESTION_JSON_FORMAT.md và khối Mẫu JSON & rubric của việc này trên board.

## C06 — Xây danh mục bài tập và ánh xạ điểm thiếu

File cần mở hoặc tạo:

- `data/seed/exercises.json`
- `data/seed/skills.json`
- `source/Model/exercise.py`

Các bước:

1. Chọn bài luyện từ tài liệu nguồn mở hoặc nội dung nhóm có quyền dùng; ghi nguồn.
2. Ánh xạ criterion gap -> skill ID -> bài tập và prerequisite IDs.
3. Viết hướng dẫn, mục tiêu, thời lượng ước tính và kết quả cần quan sát.

Kiểm tra hoàn thành:

- Mỗi khoảng thiếu trong seed có bài phù hợp hoặc no-match rõ ràng.
- Không tạo prerequisite không tồn tại hoặc thời lượng như một cam kết chắc chắn.

## C07 — Chuẩn bị 24 câu trả lời kiểm định

File cần mở hoặc tạo:

- `test/fixtures/answers/`
- `test/fixtures/expected_evaluations.json`
- `docs/evaluation_protocol.md`

Các bước:

1. Tạo 24 câu trả lời tổng hợp phủ bốn nhóm câu, gồm đúng, thiếu, sai, tương đương, mơ hồ và chèn chỉ dẫn.
2. Hai người gán tiêu chí độc lập, ghi bất đồng và thống nhất nhãn tham chiếu.
3. Tách bộ hiệu chỉnh và bộ giữ lại trước khi thử prompt/model.

Kiểm tra hoàn thành:

- Không đưa hồ sơ sinh viên thật vào fixture.
- Bộ giữ lại không bị dùng để sửa prompt rồi vẫn báo là kiểm định độc lập.

## C08 — Kiểm tra và import ngân hàng câu hỏi

File cần mở hoặc tạo:

- `source/service/question_bank_service.py`
- `source/Model/repositories/sqlite_repository.py`
- `data/seed/`

Các bước:

1. Đọc schema seed và kiểm tra skill ID, rubric, nguồn, license, review và phiên bản.
2. Import bản hợp lệ trong transaction; báo lỗi từng bản ghi có mã và vị trí.
3. Chặn cả bộ nếu thiếu độ phủ bắt buộc hoặc dữ liệu cốt lõi không đáng tin.

Kiểm tra hoàn thành:

- Câu thiếu giấy phép hoặc chưa review không được dùng trong phiên.
- Một bản ghi sai không bị bỏ qua âm thầm; báo cáo nêu dữ liệu đã/không import.

## E01 — Định nghĩa interface diễn giải bằng chứng

File cần mở hoặc tạo:

- `source/service/providers/interfaces.py`
- `source/Model/evaluation.py`

Các bước:

1. Định nghĩa EvidenceInterpreter nhận câu hỏi, rubric và bài gốc.
2. Khai báo đầu ra có criterion ID, quan sát, trích dẫn và lý do chưa kết luận.
3. Giữ interface độc lập Gemini SDK và tách lỗi provider khỏi kết quả học tập.

Kiểm tra hoàn thành:

- Provider mẫu và thật có thể thay thế qua cùng interface.
- Không yêu cầu provider trả điểm cuối hoặc nhãn năng lực toàn diện.

## E02 — Tạo provider dữ liệu mẫu

File cần mở hoặc tạo:

- `source/service/providers/fixture_provider.py`
- `test/fixtures/provider_outputs.json`

Các bước:

1. Chuẩn bị đầu ra mẫu cho đúng, sai, thiếu căn cứ và lỗi provider.
2. Cài provider trả fixture theo định danh thay vì gọi mạng.
3. Đưa metadata demo-mode vào kết quả để UI hiển thị.

Kiểm tra hoàn thành:

- Hoàn tất một câu qua mọi lớp khi không có internet/khóa.
- Màn hình và báo cáo phân biệt rõ dữ liệu minh họa với kết quả API thật.

## E03 — Viết prompt diễn giải câu trả lời

File cần mở hoặc tạo:

- `source/service/prompts/interpret_answer.txt`
- `test/fixtures/answers/`

Các bước:

1. Viết chỉ dẫn tin cậy tách khỏi câu hỏi, code và câu trả lời như dữ liệu.
2. Yêu cầu kiểm tra từng criterion ID, trích dẫn đúng nguyên văn và không bổ sung ý cho người dùng.
3. Thử trên bộ hiệu chỉnh, gồm câu cố yêu cầu bỏ rubric; ghi phiên bản prompt.

Kiểm tra hoàn thành:

- Câu chèn chỉ dẫn không đổi nhiệm vụ đánh giá.
- Prompt chấp nhận cách giải tương đương và cho phép chưa đủ căn cứ.

## E04 — Tích hợp Gemini và JSON có cấu trúc

File cần mở hoặc tạo:

- `source/service/providers/gemini_provider.py`
- `source/config.py`
- `test/service/test_gemini_provider.py`

Các bước:

1. Dùng SDK và model đã chốt ở P07, tạo request structured output theo E01.
2. Parse JSON tại ranh giới, xử lý refusal, output thiếu và schema sai.
3. Thử một yêu cầu tổng hợp có kiểm soát; lưu model/prompt version và thời gian.

Kiểm tra hoàn thành:

- Mock kiểm tra parse hợp lệ và output sai.
- Live check dùng model thật, ghi kết quả hoặc blocker; khóa chỉ nằm ở server.

## E05 — Kiểm tra tiêu chí và trích dẫn gốc

File cần mở hoặc tạo:

- `source/service/evaluation_service.py`
- `test/service/test_evidence_validation.py`

Các bước:

1. Yêu cầu đúng một check cho mỗi tiêu chí, loại ID lạ hoặc trùng.
2. Kiểm tra đoạn trích và offsets so với nguyên văn đã lưu.
3. Giữ observation về phần thiếu tách khỏi quote; output không kiểm chứng được bị trả lỗi.

Kiểm tra hoàn thành:

- Trích dẫn bịa, lệch đoạn hoặc thiếu tiêu chí không trở thành điểm công bố.
- Cùng đầu vào và cùng check hợp lệ cho kết quả xác thực nhất quán.

## E06 — Tính điểm bằng quy tắc rubric

File cần mở hoặc tạo:

- `source/service/scoring_service.py`
- `test/service/test_scoring.py`
- `docs/rubric_guide.md`

Các bước:

1. Cài quy tắc ánh xạ check hợp lệ sang mức điểm đã khai báo trong rubric.
2. Xử lý null, tiêu chí bắt buộc và điều kiện có/không được tổng hợp.
3. Viết kiểm tra từng ranh giới giữa hai mức liền kề.

Kiểm tra hoàn thành:

- Không dùng LLM để cộng điểm hoặc suy diễn tổng điểm.
- Chưa đủ căn cứ không bị đổi thành 0; không cộng raw score giữa rubric khác nhau.

## E07 — Tạo phản hồi từ kết quả đã kiểm tra

File cần mở hoặc tạo:

- `source/service/evaluation_service.py`
- `source/Model/evaluation.py`
- `test/service/test_feedback.py`

Các bước:

1. Tạo feedback có cấu trúc từ criterion checks và điểm Python đã tính.
2. Mỗi thiếu sót tham chiếu đúng criterion và căn cứ, giới hạn trong câu đang xét.
3. Dùng template giải thích cho bản đầu; không gọi AI để chấm lại khi tạo lời nhận xét.

Kiểm tra hoàn thành:

- Feedback không đưa ra điểm khác EvaluationResult.
- Chỉ confirmed issues dẫn tới gợi ý cải thiện; uncertainty được giữ rõ.

## E08 — Xử lý timeout, quota, retry và log

File cần mở hoặc tạo:

- `source/service/providers/gemini_provider.py`
- `source/config.py`
- `test/service/test_provider_failures.py`

Các bước:

1. Cấu hình giới hạn input/output, timeout, ngân sách request và retry hữu hạn.
2. Chỉ retry lỗi tạm thời phù hợp; phân biệt quota, timeout, refusal và output sai.
3. Log mã yêu cầu, thời gian và loại lỗi mà không log khóa/bài làm riêng.

Kiểm tra hoàn thành:

- Mock lỗi không dẫn tới retry vô hạn hoặc gọi thêm ngoài ngân sách.
- Lỗi provider không tạo kết luận người dùng thiếu năng lực.

## E09 — Kết nối diễn giải, chấm và lưu kết quả

File cần mở hoặc tạo:

- `source/service/evaluation_service.py`
- `source/Model/repositories/interfaces.py`
- `test/service/test_evaluation_flow.py`

Các bước:

1. Đọc bản trả lời và snapshot rubric đã lưu, gọi interpreter qua interface.
2. Xác thực, tính điểm, tạo feedback rồi lưu kết quả trong luồng nhất quán.
3. Thử provider mẫu trước, sau đó cắm provider thật mà không đổi Controller/View.

Kiểm tra hoàn thành:

- Câu đã đánh giá dùng lại đúng kết quả khi retry.
- Thất bại giữa các bước không tạo kết quả bán phần hoặc sửa bản gốc.

## I01 — Chọn câu hỏi và quản lý trạng thái phiên

File cần mở hoặc tạo:

- `source/service/interview_service.py`
- `data/seed/session_blueprints.json`
- `test/service/test_interview.py`

Các bước:

1. Định nghĩa các trạng thái hợp lệ và điều kiện chuyển bước.
2. Chọn câu đã review theo coverage, kỹ năng, level và lịch sử câu dùng.
3. Trả lỗi có ngữ cảnh nếu ngân hàng không đáp ứng blueprint.

Kiểm tra hoàn thành:

- Không chuyển câu trái thứ tự hoặc lặp khi còn biến thể phù hợp.
- Bốn nhóm câu được bao phủ đúng khi nội dung đủ.

## I02 — Tạo API mở và đọc phiên

File cần mở hoặc tạo:

- `source/Control/interview_controller.py`
- `source/Control/schemas.py`
- `test/Control/test_sessions.py`

Các bước:

1. Tạo request/response DTO theo P04.
2. Gắn phiên với định danh anonymous phía server; gọi InterviewService.
3. Ánh xạ input sai, không tồn tại và không thuộc người dùng thành lỗi phù hợp.

Kiểm tra hoàn thành:

- ID phiên tự đoán không mở được phiên của người khác.
- Controller không viết SQL, gọi Gemini hoặc import component View.

## I03 — Lưu bài trả lời và chống gửi trùng

File cần mở hoặc tạo:

- `source/Control/interview_controller.py`
- `source/service/interview_service.py`
- `source/Model/repositories/sqlite_repository.py`

Các bước:

1. Nhận question ID, nguyên văn và client submission ID; kiểm tra câu thuộc bước hiện tại.
2. Lưu nguyên văn trước khi đánh giá, gắn question/rubric version.
3. Thêm ràng buộc idempotency và transaction tại repository.

Kiểm tra hoàn thành:

- Hai lần gửi cùng submission ID trả về cùng answer ID.
- Retry API đánh giá không làm mất hoặc nhân đôi bài trả lời.

## I04 — Tạo API đánh giá, đọc kết quả và retry

File cần mở hoặc tạo:

- `source/Control/evaluation_controller.py`
- `source/service/evaluation_service.py`
- `test/Control/test_evaluations.py`

Các bước:

1. Tạo endpoint đánh giá và đọc kết quả cho bài thuộc phiên người dùng.
2. Đặt trạng thái đang xử lý, dùng lại kết quả hoàn tất và chặn ghi trùng.
3. Cho retry bản đã lưu khi lỗi phục hồi được, kèm mã lỗi/thông điệp rõ.

Kiểm tra hoàn thành:

- Hai request cùng lúc không tạo hai EvaluationResult cho cùng revision.
- Timeout giữ bài gốc và cung cấp hành động thử lại.

## I05 — Chuyển câu và tổng kết phiên

File cần mở hoặc tạo:

- `source/Control/interview_controller.py`
- `source/service/interview_service.py`
- `test/Control/test_session_summary.py`

Các bước:

1. Cài hành động next theo trạng thái server, không tin chỉ số từ client.
2. Tổng hợp per-question results, mức độ phủ và các điểm thiếu đã xác nhận.
3. Trả trạng thái kết thúc/phiên chưa xong mà không tạo điểm tổng năng lực.

Kiểm tra hoàn thành:

- Không next qua bài chưa xử lý theo chính sách.
- Summary truy được từng nhận xét về kết quả/căn cứ và nêu phần chưa được đánh giá.

## I06 — Đề xuất bài tập từ điểm thiếu đã xác nhận

File cần mở hoặc tạo:

- `source/service/recommendation_service.py`
- `source/Control/exercise_controller.py`
- `test/service/test_recommendations.py`

Các bước:

1. Lọc confirmed gaps, ánh xạ skill IDs và bài tập đã review.
2. Sắp prerequisite trước bài phụ thuộc và xử lý no-match rõ ràng.
3. Expose dữ liệu bài tập và tạo lượt luyện từ answer đã sở hữu, ưu tiên biến thể khác.

Kiểm tra hoàn thành:

- Mỗi đề xuất có lý do và prerequisite hợp lệ.
- Không đủ căn cứ hoặc hết bài không tạo khuyến nghị giả.

## U01 — Xây layout, màu và component chung

File cần mở hoặc tạo:

- `source/view/templates/base.html`
- `source/view/static/css/tokens.css`
- `source/view/static/css/components.css`

Các bước:

1. Dựng HTML semantic và layout theo P06.
2. Cài token dùng chung, nhãn form, focus rõ và font có dấu.
3. Tạo component trạng thái/button/input để các trang dùng lại.

Kiểm tra hoàn thành:

- Trang hẹp 360px và zoom 200% không cắt điều khiển thiết yếu.
- Có thể đến mọi điều khiển chính bằng bàn phím.

## U02 — Xây trang bắt đầu, lịch sử và thiết lập

File cần mở hoặc tạo:

- `source/view/templates/welcome.html`
- `source/view/templates/setup.html`
- `source/view/pages.py`

Các bước:

1. Dựng trang bắt đầu, lịch sử rỗng và cấu hình role/level theo fixture.
2. Chỉ hỏi dữ liệu cần cho phiên, cho biết format và thời lượng ước tính.
3. Nối hành động mở/tạo phiên qua Controller khi endpoint sẵn sàng.

Kiểm tra hoàn thành:

- Fixture đủ, rỗng và lỗi đều có cách đi tiếp.
- Không thu CV/danh tính dài khi bản đầu không cần.

## U03 — Xây workspace trả lời và giữ bản nháp

File cần mở hoặc tạo:

- `source/view/templates/workspace.html`
- `source/view/static/js/workspace.js`
- `source/view/static/css/workspace.css`

Các bước:

1. Hiển thị câu hỏi, ràng buộc, tiến trình và ô trả lời có label.
2. Giữ bản nháp theo chính sách đã chốt, chống bấm gửi trùng.
3. Gọi API lưu bài trước rồi đánh giá; hiển thị pending/retry rõ ràng.

Kiểm tra hoàn thành:

- Mất mạng khi đánh giá không xóa câu trả lời đang nhập.
- Toàn bộ thao tác đọc/nhập/gửi thực hiện được bằng bàn phím.

## U04 — Hiển thị từng tiêu chí và căn cứ

File cần mở hoặc tạo:

- `source/view/templates/answer_review.html`
- `source/view/static/js/evidence.js`
- `source/view/static/css/results.css`

Các bước:

1. Hiển thị từng criterion, score/null, trạng thái và lời giải thích từ DTO.
2. Cho chọn tiêu chí để mở đúng đoạn nguyên văn và phân biệt phần thiếu/mơ hồ.
3. Hiển thị lỗi xử lý riêng, không tự tính điểm hoặc biến null thành 0.

Kiểm tra hoàn thành:

- Chọn hai tiêu chí khác nhau tới đúng căn cứ tương ứng.
- Nhãn trạng thái hiểu được khi không phân biệt màu sắc.

## U05 — Xây tổng kết phiên và bước tiếp theo

File cần mở hoặc tạo:

- `source/view/templates/summary.html`
- `source/view/static/js/summary.js`

Các bước:

1. Dựng danh sách kết quả từng câu và coverage từ API.
2. Liên kết quan sát điểm thiếu về answer review và bài tập phù hợp.
3. Thêm trường hợp phiên chưa hoàn tất hoặc chưa có đủ kết quả.

Kiểm tra hoàn thành:

- Không hiển thị điểm năng lực tổng bịa từ các raw score.
- Người dùng tìm được lý do cho từng bước luyện tiếp.

## U06 — Xây trang bài tập và luyện lại

File cần mở hoặc tạo:

- `source/view/templates/exercise.html`
- `source/view/static/js/exercise.js`

Các bước:

1. Hiển thị chỉ dẫn, nguồn, lý do chọn, tiên quyết và thời lượng ước tính.
2. Thêm hành động luyện lại bằng biến thể đủ điều kiện từ API.
3. Dựng trạng thái không tìm thấy bài hoặc không còn biến thể.

Kiểm tra hoàn thành:

- Không tự dựng bài tập khi API trả no-match.
- Action luyện lại trỏ tới đúng kỹ năng và không lặp câu khi còn lựa chọn khác.

## U07 — Kết nối toàn bộ UI với API

File cần mở hoặc tạo:

- `source/view/static/js/api_client.js`
- `source/view/static/js/workspace.js`
- `source/view/static/js/summary.js`

Các bước:

1. Thay fixture bằng API client dùng DTO đã thống nhất.
2. Kết nối từng trang ngay khi endpoint sẵn sàng; kiểm tra anonymous session/cookie theo hợp đồng.
3. Chạy trọn luồng với fixture provider, rồi đổi sang provider thật qua cấu hình.

Kiểm tra hoàn thành:

- Frontend không chứa SDK hoặc key AI.
- Luồng bắt đầu -> trả lời -> kết quả -> bài tập hoạt động cùng hợp đồng.

## U08 — Hoàn thiện loading, lỗi, retry và hết phiên

File cần mở hoặc tạo:

- `source/view/templates/`
- `source/view/static/js/api_client.js`
- `source/Control/schemas.py`

Các bước:

1. Liệt kê trạng thái loading, empty, input sai, lỗi mạng/provider và hết phiên.
2. Gắn thông báo và hành động phục hồi, giữ dữ liệu người dùng khi hợp lý.
3. Kiểm tra pending/disabled, focus và thông báo động sau từng hành động.

Kiểm tra hoàn thành:

- Không hiện spinner vô hạn hoặc lỗi không có cách xử lý.
- Gửi trùng bị ngăn ở cả UI và server, dữ liệu nhập vẫn còn sau lỗi.

## Q01 — Kiểm tra rubric và căn cứ bằng pytest

File cần mở hoặc tạo:

- `test/conftest.py`
- `test/service/test_scoring.py`
- `test/service/test_evidence_validation.py`

Các bước:

1. Thiết lập pytest theo môi trường F01 với fixture cục bộ.
2. Viết case có ý nghĩa cho ranh giới rubric, null và phương án tương đương.
3. Kiểm tra missing/duplicate criterion IDs và fabricated quotes; ghi lệnh chạy thật.

Kiểm tra hoàn thành:

- Test thất bại nếu cố đổi null thành 0 hoặc chấp nhận quote giả.
- Không gọi API mạng trong bộ unit test thường xuyên.

## Q02 — Kiểm tra repository và API

File cần mở hoặc tạo:

- `test/Model/test_repository.py`
- `test/Control/test_interview_flow.py`
- `test/fixtures/`

Các bước:

1. Tạo DB tạm và provider mock cho integration test.
2. Kiểm tra ownership, trạng thái, gửi trùng, concurrent retry và lỗi giữa transaction.
3. Thực hiện luồng mở phiên -> gửi bài -> đánh giá -> next -> summary -> bài tập.

Kiểm tra hoàn thành:

- Dữ liệu bị chặn đúng quyền và phục hồi không nhân bản kết quả.
- Các bản ghi tạm được dọn trong môi trường test, không đụng DB dùng thật.

## Q03 — Đánh giá provider thật trên bộ giữ lại

File cần mở hoặc tạo:

- `docs/evaluation_protocol.md`
- `docs/evaluation_report.md`
- `test/fixtures/answers/`

Các bước:

1. Chốt model, prompt và ngưỡng chấp nhận trước khi dùng bộ giữ lại.
2. Chạy bộ giữ lại qua provider thật với ngân sách đã duyệt; ghi số lượng từng nhóm và lỗi.
3. So với nhãn adjudicated, báo agreement, quote validity, unresolved và ví dụ sai.

Kiểm tra hoàn thành:

- Không ghi fixture hoặc mẫu hiệu chỉnh là kết quả held-out độc lập.
- Báo giới hạn mẫu, model/version và thất bại thực tế; không suy ra độ chính xác thị trường.

## Q04 — Kiểm tra màn hình hẹp và bàn phím

File cần mở hoặc tạo:

- `docs/usability_check.md`
- `source/view/templates/`
- `source/view/static/css/`

Các bước:

1. Đi hết luồng ở màn hình hẹp/desktop và zoom 200%.
2. Dùng Tab/Shift+Tab/Enter/Escape để kiểm tra focus, nhãn và thông báo trạng thái.
3. Kiểm tra căn cứ và retry khi lỗi; ghi bước tái hiện, ảnh và task sửa.

Kiểm tra hoàn thành:

- Không có điều khiển chính không tiếp cận được bằng bàn phím.
- Nêu rõ kiểm tra thực tế; không tự tuyên bố đạt toàn bộ WCAG.

## Q05 — Cho người chưa quen UI thử luồng

File cần mở hoặc tạo:

- `docs/user_observations.md`
- `docs/usability_check.md`

Các bước:

1. Chuẩn bị một nhiệm vụ ngắn bằng câu trả lời tổng hợp, không dẫn từng nút.
2. Mời người chưa quen UI hoàn thành và ghi điểm dừng/hiểu nhầm.
3. Xếp hạng vấn đề ảnh hưởng luồng chính rồi tạo task sửa có bằng chứng.

Kiểm tra hoàn thành:

- Có ghi hoàn thành/thất bại và quan sát, không chỉ lời khen.
- Thông tin cá nhân không cần thiết không nằm trong biên bản.

## Q06 — Sửa lỗi chặn bàn giao

File cần mở hoặc tạo:

- `docs/release_checklist.md`
- `test/`
- `source/`

Các bước:

1. Tập hợp lỗi từ test, kiểm định AI và quan sát UI; chọn lỗi chặn bàn giao.
2. Sửa tại đúng lớp MVC-S, bổ sung kiểm tra cho lỗi có thể tái phát.
3. Chạy lại kiểm tra bị ảnh hưởng, cập nhật giới hạn còn lại.

Kiểm tra hoàn thành:

- Không còn lỗi làm mất bài hoặc không thể hoàn thành luồng chính.
- Mỗi lỗi đóng có bước tái hiện trước và bằng chứng sau sửa.

## Q07 — Viết hướng dẫn cài đặt và demo

File cần mở hoặc tạo:

- `README.md`
- `docs/demo_script.md`
- `.env.example`

Các bước:

1. Viết cài đặt, import nội dung nguồn mở và cấu hình provider từ đầu.
2. Đưa lệnh chính xác sau khi thực sự chạy, phân biệt fixture/live và biến môi trường.
3. Nhờ người khác chạy từ checkout sạch và ghi điểm còn thiếu.

Kiểm tra hoàn thành:

- Không cần hỏi tác giả để cài và demo.
- Không có khóa/DB riêng trong tài liệu hoặc gói bàn giao.

## Q08 — Chốt release và tập thuyết trình

File cần mở hoặc tạo:

- `docs/release_checklist.md`
- `docs/final_report.md`
- `docs/demo_script.md`

Các bước:

1. Chốt commit demo và chạy lại các kiểm tra release cần thiết.
2. Chuẩn bị minh chứng decomposition, pattern recognition và abstraction từ quy tắc đã làm.
3. Tập demo phiên bốn câu, nguồn mở, score/evidence, lỗi/retry và bài luyện.

Kiểm tra hoàn thành:

- Chạy được trên máy khác; số liệu báo cáo khớp kết quả đo.
- Slide phân biệt feature đã làm với mở rộng và giả thuyết chưa kiểm chứng.

## X01 — Bổ sung biến thể thứ ba cho mỗi dạng câu

File cần mở hoặc tạo:

- `data/seed/questions/`
- `data/seed/source_registry.json`
- `docs/THIRD_PARTY_NOTICES.md`

Các bước:

1. Chỉ làm sau gate MVP; chọn thêm một biến thể nguồn mở cho mỗi nhóm câu.
2. Ghi giấy phép, nguồn, bản dịch/sửa và rubric tương ứng.
3. Review độc lập độ khó và chạy bộ kiểm tra import.

Kiểm tra hoàn thành:

- Bốn câu mới được kiểm duyệt trước khi chọn trong phiên.
- Không khẳng định ngang độ khó chỉ vì cùng nhãn kỹ năng.

## X02 — Viết một kịch bản Decision Replay

File cần mở hoặc tạo:

- `data/seed/replay_scenarios.json`
- `source/Model/replay.py`

Các bước:

1. Chọn một archetype từ nội dung đã có quyền dùng.
2. Viết checkpoint, lựa chọn, giả định và hệ quả được reviewer xác nhận.
3. Ghi rõ đây là mô phỏng biên soạn, không phải kết quả chạy hệ thống thật.

Kiểm tra hoàn thành:

- Mỗi nhánh có tiền đề và lý do kỹ thuật.
- Không gán một hệ quả chắc chắn cho tình huống thiếu thông tin.

## X03 — Xây timeline Decision Replay

File cần mở hoặc tạo:

- `source/service/replay_service.py`
- `source/Control/replay_controller.py`
- `source/view/templates/replay.html`

Các bước:

1. Cài đọc checkpoint và duyệt nhánh theo kịch bản đã review.
2. Expose dữ liệu qua Controller và dựng timeline có thể chọn.
3. Giữ câu trả lời/kết quả gốc, chỉ bổ sung phần xem lại.

Kiểm tra hoàn thành:

- Chỉ hiện hệ quả trong kịch bản, không tự bịa nhánh.
- Tác vụ replay không sửa điểm đã công bố.

## X04 — Định nghĩa quy tắc hỏi thích ứng

File cần mở hoặc tạo:

- `docs/adaptive_policy.md`
- `source/service/question_selection_policy.py`

Các bước:

1. Chốt mục tiêu hỏi thêm từ confirmed gap hoặc phần chưa rõ.
2. Đặt minimum coverage, số lượt tối đa và điều kiện dừng.
3. Mô tả xếp ưu tiên, tránh lặp và giải thích quyết định.

Kiểm tra hoàn thành:

- Chưa rõ không bị kết luận sai ngay.
- Mọi nhánh đều dừng được khi hết lượt/thời gian/nội dung phù hợp.

## X05 — Xây một nhánh hỏi tiếp thích ứng

File cần mở hoặc tạo:

- `source/service/interview_service.py`
- `source/Control/interview_controller.py`
- `source/view/templates/workspace.html`
- `test/service/test_adaptive.py`

Các bước:

1. Cài một nhánh policy đã chốt với biến thể được review.
2. Kết nối Controller/View, hiển thị lý do chọn câu tiếp.
3. Kiểm tra đủ độ phủ, chống lặp và điều kiện dừng.

Kiểm tra hoàn thành:

- Câu mới kiểm tra đúng mục tiêu và giải thích được lựa chọn.
- Không tạo vòng hỏi vô hạn khi bằng chứng vẫn mơ hồ.

## X06 — Định nghĩa dữ liệu JD và nguồn được dùng

File cần mở hoặc tạo:

- `source/Model/job_posting.py`
- `docs/job_import_policy.md`

Các bước:

1. Chốt trường JD gốc và metadata nguồn/thời gian.
2. Xác định nguồn và phương thức import được dùng; tách gốc và dẫn xuất.
3. Định nghĩa version chuẩn hóa và ràng buộc thiếu dữ liệu.

Kiểm tra hoàn thành:

- Không mất nội dung JD nguyên bản khi chuẩn hóa.
- Chưa có dữ liệu không được hiểu là giá trị 0 hoặc false.

## X07 — Import JD thủ công và trích kỹ năng

File cần mở hoặc tạo:

- `source/service/job_import_service.py`
- `source/Control/job_controller.py`
- `source/view/templates/job_import.html`

Các bước:

1. Tạo form nhập JD thủ công theo schema X06.
2. Service lưu bản gốc rồi trích skill có đoạn căn cứ và ID chuẩn hóa.
3. Báo lỗi từng trường/bản ghi và cho sửa dữ liệu nhập.

Kiểm tra hoàn thành:

- Kỹ năng dẫn xuất truy lại được đoạn JD gốc.
- Không dùng chỉ dẫn nằm trong JD như lệnh hệ thống.

## X08 — Định nghĩa tiên quyết và ngân sách học

File cần mở hoặc tạo:

- `source/Model/learning_plan.py`
- `data/seed/exercises.json`
- `docs/planning_rules.md`

Các bước:

1. Xây đồ thị tiên quyết từ catalog đã review.
2. Định nghĩa thời lượng ước tính, ngân sách thời gian và deadline.
3. Chốt cách xử lý chu trình, thiếu node và kế hoạch không khả thi.

Kiểm tra hoàn thành:

- Prerequisite IDs hợp lệ; phát hiện được chu trình.
- Không hứa hoàn thành trong thời gian thiếu so với yêu cầu.

## X09 — Sắp xếp lộ trình bằng thuật toán

File cần mở hoặc tạo:

- `source/service/learning_plan_service.py`
- `test/service/test_learning_plan.py`

Các bước:

1. Cài topological ordering cho bài luyện được chọn.
2. Phân bổ theo ngân sách, giữ tiên quyết trước hoạt động phụ thuộc.
3. Trả lỗi/ràng buộc không đạt thay vì bỏ hoạt động âm thầm.

Kiểm tra hoàn thành:

- Test đồ thị phân nhánh, chu trình, node thiếu và deadline quá ngắn.
- Cùng dữ liệu và policy cho thứ tự có thể giải thích.

## X10 — Xây API và giao diện lộ trình học

File cần mở hoặc tạo:

- `source/Control/learning_plan_controller.py`
- `source/view/templates/learning_plan.html`
- `source/view/static/js/learning_plan.js`

Các bước:

1. Expose yêu cầu tạo/đọc lộ trình qua Controller.
2. Dựng danh sách hoặc lịch từ kết quả Service, kèm lý do gap/tiên quyết.
3. Hiển thị thiếu dữ liệu và lịch không khả thi cùng cách điều chỉnh.

Kiểm tra hoàn thành:

- UI không tự sắp tiên quyết hoặc tính điểm.
- Mọi thời lượng được ghi là ước tính và truy được lý do chọn.

## X11 — Chọn hosting và yêu cầu truy cập

File cần mở hoặc tạo:

- `docs/deployment_decision.md`
- `.env.example`
- `source/config.py`

Các bước:

1. Chốt yêu cầu hosted của môn học và lựa chọn dịch vụ có persistent storage.
2. Ghi chi phí, quyền truy cập, dữ liệu được dùng và biến môi trường.
3. Lập quy trình backup, migrate và rollback trước triển khai.

Kiểm tra hoàn thành:

- Hosting restart không bị hiểu là sẽ giữ DB nếu dịch vụ không hỗ trợ.
- Không nâng public hoặc dùng tiền khi chưa có quyết định tương ứng.

## X12 — Triển khai và kiểm tra bản hosted

File cần mở hoặc tạo:

- `docs/deployment_runbook.md`
- `README.md`
- `docs/release_checklist.md`

Các bước:

1. Triển khai commit đã kiểm tra và cấu hình secret ở môi trường server.
2. Áp dụng migration đúng thứ tự, kiểm tra truy cập và persistent data sau restart.
3. Demo luồng hosted, ghi URL, version và hạn chế; giữ cách chạy local.

Kiểm tra hoàn thành:

- Không có khóa ở client hoặc source.
- Phiên/bài lưu được đọc lại sau restart và rollback có chỉ dẫn rõ.
