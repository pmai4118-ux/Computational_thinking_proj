"""Next-session personalization uses only completed, evidence-backed gaps."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from source.Model.evaluation import CriterionCheck, CriterionStatus, EvaluationResult, EvaluationStatus, Evidence
from source.Model.ids import EvaluationId, QuestionId, RubricId, VersionedRef
from source.Model.interview import EvaluationTiming
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.service.interview_service import InterviewService
from source.service.seed_loader import load_seed_catalog_into_repository


def test_unseen_question_matching_prior_confirmed_gap_beats_unrelated_variant(tmp_path: Path) -> None:
    store = SQLiteRepositoryStore(tmp_path / "adaptive.sqlite3")
    load_seed_catalog_into_repository(store)
    service = InterviewService(content_repo=store, session_repo=store, evaluation_repo=store)
    first = service.open_session(owner_token_hash="owner-adaptive", evaluation_timing=EvaluationTiming.AFTER_SESSION)
    selected = store.get_question(first.session.question_refs[0])
    assert selected is not None
    answers = []
    for index, q_ref in enumerate(first.session.question_refs):
        answer = service.submit_answer(
            session_id=first.session.id,
            owner_token_hash="owner-adaptive",
            question_ref=q_ref,
            text=(
                "Em chưa giải thích được và chưa nêu kiểm thử."
                if index == 0
                else f"Câu trả lời thử nghiệm số {index}."
            ),
            client_submission_id=f"adaptive-{index}",
        ).answer
        answers.append(answer)
        service.advance_question(
            session_id=first.session.id,
            owner_token_hash="owner-adaptive",
            from_question_index=index,
        )
    answer = answers[0]
    rubric = store.get_rubric(selected.rubric_ref)
    assert rubric is not None
    store.save_evaluation(EvaluationResult(
        id=EvaluationId("eval.adaptive.first"),
        version=1,
        status=EvaluationStatus.COMPLETED,
        answer_ref=answer.ref,
        question_ref=selected.ref,
        rubric_ref=selected.rubric_ref,
        criterion_checks=tuple(CriterionCheck(
            criterion_id=criterion.id,
            status=CriterionStatus.UNMET if index == 0 else CriterionStatus.MET,
            score=0 if index == 0 else criterion.max_score,
            evidence=(Evidence(answer_ref=answer.ref, observation="Không thấy đủ nội dung yêu cầu."),),
            explanation="Chưa đáp ứng tiêu chí.",
        ) for index, criterion in enumerate(rubric.criteria)),
        total_score=sum(criterion.max_score for criterion in rubric.criteria[1:]),
        maximum_score=rubric.maximum_score,
        evaluated_at=datetime.now(UTC),
    ))

    # Add an unseen candidate whose ID sorts first but whose rubric does not
    # cover any of the confirmed gap types. The other seed variant does cover them.
    unrelated_rubric = replace(
        rubric,
        id=RubricId("rubric.test.unrelated"),
        criteria=tuple(replace(criterion, criterion_type="test_design") for criterion in rubric.criteria),
    )
    store.save_rubric(unrelated_rubric)
    unrelated = replace(
        selected,
        id=QuestionId("prog.a.unrelated"),
        rubric_ref=VersionedRef(unrelated_rubric.id, unrelated_rubric.version),
    )
    store.save_question(unrelated)

    second = service.open_session(owner_token_hash="owner-adaptive")
    selected_next = store.get_question(second.session.question_refs[0])
    assert selected_next is not None
    assert selected_next.id != selected.id
    assert selected_next.id != unrelated.id
    assert selected_next.id in {
        question.id for question in store.list_approved_questions(
            role="backend_developer", level="intern_fresher", language="vi"
        ) if question.category == "programming_knowledge"
    }
