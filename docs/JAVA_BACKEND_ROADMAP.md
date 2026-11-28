# Lộ trình Java Backend — bài đọc và bài tập có nguồn

Phiên bản **2026.11.27-v1** · Kiểm tra nguồn ngày **2026-11-27**.

## Phạm vi và cách sử dụng

- Mỗi lesson có nhiều bài học nhỏ; mở link nguồn để đọc, không có giáo trình lý thuyết do AI viết lại.
- Bài bắt buộc dùng tài liệu đọc công khai và thực hành local; không cần mua khóa Coursera hoặc kích hoạt cloud trial.
- Ngày truy cập không phải ngày xuất bản. Ưu tiên bản 2024–2026 và tài liệu đang duy trì; ngày chưa xác định được giữ null trong JSON.
- MIT 6.102 bản 2024 dùng TypeScript: chỉ dùng tư duy kiểm thử/đặc tả; không gọi đây là khóa Java.
- Thời lượng do nhóm ước tính gồm đọc và thực hành. Đánh dấu đã học là tự khai, không phải điểm thành thạo.
- Đây là catalog học liệu mới; không thêm các bài này vào ngân hàng câu hỏi đã duyệt hoặc thay rubric đang dùng.
- Bài tập thực hiện ngoài app. App không nhận, chạy hoặc tự chấm code.

## Khóa học và chương trình đã tham khảo

