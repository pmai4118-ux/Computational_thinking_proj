# Mẫu JSON câu hỏi và rubric — C02 đến C05

Format đề xuất để nhóm chốt ở P03/P05. Đây là mẫu tự soạn minh họa cấu trúc, không phải câu hỏi nguồn mở đã được xác minh. Các file example_only=true, source/license còn null, review.status=draft, nên chưa đủ điều kiện import. Các đường dẫn thuộc ứng dụng Python tại repository gốc.

## C02: Đối số mặc định có thể thay đổi trong Python

Mẫu minh họa tự soạn · format đề xuất cho P03/P05 · draft · chưa đủ điều kiện import. Source/license để null có chủ đích, không phải nguồn đã được xác minh.

### Cách lưu

1. Chốt các tên trường và skill IDs với P03/C01 trước khi viết importer. Các example.* ID trong mẫu không phải danh mục kỹ năng đã phê duyệt.
2. Tạo bản ghi thật với ID mới trong mảng JSON ở data/seed/questions/programming.json; thêm vào mảng có sẵn, không ghi đè các câu khác. Rubric được nhúng trong từng question và có ID/version riêng.
3. Thêm source record cùng source_id vào mảng data/seed/source_registry.json. Điền URL file gốc, revision nếu có, giấy phép, tác giả và original_content; giữ bản gốc riêng với prompt đã dịch/adapt.
4. Lưu câu trả lời tổng hợp và nhãn reviewer ở test/fixtures/question_reviews/c02.json. Fixture và rubric chứa căn cứ đáp án dùng phía server/reviewer; trước khi người học trả lời, View chỉ nhận nội dung đề qua DTO đã chốt ở P04.
5. Ghi nội dung dịch/sửa trong adaptation và ghi công trong docs/THIRD_PARTY_NOTICES.md. Dùng mẫu để hiểu cấu trúc; không chỉ đổi example_only thành false rồi xem như câu đã tuyển chọn.

### Cách review

1. Người tuyển chọn mở PR với question, source record, notice và fixture; giữ review.status=draft hoặc pending_review.
2. Một người khác kiểm tra nguồn/giấy phép, nội dung kỹ thuật, ranh giới 0–1–2, lời giải tương đương và các ví dụ review.
3. Chỉ ghi checks=true cho điều đã kiểm tra. Chỉ approved khi tất cả checks=true, reviewer_id khác curator_id, có reviewed_at và provenance thực đầy đủ.
4. C08/importer cần kiểm tra cả approval và provenance, từ chối mọi example_only=true. Chưa đủ căn cứ giữ score=null; chỉ cộng tổng khi mọi tiêu chí đều chấm được.

### Question record

Lưu ở: `data/seed/questions/programming.json`

