# Q05 — Biên bản quan sát người dùng chưa quen giao diện

| Thuộc tính | Nội dung |
| --- | --- |
| Mã công việc | Q05 — Cho người chưa quen UI thử luồng |
| Phụ thuộc đầu vào | U07 (tích hợp API client trên nhánh `Demo`) |
| Lớp / Phạm vi | QA / Docs và chỉnh sửa giao diện mức ưu tiên cao tại `source/view/` |
| Nguyên tắc riêng tư | Ẩn danh toàn bộ người tham gia (`P1`, `P2`, `P3`). Không ghi họ tên, email, MSSV, ảnh chụp có thông tin cá nhân hay bài làm của sinh viên thật. |
| Trạng thái kiểm định | Đã ghi nhận **2 biên bản thực tế (`P1` và `P2`)** và đối chiếu kiểm tra luồng giao diện cục bộ; các vấn đề đã tái hiện ở `P1` và `P2` đều đã được phân loại/sửa kèm test hồi quy. Lượt `P3` tùy chọn vẫn để mở trước khi chốt Q08. |

---

## 1. Nhiệm vụ ngắn cho người chưa quen giao diện (Không dẫn từng nút)

### Mục tiêu nhiệm vụ
> Bạn hãy đóng vai sinh viên chuẩn bị phỏng vấn vị trí **Backend Intern / Fresher**. Hãy tự sử dụng ứng dụng web để:
> 1. Bắt đầu một phiên luyện phỏng vấn mới bằng tiếng Việt.
> 2. Đọc đề bài và nộp câu trả lời (có thể dán nội dung từ bộ câu trả lời tổng hợp bên dưới).
> 3. Xem kết quả đối chiếu từng tiêu chí và kiểm tra đoạn căn cứ trong bài làm của mình.
> 4. Đi tiếp sang câu khác hoặc kết thúc phiên để xem trang tổng kết.
> 5. Tìm một bài tập gợi ý cho điểm còn thiếu (nếu có) và thử mở lượt luyện lại.
>
> *Lưu ý cho người điều phối:* Không chỉ vị trí từng nút, không giải thích trước ý nghĩa từng nhãn. Chỉ can thiệp khi người thử bị kẹt hoàn toàn, và ghi lại chính xác điểm dừng hoặc hiểu nhầm.

### Bộ câu trả lời tổng hợp dùng khi thử (Synthetic Answers — không dùng bài thật)
Chọn sẵn các tệp tổng hợp có sẵn trong repository để người thử không phải tự soạn dài:
- Câu trả lời thiếu một phần (tạo điểm thiếu đã xác nhận để kiểm tra luồng bài tập): `test/fixtures/answers/ans_c02_02_partial.txt`, `test/fixtures/answers/ans_c03_02_partial.txt`
- Câu trả lời mơ hồ (kiểm tra hiển thị `Chưa đủ bằng chứng`, `score: null` không biến thành `0`): `test/fixtures/answers/ans_c04_05_ambiguous.txt`
- Câu trả lời đầy đủ: `test/fixtures/answers/ans_c05_01_correct.txt`

---

## 2. Ghi nhận thực tế từ người tham gia chưa quen UI

### 2.1. Người tham gia `P1` (Phiên quan sát thực tế)

- **Nguồn ghi nhận:** Biên bản đánh giá trải nghiệm ẩn danh từ người dùng thử lần đầu (không lưu danh tính cá nhân).
- **Mức độ hoàn thành tổng thể:** **Hoàn thành có vướng mắc** — đi được trọn luồng cơ bản (`chọn phiên → trả lời câu hỏi → xem kết quả / tổng kết`), nhưng gặp 5 vấn đề về phân cấp thị giác, không gian dọc, hiển thị khối mã Python và nguy cơ bấm nhầm thoát luồng.

