"""Contracts for AI and fixture evidence interpreters (Algorithm 1, Steps 1-3)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Protocol

from source.Model.ids import AnswerRef, CriterionId, QuestionRef, RubricId
from source.Model.question import CompetencyRubric


@dataclass(frozen=True)
class EvaluationTaskInput:
    """
    Complete, immutable input snapshot required for Algorithm 1 (Step 1).
    Contains the question, constraints/requirements, context, executable rubrics,
    and the candidate's original answer text.
    """

    question_ref: QuestionRef
    question_prompt: str
    requirements: tuple[str, ...]
    context: str
    rubrics: tuple[CompetencyRubric, ...]
    answer_ref: AnswerRef
    answer_text: str
    example_only: bool = False

    def canonical_payload(self) -> dict[str, object]:
        """
        Build the canonical dictionary used for SHA-256 input hashing.
        Excludes provider, model, and prompt metadata so retries reuse completed reports.
        """
        return {
            "schema": "answerEvaluation/1",
            "example_only": self.example_only,
            "question": {
                "id": str(self.question_ref.id),
                "version": self.question_ref.version,
                "prompt": self.question_prompt,
                "requirements": list(self.requirements),
                "context": self.context,
            },
            "rubrics": [
                {
                    "id": str(rubric.id),
                    "version": rubric.version,
                    "competency": rubric.competency,
                    "review_rule": rubric.review_rule,
                    "scoring_rule": rubric.scoring_rule,
                    "criteria": [
                        {
                            "id": str(criterion.id),
                            "label": criterion.label,
                            "acceptance_rule": criterion.acceptance_rule,
                            "omission_means_unmet": criterion.omission_means_unmet,
                        }
                        for criterion in rubric.criteria
                    ],
                    "score_levels": [
                        {
                            "value": level.value,
                            "description": level.description,
                            "condition": level.condition,
                            "required_met": [str(cid) for cid in level.required_met],
                            "minimum_met": level.minimum_met,
                        }
                        for level in rubric.score_levels
                    ],
                }
                for rubric in self.rubrics
            ],
            "answer": {
                "id": str(self.answer_ref.id),
                "revision": self.answer_ref.revision,
                "text": self.answer_text,
            },
        }

    def input_digest(self) -> str:
        """Compute deterministic SHA-256 hex digest over the canonical JSON snapshot."""
        serialized = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProposedEvidenceItem:
    """
    Unverified evidence item proposed by the AI interpreter (Algorithm 1, Step 3).
    - evidence_type: Expected to be 'quote', 'ambiguous', or 'omission'.
    - observation: Explanation linking the evidence to the criterion's acceptance_rule.
    - location: Human-readable location reference inside the answer.
    - quote: Literal substring from answer_text (None when evidence_type == 'omission').
    - start_offset / end_offset: 0-based Unicode code-point slice offsets into answer_text.
    """

    evidence_type: str
    observation: str
    location: str
    quote: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass(frozen=True)
class ProposedCriterionJudgment:
    """
    Unverified criterion judgment proposed by the AI interpreter.
    Contains no numeric score; scoring is strictly reserved for Algorithm 2 in Python.
    """

    criterion_id: CriterionId
    status: str
    evidence: tuple[ProposedEvidenceItem, ...]


@dataclass(frozen=True)
class ProposedRubricJudgment:
    """Unverified grouping of criterion judgments for a single rubric."""

    rubric_id: RubricId
    criterion_checks: tuple[ProposedCriterionJudgment, ...]


@dataclass(frozen=True)
class ModelInterpretationOutput:
    """
    Structured output returned by an EvidenceInterpreter (Algorithm 1, Step 3).
    Must be validated by EvidenceValidator before any score calculation.
    """

    provider_name: str
    model_name: str
    prompt_version: str
    rubric_judgments: tuple[ProposedRubricJudgment, ...]


class EvidenceInterpreter(Protocol):
    """Protocol implemented by GeminiProvider, FixtureProvider, and RecordedInterpreter."""

    def interpret(self, task_input: EvaluationTaskInput) -> ModelInterpretationOutput:
        """
        Analyze task_input and return proposed criterion statuses and supporting evidence
        without calculating numeric rubric scores.
        """
        ...