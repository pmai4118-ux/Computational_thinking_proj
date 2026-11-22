import json
import math
import re
import time
from collections.abc import Mapping

from pydantic import ValidationError

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import Interpretation
from source.service.evaluationErrors import EvaluationError
from source.service.prompts.evaluationPrompt import EvaluationPrompt


MAX_INPUT_BYTES = 250_000
MAX_OUTPUT_BYTES = 1_000_000
MAX_OUTPUT_TOKENS = 16_384
REFUSAL_CODES = {
    "BLOCKED",
    "BLOCKLIST",
    "IMAGE_SAFETY",
    "PROHIBITED_CONTENT",
    "REFUSAL",
    "SAFETY",
}
SCHEMA_CONSTRAINTS_VALIDATED_BY_CLIENT = {
    "maxItems",
    "maxLength",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "pattern",
}


class GeminiProvider:
    providerName = "gemini"

    def __init__(
        self,
        apiKey: str,
        modelName: str,
        timeoutSeconds: float = 45,
        prompt: EvaluationPrompt | None = None,
        client=None,
    ):
        if not isinstance(apiKey, str) or not apiKey.strip():
            raise EvaluationError("providerConfig", "GEMINI_API_KEY is required for Gemini mode.")
        if not isinstance(modelName, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,119}", modelName):
            raise EvaluationError("providerConfig", "GEMINI_MODEL must be a valid model ID.")
        if (
            isinstance(timeoutSeconds, bool)
            or not isinstance(timeoutSeconds, (int, float))
            or not math.isfinite(timeoutSeconds)
            or not 1 <= timeoutSeconds <= 120
        ):
            raise EvaluationError("providerConfig", "Timeout must be between 1 and 120 seconds.")
        self.apiKey = apiKey
        self.modelName = modelName
        self.timeoutSeconds = timeoutSeconds
        self.prompt = prompt if prompt is not None else EvaluationPrompt()
        self.promptVersion = self.prompt.version
        self.client = client if client is not None else self.createClient()
        self.lastRequestDurationMs: int | None = None

    def createClient(self):
        try:
            from google import genai
        except ImportError as error:
            raise EvaluationError(
                "providerDependency",
                "The pinned Google GenAI SDK is missing. Install the project dependencies before using Gemini mode.",
            ) from error
        return genai.Client(api_key=self.apiKey)

    def buildRequest(self, inputs: EvaluationInput) -> dict[str, object]:
        payload = {
            "model": self.modelName,
            "input": json.dumps(self.prompt.promptPayload(inputs), ensure_ascii=False),
            "system_instruction": self.prompt.systemPrompt(),
            "generation_config": {
                "temperature": 0.0,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
            },
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": self.buildResponseSchema(),
            },
            "store": False,
            "timeout": self.timeoutSeconds,
        }
        serialized = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(serialized) > MAX_INPUT_BYTES:
            raise EvaluationError("inputLimit", "The Gemini request exceeds the 250 KB PoC limit.")
        return payload

    def buildResponseSchema(self) -> dict[str, object]:
        schema = Interpretation.model_json_schema()
        return self.removeClientValidatedConstraints(schema)

    def removeClientValidatedConstraints(self, value):
        if isinstance(value, dict):
            return {
                key: self.removeClientValidatedConstraints(item)
                for key, item in value.items()
                if key not in SCHEMA_CONSTRAINTS_VALIDATED_BY_CLIENT
            }
        if isinstance(value, list):
            return [self.removeClientValidatedConstraints(item) for item in value]
        return value

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        self.lastRequestDurationMs = None
        request = self.buildRequest(inputs)
        startedAt = time.perf_counter()
        try:
            response = self.client.interactions.create(**request)
            return self.parseResponse(response)
        except EvaluationError:
            raise
        except Exception as error:
            mappedError = self.mapSdkError(error)
            if mappedError is None:
                raise
            raise mappedError from error
        finally:
            self.lastRequestDurationMs = max(0, round((time.perf_counter() - startedAt) * 1000))

    def parseResponse(self, response: object) -> Interpretation:
        errors = self.readField(response, "errors")
        error = self.readField(response, "error")
        if self.isRefusal(errors) or self.isRefusal(error):
            raise EvaluationError("providerRefusal", "Gemini declined the request; this is not an assessment result.")
        if errors:
            raise EvaluationError("providerFailure", "Gemini returned an error response; no score was created.", True)

        status = self.normalizeValue(self.readField(response, "status"))
        if status and status not in {"COMPLETED", "COMPLETE", "SUCCESS"}:
            raise EvaluationError("providerIncomplete", "Gemini did not complete the interpretation; no score was created.", True)

        outputText = self.readField(response, "output_text")
        if not isinstance(outputText, str) or not outputText.strip():
            raise EvaluationError("providerIncomplete", "Gemini returned no interpretation text; no score was created.", True)
        if len(outputText.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise EvaluationError("providerOutput", "Gemini returned more than 1 MB of output; no score was created.")

        try:
            return Interpretation.model_validate_json(outputText)
        except (ValidationError, ValueError, TypeError) as error:
            raise EvaluationError(
                "providerOutput",
                "Gemini returned invalid JSON or data that does not match the interpretation schema.",
            ) from error

    def mapSdkError(self, error: Exception) -> EvaluationError | None:
        errorName = type(error).__name__.lower()
        errorModule = type(error).__module__
        statusCode = self.readField(error, "status_code")
        if statusCode is None:
            statusCode = self.readField(error, "statusCode")
        if statusCode is None:
            statusCode = self.readField(error, "code")

        if "timeout" in errorName or isinstance(error, TimeoutError):
            return EvaluationError("providerTimeout", "Gemini timed out; no score was created.", True)
        if "connection" in errorName or isinstance(error, OSError):
            return EvaluationError("providerNetwork", "Gemini could not be reached; no score was created.", True)

        if isinstance(statusCode, int):
            if statusCode == 429:
                return EvaluationError("providerQuota", "Gemini rate limit reached; no score was created.", True)
            if statusCode in {401, 403}:
                return EvaluationError("providerAuth", "Gemini rejected the configured credentials; no score was created.")
            if statusCode == 408 or statusCode >= 500:
                return EvaluationError("providerHttp", "Gemini is temporarily unavailable; no score was created.", True)
            if 400 <= statusCode < 500:
                return EvaluationError("providerHttp", "Gemini rejected the request; check model access and request configuration.")

        if errorModule.startswith("google.genai"):
            return EvaluationError("providerFailure", "Gemini could not complete the request; no score was created.", True)
        return None

    def isRefusal(self, error: object) -> bool:
        if error is None:
            return False
        if isinstance(error, (list, tuple)):
            return any(self.isRefusal(item) for item in error)
        fields = ("code", "status", "type", "reason", "block_reason", "blockReason")
        for fieldName in fields:
            value = self.readField(error, fieldName)
            if self.normalizeValue(value) in REFUSAL_CODES:
                return True
        return False

    @staticmethod
    def readField(value: object, fieldName: str):
        if isinstance(value, Mapping):
            return value.get(fieldName)
        return getattr(value, fieldName, None)

    @staticmethod
    def normalizeValue(value: object) -> str:
        if value is None:
            return ""
        if hasattr(value, "value"):
            value = value.value
        elif hasattr(value, "name"):
            value = value.name
        return str(value).rsplit(".", maxsplit=1)[-1].replace("-", "_").replace(" ", "_").upper()
