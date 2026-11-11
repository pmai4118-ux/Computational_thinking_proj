# P02 — Use case và hành vi nút theo bộ UI ZIP

Cập nhật 10/11/2026 theo yêu cầu mới nhất. Đây là **yêu cầu thiết kế**, chưa phải tính năng đã triển khai. Tài liệu này làm rõ sáu khu vực; các modal, chi tiết câu, kết quả và lịch sử là màn hình con trong khu vực, không mở thêm phạm vi sản phẩm tùy ý.

## 1. Căn cứ và quyết định

Nguồn UI là `D:/stitch_ct_nh_m_5.zip`, bản nhập giữ nguyên trong [design/demo-web](../design/demo-web/IMPORT_README.md). Đã đọc HTML của 22 màn hình và xem ảnh workspace 70/30, auth 40/60, bài đầu vào ba phần và lộ trình. Những mô tả nghiệp vụ dưới đây là thiết kế bổ sung từ UI; nút HTML tĩnh không chứng minh backend đã hoạt động.

| Nội dung | Quyết định hiện hành |
| --- | --- |
| Đầu vào tự luận | Gõ văn bản **hoặc** ghi âm → phiên âm → xem/sửa → xác nhận đưa vào bản nháp → gửi bài. Người dùng đã chọn phương án này. |
| Bài kiểm tra đầu vào | Có **trắc nghiệm, tự luận và tình huống** như UI ZIP. Người dùng đã xác nhận; thay yêu cầu cũ “chỉ tự luận” cho bài đầu vào. |
| Khung chat | Tách khỏi ô bài làm. Gửi chat không nộp bài, không chuyển câu, không tự thêm nội dung AI vào bài. |
| Chấm bài | Chỉ chấm văn bản đã nộp hoặc lựa chọn trắc nghiệm. Không chấm âm sắc, cảm xúc, độ tự tin, giọng địa phương hay tiếng ồn. |
| Phiên phỏng vấn | Giữ bốn nhóm tự luận; không lấy số câu 5/7, cấp Senior hoặc điểm minh họa trên ảnh làm cấu hình thật. |
| Auth | Thiết kế Google và email/mật khẩu theo hai màn hình auth. Khách vẫn luyện thử một câu; không thêm SSO trường/GitHub, giảm giá hoặc CV vào đợt này. |
| Phạm vi thay đổi | Chỉ P02 (luồng/use case) và P06 (thiết kế/wireframe). Không sửa task khác, hợp đồng API/data, spec hoặc backend; không commit. |

## 2. Mapping từ UI đến sáu khu vực

Các tên thư mục sau đều nằm dưới `design/demo-web/`; mỗi thư mục có `code.html` và `screen.png`.

| Khu vực | Màn hình tham chiếu chính | Giữ / điều chỉnh |
| --- | --- | --- |
| Câu hỏi luyện tập | `question-library`, `question-detail`, `guided-practice` | Giữ tìm/lọc, đề chi tiết, khối luận điểm, lưu nháp, giọng nói và chat. Bỏ toolbar Code Snippet; vẫn giải thích thuật toán bằng lời. |
| Phiên phỏng vấn | `interview-setup`, `interview-workspace-structured`, biến thể `interview-workspace`, `interview-report` | Dùng workspace chính 70% bài làm / 30% chat trên desktop; không phát triển hai biến thể thành hai sản phẩm. Đổi “giữ mic” thành bắt đầu/dừng rõ ràng. |
| Lộ trình cá nhân hóa | `learning-roadmap`, `assessment-result` | Giữ kết quả nền, chặng, mục học, prerequisite và CTA luyện. Ngưỡng 70/80, phần trăm năng lực trên ảnh chỉ là minh họa. |
| Tổng quan | `dashboard`, `history` | Giữ việc hôm nay, tiếp tục, lịch và bài cũ. Đổi “Nghe lại audio & sửa” thành “Xem transcript & luyện lại” vì không lưu audio lâu dài. |
| Đăng nhập | `auth-google`, `auth-standard` | Lấy layout 40/60 và Google + email/mật khẩu, tạo tài khoản, quên mật khẩu, khách. Bỏ discount, SSO giả và lời hứa mã hóa đầu cuối chưa có căn cứ. |
| Bài kiểm tra đầu vào | `entry-assessment`, `incomplete-submission-dialog`, màn hình kết quả đầu vào | Giữ ba phần và bảng điều hướng; không khóa tình huống chỉ vì chưa làm phần trước. Cho rà câu trống và xác nhận nộp thiếu. |

