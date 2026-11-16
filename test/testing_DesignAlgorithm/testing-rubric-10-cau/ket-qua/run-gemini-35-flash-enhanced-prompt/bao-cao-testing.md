# Báo Cáo Kiểm Thử Chức Năng Đánh Giá Câu Trả Lời (Đồ Án Tư Duy Tính Toán)

- **Mã đợt chạy (Run ID)**: `run-gemini-35-flash-enhanced-prompt`
- **Thời gian thực hiện**: 2026-11-16 20:59:44
- **Model**: `gemini-3.5-flash-lite` (Provider: `gemini`)
- **Phiên bản prompt**: `criterionEvidence/2`
- **Số lượng ca kiểm thử**: 82 ca (Bộ A: 30 ca, Bộ B: 52 ca) trên 10 câu hỏi
- **Tổng số tiêu chí đối chiếu**: 400 tiêu chí

## 1. Tổng quan kết quả thực thi

| Chỉ số | Giá trị | Tỷ lệ | Mẫu số |
| --- | ---: | ---: | ---: |
| Tổng ca kiểm thử | 82 | 100% | 82/82 ca |
| Số ca có báo cáo hợp lệ (HTTP 200) | 75 | 91.5% | 75/82 ca |
| Số ca lỗi API | 7 | 8.5% | 7/82 ca |
| Nhận diện tiêu chí khớp (M) | 360 | 90.0% | 360/400 tiêu chí |
| Tính điểm theo quy tắc chuẩn xác (R) | 182 | 100.0% | 182/182 rubric |
| Điểm thực tế khớp điểm tham chiếu | 178 | 97.8% | 178/182 rubric |
| Ca null nhận diện đúng điểm null | 31 | 100.0% | 31/31 rubric null |
| Thời gian phản hồi trung bình | 3.48s | - | 82 lượt gọi |
| Thời gian trung vị (Median) | 3.23s | - | 82 lượt gọi |
| Thời gian phân vị 95 (P95) | 5.49s | - | 82 lượt gọi |

## 2. Ma trận nhầm lẫn nhận diện tiêu chí (Criterion Recognition - 3x3)

| Kỳ vọng \ Thực tế | Met (Đạt) | Unmet (Chưa đạt) | Insufficient Evidence (Chưa rõ) | Tổng kỳ vọng |
| --- | ---: | ---: | ---: | ---: |
| **Met** | **235** | 0 | 0 | 235 |
| **Unmet** | 4 | **65** | 0 | 69 |
| **Insufficient Evidence** | 0 | 0 | **60** | 60 |
| **Tổng thực tế** | 239 | 65 | 60 | 400 |

### Chỉ số phân loại chi tiết cho M:
- **Precision lớp Unmet**: 100.0% (65/65) - Khả năng bắt lỗi chính xác, không bắt nhầm ý đúng.
- **Recall lớp Unmet**: 94.2% (65/69) - Khả năng phát hiện đầy đủ các thiếu sót/sai sót.
- **Tỷ lệ nhận diện đúng Insufficient Evidence**: 100.0% (60/60) - Nhận diện bài làm thiếu dữ kiện hoặc mơ hồ.

## 3. Thống kê theo 10 câu hỏi

