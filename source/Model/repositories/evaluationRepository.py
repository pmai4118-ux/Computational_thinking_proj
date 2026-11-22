from pathlib import Path
from typing import Protocol

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import EvaluationReport, RecordedReview


class EvaluationRepository(Protocol):
    def loadInput(self, inputPath: Path) -> EvaluationInput:
        ...

    def loadAnswer(self, answerPath: Path) -> str:
        ...

    def loadRecording(self, recordingPath: Path) -> RecordedReview:
        ...

    def resolveOutput(self, outputPath: Path | None) -> Path:
        ...

    def saveReport(self, report: EvaluationReport, outputPath: Path) -> None:
        ...
