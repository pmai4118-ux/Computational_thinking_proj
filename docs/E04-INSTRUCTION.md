# E04-INSTRUCTION — Chạy đánh giá AI bằng Antigravity

Tài liệu này hướng dẫn từ lúc lấy nhánh `codex/e04-gemini-structured-output` về máy Windows đến khi xem được điểm và báo cáo JSON. Đường chạy demo dùng **Antigravity CLI (`agy`)**: mỗi người cài CLI và đăng nhập tài khoản Google của mình; **không cần Gemini API key**. Model mặc định của đường chạy này là `gemini-3.8-flash-medium`.

E04 hiện đánh giá **một câu trả lời cho một câu hỏi** bằng dòng lệnh. Chương trình đọc câu hỏi, rubric và bài gốc từ JSON; AI diễn giải từng tiêu chí; Python kiểm tra bằng chứng, chọn mức điểm theo rubric, in phản hồi và lưu báo cáo. Luồng này chưa kết nối vào giao diện web.

## 1. Mở PowerShell và lấy nhánh E04

Nhấn **phím Windows** hoặc **nút Windows Start** trên thanh tác vụ, gõ `PowerShell`, rồi mở **Windows PowerShell**.

**Nếu chưa clone repo**, chuyển đến nơi muốn lưu dự án và chạy:

```powershell
Set-Location "$HOME\Documents"
git clone --branch codex/e04-gemini-structured-output https://github.com/pmai4118-ux/Computational_thinking_proj.git
Set-Location .\Computational_thinking_proj
```

**Nếu đã clone repo**, thay đường dẫn ví dụ bên dưới bằng đường dẫn repo trên máy của bạn. Nếu nhánh E04 **chưa có ở máy**, chạy:

```powershell
Set-Location "D:\TDTT\src\Computational_thinking_proj"
git fetch origin
git switch --track origin/codex/e04-gemini-structured-output
git pull --ff-only origin codex/e04-gemini-structured-output
```

Nếu nhánh E04 **đã có ở máy**, dùng `git switch codex/e04-gemini-structured-output` thay cho dòng `git switch --track ...`, rồi chạy `git pull --ff-only origin codex/e04-gemini-structured-output`.

Kiểm tra thư mục và nhánh:

```powershell
git status --short --branch
Test-Path .\pyproject.toml
```

Kết quả phải hiện tên nhánh E04 và `True`. Nếu Git báo có thay đổi cục bộ cản trở việc chuyển nhánh/pull, hãy giữ lại và xử lý chúng trước; không dùng lệnh reset để xóa công việc đang có.

## 2. Cài Python và thư viện dự án

Dự án yêu cầu **Python 3.11** và cài phiên bản thư viện từ `uv.lock`. Kiểm tra `uv`:

```powershell
uv --version
```

Nếu chưa có `uv`, dùng WinGet:

```powershell
winget install --id astral-sh.uv -e
```

