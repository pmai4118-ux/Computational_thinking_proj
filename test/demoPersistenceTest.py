import sqlite3
from pathlib import Path

import pytest

from source.Control.demoSchemas import LiveRequest
from source.Model.repositories.jsonEvaluationRepository import JsonEvaluationRepository
from source.Model.repositories.jsonQuestionRepository import JsonQuestionRepository
from source.Model.repositories.sqliteSubmissionRepository import SqliteSubmissionRepository
from source.service.demoService import DemoService
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService
from source.service.evidenceReview import EvidenceReview
from source.service.feedbackBuilder import FeedbackBuilder
from source.service.providers.interpreterFactory import InterpreterFactory
from source.service.questionBankService import QuestionBankService
from source.service.rubricRules import RubricRules


class CountingFactory(InterpreterFactory):
    def __init__(self, interpretation):
        self.interpretation = interpretation
        self.calls = 0
        self.fail = False
        self.modelName = "test-model"
        self.promptVersion = "test/1"
        self.providerName = "gemini"

    def createInterpreter(self, providerName, recording):
        if providerName == "recorded": return super().createInterpreter(providerName, recording)
        return self

    def interpret(self, inputs):
        self.calls += 1
        if self.fail: raise EvaluationError("providerQuota", "Quota unavailable.", True)
        return self.interpretation


def buildService(tmpPath):
    root = Path(__file__).resolve().parents[1]
    bank = QuestionBankService(JsonQuestionRepository(root / "data/questionBank/catalog.json"))
    item = bank.getQuestion("demo.Q009")
    sample = bank.getSample(item, "correct")
    factory = CountingFactory(sample.recording.interpretation)
    evaluator = EvaluationService(JsonEvaluationRepository(tmpPath / "unused"), factory, RubricRules(), EvidenceReview(), FeedbackBuilder())
    service = DemoService(bank, evaluator, SqliteSubmissionRepository(tmpPath / "submissions.sqlite3"), "gemini", {"liveEvaluationConfigured": True})
    request = LiveRequest(questionId=item.questionId, questionVersion=item.template.question.version, rubricVersions={rubric.rubricId: rubric.version for rubric in item.template.rubrics}, answerText=sample.answerText, answerId="answer.stable", revision=1)
    return service, factory, request, item, sample


def testRetryAndRestartReuseCompletedReport(tmp_path):
    service, factory, request, item, sample = buildService(tmp_path)
    first = service.evaluateAnswer(request)
    assert service.evaluateAnswer(request) == first
    assert factory.calls == 1
    restarted, secondFactory, _, _, _ = buildService(tmp_path)
    assert restarted.evaluateAnswer(request) == first
    assert secondFactory.calls == 0
    assert [result.score for result in first.results] == [2, 2, 2, 2]


def testFailedProviderKeepsInputAndRetryCanComplete(tmp_path):
    service, factory, request, item, sample = buildService(tmp_path)
    factory.fail = True
    with pytest.raises(EvaluationError): service.evaluateAnswer(request)
    with sqlite3.connect(tmp_path / "submissions.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
        assert sample.answerText in __import__('json').loads(connection.execute("SELECT payload FROM submissions").fetchone()[0])["answer"]["originalText"]
    factory.fail = False
    assert service.evaluateAnswer(request).inputs.answer.originalText == sample.answerText
    assert factory.calls == 2


def testRecordedResultCannotStandInForLiveResult(tmp_path):
    service, factory, request, item, sample = buildService(tmp_path)
    inputs = service.questionBank.sampleInputs(item, sample)
    recorded = factory.createInterpreter("recorded", sample.recording)
    recordedReport = service.processAnswer(inputs, recorded)
    liveReport = service.processAnswer(inputs, factory)
    assert factory.calls == 1
    assert recordedReport.providerName == "recorded"
    assert liveReport.providerName == "gemini"
    factory.promptVersion = "test/2"
    service.processAnswer(inputs, factory)
    assert factory.calls == 2


def testNewRevisionGetsSeparateAssessment(tmp_path):
    service, factory, request, item, sample = buildService(tmp_path)
    service.evaluateAnswer(request)
    second = request.model_copy(update={"revision": 2})
    report = service.evaluateAnswer(second)
    assert factory.calls == 2
    assert report.inputs.answer.revision == 2
