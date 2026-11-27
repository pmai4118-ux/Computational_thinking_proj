# Thay UI phiên phỏng vấn theo HTML Stitch của người dùng

Bàn giao 27/11/2026. Tài liệu này giao cho AGY triển khai UI vào code hiện tại. Bản UI đã được tích hợp ở yêu cầu tiếp theo; xem [bàn giao triển khai](STITCH_UI_IMPLEMENTATION.md). Phạm vi là hub thiết lập, không gian trả lời và hai tab xem kết quả; không thay engine đánh giá hoặc tạo ngân hàng Java mới.

## 1. Nguồn bắt buộc đọc

- `AGENTS.md` tại workspace; [PROJECT_SPEC.md hiện hành](../../PROJECT_SPEC.md). Đặc tả tự luận hiện hành ưu tiên hơn nội dung cũ về sandbox/code trong skill.
- [Design system gốc](../design/stitch-java-backend/design-system/DESIGN.md).
- [Hub HTML](../design/stitch-java-backend/interview-hub/interview-hub.html) · [PNG](../design/stitch-java-backend/interview-hub/interview-hub.png).
- [Workspace HTML](../design/stitch-java-backend/interview-workspace/interview-workspace.html) · [PNG](../design/stitch-java-backend/interview-workspace/interview-workspace.png).
- [Overview HTML](../design/stitch-java-backend/answer-review-overview/answer-review-overview.html) · [PNG](../design/stitch-java-backend/answer-review-overview/answer-review-overview.png).
- [Detail HTML](../design/stitch-java-backend/answer-review-detail/answer-review-detail.html) · [PNG](../design/stitch-java-backend/answer-review-detail/answer-review-detail.png).
- [API contract](api_contract.md), [data contract](data_contract.md), `source/Control/schemas.py`, `source/view/pages.py`, `source/view/static/js/{api_client,workspace,evidence,summary}.js`.

## 2. Nguyên tắc bám thiết kế

Port trực tiếp cấu trúc HTML/CSS của bốn mẫu, thay dữ liệu mẫu bằng dữ liệu server. Không thiết kế lại thành dashboard khác, không đổi sang dark theme, không đổi font, không biến workspace thành hai cột nếu mẫu là các card xếp dọc.

- Plus Jakarta Sans cho nội dung/heading; Space Grotesk cho metadata ở các màn có dùng; JetBrains Mono chỉ ở vùng monospace mà workspace gốc quy định.
- Nền trắng tím rất nhạt; card trắng, viền tím nhạt, shadow mềm; nút gradient violet và trạng thái active tím. Giữ tỉ lệ, margin, padding, border-radius và font weight của từng HTML. Mẫu workspace dùng `#7c3aed`/`#8b5cf6`, còn hai màn review có token `primary=#630ed4`, `primary-container=#7c3aed`: không ép tất cả thành một mã màu.
- Desktop giữ thứ tự nội dung và chiều rộng theo mẫu; mobile dùng một cột, tab có nhãn dễ đọc, button wrap hợp lý, không cắt nội dung dài.
- Header chung giữ logo interviewUS và active Phỏng vấn ảo. Gắn các mục vào route thật; mục chưa có không dùng `href="#"` rồi coi là hoạt động. Avatar/tên An Nguyễn, thông báo và dark-mode trong mẫu không chứng minh app có tài khoản hay notification. Dùng nhãn phiên ẩn danh; ẩn control không có chức năng hoặc ghi rõ trạng thái chưa hỗ trợ.
- PNG hub có vùng đen dư sau footer: không dựng vùng đen hoặc chiều cao canvas dư trong app. Giữ ảnh gốc không chỉnh để làm chứng cứ thiết kế.
- Không dùng một ảnh PNG làm toàn bộ trang. Phải là HTML tương tác, text chọn/copy được và truy cập bằng bàn phím.
- Các nội dung đổi do hợp đồng/phạm vi được liệt kê dưới đây; giữ vị trí và ngôn ngữ thị giác của vùng tương ứng.

## 3. Mapping màn hình vào app

