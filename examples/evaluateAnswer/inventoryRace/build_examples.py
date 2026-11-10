"""Regenerate the illustrative inputs and recorded checks; no model is called."""
import json
from pathlib import Path

from source.Model.answerData import EvaluationInput


DEST = Path(__file__).resolve().parent
QUESTION_ID = "question.inventoryRace.poc"
REVIEW_RULE = ("Chấp nhận phương án tương đương đúng. Nội dung mơ hồ hoặc dẫn tới tài liệu không có "
               "là insufficientEvidence; không tự bổ sung chi tiết. Đánh dấu thiếu yêu cầu rõ ràng là unmet.")


def criterion(identifier, description, acceptance):
    return {"criterionId": identifier, "description": description, "acceptanceRule": acceptance,
            "reviewRule": REVIEW_RULE, "omissionMeansUnmet": True}


def rubric(identifier, competency, criteria):
    first, second = (item["criterionId"] for item in criteria)
    return {"rubricId": identifier, "version": 1, "questionId": QUESTION_ID, "competency": competency,
            "criteria": criteria, "scoreLevels": [
                {"value": 0.0, "description": "Chưa xác nhận yêu cầu cơ bản.", "condition": "Mức nền.", "requiredMet": [], "minimumMet": 0},
                {"value": 1.0, "description": "Đáp ứng yêu cầu cơ bản; phần chi tiết chưa đầy đủ.", "condition": f"Cần {first}.", "requiredMet": [first], "minimumMet": 1},
                {"value": 2.0, "description": "Đáp ứng yêu cầu cơ bản và chi tiết.", "condition": f"Cần {first} và {second}.", "requiredMet": [first, second], "minimumMet": 2}],
            "scoringRule": "Chọn mức cao nhất thỏa các điều kiện; giữ null nếu tiêu chí chưa rõ có thể đổi mức. Không cộng điểm giữa các rubric."}


RUBRICS = [
    rubric("poc.inventory.race", "Nhận diện tranh chấp", [
        criterion("race.risk", "Nhận ra nguy cơ tranh chấp", "Nhận ra các yêu cầu đồng thời có thể bán quá số lượng tồn."),
        criterion("race.detail", "Giải thích thứ tự tranh chấp giữa instance", "Mô tả hai instance cùng đọc stock=1 và kiểm tra còn hàng trước khi ghi trừ theo dữ liệu đã đọc trong cơ sở dữ liệu chung.")]),
    rubric("poc.inventory.atomicity", "Bảo vệ tồn kho và transaction", [
        criterion("atomic.guard", "Bảo vệ tồn kho ở dữ liệu dùng chung", "Dùng một trong các cách tại database để không trừ quá kho: khóa hàng và kiểm tra tồn; cập nhật có điều kiện và kiểm tra số dòng; hoặc kiểm soát phiên bản lạc quan với xử lý xung đột/thử lại đúng."),
        criterion("atomic.transaction", "Tạo đơn và trừ kho cùng transaction", "Tạo đơn và trừ kho trong cùng transaction; rollback cả hai khi tạo đơn thất bại.")]),
    rubric("poc.inventory.tests", "Kiểm thử đồng thời", [
        criterion("tests.concurrent", "Tạo yêu cầu đồng thời", "Đề xuất hai client hoặc instance gửi yêu cầu đồng thời."),
        criterion("tests.assertions", "Kiểm tra bất biến và rollback", "Kiểm tra một đơn thành công, tồn cuối bằng 0; khi tạo đơn lỗi kiểm tra rollback đơn và tồn.")]),
]

QUESTION = {"questionId": QUESTION_ID, "version": 1,
            "prompt": "Kho còn một sản phẩm. Hai yêu cầu mua đến đồng thời, có thể tới hai instance ứng dụng khác nhau. Đề xuất cách chỉ tạo tối đa một đơn thành công, không âm kho; giải thích transaction và cách kiểm thử.",
            "requirements": ["Cơ sở dữ liệu được dùng chung giữa các instance ứng dụng.", "Nếu tạo đơn hàng thất bại thì thay đổi tồn kho cũng phải rollback.", "Không yêu cầu thiết kế hệ thống thanh toán hoặc quy trình giao hàng bên ngoài."],
            "context": "Tình huống PoC tạm thời, cần người review độc lập trước khi dùng làm chuẩn đánh giá.", "expectedLevel": "Backend Intern/Fresher"}

