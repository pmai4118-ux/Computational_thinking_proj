"""Session question selection, blueprint coverage, and lifecycle transitions (I01/I03)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from uuid import uuid4

from source.Model.evaluation import CriterionStatus, EvaluationResult, EvaluationStatus
from source.Model.competency_profile import CompetencyState
from source.Model.ids import (
    AnswerId,
    QuestionId,
    SessionId,
    SkillId,
    VersionedRef,
)
from source.Model.interview import Answer, EvaluationTiming, Session, SessionState
from source.Model.question import LicenseStatus, Question, ReviewStatus, SourceMetadata
from source.Model.repositories.interfaces import (
    AnswerLockedError,
    CompetencyProfileRepository,
    ContentRepository,
    EvaluationRepository,
    SessionRepository,
)
from source.service.coverage import missing_coverage
from source.service.competency_profile_service import CompetencyProfileService

DEFAULT_BLUEPRINTS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "seed" / "session_blueprints.json"
)
logger = logging.getLogger(__name__)


class InterviewServiceError(RuntimeError):
    """Base domain error for interview session coordination."""


class UnsupportedBlueprintError(InterviewServiceError):
    """Raised when requested (role, level, language) has no configured session blueprint."""


class InsufficientQuestionBankError(InterviewServiceError):
    """Raised when approved, verified questions cannot cover every blueprint slot."""

    def __init__(self, missing_by_category: dict[str, SkillId]) -> None:
        self.missing_by_category = dict(missing_by_category)
        details = ", ".join(
            f"{category} ({skill_id})"
            for category, skill_id in self.missing_by_category.items()
        )
        super().__init__(
            f"Approved question bank is missing required blueprint coverage for: {details}."
        )


class SessionNotFoundError(InterviewServiceError):
    """Raised when a session ID does not exist."""


class SessionForbiddenError(InterviewServiceError):
    """Raised when the caller's anonymous owner hash does not match the session owner."""


class SessionExpiredError(InterviewServiceError):
    """Raised when attempting an active mutation on an expired session."""


class InvalidSessionStateError(InterviewServiceError):
    """Raised when an action violates session state or question ordering invariants."""


@dataclass(frozen=True, slots=True)
class BlueprintSlot:
    category: str
    skill_id: SkillId
    eligible_criterion_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SessionBlueprint:
    id: str
    version: int
    role: str
    level: str
    language: str
    allowed_difficulties: frozenset[str]
    on_missing_coverage: str
    slots: tuple[BlueprintSlot, ...]


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    """Resolved view-ready domain state for a single session."""

    session: Session
    current_question: Question | None
    current_source: SourceMetadata | None
    current_answer: Answer | None
    latest_evaluation: EvaluationResult | None
    answered_count: int
    evaluated_count: int
    current_draft: str | None = None


@dataclass(frozen=True, slots=True)
class SubmittedAnswerOutcome:
    """Result of saving an immutable answer revision for the active session question."""

    answer: Answer
    idempotent_replay: bool
    evaluation_status: EvaluationStatus


