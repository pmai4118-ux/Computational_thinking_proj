"""Read the saved assessment and coverage for an owned interview session."""

from __future__ import annotations

from fastapi import APIRouter, Request

from source.Control.interview_controller import InterviewController, OWNER_COOKIE_NAME
from source.Control.schemas import (
    AnswerRevisionRefDTO,
    ObservedGapDTO,
    QuestionOutcomeSummaryDTO,
    SessionSummaryDTO,
    VersionedRefDTO,
)
from source.Model.evaluation import CriterionStatus, EvaluationStatus
from source.Model.ids import SessionId
from source.Model.repositories.interfaces import ContentRepository, EvaluationRepository, SessionRepository
from source.service.interview_service import InterviewService
from source.service.recommendation_service import RecommendationService


class SessionSummaryController:
    """Build an evidence-based report without implying unanswered work is scored."""

    def __init__(
        self,
        *,
        interview_controller: InterviewController,
        interview_service: InterviewService,
        recommendation_service: RecommendationService,
        content_repo: ContentRepository,
        session_repo: SessionRepository,
        evaluation_repo: EvaluationRepository,
    ) -> None:
        self._interview_controller = interview_controller
        self._interview_service = interview_service
        self._recommendation_service = recommendation_service
        self._content_repo = content_repo
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo

    def get_summary(self, session_id: SessionId, *, owner_token: str | None) -> SessionSummaryDTO:
        # The existing controller maps missing, foreign and expired sessions to API errors.
        view = self._interview_controller.get_session(session_id, owner_token=owner_token)
        session = self._session_repo.get_session(session_id)
        assert session is not None
        blueprint = self._interview_service.find_blueprint(
            role=session.role, level=session.level, language=session.language
        )
        skills_by_category = {slot.category: slot.skill_id for slot in blueprint.slots}
        latest_answers = {}
        for answer in self._session_repo.list_answers_for_session(session_id):
            previous = latest_answers.get(answer.question_ref)
            if previous is None or answer.revision > previous.revision:
                latest_answers[answer.question_ref] = answer

        gaps = self._recommendation_service.confirmed_gaps(session)
        gap_ids_by_question = {}
        for gap in gaps:
            gap_ids_by_question.setdefault(gap.question_ref, []).append(gap.criterion_id)

        outcomes = []
        unanswered_categories = []
        unresolved_categories = []
        completed_count = 0
        for index, question_ref in enumerate(session.question_refs):
            question = self._content_repo.get_question(question_ref)
            if question is None:
                raise RuntimeError(f"Saved session references missing question {question_ref}.")
            answer = latest_answers.get(question_ref)
            if answer is None:
                unanswered_categories.append(question.category)
                continue
            evaluation = self._evaluation_repo.get_latest_evaluation_for_answer(answer.ref)
            if evaluation is not None and evaluation.status is EvaluationStatus.COMPLETED:
                completed_count += 1
            unresolved_count = 0
            if evaluation is not None:
                unresolved_count = sum(
                    check.status is CriterionStatus.INSUFFICIENT_EVIDENCE
                    for check in evaluation.criterion_checks
                )
                if unresolved_count:
                    unresolved_categories.append(question.category)
            outcomes.append(QuestionOutcomeSummaryDTO(
                slot_index=index,
                category=question.category,
                skill_id=skills_by_category.get(question.category, question.skill_ids[0]),
                question_ref=VersionedRefDTO(id=question_ref.id, version=question_ref.version),
                question_prompt=question.prompt,
                answer_ref=AnswerRevisionRefDTO(id=answer.id, revision=answer.revision),
                evaluation_id=evaluation.id if evaluation is not None else None,
                evaluation_status=evaluation.status.value if evaluation is not None else "pending",
                total_score=evaluation.total_score if evaluation is not None else None,
                maximum_score=evaluation.maximum_score if evaluation is not None else None,
                unresolved_criteria_count=unresolved_count,
                confirmed_gap_criterion_ids=tuple(gap_ids_by_question.get(question_ref, ())),
            ))

        return SessionSummaryDTO(
            session_id=session_id,
            state=view.state,
            demo_mode_label=view.demo_mode_label,
            completed_question_count=completed_count,
            total_question_count=len(session.question_refs),
            unanswered_categories=tuple(unanswered_categories),
            unresolved_categories=tuple(unresolved_categories),
            outcomes=tuple(outcomes),
            observed_gaps=tuple(ObservedGapDTO(
                skill_id=gap.skill_id,
                skill_label=gap.skill_label,
                question_ref=VersionedRefDTO(
                    id=gap.question_ref.id, version=gap.question_ref.version
                ),
                answer_ref=AnswerRevisionRefDTO(
                    id=gap.answer_ref.id, revision=gap.answer_ref.revision
                ),
                evaluation_id=gap.evaluation_id,
                criterion_id=gap.criterion_id,
                criterion_label=gap.criterion_label,
                reason=gap.reason,
            ) for gap in gaps),
        )


def build_session_summary_router(controller: SessionSummaryController) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    @router.get("/{session_id}/summary", response_model=SessionSummaryDTO)
    def get_summary(session_id: str, request: Request) -> SessionSummaryDTO:
        return controller.get_summary(
            SessionId(session_id), owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

    return router


__all__ = ["SessionSummaryController", "build_session_summary_router"]
