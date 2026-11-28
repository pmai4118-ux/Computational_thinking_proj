"""Controller and REST endpoints for multi-branch AI-assisted Decision Replay (X02/X03)."""

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
from source.Model.decision_replay import ReplayCaseCatalogItem, ReplayTreeNode
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId, SessionId
from source.service.decision_replay_service import (
    AnswerReplayAvailability,
    DecisionReplayError,
    DecisionReplayService,
    EligibleAnswerReplay,
    InvalidReplayChoiceError,
    MAX_CUSTOM_PROPOSAL_LENGTH,
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
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError


class SelectReplayNodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)


class ChooseReplayOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)
    option_id: str = Field(min_length=1)


class RewindReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)


class CustomReplayBranchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    parent_node_id: str = Field(min_length=1)
    proposal_text: str = Field(min_length=1, max_length=MAX_CUSTOM_PROPOSAL_LENGTH)


class ReplayTraceStepDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor: str
    event: str
    state_after: str | None = None
    time_label: str | None = None


class ReplayInvariantDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    status: str
    detail: str
    category: str = "safety"


class ReplayOptionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    option_id: str
    label: str
    action_summary: str
    target_node_id: str


class ReplayNodeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    parent_id: str | None = None
    branch_label: str
    depth: int
    origin: str
    answer_alignment: str
    title: str
    situation: str
    consequence_summary: str
    system_impact: str
    tradeoff_note: str
    answer_quote: str | None = None
    answer_quote_start: int | None = None
    answer_quote_end: int | None = None
    assumptions_used: tuple[str, ...] = ()
    state_delta: str = ""
    trace_steps: tuple[ReplayTraceStepDTO, ...] = ()
    is_terminal: bool = False
    invariants: tuple[ReplayInvariantDTO, ...] = ()
    comparison_note: str | None = None
    options: tuple[ReplayOptionDTO, ...] = ()
    user_proposal: str | None = None


class ReplayRunDetailDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    question_id: str
    question_version: int
    title: str
    summary: str
    question_prompt: str | None = None
    question_code: str | None = None
    question_code_language: str | None = None
    question_constraints: tuple[str, ...] = ()
    question_source_id: str | None = None
    question_assumptions: tuple[str, ...] = ()
    root_node_id: str
    active_node_id: str
    active_path_ids: tuple[str, ...] = ()
    visited_node_ids: tuple[str, ...] = ()
    nodes: tuple[ReplayNodeDTO, ...] = ()
    linked_session_id: str | None = None
    linked_answer_ref: AnswerRevisionRefDTO | None = None
    linked_answer_text: str | None = None
    linked_total_score: int | None = None
    linked_maximum_score: int | None = None
    linked_evaluation_status: str | None = None
    custom_branches_used: int = 0
    custom_branch_limit: int = 2
    prompt_version: str = "decision_replay/v1"
    model_id: str | None = None
    demo_mode_label: str | None = None
    generation_status: str = "ready"
    generation_error: str | None = None
    created_at: datetime
    updated_at: datetime


class EligibleAnswerReplayDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    session_state: str
    answered_count: int
    total_questions: int
    session_completed: bool
    eligible: bool
    lock_reason: str | None = None
    answer_ref: AnswerRevisionRefDTO
    question_id: str
    question_version: int
    question_title: str
    answer_excerpt: str
    evaluation_status: str
    total_score: int | None = None
    maximum_score: int | None = None
    existing_run_id: str | None = None
    explored_nodes_count: int = 0
    custom_branches_used: int = 0
    submitted_at: datetime


class ReplayCaseCatalogItemDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: str
    question_version: int
    title: str
    summary: str
    related_skill_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    core_invariants: tuple[str, ...] = ()
    source_id: str


class ReplayHubDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    eligible_answers: tuple[EligibleAnswerReplayDTO, ...] = ()
    recent_runs: tuple[ReplayRunDetailDTO, ...] = ()
    cases: tuple[ReplayCaseCatalogItemDTO, ...] = ()


class AnswerReplayAvailabilityDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    eligible_now: bool = False
    question_id: str | None = None
    question_title: str | None = None
    existing_run_id: str | None = None
    reason: str | None = None