Home chỉ là điểm vào; settings, notifications, lịch rảnh, mascot/XP trong 22 ảnh không tự trở thành trang mới hoặc task mới. Nguồn/công ty/số người dùng chỉ hiển thị khi có bằng chứng thật. Không hứa “đạt chuẩn tuyển dụng”.

## 3. Quy tắc chung: ba luồng độc lập

| Luồng | Bắt đầu bởi | Tạo/cập nhật gì | Tuyệt đối không làm |
| --- | --- | --- | --- |
| Soạn và nộp bài | Nhập, chèn transcript, Lưu nháp, Nộp bài | Draft có revision; khi nộp tạo Answer/AssessmentSubmission bất biến | Không dùng chat hoặc transcript chưa xác nhận để tự nộp |
| Trợ lý chat | Nút gửi trong khung chat / chip gợi ý | ChatMessage gắn đúng câu, intent và lượt yêu cầu | Không ghi đè draft, tạo Answer, chuyển câu hay tự chấm điểm |
| Ghi âm | Chọn Ghi âm rồi bấm Bắt đầu | Recording tạm và TranscriptionJob, sau xác nhận mới cập nhật draft | Không tự xin mic khi mở trang, không tự gửi bài, không phát audio AI |

Trạng thái nháp và bài nộp phải khác nhãn. Auto-save nháp không có nghĩa là đã nộp. Mọi thao tác lưu/nộp dùng ID chống trùng; retry cùng nội dung trả bản đã có, cùng ID với nội dung khác báo conflict. Khi kết quả lưu chưa rõ, đối soát trước khi sửa hoặc gửi snapshot khác.

## 4. UC-Q — Câu hỏi luyện tập

**Mục tiêu:** hoàn thành một câu và hiểu phần cần củng cố. **Tác nhân:** khách hoặc người có tài khoản. **Tiền điều kiện:** có câu đã review; nếu không có phải hiển thị trống. **Kết quả:** bài và kết quả gắn đúng phiên bản; bộ lọc không mất khi quay lại.

Luồng: mở thư viện → tìm/lọc → chi tiết → xác nhận vai trò/cấp độ/chủ đề → chọn nhập văn bản hoặc ghi âm → soạn bài, hỏi trợ lý nếu cần → lưu và nộp → xem tiêu chí/căn cứ → chọn luyện lại hoặc quay thư viện.

| Nút / thao tác trong UI | Hành vi và logic | Lỗi / trạng thái cần có |
| --- | --- | --- |
| Tìm kiếm / Enter | Gửi từ khóa cùng bộ lọc; reset trang về đầu, giữ query khi mở chi tiết | Không có kết quả → Xóa lọc; lỗi tải → giữ kết quả đang có |
| Chip chủ đề, cấp độ, loại, nguồn | Chỉ đổi tiêu chí truy vấn; hiển thị tập đang chọn | Junior ngoài target hiện tại bị ẩn; “công ty xác minh” cần chứng cứ riêng |
| Sắp xếp, Trang trước/sau, số trang | Đổi thứ tự/trang trên cùng bộ lọc; chặn trang không tồn tại | Chỉ cho sắp theo trường có dữ liệu; không xếp “phổ biến” bằng số giả |
| Luyện câu này / Bắt đầu làm bài | Mở chi tiết rồi xác nhận mục tiêu; khóa question/rubric version sau xác nhận | Có nháp → Tiếp tục hoặc xác nhận tạo lượt mới; chưa đủ nội dung → không tạo lượt rỗng |
| Lưu vào ôn tập | Đánh dấu bookmark của owner, không tính đã học | Khách được lưu theo owner trình duyệt; không giả đồng bộ tài khoản |
| Quay lại thư viện | Trở đúng filter/scroll; nếu có nháp chưa lưu phải xác nhận rời | Lưu lỗi thì giữ trang và nội dung, cho hủy rời |
| Xem nguồn / tiêu chuẩn chấm | Mở panel nguồn và tên tiêu chí công khai | Không lộ đáp án/expected evidence trước nộp |
| Thêm khung luận điểm / di chuyển / xóa | Sửa các block có ID ổn định; xóa block có nội dung cần xác nhận/hoàn tác | Lưu thứ tự; không gán điểm theo số block, không tự điền đáp án mẫu |
| B / I / danh sách / công thức | Định dạng trình bày hoặc chèn ký hiệu toán; lưu văn bản chuẩn hóa theo hợp đồng | Không có code editor, chạy code hoặc toolbar sinh code |
| Lưu bản nháp | Lưu đúng snapshot và draft revision, giữ trạng thái “chưa nộp” | Conflict giữa tab → đối soát/chọn bản, không last-write-wins âm thầm |
| Nộp bài & nhận phản hồi | Chặn rỗng, đang ghi âm/phiên âm hoặc chưa xử lý transcript; lưu Answer trước đánh giá | Lưu lỗi giữ nháp; AI lỗi giữ Answer; thiếu evidence giữ null, không gán 0 |
| Xem bằng chứng / Luyện lại / Luyện liên quan | Mở đúng quote; lượt mới giữ bài cũ và lý do chọn câu | Không có câu phù hợp → nêu rõ và quay thư viện |