def load_session_blueprints(
    path: Path = DEFAULT_BLUEPRINTS_PATH,
) -> tuple[SessionBlueprint, ...]:
    """Load session blueprints from `data/seed/session_blueprints.json`."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("session_blueprints.json must contain a JSON array.")
    blueprints: list[SessionBlueprint] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("slots"), list):
            raise ValueError("Each session blueprint must be an object with a slots array.")
        slots = tuple(
            BlueprintSlot(
                category=slot["category"],
                skill_id=SkillId(slot["skill_id"]),
                eligible_criterion_types=tuple(slot["eligible_criterion_types"]),
            )
            if isinstance(slot, dict)
            else (_ for _ in ()).throw(ValueError("Each blueprint slot must be an object."))
            for slot in item["slots"]
        )
        blueprints.append(
            SessionBlueprint(
                id=item["id"],
                version=int(item["version"]),
                role=item["role"],
                level=item["level"],
                language=item["language"],
                allowed_difficulties=frozenset(item["allowed_difficulties"]),
                on_missing_coverage=item.get("on_missing_coverage", "error"),
                slots=slots,
            )
        )
    return tuple(blueprints)


class InterviewService:
    """Selects blueprint-compliant questions and enforces server-side session state transitions."""

    def __init__(
        self,
        *,
        content_repo: ContentRepository,
        session_repo: SessionRepository,
        evaluation_repo: EvaluationRepository | None = None,
        profile_service: CompetencyProfileService | None = None,
        blueprints: tuple[SessionBlueprint, ...] | None = None,
    ) -> None:
        self._content_repo = content_repo
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
        self._profile_service = profile_service
        if self._profile_service is None and evaluation_repo is not None and isinstance(
            session_repo, CompetencyProfileRepository
        ):
            self._profile_service = CompetencyProfileService(
                content_repo=content_repo, session_repo=session_repo,
                evaluation_repo=evaluation_repo, profile_repo=session_repo,
            )
        self._blueprints = (
            blueprints if blueprints is not None else load_session_blueprints()
        )

    def find_blueprint(
        self,
        *,
        role: str,
        level: str,
        language: str,
    ) -> SessionBlueprint:
        for bp in self._blueprints:
            if bp.role == role and bp.level == level and bp.language == language:
                return bp
        raise UnsupportedBlueprintError(
            f"No session blueprint configured for role='{role}', level='{level}', language='{language}'."
        )

    def _active_eligible_questions(self, blueprint: SessionBlueprint) -> list[Question]:
        approved = self._content_repo.list_approved_questions(
            role=blueprint.role,
            level=blueprint.level,
            language=blueprint.language,
        )
        # Keep only the highest version per logical QuestionId and verify source license
        latest_by_id: dict[QuestionId, Question] = {}
        for question in approved:
            if question.difficulty not in blueprint.allowed_difficulties:
                continue
            source = self._content_repo.get_source(question.source_id)
            if source is None or source.license_status is not LicenseStatus.VERIFIED:
                continue
            rubric = self._content_repo.get_rubric(question.rubric_ref)
            if rubric is None or rubric.review.status is not ReviewStatus.APPROVED:
                continue
            prev = latest_by_id.get(question.id)
            if prev is None or question.version > prev.version:
                latest_by_id[question.id] = question
        return [latest_by_id[qid] for qid in sorted(latest_by_id)]

    def _select_questions_for_owner(
        self,
        *,
        blueprint: SessionBlueprint,
        owner_token_hash: str,
    ) -> tuple[VersionedRef[QuestionId], ...]:
        eligible = self._active_eligible_questions(blueprint)
        required_skills = {
            slot.category: slot.skill_id for slot in blueprint.slots
        }
        uncovered = missing_coverage(required_skills, eligible)
        if uncovered:
            raise InsufficientQuestionBankError(uncovered)

        # Only finished, scored sessions can inform the next interview. An answer in
        # the current interview has not been assessed and must not be treated as a gap.
        usage_counts: dict[QuestionId, int] = {}
        past_sessions = sorted(
            self._session_repo.list_sessions_by_owner(owner_token_hash),
            key=lambda item: item.created_at.timestamp() if item.created_at else float("-inf"),
            reverse=True,
        )
        for past_session in past_sessions:
            for q_ref in past_session.question_refs:
                usage_counts[q_ref.id] = usage_counts.get(q_ref.id, 0) + 1
        gap_priority: dict[SkillId, dict[str, float]] = {}
        if self._profile_service is not None:
            for entry in self._profile_service.refresh(owner_token_hash):
                if entry.state is CompetencyState.NEEDS_PRACTICE:
                    gap_priority.setdefault(entry.skill_id, {})[entry.criterion_type] = (
                        entry.selection_priority
                    )
        elif self._evaluation_repo is not None:
            # Compatibility for injected repositories without profile persistence.
            latest_observations: dict[tuple[SkillId, str], bool] = {}
            for past_session in past_sessions:
                if past_session.state not in (SessionState.COMPLETED, SessionState.ENDED_EARLY):
                    continue
                latest_answers = {}
                for answer in self._session_repo.list_answers_for_session(past_session.id):
                    previous = latest_answers.get(answer.question_ref)
                    if previous is None or answer.revision > previous.revision:
                        latest_answers[answer.question_ref] = answer
                for answer in latest_answers.values():
                    evaluation = self._evaluation_repo.get_completed_evaluation_for_answer(answer.ref)
                    question = self._content_repo.get_question(answer.question_ref)
                    rubric = self._content_repo.get_rubric(answer.rubric_ref)
                    if evaluation is None or question is None or rubric is None:
                        continue
                    criteria = {criterion.id: criterion for criterion in rubric.criteria}
                    for check in evaluation.criterion_checks:
                        criterion = criteria.get(check.criterion_id)
                        if criterion is None or not criterion.criterion_type:
                            continue
                        for skill_id in question.skill_ids:
                            latest_observations.setdefault(
                                (skill_id, criterion.criterion_type),
                                check.status is CriterionStatus.UNMET
                                and check.score is not None
                                and check.score < criterion.max_score,
                            )
            for (skill_id, criterion_type), still_gap in latest_observations.items():
                if still_gap:
                    gap_priority.setdefault(skill_id, {})[criterion_type] = 1.0

        chosen: list[VersionedRef[QuestionId]] = []
        chosen_ids: set[QuestionId] = set()

        for idx, slot in enumerate(blueprint.slots):
            remaining_required = {
                later_slot.category: later_slot.skill_id
                for later_slot in blueprint.slots[idx + 1 :]
            }
            slot_candidates = [
                q
                for q in eligible
                if q.id not in chosen_ids
                and q.category == slot.category
                and slot.skill_id in q.skill_ids
                and any(
                    criterion.criterion_type in slot.eligible_criterion_types
                    for criterion in self._content_repo.get_rubric(q.rubric_ref).criteria
                )
            ]
            def selection_key(question: Question) -> tuple[int, float, str]:
                rubric = self._content_repo.get_rubric(question.rubric_ref)
                matched_types = 0.0 if rubric is None else sum(
                    gap_priority.get(slot.skill_id, {}).get(criterion_type, 0.0)
                    for criterion_type in {criterion.criterion_type for criterion in rubric.criteria}
                )
                # Exposure control wins over personalization in the small seed bank.
                return (usage_counts.get(question.id, 0), -matched_types, question.id)

            slot_candidates.sort(key=selection_key)

            picked: Question | None = None
            for candidate in slot_candidates:
                remaining_pool = [
                    q for q in eligible if q.id not in chosen_ids and q.id != candidate.id
                ]
                if not missing_coverage(remaining_required, remaining_pool):
                    picked = candidate
                    break

            if picked is None:
                still_missing = missing_coverage(
                    {s.category: s.skill_id for s in blueprint.slots[idx:]},
                    [q for q in eligible if q.id not in chosen_ids],
                )
                raise InsufficientQuestionBankError(
                    still_missing or {slot.category: slot.skill_id}
                )

            chosen.append(picked.ref)
            chosen_ids.add(picked.id)

        return tuple(chosen)

    def open_session(
        self,
        *,
        owner_token_hash: str,
        role: str = "backend_developer",
        level: str = "intern_fresher",
        language: str = "vi",
        session_id: SessionId | None = None,
        evaluation_timing: EvaluationTiming = EvaluationTiming.PER_QUESTION,
    ) -> SessionSnapshot:
        blueprint = self.find_blueprint(role=role, level=level, language=language)
        selected_refs = self._select_questions_for_owner(
            blueprint=blueprint,
            owner_token_hash=owner_token_hash,
        )
        now = datetime.now(UTC)
        resolved_id = session_id or SessionId(f"session.{uuid4().hex[:12]}")
        session = Session(
            id=resolved_id,
            owner_token_hash=owner_token_hash,
            role=blueprint.role,
            level=blueprint.level,
            language=blueprint.language,
            state=SessionState.IN_PROGRESS,
            question_refs=selected_refs,
            current_index=0,
            answer_refs=(),
            created_at=now,
            updated_at=now,
            evaluation_timing=evaluation_timing,
        )
        stored = self._session_repo.create_session(session)
        return self._build_snapshot(stored)

    def _require_owned_session(
        self,
        *,
        session_id: SessionId,
        owner_token_hash: str,
    ) -> Session:
        session = self._session_repo.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' was not found.")
        if session.owner_token_hash != owner_token_hash:
            raise SessionForbiddenError(
                f"Session '{session_id}' does not belong to the current caller."
            )
        return session

    def get_owned_session(
        self,
        *,
        session_id: SessionId,
        owner_token_hash: str,
    ) -> SessionSnapshot:
        session = self._require_owned_session(
            session_id=session_id,
            owner_token_hash=owner_token_hash,
        )
        if session.state is SessionState.ENDED_EARLY:
            session = self._session_repo.resume_ended_session(session.id)
        if (session.state is SessionState.IN_PROGRESS
                and session.current_index == len(session.question_refs) - 1):
            answered = {answer.question_ref for answer in self._session_repo.list_answers_for_session(session.id)}
            if all(ref in answered for ref in session.question_refs):
                # Recover a crash between the final answer save and the next action.
                # The repository transition is atomic and repeated requests are idempotent.
                session = self._session_repo.advance_session(session.id, session.current_index)
                if session.state is SessionState.COMPLETED:
                    self._refresh_profile_after_finish(session)
        return self._build_snapshot(session)

    def list_owner_sessions(self, *, owner_token_hash: str) -> tuple[Session, ...]:
        return self._session_repo.list_sessions_by_owner(owner_token_hash)

    def save_draft(
        self, *, session_id: SessionId, owner_token_hash: str,
        question_ref: VersionedRef[QuestionId], text: str,
    ) -> None:
        session = self._require_owned_session(session_id=session_id, owner_token_hash=owner_token_hash)
        if session.state is not SessionState.IN_PROGRESS or session.current_question_ref != question_ref:
            raise InvalidSessionStateError("Bản nháp chỉ được lưu cho câu hỏi hiện tại.")
        if len(text) > 20_000:
            raise ValueError("Bản nháp tối đa 20.000 ký tự.")
        try:
            self._session_repo.save_draft(session_id, question_ref, text)
        except AnswerLockedError as error:
            raise InvalidSessionStateError(str(error)) from error

    def submit_answer(
        self,
        *,
        session_id: SessionId,
        owner_token_hash: str,
        question_ref: VersionedRef[QuestionId],
        text: str,
        client_submission_id: str,
        answer_id: AnswerId | None = None,
    ) -> SubmittedAnswerOutcome:
        """Validate active question ownership, persist verbatim Answer before evaluation, and enforce idempotency."""
        session = self._require_owned_session(
            session_id=session_id,
            owner_token_hash=owner_token_hash,
        )
        if session.state is SessionState.EXPIRED:
            raise SessionExpiredError(f"Session '{session_id}' has expired.")
        # Allow exact idempotent replay even if client retries an already saved submission
        existing_answers = self._session_repo.list_answers_for_session(session_id)
        for existing in existing_answers:
            if existing.client_submission_id == client_submission_id:
                # Delegate to repository save_answer so identical replays return (existing, True)
                # and mismatched text/question raises DuplicateSubmissionConflictError.
                candidate = Answer(
                    id=existing.id,
                    revision=existing.revision,
                    session_id=session.id,
                    question_ref=question_ref,
                    rubric_ref=existing.rubric_ref,
                    text=text,
                    submitted_at=datetime.now(UTC),
                    client_submission_id=client_submission_id,
                )
                stored_answer, replay = self._session_repo.save_answer(candidate)
                eval_status = EvaluationStatus.PENDING
                if self._evaluation_repo is not None:
                    latest_eval = self._evaluation_repo.get_latest_evaluation_for_answer(
                        stored_answer.ref
                    )
                    if latest_eval is not None:
                        eval_status = latest_eval.status
                return SubmittedAnswerOutcome(
                    answer=stored_answer,
                    idempotent_replay=replay,
                    evaluation_status=eval_status,
                )

        if session.state is not SessionState.IN_PROGRESS:
            raise InvalidSessionStateError(
                f"Cannot submit answers when session '{session_id}' is in state '{session.state.value}'."
            )

        active_q_ref = session.current_question_ref
        if active_q_ref is None or active_q_ref != question_ref:
            raise InvalidSessionStateError(
                f"Question ({question_ref.id}, v{question_ref.version}) does not match "
                f"the active session slot."
            )

        question = self._content_repo.get_question(question_ref)
        if question is None:
            raise InvalidSessionStateError(
                f"Question ({question_ref.id}, v{question_ref.version}) is missing from content store."
            )

        prior_for_question = [
            ans for ans in existing_answers if ans.question_ref == question_ref
        ]
        if prior_for_question:
            raise InvalidSessionStateError("The submitted answer is locked.")
        else:
            resolved_answer_id = answer_id or AnswerId(f"answer.{uuid4().hex[:12]}")
            next_revision = 1

        new_answer = Answer(
            id=resolved_answer_id,
            revision=next_revision,
            session_id=session.id,
            question_ref=question.ref,
            rubric_ref=question.rubric_ref,
            text=text,
            submitted_at=datetime.now(UTC),
            client_submission_id=client_submission_id,
        )
        try:
            stored_answer, replay = self._session_repo.save_answer(new_answer)
        except AnswerLockedError as error:
            raise InvalidSessionStateError(str(error)) from error
        return SubmittedAnswerOutcome(
            answer=stored_answer,
            idempotent_replay=replay,
            evaluation_status=EvaluationStatus.PENDING,
        )

    def advance_question(
        self,
        *,
        session_id: SessionId,
        owner_token_hash: str,
        from_question_index: int,
    ) -> SessionSnapshot:
        session = self._require_owned_session(
            session_id=session_id,
            owner_token_hash=owner_token_hash,
        )
        if session.state is SessionState.EXPIRED:
            raise SessionExpiredError(f"Session '{session_id}' has expired.")
        if hasattr(self._session_repo, "advance_session"):
            try:
                advanced = self._session_repo.advance_session(session_id, from_question_index)
            except AnswerLockedError as error:
                raise InvalidSessionStateError(str(error)) from error
            if advanced.state is SessionState.COMPLETED:
                self._refresh_profile_after_finish(advanced)
            return self._build_snapshot(advanced)
        if session.state is SessionState.COMPLETED and from_question_index == len(session.question_refs) - 1:
            return self._build_snapshot(session)
        if session.state is not SessionState.IN_PROGRESS:
            raise InvalidSessionStateError(
                f"Session '{session_id}' is in state '{session.state.value}' and cannot advance."
            )
        if session.current_index > 0 and from_question_index == session.current_index - 1:
            # Idempotent retry of 'next' after already advancing one step (W05)
            return self._build_snapshot(session)
        if from_question_index != session.current_index:
            raise InvalidSessionStateError(
                f"Expected from_question_index={session.current_index}, got {from_question_index}."
            )

        current_q_ref = session.question_refs[session.current_index]
        answers = [
            ans
            for ans in self._session_repo.list_answers_for_session(session.id)
            if ans.question_ref == current_q_ref
        ]
        if not answers:
            raise InvalidSessionStateError(
                "Cannot advance before submitting an answer for the current question."
            )
        next_index = session.current_index + 1
        next_state = (
            SessionState.COMPLETED
            if next_index >= len(session.question_refs)
            else SessionState.IN_PROGRESS
        )
        updated = replace(
            session,
            current_index=next_index,
            state=next_state,
            updated_at=datetime.now(UTC),
        )
        stored = self._session_repo.update_session(updated)
        if next_state is SessionState.COMPLETED:
            self._refresh_profile_after_finish(stored)
        return self._build_snapshot(stored)

    def end_session(
        self,
        *,
        session_id: SessionId,
        owner_token_hash: str,
    ) -> Session:
        session = self._require_owned_session(
            session_id=session_id,
            owner_token_hash=owner_token_hash,
        )
        if session.state is SessionState.EXPIRED:
            raise SessionExpiredError(f"Session '{session_id}' has expired.")
        if session.state in (SessionState.COMPLETED, SessionState.ENDED_EARLY):
            return session
        if len({a.question_ref for a in self._session_repo.list_answers_for_session(session.id)} & set(session.question_refs)) < len(session.question_refs):
            raise InvalidSessionStateError("Hãy lưu và thoát để tiếp tục phiên sau.")
        updated = replace(
            session,
            state=SessionState.ENDED_EARLY,
            updated_at=datetime.now(UTC),
        )
        stored = self._session_repo.update_session(updated)
        self._refresh_profile_after_finish(stored)
        return stored

    def _refresh_profile_after_finish(self, session: Session) -> None:
        if self._profile_service is None:
            return
        try:
            self._profile_service.refresh(session.owner_token_hash)
        except Exception:
            # Completion remains durable; opening the next session rebuilds the profile.
            logger.exception("Could not refresh profile for finished session %s", session.id)

    def _build_snapshot(self, session: Session) -> SessionSnapshot:
        all_answers = self._session_repo.list_answers_for_session(session.id)
        latest_by_q: dict[VersionedRef[QuestionId], Answer] = {}
        for ans in all_answers:
            if ans.question_ref not in session.question_refs:
                continue
            prev = latest_by_q.get(ans.question_ref)
            if prev is None or ans.revision > prev.revision:
                latest_by_q[ans.question_ref] = ans

        evaluated_count = 0
        if self._evaluation_repo is not None:
            for ans in latest_by_q.values():
                if self._evaluation_repo.get_completed_evaluation_for_answer(ans.ref) is not None:
                    evaluated_count += 1

        current_q_ref = session.current_question_ref
        current_question: Question | None = None
        current_source: SourceMetadata | None = None
        current_answer: Answer | None = None
        latest_eval: EvaluationResult | None = None

        if current_q_ref is not None:
            current_question = self._content_repo.get_question(current_q_ref)
            if current_question is not None:
                current_source = self._content_repo.get_source(current_question.source_id)
            current_answer = latest_by_q.get(current_q_ref)
            if current_answer is not None and self._evaluation_repo is not None:
                latest_eval = self._evaluation_repo.get_latest_evaluation_for_answer(
                    current_answer.ref
                )

        return SessionSnapshot(
            session=session,
            current_question=current_question,
            current_source=current_source,
            current_answer=current_answer,
            latest_evaluation=latest_eval,
            answered_count=len(latest_by_q),
            evaluated_count=evaluated_count,
            current_draft=(
                self._session_repo.get_draft(session.id, current_q_ref)
                if current_q_ref is not None and current_answer is None else None
            ),
        )


__all__ = [
    "BlueprintSlot",
    "DEFAULT_BLUEPRINTS_PATH",
    "InsufficientQuestionBankError",
    "InterviewService",
    "InterviewServiceError",
    "InvalidSessionStateError",
    "SessionBlueprint",
    "SessionExpiredError",
    "SessionForbiddenError",
    "SessionNotFoundError",
    "SessionSnapshot",
    "SubmittedAnswerOutcome",
    "UnsupportedBlueprintError",
    "load_session_blueprints",
]
