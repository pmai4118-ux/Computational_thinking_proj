"""P07/E04 Antigravity CLI structured-output adapter conforming to E01 `EvidenceInterpreter`.

Runs the signed-in local Antigravity CLI (`agy`, defaulting to `gemini-3.8-flash-medium`)
inside an isolated empty directory with all agent tools disabled and API-key variables
cleared so evaluation strictly uses the member's Antigravity subscription session.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import logging
from pathlib import Path
from uuid import uuid4
import shutil
import subprocess
import tempfile
import time
from typing import Any, Callable, NoReturn, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model, model_validator

from source.Model.repositories.request_budget import RequestBudget
from source.Model.repositories.interfaces import RepositoryError, RequestBudgetRepository
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

DEFAULT_ANTIGRAVITY_MODEL = "gemini-3.8-flash-medium"
DEFAULT_ANTIGRAVITY_EXECUTABLE = "agy"
DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS = 120.0
MAX_REQUEST_BYTES = 250_000
MAX_RESPONSE_BYTES = 2_000_000
_MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


class _AntigravitySettingsLike(Protocol):
    database_path: Path
    gemini_limits: GeminiLimits
    provider: str
    antigravity_model: str | None
    antigravity_timeout_seconds: float
    antigravity_executable: str


class AntigravityProviderError(ProviderFailureError):
    """Raised when the Antigravity CLI cannot produce a valid structured interpretation."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AntigravityCriterionDTO(_StrictModel):
    """Structured observation emitted by Antigravity for one criterion (no numeric score)."""

    status: CriterionStatus
    quote: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    observation: str | None = None
    explanation: str = Field(min_length=1)
    unresolved_reason: str | None = None
    satisfied_expected_indexes: list[int] | None = None

    @model_validator(mode="after")
    def _validate_evidence_and_reason(self) -> AntigravityCriterionDTO:
        has_quote = self.quote is not None and bool(self.quote)
        has_offsets = self.start_offset is not None and self.end_offset is not None
        has_partial_offset = (self.start_offset is not None) != (self.end_offset is not None)
        has_observation = self.observation is not None and bool(self.observation.strip())

        if has_partial_offset:
            raise ValueError("Provide both start_offset and end_offset, or leave both null.")
        if has_offsets and not has_quote:
            raise ValueError("Offsets require a non-empty quote.")
        if has_quote and has_observation:
            raise ValueError("Provide either a literal quote or an observation, not both.")
        if not has_quote and not has_observation:
            raise ValueError("Each criterion check requires either a quote or an observation.")
        if has_quote and has_offsets:
            assert self.quote is not None
            assert self.start_offset is not None
            assert self.end_offset is not None
            if self.end_offset <= self.start_offset:
                raise ValueError("end_offset must be greater than start_offset.")
            if len(self.quote) != (self.end_offset - self.start_offset):
                raise ValueError("Quote length must match end_offset - start_offset.")
        if self.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            if not self.unresolved_reason or not self.unresolved_reason.strip():
                raise ValueError("insufficient_evidence requires a non-empty unresolved_reason.")
        return self


@dataclass(frozen=True, slots=True)
class AntigravityCallResult:
    """Validated Antigravity structured observations paired with telemetry."""

    observations: tuple[CriterionObservation, ...]
    model_id: str
    prompt_version: str
    elapsed_ms: int


def _resolve_quote_offsets(
    criterion_id: str,
    dto: AntigravityCriterionDTO,
    answer_text: str,
) -> AntigravityCriterionDTO:
    """Populate exact offsets when Antigravity returns a unique exact quote with null offsets."""
    if dto.quote is None or (dto.start_offset is not None and dto.end_offset is not None):
        return dto
    first = answer_text.find(dto.quote)
    if first == -1:
        raise AntigravityProviderError(
            ProviderErrorKind.INVALID_OUTPUT,
            f"Antigravity returned a quote for '{criterion_id}' that is not present in the answer.",
            retryable=True,
        )
    if answer_text.find(dto.quote, first + 1) != -1:
        raise AntigravityProviderError(
            ProviderErrorKind.INVALID_OUTPUT,
            f"Quote for '{criterion_id}' appears multiple times without explicit offsets.",
            retryable=True,
        )
    return dto.model_copy(
        update={
            "start_offset": first,
            "end_offset": first + len(dto.quote),
        }
    )


