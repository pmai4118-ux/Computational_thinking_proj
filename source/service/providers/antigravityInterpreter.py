"""Interpret evidence using the signed-in local Antigravity CLI subscription."""

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Annotated, NoReturn

from pydantic import Field, ValidationError, create_model

from source.Model.answerData import EvaluationInput, FrozenData, Text
from source.Model.evaluationData import CheckStatus, Evidence, Interpretation, Offset
from source.service.evaluationErrors import EvaluationError
from source.service.prompts.evaluationPrompt import EvaluationPrompt


@dataclass(frozen=True)
class AntigravitySettings:
    modelName: str = "gemini-3.8-flash-medium"
    timeoutSeconds: float = 120
    executable: str = "agy"

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", self.modelName):
            raise EvaluationError("providerConfig", "Provide an Antigravity model slug from 'agy models'.")
        if isinstance(self.timeoutSeconds, bool) or not 1 <= self.timeoutSeconds <= 300:
            raise EvaluationError("providerConfig", "Antigravity timeout must be between 1 and 300 seconds.")


class AntigravityEvidence(Evidence):
    # Optional provider metadata is filled deterministically by EvidenceReview.
    # Supplied quotes/offsets remain untouched and must pass its strict checks.
    quote: Text | None = None
    location: Text = "originalText"
    startOffset: Offset | None = None
    endOffset: Offset | None = None


class AntigravityCriterion(FrozenData):
    status: CheckStatus
    evidence: Annotated[tuple[AntigravityEvidence, ...], Field(min_length=1, max_length=12)]