```json
[
  {
    "schema_version": "question-record/0.1-proposal",
    "example_only": true,
    "id": "example.c02.v1",
    "version": 1,
    "category": "programming_knowledge",
    "language": "vi",
    "role": "backend_developer",
    "level": "intern_fresher",
    "skill_ids": [
      "example.python.default_arguments"
    ],
    "source_id": "example.source.c02",
    "prompt": "Đoạn code in ra gì? Giải thích nguyên nhân và sửa để các lần gọi không truyền bucket có list riêng. Nếu truyền bucket, hàm phải append vào chính list đó. Đề xuất kiểm thử cho bản sửa.",
    "code": "def add_item(value, bucket=[]):\n    bucket.append(value)\n    return bucket\n\nfirst = add_item(1)\nsecond = add_item(2)\nprint(first)\nprint(second)",
    "code_language": "python",
    "constraints": [
      "Giả sử Python 3; hai lệnh print chạy sau cả hai lần gọi.",
      "Giữ hành vi thêm vào list mà người gọi truyền rõ ràng, kể cả list rỗng."
    ],
    "adaptation": {
      "kind": "illustrative_authored_example",
      "summary": "Mẫu tự soạn để minh họa format, không phải câu hỏi nguồn mở đã xác minh. Thay bằng nội dung đã tuyển chọn và ghi lại thay đổi.",
      "translator_id": null
    },
    "rubric": {
      "id": "rubric.c02.v1",
      "version": 1,
      "criteria": [
        {
          "id": "c02.default_semantics",
          "label": "Giải thích kết quả và nguyên nhân",
          "expected_evidence": [
            "Hai lần print đều là [1, 2].",
            "Đối số mặc định được tạo một lần và list bị dùng chung."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Khẳng định hai list độc lập hoặc giải thích sai nguyên nhân."
            },
            {
              "score": 1,
              "description": "Nêu đúng kết quả nhưng chưa giải thích vì sao list dùng chung."
            },
            {
              "score": 2,
              "description": "Nêu đúng cả hai kết quả, thời điểm tạo mặc định và tác động mutation."
            }
          ],
          "equivalent_answers": "Chấp nhận diễn đạt tương đương về cùng đối tượng list; không cần khớp từ khóa."
        },
        {
          "id": "c02.safe_fix",
          "label": "Sửa đúng hợp đồng",
          "expected_evidence": [
            "Mỗi lần bỏ qua bucket tạo list mới.",
            "List truyền tường minh vẫn được dùng, kể cả []."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Bản sửa vẫn dùng chung list mặc định hoặc không tạo được list riêng khi bỏ qua tham số."
            },
            {
              "score": 1,
              "description": "Tạo được list mặc định riêng nhưng chưa giữ đúng list truyền tường minh, chẳng hạn dùng bucket or []."
            },
            {
              "score": 2,
              "description": "Tạo list mới chỉ khi tham số bị bỏ qua và giữ đúng list đã truyền."
            }
          ],
          "equivalent_answers": "None guard hoặc sentinel đúng đều hợp lệ; không bắt buộc một mẫu code duy nhất."
        },
        {
          "id": "c02.tests",
          "label": "Kiểm chứng bằng ví dụ cụ thể",
          "expected_evidence": [
            "Hai lần gọi bỏ qua bucket độc lập.",
            "Một list rỗng truyền vào được cập nhật và giữ identity."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Không đưa kiểm thử dù đề yêu cầu hoặc kiểm thử khẳng định sai kết quả."
            },
            {
              "score": 1,
              "description": "Có một kiểm thử đúng nhưng thiếu một hành vi bắt buộc."
            },
            {
              "score": 2,
              "description": "Có kiểm thử cụ thể cho cả hai hành vi và kết quả mong đợi."
            }
          ],
          "equivalent_answers": "Chấp nhận assert hoặc mô tả input/output đủ rõ để người khác chạy lại."
        }
      ],
      "scoring": {
        "allowed_scores": [
          0,
          1,
          2
        ],
        "maximum_score": 6,
        "total_policy": "sum_only_when_every_criterion_is_decidable",
        "insufficient_evidence": {
          "score": null,
          "reason_required": true,
          "total_score": null
        },
        "missing_required_content": "Có thể là unmet/0 nếu rubric yêu cầu rõ và quan sát được nội dung bị thiếu; tệp/ngữ cảnh được viện dẫn nhưng chưa có thì chưa đủ căn cứ.",
        "provider_failure": "processing_error, không gán điểm hoặc kết luận năng lực",
        "equivalent_answers": "Chấp nhận phương án khác đúng theo ràng buộc; không so khớp chữ với đáp án mẫu."
      }
    },
    "review": {
      "status": "draft",
      "curator_id": null,
      "reviewer_id": null,
      "reviewed_at": null,
      "checks": {
        "source_and_license_verified": null,
        "original_and_adaptation_preserved": null,
        "technical_correctness_checked": null,
        "rubric_levels_distinct": null,
        "equivalent_answers_checked": null,
        "review_cases_checked": null
      },
      "notes": "Mẫu minh họa, không import vào ngân hàng thật. Bản ghi thật cần nguồn hợp lệ, người review khác người tuyển chọn và đầy đủ kiểm tra."
    }
  }
]
```

### Source registry

Lưu ở: `data/seed/source_registry.json`

```json
[
  {
    "schema_version": "source-record/0.1-proposal",
    "example_only": true,
    "id": "example.source.c02",
    "title": null,
    "url": null,
    "file_path": null,
    "revision": null,
    "authors": [],
    "collected_at": null,
    "original_language": null,
    "original_content": {
      "question_text": null,
      "code": null
    },
    "license": {
      "spdx_id": null,
      "url": null,
      "required_notice": null,
      "status": "not_checked"
    }
  }
]
```

### Review fixture

Lưu ở: `test/fixtures/question_reviews/c02.json`

```json
{
  "schema_version": "review-fixture/0.1-proposal",
  "example_only": true,
  "review_status": "illustrative_unreviewed",
  "question_id": "example.c02.v1",
  "question_version": 1,
  "rubric_id": "rubric.c02.v1",
  "cases": [
    {
      "label": "Câu trả lời minh họa đáp ứng rubric",
      "answer": "Cả hai lần print đều là [1, 2], vì bucket mặc định được tạo một lần và dùng chung. Tôi dùng bucket=None rồi chỉ tạo [] khi bucket is None. Test hai lần gọi không truyền bucket phải trả [1] và [2] riêng; truyền b=[] thì kết quả phải là b và b thành [3].",
      "answer_context": {
        "missing_attachment": false
      },
      "checks": [
        {
          "criterion_id": "c02.default_semantics",
          "status": "met",
          "score": 2,
          "evidence_quote": "bucket mặc định được tạo một lần và dùng chung",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c02.safe_fix",
          "status": "met",
          "score": 2,
          "evidence_quote": "chỉ tạo [] khi bucket is None",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c02.tests",
          "status": "met",
          "score": 2,
          "evidence_quote": "truyền b=[] thì kết quả phải là b và b thành [3]",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        }
      ],
      "expected_total": 6
    },
    {
      "label": "Thiếu tệp được viện dẫn: chưa thể chấm",
      "answer": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
      "answer_context": {
        "missing_attachment": true
      },
      "checks": [
        {
          "criterion_id": "c02.default_semantics",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c02.safe_fix",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c02.tests",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        }
      ],
      "expected_total": null
    }
  ],
  "notes": "Ví dụ giúp reviewer hiểu cách áp dụng rubric, không phải bộ benchmark đã được kiểm định. Lưu riêng khỏi dữ liệu hiển thị cho người học."
}
```

