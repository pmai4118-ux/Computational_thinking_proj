"""Versioned SQLite repository implementing Content, Session, and Evaluation protocols (F04)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from source.Model.competency_profile import CompetencyProfileEntry, RecentCriterionScore
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
from source.Model.interview import Answer, EvaluationTiming, Session, SessionState
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
    EvaluationInProgressError,
    EvaluationRetryNotAllowedError,
    RecordNotFoundError,
    RepositoryError,
    RETRYABLE_EVALUATION_FAILURES,
)

SCHEMA_VERSION = 3
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
EVALUATION_LEASE = timedelta(minutes=15)


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
                columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions);")}
                if "evaluation_timing" not in columns:
                    conn.execute(
                        "ALTER TABLE sessions ADD COLUMN evaluation_timing TEXT NOT NULL DEFAULT 'per_question';"
                    )
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                    (SCHEMA_VERSION, _dt_to_iso(datetime.now(UTC))),
                )

    def import_seed_records(
        self, *, skills: tuple[Skill, ...], sources: tuple[SourceMetadata, ...],
        rubrics: tuple[Rubric, ...], questions: tuple[Question, ...],
        exercises: tuple[Exercise, ...],
    ) -> dict[str, int]:
        """Commit the validated catalog as one unit; reject changed versioned records."""
        inserted = {name: 0 for name in ("skills", "sources", "rubrics", "questions", "exercises")}
        try:
            with self._connect() as conn, conn:
                conn.execute("BEGIN IMMEDIATE;")
                for skill in skills:
                    if conn.execute("SELECT 1 FROM skills WHERE id=?;", (skill.id,)).fetchone() is None:
                        inserted["skills"] += 1
                    conn.execute(
                        """INSERT INTO skills (id, label, description) VALUES (?, ?, ?)
                           ON CONFLICT(id) DO UPDATE SET label=excluded.label,
                           description=excluded.description;""",
                        (skill.id, skill.label, skill.description),
                    )
                for source in sources:
                    if conn.execute("SELECT 1 FROM sources WHERE id=?;", (source.id,)).fetchone() is None:
                        inserted["sources"] += 1
                    conn.execute(
                        """INSERT INTO sources (
                             id, url, revision, author, license_identifier, license_url,
                             license_status, collected_at, required_notice
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(id) DO UPDATE SET
                             url=excluded.url, revision=excluded.revision,
                             author=excluded.author,
                             license_identifier=excluded.license_identifier,
                             license_url=excluded.license_url,
                             license_status=excluded.license_status,
                             collected_at=excluded.collected_at,
                             required_notice=excluded.required_notice;""",
                        (source.id, source.url, source.revision, source.author,
                         source.license_identifier, source.license_url,
                         source.license_status.value, _dt_to_iso(source.collected_at),
                         source.required_notice),
                    )
                for rubric in rubrics:
                    criteria_json = json.dumps([
                        {"id": criterion.id, "label": criterion.label,
                         "expected_evidence": list(criterion.expected_evidence),
                         "levels": [{"score": level.score, "description": level.description}
                                    for level in criterion.levels],
                         "equivalent_answers_note": criterion.equivalent_answers_note,
                         "criterion_type": criterion.criterion_type}
                        for criterion in rubric.criteria
                    ], ensure_ascii=False)
                    review_json = _serialize_review(rubric.review)
                    cursor = conn.execute(
                        """INSERT INTO rubrics (id, version, criteria_json, review_json)
                           VALUES (?, ?, ?, ?) ON CONFLICT(id, version) DO NOTHING;""",
                        (rubric.id, rubric.version, criteria_json, review_json),
                    )
                    inserted["rubrics"] += cursor.rowcount
                    row = conn.execute(
                        "SELECT criteria_json, review_json FROM rubrics WHERE id=? AND version=?;",
                        (rubric.id, rubric.version),
                    ).fetchone()
                    if (json.loads(row["criteria_json"]) != json.loads(criteria_json)
                            or json.loads(row["review_json"]) != json.loads(review_json)):
                        raise DuplicateRecordError(
                            f"Rubric ({rubric.id}, {rubric.version}) conflicts with existing content."
                        )
                for question in questions:
                    cursor = conn.execute(
                        """INSERT INTO questions (
                             id, version, category, language, role, level, difficulty,
                             prompt, skill_ids_json, rubric_id, rubric_version, source_id,
                             review_status, review_json, original_content, adaptation_note,
                             code, code_language, constraints_json
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(id, version) DO NOTHING;""",
                        (question.id, question.version, question.category, question.language,
                         question.role, question.level, question.difficulty, question.prompt,
                         json.dumps(list(question.skill_ids), ensure_ascii=False),
                         question.rubric_ref.id, question.rubric_ref.version,
                         question.source_id, question.review.status.value,
                         _serialize_review(question.review), question.original_content,
                         question.adaptation_note, question.code, question.code_language,
                         json.dumps(list(question.constraints), ensure_ascii=False)),
                    )
                    inserted["questions"] += cursor.rowcount
                    row = conn.execute(
                        "SELECT * FROM questions WHERE id=? AND version=?;",
                        (question.id, question.version),
                    ).fetchone()
                    if self._row_to_question(row) != question:
                        raise DuplicateRecordError(
                            f"Question ({question.id}, {question.version}) conflicts with existing content."
                        )
                for exercise in exercises:
                    cursor = conn.execute(
                        """INSERT INTO exercises (
                             id, version, title, summary, instructions,
                             related_skill_ids_json, prerequisite_ids_json,
                             target_criterion_types_json, estimated_duration_minutes,
                             observable_outcome, source_id, review_status, review_json
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(id, version) DO NOTHING;""",
                        (exercise.id, exercise.version, exercise.title, exercise.summary,
                         exercise.instructions,
                         json.dumps(list(exercise.related_skill_ids), ensure_ascii=False),
                         json.dumps(list(exercise.prerequisite_ids), ensure_ascii=False),
                         json.dumps(list(exercise.target_criterion_types), ensure_ascii=False),
                         exercise.estimated_duration_minutes, exercise.observable_outcome,
                         exercise.source_id, exercise.review.status.value,
                         _serialize_review(exercise.review)),
                    )
                    inserted["exercises"] += cursor.rowcount
                    row = conn.execute(
                        "SELECT * FROM exercises WHERE id=? AND version=?;",
                        (exercise.id, exercise.version),
                    ).fetchone()
                    if self._row_to_exercise(row) != exercise:
                        raise DuplicateRecordError(
                            f"Exercise ({exercise.id}, {exercise.version}) conflicts with existing content."
                        )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Atomic seed import failed: {error}") from error
        return inserted

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
            evaluation_timing=EvaluationTiming(row["evaluation_timing"]),
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
                        created_at, updated_at, evaluation_timing
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                        session.evaluation_timing.value,
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
                    updated_at = ?,
                    evaluation_timing = ?
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
                    session.evaluation_timing.value,
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
    def claim_evaluation(
        self, answer_ref: AnswerRevisionRef,
        question_ref: VersionedRef[QuestionId], rubric_ref: VersionedRef[RubricId],
    ) -> EvaluationResult:
        """Atomically reserve one attempt across threads and app processes."""
        now = datetime.now(UTC)
        with self._connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM evaluations WHERE answer_id=? AND answer_revision=? "
                "AND status='completed' ORDER BY version DESC LIMIT 1",
                (answer_ref.id, answer_ref.revision),
            ).fetchone()
            if row is not None:
                return self._load_evaluation_from_row(conn, row)
            row = conn.execute(
                "SELECT * FROM evaluations WHERE answer_id=? AND answer_revision=? "
                "ORDER BY version DESC LIMIT 1",
                (answer_ref.id, answer_ref.revision),
            ).fetchone()
            if row is not None and row["status"] == EvaluationStatus.PROCESSING.value:
                started = _iso_to_dt(row["evaluated_at"])
                if started is not None and now - started < EVALUATION_LEASE:
                    raise EvaluationInProgressError("Evaluation is already processing.")
                conn.execute(
                    "UPDATE evaluations SET status='failed', failure_code='EVALUATION_INTERRUPTED', "
                    "failure_message='The prior evaluation was interrupted.' "
                    "WHERE id=? AND version=? AND status='processing'",
                    (row["id"], row["version"]),
                )
            elif row is not None and row["status"] == EvaluationStatus.FAILED.value:
                if row["failure_code"] not in RETRYABLE_EVALUATION_FAILURES:
                    raise EvaluationRetryNotAllowedError("This evaluation failure cannot be retried.")
            claim = EvaluationResult(
                id=EvaluationId(row["id"] if row is not None else f"evaluation.{uuid4().hex[:12]}"),
                version=int(row["version"]) + 1 if row is not None else 1,
                status=EvaluationStatus.PROCESSING,
                answer_ref=answer_ref,
                question_ref=question_ref,
                rubric_ref=rubric_ref,
                evaluated_at=now,
            )
            conn.execute(
                "INSERT INTO evaluations (id, version, status, answer_id, answer_revision, "
                "question_id, question_version, rubric_id, rubric_version, evaluated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (claim.id, claim.version, claim.status.value, answer_ref.id, answer_ref.revision,
                 question_ref.id, question_ref.version, rubric_ref.id, rubric_ref.version,
                 _dt_to_iso(now)),
            )
            return claim

    def complete_evaluation(self, claim: EvaluationResult, result: EvaluationResult) -> EvaluationResult:
        if claim.status is not EvaluationStatus.PROCESSING or result.status is not EvaluationStatus.COMPLETED:
            raise ValueError("A processing claim can only be completed with a completed result.")
        if (
            claim.id, claim.version, claim.answer_ref, claim.question_ref, claim.rubric_ref
        ) != (
            result.id, result.version, result.answer_ref, result.question_ref, result.rubric_ref
        ):
            raise ValueError("Completed result must match the reserved attempt.")
        return self.save_evaluation(result, processing_claim=claim)

    def fail_evaluation(self, claim: EvaluationResult, code: str, message: str) -> EvaluationResult:
        failed = replace(claim, status=EvaluationStatus.FAILED, failure_code=code,
                         failure_message=message, evaluated_at=datetime.now(UTC))
        with self._connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                "UPDATE evaluations SET status='failed', failure_code=?, failure_message=?, "
                "evaluated_at=? WHERE id=? AND version=? AND status='processing'",
                (code, message, _dt_to_iso(failed.evaluated_at), claim.id, claim.version),
            )
            if updated.rowcount != 1:
                raise EvaluationInProgressError("Evaluation claim is no longer active.")
        return failed

    def save_evaluation(
        self, result: EvaluationResult, *, reuse_completed: bool = False,
        processing_claim: EvaluationResult | None = None,
    ) -> EvaluationResult:
        try:
            with self._connect() as conn, conn:
                conn.execute("BEGIN IMMEDIATE")
                if reuse_completed:
                    row = conn.execute(
                        "SELECT * FROM evaluations WHERE answer_id=? AND answer_revision=? "
                        "AND status='completed' ORDER BY version DESC LIMIT 1",
                        (result.answer_ref.id, result.answer_ref.revision),
                    ).fetchone()
                    if row is not None:
                        return self._load_evaluation_from_row(conn, row)
                row = conn.execute("SELECT * FROM evaluations WHERE id=? AND version=?",
                                   (result.id, result.version)).fetchone()
                if row is not None:
                    existing = self._load_evaluation_from_row(conn, row)
                    if processing_claim is not None and existing == processing_claim:
                        conn.execute(
                            "UPDATE evaluations SET status=?, total_score=?, maximum_score=?, "
                            "evaluated_at=?, prompt_version=?, model_id=?, demo_mode_label=? "
                            "WHERE id=? AND version=? AND status='processing'",
                            (result.status.value, result.total_score, result.maximum_score,
                             _dt_to_iso(result.evaluated_at), result.prompt_version, result.model_id,
                             result.demo_mode_label, result.id, result.version),
                        )
                    elif existing == result:
                        return existing
                    else:
                        raise DuplicateRecordError(f"Evaluation ({result.id}, {result.version}) already exists.")
                else:
                    if processing_claim is not None:
                        raise RecordNotFoundError("Evaluation claim is no longer active.")
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

    def replace_competency_profile(
        self, owner_token_hash: str, entries: tuple[CompetencyProfileEntry, ...]
    ) -> None:
        """Atomically replace only this owner's derived rows."""
        try:
            with self._connect() as conn, conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "DELETE FROM competency_profiles WHERE owner_token_hash=?",
                    (owner_token_hash,),
                )
                conn.executemany(
                    """INSERT INTO competency_profiles (
                        owner_token_hash, skill_id, criterion_type, observed_count,
                        met_count, unmet_count, unresolved_count, latest_status,
                        latest_evaluated_at, latest_session_id, latest_answer_id,
                        latest_answer_revision, latest_evaluation_id,
                        latest_evaluation_version, latest_criterion_id, recent_scored_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            owner_token_hash, item.skill_id, item.criterion_type,
                            item.observed_count, item.met_count, item.unmet_count,
                            item.unresolved_count, item.latest_status.value,
                            _dt_to_iso(item.latest_evaluated_at), item.latest_session_id,
                            item.latest_answer_ref.id, item.latest_answer_ref.revision,
                            item.latest_evaluation_id, item.latest_evaluation_version,
                            item.latest_criterion_id,
                            json.dumps([
                                {"score": score.score, "maximum_score": score.maximum_score,
                                 "status": score.status.value}
                                for score in item.recent_scored
                            ]),
                        ) for item in entries
                    ],
                )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist competency profile: {error}") from error

    def list_competency_profile(
        self, owner_token_hash: str
    ) -> tuple[CompetencyProfileEntry, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM competency_profiles WHERE owner_token_hash=? "
                "ORDER BY skill_id, criterion_type",
                (owner_token_hash,),
            ).fetchall()
        return tuple(
            CompetencyProfileEntry(
                skill_id=SkillId(row["skill_id"]),
                criterion_type=row["criterion_type"],
                observed_count=row["observed_count"],
                met_count=row["met_count"],
                unmet_count=row["unmet_count"],
                unresolved_count=row["unresolved_count"],
                latest_status=CriterionStatus(row["latest_status"]),
                latest_evaluated_at=_iso_to_dt(row["latest_evaluated_at"]),
                latest_session_id=SessionId(row["latest_session_id"]),
                latest_answer_ref=AnswerRevisionRef(
                    AnswerId(row["latest_answer_id"]), row["latest_answer_revision"]
                ),
                latest_evaluation_id=EvaluationId(row["latest_evaluation_id"]),
                latest_evaluation_version=row["latest_evaluation_version"],
                latest_criterion_id=CriterionId(row["latest_criterion_id"]),
                recent_scored=tuple(
                    RecentCriterionScore(
                        score=item["score"], maximum_score=item["maximum_score"],
                        status=CriterionStatus(item["status"]),
                    ) for item in json.loads(row["recent_scored_json"])
                ),
            ) for row in rows
        )


__all__ = ["SCHEMA_VERSION", "SQLiteRepositoryStore"]
