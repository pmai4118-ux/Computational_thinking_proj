"""Acceptance checks for U05 partial and complete session summaries."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_u05_summary_page_has_coverage_outcome_and_next_action_regions(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    response = ui_client.get(f"/sessions/{session_id}/summary")
    assert response.status_code == 200
    assert 'data-session-summary' in response.text
    assert "Tiến độ và độ phủ" in response.text
    assert "Kết quả từng câu" in response.text
    assert "Điểm cần luyện tiếp" in response.text
    assert "/static/js/summary.js" in response.text


def test_u05_never_converts_missing_total_to_zero_and_links_gaps_by_skill() -> None:
    summary_js = (ROOT_DIR / "source" / "view" / "static" / "js" / "summary.js").read_text(encoding="utf-8")
    summary_css = (ROOT_DIR / "source" / "view" / "static" / "css" / "summary.css").read_text(encoding="utf-8")

    assert 'outcome.total_score === null || outcome.total_score === undefined' in summary_js
    assert "unanswered_categories" in summary_js
    assert "unresolved_categories" in summary_js
    assert "observed_gaps" in summary_js
    assert "confirmed_gap_criterion_ids" in summary_js
    assert "/exercises?skill_id=" in summary_js
    assert "@media (max-width: 48rem)" in summary_css