class DecisionReplayController:
    """Coordinates multi-branch Decision Replay endpoints without direct DB/provider logic."""

    def __init__(
        self,
        service: DecisionReplayService,
        *,
        interview_controller: InterviewController | None = None,
    ) -> None:
        self._service = service
        self._interview_controller = interview_controller

    @staticmethod
    def _case_dto(item: ReplayCaseCatalogItem) -> ReplayCaseCatalogItemDTO:
        return ReplayCaseCatalogItemDTO(
            question_id=str(item.question_id),
            question_version=item.question_version,
            title=item.title,
            summary=item.summary,
            related_skill_ids=tuple(str(s) for s in item.related_skill_ids),
            assumptions=item.assumptions,
            core_invariants=item.core_invariants,
            source_id=str(item.source_id),
        )

    @staticmethod
    def _eligible_dto(item: EligibleAnswerReplay) -> EligibleAnswerReplayDTO:
        return EligibleAnswerReplayDTO(
            session_id=str(item.session_id),
            session_state=item.session_state,
            answered_count=item.answered_count,
            total_questions=item.total_questions,
            session_completed=item.session_completed,
            eligible=item.eligible,
            lock_reason=item.lock_reason,
            answer_ref=AnswerRevisionRefDTO(
                id=item.answer_ref.id,
                revision=item.answer_ref.revision,
            ),
            question_id=str(item.question_id),
            question_version=item.question_version,
            question_title=item.question_title,
            answer_excerpt=item.answer_excerpt,
            evaluation_status=item.evaluation_status,
            total_score=item.total_score,
            maximum_score=item.maximum_score,
            existing_run_id=item.existing_run_id,
            explored_nodes_count=item.explored_nodes_count,
            custom_branches_used=item.custom_branches_used,
            submitted_at=item.submitted_at,
        )

    @staticmethod
    def _node_dto(node: ReplayTreeNode) -> ReplayNodeDTO:
        return ReplayNodeDTO(
            id=node.id,
            parent_id=node.parent_id,
            branch_label=node.branch_label,
            depth=node.depth,
            origin=node.origin,
            answer_alignment=node.answer_alignment,
            title=node.title,
            situation=node.situation,
            consequence_summary=node.consequence_summary,
            system_impact=node.system_impact,
            tradeoff_note=node.tradeoff_note,
            answer_quote=node.answer_quote,
            answer_quote_start=node.answer_quote_start,
            answer_quote_end=node.answer_quote_end,
            assumptions_used=node.assumptions_used,
            state_delta=node.state_delta,
            trace_steps=tuple(
                ReplayTraceStepDTO(
                    actor=s.actor,
                    event=s.event,
                    state_after=s.state_after,
                    time_label=s.time_label,
                )
                for s in node.trace_steps
            ),
            is_terminal=node.is_terminal,
            invariants=tuple(
                ReplayInvariantDTO(
                    name=inv.name,
                    status=inv.status,
                    detail=inv.detail,
                    category=inv.category,
                )
                for inv in node.invariants
            ),
            comparison_note=node.comparison_note,
            options=tuple(
                ReplayOptionDTO(
                    option_id=o.option_id,
                    label=o.label,
                    action_summary=o.action_summary,
                    target_node_id=o.target_node_id,
                )
                for o in node.options
            ),
            user_proposal=node.user_proposal,
        )

    @classmethod
    def _context_to_dto(cls, ctx: ReplayRunContext) -> ReplayRunDetailDTO:
        run = ctx.run
        question = ctx.question
        return ReplayRunDetailDTO(
            run_id=run.id,
            question_id=str(run.question_id),
            question_version=run.question_version,
            title=run.title,
            summary=run.summary,
            question_prompt=question.prompt if question is not None else None,
            question_code=question.code if question is not None else None,
            question_code_language=question.code_language if question is not None else None,
            question_constraints=question.constraints if question is not None else (),
            question_source_id=str(question.source_id) if question is not None else None,
            question_assumptions=(
                question.replay_grounding.environment_assumptions
                if question is not None and question.replay_grounding is not None
                else ()
            ),
            root_node_id=run.root_node_id,
            active_node_id=run.active_node_id,
            active_path_ids=ctx.active_path_ids,
            visited_node_ids=run.visited_node_ids,
            nodes=tuple(cls._node_dto(node) for node in run.nodes),
            linked_session_id=str(run.linked_session_id) if run.linked_session_id else None,
            linked_answer_ref=(
                AnswerRevisionRefDTO(
                    id=run.linked_answer_ref.id,
                    revision=run.linked_answer_ref.revision,
                )
                if run.linked_answer_ref is not None
                else None
            ),
            linked_answer_text=ctx.linked_answer_text,
            linked_total_score=ctx.linked_total_score,
            linked_maximum_score=ctx.linked_maximum_score,
            linked_evaluation_status=ctx.linked_evaluation_status,
            custom_branches_used=run.custom_branches_used,
            custom_branch_limit=run.custom_branch_limit,
            prompt_version=run.prompt_version,
            model_id=run.model_id,
            demo_mode_label=run.demo_mode_label,
            generation_status=run.generation_status,
            generation_error=run.generation_error,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _raise_provider_error(error: ProviderFailureError) -> None:
        if error.code is ProviderErrorKind.TIMEOUT:
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            code = ErrorCode.PROVIDER_TIMEOUT
        elif error.code is ProviderErrorKind.QUOTA:
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
            code = ErrorCode.PROVIDER_QUOTA_EXCEEDED
        elif error.code is ProviderErrorKind.CONFIG:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            code = ErrorCode.PROVIDER_CONFIG_ERROR
        elif error.code is ProviderErrorKind.INVALID_OUTPUT:
            status_code = status.HTTP_502_BAD_GATEWAY
            code = ErrorCode.PROVIDER_OUTPUT_INVALID
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
            code = ErrorCode.PROVIDER_NETWORK_ERROR
        raise ApiControllerError(
            status_code,
            ApiErrorResponse(
                error_code=code,
                message=str(error),
                retryable=error.retryable,
                recovery_action=(
                    "Bài trả lời gốc và các nhánh đã mở vẫn được giữ nguyên; bạn có thể thử lại."
                ),
            ),
        ) from error

    def get_hub(self, *, owner_token: str | None) -> ReplayHubDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        eligible = (
            tuple(
                self._eligible_dto(item)
                for item in self._service.list_eligible_answers_for_owner(
                    owner_token_hash=token_hash
                )
            )
            if token_hash
            else ()
        )
        recent = (
            tuple(
                self._context_to_dto(ctx)
                for ctx in self._service.list_owner_runs(owner_token_hash=token_hash)
            )
            if token_hash
            else ()
        )
        cases = tuple(self._case_dto(item) for item in self._service.list_catalog_cases())
        return ReplayHubDTO(
            eligible_answers=eligible,
            recent_runs=recent,
            cases=cases,
        )

    def inspect_answer_replay(
        self,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        *,
        owner_token: str | None,
    ) -> AnswerReplayAvailabilityDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            avail: AnswerReplayAvailability = self._service.inspect_answer_replay(
                session_id=session_id,
                answer_ref=answer_ref,
                owner_token_hash=token_hash,
            )
        except SessionNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.SESSION_NOT_FOUND, message=str(error)),
            ) from error
        except SessionForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(error_code=ErrorCode.SESSION_FORBIDDEN, message=str(error)),
            ) from error
        except SessionExpiredError as error:
            raise ApiControllerError(
                status.HTTP_410_GONE,
                ApiErrorResponse(error_code=ErrorCode.SESSION_EXPIRED, message=str(error)),
            ) from error
        except ScenarioNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.INVALID_INPUT, message=str(error)),
            ) from error
        return AnswerReplayAvailabilityDTO(
            available=avail.available,
            eligible_now=avail.eligible_now,
            question_id=str(avail.question_id) if avail.question_id else None,
            question_title=avail.question_title,
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
        async_generate: bool = False,
    ) -> ReplayRunDetailDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.start_run_for_answer(
                session_id=session_id,
                answer_ref=answer_ref,
                owner_token_hash=token_hash,
                reuse_existing=reuse_existing,
                async_generate=async_generate,
            )
        except SessionNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.SESSION_NOT_FOUND, message=str(error)),
            ) from error
        except SessionForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(error_code=ErrorCode.SESSION_FORBIDDEN, message=str(error)),
            ) from error
        except SessionExpiredError as error:
            raise ApiControllerError(
                status.HTTP_410_GONE,
                ApiErrorResponse(error_code=ErrorCode.SESSION_EXPIRED, message=str(error)),
            ) from error
        except ScenarioNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.INVALID_INPUT, message=str(error)),
            ) from error
        except ProviderFailureError as error:
            self._raise_provider_error(error)
        except DecisionReplayError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_STATE_TRANSITION,
                    message=str(error),
                    recovery_action="Hoàn tất đủ toàn bộ câu hỏi của phiên rồi mở lại Decision Replay.",
                ),
            ) from error
        return self._context_to_dto(ctx)

    def start_standalone_run(
        self,
        question_id: str,
        *,
        owner_token: str,
        async_generate: bool = False,
    ) -> ReplayRunDetailDTO:
        try:
            ctx = self._service.start_standalone_run(
                question_id=question_id,
                owner_token_hash=hash_owner_token(owner_token),
                async_generate=async_generate,
            )
        except ScenarioNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    recovery_action="Chọn một tình huống kỹ thuật hợp lệ từ trang Decision Replay.",
                ),
            ) from error
        except ProviderFailureError as error:
            self._raise_provider_error(error)
        except DecisionReplayError as error:
            raise ApiControllerError(
                status.HTTP_400_BAD_REQUEST,
                ApiErrorResponse(error_code=ErrorCode.INVALID_INPUT, message=str(error)),
            ) from error
        return self._context_to_dto(ctx)

    def retry_generation(
        self,
        run_id: str,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.retry_generation(run_id=run_id, owner_token_hash=token_hash)
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.SESSION_NOT_FOUND, message=str(error)),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(error_code=ErrorCode.SESSION_FORBIDDEN, message=str(error)),
            ) from error
        except ScenarioNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.INVALID_INPUT, message=str(error)),
            ) from error
        return self._context_to_dto(ctx)

    def get_run(self, run_id: str, *, owner_token: str | None) -> ReplayRunDetailDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.get_owned_run(run_id=run_id, owner_token_hash=token_hash)
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message=str(error),
                    recovery_action="Mở lại từ trung tâm Decision Replay.",
                ),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message=str(error),
                    recovery_action="Mở Decision Replay trên chính trình duyệt đã tạo phiên.",
                ),
            ) from error
        return self._context_to_dto(ctx)

    def select_node(
        self,
        run_id: str,
        payload: SelectReplayNodeRequest,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.select_node(
                run_id=run_id,
                owner_token_hash=token_hash,
                node_id=payload.node_id,
            )
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.SESSION_NOT_FOUND, message=str(error)),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(error_code=ErrorCode.SESSION_FORBIDDEN, message=str(error)),
            ) from error
        except InvalidReplayChoiceError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(error_code=ErrorCode.INVALID_STATE_TRANSITION, message=str(error)),
            ) from error
        return self._context_to_dto(ctx)

    def choose(
        self,
        run_id: str,
        payload: ChooseReplayOptionRequest,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.choose_option(
                run_id=run_id,
                owner_token_hash=token_hash,
                node_id=payload.node_id,
                option_id=payload.option_id,
            )
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.SESSION_NOT_FOUND, message=str(error)),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(error_code=ErrorCode.SESSION_FORBIDDEN, message=str(error)),
            ) from error
        except InvalidReplayChoiceError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(error_code=ErrorCode.INVALID_STATE_TRANSITION, message=str(error)),
            ) from error
        return self._context_to_dto(ctx)

    def rewind(
        self,
        run_id: str,
        payload: RewindReplayRequest,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.rewind_to_node(
                run_id=run_id,
                owner_token_hash=token_hash,
                node_id=payload.node_id,
            )
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.SESSION_NOT_FOUND, message=str(error)),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(error_code=ErrorCode.SESSION_FORBIDDEN, message=str(error)),
            ) from error
        except InvalidReplayChoiceError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(error_code=ErrorCode.INVALID_STATE_TRANSITION, message=str(error)),
            ) from error
        return self._context_to_dto(ctx)

    def add_custom_branch(
        self,
        run_id: str,
        payload: CustomReplayBranchRequest,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        token_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            ctx = self._service.add_custom_branch(
                run_id=run_id,
                owner_token_hash=token_hash,
                parent_node_id=payload.parent_node_id,
                proposal_text=payload.proposal_text,
            )
        except ReplayRunNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.SESSION_NOT_FOUND, message=str(error)),
            ) from error
        except ReplayRunForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(error_code=ErrorCode.SESSION_FORBIDDEN, message=str(error)),
            ) from error
        except ProviderFailureError as error:
            self._raise_provider_error(error)
        except (InvalidReplayChoiceError, DecisionReplayError) as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(error_code=ErrorCode.INVALID_STATE_TRANSITION, message=str(error)),
            ) from error
        return self._context_to_dto(ctx)


