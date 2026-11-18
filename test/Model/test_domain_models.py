"""Acceptance checks for F02 typed domain records and invariants."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from source.Model.evaluation import (
    AnswerRevisionRef,
    CriterionCheck,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
    Evidence,
)
from source.Model.exercise import Exercise
from source.Model.ids import (
    AnswerId,
    CriterionId,
    EvaluationId,
    ExerciseId,
    QuestionId,
    RubricId,
    SessionId,
    SkillId,
    SourceId,
    VersionedRef,
)
from source.Model.interview import Answer, Session, SessionState
from source.Model.question import (
    Criterion,
    CriterionLevel,
    LicenseStatus,
    Question,
    ReviewChecks,
    ReviewMetadata,
    ReviewStatus,
    Rubric,
    SourceMetadata,
)

MODEL_DIR = Path(__file__).resolve().parents[2] / "source" / "Model"


def test_f02_model_layer_never_imports_view_control_or_service() -> None:
    forbidden_prefixes = ("source.view", "source.Control", "source.service", "fastapi", "jinja2")
    for py_file in MODEL_DIR.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            for mod in imported:
                assert not any(
                    mod == prefix or mod.startswith(prefix + ".")
                    for prefix in forbidden_prefixes
                ), f"{py_file} must not import {mod}"


def test_f02_valid_domain_records_preserve_zero_vs_null_and_verbatim_answer() -> None:
    now = datetime(2026, 11, 18, 4, 0, tzinfo=UTC)
    verbatim_text = "  Line 1: answer with leading spaces.\r\nLine 2.  "
    answer = Answer(
        id=AnswerId("answer.01"),
        revision=1,
        session_id=SessionId("session.01"),
        question_ref=VersionedRef(QuestionId("question.01"), 1),
        rubric_ref=VersionedRef(RubricId("rubric.01"), 1),
        text=verbatim_text,
        submitted_at=now,
        client_submission_id="subm-01",
    )
    # Original text is preserved verbatim and immutable
    assert answer.text == verbatim_text
    with pytest.raises(FrozenInstanceError):
        answer.text = "mutated"  # type: ignore[misc]

    # Numeric zero is preserved as 0 (not None)
    zero_check = CriterionCheck(
        criterion_id=CriterionId("crit.01"),
        status=CriterionStatus.UNMET,
        score=0,
        evidence=(
            Evidence(
                answer_ref=answer.ref,
                quote="Line 1",
                start_offset=2,
                end_offset=8,
            ),
        ),
        explanation="Explicitly incorrect.",
    )
    zero_eval = EvaluationResult(
        id=EvaluationId("eval.zero"),
        version=1,
        status=EvaluationStatus.COMPLETED,
        answer_ref=answer.ref,
        question_ref=answer.question_ref,
        rubric_ref=answer.rubric_ref,
        criterion_checks=(zero_check,),
        total_score=0,
        maximum_score=2,
    )
    assert zero_eval.total_score == 0
    assert zero_eval.criterion_checks[0].score == 0

    # Insufficient evidence keeps score=None and total_score=None
    null_check = CriterionCheck(
        criterion_id=CriterionId("crit.01"),
        status=CriterionStatus.INSUFFICIENT_EVIDENCE,
        score=None,
        evidence=(
            Evidence(
                answer_ref=answer.ref,
                observation="Referenced external file not attached.",
            ),
        ),
        explanation="Cannot verify missing attachment.",
        unresolved_reason="Missing referenced file.",
    )
    null_eval = EvaluationResult(
        id=EvaluationId("eval.null"),
        version=1,
        status=EvaluationStatus.COMPLETED,
        answer_ref=answer.ref,
        question_ref=answer.question_ref,
        rubric_ref=answer.rubric_ref,
        criterion_checks=(null_check,),
        total_score=None,
        maximum_score=2,
    )
    assert null_eval.total_score is None
    assert null_eval.criterion_checks[0].score is None


def test_f02_domain_invariants_reject_invalid_ids_versions_reviews_and_scores() -> None:
    now = datetime(2026, 11, 18, 4, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="VersionedRef.version"):
        VersionedRef(QuestionId("q.1"), 0)

    with pytest.raises(ValueError, match="reviewer_id must differ from curator_id"):
        ReviewMetadata(
            status=ReviewStatus.APPROVED,
            curator_id="same-person",
            reviewer_id="same-person",
            reviewed_at=now,
            checks=ReviewChecks(
                source_and_license_verified=True,
                original_and_adaptation_preserved=True,
                technical_correctness_checked=True,
                rubric_levels_distinct=True,
                equivalent_answers_checked=True,
                review_cases_checked=True,
            ),
        )

    with pytest.raises(ValueError, match="Verified source requires"):
        SourceMetadata(
            id=SourceId("source.bad"),
            url=None,
            revision="abc",
            author="Author",
            license_identifier="MIT",
            license_url="https://opensource.org/licenses/MIT",
            license_status=LicenseStatus.VERIFIED,
        )

    with pytest.raises(ValueError, match="score=None"):
        CriterionCheck(
            criterion_id=CriterionId("crit.1"),
            status=CriterionStatus.INSUFFICIENT_EVIDENCE,
            score=0,
            evidence=(),
            explanation="Should not coerce null to 0.",
            unresolved_reason="Missing evidence.",
        )

    with pytest.raises(ValueError, match="duplicate|repeat"):
        Session(
            id=SessionId("session.dup"),
            owner_token_hash="hash-1",
            role="backend_developer",
            level="intern_fresher",
            language="vi",
            state=SessionState.IN_PROGRESS,
            question_refs=(
                VersionedRef(QuestionId("q.same"), 1),
                VersionedRef(QuestionId("q.same"), 2),
            ),
        )

    with pytest.raises(ValueError, match="itself in prerequisite_ids"):
        Exercise(
            id=ExerciseId("ex.self"),
            version=1,
            title="Self prereq",
            summary="Summary",
            instructions="Instructions",
            related_skill_ids=(SkillId("skill.backend.data_consistency"),),
            source_id=SourceId("source.1"),
            prerequisite_ids=(ExerciseId("ex.self"),),
        )