| Mẫu | Route/file triển khai | Hành vi |
|---|---|---|
| interview-hub | `/setup`, `templates/setup.html`; phần lịch sử tái dùng dữ liệu ở `/` | Ba bước thiết lập, xác nhận, tạo session thật |
| interview-workspace | `/sessions/{session_id}`, `templates/workspace.html`, `workspace.js` | Đọc câu, nhập tự luận, lưu, tiếp tục/kết thúc |
| answer-review-overview | `/sessions/{session_id}/review?answer_id=...&revision=...`, `templates/answer_review.html`, `evidence.js` | Tab tổng quan kết quả/rubric |
| answer-review-detail | Cùng route và cùng evaluation với overview | Tab bài đã lưu, highlight và nhận xét theo đoạn |
| Link kết quả cũ | `/sessions/{session_id}/answers/{answer_id}/result?revision=...` | Giữ tương thích; không làm link lịch sử cũ hỏng |
| Tổng kết/bài ôn | `/sessions/{session_id}/summary`, `/sessions/{session_id}/exercises` | Giữ luồng hiện có; chỉ hòa hợp shell nếu cần |

Không dựng hai backend result độc lập cho hai tab. Có thể lưu tab đang xem bằng hash/query client, nhưng answer ID/revision trên URL vẫn chỉ đúng bài đang xem. Chuyển tab không gửi yêu cầu evaluate mới.

## 4. Hub phỏng vấn: bố cục ba bước

Giữ hero “Phòng phỏng vấn ảo”, các bước đánh số tím, hai mode card, khối chủ đề, khối cấu hình và CTA dài toàn chiều rộng, cuối trang là lịch sử dạng hàng như mẫu.

| Thành phần mock | Kết nối đúng phạm vi hiện tại |
|---|---|
| Mode “Mô phỏng thực tế” | Mặc định selected, `evaluation_timing=after_session`: lưu rồi chuyển câu, đánh giá sau khi kết thúc. |
| Mode “Luyện tập có hướng dẫn” | API có `per_question` để đánh giá sau từng câu; có thể bật card này với nhãn chính xác “Nhận phản hồi sau từng câu”. Không hứa có adaptive probing hoặc ba gợi ý trước khi trả lời. Nếu chưa nối lựa chọn vào setup thì card disabled và có giải thích; không selected giả. |
| Thanh áp lực 100% | Không đo stress/cảm xúc. Giữ vị trí bằng metadata “Phản hồi cuối phiên”/“Phản hồi từng câu”; bỏ phần trăm áp lực giả. |
| Chọn Java Core/OOP/SQL/Spring và bộ 5 câu theo roadmap | API hiện chưa nhận topic filter/roadmap lesson. Giữ vỏ card/tab, trong đó hiển thị bốn nhóm câu hiện có và ghi rõ “Theo blueprint hiện tại”. Bộ Java theo roadmap là phần nội dung chưa có; không cho chọn rồi bỏ qua. |
| Vai trò/cấp độ/ngôn ngữ | Giá trị hỗ trợ: `backend_developer`, `intern_fresher`, `vi`. Chưa có bộ Senior/Java chuyên biệt. |
| 5 câu/30 phút | Phiên chính hiện cố định **4 câu**, thời gian ước tính 25–35 phút; không khóa countdown và không thêm số lượng vào request chưa hỗ trợ. Lượt luyện bổ trợ một câu là luồng riêng. |
| AI luôn sẵn sàng | Chỉ dùng thông tin trạng thái thật nếu đã có. Chưa có health check provider thì copy trung tính “Phản hồi được tạo sau khi gửi bài”; vẫn hiển thị demo label khi fixture. |
| Lịch sử ngày/giờ/88 điểm mẫu | Render phiên của chủ cookie hiện tại; không bịa timestamp hoặc aggregate score nếu DTO không cung cấp. Có thể dùng tiến độ/trạng thái/ID hiện hữu ở vị trí cột đó. |

`GET /setup` hiện chưa truyền danh sách sessions. Nếu đưa lịch sử vào hub, tái dùng `controller.list_sessions_for_owner` và cách dựng `session_labels` đang dùng trong `welcome_page`, bổ sung context server-rendered; giữ giới hạn/chính sách quyền sở hữu. Không invent endpoint list history, không đọc SQLite trực tiếp từ JS. `/` vẫn giữ được lịch sử cũ.

