"""Public link catalog and anonymous-owner learning-plan orchestration."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from source.Control.interview_controller import OWNER_COOKIE_NAME, hash_owner_token
from source.Model.learning_path import LearningPlanRequest
from source.Model.repositories.interfaces import RepositoryError
from source.service.competency_profile_service import CompetencyProfileService
from source.service.learning_path_service import LearningPathService


def build_learning_path_router(service: LearningPathService, profile_service: CompetencyProfileService) -> APIRouter:
    router = APIRouter(prefix="/api/learning-paths", tags=["learning paths"])

    @router.get("/catalog")
    def catalog() -> dict:
        return service.catalog.model_dump(mode="json")

    @router.get("/markdown")
    def markdown() -> Response:
        # Generated from the same catalog; never execute or fetch remote resources.
        from source.service.learning_path_export import catalog_markdown
        return Response(catalog_markdown(service.catalog), media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="java-backend-roadmap.md"'})

    @router.post("/plan")
    def plan(payload: LearningPlanRequest, request: Request) -> dict:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        entries = ()
        profile_warning = None
        if payload.use_profile and owner_token:
            try:
                entries = profile_service.refresh(hash_owner_token(owner_token))
            except RepositoryError:
                profile_warning = "Chưa đọc được hồ sơ; đã giữ lựa chọn và tạo kế hoạch theo mục tiêu bạn xác nhận."
        try:
            result = service.plan(payload, entries)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if profile_warning:
            result["warnings"].append(profile_warning)
        return result

    return router