## 5. UC-I — Phiên phỏng vấn

**Mục tiêu:** hoàn thành phiên bốn câu đủ bốn nhóm. **Tiền điều kiện:** role/level/topic rõ, đủ câu được review, owner hợp lệ. **Kết quả:** tổng kết ghi đủ/thiếu câu và tình trạng đánh giá, không suy ra xác suất đậu phỏng vấn.

| Nút / thao tác | Hành vi và logic | Lỗi / trạng thái cần có |
| --- | --- | --- |
| Có hướng dẫn / Mô phỏng | Khóa `mode` vào phiên sau xác nhận. Guided có hỏi rõ và gợi ý; Simulation chỉ hỏi rõ đề, không hint | Không đổi mode giữa phiên; muốn đổi phải tạo phiên khác |
| Chỉnh sửa nâng cao | Mở form vai trò Backend, Intern/Fresher, chủ đề; chọn input mặc định và thời gian nếu bộ đề có cấu hình | Không lấy Frontend/Senior hoặc 3/5/7 câu của mockup làm phạm vi đã chốt |
| Bắt đầu thiết lập / Quay lại chỉnh sửa | Hiện bản tóm tắt để làm rõ, kiểm tra coverage và quyền | Chưa tạo phiên chỉ vì chọn radio hoặc mở modal |
| Bắt đầu ngay | Tạo phiên idempotent, snapshot câu/rubric, mode và deadline nếu có | Thiếu câu → giữ form và nêu nhóm thiếu, không giảm coverage |
| Tiếp tục phiên | Đọc phiên cũ và khôi phục đúng câu, nháp, trạng thái nộp | Hết quyền → không lộ bài; không resume thành lượt mới |
| Văn bản / Ghi âm | Đổi phương thức nhập, không đổi mode Guided/Simulation; dùng UC-V | Không xóa nội dung đã gõ hoặc trợ giúp đã nhận |
| Gửi ở khung chat | Chỉ hỏi rõ/gợi ý theo mode; dùng UC-C | Không gửi câu trả lời đi chấm |
| Câu trước | Xem bài cũ; simulation đã nộp chỉ đọc. Bài chưa nộp được giữ nháp trước chuyển | Không sửa Answer đã nộp trong cùng phiên |
| Nộp câu trả lời | Tạo bài bất biến trước khi xử lý AI. Guided mở kết quả từng câu; Simulation chỉ báo đã nhận bài | Backend cũng chặn đọc điểm simulation trước kết thúc, không chỉ ẩn UI |
| Câu tiếp | Chỉ chuyển khi xác nhận lưu bài hiện tại; không chọn câu theo điểm, không bỏ nhóm | Khóa double click; đánh giá đang pending không làm mất bài |
| Lưu & thoát | Nếu đang ghi âm, yêu cầu Dừng và xử lý transcript hoặc Hủy bản ghi; lưu nháp rồi thoát khi xác nhận | Nếu lưu thất bại, cho giữ trang hoặc rời có xác nhận mất phần chưa lưu |
| Kết thúc sớm / Hủy phiên | Modal nêu số bài đã nộp/câu còn thiếu. Hủy modal giữ nguyên phiên; xác nhận kết thúc giữ bài đã có | Phiên kết thúc không nhận nộp mới. Câu chưa làm là unanswered, không thành điểm 0 |
| Hết thời gian, nếu bật timer | Deadline do server xác định; đóng quyền sửa/nộp mới, dừng mic; giữ snapshot chưa nộp riêng và tổng kết phần đã xác nhận | Không auto-submit nháp/transcript chưa duyệt. Retry cùng bài gửi trước deadline chỉ đối soát trạng thái |
| Xem phân tích / Luyện lại phiên / Tải PDF | Đọc từng bài/căn cứ; luyện lại tạo phiên mới; PDF chứa đúng kết quả được phép xem | Kết quả chưa xong có nhãn; chưa có export thì ẩn nút, không tải file giả |

