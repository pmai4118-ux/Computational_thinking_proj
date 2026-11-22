"""Composition root and FastAPI application factory (F05)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from source.config import Settings, load_settings
from source.Control.interview_controller import (
    InterviewController,
    build_interview_router,
    register_api_exception_handlers,
)
from source.Model.repositories.interfaces import (
    ContentRepository,
    EvaluationRepository,
    SessionRepository,
)
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.service.evaluation_service import EvaluationService
from source.service.interview_service import InterviewService
from source.service.providers.factory import create_evidence_interpreter
from source.service.providers.interfaces import EvidenceInterpreter
from source.service.seed_loader import load_seed_catalog_into_repository
from source.view.pages import build_pages_router

STATIC_DIR = Path(__file__).resolve().parent / "view" / "static"


@dataclass(frozen=True, slots=True)
class AppContainer:
    """Wired application dependencies exposed for inspection and route handlers."""

    settings: Settings
    content_repo: ContentRepository
    session_repo: SessionRepository
    evaluation_repo: EvaluationRepository
    interpreter: EvidenceInterpreter
    interview_service: InterviewService
    evaluation_service: EvaluationService
    interview_controller: InterviewController


def create_app(
    *,
    settings: Settings | None = None,
    content_repo: ContentRepository | None = None,
    session_repo: SessionRepository | None = None,
    evaluation_repo: EvaluationRepository | None = None,
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

    if auto_seed and not resolved_content_repo.list_skills():
        load_seed_catalog_into_repository(resolved_content_repo)

    resolved_interpreter = (
        interpreter if interpreter is not None else create_evidence_interpreter(resolved_settings)
    )

    interview_service = InterviewService(
        content_repo=resolved_content_repo,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
    )
    evaluation_service = EvaluationService(
        evaluation_repo=resolved_eval_repo, session_repo=resolved_session_repo,
        content_repo=resolved_content_repo, interpreter=resolved_interpreter,
    )
    interview_controller = InterviewController(
        interview_service=interview_service,
        demo_mode_label=resolved_settings.demo_label,
    )

    app = FastAPI(
        title="interviewUS — Luyện phỏng vấn kỹ thuật Backend",
        version="0.1.0",
    )
    app.state.container = AppContainer(
        settings=resolved_settings,
        content_repo=resolved_content_repo,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
        interpreter=resolved_interpreter,
        interview_service=interview_service,
        evaluation_service=evaluation_service,
        interview_controller=interview_controller,
    )

    register_api_exception_handlers(app)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(build_interview_router(interview_controller))
    app.include_router(build_pages_router(interview_controller))

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str | None]:
        return {
            "status": "ok",
            "provider": resolved_settings.provider.value,
            "demo_mode_label": resolved_settings.demo_label,
        }

    return app


__all__ = ["AppContainer", "STATIC_DIR", "create_app"]


if __name__ == "__main__":
    from source.view.evaluation_cli import run

    raise SystemExit(run())
