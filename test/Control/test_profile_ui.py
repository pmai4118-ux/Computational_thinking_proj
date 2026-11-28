"""Tests for the Vietnamese Competency Profile UI page (/profile)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from test.fixtures.session_flow import complete_session, wait_for_evaluation_queue


def test_profile_page_renders_empty_state_then_owner_scoped_competency_data(tmp_path: Path) -> None:
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / "profile-ui.sqlite3"),
        }),
        interpreter=FixtureProvider(),
    )
    with TestClient(app) as student_a, TestClient(app) as student_b:
        empty = student_a.get("/profile")
        assert empty.status_code == 200
        assert "Hồ sơ năng lực qua các phiên" in empty.text
        assert "Bắt đầu phiên phỏng vấn đầu tiên" in empty.text

        session_id, answers = complete_session(
            student_a,
            first_answer_text="Câu trả lời ngắn thử nghiệm cho trang hồ sơ.",
            submission_prefix="profile-page",
        )
        wait_for_evaluation_queue(app)

        filled = student_a.get("/profile")
        assert filled.status_code == 200
        assert "Giải thích hành vi của mã" in filled.text
        assert f"/sessions/{session_id}/review?answer_id={answers[0]['answer_id']}" in filled.text
        assert "Cần luyện thêm" in filled.text

        # Different browser cookie must not see student_a's profile entries.
        isolated = student_b.get("/profile")
        assert isolated.status_code == 200
        assert "Bắt đầu phiên phỏng vấn đầu tiên" in isolated.text
        assert answers[0]["answer_id"] not in isolated.text


def test_profile_page_distinguishes_initial_met_from_repeated_strength_and_counts_unresolved(
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime
    from source.Model.competency_profile import (
        CompetencyProfileEntry,
        RecentCriterionScore,
    )
    from source.Model.evaluation import AnswerRevisionRef, CriterionStatus
    from source.Model.ids import AnswerId, CriterionId, EvaluationId, SessionId, SkillId
    from source.Control.interview_controller import OWNER_COOKIE_NAME

    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / "profile-confidence.sqlite3"),
        }),
        interpreter=FixtureProvider(),
    )
    owner_token = "owner-profile-labels-test"
    now = datetime.now(UTC)

    # Seed profile entries directly via a controlled profile service stub so we exercise
    # single-observation met, repeated strength, and insufficient_evidence rendering together.
    entries = (
        CompetencyProfileEntry(
            skill_id=SkillId("skill.programming.code_semantics"),
            criterion_type="behavior_explanation",
            observed_count=1,
            met_count=1,
            unmet_count=0,
            unresolved_count=0,
            latest_status=CriterionStatus.MET,
            latest_evaluated_at=now,
            latest_session_id=SessionId("session.one"),
            latest_answer_ref=AnswerRevisionRef(AnswerId("answer.one"), 1),
            latest_evaluation_id=EvaluationId("eval.one"),
            latest_evaluation_version=1,
            latest_criterion_id=CriterionId("c02.q1.semantics"),
            recent_scored=(RecentCriterionScore(2, 2, CriterionStatus.MET),),
        ),
        CompetencyProfileEntry(
            skill_id=SkillId("skill.backend.data_consistency"),
            criterion_type="invariant_preservation",
            observed_count=2,
            met_count=2,
            unmet_count=0,
            unresolved_count=0,
            latest_status=CriterionStatus.MET,
            latest_evaluated_at=now,
            latest_session_id=SessionId("session.two"),
            latest_answer_ref=AnswerRevisionRef(AnswerId("answer.two"), 1),
            latest_evaluation_id=EvaluationId("eval.two"),
            latest_evaluation_version=1,
            latest_criterion_id=CriterionId("c03.q1.invariant"),
            recent_scored=(
                RecentCriterionScore(2, 2, CriterionStatus.MET),
                RecentCriterionScore(2, 2, CriterionStatus.MET),
            ),
        ),
        CompetencyProfileEntry(
            skill_id=SkillId("skill.algorithms.correctness_and_complexity"),
            criterion_type="complexity_analysis",
            observed_count=1,
            met_count=0,
            unmet_count=0,
            unresolved_count=1,
            latest_status=CriterionStatus.INSUFFICIENT_EVIDENCE,
            latest_evaluated_at=now,
            latest_session_id=SessionId("session.three"),
            latest_answer_ref=AnswerRevisionRef(AnswerId("answer.three"), 1),
            latest_evaluation_id=EvaluationId("eval.three"),
            latest_evaluation_version=1,
            latest_criterion_id=CriterionId("c04.q1.complexity"),
            recent_scored=(),
        ),
    )
    app.state.container.profile_service.refresh = lambda _owner_hash: entries  # type: ignore[method-assign]

    with TestClient(app) as client:
        client.cookies.set(OWNER_COOKIE_NAME, owner_token)
        resp = client.get("/profile")
        assert resp.status_code == 200
        assert "Đạt ở lần quan sát đầu tiên" in resp.text
        assert "Đã vững (quan sát lặp lại)" in resp.text
        assert "Quan sát lặp lại ổn định" in resp.text
        assert "Chưa đủ căn cứ để kết luận" in resp.text
        assert ">repeated<" not in resp.text
        assert ">unresolved<" not in resp.text
        # Metric box for Chưa đủ căn cứ must reflect the 1 insufficient_evidence entry (not 0).
        assert (
            '<p class="metric-box__value">1</p>\n        <p class="metric-box__label">Chưa đủ căn cứ'
            in resp.text
        )
