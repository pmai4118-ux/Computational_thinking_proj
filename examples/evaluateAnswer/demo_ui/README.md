# Portable answer evaluation PoC

## Bản này demo được đến đâu?

**Có thể demo ngay quy trình bằng bài mẫu đã chuẩn bị:** chọn câu, xem rubric,
đối chiếu bằng chứng, tính điểm, phản hồi, lưu và tải báo cáo. Chưa đủ căn cứ để
tuyên bố hệ thống đánh giá chính xác một câu trả lời mới bằng AI: cần cấu hình
provider, chạy thật và đối chiếu kết quả với người chấm độc lập.

Danh sách đã làm và việc còn thiếu nằm trong [NEXT_STEPS.md](NEXT_STEPS.md).
Các bước bên dưới dùng cho bản demo này; không yêu cầu dựng toàn bộ app trong backlog.

## Chạy trên máy bất kỳ

Máy cần Git, Python 3.11 và [uv](https://docs.astral.sh/uv/getting-started/installation/).
Nếu chưa có repo, clone đúng nhánh rồi vào thư mục:

```powershell
git clone --branch evaluateAnswer https://github.com/pmai4118-ux/Computational_thinking_proj.git
cd Computational_thinking_proj
```

Nếu đã clone, mở terminal tại thư mục chứa `pyproject.toml`, `uv.lock` và `source`.
Khi cần lấy bản mới, kiểm tra `git status` trước; giữ lại thay đổi riêng rồi mới
chuyển nhánh và cập nhật bằng `git switch evaluateAnswer`, `git pull --ff-only`.
Không clone chồng vào thư mục đang có code.

Cài môi trường và chạy:

```powershell
uv python install 3.11
uv sync --locked
uv run --locked python -m source.main --web --port 8001
```

Nếu máy Windows đã có `.venv` được tạo từ file khóa của repo (như máy đang làm
việc hiện tại), có thể chạy trực tiếp, không cần kích hoạt môi trường:

```powershell
.\.venv\Scripts\python.exe -m source.main --web --port 8001
```

Mở http://127.0.0.1:8001. Chọn câu hỏi → chọn loại bài → **Tải bài mẫu** →
**Xem kết quả ghi sẵn**. Không cần key, tài khoản AI, đường dẫn máy cũ hay checkout
nhánh dữ liệu. Python vẫn kiểm tra bằng chứng và tính điểm từ nhận định đã lưu.
Đây là minh họa quy trình; không chứng minh AI đã hiểu một bài mới.

Dừng bằng Ctrl+C. Nếu cổng đang dùng, đổi `--port 8001` thành `--port 8002`.
Ứng dụng mặc định chỉ lắng nghe trên máy đang chạy, không tự triển khai lên Internet.

## Chấm bài mới bằng Gemini

Gemini là lựa chọn mặc định. Key được đặt ở máy chạy server, không nằm trong code,
không gửi từ trình duyệt. Những người clone repo đặt key của họ; nếu triển khai
chung một server sau này, chỉ server đó cần key.

1. Tạo key tại [Google AI Studio](https://aistudio.google.com/api-keys).
2. Tạo thư mục `secrets` ở gốc repo, sao chép `gemini.example.json` trong thư mục
   hướng dẫn này thành `secrets/demo-gemini.json`.
3. Thay `REPLACE_WITH_YOUR_KEY` trong file đó bằng key thật rồi khởi động lại server.
4. Nhập bài mới và chọn **Đánh giá bằng AI**. File cấu hình được Git bỏ qua.

Lệnh tạo file mẫu trong PowerShell, chỉ sao chép khi chưa có file cấu hình:

```powershell
New-Item -ItemType Directory -Path secrets -Force
if (-not (Test-Path -LiteralPath secrets/demo-gemini.json)) {
    Copy-Item examples/evaluateAnswer/demo_ui/gemini.example.json secrets/demo-gemini.json
}
notepad secrets/demo-gemini.json
```

Lưu key trong trình soạn thảo, không giữ nguyên chuỗi mẫu. Nếu trước đó đã chọn
Antigravity, đặt `$env:DEMO_EVALUATION_PROVIDER = "gemini"` trước khi khởi động.

Có thể dùng biến môi trường `GEMINI_API_KEY`, `GEMINI_MODEL`, `EVALUATION_TIMEOUT`
thay file. Biến môi trường ưu tiên hơn file. Ứng dụng không tự đọc file `.env`.
Không ghi key vào câu trả lời, JSON gửi từ web, tài liệu hay commit.

Mặc định `gemini-2.5-flash-lite`, timeout 60 giây. Theo
[bảng giá Google](https://aistudio.google.com/docs/pricing), model này có Free Tier
cho tài khoản đủ điều kiện; quota và quyền truy cập phụ thuộc tài khoản.
[Gemini vẫn yêu cầu API key](https://aistudio.google.com/docs/api-key).
Không có API miễn phí vô hạn, không cần tài khoản được tích hợp ở đây. Code không
tự nâng gói hoặc đổi sang model trả phí. Đặt model khác qua cấu hình khi cần.

Antigravity là tùy chọn: cài `agy`, đăng nhập trên máy đang chạy, đặt
`DEMO_EVALUATION_PROVIDER=antigravity`. `ANTIGRAVITY_EXECUTABLE` chỉ là cấu hình
cục bộ; không cần đưa đường dẫn riêng vào repo. Thiếu hoặc sai cấu hình AI vẫn
cho xem bản ghi. Nút AI chỉ xác nhận đã có cấu hình; một lượt gọi thành công mới
xác nhận kết nối và quota thực tế.

## Bộ 10 câu

| ID nguồn | Nội dung | Nhóm được chấm |
| --- | --- | --- |
| Q009 | Tìm kiếm nhị phân | Knowledge, Analysis, Testing, Implementation |
| Q028 | Tra cứu nhân viên theo ID | Knowledge, Analysis, Testing, Implementation |
| Q017 | Sửa infix sang postfix | Knowledge, Analysis, Testing, Implementation |
| Q018 | Sửa Counting Sort | Knowledge, Analysis, Testing, Implementation |
| Q002 | JDK, JRE và JVM | Knowledge |
| Q005 | `==` và `equals` | Knowledge, Analysis |
| Q007 | Tính bất biến của String | Knowledge, Analysis |
| Q010 | Bubble Sort | Knowledge, Analysis, Testing |
| Q022 | List, Set hay Map | Knowledge, Analysis |
| Q085 | Unit test Service có Repository | Knowledge, Analysis, Testing |

Nhóm không có trong yêu cầu được ghi **Không áp dụng**, không bị tính điểm 0.
Mỗi câu có năm mẫu: đúng, một phần, sai/thiếu, cách trình bày tương đương và mơ hồ.
Tổng cộng 50 bản nhận định. Dữ liệu và giấy phép đang chờ người duyệt độc lập;
chúng có nhãn demo và chưa được dùng như bộ chuẩn đã kiểm chứng.

## Chấm và hiển thị kết quả

Mở **Nhóm đánh giá và thang điểm 0–1–2**, rồi mở từng nhóm để xem yêu cầu và mô tả
các mức. Mỗi nhóm áp dụng có một rubric với hai dấu hiệu quan sát cụ thể:

| Điểm | Quy tắc |
| --- | --- |
| 0 | Không dấu hiệu nào được xác nhận đạt và không còn mơ hồ có thể đổi điểm. |
| 1 | Một dấu hiệu đạt, dấu hiệu kia được xác định chưa đạt. |
| 2 | Cả hai dấu hiệu đạt. |
| Chưa đủ căn cứ | Thông tin chưa rõ có thể làm thay đổi mức điểm; `score=null`. |

Mô tả cụ thể tùy câu hỏi trong `data/questionBank/catalog.json`; không phải AI tự
đặt thang điểm. Bản 0/1/2 này là rubric PoC được biên soạn lại có ghi chú, chưa
được người sở hữu dữ liệu Task 3 phê duyệt như một phép chuyển đổi tương đương.

Luồng: nhận nguyên văn bài + phiên bản câu hỏi/rubric → kiểm tra đầu vào →
lưu snapshot → chọn Gemini hoặc bản ghi → nhận trạng thái từng dấu hiệu và trích
dẫn → kiểm tra trích dẫn/ID/vị trí → Python chọn mức → dựng feedback → lưu báo cáo.
Gemini diễn giải ngữ nghĩa; Python không tự hiểu câu và không thực thi code của
người trả lời. Feedback dùng mẫu của `FeedbackBuilder` kèm nhận định từ interpreter.

Kết quả hiện trên web, không chỉ trên console. Mỗi nhóm có điểm hoặc trạng thái,
lý do, bằng chứng và feedback. **Tải JSON** xuất đúng `EvaluationReport` đã lưu,
bao gồm nguyên văn đầu vào và metadata provider/model/prompt. Không cộng điểm
của các nhóm thành tổng chung. Giao diện thao tác tiếng Việt; chuẩn chấm, bài
mẫu và báo cáo kỹ thuật được giữ bằng tiếng Anh.

## Lưu bài, retry và lỗi

- Bản nháp riêng từng câu được giữ trong phiên trình duyệt; tải lại trang vẫn giữ
  bài. Đóng phiên hoặc xóa dữ liệu trình duyệt có thể xóa bản nháp chưa nộp.
- Server lưu bài đã nộp và báo cáo vào `artifacts/demo/submissions.sqlite3`.
  Đổi thư mục bằng `EVALUATION_DATA_DIR`; Git bỏ qua `artifacts/`.
- Cùng answer ID/revision, input snapshot, provider/model/prompt thì dùng lại báo
  cáo đã hoàn thành. Sửa bài tạo revision mới. Bản ghi không che kết quả AI.
- Lỗi AI giữ nguyên bài, không lưu điểm giả. Có thể retry sau khi khắc phục.
- Đổi câu hỏi hoặc sửa bài làm ẩn kết quả không còn khớp. Sửa bài mẫu sẽ không
  được xem recording cũ như thể đó là nhận định cho bài vừa sửa.
- Chạy một worker cho PoC; khóa trong service chống gọi lặp đồng thời trong worker.
  Chưa có điều phối nhiều server, tài khoản người dùng hoặc phân quyền dữ liệu.

## Kiến trúc và tương thích

| Lớp | File chính | Trách nhiệm |
| --- | --- | --- |
| Composition root | `source/main.py` | `Application.createDemoApp()` nối các dependency. |
| View | `source/view/demoView.py`, `source/view/web/` | HTTP, giao diện, trạng thái nháp, hiển thị; không tính điểm. |
| Controller | `source/Control/demoController.py`, `demoSchemas.py` | Hành động người dùng và schema request. |
| Service | `questionBankService.py`, `demoService.py`, `demoConfiguration.py` | Duyệt/phiên bản dữ liệu, orchestration, retry và cấu hình provider. |
| Evaluator | `evaluationService.py`, `rubricRules.py`, `evidenceReview.py`, `feedbackBuilder.py` | Diễn giải, kiểm tra bằng chứng, xếp mức, phản hồi. |
| Model | `questionBankData.py`, `Model/repositories/` | Schema và repository JSON/SQLite. |

`InterpreterFactory` là routing giữa Gemini, Antigravity và recorded.
`DemoService` điều phối phiên bản/lưu bài/cache; `EvaluationService` điều phối chấm.
Các file Python cũ dưới `examples/.../demo_ui` chỉ là alias chuyển tiếp.
Lệnh ASGI cũ `examples.evaluateAnswer.demo_ui.main:app` còn hoạt động; code Python
khởi tạo controller/service trực tiếp phải dùng dependency injection trong `source`.
API POST mới bắt buộc `questionVersion` và `rubricVersions`; xem
[hợp đồng dữ liệu](../../../docs/data_contract.md). CLI cũ và schema báo cáo giữ nguyên.

## Kiểm tra trước buổi demo

Kịch bản trình bày khoảng 5 phút:

1. Chọn Q009, mở bốn nhóm và chỉ ra mô tả mức 0/1/2.
2. Tải mẫu đúng, xem bản ghi: bốn nhóm đều 2/2; mở một trích dẫn và feedback.
3. Tải mẫu một phần rồi mẫu mơ hồ: lần lượt thấy 1/2 và chưa đủ căn cứ.
4. Chọn Q002: chỉ Kiến thức có điểm, ba nhóm còn lại không áp dụng.
5. Tải JSON để thấy nguyên văn bài, rubric, kết quả, bằng chứng và metadata.
6. Nếu đã có key và đã kiểm chứng kết nối, nhập một bài mới rồi chấm bằng AI;
   nếu chưa có thì nêu rõ phần vừa trình bày sử dụng nhận định ghi sẵn.

```powershell
uv run --locked python -m pytest
node --test test/demoUiState.test.cjs
```

Node chỉ cần cho kiểm thử trạng thái giao diện, không cần để chạy ứng dụng.
Với môi trường Windows đã cài sẵn, lệnh Python tương đương là
`.\.venv\Scripts\python.exe -m pytest`.
Kiểm tra thủ công: đổi giữa Q009 và Q002, nhập nháp riêng, tải lại trang, mở chuẩn
chấm bằng bàn phím, chạy mẫu đúng và mơ hồ, mở bằng chứng, tải JSON. Thử sửa bài
mẫu để thấy nút bản ghi ngừng hoạt động. Thử màn hình rộng và hẹp.

Để kiểm chứng AI thật: cấu hình key, gửi một bài mới chưa có recording, tải JSON,
ghi model/prompt/commit dữ liệu và so kết quả với đánh giá độc lập theo từng dấu
hiệu. Lặp với bài thiếu, sai, mơ hồ và tương đương. Không dùng 50 bản ghi làm số
liệu về độ chính xác của Gemini. Chưa có key thì chỉ xác nhận demo quy trình.

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không nhận diện `uv` | Cài uv, mở terminal mới; hoặc dùng Python trong `.venv` đã cài đúng dependency. |
| Không tìm thấy `source` hoặc `pyproject.toml` | Chuyển terminal về thư mục gốc repo. |
| Cổng đang được dùng | Đổi `--port` sang cổng khác và mở đúng URL đó. |
| Nút AI bị vô hiệu hóa | Nhập bài, kiểm tra key/provider trên server, khởi động lại. Vẫn có thể xem bản ghi. |
| AI báo quota, timeout hoặc cấu hình sai | Kiểm tra tài khoản/model/key; giữ bài và retry sau khi xử lý lỗi. Không đổi sang bản ghi rồi gọi đó là kết quả AI. |
| Không xem được recording sau khi sửa bài mẫu | Tải lại nguyên văn bài mẫu hoặc dùng AI để chấm bài mới. |
| Phiên bản câu hỏi/rubric thay đổi | Tải lại trang để lấy phiên bản mới; kiểm tra bản nháp trước khi gửi lại. |

Xem [trạng thái bàn giao](NEXT_STEPS.md) và
[hướng dẫn duyệt dữ liệu](../../../data/questionBank/README.md).
