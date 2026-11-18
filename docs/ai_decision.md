# Khảo sát AI Provider, Structured Output, Quota và Ngân sách (P07)

| Thuộc tính | Nội dung |
| --- | --- |
| Mã công việc | P07 — Khảo sát Gemini, SDK, quota và ngân sách |
| Người thực hiện | hwngMP (`member-1`) |
| Phụ thuộc | [P03 (`data_contract.md`)](data_contract.md), [P05 (`rubric_guide.md`)](rubric_guide.md), [F06 (`source/config.py`)](../source/config.py) |
| Đầu ra | `docs/ai_decision.md`, [`.env.example`](../.env.example), [`source/config.py`](../source/config.py), [`source/service/providers/antigravity_provider.py`](../source/service/providers/antigravity_provider.py), [`source/service/providers/gemini_provider.py`](../source/service/providers/gemini_provider.py) |

---

## 1. So sánh 2 phương án kết nối AI (từ PoC `evaluateAnswer`) & Chốt phương án nhóm

Từ quá trình thử nghiệm trên nhánh tham khảo `evaluateAnswer`, nhóm đánh giá **hai phương thức chạy đánh giá AI thật** (cùng chế độ ngoại tuyến `fixture` để phát triển không cần tài khoản):

| Tiêu chí | Phương án A — Nối trực tiếp qua **Antigravity CLI (`antigravity`)** *(Nhóm chọn dùng chính)* | Phương án B — Gọi Gemini REST API qua **API Key (`gemini`)** *(Phương án dự phòng)* |
| --- | --- | --- |
| **Biến cấu hình** | `EVALUATION_PROVIDER=antigravity`<br>`ANTIGRAVITY_MODEL=gemini-3.8-flash-medium` (`120s` timeout) | `EVALUATION_PROVIDER=gemini`<br>`GEMINI_MODEL=gemini-2.5-flash-lite` (hoặc `gemini-2.5-flash`) + `GEMINI_API_KEY` |
| **Model đã chốt** | **`gemini-3.8-flash-medium`** (*Gemini 3.8 Flash (Medium)* trong `agy models`) | `gemini-2.5-flash` / `gemini-2.5-flash-lite` |
| **Cơ chế xác thực** | Phiên đăng nhập **Antigravity CLI (`agy`)** cục bộ trên máy server (`--input-format stream-json`, `--output-format stream-json`); tự động xóa biến `GEMINI_API_KEY`/`GOOGLE_API_KEY` khỏi môi trường con để không gọi nhầm API key. | Khóa `GEMINI_API_KEY` đọc qua `SecretStr` tại server (`x-goog-api-key` tới `generativelanguage.googleapis.com`). |
| **Ràng buộc an toàn** | Chạy trong thư mục rỗng tạm thời (`TemporaryDirectory`), tắt slash command (`--disable-slash-commands`), chặn toàn bộ tool (`command`, `read_file`, `write_file`, `read_url`, `execute_url`, `mcp`), chỉ nhận tool `finish` và schema `AntigravityAssessmentResponse` khóa theo `criterion_id` (`--json-schema`). Trên Windows yêu cầu tệp `.exe` gốc (từ chối `.cmd`/`.bat` shim). | `responseMimeType="application/json"` + `responseJsonSchema` (`AnswerInterpretationResponse`), không cần SDK ngoài nhờ `urllib.request`, chặn `250 KB` input / `1 MB` output, lọc phần `thought: true`. |
| **Quyết định nhóm** | **CHỌN LÀM PROVIDER CHẠY THẬT CHÍNH** của nhóm (`gemini-3.8-flash-medium` qua `agy`), không cần cấp phát hoặc chia sẻ `GEMINI_API_KEY` trả phí. | **GIỮ LẠI LÀM ADAPTER TÙY CHỌN** qua cùng giao diện `EvidenceInterpreter` khi cần chạy trên server không có `agy`. |

### Phân tách trách nhiệm AI và Python (Computational Thinking boundary)
- Cả **Antigravity (`gemini-3.8-flash-medium`)** và **Gemini API** **chỉ** thực hiện trích xuất bằng chứng theo tiêu chí (`status` thuộc `met | unmet | insufficient_evidence`, `quote` + offsets hoặc `observation`, `explanation`, `unresolved_reason`).
- Không có provider nào được phép trả điểm số (`score` hoặc `total_score`). Việc xác thực độ bao phủ tiêu chí, đối chiếu đoạn trích nguyên văn (`E05`) và tính điểm theo bảng quy tắc rubric (`E06`) luôn do mã Python thực hiện.

---

## 2. Quota, Ngân sách và Ràng buộc vận hành

