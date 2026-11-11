/* Offline diagrams for the six pages requested on 10 November 2026. No backend. */
const fs = require('node:fs');
const path = require('node:path');
const inventory = JSON.parse(fs.readFileSync(path.join(__dirname, 'user_flow_review.json'), 'utf8'));
const screens = Object.fromEntries(inventory.screens.map(s => [s.id, s]));
const N = (id, x, y, title, caption, type, refs, detail) => ({id,x,y,w:280,h:90,title,caption,type,refs,detail});
const E = (from, to, label='', points=null, kind='normal') => ({from,to,label,points,kind});
const pages = [
  {
    id:'questions', name:'Câu hỏi luyện tập', short:'Luyện câu hỏi', scope:'Lõi luyện tập',
    summary:'Chọn một câu, trả lời tự luận, xem căn cứ và luyện lại khi cần.',
    reading:'Thư viện → Chi tiết → Xác nhận mục tiêu → Trả lời → Kết quả.',
    rules:['Quay về danh sách giữ từ khóa, bộ lọc và vị trí cuộn.','Chỉ xem đề không được tính là đã làm.','Luyện lại tạo lượt mới; bài và kết quả cũ được giữ nguyên.'],
    nodes:[
      N('list',390,40,['Mở thư viện câu hỏi'],['Tìm kiếm · lọc chủ đề/cấp độ'],'step',['P01','P02'],{action:'Chọn câu phù hợp từ danh sách đã được review.',next:'Mở chi tiết câu; nếu chưa có lịch sử thì hiển thị hướng dẫn khởi đầu.'}),
      N('empty',30,40,['Không tìm thấy câu'],['Xóa bộ lọc hoặc tải lại'],'error',[],{action:'Hiện rõ ngân hàng trống, bộ lọc không có kết quả hoặc lỗi tải.',next:'Cho xóa bộ lọc / tải lại; giữ danh sách đã tải nếu chỉ lỗi phân trang.'}),
      N('detail',390,190,['Xem chi tiết câu'],['Đề · mục tiêu · tiêu chí · nguồn'],'step',['P03','QMETA01'],{action:'Đọc đề, ràng buộc và nguồn; bấm “Luyện câu này”.',next:'Đến bước xác nhận mục tiêu; chưa mở đáp án hoặc rubric nội bộ.'}),
      N('setup',390,340,['Xác nhận mục tiêu'],['Vai trò · cấp độ · chủ đề'],'step',['I03'],{action:'Làm rõ thông tin còn thiếu và xác nhận trước khi bắt đầu.',next:'Chỉ tạo lượt khi cấu hình hợp lệ và có câu đủ điều kiện.'}),
      N('write',390,490,['Nhập và gửi tự luận'],['Lưu bài trước khi đánh giá'],'step',['I04'],{action:'Đọc đề, nhập câu trả lời, kiểm tra nội dung rồi gửi.',next:'Xác nhận đã lưu bài → trích và xác thực bằng chứng → tính rubric bằng quy tắc.'}),
      N('failure',750,490,['Lưu / đánh giá gặp lỗi'],['Giữ bài · thử lại đúng bước'],'error',[],{action:'Nếu chưa xác nhận lưu: giữ bản nháp và đối soát lần gửi. Nếu đã lưu nhưng AI lỗi: giữ bài đã nộp.',next:'Thử lại bước lỗi có giới hạn; không nộp trùng và không biến lỗi thành điểm 0.'}),
      N('result',390,640,['Đọc kết quả câu'],['Điểm có căn cứ · phần cần cải thiện'],'result',['F01'],{action:'Xem tiêu chí, điểm nếu đủ căn cứ, lý do và gợi ý ôn phù hợp.',next:'Mở trích dẫn, luyện câu liên quan hoặc quay lại thư viện.'}),
      N('evidence',750,640,['Xem căn cứ'],['Mở đúng đoạn trong bài gốc'],'result',['F03'],{action:'Chọn một tiêu chí để xem trích dẫn và giải thích tương ứng.',next:'Đóng phần căn cứ trở lại đúng tiêu chí đang đọc; bài gốc không thay đổi.'}),
      N('again',30,640,['Luyện câu liên quan'],['Cùng kỹ năng · khác ngữ cảnh'],'extension',['F04'],{action:'Chọn biến thể đã review để kiểm tra khả năng vận dụng.',next:'Tạo lượt luyện mới qua bước xác nhận. Không có biến thể thì về thư viện.',note:'Thiết kế ôn tập / R8; chưa coi tính năng đã triển khai.'})
    ],
    edges:[E('list','detail'),E('list','empty','Không có câu'),E('empty','list','Thử lại',[[170,40],[170,20],[530,20],[530,40]],'retry'),E('detail','setup','Luyện câu này'),E('setup','write','Đã xác nhận'),E('write','result','Đã lưu và đánh giá'),E('write','failure','Có lỗi'),E('failure','write','Thử lại',[[890,490],[890,465],[670,465],[670,490]],'retry'),E('result','evidence','Xem chi tiết'),E('result','again','Luyện thêm'),E('again','setup','Lượt mới',[[170,640],[170,385],[390,385]],'retry')]
  },
  {
    id:'interview',name:'Phiên phỏng vấn',short:'Phiên phỏng vấn',scope:'Lõi phiên; chế độ full là đề xuất',
    summary:'Thiết lập phiên, trả lời lần lượt bốn nhóm câu và xem tổng kết.',
    reading:'Chọn cấu hình → Xác nhận → Trả lời và lưu → Câu tiếp → Tổng kết.',
    rules:['Bốn nhóm: kiến thức lập trình, tình huống, giải thích thuật toán, lập luận/đánh đổi.','Demo rubric: xem phản hồi từng câu. Mô phỏng full: chỉ mở phản hồi cuối phiên.','Chế độ hướng dẫn full có gợi ý chủ động; chưa đưa adaptive probing vào MVP.'],
    nodes:[
      N('config',390,40,['Chọn phiên và chế độ'],['Chủ đề · cấp độ · cách nhận phản hồi'],'step',['I01','I02'],{action:'Từ danh sách phiên, chọn tạo phiên mới hoặc tiếp tục phiên đang dở.',next:'Chọn cấu hình và đọc rõ thời điểm nhận phản hồi; lựa chọn chưa khả dụng phải có nhãn.'}),
      N('setup',390,190,['Làm rõ và xác nhận'],['Kiểm tra mục tiêu và đủ câu hỏi'],'step',['I03'],{action:'Xác nhận vai trò, cấp độ, chủ đề và phạm vi của phiên.',next:'Khóa cấu hình cùng phiên bản câu hỏi/rubric; không bắt đầu khi thiếu nội dung bắt buộc.'}),
      N('missing',750,190,['Thiếu thông tin / câu hỏi'],['Sửa cấu hình hoặc hủy'],'error',[],{action:'Hỏi thông tin còn thiếu hoặc báo nhóm câu không đủ nội dung đã review.',next:'Trở lại cấu hình, giữ các lựa chọn đã nhập; không âm thầm giảm độ phủ.'}),
      N('write',390,340,['Trả lời câu hiện tại'],['Nhập tự luận → gửi → xác nhận lưu'],'step',['I04','I05'],{action:'Trả lời và lưu nguyên văn bài. Chế độ hướng dẫn có thể xin gợi ý theo chính sách đã duyệt.',next:'Demo/hướng dẫn: xem phản hồi câu rồi tiếp tục. Mô phỏng: tiếp tục mà chưa lộ điểm.',note:'Nếu lưu hoặc AI lỗi, giữ bài và xử lý như nhánh lỗi ở trang Câu hỏi luyện tập.'}),
      N('exit',30,340,['Muốn rời / kết thúc sớm'],['Hủy rời · lưu và thoát · kết thúc'],'decision',[],{action:'Hiển thị lựa chọn rõ khi người học rời trang.',next:'Hủy rời → ở lại; lưu và thoát → lần sau tiếp tục; xác nhận kết thúc → tổng kết phần đã làm.',note:'Chỉ báo đã lưu sau xác nhận. Không tự gửi bản nháp hoặc coi câu chưa làm là 0.'}),
      N('more',390,490,['Còn câu trong phiên?'],['Kiểm tra tiến độ sau mỗi lần lưu'],'decision',[],{action:'Đối chiếu số câu đã gửi với blueprint của phiên.',next:'Còn → mở câu tiếp. Hết hoặc đã xác nhận kết thúc sớm → tổng kết.'}),
      N('next',750,490,['Mở câu tiếp theo'],['Giữ nguyên bài đã nộp'],'step',[],{action:'Tăng tiến độ sau khi bài hiện tại đã được lưu thành công.',next:'Quay lại workspace với đúng câu và cấu hình phiên; không bỏ câu do điểm thấp.'}),
      N('summary',390,640,['Xem tổng kết phiên'],['Đủ / thiếu câu · trạng thái từng bài'],'result',['F02','F01','F03'],{action:'Xem danh sách câu, kết quả, tiêu chí và căn cứ. Bài đang xử lý hoặc lỗi có nhãn riêng.',next:'Xem chi tiết câu, ôn điểm thiếu hoặc tạo phiên mới; kết quả cũ giữ nguyên.'}),
      N('resume',30,40,['Tiếp tục phiên dở'],['Mở đúng câu và bản nháp'],'step',[],{action:'Chọn một phiên đang dở mà người dùng còn quyền truy cập.',next:'Khôi phục phần đã lưu và bản nháp được phép; không tự nộp bài khi mở lại.'})
    ],
    edges:[E('config','setup','Tạo phiên'),E('config','resume','Có phiên dở'),E('resume','write','Tiếp tục',[[170,130],[170,300],[390,300],[390,340]],'retry'),E('setup','missing','Chưa hợp lệ'),E('setup','write','Đã xác nhận'),E('write','exit','Rời trang'),E('write','more','Đã lưu; phản hồi theo chế độ'),E('more','next','Có'),E('next','write','Tiếp tục',[[890,490],[890,385],[670,385]],'retry'),E('more','summary','Không'),E('exit','summary','Xác nhận kết thúc',[[170,430],[170,685],[390,685]])]
  },
  {
    id:'roadmap',name:'Lộ trình cá nhân hóa',short:'Lộ trình',scope:'Thiết kế mở rộng; chưa tự thêm vào sprint',
    summary:'Dùng kết quả đầu vào để chọn nội dung học, kiểm tra và cập nhật tiến độ.',
    reading:'Mở lộ trình → Kiểm tra dữ liệu nền → Chọn mục → Học và kiểm tra → Cập nhật.',
    rules:['Chưa có kiểm tra đầu vào: chỉ hiển thị bản xem trước, chưa gọi là cá nhân hóa.','Tự đánh dấu “đã biết” khác với kiến thức đã được kiểm tra.','Thứ tự học dựa trên bằng chứng và tiên quyết; XP không mở khóa chặng.'],
    nodes:[
      N('open',390,40,['Mở lộ trình'],['Đọc mục tiêu đang được xác nhận'],'extension',['L01','L05'],{action:'Mở trang từ điều hướng hoặc sau kết quả kiểm tra đầu vào.',next:'Kiểm tra có kết quả nền phù hợp với mục tiêu hiện tại hay chưa.'}),
      N('has',390,190,['Có kết quả nền phù hợp?'],['Kiểm tra phạm vi và bằng chứng'],'decision',[],{action:'Đối chiếu mục tiêu và phần kỹ năng đã được đánh giá.',next:'Có → mở lộ trình có căn cứ. Chưa → xem trước và đề nghị kiểm tra đầu vào.'}),
      N('test',750,190,['Làm kiểm tra đầu vào'],['Chuyển sang trang Kiểm tra đầu vào'],'destination',[],{action:'Giải thích cần kiểm tra gì trước khi cá nhân hóa.',next:'Sau khi có kết quả, quay lại lộ trình; chỉ lập phần đủ căn cứ.',go:'assessment'}),
      N('choose',390,340,['Chọn chặng và mục học'],['Lý do chọn · tiên quyết · thời lượng'],'extension',['L05','L06'],{action:'Đọc mục tiêu, lý do đề xuất và mở học liệu có nguồn.',next:'Học nội dung được đề xuất hoặc chọn ôn một mục phù hợp.'}),
      N('learn',390,490,['Học rồi kiểm tra mục'],['Trả lời tự luận ngắn, xem căn cứ'],'extension',['L06','L07'],{action:'Học từ nguồn đã review rồi làm bài kiểm tra cho phạm vi mục đó.',next:'Đạt → cập nhật phần đã xác minh. Cần củng cố → quay lại học. Lỗi/thiếu căn cứ → giữ trạng thái chưa xác định.'}),
      N('reinforce',750,490,['Cần củng cố / chưa đủ căn cứ'],['Học lại · bổ sung · thử đánh giá lại'],'error',[],{action:'Đọc lý do để phân biệt trả lời chưa đạt, thiếu bằng chứng và lỗi xử lý.',next:'Học lại hoặc bổ sung câu trả lời; nếu AI lỗi thì thử lại trên bài đã lưu. Không xóa kết quả cũ.'}),
      N('update',390,640,['Cập nhật lộ trình'],['Lưu kết quả và bước học tiếp'],'result',['L05','L08'],{action:'Cập nhật phạm vi kỹ năng đã xác minh; hiển thị phần cần ôn và mục tiếp theo.',next:'Chọn mục học tiếp hoặc mở Tổng quan để xem việc cần làm.',go:'overview'}),
      N('change',30,340,['Đổi mục tiêu / kiểm tra lại'],['Xác nhận tạo phiên bản kế hoạch mới'],'extension',[],{action:'Cho biết việc thay mục tiêu hoặc kiểm tra lại ảnh hưởng đến kế hoạch ra sao.',next:'Giữ kế hoạch và bài cũ; chỉ cập nhật sau khi có xác nhận và kết quả mới.'})
    ],
    edges:[E('open','has'),E('has','test','Chưa'),E('has','choose','Có'),E('test','choose','Có kết quả phù hợp',[[890,280],[890,315],[530,315],[530,340]],'retry'),E('choose','change','Điều chỉnh'),E('choose','learn','Mở mục học'),E('learn','reinforce','Chưa đạt / lỗi'),E('reinforce','learn','Củng cố / thử lại',[[890,580],[890,610],[705,610],[705,535],[670,535]],'retry'),E('learn','update','Đạt trong phạm vi kiểm tra'),E('update','choose','Mục tiếp',[[390,685],[340,685],[340,385],[390,385]],'retry')]
  },
  {
    id:'overview',name:'Tổng quan',short:'Tổng quan',scope:'Thiết kế trang tổng hợp; lịch sử là lõi',
    summary:'Biết hôm nay nên làm gì, tiếp tục bài dở hoặc xem lại kết quả đã có.',
    reading:'Mở tổng quan → Đọc trạng thái dữ liệu → Chọn việc cần làm → Quay lại cập nhật.',
    rules:['Không có dữ liệu thì hiển thị trạng thái trống và hành động bắt đầu.','Điểm danh và hoạt động học là hai trạng thái khác nhau; không tự cộng XP khi mở trang.','Quay lại từ bài cũ giữ bộ lọc lịch sử, tháng và ngày đang xem.'],
    nodes:[
      N('open',390,40,['Mở trang Tổng quan'],['Việc hôm nay · tiến độ · lịch sử'],'step',['D01','D02'],{action:'Tải dữ liệu được phép xem của người dùng hiện tại.',next:'Hiển thị từng vùng đã tải; lỗi một vùng không làm mất toàn trang.'}),
      N('has',390,190,['Đã có hoạt động học?'],['Phân biệt dữ liệu thật và trang trống'],'decision',[],{action:'Kiểm tra bài đã nộp, phiên đang dở và kết quả đã được lưu.',next:'Chưa → hướng dẫn bắt đầu. Có → hiển thị các hành động phù hợp.'}),
      N('empty',750,190,['Chưa có hoạt động'],['Chọn cách bắt đầu luyện'],'step',['D02'],{action:'Cho chọn làm câu đầu tiên, tạo phiên hoặc làm kiểm tra đầu vào.',next:'Đi tới một trong ba trang tương ứng; không tạo điểm hay lịch sử minh họa.',links:['questions','interview','assessment']}),
      N('choose',390,340,['Chọn việc muốn làm'],['Tiếp tục · luyện · ôn · xem lại'],'step',['D01'],{action:'Đọc việc hôm nay và chọn đúng hành động cần thực hiện.',next:'Đi thẳng đến nội dung tương ứng, không bắt qua một bước điều hướng trung gian.'}),
      N('resume',30,340,['Tiếp tục bài / phiên dở'],['Mở đúng câu, giữ bài đã lưu'],'destination',[],{action:'Chọn phiên gần nhất còn có thể tiếp tục.',next:'Chuyển sang Phiên phỏng vấn; nếu là bài đầu vào thì về đúng bài kiểm tra đang dở.',links:['interview','assessment']}),
      N('learn',750,340,['Luyện mới hoặc ôn tập'],['Chọn câu · tạo phiên · mở lộ trình'],'destination',[],{action:'Chọn hoạt động từ tiến độ thực tế; nếu chưa có mục đến hạn, cho luyện tự chọn.',next:'Chuyển tới trang luyện câu hỏi, phiên phỏng vấn hoặc lộ trình.',links:['questions','interview','roadmap']}),
      N('history',390,490,['Chọn bài trong lịch sử'],['Lọc thời gian · chủ đề · trạng thái'],'step',['H01'],{action:'Chọn bài hoặc phiên đã làm để mở nguyên văn, kết quả và căn cứ.',next:'Bài cũ chỉ đọc; luyện lại tạo lượt mới. Bài đang đánh giá chỉ mở trạng thái, không nộp lại.'}),
      N('calendar',30,490,['Xem ngày / điểm danh'],['Chọn ngày; xác nhận khi đã lưu'],'extension',['D01'],{action:'Xem hoạt động theo ngày hoặc điểm danh hôm nay theo chính sách đã duyệt.',next:'Chỉ đổi trạng thái sau xác nhận; retry không cộng trùng. Điểm danh không thay thế việc học.'}),
      N('return',390,640,['Quay lại Tổng quan'],['Cập nhật hoạt động đã được lưu'],'result',[],{action:'Sau khi hoàn thành hoặc xem lại, trở về đúng vùng đã mở.',next:'Cập nhật dữ liệu thực; chưa có thay đổi thì giữ nguyên thống kê, bộ lọc và vị trí.'})
    ],
    edges:[E('open','has'),E('has','empty','Chưa'),E('has','choose','Có'),E('choose','resume','Tiếp tục'),E('choose','learn','Luyện / ôn'),E('choose','history','Xem lại'),E('history','calendar','Xem theo ngày'),E('history','return','Đóng chi tiết'),E('calendar','return','Trở lại',[[170,580],[170,685],[390,685]])]
  },
  {
    id:'login',name:'Đăng nhập',short:'Đăng nhập',scope:'Thiết kế tài khoản theo yêu cầu; ngoài baseline ẩn danh',
    summary:'Đăng nhập bằng Google, xử lý hủy/lỗi và trở lại đúng nơi đang cần lưu tiến độ.',
    reading:'Mở đăng nhập → Chọn Google → Xác nhận → Kiểm tra tài khoản → Trở lại trang đích.',
    rules:['Chọn phương án Google theo bản UI tham chiếu; chưa thêm đăng ký bằng mật khẩu.','Lần đầu có thể khởi tạo hồ sơ tối thiểu; chỉ hỏi thông tin cần để luyện tập.','MVP hiện vẫn mô tả owner ẩn danh. Ghép lịch sử khách vào tài khoản cần nhóm chốt trước khi triển khai.'],
    nodes:[
      N('open',390,40,['Mở trang Đăng nhập'],['Ghi nhớ trang người dùng đang đến'],'step',[],{action:'Mở từ nút đăng nhập hoặc khi một thao tác cần tài khoản theo chính sách full.',next:'Hiển thị lý do đăng nhập và giữ đích nội bộ để quay lại; giữ nháp được phép.',note:'Đây là thiết kế đề xuất theo yêu cầu mới, chưa phải backend auth đã có.'}),
      N('google',390,190,['Tiếp tục với Google'],['Chọn tài khoản và chấp thuận'],'step',[],{action:'Bấm nút Google; thực hiện xác thực trên giao diện nhà cung cấp.',next:'Chờ kết quả; khóa bấm trùng, không yêu cầu nhập mật khẩu Google vào ứng dụng.'}),
      N('cancel',750,190,['Hủy / từ chối / lỗi kết nối'],['Giữ đích đến và dữ liệu đang làm'],'error',[],{action:'Hiển thị trạng thái đăng nhập chưa hoàn tất bằng lời rõ ràng.',next:'Cho thử lại hoặc quay về trang trước; không báo đã đăng nhập khi chưa xác minh.'}),
      N('account',390,340,['Tài khoản đã có hồ sơ?'],['Sau khi xác thực thành công'],'decision',[],{action:'Kiểm tra tài khoản ứng dụng tương ứng sau xác thực.',next:'Đã có → trở lại đích. Lần đầu → tạo hồ sơ tối thiểu sau xác nhận.',note:'Không coi việc cùng địa chỉ email là quyền tự động lấy bài của owner khác.'}),
      N('profile',750,340,['Lần đầu: xác nhận hồ sơ'],['Tên hiển thị · mục tiêu luyện'],'step',[],{action:'Giải thích phạm vi lưu dữ liệu; thu mục tiêu tối thiểu khi cần.',next:'Xác nhận khởi tạo rồi trở lại trang đích. Nếu lưu lỗi, giữ form để thử lại.'}),
      N('return',390,490,['Trở lại đúng trang đích'],['Khôi phục ngữ cảnh, không tự gửi bài'],'result',[],{action:'Quay về thao tác đang thực hiện sau khi đăng nhập thành công.',next:'Nếu không có đích thì tới Tổng quan; người học tiếp tục chủ động.',links:['overview','questions','interview','roadmap','assessment']}),
      N('expired',30,490,['Phiên đăng nhập hết hạn'],['Giữ nháp; yêu cầu xác thực lại'],'error',[],{action:'Giải thích cần đăng nhập lại; không hiển thị dữ liệu riêng của tài khoản khác.',next:'Đăng nhập lại rồi kiểm tra quyền trước khi khôi phục. Không tự chuyển bài sang tài khoản mới.'}),
      N('merge',390,640,['Nếu đang có lịch sử khách'],['Cần chốt chính sách ghép dữ liệu'],'extension',[],{action:'Giải thích dữ liệu nào thuộc lượt khách và dữ liệu nào thuộc tài khoản.',next:'Chỉ thực hiện liên kết theo chính sách đã được duyệt; chưa có chính sách thì giữ tách biệt.',note:'Đây là điều kiện cần quyết định, không phải bước bắt buộc trong mọi lần đăng nhập.'})
    ],
    edges:[E('open','google'),E('google','cancel','Không thành công'),E('cancel','google','Thử lại',[[890,190],[890,165],[670,165],[670,190]],'retry'),E('google','account','Đã xác thực'),E('account','profile','Chưa có'),E('account','return','Đã có'),E('profile','return','Đã lưu hồ sơ',[[890,430],[890,460],[530,460],[530,490]]),E('expired','open','Xác thực lại',[[170,490],[170,85],[390,85]],'retry'),E('return','merge','Chỉ khi có lịch sử khách',null,'optional')]
  },
  {
    id:'assessment',name:'Bài kiểm tra đầu vào',short:'Kiểm tra đầu vào',scope:'Thiết kế cho lộ trình; chưa phải sprint đã hoàn thành',
    summary:'Làm rõ mục tiêu, trả lời bộ tự luận và dùng kết quả có căn cứ để lập lộ trình.',
    reading:'Xác nhận mục tiêu → Làm bài → Rà soát → Lưu và đánh giá → Kết quả nền.',
    rules:['Bài đầu vào chỉ có tự luận kỹ thuật theo phạm vi hiện hành; không kế thừa trắc nghiệm/code từ ảnh UI cũ.','Số câu và thời lượng lấy từ bộ kiểm tra đã được duyệt; không mặc định là phiên bốn câu.','Nộp thiếu cần xác nhận; phần chưa làm được ghi rõ và không tự tính là 0.'],
    nodes:[
      N('intro',390,40,['Xác nhận mục tiêu kiểm tra'],['Vai trò · cấp độ · phạm vi đánh giá'],'extension',['L02'],{action:'Đọc hướng dẫn, số câu, thời lượng nếu đã cấu hình và tác động của việc kiểm tra lại.',next:'Bắt đầu lượt mới sau xác nhận hoặc tiếp tục lượt đang dở; giữ kết quả cũ.'}),
      N('write',390,190,['Trả lời các câu tự luận'],['Chuyển câu · lưu tiến độ · giữ nháp'],'extension',['L03'],{action:'Nhập câu trả lời cho từng câu, theo dõi câu đã làm và trạng thái lưu.',next:'Rà soát trước khi nộp. Rời giữa chừng có lựa chọn giữ tiến độ; mở lại không tự nộp.'}),
      N('resume',30,190,['Lưu và thoát / tiếp tục'],['Mở lại đúng lượt và đúng câu'],'step',[],{action:'Chọn lưu và thoát; chỉ xác nhận lưu sau phản hồi thành công.',next:'Lần sau cho tiếp tục lượt cũ hoặc xác nhận tạo lượt khác, giữ lượt trước.'}),
      N('review',390,340,['Rà soát: đã trả lời đủ?'],['Xem danh sách câu còn trống'],'decision',[],{action:'Hiển thị các câu còn thiếu trước nút xác nhận nộp.',next:'Đủ → xác nhận nộp. Thiếu → quay lại làm hoặc xác nhận nộp phần đã có theo chính sách được duyệt.'}),
      N('missing',750,340,['Còn câu chưa trả lời'],['Làm tiếp hoặc xác nhận nộp thiếu'],'decision',[],{action:'Nêu số câu chưa làm và giới hạn của kết quả nếu nộp lúc này.',next:'Làm tiếp quay về bài; nộp thiếu chỉ tiếp tục khi đã xác nhận.',note:'Quyền nộp thiếu là đề xuất cần nhóm duyệt, không phải chính sách đã triển khai.'}),
      N('submit',390,490,['Nộp và đánh giá bài đã lưu'],['Trích bằng chứng → đối chiếu rubric'],'extension',[],{action:'Xác nhận lưu trước khi đánh giá từng bài; AI diễn giải, Service kiểm tra và tính điểm.',next:'Đủ căn cứ → có điểm. Thiếu căn cứ → giữ chưa xác định. Lỗi hệ thống → thử lại trên bài đã lưu.'}),
      N('failure',750,490,['Lưu / AI gặp lỗi'],['Giữ bài, đối soát và thử lại'],'error',[],{action:'Phân biệt chưa lưu được với đã lưu nhưng chưa đánh giá được.',next:'Thử lại đúng bước có giới hạn; giữ các kết quả câu đã có, không chạy lại toàn bộ hoặc gán điểm 0.'}),
      N('result',390,640,['Xem kết quả đầu vào'],['Kỹ năng đã kiểm tra · phần còn thiếu'],'result',['L04'],{action:'Đọc kết quả theo phạm vi câu đã làm, bằng chứng và giới hạn của đánh giá.',next:'Đủ dữ liệu phù hợp → mở lộ trình; thiếu → bổ sung phần còn thiếu, giữ kết quả hiện có.'}),
      N('roadmap',30,640,['Mở lộ trình cá nhân hóa'],['Chỉ đề xuất phần có căn cứ'],'destination',[],{action:'Dùng kết quả đã xác nhận để chọn mục học có nguồn và tiên quyết.',next:'Chuyển sang trang Lộ trình cá nhân hóa.',go:'roadmap'}),
      N('add',750,640,['Bổ sung phần còn thiếu'],['Làm thêm / thử lại bài lỗi'],'extension',[],{action:'Xem kỹ năng nào chưa có đủ dữ liệu và lý do.',next:'Tạo lượt bổ sung có xác nhận hoặc thử lại bài đã lưu bị lỗi; không xóa kết quả cũ.'})
    ],
    edges:[E('intro','write','Đã xác nhận'),E('write','resume','Tạm dừng'),E('write','review','Rà soát nộp'),E('review','missing','Chưa đủ'),E('missing','write','Làm tiếp',[[890,340],[890,235],[670,235]],'retry'),E('review','submit','Đủ; xác nhận nộp'),E('missing','submit','Xác nhận nộp thiếu',[[890,430],[890,465],[530,465],[530,490]]),E('submit','failure','Có lỗi'),E('submit','result','Đã có kết quả'),E('result','roadmap','Đủ căn cứ'),E('result','add','Chưa đủ')]
  }
];

