"""P07/E04 Gemini structured-output adapter conforming to E01 `EvidenceInterpreter`."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from source.Model.repositories.request_budget import RequestBudget
from source.Model.repositories.interfaces import RepositoryError, RequestBudgetRepository
from uuid import uuid4
import re
import socket
import time
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from source.config import GeminiLimits
from source.Model.evaluation import CriterionStatus
from source.Model.ids import CriterionId
from source.Model.question import Question, Rubric
from source.service.prompts import PROMPT_VERSION, InterpretationPromptBuilder
from source.service.providers.interfaces import (
    CriterionObservation,
    InterpretationBatch,
    ProviderErrorKind,
    ProviderFailureError,
)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
logger = logging.getLogger(__name__)
_MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


class _SecretValueLike(Protocol):
    def get_secret_value(self) -> str: ...


class _GeminiSettingsLike(Protocol):
    database_path: Path
    gemini_limits: GeminiLimits
    provider: str
    gemini_timeout_seconds: float
    gemini_model: str | None
    gemini_api_key: _SecretValueLike | None


class GeminiProviderError(ProviderFailureError):
    """Raised when the Gemini provider cannot produce a valid structured interpretation."""


class CriterionInterpretationDTO(BaseModel):
    """Structured observation for one rubric criterion without a numeric score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str = Field(min_length=1)
    status: CriterionStatus
    quote: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    observation: str | None = None
    explanation: str = Field(min_length=1)
    unresolved_reason: str | None = None
    satisfied_expected_indexes: tuple[int, ...] | None = None

    @model_validator(mode="after")
    def _validate_evidence_and_reason(self) -> CriterionInterpretationDTO:
        has_quote = (
            self.quote is not None
            and self.start_offset is not None
            and self.end_offset is not None
        )
        has_partial_quote = any(
            value is not None for value in (self.quote, self.start_offset, self.end_offset)
        )
        has_observation = self.observation is not None and bool(self.observation.strip())
        if has_quote and has_observation:
            raise ValueError("Provide either a literal quote with offsets or an observation, not both.")
        if has_partial_quote and not has_quote:
            raise ValueError("A quote requires quote, start_offset, and end_offset.")
        if not has_quote and not has_observation:
            raise ValueError("Each criterion check requires either a quote with offsets or an observation.")
        if has_quote and self.start_offset is not None and self.end_offset is not None:
            if self.end_offset <= self.start_offset:
                raise ValueError("end_offset must be greater than start_offset for a non-empty quote.")
            if self.quote is not None and len(self.quote) != (self.end_offset - self.start_offset):
                raise ValueError("Quote length must match end_offset - start_offset.")
        if self.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            if not self.unresolved_reason or not self.unresolved_reason.strip():
                raise ValueError("insufficient_evidence requires a non-empty unresolved_reason.")
        return self


