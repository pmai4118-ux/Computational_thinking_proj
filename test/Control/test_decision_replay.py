"""Tests for curated Decision Replay scenarios, deterministic traversal, and timeline UI (X02/X03)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider


def _app(tmp_path: Path, name: str):
    return create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / name),
        }),
        interpreter=FixtureProvider(),
    )


def test_decision_replay_traverses_curated_checkpoints_and_records_timeline(tmp_path: Path) -> None:
    app = _app(tmp_path, "replay.sqlite3")
    with TestClient(app) as client, TestClient(app) as other:
        catalog = client.get("/api/replays")
        assert catalog.status_code == 200
        scenarios = catalog.json()["scenarios"]
        assert len(scenarios) >= 2
        scenario = scenarios[0]
        assert scenario["assumptions"]

        # Start run
        started = client.post(f"/api/replays/{scenario['id']}/runs")
        assert started.status_code == 201, started.text
        run = started.json()
        run_id = run["run_id"]
        assert run["completed"] is False
        assert run["current_checkpoint"] is not None
        assert run["steps"] == []

        # Invalid option returns 409
        bad = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"checkpoint_id": run["current_checkpoint"]["id"], "option_id": "nonexistent"},
        )
        assert bad.status_code == 409

        # Walk through every checkpoint deterministically
        steps_taken = 0
        while not run["completed"]:
            cp = run["current_checkpoint"]
            assert cp is not None
            choice = cp["options"][0]
            resp = client.post(
                f"/api/replays/runs/{run_id}/choose",
                json={"checkpoint_id": cp["id"], "option_id": choice["id"]},
            )
            assert resp.status_code == 200, resp.text
            run = resp.json()
            steps_taken += 1
            assert len(run["steps"]) == steps_taken
            assert run["steps"][-1]["consequence_summary"]
            assert run["steps"][-1]["system_impact"]

        assert run["completed"] is True
        assert run["current_checkpoint"] is None
        assert steps_taken == scenario["checkpoint_count"]

        # Further choices on a completed run are refused with 409
        after_done = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"checkpoint_id": "cp1_locking_strategy", "option_id": "opt_app_mutex"},
        )
        assert after_done.status_code == 409

        # Owner isolation: another client cannot read or advance this run
        assert other.get(f"/api/replays/runs/{run_id}").status_code == 403
        assert other.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"checkpoint_id": "cp1", "option_id": "opt1"},
        ).status_code == 403


def test_decision_replay_html_pages_support_end_to_end_traversal(tmp_path: Path) -> None:
    app = _app(tmp_path, "replay-html.sqlite3")
    with TestClient(app) as client:
        index = client.get("/replays")
        assert index.status_code == 200
        assert "Tình huống Decision Replay đã kiểm duyệt" in index.text
        assert "replay.c03.flash_sale_inventory" in index.text

        started = client.post(
            "/replays/replay.c03.transfer_deadlock_order/start",
            follow_redirects=False,
        )
        assert started.status_code == 303
        run_url = started.headers["location"]
        page = client.get(run_url)
        assert page.status_code == 200
        assert "Điểm chốt 1" in page.text

        chosen = client.post(
            f"{run_url}/choose",
            data={"checkpoint_id": "cp1_lock_order", "option_id": "opt_canonical_order"},
            follow_redirects=False,
        )
        assert chosen.status_code == 303
        page2 = client.get(run_url)
        assert page2.status_code == 200
        assert "Điểm chốt 2" in page2.text
        assert "Phương án khuyến nghị" in page2.text
