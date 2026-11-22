"""Load one E04 answer bundle and write an evidence-linked JSON report."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from source.Control.interview_controller import OWNER_COOKIE_NAME
from source.Control.saved_evaluation_controller import SavedEvaluationController
from source.Control.schemas import EvaluateAnswerRequest, EvaluationResultDTO

from source.Model.ids import (
    AnswerId, CriterionId, QuestionId, RubricId, SessionId,
    SkillId, SourceId, VersionedRef,
)
from source.Model.evaluation import AnswerRevisionRef
from source.Model.interview import Answer
from source.Model.question import Criterion, CriterionLevel, Question, Rubric
from source.service.evaluation_service import EvaluationService, build_feedback
from source.service.providers.interfaces import EvidenceInterpreter, InterpretationBatch


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LevelInput(StrictInput):
    score: int = Field(ge=0)
    description: str = Field(min_length=1)


class CriterionInput(StrictInput):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    expectedEvidence: list[str] = Field(min_length=1)
    levels: list[LevelInput] = Field(min_length=1)


class RubricInput(StrictInput):
    id: str = Field(min_length=1)
    version: int = Field(ge=1)
    criteria: list[CriterionInput] = Field(min_length=1)


class QuestionInput(StrictInput):
    id: str = Field(min_length=1)
    version: int = Field(ge=1)
    category: str = Field(min_length=1)
    language: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    skillIds: list[str] = Field(min_length=1)
    sourceId: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)


class AnswerInput(StrictInput):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class EvaluationInput(StrictInput):
    question: QuestionInput
    rubric: RubricInput
    answer: AnswerInput


class _RecordingInterpreter:
    """Retain the one provider response used by the service for the CLI report."""

    def __init__(self, delegate: EvidenceInterpreter) -> None:
        self.delegate = delegate
        self.batch: InterpretationBatch | None = None

    def interpret(self, *, question: Question, rubric: Rubric, answer_text: str) -> InterpretationBatch:
        self.batch = self.delegate.interpret(
            question=question, rubric=rubric, answer_text=answer_text
        )
        return self.batch


class EvaluationController:
    """Translate a standalone answer bundle into an evidence-linked JSON report."""

    def __init__(
        self,
        service: EvaluationService,
        interpreter: EvidenceInterpreter,
        provider_name: str,
    ) -> None:
        self.service = service
        self.interpreter = interpreter
        self.provider_name = provider_name

    def evaluate_file(self, input_path: Path, output_path: Path) -> dict[str, Any]:
        source = json.loads(input_path.read_text(encoding="utf-8"))
        bundle = EvaluationInput.model_validate(source)
        question, rubric, answer = self.build_records(bundle)
        recorder = _RecordingInterpreter(self.interpreter)
        result = self.service.evaluate_answer(
            answer=answer, question=question, rubric=rubric, interpreter=recorder
        )
        batch = recorder.batch
        if batch is None:
            raise RuntimeError("The interpreter did not return an evaluation batch.")
        feedback = build_feedback(result, rubric)
        observations = {item.criterion_id: item for item in batch.observations}

        report = {
            "schemaVersion": "e04/1",
            "provider": self.provider_name,
            "modelId": result.model_id,
            "promptVersion": result.prompt_version,
            "elapsedMs": batch.elapsed_ms,
            "inputs": bundle.model_dump(mode="json"),
            "result": {
                "evaluationId": result.id,
                "status": result.status.value,
                "totalScore": result.total_score,
                "maximumScore": result.maximum_score,
                "evaluatedAt": result.evaluated_at.isoformat()
                if result.evaluated_at else None,
                "criterionChecks": [
                    {
                        "criterionId": check.criterion_id,
                        "status": check.status.value,
                        "score": check.score,
                        "satisfiedExpectedIndexes": (
                            list(observations[check.criterion_id].satisfied_expected_indexes)
                            if observations[check.criterion_id].satisfied_expected_indexes is not None
                            else None
                        ),
                        "explanation": check.explanation,
                        "unresolvedReason": check.unresolved_reason,
                        "evidence": [
                            {
                                "quote": evidence.quote,
                                "startOffset": evidence.start_offset,
                                "endOffset": evidence.end_offset,
                                "observation": evidence.observation,
                            }
                            for evidence in check.evidence
                        ],
                    }
                    for check in result.criterion_checks
                ],
            },
            "feedbackItems": [
                {
                    "criterionId": item.check.criterion_id,
                    "label": item.label,
                    "status": item.check.status.value,
                    "score": item.check.score,
                    "message": item.message,
                    "suggestion": item.suggestion,
                }
                for item in feedback.criteria
            ],
        }
        self.save_report(output_path, report)
        return report

    @staticmethod
    def build_records(bundle: EvaluationInput) -> tuple[Question, Rubric, Answer]:
        rubric = Rubric(
            id=RubricId(bundle.rubric.id),
            version=bundle.rubric.version,
            criteria=tuple(
                Criterion(
                    id=CriterionId(item.id),
                    label=item.label,
                    expected_evidence=tuple(item.expectedEvidence),
                    levels=tuple(
                        CriterionLevel(level.score, level.description)
                        for level in item.levels
                    ),
                )
                for item in bundle.rubric.criteria
            ),
        )
        question = Question(
            id=QuestionId(bundle.question.id),
            version=bundle.question.version,
            category=bundle.question.category,
            language=bundle.question.language,
            prompt=bundle.question.prompt,
            skill_ids=tuple(SkillId(skill) for skill in bundle.question.skillIds),
            rubric_ref=VersionedRef(rubric.id, rubric.version),
            source_id=SourceId(bundle.question.sourceId),
            constraints=tuple(bundle.question.constraints),
        )
        answer = Answer(
            id=AnswerId(bundle.answer.id),
            revision=1,
            session_id=SessionId("session.e04.demo"),
            question_ref=question.ref,
            rubric_ref=question.rubric_ref,
            text=bundle.answer.text,
            submitted_at=datetime.now(UTC),
        )
        return question, rubric, answer

    @staticmethod
    def save_report(output_path: Path, report: dict[str, Any]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=output_path.parent,
                prefix=".e04-", suffix=".json", delete=False,
            ) as stream:
                temp_name = stream.name
                stream.write(payload)
            os.replace(temp_name, output_path)
        finally:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)


def build_evaluation_router(controller: SavedEvaluationController) -> APIRouter:
    """Expose the P04 answer routes while sharing E09 ownership and presentation logic."""
    router = APIRouter(prefix="/api/answers", tags=["evaluations"])

    @router.post("/{answer_id}/evaluate", response_model=EvaluationResultDTO,
                 status_code=status.HTTP_200_OK)
    def evaluate_endpoint(
        answer_id: str, payload: EvaluateAnswerRequest, request: Request,
    ) -> EvaluationResultDTO:
        answer_ref = AnswerRevisionRef(AnswerId(answer_id), payload.answer_revision)
        session_id = controller.session_for_answer(answer_ref)
        return controller.evaluate(
            session_id, answer_ref, request.cookies.get(OWNER_COOKIE_NAME)
        ).result

    @router.get("/{answer_id}/evaluation", response_model=EvaluationResultDTO,
                status_code=status.HTTP_200_OK)
    def read_endpoint(
        answer_id: str, request: Request, answer_revision: int = Query(default=1, ge=1),
    ) -> EvaluationResultDTO:
        answer_ref = AnswerRevisionRef(AnswerId(answer_id), answer_revision)
        session_id = controller.session_for_answer(answer_ref)
        return controller.read(
            session_id, answer_ref, request.cookies.get(OWNER_COOKIE_NAME)
        ).result

    return router