`POST /setup` hiện chỉ đọc role/level/language. Nếu bật cả hai mode: mở rộng form adapter một cách tường minh để validate `evaluation_timing`, giữ mặc định `after_session` và fallback không JS; hoặc submit JSON bằng `InterviewApi.createSession` và giữ hành vi form fallback tương đương. Chỉ dùng enum có sẵn; cập nhật test adapter. Không bỏ qua giá trị mode của người dùng.

## 5. Workspace: card xếp dọc như mẫu

Thứ tự cần giữ:

1. Banner tím nhạt “Không gian trả lời”, badge mode thật, câu thứ mấy/tổng và progress.
2. Khối gợi ý dạng accordion như mẫu, **chỉ khi có dữ liệu công khai đã duyệt**. Chưa có API ba hints thì giữ shell nhỏ với thông báo “Phiên hiện tại chưa hỗ trợ gợi ý trước khi nộp”, đóng mặc định. Không lấy `expected_evidence`/reference answer từ rubric để tạo hint, không copy gợi ý Python cố định cho mọi câu.
3. Card đề bài: category, license khi có, prompt, ràng buộc, source URL/ID. Không dán nội dung late binding trong mock vào câu khác. Ngân hàng cũ còn `code`/`code_language`; nếu cần hiển thị để không phá bài lịch sử thì chỉ là trích đoạn đề legacy read-only trong vùng tối tương ứng, không có editor/run/submit code mới. Chuyển ngân hàng sang tự luận thuần là hạng mục nội dung/version riêng.
4. Card trả lời: title, mô tả, vùng bài giải, nháp, đếm ký tự, CTA gửi; footer link tổng kết và kết thúc sớm.

Tiến độ đọc `session.progress`: số câu đã lưu và số câu đã có đánh giá khác nhau. Trong `after_session`, sau khi gửi câu 1 có thể đã lưu 1/4 nhưng 0/4 có kết quả. Không biến trạng thái lưu thành đã chấm.

### Khung luận điểm nhiều phần

Mẫu có ba card đánh số và nút “Thêm khung luận điểm”. Đây là thành phần View mới cần nối với một `Answer.text`, không phải ba API answers:

- Dùng heading chung theo tự luận: “Phân tích vấn đề”, “Phương án và đánh đổi”, “Cách xác minh”; người dùng có thể chỉnh/thêm khung. Không ép mọi câu phải có “sửa mã”. Các trường trống không chặn người dùng nếu tổng bài hợp lệ theo quy tắc hiện tại.
- Khi bấm gửi, serialize các phần theo thứ tự thành văn bản với heading/ngắt dòng rõ, cho thấy định dạng được lưu; tổng payload bao gồm heading cũng phải ≤20.000 ký tự. Không `innerHTML`, không thêm HTML vào `Answer.text`.
- Giữ một nguồn dữ liệu canonical tương thích `#answer-text` và `workspace.js`; cập nhật handler/counter/draft có kiểm tra. Nếu dùng textarea canonical ẩn, không duplicate ID hoặc bỏ cập nhật khi gõ trong từng card.
- Nháp structured dùng khóa có version trong `sessionStorage`, scoped theo session + question/version. Đọc được nháp text cũ: khôi phục nguyên văn vào một khung, không tự phân tích phá nội dung. Nếu storage bị chặn vẫn gửi được.
- Sau khi lưu, render đúng `current_answer.text`/revision, không parse rồi serialize lại và thay bản gốc. Highlight review dựa đúng chuỗi server lưu.
- Toolbar B/I/code và Voice AI trong prototype chưa có backend tương ứng. Chỉ bật control đã thực sự có tác dụng trong text thuần, hoặc ẩn/disabled với nhãn giải thích. Không thêm voice/STT, code editor hoặc rich-text HTML để giống mẫu.

Giữ wording nháp “Bản nháp trong tab này, chưa lưu máy chủ”. Chỉ hiện “Đã lưu trên máy chủ” sau response lưu thành công. Nút kết thúc sớm có xác nhận; bản nháp chưa gửi không tự đưa vào tổng kết.

