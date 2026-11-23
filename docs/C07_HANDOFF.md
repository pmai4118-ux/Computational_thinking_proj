# Bàn giao công việc `C07` và cập nhật trạng thái MVP

- **Ngày cập nhật:** 23/11/2026
- **Nhánh nền:** `Demo` (sau mốc bàn giao `341e833` trong `docs/DEMO_HANDOFF.md`)
- **Phạm vi phiên làm việc này:** Hoàn tất cài đặt và kiểm tra ngoại tuyến công việc **`C07`** (*Chuẩn bị 24 câu trả lời kiểm định*), cập nhật `README.md` và biên bản bàn giao này.
- **Lớp MVC-S / phạm vi bị tác động:** Chỉ bổ sung tệp ở tầng `Content / QA / Docs`; **không sửa** bất kỳ mã nguồn nào trong `source/` hay các fixture API/review hiện có.

---

## 1. Tóm tắt những gì đã hoàn thành trong phiên này (`C07`)

| Tệp tạo mới / cập nhật | Vai trò | Chi tiết đã triển khai |
| --- | --- | --- |
| `test/fixtures/answers/programming.json` | Content / QA | 6 câu trả lời tổng hợp tiếng Việt cho 2 câu `C02` (`mutable_default_arg`, `closure_late_binding`), phủ đủ 6 dạng (`correct`, `equivalent`, `partial`, `wrong`, `ambiguous`, `prompt_injection`), chia 3 `calibration` / 3 `held_out`. |
| `test/fixtures/answers/cases.json` | Content / QA | 6 câu trả lời tổng hợp tiếng Việt cho 2 câu `C03` (`inventory_race`, `transfer_deadlock`), phủ đủ 6 dạng, chia 3 `calibration` / 3 `held_out`. |
| `test/fixtures/answers/algorithms.json` | Content / QA | 6 câu trả lời tổng hợp tiếng Việt cho 2 câu `C04` (`bisect_left_bounds`, `balanced_brackets_stack`), phủ đủ 6 dạng, chia 3 `calibration` / 3 `held_out`. |
| `test/fixtures/answers/ai_review.json` | Content / QA | 6 câu trả lời tổng hợp tiếng Việt cho 2 câu `C05` (`binary_search_precheck`, `sql_query_parameterization`), phủ đủ 6 dạng, chia 3 `calibration` / 3 `held_out`. |
| `test/fixtures/expected_evaluations.json` | Content / QA | 24 bản ghi đánh giá tham chiếu (72 tiêu chí), khớp 1-1 với rubric trong `data/seed/questions/*.json`, có `satisfied_expected_indexes`, trích dẫn nguyên văn + chỉ số Unicode chính xác (`answer_text[start:end] == quote`) hoặc `observation`, bảo toàn `null` vs `0` và khung `adjudication`. |
| `docs/evaluation_protocol.md` | Docs / QA | Đặc tả phân bổ 24 mẫu, quy tắc khóa cứng tập `12 calibration / 12 held_out`, quy trình gán nhãn/chốt bất đồng độc lập và ngưỡng nghiệm thu đăng ký trước cho `Q03` (100% quote hợp lệ, 100% điểm Python nhất quán, >= 85% đồng thuận nhãn xác định được). |
| `test/content/test_c07_evaluation_dataset.py` | QA | 3 ca kiểm thử tự động ngoại tuyến bằng `pytest` xác minh đủ 24 mẫu/72 tiêu chí, cân bằng split/nhóm/dạng, khớp seed catalog, khớp trích dẫn nguyên văn, hợp lệ qua domain model `Answer`/`Evidence`/`CriterionCheck`/`EvaluationResult` và không có dữ liệu cá nhân thật. |
| `README.md` | Docs | Cập nhật danh mục năng lực hiện có, sơ đồ cấu trúc MVC-S, lệnh kiểm tra seed (`C08`) & bộ kiểm định (`C07`), và liên kết sang `docs/C07_HANDOFF.md`. |
| `docs/C07_HANDOFF.md` | Docs | Biên bản bàn giao trạng thái mới nhất cho người tiếp nhận. |

### Kết quả kiểm chứng cần giữ làm mốc hồi quy

Chạy từ thư mục gốc repository trên PowerShell:

```powershell
uv run --locked python -m pytest test/content/test_c07_evaluation_dataset.py -v
uv run --locked python -m pytest -q
uv pip check