## 6. UC-V — Nhập bằng ghi âm, dùng chung

Áp dụng cho luyện câu, phiên phỏng vấn và các câu tự luận/tình huống ở đầu vào. Trắc nghiệm không cần ghi âm. Đây là **Speech to Text**, không phải hội thoại audio hai chiều.

| Trạng thái / nút | Điều kiện và tác động | Khi không thành công |
| --- | --- | --- |
| Chọn Văn bản | Hiện editor/khối luận điểm; giữ nguyên nháp | Nếu đang thu phải Dừng hoặc Hủy trước, không chuyển âm thầm |
| Chọn Ghi âm | Hiện hướng dẫn, nơi chèn transcript và thông tin xử lý audio; chưa bật mic | Trình duyệt không hỗ trợ → hướng dẫn dùng văn bản |
| Bắt đầu ghi âm | Xin quyền mic theo thao tác người dùng; sau chấp thuận mới thu và hiện timer/trạng thái | Từ chối quyền/không có mic → giữ nháp, cho nhập văn bản hoặc thử lại |
| Dừng ghi âm | Dừng track mic, đóng bản ghi, cho Nghe thử / Thu lại / Chuyển thành văn bản | Không có tiếng/không có dữ liệu → thu lại hoặc văn bản; không tự đánh giá |
| Nghe thử / Thu lại / Hủy | Nghe audio trong tab; thu lại/hủy cần xác nhận nếu sắp mất bản chưa dùng | Không bật mic lại tự động. Hủy không xóa nháp văn bản trước đó |
| Chuyển thành văn bản | Tạo transcription job chống trùng, khóa thay bản ghi đó khi đang xử lý; UI ghi “đang phiên âm” | Timeout/quota/nhận dạng lỗi → giữ audio tạm trong tab để retry, hoặc chuyển văn bản |
| Sửa transcript | Người học chỉnh phần thuật ngữ sai; transcript preview tách khỏi bài làm | Không khẳng định transcript tạm là lời người học đã xác nhận |
| Dùng transcript | Chọn chèn vào block đang chọn/thêm block mới hoặc thay block có xác nhận; ghi nhận bản đã sửa | Draft thay đổi trong lúc phiên âm → hỏi lại nơi chèn; không ghi đè bản mới |
| Nộp bài | Chỉ gửi văn bản canonical đã được người học xác nhận; chuyển sang luồng nộp bình thường | Không cho nộp khi còn recording/transcribing hoặc transcript chưa chọn Dùng/Hủy |

FSM: `idle → permission_request → recording → recorded → transcribing → transcript_review → inserted`. Nhánh `denied`, `failed`, `cancelled` đều cho quay về nhập văn bản; retry hữu hạn theo cấu hình. Đổi câu/rời trang lúc recording phải hỏi; khi rời luôn tắt mọi mic track.

