"""Shared app fixture for independent U03-U06 view acceptance tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.main import create_app
from test.fixtures.repositories import InMemoryRepositoryStore
@pytest.fixture
def ui_client(tmp_path: Path):
    store = InMemoryRepositoryStore()
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "ui_acceptance_unused.sqlite3",
        gemini_timeout_seconds=10.0,
    )
    with TestClient(
        create_app(
            settings=settings,
            content_repo=store,
            session_repo=store,
            evaluation_repo=store,
            auto_seed=True,
        )
    ) as client:
        yield client


@pytest.fixture
def ui_session(ui_client: TestClient) -> dict[str, object]:
    response = ui_client.post("/api/sessions", json={})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def complete_ui_session(ui_client: TestClient, ui_session: dict[str, object]) -> dict[str, object]:
    """Finish all ordered answers and wait for queued fixture evaluations."""
    session_id = ui_session["session_id"]
    session = ui_session
    answers: list[dict[str, object]] = []
    for index in range(session["progress"]["total_questions"]):
        question = session["current_question"]
        assert question is not None
        response = ui_client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": f"complete-ui-{index}",
                "text": f"Synthetic test answer for question {index}.",
            },
        )
        assert response.status_code == 201
        answers.append(response.json()["answer"])
        advanced = ui_client.post(
            f"/api/sessions/{session_id}/next", json={"from_question_index": index}
        )
        assert advanced.status_code == 200
        session = advanced.json()

    ui_client.app.state.container.evaluation_queue._executor.submit(lambda: None).result(timeout=5)
    return {"session_id": session_id, "session": session, "answers": answers}