COMPLETE = [
    "Hai yêu cầu đồng thời có thể bán vượt số lượng tồn.",
    "Hai instance cùng đọc stock=1 ở database chung, cùng kiểm tra còn hàng rồi ghi trừ theo dữ liệu đã đọc.",
    "Dùng UPDATE có điều kiện stock >= 1 tại database và kiểm tra số dòng được cập nhật.",
    "Tạo đơn và trừ kho trong cùng transaction, rollback cả hai khi tạo đơn lỗi.",
    "Cho hai client gửi yêu cầu đồng thời.",
    "Kiểm tra một đơn thành công và tồn cuối bằng 0; khi tạo đơn lỗi kiểm tra không có đơn và tồn được khôi phục."
]
EQUIVALENT = [
    "Hai người mua cùng lúc có thể gây bán quá kho.",
    "Hai instance cùng đọc stock=1 từ database chung, cùng kiểm tra còn hàng rồi ghi trừ theo dữ liệu cũ.",
    "Khóa hàng bằng SELECT FOR UPDATE trong transaction, kiểm tra stock >= 1 trước khi trừ và từ chối nếu hết hàng.",
    "Ghi đơn và cập nhật kho trong cùng transaction rồi rollback cả hai nếu ghi đơn thất bại.",
    "Chạy hai luồng từ hai client cùng gửi lệnh mua.",
    "Assert chỉ một đơn thành công, stock cuối là 0; giả lập lỗi ghi đơn và assert không có đơn cùng stock ban đầu."
]
WRONG = [
    "Hai yêu cầu đồng thời không bao giờ gây bán quá kho.",
    "Hai instance đọc stock=1 rồi ghi riêng luôn an toàn.",
    "Chỉ cần synchronized trong RAM của từng instance là đủ để bảo vệ kho chung.",
    "Trừ kho rồi commit riêng; nếu tạo đơn lỗi thì không cần rollback.",
    "Chỉ cần thử một yêu cầu tuần tự.",
    "Không cần kiểm tra số đơn, tồn cuối hay rollback."
]
PARTIAL = [COMPLETE[0], None, COMPLETE[2], None, COMPLETE[4], None]
AMBIGUOUS = "Chi tiết giải pháp và kiểm thử nằm trong tệp đính kèm không có ở đây."
SCENARIOS = {"correct": COMPLETE, "partial": PARTIAL, "incorrect": WRONG,
             "equivalent": EQUIVALENT, "ambiguous": [AMBIGUOUS] * 6}


def build(name, statements):
    answer = AMBIGUOUS if name == "ambiguous" else "\n".join(item for item in statements if item)
    data = {"question": QUESTION, "rubrics": RUBRICS,
            "answer": {"answerId": f"answer.inventoryRace.{name}", "revision": 1,
                       "questionId": QUESTION_ID, "originalText": answer}, "exampleOnly": True}
    inputs = EvaluationInput.model_validate(data)
    checks = []
    for index, statement in enumerate(statements):
        status = "insufficientEvidence" if name == "ambiguous" else "unmet" if name == "incorrect" or statement is None else "met"
        if statement is None:
            evidence = {"type": "omission", "quote": None, "location": "Entire originalText", "observation": "Yêu cầu này không được trình bày.", "startOffset": None, "endOffset": None}
        else:
            evidence = {"type": "ambiguity" if name == "ambiguous" else "excerpt", "quote": statement, "location": "originalText", "observation": "Cần tài liệu được nhắc tới để kết luận." if name == "ambiguous" else "Nhận định này đáp ứng tiêu chí." if status == "met" else "Nhận định này trái với tiêu chí.", "startOffset": None, "endOffset": None}
        checks.append({"criterionId": RUBRICS[index // 2]["criteria"][index % 2]["criterionId"], "status": status, "evidence": [evidence]})
    reviews = [{"rubricId": rubric["rubricId"], "criterionChecks": checks[i * 2:i * 2 + 2]} for i, rubric in enumerate(RUBRICS)]
    recording = {"inputHash": inputs.inputDigest(), "interpretation": {"reviews": reviews}}
    expected = {"provisional": True, "reviewedByHuman": False, "scores": [None if name == "ambiguous" else 0 if name == "incorrect" else 1 if name == "partial" else 2] * 3,
                "checks": [{"criterionId": check["criterionId"], "status": check["status"], "quote": check["evidence"][0]["quote"],
                            "feedbackObservation": check["evidence"][0]["observation"], "identifiedIssue": check["status"] == "unmet"} for check in checks]}
    for suffix, payload in (("input", data), ("recording", recording), ("expected", expected)):
        (DEST / f"{name}.{suffix}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for scenario, values in SCENARIOS.items():
        build(scenario, values)
