# PoC đánh giá câu trả lời

Phạm vi: đánh giá một câu trả lời theo từng rubric, tính mức điểm bằng Python và
phản hồi có căn cứ. Đầu vào là câu hỏi, các rubric tương ứng và bài làm nguyên văn.
Đầu ra gồm từng tiêu chí, bằng chứng, điểm hoặc lý do chưa thể chấm, và phản hồi.

Thiết kế dựa trên `Abstraction.docx`, `decompose.png` và
`Keep-Remove-Deffer.png` do người dùng cung cấp. Thang điểm nhiều mức được giữ theo
yêu cầu mới nhất và tài liệu abstraction, kể cả khi một dòng cũ trong sơ đồ còn
ghi bản tối thiểu chưa cần điểm.

## 1. Chạy ngay bằng dữ liệu minh họa

Mở PowerShell tại thư mục repo. Cài môi trường theo README nếu chưa có:

```powershell
uv sync --locked
.\.venv\Scripts\python.exe -m source.evaluateAnswer --input examples/evaluateAnswer/sampleInput.json --provider recorded --recording examples/evaluateAnswer/sampleReview.json
```

Kết quả hiển thị bằng tiếng Việt và được lưu vào `localReports/` dưới tên mới.
Không ghi đè báo cáo cũ. JSON lưu nguyên đầu vào, phiên bản, mã băm đầu vào,
nguồn diễn giải, phiên bản prompt, kết quả và phản hồi. Thư mục này được Git bỏ qua
vì có thể chứa bài làm riêng tư.

**`recorded` dùng kết quả diễn giải có sẵn để trình diễn và kiểm tra phần mềm. Nó
không tự hiểu bài mới và không chứng minh chất lượng chấm của AI.** Thay câu hỏi,
rubric hoặc bài làm sẽ làm mã băm không khớp và bị từ chối. Câu hỏi và diễn giải
mẫu do chúng tôi tự soạn cho PoC, chưa được người khác kiểm duyệt. Chúng không phải
nội dung đã duyệt để nhập vào ngân hàng câu hỏi của nhóm.

## 2. Đánh giá bài mới bằng Gemini

Repo dự kiến Gemini. Adapter dùng REST `generateContent`, không thêm SDK hay đổi
`uv.lock`. Cấu hình model có quyền truy cập và hỗ trợ structured JSON trong tài
khoản của nhóm. Không tự chọn model hoặc dịch vụ trả phí thay cho nhóm.

```powershell
$secretKey = Read-Host "Gemini API key" -AsSecureString
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', $secretKey).Password
$env:GEMINI_MODEL = "ten-model-trong-tai-khoan-cua-ban"
$env:EVALUATION_TIMEOUT = "45"
New-Item -ItemType Directory -Force localAnswers
notepad localAnswers/answer.txt
.\.venv\Scripts\python.exe -m source.evaluateAnswer --input examples/evaluateAnswer/sampleInput.json --answerFile localAnswers/answer.txt --provider gemini
Remove-Item Env:\GEMINI_API_KEY
```

Lưu bài mới dưới dạng UTF-8. `--answerFile` tạo mã bài mới và giữ nguyên xuống dòng,
khoảng trắng trong nội dung; không sửa tệp đầu vào. Muốn đổi cả câu hỏi/rubric,
tạo JSON khác theo mẫu, không chỉ thay prompt trong khi giữ tiêu chí của câu cũ.

Mỗi lần chạy Gemini gửi câu hỏi, tiêu chí và bài làm tới Google, với một request
duy nhất; không tự retry và không tự chuyển sang dữ liệu mẫu khi có lỗi. Timeout,
quota, từ chối, phản hồi bị cắt và JSON sai đều là **lỗi xử lý**, không phải điểm
thấp của người học. Tệp bài gốc vẫn còn để chạy lại. API key chỉ đọc từ môi trường,
không đưa vào URL, báo cáo hoặc thông báo lỗi.

