import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import EvaluationReport, RecordedReview


class JsonEvaluationRepository:
    def __init__(self, reportDirectory: Path):
        self.reportDirectory = reportDirectory

    def loadInput(self, inputPath: Path) -> EvaluationInput:
        return EvaluationInput.model_validate_json(self.readTextFile(inputPath))

    def loadAnswer(self, answerPath: Path) -> str:
        return self.readTextFile(answerPath)

    def loadRecording(self, recordingPath: Path) -> RecordedReview:
        return RecordedReview.model_validate_json(self.readTextFile(recordingPath))

    def cachePath(self, inputHash: str) -> Path:
        return self.reportDirectory / f"report-{inputHash}.json"

    def findCompletedReport(self, inputHash: str) -> tuple[EvaluationReport, Path] | None:
        path = self.cachePath(inputHash)
        if path.exists():
            report = EvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))
            if report.inputHash != inputHash or report.inputs.inputDigest() != inputHash:
                raise OSError("The stored evaluation does not match its input hash.")
            return report, path

        # Reports from before hash-based storage used a UUID hex filename.
        for legacyPath in sorted(self.reportDirectory.glob("report-*.json")):
            if not re.fullmatch(r"report-[0-9a-f]{32}\.json", legacyPath.name) or not legacyPath.is_file():
                continue
            try:
                report = EvaluationReport.model_validate_json(legacyPath.read_bytes())
            except (FileNotFoundError, ValidationError):
                continue
            if report.inputHash == inputHash and report.inputs.inputDigest() == inputHash:
                return report, legacyPath
        return None

    def resolveOutput(self, outputPath: Path | None, inputHash: str | None = None) -> Path:
        resultPath = outputPath if outputPath is not None else self.cachePath(inputHash or uuid4().hex)
        if outputPath is not None and inputHash is not None:
            cachePath = self.cachePath(inputHash)
            if outputPath.resolve() == cachePath.resolve():
                resultPath = cachePath
        if resultPath.exists():
            raise FileExistsError("The report already exists.")
        return resultPath

    def saveReport(self, report: EvaluationReport, outputPath: Path) -> None:
        cachePath = self.cachePath(report.inputHash)
        if outputPath.resolve() == cachePath.resolve():
            self._writeReport(report, cachePath)
            return
        # Publish the canonical report first, so an interrupted export still leaves
        # a complete report that can be found on retry.
        self._writeReport(report, cachePath)
        try:
            self._writeReport(report, outputPath)
        except BaseException:
            cachePath.unlink(missing_ok=True)
            raise

    def _writeReport(self, report: EvaluationReport, outputPath: Path) -> None:
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        temporaryPath = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=outputPath.parent, delete=False,
            ) as reportFile:
                temporaryPath = Path(reportFile.name)
                reportFile.write(report.model_dump_json(indent=2))
                reportFile.flush()
                os.fsync(reportFile.fileno())
            os.link(temporaryPath, outputPath)
        finally:
            if temporaryPath is not None:
                temporaryPath.unlink(missing_ok=True)

    def readTextFile(self, filePath: Path) -> str:
        with filePath.open("rb") as inputFile:
            rawText = inputFile.read(1000001)
        if len(rawText) > 1000000:
            raise OSError("The input file exceeds 1 MB.")
        return rawText.decode("utf-8-sig")
