# Dữ liệu minh họa

- `sampleInput.json`: câu hỏi tự soạn, 4 rubric, mỗi rubric có 3 mức 0/1/2,
  bài làm tổng hợp có giải thích và code. Không cố định thang này trong bộ chấm.
- `sampleReview.json`: diễn giải có sẵn cho đúng inputHash của sampleInput.
  Dùng trình diễn và kiểm thử cơ chế tính điểm; không phải kết quả Gemini thật.
- `alternativeAnswer.txt`: giải pháp vét cạn khác cách dùng bảng băm ở bài mẫu.
  Đề không yêu cầu thời gian tuyến tính, nên không được kết luận sai chỉ vì dùng
  cách này. Dùng cho đối chiếu thủ công và chạy Gemini sau khi cấu hình.

Các nội dung tự soạn này chưa được người khác kiểm duyệt; không có nguồn bên
ngoài hoặc giấy phép bên ngoài cần nhập. Chúng không được gắn trạng thái approved
hay dùng làm ngân hàng câu hỏi đã duyệt. Có sẵn code trong bài trả lời không có
nghĩa hệ thống sẽ thực thi code đó.

```powershell
.\.venv\Scripts\python.exe -m source.evaluateAnswer --input examples/evaluateAnswer/sampleInput.json --answerFile examples/evaluateAnswer/alternativeAnswer.txt --provider gemini
```

Sau khi chạy thật, cần người khác đối chiếu từng criterionCheck và evidence với
bài làm, đặc biệt việc chấp nhận thuật toán khác nhưng đúng. Không dùng file
sampleReview cho alternativeAnswer; bộ kiểm tra inputHash sẽ từ chối.
