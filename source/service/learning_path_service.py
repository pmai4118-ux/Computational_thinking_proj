"""Catalog validation, prerequisite ordering and deterministic time allocation."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from source.Model.competency_profile import CompetencyProfileEntry, CompetencyState
from source.Model.learning_path import LearningCatalog, LearningPlanRequest

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data/learning/java_backend_v1.json"


class LearningPathService:
    def __init__(self, catalog_path: Path = CATALOG_PATH, *, catalog: LearningCatalog | None = None) -> None:
        self.catalog = catalog or LearningCatalog.model_validate_json(catalog_path.read_text(encoding="utf-8"))
        self.lessons = {lesson.id: lesson for lesson in self.catalog.lessons}
        self.validate()

    def validate(self) -> None:
        def unique(values: Iterable[str], label: str) -> set[str]:
            materialized = list(values)
            if len(materialized) != len(set(materialized)):
                raise ValueError(f"Duplicate {label} ID")
            return set(materialized)

        lessons = unique((x.id for x in self.catalog.lessons), "lesson")
        resources = unique((x.id for x in self.catalog.resources), "resource")
        courses = unique((x.id for x in self.catalog.courses), "course")
        unique((u.id for l in self.catalog.lessons for u in l.units), "unit")
        unique((p.id for l in self.catalog.lessons for p in l.practices), "practice")
        for lesson in self.catalog.lessons:
            if not set(lesson.prerequisite_ids) <= lessons:
                raise ValueError(f"Unknown prerequisite for {lesson.id}")
            if not set(lesson.course_ids) <= courses:
                raise ValueError(f"Unknown course for {lesson.id}")
            linked = {r for u in lesson.units for r in u.reading_ids} | {r for p in lesson.practices for r in p.resource_ids}
            if not linked <= resources:
                raise ValueError(f"Unknown resource for {lesson.id}")
        for ids in self.catalog.tracks.values():
            if not set(ids) <= lessons:
                raise ValueError("Track references unknown lesson")
        for bridge in self.catalog.profile_bridges:
            if not set(bridge.target_lesson_ids) <= lessons:
                raise ValueError("Profile bridge references unknown lesson")
        self._ordered(set(self.lessons), {})  # Detect cycles even in optional lessons.

    def _ordered(self, wanted: set[str], priorities: dict[str, float]) -> list[str]:
        remaining = {lid: set(self.lessons[lid].prerequisite_ids) & wanted for lid in wanted}
        ordered: list[str] = []
        while remaining:
            ready = [lid for lid, deps in remaining.items() if not deps]
            if not ready:
                raise ValueError("Prerequisite graph contains a cycle")
            current = min(ready, key=lambda lid: (-priorities.get(lid, 0), lid))
            ordered.append(current)
            del remaining[current]
            for dependencies in remaining.values():
                dependencies.discard(current)
        return ordered

    def plan(self, request: LearningPlanRequest, entries: Iterable[CompetencyProfileEntry] = ()) -> dict:
        completed = set(request.completed_lesson_ids)
        explicit = set(request.target_lesson_ids)
        unknown = (completed | explicit) - self.lessons.keys()
        if unknown:
            raise ValueError("Lesson ID không tồn tại: " + ", ".join(sorted(unknown)))
        warnings = [
            "Thời lượng là ước tính; hoàn thành bài tự học không phải xác nhận thành thạo.",
            "Ngân hàng phỏng vấn hiện chưa chuyên biệt Java; không suy diễn điểm Python thành năng lực Java.",
        ]
        reasons: dict[str, list[str]] = defaultdict(list)
        priorities: dict[str, float] = {}
        bridge_map = {b.source_skill_id: b for b in self.catalog.profile_bridges}
        allowed_track = set(self.catalog.tracks[request.track])
        profile_targets: set[str] = set()
        if request.use_profile:
            for entry in entries:
                bridge = bridge_map.get(entry.skill_id)
                if bridge is None or entry.state is not CompetencyState.NEEDS_PRACTICE:
                    continue
                for lid in bridge.target_lesson_ids:
                    if lid not in allowed_track:
                        continue
                    profile_targets.add(lid)
                    priorities[lid] = max(priorities.get(lid, 0.0), entry.selection_priority)
                    reason = f"Ôn kiến thức chuyển giao từ điểm thiếu {entry.skill_id} / {entry.criterion_type}; không xác nhận mức Java."
                    if reason not in reasons[lid]:
                        reasons[lid].append(reason)
        targets = explicit or (profile_targets if request.mode == "confirmed_gaps" and profile_targets else set(self.catalog.tracks[request.track]))
        if request.mode == "confirmed_gaps" and not profile_targets and not explicit:
            warnings.append("Chưa có điểm thiếu phù hợp có căn cứ; dùng lộ trình mục tiêu đã chọn, không tự gán kỹ năng yếu.")
        wanted: set[str] = set()

        def include(lid: str, parent: str | None = None) -> None:
            if lid in completed:
                return
            if parent:
                message = "Tiên quyết cho " + parent + ": " + self.lessons[parent].title
                if message not in reasons[lid]:
                    reasons[lid].append(message)
                priorities[lid] = max(priorities.get(lid, 0), priorities.get(parent, 0))
            if lid in wanted:
                return
            wanted.add(lid)
            for dependency in self.lessons[lid].prerequisite_ids:
                include(dependency, lid)

        for lid in sorted(targets, key=lambda value: (-priorities.get(value, 0), value)):
            include(lid)
        ordered = self._ordered(wanted, priorities)
        total = sum(self.lessons[lid].estimated_minutes for lid in ordered)
        weekly = request.hours_per_week * 60
        budget = weekly * request.weeks
        schedule: list[dict] = []
        remaining_budget = budget
        current_week, used = 1, 0
        planned = []
        for lid in ordered:
            lesson = self.lessons[lid]
            remaining = lesson.estimated_minutes
            allocated = 0
            while remaining > 0 and remaining_budget > 0:
                capacity = weekly - used
                amount = min(remaining, capacity, remaining_budget)
                schedule.append(dict(week=current_week,lesson_id=lid,minutes=amount))
                remaining -= amount
                remaining_budget -= amount
                allocated += amount
                used += amount
                if used == weekly:
                    current_week += 1
                    used = 0
            planned.append(dict(lesson_id=lid,title=lesson.title,estimated_minutes=lesson.estimated_minutes,
                allocated_minutes=allocated,remaining_minutes=remaining,
                priority=priorities.get(lid,0),reasons=reasons[lid] or ["Thuộc mục tiêu học đã xác nhận."],
                status="scheduled" if remaining == 0 else "partially_scheduled" if allocated else "deferred"))
        if total > budget:
            warnings.append(f"Quỹ thời gian thiếu {total-budget} phút. Các phần chưa xếp lịch vẫn được liệt kê; hãy tăng số tuần/giờ hoặc thu hẹp mục tiêu.")
        if completed & profile_targets:
            warnings.append("Một số bài đã tự đánh dấu vẫn liên quan điểm thiếu trong hồ sơ; tự đánh dấu không xóa bằng chứng đánh giá.")
        return dict(catalog_version=self.catalog.version,track=request.track,mode=request.mode,
            completion_basis="self_reported",completed_lesson_ids=sorted(completed),
            confirmed_gap_lesson_ids=sorted(profile_targets),target_lesson_ids=sorted(targets),
            total_estimated_minutes=total,available_minutes=budget,shortfall_minutes=max(0,total-budget),
            feasible=total<=budget,estimated_weeks=(total+weekly-1)//weekly,
            ordered_lessons=planned,schedule=schedule,warnings=warnings,
            privacy_note="Kế hoạch được tính theo request; tiến độ tự đánh dấu chỉ lưu trong trình duyệt. Hồ sơ đọc theo cookie hiện tại.")
