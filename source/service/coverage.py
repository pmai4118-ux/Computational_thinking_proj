"""Check fixed session coverage against the eligible question inventory."""

from collections.abc import Iterable, Mapping

from source.Model.ids import QuestionId, SkillId
from source.Model.question import Question


def missing_coverage(
    required_skills: Mapping[str, SkillId],
    eligible_questions: Iterable[Question],
) -> dict[str, SkillId]:
    """Return uncovered categories and skills for a one-question-per-category blueprint.

    The caller filters questions by content eligibility and passes the active
    revision of each question. Each question ID can fill at most one slot.
    """
    missing = dict(required_skills)
    counted_ids: set[QuestionId] = set()
    for question in eligible_questions:
        if question.id in counted_ids:
            continue
        skill = missing.get(question.category)
        if skill is not None and skill in question.skill_ids:
            del missing[question.category]
            counted_ids.add(question.id)
    return missing
