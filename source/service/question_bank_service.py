"""Validate reviewed seed content before importing an atomic question bank."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from source.Model.exercise import Exercise
from source.Model.ids import CriterionId, ExerciseId, QuestionId, RubricId, SkillId, SourceId, VersionedRef
from source.Model.question import (
    CodingConfig, Criterion, CriterionLevel, LicenseStatus, Question, ReplayGrounding,
    ReviewChecks, ReviewMetadata, ReviewStatus, Rubric, Skill, SourceMetadata,
)
from source.Model.repositories.interfaces import ContentRepository, RepositoryError
from source.service.interview_service import SessionBlueprint, load_session_blueprints

DEFAULT_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"
QUESTION_FILES = {
    "programming_knowledge": "programming.json",
    "technical_case": "cases.json",
    "algorithm_explanation": "algorithms.json",
    "ai_code_review": "ai_review.json",
}


@dataclass(frozen=True, slots=True)
class SeedIssue:
    code: str
    file: str
    index: int | None
    record_id: str | None
    message: str


@dataclass(frozen=True, slots=True)
class SeedCatalog:
    skills: tuple[Skill, ...] = ()
    sources: tuple[SourceMetadata, ...] = ()
    rubrics: tuple[Rubric, ...] = ()
    questions: tuple[Question, ...] = ()
    exercises: tuple[Exercise, ...] = ()

    def counts(self) -> dict[str, int]:
        return {name: len(getattr(self, name)) for name in
                ("skills", "sources", "rubrics", "questions", "exercises")}


@dataclass(frozen=True, slots=True)
class SeedImportReport:
    imported: dict[str, int]
    accepted: dict[str, int]
    issues: tuple[SeedIssue, ...]
    blocked: bool

    def to_dict(self) -> dict[str, Any]:
        excluded = {name: 0 for name in self.accepted}
        for issue in self.issues:
            if issue.index is None:
                continue
            group = ("questions" if issue.file.startswith("questions/") else
                     {"skills.json": "skills", "source_registry.json": "sources",
                      "exercises.json": "exercises"}.get(issue.file))
            if group is not None:
                excluded[group] += 1
        return {
            "blocked": self.blocked,
            "imported": self.imported,
            "accepted": self.accepted,
            "excluded": excluded,
            "issues": [asdict(issue) for issue in self.issues],
        }


class SeedImportBlockedError(ValueError):
    def __init__(self, report: SeedImportReport) -> None:
        super().__init__("Seed import blocked; inspect the report for record and coverage errors.")
        self.report = report


def _version(value: Any) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("version must be a positive integer")
    return value


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _text_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty array")
    return tuple(_nonempty(item, f"{name}[]") for item in value)


def _optional_text_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    return tuple(_nonempty(item, f"{name}[]") for item in value)


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _real_record(item: Any) -> dict[str, Any]:
    record = _object(item, "record")
    if record.get("example_only") is not False:
        raise ValueError("example_only must be false for reviewed content")
    return record


def _review(raw: Any) -> ReviewMetadata:
    if not isinstance(raw, dict):
        raise ValueError("review must be an object")
    if raw.get("status") != "approved":
        raise ValueError("review.status must be approved")
    checks = raw.get("checks")
    if not isinstance(checks, dict):
        raise ValueError("review.checks must be an object")
    reviewed_at = datetime.fromisoformat(_nonempty(raw.get("reviewed_at"), "review.reviewed_at"))
    if reviewed_at.tzinfo is None:
        raise ValueError("review.reviewed_at must include a timezone")
    return ReviewMetadata(
        status=ReviewStatus.APPROVED,
        curator_id=_nonempty(raw.get("curator_id"), "review.curator_id"),
        reviewer_id=_nonempty(raw.get("reviewer_id"), "review.reviewer_id"),
        reviewed_at=reviewed_at,
        checks=ReviewChecks(**{name: checks.get(name) for name in ReviewChecks.__dataclass_fields__}),
    )


def _records(seed_dir: Path, relative: str, issues: list[SeedIssue]) -> list[Any]:
    path = seed_dir / relative
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        issues.append(SeedIssue("CORE_FILE_INVALID", relative, None, None, str(error)))
        return []
    if not isinstance(raw, list):
        issues.append(SeedIssue("CORE_FILE_INVALID", relative, None, None, "Expected a JSON array."))
        return []
    return raw


def _record_error(issues: list[SeedIssue], code: str, file: str, index: int,
                  item: Any, error: Exception | str) -> None:
    record_id = item.get("id") if isinstance(item, dict) else None
    issues.append(SeedIssue(code, file, index, record_id if isinstance(record_id, str) else None,
                            str(error)))


def _is_example(item: Any, file: str, index: int, issues: list[SeedIssue]) -> bool:
    if isinstance(item, dict) and item.get("example_only") is True:
        _record_error(issues, "EXAMPLE_ONLY", file, index, item, "Illustrative record is excluded from import.")
        return True
    return False


def _source(item: Any) -> tuple[SourceMetadata, str]:
    item = _real_record(item)
    if item.get("schema_version") != "source-record/0.1-proposal":
        raise ValueError("Unsupported source schema_version")
    lic = item["license"]
    if not isinstance(lic, dict) or lic.get("status") != "verified":
        raise ValueError("source license must be verified")
    url = _nonempty(item.get("url"), "source.url")
    revision = _nonempty(item.get("revision"), "source.revision")
    file_path = _nonempty(item.get("file_path"), "source.file_path")
    if (not url.startswith("https://") or not re.fullmatch(r"[0-9a-fA-F]{40}", revision)
            or revision not in url or file_path not in url):
        raise ValueError("source.url must be HTTPS and contain its 40-character revision")
    license_url = _nonempty(lic.get("url"), "license.url")
    if not license_url.startswith("https://"):
        raise ValueError("license.url must be HTTPS")
    authors = _text_list(item.get("authors"), "source.authors")
    original = item.get("original_content")
    if not isinstance(original, dict):
        raise ValueError("source.original_content must be an object")
    original_text = _nonempty(original.get("question_text"), "source.original_content.question_text")
    code = original.get("code")
    if isinstance(code, str) and code.strip():
        original_text += "\n\n" + code.strip()
    return SourceMetadata(
        id=SourceId(_nonempty(item["id"], "source.id")),
        url=url, revision=revision, author=", ".join(authors),
        license_identifier=_nonempty(lic.get("spdx_id"), "license.spdx_id"),
        license_url=license_url,
        license_status=LicenseStatus.VERIFIED,
        collected_at=datetime.fromisoformat(_nonempty(item.get("collected_at"), "source.collected_at")),
        required_notice=_nonempty(lic.get("required_notice"), "license.required_notice"),
    ), original_text


def _question(item: Any, *, category: str, skills: set[SkillId],
              sources: dict[SourceId, str]) -> tuple[Rubric, Question]:
    item = _real_record(item)
    if item.get("schema_version") != "question-record/0.1-proposal":
        raise ValueError("Unsupported question schema_version")
    if item.get("category") != category:
        raise ValueError(f"question.category must be {category}")
    review = _review(item.get("review"))
    skill_ids = tuple(SkillId(value) for value in _text_list(item["skill_ids"], "question.skill_ids"))
    if not skill_ids or any(skill not in skills for skill in skill_ids):
        raise ValueError("question.skill_ids includes an unknown or missing skill")
    source_id = SourceId(_nonempty(item["source_id"], "question.source_id"))
    if source_id not in sources:
        raise ValueError("question.source_id has no verified source")
    raw_rubric = _object(item.get("rubric"), "question.rubric")
    raw_criteria = raw_rubric.get("criteria")
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise ValueError("rubric.criteria must be a non-empty array")
    criteria = []
    for raw in raw_criteria:
        raw_criterion = _object(raw, "rubric.criteria[]")
        raw_levels = raw_criterion.get("levels")
        if not isinstance(raw_levels, list):
            raise ValueError("rubric criterion levels must be an array")
        levels = tuple(
            CriterionLevel(
                score=_object(level, "criterion.levels[]")["score"],
                description=_object(level, "criterion.levels[]")["description"],
            )
            for level in raw_levels
        )
        if tuple(level.score for level in levels) != (0, 1, 2):
            raise ValueError("rubric criterion levels must be 0, 1, 2")
        criteria.append(Criterion(
            id=CriterionId(_nonempty(raw_criterion["id"], "criterion.id")),
            label=raw_criterion["label"],
            expected_evidence=_text_list(raw_criterion["expected_evidence"], "criterion.expected_evidence"),
            levels=levels,
            equivalent_answers_note=_nonempty(raw_criterion.get("equivalent_answers"), "criterion.equivalent_answers"),
            criterion_type=_nonempty(raw_criterion.get("criterion_type"), "criterion.criterion_type"),
        ))
    rubric = Rubric(id=RubricId(_nonempty(raw_rubric["id"], "rubric.id")),
                    version=_version(raw_rubric["version"]), criteria=tuple(criteria), review=review)
    scoring = raw_rubric.get("scoring")
    if not isinstance(scoring, dict) or scoring.get("maximum_score") != rubric.maximum_score:
        raise ValueError("rubric scoring.maximum_score does not match criterion levels")
    if scoring.get("allowed_scores") != [0, 1, 2] or scoring.get("total_policy") != "sum_only_when_every_criterion_is_decidable":
        raise ValueError("rubric scoring policy does not match the supported 0–2 rubric")
    adaptation = item.get("adaptation")
    if not isinstance(adaptation, dict):
        raise ValueError("question.adaptation must be an object")

    raw_coding = item.get("coding_config")
    if not isinstance(raw_coding, dict):
        raise ValueError(
            "question.coding_config is required (object with mode: required|optional|hidden)"
        )
    coding_mode = _nonempty(raw_coding.get("mode"), "question.coding_config.mode")
    raw_lang = raw_coding.get("language")
    coding_lang = _nonempty(raw_lang, "question.coding_config.language") if raw_lang is not None else None
    raw_starter = raw_coding.get("starter_code")
    if raw_starter is not None and not isinstance(raw_starter, str):
        raise ValueError("question.coding_config.starter_code must be a string or null")
    raw_placeholder = raw_coding.get("placeholder")
    coding_placeholder = (
        _nonempty(raw_placeholder, "question.coding_config.placeholder")
        if raw_placeholder is not None
        else None
    )
    coding_config = CodingConfig(
        mode=coding_mode,
        language=coding_lang,
        starter_code=raw_starter,
        placeholder=coding_placeholder,
    )

    replay_grounding: ReplayGrounding | None = None
    raw_grounding = item.get("replay_grounding")
    if category == "technical_case":
        if not isinstance(raw_grounding, dict):
            raise ValueError(
                "technical_case questions require replay_grounding "
                "(environment_assumptions, core_invariants, decision_focus, reference_notes)"
            )
        replay_grounding = ReplayGrounding(
            environment_assumptions=_text_list(
                raw_grounding.get("environment_assumptions"),
                "question.replay_grounding.environment_assumptions",
            ),
            core_invariants=_text_list(
                raw_grounding.get("core_invariants"),
                "question.replay_grounding.core_invariants",
            ),
            decision_focus=_text_list(
                raw_grounding.get("decision_focus"),
                "question.replay_grounding.decision_focus",
            ),
            reference_notes=_text_list(
                raw_grounding.get("reference_notes"),
                "question.replay_grounding.reference_notes",
            ),
        )
    elif raw_grounding is not None:
        if not isinstance(raw_grounding, dict):
            raise ValueError("question.replay_grounding must be an object or null")
        replay_grounding = ReplayGrounding(
            environment_assumptions=_text_list(
                raw_grounding.get("environment_assumptions"),
                "question.replay_grounding.environment_assumptions",
            ),
            core_invariants=_text_list(
                raw_grounding.get("core_invariants"),
                "question.replay_grounding.core_invariants",
            ),
            decision_focus=_text_list(
                raw_grounding.get("decision_focus"),
                "question.replay_grounding.decision_focus",
            ),
            reference_notes=_optional_text_list(
                raw_grounding.get("reference_notes", []),
                "question.replay_grounding.reference_notes",
            ),
        )

    question = Question(
        id=QuestionId(_nonempty(item["id"], "question.id")), version=_version(item["version"]),
        category=category, language=item["language"], prompt=item["prompt"], skill_ids=skill_ids,
        rubric_ref=VersionedRef(rubric.id, rubric.version), source_id=source_id, review=review,
        original_content=sources[source_id],
        adaptation_note=_nonempty(adaptation.get("summary"), "question.adaptation.summary"),
        code=item.get("code"), code_language=item.get("code_language"),
        constraints=_optional_text_list(item.get("constraints", []), "question.constraints"),
        role=item["role"], level=item["level"], difficulty=item["difficulty"],
        coding_config=coding_config,
        replay_grounding=replay_grounding,
    )
    return rubric, question


def _exercise(item: Any, skills: set[SkillId], sources: set[SourceId]) -> Exercise:
    item = _real_record(item)
    if item.get("schema_version") != "exercise-record/0.1-proposal":
        raise ValueError("Unsupported exercise schema_version")
    review = _review(item.get("review"))
    skill_ids = tuple(SkillId(value) for value in
                      _text_list(item["related_skill_ids"], "exercise.related_skill_ids"))
    if not skill_ids or any(skill not in skills for skill in skill_ids):
        raise ValueError("exercise.related_skill_ids includes an unknown or missing skill")
    source_id = SourceId(_nonempty(item["source_id"], "exercise.source_id"))
    if source_id not in sources:
        raise ValueError("exercise.source_id has no verified source")
    return Exercise(
        id=ExerciseId(_nonempty(item["id"], "exercise.id")), version=_version(item["version"]),
        title=item["title"], summary=item["summary"], instructions=item["instructions"],
        related_skill_ids=skill_ids, source_id=source_id,
        prerequisite_ids=tuple(ExerciseId(value) for value in
                               _optional_text_list(item.get("prerequisite_ids", []),
                                                   "exercise.prerequisite_ids")),
        target_criterion_types=_text_list(item["target_criterion_types"], "exercise.target_criterion_types"),
        estimated_duration_minutes=item.get("estimated_duration_minutes"),
        observable_outcome=item.get("observable_outcome"), review=review,
    )


class QuestionBankService:
    """Separate record rejection from release-blocking dataset failures."""

    def validate(self, seed_dir: Path = DEFAULT_SEED_DIR) -> tuple[SeedCatalog, tuple[SeedIssue, ...]]:
        issues: list[SeedIssue] = []
        raw_skills = _records(seed_dir, "skills.json", issues)
        raw_sources = _records(seed_dir, "source_registry.json", issues)
        _records(seed_dir, "session_blueprints.json", issues)
        raw_exercises = _records(seed_dir, "exercises.json", issues)
        raw_questions = {category: _records(seed_dir, f"questions/{filename}", issues)
                         for category, filename in QUESTION_FILES.items()}

        try:
            blueprints = load_session_blueprints(seed_dir / "session_blueprints.json")
            if not blueprints or any(not bp.slots or not bp.allowed_difficulties for bp in blueprints):
                raise ValueError("at least one complete blueprint is required")
            if len({(bp.id, bp.version) for bp in blueprints}) != len(blueprints):
                raise ValueError("duplicate blueprint ID/version")
        except (OSError, UnicodeError, ValueError, TypeError, KeyError) as error:
            issues.append(SeedIssue("CORE_BLUEPRINT_INVALID", "session_blueprints.json", None, None, str(error)))
            blueprints = ()

        skills: dict[SkillId, Skill] = {}
        for index, item in enumerate(raw_skills):
            try:
                if _is_example(item, "skills.json", index, issues):
                    continue
                record = _object(item, "skill record")
                skill = Skill(SkillId(_nonempty(record["id"], "skill.id")),
                              _nonempty(record["label"], "skill.label"), record.get("description"))
                if skill.id in skills:
                    _record_error(issues, "CORE_ID_CONFLICT", "skills.json", index, item, "duplicate skill ID")
                    continue
                skills[skill.id] = skill
            except (KeyError, TypeError, ValueError) as error:
                _record_error(issues, "INVALID_SKILL", "skills.json", index, item, error)

        sources: dict[SourceId, SourceMetadata] = {}
        originals: dict[SourceId, str] = {}
        for index, item in enumerate(raw_sources):
            try:
                if _is_example(item, "source_registry.json", index, issues):
                    continue
                source, original = _source(item)
                if source.id in sources:
                    _record_error(issues, "CORE_ID_CONFLICT", "source_registry.json", index, item, "duplicate source ID")
                    continue
                sources[source.id] = source
                originals[source.id] = original
            except (KeyError, TypeError, ValueError) as error:
                _record_error(issues, "INVALID_SOURCE", "source_registry.json", index, item, error)

        rubrics: dict[tuple[RubricId, int], Rubric] = {}
        questions: dict[tuple[QuestionId, int], Question] = {}
        for category, filename in QUESTION_FILES.items():
            relative = f"questions/{filename}"
            for index, item in enumerate(raw_questions[category]):
                try:
                    if _is_example(item, relative, index, issues):
                        continue
                    rubric, question = _question(item, category=category,
                                                 skills=set(skills), sources=originals)
                    eligible_slots = [slot for blueprint in blueprints
                                      if question.role == blueprint.role
                                      and question.level == blueprint.level
                                      and question.language == blueprint.language
                                      and question.difficulty in blueprint.allowed_difficulties
                                      for slot in blueprint.slots
                                      if slot.category == question.category]
                    if not any(slot.skill_id in question.skill_ids
                               and all(criterion.criterion_type in slot.eligible_criterion_types
                                       for criterion in rubric.criteria)
                               for slot in eligible_slots):
                        raise ValueError("question skill, difficulty or rubric types do not match a blueprint slot")
                    if (question.id, question.version) in questions:
                        raise ValueError("duplicate question ID/version")
                    if (rubric.id, rubric.version) in rubrics:
                        raise ValueError("duplicate rubric ID/version")
                    rubrics[(rubric.id, rubric.version)] = rubric
                    questions[(question.id, question.version)] = question
                except (KeyError, TypeError, ValueError) as error:
                    _record_error(issues, "INVALID_QUESTION", relative, index, item, error)

        exercises: dict[tuple[ExerciseId, int], Exercise] = {}
        locations: dict[tuple[ExerciseId, int], int] = {}
        for index, item in enumerate(raw_exercises):
            try:
                if _is_example(item, "exercises.json", index, issues):
                    continue
                exercise = _exercise(item, set(skills), set(sources))
                covered_pairs = {(slot.skill_id, criterion_type)
                                 for blueprint in blueprints for slot in blueprint.slots
                                 for criterion_type in slot.eligible_criterion_types}
                if not all(any((skill_id, criterion_type) in covered_pairs
                               for skill_id in exercise.related_skill_ids)
                           for criterion_type in exercise.target_criterion_types):
                    raise ValueError("exercise target criterion types do not match related blueprint skills")
                if (exercise.id, exercise.version) in exercises:
                    raise ValueError("duplicate exercise ID/version")
                exercises[(exercise.id, exercise.version)] = exercise
                locations[(exercise.id, exercise.version)] = index
            except (KeyError, TypeError, ValueError) as error:
                _record_error(issues, "INVALID_EXERCISE", "exercises.json", index, item, error)

        # Reject an entire dependent chain if a prerequisite is missing or cyclic.
        while True:
            current = {exercise.id: exercise for exercise in exercises.values()}
            bad: set[tuple[ExerciseId, int]] = set()
            for key, exercise in exercises.items():
                def visit(exercise_id: ExerciseId, path: set[ExerciseId]) -> bool:
                    if exercise_id in path or exercise_id not in current:
                        return False
                    return all(visit(dep, path | {exercise_id})
                               for dep in current[exercise_id].prerequisite_ids)
                if not all(visit(dep, {exercise.id}) for dep in exercise.prerequisite_ids):
                    bad.add(key)
            if not bad:
                break
            for key in bad:
                _record_error(issues, "INVALID_PREREQUISITE", "exercises.json", locations[key],
                              {"id": key[0]}, "missing or cyclic prerequisite")
                del exercises[key]

        catalog = SeedCatalog(tuple(skills.values()), tuple(sources.values()),
                              tuple(rubrics.values()), tuple(questions.values()), tuple(exercises.values()))
        self._check_coverage(catalog, blueprints, issues)
        return catalog, tuple(issues)

    @staticmethod
    def _check_coverage(catalog: SeedCatalog, blueprints: tuple[SessionBlueprint, ...],
                        issues: list[SeedIssue]) -> None:
        skills = {skill.id for skill in catalog.skills}
        for blueprint in blueprints:
            categories = [slot.category for slot in blueprint.slots]
            if len(set(categories)) != len(categories):
                issues.append(SeedIssue("COVERAGE_MISSING", "session_blueprints.json", None,
                                        blueprint.id, "blueprint has duplicate category slots"))
            for slot in blueprint.slots:
                if slot.skill_id not in skills:
                    issues.append(SeedIssue("COVERAGE_MISSING", "session_blueprints.json", None,
                                            blueprint.id, f"unknown required skill {slot.skill_id}"))
                    continue
                eligible = [q for q in catalog.questions if q.category == slot.category
                            and q.role == blueprint.role and q.level == blueprint.level
                            and q.language == blueprint.language
                            and q.difficulty in blueprint.allowed_difficulties
                            and slot.skill_id in q.skill_ids
                            and any(c.criterion_type in slot.eligible_criterion_types
                                    for c in next(r for r in catalog.rubrics if r.id == q.rubric_ref.id
                                                  and r.version == q.rubric_ref.version).criteria)]
                if len({q.id for q in eligible}) < 2:
                    issues.append(SeedIssue("COVERAGE_MISSING", "session_blueprints.json", None,
                                            blueprint.id, f"{slot.category}: need two reviewed question IDs"))
                for criterion_type in slot.eligible_criterion_types:
                    if not any(slot.skill_id in ex.related_skill_ids
                               and criterion_type in ex.target_criterion_types
                               for ex in catalog.exercises):
                        issues.append(SeedIssue("EXERCISE_COVERAGE_MISSING", "session_blueprints.json", None,
                                                blueprint.id,
                                                f"{slot.category}/{criterion_type}: no reviewed exercise"))

    def import_seed(self, content_repo: ContentRepository,
                    seed_dir: Path = DEFAULT_SEED_DIR) -> SeedImportReport:
        catalog, issues = self.validate(seed_dir)
        fatal_codes = {"CORE_FILE_INVALID", "CORE_BLUEPRINT_INVALID", "CORE_ID_CONFLICT", "COVERAGE_MISSING",
                       "EXERCISE_COVERAGE_MISSING"}
        blocked = any(issue.code in fatal_codes for issue in issues)
        accepted = catalog.counts()
        zero = {name: 0 for name in accepted}
        if blocked:
            raise SeedImportBlockedError(SeedImportReport(zero, accepted, issues, True))
        try:
            if hasattr(content_repo, "import_seed_records"):
                imported = content_repo.import_seed_records(
                    skills=catalog.skills, sources=catalog.sources, rubrics=catalog.rubrics,
                    questions=catalog.questions, exercises=catalog.exercises,
                )
            else:
                for skill in catalog.skills:
                    content_repo.save_skill(skill)
                for source in catalog.sources:
                    content_repo.save_source(source)
                for rubric in catalog.rubrics:
                    content_repo.save_rubric(rubric)
                for question in catalog.questions:
                    content_repo.save_question(question)
                for exercise in catalog.exercises:
                    content_repo.save_exercise(exercise)
                imported = accepted
        except RepositoryError as error:
            issue = SeedIssue("PERSISTENCE_CONFLICT", "database", None, None, str(error))
            raise SeedImportBlockedError(SeedImportReport(zero, accepted, issues + (issue,), True)) from error
        return SeedImportReport(imported, accepted, issues, False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and atomically import reviewed seed records")
    parser.add_argument("--seed-dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args(argv)
    from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
    try:
        report = QuestionBankService().import_seed(SQLiteRepositoryStore(args.database), args.seed_dir)
    except SeedImportBlockedError as error:
        report = error.report
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 1 if report.blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["DEFAULT_SEED_DIR", "QuestionBankService", "SeedCatalog", "SeedImportBlockedError",
           "SeedImportReport", "SeedIssue", "main"]
