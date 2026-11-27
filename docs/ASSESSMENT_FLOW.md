# Luồng phỏng vấn, chọn câu hỏi và báo cáo ba phần

## Chế độ của ứng dụng

Phiên mở từ `/setup` dùng `evaluation_timing=after_session`: lưu từng câu trả lời
nguyên văn, chuyển câu khi đã lưu, chấm bằng provider được cấu hình sau khi
phiên hoàn tất hoặc kết thúc sớm. Trang tổng kết gọi tối đa hai lượt đánh giá
đồng thời, đọc lại trạng thái đã lưu và hiển thị số câu đã chấm trên số câu đã
gửi. Nếu trang đóng giữa chừng, câu trả lời và kết quả đã hoàn tất còn trong
SQLite; mở lại tổng kết để tiếp tục các câu còn `pending`. Lượt `failed` không
tự thử lại vô hạn: người dùng chọn thử lại từ đúng bản đã lưu. Lượt đã hoàn tất
được dùng lại, không gọi AI lần nữa. Provider thật vẫn do cấu hình
`EVALUATION_PROVIDER=antigravity` chọn; `fixture` chỉ phục vụ kiểm thử/demo.
Nếu một lượt còn `processing` sau khi tab hoặc tiến trình bị ngắt, trang tổng
kết kiểm tra quyền sở hữu claim theo nhịp 60 giây; repository chỉ cho chạy lại
khi claim cũ hết hạn 15 phút. Lượt còn chạy hợp lệ trả xung đột và không gọi
provider lần hai.

API `/api/sessions` vẫn mặc định `per_question` để giữ tương thích với các
client và kiểm thử hiện có; `api_client.js` của ứng dụng và client mới gửi
`evaluation_timing=after_session`.
Đây là hai chế độ tường minh được lưu cùng phiên, không suy đoán từ provider.

## Chọn câu hỏi thích ứng ở mức MVP

Chọn **một lần khi mở phiên** từ các câu đã duyệt, đúng vai trò, cấp độ, ngôn
ngữ, độ khó cho phép và nguồn có giấy phép đã xác minh. Blueprint yêu cầu một
câu cho mỗi dạng: kiến thức lập trình, tình huống kỹ thuật, giải thích thuật
toán, review mã. Bộ chọn luôn giữ đủ bốn slot và không lặp cùng câu trong
phiên. Với mỗi slot, thứ tự là:

1. Câu được chủ phiên gặp ít lần hơn, ưu tiên câu chưa từng thấy.
2. Trong các câu có cùng số lần gặp, ưu tiên rubric đo các điểm thiếu hiện có
   trong **hồ sơ năng lực đã lưu**. Mỗi loại tiêu chí chưa đạt có độ ưu tiên
   theo tỷ lệ điểm còn thiếu trong tối đa ba kết quả có điểm gần nhất; kết quả
   mới hơn được đặt trọng số cao hơn. Chỉ quan sát mới nhất là `unmet` mới là
   điểm thiếu để chọn câu. `met` hoặc `insufficient_evidence` mới nhất không
   được biến thành nhãn yếu hoặc điểm 0.
3. Nếu vẫn hòa, dùng ID ổn định để kết quả có thể tái hiện.

Không phân tích câu trả lời chưa chấm để đổi câu giữa phiên. Bài luyện và lượt
thử lại sau phiên dùng điểm thiếu đã xác nhận và biến thể đã duyệt. Đây là chọn
câu cá nhân hóa có ràng buộc, chưa phải computerized adaptive testing được
hiệu chuẩn. Ngân hàng chỉ có hai câu mỗi dạng, nên khả năng cá nhân hóa còn
hạn chế; xem `QUESTION_SOURCE_CANDIDATES.md` để mở rộng sau review.

### Hồ sơ năng lực và dữ liệu gốc