class AntigravityInterpreter:
    providerName = "antigravity"

    def __init__(self, settings: AntigravitySettings):
        self.settings = settings
        self.modelName = settings.modelName
        self.prompt = EvaluationPrompt()
        self.promptVersion = self.prompt.version + "+antigravity/3"

    @staticmethod
    def sessionSettings() -> dict:
        return {
            "modelProvider": "",
            "useG1Credits": False,
            "toolPermission": "request-review",
            "permissions": {
                "allow": [],
                "deny": ["command(*)", "read_file(*)", "write_file(*)", "read_url(*)", "execute_url(*)", "mcp(*)"],
            },
        }

    @staticmethod
    def subscriptionEnvironment() -> dict[str, str]:
        environment = dict(os.environ)
        for name in (
            "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GEMINI_BASE_URL",
            "GOOGLE_GENAI_USE_VERTEXAI", "AGY_ADC_AUTH", "GOOGLE_APPLICATION_CREDENTIALS",
        ):
            environment.pop(name, None)
        return environment

    @staticmethod
    def responseModel(inputs: EvaluationInput) -> type[FrozenData]:
        """Require exact IDs as object keys using Gemini-compatible tool schemas.

        The CLI submits this as a tool schema, which cannot express fixed tuples
        using prefixItems. Keyed objects require every rubric and criterion without
        depending on array order, const, or composition keywords.
        """
        rubricFields = {}
        for index, rubric in enumerate(inputs.rubrics):
            checks = create_model(
                f"AntigravityRubric{index}", __base__=FrozenData,
                **{f"c{number}": (AntigravityCriterion, Field(alias=criterion.criterionId))
                   for number, criterion in enumerate(rubric.criteria)},
            )
            rubricFields[f"r{index}"] = (checks, Field(alias=rubric.rubricId))
        reviews = create_model("AntigravityReviews", __base__=FrozenData, **rubricFields)
        return create_model("AntigravityAssessment", __base__=FrozenData, reviews=(reviews, ...))

    @classmethod
    def responseSchema(cls, inputs: EvaluationInput) -> dict:
        return cls.responseModel(inputs).model_json_schema()

    def executablePath(self) -> str | None:
        executable = shutil.which(self.settings.executable)
        if executable is not None and os.name == "nt" and not executable.lower().endswith(".exe"):
            return None
        return executable

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        executable = self.executablePath()
        if executable is None:
            raise EvaluationError("providerConfig", "Antigravity CLI is unavailable. Install it (a native .exe on Windows) and sign in with your Google AI Pro account using 'agy'.")
        prompt = self.prompt.systemPrompt() + (
            "\nSubmit the assessment using the finish structured-output tool only. "
            "Do not use command, file, workspace, web, or MCP tools. All required data is in the JSON below. "
            "Return a reviews OBJECT keyed by the exact rubricId values. "
            "Each rubric value is an OBJECT keyed by its exact criterionId values. "
            "Each criterion value contains status and evidence only, following the output schema. "
            "Include every rubric and criterion exactly once; do not invent ID fields or keys. "
            "For a unique exact quote, set both offsets to null; Python will locate it. "
            "For a repeated quote, provide both exact offsets. "
            "For omission evidence, quote and both offsets must be null and location must be 'Entire originalText'.\n"
        )
        prompt += json.dumps(self.prompt.promptPayload(inputs), ensure_ascii=False)
        if len(prompt.encode("utf-8")) > 250000:
            raise EvaluationError("inputLimit", "The AI request exceeds the 250 KB PoC limit.")
        # Send the answer on stdin to avoid shell interpretation and Windows' command-line length limit.
        request = json.dumps({"event": "user", "message": {"content": prompt}}, ensure_ascii=False) + "\n"
        command = [
            executable,
            "--settings", json.dumps(self.sessionSettings()),
            "--model", self.modelName,
            "--disable-slash-commands",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--json-schema", json.dumps(self.responseSchema(inputs)),
            "--print-timeout", f"{self.settings.timeoutSeconds}s",
        ]
        try:
            # Empty workspace avoids loading repository instructions or exposing local credentials.
            with tempfile.TemporaryDirectory(prefix="interview-antigravity-") as workingDirectory:
                response = subprocess.run(
                    command, input=request, capture_output=True, text=True, encoding="utf-8",
                    timeout=self.settings.timeoutSeconds + 10, cwd=workingDirectory,
                    env=self.subscriptionEnvironment(), shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            return self.parseResponse(response, inputs)
        except subprocess.TimeoutExpired:
            raise EvaluationError("providerTimeout", "Antigravity timed out. The original answer remains in the editor.", True) from None
        except (OSError, UnicodeError):
            raise EvaluationError("providerNetwork", "Cannot run Antigravity. Check its installation and Google account sign-in.", True) from None

    @staticmethod
    def raiseProviderFailure(stderr: str, results: list[dict]) -> NoReturn:
        # Do not search echoed response/schema data: IDs and answer text are data,
        # not diagnostics. These are the CLI's documented failure envelope fields.
        parts = [stderr]
        for result in results:
            parts.extend(str(result.get(key, "")) for key in ("status", "error"))
        diagnostics = " ".join(parts).lower()
        if re.search(r"\b(?:timeout|timed out|deadline[ _]exceeded)\b", diagnostics):
            raise EvaluationError("providerTimeout", "Antigravity timed out. The original answer remains in the editor.", True)
        if re.search(r"\b(?:quota|rate[ -]limit(?:ed)?|resource_exhausted)\b", diagnostics):
            raise EvaluationError("providerQuota", "Antigravity subscription quota is exhausted. Wait for its quota to refresh; no API-key fallback was used.", True)
        if re.search(r"\b(?:unauthenticated|unauthorized|authentication|credentials?|sign[ -]in|log[ -]?in)\b", diagnostics):
            raise EvaluationError("providerConfig", "Sign in to Antigravity with your Google AI Pro account using 'agy', then retry.")
        if "invalid_argument" in diagnostics:
            raise EvaluationError("providerSchema", "Antigravity rejected the assessment request format. Restart the demo with the updated provider adapter.")
        raise EvaluationError("providerOutput", "Antigravity did not return one complete assessment. Check its account and model availability.")

    def parseResponse(self, response: subprocess.CompletedProcess, inputs: EvaluationInput) -> Interpretation:
        if len(response.stdout.encode("utf-8")) > 2000000:
            raise EvaluationError("providerOutput", "The Antigravity response exceeds the PoC output limit.")
        try:
            events = []
            malformed = False
            for line in response.stdout.splitlines():
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
            results = []
            for event in events:
                if event.get("event") == "result":
                    if isinstance(event.get("result"), dict):
                        results.append(event["result"])
                    else:
                        malformed = True
            # A result is accepted only when the request completed without agent tool execution.
            for event in events:
                step = event.get("step_update", {})
                if not isinstance(step, dict):
                    malformed = True
                    continue
                if step.get("step_type") == "tool" and step.get("tool_name") != "finish":
                    raise EvaluationError("providerOutput", "Antigravity attempted a tool action instead of returning an assessment.")
            # CLI 1.5.3 can emit SUCCESS/exit 0 with partial output on print timeout;
            # its explicit stderr error envelope takes precedence over that result.
            runtimeError = any(line.startswith("AGY_ERROR:") for line in response.stderr.splitlines())
            if runtimeError or response.returncode != 0 or len(results) != 1 or results[0].get("status") != "SUCCESS":
                self.raiseProviderFailure(response.stderr, results)
            if malformed:
                raise ValueError()
            result = results[0]
            content = result.get("structured_output")
            if content is None:
                content = json.loads(result["response"])
            checked = self.responseModel(inputs).model_validate(content).model_dump(by_alias=True)
            return Interpretation.model_validate({"reviews": [
                {"rubricId": rubric.rubricId, "criterionChecks": [
                    {"criterionId": criterion.criterionId, **checked["reviews"][rubric.rubricId][criterion.criterionId]}
                    for criterion in rubric.criteria
                ]}
                for rubric in inputs.rubrics
            ]})
        except (ValueError, TypeError, KeyError, AttributeError, ValidationError):
            raise EvaluationError("providerOutput", "Antigravity returned invalid assessment JSON; no score was created.") from None
