import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from source.Control.evaluationController import evaluateAnswer
from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import RecordedReview
from source.Model.reportFiles import readJsonFile, saveReport
from source.service.evaluationErrors import EvaluationError
from source.service.providers.geminiInterpreter import GeminiInterpreter
from source.service.providers.recordedInterpreter import RecordedInterpreter
from source.view.evaluationView import renderReport


def readArguments():
    parser = argparse.ArgumentParser(description="PoC đánh giá câu trả lời theo rubric và bằng chứng.")
    parser.add_argument("--input", required=True, type=Path, help="JSON gồm question, rubrics và answer.")
    parser.add_argument("--provider", choices=("gemini", "recorded"), default="gemini")
    parser.add_argument("--recording", type=Path, help="Bản diễn giải có sẵn, khớp inputHash; chỉ dùng với recorded.")
    parser.add_argument("--answerFile", type=Path, help="Tệp UTF-8 chứa nguyên văn câu trả lời mới.")
    parser.add_argument("--output", type=Path, help="JSON kết quả; không ghi đè tệp đã tồn tại.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    if (args.provider == "recorded") != (args.recording is not None):
        parser.error("--recording bắt buộc và chỉ dùng khi --provider recorded.")
    return args


def loadInputs(inputPath: Path, answerPath: Path | None) -> EvaluationInput:
    inputs = EvaluationInput.model_validate_json(readJsonFile(inputPath))
    if answerPath is not None:
        answerData = inputs.answer.model_dump()
        answerData.update(originalText=readJsonFile(answerPath), answerId=f"answer.{uuid4().hex}", revision=1)
        inputData = inputs.model_dump()
        inputData["answer"] = answerData
        inputs = EvaluationInput.model_validate(inputData)
    return inputs


def runCommand(args) -> int:
    try:
        inputs = loadInputs(args.input, args.answerFile)
        outputPath = args.output or Path("localReports") / f"report-{uuid4().hex}.json"
        if outputPath.exists():
            raise EvaluationError("outputExists", "Tệp kết quả đã tồn tại. Chọn đường dẫn mới để giữ bản cũ.")
        if args.provider == "recorded":
            recording = RecordedReview.model_validate_json(readJsonFile(args.recording))
            interpreter = RecordedInterpreter(recording)
        else:
            interpreter = GeminiInterpreter.fromEnvironment()
        report = evaluateAnswer(inputs, interpreter)
        saveReport(report, outputPath)
        print(report.model_dump_json(indent=2) if args.format == "json" else renderReport(report))
        print(f"Đã lưu kết quả: {outputPath.resolve()}", file=sys.stderr)
        return 0
    except EvaluationError as error:
        errorData = {"code": error.code, "message": error.message, "retryable": error.retryable}
    except ValidationError as error:
        fields = [".".join(str(part) for part in issue["loc"]) for issue in error.errors(include_input=False)]
        errorData = {"code": "invalidInput", "message": "Sai cấu trúc hoặc giá trị dữ liệu.", "fields": fields, "retryable": False}
    except (OSError, ValueError) as error:
        errorData = {"code": "fileError", "message": "Không đọc/ghi được tệp UTF-8; kiểm tra đường dẫn, quyền và kích thước.", "retryable": False}
    print(json.dumps({"error": errorData}, ensure_ascii=False), file=sys.stderr)
    return 1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    return runCommand(readArguments())


if __name__ == "__main__":
    raise SystemExit(main())
