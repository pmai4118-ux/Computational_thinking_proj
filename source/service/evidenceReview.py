from source.Model.answerData import Criterion, EvaluationInput
from source.Model.evaluationData import CriterionCheck, Evidence, Interpretation
from source.service.evaluationErrors import EvaluationError


def invalidEvidence(message: str) -> None:
    raise EvaluationError("invalidEvidence", message)


def validateQuote(evidence: Evidence, originalText: str) -> Evidence:
    quote = evidence.quote
    if not quote or quote not in originalText:
        invalidEvidence("Trích dẫn không xuất hiện nguyên văn trong câu trả lời.")
    startOffset = evidence.startOffset
    endOffset = evidence.endOffset
    if startOffset is None and endOffset is None:
        firstOffset = originalText.find(quote)
        if originalText.find(quote, firstOffset + 1) != -1:
            invalidEvidence("Trích dẫn xuất hiện nhiều lần; cần chỉ rõ startOffset và endOffset.")
        startOffset = firstOffset
        endOffset = startOffset + len(quote)
    if startOffset is None or endOffset is None:
        invalidEvidence("Cần cung cấp cả hai offsets hoặc để cả hai null.")
    if endOffset > len(originalText) or endOffset <= startOffset or originalText[startOffset:endOffset] != quote:
        invalidEvidence("Offsets không khớp trích dẫn trong câu trả lời gốc.")
    return evidence.model_copy(update={
        "startOffset": startOffset,
        "endOffset": endOffset,
        "location": f"originalText[{startOffset}:{endOffset}]",
    })


def validateOmission(evidence: Evidence, criterion: Criterion, check: CriterionCheck) -> Evidence:
    if any(value is not None for value in (evidence.quote, evidence.startOffset, evidence.endOffset)):
        invalidEvidence("Bằng chứng thiếu nội dung phải có quote và offsets bằng null.")
    if check.status == "met":
        invalidEvidence("Thiếu nội dung không chứng minh tiêu chí đã đáp ứng.")
    if check.status == "unmet" and not criterion.omissionMeansUnmet:
        invalidEvidence("Rubric không cho phép kết luận unmet chỉ từ việc thiếu nội dung.")
    return evidence.model_copy(update={"location": "Toàn bộ originalText"})


def validateCheck(check: CriterionCheck, criterion: Criterion, originalText: str) -> CriterionCheck:
    checkedEvidence = []
    for evidence in check.evidence:
        if evidence.type == "omission":
            checkedEvidence.append(validateOmission(evidence, criterion, check))
        else:
            if evidence.type == "ambiguity" and check.status != "insufficientEvidence":
                invalidEvidence("Nội dung mơ hồ phải được ghi nhận là insufficientEvidence.")
            checkedEvidence.append(validateQuote(evidence, originalText))
    if check.status == "met" and not any(item.type == "excerpt" for item in checkedEvidence):
        invalidEvidence("Tiêu chí met cần trích dẫn hỗ trợ trực tiếp.")
    return check.model_copy(update={"evidence": tuple(checkedEvidence)})


def validateInterpretation(inputs: EvaluationInput, interpretation: Interpretation) -> Interpretation:
    reviews = interpretation.reviews
    rubricIds = [item.rubricId for item in reviews]
    if len(set(rubricIds)) != len(rubricIds) or set(rubricIds) != {item.rubricId for item in inputs.rubrics}:
        invalidEvidence("Phải có đúng một đánh giá cho mỗi rubric, không có ID lạ.")
    checkedReviews = []
    reviewMap = {item.rubricId: item for item in reviews}
    for rubric in inputs.rubrics:
        review = reviewMap[rubric.rubricId]
        checkIds = [item.criterionId for item in review.criterionChecks]
        if len(set(checkIds)) != len(checkIds) or set(checkIds) != {item.criterionId for item in rubric.criteria}:
            invalidEvidence(f"Rubric {rubric.rubricId} cần đúng một check cho từng tiêu chí.")
        checkMap = {item.criterionId: item for item in review.criterionChecks}
        checks = tuple(
            validateCheck(checkMap[item.criterionId], item, inputs.answer.originalText)
            for item in rubric.criteria
        )
        checkedReviews.append(review.model_copy(update={"criterionChecks": checks}))
    return Interpretation(reviews=tuple(checkedReviews))