Nếu máy không có WinGet, dùng [lệnh cài đặt chính thức của uv trên Windows](https://docs.astral.sh/uv/getting-started/installation/):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Sau khi cài, **đóng PowerShell và mở lại**, quay về thư mục gốc repo và xác nhận `uv --version` chạy được. Sau đó:

```powershell
uv python install 3.11
uv sync --locked
uv run --locked python --version
uv pip check
```

`uv sync --locked` tạo `.venv` và cài dependencies đúng theo repo. Phiên bản Python cần là `3.11.x`. Không cần `pip` hoặc `google-genai` để chạy qua `agy`. Luôn chạy các lệnh `uv` ở thư mục có `pyproject.toml`.

## 3. Cài `agy` và đăng nhập

Cần cài **Antigravity CLI**, kể cả khi máy đã có ứng dụng Antigravity. [Lệnh PowerShell chính thức của Google](https://antigravity.google/docs/getting-started):

```powershell
irm https://antigravity.google/cli/install.ps1 | iex
```

Đóng và mở lại PowerShell để cập nhật `PATH`, quay về thư mục repo, rồi kiểm tra:

```powershell
agy --version
```

Gõ `agy` để mở CLI tương tác, làm theo hướng dẫn đăng nhập bằng **tài khoản Google của chính bạn** trong trình duyệt, hoàn tất thiết lập lần đầu và thoát CLI. Xem model mà tài khoản được dùng:

```powershell
agy models
```

Cần thấy `gemini-3.8-flash-medium`. Code đã chọn model này làm mặc định; người dùng **không phải tạo key, không sửa code và không ghi đường dẫn máy mình vào Git**. Việc được dùng model và quota phụ thuộc tài khoản đã đăng nhập. Phiên đăng nhập có thể cần làm lại khi hết hạn.

Nếu `agy` chưa có trong `PATH`, kiểm tra vị trí cài mặc định trên Windows:

```powershell
Test-Path "$env:LOCALAPPDATA\agy\bin\agy.exe"
```

Nếu trả `True`, dùng tham số `--antigravity-executable` ở bước 4. Tham số này chỉ dành cho máy đang chạy, không phải cấu hình cố định trong repo.

## 4. Gọi AI để đánh giá và xem báo cáo

Ở **thư mục gốc repo**, chạy bài mẫu tổng hợp có bốn tiêu chí:

```powershell
uv run --locked python -m source.main --provider antigravity --input test/fixtures/e04/inventory_answer.json --output .local/e04-report.json
```

Nếu `agy` chưa có trong `PATH`, dùng đường dẫn thực thi cục bộ:

```powershell
uv run --locked python -m source.main --provider antigravity --antigravity-executable "$env:LOCALAPPDATA\agy\bin\agy.exe" --input test/fixtures/e04/inventory_answer.json --output .local/e04-report.json
```

Terminal sẽ hiện `Evaluation complete: .../8 | model=gemini-3.8-flash-medium`, phản hồi cho **Knowledge, Analysis, Implementation, Testing** và vị trí lưu report. Mỗi tiêu chí có các mức **0, 1, 2**. Kết quả do AI diễn giải có thể thay đổi giữa các lần chạy; không mặc định bài nào cũng đạt điểm tối đa.

Xem báo cáo JSON đã lưu:

```powershell
$report = Get-Content .local/e04-report.json -Raw | ConvertFrom-Json
$report.provider
$report.modelId
$report.result.totalScore
$report.result.maximumScore
$report.result.criterionChecks | Select-Object criterionId,status,score
$report.feedbackItems | Select-Object label,message
```

Report chứa câu hỏi, rubric, bài gốc, trạng thái từng tiêu chí, đoạn trích hoặc ghi nhận nội dung thiếu, điểm, phản hồi, model ID, phiên bản prompt và thời gian gọi. Nếu **chưa đủ căn cứ**, điểm của tiêu chí là `null`, khác với 0. Thư mục `.local/` không được Git theo dõi. Nếu lời gọi AI hoặc bằng chứng lỗi, chương trình báo lỗi và không ghi report mới.

**Thử câu trả lời của bạn cho cùng câu hỏi:** sao chép file mẫu vào `.local/`, mở bản sao và chỉ sửa `answer.id`, `answer.text`; giữ nguyên câu hỏi và rubric, bảo đảm JSON hợp lệ:

```powershell
Copy-Item test/fixtures/e04/inventory_answer.json .local/my-answer.json
notepad .local/my-answer.json
uv run --locked python -m source.main --provider antigravity --input .local/my-answer.json --output .local/my-report.json
```

Nội dung `answer.text` được gửi đến dịch vụ Antigravity theo phiên đăng nhập của bạn, nên hãy dùng bài luyện tập không chứa dữ liệu riêng tư. Nếu muốn đổi câu hỏi hoặc rubric thì phải khai báo lại tiêu chí, bằng chứng mong đợi và các mức điểm cho phù hợp; rubric mẫu không dùng chung cho mọi câu hỏi.

## 5. Kiểm tra code và hiểu bài test bị bỏ qua

Bộ test tự động dùng mock/fixture, **không gọi `agy` thật**:

```powershell
uv run --locked python -m pytest -q
```

Ở phiên bản bàn giao này, khi không bật bài live dùng Gemini API key, kết quả đã kiểm tra là `53 passed, 1 skipped`. `1 skipped` là **bài thử Gemini API trực tiếp**; nó **không phải** việc gọi `agy` bị bỏ qua. Muốn kiểm chứng AI thật và report JSON, chạy lệnh ở bước 4. Khi bàn giao E04, bài mẫu đầy đủ cho **8/8**, bài cố ý thiếu ý cho **3/8**; mỗi report có bốn kết quả tiêu chí, bốn phản hồi và vị trí trích dẫn đúng. Hai lần chạy này chứng minh luồng demo hoạt động, chưa chứng minh độ chính xác trên mọi bài.

Repo cũng giữ provider gọi Gemini API trực tiếp cho một luồng khác. Bài live riêng của provider đó cần `GEMINI_API_KEY` và model được đặt qua `E04_GEMINI_LIVE_MODEL`; **không cần** các biến này trong hướng dẫn `agy`. CLI đánh giá E04 hiện nhận `antigravity` hoặc `fixture`, chưa có tùy chọn `--provider gemini`.

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `uv` hoặc `agy` không được nhận diện | Đóng/mở PowerShell sau khi cài; kiểm tra `uv --version`, `agy --version`. Với `agy`, dùng tham số đường dẫn thực thi nếu cần. |
| Thiếu module hoặc `.venv` | Chạy `uv sync --locked` tại thư mục gốc repo rồi dùng `uv run --locked python ...`, không gọi Python hệ thống. |
| Chưa đăng nhập hoặc không thấy model | Chạy `agy` đăng nhập lại; kiểm tra `agy models` và quyền dùng model. |
| Hết quota hoặc timeout | Kiểm tra tài khoản, kết nối và trạng thái CLI. Có thể đặt `$env:ANTIGRAVITY_TIMEOUT_SECONDS = "180"` cho cửa sổ hiện tại rồi thử lại; code chấp nhận 1–300 giây. |
| Test có `1 skipped` | Đây là test live tùy chọn của Gemini API. Dùng bước 4 để kiểm tra Antigravity thật. |
| Không có report mới | Xem lỗi trong terminal; AI trả kết quả không hợp lệ sẽ không được biến thành điểm hay report. |

Nguồn cài đặt: [Google Antigravity](https://antigravity.google/docs/getting-started), [uv](https://docs.astral.sh/uv/getting-started/installation/). Xem thêm [ghi chú tích hợp E04](E04-gemini-structured-output.md).
