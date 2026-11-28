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

from source.Model.adaptive_probe import FollowUpProbe, ProbeStatus, ProbeTriggerKind
from source.Model.competency_profile import CompetencyProfileEntry, RecentCriterionScore
from source.Model.decision_replay import (
    ReplayInvariantCheck,
    ReplayOptionBranch,
    ReplayRun,
    ReplayTraceStep,
    ReplayTreeNode,
)
from source.Model.job_posting import (
    JobAnalysisRecord,
    JobPosting,
    JobSkillEvidence,
    UnmatchedJobTerm,
)
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
    CodingConfig,
    Criterion,
    CriterionLevel,
    LicenseStatus,
    Question,
    ReplayGrounding,
    ReviewChecks,
    ReviewMetadata,
    ReviewStatus,
    Rubric,
    Skill,
    SourceMetadata,
)
from source.Model.repositories.interfaces import (
    AnswerLockedError,
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


def _serialize_coding_config(config: CodingConfig | None) -> str | None:
    if config is None:
        return None
    return json.dumps(
        {
            "mode": config.mode,
            "language": config.language,
            "starter_code": config.starter_code,
            "placeholder": config.placeholder,
        },
        ensure_ascii=False,
    )


def _deserialize_coding_config(raw: str | None) -> CodingConfig | None:
    if not raw:
        return None
    data = json.loads(raw)
    return CodingConfig(
        mode=str(data.get("mode", "optional")),
        language=data.get("language"),
        starter_code=data.get("starter_code"),
        placeholder=data.get("placeholder"),
    )


def _serialize_replay_grounding(grounding: ReplayGrounding | None) -> str | None:
    if grounding is None:
        return None
    return json.dumps(
        {
            "environment_assumptions": list(grounding.environment_assumptions),
            "core_invariants": list(grounding.core_invariants),
            "decision_focus": list(grounding.decision_focus),
            "reference_notes": list(grounding.reference_notes),
        },
        ensure_ascii=False,
    )


def _deserialize_replay_grounding(raw: str | None) -> ReplayGrounding | None:
    if not raw:
        return None
    data = json.loads(raw)
    return ReplayGrounding(
        environment_assumptions=tuple(str(x) for x in data.get("environment_assumptions", ())),
        core_invariants=tuple(str(x) for x in data.get("core_invariants", ())),
        decision_focus=tuple(str(x) for x in data.get("decision_focus", ())),
        reference_notes=tuple(str(x) for x in data.get("reference_notes", ())),
    )


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
                question_cols = {row[1] for row in conn.execute("PRAGMA table_info(questions);")}
                if "coding_config_json" not in question_cols:
                    conn.execute("ALTER TABLE questions ADD COLUMN coding_config_json TEXT;")
                if "replay_grounding_json" not in question_cols:
                    conn.execute("ALTER TABLE questions ADD COLUMN replay_grounding_json TEXT;")
                replay_cols = {
                    row[1] for row in conn.execute("PRAGMA table_info(decision_replay_runs);")
                }
                if "linked_answer_id" not in replay_cols:
                    conn.execute("ALTER TABLE decision_replay_runs ADD COLUMN linked_answer_id TEXT;")
                if "linked_answer_revision" not in replay_cols:
                    conn.execute(
                        "ALTER TABLE decision_replay_runs ADD COLUMN linked_answer_revision INTEGER;"
                    )
                if "tree_json" not in replay_cols:
                    conn.execute("ALTER TABLE decision_replay_runs ADD COLUMN tree_json TEXT;")
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
                    coding_json = _serialize_coding_config(question.coding_config)
                    grounding_json = _serialize_replay_grounding(question.replay_grounding)
                    cursor = conn.execute(
                        """INSERT INTO questions (
                             id, version, category, language, role, level, difficulty,
                             prompt, skill_ids_json, rubric_id, rubric_version, source_id,
                             review_status, review_json, original_content, adaptation_note,
                             code, code_language, constraints_json,
                             coding_config_json, replay_grounding_json
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(id, version) DO NOTHING;""",
                        (question.id, question.version, question.category, question.language,
                         question.role, question.level, question.difficulty, question.prompt,
                         json.dumps(list(question.skill_ids), ensure_ascii=False),
                         question.rubric_ref.id, question.rubric_ref.version,
                         question.source_id, question.review.status.value,
                         _serialize_review(question.review), question.original_content,
                         question.adaptation_note, question.code, question.code_language,
                         json.dumps(list(question.constraints), ensure_ascii=False),
                         coding_json, grounding_json),
                    )
                    inserted["questions"] += cursor.rowcount
                    row = conn.execute(
                        "SELECT * FROM questions WHERE id=? AND version=?;",
                        (question.id, question.version),
                    ).fetchone()
                    existing_question = self._row_to_question(row)
                    if existing_question != question:
                        # Safely backfill or sync metadata columns when core versioned question fields match.
                        backfilled = replace(
                            existing_question,
                            coding_config=question.coding_config,
                            replay_grounding=question.replay_grounding,
                        )
                        if backfilled == question:
                            conn.execute(
                                """UPDATE questions
                                   SET coding_config_json = ?, replay_grounding_json = ?
                                   WHERE id = ? AND version = ?;""",
                                (
                                    _serialize_coding_config(backfilled.coding_config),
                                    _serialize_replay_grounding(backfilled.replay_grounding),
                                    question.id,
                                    question.version,
                                ),
                            )
                        else:
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
                        constraints_json, coding_config_json, replay_grounding_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                        _serialize_coding_config(question.coding_config),
                        _serialize_replay_grounding(question.replay_grounding),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist Question {question.id}: {error}") from error

    @staticmethod
    def _row_to_question(row: sqlite3.Row) -> Question:
        keys = set(row.keys())
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
            coding_config=(
                _deserialize_coding_config(row["coding_config_json"])
                if "coding_config_json" in keys
                else None
            ),
            replay_grounding=(
                _deserialize_replay_grounding(row["replay_grounding_json"])
                if "replay_grounding_json" in keys
                else None
            ),
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

    def resume_ended_session(self, session_id: SessionId) -> Session:
        """Repair a legacy ended session without overwriting concurrent updates."""
        with self._connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row is None:
                raise RecordNotFoundError(f"Session {session_id} does not exist.")
            session = self._row_to_session(row)
            if session.state is not SessionState.ENDED_EARLY:
                return session
            rows = conn.execute(
                "SELECT question_id, question_version FROM answers WHERE session_id=?", (session_id,)
            ).fetchall()
            answered = {(r["question_id"], int(r["question_version"])) for r in rows}
            index = next((i for i, q in enumerate(session.question_refs) if (q.id, q.version) not in answered), len(session.question_refs))
            state = SessionState.IN_PROGRESS if index < len(session.question_refs) else SessionState.COMPLETED
            now = datetime.now(UTC)
            conn.execute("UPDATE sessions SET current_index=?, state=?, updated_at=? WHERE id=?", (index, state.value, _dt_to_iso(now), session_id))
            return replace(session, current_index=index, state=state, updated_at=now)

    def advance_session(self, session_id: SessionId, from_question_index: int) -> Session:
        """Advance once, atomically, while preserving concurrent answer references."""
        with self._connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row is None:
                raise RecordNotFoundError(f"Session {session_id} does not exist.")
            session = self._row_to_session(row)
            if session.state is SessionState.COMPLETED and from_question_index == len(session.question_refs) - 1:
                return session
            if session.state is not SessionState.IN_PROGRESS:
                raise AnswerLockedError("This session cannot advance.")
            if session.current_index > 0 and from_question_index == session.current_index - 1:
                return session
            if from_question_index != session.current_index:
                raise AnswerLockedError("The current question has changed.")
            question_ref = session.question_refs[session.current_index]
            if not conn.execute(
                "SELECT 1 FROM answers WHERE session_id=? AND question_id=? AND question_version=? LIMIT 1",
                (session_id, question_ref.id, question_ref.version),
            ).fetchone():
                raise AnswerLockedError("Submit an answer before advancing.")
            index = session.current_index + 1
            next_state = SessionState.COMPLETED if index == len(session.question_refs) else SessionState.IN_PROGRESS
            now = datetime.now(UTC)
            conn.execute(
                "UPDATE sessions SET current_index=?, state=?, updated_at=? WHERE id=?",
                (index, next_state.value, _dt_to_iso(now), session_id),
            )
            return replace(session, current_index=index, state=next_state, updated_at=now)

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

                    if session.state is not SessionState.IN_PROGRESS or session.current_question_ref != answer.question_ref:
                        raise AnswerLockedError("This question is no longer active.")
                    prior = conn.execute(
                        "SELECT 1 FROM answers WHERE session_id=? AND question_id=? AND question_version=? LIMIT 1",
                        (answer.session_id, answer.question_ref.id, answer.question_ref.version),
                    ).fetchone()
                    if prior is not None:
                        raise AnswerLockedError("The submitted answer is locked.")

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
                    conn.execute(
                        "DELETE FROM answer_drafts WHERE session_id=? AND question_id=? AND question_version=?",
                        (answer.session_id, answer.question_ref.id, answer.question_ref.version),
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

    def get_draft(self, session_id: SessionId, question_ref: VersionedRef[QuestionId]) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT text FROM answer_drafts WHERE session_id=? AND question_id=? AND question_version=?",
                (session_id, question_ref.id, question_ref.version),
            ).fetchone()
        return None if row is None else str(row["text"])

    def save_draft(self, session_id: SessionId, question_ref: VersionedRef[QuestionId], text: str) -> None:
        with self._connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row is None:
                raise RecordNotFoundError(f"Session {session_id} does not exist.")
            session = self._row_to_session(row)
            if session.state is not SessionState.IN_PROGRESS or session.current_question_ref != question_ref:
                raise AnswerLockedError("This question is no longer active.")
            if conn.execute(
                "SELECT 1 FROM answers WHERE session_id=? AND question_id=? AND question_version=? LIMIT 1",
                (session_id, question_ref.id, question_ref.version),
            ).fetchone():
                raise AnswerLockedError("The submitted answer is locked.")
            conn.execute(
                "INSERT INTO answer_drafts (session_id, question_id, question_version, text, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(session_id, question_id, question_version) "
                "DO UPDATE SET text=excluded.text, updated_at=excluded.updated_at",
                (session_id, question_ref.id, question_ref.version, text, _dt_to_iso(datetime.now(UTC))),
            )

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
            elif row is not None and row["status"] == EvaluationStatus.PENDING.value:
                conn.execute(
                    "UPDATE evaluations SET status='processing', evaluated_at=? WHERE id=? AND version=?",
                    (_dt_to_iso(now), row["id"], row["version"]),
                )
                return EvaluationResult(
                    id=EvaluationId(row["id"]), version=int(row["version"]),
                    status=EvaluationStatus.PROCESSING, answer_ref=answer_ref,
                    question_ref=question_ref, rubric_ref=rubric_ref, evaluated_at=now,
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

    def prepare_evaluation(
        self, answer_ref: AnswerRevisionRef, question_ref: VersionedRef[QuestionId],
        rubric_ref: VersionedRef[RubricId], *, retry_failed: bool = False,
        recover_interrupted: bool = False,
    ) -> EvaluationResult:
        """Reserve a durable pending attempt; only retry failures on request."""
        now = datetime.now(UTC)
        with self._connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM evaluations WHERE answer_id=? AND answer_revision=? "
                "ORDER BY version DESC LIMIT 1", (answer_ref.id, answer_ref.revision),
            ).fetchone()
            if row is not None:
                current = self._load_evaluation_from_row(conn, row)
                if current.status in (EvaluationStatus.COMPLETED, EvaluationStatus.PENDING):
                    return current
                if current.status is EvaluationStatus.PROCESSING:
                    if current.evaluated_at and now - current.evaluated_at < EVALUATION_LEASE:
                        return current
                    if not recover_interrupted and not retry_failed:
                        return current
                    conn.execute(
                        "UPDATE evaluations SET status='failed', failure_code='EVALUATION_INTERRUPTED', "
                        "failure_message='The prior evaluation was interrupted.' "
                        "WHERE id=? AND version=? AND status='processing'", (current.id, current.version),
                    )
                elif current.status is EvaluationStatus.FAILED:
                    if not retry_failed and not (recover_interrupted and current.failure_code == 'EVALUATION_INTERRUPTED'):
                        return current
                    if current.failure_code not in RETRYABLE_EVALUATION_FAILURES:
                        raise EvaluationRetryNotAllowedError("This evaluation failure cannot be retried.")
            pending = EvaluationResult(
                id=EvaluationId(row["id"] if row else f"evaluation.{uuid4().hex[:12]}"),
                version=int(row["version"]) + 1 if row else 1,
                status=EvaluationStatus.PENDING, answer_ref=answer_ref,
                question_ref=question_ref, rubric_ref=rubric_ref,
            )
            conn.execute(
                "INSERT INTO evaluations (id,version,status,answer_id,answer_revision,question_id,"
                "question_version,rubric_id,rubric_version) VALUES (?,?,?,?,?,?,?,?,?)",
                (pending.id, pending.version, pending.status.value, answer_ref.id, answer_ref.revision,
                 question_ref.id, question_ref.version, rubric_ref.id, rubric_ref.version),
            )
            return pending

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
            # The evaluation row and its criteria must come from one SQLite snapshot.
            conn.execute("BEGIN")
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
            conn.execute("BEGIN")
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
            conn.execute("BEGIN")
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

    def save_job_analysis(self, record: JobAnalysisRecord) -> JobAnalysisRecord:
        posting = record.posting
        matched_json = json.dumps(
            [
                {
                    "skill_id": str(item.skill_id),
                    "matched_term": item.matched_term,
                    "quote": item.quote,
                    "start_offset": item.start_offset,
                    "end_offset": item.end_offset,
                }
                for item in record.matched_skills
            ],
            ensure_ascii=False,
        )
        unmatched_json = json.dumps(
            [
                {
                    "term_label": item.term_label,
                    "quote": item.quote,
                    "start_offset": item.start_offset,
                    "end_offset": item.end_offset,
                    "reason": item.reason,
                }
                for item in record.unmatched_terms
            ],
            ensure_ascii=False,
        )
        try:
            with self._connect() as conn, conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO job_analyses (
                        id, owner_token_hash, title, company, raw_text, source_url,
                        published_at, collected_at, normalization_version,
                        matched_skills_json, unmatched_terms_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        posting.id,
                        posting.owner_token_hash,
                        posting.title,
                        posting.company,
                        posting.raw_text,
                        posting.source_url,
                        posting.published_at,
                        _dt_to_iso(posting.collected_at),
                        posting.normalization_version,
                        matched_json,
                        unmatched_json,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist job analysis: {error}") from error
        return record

    @staticmethod
    def _row_to_job_analysis(row: sqlite3.Row) -> JobAnalysisRecord:
        collected_at = _iso_to_dt(row["collected_at"])
        assert collected_at is not None
        posting = JobPosting(
            id=row["id"],
            owner_token_hash=row["owner_token_hash"],
            title=row["title"],
            company=row["company"],
            raw_text=row["raw_text"],
            source_url=row["source_url"],
            published_at=row["published_at"],
            collected_at=collected_at,
            normalization_version=row["normalization_version"],
        )
        matched = tuple(
            JobSkillEvidence(
                skill_id=SkillId(item["skill_id"]),
                matched_term=item["matched_term"],
                quote=item["quote"],
                start_offset=int(item["start_offset"]),
                end_offset=int(item["end_offset"]),
            )
            for item in json.loads(row["matched_skills_json"])
        )
        unmatched = tuple(
            UnmatchedJobTerm(
                term_label=item["term_label"],
                quote=item["quote"],
                start_offset=int(item["start_offset"]),
                end_offset=int(item["end_offset"]),
                reason=item["reason"],
            )
            for item in json.loads(row["unmatched_terms_json"])
        )
        return JobAnalysisRecord(
            posting=posting,
            matched_skills=matched,
            unmatched_terms=unmatched,
        )

    def get_job_analysis(self, analysis_id: str) -> JobAnalysisRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM job_analyses WHERE id = ?;", (analysis_id,)
            ).fetchone()
        return None if row is None else self._row_to_job_analysis(row)

    def list_job_analyses_by_owner(self, owner_token_hash: str) -> tuple[JobAnalysisRecord, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM job_analyses WHERE owner_token_hash = ? ORDER BY collected_at DESC, id DESC;",
                (owner_token_hash,),
            ).fetchall()
        return tuple(self._row_to_job_analysis(row) for row in rows)

    def save_probe(self, probe: FollowUpProbe) -> FollowUpProbe:
        try:
            with self._connect() as conn, conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO follow_up_probes (
                        id, session_id, owner_token_hash, answer_id, answer_revision,
                        question_id, question_version, rubric_id, rubric_version,
                        criterion_id, criterion_label, trigger_kind, probe_prompt,
                        choice_reason, status, response_text, outcome_status,
                        outcome_score, outcome_max_score, outcome_explanation,
                        outcome_quote, created_at, answered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        probe.id,
                        probe.session_id,
                        probe.owner_token_hash,
                        probe.answer_ref.id,
                        probe.answer_ref.revision,
                        probe.question_ref.id,
                        probe.question_ref.version,
                        probe.rubric_ref.id,
                        probe.rubric_ref.version,
                        probe.criterion_id,
                        probe.criterion_label,
                        probe.trigger_kind.value,
                        probe.probe_prompt,
                        probe.choice_reason,
                        probe.status.value,
                        probe.response_text,
                        probe.outcome_status.value if probe.outcome_status else None,
                        probe.outcome_score,
                        probe.outcome_max_score,
                        probe.outcome_explanation,
                        probe.outcome_quote,
                        _dt_to_iso(probe.created_at),
                        _dt_to_iso(probe.answered_at),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist follow-up probe: {error}") from error
        return probe

    @staticmethod
    def _row_to_probe(row: sqlite3.Row) -> FollowUpProbe:
        created_at = _iso_to_dt(row["created_at"])
        assert created_at is not None
        return FollowUpProbe(
            id=row["id"],
            session_id=SessionId(row["session_id"]),
            owner_token_hash=row["owner_token_hash"],
            answer_ref=AnswerRevisionRef(AnswerId(row["answer_id"]), int(row["answer_revision"])),
            question_ref=VersionedRef(QuestionId(row["question_id"]), int(row["question_version"])),
            rubric_ref=VersionedRef(RubricId(row["rubric_id"]), int(row["rubric_version"])),
            criterion_id=CriterionId(row["criterion_id"]),
            criterion_label=row["criterion_label"],
            trigger_kind=ProbeTriggerKind(row["trigger_kind"]),
            probe_prompt=row["probe_prompt"],
            choice_reason=row["choice_reason"],
            status=ProbeStatus(row["status"]),
            response_text=row["response_text"],
            outcome_status=CriterionStatus(row["outcome_status"]) if row["outcome_status"] else None,
            outcome_score=row["outcome_score"],
            outcome_max_score=row["outcome_max_score"],
            outcome_explanation=row["outcome_explanation"],
            outcome_quote=row["outcome_quote"],
            created_at=created_at,
            answered_at=_iso_to_dt(row["answered_at"]),
        )

    def get_probe(self, probe_id: str) -> FollowUpProbe | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM follow_up_probes WHERE id = ?;", (probe_id,)
            ).fetchone()
        return None if row is None else self._row_to_probe(row)

    def list_probes_for_session(self, session_id: SessionId) -> tuple[FollowUpProbe, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM follow_up_probes WHERE session_id = ? ORDER BY created_at ASC, id ASC;",
                (session_id,),
            ).fetchall()
        return tuple(self._row_to_probe(row) for row in rows)

    def list_probes_for_answer(self, answer_ref: AnswerRevisionRef) -> tuple[FollowUpProbe, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM follow_up_probes WHERE answer_id = ? AND answer_revision = ? ORDER BY created_at ASC, id ASC;",
                (answer_ref.id, answer_ref.revision),
            ).fetchall()
        return tuple(self._row_to_probe(row) for row in rows)

    def save_replay_run(self, run: ReplayRun) -> ReplayRun:
        tree_payload = {
            "schema_version": 2,
            "question_id": str(run.question_id),
            "question_version": run.question_version,
            "title": run.title,
            "summary": run.summary,
            "root_node_id": run.root_node_id,
            "active_node_id": run.active_node_id,
            "visited_node_ids": list(run.visited_node_ids),
            "custom_branches_used": run.custom_branches_used,
            "custom_branch_limit": run.custom_branch_limit,
            "prompt_version": run.prompt_version,
            "model_id": run.model_id,
            "demo_mode_label": run.demo_mode_label,
            "generation_status": run.generation_status,
            "generation_error": run.generation_error,
            "nodes": [
                {
                    "id": node.id,
                    "parent_id": node.parent_id,
                    "branch_label": node.branch_label,
                    "depth": node.depth,
                    "origin": node.origin,
                    "answer_alignment": node.answer_alignment,
                    "title": node.title,
                    "situation": node.situation,
                    "consequence_summary": node.consequence_summary,
                    "system_impact": node.system_impact,
                    "tradeoff_note": node.tradeoff_note,
                    "answer_quote": node.answer_quote,
                    "answer_quote_start": node.answer_quote_start,
                    "answer_quote_end": node.answer_quote_end,
                    "assumptions_used": list(node.assumptions_used),
                    "state_delta": node.state_delta,
                    "trace_steps": [
                        {
                            "actor": step.actor,
                            "event": step.event,
                            "state_after": step.state_after,
                            "time_label": step.time_label,
                        }
                        for step in node.trace_steps
                    ],
                    "is_terminal": node.is_terminal,
                    "invariants": [
                        {
                            "name": inv.name,
                            "status": inv.status,
                            "detail": inv.detail,
                            "category": inv.category,
                        }
                        for inv in node.invariants
                    ],
                    "comparison_note": node.comparison_note,
                    "options": [
                        {
                            "option_id": opt.option_id,
                            "label": opt.label,
                            "action_summary": opt.action_summary,
                            "target_node_id": opt.target_node_id,
                        }
                        for opt in node.options
                    ],
                    "user_proposal": node.user_proposal,
                    "created_at": _dt_to_iso(node.created_at),
                }
                for node in run.nodes
            ],
        }
        tree_json = json.dumps(tree_payload, ensure_ascii=False)
        active = run.active_node
        try:
            with self._connect() as conn, conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO decision_replay_runs (
                        id, scenario_id, scenario_version, owner_token_hash,
                        current_checkpoint_id, completed, steps_json, tree_json,
                        linked_session_id, linked_answer_id, linked_answer_revision,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        run.id,
                        str(run.question_id),
                        run.question_version,
                        run.owner_token_hash,
                        run.active_node_id,
                        1 if active.is_terminal else 0,
                        "[]",
                        tree_json,
                        str(run.linked_session_id) if run.linked_session_id else None,
                        str(run.linked_answer_ref.id) if run.linked_answer_ref else None,
                        run.linked_answer_ref.revision if run.linked_answer_ref else None,
                        _dt_to_iso(run.created_at),
                        _dt_to_iso(run.updated_at),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(f"Cannot persist replay run: {error}") from error
        return run

    @staticmethod
    def _row_to_replay_run(row: sqlite3.Row) -> ReplayRun | None:
        keys = set(row.keys())
        raw_tree = row["tree_json"] if "tree_json" in keys else None
        if not raw_tree:
            return None
        payload = json.loads(raw_tree)
        if not isinstance(payload, dict) or not payload.get("nodes"):
            return None
        created_at = _iso_to_dt(row["created_at"])
        updated_at = _iso_to_dt(row["updated_at"])
        assert created_at is not None and updated_at is not None
        nodes = tuple(
            ReplayTreeNode(
                id=str(n["id"]),
                parent_id=n.get("parent_id"),
                branch_label=str(n.get("branch_label", "")),
                depth=int(n.get("depth", 0)),
                origin=str(n.get("origin", "prebuilt_branch")),
                answer_alignment=str(n.get("answer_alignment", "what_if_branch")),
                title=str(n.get("title", "")),
                situation=str(n.get("situation", "")),
                consequence_summary=str(n.get("consequence_summary", "")),
                system_impact=str(n.get("system_impact", "")),
                tradeoff_note=str(n.get("tradeoff_note", "")),
                answer_quote=n.get("answer_quote"),
                answer_quote_start=n.get("answer_quote_start"),
                answer_quote_end=n.get("answer_quote_end"),
                assumptions_used=tuple(str(x) for x in n.get("assumptions_used", ())),
                state_delta=str(n.get("state_delta", "")),
                trace_steps=tuple(
                    ReplayTraceStep(
                        actor=str(s["actor"]),
                        event=str(s["event"]),
                        state_after=s.get("state_after"),
                        time_label=s.get("time_label"),
                    )
                    for s in n.get("trace_steps", ())
                ),
                is_terminal=bool(n.get("is_terminal", False)),
                invariants=tuple(
                    ReplayInvariantCheck(
                        name=str(inv["name"]),
                        status=str(inv["status"]),
                        detail=str(inv["detail"]),
                        category=str(inv.get("category", "safety")),
                    )
                    for inv in n.get("invariants", ())
                ),
                comparison_note=n.get("comparison_note"),
                options=tuple(
                    ReplayOptionBranch(
                        option_id=str(o["option_id"]),
                        label=str(o["label"]),
                        action_summary=str(o["action_summary"]),
                        target_node_id=str(o["target_node_id"]),
                    )
                    for o in n.get("options", ())
                ),
                user_proposal=n.get("user_proposal"),
                created_at=_iso_to_dt(n.get("created_at")),
            )
            for n in payload["nodes"]
        )
        linked_answer_ref = (
            AnswerRevisionRef(
                AnswerId(row["linked_answer_id"]),
                int(row["linked_answer_revision"] or 1),
            )
            if row["linked_answer_id"]
            else None
        )
        return ReplayRun(
            id=row["id"],
            question_id=QuestionId(str(payload.get("question_id") or row["scenario_id"])),
            question_version=int(payload.get("question_version") or row["scenario_version"]),
            owner_token_hash=row["owner_token_hash"],
            root_node_id=str(payload["root_node_id"]),
            active_node_id=str(payload["active_node_id"]),
            visited_node_ids=tuple(str(x) for x in payload.get("visited_node_ids", ())),
            nodes=nodes,
            title=str(payload.get("title", "")),
            summary=str(payload.get("summary", "")),
            linked_session_id=SessionId(row["linked_session_id"]) if row["linked_session_id"] else None,
            linked_answer_ref=linked_answer_ref,
            custom_branches_used=int(payload.get("custom_branches_used", 0)),
            custom_branch_limit=int(payload.get("custom_branch_limit", 2)),
            prompt_version=str(payload.get("prompt_version", "decision_replay/v1")),
            model_id=payload.get("model_id"),
            demo_mode_label=payload.get("demo_mode_label"),
            generation_status=str(payload.get("generation_status", "ready")),
            generation_error=payload.get("generation_error"),
            created_at=created_at,
            updated_at=updated_at,
        )

    def get_replay_run(self, run_id: str) -> ReplayRun | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM decision_replay_runs WHERE id = ?;", (run_id,)
            ).fetchone()
        return None if row is None else self._row_to_replay_run(row)

    def list_replay_runs_by_owner(self, owner_token_hash: str) -> tuple[ReplayRun, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM decision_replay_runs WHERE owner_token_hash = ? ORDER BY updated_at DESC, id DESC;",
                (owner_token_hash,),
            ).fetchall()
        runs = [self._row_to_replay_run(row) for row in rows]
        return tuple(run for run in runs if run is not None)


__all__ = ["SCHEMA_VERSION", "SQLiteRepositoryStore"]
