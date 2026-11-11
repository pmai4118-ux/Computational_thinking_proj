from fastapi.testclient import TestClient

from examples.evaluateAnswer.demo_ui.main import create_app
from examples.evaluateAnswer.demo_ui.task3QuestionBank import Task3QuestionBank


C02_ID = "question.c02.string_immutability.v2"


def testTask3QuestionAdapterPreservesTheThreeRubricLevelsAsCumulativeChecks():
    bank = Task3QuestionBank()

    inputs = bank.loadQuestion(C02_ID)

    assert inputs.exampleOnly is True
    assert "String" in inputs.question.prompt
    assert "Code cần phân tích" in inputs.question.prompt
    assert len(inputs.rubrics) == 3
    for rubric in inputs.rubrics:
        assert [level.value for level in rubric.scoreLevels] == [0.0, 1.0, 2.0]
        assert len(rubric.criteria) == 2
        assert all("mức cao hơn cũng đạt mốc này" in item.acceptanceRule for item in rubric.criteria)


def testTask3ExamplesExposeAnswerTextButNotReferenceJudgments():
    bank = Task3QuestionBank()

    examples = bank.listExamples(C02_ID)
    sample = bank.getExample(C02_ID, examples[0]["caseName"])

    assert {item["responseType"] for item in examples} == {
        "correct",
        "partial",
        "wrong",
        "equivalent",
        "ambiguous",
        "prompt_injection",
    }
    assert sample["answerText"]
    assert sample["canPreview"] is False
    assert "expected_total_score" not in sample


def testQuestionAndTask3SamplesCanBeSelectedThroughTheDemoApi():
    with TestClient(create_app(providerName="antigravity")) as client:
        questions = client.get("/api/questions").json()
        question = client.get(f"/api/question?questionId={C02_ID}").json()
        examples = client.get(f"/api/examples?questionId={C02_ID}").json()
        sample = client.get(f"/api/examples/{examples[0]['caseName']}?questionId={C02_ID}").json()

        assert C02_ID in {item["questionId"] for item in questions}
        assert question["reviewStatus"] == "pending_review"
        assert question["exampleOnly"] is True
        assert len(question["competencies"]) == 3
        assert "expected_total_score" not in str(question)
        assert "annotator_evaluations" not in str(examples)
        assert sample["questionId"] == C02_ID
        assert sample["answerText"]
        assert client.post(
            "/api/preview",
            json={
                "questionId": C02_ID,
                "caseName": sample["caseName"],
                "answerText": sample["answerText"],
            },
        ).status_code == 409


def testUnknownTask3QuestionAndAnswerReturnNotFound():
    with TestClient(create_app(providerName="antigravity")) as client:
        assert client.get("/api/question?questionId=unknown").status_code == 404
        assert client.get("/api/examples/unknown?questionId=" + C02_ID).status_code == 404
