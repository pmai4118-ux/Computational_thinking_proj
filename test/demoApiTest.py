import sqlite3

import pytest
from fastapi.testclient import TestClient

from source.main import Application


@pytest.fixture
def demoClient(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app = Application.createDemoApp(settingsPath=tmp_path / "absent.json", providerName="gemini", databasePath=tmp_path / "demo.sqlite3")
    with TestClient(app) as client:
        yield client, tmp_path / "demo.sqlite3"


def requestBody(question, sample):
    return {"questionId": question["questionId"], "questionVersion": question["version"], "rubricVersions": {rubric["rubricId"]: rubric["version"] for rubric in question["rubrics"]}, "answerText": sample["answerText"]}


def testAllFiftyPreviewsAndNoHiddenReferenceLeak(demoClient):
    client, databasePath = demoClient
    questions = client.get("/api/questions").json()
    assert len(questions) == 10
    assert "recording" not in str(questions) and "expectedScores" not in str(questions)
    for question in questions:
        for sampleType in question["examples"]:
            caseName = sampleType["caseName"]
            sample = client.get(f"/api/examples/{caseName}", params={"questionId": question["questionId"]}).json()
            response = client.post("/api/preview", json={**requestBody(question, sample), "caseName": caseName})
            assert response.status_code == 200, response.text
            report = response.json()
            expected = {"correct": 2, "partial": 1, "incorrect": 0, "equivalent": 2, "ambiguous": None}[caseName]
            assert [result["score"] for result in report["results"]] == [expected] * len(question["rubrics"])
            assert report["providerName"] == "recorded"
            assert report["inputs"]["answer"]["originalText"] == sample["answerText"]
            assert len(report["feedbackItems"]) == len(question["rubrics"])
    with sqlite3.connect(databasePath) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 50


def testPreviewVersionTextAndUnknownIds(demoClient):
    client, databasePath = demoClient
    question = client.get("/api/question").json()
    sample = client.get("/api/examples/correct").json()
    body = {**requestBody(question, sample), "caseName": "correct"}
    assert client.post("/api/preview", json=body).status_code == 200
    assert client.post("/api/preview", json={**body, "answerText": body["answerText"] + " changed"}).status_code == 409
    assert client.post("/api/preview", json={**body, "questionVersion": 99}).status_code == 409
    assert client.post("/api/preview", json={**body, "rubricVersions": {}}).status_code == 409
    assert client.post("/api/preview", json={**body, "caseName": "unknown"}).status_code == 404
    assert client.get("/api/question?questionId=unknown").status_code == 404
    assert client.post("/api/evaluate", json={**body, "apiKey": "secret-value"}).status_code == 422
    assert "secret-value" not in client.post("/api/evaluate", json={"answerText": "secret-value"}).text


def testNoCredentialsKeepsSubmittedAnswerWithoutScore(demoClient):
    client, databasePath = demoClient
    assert client.get("/api/status").json()["liveEvaluationConfigured"] is False
    question = client.get("/api/question").json()
    sample = {"answerText": "My own original answer."}
    body = {**requestBody(question, sample), "answerId": "answer.retry", "revision": 1}
    response = client.post("/api/evaluate", json=body)
    assert response.status_code == 503
    with sqlite3.connect(databasePath) as connection:
        assert "My own original answer." in connection.execute("SELECT payload FROM submissions").fetchone()[0]
        assert connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
    assert client.post("/api/evaluate", json={**body, "answerText": "Different answer."}).status_code == 409
    assert client.post("/api/evaluate", json={**body, "answerText": "Different answer.", "revision": 2}).status_code == 503


def testErrorsDoNotLeakRequestOrProviderContent(demoClient, monkeypatch, caplog):
    client, databasePath = demoClient
    from source.service.demoService import DemoService
    def failRequest(self, request):
        raise RuntimeError("private-key-and-answer-secret")
    monkeypatch.setattr(DemoService, "evaluateAnswer", failRequest)
    question = client.get("/api/question").json()
    response = client.post("/api/evaluate", json=requestBody(question, {"answerText": "private-answer"}))
    assert response.status_code == 500
    assert "private" not in response.text and "private" not in caplog.text


def testOriginAndStaticAssets(demoClient):
    client, databasePath = demoClient
    assert client.get("/").status_code == 200
    for path in ("demo.js", "demoState.js", "demo.css"):
        assert client.get("/static/" + path).status_code == 200
    assert client.post("/api/evaluate", headers={"Origin": "https://unrelated.example"}, json={}).status_code == 403
    assert client.post("/api/evaluate", content="x"*250001).status_code == 413
    assert client.get("/").headers["Cache-Control"] == "no-store"


def testDownloadMatchesSavedReportAndProvider(demoClient):
    client, databasePath = demoClient
    question = client.get("/api/question").json()
    sample = client.get("/api/examples/correct").json()
    report = client.post("/api/preview", json={**requestBody(question, sample), "caseName": "correct"}).json()
    query = {name: report[name] for name in ("providerName", "modelName", "promptVersion")}
    address = "/api/reports/" + report["inputHash"]
    downloaded = client.get(address, params=query)
    assert downloaded.status_code == 200
    assert downloaded.json() == report
    assert downloaded.headers["Content-Disposition"].startswith("attachment;")
    assert client.get(address, params={**query, "providerName": "gemini"}).status_code == 404
    assert client.get("/api/reports/invalid", params=query).status_code == 422


def testInvalidProviderDoesNotBlockRecordedPreview(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_EVALUATION_PROVIDER", "unknown-provider")
    app = Application.createDemoApp(settingsPath=tmp_path / "missing.json", databasePath=tmp_path / "demo.sqlite3")
    with TestClient(app) as client:
        assert client.get("/api/status").json()["liveEvaluationConfigured"] is False
        question = client.get("/api/question").json()
        sample = client.get("/api/examples/correct").json()
        assert client.post("/api/preview", json={**requestBody(question, sample), "caseName": "correct"}).status_code == 200
