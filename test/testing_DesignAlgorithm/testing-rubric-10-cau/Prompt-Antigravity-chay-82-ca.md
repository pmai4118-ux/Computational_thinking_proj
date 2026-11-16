# Prompt cho Antigravity

Bạn phụ trách chạy kiểm thử chức năng đánh giá câu trả lời kỹ thuật cho đồ án Tư duy tính toán. Hãy dùng terminal PowerShell và Python trong workspace `K:\HCMUS\HK4_2026-2027\TDTT`. Tạo script, thực sự chạy kiểm thử, lưu kết quả và chuẩn bị nội dung 10 slide bằng tiếng Việt. Đây là đợt kiểm tra tính năng với Gemini 3.5 Flash-Lite. Nếu người dùng yêu cầu đo Gemini 3.8 Flash, dùng cổng 8002 với model gemini-3.8-flash thay cho cổng 8003 và lưu ở run ID riêng. Không gộp số liệu hai model. Kiểm tra promptVersion của báo cáo đầu tiên là criterionEvidence/2 và ghi phiên bản cho toàn bộ đợt.

## 1. Dữ liệu và dịch vụ

- Thư mục repo là `Computational_thinking_proj`. Đọc `AGENTS.md`, `PROJECT_SPEC.md`, `Computational_thinking_proj/AGENTS.md` và phần liên quan trong README demo.
- Thư mục dữ liệu là `deliverables/testing-rubric-10-cau`. Dùng `A-30-ca-requests.jsonl` (10 đúng, 10 sai phân nửa, 10 null) và `B-52-ca-requests.jsonl` (40 đúng, 10 sai, 2 null). Tổng cộng cần kiểm thử 82 ca, 10 câu hỏi và 400 lượt đối chiếu tiêu chí tham chiếu. Dùng `dap-an-tham-chieu.json` để lấy mã ca, rubric, nhãn và căn cứ kỳ vọng; kiểm tra dữ liệu hai tập theo mã ca và đối chiếu phiên bản với catalog.
- Antigravity điều khiển terminal. Provider được kiểm thử là **Gemini API với model ID `gemini-3.5-flash-lite`**. Kiểm tra `GET http://127.0.0.1:8003/api/status` trước. Chỉ chạy khi `providerName=gemini`, `modelName=gemini-3.5-flash-lite`, `liveEvaluationConfigured=true`. Nếu demo chưa chạy, dùng Python của repo để khởi động `python -m source.main --web --port 8003` với `DEMO_EVALUATION_PROVIDER=gemini`, `GEMINI_MODEL=gemini-3.5-flash-lite` và `EVALUATION_TIMEOUT=300` trong môi trường của tiến trình. Nếu cấu hình hoặc key còn lỗi, báo lỗi cụ thể và giữ kết quả đã có để tiếp tục sau.
- Gửi từng JSON tới **POST `http://127.0.0.1:8003/api/evaluate`**. Chỉ gửi các trường của request body, tuyệt đối không gửi nhãn tham chiếu hay kết quả mong đợi. Chạy live qua backend. Giữ nguyên nội dung câu trả lời, rubric, model và prompt. Không dùng `/api/preview`, fixture recorded, mock hay chấm thay bằng Antigravity. Không đọc, in hoặc sao chép API key. Backend đã quản lý key.

## 2. Cách chạy trong terminal