Thiết kế mặc định: audio chỉ dùng xử lý tạm, không có kho ghi âm hoặc nút nghe lại lâu dài trong lịch sử. Bản ghi trong tab bị giải phóng khi xác nhận transcript, hủy hoặc rời; bản tạm phía server có TTL tối đa một giờ và có job dọn, kể cả phiên âm lỗi. Giới hạn ban đầu đề xuất 120 giây/10 MB mỗi bản ghi, transcript 20.000 ký tự; kiểm tra trước upload và ở server, giá trị cần khảo sát provider rồi version hóa. Không log audio, transcript đầy đủ, token hoặc mật khẩu.

## 7. UC-C — Chat trợ lý, tách khỏi bài nộp

UI desktop 70/30: trái là đề và bài làm, phải là chat. Mobile dùng tab Bài làm / Trợ lý, badge tin chưa đọc; đổi tab giữ nháp và không tự mở mic.

| Nút / chế độ | Logic cần thực hiện |
| --- | --- |
| Gửi chat / Enter; Shift+Enter xuống dòng | Chặn rỗng/quá giới hạn; lưu message người dùng với request ID, intent và context câu. Hiện pending; một request đang chạy trên cùng thread |
| Hỏi rõ đề | Giải thích thuật ngữ, phạm vi và ràng buộc từ đề đã review; không tiết lộ đáp án, rubric nội bộ hoặc điểm |
| Xin gợi ý (chỉ Guided/luyện câu) | Gợi ý theo mức từ nội dung được review, người dùng chủ động bấm; ghi mức trợ giúp. Không tự trừ điểm khi chưa có quy tắc công bố |
| Simulation | Cho clarification; từ chối yêu cầu giải hộ/gợi ý trước kết thúc. Client không được tự chuyển intent để vượt quyền |
| Đầu vào đang làm | Chỉ có hướng dẫn thao tác hoặc làm rõ đề trung tính; không có hint nội dung, xem nháp để sửa hay đánh giá trước nộp |
| Phản hồi sau nộp | Chỉ bàn về kết quả đã xác thực và đúng answer revision; không sửa điểm hoặc bản nộp từ chat |
| Chip câu hỏi gợi ý | Điền vào ô chat để người dùng xác nhận gửi; không gửi ngầm và không chèn đáp án vào bài |
| “Kiểm tra lỗi logic trong bài của tôi” | Guided: chỉ chạy sau khi người dùng chọn chia sẻ snapshot nháp, trả câu hỏi gợi mở có giới hạn; Simulation/đầu vào: không cho trước nộp |
| Thử lại chat lỗi | Reuse request ID, không nhân đôi message hoặc tính hai lượt trợ giúp; không retry vô hạn, không khóa nút lưu bài |

Ngữ cảnh trợ lý gồm đề đúng version, mode, intent, thread đúng câu, và snapshot draft chỉ khi đã chủ động chia sẻ. Khi đổi câu mở đúng thread mới; tin đến muộn không chèn nhầm vào câu khác. Message/answer là dữ liệu không tin cậy; nội dung “ignore instructions” được giữ như dữ liệu, không trở thành lệnh hệ thống. Chat không phải nguồn evidence để chấm bài; nội dung AI không tính là lời người học. Có thể xin gợi ý tối đa theo config đã duyệt; hết lượt vẫn được làm/nộp bài.

## 8. UC-L — Lộ trình cá nhân hóa

**Tiền điều kiện:** tài khoản hoặc owner có kết quả đầu vào phù hợp. **Luồng:** xem phần nền → làm kiểm tra nếu chưa có → đọc kết quả và coverage → xem kế hoạch đề xuất → kích hoạt → chọn chặng/mục → học nguồn → kiểm tra mục → cập nhật phần đã xác minh.

