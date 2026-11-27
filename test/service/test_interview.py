"""Acceptance checks for I01 question selection, coverage errors, and session state transitions."""

from __future__ import annotations

import pytest

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


def test_session_advances_in_order_after_each_saved_answer_without_waiting_for_evaluation() -> None:
    _store, service = _make_seeded_service()
    snap = service.open_session(owner_token_hash="owner-hash-1")
    session_id = snap.session.id

    # Cannot skip ahead or advance before answering.
    with pytest.raises(InvalidSessionStateError, match="Submit an answer"):
        service.advance_question(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            from_question_index=0,
        )

    with pytest.raises(InvalidSessionStateError, match="current question has changed"):
        service.advance_question(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            from_question_index=2,
        )

    # Walk all four questions without creating any evaluations.
    for expected_idx in range(4):
        current = service.get_owned_session(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
        )
        assert current.session.current_index == expected_idx
        assert current.current_question is not None

        service.submit_answer(
            session_id=session_id,
            owner_token_hash="owner-hash-1",
            question_ref=current.current_question.ref,
            text="Bài trả lời thử nghiệm hợp lệ cho bước hiện tại.",
            client_submission_id=f"subm-{expected_idx}",
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
    assert final_snap.evaluated_count == 0


def test_i01_rejects_negative_retry_index_before_first_question() -> None:
    _store, service = _make_seeded_service()
    snapshot = service.open_session(owner_token_hash="owner-hash-negative-index")

    with pytest.raises(InvalidSessionStateError, match="current question has changed"):
        service.advance_question(
            session_id=snapshot.session.id,
            owner_token_hash="owner-hash-negative-index",
            from_question_index=-1,
        )
