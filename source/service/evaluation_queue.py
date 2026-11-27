"""Local worker for durable, resumable evaluation attempts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from threading import Lock

from source.Model.evaluation import AnswerRevisionRef, EvaluationResult, EvaluationStatus
from source.Model.ids import SessionId, VersionedRef
from source.Model.repositories.interfaces import SessionRepository
from source.service.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)


class EvaluationQueue:
    """Queue saved answers while SQLite remains the source of job status."""

    def __init__(self, service: EvaluationService, session_repo: SessionRepository) -> None:
        self._service = service
        self._session_repo = session_repo
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="grading")
        self._lock = Lock()
        self._scheduled: set[AnswerRevisionRef] = set()

    def enqueue(self, answer_ref: AnswerRevisionRef, *, retry_failed: bool = False,
                recover_interrupted: bool = False) -> EvaluationResult:
        _answer, question, rubric = self._service.get_saved_context(answer_ref)
        repo = self._service.evaluation_repository
        attempt = repo.prepare_evaluation(
            answer_ref, question.ref, VersionedRef(rubric.id, rubric.version),
            retry_failed=retry_failed, recover_interrupted=recover_interrupted,
        )
        if attempt.status is EvaluationStatus.PENDING:
            with self._lock:
                if answer_ref not in self._scheduled:
                    self._scheduled.add(answer_ref)
                    try:
                        self._executor.submit(self._run, answer_ref)
                    except RuntimeError:
                        self._scheduled.discard(answer_ref)
                        raise
        return attempt

    def resume_session(self, session_id: SessionId) -> None:
        latest = {}
        for answer in self._session_repo.list_answers_for_session(session_id):
            previous = latest.get(answer.question_ref)
            if previous is None or answer.revision > previous.revision:
                latest[answer.question_ref] = answer
        for answer in latest.values():
            # A session resume may restart interrupted work, but it must not
            # create a grading attempt for answers that have never been queued.
            existing = self._service.evaluation_repository.get_latest_evaluation_for_answer(
                answer.ref
            )
            if existing is not None and existing.status in {
                EvaluationStatus.PENDING,
                EvaluationStatus.PROCESSING,
            }:
                self.enqueue(answer.ref, recover_interrupted=True)

    def _run(self, answer_ref: AnswerRevisionRef) -> None:
        initial = None
        try:
            initial = self._service.evaluation_repository.get_latest_evaluation_for_answer(answer_ref)
            self._service.evaluate_saved_answer(answer_ref)
        except Exception:
            # The service saves an error state when a claimed attempt fails.
            logger.warning("Background evaluation did not complete for a saved answer.")
        finally:
            with self._lock:
                self._scheduled.discard(answer_ref)
                try:
                    latest = self._service.evaluation_repository.get_latest_evaluation_for_answer(answer_ref)
                except Exception:
                    logger.warning("Could not read the background evaluation state.")
                    return
                # Retry can arrive after a failure was stored but before this worker exits.
                if (latest is not None and latest.status is EvaluationStatus.PENDING
                        and initial is not None and latest.version > initial.version):
                    self._scheduled.add(answer_ref)
                    try:
                        self._executor.submit(self._run, answer_ref)
                    except RuntimeError:
                        self._scheduled.discard(answer_ref)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
