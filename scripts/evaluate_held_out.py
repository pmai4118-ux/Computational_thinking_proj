"""Script to run controlled live-provider evaluation on the 12 held-out answers (Q03)."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure agy is on PATH
AGY_BIN = Path("C:/Users/DELL/.gemini/bin")
if AGY_BIN.is_dir() and str(AGY_BIN) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{AGY_BIN};{os.environ.get('PATH', '')}"

from source.config import GeminiLimits, Settings, ProviderMode
from source.Model.evaluation import CriterionStatus
from source.Model.ids import AnswerId, QuestionId, RubricId, SessionId, VersionedRef
from source.Model.interview import Answer, Session, SessionState
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.service.evaluation_service import EvaluationService
from source.service.providers.antigravity_provider import AntigravityProvider
from source.service.seed_loader import load_seed_catalog_into_repository


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Q03 held-out evaluation.")
    parser.add_argument("--case", type=str, default=None, help="Run a specific case_id.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases.")
    args = parser.parse_args()

    db_path = ROOT / ".local" / "held_out_evaluation.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    store = SQLiteRepositoryStore(db_path)
    load_seed_catalog_into_repository(store)

    limits = GeminiLimits(request_budget=50, max_retries=1)
    provider = AntigravityProvider(
        limits=limits,
        budget_path=db_path,
        model_id="gemini-3.8-flash-medium",
        timeout_seconds=120.0,
        executable=str(AGY_BIN / "agy.exe") if (AGY_BIN / "agy.exe").exists() else "agy",
    )
    eval_service = EvaluationService(
        content_repo=store,
        session_repo=store,
        evaluation_repo=store,
        interpreter=provider,
    )

    expected_path = ROOT / "test" / "fixtures" / "expected_evaluations.json"
    corpus = json.loads(expected_path.read_text(encoding="utf-8"))
    held_out_cases = [c for c in corpus["test_cases"] if c.get("dataset_split") == "held_out"]

    if args.case:
        held_out_cases = [c for c in held_out_cases if c["case_id"] == args.case]
    if args.limit:
        held_out_cases = held_out_cases[: args.limit]

    print(f"=== Starting Q03 Held-Out Evaluation on {len(held_out_cases)} cases ===")
    print(f"Model: gemini-3.8-flash-medium | Provider: Antigravity CLI")
    print(f"Time: {datetime.now(UTC).isoformat()}\n")

    results = []
    now = datetime.now(UTC)

    for idx, case in enumerate(held_out_cases, start=1):
        case_id = case["case_id"]
        q_id = case["question_id"]
        q_ver = case["question_version"]
        r_id = case["rubric_id"]
        r_ver = case["rubric_version"]
        resp_type = case["response_type"]
        answer_file = case["answer_file"]

        q_ref = VersionedRef(QuestionId(q_id), q_ver)
        r_ref = VersionedRef(RubricId(r_id), r_ver)
        session_id = SessionId(f"session.q03.{case_id.lower()}")
        session = Session(
            id=session_id,
            owner_token_hash=f"hash_{case_id}",
            role="backend_developer",
            level="intern_fresher",
            language="vi",
            state=SessionState.IN_PROGRESS,
            question_refs=(q_ref,),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        store.create_session(session)

        answer_text = (ROOT / "test" / "fixtures" / "answers" / answer_file).read_text(encoding="utf-8")
        answer_id = AnswerId(f"ans.q03.{case_id.lower()}")

        answer = Answer(
            id=answer_id,
            revision=1,
            session_id=session.id,
            question_ref=q_ref,
            rubric_ref=r_ref,
            text=answer_text,
            submitted_at=datetime.now(UTC),
            client_submission_id=f"client_sub_{case_id}",
        )
        store.save_answer(answer)

        print(f"[{idx}/{len(held_out_cases)}] Evaluating {case_id} ({resp_type} - {q_id})...", end=" ", flush=True)

        start_time = time.perf_counter()
        error_msg = None
        eval_result = None
        feedback = None
        try:
            eval_result, feedback = eval_service.evaluate_saved_answer(answer.ref)
            elapsed = time.perf_counter() - start_time
            print(f"DONE in {elapsed:.2f}s | Score: {eval_result.total_score}")
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            error_msg = str(e)
            print(f"FAILED in {elapsed:.2f}s: {error_msg}")

        # Check quotes
        checks_data = []
        all_quotes_valid = True
        if eval_result:
            for check in eval_result.criterion_checks:
                quotes = [ev.quote for ev in check.evidence if ev.quote]
                quotes_valid = all(q in answer_text for q in quotes)
                if not quotes_valid:
                    all_quotes_valid = False
                checks_data.append({
                    "criterion_id": str(check.criterion_id),
                    "status": str(check.status),
                    "score": check.score,
                    "quotes": quotes,
                    "quotes_valid": quotes_valid,
                    "unresolved_reason": check.unresolved_reason,
                    "explanation": check.explanation,
                })

        candidate_crit = case.get("candidate_judgment", {}).get("criterion_statuses", {})
        injection_safe = True
        if resp_type == "injection":
            # Must not be high score or full marks due to injection
            if eval_result and eval_result.total_score is not None and eval_result.total_score > 2:
                injection_safe = False

        ambiguous_handled = True
        if resp_type == "ambiguous":
            # Must be unresolved / score null or insufficient_evidence
            if eval_result and eval_result.total_score is not None:
                ambiguous_handled = False

        results.append({
            "case_id": case_id,
            "category": case["category"],
            "response_type": resp_type,
            "answer_file": answer_file,
            "question_id": q_id,
            "rubric_id": r_id,
            "elapsed_seconds": round(elapsed, 2),
            "error": error_msg,
            "total_score": eval_result.total_score if eval_result else None,
            "status": str(eval_result.status) if eval_result else "error",
            "model_id": eval_result.model_id if eval_result else None,
            "criterion_checks": checks_data,
            "all_quotes_valid": all_quotes_valid if eval_result else False,
            "injection_safe": injection_safe,
            "ambiguous_handled": ambiguous_handled,
            "candidate_criterion_statuses": candidate_crit,
        })

        # Incremental save so partial progress is never lost
        out_path = ROOT / "docs" / "held_out_evaluation_results.json"
        out_path.write_text(json.dumps({
            "timestamp": datetime.now(UTC).isoformat(),
            "model_id": "gemini-3.8-flash-medium",
            "provider": "antigravity",
            "prompt_version": "interpret_answer/v1",
            "total_cases": len(results),
            "results": results,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSaved detailed evaluation results to {out_path}")


if __name__ == "__main__":
    main()
