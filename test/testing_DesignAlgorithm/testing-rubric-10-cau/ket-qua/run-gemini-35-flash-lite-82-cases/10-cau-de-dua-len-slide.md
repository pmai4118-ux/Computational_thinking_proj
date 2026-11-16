# 10 Mục Dữ Liệu Thực Tế Để Đưa Lên Slide Báo Cáo

Tài liệu này tổng hợp 10 ca kiểm thử tiêu biểu cho 10 câu hỏi, được trích xuất từ dữ liệu chạy thực nghiệm trực tiếp qua API Gemini 3.5 Flash-Lite. Mỗi mục tương ứng với nội dung chi tiết của một slide thuyết trình.

---
## Slide 1: Câu demo.Q002 - JDK, JRE và JVM

- **Mã câu & Tiêu đề**: `demo.Q002` - **JDK, JRE và JVM**
- **Đề bài tóm tắt**: Phân biệt JDK, JRE và JVM. Vai trò của từng thành phần là gì?...
- **Mã ca kiểm thử**: `A-Q002-Dung-01` (Loại ca: Dung)
- **Bài làm của sinh viên**:
  > "JVM thực thi bytecode Java. JRE chứa JVM và các thư viện cần để ứng dụng chạy.  JDK cung cấp môi trường chạy và các công cụ phát triển như javac. Dùng JDK không bắt buộc cài thêm một bản JRE riêng."
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q002.knowledge`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: JVM and runtime and Development tools. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 2: Both observations are demonstrated: JVM and runtime and Development tools. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - JVM and runtime: The candidate correctly distinguishes the JVM as executing bytecode and the JRE as containing the JVM and necessary libraries for running applications.
Met - Development tools: The candidate explains that the JDK supplies development tools like javac and notes that a separate JRE distribution installation is not required.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q002.knowledge.1` (met): Trích dẫn nguyên văn *"JVM thực thi bytecode Java. JRE chứa JVM và các thư viện cần để ứng dụng chạy."* -> The candidate correctly distinguishes the JVM as executing bytecode and the JRE as containing the JVM and necessary libraries for running applications.
  - Tiêu chí `demo.Q002.knowledge.2` (met): Trích dẫn nguyên văn *"JDK cung cấp môi trường chạy và các công cụ phát triển như javac. Dùng JDK không bắt buộc cài thêm m"* -> The candidate explains that the JDK supplies development tools like javac and notes that a separate JRE distribution installation is not required.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

---
## Slide 2: Câu demo.Q005 - So sánh == và equals

