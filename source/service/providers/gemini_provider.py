"""
Live Gemini API adapter implementing EvidenceInterpreter (Tasks E03, E04, E08).
Constructs the structured prompt without score_levels, enforces JSON schema output,
and handles transient rate-limit/timeout retries safely.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Callable
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from source.Model.ids import CriterionId, RubricId
from source.service.evaluationErrors import (
    EvaluationError,
    invalid_ai_output_error,
    provider_rate_limit_error,
    provider_timeout_error,
    provider_unavailable_error,
)
from source.service.providers.interfaces import (
    EvaluationTaskInput,
    EvidenceInterpreter,
    ModelInterpretationOutput,
    ProposedCriterionJudgment,
    ProposedEvidenceItem,
    ProposedRubricJudgment,
)

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "interpret_answer.txt"
DEFAULT_PROMPT_VERSION = "interpret_answer/1"


@dataclass(frozen=True)
class GeminiProviderConfig:
    """Configuration settings for the Gemini API evidence interpreter."""

    api_key: str
    model_name: str = "gemini-2.5-flash"
    api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_backoff_seconds: float = 1.0
    prompt_path: Path = DEFAULT_PROMPT_PATH


HttpTransport = Callable[[str, dict[str, object], float], dict[str, object]]


class GeminiProvider(EvidenceInterpreter):
    """
    Structured-output Gemini adapter for Algorithm 1 (Steps 2 & 3).
    Sends only question, rubric criteria, acceptance/review rules, and untrusted answer data.
    Never sends score_levels or asks the LLM for numeric scores.
    """

    def __init__(
        self,
        config: GeminiProviderConfig,
        transport: HttpTransport | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._transport = transport or self._default_http_transport
        self._sleep_fn = sleep_fn

    def load_prompt_template(self) -> tuple[str, str]:
        """Read the versioned instruction template from source/service/prompts/interpret_answer.txt."""
        try:
            raw_text = self._config.prompt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise provider_unavailable_error(
                f"Kh\xf4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c t\u1ec7p prompt ch\u1ec9 d\u1eabn h\u1ec7 th\u1ed1ng: {exc}",
                retryable=False,
            ) from exc

        first_line = raw_text.splitlines()[0].strip() if raw_text else ""
        if first_line.startswith("PROMPT_VERSION:"):
            version = first_line.split(":", 1)[1].strip() or DEFAULT_PROMPT_VERSION
        else:
            version = DEFAULT_PROMPT_VERSION
        return version, raw_text

    def build_prompt(self, task_input: EvaluationTaskInput) -> str:
        """
        Algorithm 1 (Step 2):
        Build the prompt combining trusted system instructions, question & rubric criteria
        (excluding score_levels), and the delimited candidate answer text.
        """
        _, template_text = self.load_prompt_template()

        rubric_specifications = [
            {
                "rubric_id": str(rubric.id),
                "competency": rubric.competency,
                "review_rule": rubric.review_rule,
                "criteria": [
                    {
                        "criterion_id": str(criterion.id),
                        "label": criterion.label,
                        "acceptance_rule": criterion.acceptance_rule,
                        "omission_means_unmet": criterion.omission_means_unmet,
                    }
                    for criterion in rubric.criteria
                ],
            }
            for rubric in task_input.rubrics
        ]

        evaluation_context_json = json.dumps(
            {
                "question": {
                    "id": str(task_input.question_ref.id),
                    "version": task_input.question_ref.version,
                    "prompt": task_input.question_prompt,
                    "requirements": list(task_input.requirements),
                    "context": task_input.context,
                },
                "rubrics": rubric_specifications,
            },
            ensure_ascii=False,
            indent=2,
        )

        return (
            f"{template_text}\n\n"
            f"=== D\u1eee LI\u1ec6U C\xc2U H\u1eceI V\xc0 TI\xcaU CH\xcd RUBRIC ===\n"
            f"{evaluation_context_json}\n\n"
            f"=== B\xc0I L\xc0M C\u1ee6A \u1ee8NG VI\xcaN (D\u1eee LI\u1ec6U KH\xd4NG TIN C\u1eacY - CH\u1ec8 \u0110\u1ed0I CHI\u1ebeU) ===\n"
            f"<CANDIDATE_ANSWER_DATA>\n"
            f"{task_input.answer_text}\n"
            f"</CANDIDATE_ANSWER_DATA>\n"
        )

    @staticmethod
    def response_json_schema() -> dict[str, object]:
        """Return the strict JSON schema constraining Gemini's structured response."""
        return {
            "type": "OBJECT",
            "required": ["rubric_judgments"],
            "properties": {
                "rubric_judgments": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "required": ["rubric_id", "criterion_checks"],
                        "properties": {
                            "rubric_id": {"type": "STRING"},
                            "criterion_checks": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "required": ["criterion_id", "status", "evidence"],
                                    "properties": {
                                        "criterion_id": {"type": "STRING"},
                                        "status": {
                                            "type": "STRING",
                                            "enum": [
                                                "met",
                                                "unmet",
                                                "insufficient_evidence",
                                            ],
                                        },
                                        "evidence": {
                                            "type": "ARRAY",
                                            "items": {
                                                "type": "OBJECT",
                                                "required": [
                                                    "evidence_type",
                                                    "observation",
                                                    "location",
                                                ],
                                                "properties": {
                                                    "evidence_type": {
                                                        "type": "STRING",
                                                        "enum": [
                                                            "quote",
                                                            "ambiguous",
                                                            "omission",
                                                        ],
                                                    },
                                                    "observation": {"type": "STRING"},
                                                    "location": {"type": "STRING"},
                                                    "quote": {
                                                        "type": "STRING",
                                                        "nullable": True,
                                                    },
                                                    "start_offset": {
                                                        "type": "INTEGER",
                                                        "nullable": True,
                                                    },
                                                    "end_offset": {
                                                        "type": "INTEGER",
                                                        "nullable": True,
                                                    },
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            },
        }

    def interpret(self, task_input: EvaluationTaskInput) -> ModelInterpretationOutput:
        """
        Execute the structured interpretation call with bounded transient retry (Task E08)
        and parse the response into ModelInterpretationOutput.
        """
        api_key = self._config.api_key.strip() if self._config.api_key else ""
        if not api_key:
            raise provider_unavailable_error(
                "Ch\u01b0a c\u1ea5u h\xecnh kh\xf3a GEMINI_API_KEY tr\xean m\xe1y ch\u1ee7. "
                "B\xe0i tr\u1ea3 l\u1eddi c\u1ee7a b\u1ea1n v\u1eabn \u0111\u01b0\u1ee3c gi\u1eef nguy\xean; vui l\xf2ng c\u1ea5u h\xecnh kh\xf3a ho\u1eb7c d\xf9ng ch\u1ebf \u0111\u1ed9 m\u1eabu.",
                retryable=False,
            )

        prompt_version, _ = self.load_prompt_template()
        prompt_text = self.build_prompt(task_input)

        encoded_model = urllib_parse.quote(self._config.model_name, safe="")
        encoded_key = urllib_parse.quote(api_key, safe="")
        endpoint = (
            f"{self._config.api_base_url.rstrip('/')}/models/"
            f"{encoded_model}:generateContent?key={encoded_key}"
        )

        request_body: dict[str, object] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                "responseSchema": self.response_json_schema(),
            },
        }

        max_attempts = max(1, 1 + self._config.max_retries)
        last_error: EvaluationError | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                raw_response = self._transport(
                    endpoint,
                    request_body,
                    self._config.timeout_seconds,
                )
                return self._parse_api_response(raw_response, prompt_version)
            except EvaluationError as exc:
                last_error = exc
                is_transient = exc.code in {
                    "PROVIDER_RATE_LIMIT",
                    "PROVIDER_TIMEOUT",
                    "PROVIDER_UNAVAILABLE",
                }
                if is_transient and exc.retryable and attempt < max_attempts:
                    self._sleep_fn(self._config.retry_backoff_seconds * attempt)
                    continue
                raise

        assert last_error is not None
        raise last_error

    def _default_http_transport(
        self,
        url: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        """Execute HTTPS POST request to Gemini REST API without leaking API keys in errors."""
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib_request.Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
                body_text = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            if exc.code == 429:
                raise provider_rate_limit_error(
                    "H\u1ec7 th\u1ed1ng AI \u0111ang v\u01b0\u1ee3t gi\u1edbi h\u1ea1n t\u1ea7n su\u1ea5t g\u1ecdi (Rate Limit 429). "
                    "C\xe2u tr\u1ea3 l\u1eddi \u0111\xe3 \u0111\u01b0\u1ee3c l\u01b0u, vui l\xf2ng th\u1eed l\u1ea1i sau \xedt gi\xe2y."
                ) from exc
            if exc.code in {502, 503, 504}:
                raise provider_timeout_error(
                    f"D\u1ecbch v\u1ee5 AI t\u1ea1m th\u1eddi qu\xe1 t\u1ea3i (HTTP {exc.code}). Vui l\xf2ng th\u1eed l\u1ea1i."
                ) from exc
            if exc.code in {401, 403}:
                raise provider_unavailable_error(
                    "Kh\xf3a k\u1ebft n\u1ed1i AI kh\xf4ng h\u1ee3p l\u1ec7 ho\u1eb7c kh\xf4ng c\xf3 quy\u1ec1n truy c\u1eadp model \u0111\xe3 ch\u1ecdn.",
                    retryable=False,
                ) from exc
            raise provider_unavailable_error(
                f"Y\xeau c\u1ea7u \u0111\xe1nh gi\xe1 AI th\u1ea5t b\u1ea1i v\u1edbi m\xe3 HTTP {exc.code}.",
                retryable=False,
            ) from exc
        except TimeoutError as exc:
            raise provider_timeout_error(
                "Y\xeau c\u1ea7u \u0111\xe1nh gi\xe1 AI b\u1ecb qu\xe1 th\u1eddi gian ch\u1edd (timeout). "
                "B\xe0i l\xe0m c\u1ee7a b\u1ea1n v\u1eabn \u0111\u01b0\u1ee3c gi\u1eef nguy\xean \u0111\u1ec3 th\u1eed l\u1ea1i."
            ) from exc
        except urllib_error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise provider_timeout_error(
                    "Y\xeau c\u1ea7u \u0111\xe1nh gi\xe1 AI b\u1ecb qu\xe1 th\u1eddi gian ch\u1edd (timeout). "
                    "B\xe0i l\xe0m c\u1ee7a b\u1ea1n v\u1eabn \u0111\u01b0\u1ee3c gi\u1eef nguy\xean \u0111\u1ec3 th\u1eed l\u1ea1i."
                ) from exc
            raise provider_unavailable_error(
                "Kh\xf4ng th\u1ec3 k\u1ebft n\u1ed1i t\u1edbi d\u1ecbch v\u1ee5 AI. Vui l\xf2ng ki\u1ec3m tra k\u1ebft n\u1ed1i m\u1ea1ng v\xe0 th\u1eed l\u1ea1i.",
                retryable=True,
            ) from exc

        try:
            parsed = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise invalid_ai_output_error(
                "Ph\u1ea3n h\u1ed3i t\u1eeb d\u1ecbch v\u1ee5 AI kh\xf4ng ph\u1ea3i JSON h\u1ee3p l\u1ec7."
            ) from exc

        if not isinstance(parsed, dict):
            raise invalid_ai_output_error("Ph\u1ea3n h\u1ed3i g\u1ed1c t\u1eeb d\u1ecbch v\u1ee5 AI kh\xf4ng ph\u1ea3i \u0111\u1ed1i t\u01b0\u1ee3ng JSON.")
        return parsed

    def _parse_api_response(
        self,
        raw_response: dict[str, object],
        prompt_version: str,
    ) -> ModelInterpretationOutput:
        """Extract candidate JSON text from Gemini response and convert to ModelInterpretationOutput."""
        candidates = raw_response.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise invalid_ai_output_error(
                "D\u1ecbch v\u1ee5 AI kh\xf4ng tr\u1ea3 v\u1ec1 ph\u01b0\u01a1ng \xe1n ph\xe2n t\xedch n\xe0o (candidates r\u1ed7ng ho\u1eb7c b\u1ecb ch\u1eb7n)."
            )

        first_candidate = candidates[0]
        if not isinstance(first_candidate, dict):
            raise invalid_ai_output_error("C\u1ea5u tr\xfac candidate t\u1eeb AI kh\xf4ng h\u1ee3p l\u1ec7.")

        finish_reason = first_candidate.get("finishReason")
        if finish_reason in {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "RECITATION"}:
            raise invalid_ai_output_error(
                f"Ph\u1ea3n h\u1ed3i c\u1ee7a AI b\u1ecb d\u1eebng s\u1edbm do b\u1ed9 l\u1ecdc ({finish_reason})."
            )

        content = first_candidate.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list) or not parts:
            raise invalid_ai_output_error("Ph\u1ea3n h\u1ed3i c\u1ee7a AI kh\xf4ng ch\u1ee9a n\u1ed9i dung v\u0103n b\u1ea3n (parts r\u1ed7ng).")

        first_part = parts[0]
        raw_json_text = first_part.get("text") if isinstance(first_part, dict) else None
        if not isinstance(raw_json_text, str) or not raw_json_text.strip():
            raise invalid_ai_output_error("N\u1ed9i dung JSON trong ph\u1ea3n h\u1ed3i c\u1ee7a AI b\u1ecb tr\u1ed1ng.")

        return self.parse_structured_json(raw_json_text, prompt_version=prompt_version)

    def parse_structured_json(
        self,
        raw_json_text: str,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ) -> ModelInterpretationOutput:
        """Parse the structured JSON string returned by Gemini into ModelInterpretationOutput."""
        try:
            payload = json.loads(raw_json_text)
        except json.JSONDecodeError as exc:
            raise invalid_ai_output_error(
                f"AI tr\u1ea3 v\u1ec1 chu\u1ed7i JSON sai c\xfa ph\xe1p: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise invalid_ai_output_error("\u0110\u1ea7u ra c\u1ee7a AI ph\u1ea3i l\xe0 m\u1ed9t \u0111\u1ed1i t\u01b0\u1ee3ng JSON.")

        raw_rubrics = payload.get("rubric_judgments")
        if raw_rubrics is None:
            raw_rubrics = payload.get("rubricJudgments")
        if not isinstance(raw_rubrics, list):
            raise invalid_ai_output_error(
                "\u0110\u1ea7u ra c\u1ee7a AI thi\u1ebfu danh s\xe1ch 'rubric_judgments'."
            )

        rubric_judgments: list[ProposedRubricJudgment] = []
        for r_item in raw_rubrics:
            if not isinstance(r_item, dict):
                raise invalid_ai_output_error("Ph\u1ea7n t\u1eed trong 'rubric_judgments' ph\u1ea3i l\xe0 object.")

            rubric_id = r_item.get("rubric_id") or r_item.get("rubricId")
            if not isinstance(rubric_id, str) or not rubric_id.strip():
                raise invalid_ai_output_error("M\u1ed7i rubric judgment ph\u1ea3i c\xf3 'rubric_id' h\u1ee3p l\u1ec7.")

            raw_checks = r_item.get("criterion_checks")
            if raw_checks is None:
                raw_checks = r_item.get("criterionChecks")
            if not isinstance(raw_checks, list):
                raise invalid_ai_output_error(
                    f"Rubric '{rubric_id}' thi\u1ebfu danh s\xe1ch 'criterion_checks'."
                )

            criterion_checks: list[ProposedCriterionJudgment] = []
            for c_item in raw_checks:
                if not isinstance(c_item, dict):
                    raise invalid_ai_output_error(
                        f"Ph\u1ea7n t\u1eed criterion check trong rubric '{rubric_id}' ph\u1ea3i l\xe0 object."
                    )
                criterion_id = c_item.get("criterion_id") or c_item.get("criterionId")
                status = c_item.get("status")
                raw_evidence = c_item.get("evidence")

                if not isinstance(criterion_id, str) or not criterion_id.strip():
                    raise invalid_ai_output_error(
                        f"Rubric '{rubric_id}' c\xf3 criterion check thi\u1ebfu 'criterion_id'."
                    )
                if not isinstance(status, str) or not status.strip():
                    raise invalid_ai_output_error(
                        f"Ti\xeau ch\xed '{criterion_id}' thi\u1ebfu tr\u01b0\u1eddng 'status'."
                    )
                if not isinstance(raw_evidence, list):
                    raise invalid_ai_output_error(
                        f"Ti\xeau ch\xed '{criterion_id}' thi\u1ebfu danh s\xe1ch 'evidence'."
                    )

                evidence_items: list[ProposedEvidenceItem] = []
                for e_item in raw_evidence:
                    if not isinstance(e_item, dict):
                        raise invalid_ai_output_error(
                            f"B\u1eb1ng ch\u1ee9ng c\u1ee7a ti\xeau ch\xed '{criterion_id}' ph\u1ea3i l\xe0 object."
                        )
                    ev_type = e_item.get("evidence_type") or e_item.get("type")
                    observation = e_item.get("observation")
                    location = e_item.get("location")
                    quote = e_item.get("quote")
                    start_offset = (
                        e_item.get("start_offset")
                        if "start_offset" in e_item
                        else e_item.get("startOffset")
                    )
                    end_offset = (
                        e_item.get("end_offset")
                        if "end_offset" in e_item
                        else e_item.get("endOffset")
                    )

                    if not isinstance(ev_type, str) or not isinstance(observation, str) or not isinstance(location, str):
                        raise invalid_ai_output_error(
                            f"B\u1eb1ng ch\u1ee9ng c\u1ee7a ti\xeau ch\xed '{criterion_id}' thi\u1ebfu tr\u01b0\u1eddng b\u1eaft bu\u1ed9c "
                            "('evidence_type', 'observation', 'location')."
                        )

                    evidence_items.append(
                        ProposedEvidenceItem(
                            evidence_type=ev_type,
                            observation=observation,
                            location=location,
                            quote=quote if isinstance(quote, str) else None,
                            start_offset=start_offset if isinstance(start_offset, int) and not isinstance(start_offset, bool) else None,
                            end_offset=end_offset if isinstance(end_offset, int) and not isinstance(end_offset, bool) else None,
                        )
                    )

                criterion_checks.append(
                    ProposedCriterionJudgment(
                        criterion_id=CriterionId(criterion_id.strip()),
                        status=status.strip(),
                        evidence=tuple(evidence_items),
                    )
                )

            rubric_judgments.append(
                ProposedRubricJudgment(
                    rubric_id=RubricId(rubric_id.strip()),
                    criterion_checks=tuple(criterion_checks),
                )
            )

        return ModelInterpretationOutput(
            provider_name="gemini",
            model_name=self._config.model_name,
            prompt_version=prompt_version,
            rubric_judgments=tuple(rubric_judgments),
        )