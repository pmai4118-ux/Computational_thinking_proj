"""Acceptance checks for U02 Welcome, Session History, and Setup pages."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.main import create_app
from test.fixtures.repositories import InMemoryRepositoryStore


def _make_app(tmp_path: Path, *, auto_seed: bool = True):
    store = InMemoryRepositoryStore()
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "u02_unused.sqlite3",
        gemini_timeout_seconds=10.0,
    )
    return create_app(
        settings=settings,
        content_repo=store,
        session_repo=store,
        evaluation_repo=store,
        auto_seed=auto_seed,
    )


def test_u02_welcome_and_setup_flow_creates_session_lists_history_and_collects_no_pii(
    tmp_path: Path,
) -> None:
    app = _make_app(tmp_path, auto_seed=True)

    with TestClient(app) as client:
        # 1. Empty history state on Welcome page
        welcome_empty = client.get("/")
        assert welcome_empty.status_code == 200
        assert "Chưa có phiên luyện tập nào trên trình duyệt này" in welcome_empty.text
        assert "Bắt đầu luyện tập" in welcome_empty.text
        assert "khoảng 25–35 phút" in welcome_empty.text

        # 2. Setup page asks only role/level/language, no CV or PII fields
        setup_resp = client.get("/setup")
        assert setup_resp.status_code == 200
        assert "Xác nhận bắt đầu" in setup_resp.text
        for forbidden_input in ('type="file"', 'name="email"', 'name="full_name"', 'name="cv"'):
            assert forbidden_input not in setup_resp.text

        # 3. Submitting Setup creates session via Controller and redirects to session shell
        post_resp = client.post(
            "/setup",
            content=urlencode(
                {
                    "role": "backend_developer",
                    "level": "intern_fresher",
                    "language": "vi",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert post_resp.status_code == 303
        location = post_resp.headers["location"]
        assert location.startswith("/sessions/session.")

        session_page = client.get(location)
        assert session_page.status_code == 200
        assert "Câu 1 / 4" in session_page.text
        assert "expected_evidence" not in session_page.text

        # 4. Returning to Welcome page shows populated session history with "Tiếp tục phiên"
        welcome_with_history = client.get("/")
        assert welcome_with_history.status_code == 200
        assert "Tiếp tục phiên" in welcome_with_history.text
        assert location in welcome_with_history.text


def test_u02_handles_empty_question_bank_invalid_setup_and_foreign_session_with_recovery_paths(
    tmp_path: Path,
) -> None:
    # Empty question bank -> 503 with alert and recovery links, no dead end
    empty_app = _make_app(tmp_path, auto_seed=False)
    with TestClient(empty_app) as client:
        err_resp = client.post(
            "/setup",
            content=urlencode(
                {
                    "role": "backend_developer",
                    "level": "intern_fresher",
                    "language": "vi",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert err_resp.status_code == 503
        assert 'role="alert"' in err_resp.text
        assert "Ngân hàng câu hỏi đã duyệt chưa đủ độ phủ" in err_resp.text
        assert 'href="/"' in err_resp.text

    # Invalid role -> 422 with recovery hint; foreign session -> 403 on welcome page with CTA
    seeded_app = _make_app(tmp_path, auto_seed=True)
    with TestClient(seeded_app) as owner_client, TestClient(seeded_app) as stranger_client:
        invalid_resp = owner_client.post(
            "/setup",
            content=urlencode(
                {"role": "unsupported_role", "level": "intern_fresher", "language": "vi"}
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert invalid_resp.status_code == 422
        assert 'role="alert"' in invalid_resp.text
        assert "Xác nhận bắt đầu" in invalid_resp.text

        created = owner_client.post("/api/sessions", json={}).json()
        forbid_page = stranger_client.get(f"/sessions/{created['session_id']}")
        assert forbid_page.status_code == 403
        assert 'role="alert"' in forbid_page.text
        assert "Bắt đầu luyện tập" in forbid_page.text
