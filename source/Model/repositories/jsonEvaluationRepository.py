import os
import tempfile
from pathlib import Path
from uuid import uuid4

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import EvaluationReport, RecordedReview


def readTextFile(filePath: Path) -> str:
    with filePath.open("rb") as inputFile:
        rawText = inputFile.read(1000001)
    if len(rawText) > 1000000:
        raise ValueError("The input file exceeds 1 MB.")
    return rawText.decode("utf-8-sig")


def writeNewReport(report: EvaluationReport, outputPath: Path) -> None:
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    temporaryPath = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=outputPath.parent, delete=False) as reportFile:
            temporaryPath = Path(reportFile.name)
            reportFile.write(report.model_dump_json(indent=2))
            reportFile.flush()
            os.fsync(reportFile.fileno())
        os.link(temporaryPath, outputPath)
    finally:
        if temporaryPath is not None:
            temporaryPath.unlink(missing_ok=True)


class JsonEvaluationRepository:
    def __init__(self, reportDirectory: Path):
        self.reportDirectory = reportDirectory

    def loadInput(self, inputPath: Path) -> EvaluationInput:
        return EvaluationInput.model_validate_json(readTextFile(inputPath))

    def loadAnswer(self, answerPath: Path) -> str:
        return readTextFile(answerPath)

    def loadRecording(self, recordingPath: Path) -> RecordedReview:
        return RecordedReview.model_validate_json(readTextFile(recordingPath))

    def resolveOutput(self, outputPath: Path | None) -> Path:
        resultPath = outputPath if outputPath is not None else self.reportDirectory / f"report-{uuid4().hex}.json"
        if resultPath.exists():
            raise FileExistsError("The report already exists.")
        return resultPath

    def saveReport(self, report: EvaluationReport, outputPath: Path) -> None:
        writeNewReport(report, outputPath)