## C03: Hai yêu cầu mua sản phẩm cuối cùng

Mẫu minh họa tự soạn · format đề xuất cho P03/P05 · draft · chưa đủ điều kiện import. Source/license để null có chủ đích, không phải nguồn đã được xác minh.

### Cách lưu

1. Chốt các tên trường và skill IDs với P03/C01 trước khi viết importer. Các example.* ID trong mẫu không phải danh mục kỹ năng đã phê duyệt.
2. Tạo bản ghi thật với ID mới trong mảng JSON ở data/seed/questions/cases.json; thêm vào mảng có sẵn, không ghi đè các câu khác. Rubric được nhúng trong từng question và có ID/version riêng.
3. Thêm source record cùng source_id vào mảng data/seed/source_registry.json. Điền URL file gốc, revision nếu có, giấy phép, tác giả và original_content; giữ bản gốc riêng với prompt đã dịch/adapt.
4. Lưu câu trả lời tổng hợp và nhãn reviewer ở test/fixtures/question_reviews/c03.json. Fixture và rubric chứa căn cứ đáp án dùng phía server/reviewer; trước khi người học trả lời, View chỉ nhận nội dung đề qua DTO đã chốt ở P04.
5. Ghi nội dung dịch/sửa trong adaptation và ghi công trong docs/THIRD_PARTY_NOTICES.md. Dùng mẫu để hiểu cấu trúc; không chỉ đổi example_only thành false rồi xem như câu đã tuyển chọn.

### Cách review

1. Người tuyển chọn mở PR với question, source record, notice và fixture; giữ review.status=draft hoặc pending_review.
2. Một người khác kiểm tra nguồn/giấy phép, nội dung kỹ thuật, ranh giới 0–1–2, lời giải tương đương và các ví dụ review.
3. Chỉ ghi checks=true cho điều đã kiểm tra. Chỉ approved khi tất cả checks=true, reviewer_id khác curator_id, có reviewed_at và provenance thực đầy đủ.
4. C08/importer cần kiểm tra cả approval và provenance, từ chối mọi example_only=true. Chưa đủ căn cứ giữ score=null; chỉ cộng tổng khi mọi tiêu chí đều chấm được.

### Question record

Lưu ở: `data/seed/questions/cases.json`

```json
[
  {
    "schema_version": "question-record/0.1-proposal",
    "example_only": true,
    "id": "example.c03.v1",
    "version": 1,
    "category": "technical_case",
    "language": "vi",
    "role": "backend_developer",
    "level": "intern_fresher",
    "skill_ids": [
      "example.backend.concurrent_inventory"
    ],
    "source_id": "example.source.c03",
    "prompt": "Kho còn một sản phẩm. Hai yêu cầu mua đến đồng thời, có thể tới hai instance ứng dụng khác nhau. Đề xuất cách chỉ tạo tối đa một đơn thành công, không âm kho; giải thích transaction và cách kiểm thử.",
    "code": null,
    "code_language": null,
    "constraints": [
      "Cơ sở dữ liệu được dùng chung giữa các instance.",
      "Nếu tạo đơn thất bại thì thay đổi tồn kho cũng phải rollback.",
      "Không yêu cầu thiết kế cơ chế thanh toán hoặc giao hàng."
    ],
    "adaptation": {
      "kind": "illustrative_authored_example",
      "summary": "Mẫu tự soạn để minh họa format, không phải câu hỏi nguồn mở đã xác minh. Thay bằng nội dung đã tuyển chọn và ghi lại thay đổi.",
      "translator_id": null
    },
    "rubric": {
      "id": "rubric.c03.v1",
      "version": 1,
      "criteria": [
        {
          "id": "c03.race",
          "label": "Nhận ra thao tác tranh chấp",
          "expected_evidence": [
            "Hai luồng có thể cùng đọc stock=1 trước khi ghi.",
            "Phân tích phải áp dụng cho nhiều instance."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Cho rằng đọc rồi ghi riêng lẻ luôn an toàn."
            },
            {
              "score": 1,
              "description": "Nhận ra đồng thời nhưng chưa chỉ ra khoảng tranh chấp hoặc phạm vi nhiều instance."
            },
            {
              "score": 2,
              "description": "Mô tả được interleaving đọc-kiểm-tra-ghi và phạm vi nhiều instance."
            }
          ],
          "equivalent_answers": "Không bắt buộc gọi đúng tên race condition nếu giải thích đúng bản chất."
        },
        {
          "id": "c03.atomicity",
          "label": "Giữ bất biến tại dữ liệu chia sẻ",
          "expected_evidence": [
            "Điều kiện mua và trừ kho được bảo vệ nguyên tử.",
            "Tạo đơn và trừ kho thuộc transaction có rollback."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Chỉ dùng khóa RAM từng instance hoặc vẫn để hai đơn cùng thành công."
            },
            {
              "score": 1,
              "description": "Có cơ chế bảo vệ kho nhưng chưa bao quát transaction tạo đơn/rollback."
            },
            {
              "score": 2,
              "description": "Cơ chế ở dữ liệu chia sẻ bảo đảm tối đa một thành công và rollback đúng khi tạo đơn lỗi."
            }
          ],
          "equivalent_answers": "Chấp nhận conditional update kèm kiểm tra affected rows, row lock/transaction, hoặc optimistic concurrency có xử lý xung đột đúng."
        },
        {
          "id": "c03.concurrent_tests",
          "label": "Kiểm thử bất biến",
          "expected_evidence": [
            "Gửi hai yêu cầu đồng thời qua hai instance.",
            "Kiểm tra số đơn, tồn kho và rollback khi chèn đơn lỗi."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Không đề xuất test hoặc kết quả mong đợi vi phạm bất biến."
            },
            {
              "score": 1,
              "description": "Có test hai yêu cầu nhưng thiếu kiểm tra đơn/tồn kho hoặc rollback."
            },
            {
              "score": 2,
              "description": "Test đồng thời và test rollback đều có assertion rõ cho số đơn và tồn kho."
            }
          ],
          "equivalent_answers": "Không bắt buộc framework kiểm thử; phải nêu được cách tạo đồng thời và kiểm tra kết quả."
        }
      ],
      "scoring": {
        "allowed_scores": [
          0,
          1,
          2
        ],
        "maximum_score": 6,
        "total_policy": "sum_only_when_every_criterion_is_decidable",
        "insufficient_evidence": {
          "score": null,
          "reason_required": true,
          "total_score": null
        },
        "missing_required_content": "Có thể là unmet/0 nếu rubric yêu cầu rõ và quan sát được nội dung bị thiếu; tệp/ngữ cảnh được viện dẫn nhưng chưa có thì chưa đủ căn cứ.",
        "provider_failure": "processing_error, không gán điểm hoặc kết luận năng lực",
        "equivalent_answers": "Chấp nhận phương án khác đúng theo ràng buộc; không so khớp chữ với đáp án mẫu."
      }
    },
    "review": {
      "status": "draft",
      "curator_id": null,
      "reviewer_id": null,
      "reviewed_at": null,
      "checks": {
        "source_and_license_verified": null,
        "original_and_adaptation_preserved": null,
        "technical_correctness_checked": null,
        "rubric_levels_distinct": null,
        "equivalent_answers_checked": null,
        "review_cases_checked": null
      },
      "notes": "Mẫu minh họa, không import vào ngân hàng thật. Bản ghi thật cần nguồn hợp lệ, người review khác người tuyển chọn và đầy đủ kiểm tra."
    }
  }
]
```

