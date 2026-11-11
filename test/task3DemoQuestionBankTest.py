import json
from pathlib import Path

from source.Model.repositories.jsonQuestionRepository import JsonQuestionRepository
from source.service.questionBankService import QuestionBankService


def testSelectedQuestionsRetainTheirDatasetProvenance():
    root = Path(__file__).resolve().parents[1]
    bank = QuestionBankService(JsonQuestionRepository(root / "data/questionBank/catalog.json"))
    for item in bank.readQuestions().values():
        sourcePath = root / "data/questionBank/upstream" / Path(item.source.sourcePath).name
        source = json.loads(sourcePath.read_text(encoding="utf-8-sig"))
        assert any(record["prompt"] == item.source.originalPrompt for record in source)
        assert item.source.sourceCommit == "9106f6d44a8e03ec8d7894a443679de2f0b2f05f"
        assert item.review.status == "pending_review"
        assert item.template.exampleOnly
        assert not item.review.reviewerId
