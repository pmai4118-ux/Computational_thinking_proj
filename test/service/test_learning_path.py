"""Real prerequisite, budget and evidence boundaries for the Java roadmap."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from source.Model.competency_profile import CompetencyState
from source.Model.learning_path import LearningPlanRequest
from source.service.learning_path_export import catalog_markdown
from source.service.learning_path_service import LearningPathService


@pytest.fixture
def service():
    return LearningPathService()


def request(**kwargs):
    return LearningPlanRequest(confirm_goal=True, **kwargs)


def test_catalog_has_multiple_units_and_sourced_local_practices(service):
    assert len(service.catalog.lessons) == 24
    assert sum(len(l.units) for l in service.catalog.lessons) == 78
    assert sum(len(l.practices) for l in service.catalog.lessons) == 48
    assert all(len(l.units) >= 3 and len(l.practices) >= 2 for l in service.catalog.lessons)
    assert all(r.access == "free_reading" and r.url.startswith("https://") for r in service.catalog.resources)
    assert all(p.environment == "local" for l in service.catalog.lessons for p in l.practices)
    assert any(c.access == "paid_or_limited_preview" for c in service.catalog.courses)
    assert all(not c.java_specific for c in service.catalog.courses if c.id == "course-mit24")


def test_target_expands_prerequisites_and_orders_before_dependents(service):
    plan = service.plan(request(target_lesson_ids=("JB15",), hours_per_week=40, weeks=20))
    ids = [item["lesson_id"] for item in plan["ordered_lessons"]]
    assert {"JB01", "JB10", "JB11", "JB12", "JB14", "JB15"} <= set(ids)
    assert "JB24" not in ids
    for lid in ids:
        assert all(ids.index(dep) < ids.index(lid) for dep in service.lessons[lid].prerequisite_ids)
    assert plan["feasible"]


def test_insufficient_budget_keeps_deferred_work_and_never_exceeds_week(service):
    plan = service.plan(request(hours_per_week=1, weeks=2))
    assert not plan["feasible"] and plan["shortfall_minutes"] > 0
    assert sum(slot["minutes"] for slot in plan["schedule"]) == 120
    assert {slot["week"] for slot in plan["schedule"]} <= {1, 2}
    assert sum(item["remaining_minutes"] for item in plan["ordered_lessons"]) == plan["shortfall_minutes"]
    assert any(item["status"] == "deferred" for item in plan["ordered_lessons"])
    assert plan["ordered_lessons"][0]["status"] == "partially_scheduled"


def test_split_across_weeks_keeps_prerequisite_completion_before_next_lesson(service):
    plan = service.plan(request(target_lesson_ids=("JB03",), hours_per_week=1, weeks=20))
    schedule = plan["schedule"]
    for lid in ("JB02", "JB03"):
        for dependency in service.lessons[lid].prerequisite_ids:
            assert max(i for i, s in enumerate(schedule) if s["lesson_id"] == dependency) < min(i for i, s in enumerate(schedule) if s["lesson_id"] == lid)
    for week in {s["week"] for s in schedule}:
        assert sum(s["minutes"] for s in schedule if s["week"] == week) <= 60


def test_unknown_lesson_and_cycles_are_rejected(service):
    with pytest.raises(ValueError, match="không tồn tại"):
        service.plan(request(completed_lesson_ids=("not-a-lesson",)))
    first = service.catalog.lessons[0].model_copy(update={"prerequisite_ids": ("JB03",)})
    broken = service.catalog.model_copy(update={"lessons": (first, *service.catalog.lessons[1:])})
    with pytest.raises(ValueError, match="cycle"):
        LearningPathService(catalog=broken)
    first = service.catalog.lessons[0].model_copy(update={"prerequisite_ids": ("missing",)})
    broken = service.catalog.model_copy(update={"lessons": (first, *service.catalog.lessons[1:])})
    with pytest.raises(ValueError, match="Unknown prerequisite"):
        LearningPathService(catalog=broken)


def test_self_report_does_not_claim_mastery_and_can_empty_plan(service):
    ids = tuple(service.catalog.tracks["backend"])
    plan = service.plan(request(completed_lesson_ids=ids))
    assert plan["ordered_lessons"] == [] and plan["schedule"] == []
    assert plan["completion_basis"] == "self_reported"
    assert plan["feasible"] and plan["total_estimated_minutes"] == 0


def test_profile_only_bridges_confirmed_transferable_gaps(service):
    def observation(skill, state):
        return SimpleNamespace(skill_id=skill, state=state, selection_priority=0.75, criterion_type="invariant_preservation")
    plan = service.plan(request(mode="confirmed_gaps"), [observation("skill.backend.data_consistency", CompetencyState.NEEDS_PRACTICE)])
    assert plan["target_lesson_ids"] == ["JB15"]
    assert "chuyển giao" in " ".join(plan["ordered_lessons"][-1]["reasons"])
    for state in (CompetencyState.INSUFFICIENT_EVIDENCE, CompetencyState.OBSERVED_STRENGTH):
        result = service.plan(request(mode="confirmed_gaps"), [observation("skill.backend.data_consistency", state)])
        assert result["confirmed_gap_lesson_ids"] == []
    result = service.plan(request(mode="confirmed_gaps"), [observation("skill.programming.code_semantics", CompetencyState.NEEDS_PRACTICE)])
    assert result["confirmed_gap_lesson_ids"] == []  # Python evidence is not Java syntax evidence.
    result = service.plan(request(mode="confirmed_gaps",track="foundation"), [observation("skill.backend.data_consistency", CompetencyState.NEEDS_PRACTICE)])
    assert "JB15" not in result["target_lesson_ids"]  # A gap cannot silently expand the confirmed track.


def test_clarification_validation_and_determinism(service):
    with pytest.raises(ValidationError):
        LearningPlanRequest()
    for kwargs in ({"hours_per_week": True}, {"hours_per_week": 0}, {"weeks": 53}, {"completed_lesson_ids": ("JB01", "JB01")}):
        with pytest.raises(ValidationError):
            request(**kwargs)
    assert service.plan(request()) == service.plan(request())


def test_markdown_and_machine_catalog_stay_aligned(service):
    md = catalog_markdown(service.catalog)
    for lesson in service.catalog.lessons:
        assert f"## {lesson.id} —" in md
        for unit in lesson.units:
            assert unit.id in md
    for resource in service.catalog.resources:
        assert resource.url in md
    assert "TypeScript" in md and "Trả phí / preview" in md