| Nút / thao tác | Hành vi và logic | Nhánh cần xử lý |
| --- | --- | --- |
| Kiểm tra kiến thức nền / Kiểm tra lại | Mở bài đầu vào, xác nhận mục tiêu; giữ kết quả/kế hoạch cũ tới khi kích hoạt bản mới | Có lượt dở → Tiếp tục/Tạo lượt mới có xác nhận |
| Xem chi tiết đánh giá / Xem bài tự luận đã nộp | Mở đúng assessment hoặc answer revision và evidence | Chưa có kết quả → hướng dẫn kiểm tra, không dựng phần trăm |
| Tùy chỉnh lộ trình | Thay mục tiêu/ngân sách, xem lý do và phần không khả thi trong bản preview | Chưa lưu thì Hủy giữ kế hoạch cũ; prerequisite thiếu/chu trình phải báo |
| Kích hoạt lộ trình | Tạo/đổi `active_plan_ref` sau xác nhận; lưu assessment refs và config version | Retry không tạo nhiều plan; lỗi giữ bản đang dùng |
| Chọn chặng / node | Đổi vùng xem, giữ vị trí; giải thích thứ tự từ prerequisite | Không khóa bằng XP; node chỉ đọc khi chưa đủ điều kiện đã công bố |
| Luyện bài tự luận ngay / Bắt đầu bài 1 | Mở lượt gắn skill/module và câu đã review; chọn Văn bản/Ghi âm như UC-V | Không có câu phù hợp → nêu rõ, cho học nguồn hoặc về danh sách |
| Mở tài liệu / Xem rubric | Mở nguồn có attribution, tiêu chí công khai; giữ nháp khi quay lại | Nguồn lỗi → dùng nguồn thay thế đã review; không sinh link giả |
| Hoàn tất mục / Kiểm tra mục | Tự báo cáo chỉ là self_reported; verified phải dựa trên bài kiểm tra và config ngưỡng | Chưa đủ căn cứ khác chưa đạt; lỗi AI chỉ failed. Không tự ấn định 70/80 theo mockup |

Thuật toán: xác nhận gap → lấy học liệu/câu đã review → đóng tập tiên quyết → phát hiện node thiếu/chu trình → topo sort có thứ tự ổn định → kiểm tra ngân sách → preview có lý do → kích hoạt. Không dùng LLM tự tạo thứ tự hoặc thời lượng. Chưa đủ dữ liệu chỉ lập phần có căn cứ và nêu phần cần bổ sung.

## 9. UC-D — Tổng quan và lịch sử

| Nút / thao tác | Hành vi và logic | Nhánh cần xử lý |
| --- | --- | --- |
| Luyện ngay / Tiếp tục phiên / Xem bài | Đi đúng question/session/assessment còn quyền; chỉ thao tác người học đã lưu mới tạo hoạt động | Phiên hết hạn/đã kết thúc → xem lại hoặc tạo lượt mới, không tự resume |
| Xem tất cả bài nộp / Xem chi tiết | Lọc, phân trang, đọc bài/kết quả; giữ trạng thái query khi Back | Pending/failed/partial/unknown có nhãn riêng; chỉ mở ID không cấp quyền |
| Cuộn trước/sau | Chỉ cuộn rail, không thay đổi dữ liệu hoặc cộng lượt học | Chặn nút khi đã ở đầu/cuối |
| Xem transcript & luyện lại | Mở văn bản đã xác nhận của bài nguồn voice; sửa bằng lượt mới | Không hứa nghe audio đã xóa; không sửa bài cũ |
| Viết lại câu này | Tạo lượt/revision mới theo policy sau xác nhận, liên kết bài nguồn | Không ghi đè Answer/Evaluation cũ |
| Xem bằng chứng | Chọn tiêu chí mở đúng quote trong bài gốc | Evidence không hợp lệ → báo thiếu căn cứ, không lấy draft thay thế |
| Tháng trước/sau, chọn ngày | Đổi lịch và xem hoạt động thật theo timezone cấu hình | Ngày tương lai không có nút điểm danh; tháng trống không dựng hoạt động |
| Điểm danh hôm nay | Lưu duy nhất một attendance event/owner/ngày; retry idempotent | Điểm danh khác đã học; không tự thưởng XP vì mở trang |

Tổng quan chỉ tổng hợp dữ liệu đã xác nhận, không tính lại điểm trong UI. Nếu giữ XP từ ảnh: tách ledger hoạt động khỏi rubric, chưa cộng thưởng khi chưa có config duyệt; đây không phải task bắt buộc trong lần đặc tả sáu trang.

## 10. UC-A — Đăng nhập, tạo tài khoản và khách

