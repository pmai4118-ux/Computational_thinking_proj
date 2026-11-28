"""Composition root and FastAPI application factory (F05)."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from source.config import Settings, load_settings
from source.Control.adaptive_probe_controller import (
    AdaptiveProbeController,
    build_adaptive_probe_router,
)
from source.Control.decision_replay_controller import (
    DecisionReplayController,
    build_decision_replay_router,
)
from source.Control.job_analysis_controller import (
    JobAnalysisController,
    build_job_analysis_router,
)
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
    DecisionReplayRepository,
    EvaluationRepository,
    FollowUpProbeRepository,
    JobPostingRepository,
    SessionRepository,
)
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.Model.repositories.memory_profile_repository import MemoryCompetencyProfileRepository
from source.Model.repositories.memory_feature_repositories import (
    MemoryDecisionReplayRepository,
    MemoryFollowUpProbeRepository,
    MemoryJobPostingRepository,
)
from source.service.adaptive_probe_service import AdaptiveProbeService
from source.service.competency_profile_service import CompetencyProfileService
from source.service.decision_replay_service import DecisionReplayService
from source.service.evaluation_service import EvaluationService
from source.service.evaluation_queue import EvaluationQueue
from source.service.interview_service import InterviewService
from source.service.job_analysis_service import JobAnalysisService
from source.service.recommendation_service import RecommendationService
from source.service.session_report_service import SessionReportService
from source.service.providers.factory import create_evidence_interpreter, create_replay_simulator
from source.service.providers.interfaces import EvidenceInterpreter
from source.service.providers.replay_provider import ReplaySimulator
from source.service.seed_loader import load_seed_catalog_into_repository
from source.view.pages import build_pages_router
from source.Control.evaluation_controller import build_evaluation_router

STATIC_DIR = Path(__file__).resolve().parent / "view" / "static"


class _RevalidatingStaticFiles(StaticFiles):
    """Serve static assets with Cache-Control: no-cache to force ETag revalidation."""

    def file_response(
        self,
        full_path,
        stat_result,
        scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(
            full_path,
            stat_result,
            scope,
            status_code=status_code,
        )
        response.headers.setdefault("Cache-Control", "no-cache")
        return response


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
    job_analysis_service: JobAnalysisService
    job_analysis_controller: JobAnalysisController
    adaptive_probe_service: AdaptiveProbeService
    adaptive_probe_controller: AdaptiveProbeController
    decision_replay_service: DecisionReplayService
    decision_replay_controller: DecisionReplayController


def create_app(
    *,
    settings: Settings | None = None,
    content_repo: ContentRepository | None = None,
    session_repo: SessionRepository | None = None,
    evaluation_repo: EvaluationRepository | None = None,
    profile_repo: CompetencyProfileRepository | None = None,
    interpreter: EvidenceInterpreter | None = None,
    replay_simulator: ReplaySimulator | None = None,
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

    if auto_seed:
        existing_skills = resolved_content_repo.list_skills()
        needs_metadata_backfill = False
        if existing_skills:
            approved_qs = resolved_content_repo.list_approved_questions(
                role="backend_developer", level="intern_fresher", language="vi"
            )
            needs_metadata_backfill = any(
                q.coding_config is None
                or (q.category == "technical_case" and q.replay_grounding is None)
                for q in approved_qs
            )
        if not existing_skills or needs_metadata_backfill:
            load_seed_catalog_into_repository(resolved_content_repo)

    resolved_interpreter = (
        interpreter if interpreter is not None else create_evidence_interpreter(resolved_settings)
    )

    profile_service = CompetencyProfileService(
        content_repo=resolved_content_repo, session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo, profile_repo=resolved_profile_repo,
    )
    profile_controller = CompetencyProfileController(profile_service, resolved_content_repo)
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

    resolved_job_repo: JobPostingRepository = (
        resolved_session_repo if isinstance(resolved_session_repo, JobPostingRepository)
        else default_store if default_store is not None
        else MemoryJobPostingRepository()
    )
    resolved_probe_repo: FollowUpProbeRepository = (
        resolved_session_repo if isinstance(resolved_session_repo, FollowUpProbeRepository)
        else default_store if default_store is not None
        else MemoryFollowUpProbeRepository()
    )
    resolved_replay_repo: DecisionReplayRepository = (
        resolved_session_repo if isinstance(resolved_session_repo, DecisionReplayRepository)
        else default_store if default_store is not None
        else MemoryDecisionReplayRepository()
    )
    job_analysis_service = JobAnalysisService(
        content_repo=resolved_content_repo,
        job_repo=resolved_job_repo,
        profile_service=profile_service,
    )
    job_analysis_controller = JobAnalysisController(job_analysis_service)
    adaptive_probe_service = AdaptiveProbeService(
        interview_service=interview_service,
        content_repo=resolved_content_repo,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
        probe_repo=resolved_probe_repo,
        evaluation_service=evaluation_service,
        interpreter=resolved_interpreter,
    )
    adaptive_probe_controller = AdaptiveProbeController(
        interview_controller=interview_controller,
        probe_service=adaptive_probe_service,
    )
    resolved_replay_simulator = (
        replay_simulator
        if replay_simulator is not None
        else create_replay_simulator(resolved_settings)
    )
    decision_replay_service = DecisionReplayService(
        replay_repo=resolved_replay_repo,
        content_repo=resolved_content_repo,
        interview_service=interview_service,
        session_repo=resolved_session_repo,
        evaluation_repo=resolved_eval_repo,
        simulator=resolved_replay_simulator,
    )
    decision_replay_controller = DecisionReplayController(
        decision_replay_service,
        interview_controller=interview_controller,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            evaluation_queue.shutdown()
            decision_replay_service.shutdown()

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
        job_analysis_service=job_analysis_service,
        job_analysis_controller=job_analysis_controller,
        adaptive_probe_service=adaptive_probe_service,
        adaptive_probe_controller=adaptive_probe_controller,
        decision_replay_service=decision_replay_service,
        decision_replay_controller=decision_replay_controller,
    )

    register_api_exception_handlers(app)
    app.mount("/static", _RevalidatingStaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(build_interview_router(interview_controller))
    app.include_router(build_saved_evaluation_router(saved_evaluation_controller))
    app.include_router(build_exercise_router(exercise_controller))
    app.include_router(build_session_summary_router(session_summary_controller))
    app.include_router(build_competency_profile_router(profile_controller))
    app.include_router(build_job_analysis_router(job_analysis_controller))
    app.include_router(build_adaptive_probe_router(adaptive_probe_controller))
    app.include_router(build_decision_replay_router(decision_replay_controller))
    app.include_router(
        build_pages_router(
            interview_controller,
            saved_evaluation_controller,
            profile_controller=profile_controller,
            job_analysis_controller=job_analysis_controller,
            decision_replay_controller=decision_replay_controller,
        )
    )

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
