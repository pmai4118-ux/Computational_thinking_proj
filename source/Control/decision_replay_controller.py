"""Controller and REST endpoints for curated Decision Replay linked to answers + rewind (X02/X03)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from source.Control.interview_controller import (
    ApiControllerError,
    InterviewController,
    OWNER_COOKIE_NAME,
    apply_owner_cookie,
    ensure_owner_cookie_token,
    hash_owner_token,
)
from source.Control.schemas import AnswerRevisionRefDTO, ApiErrorResponse, ErrorCode
from source.Model.decision_replay import DecisionReplayScenario, ReplayCheckpoint
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId, SessionId
from source.service.decision_replay_service import (
    AnswerReplayAvailability,
    DecisionReplayError,
    DecisionReplayService,
    InvalidReplayChoiceError,
    ReplayCheckpointDiagnostic,
    ReplayRunContext,
    ReplayRunForbiddenError,
    ReplayRunNotFoundError,
    ScenarioNotFoundError,
)
from source.service.interview_service import (
    SessionExpiredError,
    SessionForbiddenError,
    SessionNotFoundError,
)


class StartReplayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    linked_session_id: SessionId | None = None
    reuse_existing: bool = True


class ChooseReplayOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: str = Field(min_length=1)
    option_id: str = Field(min_length=1)


class RewindReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: str = Field(min_length=1)


class ReplayOptionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    label: str
    action_summary: str


class ReplayCheckpointDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    criterion_id: str | None = None
    title: str
    situation: str
    question: str
    insufficient_evidence_note: str | None = None
    options: tuple[ReplayOptionDTO, ...] = ()


class ReplayCheckpointDiagnosticDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: str
    checkpoint_title: str
    criterion_id: str | None = None
    answer_verdict: str
    answer_score: int | None = None
    answer_max_score: int | None = None
    answer_explanation: str | None = None
    answer_quote: str | None = None
    diagnosis_note: str


class ReplayScenarioSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    version: int
    question_id: str | None = None
    title: str
    summary: str
    related_skill_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    checkpoint_count: int
    source_id: str


class ReplayStepDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_number: int
    checkpoint_id: str
    checkpoint_title: str
    option_id: str
    option_label: str
    consequence_summary: str
    system_impact: str
    tradeoff_note: str
    outcome_tag: str
    decided_at: datetime


class ReplayRunDetailDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    scenario: ReplayScenarioSummaryDTO
    completed: bool
    current_checkpoint: ReplayCheckpointDTO | None = None
    steps: tuple[ReplayStepDTO, ...] = ()
    recommended_steps_count: int
    risky_steps_count: int
    linked_session_id: str | None = None
    linked_answer_ref: AnswerRevisionRefDTO | None = None
    linked_answer_text: str | None = None
    linked_total_score: int | None = None
    linked_maximum_score: int | None = None
    linked_evaluation_status: str | None = None
    checkpoint_diagnostics: tuple[ReplayCheckpointDiagnosticDTO, ...] = ()
    created_at: datetime
    updated_at: datetime


class AnswerReplayAvailabilityDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    question_id: str | None = None
    scenario: ReplayScenarioSummaryDTO | None = None
    existing_run_id: str | None = None
    reason: str | None = None


class ReplayCatalogDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenarios: tuple[ReplayScenarioSummaryDTO, ...] = ()


class DecisionReplayController:
    def __init__(
        self,
        service: DecisionReplayService,
        interview_controller: InterviewController | None = None,
    ) -> None:
        self._service = service
        self._interview_controller = interview_controller

    @staticmethod
    def _scenario_summary(scenario: DecisionReplayScenario) -> ReplayScenarioSummaryDTO:
        return ReplayScenarioSummaryDTO(
            id=scenario.id,
            version=scenario.version,
            question_id=str(scenario.question_id) if scenario.question_id else None,
            title=scenario.title,
            summary=scenario.summary,
            related_skill_ids=tuple(str(s) for s in scenario.related_skill_ids),
            assumptions=scenario.assumptions,
            checkpoint_count=len(scenario.checkpoints),
            source_id=str(scenario.source_id),
        )

    @staticmethod
    def _checkpoint_dto(cp: ReplayCheckpoint) -> ReplayCheckpointDTO:
        return ReplayCheckpointDTO(
            id=cp.id,
            criterion_id=str(cp.criterion_id) if cp.criterion_id else None,
            title=cp.title,
            situation=cp.situation,
            question=cp.question,
            insufficient_evidence_note=cp.insufficient_evidence_note,
            options=tuple(
                ReplayOptionDTO(
                    id=opt.id,
                    label=opt.label,
                    action_summary=opt.action_summary,
                )
                for opt in cp.options
            ),
        )

    @staticmethod
    def _diag_dto(item: ReplayCheckpointDiagnostic) -> ReplayCheckpointDiagnosticDTO:
        return ReplayCheckpointDiagnosticDTO(
            checkpoint_id=item.checkpoint_id,
            checkpoint_title=item.checkpoint_title,
            criterion_id=str(item.criterion_id) if item.criterion_id else None,
            answer_verdict=item.answer_verdict,
            answer_score=item.answer_score,
            answer_max_score=item.answer_max_score,
            answer_explanation=item.answer_explanation,
            answer_quote=item.answer_quote,
            diagnosis_note=item.diagnosis_note,
        )

    @classmethod
    def _context_to_dto(cls, ctx: ReplayRunContext) -> ReplayRunDetailDTO:
        scenario, run = ctx.scenario, ctx.run
        current_cp = None
        if run.current_checkpoint_id is not None:
            matched = next(
                (cp for cp in scenario.checkpoints if cp.id == run.current_checkpoint_id),
                None,
            )
            if matched is not None:
                current_cp = cls._checkpoint_dto(matched)
        return ReplayRunDetailDTO(
            run_id=run.id,
            scenario=cls._scenario_summary(scenario),
            completed=run.completed,
            current_checkpoint=current_cp,
            steps=tuple(
                ReplayStepDTO(
                    step_number=step.step_number,
                    checkpoint_id=step.checkpoint_id,
                    checkpoint_title=step.checkpoint_title,
                    option_id=step.option_id,
                    option_label=step.option_label,
                    consequence_summary=step.consequence_summary,
                    system_impact=step.system_impact,
                    tradeoff_note=step.tradeoff_note,
                    outcome_tag=step.outcome_tag,
                    decided_at=step.decided_at,
                )
                for step in run.steps
            ),
            recommended_steps_count=sum(1 for s in run.steps if s.outcome_tag == "recommended"),
            risky_steps_count=sum(1 for s in run.steps if s.outcome_tag == "risky"),
            linked_session_id=str(run.linked_session_id) if run.linked_session_id else None,
            linked_answer_ref=(
                AnswerRevisionRefDTO(
                    id=run.linked_answer_ref.id, revision=run.linked_answer_ref.revision
                )
                if run.linked_answer_ref is not None
                else None
            ),
            linked_answer_text=ctx.linked_answer_text,
            linked_total_score=ctx.linked_total_score,
            linked_maximum_score=ctx.linked_maximum_score,
            linked_evaluation_status=ctx.linked_evaluation_status,
            checkpoint_diagnostics=tuple(cls._diag_dto(item) for item in ctx.checkpoint_diagnostics),
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    def list_scenarios(self) -> ReplayCatalogDTO:
        return ReplayCatalogDTO(
            scenarios=tuple(self._scenario_summary(s) for s in self._service.list_scenarios())
        )

    def inspect_answer_replay(
        self,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        *,
        owner_token: str | None,
    ) -> AnswerReplayAvailabilityDTO:
        if self._interview_controller is not None:
            self._interview_controller.require_complete(session_id, owner_token=owner_token)
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            avail: AnswerReplayAvailability = self._service.inspect_answer_replay(
                session_id=session_id,
                answer_ref=answer_ref,
                owner_token_hash=owner_hash,
            )
        except (SessionNotFoundError, SessionForbiddenError, SessionExpiredError) as error:
            raise self._translate_session_error(error, session_id) from error
        except ScenarioNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                ),
            ) from error
        return AnswerReplayAvailabilityDTO(
            available=avail.available,
            question_id=str(avail.question_id) if avail.question_id else None,
            scenario=self._scenario_summary(avail.scenario) if avail.scenario else None,
            existing_run_id=avail.existing_run_id,
            reason=avail.reason,
        )

    def start_run_for_answer(
        self,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        *,
        owner_token: str | None,
        reuse_existing: bool = True,
    ) -> ReplayRunDetailDTO:
        if self._interview_controller is not None:
            self._interview_controller.require_complete(session_id, owner_token=owner_token)
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.start_run_for_answer(
                session_id=session_id,
                answer_ref=answer_ref,
                owner_token_hash=owner_hash,
                reuse_existing=reuse_existing,
            )
        except (SessionNotFoundError, SessionForbiddenError, SessionExpiredError) as error:
            raise self._translate_session_error(error, session_id) from error
        except ScenarioNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                ),
            ) from error
        except DecisionReplayError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_STATE_TRANSITION,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                ),
            ) from error
        return self._context_to_dto(ctx)

    def start_run(
        self,
        scenario_id: str,
        *,
        owner_token: str,
        linked_session_id: SessionId | None = None,
    ) -> ReplayRunDetailDTO:
        try:
            ctx = self._service.start_run(
                scenario_id=scenario_id,
                owner_token_hash=hash_owner_token(owner_token),
                linked_session_id=linked_session_id,
            )
        except ScenarioNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    recovery_action="Chọn một kịch bản hợp lệ từ danh sách Decision Replay.",
                ),
            ) from error
        except DecisionReplayError as error:
            raise ApiControllerError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        return self._context_to_dto(ctx)

    def get_run(self, run_id: str, *, owner_token: str | None) -> ReplayRunDetailDTO:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.get_owned_run(run_id=run_id, owner_token_hash=owner_hash)
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        return self._context_to_dto(ctx)

    def choose(
        self,
        run_id: str,
        payload: ChooseReplayOptionRequest,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.choose_option(
                run_id=run_id,
                owner_token_hash=owner_hash,
                checkpoint_id=payload.checkpoint_id,
                option_id=payload.option_id,
            )
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        except InvalidReplayChoiceError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_STATE_TRANSITION,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        return self._context_to_dto(ctx)

    def rewind(
        self,
        run_id: str,
        payload: RewindReplayRequest,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.rewind_to_checkpoint(
                run_id=run_id,
                owner_token_hash=owner_hash,
                checkpoint_id=payload.checkpoint_id,
            )
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        except InvalidReplayChoiceError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_STATE_TRANSITION,
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        return self._context_to_dto(ctx)

    def list_runs_for_owner(self, *, owner_token: str | None) -> tuple[ReplayRunDetailDTO, ...]:
        if not owner_token:
            return ()
        contexts = self._service.list_owner_runs(owner_token_hash=hash_owner_token(owner_token))
        return tuple(self._context_to_dto(ctx) for ctx in contexts)

    @staticmethod
    def _translate_session_error(error: Exception, session_id: SessionId) -> ApiControllerError:
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


def build_decision_replay_router(controller: DecisionReplayController) -> APIRouter:
    router = APIRouter(tags=["decision-replay"])

    @router.get("/api/replays", response_model=ReplayCatalogDTO)
    def list_scenarios() -> ReplayCatalogDTO:
        return controller.list_scenarios()

    @router.post(
        "/api/replays/{scenario_id}/runs",
        response_model=ReplayRunDetailDTO,
        status_code=status.HTTP_201_CREATED,
    )
    def start_replay(
        scenario_id: str,
        request: Request,
        response: Response,
        payload: StartReplayRunRequest | None = None,
    ) -> ReplayRunDetailDTO:
        token, created = ensure_owner_cookie_token(request.cookies.get(OWNER_COOKIE_NAME))
        if created:
            apply_owner_cookie(response, token)
        return controller.start_run(
            scenario_id,
            owner_token=token,
            linked_session_id=payload.linked_session_id if payload else None,
        )

    @router.get("/api/replays/runs/{run_id}", response_model=ReplayRunDetailDTO)
    def get_run(run_id: str, request: Request) -> ReplayRunDetailDTO:
        return controller.get_run(run_id, owner_token=request.cookies.get(OWNER_COOKIE_NAME))

    @router.post("/api/replays/runs/{run_id}/choose", response_model=ReplayRunDetailDTO)
    def choose_option(
        run_id: str,
        payload: ChooseReplayOptionRequest,
        request: Request,
    ) -> ReplayRunDetailDTO:
        return controller.choose(
            run_id, payload, owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

    @router.post("/api/replays/runs/{run_id}/rewind", response_model=ReplayRunDetailDTO)
    def rewind_run(
        run_id: str,
        payload: RewindReplayRequest,
        request: Request,
    ) -> ReplayRunDetailDTO:
        return controller.rewind(
            run_id, payload, owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

    @router.get(
        "/api/sessions/{session_id}/answers/{answer_id}/replay",
        response_model=AnswerReplayAvailabilityDTO,
    )
    def get_answer_replay_availability(
        session_id: str,
        answer_id: str,
        request: Request,
        revision: int = Query(default=1, ge=1),
    ) -> AnswerReplayAvailabilityDTO:
        return controller.inspect_answer_replay(
            SessionId(session_id),
            AnswerRevisionRef(AnswerId(answer_id), revision),
            owner_token=request.cookies.get(OWNER_COOKIE_NAME),
        )

    @router.post(
        "/api/sessions/{session_id}/answers/{answer_id}/replay",
        response_model=ReplayRunDetailDTO,
        status_code=status.HTTP_201_CREATED,
    )
    def start_answer_replay(
        session_id: str,
        answer_id: str,
        request: Request,
        revision: int = Query(default=1, ge=1),
        reuse_existing: bool = Query(default=True),
    ) -> ReplayRunDetailDTO:
        return controller.start_run_for_answer(
            SessionId(session_id),
            AnswerRevisionRef(AnswerId(answer_id), revision),
            owner_token=request.cookies.get(OWNER_COOKIE_NAME),
            reuse_existing=reuse_existing,
        )

    return router


__all__ = [
    "AnswerReplayAvailabilityDTO",
    "ChooseReplayOptionRequest",
    "DecisionReplayController",
    "ReplayCatalogDTO",
    "ReplayCheckpointDiagnosticDTO",
    "ReplayRunDetailDTO",
    "RewindReplayRequest",
    "StartReplayRunRequest",
    "build_decision_replay_router",
]
