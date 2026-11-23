"""Acceptance checks for U06 exercise details and alternate availability."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_u06_exercise_page_accepts_session_skill_and_exercise_filters(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    response = ui_client.get(
        f"/sessions/{session_id}/exercises?skill_id=skill.backend.data_consistency&exercise_id=exercise.backend.rollback_invariant_test"
    )
    exercise_js = (ROOT_DIR / "source" / "view" / "static" / "js" / "exercise.js").read_text(encoding="utf-8")
    assert response.status_code == 200
    assert 'data-exercise-page' in response.text
    assert 'data-skill-id="skill.backend.data_consistency"' in response.text
    assert 'data-exercise-id="exercise.backend.rollback_invariant_test"' in response.text
    assert "/static/js/exercise.js" in response.text
    assert "Vì sao bài này phù hợp" in exercise_js


def test_u06_renders_only_api_exercises_and_explains_missing_alternate_action() -> None:
    exercise_js = (ROOT_DIR / "source" / "view" / "static" / "js" / "exercise.js").read_text(encoding="utf-8")

    assert "estimated_duration_minutes" in exercise_js
    assert "prerequisite_ids" in exercise_js
    assert "matched_gap" in exercise_js
    assert "source.required_notice" in exercise_js
    assert "eligible_alternate_question_available" in exercise_js
    assert "Không tạo bài thay thế tự động" in exercise_js
    assert "startPractice" in exercise_js
    assert "item.matched_gap.answer_ref" in exercise_js
    assert "api.startPractice(sessionId, answerId" in exercise_js
    api_client = (ROOT_DIR / "source" / "view" / "static" / "js" / "api_client.js").read_text(encoding="utf-8")
    assert "}/practice`" in api_client
