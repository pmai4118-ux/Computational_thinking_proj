"""Read the saved assessment and coverage for an owned interview session."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request

from source.Control.interview_controller import (
    InterviewController,
    OWNER_COOKIE_NAME,
    hash_owner_token,
)
from source.Control.schemas import (
    AnswerRevisionRefDTO,
    EndSessionRequest,
    ObservedGapDTO,
    QuestionOutcomeSummaryDTO,
    SessionSummaryDTO,
    SessionOverviewDTO,
    SessionReportDTO,
    VersionedRefDTO,
)
from source.Model.ids import SessionId
from source.service.recommendation_service import RecommendationService
from source.service.session_report_service import SessionReportService


class SessionSummaryController:
    """Coordinate session summary actions and map Service records into DTOs."""

    def __init__(
        self,
        *,
        interview_controller: InterviewController,
        recommendation_service: RecommendationService,
        report_service: SessionReportService,
    ) -> None:
        self._interview_controller = interview_controller
        self._recommendation_service = recommendation_service
        self._report_service = report_service

    def get_summary(self, session_id: SessionId, *, owner_token: str | None) -> SessionSummaryDTO:
        # Delegate missing, foreign, and expired session checks to InterviewController.
        view = self._interview_controller.require_complete(session_id, owner_token=owner_token)
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        report = self._recommendation_service.summarize_session(
            session_id=session_id,
            owner_token_hash=owner_hash,
        )
        three_part = asdict(self._report_service.build(
            session_id=session_id, owner_token_hash=owner_hash,
        ))
        overview = SessionOverviewDTO.model_validate({
            key: three_part[key] for key in (
                "scope_note", "answered_count", "evaluated_count", "total_questions",
                "axes", "strengths", "gaps",
            )
        })
        return SessionSummaryDTO(
            session_id=report.session_id,
            state=view.state,
            demo_mode_label=view.demo_mode_label,
            completed_question_count=report.completed_question_count,
            total_question_count=report.total_question_count,
            unanswered_categories=report.unanswered_categories,
            unresolved_categories=report.unresolved_categories,
            outcomes=tuple(
                QuestionOutcomeSummaryDTO(
                    slot_index=item.slot_index,
                    category=item.category,
                    skill_id=item.skill_id,
                    question_ref=VersionedRefDTO(
                        id=item.question_ref.id, version=item.question_ref.version
                    ),
                    question_prompt=item.question_prompt,
                    question_code=item.question_code,
                    answer_text=item.answer_text,
                    failure_message=item.failure_message,
                    retryable=item.retryable,
                    answer_ref=(
                        AnswerRevisionRefDTO(id=item.answer_ref.id, revision=item.answer_ref.revision)
                        if item.answer_ref is not None
                        else None
                    ),
                    evaluation_id=item.evaluation_id,
                    evaluation_status=item.evaluation_status,
                    total_score=item.total_score,
                    maximum_score=item.maximum_score,
                    unresolved_criteria_count=item.unresolved_criteria_count,
                    confirmed_gap_criterion_ids=item.confirmed_gap_criterion_ids,
                )
                for item in report.outcomes
            ),
            observed_gaps=tuple(
                ObservedGapDTO(
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
                )
                for gap in report.observed_gaps
            ),
            report=SessionReportDTO(
                session_id=session_id,
                status=three_part["status"],
                overview=overview,
                details=three_part["details"],
                proposals=three_part["proposals"],
                message=three_part["message"],
            ),
        )

    def end_and_summarize(
        self, session_id: SessionId, *, owner_token: str | None, reason: str
    ) -> SessionSummaryDTO:
        self._interview_controller.require_complete(session_id, owner_token=owner_token)
        self._interview_controller.end_session(
            session_id, owner_token=owner_token, reason=reason
        )
        return self.get_summary(session_id, owner_token=owner_token)


def build_session_summary_router(controller: SessionSummaryController) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    @router.get("/{session_id}/summary", response_model=SessionSummaryDTO)
    def get_summary(session_id: str, request: Request) -> SessionSummaryDTO:
        return controller.get_summary(
            SessionId(session_id), owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

    @router.post("/{session_id}/end", response_model=SessionSummaryDTO)
    def end_session(
        session_id: str, payload: EndSessionRequest, request: Request
    ) -> SessionSummaryDTO:
        return controller.end_and_summarize(
            SessionId(session_id),
            owner_token=request.cookies.get(OWNER_COOKIE_NAME),
            reason=payload.reason,
        )

    return router


__all__ = ["SessionSummaryController", "build_session_summary_router"]