class AnswerInterpretationResponse(BaseModel):
    """Top-level structured output schema requested from Gemini."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_checks: tuple[CriterionInterpretationDTO, ...] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class GeminiCallResult:
    """Validated provider output paired with redacted telemetry."""

    interpretation: AnswerInterpretationResponse
    model_id: str
    prompt_version: str
    elapsed_ms: int


SYSTEM_INSTRUCTION = InterpretationPromptBuilder().system_instruction()


class GeminiProvider:
    """Structured-output client for Gemini `generateContent` implementing `EvidenceInterpreter`."""

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str = DEFAULT_GEMINI_MODEL,
        timeout_seconds: float = 30.0,
        limits: GeminiLimits = GeminiLimits(),
        budget_path: Path | None = None,
        budget: RequestBudgetRepository | None = None,
        prompt_version: str = PROMPT_VERSION,
        prompt_builder: InterpretationPromptBuilder | None = None,
        transport: Callable[[Request, float], bytes] | None = None,
    ) -> None:
        cleaned_key = api_key.strip()
        cleaned_model = model_id.strip()
        if not cleaned_key:
            raise GeminiProviderError(
                ProviderErrorKind.CONFIG,
                "Missing GEMINI_API_KEY for live Gemini evaluation.",
                retryable=False,
            )
        if not _MODEL_NAME_PATTERN.fullmatch(cleaned_model):
            raise GeminiProviderError(
                ProviderErrorKind.CONFIG,
                "GEMINI_MODEL must be a valid model identifier without the 'models/' prefix.",
                retryable=False,
            )
        if isinstance(timeout_seconds, bool) or not (1.0 <= float(timeout_seconds) <= 120.0):
            raise GeminiProviderError(
                ProviderErrorKind.CONFIG,
                "GEMINI_TIMEOUT_SECONDS must be between 1 and 120 seconds.",
                retryable=False,
            )
        self.limits = limits
        self._budget: RequestBudgetRepository = budget if budget is not None else RequestBudget(limits.request_budget, budget_path)
        self._api_key = cleaned_key
        self.model_id = cleaned_model
        self.timeout_seconds = float(timeout_seconds)
        self._prompt_builder = prompt_builder or InterpretationPromptBuilder(version=prompt_version)
        self.prompt_version = self._prompt_builder.version
        self._transport = transport or self._default_transport

    def __repr__(self) -> str:
        return (
            f"GeminiProvider(model_id={self.model_id!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"prompt_version={self.prompt_version!r}, api_key='***')"
        )

    @classmethod
    def from_settings(
        cls,
        settings: _GeminiSettingsLike,
        *,
        transport: Callable[[Request, float], bytes] | None = None,
    ) -> GeminiProvider:
        if str(settings.provider) != "gemini":
            raise GeminiProviderError(
                ProviderErrorKind.CONFIG,
                "GeminiProvider requires EVALUATION_PROVIDER=gemini in Settings.",
                retryable=False,
            )
        api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        model_id = settings.gemini_model or ""
        return cls(
            api_key=api_key,
            model_id=model_id,
            limits=settings.gemini_limits,
            budget_path=settings.database_path,
            timeout_seconds=settings.gemini_timeout_seconds,
            transport=transport,
        )

    def build_request(
        self,
        *,
        question: Question,
        rubric: Rubric,
        answer_text: str,
    ) -> Request:
        user_json = self._prompt_builder.build_user_data_json(
            question=question,
            rubric=rubric,
            answer_text=answer_text,
        )
        body_dict = {
            "systemInstruction": {
                "parts": [{"text": self._prompt_builder.system_instruction()}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_json}],
                }
            ],
            "generationConfig": {
                "candidateCount": 1,
                "temperature": 0.0,
                "maxOutputTokens": self.limits.output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": AnswerInterpretationResponse.model_json_schema(),
            },
        }
        encoded = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
        if len(encoded) > self.limits.input_bytes:
            raise GeminiProviderError(
                ProviderErrorKind.INPUT_LIMIT,
                "Request payload exceeds the configured byte limit.",
                retryable=False,
            )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_id}:generateContent"
        )
        return Request(
            url,
            data=encoded,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )

    def interpret_answer(
        self,
        *,
        question: Question,
        rubric: Rubric,
        answer_text: str,
    ) -> GeminiCallResult:
        started = time.perf_counter()
        request_id = uuid4().hex
        for attempt in range(1, self.limits.max_retries + 2):
            tick = time.perf_counter()
            outcome = "OK"
            tokens = None
            try:
                request = self.build_request(question=question, rubric=rubric, answer_text=answer_text)
                try:
                    if not self._budget.reserve():
                        raise GeminiProviderError(ProviderErrorKind.QUOTA, "Configured request budget exhausted.")
                except RepositoryError:
                    raise GeminiProviderError(ProviderErrorKind.CONFIG,
                                              "Cannot reserve Gemini request budget.") from None
                raw_body = self._transport(request, self.timeout_seconds)
                if len(raw_body) > self.limits.response_bytes:
                    raise GeminiProviderError(ProviderErrorKind.INVALID_OUTPUT, "Response exceeds byte limit.")
                interpretation = self.parse_response(raw_body)
                usage = json.loads(raw_body).get("usageMetadata")
                if isinstance(usage, dict) and type(usage.get("totalTokenCount")) is int:
                    tokens = usage["totalTokenCount"]
                break
            except GeminiProviderError as error:
                outcome = error.code
                transient = error.code in {
                    ProviderErrorKind.TIMEOUT, ProviderErrorKind.NETWORK,
                    ProviderErrorKind.HTTP, ProviderErrorKind.QUOTA,
                }
                if not transient or not error.retryable or attempt > self.limits.max_retries:
                    raise
            finally:
                logger.info("gemini request_id=%s attempt=%d elapsed_ms=%d outcome=%s tokens=%s",
                            request_id, attempt, (time.perf_counter() - tick) * 1000, outcome, tokens)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return GeminiCallResult(
            interpretation=interpretation,
            model_id=self.model_id,
            prompt_version=self.prompt_version,
            elapsed_ms=elapsed_ms,
        )

    def interpret(
        self,
        *,
        question: Question,
        rubric: Rubric,
        answer_text: str,
    ) -> InterpretationBatch:
        call_result = self.interpret_answer(
            question=question,
            rubric=rubric,
            answer_text=answer_text,
        )
        observations = tuple(
            CriterionObservation(
                criterion_id=CriterionId(item.criterion_id),
                status=item.status,
                explanation=item.explanation,
                quote=item.quote,
                start_offset=item.start_offset,
                end_offset=item.end_offset,
                observation=item.observation,
                unresolved_reason=item.unresolved_reason,
                satisfied_expected_indexes=item.satisfied_expected_indexes,
            )
            for item in call_result.interpretation.criterion_checks
        )
        return InterpretationBatch(
            observations=observations,
            model_id=call_result.model_id,
            prompt_version=call_result.prompt_version,
            demo_mode_label=None,
            elapsed_ms=call_result.elapsed_ms,
        )

    def _default_transport(self, request: Request, timeout_seconds: float) -> bytes:
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw_body = response.read(self.limits.response_bytes + 1)
            if len(raw_body) > self.limits.response_bytes:
                raise GeminiProviderError(
                    ProviderErrorKind.INVALID_OUTPUT,
                    "Gemini response exceeded the configured byte limit.",
                    retryable=False,
                )
            return raw_body
        except HTTPError as error:
            error.close()
            if error.code == 408:
                raise GeminiProviderError(ProviderErrorKind.TIMEOUT, "Gemini HTTP timeout.", retryable=True) from None
            if error.code == 402:
                raise GeminiProviderError(
                    ProviderErrorKind.BILLING,
                    "Gemini project has no available quota/credits (HTTP 402).",
                    retryable=False,
                ) from None
            if error.code == 429:
                raise GeminiProviderError(
                    ProviderErrorKind.QUOTA,
                    "Gemini rate limit or quota reached (HTTP 429); saved answer is unchanged.",
                    retryable=True,
                ) from None
            retryable = error.code in {500, 502, 503, 504}
            raise GeminiProviderError(
                ProviderErrorKind.HTTP,
                f"Gemini returned HTTP {error.code}; saved answer is unchanged.",
                retryable=retryable,
            ) from None
        except (TimeoutError, socket.timeout):
            raise GeminiProviderError(
                ProviderErrorKind.TIMEOUT,
                "Gemini request timed out; saved answer is unchanged.",
                retryable=True,
            ) from None
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise GeminiProviderError(ProviderErrorKind.TIMEOUT, "Gemini request timed out.",
                                          retryable=True) from None
            raise GeminiProviderError(ProviderErrorKind.NETWORK, "Gemini connection failed.",
                                      retryable=True) from None
        except OSError:
            raise GeminiProviderError(
                ProviderErrorKind.NETWORK,
                "Network error while contacting Gemini; saved answer is unchanged.",
                retryable=True,
            ) from None

    @staticmethod
    def parse_response(raw_body: bytes) -> AnswerInterpretationResponse:
        try:
            payload = json.loads(raw_body)
            if payload.get("promptFeedback", {}).get("blockReason"):
                raise GeminiProviderError(
                    ProviderErrorKind.REFUSAL,
                    "Gemini declined the request via promptFeedback.blockReason.",
                    retryable=False,
                )
            candidates = payload.get("candidates", [])
            if len(candidates) == 1 and candidates[0].get("finishReason") in {
                "SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "RECITATION"
            }:
                raise GeminiProviderError(ProviderErrorKind.REFUSAL, "Gemini blocked the candidate.")
            if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
                raise GeminiProviderError(
                    ProviderErrorKind.INCOMPLETE,
                    "Gemini did not return a single completed candidate (finishReason=STOP).",
                    retryable=True,
                )
            parts = candidates[0]["content"]["parts"]
            text_content = "".join(
                part["text"]
                for part in parts
                if "text" in part and not part.get("thought", False)
            )
            return AnswerInterpretationResponse.model_validate_json(text_content)
        except GeminiProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError, ValidationError):
            raise GeminiProviderError(
                ProviderErrorKind.INVALID_OUTPUT,
                "Gemini returned malformed JSON that did not match AnswerInterpretationResponse.",
                retryable=True,
            ) from None


__all__ = [
    "AnswerInterpretationResponse",
    "CriterionInterpretationDTO",
    "DEFAULT_GEMINI_MODEL",
    "GeminiCallResult",
    "GeminiProvider",
    "GeminiProviderError",
    "PROMPT_VERSION",
    "ProviderErrorKind",
    "SYSTEM_INSTRUCTION",
]