// UI-2026-11-10.2 supersedes the old text-only inventory's behavior.
const findPage=id=>pages.find(p=>p.id===id);
const findNode=(p,id)=>p.nodes.find(n=>n.id===id);
const voiceDetail={action:'Chọn Ghi âm, bấm Bắt đầu để xin quyền mic; Dừng rồi Nghe thử, Thu lại hoặc Chuyển thành văn bản.',next:'Xem/sửa transcript, chọn block và bấm Dùng transcript để đưa vào nháp. Sau đó mới bấm Nộp bài.',note:'Không chấm âm thanh. Từ chối mic/STT lỗi luôn quay về Văn bản; không ghi đè nháp mới hoặc tự nộp. Audio chỉ lưu tạm, server TTL tối đa 1 giờ.'};
const chatDetail={action:'Hỏi rõ đề; Guided/luyện câu cho xin gợi ý theo mức. Gửi chat chỉ tạo tin nhắn trong đúng thread.',next:'Đọc phản hồi rồi tiếp tục tự soạn bài. Không chèn đáp án AI vào nháp hoặc tạo bài nộp.',note:'Simulation/đầu vào không có hint nội dung trước nộp. Chia sẻ nháp phải chủ động; chat lỗi không chặn Lưu/Nộp bài.'};
{
 const p=findPage('questions');p.scope='Thiết kế theo UI ZIP · chưa triển khai';p.summary='Chọn câu, trả lời bằng văn bản hoặc transcript đã xác nhận; hỏi trợ lý và xem căn cứ.';
 p.rules=['Ba thao tác độc lập: Gửi chat, Dùng transcript và Nộp bài.','Nháp có revision; bài đã nộp bất biến. Không chấm audio hoặc lời AI trong chat.','Quay thư viện giữ filter/scroll; luyện lại tạo lượt mới.'];
 Object.assign(findNode(p,'write'),{title:['Soạn và nộp câu trả lời'],caption:['Văn bản / STT đã xác nhận']});
 findNode(p,'write').detail={action:'Soạn các khối luận điểm; thêm, di chuyển, xóa có xác nhận. Chọn gõ hoặc chèn transcript đã xem/sửa.',next:'Nộp khóa snapshot nháp đã xác nhận; lưu Answer trước đánh giá. Gửi chat và Lưu nháp không nộp bài.'};
 p.nodes.push(N('voice',750,340,['Ghi âm → xác nhận transcript'],['Bắt đầu · Dừng · Sửa · Dùng'],'step',[],voiceDetail),N('chat',30,490,['Chat trợ lý riêng'],['Hỏi rõ · xin gợi ý có giới hạn'],'step',[],chatDetail));
 p.edges.push(E('write','voice','Chọn ghi âm',[[670,535],[710,535],[710,385],[750,385]]),E('voice','write','Dùng transcript',[[890,430],[890,450],[690,450],[690,490],[670,490]],'retry'),E('write','chat','Gửi chat'));
 p.edges.find(e=>e.from==='again'&&e.to==='setup').points=[[30,685],[10,685],[10,385],[390,385]];
}
{
 const p=findPage('interview');p.scope='Thiết kế hai mode theo ZIP · input text/STT độc lập';
 p.rules=['Bốn nhóm tự luận; số câu/thời gian minh họa trong ảnh không tự thành cấu hình.','Guided: gợi ý theo yêu cầu, phản hồi từng câu. Simulation: chỉ clarification, phản hồi cuối phiên.','Hết giờ nếu có timer: giữ nháp riêng, không tự nộp bản ghi/transcript chưa xác nhận.'];
 findNode(p,'write').detail={action:'Soạn văn bản hoặc ghi âm, xem/sửa và Dùng transcript. Khung chat riêng theo policy mode; lưu nháp không nộp bài.',next:'Nộp → xác nhận đã lưu. Guided mở phản hồi từng câu; Simulation chỉ báo đã nhận. Backend cũng chặn điểm trước kết thúc.'};
 p.nodes.push(N('voice',750,340,['Văn bản hoặc ghi âm'],['Transcript phải được xác nhận'],'step',[],voiceDetail),N('chat',30,490,['Gửi tin cho trợ lý'],['Không phải nút nộp câu trả lời'],'step',[],chatDetail));
 p.edges.push(E('write','voice','Đổi cách nhập'),E('voice','write','Dùng transcript',[[890,340],[890,310],[670,310],[670,340]],'retry'),E('write','chat','Chat',[[390,385],[340,385],[340,535],[310,535]]));
 p.edges.find(e=>e.from==='exit'&&e.to==='summary').points=[[30,385],[10,385],[10,685],[390,685]];
}
{
 const p=findPage('roadmap');p.scope='Thiết kế từ kết quả đầu vào ba phần';
 p.summary='Dùng kết quả trắc nghiệm, tự luận và tình huống để xem trước, kích hoạt và học theo lộ trình.';
 findNode(p,'choose').detail={action:'Xem kế hoạch đề xuất và lý do từ evidence/tiên quyết; tùy chỉnh mục tiêu hoặc ngân sách rồi xác nhận Kích hoạt.',next:'Chỉ khi kích hoạt thành công mới đổi active plan; giữ bản cũ. Chọn chặng/node để học nguồn và luyện bài liên quan.'};
 findNode(p,'learn').detail.action='Học nguồn rồi kiểm tra mục bằng tự luận; chọn văn bản hoặc STT đã xác nhận. Tự đánh dấu đã biết chỉ là self-report.';
 p.rules=['Preview khác active plan; bấm Kích hoạt mới đổi kế hoạch, retry không tạo trùng.','Thiếu kết quả đầu vào: chỉ xem trước và bổ sung phần thiếu, không dựng năng lực giả.','Thứ tự theo prerequisite, phát hiện chu trình/ngân sách không đủ; XP không mở khóa.'];
}
{
 const p=findPage('overview');p.scope='Thiết kế dữ liệu thật · lịch sử và tiếp tục đúng owner';
 p.rules=['Luyện ngay / Tiếp tục / Xem bài dẫn đúng câu, phiên hoặc assessment.','Bài nguồn ghi âm xem transcript đã nộp; Luyện lại tạo lượt mới, không có kho audio.','Lịch theo timezone cấu hình; điểm danh khác học, không tự cộng XP khi mở trang.'];
 findNode(p,'history').detail={action:'Lọc bài/phiên/assessment, xem chi tiết, transcript và bằng chứng đúng revision; cuộn rail không thay dữ liệu.',next:'Viết lại/Luyện lại tạo lượt mới; đóng chi tiết giữ filter/scroll/tháng-ngày. Không có nút nghe clip đã xóa.'};
}
{
 const p=findPage('login');p.scope='Thiết kế theo auth 40/60: Google + email + khách';
 p.summary='Đăng nhập Google hoặc email; tạo tài khoản, khôi phục mật khẩu và quay đúng đích.';
 p.reading='Chọn Google / email / khách → Xác thực hoặc xác minh → Trở đúng trang đích.';
 p.rules=['Google và email/mật khẩu theo ZIP; trường .edu.vn/discount/GitHub chưa triển khai thì ẩn.','Tạo tài khoản cần xác minh email; reset dùng token có hạn, dùng một lần.','Liên kết lịch sử khách cần xác nhận; không tự gộp theo email, không lưu mật khẩu vào storage.'];
 findNode(p,'google').detail.note='Khách và email là các lựa chọn độc lập. Ghi nhớ phiên chỉ đổi TTL cookie theo config, không lưu mật khẩu.';
 findNode(p,'account').detail={action:'Server kiểm tra identity và tài khoản sau xác thực, không tin owner/email do client tự khai.',next:'Có hồ sơ → quay đúng đích. Lần đầu → xác nhận hồ sơ tối thiểu. Google/email không tự gộp theo địa chỉ email.'};
 p.nodes.push(N('email',30,190,['Đăng nhập bằng email'],['Email · mật khẩu · ghi nhớ phiên'],'step',[],{action:'Validate form rồi xác thực server; icon mắt chỉ đổi hiển thị, không gọi server.',next:'Đúng credential → rotate session và kiểm tra hồ sơ. Sai → thông báo chung/rate limit, giữ email, không log mật khẩu.'}),N('reset',30,340,['Quên mật khẩu'],['Yêu cầu link → đặt mật khẩu mới'],'step',[],{action:'Gửi yêu cầu reset có phản hồi trung tính; kiểm tra token có hạn/dùng một lần khi đặt lại.',next:'Reset thành công về đăng nhập. Link lỗi/hết hạn cho yêu cầu lại; không tự đăng nhập.'}),N('register',750,40,['Tạo tài khoản'],['Thông tin tối thiểu · xác minh email'],'step',[],{action:'Đổi tab Tạo tài khoản, nhập tên/email/mật khẩu và chấp thuận điều khoản; gửi yêu cầu tạo.',next:'Xác minh email theo link có hạn rồi đăng nhập; Google lần đầu dùng provider identity đã xác thực. Không thu CV.'}));
 p.edges.push(E('open','email','Chọn email',[[390,85],[340,85],[340,235],[310,235]]),E('email','account','Thành công',[[310,235],[350,235],[350,385],[390,385]]),E('email','reset','Quên mật khẩu'),E('open','register','Tạo tài khoản'),E('register','google','Sau xác minh',[[890,130],[890,150],[530,150],[530,190]],'retry'));
}
{
 const p=findPage('assessment');p.scope='Thiết kế theo ZIP · người dùng xác nhận ba loại câu';
 p.summary='Ba phần: trắc nghiệm, tự luận và tình huống; xác nhận nộp rồi dùng kết quả để lập kế hoạch.';
 p.rules=['Trắc nghiệm đúng theo key, sai = 0, chưa chọn = unanswered; không gọi LLM chấm choice.','Tự luận/tình huống có Văn bản hoặc Ghi âm→sửa/xác nhận transcript. Chat không gợi ý nội dung trước nộp.','Nộp thiếu có xác nhận và coverage; tổng null khi partial/unknown/failed, không renormalize phần đã làm.'];
 findNode(p,'write').title=['Làm bài kiểm tra ba phần'];findNode(p,'write').caption=['Trắc nghiệm · tự luận · tình huống'];
 findNode(p,'write').detail={action:'Chọn option ở trắc nghiệm; soạn blocks hoặc chèn transcript đã xác nhận ở tự luận/case. Tab/số câu/Câu trước giữ nháp, không nộp.',next:'Lưu & sang câu tiếp chỉ lưu draft; Nộp bài mở rà soát. Không khóa case chỉ vì phần trước chưa xong; chat chỉ thao tác/làm rõ trung tính.'};
 findNode(p,'missing').detail.note='Người dùng xác nhận nộp thiếu thì lưu snapshot partial; phần chưa làm không tính 0.';
 findNode(p,'submit').detail={action:'Server đếm lại câu trống và kiểm tra revision; xác nhận full/partial tạo snapshot atomic, khóa sửa mọi response.',next:'Choice so key đã review; tự luận/case diễn giải→xác thực→rubric. Lỗi từng item retry đúng snapshot, không chấm lại tất cả hoặc sửa đáp án.'};
 findNode(p,'result').detail={action:'Xem đáp án đối chiếu choice sau nộp, tiêu chí/quote tự luận, điểm từng item, completion và coverage riêng.',next:'Chỉ có tổng khi đủ required và evidence; partial/failed/unknown tổng null. Preview/Tùy chỉnh/Kích hoạt lộ trình là các thao tác riêng.'};
}