- **Mã câu & Tiêu đề**: `demo.Q005` - **So sánh == và equals**
- **Đề bài tóm tắt**: Phân biệt == và .equals() trong Java....
- **Mã ca kiểm thử**: `A-Q005-SaiNua-01` (Loại ca: SaiNua)
- **Bài làm của sinh viên**:
  > "Với int, == so sánh giá trị; với biến tham chiếu, == kiểm tra cùng đối tượng.  Hai lần new String("hi") tạo hai đối tượng khác nhau, nên == trả false còn equals trả true."
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q005.knowledge`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Equality operators / Equals contract. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q005.analysis`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Distinct equal strings / Interning limitation. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 1: One of the two observations is demonstrated: Equality operators / Equals contract. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Equality operators: The answer correctly explains primitive value comparison using int and reference identity comparison for reference variables.
Not met - Equals contract: The answer fails to explain that equals defines logical equality, that String compares content, and that default Object.equals uses identity.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q005.knowledge.2] Equals contract. Required: Explain that equals can define logical equality, that String compares content, and that default Object.equals uses identity.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 1: One of the two observations is demonstrated: Distinct equal strings / Interning limitation. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Distinct equal strings: The answer illustrates the difference using two separately constructed String objects with new String("hi").
Not met - Interning limitation: The answer does not mention interning or explain why equal interned literals do not establish that == compares string contents.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q005.analysis.2] Interning limitation. Required: Explain why equal interned literals do not establish that == compares String contents.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q005.knowledge.1` (met): Trích dẫn nguyên văn *"Với int, == so sánh giá trị; với biến tham chiếu, == kiểm tra cùng đối tượng."* -> The answer correctly explains primitive value comparison using int and reference identity comparison for reference variables.
  - Tiêu chí `demo.Q005.knowledge.2` (unmet): Thiếu ý (Omission) -> The answer fails to explain that equals defines logical equality, that String compares content, and that default Object.equals uses identity.
  - Tiêu chí `demo.Q005.analysis.1` (met): Trích dẫn nguyên văn *"Hai lần new String("hi") tạo hai đối tượng khác nhau, nên == trả false còn equals trả true."* -> The answer illustrates the difference using two separately constructed String objects with new String("hi").
  - Tiêu chí `demo.Q005.analysis.2` (unmet): Thiếu ý (Omission) -> The answer does not mention interning or explain why equal interned literals do not establish that == compares string contents.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

---
## Slide 3: Câu demo.Q007 - Tính bất biến của String

- **Mã câu & Tiêu đề**: `demo.Q007` - **Tính bất biến của String**
- **Đề bài tóm tắt**: Tại sao đối tượng String trong Java được thiết kế là Immutable (không thể thay đổi)? Phân tích đoạn code minh họa bên dưới, nêu lợi ích của tính bất biến và cách xử lý khi cần nối chuỗi lặp nhiều lần....
- **Mã ca kiểm thử**: `B-Q007-Null-01` (Loại ca: Null)
- **Bài làm của sinh viên**:
  > "Nội dung String đã tạo giữ nguyên; gán lại biến chỉ đổi tham chiếu.  Có thể chia sẻ cùng chuỗi mà bên nhận không sửa được nội dung của bên gửi.  first in "Java" và second in "Java Backend" vì concat tạo chuỗi kết quả mới.  Cách nối lặp một luồng và l ... (trích đoạn, xem toàn văn theo mã ca)"
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q007.knowledge`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Immutable value and Benefits. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q007.analysis`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Unassigned concatenation / Repeated concatenation. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 2: Both observations are demonstrated: Immutable value and Benefits. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Immutable value: The answer explains that String content cannot be changed and reassignment only changes the reference.
Met - Benefits: The answer identifies safe sharing as a benefit of immutability.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 1: One of the two observations is demonstrated: Unassigned concatenation / Repeated concatenation. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Unassigned concatenation: The answer correctly explains the values of first and second by noting that concat creates a new result string without mutating the original.
Not met - Repeated concatenation: The candidate mentions that the recommendation and reasoning are in unsent notes, failing to provide StringBuilder or explain how it avoids creating immutable intermediate strings.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q007.analysis.2] Repeated concatenation. Required: Recommend StringBuilder for repeated single-thread concatenation and explain why it avoids repeatedly creating immutable intermediate strings.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q007.knowledge.1` (met): Trích dẫn nguyên văn *"Nội dung String đã tạo giữ nguyên; gán lại biến chỉ đổi tham chiếu."* -> The answer explains that String content cannot be changed and reassignment only changes the reference.
  - Tiêu chí `demo.Q007.knowledge.2` (met): Trích dẫn nguyên văn *"Có thể chia sẻ cùng chuỗi mà bên nhận không sửa được nội dung của bên gửi."* -> The answer identifies safe sharing as a benefit of immutability.
  - Tiêu chí `demo.Q007.analysis.1` (met): Trích dẫn nguyên văn *"first in "Java" và second in "Java Backend" vì concat tạo chuỗi kết quả mới."* -> The answer correctly explains the values of first and second by noting that concat creates a new result string without mutating the original.
  - Tiêu chí `demo.Q007.analysis.2` (unmet): Thiếu ý (Omission) -> The candidate mentions that the recommendation and reasoning are in unsent notes, failing to provide StringBuilder or explain how it avoids creating immutable intermediate strings.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca SAI LỆCH ở bước nhận diện tiêu chí (M) do mô hình phân loại trạng thái khác đáp án tham chiếu, kéo theo điểm số tính lại ở bước R bị thay đổi.**

---
## Slide 4: Câu demo.Q009 - Tìm kiếm nhị phân