| Hạng mục | Quyết định cho dự án |
| --- | --- |
| **Gói tài khoản & chi phí** | Nhóm sử dụng phiên đăng nhập **Antigravity (`agy`)** với model `gemini-3.8-flash-medium` (không giả định ngân sách Paid API Tier); nếu chạy chế độ API key (`gemini`) chỉ giả định **Google AI Studio Free Tier** cục bộ. |
| **Chế độ mặc định khi phát triển / CI** | `EVALUATION_PROVIDER=fixture` trong [`.env.example`](../.env.example). Toàn bộ luồng UI, Controller và kiểm thử tự động chạy ngoại tuyến không cần đăng nhập `agy` hay `GEMINI_API_KEY`, gắn nhãn **`Dữ liệu minh họa`**. |
| **Giới hạn kích thước & Timeout** | Antigravity: input tối đa `250 KB`, stdout tối đa `2 MB`, `ANTIGRAVITY_TIMEOUT_SECONDS = 120` (hợp lệ `1–300s`).<br>Gemini REST: request `250 KB`, response `1 MB`, `GEMINI_TIMEOUT_SECONDS = 30` (`1–120s`). |
| **Ngân sách gọi AI khi kiểm định (`Q03`)** | Tối đa `1` lần gọi cho mỗi mẫu trong bộ giữ lại (`held-out` của `C07`), retry tối đa `1` lần cho lỗi tạm thời (`timeout` / `RESOURCE_EXHAUSTED` / `429`). Không tự động fallback sang API key khi `antigravity` hết quota. |
| **Bảo mật (`F06`)** | Không lưu khóa API, token hay dữ liệu bài làm riêng vào Git, client JS hoặc log lỗi. Adapter Antigravity loại bỏ hoàn toàn các biến `GEMINI_API_KEY` trước khi gọi `agy` và không đưa văn bản bài làm vào tham số dòng lệnh (truyền qua `stdin`). |

---

## 3. Kết quả kiểm tra xác minh P07

1. **Xác minh CLI `agy` và yêu cầu tổng hợp thật trên `gemini-3.8-flash-medium`:**
   - Lệnh `agy models` xác nhận sự tồn tại của model slug **`gemini-3.8-flash-medium`** (*Gemini 3.8 Flash (Medium)*) cùng `gemini-3.8-flash-low` và `gemini-3.8-flash-high`, và `agy --help` xác nhận đầy đủ các cờ `--settings`, `--model`, `--disable-slash-commands`, `--input-format stream-json`, `--output-format stream-json`, `--json-schema`, `--print-timeout`.
   - Đã chạy kiểm tra **1 yêu cầu tổng hợp nhỏ** qua `AntigravityProvider` gọi trực tiếp `agy` CLI (`gemini-3.8-flash-medium`, `ANTIGRAVITY_TIMEOUT_SECONDS=60`) kết hợp `EvidenceValidator` + `RubricScoringService` trên mẫu giả lập 1 tiêu chí `c03.race`:
     - Kết quả thật quan sát được: `status=met`, trích dẫn nguyên văn khớp chính xác chỉ số `0:94`, `total_score=2/2`, `prompt_version=interpret_answer/v1+antigravity/1`, thời gian phản hồi **`elapsed_ms=60972` (~61 giây)** — xác nhận thực tế lý do cần giữ mặc định `ANTIGRAVITY_TIMEOUT_SECONDS=120` thay vì 30 giây.
   - Giới hạn rõ: đây mới là 1 ca kiểm tra kỹ thuật tối thiểu ở P07; việc đo độ chính xác và độ đồng thuận trên toàn bộ bộ mẫu `held-out` thuộc phạm vi **`Q03`** (`docs/evaluation_report.md`).
2. **Kiểm tra hợp đồng cấu hình và bộ giả lập (`test/test_config.py`, `test/test_antigravity_provider.py`, `test/test_gemini_provider.py`):**
   - Kiểm tra cấu hình `EVALUATION_PROVIDER=antigravity` mặc định `ANTIGRAVITY_MODEL=gemini-3.8-flash-medium` không đòi `GEMINI_API_KEY` và trả `demo_label=None`.
   - Kiểm tra `AntigravityProvider` tạo schema JSON không chứa từ khóa cấm (`prefixItems`, `allOf`, `const`), gửi bài làm qua `stdin`, từ chối tool call ngoài `finish`, xử lý `AGY_ERROR:` vượt mặt `SUCCESS` khi hết `--print-timeout`, và giải mã đúng offset cho câu trích dẫn duy nhất.
   - Chế độ mặc định khi phát triển và chạy CI vẫn là `EVALUATION_PROVIDER=fixture` (`FixtureProvider`) để không phụ thuộc mạng hay tài khoản cá nhân.

```powershell
uv run --locked python -m pytest test/test_config.py test/test_antigravity_provider.py test/test_gemini_provider.py -q
```