| Bước luồng | Kết quả | Điểm dừng / Hiểu nhầm / Quan sát thực tế | Mức ảnh hưởng |
| --- | --- | --- | --- |
| Thiết lập phiên (`S01 → S02`) | Hoàn thành có góp ý | Nhận định cấu hình cố định `4/4` câu hơi ít để luyện chuyên sâu hoặc trải nghiệm nhiều dạng câu hỏi; mong muốn có tùy chọn linh hoạt (`4, 6, 8, 10` câu hoặc chế độ nhanh / đầy đủ). | Thấp (Nằm ngoài phạm vi MVP cố định 4 câu của `P01`) |
| Workspace — Header & Tiến độ (`S03`) | Hoàn thành có vướng mắc | Phần Header & Banner chiếm quá nhiều chiều dọc, đẩy ô nhập câu trả lời và nút **Gửi câu trả lời** xuống quá thấp; người dùng phải cuộn trang mới thấy nút gửi. Thanh tiến độ, nhãn `Câu 1 / 4` và dòng `0 câu đã có kết quả` bị tách thành nhiều tầng rời rạc. | **Cao (P1)** |
| Workspace — Khối mã nguồn (`S03`) | Gặp khó khăn khi đọc đề | Nền khối code Python sáng gần trùng nền card nên không nổi bật. Dòng code dài (ví dụ `def append_audit_event...`) bị tràn ngang / khuất hoặc cắt chữ khi đọc đề. | **Cao (P1)** |
| Workspace — Cụm nút hành động (`S03`) | Nguy cơ thao tác nhầm | Ba nút **Gửi câu trả lời**, **Xem tổng kết phiên** và **Kết thúc sớm** xếp cùng hàng/cùng kích thước tương đương khiến phân cấp thị giác mờ nhạt, dễ bấm nhầm **Kết thúc sớm** hoặc **Xem tổng kết phiên** khi chưa nộp bài. | **Cao (P1)** |
| Điều hướng Navbar khi đang làm bài (`S03`) | Nguy cơ mất tiến trình | Thanh điều hướng trên cùng vẫn hiện đầy đủ liên kết ngoài luồng (**Bắt đầu**, **Thiết lập phiên**); bấm nhầm sẽ rời trang mà không có cảnh báo xác nhận, gây lo ngại mất dữ liệu đang trả lời. | **Cao (P1)** |

### 2.2. Người tham gia `P2` (Rà soát thực tế ngày 25/11/2026)

- **Điều kiện thử nghiệm:** Ứng dụng chạy cục bộ trên nhánh `Demo` (commit `a2ed9c3`) với `EVALUATION_PROVIDER=fixture` (hiển thị huy hiệu **Dữ liệu minh họa**) và SQLite thử nghiệm riêng; thao tác trên trình duyệt ở độ rộng desktop (`1280px`) và màn hình hẹp (`320px`), kèm kiểm tra bàn phím (`Tab` tới *"Chuyển tới nội dung chính"*, `Enter`, `Escape` đóng xác nhận kết thúc sớm và trả focus về nút mở).
- **Mức độ hoàn thành tổng thể:** **Hoàn thành luồng chính, không có lỗi chặn** — đi trọn luồng `bắt đầu → thiết lập → câu 1/4 → nộp bài → xem tiêu chí/căn cứ → bài tập → luyện lại với câu hỏi khác → câu 2/4 → kết thúc sớm → tổng kết → lịch sử → trạng thái lọc không có bài tập khớp`. Ghi nhận 4 vấn đề trải nghiệm tái hiện được (`UI-01`–`UI-04`) và 3 quan sát/giới hạn thiết kế (`UI-05`–`UI-07`).
- **Giới hạn của lượt thử `P2`:** Dùng `fixture` để kiểm tra giao diện (không phải bằng chứng độ chính xác của Antigravity), chưa thử browser end-to-end với Antigravity thật, chưa đo zoom trình duyệt 200% hoặc thử trên Chrome/Edge độc lập.