- **Mã câu & Tiêu đề**: `demo.Q009` - **Tìm kiếm nhị phân**
- **Đề bài tóm tắt**: Viết hàm Java lặp `static int binarySearch(int[] values, int target)` cho mảng số nguyên tăng dần; trả về một chỉ số hợp lệ nếu tìm thấy target và -1 nếu không có. Giải thích bất biến vòng lặp, cách c...
- **Mã ca kiểm thử**: `A-Q009-Dung-01` (Loại ca: Dung)
- **Bài làm của sinh viên**:
  > "Do mảng tăng dần, nếu giá trị giữa nhỏ hơn target thì mọi vị trí từ low đến mid cũng nhỏ hơn; nếu lớn hơn thì loại từ mid đến high. Khoảng ứng viên xấp xỉ giảm một nửa.  Bản lặp có thời gian xấu nhất O(log n), bộ nhớ phụ O(1).  Bất biến: nếu còn chỉ  ... (trích đoạn, xem toàn văn theo mã ca)"
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q009.knowledge`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Sorted input and Complexity. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q009.analysis`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Search invariant and Progress and termination. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Testing** (`rubric.demo.Q009.testing`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Found and absent cases and Boundary cases. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Implementation** (`rubric.demo.Q009.implementation`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Executable search loop and Return contract. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 2: Both observations are demonstrated: Sorted input and Complexity. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Sorted input: The candidate explains that sorted input allows the search interval to be halved based on comparisons with the midpoint.
Met - Complexity: The candidate states O(log n) worst-case time complexity and O(1) auxiliary space complexity.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 2: Both observations are demonstrated: Search invariant and Progress and termination. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Search invariant: The candidate explicitly states the search invariant using the inclusive interval [low, high].
Met - Progress and termination: The candidate explains safe midpoint calculation, updates to boundaries, and termination when low > high.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 2: Both observations are demonstrated: Found and absent cases and Boundary cases. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Found and absent cases: The candidate provides concrete found and absent test cases.
Met - Boundary cases: The candidate provides empty, singleton, and duplicate boundary test cases.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Level 2: Both observations are demonstrated: Executable search loop and Return contract. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Executable search loop: The candidate provides a correct iterative Java binary search method with midpoint comparison and bound updates.
Met - Return contract: The candidate explains that -1 is returned for absent targets and empty arrays set high = -1 avoiding array reads.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q009.knowledge.1` (met): Trích dẫn nguyên văn *"Do mảng tăng dần, nếu giá trị giữa nhỏ hơn target thì mọi vị trí từ low đến mid cũng nhỏ hơn; nếu lớ"* -> The candidate explains that sorted input allows the search interval to be halved based on comparisons with the midpoint.
  - Tiêu chí `demo.Q009.knowledge.2` (met): Trích dẫn nguyên văn *"Bản lặp có thời gian xấu nhất O(log n), bộ nhớ phụ O(1)."* -> The candidate states O(log n) worst-case time complexity and O(1) auxiliary space complexity.
  - Tiêu chí `demo.Q009.analysis.1` (met): Trích dẫn nguyên văn *"Bất biến: nếu còn chỉ số khớp, nó nằm trong khoảng đóng [low, high]."* -> The candidate explicitly states the search invariant using the inclusive interval [low, high].
  - Tiêu chí `demo.Q009.analysis.2` (met): Trích dẫn nguyên văn *"Tính mid = low + (high - low) / 2 để tránh tràn tổng. Đặt low = mid + 1 nếu giá trị giữa nhỏ hơn tar"* -> The candidate explains safe midpoint calculation, updates to boundaries, and termination when low > high.
  - Tiêu chí `demo.Q009.testing.1` (met): Trích dẫn nguyên văn *"[2, 4, 9] tìm 4 trả 1, tìm 5 trả -1."* -> The candidate provides concrete found and absent test cases.
  - Tiêu chí `demo.Q009.testing.2` (met): Trích dẫn nguyên văn *"[] tìm 4 trả -1; [4] tìm 4 trả 0; [4, 4] tìm 4 trả 0 hoặc 1 đều đúng."* -> The candidate provides empty, singleton, and duplicate boundary test cases.
  - Tiêu chí `demo.Q009.implementation.1` (met): Trích dẫn nguyên văn *"static int binarySearch(int[] values, int target) {
    int low = 0, high = values.length - 1;
    w"* -> The candidate provides a correct iterative Java binary search method with midpoint comparison and bound updates.
  - Tiêu chí `demo.Q009.implementation.2` (met): Trích dẫn nguyên văn *"Hàm trả -1 sau vòng lặp nếu vắng target; mảng rỗng đặt high = -1 nên không đọc mảng."* -> The candidate explains that -1 is returned for absent targets and empty arrays set high = -1 avoiding array reads.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

---
## Slide 5: Câu demo.Q010 - Giải thích Bubble Sort

- **Mã câu & Tiêu đề**: `demo.Q010` - **Giải thích Bubble Sort**
- **Đề bài tóm tắt**: Mô tả Bubble Sort để sắp xếp mảng số nguyên tăng dần. Giải thích vì sao sau mỗi lượt phần tử lớn nhất còn lại nằm cuối vùng chưa sắp xếp, phân tích độ phức tạp và nêu test biên....
- **Mã ca kiểm thử**: `A-Q010-SaiNua-01` (Loại ca: SaiNua)
- **Bài làm của sinh viên**:
  > "So sánh các cặp kề và đổi chỗ nếu bên trái lớn hơn, rồi tiếp tục các lượt quét.  Em tính thời gian xấu nhất là O(n log n).  Trong một lượt quét từ trái sang phải, số lớn nhất gặp lần lượt mọi số phía sau và tới cuối vùng.  Lượt sau em vẫn quét cả đoạ ... (trích đoạn, xem toàn văn theo mã ca)"
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q010.knowledge`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Adjacent swaps / Complexity. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q010.analysis`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Pass invariant / Shrinking region. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
  - **Testing** (`rubric.demo.Q010.testing`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: General sorting / Boundary and duplicate data. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 1: One of the two observations is demonstrated: Adjacent swaps / Complexity. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Adjacent swaps: The candidate correctly describes comparing adjacent elements and swapping them if they are out of order over repeated passes.
Not met - Complexity: The stated worst-case time complexity is O(n log n), which is incorrect for Bubble Sort.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q010.knowledge.2] Complexity. Required: State quadratic worst-case time, constant auxiliary space and linear best-case time only when an early-exit flag is used.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 1: One of the two observations is demonstrated: Pass invariant / Shrinking region. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Pass invariant: The candidate explains that during a pass, the largest number bubbles up by comparing with subsequent elements until it reaches the end of the region.
Not met - Shrinking region: The candidate explicitly states they do not exclude the sorted suffix or stop early on a no-swap pass, failing the requirement.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q010.analysis.2] Shrinking region. Required: Explain excluding the sorted suffix and why a no-swap pass permits termination.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 1: One of the two observations is demonstrated: General sorting / Boundary and duplicate data. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - General sorting: The candidate provides a nontrivial unsorted input and its correct sorted output.
Not met - Boundary and duplicate data: The answer does not provide empty, singleton, or duplicate-containing boundary examples.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q010.testing.2] Boundary and duplicate data. Required: Give empty, singleton and duplicate-containing examples with expected outputs.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q010.knowledge.1` (met): Trích dẫn nguyên văn *"So sánh các cặp kề và đổi chỗ nếu bên trái lớn hơn, rồi tiếp tục các lượt quét."* -> The candidate correctly describes comparing adjacent elements and swapping them if they are out of order over repeated passes.
  - Tiêu chí `demo.Q010.knowledge.2` (unmet): Trích dẫn nguyên văn *"Em tính thời gian xấu nhất là O(n log n)."* -> The stated worst-case time complexity is O(n log n), which is incorrect for Bubble Sort.
  - Tiêu chí `demo.Q010.analysis.1` (met): Trích dẫn nguyên văn *"Trong một lượt quét từ trái sang phải, số lớn nhất gặp lần lượt mọi số phía sau và tới cuối vùng."* -> The candidate explains that during a pass, the largest number bubbles up by comparing with subsequent elements until it reaches the end of the region.
  - Tiêu chí `demo.Q010.analysis.2` (unmet): Trích dẫn nguyên văn *"Lượt sau em vẫn quét cả đoạn đuôi đã chốt; em không xét dừng khi cả lượt không đổi chỗ."* -> The candidate explicitly states they do not exclude the sorted suffix or stop early on a no-swap pass, failing the requirement.
  - Tiêu chí `demo.Q010.testing.1` (met): Trích dẫn nguyên văn *"[9, 1, 4] phải ra [1, 4, 9]."* -> The candidate provides a nontrivial unsorted input and its correct sorted output.
  - Tiêu chí `demo.Q010.testing.2` (unmet): Thiếu ý (Omission) -> The answer does not provide empty, singleton, or duplicate-containing boundary examples.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

---
## Slide 6: Câu demo.Q017 - Sửa bộ chuyển infix sang postfix

- **Mã câu & Tiêu đề**: `demo.Q017` - **Sửa bộ chuyển infix sang postfix**
- **Đề bài tóm tắt**: Giả sử trợ lý AI đề xuất hàm Java chuyển infix sang postfix như snippet. Đây là fixture mô phỏng do nhóm biên soạn từ mã nguồn mở, không phải bản ghi AI thật. Hãy tìm lỗi, đề xuất sửa và nêu test. Hợp...
- **Mã ca kiểm thử**: `A-Q017-Null-01` (Loại ca: Null)
- **Bài làm của sinh viên**:
  > "Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này không ghi lại các kết luận đó."
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q017.knowledge`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **0.0 đ**
    - Căn cứ quy tắc: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q017.analysis`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **0.0 đ**
    - Căn cứ quy tắc: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
  - **Testing** (`rubric.demo.Q017.testing`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **0.0 đ**
    - Căn cứ quy tắc: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
  - **Implementation** (`rubric.demo.Q017.implementation`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **0.0 đ**
    - Căn cứ quy tắc: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
Not met - Operator stack: The answer completely omits any explanation regarding the operator stack holding pending operators.
Not met - Precedence and associativity: The answer provides no explanation of multiplication/division precedence and left associativity.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q017.knowledge.1] Operator stack. Required: Explain that the output contains operands and emitted operators while the stack temporarily holds pending operators.
    + [demo.Q017.knowledge.2] Precedence and associativity. Required: Explain multiplication/division precedence and left associativity for equal-precedence operators.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
Not met - Identify pending operators: The answer does not identify the missing final stack drain defect.
Not met - Explain failure and complexity: The answer fails to trace a valid counterexample or discuss complexity.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q017.analysis.1] Identify pending operators. Required: Locate the missing final stack drain, rather than inventing an unrelated defect outside the given input contract.
    + [demo.Q017.analysis.2] Explain failure and complexity. Required: Trace a valid counterexample and explain linear processing with each token pushed/popped at most once.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
Not met - Simple and precedence cases: The answer omits expected postfix outputs for simple and precedence cases.
Not met - Parentheses and associativity: The answer omits outputs for parentheses and associativity tests.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q017.testing.1] Simple and precedence cases. Required: Give exact expected postfix outputs for a simple expression and mixed precedence.
    + [demo.Q017.testing.2] Parentheses and associativity. Required: Give correct expected outputs for parentheses and equal-precedence left associativity.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
Not met - Concrete final drain: The answer does not provide any Java patch.
Not met - Patch placement and scope: The answer does not provide patch placement and scope details.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q017.implementation.1] Concrete final drain. Required: Provide an exact Java patch that pops all remaining operators before the final return.
    + [demo.Q017.implementation.2] Patch placement and scope. Required: Place the patch after the token loop while preserving the existing precedence and parenthesis logic for valid input.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q017.knowledge.1` (unmet): Thiếu ý (Omission) -> The answer completely omits any explanation regarding the operator stack holding pending operators.
  - Tiêu chí `demo.Q017.knowledge.2` (unmet): Thiếu ý (Omission) -> The answer provides no explanation of multiplication/division precedence and left associativity.
  - Tiêu chí `demo.Q017.analysis.1` (unmet): Thiếu ý (Omission) -> The answer does not identify the missing final stack drain defect.
  - Tiêu chí `demo.Q017.analysis.2` (unmet): Thiếu ý (Omission) -> The answer fails to trace a valid counterexample or discuss complexity.
  - Tiêu chí `demo.Q017.testing.1` (unmet): Thiếu ý (Omission) -> The answer omits expected postfix outputs for simple and precedence cases.
  - Tiêu chí `demo.Q017.testing.2` (unmet): Thiếu ý (Omission) -> The answer omits outputs for parentheses and associativity tests.
  - Tiêu chí `demo.Q017.implementation.1` (unmet): Thiếu ý (Omission) -> The answer does not provide any Java patch.
  - Tiêu chí `demo.Q017.implementation.2` (unmet): Thiếu ý (Omission) -> The answer does not provide patch placement and scope details.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca SAI LỆCH ở bước nhận diện tiêu chí (M) do mô hình phân loại trạng thái khác đáp án tham chiếu, kéo theo điểm số tính lại ở bước R bị thay đổi.**

---
## Slide 7: Câu demo.Q018 - Sửa Counting Sort

- **Mã câu & Tiêu đề**: `demo.Q018` - **Sửa Counting Sort**
- **Đề bài tóm tắt**: Giả sử trợ lý AI đề xuất Counting Sort cho mảng int trong Java. Hãy review code để xử lý mảng rỗng, số âm và phần tử trùng. Khi range = max - min + 1 vượt quá 1.000.000, hàm phải từ chối rõ ràng thay ...
- **Mã ca kiểm thử**: `A-Q018-Dung-01` (Loại ca: Dung)
- **Bài làm của sinh viên**:
  > "Đếm tần suất rồi duyệt giá trị tăng dần. Ghi ra mỗi giá trị đúng số lần đếm được nên giữ phần tử trùng.  Đặt k = max - min + 1. Thời gian O(n+k) và bộ nhớ O(n+k) tính cả bảng đếm k ô và mảng trả về n ô.  max().getAsInt() lỗi khi đầu vào rỗng. Dùng tr ... (trích đoạn, xem toàn văn theo mã ca)"
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q018.knowledge`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Frequency counts and Range-dependent cost. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q018.analysis`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Empty and negative defects and Overflow and allocation limit. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Testing** (`rubric.demo.Q018.testing`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Empty, negatives and duplicates and Limit and overflow cases. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Implementation** (`rubric.demo.Q018.implementation`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Counting implementation and Enforced width guard. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 2: Both observations are demonstrated: Frequency counts and Range-dependent cost. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Frequency counts: The answer explains counting frequencies and reconstructing values in ascending order while preserving duplicates.
Met - Range-dependent cost: The answer correctly explains the O(n+k) time and O(n+k) space complexity.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 2: Both observations are demonstrated: Empty and negative defects and Overflow and allocation limit. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Empty and negative defects: The answer identifies both max().getAsInt() on empty arrays and negative-value indexing as distinct defects.
Met - Overflow and allocation limit: The answer explains computing range in long before allocation and rejecting ranges above 1,000,000.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 2: Both observations are demonstrated: Empty, negatives and duplicates and Limit and overflow cases. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Empty, negatives and duplicates: The answer gives concrete empty and mixed negative/duplicate test cases with expected sorted arrays.
Met - Limit and overflow cases: The answer tests the accepted range boundary, one-over-boundary rejection and extreme int values.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Level 2: Both observations are demonstrated: Counting implementation and Enforced width guard. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Counting implementation: The code provides an empty guard, min offset, frequency counts, and duplicate-preserving reconstruction.
Met - Enforced width guard: The supplied code calculates width in long and rejects an oversized width before allocating counts.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q018.knowledge.1` (met): Trích dẫn nguyên văn *"Đếm tần suất rồi duyệt giá trị tăng dần. Ghi ra mỗi giá trị đúng số lần đếm được nên giữ phần tử trù"* -> The answer explains counting frequencies and reconstructing values in ascending order while preserving duplicates.
  - Tiêu chí `demo.Q018.knowledge.2` (met): Trích dẫn nguyên văn *"Đặt k = max - min + 1. Thời gian O(n+k) và bộ nhớ O(n+k) tính cả bảng đếm k ô và mảng trả về n ô."* -> The answer correctly explains the O(n+k) time and O(n+k) space complexity.
  - Tiêu chí `demo.Q018.analysis.1` (met): Trích dẫn nguyên văn *"max().getAsInt() lỗi khi đầu vào rỗng. Dùng trực tiếp giá trị âm làm chỉ số count cũng lỗi."* -> The answer identifies both max().getAsInt() on empty arrays and negative-value indexing as distinct defects.
  - Tiêu chí `demo.Q018.analysis.2` (met): Trích dẫn nguyên văn *"Tính (long) max - min + 1 trước cấp phát; từ chối khi vượt 1.000.000 để tránh tràn int hoặc cấp phát"* -> The answer explains computing range in long before allocation and rejecting ranges above 1,000,000.
  - Tiêu chí `demo.Q018.testing.1` (met): Trích dẫn nguyên văn *"[] → []; [3, -1, 3, 0, -1] → [-1, -1, 0, 3, 3]."* -> The answer gives concrete empty and mixed negative/duplicate test cases with expected sorted arrays.
  - Tiêu chí `demo.Q018.testing.2` (met): Trích dẫn nguyên văn *"[-1, 999998] có range đúng 1.000.000, chấp nhận và trả [-1, 999998]. [-1, 999999] và [Integer.MIN_VA"* -> The answer tests the accepted range boundary, one-over-boundary rejection and extreme int values.
  - Tiêu chí `demo.Q018.implementation.1` (met): Trích dẫn nguyên văn *"static int[] countingSort(int[] values) {
    if (values.length == 0) return new int[0];
    int min"* -> The code provides an empty guard, min offset, frequency counts, and duplicate-preserving reconstruction.
  - Tiêu chí `demo.Q018.implementation.2` (met): Trích dẫn nguyên văn *"long width = (long) max - min + 1;
    if (width > 1_000_000L) throw new IllegalArgumentException("R"* -> The supplied code calculates width in long and rejects an oversized width before allocating counts.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

---
## Slide 8: Câu demo.Q022 - Chọn List, Set hay Map

- **Mã câu & Tiêu đề**: `demo.Q022` - **Chọn List, Set hay Map**
- **Đề bài tóm tắt**: Phân biệt List, Set và Map. Khi nào nên sử dụng từng loại?...
- **Mã ca kiểm thử**: `B-Q022-Sai-01` (Loại ca: Sai)
- **Bài làm của sinh viên**:
  > "List chỉ giữ giá trị duy nhất, Set cho trùng, Map là danh sách có chỉ số nguyên liên tục.  Set nào cũng tự sắp xếp tăng và Map nào cũng luôn giữ thứ tự chèn.  Em dùng Set để giữ nguyên thứ tự lịch sử có lượt lặp, List để tự loại trùng ID.  Em không d ... (trích đoạn, xem toàn văn theo mã ca)"
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q022.knowledge`):
    - Điểm kỳ vọng tham chiếu: **0.0 đ**
    - Điểm AI thực tế: **0.0 đ**
    - Căn cứ quy tắc: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q022.analysis`):
    - Điểm kỳ vọng tham chiếu: **0.0 đ**
    - Điểm AI thực tế: **0.0 đ**
    - Căn cứ quy tắc: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