## 6. Review tab 1: Tổng quan kết quả & Rubric

Giữ header/title, hai tab lớn, phần trên hai cột và khối chi tiết bằng chứng bên dưới; footer CTA theo trạng thái phiên.

- Cột trái: vòng điểm câu, các thanh tiêu chí và khung nhận xét. Điểm là `result.total_score / result.maximum_score`, không cố định 1/6 hay 100. Khi thiếu bằng chứng thì hiện “Chưa tính tổng điểm”; vòng trung tính, không 0%.
- Cột phải: danh sách `criterion_checks` có nhãn, điểm/max_score và trạng thái `met`, `unmet`, `insufficient_evidence`. Số tiêu chí lấy độ dài dữ liệu, không hard-code 3.
- Chọn card đặt active border tím, cập nhật panel dưới đúng criterion ID: explanation, evidence quote/observation, feedback message/suggestion nối bằng `criterion_id`.
- Màu xanh cho đạt, đỏ cho chưa đạt, trung tính/vàng cho chưa đủ bằng chứng. Không tự thêm ngưỡng “đậu/rớt” hoặc tổng hợp pass/fail chỉ từ % nếu contract không định nghĩa.
- “Us-Bot Assessor” chỉ là khung trình bày nhận xét từ response có thật; không gọi LLM mới khi đổi tab/card và không viết thêm chẩn đoán tại client.
- Giữ điểm do Service tính; UI không đổi schema sang A–D có trọng số hoặc tự chuẩn hóa thành 100 rồi thay giá trị nguồn. Nếu thêm phần trăm chỉ là hiển thị phụ có nhãn và chỉ khi score/max hợp lệ.

## 7. Review tab 2: Bài trả lời đã lưu & Nhận xét chi tiết

Giữ card toàn văn lớn ở trên, các đoạn tô xanh/đỏ, khung nhận xét có viền trái bên dưới, liên kết tiêu chí, copy bài và link xem lỗi chính.

- Toàn văn lấy `response.result.answer_text` của đúng answer revision. Copy trả chuỗi gốc, không lẫn badge/nhãn nhận xét. Đếm từ tính client phải ghi đúng là đếm từ, không lấy “428 từ” mẫu; thời gian nộp chỉ hiện nếu lấy từ saved answer có thật.
- Các range dùng `start_offset`, `end_offset` (end-exclusive) và `quote`. Python offset theo Unicode code point: dùng `Array.from(text)` trong JS như renderer hiện có, không cắt bằng UTF-16 index sai khi có emoji.
- Trước khi highlight kiểm tra `points.slice(start,end).join("") === quote`. Offset/quote không khớp không highlight; hiển thị cảnh báo dữ liệu hoặc quote dạng riêng, không sửa bài gốc để khớp.
- Tab 2 cần tổng hợp quote của tất cả criteria, không chỉ criterion đang chọn. Range trùng/chồng được chia đoạn và gắn nhiều criterion IDs; không bỏ nội dung text hoặc gán màu đạt khi cùng đoạn còn bất đồng. Có thể dùng màu trung tính cho chồng lấn và danh sách chọn tiêu chí ở panel.
- Chọn highlight bằng chuột hoặc bàn phím cập nhật detail panel tương ứng criterion/evidence; panel có feedback/suggestion thật. Trường observation không có offset được hiển thị riêng, không tự tạo đoạn trích. `insufficient_evidence` không tô như lỗi sai đã xác định.
- Badge số đoạn xanh/đỏ tính theo quote hợp lệ và quy tắc deduplicate rõ; không coi số criteria là số quotes. Không copy sẵn 2 đạt/2 lỗi trong PNG.
- Trạng thái chọn criterion/quote dùng chung cho hai tab; chuyển tab không reset sang dữ liệu khác, không đánh giá lại. Nút “Xem lỗi chính” chọn một evidence `unmet` có thật; không có lỗi xác định thì ghi rõ hoặc ẩn.
- Nội dung bài và quote tạo bằng text nodes/`textContent`; không render HTML từ answer/provider. Ví dụ `<script>` phải hiển thị nguyên văn.

### Những trạng thái bắt buộc của hai tab

