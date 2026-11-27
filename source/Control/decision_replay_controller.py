"""Controller and REST endpoints for curated Decision Replay traversal (X02/X03)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from source.Control.interview_controller import (
    ApiControllerError,
    OWNER_COOKIE_NAME,
    apply_owner_cookie,
    ensure_owner_cookie_token,
    hash_owner_token,
)
from source.Control.schemas import ApiErrorResponse, ErrorCode
from source.Model.decision_replay import (
    DecisionReplayScenario,
    ReplayCheckpoint,
    ReplayRun,
)
from source.Model.ids import SessionId
from source.service.decision_replay_service import (
    DecisionReplayError,
    DecisionReplayService,
    InvalidReplayChoiceError,
    ReplayRunForbiddenError,
    ReplayRunNotFoundError,
    ScenarioNotFoundError,
)


class StartReplayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    linked_session_id: SessionId | None = None


class ChooseReplayOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: str = Field(min_length=1)
    option_id: str = Field(min_length=1)


class ReplayOptionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    label: str
    action_summary: str


class ReplayCheckpointDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    situation: str
    question: str
    options: tuple[ReplayOptionDTO, ...] = ()


class ReplayScenarioSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    version: int
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
    created_at: datetime
    updated_at: datetime


class ReplayCatalogDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenarios: tuple[ReplayScenarioSummaryDTO, ...] = ()


class DecisionReplayController:
    def __init__(self, service: DecisionReplayService) -> None:
        self._service = service

    @staticmethod
    def _scenario_summary(scenario: DecisionReplayScenario) -> ReplayScenarioSummaryDTO:
        return ReplayScenarioSummaryDTO(
            id=scenario.id,
            version=scenario.version,
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
            title=cp.title,
            situation=cp.situation,
            question=cp.question,
            options=tuple(
                ReplayOptionDTO(
                    id=opt.id,
                    label=opt.label,
                    action_summary=opt.action_summary,
                )
                for opt in cp.options
            ),
        )

    @classmethod
    def _run_to_dto(cls, scenario: DecisionReplayScenario, run: ReplayRun) -> ReplayRunDetailDTO:
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
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    def list_scenarios(self) -> ReplayCatalogDTO:
        return ReplayCatalogDTO(
            scenarios=tuple(self._scenario_summary(s) for s in self._service.list_scenarios())
        )

    def start_run(
        self,
        scenario_id: str,
        *,
        owner_token: str,
        linked_session_id: SessionId | None = None,
    ) -> ReplayRunDetailDTO:
        try:
            scenario, run = self._service.start_run(
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
        return self._run_to_dto(scenario, run)

    def get_run(self, run_id: str, *, owner_token: str | None) -> ReplayRunDetailDTO:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            scenario, run = self._service.get_owned_run(
                run_id=run_id, owner_token_hash=owner_hash
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
        return self._run_to_dto(scenario, run)

    def choose(
        self,
        run_id: str,
        payload: ChooseReplayOptionRequest,
        *,
        owner_token: str | None,
    ) -> ReplayRunDetailDTO:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            scenario, run = self._service.choose_option(
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
        return self._run_to_dto(scenario, run)

    def list_runs_for_owner(self, *, owner_token: str | None) -> tuple[ReplayRunDetailDTO, ...]:
        if not owner_token:
            return ()
        runs = self._service.list_owner_runs(owner_token_hash=hash_owner_token(owner_token))
        dtos: list[ReplayRunDetailDTO] = []
        for run in runs:
            try:
                scenario = self._service.get_scenario(run.scenario_id)
            except ScenarioNotFoundError:
                continue
            dtos.append(self._run_to_dto(scenario, run))
        return tuple(dtos)


def build_decision_replay_router(controller: DecisionReplayController) -> APIRouter:
    router = APIRouter(prefix="/api/replays", tags=["decision-replay"])

    @router.get("", response_model=ReplayCatalogDTO)
    def list_scenarios() -> ReplayCatalogDTO:
        return controller.list_scenarios()

    @router.post(
        "/{scenario_id}/runs",
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

    @router.get("/runs/{run_id}", response_model=ReplayRunDetailDTO)
    def get_run(run_id: str, request: Request) -> ReplayRunDetailDTO:
        return controller.get_run(run_id, owner_token=request.cookies.get(OWNER_COOKIE_NAME))

    @router.post("/runs/{run_id}/choose", response_model=ReplayRunDetailDTO)
    def choose_option(
        run_id: str,
        payload: ChooseReplayOptionRequest,
        request: Request,
    ) -> ReplayRunDetailDTO:
        return controller.choose(
            run_id, payload, owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

    return router


__all__ = [
    "ChooseReplayOptionRequest",
    "DecisionReplayController",
    "ReplayCatalogDTO",
    "ReplayRunDetailDTO",
    "StartReplayRunRequest",
    "build_decision_replay_router",
]
