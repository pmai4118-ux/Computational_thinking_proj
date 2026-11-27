"""Controller and REST endpoints for JD import and skill-gap analysis (X06/X07)."""

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
from source.service.job_analysis_service import (
    JobAnalysisError,
    JobAnalysisForbiddenError,
    JobAnalysisNotFoundError,
    JobAnalysisService,
    JobGapReport,
    SkillGapItem,
)


class CreateJobAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_text: str = Field(min_length=1, max_length=30000)
    title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=1000)
    published_at: str | None = Field(default=None, max_length=64)


class JobEvidenceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_id: str
    matched_term: str
    quote: str
    start_offset: int
    end_offset: int


class UnmatchedJobTermDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    term_label: str
    quote: str
    start_offset: int
    end_offset: int
    reason: str


class JobExerciseHintDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exercise_id: str
    title: str
    summary: str
    estimated_duration_minutes: int | None = None


class JobSkillGapDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_id: str
    skill_label: str
    profile_state: str
    evidence: tuple[JobEvidenceDTO, ...] = ()
    weak_criterion_types: tuple[str, ...] = ()
    recommended_exercises: tuple[JobExerciseHintDTO, ...] = ()
    explanation: str


class JobAnalysisSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    analysis_id: str
    title: str | None = None
    company: str | None = None
    source_url: str | None = None
    published_at: str | None = None
    collected_at: datetime
    normalization_version: str
    matched_skill_count: int
    unmatched_term_count: int


class JobAnalysisDetailDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    analysis_id: str
    title: str | None = None
    company: str | None = None
    raw_text: str
    source_url: str | None = None
    published_at: str | None = None
    collected_at: datetime
    normalization_version: str
    matched_catalog_skill_count: int
    strength_count: int
    needs_practice_count: int
    unobserved_count: int
    unresolved_count: int
    unmatched_term_count: int
    summary_note: str
    skill_gaps: tuple[JobSkillGapDTO, ...] = ()
    unmatched_terms: tuple[UnmatchedJobTermDTO, ...] = ()


class JobAnalysisListDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    analyses: tuple[JobAnalysisSummaryDTO, ...] = ()


