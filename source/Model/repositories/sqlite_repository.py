"""Versioned SQLite repository implementing Content, Session, and Evaluation protocols (F04)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from source.Model.evaluation import (
    AnswerRevisionRef,
    CriterionCheck,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
    Evidence,
)
from source.Model.exercise import Exercise
from source.Model.ids import (
    AnswerId,
    CriterionId,
    EvaluationId,
    ExerciseId,
    QuestionId,
    RubricId,
    SessionId,
    SkillId,
    SourceId,
    VersionedRef,
)
from source.Model.interview import Answer, Session, SessionState
from source.Model.question import (
    Criterion,
    CriterionLevel,
    LicenseStatus,
    Question,
    ReviewChecks,
    ReviewMetadata,
    ReviewStatus,
    Rubric,
    Skill,
    SourceMetadata,
)
from source.Model.repositories.interfaces import (
    DuplicateRecordError,
    DuplicateSubmissionConflictError,
    RecordNotFoundError,
    RepositoryError,
)

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _dt_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat()
    return value.astimezone(UTC).isoformat()


def _iso_to_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _serialize_review(review: ReviewMetadata) -> str:
    return json.dumps(
        {
            "status": review.status.value,
            "curator_id": review.curator_id,
            "reviewer_id": review.reviewer_id,
            "reviewed_at": _dt_to_iso(review.reviewed_at),
            "checks": {
                "source_and_license_verified": review.checks.source_and_license_verified,
                "original_and_adaptation_preserved": review.checks.original_and_adaptation_preserved,
                "technical_correctness_checked": review.checks.technical_correctness_checked,
                "rubric_levels_distinct": review.checks.rubric_levels_distinct,
                "equivalent_answers_checked": review.checks.equivalent_answers_checked,
                "review_cases_checked": review.checks.review_cases_checked,
            },
        },
        ensure_ascii=False,
    )


def _deserialize_review(raw: str) -> ReviewMetadata:
    data = json.loads(raw)
    checks_data = data.get("checks") or {}
    return ReviewMetadata(
        status=ReviewStatus(data["status"]),
        curator_id=data.get("curator_id"),
        reviewer_id=data.get("reviewer_id"),
        reviewed_at=_iso_to_dt(data.get("reviewed_at")),
        checks=ReviewChecks(
            source_and_license_verified=checks_data.get("source_and_license_verified"),
            original_and_adaptation_preserved=checks_data.get("original_and_adaptation_preserved"),
            technical_correctness_checked=checks_data.get("technical_correctness_checked"),
            rubric_levels_distinct=checks_data.get("rubric_levels_distinct"),
            equivalent_answers_checked=checks_data.get("equivalent_answers_checked"),
            review_cases_checked=checks_data.get("review_cases_checked"),
        ),
    )


class SQLiteRepositoryStore:
    """SQLite-backed persistence store with parameterized SQL and atomic transactions."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        ddl = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connect() as conn:
            with conn:
                conn.executescript(ddl)
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                    (SCHEMA_VERSION, _dt_to_iso(datetime.now(UTC))),
                )

    # ContentRepository
    def save_skill(self, skill: Skill) -> None:
        with self._connect() as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO skills (id, label, description) VALUES (?, ?, ?);",
                (skill.id, skill.label, skill.description),
            )

    def list_skills(self) -> tuple[Skill, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, label, description FROM skills ORDER BY id;"
            ).fetchall()
        return tuple(
            Skill(id=SkillId(row["id"]), label=row["label"], description=row["description"])
            for row in rows
        )

    def save_source(self, source: SourceMetadata) -> None:
        with self._connect() as conn, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sources (
                    id, url, revision, author, license_identifier, license_url,
                    license_status, collected_at, required_notice
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    source.id,
                    source.url,
                    source.revision,
                    source.author,
                    source.license_identifier,
                    source.license_url,
                    source.license_status.value,
                    _dt_to_iso(source.collected_at),
                    source.required_notice,
                ),
            )

    def get_source(self, source_id: SourceId) -> SourceMetadata | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sources WHERE id = ?;", (source_id,)
            ).fetchone()
        if row is None:
            return None
        return SourceMetadata(
            id=SourceId(row["id"]),
            url=row["url"],
            revision=row["revision"],
            author=row["author"],
            license_identifier=row["license_identifier"],
            license_url=row["license_url"],
            license_status=LicenseStatus(row["license_status"]),
            collected_at=_iso_to_dt(row["collected_at"]),
            required_notice=row["required_notice"],
        )

    def save_rubric(self, rubric: Rubric) -> None:
        existing = self.get_rubric(VersionedRef(rubric.id, rubric.version))
        if existing is not None:
            if existing == rubric:
                return
            raise DuplicateRecordError(
                f"Rubric ({rubric.id}, {rubric.version}) already exists with different content."
            )
        criteria_json = json.dumps(
            [
                {
                    "id": crit.id,
                    "label": crit.label,
                    "expected_evidence": list(crit.expected_evidence),
                    "levels": [
                        {"score": lvl.score, "description": lvl.description}
                        for lvl in crit.levels
                    ],
                    "equivalent_answers_note": crit.equivalent_answers_note,
                    "criterion_type": crit.criterion_type,
                }
                for crit in rubric.criteria
            ],
            ensure_ascii=False,
        )
        with self._connect() as conn, conn:
            conn.execute(
                "INSERT INTO rubrics (id, version, criteria_json, review_json) VALUES (?, ?, ?, ?);",
                (rubric.id, rubric.version, criteria_json, _serialize_review(rubric.review)),
            )

    def get_rubric(self, ref: VersionedRef[RubricId]) -> Rubric | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM rubrics WHERE id = ? AND version = ?;",
                (ref.id, ref.version),
            ).fetchone()
        if row is None:
            return None
        raw_criteria = json.loads(row["criteria_json"])
        criteria = tuple(
            Criterion(
                id=CriterionId(item["id"]),
                label=item["label"],
                expected_evidence=tuple(item["expected_evidence"]),
                levels=tuple(
                    CriterionLevel(score=lvl["score"], description=lvl["description"])
                    for lvl in item["levels"]
                ),
                equivalent_answers_note=item.get("equivalent_answers_note"),
                criterion_type=item.get("criterion_type"),
            )
            for item in raw_criteria
        )
        return Rubric(
            id=RubricId(row["id"]),
            version=int(row["version"]),
            criteria=criteria,
            review=_deserialize_review(row["review_json"]),
        )

    def save_question(self, question: Question) -> None:
        existing = self.get_question(question.ref)
        if existing is not None:
            if existing == question:
                return
            raise DuplicateRecordError(
                f"Question ({question.id}, {question.version}) already exists with different content."
            )
        try:
            with self._connect() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO questions (
                        id, version, category, language, role, level, difficulty, prompt,
                        skill_ids_json, rubric_id, rubric_version, source_id, review_status,
                        review_json, original_content, adaptation_note, code, code_language,
                        constraints_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        question.id,
                        question.version,
                        question.category,
                        question.language,
                        question.role,
                        question.level,
                        question.difficulty,
                        question.prompt,
                        json.dumps(list(question.skill_ids), ensure_ascii=False),
                        question.rubric_ref.id,
                        question.rubric_ref.version,
                        question.source_id,
                        question.review.status.value,
                        _serialize_review(question.review),
                        question.original_content,
                        question.adaptation_note,
                        question.code,
                        question.code_language,
                        json.dumps(list(question.constraints), ensure_ascii=False),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist Question {question.id}: {error}") from error

    @staticmethod
    def _row_to_question(row: sqlite3.Row) -> Question:
        return Question(
            id=QuestionId(row["id"]),
            version=int(row["version"]),
            category=row["category"],
            language=row["language"],
            role=row["role"],
            level=row["level"],
            difficulty=row["difficulty"],
            prompt=row["prompt"],
            skill_ids=tuple(SkillId(s) for s in json.loads(row["skill_ids_json"])),
            rubric_ref=VersionedRef(RubricId(row["rubric_id"]), int(row["rubric_version"])),
            source_id=SourceId(row["source_id"]),
            review=_deserialize_review(row["review_json"]),
            original_content=row["original_content"],
            adaptation_note=row["adaptation_note"],
            code=row["code"],
            code_language=row["code_language"],
            constraints=tuple(json.loads(row["constraints_json"])),
        )

    def get_question(self, ref: VersionedRef[QuestionId]) -> Question | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM questions WHERE id = ? AND version = ?;",
                (ref.id, ref.version),
            ).fetchone()
        return None if row is None else self._row_to_question(row)

    def list_approved_questions(
        self,
        *,
        role: str,
        level: str,
        language: str,
    ) -> tuple[Question, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT q.*
                FROM questions q
                JOIN sources s ON s.id = q.source_id
                WHERE q.role = ?
                  AND q.level = ?
                  AND q.language = ?
                  AND q.review_status = ?
                  AND s.license_status = ?
                ORDER BY q.id ASC, q.version DESC;
                """,
                (
                    role,
                    level,
                    language,
                    ReviewStatus.APPROVED.value,
                    LicenseStatus.VERIFIED.value,
                ),
            ).fetchall()
        latest_by_id: dict[QuestionId, Question] = {}
        for row in rows:
            q = self._row_to_question(row)
            if q.id not in latest_by_id:
                latest_by_id[q.id] = q
        return tuple(latest_by_id.values())

    def save_exercise(self, exercise: Exercise) -> None:
        existing = self.get_exercise(exercise.ref)
        if existing is not None:
            if existing == exercise:
                return
            raise DuplicateRecordError(
                f"Exercise ({exercise.id}, {exercise.version}) already exists with different content."
            )
        try:
            with self._connect() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO exercises (
                        id, version, title, summary, instructions, related_skill_ids_json,
                        prerequisite_ids_json, target_criterion_types_json,
                        estimated_duration_minutes, observable_outcome, source_id,
                        review_status, review_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        exercise.id,
                        exercise.version,
                        exercise.title,
                        exercise.summary,
                        exercise.instructions,
                        json.dumps(list(exercise.related_skill_ids), ensure_ascii=False),
                        json.dumps(list(exercise.prerequisite_ids), ensure_ascii=False),
                        json.dumps(list(exercise.target_criterion_types), ensure_ascii=False),
                        exercise.estimated_duration_minutes,
                        exercise.observable_outcome,
                        exercise.source_id,
                        exercise.review.status.value,
                        _serialize_review(exercise.review),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist Exercise {exercise.id}: {error}") from error

    @staticmethod
    def _row_to_exercise(row: sqlite3.Row) -> Exercise:
        return Exercise(
            id=ExerciseId(row["id"]),
            version=int(row["version"]),
            title=row["title"],
            summary=row["summary"],
            instructions=row["instructions"],
            related_skill_ids=tuple(
                SkillId(s) for s in json.loads(row["related_skill_ids_json"])
            ),
            prerequisite_ids=tuple(
                ExerciseId(e) for e in json.loads(row["prerequisite_ids_json"])
            ),
            target_criterion_types=tuple(json.loads(row["target_criterion_types_json"])),
            estimated_duration_minutes=row["estimated_duration_minutes"],
            observable_outcome=row["observable_outcome"],
            source_id=SourceId(row["source_id"]),
            review=_deserialize_review(row["review_json"]),
        )

    def get_exercise(self, ref: VersionedRef[ExerciseId]) -> Exercise | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM exercises WHERE id = ? AND version = ?;",
                (ref.id, ref.version),
            ).fetchone()
        return None if row is None else self._row_to_exercise(row)

    def list_approved_exercises(self) -> tuple[Exercise, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.*
                FROM exercises e
                JOIN sources s ON s.id = e.source_id
                WHERE e.review_status = ?
                  AND s.license_status = ?
                ORDER BY e.id ASC, e.version DESC;
                """,
                (ReviewStatus.APPROVED.value, LicenseStatus.VERIFIED.value),
            ).fetchall()
        latest_by_id: dict[ExerciseId, Exercise] = {}
        for row in rows:
            ex = self._row_to_exercise(row)
            if ex.id not in latest_by_id:
                latest_by_id[ex.id] = ex
        return tuple(latest_by_id.values())

    # SessionRepository
    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> Session:
        q_refs = tuple(
            VersionedRef(QuestionId(item["id"]), int(item["version"]))
            for item in json.loads(row["question_refs_json"])
        )
        a_refs = tuple(
            AnswerRevisionRef(AnswerId(item["id"]), int(item["revision"]))
            for item in json.loads(row["answer_refs_json"])
        )
        return Session(
            id=SessionId(row["id"]),
            owner_token_hash=row["owner_token_hash"],
            role=row["role"],
            level=row["level"],
            language=row["language"],
            state=SessionState(row["state"]),
            question_refs=q_refs,
            current_index=int(row["current_index"]),
            answer_refs=a_refs,
            created_at=_iso_to_dt(row["created_at"]),
            updated_at=_iso_to_dt(row["updated_at"]),
        )

    def create_session(self, session: Session) -> Session:
        q_json = json.dumps(
            [{"id": r.id, "version": r.version} for r in session.question_refs],
            ensure_ascii=False,
        )
        a_json = json.dumps(
            [{"id": r.id, "revision": r.revision} for r in session.answer_refs],
            ensure_ascii=False,
        )
        try:
            with self._connect() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        id, owner_token_hash, role, level, language, state,
                        question_refs_json, current_index, answer_refs_json,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        session.id,
                        session.owner_token_hash,
                        session.role,
                        session.level,
                        session.language,
                        session.state.value,
                        q_json,
                        session.current_index,
                        a_json,
                        _dt_to_iso(session.created_at),
                        _dt_to_iso(session.updated_at),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError(f"Session {session.id} already exists.") from error
        return session

    def get_session(self, session_id: SessionId) -> Session | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?;", (session_id,)
            ).fetchone()
        return None if row is None else self._row_to_session(row)

    def list_sessions_by_owner(self, owner_token_hash: str) -> tuple[Session, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE owner_token_hash = ? ORDER BY created_at DESC, id DESC;",
                (owner_token_hash,),
            ).fetchall()
        return tuple(self._row_to_session(row) for row in rows)

    def update_session(self, session: Session) -> Session:
        q_json = json.dumps(
            [{"id": r.id, "version": r.version} for r in session.question_refs],
            ensure_ascii=False,
        )
        a_json = json.dumps(
            [{"id": r.id, "revision": r.revision} for r in session.answer_refs],
            ensure_ascii=False,
        )
        with self._connect() as conn, conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET owner_token_hash = ?,
                    role = ?,
                    level = ?,
                    language = ?,
                    state = ?,
                    question_refs_json = ?,
                    current_index = ?,
                    answer_refs_json = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    session.owner_token_hash,
                    session.role,
                    session.level,
                    session.language,
                    session.state.value,
                    q_json,
                    session.current_index,
                    a_json,
                    _dt_to_iso(session.updated_at),
                    session.id,
                ),
            )
            if cursor.rowcount == 0:
                raise RecordNotFoundError(f"Session {session.id} does not exist.")
        return session

    @staticmethod
    def _row_to_answer(row: sqlite3.Row) -> Answer:
        submitted_at = _iso_to_dt(row["submitted_at"])
        assert submitted_at is not None
        return Answer(
            id=AnswerId(row["id"]),
            revision=int(row["revision"]),
            session_id=SessionId(row["session_id"]),
            question_ref=VersionedRef(
                QuestionId(row["question_id"]), int(row["question_version"])
            ),
            rubric_ref=VersionedRef(
                RubricId(row["rubric_id"]), int(row["rubric_version"])
            ),
            text=row["text"],
            submitted_at=submitted_at,
            client_submission_id=row["client_submission_id"],
        )

    def save_answer(self, answer: Answer) -> tuple[Answer, bool]:
        with self._connect() as conn:
            try:
                with conn:
                    # Reserve SQLite's single-writer slot before checking idempotency;
                    # otherwise concurrent retries can both observe no saved answer.
                    conn.execute("BEGIN IMMEDIATE;")
                    session_row = conn.execute(
                        "SELECT * FROM sessions WHERE id = ?;", (answer.session_id,)
                    ).fetchone()
                    if session_row is None:
                        raise RecordNotFoundError(
                            f"Session {answer.session_id} does not exist."
                        )
                    session = self._row_to_session(session_row)

                    if answer.client_submission_id is not None:
                        sub_row = conn.execute(
                            """
                            SELECT * FROM answers
                            WHERE session_id = ? AND client_submission_id = ?;
                            """,
                            (answer.session_id, answer.client_submission_id),
                        ).fetchone()
                        if sub_row is not None:
                            existing = self._row_to_answer(sub_row)
                            if (
                                existing.question_ref == answer.question_ref
                                and existing.text == answer.text
                            ):
                                return existing, True
                            raise DuplicateSubmissionConflictError(
                                "client_submission_id already bound to different answer content.",
                                existing_answer=existing,
                            )

                    id_row = conn.execute(
                        "SELECT * FROM answers WHERE id = ? AND revision = ?;",
                        (answer.id, answer.revision),
                    ).fetchone()
                    if id_row is not None:
                        existing = self._row_to_answer(id_row)
                        if existing == answer:
                            return existing, True
                        raise DuplicateRecordError(
                            f"Answer ({answer.id}, {answer.revision}) already exists with different content."
                        )

                    conn.execute(
                        """
                        INSERT INTO answers (
                            id, revision, session_id, question_id, question_version,
                            rubric_id, rubric_version, text, submitted_at, client_submission_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            answer.id,
                            answer.revision,
                            answer.session_id,
                            answer.question_ref.id,
                            answer.question_ref.version,
                            answer.rubric_ref.id,
                            answer.rubric_ref.version,
                            answer.text,
                            _dt_to_iso(answer.submitted_at),
                            answer.client_submission_id,
                        ),
                    )
                    if answer.ref not in session.answer_refs:
                        updated_session = replace(
                            session,
                            answer_refs=(*session.answer_refs, answer.ref),
                            updated_at=answer.submitted_at,
                        )
                        a_json = json.dumps(
                            [
                                {"id": r.id, "revision": r.revision}
                                for r in updated_session.answer_refs
                            ],
                            ensure_ascii=False,
                        )
                        conn.execute(
                            "UPDATE sessions SET answer_refs_json = ?, updated_at = ? WHERE id = ?;",
                            (a_json, _dt_to_iso(updated_session.updated_at), session.id),
                        )
                    return answer, False
            except sqlite3.IntegrityError as error:
                raise RepositoryError(f"Cannot persist Answer {answer.id}: {error}") from error

    def get_answer(self, ref: AnswerRevisionRef) -> Answer | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM answers WHERE id = ? AND revision = ?;",
                (ref.id, ref.revision),
            ).fetchone()
        return None if row is None else self._row_to_answer(row)

    def get_latest_answer(self, answer_id: AnswerId) -> Answer | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM answers WHERE id = ? ORDER BY revision DESC LIMIT 1;",
                (answer_id,),
            ).fetchone()
        return None if row is None else self._row_to_answer(row)

    def list_answers_for_session(self, session_id: SessionId) -> tuple[Answer, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM answers WHERE session_id = ? ORDER BY submitted_at ASC, id ASC, revision ASC;",
                (session_id,),
            ).fetchall()
        return tuple(self._row_to_answer(row) for row in rows)

    # EvaluationRepository
    def save_evaluation(self, result: EvaluationResult) -> EvaluationResult:
        existing = self.get_evaluation(result.id, result.version)
        if existing is not None:
            if existing == result:
                return existing
            raise DuplicateRecordError(
                f"Evaluation ({result.id}, {result.version}) already exists with different content."
            )
        try:
            with self._connect() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO evaluations (
                        id, version, status, answer_id, answer_revision,
                        question_id, question_version, rubric_id, rubric_version,
                        total_score, maximum_score, failure_code, failure_message,
                        evaluated_at, prompt_version, model_id, demo_mode_label
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        result.id,
                        result.version,
                        result.status.value,
                        result.answer_ref.id,
                        result.answer_ref.revision,
                        result.question_ref.id,
                        result.question_ref.version,
                        result.rubric_ref.id,
                        result.rubric_ref.version,
                        result.total_score,
                        result.maximum_score,
                        result.failure_code,
                        result.failure_message,
                        _dt_to_iso(result.evaluated_at),
                        result.prompt_version,
                        result.model_id,
                        result.demo_mode_label,
                    ),
                )
                for index, check in enumerate(result.criterion_checks):
                    evidence_json = json.dumps(
                        [
                            {
                                "answer_id": ev.answer_ref.id,
                                "answer_revision": ev.answer_ref.revision,
                                "quote": ev.quote,
                                "start_offset": ev.start_offset,
                                "end_offset": ev.end_offset,
                                "observation": ev.observation,
                            }
                            for ev in check.evidence
                        ],
                        ensure_ascii=False,
                    )
                    conn.execute(
                        """
                        INSERT INTO evaluation_criterion_checks (
                            evaluation_id, evaluation_version, position, criterion_id,
                            status, score, evidence_json, explanation, unresolved_reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            result.id,
                            result.version,
                            index,
                            check.criterion_id,
                            check.status.value,
                            check.score,
                            evidence_json,
                            check.explanation,
                            check.unresolved_reason,
                        ),
                    )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist Evaluation {result.id}: {error}") from error
        return result

    def _load_evaluation_from_row(
        self,
        conn: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> EvaluationResult:
        check_rows = conn.execute(
            """
            SELECT * FROM evaluation_criterion_checks
            WHERE evaluation_id = ? AND evaluation_version = ?
            ORDER BY position ASC;
            """,
            (row["id"], row["version"]),
        ).fetchall()
        checks = tuple(
            CriterionCheck(
                criterion_id=CriterionId(c_row["criterion_id"]),
                status=CriterionStatus(c_row["status"]),
                score=c_row["score"],
                evidence=tuple(
                    Evidence(
                        answer_ref=AnswerRevisionRef(
                            AnswerId(ev["answer_id"]), int(ev["answer_revision"])
                        ),
                        quote=ev["quote"],
                        start_offset=ev["start_offset"],
                        end_offset=ev["end_offset"],
                        observation=ev["observation"],
                    )
                    for ev in json.loads(c_row["evidence_json"])
                ),
                explanation=c_row["explanation"],
                unresolved_reason=c_row["unresolved_reason"],
            )
            for c_row in check_rows
        )
        return EvaluationResult(
            id=EvaluationId(row["id"]),
            version=int(row["version"]),
            status=EvaluationStatus(row["status"]),
            answer_ref=AnswerRevisionRef(
                AnswerId(row["answer_id"]), int(row["answer_revision"])
            ),
            question_ref=VersionedRef(
                QuestionId(row["question_id"]), int(row["question_version"])
            ),
            rubric_ref=VersionedRef(
                RubricId(row["rubric_id"]), int(row["rubric_version"])
            ),
            criterion_checks=checks,
            total_score=row["total_score"],
            maximum_score=row["maximum_score"],
            failure_code=row["failure_code"],
            failure_message=row["failure_message"],
            evaluated_at=_iso_to_dt(row["evaluated_at"]),
            prompt_version=row["prompt_version"],
            model_id=row["model_id"],
            demo_mode_label=row["demo_mode_label"],
        )

    def get_evaluation(
        self,
        evaluation_id: EvaluationId,
        version: int | None = None,
    ) -> EvaluationResult | None:
        with self._connect() as conn:
            if version is not None:
                row = conn.execute(
                    "SELECT * FROM evaluations WHERE id = ? AND version = ?;",
                    (evaluation_id, version),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM evaluations WHERE id = ? ORDER BY version DESC LIMIT 1;",
                    (evaluation_id,),
                ).fetchone()
            return None if row is None else self._load_evaluation_from_row(conn, row)

    def get_completed_evaluation_for_answer(
        self,
        answer_ref: AnswerRevisionRef,
    ) -> EvaluationResult | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM evaluations
                WHERE answer_id = ? AND answer_revision = ? AND status = ?
                ORDER BY version DESC LIMIT 1;
                """,
                (answer_ref.id, answer_ref.revision, EvaluationStatus.COMPLETED.value),
            ).fetchone()
            return None if row is None else self._load_evaluation_from_row(conn, row)

    def get_latest_evaluation_for_answer(
        self,
        answer_ref: AnswerRevisionRef,
    ) -> EvaluationResult | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM evaluations
                WHERE answer_id = ? AND answer_revision = ?
                ORDER BY version DESC LIMIT 1;
                """,
                (answer_ref.id, answer_ref.revision),
            ).fetchone()
            return None if row is None else self._load_evaluation_from_row(conn, row)


__all__ = ["SCHEMA_VERSION", "SQLiteRepositoryStore"]
