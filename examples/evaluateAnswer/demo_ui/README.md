# Standalone PoC demo UI

This small web UI is for presenting the Task 2 answer-evaluation flow. It lives under `examples/` and does not change the main app entry point or become part of the product UI.

## Chạy nhanh trên Windows

Mở PowerShell tại thư mục gốc repository:

```powershell
uv sync --locked
agy --version
agy
```

Ở lần đầu, `agy` sẽ mở luồng đăng nhập bằng trình duyệt nếu chưa có phiên đăng
nhập cục bộ. Đăng nhập tài khoản Google có Antigravity Pro, đợi CLI vào được
phiên làm việc rồi nhấn `Ctrl+C` để thoát. CLI headless của demo dùng lại phiên
đăng nhập đã lưu trong máy.

Khởi động web demo:

```powershell
$env:DEMO_EVALUATION_PROVIDER = "antigravity"
uv run --locked uvicorn examples.evaluateAnswer.demo_ui.main:app --host 127.0.0.1 --port 8001 --reload
```

Mở [http://127.0.0.1:8001](http://127.0.0.1:8001). Chọn câu hỏi ở đầu khung bên
trái, chọn một câu trả lời mẫu hoặc nhập câu trả lời, rồi bấm **Đánh giá bằng AI**.
Nhấn `Ctrl+C` trong cửa sổ PowerShell để dừng server.

Không cần dán Gemini API key vào trình duyệt hoặc request. Gemini API key cũ
được giữ trong cấu hình local nhưng không được đọc khi provider là Antigravity.
Trình duyệt chỉ gọi server local; server gọi `agy`, còn `agy` dùng phiên tài
khoản đã đăng nhập.

Nếu lệnh `agy` không được nhận diện, cài CLI hoặc thêm executable vào `PATH`,
rồi mở PowerShell mới. Nếu server báo Antigravity chưa sẵn sàng, kiểm tra
`agy --version`, mở `agy` để hoàn tất đăng nhập, sau đó khởi động lại server.
Nếu port 8001 đang được dùng, đổi `--port 8001` thành `--port 8002` và mở URL
tương ứng.

## Run with Antigravity subscription quota (default)

Install [Antigravity CLI](https://antigravity.google/docs/install?tab=cli) and sign in once with the Google account that has your Pro subscription. `agy models` lists the available model slugs. The adapter was reviewed with CLI 1.5.3 and `gemini-3.8-flash-medium`.

From the repository root:

```powershell
uv run --locked uvicorn examples.evaluateAnswer.demo_ui.main:app --host 127.0.0.1 --port 8001 --reload
```

Then open `http://127.0.0.1:8001`.

Restart a running demo server after changing providers. The status below the answer editor shows **Antigravity** and the pinned model. This status checks installation only; authentication and quota are checked by Antigravity when an answer is submitted.

Blank optional environment overrides use the defaults (or the local Gemini file value where present). An explicitly blank `GEMINI_API_KEY` still disables the API-key mode.

## Demo modes

- Select one of the five inventory-race examples, load its exact answer, and choose **Xem kết quả ghi sẵn**. This uses the matching recorded interpretation and does not call Gemini or need an API key.
- Switch among the Task 2 inventory-race question and the pinned Task 3 C02–C05 questions. The Task 3 sample answers can be loaded into the editor. They have no Task 2 recorded reports, so **Xem kết quả ghi sẵn** is unavailable for them; a live AI evaluation is still provisional and is not benchmark evidence.
- Newly entered or edited answers use the signed-in Antigravity account by default. The adapter sends one prompt via stdin. Its tool-compatible schema requires objects keyed by each exact rubric and criterion ID, then converts the validated response into the existing interpretation model. Evidence validation and score calculations remain in the Python service. Fixed tuple schemas (`prefixItems`) are unsupported by this CLI's Gemini tool path.

The adapter runs in an empty temporary working directory with command, file, web, and MCP actions denied. Antigravity's `finish` action is permitted only as its structured-output submission mechanism. The prompt explicitly requests `finish` and the adapter rejects other tool events. Session-only settings select account authentication and turn off purchased credit overages (`useG1Credits=false`). API-key and ADC environment variables are removed from the child process. No personal authentication tokens are copied into the app.

There is no automatic retry, model substitution, or fallback to the API-key provider. Antigravity quota errors preserve the answer and create no evaluation report. The default timeout is 120 seconds.

CLI timeout diagnostics override even a `SUCCESS` result: CLI 1.5.3 was observed returning exit 0 with partial output and an `AGY_ERROR` deadline envelope. The adapter rejects that partial result as a timeout (HTTP 504).

Optional environment settings:

| Variable | Default |
| --- | --- |
| `DEMO_EVALUATION_PROVIDER` | `antigravity` |
| `ANTIGRAVITY_MODEL` | `gemini-3.8-flash-medium` |
| `ANTIGRAVITY_TIMEOUT` | `120` seconds |
| `ANTIGRAVITY_EXECUTABLE` | `agy` from PATH (a native `.exe` on Windows) |

The official [headless interface](https://antigravity.google/docs/cli/headless/) supports cached account sign-in, schema output, and stdin requests. The SDK's documented setup currently uses API or Enterprise credentials, so this demo uses the already installed CLI to access the subscription. [Settings](https://antigravity.google/docs/settings?tab=cli) and [plans](https://antigravity.google/docs/plans) describe credit overages and plan limits.

## Preserved Gemini API version (inactive by default)

The existing Gemini API provider and `secrets/demo-gemini.json` are preserved. The default Antigravity path does not read this file or use its key. To explicitly select the earlier version:

```powershell
$env:DEMO_EVALUATION_PROVIDER = "gemini"
uv run --locked uvicorn examples.evaluateAnswer.demo_ui.main:app --reload
```

This version reads the ignored file, with same-named environment variables taking precedence. [gemini.example.json](gemini.example.json) documents its settings. It contacts the Gemini Developer API using a server-only key in the `x-goog-api-key` header. API project billing and quota are separate from Antigravity subscription quota; HTTP 402 indicates unavailable prepaid credits. To return to Antigravity, remove the `DEMO_EVALUATION_PROVIDER` override and restart.

## Demo API

The browser calls the local FastAPI server; only the server contacts Google.

| Method and path | Request | Response |
| --- | --- | --- |
| `GET /api/questions` | None | Demo question IDs and review labels |
| `GET /api/question?questionId=...` | Optional question ID; omitted selects the Task 2 example | Prompt, optional code, requirements, level, rubric labels and sample-answer labels |
| `GET /api/status` | None | Configuration presence, provider and model name; no credential |
| `GET /api/examples?questionId=...` | Optional question ID | Synthetic example IDs and labels for that question |
| `GET /api/examples/{case_name}?questionId=...` | Example ID and optional question ID | Exact sample answer text |
| `POST /api/preview` | `{"caseName":"correct","answerText":"exact sample text"}` | Existing `answerEvaluation/1` report for the Task 2 example's matching recording |
| `POST /api/evaluate` | `{"questionId":"...","answerText":"student answer"}` | Existing `answerEvaluation/1` report using the selected question and rubric |

The evaluation accepts up to 40,000 characters and rejects blank answers. The browser cannot supply a key or choose a model in either POST body. Error responses use FastAPI's `detail` message; HTTP 402 means unavailable billing credits, 429 means exhausted quota, 504 means a provider timeout, 502 means an invalid provider response or rejected output schema, and 422 means invalid input. Retrying the live demo is a new submission; it does not persist answers or reuse the CLI's saved-report cache.

Displayed reports belong to the exact submitted answer. Editing its text or loading a different answer clears the previous report; loading the identical text preserves its matching report.

With Node installed, run the UI state regression checks without a browser or provider call:

```powershell
node --test test/demoUiState.test.cjs
```

## Verified live smoke check

On 2026-11-11, the Task 2 synthetic `correct` answer was submitted with **Đánh giá bằng AI** through the running demo at `http://127.0.0.1:8001`. The Antigravity CLI returned a valid assessment using `gemini-3.8-flash-medium`; the local endpoint returned HTTP 200 and the UI displayed three scores of 2/2 with all six excerpts validated against the original answer. That smoke used prompt version `criterionEvidence/1+antigravity/2`, before later provider review changes. It confirms only that earlier Task 2 sample path; it does not validate the current prompt version or the new Task 3 question adapter.

The sample question and rubric are provisional. Recorded results demonstrate the presentation flow only; they are not human-reviewed judgments or evidence of live model quality. The web app does not persist submitted answers or reports. Antigravity manages its own local sessions and may retain transcripts outside this repository. Use synthetic answers for the presentation.

## Task 3 snapshot and handoff

The four imported Task 3 question/example sets are pinned under
[`task3_snapshot/`](task3_snapshot/README.md), sourced from commit
`9106f6d44a8e03ec8d7894a443679de2f0b2f05f` of
`origin/task3-answer-fixtures-Khoa`. They are not loaded from a Git branch at
runtime. All selected questions are still pending review; the adapter marks
them `exampleOnly=true`. The browser receives answer text and neutral category
labels, not expected scores or annotator judgments.

The follow-up requirements for integrating approved content, human-reviewed
references, recorded previews, persistence, and the MVC-S app flow are in
[`NEXT_STEPS.md`](NEXT_STEPS.md).
