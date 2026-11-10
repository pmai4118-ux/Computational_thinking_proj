from source.Model.evaluationData import EvaluationReport


def renderReport(report: EvaluationReport) -> str:
    lines = ["ĐÁNH GIÁ CÂU TRẢ LỜI — PoC", f"Nguồn diễn giải: {report.providerName} / {report.modelName}"]
    if report.inputs.exampleOnly:
        lines.append("Nội dung minh họa tự soạn, chưa được người khác kiểm duyệt; không phải bộ đo chất lượng AI.")
    lines.append("Phạm vi: phần thể hiện trong câu hỏi này; không suy ra năng lực tổng thể.")
    rubricMap = {item.rubricId: item for item in report.inputs.rubrics}
    feedbackMap = {item.resultId: item for item in report.feedbackItems}
    for result in report.results:
        rubric = rubricMap[result.rubricId]
        allowedScores = ", ".join(f"{item.value:g}" for item in rubric.scoreLevels)
        scoreLabel = "Chưa đủ căn cứ" if result.score is None else f"{result.score:g}"
        lines.extend(["", f"{rubric.competency}: {scoreLabel} | Các mức: {allowedScores}"])
        lines.append(feedbackMap[result.resultId].explanation)
        for check in result.criterionChecks:
            for evidence in check.evidence:
                quote = f"«{evidence.quote}»" if evidence.quote is not None else "[Không có đoạn trích: quan sát phần thiếu]"
                lines.append(f"  [{check.criterionId}] {evidence.location}: {quote}")
    return "\n".join(lines)
