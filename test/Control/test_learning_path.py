"""Catalog/plan endpoints do not disclose another anonymous owner's profile."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from source.Control.interview_controller import OWNER_COOKIE_NAME, hash_owner_token
from source.Model.competency_profile import CompetencyState
from source.Model.repositories.interfaces import RepositoryError
from source.config import load_settings
from source.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(settings=load_settings({"EVALUATION_PROVIDER": "fixture", "DATABASE_PATH": str(tmp_path / "learning.sqlite3")}))


def test_catalog_page_markdown_and_confirmed_plan(app):
    with TestClient(app) as client:
        assert client.get("/learning-path").status_code == 200
        data = client.get("/api/learning-paths/catalog").json()
        assert len(data["lessons"]) == 24
        md = client.get("/api/learning-paths/markdown")
        assert md.status_code == 200 and "text/markdown" in md.headers["content-type"]
        assert "JB24" in md.text and "MIT" in md.text
        assert client.post("/api/learning-paths/plan", json={}).status_code == 422
        good = client.post("/api/learning-paths/plan", json={"confirm_goal": True, "hours_per_week": 1, "weeks": 1})
        assert good.status_code == 200 and not good.json()["feasible"]
        assert good.json()["available_minutes"] == 60
        assert client.post("/api/learning-paths/plan", json={"confirm_goal":True,"target_lesson_ids":["unknown"]}).status_code == 422


def test_profile_is_read_only_for_cookie_owner_and_cannot_be_spoofed_in_payload(app):
    entry = SimpleNamespace(skill_id="skill.backend.data_consistency",state=CompetencyState.NEEDS_PRACTICE,selection_priority=0.5,criterion_type="failure_analysis")
    app.state.container.profile_service.refresh = Mock(side_effect=lambda owner: (entry,) if owner == hash_owner_token("owner-a") else ())
    with TestClient(app) as a, TestClient(app) as b:
        a.cookies.set(OWNER_COOKIE_NAME,"owner-a")
        b.cookies.set(OWNER_COOKIE_NAME,"owner-b")
        payload = {"confirm_goal":True,"mode":"confirmed_gaps"}
        assert a.post("/api/learning-paths/plan",json=payload).json()["target_lesson_ids"] == ["JB15"]
        assert b.post("/api/learning-paths/plan",json=payload).json()["confirmed_gap_lesson_ids"] == []
        assert b.post("/api/learning-paths/plan",json={**payload,"owner_token":"owner-a"}).status_code == 422
        assert a.post("/api/learning-paths/plan",json={**payload,"use_profile":False}).json()["confirmed_gap_lesson_ids"] == []


def test_profile_read_failure_preserves_explicit_goal_and_returns_fallback_plan(app):
    app.state.container.profile_service.refresh = Mock(side_effect=RepositoryError("unavailable"))
    with TestClient(app) as client:
        client.cookies.set(OWNER_COOKIE_NAME,"owner")
        response = client.post("/api/learning-paths/plan",json={"confirm_goal":True,"target_lesson_ids":["JB03"]})
        assert response.status_code == 200
        assert response.json()["target_lesson_ids"] == ["JB03"]
        assert any("Chưa đọc được hồ sơ" in warning for warning in response.json()["warnings"])
