"""Read the pinned Task 3 question and synthetic-answer snapshot for the demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from source.Model.answerData import (
    Criterion,
    EvaluationInput,
    Question,
    Rubric,
    ScoreLevel,
)
from source.service.evaluationErrors import EvaluationError


SNAPSHOT_DIRECTORY = Path(__file__).resolve().parent / "task3_snapshot"
QUESTION_FILES = ("programming.json", "cases.json", "algorithms.json", "ai_review.json")
ANSWER_FILE = "question_answer_testcases.json"
LEVEL_LABELS = {
    "correct": "Đúng đầy đủ",
    "partial": "Đúng một phần",
    "wrong": "Chưa đúng",
    "equivalent": "Diễn đạt tương đương",
    "ambiguous": "Mơ hồ hoặc thiếu ngữ cảnh",
    "prompt_injection": "Có nội dung chèn chỉ dẫn",
}


class Task3QuestionBank:
    """Adapt the Task 3 seed schema to the existing Task 2 evaluation contract.

    Task 3 gives each rubric criterion three levels (0/1/2). The evaluator accepts
    binary evidence checks, so each positive level becomes one atomic check and
    the original level order becomes the score thresholds. The source records
    remain unchanged in ``task3_snapshot``.
    """

    def __init__(self, snapshotDirectory: Path = SNAPSHOT_DIRECTORY):
        self.snapshotDirectory = snapshotDirectory
        questionRows: dict[str, dict[str, Any]] = {}
        for fileName in QUESTION_FILES:
            for row in self._readList(fileName):
                questionId = row.get("id")
                if not isinstance(questionId, str) or questionId in questionRows:
                    raise self._invalidSnapshot()
                questionRows[questionId] = row

        answerRows = self._readList(ANSWER_FILE)
        self._answersByQuestion: dict[str, dict[str, Any]] = {}
        for row in answerRows:
            questionId = row.get("question_id")
            if not isinstance(questionId, str) or questionId in self._answersByQuestion:
                raise self._invalidSnapshot()
            self._answersByQuestion[questionId] = row

        self._questionsById = {
            questionId: questionRows[questionId]
            for questionId in self._answersByQuestion
            if questionId in questionRows
        }
        if len(self._questionsById) != len(self._answersByQuestion) or not self._questionsById:
            raise self._invalidSnapshot()

    @staticmethod
    def _invalidSnapshot() -> EvaluationError:
        return EvaluationError(
            "questionBankInvalid",
            "Không thể đọc bộ câu hỏi Task 3 trong bản demo. Kiểm tra lại các tệp snapshot.",
        )

    def _readList(self, fileName: str) -> list[dict[str, Any]]:
        try:
            value = json.loads((self.snapshotDirectory / fileName).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise self._invalidSnapshot() from None
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            raise self._invalidSnapshot()
        return value

    def questionIds(self) -> tuple[str, ...]:
        return tuple(self._questionsById)

    def listQuestions(self) -> list[dict[str, Any]]:
        return [self.questionDetails(questionId) for questionId in self.questionIds()]

    def questionDetails(self, questionId: str) -> dict[str, Any]:
        question, answerSet = self._records(questionId)
        rubric = question["rubric"]
        return {
            "questionId": questionId,
            "title": answerSet["title"],
            "prompt": question["prompt"],
            "code": question.get("code"),
            "codeLanguage": question.get("code_language"),
            "requirements": question.get("constraints", []),
            "expectedLevel": question.get("level", "intern_fresher").replace("_", " ").title(),
            "competencies": [criterion["label"] for criterion in rubric["criteria"]],
            "exampleOnly": True,
            "reviewStatus": question.get("review", {}).get("status", "unknown"),
            "sourceLabel": "Task 3 · dữ liệu snapshot, chưa duyệt làm benchmark",
            "examples": self.listExamples(questionId),
        }

    def loadQuestion(self, questionId: str) -> EvaluationInput:
        question, answerSet = self._records(questionId)
        sourceRubric = question["rubric"]
        sourceCode = question.get("code")
        prompt = question["prompt"]
        if sourceCode:
            prompt += f"\n\nCode cần phân tích ({question.get('code_language') or 'text'}):\n{sourceCode}"

        rubrics = tuple(
            self._adaptCriterion(questionId, sourceRubric, criterion)
            for criterion in sourceRubric["criteria"]
        )
        return EvaluationInput.model_validate(
            {
                "question": {
                    "questionId": questionId,
                    "version": question["version"],
                    "prompt": prompt,
                    "requirements": question.get("constraints") or ("Không có yêu cầu bổ sung.",),
                    "context": None,
                    "expectedLevel": question.get("level", "intern_fresher"),
                },
                "rubrics": rubrics,
                "answer": {
                    "answerId": f"answer.demo.{questionId}",
                    "revision": 1,
                    "questionId": questionId,
                    "originalText": "",
                },
                # Every Task 3 seed item is still pending independent review.
                "exampleOnly": True,
            }
        )

    def listExamples(self, questionId: str) -> list[dict[str, Any]]:
        _, answerSet = self._records(questionId)
        examples: list[dict[str, Any]] = []
        seenTypes: set[str] = set()
        for sample in answerSet["sample_answers"]:
            responseType = sample.get("response_type")
            caseId = sample.get("case_id")
            if responseType not in LEVEL_LABELS or responseType in seenTypes or not isinstance(caseId, str):
                continue
            seenTypes.add(responseType)
            examples.append(
                {
                    "caseName": caseId,
                    "label": LEVEL_LABELS[responseType],
                    "responseType": responseType,
                    "canPreview": False,
                }
            )
        return examples

    def getExample(self, questionId: str, caseName: str) -> dict[str, Any]:
        _, answerSet = self._records(questionId)
        sample = next(
            (item for item in answerSet["sample_answers"] if item.get("case_id") == caseName),
            None,
        )
        if sample is None or not isinstance(sample.get("answer_text"), str):
            raise EvaluationError("unknownExample", "Không tìm thấy câu trả lời mẫu của câu hỏi này.")
        return {
            "questionId": questionId,
            "caseName": caseName,
            "answerText": sample["answer_text"],
            "canPreview": False,
        }

    def _records(self, questionId: str) -> tuple[dict[str, Any], dict[str, Any]]:
        question = self._questionsById.get(questionId)
        answerSet = self._answersByQuestion.get(questionId)
        if question is None or answerSet is None:
            raise EvaluationError("unknownQuestion", "Không tìm thấy câu hỏi trong bộ dữ liệu demo.")
        return question, answerSet

    @staticmethod
    def _adaptCriterion(
        questionId: str,
        sourceRubric: dict[str, Any],
        sourceCriterion: dict[str, Any],
    ) -> Rubric:
        levels = sorted(sourceCriterion.get("levels", []), key=lambda item: item.get("score", -1))
        scores = [level.get("score") for level in levels]
        if scores != [0, 1, 2]:
            raise Task3QuestionBank._invalidSnapshot()

        criterionId = sourceCriterion["id"]
        atomicCriteria = tuple(
            Criterion(
                criterionId=f"{criterionId}.level{level['score']}",
                description=f"{sourceCriterion['label']} · mức {level['score']}",
                acceptanceRule=(
                    f"Đây là mốc tích lũy {level['score']}/2. Đánh dấu đạt nếu câu trả lời có bằng chứng "
                    f"đạt mức này trở lên; câu trả lời đạt mức cao hơn cũng đạt mốc này. "
                    f"Mô tả mức nguồn: {level['description']}"
                ),
                reviewRule=(
                    "Chấp nhận câu trả lời đúng có cách diễn đạt tương đương. "
                    "Chỉ dùng nội dung trong câu trả lời gốc làm bằng chứng. "
                    "Các mốc mức điểm có tính tích lũy: khi đạt mức cao hơn, đánh dấu các mốc thấp hơn là đạt. "
                    "Nếu câu trả lời không đủ rõ để phân loại mức điểm, đánh dấu chưa đủ bằng chứng. "
                    + (sourceCriterion.get("equivalent_answers") or "")
                ),
                omissionMeansUnmet=True,
            )
            for level in levels
            if level["score"] > 0
        )
        checkIds = tuple(criterion.criterionId for criterion in atomicCriteria)
        scoreLevels = tuple(
            ScoreLevel(
                value=float(level["score"]),
                description=level["description"],
                condition=f"Đạt mức {level['score']} của tiêu chí nguồn.",
                requiredMet=checkIds[: level["score"]],
                minimumMet=level["score"],
            )
            for level in levels
        )
        return Rubric(
            rubricId=f"{sourceRubric['id']}.{criterionId}",
            version=sourceRubric.get("version", 1),
            questionId=questionId,
            competency=sourceCriterion["label"],
            criteria=atomicCriteria,
            scoreLevels=scoreLevels,
            scoringRule="Chấm theo các mốc nguyên tử từ rubric Task 3; chọn mức cao nhất có đủ bằng chứng.",
        )
