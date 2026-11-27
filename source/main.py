"""Composition root and FastAPI application factory (F05)."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from source.config import Settings, load_settings
from source.Control.saved_evaluation_controller import (
    SavedEvaluationController,
    build_saved_evaluation_router,
)
from source.Control.competency_profile_controller import (
    CompetencyProfileController, build_competency_profile_router,
)
from source.Control.exercise_controller import ExerciseController, build_exercise_router
from source.Control.session_summary_controller import (
    SessionSummaryController,
    build_session_summary_router,
)
from source.Control.interview_controller import (
    InterviewController,
    build_interview_router,
    register_api_exception_handlers,
)
from source.Model.repositories.interfaces import (
    CompetencyProfileRepository,
    ContentRepository,
    EvaluationRepository,
    SessionRepository,
)
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.Model.repositories.memory_profile_repository import MemoryCompetencyProfileRepository
from source.service.competency_profile_service import CompetencyProfileService
from source.service.evaluation_service import EvaluationService
from source.service.evaluation_queue import EvaluationQueue
from source.service.interview_service import InterviewService
from source.service.recommendation_service import RecommendationService
from source.service.session_report_service import SessionReportService
from source.service.providers.factory import create_evidence_interpreter
from source.service.providers.interfaces import EvidenceInterpreter
from source.service.seed_loader import load_seed_catalog_into_repository
from source.view.pages import build_pages_router
from source.Control.evaluation_controller import build_evaluation_router

STATIC_DIR = Path(__file__).resolve().parent / "view" / "static"


@dataclass(frozen=True, slots=True)
class AppContainer:
    """Wired application dependencies exposed for inspection and route handlers."""

    settings: Settings
    content_repo: ContentRepository
    session_repo: SessionRepository
    evaluation_repo: EvaluationRepository
    profile_repo: CompetencyProfileRepository
    interpreter: EvidenceInterpreter
    interview_service: InterviewService
    evaluation_service: EvaluationService
    evaluation_queue: EvaluationQueue
    profile_service: CompetencyProfileService
    profile_controller: CompetencyProfileController
    interview_controller: InterviewController
    saved_evaluation_controller: SavedEvaluationController
    recommendation_service: RecommendationService
    report_service: SessionReportService
    exercise_controller: ExerciseController
    session_summary_controller: SessionSummaryController


def create_app(
    *,
    settings: Settings | None = None,
    content_repo: ContentRepository | None = None,
    session_repo: SessionRepository | None = None,
    evaluation_repo: EvaluationRepository | None = None,
    profile_repo: CompetencyProfileRepository | None = None,
    interpreter: EvidenceInterpreter | None = None,
    auto_seed: bool = True,
) -> FastAPI:
    """Configure and connect MVC-S layers at the composition boundary."""
    resolved_settings = settings or load_settings()

    default_store: SQLiteRepositoryStore | None = None
    if content_repo is None or session_repo is None or evaluation_repo is None:
        default_store = SQLiteRepositoryStore(resolved_settings.database_path)

    resolved_content_repo = content_repo if content_repo is not None else default_store
    resolved_session_repo = session_repo if session_repo is not None else default_store
    resolved_eval_repo = evaluation_repo if evaluation_repo is not None else default_store
    assert resolved_content_repo is not None
    assert resolved_session_repo is not None
    assert resolved_eval_repo is not None

    resolved_profile_repo = profile_repo
    if resolved_profile_repo is None:
        resolved_profile_repo = (
            resolved_session_repo if isinstance(resolved_session_repo, CompetencyProfileRepository)
            else default_store if default_store is not None
            else MemoryCompetencyProfileRepository()
        )

    if auto_seed and not resolved_content_repo.list_skills():
        load_seed_catalog_into_repository(resolved_content_repo)

    resolved_interpreter = (
        interpreter if interpreter is not None else create_evidence_interpreter(resolved_settings)
    )

    profile_service = CompetencyProfileService(
        content_repo=resolved_content_repo, session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo, profile_repo=resolved_profile_repo,
    )
    profile_controller = CompetencyProfileController(profile_service)
    interview_service = InterviewService(
        content_repo=resolved_content_repo,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
        profile_service=profile_service,
    )
    evaluation_service = EvaluationService(
        evaluation_repo=resolved_eval_repo, session_repo=resolved_session_repo,
        content_repo=resolved_content_repo, interpreter=resolved_interpreter,
        profile_service=profile_service,
    )
    evaluation_queue = EvaluationQueue(evaluation_service, resolved_session_repo)
    interview_controller = InterviewController(
        interview_service=interview_service,
        demo_mode_label=resolved_settings.demo_label,
        evaluation_queue=evaluation_queue,
    )

    saved_evaluation_controller = SavedEvaluationController(
        interview_controller, evaluation_service, evaluation_queue
    )
    recommendation_service = RecommendationService(
        content_repo=resolved_content_repo,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
        interview_service=interview_service,
    )
    report_service = SessionReportService(
        interview_service=interview_service,
        content_repo=resolved_content_repo,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
        recommendation_service=recommendation_service,
    )
    exercise_controller = ExerciseController(
        service=recommendation_service,
        interview_controller=interview_controller,
        demo_mode_label=resolved_settings.demo_label,
    )
    session_summary_controller = SessionSummaryController(
        interview_controller=interview_controller,
        recommendation_service=recommendation_service,
        report_service=report_service,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            evaluation_queue.shutdown()

    app = FastAPI(
        title="interviewUS — Luyện phỏng vấn kỹ thuật Backend",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.container = AppContainer(
        settings=resolved_settings,
        content_repo=resolved_content_repo,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
        profile_repo=resolved_profile_repo,
        interpreter=resolved_interpreter,
        interview_service=interview_service,
        evaluation_service=evaluation_service,
        evaluation_queue=evaluation_queue,
        profile_service=profile_service,
        profile_controller=profile_controller,
        interview_controller=interview_controller,
        saved_evaluation_controller=saved_evaluation_controller,
        recommendation_service=recommendation_service,
        report_service=report_service,
        exercise_controller=exercise_controller,
        session_summary_controller=session_summary_controller,
    )

    register_api_exception_handlers(app)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(build_interview_router(interview_controller))
    app.include_router(build_saved_evaluation_router(saved_evaluation_controller))
    app.include_router(build_exercise_router(exercise_controller))
    app.include_router(build_session_summary_router(session_summary_controller))
    app.include_router(build_competency_profile_router(profile_controller))
    app.include_router(build_pages_router(interview_controller, saved_evaluation_controller))

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str | None]:
        return {
            "status": "ok",
            "provider": resolved_settings.provider.value,
            "demo_mode_label": resolved_settings.demo_label,
        }

    app.include_router(build_evaluation_router(saved_evaluation_controller))
    return app


__all__ = ["AppContainer", "STATIC_DIR", "create_app"]


if __name__ == "__main__":
    from source.view.evaluation_cli import run

    raise SystemExit(run())