| Mã quan sát | Mức độ | Bước luồng / Vùng liên quan | Điểm dừng / Hiểu nhầm / Quan sát thực tế |
| --- | --- | --- | --- |
| `UI-01` | **P2 (TB)** | Bài tập (`exercise.js` — `renderRecommendations`) | Khi câu trả lời ngắn ở câu closure Python thiếu 3 tiêu chí cùng ánh xạ về một bài tập, trang hiển thị **3 thẻ bài tập trùng tiêu đề, nguồn, hướng dẫn và nút "Luyện lại với câu hỏi khác"**, chỉ khác phần lý do theo từng tiêu chí; người học dễ hiểu nhầm là 3 bài khác nhau. |
| `UI-02` | **P2 (TB)** | Kết quả câu trả lời (`answer_review.html`) | Sau khi kết thúc phiên sớm (hoặc hoàn tất phiên), mở *"Xem căn cứ và tiêu chí"* từ trang tổng kết rồi bấm *"Về câu hỏi"* sẽ dẫn tới workspace hiển thị *"Không còn câu hỏi đang chờ"*, buộc người học bấm thêm một lần để quay về tổng kết. |
| `UI-03` | **P3 (Thấp)** | Lịch sử & Tổng kết (`welcome.html`, `summary.html`) | Tiêu đề chính hiển thị mã kỹ thuật thô (`Phiên session.practice.73eb...`, `Phiên session.a851...`), thiếu thời điểm tạo hoặc nhãn ngữ cảnh dễ đọc để phân biệt các phiên cùng vai trò. |
| `UI-04` | **P3 (Thấp)** | Bộ lọc bài tập rỗng (`exercise.js`) | Mở `/exercises?skill_id=skill.unknown` hiện thông báo có thuật ngữ nội bộ *"Không có bài tập trong phản hồi API khớp với lựa chọn này"* thay vì ngôn ngữ người học. |
| `UI-05` | Quan sát cần xác nhận | Mở căn cứ từ Tổng kết (`evidence.js`) | Trong trình duyệt thử nghiệm, mở *"Xem căn cứ và tiêu chí"* đôi lúc cuộn xuống giữa trang (`scrollY ~1825px` ở 320px và `~260px` ở desktop) thay vì đầu trang. Đối chiếu mã nguồn cho thấy `renderEvaluation()` tự kích hoạt `firstButton.click()` gây gọi `mark.scrollIntoView(...)` ngay khi vừa tải trang. |
| `UI-06` | Giới hạn thiết kế | Bản nháp workspace (`workspace.html` / `sessionStorage`) | Mở cùng phiên ở tab trình duyệt khác không thấy bản nháp chưa gửi do thiết kế dùng `sessionStorage` theo `docs/api_contract.md` và `docs/ui_direction.md`. Cần nêu rõ phạm vi *"trong tab trình duyệt hiện tại"* ngay cạnh ô nhập. |
| `UI-07` | Chỉ ở `fixture` | Phản hồi minh họa (`fixture_provider.py`) | Khi nhập câu ngắn tự do trong chế độ `fixture`, heuristic có thể chấm `0/6` kèm giải thích tiêu chí không sát câu vừa gõ. Đây là giới hạn của dữ liệu minh họa, không phản ánh Antigravity thật. |

### 2.3. Tổng hợp các lượt người tham gia

| Mã người thử | Ngày thử | Môi trường (`fixture` / `antigravity`) | Trạng thái hoàn thành | Điểm dừng / Hiểu nhầm chính | Ghi chú thất bại / Phục hồi |
| --- | --- | --- | --- | --- | --- |
| `P1` | Đợt 1 Q05 | Cục bộ | Hoàn thành có vướng mắc | Chiều dọc workspace, khối code sáng/cắt dòng, nút hành động thiếu phân cấp, rời trang qua Navbar không cảnh báo (`Q05-01`–`Q05-05`) | Đã sửa `Q05-02`–`Q05-10`, hoãn `Q05-01` sang post-MVP |
| `P2` | 25/11/2026 | `fixture` (1280px & 320px) | Hoàn thành, không lỗi chặn | Trùng thẻ bài tập (`UI-01`), link *"Về câu hỏi"* ở phiên đã đóng (`UI-02`), mã phiên kỹ thuật (`UI-03`), từ *"phản hồi API"* (`UI-04`), tự cuộn trang review (`UI-05`), phạm vi bản nháp theo tab (`UI-06`), heuristic fixture (`UI-07`) | Bàn phím (`Tab`/`Enter`/`Escape`) và không tràn ngang ở 320px đều đạt; đã sửa `UI-01`–`UI-06` và ghi rõ giới hạn `UI-06`/`UI-07` |
| `P3` | *(Chưa thực hiện)* | — | Chưa chạy | — | Tùy chọn bổ sung trước cổng Q08 |

---

## 3. Đối chiếu kiểm tra tĩnh & luồng giao diện hiện tại (Pre-fix UI Audit)