const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function pointsFor(a,b) {
  if (a.x === b.x) return [[a.x+a.w/2,a.y+a.h],[b.x+b.w/2,b.y]];
  if (a.y === b.y) return a.x < b.x ? [[a.x+a.w,a.y+a.h/2],[b.x,b.y+b.h/2]] : [[a.x,a.y+a.h/2],[b.x+b.w,b.y+b.h/2]];
  throw Error('Manual route required: '+a.id+' -> '+b.id);
}
function svgFor(p, standalone=false) {
  const dict = Object.fromEntries(p.nodes.map(n=>[n.id,n]));
  const edges = p.edges.map((e,i)=>{
    if (!dict[e.from] || !dict[e.to]) throw Error('Unknown edge '+p.id);
    const pts=e.points || pointsFor(dict[e.from],dict[e.to]);
    const a=pts[0], b=pts[1], vertical=a[0]===b[0];
    let lx=(a[0]+b[0])/2, ly=(a[1]+b[1])/2-8;
    if(vertical) {lx+=12; ly+=6;}
    const words=e.label.split(' '), lines=[];let line='';
    for(const word of words){if(line && (line+' '+word).length>(vertical?34:12)){lines.push(line);line=word;}else line+=(line?' ':'')+word;}if(line)lines.push(line);
    const width=Math.max(...lines.map(t=>t.length),0)*6.1+8;
    const label=e.label ? `<g class="edge-label"><rect x="${vertical?lx-4:lx-width/2}" y="${ly-13-(lines.length-1)*13}" width="${width}" height="${lines.length*13+5}" rx="3"/><text text-anchor="${vertical?'start':'middle'}">${lines.map((t,j)=>`<tspan x="${lx}" y="${ly+1-(lines.length-1-j)*13}">${esc(t)}</tspan>`).join('')}</text></g>`:'';
    return `<g class="edge ${e.kind}"><path d="${pts.map((v,j)=>(j?'L':'M')+v.join(',')).join(' ')}" marker-end="url(#arrow-${p.id})"/>${label}</g>`;
  }).join('');
  const nodes=p.nodes.map((n,i)=>{
    const label=({step:'Bước thực hiện',extension:'Thiết kế mở rộng',decision:'Điều kiện / lựa chọn',result:'Kết quả',error:'Nhánh lỗi / ngoại lệ',destination:'Chuyển trang'})[n.type];
    const shape=n.type==='decision' ? `<path class="box" d="M${n.x+18},${n.y} H${n.x+n.w-18} L${n.x+n.w},${n.y+45} L${n.x+n.w-18},${n.y+90} H${n.x+18} L${n.x},${n.y+45} Z"/>` : `<rect class="box" x="${n.x}" y="${n.y}" width="${n.w}" height="90" rx="10"/>`;
    return `<g class="node ${n.type}" data-node="${n.id}" tabindex="0" role="button" aria-label="${esc(n.title.join(' '))}: ${esc(n.caption.join(' '))}" aria-pressed="false">${shape}<text class="node-kind" x="${n.x+20}" y="${n.y+21}">${esc(label)}</text><text class="node-title" x="${n.x+20}" y="${n.y+47}">${esc(n.title.join(' '))}</text><text class="node-caption" x="${n.x+20}" y="${n.y+70}">${esc(n.caption.join(' '))}</text></g>`;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1060 770" role="group" aria-label="Sơ đồ ${esc(p.name)}" class="flow-svg"><title>User flow — ${esc(p.name)}</title><desc>${esc(p.reading)} Chọn một khối để xem chi tiết.</desc><defs><marker id="arrow-${p.id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#69778d"/></marker></defs><style>${svgCss}</style><rect width="1060" height="770" fill="white"/>${edges}${nodes}</svg>`;
}
const svgCss = `.flow-svg{font-family:'Segoe UI',Arial,sans-serif}.edge path{fill:none;stroke:#69778d;stroke-width:1.7;stroke-linejoin:round}.edge.retry path{stroke-dasharray:5 4}.edge.optional path{stroke-dasharray:2 5}.edge-label rect{fill:#fff;opacity:.97}.edge-label text{font-size:11px;fill:#475569}.node{cursor:pointer;outline:none}.node .box{fill:#f5f3ff;stroke:#8b76bd;stroke-width:1.4}.node.extension .box{fill:#f8fafc;stroke:#9ca9ba;stroke-dasharray:5 3}.node.decision .box{fill:#fff8e7;stroke:#b58b30}.node.error .box{fill:#fff3ef;stroke:#c78570}.node.result .box{fill:#edf9f5;stroke:#478b77}.node.destination .box{fill:#eef4ff;stroke:#7792bd}.node-kind{font-size:10.5px;fill:#596579}.node-title{font-size:16px;font-weight:650;fill:#1e293b}.node-caption{font-size:12px;fill:#4d5b70}.node:hover .box{stroke:#594090;stroke-width:2.5}.node:focus .box,.node[aria-pressed=true] .box{stroke:#593699;stroke-width:3.5}.node[aria-pressed=true] .node-title{fill:#50317f}`;
for (const p of pages) {
  if (new Set(p.nodes.map(n=>n.id)).size!==p.nodes.length) throw Error('Duplicate node');
  for(const n of p.nodes) {
    for(const id of n.refs) if(!screens[id]) throw Error('Unknown screen '+id);
    for(const target of [...(n.detail.links||[]), ...(n.detail.go?[n.detail.go]:[])]) if(!pages.some(p=>p.id===target)) throw Error('Unknown page '+target);
  }
  p.svg=svgFor(p);
}
const { renderFlowPage } = require('./render_p02_flow.cjs');
fs.writeFileSync(path.join(__dirname, '..', 'p02-user-flow.html'), renderFlowPage(pages));
fs.writeFileSync(path.join(__dirname,'user_flow_pages.data.json'),JSON.stringify(pages,null,2)+'\n');
const out=path.join(__dirname,'user_flow_diagrams');fs.mkdirSync(out,{recursive:true});
for(const p of pages) fs.writeFileSync(path.join(out,p.id+'.svg'),p.svg);
const scopedPlan=`# P02 — User flow sáu khu vực

Cập nhật 10/11/2026. Phạm vi lần này **chỉ P02 và P06** theo yêu cầu mới nhất. Không mở rộng backlog, sửa P03/P04, triển khai backend hoặc commit. Đây là thiết kế để review; chưa có phê duyệt nghiệp vụ của cả nhóm.

## Mở sơ đồ P02

[p02-user-flow.html](../p02-user-flow.html) mở trực tiếp trên trình duyệt. Chọn một trong sáu khu vực, rồi bấm vào từng khối để xem thao tác và hướng đi.

## Hành trình từng khu vực

${pages.map((p,i)=>`${i+1}. **${p.name}** — ${p.reading}\n   [Sơ đồ SVG](user_flow_diagrams/${p.id}.svg)`).join('\n\n')}

## Luồng nối trang

- Đăng nhập/khách → Tổng quan hoặc thư viện. Google/email/register/reset chỉ mô phỏng chuyển trạng thái, không xác thực thật.
- Thư viện → chi tiết → xác nhận mục tiêu → làm một câu → bài đã nộp/kết quả mẫu → luyện lại, Tổng quan hoặc Lộ trình.
- Phiên phỏng vấn → chọn mode → xác nhận → bốn nhóm câu → lưu từng bài → tổng kết → mở lại từng bài. Guided xem mẫu từng câu, Simulation cuối phiên.
- Bài đầu vào → mục tiêu → ba phần (trắc nghiệm/tự luận/tình huống) → rà câu thiếu → xác nhận full/partial → kết quả mẫu → Lộ trình.
- Lộ trình → xem trước/kích hoạt mẫu → mục học → câu liên quan → kết quả → Tổng quan. Nội dung kế hoạch chưa được cá nhân hóa bằng thuật toán.
- Tổng quan → tiếp tục phiên/đầu vào, xem bài gốc hoặc luyện lại; ngày/tháng và điểm danh chỉ đổi trạng thái demo.

## Những quy tắc UX phải thấy được

Gửi chat, Dùng bản phiên âm và Nộp bài là ba nút độc lập. Ghi âm là mô phỏng STT với bước sửa/xác nhận; không bật mic thật. Chat không biến thành Answer; hướng dẫn và mô phỏng có phạm vi trợ giúp khác nhau. Lỗi lưu giữ nháp, lỗi phản hồi giữ bài đã nộp. Câu chưa trả lời khác điểm 0. Kết quả mẫu có nhãn; không có chấm năng lực thật.

Chi tiết từng nút/nhánh lỗi: [USE_CASES.md](USE_CASES.md). Thiết kế, token, breakpoint và acceptance P06: [ui_direction.md](ui_direction.md). Những giới hạn thời gian, retention, threshold và policy tài khoản nêu trong use case là đề xuất bàn giao cho owner nghiệp vụ, không tự sửa spec/backlog trong hai task này.

## Tư duy tính toán

Phân rã sáu khu vực/ba luồng nhập-chat-nộp. Nhận diện mẫu trạng thái nháp/lỗi/thử lại/quay lại. Trừu tượng hóa bước người học nhìn thấy, chi tiết trong panel. Thiết kế thuật toán ở mức flow quyết định đủ câu, còn câu, có dữ liệu nền và đúng thời điểm mở kết quả; chưa triển khai thuật toán sản phẩm.
`;
fs.writeFileSync(path.join(__dirname,'user_flow.md'),scopedPlan);
fs.writeFileSync(path.join(__dirname,'user_flow_pages.md'),'# Sơ đồ P02\n\nMở [p02-user-flow.html](../p02-user-flow.html). Luồng ở [user_flow.md](user_flow.md) và chi tiết nút ở [USE_CASES.md](USE_CASES.md).\n');
console.log(JSON.stringify({pages:pages.length,nodes:pages.reduce((a,p)=>a+p.nodes.length,0),edges:pages.reduce((a,p)=>a+p.edges.length,0),data:'docs/user_flow_pages.data.json',svg:pages.map(p=>p.id+'.svg')}));