### Source registry

Lưu ở: `data/seed/source_registry.json`

```json
[
  {
    "schema_version": "source-record/0.1-proposal",
    "example_only": true,
    "id": "example.source.c03",
    "title": null,
    "url": null,
    "file_path": null,
    "revision": null,
    "authors": [],
    "collected_at": null,
    "original_language": null,
    "original_content": {
      "question_text": null,
      "code": null
    },
    "license": {
      "spdx_id": null,
      "url": null,
      "required_notice": null,
      "status": "not_checked"
    }
  }
]
```

### Review fixture

Lưu ở: `test/fixtures/question_reviews/c03.json`

```json
{
  "schema_version": "review-fixture/0.1-proposal",
  "example_only": true,
  "review_status": "illustrative_unreviewed",
  "question_id": "example.c03.v1",
  "question_version": 1,
  "rubric_id": "rubric.c03.v1",
  "cases": [
    {
      "label": "Câu trả lời minh họa đáp ứng rubric",
      "answer": "Hai yêu cầu có thể cùng đọc stock=1 trước khi ghi. Tôi dùng conditional update stock=stock-1 với stock>=1 và kiểm tra affected rows=1. Trừ kho và tạo đơn trong cùng transaction; tạo đơn lỗi thì rollback. Test hai yêu cầu đồng thời qua hai instance: chỉ một đơn thành công, stock=0. Thử lỗi chèn đơn: không có đơn và stock trở về 1.",
      "answer_context": {
        "missing_attachment": false
      },
      "checks": [
        {
          "criterion_id": "c03.race",
          "status": "met",
          "score": 2,
          "evidence_quote": "cùng đọc stock=1 trước khi ghi",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c03.atomicity",
          "status": "met",
          "score": 2,
          "evidence_quote": "Trừ kho và tạo đơn trong cùng transaction; tạo đơn lỗi thì rollback",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c03.concurrent_tests",
          "status": "met",
          "score": 2,
          "evidence_quote": "chỉ một đơn thành công, stock=0",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        }
      ],
      "expected_total": 6
    },
    {
      "label": "Thiếu tệp được viện dẫn: chưa thể chấm",
      "answer": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
      "answer_context": {
        "missing_attachment": true
      },
      "checks": [
        {
          "criterion_id": "c03.race",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c03.atomicity",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c03.concurrent_tests",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        }
      ],
      "expected_total": null
    }
  ],
  "notes": "Ví dụ giúp reviewer hiểu cách áp dụng rubric, không phải bộ benchmark đã được kiểm định. Lưu riêng khỏi dữ liệu hiển thị cho người học."
}
```

