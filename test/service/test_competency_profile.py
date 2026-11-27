"""Profile persistence, evidence provenance, and next-session selection."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from source.Model.competency_profile import CompetencyState, CompetencyTrend, EvidenceConfidence
from source.Model.evaluation import CriterionCheck, CriterionStatus, EvaluationResult, EvaluationStatus, Evidence
from source.Model.ids import EvaluationId
from source.Model.interview import EvaluationTiming
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.config import load_settings
from source.main import create_app
from source.service.competency_profile_service import CompetencyProfileService
from source.service.interview_service import InterviewService
from source.service.providers.fixture_provider import FixtureProvider
from source.service.seed_loader import load_seed_catalog_into_repository
from test.fixtures.session_flow import complete_session, wait_for_evaluation_queue


def _assess_programming(
    store: SQLiteRepositoryStore, service: InterviewService, *, owner: str,
    outcome: CriterionStatus, evaluated_at: datetime, revision_count: int = 1,
) -> tuple[str, str]:
    session = service.open_session(
        owner_token_hash=owner, evaluation_timing=EvaluationTiming.AFTER_SESSION,
    ).session
    question = store.get_question(session.question_refs[0])
    assert question is not None
    first_answer = service.submit_answer(
        session_id=session.id, owner_token_hash=owner, question_ref=question.ref,
        text="Synthetic answer revision 0.",
        client_submission_id=f"{session.id}-revision-0",
    ).answer
    answers = [first_answer]
    if revision_count > 1:
        with store._connect() as conn, conn:
            for index in range(1, revision_count):
                revised = replace(
                    first_answer,
                    revision=index + 1,
                    text=f"Synthetic answer revision {index}.",
                    submitted_at=first_answer.submitted_at + timedelta(seconds=index),
                    client_submission_id=f"{session.id}-revision-{index}",
                )
                conn.execute(
                    """
                    INSERT INTO answers (
                        id, revision, session_id, question_id, question_version,
                        rubric_id, rubric_version, text, submitted_at, client_submission_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        revised.id, revised.revision, revised.session_id,
                        revised.question_ref.id, revised.question_ref.version,
                        revised.rubric_ref.id, revised.rubric_ref.version,
                        revised.text, revised.submitted_at.isoformat(), revised.client_submission_id,
                    ),
                )
                answers.append(revised)
    service.advance_question(
        session_id=session.id, owner_token_hash=owner, from_question_index=0,
    )
    for index, q_ref in enumerate(session.question_refs[1:], start=1):
        service.submit_answer(
            session_id=session.id, owner_token_hash=owner, question_ref=q_ref,
            text=f"Synthetic answer slot {index}.",
            client_submission_id=f"{session.id}-slot-{index}",
        )
        service.advance_question(
            session_id=session.id, owner_token_hash=owner, from_question_index=index,
        )
    rubric = store.get_rubric(question.rubric_ref)
    assert rubric is not None
    for index, answer in enumerate(answers):
        status = outcome if index == len(answers) - 1 else CriterionStatus.MET
        checks = tuple(CriterionCheck(
            criterion_id=criterion.id,
            status=status if criterion_index == 0 else CriterionStatus.MET,
            score=(0 if status is CriterionStatus.UNMET and criterion_index == 0
                   else criterion.max_score),
            evidence=(Evidence(answer_ref=answer.ref, observation="Synthetic observation."),),
            explanation="Synthetic assessment for profile projection.",
        ) for criterion_index, criterion in enumerate(rubric.criteria))
        store.save_evaluation(EvaluationResult(
            id=EvaluationId(f"evaluation.profile.{session.id}.{index}"),
            version=1, status=EvaluationStatus.COMPLETED,
            answer_ref=answer.ref, question_ref=question.ref,
            rubric_ref=answer.rubric_ref, criterion_checks=checks,
            total_score=sum(check.score for check in checks),
            maximum_score=rubric.maximum_score,
            evaluated_at=evaluated_at + timedelta(seconds=index),
        ))
    return session.id, question.id