Not met - Collection semantics: The candidate incorrectly swaps the definitions of List and Set, stating List holds unique values and Set allows duplicates, and misdefines Map as a list with continuous integer indices.
Not met - Contract limits: The candidate makes incorrect absolute claims that every Set is sorted and every Map always retains insertion order without connecting ordering to specific implementations.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q022.knowledge.1] Collection semantics. Required: Distinguish ordered sequence with duplicates, unique elements, and key-to-value associations.
    + [demo.Q022.knowledge.2] Contract limits. Required: Do not assume every Set is sorted or every Map retains insertion order; connect ordering to the chosen implementation.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
Not met - List and Set choices: The candidate provides incorrect use cases, proposing to use a Set to keep history order with duplicates and a List to remove duplicate IDs.
Not met - Map choice: The candidate explicitly rejects using Map for key-based lookups and provides incorrect reasoning about keys and values.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q022.analysis.1] List and Set choices. Required: Give suitable use cases for a sequence with duplicates and uniqueness membership.
    + [demo.Q022.analysis.2] Map choice. Required: Give a key-to-value lookup use case and distinguish a repeated key from repeated values.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q022.knowledge.1` (unmet): Trích dẫn nguyên văn *"List chỉ giữ giá trị duy nhất, Set cho trùng, Map là danh sách có chỉ số nguyên liên tục."* -> The candidate incorrectly swaps the definitions of List and Set, stating List holds unique values and Set allows duplicates, and misdefines Map as a list with continuous integer indices.
  - Tiêu chí `demo.Q022.knowledge.2` (unmet): Trích dẫn nguyên văn *"Set nào cũng tự sắp xếp tăng và Map nào cũng luôn giữ thứ tự chèn."* -> The candidate makes incorrect absolute claims that every Set is sorted and every Map always retains insertion order without connecting ordering to specific implementations.
  - Tiêu chí `demo.Q022.analysis.1` (unmet): Trích dẫn nguyên văn *"Em dùng Set để giữ nguyên thứ tự lịch sử có lượt lặp, List để tự loại trùng ID."* -> The candidate provides incorrect use cases, proposing to use a Set to keep history order with duplicates and a List to remove duplicate IDs.
  - Tiêu chí `demo.Q022.analysis.2` (unmet): Trích dẫn nguyên văn *"Em không dùng Map để tra theo khóa; hai khóa có cùng giá trị nên bị hệ thống cấm."* -> The candidate explicitly rejects using Map for key-based lookups and provides incorrect reasoning about keys and values.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

---
## Slide 9: Câu demo.Q028 - Tra cứu nhân viên theo ID

- **Mã câu & Tiêu đề**: `demo.Q028` - **Tra cứu nhân viên theo ID**
- **Đề bài tóm tắt**: Bạn có một danh sách 10.000 nhân viên và cần tìm nhân viên theo ID. Bạn sẽ chọn cấu trúc dữ liệu nào để tối ưu việc tìm kiếm? Vì sao? Giả sử có nhiều lần tra cứu trên cùng tập dữ liệu và ID là duy nhấ...
- **Mã ca kiểm thử**: `A-Q028-SaiNua-01` (Loại ca: SaiNua)
- **Bài làm của sinh viên**:
  > "Dùng HashMap với ID nhân viên làm khóa duy nhất, Employee làm giá trị.  Em tính dựng chỉ mục O(1) và tra luôn O(1), cả xấu nhất.  Dựng bảng một lần để tránh quét lại 10.000 nhân viên cho từng lượt.  Nếu ID vắng, em vẫn gọi getId trên kết quả trả về v ... (trích đoạn, xem toàn văn theo mã ca)"
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q028.knowledge`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Keyed lookup / Cost distinction. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q028.analysis`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Repeated lookup benefit and Missing key behavior. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Testing** (`rubric.demo.Q028.testing`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Existing employee / Missing and empty data. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
  - **Implementation** (`rubric.demo.Q028.implementation`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Build Java index / Handle null result. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 1: One of the two observations is demonstrated: Keyed lookup / Cost distinction. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Keyed lookup: The candidate chooses HashMap keyed by unique employee ID and values as Employee objects.
Not met - Cost distinction: The candidate incorrectly claims worst-case constant lookup O(1).
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q028.knowledge.2] Cost distinction. Required: State expected O(1) lookup, O(n) index construction and O(n) extra storage; do not claim worst-case constant lookup.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 2: Both observations are demonstrated: Repeated lookup benefit and Missing key behavior. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Repeated lookup benefit: The candidate explains preprocessing avoids scanning the list repeatedly for each query.
Met - Missing key behavior: Defines behavior when ID is missing, explicitly stating it calls getId on the null result.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 1: One of the two observations is demonstrated: Existing employee / Missing and empty data. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Existing employee: Gives a concrete existing ID example (7 is An) and expected employee result.
Not met - Missing and empty data: The candidate does not test an empty input collection.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q028.testing.2] Missing and empty data. Required: Test a missing ID and an empty input collection with a not-found result.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Level 1: One of the two observations is demonstrated: Build Java index / Handle null result. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Build Java index: Provides concrete Java code building the map and performing lookup.
Not met - Handle null result: The code fails to handle null results properly and will cause a NullPointerException.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q028.implementation.2] Handle null result. Required: The supplied implementation must handle a missing lookup without dereferencing null.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q028.knowledge.1` (met): Trích dẫn nguyên văn *"Dùng HashMap với ID nhân viên làm khóa duy nhất, Employee làm giá trị."* -> The candidate chooses HashMap keyed by unique employee ID and values as Employee objects.
  - Tiêu chí `demo.Q028.knowledge.2` (unmet): Trích dẫn nguyên văn *"Em tính dựng chỉ mục O(1) và tra luôn O(1), cả xấu nhất."* -> The candidate incorrectly claims worst-case constant lookup O(1).
  - Tiêu chí `demo.Q028.analysis.1` (met): Trích dẫn nguyên văn *"Dựng bảng một lần để tránh quét lại 10.000 nhân viên cho từng lượt."* -> The candidate explains preprocessing avoids scanning the list repeatedly for each query.
  - Tiêu chí `demo.Q028.analysis.2` (met): Trích dẫn nguyên văn *"Nếu ID vắng, em vẫn gọi getId trên kết quả trả về và không có nhánh not-found."* -> Defines behavior when ID is missing, explicitly stating it calls getId on the null result.
  - Tiêu chí `demo.Q028.testing.1` (met): Trích dẫn nguyên văn *"Nếu ID 7 là An, tra 7 phải trả An."* -> Gives a concrete existing ID example (7 is An) and expected employee result.
  - Tiêu chí `demo.Q028.testing.2` (unmet): Thiếu ý (Omission) -> The candidate does not test an empty input collection.
  - Tiêu chí `demo.Q028.implementation.1` (met): Trích dẫn nguyên văn *"Map<Long, Employee> index = new HashMap<>();