## C04: Tìm hai vị trí có tổng bằng target

Mẫu minh họa tự soạn · format đề xuất cho P03/P05 · draft · chưa đủ điều kiện import. Source/license để null có chủ đích, không phải nguồn đã được xác minh.

### Cách lưu

1. Chốt các tên trường và skill IDs với P03/C01 trước khi viết importer. Các example.* ID trong mẫu không phải danh mục kỹ năng đã phê duyệt.
2. Tạo bản ghi thật với ID mới trong mảng JSON ở data/seed/questions/algorithms.json; thêm vào mảng có sẵn, không ghi đè các câu khác. Rubric được nhúng trong từng question và có ID/version riêng.
3. Thêm source record cùng source_id vào mảng data/seed/source_registry.json. Điền URL file gốc, revision nếu có, giấy phép, tác giả và original_content; giữ bản gốc riêng với prompt đã dịch/adapt.
4. Lưu câu trả lời tổng hợp và nhãn reviewer ở test/fixtures/question_reviews/c04.json. Fixture và rubric chứa căn cứ đáp án dùng phía server/reviewer; trước khi người học trả lời, View chỉ nhận nội dung đề qua DTO đã chốt ở P04.
5. Ghi nội dung dịch/sửa trong adaptation và ghi công trong docs/THIRD_PARTY_NOTICES.md. Dùng mẫu để hiểu cấu trúc; không chỉ đổi example_only thành false rồi xem như câu đã tuyển chọn.

### Cách review

1. Người tuyển chọn mở PR với question, source record, notice và fixture; giữ review.status=draft hoặc pending_review.
2. Một người khác kiểm tra nguồn/giấy phép, nội dung kỹ thuật, ranh giới 0–1–2, lời giải tương đương và các ví dụ review.
3. Chỉ ghi checks=true cho điều đã kiểm tra. Chỉ approved khi tất cả checks=true, reviewer_id khác curator_id, có reviewed_at và provenance thực đầy đủ.
4. C08/importer cần kiểm tra cả approval và provenance, từ chối mọi example_only=true. Chưa đủ căn cứ giữ score=null; chỉ cộng tổng khi mọi tiêu chí đều chấm được.

### Question record

Lưu ở: `data/seed/questions/algorithms.json`

```json
[
  {
    "schema_version": "question-record/0.1-proposal",
    "example_only": true,
    "id": "example.c04.v1",
    "version": 1,
    "category": "algorithm_explanation",
    "language": "vi",
    "role": "backend_developer",
    "level": "intern_fresher",
    "skill_ids": [
      "example.algorithm.correctness",
      "example.algorithm.complexity"
    ],
    "source_id": "example.source.c04",
    "prompt": "Cho danh sách số nguyên nums và target, tìm hai vị trí khác nhau có tổng bằng target; trả None nếu không có. Giải thích thuật toán, vì sao đúng, độ phức tạp và kiểm thử biên.",
    "code": null,
    "code_language": null,
    "constraints": [
      "Chỉ số bắt đầu từ 0; không dùng cùng một vị trí hai lần.",
      "Có thể có giá trị trùng nhau; nếu có nhiều cặp thì trả một cặp bất kỳ.",
      "Đề không bắt buộc một độ phức tạp tối ưu cụ thể."
    ],
    "adaptation": {
      "kind": "illustrative_authored_example",
      "summary": "Mẫu tự soạn để minh họa format, không phải câu hỏi nguồn mở đã xác minh. Thay bằng nội dung đã tuyển chọn và ghi lại thay đổi.",
      "translator_id": null
    },
    "rubric": {
      "id": "rubric.c04.v1",
      "version": 1,
      "criteria": [
        {
          "id": "c04.correctness",
          "label": "Thuật toán và lập luận đúng",
          "expected_evidence": [
            "Chỉ trả cặp vị trí khác nhau có đúng tổng.",
            "Xử lý giá trị trùng và không tìm thấy."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Có thể dùng một vị trí hai lần hoặc trả cặp sai tổng."
            },
            {
              "score": 1,
              "description": "Ý tưởng phù hợp nhưng chưa giải thích một ràng buộc quan trọng."
            },
            {
              "score": 2,
              "description": "Thuật toán và lập luận đáp ứng đầy đủ các ràng buộc, kể cả duplicate/no-match."
            }
          ],
          "equivalent_answers": "Duyệt cặp j>i hoặc hash lookup trước khi insert đều có thể đạt đủ nếu giải thích đúng; không ép theo đáp án mẫu."
        },
        {
          "id": "c04.complexity",
          "label": "Độ phức tạp khớp phương án",
          "expected_evidence": [
            "Nêu thời gian và bộ nhớ của chính cách đã chọn.",
            "Nêu giả định average-case nếu dựa vào hash table."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Khẳng định độ phức tạp sai cho chính phương án."
            },
            {
              "score": 1,
              "description": "Nêu đúng một phần nhưng bỏ thời gian/bộ nhớ hoặc giả định quan trọng."
            },
            {
              "score": 2,
              "description": "Nêu đúng thời gian, bộ nhớ và giả định cần thiết."
            }
          ],
          "equivalent_answers": "Cách O(n²) vẫn đạt tiêu chí này nếu phân tích đúng vì đề không yêu cầu tối ưu nhất."
        },
        {
          "id": "c04.edge_tests",
          "label": "Kiểm thử điều kiện biên",
          "expected_evidence": [
            "[3,3], target=6 trả hai vị trí khác nhau.",
            "Input không đủ phần tử hoặc không có cặp trả None."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Không nêu test hoặc test cho phép dùng lại cùng vị trí."
            },
            {
              "score": 1,
              "description": "Có một nhóm test đúng nhưng thiếu duplicate hoặc no-match."
            },
            {
              "score": 2,
              "description": "Nêu test duplicate và no-match/không đủ phần tử với kết quả rõ ràng."
            }
          ],
          "equivalent_answers": "Có thể dùng input tương đương; không bắt buộc đúng các số trong ví dụ."
        }
      ],
      "scoring": {
        "allowed_scores": [
          0,
          1,
          2
        ],
        "maximum_score": 6,
        "total_policy": "sum_only_when_every_criterion_is_decidable",
        "insufficient_evidence": {
          "score": null,
          "reason_required": true,
          "total_score": null
        },
        "missing_required_content": "Có thể là unmet/0 nếu rubric yêu cầu rõ và quan sát được nội dung bị thiếu; tệp/ngữ cảnh được viện dẫn nhưng chưa có thì chưa đủ căn cứ.",
        "provider_failure": "processing_error, không gán điểm hoặc kết luận năng lực",
        "equivalent_answers": "Chấp nhận phương án khác đúng theo ràng buộc; không so khớp chữ với đáp án mẫu."
      }
    },
    "review": {
      "status": "draft",
      "curator_id": null,
      "reviewer_id": null,
      "reviewed_at": null,
      "checks": {
        "source_and_license_verified": null,
        "original_and_adaptation_preserved": null,
        "technical_correctness_checked": null,
        "rubric_levels_distinct": null,
        "equivalent_answers_checked": null,
        "review_cases_checked": null
      },
      "notes": "Mẫu minh họa, không import vào ngân hàng thật. Bản ghi thật cần nguồn hợp lệ, người review khác người tuyển chọn và đầy đủ kiểm tra."
    }
  }
]
```