Tham khảo API: [structured output](https://ai.google.dev/gemini-api/docs/structured-output),
[generateContent](https://ai.google.dev/api/generate-content).

## 3. Luồng và tổ chức code

```text
source.evaluateAnswer (cấu hình và điểm chạy CLI)
  -> Control/evaluationController.evaluateAnswer
  -> service/answerEvaluation
     -> createEvaluation: kiểm tra liên kết và rubric
     -> evaluate: interpreter -> kiểm tra bằng chứng -> tính điểm
     -> generateFeedback: tạo phản hồi từ kết quả đã có
     -> readReport: đọc kết quả, không sửa trạng thái
  -> view/evaluationView: định dạng kết quả
  -> Model/reportFiles: lưu báo cáo hoàn chỉnh
```

| Nội dung từ decomposition/abstraction | Cài đặt |
| --- | --- |
| Câu hỏi, yêu cầu, ràng buộc, năng lực thực sự được chấm | `Model/answerData.py`; kiểm tra liên kết trong `service/rubricRules.py` |
| Số mức, mô tả, ngưỡng, tiêu chí bắt buộc và ranh giới các mức | `Rubric.scoreLevels`; `validateLevels`, `findLevel`, `scoreChecks` |
| Hiểu nội dung quan trọng, chấp nhận cách giải khác, không tự thêm ý | `providers/evaluationPrompt.py`; interpreter nhận bài nguyên văn |
| Phân biệt sai, thiếu yêu cầu rõ ràng và chưa đủ căn cứ | `CriterionCheck.status`, `Criterion.reviewRule`, `omissionMeansUnmet` |
| Trích dẫn/bằng chứng cho từng nhận định | `service/evidenceReview.py`; kiểm tra quote và offsets |
| Phản hồi nội dung đáp ứng/chưa đạt và lý do | `service/feedbackBuilder.py`; không gọi AI chấm lần nữa |
| ADT và đầu vào bất biến, không xuất kết quả chấm dở dang | `service/answerEvaluation.py`; các mô hình frozen và tuple |
| Cấu trúc chung có thể dùng cho nhiều câu hỏi | Cùng `Question`, `Rubric`, `CriterionCheck`, `Evidence` cho dữ liệu khác nhau |

Không cộng điểm giữa các năng lực, không kết luận năng lực tổng thể từ một câu,
không xây ngân hàng câu hỏi, lựa chọn thích ứng, giọng nói hoặc lộ trình học trong
PoC này. Chưa có giao diện web hay lưu phiên DB; gọi Controller được từ giao diện
của nhóm sau này. Giữ nguyên `source/main.py` dành cho app factory F05.

## 4. Rubric thực thi được

Mô tả bằng chữ là cần thiết cho người đọc, nhưng Python không thể tự suy ra quy
tắc chấm tùy ý từ `scoringRule: String`. Vì vậy PoC bổ sung hai trường rõ nghĩa
vào mỗi `ScoreLevel`:

| Trường | Ý nghĩa |
| --- | --- |
| `value` | Điểm thực tế của mức; không cố định 0–2 hay 0–10. |
| `description` | Mức thể hiện đạt được, không phải một đáp án mẫu duy nhất. |
| `condition` | Diễn giải điều kiện bằng chữ cho người đọc. |
| `requiredMet` | Những criterionId bắt buộc phải là `met` để đạt mức này. |
| `minimumMet` | Số tiêu chí `met` tối thiểu trong rubric này. |

Python chọn **mức có value cao nhất thỏa cả hai điều kiện**. Các điều kiện của
nhiều mức có thể cùng đúng; quy tắc chọn mức cao nhất giải quyết trường hợp này.
Mức cơ sở có `requiredMet=[]`, `minimumMet=0`. Số mức bằng độ dài `scoreLevels`,
không lưu thêm biến đếm dễ lệch. Giá trị điểm phải hữu hạn, khác nhau, tăng dần.
Không chấp nhận mức không thể đạt hoặc tham chiếu tiêu chí không có.

Ví dụ một rubric có A = lập luận nền tảng và B = phân tích đầy đủ:

| Điểm | Điều kiện | Phân biệt mức liền kề |
| --- | --- | --- |
| 0 | Không cần tiêu chí met | Chưa xác nhận A. |
| 1 | A met, tối thiểu 1 tiêu chí met | Đã xác nhận nền tảng A. |
| 2 | A và B met, tối thiểu 2 tiêu chí met | Đã xác nhận cả A và phần phân tích B. |

Sai A ảnh hưởng nền tảng nên không được mức 1 hoặc 2, dù B met. Đây là quy tắc của
rubric ví dụ; câu khác có thể dùng ngưỡng đếm hoặc bộ tiêu chí bắt buộc khác. Các
thiếu sót quan trọng phải được tách thành tiêu chí đủ cụ thể để quy tắc thể hiện
được tác động. PoC không hỗ trợ biểu thức Python tùy ý, trọng số hoặc điều kiện
phủ định trong rubric. Nếu cần quy tắc khác, mở rộng schema và bộ tính điểm, không
âm thầm diễn dịch đoạn văn thành thuật toán.

### Chưa đủ căn cứ không phải 0

Tính mức thấp nhất từ tiêu chí đã xác nhận met, và mức cao nhất nếu các tiêu chí
chưa rõ đều met. Các điều kiện chỉ gồm các yêu cầu dương nên điểm không thể giảm
khi thêm tiêu chí met. Nếu hai mức bằng nhau, mức đã được xác định; nếu khác nhau,
giữ `score=null` và nêu tiêu chí cần làm rõ.

- A met, B chưa rõ: có thể mức 1 hoặc 2 → chưa chấm điểm.
- A unmet, B chưa rõ: cả hai khả năng đều mức 0 → chấm 0, vẫn ghi B chưa rõ.
- Bài rỗng: là bài đã nộp. Với tiêu chí yêu cầu trình bày rõ và cho phép kết luận
  thiếu yêu cầu, ghi omission/unmet; không nhầm với lỗi API.

Giới hạn PoC: tối đa 8 rubric/câu, 12 tiêu chí/rubric, 16 mức/rubric, 40.000 ký tự
bài làm, 250 KB request AI và 1 MB phản hồi. Kiểm tra khả năng đạt từng mức duyệt
tối đa 2^12 tập tiêu chí. Các giới hạn được khai báo để tránh xử lý không giới hạn.

## 5. Bằng chứng và giới hạn nhận định

`excerpt` và `ambiguity` phải trích đúng chuỗi từ `originalText`. Offsets là chỉ số
Unicode Python, đầu bao gồm, cuối không gồm. Nếu một quote xuất hiện duy nhất,
Python có thể điền offsets; nếu xuất hiện nhiều lần, cần offsets chính xác.
`omission` không có quote/offsets, ghi phạm vi đã xem và yêu cầu bị thiếu.
`omissionMeansUnmet` phải được người soạn rubric chọn rõ; mặc định không suy diễn
từ câu văn reviewRule. `ambiguity` chỉ đi với `insufficientEvidence`.

Các kiểm tra này phát hiện trích dẫn bịa, lệch vị trí, ID sai/trùng/thiếu và dữ
liệu sai cấu trúc. **Trích dẫn đúng không chứng minh nhận xét về ý nghĩa là đúng.**
Gemini vẫn có thể hiểu sai kỹ thuật, phủ định, mức độ thiếu sót hoặc nội dung mơ
hồ. Cần đối chiếu kết quả với người chấm độc lập trước khi kết luận PoC đạt yêu
cầu về chất lượng. PoC không thực thi code do người học gửi, nên không tuyên bố
code đó đã vượt qua kiểm thử.

Feedback dùng kết quả và quan sát đã lưu, không tạo điểm mới. Chỉ tiêu chí `unmet`
được liệt kê trong `identifiedIssues`; phần chưa rõ được nêu riêng trong giải
thích. Các nhận xét chỉ áp dụng cho câu hỏi đang xét.

## 6. Kiểm thử và đánh giá PoC

```powershell
uv run --locked python -m pytest -q
uv pip check
```

Bộ kiểm thử gồm luồng CLI, đầy đủ 9 tổ hợp trạng thái của rubric hai tiêu chí,
điểm tùy chỉnh, ngưỡng đếm, rubric sai, bằng chứng sai, dữ liệu bất biến, lỗi AI,
không ghi đè báo cáo và không xuất kết quả khi xử lý thất bại. Các lời gọi AI trong
kiểm thử đều giả lập; không dùng khóa thật hay chi phí API.

Lần kiểm tra triển khai ngày 10/11/2026: **63 kiểm thử đạt** trên CPython 3.11.18,
`uv pip check` xác nhận 26 gói tương thích, luồng CLI recorded tạo được báo cáo
với đủ bốn kết quả và phản hồi. Chưa thực hiện lời gọi Gemini thật và chưa có kết
quả đánh giá độ chính xác ngữ nghĩa bởi người chấm độc lập.

Để kiểm chứng chất lượng diễn giải thật, dùng cùng câu hỏi và rubric đã được người
khác rà soát, chuẩn bị các bài: đúng đầy đủ; cách giải khác đúng; sai điều kiện
cốt lõi; thiếu yêu cầu; mơ hồ; rỗng. Người chấm ghi kết quả kỳ vọng theo tiêu chí
trước khi xem kết quả AI. Chạy `--provider gemini`, đối chiếu trạng thái, căn cứ,
mức điểm và phản hồi; báo cáo các chỗ bất đồng. Không dùng kết quả `recorded` làm
số liệu độ chính xác của AI.

## 7. Tương thích với repo chung

Phần này thực hiện phạm vi PoC tương ứng E01, E03–E07 và phần lỗi/điều phối của
E08–E09; không tuyên bố hoàn thành toàn bộ sprint, persistence, UI hay live benchmark.
Không xóa hoặc đổi tên file có sẵn. Mô hình P03 vẫn giữ nguyên và tái sử dụng các
kiểu ID từ `source/Model/ids.py`.

Bản abstraction mới có nhiều rubric theo năng lực/câu và chấm mức trên rubric,
trong khi P03 đang có một rubric/câu và mức điểm theo criterion. Do đó PoC có
namespace/schema `answerEvaluation/1` riêng ở `answerData.py`, `evaluationData.py`;
không giả định chúng thay thế trực tiếp các dataclass P03. Xem phần bổ sung trong
`data_contract.md` trước khi tích hợp. Các tên mới dùng camelCase; PascalCase dành
cho lớp/kiểu. Tên bắt buộc của Python/Pydantic/pytest như `__init__`, `model_config`
và cấu hình công cụ được giữ đúng API.