class AntigravityProvider:
    """Adapter calling local signed-in `agy` CLI with `--model gemini-3.8-flash-medium`."""

    provider_name = "antigravity"

    def __init__(
        self,
        *,
        limits: GeminiLimits = GeminiLimits(response_bytes=MAX_RESPONSE_BYTES),
        budget_path: Path | None = None,
        budget: RequestBudgetRepository | None = None,
        model_id: str = DEFAULT_ANTIGRAVITY_MODEL,
        timeout_seconds: float = DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS,
        executable: str = DEFAULT_ANTIGRAVITY_EXECUTABLE,
        prompt_builder: InterpretationPromptBuilder | None = None,
        prompt_version: str = PROMPT_VERSION,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        cleaned_model = model_id.strip()
        cleaned_exec = executable.strip()
        if not _MODEL_NAME_PATTERN.fullmatch(cleaned_model):
            raise AntigravityProviderError(
                ProviderErrorKind.CONFIG,
                "ANTIGRAVITY_MODEL must be a valid model slug from 'agy models' without 'models/' prefix.",
                retryable=False,
            )
        if isinstance(timeout_seconds, bool) or not (1.0 <= float(timeout_seconds) <= 300.0):
            raise AntigravityProviderError(
                ProviderErrorKind.CONFIG,
                "ANTIGRAVITY_TIMEOUT_SECONDS must be between 1 and 300 seconds.",
                retryable=False,
            )
        if not cleaned_exec or "\0" in cleaned_exec:
            raise AntigravityProviderError(
                ProviderErrorKind.CONFIG,
                "ANTIGRAVITY_EXECUTABLE must be a valid executable name or path.",
                retryable=False,
            )
        self.limits = limits
        self._budget: RequestBudgetRepository = budget if budget is not None else RequestBudget(limits.request_budget, budget_path)
        self.model_id = cleaned_model
        self.timeout_seconds = float(timeout_seconds)
        self.executable = cleaned_exec
        self._prompt_builder = prompt_builder or InterpretationPromptBuilder(version=prompt_version)
        self.prompt_version = f"{self._prompt_builder.version}+antigravity/1"
        self._runner = runner or self._bounded_runner

    def __repr__(self) -> str:
        return (
            f"AntigravityProvider(model_id={self.model_id!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"prompt_version={self.prompt_version!r}, executable={self.executable!r})"
        )

    @classmethod
    def from_settings(
        cls,
        settings: _AntigravitySettingsLike,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> AntigravityProvider:
        if str(settings.provider) != "antigravity":
            raise AntigravityProviderError(
                ProviderErrorKind.CONFIG,
                "AntigravityProvider requires EVALUATION_PROVIDER=antigravity in Settings.",
                retryable=False,
            )
        return cls(
            limits=settings.gemini_limits,
            budget_path=settings.database_path,
            model_id=settings.antigravity_model or DEFAULT_ANTIGRAVITY_MODEL,
            timeout_seconds=settings.antigravity_timeout_seconds,
            executable=settings.antigravity_executable or DEFAULT_ANTIGRAVITY_EXECUTABLE,
            runner=runner,
        )

    @staticmethod
    def session_settings() -> dict[str, Any]:
        """Isolated CLI settings blocking all filesystem, shell, web, and MCP tools."""
        return {
            "modelProvider": "",
            "useG1Credits": False,
            "toolPermission": "request-review",
            "permissions": {
                "allow": [],
                "deny": [
                    "command(*)",
                    "read_file(*)",
                    "write_file(*)",
                    "read_url(*)",
                    "execute_url(*)",
                    "mcp(*)",
                ],
            },
        }

    @staticmethod
    def subscription_environment() -> dict[str, str]:
        """Strip API-key env vars so Antigravity CLI uses the signed-in account only."""
        env = dict(os.environ)
        for name in (
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GEMINI_BASE_URL",
            "GOOGLE_GENAI_USE_VERTEXAI",
            "AGY_ADC_AUTH",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ):
            env.pop(name, None)
        return env

    def executable_path(self) -> str | None:
        resolved = shutil.which(self.executable)
        if resolved is not None and os.name == "nt" and not resolved.lower().endswith(".exe"):
            return None
        return resolved

    @staticmethod
    def response_model(rubric: Rubric) -> type[BaseModel]:
        """Build a keyed-object Pydantic schema without prefixItems/allOf/const for `agy`."""
        criterion_fields: dict[str, Any] = {
            f"c{index}": (AntigravityCriterionDTO, Field(alias=criterion.id))
            for index, criterion in enumerate(rubric.criteria)
        }
        checks_model = create_model(
            "AntigravityCriterionChecks",
            __base__=_StrictModel,
            **criterion_fields,
        )
        return create_model(
            "AntigravityAssessmentResponse",
            __base__=_StrictModel,
            criterion_checks=(checks_model, ...),
        )

    @classmethod
    def response_schema(cls, rubric: Rubric) -> dict[str, Any]:
        return cls.response_model(rubric).model_json_schema()

    def build_prompt(
        self,
        *,
        question: Question,
        rubric: Rubric,
        answer_text: str,
    ) -> str:
        user_json = self._prompt_builder.build_user_data_json(
            question=question,
            rubric=rubric,
            answer_text=answer_text,
        )
        prompt = (
            f"{self._prompt_builder.system_instruction()}\n"
            "Submit the assessment using the finish structured-output tool only. "
            "Do not use command, file, workspace, web, or MCP tools. "
            "Return a `criterion_checks` OBJECT keyed by the exact rubric criterion IDs, "
            "including every criterion exactly once and never adding scores. "
            "For a unique exact quote you may leave start_offset/end_offset null or give exact "
            "Python 0-based indices; for omissions/ambiguities set observation with quote=null.\n"
            f"{user_json}"
        )
        if len(prompt.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise AntigravityProviderError(
                ProviderErrorKind.INPUT_LIMIT,
                "Antigravity request payload exceeds the 250 KB safety limit.",
                retryable=False,
            )
        return prompt

    def build_command(self, executable: str, rubric: Rubric) -> list[str]:
        timeout_arg = int(self.timeout_seconds) if self.timeout_seconds.is_integer() else self.timeout_seconds
        return [
            executable,
            "--settings",
            json.dumps(self.session_settings()),
            "--model",
            self.model_id,
            "--disable-slash-commands",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--json-schema",
            json.dumps(self.response_schema(rubric), ensure_ascii=False),
            "--print-timeout",
            f"{timeout_arg}s",
        ]

    @staticmethod
    def _raise_provider_failure(stderr: str, results: list[dict[str, Any]]) -> NoReturn:
        parts = [stderr]
        for res in results:
            parts.extend(str(res.get(key, "")) for key in ("status", "error"))
        diagnostics = " ".join(parts).lower()
        if re.search(r"\b(?:timeout|timed out|deadline[ _]exceeded)\b", diagnostics):
            raise AntigravityProviderError(
                ProviderErrorKind.TIMEOUT,
                "Antigravity CLI timed out; saved answer is unchanged.",
                retryable=True,
            )
        if re.search(r"\b(?:quota|rate[ -]limit(?:ed)?|resource_exhausted)\b", diagnostics):
            raise AntigravityProviderError(
                ProviderErrorKind.QUOTA,
                "Antigravity subscription quota reached; saved answer is unchanged.",
                retryable=True,
            )
        if re.search(
            r"\b(?:unauthenticated|unauthorized|authentication|credentials?|sign[ -]in|log[ -]?in)\b",
            diagnostics,
        ):
            raise AntigravityProviderError(
                ProviderErrorKind.CONFIG,
                "Sign in to Antigravity CLI (`agy`) before running live evaluation.",
                retryable=False,
            )
        if re.search(r"\b(?:refusal|safety_block|prohibited_content|blocked_by_safety)\b", diagnostics):
            raise AntigravityProviderError(ProviderErrorKind.REFUSAL, "Assessment blocked by the provider.")
        if "invalid_argument" in diagnostics:
            raise AntigravityProviderError(
                ProviderErrorKind.INVALID_OUTPUT,
                "Antigravity CLI rejected the assessment schema argument.",
                retryable=False,
            )
        raise AntigravityProviderError(
            ProviderErrorKind.INVALID_OUTPUT,
            "Antigravity CLI did not return a complete assessment result.",
            retryable=True,
        )

    @classmethod
    def parse_response(
        cls,
        *,
        returncode: int,
        stdout: str,
        stderr: str,
        rubric: Rubric,
        answer_text: str,
    ) -> tuple[CriterionObservation, ...]:
        if len(stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise AntigravityProviderError(
                ProviderErrorKind.INVALID_OUTPUT,
                "Antigravity response exceeded the 2 MB safety limit.",
                retryable=False,
            )

        events: list[dict[str, Any]] = []
        malformed = False
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                malformed = True
                continue
            if not isinstance(event, dict):
                malformed = True
                continue
            events.append(event)

        results: list[dict[str, Any]] = []
        for event in events:
            if event.get("event") == "result":
                raw_res = event.get("result")
                if isinstance(raw_res, dict):
                    results.append(raw_res)
                else:
                    malformed = True

        for event in events:
            step = event.get("step_update", {})
            if not isinstance(step, dict):
                malformed = True
                continue
            if step.get("step_type") == "tool" and step.get("tool_name") != "finish":
                raise AntigravityProviderError(
                    ProviderErrorKind.INVALID_OUTPUT,
                    "Antigravity attempted a tool call instead of returning an assessment.",
                    retryable=True,
                )

        has_runtime_error = any(
            line.startswith("AGY_ERROR:") for line in stderr.splitlines()
        )
        if (
            has_runtime_error
            or returncode != 0
            or len(results) != 1
            or results[0].get("status") != "SUCCESS"
        ):
            cls._raise_provider_failure(stderr, results)
        if malformed:
            raise AntigravityProviderError(
                ProviderErrorKind.INVALID_OUTPUT,
                "Antigravity CLI emitted malformed NDJSON lines alongside result.",
                retryable=True,
            )

        try:
            res_payload = results[0]
            content = res_payload.get("structured_output")
            if content is None:
                content = res_payload["response"]
            if isinstance(content, str):
                content = json.loads(content)
            validated_top = cls.response_model(rubric).model_validate(content)
            raw_checks = validated_top.model_dump(by_alias=True)["criterion_checks"]
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            detail = "invalid JSON envelope"
            if isinstance(error, ValidationError):
                first = error.errors(include_input=False, include_context=False)[0]
                known_fields = {"criterion_checks", *AntigravityCriterionDTO.model_fields,
                                *(criterion.id for criterion in rubric.criteria)}
                path = ".".join(str(part) if part in known_fields else "?" for part in first["loc"])
                detail = f"{path or 'root'} ({first['type']})"
            raise AntigravityProviderError(
                ProviderErrorKind.INVALID_OUTPUT,
                f"Invalid assessment JSON: {detail}; no score was created.",
                retryable=True,
            ) from None

        observations: list[CriterionObservation] = []
        for criterion in rubric.criteria:
            dto = AntigravityCriterionDTO.model_validate(raw_checks[criterion.id])
            resolved = _resolve_quote_offsets(criterion.id, dto, answer_text)
            observations.append(
                CriterionObservation(
                    criterion_id=CriterionId(criterion.id),
                    status=resolved.status,
                    explanation=resolved.explanation,
                    quote=resolved.quote,
                    start_offset=resolved.start_offset,
                    end_offset=resolved.end_offset,
                    observation=resolved.observation,
                    unresolved_reason=resolved.unresolved_reason,
                    satisfied_expected_indexes=(
                        tuple(resolved.satisfied_expected_indexes)
                        if resolved.satisfied_expected_indexes is not None
                        else None
                    ),
                )
            )
        return tuple(observations)

    def interpret_answer(
        self,
        *,
        question: Question,
        rubric: Rubric,
        answer_text: str,
    ) -> AntigravityCallResult:
        executable = self.executable_path()
        if executable is None:
            raise AntigravityProviderError(
                ProviderErrorKind.CONFIG,
                "Antigravity CLI (`agy`) is unavailable; install it (a native .exe on Windows) and sign in.",
                retryable=False,
            )

        prompt = self.build_prompt(
            question=question,
            rubric=rubric,
            answer_text=answer_text,
        )
        stdin_ndjson = (
            json.dumps({"event": "user", "message": {"content": prompt}}, ensure_ascii=False)
            + "\n"
        )
        if len(stdin_ndjson.encode("utf-8")) > self.limits.input_bytes:
            raise AntigravityProviderError(ProviderErrorKind.INPUT_LIMIT, "Request exceeds byte limit.")
        command = self.build_command(executable, rubric)
        started = time.perf_counter()
        request_id = uuid4().hex
        for attempt in range(self.limits.max_retries + 1):
            outcome = "OK"
            tick = time.perf_counter()
            try:
                try:
                    reserved = self._budget.reserve()
                except RepositoryError:
                    raise AntigravityProviderError(ProviderErrorKind.CONFIG, "Cannot reserve request budget.") from None
                if not reserved:
                    raise AntigravityProviderError(ProviderErrorKind.QUOTA, "Configured request budget exhausted.")
                return self._run_attempt(command, stdin_ndjson, started, rubric, answer_text)
            except AntigravityProviderError as error:
                outcome = error.code
                if (attempt >= self.limits.max_retries or not error.retryable or
                        error.code not in {ProviderErrorKind.TIMEOUT, ProviderErrorKind.QUOTA}):
                    raise
            finally:
                logging.getLogger(__name__).info(
                    "agy request_id=%s attempt=%d elapsed_ms=%d outcome=%s",
                    request_id, attempt + 1, (time.perf_counter() - tick) * 1000, outcome,
                )
        raise AssertionError("Invalid retry configuration")

    def _bounded_runner(self, command, *, input, timeout, cwd, env, creationflags,
                        encoding, **options):
        """Feed stdin from a file; drain both output pipes within fixed byte limits."""
        from threading import Event, Thread

        exceeded = Event()
        buffers = [bytearray(), bytearray()]
        with tempfile.TemporaryFile() as source:
            source.write(input.encode(encoding))
            source.seek(0)
            with subprocess.Popen(command, stdin=source, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, cwd=cwd, env=env,
                                  creationflags=creationflags, bufsize=0) as process:
                def drain(pipe, buffer):
                    with pipe:
                        while True:
                            remaining = self.limits.response_bytes - len(buffer)
                            chunk = pipe.read(min(65536, remaining + 1))
                            if len(chunk) > remaining:
                                exceeded.set()
                                process.kill()
                                return
                            if not chunk:
                                return
                            buffer.extend(chunk)

                readers = [Thread(target=drain, args=(pipe, buffer), daemon=True)
                           for pipe, buffer in zip((process.stdout, process.stderr), buffers)]
                for reader in readers:
                    reader.start()
                deadline = time.monotonic() + timeout
                try:
                    process.wait(timeout=timeout)
                    for reader in readers:
                        reader.join(max(0, deadline - time.monotonic()))
                        if reader.is_alive():
                            raise subprocess.TimeoutExpired(command, timeout)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                if exceeded.is_set():
                    raise AntigravityProviderError(ProviderErrorKind.INVALID_OUTPUT,
                                                   "Antigravity output exceeds byte limit.")
                return subprocess.CompletedProcess(command, process.returncode,
                                                   buffers[0].decode(encoding), buffers[1].decode(encoding))

    def _run_attempt(self, command: list[str], stdin_ndjson: str, started: float,
                     rubric: Rubric, answer_text: str) -> AntigravityCallResult:
        try:
            with tempfile.TemporaryDirectory(prefix="interview-antigravity-") as workdir:
                proc = self._runner(
                    command,
                    input=stdin_ndjson,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=self.timeout_seconds + 10.0,
                    cwd=workdir,
                    env=self.subscription_environment(),
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
        except subprocess.TimeoutExpired:
            raise AntigravityProviderError(
                ProviderErrorKind.TIMEOUT,
                "Antigravity CLI process timed out; saved answer is unchanged.",
                retryable=True,
            ) from None
        except (OSError, UnicodeError):
            raise AntigravityProviderError(
                ProviderErrorKind.NETWORK,
                "Cannot execute Antigravity CLI; check installation and sign-in.",
                retryable=True,
            ) from None

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if max(len(proc.stdout.encode("utf-8")), len(proc.stderr.encode("utf-8"))) > self.limits.response_bytes:
            raise AntigravityProviderError(ProviderErrorKind.INVALID_OUTPUT, "Response exceeds byte limit.")
        observations = self.parse_response(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            rubric=rubric,
            answer_text=answer_text,
        )
        return AntigravityCallResult(
            observations=observations,
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
        return InterpretationBatch(
            observations=call_result.observations,
            model_id=call_result.model_id,
            prompt_version=call_result.prompt_version,
            demo_mode_label=None,
            elapsed_ms=call_result.elapsed_ms,
        )


__all__ = [
    "AntigravityCallResult",
    "AntigravityCriterionDTO",
    "AntigravityProvider",
    "AntigravityProviderError",
    "DEFAULT_ANTIGRAVITY_EXECUTABLE",
    "DEFAULT_ANTIGRAVITY_MODEL",
    "DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS",
]
