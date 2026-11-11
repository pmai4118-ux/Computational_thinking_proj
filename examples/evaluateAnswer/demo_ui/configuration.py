"""Server-only configuration for the standalone demo."""

import json
import os
from collections.abc import Mapping
from pathlib import Path

from source.service.evaluationErrors import EvaluationError
from source.service.providers.geminiInterpreter import GeminiInterpreter, GeminiSettings
from source.service.providers.antigravityInterpreter import AntigravitySettings


DEFAULT_MODEL = "gemini-3.8-flash"
LOCAL_SETTINGS_PATH = Path(__file__).resolve().parents[3] / "secrets" / "demo-gemini.json"
SETTING_NAMES = {"GEMINI_API_KEY", "GEMINI_MODEL", "EVALUATION_TIMEOUT"}


def selectedProvider() -> str:
    providerName = os.environ.get("DEMO_EVALUATION_PROVIDER", "").strip() or "antigravity"
    if providerName not in {"antigravity", "gemini"}:
        raise EvaluationError("providerConfig", "DEMO_EVALUATION_PROVIDER must be antigravity or gemini.")
    return providerName


def loadAntigravitySettings() -> AntigravitySettings:
    try:
        timeout = float(os.environ.get("ANTIGRAVITY_TIMEOUT", "").strip() or "120")
    except ValueError:
        raise EvaluationError("providerConfig", "ANTIGRAVITY_TIMEOUT must be a number of seconds.") from None
    return AntigravitySettings(
        modelName=os.environ.get("ANTIGRAVITY_MODEL", "").strip() or "gemini-3.8-flash-medium",
        timeoutSeconds=timeout,
        executable=os.environ.get("ANTIGRAVITY_EXECUTABLE", "").strip() or "agy",
    )


def loadDemoSettings(
    settingsPath: Path = LOCAL_SETTINGS_PATH,
    environment: Mapping[str, str] | None = None,
) -> GeminiSettings | None:
    """Read ignored local settings; environment variables take precedence.

    Missing credentials leave recorded previews available. Settings are never
    added to the process environment or returned to the browser.
    """
    values = {}
    if settingsPath.exists():
        try:
            values = json.loads(settingsPath.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            raise EvaluationError("providerConfig", "Cannot read secrets/demo-gemini.json; check its JSON format.") from None
        if not isinstance(values, dict) or set(values) - SETTING_NAMES or any(not isinstance(value, str) for value in values.values()):
            raise EvaluationError("providerConfig", "Local demo settings must contain only supported string-valued settings.")

    currentEnvironment = os.environ if environment is None else environment
    values.update({
        name: currentEnvironment[name] for name in SETTING_NAMES
        if name in currentEnvironment and (name == "GEMINI_API_KEY" or currentEnvironment[name].strip())
    })
    apiKey = values.get("GEMINI_API_KEY", "").strip()
    if not apiKey:
        return None
    modelName = values.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
    try:
        timeoutSeconds = float(values.get("EVALUATION_TIMEOUT", "").strip() or "60")
    except ValueError:
        raise EvaluationError("providerConfig", "EVALUATION_TIMEOUT must be a number of seconds.") from None
    # Reuse provider validation without making a network request.
    GeminiInterpreter(apiKey, modelName, timeoutSeconds)
    return GeminiSettings(apiKey=apiKey, modelName=modelName, timeoutSeconds=timeoutSeconds)