Luồng: mở auth và giữ return target → chọn Google hoặc email → xác thực → tạo hồ sơ tối thiểu nếu lần đầu → quay đúng đích. Nếu không có đích thì về Tổng quan. Không yêu cầu đăng nhập trước khi người học xem thư viện công khai.

| Nút / thao tác | Logic | Lỗi / giới hạn |
| --- | --- | --- |
| Tab Đăng nhập / Tạo tài khoản | Đổi form, không gửi request; giữ email nhưng không lưu mật khẩu vào storage | Không xin CV, năm tốt nghiệp hoặc tài khoản trường để bắt đầu |
| Tiếp tục bằng Google | Bắt đầu xác thực, bind state/nonce/return target và kiểm tra callback phía server; khóa bấm trùng | Hủy/từ chối/timeout → vẫn chưa đăng nhập, giữ đích; không lấy email callback chưa xác minh làm owner |
| Đăng nhập ngay | Validate form, xác thực credential phía server; trả cookie phiên, rotate session | Sai thông tin dùng thông báo chung, rate limit; không log mật khẩu |
| Tạo tài khoản | Validate tên/email/mật khẩu và chấp thuận điều khoản; tạo tài khoản ở trạng thái xác minh, gửi link xác minh qua service khi triển khai | Email đã tồn tại không lộ dữ liệu riêng; token xác minh có hạn, dùng một lần |
| Quên mật khẩu / Gửi lại link | Luồng yêu cầu reset với phản hồi trung tính, link hết hạn/dùng một lần, giới hạn tần suất | Không tự đăng nhập chỉ vì mở link reset; reset thành công yêu cầu đăng nhập lại |
| Hiện/ẩn mật khẩu | Đổi cách hiển thị tại client, không gọi server hoặc thay giá trị | Không copy/log mật khẩu |
| Ghi nhớ phiên | Chọn thời hạn cookie theo config đã công bố; không lưu credential trong localStorage | Thời hạn cụ thể cần chốt; hết phiên giữ nháp không nhạy cảm được phép |
| Trải nghiệm ẩn danh | Tạo/reuse owner khách bằng cookie, mở luyện một câu | Cần giải thích lịch sử khách không tự đồng bộ nhiều thiết bị |
| Đăng nhập khi có bài khách | Hỏi có liên kết các bài thuộc đúng owner khách hiện tại hay không; chỉ liên kết sau xác nhận | Không tự gộp theo email; chuyển tài khoản không mở bài của người trước |
| Đăng xuất / Đăng nhập lại | Xác nhận xử lý nháp, hủy phiên server và xóa cache riêng theo owner, tắt mic | Không xóa bài đã lưu; tài khoản mới không kế thừa draft cũ |

Nút trường `.edu.vn`, GitHub và dòng giảm giá trong ảnh được ẩn cho tới khi có nghiệp vụ thật. Điều kiện mật khẩu, session TTL, email delivery và provider Google cần được RQ01 cấu hình/kiểm thử; không coi nhãn “E2EE” trên ảnh là cam kết bảo mật đã có.

## 11. UC-B — Bài kiểm tra đầu vào ba phần

**Mục tiêu:** đánh giá kiến thức trong phạm vi bộ đề, làm căn cứ lập kế hoạch. **Tiền điều kiện:** mục tiêu rõ và có blueprint đã review. Số câu/thời lượng/trọng số lấy theo assessment version; số 5+3+1 và 38:39 trong ảnh không phải cấu hình đã chốt.