def build_decision_replay_router(controller: DecisionReplayController) -> APIRouter:
    router = APIRouter(tags=["decision-replay"])

    @router.get("/api/replays", response_model=ReplayHubDTO)
    def get_replay_hub(request: Request) -> ReplayHubDTO:
        return controller.get_hub(owner_token=request.cookies.get(OWNER_COOKIE_NAME))

    @router.post(
        "/api/replays/cases/{question_id}/runs",
        response_model=ReplayRunDetailDTO,
        status_code=status.HTTP_201_CREATED,
    )
    def start_standalone_replay(
        question_id: str,
        request: Request,
        response: Response,
        async_generate: bool = Query(default=False),
    ) -> ReplayRunDetailDTO:
        token, created = ensure_owner_cookie_token(request.cookies.get(OWNER_COOKIE_NAME))
        if created:
            apply_owner_cookie(response, token)
        return controller.start_standalone_run(
            question_id, owner_token=token, async_generate=async_generate
        )

    @router.get("/api/replays/runs/{run_id}", response_model=ReplayRunDetailDTO)
    def get_run(run_id: str, request: Request) -> ReplayRunDetailDTO:
        return controller.get_run(run_id, owner_token=request.cookies.get(OWNER_COOKIE_NAME))

    @router.post("/api/replays/runs/{run_id}/retry-generation", response_model=ReplayRunDetailDTO)
    def retry_generation(run_id: str, request: Request) -> ReplayRunDetailDTO:
        return controller.retry_generation(
            run_id, owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

    @router.post("/api/replays/runs/{run_id}/select", response_model=ReplayRunDetailDTO)
    def select_node(
        run_id: str,
        payload: SelectReplayNodeRequest,
        request: Request,
    ) -> ReplayRunDetailDTO:
        return controller.select_node(
            run_id, payload, owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

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

    @router.post("/api/replays/runs/{run_id}/custom-branch", response_model=ReplayRunDetailDTO)
    def create_custom_branch(
        run_id: str,
        payload: CustomReplayBranchRequest,
        request: Request,
    ) -> ReplayRunDetailDTO:
        return controller.add_custom_branch(
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
        async_generate: bool = Query(default=False),
    ) -> ReplayRunDetailDTO:
        return controller.start_run_for_answer(
            SessionId(session_id),
            AnswerRevisionRef(AnswerId(answer_id), revision),
            owner_token=request.cookies.get(OWNER_COOKIE_NAME),
            reuse_existing=reuse_existing,
            async_generate=async_generate,
        )

    return router


__all__ = [
    "AnswerReplayAvailabilityDTO",
    "ChooseReplayOptionRequest",
    "CustomReplayBranchRequest",
    "DecisionReplayController",
    "EligibleAnswerReplayDTO",
    "ReplayCaseCatalogItemDTO",
    "ReplayHubDTO",
    "ReplayInvariantDTO",
    "ReplayNodeDTO",
    "ReplayOptionDTO",
    "ReplayRunDetailDTO",
    "ReplayTraceStepDTO",
    "RewindReplayRequest",
    "SelectReplayNodeRequest",
    "build_decision_replay_router",
]
