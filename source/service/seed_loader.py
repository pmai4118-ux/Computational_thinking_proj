"""Seed catalog loader hydrating any ContentRepository from `data/seed/` JSON files."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from source.Model.exercise import Exercise
from source.Model.ids import (
    CriterionId,
    ExerciseId,
    QuestionId,
    RubricId,
    SkillId,
    SourceId,
    VersionedRef,
)
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
from source.Model.repositories.interfaces import ContentRepository

DEFAULT_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def _parse_review(raw: dict[str, object]) -> ReviewMetadata:
    checks_raw = raw.get("checks")
    checks_dict = checks_raw if isinstance(checks_raw, dict) else {}
    reviewed_at_raw = raw.get("reviewed_at")
    reviewed_at = (
        datetime.fromisoformat(reviewed_at_raw)
        if isinstance(reviewed_at_raw, str) and reviewed_at_raw
        else None
    )
    return ReviewMetadata(
        status=ReviewStatus(str(raw.get("status", "draft"))),
        curator_id=raw.get("curator_id") if isinstance(raw.get("curator_id"), str) else None,
        reviewer_id=raw.get("reviewer_id") if isinstance(raw.get("reviewer_id"), str) else None,
        reviewed_at=reviewed_at,
        checks=ReviewChecks(
            source_and_license_verified=checks_dict.get("source_and_license_verified"),
            original_and_adaptation_preserved=checks_dict.get("original_and_adaptation_preserved"),
            technical_correctness_checked=checks_dict.get("technical_correctness_checked"),
            rubric_levels_distinct=checks_dict.get("rubric_levels_distinct"),
            equivalent_answers_checked=checks_dict.get("equivalent_answers_checked"),
            review_cases_checked=checks_dict.get("review_cases_checked"),
        ),
    )


def load_seed_catalog_into_repository(
    content_repo: ContentRepository,
    *,
    seed_dir: Path = DEFAULT_SEED_DIR,
) -> None:
    """Populate `content_repo` with verified non-example seed skills, sources, questions, and exercises."""
    skills_path = seed_dir / "skills.json"
    if skills_path.exists():
        for item in json.loads(skills_path.read_text(encoding="utf-8")):
            content_repo.save_skill(
                Skill(
                    id=SkillId(item["id"]),
                    label=item["label"],
                    description=item.get("description"),
                )
            )

    sources_path = seed_dir / "source_registry.json"
    source_originals: dict[str, str] = {}
    if sources_path.exists():
        for item in json.loads(sources_path.read_text(encoding="utf-8")):
            if item.get("example_only") is True:
                continue
            lic = item["license"]
            collected_raw = item.get("collected_at")
            authors = item.get("authors") or []
            author_str = ", ".join(str(a) for a in authors) if authors else item.get("title")
            original_obj = item.get("original_content") or {}
            if isinstance(original_obj, dict):
                parts = [
                    str(original_obj.get("question_text") or "").strip(),
                    str(original_obj.get("code") or "").strip(),
                ]
                source_originals[item["id"]] = "\n\n".join(p for p in parts if p)
            content_repo.save_source(
                SourceMetadata(
                    id=SourceId(item["id"]),
                    url=item.get("url"),
                    revision=item.get("revision"),
                    author=author_str,
                    license_identifier=lic.get("spdx_id"),
                    license_url=lic.get("url"),
                    license_status=LicenseStatus(lic.get("status", "not_checked")),
                    collected_at=(
                        datetime.fromisoformat(collected_raw)
                        if isinstance(collected_raw, str) and collected_raw
                        else None
                    ),
                    required_notice=lic.get("required_notice"),
                )
            )

    questions_dir = seed_dir / "questions"
    if questions_dir.is_dir():
        for q_file in sorted(questions_dir.glob("*.json")):
            for item in json.loads(q_file.read_text(encoding="utf-8")):
                if item.get("example_only") is True:
                    continue
                review = _parse_review(item["review"])
                raw_rubric = item["rubric"]
                criteria = tuple(
                    Criterion(
                        id=CriterionId(crit["id"]),
                        label=crit["label"],
                        expected_evidence=tuple(crit["expected_evidence"]),
                        levels=tuple(
                            CriterionLevel(score=lvl["score"], description=lvl["description"])
                            for lvl in crit["levels"]
                        ),
                        equivalent_answers_note=crit.get("equivalent_answers"),
                        criterion_type=crit.get("criterion_type"),
                    )
                    for crit in raw_rubric["criteria"]
                )
                rubric = Rubric(
                    id=RubricId(raw_rubric["id"]),
                    version=int(raw_rubric["version"]),
                    criteria=criteria,
                    review=review,
                )
                content_repo.save_rubric(rubric)

                adaptation = item.get("adaptation") or {}
                adaptation_summary = (
                    adaptation.get("summary") if isinstance(adaptation, dict) else None
                )
                question = Question(
                    id=QuestionId(item["id"]),
                    version=int(item["version"]),
                    category=item["category"],
                    language=item["language"],
                    prompt=item["prompt"],
                    skill_ids=tuple(SkillId(s) for s in item["skill_ids"]),
                    rubric_ref=VersionedRef(rubric.id, rubric.version),
                    source_id=SourceId(item["source_id"]),
                    review=review,
                    original_content=source_originals.get(item["source_id"]),
                    adaptation_note=adaptation_summary,
                    code=item.get("code"),
                    code_language=item.get("code_language"),
                    constraints=tuple(item.get("constraints") or ()),
                    role=item.get("role", "backend_developer"),
                    level=item.get("level", "intern_fresher"),
                    difficulty=item.get("difficulty", "applied"),
                )
                content_repo.save_question(question)

    exercises_path = seed_dir / "exercises.json"
    if exercises_path.exists():
        for item in json.loads(exercises_path.read_text(encoding="utf-8")):
            if item.get("example_only") is True:
                continue
            review = _parse_review(item["review"])
            exercise = Exercise(
                id=ExerciseId(item["id"]),
                version=int(item["version"]),
                title=item["title"],
                summary=item["summary"],
                instructions=item["instructions"],
                related_skill_ids=tuple(SkillId(s) for s in item["related_skill_ids"]),
                source_id=SourceId(item["source_id"]),
                prerequisite_ids=tuple(
                    ExerciseId(p) for p in (item.get("prerequisite_ids") or ())
                ),
                target_criterion_types=tuple(item.get("target_criterion_types") or ()),
                estimated_duration_minutes=item.get("estimated_duration_minutes"),
                observable_outcome=item.get("observable_outcome"),
                review=review,
            )
            content_repo.save_exercise(exercise)


__all__ = ["DEFAULT_SEED_DIR", "load_seed_catalog_into_repository"]