def test_profile_backfills_latest_revision_and_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "profile.sqlite3"
    store = SQLiteRepositoryStore(path)
    load_seed_catalog_into_repository(store)
    profile = CompetencyProfileService(
        content_repo=store, session_repo=store, evaluation_repo=store, profile_repo=store,
    )
    service = InterviewService(
        content_repo=store, session_repo=store, evaluation_repo=store,
        profile_service=profile,
    )
    _, first_question_id = _assess_programming(
        store, service, owner="student-a", outcome=CriterionStatus.UNMET,
        evaluated_at=datetime.now(UTC), revision_count=2,
    )
    entries = profile.refresh("student-a")
    weak = next(item for item in entries if item.criterion_type == "behavior_explanation")
    assert weak.observed_count == 1  # Superseded answer is not counted twice.
    assert weak.unmet_count == 1
    assert weak.latest_answer_ref.revision == 2
    assert weak.state is CompetencyState.NEEDS_PRACTICE
    assert weak.evidence_confidence is EvidenceConfidence.LIMITED
    assert weak.selection_priority > 0
    assert profile.refresh("student-b") == ()

    reopened = SQLiteRepositoryStore(path)
    assert reopened.list_competency_profile("student-a") == entries
    next_session = service.open_session(owner_token_hash="student-a").session
    assert next_session.question_refs[0].id != first_question_id


def test_profile_tracks_latest_completed_observation_by_assessment_time(tmp_path: Path) -> None:
    store = SQLiteRepositoryStore(tmp_path / "trend.sqlite3")
    load_seed_catalog_into_repository(store)
    profile = CompetencyProfileService(
        content_repo=store, session_repo=store, evaluation_repo=store, profile_repo=store,
    )
    service = InterviewService(
        content_repo=store, session_repo=store, evaluation_repo=store,
        profile_service=profile,
    )
    now = datetime.now(UTC)
    _assess_programming(
        store, service, owner="student-a", outcome=CriterionStatus.UNMET,
        evaluated_at=now + timedelta(minutes=5),
    )
    _assess_programming(
        store, service, owner="student-a", outcome=CriterionStatus.MET,
        evaluated_at=now + timedelta(minutes=10),
    )
    # This session was created later but its synthetic assessment timestamp is
    # earlier than the previous one. Profile order follows assessment time.
    _assess_programming(
        store, service, owner="student-a", outcome=CriterionStatus.UNMET,
        evaluated_at=now + timedelta(minutes=7),
    )
    entry = next(
        item for item in profile.refresh("student-a")
        if item.criterion_type == "behavior_explanation"
    )
    assert (entry.observed_count, entry.unmet_count, entry.met_count) == (3, 2, 1)
    assert entry.state is CompetencyState.OBSERVED_STRENGTH
    assert entry.trend is CompetencyTrend.IMPROVING
    assert entry.evidence_confidence is EvidenceConfidence.MIXED
    assert entry.selection_priority == 0


def test_profile_api_updates_after_completed_evaluation_and_is_owner_scoped(tmp_path: Path) -> None:
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / "profile-api.sqlite3"),
        }),
        interpreter=FixtureProvider(),
    )
    with TestClient(app) as first, TestClient(app) as second:
        assert second.get("/api/profile").json()["entries"] == []
        assert first.get("/api/profile").json()["entries"] == []
        session_id, answers = complete_session(
            first, first_answer_text="Em kiểm thử hàm này.", submission_prefix="profile-api"
        )
        wait_for_evaluation_queue(app)
        assert session_id
        mine = first.get("/api/profile")
        assert mine.status_code == 200
        assert mine.json()["entries"]
        expected_ids = {item["answer_id"] for item in answers}
        assert all(
            item["latest_answer_ref"]["id"] in expected_ids
            for item in mine.json()["entries"]
        )
        assert second.get("/api/profile").json()["entries"] == []