### Source registry

Lưu ở: `data/seed/source_registry.json`

```json
[
  {
    "schema_version": "source-record/0.1-proposal",
    "example_only": true,
    "id": "example.source.c04",
    "title": null,
    "url": null,
    "file_path": null,
    "revision": null,
    "authors": [],
    "collected_at": null,
    "original_language": null,
    "original_content": {
      "question_text": null,
      "code": null
    },
    "license": {
      "spdx_id": null,
      "url": null,
      "required_notice": null,
      "status": "not_checked"
    }
  }
]
```

### Review fixture

Lưu ở: `test/fixtures/question_reviews/c04.json`

```json
{
  "schema_version": "review-fixture/0.1-proposal",
  "example_only": true,
  "review_status": "illustrative_unreviewed",
  "question_id": "example.c04.v1",
  "question_version": 1,
  "rubric_id": "rubric.c04.v1",
  "cases": [
    {
      "label": "Câu trả lời minh họa đáp ứng rubric",
      "answer": "Tôi duyệt mọi cặp i<j và trả cặp nếu nums[i]+nums[j]==target; hết các cặp thì trả None. Vì chỉ duyệt i<j nên không dùng lại một vị trí và vẫn duyệt mọi cặp khác nhau. Thời gian O(n²), bộ nhớ phụ O(1). Với [3,3], target=6 trả (0,1); với [] hoặc [1], và với [1,2], target=8 thì trả None.",
      "answer_context": {
        "missing_attachment": false
      },
      "checks": [
        {
          "criterion_id": "c04.correctness",
          "status": "met",
          "score": 2,
          "evidence_quote": "chỉ duyệt i<j nên không dùng lại một vị trí",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c04.complexity",
          "status": "met",
          "score": 2,
          "evidence_quote": "Thời gian O(n²), bộ nhớ phụ O(1)",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c04.edge_tests",
          "status": "met",
          "score": 2,
          "evidence_quote": "Với [3,3], target=6 trả (0,1)",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        }
      ],
      "expected_total": 6
    },
    {
      "label": "Thiếu tệp được viện dẫn: chưa thể chấm",
      "answer": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
      "answer_context": {
        "missing_attachment": true
      },
      "checks": [
        {
          "criterion_id": "c04.correctness",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c04.complexity",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c04.edge_tests",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        }
      ],
      "expected_total": null
    }
  ],
  "notes": "Ví dụ giúp reviewer hiểu cách áp dụng rubric, không phải bộ benchmark đã được kiểm định. Lưu riêng khỏi dữ liệu hiển thị cho người học."
}
```

## C05: Kiểm chứng gợi ý code tính trung bình

Mẫu minh họa tự soạn · format đề xuất cho P03/P05 · draft · chưa đủ điều kiện import. Source/license để null có chủ đích, không phải nguồn đã được xác minh.

