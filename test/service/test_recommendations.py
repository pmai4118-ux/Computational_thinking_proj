"""I06 acceptance checks for reviewed exercise selection and targeted practice."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.Model.evaluation import (
    AnswerRevisionRef,
    CriterionCheck,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
)
from source.Model.ids import AnswerId, CriterionId, EvaluationId, ExerciseId
from source.Model.interview import Answer
from source.Model.question import ReviewMetadata
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.main import create_app
from source.service.recommendation_service import RecommendationService
from test.fixtures.repositories import InMemoryRepositoryStore


class EmptyExerciseStore(InMemoryRepositoryStore):
    def list_approved_exercises(self):  # type: ignore[override]
        return ()


class SingleVariantStore(InMemoryRepositoryStore):
    only_question_id: str | None = None

    def list_approved_questions(self, *, role: str, level: str, language: str):  # type: ignore[override]
        questions = super().list_approved_questions(role=role, level=level, language=language)
        if self.only_question_id is None:
            return questions
        return tuple(
            question for question in questions
            if question.category != "technical_case" or question.id == self.only_question_id
        )


class BrokenPrerequisiteStore(InMemoryRepositoryStore):
    def list_approved_exercises(self):  # type: ignore[override]
        return tuple(
            replace(item, prerequisite_ids=(ExerciseId("exercise.missing"),))
            if item.id == "exercise.backend.rollback_invariant_test" else item
            for item in super().list_approved_exercises()
        )


def _app(tmp_path: Path, store: InMemoryRepositoryStore):
    return create_app(
        settings=Settings(
            provider=ProviderMode.FIXTURE,
            database_path=tmp_path / "unused.sqlite3",
            gemini_timeout_seconds=10.0,
        ),
        content_repo=store,
        session_repo=store,
        evaluation_repo=store,
    )


def _evaluated_answer(
    client: TestClient,
    store: InMemoryRepositoryStore,
    *,
    target_status: CriterionStatus = CriterionStatus.UNMET,
    additional_unmet_types: tuple[str, ...] = (),
) -> tuple[str, AnswerRevisionRef, CriterionId]:
    response = client.post("/api/sessions", json={})
    assert response.status_code == 201
    session_id = response.json()["session_id"]
    session = store.get_session(session_id)
    assert session is not None
    question = next(
        store.get_question(ref) for ref in session.question_refs
        if store.get_question(ref).category == "technical_case"  # type: ignore[union-attr]
    )
    assert question is not None
    rubric = store.get_rubric(question.rubric_ref)
    assert rubric is not None
    target = next(item for item in rubric.criteria if item.criterion_type == "test_design")
    answer = Answer(
        id=AnswerId("answer.i06.synthetic"),
        revision=1,
        session_id=session.id,
        question_ref=question.ref,
        rubric_ref=question.rubric_ref,
        text="A synthetic response that omits the rollback test.",
        submitted_at=datetime.now(UTC),
    )
    store.save_answer(answer)
    checks = tuple(
        CriterionCheck(
            criterion_id=item.id,
            status=(
                target_status
                if item.id == target.id
                else (
                    CriterionStatus.UNMET
                    if item.criterion_type in additional_unmet_types
                    else CriterionStatus.MET
                )
            ),
            score=(
                (None if target_status is CriterionStatus.INSUFFICIENT_EVIDENCE else 1)
                if item.id == target.id
                else (1 if item.criterion_type in additional_unmet_types else item.max_score)
            ),
            evidence=(),
            explanation=(
                "Rollback test is missing."
                if item.id == target.id
                else (
                    "Atomicity invariant is missing."
                    if item.criterion_type in additional_unmet_types
                    else "Met."
                )
            ),
            unresolved_reason=(
                "The answer refers to unavailable material."
                if item.id == target.id and target_status is CriterionStatus.INSUFFICIENT_EVIDENCE
                else None
            ),
        )
        for item in rubric.criteria
    )
    result = EvaluationResult(
        id=EvaluationId("evaluation.i06.synthetic"),
        version=1,
        status=EvaluationStatus.COMPLETED,
        answer_ref=answer.ref,
        question_ref=question.ref,
        rubric_ref=question.rubric_ref,
        criterion_checks=checks,
        total_score=(
            None if target_status is CriterionStatus.INSUFFICIENT_EVIDENCE
            else sum(check.score for check in checks if check.score is not None)
        ),
        maximum_score=rubric.maximum_score,
    )
    store.save_evaluation(result)
    return session_id, answer.ref, target.id


def test_i06_orders_prerequisites_and_exposes_reviewed_detail_and_alternate(tmp_path: Path) -> None:
    store = InMemoryRepositoryStore()
    app = _app(tmp_path, store)
    with TestClient(app) as client:
        session_id, answer_ref, criterion_id = _evaluated_answer(client, store)
        response = client.get(f"/api/sessions/{session_id}/exercises")
        assert response.status_code == 200
        suggestions = response.json()["recommendations"]
        ids = [item["exercise_id"] for item in suggestions]
        prerequisite_id = "exercise.backend.atomic_transaction_locking"
        target_id = "exercise.backend.rollback_invariant_test"
        assert ids.index(prerequisite_id) < ids.index(target_id)
        target = next(item for item in suggestions if item["exercise_id"] == target_id)
        assert target["matched_gap"]["criterion_id"] == criterion_id
        assert target["recommendation_reason"]
        assert target["eligible_alternate_question_available"] is True

        detail = client.get(f"/api/exercises/{target_id}?version=1")
        assert detail.status_code == 200
        assert detail.json()["instructions"]
        assert detail.json()["prerequisite_ids"] == [prerequisite_id]
        assert detail.json()["source"]["source_id"]

        practice = client.post(
            f"/api/sessions/{session_id}/answers/{answer_ref.id}/practice",
            json={
                "answer_revision": answer_ref.revision,
                "criterion_id": criterion_id,
                "exercise_id": target_id,
            },
        )
        assert practice.status_code == 201
        assert practice.json()["progress"]["total_questions"] == 1
        original = store.get_answer(answer_ref)
        assert original is not None
        assert practice.json()["current_question"]["id"] != original.question_ref.id
        assert store.get_session(practice.json()["session_id"]) is not None


def test_i06_unresolved_evidence_never_creates_a_gap(tmp_path: Path) -> None:
    store = InMemoryRepositoryStore()
    app = _app(tmp_path, store)
    with TestClient(app) as client:
        session_id, _, _ = _evaluated_answer(
            client, store, target_status=CriterionStatus.INSUFFICIENT_EVIDENCE
        )
        response = client.get(f"/api/sessions/{session_id}/exercises")
        assert response.status_code == 200
        assert response.json()["recommendations"] == []
        assert response.json()["unmatched_skill_ids"] == []
        assert "No confirmed gaps" in response.json()["message"]


def test_i06_new_answer_revision_without_completed_evaluation_has_no_gap(tmp_path: Path) -> None:
    store = InMemoryRepositoryStore()
    app = _app(tmp_path, store)
    with TestClient(app) as client:
        session_id, answer_ref, _ = _evaluated_answer(client, store)
        original = store.get_answer(answer_ref)
        assert original is not None
        store.save_answer(
            replace(
                original, revision=2, text="A revised answer awaiting evaluation.",
                submitted_at=datetime.now(UTC),
            )
        )
        response = client.get(f"/api/sessions/{session_id}/exercises")
        assert response.status_code == 200
        assert response.json()["recommendations"] == []
        assert response.json()["unmatched_skill_ids"] == []


def test_i06_no_reviewed_match_is_explicit_and_foreign_session_is_forbidden(tmp_path: Path) -> None:
    store = EmptyExerciseStore()
    app = _app(tmp_path, store)
    with TestClient(app) as owner, TestClient(app) as stranger:
        session_id, _, _ = _evaluated_answer(owner, store)
        response = owner.get(f"/api/sessions/{session_id}/exercises")
        assert response.status_code == 200
        assert response.json()["recommendations"] == []
        assert response.json()["unmatched_skill_ids"] == ["skill.backend.data_consistency"]
        assert stranger.get(f"/api/sessions/{session_id}/exercises").status_code == 403
        assert owner.get("/api/exercises/exercise.unknown").status_code == 404


def test_i06_practice_requires_owned_answer_and_different_reviewed_question(tmp_path: Path) -> None:
    store = SingleVariantStore()
    app = _app(tmp_path, store)
    with TestClient(app) as owner, TestClient(app) as stranger:
        session_id, answer_ref, criterion_id = _evaluated_answer(owner, store)
        original = store.get_answer(answer_ref)
        assert original is not None
        store.only_question_id = original.question_ref.id
        url = f"/api/sessions/{session_id}/answers/{answer_ref.id}/practice"
        payload = {
            "answer_revision": answer_ref.revision,
            "criterion_id": criterion_id,
            "exercise_id": "exercise.backend.rollback_invariant_test",
        }
        assert stranger.post(url, json=payload).status_code == 403
        assert owner.post(url, json={**payload, "answer_revision": 2}).status_code == 422
        assert owner.post(url, json=payload).status_code == 409
        suggestions = owner.get(f"/api/sessions/{session_id}/exercises").json()["recommendations"]
        assert all(not item["eligible_alternate_question_available"] for item in suggestions)


def test_i06_invalid_prerequisite_chain_is_not_recommended(tmp_path: Path) -> None:
    store = BrokenPrerequisiteStore()
    app = _app(tmp_path, store)
    with TestClient(app) as client:
        session_id, _, _ = _evaluated_answer(client, store)
        service: RecommendationService = app.state.container.recommendation_service
        original = next(
            item for item in store.list_approved_exercises()
            if item.id == "exercise.backend.rollback_invariant_test"
        )
        catalog = {original.id: original}
        assert service._ordered_chain(original, catalog) is None
        other = next(
            item for item in store.list_approved_exercises()
            if item.id == "exercise.backend.atomic_transaction_locking"
        )
        cyclic = replace(other, prerequisite_ids=(original.id,))
        assert service._ordered_chain(original, {original.id: original, cyclic.id: cyclic}) is None
        response = client.get(f"/api/sessions/{session_id}/exercises")
        assert response.status_code == 200
        assert response.json()["recommendations"] == []
        assert response.json()["unmatched_skill_ids"] == ["skill.backend.data_consistency"]


def test_i06_sqlite_repository_serves_seeded_reviewed_exercises(tmp_path: Path) -> None:
    store = SQLiteRepositoryStore(tmp_path / "i06.sqlite3")
    app = _app(tmp_path, store)
    with TestClient(app) as client:
        session_id, _, _ = _evaluated_answer(client, store)
        response = client.get(f"/api/sessions/{session_id}/exercises")
        assert response.status_code == 200
        assert any(
            item["exercise_id"] == "exercise.backend.rollback_invariant_test"
            for item in response.json()["recommendations"]
        )


def test_i06_shared_exercise_keeps_each_gap_available_for_practice(tmp_path: Path) -> None:
    store = InMemoryRepositoryStore()
    app = _app(tmp_path, store)
    with TestClient(app) as client:
        session_id, answer_ref, _ = _evaluated_answer(
            client, store, additional_unmet_types=("invariant_preservation",)
        )
        response = client.get(f"/api/sessions/{session_id}/exercises")
        assert response.status_code == 200
        shared = [
            item for item in response.json()["recommendations"]
            if item["exercise_id"] == "exercise.backend.rollback_invariant_test"
        ]
        assert {item["matched_gap"]["criterion_id"] for item in shared} == {
            "c03.atomicity",
            "c03.concurrent_tests",
        }
        for item in shared:
            practice = client.post(
                f"/api/sessions/{session_id}/answers/{answer_ref.id}/practice",
                json={
                    "answer_revision": answer_ref.revision,
                    "criterion_id": item["matched_gap"]["criterion_id"],
                    "exercise_id": item["exercise_id"],
                },
            )
            assert practice.status_code == 201
            assert practice.json()["progress"]["total_questions"] == 1


def test_i06_detail_uses_requested_reviewed_version(tmp_path: Path) -> None:
    store = InMemoryRepositoryStore()
    app = _app(tmp_path, store)
    exercise_ref = next(
        item.ref for item in store.list_approved_exercises()
        if item.id == "exercise.backend.rollback_invariant_test"
    )
    exercise = store.get_exercise(exercise_ref)
    assert exercise is not None
    store.save_exercise(replace(exercise, version=2, title="Revised rollback exercise"))
    store.save_exercise(replace(exercise, version=3, review=ReviewMetadata()))
    with TestClient(app) as client:
        old = client.get(f"/api/exercises/{exercise.id}?version=1")
        current = client.get(f"/api/exercises/{exercise.id}")
        draft = client.get(f"/api/exercises/{exercise.id}?version=3")
        assert old.status_code == current.status_code == 200
        assert old.json()["version"] == 1
        assert current.json()["version"] == 2
        assert current.json()["title"] == "Revised rollback exercise"
        assert draft.status_code == 404