| Trạng thái | Hiển thị/hành động |
|---|---|
| Chưa có bài | Empty state, trở về câu hỏi nếu phiên còn làm |
| Đã lưu, đang làm phiên after_session | Xem bài đã lưu; chưa có rubric/điểm. Không tự evaluate để lấp card. |
| pending/processing | Status đang xử lý, không điểm mẫu; tải lại có kiểm soát |
| completed có đủ căn cứ | Điểm/criteria/evidence từ response |
| completed còn insufficient_evidence | Score null và lý do; không quy 0 |
| failed | Giữ bài gốc; thông báo lỗi dịch vụ, retry nếu response cho phép |
| 403/404/410 | Thông báo quyền/không tìm thấy/hết hạn và link phục hồi; không lộ bài người khác |

## 8. Luồng và API cần giữ

### Tạo phiên

```json
{
  "role": "backend_developer",
  "level": "intern_fresher",
  "language": "vi",
  "evaluation_timing": "after_session"
}
```

POST `/api/sessions` qua client hiện có; API raw mặc định `per_question` để tương thích, còn UI/client đang ưu tiên `after_session`. Vì vậy phải truyền mode tường minh. Không gửi lesson_id/topic/question_count chưa có trong DTO.

### Làm và đánh giá

| Method | URL | Payload/đọc dữ liệu |
|---|---|---|
| GET | `/api/sessions/{sid}` | SessionViewDTO và current question/answer |
| POST | `/api/sessions/{sid}/answers` | `{question_id, question_version, client_submission_id, text}`; đọc `.answer.answer_id`, `.answer.revision` |
| POST | `/api/sessions/{sid}/next` | `{from_question_index}`; chỉ chuyển theo state machine |
| POST | `/api/sessions/{sid}/end` | `{reason:"student_requested"}` |
| GET | `/api/sessions/{sid}/summary` | Summary cùng trạng thái phiên/bài |
| POST | `/api/sessions/{sid}/answers/{aid}/evaluate` | `{answer_revision}` |
| GET | `/api/sessions/{sid}/answers/{aid}/evaluations/{revision}` | `{result,feedback_items}` theo revision |
| GET | `/api/sessions/{sid}/exercises` | Bài ôn theo điểm thiếu, không tạo bài mới ở client |

Luồng `after_session`: xác nhận mục tiêu → tạo phiên → nhập → POST lưu → next → lặp → hoàn tất/kết thúc sớm → summary điều phối đánh giá các bài đã lưu (hiện tối đa 2 yêu cầu đồng thời) → mở review của từng revision. Không gọi AI trước khi kết thúc chỉ để giống màn review mẫu.

Luồng `per_question` nếu bật: lưu → đánh giá → review → next; giữ retry/polling hiện có. Không quảng cáo thêm Socratic follow-up khi chưa có.

Mọi request giữ cookie cùng origin; owner không lấy từ URL/form do người dùng chọn. Double-click gửi cùng `client_submission_id` phải idempotent. Lỗi lưu/next hoặc network không làm mất nháp; không tự tăng revision hoặc submit lại bài mới khi người dùng chỉ retry evaluation. Không đổi lỗi provider thành điểm 0. Không kích hoạt AI thật trong test mặc định.

## 9. File/hook để AGY làm

Giữ FastAPI + Jinja2 + CSS/JavaScript hiện có. Không cần SPA/framework mới.

