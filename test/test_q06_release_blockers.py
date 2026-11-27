"""Regression checks for Q06 release-blocking fixes, MVC-S boundaries, and release checklist."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import re
from unittest.mock import Mock

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.Control.schemas import ApiErrorResponse, ErrorCode
from source.main import create_app
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId, SessionId
from source.Model.interview import SessionState

ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT_DIR / "source"
STATIC_JS_DIR = SOURCE_DIR / "view" / "static" / "js"
_API_KEY_LEAK_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{20,}")


def _build_app(tmp_path: Path, db_name: str, interpreter: object | None = None):
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / db_name,
        gemini_timeout_seconds=10.0,
    )
    return create_app(settings=settings, interpreter=interpreter)


def test_q06_expired_session_blocks_evaluation_without_calling_provider(tmp_path: Path) -> None:
    """Q06-01: Expired sessions must return 410 SESSION_EXPIRED before invoking the provider."""
    provider = Mock()
    app = _build_app(tmp_path, "q06_expired_eval.sqlite3", interpreter=provider)

    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]

        submitted = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "q06-expired-eval-1",
                "text": "Câu trả lời đã lưu trước khi phiên hết hạn.",
            },
        )
        assert submitted.status_code == 201
        answer_id = submitted.json()["answer"]["answer_id"]

        session_repo = app.state.container.session_repo
        stored = session_repo.get_session(SessionId(session_id))
        assert stored is not None
        session_repo.update_session(replace(stored, state=SessionState.EXPIRED))

        session_eval = client.post(
            f"/api/sessions/{session_id}/answers/{answer_id}/evaluate",
            json={"answer_revision": 1},
        )
        assert session_eval.status_code == 410
        err1 = ApiErrorResponse.model_validate(session_eval.json())
        assert err1.error_code is ErrorCode.SESSION_EXPIRED
        assert err1.retryable is False

        answer_eval = client.post(
            f"/api/answers/{answer_id}/evaluate",
            json={"answer_revision": 1},
        )
        assert answer_eval.status_code == 410
        err2 = ApiErrorResponse.model_validate(answer_eval.json())
        assert err2.error_code is ErrorCode.SESSION_EXPIRED
        assert err2.retryable is False

        provider.interpret.assert_not_called()


def test_q06_unexpected_evaluation_error_returns_structured_api_error_and_preserves_answer(
    tmp_path: Path,
) -> None:
    """Q06-01: Non-provider runtime failures return ApiErrorResponse(EVALUATION_FAILED) without losing the answer."""
    provider = Mock()
    provider.interpret.side_effect = RuntimeError("Simulated unexpected internal error")
    app = _build_app(tmp_path, "q06_unexpected_eval.sqlite3", interpreter=provider)

    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]
        answer_text = "Nguyên văn câu trả lời phải còn nguyên sau lỗi hệ thống."

        submitted = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "q06-unexpected-1",
                "text": answer_text,
            },
        )
        assert submitted.status_code == 201
        answer_id = submitted.json()["answer"]["answer_id"]

        failed = client.post(
            f"/api/sessions/{session_id}/answers/{answer_id}/evaluate",
            json={"answer_revision": 1},
        )
        assert failed.status_code == 500
        err = ApiErrorResponse.model_validate(failed.json())
        assert err.error_code is ErrorCode.EVALUATION_FAILED
        assert err.retryable is True
        assert err.answer_ref is not None
        assert err.answer_ref.id == AnswerId(answer_id)

        latest = client.get(f"/api/sessions/{session_id}/answers/{answer_id}/evaluations/1")
        assert latest.status_code == 200
        assert latest.json()["result"]["status"] == "failed"
        assert latest.json()["result"]["failure_code"] == "EVALUATION_FAILED"
        assert latest.json()["result"]["total_score"] is None
        assert latest.json()["result"]["answer_text"] == answer_text

    saved = app.state.container.session_repo.get_answer(
        AnswerRevisionRef(AnswerId(answer_id), 1)
    )
    assert saved is not None
    assert saved.text == answer_text


def test_q06_review_template_and_scripts_provide_failed_evaluation_recovery(
    tmp_path: Path,
) -> None:
    """Q06-02: Workspace hides broken review CTA on failure and review page exposes retry recovery."""
    app = _build_app(tmp_path, "q06_recovery_ui.sqlite3")
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]
        submitted = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "q06-recovery-submit-1",
                "text": "Câu trả lời kiểm tra phục hồi lỗi trên giao diện review.",
            },
        )
        answer = submitted.json()["answer"]

        review = client.get(
            f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}"
        )
        assert review.status_code == 200
        assert 'id="retry-review-evaluation"' in review.text
        assert "Thử đánh giá lại" in review.text

    workspace_js = (STATIC_JS_DIR / "workspace.js").read_text(encoding="utf-8")
    evidence_js = (STATIC_JS_DIR / "evidence.js").read_text(encoding="utf-8")
    assert "hideOpenReview" in workspace_js
    assert "#open-review" in workspace_js
    assert "retrySavedEvaluation" in evidence_js
    assert "#retry-review-evaluation" in evidence_js


def test_q06_expired_session_status_is_localized_in_welcome_and_summary(
    tmp_path: Path,
) -> None:
    """Q06-03: Expired sessions show Vietnamese label 'Đã hết hạn' instead of raw English or 'Đã lưu'."""
    app = _build_app(tmp_path, "q06_expired_label.sqlite3")
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        session_repo = app.state.container.session_repo
        stored = session_repo.get_session(SessionId(session_id))
        assert stored is not None
        session_repo.update_session(replace(stored, state=SessionState.EXPIRED))

        welcome = client.get("/interview")
        assert welcome.status_code == 200
        assert "Đã hết hạn" in welcome.text

    summary_js = (STATIC_JS_DIR / "summary.js").read_text(encoding="utf-8")
    assert 'expired: "Đã hết hạn"' in summary_js


def test_q06_run_demo_script_resolves_configured_antigravity_exe() -> None:
    """Q06-04: run_demo.ps1 honors ANTIGRAVITY_EXECUTABLE and falls back to LOCALAPPDATA agy.exe."""
    script = (ROOT_DIR / "run_demo.ps1").read_text(encoding="utf-8")
    assert "Resolve-AntigravityExecutable" in script
    assert "ANTIGRAVITY_EXECUTABLE" in script
    assert r"agy\bin\agy.exe" in script
    assert "& $agyExe models" in script
    assert "gemini-3.8-flash-medium" in script


def test_q06_mvcs_layer_import_boundaries_hold() -> None:
    """Verify strict MVC-S import boundaries documented in AGENTS.md across source/."""
    forbidden_by_layer = {
        "Model": ("source.view", "source.Control", "source.service"),
        "service": ("source.view", "source.Control"),
        "Control": ("source.view",),
    }
    violations: list[tuple[str, str]] = []
    for layer, forbidden in forbidden_by_layer.items():
        for py_file in (SOURCE_DIR / layer).rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                imported: list[str] = []
                if isinstance(node, ast.Import):
                    imported = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported = [node.module]
                for module_name in imported:
                    if any(
                        module_name == prefix or module_name.startswith(f"{prefix}.")
                        for prefix in forbidden
                    ):
                        violations.append((str(py_file.relative_to(ROOT_DIR)), module_name))
    assert violations == []


def test_q06_release_checklist_records_blockers_and_honest_limits_without_secrets() -> None:
    checklist = (ROOT_DIR / "docs" / "release_checklist.md").read_text(encoding="utf-8")
    assert not _API_KEY_LEAK_PATTERN.search(checklist)
    for required in ("Q06-01", "Q06-02", "Q06-03", "Q06-04", "C07", "Q03", "Q07", "Q08"):
        assert required in checklist
