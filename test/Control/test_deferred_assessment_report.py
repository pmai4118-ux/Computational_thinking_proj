"""Background assessment, 4/4 completion gate, and 3-part session report contract."""

from __future__ import annotations

from pathlib import Path
import threading
from unittest.mock import Mock

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError
from test.fixtures.session_flow import complete_session, wait_for_evaluation_queue


def test_deferred_four_question_flow_and_three_part_report(tmp_path: Path) -> None:
    delegate = FixtureProvider()
    started = threading.Event()
    release = threading.Event()

    def gated_interpret(*args, **kwargs):
        started.set()
        assert release.wait(timeout=5)
        return delegate.interpret(*args, **kwargs)

    provider = Mock(side_effect=gated_interpret)
    interpreter = Mock()
    interpreter.interpret = provider
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture", "DATABASE_PATH": str(tmp_path / "deferred.sqlite3"),
        }),
        interpreter=interpreter,
    )
    with TestClient(app) as client:
        try:
            created = client.post("/api/sessions", json={}).json()
            session_id = created["session_id"]
            session = created
            answers = []
            for index in range(4):
                question = session["current_question"]
                saved = client.post(f"/api/sessions/{session_id}/answers", json={
                    "question_id": question["id"],
                    "question_version": question["version"],
                    "client_submission_id": f"deferred-{index}",
                    "text": f"Bài trả lời thử nghiệm số {index}; em sẽ kiểm tra kết quả.",
                })
                assert saved.status_code == 201
                answer = saved.json()["answer"]
                answers.append(answer)
                if index < 3:
                    premature = client.post(
                        f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate",
                        json={"answer_revision": answer["revision"]},
                    )
                    assert premature.status_code == 409
                session = client.post(
                    f"/api/sessions/{session_id}/next", json={"from_question_index": index}
                ).json()

            assert session["state"] == "completed"
            assert started.wait(timeout=5)
            before = client.get(f"/api/sessions/{session_id}/summary").json()
            assert before["report"]["status"] == "assessing"
            assert before["report"]["overview"]["evaluated_count"] < 4
        finally:
            release.set()
            wait_for_evaluation_queue(app)

        assert provider.call_count == 4
        for answer in answers:
            path = f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate"
            first = client.post(path, json={"answer_revision": answer["revision"]})
            assert first.status_code == 200
            replay = client.post(path, json={"answer_revision": answer["revision"]})
            assert replay.status_code == 200
            assert replay.json()["result"]["evaluation_id"] == first.json()["result"]["evaluation_id"]
        assert provider.call_count == 4

        report = client.get(f"/api/sessions/{session_id}/summary").json()["report"]
        assert report["status"] == "complete"
        assert set(report) == {"session_id", "status", "overview", "details", "proposals", "message"}
        assert len(report["details"]) == 4
        assert [axis["id"] for axis in report["overview"]["axes"]] == [
            "knowledge", "problem_analysis", "solution", "verification",
        ]
        for detail in report["details"]:
            assert detail["answer_text"]
            assert detail["evaluation_status"] == "completed"
            assert len({item["axis_id"] for item in detail["findings"]}) < 4
            for finding in detail["findings"]:
                for evidence in finding["evidence"]:
                    if evidence["quote"] is not None:
                        assert detail["answer_text"][evidence["start_offset"]:evidence["end_offset"]] == evidence["quote"]
        assert "total_score" not in report["overview"]


def test_early_end_is_rejected_until_all_four_questions_are_answered(tmp_path: Path) -> None:
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture", "DATABASE_PATH": str(tmp_path / "early.sqlite3"),
        }),
        interpreter=FixtureProvider(),
    )
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        saved = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"], "question_version": question["version"],
            "client_submission_id": "early-end", "text": "Em chưa biết đủ để giải thích.",
        })
        assert saved.status_code == 201
        ended = client.post(f"/api/sessions/{session_id}/end", json={"reason": "student_requested"})
        assert ended.status_code == 409
        assert client.get(f"/api/sessions/{session_id}/summary").status_code == 409
        wait_for_evaluation_queue(app)


def test_timeout_keeps_report_partial_until_saved_answer_retry(tmp_path: Path) -> None:
    fixture = FixtureProvider()
    provider = Mock()
    attempts = 0

    def interpret_first_timeout(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ProviderFailureError(ProviderErrorKind.TIMEOUT, "Synthetic timeout", retryable=True)
        return fixture.interpret(*args, **kwargs)

    provider.interpret.side_effect = interpret_first_timeout
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture", "DATABASE_PATH": str(tmp_path / "retry.sqlite3"),
        }),
        interpreter=provider,
    )
    with TestClient(app) as client:
        original_text = "Bản trả lời gốc phải còn nguyên sau timeout."
        session_id, answers = complete_session(
            client, first_answer_text=original_text, submission_prefix="timeout-original"
        )
        wait_for_evaluation_queue(app)

        partial = client.get(f"/api/sessions/{session_id}/summary").json()["report"]
        assert partial["status"] == "partial_failure"
        assert partial["details"][0]["answer_text"] == original_text
        assert partial["details"][0]["total_score"] is None
        assert partial["details"][0]["retryable"] is True

        path = f"/api/sessions/{session_id}/answers/{answers[0]['answer_id']}/evaluate"
        retry = client.post(path, json={"answer_revision": 1})
        assert retry.status_code == 200
        wait_for_evaluation_queue(app)
        assert attempts == 5

        complete = client.get(f"/api/sessions/{session_id}/summary").json()["report"]
        assert complete["status"] == "complete"
        assert complete["details"][0]["answer_text"] == original_text
