# E04 — Hướng dẫn cài đặt và chạy kiểm tra Gemini

**Cập nhật:** 22/11/2026.

Tài liệu này dành cho người vừa lấy nhánh `codex/e04-gemini-structured-output` về Windows. E04 thêm adapter gọi Gemini API và yêu cầu Gemini trả kết quả JSON có cấu trúc theo hợp đồng E01.

**Phạm vi hiện tại:** E04 chưa phải một ứng dụng có giao diện để chạy độc lập và chưa tự tạo `EvaluationReport`. Hãy kiểm chứng adapter bằng các lệnh pytest ở dưới. Mặc định toàn dự án là `fixture`, tức dữ liệu minh họa chạy ngoại tuyến; muốn gọi Gemini thật thì cần API key cá nhân.

**Model hướng dẫn dùng:** code hiện tại còn giá trị mặc định `gemini-2.5-flash` trong adapter và bài test live. Tuy nhiên, cấu hình cho phép truyền model qua biến `GEMINI_MODEL`, và bạn đã xác nhận gọi live thành công với `gemini-4-hydrogen`. Vì vậy, các lệnh trong tài liệu này chọn `gemini-4-hydrogen`; đây là lựa chọn hướng dẫn, không phải giá trị mặc định đã hard-code trong nhánh. Google liệt kê model này là Stable và hỗ trợ structured outputs. Xem mục [Model và giới hạn](#model-và-giới-hạn).

## 1. Lấy nhánh E04

Mở PowerShell tại thư mục mà bạn muốn lưu dự án. Nếu chưa clone repo, chạy:

```powershell
git clone --branch codex/e04-gemini-structured-output https://github.com/pmai4118-ux/Computational_thinking_proj.git
Set-Location .\Computational_thinking_proj
```

Nếu đã clone repo, vào thư mục gốc rồi cập nhật nhánh:

```powershell
Set-Location "D:\TDTT\src\Computational_thinking_proj"
git fetch origin
git switch --track origin/codex/e04-gemini-structured-output
git pull --ff-only
```

Nếu nhánh đã có ở máy, dùng `git switch codex/e04-gemini-structured-output` thay cho lệnh `git switch --track ...`, rồi chạy `git pull --ff-only`.

Kiểm tra bạn đang ở đúng nhánh và đúng thư mục gốc:

```powershell
git status --short --branch
Test-Path .\pyproject.toml
```

Lệnh đầu cần hiện `codex/e04-gemini-structured-output`; lệnh sau cần trả `True`. Nếu repo của bạn nằm ở đường dẫn khác, thay đường dẫn trong `Set-Location`.

## 2. Cài Python, uv và dependencies

Dự án yêu cầu CPython **3.11**. `uv` sẽ tạo môi trường ảo `.venv` và cài đúng các phiên bản được khóa trong `uv.lock`.

### 2.1. Cài uv

Trong PowerShell, thử cài bằng WinGet:

```powershell
winget install --id astral-sh.uv -e
```

Nếu WinGet không có trên máy, dùng lệnh cài đặt PowerShell chính thức của uv:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Sau khi cài, **đóng PowerShell và mở cửa sổ PowerShell mới** để cập nhật `PATH`, rồi kiểm tra:

```powershell
uv --version
```

### 2.2. Cài Python và thư viện dự án

Đảm bảo PowerShell đang ở thư mục gốc repo, sau đó chạy:

```powershell
uv python install 3.11
uv sync --locked
```

`uv sync --locked` đọc `pyproject.toml` và `uv.lock`, tạo `.venv`, cài FastAPI, Pydantic, Jinja2, Uvicorn cùng các công cụ phát triển như pytest. E04 gọi Gemini qua HTTP bằng thư viện chuẩn của Python (`urllib`), nên **không cần cài `google-genai`**.

Kiểm tra phiên bản Python và dependencies:

```powershell
uv run --locked python --version
uv pip check
```

Python cần hiện phiên bản `3.11.x`; `uv pip check` cần báo không có dependency bị thiếu hoặc xung đột.

## 3. Tạo Gemini API key

Mỗi người dùng tạo và giữ key riêng. Không gửi key qua chat, không dán key vào file `.py`, không commit key lên Git và không đưa key vào ảnh chụp màn hình.

1. Mở trang [Google AI Studio — API keys](https://aistudio.google.com/apikey) và đăng nhập tài khoản Google.
2. Chọn một Google Cloud project có quyền dùng Gemini API. Nếu AI Studio yêu cầu, hãy tạo project hoặc import project hiện có.
3. Nhấn **Create API key** và chọn project phù hợp.
4. Sao chép key vừa tạo, cất ở nơi riêng tư. Không dán key vào tài liệu hoặc repo.
5. Nếu trang cho phép, giới hạn key chỉ dùng với **Gemini API**.

Khả năng sử dụng miễn phí, xác minh project và yêu cầu billing phụ thuộc tài khoản/project. Tạo được key không đảm bảo model đã chọn có quota hoặc đang được cấp quyền cho tài khoản đó.

## 4. Lưu key vào Windows User environment variables

Cách này lưu key trong biến môi trường của tài khoản Windows hiện tại, không ghi key vào repo.

1. Nhấn **nút Windows Start** trên thanh tác vụ hoặc nhấn phím Windows.
2. Gõ `Edit environment variables for your account`.
3. Mở kết quả **Edit environment variables for your account**.
4. Trong phần **User variables for ...**, nhấn **New...**.
5. Điền:
   - **Variable name:** `GEMINI_API_KEY`
   - **Variable value:** dán API key vừa tạo; không thêm dấu ngoặc kép và không thêm khoảng trắng ở đầu/cuối.
6. Nhấn **OK** trong các cửa sổ để lưu và đóng.
7. Đóng các cửa sổ PowerShell đang mở, rồi mở PowerShell mới. Ứng dụng đã mở trước khi tạo biến cũng cần được khởi động lại để nhận biến mới.

Kiểm tra key đã được nạp mà không in key ra màn hình:

```powershell
if ([string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) {
    "GEMINI_API_KEY chưa có trong PowerShell này."
} else {
    "GEMINI_API_KEY đã sẵn sàng."
}
```

Nếu vừa sửa biến User mà PowerShell mới vẫn chưa thấy, nạp lại trong cửa sổ hiện tại:

```powershell
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
```

Không chạy lệnh `Write-Output $env:GEMINI_API_KEY`, vì lệnh đó sẽ làm lộ key trong terminal.

## 5. Chọn cấu hình Gemini cho lần chạy hiện tại

Tại PowerShell mới, vào thư mục gốc repo:

```powershell
Set-Location "D:\TDTT\src\Computational_thinking_proj"
```

Chọn provider Gemini và khai báo model/timeout cho **cửa sổ PowerShell này**:

```powershell
$env:EVALUATION_PROVIDER = "gemini"
$env:GEMINI_MODEL = "gemini-4-hydrogen"
$env:GEMINI_TIMEOUT_SECONDS = "30"
```

Ứng dụng yêu cầu `GEMINI_MODEL` khi `EVALUATION_PROVIDER=gemini`; không dựa vào mặc định trong class provider. `GEMINI_TIMEOUT_SECONDS` mặc định là 30 giây; adapter chấp nhận từ 1 đến 120 giây.

Các lệnh trên không thay đổi biến User đã lưu trong Windows; chúng chỉ cấu hình tiến trình PowerShell hiện tại. Muốn chạy bài live test bên dưới thì cần thêm hai biến bật bài test và chọn model kiểm tra:

```powershell
$env:RUN_GEMINI_LIVE_TEST = "1"
$env:E04_GEMINI_LIVE_MODEL = $env:GEMINI_MODEL
```

## 6. Chạy kiểm tra

### 6.1. Kiểm tra offline, không gọi API

Chạy các test của adapter. Các test này dùng dữ liệu giả lập và mock HTTP, không cần key, không tiêu thụ quota:

```powershell
Remove-Item Env:RUN_GEMINI_LIVE_TEST -ErrorAction SilentlyContinue
uv run --locked python -m pytest -q test/test_gemini_provider.py
```

Chạy toàn bộ test suite của repo:

```powershell
uv run --locked python -m pytest
```

### 6.2. Gọi Gemini thật bằng dữ liệu tổng hợp

Trước khi chạy, xác nhận key đã có mà không hiển thị giá trị:

```powershell
if ([string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) { throw "GEMINI_API_KEY chưa được nạp." }
```

Sau đó chạy đúng một bài live test:

```powershell
$env:EVALUATION_PROVIDER = "gemini"
$env:GEMINI_MODEL = "gemini-4-hydrogen"
$env:RUN_GEMINI_LIVE_TEST = "1"
$env:E04_GEMINI_LIVE_MODEL = $env:GEMINI_MODEL
uv run --locked python -m pytest -q test/test_gemini_provider.py -k live
```

Bài test gửi một câu hỏi, rubric và câu trả lời **tổng hợp** đến Gemini. Thành công thường hiện `1 passed`. Khi kết thúc, tắt chế độ live để lần pytest sau không gọi API ngoài ý muốn:

```powershell
Remove-Item Env:RUN_GEMINI_LIVE_TEST -ErrorAction SilentlyContinue
```

`1 passed` xác nhận lần gọi live trả về observation có cấu trúc, model ID khớp cấu hình và bằng chứng trích dẫn có vị trí hợp lệ. Nó không đo chất lượng chấm trên toàn bộ bộ câu hỏi, không tạo report đánh giá hoàn chỉnh, và không thay thế việc so sánh với kết quả tham chiếu.

## 7. Model và các giới hạn cần biết

### Model của repo và model của E04

| Trường hợp | Cấu hình hiện tại |
| --- | --- |
| Chạy mặc định của dự án | `EVALUATION_PROVIDER=fixture`: dữ liệu minh họa, không gọi AI. |
| Provider AI thật nhóm chọn làm chính trong P07 | Antigravity CLI, model `gemini-3.8-flash-medium`; cần cài/đăng nhập `agy`, không dùng API key Gemini trong luồng này. |
| Adapter E04 gọi trực tiếp Gemini API | `GEMINI_MODEL` bắt buộc trong cấu hình. Hướng dẫn và lệnh live test bên dưới chọn `gemini-4-hydrogen`; test trong source tự mặc định về `gemini-2.5-flash` nếu không đặt biến override. Cần `GEMINI_API_KEY`. |

Vì vậy, cần phân biệt: **model dùng theo hướng dẫn E04 là `gemini-4-hydrogen` (bạn đã xác nhận live test chạy được); giá trị mặc định cũ trong source test là `gemini-2.5-flash`; toàn ứng dụng mặc định là `fixture`, còn phương án AI thật chính theo P07 là Antigravity với `gemini-3.8-flash-medium`.** Xem [quyết định AI P07](ai_decision.md) để biết lý do nhóm chọn hai đường kết nối này.

### Giới hạn trong code

| Giới hạn | Giá trị hiện tại | Nguồn |
| --- | --- | --- |
| Payload request tới Gemini | Tối đa 250 KB | `MAX_REQUEST_BYTES` trong `source/service/providers/gemini_provider.py`. |
| Nội dung response đọc từ mạng | Tối đa 1 MB | `MAX_RESPONSE_BYTES` trong cùng provider. |
| Số token output được yêu cầu | Tối đa 4,096 token | `generationConfig.maxOutputTokens` trong provider; thấp hơn giới hạn tối đa công bố của model. |
| Timeout API | Mặc định 30 giây; provider nhận 1–120 giây | `GEMINI_TIMEOUT_SECONDS` trong `source/config.py` và provider. |
| Token limit của `gemini-4-hydrogen` | Context tổng 1,048,576 token; output đồng bộ tối đa 65,536 token | E04 hiện chỉ yêu cầu tối đa 4,096 output token; không bật chế độ long decode. |

### Quota, quyền truy cập và chi phí API

Google đo quota theo các giới hạn như RPM (request/phút), TPM (token/phút) và RPD (request/ngày). Quota áp dụng theo **Google Cloud project**, không phải riêng từng API key; quota model/tier và tài khoản thay đổi, nên không thể đảm bảo một con số cố định cho tất cả người pull code. Xem số đang áp dụng cho project của bạn tại [AI Studio → Rate limits](https://aistudio.google.com/rate-limit?timeRange=last-28-days) và mức sử dụng tại [AI Studio → Usage](https://aistudio.google.com/usage).

Tính đến 22/11/2026, Google liệt kê `gemini-4-hydrogen` là model Stable, có context tổng 1,048,576 token và hỗ trợ structured output. Quota thực tế và quyền truy cập vẫn tùy project/tài khoản; nếu model bị từ chối, kiểm tra AI Studio Rate limits và thông tin API key.

Giá trị mặc định cũ `gemini-2.5-flash` đã deprecated: Google giới hạn API model đó cho người dùng hiện hữu đến 1/12/2026 và sau ngày này chuyển tuyến request sang `gemini-3.5-flash-lite`. Lệnh hướng dẫn ở trên đặt rõ `GEMINI_MODEL=gemini-4-hydrogen`, nên không phụ thuộc mặc định 2.5 Flash.

Google ghi nhận Gemini API Free Tier có thể miễn phí cho một số model và khu vực, nhưng model/quota sẵn có phụ thuộc project và tài khoản; Paid Tier tính phí theo token. Kiểm tra [bảng giá Gemini API](https://ai.google.dev/gemini-api/docs/pricing) và thiết lập cảnh báo billing nếu project liên kết thanh toán. Không gửi dữ liệu phỏng vấn thật hoặc thông tin cá nhân vào bài live test này.

## 8. Xử lý lỗi thường gặp

| Thông báo/tình huống | Cách xử lý |
| --- | --- |
| `uv` is not recognized | Cài uv, đóng/mở PowerShell mới, chạy `uv --version`. |
| Python không phải 3.11 | Chạy `uv python install 3.11`, rồi `uv sync --locked`. |
| `No module named 'google'` | E04 hiện không cần package `google-genai`; từ repo root chạy lại `uv sync --locked` và test bằng `uv run --locked ...`. Không cài SDK chỉ để sửa lỗi môi trường cũ. |
| `GEMINI_API_KEY` thiếu | Kiểm tra User variable, mở PowerShell mới và dùng lệnh kiểm tra ở mục 4. |
| 401/403 hoặc lỗi key | Xác nhận key thuộc project hợp lệ, còn hiệu lực và bị giới hạn đúng API. Không chép key vào log để nhờ người khác kiểm tra. |
| 404 hoặc model không khả dụng | Kiểm tra `GEMINI_MODEL` và `E04_GEMINI_LIVE_MODEL` cùng là `gemini-4-hydrogen`, rồi xác nhận quyền truy cập model trong AI Studio. Không dựa vào mặc định cũ `gemini-2.5-flash`. |
| 429 | Vượt giới hạn RPM/TPM/RPD; kiểm tra AI Studio Rate limits/Usage rồi chờ quota hồi phục hoặc điều chỉnh project/tier. |
| 402 | Project không có quota/credit khả dụng hoặc cần kiểm tra billing. |
| Timeout / lỗi mạng | Kiểm tra kết nối; có thể tăng timeout tối đa 120 giây rồi thử lại một lần. |
| Test hiện `1 skipped` | Chưa bật `$env:RUN_GEMINI_LIVE_TEST = "1"`, hoặc tiến trình test không nhận được key. |

## 9. Tệp liên quan trong repo

- `source/service/providers/gemini_provider.py` — gọi Gemini `generateContent`, yêu cầu JSON schema và xác thực response.
- `source/config.py` — đọc `EVALUATION_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL` và timeout.
- `source/service/providers/interfaces.py` — hợp đồng provider dùng chung.
- `source/service/prompts.py` — prompt yêu cầu diễn giải câu trả lời theo tiêu chí.
- `test/test_gemini_provider.py` — test mock và test live có opt-in.
- `docs/ai_decision.md` — quyết định chọn provider/model và ghi chú quota của nhóm.

### Tài liệu chính thức

- [Cài uv trên Windows](https://docs.astral.sh/uv/getting-started/installation/)
- [Tạo và bảo vệ Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)
- [Model Gemini 4 Hydrogen, structured output và giới hạn token](https://ai.google.dev/gemini-api/docs/models/gemini-4-hydrogen)
- [Model Gemini 2.5 Flash và trạng thái deprecation](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash)
- [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [Quota và rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Giá Gemini API](https://ai.google.dev/gemini-api/docs/pricing)
