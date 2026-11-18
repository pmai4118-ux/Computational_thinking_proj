"""
Question bank validation (Task C08) and P03-to-CompetencyRubric normalization adapter.
Ensures seed questions preserve 0/1/2 multi-level scoring via explicit sub-criteria
(required_met and minimum_met) instead of collapsing into binary 0/2 scores.
"""

from __future__ import annotations

import json
from pathlib import Path
from pydantic import ValidationError

from source.Model.answerData import EvaluationInput
from source.Model.questionBankData import BankQuestion, QuestionSample
from source.Model.repositories.questionRepository import QuestionRepository
from source.service.evaluationErrors import EvaluationError, malformed_input_error
from source.service.evidenceReview import EvidenceReview
from source.service.rubricRules import RubricRules
from source.Model.ids import (
    AnswerRef,
    CriterionId,
    QuestionId,
    QuestionRef,
    RubricId,
    SourceId,
)
from source.Model.question import (
    CompetencyRubric,
    ExecutableCriterion,
    ExecutableScoreLevel,
)
from source.service.evaluationErrors import malformed_input_error
from source.service.providers.interfaces import EvaluationTaskInput


class QuestionBankService:
    """
    Validates curated seed question files against source_registry.json and converts
    question records into executable EvaluationTaskInput instances for Algorithm 1 & 2.
    """

    dimensionNames = ("Knowledge", "Analysis", "Testing", "Implementation")
    reviewChecks = ("sourceAndLicense", "technicalCorrectness", "rubricBoundaries", "equivalentAnswers", "referenceAnswers")

    def __init__(self, repository: QuestionRepository | None = None, demoMode: bool = True) -> None:
        self.repository = repository
        self.demoMode = demoMode

    def readQuestions(self) -> dict[str, BankQuestion]:
        if self.repository is None:
            raise EvaluationError("questionBankInvalid", "Repository is required to read questions.")
        try:
            catalog = self.repository.loadCatalog()
        except (OSError, ValueError, ValidationError) as error:
            raise EvaluationError("questionBankInvalid", "Cannot load the question bank. Check its schema and path.") from error
        questions = {}
        for item in catalog.questions:
            if item.questionId in questions:
                raise EvaluationError("questionBankInvalid", "Question IDs must be unique.")
            self.validateQuestion(item)
            questions[item.questionId] = item
        return questions

    def validateQuestion(self, item: BankQuestion) -> None:
        rules = RubricRules()
        rules.validateInputs(item.template)
        if item.questionId != item.template.question.questionId:
            raise EvaluationError("questionBankInvalid", "Question and template IDs must match.")
        if tuple(dimension.name for dimension in item.dimensions) != self.dimensionNames:
            raise EvaluationError("questionBankInvalid", "Declare the four dimensions in their standard order.")
        applicable = tuple(dimension.name for dimension in item.dimensions if dimension.applies)
        if tuple(rubric.competency for rubric in item.template.rubrics) != applicable:
            raise EvaluationError("questionBankInvalid", "Applicable dimensions must match the rubrics exactly.")
        if item.review.status == "approved":
            review = item.review
            approved = bool(review.reviewerId and review.reviewerId != review.curatorId and review.reviewedAt)
            approved = approved and all(review.checks.get(name) is True for name in self.reviewChecks)
            approved = approved and item.source.licenseStatus == "verified" and bool(item.source.licenseId and item.source.licenseUrl and item.source.sourceUrl)
            approved = approved and all(sample.referenceStatus == "human_reviewed" for sample in item.samples)
            if not approved or item.template.exampleOnly:
                raise EvaluationError("contentUnapproved", "Approval requires independent review, verified provenance and reviewed references.")
        elif not item.template.exampleOnly:
            raise EvaluationError("contentUnapproved", "Pending content must remain explicitly marked exampleOnly.")
        if not self.demoMode and item.review.status != "approved":
            raise EvaluationError("contentUnapproved", "This question has not been approved for assessed use.")
        caseNames = [sample.caseName for sample in item.samples]
        if len(caseNames) != len(set(caseNames)):
            raise EvaluationError("questionBankInvalid", "Sample names must be unique within a question.")

    def getQuestion(self, questionId: str | None = None) -> BankQuestion:
        questions = self.readQuestions()
        selectedId = questionId or next(iter(questions))
        if selectedId not in questions:
            raise EvaluationError("unknownQuestion", "Select an available question.")
        return questions[selectedId]

    def getSample(self, item: BankQuestion, caseName: str) -> QuestionSample:
        sample = next((sample for sample in item.samples if sample.caseName == caseName), None)
        if sample is None:
            raise EvaluationError("unknownExample", "Select an available sample for this question.")
        inputs = self.sampleInputs(item, sample)
        if sample.recording.inputHash != inputs.inputDigest():
            raise EvaluationError("recordingMismatch", "The sample recording belongs to another input or rubric version.")
        EvidenceReview().validateInterpretation(inputs, sample.recording.interpretation)
        return sample

    def sampleInputs(self, item: BankQuestion, sample: QuestionSample) -> EvaluationInput:
        payload = item.template.model_dump()
        payload["answer"].update(answerId=f"answer.{item.questionId}.{sample.caseName}", revision=1, originalText=sample.answerText)
        return EvaluationInput.model_validate(payload)

    def describeQuestion(self, item: BankQuestion) -> dict:
        inputs = item.template
        return {
            "questionId": item.questionId,
            "title": item.title,
            "version": inputs.question.version,
            "prompt": inputs.question.prompt,
            "context": inputs.question.context,
            "requirements": list(inputs.question.requirements),
            "expectedLevel": inputs.question.expectedLevel,
            "dimensions": [dimension.model_dump() for dimension in item.dimensions],
            "rubrics": [rubric.model_dump(mode="json") for rubric in inputs.rubrics],
            "exampleOnly": inputs.exampleOnly,
            "reviewStatus": item.review.status,
            "source": item.source.model_dump(mode="json"),
            "examples": [{"caseName": sample.caseName, "canPreview": True, "referenceStatus": sample.referenceStatus} for sample in item.samples],
        }

    def load_source_registry(self, source_registry_path: Path) -> dict[str, dict[str, object]]:
        """Load and index source_registry.json by source ID, rejecting example_only records."""
        try:
            records = json.loads(source_registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise malformed_input_error(
                f"Kh\xf4ng th\u1ec3 \u0111\u1ecdc t\u1ec7p \u0111\u0103ng k\xfd ngu\u1ed3n '{source_registry_path}': {exc}"
            ) from exc

        if not isinstance(records, list):
            raise malformed_input_error("T\u1ec7p source_registry.json ph\u1ea3i ch\u1ee9a m\u1ed9t m\u1ea3ng JSON.")

        indexed: dict[str, dict[str, object]] = {}
        for index, entry in enumerate(records):
            if not isinstance(entry, dict):
                raise malformed_input_error(
                    f"B\u1ea3n ghi ngu\u1ed3n t\u1ea1i v\u1ecb tr\xed {index} kh\xf4ng ph\u1ea3i object."
                )
            source_id = entry.get("id")
            if not isinstance(source_id, str) or not source_id.strip():
                raise malformed_input_error(
                    f"B\u1ea3n ghi ngu\u1ed3n t\u1ea1i v\u1ecb tr\xed {index} thi\u1ebfu tr\u01b0\u1eddng 'id'."
                )
            if entry.get("example_only") is True:
                raise malformed_input_error(
                    f"Ngu\u1ed3n '{source_id}' \u0111\u01b0\u1ee3c \u0111\xe1nh d\u1ea5u example_only=true, kh\xf4ng \u0111\u01b0\u1ee3c import."
                )
            if source_id in indexed:
                raise malformed_input_error(f"Tr\xf9ng m\xe3 ngu\u1ed3n '{source_id}' trong source_registry.")
            indexed[source_id] = entry

        return indexed

    def validate_seed_question_record(
        self,
        record: dict[str, object],
        source_registry: dict[str, dict[str, object]],
        require_approved_review: bool = False,
    ) -> None:
        """
        Task C08:
        Validate a single P03 seed question dictionary for required identity, provenance,
        rubric structure, and review metadata.
        """
        if record.get("example_only") is True:
            raise malformed_input_error(
                f"C\xe2u h\u1ecfi '{record.get('id')}' l\xe0 m\u1eabu minh h\u1ecda (example_only=true), kh\xf4ng \u0111\u01b0\u1ee3c n\u1ea1p v\xe0o phi\xean th\u1eadt."
            )

        question_id = record.get("id")
        version = record.get("version")
        prompt = record.get("prompt")
        source_id = record.get("source_id")

        if not isinstance(question_id, str) or not question_id.strip():
            raise malformed_input_error("B\u1ea3n ghi c\xe2u h\u1ecfi thi\u1ebfu 'id' h\u1ee3p l\u1ec7.")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise malformed_input_error(f"C\xe2u h\u1ecfi '{question_id}' c\xf3 'version' kh\xf4ng h\u1ee3p l\u1ec7.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise malformed_input_error(f"C\xe2u h\u1ecfi '{question_id}' thi\u1ebfu n\u1ed9i dung 'prompt'.")
        if not isinstance(source_id, str) or source_id not in source_registry:
            raise malformed_input_error(
                f"C\xe2u h\u1ecfi '{question_id}' tham chi\u1ebfu t\u1edbi source_id '{source_id}' ch\u01b0a \u0111\u0103ng k\xfd."
            )

        source_entry = source_registry[source_id]
        license_info = source_entry.get("license")
        license_status = license_info.get("status") if isinstance(license_info, dict) else None
        if license_status in {None, "not_checked", "incompatible"}:
            raise malformed_input_error(
                f"Ngu\u1ed3n '{source_id}' c\u1ee7a c\xe2u h\u1ecfi '{question_id}' c\xf3 tr\u1ea1ng th\xe1i gi\u1ea5y ph\xe9p '{license_status}' kh\xf4ng h\u1ee3p l\u1ec7."
            )

        if require_approved_review:
            review = record.get("review")
            status = review.get("status") if isinstance(review, dict) else None
            curator = review.get("curator_id") if isinstance(review, dict) else None
            reviewer = review.get("reviewer_id") if isinstance(review, dict) else None
            if status != "approved" or not curator or not reviewer or curator == reviewer:
                raise malformed_input_error(
                    f"C\xe2u h\u1ecfi '{question_id}' ch\u01b0a ho\xe0n t\u1ea5t quy tr\xecnh ki\u1ec3m duy\u1ec7t \u0111\u1ed9c l\u1eadp (status='{status}')."
                )

    def adapt_p03_question_to_task_input(
        self,
        question_record: dict[str, object],
        answer_ref: AnswerRef,
        answer_text: str,
    ) -> EvaluationTaskInput:
        """
        Convert a P03 seed question dictionary (from data/seed/questions/*.json) into an
        executable EvaluationTaskInput for Algorithm 1 and Algorithm 2.

        How 0 / 1 / 2 scoring granularity is preserved:
        - In P03 seed files, each criterion inside `question.rubric.criteria` represents a
          competency area with a 0/1/2 scale and multiple bullets in `expected_evidence`.
        - If `expected_evidence` has >= 2 items, this adapter splits them into foundational
          sub-criterion A (`<id>.part1`) and supplementary sub-criterion B (`<id>.part2`...),
          configuring:
            * Level 0: required_met=(), minimum_met=0
            * Level 1: required_met=(), minimum_met=1 (achieving any core sub-criterion gives partial score 1)
            * Level 2: required_met=(all sub-criteria), minimum_met=len(sub-criteria) (achieving all gives full score 2)
        - If `expected_evidence` has 1 item, it configures Level 0 (0 met) and Level 2 (1 met).
        """
        question_id = str(question_record.get("id") or "").strip()
        version = question_record.get("version")
        prompt = str(question_record.get("prompt") or "").strip()

        if not question_id or not isinstance(version, int) or version < 1 or not prompt:
            raise malformed_input_error("B\u1ea3n ghi c\xe2u h\u1ecfi P03 thi\u1ebfu id, version ho\u1eb7c prompt h\u1ee3p l\u1ec7.")

        code_snippet = question_record.get("code")
        full_prompt = (
            f"{prompt}\n\nM\xe3 ngu\u1ed3n \u0111\xednh k\xe8m:\n{code_snippet}"
            if isinstance(code_snippet, str) and code_snippet.strip()
            else prompt
        )

        raw_constraints = question_record.get("constraints")
        requirements = (
            tuple(str(c).strip() for c in raw_constraints if str(c).strip())
            if isinstance(raw_constraints, list)
            else ("Tr\u1ea3 l\u1eddi \u0111\xfang tr\u1ecdng t\xe2m c\xe2u h\u1ecfi k\u1ef9 thu\u1eadt.",)
        )

        adaptation = question_record.get("adaptation")
        context = (
            str(adaptation.get("summary") or "").strip()
            if isinstance(adaptation, dict) and adaptation.get("summary")
            else f"Role: {question_record.get('role', 'backend_developer')} ({question_record.get('level', 'intern_fresher')})"
        )

        raw_rubric = question_record.get("rubric")
        if not isinstance(raw_rubric, dict):
            raise malformed_input_error(f"C\xe2u h\u1ecfi '{question_id}' thi\u1ebfu \u0111\u1ed1i t\u01b0\u1ee3ng 'rubric'.")

        rubric_version = int(raw_rubric.get("version", 1))
        raw_criteria = raw_rubric.get("criteria")
        if not isinstance(raw_criteria, list) or not raw_criteria:
            raise malformed_input_error(f"Rubric c\u1ee7a c\xe2u h\u1ecfi '{question_id}' kh\xf4ng c\xf3 ti\xeau ch\xed n\xe0o.")

        competency_rubrics: list[CompetencyRubric] = []
        for raw_criterion in raw_criteria:
            if not isinstance(raw_criterion, dict):
                raise malformed_input_error(f"Ti\xeau ch\xed trong c\xe2u h\u1ecfi '{question_id}' kh\xf4ng h\u1ee3p l\u1ec7.")
            competency_rubrics.append(
                self._convert_p03_criterion_to_competency_rubric(
                    raw_criterion=raw_criterion,
                    rubric_version=rubric_version,
                )
            )

        example_only = bool(question_record.get("example_only", False))

        return EvaluationTaskInput(
            question_ref=QuestionRef(id=QuestionId(question_id), version=version),
            question_prompt=full_prompt,
            requirements=requirements,
            context=context,
            rubrics=tuple(competency_rubrics),
            answer_ref=answer_ref,
            answer_text=answer_text,
            example_only=example_only,
        )

    def _convert_p03_criterion_to_competency_rubric(
        self,
        raw_criterion: dict[str, object],
        rubric_version: int,
    ) -> CompetencyRubric:
        """
        Convert one P03 criterion (with expected_evidence[] and levels 0/1/2) into an
        executable CompetencyRubric with sub-criteria and deterministic ScoreLevels.
        """
        base_id = str(raw_criterion.get("id") or "").strip()
        label = str(raw_criterion.get("label") or "").strip()
        if not base_id or not label:
            raise malformed_input_error("Ti\xeau ch\xed P03 thi\u1ebfu 'id' ho\u1eb7c 'label'.")

        raw_evidence_list = raw_criterion.get("expected_evidence")
        evidence_points = (
            [str(item).strip() for item in raw_evidence_list if str(item).strip()]
            if isinstance(raw_evidence_list, list)
            else []
        )
        if not evidence_points:
            raise malformed_input_error(
                f"Ti\xeau ch\xed '{base_id}' thi\u1ebfu danh s\xe1ch 'expected_evidence'."
            )

        equivalent_note = str(
            raw_criterion.get("equivalent_answers")
            or raw_criterion.get("equivalent_answers_note")
            or "Ch\u1ea5p nh\u1eadn c\xe1ch di\u1ec5n \u0111\u1ea1t ho\u1eb7c l\u1eddi gi\u1ea3i t\u01b0\u01a1ng \u0111\u01b0\u01a1ng \u0111\xfang b\u1ea3n ch\u1ea5t k\u1ef9 thu\u1eadt."
        ).strip()

        raw_levels = raw_criterion.get("levels")
        level_descriptions: dict[int, str] = {}
        if isinstance(raw_levels, list):
            for lvl in raw_levels:
                if isinstance(lvl, dict) and isinstance(lvl.get("score"), int):
                    level_descriptions[int(lvl["score"])] = str(
                        lvl.get("description") or f"M\u1ee9c \u0111i\u1ec3m {lvl['score']}"
                    ).strip()

        desc_0 = level_descriptions.get(0, "Ch\u01b0a \u0111\xe1p \u1ee9ng y\xeau c\u1ea7u c\u1ee7a ti\xeau ch\xed.")
        desc_1 = level_descriptions.get(1, "\u0110\xe1p \u1ee9ng \u0111\u01b0\u1ee3c m\u1ed9t ph\u1ea7n y\xeau c\u1ea7u c\u1ee7a ti\xeau ch\xed.")
        desc_2 = level_descriptions.get(2, "\u0110\xe1p \u1ee9ng \u0111\u1ea7y \u0111\u1ee7 c\xe1c y\xeau c\u1ea7u c\u1ee7a ti\xeau ch\xed.")

        if len(evidence_points) == 1:
            sub_criterion = ExecutableCriterion(
                id=CriterionId(base_id),
                label=label,
                acceptance_rule=evidence_points[0],
                omission_means_unmet=True,
            )
            score_levels = (
                ExecutableScoreLevel(
                    value=0,
                    description=desc_0,
                    condition="Ch\u01b0a \u0111\u1ea1t ti\xeau ch\xed y\xeau c\u1ea7u.",
                    required_met=(),
                    minimum_met=0,
                ),
                ExecutableScoreLevel(
                    value=2,
                    description=desc_2,
                    condition=f"\u0110\u1ea1t ti\xeau ch\xed '{base_id}'.",
                    required_met=(sub_criterion.id,),
                    minimum_met=1,
                ),
            )
            sub_criteria = (sub_criterion,)
        else:
            sub_criteria_list: list[ExecutableCriterion] = []
            for idx, point in enumerate(evidence_points, start=1):
                sub_id = CriterionId(f"{base_id}.part{idx}")
                sub_criteria_list.append(
                    ExecutableCriterion(
                        id=sub_id,
                        label=f"{label} (\xdd {idx})",
                        acceptance_rule=point,
                        omission_means_unmet=True,
                    )
                )
            sub_criteria = tuple(sub_criteria_list)
            all_sub_ids = tuple(c.id for c in sub_criteria)

            score_levels = (
                ExecutableScoreLevel(
                    value=0,
                    description=desc_0,
                    condition="Kh\xf4ng \u0111\u1ea1t \xfd n\xe0o trong nh\xf3m ti\xeau ch\xed n\xe0y.",
                    required_met=(),
                    minimum_met=0,
                ),
                ExecutableScoreLevel(
                    value=1,
                    description=desc_1,
                    condition=f"\u0110\u1ea1t \xedt nh\u1ea5t 1/{len(sub_criteria)} \xfd c\u1ee7a nh\xf3m ti\xeau ch\xed '{base_id}'.",
                    required_met=(),
                    minimum_met=1,
                ),
                ExecutableScoreLevel(
                    value=2,
                    description=desc_2,
                    condition=f"\u0110\u1ea1t \u0111\u1ea7y \u0111\u1ee7 c\u1ea3 {len(sub_criteria)}/{len(sub_criteria)} \xfd c\u1ee7a nh\xf3m ti\xeau ch\xed '{base_id}'.",
                    required_met=all_sub_ids,
                    minimum_met=len(sub_criteria),
                ),
            )

        return CompetencyRubric(
            id=RubricId(f"rubric.{base_id}"),
            version=rubric_version,
            competency=label,
            review_rule=(
                f"{equivalent_note} N\u1ebfu c\xe2u tr\u1ea3 l\u1eddi d\u1eabn chi\u1ebfu t\xe0i li\u1ec7u/t\u1ec7p \u0111\xednh k\xe8m kh\xf4ng c\xf3 s\u1eb5n "
                "trong phi\xean th\xec g\u1eafn tr\u1ea1ng th\xe1i 'insufficient_evidence'."
            ),
            scoring_rule="Ch\u1ecdn m\u1ee9c \u0111i\u1ec3m cao nh\u1ea5t th\u1ecfa m\xe3n \u0111i\u1ec1u ki\u1ec7n required_met v\xe0 minimum_met.",
            criteria=sub_criteria,
            score_levels=score_levels,
        )