`competency_profiles` lưu một hàng cho mỗi `(owner_token_hash, skill_id,
criterion_type)` trong SQLite. Hàng có số lần quan sát đạt/chưa đạt/chưa đủ
căn cứ, ba mức điểm gần nhất, trạng thái, xu hướng và độ dày bằng chứng định
tính (`limited`, `mixed`, `repeated`, `unresolved`); đây không phải xác suất
thống kê. Hàng cũng lưu thời điểm đánh giá cùng
tham chiếu tới phiên, bản trả lời, phiên bản kết quả và tiêu chí gốc. Cookie
người dùng không được lưu nguyên văn; chỉ hash từ cookie liên kết lịch sử.

Sau khi một kết quả chấm hoàn tất, Service tái tạo hồ sơ từ các phiên đã kết
thúc. Khi mở phiên mới hoặc đọc `GET /api/profile`, Service cũng tái tạo để
backfill dữ liệu cũ và khôi phục nếu lần cập nhật trước bị gián đoạn. Mỗi câu
trong một phiên chỉ xét **bản trả lời mới nhất**; nếu bản đó chưa có kết quả
hoàn tất thì câu chưa đóng góp. Chấm lại hoặc gọi API lặp không tăng số quan
sát giả. Lịch sử được
sắp theo `evaluated_at`, không theo thời điểm tạo phiên. Chỉ các tiêu chí rubric
thực sự có trong câu mới tạo quan sát; một câu không phải đo đủ bốn nhóm.
`GET /api/profile` chỉ trả hồ sơ gắn với cookie hiện tại, hoặc danh sách trống
nếu chưa có đánh giá. Báo cáo ba phần vẫn mô tả **phiên hiện tại**; hồ sơ theo
dõi tiến triển qua các phiên và phục vụ chọn câu cho phiên kế tiếp. Không có
đăng nhập hoặc đồng bộ giữa trình duyệt; đổi/xóa cookie sẽ không nối lịch sử.

## Dạng câu hỏi khác nhóm năng lực

Bốn **dạng câu** của blueprint không phải bốn **nhóm năng lực** trong báo cáo.
Báo cáo gán từng tiêu chí rubric quan sát được vào trục:

| Nhóm năng lực | Loại tiêu chí rubric hiện có |
| --- | --- |
| Kiến thức | `behavior_explanation`, `complexity_analysis` |
| Phân tích vấn đề | `failure_analysis` |
| Đề xuất giải pháp | `correctness_argument`, `contract_preservation`, `invariant_preservation` |
| Kiểm chứng | `test_design` |

Ví dụ câu về hành vi Python thường đo kiến thức, sửa hợp đồng và kiểm chứng;
nó không cần đo phân tích vấn đề. Câu về tranh chấp dữ liệu có thể đo phân tích,
giải pháp và kiểm chứng nhưng không cần có tiêu chí kiến thức riêng. Mỗi trục
hiện số tiêu chí thực sự được quan sát: đạt, chưa đạt, chưa đủ căn cứ. Trục
không có tiêu chí trong phiên được ghi **chưa được quan sát**, không gán 0 điểm.
Một tiêu chí đạt là một điểm mạnh có căn cứ trong phiên, không đủ để kết luận
năng lực toàn diện. Điểm tổng toàn phiên không được suy diễn từ bốn câu ngắn.

## Báo cáo sau phiên

`GET /api/sessions/{id}/summary` giữ các trường cũ và thêm `report`:

- `overview`: phạm vi phiên, độ phủ từng trục, điểm mạnh và điểm thiếu có căn cứ.
- `details`: từng câu, bản trả lời gốc, điểm và trạng thái từng tiêu chí, giải
  thích, trích dẫn chính xác hoặc quan sát, phần chưa đủ căn cứ.
- `proposals`: tối đa ba điểm thiếu ưu tiên theo mức đáp ứng thấp và đa dạng
  trục, mục tiêu từ mức rubric cao nhất, bài luyện đã duyệt theo thứ tự tiên
  quyết, thời lượng **ước tính**, khả năng thử lại bằng biến thể khác. Không có
  bài phù hợp thì ghi rõ, không tạo gợi ý giả.

Trạng thái `assessing` và `partial_failure` giữ điểm chưa có ở `null`. Progress
đếm câu hoàn tất trên số câu đã gửi, không giả định thời gian AI còn lại.