### Cách lưu

1. Chốt các tên trường và skill IDs với P03/C01 trước khi viết importer. Các example.* ID trong mẫu không phải danh mục kỹ năng đã phê duyệt.
2. Tạo bản ghi thật với ID mới trong mảng JSON ở data/seed/questions/ai_review.json; thêm vào mảng có sẵn, không ghi đè các câu khác. Rubric được nhúng trong từng question và có ID/version riêng.
3. Thêm source record cùng source_id vào mảng data/seed/source_registry.json. Điền URL file gốc, revision nếu có, giấy phép, tác giả và original_content; giữ bản gốc riêng với prompt đã dịch/adapt.
4. Lưu câu trả lời tổng hợp và nhãn reviewer ở test/fixtures/question_reviews/c05.json. Fixture và rubric chứa căn cứ đáp án dùng phía server/reviewer; trước khi người học trả lời, View chỉ nhận nội dung đề qua DTO đã chốt ở P04.
5. Ghi nội dung dịch/sửa trong adaptation và ghi công trong docs/THIRD_PARTY_NOTICES.md. Dùng mẫu để hiểu cấu trúc; không chỉ đổi example_only thành false rồi xem như câu đã tuyển chọn.

### Cách review

1. Người tuyển chọn mở PR với question, source record, notice và fixture; giữ review.status=draft hoặc pending_review.
2. Một người khác kiểm tra nguồn/giấy phép, nội dung kỹ thuật, ranh giới 0–1–2, lời giải tương đương và các ví dụ review.
3. Chỉ ghi checks=true cho điều đã kiểm tra. Chỉ approved khi tất cả checks=true, reviewer_id khác curator_id, có reviewed_at và provenance thực đầy đủ.
4. C08/importer cần kiểm tra cả approval và provenance, từ chối mọi example_only=true. Chưa đủ căn cứ giữ score=null; chỉ cộng tổng khi mọi tiêu chí đều chấm được.

### Question record

Lưu ở: `data/seed/questions/ai_review.json`

```json
[
  {
    "schema_version": "question-record/0.1-proposal",
    "example_only": true,
    "id": "example.c05.v1",
    "version": 1,
    "category": "ai_code_review",
    "language": "vi",
    "role": "backend_developer",
    "level": "intern_fresher",
    "skill_ids": [
      "example.ai.independent_code_verification"
    ],
    "source_id": "example.source.c05",
    "prompt": "Bạn đang kiểm chứng một gợi ý code tính trung bình cộng. nums là list số hữu hạn; kết quả cần là trung bình thực, còn list rỗng phải raise ValueError. Hãy chỉ ra lỗi, sửa và nêu các test độc lập để kiểm chứng gợi ý.",
    "code": "def average(nums):\n    return sum(nums) // len(nums)",
    "code_language": "python",
    "constraints": [
      "Giả sử lớp nhận dữ liệu đã bảo đảm phần tử là số hữu hạn.",
      "Đoạn code trong mẫu này do người soạn mẫu tạo; không phải nội dung đã xác minh do AI hoặc một tác giả nguồn mở tạo ra."
    ],
    "adaptation": {
      "kind": "illustrative_authored_example",
      "summary": "Mẫu tự soạn để minh họa format, không phải câu hỏi nguồn mở đã xác minh. Thay bằng nội dung đã tuyển chọn và ghi lại thay đổi.",
      "translator_id": null
    },
    "rubric": {
      "id": "rubric.c05.v1",
      "version": 1,
      "criteria": [
        {
          "id": "c05.bugs",
          "label": "Phát hiện lỗi theo yêu cầu",
          "expected_evidence": [
            "// làm tròn xuống thay vì trung bình thực.",
            "List rỗng gây chia cho 0 thay vì ValueError theo hợp đồng."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Khẳng định code luôn đúng hoặc giải thích sai lỗi chính."
            },
            {
              "score": 1,
              "description": "Chỉ phát hiện đúng một trong hai lỗi."
            },
            {
              "score": 2,
              "description": "Phát hiện và giải thích đúng cả hai lỗi so với hợp đồng."
            }
          ],
          "equivalent_answers": "Chấp nhận ví dụ phản chứng thay cho thuật ngữ floor division."
        },
        {
          "id": "c05.fix",
          "label": "Sửa đúng cả hai hành vi",
          "expected_evidence": [
            "Dùng phép chia thực.",
            "Chủ động raise ValueError khi rỗng."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Bản sửa vẫn sai cả hai yêu cầu chính."
            },
            {
              "score": 1,
              "description": "Sửa đúng một yêu cầu nhưng còn vi phạm yêu cầu kia."
            },
            {
              "score": 2,
              "description": "Sửa đúng chia thực và trường hợp rỗng mà không thay đổi hợp đồng."
            }
          ],
          "equivalent_answers": "Có thể dùng cách tính trung bình tương đương nếu vẫn tuân theo hợp đồng, không bắt buộc một mẫu hàm."
        },
        {
          "id": "c05.independent_tests",
          "label": "Kiểm chứng độc lập với gợi ý",
          "expected_evidence": [
            "Test [1,2] cho 1.5.",
            "Test [] raise ValueError và thêm một trường hợp số âm/thập phân."
          ],
          "levels": [
            {
              "score": 0,
              "description": "Không kiểm chứng hoặc chỉ dựa vào việc AI tự nhận code đúng."
            },
            {
              "score": 1,
              "description": "Có test độc lập nhưng thiếu một hành vi hoặc thiếu expected result."
            },
            {
              "score": 2,
              "description": "Các test cho chia thực, rỗng và số âm/thập phân có expected result tự xác định."
            }
          ],
          "equivalent_answers": "Chấp nhận test tay hoặc automated test, nhưng phải chỉ ra expected result trước khi dựa vào output gợi ý."
        }
      ],
      "scoring": {
        "allowed_scores": [
          0,
          1,
          2
        ],
        "maximum_score": 6,
        "total_policy": "sum_only_when_every_criterion_is_decidable",
        "insufficient_evidence": {
          "score": null,
          "reason_required": true,
          "total_score": null
        },
        "missing_required_content": "Có thể là unmet/0 nếu rubric yêu cầu rõ và quan sát được nội dung bị thiếu; tệp/ngữ cảnh được viện dẫn nhưng chưa có thì chưa đủ căn cứ.",
        "provider_failure": "processing_error, không gán điểm hoặc kết luận năng lực",
        "equivalent_answers": "Chấp nhận phương án khác đúng theo ràng buộc; không so khớp chữ với đáp án mẫu."
      }
    },
    "review": {
      "status": "draft",
      "curator_id": null,
      "reviewer_id": null,
      "reviewed_at": null,
      "checks": {
        "source_and_license_verified": null,
        "original_and_adaptation_preserved": null,
        "technical_correctness_checked": null,
        "rubric_levels_distinct": null,
        "equivalent_answers_checked": null,
        "review_cases_checked": null
      },
      "notes": "Mẫu minh họa, không import vào ngân hàng thật. Bản ghi thật cần nguồn hợp lệ, người review khác người tuyển chọn và đầy đủ kiểm tra."
    }
  }
]
```

