"""E04 evidence validation, scoring, and JSON report acceptance checks."""

from dataclasses import replace
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from source.Control.evaluation_controller import EvaluationController, EvaluationInput
from source.Model.evaluation import CriterionStatus
from source.service.evaluation_service import EvaluationService, EvidenceValidationError, build_feedback
from source.service.scoring_service import RubricScoringService
from source.service.providers.antigravity_provider import (
    AntigravityCriterionDTO,
    AntigravityProviderError,
    _resolve_quote_offsets,
)
from source.service.providers.fixture_provider import FixtureProvider

SAMPLE = (
    Path(__file__).resolve().parents[1]
    / "fixtures" / "e04" / "inventory_answer.json"
)


def load_bundle():
    return EvaluationInput.model_validate_json(SAMPLE.read_text(encoding="utf-8"))


def test_report_has_scores_evidence_feedback_and_original_inputs(tmp_path):
    destination = tmp_path / "report.json"
    report = EvaluationController(
        EvaluationService(), FixtureProvider(), "fixture"
    ).evaluate_file(SAMPLE, destination)

    saved = json.loads(destination.read_text(encoding="utf-8"))
    assert saved == report
    assert report["result"]["totalScore"] == 8
    assert report["result"]["maximumScore"] == 8
    assert len(report["result"]["criterionChecks"]) == 4
    assert len(report["feedbackItems"]) == 4
    answer = report["inputs"]["answer"]["text"]
    for check in report["result"]["criterionChecks"]:
        assert check["satisfiedExpectedIndexes"] == [0, 1]
        evidence = check["evidence"][0]
        assert answer[evidence["startOffset"]:evidence["endOffset"]] == evidence["quote"]


def test_unresolved_evidence_keeps_null_score_and_feedback(tmp_path):
    question, rubric, answer = EvaluationController.build_records(load_bundle())
    batch = FixtureProvider().interpret(
        question=question, rubric=rubric, answer_text=answer.text
    )
    first = replace(
        batch.observations[0],
        status=CriterionStatus.INSUFFICIENT_EVIDENCE,
        quote=None,
        start_offset=None,
        end_offset=None,
        observation="The answer needs clarification.",
        unresolved_reason="The evidence is ambiguous.",
        satisfied_expected_indexes=(),
    )
    interpreter = Mock()
    interpreter.interpret.return_value = replace(
        batch, observations=(first, *batch.observations[1:])
    )
    result = EvaluationService().evaluate_answer(
        answer=answer, question=question, rubric=rubric, interpreter=interpreter
    )
    feedback = build_feedback(result, rubric)
    assert result.total_score is None
    assert result.criterion_checks[0].score is None
    assert "Chưa đủ căn cứ" in feedback.criteria[0].message


def test_fabricated_quote_fails_before_scoring():
    question, rubric, answer = EvaluationController.build_records(load_bundle())
    batch = FixtureProvider().interpret(
        question=question, rubric=rubric, answer_text=answer.text
    )
    bad = replace(batch.observations[0], quote="fabricated", start_offset=0, end_offset=10)
    interpreter = Mock()
    interpreter.interpret.return_value = replace(
        batch, observations=(bad, *batch.observations[1:])
    )
    with pytest.raises(EvidenceValidationError, match="Fabricated or misaligned quote"):
        EvaluationService().evaluate_answer(
            answer=answer, question=question, rubric=rubric, interpreter=interpreter
        )


def test_antigravity_repairs_unique_exact_quote_offset_only():
    quote = "stock 1"
    answer = "Two buyers read stock 1 before committing."
    item = AntigravityCriterionDTO(
        status=CriterionStatus.MET,
        quote=quote,
        start_offset=16,
        end_offset=24,
        explanation="The answer identifies the shared read.",
        satisfied_expected_indexes=[0],
    )
    repaired = _resolve_quote_offsets("knowledge", item, answer)
    assert answer[repaired.start_offset:repaired.end_offset] == quote
    assert repaired.start_offset == answer.index(quote)
    trailing = AntigravityCriterionDTO(
        status=CriterionStatus.MET,
        quote="committing.",
        start_offset=answer.index("committing."),
        end_offset=len(answer) + 1,
        explanation="The quote is at the end of the answer.",
    )
    fixed_trailing = _resolve_quote_offsets("knowledge", trailing, answer)
    assert fixed_trailing.end_offset == len(answer)
    with pytest.raises(AntigravityProviderError, match="ambiguous"):
        _resolve_quote_offsets("knowledge", item, "stock 1 then stock 1 again")
    with pytest.raises(AntigravityProviderError, match="not present"):
        _resolve_quote_offsets("knowledge", item, "No matching literal text.")



def test_middle_rubric_level_is_reachable_for_partial_evidence():
    _question, rubric, _answer = EvaluationController.build_records(load_bundle())
    criterion = rubric.criteria[0]
    scorer = RubricScoringService()
    assert scorer.score_criterion(
        criterion, status=CriterionStatus.UNMET, satisfied_expected_indexes=(0,)
    ) == 1


def test_e04_cli_writes_json_using_the_merged_service(tmp_path):
    output = tmp_path / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable, "-m", "source.main", "--provider", "fixture",
            "--input", str(SAMPLE), "--output", str(output),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["result"]["totalScore"] == 8
    assert len(report["feedbackItems"]) == 4
