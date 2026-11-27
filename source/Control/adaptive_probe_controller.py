"""Controller and REST endpoints for bounded adaptive follow-up probing (X04/X05)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from source.Control.interview_controller import (
    ApiControllerError,
    InterviewController,
    OWNER_COOKIE_NAME,
    hash_owner_token,
)
from source.Control.schemas import AnswerRevisionRefDTO, ApiErrorResponse, ErrorCode
from source.Model.adaptive_probe import FollowUpProbe, ProbeStatus, ProbeTriggerKind
from source.Model.evaluation import AnswerRevisionRef, CriterionStatus
from source.Model.ids import AnswerId, CriterionId, SessionId
from source.service.adaptive_probe_service import (
    AdaptiveProbeError,
    AdaptiveProbePlan,
    AdaptiveProbeService,
    ProbeLimitReachedError,
    ProbeNotEligibleError,
)
from source.service.interview_service import (
    SessionExpiredError,
    SessionForbiddenError,
    SessionNotFoundError,
)


class SubmitFollowUpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_revision: int = Field(default=1, ge=1)
    criterion_id: CriterionId | None = None
    response_text: str = Field(min_length=1, max_length=5000)


class FollowUpProbeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    probe_id: str
    session_id: SessionId
    answer_ref: AnswerRevisionRefDTO
    criterion_id: CriterionId
    criterion_label: str
    trigger_kind: ProbeTriggerKind
    probe_prompt: str
    choice_reason: str
    status: ProbeStatus
    response_text: str | None = None
    outcome_status: CriterionStatus | None = None
    outcome_score: int | None = None
    outcome_max_score: int | None = None
    outcome_explanation: str | None = None
    outcome_quote: str | None = None
    created_at: datetime
    answered_at: datetime | None = None


class AdaptiveProbePlanDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SessionId
    answer_ref: AnswerRevisionRefDTO
    can_probe: bool
    stop_reason: str | None = None
    policy_summary: str
    answer_probes_used: int
    answer_probe_limit: int
    session_probes_used: int
    session_probe_limit: int
    recommended_criterion_id: CriterionId | None = None
    recommended_criterion_label: str | None = None
    trigger_kind: ProbeTriggerKind | None = None
    probe_prompt: str | None = None
    choice_reason: str | None = None
    alternate_variant_available: bool = False
    alternate_variant_id: str | None = None
    alternate_variant_note: str
    existing_probes: tuple[FollowUpProbeDTO, ...] = ()


class AdaptiveProbeController:
    def __init__(
        self,
        *,
        interview_controller: InterviewController,
        probe_service: AdaptiveProbeService,
    ) -> None:
        self._interview_controller = interview_controller
        self._probe_service = probe_service

    @staticmethod
    def _probe_to_dto(probe: FollowUpProbe) -> FollowUpProbeDTO:
        return FollowUpProbeDTO(
            probe_id=probe.id,
            session_id=probe.session_id,
            answer_ref=AnswerRevisionRefDTO(
                id=probe.answer_ref.id, revision=probe.answer_ref.revision
            ),
            criterion_id=probe.criterion_id,
            criterion_label=probe.criterion_label,
            trigger_kind=probe.trigger_kind,
            probe_prompt=probe.probe_prompt,
            choice_reason=probe.choice_reason,
            status=probe.status,
            response_text=probe.response_text,
            outcome_status=probe.outcome_status,
            outcome_score=probe.outcome_score,
            outcome_max_score=probe.outcome_max_score,
            outcome_explanation=probe.outcome_explanation,
            outcome_quote=probe.outcome_quote,
            created_at=probe.created_at,
            answered_at=probe.answered_at,
        )

    @classmethod
    def _plan_to_dto(cls, plan: AdaptiveProbePlan) -> AdaptiveProbePlanDTO:
        return AdaptiveProbePlanDTO(
            session_id=plan.session_id,
            answer_ref=AnswerRevisionRefDTO(
                id=plan.answer_ref.id, revision=plan.answer_ref.revision
            ),
            can_probe=plan.can_probe,
            stop_reason=plan.stop_reason,
            policy_summary=plan.policy_summary,
            answer_probes_used=plan.answer_probes_used,
            answer_probe_limit=plan.answer_probe_limit,
            session_probes_used=plan.session_probes_used,
            session_probe_limit=plan.session_probe_limit,
            recommended_criterion_id=plan.recommended_criterion_id,
            recommended_criterion_label=plan.recommended_criterion_label,
            trigger_kind=plan.trigger_kind,
            probe_prompt=plan.probe_prompt,
            choice_reason=plan.choice_reason,
            alternate_variant_available=plan.alternate_variant_available,
            alternate_variant_id=str(plan.alternate_variant_id) if plan.alternate_variant_id else None,
            alternate_variant_note=plan.alternate_variant_note,
            existing_probes=tuple(cls._probe_to_dto(item) for item in plan.existing_probes),
        )

    def get_plan(
        self,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        *,
        owner_token: str | None,
    ) -> AdaptiveProbePlanDTO:
        self._interview_controller.require_complete(session_id, owner_token=owner_token)
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            plan = self._probe_service.inspect_plan(
                session_id=session_id,
                answer_ref=answer_ref,
                owner_token_hash=owner_hash,
            )
        except (SessionNotFoundError, SessionForbiddenError, SessionExpiredError) as error:
            raise self._translate_error(error, session_id) from error
        except ProbeNotEligibleError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                ),
            ) from error
        return self._plan_to_dto(plan)

    def submit(
        self,
        session_id: SessionId,
        answer_id: AnswerId,
        payload: SubmitFollowUpRequest,
        *,
        owner_token: str | None,
    ) -> FollowUpProbeDTO:
        self._interview_controller.require_complete(session_id, owner_token=owner_token)
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        answer_ref = AnswerRevisionRef(answer_id, payload.answer_revision)
        try:
            probe = self._probe_service.submit_follow_up(
                session_id=session_id,
                answer_ref=answer_ref,
                owner_token_hash=owner_hash,
                response_text=payload.response_text,
                criterion_id=payload.criterion_id,
            )
        except (SessionNotFoundError, SessionForbiddenError, SessionExpiredError) as error:
            raise self._translate_error(error, session_id) from error
        except (ProbeLimitReachedError, ProbeNotEligibleError) as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_STATE_TRANSITION,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                ),
            ) from error
        except AdaptiveProbeError as error:
            raise ApiControllerError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                ),
            ) from error
        return self._probe_to_dto(probe)

    @staticmethod
    def _translate_error(error: Exception, session_id: SessionId) -> ApiControllerError:
        if isinstance(error, SessionNotFoundError):
            return ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="Không tìm thấy phiên luyện tập yêu cầu.",
                    retryable=False,
                    session_id=session_id,
                ),
            )
        if isinstance(error, SessionForbiddenError):
            return ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message="Phiên luyện tập này không thuộc trình duyệt hiện tại.",
                    retryable=False,
                    session_id=session_id,
                ),
            )
        return ApiControllerError(
            status.HTTP_410_GONE,
            ApiErrorResponse(
                error_code=ErrorCode.SESSION_EXPIRED,
                message="Phiên luyện tập đã hết hạn khả dụng.",
                retryable=False,
                session_id=session_id,
            ),
        )


def build_adaptive_probe_router(controller: AdaptiveProbeController) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["adaptive-probing"])

    @router.get(
        "/{session_id}/answers/{answer_id}/follow-up",
        response_model=AdaptiveProbePlanDTO,
    )
    def get_follow_up_plan(
        session_id: str,
        answer_id: str,
        request: Request,
        revision: int = Query(default=1, ge=1),
    ) -> AdaptiveProbePlanDTO:
        return controller.get_plan(
            SessionId(session_id),
            AnswerRevisionRef(AnswerId(answer_id), revision),
            owner_token=request.cookies.get(OWNER_COOKIE_NAME),
        )

    @router.post(
        "/{session_id}/answers/{answer_id}/follow-up",
        response_model=FollowUpProbeDTO,
        status_code=status.HTTP_201_CREATED,
    )
    def submit_follow_up(
        session_id: str,
        answer_id: str,
        payload: SubmitFollowUpRequest,
        request: Request,
    ) -> FollowUpProbeDTO:
        return controller.submit(
            SessionId(session_id),
            AnswerId(answer_id),
            payload,
            owner_token=request.cookies.get(OWNER_COOKIE_NAME),
        )

    return router


__all__ = [
    "AdaptiveProbeController",
    "AdaptiveProbePlanDTO",
    "FollowUpProbeDTO",
    "SubmitFollowUpRequest",
    "build_adaptive_probe_router",
]
