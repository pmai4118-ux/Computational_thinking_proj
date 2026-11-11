from pathlib import Path

import pytest

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import RecordedReview
from source.Model.repositories.jsonEvaluationRepository import JsonEvaluationRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService
from source.service.evidenceReview import EvidenceReview
from source.service.feedbackBuilder import FeedbackBuilder
from source.service.providers.recordedInterpreter import RecordedInterpreter
from source.service.rubricRules import RubricRules


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "evaluateAnswer"


class CountingFactory:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def createInterpreter(self, providerName, recording):
        self.calls += 1
        if self.fail:
            raise EvaluationError("providerTimeout", "Timed out", True)
        return RecordedInterpreter(recording)


def service(repo, factory):
    return EvaluationService(repo, factory, RubricRules(), EvidenceReview(), FeedbackBuilder())


def test_retry_reuses_completed_report_across_instances_and_output_paths(tmp_path):
    repo = JsonEvaluationRepository(tmp_path / "reports")
    factory = CountingFactory()
    input_path = EXAMPLES / "sampleInput.json"
    recording = EXAMPLES / "sampleReview.json"
    first, original_path = service(repo, factory).evaluateFiles(input_path, "recorded", recording, outputPath=tmp_path / "export.json")
    # Retry works even if the recording is unavailable and the destination changes.
    repeated, cached_path = service(JsonEvaluationRepository(tmp_path / "reports"), factory).evaluateFiles(
        input_path, "recorded", tmp_path / "missing.json", outputPath=tmp_path / "other.json"
    )
    assert repeated == first
    assert factory.calls == 1
    assert original_path.exists() and cached_path.exists()
    assert not (tmp_path / "other.json").exists()
    # A later provider choice is a retry of this snapshot, not a re-evaluation.
    cached, _ = service(JsonEvaluationRepository(tmp_path / "reports"), factory).evaluateFiles(input_path, "gemini")
    assert cached == first
    assert cached.providerName == "recorded"
    assert cached.modelName == first.modelName
    assert cached.promptVersion == first.promptVersion
    assert factory.calls == 1


def test_retry_reuses_legacy_uuid_report_without_creating_a_copy(tmp_path):
    repo = JsonEvaluationRepository(tmp_path / "reports")
    input_path = EXAMPLES / "sampleInput.json"
    original, canonical_path = service(repo, CountingFactory()).evaluateFiles(
        input_path, "recorded", EXAMPLES / "sampleReview.json"
    )
    legacy_path = canonical_path.with_name("report-7885183b881341cc9aed1e60ba4718cb.json")
    canonical_path.rename(legacy_path)
    original_bytes = legacy_path.read_bytes()
    invalid_path = legacy_path.with_name("report-00000000000000000000000000000000.json")
    invalid_path.write_text("invalid JSON", encoding="utf-8")

    retry_factory = CountingFactory(fail=True)
    repeated, result_path = service(JsonEvaluationRepository(repo.reportDirectory), retry_factory).evaluateFiles(
        input_path, "recorded", tmp_path / "missing-recording.json"
    )

    assert repeated == original
    assert result_path == legacy_path
    assert retry_factory.calls == 0
    assert legacy_path.read_bytes() == original_bytes
    assert set(repo.reportDirectory.iterdir()) == {legacy_path, invalid_path}


def test_equivalent_output_path_publishes_one_canonical_report(tmp_path):
    repo = JsonEvaluationRepository(tmp_path / "reports")
    input_path = EXAMPLES / "sampleInput.json"
    canonical_path = repo.cachePath(repo.loadInput(input_path).inputDigest())
    nested_path = repo.reportDirectory / "nested"
    nested_path.mkdir(parents=True)
    equivalent_path = nested_path / ".." / canonical_path.name

    report, result_path = service(repo, CountingFactory()).evaluateFiles(
        input_path, "recorded", EXAMPLES / "sampleReview.json", outputPath=equivalent_path
    )

    assert result_path == canonical_path
    assert repo.findCompletedReport(report.inputHash) == (report, canonical_path)
    assert list(repo.reportDirectory.glob("report-*.json")) == [canonical_path]


@pytest.mark.parametrize("change", ["question_version", "rubric_version", "answer_text"])
def test_changed_snapshot_produces_new_report(tmp_path, change):
    inputs = EvaluationInput.model_validate_json((EXAMPLES / "sampleInput.json").read_text(encoding="utf-8"))
    input_data = inputs.model_dump(mode="json")
    if change == "question_version":
        input_data["question"]["version"] += 1
    elif change == "rubric_version":
        input_data["rubrics"][0]["version"] += 1
    else:
        input_data["answer"]["originalText"] += "\nAdditional context."
    changed = EvaluationInput.model_validate(input_data)
    input_path = tmp_path / "changed.json"
    input_path.write_text(changed.model_dump_json(), encoding="utf-8")
    recorded = RecordedReview.model_validate_json((EXAMPLES / "sampleReview.json").read_text(encoding="utf-8"))
    recording_path = tmp_path / "changed-review.json"
    recording_path.write_text(recorded.model_copy(update={"inputHash": changed.inputDigest()}).model_dump_json(), encoding="utf-8")
    factory = CountingFactory()
    evaluator = service(JsonEvaluationRepository(tmp_path / "reports"), factory)
    first, _ = evaluator.evaluateFiles(EXAMPLES / "sampleInput.json", "recorded", EXAMPLES / "sampleReview.json")
    second, _ = evaluator.evaluateFiles(input_path, "recorded", recording_path)
    assert first.inputHash != second.inputHash
    assert factory.calls == 2


def test_failure_leaves_no_report_and_can_be_retried(tmp_path):
    repo = JsonEvaluationRepository(tmp_path / "reports")
    factory = CountingFactory(fail=True)
    evaluator = service(repo, factory)
    input_path = EXAMPLES / "sampleInput.json"
    original = input_path.read_bytes()
    with pytest.raises(EvaluationError, match="Timed out"):
        evaluator.evaluateFiles(input_path, "gemini")
    assert not repo.reportDirectory.exists()
    assert input_path.read_bytes() == original
    factory.fail = False
    report, path = evaluator.evaluateFiles(input_path, "recorded", EXAMPLES / "sampleReview.json")
    assert path.exists() and report.results


def test_failed_export_removes_canonical_report(tmp_path, monkeypatch):
    repo = JsonEvaluationRepository(tmp_path / "reports")
    original_write = repo._writeReport
    export_path = tmp_path / "export.json"

    def fail_export(report, output_path):
        if output_path == export_path:
            raise OSError("Export failed")
        original_write(report, output_path)

    monkeypatch.setattr(repo, "_writeReport", fail_export)
    with pytest.raises(OSError, match="Export failed"):
        service(repo, CountingFactory()).evaluateFiles(
            EXAMPLES / "sampleInput.json", "recorded", EXAMPLES / "sampleReview.json", outputPath=export_path
        )
    assert not export_path.exists()
    assert list(repo.reportDirectory.iterdir()) == []
