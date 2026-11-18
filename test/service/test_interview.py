"""Acceptance checks for I01 question selection, coverage errors, and session state transitions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from source.Model.evaluation import (
    CriterionCheck,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
    Evidence,
)
from source.Model.ids import EvaluationId
from source.Model.interview import SessionState
from source.service.interview_service import (
    InsufficientQuestionBankError,
    InterviewService,
    InvalidSessionStateError,
    UnsupportedBlueprintError,
)
from source.service.seed_loader import load_seed_catalog_into_repository
from test.fixtures.repositories import InMemoryRepositoryStore


def _make_seeded_service() -> tuple[InMemoryRepositoryStore, InterviewService]:
    store = InMemoryRepositoryStore()
    load_seed_catalog_into_repository(store)
    service = InterviewService(
        content_repo=store,
        session_repo=store,
        evaluation_repo=store,
    )
    return store, service


def test_i01_open_session_covers_four_blueprint_categories_and_rotates_unseen_variants() -> None:
    _, service = _make_seeded_service()

    first = service.open_session(owner_token_hash="owner-hash-a")
    assert first.session.state is SessionState.IN_PROGRESS
    assert len(first.session.question_refs) == 4
    assert first.current_question is not None

    # Open a second session for the same owner: since each category has 2 approved questions
    # in C02-C05, none of the 4 questions in session 2 should repeat session 1!
    second = service.open_session(owner_token_hash="owner-hash-a")
    first_ids = {ref.id for ref in first.session.question_refs}
    second_ids = {ref.id for ref in second.session.question_refs}
    assert first_ids.isdisjoint(second_ids)

    expected_categories = [
        "programming_knowledge",
        "technical_case",
        "algorithm_explanation",
        "ai_code_review",
    ]
    actual_categories = [
        service.get_owned_session(
            session_id=first.session.id, owner_token_hash="owner-hash-a"
        ).current_question.category  # slot 0
    ]
    assert actual_categories[0] == expected_categories[0]


def test_i01_reports_contextual_error_when_question_bank_is_empty_or_missing_slot() -> None:
    empty_store = InMemoryRepositoryStore()
    service = InterviewService(
        content_repo=empty_store,
        session_repo=empty_store,
        evaluation_repo=empty_store,
    )

    with pytest.raises(InsufficientQuestionBankError) as exc_info:
        service.open_session(owner_token_hash="owner-hash-a")

    assert set(exc_info.value.missing_by_category.keys()) == {
        "programming_knowledge",
        "technical_case",
        "algorithm_explanation",
        "ai_code_review",
    }

    with pytest.raises(UnsupportedBlueprintError):
        service.open_session(owner_token_hash="owner-hash-a", role="unknown_role")


def test_i01_enforces_ordered_question_transitions_and_completed_evaluation_gate() -> None:
    store, service = _make_seeded_service()
    snap = service.open_session(owner_token_hash="owner-hash-1")
    session_id = snap.session.id

    # Cannot skip ahead or advance before answering and evaluating
    with pytest.raises(InvalidSessionStateError, match="before submitting an answer"):
        service.advance_question(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            from_question_index=0,
        )

    with pytest.raises(InvalidSessionStateError, match="Expected from_question_index=0"):
        service.advance_question(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            from_question_index=2,
        )

    # Walk all 4 questions in order: submit -> require evaluation -> advance
    for expected_idx in range(4):
        current = service.get_owned_session(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
        )
        assert current.session.current_index == expected_idx
        assert current.current_question is not None

        submitted = service.submit_answer(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            question_ref=current.current_question.ref,
            text="Bài trả lời thử nghiệm hợp lệ cho bước hiện tại.",
            client_submission_id=f"subm-{expected_idx}",
        )

        # Still blocked before evaluation completes
        with pytest.raises(InvalidSessionStateError, match="evaluation has completed"):
            service.advance_question(
                session_id=session_id,
                owner_token_hash="owner-hash-1",
                from_question_index=expected_idx,
            )

        rubric = store.get_rubric(current.current_question.rubric_ref)
        assert rubric is not None
        checks = tuple(
            CriterionCheck(
                criterion_id=crit.id,
                status=CriterionStatus.MET,
                score=2,
                evidence=(
                    Evidence(
                        answer_ref=submitted.answer.ref,
                        quote="Bài trả lời",
                        start_offset=0,
                        end_offset=11,
                    ),
                ),
                explanation="Đạt tiêu chí.",
            )
            for crit in rubric.criteria
        )
        store.save_evaluation(
            EvaluationResult(
                id=EvaluationId(f"eval.{expected_idx}"),
                version=1,
                status=EvaluationStatus.COMPLETED,
                answer_ref=submitted.answer.ref,
                question_ref=current.current_question.ref,
                rubric_ref=current.current_question.rubric_ref,
                criterion_checks=checks,
                total_score=6,
                maximum_score=6,
                evaluated_at=datetime.now(UTC),
            )
        )

        advanced = service.advance_question(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            from_question_index=expected_idx,
        )
        # Replaying the exact same from_question_index is idempotent (W05)
        replayed = service.advance_question(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            from_question_index=expected_idx,
        )
        assert replayed.session.current_index == advanced.session.current_index
        assert replayed.session.state is advanced.session.state

    final_snap = service.get_owned_session(
        session_id=session_id,
        owner_token_hash="owner-hash-1",
    )
    assert final_snap.session.state is SessionState.COMPLETED
    assert final_snap.current_question is None
    assert final_snap.answered_count == 4
    assert final_snap.evaluated_count == 4