### Source registry

Lưu ở: `data/seed/source_registry.json`

```json
[
  {
    "schema_version": "source-record/0.1-proposal",
    "example_only": true,
    "id": "example.source.c05",
    "title": null,
    "url": null,
    "file_path": null,
    "revision": null,
    "authors": [],
    "collected_at": null,
    "original_language": null,
    "original_content": {
      "question_text": null,
      "code": null
    },
    "license": {
      "spdx_id": null,
      "url": null,
      "required_notice": null,
      "status": "not_checked"
    }
  }
]
```

### Review fixture

Lưu ở: `test/fixtures/question_reviews/c05.json`

```json
{
  "schema_version": "review-fixture/0.1-proposal",
  "example_only": true,
  "review_status": "illustrative_unreviewed",
  "question_id": "example.c05.v1",
  "question_version": 1,
  "rubric_id": "rubric.c05.v1",
  "cases": [
    {
      "label": "Câu trả lời minh họa đáp ứng rubric",
      "answer": "Dùng // khiến [1,2] ra 1 thay vì 1.5; [] gây chia cho 0. Tôi kiểm tra if not nums: raise ValueError rồi return sum(nums)/len(nums). Tôi tự xác định test [1,2] -> 1.5, [] -> ValueError, [-1,2] -> 0.5, thay vì tin lời gợi ý rằng code đúng.",
      "answer_context": {
        "missing_attachment": false
      },
      "checks": [
        {
          "criterion_id": "c05.bugs",
          "status": "met",
          "score": 2,
          "evidence_quote": "[1,2] ra 1 thay vì 1.5",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c05.fix",
          "status": "met",
          "score": 2,
          "evidence_quote": "if not nums: raise ValueError rồi return sum(nums)/len(nums)",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        },
        {
          "criterion_id": "c05.independent_tests",
          "status": "met",
          "score": 2,
          "evidence_quote": "[-1,2] -> 0.5",
          "reason": "Ví dụ minh họa được đối chiếu với mức 2 của tiêu chí này."
        }
      ],
      "expected_total": 6
    },
    {
      "label": "Thiếu tệp được viện dẫn: chưa thể chấm",
      "answer": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
      "answer_context": {
        "missing_attachment": true
      },
      "checks": [
        {
          "criterion_id": "c05.bugs",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c05.fix",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        },
        {
          "criterion_id": "c05.independent_tests",
          "status": "insufficient_evidence",
          "score": null,
          "evidence_quote": "Em đã trình bày lời giải và kiểm thử trong tệp đính kèm.",
          "reason": "Tệp được viện dẫn không có trong bản ghi hiện tại; chưa có nội dung để đối chiếu. Không tự xem đây là câu trả lời sai kỹ thuật."
        }
      ],
      "expected_total": null
    }
  ],
  "notes": "Ví dụ giúp reviewer hiểu cách áp dụng rubric, không phải bộ benchmark đã được kiểm định. Lưu riêng khỏi dữ liệu hiển thị cho người học."
}
```

