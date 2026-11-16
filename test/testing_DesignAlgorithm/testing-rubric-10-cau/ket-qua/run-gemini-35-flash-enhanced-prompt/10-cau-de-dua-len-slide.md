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
Met - JVM and runtime: The answer correctly distinguishes the JVM as executing bytecode and the JRE as containing the JVM and libraries needed to run applications.
Met - Development tools: The answer explains that the JDK supplies development tools like javac along with runtime capabilities, and explicitly notes that a separate JRE installation is not required.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q002.knowledge.1` (met): Trích dẫn nguyên văn *"JVM thực thi bytecode Java. JRE chứa JVM và các thư viện cần để ứng dụng chạy."* -> The answer correctly distinguishes the JVM as executing bytecode and the JRE as containing the JVM and libraries needed to run applications.
  - Tiêu chí `demo.Q002.knowledge.2` (met): Trích dẫn nguyên văn *"JDK cung cấp môi trường chạy và các công cụ phát triển như javac. Dùng JDK không bắt buộc cài thêm m"* -> The answer explains that the JDK supplies development tools like javac along with runtime capabilities, and explicitly notes that a separate JRE installation is not required.
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
    - Điểm AI thực tế: **2.0 đ**
    - Căn cứ quy tắc: Level 2: Both observations are demonstrated: Equality operators and Equals contract. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
  - **Analysis** (`rubric.demo.Q005.analysis`):
    - Điểm kỳ vọng tham chiếu: **1.0 đ**
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Distinct equal strings / Interning limitation. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 2: Both observations are demonstrated: Equality operators and Equals contract. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Equality operators: The candidate correctly explains primitive value comparison using int and reference identity comparison for reference variables.
Met - Equals contract: The candidate contrasts == returning false and equals returning true for distinct string objects, demonstrating the difference between reference identity and content equality.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 1: One of the two observations is demonstrated: Distinct equal strings / Interning limitation. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Distinct equal strings: The candidate illustrates the requirement using two separately constructed String objects with the same content via new String("hi").
Not met - Interning limitation: The candidate does not mention or explain string interning or why string literals can evaluate to true with ==.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q005.analysis.2] Interning limitation. Required: Explain why equal interned literals do not establish that == compares String contents.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q005.knowledge.1` (met): Trích dẫn nguyên văn *"Với int, == so sánh giá trị; với biến tham chiếu, == kiểm tra cùng đối tượng."* -> The candidate correctly explains primitive value comparison using int and reference identity comparison for reference variables.
  - Tiêu chí `demo.Q005.knowledge.2` (met): Trích dẫn nguyên văn *"== trả false còn equals trả true"* -> The candidate contrasts == returning false and equals returning true for distinct string objects, demonstrating the difference between reference identity and content equality.
  - Tiêu chí `demo.Q005.analysis.1` (met): Trích dẫn nguyên văn *"Hai lần new String("hi") tạo hai đối tượng khác nhau, nên == trả false còn equals trả true."* -> The candidate illustrates the requirement using two separately constructed String objects with the same content via new String("hi").
  - Tiêu chí `demo.Q005.analysis.2` (unmet): Thiếu ý (Omission) -> The candidate does not mention or explain string interning or why string literals can evaluate to true with ==.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca SAI LỆCH ở bước nhận diện tiêu chí (M) do mô hình phân loại trạng thái khác đáp án tham chiếu, kéo theo điểm số tính lại ở bước R bị thay đổi.**

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
    - Điểm AI thực tế: **null (chưa đủ căn cứ)**
    - Căn cứ quy tắc: Insufficient evidence to select a level: possible values range from 1 to 2. Clarify: demo.Q007.analysis.2.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Level 2: Both observations are demonstrated: Immutable value and Benefits. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Immutable value: The candidate explains that String content cannot change and variable reassignment only changes the reference.
