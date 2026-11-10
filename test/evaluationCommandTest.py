import json
import subprocess
import sys
from pathlib import Path

import pytest

from source.Model.reportFiles import saveReport
from source.Model.evaluationData import EvaluationReport


repoPath = Path(__file__).resolve().parents[1]


@pytest.fixture
def tempPath(request):
    return request.getfixturevalue("tmp_path")


def runCli(outputPath, *extraArgs):
    return subprocess.run([
        sys.executable, "-m", "source.evaluateAnswer", "--input", "examples/evaluateAnswer/sampleInput.json",
        "--provider", "recorded", "--recording", "examples/evaluateAnswer/sampleReview.json",
        "--output", str(outputPath), *extraArgs,
    ], cwd=repoPath, capture_output=True, encoding="utf-8", timeout=30)


def testCommandRoundTrip(tempPath):
    outputPath = tempPath / "report.json"
    completed = runCli(outputPath, "--format", "json")
    assert completed.returncode == 0, completed.stderr
    data = json.loads(completed.stdout)
    assert data == json.loads(outputPath.read_text(encoding="utf-8"))
    assert data["providerName"] == "recorded"
    assert len(data["results"]) == 4
    assert len(data["feedbackItems"]) == 4
    originalBytes = outputPath.read_bytes()
    repeated = runCli(outputPath)
    assert repeated.returncode == 1
    assert "outputExists" in repeated.stderr
    assert outputPath.read_bytes() == originalBytes
    with pytest.raises(FileExistsError):
        saveReport(EvaluationReport.model_validate(data), outputPath)
    assert len(list(tempPath.iterdir())) == 1


def testTextPresentation(tempPath):
    completed = runCli(tempPath / "report.json")
    assert completed.returncode == 0, completed.stderr
    assert "không phải AI đang chấm" in completed.stdout
    assert "không suy ra năng lực tổng thể" in completed.stdout
    assert "originalText[" in completed.stdout


def testNewAnswerNeedsReview(tempPath):
    answerPath = tempPath / "answer.txt"
    answerPath.write_bytes("Bài mới.\r\nDòng hai.".encode("utf-8"))
    outputPath = tempPath / "report.json"
    completed = runCli(outputPath, "--answerFile", str(answerPath))
    assert completed.returncode == 1
    assert "recordingMismatch" in completed.stderr
    assert not outputPath.exists()
    assert answerPath.read_bytes() == "Bài mới.\r\nDòng hai.".encode("utf-8")