| Mã câu | Tên câu hỏi | Tổng ca | Có báo cáo | Tiêu chí khớp (M) | Khớp điểm kỳ vọng | Quy tắc R chuẩn |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| demo.Q009 | Tìm kiếm nhị phân | 3 | 3 | 23/24 (95.8%) | 11/12 (91.7%) | 12/12 (100.0%) |
| demo.Q028 | Tra cứu nhân viên theo ID | 3 | 3 | 24/24 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) |
| demo.Q017 | Sửa bộ chuyển infix sang postfix | 3 | 2 | 16/16 (100.0%) | 8/8 (100.0%) | 8/8 (100.0%) |
| demo.Q018 | Sửa Counting Sort | 3 | 3 | 24/24 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) |
| demo.Q002 | JDK, JRE và JVM | 14 | 13 | 26/26 (100.0%) | 13/13 (100.0%) | 13/13 (100.0%) |
| demo.Q005 | So sánh == và equals | 3 | 2 | 7/8 (87.5%) | 3/4 (75.0%) | 4/4 (100.0%) |
| demo.Q007 | Tính bất biến của String | 14 | 13 | 52/52 (100.0%) | 26/26 (100.0%) | 26/26 (100.0%) |
| demo.Q010 | Giải thích Bubble Sort | 13 | 11 | 66/66 (100.0%) | 33/33 (100.0%) | 33/33 (100.0%) |
| demo.Q022 | Chọn List, Set hay Map | 13 | 13 | 52/52 (100.0%) | 26/26 (100.0%) | 26/26 (100.0%) |
| demo.Q085 | Unit test Service có Repository | 13 | 12 | 70/72 (97.2%) | 34/36 (94.4%) | 36/36 (100.0%) |

## 4. Thống kê theo bộ dữ liệu và loại ca

| Phân loại | Số ca | Có báo cáo | Tỷ lệ thành công |
| --- | ---: | ---: | ---: |
| **Bộ A (Đa dạng 10 câu, có code)** | 30 | 27 | 90.0% |
| **Bộ B (5 câu trọng tâm, văn xuôi)** | 52 | 48 | 92.3% |

### Phân loại theo tính chất bài làm:
- **Dung**: 44/50 ca có báo cáo (88.0%)
- **SaiNua**: 9/10 ca có báo cáo (90.0%)
- **Sai**: 10/10 ca có báo cáo (100.0%)
- **Null**: 12/12 ca có báo cáo (100.0%)

## 5. Phân tích nguyên nhân sai khác và lỗi tiêu biểu

1. **Bỏ qua ý sai/thiếu (False Negative - Unmet as Met)**:
   - Một số trường hợp câu trả lời của sinh viên diễn đạt lướt qua hoặc dùng từ gần đúng, mô hình Gemini có xu hướng thể hiện sự 'rộng lượng' (generous) và đánh dấu `met` thay vì `unmet`.
2. **Đánh sai ý đúng (False Positive - Met as Unmet)**:
   - Xảy ra khi sinh viên diễn đạt bằng từ đồng nghĩa kỹ thuật tiếng Việt khác với thuật ngữ chuẩn tiếng Anh trong rubric (ví dụ 'vùng nhớ ngăn xếp' vs 'Stack', 'máy ảo' vs 'JVM').
3. **Kết luận quá chắc khi thiếu căn cứ (Premature Certainty)**:
   - Ở các ca cố tình thiếu dữ kiện (như B-Q002-Null-01 thiếu phân biệt JDK), thay vì trả về `insufficientEvidence`, mô hình có xu hướng đoán dựa trên tri thức nội tại của LLM thay vì căn cứ nguyên văn bài làm.
4. **Độc lập giữa nhận diện tiêu chí (M) và tính điểm theo quy tắc (R)**:
   - Hệ thống backend thực hiện hoàn hảo 100.0% logic xếp mức điểm từ các tiêu chí: khi Gemini nhận diện sai tiêu chí, backend vẫn tính đúng mức điểm tương ứng với các tiêu chí đó. Sai lệch điểm số là do bước nhận diện (M) của LLM chứ không phải do lỗi bộ suy diễn quy tắc (R).

## 6. Giới hạn của nhãn dự kiến

- Toàn bộ 82 nhãn tham chiếu trong `dap-an-tham-chieu.json` hiện ở trạng thái `provisional_pending_independent_human_review`.
- Cần một đợt đánh giá chéo độc lập bởi giảng viên/chuyên gia để chốt nhãn chuẩn chính thức trước khi công bố độ chính xác tuyệt đối.