class JobAnalysisController:
    def __init__(self, service: JobAnalysisService) -> None:
        self._service = service

    @staticmethod
    def _gap_to_dto(item: SkillGapItem) -> JobSkillGapDTO:
        return JobSkillGapDTO(
            skill_id=str(item.skill_id),
            skill_label=item.skill_label,
            profile_state=item.profile_state,
            evidence=tuple(
                JobEvidenceDTO(
                    skill_id=str(ev.skill_id),
                    matched_term=ev.matched_term,
                    quote=ev.quote,
                    start_offset=ev.start_offset,
                    end_offset=ev.end_offset,
                )
                for ev in item.evidence
            ),
            weak_criterion_types=item.weak_criterion_types,
            recommended_exercises=tuple(
                JobExerciseHintDTO(
                    exercise_id=str(ex.id),
                    title=ex.title,
                    summary=ex.summary,
                    estimated_duration_minutes=ex.estimated_duration_minutes,
                )
                for ex in item.recommended_exercises
            ),
            explanation=item.explanation,
        )

    @classmethod
    def _report_to_dto(cls, report: JobGapReport) -> JobAnalysisDetailDTO:
        posting = report.record.posting
        return JobAnalysisDetailDTO(
            analysis_id=posting.id,
            title=posting.title,
            company=posting.company,
            raw_text=posting.raw_text,
            source_url=posting.source_url,
            published_at=posting.published_at,
            collected_at=posting.collected_at,
            normalization_version=posting.normalization_version,
            matched_catalog_skill_count=report.matched_catalog_skill_count,
            strength_count=report.strength_count,
            needs_practice_count=report.needs_practice_count,
            unobserved_count=report.unobserved_count,
            unresolved_count=report.unresolved_count,
            unmatched_term_count=report.unmatched_term_count,
            summary_note=report.summary_note,
            skill_gaps=tuple(cls._gap_to_dto(item) for item in report.skill_gaps),
            unmatched_terms=tuple(
                UnmatchedJobTermDTO(
                    term_label=term.term_label,
                    quote=term.quote,
                    start_offset=term.start_offset,
                    end_offset=term.end_offset,
                    reason=term.reason,
                )
                for term in report.record.unmatched_terms
            ),
        )

    def create(
        self, payload: CreateJobAnalysisRequest, *, owner_token: str
    ) -> JobAnalysisDetailDTO:
        try:
            report = self._service.analyze_jd(
                owner_token_hash=hash_owner_token(owner_token),
                raw_text=payload.raw_text,
                title=payload.title,
                company=payload.company,
                source_url=payload.source_url,
                published_at=payload.published_at,
            )
        except JobAnalysisError as error:
            raise ApiControllerError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    recovery_action="Kiểm tra nội dung JD và liên kết nguồn rồi gửi lại.",
                ),
            ) from error
        return self._report_to_dto(report)

    def get(self, analysis_id: str, *, owner_token: str | None) -> JobAnalysisDetailDTO:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            report = self._service.get_owned_report(
                analysis_id=analysis_id, owner_token_hash=owner_hash
            )
        except JobAnalysisNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    recovery_action="Quay lại trang Phân tích JD để tạo phân tích mới.",
                ),
            ) from error
        except JobAnalysisForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message=str(error),
                    retryable=False,
                    recovery_action="Chỉ trình duyệt đã tạo phân tích JD này mới có quyền đọc.",
                ),
            ) from error
        return self._report_to_dto(report)

    def list_for_owner(self, *, owner_token: str | None) -> JobAnalysisListDTO:
        if not owner_token:
            return JobAnalysisListDTO()
        records = self._service.list_owner_analyses(owner_token_hash=hash_owner_token(owner_token))
        return JobAnalysisListDTO(
            analyses=tuple(
                JobAnalysisSummaryDTO(
                    analysis_id=rec.posting.id,
                    title=rec.posting.title,
                    company=rec.posting.company,
                    source_url=rec.posting.source_url,
                    published_at=rec.posting.published_at,
                    collected_at=rec.posting.collected_at,
                    normalization_version=rec.posting.normalization_version,
                    matched_skill_count=len({ev.skill_id for ev in rec.matched_skills}),
                    unmatched_term_count=len(rec.unmatched_terms),
                )
                for rec in records
            )
        )


def build_job_analysis_router(controller: JobAnalysisController) -> APIRouter:
    router = APIRouter(prefix="/api/jd-analyses", tags=["jd-analysis"])

    @router.post("", response_model=JobAnalysisDetailDTO, status_code=status.HTTP_201_CREATED)
    def create_analysis(
        payload: CreateJobAnalysisRequest, request: Request, response: Response
    ) -> JobAnalysisDetailDTO:
        token, created = ensure_owner_cookie_token(request.cookies.get(OWNER_COOKIE_NAME))
        if created:
            apply_owner_cookie(response, token)
        return controller.create(payload, owner_token=token)

    @router.get("", response_model=JobAnalysisListDTO)
    def list_analyses(request: Request) -> JobAnalysisListDTO:
        return controller.list_for_owner(owner_token=request.cookies.get(OWNER_COOKIE_NAME))

    @router.get("/{analysis_id}", response_model=JobAnalysisDetailDTO)
    def get_analysis(analysis_id: str, request: Request) -> JobAnalysisDetailDTO:
        return controller.get(analysis_id, owner_token=request.cookies.get(OWNER_COOKIE_NAME))

    return router


__all__ = [
    "CreateJobAnalysisRequest",
    "JobAnalysisController",
    "JobAnalysisDetailDTO",
    "JobAnalysisListDTO",
    "build_job_analysis_router",
]
