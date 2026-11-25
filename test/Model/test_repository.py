"""Acceptance checks for F04 SQLite schema, reopen persistence, rollback, and idempotency."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

import pytest

from source.Model.evaluation import (
    CriterionCheck,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
    Evidence,
)
from source.Model.ids import (
    AnswerId,
    CriterionId,
    EvaluationId,
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
    Skill,
    SourceMetadata,
)
from source.Model.repositories.interfaces import (
    ContentRepository,
    DuplicateSubmissionConflictError,
    EvaluationRepository,
    RepositoryError,
    SessionRepository,
)
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore


def _approved_review(now: datetime) -> ReviewMetadata:
    return ReviewMetadata(
        status=ReviewStatus.APPROVED,
        curator_id="hwngMP",
        reviewer_id="Tin",
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


def _seed_question(store: SQLiteRepositoryStore, now: datetime) -> tuple[Question, Rubric]:
    skill = Skill(
        id=SkillId("skill.backend.data_consistency"),
        label="Data consistency",
        description="Preserve shared data invariants.",
    )
    source = SourceMetadata(
        id=SourceId("source.postgres.mvcc"),
        url="https://github.com/postgres/postgres/blob/83cefb7b738c32a66a91537aa502d99891a63b11/doc/src/sgml/mvcc.sgml",
        revision="83cefb7b738c32a66a91537aa502d99891a63b11",
        author="PostgreSQL Global Development Group",
        license_identifier="PostgreSQL",
        license_url="https://github.com/postgres/postgres/blob/83cefb7b738c32a66a91537aa502d99891a63b11/COPYRIGHT",
        license_status=LicenseStatus.VERIFIED,
        collected_at=now,
    )
    rubric = Rubric(
        id=RubricId("rubric.case.01"),
        version=1,
        criteria=(
            Criterion(
                id=CriterionId("crit.atomicity"),
                label="Atomic update and rollback",
                expected_evidence=("Atomic check-and-decrement inside transaction",),
                levels=(
                    CriterionLevel(score=0, description="Unsafe"),
                    CriterionLevel(score=1, description="Partial"),
                    CriterionLevel(score=2, description="Complete"),
                ),
            ),
        ),
        review=_approved_review(now),
    )
    question = Question(
        id=QuestionId("question.case.01"),
        version=1,
        category="technical_case",
        language="vi",
        prompt="Kho con mot san pham...",
        skill_ids=(skill.id,),
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        source_id=source.id,
        review=_approved_review(now),
    )
    store.save_skill(skill)
    store.save_source(source)
    store.save_rubric(rubric)
    store.save_question(question)
    return question, rubric


def test_f04_session_verbatim_answer_and_versioned_evaluation_survive_reopen(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "interview.sqlite3"
    now = datetime(2026, 11, 18, 4, 45, tzinfo=UTC)

    store1 = SQLiteRepositoryStore(db_file)
    assert isinstance(store1, ContentRepository)
    assert isinstance(store1, SessionRepository)
    assert isinstance(store1, EvaluationRepository)

    question, rubric = _seed_question(store1, now)
    session = Session(
        id=SessionId("session.sqlite.01"),
        owner_token_hash="owner-hash-abc",
        role="backend_developer",
        level="intern_fresher",
        language="vi",
        state=SessionState.IN_PROGRESS,
        question_refs=(question.ref,),
        created_at=now,
        updated_at=now,
    )
    store1.create_session(session)

    verbatim = "  SELECT stock FROM inventory FOR UPDATE;\r\nROLLBACK on error.  "
    answer = Answer(
        id=AnswerId("answer.sqlite.01"),
        revision=1,
        session_id=session.id,
        question_ref=question.ref,
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        text=verbatim,
        submitted_at=now,
        client_submission_id="subm-sqlite-01",
    )
    saved_ans, replayed = store1.save_answer(answer)
    assert saved_ans == answer
    assert replayed is False

    evaluation = EvaluationResult(
        id=EvaluationId("eval.sqlite.01"),
        version=1,
        status=EvaluationStatus.COMPLETED,
        answer_ref=answer.ref,
        question_ref=question.ref,
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        criterion_checks=(
            CriterionCheck(
                criterion_id=CriterionId("crit.atomicity"),
                status=CriterionStatus.MET,
                score=2,
                evidence=(
                    Evidence(
                        answer_ref=answer.ref,
                        quote="SELECT stock FROM inventory FOR UPDATE;",
                        start_offset=2,
                        end_offset=41,
                    ),
                ),
                explanation="Locks row inside transaction.",
            ),
        ),
        total_score=2,
        maximum_score=2,
        evaluated_at=now,
        prompt_version="interpret_answer/v1",
        model_id="fixture",
    )
    store1.save_evaluation(evaluation)

    # Reopen a brand-new SQLiteRepositoryStore instance on the same file
    store2 = SQLiteRepositoryStore(db_file)
    loaded_session = store2.get_session(session.id)
    assert loaded_session is not None
    assert loaded_session.answer_refs == (answer.ref,)

    loaded_answer = store2.get_answer(answer.ref)
    assert loaded_answer == answer
    assert loaded_answer.text == verbatim

    loaded_rubric = store2.get_rubric(loaded_answer.rubric_ref)
    assert loaded_rubric == rubric

    loaded_eval = store2.get_completed_evaluation_for_answer(answer.ref)
    assert loaded_eval == evaluation


def test_f04_idempotent_duplicate_submission_and_mid_transaction_rollback(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "rollback.sqlite3"
    now = datetime(2026, 11, 18, 5, 0, tzinfo=UTC)
    store = SQLiteRepositoryStore(db_file)
    question, rubric = _seed_question(store, now)

    session = Session(
        id=SessionId("session.rollback.01"),
        owner_token_hash="owner-hash-xyz",
        role="backend_developer",
        level="intern_fresher",
        language="vi",
        state=SessionState.IN_PROGRESS,
        question_refs=(question.ref,),
        created_at=now,
        updated_at=now,
    )
    store.create_session(session)

    answer = Answer(
        id=AnswerId("answer.rb.01"),
        revision=1,
        session_id=session.id,
        question_ref=question.ref,
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        text="Conditional UPDATE stock = stock - 1 WHERE stock >= 1",
        submitted_at=now,
        client_submission_id="subm-idempotent-01",
    )
    first_saved, first_replayed = store.save_answer(answer)
    assert first_replayed is False

    # Re-sending identical client_submission_id + text returns original record without duplicating
    second_saved, second_replayed = store.save_answer(
        Answer(
            id=AnswerId("answer.rb.duplicate-attempt"),
            revision=1,
            session_id=session.id,
            question_ref=question.ref,
            rubric_ref=VersionedRef(rubric.id, rubric.version),
            text=answer.text,
            submitted_at=now,
            client_submission_id="subm-idempotent-01",
        )
    )
    assert second_saved == first_saved
    assert second_replayed is True
    assert len(store.list_answers_for_session(session.id)) == 1

    # Conflicting text under same client_submission_id raises conflict and leaves DB untouched
    with pytest.raises(DuplicateSubmissionConflictError):
        store.save_answer(
            Answer(
                id=AnswerId("answer.rb.conflict"),
                revision=1,
                session_id=session.id,
                question_ref=question.ref,
                rubric_ref=VersionedRef(rubric.id, rubric.version),
                text="Mutated text with same submission ID",
                submitted_at=now,
                client_submission_id="subm-idempotent-01",
            )
        )
    assert len(store.list_answers_for_session(session.id)) == 1

    # Saving an evaluation referencing a non-existent answer fails FK check and leaves zero partial rows
    bad_eval = EvaluationResult(
        id=EvaluationId("eval.orphan"),
        version=1,
        status=EvaluationStatus.COMPLETED,
        answer_ref=Answer(
            id=AnswerId("answer.missing"),
            revision=1,
            session_id=session.id,
            question_ref=question.ref,
            rubric_ref=VersionedRef(rubric.id, rubric.version),
            text="Unpersisted answer",
            submitted_at=now,
        ).ref,
        question_ref=question.ref,
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        criterion_checks=(
            CriterionCheck(
                criterion_id=CriterionId("crit.atomicity"),
                status=CriterionStatus.UNMET,
                score=0,
                evidence=(
                    Evidence(
                        answer_ref=Answer(
                            id=AnswerId("answer.missing"),
                            revision=1,
                            session_id=session.id,
                            question_ref=question.ref,
                            rubric_ref=VersionedRef(rubric.id, rubric.version),
                            text="Unpersisted answer",
                            submitted_at=now,
                        ).ref,
                        observation="No transaction mentioned.",
                    ),
                ),
                explanation="Missing transaction.",
            ),
        ),
        total_score=0,
        maximum_score=2,
    )
    with pytest.raises(RepositoryError):
        store.save_evaluation(bad_eval)

    assert store.get_evaluation(EvaluationId("eval.orphan")) is None
    with sqlite3.connect(db_file) as raw_conn:
        count = raw_conn.execute(
            "SELECT COUNT(*) FROM evaluation_criterion_checks WHERE evaluation_id = 'eval.orphan';"
        ).fetchone()[0]
        assert count == 0


def test_f04_concurrent_identical_submission_ids_return_one_saved_answer(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 11, 18, 5, 30, tzinfo=UTC)
    db_file = tmp_path / "concurrent-submissions.sqlite3"
    setup_store = SQLiteRepositoryStore(db_file)
    question, rubric = _seed_question(setup_store, now)
    session = Session(
        id=SessionId("session.concurrent.01"),
        owner_token_hash="owner-hash-concurrent",
        role="backend_developer",
        level="intern_fresher",
        language="vi",
        state=SessionState.IN_PROGRESS,
        question_refs=(question.ref,),
        created_at=now,
        updated_at=now,
    )
    setup_store.create_session(session)

    answers = (
        Answer(
            id=AnswerId("answer.concurrent.01"),
            revision=1,
            session_id=session.id,
            question_ref=question.ref,
            rubric_ref=VersionedRef(rubric.id, rubric.version),
            text="Same verbatim response",
            submitted_at=now,
            client_submission_id="subm-concurrent-01",
        ),
        Answer(
            id=AnswerId("answer.concurrent.02"),
            revision=1,
            session_id=session.id,
            question_ref=question.ref,
            rubric_ref=VersionedRef(rubric.id, rubric.version),
            text="Same verbatim response",
            submitted_at=now,
            client_submission_id="subm-concurrent-01",
        ),
    )
    stores = (SQLiteRepositoryStore(db_file), SQLiteRepositoryStore(db_file))
    start_together = Barrier(2)

    def submit(index: int) -> tuple[Answer, bool]:
        start_together.wait(timeout=5)
        return stores[index].save_answer(answers[index])

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(submit, index) for index in range(2)]
        results = [future.result(timeout=10) for future in futures]

    assert sorted(replayed for _, replayed in results) == [False, True]
    assert results[0][0] == results[1][0]
    assert setup_store.list_answers_for_session(session.id) == (results[0][0],)


def test_q02_repository_session_state_transitions_and_history_invariants(
    tmp_path: Path,
) -> None:
    """Q02: Verify session state transitions, history invariants, and non-existent updates."""
    now = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)
    db_file = tmp_path / "session_transitions.sqlite3"
    store = SQLiteRepositoryStore(db_file)
    question, _rubric = _seed_question(store, now)

    session = Session(
        id=SessionId("session.q02.transitions"),
        owner_token_hash="owner-token-hash-q02",
        role="backend_developer",
        level="intern_fresher",
        language="vi",
        state=SessionState.IN_PROGRESS,
        question_refs=(question.ref,),
        current_index=0,
        answer_refs=(),
        created_at=now,
        updated_at=now,
    )
    store.create_session(session)

    # 1. Verify initial state and owner listing
    loaded = store.get_session(session.id)
    assert loaded is not None
    assert loaded.state is SessionState.IN_PROGRESS
    assert loaded.current_index == 0
    by_owner = store.list_sessions_by_owner("owner-token-hash-q02")
    assert len(by_owner) == 1
    assert by_owner[0].id == session.id

    # 2. Transition state to COMPLETED
    updated_session = Session(
        id=session.id,
        owner_token_hash=session.owner_token_hash,
        role=session.role,
        level=session.level,
        language=session.language,
        state=SessionState.COMPLETED,
        question_refs=session.question_refs,
        current_index=1,
        answer_refs=session.answer_refs,
        created_at=session.created_at,
        updated_at=now,
    )
    store.update_session(updated_session)
    completed_loaded = store.get_session(session.id)
    assert completed_loaded is not None
    assert completed_loaded.state is SessionState.COMPLETED
    assert completed_loaded.current_index == 1
    assert completed_loaded.question_refs == (question.ref,)

    # 3. Transition state to ENDED_EARLY
    ended_session = Session(
        id=session.id,
        owner_token_hash=session.owner_token_hash,
        role=session.role,
        level=session.level,
        language=session.language,
        state=SessionState.ENDED_EARLY,
        question_refs=session.question_refs,
        current_index=1,
        answer_refs=session.answer_refs,
        created_at=session.created_at,
        updated_at=now,
    )
    store.update_session(ended_session)
    ended_loaded = store.get_session(session.id)
    assert ended_loaded is not None
    assert ended_loaded.state is SessionState.ENDED_EARLY

    # 4. Updating a non-existent session raises RecordNotFoundError
    ghost_session = Session(
        id=SessionId("session.ghost.not-exists"),
        owner_token_hash="ghost-hash",
        role="backend_developer",
        level="intern_fresher",
        language="vi",
        state=SessionState.IN_PROGRESS,
        question_refs=(question.ref,),
        created_at=now,
        updated_at=now,
    )
    from source.Model.repositories.interfaces import RecordNotFoundError

    with pytest.raises(RecordNotFoundError):
        store.update_session(ghost_session)


def test_q02_repository_transaction_rollback_on_failed_evaluation(
    tmp_path: Path,
) -> None:
    """Q02: Foreign key violation rolls back evaluation transaction with no orphan checks."""
    now = datetime(2026, 11, 24, 10, 30, tzinfo=UTC)
    db_file = tmp_path / "rollback_eval.sqlite3"
    store = SQLiteRepositoryStore(db_file)
    question, rubric = _seed_question(store, now)

    session = Session(
        id=SessionId("session.q02.eval_rb"),
        owner_token_hash="owner-token-hash-rb",
        role="backend_developer",
        level="intern_fresher",
        language="vi",
        state=SessionState.IN_PROGRESS,
        question_refs=(question.ref,),
        created_at=now,
        updated_at=now,
    )
    store.create_session(session)

    # Attempting to save evaluation referencing a non-existent answer
    orphan_eval = EvaluationResult(
        id=EvaluationId("eval.q02.orphan"),
        version=1,
        status=EvaluationStatus.COMPLETED,
        answer_ref=Answer(
            id=AnswerId("answer.does_not_exist"),
            revision=1,
            session_id=session.id,
            question_ref=question.ref,
            rubric_ref=VersionedRef(rubric.id, rubric.version),
            text="Unsaved answer",
            submitted_at=now,
        ).ref,
        question_ref=question.ref,
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        criterion_checks=(
            CriterionCheck(
                criterion_id=CriterionId("crit.atomicity"),
                status=CriterionStatus.MET,
                score=2,
                evidence=(),
                explanation="Check for non-existent answer",
            ),
        ),
        total_score=2,
        maximum_score=2,
    )
    with pytest.raises(RepositoryError):
        store.save_evaluation(orphan_eval)

    # Verify no partial rows exist in SQLite
    with sqlite3.connect(db_file) as conn:
        eval_count = conn.execute(
            "SELECT COUNT(*) FROM evaluations WHERE id = 'eval.q02.orphan';"
        ).fetchone()[0]
        check_count = conn.execute(
            "SELECT COUNT(*) FROM evaluation_criterion_checks WHERE evaluation_id = 'eval.q02.orphan';"
        ).fetchone()[0]
        assert eval_count == 0
        assert check_count == 0


def test_q02_repository_test_environment_isolation(tmp_path: Path) -> None:
    """Q02: Verify test records are isolated in tmp_path without touching real database."""
    prod_db = Path(".local/interview.sqlite3")
    prod_mtime_before = prod_db.stat().st_mtime if prod_db.exists() else None

    # Run isolated repository actions
    test_db = tmp_path / "isolated.sqlite3"
    store = SQLiteRepositoryStore(test_db)
    now = datetime(2026, 11, 24, 11, 0, tzinfo=UTC)
    _seed_question(store, now)

    assert test_db.exists()
    assert test_db != prod_db

    prod_mtime_after = prod_db.stat().st_mtime if prod_db.exists() else None
    assert prod_mtime_before == prod_mtime_after

