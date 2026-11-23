"""U07 acceptance checks for shared API transport and fixture-provider flow."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
JS_DIR = ROOT_DIR / "source" / "view" / "static" / "js"


def test_u07_api_client_is_loaded_before_each_screen_script(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    pages = {
        "/": None,
        "/setup": None,
        f"/sessions/{session_id}": "workspace.js",
        f"/sessions/{session_id}/review": "evidence.js",
        f"/sessions/{session_id}/summary": "summary.js",
        f"/sessions/{session_id}/exercises": "exercise.js",
    }

    for path, page_script in pages.items():
        response = ui_client.get(path)
        assert response.status_code == 200
        assert "/static/js/api_client.js" in response.text
        if page_script:
            assert response.text.index("/static/js/api_client.js") < response.text.index(
                f"/static/js/{page_script}"
            )


def test_u07_page_scripts_use_the_shared_same_origin_client() -> None:
    api_client = (JS_DIR / "api_client.js").read_text(encoding="utf-8")
    page_scripts = ("workspace.js", "evidence.js", "summary.js", "exercise.js")

    assert 'credentials: "same-origin"' in api_client
    assert 'window.InterviewApi = Object.freeze(api)' in api_client
    assert "/evaluations/${encode(answerRevision)}" in api_client
    assert '"/summary"' in api_client or "}/summary`" in api_client
    for script_name in page_scripts:
        script = (JS_DIR / script_name).read_text(encoding="utf-8")
        assert "fetch(" not in script
        assert "window.InterviewApi" in script


def test_u07_fixture_provider_flow_starts_answers_reviews_and_recommends(
    ui_client: TestClient,
) -> None:
    started = ui_client.post(
        "/setup",
        data={"role": "backend_developer", "level": "intern_fresher", "language": "vi"},
        follow_redirects=False,
    )
    assert started.status_code == 303
    set_cookie = started.headers["set-cookie"]
    assert set_cookie.startswith("interview_owner_id=")
    assert "httponly" in set_cookie.lower()
    assert ui_client.cookies.get("interview_owner_id")
    workspace_url = started.headers["location"]
    session_id = workspace_url.rsplit("/", maxsplit=1)[-1]
    session_response = ui_client.get(f"/api/sessions/{session_id}")
    assert session_response.status_code == 200
    ui_session = session_response.json()
    question = ui_session["current_question"]
    assert isinstance(question, dict)

    workspace = ui_client.get(workspace_url)
    assert workspace.status_code == 200
    assert 'data-workspace' in workspace.text

    submitted = ui_client.post(
        f"/api/sessions/{session_id}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "u07-fixture-flow-submit-1",
            "text": "x",
        },
    )
    assert submitted.status_code == 201
    answer = submitted.json()["answer"]

    evaluated = ui_client.post(
        f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate",
        json={"answer_revision": answer["revision"]},
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["result"]["status"] == "completed"

    review = ui_client.get(
        f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluations/{answer['revision']}"
    )
    assert review.status_code == 200
    assert review.json()["result"]["answer_text"] == "x"

    review_page = ui_client.get(
        f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}"
    )
    assert review_page.status_code == 200
    assert 'data-answer-revision="1"' in review_page.text
    assert f"/sessions/{session_id}/exercises" in review_page.text

    recommendations = ui_client.get(f"/api/sessions/{session_id}/exercises")
    assert recommendations.status_code == 200
    exercise_page = ui_client.get(f"/sessions/{session_id}/exercises")
    assert exercise_page.status_code == 200

    payload = recommendations.json()
    if payload["recommendations"]:
        suggestion = payload["recommendations"][0]
        detail = ui_client.get(
            f"/api/exercises/{suggestion['exercise_id']}?version={suggestion['version']}"
        )
        assert detail.status_code == 200
        assert detail.json()["instructions"]