1. Tạo `deliverables/testing-rubric-10-cau/run_evaluation.py`, chạy được bằng thư viện chuẩn Python. Hỗ trợ đối số `--base-url`, `--run-dir` và `--resume`. Chỉ thêm script và báo cáo, giữ nguyên mã sản phẩm và dữ liệu nguồn.
2. Đặt đầu ra theo thư mục `deliverables/testing-rubric-10-cau/ket-qua/<run-id>/`. Ghi thời điểm, model, phiên bản prompt, ID phiên bản rubric và số lượng ca. Mỗi đợt mới có run ID và answerId riêng hợp lệ theo schema để backend không tái sử dụng báo cáo của đợt cũ. Retry hoặc resume trong cùng đợt giữ nguyên ID ca, input và answerId. Giữ một bản đồ ổn định từ caseId sang answerId đã dùng.
3. Chạy **A-Q002-Dung-01** trước để xác nhận pipeline trả được một EvaluationReport với model đã chốt. Tính luôn ca này vào 82 ca. Nếu điểm thực tế khác nhãn dự kiến nhưng API trả báo cáo hợp lệ, ghi nhận sai khác và tiếp tục.
4. Chạy lần lượt một request tại một thời điểm, dùng HTTP client timeout khoảng **330 giây** để backend có đủ 300 giây. Sau mỗi lần thử, ghi ngay một dòng JSONL gồm caseId, attempt, HTTP status, thời gian, lỗi hoặc EvaluationReport đầy đủ. In tiến độ, ví dụ `[14/82] A-Q017-SaiNua-01 HTTP 200 22.4s`. Dùng UTF-8, lưu đầy đủ xuống đĩa để chạy tiếp được. Cho phép tiếp tục các ca chưa xong bằng `--resume`; bỏ qua ca đã có báo cáo thành công.
5. Lỗi mạng, timeout và lỗi tạm thời chỉ retry có giới hạn, tối đa một lần mỗi ca trong lần chạy hiện tại. Nếu HTTP 429 có Retry-After thì tôn trọng thời gian đó. Nếu xác định hết quota, lỗi billing, key hoặc model, dừng gửi thêm request và báo số ca chưa chạy. Ghi rõ số ca có báo cáo, số ca lỗi và số ca chưa chạy. Không đổi lỗi API thành điểm 0 hoặc null. Đợt chạy còn ca chưa xong phải ghi là kết quả tạm thời.

## 3. Cách kiểm tra nhận diện lỗi và điểm

Đối chiếu theo `rubricId` và `criterionId`, kể cả khi thứ tự khác. Dùng các trạng thái `met`, `unmet`, `insufficientEvidence` như dữ liệu thật.

- **Nhận diện tiêu chí (M).** So trạng thái thực tế với nhãn dự kiến. Tính số đúng trên số tiêu chí có báo cáo, ma trận nhầm lẫn 3×3, Precision/Recall cho lớp `unmet` và tỷ lệ nhận diện đúng `insufficientEvidence`. Nếu mẫu số bằng 0 thì ghi không áp dụng. Liệt kê sai sót cụ thể: ý sai hoặc thiếu bị bỏ qua, đánh sai ý đúng, hoặc kết luận quá chắc khi thiếu căn cứ. Gắn mỗi sai khác với caseId, criterionId, trích dẫn thực tế nếu có và yêu cầu của rubric.
- **Nguồn bằng chứng.** Với excerpt hoặc ambiguity, kiểm tra quote khớp nguyên văn và `originalText[startOffset:endOffset]` khớp quote khi có offset. Với omission, kiểm tra quote và offset đều null, và trạng thái phù hợp `omissionMeansUnmet`. Trích dẫn khác đáp án tham chiếu vẫn có thể phù hợp. Tách kết quả kiểm tra nguyên văn/vị trí khỏi đánh giá đoạn trích có thực sự chứng minh nhận xét hay không. Ghi đánh giá ngữ nghĩa có lý do hoặc đánh dấu cần người duyệt, nhất là khi có bất đồng. Nếu backend trả `invalidEvidence`, ghi riêng ca bị chặn ở bước kiểm tra bằng chứng.
- **Tính điểm theo quy tắc (R).** Từ các trạng thái thực tế, tính lại điểm độc lập theo scoreLevels: xét từ cao xuống thấp, mức đầu tiên thỏa `requiredMet` và `minimumMet` là mức chọn. Tính một lần với tập tiêu chí đạt và một lần với tập đạt hợp tiêu chí chưa rõ. Cùng mức thì chốt điểm; khác mức thì điểm null. So điểm tính lại với điểm backend trả. Báo tỷ lệ này riêng với tỷ lệ **điểm thực tế khớp điểm tham chiếu**. Nếu Gemini chọn sai trạng thái nhưng backend tính đúng từ trạng thái đó, phân loại sai khác ở M.
- **Nhận xét cho người học.** Trích thực tế từ `feedbackItems.explanation`, `feedbackItems.identifiedIssues` và `results[].criterionChecks[].evidence`. Kiểm tra điểm mạnh có căn cứ từ tiêu chí đạt, vấn đề đúng với tiêu chí chưa đạt, yêu cầu cải thiện bám rubric và phần chưa rõ được xử lý phù hợp. Nếu nội dung chỉ nói tiêu chí mà chưa chỉ rõ cách sửa, ghi đúng hạn chế đó. Phân biệt đoạn trích nguyên văn với gợi ý của nhóm.
- **Ca null.** Kiểm tra từng rubric được kỳ vọng null. Lưu ý B-Q007-Null-01 có Knowledge = 2 và Analysis = null. Một bài có rubric null vẫn có thể trả HTTP 200, phản hồi và điểm ở rubric khác.