| Nút / thao tác | Hành vi và logic | Nhánh cần xử lý |
| --- | --- | --- |
| Bắt đầu / Tiếp tục bài | Xác nhận mục tiêu, số câu, ba phần, thời gian nếu có và nguyên tắc không gợi ý nội dung | Còn lượt dở → chọn tiếp tục hoặc tạo lượt mới có xác nhận |
| Tab phần / số câu / Câu trước | Chuyển tới câu trong bộ đề; lưu nháp và giữ phương thức nhập riêng từng câu | Không khóa phần tình huống theo tiến độ giả; chưa lưu thì hiện nhãn pending |
| Chọn đáp án trắc nghiệm | Câu mặc định single-choice; đổi được trước nộp, lưu option ID cùng question version | Chưa chọn là unanswered, không thành đáp án sai; không trả đáp án đúng trước nộp |
| Thêm khung luận điểm | Soạn câu tự luận hoặc tình huống theo blocks; voice như UC-V | Không yêu cầu viết code; trường hợp thực tế chấm nguyên nhân/giải pháp/đánh đổi bằng lời |
| Chat trợ lý | Chỉ hướng dẫn thao tác và clarification trung tính theo UC-C | Không xin hint, sửa logic draft, xem đáp án hoặc nhận điểm trong lúc kiểm tra |
| Lưu tạm bản nháp | Lưu revision các lựa chọn và văn bản, giữ nhãn chưa nộp | Không gọi AI/scoring hoặc cập nhật năng lực |
| Lưu & sang câu tiếp | Xác nhận lưu nháp rồi chuyển câu; không phải nộp cuối kỳ | Lưu lỗi → giữ câu, cho thử lại đúng snapshot |
| Nộp bài kiểm tra | Mở màn rà soát tổng số câu đã/ chưa trả lời; xử lý transcript còn chờ trước | Nếu còn ghi âm/phiên âm phải Dừng và Dùng/Hủy transcript; không auto-submit |
| Làm câu này / Tiếp tục viết | Đóng modal về đúng câu chưa xong, giữ mọi dữ liệu | Không reset timer hoặc tạo attempt mới |
| Tôi hiểu, vẫn muốn nộp | Xác nhận nộp phần đã có; server khóa snapshot của mọi response và tạo submission idempotent | Ghi submitted_partial và coverage; câu bỏ trống là unanswered, không tính 0 |
| Xác nhận nộp đủ | Tạo snapshot cuối, khóa chỉnh sửa, chấm trắc nghiệm theo đáp án version và tự luận/case theo evidence/rubric | Lưu thất bại giữ draft; đánh giá lỗi giữ snapshot, retry từng bài lỗi |
| Xem lại bài & đáp án đối chiếu | Sau nộp, xem đúng phiên bản lựa chọn, key/rationale công khai và tiêu chí/quote | Không mở key trong attempt đang làm; không trộn điểm các thang tùy ý |
| Kích hoạt / Tùy chỉnh lộ trình | Chỉ dùng kết quả đã xác nhận, phần thiếu hiển thị rõ; chuyển UC-L | Thiếu dữ liệu → đề nghị bổ sung, không tự gán nhãn năng lực toàn diện |

Trắc nghiệm: đúng theo key được review thì điểm theo item config, sai thì 0; không có điểm âm mặc định. Self-report/đoán không thành verified. Chỉ hiển thị tổng chuẩn hóa khi mọi item bắt buộc được trả lời và đánh giá có căn cứ; nộp thiếu hoặc item lỗi giữ tổng null, vẫn hiển thị điểm từng mục đủ căn cứ, completion và coverage riêng. Không renormalize phần đã làm thành “điểm tổng” để tạo kết quả cao giả. Làm lại tạo attempt mới, giữ kết quả cũ.

## 12. Bàn giao P02 / P06

- P02: đường vào, hành động/đích, Back/Close, nhánh lỗi và dữ liệu cần giữ được mô tả cho sáu khu vực.
- P06: một file demo.html có các khu vực nối bằng tab/nút, modal, nháp và các kịch bản ghi âm, chat, đăng nhập và kết quả mẫu. Quy chuẩn và ảnh nguồn nằm trong tài liệu bàn giao.
- Mọi chi tiết triển khai như API, model, auth thật, STT, scoring, retention và thuật toán kế hoạch chỉ là đầu vào để owner task tương ứng quyết định sau; không được xem là đã triển khai hoặc tự thay scope sprint.
- Các thông số 120 giây/10 MB/TTL một giờ hoặc policy nộp thiếu trong phần mô tả là đề xuất thiết kế cần review, không sửa PROJECT_SPEC hay tạo task mới trong P02/P06.
- Đầu vào ba phần và STT có xác nhận là quyết định UI đã được người dùng chọn trong chat; chưa có lời hứa backend hiện tại hỗ trợ.

Mở [sơ đồ P02](../p02-user-flow.html) để xem luồng tương tác theo khu vực. Bản demo P06 nằm tại [demo.html](../demo.html).
