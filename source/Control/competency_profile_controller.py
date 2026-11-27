"""Read the current browser owner's evidence-linked competency profile."""

from __future__ import annotations

from fastapi import APIRouter, Request

from source.Control.interview_controller import OWNER_COOKIE_NAME, hash_owner_token
from source.Control.schemas import (
    AnswerRevisionRefDTO, CompetencyProfileEntryDTO, CompetencyProfileResponseDTO,
    RecentCriterionScoreDTO,
)
from source.Model.repositories.interfaces import ContentRepository
from source.service.competency_profile_service import CompetencyProfileService


class CompetencyProfileController:
    def __init__(
        self,
        service: CompetencyProfileService,
        content_repo: ContentRepository | None = None,
    ) -> None:
        self._service = service
        self._content_repo = content_repo

    def skill_labels(self) -> dict[str, str]:
        if self._content_repo is None:
            return {}
        return {str(skill.id): skill.label for skill in self._content_repo.list_skills()}

    def read(self, owner_token: str | None) -> CompetencyProfileResponseDTO:
        if not owner_token:
            return CompetencyProfileResponseDTO(
                message="Chưa có phiên nào gắn với trình duyệt này."
            )
        entries = self._service.refresh(hash_owner_token(owner_token))
        return CompetencyProfileResponseDTO(
            entries=tuple(CompetencyProfileEntryDTO(
                skill_id=item.skill_id,
                criterion_type=item.criterion_type,
                state=item.state,
                trend=item.trend,
                evidence_confidence=item.evidence_confidence,
                observed_count=item.observed_count,
                met_count=item.met_count,
                unmet_count=item.unmet_count,
                unresolved_count=item.unresolved_count,
                selection_priority=item.selection_priority,
                latest_status=item.latest_status,
                latest_evaluated_at=item.latest_evaluated_at,
                latest_session_id=item.latest_session_id,
                latest_answer_ref=AnswerRevisionRefDTO(
                    id=item.latest_answer_ref.id, revision=item.latest_answer_ref.revision,
                ),
                latest_evaluation_id=item.latest_evaluation_id,
                latest_evaluation_version=item.latest_evaluation_version,
                latest_criterion_id=item.latest_criterion_id,
                recent_scored=tuple(RecentCriterionScoreDTO(
                    score=score.score, maximum_score=score.maximum_score,
                    status=score.status,
                ) for score in item.recent_scored),
            ) for item in entries),
            message=None if entries else "Chưa có kết quả chấm hoàn tất để tạo hồ sơ năng lực.",
        )


def build_competency_profile_router(controller: CompetencyProfileController) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["profile"])

    @router.get("/profile", response_model=CompetencyProfileResponseDTO)
    def read_profile(request: Request) -> CompetencyProfileResponseDTO:
        return controller.read(request.cookies.get(OWNER_COOKIE_NAME))

    return router


__all__ = ["CompetencyProfileController", "build_competency_profile_router"]