| Chương trình | Nhà cung cấp | Truy cập | Phiên bản / lưu ý |
|---|---|---|---|
| [Dev.java learning paths](https://dev.java/learn/) | Oracle / Dev.java | Miễn phí đọc công khai | Maintained; checked 2026. Free public Java reading paths; not a certificate program. Original publication dates vary. |
| [Spring Getting Started Guides](https://spring.io/guides/) | Spring | Miễn phí đọc công khai | Maintained; checked 2026. Public step-by-step Java/Spring guides. This is a guide collection, not a single accredited course. |
| [Get started with Java on Azure](https://learn.microsoft.com/en-us/training/paths/get-started-java-azure/) | Microsoft Learn | Bài đọc miễn phí; cloud lab có thể mất phí | Maintained; checked 2026. Seven modules. Reading is free; Azure subscription/resources may incur costs. Do not default to retired Azure Spring Apps examples. |
| [6.102 Software Construction](https://web.mit.edu/6.102/www/sp24/) | MIT | Miễn phí đọc công khai | Spring 2024. Public readings and problem statements. Uses TypeScript, NOT Java; included only for transferable testing/specification/concurrency concepts. Tutors and grading may require MIT access. |
| [CS50 Introduction to Databases with SQL](https://cs50.harvard.edu/sql/) | Harvard | Miễn phí đọc công khai | 2024 entry redirects to maintained OCW. Public notes and problem sets; optional verified certificate has separate terms. SQL foundation, not a Java course. |
| [Spring Academy](https://spring.academy/) | Spring | Thông báo miễn phí từ 2024; cần đăng ký, chưa thử lab hiện tại | Official announcement 2024-04-10. Official 2024 announcement removed Pro subscription for eligible registered email addresses. Current authenticated lab access was not tested; all required lessons have public guide alternatives. |
| [IBM Java Developer Professional Certificate](https://www.coursera.org/professional-certificates/java-developer) | IBM / Coursera | Trả phí / preview giới hạn; chỉ tham khảo chương trình | Current catalog checked 2026; publication date not established. Curriculum reference only. Enroll for free is not evidence that full course, graded labs or certificate are free. No subscription/trial is required by this roadmap. |
| [Amazon Junior Software Developer Professional Certificate](https://www.coursera.org/professional-certificates/amazon-junior-software-developer) | Amazon / Coursera | Trả phí / preview giới hạn; chỉ tham khảo chương trình | Current catalog checked 2026; publication date not established. Seven-course program, used to compare Java/OOP/data/engineering coverage. Full access and certificate pricing depend on Coursera enrollment terms. |
| [Java Programming and Software Engineering Fundamentals](https://www.coursera.org/specializations/java-programming) | Duke / Coursera | Trả phí / preview giới hạn; chỉ tham khảo chương trình | Current catalog checked 2026; original course is older. Curriculum reference, not represented as a 2024 launch or fully free program. Public documentation replaces paid lessons in the default plan. |
| [Software Construction in Java, 6.005.1x](https://openlearninglibrary.mit.edu/courses/course-v1%3AMITx%2B6.005.1x%2B3T2016/about) | MIT Open Learning Library | Tài liệu cũ ngoài giai đoạn, bổ trợ tùy chọn | Site reports created 2021; older course identifier. Java-specific historical supplement outside 2024–2026. Not a required resource or a newly released course; enrollment availability was not tested. |

## Các chặng học

| Lesson | Chủ đề | Tiên quyết | Ước tính |
|---|---|---|---|
| [JB01](#jb01) | Môi trường Java, IDE và Maven | Không | 240 phút |
| [JB02](#jb02) | Cú pháp, kiểu dữ liệu và xử lý giá trị | JB01 | 240 phút |
| [JB03](#jb03) | OOP, interface và dữ liệu bất biến | JB02 | 240 phút |
| [JB04](#jb04) | Exception, thời gian và ranh giới dữ liệu | JB03 | 240 phút |
| [JB05](#jb05) | Generics, Collections và equals/hashCode | JB03 | 240 phút |
| [JB06](#jb06) | Lambda, Stream và phân tích chi phí | JB05 | 240 phút |
| [JB07](#jb07) | Đặc tả, bất biến và kiểm thử nền tảng | JB03 | 240 phút |
| [JB08](#jb08) | Concurrency, virtual thread và JVM tools | JB04, JB07 | 300 phút |
| [JB09](#jb09) | HTTP và hợp đồng REST API | JB02 | 240 phút |
| [JB10](#jb10) | SQL, truy vấn và quan hệ dữ liệu | JB02 | 240 phút |
| [JB11](#jb11) | Thiết kế schema, index và tối ưu truy vấn | JB10 | 240 phút |
| [JB12](#jb12) | Spring Core, Boot và cấu hình | JB01, JB03, JB04 | 240 phút |
| [JB13](#jb13) | REST Controller, validation và xử lý lỗi | JB09, JB12 | 240 phút |
| [JB14](#jb14) | JDBC, JPA và truy vấn repository | JB05, JB10, JB12 | 300 phút |
| [JB15](#jb15) | Transaction, isolation và tranh chấp dữ liệu | JB11, JB14 | 300 phút |
| [JB16](#jb16) | Spring Security, session và JWT | JB13 | 300 phút |
| [JB17](#jb17) | Kiểm thử web, database và tích hợp | JB07, JB13, JB14 | 300 phút |
| [JB18](#jb18) | Gọi dịch vụ ngoài và phục hồi lỗi | JB13, JB17 | 240 phút |
| [JB19](#jb19) | Cache, Redis và tính nhất quán | JB14, JB15 | 240 phút |
| [JB20](#jb20) | Messaging, scheduler và batch | JB15, JB18 | 360 phút |
| [JB21](#jb21) | Docker, build và CI cho Java | JB17 | 240 phút |
| [JB22](#jb22) | Quan sát hệ thống và kiểm tra hiệu năng | JB18, JB21 | 300 phút |
| [JB23](#jb23) | Capstone Java Backend và ôn phỏng vấn | JB15, JB16, JB17, JB21 | 600 phút |
| [JB24](#jb24) | Tùy chọn: cloud, microservices và reactive | JB20, JB22, JB23 | 360 phút |

<a id="jb01"></a>
## JB01 — Môi trường Java, IDE và Maven

Chặng: Java nền tảng. Tiên quyết: Không. Ước tính: 240 phút.
Kỹ năng: java.tooling.

### Các bài học nhỏ

- **JB01.U1 · Cài JDK và chạy ứng dụng đầu tiên:** [Getting Started with Java](https://dev.java/learn/first-steps/first-java-code/getting-started/) — Oracle / Dev.java.
- **JB01.U2 · Debug ứng dụng Java bằng VS Code:** [Getting Started with Java in VS Code](https://code.visualstudio.com/docs/java/java-tutorial) — Microsoft.
- **JB01.U3 · Build, test và đóng gói bằng Maven:** [Maven in 5 Minutes](https://maven.apache.org/guides/getting-started/maven-in-five-minutes.html) — Apache Maven.

### Bài tập áp dụng

- **JB01.P1 · Làm Maven in 5 Minutes** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Maven in 5 Minutes](https://maven.apache.org/guides/getting-started/maven-in-five-minutes.html).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB01.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Tạo một ứng dụng CLI ghi nhận chi tiêu, build bằng Maven và lưu hướng dẫn chạy cùng các lệnh kiểm tra phiên bản.
  - Nguồn: [Getting Started with Java](https://dev.java/learn/first-steps/first-java-code/getting-started/); [Getting Started with Java in VS Code](https://code.visualstudio.com/docs/java/java-tutorial); [Maven in 5 Minutes](https://maven.apache.org/guides/getting-started/maven-in-five-minutes.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb02"></a>
## JB02 — Cú pháp, kiểu dữ liệu và xử lý giá trị

Chặng: Java nền tảng. Tiên quyết: JB01. Ước tính: 240 phút.
Kỹ năng: java.language.values.

### Các bài học nhỏ

- **JB02.U1 · Biến, điều kiện, vòng lặp và method:** [Java Language Basics](https://dev.java/learn/language/constructs/basics/) — Oracle / Dev.java.
- **JB02.U2 · Chuỗi và giá trị số:** [Numbers and Strings](https://dev.java/learn/language/constructs/numbers-strings/) — Oracle / Dev.java.
- **JB02.U3 · Số tiền và quy tắc làm tròn:** [BigDecimal API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html) — Oracle.

### Bài tập áp dụng

- **JB02.P1 · Thử biểu thức với JShell** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [JShell — The Java Shell Tool](https://dev.java/learn/first-steps/first-java-code/jshell-tool/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB02.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Xử lý danh sách đơn hàng có dữ liệu rỗng, số lượng âm và số tiền thập phân; liệt kê kết quả mong đợi và giải thích quyết định validation.
  - Nguồn: [Java Language Basics](https://dev.java/learn/language/constructs/basics/); [Numbers and Strings](https://dev.java/learn/language/constructs/numbers-strings/); [BigDecimal API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb03"></a>
## JB03 — OOP, interface và dữ liệu bất biến

Chặng: Java nền tảng. Tiên quyết: JB02. Ước tính: 240 phút.
Kỹ năng: java.oop, java.immutability.

### Các bài học nhỏ

- **JB03.U1 · Đối tượng và đóng gói:** [Classes and Objects](https://dev.java/learn/language/oop/classes-objects/) — Oracle / Dev.java.
- **JB03.U2 · Interface và hợp đồng:** [Interfaces](https://dev.java/learn/language/oop/interfaces/) — Oracle / Dev.java.
- **JB03.U3 · Record và dữ liệu bất biến:** [Using Records to Model Immutable Data](https://dev.java/learn/language/oop/records/) — Oracle / Dev.java.
- **JB03.U4 · Kế thừa và lựa chọn composition:** [Inheritance](https://dev.java/learn/language/oop/inheritance/) — Oracle / Dev.java.

### Bài tập áp dụng

- **JB03.P1 · Thực hiện các ví dụ record** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Using Records to Model Immutable Data](https://dev.java/learn/language/oop/records/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB03.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Mô hình hóa giỏ hàng, tiền và phương thức vận chuyển; giải thích phần nào dùng interface, composition hoặc record và cách tránh lộ trạng thái có thể thay đổi.
  - Nguồn: [Classes and Objects](https://dev.java/learn/language/oop/classes-objects/); [Interfaces](https://dev.java/learn/language/oop/interfaces/); [Using Records to Model Immutable Data](https://dev.java/learn/language/oop/records/); [Inheritance](https://dev.java/learn/language/oop/inheritance/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb04"></a>
## JB04 — Exception, thời gian và ranh giới dữ liệu

Chặng: Java nền tảng. Tiên quyết: JB03. Ước tính: 240 phút.
Kỹ năng: java.exceptions, java.datetime.

### Các bài học nhỏ

- **JB04.U1 · Xử lý và phân loại exception:** [Exceptions](https://dev.java/learn/language/annotations-exceptions/exceptions/) — Oracle / Dev.java.
- **JB04.U2 · Thời điểm, múi giờ và khoảng thời gian:** [The Date Time API](https://dev.java/learn/api/date-time-regex/date-time/) — Oracle / Dev.java.
- **JB04.U3 · Hợp đồng, đầu vào không hợp lệ và kết quả đặc biệt:** [MIT 6.102: Specifications](https://web.mit.edu/6.102/www/sp24/classes/04-specifications/) — MIT.

### Bài tập áp dụng

- **JB04.P1 · Thực hiện ví dụ exception trong nguồn** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Exceptions](https://dev.java/learn/language/annotations-exceptions/exceptions/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB04.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Thiết kế nhập lịch hẹn có timezone: chỉ ra lỗi dữ liệu, lỗi hệ thống, xử lý thời điểm không hợp lệ và tài nguyên cần đóng khi thất bại.
  - Nguồn: [Exceptions](https://dev.java/learn/language/annotations-exceptions/exceptions/); [The Date Time API](https://dev.java/learn/api/date-time-regex/date-time/); [MIT 6.102: Specifications](https://web.mit.edu/6.102/www/sp24/classes/04-specifications/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb05"></a>
## JB05 — Generics, Collections và equals/hashCode

Chặng: Java nền tảng. Tiên quyết: JB03. Ước tính: 240 phút.
Kỹ năng: java.generics, java.collections.

### Các bài học nhỏ

- **JB05.U1 · Kiểu tổng quát và wildcard:** [Generics](https://dev.java/learn/language/fp/generics/) — Oracle / Dev.java.
- **JB05.U2 · List, Set, Map và lựa chọn cấu trúc:** [The Collections Framework](https://dev.java/learn/api/collections-and-streams/collections-framework/) — Oracle / Dev.java.
- **JB05.U3 · Hợp đồng equals/hashCode:** [Object: equals and hashCode API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html) — Oracle.

### Bài tập áp dụng

- **JB05.P1 · Thử các ví dụ Collections** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [The Collections Framework](https://dev.java/learn/api/collections-and-streams/collections-framework/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB05.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Thiết kế danh mục sản phẩm không trùng ID và hàng đợi xử lý đơn; so sánh cấu trúc dữ liệu và kiểm tra trường hợp hai đối tượng bằng nhau nhưng khác identity.
  - Nguồn: [Generics](https://dev.java/learn/language/fp/generics/); [The Collections Framework](https://dev.java/learn/api/collections-and-streams/collections-framework/); [Object: equals and hashCode API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb06"></a>
## JB06 — Lambda, Stream và phân tích chi phí

Chặng: Java nền tảng. Tiên quyết: JB05. Ước tính: 240 phút.
Kỹ năng: java.streams, java.algorithms.complexity.

### Các bài học nhỏ

- **JB06.U1 · Functional interface và lambda:** [Lambda Expressions](https://dev.java/learn/language/fp/lambdas/) — Oracle / Dev.java.
- **JB06.U2 · Pipeline Stream và Collector:** [The Stream API](https://dev.java/learn/api/collections-and-streams/streams/) — Oracle / Dev.java.
- **JB06.U3 · Chi phí thao tác trên Collections:** [The Collections Framework](https://dev.java/learn/api/collections-and-streams/collections-framework/) — Oracle / Dev.java.

### Bài tập áp dụng

- **JB06.P1 · Thực hiện ví dụ Stream và Collector** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [The Stream API](https://dev.java/learn/api/collections-and-streams/streams/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB06.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Tổng hợp doanh thu theo khách hàng, xử lý đơn trùng và danh sách rỗng; giải thích chi phí thời gian/bộ nhớ và tác hại của side effect.
  - Nguồn: [Lambda Expressions](https://dev.java/learn/language/fp/lambdas/); [The Stream API](https://dev.java/learn/api/collections-and-streams/streams/); [The Collections Framework](https://dev.java/learn/api/collections-and-streams/collections-framework/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb07"></a>
## JB07 — Đặc tả, bất biến và kiểm thử nền tảng

Chặng: Java nền tảng. Tiên quyết: JB03. Ước tính: 240 phút.
Kỹ năng: java.testing.design, java.design.contracts.

### Các bài học nhỏ

- **JB07.U1 · MIT 2024: partition và ranh giới kiểm thử:** [MIT 6.102: Testing](https://web.mit.edu/6.102/www/sp24/classes/02-testing/) — MIT.
- **JB07.U2 · MIT 2024: đặc tả hành vi:** [MIT 6.102: Specifications](https://web.mit.edu/6.102/www/sp24/classes/04-specifications/) — MIT.
- **JB07.U3 · JUnit: tổ chức kiểm thử Java:** [JUnit User Guide](https://docs.junit.org/6.1.3/overview.html) — JUnit.
- **JB07.U4 · MIT 2024: bất biến biểu diễn:** [MIT 6.102: Abstraction Functions & Rep Invariants](https://web.mit.edu/6.102/www/sp24/classes/07-abstraction-functions-rep-invariants/) — MIT.

### Bài tập áp dụng

- **JB07.P1 · Đọc và tự trả lời câu hỏi công khai trong MIT Testing** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [MIT 6.102: Testing](https://web.mit.edu/6.102/www/sp24/classes/02-testing/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB07.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Viết kế hoạch test cho hàm chuyển tiền hoặc tính phí, phân vùng đầu vào và nêu kết quả mong đợi; thực hiện test Java tại máy cá nhân nếu muốn.
  - Nguồn: [MIT 6.102: Testing](https://web.mit.edu/6.102/www/sp24/classes/02-testing/); [MIT 6.102: Specifications](https://web.mit.edu/6.102/www/sp24/classes/04-specifications/); [JUnit User Guide](https://docs.junit.org/6.1.3/overview.html); [MIT 6.102: Abstraction Functions & Rep Invariants](https://web.mit.edu/6.102/www/sp24/classes/07-abstraction-functions-rep-invariants/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb08"></a>
## JB08 — Concurrency, virtual thread và JVM tools

Chặng: Java nền tảng. Tiên quyết: JB04, JB07. Ước tính: 300 phút.
Kỹ năng: java.concurrency, java.jvm.

### Các bài học nhỏ

- **JB08.U1 · Executor, Future và đồng bộ:** [java.util.concurrent API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html) — Oracle.
- **JB08.U2 · Virtual thread và giới hạn tài nguyên:** [Virtual Threads](https://dev.java/learn/api/virtual-threads/) — Oracle / Dev.java.
- **JB08.U3 · Công cụ JVM và thread dump:** [The Core JDK Tools](https://dev.java/learn/jvm/core-tools/) — Oracle / Dev.java.
- **JB08.U4 · MIT 2024: race condition và mutual exclusion:** [MIT 6.102: Mutual Exclusion](https://web.mit.edu/6.102/www/sp24/classes/16-mutual-exclusion/) — MIT.

### Bài tập áp dụng

- **JB08.P1 · Thử các ví dụ virtual thread** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Virtual Threads](https://dev.java/learn/api/virtual-threads/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB08.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Mô phỏng nhiều yêu cầu cập nhật một bộ đếm, so sánh sai lệch trước/sau đồng bộ; phân biệt giới hạn CPU với giới hạn kết nối database.
  - Nguồn: [java.util.concurrent API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html); [Virtual Threads](https://dev.java/learn/api/virtual-threads/); [The Core JDK Tools](https://dev.java/learn/jvm/core-tools/); [MIT 6.102: Mutual Exclusion](https://web.mit.edu/6.102/www/sp24/classes/16-mutual-exclusion/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb09"></a>
## JB09 — HTTP và hợp đồng REST API

Chặng: Web và dữ liệu. Tiên quyết: JB02. Ước tính: 240 phút.
Kỹ năng: backend.http, backend.api.design.

### Các bài học nhỏ

- **JB09.U1 · Luồng request/response:** [Overview of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) — MDN.
- **JB09.U2 · Method, tính an toàn và idempotency:** [HTTP request methods](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods) — MDN.
- **JB09.U3 · Status code và hợp đồng lỗi:** [HTTP response status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) — MDN.

### Bài tập áp dụng

- **JB09.P1 · Thử request bằng curl theo các ví dụ HTTP của MDN** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Overview of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB09.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Soạn hợp đồng API quản lý đơn hàng: URL, method, status, pagination và lỗi; phân tích gửi lặp một yêu cầu tạo đơn.
  - Nguồn: [Overview of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview); [HTTP request methods](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods); [HTTP response status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb10"></a>
## JB10 — SQL, truy vấn và quan hệ dữ liệu

Chặng: Web và dữ liệu. Tiên quyết: JB02. Ước tính: 240 phút.
Kỹ năng: backend.sql.query.

### Các bài học nhỏ

- **JB10.U1 · CS50: truy vấn và điều kiện:** [CS50 SQL: Querying](https://cs50.harvard.edu/sql/notes/0/) — Harvard CS50.
- **JB10.U2 · CS50: liên kết bảng và khóa:** [CS50 SQL: Relating](https://cs50.harvard.edu/sql/notes/1/) — Harvard CS50.
- **JB10.U3 · PostgreSQL: thực hành SQL:** [PostgreSQL Tutorial](https://www.postgresql.org/docs/16/tutorial.html) — PostgreSQL.

### Bài tập áp dụng

- **JB10.P1 · Làm CS50 SQL Problem Sets 0 và phần mở rộng ở bài đọc** (Đề gốc công khai). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [CS50 SQL Problem Set 0](https://cs50.harvard.edu/sql/psets/0/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB10.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Thiết kế truy vấn danh sách đơn theo khách hàng, bao gồm khách chưa có đơn và dữ liệu NULL; ghi kết quả mong đợi cho dữ liệu mẫu.
  - Nguồn: [CS50 SQL: Querying](https://cs50.harvard.edu/sql/notes/0/); [CS50 SQL: Relating](https://cs50.harvard.edu/sql/notes/1/); [PostgreSQL Tutorial](https://www.postgresql.org/docs/16/tutorial.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb11"></a>
## JB11 — Thiết kế schema, index và tối ưu truy vấn

Chặng: Web và dữ liệu. Tiên quyết: JB10. Ước tính: 240 phút.
Kỹ năng: backend.sql.design, backend.sql.performance.

### Các bài học nhỏ

- **JB11.U1 · CS50: thiết kế schema và ràng buộc:** [CS50 SQL: Designing](https://cs50.harvard.edu/sql/notes/2/) — Harvard CS50.
- **JB11.U2 · CS50: index và tối ưu:** [CS50 SQL: Optimizing](https://cs50.harvard.edu/sql/notes/5/) — Harvard CS50.
- **JB11.U3 · CS50: bài tập quan hệ dữ liệu:** [CS50 SQL Problem Set 1](https://cs50.harvard.edu/sql/psets/1/) — Harvard CS50.

### Bài tập áp dụng

- **JB11.P1 · Làm CS50 SQL Problem Set 5** (Đề gốc công khai). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [CS50 SQL Problem Set 5](https://cs50.harvard.edu/sql/psets/5/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB11.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Thiết kế schema đơn hàng có khóa và ràng buộc; đề xuất index cho hai truy vấn khác nhau, ghi execution plan và đánh đổi chi phí ghi.
  - Nguồn: [CS50 SQL: Designing](https://cs50.harvard.edu/sql/notes/2/); [CS50 SQL: Optimizing](https://cs50.harvard.edu/sql/notes/5/); [CS50 SQL Problem Set 1](https://cs50.harvard.edu/sql/psets/1/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb12"></a>
## JB12 — Spring Core, Boot và cấu hình

Chặng: Spring Backend. Tiên quyết: JB01, JB03, JB04. Ước tính: 240 phút.
Kỹ năng: spring.core, spring.boot.configuration.

### Các bài học nhỏ

- **JB12.U1 · IoC, bean và dependency injection:** [The IoC Container](https://docs.spring.io/spring-framework/reference/core/beans.html) — Spring.
- **JB12.U2 · Spring Boot: cấu hình theo môi trường:** [Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html) — Spring.
- **JB12.U3 · Blog Spring Boot 2024: cấu trúc và khả năng nền tảng:** [Bootiful Spring Boot in 2024, part 1](https://spring.io/blog/2024/03/11/bootiful-spring-boot-in-2024-part-1/) — Spring / Josh Long.
- **JB12.U4 · Blog 2025: module và starter khi chuyển Boot 4:** [Modularizing Spring Boot](https://spring.io/blog/2025/10/28/modularizing-spring-boot/) — Spring Boot Team.

### Bài tập áp dụng

- **JB12.P1 · Hoàn thành Building an Application with Spring Boot** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Building an Application with Spring Boot](https://spring.io/guides/gs/spring-boot/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB12.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Tách Controller/Service/Repository cho ứng dụng quản lý sách; giải thích constructor injection và cách cấu hình local/test mà không ghi secret vào mã.
  - Nguồn: [The IoC Container](https://docs.spring.io/spring-framework/reference/core/beans.html); [Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html); [Bootiful Spring Boot in 2024, part 1](https://spring.io/blog/2024/03/11/bootiful-spring-boot-in-2024-part-1/); [Modularizing Spring Boot](https://spring.io/blog/2025/10/28/modularizing-spring-boot/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb13"></a>
## JB13 — REST Controller, validation và xử lý lỗi

Chặng: Spring Backend. Tiên quyết: JB09, JB12. Ước tính: 240 phút.
Kỹ năng: spring.mvc, backend.api.validation.

### Các bài học nhỏ

- **JB13.U1 · Tạo REST endpoint:** [Building a RESTful Web Service](https://spring.io/guides/gs/rest-service/) — Spring.
- **JB13.U2 · Validation đầu vào:** [Validating Form Input](https://spring.io/guides/gs/validating-form-input/) — Spring.
- **JB13.U3 · Thiết kế tài nguyên và lỗi REST:** [Building REST services with Spring](https://spring.io/guides/tutorials/rest/) — Spring.

### Bài tập áp dụng

- **JB13.P1 · Hoàn thành Building REST services with Spring** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Building REST services with Spring](https://spring.io/guides/tutorials/rest/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB13.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Bổ sung hợp đồng lỗi cho tạo/sửa sách, phân biệt không tìm thấy, dữ liệu sai và xung đột; đề xuất kiểm tra quyền sở hữu và phân trang.
  - Nguồn: [Building a RESTful Web Service](https://spring.io/guides/gs/rest-service/); [Validating Form Input](https://spring.io/guides/gs/validating-form-input/); [Building REST services with Spring](https://spring.io/guides/tutorials/rest/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb14"></a>
## JB14 — JDBC, JPA và truy vấn repository

Chặng: Spring Backend. Tiên quyết: JB05, JB10, JB12. Ước tính: 300 phút.
Kỹ năng: spring.persistence.jpa, backend.jdbc.

### Các bài học nhỏ

- **JB14.U1 · JDBC và tài nguyên kết nối:** [Data Access with JDBC](https://docs.spring.io/spring-framework/reference/data-access/jdbc.html) — Spring.
- **JB14.U2 · Entity, repository và lưu trữ JPA:** [Accessing Data with JPA](https://spring.io/guides/gs/accessing-data-jpa/) — Spring.
- **JB14.U3 · Query methods và projection:** [JPA Query Methods](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html) — Spring.

### Bài tập áp dụng

- **JB14.P1 · Hoàn thành Accessing Data with JPA** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Accessing Data with JPA](https://spring.io/guides/gs/accessing-data-jpa/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB14.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Mô hình hóa khách hàng/đơn hàng, phân biệt DTO và entity; ghi những truy vấn cần chạy và cách nhận diện tải dữ liệu thừa trước khi tối ưu.
  - Nguồn: [Data Access with JDBC](https://docs.spring.io/spring-framework/reference/data-access/jdbc.html); [Accessing Data with JPA](https://spring.io/guides/gs/accessing-data-jpa/); [JPA Query Methods](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb15"></a>
## JB15 — Transaction, isolation và tranh chấp dữ liệu

Chặng: Spring Backend. Tiên quyết: JB11, JB14. Ước tính: 300 phút.
Kỹ năng: backend.sql.transactions, spring.transactions.

### Các bài học nhỏ

- **JB15.U1 · Transaction và rollback trong Spring:** [Managing Transactions](https://spring.io/guides/gs/managing-transactions/) — Spring.
- **JB15.U2 · Isolation và hành vi đọc/ghi:** [Transaction Isolation](https://www.postgresql.org/docs/16/transaction-iso.html) — PostgreSQL.
- **JB15.U3 · Khóa, deadlock và thứ tự truy cập:** [Explicit Locking and Deadlocks](https://www.postgresql.org/docs/16/explicit-locking.html) — PostgreSQL.
- **JB15.U4 · Proxy và @Transactional:** [Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html) — Spring.

### Bài tập áp dụng

- **JB15.P1 · Hoàn thành Managing Transactions** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Managing Transactions](https://spring.io/guides/gs/managing-transactions/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB15.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Phân tích hai yêu cầu mua sản phẩm cuối cùng: giữ bất biến tồn kho, rollback khi tạo đơn lỗi và xác minh bằng hai session database.
  - Nguồn: [Managing Transactions](https://spring.io/guides/gs/managing-transactions/); [Transaction Isolation](https://www.postgresql.org/docs/16/transaction-iso.html); [Explicit Locking and Deadlocks](https://www.postgresql.org/docs/16/explicit-locking.html); [Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb16"></a>
## JB16 — Spring Security, session và JWT

Chặng: Spring Backend. Tiên quyết: JB13. Ước tính: 300 phút.
Kỹ năng: spring.security, backend.security.authorization.

### Các bài học nhỏ

- **JB16.U1 · Filter chain và kiến trúc bảo mật:** [Spring Security Architecture](https://docs.spring.io/spring-security/reference/servlet/architecture.html) — Spring.
- **JB16.U2 · Resource server kiểm tra JWT:** [OAuth 2.0 Resource Server JWT](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html) — Spring.
- **JB16.U3 · Checklist bảo mật REST:** [REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) — OWASP.

### Bài tập áp dụng

- **JB16.P1 · Hoàn thành Securing a Web Application** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Securing a Web Application](https://spring.io/guides/gs/securing-web/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB16.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Thiết kế quyền xem/sửa đơn hàng: chủ sở hữu, quản trị viên, token hết hạn, ID đoán được; liệt kê ca kiểm tra quyền ở tầng tài nguyên.
  - Nguồn: [Spring Security Architecture](https://docs.spring.io/spring-security/reference/servlet/architecture.html); [OAuth 2.0 Resource Server JWT](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html); [REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb17"></a>
## JB17 — Kiểm thử web, database và tích hợp

Chặng: Spring Backend. Tiên quyết: JB07, JB13, JB14. Ước tính: 300 phút.
Kỹ năng: spring.testing.integration.

### Các bài học nhỏ

- **JB17.U1 · Spring Boot test support:** [Spring Boot Testing](https://docs.spring.io/spring-boot/reference/testing/index.html) — Spring.
- **JB17.U2 · MockMvc và kiểm thử web layer:** [Testing the Web Layer](https://spring.io/guides/gs/testing-web/) — Spring.
- **JB17.U3 · Testcontainers: database tạm cho test:** [JUnit 5 Quickstart](https://java.testcontainers.org/quickstart/junit_5_quickstart/) — Testcontainers.

### Bài tập áp dụng

- **JB17.P1 · Hoàn thành Testing the Web Layer** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Testing the Web Layer](https://spring.io/guides/gs/testing-web/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB17.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Xây ma trận test cho API đơn hàng: thành công, dữ liệu sai, truy cập chéo chủ sở hữu và rollback; nêu chỗ nào dùng mock, chỗ nào cần database thật.
  - Nguồn: [Spring Boot Testing](https://docs.spring.io/spring-boot/reference/testing/index.html); [Testing the Web Layer](https://spring.io/guides/gs/testing-web/); [JUnit 5 Quickstart](https://java.testcontainers.org/quickstart/junit_5_quickstart/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb18"></a>
## JB18 — Gọi dịch vụ ngoài và phục hồi lỗi

Chặng: Vận hành và mở rộng. Tiên quyết: JB13, JB17. Ước tính: 240 phút.
Kỹ năng: backend.integration.resilience.

### Các bài học nhỏ

- **JB18.U1 · RestClient và WebClient:** [REST Clients](https://docs.spring.io/spring-framework/reference/integration/rest-clients.html) — Spring.
- **JB18.U2 · Circuit breaker và giới hạn lỗi lan truyền:** [Spring Cloud Circuit Breaker Guide](https://spring.io/guides/gs/cloud-circuit-breaker/) — Spring.
- **JB18.U3 · Blog Boot 3.4: HTTP client và cấu hình:** [Bootiful Spring Boot 3.4: Spring Boot](https://spring.io/blog/2024/11/24/bootiful-34-boot/) — Spring / Josh Long.

### Bài tập áp dụng

- **JB18.P1 · Hoàn thành Spring Cloud Circuit Breaker Guide** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Spring Cloud Circuit Breaker Guide](https://spring.io/guides/gs/cloud-circuit-breaker/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB18.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Mô tả gọi dịch vụ vận chuyển bị timeout: giới hạn thời gian, retry có điều kiện, idempotency và cách giữ kết quả chưa rõ; không gọi API trả phí.
  - Nguồn: [REST Clients](https://docs.spring.io/spring-framework/reference/integration/rest-clients.html); [Spring Cloud Circuit Breaker Guide](https://spring.io/guides/gs/cloud-circuit-breaker/); [Bootiful Spring Boot 3.4: Spring Boot](https://spring.io/blog/2024/11/24/bootiful-34-boot/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb19"></a>
## JB19 — Cache, Redis và tính nhất quán

Chặng: Vận hành và mở rộng. Tiên quyết: JB14, JB15. Ước tính: 240 phút.
Kỹ năng: backend.caching.

### Các bài học nhỏ

- **JB19.U1 · Spring cache abstraction:** [Cache Abstraction](https://docs.spring.io/spring-framework/reference/integration/cache.html) — Spring.
- **JB19.U2 · Ví dụ cache chính thức của Spring:** [Caching Data with Spring](https://github.com/spring-guides/gs-caching) — Spring.
- **JB19.U3 · Redis data types:** [Redis data types](https://redis.io/docs/latest/develop/data-types/) — Redis.

### Bài tập áp dụng

- **JB19.P1 · Hoàn thành ví dụ gs-caching trong repo chính thức** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Caching Data with Spring](https://github.com/spring-guides/gs-caching).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB19.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Đề xuất cache danh mục sách: key, TTL, invalidation sau cập nhật và xử lý dữ liệu cũ; phân biệt cache cục bộ với cache chia sẻ.
  - Nguồn: [Cache Abstraction](https://docs.spring.io/spring-framework/reference/integration/cache.html); [Caching Data with Spring](https://github.com/spring-guides/gs-caching); [Redis data types](https://redis.io/docs/latest/develop/data-types/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb20"></a>
## JB20 — Messaging, scheduler và batch

Chặng: Vận hành và mở rộng. Tiên quyết: JB15, JB18. Ước tính: 360 phút.
Kỹ năng: backend.messaging, backend.batch.

### Các bài học nhỏ

- **JB20.U1 · Publisher/consumer với RabbitMQ:** [Messaging with RabbitMQ](https://spring.io/guides/gs/messaging-rabbitmq/) — Spring.
- **JB20.U2 · Lập lịch tác vụ:** [Scheduling Tasks](https://spring.io/guides/gs/scheduling-tasks/) — Spring.
- **JB20.U3 · Batch import CSV vào database:** [Creating a Batch Service](https://spring.io/guides/gs/batch-processing/) — Spring.

### Bài tập áp dụng

- **JB20.P1 · Hoàn thành Messaging with RabbitMQ** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Messaging with RabbitMQ](https://spring.io/guides/gs/messaging-rabbitmq/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB20.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Thiết kế gửi thông báo sau tạo đơn: message trùng, consumer lỗi, retry và dead-letter; giải thích cách tránh ghi nhận cùng sự kiện hai lần.
  - Nguồn: [Messaging with RabbitMQ](https://spring.io/guides/gs/messaging-rabbitmq/); [Scheduling Tasks](https://spring.io/guides/gs/scheduling-tasks/); [Creating a Batch Service](https://spring.io/guides/gs/batch-processing/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb21"></a>
## JB21 — Docker, build và CI cho Java

Chặng: Vận hành và mở rộng. Tiên quyết: JB17. Ước tính: 240 phút.
Kỹ năng: backend.delivery.containers, backend.delivery.ci.

### Các bài học nhỏ

- **JB21.U1 · Container: tài liệu Docker 2026:** [What is a container?](https://docs.docker.com/learn/content/what-is-a-container/) — Docker.
- **JB21.U2 · Đóng gói Spring Boot bằng Docker:** [Spring Boot with Docker](https://spring.io/guides/gs/spring-boot-docker/) — Spring.
- **JB21.U3 · Build/test Java bằng Maven trong CI:** [Building and testing Java with Maven](https://docs.github.com/en/actions/tutorials/build-and-test-code/java-with-maven) — GitHub / Microsoft.

### Bài tập áp dụng

- **JB21.P1 · Hoàn thành Spring Boot with Docker trên máy local** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Spring Boot with Docker](https://spring.io/guides/gs/spring-boot-docker/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB21.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Chuẩn bị hướng dẫn build/test và restart ứng dụng cùng database có volume; phân biệt image, container, secret và dữ liệu cần giữ. CI cloud là tùy chọn, không bắt buộc.
  - Nguồn: [What is a container?](https://docs.docker.com/learn/content/what-is-a-container/); [Spring Boot with Docker](https://spring.io/guides/gs/spring-boot-docker/); [Building and testing Java with Maven](https://docs.github.com/en/actions/tutorials/build-and-test-code/java-with-maven).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb22"></a>
## JB22 — Quan sát hệ thống và kiểm tra hiệu năng

Chặng: Vận hành và mở rộng. Tiên quyết: JB18, JB21. Ước tính: 300 phút.
Kỹ năng: backend.observability, java.jvm.performance.

### Các bài học nhỏ

- **JB22.U1 · Actuator và health endpoint:** [Building a RESTful Web Service with Spring Boot Actuator](https://spring.io/guides/gs/actuator-service/) — Spring.
- **JB22.U2 · Logging, metrics và traces:** [Spring Boot Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html) — Spring.
- **JB22.U3 · Java OpenTelemetry example:** [Java OpenTelemetry: Getting Started by Example](https://opentelemetry.io/docs/languages/java/getting-started/) — OpenTelemetry.
- **JB22.U4 · Blog 2026: Optimizations in Spring MVC:** [Optimizations in Spring MVC](https://spring.io/blog/2026/02/25/optimizing-spring-mvc/) — Spring / Dave Syer.

### Bài tập áp dụng

- **JB22.P1 · Hoàn thành Actuator service guide** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Building a RESTful Web Service with Spring Boot Actuator](https://spring.io/guides/gs/actuator-service/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB22.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Theo dõi một API chậm: ghi request ID, latency, số truy vấn và lỗi; dùng JFR hoặc công cụ local, không kết luận tối ưu chỉ từ một lần đo.
  - Nguồn: [Building a RESTful Web Service with Spring Boot Actuator](https://spring.io/guides/gs/actuator-service/); [Spring Boot Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html); [Java OpenTelemetry: Getting Started by Example](https://opentelemetry.io/docs/languages/java/getting-started/); [Optimizations in Spring MVC](https://spring.io/blog/2026/02/25/optimizing-spring-mvc/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb23"></a>
## JB23 — Capstone Java Backend và ôn phỏng vấn

Chặng: Vận hành và mở rộng. Tiên quyết: JB15, JB16, JB17, JB21. Ước tính: 600 phút.
Kỹ năng: java.backend.capstone, java.design.contracts.

### Các bài học nhỏ

- **JB23.U1 · Ứng dụng tham chiếu Spring Petclinic:** [Spring Petclinic sample application](https://github.com/spring-projects/spring-petclinic) — Spring.
- **JB23.U2 · MIT 2024: abstract data types và ranh giới module:** [MIT 6.102: Abstract Data Types](https://web.mit.edu/6.102/www/sp24/classes/06-abstract-data-types/) — MIT.
- **JB23.U3 · CS50: yêu cầu dự án dữ liệu:** [CS50 SQL Final Project](https://cs50.harvard.edu/sql/project/) — Harvard CS50.

### Bài tập áp dụng

- **JB23.P1 · Chạy Spring Petclinic local theo README** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Spring Petclinic sample application](https://github.com/spring-projects/spring-petclinic).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB23.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). Xây hoặc mô tả dịch vụ đặt lịch riêng: API, schema, transaction, quyền truy cập, test và deployment. Trả lời bằng lời các đánh đổi; dự án cá nhân không được chấm tự động trong app.
  - Nguồn: [Spring Petclinic sample application](https://github.com/spring-projects/spring-petclinic); [MIT 6.102: Abstract Data Types](https://web.mit.edu/6.102/www/sp24/classes/06-abstract-data-types/); [CS50 SQL Final Project](https://cs50.harvard.edu/sql/project/).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

<a id="jb24"></a>
## JB24 — Tùy chọn: cloud, microservices và reactive

Chặng: Nâng cao tùy chọn. Tiên quyết: JB20, JB22, JB23. Ước tính: 360 phút.
Kỹ năng: backend.cloud, backend.distributed, spring.reactive.

### Các bài học nhỏ

- **JB24.U1 · Microsoft Learn: Java trên Azure Container Apps:** [Deploy a Spring Boot app to Azure Container Apps](https://learn.microsoft.com/en-us/training/modules/java-spring-on-azure-container-apps/) — Microsoft Learn.
- **JB24.U2 · Service discovery: ví dụ hai dịch vụ:** [Service Registration and Discovery](https://spring.io/guides/gs/service-registration-and-discovery/) — Spring.
- **JB24.U3 · Spring WebFlux và mô hình reactive:** [Spring WebFlux](https://docs.spring.io/spring-framework/reference/web/webflux.html) — Spring.

### Bài tập áp dụng

- **JB24.P1 · Thực hiện service discovery local, không cần cloud** (Ví dụ/lab hoặc câu hỏi trong nguồn). Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.
  - Nguồn: [Service Registration and Discovery](https://spring.io/guides/gs/service-registration-and-discovery/).
  - Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp.
- **JB24.P2 · Vận dụng vào tình huống backend** (Bài vận dụng do nhóm biên soạn). So sánh modular monolith với tách dịch vụ cho bài capstone; nêu chi phí mạng, dữ liệu và vận hành. Chỉ đọc phần Azure; nếu tự triển khai cloud phải kiểm tra chi phí trước.
  - Nguồn: [Deploy a Spring Boot app to Azure Container Apps](https://learn.microsoft.com/en-us/training/modules/java-spring-on-azure-container-apps/); [Service Registration and Discovery](https://spring.io/guides/gs/service-registration-and-discovery/); [Spring WebFlux](https://docs.spring.io/spring-framework/reference/web/webflux.html).
  - Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.

## Quy tắc cá nhân hóa

1. Người học xác nhận chặng, mục tiêu và quỹ thời gian; có thể tự đánh dấu bài đã học.
2. Mở rộng mục tiêu bằng toàn bộ tiên quyết, phát hiện ID thiếu/chu trình và sắp topo bằng Service.
3. Chỉ hai nhóm kiến thức chuyển giao được nối với hồ sơ hiện tại: data consistency → JB15, complexity → JB06. Không chuyển điểm Python thành mức Java.
4. Kỹ năng chưa được quan sát không bị coi là yếu. Bằng chứng thiếu không thành điểm 0. Lựa chọn đã học là tự khai, không sửa hồ sơ đánh giá.
5. Chia thời gian tuần theo thứ tự tiên quyết; có thể tách một lesson qua nhiều tuần. Thiếu ngân sách phải liệt kê phần hoãn và số phút thiếu.
6. Các khóa trả phí, lab cloud và chứng chỉ không phải điều kiện của lộ trình mặc định.

## Sổ nguồn

Tất cả nguồn dưới đây chỉ được dẫn link và ghi metadata, không sao chép nội dung khóa. Các reference rolling có thể thay đổi; xem phiên bản dependency của từng lab.

- **java-start** · [Getting Started with Java](https://dev.java/learn/first-steps/first-java-code/getting-started/) · Oracle / Dev.java
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-shell** · [JShell — The Java Shell Tool](https://dev.java/learn/first-steps/first-java-code/jshell-tool/) · Oracle / Dev.java
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-basics** · [Java Language Basics](https://dev.java/learn/language/constructs/basics/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-strings** · [Numbers and Strings](https://dev.java/learn/language/constructs/numbers-strings/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-classes** · [Classes and Objects](https://dev.java/learn/language/oop/classes-objects/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-records** · [Using Records to Model Immutable Data](https://dev.java/learn/language/oop/records/) · Oracle / Dev.java
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-inheritance** · [Inheritance](https://dev.java/learn/language/oop/inheritance/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-interfaces** · [Interfaces](https://dev.java/learn/language/oop/interfaces/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-generics** · [Generics](https://dev.java/learn/language/fp/generics/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-lambda** · [Lambda Expressions](https://dev.java/learn/language/fp/lambdas/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-exceptions** · [Exceptions](https://dev.java/learn/language/annotations-exceptions/exceptions/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-collections** · [The Collections Framework](https://dev.java/learn/api/collections-and-streams/collections-framework/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-streams** · [The Stream API](https://dev.java/learn/api/collections-and-streams/streams/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-time** · [The Date Time API](https://dev.java/learn/api/date-time-regex/date-time/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-virtual** · [Virtual Threads](https://dev.java/learn/api/virtual-threads/) · Oracle / Dev.java
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: 2026-05-10; kiểm tra: 2026-11-27.
  - Page explicitly reports last update May 10, 2026; examples include version-specific pinning differences.
- **java-tools** · [The Core JDK Tools](https://dev.java/learn/jvm/core-tools/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-jfr** · [JFR, Monitoring and Troubleshooting](https://dev.java/learn/jvm/monitoring-troubleshooting/) · Oracle / Dev.java
  - Loại: tutorial_path; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-object** · [Object: equals and hashCode API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html) · Oracle
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: Java SE 21 reference; not claimed published in 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-money** · [BigDecimal API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html) · Oracle
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: Java SE 21 reference; not claimed published in 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **java-concurrency** · [java.util.concurrent API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html) · Oracle
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: Java SE 21 reference; not claimed published in 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **maven** · [Maven in 5 Minutes](https://maven.apache.org/guides/getting-started/maven-in-five-minutes.html) · Apache Maven
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **vscode** · [Getting Started with Java in VS Code](https://code.visualstudio.com/docs/java/java-tutorial) · Microsoft
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **http** · [Overview of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) · MDN
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **http-methods** · [HTTP request methods](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods) · MDN
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **http-status** · [HTTP response status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) · MDN
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **mit-testing** · [MIT 6.102: Testing](https://web.mit.edu/6.102/www/sp24/classes/02-testing/) · MIT
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; TypeScript examples; edition: Spring 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - 2024 course archive inspected. General software-construction material, NOT a Java or Spring course. Embedded tutor may require access; public reading remains usable.
- **mit-spec** · [MIT 6.102: Specifications](https://web.mit.edu/6.102/www/sp24/classes/04-specifications/) · MIT
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; TypeScript examples; edition: Spring 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - 2024 course archive inspected. General software-construction material, NOT a Java or Spring course. Embedded tutor may require access; public reading remains usable.
- **mit-adt** · [MIT 6.102: Abstract Data Types](https://web.mit.edu/6.102/www/sp24/classes/06-abstract-data-types/) · MIT
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; TypeScript examples; edition: Spring 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - 2024 course archive inspected. General software-construction material, NOT a Java or Spring course. Embedded tutor may require access; public reading remains usable.
- **mit-invariant** · [MIT 6.102: Abstraction Functions & Rep Invariants](https://web.mit.edu/6.102/www/sp24/classes/07-abstraction-functions-rep-invariants/) · MIT
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; TypeScript examples; edition: Spring 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - 2024 course archive inspected. General software-construction material, NOT a Java or Spring course. Embedded tutor may require access; public reading remains usable.
- **mit-concurrency** · [MIT 6.102: Concurrency](https://web.mit.edu/6.102/www/sp24/classes/14-concurrency/) · MIT
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; TypeScript examples; edition: Spring 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - 2024 course archive inspected. General software-construction material, NOT a Java or Spring course. Embedded tutor may require access; public reading remains usable.
- **mit-locks** · [MIT 6.102: Mutual Exclusion](https://web.mit.edu/6.102/www/sp24/classes/16-mutual-exclusion/) · MIT
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; TypeScript examples; edition: Spring 2024.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - 2024 course archive inspected. General software-construction material, NOT a Java or Spring course. Embedded tutor may require access; public reading remains usable.
- **sql-query** · [CS50 SQL: Querying](https://cs50.harvard.edu/sql/notes/0/) · Harvard CS50
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Opened /sql/2024/notes/0/; redirects to this maintained public page. Original publication date is not inferred from redirect.
- **sql-query-pset** · [CS50 SQL Problem Set 0](https://cs50.harvard.edu/sql/psets/0/) · Harvard CS50
  - Loại: official_exercise; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public assignment statement inspected; submission/gradebook may require an account.
- **sql-relations** · [CS50 SQL: Relating](https://cs50.harvard.edu/sql/notes/1/) · Harvard CS50
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Opened /sql/2024/notes/1/; redirects to this maintained public page. Original publication date is not inferred from redirect.
- **sql-relations-pset** · [CS50 SQL Problem Set 1](https://cs50.harvard.edu/sql/psets/1/) · Harvard CS50
  - Loại: official_exercise; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public assignment statement inspected; submission/gradebook may require an account.
- **sql-design** · [CS50 SQL: Designing](https://cs50.harvard.edu/sql/notes/2/) · Harvard CS50
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Opened /sql/2024/notes/2/; redirects to this maintained public page. Original publication date is not inferred from redirect.
- **sql-design-pset** · [CS50 SQL Problem Set 2](https://cs50.harvard.edu/sql/psets/2/) · Harvard CS50
  - Loại: official_exercise; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public assignment statement inspected; submission/gradebook may require an account.
- **sql-index** · [CS50 SQL: Optimizing](https://cs50.harvard.edu/sql/notes/5/) · Harvard CS50
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Opened /sql/2024/notes/5/; redirects to this maintained public page. Original publication date is not inferred from redirect.
- **sql-index-pset** · [CS50 SQL Problem Set 5](https://cs50.harvard.edu/sql/psets/5/) · Harvard CS50
  - Loại: official_exercise; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public assignment statement inspected; submission/gradebook may require an account.
- **sql-final** · [CS50 SQL Final Project](https://cs50.harvard.edu/sql/project/) · Harvard CS50
  - Loại: official_exercise; truy cập: free_reading; ngôn ngữ: en; edition: 2024 entry redirects to maintained public OCW.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **postgres** · [PostgreSQL Tutorial](https://www.postgresql.org/docs/16/tutorial.html) · PostgreSQL
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: PostgreSQL 16 maintained reference.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **isolation** · [Transaction Isolation](https://www.postgresql.org/docs/16/transaction-iso.html) · PostgreSQL
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: PostgreSQL 16 maintained reference.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **db-locks** · [Explicit Locking and Deadlocks](https://www.postgresql.org/docs/16/explicit-locking.html) · PostgreSQL
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: PostgreSQL 16 maintained reference.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **boot-lab** · [Building an Application with Spring Boot](https://spring.io/guides/gs/spring-boot/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **rest-lab** · [Building a RESTful Web Service](https://spring.io/guides/gs/rest-service/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **validation-lab** · [Validating Form Input](https://spring.io/guides/gs/validating-form-input/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **jpa-lab** · [Accessing Data with JPA](https://spring.io/guides/gs/accessing-data-jpa/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **mysql-lab** · [Accessing data with MySQL](https://spring.io/guides/gs/accessing-data-mysql/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **tx-lab** · [Managing Transactions](https://spring.io/guides/gs/managing-transactions/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **security-lab** · [Securing a Web Application](https://spring.io/guides/gs/securing-web/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **testing-lab** · [Testing the Web Layer](https://spring.io/guides/gs/testing-web/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **client-lab** · [Consuming a RESTful Web Service](https://spring.io/guides/gs/consuming-rest/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **breaker-lab** · [Spring Cloud Circuit Breaker Guide](https://spring.io/guides/gs/cloud-circuit-breaker/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **mq-lab** · [Messaging with RabbitMQ](https://spring.io/guides/gs/messaging-rabbitmq/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **batch-lab** · [Creating a Batch Service](https://spring.io/guides/gs/batch-processing/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **schedule-lab** · [Scheduling Tasks](https://spring.io/guides/gs/scheduling-tasks/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **docker-lab** · [Spring Boot with Docker](https://spring.io/guides/gs/spring-boot-docker/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **actuator-lab** · [Building a RESTful Web Service with Spring Boot Actuator](https://spring.io/guides/gs/actuator-service/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **discovery-lab** · [Service Registration and Discovery](https://spring.io/guides/gs/service-registration-and-discovery/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **rest-tutorial** · [Building REST services with Spring](https://spring.io/guides/tutorials/rest/) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **ioc** · [The IoC Container](https://docs.spring.io/spring-framework/reference/core/beans.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **config** · [Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **jdbc** · [Data Access with JDBC](https://docs.spring.io/spring-framework/reference/data-access/jdbc.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **jpa-query** · [JPA Query Methods](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **transaction** · [Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **security** · [Spring Security Architecture](https://docs.spring.io/spring-security/reference/servlet/architecture.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **jwt** · [OAuth 2.0 Resource Server JWT](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **owasp** · [REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) · OWASP
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **boot-test** · [Spring Boot Testing](https://docs.spring.io/spring-boot/reference/testing/index.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **junit** · [JUnit User Guide](https://docs.junit.org/6.1.3/overview.html) · JUnit
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: JUnit 6.1.3; use the version managed by the chosen Spring Boot BOM.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
  - [Nguồn dự phòng chính thức](https://github.com/junit-team/junit-framework) nếu trang tài liệu gặp lỗi truy cập/chứng chỉ.
- **testcontainers** · [JUnit 5 Quickstart](https://java.testcontainers.org/quickstart/junit_5_quickstart/) · Testcontainers
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **rest-client** · [REST Clients](https://docs.spring.io/spring-framework/reference/integration/rest-clients.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **cache** · [Cache Abstraction](https://docs.spring.io/spring-framework/reference/integration/cache.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **cache-lab** · [Caching Data with Spring](https://github.com/spring-guides/gs-caching) · Spring
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Official guide repository/README inspected; spring.io guide URL returned 404, so this working source is used.
- **redis** · [Redis data types](https://redis.io/docs/latest/develop/data-types/) · Redis
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **docker** · [What is a container?](https://docs.docker.com/learn/content/what-is-a-container/) · Docker
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: 2026-10-21; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **ci** · [Building and testing Java with Maven](https://docs.github.com/en/actions/tutorials/build-and-test-code/java-with-maven) · GitHub / Microsoft
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Reading is public; Actions execution can be metered depending on repository/account. Local Maven is the free default practice.
- **observability** · [Spring Boot Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **otel** · [Java OpenTelemetry: Getting Started by Example](https://opentelemetry.io/docs/languages/java/getting-started/) · OpenTelemetry
  - Loại: guided_tutorial; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
  - [Nguồn dự phòng chính thức](https://github.com/open-telemetry/opentelemetry.io/blob/main/content/en/docs/languages/java/getting-started.md) nếu trang tài liệu gặp lỗi truy cập/chứng chỉ.
- **petclinic** · [Spring Petclinic sample application](https://github.com/spring-projects/spring-petclinic) · Spring
  - Loại: reference_project; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Official sample repository inspected; read the checked-out LICENSE and pin a commit before redistributing code. This catalog only links to it.
- **reactive** · [Spring WebFlux](https://docs.spring.io/spring-framework/reference/web/webflux.html) · Spring
  - Loại: documentation; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **azure** · [Deploy a Spring Boot app to Azure Container Apps](https://learn.microsoft.com/en-us/training/modules/java-spring-on-azure-container-apps/) · Microsoft Learn
  - Loại: course_reading; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: chưa xác định; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Seven-unit learning module is public; Azure resources are NOT guaranteed free. Cloud deployment is optional, never part of the free-only plan.
- **blog-boot24** · [Bootiful Spring Boot in 2024, part 1](https://spring.io/blog/2024/03/11/bootiful-spring-boot-in-2024-part-1/) · Spring / Josh Long
  - Loại: blog; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: 2024-03-11; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **blog-boot34** · [Bootiful Spring Boot 3.4: Spring Boot](https://spring.io/blog/2024/11/24/bootiful-34-boot/) · Spring / Josh Long
  - Loại: blog; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: 2024-11-24; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **blog-mvc26** · [Optimizations in Spring MVC](https://spring.io/blog/2026/02/25/optimizing-spring-mvc/) · Spring / Dave Syer
  - Loại: blog; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: 2026-02-25; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **blog-boot4-25** · [Modularizing Spring Boot](https://spring.io/blog/2025/10/28/modularizing-spring-boot/) · Spring Boot Team
  - Loại: blog; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: 2025-10-28; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.
- **academy-announcement** · [Spring Academy Pro Content Now Free To Access](https://spring.io/blog/2024/04/10/spring-academy-pro-content-now-free-to-access/) · Spring / Michael Minella
  - Loại: blog; truy cập: free_reading; ngôn ngữ: en; edition: rolling_checked_2026.
  - Ngày công bố: 2024-04-10; ngày cập nhật xác minh được: chưa xác định; kiểm tra: 2026-11-27.
  - Public page content inspected; enrollment and execution were not tested.

## Giới hạn kiểm định

Curated by one research pass; not independently reviewed assessment content. Never imported into the approved interview question bank.

Pick one supported JDK/Spring Boot BOM for a lab and follow that version's documentation. Rolling references and 2024 blogs can describe different versions; do not mix dependency versions mechanically.