- View adapters: `source/view/pages.py`; templates `base.html`, `setup.html`, `workspace.html`, `answer_review.html`; có thể chia partials tái sử dụng. Welcome chỉ chỉnh phần chung/lịch sử cần cho hub, summary/exercise giữ nghiệp vụ.
- CSS: `tokens.css`, `components.css`, `workspace.css`, `results.css`; thêm `interview_hub.css` nếu cần tách scope. Không để class review ảnh hưởng roadmap.
- JS: `workspace.js`, `evidence.js`; thêm module hub hoặc tabs/outline theo cấu trúc hiện tại; tái dùng `api_client.js`. Không thay `summary.js` orchestration vì đổi layout.
- Các hook gốc cần giữ hoặc migrate đồng bộ cả JS/test: `[data-workspace]` và dataset session/question/version/answer/revision/timing; `#answer-form`, `#answer-text`, `#submit-answer`, `#answer-counter`, `#draft-label`, `#workspace-status`, `#workspace-error`, `#retry-evaluation`, `#end-session` và confirmation/recovery IDs.
- Review: `[data-answer-review]` và dataset revision/current index; `#review-status`, `#review-error`, `#review-content`, `#retry-review-load`, `#retry-review-evaluation`, `#evaluation-total`, `#evaluation-state`, `#criteria-list`, `#answer-source`, `#evidence-detail`, `#selected-criterion-explanation`, `#next-question`. Tránh render duplicate ID ở hai tab; dùng một nguồn dữ liệu/shared state và renderer cho từng panel.
- Không sửa `data/seed`, dữ liệu rubric, scoring/evidence validation, ngân sách retry, quyền sở hữu hay cookie để làm UI dễ demo. Không sửa `data/learning` hoặc mất link `/learning-path`.

## 10. Kế hoạch thực hiện và nghiệm thu

1. Kiểm tra git diff trước; bảo toàn thay đổi chưa commit. Đọc bốn HTML và PNG, lập mapping component → template/hook/API. Giữ bản gốc trong `design/`.
2. Port tokens/shell và hub, sau đó workspace, rồi hai tab review. Thay text mẫu ở nơi dữ liệu/phạm vi khác bằng quy tắc trong tài liệu; không dùng fixture giả làm dữ liệu live.
3. Nối tương tác thật: mode, submit/retry/next/end, draft outline, tab, criterion/quote select/copy. Làm loading/empty/error/insufficient states cùng lượt build.
4. So screenshot tại cùng chiều rộng nguồn (workspace 1280px; hai review xấp xỉ 1080/1040px; đọc kích thước PNG thật trước khi capture), thêm desktop 1440 và mobile 390px. Đối chiếu cấu trúc/font/card/tab/tím/glow; ghi riêng sai khác có chủ ý do dữ liệu/phạm vi. Không chấp nhận “giống tone màu” mà khác bố cục.
5. Kiểm tra 320/390/768/1024/1440px, text dài/emoji, không tràn ngang, keyboard tab/arrow/Enter/Space, focus rõ, tab có `role=tablist/tab/tabpanel` và `aria-selected`, accordion `aria-expanded`, reduced-motion. Đừng để gradient/blur làm mất tương phản chữ.
6. Test hồi quy phù hợp: Python ngoại tuyến khi sửa adapter/controller, Node suites hiện có cho UI, browser qua hai mode; refresh/resume; double submit; mất mạng sau lưu trước next; provider fail/retry; ended early; completed; expired/forbidden; thiếu bằng chứng; Unicode offset; quote chồng; XSS text; nháp cũ và structured draft mới.
7. Với `after_session`, xác minh không có evaluate request khi còn làm phiên; sau kết thúc summary vẫn đánh giá theo concurrency hiện có. Đổi tab/chọn quote không gửi POST. Bài copy và text gốc server phải khớp nguyên văn.
8. Bàn giao danh sách file thay, ảnh trước/sau, test thực chạy và phần chưa hỗ trợ; không tự commit/push/deploy khi người dùng chưa yêu cầu.

Các kết quả 270 Python tests/18 Node tests của lần bàn giao lộ trình trước chỉ là baseline đã ghi trong `JAVA_BACKEND_IMPLEMENTATION.md`, không chứng minh bản UI Stitch đã được test. AGY phải báo kết quả lần build mới.

## 11. Tư duy tính toán

- **Phân rã:** hub/setup, trả lời/nháp, lưu/điều phối, tổng quan rubric, đối chiếu quote.
- **Nhận diện mẫu:** cùng trạng thái lưu/đang xử lý/lỗi/thử lại trên mọi loại câu; dùng chung criterion/evidence renderer.
- **Trừu tượng hóa:** session ID, question/rubric version và answer revision là khóa; tab là trạng thái View, không là bài nộp khác.
- **Thiết kế thuật toán:** serialize outline ổn định, render Unicode ranges không mất ký tự, đồng bộ selection và giữ state machine/idempotency hiện có.
