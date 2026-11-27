"""Helpers for the ordered, all-answers-first interview flow."""

from __future__ import annotations

from typing import Any


def complete_session(
    client: Any,
    *,
    first_answer_text: str = "Synthetic answer for question 0.",
    submission_prefix: str = "complete-session",
) -> tuple[str, list[dict[str, Any]]]:
    """Create a four-question session, answer each question in order, and finish it."""
    created = client.post("/api/sessions", json={})
    assert created.status_code == 201
    session = created.json()
    session_id = session["session_id"]
    answers: list[dict[str, Any]] = []

    for index in range(session["progress"]["total_questions"]):
        question = session["current_question"]
        assert question is not None
        text = (
            first_answer_text
            if index == 0
            else f"Synthetic answer for question {index}."
        )
        submitted = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": f"{submission_prefix}-{index}",
                "text": text,
            },
        )
        assert submitted.status_code == 201
        answers.append(submitted.json()["answer"])

        advanced = client.post(
            f"/api/sessions/{session_id}/next",
            json={"from_question_index": index},
        )
        assert advanced.status_code == 200
        session = advanced.json()

    assert session["progress"]["answered_count"] == session["progress"]["total_questions"]
    return session_id, answers


def wait_for_evaluation_queue(app: Any, *, timeout: float = 5.0) -> None:
    """Wait until all already-enqueued local fixture jobs have left the worker."""
    app.state.container.evaluation_queue._executor.submit(lambda: None).result(timeout=timeout)
