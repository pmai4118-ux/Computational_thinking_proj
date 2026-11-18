"""
SQLite repository implementation (Task F04).
All SQL queries live strictly inside this module using parameterized statements
and atomic transactions.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from source.Model.evaluation import (
    CompleteEvaluationReport,
    CriterionStatus,
    EvidenceType,
    RubricEvaluationResult,
    RubricResultStatus,
    StructuredFeedback,
    VerifiedCriterionCheck,
    VerifiedEvidence,
)
from source.Model.ids import (
    AnswerId,
    AnswerRef,
    CriterionId,
    EvaluationId,
    QuestionId,
    QuestionRef,
    RubricId,
    RubricRef,
    SessionId,
)
from source.Model.interview import Answer, InterviewSession, SessionState
from source.Model.question import (
    CompetencyRubric,
    ExecutableCriterion,
    ExecutableScoreLevel,
)
from source.Model.repositories.interfaces import EvaluationRepository, SessionRepository


class StorageFailureError(Exception):
    """Storage failure in repository layer."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "STORAGE_FAILURE"
        self.message = message
        self.retryable = True
        self.field_errors: dict[str, str] = {}

    def to_envelope(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


storage_failure_error = StorageFailureError

SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"


class SQLiteRepository(EvaluationRepository, SessionRepository):
    """Unified SQLite persistence for sessions, immutable answers, and evaluation reports."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        self.initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        """Create a SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize_schema(self) -> None:
        """Apply schema.sql idempotently on startup."""
        try:
            ddl = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
            with self._connect() as conn:
                conn.executescript(ddl)
        except (OSError, sqlite3.Error) as exc:
            raise storage_failure_error(
                f"Kh\xf4ng th\u1ec3 kh\u1edfi t\u1ea1o c\u01a1 s\u1edf d\u1eef li\u1ec7u SQLite: {exc}"
            ) from exc

    # -----------------------------------------------------------------------
    # SessionRepository Operations
    # -----------------------------------------------------------------------

    def create_session(self, session: InterviewSession) -> InterviewSession:
        """Persist a new InterviewSession atomically."""
        q_refs = [
            {"id": str(ref.id), "version": ref.version}
            for ref in session.question_refs
        ]
        a_refs = [
            {"id": str(ref.id), "revision": ref.revision}
            for ref in session.answer_refs
        ]
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO interview_sessions (
                        session_id, owner_token_hash, role, level, state,
                        question_refs_json, current_index, answer_refs_json,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(session.id),
                        session.owner_token_hash,
                        session.role,
                        session.level,
                        session.state.value,
                        json.dumps(q_refs, ensure_ascii=False),
                        session.current_index,
                        json.dumps(a_refs, ensure_ascii=False),
                        session.created_at,
                        session.updated_at,
                    ),
                )
            return session
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i l\u01b0u phi\xean luy\u1ec7n t\u1eadp m\u1edbi: {exc}") from exc

    def get_session(self, session_id: SessionId) -> InterviewSession | None:
        """Read an InterviewSession by ID."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM interview_sessions WHERE session_id = ?",
                    (str(session_id),),
                ).fetchone()
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i \u0111\u1ecdc phi\xean luy\u1ec7n t\u1eadp: {exc}") from exc

        if row is None:
            return None

        raw_q_refs = json.loads(row["question_refs_json"])
        raw_a_refs = json.loads(row["answer_refs_json"])

        return InterviewSession(
            id=SessionId(row["session_id"]),
            owner_token_hash=row["owner_token_hash"],
            role=row["role"],
            level=row["level"],
            state=SessionState(row["state"]),
            question_refs=tuple(
                QuestionRef(id=QuestionId(item["id"]), version=int(item["version"]))
                for item in raw_q_refs
            ),
            current_index=int(row["current_index"]),
            answer_refs=tuple(
                AnswerRef(id=AnswerId(item["id"]), revision=int(item["revision"]))
                for item in raw_a_refs
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def update_session(self, session: InterviewSession) -> InterviewSession:
        """Update mutable session state fields inside a transaction."""
        q_refs = [
            {"id": str(ref.id), "version": ref.version}
            for ref in session.question_refs
        ]
        a_refs = [
            {"id": str(ref.id), "revision": ref.revision}
            for ref in session.answer_refs
        ]
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    UPDATE interview_sessions
                    SET state = ?, question_refs_json = ?, current_index = ?,
                        answer_refs_json = ?, updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        session.state.value,
                        json.dumps(q_refs, ensure_ascii=False),
                        session.current_index,
                        json.dumps(a_refs, ensure_ascii=False),
                        session.updated_at,
                        str(session.id),
                    ),
                )
                if cursor.rowcount == 0:
                    raise storage_failure_error(
                        f"Kh\xf4ng t\xecm th\u1ea5y phi\xean '{session.id}' \u0111\u1ec3 c\u1eadp nh\u1eadt."
                    )
            return session
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i c\u1eadp nh\u1eadt phi\xean luy\u1ec7n t\u1eadp: {exc}") from exc

    def save_answer(self, answer: Answer) -> Answer:
        """
        Save an immutable Answer revision.
        If (session_id, client_submission_id) was already saved, return that Answer idempotently.
        """
        try:
            with self._connect() as conn:
                if answer.client_submission_id:
                    existing_row = conn.execute(
                        """
                        SELECT * FROM answers
                        WHERE session_id = ? AND client_submission_id = ?
                        """,
                        (str(answer.session_id), answer.client_submission_id),
                    ).fetchone()
                    if existing_row is not None:
                        return self._row_to_answer(existing_row)

                conn.execute(
                    """
                    INSERT INTO answers (
                        answer_id, revision, session_id, question_id, question_version,
                        original_text, submitted_at, client_submission_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(answer.id),
                        answer.revision,
                        str(answer.session_id),
                        str(answer.question_ref.id),
                        answer.question_ref.version,
                        answer.text,
                        answer.submitted_at,
                        answer.client_submission_id,
                    ),
                )
            return answer
        except sqlite3.IntegrityError:
            if answer.client_submission_id:
                with self._connect() as conn:
                    row = conn.execute(
                        """
                        SELECT * FROM answers
                        WHERE session_id = ? AND client_submission_id = ?
                        """,
                        (str(answer.session_id), answer.client_submission_id),
                    ).fetchone()
                    if row is not None:
                        return self._row_to_answer(row)
            raise storage_failure_error(
                f"B\u1ea3n ghi c\xe2u tr\u1ea3 l\u1eddi '{answer.id}' (revision {answer.revision}) \u0111\xe3 t\u1ed3n t\u1ea1i."
            )
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i l\u01b0u c\xe2u tr\u1ea3 l\u1eddi v\xe0o SQLite: {exc}") from exc

    def get_answer(
        self,
        answer_id: AnswerId,
        revision: int | None = None,
    ) -> Answer | None:
        """Retrieve a specific answer revision or the latest revision when revision is None."""
        try:
            with self._connect() as conn:
                if revision is not None:
                    row = conn.execute(
                        """
                        SELECT * FROM answers
                        WHERE answer_id = ? AND revision = ?
                        """,
                        (str(answer_id), revision),
                    ).fetchone()
                else:
                    row = conn.execute(
                        """
                        SELECT * FROM answers
                        WHERE answer_id = ?
                        ORDER BY revision DESC
                        LIMIT 1
                        """,
                        (str(answer_id),),
                    ).fetchone()
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i \u0111\u1ecdc c\xe2u tr\u1ea3 l\u1eddi t\u1eeb SQLite: {exc}") from exc

        return self._row_to_answer(row) if row is not None else None

    @staticmethod
    def _row_to_answer(row: sqlite3.Row) -> Answer:
        return Answer(
            id=AnswerId(row["answer_id"]),
            revision=int(row["revision"]),
            session_id=SessionId(row["session_id"]),
            question_ref=QuestionRef(
                id=QuestionId(row["question_id"]),
                version=int(row["question_version"]),
            ),
            text=row["original_text"],
            submitted_at=row["submitted_at"],
            client_submission_id=row["client_submission_id"],
        )

    # -----------------------------------------------------------------------
    # EvaluationRepository Operations
    # -----------------------------------------------------------------------

    def find_by_input_digest(self, input_digest: str) -> CompleteEvaluationReport | None:
        """Find a stored evaluation report by its canonical SHA-256 input digest."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT report_json FROM evaluation_reports WHERE input_digest = ?",
                    (input_digest,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i tra c\u1ee9u b\xe1o c\xe1o theo input_digest: {exc}") from exc

        if row is None:
            return None
        return self._deserialize_report(row["report_json"])

    def find_by_answer_ref(self, answer_ref: AnswerRef) -> CompleteEvaluationReport | None:
        """Find the latest completed report for a given AnswerRef."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT report_json FROM evaluation_reports
                    WHERE answer_id = ? AND answer_revision = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (str(answer_ref.id), answer_ref.revision),
                ).fetchone()
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i tra c\u1ee9u b\xe1o c\xe1o theo answer_ref: {exc}") from exc

        if row is None:
            return None
        return self._deserialize_report(row["report_json"])

    def find_by_id(self, evaluation_id: EvaluationId) -> CompleteEvaluationReport | None:
        """Find a stored evaluation report by its EvaluationId."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT report_json FROM evaluation_reports WHERE evaluation_id = ?",
                    (str(evaluation_id),),
                ).fetchone()
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i tra c\u1ee9u b\xe1o c\xe1o theo evaluation_id: {exc}") from exc

        if row is None:
            return None
        return self._deserialize_report(row["report_json"])

    def save_report(self, report: CompleteEvaluationReport) -> CompleteEvaluationReport:
        """
        Atomically persist a CompleteEvaluationReport.
        If a report with the same input_digest was inserted concurrently, return the stored report.
        """
        serialized = json.dumps(asdict(report), ensure_ascii=False)
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO evaluation_reports (
                        evaluation_id, input_digest, answer_id, answer_revision,
                        question_id, question_version, provider_name, model_name,
                        prompt_version, created_at, report_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(report.evaluation_id),
                        report.input_digest,
                        str(report.answer_ref.id),
                        report.answer_ref.revision,
                        str(report.question_ref.id),
                        report.question_ref.version,
                        report.provider_name,
                        report.model_name,
                        report.prompt_version,
                        report.created_at,
                        serialized,
                    ),
                )
            return report
        except sqlite3.IntegrityError:
            existing = self.find_by_input_digest(report.input_digest)
            if existing is not None:
                return existing
            raise storage_failure_error(
                f"B\xe1o c\xe1o \u0111\xe1nh gi\xe1 '{report.evaluation_id}' b\u1ecb xung \u0111\u1ed9t kh\xf3a khi l\u01b0u."
            )
        except sqlite3.Error as exc:
            raise storage_failure_error(f"L\u1ed7i l\u01b0u b\xe1o c\xe1o \u0111\xe1nh gi\xe1 v\xe0o SQLite: {exc}") from exc

    @staticmethod
    def _deserialize_report(raw_json: str) -> CompleteEvaluationReport:
        """Reconstruct CompleteEvaluationReport from its serialized JSON representation."""
        data = json.loads(raw_json)
        question_ref = QuestionRef(
            id=QuestionId(data["question_ref"]["id"]),
            version=int(data["question_ref"]["version"]),
        )
        answer_ref = AnswerRef(
            id=AnswerId(data["answer_ref"]["id"]),
            version_or_rev = int(data["answer_ref"]["revision"]),
        )

        rubrics = tuple(
            CompetencyRubric(
                id=RubricId(r["id"]),
                version=int(r["version"]),
                competency=r["competency"],
                review_rule=r["review_rule"],
                scoring_rule=r["scoring_rule"],
                criteria=tuple(
                    ExecutableCriterion(
                        id=CriterionId(c["id"]),
                        label=c["label"],
                        acceptance_rule=c["acceptance_rule"],
                        omission_means_unmet=bool(c["omission_means_unmet"]),
                    )
                    for c in r["criteria"]
                ),
                score_levels=tuple(
                    ExecutableScoreLevel(
                        value=int(lvl["value"]),
                        description=lvl["description"],
                        condition=lvl["condition"],
                        required_met=tuple(CriterionId(cid) for cid in lvl["required_met"]),
                        minimum_met=int(lvl["minimum_met"]),
                    )
                    for lvl in r["score_levels"]
                ),
            )
            for r in data["rubrics"]
        )

        results = tuple(
            RubricEvaluationResult(
                result_id=res["result_id"],
                rubric_ref=RubricRef(
                    id=RubricId(res["rubric_ref"]["id"]),
                    version=int(res["rubric_ref"]["version"]),
                ),
                competency=res["competency"],
                status=RubricResultStatus(res["status"]),
                score=res["score"] if res["score"] is not None else None,
                maximum_score=int(res["maximum_score"]),
                reason=res["reason"],
                criterion_checks=tuple(
                    VerifiedCriterionCheck(
                        criterion_id=CriterionId(chk["criterion_id"]),
                        status=CriterionStatus(chk["status"]),
                        evidence=tuple(
                            VerifiedEvidence(
                                answer_ref=AnswerRef(
                                    id=AnswerId(ev["answer_ref"]["id"]),
                                    revision=int(ev["answer_ref"]["revision"]),
                                ),
                                evidence_type=EvidenceType(ev["evidence_type"]),
                                observation=ev["observation"],
                                location=ev["location"],
                                quote=ev["quote"],
                                start_offset=ev["start_offset"],
                                end_offset=ev["end_offset"],
                            )
                            for ev in chk["evidence"]
                        ),
                    )
                    for chk in res["criterion_checks"]
                ),
            )
            for res in data["results"]
        )

        feedback_items = tuple(
            StructuredFeedback(
                result_id=fb["result_id"],
                rubric_ref=RubricRef(
                    id=RubricId(fb["rubric_ref"]["id"]),
                    version=int(fb["rubric_ref"]["version"]),
                ),
                competency=fb["competency"],
                status=RubricResultStatus(fb["status"]),
                score=fb["score"] if fb["score"] is not None else None,
                explanation=fb["explanation"],
                identified_issues=tuple(fb["identified_issues"]),
            )
            for fb in data["feedback_items"]
        )

        return CompleteEvaluationReport(
            evaluation_id=EvaluationId(data["evaluation_id"]),
            schema_version=data["schema_version"],
            input_digest=data["input_digest"],
            question_ref=question_ref,
            question_prompt=data["question_prompt"],
            requirements=tuple(data["requirements"]),
            context=data["context"],
            rubrics=rubrics,
            answer_ref=answer_ref,
            answer_text=data["answer_text"],
            example_only=bool(data["example_only"]),
            provider_name=data["provider_name"],
            model_name=data["model_name"],
            prompt_version=data["prompt_version"],
            created_at=data["created_at"],
            results=results,
            feedback_items=feedback_items,
        )