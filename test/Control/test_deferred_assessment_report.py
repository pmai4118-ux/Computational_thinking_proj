"""The form-facing interview saves every answer before any provider call."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError


def test_deferred_four_question_flow_and_three_part_report(tmp_path: Path) -> None:
    provider = Mock(wraps=FixtureProvider())
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture", "DATABASE_PATH": str(tmp_path / "deferred.sqlite3"),
        }),
        interpreter=provider,
    )
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"evaluation_timing": "after_session"}).json()
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
            premature = client.post(
                f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate",
                json={"answer_revision": answer["revision"]},
            )
            assert premature.status_code == 409
            assert provider.interpret.call_count == 0
            session = client.post(
                f"/api/sessions/{session_id}/next", json={"from_question_index": index}
            ).json()

        assert session["state"] == "completed"
        before = client.get(f"/api/sessions/{session_id}/summary").json()
        assert before["report"]["status"] == "assessing"
        assert before["report"]["overview"]["evaluated_count"] == 0
        assert all(axis["observed_count"] == 0 for axis in before["report"]["overview"]["axes"])

        for answer in answers:
            path = f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate"
            first = client.post(path, json={"answer_revision": answer["revision"]})
            assert first.status_code == 200
            replay = client.post(path, json={"answer_revision": answer["revision"]})
            assert replay.status_code == 200
            assert replay.json() == first.json()
        assert provider.interpret.call_count == 4

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
            # A question may cover only some axes. The report counts actual rubric checks.
            assert len({item["axis_id"] for item in detail["findings"]}) < 4
            for finding in detail["findings"]:
                for evidence in finding["evidence"]:
                    if evidence["quote"] is not None:
                        assert detail["answer_text"][evidence["start_offset"]:evidence["end_offset"]] == evidence["quote"]
        assert "total_score" not in report["overview"]  # No unsupported global ability score.


def test_deferred_session_early_end_only_evaluates_saved_answers(tmp_path: Path) -> None:
    provider = Mock(wraps=FixtureProvider())
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture", "DATABASE_PATH": str(tmp_path / "early.sqlite3"),
        }),
        interpreter=provider,
    )
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={"evaluation_timing": "after_session"}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        saved = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"], "question_version": question["version"],
            "client_submission_id": "early-end", "text": "Em chưa biết đủ để giải thích.",
        }).json()["answer"]
        ended = client.post(f"/api/sessions/{session_id}/end", json={"reason": "student_requested"})
        assert ended.status_code == 200
        assert ended.json()["report"]["status"] == "assessing"
        evaluated = client.post(
            f"/api/sessions/{session_id}/answers/{saved['answer_id']}/evaluate",
            json={"answer_revision": 1},
        )
        assert evaluated.status_code == 200
        assert provider.interpret.call_count == 1
        report = client.get(f"/api/sessions/{session_id}/summary").json()["report"]
        assert report["status"] == "complete"
        assert report["overview"]["answered_count"] == 1
        assert report["overview"]["evaluated_count"] == 1
        assert len(report["details"]) == 4
        assert sum(item["answer_ref"] is None for item in report["details"]) == 3


def test_timeout_keeps_deferred_report_partial_until_saved_answer_retry(tmp_path: Path) -> None:
    fixture = FixtureProvider()
    provider = Mock()
    attempts = 0

    def interpret_once_timeout(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ProviderFailureError(ProviderErrorKind.TIMEOUT, "Synthetic timeout", retryable=True)
        return fixture.interpret(*args, **kwargs)

    provider.interpret.side_effect = interpret_once_timeout
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture", "DATABASE_PATH": str(tmp_path / "retry.sqlite3"),
        }),
        interpreter=provider,
    )
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={"evaluation_timing": "after_session"}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        original_text = "Bản trả lời gốc phải còn nguyên sau timeout."
        answer = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"], "question_version": question["version"],
            "client_submission_id": "timeout-original", "text": original_text,
        }).json()["answer"]
        client.post(f"/api/sessions/{session_id}/end", json={"reason": "student_requested"})
        path = f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate"
        failed = client.post(path, json={"answer_revision": 1})
        assert failed.status_code == 504
        partial = client.get(f"/api/sessions/{session_id}/summary").json()["report"]
        assert partial["status"] == "partial_failure"
        assert partial["details"][0]["answer_text"] == original_text
        assert partial["details"][0]["total_score"] is None
        assert partial["details"][0]["retryable"] is True
        retry = client.post(path, json={"answer_revision": 1})
        assert retry.status_code == 200
        assert attempts == 2
        complete = client.get(f"/api/sessions/{session_id}/summary").json()["report"]
        assert complete["status"] == "complete"
        assert complete["details"][0]["answer_text"] == original_text