Bên cạnh quan sát thực tế của `P1`, việc rà soát trực tiếp các template và script hiện có tại `source/view/` ghi nhận thêm các điểm gây vướng mắc cho người dùng mới:

| Mã | Màn hình / File | Quan sát cụ thể | Tác động đến luồng chính |
| --- | --- | --- | --- |
| `Q05-06` | `welcome.html` | Phiên kết thúc sớm hiển thị chuỗi enum tiếng Anh `ended_early`; nút **Xem phiên** của phiên đã xong/kết thúc sớm trỏ về `/sessions/{id}` (workspace rỗng) thay vì `/sessions/{id}/summary`. | Người dùng thấy trạng thái khó hiểu và bị buộc thêm bước trung gian khi xem lại phiên cũ. |
| `Q05-07` | `answer_review.html` | Hai nút cùng kiểu `btn--primary` (**Sang câu tiếp theo** và **Xem bài tập theo điểm thiếu**) cạnh tranh trực tiếp; thiếu lối mở thẳng **Xem tổng kết phiên**; nhãn **Sang câu tiếp theo** chưa thống nhất với từ điển `Câu tiếp theo` trong `docs/ui_direction.md`. | Người dùng dễ phân vân giữa tiếp tục phiên hay nhảy sang bài tập giữa chừng; khó quay lại tổng kết khi xem bài cũ. |
| `Q05-08` | `exercise.js` | Khi lọc theo `?skill_id=` hoặc `?exercise_id=` mà không có bài khớp, thông báo bảo *"Hãy xem toàn bộ bài tập của phiên"* nhưng không cung cấp nút/liên kết bấm được; huy hiệu kỹ năng hiển thị mã nội bộ dạng `skill.backend.data_consistency`. | Ngõ cụt nhẹ khi lọc bài tập và lộ mã kỹ thuật thay vì tên kỹ năng tiếng Việt. |
| `Q05-09` | `summary.js` | Thẻ kết quả câu hiển thị mã tiêu chí thô (`confirmed_gap_criterion_ids`) thay vì tên tiêu chí dễ đọc đối chiếu từ `observed_gaps`. | Người dùng mới khó hiểu các mã như `c03.concurrent_tests`. |
| `Q05-10` | `workspace.js`, `evidence.js` | `evidence.js` dùng từ tiếng Anh `"workspace"` trong thông báo người học; `workspace.js` dùng `"Đã lưu trên máy chủ"` lệch nhẹ với chuẩn `"Đã lưu câu trả lời trên máy chủ"` trong `docs/ui_direction.md`. | Thiếu nhất quán ngôn ngữ giao diện tiếng Việt. |

---

## 4. Xếp hạng mức độ ưu tiên và quyết định xử lý trong Q05

