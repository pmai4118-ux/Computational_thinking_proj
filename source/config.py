import math
import os
import re
from dataclasses import dataclass, field
from typing import ClassVar

from source.service.evaluationErrors import EvaluationError


@dataclass(frozen=True)
class GeminiSettings:
    defaultModelName: ClassVar[str] = "gemini-4-hydrogen"
    apiKey: str = field(repr=False)
    modelName: str
    timeoutSeconds: float = 45

    @classmethod
    def fromEnvironment(cls) -> "GeminiSettings":
        apiKey = os.environ.get("GEMINI_API_KEY", "")
        modelName = os.environ.get("GEMINI_MODEL", cls.defaultModelName).strip()
        if not apiKey.strip():
            raise EvaluationError("providerConfig", "GEMINI_API_KEY is required for Gemini mode.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,119}", modelName):
            raise EvaluationError("providerConfig", "GEMINI_MODEL must be a valid model ID.")
        try:
            timeoutSeconds = float(os.environ.get("EVALUATION_TIMEOUT", "45"))
        except ValueError as error:
            raise EvaluationError("providerConfig", "EVALUATION_TIMEOUT must be a number of seconds.") from error
        if not math.isfinite(timeoutSeconds) or not 1 <= timeoutSeconds <= 120:
            raise EvaluationError("providerConfig", "EVALUATION_TIMEOUT must be between 1 and 120 seconds.")
        return cls(apiKey=apiKey, modelName=modelName, timeoutSeconds=timeoutSeconds)
