"""Session question selection, blueprint coverage, and lifecycle transitions (I01/I03)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import uuid4

from source.Model.evaluation import EvaluationResult, EvaluationStatus
from source.Model.ids import (
    AnswerId,
    QuestionId,
    SessionId,
    SkillId,
    VersionedRef,
)
from source.Model.interview import Answer, Session, SessionState
from source.Model.question import LicenseStatus, Question, SourceMetadata
from source.Model.repositories.interfaces import (
    ContentRepository,
    EvaluationRepository,
    SessionRepository,
)
from source.service.coverage import missing_coverage

DEFAULT_BLUEPRINTS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "seed" / "session_blueprints.json"
)


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
    blueprints: list[SessionBlueprint] = []
    for item in raw:
        slots = tuple(
            BlueprintSlot(
                category=slot["category"],
                skill_id=SkillId(slot["skill_id"]),
                eligible_criterion_types=tuple(slot["eligible_criterion_types"]),
            )
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
        blueprints: tuple[SessionBlueprint, ...] | None = None,
    ) -> None:
        self._content_repo = content_repo
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
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
            if self._content_repo.get_rubric(question.rubric_ref) is None:
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

        # Track usage frequency/order across prior sessions of this owner so unseen variants win
        usage_counts: dict[QuestionId, int] = {}
        for past_session in self._session_repo.list_sessions_by_owner(owner_token_hash):
            for q_ref in past_session.question_refs:
                usage_counts[q_ref.id] = usage_counts.get(q_ref.id, 0) + 1

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
            ]
            # Sort unseen (usage_count == 0) first, then fewer prior uses, then stable ID
            slot_candidates.sort(key=lambda q: (usage_counts.get(q.id, 0), q.id))

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
        return self._build_snapshot(session)

    def list_owner_sessions(self, *, owner_token_hash: str) -> tuple[Session, ...]:
        return self._session_repo.list_sessions_by_owner(owner_token_hash)

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
        if session.state is not SessionState.IN_PROGRESS:
            raise InvalidSessionStateError(
                f"Cannot submit answers when session '{session_id}' is in state '{session.state.value}'."
            )

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
            latest_prior = max(prior_for_question, key=lambda a: a.revision)
            resolved_answer_id = latest_prior.id
            next_revision = latest_prior.revision + 1
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
        stored_answer, replay = self._session_repo.save_answer(new_answer)
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
        if session.state is SessionState.COMPLETED and from_question_index == len(session.question_refs) - 1:
            return self._build_snapshot(session)
        if session.state is not SessionState.IN_PROGRESS:
            raise InvalidSessionStateError(
                f"Session '{session_id}' is in state '{session.state.value}' and cannot advance."
            )
        if from_question_index == session.current_index - 1:
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
        latest_answer = max(answers, key=lambda a: a.revision)
        if self._evaluation_repo is not None:
            completed_eval = self._evaluation_repo.get_completed_evaluation_for_answer(
                latest_answer.ref
            )
            if completed_eval is None:
                raise InvalidSessionStateError(
                    "Cannot advance until the current question's evaluation has completed."
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
        updated = replace(
            session,
            state=SessionState.ENDED_EARLY,
            updated_at=datetime.now(UTC),
        )
        return self._session_repo.update_session(updated)

    def _build_snapshot(self, session: Session) -> SessionSnapshot:
        all_answers = self._session_repo.list_answers_for_session(session.id)
        latest_by_q: dict[VersionedRef[QuestionId], Answer] = {}
        for ans in all_answers:
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
