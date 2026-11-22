from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator as modelValidator

from source.Model.evaluationData import EvaluationReport


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    inputPath: Path
    providerName: Literal["gemini", "recorded"]
    recordingPath: Path | None = None
    answerPath: Path | None = None
    outputPath: Path | None = None

    @modelValidator(mode="after")
    def checkRecording(self):
        if (self.providerName == "recorded") != (self.recordingPath is not None):
            raise ValueError("recordingPath is required only for the recorded provider.")
        return self


class EvaluationFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    retryable: bool = False
    fields: tuple[str, ...] = ()


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: EvaluationReport | None = None
    outputPath: Path | None = None
    error: EvaluationFailure | None = None

    @modelValidator(mode="after")
    def checkOutcome(self):
        success = self.report is not None and self.outputPath is not None and self.error is None
        failure = self.report is None and self.outputPath is None and self.error is not None
        if not (success or failure):
            raise ValueError("A response must contain either a complete report or an error.")
        return self
