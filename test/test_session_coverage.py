import json
from dataclasses import replace
from pathlib import Path

import pytest

from source.Model.ids import QuestionId, RubricId, SkillId, SourceId, VersionedRef
from source.Model.question import Question
from source.service.coverage import missing_coverage

SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "seed"


@pytest.fixture
def required_skills() -> dict[str, SkillId]:
    skills = json.loads((SEED_DIR / "skills.json").read_text(encoding="utf-8"))
    [blueprint] = json.loads((SEED_DIR / "session_blueprints.json").read_text(encoding="utf-8"))
    slots = blueprint["slots"]
    catalog_ids = {skill["id"] for skill in skills}
    assert len(catalog_ids) == len(skills)
    assert all(skill["label"].strip() and skill["description"].strip() for skill in skills)
    assert [slot["category"] for slot in slots] == [
        "programming_knowledge",
        "technical_case",
        "algorithm_explanation",
        "ai_code_review",
    ]
    assert all(slot["skill_id"] in catalog_ids and slot["eligible_criterion_types"] for slot in slots)
    assert (blueprint["role"], blueprint["level"], blueprint["language"]) == (
        "backend_developer",
        "intern_fresher",
        "vi",
    )
    assert blueprint["allowed_difficulties"] == ["foundational", "applied"]
    assert blueprint["on_missing_coverage"] == "error"
    return {slot["category"]: SkillId(slot["skill_id"]) for slot in slots}


def _inventory(required_skills: dict[str, SkillId]) -> list[Question]:
    return [
        Question(
            id=QuestionId(f"question.synthetic.{category}"),
            version=1,
            category=category,
            language="vi",
            prompt="Câu tổng hợp",
            skill_ids=(skill,),
            rubric_ref=VersionedRef(RubricId("rubric.synthetic"), 1),
            source_id=SourceId("source.synthetic"),
        )
        for category, skill in required_skills.items()
    ]


def test_complete_inventory_covers_all_slots(required_skills: dict[str, SkillId]) -> None:
    assert missing_coverage(required_skills, _inventory(required_skills)) == {}


def test_empty_inventory_reports_every_slot(required_skills: dict[str, SkillId]) -> None:
    assert missing_coverage(required_skills, []) == required_skills


def test_question_with_wrong_skill_leaves_slot_uncovered(required_skills: dict[str, SkillId]) -> None:
    questions = _inventory(required_skills)
    first = questions[0]
    questions[0] = replace(first, skill_ids=questions[1].skill_ids)
    assert missing_coverage(required_skills, questions) == {first.category: required_skills[first.category]}


def test_two_revisions_of_one_id_cannot_fill_two_slots(required_skills: dict[str, SkillId]) -> None:
    questions = _inventory(required_skills)
    last = questions[-1]
    questions[-1] = replace(last, id=questions[0].id, version=2)
    assert missing_coverage(required_skills, questions) == {last.category: required_skills[last.category]}
