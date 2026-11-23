"""Guard the C07 synthetic corpus against drifting away from Demo's reviewed seed."""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "test" / "fixtures"
QUESTION_FILES = ROOT / "data" / "seed" / "questions"
RESPONSE_TYPES = {"correct", "partial", "wrong", "equivalent", "ambiguous", "injection"}
STATUSES = {"met", "unmet", "insufficient_evidence"}


def _fingerprint(question: dict) -> str:
    fields = {key: question.get(key) for key in ("id", "version", "prompt", "code", "constraints", "rubric")}
    canonical = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_c07_cases_match_reviewed_demo_questions_and_remain_provisional() -> None:
    dataset = json.loads((FIXTURES / "expected_evaluations.json").read_text(encoding="utf-8"))
    questions = {
        question["id"]: question
        for path in QUESTION_FILES.glob("*.json")
        for question in json.loads(path.read_text(encoding="utf-8"))
    }
    cases = dataset["test_cases"]
    assert dataset["total_cases"] == len(cases) == 24
    assert len({case["case_id"] for case in cases}) == 24
    assert len({case["answer_file"] for case in cases}) == 24

    types_by_category: dict[str, set[str]] = defaultdict(set)
    split_by_category: Counter[tuple[str, str]] = Counter()
    split_by_type: Counter[tuple[str, str]] = Counter()
    for case in cases:
        question = questions[case["question_id"]]
        assert question["review"]["status"] == "approved"
        assert case["question_version"] == question["version"]
        assert case["rubric_id"] == question["rubric"]["id"]
        assert case["rubric_version"] == question["rubric"]["version"]
        assert case["question_fingerprint_sha256"] == _fingerprint(question)
        assert case["category"] == question["category"]
        assert case["response_type"] in RESPONSE_TYPES
        assert case["dataset_split"] in {"calibration", "held_out"}

        answer = FIXTURES / "answers" / case["answer_file"]
        assert answer.is_file()
        assert len(answer.read_text(encoding="utf-8").strip()) >= 50

        criterion_ids = {criterion["id"] for criterion in question["rubric"]["criteria"]}
        statuses = case["candidate_judgment"]["criterion_statuses"]
        assert set(statuses) == criterion_ids
        assert set(statuses.values()) <= STATUSES
        assert case["candidate_judgment"]["injection_instructions_must_be_ignored"] == (
            case["response_type"] == "injection"
        )
        assert case["annotation_status"] == "provisional_pending_independent_review"
        assert case["independent_reviews"] == []
        assert case["adjudicated_evaluation"] is None

        types_by_category[case["category"]].add(case["response_type"])
        split_by_category[case["category"], case["dataset_split"]] += 1
        split_by_type[case["response_type"], case["dataset_split"]] += 1

    assert len(types_by_category) == 4
    assert all(types == RESPONSE_TYPES for types in types_by_category.values())
    assert all(count == 3 for count in split_by_category.values())
    assert all(count == 2 for count in split_by_type.values())
    assert dataset["split_summary"] == {"calibration_count": 12, "held_out_count": 12}
    assert {path.name for path in (FIXTURES / "answers").glob("*.txt")} == {
        case["answer_file"] for case in cases
    }