Met - Benefits: The candidate provides a valid benefit of immutability regarding safe sharing without modification by the receiver.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Insufficient evidence to select a level: possible values range from 1 to 2. Clarify: demo.Q007.analysis.2.
Met - Unassigned concatenation: The candidate explains the values of first and second, noting that concat creates a new result string.
Insufficient evidence - Repeated concatenation: The candidate explicitly claims that the requested explanation and reasoning are located in unsubmitted notes, requiring an insufficientEvidence classification.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q007.knowledge.1` (met): Trích dẫn nguyên văn *"Nội dung String đã tạo giữ nguyên; gán lại biến chỉ đổi tham chiếu."* -> The candidate explains that String content cannot change and variable reassignment only changes the reference.
  - Tiêu chí `demo.Q007.knowledge.2` (met): Trích dẫn nguyên văn *"Có thể chia sẻ cùng chuỗi mà bên nhận không sửa được nội dung của bên gửi."* -> The candidate provides a valid benefit of immutability regarding safe sharing without modification by the receiver.
  - Tiêu chí `demo.Q007.analysis.1` (met): Trích dẫn nguyên văn *"first in "Java" và second in "Java Backend" vì concat tạo chuỗi kết quả mới."* -> The candidate explains the values of first and second, noting that concat creates a new result string.
  - Tiêu chí `demo.Q007.analysis.2` (insufficientEvidence): Trích dẫn nguyên văn *"Cách nối lặp một luồng và lý do chọn của em nằm trong ghi chú em chưa gửi kèm."* -> The candidate explicitly claims that the requested explanation and reasoning are located in unsubmitted notes, requiring an insufficientEvidence classification.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

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
Met - Sorted input: The candidate explains that sorted input allows discarding half of the remaining interval based on the comparison.
Met - Complexity: The candidate clearly states O(log n) worst-case time and O(1) auxiliary space.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 2: Both observations are demonstrated: Search invariant and Progress and termination. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Search invariant: The candidate explicitly states the search invariant using the inclusive interval [low, high].
Met - Progress and termination: The candidate explains safe midpoint arithmetic, updates low=mid+1 and high=mid-1, and termination condition low>high.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 2: Both observations are demonstrated: Found and absent cases and Boundary cases. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Found and absent cases: Provides concrete found and absent test cases with expected results.
Met - Boundary cases: Provides empty, singleton, and duplicate test cases.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Level 2: Both observations are demonstrated: Executable search loop and Return contract. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Executable search loop: Provides the complete iterative Java binary search method with midpoint comparison and bound updates.
Met - Return contract: Confirms return -1 on absence and explains empty array handling without accessing the array.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q009.knowledge.1` (met): Trích dẫn nguyên văn *"Do mảng tăng dần, nếu giá trị giữa nhỏ hơn target thì mọi vị trí từ low đến mid cũng nhỏ hơn; nếu lớ"* -> The candidate explains that sorted input allows discarding half of the remaining interval based on the comparison.
  - Tiêu chí `demo.Q009.knowledge.2` (met): Trích dẫn nguyên văn *"Bản lặp có thời gian xấu nhất O(log n), bộ nhớ phụ O(1)."* -> The candidate clearly states O(log n) worst-case time and O(1) auxiliary space.
  - Tiêu chí `demo.Q009.analysis.1` (met): Trích dẫn nguyên văn *"Bất biến: nếu còn chỉ số khớp, nó nằm trong khoảng đóng [low, high]."* -> The candidate explicitly states the search invariant using the inclusive interval [low, high].
  - Tiêu chí `demo.Q009.analysis.2` (met): Trích dẫn nguyên văn *"Tính mid = low + (high - low) / 2 để tránh tràn tổng. Đặt low = mid + 1 nếu giá trị giữa nhỏ hơn tar"* -> The candidate explains safe midpoint arithmetic, updates low=mid+1 and high=mid-1, and termination condition low>high.
  - Tiêu chí `demo.Q009.testing.1` (met): Trích dẫn nguyên văn *"[2, 4, 9] tìm 4 trả 1, tìm 5 trả -1."* -> Provides concrete found and absent test cases with expected results.
  - Tiêu chí `demo.Q009.testing.2` (met): Trích dẫn nguyên văn *"[] tìm 4 trả -1; [4] tìm 4 trả 0; [4, 4] tìm 4 trả 0 hoặc 1 đều đúng."* -> Provides empty, singleton, and duplicate test cases.
  - Tiêu chí `demo.Q009.implementation.1` (met): Trích dẫn nguyên văn *"static int binarySearch(int[] values, int target) {
    int low = 0, high = values.length - 1;
    w"* -> Provides the complete iterative Java binary search method with midpoint comparison and bound updates.
  - Tiêu chí `demo.Q009.implementation.2` (met): Trích dẫn nguyên văn *"Hàm trả -1 sau vòng lặp nếu vắng target; mảng rỗng đặt high = -1 nên không đọc mảng."* -> Confirms return -1 on absence and explains empty array handling without accessing the array.
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
Met - Adjacent swaps: Candidate describes comparing adjacent elements and swapping when out of order.
Not met - Complexity: Candidate incorrectly states worst-case time as O(n log n) instead of O(n^2), and does not state correct space complexity or best-case behavior with early exit.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q010.knowledge.2] Complexity. Required: State quadratic worst-case time, constant auxiliary space and linear best-case time only when an early-exit flag is used.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 1: One of the two observations is demonstrated: Pass invariant / Shrinking region. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Pass invariant: Explains how the largest number bubbles up to the end of the region during a pass.
Not met - Shrinking region: Candidate explicitly states they do not shrink the region or use early termination on a no-swap pass.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q010.analysis.2] Shrinking region. Required: Explain excluding the sorted suffix and why a no-swap pass permits termination.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 1: One of the two observations is demonstrated: General sorting / Boundary and duplicate data. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - General sorting: Provides a nontrivial unsorted input with correct sorted output.
Not met - Boundary and duplicate data: Candidate failed to provide empty, singleton, and duplicate-containing examples with expected outputs.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q010.testing.2] Boundary and duplicate data. Required: Give empty, singleton and duplicate-containing examples with expected outputs.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q010.knowledge.1` (met): Trích dẫn nguyên văn *"So sánh các cặp kề và đổi chỗ nếu bên trái lớn hơn, rồi tiếp tục các lượt quét."* -> Candidate describes comparing adjacent elements and swapping when out of order.
  - Tiêu chí `demo.Q010.knowledge.2` (unmet): Trích dẫn nguyên văn *"Em tính thời gian xấu nhất là O(n log n)."* -> Candidate incorrectly states worst-case time as O(n log n) instead of O(n^2), and does not state correct space complexity or best-case behavior with early exit.
  - Tiêu chí `demo.Q010.analysis.1` (met): Trích dẫn nguyên văn *"Trong một lượt quét từ trái sang phải, số lớn nhất gặp lần lượt mọi số phía sau và tới cuối vùng."* -> Explains how the largest number bubbles up to the end of the region during a pass.
  - Tiêu chí `demo.Q010.analysis.2` (unmet): Trích dẫn nguyên văn *"Lượt sau em vẫn quét cả đoạn đuôi đã chốt; em không xét dừng khi cả lượt không đổi chỗ."* -> Candidate explicitly states they do not shrink the region or use early termination on a no-swap pass.
  - Tiêu chí `demo.Q010.testing.1` (met): Trích dẫn nguyên văn *"[9, 1, 4] phải ra [1, 4, 9]."* -> Provides a nontrivial unsorted input with correct sorted output.
  - Tiêu chí `demo.Q010.testing.2` (unmet): Thiếu ý (Omission) -> Candidate failed to provide empty, singleton, and duplicate-containing examples with expected outputs.
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
    - Điểm AI thực tế: **null (chưa đủ căn cứ)**
    - Căn cứ quy tắc: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.knowledge.1, demo.Q017.knowledge.2.
  - **Analysis** (`rubric.demo.Q017.analysis`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **null (chưa đủ căn cứ)**
    - Căn cứ quy tắc: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.analysis.1, demo.Q017.analysis.2.
  - **Testing** (`rubric.demo.Q017.testing`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **null (chưa đủ căn cứ)**
    - Căn cứ quy tắc: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.testing.1, demo.Q017.testing.2.
  - **Implementation** (`rubric.demo.Q017.implementation`):
    - Điểm kỳ vọng tham chiếu: **null (chưa đủ căn cứ)**
    - Điểm AI thực tế: **null (chưa đủ căn cứ)**
    - Căn cứ quy tắc: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.implementation.1, demo.Q017.implementation.2.
- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Knowledge: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.knowledge.1, demo.Q017.knowledge.2.
Insufficient evidence - Operator stack: The candidate explicitly states that the explanation is located in an unsubmitted draft, requiring an insufficientEvidence classification under the critical rule.
Insufficient evidence - Precedence and associativity: The candidate explicitly states that the content is in an unsubmitted draft, requiring insufficientEvidence.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.analysis.1, demo.Q017.analysis.2.
Insufficient evidence - Identify pending operators: The candidate states the analysis is in an unsubmitted draft, resulting in insufficientEvidence.
Insufficient evidence - Explain failure and complexity: The candidate indicates the explanation is in an unsubmitted draft, triggering insufficientEvidence.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.testing.1, demo.Q017.testing.2.
Insufficient evidence - Simple and precedence cases: The candidate points to an unsubmitted draft for test cases, requiring insufficientEvidence.
Insufficient evidence - Parentheses and associativity: The candidate references an unsubmitted draft for test outputs, triggering insufficientEvidence.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Insufficient evidence to select a level: possible values range from 0 to 2. Clarify: demo.Q017.implementation.1, demo.Q017.implementation.2.
Insufficient evidence - Concrete final drain: The candidate explicitly asserts the Java patch is in an unsubmitted draft, requiring insufficientEvidence.
Insufficient evidence - Patch placement and scope: The candidate states the patch placement details are in an unsubmitted draft, resulting in insufficientEvidence.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q017.knowledge.1` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate explicitly states that the explanation is located in an unsubmitted draft, requiring an insufficientEvidence classification under the critical rule.
  - Tiêu chí `demo.Q017.knowledge.2` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate explicitly states that the content is in an unsubmitted draft, requiring insufficientEvidence.
  - Tiêu chí `demo.Q017.analysis.1` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate states the analysis is in an unsubmitted draft, resulting in insufficientEvidence.
  - Tiêu chí `demo.Q017.analysis.2` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate indicates the explanation is in an unsubmitted draft, triggering insufficientEvidence.
  - Tiêu chí `demo.Q017.testing.1` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate points to an unsubmitted draft for test cases, requiring insufficientEvidence.
  - Tiêu chí `demo.Q017.testing.2` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate references an unsubmitted draft for test outputs, triggering insufficientEvidence.
  - Tiêu chí `demo.Q017.implementation.1` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate explicitly asserts the Java patch is in an unsubmitted draft, requiring insufficientEvidence.
  - Tiêu chí `demo.Q017.implementation.2` (insufficientEvidence): Trích dẫn nguyên văn *"Truy vết stack, vị trí bản sửa Java và các đầu ra mẫu nằm trong bản nháp chưa gửi; phần nộp này khôn"* -> The candidate states the patch placement details are in an unsubmitted draft, resulting in insufficientEvidence.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

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
Met - Frequency counts: The candidate correctly explains counting frequencies and reconstructing values in ascending order while preserving duplicates.
Met - Range-dependent cost: The candidate correctly explains O(n+k) time complexity and O(n+k) space complexity.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 2: Both observations are demonstrated: Empty and negative defects and Overflow and allocation limit. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Empty and negative defects: The candidate clearly identifies the empty array defect with max().getAsInt() and the negative-value indexing defect.
Met - Overflow and allocation limit: The candidate explains computing the range using long and rejecting values exceeding 1,000,000.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 2: Both observations are demonstrated: Empty, negatives and duplicates and Limit and overflow cases. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Empty, negatives and duplicates: The candidate provides concrete empty and mixed negative/duplicate test cases with expected sorted arrays.
Met - Limit and overflow cases: The candidate tests the accepted range boundary, one-over-boundary rejection, and extreme int values.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Level 2: Both observations are demonstrated: Counting implementation and Enforced width guard. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Counting implementation: The implementation includes an empty guard, min offset, frequency counts, and duplicate-preserving reconstruction.
Met - Enforced width guard: The code calculates the width in long and explicitly rejects an oversized width before allocation.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q018.knowledge.1` (met): Trích dẫn nguyên văn *"Đếm tần suất rồi duyệt giá trị tăng dần. Ghi ra mỗi giá trị đúng số lần đếm được nên giữ phần tử trù"* -> The candidate correctly explains counting frequencies and reconstructing values in ascending order while preserving duplicates.
  - Tiêu chí `demo.Q018.knowledge.2` (met): Trích dẫn nguyên văn *"Đặt k = max - min + 1. Thời gian O(n+k) và bộ nhớ O(n+k) tính cả bảng đếm k ô và mảng trả về n ô."* -> The candidate correctly explains O(n+k) time complexity and O(n+k) space complexity.
  - Tiêu chí `demo.Q018.analysis.1` (met): Trích dẫn nguyên văn *"max().getAsInt() lỗi khi đầu vào rỗng. Dùng trực tiếp giá trị âm làm chỉ số count cũng lỗi."* -> The candidate clearly identifies the empty array defect with max().getAsInt() and the negative-value indexing defect.
  - Tiêu chí `demo.Q018.analysis.2` (met): Trích dẫn nguyên văn *"Tính (long) max - min + 1 trước cấp phát; từ chối khi vượt 1.000.000 để tránh tràn int hoặc cấp phát"* -> The candidate explains computing the range using long and rejecting values exceeding 1,000,000.
  - Tiêu chí `demo.Q018.testing.1` (met): Trích dẫn nguyên văn *"[] → []; [3, -1, 3, 0, -1] → [-1, -1, 0, 3, 3]."* -> The candidate provides concrete empty and mixed negative/duplicate test cases with expected sorted arrays.
  - Tiêu chí `demo.Q018.testing.2` (met): Trích dẫn nguyên văn *"[-1, 999998] có range đúng 1.000.000, chấp nhận và trả [-1, 999998]. [-1, 999999] và [Integer.MIN_VA"* -> The candidate tests the accepted range boundary, one-over-boundary rejection, and extreme int values.
  - Tiêu chí `demo.Q018.implementation.1` (met): Trích dẫn nguyên văn *"static int[] countingSort(int[] values) {
    if (values.length == 0) return new int[0];
    int min"* -> The implementation includes an empty guard, min offset, frequency counts, and duplicate-preserving reconstruction.
  - Tiêu chí `demo.Q018.implementation.2` (met): Trích dẫn nguyên văn *"long width = (long) max - min + 1;
    if (width > 1_000_000L) throw new IllegalArgumentException("R"* -> The code calculates the width in long and explicitly rejects an oversized width before allocation.
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
Not met - Collection semantics: The candidate defines List as keeping unique values and Set as allowing duplicates, which completely reverses the standard semantics of List and Set, and incorrectly defines Map as a contiguous integer-indexed list.
Not met - Contract limits: The candidate incorrectly asserts that every Set is always sorted in ascending order and every Map always retains insertion order, failing to acknowledge that contract limits depend on specific implementations (e.g., HashSet vs TreeSet, HashMap vs LinkedHashMap).
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q022.knowledge.1] Collection semantics. Required: Distinguish ordered sequence with duplicates, unique elements, and key-to-value associations.
    + [demo.Q022.knowledge.2] Contract limits. Required: Do not assume every Set is sorted or every Map retains insertion order; connect ordering to the chosen implementation.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 0: Neither required observation is demonstrated. Condition: No check is confirmed as met and unresolved checks cannot change the result. 0/2 criteria were confirmed as met.
Not met - List and Set choices: The candidate suggests using Set for historical order with duplicates and List for deduplicating IDs, which contradicts the correct usage of these collections.
Not met - Map choice: The candidate explicitly rejects using Map for key-based lookups and provides incorrect reasoning about keys and values.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q022.analysis.1] List and Set choices. Required: Give suitable use cases for a sequence with duplicates and uniqueness membership.
    + [demo.Q022.analysis.2] Map choice. Required: Give a key-to-value lookup use case and distinguish a repeated key from repeated values.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q022.knowledge.1` (unmet): Trích dẫn nguyên văn *"List chỉ giữ giá trị duy nhất, Set cho trùng, Map là danh sách có chỉ số nguyên liên tục."* -> The candidate defines List as keeping unique values and Set as allowing duplicates, which completely reverses the standard semantics of List and Set, and incorrectly defines Map as a contiguous integer-indexed list.
  - Tiêu chí `demo.Q022.knowledge.2` (unmet): Trích dẫn nguyên văn *"Set nào cũng tự sắp xếp tăng và Map nào cũng luôn giữ thứ tự chèn."* -> The candidate incorrectly asserts that every Set is always sorted in ascending order and every Map always retains insertion order, failing to acknowledge that contract limits depend on specific implementations (e.g., HashSet vs TreeSet, HashMap vs LinkedHashMap).
  - Tiêu chí `demo.Q022.analysis.1` (unmet): Trích dẫn nguyên văn *"Em dùng Set để giữ nguyên thứ tự lịch sử có lượt lặp, List để tự loại trùng ID."* -> The candidate suggests using Set for historical order with duplicates and List for deduplicating IDs, which contradicts the correct usage of these collections.
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
    - Điểm AI thực tế: **1.0 đ**
    - Căn cứ quy tắc: Level 1: One of the two observations is demonstrated: Repeated lookup benefit / Missing key behavior. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
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
Met - Keyed lookup: Candidate chooses HashMap keyed by unique employee ID and values as Employee.
Not met - Cost distinction: Candidate incorrectly claims O(1) worst-case lookup.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q028.knowledge.2] Cost distinction. Required: State expected O(1) lookup, O(n) index construction and O(n) extra storage; do not claim worst-case constant lookup.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 1: One of the two observations is demonstrated: Repeated lookup benefit / Missing key behavior. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Repeated lookup benefit: Explains that building an index once avoids scanning all employees for each lookup.
Not met - Missing key behavior: Fails to define proper missing key behavior, instead stating it will call methods on null.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q028.analysis.2] Missing key behavior. Required: Define what happens for a missing employee ID under the stated unique-ID constraint.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 1: One of the two observations is demonstrated: Existing employee / Missing and empty data. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Existing employee: Provides a concrete existing-ID example and the expected employee.
Not met - Missing and empty data: Candidate does not test a missing ID or an empty input collection properly.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q028.testing.2] Missing and empty data. Required: Test a missing ID and an empty input collection with a not-found result.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Implementation: Level 1: One of the two observations is demonstrated: Build Java index / Handle null result. Condition: At least one check is met; both checks are required for level 2. 1/2 criteria were confirmed as met.
Met - Build Java index: Provides Java code to build map from employees and look up targetId.
Not met - Handle null result: Explicitly fails to handle null result safely, causing a NullPointerException.
  - **Vấn đề cần khắc phục & làm rõ**:
    + [demo.Q028.implementation.2] Handle null result. Required: The supplied implementation must handle a missing lookup without dereferencing null.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q028.knowledge.1` (met): Trích dẫn nguyên văn *"Dùng HashMap với ID nhân viên làm khóa duy nhất, Employee làm giá trị."* -> Candidate chooses HashMap keyed by unique employee ID and values as Employee.
  - Tiêu chí `demo.Q028.knowledge.2` (unmet): Trích dẫn nguyên văn *"Em tính dựng chỉ mục O(1) và tra luôn O(1), cả xấu nhất."* -> Candidate incorrectly claims O(1) worst-case lookup.
  - Tiêu chí `demo.Q028.analysis.1` (met): Trích dẫn nguyên văn *"Dựng bảng một lần để tránh quét lại 10.000 nhân viên cho từng lượt."* -> Explains that building an index once avoids scanning all employees for each lookup.
  - Tiêu chí `demo.Q028.analysis.2` (unmet): Trích dẫn nguyên văn *"Nếu ID vắng, em vẫn gọi getId trên kết quả trả về và không có nhánh not-found."* -> Fails to define proper missing key behavior, instead stating it will call methods on null.
  - Tiêu chí `demo.Q028.testing.1` (met): Trích dẫn nguyên văn *"Nếu ID 7 là An, tra 7 phải trả An."* -> Provides a concrete existing-ID example and the expected employee.
  - Tiêu chí `demo.Q028.testing.2` (unmet): Thiếu ý (Omission) -> Candidate does not test a missing ID or an empty input collection properly.
  - Tiêu chí `demo.Q028.implementation.1` (met): Trích dẫn nguyên văn *"Map<Long, Employee> index = new HashMap<>();
for (Employee employee : employees) index.put(employee."* -> Provides Java code to build map from employees and look up targetId.
  - Tiêu chí `demo.Q028.implementation.2` (unmet): Trích dẫn nguyên văn *"Đoạn trên gọi result.getId kể cả khi get trả null."* -> Explicitly fails to handle null result safely, causing a NullPointerException.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

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
Met - Unit boundary: The candidate explains isolating service behavior from a real database by replacing the repository dependency.
Met - Test double: The candidate explains using mocks/fakes to control repository responses and clearly distinguishes this from integration testing.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Analysis: Level 2: Both observations are demonstrated: Arrange act assert and Meaningful verification. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Arrange act assert: The candidate describes injecting the test double, arranging responses, invoking the service method, and asserting outcomes.
Met - Meaningful verification: The candidate explains verifying important side effects without making every internal method call part of the contract.
  - **Điểm mạnh / Nhận xét tổng quan**: For this question, Testing: Level 2: Both observations are demonstrated: Success and missing data and Validation and dependency failure. Condition: Both checks are confirmed as met. 2/2 criteria were confirmed as met.
Met - Success and missing data: The candidate provides concrete success (user found) and missing-data (not found) scenarios with explicit expected service outcomes.
Met - Validation and dependency failure: The candidate provides invalid-input and repository-failure scenarios along with the expected outcomes.
- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:
  - Tiêu chí `demo.Q085.knowledge.1` (met): Trích dẫn nguyên văn *"Kiểm thử logic UserService bằng cách thay phụ thuộc Repository để chạy độc lập với cơ sở dữ liệu thậ"* -> The candidate explains isolating service behavior from a real database by replacing the repository dependency.
  - Tiêu chí `demo.Q085.knowledge.2` (met): Trích dẫn nguyên văn *"Mock hoặc fake cho phép đặt sẵn dữ liệu trả về hay lỗi. Integration test riêng mới kiểm tra Reposito"* -> The candidate explains using mocks/fakes to control repository responses and clearly distinguishes this from integration testing.
  - Tiêu chí `demo.Q085.analysis.1` (met): Trích dẫn nguyên văn *"Inject mock vào Service, sắp đặt phản hồi cho từng ID, gọi findUser rồi assert giá trị hoặc lỗi theo"* -> The candidate describes injecting the test double, arranging responses, invoking the service method, and asserting outcomes.
  - Tiêu chí `demo.Q085.analysis.2` (met): Trích dẫn nguyên văn *"Với nghiệp vụ lưu, xác minh đúng bản ghi được lưu khi hợp lệ và không lưu khi sai; không verify mọi "* -> The candidate explains verifying important side effects without making every internal method call part of the contract.
  - Tiêu chí `demo.Q085.testing.1` (met): Trích dẫn nguyên văn *"findUser(7) trả người dùng ID 7 nếu có bản ghi, hoặc trả not-found nếu repo không có bản ghi."* -> The candidate provides concrete success (user found) and missing-data (not found) scenarios with explicit expected service outcomes.
  - Tiêu chí `demo.Q085.testing.2` (met): Trích dẫn nguyên văn *"ID 0 phải bị từ chối trước khi gọi repo. Nếu repo ném lỗi truy cập thì Service phải báo lỗi theo hợp"* -> The candidate provides invalid-input and repository-failure scenarios along with the expected outcomes.
- **Đánh giá ca kiểm thử**: **Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R).**

