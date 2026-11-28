"""Recent session previews and the owner-scoped full history page."""
from html.parser import HTMLParser
from datetime import UTC, datetime, timedelta
from itertools import count

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def history_clock(monkeypatch):
    # Windows wall clocks can return identical timestamps for rapid API calls.
    start = datetime.now(UTC)
    ticks = count()

    class Clock:
        min = datetime.min

        @staticmethod
        def now(tz=UTC):
            return (start + timedelta(seconds=next(ticks))).astimezone(tz)

    monkeypatch.setattr("source.service.interview_service.datetime", Clock)


class HistoryRows(HTMLParser):
    def __init__(self, html: str):
        super().__init__()
        self.ids: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "li" and "data-session-id" in values:
            self.ids.append(values["data-session-id"])


def create_sessions(client: TestClient, count: int) -> list[str]:
    ids = []
    for _ in range(count):
        response = client.post("/api/sessions", json={"evaluation_timing": "after_session"})
        assert response.status_code == 201
        ids.append(response.json()["session_id"])
    return ids


def complete_existing_session(client: TestClient, session_id: str) -> None:
    session = client.get(f"/api/sessions/{session_id}").json()
    for index in range(session["progress"]["total_questions"]):
        question = session["current_question"]
        assert question is not None
        submitted = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": f"history-complete-{session_id}-{index}",
                "text": f"Câu trả lời hoàn chỉnh cho câu {index + 1}.",
            },
        )
        assert submitted.status_code == 201
        advanced = client.post(
            f"/api/sessions/{session_id}/next",
            json={"from_question_index": index},
        )
        assert advanced.status_code == 200
        session = advanced.json()


@pytest.mark.parametrize("url", ["/interview"])
def test_recent_preview_shows_latest_three_and_preserves_session_actions(ui_client, url):
    ids = create_sessions(ui_client, 5)
    complete_existing_session(ui_client, ids[-1])
    page = ui_client.get(url)
    assert page.status_code == 200
    assert HistoryRows(page.text).ids == list(reversed(ids[-3:]))
    assert 'href="/history" data-history-all' in page.text
    assert "Xem tất cả" in page.text
    assert f'href="/sessions/{ids[-1]}/summary"' in page.text
    assert f'href="/sessions/{ids[-2]}"' in page.text
    assert "Đã hoàn thành" in page.text
    # Ordinals are based on the full history, not reset to #1 for the preview.
    assert "Phiên luyện phỏng vấn #5" in page.text


def test_full_history_is_newest_first_and_does_not_leak_another_owners_sessions(ui_client):
    ids = create_sessions(ui_client, 5)
    page = ui_client.get("/history")
    assert page.status_code == 200
    assert HistoryRows(page.text).ids == list(reversed(ids))
    assert "Lịch sử phiên phỏng vấn" in page.text
    assert 'href="/history" aria-current="page"' in page.text
    assert "data-history-all" not in page.text
    with TestClient(ui_client.app) as stranger:
        private = stranger.get(f"/history?session_id={ids[0]}")
        assert private.status_code == 200
        assert HistoryRows(private.text).ids == []
        assert all(session_id not in private.text for session_id in ids)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_short_histories_do_not_add_placeholder_sessions(ui_client, count):
    ids = create_sessions(ui_client, count)
    for url in ("/interview", "/history"):
        response = ui_client.get(url)
        assert response.status_code == 200
        assert HistoryRows(response.text).ids == list(reversed(ids))
        if count == 0:
            assert "Chưa có phiên luyện tập nào" in response.text

    setup_page = ui_client.get("/setup")
    assert setup_page.status_code == 200
    assert HistoryRows(setup_page.text).ids == []
