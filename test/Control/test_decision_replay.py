"""Tests for curated Decision Replay linked to evaluated answers and checkpoint rewind (X02/X03)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from test.fixtures.session_flow import complete_session, wait_for_evaluation_queue


def _app(tmp_path: Path, name: str):
    return create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / name),
        }),
        interpreter=FixtureProvider(),
    )


def _submit_case_text(client: TestClient, case_text: str, prefix: str) -> tuple[str, list[dict]]:
    created = client.post("/api/sessions", json={})
    assert created.status_code == 201
    session = created.json()
    session_id = session["session_id"]
    answers = []
    for idx in range(session["progress"]["total_questions"]):
        q = session["current_question"]
        text = case_text if q["category"] == "technical_case" else f"Synthetic answer {idx}."
        saved = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": q["id"],
                "question_version": q["version"],
                "client_submission_id": f"{prefix}-{idx}",
                "text": text,
            },
        )
        assert saved.status_code == 201
        answers.append(saved.json()["answer"])
        nxt = client.post(
            f"/api/sessions/{session_id}/next",
            json={"from_question_index": idx},
        )
        assert nxt.status_code == 200
        session = nxt.json()
    return session_id, answers


def test_answer_linked_decision_replay_diagnoses_gaps_rewinds_and_preserves_score(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, "replay-answer.sqlite3")
    with TestClient(app) as client, TestClient(app) as other:
        case_text = "Em dùng khóa cục bộ trong Python rồi cập nhật sau."
        session_id, answers = _submit_case_text(client, case_text, "replay-unmet")
        wait_for_evaluation_queue(app)

        prog_answer = answers[0]
        case_answer = answers[1]

        # Non-technical_case question cleanly reports unavailable instead of inventing scenarios.
        no_replay = client.get(
            f"/api/sessions/{session_id}/answers/{prog_answer['answer_id']}/replay?revision=1"
        )
        assert no_replay.status_code == 200
        assert no_replay.json()["available"] is False

        # Technical case question maps to its curated scenario and baseline diagnosis.
        avail = client.get(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/replay?revision=1"
        )
        assert avail.status_code == 200, avail.text
        avail_data = avail.json()
        assert avail_data["available"] is True
        assert avail_data["scenario"]["question_id"] in {
            "case.c03.inventory_race.v1",
            "case.c03.transfer_deadlock.v1",
        }

        started = client.post(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/replay?revision=1"
        )
        assert started.status_code == 201, started.text
        run = started.json()
        run_id = run["run_id"]
        assert run["linked_session_id"] == session_id
        assert run["linked_answer_ref"] == {"id": case_answer["answer_id"], "revision": 1}
        assert run["linked_answer_text"] == case_text
        assert run["linked_total_score"] == 0
        assert all(d["answer_verdict"] == "unmet" for d in run["checkpoint_diagnostics"])

        # Step through checkpoints 1 -> 2 -> 3
        cp1_id = run["current_checkpoint"]["id"]
        run = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"checkpoint_id": cp1_id, "option_id": run["current_checkpoint"]["options"][0]["id"]},
        ).json()
        cp2_id = run["current_checkpoint"]["id"]
        run = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"checkpoint_id": cp2_id, "option_id": run["current_checkpoint"]["options"][0]["id"]},
        ).json()
        cp3_id = run["current_checkpoint"]["id"]
        run = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"checkpoint_id": cp3_id, "option_id": run["current_checkpoint"]["options"][1]["id"]},
        ).json()
        assert run["completed"] is True
        assert len(run["steps"]) == 3

        # Rewind right back to checkpoint 2 (keeping step 1 intact!) and take an alternative choice.
        rewound = client.post(
            f"/api/replays/runs/{run_id}/rewind",
            json={"checkpoint_id": cp2_id},
        )
        assert rewound.status_code == 200, rewound.text
        rewound_data = rewound.json()
        assert rewound_data["completed"] is False
        assert rewound_data["current_checkpoint"]["id"] == cp2_id
        assert len(rewound_data["steps"]) == 1
        assert rewound_data["steps"][0]["checkpoint_id"] == cp1_id

        alt_opt = rewound_data["current_checkpoint"]["options"][1]
        branched = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"checkpoint_id": cp2_id, "option_id": alt_opt["id"]},
        ).json()
        assert len(branched["steps"]) == 2
        assert branched["steps"][1]["option_id"] == alt_opt["id"]

        # Original answer and published evaluation score remain completely untouched!
        orig_eval = client.get(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/evaluations/1"
        ).json()["result"]
        assert orig_eval["answer_text"] == case_text
        assert orig_eval["total_score"] == 0

        # Owner isolation on both run read and rewind
        assert other.get(f"/api/replays/runs/{run_id}").status_code == 403
        assert other.post(
            f"/api/replays/runs/{run_id}/rewind", json={"checkpoint_id": cp2_id}
        ).status_code == 403


def test_answer_linked_replay_flags_insufficient_evidence_and_supports_html_rewind(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, "replay-unresolved.sqlite3")
    with TestClient(app) as client:
        case_text = "Em đã viết chi tiết phần khóa trong tệp đính kèm."
        session_id, answers = _submit_case_text(client, case_text, "replay-unresolved")
        wait_for_evaluation_queue(app)
        case_answer = answers[1]

        start_form = client.post(
            f"/sessions/{session_id}/answers/{case_answer['answer_id']}/replay/start?revision=1",
            follow_redirects=False,
        )
        assert start_form.status_code == 303
        run_url = start_form.headers["location"]
        page = client.get(run_url)
        assert page.status_code == 200
        assert case_text in page.text
        assert "không gán hệ quả chắc chắn" in page.text

        # Choose option at checkpoint 1, then rewind via HTML form back to checkpoint 1.
        api_run = client.get(f"/api{run_url}").json()
        cp1_id = api_run["current_checkpoint"]["id"]
        opt1_id = api_run["current_checkpoint"]["options"][0]["id"]
        chosen = client.post(
            f"{run_url}/choose",
            data={"checkpoint_id": cp1_id, "option_id": opt1_id},
            follow_redirects=False,
        )
        assert chosen.status_code == 303
        after_choose = client.get(run_url)
        assert "Tua lại từ điểm chốt này" in after_choose.text

        rewound_page = client.post(
            f"{run_url}/rewind",
            data={"checkpoint_id": cp1_id},
            follow_redirects=False,
        )
        assert rewound_page.status_code == 303
        final_page = client.get(run_url)
        assert "Điểm chốt 1" in final_page.text


def test_standalone_replay_catalog_still_validates_invalid_choices(tmp_path: Path) -> None:
    app = _app(tmp_path, "replay-catalog.sqlite3")
    with TestClient(app) as client:
        catalog = client.get("/api/replays")
        assert catalog.status_code == 200
        scenarios = catalog.json()["scenarios"]
        assert len(scenarios) == 2

        started = client.post(f"/api/replays/{scenarios[0]['id']}/runs")
        assert started.status_code == 201
        run = started.json()
        bad = client.post(
            f"/api/replays/runs/{run['run_id']}/choose",
            json={"checkpoint_id": run["current_checkpoint"]["id"], "option_id": "invalid-opt"},
        )
        assert bad.status_code == 409
        assert client.get("/replays").status_code == 200
