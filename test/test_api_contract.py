"""Acceptance checks for P04, P05, P06, and P08 contracts and fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from source.Control.schemas import (
    ApiErrorResponse,
    CriterionCheckDTO,
    ErrorCode,
    EvaluationResultDTO,
    ExerciseRecommendationsResponse,
    SessionSummaryDTO,
    SessionViewDTO,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from source.Model.evaluation import CriterionStatus, EvaluationStatus
from source.Model.ids import QuestionId, RubricId, SkillId, SourceId, VersionedRef
from source.Model.question import Question
from source.service.coverage import missing_coverage

ROOT_DIR = Path(__file__).resolve().parents[1]
API_FIXTURES_DIR = ROOT_DIR / "test" / "fixtures" / "api"
SEED_DIR = ROOT_DIR / "data" / "seed"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_p04_success_fixtures_validate_against_controller_schemas() -> None:
    session = SessionViewDTO.model_validate(_load_json(API_FIXTURES_DIR / "session_created.json"))
    assert session.current_question is not None
    assert "expected_evidence" not in (API_FIXTURES_DIR / "session_created.json").read_text(encoding="utf-8")

    submitted = SubmitAnswerResponse.model_validate(
        _load_json(API_FIXTURES_DIR / "answer_submitted.json")
    )
    assert submitted.answer.session_id == session.session_id
    assert submitted.evaluation_status is EvaluationStatus.PENDING

    completed = EvaluationResultDTO.model_validate(
        _load_json(API_FIXTURES_DIR / "evaluation_completed.json")
    )
    assert completed.total_score == 5
    assert completed.maximum_score == 6
    for check in completed.criterion_checks:
        for ev in check.evidence:
            if ev.quote is not None:
                assert completed.answer_text[ev.start_offset : ev.end_offset] == ev.quote

    unresolved = EvaluationResultDTO.model_validate(
        _load_json(API_FIXTURES_DIR / "evaluation_insufficient_evidence.json")
    )
    assert unresolved.total_score is None
    assert all(
        check.status is CriterionStatus.INSUFFICIENT_EVIDENCE and check.score is None
        for check in unresolved.criterion_checks
    )

    summary = SessionSummaryDTO.model_validate(
        _load_json(API_FIXTURES_DIR / "session_summary.json")
    )
    assert summary.outcomes[0].total_score == 5
    assert summary.outcomes[1].total_score is None
    assert len(summary.observed_gaps) == 1

    exercises = ExerciseRecommendationsResponse.model_validate(
        _load_json(API_FIXTURES_DIR / "exercise_recommendations.json")
    )
    assert len(exercises.recommendations) == 1
    assert exercises.recommendations[0].matched_gap.criterion_id == "c03.concurrent_tests"


def test_p04_error_fixtures_cover_invalid_input_foreign_session_conflict_and_timeout() -> None:
    raw_errors = _load_json(API_FIXTURES_DIR / "errors.json")
    assert isinstance(raw_errors, dict)

    invalid_input = ApiErrorResponse.model_validate(raw_errors["invalid_input"])
    assert invalid_input.error_code is ErrorCode.INVALID_INPUT
    assert invalid_input.retryable is False
    assert "text" in invalid_input.field_errors

    foreign_session = ApiErrorResponse.model_validate(raw_errors["foreign_session"])
    assert foreign_session.error_code is ErrorCode.SESSION_FORBIDDEN
    assert foreign_session.retryable is False

    conflict = ApiErrorResponse.model_validate(raw_errors["submission_conflict"])
    assert conflict.error_code is ErrorCode.SUBMISSION_CONFLICT
    assert conflict.answer_ref is not None

    timeout = ApiErrorResponse.model_validate(raw_errors["provider_timeout"])
    assert timeout.error_code is ErrorCode.PROVIDER_TIMEOUT
    assert timeout.retryable is True
    assert timeout.answer_ref is not None


def test_p04_schemas_reject_blank_answers_and_coerced_unresolved_scores() -> None:
    with pytest.raises(ValidationError):
        SubmitAnswerRequest(
            question_id="case.c03.inventory_race.v1",
            question_version=1,
            client_submission_id="subm-blank",
            text="   ",
        )

    with pytest.raises(ValidationError, match="score=null"):
        CriterionCheckDTO(
            criterion_id="c03.race",
            criterion_label="Nhận ra thao tác tranh chấp",
            status=CriterionStatus.INSUFFICIENT_EVIDENCE,
            score=0,
            max_score=2,
            evidence=(),
            explanation="Chưa đủ bằng chứng",
            unresolved_reason="Thiếu tệp đính kèm",
        )

    bad_eval = dict(_load_json(API_FIXTURES_DIR / "evaluation_completed.json"))
    bad_eval["total_score"] = 6
    with pytest.raises(ValidationError, match="sum of decidable criterion scores"):
        EvaluationResultDTO.model_validate(bad_eval)

    mismatched_quote_eval = json.loads(
        (API_FIXTURES_DIR / "evaluation_completed.json").read_text(encoding="utf-8")
    )
    mismatched_quote_eval["answer_text"] = "X" * len(mismatched_quote_eval["answer_text"])
    with pytest.raises(ValidationError, match="Evidence quote does not match"):
        EvaluationResultDTO.model_validate(mismatched_quote_eval)


def test_p05_case_question_rubric_provenance_and_review_fixture_are_aligned() -> None:
    skills = {item["id"] for item in _load_json(SEED_DIR / "skills.json")}
    [blueprint] = _load_json(SEED_DIR / "session_blueprints.json")
    case_slot = next(
        slot for slot in blueprint["slots"] if slot["category"] == "technical_case"
    )
    sources = {item["id"]: item for item in _load_json(SEED_DIR / "source_registry.json")}
    cases = _load_json(SEED_DIR / "questions" / "cases.json")
    review_fixture = _load_json(ROOT_DIR / "test" / "fixtures" / "question_reviews" / "p05.json")

    assert len(cases) >= 1
    case_record = cases[0]
    assert case_record["example_only"] is False
    assert case_record["id"] == "case.c03.inventory_race.v1"
    assert set(case_record["skill_ids"]).issubset(skills)
    assert case_slot["skill_id"] in case_record["skill_ids"]

    domain_question = Question(
        id=QuestionId(case_record["id"]),
        version=case_record["version"],
        category=case_record["category"],
        language=case_record["language"],
        prompt=case_record["prompt"],
        skill_ids=tuple(SkillId(s) for s in case_record["skill_ids"]),
        rubric_ref=VersionedRef(
            RubricId(case_record["rubric"]["id"]),
            case_record["rubric"]["version"],
        ),
        source_id=SourceId(case_record["source_id"]),
        constraints=tuple(case_record["constraints"]),
    )
    assert (
        missing_coverage(
            {"technical_case": SkillId(case_slot["skill_id"])},
            [domain_question],
        )
        == {}
    )

    source_record = sources[case_record["source_id"]]
    assert source_record["license"]["status"] == "verified"
    assert source_record["license"]["spdx_id"] in {"MIT", "PostgreSQL"}
    assert source_record["revision"]
    assert source_record["original_content"]["question_text"]

    review = case_record["review"]
    assert review["status"] == "approved"
    assert review["curator_id"] and review["reviewer_id"]
    assert review["curator_id"] != review["reviewer_id"]
    assert all(review["checks"].values())

    criteria = case_record["rubric"]["criteria"]
    criterion_ids = [item["id"] for item in criteria]
    for item in criteria:
        assert item["criterion_type"] in case_slot["eligible_criterion_types"]
        assert [level["score"] for level in item["levels"]] == [0, 1, 2]
        assert item["equivalent_answers"].strip()

    assert review_fixture["question_id"] == case_record["id"]
    assert review_fixture["rubric_id"] == case_record["rubric"]["id"]
    assert len(review_fixture["cases"]) == 4

    for sample in review_fixture["cases"]:
        assert [check["criterion_id"] for check in sample["checks"]] == criterion_ids
        for check in sample["checks"]:
            assert check["evidence_quote"] in sample["answer"]
        if any(check["status"] == "insufficient_evidence" for check in sample["checks"]):
            assert sample["expected_total"] is None
            assert all(
                check["score"] is None
                for check in sample["checks"]
                if check["status"] == "insufficient_evidence"
            )
        else:
            assert sample["expected_total"] == sum(check["score"] for check in sample["checks"])


def test_p06_tokens_and_p08_workflow_documents_exist_and_cover_required_contracts() -> None:
    tokens_css = (ROOT_DIR / "source" / "view" / "static" / "css" / "tokens.css").read_text(
        encoding="utf-8"
    )
    for required_token in (
        "--sbx-paper: #f7f3e9",
        "--sbx-card: #fffdf6",
        "--sbx-violet: #6346f5",
        "--color-canvas: var(--sbx-paper)",
        "--color-surface: var(--sbx-card)",
        "--color-primary: var(--sbx-violet)",
        "--color-status-met-bg",
        "--color-status-unmet-bg",
        "--color-status-unresolved-bg",
        "--color-evidence-highlight-active-bg",
        "--font-sans: \"Be Vietnam Pro\"",
        "prefers-reduced-motion: reduce",
    ):
        assert required_token in tokens_css

    ui_direction = (ROOT_DIR / "docs" / "ui_direction.md").read_text(encoding="utf-8")
    assert "Xem căn cứ trên bài làm" in ui_direction
    assert "Chưa đủ bằng chứng" in ui_direction
    assert "360px" in ui_direction

    team_workflow = (ROOT_DIR / "docs" / "team_workflow.md").read_text(encoding="utf-8")
    assert "[T...] <short description>" in team_workflow
    assert "Definition of Done" in team_workflow
    assert "Tin" in team_workflow