## 4. Đầu ra cần bàn giao

Xuất trong thư mục đợt chạy, giữ đủ dữ liệu để người khác có thể kiểm tra lại.

| Tệp | Nội dung |
| --- | --- |
| `raw-results.jsonl` | Lịch sử tất cả lượt gọi và kết quả gốc. Không chứa key. |
| `thong-ke-82-ca.csv` | Đủ 82 dòng kể cả ca lỗi và chưa chạy. Có mã ca, bộ A/B, câu hỏi, loại bài, HTTP, thời gian, trạng thái tiêu chí và điểm kỳ vọng/thực tế, kết quả M/R, nhận xét và nguyên nhân sai khác. |
| `thong-ke-10-cau.csv` | Một dòng mỗi câu hỏi. Có tổng ca, đã chạy, có báo cáo, lỗi, chưa chạy, số tiêu chí khớp/tổng có thể so, số rubric khớp điểm kỳ vọng và số rubric backend tính đúng theo trạng thái thực tế. |
| `doi-chieu-tieu-chi.csv` | Một dòng mỗi cặp ca và criterionId tham chiếu. Lưu status kỳ vọng/thực tế, trích dẫn, kết quả đối chiếu và ghi chú. |
| `bao-cao-testing.md` | Tổng quan, bảng theo câu, theo A/B và theo loại ca, ma trận nhầm lẫn, số ca null đúng, lỗi API, phân tích nguyên nhân và các giới hạn của nhãn dự kiến chưa duyệt độc lập. Nêu mẫu số cạnh mọi tỷ lệ. Có thể báo thêm thời gian trung vị và P95 nếu đủ dữ liệu. |
| `10-cau-de-dua-len-slide.md` | 10 mục, mỗi mục dành cho một slide. Mỗi mục gồm tên/mã câu và đề; mã ca và bài làm; kết quả AI thật; điểm kỳ vọng và điểm thực tế theo rubric; điểm mạnh, điểm yếu, ý cần cải thiện hoặc cần làm rõ, kèm bằng chứng; một câu kết luận ca đúng hay sai và ở bước nào. |

Cho 10 slide, ưu tiên các ca A-Q002-Dung-01, A-Q005-SaiNua-01, B-Q007-Null-01, A-Q009-Dung-01, A-Q010-SaiNua-01, A-Q017-Null-01, A-Q018-Dung-01, B-Q022-Sai-01, A-Q028-SaiNua-01 và A-Q085-Dung-01. Nếu ca ưu tiên lỗi API, dùng ca có kết quả thật khác của cùng câu và ghi rõ mã ca đã dùng. Nếu câu đó chưa có kết quả thật, ghi rõ chưa có nhận xét live và lý do. Với bài dài, có thể dùng trích đoạn đáp án nguyên văn đủ minh họa, ghi rõ là trích đoạn và trỏ về mã ca để tra toàn văn.

Kết thúc bằng số lượng đã chạy trên 82, số báo cáo hợp lệ, số lỗi, số chưa chạy, model/prompt đã ghi, một vài sai khác tiêu biểu và đường dẫn của tất cả tệp đầu ra. Thực thi công việc qua terminal và chỉ báo những gì có bằng chứng từ dữ liệu chạy thật.
