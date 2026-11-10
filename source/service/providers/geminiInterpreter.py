import json
import os
import re
import socket
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import Interpretation
from source.service.evaluationErrors import EvaluationError
from source.service.prompts.evaluationPrompt import promptPayload, promptVersion, systemPrompt


@dataclass(frozen=True)
class GeminiSettings:
    apiKey: str = field(repr=False)
    modelName: str
    timeoutSeconds: float


def readGeminiSettings() -> GeminiSettings:
    apiKey = os.environ.get("GEMINI_API_KEY", "")
    modelName = os.environ.get("GEMINI_MODEL", "")
    if not apiKey.strip() or not modelName.strip():
        raise EvaluationError("providerConfig", "GEMINI_API_KEY and GEMINI_MODEL are required.")
    try:
        timeoutSeconds = float(os.environ.get("EVALUATION_TIMEOUT", "45"))
    except ValueError as error:
        raise EvaluationError("providerConfig", "EVALUATION_TIMEOUT must be a number of seconds.") from error
    return GeminiSettings(apiKey=apiKey, modelName=modelName, timeoutSeconds=timeoutSeconds)


class GeminiInterpreter:
    providerName = "gemini"
    promptVersion = promptVersion

    def __init__(self, apiKey: str, modelName: str, timeoutSeconds: float = 45):
        if not apiKey.strip() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", modelName):
            raise EvaluationError("providerConfig", "Provide a valid GEMINI_API_KEY and GEMINI_MODEL without the models/ prefix.")
        if not 1 <= timeoutSeconds <= 120:
            raise EvaluationError("providerConfig", "Timeout must be between 1 and 120 seconds.")
        self.apiKey = apiKey
        self.modelName = modelName
        self.timeoutSeconds = timeoutSeconds

    def buildRequest(self, inputs: EvaluationInput) -> Request:
        payload = {
            "systemInstruction": {"parts": [{"text": systemPrompt()}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(promptPayload(inputs), ensure_ascii=False)}]}],
            "generationConfig": {
                "candidateCount": 1,
                "maxOutputTokens": 16384,
                "responseMimeType": "application/json",
                "responseJsonSchema": Interpretation.model_json_schema(),
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > 250000:
            raise EvaluationError("inputLimit", "The AI request exceeds the 250 KB PoC limit.")
        return Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.modelName}:generateContent",
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": self.apiKey},
            method="POST",
        )

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        request = self.buildRequest(inputs)
        try:
            with urlopen(request, timeout=self.timeoutSeconds) as response:
                rawBody = response.read(1000001)
            if len(rawBody) > 1000000:
                raise EvaluationError("providerOutput", "The AI response exceeds 1 MB.")
            return self.parseResponse(rawBody)
        except HTTPError as error:
            error.close()
            if error.code == 429:
                raise EvaluationError("providerQuota", "The AI service rate limit was reached; no score was created.", True) from error
            retryable = error.code >= 500 or error.code == 408
            raise EvaluationError("providerHttp", f"The AI service returned HTTP {error.code}; check the model and configuration or retry.", retryable) from error
        except (TimeoutError, socket.timeout) as error:
            raise EvaluationError("providerTimeout", "The AI service timed out; the original answer remains unchanged.", True) from error
        except URLError as error:
            raise EvaluationError("providerNetwork", "Cannot reach the AI service; no score was created.", True) from error
        except OSError as error:
            raise EvaluationError("providerNetwork", "The AI service connection was interrupted; no score was created.", True) from error

    def parseResponse(self, rawBody: bytes) -> Interpretation:
        try:
            response = json.loads(rawBody)
            if response.get("promptFeedback", {}).get("blockReason"):
                raise EvaluationError("providerRefusal", "The AI service declined this request; this is not an assessment result.")
            candidates = response.get("candidates", [])
            if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
                raise EvaluationError("providerIncomplete", "The AI service did not return one complete result; no score was created.")
            parts = candidates[0]["content"]["parts"]
            content = "".join(part["text"] for part in parts if "text" in part and not part.get("thought", False))
            return Interpretation.model_validate_json(content)
        except (ValueError, KeyError, TypeError, AttributeError, ValidationError) as error:
            raise EvaluationError("providerOutput", "The AI response JSON is invalid; no score was created.") from error