for (Employee employee : employees) index.put(employee."* -> Provides concrete Java code building the map and performing lookup.
  - Tiêu chí `demo.Q028.implementation.2` (unmet): Trích dẫn nguyên văn *"Đoạn trên gọi result.getId kể cả khi get trả null."* -> The code fails to handle null results properly and will cause a NullPointerException.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca SAI LỆCH ở bước nhận diện tiêu chí (M) do mô hình phân loại trạng thái khác đáp án tham chiếu, kéo theo điểm số tính lại ở bước R bị thay đổi.**

---
## Slide 10: Câu demo.Q085 - Unit test Service có Repository

- **Mã câu & Tiêu đề**: `demo.Q085` - **Unit test Service có Repository**
- **Đề bài tóm tắt**: Khi viết Unit Test cho một Service có phụ thuộc vào Repository, bạn sẽ tổ chức bài kiểm thử như thế nào?...
- **Mã ca kiểm thử**: `A-Q085-Dung-01` (Loại ca: Dung)
- **Bài làm của sinh viên**:
  > "Kiểm thử logic UserService bằng cách thay phụ thuộc Repository để chạy độc lập với cơ sở dữ liệu thật.  Mock hoặc fake cho phép đặt sẵn dữ liệu trả về hay lỗi. Integration test riêng mới kiểm tra Repository kết nối và truy vấn DB thật.  Inject mock v ... (trích đoạn, xem toàn văn theo mã ca)"
- **Kết quả điểm theo Rubric**:
  - **Knowledge** (`rubric.demo.Q085.knowledge`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Unit boundary and Test double. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q085.analysis`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Arrange act assert and Meaningful verification. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Testing** (`rubric.demo.Q085.testing`):
    - Điểm kỳ vọng tham chiếu: **2.0 đ**
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Success and missing data and Validation and dependency failure. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 2: Both observations are demonstrated: Unit boundary and Test double. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Unit boundary: The answer explains isolating the service behavior from a real repository and database.
Met - Test double: The answer explains controlling repository responses with mock or fake and distinguishes it from integration testing.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 2: Both observations are demonstrated: Arrange act assert and Meaningful verification. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Arrange act assert: The answer describes injecting the test double, arranging responses, invoking the method, and asserting outcomes.
Met - Meaningful verification: The answer explains verifying important side effects without verifying every internal invocation.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 2: Both observations are demonstrated: Success and missing data and Validation and dependency failure. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Success and missing data: The answer provides concrete success and missing data scenarios with explicit service outcomes.
Met - Validation and dependency failure: The answer provides invalid input and repository failure scenarios with expected outcomes.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q085.knowledge.1` (met): Trích dẫn nguyên văn *"Kiểm thử logic UserService bằng cách thay phụ thuộc Repository để chạy độc lập với cơ sở dữ liệu thậ"* -> The answer explains isolating the service behavior from a real repository and database.
  - Tiêu chí `demo.Q085.knowledge.2` (met): Trích dẫn nguyên văn *"Mock hoặc fake cho phép đặt sẵn dữ liệu trả về hay lỗi. Integration test riêng mới kiểm tra Reposito"* -> The answer explains controlling repository responses with mock or fake and distinguishes it from integration testing.
  - Tiêu chí `demo.Q085.analysis.1` (met): Trích dẫn nguyên văn *"Inject mock vào Service, sắp đặt phản hồi cho từng ID, gọi findUser rồi assert giá trị hoặc lỗi theo"* -> The answer describes injecting the test double, arranging responses, invoking the method, and asserting outcomes.
  - Tiêu chí `demo.Q085.analysis.2` (met): Trích dẫn nguyên văn *"Với nghiệp vụ lưu, xác minh đúng bản ghi được lưu khi hợp lệ và không lưu khi sai; không verify mọi "* -> The answer explains verifying important side effects without verifying every internal invocation.
  - Tiêu chí `demo.Q085.testing.1` (met): Trích dẫn nguyên văn *"findUser(7) trả người dùng ID 7 nếu có bản ghi, hoặc trả not-found nếu repo không có bản ghi."* -> The answer provides concrete success and missing data scenarios with explicit service outcomes.
  - Tiêu chí `demo.Q085.testing.2` (met): Trích dẫn nguyên văn *"ID 0 phải bị từ chối trước khi gọi repo. Nếu repo ném lỗi truy cập thì Service phải báo lỗi theo hợp"* -> The answer provides invalid input and repository failure scenarios with expected outcomes.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

