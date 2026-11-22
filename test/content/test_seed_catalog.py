"""Acceptance checks for C02, C03, C04, C05, and C06 curated seed content."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from source.Model.exercise import Exercise
from source.Model.ids import ExerciseId, QuestionId, RubricId, SkillId, SourceId, VersionedRef
from source.Model.question import Question, ReviewChecks, ReviewMetadata, ReviewStatus
from source.service.coverage import missing_coverage

ROOT_DIR = Path(__file__).resolve().parents[2]
SEED_DIR = ROOT_DIR / "data" / "seed"
REVIEWS_DIR = ROOT_DIR / "test" / "fixtures" / "question_reviews"
NOTICES_PATH = ROOT_DIR / "docs" / "THIRD_PARTY_NOTICES.md"
HANDOFF_PATH = ROOT_DIR / "docs" / "QUESTION_PROVENANCE_HANDOFF.md"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_source_registry_and_notices_have_verified_real_open_source_provenance() -> None:
    sources = _load_json(SEED_DIR / "source_registry.json")
    assert isinstance(sources, list)
    assert len(sources) >= 9

    notices_text = NOTICES_PATH.read_text(encoding="utf-8")
    handoff_text = HANDOFF_PATH.read_text(encoding="utf-8")

    seen_ids: set[str] = set()
    for record in sources:
        source_id = record["id"]
        assert source_id not in seen_ids
        seen_ids.add(source_id)
        assert record["example_only"] is False
        assert record["url"].startswith("https://github.com/")
        assert len(record["revision"]) == 40
        assert record["revision"] in record["url"]
        assert record["file_path"] in record["url"]
        assert record["authors"]
        assert record["original_content"]["question_text"]

        license_info = record["license"]
        assert license_info["status"] == "verified"
        assert license_info["spdx_id"] in {"PSF-2.0", "PostgreSQL", "MIT", "CC-BY-SA-4.0"}
        assert license_info["url"].startswith("https://")
        assert license_info["required_notice"].strip()

        assert source_id in notices_text
        assert source_id in handoff_text
        assert record["revision"] in handoff_text


def test_c02_to_c05_questions_satisfy_blueprint_coverage_provenance_and_review_rules() -> None:
    skills = {item["id"] for item in _load_json(SEED_DIR / "skills.json")}
    [blueprint] = _load_json(SEED_DIR / "session_blueprints.json")
    slot_by_category = {slot["category"]: slot for slot in blueprint["slots"]}
    sources = {item["id"]: item for item in _load_json(SEED_DIR / "source_registry.json")}
    handoff_text = HANDOFF_PATH.read_text(encoding="utf-8")

    question_files = {
        "programming_knowledge": SEED_DIR / "questions" / "programming.json",
        "technical_case": SEED_DIR / "questions" / "cases.json",
        "algorithm_explanation": SEED_DIR / "questions" / "algorithms.json",
        "ai_code_review": SEED_DIR / "questions" / "ai_review.json",
    }

    domain_questions: list[Question] = []
    seen_question_ids: set[str] = set()

    for expected_category, file_path in question_files.items():
        records = _load_json(file_path)
        assert isinstance(records, list)
        assert len(records) >= 2, f"{file_path.name} must contain at least 2 approved questions"

        slot = slot_by_category[expected_category]
        for record in records:
            qid = record["id"]
            assert qid not in seen_question_ids
            seen_question_ids.add(qid)
            assert qid in handoff_text

            assert record["example_only"] is False
            assert record["category"] == expected_category
            assert record["language"] == blueprint["language"]
            assert record["role"] == blueprint["role"]
            assert record["level"] == blueprint["level"]
            assert record["difficulty"] in blueprint["allowed_difficulties"]

            assert set(record["skill_ids"]).issubset(skills)
            assert slot["skill_id"] in record["skill_ids"]
            assert record["source_id"] in sources
            assert record["adaptation"]["summary"].strip()

            review = record["review"]
            assert review["status"] == "approved"
            assert review["curator_id"] and review["reviewer_id"]
            assert review["curator_id"] != review["reviewer_id"]
            assert all(review["checks"].values())

            rubric = record["rubric"]
            assert len(rubric["criteria"]) == 3
            for criterion in rubric["criteria"]:
                assert criterion["criterion_type"] in slot["eligible_criterion_types"]
                assert [lvl["score"] for lvl in criterion["levels"]] == [0, 1, 2]
                assert criterion["equivalent_answers"].strip()

            domain_questions.append(
                Question(
                    id=QuestionId(qid),
                    version=record["version"],
                    category=record["category"],
                    language=record["language"],
                    prompt=record["prompt"],
                    skill_ids=tuple(SkillId(s) for s in record["skill_ids"]),
                    rubric_ref=VersionedRef(RubricId(rubric["id"]), rubric["version"]),
                    source_id=SourceId(record["source_id"]),
                    code=record["code"],
                    code_language=record["code_language"],
                    constraints=tuple(record["constraints"]),
                    difficulty=record["difficulty"],
                    review=ReviewMetadata(
                        status=ReviewStatus(review["status"]),
                        curator_id=review["curator_id"],
                        reviewer_id=review["reviewer_id"],
                        reviewed_at=datetime.fromisoformat(review["reviewed_at"]),
                        checks=ReviewChecks(**review["checks"]),
                    ),
                )
            )

    required_skills = {
        slot["category"]: SkillId(slot["skill_id"]) for slot in blueprint["slots"]
    }
    assert missing_coverage(required_skills, domain_questions) == {}


def test_c02_to_c05_review_fixtures_match_questions_and_verbatim_quotes() -> None:
    all_questions: dict[str, dict[str, object]] = {}
    for name in ("programming.json", "cases.json", "algorithms.json", "ai_review.json"):
        for item in _load_json(SEED_DIR / "questions" / name):
            all_questions[item["id"]] = item

    for fixture_name in ("p05.json", "c02.json", "c03.json", "c04.json", "c05.json"):
        fixture = _load_json(REVIEWS_DIR / fixture_name)
        assert fixture["example_only"] is False
        assert fixture["review_status"] == "approved"

        question = all_questions[fixture["question_id"]]
        assert fixture["rubric_id"] == question["rubric"]["id"]
        expected_criteria = [c["id"] for c in question["rubric"]["criteria"]]

        for sample in fixture["cases"]:
            assert [chk["criterion_id"] for chk in sample["checks"]] == expected_criteria
            for chk in sample["checks"]:
                assert chk["evidence_quote"] in sample["answer"]
            if any(chk["status"] == "insufficient_evidence" for chk in sample["checks"]):
                assert sample["expected_total"] is None
            else:
                assert sample["expected_total"] == sum(
                    chk["score"] for chk in sample["checks"]
                )


def test_c06_exercises_cover_all_seed_criterion_gaps_and_valid_prerequisites() -> None:
    skills = {item["id"] for item in _load_json(SEED_DIR / "skills.json")}
    [blueprint] = _load_json(SEED_DIR / "session_blueprints.json")
    sources = {item["id"]: item for item in _load_json(SEED_DIR / "source_registry.json")}
    raw_exercises = _load_json(SEED_DIR / "exercises.json")
    assert isinstance(raw_exercises, list)
    assert len(raw_exercises) >= 5

    exercises_by_id: dict[str, Exercise] = {}
    covered_pairs: set[tuple[str, str]] = set()

    for item in raw_exercises:
        assert item["example_only"] is False
        assert item["source_id"] in sources
        assert set(item["related_skill_ids"]).issubset(skills)
        assert "ước tính" in item["summary"].lower()

        review = item["review"]
        assert review["status"] == "approved"
        assert review["curator_id"] != review["reviewer_id"]

        exercise = Exercise(
            id=ExerciseId(item["id"]),
            version=item["version"],
            title=item["title"],
            summary=item["summary"],
            instructions=item["instructions"],
            related_skill_ids=tuple(SkillId(s) for s in item["related_skill_ids"]),
            source_id=SourceId(item["source_id"]),
            prerequisite_ids=tuple(ExerciseId(p) for p in item["prerequisite_ids"]),
            target_criterion_types=tuple(item["target_criterion_types"]),
            estimated_duration_minutes=item["estimated_duration_minutes"],
            observable_outcome=item["observable_outcome"],
            review=ReviewMetadata(
                status=ReviewStatus(review["status"]),
                curator_id=review["curator_id"],
                reviewer_id=review["reviewer_id"],
                reviewed_at=datetime.fromisoformat(review["reviewed_at"]),
                checks=ReviewChecks(**review["checks"]),
            ),
        )
        assert exercise.id not in exercises_by_id
        exercises_by_id[exercise.id] = exercise

        for skill_id in exercise.related_skill_ids:
            for ctype in exercise.target_criterion_types:
                covered_pairs.add((skill_id, ctype))

    # Every prerequisite must exist and graph must be acyclic
    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(ex_id: str) -> None:
        assert ex_id in exercises_by_id, f"Missing prerequisite exercise: {ex_id}"
        assert ex_id not in visiting, f"Cycle detected in exercise prerequisites at {ex_id}"
        if ex_id in visited:
            return
        visiting.add(ex_id)
        for prereq in exercises_by_id[ex_id].prerequisite_ids:
            _visit(prereq)
        visiting.remove(ex_id)
        visited.add(ex_id)

    for ex_id in exercises_by_id:
        _visit(ex_id)

    # Every (skill_id, criterion_type) declared in blueprint slots is covered
    for slot in blueprint["slots"]:
        for ctype in slot["eligible_criterion_types"]:
            assert (slot["skill_id"], ctype) in covered_pairs