| Hạng | Mã vấn đề | Nguồn phát hiện | Tóm tắt vấn đề | Quyết định xử lý |
| --- | --- | --- | --- | --- |
| **1 (P1 — Cao)** | `Q05-04` | Người thử `P1` | Cụm nút **Gửi câu trả lời / Xem tổng kết / Kết thúc sớm** thiếu phân cấp, dễ bấm nhầm | **Sửa ngay trong Q05** (`workspace.html`, `workspace.css`, `components.css`) |
| **2 (P1 — Cao)** | `Q05-05` | Người thử `P1` | Bấm nhầm Navbar (**Bắt đầu / Thiết lập phiên**) lúc đang làm bài không có cảnh báo | **Sửa ngay trong Q05** (`workspace.js`, `workspace.css`) |
| **3 (P1 — Cao)** | `Q05-03` | Người thử `P1` | Khối code Python nền sáng trùng card và cắt/tràn ngang dòng dài | **Sửa ngay trong Q05** (`components.css`) |
| **4 (P1 — Cao)** | `Q05-02` | Người thử `P1` | Header & thanh tiến độ chiếm nhiều chiều dọc, đẩy nút Gửi xuống dưới màn hình | **Sửa ngay trong Q05** (`workspace.html`, `workspace.css`) |
| **5 (P1 — Cao)** | `Q05-06` | Rà soát UI | Lịch sử phiên lộ `ended_early` tiếng Anh và dẫn vào workspace rỗng | **Sửa ngay trong Q05** (`welcome.html`) |
| **6 (P1 — Cao)** | `Q05-07` | Rà soát UI | Trang kết quả có hai nút chính cạnh tranh và thiếu đường về tổng kết | **Sửa ngay trong Q05** (`answer_review.html`) |
| **7 (P2 — Trung bình)** | `Q05-08` | Rà soát UI | Trạng thái lọc rỗng trang bài tập thiếu nút xem toàn bộ; lộ `skill.*` raw ID | **Sửa ngay trong Q05** (`exercise.js`) |
| **8 (P2 — Trung bình)** | `Q05-09`, `Q05-10` | Rà soát UI | Lộ mã tiêu chí thô ở tổng kết; nhãn tiếng Anh/chưa đồng nhất ở `workspace.js`/`evidence.js` | **Sửa ngay trong Q05** (`summary.js`, `workspace.js`, `evidence.js`) |
| **9 (P2 — Trung bình)** | `Q05-11` (`UI-01`) | Người thử `P2` | Một bài tập hiển thị thành nhiều thẻ lặp khi nhiều tiêu chí cùng trỏ về một bài | **Sửa ngay trong Q05** (`exercise.js`, `exercise.css`) — gom theo `(exercise_id, version)` giữ thứ tự tiên quyết, hiển thị đủ danh sách lý do và tránh lặp nút luyện lại |
| **10 (P2 — Trung bình)** | `Q05-12` (`UI-02`) | Người thử `P2` | Liên kết *"Về câu hỏi"* ở trang kết quả dẫn vào workspace rỗng khi phiên đã kết thúc/hoàn tất | **Sửa ngay trong Q05** (`answer_review.html`) — đổi thành *"Về tổng kết"* khi phiên không còn `in_progress` |
| **11 (P2 — Trung bình)** | `Q05-15` (`UI-05`) | Người thử `P2` | Mở trang kết quả đôi lúc tự cuộn xuống giữa trang do auto-click tiêu chí đầu gọi `scrollIntoView` | **Sửa ngay trong Q05** (`evidence.js`) — chỉ cuộn tới `<mark>` khi người học chủ động chọn tiêu chí; ghi chú cần xác nhận thêm trên Chrome/Edge |
| **12 (P3 — Thấp)** | `Q05-13` (`UI-03`) | Người thử `P2` | Lịch sử và tổng kết lấy mã phiên kỹ thuật làm nhãn chính | **Sửa ngay trong Q05** (`interview_controller.py`, `pages.py`, `welcome.html`, `summary.html`) — dùng nhãn loại phiên + thứ tự/thời điểm tạo, đẩy mã tham chiếu xuống phụ |
| **13 (P3 — Thấp)** | `Q05-14` (`UI-04`) | Người thử `P2` | Thông báo lọc bài tập rỗng lộ cụm *"phản hồi API"* | **Sửa ngay trong Q05** (`exercise.js`, `summary.js`) — chuẩn hóa sang tiếng Việt tự nhiên cho người học |
| **14 (Thiết kế MVP)** | `Q05-16` (`UI-06`) | Người thử `P2` | Bản nháp `sessionStorage` chỉ tồn tại trong tab hiện tại | **Giữ thiết kế `sessionStorage` theo P04/P06 và ghi chú rõ cạnh ô nhập** (`workspace.html`) |
| **15 (Chỉ ở `fixture`)** | `Q05-17` (`UI-07`) | Người thử `P2` | Heuristic chế độ `fixture` có thể trả giải thích không sát câu ngắn tự do | **Không đổi provider/scoring trong Q05; ghi rõ giới hạn fixture** (dùng câu trả lời tổng hợp chuẩn trong `docs/demo_script.md` khi demo offline) |
| **16 (Hoãn — Post-MVP)** | `Q05-01` | Người thử `P1` | Cho phép tùy chỉnh số lượng câu hỏi (4, 6, 8, 10 câu) khi thiết lập phiên | **Ghi nhận backlog sau MVP** (Phạm vi `P01` chốt cố định 4 câu/4 nhóm với 8 câu seed; cần mở rộng ngân hàng câu hỏi ở `X01` và cập nhật hợp đồng `P01`/`P04`/`C01` trước khi triển khai). |

Chi tiết từng task sửa, bước tái hiện và bằng chứng kiểm tra được theo dõi tại [usability_check.md](usability_check.md).