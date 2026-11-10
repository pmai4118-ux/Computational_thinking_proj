import os
import tempfile
from pathlib import Path

from source.Model.evaluationData import EvaluationReport


def readJsonFile(filePath: Path) -> str:
    if filePath.stat().st_size > 1000000:
        raise ValueError("Tệp JSON vượt giới hạn 1 MB.")
    return filePath.read_bytes().decode("utf-8-sig")


def saveReport(report: EvaluationReport, outputPath: Path) -> None:
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
